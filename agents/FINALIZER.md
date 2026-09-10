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

The host post-worker phase is not a second finalizer pass. It mechanically
inspects/reconciles the worker result and, when narrowly authorized, may publish
it; it never infers or supplies supervisor approval.

The reference executable is `runtime/gate_ai_finalizer.py`. Its argv identifies
exactly one repository, PR, and checkpoint; a configured credential-bearing
provider supplies fresh structured snapshots and implements only snapshot,
closure-commit, and expected-HEAD merge operations. Exit `0` carries a
deterministic `finalized`, `ineligible`, or `stale` JSON outcome, exit `65`
identifies invalid evidence, and exit `70` identifies a mechanical provider
failure. Provider failure and ineligibility never authorize a queue rewrite.
