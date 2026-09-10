#!/usr/bin/env python3
"""Deterministic, provider-neutral Gate-AI closure and merge finalizer.

The provider is an argv command which accepts one JSON request on stdin and emits
one JSON response on stdout.  It owns GitHub authentication and fresh API reads;
this process owns only validation and the two allowlisted mutations.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence


INVALID = 65
MECHANICAL_FAILURE = 70
SHA = re.compile(r"^[0-9a-f]{40}$")
DECISIONS = {"APPROVED", "AI_REWORK", "HUMAN_REQUIRED"}
QUEUE_PATH = "docs/WORK_QUEUE.md"
OUTPUT_LIMIT = 1024 * 1024


class InvalidEvidence(Exception):
    pass


class ProviderFailure(Exception):
    pass


class Ineligible(Exception):
    pass


class Provider:
    def __init__(self, argv: Sequence[str]):
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise InvalidEvidence("provider argv must be a non-empty string array")
        self.argv = list(argv)

    def call(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                self.argv, input=json.dumps(request, sort_keys=True),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", shell=False, check=False,
            )
        except (OSError, ValueError) as error:
            raise ProviderFailure(f"provider launch failed: {error}") from error
        if completed.returncode != 0:
            detail = completed.stderr[:500].strip() or f"exit {completed.returncode}"
            raise ProviderFailure(f"provider failed: {detail}")
        if len(completed.stdout) > OUTPUT_LIMIT:
            raise ProviderFailure("provider response exceeded output limit")
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ProviderFailure("provider emitted invalid JSON") from error
        if not isinstance(response, dict):
            raise ProviderFailure("provider response must be an object")
        if response.get("ok") is not True:
            classification = response.get("classification", "mechanical_failure")
            if classification == "stale":
                return response
            raise ProviderFailure(str(response.get("error", classification))[:500])
        return response


def emit(outcome: str, classification: str, **values: object) -> int:
    result = {"outcome": outcome, "classification": classification, **values}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if classification == "invalid_evidence":
        return INVALID
    if classification == "mechanical_failure":
        return MECHANICAL_FAILURE
    return 0


def require(value: bool, message: str) -> None:
    if not value:
        raise InvalidEvidence(message)


def eligible(value: bool, message: str) -> None:
    if not value:
        raise Ineligible(message)


def queue_row(text: str, checkpoint: str) -> tuple[list[str], int]:
    matches: list[tuple[list[str], int]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == checkpoint:
            matches.append((cells, number))
    require(len(matches) == 1, "checkpoint must occur in exactly one queue row")
    cells, number = matches[0]
    require(len(cells) == 7, "checkpoint queue row must contain seven columns")
    return cells, number


def replace_queue_row(text: str, checkpoint: str, pr: int, branch: str,
                      substantive_head: str) -> str:
    cells, row_number = queue_row(text, checkpoint)
    require(cells[3] == "AI_REVIEW", "checkpoint is not AI_REVIEW")
    require(cells[4] == "AI", "checkpoint gate is not AI")
    identity = cells[5]
    require(branch in identity and f"#{pr}" in identity,
            "queue active identity does not match branch and PR")
    cells[3] = "DONE"
    cells[5] = "—"
    cells[6] = ("`AI_SUPERVISOR: APPROVED` on substantive HEAD "
                f"`{substantive_head}`.")
    lines = text.splitlines(keepends=True)
    ending = "\n" if lines[row_number - 1].endswith("\n") else ""
    lines[row_number - 1] = "| " + " | ".join(cells) + " |" + ending
    return "".join(lines)


def validate_snapshot(snapshot: dict[str, Any], repository: str, pr: int,
                      checkpoint: str) -> tuple[dict[str, Any], str, str, str]:
    require(snapshot.get("schema_version") == 1, "unsupported snapshot schema")
    require(snapshot.get("repository") == repository, "repository identity mismatch")
    candidate = snapshot.get("candidate")
    require(isinstance(candidate, dict), "snapshot candidate is missing")
    require(candidate.get("number") == pr, "PR identity mismatch")
    require(candidate.get("checkpoint") == checkpoint, "checkpoint identity mismatch")
    if candidate.get("merged") is True:
        raise StopIteration("already_merged")
    eligible(candidate.get("state") == "OPEN", "candidate_pr_not_open")
    require(candidate.get("base_branch") == snapshot.get("default_branch"),
            "PR does not target the default branch")
    require(isinstance(snapshot.get("baseline_head"), str)
            and SHA.fullmatch(snapshot["baseline_head"]) is not None,
            "published baseline HEAD is missing")
    eligible(candidate.get("gate") == "AI", "gate_is_not_ai")
    eligible(candidate.get("authority_clear") is True, "human_reserved_condition")
    head = candidate.get("head")
    substantive = candidate.get("substantive_head")
    require(isinstance(candidate.get("branch"), str) and candidate["branch"],
            "PR branch identity is missing")
    require(isinstance(head, str) and SHA.fullmatch(head) is not None, "invalid PR HEAD")
    require(isinstance(substantive, str) and SHA.fullmatch(substantive) is not None,
            "invalid substantive HEAD")
    queue_text = candidate.get("queue_text")
    require(isinstance(queue_text, str), "queue content is missing")
    cells, _ = queue_row(queue_text, checkpoint)
    if cells[3] == "DONE" and candidate.get("merged") is not True:
        # DONE is resumable only as a rigorously validated derived closure below.
        if head == substantive:
            raise StopIteration("already_done")
    else:
        require(cells[3] == "AI_REVIEW", "queue state is neither AI_REVIEW nor closure DONE")
    require(cells[4] == "AI", "queue gate is not AI")

    decisions = candidate.get("decisions")
    require(isinstance(decisions, list), "supervisor decisions are missing")
    parsed: list[tuple[int, str, str]] = []
    for item in decisions:
        require(isinstance(item, dict), "invalid supervisor decision")
        decision, decision_head, sequence = item.get("decision"), item.get("head"), item.get("sequence")
        require(decision in DECISIONS and isinstance(sequence, int) and sequence >= 0,
                "invalid supervisor decision fields")
        require(isinstance(decision_head, str) and SHA.fullmatch(decision_head) is not None,
                "decision lacks an exact HEAD binding")
        parsed.append((sequence, decision, decision_head))
    require(len({item[0] for item in parsed}) == len(parsed), "decision order is ambiguous")
    parsed.sort()
    approvals = [item for item in parsed if item[1] == "APPROVED" and item[2] == substantive]
    eligible(bool(approvals), "missing_current_head_approval")
    approval_sequence = approvals[-1][0]
    eligible(not any(sequence > approval_sequence and decision in {"AI_REWORK", "HUMAN_REQUIRED"}
                     for sequence, decision, _ in parsed),
             "approval_invalidated_by_later_decision")
    return candidate, head, substantive, queue_text


def validate_checks_and_mergeability(candidate: dict[str, Any], expected_head: str) -> None:
    require(candidate.get("head") == expected_head, "fresh HEAD does not match expected HEAD")
    eligible(candidate.get("mergeable") is True, "mergeability_not_confirmed")
    required = candidate.get("required_checks")
    checks = candidate.get("checks")
    require(isinstance(required, list) and all(isinstance(name, str) and name for name in required),
            "required-check policy is missing or invalid")
    require(len(set(required)) == len(required), "required-check policy is ambiguous")
    require(isinstance(checks, list), "check evidence is missing")
    observed: dict[str, tuple[str, str | None]] = {}
    for check in checks:
        require(isinstance(check, dict) and isinstance(check.get("name"), str),
                "invalid check evidence")
        require(check.get("head") == expected_head, "check evidence is not bound to merge HEAD")
        require(check["name"] not in observed, "duplicate check evidence is ambiguous")
        observed[check["name"]] = (check.get("status"), check.get("conclusion"))
    eligible(all(observed.get(name) == ("completed", "success") for name in required),
             "required_checks_not_successful")


def closure_is_exact(candidate: dict[str, Any], expected_text: str,
                     substantive: str) -> bool:
    return (
        candidate.get("head") != substantive
        and candidate.get("head_parent") == substantive
        and candidate.get("changed_paths_from_substantive") == [QUEUE_PATH]
        and candidate.get("queue_text") == expected_text
    )


def snapshot(provider: Provider, repository: str, pr: int, checkpoint: str) -> dict[str, Any]:
    response = provider.call({"operation": "snapshot", "repository": repository,
                              "pr": pr, "checkpoint": checkpoint})
    value = response.get("snapshot")
    if not isinstance(value, dict):
        raise ProviderFailure("provider snapshot is missing")
    return value


def _run(provider: Provider, repository: str, pr: int, checkpoint: str) -> int:
    initial = snapshot(provider, repository, pr, checkpoint)
    try:
        candidate, head, substantive, queue_text = validate_snapshot(
            initial, repository, pr, checkpoint)
    except StopIteration as result:
        return emit("ineligible", str(result.value), pr=pr, checkpoint=checkpoint)

    source_text = candidate.get("substantive_queue_text", queue_text)
    require(isinstance(source_text, str), "substantive queue content is missing")
    expected_text = replace_queue_row(source_text, checkpoint, pr,
                                      str(candidate.get("branch")), substantive)

    if head == substantive:
        require(queue_text == source_text, "substantive queue snapshots disagree")
        created = provider.call({
            "operation": "create_closure", "repository": repository, "pr": pr,
            "expected_head": substantive, "path": QUEUE_PATH,
            "content_base64": base64.b64encode(expected_text.encode()).decode(),
            "message": f"Finalize {checkpoint} after AI_SUPERVISOR approval",
        })
        if created.get("ok") is not True:
            return emit("stale", "head_race", pr=pr, checkpoint=checkpoint)
    else:
        require(closure_is_exact(candidate, expected_text, substantive),
                "existing post-approval HEAD is not the exact derived closure")

    refreshed = snapshot(provider, repository, pr, checkpoint)
    try:
        current, current_head, refreshed_substantive, _ = validate_snapshot(
            refreshed, repository, pr, checkpoint)
    except StopIteration as result:
        return emit("ineligible", str(result.value), pr=pr, checkpoint=checkpoint)
    require(refreshed_substantive == substantive, "substantive HEAD changed")
    require(closure_is_exact(current, expected_text, substantive),
            "closure HEAD or diff is not the exact allowlisted derivation")
    validate_checks_and_mergeability(current, current_head)

    # A second fresh read is the decision boundary immediately before CAS merge.
    boundary = snapshot(provider, repository, pr, checkpoint)
    boundary_candidate, boundary_head, boundary_substantive, _ = validate_snapshot(
        boundary, repository, pr, checkpoint)
    require(boundary_substantive == substantive and boundary_head == current_head,
            "HEAD moved before merge")
    require(closure_is_exact(boundary_candidate, expected_text, substantive),
            "closure changed before merge")
    validate_checks_and_mergeability(boundary_candidate, current_head)
    merged = provider.call({"operation": "merge", "repository": repository, "pr": pr,
                            "expected_head": current_head})
    if merged.get("ok") is not True:
        return emit("stale", "head_race", pr=pr, checkpoint=checkpoint,
                    expected_head=current_head)
    return emit("finalized", "finalized", pr=pr, checkpoint=checkpoint,
                substantive_head=substantive, closure_head=current_head)


def run(provider: Provider, repository: str, pr: int, checkpoint: str) -> int:
    """Evaluate and, when authorized, finalize one exact candidate."""
    try:
        return _run(provider, repository, pr, checkpoint)
    except InvalidEvidence as error:
        return emit("invalid", "invalid_evidence", error=str(error)[:500],
                    pr=pr, checkpoint=checkpoint)
    except Ineligible as error:
        return emit("ineligible", str(error), pr=pr, checkpoint=checkpoint)
    except ProviderFailure as error:
        return emit("failed", "mechanical_failure", error=str(error)[:500],
                    pr=pr, checkpoint=checkpoint)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="exact owner/name identity")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument(
        "--provider-argv", default=os.environ.get("GOVERNANCE_FINALIZER_PROVIDER_ARGV"),
        help="JSON argv array for the credential-bearing provider integration",
    )
    args = parser.parse_args()
    try:
        provider_argv = json.loads(args.provider_argv) if args.provider_argv else None
        provider = Provider(provider_argv)
        return run(provider, args.repository, args.pr, args.checkpoint)
    except InvalidEvidence as error:
        return emit("invalid", "invalid_evidence", error=str(error)[:500],
                    pr=args.pr, checkpoint=args.checkpoint)
    except ProviderFailure as error:
        return emit("failed", "mechanical_failure", error=str(error)[:500],
                    pr=args.pr, checkpoint=args.checkpoint)


if __name__ == "__main__":
    raise SystemExit(main())
