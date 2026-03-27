#!/usr/bin/env bash
# build_pkg.sh — Build MoskoMeter.pkg for macOS
#
# Usage:
#   ./build_pkg.sh                  # unsigned build
#   ./build_pkg.sh --sign "Developer ID Application: Your Name (TEAMID)"
#
# Requirements: macOS, Python 3.10+, Xcode Command Line Tools

set -euo pipefail

APP_NAME="MoskoMeter"
PKG_ID="com.mosko.moskometer"
VERSION="7.0.0"
INSTALL_LOCATION="/Applications"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
PKG_STAGE="$BUILD_DIR/pkg_stage"
OUTPUT_PKG="$SCRIPT_DIR/${APP_NAME}-${VERSION}.pkg"
SIGN_IDENTITY=""

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sign)
            SIGN_IDENTITY="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    echo "ERROR: This script must be run on macOS."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    exit 1
fi

PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [[ "$PYTHON_MINOR" -lt 10 ]]; then
    echo "ERROR: Python 3.10+ required (found 3.$PYTHON_MINOR)."
    exit 1
fi

echo "==> Building $APP_NAME v$VERSION"

# ── Virtual environment ───────────────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "==> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
echo "==> Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# ── PyInstaller build ─────────────────────────────────────────────────────────
echo "==> Running PyInstaller..."
rm -rf "$BUILD_DIR" "$DIST_DIR"
pyinstaller "$SCRIPT_DIR/MoskoMeter.spec" \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --noconfirm

APP_BUNDLE="$DIST_DIR/${APP_NAME}.app"

if [[ ! -d "$APP_BUNDLE" ]]; then
    echo "ERROR: PyInstaller did not produce $APP_BUNDLE"
    exit 1
fi

echo "==> App bundle created: $APP_BUNDLE"

# ── Code signing ──────────────────────────────────────────────────────────────
# For one-dir app bundles, sign leaf binaries/frameworks first, then the bundle.
# codesign --deep is deprecated and unreliable for Qt app bundles.
sign_bundle() {
    local identity="$1"
    echo "==> Signing frameworks and dylibs..."
    # Sign all dynamic libraries inside the bundle (deepest first)
    find "$APP_BUNDLE" -name "*.dylib" -o -name "*.so" | sort -r | while read -r lib; do
        codesign --force --sign "$identity" "$lib" 2>/dev/null || true
    done
    # Sign any nested executables
    find "$APP_BUNDLE/Contents/MacOS" -type f ! -name "MoskoMeter" | while read -r bin; do
        codesign --force --sign "$identity" "$bin" 2>/dev/null || true
    done
    echo "==> Signing app bundle..."
    codesign --force --verify --sign "$identity" "$APP_BUNDLE"
}

if [[ -n "$SIGN_IDENTITY" ]]; then
    echo "==> Signing app bundle with: $SIGN_IDENTITY"
    sign_bundle "$SIGN_IDENTITY"
else
    echo "==> Applying ad-hoc signature (no Developer ID)..."
    sign_bundle "-"
fi

# ── Build .pkg with pkgbuild ──────────────────────────────────────────────────
echo "==> Building .pkg installer..."
rm -rf "$PKG_STAGE"
mkdir -p "$PKG_STAGE"

PKG_ARGS=(
    --component "$APP_BUNDLE"
    --install-location "$INSTALL_LOCATION"
    --identifier "$PKG_ID"
    --version "$VERSION"
)

if [[ -n "$SIGN_IDENTITY" ]]; then
    # Derive installer signing identity from app signing identity
    INSTALLER_IDENTITY="${SIGN_IDENTITY/Developer ID Application/Developer ID Installer}"
    PKG_ARGS+=(--sign "$INSTALLER_IDENTITY")
fi

pkgbuild "${PKG_ARGS[@]}" "$OUTPUT_PKG"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "✓ Package ready: $OUTPUT_PKG"
echo ""
echo "Install on any Mac with:"
echo "  sudo installer -pkg $OUTPUT_PKG -target /"
echo "Or double-click the .pkg file in Finder."

if [[ -z "$SIGN_IDENTITY" ]]; then
    echo ""
    echo "NOTE: This build is not signed with a Developer ID."
    echo "Recipients may need to right-click → Open to bypass Gatekeeper,"
    echo "or you can notarize by passing --sign \"Developer ID Application: ...\""
fi
