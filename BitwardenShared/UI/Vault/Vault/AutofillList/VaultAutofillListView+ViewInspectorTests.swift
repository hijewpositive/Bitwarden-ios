// swiftlint:disable:this file_name
import BitwardenKit
import BitwardenKitMocks
import BitwardenResources
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
}
