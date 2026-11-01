import SRXCore
import SwiftUI

struct ExportProgressView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        HStack(alignment: .top, spacing: 24) {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(stages) { s in
                    StageRow(stage: s, state: state(of: s),
                             fraction: model.currentStage == s ? model.stageFraction : nil)
                }
            }
            .frame(width: 270)

            VStack(alignment: .leading, spacing: 12) {
                if let s = model.currentStage, model.running {
                    Text(s.title).font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.textPrimary)
                    ProgressView(value: model.stageFraction)
                        .progressViewStyle(.linear)
                        .tint(Theme.accent)
                    HStack {
                        Text(model.stageMessage).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
                            .lineLimit(2)
                        Spacer()
                        Text(String(format: "%.0f%%", model.stageFraction * 100)).font(Theme.monoSmall)
                        if let eta = model.eta {
                            Text("· \(etaText(eta)) left").font(Theme.monoSmall).foregroundStyle(Theme.textSecondary)
                        }
                    }
                } else if let err = model.exportError {
                    Label(err, systemImage: "xmark.octagon.fill")
                        .font(.system(size: 12)).foregroundStyle(Theme.failure)
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                } else if model.report?.passed == true {
                    Label("Export complete and verified", systemImage: "checkmark.seal.fill")
                        .font(.system(size: 14, weight: .semibold)).foregroundStyle(Theme.success)
                }
                if let st = model.stats, model.running {
                    HStack(spacing: 18) {
                        stat("Engine CPU", "\(st["engine_cpu_percent"]?.int ?? 0)%")
                        stat("FFmpeg CPU", "\(st["child_cpu_percent"]?.int ?? 0)%")
                        stat("Memory", "\((st["engine_rss_mb"]?.int ?? 0) + (st["child_rss_mb"]?.int ?? 0)) MB")
                        stat("Load", String(format: "%.1f", st["load_avg"]?.double ?? 0))
                    }
                }
                if !model.warnings.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(model.warnings.enumerated()), id: \.offset) { _, w in
                            Label(w, systemImage: "exclamationmark.triangle.fill")
                                .font(.system(size: 11)).foregroundStyle(Theme.warning)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                Spacer(minLength: 0)
            }
        }
    }

    var stages: [ExportStage] {
        model.mode.isPatch ? ExportStage.allCases : [.render, .encode, .assemble, .verify]
    }

    func state(of s: ExportStage) -> StageRow.State {
        if model.completedStages.contains(s) { return .done }
        if model.currentStage == s { return model.running ? .active : (model.exportError != nil ? .failed : .done) }
        return .pending
    }

    func stat(_ k: String, _ v: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(k).font(.system(size: 9, weight: .medium)).foregroundStyle(Theme.textTertiary)
            Text(v).font(.system(size: 12, weight: .semibold, design: .rounded)).foregroundStyle(Theme.textPrimary)
        }
    }

    func etaText(_ s: Double) -> String {
        s >= 60 ? String(format: "%d min %02d s", Int(s) / 60, Int(s) % 60) : String(format: "%.0f s", s)
    }
}

struct StageRow: View {
    enum State { case pending, active, done, failed }
    let stage: ExportStage
    let state: State
    let fraction: Double?

    var body: some View {
        HStack(spacing: 10) {
            ZStack {
                switch state {
                case .done: Image(systemName: "checkmark.circle.fill").foregroundStyle(Theme.success)
                case .active: ProgressView().controlSize(.small).scaleEffect(0.7)
                case .failed: Image(systemName: "xmark.circle.fill").foregroundStyle(Theme.failure)
                case .pending: Image(systemName: "circle").foregroundStyle(Theme.textTertiary)
                }
            }
            .frame(width: 16, height: 16)
            Text(stage.title)
                .font(.system(size: 12, weight: state == .active ? .semibold : .regular))
                .foregroundStyle(state == .pending ? Theme.textTertiary : Theme.textPrimary)
            Spacer()
            if let f = fraction, state == .active {
                Text(String(format: "%.0f%%", f * 100)).font(Theme.monoSmall).foregroundStyle(Theme.textSecondary)
            }
        }
    }
}
