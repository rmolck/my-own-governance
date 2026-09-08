# Decisions

## D-001 — Public canonical personal baseline

**Decision:** Maintain this repository as the public canonical baseline for independent personal repositories, under MIT, with attribution to the conceptual/documentary reference.

**Rationale:** Reusable stable policy should be reviewable and revision-pinnable while consumer specifics remain local.

**Consequences:** All repository surfaces are treated as public; no secrets or sensitive consumer details belong here. Consumers adopt deliberately rather than inheriting an automatic upstream.

## D-002 — GitHub durable state has operational authority

**Decision:** Fresh GitHub durable state is authoritative over conversations, remembered state, examples, stale local files, and previous heartbeat output.

**Rationale:** Sessions are temporary and cannot safely coordinate autonomous work.

**Consequences:** New-work selection requires a fresh published-baseline read. Legitimate active branch/PR work is reconciled and preserved rather than reconstructed or discarded.

## D-003 — Separate human, worker, and supervisor authority *(amended by D-010)*

**Decision:** Separate HUMAN OWNER, CODEX WORKER, and AI SUPERVISOR roles. Capability does not imply authorization.

**Rationale:** Implementation, independent review, and material ownership require distinct authority.

**Consequences:** The worker cannot self-approve or cross human gates. The supervisor reviews but neither executes merges nor writes to `main`. The owner retains material decisions and merge authorization unless explicitly delegated; D-010 records the bounded Gate-`AI` delegation.

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

## D-011 — Supervisor review is HEAD-bound and evidence-driven

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
