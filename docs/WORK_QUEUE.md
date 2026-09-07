# Work queue

Operational coordination for this repository only. Requirements and governance rules live in the linked canonical documents; this file does not restate them.

| ID | Objective | Dependencies | State | Gate | Active branch / PR | Last relevant result |
|---|---|---|---|---|---|---|
| GOV-001 | Establish the initial public governance baseline and adoption templates. | Bootstrap repository; owner task specification. | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `518bf20ce69881d92dc9d1bfeba9800c6be4d162`; HUMAN OWNER authorized merge of PR #1. |
| GOV-002 | Define the portable execution contract for one autonomous invocation. | GOV-001 `DONE`; [`AUTONOMY.md`](AUTONOMY.md); [`WORKFLOW.md`](WORKFLOW.md); [`ROADMAP.md`](ROADMAP.md); [`DECISIONS.md`](DECISIONS.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `70fe9327a602a22e288bde374fe444922a743a0f`; HUMAN OWNER authorized merge of PR #5. |
| GOV-003 | Implement a Codex CLI execution adapter as a reference implementation. | GOV-002 `DONE`; [`EXECUTION.md`](EXECUTION.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `6fba65011815771483f4904a3bfed3cfc335024d`; HUMAN OWNER authorized merge of PR #6. |
| GOV-004 | Implement a reference Linux runtime using systemd. | GOV-003 `DONE`; [`EXECUTION.md`](EXECUTION.md); existing [`adapter`](../adapter/README.md). | AI_REVIEW | AI | `codex/crear-gov-004-para-runtime-linux-basado-en-systemd` / PR #7 | Reference Linux systemd runtime complete and ready for AI SUPERVISOR review. |

Future work enters only with a concise objective, objective dependencies, one normative state, one gate, active work identity when present, and the last relevant durable result. Detailed requirements must be linked, not copied here.
