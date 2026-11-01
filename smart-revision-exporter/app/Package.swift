// swift-tools-version:5.9
// Smart Revision Exporter - native macOS front end (SwiftUI) for the srx engine.
import PackageDescription

let package = Package(
    name: "SmartRevisionExporter",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "SmartRevisionExporter", targets: ["SmartRevisionExporter"]),
        .library(name: "SRXCore", targets: ["SRXCore"]),
    ],
    targets: [
        // Foundation-only logic: engine process client, JSON models, timecode, revision set.
        .target(name: "SRXCore", path: "Sources/SRXCore"),
        // SwiftUI application.
        .executableTarget(
            name: "SmartRevisionExporter",
            dependencies: ["SRXCore"],
            path: "Sources/SmartRevisionExporter"
        ),
        .testTarget(name: "SRXCoreTests", dependencies: ["SRXCore"], path: "Tests/SRXCoreTests"),
    ]
)
