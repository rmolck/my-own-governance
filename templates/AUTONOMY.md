# Autonomous work contract

This is the normative, scheduler/runner-agnostic contract for HUMAN OWNER, CODEX WORKER, AI SUPERVISOR, and GITHUB. It defines authority and durable coordination; it does not install or authorize automation and does not depend on any particular execution product, user interface, or scheduler.

## Authority of durable remote state

> Conversation context is historical context, not current operational state. When conversation context, previous heartbeat output, local stale files, examples, or remembered state conflict with freshly retrieved GitHub durable state, GitHub durable state wins.

An earlier heartbeat has no authority over a later invocation. Selection of a new `READY` checkpoint **must be based on current, freshly retrieved remote state from the published baseline**—conceptually equivalent to fetching `origin` and reading `origin/main:docs/WORK_QUEUE.md`; exact commands are not normative.

An identified legitimate active branch/PR may take precedence for continuity and must be reconciled with the fresh baseline. Never discard valid work merely because `origin/main` advanced. Inspect its HEAD, diff, discussion, checks, and durable supervisor decision before acting.

## Roles

### HUMAN OWNER

Owns product, observable behavior, significant architecture, data model, compatibility, security, persistence, data-loss risk, credentials, production, irreversible operations, external contracts, business rules, relevant UX, other material decisions, and every Gate `HUMAN` merge. For Gate `AI`, merge authorization is delegated only under the approval and finalization rules below. Changes to authority, merge policy, or security remain human-reserved; GOV-006 is authorized by the owner task that established it. The owner is not required for local, equivalent, easily reversible decisions.

### CODEX WORKER

May execute authorized checkpoints, implement, test, repair in-scope failures, maintain affected documentation, work on branches, commit, push a branch, open/update PRs, respond to `AI_REWORK`, and update the queue. It may not self-approve, cross a human gate, merge or push directly to `main`, force-push, rewrite history, delete branches, create releases/tags, change repository policy, act in production, modify real data, perform an unauthorized destructive/irreversible operation, or persist secrets.

### AI SUPERVISOR

Reviews scope, correctness, diff, checks, documentation, architecture, evidence, and governance. Its only durable decision forms are:

- `AI_SUPERVISOR: APPROVED`
- `AI_SUPERVISOR: AI_REWORK`
- `AI_SUPERVISOR: HUMAN_REQUIRED`

A top-level PR comment is sufficient; the protocol does not depend on formal GitHub review approval. The supervisor decides and authorizes but neither needs to execute the merge nor writes directly to `main`. It does not repeat a decision for the same HEAD unless a relevant change invalidates it. Correctable, in-scope problems require `AI_REWORK`, not human escalation. For Gate `AI`, approval of the relevant PR HEAD means semantic completion and delegates merge authorization subject to the mechanical safeguards below. It never delegates a Gate `HUMAN` merge or a human-reserved decision.

### GITHUB

Provides durable persistence and traceability through branches, commits, PRs, comments/reviews, and checks. GITHUB is not an intelligent agent: it records evidence and coordination but neither decides what is authorized nor grants or expands the authority of HUMAN OWNER, CODEX WORKER, or AI SUPERVISOR.

## Portable execution boundaries

The minimum conceptual architecture is:

`governance contract -> execution adapter -> scheduler/runtime`

- The **governance contract** contains the intelligence, authority, states, gates, priorities, and semantic work selection defined here.
- An **execution adapter** translates one invocation into the interface of a concrete agent without redefining governance.
- A **scheduler/runtime** decides when to wake or evaluate and performs only execution mechanics.

A future runner must remain deliberately simple. It must not duplicate checkpoint states, priorities, the roadmap, product or architecture decisions, or semantic checkpoint selection. Codex CLI, Codex Automations, GitHub Actions, systemd, cron, Windows Task Scheduler, and any other adapter, UI, scheduler, or runtime are possible implementations rather than normative protocol requirements.

The normative execution-layer interface, preflight, exclusion, result, exit, and observability requirements are defined in [`EXECUTION.md`](EXECUTION.md). That contract applies these governance semantics without creating a second state machine or work selector.

## States and transitions

The complete state vocabulary is exactly:

- `READY`: dependencies and authorization permit selection.
- `WORKING`: one worker is actively advancing the checkpoint or its PR.
- `AI_REVIEW`: implementation awaits a supervisor decision for its current relevant HEAD.
- `AI_REWORK`: the supervisor recorded correctable findings.
- `HUMAN_REQUIRED`: a material owner decision is necessary.
- `BLOCKED`: an objective dependency prevents progress.
- `DONE`: the checkpoint has explicit supervisor approval and its permitted closure is recorded.

Required transitions:

- `READY -> WORKING`
- `WORKING -> AI_REVIEW`
- `AI_REVIEW -> AI_REWORK`
- `AI_REWORK -> WORKING`
- `AI_REVIEW ->` semantic completion only through explicit `AI_SUPERVISOR: APPROVED`; mechanically recording `DONE` is closure metadata, not a later semantic transition
- `WORKING -> HUMAN_REQUIRED`
- `HUMAN_REQUIRED -> READY` or `HUMAN_REQUIRED -> WORKING` only after a recorded human resolution
- `WORKING -> BLOCKED`
- `BLOCKED -> READY` or `BLOCKED -> WORKING` only after a recorded objective resolution

