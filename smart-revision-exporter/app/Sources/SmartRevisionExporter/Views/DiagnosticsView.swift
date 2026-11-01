import SRXCore
import SwiftUI

struct DiagnosticsView: View {
    @EnvironmentObject var model: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var installing = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Diagnostics").font(.system(size: 17, weight: .semibold))
                Spacer()
                Button("Close") { dismiss() }.buttonStyle(QuietButtonStyle())
            }
            if let e = model.engineError {
                Label(e, systemImage: "xmark.octagon.fill").foregroundStyle(Theme.failure).font(.system(size: 12))
            }
            HStack {
                Text("Python 3").font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
                TextField("auto-detect", text: $model.pythonPath)
                    .textFieldStyle(.roundedBorder)
                    .font(Theme.monoSmall)
                Button("Re-check") {
                    model.resetEngine()
                    Task { await model.runDoctor() }
                }
                .buttonStyle(QuietButtonStyle())
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 6) {
                    if let d = model.doctor {
                        KeyValueRow(key: "Engine", value: "\(d["engine_version"]?.string ?? "?") · \(d["build"]?.string ?? "")")
                        KeyValueRow(key: "Platform", value: d["platform"]?.string ?? "", mono: true)
                        KeyValueRow(key: "Data folder", value: d["home"]?.string ?? "", mono: true)
                        ForEach(Array((d["checks"]?.array ?? []).enumerated()), id: \.offset) { _, c in
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: (c["ok"]?.bool ?? false) ? "checkmark.circle.fill"
                                      : ((c["required"]?.bool ?? true) ? "xmark.circle.fill" : "minus.circle"))
                                    .foregroundStyle((c["ok"]?.bool ?? false) ? Theme.success
                                                     : ((c["required"]?.bool ?? true) ? Theme.failure : Theme.textTertiary))
                                Text(c["name"]?.string ?? "").font(.system(size: 12, weight: .medium)).frame(width: 190, alignment: .leading)
                                Text(c["detail"]?.string ?? "").font(Theme.monoSmall).foregroundStyle(Theme.textSecondary)
                                    .textSelection(.enabled)
                            }
                        }
                    } else {
                        Text("Running checks…").foregroundStyle(Theme.textSecondary)
                    }
                    if let r = model.resolve {
                        Divider().padding(.vertical, 6)
                        Text("DaVinci Resolve scripting API").font(.system(size: 13, weight: .semibold))
                        if r.connected {
                            ForEach(r.apiReport, id: \.0) { name, ok in
                                HStack {
                                    Image(systemName: ok ? "checkmark" : "minus").foregroundStyle(ok ? Theme.success : Theme.textTertiary)
                                    Text(name).font(Theme.monoSmall)
                                }
                            }
                        } else {
                            Text(r.error ?? "Not connected").font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
                            Text("Open DaVinci Resolve with a project, then set Preferences ▸ System ▸ General ▸ "
                                 + "External scripting using: Local. Without scripting, use manual render import.")
                                .font(.system(size: 11)).foregroundStyle(Theme.textTertiary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
            HStack {
                Button(installing ? "Installing numpy…" : "Install numpy (faster verification)") {
                    installing = true
                    Task {
                        await model.installNumpy()
                        installing = false
                    }
                }
                .buttonStyle(QuietButtonStyle())
                .disabled(installing)
                Button("Recover Interrupted Jobs") { Task { await model.recoverJobs() } }
                    .buttonStyle(QuietButtonStyle())
                Button("Open Logs Folder") { model.openLogsFolder() }
                    .buttonStyle(QuietButtonStyle())
                Spacer()
            }
        }
        .padding(20)
        .frame(width: 720, height: 560)
        .background(Theme.background)
        .task { await model.runDoctor(silent: true) }
    }
}
