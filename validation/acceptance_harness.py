#!/usr/bin/env python3
"""Test-only composition harness for the autonomous governance protocol.

This module connects the existing heartbeat and supervisor oracles.  It is not
a worker, scheduler, finalizer, GitHub client, or production state machine.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from validation.heartbeat_harness import evaluate
from validation.supervisor_harness import (
    AI_REWORK,
    APPROVED,
    HUMAN_REQUIRED,
    ReviewDecision,
    mechanical_closure_preserves_review,
    review,
)


class AcceptanceFixtureError(RuntimeError):
    """A simulated layer supplied an outcome incompatible with the protocol."""


class AcceptanceProtocol:
    """Compose existing deterministic oracles around one durable-state fixture."""

    def __init__(self, checkpoints: list[dict[str, Any]]) -> None:
        self.checkpoints = copy.deepcopy(checkpoints)
        self.selected: str | None = None
        self.principal_units = 0

    def checkpoint(self, identifier: str) -> dict[str, Any]:
        return next(item for item in self.checkpoints if item["id"] == identifier)

    def heartbeat(self) -> dict[str, Any]:
        result = evaluate({"checkpoints": self.checkpoints})
        if result["checkpoint"] is not None:
            if self.selected not in (None, result["checkpoint"]):
                raise AcceptanceFixtureError("one invocation selected two checkpoints")
            self.selected = result["checkpoint"]
        if result["transition"]:
            self.principal_units += 1
        return result

    def worker_result(self, technically_completed: bool, valid_outcome: bool) -> None:
        """Apply the observable worker boundary, without implementing worker logic."""
        if not technically_completed:
            return
        if not valid_outcome:
            raise AcceptanceFixtureError("completed worker returned an invalid outcome")
        if self.selected is None:
            raise AcceptanceFixtureError("worker has no selected checkpoint")
        item = self.checkpoint(self.selected)
        if item["state"] != "WORKING":
            raise AcceptanceFixtureError("worker result requires WORKING")
        item["state"] = "AI_REVIEW"

    def supervise(
        self,
        evidence: dict[str, Any],
        current_head: Callable[[], str] | None = None,
    ) -> ReviewDecision:
        if self.selected is None:
            raise AcceptanceFixtureError("supervisor has no selected checkpoint/PR")
        item = self.checkpoint(self.selected)
        candidate = {
            "repository": "fixture/repository",
            "checkpoint": item["id"],
            "branch": item.get("branch"),
            "pr": item.get("pr"),
            "head": item.get("head"),
            "state": item["state"],
            "gate": item["gate"],
            "legitimate_pr": item.get("legitimate_pr", True),
        } | evidence
        decision = review(candidate, current_head or (lambda: candidate["head"]))
        item.setdefault("decisions", []).append({
            "value": decision.value,
            "head": decision.head,
            "pr": decision.pr,
        })
        if decision.value == AI_REWORK:
            item["state"] = "AI_REWORK"
        elif decision.value == HUMAN_REQUIRED:
            item["state"] = "HUMAN_REQUIRED"
        elif decision.value != APPROVED:
            raise AcceptanceFixtureError("unknown supervisor outcome")
        return decision

    def closure(self, decision: ReviewDecision, closure: dict[str, Any]) -> dict[str, Any]:
        """Require agreement at both sides of the supervisor/finalizer boundary."""
        item = self.checkpoint(decision.checkpoint)
        item.update(
            approved_base=decision.head,
            head=closure.get("head", "closure-head"),
            closure_parent=closure.get("parent"),
            closure_files=closure.get("files", []),
            closure_changes=closure.get("changes", []),
        )
        supervisor_accepts = mechanical_closure_preserves_review(decision, closure)
        heartbeat_result = evaluate({"checkpoints": self.checkpoints})
        heartbeat_result["supervisor_accepts_closure"] = supervisor_accepts
        heartbeat_result["protocol_accepts_closure"] = (
            supervisor_accepts and heartbeat_result["merge_executable"]
        )
        return heartbeat_result
