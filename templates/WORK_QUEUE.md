# Work queue

This is minimal operational coordination, not a product, architecture, or methodology specification. Link to those durable documents.

| ID | Objective | Dependencies | State | Gate | Active branch / PR | Last relevant result |
|---|---|---|---|---|---|---|

Use only `READY`, `WORKING`, `AI_REVIEW`, `AI_REWORK`, `HUMAN_REQUIRED`, `BLOCKED`, or `DONE`. Use only Gate `AI` or Gate `HUMAN`. Keep an entry concise: stable checkpoint ID, summarized objective, objective dependencies, current state/gate, active branch/PR when present, and last durable result or decision.

Do not add speculative work merely to populate the table. An empty queue means the future worker returns `NO_OP`.
