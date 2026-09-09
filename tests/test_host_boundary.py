import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from runtime.host_boundary import (reconcile_identity, recovery_action, run_process,
                                   validate_git_state)


class HostBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-b", "gov-010", self.repo], check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        (self.repo / "allowed").mkdir()
        (self.repo / "allowed" / "tracked.txt").write_text("base\n")
        (self.repo / "other.txt").write_text("base\n")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.repo, check=True,
                       capture_output=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_git_state_classifies_clean_expected_and_unexpected_paths(self):
        self.assertEqual(validate_git_state(self.repo, "gov-010", ["allowed"]).classification,
                         "clean")
        (self.repo / "allowed" / "tracked.txt").write_text("changed\n")
        (self.repo / "allowed" / "new.txt").write_text("new\n")
        state = validate_git_state(self.repo, "gov-010", ["allowed"])
        self.assertTrue(state.publishable)
        self.assertEqual(state.classification, "expected_modifications")
        self.assertEqual(set(state.expected_changes),
                         {"allowed/tracked.txt", "allowed/new.txt"})
        (self.repo / "other.txt").write_text("changed\n")
        self.assertEqual(validate_git_state(self.repo, "gov-010", ["allowed"]).classification,
                         "unexpected_tracked_modifications")
        subprocess.run(["git", "restore", "other.txt"], cwd=self.repo, check=True)
        (self.repo / "surprise.txt").write_text("new\n")
        self.assertEqual(validate_git_state(self.repo, "gov-010", ["allowed"]).classification,
                         "unexpected_untracked_paths")

    def test_git_state_fails_closed_on_branch_mismatch(self):
        state = validate_git_state(self.repo, "different", ["allowed"])
        self.assertFalse(state.publishable)
        self.assertEqual(state.classification, "branch_ref_mismatch")

    def test_existing_durable_identity_wins_and_new_identity_is_derived_once(self):
        preserved = reconcile_identity(durable_branch="real", durable_pr=15,
                                       local_branch=None, derived_branch="derived",
                                       remote_branches=["real"])
        self.assertEqual(preserved.classification, "preserved_durable_identity")
        self.assertFalse(preserved.should_derive)
        new = reconcile_identity(durable_branch=None, durable_pr=None, local_branch=None,
                                 derived_branch="derived", remote_branches=[])
        self.assertEqual(new.classification, "new_identity")
        self.assertTrue(new.should_derive)

    def test_unverified_existing_branch_fails_closed(self):
        result = reconcile_identity(durable_branch=None, durable_pr=None,
                                    local_branch="derived", derived_branch="derived",
                                    remote_branches=["derived"])
        self.assertEqual(result.classification, "unverified_existing_remote_identity")
        self.assertFalse(result.should_derive)

    def test_recovery_prefers_durable_results_over_stale_local_result(self):
        self.assertEqual(recovery_action(durable_state="AI_REVIEW", branch_exists=True,
                                         pr_exists=True, worker_result_complete=False),
                         "reconciled_no_action")
        self.assertEqual(recovery_action(durable_state="WORKING", branch_exists=True,
                                         pr_exists=True, worker_result_complete=False),
                         "reconcile_existing_publication")
        self.assertEqual(recovery_action(durable_state="WORKING", branch_exists=True,
                                         pr_exists=False, worker_result_complete=False),
                         "reconcile_existing_publication")

    def test_process_boundary_has_no_shell_and_distinguishes_failures(self):
        marker = self.repo / "marker"
        result = run_process(["printf", "%s", f"value;touch {marker}"], self.repo)
        self.assertEqual(result.classification, "completed")
        self.assertFalse(marker.exists())
        child = run_process(["sh", "-c", "exit 7"], self.repo)
        self.assertEqual((child.classification, child.exit_status), ("child_nonzero", 7))
        launch = run_process([str(self.repo / "missing")], self.repo)
        self.assertEqual((launch.classification, launch.exit_status),
                         ("launch_failure", None))

    def test_process_output_is_utf8_text_and_bounded(self):
        result = run_process(["python3", "-c", "print('x' * 50)"], self.repo,
                             output_limit=10)
        self.assertEqual(result.stdout, "x" * 10)
        json.dumps(result.__dict__)


if __name__ == "__main__":
    unittest.main()
