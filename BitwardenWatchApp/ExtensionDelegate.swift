#if !DEBUG && !BITWARDEN_DUO_DISABLE_FIREBASE
import FirebaseCore
#endif
import WatchKit

class ExtensionDelegate: NSObject, WKExtensionDelegate {
    func applicationDidFinishLaunching() {
        #if !DEBUG && !BITWARDEN_DUO_DISABLE_FIREBASE
        FirebaseApp.configure()
        #endif
    }
}
