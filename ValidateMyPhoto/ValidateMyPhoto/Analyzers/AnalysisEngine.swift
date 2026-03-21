import Foundation
import CoreImage
import ImageIO

// MARK: - Analysis Engine

/// Orchestrates all sub-analyzers and produces a composite AnalysisResult.
actor AnalysisEngine {

    private let metadataAnalyzer    = MetadataAnalyzer()
    private let pixelAnalyzer       = PixelForensicsAnalyzer()
    private let frequencyAnalyzer   = FrequencyAnalyzer()
    private let lightingAnalyzer    = LightingAnalyzer()
    private let aiPatternDetector   = AIPatternDetector()

    // Sub-score weights (must sum to 1.0)
    // Metadata is the most reliable signal (no false positives for real cameras).
    // Pixel forensics reduced — ELA and noise variance fire on compressed JPEGs.
    // AI pattern bumped — CoreML classifier anchors this with higher reliability.
    private let weights: [ScoreCategory: Double] = [
        .metadata:            0.28,
        .pixelForensics:      0.22,
        .frequencyDomain:     0.18,
        .lightingConsistency: 0.12,
        .aiPatternMatch:      0.20
    ]

    func analyze(
        item: ImageItem,
        deepMode: Bool,
        progressHandler: @Sendable @escaping (Double) -> Void
    ) async throws -> AnalysisResult {

        let start = Date()
        let url = item.url
        let fileName = item.fileName
        let fileSize = item.fileSize

        guard let imageSource = CGImageSourceCreateWithURL(url as CFURL, nil) else {
            throw AnalysisError.unreadableImage
        }

        // Load full CGImage
        guard let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
            throw AnalysisError.unreadableImage
        }

        let width  = cgImage.width
        let height = cgImage.height
        let format = url.pathExtension.uppercased()

        progressHandler(0.1)

        // --- Run analyzers concurrently ---
        async let metaTask     = metadataAnalyzer.analyze(imageSource: imageSource)
        async let pixelTask    = pixelAnalyzer.analyze(cgImage: cgImage, deepMode: deepMode)
        async let freqTask     = frequencyAnalyzer.analyze(cgImage: cgImage)
        async let lightTask    = lightingAnalyzer.analyze(cgImage: cgImage)
        async let aiTask       = aiPatternDetector.analyze(cgImage: cgImage, deepMode: deepMode)

        progressHandler(0.3)

        let metaScore  = await metaTask
        progressHandler(0.45)
        let pixelScore = await pixelTask
        progressHandler(0.60)
        let freqScore  = await freqTask
        progressHandler(0.72)
        let lightScore = await lightTask
        progressHandler(0.84)
        let aiScore    = await aiTask
        progressHandler(0.92)

        let subScores: [SubScore] = [
            SubScore(category: .metadata,
                     score: metaScore.score,
                     weight: weights[.metadata]!,
                     insights: metaScore.insights,
                     confidence: metaScore.confidence),
            SubScore(category: .pixelForensics,
                     score: pixelScore.score,
                     weight: weights[.pixelForensics]!,
                     insights: pixelScore.insights,
                     confidence: pixelScore.confidence),
            SubScore(category: .frequencyDomain,
                     score: freqScore.score,
                     weight: weights[.frequencyDomain]!,
                     insights: freqScore.insights,
                     confidence: freqScore.confidence),
            SubScore(category: .lightingConsistency,
                     score: lightScore.score,
                     weight: weights[.lightingConsistency]!,
                     insights: lightScore.insights,
                     confidence: lightScore.confidence),
            SubScore(category: .aiPatternMatch,
                     score: aiScore.score,
                     weight: weights[.aiPatternMatch]!,
                     insights: aiScore.insights,
                     confidence: aiScore.confidence)
        ]

        // Weighted composite
        var weightedSum = 0.0
        var weightTotal = 0.0
        for s in subScores {
            weightedSum += s.score * s.weight * s.confidence
            weightTotal += s.weight * s.confidence
        }
        let composite = weightTotal > 0 ? (weightedSum / weightTotal) : 50.0

        // Aggregate all findings
        let keyFindings = subScores.flatMap(\.insights)

        let duration = Date().timeIntervalSince(start)
        progressHandler(1.0)

        return AnalysisResult(
            imageURL: url,
            imageName: fileName,
            authenticityScore: composite,
            subScores: subScores,
            keyFindings: keyFindings,
            elaResult: pixelScore.elaResult,
            fileSize: fileSize,
            imageWidth: width,
            imageHeight: height,
            fileFormat: format,
            analysisDuration: duration
        )
    }
}

// MARK: - Sub-Analyzer Result

struct AnalyzerResult {
    let score: Double         // 0–100
    let insights: [String]
    let confidence: Double    // 0–1
    let elaResult: ELAResult?

    init(score: Double, insights: [String], confidence: Double = 1.0, elaResult: ELAResult? = nil) {
        self.score = min(max(score, 0), 100)
        self.insights = insights
        self.confidence = min(max(confidence, 0), 1)
        self.elaResult = elaResult
    }
}

// MARK: - Errors

enum AnalysisError: LocalizedError {
    case unreadableImage
    case unsupportedFormat
    case fileTooLarge
    case cancelled

    var errorDescription: String? {
        switch self {
        case .unreadableImage:    return "Could not read image data."
        case .unsupportedFormat:  return "Unsupported image format."
        case .fileTooLarge:       return "Image exceeds the 100 MB size limit."
        case .cancelled:          return "Analysis was cancelled."
        }
    }
}
