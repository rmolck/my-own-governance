# Work queue

Operational coordination for this repository only. Requirements and governance rules live in the linked canonical documents; this file does not restate them.

| ID | Objective | Dependencies | State | Gate | Active branch / PR | Last relevant result |
|---|---|---|---|---|---|---|
| GOV-001 | Establish the initial public governance baseline and adoption templates. | Bootstrap repository; owner task specification. | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `518bf20ce69881d92dc9d1bfeba9800c6be4d162`; HUMAN OWNER authorized merge of PR #1. |
| GOV-002 | Define the portable execution contract for one autonomous invocation. | GOV-001 `DONE`; [`AUTONOMY.md`](AUTONOMY.md); [`WORKFLOW.md`](WORKFLOW.md); [`ROADMAP.md`](ROADMAP.md); [`DECISIONS.md`](DECISIONS.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `70fe9327a602a22e288bde374fe444922a743a0f`; HUMAN OWNER authorized merge of PR #5. |
| GOV-003 | Implement a Codex CLI execution adapter as a reference implementation. | GOV-002 `DONE`; [`EXECUTION.md`](EXECUTION.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `6fba65011815771483f4904a3bfed3cfc335024d`; HUMAN OWNER authorized merge of PR #6. |
| GOV-004 | Implement a reference Linux runtime using systemd. | GOV-003 `DONE`; [`EXECUTION.md`](EXECUTION.md); existing [`adapter`](../adapter/README.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `fa65e3b45b121bd42f6bdb6691cad68968f178ff`; HUMAN OWNER authorized merge of PR #7. |
| GOV-005 | Validate heartbeat behavior reproducibly against the autonomous and execution contracts. | GOV-004 `DONE`; [`AUTONOMY.md`](AUTONOMY.md); [`EXECUTION.md`](EXECUTION.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `72624d4d39c2481f6dee39e70749b7bdd0f55267`; HUMAN OWNER authorized merge of PR #8. |

| GOV-006 | Simplify approval closure and delegate Gate-AI merge authorization to the AI SUPERVISOR. | GOV-001..GOV-005 `DONE`; explicit HUMAN OWNER authorization in the originating task; [`AUTONOMY.md`](AUTONOMY.md); [`EXECUTION.md`](EXECUTION.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `1d4e6537d7c539270870a37bfccf5e33adf2ef2b`. |
| GOV-007 | Configure and reproducibly validate the AI SUPERVISOR contract. | GOV-001..GOV-006 `DONE`; [`AUTONOMY.md`](AUTONOMY.md); [`SUPERVISOR_VALIDATION.md`](SUPERVISOR_VALIDATION.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on HEAD `0ccf358abbf564a432394b165671a6caca53bf1f`. |
| GOV-008 | Execute end-to-end acceptance tests for the autonomous governance protocol. | GOV-001..GOV-007 `DONE`; [`ACCEPTANCE_VALIDATION.md`](ACCEPTANCE_VALIDATION.md). | DONE | AI | — | `AI_SUPERVISOR: APPROVED` on substantive HEAD `463c3b50277987c0adfccfde276ea68d0b08297b`; HUMAN OWNER authorized merge of PR #12. |

| GOV-009 | Define actor ownership, versioned agent instructions, and runtime timing evidence ([issue #13](https://github.com/rmolck/my-own-governance/issues/13)). | GOV-001..GOV-008 `DONE`; explicit HUMAN OWNER authorization in issue #13. | AI_REVIEW | AI | `codex/gov-009-actor-ownership` / PR pending | Implementation and deterministic tests completed locally; publication evidence is recorded only after real publication. |

Future work enters only with a concise objective, objective dependencies, one normative state, one gate, active work identity when present, and the last relevant durable result. Detailed requirements must be linked, not copied here.
