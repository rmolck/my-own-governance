# Portable execution contract

This document defines the minimum portable contract between the governance-aware worker, an execution adapter, and a scheduler/runtime. It is normative for execution behavior but does not redefine the authority, state machine, gates, or heartbeat priority in [`AUTONOMY.md`](AUTONOMY.md). It neither installs nor requires a particular agent, scheduler, operating system, or service.

## Invocation unit

One autonomous invocation, or heartbeat, asks: **does current durable state authorize an autonomous transition, and, if so, can the worker execute at most one checkpoint/PR?** A heartbeat is an opportunity to evaluate and possibly act; it is not an obligation to produce work.

The governance-aware worker performs semantic evaluation and work selection according to `AUTONOMY.md`. A valid evaluation that finds no authorized transition returns `NO_OP`. It must not invent work merely to make an invocation productive.

Each invocation is limited to:

- at most one checkpoint;
- at most one active PR; and
- at most one principal semantic transition or one approved operational finalization.

Incidental mechanical steps needed to complete that unit—including allowlisted approval closure—do not authorize another checkpoint or an unrelated transition.

## Required resolved inputs

Before the worker acts, the execution layer must make it possible to resolve:

- repository identity and the published/default integration branch;
- freshly retrieved durable remote state, including the published baseline;
- applicable normative instructions and `docs/WORK_QUEUE.md`;
- relevant active branches and PRs, their current HEADs, and the invocation's current HEAD;
- durable AI SUPERVISOR decisions associated with the relevant HEAD; and
- relevant checks and evidence, when they exist.

This is an information contract, not a mandated sequence of Git commands or provider API calls.

## Freshness and continuity

New-work selection must use freshly retrieved remote state. A cache, old checkout, previous heartbeat output, example, or agent memory cannot authorize new work. If the durable state cannot be read sufficiently to evaluate the protocol, evaluation has not validly completed.

A legitimate active branch/PR must be preserved and considered before new work is selected. Its current durable HEAD, diff, discussion, checks, and supervisor decision must be reconciled with any advances in the published baseline. Freshness does not justify reconstructing, discarding, or silently superseding valid active work.

## Layer responsibilities

The conceptual flow remains:

`governance contract -> execution adapter -> scheduler/runtime`

Across review and completion, the role flow is:

`heartbeat/runtime -> CODEX WORKER -> PR/evidence -> AI SUPERVISOR -> durable decision -> mechanical finalizer (when authorized) -> durable closure -> merge`

The first diagram separates portable execution layers; the second separates
principals. Neither makes the supervisor an adapter, scheduler, worker, or
finalizer.

### Governance-aware worker

The worker applies authority, states, gates, heartbeat priority, and semantic selection from `AUTONOMY.md`. Only this layer determines whether durable state permits a transition and performs authorized checkpoint work.

### Execution adapter

The adapter:

- translates one portable invocation into the interface of a concrete agent;
- supplies the minimum resolved context the agent needs;
- collects the agent result, execution-layer exit status, and technical evidence; and
- faithfully reports whether evaluation completed.

It does not redefine states, gates, heartbeat priority, authority, or work selection; decide what product to build; or maintain a parallel roadmap or copy of `docs/WORK_QUEUE.md`.

### Scheduler/runtime

The scheduler/runtime:

- decides when to wake;
- establishes mutual exclusion and performs technical preflight;
- invokes the adapter mechanically;
- captures output, errors, and execution status; and
- terminates.

It does not interpret the queue semantically or select priorities beyond invoking the governance-aware worker. Time remaining after an invocation does not authorize another checkpoint.

### Review and finalization boundary

The AI SUPERVISOR consumes a review-ready PR and observable repository/GitHub
evidence, re-confirms its exact HEAD before publishing one durable decision, and
does not modify substantive work. The mechanical finalizer consumes a valid
Gate-`AI` approval and verifies closure conditions; it cannot supply semantic
judgment or repair evidence. Review execution failures publish no decision and
remain execution failures rather than automatic human escalation.

## Mutual exclusion and technical preflight

The runtime must prevent incompatible concurrent invocations for the same repository. The mechanism is implementation-specific. If exclusion is already held, the runtime must not start conflicting work; contention is an execution-layer condition, not automatic evidence that a checkpoint is `BLOCKED`.

Before invoking the worker, the runtime performs only the technical checks necessary to evaluate or execute safely. At minimum, it establishes:

- required repository access;
- ability to read the necessary durable state;
- a usable checkout or worktree;
- absence of an incompatible concurrent invocation; and
- availability of the required adapter and agent.

