import Foundation

public enum EngineError: Error, LocalizedError {
    case pythonNotFound
    case engineNotFound
    case launchFailed(String)
    case failed(code: Int32, message: String)

    public var errorDescription: String? {
        switch self {
        case .pythonNotFound:
            return "Python 3 was not found. Install it (python.org or Homebrew) or set its path in Diagnostics."
        case .engineNotFound:
            return "The srx engine was not found inside the application bundle."
        case .launchFailed(let m):
            return "Could not start the engine: \(m)"
        case .failed(let code, let message):
            return message.isEmpty ? "Engine exited with code \(code)." : message
        }
    }
}

/// Locates the Python interpreter and the bundled engine package.
public enum EngineLocator {
    public static var supportDirectory: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Library/Application Support")
        return base.appendingPathComponent("Smart Revision Exporter", isDirectory: true)
    }

    public static func pythonCandidates(userPath: String?) -> [String] {
        var c: [String] = []
        if let u = userPath, !u.isEmpty { c.append(u) }
        c.append(supportDirectory.appendingPathComponent("venv/bin/python3").path)
        c += ["/opt/homebrew/bin/python3", "/usr/local/bin/python3",
              "/Library/Frameworks/Python.framework/Versions/Current/bin/python3", "/usr/bin/python3"]
        return c
    }

    public static func findPython(userPath: String?) -> String? {
        pythonCandidates(userPath: userPath).first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    /// Engine directory containing the `srx` package.
    public static func engineDirectory(bundle: Bundle = .main) -> String? {
        if let env = ProcessInfo.processInfo.environment["SRX_ENGINE_DIR"],
           FileManager.default.fileExists(atPath: env + "/srx/__init__.py") {
            return env
        }
        if let res = bundle.resourceURL?.appendingPathComponent("engine").path,
           FileManager.default.fileExists(atPath: res + "/srx/__init__.py") {
            return res
        }
        // Development: running from app/ inside the source tree.
        let dev = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("../engine").standardizedFileURL.path
        if FileManager.default.fileExists(atPath: dev + "/srx/__init__.py") { return dev }
        return nil
    }
}

public enum EngineOutput {
    case event(EngineEvent)
    case stderr(String)
    case exit(Int32)
}

/// A running engine process.  `cancel()` sends SIGINT; the engine stops its
/// FFmpeg/Resolve work, removes partial output and exits with code 130.
public final class EngineTask {
    let process: Process

    init(process: Process) { self.process = process }

    public var isRunning: Bool { process.isRunning }

    public func cancel() {
        if process.isRunning { process.interrupt() }
    }

    public func terminate() {
        if process.isRunning { process.terminate() }
    }
}

public final class EngineClient {
    public let python: String
    public let engineDir: String

    public init(python: String, engineDir: String) {
        self.python = python
        self.engineDir = engineDir
    }

    public static func make(userPython: String?) throws -> EngineClient {
        guard let py = EngineLocator.findPython(userPath: userPython) else { throw EngineError.pythonNotFound }
        guard let dir = EngineLocator.engineDirectory() else { throw EngineError.engineNotFound }
        return EngineClient(python: py, engineDir: dir)
    }

    var environment: [String: String] {
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = engineDir
        env["PYTHONUNBUFFERED"] = "1"
        let extra = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
        env["PATH"] = (env["PATH"].map { $0 + ":" } ?? "") + extra
        return env
    }

