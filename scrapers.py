"""
scrapers.py — JobHelp Version 1
Individual scraper for every supported job board.

Each scraper returns List[Job].  New boards can be added by
subclassing BaseScraper and registering the class in SCRAPER_REGISTRY.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── HTTP helpers ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = 15  # seconds


def _get(url: str, params: dict | None = None, headers: dict | None = None,
         json_response: bool = False):
    """Safe GET wrapper with a single retry on transient errors."""
    h = {**HEADERS, **(headers or {})}
    for attempt in range(2):
        try:
            resp = requests.get(url, params=params, headers=h,
                                timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json() if json_response else resp
        except requests.RequestException as exc:
            if attempt == 0:
                time.sleep(2)
            else:
                logger.warning("Request failed for %s: %s", url, exc)
    return None


# ── Job dataclass ─────────────────────────────────────────────────────────────

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str                       # Board name
    posted: Optional[datetime] = None
    description: str = ""
    search_term: str = ""             # Which title triggered this result
    remote: bool = False
    tags: List[str] = field(default_factory=list)

    def is_recent(self, hours: int = 24) -> bool:
        """Return True if the job was posted within *hours* hours."""
        if self.posted is None:
            return True  # unknown date — include by default
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        posted = self.posted
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return posted >= cutoff

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "posted": self.posted.isoformat() if self.posted else None,
            "description": self.description,
            "search_term": self.search_term,
            "remote": self.remote,
        }


# ── Base scraper ──────────────────────────────────────────────────────────────

class BaseScraper:
    name: str = "base"

    def __init__(self, config: dict):
        self.config = config
        self.search_config: dict = config.get("search", {})
        self.hours_ago: int = self.search_config.get("hours_ago", 24)
        self.location: str = self.search_config.get("location", "")
        self.max_results: int = self.search_config.get("results_per_board", 25)

    def fetch(self, job_title: str) -> List[Job]:
        raise NotImplementedError

    def search_all(self, job_titles: List[str]) -> List[Job]:
        results: List[Job] = []
        for title in job_titles:
            try:
                jobs = self.fetch(title)
                for j in jobs:
                    j.search_term = title
                # Universal recency filter — keeps jobs posted within hours_ago
                # or jobs with no posting date (unknown age = include them)
                before = len(jobs)
                jobs = [j for j in jobs if j.is_recent(self.hours_ago)]
                filtered_out = before - len(jobs)
                if filtered_out:
                    logger.info(
                        "  [%s] '%s': %d results, %d filtered as older than %dh",
                        self.name, title, before, filtered_out, self.hours_ago,
                    )
                results.extend(jobs)
                time.sleep(1.2)  # polite rate limiting
            except Exception as exc:
                logger.error("[%s] Error searching '%s': %s", self.name, title, exc)
        if not results:
            logger.warning(
                "[%s] returned 0 results across all titles — board may be "
                "blocking requests or no matching jobs found.", self.name,
            )
        return results


# ── Indeed ────────────────────────────────────────────────────────────────────

class IndeedScraper(BaseScraper):
    """Uses Indeed's public RSS feed — no credentials required."""
    name = "Indeed"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "q": job_title,
            "fromage": "1",          # last 1 day
            "sort": "date",
        }
        if self.location:
            params["l"] = self.location

        url = "https://www.indeed.com/rss?" + urllib.parse.urlencode(params)
        resp = _get(url)
        if not resp:
            return []

        jobs: List[Job] = []
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            return []

        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        items = root.findall(".//item")

        for item in items[: self.max_results]:
            def _text(tag: str) -> str:
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            posted = None
            pub_date = _text("pubDate")
            if pub_date:
                try:
                    from email.utils import parsedate_to_datetime
                    posted = parsedate_to_datetime(pub_date).astimezone(timezone.utc)
                except Exception:
                    pass

            # Indeed title format: "Job Title - Company Name - Location"
            raw_title = _text("title")
            parts = [p.strip() for p in raw_title.split(" - ")]
            title = parts[0] if parts else raw_title
            company = parts[1] if len(parts) > 1 else "Unknown"
            location = parts[2] if len(parts) > 2 else self.location or "US"

            description = BeautifulSoup(
                _text("description"), "html.parser"
            ).get_text()[:300]

            job = Job(
                title=title,
                company=company,
                location=location,
                url=_text("link"),
                source=self.name,
                posted=posted,
                description=description,
            )
            jobs.append(job)

        return jobs


