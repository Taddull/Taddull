import SRXCore
import SwiftUI

/// Shown only once the engine has finished verification - never earlier.
struct VerificationReportView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        if let rep = model.report {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    header(rep)
                    metrics(rep)
                    checks(rep)
                    audio(rep)
                    encoding(rep)
                    if !rep.failures.isEmpty || !rep.warnings.isEmpty { notes(rep) }
                }
            }
        } else if model.running {
            Text("The verification report appears when the export has been fully verified.")
                .font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
        } else {
            Text("No report yet.").font(.system(size: 12)).foregroundStyle(Theme.textTertiary)
        }
    }

    func header(_ rep: VerificationReport) -> some View {
        HStack(spacing: 12) {
            Image(systemName: rep.passed ? "checkmark.seal.fill" : "xmark.seal.fill")
                .font(.system(size: 26))
                .foregroundStyle(rep.passed ? Theme.success : Theme.failure)
            VStack(alignment: .leading, spacing: 2) {
                Text(rep.passed ? "Verified" : "Verification failed - output NOT delivered")
                    .font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.textPrimary)
                Text(rep.level == "full" ? "Full decode: every frame of the output compared"
                     : "Fast: splice neighbourhoods decoded; other unchanged frames are packet copies")
                    .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
            Spacer()
            if rep.passed && model.resultOutput != nil {
                Button("Reveal in Finder") { model.revealOutput() }.buttonStyle(QuietButtonStyle())
                Button(model.approved ? "Approved ✓" : "Approve as New Base") {
                    Task { await model.approveOutput() }
                }
                .buttonStyle(QuietButtonStyle())
                .disabled(model.approved)
                .help("Record this verified output as the approved master for the next revision cycle")
            }
            if model.reportPath != nil {
                Button("Open Report") { model.openReport() }.buttonStyle(QuietButtonStyle())
            }
        }
    }

    func metrics(_ rep: VerificationReport) -> some View {
        let cols = [GridItem(.adaptive(minimum: 150), spacing: 10)]
        return LazyVGrid(columns: cols, alignment: .leading, spacing: 10) {
            tile("Original frames", rep.video("master_frames")?.string ?? "—")
            tile("Final frames", rep.video("output_frames")?.string ?? "—")
            tile("Unchanged compared", rep.video("compared_unchanged")?.string ?? "—")
            tile("Pixel-identical", rep.video("identical_unchanged")?.string ?? "—",
                 good: rep.video("identical_unchanged")?.int == rep.video("compared_unchanged")?.int)
            tile("Re-encoded", rep.video("reencoded_frames")?.string ?? "—")
            tile("Boundary (unchanged content)", rep.video("boundary_frames")?.string ?? "—")
            tile("Encode PSNR min", psnr(rep.video("encode_fidelity_psnr_y")?["min"]))
            tile("Boundary vs master min", psnr(rep.video("boundary_render_vs_master_psnr_min_plane")?["min"]))
        }
    }

    func tile(_ k: String, _ v: String, good: Bool? = nil) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(k).font(.system(size: 10, weight: .medium)).foregroundStyle(Theme.textTertiary)
            Text(v).font(.system(size: 15, weight: .semibold, design: .rounded))
                .foregroundStyle(good == false ? Theme.failure : Theme.textPrimary)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 7).fill(Theme.surfaceRaised))
    }

    func psnr(_ v: JSONValue?) -> String {
        guard let d = v?.double else { return "—" }
        return d.isInfinite ? "∞ (identical)" : String(format: "%.2f dB", d)
    }

    func checks(_ rep: VerificationReport) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("CHECKS").font(Theme.caption).tracking(0.8).foregroundStyle(Theme.textTertiary)
            ForEach(rep.checks) { c in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: icon(c.status)).foregroundStyle(color(c.status)).frame(width: 14)
                    Text(c.name.replacingOccurrences(of: "_", with: " "))
                        .font(.system(size: 11, weight: .semibold)).foregroundStyle(Theme.textPrimary)
                        .frame(width: 160, alignment: .leading)
                    Text(c.detail).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    func audio(_ rep: VerificationReport) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("AUDIO").font(Theme.caption).tracking(0.8).foregroundStyle(Theme.textTertiary)
            if rep.audio.isEmpty {
                Text("No audio tracks").font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
            ForEach(Array(rep.audio.enumerated()), id: \.offset) { _, a in
                Text("Track \(a["index"]?.int ?? 0): \(a["strategy"]?.string ?? "") - \(a["reason"]?.string ?? "")")
                    .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
        }
    }

    func encoding(_ rep: VerificationReport) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("ENCODING").font(Theme.caption).tracking(0.8).foregroundStyle(Theme.textTertiary)
            if let x = rep.x264Params {
                Text("libx264 · \(x)").font(Theme.monoSmall).foregroundStyle(Theme.textSecondary).textSelection(.enabled)
            }
            if let sha = rep.outputSHA {
                Text("Output SHA-256 \(sha)").font(Theme.monoSmall).foregroundStyle(Theme.textTertiary)
                    .textSelection(.enabled)
            }
            let t = rep.timings
            if !t.isEmpty {
                Text(t.map { "\($0.0) \(String(format: "%.1f", $0.1)) s" }.joined(separator: " · "))
                    .font(Theme.monoSmall).foregroundStyle(Theme.textTertiary)
            }
        }
    }

    func notes(_ rep: VerificationReport) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(rep.failures.enumerated()), id: \.offset) { _, f in
                Label(f, systemImage: "xmark.octagon.fill").font(.system(size: 11)).foregroundStyle(Theme.failure)
                    .fixedSize(horizontal: false, vertical: true)
            }
            ForEach(Array(rep.warnings.enumerated()), id: \.offset) { _, w in
                Label(w, systemImage: "exclamationmark.triangle.fill").font(.system(size: 11))
                    .foregroundStyle(Theme.warning).fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    func icon(_ s: String) -> String {
        switch s {
        case "pass": return "checkmark.circle.fill"
        case "fail": return "xmark.circle.fill"
        case "warn": return "exclamationmark.triangle.fill"
        default: return "minus.circle"
        }
    }

    func color(_ s: String) -> Color {
        switch s {
        case "pass": return Theme.success
        case "fail": return Theme.failure
        case "warn": return Theme.warning
        default: return Theme.textTertiary
        }
    }
}