    /// Start `python3 -m srx <args>`.  Output arrives, in order, on the returned
    /// stream: events (JSON lines on stdout), stderr lines, then the exit code.
    public func stream(_ args: [String]) throws -> (EngineTask, AsyncStream<EngineOutput>) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: python)
        p.arguments = ["-m", "srx"] + args
        p.environment = environment
        p.currentDirectoryURL = URL(fileURLWithPath: engineDir)
        let out = Pipe()
        let err = Pipe()
        p.standardOutput = out
        p.standardError = err
        p.standardInput = FileHandle.nullDevice

        var continuation: AsyncStream<EngineOutput>.Continuation!
        let stream = AsyncStream<EngineOutput>(bufferingPolicy: .unbounded) { continuation = $0 }
        let cont = continuation!
        let splitter = LineSplitter { line in
            if let ev = EngineEvent(line: line) { cont.yield(.event(ev)) }
        }
        let errSplitter = LineSplitter { line in cont.yield(.stderr(line)) }
        out.fileHandleForReading.readabilityHandler = { h in
            let d = h.availableData
            if d.isEmpty { h.readabilityHandler = nil } else { splitter.feed(d) }
        }
        err.fileHandleForReading.readabilityHandler = { h in
            let d = h.availableData
            if d.isEmpty { h.readabilityHandler = nil } else { errSplitter.feed(d) }
        }
        p.terminationHandler = { proc in
            // stop the async handlers, then drain what is left before reporting the exit
            out.fileHandleForReading.readabilityHandler = nil
            err.fileHandleForReading.readabilityHandler = nil
            splitter.feed(out.fileHandleForReading.readDataToEndOfFile())
            splitter.flush()
            errSplitter.feed(err.fileHandleForReading.readDataToEndOfFile())
            errSplitter.flush()
            cont.yield(.exit(proc.terminationStatus))
            cont.finish()
        }
        do {
            try p.run()
        } catch {
            cont.finish()
            throw EngineError.launchFailed(error.localizedDescription)
        }
        return (EngineTask(process: p), stream)
    }

    /// Run a short command and return all events (for probe/status/plan).
    public func run(_ args: [String]) async throws -> [EngineEvent] {
        let (_, output) = try stream(args)
        var events: [EngineEvent] = []
        var stderrLines: [String] = []
        var code: Int32 = -1
        for await o in output {
            switch o {
            case .event(let e): events.append(e)
            case .stderr(let l): stderrLines.append(l)
            case .exit(let c): code = c
            }
        }
        if code == 0 { return events }
        let msg = events.last(where: { $0.type == "error" })?.message ?? stderrLines.suffix(5).joined(separator: "\n")
        throw EngineError.failed(code: code, message: msg)
    }

    /// Convenience: the payload of the final `result` event.
    public func result(_ args: [String]) async throws -> JSONValue {
        let events = try await run(args + ["--json"])
        guard let r = events.last(where: { $0.type == "result" }) else {
            throw EngineError.failed(code: 1, message: "engine returned no result")
        }
        return r.body
    }

    /// Write a request JSON file into the support directory and return its path.
    public static func writeRequest(_ request: [String: JSONValue]) throws -> String {
        let dir = EngineLocator.supportDirectory.appendingPathComponent("requests", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("request-\(UUID().uuidString).json")
        try JSONValue.object(request).encodedData().write(to: url, options: .atomic)
        return url.path
    }
}

/// Splits a byte stream into UTF-8 lines (thread-safe).
final class LineSplitter {
    private var buffer = Data()
    private let lock = NSLock()
    private let onLine: (String) -> Void

    init(onLine: @escaping (String) -> Void) { self.onLine = onLine }

    func feed(_ data: Data) {
        guard !data.isEmpty else { return }
        lock.lock()
        buffer.append(data)
        var lines: [String] = []
        while let nl = buffer.firstIndex(of: 0x0A) {
            let lineData = buffer.subdata(in: buffer.startIndex..<nl)
            buffer.removeSubrange(buffer.startIndex...nl)
            if let s = String(data: lineData, encoding: .utf8) { lines.append(s) }
        }
        lock.unlock()
        lines.forEach(onLine)
    }

    func flush() {
        lock.lock()
        let rest = buffer
        buffer.removeAll()
        lock.unlock()
        if !rest.isEmpty, let s = String(data: rest, encoding: .utf8) { onLine(s) }
    }
}
