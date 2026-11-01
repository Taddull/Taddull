import Foundation

/// Loosely typed JSON value used for engine events and reports.
///
/// The engine's payloads evolve independently of the UI, so the app reads them
/// through tolerant accessors instead of strict Codable structs: a missing or
/// renamed field degrades to `nil` instead of failing the whole decode.
public enum JSONValue: Codable, Equatable, CustomStringConvertible {
    case null
    case bool(Bool)
    case number(Double)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])

    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() {
            self = .null
        } else if let b = try? c.decode(Bool.self) {
            self = .bool(b)
        } else if let n = try? c.decode(Double.self) {
            self = .number(n)
        } else if let s = try? c.decode(String.self) {
            self = .string(s)
        } else if let a = try? c.decode([JSONValue].self) {
            self = .array(a)
        } else if let o = try? c.decode([String: JSONValue].self) {
            self = .object(o)
        } else {
            throw DecodingError.dataCorruptedError(in: c, debugDescription: "Unsupported JSON value")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .null: try c.encodeNil()
        case .bool(let b): try c.encode(b)
        case .number(let n): try c.encode(n)
        case .string(let s): try c.encode(s)
        case .array(let a): try c.encode(a)
        case .object(let o): try c.encode(o)
        }
    }

    public static func parse(_ data: Data) -> JSONValue? {
        try? JSONDecoder().decode(JSONValue.self, from: data)
    }

    public static func parse(_ line: String) -> JSONValue? {
        guard let d = line.data(using: .utf8) else { return nil }
        return parse(d)
    }

    public subscript(key: String) -> JSONValue? {
        if case .object(let o) = self { return o[key] }
        return nil
    }

    public subscript(index: Int) -> JSONValue? {
        if case .array(let a) = self, index >= 0, index < a.count { return a[index] }
        return nil
    }

    /// Follow a dotted path such as "video.sps.profile".
    public func path(_ dotted: String) -> JSONValue? {
        var cur: JSONValue? = self
        for part in dotted.split(separator: ".") {
            cur = cur?[String(part)]
        }
        return cur
    }

    public var string: String? {
        switch self {
        case .string(let s): return s
        case .number(let n): return n == n.rounded() && abs(n) < 1e15 ? String(Int64(n)) : String(n)
        case .bool(let b): return b ? "true" : "false"
        default: return nil
        }
    }

    /// Numbers; the engine encodes infinity as the string "inf".
    public var double: Double? {
        switch self {
        case .number(let n): return n
        case .string(let s):
            if s == "inf" { return .infinity }
            if s == "-inf" { return -.infinity }
            return Double(s)
        default: return nil
        }
    }

    public var int: Int? {
        guard let d = double, d.isFinite else { return nil }
        return Int(d)
    }

    public var bool: Bool? {
        if case .bool(let b) = self { return b }
        return nil
    }

    public var array: [JSONValue]? {
        if case .array(let a) = self { return a }
        return nil
    }

    public var object: [String: JSONValue]? {
        if case .object(let o) = self { return o }
        return nil
    }

    public var isNull: Bool {
        if case .null = self { return true }
        return false
    }

    public var description: String {
        switch self {
        case .null: return "null"
        case .bool(let b): return String(b)
        case .number: return string ?? ""
        case .string(let s): return s
        case .array(let a): return "[" + a.map { $0.description }.joined(separator: ", ") + "]"
        case .object(let o):
            return "{" + o.keys.sorted().map { "\($0): \(o[$0]!.description)" }.joined(separator: ", ") + "}"
        }
    }

    public func encodedData() -> Data {
        (try? JSONEncoder().encode(self)) ?? Data()
    }
}

public extension Dictionary where Key == String, Value == JSONValue {
    static func from(_ any: [String: Any]) -> [String: JSONValue] {
        var out: [String: JSONValue] = [:]
        for (k, v) in any { out[k] = JSONValue.from(v) }
        return out
    }
}

public extension JSONValue {
    static func from(_ any: Any?) -> JSONValue {
        switch any {
        case nil: return .null
        case let b as Bool: return .bool(b)
        case let i as Int: return .number(Double(i))
        case let d as Double: return .number(d)
        case let s as String: return .string(s)
        case let a as [Any]: return .array(a.map { JSONValue.from($0) })
        case let o as [String: Any]: return .object(.from(o))
        case let j as JSONValue: return j
        default: return .string(String(describing: any!))
        }
    }
}
