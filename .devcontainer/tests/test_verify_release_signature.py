from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SignatureVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("gpg") is None:
            raise unittest.SkipTest("gpg is required for signature integration tests")

        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary_directory.name)
        cls.verifier = Path(__file__).resolve().parents[1] / "verify-release-signature.sh"
        cls.payload = cls.root / "payload"
        cls.payload.write_text("reviewed release payload\n", encoding="utf-8")

        cls.expected_home = cls._new_gpg_home("expected-home")
        cls.attacker_home = cls._new_gpg_home("attacker-home")
        cls._generate_key(cls.expected_home, "Expected Signer <expected@example.invalid>")
        cls._generate_key(cls.attacker_home, "Unexpected Signer <unexpected@example.invalid>")
        cls.expected_fingerprint = cls._fingerprint(cls.expected_home)
        cls.attacker_fingerprint = cls._fingerprint(cls.attacker_home)

        cls.expected_key = cls.root / "expected.asc"
        cls.attacker_key = cls.root / "attacker.asc"
        cls.expected_key.write_bytes(cls._export_key(cls.expected_home, cls.expected_fingerprint))
        cls.attacker_key.write_bytes(cls._export_key(cls.attacker_home, cls.attacker_fingerprint))

        cls.expected_signature = cls.root / "expected.sig"
        cls.attacker_signature = cls.root / "attacker.sig"
        cls._sign(cls.expected_home, cls.expected_fingerprint, cls.expected_signature)
        cls._sign(cls.attacker_home, cls.attacker_fingerprint, cls.attacker_signature)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary_directory.cleanup()

    @classmethod
    def _run_gpg(cls, home: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["gpg", "--batch", "--homedir", str(home), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @classmethod
    def _new_gpg_home(cls, name: str) -> Path:
        home = cls.root / name
        home.mkdir(mode=0o700)
        return home

    @classmethod
    def _generate_key(cls, home: Path, identity: str) -> None:
        cls._run_gpg(
            home,
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "",
            "--quick-generate-key",
            identity,
            "ed25519",
            "sign",
            "1d",
        )

    @classmethod
    def _fingerprint(cls, home: Path) -> str:
        listing = cls._run_gpg(home, "--with-colons", "--list-keys").stdout.decode("utf-8")
        return next(line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:"))

    @classmethod
    def _export_key(cls, home: Path, fingerprint: str) -> bytes:
        return cls._run_gpg(home, "--armor", "--export", fingerprint).stdout

    @classmethod
    def _sign(cls, home: Path, fingerprint: str, output: Path) -> None:
        cls._run_gpg(
            home,
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "",
            "--local-user",
            fingerprint,
            "--output",
            str(output),
            "--detach-sign",
            str(cls.payload),
        )

    def _verification_home(self, name: str) -> Path:
        return self._new_gpg_home(name)

    def _verify(
        self,
        public_key: Path,
        home: Path,
        expected_fingerprint: str,
        signature: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "sh",
                str(self.verifier),
                str(public_key),
                str(home),
                expected_fingerprint,
                str(signature),
                str(self.payload),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_accepts_signature_from_exact_expected_key(self) -> None:
        result = self._verify(
            self.expected_key,
            self._verification_home("verify-expected"),
            self.expected_fingerprint,
            self.expected_signature,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_expected_key_followed_by_attacker_key(self) -> None:
        key_bundle = self.root / "expected-plus-attacker.asc"
        key_bundle.write_bytes(self.expected_key.read_bytes() + self.attacker_key.read_bytes())

        result = self._verify(
            key_bundle,
            self._verification_home("verify-bundle"),
            self.expected_fingerprint,
            self.attacker_signature,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly expected primary fingerprint", result.stderr)

    def test_rejects_signature_from_other_key_already_in_keyring(self) -> None:
        verification_home = self._verification_home("verify-preloaded")
        self._run_gpg(verification_home, "--import", str(self.attacker_key))

        result = self._verify(
            self.expected_key,
            verification_home,
            self.expected_fingerprint,
            self.attacker_signature,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("was not made by expected primary key", result.stderr)


if __name__ == "__main__":
    unittest.main()