# ── LinkedIn ──────────────────────────────────────────────────────────────────

class LinkedInScraper(BaseScraper):
    """Uses LinkedIn's public guest job-search API (no auth needed)."""
    name = "LinkedIn"
    _BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "keywords": job_title,
            "location": self.location or "United States",
            "f_TPR": "r86400",       # posted in last 86 400 s = 24 h
            "start": 0,
        }
        headers = {**HEADERS, "Referer": "https://www.linkedin.com/jobs/"}
        resp = _get(self._BASE, params=params, headers=headers)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []

        for card in soup.select("li")[:self.max_results]:
            title_el = card.select_one(".base-search-card__title")
            company_el = card.select_one(".base-search-card__subtitle")
            location_el = card.select_one(".job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            time_el = card.select_one("time")

            if not title_el or not link_el:
                continue

            posted = None
            if time_el and time_el.get("datetime"):
                try:
                    posted = datetime.fromisoformat(
                        time_el["datetime"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            job = Job(
                title=title_el.get_text(strip=True),
                company=(company_el.get_text(strip=True)
                         if company_el else "Unknown"),
                location=(location_el.get_text(strip=True)
                          if location_el else self.location or "US"),
                url=link_el["href"].split("?")[0],
                source=self.name,
                posted=posted,
            )
            jobs.append(job)

        return jobs


# ── ZipRecruiter ──────────────────────────────────────────────────────────────

class ZipRecruiterScraper(BaseScraper):
    """Scrapes ZipRecruiter's job search page."""
    name = "ZipRecruiter"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "search": job_title,
            "location": self.location or "",
            "days": "1",
        }
        url = "https://www.ziprecruiter.com/candidate/search"
        resp = _get(url, params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []

        for card in soup.select("article.job_result, div[data-testid='job-card']")[:self.max_results]:
            title_el = (card.select_one("h2.title a") or
                        card.select_one("[data-testid='job-title']") or
                        card.select_one("a.job_link"))
            company_el = (card.select_one("a.company_name") or
                          card.select_one("[data-testid='company-name']"))
            location_el = (card.select_one("a.location") or
                           card.select_one("[data-testid='location']"))

            if not title_el:
                continue

            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.ziprecruiter.com" + href

            job = Job(
                title=title_el.get_text(strip=True),
                company=(company_el.get_text(strip=True)
                         if company_el else "Unknown"),
                location=(location_el.get_text(strip=True)
                          if location_el else self.location or "US"),
                url=href,
                source=self.name,
            )
            jobs.append(job)

        return jobs


# ── Glassdoor ─────────────────────────────────────────────────────────────────

class GlassdoorScraper(BaseScraper):
    """Scrapes Glassdoor's public job search results."""
    name = "Glassdoor"

    def fetch(self, job_title: str) -> List[Job]:
        encoded = urllib.parse.quote_plus(job_title)
        url = (
            f"https://www.glassdoor.com/Job/jobs.htm"
            f"?sc.keyword={encoded}&fromAge=1&sort.sortType=date"
        )
        resp = _get(url)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []

        for card in soup.select("li[data-test='jobListing'], li.react-job-listing")[:self.max_results]:
            title_el = (card.select_one("[data-test='job-title']") or
                        card.select_one("a.jobLink"))
            company_el = card.select_one("[data-test='employer-name']")
            location_el = card.select_one("[data-test='emp-location']")
            link_el = card.select_one("a[href*='/job-listing/']")

            if not title_el:
                continue

            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.glassdoor.com" + href

            job = Job(
                title=title_el.get_text(strip=True),
                company=(company_el.get_text(strip=True)
                         if company_el else "Unknown"),
                location=(location_el.get_text(strip=True)
                          if location_el else self.location or "US"),
                url=href,
                source=self.name,
            )
            jobs.append(job)

        return jobs


# ── Dice ──────────────────────────────────────────────────────────────────────

class DiceScraper(BaseScraper):
    """Uses Dice's internal search API — no credentials required."""
    name = "Dice"
    _API = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "q": job_title,
            "countryCode2": "US",
            "radius": "30",
            "radiusUnit": "mi",
            "page": 1,
            "pageSize": self.max_results,
            "filters.postedDate": "ONE",   # last 24 h
            "sort": "-postedDate",
        }
        if self.location:
            params["location"] = self.location

        data = _get(self._API, params=params, json_response=True)
        if not data:
            return []

        jobs: List[Job] = []
        for item in data.get("data", []):
            posted = None
            date_str = item.get("postedDate", "")
            if date_str:
                try:
                    posted = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            job_id = item.get("id", "")
            url = f"https://www.dice.com/job-detail/{job_id}" if job_id else ""

            job = Job(
                title=item.get("title", "N/A"),
                company=item.get("companyPageUrl", item.get("company", "Unknown")),
                location=item.get("location", self.location or "US"),
                url=url,
                source=self.name,
                posted=posted,
                remote=item.get("workplaceTypes", []) and
                       "Remote" in item.get("workplaceTypes", []),
            )
            jobs.append(job)

        return jobs


# ── SimplyHired ───────────────────────────────────────────────────────────────

class SimplyHiredScraper(BaseScraper):
    """Scrapes SimplyHired's public search results."""
    name = "SimplyHired"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "q": job_title,
            "l": self.location or "",
            "dateposted": "1",       # last 24 h
        }
        resp = _get("https://www.simplyhired.com/search", params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []

        for card in soup.select("div[data-testid='job-card'], article.SerpJob")[:self.max_results]:
            title_el = (card.select_one("[data-testid='jobTitle']") or
                        card.select_one("h3.jobposting-title a"))
            company_el = (card.select_one("[data-testid='company']") or
                          card.select_one("span.jobposting-company"))
            location_el = (card.select_one("[data-testid='searchSerpJobLocation']") or
                           card.select_one("span.jobposting-location"))
            link_el = (card.select_one("a[data-testid='job-title-link']") or
                       card.select_one("a.jobposting-permalink"))

            if not title_el:
                continue

            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.simplyhired.com" + href

            job = Job(
                title=title_el.get_text(strip=True),
                company=(company_el.get_text(strip=True)
                         if company_el else "Unknown"),
                location=(location_el.get_text(strip=True)
                          if location_el else self.location or "US"),
                url=href,
                source=self.name,
            )
            jobs.append(job)

        return jobs


# ── Monster ───────────────────────────────────────────────────────────────────

class MonsterScraper(BaseScraper):
    """Scrapes Monster's public job search."""
    name = "Monster"

    def fetch(self, job_title: str) -> List[Job]:
        encoded = urllib.parse.quote_plus(job_title)
        loc = urllib.parse.quote_plus(self.location or "")
        url = (
            f"https://www.monster.com/jobs/search"
            f"?q={encoded}&where={loc}&tm=1"  # tm=1 = last 24 h
        )
        resp = _get(url)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []

        for card in soup.select("div[data-testid='JobCard'], section.card-content")[:self.max_results]:
            title_el = (card.select_one("[data-testid='jobTitle']") or
                        card.select_one("h2.title"))
            company_el = (card.select_one("[data-testid='company']") or
                          card.select_one("div.company"))
            location_el = (card.select_one("[data-testid='location']") or
                           card.select_one("div.location"))
            link_el = card.select_one("a")

            if not title_el or not link_el:
                continue

            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.monster.com" + href

            job = Job(
                title=title_el.get_text(strip=True),
                company=(company_el.get_text(strip=True)
                         if company_el else "Unknown"),
                location=(location_el.get_text(strip=True)
                          if location_el else self.location or "US"),
                url=href,
                source=self.name,
            )
            jobs.append(job)

        return jobs


# ── The Muse ──────────────────────────────────────────────────────────────────

class TheMuseScraper(BaseScraper):
    """Uses The Muse's completely free public API — no key required."""
    name = "The Muse"
    _API = "https://www.themuse.com/api/public/jobs"

    # Map generic titles to Muse category/level slugs
    _LEVEL_MAP = {
        "CTO": "Senior Level",
        "CIO": "Senior Level",
        "VP of Technology": "Senior Level",
        "SVP of Technology": "Senior Level",
        "Head of IT": "Senior Level",
        "Head of Infrastructure": "Senior Level",
        "Director of Technology": "Senior Level",
        "EUC": "Mid Level",
    }

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "page": 1,
            "descending": "true",
        }
        # The Muse doesn't support full-text search in free tier,
        # so we fetch recent tech jobs and filter client-side.
        params["category"] = "IT"

        data = _get(self._API, params=params, json_response=True)
        if not data:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.hours_ago)
        keyword = job_title.lower()
        jobs: List[Job] = []

        for item in data.get("results", []):
            title = item.get("name", "")
            if keyword not in title.lower():
                continue

            posted = None
            date_str = item.get("publication_date", "")
            if date_str:
                try:
                    posted = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            if posted and posted < cutoff:
                continue

            company = (item.get("company", {}).get("name", "Unknown")
                       if isinstance(item.get("company"), dict) else "Unknown")
            locations = item.get("locations", [])
            location = (locations[0].get("name", "Remote")
                        if locations else "Remote")

            refs = item.get("refs", {})
            url = refs.get("landing_page", "")

            job = Job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.name,
                posted=posted,
            )
            jobs.append(job)
            if len(jobs) >= self.max_results:
                break

        return jobs


