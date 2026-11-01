import Foundation

/// Exact rational frame rate (e.g. 30000/1001).
public struct FrameRate: Equatable, Hashable, CustomStringConvertible {
    public let num: Int
    public let den: Int

    public init(_ num: Int, _ den: Int = 1) {
        let g = FrameRate.gcd(num, den)
        self.num = num / g
        self.den = den / g
    }

    /// Parses "30000/1001", "29.97", "25".
    public init?(string: String) {
        let s = string.trimmingCharacters(in: .whitespaces)
        if s.contains("/") {
            let p = s.split(separator: "/")
            guard p.count == 2, let n = Int(p[0]), let d = Int(p[1]), d > 0 else { return nil }
            self.init(n, d)
            return
        }
        guard let f = Double(s), f > 0 else { return nil }
        let known: [(Double, Int, Int)] = [
            (23.976, 24000, 1001), (29.97, 30000, 1001), (47.952, 48000, 1001),
            (59.94, 60000, 1001), (119.88, 120000, 1001),
        ]
        for (v, n, d) in known where abs(v - f) < 0.0015 {
            self.init(n, d)
            return
        }
        if abs(f - f.rounded()) < 1e-6 {
            self.init(Int(f.rounded()), 1)
            return
        }
        return nil
    }

    public var value: Double { Double(num) / Double(den) }
    public var nominal: Int { Int(value.rounded()) }
    public var isDropFrameCapable: Bool { den == 1001 && (nominal == 30 || nominal == 60) }
    public var description: String { "\(num)/\(den)" }
    public var displayName: String {
        den == 1 ? "\(num) fps" : String(format: "%.3f fps", value).replacingOccurrences(of: "0 fps", with: " fps")
    }

    static func gcd(_ a: Int, _ b: Int) -> Int {
        var (x, y) = (abs(a), abs(b))
        while y != 0 { (x, y) = (y, x % y) }
        return max(x, 1)
    }
}

public enum TimecodeError: Error, Equatable {
    case invalidFormat(String)
    case outOfRange(String)
    case droppedFrame(String)
}

/// SMPTE timecode conversion; mirrors srx/timecode.py exactly.
public enum Timecode {
    public static func frames(from tc: String, rate: FrameRate, dropFrame: Bool? = nil) throws -> Int {
        let s = tc.trimmingCharacters(in: .whitespaces)
        let neg = s.hasPrefix("-")
        let body = neg ? String(s.dropFirst()) : s
        let usesDropSeparator = body.contains(";") || body.contains(",")
        let parts = body.split(whereSeparator: { ":;.,".contains($0) }).map(String.init)
        guard parts.count == 4, let hh = Int(parts[0]), let mm = Int(parts[1]), let ss = Int(parts[2]),
              let ff = Int(parts[3]) else { throw TimecodeError.invalidFormat(tc) }
        let fps = rate.nominal
        guard mm <= 59, ss <= 59, ff < fps else { throw TimecodeError.outOfRange(tc) }
        let df = dropFrame ?? (usesDropSeparator && rate.isDropFrameCapable)
        var total = (hh * 3600 + mm * 60 + ss) * fps + ff
        if df {
            guard rate.isDropFrameCapable else { throw TimecodeError.invalidFormat(tc) }
            let drop = 2 * fps / 30
            if ss == 0 && ff < drop && mm % 10 != 0 { throw TimecodeError.droppedFrame(tc) }
            let minutes = 60 * hh + mm
            total -= drop * (minutes - minutes / 10)
        }
        return neg ? -total : total
    }

    public static func string(from frames: Int, rate: FrameRate, dropFrame: Bool = false) -> String {
        let fps = rate.nominal
        let neg = frames < 0
        var f = abs(frames)
        let df = dropFrame && rate.isDropFrameCapable
        if df {
            let drop = 2 * fps / 30
            let per10 = fps * 600 - drop * 9
            let perMin = fps * 60 - drop
            let d = f / per10
            let m = f % per10
            if m > drop {
                f += drop * 9 * d + drop * ((m - drop) / perMin)
            } else {
                f += drop * 9 * d
            }
        }
        let ff = f % fps
        let total = f / fps
        let sep = df ? ";" : ":"
        return (neg ? "-" : "") + String(format: "%02d:%02d:%02d", total / 3600, (total / 60) % 60, total % 60)
            + sep + String(format: "%02d", ff)
    }

    public static func seconds(frames: Int, rate: FrameRate) -> Double {
        Double(frames) * Double(rate.den) / Double(rate.num)
    }

    /// Human duration, e.g. "5.00 s (125 frames)".
    public static func durationText(frames: Int, rate: FrameRate) -> String {
        String(format: "%.2f s (%d fr)", seconds(frames: frames, rate: rate), frames)
    }
}
