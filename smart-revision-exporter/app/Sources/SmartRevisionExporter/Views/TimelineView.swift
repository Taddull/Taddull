import SRXCore
import SwiftUI

/// Whole-programme timeline: preserved (grey), revised (blue), codec boundary
/// expansion (amber, hatched), guard renders (thin amber), IDR splice points
/// (ticks) and a frame-accurate playhead with preview.
struct TimelineView: View {
    @EnvironmentObject var model: AppModel
    @State private var zoom: Double = 1          // 1 = whole programme visible
    @State private var viewStart: Double = 0     // first visible frame
    @State private var dragging = false

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(alignment: .leading, spacing: 8) {
                toolbar
                GeometryReader { geo in
                    let width = geo.size.width
                    Canvas { ctx, size in draw(ctx: &ctx, size: size) }
                        .contentShape(Rectangle())
                        .gesture(DragGesture(minimumDistance: 0)
                            .onChanged { v in
                                dragging = true
                                model.setPlayhead(frame(atX: v.location.x, width: width))
                            }
                            .onEnded { _ in dragging = false })
                        .background(RoundedRectangle(cornerRadius: 8).fill(Theme.background))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.hairline))
                }
                .frame(height: 132)
                legend
            }
            PreviewInspector()
                .frame(width: 300)
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Theme.corner).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: Theme.corner).stroke(Theme.hairline))
        .background(keyboardShortcuts)
        .onChange(of: model.playhead) { f in keepVisible(f) }
    }

    // MARK: geometry

    var total: Double { Double(max(model.frameCount, 1)) }
    var span: Double { max(total / zoom, 10) }

    func x(_ frame: Int, _ width: CGFloat) -> CGFloat {
        CGFloat((Double(frame) - viewStart) / span) * width
    }

    func frame(atX px: CGFloat, width: CGFloat) -> Int {
        Int((viewStart + Double(px / max(width, 1)) * span).rounded(.down))
    }

    func keepVisible(_ f: Int) {
        let d = Double(f)
        if d < viewStart || d > viewStart + span {
            viewStart = max(0, min(total - span, d - span / 2))
        }
    }

    // MARK: drawing

    func draw(ctx: inout GraphicsContext, size: CGSize) {
        let w = size.width
        let rulerH: CGFloat = 20
        let laneTop: CGFloat = rulerH + 4
        let laneH = size.height - laneTop - 14
        guard model.frameCount > 0 else {
            ctx.draw(Text("Open a master to see its timeline").font(.system(size: 12)).foregroundColor(Theme.textTertiary),
                     at: CGPoint(x: w / 2, y: size.height / 2))
            return
        }
        // filmstrip background (whole programme, scaled into the visible window)
        if let img = model.filmstrip {
            let full = CGRect(x: x(0, w), y: laneTop, width: CGFloat(total / span) * w, height: laneH)
            ctx.opacity = 0.35
            ctx.draw(Image(nsImage: img).resizable(), in: full)
            ctx.opacity = 1
        }
        let lane = CGRect(x: 0, y: laneTop, width: w, height: laneH)
        ctx.fill(Path(lane), with: .color(Theme.preserved))

        // planned render segments
        if let plan = model.plan, model.mode.isPatch {
            for s in plan.segments where s.kind == "render" {
                let gx0 = x(s.renderStart, w), gx1 = x(s.renderEnd, w)
                ctx.fill(Path(CGRect(x: gx0, y: laneTop + laneH - 3, width: max(1, gx1 - gx0), height: 3)),
                         with: .color(Theme.boundary.opacity(0.5)))
                let bx0 = x(s.outStart, w), bx1 = x(s.outEnd, w)
                let rect = CGRect(x: bx0, y: laneTop, width: max(1, bx1 - bx0), height: laneH - 4)
                ctx.fill(Path(rect), with: .color(Theme.boundary.opacity(0.35)))
                hatch(ctx: &ctx, rect: rect)
                for (a, b) in s.revised {
                    let r = CGRect(x: x(a, w), y: laneTop, width: max(1, x(b, w) - x(a, w)), height: laneH - 4)
                    ctx.fill(Path(r), with: .color(Theme.accent.opacity(0.85)))
                }
            }
        } else {
            for r in model.revisions.items {
                let rect = CGRect(x: x(r.replaceStart, w), y: laneTop,
                                  width: max(1, x(r.replaceEnd, w) - x(r.replaceStart, w)), height: laneH - 4)
                ctx.fill(Path(rect), with: .color(Theme.accent.opacity(0.85)))
            }
        }

        // IDR resume points (splice points)
        if let m = model.master {
            let pts = m.resumePoints
            let step = max(1, pts.count / 600)
            for (i, p) in pts.enumerated() where i % step == 0 {
                let px = x(p, w)
                if px < 0 || px > w { continue }
                ctx.fill(Path(CGRect(x: px, y: size.height - 10, width: 1, height: 6)),
                         with: .color(Color.white.opacity(0.35)))
            }
        }

        // ruler
        ctx.fill(Path(CGRect(x: 0, y: 0, width: w, height: rulerH)), with: .color(Theme.surfaceRaised))
        let secondsVisible = span / model.rate.value
        let candidates: [Double] = [0.04, 0.2, 1, 2, 5, 10, 30, 60, 120, 300, 600]
        let tickSec = candidates.first { secondsVisible / $0 <= 10 } ?? 600
        let tickFrames = max(1, Int((tickSec * model.rate.value).rounded()))
        var f = Int(viewStart) / tickFrames * tickFrames
        while Double(f) <= viewStart + span {
            let px = x(f, w)
            if px >= 0 {
                ctx.fill(Path(CGRect(x: px, y: rulerH - 6, width: 1, height: 6)), with: .color(Theme.textTertiary))
                ctx.draw(Text(model.timecode(f)).font(Theme.monoSmall).foregroundColor(Theme.textTertiary),
                         at: CGPoint(x: px + 3, y: 8), anchor: .leading)
            }
            f += tickFrames
        }

        // playhead
        let ph = x(model.playhead, w)
        let frameW = max(1, w / CGFloat(span))
        if frameW > 3 {
            ctx.fill(Path(CGRect(x: ph, y: laneTop, width: frameW, height: laneH)), with: .color(Color.white.opacity(0.12)))
        }
        ctx.fill(Path(CGRect(x: ph - 0.75, y: 0, width: 1.5, height: size.height)), with: .color(.white))
        var head = Path()
        head.move(to: CGPoint(x: ph - 5, y: 0))
        head.addLine(to: CGPoint(x: ph + 5, y: 0))
        head.addLine(to: CGPoint(x: ph, y: 7))
        head.closeSubpath()
        ctx.fill(head, with: .color(.white))
    }

    func hatch(ctx: inout GraphicsContext, rect: CGRect) {
        var p = Path()
        var xx = rect.minX - rect.height
        while xx < rect.maxX {
            p.move(to: CGPoint(x: max(xx, rect.minX), y: rect.maxY - max(0, rect.minX - xx)))
            p.addLine(to: CGPoint(x: min(xx + rect.height, rect.maxX), y: rect.maxY - min(rect.height, rect.maxX - xx)))
            xx += 7
        }
        ctx.stroke(p, with: .color(Theme.boundary.opacity(0.55)), lineWidth: 1)
    }

    // MARK: controls

    var toolbar: some View {
        HStack(spacing: 8) {
            Text("TIMELINE").font(Theme.caption).tracking(0.8).foregroundStyle(Theme.textTertiary)
            Spacer()
            Group {
                Button { model.step(-Int(model.rate.value.rounded())) } label: { Image(systemName: "backward.end") }
                    .help("Back 1 second (⇧←)")
                Button { model.step(-1) } label: { Image(systemName: "chevron.left") }
                    .help("Previous frame (←)")
                Button { model.step(1) } label: { Image(systemName: "chevron.right") }
                    .help("Next frame (→)")
                Button { model.step(Int(model.rate.value.rounded())) } label: { Image(systemName: "forward.end") }
                    .help("Forward 1 second (⇧→)")
            }
            .buttonStyle(.plain)
            .foregroundStyle(Theme.textSecondary)
            Divider().frame(height: 14)
            Button { zoom = max(1, zoom / 2); clampView() } label: { Image(systemName: "minus.magnifyingglass") }
                .buttonStyle(.plain).foregroundStyle(Theme.textSecondary)
            Text(zoom <= 1 ? "Fit" : String(format: "%.0f×", zoom))
                .font(Theme.monoSmall).foregroundStyle(Theme.textTertiary).frame(width: 34)
            Button { zoom = min(4096, zoom * 2); keepVisibleCentered() } label: { Image(systemName: "plus.magnifyingglass") }
                .buttonStyle(.plain).foregroundStyle(Theme.textSecondary)
            Button { zoom = 1; viewStart = 0 } label: { Text("Fit").font(.system(size: 11)) }
                .buttonStyle(QuietButtonStyle())
        }
    }

    func clampView() { viewStart = max(0, min(viewStart, total - span)) }

    func keepVisibleCentered() {
        viewStart = max(0, min(total - span, Double(model.playhead) - span / 2))
    }

    var legend: some View {
        HStack(spacing: 14) {
            legendItem(Theme.preserved.opacity(3), "Preserved (packet copy)")
            legendItem(Theme.accent, "Revised")
            legendItem(Theme.boundary, "Re-encoded for GOP dependencies")
            legendItem(Color.white.opacity(0.35), "IDR splice points")
            Spacer()
        }
        .font(.system(size: 10))
        .foregroundStyle(Theme.textSecondary)
    }

    func legendItem(_ c: Color, _ t: String) -> some View {
        HStack(spacing: 5) {
            RoundedRectangle(cornerRadius: 2).fill(c).frame(width: 12, height: 8)
            Text(t)
        }
    }

    var keyboardShortcuts: some View {
        ZStack {
            Button("") { model.step(-1) }.keyboardShortcut(.leftArrow, modifiers: [])
            Button("") { model.step(1) }.keyboardShortcut(.rightArrow, modifiers: [])
            Button("") { model.step(-Int(model.rate.value.rounded())) }.keyboardShortcut(.leftArrow, modifiers: .shift)
            Button("") { model.step(Int(model.rate.value.rounded())) }.keyboardShortcut(.rightArrow, modifiers: .shift)
            Button("") { model.setPlayhead(0) }.keyboardShortcut(.home, modifiers: [])
            Button("") { model.setPlayhead(model.frameCount - 1) }.keyboardShortcut(.end, modifiers: [])
        }
        .opacity(0)
        .frame(width: 0, height: 0)
        .accessibilityHidden(true)
    }
}

