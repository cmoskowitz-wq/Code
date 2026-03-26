# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Mosko Meter

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='MoskoMeter',
)

app = BUNDLE(
    coll,
    name='MoskoMeter.app',
    icon=None,
    bundle_identifier='com.mosko.moskometer',
    info_plist={
        'CFBundleName': 'Mosko Meter',
        'CFBundleDisplayName': 'Mosko Meter',
        'CFBundleIdentifier': 'com.mosko.moskometer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleExecutable': 'MoskoMeter',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
    },
)
