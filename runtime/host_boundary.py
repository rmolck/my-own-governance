#!/usr/bin/env python3
"""Deterministic host-boundary primitives for recovery and safe publication."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Sequence


OUTPUT_LIMIT = 4096


@dataclass(frozen=True)
class ProcessResult:
    classification: str
    exit_status: int | None
    stdout: str
    stderr: str
    technical_error: str | None = None


def run_process(argv: Sequence[str], cwd: Path, output_limit: int = OUTPUT_LIMIT) -> ProcessResult:
    """Launch structured argv with no shell and return bounded UTF-8 text."""
    if not argv or not all(isinstance(value, str) and value for value in argv):
        return ProcessResult("launch_failure", None, "", "", "argv must contain strings")
    try:
        completed = subprocess.run(
            list(argv), cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", shell=False, check=False,
        )
    except (OSError, ValueError) as error:
        return ProcessResult("launch_failure", None, "", "", str(error)[:300])
    classification = "completed" if completed.returncode == 0 else "child_nonzero"
    return ProcessResult(
        classification, completed.returncode,
        completed.stdout[:output_limit], completed.stderr[:output_limit],
    )


def parse_argv(value: str) -> list[str]:
    """Parse one JSON array of strings; shell command strings are rejected."""
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not parsed or not all(
        isinstance(item, str) and item for item in parsed
    ):
        raise ValueError("phase command must be a non-empty JSON string array")
    return parsed


@dataclass(frozen=True)
class GitState:
    classification: str
    branch: str | None
    head: str | None
    expected_changes: tuple[str, ...]
    unexpected_tracked: tuple[str, ...]
    unexpected_untracked: tuple[str, ...]
    technical_error: str | None = None

    @property
    def publishable(self) -> bool:
        return self.classification in {"clean", "expected_modifications"}


def _allowed(path: str, allowed: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate == PurePosixPath(item) or PurePosixPath(item) in candidate.parents
               for item in allowed)


def validate_git_state(repository: Path, expected_branch: str,
                       allowed_paths: Sequence[str]) -> GitState:
    """Classify tracked and untracked changes, failing closed on ambiguous Git state."""
    head = run_process(["git", "rev-parse", "HEAD"], repository)
    branch = run_process(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], repository)
    if head.classification != "completed" or branch.classification != "completed":
        return GitState("invalid_git_state", None, None, (), (), (),
                        "HEAD or branch could not be resolved")
    actual_branch = branch.stdout.strip()
    actual_head = head.stdout.strip()
    if actual_branch != expected_branch:
        return GitState("branch_ref_mismatch", actual_branch, actual_head, (), (), ())

    status = run_process(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], repository,
        output_limit=1024 * 1024,
    )
    if status.classification != "completed":
        return GitState("invalid_git_state", actual_branch, actual_head, (), (), (),
                        "git status failed")
    expected: list[str] = []
    tracked: list[str] = []
    untracked: list[str] = []
    records = status.stdout.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            return GitState("invalid_git_state", actual_branch, actual_head, (), (), (),
                            "unrecognized porcelain record")
        code, path = record[:2], record[3:]
        # Rename/copy records include the source as the following NUL field.
        paths = [path]
        if "R" in code or "C" in code:
            if index >= len(records) or not records[index]:
                return GitState("invalid_git_state", actual_branch, actual_head, (), (), (),
                                "incomplete rename/copy record")
            paths.append(records[index])
            index += 1
        target = untracked if code == "??" else tracked
        for changed in paths:
            (expected if _allowed(changed, allowed_paths) else target).append(changed)
    if tracked:
        classification = "unexpected_tracked_modifications"
    elif untracked:
        classification = "unexpected_untracked_paths"
    elif expected:
        classification = "expected_modifications"
    else:
        classification = "clean"
    return GitState(classification, actual_branch, actual_head, tuple(sorted(set(expected))),
                    tuple(sorted(set(tracked))), tuple(sorted(set(untracked))))


@dataclass(frozen=True)
class IdentityResult:
    classification: str
    branch: str | None
    pr: int | None
    should_derive: bool


def reconcile_identity(*, durable_branch: str | None, durable_pr: int | None,
                       local_branch: str | None, derived_branch: str,
                       remote_branches: Sequence[str]) -> IdentityResult:
    """Preserve durable identity; derive only when no active durable identity exists."""
    if durable_pr is not None and not durable_branch:
        return IdentityResult("inconsistent_durable_identity", None, durable_pr, False)
    if durable_branch:
        if local_branch not in (None, durable_branch):
            return IdentityResult("branch_ref_mismatch", durable_branch, durable_pr, False)
        return IdentityResult("preserved_durable_identity", durable_branch, durable_pr, False)
    if local_branch and local_branch in remote_branches:
        return IdentityResult("unverified_existing_remote_identity", local_branch, None, False)
    if derived_branch in remote_branches:
        return IdentityResult("unverified_existing_remote_identity", derived_branch, None, False)
    return IdentityResult("new_identity", derived_branch, None, True)


def recovery_action(*, durable_state: str | None, branch_exists: bool,
                    pr_exists: bool, worker_result_complete: bool) -> str:
    """Choose mechanics only; durable review/publication always beats local bookkeeping."""
    if durable_state == "AI_REVIEW" and pr_exists:
        return "reconciled_no_action"
    if pr_exists:
        return "reconcile_existing_pr"
    if branch_exists:
        return "reconcile_existing_branch"
    if worker_result_complete:
        return "validate_and_publish"
    return "invoke_worker"


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("expected_branch")
    parser.add_argument("allowed_path", nargs="*")
    args = parser.parse_args()
    result = validate_git_state(args.repository.resolve(), args.expected_branch,
                                args.allowed_path)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.publishable else 70


if __name__ == "__main__":
    raise SystemExit(main())
