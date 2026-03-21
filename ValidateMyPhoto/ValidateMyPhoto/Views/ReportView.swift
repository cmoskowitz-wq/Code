import SwiftUI

struct ReportView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme
    @State private var isExportingPDF = false
    @State private var isExportingCSV = false
    @State private var exportMessage: String?
    @State private var showExportMessage = false

    private var results: [AnalysisResult] {
        appState.completedItems.compactMap(\.result)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                reportHeader
                summarySection
                if !results.isEmpty {
                    imageResultsSection
                }
                disclaimerSection
            }
            .padding(32)
        }
        .safeAreaInset(edge: .bottom) {
            exportBar
        }
        .overlay(alignment: .top) {
            if showExportMessage, let msg = exportMessage {
                Text(msg)
                    .font(.system(size: 12, weight: .medium))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Capsule().fill(Color.authenticGreen))
                    .foregroundColor(.white)
                    .padding(.top, 8)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.spring(response: 0.3), value: showExportMessage)
    }

    // MARK: - Header

    private var reportHeader: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 4) {
                Label("Analysis Report", systemImage: "doc.text.fill")
                    .font(.system(size: 22, weight: .bold))

                Text("Mosko Photo Labs · Validate My Photo")
                    .font(.system(size: 12))
                    .foregroundColor(.accentTeal)

                Text(formatDate(Date()))
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }

            Spacer()

            Image(systemName: "camera.viewfinder")
                .font(.system(size: 40, weight: .thin))
                .foregroundStyle(
                    LinearGradient(colors: [.accentTeal, .blue],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                )
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(colorScheme == .dark ? Color.white.opacity(0.05) : Color.black.opacity(0.03))
        )
    }

    // MARK: - Summary

    private var summarySection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Summary")
                .font(.system(size: 16, weight: .semibold))

            HStack(spacing: 16) {
                SummaryCard(
                    title: "Images Analyzed",
                    value: "\(results.count)",
                    icon: "photo.stack",
                    color: .accentTeal
                )

                if let avg = appState.averageScore {
                    SummaryCard(
                        title: "Average Score",
                        value: "\(Int(avg.rounded()))%",
                        icon: "chart.bar.fill",
                        color: avg.authenticityColor
                    )
                }

                SummaryCard(
                    title: "Flagged",
                    value: "\(appState.flaggedItems.count)",
                    icon: "exclamationmark.triangle.fill",
                    color: appState.flaggedItems.isEmpty ? .secondary : .aiRed
                )

                let authentic = results.filter { $0.classification == .likelyAuthentic }.count
                SummaryCard(
                    title: "Likely Authentic",
                    value: "\(authentic)",
                    icon: "checkmark.seal.fill",
                    color: .authenticGreen
                )
            }
        }
    }

    // MARK: - Image Results

    private var imageResultsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Results")
                .font(.system(size: 16, weight: .semibold))

            ForEach(results) { result in
                ReportImageRow(result: result)
            }
        }
    }

    // MARK: - Disclaimer

    private var disclaimerSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Disclaimer", systemImage: "exclamationmark.shield")
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.secondary)

            Text("Validate My Photo uses probabilistic analysis. Results should be considered as one factor among many in any authentication workflow. This report does not constitute legal evidence. No AI detection system can guarantee 100% accuracy. Mosko Photo Labs makes no warranties regarding detection outcomes.")
                .font(.system(size: 11))
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.secondary.opacity(0.07))
        )
    }

    // MARK: - Export Bar

    private var exportBar: some View {
        VStack(spacing: 0) {
            Divider()
            HStack(spacing: 12) {
                Text("\(results.count) result\(results.count == 1 ? "" : "s") ready to export")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                Spacer()

                Button {
                    exportCSV()
                } label: {
                    Label("Export CSV", systemImage: "tablecells")
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 7)
                }
                .buttonStyle(.bordered)
                .disabled(results.isEmpty || isExportingCSV)

                Button {
                    exportPDF()
                } label: {
                    Label(isExportingPDF ? "Generating…" : "Export PDF", systemImage: "doc.fill")
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 7)
                        .background(Color.accentTeal)
                        .foregroundColor(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                .buttonStyle(.plain)
                .disabled(results.isEmpty || isExportingPDF)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background(.ultraThinMaterial)
        }
    }

    // MARK: - Export Actions

    private func exportPDF() {
        isExportingPDF = true
        Task {
            do {
                let url = try await PDFExporter().export(results: results)
                await MainActor.run {
                    isExportingPDF = false
                    NSWorkspace.shared.open(url)
                    showSuccess("PDF exported successfully.")
                }
            } catch {
                await MainActor.run {
                    isExportingPDF = false
                    appState.postError("PDF export failed: \(error.localizedDescription)")
                }
            }
        }
    }

    private func exportCSV() {
        isExportingCSV = true
        Task {
            do {
                let url = try await CSVExporter().export(results: results)
                await MainActor.run {
                    isExportingCSV = false
                    NSWorkspace.shared.open(url)
                    showSuccess("CSV exported successfully.")
                }
            } catch {
                await MainActor.run {
                    isExportingCSV = false
                    appState.postError("CSV export failed: \(error.localizedDescription)")
                }
            }
        }
    }

    private func showSuccess(_ msg: String) {
        exportMessage = msg
        withAnimation { showExportMessage = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            withAnimation { showExportMessage = false }
        }
    }

    private func formatDate(_ date: Date) -> String {
        let fmt = DateFormatter()
        fmt.dateStyle = .long
        fmt.timeStyle = .short
        return fmt.string(from: date)
    }
}

// MARK: - Summary Card

struct SummaryCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(color)

            Text(value)
                .font(.system(size: 26, weight: .bold, design: .rounded))
                .foregroundColor(.primary)

            Text(title)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.secondary)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(colorScheme == .dark ? Color.white.opacity(0.06) : Color.black.opacity(0.03))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(color.opacity(0.2), lineWidth: 1)
        )
    }
}

// MARK: - Report Image Row

struct ReportImageRow: View {
    let result: AnalysisResult
    @State private var expanded = false

    var body: some View {
        VStack(spacing: 0) {
            Button {
                withAnimation(.spring(response: 0.25)) { expanded.toggle() }
            } label: {
                HStack(spacing: 14) {
                    // Thumbnail
                    AsyncImage(url: result.imageURL) { image in
                        image.resizable().aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Rectangle().fill(Color.secondary.opacity(0.1))
                    }
                    .frame(width: 54, height: 54)
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                    // Name + classification
                    VStack(alignment: .leading, spacing: 4) {
                        Text(result.imageName)
                            .font(.system(size: 13, weight: .semibold))
                            .lineLimit(1)
                        ClassificationBadge(classification: result.classification, compact: true)
                    }

                    Spacer()

                    // Score
                    ScoreBadge(score: result.authenticityScore, size: .small)

                    Image(systemName: "chevron.right")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .rotationEffect(.degrees(expanded ? 90 : 0))
                }
                .padding(14)
            }
            .buttonStyle(.plain)

            if expanded {
                VStack(alignment: .leading, spacing: 8) {
                    Divider()
                    ForEach(result.keyFindings.prefix(6), id: \.self) { finding in
                        InsightRow(text: finding)
                    }
                    if result.keyFindings.count > 6 {
                        Text("+ \(result.keyFindings.count - 6) more findings")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.bottom, 12)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.secondary.opacity(0.05))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(result.classification.color.opacity(0.2), lineWidth: 1)
        )
    }
}
