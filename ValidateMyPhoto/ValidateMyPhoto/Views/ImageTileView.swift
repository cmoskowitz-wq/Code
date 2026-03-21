import SwiftUI

struct ImageTileView: View {
    @ObservedObject var item: ImageItem
    @Environment(\.colorScheme) var colorScheme
    @State private var isHovered = false

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            // Thumbnail
            thumbnailView

            // Score overlay
            if let result = item.result {
                scoreOverlay(result: result)
            }

            // Analyzing overlay
            if case .analyzing(let progress) = item.state {
                analyzingOverlay(progress: progress)
            }

            // Failed overlay
            if case .failed(let msg) = item.state {
                failedOverlay(message: msg)
            }

            // Remove button
            if isHovered {
                removeButton
                    .transition(.opacity.combined(with: .scale(scale: 0.8)))
            }
        }
        .frame(height: 220)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(borderColor, lineWidth: isHovered ? 1.5 : 0.5)
        )
        .shadow(color: shadowColor, radius: isHovered ? 12 : 4, y: isHovered ? 6 : 2)
        .scaleEffect(isHovered ? 1.01 : 1.0)
        .animation(.spring(response: 0.2), value: isHovered)
        .onHover { isHovered = $0 }
    }

    // MARK: - Thumbnail

    private var thumbnailView: some View {
        Group {
            if let thumb = item.thumbnail {
                Image(nsImage: thumb)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Rectangle()
                    .fill(Color.secondary.opacity(0.1))
                    .overlay(
                        ProgressView()
                            .scaleEffect(0.7)
                    )
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Score Overlay

    private func scoreOverlay(result: AnalysisResult) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                ClassificationBadge(classification: result.classification, compact: true)

                Text(item.fileName)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.white.opacity(0.8))
                    .lineLimit(1)
                    .truncationMode(.middle)
            }

            Spacer()

            ScoreBadge(score: result.authenticityScore, size: .small, showLabel: false)
        }
        .padding(10)
        .background(
            LinearGradient(
                colors: [.black.opacity(0.0), .black.opacity(0.75)],
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }

    // MARK: - Analyzing Overlay

    private func analyzingOverlay(progress: Double) -> some View {
        ZStack {
            Rectangle()
                .fill(.ultraThinMaterial)

            VStack(spacing: 10) {
                CircularProgress(progress: progress, size: 40)

                Text(progress < 0.5 ? "Analyzing…" : progress < 0.85 ? "Processing…" : "Finalizing…")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.secondary)
            }
        }
    }

    // MARK: - Failed Overlay

    private func failedOverlay(message: String) -> some View {
        ZStack {
            Rectangle()
                .fill(Color.aiRed.opacity(0.15))

            VStack(spacing: 8) {
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 22, weight: .thin))
                    .foregroundColor(.aiRed)
                Text("Analysis failed")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.aiRed)
                Text(message)
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 8)
            }
        }
    }

    // MARK: - Remove Button

    private var removeButton: some View {
        VStack {
            HStack {
                Spacer()
                Button {
                    withAnimation(.spring(response: 0.2)) {
                        // Notify parent
                        NotificationCenter.default.post(name: .removeImageItem, object: item.id)
                    }
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.white)
                        .shadow(color: .black.opacity(0.4), radius: 4)
                }
                .buttonStyle(.plain)
                .padding(8)
            }
            Spacer()
        }
    }

    // MARK: - Styling

    private var borderColor: Color {
        if case .complete(let r) = item.state {
            return r.classification.color.opacity(0.5)
        }
        if isHovered { return Color.accentTeal.opacity(0.4) }
        return Color.secondary.opacity(0.2)
    }

    private var shadowColor: Color {
        if case .complete(let r) = item.state {
            return r.classification.color.opacity(isHovered ? 0.3 : 0.1)
        }
        return .black.opacity(isHovered ? 0.2 : 0.08)
    }
}

extension Notification.Name {
    static let removeImageItem = Notification.Name("removeImageItem")
}
