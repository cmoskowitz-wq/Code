import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        ZStack {
            // Background
            backgroundGradient
                .ignoresSafeArea()

            // Main content
            Group {
                switch appState.currentView {
                case .home:
                    HomeView()
                        .transition(.asymmetric(
                            insertion: .opacity.combined(with: .scale(scale: 0.97)),
                            removal: .opacity
                        ))
                case .analysis:
                    AnalysisGridView()
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                case .detail:
                    DetailView()
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                case .report:
                    ReportView()
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .leading).combined(with: .opacity)
                        ))
                }
            }
            .animation(.easeInOut(duration: 0.25), value: appState.currentView)
        }
        .fileImporter(
            isPresented: $appState.showingFilePicker,
            allowedContentTypes: UTType.supportedImageTypes,
            allowsMultipleSelection: true
        ) { result in
            switch result {
            case .success(let urls):
                appState.addImages(urls: urls)
            case .failure(let error):
                appState.postError(error.localizedDescription)
            }
        }
        .alert("Notice", isPresented: $appState.showingError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(appState.errorMessage ?? "")
        }
        .toolbar {
            toolbarContent
        }
    }

    // MARK: - Background

    private var backgroundGradient: some View {
        LinearGradient(
            gradient: Gradient(colors: colorScheme == .dark
                ? [Color(white: 0.08), Color(white: 0.06)]
                : [Color(white: 0.96), Color(white: 0.92)]),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItemGroup(placement: .navigation) {
            if appState.currentView != .home {
                Button {
                    withAnimation { appState.navigateTo(.home) }
                } label: {
                    Image(systemName: "chevron.left")
                }
                .help("Back to Home")
            }

            // App brand
            HStack(spacing: 6) {
                Image(systemName: "camera.viewfinder")
                    .foregroundColor(.accentTeal)
                    .font(.system(size: 15, weight: .semibold))
                Text("Validate My Photo")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.primary)
            }
        }

        ToolbarItemGroup(placement: .primaryAction) {
            if !appState.imageItems.isEmpty {
                Button {
                    appState.navigateTo(.report)
                } label: {
                    Label("Report", systemImage: "doc.text.fill")
                }
                .help("View Report")
                .disabled(appState.completedItems.isEmpty)
            }

            if appState.currentView == .analysis || appState.currentView == .detail {
                Button {
                    appState.analyzeAll()
                } label: {
                    Label("Analyze", systemImage: "sparkle.magnifyingglass")
                }
                .help("Analyze all images")
                .disabled(!appState.canAnalyze)
                .keyboardShortcut(.return, modifiers: .command)
            }

            Button {
                appState.triggerFilePicker()
            } label: {
                Label("Add Photos", systemImage: "plus.circle.fill")
            }
            .help("Add photos (⌘O)")
            .disabled(appState.imageItems.count >= 12)
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
        .frame(width: 1100, height: 720)
}
