# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Deliver and review the reusable adoption and synchronization contract
  (GOV-013), now that GOV-014 has established the home/developer handoff model.

## Next

- Reconcile whether a bounded implementation checkpoint for safe consumer
  synchronization is justified after GOV-013 evidence is complete; no tooling
  or consumer mutation is admitted by this direction.

## Later

- Add proportionate CI/hygiene for governance validation.
- Evaluate other execution adapters and schedulers.
- Consider a bounded finalizer text-format hardening checkpoint for CRLF/LF and
  end-of-file handling if later durable reconciliation admits it; it is not a
  dependency of GOV-013 and is not implemented here.

Codex CLI and systemd reference implementations are not normative requirements of the portable autonomy protocol.
