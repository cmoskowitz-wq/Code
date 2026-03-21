import SwiftUI

@main
struct ValidateMyPhotoApp: App {
    @StateObject private var appState = AppState()
    @AppStorage("colorScheme") private var colorSchemePreference: String = "system"

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .preferredColorScheme(resolvedColorScheme)
                .frame(minWidth: 900, minHeight: 640)
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(after: .newItem) {
                Button("Open Photos...") {
                    appState.triggerFilePicker()
                }
                .keyboardShortcut("o", modifiers: .command)
            }
            CommandGroup(replacing: .help) {
                Button("Validate My Photo Help") {
                    NSWorkspace.shared.open(URL(string: "https://moskophotolabs.com/help")!)
                }
            }
        }

        Settings {
            SettingsView()
                .environmentObject(appState)
        }
    }

    private var resolvedColorScheme: ColorScheme? {
        switch colorSchemePreference {
        case "light": return .light
        case "dark": return .dark
        default: return nil
        }
    }
}
