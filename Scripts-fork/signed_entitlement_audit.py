#!/usr/bin/env python3
"""Flag missing Duo entitlements in an existing extracted signing report.

This is a diagnostic only. It does not inspect an IPA or verify report provenance,
signatures, capabilities, group assignment, callback safety, or export compliance.
Never treat a clean report as permission to upload.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

BASE = 'com.sputnicity.bitwarden-duo'
TEAM = 'NGYQ8H5H97'
MAIN_GROUP = 'group.' + BASE
AUTH_GROUP = MAIN_GROUP + '.authenticator'
KEYCHAIN = TEAM + '.' + BASE
GROUPS = 'com.apple.security.application-groups'
KEYCHAINS = 'keychain-access-groups'
ICLOUD = 'com.apple.developer.ubiquity-container-identifiers'
AUTOFILL = 'com.apple.developer.authentication-services.autofill-credential-provider'
DOMAINS = 'com.apple.developer.associated-domains'
NFC = 'com.apple.developer.nfc.readersession.formats'
SUFFIXES = ('', '.autofill', '.share-extension', '.find-login-action-extension', '.notification', '.watchkitapp', '.watchkitapp.widget-extension')

def audit_report(report: dict) -> list[str]:
    errors = []
    entries = report.get('bundles')
    if not isinstance(entries, list):
        return ['missing bundles list']
    ids = [x.get('bundleId') for x in entries if isinstance(x, dict)]
    expected = {BASE + s for s in SUFFIXES}
    if len(entries) != 7 or set(ids) != expected or len(ids) != len(set(ids)):
        errors.append('bundle inventory must contain each of the seven exact Duo identifiers once')
    for item in entries:
        if not isinstance(item, dict):
            errors.append('invalid bundle entry')
            continue
        bundle_id = item.get('bundleId', '<missing>')
        if bundle_id not in expected:
            errors.append(f'{bundle_id}: unexpected bundle identifier')
            continue
        ent = item.get('signedEntitlements')
        if not isinstance(ent, dict):
            errors.append(f'{bundle_id}: signedEntitlements missing or invalid')
            continue
        def require(key, value):
            if type(ent.get(key)) is not type(value) or ent.get(key) != value:
                errors.append(f'{bundle_id}: {key} must be {value!r}, got {ent.get(key)!r}')
        def contain(key, value):
            actual = ent.get(key)
            if not isinstance(actual, list) or not set(value).issubset(actual):
                errors.append(f'{bundle_id}: {key} must include {value!r}, got {actual!r}')
        require('application-identifier', TEAM + '.' + bundle_id)
        if bundle_id in {BASE, BASE+'.autofill', BASE+'.share-extension', BASE+'.find-login-action-extension', BASE+'.notification'}:
            needed = [MAIN_GROUP] + ([AUTH_GROUP] if bundle_id == BASE else [])
            contain(GROUPS, needed)
            granted = item.get('profileGroups')
            if not isinstance(granted, list) or not set(needed).issubset(granted):
                errors.append(f'{bundle_id}: profileGroups must include {needed!r}, got {granted!r}')
        if bundle_id in {BASE, BASE+'.autofill', BASE+'.share-extension', BASE+'.find-login-action-extension'}:
            contain(KEYCHAINS, [KEYCHAIN])
        if bundle_id in {BASE, BASE+'.autofill'}:
            require(AUTOFILL, True)
        if bundle_id == BASE:
            require('aps-environment', 'production')
            contain(NFC, ['TAG'])
            domains = [f'{kind}:*.{domain}' for kind in ('webcredentials', 'applinks') for domain in ('bitwarden.com','bitwarden.eu','bitwarden.pw','bitwarden-gov.com')]
            contain(DOMAINS, domains)
            contain(ICLOUD, ['iCloud.'+BASE])
            granted = item.get('profileICloudContainers')
            if not isinstance(granted, list) or 'iCloud.'+BASE not in granted:
                errors.append(f'{bundle_id}: profile {ICLOUD} missing iCloud.{BASE}')
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.report.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('report must be a JSON object')
        errors = audit_report(data)
    except (OSError, ValueError, TypeError) as exc:
        print(f'ERROR: cannot audit report: {exc}')
        return 2
    for error in errors:
        print('BLOCKED:', error)
    print(f'{len(errors)} diagnostic finding(s). A clean report is NOT release approval; verify the actual signed IPA independently.')
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
