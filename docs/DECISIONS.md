# Decisions

## D-001 — Public canonical personal baseline

**Decision:** Maintain this repository as the public canonical baseline for independent personal repositories, under MIT, with attribution to the conceptual/documentary reference.

**Rationale:** Reusable stable policy should be reviewable and revision-pinnable while consumer specifics remain local.

**Consequences:** All repository surfaces are treated as public; no secrets or sensitive consumer details belong here. Consumers adopt deliberately rather than inheriting an automatic upstream.

## D-002 — GitHub durable state has operational authority

**Decision:** Fresh GitHub durable state is authoritative over conversations, remembered state, examples, stale local files, and previous heartbeat output.

**Rationale:** Sessions are temporary and cannot safely coordinate autonomous work.

**Consequences:** New-work selection requires a fresh published-baseline read. Legitimate active branch/PR work is reconciled and preserved rather than reconstructed or discarded.

## D-003 — Separate human, worker, and supervisor authority *(amended by D-010 and D-013)*

**Decision:** Separate HUMAN OWNER, CODEX WORKER, and AI SUPERVISOR roles. Capability does not imply authorization.

**Rationale:** Implementation, independent review, and material ownership require distinct authority.

**Consequences:** The worker cannot self-approve or cross human gates. The supervisor reviews but neither executes merges nor writes to `main`. The owner retains material decisions and merge authorization unless explicitly delegated; D-010 records the bounded Gate-`AI` delegation.

**Amendment:** D-013 preserves separation of logical authority while making AI
ORCHESTRATOR and AI SUPERVISOR roles of ChatGPT by default. Distinct logical roles
need not imply distinct products or identities.

## D-004 — No auto-merge initially *(superseded by D-010; retained for history)*

**Decision:** Do not configure or presume auto-merge.

**Rationale:** The initial model must be validated while merge remains an explicit human-controlled act.

**Historical consequences:** Under the initial policy, `AI_SUPERVISOR: APPROVED` supported mechanical closure to `DONE` but did not authorize merge. D-010 replaces that rule for Gate `AI` while retaining the prohibition on implicit auto-merge.

## D-005 — Durable supervisor comment protocol

**Decision:** A top-level PR comment containing exactly one of `AI_SUPERVISOR: APPROVED`, `AI_SUPERVISOR: AI_REWORK`, or `AI_SUPERVISOR: HUMAN_REQUIRED` is a valid durable decision.

**Rationale:** Correct coordination must not depend on whether GitHub grants formal review approval to the supervisor identity.

**Consequences:** Decisions bind a relevant PR HEAD and are not duplicated absent a change that invalidates the previous decision.

## D-006 — Queue is coordination, not specification

**Decision:** `docs/WORK_QUEUE.md` stores only minimal operational checkpoint state.

**Rationale:** Mixing requirements or architecture into a live queue creates conflicting sources of truth.

**Consequences:** Entries link to canonical product, architecture, methodology, and decision documents.

## D-007 — High human-escalation threshold

**Decision:** Reserve `HUMAN_REQUIRED` for materially consequential choices, not correctable or reversible local work.

**Rationale:** Human authority must be protected without turning normal implementation judgment into a bottleneck.

**Consequences:** In-scope defects lead to `AI_REWORK`; objective non-decision dependencies lead to `BLOCKED`.

## D-008 — Portable governance separated from execution

**Decision:** Keep the autonomy contract independent of execution adapters and scheduler/runtime implementations, using the conceptual boundary `governance contract -> execution adapter -> scheduler/runtime`.

**Rationale:** A reusable contract validated against a prior real consumer implementation must preserve one source for intelligence and authority while allowing different execution mechanisms.

**Consequences:** Runners remain deliberately mechanical and do not duplicate states, priorities, roadmap, product, architecture, or semantic work selection. Codex CLI and systemd may become reference implementations but are not protocol requirements.

## D-009 — Linux reference runtime uses advisory locking and the journal

**Decision:** The reference systemd runtime uses a per-checkout, nonblocking
Linux `flock` for mutual exclusion and emits one bounded technical summary to
the systemd journal. These are implementation choices, not portable protocol
requirements.

**Rationale:** Standard Linux facilities provide proportional exclusion and
observability without a new dependency, state machine, semantic queue, or
duplicated agent output.

**Consequences:** Lock contention skips the adapter and exits successfully as a
distinct runtime classification; it never makes a checkpoint `BLOCKED`. Other
runtimes may use equivalent locking and logging mechanisms while preserving the
portable behavior in [`EXECUTION.md`](EXECUTION.md).

## D-010 — Gate-AI approval delegates safeguarded merge authorization

**Decision:** For Gate `AI`, a durable `AI_SUPERVISOR: APPROVED` bound to the legitimate PR's relevant HEAD is both semantic completion and conditional merge authorization. No subsequent semantic `AI_REVIEW -> DONE` evaluation is required. A distinct mechanical finalizer may verify safeguards, record allowlisted closure metadata, and execute the merge; it does not decide approval, gate, product, or architecture. Gate `HUMAN`, authority and merge-policy changes, security, credentials, production or real data, destructive or irreversible operations, and other materially owner-reserved matters continue to require explicit human authority. GOV-006 is valid because the HUMAN OWNER explicitly authorized this policy change.

**Rationale:** Separating semantic authority from operational capability removes a redundant heartbeat and routine human merge bottleneck without turning the runtime into a second supervisor.

