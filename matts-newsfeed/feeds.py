"""
feeds.py — Matt's Newsfeed
Fetch and parse RSS feeds + basic web scraping for kratom news sources.
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

# ---------- Default kratom sources ----------

DEFAULT_SOURCES = [
    # Advocacy / organizations
    {"name": "American Kratom Association", "url": "https://www.americankratom.org/media/news", "source_type": "scrape", "category": "advocacy"},
    {"name": "Kratom Science", "url": "https://www.kratomscience.com/feed/", "source_type": "rss", "category": "science"},

    # News via Google News RSS
    {"name": "Google News — Kratom", "url": "https://news.google.com/rss/search?q=kratom&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "news"},
    {"name": "Google News — Kratom FDA", "url": "https://news.google.com/rss/search?q=kratom+FDA&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation"},
    {"name": "Google News — Kratom legislation", "url": "https://news.google.com/rss/search?q=kratom+legislation+law&hl=en-US&gl=US&ceid=US:en", "source_type": "rss", "category": "regulation"},

    # Reddit
    {"name": "r/kratom", "url": "https://www.reddit.com/r/kratom/new/.rss", "source_type": "rss", "category": "community"},
    {"name": "r/KratomKorner", "url": "https://www.reddit.com/r/KratomKorner/new/.rss", "source_type": "rss", "category": "community"},

    # Science / PubMed
    {"name": "PubMed — Kratom research", "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1wCKfMEfKODRHOYBu3RCOSL1UbMaFz3JwDxMBfGMKzavJXGO8W/?limit=20&utm_campaign=pubmed-2&fc=20210101000000", "source_type": "rss", "category": "science"},

    # FDA press releases (general, filtered client-side)
    {"name": "FDA Press Releases", "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml", "source_type": "rss", "category": "regulation"},
]


def seed_sources():
    """Insert default sources if the sources table is empty."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    if count == 0:
        for s in DEFAULT_SOURCES:
            conn.execute(
                "INSERT OR IGNORE INTO sources (name, url, source_type, enabled) VALUES (?, ?, ?, 1)",
                (s["name"], s["url"], s["source_type"]),
            )
        conn.commit()
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


def fetch_scrape_aka(url: str, source_name: str) -> List[dict]:
    """Scrape the AKA news page as a fallback."""
    articles = []
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a_tag in soup.select("a[href]"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if title and href and "/media/" in href and len(title) > 20:
                full_url = href if href.startswith("http") else f"https://www.americankratom.org{href}"
                articles.append({
                    "title": title,
                    "url": full_url,
                    "source": source_name,
                    "author": "AKA",
                    "summary": "",
                    "published": "",
                    "category": "advocacy",
                })
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

    for i, src in enumerate(sources):
        name = src["name"]
        url = src["url"]
        stype = src["source_type"]

        if progress_callback:
            progress_callback(i + 1, total, name)

        # Determine category from DEFAULT_SOURCES
        cat = "general"
        for ds in DEFAULT_SOURCES:
            if ds["url"] == url:
                cat = ds.get("category", "general")
                break

        if stype == "rss":
            articles = fetch_rss(url, name, cat)
        elif stype == "scrape":
            articles = fetch_scrape_aka(url, name)
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
