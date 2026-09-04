# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Close the reusable baseline.
- Reconcile and stabilize the autonomous governance contract.
- Separate governance from runtime concerns.

## Next

- Define a portable automation-runtime contract.
- Implement a Codex CLI execution adapter as a reference implementation.
- Implement a reference Linux runtime using systemd.
- Validate heartbeat behavior.
- Configure and validate an AI SUPERVISOR.
- Execute acceptance tests.
- Define reusable adoption and synchronization.

Codex CLI and systemd are future reference implementations, not normative requirements of the portable autonomy protocol.

## Later

- Add proportionate CI/hygiene for governance validation.
- Provide safe synchronization with consumers.
- Evaluate other execution adapters and schedulers.
- Evaluate greater automation without assuming auto-merge.
