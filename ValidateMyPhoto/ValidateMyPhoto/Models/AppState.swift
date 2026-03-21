import Foundation
import SwiftUI
import Combine
import UniformTypeIdentifiers

@MainActor
class AppState: ObservableObject {

    // MARK: - Published State

    @Published var imageItems: [ImageItem] = []
    @Published var selectedItemID: UUID?
    @Published var currentView: AppView = .home
    @Published var isAnalyzing: Bool = false
    @Published var showingFilePicker: Bool = false
    @Published var showingSettings: Bool = false
    @Published var errorMessage: String?
    @Published var showingError: Bool = false

    // MARK: - Settings (backed by UserDefaults)

    @AppStorage("deepAnalysisMode") var deepAnalysisMode: Bool = false
    @AppStorage("processLocallyOnly") var processLocallyOnly: Bool = true

    // MARK: - Private

    private let engine = AnalysisEngine()
    private var analysisTask: Task<Void, Never>?
    private var filePickerTrigger: (() -> Void)?

    // MARK: - Computed

    var selectedItem: ImageItem? {
        imageItems.first { $0.id == selectedItemID }
    }

    var completedItems: [ImageItem] {
        imageItems.filter { $0.result != nil }
    }

    var averageScore: Double? {
        let results = completedItems.compactMap(\.result)
        guard !results.isEmpty else { return nil }
        return results.map(\.authenticityScore).reduce(0, +) / Double(results.count)
    }

    var flaggedItems: [ImageItem] {
        completedItems.filter {
            $0.result?.classification == .likelyAIGenerated
        }
    }

    var canAnalyze: Bool {
        !imageItems.isEmpty && !isAnalyzing
    }

    // MARK: - Image Management

    func addImages(urls: [URL]) {
        var added = 0
        var skippedSize = 0
        var skippedFormat = 0

        for url in urls {
            guard imageItems.count < 12 else { break }
            guard !imageItems.contains(where: { $0.url == url }) else { continue }

            if !ImageItem.isSupported(url: url) {
                skippedFormat += 1
                continue
            }
            if !ImageItem.fileSizeWithinLimit(url) {
                skippedSize += 1
                continue
            }

            let item = ImageItem(url: url)
            imageItems.append(item)
            added += 1
        }

        if skippedSize > 0 || skippedFormat > 0 {
            var msg = ""
            if skippedFormat > 0 { msg += "\(skippedFormat) unsupported file(s). " }
            if skippedSize > 0  { msg += "\(skippedSize) file(s) exceed 100 MB limit." }
            postError(msg.trimmingCharacters(in: .whitespaces))
        }

        if added > 0 && currentView == .home {
            currentView = .analysis
        }
    }

    func removeItem(_ item: ImageItem) {
        imageItems.removeAll { $0.id == item.id }
        if selectedItemID == item.id { selectedItemID = nil }
        if imageItems.isEmpty { currentView = .home }
    }

    func clearAll() {
        analysisTask?.cancel()
        imageItems.removeAll()
        selectedItemID = nil
        currentView = .home
        isAnalyzing = false
    }

    // MARK: - Analysis

    func analyzeAll() {
        guard !isAnalyzing else { return }
        isAnalyzing = true

        analysisTask = Task {
            let pendingItems = imageItems.filter {
                if case .idle = $0.state { return true }
                if case .failed = $0.state { return true }
                return false
            }

            await withTaskGroup(of: Void.self) { group in
                for item in pendingItems {
                    group.addTask { [weak self] in
                        await self?.analyzeItem(item)
                    }
                }
            }

            await MainActor.run {
                self.isAnalyzing = false
            }
        }
    }

    private func analyzeItem(_ item: ImageItem) async {
        await MainActor.run { item.state = .analyzing(progress: 0.05) }

        do {
            let result = try await engine.analyze(
                item: item,
                deepMode: deepAnalysisMode,
                progressHandler: { [weak item] p in
                    Task { @MainActor in
                        item?.state = .analyzing(progress: p)
                    }
                }
            )
            await MainActor.run {
                item.state = .complete(result: result)
                if self.selectedItemID == nil { self.selectedItemID = item.id }
            }
        } catch {
            await MainActor.run {
                item.state = .failed(error: error.localizedDescription)
            }
        }
    }

    // MARK: - Navigation

    func selectItem(_ item: ImageItem) {
        selectedItemID = item.id
        currentView = .detail
    }

    func navigateTo(_ view: AppView) {
        currentView = view
    }

    // MARK: - File Picker

    func triggerFilePicker() {
        showingFilePicker = true
    }

    // MARK: - Error Handling

    func postError(_ message: String) {
        errorMessage = message
        showingError = true
    }

    // MARK: - Reset / Reanalyze

    func reanalyzeItem(_ item: ImageItem) {
        item.state = .idle
        Task { await analyzeItem(item) }
    }
}

// MARK: - App View

enum AppView: Hashable {
    case home
    case analysis
    case detail
    case report
}
