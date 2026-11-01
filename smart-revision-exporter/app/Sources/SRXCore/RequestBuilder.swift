import Foundation

public enum ExportMode: String, CaseIterable, Identifiable {
    case fastPatch = "fast"
    case verifiedPatch = "verified"
    case revisionReadyMaster = "revision-ready"
    case safeFullExport = "full-export"

    public var id: String { rawValue }

    public var title: String {
        switch self {
        case .fastPatch: return "Fast Patch"
        case .verifiedPatch: return "Verified Patch"
        case .revisionReadyMaster: return "Revision-Ready Master"
        case .safeFullExport: return "Safe Full Export"
        }
    }

    public var summary: String {
        switch self {
        case .fastPatch:
            return "Renders only the revised GOPs. Verifies structure and the frames around every splice; "
                + "other unchanged frames are byte-identical packet copies but are not decoded."
        case .verifiedPatch:
            return "Renders only the revised GOPs, then decodes the whole result and proves every unchanged "
                + "frame is pixel-identical (SHA-256). Recommended."
        case .revisionReadyMaster:
            return "One full render, encoded with short closed GOPs (or all-intra) so future revisions "
                + "re-encode fewer unchanged frames. Delivery stays H.264 MP4."
        case .safeFullExport:
            return "Full render of the timeline with structural verification against the current master. "
                + "Use when a patch cannot meet the quality requirements."
        }
    }

    public var isPatch: Bool { self == .fastPatch || self == .verifiedPatch }
}

public enum AudioStrategy: String, CaseIterable, Identifiable {
    case auto, copy, splice, full
    public var id: String { rawValue }
    public var title: String {
        switch self {
        case .auto: return "Automatic"
        case .copy: return "Keep original audio"
        case .splice: return "Splice revised region"
        case .full: return "Re-encode full track"
        }
    }
}

public enum PatchQuality: String, CaseIterable, Identifiable {
    case transparent, high, balanced, match
    public var id: String { rawValue }
    public var title: String {
        switch self {
        case .transparent: return "Transparent (CRF 12)"
        case .high: return "High (CRF 16)"
        case .balanced: return "Balanced (CRF 19)"
        case .match: return "Match master bitrate"
        }
    }
}

public struct ManualRenderFile: Identifiable, Equatable {
    public let id = UUID()
    public var path: String
    public var timelineStartFrame: Int
    public init(path: String, timelineStartFrame: Int) {
        self.path = path
        self.timelineStartFrame = timelineStartFrame
    }
}

public struct ExportRequest {
    public var master: String
    public var output: String
    public var mode: ExportMode
    public var strict: Bool
    public var audio: AudioStrategy
    public var quality: PatchQuality
    public var preset: String
    public var revisions: [RevisionRange]
    public var timelineOffset: Int
    public var useResolve: Bool
    public var manualRenders: [ManualRenderFile]
    public var rate: FrameRate
    public var gopSeconds: Double?
    public var allIntra: Bool
    public var resolvePreset: String?
    public var timelineFrames: Int?

    public init(master: String, output: String, mode: ExportMode, strict: Bool, audio: AudioStrategy,
                quality: PatchQuality, preset: String, revisions: [RevisionRange], timelineOffset: Int,
                useResolve: Bool, manualRenders: [ManualRenderFile], rate: FrameRate, gopSeconds: Double? = nil,
                allIntra: Bool = false, resolvePreset: String? = nil, timelineFrames: Int? = nil) {
        self.master = master
        self.output = output
        self.mode = mode
        self.strict = strict
        self.audio = audio
        self.quality = quality
        self.preset = preset
        self.revisions = revisions
        self.timelineOffset = timelineOffset
        self.useResolve = useResolve
        self.manualRenders = manualRenders
        self.rate = rate
        self.gopSeconds = gopSeconds
        self.allIntra = allIntra
        self.resolvePreset = resolvePreset
        self.timelineFrames = timelineFrames
    }

    var sourceJSON: JSONValue {
        if useResolve { return .object(["type": .string("resolve")]) }
        return .object([
            "type": .string("files"),
            "fps": .string(rate.description),
            "timeline_offset": .number(Double(timelineOffset)),
            "frames": timelineFrames.map { JSONValue.number(Double($0)) } ?? JSONValue.null,
            "renders": .array(manualRenders.map { (r: ManualRenderFile) -> JSONValue in
                JSONValue.object(["path": .string(r.path),
                                  "timeline_start": .number(Double(r.timelineStartFrame))])
            }),
        ])
    }

    /// JSON request understood by `srx export|prepare-master|full-export --request`.
    public var json: [String: JSONValue] {
        var r: [String: JSONValue] = [
            "output": .string(output),
            "mode": .string(mode == .fastPatch ? "fast" : "verified"),
            "strict": .bool(strict),
            "audio": .string(audio.rawValue),
            "quality": .string(quality.rawValue),
            "preset": .string(preset),
            "revision_units": .string("master"),
            "revisions": .array(revisions.map { (r: RevisionRange) -> JSONValue in JSONValue.object(r.engineJSON) }),
            "timeline_offset": .number(Double(timelineOffset)),
            "source": sourceJSON,
        ]
        if !master.isEmpty {
            r["master"] = .string(master)
            r["reference"] = .string(master)
        }
        if let g = gopSeconds { r["gop_seconds"] = .number(g) }
        if allIntra { r["all_intra"] = .bool(true) }
        if let p = resolvePreset, !p.isEmpty { r["resolve_preset"] = .string(p) }
        if let f = timelineFrames { r["frames"] = .number(Double(f)) }
        return r
    }

    /// Engine sub-command for this mode.
    public var command: String {
        switch mode {
        case .fastPatch, .verifiedPatch: return "export"
        case .revisionReadyMaster: return "prepare-master"
        case .safeFullExport: return "full-export"
        }
    }

    /// Suggest a non-existing output name next to the master: name_rev2.mp4, name_rev3.mp4 ...
    public static func suggestOutput(for master: String, suffix: String = "rev") -> String {
        let url = URL(fileURLWithPath: master)
        let dir = url.deletingLastPathComponent()
        var stem = url.deletingPathExtension().lastPathComponent
        if let r = stem.range(of: "_\(suffix)", options: .backwards),
           Int(stem[r.upperBound...]) != nil {
            stem = String(stem[..<r.lowerBound])
        }
        let ext = url.pathExtension.isEmpty ? "mp4" : url.pathExtension
        var n = 2
        while true {
            let cand = dir.appendingPathComponent("\(stem)_\(suffix)\(n).\(ext)").path
            if !FileManager.default.fileExists(atPath: cand) { return cand }
            n += 1
        }
    }
}
