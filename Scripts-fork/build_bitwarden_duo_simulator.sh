#!/usr/bin/env bash
# Build the Bitwarden-Duo app for Simulator with isolated identity and no signing.
# This helper never generates projects, installs dependencies, signs, installs, or uploads.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
CONFIG="$ROOT/Configs-fork/Bitwarden-Duo-Simulator.xcconfig"
VALIDATOR="$ROOT/Scripts-fork/validate_bitwarden_duo_identity.py"

fail() {
    local code="$1"
    shift
    printf 'BLOCKED [%s]: %s\n' "$code" "$*" >&2
    exit 2
}

resolve_path() {
    python3 - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

[[ "$(uname -s)" == "Darwin" ]] || fail "MACOS_REQUIRED" "run this helper on the Mac with Xcode installed"
command -v xcrun >/dev/null 2>&1 || fail "XCODE_REQUIRED" "xcrun is not available"
command -v python3 >/dev/null 2>&1 || fail "PYTHON_REQUIRED" "python3 is not available"

if pgrep -x xcodebuild >/dev/null 2>&1; then
    fail "XCODEBUSY" "another xcodebuild is running; wait for it to finish before starting a build"
fi

run_tag="$(date -u +%Y%m%dT%H%M%SZ)"
reuse_derived_data="${BITWARDEN_DUO_REUSE_DERIVED_DATA:-NO}"
case "$reuse_derived_data" in
    YES)
        [[ -n "${BITWARDEN_DUO_DERIVED_DATA:-}" ]] || fail "REUSE_PATH" "set BITWARDEN_DUO_DERIVED_DATA to the existing task-owned DerivedData directory when reuse is enabled"
        DERIVED_DATA_INPUT="$BITWARDEN_DUO_DERIVED_DATA"
        ;;
    NO)
        DERIVED_DATA_INPUT="${BITWARDEN_DUO_DERIVED_DATA:-$HOME/agent-builds/bitwarden-duo-simulator-unsigned-$run_tag/DerivedData}"
        ;;
    *) fail "REUSE_MODE" "BITWARDEN_DUO_REUSE_DERIVED_DATA must be YES or NO" ;;
esac
[[ ! -L "$DERIVED_DATA_INPUT" ]] || fail "OUTPUT_EXISTS" "refusing to use a symlink as derived data: $DERIVED_DATA_INPUT"
DERIVED_DATA="$(resolve_path "$DERIVED_DATA_INPUT")"
case "$DERIVED_DATA/" in
    "$ROOT/"*) fail "OUTPUT_PATH" "derived data must resolve outside the source repository" ;;
esac
if [[ "$reuse_derived_data" == YES ]]; then
    [[ -d "$DERIVED_DATA" ]] || fail "REUSE_PATH" "reuse is allowed only for an existing DerivedData directory: $DERIVED_DATA"
else
    [[ ! -e "$DERIVED_DATA" && ! -L "$DERIVED_DATA" ]] || fail "OUTPUT_EXISTS" "refusing to overwrite existing derived data: $DERIVED_DATA"
fi

disk_probe="$(dirname "$DERIVED_DATA")"
while [[ ! -d "$disk_probe" ]]; do
    parent="$(dirname "$disk_probe")"
    [[ "$parent" != "$disk_probe" ]] || fail "DISK_CHECK" "could not find an existing directory for the derived-data volume"
    disk_probe="$parent"
done
free_kib="$(df -Pk "$disk_probe" | awk 'NR == 2 {print $4}')"
[[ "$free_kib" =~ ^[0-9]+$ ]] || fail "DISK_CHECK" "could not determine free space on the derived-data volume"
minimum_gib=28
if [[ "$reuse_derived_data" == YES ]]; then
    # Reuse is an explicit, user-authorized incremental path. Keep a hard 5 GiB floor.
    minimum_gib=5
fi
minimum_kib=$((minimum_gib * 1024 * 1024))
(( free_kib >= minimum_kib )) || fail "DISK_SPACE" "need at least $minimum_gib GiB free on the derived-data volume; df reports $((free_kib / 1024 / 1024)) GiB"

