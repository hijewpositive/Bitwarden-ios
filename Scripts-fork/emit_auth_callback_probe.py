# Emits a synthetic Swift harness around the actual callback policy and routing methods.
# Pipe to a macOS Swift interpreter; this is not an ASWebAuthenticationSession runtime test.
from pathlib import Path
import re,sys
s=Path(sys.argv[1] if len(sys.argv) > 1 else 'BitwardenShared/Core/Auth/Services/AuthService.swift').read_text()
def part(pattern):
    m=re.search(pattern,s,re.S)
    if not m: raise SystemExit('missing source fragment: '+pattern)
    return m.group(0)
policy=re.search(r'// MARK: - AuthWebSessionCallbackPolicy\n(.*?)// MARK: - AuthWebSessionCallback\n',s,re.S)
types=part(r'enum AuthWebSessionCallback: Equatable \{.*?\n\}\n.*?enum AuthWebSessionCallbackKind \{.*?\n\}')
https=part(r'    private var supportsHttpsAuthCallback: Bool \{.*?\n    \}')
scheme=part(r'    private var deeplinkScheme: String \{.*?\n    \}')
url=part(r'    private func callbackUrl\(for kind: AuthWebSessionCallbackKind\) -> String \{.*?\n    \}')
resolve=part(r'    private func resolveCallback\(for kind: AuthWebSessionCallbackKind\) -> AuthWebSessionCallback \{.*?\n    \}')
program='''import Foundation
final class Bundle { static let main = Bundle(); var bundleIdentifier: String? }
struct Region { let authCallbackHost: String? }
struct Env { let region: Region }
''' + (policy.group(1) if policy else '') + types + '''
final class Subject {
 let environmentService: Env
 let callbackUrlScheme = "bitwarden"
 init(_ host: String?) { environmentService = Env(region: Region(authCallbackHost: host)) }
''' + https + '\n' + scheme + '\n' + url + '\n' + resolve + '''
 func values() -> (String, String, String, AuthWebSessionCallback) { (deeplinkScheme, callbackUrl(for: .singleSignOn), callbackUrl(for: .duo), resolveCallback(for: .duo)) }
}
func check(_ label: String, _ actual: Bool) { if !actual { print("FAIL: \\(label)"); exit(1) }; print("PASS: \\(label)") }
Bundle.main.bundleIdentifier = "com.sputnicity.bitwarden-duo"
let fork = Subject("bitwarden.com").values()
check("fork SSO and Duo use same legacy callback as deeplink hint", fork.0 == "bitwarden" && fork.1 == "bitwarden://sso-callback" && fork.2 == "bitwarden://duo-callback" && fork.3 == .customScheme("bitwarden"))
Bundle.main.bundleIdentifier = "com.8bit.bitwarden"
let upstream = Subject("bitwarden.com").values()
check("upstream cloud preserves HTTPS", upstream.0 == "https" && upstream.1 == "https://bitwarden.com/sso-callback" && upstream.3 == .https(host: "bitwarden.com", path: "/duo-callback"))
let selfHosted = Subject(nil).values()
check("self-hosted remains legacy", selfHosted.0 == "bitwarden" && selfHosted.3 == .customScheme("bitwarden"))
'''
sys.stdout.write(program)
