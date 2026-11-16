# Bitwarden Duo fork: authentication callback assessment

Assessment date: 2026-11-16. Baseline: `844a47f139ac5a1c8485f3285b60c756968a628b`. This is a source checkpoint for review, not evidence of an installed or released fix.

## Finding

Build 1.0 (2) was reported to support ordinary password login; this does not prove SSO or Duo 2FA. Its source `252c24d` requests HTTPS callbacks on iOS 17.4+ for cloud regions. In the independently read-back signed build 2 app, application identifier `NGYQ8H5H97.com.sputnicity.bitwarden-duo` has wildcard subdomain associated-domain entries, not explicit apex entries. Apple requires the HTTPS callback host to be associated with the app. On this date Apple's AASA CDN for `bitwarden.com`, `bitwarden.eu`, and `bitwarden.pw` did not list this application identifier. The `bitwarden-gov.com` CDN request timed out and was not assessed. This is a concrete configuration mismatch and a potential connector failure; there was no observed Simon SSO/Duo failure and no runtime callback test was performed.

* [Apple HTTPS callback host requirements](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession/callback/https(host:path:))
* [Apple associated domains](https://developer.apple.com/documentation/xcode/supporting-associated-domains)
* [Apple CDN, US](https://app-site-association.cdn-apple.com/a/v1/bitwarden.com), [EU](https://app-site-association.cdn-apple.com/a/v1/bitwarden.eu), [internal](https://app-site-association.cdn-apple.com/a/v1/bitwarden.pw)

## Candidate mitigation

For the exact app bundle ID `com.sputnicity.bitwarden-duo` only, use the existing legacy `bitwarden://` ASWebAuthenticationSession path, including the Duo server deeplink hint and SSO redirect URI. Other bundle IDs retain their prior behavior; self-hosted and pre-iOS-17.4 paths remain legacy. No changes are made to password verification, PKCE, the Duo token/state handling, entitlements, domain ownership, or the general URL-scheme registration.

This is a supported legacy path in the reviewed Bitwarden server/client source, not a newly invented scheme: the SSO redirect allowlist contains `bitwarden://sso-callback`; the web connector maps non-HTTPS Duo deeplink hints to `bitwarden://duo-callback`. A fork-unique scheme would not work with those contracts without coordinated upstream service changes. Apple documents that an active ASWebAuthenticationSession returns its callback to the calling app even when multiple apps register the same scheme; this guarantee concerns the authentication session, not all non-session URL routing. The fork and upstream already share this scheme; this patch does not introduce a new registration or claim general deep-link isolation.

* [Apple ASWebAuthenticationSession](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession)
* [Bitwarden server redirect allowlist, reviewed revision](https://github.com/bitwarden/server/blob/577031933f38604d2d1a388b576d8f460fe9f68f/src/Core/Constants.cs)
* [Bitwarden web connector mapping, reviewed revision](https://github.com/bitwarden/clients/blob/b96dc7b8786ebb4423f82b3f50d8f576df6702e1/apps/web/src/connectors/common.ts)

## Verification and limitations

The synthetic regression harness extracts the real callback-selection, URL generation and deeplink-scheme methods and runs them with stubbed environment and bundle identity in macOS Swift. It failed against the baseline for the expected fork cloud callback mismatch, then passed for fork cloud SSO and Duo, upstream US cloud, and self-hosted. Both modified Swift files passed `swiftc -frontend -parse`; the existing fork identity tests passed 30/30 and signed-entitlement audit tests 6/6. These are not an iOS build, XCTest execution, ASWebAuthenticationSession delivery, or end-to-end authentication. The added XCTest and the adjusted cloud redirect tests were not run in Xcode.

Before distribution, perform isolated simulator or device verification using synthetic callback fixtures, with the upstream and fork apps co-installed and each session separately active; verify correct callback delivery, cancellation, malformed/error responses, unchanged password-login behavior and retained SSO/Duo state and PKCE security. No personal account, personal vault or production service is needed for those local delivery tests. To establish real SSO and Duo interoperability, separately authorize an isolated test account/tenant and appropriate non-personal test environment; server-side contracts and a synthetic fixture are not proof of real sign-in or 2FA. If HTTPS callbacks are desired instead, the actual host association and exact app identity would require cooperation by the domain owner; simply changing local entitlements cannot create that association. No Apple portal assets or upstream AASA files were modified.
