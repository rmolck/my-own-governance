# Home/developer continuation profile

This document defines the repository's user-facing execution profile. It applies
the provider-neutral contracts in [`AUTONOMY.md`](AUTONOMY.md) and
[`EXECUTION.md`](EXECUTION.md); it does not add a state machine, actor authority,
or portable dependency.

## One request

The HUMAN OWNER may say **`continue`** or **`run`** without identifying the next
actor. The request means: retrieve fresh durable repository state and continue the
currently authorized governance cycle as far as present capability and authority
permit.

AI ORCHESTRATOR then owns the handoff:

1. refresh the published baseline, queue, active branches and PRs, exact HEADs,
   discussions, decisions, checks, and relevant evidence;
2. apply the priority and authority rules in `AUTONOMY.md` to identify at most one
   eligible checkpoint/PR;
3. perform the next routine handoff directly when the current interface can do so;
4. preserve every logical role boundary, including independent supervision and
   deterministic finalization; and
5. report durable progress, actor/work in progress, a concrete capability blocker,
   or the exact HUMAN OWNER decision required.

The owner is not a message bus. The orchestrator must not ask the owner to copy a
worker prompt, return worker output, remember a later review request, or relay PR
identity/metadata when an authorized interface can make that handoff directly.
When capability is absent, it reports the precise unavailable operation rather
than implying that it happened.

## Execution venue

For this home/developer profile, a capable **Codex Cloud** environment is the
preferred CODEX WORKER venue. The preference applies only when that environment
can satisfy the selected checkpoint's repository access, authority, continuity,
publication, and evidence requirements. It does not make Codex Cloud part of the
portable governance contract and does not authorize provider-specific integration
work.

The first-class alternate path is one manually requested local wake using the
configured reference runtime:

```bash
GOVERNANCE_REPOSITORY=/path/to/target-worktree \
  python3 runtime/systemd_runner.py
```

The deployment must also provide the required configuration described in
[`runtime/README.md`](../runtime/README.md). The command offers one normal wake;
it does not select a checkpoint, bypass fresh-state recovery, or promise that work
will exist. Calling the adapter directly remains a lower-level reference option,
not a second workflow.

A timer or other scheduler may offer the same wake automatically, but scheduling
is optional. Manual, hosted, and scheduled paths converge on the same queue,
priority, gate, HEAD binding, publication, review, finalization, and outcome
semantics. Switching venue must preserve an existing legitimate branch/PR rather
than reconstructing work.

## Routing boundaries

Fresh durable state determines the next logical action:

| Durable condition | Handoff owner/action |
|---|---|
| Authorized orchestration or reconciliation is required | AI ORCHESTRATOR performs it within its semantic authority. |
| Worker work is authorized | AI ORCHESTRATOR prefers a capable cloud worker; otherwise it may invoke or identify the configured manual local wake. |
| A current exact-HEAD PR is review-ready | AI SUPERVISOR reviews independently and records one durable decision. |
| Gate-`AI` approval is mechanically eligible | The deterministic FINALIZER may perform only safeguarded closure/merge. |
| A host publication/recovery boundary is required | The configured HOST performs only its validated mechanics. |
| A material choice or unavailable authorized operation prevents progress | HUMAN OWNER receives the exact decision or capability blocker. |

Routing never grants CODEX WORKER, HOST, RUNNER, or FINALIZER planning, approval,
or expanded mutation authority. HUMAN-reserved choices still fail closed to
`HUMAN_REQUIRED`. GitHub durable state—not conversation, provider task status, or
local runtime logs—remains authoritative for checkpoint state and coordination.
