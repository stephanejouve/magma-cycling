import Combine
import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    // MARK: - Server

    @Published var serverRunning = false
    @Published var serverPID: Int32?
    @Published var serverLog: [String] = []

    // MARK: - Setup

    @Published var isConfigured: Bool
    @Published var athleteName: String

    // MARK: - Update

    @Published var updateAvailable: String?
    @Published var isDownloading = false
    @Published var downloadProgress: Double = 0

    // MARK: - Services

    let server = ServerManager()
    let releases = ReleaseChecker()
    let launchAgent = LaunchAgentManager()
    let claudeDesktop = ClaudeDesktopConfigurator()

    // MARK: - Paths

    static let appSupport: URL = {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("MagmaCycling")
    }()

    static let binaryPath: URL = appSupport.appendingPathComponent("magma-cycling")
    static let configDir: URL = appSupport.appendingPathComponent("config")
    static let envFile: URL = configDir.appendingPathComponent(".env")
    static let logsDir: URL = appSupport.appendingPathComponent("logs")

    init() {
        let configured = FileManager.default.fileExists(atPath: Self.envFile.path)
        self.isConfigured = configured
        self.athleteName = UserDefaults.standard.string(forKey: "athleteName") ?? ""

        Task { await bootstrap() }
    }

    func bootstrap() async {
        ensureDirectories()
        serverRunning = server.isRunning()

        if let latest = try? await releases.latestVersion() {
            let current = currentVersion()
            if latest != current {
                updateAvailable = latest
            }
        }
    }

    func currentVersion() -> String {
        guard FileManager.default.fileExists(atPath: Self.binaryPath.path) else { return "0.0.0" }
        let pipe = Pipe()
        let proc = Process()
        proc.executableURL = Self.binaryPath
        proc.arguments = ["--version"]
        proc.standardOutput = pipe
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        proc.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let raw = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "0.0.0"
        // Parse "magma-cycling 3.14.0" → "3.14.0"
        return raw.split(separator: " ").last.map(String.init) ?? raw
    }

    func ensureDirectories() {
        let fm = FileManager.default
        for dir in [Self.appSupport, Self.configDir, Self.logsDir] {
            try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
        }
    }

    // MARK: - Server control

    func startServer() {
        guard !serverRunning else { return }
        do {
            try server.start(binary: Self.binaryPath, envFile: Self.envFile, logsDir: Self.logsDir)
            serverRunning = true
            serverPID = server.pid
            appendLog("Serveur MCP demarr\u{e9} (PID \(server.pid ?? 0))")
        } catch {
            appendLog("Erreur demarrage: \(error.localizedDescription)")
        }
    }

    func stopServer() {
        server.stop()
        serverRunning = false
        serverPID = nil
        appendLog("Serveur MCP arret\u{e9}")
    }

    func appendLog(_ line: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        serverLog.append("[\(ts)] \(line)")
        if serverLog.count > 200 { serverLog.removeFirst() }
    }

    // MARK: - Setup completion

    func completeSetup(athleteID: String, apiKey: String, name: String) throws {
        let env = """
        ATHLETE_ID=\(athleteID)
        INTERVALS_API_KEY=\(apiKey)
        """
        try env.write(to: Self.envFile, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o600],
            ofItemAtPath: Self.envFile.path
        )

        athleteName = name
        UserDefaults.standard.set(name, forKey: "athleteName")
        isConfigured = true

        // Configurer Claude Desktop
        claudeDesktop.configure(binaryPath: Self.binaryPath)

        // Installer LaunchAgent
        launchAgent.install(binaryPath: Self.binaryPath, envFile: Self.envFile)
    }

    // MARK: - Update

    func installUpdate() async throws {
        guard let version = updateAvailable else { return }
        isDownloading = true
        defer { isDownloading = false }

        let wasRunning = serverRunning
        if wasRunning { stopServer() }

        try await releases.download(
            version: version,
            destination: Self.binaryPath
        ) { progress in
            Task { @MainActor in self.downloadProgress = progress }
        }

        // chmod +x
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o755],
            ofItemAtPath: Self.binaryPath.path
        )

        updateAvailable = nil
        appendLog("Mise \u{e0} jour \(version) install\u{e9}e")

        if wasRunning { startServer() }
    }
}
