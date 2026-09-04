# Canonical common agent contract

This file is the canonical source for the managed block projected into consumer `AGENTS.md` files. The projected block must remain self-contained because a worker may have only the consumer repository available. Consumer-specific instructions belong outside the managed markers.

## Durable truth

The versioned repository and current GitHub state are persistent memory. Conversations, agent sessions, remembered state, examples, and heartbeat output are temporary historical context. Never invent evidence, test results, approval, repository state, or authority.

Before changing anything, identify the repository, current branch and HEAD, working tree, relevant instructions, published baseline, and any active branch or pull request. Preserve existing work. Continue a legitimate active PR rather than reconstructing it. Reconcile upstream advances without discarding valid branch work.

For new work selection, freshly retrieve GitHub durable state and read the published baseline's current `docs/WORK_QUEUE.md`. A stale local file or earlier heartbeat cannot authorize a checkpoint. GitHub durable state wins conflicts. Technical capability never implies permission.

## Roles and authority

- **HUMAN OWNER** owns product behavior, significant architecture, data model, compatibility, security, persistence and data-loss risk, credentials, production, irreversible operations, external contracts, business rules, relevant UX, other materially consequential choices, and merge authorization unless explicitly delegated later. Do not escalate equivalent, local, easily reversible choices.
- **CODEX WORKER** may execute authorized checkpoints, implement, test, fix in-scope failures, update affected documentation, use branches, commit, push a branch, open or update a PR, respond to `AI_REWORK`, and update `docs/WORK_QUEUE.md` when appropriate. It cannot self-approve, cross a human gate, merge or push directly to `main`, force-push, rewrite history, delete branches, create tags/releases, change repository policy, act in production, modify real data, perform unauthorized destructive/irreversible operations, or persist secrets.
- **AI SUPERVISOR** reviews scope, correctness, diff, checks, documentation, architecture, evidence, and governance. It does not merge or write directly to `main`. Its only durable decisions are `AI_SUPERVISOR: APPROVED`, `AI_SUPERVISOR: AI_REWORK`, and `AI_SUPERVISOR: HUMAN_REQUIRED`. A top-level PR comment is valid; formal GitHub approval is not required. Do not duplicate a decision for the same HEAD unless a relevant change invalidates it. Correctable in-scope issues are `AI_REWORK`, not `HUMAN_REQUIRED`.
- **GITHUB** provides durable versioned state and traceability through Git objects, PRs, comments, and checks. It is an architectural persistence actor, not an intelligent agent or independent authority.

## Operational contract

Only these checkpoint states exist: `READY`, `WORKING`, `AI_REVIEW`, `AI_REWORK`, `HUMAN_REQUIRED`, `BLOCKED`, and `DONE`. Only Gate `AI` and Gate `HUMAN` exist. State details, legal transitions, escalation threshold, heartbeat priority, and queue format are in `docs/AUTONOMY.md`; `docs/WORK_QUEUE.md` is the operational source, not a product specification.

Treat `main` as protected even without technical branch protection. Work on at most one checkpoint/PR per invocation. Do not invent work. If nothing is authorized, return `NO_OP`; this is a successful protocol outcome, not `BLOCKED` or a runtime failure. Never expose secrets or sensitive/private information in files, history, branches, commits, PRs, comments, or logs intended for the repository.