required_xcode="$(tr -d '[:space:]' < "$ROOT/.xcode-version")"
[[ "$required_xcode" =~ ^[0-9]+(\.[0-9]+){1,2}$ ]] || fail "XCODE_VERSION" "repository .xcode-version pin is invalid: $required_xcode"
if ! xcode_version_output="$(xcrun xcodebuild -version 2>&1)"; then
    fail "XCODE_REQUIRED" "xcrun could not run the selected xcodebuild: $xcode_version_output"
fi
current_xcode="$(printf '%s\n' "$xcode_version_output" | awk 'NR == 1 {print $2}')"
[[ "$current_xcode" =~ ^[0-9]+(\.[0-9]+){1,2}$ ]] || fail "XCODE_VERSION" "could not parse selected Xcode version: $xcode_version_output"
if [[ "$current_xcode" != "$required_xcode" ]]; then
    allowed_xcode="${BITWARDEN_DUO_ALLOW_XCODE_VERSION:-}"
    [[ "$allowed_xcode" == "$current_xcode" ]] || fail "XCODE_VERSION" "repository pins Xcode $required_xcode, but xcrun selects $current_xcode; set BITWARDEN_DUO_ALLOW_XCODE_VERSION=$current_xcode to explicitly opt in to this exact version"
    printf 'WARNING: explicit opt-in: using non-pinned Xcode %s (repository pin: %s)\n' "$current_xcode" "$required_xcode" >&2
fi

for project in Bitwarden.xcodeproj BitwardenKit.xcodeproj Authenticator.xcodeproj TestHarness.xcodeproj; do
    [[ -d "$ROOT/$project" ]] || fail "PROJECTS_MISSING" "generated $project is missing; prepare the standard generated projects and rerun"
done
[[ -f "$ROOT/Bitwarden.xcworkspace/contents.xcworkspacedata" ]] || fail "WORKSPACE_MISSING" "Bitwarden.xcworkspace is missing"

MINT_BIN_DIR_INPUT="${BITWARDEN_DUO_MINT_BIN_DIR:-${MINT_PATH:-$HOME/.mint}/bin}"
MINT_BIN_DIR="$(resolve_path "$MINT_BIN_DIR_INPUT")"
for tool in license-plist sourcery swiftgen; do
    [[ -x "$MINT_BIN_DIR/$tool" ]] || fail "LOCAL_TOOL_MISSING" "cached $tool is required at $MINT_BIN_DIR/$tool; this helper will not download it"
done
SOURCE_PACKAGES_INPUT="${BITWARDEN_DUO_SOURCE_PACKAGES:-}"
[[ -n "$SOURCE_PACKAGES_INPUT" ]] || fail "PACKAGE_CACHE_MISSING" "set BITWARDEN_DUO_SOURCE_PACKAGES to an existing Xcode SourcePackages directory"
SOURCE_PACKAGES="$(resolve_path "$SOURCE_PACKAGES_INPUT")"
[[ -d "$SOURCE_PACKAGES/checkouts" ]] || fail "PACKAGE_CACHE_MISSING" "SourcePackages checkouts are missing at $SOURCE_PACKAGES/checkouts"
[[ -d "$SOURCE_PACKAGES/checkouts/sdk-swift" ]] || fail "PACKAGE_CACHE_MISSING" "cached sdk-swift checkout is missing at $SOURCE_PACKAGES/checkouts/sdk-swift"
RESOLVED_PACKAGES="$ROOT/Bitwarden.xcworkspace/xcshareddata/swiftpm/Package.resolved"
[[ -f "$RESOLVED_PACKAGES" ]] || fail "PACKAGE_CACHE_MISSING" "workspace Package.resolved is missing: $RESOLVED_PACKAGES"
if ! python3 - "$RESOLVED_PACKAGES" "$SOURCE_PACKAGES/checkouts" <<'PY'
import json
import sys
from pathlib import Path

try:
    resolved = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    print(f"could not read valid Package.resolved: {error}", file=sys.stderr)
    raise SystemExit(2)
if not isinstance(resolved, dict):
    print("Package.resolved must contain a JSON object", file=sys.stderr)
    raise SystemExit(2)
pins = resolved.get("pins")
if not isinstance(pins, list):
    print("Package.resolved has no valid pins list", file=sys.stderr)
    raise SystemExit(2)