Preflight cannot decide product direction, architecture, semantic priority, or checkpoint content. It cannot invent a checkpoint. A failed preflight is a runtime/execution failure unless durable evidence independently satisfies the governance definition of `BLOCKED` and the worker records that state through an authorized transition.

## Invocation results

Every invocation must be distinguishable as exactly one of these outcomes:

1. **Transition completed:** evaluation was valid and the authorized principal transition completed successfully.
2. **`NO_OP`:** evaluation was valid, but current durable state authorized no transition. `NO_OP` is successful evaluation, not an error and not persistent checkpoint state.
3. **Checkpoint `BLOCKED`:** the worker validly determined and durably recorded that an objective dependency prevents checkpoint progress. `BLOCKED` is a persistent state defined by `AUTONOMY.md`, not a generic runtime result.
4. **Runtime/execution failure:** the launcher, scheduler, adapter, agent CLI, temporary quota, locking mechanism, or another execution mechanism prevented valid completion. This is neither `NO_OP` nor checkpoint state and must not automatically mutate a checkpoint to `BLOCKED`.

For Gate `AI`, durable `AI_SUPERVISOR: APPROVED` on the relevant HEAD is semantic completion and conditional merge authorization. If that HEAD still publishes `AI_REVIEW`, merge is not executable until a finalizer derives and validates the required strictly allowlisted commit that materializes `DONE`; it then merges the derived HEAD as the same operational finalization. Closure is not a second semantic transition or heartbeat and cannot select more work. The finalizer must verify every safeguard in `AUTONOMY.md`. A failed closure, mergeability, or checks precondition pauses execution without automatically recording `BLOCKED`, and approval never implicitly enables auto-merge.

## Portable exit semantics

An adapter/runtime interface must distinguish, without parsing prose:

- **valid completion**, covering either a completed authorized transition or `NO_OP` and carrying the reported invocation result;
- **execution failure**, meaning valid protocol evaluation or execution did not complete; and
- **interrupted/invalid execution**, when the invocation was cancelled or its result cannot be trusted.

Concrete adapters may assign numeric exit codes and define retry policy. Those numbers and policies are implementation details, not part of this portable contract. A persistent `BLOCKED` state is reported as the valid governance result that was recorded, rather than encoded as an execution-layer failure.

## Minimum observability

For diagnosis, the execution layer must make available:

- an invocation timestamp or other temporal identity;
- repository identity;
- observed baseline and relevant HEAD identities, when resolved;
- the invocation result;
- execution-layer exit status; and
- any technical error that prevented completion.

The representation, retention, and transport are implementation-specific. Logs should reference durable GitHub evidence rather than duplicate it, and must never record credentials, secrets, private data, or sensitive infrastructure details.

## Explicit prohibitions

An execution adapter, runner, scheduler, or runtime must not:

- decide product or architecture;
- change priorities or invent checkpoints;
- cross Gate `HUMAN`;
- approve work, enable auto-merge, or write directly to `main`; a designated mechanical finalizer may execute only a safeguarded, already-authorized Gate-`AI` merge;
- duplicate the state machine or maintain a semantic queue of its own;
- reinterpret `AI_REWORK` or other durable supervisor decisions;
- perform unauthorized destructive or irreversible operations; or
- treat technical capability as authority.

## Portability

The contract can be implemented by combinations such as Codex CLI with systemd, another agent CLI with cron, GitHub Actions, Codex Automations, or future runtimes. These are informative examples only. No named agent, scheduler, operating system, lock primitive, or hosting provider is a normative dependency.

## Reference phase sequence and timing evidence

A reference wake follows `lock -> fresh refresh -> finalizer pre-pass -> worker if still authorized -> await -> fresh refresh -> finalizer post-pass -> record -> unlock`. Every finalizer pass consumes newly refreshed durable state and acts only on a mechanically eligible, approved Gate-`AI` PR; Codex exiting is not an eligibility signal. A successful pre-pass consumes the one-checkpoint/PR allowance and skips the worker. The finalizer is deterministic and allowlisted, while the runner provides no semantic selector.

The runtime measures externally with a monotonic clock around `codex exec` and, where feasible, the complete locked iteration. Append-only structured evidence records UTC start/finish identity, `codex_wall_seconds`, runner wall seconds, exit/classification/outcome, lock contention, checkpoint/branch/PR and relevant before/after HEAD when resolved. Unknown fields remain null rather than invented. Raw per-run evidence is private local runtime data by default; public repository evidence is sanitized and aggregated periodically or in bounded batches, never committed once per wake.

Cadence is runtime configuration. The initial alternating runner/worker opportunity at `:00` and supervisor opportunity at `:30` is only a reference. Changes must use enough observed samples and consider median, p90, p95, maximum, failures, outcomes, and lock contention with operational margin—not mean alone.
