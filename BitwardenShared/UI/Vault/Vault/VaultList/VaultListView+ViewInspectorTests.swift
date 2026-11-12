// swiftlint:disable:this file_name
// swiftlint:disable file_length
import BitwardenKit
import BitwardenKitMocks
import BitwardenResources
import BitwardenSdk
import SwiftUI
#if DEBUG
import UIKit
#endif
import ViewInspector
import ViewInspectorTestHelpers
import XCTest

@testable import BitwardenShared
@testable import BitwardenSharedMocks

// MARK: - VaultListViewTests

class VaultListViewTests: BitwardenTestCase { // swiftlint:disable:this type_body_length
    // MARK: Properties

    var processor: MockProcessor<VaultListState, VaultListAction, VaultListEffect>!
    var subject: VaultListView!
    var timeProvider: MockTimeProvider!

    // MARK: Setup & Teardown

    override func setUp() {
        super.setUp()

        let account = ProfileSwitcherItem.fixture(
            email: "anne.account@bitwarden.com",
            userInitials: "AA",
        )
        let state = VaultListState(
            itemTypesUserCanCreate: CipherType.canCreateCases,
            profileSwitcherState: ProfileSwitcherState(
                accounts: [account],
                activeAccountId: account.userId,
                allowLockAndLogout: true,
                isVisible: false,
            ),
        )
        processor = MockProcessor(state: state)
        timeProvider = MockTimeProvider(.mockTime(Date(year: 2023, month: 12, day: 31)))
        subject = VaultListView(
            store: Store(processor: processor),
            timeProvider: timeProvider,
        )
    }

    override func tearDown() {
        super.tearDown()

        processor = nil
        subject = nil
        timeProvider = nil
    }

    // MARK: Tests

