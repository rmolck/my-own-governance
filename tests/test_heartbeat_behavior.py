import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from validation.heartbeat_harness import NO_OP, TRANSITION_COMPLETED, evaluate, evaluate_remote


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

    def test_h07_current_approval_closes_without_merge_or_second_work(self):
        items = [checkpoint("review", "AI_REVIEW", head="b",
                            decision={"value": "AI_SUPERVISOR: APPROVED", "head": "b"}),
                 checkpoint("ready", "READY")]
        result = evaluate({"checkpoints": items})
        self.assertEqual(result["transition"], ["AI_REVIEW", "DONE"])
        self.assertFalse(result["merge"])
        self.assertEqual(items[1]["state"], "READY")

    def test_h08_stale_approval_does_not_close_new_head(self):
        self.assert_no_op([checkpoint("review", "AI_REVIEW", head="head-b",
                                      decision={"value": "AI_SUPERVISOR: APPROVED",
                                                "head": "head-a"})])

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

    def test_h12_fresh_remote_state_overrides_stale_checkout_and_memories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "durable.git"
            writer = root / "writer"
            subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
            subprocess.run(["git", "clone", "--quiet", str(remote), str(writer)], check=True)
            subprocess.run(["git", "-C", str(writer), "config", "user.name", "Fixture"], check=True)
            subprocess.run(["git", "-C", str(writer), "config", "user.email", "fixture@example.invalid"], check=True)
            stale = {"checkpoints": [checkpoint("stale-ready", "READY")],
                     "previous_output": "work was once authorized",
                     "example": "READY", "agent_memory": "select stale-ready"}
            path = writer / "heartbeat-state.json"
            path.write_text(json.dumps(stale))
            subprocess.run(["git", "-C", str(writer), "add", "."], check=True)
            subprocess.run(["git", "-C", str(writer), "commit", "--quiet", "-m", "stale"], check=True)
            subprocess.run(["git", "-C", str(writer), "push", "--quiet", "origin", "HEAD:main"], check=True)
            subprocess.run(["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
            stale_checkout = root / "stale"
            subprocess.run(["git", "clone", "--quiet", str(remote), str(stale_checkout)], check=True)
            path.write_text(json.dumps({"checkpoints": [checkpoint("durable", "DONE")]}))
            subprocess.run(["git", "-C", str(writer), "commit", "--quiet", "-am", "fresh"], check=True)
            subprocess.run(["git", "-C", str(writer), "push", "--quiet", "origin", "HEAD:main"], check=True)
            self.assertEqual(json.loads((stale_checkout / "heartbeat-state.json").read_text())
                             ["checkpoints"][0]["state"], "READY")
            state, result = evaluate_remote(remote)
            self.assertEqual(state["checkpoints"][0]["state"], "DONE")
            self.assertEqual(result["outcome"], NO_OP)

    def test_h12_unresolvable_durable_state_is_execution_failure_not_no_op(self):
        with self.assertRaisesRegex(RuntimeError, "durable state unavailable"):
            evaluate_remote(Path("/definitely/missing/durable.git"))

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

    def test_h17_closure_is_only_principal_transition(self):
        items = [checkpoint("approved", "AI_REVIEW", head="x",
                            decision={"value": "AI_SUPERVISOR: APPROVED", "head": "x"}),
                 checkpoint("next", "READY")]
        result = evaluate({"checkpoints": items})
        self.assertEqual(result["checkpoint"], "approved")
        self.assertEqual(items[1]["state"], "READY")

    def test_h18_only_one_pr_even_when_two_reworks_are_possible(self):
        items = [checkpoint("first", "AI_REWORK", pr=1), checkpoint("second", "AI_REWORK", pr=2)]
        result = evaluate({"checkpoints": items})
        self.assertEqual((result["checkpoint"], result["pr"]), ("first", 1))
        self.assertEqual(items[1]["state"], "AI_REWORK")


if __name__ == "__main__":
    unittest.main()
