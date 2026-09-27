# Remaining source bugs — bounded revalidation and repair

## Owner intent and source binding

The owner requests revalidation of Aether issues **#267, #352, #421, #422, #444 and #460**, correction and closure of still-applicable defects through the existing Supervisor/Implementer pipeline, without overengineering, excessive verification, an RC17 or indefinite tasks. This is one source-backlog sweep, not a release program. Existing owner-closed behavior/qualification tickets are not reopened.

- Aether source base: `9ecacf07d1afdb7d0edeb1b9ef906004bc3b5b5b`.
- Maintained Hermes fork base: `DarkArty07/aether-hermes@58750d6cf8182c0ff5093719b9e7cc5026621fbf` (`aether-main` at intake). The shared checkout is not the working copy; use an isolated fork checkout if needed.
- Portable Project: `12027989-a08f-41cd-a82c-54ff1bfb6b03`. Keep the existing repository Project binding and the exact execution board supplied by the handoff.
- Graph navigation was available at the Aether base with structural coverage; the unrelated dirty `plan-rc6.md` was excluded. The source references below, not the graph, support decisions.
- The existing local Objective Plan retains the historical diagnoses and budgets. Workers must be able to execute from this file, the finalized contract and the linked issues without that private plan.

## Scope and disposition

Each issue gets an attributed result at exact revisions, not an automatic new card or a fresh test campaign:

1. **Applicable and repaired:** causal regression/source evidence, smallest complete correction, bounded independent review, required repository checks and normal source merge; close the issue as fixed in source, without installed-behavior claims.
2. **Demonstrably superseded/not applicable:** name the current source change or removed premise and the evidence that covers the reported case; close with that precise reason. An old date or an unchanged passing rerun alone is insufficient.
3. **Inconclusive/blocked by missing evidence or authority:** record the exact remaining uncertainty and useful preserved evidence, then stop that investigation and leave the issue open. This is a completed diagnostic disposition, not acceptance of an unfixed bug. It must not strand independently repairable work.

An implementation may make equivalent reversible internal choices within the boundaries below. A new public interface, changed guarantee, global policy, dependency/runtime selection or materially different causal premise returns to Morfeo through existing collaboration before mutation. Do not turn investigation into implementation based only on a ticket being open.

## Issue boundaries and current findings

### #460 — rooted decision-card parentage

**Applicable source defect already reproduced** at the exact fork base: both `create_task(parents=[canonical_root, independent_decision])` and `link_tasks(independent_decision, child_of_root)` persist two roots. `get_collaboration_root` then returns no unique root and the Aether reviewer correctly refuses to spawn. Historical repaired live graphs are evidence, not targets to edit. Prior disposable REDs use an opted-in root, matching board/Project identity and a native `collaboration_opted_in` event; a correctly anchored root→decision→unit control preserves one root. The earlier dispatch control used a simulated spawn, not a real model reviewer.

**Decided correction:** reject ambiguous parentage atomically rather than silently inventing an edge or selecting a root. Cover both native insertion paths and downstream nodes affected by a new edge. Corroborate Aether opt-in using persisted native events, the actual connection's board metadata, contract/version and Project identities; do not trust an ambient/default board or an isolated Aether-looking key. Do not equate generic no-opt-in with corrupt/mismatched Aether claims. Validation belongs inside the existing write transaction before committed rows, links, events, subscription inheritance or workspace side effects can escape. Use the existing native validation-error surface, not a new workflow engine.

Preserve generic Hermes multi-root DAG behavior, legitimate root→decision then decision→unit insertion, missing-parent/cycle refusal, review fail-closed behavior and the merged #475 review-dispatch correction. Never rewrite existing historical graphs or relax `_corroborate_aether_review_opt_in` merely to make dispatch pass. The producer guidance in R7's existing decision-card pattern must require canonical rooting before participation in an opted-in flow. The helper/SQL shape remains local implementation freedom.

The invariant is the same exact canonical root, not merely any single ancestor root. Minimal controls are: valid rooted insertion; rejected ambiguous `create_task` with no persisted task/edges/events; rejected `link_tasks` with links/status/subscriptions unchanged; an edge into the opted-in root or an ancestor of affected descendants cannot replace that root; generic multi-root remains allowed; and a pre-damaged Aether graph still fails review. Use existing cycle/missing-parent and #475 tests rather than constructing an exhaustive graph campaign.

