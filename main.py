#!/usr/bin/env python3
"""
main.py — JobHelp Version 1
Entry point: loads config, runs all scrapers, emails the digest,
and optionally keeps running on a schedule.

Usage:
  python main.py              # run once, then schedule
  python main.py --now        # run immediately and exit
  python main.py --dry-run    # run scrapers, print report, don't send email
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import schedule
import yaml
from dotenv import load_dotenv

from email_sender import build_html_report, send_report
from scrapers import Job, build_scrapers, deduplicate, shutdown_browser

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jobhelp")

# ── Config loader ─────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config() -> dict:
    """Load YAML config and overlay secrets from .env / environment variables."""
    load_dotenv()  # reads .env if present

    with open(CONFIG_PATH, "r") as fh:
        cfg = yaml.safe_load(fh)

    # Override email credentials from environment (takes priority over config.yaml)
    email = cfg.setdefault("email", {})
    if os.getenv("EMAIL_SENDER"):
        email["sender"] = os.environ["EMAIL_SENDER"]
    if os.getenv("EMAIL_PASSWORD"):
        email["password"] = os.environ["EMAIL_PASSWORD"]

    # Override Adzuna keys from environment
    boards = cfg.setdefault("job_boards", {})
    adzuna = boards.setdefault("adzuna", {})
    if os.getenv("ADZUNA_APP_ID"):
        adzuna["app_id"] = os.environ["ADZUNA_APP_ID"]
    if os.getenv("ADZUNA_APP_KEY"):
        adzuna["app_key"] = os.environ["ADZUNA_APP_KEY"]

    return cfg


# ── Core job ──────────────────────────────────────────────────────────────────

def run_job(cfg: dict, dry_run: bool = False) -> List[Job]:  # noqa: F821
    """Run all scrapers, deduplicate, (optionally) email, return job list."""
    job_titles: list[str] = cfg.get("job_titles", [])
    if not job_titles:
        logger.warning("No job titles configured — nothing to search.")
        return []

    scrapers = build_scrapers(cfg)
    if not scrapers:
        logger.warning("No job boards enabled — check config.yaml.")
        return []

    logger.info(
        "Starting JobHelp Version 1 — %d boards × %d titles",
        len(scrapers), len(job_titles),
    )

    all_jobs: list[Job] = []
    for scraper in scrapers:
        logger.info("  Scraping %s ...", scraper.name)
        jobs = scraper.search_all(job_titles)
        logger.info("    → %d results", len(jobs))
        all_jobs.extend(jobs)

    all_jobs = deduplicate(all_jobs)
    logger.info("Total unique jobs after deduplication: %d", len(all_jobs))

    if dry_run:
        _print_dry_run(all_jobs, cfg)
    else:
        send_report(all_jobs, cfg)

    return all_jobs


def _print_dry_run(jobs: list[Job], cfg: dict) -> None:
    """Print a plain-text preview instead of sending the email."""
    print("\n" + "=" * 70)
    print("DRY RUN — email would contain:")
    print("=" * 70)
    from collections import defaultdict
    by_title: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        by_title[job.search_term].append(job)

    for title in cfg.get("job_titles", []):
        title_jobs = by_title.get(title, [])
        print(f"\n{title.upper()} ({len(title_jobs)} results)")
        print("─" * 50)
        for job in title_jobs[:5]:
            posted_str = ""
            if job.posted:
                delta = datetime.now(timezone.utc) - job.posted.replace(
                    tzinfo=timezone.utc) if job.posted.tzinfo is None else job.posted
                hours = int((datetime.now(timezone.utc) - (job.posted if job.posted.tzinfo else job.posted.replace(tzinfo=timezone.utc))).total_seconds() / 3600)
                posted_str = f" [{hours}h ago]"
            print(f"  • {job.title} @ {job.company} ({job.source}){posted_str}")
            if job.url:
                print(f"    {job.url}")
        if len(title_jobs) > 5:
            print(f"  ... and {len(title_jobs) - 5} more")
    print("\n" + "=" * 70 + "\n")


# ── Scheduler ─────────────────────────────────────────────────────────────────

def start_scheduler(cfg: dict) -> None:
    """Block forever, running run_job on the configured schedule."""
    email_cfg = cfg.get("email", {})
    sched = email_cfg.get("schedule", "daily")
    daily_time = email_cfg.get("daily_time", "08:00")

    if sched == "daily":
        logger.info("Scheduling daily digest at %s.", daily_time)
        schedule.every().day.at(daily_time).do(run_job, cfg=cfg)
        # Also run immediately on first start
        run_job(cfg)

    elif sched == "hourly":
        logger.info("Scheduling hourly digest.")
        schedule.every().hour.do(run_job, cfg=cfg)
        run_job(cfg)

    else:
        # Treat as a cron expression approximation:
        # For simplicity parse "HH:MM" or fall back to daily at daily_time
        try:
            h, m = [int(x) for x in sched.split(":")[:2]]
            run_time = f"{h:02d}:{m:02d}"
            logger.info("Scheduling daily digest at %s (custom time).", run_time)
            schedule.every().day.at(run_time).do(run_job, cfg=cfg)
        except (ValueError, AttributeError):
            logger.warning(
                "Unrecognised schedule '%s', defaulting to daily at %s.",
                sched, daily_time,
            )
            schedule.every().day.at(daily_time).do(run_job, cfg=cfg)
        run_job(cfg)

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="JobHelp Version 1 — Tech leadership job digest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Run once then stay scheduled (daemon mode)
  python main.py --now        Scrape and email right now, then exit
  python main.py --dry-run    Scrape and print results, do NOT email
  python main.py --config /path/to/other.yaml   Use a custom config file
""",
    )
    p.add_argument(
        "--now", action="store_true",
        help="Run once immediately and exit (no scheduling).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Scrape but print results instead of emailing.",
    )
    p.add_argument(
        "--config", default=None,
        help="Path to an alternative config YAML file.",
    )
    p.add_argument(
        "--list-boards", action="store_true",
        help="List all supported job boards and exit.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # Allow overriding the config path via CLI
    global CONFIG_PATH
    if args.config:
        CONFIG_PATH = Path(args.config)

    if args.list_boards:
        from scrapers import SCRAPER_REGISTRY
        print("\nSupported job boards:")
        for key, cls in SCRAPER_REGISTRY.items():
            print(f"  {key:<18} → {cls.name}")
        print()
        sys.exit(0)

    try:
        cfg = load_config()
    except FileNotFoundError:
        logger.error("config.yaml not found at %s", CONFIG_PATH)
        sys.exit(1)
    except yaml.YAMLError as exc:
        logger.error("Invalid config.yaml: %s", exc)
        sys.exit(1)

    logger.info("Loaded config: %s", cfg.get("version", "JobHelp Version 1"))

    try:
        if args.now:
            run_job(cfg, dry_run=args.dry_run)
        elif args.dry_run:
            run_job(cfg, dry_run=True)
        else:
            try:
                start_scheduler(cfg)
            except KeyboardInterrupt:
                logger.info("JobHelp stopped by user.")
    finally:
        shutdown_browser()


if __name__ == "__main__":
    main()
