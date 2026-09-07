# Heartbeat behavior validation

This is the durable validation record for GOV-005. It validates the observable
semantics in [`AUTONOMY.md`](AUTONOMY.md) and [`EXECUTION.md`](EXECUTION.md);
it is not another normative state machine. The structured oracle in
[`validation/heartbeat_harness.py`](../validation/heartbeat_harness.py) exists
only inside the test surface. Production selection remains the responsibility
of the governance-aware worker, while the adapter and runtime remain mechanical.

## Strategy and result taxonomy

The suite uses explicit structured fixtures rather than parsing free-form agent
text. Semantic tests pass a single invocation an ordered durable-state fixture.
The freshness test creates a temporary bare Git remote, retains an old clone,
and publishes an incompatible newer commit. It then resolves the current remote
SHA with `ls-remote`, observes a stale `refs/remotes/origin/main`, performs a
directed fetch into that exact remote-tracking ref, and requires SHA equality
before reading durable state. Negative fixtures simulate remote lookup failure,
directed-fetch failure, and a ref that remains stale after fetch. Runtime and
adapter boundary tests use isolated fake executables and sentinel
files. No test writes to this repository's `main`, uses a network, invokes real
Codex, merges, or activates a systemd service/timer.

Assertions keep these contract results distinct: `Transition completed`,
`NO_OP`, checkpoint `BLOCKED`, runtime/execution failure, and
interrupted/invalid execution. `NO_OP` is never represented as a state. Fixture
metadata for prior output, examples, and agent memory is deliberately ignored;
only the newly cloned durable fixture supplies checkpoint authority.

## Scenario matrix

“Observed” records the deterministic assertion supplied by the associated test;
a passing full suite reproduces every row.

| ID | Initial durable state / boundary | Expected action and observed assertion | Result | Evidence |
|---|---|---|---|---|
| H-01 | No actionable checkpoint | `NO_OP`; no mutation, invented checkpoint, PR, or `BLOCKED` | PASS | `test_h01_no_authorized_work_is_no_op_without_mutation` |
| H-02 | Two eligible `READY` / Gate `AI` entries | First changes `READY -> WORKING`; second remains untouched | PASS | `test_h02_ready_ai_selects_only_one` |
| H-03 | `READY` / Gate `HUMAN` | `NO_OP`; gate is not crossed | PASS | `test_h03_ready_human_is_no_op` |
| H-04 | `AI_REWORK` plus `READY` / Gate `AI` | Rework changes `AI_REWORK -> WORKING`; ready entry remains untouched | PASS | `test_h04_ai_rework_precedes_ready_ai`, `test_published_priority_order_is_exact_for_actionable_entries` |
| H-05 | Legitimate `WORKING` PR at its own HEAD and advanced baseline | Existing PR/HEAD is continued without reconstruction or transition | PASS | `test_h05_working_preserves_existing_pr_and_head` |
| H-06 | `AI_REVIEW` without decision | `NO_OP`; no implicit approval or closure | PASS | `test_h06_ai_review_without_decision_is_no_op` |
| H-07 | Gate-`AI` `AI_REVIEW`, current-HEAD approval, and another ready item | Semantically complete and merge authorized; allowlisted finalization records `DONE`; no semantic transition or second selection | PASS | `test_h07_current_approval_semantically_completes_and_authorizes_merge` |
| H-08 | Approval/closure/merge safety variants | Stale or later-invalidated approval, Gate `HUMAN`, non-allowlisted path or queue content, failed checks/mergeability, and reserved matters cannot merge; exact allowlisted closure from approved HEAD that changes only that checkpoint's state and approval metadata preserves authorization; changing another checkpoint, priority, gate, objective, dependencies, or unverified result metadata does not; auto-merge stays disabled | PASS | `test_h08_stale_approval_does_not_close_new_head` and `test_h08_*` safety tests |
| H-09 | `HUMAN_REQUIRED`, no independent work | `NO_OP`; no human boundary crossing | PASS | `test_h09_human_required_without_independent_work_is_no_op` |
| H-10 | `BLOCKED`, objective cause persists | `NO_OP`; no compensating work | PASS | `test_h10_persistent_blocked_is_no_op` |
| H-11 | Objective resolution durably records `READY` or `WORKING` | Only recorded `READY -> WORKING`, or continuation of recorded `WORKING` | PASS | `test_h11_resolved_block_only_uses_recorded_ready_or_working` |
| H-12 | Local `origin/main` says `READY`; remote `main` says `DONE` | Remote SHA is resolved, directed fetch updates `origin/main`, equality is verified, then `NO_OP`; lookup/fetch/ref-update failures prevent selection and are execution failures | PASS | `test_h12_updates_stale_remote_tracking_ref_before_evaluation`, `test_h12_unreachable_remote_is_execution_failure_without_selection`, `test_h12_directed_fetch_failure_does_not_use_stale_ref`, `test_h12_unupdated_tracking_ref_mismatch_prevents_selection` |
| H-13 | Advanced baseline plus legitimate active PR/HEAD | Existing PR is selected; replacement ready entry is untouched | PASS | `test_h13_pr_continuity_wins_after_baseline_advance` |
| H-14 | Runtime lock already held | Adapter sentinel absent; `lock_contended`, exit 0; durable sentinel unchanged | PASS | `test_occupied_lock_skips_adapter_and_exits_cleanly` |
| H-15 | Missing checkout, adapter, Python, or Codex executable | Runtime/execution failure, never `NO_OP`/checkpoint `BLOCKED`; durable sentinel unchanged | PASS | `test_preflight_failure_is_runtime_failure`, `test_missing_adapter_and_python_are_preflight_failures`, `test_launch_failure_is_execution_failure` |
| H-16 | Adapter invalid, interrupted, or unknown exit | `interrupted_invalid`; no trustworthy governance result or durable mutation | PASS | `test_invalid_success_output_is_invalid_execution`, `test_signalled_cli_is_interrupted_execution`, `test_adapter_invalid_and_interrupted_are_propagated`, `test_unknown_adapter_status_maps_to_invalid` |
| H-17 | Approved finalization plus another ready action | Finalization is not a semantic transition, cannot decide authority, and selects no second checkpoint | PASS | `test_h17_finalization_is_not_a_transition_or_second_selection`, `test_h17_finalizer_does_not_decide_gate_or_reserved_authority` |
| H-18 | Two actionable PR/checkpoints | Only first PR/checkpoint advances | PASS | `test_h18_only_one_pr_even_when_two_reworks_are_possible` |

The cross-cutting priority test asserts the published order without adding it to
`runtime/systemd_runner.py`: `AI_REWORK`, approved mechanical finalization,
`WORKING`, `READY` / Gate `AI`, then non-action for `READY` / Gate `HUMAN`,
undecided `AI_REVIEW`, `HUMAN_REQUIRED`, and persistent `BLOCKED`.


## Operational limitation demonstrated

A successful interactive evaluation does not establish that an unattended
scheduler can do the same work. Interactive and runtime processes can differ in
identity, agent home, sandbox, network access, credentials, and permission to
write Git metadata. Each effective runtime therefore has to demonstrate both
remote visibility and the ability to update and verify its own remote-tracking
ref. Failure at any of those steps is a runtime/execution failure: it is not
`NO_OP`, does not authorize selection from stale state, and must not mutate a
checkpoint to `BLOCKED`. This portable constraint does not prescribe a host OS,
scheduler, credential mechanism, or private deployment detail.
