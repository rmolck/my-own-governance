# Portable execution contract

This document defines the minimum portable contract between the governance-aware worker, an execution adapter, and a scheduler/runtime. It is normative for execution behavior but does not redefine the authority, state machine, gates, or heartbeat priority in [`AUTONOMY.md`](AUTONOMY.md). It neither installs nor requires a particular agent, scheduler, operating system, or service.

## Invocation unit

One autonomous invocation, or heartbeat, asks: **does current durable state authorize an autonomous transition, and, if so, can the worker execute at most one checkpoint/PR?** A heartbeat is an opportunity to evaluate and possibly act; it is not an obligation to produce work.

The governance-aware worker performs semantic evaluation and work selection according to `AUTONOMY.md`. A valid evaluation that finds no authorized transition returns `NO_OP`. It must not invent work merely to make an invocation productive.

Each worker invocation is limited to:

- at most one checkpoint;
- at most one active PR; and
- at most one principal semantic transition or one approved operational finalization.

Incidental mechanical steps needed to complete that worker unit do not authorize
another worker checkpoint or an unrelated transition. A runtime wake may first
finalize at most one already-approved PR, then refresh and offer one worker
invocation; finalization is a distinct principal unit rather than worker-selected
work.

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

It does not interpret the queue semantically or select priorities beyond invoking
the governance-aware worker. After the allowlisted pre-pass cycle, time remaining
does not authorize a second worker invocation or checkpoint.

### Mechanical host boundary

The host refreshes and reconciles before finalization, repeats that boundary after
a successful finalization, and inspects/reconciles the result after the worker
returns. The post-worker host phase is not a finalizer, supervisor, or semantic
selector. When Codex already had Git/GitHub capability, it verifies the resulting
durable branch/PR state. When Codex lacked publication capability, it may perform
only narrowly authorized mechanics needed to publish the worker result, with fresh
state and validation safeguards. It must preserve missing publication as missing,
not assert `AI_REVIEW` or other GitHub state prematurely. The portable architecture
does not require Codex to hold GitHub credentials. The reference defaults to worker-capable publication (Model A): a capable worker may
commit, push, and open/update the initial PR, while the host validates and reconciles
what actually became durable. A deployment may instead use host-owned publication
(Model B) when its integration provides the same fail-closed validation and durable
identity inputs. In either model, credentials belong only to the component performing
the publication operation and are supplied outside public artifacts.

### Recovery, identity, and changed-state validation

Every host phase begins from freshly refreshed durable state. Local completion flags
are diagnostic only. If a legitimate PR or branch already exists, the host preserves
that identity and reconciles it; it never derives or publishes a duplicate. Durable
`AI_REVIEW` for the current PR is already-completed publication even when a prior
local result or evidence append is absent. Derivation is permitted only when no
active durable identity or colliding remote branch exists. A contradictory PR,
branch, local HEAD, or ref fails closed.

Before host-owned publication, the host obtains a NUL-delimited Git status including
all untracked paths, resolves symbolic branch and HEAD, and compares every tracked
and untracked changed path with an explicit allowlist supplied by the integration.
It classifies clean state, expected modifications, unexpected tracked modifications,
unexpected untracked paths, and branch/ref mismatch. Only clean or wholly expected
changes are publishable; this validates mechanics, never semantic correctness.

Host subprocess interfaces are structured argv arrays, run without a shell, and use
explicit UTF-8 text decoding. Output is bounded and private by default. Launch failure
(no child exists) and child nonzero exit are distinct from worker, publication, and
finalizer outcomes in evidence. A failed publication remains a publication failure:
it must not be reported as `AI_REVIEW` or as worker failure.

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

A reference wake follows `lock -> host fresh refresh/reconcile -> finalizer pre-pass -> if finalized, host fresh refresh/reconcile -> worker once if authorized -> host post-worker inspect/reconcile/publish -> record -> unlock`. The finalizer consumes fresh durable state and acts only on a mechanically eligible, approved Gate-`AI` PR. It neither selects nor calls the worker. After a successful finalization, the runner must refresh before offering Codex one evaluation of newly eligible work. Codex completion leads to the distinct mechanical host boundary and never triggers a finalizer post-pass because no later supervisor approval can yet exist. The finalizer is deterministic and allowlisted, while the runner and host provide no semantic selector.

The runtime measures externally with a monotonic clock around `codex exec` and, where feasible, the complete locked iteration. Append-only structured evidence records UTC start/finish identity, `codex_wall_seconds`, runner wall seconds, exit/classification/outcome, lock contention, checkpoint/branch/PR and relevant before/after HEAD when resolved. Unknown fields remain null rather than invented. Raw per-run evidence is private local runtime data by default; public repository evidence is sanitized and aggregated periodically or in bounded batches, never committed once per wake.

Cadence is runtime configuration. The initial alternating runner/worker opportunity at `:00` and supervisor opportunity at `:30` is only a reference. Changes must use enough observed samples and consider median, p90, p95, maximum, failures, outcomes, and lock contention with operational margin—not mean alone.
