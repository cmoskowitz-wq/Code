#!/bin/bash
# Notarizes the .pkg installer with Apple's notarization service.
# Required for distribution outside the Mac App Store (Gatekeeper).
#
# Prerequisites:
#   - Valid Apple Developer ID account
#   - App-specific password stored in Keychain as "AC_PASSWORD"
#     Create at: https://appleid.apple.com → Security → App-Specific Passwords
#
# Usage:
#   NOTARIZE_APPLE_ID="you@example.com" \
#   NOTARIZE_TEAM_ID="ABCDE12345" \
#   NOTARIZE_PASSWORD="@keychain:AC_PASSWORD" \
#   ./notarize.sh build/ValidateMyPhoto-installer.pkg

set -euo pipefail

PKG_PATH="${1:-}"
APPLE_ID="${NOTARIZE_APPLE_ID:-$2}"
TEAM_ID="${NOTARIZE_TEAM_ID:-$3}"
PASSWORD="${NOTARIZE_PASSWORD:-$4}"

if [ -z "$PKG_PATH" ] || [ -z "$APPLE_ID" ] || [ -z "$TEAM_ID" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: NOTARIZE_APPLE_ID=... NOTARIZE_TEAM_ID=... NOTARIZE_PASSWORD=... $0 <pkg_path>"
    exit 1
fi

echo "→ Submitting for notarization: $PKG_PATH"
echo "   Apple ID : $APPLE_ID"
echo "   Team ID  : $TEAM_ID"

# Submit
SUBMISSION_OUTPUT=$(xcrun notarytool submit "$PKG_PATH" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$PASSWORD" \
    --wait \
    --output-format json)

STATUS=$(echo "$SUBMISSION_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))")

if [ "$STATUS" = "Accepted" ]; then
    echo "✅ Notarization accepted!"
    echo "→ Stapling ticket to package..."
    xcrun stapler staple "$PKG_PATH"
    echo "✅ Stapled. Package is ready for distribution."
else
    echo "❌ Notarization failed with status: $STATUS"
    echo "$SUBMISSION_OUTPUT"
    exit 1
fi
