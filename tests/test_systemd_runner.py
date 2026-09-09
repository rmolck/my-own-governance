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
                         ["refresh_pre", "finalizer_pre", "host_post_worker"])
        evidence = self.repository / ".git" / "governance-runtime" / "runs.jsonl"
        self.assertEqual(len(evidence.read_text().splitlines()), 1)

    def test_finalizer_pre_pass_refreshes_then_invokes_worker_once(self):
        order = self.directory / "order"
        refresh = self.phase_script("refresh", f'echo refresh >> "{order}"\n')
        finalizer = self.phase_script(
            "finalizer", f'echo finalizer >> "{order}"\nprintf \'{{"outcome":"finalized"}}\\n\'\n')
        result = self.invoke(env=self.env | {
            "GOVERNANCE_REFRESH_ARGV": json.dumps([str(refresh)]),
            "GOVERNANCE_FINALIZER_ARGV": json.dumps([str(finalizer)]),
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual((self.directory / "counter").read_text(), "x")
        self.assertEqual(order.read_text().splitlines(),
                         ["refresh", "finalizer", "refresh"])
        self.assertEqual([phase["phase"] for phase in self.summary(result)["phases"]],
                         ["refresh_pre", "finalizer_pre", "refresh_after_finalization",
                          "host_post_worker"])

    def test_worker_completion_never_triggers_finalizer_post_pass(self):
        count = self.directory / "finalizer-count"
        finalizer = self.phase_script(
            "finalizer", f'echo x >> "{count}"\nprintf \'{{"outcome":"ineligible"}}\\n\'\n')
        result = self.invoke(env=self.env | {"GOVERNANCE_FINALIZER_ARGV": json.dumps([str(finalizer)])})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(count.read_text().splitlines(), ["x"])
        self.assertEqual([phase["phase"] for phase in self.summary(result)["phases"]],
                         ["refresh_pre", "finalizer_pre", "host_post_worker"])

    def test_host_post_worker_runs_after_worker(self):
        observation = self.directory / "host-observation"
        host = self.phase_script(
            "host-post-worker",
            f'test -f "{self.directory / "counter"}"\n'
            f'printf reconciled > "{observation}"\n',
        )
        result = self.invoke(env=self.env | {
            "GOVERNANCE_HOST_POST_WORKER_ARGV": json.dumps([str(host)]),
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(observation.read_text(), "reconciled")
        self.assertEqual(self.summary(result)["phases"][-1], {
            "phase": "host_post_worker", "exit_status": 0,
            "classification": "completed",
        })

    def test_host_post_worker_failure_overrides_worker_success(self):
        host = self.phase_script("host-post-worker", "exit 9\n")
        result = self.invoke(env=self.env | {
            "GOVERNANCE_HOST_POST_WORKER_ARGV": json.dumps([str(host)]),
        })
        self.assertEqual(result.returncode, 70)
        summary = self.summary(result)
        self.assertEqual(summary["classification"], "runner_internal_failure")
        self.assertEqual(summary["technical_error"], "host_post_worker failed")
        self.assertEqual(summary["phases"][-1]["classification"], "child_nonzero")

    def phase_script(self, name, body):
        script = self.directory / name
        script.write_text("#!/bin/sh\n" + body)
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        return script

    def test_failed_refresh_after_finalization_skips_worker(self):
        refresh = self.phase_script("refresh", f'test -f "{self.directory / "refreshed"}" && exit 8\n'
                                    f'touch "{self.directory / "refreshed"}"\n')
        finalizer = self.phase_script("finalizer", 'printf \'{"outcome":"finalized"}\\n\'\n')
        result = self.invoke(env=self.env | {
            "GOVERNANCE_REFRESH_ARGV": json.dumps([str(refresh)]),
            "GOVERNANCE_FINALIZER_ARGV": json.dumps([str(finalizer)]),
        })
        self.assertEqual(result.returncode, 70)
        summary = self.summary(result)
        self.assertEqual(summary["classification"], "preflight_failure")
        self.assertEqual(summary["technical_error"], "refresh_after_finalization failed")
        self.assertFalse((self.directory / "counter").exists())

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

    def test_phase_requires_structured_argv(self):
        result = self.invoke(env=self.env | {"GOVERNANCE_REFRESH_ARGV": "/bin/true"})
        self.assertEqual(result.returncode, 70)
        self.assertEqual(self.summary(result)["classification"], "preflight_failure")

    def test_missing_phase_executable_is_distinct_launch_failure(self):
        result = self.invoke(env=self.env | {
            "GOVERNANCE_REFRESH_ARGV": json.dumps([str(self.directory / "missing")]),
        })
        self.assertEqual(result.returncode, 70)
        self.assertEqual(self.summary(result)["phases"][0]["classification"],
                         "launch_failure")

    def test_source_has_no_retry_or_repository_mutation_commands(self):
        source = RUNNER.read_text()
        for forbidden in ("while ", "git merge", "auto-merge", "git push", "WORK_QUEUE"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
