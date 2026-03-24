#!/usr/bin/env python3
"""
TradeMe — Build Script
Packages the app into a standalone executable using PyInstaller.

Usage (from the trademe/ directory):
    python build.py

Output:
    dist/TradeMe/TradeMe.exe       ← Windows
    dist/TradeMe/TradeMe           ← macOS / Linux

To distribute: zip the entire  dist/TradeMe/  folder and share it.
Recipients just unzip and run TradeMe.exe — no Python needed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEP  = ";" if sys.platform == "win32" else ":"   # PyInstaller path separator


# ── Helpers ────────────────────────────────────────────────────────────────────

def step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}")


def run(cmd: list[str]) -> None:
    print("  $", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        print(f"\n  ERROR: command failed (exit code {result.returncode})")
        sys.exit(result.returncode)


def pip(*packages: str) -> None:
    run([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *packages])


# ── Build steps ────────────────────────────────────────────────────────────────

def install_build_deps() -> None:
    step(1, 4, "Installing build dependencies…")
    pip("pyinstaller>=6.0", "pyinstaller-hooks-contrib>=2024.0")
    print("  ✓ PyInstaller ready")


def download_nltk_data() -> None:
    """TextBlob uses NLTK under the hood; corpora must be present before bundling."""
    step(2, 4, "Downloading TextBlob / NLTK corpora…")
    try:
        import nltk  # noqa: PLC0415
        for corpus in (
            "punkt",
            "punkt_tab",
            "averaged_perceptron_tagger",
            "averaged_perceptron_tagger_eng",
        ):
            result = nltk.download(corpus, quiet=True)
            mark = "✓" if result else "·"
            print(f"  {mark} {corpus}")
        print("  ✓ Corpora ready")
    except ImportError:
        print("  ERROR: nltk not found — run:  pip install -r requirements.txt")
        sys.exit(1)


def find_nltk_paths() -> list[Path]:
    """Return all existing NLTK data directories so we can bundle them."""
    step(3, 4, "Locating NLTK data directories…")
    import nltk.data  # noqa: PLC0415

    found: list[Path] = []
    for p in nltk.data.path:
        path = Path(p)
        if path.exists():
            found.append(path)
            print(f"  Found: {path}")
    if not found:
        print("  ERROR: No NLTK data directories found.")
        sys.exit(1)
    return found


def run_pyinstaller(nltk_paths: list[Path]) -> Path:
    step(4, 4, "Running PyInstaller…")

    # ── --add-data entries ─────────────────────────────────────────────────
    add_data: list[str] = []

    # Ship config.json alongside the exe (user's watchlist)
    add_data += ["--add-data", f"config.json{SEP}."]

    # Bundle every NLTK data directory found on this machine
    for np in nltk_paths:
        add_data += ["--add-data", f"{np}{SEP}nltk_data"]

    # ── Exclude competing Qt bindings ─────────────────────────────────────
    # PyInstaller aborts if more than one Qt binding is collected.
    # We use PyQt6 exclusively, so strip out PyQt5 and PySide6/2.
    exclude: list[str] = []
    for pkg in ("PyQt5", "PySide2", "PySide6"):
        exclude += ["--exclude-module", pkg]

    # ── Hidden imports ─────────────────────────────────────────────────────
    # These are discovered at runtime via string lookups and PyInstaller
    # won't find them through static analysis alone.
    hidden: list[str] = []
    for imp in (
        # matplotlib Qt backend — PyQt6 only
        "matplotlib.backends.backend_qtagg",
        # PyQt6 internals
        "PyQt6.sip",
        "PyQt6.QtPrintSupport",
        # yfinance deps
        "peewee",
        "multitasking",
        "frozendict",
        "appdirs",
        "curl_cffi",
        "curl_cffi.requests",
        # lxml / html parsing (used by yfinance / pandas read_html)
        "lxml.etree",
        "lxml._elementpath",
        "bs4",
        "html5lib",
        # Babel (pandas locale formatting)
        "babel.numbers",
    ):
        hidden += ["--hidden-import", imp]

    # ── Packages that use heavy dynamic imports — collect everything ────────
    collect_all: list[str] = []
    for pkg in (
        "yfinance",
        "mplfinance",
        "textblob",
        "matplotlib",
        "pandas",
        "numpy",
    ):
        collect_all += ["--collect-all", pkg]

    # ── Assemble the full command ──────────────────────────────────────────
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name",        "TradeMe",
        "--windowed",               # No console window in production
        "--onedir",                 # Folder bundle — fast startup, easy updates
        "--clean",                  # Remove stale cache before building
        "--noconfirm",              # Overwrite dist/ without prompting
        *exclude,
        *collect_all,
        *hidden,
        *add_data,
        "main.py",
    ]

    run(cmd)

    dist = HERE / "dist" / "TradeMe"
    exe  = dist / ("TradeMe.exe" if sys.platform == "win32" else "TradeMe")
    return exe


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 58)
    print("  TradeMe — Build Script")
    print("=" * 58)

    os.chdir(HERE)

    install_build_deps()
    download_nltk_data()
    nltk_paths = find_nltk_paths()
    exe = run_pyinstaller(nltk_paths)

    dist_folder = HERE / "dist" / "TradeMe"
    print()
    print("=" * 58)
    print("  Build complete!")
    print("=" * 58)
    print(f"  Executable : {exe}")
    print(f"  Folder     : {dist_folder}")
    print()
    print("  To share with others:")
    print("    • Zip the entire  dist/TradeMe/  folder")
    print("    • Recipients unzip and run TradeMe.exe")
    print("    • No Python installation required")
    print()
    if sys.platform == "win32":
        print("  Tip: to add an icon, place a  trademe.ico  file here")
        print("  and add  --icon trademe.ico  to the PyInstaller command")
        print("  in this script.")
    print()


if __name__ == "__main__":
    main()
