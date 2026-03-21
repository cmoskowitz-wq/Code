import SwiftUI

// MARK: - Score Badge

struct ScoreBadge: View {
    let score: Double
    let size: BadgeSize
    var showLabel: Bool = true

    enum BadgeSize {
        case small, medium, large

        var diameter: CGFloat {
            switch self { case .small: return 44; case .medium: return 72; case .large: return 110 }
        }
        var scoreFont: Font {
            switch self { case .small: return .system(size: 14, weight: .bold); case .medium: return .system(size: 22, weight: .bold); case .large: return .system(size: 34, weight: .bold, design: .rounded) }
        }
        var labelFont: Font {
            switch self { case .small: return .system(size: 8, weight: .medium); case .medium: return .system(size: 11, weight: .medium); case .large: return .system(size: 13, weight: .semibold) }
        }
        var lineWidth: CGFloat {
            switch self { case .small: return 3; case .medium: return 5; case .large: return 7 }
        }
    }

    private var classification: AuthenticityClassification {
        if score >= 75 { return .likelyAuthentic }
        if score >= 45 { return .uncertain }
        return .likelyAIGenerated
    }

    private var scoreColor: Color { classification.color }

    var body: some View {
        ZStack {
            // Background track
            Circle()
                .stroke(scoreColor.opacity(0.15), lineWidth: size.lineWidth)

            // Progress arc
            Circle()
                .trim(from: 0, to: score / 100)
                .stroke(
                    AngularGradient(
                        gradient: Gradient(colors: [scoreColor.opacity(0.6), scoreColor]),
                        center: .center,
                        startAngle: .degrees(-90),
                        endAngle: .degrees(270)
                    ),
                    style: StrokeStyle(lineWidth: size.lineWidth, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .animation(.spring(response: 0.7, dampingFraction: 0.75), value: score)

            // Score text
            VStack(spacing: 1) {
                Text("\(Int(score.rounded()))")
                    .font(size.scoreFont)
                    .foregroundColor(.primary)

                if showLabel {
                    Text("%")
                        .font(size.labelFont)
                        .foregroundColor(.secondary)
                }
            }
        }
        .frame(width: size.diameter, height: size.diameter)
    }
}

// MARK: - Classification Badge

struct ClassificationBadge: View {
    let classification: AuthenticityClassification
    var compact: Bool = false

    var body: some View {
        HStack(spacing: compact ? 4 : 6) {
            Image(systemName: classification.icon)
                .font(.system(size: compact ? 10 : 12, weight: .semibold))
            Text(compact ? classification.shortLabel : classification.rawValue)
                .font(.system(size: compact ? 10 : 12, weight: .semibold))
        }
        .padding(.horizontal, compact ? 8 : 12)
        .padding(.vertical, compact ? 4 : 6)
        .background(
            Capsule().fill(classification.color.opacity(0.15))
        )
        .overlay(
            Capsule().stroke(classification.color.opacity(0.3), lineWidth: 1)
        )
        .foregroundColor(classification.color)
    }
}

// MARK: - Score Color Band

extension Double {
    var authenticityColor: Color {
        if self >= 75 { return .authenticGreen }
        if self >= 45 { return .uncertainYellow }
        return .aiRed
    }
}

#Preview {
    HStack(spacing: 24) {
        ScoreBadge(score: 88, size: .small)
        ScoreBadge(score: 62, size: .medium)
        ScoreBadge(score: 31, size: .large)
    }
    .padding(40)
    .background(Color(white: 0.1))
}
