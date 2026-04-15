import SwiftUI

enum SetupStep: Int, CaseIterable {
    case welcome
    case download
    case intervals
    case claudeDesktop
    case done
}

struct SetupWizardView: View {
    @EnvironmentObject var state: AppState
    @State private var step: SetupStep = .welcome

    // Download
    @State private var downloading = false
    @State private var downloadProgress: Double = 0
    @State private var downloadError: String?

    // Intervals.icu
    @State private var athleteID = ""
    @State private var apiKey = ""
    @State private var validating = false
    @State private var validationResult: String?
    @State private var validatedName: String?
    @State private var validationError: String?

    // Claude Desktop
    @State private var claudeConfigured = false

    var body: some View {
        VStack(spacing: 0) {
            // Progress bar
            StepIndicator(current: step)
                .padding()

            Divider()

            // Step content
            Group {
                switch step {
                case .welcome:
                    WelcomeStep()
                case .download:
                    DownloadStep(
                        downloading: $downloading,
                        progress: $downloadProgress,
                        error: $downloadError
                    )
                case .intervals:
                    IntervalsStep(
                        athleteID: $athleteID,
                        apiKey: $apiKey,
                        validating: $validating,
                        validatedName: $validatedName,
                        validationError: $validationError
                    )
                case .claudeDesktop:
                    ClaudeDesktopStep(configured: $claudeConfigured)
                case .done:
                    DoneStep()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()

            Divider()

            // Navigation
            HStack {
                if step != .welcome && step != .done {
                    Button("Retour") {
                        step = SetupStep(rawValue: step.rawValue - 1) ?? .welcome
                    }
                    .keyboardShortcut(.cancelAction)
                }

                Spacer()

                switch step {
                case .welcome:
                    Button("Commencer") {
                        if FileManager.default.fileExists(atPath: AppState.binaryPath.path) {
                            step = .intervals
                        } else {
                            step = .download
                        }
                    }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)

                case .download:
                    Button("Telecharger") {
                        Task { await downloadBinary() }
                    }
                    .disabled(downloading)
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)

                case .intervals:
                    Button("Valider") {
                        Task { await validateIntervals() }
                    }
                    .disabled(athleteID.isEmpty || apiKey.isEmpty || validating)
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)

                case .claudeDesktop:
                    Button("Configurer") {
                        configureClaude()
                    }
                    .disabled(claudeConfigured)
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)

                case .done:
                    Button("Terminer") {
                        NSApplication.shared.keyWindow?.close()
                    }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
                }
            }
            .padding()
        }
    }

    // MARK: - Actions

    func downloadBinary() async {
        downloading = true
        downloadError = nil
        do {
            guard let version = try await state.releases.latestVersion() else {
                downloadError = "Aucune release trouvee sur GitHub"
                downloading = false
                return
            }
            try await state.releases.download(
                version: version,
                destination: AppState.binaryPath
            ) { p in
                Task { @MainActor in downloadProgress = p }
            }
            try FileManager.default.setAttributes(
                [.posixPermissions: 0o755],
                ofItemAtPath: AppState.binaryPath.path
            )
            step = .intervals
        } catch {
            downloadError = error.localizedDescription
        }
        downloading = false
    }

    func validateIntervals() async {
        validating = true
        validationError = nil
        validatedName = nil
        do {
            let name = try await IntervalsValidator.validate(athleteID: athleteID, apiKey: apiKey)
            validatedName = name
            try state.completeSetup(athleteID: athleteID, apiKey: apiKey, name: name)
            step = .claudeDesktop
        } catch IntervalsValidator.ValidationError.authFailed {
            validationError = "Connexion echouee -- verifie ton ID et ta cle API."
        } catch IntervalsValidator.ValidationError.networkError(let msg) {
            validationError = "Erreur reseau: \(msg)"
        } catch {
            validationError = error.localizedDescription
        }
        validating = false
    }

    func configureClaude() {
        state.claudeDesktop.configure(binaryPath: AppState.binaryPath)
        claudeConfigured = true
        step = .done
    }
}

// MARK: - Step indicator

