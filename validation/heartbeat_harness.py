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
import tempfile
from typing import Any


TRANSITION_COMPLETED = "Transition completed"
NO_OP = "NO_OP"


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


def evaluate_remote(remote: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Clone the durable fixture afresh, then evaluate its structured state."""
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory) / "fresh"
        completed = subprocess.run(
            ["git", "clone", "--quiet", str(remote), str(checkout)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(f"durable state unavailable: {completed.stderr.strip()}")
        state_path = checkout / "heartbeat-state.json"
        if not state_path.is_file():
            raise RuntimeError("durable state unavailable: heartbeat-state.json missing")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        observed = evaluate(state)
        return state, observed
