# Mechanical FINALIZER contract

The FINALIZER is a distinct, potentially fully deterministic component. It uses
fresh durable GitHub state and performs no semantic interpretation, approval,
work selection, roadmap selection, or product/architecture judgment.

For at most one PR, act only when all mechanically verifiable Gate-`AI` safeguards
in `docs/AUTONOMY.md` hold: legitimate identity, current HEAD-bound approval, no
invalidating decision/change, non-human-reserved scope, required checks,
mergeability, strictly allowlisted closure from the exact approved HEAD when
needed, and expected-HEAD-protected merge. Otherwise emit a bounded ineligible or
failed outcome without changing checkpoint state. Never enable auto-merge, merge
Gate `HUMAN`, select subsequent work, or invoke the worker. After successful
finalization, the runner refreshes and may offer one worker invocation; that is a
separate principal unit selected from freshly reconciled durable state.