# ── Adzuna ────────────────────────────────────────────────────────────────────

class AdzunaScraper(BaseScraper):
    """Uses the Adzuna official API (free tier — register at developer.adzuna.com)."""
    name = "Adzuna"

    def __init__(self, config: dict):
        super().__init__(config)
        board_cfg = config.get("job_boards", {}).get("adzuna", {})
        self.app_id = board_cfg.get("app_id", "")
        self.app_key = board_cfg.get("app_key", "")
        self.country = board_cfg.get("country", "us")

    def fetch(self, job_title: str) -> List[Job]:
        if not self.app_id or not self.app_key:
            logger.warning("[Adzuna] app_id / app_key not set — skipping.")
            return []

        url = (
            f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
        )
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": job_title,
            "max_days_old": "1",
            "results_per_page": self.max_results,
            "sort_by": "date",
            "content-type": "application/json",
        }
        if self.location:
            params["where"] = self.location

        data = _get(url, params=params, json_response=True)
        if not data:
            return []

        jobs: List[Job] = []
        for item in data.get("results", []):
            posted = None
            date_str = item.get("created", "")
            if date_str:
                try:
                    posted = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            job = Job(
                title=item.get("title", "N/A"),
                company=item.get("company", {}).get("display_name", "Unknown"),
                location=item.get("location", {}).get("display_name",
                                                       self.location or "US"),
                url=item.get("redirect_url", ""),
                source=self.name,
                posted=posted,
                description=item.get("description", "")[:300],
            )
            jobs.append(job)

        return jobs


