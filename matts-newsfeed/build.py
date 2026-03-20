"""
build.py — Build Chris's Cannabis Counter into a standalone .exe
Run: python build.py
"""

import PyInstaller.__main__
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(HERE, "app.py"),
    "--name", "ChrisCannabisCounter",
    "--onefile",
    "--windowed",
    "--noconfirm",
    "--clean",
    # Hidden imports needed at runtime
    "--hidden-import", "customtkinter",
    "--hidden-import", "requests",
    "--hidden-import", "bs4",
    "--hidden-import", "PIL",
    "--hidden-import", "PIL.ImageTk",
    "--hidden-import", "PIL.ImageDraw",
    "--hidden-import", "logo",
    # Collect customtkinter data files (themes, etc.)
    "--collect-data", "customtkinter",
    # Exclude modules not needed by this app
    "--exclude-module", "pytest",
    "--exclude-module", "unittest",
    # Work/dist dirs
    "--distpath", os.path.join(HERE, "dist"),
    "--workpath", os.path.join(HERE, "build"),
    "--specpath", HERE,
])

print("\n=== Build complete! ===")
print(f"Executable: {os.path.join(HERE, 'dist', 'ChrisCannabisCounter.exe')}")
