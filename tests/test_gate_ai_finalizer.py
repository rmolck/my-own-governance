import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.gate_ai_finalizer import (  # noqa: E402
    INVALID, MECHANICAL_FAILURE, ProviderFailure, run,
)


APPROVED = "a" * 40
BASE = "b" * 40
CLOSURE = "c" * 40
QUEUE = """# Work queue

| ID | Objective | Dependencies | State | Gate | Active branch / PR | Last relevant result |
|---|---|---|---|---|---|---|
| GOV-011 | Finalizer. | GOV-010. | AI_REVIEW | AI | `gov-011` / PR #18 | implementation complete |
"""


def initial_snapshot(**candidate_changes):
    candidate = {
        "number": 18,
        "checkpoint": "GOV-011",
        "state": "OPEN",
        "merged": False,
        "base_branch": "main",
        "branch": "gov-011",
        "gate": "AI",
        "authority_clear": True,
        "head": APPROVED,
        "substantive_head": APPROVED,
        "head_parent": BASE,
        "changed_paths_from_substantive": [],
        "queue_text": QUEUE,
        "substantive_queue_text": QUEUE,
        "mergeable": True,
        "required_checks": ["tests"],
        "checks": [{"name": "tests", "head": APPROVED,
                    "status": "completed", "conclusion": "success"}],
        "decisions": [{"sequence": 1, "decision": "APPROVED", "head": APPROVED}],
    }
    candidate.update(candidate_changes)
    return {"schema_version": 1, "repository": "rmolck/my-own-governance",
            "default_branch": "main", "baseline_head": BASE, "candidate": candidate}


class FakeProvider:
    def __init__(self, state=None):
        self.state = copy.deepcopy(state or initial_snapshot())
        self.requests = []
        self.fail_operation = None
        self.race_operation = None

    def call(self, request):
        self.requests.append(copy.deepcopy(request))
        operation = request["operation"]
        if operation == self.fail_operation:
            raise ProviderFailure("simulated API failure")
        if operation == "snapshot":
            return {"ok": True, "snapshot": copy.deepcopy(self.state)}
        candidate = self.state["candidate"]
        if operation == "create_closure":
            if self.race_operation == operation or request["expected_head"] != candidate["head"]:
                return {"ok": False, "classification": "stale"}
            content = __import__("base64").b64decode(request["content_base64"]).decode()
            candidate.update({
                "head": CLOSURE, "head_parent": APPROVED,
                "changed_paths_from_substantive": ["docs/WORK_QUEUE.md"],
                "queue_text": content,
                "checks": [{"name": "tests", "head": CLOSURE,
                            "status": "completed", "conclusion": "success"}],
            })
            return {"ok": True, "head": CLOSURE}
        if operation == "merge":
            if self.race_operation == operation or request["expected_head"] != candidate["head"]:
                return {"ok": False, "classification": "stale"}
            candidate["merged"] = True
            candidate["state"] = "MERGED"
            return {"ok": True, "merged": True}
        raise AssertionError(operation)


