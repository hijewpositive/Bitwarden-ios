#!/usr/bin/env python3
"""Offline checks for the candidate identity and opt-in Duo simulator path."""

from __future__ import annotations

import argparse
import plistlib
import re
import sys
from pathlib import Path

DEVELOPMENT_TEAM_ASSUMPTION = "NGYQ8H5H97"

EXPECTED = {
    "DEVELOPMENT_TEAM": DEVELOPMENT_TEAM_ASSUMPTION,
    "ORGANIZATION_IDENTIFIER": "com.sputnicity",
    "BASE_BUNDLE_ID": "com.sputnicity.bitwarden-duo",
    "SHARED_APP_GROUP_IDENTIFIER": "group.com.sputnicity.bitwarden-duo.authenticator",
    "BMPW_BUNDLE_DISPLAY_NAME": "Bitwarden-Duo",
    "CODE_SIGNING_ALLOWED": "NO",
    "CODE_SIGNING_REQUIRED": "NO",
}

SIMULATOR_CONFIG = "Configs-fork/Bitwarden-Duo-Simulator.xcconfig"
RELEASE_CONFIG = "Configs-fork/Bitwarden-Duo-Release.xcconfig"
SIMULATOR_OVERRIDE_KEYS = (
    "DEVELOPMENT_TEAM",
    "ORGANIZATION_IDENTIFIER",
    "BASE_BUNDLE_ID",
    "SHARED_APP_GROUP_IDENTIFIER",
    "BMPW_BUNDLE_DISPLAY_NAME",
    "CODE_SIGNING_ALLOWED",
    "CODE_SIGNING_REQUIRED",
    "EXCLUDED_SOURCE_FILE_NAMES",
)
RELEASE_OVERRIDE_KEYS = SIMULATOR_OVERRIDE_KEYS + ("SWIFT_ACTIVE_COMPILATION_CONDITIONS",)

UPSTREAM_TEAM = "LTZ2PFU5D6"
UPSTREAM_ORG = "com.8bit"
UPSTREAM_BUNDLE = "com.8bit.bitwarden"
UPSTREAM_SHARED_GROUP = "group.com.bitwarden.bitwarden-authenticator"
DERIVED_BUNDLE_IDS = (
    ("iOS app", "BASE_BUNDLE_ID", ""),
    ("AutoFill extension", "BASE_BUNDLE_ID", ".autofill"),
    ("Share extension", "BASE_BUNDLE_ID", ".share-extension"),
    ("Action extension", "BASE_BUNDLE_ID", ".find-login-action-extension"),
    ("Notification extension", "BASE_BUNDLE_ID", ".notification"),
    ("Watch app", "BASE_BUNDLE_ID", ".watchkitapp"),
    ("Watch widget extension", "BASE_BUNDLE_ID", ".watchkitapp.widget-extension"),
    ("BitwardenShared framework", "BASE_BUNDLE_ID", ".bitwarden-shared"),
    ("BitwardenKit framework", "ORGANIZATION_IDENTIFIER", ".bitwarden-kit"),
    ("BitwardenResources framework", "ORGANIZATION_IDENTIFIER", ".bitwarden-resources"),
    ("AuthenticatorBridgeKit framework", "ORGANIZATION_IDENTIFIER", ".authenticator-bridge-kit"),
    ("Networking framework", "ORGANIZATION_IDENTIFIER", ".networking"),
)
BUNDLE_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
TEAM_ID_RE = re.compile(r"^[A-Z0-9]{10}$")
PROJECT_TARGET_CONFIGS = {
    "iOS app": ("Configs/Bitwarden-Debug.xcconfig", "Configs/Bitwarden-Release.xcconfig"),
    "AutoFill extension": ("Configs/BitwardenAutoFillExtension.xcconfig",),
    "Share extension": ("Configs/BitwardenShareExtension.xcconfig",),
    "Action extension": ("Configs/BitwardenActionExtension-Debug.xcconfig", "Configs/BitwardenActionExtension-Release.xcconfig"),
    "Notification extension": ("Configs/BitwardenNotificationExtension.xcconfig",),
    "Watch app": ("Configs/BitwardenWatchApp-Debug.xcconfig", "Configs/BitwardenWatchApp-Release.xcconfig"),
    "Watch widget extension": ("Configs/BitwardenWatchWidgetExtension.xcconfig",),
    "BitwardenShared framework": ("Configs/BitwardenShared-Debug.xcconfig", "Configs/BitwardenShared-Release.xcconfig"),
    "BitwardenKit framework": ("Configs/BitwardenKit-Debug.xcconfig", "Configs/BitwardenKit-Release.xcconfig"),
    "BitwardenResources framework": ("Configs/BitwardenResources-Debug.xcconfig", "Configs/BitwardenResources-Release.xcconfig"),
    "AuthenticatorBridgeKit framework": ("Configs/AuthenticatorBridgeKit.xcconfig",),
    "Networking framework": ("Configs/Networking.xcconfig",),
}


