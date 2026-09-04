# My Own Governance

Public, canonical governance baseline for a family of independent personal software repositories. It makes durable repository state—not an agent's memory—the source from which humans and tools can resume work safely.

## Origin and scope

This project is conceptually and documentarily informed by [Innlab-idi/work-governance](https://github.com/Innlab-idi/work-governance), which is distributed under the MIT License. This repository is an independent adaptation: it is not a fork, automatic upstream, or statement of ownership or affiliation. Its text is tailored to personal projects and adds a durable contract for a future CODEX WORKER / AI SUPERVISOR loop.

Everything here is public, including Git history, branch names, commits, pull requests, and comments. Never store credentials, private data, sensitive infrastructure, or unnecessary details about consumer repositories here.

## Document architecture

- [`AGENTS_BASE.md`](AGENTS_BASE.md) is the canonical common agent contract and source for the managed block in consumer `AGENTS.md` files.
- [`docs/AUTONOMY.md`](docs/AUTONOMY.md) defines roles, states, gates, remote-state authority, and the future heartbeat protocol.
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) defines safe repository work from discovery through review.
- [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md) assigns durable information to the right document.
- [`PROJECT.md`](PROJECT.md), [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/DECISIONS.md`](docs/DECISIONS.md), and [`docs/WORK_QUEUE.md`](docs/WORK_QUEUE.md) describe this repository itself.
- [`templates/`](templates/) projects the common contract into consumers while leaving consumer-specific content local.
- [`sync/README.md`](sync/README.md) describes revision-pinned adoption and future synchronization.

The organizing rule is **common where stable, local where specific**. Product requirements, architecture, operational state, and local commands belong to the consumer; reusable safety and authority rules belong here.

## Planned autonomy

The intended flow is:

`HUMAN OWNER → GitHub durable state → CODEX WORKER → branch/commit/PR → AI_REVIEW → AI SUPERVISOR → APPROVED / AI_REWORK / HUMAN_REQUIRED → CODEX WORKER resumes → HUMAN OWNER authorizes merges and material decisions`

The repository establishes only the documentary contract. It does **not** configure Codex or ChatGPT automation, GitHub Actions, scheduled jobs, daemons, external infrastructure, auto-merge, or production access.

## Adoption

A consumer selects and records a specific commit or release revision, copies the applicable templates, fills in local facts, and preserves the provenance. The managed block in `AGENTS.md` is replaced as one unit; local instructions remain outside its markers. Each consumer retains its own `PROJECT.md`, roadmap, decisions, autonomy additions, and `docs/WORK_QUEUE.md`.

There is no automatic synchronization today. Consumers must deliberately review and adopt later baseline changes; local valid work must never be overwritten in the process. See [`sync/README.md`](sync/README.md).

## License and attribution

This repository is licensed under the [MIT License](LICENSE). The approach is adapted from ideas and documentation in `Innlab-idi/work-governance`, also MIT-licensed; see [NOTICE](NOTICE). New wording and personal-governance extensions are maintained here independently.
