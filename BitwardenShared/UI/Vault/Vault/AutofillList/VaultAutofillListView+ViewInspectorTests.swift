// swiftlint:disable:this file_name
import BitwardenKit
import BitwardenKitMocks
import BitwardenResources
#if DEBUG
import SwiftUI
import UIKit
#endif
import ViewInspector
import XCTest

@testable import BitwardenShared
@testable import BitwardenSharedMocks

class VaultAutofillListViewTests: BitwardenTestCase {
    // MARK: Properties

    var processor: MockProcessor<VaultAutofillListState, VaultAutofillListAction, VaultAutofillListEffect>!
    var subject: VaultAutofillListView!
    var timeProvider: MockTimeProvider!

    // MARK: Setup & Teardown

    override func setUp() {
        super.setUp()

        processor = MockProcessor(state: VaultAutofillListState())
        let store = Store(processor: processor)
        timeProvider = MockTimeProvider(.currentTime)

        subject = VaultAutofillListView(store: store, timeProvider: timeProvider)
    }

    override func tearDown() {
        super.tearDown()

        processor = nil
        subject = nil
        timeProvider = nil
    }

    // MARK: Tests

    #if DEBUG
    /// Measure actual AutoFill viewport, content, row and add control at compact, Duo and wide sizes.
    @MainActor
    func test_adaptiveLayout_hostedViewportAndControls() throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Synthetic Item"))
        processor.state.loadingState = .data([VaultListSection(id: "items", items: [item], name: "Items")])
        for (width, expected) in [(CGFloat(390), CGFloat(390)), (669, 600), (1_024, 600)] {
            let host = makeHostedLayout(width: width)
            defer { removeHostedLayout(host) }
            waitFor(host.recorder.frames["VaultAutofillAddButton"] != nil)
            try assertHostedFrames(host, viewportWidth: width, contentWidth: expected, hasAddButton: true)
        }
    }

    /// Search transition retains the measured content cap and keeps the result within the viewport.
    @MainActor
    func test_adaptiveLayout_hostedSearchTransition() throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Synthetic Result"))
        processor.state.loadingState = .data([])
        let host = makeHostedLayout(width: 669)
        defer { removeHostedLayout(host) }
        waitFor(host.recorder.frames["VaultAutofillContent"] != nil)
        processor.state.ciphersForSearch = [VaultListSection(id: "search", items: [item], name: "Items")]
        processor.state.searchText = "Synthetic"
        waitFor(host.recorder.frames["VaultAutofillItemRow"] != nil)
        try assertHostedFrames(host, viewportWidth: 669, contentWidth: 600, hasAddButton: false)
    }
    #endif

    /// A synthetic result remains selectable inside the adaptive AutoFill column.
    @MainActor
    func test_adaptiveLayout_itemSelection_keepsRowAndSelectionEffect() async throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Synthetic Item"))
        processor.state.loadingState = .data([VaultListSection(id: "items", items: [item], name: "Items")])
        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultAutofillContent")
        let row = try content.find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton")
        try await row.tap()
        XCTAssertEqual(processor.effects.last, .vaultItemTapped(item))
    }

    /// Search results and the no-results message remain in the same adaptive AutoFill column.
    @MainActor
    func test_adaptiveLayout_search_keepsResultsAndNoResults() throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Synthetic Result"))
        processor.state.searchText = "Synthetic"
        processor.state.ciphersForSearch = [VaultListSection(id: "search", items: [item], name: "Items")]
        var content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultAutofillContent")
        XCTAssertNoThrow(try content.find(asyncButton: "Synthetic Result"))

        processor.state.ciphersForSearch = []
        processor.state.showNoResults = true
        content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultAutofillContent")
        XCTAssertNoThrow(try content.find(viewWithAccessibilityIdentifier: "NoSearchResultsLabel"))
    }

    /// An empty AutoFill state keeps its existing add action in the column.
    @MainActor
    func test_adaptiveLayout_emptyState_keepsAddAction() throws {
        processor.state.loadingState = .data([])
        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultAutofillContent")
        let button = try content.find(button: Localizations.addItem)
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addTapped(fromFAB: false))
    }

    /// Tapping the add item floating action button dispatches the `.addItemPressed` action.`
    @MainActor
    func test_addItemFloatingActionButton_tap() async throws {
        let fab = try subject.inspect().find(
            floatingActionButtonWithAccessibilityIdentifier: "AddItemFloatingActionButton",
        )
        try await fab.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addTapped(fromFAB: true))
    }

    /// Tapping the add an item button dispatches the `.addTapped` action.
    @MainActor
    func test_addItemButton_tap_fido2CreationFlowEmptyView() throws {
        processor.state.isCreatingFido2Credential = true
        processor.state.loadingState = .data([])
        processor.state.emptyViewButtonText = Localizations.savePasskeyAsNewLogin
        let button = try subject.inspect().find(button: Localizations.savePasskeyAsNewLogin)
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addTapped(fromFAB: false))
    }

    /// Tapping the cancel button dispatches the `.cancelTapped` action.
    @MainActor
    func test_cancelButton_tap() throws {
        let button = try subject.inspect().findCancelToolbarButton()
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .cancelTapped)
    }

    /// Tapping the retry button in error state performs the `.loadData` effect.
    @MainActor
    func test_retryButton_tap_errorState() async throws {
        processor.state.loadingState = .error(
            errorMessage: Localizations.weAreUnableToProcessYourRequestPleaseTryAgainOrContactUs,
        )
        let button = try subject.inspect().find(asyncButton: Localizations.tryAgain)
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .loadData)
    }

    /// Tapping a vault item row performs the `.vaultItemTapped` effect.
    @MainActor
    func test_vaultItem_tap() async throws {
        let item = VaultListItem.fixture(cipherListView: .fixture(name: "Item"))
        processor.state.loadingState = .data([VaultListSection(id: "Items", items: [item], name: Localizations.items)])
        let button = try subject.inspect().find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton")
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .vaultItemTapped(item))
    }

    #if DEBUG
    @MainActor
    private func makeHostedLayout(width: CGFloat) -> HostedAutofillLayout {
        let frame = CGRect(x: 0, y: 0, width: width, height: 1_000)
        let recorder = AutofillFrameRecorder()
        let controller = UIHostingController(rootView: AutofillLayoutTestHost(subject: subject, recorder: recorder))
        let scene = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .first(where: { $0.activationState == .foregroundActive })
        let window = scene.map { UIWindow(windowScene: $0) } ?? UIWindow(frame: frame)
        window.frame = frame
        window.rootViewController = controller
        window.makeKeyAndVisible()
        controller.view.frame = frame
        controller.view.setNeedsLayout()
        window.setNeedsLayout()
        window.layoutIfNeeded()
        controller.view.layoutIfNeeded()
        return HostedAutofillLayout(window: window, controller: controller, recorder: recorder)
    }

    @MainActor
    private func removeHostedLayout(_ host: HostedAutofillLayout) {
        host.window.isHidden = true
        host.window.rootViewController = nil
    }

    @MainActor
    private func assertHostedFrames(
        _ host: HostedAutofillLayout,
        viewportWidth: CGFloat,
        contentWidth: CGFloat,
        hasAddButton: Bool,
    ) throws {
        let viewport = try XCTUnwrap(host.recorder.frames["VaultAutofillViewport"])
        let content = try XCTUnwrap(host.recorder.frames["VaultAutofillContent"])
        let row = try XCTUnwrap(host.recorder.frames["VaultAutofillItemRow"])
        XCTAssertEqual(viewport.width, viewportWidth, accuracy: 0.5)
        XCTAssertEqual(content.width, contentWidth, accuracy: 0.5)
        XCTAssertEqual(content.midX, viewport.midX, accuracy: 0.5)
        XCTAssertEqual(content.minX - viewport.minX, (viewportWidth - contentWidth) / 2, accuracy: 0.5)
        XCTAssertGreaterThan(row.width, 0)
        XCTAssertGreaterThan(row.height, 0)
        XCTAssertGreaterThanOrEqual(row.minX, content.minX - 1)
        XCTAssertLessThanOrEqual(row.maxX, content.maxX + 1)
        XCTAssertGreaterThanOrEqual(row.minY, viewport.minY - 1)
        XCTAssertLessThanOrEqual(row.maxY, viewport.maxY + 1)
        if hasAddButton {
            let button = try XCTUnwrap(host.recorder.frames["VaultAutofillAddButton"])
            XCTAssertGreaterThan(button.width, 0)
            XCTAssertGreaterThan(button.height, 0)
            XCTAssertGreaterThanOrEqual(button.minX, content.minX - 1)
            XCTAssertLessThanOrEqual(button.maxX, content.maxX + 1)
            XCTAssertGreaterThanOrEqual(button.minY, viewport.minY - 1)
            XCTAssertLessThanOrEqual(button.maxY, viewport.maxY + 1)
            XCTAssertEqual(button.maxX, content.maxX, accuracy: 0.5)
        }
    }
    #endif
}

#if DEBUG
@MainActor
private final class AutofillFrameRecorder {
    var frames: [String: CGRect] = [:]
}

@MainActor
private struct AutofillLayoutTestHost: View {
    let subject: VaultAutofillListView
    let recorder: AutofillFrameRecorder

    var body: some View {
        subject
            .coordinateSpace(name: VaultListLayoutFramePreferenceKey.coordinateSpaceName)
            .onPreferenceChange(VaultListLayoutFramePreferenceKey.self) { frames in
                recorder.frames = frames
            }
            .ignoresSafeArea(.container, edges: .horizontal)
    }
}

@MainActor
private struct HostedAutofillLayout {
    let window: UIWindow
    let controller: UIHostingController<AutofillLayoutTestHost>
    let recorder: AutofillFrameRecorder
}
#endif
