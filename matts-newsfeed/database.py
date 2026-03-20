"""
database.py — Chris's Cannabis Counter
SQLite database for caching articles and bookmarks.
"""

import sqlite3
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional
import re


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matts_newsfeed.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            url         TEXT UNIQUE NOT NULL,
            source      TEXT NOT NULL,
            author      TEXT DEFAULT '',
            summary     TEXT DEFAULT '',
            image_url   TEXT DEFAULT '',
            published   TEXT DEFAULT '',
            fetched_at  TEXT NOT NULL,
            is_saved    INTEGER DEFAULT 0,
            is_read     INTEGER DEFAULT 0,
            category    TEXT DEFAULT 'general'
        );

        CREATE TABLE IF NOT EXISTS sources (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            url          TEXT UNIQUE NOT NULL,
            source_type  TEXT NOT NULL,
            enabled      INTEGER DEFAULT 1,
            last_fetched TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_fetched   ON articles(fetched_at DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_saved     ON articles(is_saved);
        CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_articles_category  ON articles(category);
    """)
    conn.commit()
    conn.close()


# ── Date normalisation ────────────────────────────────────────────────────────

def normalize_date(date_str: str) -> str:
    """
    Convert any RSS/Atom date string to ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ).
    Returns '' if the date cannot be parsed.
    """
    if not date_str:
        return ""
    s = date_str.strip()

    # RFC 2822 — "Mon, 17 Mar 2025 12:00:00 +0000"  (standard RSS pubDate)
    try:
        dt = parsedate_to_datetime(s)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    # ISO 8601 with timezone offset — "2025-03-17T12:00:00+00:00"
    try:
        m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", s)
        if m:
            return f"{m.group(1)}T{m.group(2)}Z"
    except Exception:
        pass

    return ""


# ── CRUD ──────────────────────────────────────────────────────────────────────

def upsert_article(title: str, url: str, source: str, author: str = "",
                   summary: str = "", image_url: str = "", published: str = "",
                   category: str = "general") -> bool:
    """Insert article if URL is new. Normalises the published date. Returns True if inserted."""
    pub_iso = normalize_date(published)
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO articles
                (title, url, source, author, summary, image_url, published, fetched_at, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, url, source, author, summary, image_url, pub_iso,
              datetime.utcnow().isoformat(), category))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


# NJ geography terms used to filter out non-NJ articles
_NJ_TERMS_SQL = """
    (
        source LIKE '%New Jersey%' OR source LIKE '%NJ%'    OR source LIKE '%Jersey%'
     OR source LIKE '%Newark%'     OR source LIKE '%njcannabis%'
     OR title  LIKE '%New Jersey%' OR title  LIKE '%NJ cannabis%'
     OR title  LIKE '%NJ marijuana%'
     OR title  LIKE '% NJ %'       OR title  LIKE 'NJ %'     OR title  LIKE '%(NJ)%'
     OR title  LIKE '%Newark%'     OR title  LIKE '%Trenton%'
     OR title  LIKE '%Jersey City%' OR title LIKE '%Hoboken%'
     OR title  LIKE '%Atlantic City%' OR title LIKE '%NJCRC%'
     OR title  LIKE '%Garden State%'
    )
""".strip()


def get_articles(saved_only: bool = False, source: Optional[str] = None,
                 category: Optional[str] = None, search: Optional[str] = None,
                 days_back: int = 90, limit: int = 2000) -> List[dict]:
    """
    Fetch articles with optional filters.
    - days_back : exclude unsaved articles older than this many days (0 = no limit)
    - NJ tab    : additional geography keyword filter to exclude non-NJ articles
    - Sort      : published DESC (normalised ISO-8601), then fetched_at DESC
    """
    conn = get_connection()
    query  = "SELECT * FROM articles WHERE 1=1"
    params: list = []

    if days_back:
        query += " AND (fetched_at >= datetime('now', ?) OR is_saved = 1)"
        params.append(f"-{days_back} days")

    if saved_only:
        query += " AND is_saved = 1"

    if source:
        query += " AND source = ?"
        params.append(source)

    if category:
        query += " AND category = ?"
        params.append(category)
        # Extra filter: NJ tab must contain NJ geography in source or title
        if category == "nj":
            query += f" AND {_NJ_TERMS_SQL}"

    if search:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY published DESC, fetched_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_saved(article_id: int) -> bool:
    conn = get_connection()
    conn.execute("UPDATE articles SET is_saved = 1 - is_saved WHERE id = ?", (article_id,))
    conn.commit()
    row = conn.execute("SELECT is_saved FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return bool(row["is_saved"]) if row else False


def mark_read(article_id: int):
    conn = get_connection()
    conn.execute("UPDATE articles SET is_read = 1 WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()


def get_sources() -> List[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_article_count() -> dict:
    conn = get_connection()
    total  = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    saved  = conn.execute("SELECT COUNT(*) FROM articles WHERE is_saved = 1").fetchone()[0]
    unread = conn.execute("SELECT COUNT(*) FROM articles WHERE is_read = 0").fetchone()[0]
    conn.close()
    return {"total": total, "saved": saved, "unread": unread}


def delete_old_articles(days: int = 90):
    """Purge unsaved articles older than N days."""
    conn = get_connection()
    conn.execute("""
        DELETE FROM articles
        WHERE is_saved = 0
          AND fetched_at < datetime('now', ?)
    """, (f"-{days} days",))
    conn.commit()
    conn.close()
