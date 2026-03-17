#!/usr/bin/env python3
"""
main.py — Mosko Photo Labs
Application entry point.
"""

import sys
import os

# Ensure the project root is on the path when running as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.constants import APP_NAME, APP_VERSION
from app.theme import get_stylesheet
from app.ui.main_window import MainWindow


def main():
    # High-DPI support (Windows/Mac)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("MoskoPhotoLabs")

    # Apply the dark theme
    app.setStyleSheet(get_stylesheet())

    window = MainWindow()
    window.show()

    # If a folder is passed as a command-line argument, open it
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        window._browser.load_folder(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
