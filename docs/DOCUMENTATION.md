# Documentation model

Versioned documents are persistent project memory. Put each fact in one authoritative place and link to it rather than copying rules. Keep shared governance generic and local truth close to its consumer.

| Document | Responsibility |
|---|---|
| `AGENTS.md` | Self-contained operating rules visible to agents, with managed common content and unmanaged local instructions. |
| `PROJECT.md` | Purpose, boundaries, outcomes, and product-level context. |
| `docs/AUTONOMY.md` | Normative roles, authority, states, gates, selection, and safety contract. |
| `docs/EXECUTION.md` | Normative portable boundary for invocation, adapter, and scheduler/runtime mechanics. |
| `docs/ROADMAP.md` | Informative direction: now, next, later; not live checkpoint status. |
| `docs/DECISIONS.md` | Consequential decisions, rationale, and consequences; not trivial implementation choices. |
| `docs/WORK_QUEUE.md` | Minimal current checkpoint coordination; not requirements, architecture, or methodology. |
| PR and commits | Reviewable change evidence and discussion tied to concrete Git objects. |

## Managed agent block

The common block between the exact managed markers is replaced as a unit during adoption/synchronization. It must be sufficiently self-contained for a consumer whose agent has no memory of this repository. Consumer-specific commands, constraints, and facts remain outside the markers and must not be overwritten.

## Writing durable truth

State evidence separately from inference. Link requirements to their canonical document. Update documentation in the same change when behavior or authority changes. Never use a queue entry as a second product specification. Never store secrets, personal/private data, sensitive operations, or unnecessary repository details in public documentation or history.

Templates contain explicit adoption instructions. Consumers replace template guidance with verified local facts and record the adopted baseline revision; they do not fabricate missing information.
