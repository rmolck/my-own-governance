# Roadmap

This is informative direction, not operational state. Current checkpoint state belongs in [`WORK_QUEUE.md`](WORK_QUEUE.md).

## Now

- Complete the deterministic Gate-AI finalizer integration (GOV-011).

## Later

- Generalize roadmap-to-work-queue decomposition and checkpoint admission after GOV-011. Treat the validated `Innlab-idi/vevi-exporter` `P5-PREP` and subsequent Phase 5 decomposition as empirical design evidence, not as a normative contract to copy. Future work will study and formalize:
  - when a broad, informative roadmap phase warrants a preparatory/decomposition checkpoint that may propose—but neither admit nor execute—future work, make reserved decisions, or invent evidence;
  - how to produce small, executable, reviewable checkpoints with explicit dependencies, Gate `AI`/Gate `HUMAN` separation, truthful external-information or evidence needs, bounded completion criteria, and explicit scope limits;
  - how to represent sequences such as research -> decision -> implementation -> validation when appropriate, while keeping unauthorized future work out of `READY`;
  - how to keep `WORK_QUEUE.md` operational rather than a second product specification, preserve product, methodology, and business authority in each consumer repository, and standardize reusable semantics without imposing consumer-specific fields such as VEVI's `New authorized evidence required`.
- Define reusable adoption and synchronization.
- Add proportionate CI/hygiene for governance validation.
- Provide safe synchronization with consumers.
- Evaluate other execution adapters and schedulers.

Codex CLI and systemd reference implementations are not normative requirements of the portable autonomy protocol.
