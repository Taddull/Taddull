import SRXCore
import SwiftUI

struct ExportSettingsView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        Card(title: "Export") {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(ExportMode.allCases) { m in
                    ModeRow(mode: m, selected: model.mode == m) { model.mode = m }
                }
            }
            Divider().overlay(Theme.hairline)
            if model.mode.isPatch {
                Toggle(isOn: $model.strict) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Strict frame preservation").font(.system(size: 12, weight: .medium))
                        Text("Refuse if any unchanged frame would be re-encoded")
                            .font(.system(size: 10)).foregroundStyle(Theme.textTertiary)
                    }
                }
                .toggleStyle(.switch).controlSize(.small)
                .onChange(of: model.strict) { _ in model.schedulePlan() }
                Picker("Audio", selection: $model.audio) {
                    ForEach(AudioStrategy.allCases) { Text($0.title).tag($0) }
                }
                .onChange(of: model.audio) { _ in model.schedulePlan() }
                Picker("Patch quality", selection: $model.quality) {
                    ForEach(PatchQuality.allCases) { Text($0.title).tag($0) }
                }
                Picker("x264 preset", selection: $model.encoderPreset) {
                    ForEach(["medium", "slow", "slower", "veryslow"], id: \.self) { Text($0).tag($0) }
                }
            }
            if model.mode == .revisionReadyMaster {
                Toggle("All-intra (every frame an IDR)", isOn: $model.rrAllIntra)
                    .toggleStyle(.switch).controlSize(.small).font(.system(size: 12))
                if !model.rrAllIntra {
                    Picker("Keyframe interval", selection: $model.rrGopSeconds) {
                        Text("0.5 s").tag(0.5)
                        Text("1 s").tag(1.0)
                        Text("2 s").tag(2.0)
                    }
                }
                Text(model.rrAllIntra
                     ? "Every frame outside a revision stays pixel-identical in future patches. Files are typically 3–6× larger."
                     : "Future patches re-encode at most one interval of unchanged frames after each revision. "
                       + "Size overhead is small (a few percent at 1–2 s).")
                    .font(.system(size: 10)).foregroundStyle(Theme.textTertiary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if model.mode == .safeFullExport {
                if let presets = model.resolve?.renderPresets, !presets.isEmpty {
                    Picker("Resolve preset", selection: $model.resolvePreset) {
                        Text("Match master (engine encode)").tag("")
                        ForEach(presets, id: \.self) { Text($0).tag($0) }
                    }
                }
                Text("Renders the entire timeline. The result is checked against the current master for frame rate, "
                     + "resolution, colour tags and frame count; it never replaces the master.")
                    .font(.system(size: 10)).foregroundStyle(Theme.textTertiary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Divider().overlay(Theme.hairline)
            VStack(alignment: .leading, spacing: 6) {
                Text("Output").font(.system(size: 12, weight: .medium)).foregroundStyle(Theme.textSecondary)
                HStack {
                    Text(model.outputPath.isEmpty ? "Not set" : (model.outputPath as NSString).lastPathComponent)
                        .font(.system(size: 12)).lineLimit(1).truncationMode(.middle)
                        .foregroundStyle(model.outputPath.isEmpty ? Theme.textTertiary : Theme.textPrimary)
                    Spacer()
                    Button("Choose…") { model.chooseOutput() }.buttonStyle(QuietButtonStyle())
                }
                Text("A new file is always written; the master is never overwritten.")
                    .font(.system(size: 10)).foregroundStyle(Theme.textTertiary)
            }
        }
        .font(.system(size: 12))
    }
}

struct ModeRow: View {
    let mode: ExportMode
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: selected ? "largecircle.fill.circle" : "circle")
                    .foregroundStyle(selected ? Theme.accent : Theme.textTertiary)
                    .padding(.top, 1)
                VStack(alignment: .leading, spacing: 3) {
                    HStack {
                        Text(mode.title).font(.system(size: 12, weight: .semibold)).foregroundStyle(Theme.textPrimary)
                        if mode == .verifiedPatch { Pill(text: "RECOMMENDED", color: Theme.success) }
                    }
                    if selected {
                        Text(mode.summary)
                            .font(.system(size: 10.5))
                            .foregroundStyle(Theme.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                            .transition(.opacity)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(8)
            .background(RoundedRectangle(cornerRadius: 7).fill(selected ? Theme.surfaceRaised : Color.clear))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.18), value: selected)
    }
}
