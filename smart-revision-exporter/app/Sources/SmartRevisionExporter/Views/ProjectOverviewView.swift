import SRXCore
import SwiftUI

struct ProjectOverviewView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        VStack(spacing: 14) {
            Card(title: "DaVinci Resolve", trailing: AnyView(refreshButton)) {
                if let r = model.resolve, r.connected {
                    HStack(spacing: 8) {
                        StatusDot(color: Theme.success)
                        Text("Connected").font(Theme.title).foregroundStyle(Theme.textPrimary)
                        Spacer()
                        Text(r.version).font(Theme.monoSmall).foregroundStyle(Theme.textTertiary)
                    }
                    KeyValueRow(key: "Project", value: r.project)
                    KeyValueRow(key: "Timeline", value: r.timeline)
                    KeyValueRow(key: "Frame rate", value: r.rate?.displayName ?? "—")
                    KeyValueRow(key: "Start", value: r.startTimecode, mono: true)
                    KeyValueRow(key: "Resolution", value: "\(r.width) × \(r.height)")
                    Toggle("Render revisions with Resolve", isOn: $model.useResolve)
                        .font(.system(size: 12))
                        .toggleStyle(.switch)
                        .controlSize(.small)
                } else {
                    HStack(alignment: .top, spacing: 8) {
                        StatusDot(color: Theme.failure).padding(.top, 4)
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Not connected").font(Theme.title).foregroundStyle(Theme.textPrimary)
                            Text(model.resolve?.error ?? "Checking…")
                                .font(.system(size: 11))
                                .foregroundStyle(Theme.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    ManualRendersSection()
                }
            }

            Card(title: "Master") {
                if let m = model.master {
                    HStack {
                        Image(systemName: "film").foregroundStyle(Theme.accent)
                        Text(m.fileName).font(Theme.title).foregroundStyle(Theme.textPrimary)
                            .lineLimit(1).truncationMode(.middle)
                        Spacer()
                        Pill(text: m.patchable ? "PATCHABLE" : "NOT PATCHABLE",
                             color: m.patchable ? Theme.success : Theme.failure)
                    }
                    KeyValueRow(key: "Resolution", value: "\(m.width) × \(m.height)")
                    KeyValueRow(key: "Frame rate", value: "\(m.rate.displayName) (\(m.rate.description))")
                    KeyValueRow(key: "Duration",
                                value: Timecode.string(from: m.frameCount, rate: m.rate) + " · \(m.frameCount) frames",
                                mono: true)
                    KeyValueRow(key: "Codec", value: m.codecLine)
                    KeyValueRow(key: "GOP", value: m.gopLine)
                    KeyValueRow(key: "Colour", value: m.colorLine)
                    KeyValueRow(key: "Audio", value: m.audioLine)
                    ForEach(m.blockingIssues, id: \.self) { issue in
                        Label(issue, systemImage: "exclamationmark.octagon.fill")
                            .font(.system(size: 11)).foregroundStyle(Theme.failure)
                    }
                    ForEach(m.warnings, id: \.self) { w in
                        Label(w, systemImage: "exclamationmark.triangle.fill")
                            .font(.system(size: 11)).foregroundStyle(Theme.warning)
                    }
                    if !(model.resolve?.connected ?? false) {
                        HStack {
                            Text("Master starts at").font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
                            TimecodeField(frame: Binding(get: { model.timelineStartFrame },
                                                         set: { model.timelineStartFrame = $0 }),
                                          rate: m.rate, dropFrame: model.dropFrame, absolute: true)
                        }
                    }
                    Button("Choose Different Master…") { model.chooseMaster() }
                        .buttonStyle(QuietButtonStyle())
                } else {
                    Text("Select the previously approved H.264 MP4. It is opened read-only and never modified.")
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                    Button {
                        model.chooseMaster()
                    } label: {
                        Label(model.masterLoading ? "Analysing…" : "Choose Master…", systemImage: "folder")
                    }
                    .buttonStyle(QuietButtonStyle())
                    .disabled(model.masterLoading)
                }
            }
        }
    }

    var refreshButton: some View {
        Button {
            Task { await model.refreshResolve() }
        } label: {
            Image(systemName: "arrow.clockwise")
                .rotationEffect(.degrees(model.resolveBusy ? 360 : 0))
                .animation(model.resolveBusy ? .linear(duration: 1).repeatForever(autoreverses: false) : .default,
                           value: model.resolveBusy)
        }
        .buttonStyle(.plain)
        .foregroundStyle(Theme.textSecondary)
        .help("Reconnect to DaVinci Resolve")
    }
}

/// Fallback when Resolve's external scripting is unavailable.
struct ManualRendersSection: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Without scripting access, render the ranges listed by Smart Export yourself "
                 + "(ProRes 422 HQ, Linear PCM) and import them here.")
                .font(.system(size: 11))
                .foregroundStyle(Theme.textTertiary)
                .fixedSize(horizontal: false, vertical: true)
            ForEach($model.manualRenders) { $r in
                HStack {
                    Text((r.path as NSString).lastPathComponent)
                        .font(.system(size: 11)).lineLimit(1).truncationMode(.middle)
                    Spacer()
                    TimecodeField(frame: $r.timelineStartFrame, rate: model.rate, dropFrame: model.dropFrame,
                                  absolute: true)
                    Button {
                        model.manualRenders.removeAll { $0.id == r.id }
                    } label: { Image(systemName: "xmark.circle.fill") }
                        .buttonStyle(.plain).foregroundStyle(Theme.textTertiary)
                }
            }
            Button("Import Render…") { model.addManualRender() }
                .buttonStyle(QuietButtonStyle())
        }
    }
}

/// Frame-accurate timecode entry.  `absolute` = value is an absolute timeline
/// frame; otherwise a master frame (converted with the timeline start).
struct TimecodeField: View {
    @EnvironmentObject var model: AppModel
    @Binding var frame: Int
    let rate: FrameRate
    let dropFrame: Bool
    var absolute: Bool = false
    @State private var text = ""
    @State private var invalid = false
    @FocusState private var focused: Bool

    var body: some View {
        TextField("", text: $text)
            .font(Theme.monoSmall)
            .textFieldStyle(.plain)
            .multilineTextAlignment(.center)
            .frame(width: 92)
            .padding(.vertical, 4)
            .background(RoundedRectangle(cornerRadius: 5).fill(Theme.surfaceRaised))
            .overlay(RoundedRectangle(cornerRadius: 5).stroke(invalid ? Theme.failure : Theme.hairline))
            .focused($focused)
            .onAppear { text = format(frame) }
            .onChange(of: frame) { f in if !focused { text = format(f) } }
            .onSubmit(commit)
            .onChange(of: focused) { f in if !f { commit() } }
            .help("HH:MM:SS:FF (use ; for drop-frame). Enter a plain number for frames.")
    }

    func format(_ f: Int) -> String {
        Timecode.string(from: absolute ? f : model.timelineStartFrame + f, rate: rate, dropFrame: dropFrame)
    }

    func commit() {
        let t = text.trimmingCharacters(in: .whitespaces)
        if let n = Int(t) {
            frame = n
            invalid = false
        } else if let abs = try? Timecode.frames(from: t, rate: rate, dropFrame: dropFrame ? true : nil) {
            frame = absolute ? abs : abs - model.timelineStartFrame
            invalid = false
        } else {
            invalid = true
            return
        }
        text = format(frame)
    }
}
