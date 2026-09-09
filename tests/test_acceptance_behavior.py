import copy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

from validation.acceptance_harness import AcceptanceProtocol
from validation.heartbeat_harness import FreshnessError, NO_OP, evaluate_fresh_checkout
from validation.supervisor_harness import (
    AI_REWORK, APPROVED, HUMAN_REQUIRED, SupervisorExecutionError,
    approval_valid_for_head,
)


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapter" / "codex_execution_adapter.py"
RUNNER = ROOT / "runtime" / "systemd_runner.py"
HEAD_A, HEAD_B = "a" * 40, "b" * 40


def checkpoint(identifier="GOV-008", state="READY", gate="AI", **values):
    return {"id": identifier, "state": state, "gate": gate} | values


def evidence(**values):
    result = {
        "diff_observed": True, "scope_conformant": True,
        "governance_consistent": True,
        "tests": {"required": True, "status": "passed", "evidence": "deterministic suite"},
        "checks_required": True, "checks_satisfied": True,
        "mergeability_required": True, "mergeable": True,
    }
    result.update(values)
    return result


def valid_closure(identifier="GOV-008", parent=HEAD_A):
    return {
        "head": "c" * 40, "parent": parent, "files": ["docs/WORK_QUEUE.md"],
        "checkpoint": identifier,
        "changes": [
            {"checkpoint": identifier, "field": "state",
             "before": "AI_REVIEW", "after": "DONE"},
            {"checkpoint": identifier, "field": "last_relevant_result",
             "after": {"decision": APPROVED, "head": parent}},
        ],
    }


