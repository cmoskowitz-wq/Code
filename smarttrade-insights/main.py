"""
SmartTrade Insights - Application Entry Point
"""
import sys
import os
import logging
from pathlib import Path

# ── Ensure correct working directory when frozen as .exe ─────────────────────
if getattr(sys, "frozen", False):
    # PyInstaller sets sys._MEIPASS to the temp extraction dir
    os.chdir(Path(sys.executable).parent)

# ── Logging setup ─────────────────────────────────────────────────────────────
from app.config import LOG_PATH, APP_NAME, APP_VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)
logger.info("Starting %s v%s", APP_NAME, APP_VERSION)

# ── Qt imports ─────────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap

# ── App modules ────────────────────────────────────────────────────────────────
from app.database.db_manager import DatabaseManager
from app.ui.main_window import MainWindow


def _make_splash() -> QSplashScreen:
    """Create a minimal dark splash screen."""
    px = QPixmap(460, 240)
    px.fill(QColor("#0d1117"))

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Border
    from PyQt6.QtGui import QPen
    painter.setPen(QPen(QColor("#30363d"), 1))
    painter.drawRect(0, 0, 459, 239)

    # Logo text
    painter.setPen(QColor("#58a6ff"))
    painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, APP_NAME)

    # Sub-text
    painter.setPen(QColor("#8b949e"))
    painter.setFont(QFont("Segoe UI", 11))
    from PyQt6.QtCore import QRect
    sub_rect = QRect(0, 145, 460, 40)
    painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, f"v{APP_VERSION}  ·  Initialising…")

    painter.end()

    splash = QSplashScreen(px, Qt.WindowType.WindowStaysOnTopHint)
    return splash


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SmartTrade")
    app.setOrganizationDomain("smarttrade.app")

    # Splash screen
    splash = _make_splash()
    splash.show()
    app.processEvents()

    # Database initialisation
    splash.showMessage(
        "  Initialising database…",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        QColor("#58a6ff"),
    )
    app.processEvents()

    db = DatabaseManager()
    db.initialize()

    splash.showMessage(
        "  Loading UI…",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        QColor("#58a6ff"),
    )
    app.processEvents()

    window = MainWindow(db)

    # Close splash and show main window after a brief delay
    QTimer.singleShot(800, lambda: (splash.finish(window), window.show()))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
