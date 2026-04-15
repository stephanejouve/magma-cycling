import Foundation

/// Gestion du LaunchAgent pour demarrage automatique au login.
final class LaunchAgentManager {
    private let label = "eu.alliancejr.magma-cycling"
    private var plistURL: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/LaunchAgents/\(label).plist")
    }

    var isInstalled: Bool {
        FileManager.default.fileExists(atPath: plistURL.path)
    }

    /// Installe le LaunchAgent pour lancer le serveur MCP au login.
    func install(binaryPath: URL, envFile: URL) {
        let plist: [String: Any] = [
            "Label": label,
            "ProgramArguments": [
                binaryPath.path,
                "mcp-server",
                "--transport", "stdio",
            ],
            "EnvironmentVariables": [
                "MAGMA_ENV_FILE": envFile.path,
            ],
            "RunAtLoad": true,
            "KeepAlive": [
                "SuccessfulExit": false,  // Restart si crash
            ],
            "StandardOutPath": AppState.logsDir.appendingPathComponent("mcp-server.log").path,
            "StandardErrorPath": AppState.logsDir.appendingPathComponent("mcp-server.err").path,
            "ThrottleInterval": 10,
        ]

        let data = try? PropertyListSerialization.data(
            fromPropertyList: plist,
            format: .xml,
            options: 0
        )

        try? data?.write(to: plistURL, options: .atomic)

        // Load
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        proc.arguments = ["load", plistURL.path]
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        proc.waitUntilExit()
    }

    /// Desinstalle le LaunchAgent.
    func uninstall() {
        // Unload
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        proc.arguments = ["unload", plistURL.path]
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        proc.waitUntilExit()

        try? FileManager.default.removeItem(at: plistURL)
    }
}
