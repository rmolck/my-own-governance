# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Implement the bounded deterministic consumer synchronization tooling admitted as
  GOV-015, preserving the reviewed GOV-013 contract without mutating any real
  consumer repository.

## Next

- Reconcile GOV-015 implementation evidence before deciding whether any real
  consumer adoption/synchronization checkpoint is justified. No consumer
  mutation is admitted by this direction.

## Later

- Add proportionate CI/hygiene for governance validation.
- Evaluate other execution adapters and schedulers.
- Consider a bounded finalizer text-format hardening checkpoint for CRLF/LF and
  end-of-file handling if later durable reconciliation admits it.

Codex CLI and systemd reference implementations are not normative requirements of the portable autonomy protocol.