Inspected fork locations: `hermes_cli/kanban_db.py` blob `8129a4981dbad60020de86e8acfc723a99cc369a`; `create_task` parent insertion around 4651–4745, `link_tasks` around 5211–5239, `_read_board_meta_for_conn` around 5436–5461, `_find_ancestor_roots`/`get_collaboration_root` around 5619–5665, and `_corroborate_aether_review_opt_in` around 1323–1407. Do not directly reuse the reviewer-only identity validator as a creation guard when its task/reviewer prerequisites do not exist yet. Reuse its corroboration rules at the correct lifecycle boundary.

### #267 — disposable native writers

Aether already has `scrub_inherited_identity`, `isolated_hermes_env`, root-resolution preflight and `require_verified_writer_context` in `src/aether_agents/lab/isolation.py`. The latest relevant correction is `6f753d0c`; owned dispatch, persistence, observation and runner paths use the gate. The suspected embedded `_observe_native_affinity_controls` path was previously verified to enter through the gate: two focused regressions passed, including inherited-identity and escaped/symlink destinations. Reuse that evidence if its relevant blobs and assumptions are unchanged.

The recurrence was ad-hoc Python setting only `HERMES_KANBAN_HOME` while inheriting the higher-priority `HERMES_KANBAN_DB`. Revalidate the **Aether-owned executable probe entry points**, not an imagined universal Python sandbox. Repair only a demonstrated owned-path gap, before the first native connection/writer, using the existing constructors and gate. Use a disposable witness database, never an actively written production board as an immutable witness. Preserve native production DB-pin precedence. A helper cannot forbid arbitrary Python that never calls it; a global `kanban_db.connect()` restriction or a broader PD-71 workspace hook is not authorized. If no uncovered owned path is found and closure would require that broader boundary or historical live-card archival, return that precise scope/capability question and leave the issue open instead of claiming universal isolation.

### #422 — isolated observation identity

Trace the exact canonical `prepare_handoff` identity into board binding, root task, run/session provenance and coverage. Current source owners are `src/aether_agents/observation/capture/hermes_plugin.py` (including `_reconstruct_board_bindings`, `_reconcile_native_for_collector`, native ID/session rejection paths) and `observation/reduce/reconciliation.py`; reuse existing adapter fixtures. There have been later observation repairs since the original report, so establish applicability against the current producer/consumer payload before changing code.

For a demonstrated mismatch, adapt the producer/binding at its existing boundary: exact portable/native Project, contract/version, board and session provenance must agree. Valid isolated handoffs must not produce contradictory identity gaps; genuinely missing/conflicting provenance must still fail closed with truthful coverage. Do not drop privacy/authority checks, invent IDs, substitute the default board or edit/rebuild live journals to produce a ready result. Pre-decomposition absence of required units is normal, not itself a bug. Scope is source integration, not a live agent canary or revival of the withdrawn #488 acceptance gate.

A normal observation/board comparison from this actual pipeline may be reused as organic evidence, with exact identity, revision and coverage limits. Do not create extra agents or boards solely to manufacture such evidence; normal non-relocated execution alone does not disprove a relocation-specific defect.

### #352 and #444 — bounded intermittent diagnosis

For #352, the existing test in `tests/test_observation_lifecycle.py::test_two_process_transitions_with_one_expected_active_have_one_commit` already starts both processes at a gate, waits for readiness and expects one committed and one stale result with `ACTIVE_RELEASE_CAS_MISMATCH`. Historical unchanged-source evidence includes 4 sequential, 8 bounded-concurrent and 20 further sequential passes plus the lifecycle module. Do not repeat those campaigns. Inspect `_run_cas_transition`, process exit/result publication and `ReleaseStore` only where a concrete current clue points. Keep the existing timeouts and one-commit invariant; do not conceal a missing result by increasing waits.

For #444, the reported Python 3.12 node is `tests/test_observation_journal_storage.py::test_checkpoint_sink_derives_review_authority_from_durable_native_assignment`. It flushes the request before rejecting a forged approval and accepting the legitimate one. Inspect `observation/checkpoint.py`, collector snapshots and journal flush/lock outcomes; retain fail-closed authority. A targeted check on the originally affected Python version and a discriminating deterministic fixture are appropriate when there is new evidence. A pass streak is not a cause. Correct a proven fixture synchronization defect or product defect, not the expected verdict.

