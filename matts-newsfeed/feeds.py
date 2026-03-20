"""
feeds.py — Matt's Newsfeed
Fetch and parse RSS feeds + basic web scraping for kratom and NJ Cannabis news sources.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import threading
import logging

from database import get_connection, upsert_article, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

USER_AGENT = "MattsNewsfeed/1.0"
TIMEOUT = 15

# Articles older than this are not stored at all
MAX_AGE_DAYS = 90


# ---------- Default kratom sources ----------

DEFAULT_SOURCES = [
    # === Google News RSS (broad + targeted) ===
    {"name": "Google News — Kratom", "url": "https://news.google.com/rss/search?q=kratom&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "news", "tab": "kratom"},
    {"name": "Google News — Kratom FDA", "url": "https://news.google.com/rss/search?q=kratom+FDA&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation", "tab": "kratom"},
    {"name": "Google News — Kratom Legislation", "url": "https://news.google.com/rss/search?q=kratom+legislation+law+ban&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation", "tab": "kratom"},
    {"name": "Google News — 7-Hydroxymitragynine", "url": "https://news.google.com/rss/search?q=7-hydroxymitragynine&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation", "tab": "kratom"},

    # === Kratom-focused blogs & sites (RSS) ===
    {"name": "Kratom Science", "url": "https://www.kratomscience.com/feed/", "source_type": "rss", "category": "science", "tab": "kratom"},
    {"name": "Kratom Science Podcast", "url": "https://feeds.buzzsprout.com/999864.rss", "source_type": "rss", "category": "science", "tab": "kratom"},
    {"name": "Top Tree Herbs Blog", "url": "https://toptreeherbs.com/feed/", "source_type": "rss", "category": "news", "tab": "kratom"},
    {"name": "The Kratom Company Blog", "url": "https://thekratomco.com/feed/", "source_type": "rss", "category": "news", "tab": "kratom"},
    {"name": "Kraken Kratom Resources", "url": "https://krakenkratom.com/resources/feed/", "source_type": "rss", "category": "news", "tab": "kratom"},
    {"name": "Christopher's Organic Botanicals", "url": "https://christophersorganicbotanicals.com/blogs/news.atom", "source_type": "rss", "category": "news", "tab": "kratom"},
    {"name": "CaliBotanicals Blog", "url": "https://calibotanicals.com/feed/", "source_type": "rss", "category": "news", "tab": "kratom"},

    # === Government / Regulation (RSS) ===
    {"name": "FDA Press Releases", "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml", "source_type": "rss", "category": "regulation", "tab": "kratom"},
    {"name": "Federal Register — Kratom", "url": "https://www.federalregister.gov/documents/search.atom?conditions%5Bterm%5D=kratom", "source_type": "rss", "category": "regulation", "tab": "kratom"},
    {"name": "Federal Register — 7-OH", "url": "https://www.federalregister.gov/documents/search.atom?conditions%5Bterm%5D=7-hydroxymitragynine", "source_type": "rss", "category": "regulation", "tab": "kratom"},

    # === Science / PubMed (RSS) ===
    {"name": "PubMed — Kratom Research", "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1wCKfMEfKODRHOYBu3RCOSL1UbMaFz3JwDxMBfGMKzavJXGO8W/?limit=20&utm_campaign=pubmed-2&fc=20210101000000", "source_type": "rss", "category": "science", "tab": "kratom"},

    # === Reddit (RSS) ===
    {"name": "r/kratom", "url": "https://www.reddit.com/r/kratom/.rss", "source_type": "rss", "category": "community", "tab": "kratom"},
    {"name": "r/kratom — News Flair", "url": "https://www.reddit.com/r/kratom/search.rss?q=flair%3Anews&sort=new", "source_type": "rss", "category": "community", "tab": "kratom"},
    {"name": "r/KratomKorner", "url": "https://www.reddit.com/r/KratomKorner/.rss", "source_type": "rss", "category": "community", "tab": "kratom"},
    {"name": "r/quittingkratom", "url": "https://www.reddit.com/r/quittingkratom/.rss", "source_type": "rss", "category": "community", "tab": "kratom"},
    {"name": "Reddit Search — Kratom News", "url": "https://www.reddit.com/search.rss?q=kratom+news&sort=new", "source_type": "rss", "category": "community", "tab": "kratom"},

    # === Advocacy organizations (scrape) ===
    {"name": "American Kratom Association — News", "url": "https://www.americankratom.org/news", "source_type": "scrape", "category": "advocacy", "tab": "kratom"},
    {"name": "AKA — Press Releases", "url": "https://www.americankratom.org/releases", "source_type": "scrape", "category": "advocacy", "tab": "kratom"},
    {"name": "Protect Kratom (AKA Action)", "url": "https://www.protectkratom.org/", "source_type": "scrape", "category": "advocacy", "tab": "kratom"},
    {"name": "Botanical Education Alliance", "url": "https://www.botanicaleducation.com/", "source_type": "scrape", "category": "advocacy", "tab": "kratom"},
    {"name": "Kratom United", "url": "https://kratomunited.com/", "source_type": "scrape", "category": "advocacy", "tab": "kratom"},

    # === Government / Regulation (scrape) ===
    {"name": "FDA — Kratom Page", "url": "https://www.fda.gov/news-events/public-health-focus/fda-and-kratom", "source_type": "scrape", "category": "regulation", "tab": "kratom"},
    {"name": "DEA Press Releases", "url": "https://www.dea.gov/press-releases", "source_type": "scrape", "category": "regulation", "tab": "kratom"},
    {"name": "NIDA — Kratom Research", "url": "https://nida.nih.gov/research-topics/kratom", "source_type": "scrape", "category": "science", "tab": "kratom"},
    {"name": "LAPPA — Kratom State Laws", "url": "https://legislativeanalysis.org/kratom-summary-of-state-laws/", "source_type": "scrape", "category": "regulation", "tab": "kratom"},
]


# ---------- NJ Cannabis sources ----------

NJ_CANNABIS_SOURCES = [
    # === Google News RSS — NJ-targeted queries ===
    {"name": "Google News — NJ Cannabis", "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+cannabis&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "news", "tab": "nj_cannabis"},
    {"name": "Google News — NJ Marijuana", "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+marijuana&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "news", "tab": "nj_cannabis"},
    {"name": "Google News — NJ Dispensary", "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+dispensary&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "news", "tab": "nj_cannabis"},
    {"name": "Google News — NJ Cannabis Regulation", "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+cannabis+regulation+NJCRC&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation", "tab": "nj_cannabis"},
    {"name": "Google News — NJ Weed Law", "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+weed+legalization&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation", "tab": "nj_cannabis"},

    # === NJ-specific news outlets (RSS) ===
    {"name": "NJSpotlightNews — Cannabis", "url": "https://njspotlightnews.org/topic/cannabis/feed/", "source_type": "rss", "category": "news", "tab": "nj_cannabis"},
    {"name": "MJBizDaily — New Jersey", "url": "https://mjbizdaily.com/tag/new-jersey/feed/", "source_type": "rss", "category": "business", "tab": "nj_cannabis"},

    # === Reddit (RSS) ===
    {"name": "r/NJmarijuana", "url": "https://www.reddit.com/r/NJmarijuana/.rss", "source_type": "rss", "category": "community", "tab": "nj_cannabis"},
    {"name": "r/newjersey — Cannabis Search", "url": "https://www.reddit.com/r/newjersey/search.rss?q=cannabis+marijuana+weed+dispensary&sort=new&restrict_sr=1", "source_type": "rss", "category": "community", "tab": "nj_cannabis"},

    # === NJ government & regulatory (scrape) ===
    {"name": "NJ Cannabis Regulatory Commission", "url": "https://www.njcrc.nj.gov/", "source_type": "scrape", "category": "regulation", "tab": "nj_cannabis"},
    {"name": "NJ.com — Cannabis", "url": "https://www.nj.com/marijuana/", "source_type": "scrape", "category": "news", "tab": "nj_cannabis"},
    {"name": "NJ Legislature — Cannabis Bills", "url": "https://www.njleg.state.nj.us/", "source_type": "scrape", "category": "regulation", "tab": "nj_cannabis"},
]


# ---------- Date normalization ----------

def normalize_date(date_str: str) -> str:
    """
    Parse any common date string into ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SSZ).
    Returns '' if unparseable. Articles with no date use fetched_at for sorting.
    """
    if not date_str:
        return ""
    date_str = date_str.strip()

    # RFC 2822 (standard RSS pubDate: "Mon, 18 Mar 2024 12:00:00 +0000")
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    # ISO 8601 variants
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(date_str[:len(fmt)], fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

    return ""


def _is_within_90_days(published_parsed: str) -> bool:
    """Return True if the parsed date is within the last 90 days (or unparseable — allow it through)."""
    if not published_parsed:
        return True  # no date info — let it in, purge will handle it later
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    try:
        dt = datetime.strptime(published_parsed, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt >= cutoff
    except Exception:
        return True


def seed_sources():
    """Upsert all default sources — safe to call repeatedly (new sources added on each run)."""
    conn = get_connection()
    for s in DEFAULT_SOURCES + NJ_CANNABIS_SOURCES:
        conn.execute(
            "INSERT OR IGNORE INTO sources (name, url, source_type, enabled, tab) VALUES (?, ?, ?, 1, ?)",
            (s["name"], s["url"], s["source_type"], s.get("tab", "kratom")),
        )
    conn.commit()
    conn.close()


# ---------- RSS parsing ----------

def parse_rss(xml_text: str, source_name: str, category: str = "general", tab: str = "kratom") -> List[dict]:
    """Parse RSS/Atom XML and return list of article dicts."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning(f"XML parse error for {source_name}: {e}")
        return articles

    # RSS 2.0
    for item in root.iter("item"):
        title = _text(item, "title")
        link = _text(item, "link")
        if not title or not link:
            continue
        raw_date = _text(item, "pubDate") or ""
        parsed = normalize_date(raw_date)
        if not _is_within_90_days(parsed):
            continue
        articles.append({
            "title": title,
            "url": link,
            "source": source_name,
            "author": _text(item, "author") or _text(item, "{http://purl.org/dc/elements/1.1/}creator") or "",
            "summary": _clean_html(_text(item, "description") or ""),
            "published": raw_date,
            "published_parsed": parsed,
            "category": category,
            "tab": tab,
        })

    # Atom
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = _text(entry, "{http://www.w3.org/2005/Atom}title")
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.get("href", "") if link_el is not None else ""
        if not title or not link:
            continue
        raw_date = _text(entry, "{http://www.w3.org/2005/Atom}updated") or ""
        parsed = normalize_date(raw_date)
        if not _is_within_90_days(parsed):
            continue
        articles.append({
            "title": title,
            "url": link,
            "source": source_name,
            "author": _text(entry, "{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name") or "",
            "summary": _clean_html(_text(entry, "{http://www.w3.org/2005/Atom}summary") or _text(entry, "{http://www.w3.org/2005/Atom}content") or ""),
            "published": raw_date,
            "published_parsed": parsed,
            "category": category,
            "tab": tab,
        })

    return articles


