"""
feeds.py — Matt's Newsfeed
Fetch and parse RSS feeds + basic web scraping for cannabis/marijuana/weed news.
Two categories:
  "nj"       — New Jersey state-level cannabis news
  "national" — Federal / US national cannabis news
"""

import xml.etree.ElementTree as ET
from datetime import datetime
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

# ---------- Sources ----------

DEFAULT_SOURCES = [

    # =====================================================================
    # NEW JERSEY — cannabis / marijuana / weed news
    # =====================================================================

    # --- Google News RSS (NJ-specific queries) ---
    {
        "name": "Google News — Cannabis New Jersey",
        "url": "https://news.google.com/rss/search?q=cannabis+%22New+Jersey%22&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — Marijuana New Jersey",
        "url": "https://news.google.com/rss/search?q=marijuana+%22New+Jersey%22&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — Weed New Jersey",
        "url": "https://news.google.com/rss/search?q=weed+%22New+Jersey%22&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — NJ Dispensary",
        "url": "https://news.google.com/rss/search?q=dispensary+%22New+Jersey%22&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — NJ Cannabis Legislation",
        "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+cannabis+legislation+law&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — NJ Cannabis Regulation",
        "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+cannabis+regulation+NJCRC&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — NJ Cannabis Tax Revenue",
        "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+cannabis+tax+revenue+sales&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Google News — NJ Cannabis License",
        "url": "https://news.google.com/rss/search?q=%22New+Jersey%22+cannabis+license+permit&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "nj",
    },

    # --- NJ regional news outlets (RSS) ---
    {
        "name": "NJ.com — Cannabis",
        "url": "https://www.nj.com/arcio/rss/category/marijuana/",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "NJ Spotlight News",
        "url": "https://www.njspotlightnews.org/feed/",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "NJ Cannabis Insider",
        "url": "https://www.njcannabisinsider.com/feed/",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "The Record (NorthJersey.com) — Cannabis",
        "url": "https://www.northjersey.com/arcio/rss/category/marijuana/",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "Asbury Park Press — Cannabis",
        "url": "https://www.app.com/arcio/rss/category/marijuana/",
        "source_type": "rss", "category": "nj",
    },

    # --- Reddit (NJ) ---
    {
        "name": "r/njcannabis",
        "url": "https://www.reddit.com/r/njcannabis/.rss",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "r/newjersey — Cannabis Search",
        "url": "https://www.reddit.com/r/newjersey/search.rss?q=cannabis+marijuana+weed&sort=new&restrict_sr=1",
        "source_type": "rss", "category": "nj",
    },
    {
        "name": "r/NewJerseyMarijuana",
        "url": "https://www.reddit.com/r/NewJerseyMarijuana/.rss",
        "source_type": "rss", "category": "nj",
    },

    # --- NJ government / regulatory (scrape) ---
    {
        "name": "NJ Cannabis Regulatory Commission",
        "url": "https://www.nj.gov/cannabis/news/",
        "source_type": "scrape", "category": "nj",
    },
    {
        "name": "NJ.gov — Cannabis Homepage",
        "url": "https://www.nj.gov/cannabis/",
        "source_type": "scrape", "category": "nj",
    },
    {
        "name": "NJ Legislature — Cannabis Bills",
        "url": "https://www.njleg.state.nj.us/bill-search/2024/A1",
        "source_type": "scrape", "category": "nj",
    },
    {
        "name": "NJ Attorney General — Cannabis",
        "url": "https://www.njconsumeraffairs.gov/mmed",
        "source_type": "scrape", "category": "nj",
    },

    # =====================================================================
    # NATIONAL — federal / US-wide cannabis news
    # =====================================================================

    # --- Google News RSS (national queries) ---
    {
        "name": "Google News — Cannabis USA",
        "url": "https://news.google.com/rss/search?q=cannabis+USA+national&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Marijuana Legalization",
        "url": "https://news.google.com/rss/search?q=marijuana+legalization&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Cannabis Federal",
        "url": "https://news.google.com/rss/search?q=cannabis+federal+rescheduling&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Marijuana DEA",
        "url": "https://news.google.com/rss/search?q=marijuana+DEA+schedule&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Cannabis FDA",
        "url": "https://news.google.com/rss/search?q=cannabis+FDA+regulation&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Marijuana Congress",
        "url": "https://news.google.com/rss/search?q=marijuana+Congress+legislation+bill&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Cannabis Industry",
        "url": "https://news.google.com/rss/search?q=cannabis+industry+market&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Hemp CBD",
        "url": "https://news.google.com/rss/search?q=hemp+CBD+federal&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Google News — Cannabis Banking SAFE Act",
        "url": "https://news.google.com/rss/search?q=cannabis+banking+%22SAFE+Act%22&hl=en-US&gl=US&ceid=US:en",
        "source_type": "rss", "category": "national",
    },

    # --- Dedicated cannabis news outlets (RSS) ---
    {
        "name": "Marijuana Moment",
        "url": "https://www.marijuanamoment.net/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Cannabis Wire",
        "url": "https://cannabiswire.com/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "MJBizDaily",
        "url": "https://mjbizdaily.com/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "NORML News",
        "url": "https://norml.org/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Leafly News",
        "url": "https://www.leafly.com/news/rss.xml",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "High Times",
        "url": "https://hightimes.com/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Cannabis Business Times",
        "url": "https://www.cannabisbusinesstimes.com/rss/all-articles.aspx",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Green Market Report",
        "url": "https://greenmarketreport.com/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "The Fresh Toast",
        "url": "https://thefreshtoast.com/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Cannabis Now",
        "url": "https://cannabisnow.com/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Weedmaps News",
        "url": "https://weedmaps.com/news/feed/",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Benzinga Cannabis",
        "url": "https://www.benzinga.com/topic/cannabis/feed",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Rolling Stone — Cannabis",
        "url": "https://www.rollingstone.com/t/cannabis/feed/",
        "source_type": "rss", "category": "national",
    },

    # --- Federal Register (RSS) ---
    {
        "name": "Federal Register — Cannabis",
        "url": "https://www.federalregister.gov/documents/search.atom?conditions%5Bterm%5D=cannabis",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Federal Register — Marijuana",
        "url": "https://www.federalregister.gov/documents/search.atom?conditions%5Bterm%5D=marijuana",
        "source_type": "rss", "category": "national",
    },

    # --- Science / PubMed (RSS) ---
    {
        "name": "PubMed — Cannabis Research",
        "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1LLrqz5kGrEdOaA7TEOmHB0Oa6C4r5NkZm_MaY-D0w4Aq7v3eB/?limit=20&utm_campaign=pubmed-2&fc=20210101000000",
        "source_type": "rss", "category": "national",
    },

    # --- Reddit (national cannabis) ---
    {
        "name": "r/cannabis",
        "url": "https://www.reddit.com/r/cannabis/.rss",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "r/weed",
        "url": "https://www.reddit.com/r/weed/.rss",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "r/trees",
        "url": "https://www.reddit.com/r/trees/.rss",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "r/marijuana",
        "url": "https://www.reddit.com/r/marijuana/.rss",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "r/weedstocks",
        "url": "https://www.reddit.com/r/weedstocks/.rss",
        "source_type": "rss", "category": "national",
    },
    {
        "name": "Reddit Search — Cannabis Legalization",
        "url": "https://www.reddit.com/search.rss?q=cannabis+legalization+marijuana&sort=new",
        "source_type": "rss", "category": "national",
    },

    # --- Government / Federal (scrape) ---
    {
        "name": "DEA — Press Releases",
        "url": "https://www.dea.gov/press-releases",
        "source_type": "scrape", "category": "national",
    },
    {
        "name": "FDA — Cannabis & Cannabis-Derived Compounds",
        "url": "https://www.fda.gov/news-events/public-health-focus/fda-and-cannabis-research-and-drug-approval-process",
        "source_type": "scrape", "category": "national",
    },
    {
        "name": "NIDA — Cannabis Research",
        "url": "https://nida.nih.gov/research-topics/cannabis-marijuana",
        "source_type": "scrape", "category": "national",
    },
    {
        "name": "Congress.gov — Cannabis Bills",
        "url": "https://www.congress.gov/search?q=%7B%22source%22%3A%22legislation%22%2C%22search%22%3A%22cannabis+marijuana%22%7D",
        "source_type": "scrape", "category": "national",
    },
    {
        "name": "NORML — State Laws",
        "url": "https://norml.org/laws/",
        "source_type": "scrape", "category": "national",
    },
    {
        "name": "LAPPA — Cannabis State Laws",
        "url": "https://legislativeanalysis.org/marijuana-summary-of-state-laws/",
        "source_type": "scrape", "category": "national",
    },
]


