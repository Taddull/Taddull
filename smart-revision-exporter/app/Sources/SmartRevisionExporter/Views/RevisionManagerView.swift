import SRXCore
import SwiftUI

struct RevisionManagerView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("REVISIONS")
                    .font(Theme.caption).tracking(0.8).foregroundStyle(Theme.textTertiary)
                if !model.revisions.items.isEmpty {
                    Text("\(model.revisions.items.count) · \(Timecode.durationText(frames: model.revisions.totalFrames, rate: model.rate))")
                        .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
                }
                Spacer()
                Button { model.addRevisionAtPlayhead() } label: { Label("Add", systemImage: "plus") }
                    .buttonStyle(QuietButtonStyle()).disabled(model.master == nil)
                Button { Task { await model.importResolveRanges(markersOnly: false) } } label: {
                    Label("Import In/Out", systemImage: "arrow.down.to.line")
                }
                .buttonStyle(QuietButtonStyle())
                .disabled(model.master == nil || !(model.resolve?.connected ?? false))
                Button { Task { await model.importResolveRanges(markersOnly: true) } } label: {
                    Label("Import Markers", systemImage: "bookmark")
                }
                .buttonStyle(QuietButtonStyle())
                .disabled(model.master == nil || !(model.resolve?.connected ?? false))
                .help("Duration markers become revision ranges (marker name may start with REV)")
                Button { model.mergeRevisions() } label: { Label("Merge", systemImage: "arrow.triangle.merge") }
                    .buttonStyle(QuietButtonStyle())
                    .disabled(!model.revisions.hasOverlaps)
            }
            if model.revisions.items.isEmpty {
                EmptyRevisionsHint()
            } else {
                header
                ScrollView {
                    VStack(spacing: 6) {
                        ForEach(model.revisions.items) { r in
                            RevisionRow(revision: r, issues: issues(for: r.id))
                        }
                    }
                }
            }
            if let e = model.planError {
                Label(e, systemImage: "exclamationmark.triangle.fill")
                    .font(.system(size: 11)).foregroundStyle(Theme.warning)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Theme.corner).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: Theme.corner).stroke(Theme.hairline))
    }

    var header: some View {
        HStack(spacing: 10) {
            Text("Label").frame(width: 150, alignment: .leading)
            Text("In").frame(width: 96)
            Text("Out (incl.)").frame(width: 96)
            Text("Duration").frame(width: 110, alignment: .leading)
            Text("V / A").frame(width: 70)
            Text("Handles").frame(width: 120)
            Spacer()
        }
        .font(.system(size: 10, weight: .semibold))
        .foregroundStyle(Theme.textTertiary)
    }

    func issues(for id: UUID) -> [String] {
        model.revisions.issues(frameCount: model.frameCount).compactMap { i in
            switch i {
            case .empty(let x) where x == id: return "Out must be after In"
            case .outOfBounds(let x) where x == id: return "Outside the master"
            case .nothingSelected(let x) where x == id: return "Select video and/or audio"
            case .overlaps(let a, let b) where a == id || b == id: return "Overlaps another revision"
            case .adjacent(let a, let b) where a == id || b == id: return "Touches another revision"
            default: return nil
            }
        }
    }
}

struct EmptyRevisionsHint: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("No revision ranges yet.")
                .font(.system(size: 13, weight: .medium)).foregroundStyle(Theme.textPrimary)
            Text("Set In/Out around the revised section in Resolve and choose Import In/Out, mark it with a "
                 + "duration marker, or add a range at the playhead and type exact timecodes. Include the full "
                 + "length of any transition that changed.")
                .font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 8)
    }
}

struct RevisionRow: View {
    @EnvironmentObject var model: AppModel
    let revision: RevisionRange
    let issues: [String]
    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 10) {
                TextField("Label", text: bind(\.label))
                    .textFieldStyle(.plain)
                    .font(.system(size: 12, weight: .medium))
                    .frame(width: 150)
                TimecodeField(frame: bind(\.start), rate: model.rate, dropFrame: model.dropFrame)
                TimecodeField(frame: Binding(get: { revision.end - 1 }, set: { v in
                    var r = revision
                    r.end = v + 1
                    model.update(r)
                }), rate: model.rate, dropFrame: model.dropFrame)
                Text(Timecode.durationText(frames: revision.length, rate: model.rate))
                    .font(Theme.monoSmall).foregroundStyle(Theme.textSecondary)
                    .frame(width: 110, alignment: .leading)
                HStack(spacing: 4) {
                    Toggle("V", isOn: bind(\.video)).toggleStyle(.button).controlSize(.small)
                    Toggle("A", isOn: bind(\.audio)).toggleStyle(.button).controlSize(.small)
                }
                .frame(width: 70)
                HStack(spacing: 2) {
                    Stepper(value: bind(\.handlesBefore), in: 0...240) {
                        Text("\(revision.handlesBefore)").font(Theme.monoSmall).frame(width: 22)
                    }
                    Stepper(value: bind(\.handlesAfter), in: 0...240) {
                        Text("\(revision.handlesAfter)").font(Theme.monoSmall).frame(width: 22)
                    }
                }
                .controlSize(.mini)
                .frame(width: 120)
                .help("Extra frames replaced before/after (transitions, temporal effects)")
                Spacer()
                Button { model.setPlayhead(revision.start) } label: { Image(systemName: "scope") }
                    .buttonStyle(.plain).foregroundStyle(Theme.textSecondary).help("Go to In")
                Button { model.remove(revision.id) } label: { Image(systemName: "trash") }
                    .buttonStyle(.plain).foregroundStyle(hovering ? Theme.failure : Theme.textTertiary)
            }
            ForEach(issues, id: \.self) { i in
                Text(i).font(.system(size: 10)).foregroundStyle(Theme.warning)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(RoundedRectangle(cornerRadius: 7).fill(Theme.surfaceRaised.opacity(hovering ? 1 : 0.6)))
        .overlay(alignment: .leading) {
            RoundedRectangle(cornerRadius: 2).fill(Theme.accent).frame(width: 3).padding(.vertical, 6)
        }
        .onHover { hovering = $0 }
    }

    func bind<T>(_ kp: WritableKeyPath<RevisionRange, T>) -> Binding<T> {
        Binding(get: { revision[keyPath: kp] }, set: { v in
            var r = revision
            r[keyPath: kp] = v
            model.update(r)
        })
    }
}
