"""
build.py — Build Matt's Newsfeed into a standalone .exe
Run: python build.py
"""

import PyInstaller.__main__
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(HERE, "app.py"),
    "--name", "MattsNewsfeed",
    "--onefile",
    "--windowed",
    "--noconfirm",
    "--clean",
    # Hidden imports needed at runtime
    "--hidden-import", "customtkinter",
    "--hidden-import", "requests",
    "--hidden-import", "bs4",
    "--hidden-import", "PIL",
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
print(f"Executable: {os.path.join(HERE, 'dist', 'MattsNewsfeed.exe')}")
