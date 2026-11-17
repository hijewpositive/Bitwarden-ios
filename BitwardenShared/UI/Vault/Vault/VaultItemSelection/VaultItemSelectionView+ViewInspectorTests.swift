// swiftlint:disable:this file_name
import BitwardenKit
import BitwardenKitMocks
import BitwardenResources
import BitwardenSdk
import SwiftUI
#if DEBUG
import UIKit
#endif
import XCTest

@testable import BitwardenShared
@testable import BitwardenSharedMocks

class VaultItemSelectionViewTests: BitwardenTestCase {
    // MARK: Properties

    var processor: MockProcessor<VaultItemSelectionState, VaultItemSelectionAction, VaultItemSelectionEffect>!
    var subject: VaultItemSelectionView!

    // MARK: Setup & Teardown

    override func setUp() {
        super.setUp()

        processor = MockProcessor(state: VaultItemSelectionState(
            iconBaseURL: nil,
            totpKeyModel: .fixtureExample,
        ))
        let store = Store(processor: processor)

        subject = VaultItemSelectionView(store: store)
    }

    override func tearDown() {
        super.tearDown()

        processor = nil
        subject = nil
    }

    // MARK: Tests

    #if DEBUG
    /// Measures the actual inner viewport, column, item, and add control with synthetic data.
    @MainActor
    func test_adaptiveLayout_hostedCompactDuoAndWide() throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Synthetic Item"))
        processor.state.vaultListSections = [VaultListSection(id: "synthetic", items: [item], name: "Items")]
        for (width, expected) in [(CGFloat(390), CGFloat(390)), (669, 600), (1_024, 600)] {
            let hosted = makeHostedLayout(width: width)
            defer { removeHostedLayout(hosted) }
            waitFor(hosted.recorder.frames["VaultItemSelectionRow"] != nil)
            let viewport = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionViewport"])
            let content = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionContent"])
            let row = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionRow"])
            let add = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionAddButton"])
            XCTAssertEqual(viewport.width, width, accuracy: 0.5)
            XCTAssertEqual(content.width, expected, accuracy: 0.5)
            XCTAssertEqual(content.midX, viewport.midX, accuracy: 0.5)
            XCTAssertGreaterThanOrEqual(row.minX, content.minX - 1)
            XCTAssertLessThanOrEqual(row.maxX, content.maxX + 1)
            XCTAssertGreaterThanOrEqual(add.minX, content.minX - 1)
            XCTAssertLessThanOrEqual(add.maxX, content.maxX + 1)
            XCTAssertGreaterThanOrEqual(add.minY, viewport.minY)
            XCTAssertLessThanOrEqual(add.maxY, viewport.maxY)
        }
    }

    /// Search results use the same centered column as matching items.
    @MainActor
    func test_adaptiveLayout_hostedSearch() throws {
        processor.state.searchText = "Synthetic"
        processor.state.searchResults = [.fixture(cipherListView: .fixture(name: "Synthetic Item"))]
        let hosted = makeHostedLayout(width: 669)
        defer { removeHostedLayout(hosted) }
        waitFor(hosted.recorder.frames["VaultItemSelectionRow"] != nil)
        let viewport = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionViewport"])
        let content = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionContent"])
        let row = try XCTUnwrap(hosted.recorder.frames["VaultItemSelectionRow"])
        XCTAssertEqual(viewport.width, 669, accuracy: 0.5)
        XCTAssertEqual(content.width, 600, accuracy: 0.5)
        XCTAssertEqual(content.midX, viewport.midX, accuracy: 0.5)
        XCTAssertGreaterThanOrEqual(row.minX, content.minX - 1)
        XCTAssertLessThanOrEqual(row.maxX, content.maxX + 1)
    }
    #endif

    /// A synthetic search result dispatches the same selection effect as a matching item.
    @MainActor
    func test_searchResult_tap() async throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Synthetic Item"))
        processor.state.searchText = "Synthetic"
        processor.state.searchResults = [item]
        let button = try subject.inspect().find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton")
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .vaultListItemTapped(item))
    }

    /// Tapping the add item floating action button dispatches the `.addTapped` action.`
    @MainActor
    func test_addFloatingActionButton_tap() async throws {
        let fab = try subject.inspect().find(
            floatingActionButtonWithAccessibilityIdentifier: "AddItemFloatingActionButton",
        )
        try await fab.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addTapped)
    }

    /// Tapping the cancel button dispatches the `.cancelTapped` action.
    @MainActor
    func test_cancelButton_tap() throws {
        let button = try subject.inspect().findCancelToolbarButton()
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .cancelTapped)
    }

    /// In the empty state, tapping the add item button dispatches the `.addTapped` action.
    @MainActor
    func test_emptyState_addItemTapped() throws {
        let button = try subject.inspect().find(button: Localizations.addItem)
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addTapped)
    }

    /// Tapping a vault item row performs the `.vaultListItemTapped` effect.
    @MainActor
    func test_vaultListItem_tap() async throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Item"))
        processor.state.vaultListSections = [
            VaultListSection(id: "Items", items: [item], name: Localizations.items),
        ]
        let button = try subject.inspect().find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton")
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .vaultListItemTapped(item))
    }

    #if DEBUG
    @MainActor
    private func makeHostedLayout(width: CGFloat) -> HostedItemSelectionLayout {
        let frame = CGRect(x: 0, y: 0, width: width, height: 1_000)
        let recorder = ItemSelectionFrameRecorder()
        let controller = UIHostingController(rootView: ItemSelectionTestHost(subject: subject, recorder: recorder))
        let scene = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .first(where: { $0.activationState == .foregroundActive })
        let window: UIWindow
        if let scene {
            window = UIWindow(windowScene: scene)
        } else {
            window = UIWindow(frame: frame)
        }
        window.frame = frame
        window.rootViewController = controller
        window.makeKeyAndVisible()
        controller.view.frame = frame
        controller.view.setNeedsLayout()
        window.setNeedsLayout()
        window.layoutIfNeeded()
        controller.view.layoutIfNeeded()
        return HostedItemSelectionLayout(window: window, controller: controller, recorder: recorder)
    }

    @MainActor
    private func removeHostedLayout(_ hosted: HostedItemSelectionLayout) {
        hosted.window.isHidden = true
        hosted.window.rootViewController = nil
    }
    #endif
}

#if DEBUG
@MainActor
private final class ItemSelectionFrameRecorder {
    var frames: [String: CGRect] = [:]
}

@MainActor
private struct ItemSelectionTestHost: View {
    let subject: VaultItemSelectionView
    let recorder: ItemSelectionFrameRecorder

    var body: some View {
        subject
            .coordinateSpace(name: VaultListLayoutFramePreferenceKey.coordinateSpaceName)
            .onPreferenceChange(VaultListLayoutFramePreferenceKey.self) { recorder.frames = $0 }
            .ignoresSafeArea(.container, edges: .horizontal)
    }
}

@MainActor
private struct HostedItemSelectionLayout {
    let window: UIWindow
    let controller: UIHostingController<ItemSelectionTestHost>
    let recorder: ItemSelectionFrameRecorder
}
#endif
