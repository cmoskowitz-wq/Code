# Validate My Photo — Build System
# Usage:
#   make setup      — Install tools and generate Xcode project
#   make build      — Build release binary
#   make app        — Create .app bundle
#   make pkg        — Create .pkg installer
#   make notarize   — Notarize the .app (requires Apple Developer credentials)
#   make clean      — Clean build artifacts

PRODUCT_NAME    = ValidateMyPhoto
BUNDLE_ID       = com.moskophotolabs.ValidateMyPhoto
VERSION         = 1.0.0
BUILD_NUM       = 1
MIN_MACOS       = 13.0

XCODE_SCHEME    = $(PRODUCT_NAME)
ARCHIVE_PATH    = build/$(PRODUCT_NAME).xcarchive
APP_PATH        = build/$(PRODUCT_NAME).app
PKG_PATH        = build/$(PRODUCT_NAME)-$(VERSION).pkg
DIST_PKG_PATH   = build/$(PRODUCT_NAME)-$(VERSION)-installer.pkg

# Developer credentials (set via environment or .env file)
DEVELOPER_ID_APP       ?= "Developer ID Application: Mosko Photo Labs"
DEVELOPER_ID_INSTALLER ?= "Developer ID Installer: Mosko Photo Labs"
NOTARIZE_APPLE_ID      ?=
NOTARIZE_TEAM_ID       ?=
NOTARIZE_PASSWORD      ?=  # Use keychain: @keychain:AC_PASSWORD

.PHONY: all setup generate build app pkg clean notarize staple

all: pkg

# ─── Setup ───────────────────────────────────────────────────────────────────

setup:
	@echo "→ Checking for Homebrew..."
	@which brew > /dev/null || (echo "❌ Homebrew not found. Install from https://brew.sh" && exit 1)
	@echo "→ Installing XcodeGen..."
	@brew list xcodegen &>/dev/null || brew install xcodegen
	@echo "→ Generating Xcode project..."
	@$(MAKE) generate
	@echo "✅ Setup complete. Open $(PRODUCT_NAME).xcodeproj in Xcode."

generate:
	xcodegen generate

# ─── Build ───────────────────────────────────────────────────────────────────

build: generate
	@mkdir -p build
	xcodebuild \
		-scheme "$(XCODE_SCHEME)" \
		-configuration Release \
		-archivePath "$(ARCHIVE_PATH)" \
		archive \
		CODE_SIGN_STYLE=Automatic \
		DEVELOPMENT_TEAM="" \
		| xcpretty || true

app: build
	@echo "→ Exporting .app from archive..."
	@mkdir -p build
	xcodebuild \
		-exportArchive \
		-archivePath "$(ARCHIVE_PATH)" \
		-exportPath build/ \
		-exportOptionsPlist scripts/ExportOptions.plist
	@echo "✅ App exported to $(APP_PATH)"

# ─── Package ─────────────────────────────────────────────────────────────────

pkg: app
	@bash scripts/package.sh \
		"$(APP_PATH)" \
		"$(PKG_PATH)" \
		"$(DIST_PKG_PATH)" \
		"$(VERSION)" \
		"$(BUILD_NUM)"

# ─── Notarization ────────────────────────────────────────────────────────────

notarize: pkg
	@bash scripts/notarize.sh \
		"$(DIST_PKG_PATH)" \
		"$(NOTARIZE_APPLE_ID)" \
		"$(NOTARIZE_TEAM_ID)" \
		"$(NOTARIZE_PASSWORD)"

staple:
	xcrun stapler staple "$(DIST_PKG_PATH)"

# ─── Clean ───────────────────────────────────────────────────────────────────

clean:
	@rm -rf build/
	@rm -rf $(PRODUCT_NAME).xcodeproj/
	@echo "✅ Cleaned."
