# Autonomous governance protocol acceptance validation

This is the durable acceptance record for GOV-008. The reproducible suite in
[`tests/test_acceptance_behavior.py`](../tests/test_acceptance_behavior.py)
composes the existing heartbeat and supervisor oracles through the small
test-only fixture in
[`validation/acceptance_harness.py`](../validation/acceptance_harness.py). It
also invokes the reference adapter and Linux runtime at their technical failure
boundary. Nothing here is a production worker, scheduler, supervisor,
finalizer, or GitHub integration.

## Scope and evaluated architecture

The evaluated flow is:

`fresh durable state -> heartbeat/work selection -> execution adapter -> worker outcome -> PR / AI_REVIEW -> AI SUPERVISOR decision -> mechanical closure -> merge eligibility`

Structured fixtures represent durable checkpoints, PR identity, evidence,
decisions, and closure diffs. The composition fixture calls the production
adapter/runtime executables only for technical classification and reuses
`heartbeat_harness.evaluate`, `evaluate_fresh_checkout`,
`supervisor_harness.review`, approval HEAD validation, and both sides of the
mechanical-closure boundary. It adds no production selection or finalization.

## Scenario results

| ID | Composed scenario | Deterministic result |
|---|---|---|
| A1 | Gate-AI happy path | PASS: one `READY -> WORKING` selection, valid worker result, `AI_REVIEW`, HEAD-bound `APPROVED`, allowlisted closure to `DONE`, then executable merge; auto-merge false and the next checkpoint untouched. |
| A2 | Rework loop | PASS: `AI_REWORK -> WORKING` continues the same PR; approval after correction binds only the new substantive HEAD. |
| A3 | Gate HUMAN | PASS: supervisor returns `HUMAN_REQUIRED` without merge authority; no `DONE` or merge. |
| A4 | HEAD race | PASS: movement between review and publication raises an execution error, publishes no decision, and grants no authority. |
| A5 | Invalid mechanical closure | PASS: different checkpoint, extra file, substantive queue edit, wrong parent, and non-allowlisted metadata all fail composed closure authorization. |
| A6 | Runtime/execution failure | PASS: real adapter launch failure and runtime propagation remain technical failures; fixture state is not changed to `BLOCKED`, `HUMAN_REQUIRED`, or approval. |
| A7 | `NO_OP` | PASS: exactly `NO_OP`, with no semantic mutation. |
| A8 | `BLOCKED` | PASS: an objectively persistent dependency remains `BLOCKED` and yields `NO_OP`, distinct from execution failure. |
| A9 | Stale remote state | PASS: a temporary Git remote proves directed refresh before selection; unreachable freshness raises an execution failure rather than any semantic outcome. |
| A10 | Authority boundaries | PASS: Gate HUMAN, governance/authority changes, force-push, auto-merge, credentials, production/real data, and destructive operations remain human-reserved and confer no merge authority. |

## Contradiction found and resolved

The two existing closure oracles disagreed on optional approval metadata.
`heartbeat_harness` accepted an exact `last_relevant_result` containing the
approved decision and HEAD, consistent with `AUTONOMY.md`; the supervisor
helper accepted only the state-only form. The minimal resolution expands the
test-only supervisor helper to accept that one exact optional metadata change.
Regression coverage composes the metadata-bearing happy path and continues to
reject arbitrary metadata, different checkpoints, wrong parents, extra files,
and substantive changes. No normative policy changed.

## Evidence and result

The complete deterministic suite contains **66 tests**, including **10 GOV-008
acceptance tests**, and passes. Python compilation and patch hygiene also pass.
The overall GOV-008 criterion is **PASS** for the simulated/reference contract
composition represented by these fixtures.

## Simulation boundaries and limitations

The suite does not invoke a real AI model, create or comment on a live GitHub
PR, authenticate to a provider, perform a real review, create a real closure
commit, merge, enable auto-merge, deploy systemd, poll, use credentials, access
production or real data, or exercise a consumer synchronization. Supervisor
judgment, worker output, PR/check evidence, mergeability, reserved-operation
requests, and finalizer inputs are deterministic fixtures. Temporary local Git
repositories validate freshness mechanics without network access. Adapter and
runtime subprocesses are real reference entry points around fake or missing
executables, so they prove classification/propagation rather than a live Codex
invocation.
