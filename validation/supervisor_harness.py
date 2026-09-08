#!/usr/bin/env python3
"""Deterministic oracle for the observable AI SUPERVISOR contract.

This test-only model validates review inputs and publication races.  It neither
selects work nor calls an AI service or GitHub.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


APPROVED = "AI_SUPERVISOR: APPROVED"
AI_REWORK = "AI_SUPERVISOR: AI_REWORK"
HUMAN_REQUIRED = "AI_SUPERVISOR: HUMAN_REQUIRED"


class SupervisorExecutionError(RuntimeError):
    """Review could not complete; no semantic decision may be published."""


@dataclass(frozen=True)
class ReviewDecision:
    value: str
    head: str
    pr: int
    checkpoint: str
    findings: tuple[str, ...] = ()
    merge_authorized: bool = False

    def durable_comment(self) -> dict[str, Any]:
        """Return structured top-level-comment content bound to the reviewed HEAD."""
        return {
            "body": self.value,
            "head": self.head,
            "pr": self.pr,
            "checkpoint": self.checkpoint,
            "findings": list(self.findings),
        }


def review(
    candidate: dict[str, Any],
    current_head: Callable[[], str],
) -> ReviewDecision:
    """Evaluate one already-selected PR and re-check HEAD before publication."""
    required_identity = ("repository", "checkpoint", "branch", "pr", "head")
    missing_identity = [name for name in required_identity if not candidate.get(name)]
    if missing_identity:
        raise SupervisorExecutionError(
            "review identity unavailable: " + ", ".join(missing_identity)
        )
    if candidate.get("tool_error"):
        raise SupervisorExecutionError("review evidence unavailable due to tool failure")

    reviewed_head = candidate["head"]
    findings: list[str] = []
    if candidate.get("state") != "AI_REVIEW":
        findings.append("checkpoint is not in AI_REVIEW")
    if not candidate.get("legitimate_pr", False):
        findings.append("repository, branch, checkpoint, or PR identity is inconsistent")
    if not candidate.get("diff_observed", False):
        findings.append("the real PR diff was not observed")
    if not candidate.get("scope_conformant", False):
        findings.append("the PR diff exceeds or does not satisfy the authorized objective")
    if not candidate.get("governance_consistent", False):
        findings.append("the change contradicts normative governance or documentation")

    tests = candidate.get("tests", {})
    if tests.get("status") == "failed":
        findings.append("reported tests failed")
    elif tests.get("required") and tests.get("status") != "passed":
        findings.append("required test evidence is absent or was not executed")
    if tests.get("status") == "passed" and not tests.get("evidence"):
        findings.append("tests are labelled passed without observable evidence")
    if candidate.get("checks_required") and not candidate.get("checks_satisfied", False):
        findings.append("required or configured checks are not satisfied")
    if candidate.get("mergeability_required") and not candidate.get("mergeable", False):
        findings.append("current mergeability is not established")

    if candidate.get("human_reserved", False):
        value = HUMAN_REQUIRED
        findings = [candidate.get("human_question") or
                    "a material decision is reserved to the HUMAN OWNER"]
    elif candidate.get("gate") == "HUMAN":
        value = HUMAN_REQUIRED
        findings = ["Gate HUMAN requires a durable HUMAN OWNER resolution"]
    elif findings:
        value = AI_REWORK
    else:
        value = APPROVED

    # Publication is a compare-before-comment operation.  A decision about A is
    # returned only if the PR is still at A; callers must publish this exact
    # binding and must not retarget it to a later HEAD.
    try:
        publish_head = current_head()
    except Exception as error:
        raise SupervisorExecutionError("could not re-confirm PR HEAD") from error
    if publish_head != reviewed_head:
        raise SupervisorExecutionError("PR HEAD changed during review; decision not published")

    return ReviewDecision(
        value=value,
        head=reviewed_head,
        pr=candidate["pr"],
        checkpoint=candidate["checkpoint"],
        findings=tuple(findings),
        merge_authorized=(value == APPROVED and candidate.get("gate") == "AI"),
    )


def approval_valid_for_head(decision: ReviewDecision, head: str) -> bool:
    """Substantive HEAD movement always invalidates semantic approval."""
    return decision.value == APPROVED and decision.head == head


def mechanical_closure_preserves_review(
    decision: ReviewDecision, closure: dict[str, Any]
) -> bool:
    """Recognize GOV-006's narrow derived closure without re-reviewing it."""
    state_change = {
        "checkpoint": decision.checkpoint,
        "field": "state",
        "before": "AI_REVIEW",
        "after": "DONE",
    }
    result_change = {
        "checkpoint": decision.checkpoint,
        "field": "last_relevant_result",
        "after": {"decision": APPROVED, "head": decision.head},
    }
    return (
        decision.merge_authorized
        and closure.get("parent") == decision.head
        and closure.get("checkpoint") == decision.checkpoint
        and closure.get("files") == ["docs/WORK_QUEUE.md"]
        and closure.get("changes") in ([state_change], [state_change, result_change])
    )
