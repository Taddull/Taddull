import AppKit
import Foundation
import SRXCore
import SwiftUI
import UniformTypeIdentifiers

/// Central state: Resolve connection, master, revisions, plan, export job.
@MainActor
final class AppModel: ObservableObject {
    // engine
    @Published var engineError: String?
    @AppStorage("pythonPath") var pythonPath: String = ""
    private var client: EngineClient?

    // Resolve
    @Published var resolve: ResolveInfo?
    @Published var resolveBusy = false
    @Published var useResolve = true

    // master
    @Published var master: MasterInfo?
    @Published var masterLoading = false
    @Published var filmstrip: NSImage?
    /// Absolute timeline frame of master frame 0 (timeline start, unless overridden).
    @Published var timelineStartFrame: Int = 0
    @Published var dropFrame = false

    // revisions + plan
    @Published var revisions = RevisionSet()
    @Published var plan: PlanSummary?
    @Published var planError: String?
    private var planTask: Task<Void, Never>?

    // timeline navigation
    @Published var playhead: Int = 0
    @Published var preview: NSImage?
    private var previewTask: Task<Void, Never>?

    // export settings
    @Published var mode: ExportMode = .verifiedPatch
    @Published var strict = false
    @Published var audio: AudioStrategy = .auto
    @Published var quality: PatchQuality = .high
    @Published var encoderPreset = "slow"
    @Published var outputPath: String = ""
    @Published var rrGopSeconds: Double = 1.0
    @Published var rrAllIntra = false
    @Published var resolvePreset: String = ""
    @Published var manualRenders: [ManualRenderFile] = []

    // export job
    @Published var running = false
    @Published var currentStage: ExportStage?
    @Published var completedStages: Set<ExportStage> = []
    @Published var stageFraction: Double = 0
    @Published var stageMessage = ""
    @Published var eta: Double?
    @Published var stats: JSONValue?
    @Published var log: [EngineEvent] = []
    @Published var warnings: [String] = []
    @Published var report: VerificationReport?
    @Published var reportPath: String?
    @Published var resultOutput: String?
    @Published var exportError: String?
    @Published var approved = false
    private var task: EngineTask?

    // diagnostics
    @Published var doctor: JSONValue?
    @Published var showDiagnostics = false

    var rate: FrameRate { master?.rate ?? resolve?.rate ?? FrameRate(25) }
    var frameCount: Int { master?.frameCount ?? 0 }

    // MARK: - engine

    func engine() throws -> EngineClient {
        if let c = client { return c }
        let c = try EngineClient.make(userPython: pythonPath.isEmpty ? nil : pythonPath)
        client = c
        return c
    }

    func resetEngine() { client = nil }

    func bootstrap() {
        Task {
            await refreshResolve()
            await runDoctor(silent: true)
            await recoverJobs()
        }
    }

    func runDoctor(silent: Bool = false) async {
        do {
            doctor = try await engine().result(["doctor", "--no-resolve"])
            engineError = nil
        } catch {
            engineError = error.localizedDescription
            if !silent { showDiagnostics = true }
        }
    }

    func recoverJobs() async {
        _ = try? await engine().result(["jobs", "recover"])
    }

    // MARK: - Resolve

    func refreshResolve() async {
        resolveBusy = true
        defer { resolveBusy = false }
        do {
            let r = try await engine().result(["resolve", "status", "--timeout", "2"])
            let info = ResolveInfo(status: r["resolve"] ?? .null)
            resolve = info
            if info.connected {
                timelineStartFrame = info.startFrame
                dropFrame = info.dropFrame
                if resolvePreset.isEmpty { resolvePreset = info.renderPresets.first ?? "" }
            }
        } catch {
            resolve = ResolveInfo(status: .object(["connected": .bool(false),
                                                   "error": .string(error.localizedDescription)]))
        }
    }

