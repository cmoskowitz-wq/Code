# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'pyqtgraph',
    'psutil',
    '_struct',
    '_psutil_osx',
    'typing',
    'sip',
    'numpy',
]
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pyqtgraph')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# One-dir mode: binaries/datas are collected separately so the .app bundle
# has a proper directory structure instead of a self-extracting single binary.
# Self-extracting single binaries are blocked by macOS Gatekeeper on modern systems.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MoskoMeter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MoskoMeter',
)

app = BUNDLE(
    coll,
    name='MoskoMeter.app',
    icon=None,
    bundle_identifier='com.mosko.moskometer',
    info_plist={
        'CFBundleName': 'MoskoMeter',
        'CFBundleDisplayName': 'Mosko Meter',
        'CFBundleShortVersionString': '7.0.0',
        'CFBundleVersion': '7.0.0',
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSRequiresAquaSystemAppearance': False,
    },
)
