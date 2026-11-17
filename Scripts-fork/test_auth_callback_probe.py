"""Supplementary source-method probe; not an iOS or service-level test."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "BitwardenShared/Core/Auth/Services/AuthService.swift"
EMITTER = ROOT / "Scripts-fork/emit_auth_callback_probe.py"


@unittest.skipUnless(shutil.which("swift"), "Swift interpreter is unavailable")
class CallbackSourceProbeTests(unittest.TestCase):
    def run_probe(self, source):
        program = subprocess.check_output(["python3", str(EMITTER), str(source)], cwd=ROOT)
        return subprocess.run(["swift", "-"], input=program, capture_output=True, cwd=ROOT)

    def test_current_policy(self):
        result = self.run_probe(SOURCE)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"PASS: fork SSO and Duo", result.stdout)
        self.assertIn(b"PASS: upstream cloud", result.stdout)
        self.assertIn(b"PASS: self-hosted", result.stdout)

    def test_disconnected_policy_mutant_fails(self):
        source = SOURCE.read_text()
        policy_call = "&& AuthWebSessionCallbackPolicy.permitsHttpsCallback(bundleIdentifier: appBundleIdentifier)"
        self.assertEqual(source.count(policy_call), 1)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            mutant = Path(directory) / "AuthService.swift"
            mutant.write_text(source.replace(policy_call, "&& true"))
            result = self.run_probe(mutant)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"FAIL: fork SSO and Duo", result.stdout)


if __name__ == "__main__":
    unittest.main()
