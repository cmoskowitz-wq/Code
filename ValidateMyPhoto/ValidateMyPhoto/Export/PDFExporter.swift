import Foundation
import AppKit
import CoreGraphics
import ImageIO

// MARK: - PDF Exporter

actor PDFExporter {

    func export(results: [AnalysisResult]) async throws -> URL {
        let outputURL = try resolveOutputURL(prefix: "ValidateMyPhoto-Report", ext: "pdf")
        let pageRect = CGRect(x: 0, y: 0, width: 612, height: 792)  // US Letter

        guard let consumer = CGDataConsumer(url: outputURL as CFURL),
              let pdfCtx = CGContext(consumer: consumer, mediaBox: nil, nil) else {
            throw ExportError.creationFailed
        }

        // Cover page
        drawCoverPage(ctx: pdfCtx, pageRect: pageRect, results: results)

        // One page per result
        for result in results {
            drawResultPage(ctx: pdfCtx, pageRect: pageRect, result: result)
        }

        pdfCtx.closePDF()
        return outputURL
    }

    // MARK: - Cover Page

    private func drawCoverPage(ctx: CGContext, pageRect: CGRect, results: [AnalysisResult]) {
        let info: [String: Any] = [kCGPDFContextTitle as String: "Validate My Photo Report"]
        ctx.beginPDFPage(info as CFDictionary)

        // Background
        ctx.setFillColor(CGColor(red: 0.06, green: 0.06, blue: 0.08, alpha: 1))
        ctx.fill(pageRect)

        // Title
        drawText(ctx: ctx, text: "Validate My Photo", x: 60, y: 680,
                 fontSize: 26, weight: .bold, color: .white)
        drawText(ctx: ctx, text: "Authenticity Analysis Report", x: 60, y: 650,
                 fontSize: 14, weight: .regular, color: CGColor(red: 0.5, green: 0.5, blue: 0.5, alpha: 1))
        drawText(ctx: ctx, text: "Mosko Photo Labs", x: 60, y: 625,
                 fontSize: 12, weight: .medium, color: CGColor(red: 0.0, green: 0.72, blue: 0.87, alpha: 1))

        // Summary box
        let boxRect = CGRect(x: 60, y: 480, width: 492, height: 120)
        ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 0.05))
        roundedRect(ctx: ctx, rect: boxRect, radius: 10)

        let analyzed = results.count
        let avgScore = results.isEmpty ? 0 : results.map(\.authenticityScore).reduce(0, +) / Double(results.count)
        let flagged  = results.filter { $0.classification == .likelyAIGenerated }.count

        drawText(ctx: ctx, text: "Images Analyzed: \(analyzed)", x: 80, y: 572, fontSize: 13, color: .white)
        drawText(ctx: ctx, text: "Average Score: \(Int(avgScore.rounded()))%", x: 80, y: 548, fontSize: 13, color: .white)
        drawText(ctx: ctx, text: "Flagged as AI-Generated: \(flagged)", x: 80, y: 524, fontSize: 13, color: .white)
        drawText(ctx: ctx, text: "Generated: \(formatDate(Date()))", x: 80, y: 500, fontSize: 11,
                 color: CGColor(red: 0.5, green: 0.5, blue: 0.5, alpha: 1))

        // Disclaimer
        drawText(ctx: ctx, text: "Results are probabilistic. Not for use as sole legal evidence.", x: 60, y: 80,
                 fontSize: 9, color: CGColor(red: 0.4, green: 0.4, blue: 0.4, alpha: 1))

        ctx.endPDFPage()
    }

    // MARK: - Result Page

    private func drawResultPage(ctx: CGContext, pageRect: CGRect, result: AnalysisResult) {
        ctx.beginPDFPage(nil)

        // Background
        ctx.setFillColor(CGColor(red: 0.06, green: 0.06, blue: 0.08, alpha: 1))
        ctx.fill(pageRect)

        // Image thumbnail
        if let cgImage = loadThumbnail(url: result.imageURL, maxSize: 180) {
            let thumbRect = CGRect(x: 60, y: 580, width: 160, height: 160)
            roundedClip(ctx: ctx, rect: thumbRect, radius: 8)
            ctx.draw(cgImage, in: thumbRect)
            ctx.resetClip()
        }

        // Image info
        drawText(ctx: ctx, text: result.imageName, x: 240, y: 728, fontSize: 14, weight: .bold, color: .white)
        drawText(ctx: ctx, text: "\(result.imageWidth)×\(result.imageHeight) · \(result.fileFormat) · \(formatFileSize(result.fileSize))",
                 x: 240, y: 708, fontSize: 11, color: CGColor(red: 0.5, green: 0.5, blue: 0.5, alpha: 1))

        // Score
        drawText(ctx: ctx, text: "Authenticity Score: \(Int(result.authenticityScore.rounded()))%",
                 x: 240, y: 680, fontSize: 13, weight: .bold, color: classificationColor(result.classification))
        drawText(ctx: ctx, text: result.classification.rawValue,
                 x: 240, y: 658, fontSize: 12, color: classificationColor(result.classification))

        // Sub-scores
        var y = 540.0
        drawText(ctx: ctx, text: "Score Breakdown", x: 60, y: y, fontSize: 12, weight: .bold, color: .white)
        y -= 22

        for sub in result.subScores {
            let label = "\(sub.category.rawValue): \(Int(sub.score.rounded()))%"
            drawText(ctx: ctx, text: label, x: 60, y: y, fontSize: 11, color: .white)
            // Bar
            ctx.setFillColor(CGColor(red: 0.2, green: 0.2, blue: 0.22, alpha: 1))
            ctx.fill(CGRect(x: 260, y: y - 2, width: 200, height: 10))
            let barWidth = sub.score / 100.0 * 200
            ctx.setFillColor(scoreBarColor(sub.score))
            ctx.fill(CGRect(x: 260, y: y - 2, width: barWidth, height: 10))
            y -= 20
        }

        // Key findings
        y -= 10
        drawText(ctx: ctx, text: "Key Findings", x: 60, y: y, fontSize: 12, weight: .bold, color: .white)
        y -= 20

        for finding in result.keyFindings.prefix(10) {
            let truncated = finding.count > 100 ? String(finding.prefix(100)) + "…" : finding
            drawText(ctx: ctx, text: "• " + truncated, x: 60, y: y, fontSize: 9,
                     color: CGColor(red: 0.75, green: 0.75, blue: 0.75, alpha: 1))
            y -= 14
            if y < 80 { break }
        }

        ctx.endPDFPage()
    }

    // MARK: - Drawing Helpers

    private func drawText(ctx: CGContext, text: String, x: Double, y: Double,
                          fontSize: CGFloat, weight: NSFont.Weight = .regular, color: CGColor) {
        let font = NSFont.systemFont(ofSize: fontSize, weight: weight)
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor(cgColor: color) ?? .white
        ]
        let attrStr = NSAttributedString(string: text, attributes: attrs)
        let framesetter = CTFramesetterCreateWithAttributedString(attrStr)
        let path = CGPath(rect: CGRect(x: x, y: y, width: 500, height: 30), transform: nil)
        let frame = CTFramesetterCreateFrame(framesetter, CFRangeMake(0, attrStr.length), path, nil)
        ctx.saveGState()
        ctx.textMatrix = .identity
        CTFrameDraw(frame, ctx)
        ctx.restoreGState()
    }

    private func roundedRect(ctx: CGContext, rect: CGRect, radius: CGFloat) {
        let path = CGMutablePath()
        path.addRoundedRect(in: rect, cornerWidth: radius, cornerHeight: radius)
        ctx.addPath(path)
        ctx.fillPath()
    }

    private func roundedClip(ctx: CGContext, rect: CGRect, radius: CGFloat) {
        let path = CGMutablePath()
        path.addRoundedRect(in: rect, cornerWidth: radius, cornerHeight: radius)
        ctx.addPath(path)
        ctx.clip()
    }

    private func classificationColor(_ c: AuthenticityClassification) -> CGColor {
        switch c {
        case .likelyAuthentic:   return CGColor(red: 0.2,  green: 0.78, blue: 0.35, alpha: 1)
        case .uncertain:         return CGColor(red: 0.98, green: 0.78, blue: 0.18, alpha: 1)
        case .likelyAIGenerated: return CGColor(red: 0.95, green: 0.27, blue: 0.27, alpha: 1)
        }
    }

    private func scoreBarColor(_ score: Double) -> CGColor {
        if score >= 75 { return CGColor(red: 0.2, green: 0.78, blue: 0.35, alpha: 1) }
        if score >= 45 { return CGColor(red: 0.98, green: 0.78, blue: 0.18, alpha: 1) }
        return CGColor(red: 0.95, green: 0.27, blue: 0.27, alpha: 1)
    }

    private func loadThumbnail(url: URL, maxSize: Int) -> CGImage? {
        guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
        let opts: [CFString: Any] = [
            kCGImageSourceThumbnailMaxPixelSize: maxSize,
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true
        ]
        return CGImageSourceCreateThumbnailAtIndex(src, 0, opts as CFDictionary)
    }

    private func formatFileSize(_ bytes: Int64) -> String {
        let mb = Double(bytes) / 1_048_576
        return mb >= 1 ? String(format: "%.1f MB", mb) : String(format: "%.0f KB", Double(bytes) / 1024)
    }

    private func formatDate(_ date: Date) -> String {
        let fmt = DateFormatter(); fmt.dateStyle = .long; fmt.timeStyle = .short
        return fmt.string(from: date)
    }

    private func resolveOutputURL(prefix: String, ext: String) throws -> URL {
        let downloads = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first!
        let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd_HH-mm-ss"
        let name = "\(prefix)_\(formatter.string(from: Date())).\(ext)"
        return downloads.appendingPathComponent(name)
    }
}

enum ExportError: LocalizedError {
    case creationFailed
    var errorDescription: String? { "Failed to create export file." }
}
