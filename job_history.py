"""
job_history.py — Track previously seen jobs to avoid emailing duplicates.

Stores a JSON file of (title, company) keys so that across runs,
only new postings are included in the digest email.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parent / "seen_jobs.json"


def load_seen_jobs(path: Path = DEFAULT_PATH) -> set[tuple[str, str]]:
    """Load previously seen job keys from disk."""
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {(t, c) for t, c in data.get("jobs", [])}
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Could not read job history (%s), starting fresh.", exc)
        return set()


def save_seen_jobs(seen: set[tuple[str, str]], path: Path = DEFAULT_PATH) -> None:
    """Persist seen job keys to disk."""
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "jobs": sorted(seen),
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    logger.info("Saved %d seen jobs to %s", len(seen), path.name)


def job_key(title: str, company: str) -> tuple[str, str]:
    """Canonical key for deduplication — matches scrapers.deduplicate logic."""
    return (title.lower().strip(), company.lower().strip())