class FinalizerTests(unittest.TestCase):
    def invoke(self, provider):
        output = io.StringIO()
        with patch("sys.stdout", output):
            code = run(provider, "rmolck/my-own-governance", 18, "GOV-011")
        return code, json.loads(output.getvalue())

    def mutations(self, provider):
        return [r for r in provider.requests if r["operation"] != "snapshot"]

    def test_happy_path_creates_one_allowlisted_closure_and_cas_merges(self):
        provider = FakeProvider()
        code, result = self.invoke(provider)
        self.assertEqual((code, result["outcome"]), (0, "finalized"))
        mutations = self.mutations(provider)
        self.assertEqual([r["operation"] for r in mutations], ["create_closure", "merge"])
        self.assertEqual(mutations[0]["expected_head"], APPROVED)
        self.assertEqual(mutations[0]["path"], "docs/WORK_QUEUE.md")
        self.assertEqual(mutations[1]["expected_head"], CLOSURE)

    def test_gate_human_never_mutates(self):
        provider = FakeProvider(initial_snapshot(gate="HUMAN"))
        code, result = self.invoke(provider)
        self.assertEqual((code, result["classification"]), (0, "gate_is_not_ai"))
        self.assertEqual(self.mutations(provider), [])

    def test_missing_or_old_head_approval_never_mutates(self):
        for decisions in ([], [{"sequence": 1, "decision": "APPROVED", "head": BASE}]):
            with self.subTest(decisions=decisions):
                provider = FakeProvider(initial_snapshot(decisions=decisions))
                code, result = self.invoke(provider)
                self.assertEqual((code, result["classification"]),
                                 (0, "missing_current_head_approval"))
                self.assertEqual(self.mutations(provider), [])

    def test_later_rework_or_human_required_invalidates_approval(self):
        for decision in ("AI_REWORK", "HUMAN_REQUIRED"):
            provider = FakeProvider(initial_snapshot(decisions=[
                {"sequence": 1, "decision": "APPROVED", "head": APPROVED},
                {"sequence": 2, "decision": decision, "head": APPROVED},
            ]))
            code, result = self.invoke(provider)
            self.assertEqual((code, result["classification"]),
                             (0, "approval_invalidated_by_later_decision"))
            self.assertEqual(self.mutations(provider), [])

    def test_head_race_before_closure_or_merge_fails_closed(self):
        for operation in ("create_closure", "merge"):
            with self.subTest(operation=operation):
                provider = FakeProvider()
                provider.race_operation = operation
                code, result = self.invoke(provider)
                self.assertEqual((code, result["classification"]), (0, "head_race"))
                self.assertFalse(provider.state["candidate"]["merged"])

    def test_invalid_existing_closure_diff_fails_closed(self):
        state = initial_snapshot(
            head=CLOSURE, head_parent=APPROVED,
            changed_paths_from_substantive=["docs/WORK_QUEUE.md", "src/app.py"],
        )
        provider = FakeProvider(state)
        code, result = self.invoke(provider)
        self.assertEqual((code, result["classification"]), (INVALID, "invalid_evidence"))
        self.assertEqual(self.mutations(provider), [])

    def test_existing_exact_closure_resumes_without_duplicate_commit(self):
        # Capture the canonical transformation from an interrupted real first pass.
        first = FakeProvider()
        first.fail_operation = "merge"
        code, result = self.invoke(first)
        self.assertEqual((code, result["classification"]),
                         (MECHANICAL_FAILURE, "mechanical_failure"))
        resumed = FakeProvider(first.state)
        code, result = self.invoke(resumed)
        self.assertEqual((code, result["outcome"]), (0, "finalized"))
        self.assertEqual([r["operation"] for r in self.mutations(resumed)], ["merge"])

    def test_already_merged_is_idempotent_noop(self):
        provider = FakeProvider(initial_snapshot(merged=True, state="MERGED"))
        code, result = self.invoke(provider)
        self.assertEqual((code, result["classification"]), (0, "already_merged"))
        self.assertEqual(self.mutations(provider), [])

    def test_already_done_substantive_head_is_idempotent_noop(self):
        provider = FakeProvider(initial_snapshot(queue_text=QUEUE.replace(
            "AI_REVIEW", "DONE")))
        code, result = self.invoke(provider)
        self.assertEqual((code, result["classification"]), (0, "already_done"))
        self.assertEqual(self.mutations(provider), [])

    def test_api_failure_is_distinct_and_does_not_mutate_queue_semantics(self):
        provider = FakeProvider()
        provider.fail_operation = "snapshot"
        before = copy.deepcopy(provider.state)
        code, result = self.invoke(provider)
        self.assertEqual((code, result["classification"]),
                         (MECHANICAL_FAILURE, "mechanical_failure"))
        self.assertEqual(provider.state, before)

    def test_missing_checks_stays_ineligible_after_single_closure(self):
        provider = FakeProvider()
        original_call = provider.call

        def no_completed_check(request):
            response = original_call(request)
            if request["operation"] == "create_closure":
                provider.state["candidate"]["checks"] = []
            return response

        provider.call = no_completed_check
        code, result = self.invoke(provider)
        self.assertEqual((code, result["classification"]),
                         (0, "required_checks_not_successful"))
        self.assertEqual([r["operation"] for r in self.mutations(provider)], ["create_closure"])


if __name__ == "__main__":
    unittest.main()
