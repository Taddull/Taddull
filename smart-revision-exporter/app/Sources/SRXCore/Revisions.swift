import Foundation

/// One revision range in MASTER frame indices (display order), end exclusive.
public struct RevisionRange: Identifiable, Equatable, Codable {
    public var id: UUID
    public var start: Int
    public var end: Int
    public var video: Bool
    public var audio: Bool
    public var label: String
    public var handlesBefore: Int
    public var handlesAfter: Int
    /// Frames added (+) or removed (-) by this revision on the timeline.
    public var delta: Int
    public var source: String

    public init(id: UUID = UUID(), start: Int, end: Int, video: Bool = true, audio: Bool = true,
                label: String = "", handlesBefore: Int = 0, handlesAfter: Int = 0, delta: Int = 0,
                source: String = "manual") {
        self.id = id
        self.start = start
        self.end = end
        self.video = video
        self.audio = audio
        self.label = label
        self.handlesBefore = handlesBefore
        self.handlesAfter = handlesAfter
        self.delta = delta
        self.source = source
    }

    public var length: Int { end - start }
    public var replaceStart: Int { start - handlesBefore }
    public var replaceEnd: Int { end + handlesAfter }

    /// Engine request representation (srx Revision dataclass field names).
    public var engineJSON: [String: JSONValue] {
        [
            "start": .number(Double(start)), "end": .number(Double(end)),
            "video": .bool(video), "audio": .bool(audio), "label": .string(label),
            "handles_before": .number(Double(handlesBefore)), "handles_after": .number(Double(handlesAfter)),
            "delta": .number(Double(delta)),
        ]
    }
}

public enum RevisionIssue: Equatable {
    case empty(UUID)
    case outOfBounds(UUID)
    case overlaps(UUID, UUID)
    case adjacent(UUID, UUID)
    case nothingSelected(UUID)
}

public struct RevisionSet: Equatable {
    public private(set) var items: [RevisionRange] = []

    public init(_ items: [RevisionRange] = []) {
        self.items = items
        sort()
    }

    public mutating func add(_ r: RevisionRange) {
        items.append(r)
        sort()
    }

    public mutating func remove(id: UUID) {
        items.removeAll { $0.id == id }
    }

    public mutating func update(_ r: RevisionRange) {
        if let i = items.firstIndex(where: { $0.id == r.id }) { items[i] = r }
        sort()
    }

    public mutating func sort() {
        items.sort { ($0.start, $0.end) < ($1.start, $1.end) }
    }

    public var totalFrames: Int { items.reduce(0) { $0 + max(0, $1.length) } }

    /// Validation against a master of `frameCount` frames.
    public func issues(frameCount: Int) -> [RevisionIssue] {
        var out: [RevisionIssue] = []
        for r in items {
            if r.end <= r.start { out.append(.empty(r.id)) }
            if r.replaceStart < 0 || r.replaceEnd > frameCount { out.append(.outOfBounds(r.id)) }
            if !r.video && !r.audio { out.append(.nothingSelected(r.id)) }
        }
        for (a, b) in zip(items, items.dropFirst()) {
            if b.replaceStart < a.replaceEnd {
                out.append(.overlaps(a.id, b.id))
            } else if b.replaceStart == a.replaceEnd {
                out.append(.adjacent(a.id, b.id))
            }
        }
        return out
    }

    public var hasOverlaps: Bool {
        issues(frameCount: Int.max).contains { if case .overlaps = $0 { return true }; if case .adjacent = $0 { return true }; return false }
    }

    /// Merge overlapping or touching ranges (the engine also merges, this keeps the list tidy).
    public mutating func mergeOverlapping() {
        sort()
        var out: [RevisionRange] = []
        for r in items {
            if var last = out.last, r.replaceStart <= last.replaceEnd {
                last.end = max(last.end, r.end)
                last.start = min(last.start, r.start)
                last.handlesAfter = max(0, max(last.replaceEnd, r.replaceEnd) - last.end)
                last.handlesBefore = max(0, last.start - min(last.replaceStart, r.replaceStart))
                last.video = last.video || r.video
                last.audio = last.audio || r.audio
                last.delta += r.delta
                let labels = [last.label, r.label].filter { !$0.isEmpty }
                last.label = labels.joined(separator: " + ")
                out[out.count - 1] = last
            } else {
                out.append(r)
            }
        }
        items = out
    }
}