def parse_xcconfig(path: Path, active: frozenset[Path] = frozenset()) -> dict[str, str]:
    """Parse the simple assignments and nested includes used by the fork configs."""
    path = path.resolve()
    if path in active:
        raise ValueError(f"cyclic xcconfig include: {path}")
    active = active | {path}
    settings: dict[str, str] = {}
    include_re = re.compile(r'^#include(?P<optional>\?)?\s+"(?P<path>[^"]+)"$')
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        include = include_re.match(line)
        if include:
            included_path = path.parent / include.group("path")
            if included_path.is_file():
                settings.update(parse_xcconfig(included_path, active))
            elif not include.group("optional"):
                raise FileNotFoundError(f"required xcconfig include not found: {included_path}")
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        settings[key.strip()] = value.strip()
    return settings


def candidate_bundle_ids(settings: dict[str, str]) -> dict[str, str]:
    return {
        name: f"{settings.get(prefix, '')}{suffix}"
        for name, prefix, suffix in DERIVED_BUNDLE_IDS
    }


def validate_settings(
    settings: dict[str, str], *, allowed_extra: frozenset[str] = frozenset()
) -> list[str]:
    errors: list[str] = []
    for key, expected in EXPECTED.items():
        if settings.get(key) != expected:
            errors.append(f"{key} must be {expected!r}, got {settings.get(key)!r}")
    for key in settings:
        if key not in EXPECTED and key not in allowed_extra:
            errors.append(f"unreviewed setting is not allowed in this template: {key}")

    team = settings.get("DEVELOPMENT_TEAM", "")
    org = settings.get("ORGANIZATION_IDENTIFIER", "")
    base = settings.get("BASE_BUNDLE_ID", "")
    group = settings.get("SHARED_APP_GROUP_IDENTIFIER", "")
    if not TEAM_ID_RE.fullmatch(team):
        errors.append("DEVELOPMENT_TEAM must be a 10-character Apple team identifier")
    if team == UPSTREAM_TEAM:
        errors.append("Duo must not reuse the upstream Bitwarden development team")
    if not BUNDLE_ID_RE.fullmatch(org) or "." not in org:
        errors.append("ORGANIZATION_IDENTIFIER must be a lowercase reverse-DNS identifier")
    if not BUNDLE_ID_RE.fullmatch(base) or "." not in base:
        errors.append("BASE_BUNDLE_ID must be a lowercase reverse-DNS identifier")
    if org and base and not base.startswith(f"{org}."):
        errors.append("BASE_BUNDLE_ID must be nested under ORGANIZATION_IDENTIFIER")
    if base == UPSTREAM_BUNDLE or base.startswith(f"{UPSTREAM_BUNDLE}."):
        errors.append("Duo bundle identifiers must not reuse the upstream Bitwarden namespace")
    if not group.startswith("group.") or not BUNDLE_ID_RE.fullmatch(group):
        errors.append("SHARED_APP_GROUP_IDENTIFIER must be a valid group.<reverse-DNS> identifier")
    main_app_group = f"group.{base}"
    if main_app_group == UPSTREAM_SHARED_GROUP or main_app_group == f"group.{UPSTREAM_BUNDLE}":
        errors.append("the derived main app group must not reuse an upstream app-group identifier")
    if group != f"group.{base}.authenticator":
        errors.append("SHARED_APP_GROUP_IDENTIFIER must be the isolated Duo authenticator group")
    bundle_ids = candidate_bundle_ids(settings)
    values = list(bundle_ids.values())
    if len(values) != len(set(values)):
        errors.append("derived app, extension, watch, and framework bundle identifiers must be unique")
    for label, bundle_id in bundle_ids.items():
        if not BUNDLE_ID_RE.fullmatch(bundle_id) or "." not in bundle_id:
            errors.append(f"{label} has an invalid derived bundle identifier: {bundle_id!r}")
        if bundle_id == UPSTREAM_BUNDLE or bundle_id.startswith(f"{UPSTREAM_BUNDLE}."):
            errors.append(f"{label} collides with the upstream Bitwarden bundle namespace")

    # The example must remain non-signing and must not carry profiles/certificates.
    signing_keys = ("CODE_SIGN_IDENTITY", "PROVISIONING_PROFILE", "PROVISIONING_PROFILE_SPECIFIER")
    for key in settings:
        if any(key.startswith(prefix) for prefix in signing_keys):
            errors.append(f"signing credential/profile setting is not allowed in this template: {key}")
    if settings.get("CODE_SIGNING_ALLOWED") != "NO" or settings.get("CODE_SIGNING_REQUIRED") != "NO":
        errors.append("the template must explicitly disable code signing")
    return errors


