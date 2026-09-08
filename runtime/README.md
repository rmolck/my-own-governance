# Reference Linux systemd runtime

This directory supplies the Linux-specific reference runtime for the portable
execution contract in [`docs/EXECUTION.md`](../docs/EXECUTION.md). Its concrete
flow is `timer -> service -> runner -> adapter -> Codex CLI`. The timer chooses
when to evaluate, the service provides a predictable process environment, and
the thin runner performs technical preflight and exclusion before invoking the
existing [`adapter/`](../adapter/README.md) exactly once.

The governance-aware worker—not this runtime—reads durable state and decides
whether any checkpoint transition is authorized. The runner has no checkpoint,
state, gate, priority, desired-transition, merge, push, or review-decision
interface. It does not poll or retry. `NO_OP` and a valid worker-recorded
`BLOCKED` therefore remain successful adapter completions.

## Reference installation and configuration

The unit files deliberately use generic reference paths and a non-root service
account named `governance`. An operator may choose equivalent locations and a
different unprivileged account. For the paths shown in the units:

```bash
sudo install -d /opt/my-own-governance /etc/my-own-governance
sudo cp -a adapter runtime /opt/my-own-governance/
sudo install -m 0644 runtime/systemd/my-own-governance.service /etc/systemd/system/
sudo install -m 0644 runtime/systemd/my-own-governance.timer /etc/systemd/system/
sudo install -m 0644 runtime/systemd/runtime.env.example /etc/my-own-governance/runtime.env
sudo systemctl daemon-reload
```

Edit `/etc/my-own-governance/runtime.env` for the deployment. The only required
setting is `GOVERNANCE_REPOSITORY`, the target Git checkout/worktree. Optional
technical settings select Python, the adapter, Codex CLI, the lock file, and the
adapter artifact directory. They do not select semantic work. Do not place
credentials in this public example or in unit files; supply any required agent
authentication using the host's separately protected mechanism.

Run or inspect one heartbeat and its bounded runtime summary with:

```bash
sudo systemctl start my-own-governance.service
systemctl status my-own-governance.service
journalctl -u my-own-governance.service
```

Enable periodic evaluation, inspect it, or disable future scheduling with:

```bash
sudo systemctl enable --now my-own-governance.timer
systemctl list-timers my-own-governance.timer
sudo systemctl disable --now my-own-governance.timer
```

The reference cadence is ten minutes after boot and then every thirty minutes,
with two minutes of timer accuracy. This deliberately moderate cadence is an
operational example, not a portable protocol or governance rule; deployments
may override the timer. `Persistent=false` means missed heartbeats are not
caught up after downtime, avoiding an immediate catch-up run. A later scheduled
heartbeat still evaluates fresh durable state normally.

## Manual runner use and locking

With the same environment configured, invoke the runtime without systemd:

```bash
GOVERNANCE_REPOSITORY=/srv/my-own-governance/target \
  python3 runtime/systemd_runner.py
```

The runner uses Linux `flock(2)` in nonblocking exclusive mode. Its default lock
is `REPOSITORY/.git/codex-systemd-runtime.lock`, so incompatible invocations for
that checkout share exclusion. An operator can choose a writable lock path with
`GOVERNANCE_LOCK_FILE`. If the lock is already held, the runner does not launch
the adapter, emits classification `lock_contended`, exits zero, and does not
mutate durable checkpoint state. This `flock` choice is only part of the Linux
reference implementation, not a requirement of the portable contract.

## Exit and observability semantics

The runner emits one bounded JSON line to stdout (the systemd journal) with UTC
timestamp, repository, lock and launch booleans, adapter status, technical
classification, artifact paths reported by the adapter, and a short error. It
does not replay the adapter's captured Codex output or stderr.

| Runner exit | Classification | Meaning |
|---:|---|---|
| `0` | `valid_completion` | Adapter valid completion, including semantic transition, `NO_OP`, or worker-recorded `BLOCKED`. |
| `0` | `lock_contended` | Another invocation owns the lock; no adapter was launched. This is not checkpoint `BLOCKED`. |
| `65` or `130` | `interrupted_invalid` | Adapter reported invalid/interrupted execution, or the runner was interrupted. |
| `70` | `adapter_execution_failure` | Adapter reported a technical execution failure. |
| `70` | `preflight_failure` / `runner_internal_failure` | Runtime could not safely invoke or finish the adapter. |

An unknown adapter exit maps to `65`/`interrupted_invalid`, making an invalid
execution unambiguously non-successful without inventing a governance outcome.
The adapter remains responsible for at most one Codex process and private raw
artifacts. systemd and `flock` are Linux-specific mechanics; authority, states,
gates, durable-state freshness, heartbeat priority, and result meanings remain
portable contracts in `docs/AUTONOMY.md` and `docs/EXECUTION.md`.

## GOV-009 phase hooks and local evidence

`GOVERNANCE_REFRESH_COMMAND` and `GOVERNANCE_FINALIZER_COMMAND` configure mechanical commands used for the fresh-state/finalizer pre- and post-passes. A pre-pass JSON outcome of `finalized` consumes the invocation and skips Codex. These commands must implement the versioned [`FINALIZER`](../agents/FINALIZER.md) and remote-freshness contracts; the runner does not infer eligibility. `GOVERNANCE_EVIDENCE_FILE` defaults to `.git/governance-runtime/runs.jsonl`, a mode-0600 append-only local JSONL stream. It records phase classifications, lock contention, Codex wall time, and total runner wall time without creating repository commits.