For either issue, after current source/history inspection and a focused check fail to distinguish a causal mechanism, stop with an inconclusive disposition. No unchanged-source stress loops, no broad suite repetition as diagnosis, and no new card/contract to reset this bound. Additional investigation requires new evidence and a specific bounded question returned to Morfeo.

### #421 — historical SIGBUS, evidence-limited diagnosis

The recorded native stack proves SQLite WAL access at a SIGBUS, but not the database, mapping or initiating writer. Later `gateway exited`/ENOSPC symptoms are not proof of the same cause. Current intake found no `coredumpctl` command and an empty local system coredump directory; no new core was opened. Treat that missing evidence as a real limit, not a reason to invent a repair or run a stress campaign.

Use only retained sanitized stack/incident metadata and narrowly relevant current source or existing read-only logs. No raw core-memory inspection/upload, production DB probing/checkpoint/VACUUM/repair, dependency installation merely to extend diagnosis, gateway restart or worker interruption. Without evidence identifying a current causal operation, report the diagnostic limit and leave the bug open. A demonstrated obsolete premise may be reported distinctly, never labelled a causal fix based only on non-recurrence.

## Verification and convergence

Testing standard is the existing `CONTRIBUTING.md` (focused tests while iterating; the documented exact-Hermes runner for boundaries that require it; normal required CI). Representative Aether entry points are `uv run --frozen python scripts/run_tests.py -- -q <affected test paths>` using `tests/test_lab_writer_isolation.py`, the two existing gate regressions in `tests/test_e2e_harness.py`, native observation adapter/checkpoint tests and the named #352/#444 nodes as applicable. These are disposable deterministic tests, not a new agent campaign. A fork delta uses `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh <affected test paths> -q`, including `tests/hermes_cli/test_kanban_collaboration.py` and `tests/hermes_cli/test_kanban_session_affinity.py` for #460. Fixtures must scrub inherited identities and corroborate disposable destinations before any writer.

- Establish each starting state/oracle before an expensive run. Reuse valid reviewed evidence when code, environment and affected invariant are unchanged. Broad repository gates belong at the appropriate integration/CI boundary, not every review iteration.
- Preserve required checks; no skips, longer timeouts or weaker assertions merely to obtain green. For a proven change, verify the actual regression plus affected negative controls. Record baseline-shared/environment failures honestly.
- At most two ordinary review returns per logical unit, from complete durable history. Review the delta on re-review. Stop earlier without progress or an improved diagnosis; no successor card resets a failure budget.
- A diagnostic unit ends at its disposition. Do not generate speculative implementation, repeated measurement jobs or a new qualification framework just to keep a unit busy. Healthy independent units continue.
- Source fixes may land through normal reviewed PR/check/merge paths in the two provisioned repositories. If a fork delta is required, reconcile a portable HLP artifact, exact source provenance and existing ledger conventions; keep release selection unchanged and record deferred adoption, not another release contract.

## Authority, preservation and closeout

No RC17, version/tag/release/package preparation, live adoption/rollback, profile/model/provider/router/credential change, upstream PR, history rewrite, bypass, manual site deployment or service change. No new public feature, new role, general collector, permission micro-gate or unrelated cleanup. Preserve the owner's pre-existing dirty file, historical evidence and real task/session state. Necessary existing documentation updates remain scoped; any deployment consequence not already authorized returns to Morfeo before merge.

Supervisor owns the breakdown, independent review, scoped source integration, GitHub disposition and cleanup of this execution. It may combine related fixtures where they share an actual mechanism; it must not make all six bugs wait for one indivisible release gate. Morfeo creates no implementation units. A result is not accepted merely because the board is terminal; the final evidence maps all six issues to their exact source/result/disposition and attributes direct checks versus reused evidence.

Use the existing workspace/temporary-storage hygiene procedure. Keep test state under one identified disposable root, check the destination's capacity before substantial materialization, retire owned intermediates after their last consumer and evidence transfer, and retire worktrees only after review/integration/dependency gates. No broad `/tmp` wipe or deletion of unknown/historical work. Release conclusions for this source scope are `release_action=defer`, `release_channel=none`; classify actual compatibility impact from the delivered deltas rather than assuming a release.
