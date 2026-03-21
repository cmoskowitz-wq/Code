import Foundation
import Vision
import CoreImage
import CoreGraphics

// MARK: - Lighting Analyzer
// Uses Vision framework for face detection and structural analysis.
// Validates lighting direction consistency, shadow geometry,
// and luminance distribution across the scene.

actor LightingAnalyzer {

    func analyze(cgImage: CGImage) async -> AnalyzerResult {
        var score = 65.0
        var insights: [String] = []
        var confidence = 0.65

        // --- 1. Luminance Distribution ---
        let lumResult = await analyzeLuminanceDistribution(cgImage: cgImage)
        score += lumResult.adj
        insights.append(contentsOf: lumResult.findings)

        // --- 2. Face Lighting Consistency (Vision) ---
        let faceResult = await analyzeFaceLighting(cgImage: cgImage)
        score += faceResult.adj
        insights.append(contentsOf: faceResult.findings)
        if faceResult.usedFaces { confidence = min(confidence + 0.15, 1.0) }

        // --- 3. Gradient Consistency ---
        let gradResult = await analyzeGradientConsistency(cgImage: cgImage)
        score += gradResult.adj
        insights.append(contentsOf: gradResult.findings)

        // --- 4. Shadow/Highlight Balance ---
        let shadowResult = analyzeShadowHighlightBalance(cgImage: cgImage)
        score += shadowResult.adj
        insights.append(contentsOf: shadowResult.findings)

        return AnalyzerResult(
            score: min(max(score, 0), 100),
            insights: insights,
            confidence: confidence
        )
    }

    // MARK: - Luminance Distribution

    private struct LightContrib { let adj: Double; let findings: [String]; let usedFaces: Bool }

    private func analyzeLuminanceDistribution(cgImage: CGImage) async -> LightContrib {
        let w = min(cgImage.width, 256)
        let h = min(cgImage.height, 256)

        var rgba = [UInt8](repeating: 0, count: w * h * 4)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &rgba, width: w, height: h,
                                  bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
            return LightContrib(adj: 0, findings: [], usedFaces: false)
        }
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: w, height: h))

        // Divide into quadrants and compute mean luminance
        var quadrantLum = [Double](repeating: 0, count: 4)
        var quadrantCount = [Int](repeating: 0, count: 4)

        for y in 0..<h {
            for x in 0..<w {
                let idx = (y * w + x) * 4
                let lum = 0.299 * Double(rgba[idx]) + 0.587 * Double(rgba[idx+1]) + 0.114 * Double(rgba[idx+2])
                let q = (x < w/2 ? 0 : 1) + (y < h/2 ? 0 : 2)
                quadrantLum[q] += lum
                quadrantCount[q] += 1
            }
        }

        let avgLum = (0..<4).map { quadrantCount[$0] > 0 ? quadrantLum[$0] / Double(quadrantCount[$0]) : 0.0 }

        // Natural lighting creates smooth gradients; AI may create inconsistent quadrant brightness
        let maxDiff = (0..<avgLum.count).flatMap { i in
            (i..<avgLum.count).map { j in abs(avgLum[i] - avgLum[j]) }
        }.max() ?? 0

        var findings: [String] = []
        var adj = 0.0

        if maxDiff > 80 {
            adj -= 8
            findings.append("Significant luminance inconsistency across image quadrants (\(Int(maxDiff)) unit difference).")
        } else if maxDiff < 15 {
            adj -= 4  // perfectly even lighting is suspicious too
            findings.append("Unusually uniform luminance distribution — natural scenes typically have light gradients.")
        } else {
            adj += 5
        }

        return LightContrib(adj: adj, findings: findings, usedFaces: false)
    }

    // MARK: - Face Lighting via Vision

    private func analyzeFaceLighting(cgImage: CGImage) async -> LightContrib {
        return await withCheckedContinuation { continuation in
            let request = VNDetectFaceRectanglesRequest { request, error in
                guard error == nil,
                      let observations = request.results as? [VNFaceObservation],
                      !observations.isEmpty
                else {
                    continuation.resume(returning: LightContrib(adj: 0, findings: ["No faces detected — skipping facial lighting analysis."], usedFaces: false))
                    return
                }

                // Multiple faces: check if lighting direction is consistent across all
                if observations.count > 1 {
                    let result = self.checkMultiFaceLighting(cgImage: cgImage, faces: observations)
                    continuation.resume(returning: result)
                } else {
                    // Single face detected — note it
                    continuation.resume(returning: LightContrib(
                        adj: 3,
                        findings: ["Face detected — lighting analysis applied to facial region."],
                        usedFaces: true
                    ))
                }
            }

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])
        }
    }

    private func checkMultiFaceLighting(cgImage: CGImage, faces: [VNFaceObservation]) -> LightContrib {
        let w = CGFloat(cgImage.width)
        let h = CGFloat(cgImage.height)

        // For each face, compute dominant light direction from luminance gradient
        var lightDirections: [CGFloat] = []
        for face in faces {
            let box = VNImageRectForNormalizedRect(face.boundingBox, Int(w), Int(h))
            if let direction = estimateLightDirection(cgImage: cgImage, region: box) {
                lightDirections.append(direction)
            }
        }

        guard lightDirections.count > 1 else {
            return LightContrib(adj: 2, findings: ["\(faces.count) faces detected — lighting consistency evaluation applied."], usedFaces: true)
        }

        // Check consistency of light directions across faces
        let mean = lightDirections.reduce(0, +) / CGFloat(lightDirections.count)
        let variance = lightDirections.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / CGFloat(lightDirections.count)

        var findings: [String] = []
        var adj = 0.0

        if variance > 3000 {
            adj -= 15
            findings.append("Inconsistent lighting direction across \(faces.count) faces — strong indicator of composite or AI-generated image.")
        } else {
            adj += 8
            findings.append("Lighting direction consistent across \(faces.count) detected faces.")
        }

        return LightContrib(adj: adj, findings: findings, usedFaces: true)
    }

    private func estimateLightDirection(cgImage: CGImage, region: CGRect) -> CGFloat? {
        let rW = max(Int(region.width), 16)
        let rH = max(Int(region.height), 16)

        var rgba = [UInt8](repeating: 0, count: rW * rH * 4)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &rgba, width: rW, height: rH,
                                  bitsPerComponent: 8, bytesPerRow: rW * 4,
                                  space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }

        ctx.draw(cgImage, in: CGRect(x: -region.origin.x, y: -region.origin.y,
                                    width: CGFloat(cgImage.width), height: CGFloat(cgImage.height)))

        // Compute horizontal luminance gradient
        var leftLum = 0.0, rightLum = 0.0
        for y in 0..<rH {
            for x in 0..<rW/2 {
                let idx = (y * rW + x) * 4
                leftLum += 0.299 * Double(rgba[idx]) + 0.587 * Double(rgba[idx+1]) + 0.114 * Double(rgba[idx+2])
            }
            for x in rW/2..<rW {
                let idx = (y * rW + x) * 4
                rightLum += 0.299 * Double(rgba[idx]) + 0.587 * Double(rgba[idx+1]) + 0.114 * Double(rgba[idx+2])
            }
        }
        return CGFloat(leftLum - rightLum)
    }

    // MARK: - Gradient Consistency

    private func analyzeGradientConsistency(cgImage: CGImage) async -> LightContrib {
        let w = min(cgImage.width, 128)
        let h = min(cgImage.height, 128)

        var rgba = [UInt8](repeating: 0, count: w * h * 4)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &rgba, width: w, height: h,
                                  bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
            return LightContrib(adj: 0, findings: [], usedFaces: false)
        }
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: w, height: h))

        // Compute horizontal gradient direction at multiple y positions
        var gradientDirections: [Double] = []
        for y in Swift.stride(from: h/8, to: h - h/8, by: h/8) {
            var rowLum = [Double](repeating: 0, count: w)
            for x in 0..<w {
                let idx = (y * w + x) * 4
                rowLum[x] = 0.299 * Double(rgba[idx]) + 0.587 * Double(rgba[idx+1]) + 0.114 * Double(rgba[idx+2])
            }
            // Simple linear regression to find dominant gradient direction
            let meanX = Double(w) / 2
            let meanY = rowLum.reduce(0, +) / Double(w)
            var num = 0.0, den = 0.0
            for x in 0..<w {
                num += (Double(x) - meanX) * (rowLum[x] - meanY)
                den += (Double(x) - meanX) * (Double(x) - meanX)
            }
            if den > 0 { gradientDirections.append(num/den) }
        }

        guard gradientDirections.count > 2 else { return LightContrib(adj: 0, findings: [], usedFaces: false) }

        let signs = gradientDirections.map { $0 > 0 ? 1 : -1 }
        let signChanges = zip(signs, signs.dropFirst()).filter { $0.0 != $0.1 }.count
        let changeRatio = Double(signChanges) / Double(signs.count)

        var findings: [String] = []
        var adj = 0.0

        if changeRatio > 0.5 {
            adj -= 8
            findings.append("Inconsistent luminance gradient direction across scene — possible lighting compositing artifact.")
        } else {
            adj += 4
        }

        return LightContrib(adj: adj, findings: findings, usedFaces: false)
    }

    // MARK: - Shadow/Highlight Balance

    private func analyzeShadowHighlightBalance(cgImage: CGImage) -> LightContrib {
        let w = min(cgImage.width, 256)
        let h = min(cgImage.height, 256)

        var rgba = [UInt8](repeating: 0, count: w * h * 4)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &rgba, width: w, height: h,
                                  bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
            return LightContrib(adj: 0, findings: [], usedFaces: false)
        }
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: w, height: h))

        var shadows = 0, highlights = 0, midtones = 0
        for i in 0..<(w * h) {
            let idx = i * 4
            let lum = 0.299 * Double(rgba[idx]) + 0.587 * Double(rgba[idx+1]) + 0.114 * Double(rgba[idx+2])
            if lum < 64 { shadows += 1 }
            else if lum > 192 { highlights += 1 }
            else { midtones += 1 }
        }

        let total = Double(w * h)
        let shadowRatio    = Double(shadows)    / total
        let highlightRatio = Double(highlights) / total

        var findings: [String] = []
        var adj = 0.0

        // Completely clipped shadows or highlights suggest HDR-style AI compositing
        if shadowRatio > 0.40 && highlightRatio < 0.02 {
            adj -= 6
            findings.append("Extreme shadow clipping detected — atypical tonal distribution.")
        } else if highlightRatio > 0.40 && shadowRatio < 0.02 {
            adj -= 6
            findings.append("Extreme highlight clipping detected — atypical tonal distribution.")
        } else if shadowRatio < 0.35 && highlightRatio < 0.35 {
            adj += 5
            findings.append("Shadow/highlight tonal balance within expected range for authentic photography.")
        }

        return LightContrib(adj: adj, findings: findings, usedFaces: false)
    }
}
