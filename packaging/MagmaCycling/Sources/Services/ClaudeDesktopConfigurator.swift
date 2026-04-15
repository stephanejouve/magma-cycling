import Foundation

/// Configure Claude Desktop pour utiliser le serveur MCP Magma Cycling.
final class ClaudeDesktopConfigurator {
    private var configURL: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Claude/claude_desktop_config.json")
    }

    /// Injecte la configuration MCP dans claude_desktop_config.json.
    func configure(binaryPath: URL) {
        let fm = FileManager.default
        let configDir = configURL.deletingLastPathComponent()

        // Creer le dossier si besoin
        try? fm.createDirectory(at: configDir, withIntermediateDirectories: true)

        // Charger la config existante ou creer une vierge
        var config: [String: Any] = [:]
        if let data = fm.contents(atPath: configURL.path),
           let existing = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        {
            config = existing
        }

        // Section mcpServers
        var mcpServers = config["mcpServers"] as? [String: Any] ?? [:]

        mcpServers["magma-cycling"] = [
            "command": binaryPath.path,
            "args": ["mcp-server", "--transport", "stdio"],
        ]

        config["mcpServers"] = mcpServers

        // Ecrire
        if let data = try? JSONSerialization.data(
            withJSONObject: config,
            options: [.prettyPrinted, .sortedKeys]
        ) {
            try? data.write(to: configURL, options: .atomic)
            // Permissions 600
            try? fm.setAttributes(
                [.posixPermissions: 0o600],
                ofItemAtPath: configURL.path
            )
        }
    }

    /// Verifie si magma-cycling est deja configure dans Claude Desktop.
    var isConfigured: Bool {
        guard let data = FileManager.default.contents(atPath: configURL.path),
              let config = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let mcpServers = config["mcpServers"] as? [String: Any]
        else {
            return false
        }
        return mcpServers["magma-cycling"] != nil
    }
}
