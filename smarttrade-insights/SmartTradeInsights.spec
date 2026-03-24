# -*- mode: python ; coding: utf-8 -*-
# SmartTrade Insights - PyInstaller Build Spec
# Usage:  pyinstaller SmartTradeInsights.spec
#
# Produces a single-directory build in dist/SmartTradeInsights/
# Run build_windows.bat for the full build + zip workflow.

import sys
from pathlib import Path

block_cipher = None

# ── Hidden imports ─────────────────────────────────────────────────────────────
# PyQt6 and pyqtgraph need several sub-modules that PyInstaller may miss.
hidden = [
    # PyQt6
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
    "PyQt6.sip",
    # pyqtgraph
    "pyqtgraph",
    "pyqtgraph.graphicsItems",
    "pyqtgraph.widgets",
    "pyqtgraph.opengl",
    # Data
    "yfinance",
    "yfinance.base",
    "yfinance.ticker",
    "pandas",
    "pandas._libs.tslibs.timedeltas",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.skiplist",
    "numpy",
    # Networking
    "requests",
    "urllib3",
    "charset_normalizer",
    "certifi",
    # DB
    "sqlite3",
    # Keyring backends
    "keyring",
    "keyring.backends.Windows",
    "keyring.backends.fail",
    # Plyer (optional)
    "plyer",
    "plyer.platforms.win.notification",
    # App modules
    "app",
    "app.config",
    "app.database.db_manager",
    "app.data.data_manager",
    "app.data.yfinance_provider",
    "app.data.alphavantage_provider",
    "app.analysis.indicators",
    "app.analysis.signals",
    "app.analysis.profit_estimator",
    "app.simulation.engine",
    "app.ui.main_window",
    "app.ui.dashboard",
    "app.ui.stock_card",
    "app.ui.chart_widget",
    "app.ui.config_screen",
    "app.ui.simulation_screen",
    "app.ui.styles",
    "app.utils.crypto",
    "app.utils.alerts",
]

a = Analysis(
    ["main.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "IPython",
        "jupyter",
        "notebook",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SmartTradeInsights",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window (windowed app)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="resources/icon.ico",   # Uncomment when icon is available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SmartTradeInsights",
)
