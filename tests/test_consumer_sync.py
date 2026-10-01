import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from sync.consumer_sync import BEGIN, END, SyncFailure, _block, plan, write_candidate


class ConsumerSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.baseline = self.root / "baseline"
        self.consumer = self.root / "consumer"
        self.baseline.mkdir()
        self.consumer.mkdir()
        subprocess.run(["git", "init", "-q", self.baseline], check=True)
        subprocess.run(["git", "-C", self.baseline, "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", self.baseline, "config", "user.name", "Test"], check=True)
        self.old = self._commit(b"old policy")
        self.new = self._commit(b"new policy")
        self.identity = "https://example.invalid/baseline.git"
        self._consumer(self.old, b"old policy")

    def tearDown(self):
        self.temp.cleanup()

    def _template(self, policy):
        return b"template\n" + BEGIN + b"\n" + policy + b"\n" + END + b"\n"

    def _commit(self, policy):
        path = self.baseline / "templates" / "AGENTS.md"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(self._template(policy))
        subprocess.run(["git", "-C", self.baseline, "add", "."], check=True)
        subprocess.run(["git", "-C", self.baseline, "commit", "-qm", policy.decode()], check=True)
        return subprocess.check_output(["git", "-C", self.baseline, "rev-parse", "HEAD"], text=True).strip()

    def _consumer(self, revision, policy):
        (self.consumer / "AGENTS.md").write_bytes(b"local before\n" + BEGIN + b"\n" + policy + b"\n" + END + b"\nlocal after\n")
        (self.consumer / ".my-own-governance.json").write_text(json.dumps({
            "baseline_repository": self.identity, "baseline_revision": revision
        }, indent=2, sort_keys=True) + "\n")
        (self.consumer / "untouched.bin").write_bytes(b"\x00consumer bytes\xff")

    def _plan(self, revision=None):
        return plan(self.baseline, self.identity, revision or self.new, self.consumer, Path(".my-own-governance.json"))

    def test_success_and_candidate_preserve_unmanaged_content(self):
        result = self._plan()
        self.assertEqual("change", result["status"])
        self.assertEqual(["AGENTS.md", ".my-own-governance.json"], result["changed_paths"])
        self.assertTrue(result["new_agents"].startswith(b"local before\n"))
        self.assertTrue(result["new_agents"].endswith(b"local after\n"))
        result.update(baseline=str(self.baseline), repository_identity=self.identity)
        candidate = self.root / "candidate"
        write_candidate(self.consumer, candidate, Path(".my-own-governance.json"), result)
        self.assertEqual(b"\x00consumer bytes\xff", (candidate / "untouched.bin").read_bytes())
        self.assertEqual("no-op", plan(self.baseline, self.identity, self.new, candidate, Path(".my-own-governance.json"))["status"])
        self.assertEqual(b"old policy", _block((self.consumer / "AGENTS.md").read_bytes(), "original")[2].splitlines()[1])

    def test_already_synchronized_is_no_op(self):
        self._consumer(self.new, b"new policy")
        self.assertEqual("no-op", self._plan()["status"])

    def test_malformed_and_ambiguous_markers_fail(self):
        bad = [b"none", BEGIN + b"\n", END + b"\n" + BEGIN, BEGIN + b"\n" + BEGIN + b"\n" + END]
        for value in bad:
            with self.subTest(value=value):
                (self.consumer / "AGENTS.md").write_bytes(value)
                with self.assertRaises(SyncFailure):
                    self._plan()

    def test_local_managed_block_divergence_fails(self):
        self._consumer(self.old, b"locally edited")
        with self.assertRaisesRegex(SyncFailure, "diverges"):
            self._plan()

    def test_provenance_mismatch_fails(self):
        record = json.loads((self.consumer / ".my-own-governance.json").read_text())
        record["baseline_repository"] = "different"
        (self.consumer / ".my-own-governance.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(SyncFailure, "identity"):
            self._plan()

    def test_failure_is_atomic(self):
        before = {p.relative_to(self.consumer): p.read_bytes() for p in self.consumer.iterdir()}
        result = self._plan()
        result.update(baseline=str(self.baseline), repository_identity="wrong")
        with self.assertRaises(SyncFailure):
            write_candidate(self.consumer, self.root / "candidate", Path(".my-own-governance.json"), result)
        self.assertFalse((self.root / "candidate").exists())
        self.assertEqual(before, {p.relative_to(self.consumer): p.read_bytes() for p in self.consumer.iterdir()})


if __name__ == "__main__":
    unittest.main()
