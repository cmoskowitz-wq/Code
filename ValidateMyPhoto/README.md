# Validate My Photo
**by Mosko Photo Labs**

> Know if your photo is real — instantly and intelligently.

A native macOS application that analyzes digital images using multi-layer forensic analysis to determine whether they are authentic photographs or AI-generated / AI-manipulated content.

---

## Features

- **5-layer forensic analysis**: Metadata · Pixel Forensics · Frequency Domain (FFT) · Lighting Consistency · AI Pattern Detection
- **Error Level Analysis (ELA)**: Industry-standard manipulation detection technique
- **Batch processing**: Analyze up to 12 images simultaneously
- **Confidence intervals**: Probabilistic scoring with uncertainty bounds
- **Explainable results**: Every score comes with human-readable findings
- **PDF & CSV export**: Professional reports for documentation
- **100% local processing**: No network access, no data leaves your Mac
- **Universal Binary**: Native on both Apple Silicon (M-series) and Intel Macs
- **Dark / Light mode**: Full support with glassmorphism UI

---

## Supported Formats

| Format | Extension |
|--------|-----------|
| JPEG   | .jpg, .jpeg |
| PNG    | .png |
| HEIC   | .heic |
| TIFF   | .tiff, .tif |
| Canon RAW | .cr2, .cr3 |
| Nikon RAW | .nef |
| Sony RAW  | .arw |
| Adobe DNG | .dng |

**Limits**: Max 12 images per session · Max 100 MB per image

---

## Detection Methods

### 1. Metadata Analysis (25% weight)
Parses EXIF/IPTC/TIFF metadata to check for:
- Camera make/model and lens identification
- Exposure data completeness (ISO, aperture, shutter, focal length)
- Timestamp integrity
- AI software signatures (`stable diffusion`, `midjourney`, `dall-e`, etc.)
- Editing software traces
- GPS data presence

### 2. Pixel Forensics (28% weight)
Statistical analysis of raw pixel data:
- Local noise variance estimation (real sensors produce spatially random noise)
- Color channel statistics and histogram analysis
- Edge coherence and gradient analysis
- **Error Level Analysis (ELA)** — detects manipulation hotspots by recompressing at known quality
- Texture uniformity across image patches

### 3. Frequency Domain Analysis (20% weight)
FFT-based spectral analysis via Apple's Accelerate framework:
- Spectral slope analysis (natural images follow ~1/f distribution)
- High/low frequency energy ratio
- Periodic artifact detection (GAN checkerboard, upsampling patterns)

### 4. Lighting Consistency (12% weight)
Scene analysis using Vision framework:
- Luminance distribution across quadrants
- Facial lighting direction consistency (multi-face comparison)
- Shadow/highlight tonal balance
- Luminance gradient coherence

### 5. AI Pattern Detection (15% weight)
Heuristic detection of known generative AI signatures:
- Over-smoothing detection (diffusion model hallmark)
- Texture tiling/repetition (latent space upsampling)
- Color signature anomalies (Midjourney/SD saturation profiles)
- Diffusion model halo artifacts around edges
- Deep mode: GAN checkerboard artifact scan
- Face landmark anatomy validation (eye symmetry, mouth proportions)

---

## Getting Started

### Prerequisites
- macOS 13.0+ (Ventura or later)
- Xcode 15+ (for building from source)
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)

### Build from Source

```bash
# 1. Clone and set up
git clone <repo-url>
cd ValidateMyPhoto
make setup

# 2. Open in Xcode
open ValidateMyPhoto.xcodeproj

# 3. Build and run (⌘R in Xcode)
```

### Create .pkg Installer

```bash
# Build unsigned .pkg (for internal testing)
make pkg

# Build signed + notarized .pkg (for customer distribution)
export DEVELOPER_ID_APP="Developer ID Application: Mosko Photo Labs (TEAMID)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: Mosko Photo Labs (TEAMID)"
export NOTARIZE_APPLE_ID="developer@moskophotolabs.com"
export NOTARIZE_TEAM_ID="ABCDE12345"
export NOTARIZE_PASSWORD="@keychain:AC_PASSWORD"
make notarize
```

The final installer will be at `build/ValidateMyPhoto-1.0.0-installer.pkg`.

### Generate App Icon

Place a 1024×1024 PNG at `scripts/AppIcon-1024.png`, then:
```bash
./scripts/generate_icons.sh
```

---

## Project Structure

