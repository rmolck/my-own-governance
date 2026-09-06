# Codex CLI execution adapter

This directory contains the reference adapter that translates one invocation of
the portable contract in [`docs/EXECUTION.md`](../docs/EXECUTION.md) into one
non-interactive Codex CLI process. It is an adapter, not a scheduler or a second
governance engine.

## Input and invocation

The only required argument is a target Git worktree. `--codex-executable` (or
`CODEX_EXECUTABLE`) can select the executable, primarily for controlled tests,
and `--output-dir` can relocate artifacts. A manual invocation is:

```bash
python3 adapter/codex_execution_adapter.py /path/to/worktree
```

The adapter starts exactly one process using this Codex interface:

```text
codex exec --json --cd /path/to/worktree -
```

The final `-` supplies a short, generic one-iteration instruction on standard
input. Current repository documents remain authoritative for checkpoint
selection, states, gates, and permissions. The adapter does not accept a
checkpoint, priority, gate, or desired-state argument.

The implementation targets the non-interactive `codex exec` JSON Lines
interface. The development environment used for GOV-003 did not have a `codex`
binary installed, so its local help/version could not be verified; fake-CLI
tests verify the exact argument and process contract without spending a real
agent invocation. Verify `codex --version`, `codex --help`, and
`codex exec --help` on a host before operational use.

## Output and exit semantics

The adapter writes one JSON summary to standard output. Schema version 1
includes an invocation ID and UTC timestamps, canonical repository path,
whether Codex started, the Codex exit status, technical completion and
classification, count of structured events when valid, private artifact paths,
and a bounded technical-error description. Raw Codex JSONL stdout and stderr
are written as mode `0600` files beneath `REPOSITORY/.git/codex-adapter` by
default; the summary does not copy their potentially sensitive contents.

| Adapter exit | Classification | Meaning |
|---:|---|---|
| `0` | `valid_completion` | Codex returned zero and emitted nonempty valid JSONL. Governance results such as a transition, `NO_OP`, or a durably recorded `BLOCKED` remain valid worker results. |
| `65` | `interrupted_invalid` | Codex returned zero but its structured result was empty or invalid. |
| `70` | `execution_failure` | The repository/launcher was unusable, Codex could not start, or Codex returned nonzero. |
| `130` | `interrupted_invalid` | The adapter was interrupted or Codex was terminated by a signal. |

These are execution classifications, not checkpoint states. In particular, the
adapter never turns `NO_OP`, runtime failure, or interruption into `BLOCKED`.
It deliberately does not interpret natural-language agent output to decide a
governance result.

## Responsibility boundary

The worker, guided by fresh durable repository state, performs semantic
selection and authorized work. The adapter only starts and waits for one Codex
process and records technical evidence. Scheduling, periodic execution,
cross-invocation locking, retry policy, systemd integration, merge, and
auto-merge are outside this implementation. A reference Linux systemd runtime
is planned separately.
