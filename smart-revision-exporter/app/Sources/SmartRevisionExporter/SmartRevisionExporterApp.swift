import SRXCore
import SwiftUI

@main
struct SmartRevisionExporterApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup("Smart Revision Exporter") {
            ContentView()
                .environmentObject(model)
                .preferredColorScheme(.dark)
                .frame(minWidth: 1180, minHeight: 760)
                .onAppear { model.bootstrap() }
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Open Master…") { model.chooseMaster() }
                    .keyboardShortcut("o", modifiers: .command)
            }
            CommandMenu("Revision") {
                Button("Add Revision at Playhead") { model.addRevisionAtPlayhead() }
                    .keyboardShortcut("r", modifiers: [.command, .shift])
                    .disabled(model.master == nil)
                Button("Import Resolve In/Out") { Task { await model.importResolveRanges(markersOnly: false) } }
                    .keyboardShortcut("i", modifiers: [.command, .shift])
                Button("Import Resolve Range Markers") { Task { await model.importResolveRanges(markersOnly: true) } }
                Button("Merge Overlapping Revisions") { model.mergeRevisions() }
                Divider()
                Button("Smart Export") { model.startExport() }
                    .keyboardShortcut("e", modifiers: .command)
                    .disabled(!model.canExport)
                Button("Cancel Export") { model.cancelExport() }
                    .keyboardShortcut(".", modifiers: .command)
                    .disabled(!model.running)
            }
            CommandGroup(after: .help) {
                Button("Diagnostics…") { model.showDiagnostics = true }
            }
        }
    }
}
