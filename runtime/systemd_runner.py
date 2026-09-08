#!/usr/bin/env python3
"""Mechanically run one Codex execution-adapter invocation under a Linux lock."""

from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


VALID = 0
INVALID = 65
EXECUTION_FAILURE = 70
INTERRUPTED = 130


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def emit(repository: Path, **values: object) -> dict[str, object]:
    summary = {
        "timestamp": timestamp(),
        "repository": str(repository),
        "lock_acquired": False,
        "adapter_launched": False,
        "adapter_exit_status": None,
        "classification": "runner_internal_failure",
        "artifacts": None,
        "technical_error": None,
    }
    summary.update(values)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def run_command(command: str, repository: Path) -> subprocess.CompletedProcess[str]:
    """Run one configured mechanical phase without shell interpretation."""
    import shlex
    return subprocess.run(shlex.split(command), cwd=repository, capture_output=True,
                          text=True, check=False)


def append_evidence(path: Path | None, summary: dict[str, object]) -> None:
    if path is None:
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, sort_keys=True) + "\n")


def env_path(name: str, default: str | None = None) -> Path:
    value = os.environ.get(name, default)
    if not value:
        raise ValueError(f"{name} is required")
    return Path(value).expanduser().resolve()


def executable(value: str) -> str | None:
    candidate = Path(value).expanduser()
    if candidate.parent != Path("."):
        resolved = candidate.resolve()
        return str(resolved) if resolved.is_file() and os.access(resolved, os.X_OK) else None
    return shutil.which(value)