def project_config_errors(root: Path, settings: dict[str, str]) -> list[str]:
    """Check the audited target configs still derive the expected product IDs."""
    errors: list[str] = []
    expected_ids = candidate_bundle_ids(settings)
    substitutions = {
        "BASE_BUNDLE_ID": settings.get("BASE_BUNDLE_ID", ""),
        "ORGANIZATION_IDENTIFIER": settings.get("ORGANIZATION_IDENTIFIER", ""),
        "BASE_WATCH_BUNDLE_ID": f"{settings.get('BASE_BUNDLE_ID', '')}.watchkitapp",
    }
    for target_name, config_paths in PROJECT_TARGET_CONFIGS.items():
        project_file = "project-bwk.yml" if target_name in {
            "BitwardenKit framework",
            "BitwardenResources framework",
            "AuthenticatorBridgeKit framework",
            "Networking framework",
        } else "project-pm.yml"
        project_text = (root / project_file).read_text(encoding="utf-8")
        for relative_path in config_paths:
            config_path = root / relative_path
            if not config_path.is_file():
                errors.append(f"missing target configuration: {relative_path}")
                continue
            if relative_path not in project_text:
                errors.append(f"{relative_path} is not referenced by {project_file}")
                continue
            raw_id = parse_xcconfig(config_path).get("PRODUCT_BUNDLE_IDENTIFIER")
            if raw_id is None:
                errors.append(f"{relative_path} does not set PRODUCT_BUNDLE_IDENTIFIER")
                continue
            resolved_id = re.sub(
                r"\$\(([^)]+)\)",
                lambda match: substitutions.get(match.group(1), match.group(0)),
                raw_id,
            )
            if resolved_id != expected_ids[target_name]:
                errors.append(
                    f"{relative_path} derives {resolved_id!r}, expected {expected_ids[target_name]!r}"
                )
    return errors


def _read_plist(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            value = plistlib.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, plistlib.InvalidFileException):
        return {}


def identity_entitlement_errors(root: Path) -> list[str]:
    """Ensure the fork config preserves, rather than rewrites, app-group/keychain macros."""
    errors: list[str] = []
    app = _read_plist(root / "Bitwarden/Application/Support/Bitwarden.entitlements")
    expected_app_groups = {
        "group.$(BASE_BUNDLE_ID)",
        "$(SHARED_APP_GROUP_IDENTIFIER)",
    }
    app_groups = set(app.get("com.apple.security.application-groups", []))
    if app_groups != expected_app_groups:
        errors.append(f"main app app-group entitlements changed unexpectedly: {sorted(app_groups)!r}")
    expected_keychain = "$(AppIdentifierPrefix)$(BASE_BUNDLE_ID)"
    for name, relative_path in (
        ("AutoFill extension", "BitwardenAutoFillExtension/Application/Support/BitwardenAutoFill.entitlements"),
        ("Share extension", "BitwardenShareExtension/Application/Support/BitwardenShareExtension.entitlements"),
    ):
        entitlements = _read_plist(root / relative_path)
        groups = entitlements.get("com.apple.security.application-groups", [])
        if groups != ["group.$(BASE_BUNDLE_ID)"]:
            errors.append(f"{name} must retain its existing main-app group derivation")
        keychain = entitlements.get("keychain-access-groups", [])
        if keychain != [expected_keychain]:
            errors.append(f"{name} must retain the existing app-identifier keychain group")
    if app.get("keychain-access-groups") != [expected_keychain]:
        errors.append("main app must retain the existing app-identifier keychain group")
    return errors


