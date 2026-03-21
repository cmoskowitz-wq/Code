import Foundation

// MARK: - CSV Exporter

actor CSVExporter {

    func export(results: [AnalysisResult]) async throws -> URL {
        let outputURL = try resolveOutputURL()
        let csv = buildCSV(results: results)
        try csv.write(to: outputURL, atomically: true, encoding: .utf8)
        return outputURL
    }

    private func buildCSV(results: [AnalysisResult]) -> String {
        var rows: [String] = []

        // Header
        let header = [
            "Filename",
            "Authenticity Score (%)",
            "Classification",
            "Confidence Interval",
            "Metadata Score",
            "Pixel Forensics Score",
            "Frequency Analysis Score",
            "Lighting Consistency Score",
            "AI Pattern Score",
            "Format",
            "Dimensions",
            "File Size (MB)",
            "Analysis Duration (s)",
            "Key Findings",
            "Analyzed At"
        ].joined(separator: ",")
        rows.append(header)

        let df = DateFormatter(); df.dateStyle = .short; df.timeStyle = .medium

        for r in results {
            let subMap = Dictionary(uniqueKeysWithValues: r.subScores.map { ($0.category, $0.score) })

            let findings = r.keyFindings
                .map { $0.replacingOccurrences(of: "\"", with: "'") }
                .joined(separator: "; ")

            let row: [String] = [
                escape(r.imageName),
                String(format: "%.1f", r.authenticityScore),
                escape(r.classification.rawValue),
                "\(Int(r.confidenceInterval.lowerBound))–\(Int(r.confidenceInterval.upperBound))%",
                scoreStr(subMap[.metadata]),
                scoreStr(subMap[.pixelForensics]),
                scoreStr(subMap[.frequencyDomain]),
                scoreStr(subMap[.lightingConsistency]),
                scoreStr(subMap[.aiPatternMatch]),
                r.fileFormat,
                "\(r.imageWidth)x\(r.imageHeight)",
                String(format: "%.2f", Double(r.fileSize) / 1_048_576),
                String(format: "%.2f", r.analysisDuration),
                escape(findings),
                escape(df.string(from: r.analyzedAt))
            ]
            rows.append(row.joined(separator: ","))
        }

        return rows.joined(separator: "\n")
    }

    private func escape(_ str: String) -> String {
        let needsQuoting = str.contains(",") || str.contains("\"") || str.contains("\n")
        if needsQuoting {
            return "\"" + str.replacingOccurrences(of: "\"", with: "\"\"") + "\""
        }
        return str
    }

    private func scoreStr(_ score: Double?) -> String {
        guard let s = score else { return "" }
        return String(format: "%.1f", s)
    }

    private func resolveOutputURL() throws -> URL {
        let downloads = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first!
        let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd_HH-mm-ss"
        let name = "ValidateMyPhoto_\(formatter.string(from: Date())).csv"
        return downloads.appendingPathComponent(name)
    }
}