def seed_sources():
    """Clear old sources and insert current cannabis sources."""
    conn = get_connection()
    # Check if we're already seeded with cannabis sources
    existing = conn.execute(
        "SELECT COUNT(*) FROM sources WHERE name LIKE '%Cannabis%' OR name LIKE '%Marijuana%' OR name LIKE '%marijuana%'"
    ).fetchone()[0]
    if existing == 0:
        # Remove any old kratom sources and insert cannabis ones
        conn.execute("DELETE FROM sources")
        for s in DEFAULT_SOURCES:
            conn.execute(
                "INSERT OR IGNORE INTO sources (name, url, source_type, enabled) VALUES (?, ?, ?, 1)",
                (s["name"], s["url"], s["source_type"]),
            )
        conn.commit()
        log.info(f"Seeded {len(DEFAULT_SOURCES)} cannabis news sources.")
    conn.close()


# ---------- RSS parsing ----------

def parse_rss(xml_text: str, source_name: str, category: str = "general") -> List[dict]:
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
        articles.append({
            "title": title,
            "url": link,
            "source": source_name,
            "author": _text(item, "author") or _text(item, "{http://purl.org/dc/elements/1.1/}creator") or "",
            "summary": _clean_html(_text(item, "description") or ""),
            "published": _text(item, "pubDate") or "",
            "category": category,
        })

    # Atom
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = _text(entry, "{http://www.w3.org/2005/Atom}title")
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.get("href", "") if link_el is not None else ""
        if not title or not link:
            continue
        articles.append({
            "title": title,
            "url": link,
            "source": source_name,
            "author": _text(entry, "{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name") or "",
            "summary": _clean_html(_text(entry, "{http://www.w3.org/2005/Atom}summary") or _text(entry, "{http://www.w3.org/2005/Atom}content") or ""),
            "published": _text(entry, "{http://www.w3.org/2005/Atom}updated") or "",
            "category": category,
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

def fetch_rss(url: str, source_name: str, category: str = "general") -> List[dict]:
    """Download and parse an RSS feed."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        return parse_rss(resp.text, source_name, category)
    except Exception as e:
        log.warning(f"Failed to fetch {source_name} ({url}): {e}")
        return []


def fetch_scrape(url: str, source_name: str, category: str = "general") -> List[dict]:
    """Generic scraper: extract article-like links from a page."""
    articles = []
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        from urllib.parse import urlparse, urljoin
        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        seen_urls = set()

        # Look for article-like links: <a> tags with substantial text
        for a_tag in soup.select("article a[href], .post a[href], .news a[href], "
                                  ".entry a[href], .content a[href], h2 a[href], "
                                  "h3 a[href], .card a[href], a[href]"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or not href or len(title) < 15:
                continue
            # Skip nav/footer/utility links
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
                "category": category,
            })

        # Limit to avoid flooding DB with nav links
        articles = articles[:50]
    except Exception as e:
        log.warning(f"Scrape failed for {source_name}: {e}")
    return articles


def fetch_all_sources(progress_callback=None):
    """Fetch all enabled sources and upsert articles into DB. Returns count of new articles."""
    conn = get_connection()
    sources = conn.execute("SELECT * FROM sources WHERE enabled = 1").fetchall()
    conn.close()

    new_count = 0
    total = len(sources)

    # Build URL -> category lookup from DEFAULT_SOURCES
    url_to_category = {ds["url"]: ds.get("category", "general") for ds in DEFAULT_SOURCES}

    for i, src in enumerate(sources):
        name = src["name"]
        url = src["url"]
        stype = src["source_type"]

        if progress_callback:
            progress_callback(i + 1, total, name)

        cat = url_to_category.get(url, "general")

        if stype == "rss":
            articles = fetch_rss(url, name, cat)
        elif stype == "scrape":
            articles = fetch_scrape(url, name, cat)
        else:
            articles = []

        for a in articles:
            if upsert_article(**a):
                new_count += 1

        # Update last_fetched
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