struct PreviewInspector: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack {
                RoundedRectangle(cornerRadius: 8).fill(Color.black)
                if let img = model.preview {
                    Image(nsImage: img).resizable().aspectRatio(contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                } else {
                    Image(systemName: "film").font(.system(size: 26)).foregroundStyle(Theme.textTertiary)
                }
            }
            .aspectRatio(16.0 / 9.0, contentMode: .fit)
            HStack {
                TimecodeField(frame: Binding(get: { model.playhead }, set: { model.setPlayhead($0) }),
                              rate: model.rate, dropFrame: model.dropFrame)
                Spacer()
                Text("frame \(model.playhead)").font(Theme.monoSmall).foregroundStyle(Theme.textSecondary)
                if let t = frameType {
                    Pill(text: t, color: t == "IDR" ? Theme.success : Theme.textSecondary)
                }
            }
            if let c = classification {
                Text(c.0).font(.system(size: 11, weight: .medium)).foregroundStyle(c.1)
            }
        }
    }

    var frameType: String? {
        guard let m = model.master else { return nil }
        let types = m.frameTypes
        guard model.playhead < types.count else { return nil }
        switch types[model.playhead] {
        case "K": return "IDR"
        case "I": return "I"
        case "P": return "P"
        case "B": return "B"
        default: return nil
        }
    }

    var classification: (String, Color)? {
        guard let plan = model.plan, model.mode.isPatch else { return nil }
        let f = model.playhead
        for s in plan.segments where s.kind == "render" && f >= s.outStart && f < s.outEnd {
            if s.revised.contains(where: { f >= $0.0 && f < $0.1 }) {
                return ("Revised frame - rendered fresh and re-encoded", Theme.accent)
            }
            return ("Boundary frame - unchanged content, re-encoded (GOP dependency)", Theme.boundary)
        }
        return ("Preserved frame - compressed packet copied, verified pixel-identical", Theme.textSecondary)
    }
}
