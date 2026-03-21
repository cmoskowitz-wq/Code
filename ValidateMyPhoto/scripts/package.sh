#!/bin/bash
# Creates a signed .pkg installer from the built .app bundle.
# Usage: ./package.sh <app_path> <component_pkg> <dist_pkg> <version> <build_num>

set -euo pipefail

APP_PATH="${1:-build/ValidateMyPhoto.app}"
COMPONENT_PKG="${2:-build/ValidateMyPhoto.pkg}"
DIST_PKG="${3:-build/ValidateMyPhoto-installer.pkg}"
VERSION="${4:-1.0.0}"
BUILD_NUM="${5:-1}"

PRODUCT_NAME="ValidateMyPhoto"
BUNDLE_ID="com.moskophotolabs.ValidateMyPhoto"
INSTALL_LOCATION="/Applications"

# Optional: sign with Developer ID Installer (set env var or leave empty for unsigned)
DEVELOPER_ID_INSTALLER="${DEVELOPER_ID_INSTALLER:-}"
DEVELOPER_ID_APP="${DEVELOPER_ID_APP:-}"

echo "→ Building .pkg installer v${VERSION} (${BUILD_NUM})"

# Validate app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found at: $APP_PATH"
    exit 1
fi

# Sign the .app if a certificate is provided
if [ -n "$DEVELOPER_ID_APP" ]; then
    echo "→ Signing .app with: $DEVELOPER_ID_APP"
    codesign \
        --sign "$DEVELOPER_ID_APP" \
        --options runtime \
        --entitlements "ValidateMyPhoto/Resources/ValidateMyPhoto.entitlements" \
        --deep \
        --force \
        --timestamp \
        "$APP_PATH"
    echo "✅ App signed."
else
    echo "⚠️  No DEVELOPER_ID_APP set — skipping code signing (unsigned build)."
fi

# Build component package
echo "→ Building component package..."
pkgbuild \
    --component "$APP_PATH" \
    --install-location "$INSTALL_LOCATION" \
    --identifier "$BUNDLE_ID" \
    --version "$VERSION" \
    "$COMPONENT_PKG"

echo "✅ Component package created: $COMPONENT_PKG"

# Build distribution package with welcome/license
echo "→ Building distribution package..."
productbuild \
    --distribution scripts/Distribution.xml \
    --package-path "$(dirname "$COMPONENT_PKG")" \
    --resources scripts/installer-resources/ \
    ${DEVELOPER_ID_INSTALLER:+--sign "$DEVELOPER_ID_INSTALLER"} \
    "$DIST_PKG"

echo "✅ Distribution package created: $DIST_PKG"
echo ""
echo "📦 Installer ready: $DIST_PKG"
echo "   Size: $(du -sh "$DIST_PKG" | cut -f1)"
