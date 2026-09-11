# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Formalize conservative adaptive-roadmap reconciliation and just-in-time
  checkpoint planning and admission (GOV-012).

## Later

- Define reusable adoption and synchronization.
- Add proportionate CI/hygiene for governance validation.
- Provide safe synchronization with consumers.
- Evaluate other execution adapters and schedulers.
- Consider a bounded finalizer text-format hardening checkpoint for CRLF/LF and
  end-of-file handling if later durable reconciliation admits it; it is not a
  dependency of GOV-012 and is not implemented here.

Codex CLI and systemd reference implementations are not normative requirements of the portable autonomy protocol.
