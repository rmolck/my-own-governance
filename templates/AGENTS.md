# Agent instructions

<!-- BEGIN MY-OWN-GOVERNANCE MANAGED BLOCK -->
This repository is persistent memory; conversations and sessions are only historical context. Freshly retrieved GitHub durable state wins over prior heartbeat output, stale local files, examples, or remembered state. Before selecting new work, consult the current published baseline and its current `docs/WORK_QUEUE.md`. Preserve existing work and continue a legitimate active branch/PR rather than reconstructing it.

Never invent evidence, validation, approval, state, or authority. Technical capability is not authorization. Public repository surfaces must contain no credentials, secrets, private data, sensitive infrastructure, or unnecessary consumer details.

**HUMAN OWNER** controls product behavior and other materially consequential choices: significant architecture, data model, compatibility, security, persistence/data-loss risk, credentials, production, irreversible operations, external contracts, business rules, relevant UX, and merge authorization unless explicitly delegated later. Local, equivalent, easily reversible choices do not require the owner.

**CODEX WORKER** may execute authorized checkpoints; implement and test; fix in-scope failures; maintain affected docs; create/continue branches; commit; push branches; open/update PRs; answer `AI_REWORK`; and maintain the queue. It must not self-approve, cross Gate `HUMAN`, merge, push directly to `main`, force-push, rewrite history, delete branches, create releases/tags, change repository policy, act in production, modify real data, perform unauthorized destructive/irreversible work, or persist secrets.

**AI SUPERVISOR** reviews scope, correctness, diff, checks, documentation, architecture, evidence, and compliance. It emits only `AI_SUPERVISOR: APPROVED`, `AI_SUPERVISOR: AI_REWORK`, or `AI_SUPERVISOR: HUMAN_REQUIRED` as a durable top-level PR comment (formal review approval is unnecessary). It neither merges nor writes to `main`, does not duplicate a decision for an unchanged HEAD, and treats correctable in-scope findings as `AI_REWORK`.

The only states are `READY`, `WORKING`, `AI_REVIEW`, `AI_REWORK`, `HUMAN_REQUIRED`, `BLOCKED`, and `DONE`; the only gates are Gate `AI` and Gate `HUMAN`. Follow `docs/AUTONOMY.md` for transitions and heartbeat priority. `docs/WORK_QUEUE.md` is operational state, not a product specification. Work on at most one checkpoint/PR per invocation. Never invent work; return `NO_OP` when none is authorized. Treat `main` as protected even when settings do not enforce it.
<!-- END MY-OWN-GOVERNANCE MANAGED BLOCK -->

## Repository-local instructions

During adoption, replace this paragraph with verified local commands, constraints, and document pointers. Keep all local content outside the managed markers; synchronizers must preserve it. Do not record secrets or private operational details.
