import SwiftUI

struct AnalysisGridView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme

    private let columns = [
        GridItem(.adaptive(minimum: 200, maximum: 280), spacing: 16)
    ]

    var body: some View {
        VStack(spacing: 0) {
            // Summary bar
            if !appState.completedItems.isEmpty {
                summaryBar
                    .transition(.move(edge: .top).combined(with: .opacity))
            }

            ScrollView {
                LazyVGrid(columns: columns, spacing: 16) {
                    ForEach(appState.imageItems) { item in
                        ImageTileView(item: item)
                            .onTapGesture {
                                appState.selectItem(item)
                            }
                    }

                    // Add more button (if < 12)
                    if appState.imageItems.count < 12 {
                        addMoreTile
                    }
                }
                .padding(20)
            }

            // Bottom action bar
            if appState.canAnalyze {
                analyzeBar
            }
        }
        .animation(.easeInOut(duration: 0.2), value: appState.completedItems.count)
    }

    // MARK: - Summary Bar

    private var summaryBar: some View {
        HStack(spacing: 20) {
            SummaryPill(
                value: "\(appState.completedItems.count)/\(appState.imageItems.count)",
                label: "Analyzed",
                icon: "checkmark.circle.fill",
                color: .authenticGreen
            )

            if let avg = appState.averageScore {
                SummaryPill(
                    value: "\(Int(avg.rounded()))%",
                    label: "Avg. Score",
                    icon: "chart.bar.fill",
                    color: avg.authenticityColor
                )
            }

            if !appState.flaggedItems.isEmpty {
                SummaryPill(
                    value: "\(appState.flaggedItems.count)",
                    label: "Flagged",
                    icon: "exclamationmark.triangle.fill",
                    color: .aiRed
                )
            }

            Spacer()

            Button {
                withAnimation { appState.clearAll() }
            } label: {
                Label("Clear All", systemImage: "trash")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial)
    }

    // MARK: - Add More Tile

    private var addMoreTile: some View {
        Button {
            appState.triggerFilePicker()
        } label: {
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.secondary.opacity(0.07))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.secondary.opacity(0.2), style: StrokeStyle(lineWidth: 1.5, dash: [6, 4]))
                )
                .overlay(
                    VStack(spacing: 8) {
                        Image(systemName: "plus.circle")
                            .font(.system(size: 26, weight: .thin))
                            .foregroundColor(.secondary)
                        Text("Add Photo")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.secondary)
                        Text("\(appState.imageItems.count)/12")
                            .font(.system(size: 10))
                            .foregroundColor(.secondary.opacity(0.6))
                    }
                )
                .frame(height: 220)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Analyze Bar

    private var analyzeBar: some View {
        VStack(spacing: 0) {
            Divider()
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(appState.imageItems.count) photo\(appState.imageItems.count == 1 ? "" : "s") ready")
                        .font(.system(size: 13, weight: .semibold))
                    if appState.deepAnalysisMode {
                        Label("Deep Analysis Mode", systemImage: "sparkles")
                            .font(.system(size: 11))
                            .foregroundColor(.accentTeal)
                    }
                }
                Spacer()
                Button {
                    appState.analyzeAll()
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "sparkle.magnifyingglass")
                        Text("Analyze All")
                            .font(.system(size: 13, weight: .semibold))
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 9)
                    .background(Color.accentTeal)
                    .foregroundColor(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                }
                .buttonStyle(.plain)
                .shadow(color: Color.accentTeal.opacity(0.3), radius: 8, y: 3)
                .keyboardShortcut(.return, modifiers: .command)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background(.ultraThinMaterial)
        }
    }
}

// MARK: - Summary Pill

struct SummaryPill: View {
    let value: String
    let label: String
    let icon: String
    let color: Color

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(color)
            VStack(alignment: .leading, spacing: 0) {
                Text(value)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.primary)
                Text(label)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    AnalysisGridView()
        .environmentObject(AppState())
        .frame(width: 900, height: 640)
}
