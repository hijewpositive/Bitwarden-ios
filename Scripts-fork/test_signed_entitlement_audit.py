"""Tests for a diagnostic, offline signing-report entitlement audit."""
import unittest
import signed_entitlement_audit as audit


class SignedEntitlementAuditTests(unittest.TestCase):
    def test_rejects_unsigned_archive_export_missing_shared_vault_entitlements(self):
        report = {"bundles": [{"bundleId": "com.sputnicity.bitwarden-duo", "signedEntitlements": {"application-identifier": "NGYQ8H5H97.com.sputnicity.bitwarden-duo"}, "profileGroups": [], "profileICloudContainers": None}]}
        errors = audit.audit_report(report)
        self.assertTrue(any("com.apple.security.application-groups" in e for e in errors), errors)
        self.assertTrue(any("keychain-access-groups" in e for e in errors), errors)
        self.assertTrue(any("ubiquity-container-identifiers" in e for e in errors), errors)

    def test_autofill_requires_boolean_true_not_integer_one(self):
        bundle = {"bundleId": audit.BASE + ".autofill", "signedEntitlements": {audit.AUTOFILL: 1}}
        errors = audit.audit_report({"bundles": [bundle]})
        self.assertTrue(any(audit.AUTOFILL in e for e in errors), errors)

    def test_complete_synthetic_report_has_no_diagnostic_findings(self):
        bundles = []
        for suffix in audit.SUFFIXES:
            bid = audit.BASE + suffix
            ent: dict[str, object] = {"application-identifier": audit.TEAM + "." + bid}
            profile_groups = []
            item = {"bundleId": bid, "signedEntitlements": ent, "profileGroups": profile_groups}
            if suffix in ("", ".autofill", ".share-extension", ".find-login-action-extension", ".notification"):
                profile_groups.append(audit.MAIN_GROUP)
                if not suffix:
                    profile_groups.append(audit.AUTH_GROUP)
                ent[audit.GROUPS] = list(profile_groups)
            if suffix in ("", ".autofill", ".share-extension", ".find-login-action-extension"):
                ent[audit.KEYCHAINS] = [audit.KEYCHAIN]
            if suffix in ("", ".autofill"):
                ent[audit.AUTOFILL] = True
            if not suffix:
                ent.update({"aps-environment": "production", audit.NFC: ["TAG"], audit.ICLOUD: ["iCloud." + bid], audit.DOMAINS: [f"{kind}:*.{domain}" for kind in ("webcredentials", "applinks") for domain in ("bitwarden.com", "bitwarden.eu", "bitwarden.pw", "bitwarden-gov.com")]})
                item["profileICloudContainers"] = ["iCloud." + bid]
            bundles.append(item)
        self.assertEqual(audit.audit_report({"bundles": bundles}), [])
        del bundles[1]["signedEntitlements"][audit.GROUPS]
        self.assertTrue(any(audit.GROUPS in e for e in audit.audit_report({"bundles": bundles})))

    def test_rejects_duplicate_or_missing_bundle_ids(self):
        bundle = {"bundleId": audit.BASE, "signedEntitlements": {}}
        errors = audit.audit_report({"bundles": [bundle, bundle]})
        self.assertTrue(any("inventory" in e for e in errors), errors)

if __name__ == "__main__":
    unittest.main()
