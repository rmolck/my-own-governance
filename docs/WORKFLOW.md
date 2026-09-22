# Workflow

## Human continuation entry point

The home/developer interaction has one continuation intent: `continue` (or
`run`). It asks AI ORCHESTRATOR to establish fresh durable truth and advance the
authorized cycle as far as its current capabilities and authority permit. The
human does not choose whether the next internal action is planning, worker
execution, review, rework, finalization, a local wake, or an owner decision.

AI ORCHESTRATOR selects that handoff under [`AUTONOMY.md`](AUTONOMY.md), performs
routine transfers directly when capable, and finishes with one concrete outcome:
durable progress and identity, actor/work in progress, capability blocker, or the
exact reserved human decision. GitHub remains the coordination journal; a chat
handoff or status message is not evidence that a branch, PR, comment, check, or
queue transition exists.

## 1. Establish current truth

Read applicable `AGENTS.md`, project and decision documents, and the freshly retrieved published baseline. Inspect repository identity, HEAD, branch, status, remotes, worktree, active branches/PRs, checks, and review discussion. Repository state is durable; conversation is not. Preserve uncommitted and committed work and stop when a material contradiction cannot be reconciled safely.

## 2. Select one authorized checkpoint

Use the selection order in [`AUTONOMY.md`](AUTONOMY.md), based on fresh GitHub durable state. Continue an active legitimate PR before creating replacement work. Confirm dependencies, state, gate, and scope from [`WORK_QUEUE.md`](WORK_QUEUE.md); consult product and architecture documents for requirements.

Roadmap reconciliation does not select executable work. When an authorized
planning checkpoint applies, AI ORCHESTRATOR may decompose only the next valid
phase under [`AUTONOMY.md`](AUTONOMY.md). Its proposed future checkpoints remain
outside the operational queue until a separate admission action confirms that
their dependencies and authority are satisfied; planning completion alone never
makes them `READY`.

## 3. Work safely

Move through a feature branch, never directly through `main`. Make the smallest coherent change for the checkpoint, keep affected durable documentation synchronized, and do not broaden authority because a command is technically possible. Do not destroy, reset, conceal, or rewrite existing work.

## 4. Validate honestly

Run relevant available checks, inspect the full diff, and report exact commands and outcomes. Distinguish a failure from an environment limitation. Never claim a check, evidence, approval, or access that did not occur. Check public output for secrets and private or sensitive information.

## 5. Commit and review

Create focused commits, push the branch, and create or update one PR. Record its branch/PR and relevant result in the queue where the protocol requires it. Set `AI_REVIEW` only when the current relevant HEAD and evidence are ready. The AI SUPERVISOR uses only its three normative decision forms.

For `AI_REWORK`, address findings on the same branch/PR and resubmit. For `HUMAN_REQUIRED`, record the material choice and stop at the gate. For `BLOCKED`, record the objective dependency and revalidation evidence. For Gate `AI`, approval is semantic completion and conditional merge authorization. A separate mechanical finalizer may create only the allowlisted queue-closure commit and merge exactly that derived HEAD after verifying every safeguard in `AUTONOMY.md`; this is not another semantic transition and does not enable auto-merge. Gate `HUMAN`, human-reserved matters, and future authority-policy changes still require explicit owner authorization.

The supervisor reviews only the submitted checkpoint/PR. It records concrete
correctable findings as `AI_REWORK`, uses `HUMAN_REQUIRED` only for an actual
owner-reserved decision, and publishes no decision when tooling prevents a
trustworthy review. It verifies HEAD both before reviewing and immediately
before commenting; a changed HEAD must be reviewed anew.

## 6. Home execution profile

The provider-neutral steps above do not choose an agent host. The repository's
home/developer profile is defined in [`HOME_WORKFLOW.md`](HOME_WORKFLOW.md): it
prefers a capable Codex Cloud worker, retains one manual local wake over the same
state machine, and treats scheduling as optional. Venue selection changes only
the execution path, never checkpoint eligibility, role authority, or evidence.