def _text(parent, tag: str) -> Optional[str]:
    el = parent.find(tag)
    return el.text.strip() if el is not None and el.text else None


def _clean_html(html: str) -> str:
    """Strip HTML tags from summary text."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)[:500]


# ---------- Fetching ----------

def fetch_rss(url: str, source_name: str, category: str = "general", tab: str = "kratom") -> List[dict]:
    """Download and parse an RSS feed."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        return parse_rss(resp.text, source_name, category, tab)
    except Exception as e:
        log.warning(f"Failed to fetch {source_name} ({url}): {e}")
        return []


def fetch_scrape(url: str, source_name: str, category: str = "general", tab: str = "kratom") -> List[dict]:
    """Generic scraper: extract article-like links from a page."""
    articles = []
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        from urllib.parse import urlparse, urljoin
        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        seen_urls = set()

        for a_tag in soup.select("article a[href], .post a[href], .news a[href], "
                                  ".entry a[href], .content a[href], h2 a[href], "
                                  "h3 a[href], .card a[href], a[href]"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or not href or len(title) < 15:
                continue
            if any(skip in href.lower() for skip in ["#", "javascript:", "mailto:", "login", "signup", "cart"]):
                continue
            full_url = href if href.startswith("http") else urljoin(base_domain, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            articles.append({
                "title": title[:200],
                "url": full_url,
                "source": source_name,
                "author": "",
                "summary": "",
                "published": "",
                "published_parsed": "",
                "category": category,
                "tab": tab,
            })

        articles = articles[:50]
    except Exception as e:
        log.warning(f"Scrape failed for {source_name}: {e}")
    return articles


def _get_source_tab(url: str, all_sources: list) -> str:
    """Look up the tab for a source URL from the combined source list."""
    for s in all_sources:
        if s["url"] == url:
            return s.get("tab", "kratom")
    return "kratom"


def fetch_all_sources(progress_callback=None):
    """Fetch all enabled sources and upsert articles into DB. Returns count of new articles."""
    conn = get_connection()
    sources = conn.execute("SELECT * FROM sources WHERE enabled = 1").fetchall()
    conn.close()

    all_defaults = DEFAULT_SOURCES + NJ_CANNABIS_SOURCES
    new_count = 0
    total = len(sources)

    for i, src in enumerate(sources):
        name = src["name"]
        url = src["url"]
        stype = src["source_type"]
        tab = src["tab"] if src["tab"] else _get_source_tab(url, all_defaults)

        if progress_callback:
            progress_callback(i + 1, total, name)

        # Determine category from source lists
        cat = "general"
        for ds in all_defaults:
            if ds["url"] == url:
                cat = ds.get("category", "general")
                break

        if stype == "rss":
            articles = fetch_rss(url, name, cat, tab)
        elif stype == "scrape":
            articles = fetch_scrape(url, name, cat, tab)
        else:
            articles = []

        for a in articles:
            if upsert_article(**a):
                new_count += 1

        c = get_connection()
        c.execute("UPDATE sources SET last_fetched = ? WHERE id = ?",
                  (datetime.utcnow().isoformat(), src["id"]))
        c.commit()
        c.close()

    return new_count


def fetch_all_threaded(progress_callback=None, done_callback=None):
    """Run fetch_all_sources in a background thread."""
    def _run():
        count = fetch_all_sources(progress_callback)
        if done_callback:
            done_callback(count)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
