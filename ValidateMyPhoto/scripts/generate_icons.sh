#!/bin/bash
# Generates all required macOS app icon sizes from a single 1024×1024 source PNG.
# Place your master icon at: scripts/AppIcon-1024.png
# Run: ./scripts/generate_icons.sh
#
# Requires: Inkscape or ImageMagick (brew install imagemagick)

set -euo pipefail

SOURCE="scripts/AppIcon-1024.png"
ICONSET_DIR="ValidateMyPhoto/Resources/Assets.xcassets/AppIcon.appiconset"

if [ ! -f "$SOURCE" ]; then
    echo "⚠️  Source icon not found at $SOURCE"
    echo "   Please provide a 1024×1024 PNG of your app icon."
    echo ""
    echo "   Icon design guidelines:"
    echo "   • Use a camera viewfinder or lens motif with teal/blue gradient"
    echo "   • macOS icon style: subtle shadow, rounded square clipping done by macOS"
    echo "   • Reference: https://developer.apple.com/design/human-interface-guidelines/app-icons"
    exit 1
fi

which convert > /dev/null || (echo "❌ ImageMagick not found. Run: brew install imagemagick" && exit 1)

echo "→ Generating icon sizes from $SOURCE..."

declare -A sizes=(
    ["icon_16x16.png"]="16"
    ["icon_16x16@2x.png"]="32"
    ["icon_32x32.png"]="32"
    ["icon_32x32@2x.png"]="64"
    ["icon_128x128.png"]="128"
    ["icon_128x128@2x.png"]="256"
    ["icon_256x256.png"]="256"
    ["icon_256x256@2x.png"]="512"
    ["icon_512x512.png"]="512"
    ["icon_512x512@2x.png"]="1024"
)

for filename in "${!sizes[@]}"; do
    size="${sizes[$filename]}"
    convert "$SOURCE" -resize "${size}x${size}" "$ICONSET_DIR/$filename"
    echo "  ✓ ${filename} (${size}px)"
done

echo "✅ All icon sizes generated in $ICONSET_DIR"

# Update Contents.json with actual filenames
python3 - <<'PYTHON'
import json, os

iconset = "ValidateMyPhoto/Resources/Assets.xcassets/AppIcon.appiconset"
sizes = [
    ("16x16",   "1x",  "icon_16x16.png"),
    ("16x16",   "2x",  "icon_16x16@2x.png"),
    ("32x32",   "1x",  "icon_32x32.png"),
    ("32x32",   "2x",  "icon_32x32@2x.png"),
    ("128x128", "1x",  "icon_128x128.png"),
    ("128x128", "2x",  "icon_128x128@2x.png"),
    ("256x256", "1x",  "icon_256x256.png"),
    ("256x256", "2x",  "icon_256x256@2x.png"),
    ("512x512", "1x",  "icon_512x512.png"),
    ("512x512", "2x",  "icon_512x512@2x.png"),
]

contents = {
    "images": [{"filename": fn, "idiom": "mac", "scale": scale, "size": size}
               for size, scale, fn in sizes],
    "info": {"author": "xcode", "version": 1}
}

with open(f"{iconset}/Contents.json", "w") as f:
    json.dump(contents, f, indent=2)
print("✅ Contents.json updated.")
PYTHON
