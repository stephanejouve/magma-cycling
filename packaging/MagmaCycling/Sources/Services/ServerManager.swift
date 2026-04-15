import Foundation

/// Gestion du process MCP server (start/stop/monitor).
final class ServerManager {
    private var process: Process?
    private(set) var pid: Int32?

    /// Verifie si le serveur tourne encore.
    func isRunning() -> Bool {
        guard let proc = process else { return false }
        return proc.isRunning
    }

    /// Demarre le serveur MCP standalone.
    func start(binary: URL, envFile: URL, logsDir: URL) throws {
        guard !isRunning() else { return }

        let env = try loadEnv(from: envFile)

        let proc = Process()
        proc.executableURL = binary
        proc.arguments = ["mcp-server", "--transport", "stdio"]
        proc.environment = ProcessInfo.processInfo.environment.merging(env) { _, new in new }

        // Logs
        let logFile = logsDir.appendingPathComponent("mcp-server.log")
        let errFile = logsDir.appendingPathComponent("mcp-server.err")
        FileManager.default.createFile(atPath: logFile.path, contents: nil)
        FileManager.default.createFile(atPath: errFile.path, contents: nil)
        proc.standardOutput = try FileHandle(forWritingTo: logFile)
        proc.standardError = try FileHandle(forWritingTo: errFile)

        proc.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                self?.process = nil
                self?.pid = nil
            }
        }

        try proc.run()
        process = proc
        pid = proc.processIdentifier
    }

    /// Arrete le serveur gracieusement (SIGTERM puis SIGKILL apres 5s).
    func stop() {
        guard let proc = process, proc.isRunning else { return }
        proc.terminate()

        DispatchQueue.global().asyncAfter(deadline: .now() + 5) {
            if proc.isRunning {
                kill(proc.processIdentifier, SIGKILL)
            }
        }

        process = nil
        pid = nil
    }

    /// Parse un fichier .env en dictionnaire.
    private func loadEnv(from url: URL) throws -> [String: String] {
        let content = try String(contentsOf: url, encoding: .utf8)
        var env: [String: String] = [:]
        for line in content.components(separatedBy: .newlines) {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty || trimmed.hasPrefix("#") { continue }
            let parts = trimmed.split(separator: "=", maxSplits: 1)
            guard parts.count == 2 else { continue }
            env[String(parts[0])] = String(parts[1])
        }
        return env
    }
}
