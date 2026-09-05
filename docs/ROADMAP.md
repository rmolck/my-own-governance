# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Define the portable automation-runtime contract while preserving the separation between governance and execution mechanics.

## Next

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