# ── CareerBuilder ─────────────────────────────────────────────────────────────

class CareerBuilderScraper(BaseScraper):
    """Scrapes CareerBuilder's public job search."""
    name = "CareerBuilder"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "keywords": job_title,
            "location": self.location or "",
            "posted": "today",
        }
        resp = _get("https://www.careerbuilder.com/jobs", params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []

        for card in soup.select("li[data-job-did], div.data-results-content")[:self.max_results]:
            title_el = (card.select_one("div.show-for-medium-up a") or
                        card.select_one("a.job-title"))
            company_el = (card.select_one("div.data-details span:first-child") or
                          card.select_one("[data-company]"))
            location_el = card.select_one("[data-location]")

            if not title_el:
                continue

            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.careerbuilder.com" + href

            job = Job(
                title=title_el.get_text(strip=True),
                company=(company_el.get_text(strip=True)
                         if company_el else "Unknown"),
                location=(location_el.get_text(strip=True)
                          if location_el else self.location or "US"),
                url=href,
                source=self.name,
            )
            jobs.append(job)

        return jobs


# ── Remote OK ─────────────────────────────────────────────────────────────────

class RemoteOKScraper(BaseScraper):
    """Uses Remote OK's free public JSON API — no auth required."""
    name = "RemoteOK"
    _API = "https://remoteok.com/api"

    def fetch(self, job_title: str) -> List[Job]:
        keyword = job_title.lower().replace(" ", "+")
        data = _get(f"{self._API}?tag={keyword}",
                    headers={"Accept": "application/json"},
                    json_response=True)
        if not data or not isinstance(data, list):
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.hours_ago)
        jobs: List[Job] = []

        for item in data:
            if not isinstance(item, dict) or "position" not in item:
                continue

            posted = None
            epoch = item.get("epoch", 0)
            if epoch:
                posted = datetime.fromtimestamp(int(epoch), tz=timezone.utc)

            if posted and posted < cutoff:
                continue

            slug = item.get("slug", "")
            url = f"https://remoteok.com/remote-jobs/{slug}" if slug else ""

            job = Job(
                title=item.get("position", "N/A"),
                company=item.get("company", "Unknown"),
                location="Remote",
                url=url,
                source=self.name,
                posted=posted,
                remote=True,
                tags=item.get("tags", []),
                description=BeautifulSoup(
                    item.get("description", ""), "html.parser"
                ).get_text()[:300],
            )
            jobs.append(job)
            if len(jobs) >= self.max_results:
                break

        return jobs


