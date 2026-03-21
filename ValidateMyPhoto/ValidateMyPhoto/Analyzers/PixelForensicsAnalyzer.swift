import Foundation
import CoreImage
import Accelerate

// MARK: - Pixel Forensics Analyzer
// Analyzes raw pixel statistics to detect anomalies typical of AI-generated images.
// Techniques: noise variance estimation, ELA (Error Level Analysis), color channel
// statistics, and local texture consistency.

actor PixelForensicsAnalyzer {

    func analyze(cgImage: CGImage, deepMode: Bool) async -> AnalyzerResult {
        var score = 60.0
        var insights: [String] = []
        var confidence = 0.75
        var elaResult: ELAResult?

        guard let pixelData = extractPixelData(from: cgImage) else {
            return AnalyzerResult(score: 50, insights: ["Could not access pixel data for forensic analysis."], confidence: 0.3)
        }

        let width  = cgImage.width
        let height = cgImage.height

        // --- 1. Noise Variance Analysis ---
        let noiseResult = analyzeNoiseVariance(pixels: pixelData, width: width, height: height)
        score += noiseResult.scoreAdjustment
        insights.append(contentsOf: noiseResult.findings)
        confidence = max(confidence, noiseResult.confidence)

        // --- 2. Color Channel Statistics ---
        let channelResult = analyzeColorChannels(pixels: pixelData, width: width, height: height)
        score += channelResult.scoreAdjustment
        insights.append(contentsOf: channelResult.findings)

        // --- 3. Edge Coherence ---
        let edgeResult = analyzeEdgeCoherence(pixels: pixelData, width: width, height: height)
        score += edgeResult.scoreAdjustment
        insights.append(contentsOf: edgeResult.findings)

        // --- 4. ELA (Error Level Analysis) ---
        if let elaRes = performELA(cgImage: cgImage) {
            elaResult = elaRes
            let elaAdj = elaScoreAdjustment(ela: elaRes)
            score += elaAdj.scoreAdjustment
            insights.append(contentsOf: elaAdj.findings)
        }

        // --- 5. Texture Uniformity (deep mode adds more patches) ---
        let patchCount = deepMode ? 64 : 16
        let textureResult = analyzeTextureUniformity(pixels: pixelData, width: width, height: height, patches: patchCount)
        score += textureResult.scoreAdjustment
        insights.append(contentsOf: textureResult.findings)

        return AnalyzerResult(
            score: min(max(score, 0), 100),
            insights: insights,
            confidence: confidence,
            elaResult: elaResult
        )
    }

    // MARK: - Pixel Extraction

    private func extractPixelData(from image: CGImage) -> [UInt8]? {
        let width  = image.width
        let height = image.height
        let bpp    = 4  // RGBA
        var data   = [UInt8](repeating: 0, count: width * height * bpp)

        guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(
                data: &data,
                width: width, height: height,
                bitsPerComponent: 8,
                bytesPerRow: width * bpp,
                space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
              ) else { return nil }

        ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return data
    }

    // MARK: - Noise Variance

    private struct AnalysisContribution {
        let scoreAdjustment: Double
        let findings: [String]
        let confidence: Double

        init(_ adj: Double, _ findings: [String], _ conf: Double = 0.7) {
            self.scoreAdjustment = adj
            self.findings = findings
            self.confidence = conf
        }
    }

    private func analyzeNoiseVariance(pixels: [UInt8], width: Int, height: Int) -> AnalysisContribution {
        // Sample a grid of 5×5 pixel blocks and compute local variance
        // Real sensor noise is spatially random; AI images tend to be smooth or patterned
        let stride = 16
        var variances: [Double] = []

        for y in Swift.stride(from: 0, to: height - stride, by: stride) {
            for x in Swift.stride(from: 0, to: width - stride, by: stride) {
                var vals: [Double] = []
                for dy in 0..<stride {
                    for dx in 0..<stride {
                        let idx = ((y + dy) * width + (x + dx)) * 4
                        let lum = 0.299 * Double(pixels[idx]) + 0.587 * Double(pixels[idx+1]) + 0.114 * Double(pixels[idx+2])
                        vals.append(lum)
                    }
                }
                let mean = vals.reduce(0, +) / Double(vals.count)
                let variance = vals.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(vals.count)
                variances.append(variance)
            }
        }

        guard !variances.isEmpty else { return AnalysisContribution(0, []) }

        let avgVariance = variances.reduce(0, +) / Double(variances.count)
        let varianceOfVariances = {
            let mean = variances.reduce(0, +) / Double(variances.count)
            return variances.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(variances.count)
        }()

        var adj = 0.0
        var findings: [String] = []

        // AI diffusion images often have very low noise variance (smooth) or
        // very high uniformity (consistent noise pattern)
        if avgVariance < 5.0 {
            adj -= 12
            findings.append("Unusually low local noise variance — AI images tend to be over-smoothed.")
        } else if avgVariance > 8.0 && avgVariance < 200.0 {
            adj += 8
            findings.append("Natural noise variance consistent with camera sensor output.")
        }

        if varianceOfVariances < 10.0 && avgVariance < 20.0 {
            adj -= 8
            findings.append("Suspiciously uniform noise distribution across image blocks.")
        }

        return AnalysisContribution(adj, findings, 0.7)
    }

    // MARK: - Color Channels

    private func analyzeColorChannels(pixels: [UInt8], width: Int, height: Int) -> AnalysisContribution {
        var rValues: [Double] = []
        var gValues: [Double] = []
        var bValues: [Double] = []

        // Sample every 8th pixel for performance
        let sampleStep = 8
        var i = 0
        while i < pixels.count - 3 {
            rValues.append(Double(pixels[i]))
            gValues.append(Double(pixels[i+1]))
            bValues.append(Double(pixels[i+2]))
            i += sampleStep * 4
        }

        guard !rValues.isEmpty else { return AnalysisContribution(0, []) }

        let rMean = rValues.reduce(0, +) / Double(rValues.count)
        let gMean = gValues.reduce(0, +) / Double(gValues.count)
        let bMean = bValues.reduce(0, +) / Double(bValues.count)

        let rStd = stdDev(rValues)
        let gStd = stdDev(gValues)
        let bStd = stdDev(bValues)

        var adj = 0.0
        var findings: [String] = []

        // Check for unusual channel correlation (AI images often have near-perfect channel correlation)
        let channelBalance = abs(rMean - gMean) + abs(gMean - bMean) + abs(rMean - bMean)
        if channelBalance < 5.0 && rStd < 20.0 {
            adj -= 6
            findings.append("Unusually high RGB channel correlation — possible synthetic image signature.")
        }

        // Very narrow histogram (AI overprocessing)
        if rStd < 10 && gStd < 10 && bStd < 10 {
            adj -= 8
            findings.append("Narrow color histogram detected — possibly over-processed or synthetic.")
        } else if rStd > 40 || gStd > 40 || bStd > 40 {
            adj += 5
            findings.append("Rich color channel variation consistent with natural photograph.")
        }

        return AnalysisContribution(adj, findings)
    }

    // MARK: - Edge Coherence

    private func analyzeEdgeCoherence(pixels: [UInt8], width: Int, height: Int) -> AnalysisContribution {
        // Simple Sobel-based edge strength + coherence analysis
        // AI images often have "too perfect" edges or anomalous edge patterns
        var edgeStrengths: [Double] = []
        let sampleStride = 4

        for y in sampleStride..<(height - sampleStride) where y % sampleStride == 0 {
            for x in sampleStride..<(width - sampleStride) where x % sampleStride == 0 {
                let lum: (Int, Int) -> Double = { px, py in
                    let idx = (py * width + px) * 4
                    return 0.299 * Double(pixels[idx]) + 0.587 * Double(pixels[idx+1]) + 0.114 * Double(pixels[idx+2])
                }
                let gx = -lum(x-1, y-1) + lum(x+1, y-1) - 2*lum(x-1, y) + 2*lum(x+1, y) - lum(x-1, y+1) + lum(x+1, y+1)
                let gy = -lum(x-1, y-1) - 2*lum(x, y-1) - lum(x+1, y-1) + lum(x-1, y+1) + 2*lum(x, y+1) + lum(x+1, y+1)
                edgeStrengths.append(sqrt(gx*gx + gy*gy))
            }
        }

        guard !edgeStrengths.isEmpty else { return AnalysisContribution(0, []) }

        let avgEdge = edgeStrengths.reduce(0, +) / Double(edgeStrengths.count)
        let edgeStd = stdDev(edgeStrengths)

        var adj = 0.0
        var findings: [String] = []

        // Extremely sharp edges everywhere = possible AI over-sharpening
        if avgEdge > 120 && edgeStd < 30 {
            adj -= 10
            findings.append("Unusually uniform edge sharpness detected — consistent with AI generation or over-sharpening.")
        }

        // Very smooth edges = possible diffusion model blending
        if avgEdge < 8 {
            adj -= 6
            findings.append("Edge definition is unusually soft — may indicate diffusion model smoothing.")
        }

        if avgEdge >= 8 && avgEdge <= 80 && edgeStd > 20 {
            adj += 7
            findings.append("Edge coherence and variance consistent with natural photographic content.")
        }

        return AnalysisContribution(adj, findings)
    }

    // MARK: - Error Level Analysis (ELA)

    private func performELA(cgImage: CGImage) -> ELAResult? {
        // ELA compresses image at known quality and compares to original.
        // Authentic photos show uniform error levels; manipulated/generated
        // images show inconsistent error concentrations.
        let ciImage = CIImage(cgImage: cgImage)

        let context = CIContext()

        // Re-compress at 75% JPEG quality
        guard let recompressedData = context.jpegRepresentation(of: ciImage, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!, options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.75]),
              let recompressedCI = CIImage(data: recompressedData) else { return nil }

        // Compute difference
        guard let diffFilter = CIFilter(name: "CIDifferenceBlendMode") else { return nil }
        diffFilter.setValue(ciImage, forKey: kCIInputImageKey)
        diffFilter.setValue(recompressedCI, forKey: kCIInputBackgroundImageKey)

        guard let diffOutput = diffFilter.outputImage,
              let diffCG = context.createCGImage(diffOutput, from: diffOutput.extent) else { return nil }

        // Extract diff pixel stats
        guard let diffPixels = extractPixelDataFrom(diffCG) else { return nil }

        var hotspots = 0
        var maxIntensity = 0.0
        var totalIntensity = 0.0
        let threshold = 30.0

        var i = 0
        while i < diffPixels.count - 2 {
            let intensity = (Double(diffPixels[i]) + Double(diffPixels[i+1]) + Double(diffPixels[i+2])) / 3.0
            if intensity > threshold { hotspots += 1 }
            if intensity > maxIntensity { maxIntensity = intensity }
            totalIntensity += intensity
            i += 4
        }

        let pixelCount = diffPixels.count / 4
        let hotspotRatio = pixelCount > 0 ? Double(hotspots) / Double(pixelCount) : 0
        let suspicionScore = min(100, hotspotRatio * 500 + maxIntensity * 0.3)

        return ELAResult(suspicionScore: suspicionScore, hotspotCount: hotspots, maxIntensity: maxIntensity)
    }

    private func extractPixelDataFrom(_ image: CGImage) -> [UInt8]? {
        let width  = image.width
        let height = image.height
        var data   = [UInt8](repeating: 0, count: width * height * 4)
        guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &data, width: width, height: height,
                                  bitsPerComponent: 8, bytesPerRow: width * 4,
                                  space: colorSpace,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return data
    }

    private func elaScoreAdjustment(ela: ELAResult) -> AnalysisContribution {
        var adj = 0.0
        var findings: [String] = []

        if ela.suspicionScore > 60 {
            adj -= 18
            findings.append("ELA detected high error-level inconsistencies (\(Int(ela.suspicionScore))% suspicion) — indicates possible manipulation or synthetic generation.")
        } else if ela.suspicionScore > 35 {
            adj -= 8
            findings.append("ELA shows moderate error-level variation — possible local edits or compression artifacts.")
        } else {
            adj += 6
            findings.append("ELA error levels are consistent and uniform — expected for authentic photographs.")
        }

        return AnalysisContribution(adj, findings, 0.8)
    }

    // MARK: - Texture Uniformity

    private func analyzeTextureUniformity(pixels: [UInt8], width: Int, height: Int, patches: Int) -> AnalysisContribution {
        // AI images often have globally uniform texture (no grain variation)
        let patchW = max(width / 8, 16)
        let patchH = max(height / 8, 16)
        var patchVariances: [Double] = []

        for _ in 0..<patches {
            let px = Int.random(in: 0..<max(1, width  - patchW))
            let py = Int.random(in: 0..<max(1, height - patchH))
            var lumVals: [Double] = []

            for dy in 0..<patchH {
                for dx in 0..<patchW {
                    let idx = ((py + dy) * width + (px + dx)) * 4
                    guard idx + 2 < pixels.count else { continue }
                    let lum = 0.299 * Double(pixels[idx]) + 0.587 * Double(pixels[idx+1]) + 0.114 * Double(pixels[idx+2])
                    lumVals.append(lum)
                }
            }

            if !lumVals.isEmpty {
                let mean = lumVals.reduce(0, +) / Double(lumVals.count)
                let v = lumVals.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(lumVals.count)
                patchVariances.append(v)
            }
        }

        guard patchVariances.count > 4 else { return AnalysisContribution(0, []) }

        let meanVar = patchVariances.reduce(0, +) / Double(patchVariances.count)
        let varOfVar = stdDev(patchVariances)

        var adj = 0.0
        var findings: [String] = []

        if varOfVar < 5.0 && meanVar < 50 {
            adj -= 10
            findings.append("Texture uniformity is suspiciously consistent across image patches — common in AI-generated content.")
        } else if varOfVar > 20.0 {
            adj += 6
            findings.append("Natural texture variation across image regions — consistent with real-world photography.")
        }

        return AnalysisContribution(adj, findings)
    }

    // MARK: - Helpers

    private func stdDev(_ values: [Double]) -> Double {
        guard values.count > 1 else { return 0 }
        let mean = values.reduce(0, +) / Double(values.count)
        let variance = values.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(values.count)
        return sqrt(variance)
    }
}