    // Hosted frame assertions use DEBUG-only geometry preferences, so they intentionally do not
    // compile in Release. The structural ViewInspector tests below do not measure rendered frames.
    #if DEBUG
    /// Hosted Duo, compact, and wide viewports exercise the cap and keep content and controls in bounds.
    @MainActor
    func test_adaptiveLayout_hostedDuoCompactAndWideWidths_centerContentAndKeepControlsReachable() throws {
        let item = VaultListItem.fixture()
        processor.state.loadingState = .data([
            VaultListSection(id: "synthetic-layout", items: [item], name: "Synthetic fixtures"),
        ])

        XCTAssertEqual(VaultListContentLayout.contentWidth(for: 669), 600)
        XCTAssertEqual(VaultListContentLayout.contentWidth(for: 390), 390)
        XCTAssertEqual(VaultListContentLayout.contentWidth(for: 1_024), 600)

        let viewports: [(width: CGFloat, contentWidth: CGFloat, sideMargin: CGFloat)] = [
            (width: 669, contentWidth: 600, sideMargin: 34.5),
            (width: 390, contentWidth: 390, sideMargin: 0),
            (width: 1_024, contentWidth: 600, sideMargin: 212),
        ]
        for viewport in viewports {
            let width = viewport.width
            let hostedLayout = makeHostedLayout(width: width)
            defer { removeHostedLayout(hostedLayout) }

            XCTAssertEqual(hostedLayout.controller.view.bounds.width, width, accuracy: 0.5)
            waitFor(hostedLayout.frameRecorder.frames["VaultListPrimaryContent"] != nil)
            let contentFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListPrimaryContent"])
            let viewportFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListPrimaryContentViewport"])
            let rowFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListItemRow"])
            let addButtonFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListAddItemButton"])

            XCTAssertEqual(
                viewportFrame.width,
                width,
                accuracy: 0.5,
                "Assertions must use the actual recorded viewport.",
            )
            XCTAssertEqual(contentFrame.width, viewport.contentWidth, accuracy: 0.5)
            XCTAssertEqual(contentFrame.midX, viewportFrame.midX, accuracy: 0.5)
            XCTAssertEqual(contentFrame.minX - viewportFrame.minX, viewport.sideMargin, accuracy: 0.5)
            XCTAssertEqual(viewportFrame.maxX - contentFrame.maxX, viewport.sideMargin, accuracy: 0.5)
            XCTAssertGreaterThanOrEqual(rowFrame.minX, contentFrame.minX - 1)
            XCTAssertLessThanOrEqual(rowFrame.maxX, contentFrame.maxX + 1)
            XCTAssertGreaterThanOrEqual(rowFrame.minY, viewportFrame.minY)
            XCTAssertLessThanOrEqual(rowFrame.maxY, viewportFrame.maxY)
            XCTAssertGreaterThanOrEqual(addButtonFrame.minX, contentFrame.minX - 1)
            XCTAssertLessThanOrEqual(addButtonFrame.maxX, contentFrame.maxX + 1)
            XCTAssertGreaterThanOrEqual(addButtonFrame.minY, viewportFrame.minY)
            XCTAssertLessThanOrEqual(addButtonFrame.maxY, viewportFrame.maxY)
            XCTAssertEqual(addButtonFrame.maxX, contentFrame.maxX, accuracy: 0.5)
            if viewport.width > viewport.contentWidth {
                XCTAssertLessThan(addButtonFrame.maxX, viewportFrame.maxX)
            }

            let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultListPrimaryContent")
            XCTAssertNoThrow(try content.find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton"))
            XCTAssertNoThrow(try content.find(viewWithAccessibilityIdentifier: "AddItemFloatingActionButton"))
        }
    }

    /// Hosted search results retain the centered wide layout and keep a synthetic result row in bounds.
    @MainActor
    func test_adaptiveLayout_hostedSearchResults_centerContentAndKeepResultReachable() throws {
        let item = VaultListItem.fixture()
        processor.state.loadingState = .data([])
        processor.state.searchText = "Synthetic search"
        processor.state.searchResults = [item]

        let hostedLayout = makeHostedLayout(width: 669)
        defer { removeHostedLayout(hostedLayout) }
        waitFor(hostedLayout.frameRecorder.frames["VaultListSearchContent"] != nil)

        let viewportFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListSearchContentViewport"])
        let contentFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListSearchContent"])
        let resultFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListItemRow"])
        XCTAssertEqual(viewportFrame.width, 669, accuracy: 0.5, "Assertions must use the actual recorded viewport.")
        XCTAssertEqual(contentFrame.width, 600, accuracy: 0.5)
        XCTAssertEqual(contentFrame.midX, viewportFrame.midX, accuracy: 0.5)
        XCTAssertEqual(contentFrame.minX - viewportFrame.minX, 34.5, accuracy: 0.5)
        XCTAssertEqual(viewportFrame.maxX - contentFrame.maxX, 34.5, accuracy: 0.5)
        XCTAssertGreaterThanOrEqual(resultFrame.minX, contentFrame.minX - 1)
        XCTAssertLessThanOrEqual(resultFrame.maxX, contentFrame.maxX + 1)
        XCTAssertGreaterThanOrEqual(resultFrame.minY, viewportFrame.minY)
        XCTAssertLessThanOrEqual(resultFrame.maxY, viewportFrame.maxY)

        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultListSearchContent")
        XCTAssertNoThrow(try content.find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton"))
    }

    /// A wide hosted error state keeps its retry control inside the centered content column.
    @MainActor
    func test_adaptiveLayout_hostedErrorState_centerContentAndKeepRetryReachable() throws {
        processor.state.loadingState = .error(errorMessage: "Synthetic sync error")

        let hostedLayout = makeHostedLayout(width: 1_024)
        defer { removeHostedLayout(hostedLayout) }
        waitFor(hostedLayout.frameRecorder.frames["VaultListRetryButton"] != nil)

        let viewportFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListPrimaryContentViewport"])
        let contentFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListPrimaryContent"])
        let retryFrame = try XCTUnwrap(hostedLayout.frameRecorder.frames["VaultListRetryButton"])
        XCTAssertEqual(viewportFrame.width, 1_024, accuracy: 0.5)
        XCTAssertEqual(contentFrame.width, 600, accuracy: 0.5)
        XCTAssertEqual(contentFrame.midX, viewportFrame.midX, accuracy: 0.5)
        XCTAssertEqual(contentFrame.minX - viewportFrame.minX, 212, accuracy: 0.5)
        XCTAssertGreaterThanOrEqual(retryFrame.minX, contentFrame.minX - 1)
        XCTAssertLessThanOrEqual(retryFrame.maxX, contentFrame.maxX + 1)
        XCTAssertGreaterThanOrEqual(retryFrame.minY, viewportFrame.minY)
        XCTAssertLessThanOrEqual(retryFrame.maxY, viewportFrame.maxY)

        XCTAssertNoThrow(try subject.inspect().find(asyncButton: Localizations.tryAgain))
    }
    #endif

    /// The empty primary vault state remains inside the adaptive content region.
    @MainActor
    func test_adaptiveLayout_emptyVault_usesPrimaryContentRegion() throws {
        processor.state.loadingState = .data([])

        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultListPrimaryContent")
        XCTAssertNoThrow(try content.find(button: Localizations.addLogin))
    }

    /// Populated vault rows and the add-item menu remain inside the adaptive content region.
    @MainActor
    func test_adaptiveLayout_populatedVault_keepsRowsAndAddMenu() throws {
        processor.state.loadingState = .data([
            VaultListSection(id: "1", items: [.fixture()], name: "Favorites"),
        ])

        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultListPrimaryContent")
        XCTAssertNoThrow(try content.find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton"))
        XCTAssertNoThrow(try content.find(viewWithAccessibilityIdentifier: "AddItemFloatingActionButton"))
    }

    /// Search results use the adaptive search content region.
    @MainActor
    func test_adaptiveLayout_searchResults_useSearchContentRegion() throws {
        processor.state.searchText = "Bitwarden"
        processor.state.searchResults = [.fixture()]

        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultListSearchContent")
        XCTAssertNoThrow(try content.find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton"))
    }

    /// The no-results state uses the same adaptive search content region.
    @MainActor
    func test_adaptiveLayout_noSearchResults_useSearchContentRegion() throws {
        processor.state.searchText = "missing"
        processor.state.searchResults = []

        let content = try subject.inspect().find(viewWithAccessibilityIdentifier: "VaultListSearchContent")
        XCTAssertNoThrow(try content.find(viewWithAccessibilityIdentifier: "NoSearchResultsLabel"))
    }

    /// Tapping the add the new login button dispatches the `.addItemPressed` action.
    @MainActor
    func test_newLoginButton_tap() throws {
        processor.state.loadingState = .data([])
        let button = try subject.inspect().find(button: Localizations.addLogin)
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addItemPressed(.login))
    }

    /// Tapping the floating action button dispatches the `.addItemPressed` action for a new login type.
    @MainActor
    func test_addItemFloatingActionButton_tap() throws {
        let fab = try subject.inspect().find(viewWithAccessibilityIdentifier: "AddItemFloatingActionButton")
        try fab.find(button: Localizations.typeLogin).tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addItemPressed(.login))
    }

    /// Tapping the floating action button dispatches the `.addItemPressed` action for a new identity type.
    @MainActor
    func test_addItemFloatingActionButton_tap_identity() throws {
        let fab = try subject.inspect().find(viewWithAccessibilityIdentifier: "AddItemFloatingActionButton")
        try fab.find(button: Localizations.typeIdentity).tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addItemPressed(.identity))
    }

    /// Tapping the add folder button in the FAB dispatches the `.addFolder` action.
    @MainActor
    func test_addItemFloatingActionButton_tap_addFolder() throws {
        let fab = try subject.inspect().find(viewWithAccessibilityIdentifier: "AddItemFloatingActionButton")
        try fab.find(button: Localizations.folder).tap()
        XCTAssertEqual(processor.dispatchedActions.last, .addFolder)
    }

    /// The floating action button will be hidden if .
    @MainActor
    func test_addItemFloatingActionButton_hidden_policy_enable() throws {
        processor.state.loadingState = .data([])
        processor.state.itemTypesUserCanCreate = [.login, .identity, .secureNote]
        let fab = try subject.inspect().find(viewWithAccessibilityIdentifier: "AddItemFloatingActionButton")
        XCTAssertThrowsError(try fab.find(button: Localizations.typeCard))
    }

    /// Long pressing a profile row dispatches the `.accountLongPressed` action.
    @MainActor
    func test_accountRow_longPress_currentAccount() throws {
        guard #unavailable(iOS 26) else {
            throw XCTSkip("This test is for iOS < 26 and relies on the visibility of the profile switcher.")
        }

        processor.state.profileSwitcherState.isVisible = true
        let accountRow = try subject.inspect().find(button: "anne.account@bitwarden.com")
        let currentAccount = processor.state.profileSwitcherState.activeAccountProfile!
        try accountRow.labelView().callOnLongPressGesture()
        waitFor(!processor.effects.isEmpty)

        XCTAssertEqual(processor.effects.last, .profileSwitcher(.accountLongPressed(currentAccount)))
    }

