# Decisions

## D-001 — Public canonical personal baseline

**Decision:** Maintain this repository as the public canonical baseline for independent personal repositories, under MIT, with attribution to the conceptual/documentary reference.

**Rationale:** Reusable stable policy should be reviewable and revision-pinnable while consumer specifics remain local.

**Consequences:** All repository surfaces are treated as public; no secrets or sensitive consumer details belong here. Consumers adopt deliberately rather than inheriting an automatic upstream.

## D-002 — GitHub durable state has operational authority

**Decision:** Fresh GitHub durable state is authoritative over conversations, remembered state, examples, stale local files, and previous heartbeat output.

**Rationale:** Sessions are temporary and cannot safely coordinate autonomous work.

**Consequences:** New-work selection requires a fresh published-baseline read. Legitimate active branch/PR work is reconciled and preserved rather than reconstructed or discarded.

## D-003 — Separate human, worker, and supervisor authority

**Decision:** Separate HUMAN OWNER, CODEX WORKER, and AI SUPERVISOR roles. Capability does not imply authorization.

**Rationale:** Implementation, independent review, and material ownership require distinct authority.

**Consequences:** The worker cannot self-approve or cross human gates. The supervisor reviews but neither merges nor writes to `main`. The owner retains material decisions and merge authorization unless explicitly delegated later.

## D-004 — No auto-merge initially

**Decision:** Do not configure or presume auto-merge.

**Rationale:** The initial model must be validated while merge remains an explicit human-controlled act.

**Consequences:** `AI_SUPERVISOR: APPROVED` can support mechanical closure to `DONE`, but never authorizes merge.

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