    func importResolveRanges(markersOnly: Bool) async {
        do {
            let r = try await engine().result(["resolve", "ranges"])
            for item in r["ranges"]?.array ?? [] {
                let src = item["source"]?.string ?? ""
                if markersOnly != (src == "marker") { continue }
                guard let s = item["master_start"]?.int, let e = item["master_end"]?.int else { continue }
                revisions.add(RevisionRange(start: s, end: e, label: item["label"]?.string ?? src, source: src))
            }
            let edges = r["nearby_edit_points"]?.array ?? []
            if !edges.isEmpty {
                warnings.append("\(edges.count) clip edit point(s) lie within 12 frames of a revision edge. "
                                + "If a transition crosses the edge, add handles so the whole transition is replaced.")
            }
            schedulePlan()
        } catch {
            exportError = error.localizedDescription
        }
    }

    // MARK: - master

    func chooseMaster() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.mpeg4Movie, .quickTimeMovie]
        panel.allowsMultipleSelection = false
        panel.message = "Select the previously exported master (H.264 MP4)"
        if panel.runModal() == .OK, let url = panel.url {
            Task { await loadMaster(path: url.path) }
        }
    }

    func loadMaster(path: String) async {
        masterLoading = true
        defer { masterLoading = false }
        do {
            let r = try await engine().result(["probe", path, "--gop-map"])
            guard let p = r["probe"] else { return }
            let m = MasterInfo(probe: p)
            master = m
            playhead = min(playhead, max(0, m.frameCount - 1))
            report = nil
            revisions = RevisionSet()
            plan = nil
            outputPath = ExportRequest.suggestOutput(for: path)
            if let rr = resolve, rr.connected, let tr = rr.rate, tr != m.rate {
                warnings.append("Timeline frame rate \(tr.displayName) differs from master \(m.rate.displayName). "
                                + "This master may not belong to the active timeline.")
            }
            loadFilmstrip(path: path)
            requestPreview()
        } catch {
            exportError = error.localizedDescription
        }
    }

    private func loadFilmstrip(path: String) {
        let out = EngineLocator.supportDirectory.appendingPathComponent("cache/filmstrip-\(UUID().uuidString).png").path
        try? FileManager.default.createDirectory(atPath: (out as NSString).deletingLastPathComponent,
                                                 withIntermediateDirectories: true)
        Task {
            if (try? await engine().result(["filmstrip", path, "-o", out, "--tiles", "60", "--height", "56"])) != nil {
                filmstrip = NSImage(contentsOfFile: out)
            }
        }
    }

    // MARK: - navigation

    func setPlayhead(_ f: Int) {
        let n = max(0, frameCount - 1)
        playhead = min(max(0, f), n)
        requestPreview()
    }

    func step(_ frames: Int) { setPlayhead(playhead + frames) }

    func requestPreview() {
        guard let m = master else { return }
        previewTask?.cancel()
        let frame = playhead
        previewTask = Task {
            try? await Task.sleep(nanoseconds: 120_000_000)
            if Task.isCancelled { return }
            let out = EngineLocator.supportDirectory.appendingPathComponent("cache/preview.png").path
            try? FileManager.default.removeItem(atPath: out)
            if (try? await engine().result(["frame", m.path, "--index", "\(frame)", "-o", out, "--height", "360"])) != nil,
               !Task.isCancelled {
                preview = NSImage(contentsOfFile: out)
            }
        }
    }

    func timecode(_ masterFrame: Int) -> String {
        Timecode.string(from: timelineStartFrame + masterFrame, rate: rate, dropFrame: dropFrame)
    }

    func masterFrame(fromTimecode tc: String) -> Int? {
        guard let abs = try? Timecode.frames(from: tc, rate: rate, dropFrame: dropFrame) else { return nil }
        return abs - timelineStartFrame
    }

    // MARK: - revisions

    func addRevisionAtPlayhead() {
        let len = Int(rate.value.rounded()) * 5
        let s = min(playhead, max(0, frameCount - len))
        revisions.add(RevisionRange(start: s, end: min(frameCount, s + len), label: "Revision \(revisions.items.count + 1)"))
        schedulePlan()
    }

    func update(_ r: RevisionRange) {
        revisions.update(r)
        schedulePlan()
    }

    func remove(_ id: UUID) {
        revisions.remove(id: id)
        schedulePlan()
    }

    func mergeRevisions() {
        revisions.mergeOverlapping()
        schedulePlan()
    }

    // MARK: - plan

    func schedulePlan() {
        planTask?.cancel()
        guard let m = master, !revisions.items.isEmpty, mode.isPatch else {
            plan = nil
            planError = nil
            return
        }
        let req = makeRequest(master: m)
        planTask = Task {
            try? await Task.sleep(nanoseconds: 350_000_000)
            if Task.isCancelled { return }
            do {
                let path = try EngineClient.writeRequest(req.json)
                let r = try await engine().result(["plan", "--request", path])
                if Task.isCancelled { return }
                plan = r["plan"].map { PlanSummary(plan: $0) }
                planError = nil
            } catch {
                plan = nil
                planError = error.localizedDescription
            }
        }
    }

    // MARK: - export

    func makeRequest(master m: MasterInfo?) -> ExportRequest {
        ExportRequest(master: m?.path ?? "", output: outputPath, mode: mode, strict: strict, audio: audio,
                      quality: quality, preset: encoderPreset, revisions: revisions.items,
                      timelineOffset: timelineStartFrame, useResolve: useResolve && (resolve?.connected ?? false),
                      manualRenders: manualRenders, rate: rate,
                      gopSeconds: mode == .revisionReadyMaster && !rrAllIntra ? rrGopSeconds : nil,
                      allIntra: mode == .revisionReadyMaster && rrAllIntra,
                      resolvePreset: mode == .safeFullExport ? resolvePreset : nil,
                      timelineFrames: resolve?.connected == true ? nil : master?.frameCount)
    }

    var canExport: Bool {
        if running || outputPath.isEmpty { return false }
        let sourceOK = (useResolve && resolve?.connected == true) || !manualRenders.isEmpty
        switch mode {
        case .fastPatch, .verifiedPatch:
            return master?.patchable == true && !revisions.items.isEmpty && sourceOK
        case .revisionReadyMaster, .safeFullExport:
            return sourceOK
        }
    }

    func chooseOutput() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.mpeg4Movie]
        panel.nameFieldStringValue = outputPath.isEmpty ? "revision.mp4" : (outputPath as NSString).lastPathComponent
        if !outputPath.isEmpty {
            panel.directoryURL = URL(fileURLWithPath: (outputPath as NSString).deletingLastPathComponent)
        }
        panel.message = "Existing files are never overwritten; choose a new name."
        if panel.runModal() == .OK, let url = panel.url {
            if FileManager.default.fileExists(atPath: url.path) {
                exportError = "\(url.lastPathComponent) already exists. Smart Revision Exporter never overwrites files."
            } else {
                outputPath = url.path
            }
        }
    }

    func addManualRender() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.quickTimeMovie, .mpeg4Movie]
        panel.message = "Select a render exported from Resolve (ProRes 422 HQ + Linear PCM recommended)"
        if panel.runModal() == .OK, let url = panel.url {
            manualRenders.append(ManualRenderFile(path: url.path, timelineStartFrame: timelineStartFrame))
        }
    }

    func startExport() {
        guard canExport else { return }
        if FileManager.default.fileExists(atPath: outputPath) {
            exportError = "Output already exists; choose a new file name."
            return
        }
        let req = makeRequest(master: master)
        resetJobState()
        running = true
        do {
            let path = try EngineClient.writeRequest(req.json)
            let (t, output) = try engine().stream([req.command, "--request", path, "--json"])
            task = t
            Task {
                for await o in output {
                    switch o {
                    case .event(let ev):
                        handle(ev)
                    case .stderr(let line):
                        log.append(EngineEvent(type: "stderr", body: .object(["message": .string(line)])))
                    case .exit(let code):
                        finished(code: code)
                    }
                }
            }
        } catch {
            running = false
            exportError = error.localizedDescription
        }
    }

    func cancelExport() {
        task?.cancel()
        stageMessage = "Cancelling - stopping Resolve/FFmpeg and removing partial output…"
    }

    private func resetJobState() {
        currentStage = nil
        completedStages = []
        stageFraction = 0
        stageMessage = ""
        eta = nil
        log = []
        warnings = []
        report = nil
        reportPath = nil
        resultOutput = nil
        exportError = nil
        approved = false
    }

    private func handle(_ ev: EngineEvent) {
        if ev.type != "progress" && ev.type != "stats" {
            log.append(ev)
            if log.count > 2000 { log.removeFirst(log.count - 2000) }
        }
        switch ev.type {
        case "stage":
            if let cur = currentStage { completedStages.insert(cur) }
            currentStage = ExportStage(rawValue: ev.stage)
            stageFraction = 0
            eta = nil
            stageMessage = ev.message
        case "progress":
            if let s = ExportStage(rawValue: ev.stage), s != currentStage {
                if let cur = currentStage { completedStages.insert(cur) }
                currentStage = s
            }
            stageFraction = ev.fraction ?? stageFraction
            eta = ev.eta
            if !ev.message.isEmpty { stageMessage = ev.message }
        case "stats":
            stats = ev.body
        case "warning":
            warnings.append(ev.message)
        case "plan":
            if let p = ev.body["plan"] { plan = PlanSummary(plan: p) }
        case "error":
            exportError = ev.message
            if let rp = ev.body["report"]?.string { loadReport(path: rp) }
        case "result":
            resultOutput = ev.body["output"]?.string
            if let rp = ev.body["report"]?.string { loadReport(path: rp) }
        default:
            break
        }
    }

    private func loadReport(path: String) {
        reportPath = path
        if let d = FileManager.default.contents(atPath: path), let v = JSONValue.parse(d) {
            report = VerificationReport(raw: v)
        }
    }

    private func finished(code: Int32) {
        running = false
        task = nil
        if code == 0 {
            if let cur = currentStage { completedStages.insert(cur) }
            currentStage = nil
        } else if code == 130 {
            exportError = "Export cancelled. The master was not modified and no output was written."
        } else if exportError == nil {
            exportError = "Export failed (exit code \(code)). See the log for details."
        }
    }

    // MARK: - after export

    func revealOutput() {
        guard let p = resultOutput else { return }
        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: p)])
    }

    func openReport() {
        guard let p = reportPath else { return }
        let md = (p as NSString).deletingPathExtension + ".md"
        NSWorkspace.shared.open(URL(fileURLWithPath: FileManager.default.fileExists(atPath: md) ? md : p))
    }

    /// Mark the verified output as the approved base for the next revision cycle and load it.
    func approveOutput() async {
        guard let p = resultOutput else { return }
        do {
            _ = try await engine().result(["project", "approve", p])
            approved = true
            await loadMaster(path: p)
        } catch {
            exportError = error.localizedDescription
        }
    }

    func openLogsFolder() {
        let url = EngineLocator.supportDirectory.appendingPathComponent("jobs")
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        NSWorkspace.shared.open(url)
    }

    /// Optional: create a private venv with numpy for faster verification maths.
    func installNumpy() async {
        guard let py = EngineLocator.findPython(userPath: pythonPath.isEmpty ? nil : pythonPath) else { return }
        let venv = EngineLocator.supportDirectory.appendingPathComponent("venv").path
        let script = "\"\(py)\" -m venv \"\(venv)\" && \"\(venv)/bin/python3\" -m pip install --upgrade numpy"
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/sh")
        p.arguments = ["-c", script]
        do {
            try p.run()
            await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in
                DispatchQueue.global().async {
                    p.waitUntilExit()
                    c.resume()
                }
            }
            resetEngine()
            await runDoctor()
        } catch {
            engineError = error.localizedDescription
        }
    }
}