    /// Tapping a profile row dispatches the `.accountPressed` action.
    @MainActor
    func test_accountRow_tap_currentAccount() throws {
        guard #unavailable(iOS 26) else {
            throw XCTSkip("This test is for iOS < 26 and relies on the visibility of the profile switcher.")
        }

        processor.state.profileSwitcherState.isVisible = true
        let accountRow = try subject.inspect().find(button: "anne.account@bitwarden.com")
        let currentAccount = processor.state.profileSwitcherState.activeAccountProfile!
        try accountRow.labelView().callOnTapGesture()
        waitFor(!processor.effects.isEmpty)

        XCTAssertEqual(processor.effects.last, .profileSwitcher(.accountPressed(currentAccount)))
    }

    /// Tapping the add account row dispatches the `.addAccountPressed ` action.
    @MainActor
    func test_accountRow_tap_addAccount() throws {
        guard #unavailable(iOS 26) else {
            throw XCTSkip("This test is for iOS < 26 and relies on the visibility of the profile switcher.")
        }

        processor.state.profileSwitcherState.isVisible = true
        let addAccountRow = try subject.inspect().find(button: "Add account")
        try addAccountRow.tap()
        waitFor(!processor.effects.isEmpty)

        XCTAssertEqual(processor.effects.last, .profileSwitcher(.addAccountPressed))
    }

    /// The action card is hidden if the import logins setup progress is set up later or complete.
    @MainActor
    func test_importLoginsActionCard_hidden() {
        processor.state.loadingState = .data([])

        // Hidden by default when set up progress is `nil`.
        XCTAssertThrowsError(try subject.inspect().find(actionCard: Localizations.importSavedLogins))

        processor.state.importLoginsSetupProgress = .setUpLater
        XCTAssertThrowsError(try subject.inspect().find(actionCard: Localizations.importSavedLogins))

        processor.state.importLoginsSetupProgress = .complete
        XCTAssertThrowsError(try subject.inspect().find(actionCard: Localizations.importSavedLogins))
    }

    /// The action card is visible if the import logins setup progress is incomplete.
    @MainActor
    func test_importLoginsActionCard_visible() async throws {
        processor.state.importLoginsSetupProgress = .incomplete
        processor.state.loadingState = .data([])
        XCTAssertNoThrow(try subject.inspect().find(actionCard: Localizations.importSavedLogins))
    }

    /// Tapping the dismiss button in the import logins action card sends the
    /// `.dismissImportLoginsActionCard` effect.
    @MainActor
    func test_importLoginsActionCard_visible_tapDismiss() async throws {
        processor.state.importLoginsSetupProgress = .incomplete
        processor.state.loadingState = .data([])
        let actionCard = try subject.inspect().find(actionCard: Localizations.importSavedLogins)

        let button = try actionCard.find(asyncButton: Localizations.dismiss)
        try await button.tap()
        XCTAssertEqual(processor.effects, [.dismissImportLoginsActionCard])
    }

    /// Tapping the get started button in the set up unlock action card sends the
    /// `.showSetUpUnlock` action.
    @MainActor
    func test_importLoginsActionCard_visible_tapGetStarted() async throws {
        processor.state.importLoginsSetupProgress = .incomplete
        processor.state.loadingState = .data([])
        let actionCard = try subject.inspect().find(actionCard: Localizations.importSavedLogins)

        let button = try actionCard.find(asyncButton: Localizations.getStarted)
        try await button.tap()
        XCTAssertEqual(processor.dispatchedActions, [.showImportLogins])
    }

    /// The subscription attention action card is hidden when `shouldShowSubscriptionAttentionCard` is false.
    @MainActor
    func test_subscriptionAttentionActionCard_hidden() {
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [.fixture()], name: "")])
        processor.state.shouldShowSubscriptionAttentionCard = false
        XCTAssertThrowsError(
            try subject.inspect().find(actionCard: Localizations.subscriptionNeedsAttention),
        )
    }

    /// The subscription attention action card is visible in the empty vault state.
    @MainActor
    func test_subscriptionAttentionActionCard_visible_emptyVault() {
        processor.state.loadingState = .data([])
        processor.state.shouldShowSubscriptionAttentionCard = true
        XCTAssertNoThrow(
            try subject.inspect().find(actionCard: Localizations.subscriptionNeedsAttention),
        )
    }

    /// The subscription attention action card is visible in the populated vault state.
    @MainActor
    func test_subscriptionAttentionActionCard_visible_populatedVault() {
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [.fixture()], name: "")])
        processor.state.shouldShowSubscriptionAttentionCard = true
        XCTAssertNoThrow(
            try subject.inspect().find(actionCard: Localizations.subscriptionNeedsAttention),
        )
    }

    /// Tapping the "View plan" button on the subscription attention action card dispatches `.viewPlan`.
    @MainActor
    func test_subscriptionAttentionActionCard_tapViewPlan() async throws {
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [.fixture()], name: "")])
        processor.state.shouldShowSubscriptionAttentionCard = true
        let actionCard = try subject.inspect().find(actionCard: Localizations.subscriptionNeedsAttention)
        let button = try actionCard.find(asyncButton: Localizations.viewPlan)
        try await button.tap()
        XCTAssertEqual(processor.dispatchedActions, [.viewPlan])
    }

    /// The import logins action card is hidden when the subscription attention card is showing.
    @MainActor
    func test_importLoginsActionCard_hidden_whenSubscriptionAttentionShowing() {
        processor.state.importLoginsSetupProgress = .incomplete
        processor.state.loadingState = .data([])
        processor.state.shouldShowSubscriptionAttentionCard = true
        XCTAssertThrowsError(
            try subject.inspect().find(actionCard: Localizations.importSavedLogins),
        )
    }

    /// The archive onboarding action card is hidden when the subscription attention card is showing.
    @MainActor
    func test_archiveOnboardingActionCard_hidden_whenSubscriptionAttentionShowing() {
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [.fixture()], name: "")])
        processor.state.shouldShowArchiveOnboardingActionCard = true
        processor.state.shouldShowSubscriptionAttentionCard = true
        XCTAssertThrowsError(
            try subject.inspect().find(actionCard: Localizations.introducingArchive),
        )
    }

    /// The organization banner action card is hidden when `organizationUserNotificationBannerData` is `nil`.
    @MainActor
    func test_orgBannerActionCard_hidden() {
        processor.state.loadingState = .data([])
        XCTAssertThrowsError(try subject.inspect().find(actionCard: "Upcoming Maintenance"))
    }

    /// The organization banner action card is visible when `organizationUserNotificationBannerData` is set.
    @MainActor
    func test_orgBannerActionCard_visible() {
        processor.state.loadingState = .data([])
        processor.state.organizationUserNotificationBannerData = .fixture()
        XCTAssertNoThrow(try subject.inspect().find(actionCard: "Upcoming Maintenance"))
    }

    /// The organization banner action card takes precedence over other action cards, which are
    /// shown once the banner is dismissed.
    @MainActor
    func test_orgBannerActionCard_takesPrecedenceOverOtherActionCards() throws {
        processor.state.loadingState = .data([])
        processor.state.importLoginsSetupProgress = .incomplete
        processor.state.organizationUserNotificationBannerData = .fixture()
        XCTAssertNoThrow(try subject.inspect().find(actionCard: "Upcoming Maintenance"))
        XCTAssertThrowsError(try subject.inspect().find(actionCard: Localizations.importSavedLogins))

        processor.state.organizationUserNotificationBannerData = nil
        XCTAssertThrowsError(try subject.inspect().find(actionCard: "Upcoming Maintenance"))
        XCTAssertNoThrow(try subject.inspect().find(actionCard: Localizations.importSavedLogins))
    }

    /// When the organization banner has a primary button (and a header), the close (X) button is not shown.
    @MainActor
    func test_orgBannerActionCard_primaryButtonHidesCloseButton() throws {
        processor.state.loadingState = .data([])
        processor.state.organizationUserNotificationBannerData = .fixture(
            buttonText: "I understand",
            headerText: "Upcoming Maintenance",
        )
        let actionCard = try subject.inspect().find(actionCard: "Upcoming Maintenance")
        XCTAssertNoThrow(try actionCard.find(asyncButton: "I understand"))
        XCTAssertThrowsError(try actionCard.find(asyncButton: Localizations.dismiss))
    }

    /// Tapping the dismiss button on the organization banner dispatches the
    /// `.dismissOrganizationBanner(fromActionButton: false)` effect.
    @MainActor
    func test_orgBannerActionCard_tapDismiss() async throws {
        processor.state.loadingState = .data([])
        processor.state.organizationUserNotificationBannerData = .fixture(buttonText: nil)
        let actionCard = try subject.inspect().find(actionCard: "Upcoming Maintenance")
        let button = try actionCard.find(asyncButton: Localizations.dismiss)
        try await button.tap()
        XCTAssertEqual(processor.effects, [.dismissOrganizationBanner(fromActionButton: false)])
    }

    /// Tapping the action button on the organization banner dispatches the
    /// `.dismissOrganizationBanner(fromActionButton: true)` effect.
    @MainActor
    func test_orgBannerActionCard_tapActionButton() async throws {
        processor.state.loadingState = .data([])
        processor.state.organizationUserNotificationBannerData = .fixture()
        let actionCard = try subject.inspect().find(actionCard: "Upcoming Maintenance")
        let button = try actionCard.find(asyncButton: "I understand")
        try await button.tap()
        XCTAssertEqual(processor.effects, [.dismissOrganizationBanner(fromActionButton: true)])
    }

    /// Tapping the profile button dispatches the `.requestedProfileSwitcher` effect.
    @MainActor
    func test_profileButton_tap_withProfilesViewNotVisible() async throws {
        processor.state.profileSwitcherState.isVisible = false
        let buttonUnselected = try subject.inspect().find(asyncButton: "AA")
        try await buttonUnselected.tap()
        XCTAssertEqual(
            processor.effects.last,
            .profileSwitcher(.requestedProfileSwitcher(visible: true)),
        )
    }

    /// Tapping the profile button dispatches the `.requestedProfileSwitcher` effect.
    @MainActor
    func test_profileButton_tap_withProfilesViewVisible() async throws {
        processor.state.profileSwitcherState.isVisible = true
        let buttonUnselected = try subject.inspect().find(asyncButton: "AA")
        try await buttonUnselected.tap()

        XCTAssertEqual(
            processor.effects.last,
            .profileSwitcher(.requestedProfileSwitcher(visible: false)),
        )
    }

    /// Tapping the search result dispatches the `.itemPressed` effect.
    @MainActor
    func test_searchResult_tap() async throws {
        let result = VaultListItem.fixture()
        processor.state.searchResults = [result]
        let button = try subject.inspect().find(asyncButton: "Bitwarden")
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .itemPressed(result))
    }

    /// Tapping the go to settings button in the flight recorder toast banner dispatches the
    /// `.navigateToFlightRecorderSettings` action.
    @MainActor
    func test_toastBannerGoToSettings_tap() async throws {
        processor.state.flightRecorderToastBanner.activeLog = FlightRecorderData.LogMetadata(
            duration: .eightHours,
            startDate: Date(year: 2025, month: 4, day: 3),
        )
        let button = try subject.inspect().find(button: Localizations.goToSettings)
        try button.tap()
        XCTAssertEqual(processor.dispatchedActions, [.navigateToFlightRecorderSettings])
    }

    /// Tapping the try again button dispatches the `.tryAgainTapped` action.
    @MainActor
    func test_tryAgainButton_tap() async throws {
        processor.state.loadingState = .error(
            errorMessage: Localizations.weCouldntSyncYourVaultWithTheServerDescriptionLong,
        )
        let button = try subject.inspect().find(asyncButton: Localizations.tryAgain)
        try await button.tap()
        XCTAssertEqual(processor.effects, [.tryAgainTapped])
    }

    /// Tapping the vault item dispatches the `.itemPressed` effect.
    @MainActor
    func test_vaultItem_tap() async throws {
        let item = VaultListItem(id: "1", itemType: .group(.login, 123))
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [item], name: "Group")])
        let button = try subject.inspect().find(asyncButtonWithAccessibilityIdentifier: "VaultListItemRowButton")
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .itemPressed(item))
    }

    /// Tapping the vault item copy totp button dispatches the `.copyTOTPCode` action.
    @MainActor
    func test_vaultItem_copyTOTPButton_tap() throws {
        let item = VaultListItem.fixtureTOTP(totp: .fixture())
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [item], name: "Group")])
        let button = try subject.inspect().find(buttonWithAccessibilityLabel: Localizations.copyTotp)
        try button.tap()
        waitFor(!processor.dispatchedActions.isEmpty)
        XCTAssertEqual(processor.dispatchedActions.last, .copyTOTPCode("123456"))
    }

    /// Tapping the vault item more button dispatches the `.morePressed` action.
    @MainActor
    func test_vaultItem_moreButton_tap() async throws {
        let item = VaultListItem.fixture()
        processor.state.loadingState = .data([VaultListSection(id: "1", items: [item], name: "Group")])
        let button = try subject.inspect().find(asyncButtonWithAccessibilityLabel: Localizations.moreOptions)
        try await button.tap()
        XCTAssertEqual(processor.effects.last, .morePressed(item))
    }