def simulator_config_errors(root: Path) -> tuple[dict[str, str], list[str]]:
    """Validate the explicit Debug-only, non-signing simulator override."""
    errors: list[str] = []
    config_path = root / SIMULATOR_CONFIG
    if not config_path.is_file():
        return {}, [f"missing simulator override: {SIMULATOR_CONFIG}"]
    try:
        settings = parse_xcconfig(config_path)
    except (OSError, ValueError, FileNotFoundError) as error:
        return {}, [f"could not parse simulator override: {error}"]
    errors.extend(validate_settings(settings, allowed_extra=frozenset({"EXCLUDED_SOURCE_FILE_NAMES"})))
    if settings.get("EXCLUDED_SOURCE_FILE_NAMES") != "GoogleService-Info.plist":
        errors.append("simulator override must exclude upstream GoogleService-Info.plist resources")
    for project_spec in ("project-pm.yml", "project-bwk.yml"):
        project_text = (root / project_spec).read_text(encoding="utf-8")
        if SIMULATOR_CONFIG in project_text or "Configs-fork/" in project_text:
            errors.append(f"fork simulator settings must not be wired into standard XcodeGen spec {project_spec}")
    errors.extend(project_config_errors(root, settings))
    errors.extend(identity_entitlement_errors(root))

    factory = (root / "Bitwarden/Application/Services/ErrorReporter/ErrorReporterFactory.swift").read_text(
        encoding="utf-8"
    )
    if not re.search(
        r"#if\s+DEBUG\s*\|\|\s*BITWARDEN_DUO_DISABLE_FIREBASE.*?OSLogErrorReporter\(\).*?#else.*?CrashlyticsErrorReporter\.shared.*?#endif",
        factory,
        re.DOTALL,
    ):
        errors.append("Debug app path must continue to select OSLogErrorReporter instead of Crashlytics")
    watch_delegate = (root / "BitwardenWatchApp/ExtensionDelegate.swift").read_text(encoding="utf-8")
    if not re.search(r"#if\s+!DEBUG\s*&&\s*!BITWARDEN_DUO_DISABLE_FIREBASE.*?FirebaseApp\.configure\(\).*?#endif", watch_delegate, re.DOTALL):
        errors.append("Watch Firebase configuration must remain excluded from Debug builds")
    return settings, errors


def release_config_errors(root: Path) -> tuple[dict[str, str], list[str]]:
    """Validate the explicit, unsigned Release configuration that disables Firebase."""
    errors: list[str] = []
    config_path = root / RELEASE_CONFIG
    if not config_path.is_file():
        return {}, [f"missing Release Firebase isolation override: {RELEASE_CONFIG}"]
    try:
        settings = parse_xcconfig(config_path)
    except (OSError, ValueError, FileNotFoundError) as error:
        return {}, [f"could not parse Release Firebase isolation override: {error}"]

    errors.extend(
        validate_settings(
            settings,
            allowed_extra=frozenset({"EXCLUDED_SOURCE_FILE_NAMES", "SWIFT_ACTIVE_COMPILATION_CONDITIONS"}),
        )
    )
    if settings.get("EXCLUDED_SOURCE_FILE_NAMES") != "GoogleService-Info.plist":
        errors.append("Release override must exclude upstream GoogleService-Info.plist resources")
    if settings.get("SWIFT_ACTIVE_COMPILATION_CONDITIONS") != "$(inherited) BITWARDEN_DUO_DISABLE_FIREBASE":
        errors.append("Release override must inherit Swift conditions and define BITWARDEN_DUO_DISABLE_FIREBASE")
    for project_spec in ("project-pm.yml", "project-bwk.yml"):
        project_text = (root / project_spec).read_text(encoding="utf-8")
        if RELEASE_CONFIG in project_text or "Configs-fork/" in project_text:
            errors.append(f"fork Release settings must not be wired into standard XcodeGen spec {project_spec}")

    factory = (root / "Bitwarden/Application/Services/ErrorReporter/ErrorReporterFactory.swift").read_text(
        encoding="utf-8"
    )
    if not re.search(
        r"#if\s+DEBUG\s*\|\|\s*BITWARDEN_DUO_DISABLE_FIREBASE.*?OSLogErrorReporter\(\).*?#else.*?CrashlyticsErrorReporter\.shared.*?#endif",
        factory,
        re.DOTALL,
    ):
        errors.append("Release fork path must select OSLogErrorReporter instead of Crashlytics")
    reporter = (root / "Bitwarden/Application/Services/ErrorReporter/CrashlyticsErrorReporter.swift").read_text(
        encoding="utf-8"
    )
    if not re.match(r"\s*#if\s+!BITWARDEN_DUO_DISABLE_FIREBASE\b", reporter) or not reporter.rstrip().endswith("#endif"):
        errors.append("Crashlytics reporter implementation must be compiled out for the Duo Release condition")
    watch_delegate = (root / "BitwardenWatchApp/ExtensionDelegate.swift").read_text(encoding="utf-8")
    if not re.search(
        r"#if\s+!DEBUG\s*&&\s*!BITWARDEN_DUO_DISABLE_FIREBASE.*?FirebaseApp\.configure\(\).*?#endif",
        watch_delegate,
        re.DOTALL,
    ):
        errors.append("Release Watch path must not configure Firebase when Duo isolation is enabled")
    return settings, errors


