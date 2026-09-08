# AI SUPERVISOR contract validation

This is the durable validation record for GOV-007. The test-only oracle in
[`validation/supervisor_harness.py`](../validation/supervisor_harness.py)
models observable review and publication behavior without calling an AI model,
GitHub, a scheduler, a worker, or a finalizer. It does not test intelligence or
provide production integration.

## Review protocol

One invocation receives one already-selected, review-ready checkpoint/PR and
observed evidence. It verifies identity, state/gate, exact HEAD, real diff,
authorized scope, normative consistency, test/check evidence, relevant
mergeability, and human-reserved boundaries. Correctable findings produce
actionable `AI_REWORK`; only a genuinely reserved decision produces
`HUMAN_REQUIRED`. Tool/runtime inability to complete review publishes no
decision.

Publication uses a compare-before-comment model: read HEAD A, review A,
re-read the PR HEAD, then publish a decision explicitly bound to A only when it
is unchanged. The structured oracle represents the durable top-level comment
with exactly one normative decision marker plus PR and HEAD bindings. It never
retargets a decision to a later HEAD.

## Deterministic scenario matrix

| ID | Scenario | Observable assertion |
|---|---|---|
| S-01 | Gate AI, sufficient evidence, stable HEAD | `APPROVED`, exact HEAD binding, delegated merge authority |
| S-02 | Correctable scope defect | `AI_REWORK` with an actionable finding |
| S-03 | Genuinely owner-reserved choice | `HUMAN_REQUIRED`, no merge authority |
| S-04 | Gate HUMAN | `HUMAN_REQUIRED`; supervisor receives no delegated authority |
| S-05 | HEAD changes during review | execution failure; no decision is available to publish |
| S-06 | Approval publication | decision/comment bind exactly to reviewed PR HEAD |
| S-07 | Later substantive HEAD | prior approval is invalid for that HEAD |
| S-08 | Strict GOV-006 closure | approval is preserved without second semantic review |
| S-08b | Closure names a different checkpoint | approval is not preserved |
| S-09 | Required tests absent/not run | `AI_REWORK`; never a false pass |
| S-10 | Tool/runtime error | execution failure, not automatic `HUMAN_REQUIRED` |
| S-11 | Another checkpoint is ready | input remains unchanged; no selection or start occurs |
| S-12 | Missing requirements/results | no invention or input mutation; observed gaps remain findings |
| S-13 | Later invalidating decision | rework supersedes the earlier approval |
| S-14 | Diff unobserved / pass unsupported | each evidentiary defect is explicit `AI_REWORK` |

The closure helper is intentionally narrow and non-production: exact approved
parent, only `docs/WORK_QUEUE.md`, and only the reviewed checkpoint's
`AI_REVIEW -> DONE` state change. The complete GOV-006 finalizer safeguards
remain normative in [`AUTONOMY.md`](AUTONOMY.md) and covered by the heartbeat
harness; this oracle validates only the supervisor/finalizer boundary.

## Limits

No scenario performs a real model call, posts a GitHub comment, authenticates,
merges, enables auto-merge, or deploys periodic execution. Fixture evidence is
synthetic and proves only the deterministic contract. Provider/model choice,
production credentials, deployment, a production finalizer, consumer adoption,
and synchronization remain outside GOV-007.

## Rework validation evidence

The rework suite contains 55 tests, including 15 supervisor-specific tests.
The complete and focused suites pass, as do Python compilation,
`git diff --check`, the directed semantic-contradiction inspection, and the patch
credential-pattern scan. These are local deterministic checks; they do not
claim a live supervisor, GitHub-comment, or merge integration.
