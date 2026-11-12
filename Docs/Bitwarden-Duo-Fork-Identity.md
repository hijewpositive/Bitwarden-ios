# Bitwarden-Duo fork identity and unsigned simulator path

This adds an **opt-in, Debug-only iOS Simulator identity path** for the Bitwarden-Duo fork. It does not change the shipping `project-pm.yml`, `Configs/`, entitlements, auth flow, service endpoints, or any Apple account. `Configs-fork/Bitwarden-Duo-Simulator.xcconfig` is supplied explicitly to the fork helper; the standard XcodeGen project never includes it.

## Candidate identity matrix

These values are proposals carried forward from the identity audit, **not proof of Apple registration, team ownership, or availability**. The proposed team `NGYQ8H5H97` is verified for Sonarr only; using it for Bitwarden-Duo is an assumption pending Simon's confirmation. The local development identity `4WW5494JT3` is distinct and is not the App Store Connect team candidate. The helper disables signing, so the team value is informational for this simulator configuration.

| Target | Candidate bundle identifier |
| --- | --- |
| iOS app | `com.sputnicity.bitwarden-duo` |
| AutoFill extension | `com.sputnicity.bitwarden-duo.autofill` |
| Share extension | `com.sputnicity.bitwarden-duo.share-extension` |
| Action extension | `com.sputnicity.bitwarden-duo.find-login-action-extension` |
| Notification extension | `com.sputnicity.bitwarden-duo.notification` |
| Watch app | `com.sputnicity.bitwarden-duo.watchkitapp` |
| Watch widget extension | `com.sputnicity.bitwarden-duo.watchkitapp.widget-extension` |
| BitwardenShared framework | `com.sputnicity.bitwarden-duo.bitwarden-shared` |
| BitwardenKit framework | `com.sputnicity.bitwarden-kit` |
| BitwardenResources framework | `com.sputnicity.bitwarden-resources` |
| AuthenticatorBridgeKit framework | `com.sputnicity.authenticator-bridge-kit` |
| Networking framework | `com.sputnicity.networking` |

The team assumption is based on Sonarr-specific evidence: Sonarr's `testflight-20261112T0126Z` archive `Verify/profile.plist` and `DistributionSummary.plist` independently confirm signed team `NGYQ8H5H97`; the same App Store Connect key's app lookup and related profile also identify that team. This establishes the provider team for Sonarr, **not** Bitwarden-Duo's ownership, app-record association, or authorization to use it. Confirm the team choice for Bitwarden-Duo with Simon before signing or distribution. The local development identity `4WW5494JT3` is separate and does not override this unconfirmed assumption.

The app/extension/watch and framework values are derived from the existing PM/Kit target xcconfigs using candidate organization `com.sputnicity` and app ID `com.sputnicity.bitwarden-duo`. The candidate team assumption is `NGYQ8H5H97`; the authenticator-sharing group is `group.com.sputnicity.bitwarden-duo.authenticator`; the main app/extension group remains derived as `group.<BASE_BUNDLE_ID>`. Existing keychain access groups remain derived from `$(AppIdentifierPrefix)$(BASE_BUNDLE_ID)`. None of these values creates or proves an App ID, group, capability, or keychain entitlement registration.

The main app display name setting is `Bitwarden-Duo`. No extension/watch icon or display-name assets were changed.

## Build invocation

On a Mac with the repository's generated workspace/projects and already-cached local dependencies/tools, run from an isolated work copy/snapshot (normal build phases may refresh generated source files). The helper enforces the repository pin in `.xcode-version` (currently `27.0`) by default. To deliberately accept a different selected Xcode, set `BITWARDEN_DUO_ALLOW_XCODE_VERSION` to the exact version reported by `xcrun xcodebuild -version`; for example, to accept `27.2`:

```sh
BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2" \
BITWARDEN_DUO_MINT_BIN_DIR="$HOME/.mint/bin" \
BITWARDEN_DUO_SOURCE_PACKAGES="/path/to/existing/SourcePackages" \
Scripts-fork/build_bitwarden_duo_simulator.sh
```

Omit the version override when using the pinned Xcode. The override only acknowledges that exact version; it does not change the repository pin or certify Xcode compatibility.

The helper:

