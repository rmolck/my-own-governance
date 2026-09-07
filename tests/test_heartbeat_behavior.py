import json
from pathlib import Path
import subprocess
from unittest import mock
import tempfile
import unittest

from validation.heartbeat_harness import (
    FreshnessError,
    NO_OP,
    TRANSITION_COMPLETED,
    evaluate,
    evaluate_fresh_checkout,
)


def checkpoint(identifier, state, gate="AI", **extra):
    return {"id": identifier, "state": state, "gate": gate} | extra


class HeartbeatSemanticsTest(unittest.TestCase):
    def assert_no_op(self, checkpoints):
        before = json.dumps(checkpoints, sort_keys=True)
        result = evaluate({"checkpoints": checkpoints})
        self.assertEqual(result["outcome"], NO_OP)
        self.assertIsNone(result["transition"])
        self.assertFalse(result["merge"])
        self.assertEqual(json.dumps(checkpoints, sort_keys=True), before)

    def test_h01_no_authorized_work_is_no_op_without_mutation(self):
        self.assert_no_op([checkpoint("C1", "DONE"), checkpoint("C2", "AI_REVIEW")])

    def test_h02_ready_ai_selects_only_one(self):
        items = [checkpoint("C1", "READY"), checkpoint("C2", "READY")]
        result = evaluate({"checkpoints": items})
        self.assertEqual(result["outcome"], TRANSITION_COMPLETED)
        self.assertEqual(result["checkpoint"], "C1")
        self.assertEqual(result["transition"], ["READY", "WORKING"])
        self.assertEqual(items[1]["state"], "READY")

    def test_h03_ready_human_is_no_op(self):
        self.assert_no_op([checkpoint("C1", "READY", "HUMAN")])

    def test_h04_ai_rework_precedes_ready_ai(self):
        items = [checkpoint("ready", "READY"), checkpoint("rework", "AI_REWORK", pr=4)]
        result = evaluate({"checkpoints": items})
        self.assertEqual((result["checkpoint"], result["transition"]),
                         ("rework", ["AI_REWORK", "WORKING"]))
        self.assertEqual(items[0]["state"], "READY")

    def test_h05_working_preserves_existing_pr_and_head(self):
        item = checkpoint("active", "WORKING", pr=8, head="branch-head-b",
                          baseline="new-main")
        result = evaluate({"checkpoints": [item]})
        self.assertEqual(result["outcome"], "continued")
        self.assertEqual((result["pr"], result["head"]), (8, "branch-head-b"))
        self.assertIsNone(result["transition"])

    def test_h06_ai_review_without_decision_is_no_op(self):
        self.assert_no_op([checkpoint("review", "AI_REVIEW", head="b")])

    def test_h07_current_approval_semantically_completes_and_authorizes_merge(self):
        items = [checkpoint("review", "AI_REVIEW", head="b",
                            pr=7, decision={"value": "AI_SUPERVISOR: APPROVED",
                                            "head": "b", "pr": 7}),
                 checkpoint("ready", "READY")]
        result = evaluate({"checkpoints": items})
        self.assertIsNone(result["transition"])
        self.assertTrue(result["semantic_done"])
        self.assertTrue(result["merge_authorized"])
        self.assertTrue(result["merge"])
        self.assertEqual(items[0]["state"], "DONE")
        self.assertEqual(items[1]["state"], "READY")

    def test_h08_stale_approval_does_not_close_new_head(self):
        self.assert_no_op([checkpoint("review", "AI_REVIEW", head="head-b",
                                      decision={"value": "AI_SUPERVISOR: APPROVED",
                                                "head": "head-a"})])

    def test_h08_mechanical_closure_from_approved_head_preserves_authorization(self):
        item = checkpoint(
            "review", "AI_REVIEW", head="closure-head", approved_base="head-a", pr=8,
            closure_parent="head-a", closure_files=["docs/WORK_QUEUE.md"],
            closure_changes=[
                {"checkpoint": "review", "field": "state",
                 "before": "AI_REVIEW", "after": "DONE"},
                {"checkpoint": "review", "field": "last_relevant_result",
                 "after": {"decision": "AI_SUPERVISOR: APPROVED", "head": "head-a"}},
            ],
            decision={"value": "AI_SUPERVISOR: APPROVED", "head": "head-a", "pr": 8},
        )
        result = evaluate({"checkpoints": [item]})
        self.assertTrue(result["merge_authorized"])
        self.assertTrue(result["merge"])

    def test_h08_non_allowlisted_closure_invalidates_authorization(self):
        for path in ("src/code.py", "tests/test_code.py", "docs/AUTONOMY.md",
                     "docs/DECISIONS.md"):
            with self.subTest(path=path):
                item = checkpoint(
                    "review", "AI_REVIEW", head="head-b", approved_base="head-a", pr=8,
                    closure_parent="head-a", closure_files=["docs/WORK_QUEUE.md", path],
                    closure_changes=[{"checkpoint": "review", "field": "state",
                                      "before": "AI_REVIEW", "after": "DONE"}],
                    decision={"value": "AI_SUPERVISOR: APPROVED", "head": "head-a", "pr": 8},
                )
                result = evaluate({"checkpoints": [item]})
                self.assertTrue(result["semantic_done"])
                self.assertFalse(result["merge_authorized"])
                self.assertFalse(result["merge"])

    def test_h08_queue_only_substantive_closure_invalidates_authorization(self):
        forbidden_changes = (
            {"checkpoint": "other", "field": "state",
             "before": "READY", "after": "WORKING"},
            {"checkpoint": "review", "field": "priority", "after": 1},
            {"checkpoint": "review", "field": "gate", "after": "HUMAN"},
            {"checkpoint": "review", "field": "objective", "after": "different work"},
            {"checkpoint": "review", "field": "dependencies", "after": []},
            {"checkpoint": "review", "field": "last_relevant_result",
             "after": {"decision": "unverified", "head": "head-a"}},
        )
        valid_state_change = {"checkpoint": "review", "field": "state",
                              "before": "AI_REVIEW", "after": "DONE"}
        for forbidden in forbidden_changes:
            with self.subTest(field=forbidden["field"], checkpoint=forbidden["checkpoint"]):
                item = checkpoint(
                    "review", "AI_REVIEW", head="closure-head", approved_base="head-a", pr=8,
                    closure_parent="head-a", closure_files=["docs/WORK_QUEUE.md"],
                    closure_changes=[valid_state_change, forbidden],
                    decision={"value": "AI_SUPERVISOR: APPROVED", "head": "head-a", "pr": 8},
                )
                result = evaluate({"checkpoints": [item]})
                self.assertTrue(result["semantic_done"])
                self.assertFalse(result["merge_authorized"])
                self.assertFalse(result["merge"])

    def test_h08_gate_human_never_receives_delegated_merge(self):
        item = checkpoint("review", "AI_REVIEW", "HUMAN", head="a",
                          decision={"value": "AI_SUPERVISOR: APPROVED", "head": "a"})
        self.assert_no_op([item])

    def test_h08_later_rework_or_human_required_invalidates_approval(self):
        for later in ("AI_SUPERVISOR: AI_REWORK", "AI_SUPERVISOR: HUMAN_REQUIRED"):
            with self.subTest(later=later):
                item = checkpoint("review", "AI_REVIEW", head="a", decisions=[
                    {"value": "AI_SUPERVISOR: APPROVED", "head": "a"},
                    {"value": later, "head": "a"},
                ])
                self.assert_no_op([item])

    def test_h08_merge_preconditions_pause_mechanics_without_blocking(self):
        for field in ("mergeable", "checks_satisfied", "legitimate_pr"):
            with self.subTest(field=field):
                item = checkpoint("review", "AI_REVIEW", head="a",
                                  decision={"value": "AI_SUPERVISOR: APPROVED", "head": "a"},
                                  **{field: False})
                result = evaluate({"checkpoints": [item]})
                self.assertEqual(item["state"], "AI_REVIEW")
                self.assertNotEqual(item["state"], "BLOCKED")
                self.assertFalse(result["merge"])
                self.assertFalse(result["auto_merge"])

    def test_h09_human_required_without_independent_work_is_no_op(self):
        self.assert_no_op([checkpoint("human", "HUMAN_REQUIRED", "HUMAN")])

    def test_h10_persistent_blocked_is_no_op(self):
        self.assert_no_op([checkpoint("blocked", "BLOCKED", cause_resolved=False)])

    def test_h11_resolved_block_only_uses_recorded_ready_or_working(self):
        for state, expected in (("READY", ["READY", "WORKING"]), ("WORKING", None)):
            with self.subTest(state=state):
                result = evaluate({"checkpoints": [checkpoint("resumed", state,
                                                               resolution="durably recorded")]})
                self.assertEqual(result["transition"], expected)

    def make_stale_remote_fixture(self, root):
        remote = root / "durable.git"
        writer = root / "writer"
        checkout = root / "stale"
        subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
        subprocess.run(
            ["git", "clone", "--quiet", str(remote), str(writer)], check=True
        )
        for key, value in (("user.name", "Fixture"),
                           ("user.email", "fixture@example.invalid")):
            subprocess.run(
                ["git", "-C", str(writer), "config", key, value], check=True
            )
        stale = {"checkpoints": [checkpoint("stale-ready", "READY")],
                 "previous_output": "work was once authorized",
                 "example": "READY", "agent_memory": "select stale-ready"}
        path = writer / "heartbeat-state.json"
        path.write_text(json.dumps(stale))
        subprocess.run(["git", "-C", str(writer), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(writer), "commit", "--quiet", "-m", "stale"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(writer), "push", "--quiet", "origin", "HEAD:main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"],
            check=True,
        )
        subprocess.run(["git", "clone", "--quiet", str(remote), str(checkout)], check=True)
        path.write_text(json.dumps({"checkpoints": [checkpoint("durable", "DONE")]}))
        subprocess.run(
            ["git", "-C", str(writer), "commit", "--quiet", "-am", "fresh"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(writer), "push", "--quiet", "origin", "HEAD:main"],
            check=True,
        )
        return remote, checkout

    def test_h12_updates_stale_remote_tracking_ref_before_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            _, checkout = self.make_stale_remote_fixture(Path(directory))
            stale_sha = subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "refs/remotes/origin/main"],
                text=True,
            ).strip()
            evidence, result = evaluate_fresh_checkout(checkout)
            self.assertEqual(evidence["local_before"], stale_sha)
            self.assertNotEqual(evidence["remote_sha"], stale_sha)
            self.assertEqual(evidence["local_after"], evidence["remote_sha"])
            self.assertEqual(result["outcome"], NO_OP)

    def test_h12_unreachable_remote_is_execution_failure_without_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            _, checkout = self.make_stale_remote_fixture(Path(directory))
            subprocess.run(["git", "-C", str(checkout), "remote", "set-url", "origin",
                            str(Path(directory) / "missing.git")], check=True)
            with mock.patch("validation.heartbeat_harness.evaluate") as selection:
                with self.assertRaisesRegex(FreshnessError, "git ls-remote"):
                    evaluate_fresh_checkout(checkout)
                selection.assert_not_called()

    def test_h12_directed_fetch_failure_does_not_use_stale_ref(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            operation = command[3]
            if operation == "ls-remote":
                return subprocess.CompletedProcess(
                    command, 0, "b" * 40 + "\trefs/heads/main\n", ""
                )
            if operation == "rev-parse":
                return subprocess.CompletedProcess(command, 0, "a" * 40 + "\n", "")
            return subprocess.CompletedProcess(command, 1, "", "simulated fetch denial")
        with mock.patch("validation.heartbeat_harness.evaluate") as selection:
            with self.assertRaisesRegex(FreshnessError, "git fetch"):
                evaluate_fresh_checkout(Path("fixture"), runner)
            selection.assert_not_called()
        self.assertTrue(
            any("+refs/heads/main:refs/remotes/origin/main" in c for c in calls)
        )

    def test_h12_unupdated_tracking_ref_mismatch_prevents_selection(self):
        remote_sha, stale_sha = "b" * 40, "a" * 40
        rev_parse_count = 0
        def runner(command, **kwargs):
            nonlocal rev_parse_count
            operation = command[3]
            if operation == "ls-remote":
                return subprocess.CompletedProcess(command, 0,
                                                   f"{remote_sha}\trefs/heads/main\n", "")
            if operation == "fetch":
                return subprocess.CompletedProcess(command, 0, "", "")
            if operation == "rev-parse":
                rev_parse_count += 1
                return subprocess.CompletedProcess(command, 0, stale_sha + "\n", "")
            self.fail("durable state was read before freshness was established")
        with mock.patch("validation.heartbeat_harness.evaluate") as selection:
            with self.assertRaisesRegex(FreshnessError, "origin/main mismatch"):
                evaluate_fresh_checkout(Path("fixture"), runner)
            selection.assert_not_called()
        self.assertEqual(rev_parse_count, 2)

    def test_h13_pr_continuity_wins_after_baseline_advance(self):
        result = evaluate({"checkpoints": [checkpoint("existing", "WORKING", pr=13,
                                                      head="pr-head", baseline="advanced"),
                                           checkpoint("replacement", "READY")]})
        self.assertEqual((result["checkpoint"], result["pr"]), ("existing", 13))

    def test_published_priority_order_is_exact_for_actionable_entries(self):
        approval = {"value": "AI_SUPERVISOR: APPROVED", "head": "approved-head"}
        layers = [
            checkpoint("rework", "AI_REWORK"),
            checkpoint("closure", "AI_REVIEW", head="approved-head", decision=approval),
            checkpoint("working", "WORKING", pr=3),
            checkpoint("ready-ai", "READY"),
            checkpoint("ready-human", "READY", "HUMAN"),
            checkpoint("review", "AI_REVIEW"),
            checkpoint("human", "HUMAN_REQUIRED", "HUMAN"),
            checkpoint("blocked", "BLOCKED"),
        ]
        expected = ["rework", "closure", "working", "ready-ai"]
        for offset, selected in enumerate(expected):
            with self.subTest(selected=selected):
                fixture = json.loads(json.dumps({"checkpoints": layers[offset:]}))
                self.assertEqual(evaluate(fixture)["checkpoint"], selected)
        for offset in range(4, len(layers)):
            with self.subTest(no_op_from=layers[offset]["id"]):
                fixture = json.loads(json.dumps({"checkpoints": layers[offset:]}))
                self.assertEqual(evaluate(fixture)["outcome"], NO_OP)

    def test_h17_finalization_is_not_a_transition_or_second_selection(self):
        items = [checkpoint("approved", "AI_REVIEW", head="x",
                            decision={"value": "AI_SUPERVISOR: APPROVED", "head": "x"}),
                 checkpoint("next", "READY")]
        result = evaluate({"checkpoints": items})
        self.assertEqual(result["checkpoint"], "approved")
        self.assertIsNone(result["transition"])
        self.assertTrue(result["semantic_done"])
        self.assertEqual(items[1]["state"], "READY")

    def test_h17_finalizer_does_not_decide_gate_or_reserved_authority(self):
        for extra in ({"gate": "HUMAN"}, {"human_reserved": True}):
            item = checkpoint("review", "AI_REVIEW", head="x",
                              decision={"value": "AI_SUPERVISOR: APPROVED", "head": "x"},
                              **extra)
            result = evaluate({"checkpoints": [item]})
            self.assertFalse(result["merge"])
            self.assertFalse(result["auto_merge"])

    def test_h18_only_one_pr_even_when_two_reworks_are_possible(self):
        items = [checkpoint("first", "AI_REWORK", pr=1), checkpoint("second", "AI_REWORK", pr=2)]
        result = evaluate({"checkpoints": items})
        self.assertEqual((result["checkpoint"], result["pr"]), ("first", 1))
        self.assertEqual(items[1]["state"], "AI_REWORK")


if __name__ == "__main__":
    unittest.main()
