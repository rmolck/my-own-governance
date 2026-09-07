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


def _approved_for_head(checkpoint: dict[str, Any]) -> bool:
    decision = checkpoint.get("decision") or {}
    return (
        decision.get("value") == "AI_SUPERVISOR: APPROVED"
        and decision.get("head") == checkpoint.get("head")
    )


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one explicit fixture and return one structured observation."""
    checkpoints = state["checkpoints"]
    selected = next((c for c in checkpoints if c["state"] == "AI_REWORK"), None)
    transition = ("AI_REWORK", "WORKING") if selected else None

    if selected is None:
        selected = next(
            (c for c in checkpoints if c["state"] == "AI_REVIEW" and _approved_for_head(c)),
            None,
        )
        transition = ("AI_REVIEW", "DONE") if selected else None
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
                "pr": None, "merge": False}

    if transition:
        selected["state"] = transition[1]
    return {
        "outcome": TRANSITION_COMPLETED if transition else "continued",
        "checkpoint": selected["id"],
        "transition": list(transition) if transition else None,
        "pr": selected.get("pr"),
        "head": selected.get("head"),
        "merge": False,
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
