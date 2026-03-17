#!/usr/bin/env python3
"""
build_exe.py — Mosko Photo Labs
Build script: generates a standalone Windows .exe (or macOS .app) using PyInstaller.

Usage:
    python build_exe.py              # build one-file exe
    python build_exe.py --onedir     # build one-directory bundle (faster startup)
    python build_exe.py --debug      # include console window for debugging
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"

# ── Configuration ──────────────────────────────────────────────────────────

APP_NAME        = "MoskoPhotoLabs"
ENTRY_POINT     = str(ROOT / "main.py")
ICON_PATH       = str(ROOT / "assets" / "icons" / "app_icon.ico")  # Windows
ICON_MACOS_PATH = str(ROOT / "assets" / "icons" / "app_icon.icns")  # macOS

# Hidden imports that PyInstaller misses
HIDDEN_IMPORTS = [
    "piexif",
    "piexif._utils",
    "piexif.helper",
    "exifread",
    "exifread.utils",
    "exifread.tags",
    "PIL",
    "PIL.Image",
    "PIL.ExifTags",
    "PIL.JpegImagePlugin",
    "PIL.TiffImagePlugin",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
]

# Data files to bundle (src_glob, dest_folder)
DATA_FILES = [
    (str(ROOT / "assets"), "assets"),
]


def build(onedir: bool = False, debug: bool = False):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--name", APP_NAME,
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
    ]

    if onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    if not debug:
        cmd.append("--windowed")   # No console window
    else:
        cmd.append("--console")

    # Icon
    icon = ICON_PATH if sys.platform == "win32" else ICON_MACOS_PATH
    if Path(icon).exists():
        cmd += ["--icon", icon]

    # Hidden imports
    for hi in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", hi]

    # Data files
    sep = ";" if sys.platform == "win32" else ":"
    for src, dest in DATA_FILES:
        if Path(src).exists():
            cmd += ["--add-data", f"{src}{sep}{dest}"]

    # Entry point
    cmd.append(ENTRY_POINT)

    print("=" * 60)
    print("Building Mosko Photo Labs…")
    print(f"  Output: {'one-dir' if onedir else 'one-file'}")
    print(f"  Debug:  {debug}")
    print("=" * 60)
    print()

    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print()
        print("=" * 60)
        if onedir:
            print(f"✓  Bundle written to: {DIST / APP_NAME}")
        else:
            exe_ext = ".exe" if sys.platform == "win32" else ""
            print(f"✓  Executable: {DIST / (APP_NAME + exe_ext)}")
        print("=" * 60)
    else:
        print()
        print("✗  Build failed. Check output above for errors.")
        sys.exit(1)


if __name__ == "__main__":
    _onedir = "--onedir" in sys.argv
    _debug  = "--debug"  in sys.argv
    build(onedir=_onedir, debug=_debug)
