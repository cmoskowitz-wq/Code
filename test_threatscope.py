"""
test_threatscope.py — Unit tests for ThreatScope helper functions.

Run with:
    pytest test_threatscope.py -v

These tests cover pure logic only (no Qt, no network calls).
Qt and feedparser are mocked at the sys.modules level so the tests run in
environments where those packages are unavailable (e.g., headless CI).
"""

from __future__ import annotations

import sys
import types
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub out PyQt6 and feedparser before importing threatscope so that the
# module-level imports don't fail in headless / minimal environments.
# ---------------------------------------------------------------------------
def _make_pyqt6_stub() -> None:
    """Insert minimal PyQt6 stubs into sys.modules."""
    for name in [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtWebEngineWidgets",
    ]:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    # QtCore needs QThread, QTimer, QUrl, Qt, pyqtSignal
    qtcore = sys.modules["PyQt6.QtCore"]
    for attr in ("QThread", "QTimer", "QUrl", "Qt", "pyqtSignal"):
        setattr(qtcore, attr, MagicMock())

    # QtGui needs QFont
    sys.modules["PyQt6.QtGui"].QFont = MagicMock()

    # QtWidgets needs several widget classes
    qtwidgets = sys.modules["PyQt6.QtWidgets"]
    for attr in (
        "QApplication", "QHBoxLayout", "QLabel", "QListWidget",
        "QListWidgetItem", "QMessageBox", "QPushButton", "QTableWidget",
        "QTableWidgetItem", "QTabWidget", "QVBoxLayout", "QWidget",
    ):
        setattr(qtwidgets, attr, MagicMock())

    # QtWebEngineWidgets needs QWebEngineView
    sys.modules["PyQt6.QtWebEngineWidgets"].QWebEngineView = MagicMock()


def _make_feedparser_stub() -> None:
    if "feedparser" not in sys.modules:
        stub = types.ModuleType("feedparser")
        stub.parse = MagicMock(return_value=MagicMock(entries=[], feed=MagicMock(title="")))
        sys.modules["feedparser"] = stub


_make_pyqt6_stub()
_make_feedparser_stub()

from threatscope import extract_products, get_cvss_score, parse_rss_date  # noqa: E402


# ── parse_rss_date ────────────────────────────────────────────────────────────


class TestParseRssDate:
    def test_standard_rfc2822_with_timezone(self):
        result = parse_rss_date("Mon, 24 Mar 2026 12:00:00 +0000")
        # tzinfo is always stripped so aware and naive dates sort together
        assert result == datetime(2026, 3, 24, 12, 0, 0)
        assert result.tzinfo is None

    def test_standard_rfc2822_without_timezone(self):
        result = parse_rss_date("Mon, 24 Mar 2026 08:30:00")
        assert result == datetime(2026, 3, 24, 8, 30, 0)

    def test_empty_string_returns_min(self):
        assert parse_rss_date("") == datetime.min

    def test_none_like_empty_returns_min(self):
        assert parse_rss_date("") == datetime.min

    def test_garbage_string_returns_min(self):
        assert parse_rss_date("not a date at all!!") == datetime.min

    def test_extra_trailing_chars_are_ignored(self):
        # parse_rss_date only looks at the first 31 chars; extra data is fine
        result = parse_rss_date("Mon, 24 Mar 2026 12:00:00 +0000 (UTC) extra garbage")
        assert result.year == 2026

    def test_sorting_order(self):
        """Verify that parsed dates sort correctly (earlier < later)."""
        dates = [
            "Sun, 22 Mar 2026 10:00:00 +0000",
            "Mon, 23 Mar 2026 10:00:00 +0000",
            "Tue, 24 Mar 2026 10:00:00 +0000",
        ]
        parsed = [parse_rss_date(d) for d in dates]
        assert parsed == sorted(parsed)
        assert parsed[0] < parsed[1] < parsed[2]


# ── get_cvss_score ────────────────────────────────────────────────────────────


class TestGetCvssScore:
    def test_v31_preferred(self):
        metrics = {
            "cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}],
            "cvssMetricV30": [{"cvssData": {"baseScore": 8.0}}],
        }
        assert get_cvss_score(metrics) == 9.8

    def test_falls_back_to_v30(self):
        metrics = {
            "cvssMetricV30": [{"cvssData": {"baseScore": 7.5}}],
        }
        assert get_cvss_score(metrics) == 7.5

    def test_falls_back_to_v2(self):
        metrics = {
            "cvssMetricV2": [{"cvssData": {"baseScore": 6.4}}],
        }
        assert get_cvss_score(metrics) == 6.4

    def test_empty_metrics_returns_zero(self):
        assert get_cvss_score({}) == 0.0

    def test_malformed_entry_falls_back(self):
        metrics = {
            "cvssMetricV31": [{}],  # missing cvssData
            "cvssMetricV30": [{"cvssData": {"baseScore": 5.0}}],
        }
        assert get_cvss_score(metrics) == 5.0

    def test_non_numeric_score_falls_back(self):
        metrics = {
            "cvssMetricV31": [{"cvssData": {"baseScore": "N/A"}}],
            "cvssMetricV30": [{"cvssData": {"baseScore": 4.3}}],
        }
        assert get_cvss_score(metrics) == 4.3

    def test_score_cast_to_float(self):
        metrics = {"cvssMetricV31": [{"cvssData": {"baseScore": 10}}]}
        score = get_cvss_score(metrics)
        assert isinstance(score, float)
        assert score == 10.0


# ── extract_products ──────────────────────────────────────────────────────────


class TestExtractProducts:
    def _make_config(self, *criteria: str) -> list[dict]:
        return [
            {
                "nodes": [
                    {
                        "cpeMatch": [{"criteria": c} for c in criteria]
                    }
                ]
            }
        ]

    def test_standard_cpe_uri(self):
        configs = self._make_config("cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*")
        result = extract_products(configs)
        assert "log4j" in result

    def test_wildcard_ignored(self):
        configs = self._make_config("cpe:2.3:a:vendor:*:1.0:*:*:*:*:*:*:*")
        assert extract_products(configs) == "Unknown"

    def test_dash_placeholder_ignored(self):
        configs = self._make_config("cpe:2.3:a:vendor:-:1.0:*:*:*:*:*:*:*")
        assert extract_products(configs) == "Unknown"

    def test_multiple_products_deduplicated(self):
        configs = self._make_config(
            "cpe:2.3:a:apache:log4j:2.0:*:*:*:*:*:*:*",
            "cpe:2.3:a:apache:log4j:2.14:*:*:*:*:*:*:*",
            "cpe:2.3:a:apache:struts:2.5:*:*:*:*:*:*:*",
        )
        result = extract_products(configs)
        products = [p.strip() for p in result.split(",")]
        assert products.count("log4j") == 1
        assert "struts" in products

    def test_short_cpe_uri_skipped(self):
        configs = self._make_config("cpe:2.3:a:foo")
        assert extract_products(configs) == "Unknown"

    def test_empty_configurations(self):
        assert extract_products([]) == "Unknown"

    def test_multiple_config_nodes(self):
        configs = [
            {"nodes": [{"cpeMatch": [{"criteria": "cpe:2.3:a:v:nginx:1.0:*:*:*:*:*:*:*"}]}]},
            {"nodes": [{"cpeMatch": [{"criteria": "cpe:2.3:a:v:apache:2.4:*:*:*:*:*:*:*"}]}]},
        ]
        result = extract_products(configs)
        assert "nginx" in result
        assert "apache" in result
