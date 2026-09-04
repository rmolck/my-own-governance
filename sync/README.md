# Adoption and synchronization

No automatic synchronization mechanism exists yet. This directory documents a safe future contract; it contains no job, action, daemon, credential, or external integration.

## Initial adoption

1. Select a concrete commit or release revision from this public baseline and record it in the consumer's durable documentation.
2. Review that revision rather than following a moving branch blindly.
3. Copy the project/document templates and the canonical autonomy contract.
4. Replace the consumer `AGENTS.md` managed block between the exact markers as one unit.
5. Preserve all consumer-local content outside the markers.
6. Fill templates only with verified, public-safe local facts; keep consumer operational state in its own queue.
7. Review the complete diff and validate local links and commands before committing through a branch and PR.

## Later updates

Compare the currently adopted revision with the proposed revision. Classify common changes separately from local modifications, replace only managed content, and merge other templates deliberately. Never reset, overwrite, or reconstruct valid consumer work. If a legitimate branch/PR is active, reconcile the update with it.

Adoption does not create an automatic-upstream or affiliation relationship. Each consumer chooses when to synchronize, retains its own history and policies, and is responsible for reviewing changes. A future tool may automate mechanics, but it must keep revision provenance, dry-run/reviewability, local-content preservation, and the authority limits in `docs/AUTONOMY.md`.
