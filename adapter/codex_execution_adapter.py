#!/usr/bin/env python3
"""Run one governance heartbeat through the non-interactive Codex CLI."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


VALID = 0
INVALID = 65
EXECUTION_FAILURE = 70
INTERRUPTED = 130

INSTRUCTION = """Execute one CODEX WORKER invocation in the supplied repository.
Read agents/CODEX_WORKER.md, the applicable AGENTS.md files, and the fresh durable state they require. Those versioned sources are authoritative.
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, help="target repository/worktree")
    parser.add_argument(
        "--codex-executable",
        default=os.environ.get("CODEX_EXECUTABLE", "codex"),
        help="Codex executable (CODEX_EXECUTABLE or 'codex')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="artifact directory (default: REPOSITORY/.git/codex-adapter)",
    )
    return parser.parse_args(argv)


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def write_private(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def emit(summary: dict[str, object]) -> None:
    print(json.dumps(summary, sort_keys=True))


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    invocation_id = f"{timestamp().replace(':', '').replace('-', '')}-{uuid.uuid4().hex}"
    repository = args.repository.expanduser().resolve()
    output_dir = (args.output_dir or repository / ".git" / "codex-adapter").resolve()
    started_at = timestamp()
    started_monotonic = time.monotonic()
    summary: dict[str, object] = {
        "schema_version": 1,
        "invocation_id": invocation_id,
        "repository": str(repository),
        "started_at": started_at,
        "codex_started": False,
        "cli_exit_status": None,
        "technically_completed": False,
        "classification": "execution_failure",
        "structured_event_count": None,
        "stdout_path": None,
        "stderr_path": None,
        "technical_error": None,
    }

    if not repository.is_dir() or not (repository / ".git").exists():
        summary["technical_error"] = "repository is not a Git worktree"
        summary["finished_at"] = timestamp()
        summary["codex_wall_seconds"] = None
        emit(summary)
        return EXECUTION_FAILURE

    try:
        output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        stdout_path = output_dir / f"{invocation_id}.stdout.jsonl"
        stderr_path = output_dir / f"{invocation_id}.stderr.log"
        command = [args.codex_executable, "exec", "--json", "--cd", str(repository), "-"]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        summary["codex_started"] = True
        codex_started_monotonic = time.monotonic()
        try:
            stdout, stderr = process.communicate(INSTRUCTION.encode("utf-8"))
        except KeyboardInterrupt:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            write_private(stdout_path, stdout)
            write_private(stderr_path, stderr)
            summary.update(
                cli_exit_status=process.returncode,
                classification="interrupted_invalid",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                technical_error="adapter interrupted",
            )
            summary["finished_at"] = timestamp()
            summary["codex_wall_seconds"] = round(time.monotonic() - codex_started_monotonic, 6)
            emit(summary)
            return INTERRUPTED
    except (OSError, ValueError) as error:
        summary["technical_error"] = f"could not execute Codex CLI: {error}"
        summary["finished_at"] = timestamp()
        summary["codex_wall_seconds"] = None
        emit(summary)
        return EXECUTION_FAILURE

    write_private(stdout_path, stdout)
    write_private(stderr_path, stderr)
    summary.update(
        cli_exit_status=process.returncode,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )

    if process.returncode != 0:
        if process.returncode < 0:
            summary.update(
                classification="interrupted_invalid",
                technical_error=f"Codex CLI terminated by signal {-process.returncode}",
            )
            result = INTERRUPTED
        else:
            summary.update(
                classification="execution_failure",
                technical_error="Codex CLI returned a nonzero exit status",
            )
            result = EXECUTION_FAILURE
    else:
        try:
            events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            if not events:
                raise ValueError("Codex CLI emitted no structured events")
            summary.update(
                technically_completed=True,
                classification="valid_completion",
                structured_event_count=len(events),
            )
            result = VALID
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            summary.update(
                classification="interrupted_invalid",
                technical_error=f"invalid structured Codex output: {error}",
            )
            result = INVALID

    summary["finished_at"] = timestamp()
    summary["codex_wall_seconds"] = round(time.monotonic() - codex_started_monotonic, 6)
    summary["adapter_wall_seconds"] = round(time.monotonic() - started_monotonic, 6)
    emit(summary)
    return result


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
