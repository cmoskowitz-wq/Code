# -*- mode: python ; coding: utf-8 -*-
# mosko.spec — PyInstaller spec file for Mosko Photo Labs
#
# Build with: pyinstaller mosko.spec
#

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

hidden_imports = [
    "piexif", "piexif._utils", "piexif.helper",
    "exifread", "exifread.utils", "exifread.tags",
    "PIL", "PIL.Image", "PIL.ExifTags",
    "PIL.JpegImagePlugin", "PIL.TiffImagePlugin", "PIL.PngImagePlugin",
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSvg",
]

sep = ";" if sys.platform == "win32" else ":"

datas = []
assets_dir = ROOT / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "assets"))

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MoskoPhotoLabs",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # Windowless app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icons" / "app_icon.ico") if sys.platform == "win32"
         else str(ROOT / "assets" / "icons" / "app_icon.icns"),
)

# macOS .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="MoskoPhotoLabs.app",
        icon=str(ROOT / "assets" / "icons" / "app_icon.icns"),
        bundle_identifier="com.moskophotolabs.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "NSCameraUsageDescription": "Mosko Photo Labs reads image files.",
        },
    )
