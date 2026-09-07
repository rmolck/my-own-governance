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


VALID = 0
INVALID = 65
EXECUTION_FAILURE = 70
INTERRUPTED = 130


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def emit(repository: Path, **values: object) -> None:
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
                emit(repository, classification="lock_contended")
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
            except (json.JSONDecodeError, AttributeError):
                technical_error = "adapter did not emit its expected JSON summary"

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
            emit(
                repository,
                lock_acquired=True,
                adapter_launched=True,
                adapter_exit_status=completed.returncode,
                classification=classification,
                artifacts=artifacts,
                technical_error=str(technical_error)[:300] if technical_error else None,
            )
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
