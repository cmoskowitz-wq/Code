import Foundation
import ImageIO

// MARK: - Metadata Analyzer
// Parses EXIF/IPTC/TIFF metadata to assess authenticity.
// AI-generated images typically lack camera metadata or contain
// software identifiers from generative pipelines.

actor MetadataAnalyzer {

    // Known generative AI software signatures in EXIF Software field
    private let aiSoftwarePatterns: [String] = [
        "stable diffusion", "midjourney", "dall-e", "dall·e",
        "adobe firefly", "generative fill", "nightcafe",
        "dream", "artbreeder", "runway", "pika", "kling",
        "leonardo", "ideogram", "flux", "imagen"
    ]

    // Editing software that doesn't indicate AI generation but is worth noting
    private let editingSoftwarePatterns: [String] = [
        "photoshop", "lightroom", "capture one", "affinity photo",
        "darktable", "rawtherapee", "gimp"
    ]

    func analyze(imageSource: CGImageSource) async -> AnalyzerResult {
        var score = 50.0   // neutral baseline
        var insights: [String] = []
        var confidence = 0.7

        guard let props = CGImageSourceCopyPropertiesAtIndex(imageSource, 0, nil) as? [String: Any] else {
            return AnalyzerResult(
                score: 20,
                insights: ["No image metadata found — typical of AI-generated images."],
                confidence: 0.6
            )
        }

        let exif = props[kCGImagePropertyExifDictionary as String] as? [String: Any]
        let tiff = props[kCGImagePropertyTIFFDictionary as String] as? [String: Any]
        let gps  = props[kCGImagePropertyGPSDictionary  as String] as? [String: Any]
        let iptc = props[kCGImagePropertyIPTCDictionary as String] as? [String: Any]

        // --- Camera Make/Model ---
        let make  = tiff?[kCGImagePropertyTIFFMake  as String] as? String
        let model = tiff?[kCGImagePropertyTIFFModel as String] as? String

        if let make = make, let model = model, !make.isEmpty, !model.isEmpty {
            score += 18
            confidence = min(confidence + 0.1, 1.0)
            insights.append("Camera identified: \(make) \(model).")
        } else if make != nil || model != nil {
            score += 8
            insights.append("Partial camera information found.")
        } else {
            score -= 15
            insights.append("No camera make/model — missing in most authentic photos.")
        }

        // --- Lens Info ---
        let lensMake  = exif?[kCGImagePropertyExifLensMake  as String] as? String
        let lensModel = exif?[kCGImagePropertyExifLensModel as String] as? String
        if let lm = lensModel, !lm.isEmpty {
            score += 8
            insights.append("Lens identified: \((lensMake ?? "")) \(lm).")
        } else if make != nil {
            // Real cameras usually record lens data
            score -= 5
            insights.append("Camera found but lens metadata absent.")
        }

        // --- Timestamp Integrity ---
        let dateTimeOrig = exif?[kCGImagePropertyExifDateTimeOriginal as String] as? String
        let dateTimeDig  = exif?[kCGImagePropertyExifDateTimeDigitized as String] as? String
        if let orig = dateTimeOrig, !orig.isEmpty {
            score += 8
            if let dig = dateTimeDig, !dig.isEmpty {
                if orig == dig {
                    score += 4
                } else {
                    // Original capture ≠ digitization — possible re-processing
                    insights.append("Timestamp discrepancy: capture and digitization times differ.")
                }
            }
        } else {
            score -= 8
            insights.append("No capture timestamp found.")
        }

        // --- Exposure Data (ISO / Aperture / Shutter) ---
        let iso      = exif?[kCGImagePropertyExifISOSpeedRatings as String]
        let fNumber  = exif?[kCGImagePropertyExifFNumber as String] as? Double
        let expTime  = exif?[kCGImagePropertyExifExposureTime as String] as? Double
        let focalLen = exif?[kCGImagePropertyExifFocalLength as String] as? Double

        var exposureFieldCount = 0
        if iso != nil      { exposureFieldCount += 1 }
        if fNumber != nil  { exposureFieldCount += 1 }
        if expTime != nil  { exposureFieldCount += 1 }
        if focalLen != nil { exposureFieldCount += 1 }

        if exposureFieldCount >= 3 {
            score += 10
            insights.append("Complete exposure data present (ISO, aperture, shutter, focal length).")
        } else if exposureFieldCount >= 1 {
            score += 4
        } else {
            score -= 8
            insights.append("No exposure data (ISO/aperture/shutter) — unusual for authentic photos.")
        }

        // --- Software Signature ---
        let software = (tiff?[kCGImagePropertyTIFFSoftware as String] as? String ?? "").lowercased()
        let xmpData  = props["ProfileName"] as? String ?? ""  // rough XMP check

        if !software.isEmpty {
            let isAI = aiSoftwarePatterns.contains { software.contains($0) }
            let isEditor = editingSoftwarePatterns.contains { software.contains($0) }

            if isAI {
                score -= 40
                confidence = min(confidence + 0.2, 1.0)
                insights.append("AI generative software signature detected in metadata: \"\(software)\".")
            } else if isEditor {
                score -= 5
                insights.append("Image processed with editing software: \(formatSoftwareName(software)).")
            } else if software.contains("camera") || software.contains("firmware") {
                score += 8
                insights.append("Camera firmware software field indicates in-camera JPEG processing.")
            }
        } else {
            // No software field can mean stripped metadata (possible tampering)
            insights.append("Software field absent — metadata may have been stripped.")
        }

        // --- GPS Data ---
        if gps != nil {
            score += 5
            insights.append("GPS location data present — consistent with authentic photograph.")
        }

        // --- IPTC/Copyright ---
        if let copyright = iptc?[kCGImagePropertyIPTCCopyrightNotice as String] as? String,
           !copyright.isEmpty {
            score += 3
            insights.append("Copyright notice found: \"\(copyright)\".")
        }

        // --- Color Profile ---
        if let colorProfile = props[kCGImagePropertyColorModel as String] as? String {
            insights.append("Color space: \(colorProfile).")
        }

        // Clamp and return
        return AnalyzerResult(
            score: min(max(score, 0), 100),
            insights: insights.isEmpty ? ["Metadata analysis completed with no significant findings."] : insights,
            confidence: confidence
        )
    }

    private func formatSoftwareName(_ raw: String) -> String {
        let names = ["photoshop": "Adobe Photoshop",
                     "lightroom": "Adobe Lightroom",
                     "capture one": "Capture One",
                     "affinity": "Affinity Photo",
                     "gimp": "GIMP"]
        return names.first { raw.contains($0.key) }?.value ?? raw.capitalized
    }
}
