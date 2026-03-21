import Foundation
import CoreImage
import Vision
import CoreML

// MARK: - AI Pattern Detector
// Detects signatures common to specific AI generative systems.
// Currently uses heuristic signal analysis. Architecture is ready
// to accept a trained Core ML model — see the NOTE below.
//
// NOTE FOR FUTURE INTEGRATION:
// To plug in a real Core ML model:
//   1. Add your .mlmodel to the Xcode project
//   2. Replace the `heuristicAnalysis` call in `analyze()` with
//      a `coreMLAnalysis(cgImage:)` call using the compiled model.
//   Recommended: convert a HuggingFace AIGCDetect or Grounding DINO
//   model using coremltools for best accuracy.

actor AIPatternDetector {

    // MARK: - Public Entry Point

    func analyze(cgImage: CGImage, deepMode: Bool) async -> AnalyzerResult {
        async let heuristicTask = heuristicAnalysis(cgImage: cgImage, deepMode: deepMode)
        async let anatomyTask   = anatomyConsistencyCheck(cgImage: cgImage)

        let heuristic = await heuristicTask
        let anatomy   = await anatomyTask

        var combined = (heuristic.score + anatomy.score) / 2.0
        let allInsights = heuristic.insights + anatomy.insights

        // Weighted towards heuristic (more signals)
        combined = heuristic.score * 0.65 + anatomy.score * 0.35

        return AnalyzerResult(
            score: min(max(combined, 0), 100),
            insights: allInsights,
            confidence: (heuristic.confidence + anatomy.confidence) / 2
        )
    }

    // MARK: - Heuristic Analysis

    private func heuristicAnalysis(cgImage: CGImage, deepMode: Bool) async -> AnalyzerResult {
        var score = 60.0
        var insights: [String] = []

        let w = min(cgImage.width, 512)
        let h = min(cgImage.height, 512)

        var rgba = [UInt8](repeating: 0, count: w * h * 4)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &rgba, width: w, height: h,
                                  bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
            return AnalyzerResult(score: 50, insights: ["AI pattern analysis skipped."], confidence: 0.3)
        }
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: w, height: h))

        // --- Over-smoothing check ---
        let smoothResult = detectOverSmoothing(pixels: rgba, width: w, height: h)
        score += smoothResult.adj
        insights.append(contentsOf: smoothResult.findings)

        // --- Texture repetition (tiling patterns from upsampling) ---
        let tileResult = detectTextureTiling(pixels: rgba, width: w, height: h)
        score += tileResult.adj
        insights.append(contentsOf: tileResult.findings)

        // --- Color distribution anomalies ---
        let colorResult = detectAIColorSignatures(pixels: rgba, width: w, height: h)
        score += colorResult.adj
        insights.append(contentsOf: colorResult.findings)

        // --- Diffusion model halos/softening around subjects ---
        let haloResult = detectDiffusionHalos(pixels: rgba, width: w, height: h)
        score += haloResult.adj
        insights.append(contentsOf: haloResult.findings)

        if deepMode {
            let deepResult = deepPatternScan(pixels: rgba, width: w, height: h)
            score += deepResult.adj
            insights.append(contentsOf: deepResult.findings)
        }

        return AnalyzerResult(score: min(max(score, 0), 100), insights: insights, confidence: 0.68)
    }

    // MARK: - Over-Smoothing Detection

    private struct Contribution { let adj: Double; let findings: [String] }

    private func detectOverSmoothing(pixels: [UInt8], width: Int, height: Int) -> Contribution {
        // Compute local gradient magnitude variance
        // Over-smoothed (AI) images have very low variance in gradient magnitudes
        var gradMags: [Double] = []
        let step = 4

        for y in step..<(height - step) where y % step == 0 {
            for x in step..<(width - step) where x % step == 0 {
                let center = lumAt(pixels, x, y, width)
                let right  = lumAt(pixels, x+1, y, width)
                let down   = lumAt(pixels, x, y+1, width)
                let gx = right - center
                let gy = down  - center
                gradMags.append(sqrt(gx*gx + gy*gy))
            }
        }

        guard !gradMags.isEmpty else { return Contribution(0, []) }

        let mean = gradMags.reduce(0, +) / Double(gradMags.count)
        let std  = stdDev(gradMags)

        var adj = 0.0
        var findings: [String] = []

        if mean < 2.0 && std < 1.5 {
            adj -= 18
            findings.append("Severe over-smoothing detected — strong indicator of AI diffusion model output.")
        } else if mean < 5.0 {
            adj -= 8
            findings.append("Moderate over-smoothing detected — texture detail level below expected for camera sensor.")
        } else if mean > 8.0 && std > 5.0 {
            adj += 7
            findings.append("Natural texture gradient variation detected — consistent with photographic capture.")
        }

        return Contribution(adj, findings)
    }

    // MARK: - Texture Tiling Detection

    private func detectTextureTiling(pixels: [UInt8], width: Int, height: Int) -> Contribution {
        // Compare small patches at regular intervals for suspicious similarity
        // (upsampling artifacts from latent diffusion models)
        let patchSize = min(32, width/8, height/8)
        guard patchSize >= 4 else { return Contribution(0, []) }

        var patches: [[Double]] = []
        let gridX = min(6, width  / patchSize)
        let gridY = min(6, height / patchSize)

        for gy in 0..<gridY {
            for gx in 0..<gridX {
                let px = gx * patchSize
                let py = gy * patchSize
                var patch: [Double] = []
                for dy in 0..<patchSize {
                    for dx in 0..<patchSize {
                        patch.append(lumAt(pixels, px+dx, py+dy, width))
                    }
                }
                patches.append(patch)
            }
        }

        guard patches.count > 4 else { return Contribution(0, []) }

        // Compare pairs for similarity
        var highSimilarityPairs = 0
        var totalPairs = 0
        for i in 0..<min(patches.count, 10) {
            for j in (i+1)..<min(patches.count, 10) {
                let similarity = patchSimilarity(patches[i], patches[j])
                if similarity > 0.92 { highSimilarityPairs += 1 }
                totalPairs += 1
            }
        }

        let similarityRatio = totalPairs > 0 ? Double(highSimilarityPairs) / Double(totalPairs) : 0

        var findings: [String] = []
        var adj = 0.0

        if similarityRatio > 0.15 {
            adj -= 14
            findings.append("Repeating texture patterns detected (\(Int(similarityRatio*100))% patch similarity) — indicative of AI upsampling artifacts.")
        }

        return Contribution(adj, findings)
    }

    // MARK: - AI Color Signatures

    private func detectAIColorSignatures(pixels: [UInt8], width: Int, height: Int) -> Contribution {
        // Stable Diffusion / Midjourney often produce images with:
        // - Very saturated, vivid colors
        // - Specific hue clusters (painterly look)
        // - Or conversely: desaturated, film-simulation appearance

        var saturationValues: [Double] = []
        let sampleStep = 8

        var i = 0
        while i < pixels.count - 2 {
            let r = Double(pixels[i]) / 255.0
            let g = Double(pixels[i+1]) / 255.0
            let b = Double(pixels[i+2]) / 255.0
            let maxC = max(r, g, b)
            let minC = min(r, g, b)
            let saturation = maxC > 0 ? (maxC - minC) / maxC : 0
            saturationValues.append(saturation)
            i += sampleStep * 4
        }

        guard !saturationValues.isEmpty else { return Contribution(0, []) }

        let avgSat = saturationValues.reduce(0, +) / Double(saturationValues.count)
        let stdSat = stdDev(saturationValues)

        var findings: [String] = []
        var adj = 0.0

        // Midjourney/SD v1.5 signatures: extreme saturation uniformity
        if avgSat > 0.75 && stdSat < 0.08 {
            adj -= 12
            findings.append("Unusually high and uniform color saturation — typical of AI art generator output (Midjourney/SD style).")
        }

        // Over-desaturated with uniform distribution (some fine-tuned models)
        if avgSat < 0.08 && stdSat < 0.03 {
            adj -= 8
            findings.append("Near-monochrome with anomalously uniform saturation — possible synthetic grayscale conversion or AI model signature.")
        }

        return Contribution(adj, findings)
    }

    // MARK: - Diffusion Halos

    private func detectDiffusionHalos(pixels: [UInt8], width: Int, height: Int) -> Contribution {
        // Diffusion models often create a halo/glow effect around high-contrast edges
        // This manifests as high luminance variance in a band around edges

        var edgeAdjacentVariance: [Double] = []
        let step = 6

        for y in step..<(height - step) where y % step == 0 {
            for x in step..<(width - step) where x % step == 0 {
                let center = lumAt(pixels, x, y, width)
                let neighbors = [
                    lumAt(pixels, x-2, y, width), lumAt(pixels, x+2, y, width),
                    lumAt(pixels, x, y-2, width), lumAt(pixels, x, y+2, width)
                ]
                let gradMag = neighbors.map { abs($0 - center) }.max() ?? 0

                // If we're near a strong edge, check the wider neighborhood
                if gradMag > 20 {
                    let farNeighbors = [
                        lumAt(pixels, x-4, y, width), lumAt(pixels, x+4, y, width),
                        lumAt(pixels, x, y-4, width), lumAt(pixels, x, y+4, width)
                    ]
                    let nearMean = neighbors.reduce(0, +) / Double(neighbors.count)
                    let farMean  = farNeighbors.reduce(0, +) / Double(farNeighbors.count)
                    // Halo = far region is brighter than near region around edge
                    edgeAdjacentVariance.append(farMean - nearMean)
                }
            }
        }

        guard edgeAdjacentVariance.count > 20 else { return Contribution(0, []) }

        let positiveHalos = edgeAdjacentVariance.filter { $0 > 8 }.count
        let haloRatio = Double(positiveHalos) / Double(edgeAdjacentVariance.count)

        var findings: [String] = []
        var adj = 0.0

        if haloRatio > 0.20 {
            adj -= 10
            findings.append("Luminance halos detected around edges — common artifact in diffusion model outputs.")
        } else if haloRatio < 0.05 {
            adj += 4
        }

        return Contribution(adj, findings)
    }

    // MARK: - Deep Pattern Scan (Deep Mode Only)

    private func deepPatternScan(pixels: [UInt8], width: Int, height: Int) -> Contribution {
        // Additional deep-mode checks: checkerboard artifacts (GAN), border inconsistencies
        var findings: [String] = []
        var adj = 0.0

        // Checkerboard detection: common in some GAN architectures (deconv artifacts)
        var checkerboardScore = 0.0
        let checkStep = 2
        var count = 0

        for y in checkStep..<(height - checkStep) where y % (checkStep * 4) == 0 {
            for x in checkStep..<(width - checkStep) where x % (checkStep * 4) == 0 {
                let l00 = lumAt(pixels, x, y, width)
                let l01 = lumAt(pixels, x+checkStep, y, width)
                let l10 = lumAt(pixels, x, y+checkStep, width)
                let l11 = lumAt(pixels, x+checkStep, y+checkStep, width)
                // Perfect checkerboard: alternating high/low
                let pattern = (l00 - l01) * (l11 - l10)
                if pattern > 100 { checkerboardScore += 1 }
                count += 1
            }
        }

        let checkerRatio = count > 0 ? checkerboardScore / Double(count) : 0
        if checkerRatio > 0.08 {
            adj -= 12
            findings.append("Checkerboard artifacts detected — signature of certain GAN upsampling layers.")
        }

        return Contribution(adj, findings)
    }

    // MARK: - Anatomy Consistency (Vision)

    private func anatomyConsistencyCheck(cgImage: CGImage) async -> AnalyzerResult {
        return await withCheckedContinuation { continuation in
            var requests: [VNRequest] = []
            var faceCount = 0
            var anomalyInsights: [String] = []
            var adj = 0.0

            let faceRequest = VNDetectFaceLandmarksRequest { req, error in
                guard error == nil,
                      let obs = req.results as? [VNFaceObservation] else { return }
                faceCount = obs.count

                for face in obs {
                    guard let landmarks = face.landmarks else { continue }

                    // Check eye symmetry
                    if let leftEye = landmarks.leftEye, let rightEye = landmarks.rightEye {
                        let leftPts  = leftEye.normalizedPoints
                        let rightPts = rightEye.normalizedPoints
                        if !leftPts.isEmpty && !rightPts.isEmpty {
                            let leftCentroid  = centroid(leftPts)
                            let rightCentroid = centroid(rightPts)
                            // Eyes should be at roughly the same Y level
                            let yDiff = abs(leftCentroid.y - rightCentroid.y)
                            if yDiff > 0.08 {
                                adj -= 10
                                anomalyInsights.append("Eye-level asymmetry detected — AI-generated faces commonly have misaligned eyes.")
                            }
                        }
                    }

                    // Check if face landmarks are plausible (teeth/mouth)
                    if let innerLips = landmarks.innerLips {
                        let pts = innerLips.normalizedPoints
                        if pts.count >= 4 {
                            let spread = pts.map(\.x).max()! - pts.map(\.x).min()!
                            if spread > 0.6 {
                                adj -= 6
                                anomalyInsights.append("Unnatural mouth proportions detected — common in AI-generated portraits.")
                            }
                        }
                    }
                }
            }

            requests.append(faceRequest)

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform(requests)

            var score = 65.0 + adj
            var insights = anomalyInsights

            if faceCount == 0 {
                insights.append("No facial anatomy detected — structural anatomy check not applicable.")
                score = 65.0
            } else if anomalyInsights.isEmpty {
                insights.append("Facial anatomy within expected proportions for \(faceCount) detected face(s).")
                score += 8
            }

            continuation.resume(returning: AnalyzerResult(
                score: min(max(score, 0), 100),
                insights: insights,
                confidence: faceCount > 0 ? 0.75 : 0.45
            ))
        }
    }

    // MARK: - Helpers

    private func lumAt(_ pixels: [UInt8], _ x: Int, _ y: Int, _ width: Int) -> Double {
        let idx = (y * width + x) * 4
        guard idx + 2 < pixels.count else { return 0 }
        return 0.299 * Double(pixels[idx]) + 0.587 * Double(pixels[idx+1]) + 0.114 * Double(pixels[idx+2])
    }

    private func patchSimilarity(_ a: [Double], _ b: [Double]) -> Double {
        guard a.count == b.count, !a.isEmpty else { return 0 }
        let meanA = a.reduce(0, +) / Double(a.count)
        let meanB = b.reduce(0, +) / Double(b.count)
        var num = 0.0, denA = 0.0, denB = 0.0
        for i in 0..<a.count {
            let da = a[i] - meanA
            let db = b[i] - meanB
            num  += da * db
            denA += da * da
            denB += db * db
        }
        guard denA > 0, denB > 0 else { return 0 }
        return num / sqrt(denA * denB)
    }

    private func centroid(_ points: [CGPoint]) -> CGPoint {
        let x = points.map(\.x).reduce(0, +) / CGFloat(points.count)
        let y = points.map(\.y).reduce(0, +) / CGFloat(points.count)
        return CGPoint(x: x, y: y)
    }

    private func stdDev(_ values: [Double]) -> Double {
        guard values.count > 1 else { return 0 }
        let mean = values.reduce(0, +) / Double(values.count)
        let variance = values.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(values.count)
        return sqrt(variance)
    }
}
