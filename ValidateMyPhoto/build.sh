#!/bin/bash
# Validate My Photo — one-shot build + package script
# Run from the ValidateMyPhoto/ directory:  bash build.sh
# Output: build/ValidateMyPhoto-1.0.0.pkg

set -euo pipefail

PRODUCT="ValidateMyPhoto"
VERSION="1.0.0"
BUNDLE_ID="com.moskophotolabs.ValidateMyPhoto"
MIN_MACOS="13.0"
BUILD_DIR="$(pwd)/build"
APP="$BUILD_DIR/$PRODUCT.app"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Validate My Photo — Build Script v$VERSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Check requirements ─────────────────────────────────────────────────────
echo ""
echo "→ Checking requirements..."
if ! command -v swift &>/dev/null; then
    echo "❌ Swift not found. Install Xcode from the Mac App Store."
    exit 1
fi
SWIFT_VER=$(swift --version 2>&1 | head -1)
echo "   Swift: $SWIFT_VER"
echo "   ✓ Requirements met"

# ── 2. Build universal binary ─────────────────────────────────────────────────
echo ""
echo "→ Building release binary (arm64 + x86_64)..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build arm64
swift build -c release --arch arm64 2>&1 | grep -E "error:|warning:|Build complete" || true
# Build x86_64
swift build -c release --arch x86_64 2>&1 | grep -E "error:|warning:|Build complete" || true

ARM_BIN=".build/arm64-apple-macosx/release/$PRODUCT"
X86_BIN=".build/x86_64-apple-macosx/release/$PRODUCT"
UNIVERSAL="$BUILD_DIR/$PRODUCT-universal"

if [ -f "$ARM_BIN" ] && [ -f "$X86_BIN" ]; then
    echo "→ Creating universal binary..."
    lipo -create "$ARM_BIN" "$X86_BIN" -output "$UNIVERSAL"
elif [ -f "$ARM_BIN" ]; then
    echo "   (x86_64 not available — using arm64 only)"
    cp "$ARM_BIN" "$UNIVERSAL"
elif [ -f "$X86_BIN" ]; then
    echo "   (arm64 not available — using x86_64 only)"
    cp "$X86_BIN" "$UNIVERSAL"
else
    echo "❌ Build failed — binary not found."
    echo "   Run: swift build -c release 2>&1 | head -40"
    exit 1
fi
echo "   ✓ Binary built"

# ── 3. Assemble .app bundle ───────────────────────────────────────────────────
echo ""
echo "→ Assembling .app bundle..."
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources"

# Binary
cp "$UNIVERSAL" "$APP/Contents/MacOS/$PRODUCT"
chmod +x "$APP/Contents/MacOS/$PRODUCT"

# Info.plist
cp "$PRODUCT/Resources/Info.plist" "$APP/Contents/Info.plist"

# Compile asset catalog (for app icon)
if command -v xcrun &>/dev/null && [ -d "$PRODUCT/Resources/Assets.xcassets" ]; then
    echo "→ Compiling asset catalog..."
    xcrun actool \
        "$PRODUCT/Resources/Assets.xcassets" \
        --compile "$APP/Contents/Resources" \
        --platform macosx \
        --minimum-deployment-target "$MIN_MACOS" \
        --app-icon AppIcon \
        --output-partial-info-plist "$BUILD_DIR/partial-info.plist" \
        --notices --warnings 2>/dev/null || echo "   (asset catalog skipped — app icon will use default)"
fi

# PkgInfo
printf "APPL????" > "$APP/Contents/PkgInfo"

echo "   ✓ .app bundle assembled"

# ── 4. Ad-hoc code sign (runs on your Mac without a Developer account) ─────────
echo ""
echo "→ Signing app (ad-hoc)..."
codesign \
    --sign - \
    --force \
    --deep \
    --options runtime \
    --entitlements "$PRODUCT/Resources/ValidateMyPhoto.entitlements" \
    "$APP" 2>/dev/null || \
codesign \
    --sign - \
    --force \
    --deep \
    "$APP"
echo "   ✓ Signed"

# ── 5. Quick smoke test ───────────────────────────────────────────────────────
echo ""
echo "→ Verifying bundle..."
codesign --verify --deep "$APP" && echo "   ✓ Signature valid"
spctl --assess --type execute "$APP" 2>/dev/null && echo "   ✓ Gatekeeper: OK" || echo "   ℹ  Gatekeeper: ad-hoc signed (open via right-click → Open on first launch)"

# ── 6. Create .pkg installer ──────────────────────────────────────────────────
echo ""
echo "→ Building .pkg installer..."
COMPONENT_PKG="$BUILD_DIR/$PRODUCT-component.pkg"
FINAL_PKG="$BUILD_DIR/$PRODUCT-$VERSION.pkg"

pkgbuild \
    --component "$APP" \
    --install-location "/Applications" \
    --identifier "$BUNDLE_ID" \
    --version "$VERSION" \
    "$COMPONENT_PKG"

productbuild \
    --package "$COMPONENT_PKG" \
    --identifier "$BUNDLE_ID" \
    --version "$VERSION" \
    "$FINAL_PKG"

rm -f "$COMPONENT_PKG"

echo "   ✓ Package built"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Done!"
echo ""
echo "  .app  →  $APP"
echo "  .pkg  →  $FINAL_PKG"
echo "  Size  →  $(du -sh "$FINAL_PKG" | cut -f1)"
echo ""
echo "  To install: double-click the .pkg"
echo "  Or run now: open \"$APP\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