def simulator_xcodebuild_overrides(settings: dict[str, str]) -> list[str]:
    return [f"{key}={settings[key]}" for key in SIMULATOR_OVERRIDE_KEYS]


def release_xcodebuild_overrides(settings: dict[str, str]) -> list[str]:
    return [f"{key}={settings[key]}" for key in RELEASE_OVERRIDE_KEYS]


def scan_blockers(root: Path) -> list[tuple[str, str]]:
    blockers: list[tuple[str, str]] = []
    project_yml = (root / "project-pm.yml").read_text(encoding="utf-8")
    if "Configs-fork/" not in project_yml:
        blockers.append(("FORK_BUILD_INTEGRATION", "No dedicated Duo Release/archive/TestFlight target is wired into XcodeGen. The opt-in unsigned Debug/Release simulator path uses an external -xcconfig override and leaves the standard project untouched."))

    auth_service = (root / "BitwardenShared/Core/Auth/Services/AuthService.swift").read_text(encoding="utf-8")
    app_info = _read_plist(root / "Bitwarden/Application/Support/Info.plist")
    url_schemes = {
        scheme
        for url_type in app_info.get("CFBundleURLTypes", [])
        for scheme in url_type.get("CFBundleURLSchemes", [])
    }
    if 'callbackUrlScheme = "bitwarden"' in auth_service or "bitwarden" in url_schemes:
        blockers.append(("CALLBACKS", "The auth callback still uses the shared `bitwarden` URL scheme; fork-specific login/Duo/SSO/WebAuthn callbacks need code, plist, and server-side validation."))
    if "otpauth" in url_schemes:
        blockers.append(("GENERIC_URL_SCHEME", "The app also registers generic `otpauth`; decide whether the fork should claim this handler when upstream is installed."))

    app_entitlements = _read_plist(root / "Bitwarden/Application/Support/Bitwarden.entitlements")
    associated = app_entitlements.get("com.apple.developer.associated-domains", [])
    if any("bitwarden." in value or "bitwarden-gov.com" in value for value in associated):
        blockers.append(("ASSOCIATED_DOMAINS", "The shipping entitlements point at Bitwarden-owned universal-link/web-credential domains; a Duo app needs authorized AASA coverage or a reviewed domain policy."))

    _, release_firebase_errors = release_config_errors(root)
    if release_firebase_errors:
        blockers.append(("FIREBASE", "Release Firebase isolation is missing or invalid: " + "; ".join(release_firebase_errors)))

    watch_helper = (root / "BitwardenWatchApp/Helpers/KeychainHelper.swift").read_text(encoding="utf-8")
    if UPSTREAM_BUNDLE in watch_helper:
        blockers.append(("WATCH_KEYCHAIN_SERVICE", "The Watch generic-password service remains hard-coded to the upstream namespace; review and parameterize it before shipping. Its service label alone does not prove cross-app keychain sharing."))

    action_info = _read_plist(root / "BitwardenActionExtension/Application/Support/Info.plist")
    action_rule = action_info.get("NSExtension", {}).get("NSExtensionAttributes", {}).get("NSExtensionActivationRule", "")
    if "com.8bit.bitwarden.extension-setup" in action_rule:
        blockers.append(("EXTENSION_UTI", "The action-extension setup UTI remains upstream-namespaced; fork-specific app/extension protocol identifiers need review."))

    fastfile = (root / "fastlane/Fastfile").read_text(encoding="utf-8")
    appfile = (root / "fastlane/Appfile").read_text(encoding="utf-8")
    selector = (root / "Scripts/select_variant.sh").read_text(encoding="utf-8")
    if UPSTREAM_TEAM in fastfile and UPSTREAM_TEAM in selector and UPSTREAM_BUNDLE in appfile:
        blockers.append(("BUILD_AUTOMATION", "Fastlane and variant scripts contain upstream team/organization/profile defaults and write local release/export settings; do not use them for Duo without a fork-only reviewed path."))

    compliance = _read_plist(root / "Bitwarden/Application/Support/Info.plist")
    if compliance.get("ITSAppUsesNonExemptEncryption") is True and "ITSEncryptionExportComplianceCode" in compliance:
        blockers.append(("EXPORT_COMPLIANCE", "The upstream app plist declares non-exempt encryption and an export-compliance code; the Duo owner must independently confirm the correct filing/status before distribution."))

    blockers.append(("REGISTRATION_AND_SIGNING", "Offline checks cannot verify Duo App Store Connect record, App ID/capability registration, app groups, provisioning profiles, or signing readiness; none were created or queried here."))
    return blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--check-simulator-config",
        action="store_true",
        help="validate the opt-in unsigned Debug simulator configuration only",
    )
    parser.add_argument(
        "--emit-xcodebuild-overrides",
        action="store_true",
        help="print validated identity overrides, one KEY=VALUE per line",
    )
    parser.add_argument(
        "--check-release-config",
        action="store_true",
        help="validate the opt-in unsigned Release simulator Firebase isolation config",
    )
    parser.add_argument(
        "--emit-release-xcodebuild-overrides",
        action="store_true",
        help="print validated Release simulator overrides, one KEY=VALUE per line",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    simulator_settings, simulator_errors = simulator_config_errors(root)
    release_settings, release_errors = release_config_errors(root)
    if args.check_release_config or args.emit_release_xcodebuild_overrides:
        if release_errors:
            for error in release_errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        if args.emit_release_xcodebuild_overrides:
            print("\n".join(release_xcodebuild_overrides(release_settings)))
        else:
            print("PASS: Release app and Watch Firebase configuration is disabled for Duo")
            print("PASS: upstream GoogleService-Info.plist resources are excluded")
            print("PASS: Crashlytics code is compiled out and OSLog remains the app error reporter")
            print("PASS: Release override is opt-in and excluded from standard XcodeGen specs")
        return 0
    if args.check_simulator_config or args.emit_xcodebuild_overrides:
        if simulator_errors:
            for error in simulator_errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        if args.emit_xcodebuild_overrides:
            print("\n".join(simulator_xcodebuild_overrides(simulator_settings)))
        else:
            print("PASS: isolated candidate bundle IDs resolve across the PM/Kit target config matrix")
            print("PASS: shared app-group and keychain entitlements retain their existing derived forms")
            print("PASS: signing is disabled and upstream Firebase plist resources are excluded")
            print("PASS: Debug app/Watch code paths do not configure Firebase")
            print("PASS: override is opt-in and not included by the standard XcodeGen project")
            print(
                f"ASSUMPTION: DEVELOPMENT_TEAM={DEVELOPMENT_TEAM_ASSUMPTION} is verified for Sonarr only; "
                "confirm it for Bitwarden-Duo before using it."
            )
        return 0

    config_path = root / "Configs-fork/Bitwarden-Duo.xcconfig.example"
    try:
        settings = parse_xcconfig(config_path)
    except (OSError, ValueError, FileNotFoundError) as error:
        print(f"ERROR: could not parse identity template: {error}")
        return 1
    errors = validate_settings(settings)
    errors.extend(project_config_errors(root, settings))
    errors.extend(simulator_errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    ids = candidate_bundle_ids(settings)
    print(f"PASS: candidate identity syntax and isolation checks ({len(ids)} derived bundle IDs)")
    print("PASS: current PM/Kit target configs resolve to the candidate bundle-ID matrix")
    print("PASS: code signing is disabled; no certificate/profile settings are present")
    print("PASS: explicit Debug simulator override is opt-in and Firebase-fail-closed")
    if not release_errors:
        print("PASS: explicit Release override excludes upstream Firebase config and disables Crashlytics")
    print(
        f"ASSUMPTION: DEVELOPMENT_TEAM={DEVELOPMENT_TEAM_ASSUMPTION} is verified for Sonarr only; "
        "confirm it for Bitwarden-Duo before using it."
    )
    for name, bundle_id in ids.items():
        print(f"  {name}: {bundle_id}")

    blockers = scan_blockers(root)
    for code, text in blockers:
        print(f"BLOCKER [{code}]: {text}")
    print(f"NOT TESTFLIGHT-READY: {len(blockers)} unresolved blocker(s); offline audit only.")
    return 2 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
