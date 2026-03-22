// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "ScorecardMacApp",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "ScorecardMacApp",
            targets: ["ScorecardMacApp"]
        )
    ],
    targets: [
        .executableTarget(
            name: "ScorecardMacApp"
        )
    ]
)
