// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ValidateMyPhoto",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "ValidateMyPhoto", targets: ["ValidateMyPhoto"])
    ],
    targets: [
        .executableTarget(
            name: "ValidateMyPhoto",
            path: "ValidateMyPhoto",
            exclude: [
                "Resources/Info.plist",
                "Resources/ValidateMyPhoto.entitlements",
                "Resources/Assets.xcassets"
            ],
            resources: [
                // Script produces .mlpackage (Python ≤3.12) or .mlmodel (Python 3.13+)
                // Whichever exists in Resources/ is picked up at build time.
                .copy("Resources/AIGCDetector.mlpackage"),
            ]
        )
    ]
)
