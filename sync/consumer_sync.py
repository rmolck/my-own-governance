#!/usr/bin/env python3
"""Deterministic, revision-pinned managed-block synchronization."""

from __future__ import annotations

import argparse
import difflib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from typing import Any


BEGIN = b"<!-- BEGIN MY-OWN-GOVERNANCE MANAGED BLOCK -->"
END = b"<!-- END MY-OWN-GOVERNANCE MANAGED BLOCK -->"
SOURCE_PATH = "templates/AGENTS.md"
DEFAULT_RECORD = ".my-own-governance.json"
FULL_OID = re.compile(r"[0-9a-fA-F]{40,64}\Z")


class SyncFailure(Exception):
    """A visible, fail-closed validation failure."""


def _block(data: bytes, label: str) -> tuple[int, int, bytes]:
    lines = data.splitlines(keepends=True)
    begins = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == END]
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        raise SyncFailure(f"{label}: expected exactly one ordered managed marker pair")
    start = sum(map(len, lines[: begins[0]]))
    finish = sum(map(len, lines[: ends[0] + 1]))
    nested = sum(line.rstrip(b"\r\n") in (BEGIN, END) for line in lines[begins[0] : ends[0] + 1])
    if nested != 2:
        raise SyncFailure(f"{label}: nested or ambiguous managed markers")
    return start, finish, data[start:finish]


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise SyncFailure(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _verify_revision(repo: Path, revision: str) -> str:
    if not FULL_OID.fullmatch(revision):
        raise SyncFailure("revision must be a full hexadecimal object ID")
    resolved = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    if resolved.lower() != revision.lower():
        raise SyncFailure(f"revision does not resolve to itself: {revision}")
    return resolved.lower()


def _source_block(repo: Path, revision: str) -> bytes:
    source = _git(repo, "show", f"{revision}:{SOURCE_PATH}")
    return _block(source, f"{revision}:{SOURCE_PATH}")[2]


def _relative_path(value: str) -> Path:
    posix = PurePosixPath(value)
    if posix.is_absolute() or not posix.parts or ".." in posix.parts:
        raise SyncFailure("adoption record must be a relative path inside the consumer root")
    return Path(*posix.parts)


def _read_record(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SyncFailure(f"invalid adoption record {path}: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"baseline_repository", "baseline_revision"}:
        raise SyncFailure("adoption record must contain exactly baseline_repository and baseline_revision")
    if not all(isinstance(value[key], str) for key in value):
        raise SyncFailure("adoption record values must be strings")
    return value


def _record_bytes(repository: str, revision: str) -> bytes:
    return (json.dumps(
        {"baseline_repository": repository, "baseline_revision": revision},
        indent=2,
        sort_keys=True,
    ) + "\n").encode()


def plan(
    baseline: Path,
    repository_identity: str,
    proposed_revision: str,
    consumer: Path,
    record_relative: Path,
) -> dict[str, Any]:
    if not repository_identity:
        raise SyncFailure("baseline repository identity must not be empty")
    proposed = _verify_revision(baseline, proposed_revision)
    agents_path = consumer / "AGENTS.md"
    record_path = consumer / record_relative
    if agents_path.is_symlink() or record_path.is_symlink():
        raise SyncFailure("AGENTS.md and the adoption record must be regular files, not symlinks")
    try:
        agents = agents_path.read_bytes()
    except OSError as exc:
        raise SyncFailure(f"cannot read consumer AGENTS.md: {exc}") from exc
    record = _read_record(record_path)
    if record["baseline_repository"] != repository_identity:
        raise SyncFailure("adoption record repository identity does not match the explicit baseline identity")
    recorded = _verify_revision(baseline, record["baseline_revision"])
    start, finish, current = _block(agents, "consumer AGENTS.md")
    if current != _source_block(baseline, recorded):
        raise SyncFailure("consumer managed block diverges from its recorded baseline revision")
    wanted = _source_block(baseline, proposed)
    new_agents = agents[:start] + wanted + agents[finish:]
    new_record = _record_bytes(repository_identity, proposed)
    old_record = record_path.read_bytes()
    changed = new_agents != agents or new_record != old_record
    paths = [str(Path("AGENTS.md")), record_relative.as_posix()] if changed else []
    return {
        "status": "change" if changed else "no-op",
        "old_revision": recorded,
        "new_revision": proposed,
        "changed_paths": paths,
        "agents": agents,
        "new_agents": new_agents,
        "record": old_record,
        "new_record": new_record,
    }


def _diff(path: str, old: bytes, new: bytes) -> str:
    before = old.decode("utf-8", "surrogateescape").splitlines(keepends=True)
    after = new.decode("utf-8", "surrogateescape").splitlines(keepends=True)
    return "".join(difflib.unified_diff(before, after, f"a/{path}", f"b/{path}"))


def write_candidate(consumer: Path, destination: Path, record_relative: Path, result: dict[str, Any]) -> None:
    if destination.exists():
        raise SyncFailure("candidate destination already exists")
    consumer_resolved = consumer.resolve()
    destination_resolved = destination.resolve()
    if destination_resolved == consumer_resolved or consumer_resolved in destination_resolved.parents:
        raise SyncFailure("candidate destination must be outside the consumer tree")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        shutil.copytree(consumer, staging, dirs_exist_ok=True, symlinks=True)
        (staging / "AGENTS.md").write_bytes(result["new_agents"])
        candidate_record = staging / record_relative
        candidate_record.parent.mkdir(parents=True, exist_ok=True)
        candidate_record.write_bytes(result["new_record"])
        check = plan(
            baseline=Path(result["baseline"]),
            repository_identity=result["repository_identity"],
            proposed_revision=result["new_revision"],
            consumer=staging,
            record_relative=record_relative,
        )
        if check["status"] != "no-op":
            raise SyncFailure("candidate failed the idempotency postcondition")
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--baseline-identity", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--consumer", required=True, type=Path)
    parser.add_argument("--record", default=DEFAULT_RECORD)
    parser.add_argument("--write-candidate", type=Path)
    args = parser.parse_args(argv)
    try:
        record_relative = _relative_path(args.record)
        result = plan(args.baseline, args.baseline_identity, args.revision, args.consumer, record_relative)
        result["baseline"] = str(args.baseline.resolve())
        result["repository_identity"] = args.baseline_identity
        public = {key: result[key] for key in ("status", "old_revision", "new_revision", "changed_paths")}
        public["diff"] = "".join((
            _diff("AGENTS.md", result["agents"], result["new_agents"]),
            _diff(record_relative.as_posix(), result["record"], result["new_record"]),
        ))
        print(json.dumps(public, indent=2, sort_keys=True))
        if args.write_candidate and result["status"] == "change":
            write_candidate(args.consumer, args.write_candidate, record_relative, result)
        return 0
    except SyncFailure as exc:
        print(json.dumps({"status": "failure", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
