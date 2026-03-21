import Foundation
import Accelerate
import CoreImage

// MARK: - Frequency Domain Analyzer
// Uses FFT (Fast Fourier Transform) via Accelerate to detect unnatural
// frequency distributions. AI-generated images often lack the full
// high-frequency content (fine grain, detail) of real photographs,
// and diffusion models introduce periodic spectral artifacts.

actor FrequencyAnalyzer {

    func analyze(cgImage: CGImage) async -> AnalyzerResult {
        var score = 60.0
        var insights: [String] = []

        guard let grayscaleData = toGrayscaleFloat(cgImage) else {
            return AnalyzerResult(score: 50, insights: ["Frequency analysis skipped — could not process image."], confidence: 0.3)
        }

        let width  = grayscaleData.width
        let height = grayscaleData.height
        let data   = grayscaleData.pixels

        // Work on a power-of-2 size region for FFT
        let fftSize = largestPow2(min(width, height, 512))
        guard fftSize >= 64 else {
            return AnalyzerResult(score: 50, insights: ["Image too small for frequency analysis."], confidence: 0.4)
        }

        // --- 1. Row-wise FFT energy analysis ---
        let spectrumResult = analyzeSpectrum(data: data, width: width, height: height, fftSize: fftSize)
        score += spectrumResult.adj
        insights.append(contentsOf: spectrumResult.findings)

        // --- 2. High/Low frequency ratio ---
        let ratioResult = analyzeFrequencyRatio(data: data, width: width, height: height, fftSize: fftSize)
        score += ratioResult.adj
        insights.append(contentsOf: ratioResult.findings)

        // --- 3. Periodic artifact detection ---
        let periodicResult = detectPeriodicArtifacts(data: data, width: width, height: height, fftSize: fftSize)
        score += periodicResult.adj
        insights.append(contentsOf: periodicResult.findings)

        return AnalyzerResult(
            score: min(max(score, 0), 100),
            insights: insights,
            confidence: 0.72
        )
    }

    // MARK: - Grayscale Conversion

    private struct GrayscaleData {
        let pixels: [Float]
        let width: Int
        let height: Int
    }

    private func toGrayscaleFloat(_ image: CGImage) -> GrayscaleData? {
        let w = min(image.width, 512)
        let h = min(image.height, 512)

        var rgba = [UInt8](repeating: 0, count: w * h * 4)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &rgba, width: w, height: h,
                                  bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: cs,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
        else { return nil }

        ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))

        var gray = [Float](repeating: 0, count: w * h)
        for i in 0..<(w * h) {
            let r = Float(rgba[i*4])
            let g = Float(rgba[i*4+1])
            let b = Float(rgba[i*4+2])
            gray[i] = 0.299 * r + 0.587 * g + 0.114 * b
        }
        return GrayscaleData(pixels: gray, width: w, height: h)
    }

    // MARK: - FFT Helpers

    private func largestPow2(_ n: Int) -> Int {
        var p = 1
        while p * 2 <= n { p *= 2 }
        return p
    }

    private func computeRowFFT(row: [Float]) -> [Float] {
        let n = row.count
        guard n > 0, (n & (n - 1)) == 0 else { return [] }
        let log2n = vDSP_Length(log2(Float(n)))

        guard let setup = vDSP_DFT_zop_CreateSetup(nil, vDSP_Length(n), .FORWARD) else { return [] }
        defer { vDSP_DFT_DestroySetup(setup) }

        var realIn  = row
        var imagIn  = [Float](repeating: 0, count: n)
        var realOut = [Float](repeating: 0, count: n)
        var imagOut = [Float](repeating: 0, count: n)

        vDSP_DFT_Execute(setup, &realIn, &imagIn, &realOut, &imagOut)

        // Magnitude spectrum
        var mag = [Float](repeating: 0, count: n/2)
        for i in 0..<n/2 {
            mag[i] = sqrt(realOut[i]*realOut[i] + imagOut[i]*imagOut[i])
        }
        return mag
    }

    // MARK: - Spectrum Analysis

    private struct FFTContrib { let adj: Double; let findings: [String] }

    private func analyzeSpectrum(data: [Float], width: Int, height: Int, fftSize: Int) -> FFTContrib {
        // Compute average spectrum across sampled rows
        var accumulatedMag = [Double](repeating: 0, count: fftSize/2)
        var rowCount = 0
        let rowSample = max(1, height / 16)

        for row in Swift.stride(from: 0, to: height, by: rowSample) {
            let start = row * width
            let end   = min(start + fftSize, data.count)
            guard end - start >= fftSize else { continue }

            let rowSlice = Array(data[start..<start+fftSize])
            let mag = computeRowFFT(row: rowSlice)
            guard mag.count == fftSize/2 else { continue }

            for i in 0..<fftSize/2 {
                accumulatedMag[i] += Double(mag[i])
            }
            rowCount += 1
        }

        guard rowCount > 0 else { return FFTContrib(adj: 0, findings: []) }

        let avgMag = accumulatedMag.map { $0 / Double(rowCount) }

        // Check spectral slope: real images follow ~1/f distribution
        // Flat or inverted spectrum suggests synthetic content
        let lowFreqEnergy  = avgMag[1..<max(2, fftSize/8)].reduce(0, +)
        let highFreqEnergy = avgMag[fftSize/4..<fftSize/2].reduce(0, +)
        let midFreqEnergy  = avgMag[fftSize/8..<fftSize/4].reduce(0, +)

        let totalEnergy = lowFreqEnergy + midFreqEnergy + highFreqEnergy
        guard totalEnergy > 0 else { return FFTContrib(adj: 0, findings: []) }

        let lowRatio  = lowFreqEnergy  / totalEnergy
        let highRatio = highFreqEnergy / totalEnergy

        var adj = 0.0
        var findings: [String] = []

        // Natural images: lowRatio dominant, high frequencies present but weaker
        if lowRatio > 0.6 && highRatio > 0.05 {
            adj += 8
            findings.append("Frequency spectrum follows natural 1/f distribution — consistent with real photographic content.")
        }

        if highRatio < 0.02 {
            adj -= 10
            findings.append("Unusually low high-frequency energy — AI diffusion models often suppress fine-grain detail.")
        }

        if lowRatio < 0.4 {
            adj -= 8
            findings.append("Anomalous spectral energy distribution — deviates from natural photographic characteristics.")
        }

        return FFTContrib(adj: adj, findings: findings)
    }

    // MARK: - High/Low Ratio

    private func analyzeFrequencyRatio(data: [Float], width: Int, height: Int, fftSize: Int) -> FFTContrib {
        // 2D-ish approach: compare energy in central vs outer regions of spectrum
        var lowEnergy = 0.0
        var highEnergy = 0.0
        let cols = min(width, fftSize)
        let colSampleRows = min(height, 32)

        for row in 0..<colSampleRows {
            let start = row * width
            let end   = start + cols
            guard end <= data.count else { continue }

            let rowSlice = Array(data[start..<start+cols])
            let padded = padToPow2(rowSlice)
            let mag = computeRowFFT(row: padded)
            guard mag.count >= 4 else { continue }

            for i in 0..<mag.count {
                let energy = Double(mag[i])
                if i < mag.count / 4 { lowEnergy += energy }
                else { highEnergy += energy }
            }
        }

        let ratio = (lowEnergy + highEnergy) > 0 ? lowEnergy / (lowEnergy + highEnergy) : 0
        var findings: [String] = []
        var adj = 0.0

        if ratio > 0.85 {
            adj -= 5
            findings.append("High concentration of spectral energy in low frequencies — possible AI over-smoothing.")
        } else if ratio < 0.50 {
            adj -= 5
            findings.append("Unusually distributed spectral energy — possible synthetic texture generation.")
        }

        return FFTContrib(adj: adj, findings: findings)
    }

    // MARK: - Periodic Artifact Detection

    private func detectPeriodicArtifacts(data: [Float], width: Int, height: Int, fftSize: Int) -> FFTContrib {
        // Detect spectral spikes that might indicate GAN grid artifacts
        // or upsampling patterns common in some generators
        let sampleRow = height / 2
        let start = sampleRow * width
        guard start + fftSize <= data.count else { return FFTContrib(adj: 0, findings: []) }

        let rowSlice = Array(data[start..<start+fftSize])
        let mag = computeRowFFT(row: rowSlice)
        guard mag.count > 8 else { return FFTContrib(adj: 0, findings: []) }

        // Look for anomalous spikes (energy >> mean)
        let meanEnergy = mag.reduce(0.0, +) / Float(mag.count)
        let spikes = mag.filter { $0 > meanEnergy * 8.0 }
        let spikeRatio = Double(spikes.count) / Double(mag.count)

        var findings: [String] = []
        var adj = 0.0

        if spikeRatio > 0.05 {
            adj -= 12
            findings.append("Periodic spectral spikes detected — pattern consistent with GAN grid artifacts or upsampling from lower-resolution synthetic source.")
        } else if spikeRatio < 0.01 {
            adj += 4
            findings.append("Spectral analysis shows no periodic artifacts — expected for authentic photographs.")
        }

        return FFTContrib(adj: adj, findings: findings)
    }

    // MARK: - Helpers

    private func padToPow2(_ input: [Float]) -> [Float] {
        var n = 1
        while n < input.count { n *= 2 }
        return input + [Float](repeating: 0, count: n - input.count)
    }
}
