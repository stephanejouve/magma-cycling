import SwiftUI

@main
struct MagmaCyclingApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        MenuBarExtra {
            MenuBarView()
                .environmentObject(state)
        } label: {
            Label {
                Text("Magma Cycling")
            } icon: {
                Image(systemName: state.serverRunning ? "flame.fill" : "flame")
            }
        }
        .menuBarExtraStyle(.window)

        Window("Configuration Magma Cycling", id: "setup") {
            SetupWizardView()
                .environmentObject(state)
                .frame(minWidth: 520, minHeight: 480)
        }
        .defaultSize(width: 560, height: 520)
        .windowResizability(.contentSize)
    }
}
