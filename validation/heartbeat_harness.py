#!/usr/bin/env python3
"""Test-only structured oracle for isolated heartbeat validation fixtures.

This module is validation infrastructure, not a production worker or runtime. It
models published AUTONOMY/EXECUTION examples so tests can assert observable
selection without parsing agent prose. Production authority remains in the
repository's normative documents and freshly retrieved GitHub state.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Callable


TRANSITION_COMPLETED = "Transition completed"
NO_OP = "NO_OP"
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class FreshnessError(RuntimeError):
    """Fresh durable state could not be established; evaluation is invalid."""


MECHANICAL_CLOSURE_ALLOWLIST = frozenset({"docs/WORK_QUEUE.md"})
INVALIDATING_DECISIONS = {
    "AI_SUPERVISOR: AI_REWORK",
    "AI_SUPERVISOR: HUMAN_REQUIRED",
}


def _decisions(checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    if "decisions" in checkpoint:
        return checkpoint["decisions"]
    decision = checkpoint.get("decision")
    return [decision] if decision else []


def _valid_approval(checkpoint: dict[str, Any]) -> dict[str, Any] | None:
    decisions = _decisions(checkpoint)
    approval_index = next(
        (index for index in range(len(decisions) - 1, -1, -1)
         if decisions[index].get("value") == "AI_SUPERVISOR: APPROVED"),
        None,
    )
    if approval_index is None:
        return None
    decision = decisions[approval_index]
    if any(item.get("value") in INVALIDATING_DECISIONS
           for item in decisions[approval_index + 1:]):
        return None
    return (
        decision
        if decision.get("pr") in (None, checkpoint.get("pr"))
        and decision.get("head") == checkpoint.get("approved_base", checkpoint.get("head"))
        else None
    )


def _finalization(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Model only the observable, mechanical checks—not governance decisions."""
    approval = _valid_approval(checkpoint)
    semantic_done = checkpoint.get("gate") == "AI" and approval is not None
    closure_files = set(checkpoint.get("closure_files", []))
    closure_valid = (
        not closure_files
        or (
            checkpoint.get("closure_parent") == approval.get("head")
            and closure_files <= MECHANICAL_CLOSURE_ALLOWLIST
        )
    ) if approval else False
    authorized = semantic_done and closure_valid and checkpoint.get("legitimate_pr", True)
    executable = (
        authorized
        and checkpoint.get("mergeable", True)
        and checkpoint.get("checks_satisfied", True)
        and not checkpoint.get("human_reserved", False)
    )
    return {
        "semantic_done": semantic_done,
        "merge_authorized": authorized,
        "merge_executable": executable,
        "auto_merge": False,
    }


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one explicit fixture and return one structured observation."""
    checkpoints = state["checkpoints"]
    selected = next((c for c in checkpoints if c["state"] == "AI_REWORK"), None)
    transition = ("AI_REWORK", "WORKING") if selected else None

    if selected is None:
        selected = next(
            (c for c in checkpoints
             if c["state"] == "AI_REVIEW" and _finalization(c)["semantic_done"]),
            None,
        )
        # APPROVED is the semantic completion. Recording DONE is allowlisted
        # housekeeping in the same operational finalization, not a transition.
        transition = None
    if selected is None:
        selected = next((c for c in checkpoints if c["state"] == "WORKING"), None)
        transition = None
    if selected is None:
        selected = next(
            (c for c in checkpoints if c["state"] == "READY" and c["gate"] == "AI"),
            None,
        )
        transition = ("READY", "WORKING") if selected else None

    if selected is None:
        return {"outcome": NO_OP, "checkpoint": None, "transition": None,
                "pr": None, "merge": False, "merge_authorized": False,
                "semantic_done": False, "auto_merge": False}

    if transition:
        selected["state"] = transition[1]
    finalization = _finalization(selected) if selected["state"] == "AI_REVIEW" else {}
    if finalization.get("merge_executable"):
        selected["state"] = "DONE"
    return {
        "outcome": (TRANSITION_COMPLETED
                    if transition or finalization.get("merge_executable") else "continued"),
        "checkpoint": selected["id"],
        "transition": list(transition) if transition else None,
        "pr": selected.get("pr"),
        "head": selected.get("head"),
        "merge": finalization.get("merge_executable", False),
        "merge_authorized": finalization.get("merge_authorized", False),
        "semantic_done": finalization.get("semantic_done", False),
        "auto_merge": False,
    }


def _run_git(runner: CommandRunner, checkout: Path, *arguments: str) -> str:
    completed = runner(
        ["git", "-C", str(checkout), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise FreshnessError(
            f"fresh durable state unavailable during git {arguments[0]}"
        )
    return completed.stdout.strip()


def evaluate_fresh_checkout(
    checkout: Path, runner: CommandRunner = subprocess.run
) -> tuple[dict[str, str], dict[str, Any]]:
    """Verify and update origin/main before reading and evaluating durable state."""
    remote_output = _run_git(
        runner, checkout, "ls-remote", "--exit-code", "origin", "refs/heads/main"
    )
    fields = remote_output.split()
    if len(fields) != 2 or fields[1] != "refs/heads/main":
        raise FreshnessError("fresh durable state unavailable: invalid ls-remote result")
    remote_sha = fields[0]
    local_before = _run_git(runner, checkout, "rev-parse", "refs/remotes/origin/main")
    _run_git(
        runner,
        checkout,
        "fetch",
        "--no-tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
    )
    local_after = _run_git(runner, checkout, "rev-parse", "refs/remotes/origin/main")
    if local_after != remote_sha:
        raise FreshnessError("fresh durable state unavailable: origin/main mismatch")
    serialized = _run_git(
        runner, checkout, "show", "refs/remotes/origin/main:heartbeat-state.json"
    )
    state = json.loads(serialized)
    return {
        "remote_sha": remote_sha,
        "local_before": local_before,
        "local_after": local_after,
    }, evaluate(state)
