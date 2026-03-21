import SwiftUI
import UniformTypeIdentifiers

struct HomeView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme
    @State private var isDraggingOver = false
    @State private var animatePulse = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()
            heroSection
            Spacer()
            dropZone
            Spacer()
            footerNote
                .padding(.bottom, 24)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onDrop(of: UTType.supportedImageTypes, isTargeted: $isDraggingOver) { providers in
            handleDrop(providers: providers)
        }
    }

    // MARK: - Hero Section

    private var heroSection: some View {
        VStack(spacing: 12) {
            Image(systemName: "camera.viewfinder")
                .font(.system(size: 48, weight: .thin))
                .foregroundStyle(
                    LinearGradient(colors: [.accentTeal, Color(red: 0.1, green: 0.5, blue: 1.0)],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                )
                .scaleEffect(animatePulse ? 1.04 : 1.0)
                .animation(.easeInOut(duration: 2.5).repeatForever(autoreverses: true), value: animatePulse)
                .onAppear { animatePulse = true }

            Text("Validate My Photo")
                .font(.system(size: 30, weight: .bold, design: .default))
                .foregroundColor(.primary)

            Text("Detect AI-generated images with multi-layer forensic analysis")
                .font(.system(size: 14, weight: .regular))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Text("by Mosko Photo Labs")
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.accentTeal)
                .padding(.top, 2)
        }
        .padding(.horizontal, 40)
    }

    // MARK: - Drop Zone

    private var dropZone: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 20)
                .fill(dropZoneFill)
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(
                            isDraggingOver ? Color.accentTeal : Color.secondary.opacity(0.3),
                            style: StrokeStyle(lineWidth: isDraggingOver ? 2.5 : 1.5, dash: [8, 5])
                        )
                )
                .shadow(color: isDraggingOver ? Color.accentTeal.opacity(0.25) : .clear, radius: 20)
                .animation(.easeInOut(duration: 0.2), value: isDraggingOver)

            VStack(spacing: 18) {
                Image(systemName: isDraggingOver ? "arrow.down.circle.fill" : "photo.stack")
                    .font(.system(size: 40, weight: .thin))
                    .foregroundColor(isDraggingOver ? .accentTeal : .secondary)
                    .animation(.spring(response: 0.25), value: isDraggingOver)

                VStack(spacing: 6) {
                    Text(isDraggingOver ? "Release to add photos" : "Drop photos here")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(isDraggingOver ? .accentTeal : .primary)

                    Text("or")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)

                    Button {
                        appState.triggerFilePicker()
                    } label: {
                        Text("Browse Files")
                            .font(.system(size: 13, weight: .semibold))
                            .padding(.horizontal, 20)
                            .padding(.vertical, 8)
                            .background(Color.accentTeal)
                            .foregroundColor(.white)
                            .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                    .shadow(color: Color.accentTeal.opacity(0.3), radius: 8, y: 3)
                }

                formatsLabel
            }
            .padding(40)
        }
        .frame(maxWidth: 560)
        .frame(height: 280)
        .padding(.horizontal, 48)
    }

    private var dropZoneFill: some ShapeStyle {
        if colorScheme == .dark {
            return AnyShapeStyle(Color.white.opacity(isDraggingOver ? 0.06 : 0.03))
        } else {
            return AnyShapeStyle(Color.black.opacity(isDraggingOver ? 0.04 : 0.02))
        }
    }

    private var formatsLabel: some View {
        Text("JPEG · PNG · HEIC · TIFF · RAW (CR2/CR3/NEF/ARW/DNG) · Max 12 images · 100 MB each")
            .font(.system(size: 10, weight: .medium))
            .foregroundColor(.secondary)
            .multilineTextAlignment(.center)
            .padding(.top, 4)
    }

    // MARK: - Feature Pills

    private var featurePills: some View {
        HStack(spacing: 12) {
            FeaturePill(icon: "shield.checkerboard", label: "Local Only")
            FeaturePill(icon: "waveform", label: "FFT Analysis")
            FeaturePill(icon: "cpu", label: "Core ML")
            FeaturePill(icon: "doc.text.fill", label: "PDF Report")
        }
    }

    // MARK: - Footer

    private var footerNote: some View {
        VStack(spacing: 6) {
            featurePills
            Text("All processing happens locally on your device. No data leaves your Mac.")
                .font(.system(size: 11))
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Drop Handler

    private func handleDrop(providers: [NSItemProvider]) -> Bool {
        var urls: [URL] = []
        let group = DispatchGroup()

        for provider in providers {
            for type in UTType.supportedImageTypes {
                if provider.hasItemConformingToTypeIdentifier(type.identifier) {
                    group.enter()
                    provider.loadItem(forTypeIdentifier: type.identifier) { item, _ in
                        if let url = item as? URL {
                            urls.append(url)
                        } else if let data = item as? Data,
                                  let url = URL(dataRepresentation: data, relativeTo: nil) {
                            urls.append(url)
                        }
                        group.leave()
                    }
                    break
                }
            }
        }

        group.notify(queue: .main) {
            if !urls.isEmpty { appState.addImages(urls: urls) }
        }

        return !providers.isEmpty
    }
}

// MARK: - Feature Pill

struct FeaturePill: View {
    let icon: String
    let label: String
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: icon)
                .font(.system(size: 10, weight: .semibold))
                .foregroundColor(.accentTeal)
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(
            Capsule()
                .fill(colorScheme == .dark ? Color.white.opacity(0.07) : Color.black.opacity(0.05))
        )
    }
}

#Preview {
    HomeView()
        .environmentObject(AppState())
        .frame(width: 900, height: 640)
}
