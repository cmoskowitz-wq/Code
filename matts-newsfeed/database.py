"""
database.py — Matt's Newsfeed
Local SQLite database for saving/bookmarking articles and caching feeds.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Optional


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matts_newsfeed.db")

# NJ geography keywords used to filter NJ Cannabis tab
_NJ_KEYWORDS_SQL = (
    "source LIKE '%NJ%' OR source LIKE '%New Jersey%' OR source LIKE '%NJSpotlight%' "
    "OR title LIKE '%New Jersey%' OR title LIKE '%N.J.%' "
    "OR title LIKE '% NJ %' OR title LIKE 'NJ %' OR title LIKE '% NJ,' OR title LIKE '% NJ.' "
    "OR summary LIKE '%New Jersey%' OR summary LIKE '% NJ %'"
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist, then run column migrations."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            author TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            published TEXT DEFAULT '',
            published_parsed TEXT DEFAULT '',
            fetched_at TEXT NOT NULL,
            is_saved INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0,
            category TEXT DEFAULT 'general',
            tab TEXT DEFAULT 'kratom'
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source_type TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_fetched TEXT DEFAULT '',
            tab TEXT DEFAULT 'kratom'
        );

        CREATE INDEX IF NOT EXISTS idx_articles_saved ON articles(is_saved);
        CREATE INDEX IF NOT EXISTS idx_articles_published_parsed ON articles(published_parsed DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
        CREATE INDEX IF NOT EXISTS idx_articles_tab ON articles(tab);
    """)
    conn.commit()

    # Safe migrations for existing DBs (columns added in newer versions)
    _migrate(conn)
    conn.close()


def _migrate(conn: sqlite3.Connection):
    """Add new columns if they don't exist — safe to run on every startup."""
    migrations = [
        "ALTER TABLE articles ADD COLUMN published_parsed TEXT DEFAULT ''",
        "ALTER TABLE articles ADD COLUMN tab TEXT DEFAULT 'kratom'",
        "ALTER TABLE sources ADD COLUMN tab TEXT DEFAULT 'kratom'",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass  # column already exists
    conn.commit()


def purge_old_articles(days: int = 90):
    """Delete unsaved articles older than N days. Called on startup."""
    conn = get_connection()
    conn.execute("""
        DELETE FROM articles
        WHERE is_saved = 0
          AND (
            (published_parsed != '' AND published_parsed < datetime('now', ?))
            OR (published_parsed = '' AND fetched_at < datetime('now', ?))
          )
    """, (f"-{days} days", f"-{days} days"))
    conn.commit()
    conn.close()


def upsert_article(title: str, url: str, source: str, author: str = "",
                   summary: str = "", image_url: str = "", published: str = "",
                   published_parsed: str = "", category: str = "general",
                   tab: str = "kratom") -> bool:
    """Insert or ignore an article. Returns True if new."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO articles
                (title, url, source, author, summary, image_url,
                 published, published_parsed, fetched_at, category, tab)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, url, source, author, summary, image_url,
              published, published_parsed,
              datetime.utcnow().isoformat(), category, tab))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def get_articles(saved_only: bool = False, source: Optional[str] = None,
                 category: Optional[str] = None, search: Optional[str] = None,
                 tab: Optional[str] = None, nj_filter: bool = False,
                 limit: int = 300) -> List[dict]:
    """Fetch articles with optional filters, newest first."""
    conn = get_connection()
    query = "SELECT * FROM articles WHERE 1=1"
    params: list = []

    if saved_only:
        query += " AND is_saved = 1"
    if source:
        query += " AND source = ?"
        params.append(source)
    if category:
        query += " AND category = ?"
        params.append(category)
    if tab:
        query += " AND tab = ?"
        params.append(tab)
    if nj_filter:
        query += f" AND ({_NJ_KEYWORDS_SQL})"
    if search:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    # Sort: newest published first; articles with no parsed date fall to bottom
    query += """
        ORDER BY
            CASE WHEN published_parsed != '' THEN published_parsed ELSE fetched_at END DESC
        LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_saved(article_id: int) -> bool:
    """Toggle the saved/bookmarked state. Returns new state."""
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
    """Return counts for UI stats."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    saved = conn.execute("SELECT COUNT(*) FROM articles WHERE is_saved = 1").fetchone()[0]
    unread = conn.execute("SELECT COUNT(*) FROM articles WHERE is_read = 0").fetchone()[0]
    conn.close()
    return {"total": total, "saved": saved, "unread": unread}


# Keep old name for any lingering references
def delete_old_articles(days: int = 90):
    purge_old_articles(days)
