import SwiftUI

struct CircularProgress: View {
    let progress: Double    // 0.0–1.0
    var color: Color = .accentTeal
    var lineWidth: CGFloat = 3
    var size: CGFloat = 32

    var body: some View {
        ZStack {
            Circle()
                .stroke(color.opacity(0.2), lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(color, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(.linear(duration: 0.15), value: progress)
        }
        .frame(width: size, height: size)
    }
}
