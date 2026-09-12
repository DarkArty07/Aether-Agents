# MON-05-R1 Implementation Evidence — deterministic runtime clock for the handoff regressions

Portable evidence receipt for the bounded MON-05 repair unit (card `MON-05-R1` under
Objective Contract `oc_f8c9fc9320587cf3@v1`). This is a test-determinism repair; no
production behavior changed.

## Scope and changed paths

| Path | Change |
| --- | --- |
| `tests/test_telegram_monitor_runtime.py` | Controlled runtime clock for the regressions that read a store-anchored handoff through the direct runner paths; deterministic clock injected into the two real-subprocess pre-check probes; one new freshness-boundary regression. |
| `specs/telegram-monitor/evidence/MON-05-R1.md` | This receipt. |

Nothing else changed. `src/aether_agents/monitor/runtime.py`, every other production/test/
spec/contract file, root `AGENTS.md`, dependencies/lockfiles, runtime state and all MON-06
paths were untouched.

## Base reconstruction

- Base accepted at `2d49418b2ac9a3f64764b84e1b071df48b85070f` (`git merge --ff-only
  2d49418`; the branch started on an ancestor, so the fast-forward was clean).
- Blob verification before editing:
  - `tests/test_telegram_monitor_runtime.py` → `0701d0194a84f64cc27ae7ddd83ce4b7b651e376` (matched)
  - `src/aether_agents/monitor/runtime.py` → `4144bc95b2d2ba49b11fc6996bfc672ea1c01d66` (matched)

## Root cause

D9/AC-6 requires a fresh handoff to fence exactly one narration and expired/stale
handoffs to fail closed. `_read_handoff(require_fresh=True)` compares
`expires_at_utc <= datetime.now(timezone.utc)` and has no injectable clock: the runner
hook paths (`run_precheck` → `_resume_pending_narration`/`_fence_handoff`,
`handle_post_llm_call`/`handle_session_end`/`reporter_snapshot` →
`_claim_pending_lease`) call it with the default real clock.

The suite fixes every store on `ANCHOR = 2026-09-10T12:00:00Z` and creates six-hour
narration handoffs expiring at `2026-09-10T18:00:00Z`. Once the host clock passed that
instant, the stores still considered those handoffs live while the runner paths rejected
them as stale, so ten regressions flipped even though their bodies were unchanged.

## Change

1. `_FrozenRuntimeDateTime` plus the `frozen_runtime_clock` fixture install a controlled
   runtime clock at the store anchor for the regressions whose outcome depends on
   `_read_handoff` freshness. The real comparison (`expires <= now`), the six-hour TTL and
   every ownership/session/cutoff/job fence keep running exactly as production runs them;
   only `datetime.now` is pinned to the same instant as the store.
2. The two real-subprocess probes (a single pre-check child and the two-children fence)
   now share `_PRE_CHECK_CHILD_DRIVER`, which runs the real packaged
   `main_precheck` entry point in a separate process with the same controlled instant for
   the child's runtime clock and its default store clock. Without that, a handoff written
   by one process would expire against the other process's clock and the regression would
   still flip with the host date. Both regressions now also assert the child-written
   handoff expiry is exactly `ANCHOR + 6h`, so a silently ineffective injection fails
   loudly instead of passing by accident.
3. One new regression, `test_read_handoff_freshness_boundary_is_exclusive_at_expiry`,
   pins the boundary itself: `expires == now` is stale, `expires == now + 1µs` is fresh,
   for both an explicit instant and the controlled default clock.
4. The spool-pruning regressions (`handle_post_tool_call` /
   `handle_session_end_direct`) deliberately keep the real clock: `_prune_direct_records`
   compares real file mtimes against `datetime.now`, so a frozen clock there would
   introduce a new host-date dependence instead of removing one.

Decorated regressions: the ten named in the card plus
`test_precheck_waits_while_a_live_narration_owns_the_report` (its assertion outcome was
already invariant, but pinning it keeps it exercising the handoff fence rather than
silently drifting to the lease path) and the new boundary regression. No assertion was
deleted, weakened, skipped or xfailed; the only removed lines are the two duplicated
inline driver blocks replaced by the shared constant.

## Acceptance-to-evidence mapping

