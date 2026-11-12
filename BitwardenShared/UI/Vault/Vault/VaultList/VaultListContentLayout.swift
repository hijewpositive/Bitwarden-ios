import SwiftUI

/// Width policy for the adaptive vault surfaces.
enum VaultListContentLayout {
    /// Leaves useful side margins on the Duo's 669-point inner portrait viewport while keeping
    /// compact phone layouts edge-to-edge.
    static let maximumContentWidth: CGFloat = 600

    /// Returns the scroll view width without exceeding the available viewport or readable maximum.
    static func contentWidth(for availableWidth: CGFloat) -> CGFloat {
        min(availableWidth, maximumContentWidth)
    }

}

#if DEBUG
/// Collects rendered frames from the vault list's adaptive surfaces and primary controls.
struct VaultListLayoutFramePreferenceKey: PreferenceKey {
    /// A coordinate space used by layout verification to measure the rendered vault surfaces.
    static let coordinateSpaceName = "VaultListContentLayout"

    static var defaultValue: [String: CGRect] = [:]

    static func reduce(value: inout [String: CGRect], nextValue: () -> [String: CGRect]) {
        value.merge(nextValue(), uniquingKeysWith: { _, next in next })
    }
}

extension View {
    /// Reports this view's rendered frame for hosted layout verification.
    func vaultListLayoutFrame(_ identifier: String) -> some View {
        background {
            GeometryReader { geometry in
                Color.clear.preference(
                    key: VaultListLayoutFramePreferenceKey.self,
                    value: [
                        identifier: geometry.frame(in: .named(VaultListLayoutFramePreferenceKey.coordinateSpaceName)),
                    ],
                )
            }
        }
    }
}
#else
extension View {
    /// Leaves no test-only geometry instrumentation in release builds.
    func vaultListLayoutFrame(_ identifier: String) -> some View {
        self
    }
}
#endif