# ── Jobicy ────────────────────────────────────────────────────────────────────

class JobicyScraper(BaseScraper):
    """Uses Jobicy's free public API — no auth required."""
    name = "Jobicy"
    _API = "https://jobicy.com/api/v2/remote-jobs"

    def fetch(self, job_title: str) -> List[Job]:
        params = {
            "count": self.max_results,
            "tag": job_title,
        }
        data = _get(self._API, params=params, json_response=True)
        if not data:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.hours_ago)
        jobs: List[Job] = []

        for item in data.get("jobs", []):
            posted = None
            date_str = item.get("pubDate", "")
            if date_str:
                try:
                    posted = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            if posted and posted < cutoff:
                continue

            job = Job(
                title=item.get("jobTitle", "N/A"),
                company=item.get("companyName", "Unknown"),
                location=item.get("jobGeo", "Remote"),
                url=item.get("url", ""),
                source=self.name,
                posted=posted,
                remote=True,
                description=BeautifulSoup(
                    item.get("jobExcerpt", ""), "html.parser"
                ).get_text()[:300],
            )
            jobs.append(job)

        return jobs


# ── Registry & factory ────────────────────────────────────────────────────────

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "indeed": IndeedScraper,
    "linkedin": LinkedInScraper,
    "ziprecruiter": ZipRecruiterScraper,
    "glassdoor": GlassdoorScraper,
    "dice": DiceScraper,
    "simplyhired": SimplyHiredScraper,
    "monster": MonsterScraper,
    "themuse": TheMuseScraper,
    "adzuna": AdzunaScraper,
    "careerbuilder": CareerBuilderScraper,
    "remoteok": RemoteOKScraper,
    "jobicy": JobicyScraper,
}


def build_scrapers(config: dict) -> List[BaseScraper]:
    """Return a list of enabled scraper instances based on config."""
    boards_cfg = config.get("job_boards", {})
    scrapers = []
    for key, cls in SCRAPER_REGISTRY.items():
        board = boards_cfg.get(key, {})
        if board.get("enabled", False):
            scrapers.append(cls(config))
            logger.info("Scraper enabled: %s", cls.name)
    return scrapers


def deduplicate(jobs: List[Job]) -> List[Job]:
    """Remove duplicate postings (same title + company)."""
    seen: set[tuple] = set()
    unique: List[Job] = []
    for job in jobs:
        key = (job.title.lower().strip(), job.company.lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique
