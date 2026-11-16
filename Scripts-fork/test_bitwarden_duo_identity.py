"""Offline regression tests for the Duo identity and simulator build helper."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_bitwarden_duo_identity as validator  # noqa: E402


class BitwardenDuoIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = validator.parse_xcconfig(ROOT / "Configs-fork/Bitwarden-Duo.xcconfig.example")

    def test_candidate_identity_is_valid_and_isolated(self) -> None:
        self.assertEqual(validator.validate_settings(self.settings), [])
        self.assertEqual(validator.project_config_errors(ROOT, self.settings), [])
        self.assertEqual(
            self.settings["DEVELOPMENT_TEAM"], validator.DEVELOPMENT_TEAM_ASSUMPTION
        )
        ids = validator.candidate_bundle_ids(self.settings)
        self.assertEqual(len(ids), len(set(ids.values())))
        self.assertEqual(ids["iOS app"], "com.sputnicity.bitwarden-duo")
        self.assertEqual(ids["Watch app"], "com.sputnicity.bitwarden-duo.watchkitapp")
        self.assertEqual(ids["Watch widget extension"], "com.sputnicity.bitwarden-duo.watchkitapp.widget-extension")
        self.assertEqual(ids["AutoFill extension"], "com.sputnicity.bitwarden-duo.autofill")
        self.assertEqual(ids["Share extension"], "com.sputnicity.bitwarden-duo.share-extension")
        self.assertEqual(ids["Action extension"], "com.sputnicity.bitwarden-duo.find-login-action-extension")
        self.assertEqual(ids["Notification extension"], "com.sputnicity.bitwarden-duo.notification")
        self.assertEqual(ids["BitwardenShared framework"], "com.sputnicity.bitwarden-duo.bitwarden-shared")
        self.assertEqual(ids["BitwardenKit framework"], "com.sputnicity.bitwarden-kit")
        self.assertEqual(ids["BitwardenResources framework"], "com.sputnicity.bitwarden-resources")
        self.assertEqual(ids["AuthenticatorBridgeKit framework"], "com.sputnicity.authenticator-bridge-kit")
        self.assertEqual(ids["Networking framework"], "com.sputnicity.networking")

    def test_team_candidate_is_explicitly_an_unconfirmed_sonarr_assumption(self) -> None:
        config = (ROOT / "Configs-fork/Bitwarden-Duo.xcconfig.example").read_text(encoding="utf-8")
        docs = (ROOT / "Docs/Bitwarden-Duo-Fork-Identity.md").read_text(encoding="utf-8")
        self.assertIn("NGYQ8H5H97", config)
        self.assertIn("pending Simon's confirmation", config)
        self.assertIn("verified for Sonarr only", docs)
        self.assertIn("pending Simon's confirmation", docs)
        self.assertIn("4WW5494JT3", docs)

    def test_validator_does_not_claim_duo_team_is_sonarr_only(self) -> None:
        run = subprocess.run([sys.executable, str(SCRIPT_DIR / "validate_bitwarden_duo_identity.py"), "--check-simulator-config"], text=True, capture_output=True, check=True)
        self.assertNotIn("verified for Sonarr only", run.stdout)
        self.assertIn("not live verification", run.stdout)

    def test_simulator_override_is_explicit_unsigned_and_fail_closed(self) -> None:
        settings, errors = validator.simulator_config_errors(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(settings["BASE_BUNDLE_ID"], "com.sputnicity.bitwarden-duo")
        self.assertEqual(settings["SHARED_APP_GROUP_IDENTIFIER"], "group.com.sputnicity.bitwarden-duo.authenticator")
        self.assertEqual(settings["BMPW_BUNDLE_DISPLAY_NAME"], "Bitwarden-Duo")
        self.assertEqual(settings["EXCLUDED_SOURCE_FILE_NAMES"], "GoogleService-Info.plist")
        overrides = validator.simulator_xcodebuild_overrides(settings)
        self.assertIn("CODE_SIGNING_ALLOWED=NO", overrides)
        self.assertIn("CODE_SIGNING_REQUIRED=NO", overrides)
        self.assertIn("DEVELOPMENT_TEAM=NGYQ8H5H97", overrides)
        self.assertIn("EXCLUDED_SOURCE_FILE_NAMES=GoogleService-Info.plist", overrides)
        self.assertNotIn("PROVISIONING_PROFILE_SPECIFIER=", "\n".join(overrides))

    def test_archive_config_sets_verified_fork_keychain_prefix_without_wiring_upstream(self) -> None:
        settings = validator.parse_xcconfig(ROOT / "Configs-fork/Bitwarden-Duo-Archive.xcconfig")
        self.assertEqual(settings["DEVELOPMENT_TEAM"], "NGYQ8H5H97")
        self.assertEqual(settings["AppIdentifierPrefix"], "NGYQ8H5H97.")
        self.assertEqual(settings["CODE_SIGNING_ALLOWED"], "NO")
        for project in ("project-pm.yml", "project-bwk.yml"):
            self.assertNotIn("Configs-fork/Bitwarden-Duo-Archive.xcconfig", (ROOT / project).read_text())

    def test_release_override_is_fork_only_and_disables_firebase_fail_closed(self) -> None:
        settings, errors = validator.release_config_errors(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(settings["BASE_BUNDLE_ID"], "com.sputnicity.bitwarden-duo")
        self.assertEqual(settings["EXCLUDED_SOURCE_FILE_NAMES"], "GoogleService-Info.plist")
        self.assertIn("BITWARDEN_DUO_DISABLE_FIREBASE", settings["SWIFT_ACTIVE_COMPILATION_CONDITIONS"])
        overrides = validator.release_xcodebuild_overrides(settings)
        self.assertIn("EXCLUDED_SOURCE_FILE_NAMES=GoogleService-Info.plist", overrides)
        self.assertTrue(any(item.startswith("SWIFT_ACTIVE_COMPILATION_CONDITIONS=") and "BITWARDEN_DUO_DISABLE_FIREBASE" in item for item in overrides))
        project_spec = (ROOT / "project-pm.yml").read_text(encoding="utf-8")
        self.assertNotIn("Configs-fork/", project_spec)
        upstream_release = (ROOT / "Configs/Bitwarden-Release.xcconfig").read_text(encoding="utf-8")
        self.assertIn("FIREBASE_CONFIG_FILENAME = GoogleService-Info.plist", upstream_release)
        self.assertNotIn("BITWARDEN_DUO_DISABLE_FIREBASE", upstream_release)

    def test_release_override_rejects_missing_firebase_exclusion_or_compile_guard(self) -> None:
        config = ROOT / validator.RELEASE_CONFIG
        original = config.read_text(encoding="utf-8")
        try:
            config.write_text(
                original.replace(
                    "EXCLUDED_SOURCE_FILE_NAMES = GoogleService-Info.plist",
                    "EXCLUDED_SOURCE_FILE_NAMES =",
                ),
                encoding="utf-8",
            )
            _, errors = validator.release_config_errors(ROOT)
            self.assertTrue(any("GoogleService-Info.plist" in error for error in errors), errors)
            self.assertIn("FIREBASE", {code for code, _ in validator.scan_blockers(ROOT)})
            config.write_text(original.replace("BITWARDEN_DUO_DISABLE_FIREBASE", "BITWARDEN_DUO_FIREBASE"), encoding="utf-8")
            _, errors = validator.release_config_errors(ROOT)
            self.assertTrue(any("BITWARDEN_DUO_DISABLE_FIREBASE" in error for error in errors), errors)
        finally:
            config.write_text(original, encoding="utf-8")

    def test_release_config_fails_closed_when_source_guards_regress(self) -> None:
        regressions = (
            (
                ROOT / "Bitwarden/Application/Services/ErrorReporter/ErrorReporterFactory.swift",
                "#if DEBUG || BITWARDEN_DUO_DISABLE_FIREBASE",
                "#if DEBUG",
            ),
            (
                ROOT / "Bitwarden/Application/Services/ErrorReporter/CrashlyticsErrorReporter.swift",
                "#if !BITWARDEN_DUO_DISABLE_FIREBASE",
                "#if DEBUG",
            ),
            (
                ROOT / "BitwardenWatchApp/ExtensionDelegate.swift",
                "#if !DEBUG && !BITWARDEN_DUO_DISABLE_FIREBASE",
                "#if !DEBUG",
            ),
        )
        for source, old_guard, replacement in regressions:
            original = source.read_text(encoding="utf-8")
            try:
                self.assertIn(old_guard, original)
                source.write_text(original.replace(old_guard, replacement), encoding="utf-8")
                _, errors = validator.release_config_errors(ROOT)
                self.assertTrue(errors, f"validator accepted Firebase guard regression in {source}")
            finally:
                source.write_text(original, encoding="utf-8")

    def test_app_group_and_keychain_entitlements_remain_derived(self) -> None:
        self.assertEqual(validator.identity_entitlement_errors(ROOT), [])
        app = validator._read_plist(ROOT / "Bitwarden/Application/Support/Bitwarden.entitlements")
        self.assertEqual(
            set(app["com.apple.security.application-groups"]),
            {"group.$(BASE_BUNDLE_ID)", "$(SHARED_APP_GROUP_IDENTIFIER)"},
        )
        self.assertEqual(
            app["keychain-access-groups"],
            ["$(AppIdentifierPrefix)$(BASE_BUNDLE_ID)"],
        )

    def test_upstream_id_group_and_signed_config_are_rejected(self) -> None:
        upstream = dict(self.settings, BASE_BUNDLE_ID="com.8bit.bitwarden")
        self.assertTrue(validator.validate_settings(upstream))
        wrong_group = dict(self.settings, SHARED_APP_GROUP_IDENTIFIER="group.com.8bit.bitwarden")
        self.assertTrue(validator.validate_settings(wrong_group))
        signed = dict(self.settings, CODE_SIGNING_ALLOWED="YES")
        self.assertTrue(validator.validate_settings(signed))

    def test_template_is_only_identity_and_unsigned(self) -> None:
        self.assertEqual(self.settings["CODE_SIGNING_ALLOWED"], "NO")
        self.assertEqual(self.settings["CODE_SIGNING_REQUIRED"], "NO")
        self.assertTrue(
            validator.validate_settings(dict(self.settings, EXCLUDED_SOURCE_FILE_NAMES="GoogleService-Info.plist"))
        )
        for key in self.settings:
            self.assertFalse(key.startswith("PROVISIONING_PROFILE"), key)
            self.assertNotIn("FIREBASE", key)
        project = (ROOT / "project-pm.yml").read_text(encoding="utf-8")
        self.assertNotIn("Configs-fork/", project)

    def test_offline_audit_reports_known_integration_blockers(self) -> None:
        codes = {code for code, _ in validator.scan_blockers(ROOT)}
        self.assertNotIn("FIREBASE", codes)
        self.assertTrue(
            {
                "FORK_BUILD_INTEGRATION",
                "CALLBACKS",
                "GENERIC_URL_SCHEME",
                "ASSOCIATED_DOMAINS",
                "WATCH_KEYCHAIN_SERVICE",
                "EXTENSION_UTI",
                "BUILD_AUTOMATION",
                "EXPORT_COMPLIANCE",
                "REGISTRATION_AND_SIGNING",
            }.issubset(codes),
            codes,
        )


class BuildHelperIntegrationTests(unittest.TestCase):
    """Exercise the shell wrapper with fake host tools; never invoke real Xcode."""

    def setUp(self) -> None:
        scratch = Path(os.environ.get("TMPDIR", "/home/hermes/.hermes/cache/scratch"))
        scratch.mkdir(parents=True, exist_ok=True)
        self._temporary = tempfile.TemporaryDirectory(prefix="duo-helper-test-", dir=scratch)
        self.temp = Path(self._temporary.name)
        self.root = self.temp / "repo"
        self._make_fixture()
        self.mock_bin = self.temp / "mock-bin"
        self.mock_bin.mkdir()
        self._make_mock_tools()
        self.source_packages = self.temp / "cache" / "SourcePackages"
        (self.source_packages / "checkouts" / "sdk-swift").mkdir(parents=True)
        self.mint_bin = self.temp / "mint" / "bin"
        self.mint_bin.mkdir(parents=True)
        for tool in ("license-plist", "sourcery", "swiftgen"):
            self._write_executable(self.mint_bin / tool, "#!/bin/sh\nexit 0\n")
        self.args_file = self.temp / "xcodebuild-args"
        self.df_path_file = self.temp / "df-path"
        self.mint_dir_file = self.temp / "mint-dir"
        self.sdk_dir_file = self.temp / "sdk-dir"
        self.output = self.temp / "outputs" / "DerivedData"

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _make_fixture(self) -> None:
        self.root.mkdir(parents=True)
        shutil.copytree(ROOT / "Scripts-fork", self.root / "Scripts-fork", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "Configs-fork", self.root / "Configs-fork")
        shutil.copytree(ROOT / "Configs", self.root / "Configs")
        for relative in (
            ".xcode-version",
            "project-pm.yml",
            "project-bwk.yml",
            "Bitwarden/Application/Support/Bitwarden.entitlements",
            "BitwardenAutoFillExtension/Application/Support/BitwardenAutoFill.entitlements",
            "BitwardenShareExtension/Application/Support/BitwardenShareExtension.entitlements",
            "Bitwarden/Application/Services/ErrorReporter/ErrorReporterFactory.swift",
            "Bitwarden/Application/Services/ErrorReporter/CrashlyticsErrorReporter.swift",
            "BitwardenWatchApp/ExtensionDelegate.swift",
        ):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        for project in ("Bitwarden.xcodeproj", "BitwardenKit.xcodeproj", "Authenticator.xcodeproj", "TestHarness.xcodeproj"):
            (self.root / project).mkdir()
        workspace = self.root / "Bitwarden.xcworkspace"
        (workspace / "xcshareddata/swiftpm").mkdir(parents=True)
        (workspace / "contents.xcworkspacedata").write_text("fixture workspace\n", encoding="utf-8")
        (workspace / "xcshareddata/swiftpm/Package.resolved").write_text(
            json.dumps({"pins": [{"identity": "sdk-swift"}]}), encoding="utf-8"
        )

    @staticmethod
    def _write_executable(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _make_mock_tools(self) -> None:
        self._write_executable(
            self.mock_bin / "uname",
            "#!/bin/sh\ncase \"${1:-}\" in -s) printf 'Darwin\\n' ;; -m) printf 'arm64\\n' ;; *) exit 64 ;; esac\n",
        )
        self._write_executable(
            self.mock_bin / "pgrep",
            "#!/bin/sh\n[ \"${MOCK_XCODEBUSY:-0}\" = 1 ] && exit 0\nexit 1\n",
        )
        self._write_executable(
            self.mock_bin / "df",
            "#!/bin/sh\nprintf '%s\\n' \"$2\" > \"$MOCK_DF_PATH_FILE\"\nprintf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\nmock 1 0 %s 0%% /\\n' \"${MOCK_FREE_KIB:-41943040}\"\n",
        )
        self._write_executable(
            self.mock_bin / "xcrun",
            "#!/bin/sh\n[ \"${1:-}\" = xcodebuild ] || exit 64\nshift\nexport MOCK_XCODE_VERSION=\"${MOCK_XCRUN_XCODE_VERSION:-${MOCK_XCODE_VERSION:-27.2}}\"\nexec xcodebuild \"$@\"\n",
        )
        mock_xcodebuild = """#!/usr/bin/env bash