**Consequences:** Later substantive changes or a later `AI_REWORK` or `HUMAN_REQUIRED` invalidate approval. When the approved HEAD still records `AI_REVIEW`, authorization exists but merge is not executable until a closure commit materializes `DONE`. That commit preserves derived authorization without renewed review only when it starts exactly at the approved HEAD and its entire diff is allowlisted to `docs/WORK_QUEUE.md` closure metadata; code, tests, requirements, normative decisions, or any other file invalidate it. The finalizer merges exactly the verified derived HEAD using movement protection when available, after verifying PR identity and legitimacy, mergeability, required/configured checks, gate and human-reserved boundaries, and non-destructive operation. Closure and merge are one operational finalization, not a new decision or heartbeat. A failed operational precondition does not automatically mean `BLOCKED`. Approval never enables generic GitHub auto-merge.

## D-011 — Supervisor review is HEAD-bound and evidence-driven *(amended by D-013)*

**Decision:** The AI SUPERVISOR reviews one already-selected, review-ready PR
from observable repository and GitHub evidence. It re-confirms the exact PR HEAD
immediately before publishing exactly one normative decision. It does not
implement fixes, select work, schedule execution, perform finalization, invent
requirements or evidence, or turn review-tool failures into owner decisions.

**Rationale:** Delegated Gate-`AI` merge authorization is safe only when the
semantic decision is independently reproducible, tied to the content actually
reviewed, and separated from implementation and merge mechanics.

**Consequences:** A moved or later substantively changed HEAD requires review
again. Correctable defects and worker-suppliable evidence gaps are `AI_REWORK`;
only genuinely owner-reserved choices are `HUMAN_REQUIRED`. A review execution
failure publishes no semantic decision. GOV-006's strictly allowlisted closure
may preserve approval without a second semantic review, but the finalizer cannot
make or repair the supervisor's judgment.

**Amendment:** The prohibition on selecting work and GitHub coordination applies
to the supervisor role while deciding a review, not to the same agent acting in
the separate AI ORCHESTRATOR role. D-013 supersedes any reading that forbids that
orchestrator from framing work or maintaining routine PR metadata.

## D-012 — Acceptance validation composes test-only protocol oracles

**Decision:** Validate the end-to-end governance protocol with a deterministic,
test-only composition fixture that delegates heartbeat selection/finalization
and supervisor review to their existing structured oracles. It is not a new
production runtime, worker, scheduler, finalizer, or source of authority.

**Rationale:** Unit-level validation can miss incompatible outcomes, HEAD
bindings, closure formats, and authority assumptions at layer boundaries.
Composition makes those contracts executable without pretending to perform a
live model review, GitHub operation, or merge.

**Consequences:** Acceptance PASS requires the reproducible suite, not a manual
assertion. The supervisor closure oracle now accepts the same optional,
strictly-derived approval-result metadata that the heartbeat/finalizer oracle
and `AUTONOMY.md` already accepted; all other closure metadata remains invalid.

## D-013 — Least-semantic actor ownership and empirical runtime cadence

**Decision:** ChatGPT represents AI ORCHESTRATOR and AI SUPERVISOR logical roles by default; CODEX WORKER preferentially mutates and delivers the Git tree; and an allowlisted FINALIZER plus a minimal RUNNER perform only mechanics. Stable role instructions are versioned under `agents/`. Runtime measures Codex and full-run wall time externally in append-only local evidence. Scheduler tuning uses observed median, p90/p95, maxima, failures, outcomes, and lock contention plus margin.

**Rationale:** Assigning each operation to the least-semantic capable actor avoids using commits to simulate unavailable GitHub metadata, permits deterministic finalization, reduces prompt drift, and makes cadence changes evidence-driven.

**Consequences:** The reference order is fresh refresh, finalizer pre-pass, a
second host refresh/reconciliation after successful finalization, one worker
invocation when the refreshed contract authorizes it, and a mechanical host
post-worker inspect/reconcile/publish boundary. There is no finalizer post-pass
after the worker. The host can verify an already-published result or perform only
narrowly authorized publication mechanics when Codex lacks GitHub capability;
worker-held GitHub credentials are not an invariant. A finalized PR and a later worker transition are
separate principal units that may share one wake; the finalizer itself never
selects or invokes work. This owner clarification supersedes D-013's original
wording that finalization consumed the whole wake. The initial `:00` worker and
`:30` supervisor opportunities are operational configuration only. Exhaustive
per-run telemetry is local and append-only by default; repository evidence is
periodically aggregated, never committed once per execution.

## D-014 — Worker-capable publication with a validated host fallback

**Decision:** Use Model A, worker-capable publication, as the reference default. A
capable CODEX WORKER may edit, commit, push, and create or update the initial PR;
the post-worker host freshly reconciles durable identity and validates the real Git
state before verifying or narrowly completing missing mechanics. Model B,
host-owned publication, is a permitted deployment fallback when the host implements
the same fail-closed branch/ref and tracked/untracked path validation. Credentials
belong only to the publishing component and are never a worker invariant.

**Rationale:** Model A preserves the established worker delivery contract and works
across local Codex CLI and hosted environments without imposing a provider-specific
publisher. Model B can reduce the worker's credential and `.git` mutation surface,
but increases host privilege, recovery logic, provider coupling, and implementation
complexity. Fresh durable GitHub state plus deterministic validation makes Model A
recoverable without pretending that local evidence is authoritative.

**Consequences:** A legitimate durable branch/PR always wins over a derived local
name. Repeated or interrupted wakes reconcile already-published work and durable
`AI_REVIEW` instead of invoking or publishing again. Host-owned publication must
fail closed on unexpected tracked or untracked paths, detached/mismatched refs, or
ambiguous identity; it cannot infer semantic correctness or become a selector,
supervisor, or post-worker finalizer. The reference exposes provider-neutral host
primitives, while the full deterministic Gate-AI finalizer remains GOV-011 scope.
