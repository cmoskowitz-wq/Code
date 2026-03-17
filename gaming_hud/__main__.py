"""Entry point for the Gaming HUD overlay application.

Supports system tray icon with show/hide toggle and clean exit.
Usage:
    python -m gaming_hud
"""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter, QPainterPath, QFont
from PyQt5.QtWidgets import (
    QAction, QApplication, QMenu, QSystemTrayIcon,
)

from gaming_hud import __app_name__, __version__
from gaming_hud.app import HUDOverlay


def _create_tray_icon_pixmap() -> QPixmap:
    """Generate a simple tray icon programmatically (no external files)."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    # Rounded background
    path = QPainterPath()
    path.addRoundedRect(2, 2, 60, 60, 12, 12)
    p.fillPath(path, QColor("#0d1117"))
    p.setPen(QColor("#00d4ff"))
    p.drawRoundedRect(2, 2, 60, 60, 12, 12)

    # "HUD" text
    p.setPen(QColor("#00d4ff"))
    font = QFont("Segoe UI", 15, QFont.Bold)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "HUD")

    p.end()
    return pm


def main():
    # High-DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Create overlay
    overlay = HUDOverlay()

    # System tray
    tray_icon = QIcon(_create_tray_icon_pixmap())
    tray = QSystemTrayIcon(tray_icon, parent=app)
    tray.setToolTip(f"{__app_name__} v{__version__}")

    menu = QMenu()
    menu.setStyleSheet("""
        QMenu {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 4px;
        }
        QMenu::item {
            color: #e6edf3;
            padding: 6px 24px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
        }
        QMenu::item:selected {
            background-color: #1c2333;
            color: #00d4ff;
        }
        QMenu::separator {
            height: 1px;
            background: #30363d;
            margin: 4px 8px;
        }
    """)

    toggle_action = QAction("Hide HUD", menu)

    def _toggle_hud():
        if overlay.isVisible():
            overlay.hide()
            toggle_action.setText("Show HUD")
        else:
            overlay.show()
            toggle_action.setText("Hide HUD")

    toggle_action.triggered.connect(_toggle_hud)
    menu.addAction(toggle_action)
    menu.addSeparator()

    about_action = QAction(f"v{__version__}", menu)
    about_action.setEnabled(False)
    menu.addAction(about_action)

    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: _toggle_hud()
        if reason == QSystemTrayIcon.DoubleClick
        else None
    )
    tray.show()

    # Show overlay
    overlay.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