if [[ "${1:-}" == "-version" ]]; then
    printf 'Xcode %s\\nBuild version MOCK\\n' "${MOCK_XCODE_VERSION:-27.2}"
    exit 0
fi
printf '%s\\0' "$@" > "$MOCK_XCODEBUILD_ARGS_FILE"
printf '%s\\n' "${BITWARDEN_DUO_MINT_BIN_DIR:-}" > "$MOCK_MINT_DIR_FILE"
printf '%s\\n' "${BITWARDEN_SDK_PATH:-}" > "$MOCK_SDK_DIR_FILE"
derived=""
configuration=Debug
while (($#)); do
    if [[ "$1" == "-derivedDataPath" ]]; then shift; derived="$1"; fi
    if [[ "$1" == "-configuration" ]]; then shift; configuration="$1"; fi
    shift
done
app="$derived/Build/Products/${configuration}-iphonesimulator/Bitwarden.app"
mkdir -p "$app"
if [[ "${MOCK_FIREBASE:-0}" == 1 ]]; then
    watch="$app/Watch/BitwardenWatchApp.app"
    mkdir -p "$watch"
    : > "$watch/GoogleService-Info.plist"
fi
exit "${MOCK_BUILD_STATUS:-0}"
"""
        self._write_executable(self.mock_bin / "xcodebuild", mock_xcodebuild)

    def _env(self, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.mock_bin}{os.pathsep}{env.get('PATH', os.defpath)}",
                "BITWARDEN_DUO_MINT_BIN_DIR": str(self.mint_bin),
                "BITWARDEN_DUO_SOURCE_PACKAGES": str(self.source_packages),
                "BITWARDEN_DUO_DERIVED_DATA": str(self.output),
                "MOCK_XCODEBUILD_ARGS_FILE": str(self.args_file),
                "MOCK_DF_PATH_FILE": str(self.df_path_file),
                "MOCK_MINT_DIR_FILE": str(self.mint_dir_file),
                "MOCK_SDK_DIR_FILE": str(self.sdk_dir_file),
                "MOCK_FREE_KIB": str(40 * 1024 * 1024),
            }
        )
        env.update(extra)
        return env

    def _run_helper(self, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.root / "Scripts-fork/build_bitwarden_duo_simulator.sh")],
            cwd=self.root,
            env=self._env(**env),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def test_nonpinned_xcode_fails_closed_without_explicit_exact_version_opt_in(self) -> None:
        result = self._run_helper()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [XCODE_VERSION]", result.stderr)
        self.assertFalse(self.args_file.exists(), "the xcodebuild invocation must not start")

    def test_pinned_xcode_runs_without_opt_in(self) -> None:
        result = self._run_helper(MOCK_XCODE_VERSION="27.0")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("explicit opt-in", result.stderr.lower())
        self.assertTrue(self.args_file.is_file())

    def test_wrong_nonpinned_version_opt_in_is_rejected(self) -> None:
        result = self._run_helper(BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.1")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [XCODE_VERSION]", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_active_xcodebuild_blocks_before_disk_or_build(self) -> None:
        result = self._run_helper(MOCK_XCODEBUSY="1")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [XCODEBUSY]", result.stderr)
        self.assertFalse(self.df_path_file.exists())
        self.assertFalse(self.args_file.exists())

    def test_existing_derived_data_is_never_overwritten(self) -> None:
        self.output.mkdir(parents=True)
        result = self._run_helper()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [OUTPUT_EXISTS]", result.stderr)
        self.assertTrue(self.output.is_dir())
        self.assertFalse(self.args_file.exists())

    def test_explicit_reuse_uses_existing_cache_one_job_and_five_gib_floor(self) -> None:
        self.output.mkdir(parents=True)
        result = self._run_helper(
            BITWARDEN_DUO_REUSE_DERIVED_DATA="YES",
            BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2",
            MOCK_FREE_KIB=str(6 * 1024 * 1024),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        args = self.args_file.read_bytes().decode().rstrip("\0").split("\0")
        self.assertEqual(args[args.index("-derivedDataPath") + 1], str(self.output.resolve()))
        self.assertEqual(args[args.index("-jobs") + 1], "1")
        self.assertTrue(self.output.is_dir())

    def test_reuse_mode_stops_at_five_gib_floor(self) -> None:
        self.output.mkdir(parents=True)
        result = self._run_helper(
            BITWARDEN_DUO_REUSE_DERIVED_DATA="YES",
            BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2",
            MOCK_FREE_KIB=str(5 * 1024 * 1024 - 1),
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("need at least 5 GiB free", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_explicit_xcode_opt_in_passes_exact_settings_and_checks_output_volume(self) -> None:
        result = self._run_helper(
            BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2",
            BITWARDEN_DUO_MINT_BIN_DIR="../mint/bin",
            BITWARDEN_DUO_SOURCE_PACKAGES="../cache/SourcePackages",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("explicit opt-in", result.stderr.lower())
        self.assertTrue(self.args_file.is_file())
        args = self.args_file.read_bytes().decode().rstrip("\0").split("\0")
        config_index = args.index("-xcconfig")
        self.assertEqual(args[config_index + 1], str(self.root / "Configs-fork/Bitwarden-Duo-Simulator.xcconfig"))
        packages_index = args.index("-clonedSourcePackagesDirPath")
        self.assertEqual(args[packages_index + 1], str(self.source_packages.resolve()))
        self.assertEqual(Path(self.mint_dir_file.read_text(encoding="utf-8").strip()), self.mint_bin.resolve())
        self.assertEqual(
            Path(self.sdk_dir_file.read_text(encoding="utf-8").strip()),
            (self.source_packages / "checkouts/sdk-swift").resolve(),
        )
        self.assertEqual(
            args[-8:],
            validator.simulator_xcodebuild_overrides(
                validator.parse_xcconfig(self.root / validator.SIMULATOR_CONFIG)
            ),
        )
        for override in (
            "BASE_BUNDLE_ID=com.sputnicity.bitwarden-duo",
            "CODE_SIGNING_ALLOWED=NO",
            "CODE_SIGNING_REQUIRED=NO",
            "EXCLUDED_SOURCE_FILE_NAMES=GoogleService-Info.plist",
        ):
            self.assertIn(override, args)
            self.assertGreater(args.index(override), config_index)
        self.assertIn("-disableAutomaticPackageResolution", args)
        self.assertIn("-skipPackageUpdates", args)
        self.assertIn("ARCHS=arm64", args)
        self.assertIn("ONLY_ACTIVE_ARCH=YES", args)
        self.assertFalse(any(arg in args for arg in ("-allowProvisioningUpdates", "-exportArchive")))
        self.assertEqual(Path(self.df_path_file.read_text(encoding="utf-8").strip()), self.temp.resolve())
        self.assertIn("no GoogleService-Info.plist", result.stdout)

    def test_release_build_uses_explicit_firebase_isolation_overrides(self) -> None:
        result = self._run_helper(MOCK_XCODE_VERSION="27.0", BITWARDEN_DUO_CONFIGURATION="Release")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        args = self.args_file.read_bytes().decode().rstrip("\0").split("\0")
        self.assertEqual(args[args.index("-configuration") + 1], "Release")
        self.assertEqual(
            args[args.index("-xcconfig") + 1],
            str(self.root / "Configs-fork/Bitwarden-Duo-Release.xcconfig"),
        )
        expected = validator.release_xcodebuild_overrides(
            validator.parse_xcconfig(self.root / validator.RELEASE_CONFIG)
        )
        self.assertEqual(args[-len(expected):], expected)
        self.assertIn("SWIFT_ACTIVE_COMPILATION_CONDITIONS=$(inherited) BITWARDEN_DUO_DISABLE_FIREBASE", expected)
        self.assertIn("EXCLUDED_SOURCE_FILE_NAMES=GoogleService-Info.plist", expected)
        self.assertIn("Release-iphonesimulator", result.stdout)
        self.assertIn("no GoogleService-Info.plist", result.stdout)

    def test_embedded_watch_firebase_plist_blocks_release_success(self) -> None:
        result = self._run_helper(
            MOCK_XCODE_VERSION="27.0",
            BITWARDEN_DUO_CONFIGURATION="Release",
            MOCK_FIREBASE="1",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [UPSTREAM_FIREBASE_RESOURCE]", result.stderr)
        self.assertIn("BitwardenWatchApp.app/GoogleService-Info.plist", result.stderr)
        self.assertNotIn("PASS: unsigned Release simulator product created", result.stdout)

    def test_relative_output_that_resolves_inside_repo_is_rejected_before_build(self) -> None:
        result = self._run_helper(
            BITWARDEN_DUO_DERIVED_DATA="DerivedData-from-test",
            BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [OUTPUT_PATH]", result.stderr)
        self.assertFalse(self.args_file.exists())
        self.assertFalse((self.root / "DerivedData-from-test").exists())

    def test_low_space_on_derived_data_volume_fails_before_xcodebuild(self) -> None:
        result = self._run_helper(MOCK_FREE_KIB=str(25 * 1024 * 1024))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [DISK_SPACE]", result.stderr)
        self.assertEqual(Path(self.df_path_file.read_text(encoding="utf-8").strip()), self.temp.resolve())
        self.assertFalse(self.args_file.exists())

    def test_missing_package_resolved_fails_with_actionable_message(self) -> None:
        (self.root / "Bitwarden.xcworkspace/xcshareddata/swiftpm/Package.resolved").unlink()
        result = self._run_helper(BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [PACKAGE_CACHE_MISSING]", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_malformed_package_resolved_fails_closed_without_traceback(self) -> None:
        resolved = self.root / "Bitwarden.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        resolved.write_text("not-json", encoding="utf-8")
        result = self._run_helper(BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [PACKAGE_CACHE_MISSING]", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_version_guard_checks_the_xcrun_selected_xcode(self) -> None:
        result = self._run_helper(MOCK_XCODE_VERSION="27.0", MOCK_XCRUN_XCODE_VERSION="27.2")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [XCODE_VERSION]", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_simulator_config_rejects_unreviewed_build_settings(self) -> None:
        config = self.root / validator.SIMULATOR_CONFIG
        config.write_text(
            config.read_text(encoding="utf-8") + "\nSWIFT_ACTIVE_COMPILATION_CONDITIONS = RELEASE\n",
            encoding="utf-8",
        )
        _, errors = validator.simulator_config_errors(self.root)
        self.assertTrue(any("unreviewed setting" in error for error in errors), errors)

    def test_embedded_watch_firebase_plist_blocks_success(self) -> None:
        result = self._run_helper(
            BITWARDEN_DUO_ALLOW_XCODE_VERSION="27.2",
            MOCK_FIREBASE="1",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED [UPSTREAM_FIREBASE_RESOURCE]", result.stderr)
        self.assertIn("BitwardenWatchApp.app/GoogleService-Info.plist", result.stderr)
        self.assertNotIn("PASS: unsigned Debug simulator product created", result.stdout)


class MintDispatcherTests(unittest.TestCase):
    def test_dispatcher_executes_only_cached_alias_and_preserves_arguments(self) -> None:
        scratch = Path(os.environ.get("TMPDIR", "/home/hermes/.hermes/cache/scratch"))
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="duo-mint-test-", dir=scratch) as temporary:
            temp = Path(temporary)
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            capture = temp / "args"
            target = bin_dir / "license-plist"
            target.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$MINT_TEST_CAPTURE\"\n",
                encoding="utf-8",
            )
            target.chmod(0o755)
            for tool in ("sourcery", "swiftgen"):
                (bin_dir / tool).symlink_to(target)
            env = os.environ.copy()
            env["BITWARDEN_DUO_MINT_BIN_DIR"] = str(bin_dir)
            env["MINT_TEST_CAPTURE"] = str(capture)
            dispatcher = SCRIPT_DIR / "mint"
            result = subprocess.run(
                ["bash", str(dispatcher), "run", "mono0926/LicensePlist@3.27.2", "license-plist", "--config-path", "local.yml"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(capture.read_text(encoding="utf-8").splitlines(), ["--config-path", "local.yml"])

            for package, arguments in (
                ("krzysztofzablocki/Sourcery@2.3.0", ["--config", "sourcery.yml"]),
                ("SwiftGen/SwiftGen@6.6.3", ["config", "run", "--config", "swiftgen.yml"]),
            ):
                result = subprocess.run(
                    ["bash", str(dispatcher), "run", package, *arguments],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(capture.read_text(encoding="utf-8").splitlines(), arguments)

            denied = subprocess.run(
                ["bash", str(dispatcher), "run", "yonaskolb/xcodegen@2.44.1"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(denied.returncode, 64)
            self.assertIn("not allowed", denied.stderr)

            denied_linter = subprocess.run(
                ["bash", str(dispatcher), "run", "realm/SwiftLint@0.63.1", "lint"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(denied_linter.returncode, 64)
            self.assertIn("not allowed", denied_linter.stderr)

            missing = subprocess.run(
                ["bash", str(dispatcher), "run", "swiftgen"],
                env={**env, "BITWARDEN_DUO_MINT_BIN_DIR": str(temp / "empty-bin")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing.returncode, 69)
            self.assertIn("no network install attempted", missing.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
