#!/usr/bin/env python3
"""
threatscope.py — ThreatScope V4.5
Cyber-threat dashboard: CVEs, CISA KEV flags, security news, and exploit feeds.

Usage:
    python threatscope.py

Requirements:
    pip install PyQt6 PyQt6-WebEngine requests feedparser
"""

from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
from PyQt6.QtCore import QThread, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("threatscope")

# ── Constants ─────────────────────────────────────────────────────────────────

NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EXPLOIT_RSS_URL = "https://www.exploit-db.com/rss.xml"

RSS_FEEDS: list[str] = [
    "https://thehackernews.com/feeds/posts/default",
    "https://feeds.darkreading.com/darkreading/enterprise",
    "https://feeds.feedburner.com/bleepingcomputer",
    "https://www.sophos.com/en-us/rss-feed",
    "https://www.securityweek.com/rss.xml",
    "https://www.csoonline.com/index.rss",
    "https://www.securitymagazine.com/rss",
    "https://sec.cloudapps.cisco.com/security/center/rss.x?i=44",
]

HTTP_TIMEOUT: int = 10           # seconds — RSS / CISA KEV requests
NVD_TIMEOUT: int = 30           # seconds — NVD is often slow; give it more time
AUTO_REFRESH_MS: int = 10 * 60 * 1000   # 10 minutes in milliseconds
NVD_RESULTS_PER_PAGE: int = 2000        # NVD hard-caps at 2000
NEWS_ENTRIES_PER_FEED: int = 8          # max articles pulled per RSS feed
EXPLOIT_ENTRIES_MAX: int = 12           # max exploit entries to show
SUMMARY_PREVIEW_LEN: int = 150         # chars to preview in list descriptions
CVE_LOOKBACK_DAYS: int = 30            # how far back to fetch CVEs

CACHE_DIR: Path = Path.home() / ".threatscope"
CACHE_PATH: Path = CACHE_DIR / "cve_cache.json"
CACHE_MAX_AGE_HOURS: int = 1           # treat cache as stale after this long

APP_STYLESHEET = """
    QWidget { background-color: #0D1117; color: #C9D1D9; font-family: Segoe UI; }
    QTableWidget { background-color: #161B22; alternate-background-color: #0D1117; }
    QListWidget { background-color: #161B22; }
    QPushButton { background-color: #58A6FF; color: #0D1117; padding: 5px; border-radius: 6px; }
    QPushButton:hover { background-color: #1F6FEB; }
    QPushButton:disabled { background-color: #444C56; color: #8B949E; }
    QTabBar::tab { height: 35px; width: 180px; font-size: 14pt; }
    QTabBar::tab:selected { background: #58A6FF; color: #0D1117; font-weight: bold; border-radius: 6px; }
    QTabBar::tab:!selected { background: #161B22; color: #C9D1D9; border-radius: 6px; }
"""

# ── Shared helpers ────────────────────────────────────────────────────────────


def parse_rss_date(date_str: str) -> datetime:
    """Parse an RFC-2822-style RSS date string; returns datetime.min on failure.

    Always returns a naive (timezone-stripped) datetime so mixed feeds
    containing both aware and naive entries can be sorted together.
    """
    if not date_str:
        return datetime.min
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str[:31].strip(), fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    logger.debug("Unparseable date string: %r", date_str)
    return datetime.min


def get_cvss_score(metrics: dict[str, Any]) -> float:
    """Extract the best available CVSS base score, trying v3.1 → v3.0 → v2.0."""
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        try:
            return float(metrics[key][0]["cvssData"]["baseScore"])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return 0.0


def extract_products(configurations: list[dict]) -> str:
    """Parse CPE URIs from NVD configuration nodes into a product name string."""
    products: set[str] = set()
    for config in configurations:
        for node in config.get("nodes", []):
            for match in node.get("cpeMatch", []):
                uri = match.get("criteria", "")
                parts = uri.split(":")
                # CPE 2.3 format: cpe:2.3:a:<vendor>:<product>:...
                if len(parts) > 4 and parts[4] not in ("*", "-", ""):
                    products.add(parts[4])
    return ", ".join(sorted(products)) or "Unknown"


