import copy
import unittest

from validation.supervisor_harness import (
    AI_REWORK,
    APPROVED,
    HUMAN_REQUIRED,
    SupervisorExecutionError,
    approval_valid_for_head,
    mechanical_closure_preserves_review,
    review,
)


def candidate(**changes):
    value = {
        "repository": "owner/repository", "checkpoint": "GOV-X",
        "branch": "feature", "pr": 12, "head": "a" * 40,
        "state": "AI_REVIEW", "gate": "AI", "legitimate_pr": True,
        "diff_observed": True, "scope_conformant": True,
        "governance_consistent": True,
        "tests": {"required": True, "status": "passed", "evidence": "suite output"},
        "checks_required": True, "checks_satisfied": True,
        "mergeability_required": True, "mergeable": True,
    }
    value.update(changes)
    return value


class SupervisorContractTest(unittest.TestCase):
    def test_s01_gate_ai_sufficient_evidence_stable_head_approves(self):
        item = candidate()
        decision = review(item, lambda: item["head"])
        self.assertEqual(decision.value, APPROVED)
        self.assertTrue(decision.merge_authorized)

    def test_s02_correctable_defect_requests_actionable_rework(self):
        item = candidate(scope_conformant=False)
        decision = review(item, lambda: item["head"])
        self.assertEqual(decision.value, AI_REWORK)
        self.assertIn("authorized objective", decision.findings[0])

    def test_s03_genuinely_reserved_decision_requires_human(self):
        item = candidate(human_reserved=True, human_question="Owner must choose compatibility policy")
        decision = review(item, lambda: item["head"])
        self.assertEqual((decision.value, decision.merge_authorized),
                         (HUMAN_REQUIRED, False))

    def test_s04_gate_human_has_no_delegated_authority(self):
        item = candidate(gate="HUMAN")
        decision = review(item, lambda: item["head"])
        self.assertEqual(decision.value, HUMAN_REQUIRED)
        self.assertFalse(decision.merge_authorized)

    def test_s05_head_change_prevents_publication(self):
        with self.assertRaisesRegex(SupervisorExecutionError, "changed during review"):
            review(candidate(), lambda: "b" * 40)

    def test_s06_approval_and_comment_bind_exact_reviewed_head(self):
        item = candidate()
        decision = review(item, lambda: item["head"])
        self.assertEqual(decision.durable_comment()["head"], item["head"])
        self.assertTrue(approval_valid_for_head(decision, item["head"]))

    def test_s07_substantive_later_head_invalidates_approval(self):
        item = candidate()
        decision = review(item, lambda: item["head"])
        self.assertFalse(approval_valid_for_head(decision, "b" * 40))

    def test_s08_valid_mechanical_closure_needs_no_second_semantic_review(self):
        item = candidate()
        decision = review(item, lambda: item["head"])
        closure = {"parent": item["head"], "files": ["docs/WORK_QUEUE.md"],
                   "checkpoint": "GOV-X", "changes": [{
                       "checkpoint": "GOV-X", "field": "state",
                       "before": "AI_REVIEW", "after": "DONE"}]}
        self.assertTrue(mechanical_closure_preserves_review(decision, closure))

    def test_s09_missing_tests_never_become_passed(self):
        item = candidate(tests={"required": True, "status": "not_run"})
        decision = review(item, lambda: item["head"])
        self.assertEqual(decision.value, AI_REWORK)
        self.assertIn("not executed", decision.findings[0])

    def test_s10_tool_error_is_not_human_required(self):
        with self.assertRaises(SupervisorExecutionError):
            review(candidate(tool_error=True), lambda: "a" * 40)

    def test_s11_review_does_not_select_or_start_another_checkpoint(self):
        item = candidate(other_checkpoints=[{"id": "GOV-Y", "state": "READY"}])
        before = copy.deepcopy(item)
        review(item, lambda: item["head"])
        self.assertEqual(item, before)

    def test_s12_review_does_not_invent_requirements_results_or_work(self):
        item = candidate(scope_conformant=False, tests={"required": True, "status": "not_run"})
        before = copy.deepcopy(item)
        decision = review(item, lambda: item["head"])
        self.assertEqual(item, before)
        self.assertEqual(decision.value, AI_REWORK)
        self.assertEqual(len(decision.findings), 2)

    def test_s13_late_invalidating_decision_voids_prior_approval(self):
        item = candidate()
        decision = review(item, lambda: item["head"])
        self.assertTrue(approval_valid_for_head(decision, item["head"]))
        replacement = review(candidate(scope_conformant=False), lambda: item["head"])
        self.assertEqual(replacement.value, AI_REWORK)

    def test_s14_unobserved_diff_and_false_test_claim_request_rework(self):
        item = candidate(diff_observed=False,
                         tests={"required": True, "status": "passed", "evidence": ""})
        decision = review(item, lambda: item["head"])
        self.assertEqual(decision.value, AI_REWORK)
        self.assertEqual(len(decision.findings), 2)


if __name__ == "__main__":
    unittest.main()
