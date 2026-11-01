import Foundation

/// One JSON-lines event from the engine (`python3 -m srx ... --json`).
public struct EngineEvent: Identifiable {
    public let id = UUID()
    public let type: String
    public let body: JSONValue
    public let receivedAt = Date()

    public init?(line: String) {
        guard line.hasPrefix("{"), let v = JSONValue.parse(line), let t = v["type"]?.string else { return nil }
        type = t
        body = v
    }

    public init(type: String, body: JSONValue) {
        self.type = type
        self.body = body
    }

    public var message: String { body["message"]?.string ?? "" }
    public var stage: String { body["stage"]?.string ?? "" }
    public var fraction: Double? { body["fraction"]?.double }
    public var eta: Double? { body["eta_s"]?.double }
}

/// Stages reported by the engine in order.
public enum ExportStage: String, CaseIterable, Identifiable {
    case analyze, fingerprint, plan, render, encode, audio, assemble, verify, finalize

    public var id: String { rawValue }

    public var title: String {
        switch self {
        case .analyze: return "Analyse master"
        case .fingerprint: return "Fingerprint master"
        case .plan: return "Plan patch"
        case .render: return "Render in Resolve"
        case .encode: return "Encode revised segments"
        case .audio: return "Process audio"
        case .assemble: return "Assemble (stream copy)"
        case .verify: return "Verify"
        case .finalize: return "Finalise"
        }
    }
}

/// Summary of a master file from `srx probe --gop-map`.
public struct MasterInfo {
    public let raw: JSONValue

    public init(probe: JSONValue) { raw = probe }

    public var path: String { raw["path"]?.string ?? "" }
    public var fileName: String { (path as NSString).lastPathComponent }
    public var width: Int { raw.path("video.width")?.int ?? 0 }
    public var height: Int { raw.path("video.height")?.int ?? 0 }
    public var frameCount: Int { raw.path("video.frame_count")?.int ?? 0 }
    public var rate: FrameRate { FrameRate(string: raw.path("video.fps")?.string ?? "25/1") ?? FrameRate(25) }
    public var durationSeconds: Double { raw.path("video.duration_s")?.double ?? 0 }
    public var codecLine: String {
        let p = raw.path("video.sps.profile")?.string ?? "?"
        let l = raw.path("video.sps.level")?.string ?? "?"
        let pf = raw.path("video.pix_fmt")?.string ?? ""
        return "H.264 \(p) @ L\(l) · \(pf)"
    }
    public var gopLine: String {
        let avg = raw.path("video.gop_avg")?.double ?? 0
        let b = raw.path("video.b_frames")?.bool == true ? "B-frames" : "no B-frames"
        let idr = raw.path("video.idr_count")?.int ?? 0
        return "\(idr) IDR · avg GOP \(Int(avg.rounded())) fr · \(b)"
    }
    public var colorLine: String {
        let c = raw["color"]
        let parts = ["color_primaries", "color_transfer", "color_space", "color_range"].compactMap { c?[$0]?.string }
        return parts.isEmpty ? "untagged" : parts.joined(separator: " / ")
    }
    public var audioLine: String {
        guard let a = raw["audio"]?.array, !a.isEmpty else { return "No audio" }
        return a.map { t -> String in
            let codec = (t["codec"]?.string ?? "?").uppercased()
            let sr = t["sample_rate"]?.int ?? 0
            let ch = t["channels"]?.int ?? 0
            let br = (t["avg_bitrate"]?.int ?? 0) / 1000
            return "\(codec) \(sr / 1000) kHz \(ch == 2 ? "stereo" : "\(ch) ch") \(br) kb/s"
        }.joined(separator: "; ")
    }
    public var patchable: Bool { raw.path("video.patchable")?.bool ?? false }
    public var blockingIssues: [String] { raw.path("video.blocking_issues")?.array?.compactMap { $0.string } ?? [] }
    public var warnings: [String] { raw.path("video.warnings")?.array?.compactMap { $0.string } ?? [] }
    public var resumePoints: [Int] { raw.path("gop_map.resume_points")?.array?.compactMap { $0.int } ?? [] }
    /// One character per frame in display order: K (IDR), I, P, B.
    public var frameTypes: [Character] { Array(raw["frame_types"]?.string ?? "") }
}

/// Connected Resolve timeline (`srx resolve status`).
public struct ResolveInfo {
    public let raw: JSONValue

