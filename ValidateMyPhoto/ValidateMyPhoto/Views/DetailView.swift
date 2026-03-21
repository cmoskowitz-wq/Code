import SwiftUI

struct DetailView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme
    @State private var selectedTab: DetailTab = .insights

    enum DetailTab: String, CaseIterable {
        case insights = "Insights"
        case subScores = "Sub-Scores"
        case fileInfo = "File Info"
    }

    private var item: ImageItem? { appState.selectedItem }
    private var result: AnalysisResult? { item?.result }

    var body: some View {
        if let item = item {
            HStack(spacing: 0) {
                // Left: Image panel
                imagePanel(item: item)
                    .frame(maxWidth: .infinity)

                Divider()

                // Right: Analysis panel
                analysisPanel(item: item)
                    .frame(width: 360)
            }
        } else {
            Text("No image selected")
                .foregroundColor(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Image Panel

    private func imagePanel(item: ImageItem) -> some View {
        VStack(spacing: 0) {
            // Navigation strip
            if appState.imageItems.count > 1 {
                navigationStrip
                    .padding(.vertical, 8)
            }

            // Main image
            if let thumb = item.thumbnail {
                Image(nsImage: thumb)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .padding(20)
            } else {
                ProgressView("Loading…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

            // Score bar at bottom of image
            if let result = result {
                imageScoreBar(result: result)
            }
        }
    }

    private var navigationStrip: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(appState.imageItems) { navItem in
                    Button {
                        appState.selectedItemID = navItem.id
                    } label: {
                        Group {
                            if let thumb = navItem.thumbnail {
                                Image(nsImage: thumb)
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                            } else {
                                Rectangle().fill(Color.secondary.opacity(0.2))
                            }
                        }
                        .frame(width: 44, height: 44)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(navItem.id == appState.selectedItemID
                                        ? Color.accentTeal : Color.clear, lineWidth: 2)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 20)
        }
    }

    private func imageScoreBar(result: AnalysisResult) -> some View {
        HStack(spacing: 16) {
            ScoreBadge(score: result.authenticityScore, size: .medium)

            VStack(alignment: .leading, spacing: 4) {
                ClassificationBadge(classification: result.classification)

                Text("Confidence: \(Int(result.confidenceInterval.lowerBound))–\(Int(result.confidenceInterval.upperBound))%")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(result.imageName)
                    .font(.system(size: 12, weight: .semibold))
                    .lineLimit(1)
                Text("\(result.imageWidth)×\(result.imageHeight) · \(result.fileFormat)")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                Text("Analyzed in \(String(format: "%.1f", result.analysisDuration))s")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
        .background(.ultraThinMaterial)
    }

    // MARK: - Analysis Panel

    private func analysisPanel(item: ImageItem) -> some View {
        VStack(spacing: 0) {
            // Tab bar
            tabBar

            Divider()

            // Content
            ScrollView {
                if let result = result {
                    Group {
                        switch selectedTab {
                        case .insights:
                            InsightsPanel(result: result)
                        case .subScores:
                            SubScoresPanel(result: result)
                        case .fileInfo:
                            FileInfoPanel(result: result)
                        }
                    }
                    .padding(20)
                    .transition(.opacity)
                    .animation(.easeInOut(duration: 0.15), value: selectedTab)
                } else {
                    emptyAnalysisState(item: item)
                        .padding(20)
                }
            }
        }
    }

    private var tabBar: some View {
        HStack(spacing: 0) {
            ForEach(DetailTab.allCases, id: \.self) { tab in
                Button {
                    withAnimation { selectedTab = tab }
                } label: {
                    Text(tab.rawValue)
                        .font(.system(size: 12, weight: selectedTab == tab ? .semibold : .regular))
                        .foregroundColor(selectedTab == tab ? .accentTeal : .secondary)
                        .padding(.vertical, 10)
                        .frame(maxWidth: .infinity)
                        .overlay(alignment: .bottom) {
                            Rectangle()
                                .fill(selectedTab == tab ? Color.accentTeal : Color.clear)
                                .frame(height: 2)
                        }
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - Empty State

    private func emptyAnalysisState(item: ImageItem) -> some View {
        VStack(spacing: 16) {
            Spacer(minLength: 40)
            switch item.state {
            case .idle:
                Image(systemName: "sparkle.magnifyingglass")
                    .font(.system(size: 36, weight: .thin))
                    .foregroundColor(.secondary)
                Text("Ready to Analyze")
                    .font(.system(size: 15, weight: .semibold))
                Text("Press ⌘↩ or click Analyze All to start.")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)

            case .analyzing(let progress):
                CircularProgress(progress: progress, size: 52)
                Text("Analyzing…")
                    .font(.system(size: 15, weight: .semibold))
                Text("\(Int(progress * 100))% complete")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

            case .failed(let error):
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 36, weight: .thin))
                    .foregroundColor(.aiRed)
                Text("Analysis Failed")
                    .font(.system(size: 15, weight: .semibold))
                Text(error)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                Button("Retry") {
                    appState.reanalyzeItem(item)
                }
                .buttonStyle(.bordered)

            default:
                EmptyView()
            }
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Insights Panel

struct InsightsPanel: View {
    let result: AnalysisResult

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Why This Score?")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(.primary)

            ForEach(result.keyFindings, id: \.self) { finding in
                InsightRow(text: finding)
            }

            if result.keyFindings.isEmpty {
                Text("No specific findings to report.")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }

            // Disclaimer
            DisclaimerView()
                .padding(.top, 8)
        }
    }
}

struct InsightRow: View {
    let text: String

    private var icon: String {
        if text.lowercased().contains("detected") || text.lowercased().contains("suspicious") ||
           text.lowercased().contains("unusual") || text.lowercased().contains("anomalous") ||
           text.lowercased().contains("inconsist") || text.lowercased().contains("missing") ||
           text.lowercased().contains("absent") {
            return "exclamationmark.circle.fill"
        }
        if text.lowercased().contains("consistent") || text.lowercased().contains("natural") ||
           text.lowercased().contains("identified") || text.lowercased().contains("found") ||
           text.lowercased().contains("present") || text.lowercased().contains("within") {
            return "checkmark.circle.fill"
        }
        return "info.circle.fill"
    }

    private var iconColor: Color {
        if icon == "exclamationmark.circle.fill" { return .uncertainYellow }
        if icon == "checkmark.circle.fill" { return .authenticGreen }
        return .secondary
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundColor(iconColor)
                .padding(.top, 1)

            Text(text)
                .font(.system(size: 12))
                .foregroundColor(.primary.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Sub-Scores Panel

struct SubScoresPanel: View {
    let result: AnalysisResult

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Score Breakdown")
                .font(.system(size: 14, weight: .semibold))

            ForEach(result.subScores) { sub in
                SubScoreRow(subScore: sub)
            }
        }
    }
}

struct SubScoreRow: View {
    let subScore: SubScore
    @State private var expanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                withAnimation(.spring(response: 0.25)) { expanded.toggle() }
            } label: {
                HStack(spacing: 10) {
                    Image(systemName: subScore.category.icon)
                        .font(.system(size: 13))
                        .foregroundColor(.accentTeal)
                        .frame(width: 18)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(subScore.category.rawValue)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.primary)

                        // Progress bar
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(Color.secondary.opacity(0.15))
                                    .frame(height: 4)
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(subScore.score.authenticityColor)
                                    .frame(width: geo.size.width * subScore.score / 100, height: 4)
                                    .animation(.spring(response: 0.6), value: subScore.score)
                            }
                        }
                        .frame(height: 4)
                    }

                    Spacer()

                    Text("\(Int(subScore.score.rounded()))%")
                        .font(.system(size: 13, weight: .bold, design: .rounded))
                        .foregroundColor(subScore.score.authenticityColor)
                        .frame(width: 36, alignment: .trailing)

                    Image(systemName: "chevron.right")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                        .rotationEffect(.degrees(expanded ? 90 : 0))
                }
            }
            .buttonStyle(.plain)

            if expanded {
                VStack(alignment: .leading, spacing: 6) {
                    Text(subScore.category.description)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .padding(.bottom, 2)

                    ForEach(subScore.insights, id: \.self) { insight in
                        HStack(alignment: .top, spacing: 6) {
                            Circle()
                                .fill(Color.secondary.opacity(0.5))
                                .frame(width: 4, height: 4)
                                .padding(.top, 5)
                            Text(insight)
                                .font(.system(size: 11))
                                .foregroundColor(.primary.opacity(0.8))
                        }
                    }
                }
                .padding(.leading, 28)
                .padding(.vertical, 6)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }

            Divider()
        }
    }
}

// MARK: - File Info Panel

struct FileInfoPanel: View {
    let result: AnalysisResult

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("File Information")
                .font(.system(size: 14, weight: .semibold))

            FileInfoRow(label: "Filename", value: result.imageName)
            FileInfoRow(label: "Format", value: result.fileFormat)
            FileInfoRow(label: "Dimensions", value: "\(result.imageWidth) × \(result.imageHeight) px")
            FileInfoRow(label: "File Size", value: formatFileSize(result.fileSize))
            FileInfoRow(label: "Analyzed", value: formatDate(result.analyzedAt))
            FileInfoRow(label: "Duration", value: String(format: "%.2f seconds", result.analysisDuration))

            if let ela = result.elaResult {
                Divider().padding(.vertical, 4)
                Text("Error Level Analysis")
                    .font(.system(size: 13, weight: .semibold))
                FileInfoRow(label: "ELA Suspicion", value: "\(Int(ela.suspicionScore))%")
                FileInfoRow(label: "Hotspot Pixels", value: "\(ela.hotspotCount.formatted())")
                FileInfoRow(label: "Max Intensity", value: String(format: "%.1f", ela.maxIntensity))
            }
        }
    }

    private func formatFileSize(_ bytes: Int64) -> String {
        let mb = Double(bytes) / 1_048_576
        if mb >= 1 { return String(format: "%.1f MB", mb) }
        return String(format: "%.0f KB", Double(bytes) / 1024)
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

struct FileInfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .font(.system(size: 12))
                .foregroundColor(.secondary)
                .frame(width: 100, alignment: .leading)
            Text(value)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.primary)
                .lineLimit(1)
                .truncationMode(.middle)
        }
    }
}

// MARK: - Disclaimer

struct DisclaimerView: View {
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "info.circle")
                .font(.system(size: 11))
                .foregroundColor(.secondary)
                .padding(.top, 1)
            Text("Results are probabilistic and should not be used as sole evidence in legal decisions. No detection system guarantees 100% accuracy.")
                .font(.system(size: 10))
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color.secondary.opacity(0.07))
        )
    }
}
