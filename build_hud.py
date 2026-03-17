#!/usr/bin/env python3
"""Build script for Gaming HUD — creates a standalone Windows .exe using PyInstaller.

Usage (on Windows):
    python build_hud.py

This will produce:
    dist/GamingHUD.exe   — single-file portable executable
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "MoskowitzGaming"
ENTRY = str(ROOT / "gaming_hud" / "__main__.py")
ICON_PATH = str(ROOT / "gaming_hud" / "icon.ico")


def generate_icon():
    """Create a .ico file programmatically for the EXE."""
    try:
        from PyQt5.QtCore import Qt, QSize
        from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPainterPath
        from PyQt5.QtWidgets import QApplication

        # Need a QApplication for pixmap operations
        app_existed = QApplication.instance() is not None
        if not app_existed:
            _app = QApplication([])

        sizes = [16, 32, 48, 64, 128, 256]
        pixmaps = []
        for size in sizes:
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            margin = max(1, size // 16)
            path = QPainterPath()
            path.addRoundedRect(
                margin, margin, size - 2 * margin, size - 2 * margin,
                size * 0.2, size * 0.2,
            )
            p.fillPath(path, QColor("#0d1117"))
            p.setPen(QColor("#00d4ff"))
            p.drawRoundedRect(
                margin, margin, size - 2 * margin, size - 2 * margin,
                size * 0.2, size * 0.2,
            )
            p.setPen(QColor("#00d4ff"))
            font = QFont("Segoe UI", max(6, size // 5), QFont.Bold)
            p.setFont(font)
            p.drawText(pm.rect(), Qt.AlignCenter, "MG")
            p.end()
            pixmaps.append(pm)

        # Save as ICO via QIcon
        icon = QIcon()
        for pm in pixmaps:
            icon.addPixmap(pm)

        # QIcon doesn't save to .ico directly — save largest as PNG,
        # then use Pillow if available, otherwise skip .ico
        png_path = str(ROOT / "gaming_hud" / "icon.png")
        pixmaps[-1].save(png_path, "PNG")

        try:
            from PIL import Image
            img = Image.open(png_path)
            img.save(
                ICON_PATH, format="ICO",
                sizes=[(s, s) for s in sizes],
            )
            os.remove(png_path)
            print(f"  Icon generated: {ICON_PATH}")
            return True
        except ImportError:
            print("  Pillow not installed — using PNG icon (no .ico)")
            return False

    except Exception as e:
        print(f"  Could not generate icon: {e}")
        return False


def build():
    print("=" * 60)
    print(f"  Building {APP_NAME}")
    print("=" * 60)

    # Clean previous builds
    for d in [DIST, BUILD]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Cleaned {d}")

    # Generate icon
    print("\n[1/3] Generating application icon...")
    has_icon = generate_icon()

    # Build PyInstaller command
    print("\n[2/3] Running PyInstaller...\n")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--clean",
        "--noconfirm",
        # Hidden imports that PyInstaller might miss
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        "--hidden-import", "pynput.keyboard",
        "--hidden-import", "pynput.mouse",
        "--hidden-import", "psutil",
    ]

    if has_icon and os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    cmd.append(ENTRY)

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("\nBuild FAILED.")
        sys.exit(1)

    exe_path = DIST / f"{APP_NAME}.exe"
    if not exe_path.exists():
        # On non-Windows, extension might differ
        candidates = list(DIST.glob(f"{APP_NAME}*"))
        if candidates:
            exe_path = candidates[0]

    print("\n[3/3] Build complete!")
    print(f"\n  Output: {exe_path}")
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  Size:   {size_mb:.1f} MB")
    print(f"\n  To run: {exe_path}")
    print("=" * 60)


if __name__ == "__main__":
    build()
