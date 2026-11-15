import CoreGraphics
import Testing

@testable import BitwardenShared

struct VaultListContentLayoutTests {
    @Test(arguments: [
        (CGFloat(0), CGFloat(0)),
        (CGFloat(320), CGFloat(320)),
        (CGFloat(390), CGFloat(390)),
        (CGFloat(599.5), CGFloat(599.5)),
        (CGFloat(600), CGFloat(600)),
        (CGFloat(600.5), CGFloat(600)),
        (CGFloat(669), CGFloat(600)),
        (CGFloat(1_024), CGFloat(600)),
    ])
    func contentWidth_respectsCompactAndWideBoundary(available: CGFloat, expected: CGFloat) {
        #expect(VaultListContentLayout.contentWidth(for: available) == expected)
    }

    @Test
    func contentWidth_remainsBoundedAndMonotonicAcrossViewportSizes() {
        var previous: CGFloat = 0
        for points in 0 ... 2_000 {
            let available = CGFloat(points)
            let width = VaultListContentLayout.contentWidth(for: available)
            #expect(width >= previous)
            #expect(width <= available)
            #expect(width <= 600)
            guard width >= previous, width <= available, width <= 600 else { return }
            previous = width
        }
    }

    @Test
    func contentWidth_reactsToNarrowingAndWidening() {
        let widths: [CGFloat] = [390, 669, 1_024, 600, 390]
        let expected: [CGFloat] = [390, 600, 600, 600, 390]
        #expect(widths.map(VaultListContentLayout.contentWidth(for:)) == expected)
    }
}
