import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @AppStorage("colorScheme") private var colorSchemePreference: String = "system"
    @AppStorage("exportDirectory") private var exportDirectory: String = ""

    var body: some View {
        TabView {
            generalTab
                .tabItem { Label("General", systemImage: "gearshape") }

            analysisTab
                .tabItem { Label("Analysis", systemImage: "waveform") }

            privacyTab
                .tabItem { Label("Privacy", systemImage: "lock.shield") }

            aboutTab
                .tabItem { Label("About", systemImage: "info.circle") }
        }
        .frame(width: 480, height: 340)
    }

    // MARK: - General

    private var generalTab: some View {
        Form {
            Section("Appearance") {
                Picker("Color Scheme", selection: $colorSchemePreference) {
                    Text("System").tag("system")
                    Text("Light").tag("light")
                    Text("Dark").tag("dark")
                }
                .pickerStyle(.segmented)
            }

            Section("Export") {
                HStack {
                    Text("Export Location")
                    Spacer()
                    Text(exportDirectory.isEmpty ? "Downloads" : URL(fileURLWithPath: exportDirectory).lastPathComponent)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    Button("Choose…") {
                        chooseExportDirectory()
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - Analysis

    private var analysisTab: some View {
        Form {
            Section {
                Toggle("Deep Analysis Mode", isOn: $appState.deepAnalysisMode)
                Text("Enables additional texture scanning, higher-resolution FFT, and extended anatomical analysis. Increases per-image time to ~5–10 seconds.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } header: {
                Text("Analysis Options")
            }

            Section {
                HStack {
                    Text("Max Batch Size")
                    Spacer()
                    Text("12 images")
                        .foregroundColor(.secondary)
                }
                HStack {
                    Text("Max File Size")
                    Spacer()
                    Text("100 MB per image")
                        .foregroundColor(.secondary)
                }
            } header: {
                Text("Limits")
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - Privacy

    private var privacyTab: some View {
        Form {
            Section {
                HStack {
                    Image(systemName: "lock.fill")
                        .foregroundColor(.authenticGreen)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Local Processing Only")
                            .font(.system(size: 13, weight: .semibold))
                        Text("All analysis is performed on your Mac. No images or data are uploaded to any server.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.authenticGreen)
                }
                .padding(.vertical, 4)

                HStack {
                    Image(systemName: "eye.slash.fill")
                        .foregroundColor(.authenticGreen)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("No Image Retention")
                            .font(.system(size: 13, weight: .semibold))
                        Text("Images are never stored by the application beyond your current session.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.authenticGreen)
                }
                .padding(.vertical, 4)

                HStack {
                    Image(systemName: "network.slash")
                        .foregroundColor(.authenticGreen)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("No Network Required")
                            .font(.system(size: 13, weight: .semibold))
                        Text("The application works fully offline. No network access is requested.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.authenticGreen)
                }
                .padding(.vertical, 4)
            } header: {
                Text("Privacy Guarantees")
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - About

    private var aboutTab: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "camera.viewfinder")
                .font(.system(size: 44, weight: .thin))
                .foregroundStyle(
                    LinearGradient(colors: [.accentTeal, .blue],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                )

            VStack(spacing: 4) {
                Text("Validate My Photo")
                    .font(.system(size: 18, weight: .bold))
                Text("Version \(appVersion)")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
                Text("by Mosko Photo Labs")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.accentTeal)
            }

            Text("Multi-layer AI image authenticity detection using metadata forensics, pixel analysis, frequency domain analysis, and AI pattern recognition.")
                .font(.system(size: 12))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Spacer()

            Text("© 2025 Mosko Photo Labs. All rights reserved.")
                .font(.system(size: 10))
                .foregroundColor(.secondary)
                .padding(.bottom, 12)
        }
    }

    // MARK: - Helpers

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0"
    }

    private func chooseExportDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Choose"
        if panel.runModal() == .OK, let url = panel.url {
            exportDirectory = url.path
        }
    }
}