#if DEBUG
    @MainActor
    private func makeHostedLayout(width: CGFloat) -> HostedVaultListLayout {
        let viewportSize = CGSize(width: width, height: 1_000)
        let frameRecorder = VaultListLayoutFrameRecorder()
        let controller = UIHostingController(
            rootView: VaultListLayoutTestHost(subject: subject, frameRecorder: frameRecorder),
        )
        let viewportFrame = CGRect(origin: .zero, size: viewportSize)
        let windowScene = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .first(where: { $0.activationState == .foregroundActive })
        let window: UIWindow
        if let windowScene {
            window = UIWindow(windowScene: windowScene)
        } else {
            window = UIWindow(frame: viewportFrame)
        }
        window.frame = viewportFrame
        window.rootViewController = controller
        window.makeKeyAndVisible()

        controller.view.frame = viewportFrame
        controller.view.setNeedsLayout()
        window.setNeedsLayout()
        window.layoutIfNeeded()
        controller.view.layoutIfNeeded()

        return HostedVaultListLayout(window: window, controller: controller, frameRecorder: frameRecorder)
    }

    @MainActor
    private func removeHostedLayout(_ hostedLayout: HostedVaultListLayout) {
        hostedLayout.window.isHidden = true
        hostedLayout.window.rootViewController = nil
    }
#endif
}

#if DEBUG
@MainActor
private final class VaultListLayoutFrameRecorder {
    var frames: [String: CGRect] = [:]
}

@MainActor
private struct VaultListLayoutTestHost: View {
    let subject: VaultListView
    let frameRecorder: VaultListLayoutFrameRecorder

    var body: some View {
        subject
            .coordinateSpace(name: VaultListLayoutFramePreferenceKey.coordinateSpaceName)
            .onPreferenceChange(VaultListLayoutFramePreferenceKey.self) { frames in
                frameRecorder.frames = frames
            }
            .ignoresSafeArea(.container, edges: .horizontal)
    }
}

@MainActor
private struct HostedVaultListLayout {
    let window: UIWindow
    let controller: UIHostingController<VaultListLayoutTestHost>
    let frameRecorder: VaultListLayoutFrameRecorder
}
#endif
