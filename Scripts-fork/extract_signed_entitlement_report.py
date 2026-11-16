#!/usr/bin/env python3
"""Extract non-secret signing metadata from an already-extracted iOS app.

Requires macOS codesign/security. This is evidence collection, not a signature,
profile, provenance, or release validation; verify the signed app separately.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path


def extract(app: Path) -> dict:
    if not app.is_dir() or app.suffix != ".app":
        raise ValueError("expected an extracted .app directory")
    bundles = []
    for directory, dirs, _ in os.walk(app):
        dirs[:] = [d for d in dirs if not d.endswith((".framework", ".bundle", ".dSYM"))]
        bundle = Path(directory)
        if bundle.suffix not in (".app", ".appex"):
            continue
        with (bundle / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        signature = subprocess.run(
            ["/usr/bin/codesign", "-d", "--entitlements", ":-", str(bundle)],
            capture_output=True, check=True,
        )
        entitlements = plistlib.loads(signature.stdout)
        profile = subprocess.run(
            ["/usr/bin/security", "cms", "-D", "-i", str(bundle / "embedded.mobileprovision")],
            capture_output=True, check=True,
        )
        profile_entitlements = plistlib.loads(profile.stdout).get("Entitlements", {})
        bundles.append({
            "bundleId": info["CFBundleIdentifier"],
            "runtimeKeychainAccessGroup": info.get("BitwardenKeychainAccessGroup"),
            "signedEntitlements": entitlements,
            "profileGroups": profile_entitlements.get("com.apple.security.application-groups"),
            "profileICloudContainers": profile_entitlements.get("com.apple.developer.ubiquity-container-identifiers"),
        })
    return {"bundles": bundles}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="Path to the extracted Payload/*.app")
    args = parser.parse_args()
    try:
        report = extract(args.app)
    except (OSError, ValueError, KeyError, plistlib.InvalidFileException, subprocess.CalledProcessError) as exc:
        print(f"ERROR: unable to extract signing metadata: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
