# Adoption and synchronization contract

This is the portable semantic contract for taking this baseline into an
independent consumer repository and later updating the common agent block. It
does not implement a synchronizer, authorize consumer mutation, select a
consumer, schedule work, confer cross-repository product authority, or enable
automatic merge. No job, action, daemon, credential, or external integration is
defined here.

## Terms and authority boundary

- A **baseline revision** is an immutable identity for the complete reviewed
  baseline: a full Git commit object ID, or a release identifier together with
  the immutable commit object ID it resolves to. A branch name, latest release,
  URL without a revision, date, or abbreviated object ID is not sufficient.
- The **source managed block** is the exact region between and including the
  marker lines in [`templates/AGENTS.md`](../templates/AGENTS.md) at the selected
  revision. [`AGENTS_BASE.md`](../AGENTS_BASE.md) is its canonical semantic
  source, but synchronization compares the projected template bytes.
- The **consumer managed block** is the single corresponding region in the
  consumer's root `AGENTS.md`. It is baseline-owned common policy.
- **Unmanaged content** is every byte outside that region and every other
  consumer file. It remains consumer-owned.

The baseline is authoritative only for the source managed block at the selected
revision. The consumer remains authoritative for its product, requirements,
methodology, evidence, commands, decisions, roadmap, queue, gates, repository
policy, and all unmanaged instructions. A baseline change cannot decide those
matters or authorize a consumer change. The consumer chooses a revision and
reviews and accepts the proposed diff under its own governance.

## Adoption

Adoption is the consumer's first deliberate incorporation of a selected
baseline revision. It is complete only when a reviewed consumer commit:

1. contains exactly one well-formed managed block whose content is byte-for-byte
   equal to the selected revision's source managed block;
2. preserves or deliberately establishes consumer-local instructions outside
   the markers;
3. creates and fills any selected templates with verified, public-safe local
   facts rather than copying baseline repository state as consumer truth; and
4. records the baseline repository identity and full adopted commit object ID in
   durable consumer documentation included in the same reviewable change.

The durable adoption record is the evidence used by future comparison. Its file
and field format are consumer-local; it must be unambiguous to a human reviewer
and must not claim a release or commit that was not actually incorporated.
Copying files without that provenance, or merely declaring that a repository
"uses" this baseline, is not adoption under this contract.

## Synchronization

Synchronization is a later, deliberate proposal to move an adopted consumer
from its recorded baseline revision to a different immutable baseline revision.
It is not a reset, merge of repository histories, or general template overwrite.
A synchronization proposal may replace only the consumer managed block with the
source managed block from the proposed revision and update the durable adoption
record to that same revision. Other baseline templates are reference material:
changes to consumer files derived from them require separate, deliberate merges
under consumer authority.

Any edits made locally inside the managed block are divergence from its recorded
baseline, not consumer-owned customization. Synchronization must report that
divergence and fail before writing. Intentional consumer rules belong outside
the markers. A future explicitly governed extension mechanism may define other
behavior, but none exists in this contract and a tool must not invent one.

## Required synchronization checks

A future implementation must be deterministic over explicit source revision and
consumer inputs, and must satisfy all of the following.

### Preconditions (before any write)

1. Resolve and verify one immutable source commit and read all source material
   from that commit, never partly from a moving ref or working tree.
2. Verify the source template contains exactly one begin marker and one end
   marker, in that order, with no nesting, and derive exactly one source block.
3. Verify the consumer `AGENTS.md` has the same exact single, ordered,
   non-nested marker pair. Missing, duplicated, reversed, nested, or otherwise
   ambiguous markers are a visible failure; do not guess or repair them.
4. Read an unambiguous durable adoption record and verify its recorded revision
   exists. Verify the current consumer block equals the source block at that
   recorded revision. A mismatch is visible local divergence and fails closed.
5. Capture all unmanaged bytes and determine the complete proposed diff. Refuse
   paths or changes outside the expressly proposed managed-block replacement and
   adoption-record update. Never discard an active branch, PR, or valid consumer
   work to make synchronization easier.
6. Produce a dry-run/reviewable result before mutation, including old and new
   full revision identities, changed paths, and whether the result is a change,
   no-op, or failure. Passing validation is not authorization to write, commit,
   push, open a PR, or merge.

### Postconditions (after an authorized write)

1. Re-parse both exact markers and verify there remains exactly one ordered,
   non-nested managed block.
2. Verify the consumer block is byte-for-byte equal to the proposed revision's
   source block and the durable adoption record names that same full revision.
3. Verify every captured unmanaged byte is unchanged and no unapproved path was
   changed.
4. Re-run the operation against the resulting tree. It must report the no-op
   described below and produce no diff.
5. Present the complete consumer diff for review under consumer governance.

Validation or write failure must be visible and must leave the consumer tree and
adoption record unchanged. An implementation that cannot make the allowed
updates atomically must stage them in an isolated candidate tree and publish
only after all postconditions pass; it must not leave partial best-effort edits.

## Idempotency and no-op

Synchronization is a **no-op** only when the recorded revision already equals
the proposed full revision, the consumer managed block equals that revision's
source block, marker validation succeeds, and no adoption-record correction or
other file change is needed. A no-op performs no write and creates no commit,
branch, PR, approval, or merge. Equal revisions with malformed markers, local
divergence, or inconsistent provenance are failures, not no-ops.

Applying the same successful synchronization again to unchanged inputs must
produce that no-op. This synchronization outcome is local to the operation and
is not the autonomous-invocation `NO_OP` defined by
[`docs/AUTONOMY.md`](../docs/AUTONOMY.md).

## Review and future implementation

Every adoption or synchronization remains an ordinary consumer change: inspect
the full diff, validate local links and commands, and deliver it through the
consumer's authorized branch/review process. The operation supplies evidence;
it never approves itself. A future implementation checkpoint may choose a
transport or interface and add stronger checks, but it must preserve this
contract's fail-closed boundaries and cannot derive authority from technical
capability.