def run() -> int:
    runner_started_at = timestamp()
    runner_started = time.monotonic()
    try:
        repository = env_path("GOVERNANCE_REPOSITORY")
    except (OSError, ValueError) as error:
        emit(Path("."), classification="preflight_failure", technical_error=str(error)[:300])
        return EXECUTION_FAILURE

    lock_acquired = False
    adapter_launched = False
    try:
        adapter = env_path(
            "GOVERNANCE_ADAPTER",
            str(repository / "adapter" / "codex_execution_adapter.py"),
        )
        lock_file = env_path(
            "GOVERNANCE_LOCK_FILE",
            str(repository / ".git" / "codex-systemd-runtime.lock"),
        )
        evidence_file = Path(os.environ.get(
            "GOVERNANCE_EVIDENCE_FILE",
            str(repository / ".git" / "governance-runtime" / "runs.jsonl"),
        )).expanduser().resolve()
        refresh_command = os.environ.get("GOVERNANCE_REFRESH_COMMAND")
        finalizer_command = os.environ.get("GOVERNANCE_FINALIZER_COMMAND")
        python = executable(os.environ.get("GOVERNANCE_PYTHON", sys.executable))
        if not repository.is_dir() or not (repository / ".git").exists():
            raise ValueError("repository is not a usable Git checkout/worktree")
        if not adapter.is_file():
            raise ValueError("configured execution adapter does not exist")
        if python is None:
            raise ValueError("configured Python executable is unavailable")

        lock_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with lock_file.open("a", encoding="utf-8") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
            except BlockingIOError:
                summary = emit(repository, classification="lock_contended",
                               runner_started_at=runner_started_at,
                               runner_wall_seconds=round(time.monotonic() - runner_started, 6))
                append_evidence(evidence_file, summary)
                return VALID

            phases: list[dict[str, object]] = []
            for phase in ("refresh_pre", "finalizer_pre"):
                configured = refresh_command if phase == "refresh_pre" else finalizer_command
                if not configured:
                    phases.append({"phase": phase, "classification": "not_configured"})
                    continue
                completed_phase = run_command(configured, repository)
                item = {"phase": phase, "exit_status": completed_phase.returncode,
                        "classification": "completed" if completed_phase.returncode == 0 else "failed"}
                if phase == "finalizer_pre" and completed_phase.returncode == 0:
                    try:
                        item["outcome"] = json.loads(completed_phase.stdout).get("outcome")
                    except (json.JSONDecodeError, AttributeError):
                        item["classification"] = "failed"
                phases.append(item)
                if item.get("classification") == "failed":
                    summary = emit(repository, lock_acquired=True, classification="preflight_failure",
                                   phases=phases, runner_started_at=runner_started_at,
                                   runner_wall_seconds=round(time.monotonic() - runner_started, 6),
                                   technical_error=f"{phase} failed")
                    append_evidence(evidence_file, summary)
                    return EXECUTION_FAILURE
                if item.get("outcome") == "finalized":
                    summary = emit(repository, lock_acquired=True, classification="finalized_pre_pass",
                                   phases=phases, runner_started_at=runner_started_at,
                                   runner_wall_seconds=round(time.monotonic() - runner_started, 6))
                    append_evidence(evidence_file, summary)
                    return VALID

            command = [python, str(adapter), str(repository)]
            codex = os.environ.get("GOVERNANCE_CODEX_EXECUTABLE")
            output_dir = os.environ.get("GOVERNANCE_ADAPTER_OUTPUT_DIR")
            if codex:
                command.extend(["--codex-executable", codex])
            if output_dir:
                command.extend(["--output-dir", str(Path(output_dir).expanduser().resolve())])

            adapter_launched = True
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            artifacts = None
            technical_error = None
            try:
                adapter_summary = json.loads(completed.stdout)
                artifacts = {
                    "stdout_path": adapter_summary.get("stdout_path"),
                    "stderr_path": adapter_summary.get("stderr_path"),
                }
                technical_error = adapter_summary.get("technical_error")
                codex_wall_seconds = adapter_summary.get("codex_wall_seconds")
            except (json.JSONDecodeError, AttributeError):
                technical_error = "adapter did not emit its expected JSON summary"
                codex_wall_seconds = None

            post_phase_failure = None
            finalizer_post_outcome = None
            for phase in ("refresh_post", "finalizer_post"):
                configured = refresh_command if phase == "refresh_post" else finalizer_command
                if not configured:
                    phases.append({"phase": phase, "classification": "not_configured"})
                    continue
                completed_phase = run_command(configured, repository)
                item = {"phase": phase, "exit_status": completed_phase.returncode,
                        "classification": "completed" if completed_phase.returncode == 0 else "failed"}
                if phase == "finalizer_post" and completed_phase.returncode == 0:
                    try:
                        finalizer_post_outcome = json.loads(completed_phase.stdout).get("outcome")
                        item["outcome"] = finalizer_post_outcome
                    except (json.JSONDecodeError, AttributeError):
                        item["classification"] = "failed"
                phases.append(item)
                if item["classification"] == "failed":
                    post_phase_failure = phase
                    break

            classifications = {
                VALID: "valid_completion",
                INVALID: "interrupted_invalid",
                EXECUTION_FAILURE: "adapter_execution_failure",
                INTERRUPTED: "interrupted_invalid",
            }
            classification = classifications.get(
                completed.returncode, "interrupted_invalid"
            )
            result = completed.returncode if completed.returncode in classifications else INVALID
            if post_phase_failure is not None:
                classification = "runner_internal_failure"
                result = EXECUTION_FAILURE
                technical_error = f"{post_phase_failure} failed"
            summary = emit(
                repository,
                lock_acquired=True,
                adapter_launched=True,
                adapter_exit_status=completed.returncode,
                classification=classification,
                artifacts=artifacts,
                technical_error=str(technical_error)[:300] if technical_error else None,
                phases=phases,
                codex_wall_seconds=codex_wall_seconds,
                finalizer_post_outcome=finalizer_post_outcome,
                runner_started_at=runner_started_at,
                runner_wall_seconds=round(time.monotonic() - runner_started, 6),
            )
            append_evidence(evidence_file, summary)
            return result
    except KeyboardInterrupt:
        emit(
            repository,
            lock_acquired=lock_acquired,
            adapter_launched=adapter_launched,
            classification="interrupted_invalid",
            technical_error="runner interrupted",
        )
        return INTERRUPTED
    except (OSError, ValueError) as error:
        emit(
            repository,
            lock_acquired=lock_acquired,
            adapter_launched=adapter_launched,
            classification="preflight_failure" if not adapter_launched else "runner_internal_failure",
            technical_error=str(error)[:300],
        )
        return EXECUTION_FAILURE


if __name__ == "__main__":
    if sys.argv[1:]:
        emit(
            Path("."),
            classification="preflight_failure",
            technical_error="runner accepts configuration only through its technical environment",
        )
        raise SystemExit(EXECUTION_FAILURE)
    raise SystemExit(run())
