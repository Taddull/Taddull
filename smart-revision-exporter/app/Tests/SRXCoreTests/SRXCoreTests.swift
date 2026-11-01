import XCTest
@testable import SRXCore

final class TimecodeTests: XCTestCase {
    func testRates() {
        XCTAssertEqual(FrameRate(string: "23.976"), FrameRate(24000, 1001))
        XCTAssertEqual(FrameRate(string: "29.97"), FrameRate(30000, 1001))
        XCTAssertEqual(FrameRate(string: "30000/1001"), FrameRate(30000, 1001))
        XCTAssertEqual(FrameRate(string: "25"), FrameRate(25))
        XCTAssertNil(FrameRate(string: "abc"))
    }

    func testNonDropRoundTrip() throws {
        let r = FrameRate(24000, 1001)
        for f in [0, 1, 23, 24, 86_399, 86_400, 123_456] {
            XCTAssertEqual(try Timecode.frames(from: Timecode.string(from: f, rate: r), rate: r), f)
        }
        XCTAssertEqual(try Timecode.frames(from: "01:00:00:00", rate: FrameRate(25)), 90_000)
    }

    func testDropFrame() throws {
        let r = FrameRate(30000, 1001)
        XCTAssertEqual(Timecode.string(from: 1800, rate: r, dropFrame: true), "00:01:00;02")
        XCTAssertEqual(try Timecode.frames(from: "00:01:00;02", rate: r), 1800)
        XCTAssertEqual(Timecode.string(from: 17_982, rate: r, dropFrame: true), "00:10:00;00")
        for f in stride(from: 0, to: 40_000, by: 997) {
            let tc = Timecode.string(from: f, rate: r, dropFrame: true)
            XCTAssertEqual(try Timecode.frames(from: tc, rate: r, dropFrame: true), f)
        }
        XCTAssertThrowsError(try Timecode.frames(from: "00:01:00;00", rate: r, dropFrame: true))
    }
}

final class RevisionSetTests: XCTestCase {
    func testSortMergeAndIssues() {
        var s = RevisionSet([
            RevisionRange(start: 300, end: 320),
            RevisionRange(start: 100, end: 150, label: "a"),
            RevisionRange(start: 140, end: 160, label: "b"),
            RevisionRange(start: 160, end: 170),
        ])
        XCTAssertEqual(s.items.map { $0.start }, [100, 140, 160, 300])
        XCTAssertTrue(s.issues(frameCount: 1000).contains { if case .overlaps = $0 { return true }; return false })
        s.mergeOverlapping()
        XCTAssertEqual(s.items.count, 2)
        XCTAssertEqual(s.items[0].start, 100)
        XCTAssertEqual(s.items[0].end, 170)
        XCTAssertEqual(s.items[0].label, "a + b")
        XCTAssertTrue(s.issues(frameCount: 1000).isEmpty)
        XCTAssertFalse(s.issues(frameCount: 310).isEmpty)
    }
}

final class EngineEventTests: XCTestCase {
    func testParseEvents() {
        let e = EngineEvent(line: #"{"type": "progress", "stage": "render", "fraction": 0.25, "eta_s": 12.5, "ts": 1}"#)
        XCTAssertEqual(e?.type, "progress")
        XCTAssertEqual(e?.stage, "render")
        XCTAssertEqual(e?.fraction, 0.25)
        XCTAssertNil(EngineEvent(line: "not json"))
        let inf = JSONValue.parse(#"{"psnr": "inf", "n": 3}"#)
        XCTAssertEqual(inf?["psnr"]?.double, .infinity)
        XCTAssertEqual(inf?["n"]?.int, 3)
    }

    func testRequestJSON() {
        let req = ExportRequest(master: "/m.mp4", output: "/o.mp4", mode: .verifiedPatch, strict: false,
                                audio: .auto, quality: .high, preset: "slow",
                                revisions: [RevisionRange(start: 10, end: 20)], timelineOffset: 86_400,
                                useResolve: true, manualRenders: [], rate: FrameRate(24000, 1001))
        let j = JSONValue.object(req.json)
        XCTAssertEqual(j["mode"]?.string, "verified")
        XCTAssertEqual(j["revisions"]?[0]?["end"]?.int, 20)
        XCTAssertEqual(j["source"]?["type"]?.string, "resolve")
        XCTAssertEqual(req.command, "export")
        let data = j.encodedData()
        XCTAssertEqual(JSONValue.parse(data), j)
    }
}
