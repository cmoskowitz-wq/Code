import Foundation
import SwiftUI

// MARK: - Authenticity Classification

enum AuthenticityClassification: String, Codable, CaseIterable {
    case likelyAuthentic = "Likely Authentic"
    case uncertain = "Uncertain"
    case likelyAIGenerated = "Likely AI-Generated"

    var icon: String {
        switch self {
        case .likelyAuthentic: return "checkmark.seal.fill"
        case .uncertain: return "exclamationmark.triangle.fill"
        case .likelyAIGenerated: return "xmark.seal.fill"
        }
    }

    var color: Color {
        switch self {
        case .likelyAuthentic: return .authenticGreen
        case .uncertain: return .uncertainYellow
        case .likelyAIGenerated: return .aiRed
        }
    }

    var shortLabel: String {
        switch self {
        case .likelyAuthentic: return "Authentic"
        case .uncertain: return "Uncertain"
        case .likelyAIGenerated: return "AI Generated"
        }
    }
}

// MARK: - Sub-scores

struct SubScore: Codable, Identifiable {
    let id: UUID
    let category: ScoreCategory
    let score: Double          // 0–100
    let weight: Double         // relative weight in composite
    let insights: [String]     // human-readable explanations
    let confidence: Double     // 0–1, how confident the analyzer is

    init(category: ScoreCategory, score: Double, weight: Double,
         insights: [String], confidence: Double = 1.0) {
        self.id = UUID()
        self.category = category
        self.score = min(max(score, 0), 100)
        self.weight = weight
        self.insights = insights
        self.confidence = min(max(confidence, 0), 1)
    }
}

enum ScoreCategory: String, Codable, CaseIterable {
    case metadata = "Metadata Integrity"
    case pixelForensics = "Pixel Forensics"
    case frequencyDomain = "Frequency Analysis"
    case lightingConsistency = "Lighting Consistency"
    case aiPatternMatch = "AI Pattern Match"

    var icon: String {
        switch self {
        case .metadata: return "info.circle.fill"
        case .pixelForensics: return "magnifyingglass.circle.fill"
        case .frequencyDomain: return "waveform"
        case .lightingConsistency: return "sun.max.fill"
        case .aiPatternMatch: return "cpu.fill"
        }
    }

    var description: String {
        switch self {
        case .metadata:
            return "Analysis of EXIF/IPTC metadata including camera info, timestamps, and software signatures."
        case .pixelForensics:
            return "Statistical analysis of noise patterns, compression artifacts, and color channel consistency."
        case .frequencyDomain:
            return "FFT-based spectral analysis to detect unnatural frequency distributions common in AI images."
        case .lightingConsistency:
            return "Validation of light direction, shadow geometry, and reflection coherence across the scene."
        case .aiPatternMatch:
            return "Detection of known artifact patterns from diffusion models, GANs, and other generative systems."
        }
    }
}

// MARK: - Error Level Analysis

struct ELAResult: Codable {
    let suspicionScore: Double   // 0–100, higher = more suspicious
    let hotspotCount: Int
    let maxIntensity: Double
}

// MARK: - Analysis Result

struct AnalysisResult: Codable, Identifiable {
    let id: UUID
    let imageURL: URL
    let imageName: String
    let analyzedAt: Date

    // Composite
    let authenticityScore: Double          // 0–100 (100 = fully authentic)
    let classification: AuthenticityClassification
    let confidenceInterval: ClosedRange<Double>   // e.g. 72...88

    // Sub-scores
    let subScores: [SubScore]

    // All textual findings
    let keyFindings: [String]

    // Optional ELA
    let elaResult: ELAResult?

    // File info
    let fileSize: Int64
    let imageWidth: Int
    let imageHeight: Int
    let fileFormat: String

    // Duration
    let analysisDuration: TimeInterval

    init(
        imageURL: URL,
        imageName: String,
        authenticityScore: Double,
        subScores: [SubScore],
        keyFindings: [String],
        elaResult: ELAResult? = nil,
        fileSize: Int64,
        imageWidth: Int,
        imageHeight: Int,
        fileFormat: String,
        analysisDuration: TimeInterval,
        confidenceInterval: ClosedRange<Double>? = nil
    ) {
        self.id = UUID()
        self.imageURL = imageURL
        self.imageName = imageName
        self.analyzedAt = Date()
        self.authenticityScore = min(max(authenticityScore, 0), 100)
        self.subScores = subScores
        self.keyFindings = keyFindings
        self.elaResult = elaResult
        self.fileSize = fileSize
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.fileFormat = fileFormat
        self.analysisDuration = analysisDuration

        // Derive classification
        if authenticityScore >= 75 {
            self.classification = .likelyAuthentic
        } else if authenticityScore >= 45 {
            self.classification = .uncertain
        } else {
            self.classification = .likelyAIGenerated
        }

        // Derive confidence interval if not provided
        if let ci = confidenceInterval {
            self.confidenceInterval = ci
        } else {
            let margin = 15.0 * (1.0 - (subScores.map(\.confidence).reduce(0, +) / Double(max(subScores.count, 1))))
            let lower = max(0, authenticityScore - margin)
            let upper = min(100, authenticityScore + margin)
            self.confidenceInterval = lower...upper
        }
    }
}

// MARK: - Color Extensions

extension Color {
    static let authenticGreen = Color(red: 0.2, green: 0.78, blue: 0.35)
    static let uncertainYellow = Color(red: 0.98, green: 0.78, blue: 0.18)
    static let aiRed = Color(red: 0.95, green: 0.27, blue: 0.27)
    static let accentTeal = Color(red: 0.0, green: 0.72, blue: 0.87)
    static let cardBackground = Color(white: 0.12)
    static let cardBackgroundLight = Color(white: 0.96)
}
