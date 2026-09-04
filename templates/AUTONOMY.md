# Autonomous work contract

This is the normative, scheduler-agnostic protocol for a future CODEX WORKER and AI SUPERVISOR. It defines authority and durable coordination; it does not install or authorize automation.

The protocol defines **what** is authorized: authority, states, gates, transitions, work selection, continuity, review, Git policy, and `NO_OP`. It does not depend on a scheduler, operating system, agent command-line interface, automation service, or user interface.

## Authority of durable remote state

> Conversation context is historical context, not current operational state. When conversation context, previous heartbeat output, local stale files, examples, or remembered state conflict with freshly retrieved GitHub durable state, GitHub durable state wins.

An earlier heartbeat has no authority over a later invocation. Selection of a new `READY` checkpoint **must be based on current, freshly retrieved remote state from the published baseline**—conceptually equivalent to fetching `origin` and reading `origin/main:docs/WORK_QUEUE.md`; exact commands are not normative.

An identified legitimate active branch/PR may take precedence for continuity and must be reconciled with the fresh baseline. Never discard valid work merely because `origin/main` advanced. Inspect its HEAD, diff, discussion, checks, and durable supervisor decision before acting.

## Roles

### HUMAN OWNER

Owns product, observable behavior, significant architecture, data model, compatibility, security, persistence, data-loss risk, credentials, production, irreversible operations, external contracts, business rules, relevant UX, other material decisions, and merge authorization unless explicitly delegated in the future. The owner is not required for local, equivalent, easily reversible decisions.

### CODEX WORKER

May execute authorized checkpoints, implement, test, repair in-scope failures, maintain affected documentation, work on branches, commit, push a branch, open/update PRs, respond to `AI_REWORK`, and update the queue. It may not self-approve, cross a human gate, merge or push directly to `main`, force-push, rewrite history, delete branches, create releases/tags, change repository policy, act in production, modify real data, perform an unauthorized destructive/irreversible operation, or persist secrets.

### AI SUPERVISOR

Reviews scope, correctness, diff, checks, documentation, architecture, evidence, and governance. Its only durable decision forms are:

- `AI_SUPERVISOR: APPROVED`
- `AI_SUPERVISOR: AI_REWORK`
- `AI_SUPERVISOR: HUMAN_REQUIRED`

A top-level PR comment is sufficient; the protocol does not depend on formal GitHub review approval. The supervisor neither merges nor writes directly to `main`. It does not repeat a decision for the same HEAD unless a relevant change invalidates it. Correctable, in-scope problems require `AI_REWORK`, not human escalation. An approval means the reviewed HEAD may receive mechanical queue closure where allowed; it does not authorize merge.

### GITHUB

Provides the durable versioned state, Git objects, pull requests, comments, checks, and audit trail used by the protocol. It is an architectural persistence and traceability actor, not an intelligent agent and not a source of authority beyond the human and agent decisions it durably records.

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
- `AI_REVIEW -> DONE` only after explicit `AI_SUPERVISOR: APPROVED`
- `WORKING -> HUMAN_REQUIRED`
- `HUMAN_REQUIRED -> READY` or `HUMAN_REQUIRED -> WORKING` only after a recorded human resolution
- `WORKING -> BLOCKED`
- `BLOCKED -> READY` or `BLOCKED -> WORKING` only after a recorded objective resolution

A checkpoint may move dynamically to `HUMAN_REQUIRED` whenever its work exposes a material decision. Returning from rework and submitting again follows `AI_REWORK -> WORKING -> AI_REVIEW`.

## Gates

- **Gate `AI`:** a `READY` checkpoint may begin autonomously. It needs explicit AI SUPERVISOR approval before `DONE`.
- **Gate `HUMAN`:** the checkpoint contains a material HUMAN OWNER decision. It cannot be crossed without an explicit durable human resolution. After that resolution, its recorded state determines whether work becomes `READY` or resumes as `WORKING`.

A gate is authorization metadata, not an additional checkpoint state.

## High threshold for `HUMAN_REQUIRED`

Do **not** use it for naming, local organization, test structure, small refactors, equivalent choices, correctable test failures, style, derived documentation, or reversible local decisions.

Use it for observable behavior, product requirements, significant architecture, data model, compatibility, security, persistence, data-loss risk, credentials, production, irreversible operations, external contracts, a lack of evidence that forces an unsupported choice, business rules, relevant UX, or alternatives with materially different consequences.

## Objective blocking

`BLOCKED` is a persistent checkpoint state: an actual external, technical, access, environment, or evidence dependency prevents continuing the checkpoint. Record the cause and the evidence needed to revalidate it. Missing access is not automatically `HUMAN_REQUIRED`: absent a material choice, it is `BLOCKED`.

`NO_OP` is a successful protocol outcome, not a checkpoint state and not an error. It means the current durable state was evaluated correctly but permits no autonomous transition—for example, no eligible work exists, a human gate remains unresolved, review awaits the supervisor, or an objective block persists.

A runtime or execution failure belongs to the future invocation mechanism, not to checkpoint state. A launcher that cannot start, a temporary quota or capacity limit, an aborted process, a transient scheduler failure, a busy lock, or an adapter error must not automatically mutate a checkpoint to `BLOCKED`. Record `BLOCKED` only when an objective project dependency actually prevents checkpoint progress.

## Scheduler-agnostic heartbeat selection

A future heartbeat means “evaluate whether current versioned state permits an autonomous transition,” not “perform work every fixed interval.” How or when an execution mechanism invokes that evaluation is outside this protocol.

After refreshing durable GitHub state and reconciling an active PR, one invocation processes at most one checkpoint/PR in this order:

1. `AI_REWORK`.
2. Mechanical closure after `AI_SUPERVISOR: APPROVED` when the protocol permits recording state, but never merge.
3. Existing `WORKING`.
4. `READY` with Gate `AI`.
5. `READY` with Gate `HUMAN`: `NO_OP`.
6. `AI_REVIEW` without a new decision: `NO_OP`.
7. `HUMAN_REQUIRED`: do not cross it; only clearly permitted independent work may proceed.
8. `BLOCKED`: revalidate its cause; if it persists, `NO_OP`.

If no work is authorized, return exactly `NO_OP`. Never invent work and avoid unnecessary parallel work.

## Informative future execution layers

The portable, versioned governance contract—including agent instructions, this protocol, project documentation, decisions, roadmap, and queue—defines what is authorized. A future agent-specific execution adapter may invoke a worker, but must not duplicate state, roadmap, or selection semantics. A future scheduler/runtime may decide when to evaluate, perform technical preflight and locking, invoke the adapter, capture its result, and log or exit; it must not make product, architecture, roadmap, priority, checkpoint, or state-meaning decisions.

These layers are informative architecture only. This baseline neither requires nor implements any particular adapter, scheduler, service manager, automation platform, operating system, or user interface.

## Git and safety policy

Treat `main` as protected even without technical enforcement. The worker may create or continue a branch, make focused commits, push the branch, open/update a PR, respond to review, run checks, and maintain the queue.

Without sufficient explicit human authority, it may not push directly to or merge `main`; force-push; rewrite history; delete branches; create tags/releases; alter repository policy; use or persist secrets; touch production or real data; or perform destructive/irreversible operations. Capability, credentials, or a supervisor approval does not expand this authority.