A checkpoint may move dynamically to `HUMAN_REQUIRED` whenever its work exposes a material decision. Returning from rework and submitting again follows `AI_REWORK -> WORKING -> AI_REVIEW`.

## Gates

- **Gate `AI`:** a `READY` checkpoint may begin autonomously. A valid AI SUPERVISOR approval on the relevant PR HEAD completes it semantically and delegates conditional merge authorization to a mechanical finalizer.
- **Gate `HUMAN`:** the checkpoint contains a material HUMAN OWNER decision. It cannot be crossed without an explicit durable human resolution. After that resolution, its recorded state determines whether work becomes `READY` or resumes as `WORKING`.

A gate is authorization metadata, not an additional checkpoint state.

## High threshold for `HUMAN_REQUIRED`

Do **not** use it for naming, local organization, test structure, small refactors, equivalent choices, correctable test failures, style, derived documentation, or reversible local decisions.

Use it for observable behavior, product requirements, significant architecture, data model, compatibility, security, persistence, data-loss risk, credentials, production, irreversible operations, external contracts, a lack of evidence that forces an unsupported choice, business rules, relevant UX, or alternatives with materially different consequences.

## Outcomes and execution failures

- **`NO_OP`** is an invocation outcome, not a checkpoint state. It means the protocol evaluation completed validly but found no autonomous transition authorized by current durable state.
- **`BLOCKED`** is a persistent checkpoint state. It means an objective external, technical, access, environment, or evidence dependency prevents checkpoint progress. Record the cause and evidence needed to revalidate it. Missing access is not automatically `HUMAN_REQUIRED`: absent a material choice, it is `BLOCKED`.
- A **runtime/execution failure** means the evaluation mechanism did not complete correctly—for example, its launcher, scheduler, agent CLI, temporary quota, lock, or other transient mechanism failed. It is neither `NO_OP` nor a checkpoint state, and must not automatically mutate the checkpoint to `BLOCKED`; report or retry it according to the runtime's operational policy.

## Approval closure and delegated Gate-AI merge

For Gate `AI`, a durable `AI_SUPERVISOR: APPROVED` on the legitimate PR's relevant HEAD is the final semantic decision: the checkpoint is semantically `DONE` and merge is authorized conditionally. No later heartbeat or semantic `AI_REVIEW -> DONE` transition exists merely to record that fact. `AI_REWORK` or `HUMAN_REQUIRED` after approval invalidates the authorization. Approval never enables GitHub auto-merge.

A separate mechanical finalizer/host may verify and execute closure and merge; it is not a supervisor, semantic work selector, or source of product, architecture, gate, or approval decisions. Before merging it must verify the correct PR and checkpoint, approval bound to the reviewed HEAD, no later substantive change or invalidating decision, PR legitimacy and mergeability, configured/required checks, absence of a Gate `HUMAN` or human-reserved condition, and non-destructive operation. It must use expected-HEAD protection or an equivalent guard against movement when available. A failed precondition pauses finalization as an operational result and does not automatically make the checkpoint `BLOCKED`.

When the approved HEAD still publishes the checkpoint as `AI_REVIEW`, authorization exists but merge is not yet executable. The finalizer must derive one closure commit from exactly that HEAD to materialize `DONE` before merge. It may do so without renewed review only when its complete diff is allowlisted to `docs/WORK_QUEUE.md`, records only the approved checkpoint's closure metadata (including `AI_REVIEW -> DONE` and optional approval metadata), and changes no code, tests, requirements, normative decisions, or substantive behavior. Any other path or content invalidates delegated authorization and requires review of the new HEAD. Closure and merge target exactly that derived HEAD and form one operational finalization—not another checkpoint, semantic decision, heartbeat, or principal transition.

## Future heartbeat selection

After refreshing durable GitHub state and reconciling an active PR, one invocation processes at most one checkpoint/PR in this order:

1. `AI_REWORK`.
2. An approved Gate-`AI` PR eligible for mechanical closure and merge finalization.
3. Existing `WORKING`.
4. `READY` with Gate `AI`.
5. `READY` with Gate `HUMAN`: `NO_OP`.
6. `AI_REVIEW` without a new decision: `NO_OP`.
7. `HUMAN_REQUIRED`: do not cross it; only clearly permitted independent work may proceed.
8. `BLOCKED`: revalidate its cause; if it persists, `NO_OP`.

Finalization consumes the invocation's single checkpoint/PR allowance and never selects another checkpoint. If a valid evaluation completes and no work is authorized, return exactly `NO_OP`. If evaluation cannot complete, report a runtime/execution failure instead. Never invent work and avoid unnecessary parallel work.

## Git and safety policy

Treat `main` as protected even without technical enforcement. The worker may create or continue a branch, make focused commits, push the branch, open/update a PR, respond to review, run checks, and maintain the queue.

The worker may not push directly to or merge `main`; a distinct finalizer may merge only under the delegated Gate-`AI` policy above. No actor may merge a Gate `HUMAN` checkpoint without explicit owner authority. The worker and finalizer may not force-push, rewrite history; delete branches; create tags/releases; alter repository policy; use or persist secrets; touch production or real data; or perform destructive/irreversible operations. Capability, credentials, or a supervisor approval does not expand this authority.