    public init(status: JSONValue) { raw = status }

    public var connected: Bool { raw["connected"]?.bool ?? false }
    public var error: String? { raw["error"]?.string }
    public var version: String { raw["version"]?.string ?? "" }
    public var project: String { raw.path("timeline.project")?.string ?? "—" }
    public var timeline: String { raw.path("timeline.timeline")?.string ?? "—" }
    public var rate: FrameRate? { FrameRate(string: raw.path("timeline.fps")?.string ?? "") }
    public var startFrame: Int { raw.path("timeline.start_frame")?.int ?? 0 }
    public var endFrame: Int { raw.path("timeline.end_frame")?.int ?? 0 }
    public var startTimecode: String { raw.path("timeline.start_timecode")?.string ?? "" }
    public var dropFrame: Bool { raw.path("timeline.drop_frame")?.bool ?? false }
    public var width: Int { raw.path("timeline.width")?.int ?? 0 }
    public var height: Int { raw.path("timeline.height")?.int ?? 0 }
    public var renderPresets: [String] { raw["render_presets"]?.array?.compactMap { $0.string } ?? [] }
    public var apiReport: [(String, Bool)] {
        (raw["api"]?.object ?? [:]).map { ($0.key, $0.value.bool ?? false) }.sorted { $0.0 < $1.0 }
    }
}

/// A planned segment (copy or render) in output frame coordinates.
public struct PlanSegment: Identifiable {
    public let id = UUID()
    public let kind: String
    public let outStart: Int
    public let outEnd: Int
    public let renderStart: Int
    public let renderEnd: Int
    public let revised: [(Int, Int)]
    public let boundaryFrames: Int
}

public struct PlanSummary {
    public let raw: JSONValue

    public init(plan: JSONValue) { raw = plan }

    public var segments: [PlanSegment] {
        let offset = raw["timeline_offset"]?.int ?? 0
        return (raw["segments"]?.array ?? []).map { s in
            PlanSegment(kind: s["kind"]?.string ?? "copy",
                        outStart: s["out_start"]?.int ?? 0, outEnd: s["out_end"]?.int ?? 0,
                        renderStart: (s["render_start"]?.int ?? offset) - offset,
                        renderEnd: (s["render_end"]?.int ?? offset) - offset,
                        revised: (s["revised"]?.array ?? []).compactMap { r in
                            guard let a = r[0]?.int, let b = r[1]?.int else { return nil }
                            return (a, b)
                        },
                        boundaryFrames: s["boundary_frames"]?.int ?? 0)
        }
    }
    public func stat(_ key: String) -> Double { raw.path("stats.\(key)")?.double ?? 0 }
    public var warnings: [String] { raw["warnings"]?.array?.compactMap { $0.string } ?? [] }
    public var audioStrategies: [String] { raw["audio"]?.array?.compactMap { $0["strategy"]?.string } ?? [] }
}

/// Verification report (report.json written by the engine).
public struct VerificationReport {
    public let raw: JSONValue

    public init(raw: JSONValue) { self.raw = raw }

    public var passed: Bool { raw["status"]?.string == "passed" }
    public var level: String { raw["level"]?.string ?? "" }
    public struct Check: Identifiable {
        public let id = UUID()
        public let name: String
        public let status: String
        public let detail: String
    }
    public var checks: [Check] {
        (raw["checks"]?.array ?? []).map {
            Check(name: $0["name"]?.string ?? "", status: $0["status"]?.string ?? "", detail: $0["detail"]?.string ?? "")
        }
    }
    public func video(_ key: String) -> JSONValue? { raw["video"]?[key] }
    public var failures: [String] { raw["failures"]?.array?.compactMap { $0.string } ?? [] }
    public var warnings: [String] { raw["warnings"]?.array?.compactMap { $0.string } ?? [] }
    public var audio: [JSONValue] { raw["audio"]?.array ?? [] }
    public var timings: [(String, Double)] {
        (raw["timings_s"]?.object ?? [:]).compactMap { k, v in v.double.map { (k, $0) } }.sorted { $0.0 < $1.0 }
    }
    public var outputPath: String? { raw.path("output.path")?.string }
    public var outputSHA: String? { raw.path("output.sha256")?.string }
    public var x264Params: String? { raw.path("encoding.x264_params")?.string }
}