class AcceptanceProtocolTest(unittest.TestCase):
    def test_a1_gate_ai_happy_path_composes_every_layer(self):
        protocol = AcceptanceProtocol([
            checkpoint(branch="gov-008", pr=12, head=HEAD_A),
            checkpoint("GOV-009", branch="later", pr=13, head=HEAD_B),
        ])
        selection = protocol.heartbeat()
        self.assertEqual(selection["transition"], ["READY", "WORKING"])
        protocol.worker_result(technically_completed=True, valid_outcome=True)
        self.assertEqual(protocol.checkpoint("GOV-008")["state"], "AI_REVIEW")
        decision = protocol.supervise(evidence())
        self.assertEqual(decision.value, APPROVED)
        self.assertTrue(approval_valid_for_head(decision, HEAD_A))
        closed = protocol.closure(decision, valid_closure())
        self.assertTrue(closed["protocol_accepts_closure"])
        self.assertTrue(closed["merge"])
        self.assertEqual(protocol.checkpoint("GOV-008")["state"], "DONE")
        self.assertFalse(closed["auto_merge"])
        self.assertEqual(protocol.checkpoint("GOV-009")["state"], "READY")
        self.assertEqual(protocol.principal_units, 1)

    def test_a2_rework_continues_same_pr_and_invalidates_old_head(self):
        protocol = AcceptanceProtocol([checkpoint(branch="gov-008", pr=12, head=HEAD_A)])
        protocol.heartbeat(); protocol.worker_result(True, True)
        rework = protocol.supervise(evidence(scope_conformant=False))
        self.assertEqual(rework.value, AI_REWORK)
        resumed = protocol.heartbeat()
        self.assertEqual((resumed["checkpoint"], resumed["transition"]),
                         ("GOV-008", ["AI_REWORK", "WORKING"]))
        protocol.checkpoint("GOV-008")["head"] = HEAD_B
        protocol.worker_result(True, True)
        approved = protocol.supervise(evidence())
        self.assertEqual((approved.value, approved.pr), (APPROVED, 12))
        self.assertFalse(approval_valid_for_head(approved, HEAD_A))
        self.assertTrue(approval_valid_for_head(approved, HEAD_B))

    def test_a3_gate_human_never_reaches_done_or_merge(self):
        protocol = AcceptanceProtocol([
            checkpoint(state="AI_REVIEW", gate="HUMAN", branch="human", pr=12, head=HEAD_A)
        ])
        protocol.selected = "GOV-008"
        decision = protocol.supervise(evidence())
        self.assertEqual(decision.value, HUMAN_REQUIRED)
        self.assertFalse(decision.merge_authorized)
        self.assertEqual(protocol.checkpoint("GOV-008")["state"], "HUMAN_REQUIRED")
        self.assertEqual(protocol.heartbeat()["outcome"], NO_OP)

    def test_a4_head_race_publishes_no_decision_or_authority(self):
        protocol = AcceptanceProtocol([
            checkpoint(state="AI_REVIEW", branch="gov-008", pr=12, head=HEAD_A)
        ])
        protocol.selected = "GOV-008"
        with self.assertRaises(SupervisorExecutionError):
            protocol.supervise(evidence(), lambda: HEAD_B)
        self.assertNotIn("decisions", protocol.checkpoint("GOV-008"))
        self.assertEqual(protocol.heartbeat()["outcome"], NO_OP)

    def test_a5_invalid_closures_fail_both_boundary_checks(self):
        variants = {
            "checkpoint": valid_closure("GOV-OTHER"),
            "file": valid_closure() | {"files": ["docs/WORK_QUEUE.md", "docs/AUTONOMY.md"]},
            "substantive": valid_closure() | {"changes": [
                {"checkpoint": "GOV-008", "field": "state", "before": "AI_REVIEW", "after": "DONE"},
                {"checkpoint": "GOV-008", "field": "objective", "after": "different"}]},
            "parent": valid_closure(parent=HEAD_B),
            "metadata": valid_closure() | {"changes": [
                {"checkpoint": "GOV-008", "field": "state", "before": "AI_REVIEW", "after": "DONE"},
                {"checkpoint": "GOV-008", "field": "priority", "after": 1}]},
        }
        for name, closure in variants.items():
            with self.subTest(name=name):
                protocol = AcceptanceProtocol([
                    checkpoint(state="AI_REVIEW", branch="gov-008", pr=12, head=HEAD_A)
                ])
                protocol.selected = "GOV-008"
                decision = protocol.supervise(evidence())
                result = protocol.closure(decision, closure)
                self.assertFalse(result["protocol_accepts_closure"])
                self.assertFalse(result["merge"])
                self.assertNotEqual(protocol.checkpoint("GOV-008")["state"], "DONE")

    def test_a6_adapter_and_runtime_failures_do_not_create_semantic_outcomes(self):
        protocol = AcceptanceProtocol([checkpoint(state="WORKING")])
        protocol.selected = "GOV-008"
        before = copy.deepcopy(protocol.checkpoints)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"; (repo / ".git").mkdir(parents=True)
            adapter = subprocess.run(
                [sys.executable, str(ADAPTER), str(repo), "--codex-executable",
                 str(Path(directory) / "missing")], capture_output=True, text=True)
            self.assertEqual((adapter.returncode, json.loads(adapter.stdout)["classification"]),
                             (70, "execution_failure"))
            fake = Path(directory) / "adapter"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "print(json.dumps({'technical_error': 'failure'}))\n"
                "raise SystemExit(70)\n"
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            recovery = Path(directory) / "recovery"
            recovery.write_text(
                "#!/bin/sh\nprintf '{\"action\":\"invoke_worker\"}\\n'\n"
            )
            recovery.chmod(recovery.stat().st_mode | stat.S_IXUSR)
            env = os.environ | {"GOVERNANCE_REPOSITORY": str(repo),
                                "GOVERNANCE_ADAPTER": str(fake),
                                "GOVERNANCE_PYTHON": sys.executable,
                                "GOVERNANCE_RECOVERY_ARGV": json.dumps([str(recovery)]),
                                "GOVERNANCE_LOCK_FILE": str(Path(directory) / "lock")}
            runtime = subprocess.run([sys.executable, str(RUNNER)], env=env,
                                     capture_output=True, text=True)
            self.assertEqual((runtime.returncode, json.loads(runtime.stdout)["classification"]),
                             (70, "adapter_execution_failure"))
        protocol.worker_result(technically_completed=False, valid_outcome=False)
        self.assertEqual(protocol.checkpoints, before)
        self.assertNotIn(protocol.checkpoint("GOV-008")["state"],
                         ("BLOCKED", "HUMAN_REQUIRED"))
        self.assertNotIn("decisions", protocol.checkpoint("GOV-008"))

    def test_a7_no_op_is_exact_and_has_no_semantic_mutation(self):
        protocol = AcceptanceProtocol([checkpoint(state="DONE")])
        before = copy.deepcopy(protocol.checkpoints)
        self.assertEqual(protocol.heartbeat()["outcome"], "NO_OP")
        self.assertEqual(protocol.checkpoints, before)

    def test_a8_objectively_blocked_remains_distinct_from_runtime_failure(self):
        protocol = AcceptanceProtocol([
            checkpoint(state="BLOCKED", dependency="unavailable", cause_resolved=False)
        ])
        before = copy.deepcopy(protocol.checkpoints)
        self.assertEqual(protocol.heartbeat()["outcome"], NO_OP)
        self.assertEqual(protocol.checkpoints, before)
        self.assertEqual(protocol.checkpoint("GOV-008")["state"], "BLOCKED")

    def test_a9_stale_remote_is_refreshed_and_failure_never_selects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); remote = root / "remote.git"; writer = root / "writer"
            subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
            subprocess.run(["git", "clone", "--quiet", str(remote), str(writer)], check=True)
            subprocess.run(["git", "-C", str(writer), "config", "user.name", "Fixture"], check=True)
            subprocess.run(["git", "-C", str(writer), "config", "user.email", "fixture@example.invalid"], check=True)
            state = writer / "heartbeat-state.json"
            state.write_text(json.dumps({"checkpoints": [checkpoint("STALE")]}))
            subprocess.run(["git", "-C", str(writer), "add", "."], check=True)
            subprocess.run(["git", "-C", str(writer), "commit", "--quiet", "-m", "stale"], check=True)
            subprocess.run(["git", "-C", str(writer), "push", "--quiet", "origin", "HEAD:main"], check=True)
            subprocess.run(["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
            stale = root / "stale"; subprocess.run(["git", "clone", "--quiet", str(remote), str(stale)], check=True)
            state.write_text(json.dumps({"checkpoints": [checkpoint("FRESH", state="DONE")]}))
            subprocess.run(["git", "-C", str(writer), "commit", "--quiet", "-am", "fresh"], check=True)
            subprocess.run(["git", "-C", str(writer), "push", "--quiet", "origin", "HEAD:main"], check=True)
            freshness, result = evaluate_fresh_checkout(stale)
            self.assertNotEqual(freshness["local_before"], freshness["remote_sha"])
            self.assertEqual(freshness["local_after"], freshness["remote_sha"])
            self.assertEqual(result["outcome"], NO_OP)
            subprocess.run(["git", "-C", str(stale), "remote", "set-url", "origin",
                            str(root / "missing")], check=True)
            with self.assertRaises(FreshnessError):
                evaluate_fresh_checkout(stale)

    def test_a10_reserved_authority_never_emerges_from_composition(self):
        reserved = ("gate-human", "governance-authority", "force-push", "auto-merge",
                    "credentials", "production-data", "destructive-operation")
        for operation in reserved:
            with self.subTest(operation=operation):
                protocol = AcceptanceProtocol([
                    checkpoint(state="AI_REVIEW", branch="gov-008", pr=12, head=HEAD_A)
                ])
                protocol.selected = "GOV-008"
                decision = protocol.supervise(evidence(
                    human_reserved=True, human_question=f"owner authority required: {operation}"))
                self.assertEqual(decision.value, HUMAN_REQUIRED)
                self.assertFalse(decision.merge_authorized)
                self.assertEqual(protocol.heartbeat()["outcome"], NO_OP)


if __name__ == "__main__":
    unittest.main()