| Card item | Check executed | Observed result |
| --- | --- | --- |
| 1. Reproduce the pre-fix wall-clock failure set at base | At host `2026-09-10T18:29Z`, on the unmodified base: `uv run --frozen pytest -q --tb=no tests/test_telegram_monitor_runtime.py` | **10 failed, 45 passed** — exactly the ten named regressions (`test_precheck_ongoing_work_wakes_with_bounded_context_and_pending_lease`, `test_post_llm_call_persists_only_a_validated_narrator_result`, `test_post_llm_call_rejects_malformed_or_fabricated_narratives`, `test_session_end_delivers_only_for_the_owned_reporter_and_advances_on_confirm`, `test_session_end_sends_only_a_notice_for_rejected_narration`, `test_precheck_child_handoff_reaches_the_exact_reporter`, `test_two_real_precheck_children_wake_exactly_one_narration`, `test_reporter_snapshot_requires_the_exact_live_handoff`, `test_reporter_requires_the_exact_precheck_handoff`, `test_reporter_claim_is_fenced_to_the_exact_session`) |
| 2. Focused suite passes on the unmodified runtime | `uv run --frozen pytest -q tests/test_telegram_monitor_runtime.py` | **56 passed** (55 pre-existing + 1 new boundary regression) at host `2026-09-10T18:4xZ`, i.e. past the old failure instant |
| 3. Pre-expiry accepted / at-expiry rejected, existing expired-handoff and ownership regressions meaningful | `test_read_handoff_freshness_boundary_is_exclusive_at_expiry`; the expired-handoff blocks inside `test_reporter_snapshot_requires_the_exact_live_handoff` and `test_reporter_requires_the_exact_precheck_handoff`; the foreign-holder/job/cutoff and second-session refusals in the same regressions | `expires == now` → refused (explicit instant and controlled default clock); `expires == now + 1µs` → accepted; `now == expires + 1µs` → refused again. The 2020-expiry fixtures are still refused and every foreign holder/session/cutoff/job fence still rejects. Nothing weakened |
| 4. Routed three-file command removes the ten clock-window failures | `uv run --frozen python scripts/run_tests.py -- -q --tb=no tests/test_telegram_monitor_runtime.py tests/test_public_artifacts.py tests/test_observation_lifecycle.py` | Baseline (pre-fix): **17 failed, 133 passed**. Candidate: **7 failed, 144 passed**. Remaining red is exactly the six routed lifecycle entry-point allow-list collisions (`tests/test_observation_lifecycle.py`, MON-05 §"Cross-unit collision") plus the unchanged public-artifact issue #364 (`test_tracked_public_surface_contains_no_operator_paths`). No owner file was edited |
| 5. Static gates and boundary proof | `ruff check`, `ruff format --check`, `python -m compileall -q`, `git diff --check`, `git diff 2d49418 -- src/aether_agents/monitor/runtime.py`, `git status --porcelain` | `All checks passed!`; `1 file already formatted`; compileall clean; `git diff --check` clean; the runtime-module diff is **empty**; the only modified path is the writable test file |

## Supplementary clock-probe evidence

To check host-date independence beyond the current instant, the suite was re-run with a
temporary `LD_PRELOAD` probe (compiled outside the repository, not committed) that shifts
the process wall clock while leaving `CLOCK_MONOTONIC` and kernel file mtimes alone.

| Simulated host instant | Base `2d49418` | Candidate |
| --- | --- | --- |
| `2026-09-10T17:59:00Z` (pre-expiry) | 55/55 per the routed MON-05/MON-06 observation (not re-run here) | **56 passed** |
| `2026-12-31T12:00:00Z` (far future) | 14 failed, 41 passed | **4 failed, 52 passed** |
| `2026-02-14T09:00:00Z` (far past) | — | **56 passed** |

Reading of this table, stated honestly:

- The ten clock-window failures are gone at every simulated instant; the candidate only
  fails where the base fails too.
- The four residual failures at the far-future instant are the direct-spool regressions
  (`test_direct_enrollment_requires_an_exact_project_bound_session`,
  `test_direct_turn_end_marks_flags_and_continuation_opens_a_new_interval`,
  `test_direct_records_reject_unsafe_reported_summaries`,
  `test_direct_enrollment_rejects_gateway_service_and_foreign_profiles`) and they fail
  identically on the base. They are an artifact of the probe, not a host-date dependence:
  the probe shifts clock reads only, so `_prune_direct_records` sees a future "now"
  against a real (unshifted) file mtime and prunes the spool it just wrote (observed
  directly: the regression fails on an empty spool, `len(records) == 0`). On a genuinely
  dated host both the runtime clock and the file mtimes come from the same host clock, so
  the comparison stays consistent — which is exactly why those regressions keep the real
  clock instead of taking the fixture.

## Compatibility and residual risk

**Unit compatibility impact: `none`.** Test-only change in one test module plus this
receipt; no production interface, behavior or dependency changed, and the production
freshness path still rejects `expires_at_utc <= current real UTC` by default.

Residual risks, stated honestly:

- The fixture replaces the runtime module's `datetime` name for the decorated
  regressions, so any *future* host-bound `datetime.now` read added to those paths would
  see the controlled clock. The two boundary/child-expiry assertions make the pinned
  clock explicit, and the four spool regressions keep the real clock on purpose; a future
  unit that adds another wall-clock consumer to those paths must decide the same question
  explicitly.
- The controlled clock is the store anchor the suite already uses; the controlled window
  is the same six-hour narration TTL production uses. The "wall-clock advance" in the
  two-children regression is still represented by expiring the handoff artifact, as
  before.

## Deliberate non-effects

No production/spec/contract edit, no Objective Contract access, no dependency or lockfile
change, no live model call, no Telegram send, no profile/job activation, no credential or
configuration operation, no push, PR, merge, tag or issue mutation. All verification ran
in the assigned worktree against disposable state roots, disposable Hermes homes and fake
senders.
