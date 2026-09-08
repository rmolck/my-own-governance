import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "runtime" / "systemd_runner.py"

FAKE_ADAPTER = r"""#!/usr/bin/env python3
import json, os, pathlib, sys
counter = pathlib.Path(os.environ["FAKE_ADAPTER_COUNTER"])
counter.write_text(counter.read_text() + "x" if counter.exists() else "x")
pathlib.Path(os.environ["FAKE_ADAPTER_ARGS"]).write_text(json.dumps(sys.argv[1:]))
code = int(os.environ.get("FAKE_ADAPTER_EXIT", "0"))
print(json.dumps({"stdout_path": "/artifact/stdout", "stderr_path": "/artifact/stderr",
                  "technical_error": None if code == 0 else "bounded fake error"}))
raise SystemExit(code)
"""


class SystemdRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.repository = self.directory / "repo"
        (self.repository / ".git").mkdir(parents=True)
        self.adapter = self.directory / "fake-adapter"
        self.adapter.write_text(FAKE_ADAPTER)
        self.adapter.chmod(self.adapter.stat().st_mode | stat.S_IXUSR)
        self.lock = self.directory / "runtime.lock"
        self.durable = self.repository / "checkpoint-state"
        self.durable.write_text("WORKING")
        self.env = os.environ | {
            "GOVERNANCE_REPOSITORY": str(self.repository),
            "GOVERNANCE_ADAPTER": str(self.adapter),
            "GOVERNANCE_PYTHON": sys.executable,
            "GOVERNANCE_LOCK_FILE": str(self.lock),
            "FAKE_ADAPTER_COUNTER": str(self.directory / "counter"),
            "FAKE_ADAPTER_ARGS": str(self.directory / "args"),
        }

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, code=0, env=None):
        return subprocess.run(
            [sys.executable, str(RUNNER)],
            text=True,
            capture_output=True,
            env=(env or self.env) | {"FAKE_ADAPTER_EXIT": str(code)},
        )

    def summary(self, result):
        return json.loads(result.stdout)

    def test_free_lock_invokes_adapter_exactly_once(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0)
        self.assertEqual((self.directory / "counter").read_text(), "x")
        self.assertEqual(json.loads((self.directory / "args").read_text()),
                         [str(self.repository)])
        summary = self.summary(result)
        self.assertTrue(summary["lock_acquired"])
        self.assertTrue(summary["adapter_launched"])
        self.assertEqual(summary["classification"], "valid_completion")
        self.assertGreaterEqual(summary["runner_wall_seconds"], 0)
        self.assertEqual([phase["phase"] for phase in summary["phases"]],
                         ["refresh_pre", "finalizer_pre", "refresh_post", "finalizer_post"])
        evidence = self.repository / ".git" / "governance-runtime" / "runs.jsonl"
        self.assertEqual(len(evidence.read_text().splitlines()), 1)

    def test_finalizer_pre_pass_consumes_invocation(self):
        finalizer = self.directory / "finalizer"
        finalizer.write_text('#!/bin/sh\nprintf \'{"outcome":"finalized"}\\n\'\n')
        finalizer.chmod(finalizer.stat().st_mode | stat.S_IXUSR)
        result = self.invoke(env=self.env | {"GOVERNANCE_FINALIZER_COMMAND": str(finalizer)})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.summary(result)["classification"], "finalized_pre_pass")
        self.assertFalse((self.directory / "counter").exists())

    def test_finalizer_does_not_act_from_codex_exit_alone(self):
        result = self.invoke()
        phases = self.summary(result)["phases"]
        self.assertEqual(phases[-1]["classification"], "not_configured")

    def test_occupied_lock_skips_adapter_and_exits_cleanly(self):
        self.lock.touch()
        with self.lock.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.invoke()
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.directory / "counter").exists())
        summary = self.summary(result)
        self.assertFalse(summary["lock_acquired"])
        self.assertFalse(summary["adapter_launched"])
        self.assertEqual(summary["classification"], "lock_contended")
        self.assertEqual(self.durable.read_text(), "WORKING")

    def test_adapter_execution_failure_is_propagated(self):
        result = self.invoke(70)
        self.assertEqual(result.returncode, 70)
        self.assertEqual(self.summary(result)["classification"],
                         "adapter_execution_failure")

    def test_adapter_invalid_and_interrupted_are_propagated(self):
        for code in (65, 130):
            with self.subTest(code=code):
                result = self.invoke(code)
                self.assertEqual(result.returncode, code)
                self.assertEqual(self.summary(result)["classification"],
                                 "interrupted_invalid")
                self.assertEqual(self.durable.read_text(), "WORKING")

    def test_unknown_adapter_status_maps_to_invalid(self):
        result = self.invoke(9)
        self.assertEqual(result.returncode, 65)
        self.assertEqual(self.summary(result)["adapter_exit_status"], 9)
        self.assertEqual(self.summary(result)["classification"],
                         "interrupted_invalid")

    def test_preflight_failure_is_runtime_failure(self):
        env = self.env | {"GOVERNANCE_REPOSITORY": str(self.directory / "missing")}
        result = self.invoke(env=env)
        self.assertEqual(result.returncode, 70)
        self.assertFalse(self.summary(result)["adapter_launched"])
        self.assertEqual(self.summary(result)["classification"], "preflight_failure")

    def test_missing_adapter_and_python_are_preflight_failures(self):
        cases = (
            {"GOVERNANCE_ADAPTER": str(self.directory / "missing-adapter")},
            {"GOVERNANCE_PYTHON": str(self.directory / "missing-python")},
        )
        for override in cases:
            with self.subTest(override=override):
                result = self.invoke(env=self.env | override)
                self.assertEqual(result.returncode, 70)
                summary = self.summary(result)
                self.assertEqual(summary["classification"], "preflight_failure")
                self.assertFalse(summary["adapter_launched"])
                self.assertEqual(self.durable.read_text(), "WORKING")

    def test_interface_has_no_semantic_arguments(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--checkpoint", "GOV-999"],
            text=True, capture_output=True, env=self.env,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.directory / "counter").exists())

    def test_source_has_no_retry_or_repository_mutation_commands(self):
        source = RUNNER.read_text()
        for forbidden in ("while ", "git merge", "auto-merge", "git push", "WORK_QUEUE"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
