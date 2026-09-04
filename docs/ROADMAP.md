# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Close the reusable common baseline and adoption templates.
- Reconcile the autonomous contract with patterns validated by a prior real consumer implementation.
- Keep portable governance semantics clearly separated from any future execution runtime.

## Next

- Define a portable automation-runtime contract without duplicating governance semantics.
- Implement a Codex CLI execution adapter.
- Implement a reference Linux runtime using systemd and a thin runner.
- Validate scheduler-agnostic heartbeat evaluation.
- Configure and validate an AI SUPERVISOR.
- Execute acceptance tests.
- Define reusable adoption and synchronization.

## Later

- Add proportionate CI/hygiene for governance validation.
- Provide safe synchronization with consumers.
- Consider other schedulers and execution adapters.
- Evaluate greater automation only when it preserves the same authority and safety guarantees, without assuming auto-merge.
