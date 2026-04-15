import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var state: AppState
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Image(systemName: "flame.fill")
                    .foregroundStyle(.orange)
                    .font(.title2)
                Text("Magma Cycling")
                    .font(.headline)
                Spacer()
                Text(state.currentVersion())
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal)
            .padding(.top, 12)

            if !state.athleteName.isEmpty {
                Text(state.athleteName)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
                    .padding(.top, 2)
            }

            Divider().padding(.vertical, 8)

            // Server status
            ServerStatusRow()
                .padding(.horizontal)

            Divider().padding(.vertical, 8)

            // Actions
            if !state.isConfigured {
                Button {
                    openWindow(id: "setup")
                } label: {
                    Label("Configurer...", systemImage: "gearshape")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.plain)
                .padding(.horizontal)
            } else {
                // Start / Stop
                if state.serverRunning {
                    Button {
                        state.stopServer()
                    } label: {
                        Label("Arreter le serveur", systemImage: "stop.fill")
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal)
                } else {
                    Button {
                        state.startServer()
                    } label: {
                        Label("Demarrer le serveur", systemImage: "play.fill")
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal)
                }

                Button {
                    openWindow(id: "setup")
                } label: {
                    Label("Configuration...", systemImage: "gearshape")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.plain)
                .padding(.horizontal)
                .padding(.top, 4)
            }

            // Update banner
            if let version = state.updateAvailable {
                Divider().padding(.vertical, 8)
                UpdateBanner(version: version)
                    .padding(.horizontal)
            }

            Divider().padding(.vertical, 8)

            // Logs (collapsed)
            if !state.serverLog.isEmpty {
                DisclosureGroup("Logs recents") {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 2) {
                            ForEach(state.serverLog.suffix(10), id: \.self) { line in
                                Text(line)
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .frame(maxHeight: 120)
                }
                .font(.caption)
                .padding(.horizontal)

                Divider().padding(.vertical, 8)
            }

            Button {
                NSApplication.shared.terminate(nil)
            } label: {
                Label("Quitter Magma Cycling", systemImage: "power")
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.plain)
            .padding(.horizontal)
            .padding(.bottom, 12)
        }
        .frame(width: 300)
    }
}

// MARK: - Server status row

struct ServerStatusRow: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        HStack {
            Circle()
                .fill(state.serverRunning ? .green : .red)
                .frame(width: 8, height: 8)

            Text(state.serverRunning ? "Serveur MCP actif" : "Serveur MCP inactif")
                .font(.subheadline)

            Spacer()

            if let pid = state.serverPID, state.serverRunning {
                Text("PID \(pid)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: - Update banner

struct UpdateBanner: View {
    @EnvironmentObject var state: AppState
    let version: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: "arrow.down.circle.fill")
                    .foregroundStyle(.blue)
                Text("Mise a jour \(version) disponible")
                    .font(.subheadline)
            }

            if state.isDownloading {
                ProgressView(value: state.downloadProgress)
                    .progressViewStyle(.linear)
            } else {
                Button("Installer") {
                    Task { try? await state.installUpdate() }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
        }
    }
}
