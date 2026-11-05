from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


APT_STUB = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
import time

state_file = Path(os.environ["APT_TEST_STATE"])
state = json.loads(state_file.read_text())
arguments = sys.argv[1:]
phase = "update" if arguments[-1] == "update" else (
    "download" if "--download-only" in arguments else "install"
)
state[phase] += 1
state["calls"].append(arguments)
state_file.write_text(json.dumps(state))
hang = os.environ.get("APT_TEST_HANG", "")
if phase == "update" and (hang == "always" or (hang == "first" and state[phase] == 1)):
    time.sleep(60)
limit = int(os.environ.get("APT_TEST_FAIL_" + phase.upper(), "0"))
sys.exit(100 if state[phase] <= limit else 0)
"""


class AptInstallationTests(unittest.TestCase):
    script = Path(__file__).resolve().parents[1] / "install-apt-packages.sh"

    def run_installation(
        self,
        *,
        update_failures: int = 0,
        download_failures: int = 0,
        install_failures: int = 0,
        hang: str = "",
        packages: tuple[str, ...] = ("git", "jq"),
    ) -> tuple[subprocess.CompletedProcess[str], dict, list[str]]:
        real_timeout = shutil.which("timeout")
        if real_timeout is None:
            self.skipTest("GNU timeout is required")
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            state_file = root / "state.json"
            state_file.write_text(json.dumps(dict(update=0, download=0, install=0, calls=[])))
            (root / "apt-get").write_text(APT_STUB)
            (root / "apt-get").chmod(0o755)
            (root / "sleep").write_text(
                '#!/bin/sh\nprintf "%s\\n" "$1" >> "$APT_TEST_SLEEPS"\n'
            )
            (root / "sleep").chmod(0o755)
            # Verify the production time limits, then shorten them only for
            # these tests. The real timeout must terminate the stalled child.
            (root / "timeout").write_text(
                '#!/bin/sh\n'
                '[ "$1" = "--kill-after=15s" ] && [ "$2" = "300" ] || exit 99\n'
                'shift 2\n'
                'exec "$APT_TEST_REAL_TIMEOUT" --kill-after=1s 0.5 "$@"\n'
            )
            (root / "timeout").chmod(0o755)
            environment = dict(
                os.environ,
                PATH=str(root) + os.pathsep + os.environ["PATH"],
                APT_TEST_STATE=str(state_file),
                APT_TEST_SLEEPS=str(root / "sleeps"),
                APT_TEST_REAL_TIMEOUT=real_timeout,
                APT_TEST_FAIL_UPDATE=str(update_failures),
                APT_TEST_FAIL_DOWNLOAD=str(download_failures),
                APT_TEST_FAIL_INSTALL=str(install_failures),
                APT_TEST_HANG=hang,
            )
            result = subprocess.run(
                ["sh", str(self.script), *packages],
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
            )
            sleeps = root / "sleeps"
            return (
                result,
                json.loads(state_file.read_text()),
                sleeps.read_text().splitlines() if sleeps.exists() else [],
            )

    def test_downloads_before_installing_without_network(self) -> None:
        result, state, sleeps = self.run_installation()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [1, 1, 1])
        self.assertIn("APT::Update::Error-Mode=any", state["calls"][0])
        self.assertIn("Acquire::Retries=0", state["calls"][0])
        self.assertIn("--download-only", state["calls"][1])
        self.assertIn("--no-download", state["calls"][2])
        for call in state["calls"]:
            self.assertNotIn("--allow-downgrades", call)
        self.assertEqual(state["calls"][1][-2:], ["git", "jq"])
        self.assertEqual(state["calls"][2][-2:], ["git", "jq"])
        self.assertEqual(sleeps, [])

    def test_recovers_from_update_and_download_failures(self) -> None:
        result, state, sleeps = self.run_installation(update_failures=2, download_failures=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [3, 2, 1])
        self.assertEqual(sleeps, ["10", "20", "10"])

    def test_failed_update_prevents_download_and_install(self) -> None:
        result, state, sleeps = self.run_installation(update_failures=6)
        self.assertEqual(result.returncode, 100)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [6, 0, 0])
        self.assertEqual(sleeps, ["10", "20", "30", "40", "50"])
        self.assertIn("index update failed after 6 attempts", result.stderr)

    def test_failed_download_prevents_install(self) -> None:
        result, state, sleeps = self.run_installation(download_failures=6)
        self.assertEqual(result.returncode, 100)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [1, 6, 0])
        self.assertEqual(sleeps, ["10", "20", "30", "40", "50"])
        self.assertIn("package download failed after 6 attempts", result.stderr)

    def test_sixth_attempt_can_succeed_in_each_phase(self) -> None:
        result, state, sleeps = self.run_installation(update_failures=5, download_failures=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [6, 6, 1])
        self.assertEqual(sleeps, ["10", "20", "30", "40", "50"] * 2)

    def test_install_failure_is_not_retried(self) -> None:
        result, state, sleeps = self.run_installation(install_failures=1)
        self.assertEqual(result.returncode, 100)
        self.assertEqual(state["install"], 1)
        self.assertEqual(sleeps, [])

    def test_stalled_update_is_terminated_and_retried(self) -> None:
        result, state, sleeps = self.run_installation(hang="first")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [2, 1, 1])
        self.assertEqual(sleeps, ["10"])

    def test_persistent_stall_stops_without_installing(self) -> None:
        result, state, sleeps = self.run_installation(hang="always")
        self.assertEqual(result.returncode, 124)
        self.assertEqual([state[key] for key in ("update", "download", "install")], [6, 0, 0])
        self.assertEqual(sleeps, ["10", "20", "30", "40", "50"])

    def test_missing_packages_are_rejected_before_apt_runs(self) -> None:
        result, state, sleeps = self.run_installation(packages=())
        self.assertEqual(result.returncode, 2)
        self.assertEqual(state["calls"], [])
        self.assertEqual(sleeps, [])


if __name__ == "__main__":
    unittest.main()
