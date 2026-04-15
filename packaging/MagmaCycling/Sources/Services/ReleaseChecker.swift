import Foundation

/// Verifie et telecharge les releases GitHub.
final class ReleaseChecker {
    private let repo = "stephanejouve/magma-cycling"
    private let session = URLSession.shared

    struct Release: Decodable {
        let tag_name: String
        let assets: [Asset]

        struct Asset: Decodable {
            let name: String
            let browser_download_url: String
            let size: Int
        }
    }

    /// Retourne la derniere version disponible (ex: "3.14.0").
    func latestVersion() async throws -> String? {
        let url = URL(string: "https://api.github.com/repos/\(repo)/releases/latest")!
        var request = URLRequest(url: url)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            return nil
        }

        let release = try JSONDecoder().decode(Release.self, from: data)
        // "v3.14.0" → "3.14.0"
        return release.tag_name.hasPrefix("v")
            ? String(release.tag_name.dropFirst())
            : release.tag_name
    }

    /// Telecharge le binaire macOS depuis la release.
    func download(
        version: String,
        destination: URL,
        progress: @escaping (Double) -> Void
    ) async throws {
        let tag = "v\(version)"
        let url = URL(string: "https://api.github.com/repos/\(repo)/releases/tags/\(tag)")!
        var request = URLRequest(url: url)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")

        let (data, _) = try await session.data(for: request)
        let release = try JSONDecoder().decode(Release.self, from: data)

        // Detecter l'architecture
        let arch = ProcessInfo.processInfo.machineArchitecture
        let assetName = arch == "arm64"
            ? "magma-cycling-macos-arm64"
            : "magma-cycling-macos-x86_64"

        guard let asset = release.assets.first(where: { $0.name == assetName }) else {
            throw DownloadError.assetNotFound(assetName)
        }

        let downloadURL = URL(string: asset.browser_download_url)!
        let delegate = ProgressDelegate(totalSize: asset.size, onProgress: progress)

        let (tempURL, _) = try await session.download(from: downloadURL, delegate: delegate)

        // Remplacer le binaire existant
        let fm = FileManager.default
        if fm.fileExists(atPath: destination.path) {
            try fm.removeItem(at: destination)
        }
        try fm.moveItem(at: tempURL, to: destination)
    }

    enum DownloadError: LocalizedError {
        case assetNotFound(String)

        var errorDescription: String? {
            switch self {
            case .assetNotFound(let name):
                return "Asset \(name) introuvable dans la release"
            }
        }
    }
}

// MARK: - Progress tracking

private final class ProgressDelegate: NSObject, URLSessionDownloadDelegate {
    let totalSize: Int
    let onProgress: (Double) -> Void

    init(totalSize: Int, onProgress: @escaping (Double) -> Void) {
        self.totalSize = totalSize
        self.onProgress = onProgress
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didWriteData bytesWritten: Int64,
        totalBytesWritten: Int64,
        totalBytesExpectedToWrite: Int64
    ) {
        let expected = totalBytesExpectedToWrite > 0
            ? totalBytesExpectedToWrite
            : Int64(totalSize)
        let fraction = Double(totalBytesWritten) / Double(max(expected, 1))
        onProgress(min(fraction, 1.0))
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        // Handled by the async download call
    }
}

// MARK: - Architecture detection

extension ProcessInfo {
    var machineArchitecture: String {
        var sysinfo = utsname()
        uname(&sysinfo)
        return withUnsafePointer(to: &sysinfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                String(validatingUTF8: $0) ?? "unknown"
            }
        }
    }
}
