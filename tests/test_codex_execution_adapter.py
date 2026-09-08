import json
from pathlib import Path
import os
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapter" / "codex_execution_adapter.py"


FAKE = r"""#!/usr/bin/env python3
import json, os, pathlib, signal, sys
counter = pathlib.Path(os.environ["FAKE_COUNTER"])
counter.write_text(counter.read_text() + "x" if counter.exists() else "x")
pathlib.Path(os.environ["FAKE_ARGS"]).write_text(json.dumps(sys.argv[1:]))
pathlib.Path(os.environ["FAKE_PROMPT"]).write_text(sys.stdin.read())
mode = os.environ.get("FAKE_MODE", "success")
if mode == "success": print(json.dumps({"type": "turn.completed"}))
elif mode == "failure":
    print("technical failure", file=sys.stderr)
    raise SystemExit(7)
elif mode == "invalid": print("not-json")
elif mode == "signal": os.kill(os.getpid(), signal.SIGTERM)
"""


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.repository = self.directory / "repo"
        (self.repository / ".git").mkdir(parents=True)
        self.fake = self.directory / "fake-codex"
        self.fake.write_text(FAKE)
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)
        self.env = os.environ | {
            "FAKE_COUNTER": str(self.directory / "counter"),
            "FAKE_ARGS": str(self.directory / "args"),
            "FAKE_PROMPT": str(self.directory / "prompt"),
        }

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, mode="success", executable=None):
        env = self.env | {"FAKE_MODE": mode}
        return subprocess.run(
            [sys.executable, str(ADAPTER), str(self.repository),
             "--codex-executable", str(executable or self.fake)],
            text=True, capture_output=True, env=env,
        )

    def summary(self, completed):
        return json.loads(completed.stdout)

    def test_invokes_expected_cli_once_and_reports_valid_completion(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0)
        self.assertEqual((self.directory / "counter").read_text(), "x")
        self.assertEqual(json.loads((self.directory / "args").read_text()),
                         ["exec", "--json", "--cd", str(self.repository), "-"])
        summary = self.summary(result)
        self.assertTrue(summary["codex_started"])
        self.assertTrue(summary["technically_completed"])
        self.assertEqual(summary["classification"], "valid_completion")
        self.assertEqual(summary["structured_event_count"], 1)
        prompt = (self.directory / "prompt").read_text()
        self.assertIn("agents/CODEX_WORKER.md", prompt)
        self.assertNotIn("GOV-", prompt)
        self.assertGreaterEqual(summary["codex_wall_seconds"], 0)
        self.assertGreaterEqual(summary["adapter_wall_seconds"], summary["codex_wall_seconds"])
        self.assertIn("finished_at", summary)

    def test_bootstrap_does_not_embed_github_metadata_claims(self):
        self.invoke()
        prompt = (self.directory / "prompt").read_text()
        self.assertLess(len(prompt), 300)
        self.assertNotIn("PR body", prompt)

    def test_nonzero_cli_status_is_execution_failure_and_captured(self):
        result = self.invoke("failure")
        self.assertEqual(result.returncode, 70)
        summary = self.summary(result)
        self.assertEqual(summary["cli_exit_status"], 7)
        self.assertEqual(summary["classification"], "execution_failure")
        self.assertIn("technical failure", Path(summary["stderr_path"]).read_text())

    def test_launch_failure_is_execution_failure(self):
        result = self.invoke(executable=self.directory / "missing")
        self.assertEqual(result.returncode, 70)
        summary = self.summary(result)
        self.assertFalse(summary["codex_started"])
        self.assertEqual(summary["classification"], "execution_failure")

    def test_invalid_success_output_is_invalid_execution(self):
        result = self.invoke("invalid")
        self.assertEqual(result.returncode, 65)
        self.assertEqual(self.summary(result)["classification"], "interrupted_invalid")

    def test_signalled_cli_is_interrupted_execution(self):
        result = self.invoke("signal")
        self.assertEqual(result.returncode, 130)
        summary = self.summary(result)
        self.assertEqual(summary["cli_exit_status"], -15)
        self.assertEqual(summary["classification"], "interrupted_invalid")


if __name__ == "__main__":
    unittest.main()