struct StepIndicator: View {
    let current: SetupStep
    private let labels = ["Bienvenue", "Binaire", "Intervals.icu", "Claude", "Pret"]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(SetupStep.allCases, id: \.rawValue) { s in
                HStack(spacing: 4) {
                    Circle()
                        .fill(s.rawValue <= current.rawValue ? Color.orange : Color.gray.opacity(0.3))
                        .frame(width: 10, height: 10)
                    if s.rawValue < SetupStep.allCases.count - 1 {
                        Rectangle()
                            .fill(s.rawValue < current.rawValue ? Color.orange : Color.gray.opacity(0.3))
                            .frame(height: 2)
                    }
                }
            }
        }
    }
}

// MARK: - Individual steps

struct WelcomeStep: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "flame.fill")
                .font(.system(size: 64))
                .foregroundStyle(.orange)

            Text("Bienvenue dans Magma Cycling")
                .font(.title)
                .fontWeight(.bold)

            Text("Assistant de configuration pour ton entrainement cycliste intelligent.\nEn quelques etapes, tu seras connecte a Intervals.icu et Claude Desktop.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .frame(maxWidth: 400)
        }
    }
}

struct DownloadStep: View {
    @Binding var downloading: Bool
    @Binding var progress: Double
    @Binding var error: String?

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "arrow.down.circle")
                .font(.system(size: 48))
                .foregroundStyle(.blue)

            Text("Telechargement du serveur")
                .font(.title2)
                .fontWeight(.semibold)

            if downloading {
                VStack(spacing: 8) {
                    ProgressView(value: progress)
                        .progressViewStyle(.linear)
                        .frame(width: 300)
                    Text("\(Int(progress * 100))%")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } else if let err = error {
                Label(err, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
            } else {
                Text("Le binaire magma-cycling sera telecharge depuis GitHub Releases.")
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct IntervalsStep: View {
    @Binding var athleteID: String
    @Binding var apiKey: String
    @Binding var validating: Bool
    @Binding var validatedName: String?
    @Binding var validationError: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "chart.xyaxis.line")
                    .font(.title2)
                    .foregroundStyle(.orange)
                Text("Connexion Intervals.icu")
                    .font(.title2)
                    .fontWeight(.semibold)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Identifiant athlete")
                    .font(.subheadline)
                    .fontWeight(.medium)
                TextField("i123456 ou 15002177", text: $athleteID)
                    .textFieldStyle(.roundedBorder)

                Text("Cle API")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .padding(.top, 4)
                SecureField("Depuis Settings > Developer Settings", text: $apiKey)
                    .textFieldStyle(.roundedBorder)
            }

            if validating {
                HStack {
                    ProgressView()
                        .controlSize(.small)
                    Text("Verification en cours...")
                        .foregroundStyle(.secondary)
                }
            }

            if let name = validatedName {
                Label("Connecte ! Athlete : \(name)", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            }

            if let err = validationError {
                Label(err, systemImage: "xmark.circle.fill")
                    .foregroundStyle(.red)
            }

            Spacer()

            Text("Tu trouves ton ID et ta cle API dans Intervals.icu > Settings > Developer Settings")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

struct ClaudeDesktopStep: View {
    @Binding var configured: Bool

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "bubble.left.and.bubble.right.fill")
                .font(.system(size: 48))
                .foregroundStyle(.purple)

            Text("Configuration Claude Desktop")
                .font(.title2)
                .fontWeight(.semibold)

            if configured {
                Label("Claude Desktop configure !", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .font(.headline)
                Text("Redemarre Claude Desktop pour activer les outils Magma Cycling.")
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            } else {
                Text("Le fichier de configuration Claude Desktop sera mis a jour\npour connecter les outils Magma Cycling (MCP).")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct DoneStep: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 64))
                .foregroundStyle(.green)

            Text("Configuration terminee !")
                .font(.title)
                .fontWeight(.bold)

            VStack(alignment: .leading, spacing: 8) {
                Label("Serveur MCP pret", systemImage: "server.rack")
                Label("Intervals.icu connecte", systemImage: "chart.xyaxis.line")
                Label("Claude Desktop configure", systemImage: "bubble.left.and.bubble.right.fill")
                if !state.athleteName.isEmpty {
                    Label("Athlete : \(state.athleteName)", systemImage: "person.fill")
                }
            }
            .font(.subheadline)

            Text("Magma Cycling tourne en arriere-plan dans la barre de menus.\nOuvre Claude Desktop et utilise les outils MCP pour planifier tes entrainements.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .frame(maxWidth: 400)
        }
    }
}