```
ValidateMyPhoto/
├── ValidateMyPhoto/
│   ├── App/
│   │   └── ValidateMyPhotoApp.swift      # @main entry point
│   ├── Models/
│   │   ├── AnalysisResult.swift          # Data models, scoring types
│   │   ├── ImageItem.swift               # Per-image state & UTType support
│   │   └── AppState.swift                # Central ViewModel (ObservableObject)
│   ├── Analyzers/
│   │   ├── AnalysisEngine.swift          # Orchestrator (concurrent analysis)
│   │   ├── MetadataAnalyzer.swift        # EXIF/IPTC analysis (ImageIO)
│   │   ├── PixelForensicsAnalyzer.swift  # Pixel stats + ELA (CoreImage)
│   │   ├── FrequencyAnalyzer.swift       # FFT analysis (Accelerate/vDSP)
│   │   ├── LightingAnalyzer.swift        # Lighting + face analysis (Vision)
│   │   └── AIPatternDetector.swift       # Heuristics + Core ML placeholder
│   ├── Views/
│   │   ├── ContentView.swift             # Root navigation + toolbar
│   │   ├── HomeView.swift                # Drag & drop landing
│   │   ├── AnalysisGridView.swift        # 12-tile grid
│   │   ├── ImageTileView.swift           # Individual tile with score overlay
│   │   ├── DetailView.swift              # Per-image detail + insights
│   │   ├── ReportView.swift              # Batch summary + export
│   │   ├── SettingsView.swift            # App settings
│   │   └── Components/
│   │       ├── ScoreBadge.swift          # Circular score ring
│   │       └── CircularProgress.swift    # Analysis progress indicator
│   ├── Export/
│   │   ├── PDFExporter.swift             # PDF report generation (CoreGraphics)
│   │   └── CSVExporter.swift             # CSV export
│   └── Resources/
│       ├── Info.plist
│       ├── ValidateMyPhoto.entitlements
│       └── Assets.xcassets/
├── scripts/
│   ├── package.sh                        # Creates .pkg with pkgbuild/productbuild
│   ├── notarize.sh                       # Apple notarization + stapling
│   ├── generate_icons.sh                 # Batch icon size generation
│   ├── Distribution.xml                  # Installer distribution spec
│   └── installer-resources/             # Welcome/license HTML for installer
├── project.yml                          # XcodeGen project spec
└── Makefile                             # Build automation
```

---

## Integrating a Real Core ML Model

The `AIPatternDetector.swift` is architected to accept a trained Core ML model. The current implementation uses validated heuristic signals while the model slot is open for integration.

**Recommended approach:**
1. Convert a HuggingFace model (e.g., `organicphotons/ai-detector`, `Ojimi/anime-kawai-diffusion`) using `coremltools`
2. Add the `.mlpackage` to the Xcode project under `ValidateMyPhoto/Models/`
3. Replace the `heuristicAnalysis` call in `analyze()` with a Core ML inference call

```swift
// In AIPatternDetector.swift, replace heuristicAnalysis with:
private func coreMLAnalysis(cgImage: CGImage) async -> AnalyzerResult {
    guard let model = try? YourModel(configuration: MLModelConfiguration()) else {
        return AnalyzerResult(score: 50, insights: ["ML model unavailable."], confidence: 0.3)
    }
    // ... perform inference
}
```

---

## Distribution Checklist

Before shipping to customers:

- [ ] Set Apple Developer Team ID in `scripts/ExportOptions.plist`
- [ ] Set `DEVELOPER_ID_APP` and `DEVELOPER_ID_INSTALLER` in environment
- [ ] Create app-specific password at appleid.apple.com → store as `AC_PASSWORD` in Keychain
- [ ] Run `make notarize` to produce a notarized, stapled .pkg
- [ ] Test installer on a clean macOS 13 VM
- [ ] Verify Gatekeeper allows launch: `spctl --assess --type exec build/ValidateMyPhoto.app`
- [ ] Generate and include app icon (`scripts/AppIcon-1024.png` → `generate_icons.sh`)
- [ ] Update version in `project.yml` (MARKETING_VERSION) and `Makefile`

---

## Privacy

- All image analysis is performed **locally on the user's Mac**
- No images, metadata, or results are ever transmitted
- No analytics, crash reporting, or telemetry
- App Sandbox enabled — only accesses user-selected files

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| macOS | 13.0+ (Ventura) |
| Architecture | Universal (arm64 + x86_64) |
| Swift | 5.9+ |
| Xcode | 15.0+ |
| Frameworks | Core ML, Vision, Accelerate, ImageIO, CoreImage |

---

## License

Copyright © 2025 Mosko Photo Labs. All rights reserved.