# ── Disk cache ────────────────────────────────────────────────────────────────


def _load_cve_cache() -> list[dict] | None:
    """Return cached CVE list if it exists and is younger than CACHE_MAX_AGE_HOURS."""
    try:
        if not CACHE_PATH.exists():
            return None
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(payload["cached_at"])
        if datetime.now() - cached_at > timedelta(hours=CACHE_MAX_AGE_HOURS):
            logger.debug("CVE cache is stale — will refresh.")
            return None
        logger.info("CVE cache hit (%d entries, age < %dh).", len(payload["cves"]), CACHE_MAX_AGE_HOURS)
        return payload["cves"]
    except Exception as exc:
        logger.warning("CVE cache load failed: %s", exc)
        return None


def _save_cve_cache(cves: list[dict]) -> None:
    """Persist the CVE list to disk for fast startup on next launch."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps({"cached_at": datetime.now().isoformat(), "cves": cves},
                       default=str),
            encoding="utf-8",
        )
        logger.debug("CVE cache saved (%d entries).", len(cves))
    except Exception as exc:
        logger.warning("CVE cache save failed: %s", exc)


# ── Worker threads ────────────────────────────────────────────────────────────


class CVEWorker(QThread):
    """Fetches CVE data from NVD and cross-references CISA KEV in a background thread.

    Emits `cache_ready` immediately when a warm disk cache is available so the
    UI can populate instantly, then emits `data_ready` once the live fetch
    completes.  CISA KEV and NVD are fetched in parallel to halve wait time.
    """

    cache_ready = pyqtSignal(list)   # fired instantly from disk cache (may not fire)
    data_ready = pyqtSignal(list)    # fired when live network fetch is complete
    error = pyqtSignal(str)

    def run(self) -> None:
        # ── 1. Serve cached data immediately so the table isn't blank ──────────
        cached = _load_cve_cache()
        if cached:
            self.cache_ready.emit(cached)

        # ── 2. Fetch CISA KEV and NVD in parallel ─────────────────────────────
        with ThreadPoolExecutor(max_workers=2) as pool:
            kev_future: Future[set[str]] = pool.submit(self._fetch_kev)
            nvd_future: Future[list[dict] | None] = pool.submit(self._fetch_nvd_raw)
            kev_set = kev_future.result()
            raw_vulns = nvd_future.result()

        if raw_vulns is None:
            return  # error already emitted inside _fetch_nvd_raw

        # ── 3. Process, sort, cache, emit ─────────────────────────────────────
        cves = [self._process_vuln(v, kev_set) for v in raw_vulns]
        cves.sort(key=lambda x: x.get("date", ""), reverse=True)
        _save_cve_cache(cves)
        self.data_ready.emit(cves)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_kev(self) -> set[str]:
        try:
            r = requests.get(CISA_KEV_URL, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            return {entry.get("cveID") for entry in r.json().get("vulnerabilities", [])}
        except Exception as exc:
            logger.warning("CISA KEV fetch failed: %s", exc)
            return set()

    def _fetch_nvd_raw(self) -> list[dict] | None:
        now_utc = datetime.now(timezone.utc)
        start = (now_utc - timedelta(days=CVE_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end = now_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        url = (
            f"{NVD_BASE_URL}"
            f"?pubStartDate={start}&pubEndDate={end}"
            f"&resultsPerPage={NVD_RESULTS_PER_PAGE}"
        )
        try:
            r = requests.get(url, timeout=NVD_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.error("NVD CVE fetch failed: %s", exc)
            self.error.emit(f"CVE fetch failed: {exc}")
            return None

        total = data.get("totalResults", 0)
        if total > NVD_RESULTS_PER_PAGE:
            logger.warning(
                "NVD reports %d total CVEs but only %d were fetched (API cap).",
                total, NVD_RESULTS_PER_PAGE,
            )
        return data.get("vulnerabilities", [])

    @staticmethod
    def _process_vuln(vuln: dict, kev_set: set[str]) -> dict:
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "Unknown")
        desc_list = cve.get("descriptions", [])
        desc = desc_list[0].get("value", "") if desc_list else ""
        return {
            "cve": cve_id,
            "products": extract_products(cve.get("configurations", [])),
            "date": cve.get("published", ""),
            "score": get_cvss_score(cve.get("metrics", {})),
            "exploited": cve_id in kev_set,
            "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            "desc": desc,
        }


class NewsWorker(QThread):
    """Fetches and merges articles from all configured RSS news feeds."""

    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self) -> None:
        items: list[dict] = []
        for feed_url in RSS_FEEDS:
            try:
                parsed = feedparser.parse(feed_url)
                source = parsed.feed.get("title", feed_url)
                for entry in parsed.entries[:NEWS_ENTRIES_PER_FEED]:
                    pub = entry.get("published", "") or entry.get("updated", "")
                    items.append(
                        {
                            "title": entry.get("title", ""),
                            "desc": entry.get("summary", "")[:SUMMARY_PREVIEW_LEN],
                            "url": entry.get("link", ""),
                            "source": source,
                            "date": pub,
                        }
                    )
            except Exception as exc:
                logger.warning("RSS feed failed (%s): %s", feed_url, exc)

        items.sort(key=lambda x: parse_rss_date(x["date"]), reverse=True)
        self.data_ready.emit(items)


class ExploitWorker(QThread):
    """Fetches recent exploit disclosures from Exploit-DB RSS."""

    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self) -> None:
        items: list[dict] = []
        try:
            parsed = feedparser.parse(EXPLOIT_RSS_URL)
            for entry in parsed.entries[:EXPLOIT_ENTRIES_MAX]:
                pub = entry.get("published", "") or entry.get("updated", "")
                items.append(
                    {
                        "title": entry.get("title", ""),
                        "desc": entry.get("summary", "")[:SUMMARY_PREVIEW_LEN],
                        "url": entry.get("link", ""),
                        "date": pub,
                    }
                )
        except Exception as exc:
            logger.error("Exploit-DB RSS fetch failed: %s", exc)
            self.error.emit(f"Exploit fetch failed: {exc}")

        items.sort(key=lambda x: parse_rss_date(x["date"]), reverse=True)
        self.data_ready.emit(items)


# ── Main UI ───────────────────────────────────────────────────────────────────


class ThreatApp(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.cve_data: list[dict] = []
        self.exploit_data: list[dict] = []
        self._loading: set[str] = set()

        # Worker references (prevent garbage collection mid-run)
        self._cve_worker: CVEWorker | None = None
        self._news_worker: NewsWorker | None = None
        self._exploit_worker: ExploitWorker | None = None

        self._build_window()
        self._build_ui()
        self._start_auto_refresh()
        self.refresh_all()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        self.setWindowTitle("ThreatScope V4.5")
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.resize(min(1600, geo.width()), min(950, geo.height()))
            self.move(geo.center() - self.rect().center())
        else:
            self.resize(1600, 950)
        self.setStyleSheet(APP_STYLESHEET)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.addLayout(self._build_title_bar())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_news_tab(), "📰 News")
        self.tabs.addTab(self._build_cve_tab(), "🛠 CVEs")
        self.tabs.addTab(self._build_exploit_tab(), "💀 Exploits / Zero-Day")
        root.addWidget(self.tabs)

        self.status = QLabel("Initialising…")
        root.addWidget(self.status)
        self.setLayout(root)

    def _build_title_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        title = QLabel("🛡 ThreatScope V4.5 — News, CVEs & Exploits")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(title)
        help_btn = QPushButton("Help / About")
        help_btn.clicked.connect(self._show_about)
        layout.addWidget(help_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return layout

    def _build_news_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self._news_btn = QPushButton("Refresh News")
        self._news_btn.clicked.connect(self._load_news)
        btn_row.addWidget(self._news_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(btn_row)

        split = QHBoxLayout()
        self.news_list = QListWidget()
        self.news_list.itemClicked.connect(self._open_news_article)
        self.news_browser = QWebEngineView()
        split.addWidget(self.news_list, 4)
        split.addWidget(self.news_browser, 6)
        layout.addLayout(split)

        tab.setLayout(layout)
        return tab

    def _build_cve_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self._cve_btn = QPushButton("Refresh CVEs")
        self._cve_btn.clicked.connect(self._load_cves)
        btn_row.addWidget(self._cve_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(btn_row)

        self.cve_table = QTableWidget()
        self.cve_table.setColumnCount(3)
        self.cve_table.setHorizontalHeaderLabels(
            ["CVE · Score · Flags", "Affected Products", "Published"]
        )
        self.cve_table.setAlternatingRowColors(True)
        self.cve_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cve_table.setSortingEnabled(True)
        self.cve_table.verticalHeader().setVisible(False)
        self.cve_table.cellClicked.connect(self._show_cve_detail)

        # Column sizing: CVE col and date col hug their content; products stretches
        header = self.cve_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.cve_detail = QWebEngineView()

        split = QHBoxLayout()
        split.addWidget(self.cve_table, 4)
        split.addWidget(self.cve_detail, 6)
        layout.addLayout(split)

        tab.setLayout(layout)
        return tab

    def _build_exploit_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self._exploit_btn = QPushButton("Refresh Exploits")
        self._exploit_btn.clicked.connect(self._load_exploits)
        btn_row.addWidget(self._exploit_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(btn_row)

        split = QHBoxLayout()
        self.exploit_list = QListWidget()
        self.exploit_list.itemClicked.connect(self._open_exploit_article)
        self.exploit_browser = QWebEngineView()
        split.addWidget(self.exploit_list, 4)
        split.addWidget(self.exploit_browser, 6)
        layout.addLayout(split)

        tab.setLayout(layout)
        return tab

    # ── Auto-refresh ──────────────────────────────────────────────────────────

    def _start_auto_refresh(self) -> None:
        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh_all)
        self._timer.start(AUTO_REFRESH_MS)

    def refresh_all(self) -> None:
        self._load_news()
        self._load_cves()
        self._load_exploits()

    # ── Loaders ───────────────────────────────────────────────────────────────

    def _load_news(self) -> None:
        if self._news_worker and self._news_worker.isRunning():
            logger.debug("News worker already running — skipping.")
            return
        self._set_loading("news", True)
        self._news_worker = NewsWorker()
        self._news_worker.data_ready.connect(self._populate_news)
        self._news_worker.error.connect(lambda msg: self._on_error("News", msg))
        self._news_worker.finished.connect(self._news_worker.deleteLater)
        self._news_worker.finished.connect(lambda: self._set_loading("news", False))
        self._news_worker.start()

    def _load_cves(self) -> None:
        if self._cve_worker and self._cve_worker.isRunning():
            logger.debug("CVE worker already running — skipping.")
            return
        self._set_loading("cves", True)
        self._cve_worker = CVEWorker()
        self._cve_worker.cache_ready.connect(self._populate_cves)   # instant, from disk
        self._cve_worker.data_ready.connect(self._populate_cves)    # fresh, from network
        self._cve_worker.error.connect(lambda msg: self._on_error("CVE", msg))
        self._cve_worker.finished.connect(self._cve_worker.deleteLater)
        self._cve_worker.finished.connect(lambda: self._set_loading("cves", False))
        self._cve_worker.start()

    def _load_exploits(self) -> None:
        if self._exploit_worker and self._exploit_worker.isRunning():
            logger.debug("Exploit worker already running — skipping.")
            return
        self._set_loading("exploits", True)
        self._exploit_worker = ExploitWorker()
        self._exploit_worker.data_ready.connect(self._populate_exploits)
        self._exploit_worker.error.connect(lambda msg: self._on_error("Exploit", msg))
        self._exploit_worker.finished.connect(self._exploit_worker.deleteLater)
        self._exploit_worker.finished.connect(
            lambda: self._set_loading("exploits", False)
        )
        self._exploit_worker.start()

    # ── Loading state management ──────────────────────────────────────────────

    def _set_loading(self, key: str, loading: bool) -> None:
        """Track which feeds are in-flight and update button + status bar."""
        if loading:
            self._loading.add(key)
        else:
            self._loading.discard(key)

        busy = bool(self._loading)
        self._news_btn.setDisabled(busy)
        self._cve_btn.setDisabled(busy)
        self._exploit_btn.setDisabled(busy)

        if self._loading:
            label = ", ".join(sorted(self._loading))
            self.status.setText(f"Loading {label}…")
        else:
            self.status.setText("All feeds up to date.")

    # ── Populate handlers ─────────────────────────────────────────────────────

    def _populate_news(self, news: list[dict]) -> None:
        self.news_list.clear()
        for item in news:
            lw = QListWidgetItem(f"{item['date']} | {item['title']}")
            lw.setData(Qt.ItemDataRole.UserRole, item["url"])
            lw.setToolTip(item.get("desc", ""))
            self.news_list.addItem(lw)
        logger.info("%d news items loaded.", len(news))

    def _populate_cves(self, cves: list[dict]) -> None:
        self.cve_data = cves
        non_editable = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

        # Suspend repaints for the entire bulk-insert to avoid per-row flicker
        self.cve_table.setSortingEnabled(False)
        self.cve_table.setUpdatesEnabled(False)
        try:
            self.cve_table.setRowCount(len(cves))
            for row, cve in enumerate(cves):
                score = cve["score"]
                flag = ""
                if score >= 9.0:
                    flag = "  🔴 CRITICAL"
                elif score >= 7.0:
                    flag = "  🟠 HIGH"
                if cve["exploited"]:
                    flag += "  ⚠️ KEV"

                # Col 0 — CVE ID · score · severity flags (left, compact)
                cve_item = QTableWidgetItem(f"{cve['cve']}  ({score:.1f}){flag}")
                cve_item.setToolTip(cve["desc"])
                cve_item.setFlags(non_editable)

                # Col 1 — Affected products (stretches to fill)
                products_item = QTableWidgetItem(cve["products"])
                products_item.setFlags(non_editable)

                # Col 2 — Published date (right, compact)
                date_str = cve["date"][:10]   # keep only YYYY-MM-DD
                date_item = QTableWidgetItem(date_str)
                date_item.setFlags(non_editable)

                self.cve_table.setItem(row, 0, cve_item)
                self.cve_table.setItem(row, 1, products_item)
                self.cve_table.setItem(row, 2, date_item)
        finally:
            self.cve_table.setUpdatesEnabled(True)
            self.cve_table.setSortingEnabled(True)

        logger.info("%d CVEs populated.", len(cves))

    def _populate_exploits(self, items: list[dict]) -> None:
        self.exploit_list.clear()
        self.exploit_data = items
        for item in items:
            lw = QListWidgetItem(f"{item['date']} | {item['title']}")
            lw.setData(Qt.ItemDataRole.UserRole, item["url"])
            lw.setToolTip(item.get("desc", ""))
            self.exploit_list.addItem(lw)
        logger.info("%d exploits loaded.", len(items))

    # ── Click handlers ────────────────────────────────────────────────────────

    def _open_news_article(self, item: QListWidgetItem) -> None:
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.news_browser.setUrl(QUrl(url))

    def _show_cve_detail(self, row: int, _column: int) -> None:
        if 0 <= row < len(self.cve_data):
            self.cve_detail.setUrl(QUrl(self.cve_data[row]["url"]))

    def _open_exploit_article(self, item: QListWidgetItem) -> None:
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.exploit_browser.setUrl(QUrl(url))

    # ── Error handling ────────────────────────────────────────────────────────

    def _on_error(self, source: str, message: str) -> None:
        logger.error("[%s] %s", source, message)
        self.status.setText(f"Error ({source}): {message}")

    # ── About dialog ──────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About ThreatScope V4.5",
            "ThreatScope V4.5\n\n"
            "All Rights Reserved © 2026 Christopher Moskowitz\n"
            "Email: cmoskowitz@gmail.com\n\n"
            "Modern threat-intelligence dashboard.\n"
            "Data sources: NVD · CISA KEV · Exploit-DB · security RSS feeds.",
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThreatApp()
    window.show()
    sys.exit(app.exec())
