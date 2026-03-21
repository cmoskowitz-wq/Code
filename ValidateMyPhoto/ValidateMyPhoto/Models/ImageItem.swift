import Foundation
import SwiftUI
import UniformTypeIdentifiers

// MARK: - Analysis State

enum AnalysisState: Equatable {
    case idle
    case queued
    case analyzing(progress: Double)   // 0.0–1.0
    case complete(result: AnalysisResult)
    case failed(error: String)

    static func == (lhs: AnalysisState, rhs: AnalysisState) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle), (.queued, .queued): return true
        case (.analyzing(let a), .analyzing(let b)): return a == b
        case (.complete(let a), .complete(let b)): return a.id == b.id
        case (.failed(let a), .failed(let b)): return a == b
        default: return false
        }
    }
}

// MARK: - Supported UTTypes

extension UTType {
    static let heic = UTType(filenameExtension: "heic") ?? .image
    static let cr2  = UTType(filenameExtension: "cr2")  ?? .image
    static let cr3  = UTType(filenameExtension: "cr3")  ?? .image
    static let nef  = UTType(filenameExtension: "nef")  ?? .image
    static let arw  = UTType(filenameExtension: "arw")  ?? .image
    static let dng  = UTType(filenameExtension: "dng")  ?? .image

    static let supportedImageTypes: [UTType] = [
        .jpeg, .png, .tiff, .heic,
        .cr2, .cr3, .nef, .arw, .dng
    ]
}

// MARK: - Image Item

@MainActor
class ImageItem: ObservableObject, Identifiable {
    let id: UUID
    let url: URL
    let fileName: String
    let fileSize: Int64
    let fileExtension: String

    @Published var state: AnalysisState = .idle
    @Published var thumbnail: NSImage?

    var result: AnalysisResult? {
        if case .complete(let r) = state { return r }
        return nil
    }

    var isAnalyzing: Bool {
        if case .analyzing = state { return true }
        return false
    }

    var progress: Double {
        if case .analyzing(let p) = state { return p }
        if case .complete = state { return 1.0 }
        return 0.0
    }

    init(url: URL) {
        self.id = UUID()
        self.url = url
        self.fileName = url.lastPathComponent
        self.fileExtension = url.pathExtension.lowercased()

        // Get file size
        let attrs = try? FileManager.default.attributesOfItem(atPath: url.path)
        self.fileSize = attrs?[.size] as? Int64 ?? 0

        // Load thumbnail asynchronously
        Task { await self.loadThumbnail() }
    }

    private func loadThumbnail() async {
        let url = self.url
        let image = await Task.detached(priority: .utility) {
            guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return NSImage?.none }
            let opts: [CFString: Any] = [
                kCGImageSourceThumbnailMaxPixelSize: 300,
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceCreateThumbnailWithTransform: true
            ]
            guard let cgThumb = CGImageSourceCreateThumbnailAtIndex(src, 0, opts as CFDictionary) else { return NSImage?.none }
            return NSImage(cgImage: cgThumb, size: .zero)
        }.value
        self.thumbnail = image
    }

    static func isSupported(url: URL) -> Bool {
        let ext = url.pathExtension.lowercased()
        let supported = ["jpg", "jpeg", "png", "heic", "tiff", "tif",
                         "cr2", "cr3", "nef", "arw", "dng"]
        return supported.contains(ext)
    }

    static func fileSizeWithinLimit(_ url: URL) -> Bool {
        let attrs = try? FileManager.default.attributesOfItem(atPath: url.path)
        let size = attrs?[.size] as? Int64 ?? 0
        return size <= 100 * 1024 * 1024  // 100 MB
    }
}