- For a fresh DerivedData path, the helper requires at least 28 GiB free. Reusing an existing cache requires the explicit `BITWARDEN_DUO_REUSE_DERIVED_DATA=YES` opt-in and an existing directory, and keeps a hard 5 GiB minimum-free-space guard. Both modes refuse to start while another `xcodebuild` is active;
- resolves cache/output paths before use, rejects DerivedData paths that resolve into the source repository, rejects existing output unless explicit reuse is enabled, and checks free space on the actual output volume;
- requires the generated workspace projects and all already-present Swift package checkouts, plus cached `license-plist`, `sourcery`, and `swiftgen` binaries;
- uses a local-only `Scripts-fork/mint` dispatcher restricted to those cached build tools, `-disableAutomaticPackageResolution`, and `-skipPackageUpdates`; it does not run Mint installs or SwiftPM resolve/update commands;
- checks the Xcode selected through `xcrun` (the same tool used for the build). A non-pinned version fails by default; an explicit exact-version opt-in is required to proceed;
- builds the `Bitwarden` scheme in `Debug` for generic iOS Simulator. Identity, signing-off, and Firebase-resource-exclusion settings are emitted as `xcodebuild` command-line build-setting overrides as well as supplied by the opt-in xcconfig, so target xcconfig values cannot silently replace them;
- limits the build to one job and sets the active Mac architecture explicitly (`ARCHS=<uname -m> ONLY_ACTIVE_ARCH=YES`). Existing DerivedData is never reused unless the explicit reuse flag is set, and the caller remains responsible for monitoring free space during the build;
- writes DerivedData outside the repository, then recursively checks the app bundle—including its embedded Watch app—for any `GoogleService-Info.plist` before reporting success.

It does **not** install or launch the app, archive, sign, access a portal/API, or upload anything. A successful compile is not proof that unsigned app-group/keychain behavior works in Simulator.

The simulator override excludes upstream Firebase plist resources. The app's Debug `ErrorReporterFactory` selects `OSLogErrorReporter`, and the Watch delegate calls `FirebaseApp.configure()` only outside `DEBUG`. The validator checks those source guards and the config exclusion; the build helper additionally scans the produced app recursively, including the embedded Watch bundle, before reporting success. Do not use Release/TestFlight settings: they still include upstream Firebase integration and remain blocked pending Duo-owned Firebase config or an explicitly reviewed removal.

The wrapper avoids its own dependency-network paths by requiring cached Swift packages/tools, disabling automatic package resolution, skipping package updates, and intercepting Mint with a local dispatcher. It is **not** an OS-level network sandbox; if zero outbound traffic is mandatory, the Mac must separately be run with network access blocked.

## Remaining integration/distribution blockers

- Authentication callbacks still use shared `bitwarden` and generic `otpauth` schemes; callback and server redirect behavior must be designed and tested before installing both apps.
- Existing associated domains point to Bitwarden-owned domains; no fork AASA/credential authorization is established.
- Release Firebase config, Watch keychain service label, and Action extension UTI remain upstream-specific and are not changed by the simulator config.
- Upstream Fastlane/variant automation, export-compliance metadata, extension/watch branding, App Store Connect record, team ownership, app-group registration, capabilities, provisioning, signing, and TestFlight processing remain unverified.

For a deliberate incremental continuation with an existing task-owned cache, pass all paths explicitly:

```sh
BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2" \
BITWARDEN_DUO_REUSE_DERIVED_DATA="YES" \
BITWARDEN_DUO_DERIVED_DATA="$HOME/agent-builds/<task>/DerivedData" \
BITWARDEN_DUO_MINT_BIN_DIR="$HOME/agent-builds/<task>/.mint/bin" \
BITWARDEN_DUO_SOURCE_PACKAGES="$HOME/agent-builds/<task>/DerivedData/SourcePackages" \
Scripts-fork/build_bitwarden_duo_simulator.sh
```

Only use the reuse mode for task-owned DerivedData and continue monitoring the destination volume; stop only the build process group started for that task if free space reaches the authorized floor.

## Offline checks

```sh
python3 Scripts-fork/test_bitwarden_duo_identity.py
python3 Scripts-fork/validate_bitwarden_duo_identity.py --check-simulator-config
python3 Scripts-fork/validate_bitwarden_duo_identity.py --emit-xcodebuild-overrides
python3 Scripts-fork/validate_bitwarden_duo_identity.py
```

The offline tests exercise the build wrapper with fake `xcrun`/`xcodebuild`/disk/process commands and synthetic app/watch bundle paths. They verify version and disk gates, explicit cache reuse, one-job argument forwarding, path handling, local Mint dispatch, and the recursive Firebase fail-closed check; they do **not** run Xcode, verify effective Xcode build settings, or prove a compiled product is usable.

The repository pin remains `27.0`; any other selected Xcode requires an exact-version opt-in (illustrated with `27.2` above). No signing, provisioning, or distribution readiness is established. An unsigned simulator build does not prove app-group/keychain registration or runtime behavior.
