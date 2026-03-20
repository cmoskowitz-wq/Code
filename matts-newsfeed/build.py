"""
build.py — Build Matt's Newsfeed into a standalone app.

  Windows  →  dist/MattsNewsfeed.exe
  macOS    →  dist/MattsNewsfeed.app  (drag-to-Applications bundle)
  Linux    →  dist/MattsNewsfeed

Run from anywhere:
    python build.py

macOS prerequisites
-------------------
Do NOT use the system Python (/usr/bin/python3) — it ships without Tk.
Install Python from python.org (≥3.10) or via Homebrew:
    brew install python-tk@3.12
Then install deps into that interpreter:
    pip3 install -r requirements.txt pyinstaller
"""

import os
import sys

import PyInstaller.__main__

HERE = os.path.dirname(os.path.abspath(__file__))
PLATFORM = sys.platform          # "darwin", "win32", "linux"
APP_NAME = "MattsNewsfeed"

# ── Platform-specific settings ────────────────────────────────────────────────

if PLATFORM == "darwin":
    output_desc = f"dist/{APP_NAME}.app"
    extra_args = [
        # Bundle Tcl/Tk properly on macOS (avoids blank-window issues)
        "--collect-all", "tkinter",
        # Build a universal binary that runs natively on both Intel and
        # Apple Silicon Macs.  Remove this line if your Python is not a
        # universal2 build (python.org installers are; Homebrew's are not).
        "--target-arch", "universal2",
    ]
elif PLATFORM == "win32":
    output_desc = f"dist\\{APP_NAME}.exe"
    extra_args = []
else:   # Linux
    output_desc = f"dist/{APP_NAME}"
    extra_args = []

# ── PyInstaller invocation ────────────────────────────────────────────────────

args = [
    os.path.join(HERE, "app.py"),
    "--name",     APP_NAME,
    "--onefile",            # single executable / single .app bundle
    "--windowed",           # no terminal window on launch
    "--noconfirm",
    "--clean",

    # Hidden imports that PyInstaller's static analysis can miss
    "--hidden-import", "customtkinter",
    "--hidden-import", "requests",
    "--hidden-import", "bs4",
    "--hidden-import", "PIL",
    "--hidden-import", "xml.etree.ElementTree",
    "--hidden-import", "email.utils",

    # Bundle customtkinter themes / assets
    "--collect-data", "customtkinter",

    # Trim the binary of unused test machinery
    "--exclude-module", "pytest",
    "--exclude-module", "unittest",

    "--distpath", os.path.join(HERE, "dist"),
    "--workpath", os.path.join(HERE, "build"),
    "--specpath", HERE,
]

args.extend(extra_args)

print(f"=== Building for platform: {PLATFORM} ===")
PyInstaller.__main__.run(args)

print("\n=== Build complete! ===")
print(f"Output: {os.path.join(HERE, output_desc)}")

if PLATFORM == "darwin":
    print("\nTo distribute:")
    print("  1. Drag MattsNewsfeed.app from the dist/ folder to /Applications")
    print("  2. On first launch macOS may show a Gatekeeper warning —")
    print("     right-click the .app and choose Open to bypass it.")
    print("  3. For wider distribution, sign & notarize with:")
    print("     codesign --deep --sign 'Developer ID Application: <Your Name>' dist/MattsNewsfeed.app")
