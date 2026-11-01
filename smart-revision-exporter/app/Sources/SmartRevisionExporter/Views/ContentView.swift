import SRXCore
import SwiftUI

struct ContentView: View {
    @EnvironmentObject var model: AppModel
    @State private var bottomTab = 0

    var body: some View {
        HStack(spacing: 0) {
            ScrollView {
                VStack(spacing: 14) {
                    ProjectOverviewView()
                    ExportSettingsView()
                }
                .padding(16)
            }
            .frame(width: 340)
            .background(Theme.background)

            Rectangle().fill(Theme.hairline).frame(width: 1)

            VStack(spacing: 14) {
                HeaderBar()
                TimelineView()
                RevisionManagerView()
                    .frame(minHeight: 160)
                if model.running || model.report != nil || model.exportError != nil || !model.log.isEmpty {
                    BottomPanel(tab: $bottomTab)
                        .frame(minHeight: 230, idealHeight: 280)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .padding(16)
            .background(Theme.background)
            .animation(.easeInOut(duration: 0.25), value: model.running)
        }
        .background(Theme.background)
        .sheet(isPresented: $model.showDiagnostics) { DiagnosticsView().environmentObject(model) }
        .onChange(of: model.report != nil) { has in if has { bottomTab = 1 } }
        .onChange(of: model.running) { r in if r { bottomTab = 0 } }
        .onChange(of: model.mode) { _ in model.schedulePlan() }
    }
}

struct HeaderBar: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Smart Revision Exporter")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Theme.textPrimary)
                Text(subtitle)
                    .font(.system(size: 12))
                    .foregroundStyle(Theme.textSecondary)
            }
            Spacer()
            if let p = model.plan, model.mode.isPatch {
                PlanBadge(plan: p)
            }
            if model.running {
                Button("Cancel") { model.cancelExport() }
                    .buttonStyle(QuietButtonStyle())
            }
            Button {
                model.startExport()
            } label: {
                Label(model.mode.isPatch ? "Smart Export" : model.mode.title, systemImage: "bolt.fill")
            }
            .buttonStyle(PrimaryButtonStyle(enabled: model.canExport))
            .disabled(!model.canExport)
            .help(exportHelp)
        }
    }

    var subtitle: String {
        if let m = model.master {
            return "\(m.fileName) · \(model.revisions.items.count) revision(s) · \(model.mode.title)"
        }
        return "Open the approved master to begin"
    }

    var exportHelp: String {
        if model.master == nil && model.mode.isPatch { return "Choose the master file first." }
        if model.revisions.items.isEmpty && model.mode.isPatch { return "Add at least one revision range." }
        if !(model.resolve?.connected ?? false) && model.manualRenders.isEmpty {
            return "Connect DaVinci Resolve or import manual renders."
        }
        return model.mode.summary
    }
}

struct PlanBadge: View {
    let plan: PlanSummary

    var body: some View {
        HStack(spacing: 14) {
            metric(String(format: "%.1f%%", plan.stat("rendered_percent")), "rendered")
            metric("\(Int(plan.stat("reencoded_frames")))", "re-encoded")
            metric("\(Int(plan.stat("boundary_frames")))", "boundary")
            metric(String(format: "%.1f%%", plan.stat("preserved_percent")), "copied")
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(RoundedRectangle(cornerRadius: 8).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.hairline))
    }

    func metric(_ v: String, _ k: String) -> some View {
        VStack(spacing: 1) {
            Text(v).font(.system(size: 13, weight: .semibold, design: .rounded)).foregroundStyle(Theme.textPrimary)
            Text(k).font(.system(size: 9, weight: .medium)).foregroundStyle(Theme.textTertiary)
        }
    }
}

struct BottomPanel: View {
    @EnvironmentObject var model: AppModel
    @Binding var tab: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Picker("", selection: $tab) {
                    Text("Progress").tag(0)
                    Text("Verification Report").tag(1)
                    Text("Log").tag(2)
                }
                .pickerStyle(.segmented)
                .frame(width: 360)
                Spacer()
            }
            Group {
                switch tab {
                case 0: ExportProgressView()
                case 1: VerificationReportView()
                default: LogView()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Theme.corner).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: Theme.corner).stroke(Theme.hairline))
    }
}

struct LogView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 2) {
                    ForEach(model.log) { ev in
                        Text(line(ev))
                            .font(Theme.monoSmall)
                            .foregroundStyle(color(ev))
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .id(ev.id)
                    }
                }
            }
            .onChange(of: model.log.count) { _ in
                if let last = model.log.last { proxy.scrollTo(last.id, anchor: .bottom) }
            }
        }
    }

    func line(_ ev: EngineEvent) -> String {
        switch ev.type {
        case "stage": return "== \(ev.stage): \(ev.message)"
        case "plan": return "plan received"
        case "master": return "master analysed"
        case "job": return "job \(ev.body["id"]?.string ?? "") · \(ev.body["dir"]?.string ?? "")"
        case "result": return "result: \(ev.body["status"]?.string ?? "") → \(ev.body["output"]?.string ?? "")"
        default: return "\(ev.type): \(ev.message)"
        }
    }

    func color(_ ev: EngineEvent) -> Color {
        switch ev.type {
        case "error": return Theme.failure
        case "warning": return Theme.warning
        case "stage", "result": return Theme.textPrimary
        default: return Theme.textSecondary
        }
    }
}
