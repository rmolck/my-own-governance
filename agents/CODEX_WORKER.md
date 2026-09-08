# CODEX WORKER invocation

This is the reusable bootstrap contract for a repository mutation invocation.

1. Retrieve fresh GitHub durable state and read the published baseline, applicable
   `AGENTS.md`, `docs/AUTONOMY.md`, `docs/EXECUTION.md`, and `docs/WORK_QUEUE.md`.
2. Preserve and continue a legitimate active branch/PR. Process at most one
   checkpoint/PR and follow the priority and authority in `AUTONOMY.md`.
3. Prefer Git-tree work: implementation, tests, refactors, implementation-linked
   documentation, commits, and branch/PR delivery. Once a PR exists, leave routine
   PR coordination and GitHub metadata to AI ORCHESTRATOR/SUPERVISOR when capable.
4. Never make a repository commit that claims an external PR body, comment, check,
   label, or other GitHub metadata was changed when it was not. Report the exact
   capability/access failure instead.
5. Do not self-approve, finalize, merge, cross Gate `HUMAN`, push to `main`, invent
   work/evidence, or expand authority. Return exactly `NO_OP` only after a valid
   fresh-state evaluation finds no authorized transition.