checkouts = Path(sys.argv[2])
identities = [pin.get("identity") for pin in pins if isinstance(pin, dict)]
if len(identities) != len(pins) or any(
    not isinstance(identity, str)
    or not identity
    or identity in {".", ".."}
    or Path(identity).name != identity
    for identity in identities
):
    print("Package.resolved contains an invalid package identity", file=sys.stderr)
    raise SystemExit(2)
missing = [identity for identity in identities if not (checkouts / identity).is_dir()]
if missing:
    print("missing cached Swift packages (no fetch attempted): " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(2)
print(f"PASS: all {len(pins)} resolved Swift packages are cached locally")
PY
then
    fail "PACKAGE_CACHE_MISSING" "could not validate local checkouts against $RESOLVED_PACKAGES"
fi


python3 "$VALIDATOR" --check-simulator-config
if ! override_output="$(python3 "$VALIDATOR" --emit-xcodebuild-overrides)"; then
    fail "SIMULATOR_CONFIG" "could not emit validated xcodebuild overrides"
fi
BUILD_OVERRIDES=()
while IFS= read -r setting; do
    if [[ -n "$setting" ]]; then
        BUILD_OVERRIDES+=("$setting")
    fi
done <<< "$override_output"
[[ "${#BUILD_OVERRIDES[@]}" -eq 8 ]] || fail "SIMULATOR_CONFIG" "validator emitted an incomplete set of build-setting overrides"

mkdir -p "$(dirname "$DERIVED_DATA")"
if [[ "$reuse_derived_data" == YES ]]; then
    [[ -d "$DERIVED_DATA" && ! -L "$DERIVED_DATA_INPUT" ]] || fail "REUSE_PATH" "task-owned DerivedData disappeared or became a symlink: $DERIVED_DATA"
else
    [[ ! -e "$DERIVED_DATA" && ! -L "$DERIVED_DATA" ]] || fail "OUTPUT_EXISTS" "derived data appeared during preflight; refusing to overwrite it: $DERIVED_DATA"
fi

export BITWARDEN_DUO_MINT_BIN_DIR="$MINT_BIN_DIR"
export BITWARDEN_SDK_PATH="$SOURCE_PACKAGES/checkouts/sdk-swift"
export CI=1
# The local dispatcher precedes Homebrew so Xcode build phases cannot invoke
# Mint's network installer. The dispatcher only runs the cached tools checked above.
export PATH="$SCRIPT_DIR:/opt/homebrew/bin:$PATH"
simulator_arch="$(uname -m)"
case "$simulator_arch" in
    arm64|x86_64) ;;
    *) fail "SIMULATOR_ARCH" "unsupported Mac architecture for an iOS Simulator build: $simulator_arch" ;;
esac

xcrun xcodebuild \
    -workspace "$ROOT/Bitwarden.xcworkspace" \
    -scheme Bitwarden \
    -configuration Debug \
    -destination "generic/platform=iOS Simulator" \
    -jobs 1 \
    -derivedDataPath "$DERIVED_DATA" \
    -clonedSourcePackagesDirPath "$SOURCE_PACKAGES" \
    -xcconfig "$CONFIG" \
    -disableAutomaticPackageResolution \
    -skipPackageUpdates \
    "ARCHS=$simulator_arch" \
    ONLY_ACTIVE_ARCH=YES \
    "${BUILD_OVERRIDES[@]}"

APP="$DERIVED_DATA/Build/Products/Debug-iphonesimulator/Bitwarden.app"
[[ -d "$APP" ]] || fail "APP_MISSING" "xcodebuild succeeded but did not produce $APP"
firebase_plists="$(find "$APP" -name GoogleService-Info.plist -print)"
if [[ -n "$firebase_plists" ]]; then
    fail "UPSTREAM_FIREBASE_RESOURCE" "upstream Firebase plist remains in the product; do not install or launch this build: $firebase_plists"
fi
printf 'PASS: unsigned Debug simulator product created at %s\n' "$APP"
printf 'PASS: no GoogleService-Info.plist exists in the app/watch bundles\n'
printf 'No simulator install, launch, archive, signing, or upload was performed.\n'
