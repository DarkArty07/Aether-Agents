# LC-BLOCK Implementation Evidence — release blockers #437 and #438

**Unit:** LC-BLOCK (task `t_8a02a727`)
**Objective Contract:** `oc_3397f9f05d780f8e@v1` (`.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md`, SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`)
**Source:** contract in-scope 2; deliverable D7; AC-10 (focused regressions); issues [#437](https://github.com/DarkArty07/Aether-Agents/issues/437) and [#438](https://github.com/DarkArty07/Aether-Agents/issues/438); Supervisor breakdown `specs/001-aether-v1-productization/tasks.md` (§LC-BLOCK) and shared decisions 11, 13, 14, 16
**Base:** `410c172ae69ffa87f6e32960ae4aef3b8d6598f0` (verified with `git rev-parse HEAD` on a clean worktree before editing)
**Candidate:** see §8
**Phase:** Implementer unit; **no live effect performed** — no push, PR, merge, tag, release, issue mutation, service restart, activation, board write or credential/provider/model change. All test state is disposable (`tmp_path`, `/tmp` scratch); the operator's live profile is never read, written or required.
**Unit compatibility impact:** `patch` — three literal manifest lines, one Monitor-laboratory fixture correction and test-isolation corrections. No product surface, CLI, schema, release lock or shared interface changes; `src/aether_agents/**` is untouched. Aggregate `release_impact`/`release_action`/`release_channel` remain LC-INT/LC-CLOSE's conclusion.
**Review lane:** same-card Supervisor review (`kanban_request_review`, reviewer `supervisor`).

---

## 1. RED facts reproduced on the unchanged unit base

Every failure below was reproduced before any edit, with the baseline still intact.

| # | Defect | Command (canonical exact-Hermes bootstrap) | Observed |
| --- | --- | --- | --- |
| R1 | #437 part 1 — tracked patch missing from the literal manifest | `uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | `1 failed` — `assert expected == actual` |
| R2 | #437 part 2 — D15R fixture review request refused | `AETHER_HERMES_PYTHON=<provisioned runtime> … run_tests.py -- -q --tb=short tests/test_telegram_monitor_cli_plugin.py::test_d15r_fixture_and_environment_gaps_chain_end_to_end` | `1 failed` — `QualificationError: the synthetic laboratory scope could not be materialized through the shipped writers`; `detail: {"errors": ["fixture-review-refused"]}` |
| R3 | #438 — manager-only pre-check reads the ambient profile | `HERMES_HOME=<disposable language-configured profile> … run_tests.py -- -q --tb=short tests/test_telegram_monitor_runtime.py::test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator` | `1 failed` — `assert [] == [<expected rendered part>]`; the same file alone with the ambient live profile was `57 passed` |
| R4 | #438 — the ordered pair | `HERMES_HOME=<disposable language-configured profile> … run_tests.py -- -q --tb=short <EXACT> <MANAGER>` | `1 failed, 1 passed` |

### 1.1 Measured manifest gap (R1), with the check's own logic

| Measurement at base `410c172` | Value |
| --- | --- |
| entries in the `cat >"$expected" <<'EOF'` heredoc | **400** |
| `git ls-files \| grep -v '^specs/'` | **402** |
| missing lines | `patches/hermes/HLP-425-review-flow-continuity.patch`, `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` |

Root causes, attributed separately:

- `patches/hermes/HLP-425-review-flow-continuity.patch` is **issue #437's stated defect**: the portable patch entered the repository in `431b19d` and its adoption ledger was updated in `3d8475c`, neither of which added the literal line.
- `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` was added by the contract commit `410c172` itself without its own manifest line (`git log --oneline -1 -- .aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` → `410c172`). It is **base manifest coverage required by AC-10 / same-class blocker per contract in-scope 2** (shared decision 16), *not* part of #437.

### 1.2 Why R3/R4 reproduce only on some machines (the real defect, measured)

`configured_owner_language()` (`src/aether_agents/monitor/runtime.py:866`) resolves the installation's narration language through `hermes_cli.config.load_config_readonly()` whenever that native module is importable in the process, and that loader resolves `HERMES_HOME` from the ambient environment. The manager-only Monitor module calls `run_precheck` without pinning any native configuration, so:

- when `hermes_cli` is importable (the canonical runner puts the exact checkout first on `PYTHONPATH`; the exact-Hermes lane also imports it as a side effect) and the ambient `HERMES_HOME` configures a language, the retry path re-renders an already enqueued outbox part under that language (`_retry_pending_deliveries`, `runtime.py:1123`);
- immutable outbox identity then refuses the dispatch, and the case fails with `assert [] == [<expected rendered part>]`;
- when `hermes_cli` is not importable, or the ambient profile configures no language, the same case passes — which is why the failure looked order- and machine-dependent rather than deterministic.

Reproduction therefore uses a **disposable** profile that configures a language, never the operator's live one:

```bash
mkdir -p /tmp/lcblock/ambient-profile
cat > /tmp/lcblock/ambient-profile/config.yaml <<'YAML'
plugins:
  enabled:
    - aether-telegram-monitor
  entries:
    aether-telegram-monitor:
      settings:
        language: Spanish
YAML
```

### 1.3 Second #438 defect found by direct measurement: the exact-precheck second invocation

`test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter` ended with `assert scheduler._parse_wake_gate(output) is True` for a *second* execution of the packaged script against the same store and cut, "whatever the child runtime can resolve". That assertion is environment-dependent, because the native scheduler builds its child environment through `tools.environments.local.build_subprocess_env()`, which strips the exact Hermes checkout root from `PYTHONPATH`:

- child cannot resolve the packaged runtime (this repository's canonical runner) → `{"reason": "runtime-mismatch", "wakeAgent": true}` → the old assertion happened to pass;
- child resolves the runtime (the production-relevant layout) → `{"reason": "narration-in-progress", "wakeAgent": false}`. Measured directly with two explicit packaged-script children against one disposable store: child #1 `pending-report` / `wakeAgent: true`; child #2 `narration-in-progress` / `wakeAgent: false` with the handoff child #1 wrote still live.

The second gate is the designed D9/AC-6 fence (`_fence_handoff`, `runtime.py:775`), not an idle no-op — but the old assertion could only hold in one of the two layouts.

---

## 2. Changes (smallest change that removes the real defect)

| File | Change |
| --- | --- |
| `.github/workflows/policy.yml` | Three literal heredoc lines, each indented like its neighbours: `patches/hermes/HLP-425-review-flow-continuity.patch` (#437 part 1), `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` (base coverage, shared decision 16) and `tests/test_telegram_monitor_ambient_isolation.py` (the module this unit adds). No other entry was reordered, reformatted or removed, and the comparison logic is untouched. |
| `scripts/qualify_telegram_monitor.py` | New constant `SYNTHETIC_REVIEW_REVIEWER = "supervisor"`; the synthetic scope manifest gives its pending-review case that explicit `reviewer`; `_LAB_FIXTURE_PROBE` now passes `reviewer=<manifest reviewer>` to the shipped `kanban_db.request_review` and refuses with the bounded `fixture-review-reviewer-missing` code when the manifest carries none. The HLP-425 review-independence rule itself is untouched and is now what the fixture exercises. |
| `tests/test_telegram_monitor_runtime.py` | New autouse `_native_configuration` fixture: pins `HERMES_HOME` to a disposable home whose `config.yaml` declares no plugin entry (so `configured_owner_language()` resolves `None`) and clears `AETHER_MONITOR_LANGUAGE` for every regression in the manager-only module. No test body, oracle or skip changed. |
| `tests/test_telegram_monitor_cli_plugin.py` | The exact-precheck regression now pins both real outcomes of the native scheduler's own execution instead of asserting the one its layout happens to produce: a runtime-resolving child must emit the handoff fence bound to `report-alpha` (`_parse_wake_gate` `False`); a runtime-refusing child must emit `runtime-mismatch` with `wakeAgent: True`. The dead-owner/lease/handoff and single-delivery checks around it are unchanged. |
| `tests/test_telegram_monitor_ambient_isolation.py` | New focused regression (the one module this unit owns): runs the ordered pair, and the manager-only case alone, as real child pytest processes whose ambient `HERMES_HOME` is a disposable language-configured profile, so #438's acceptance is executable rather than argued. |
| `specs/001-aether-v1-productization/evidence/LC-BLOCK.md` | This record. |

Judgement calls and why they preserve the contract:

- **Where the #438 fix belongs.** The diagnosed defect is in the test lane, not in the product: reading the installation's configured narration language through `hermes_cli.config` is the shipped behaviour the D9 narration/renderer agreement requires, and it has its own release-locked regression (`test_configured_owner_language_prefers_plugin_settings`). `src/aether_agents/**` therefore stays untouched, as the card requires.
- **Pinning in the manager-only module, not in `scripts/run_tests.py`.** Scrubbing `HERMES_HOME` in the bootstrap would hide the same dependency for every other module instead of making this module's cases explicit about the configuration they read; the card's writable surface also excludes the bootstrap. Only the module whose regressions were measured failing was pinned.
- **Pin scope.** Only the language source (`hermes_cli.config` through `HERMES_HOME`) and its environment fallback are pinned. `HERMES_TIMEZONE`, the store clock and every other input stay exactly as the regressions set them, so no oracle was narrowed.
- **Both manifest lines, both attributed.** The contract-file line is recorded as base coverage required by AC-10 (shared decision 16), never as part of #437.
- **The fixture fix does not add a writer requirement.** `WRITER_REQUIREMENTS` in `scripts/telegram_monitor_lab.py` still lists only what it listed before; a runtime whose `request_review` lacks `reviewer` is still refused fail-closed (now with the bounded `fixture-review-reviewer-missing`/`fixture-tasks` codes instead of a silent pass).

---

## 3. GREEN verification (raw results, canonical bootstrap)

Provisioned runtime interpreter for the exact-runtime Monitor cases: `AETHER_HERMES_PYTHON=<XDG data root>/aether/runtime/current/venv/bin/python3` (resolved through `aether_agents.monitor.commands.runtime_interpreter()`; private operational context, not recorded here).

| Check | Command | Result |
| --- | --- | --- |
| Manifest node (#437 part 1) | `… run_tests.py -- -q --tb=short tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | **1 passed** |
| Manifest file | `… run_tests.py -- -q --tb=short tests/test_public_artifacts.py` | **8 passed** in 6.36s |
| Manifest equality, workflow logic | heredoc list vs `git ls-files \| grep -v '^specs/' \| sort` | empty diff; **402 == 402** |
| D15R fixture node (#437 part 2) | `… run_tests.py -- -q --tb=short tests/test_telegram_monitor_cli_plugin.py::test_d15r_fixture_and_environment_gaps_chain_end_to_end` | **1 passed** in 3.18s |
| D15R fixture, direct measurement | `/tmp` probe calling `_lab_fixture` on the real provisioned runtime | RED errors gone; `boards: 2`, `tasks: 8`, `direct: 2` |
| Exact-precheck regression | `… run_tests.py -- -q --tb=short tests/test_telegram_monitor_cli_plugin.py::test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter` | **1 passed** in 5.51s |
| Manager-only module, ambient live profile | `… run_tests.py -- -q --tb=line tests/test_telegram_monitor_runtime.py` | **57 passed** in 3.83s |
| Manager-only module, language-configured disposable ambient profile (R3) | `HERMES_HOME=/tmp/lcblock/ambient-profile … run_tests.py -- -q --tb=line tests/test_telegram_monitor_runtime.py` | **57 passed** in 6.65s |
| Ordered pair, language-configured ambient profile (R4) | `HERMES_HOME=/tmp/lcblock/ambient-profile … run_tests.py -- -q --tb=short <EXACT> <MANAGER>` | **2 passed** in 2.56s |
| Reversed pair (reordered) | `… run_tests.py -- -q --tb=short <MANAGER> <EXACT>` | **2 passed** in 1.78s |
| Exact-Hermes CLI/plugin module | `… run_tests.py -- -q --tb=line tests/test_telegram_monitor_cli_plugin.py` | **132 passed** in 136.23s |
| New ambient-isolation regression | `… run_tests.py -- -q --tb=short tests/test_telegram_monitor_ambient_isolation.py` | **2 passed** in 1.58s (child processes reported `2 passed` and `1 passed`) |
| Reordered monitor set (alphabetical) | `… run_tests.py -- -q --tb=line <AMBIENT_ISOLATION> <CLI_PLUGIN> <DELIVERY> <REPORTING> <RUNTIME> <SOURCES> <STATE>` | see §3.1 |
| Full canonical suite | `… run_tests.py` | see §3.2 |
| Mutation check (regression has teeth) | see §3.3 | see §3.3 |
| Format/lint | `uv run --frozen ruff check` / `ruff format --check` on every touched Python path | `All checks passed!` / `already formatted` |
| Whitespace | `git diff --check` | clean (exit 0) |
| Workflow file | `python -c "yaml.safe_load(...)"` + heredoc extraction | `policy.yml` parses; heredoc equals the tracked set |

No skip was added or removed to obtain green; the two new `hermes_exact` cases run under the canonical bootstrap and skip only when the release-locked checkout is genuinely unavailable, exactly like the pre-existing exact-Hermes lane.

### 3.1 Reordered/alphabetical monitor set

Two runs of the seven-module set above, ambient live profile, machine load average **31–35** with another unit's fork test suite running concurrently:

| Run | Result |
| --- | --- |
| 1 | `1 failed, 354 passed` in 176.21s — `tests/test_telegram_monitor_state.py::test_collection_lease_fences_duplicate_workers` (`UnsafeObservationPath: private file has multiple hard links`) |
| 2 | `1 failed, 354 passed` in 174.80s — `tests/test_telegram_monitor_cli_plugin.py::test_d16t_lab_scheduler_stop_fails_closed_when_child_ignores_stop_and_sigterm` (`DID NOT RAISE QualificationError`) |

Attribution of both, by measurement rather than assertion:

- neither node touches any path this unit changed (`git diff --name-only 410c172` = the five paths in §2);
- `test_collection_lease_fences_duplicate_workers`: **3/3 passed** alone and its whole module **5 × `20 passed`** alone, under the same load;
- `test_d16t_lab_scheduler_stop_fails_closed_when_child_ignores_stop_and_sigterm`: **6/8 passed** alone (load ≈35), and with the **base content** of its file restored the same node was **2/6 passed** — a pre-existing child-startup-vs-`LAB_SCHEDULER_STOP_SECONDS` race, not order- or diff-dependent;
- both nodes passed in the full canonical suite of §3.2, and a different node flaked in each reordered run, which is the signature of load-induced timing, not of a deterministic order dependency.

### 3.2 Full canonical suite

`uv run --frozen python scripts/run_tests.py -- -q --tb=line` → **2 failed, 1694 passed, 65 skipped, 587 subtests passed** in 714.95s (11:54), load average 13 → 23 with the concurrent fork suite.

Both failures are the same file: `tests/test_observation_performance.py` timing budgets (`10k reduction took 2.042s` against a 2.0s budget; p95 `10.530652 <= 5.0`). Attribution:

- the file is **byte-identical to base** — it is not in this unit's diff;
- the coverage gate excludes exactly this file (`policy.yml:642`: `coverage run -m pytest -q --ignore=tests/test_observation_performance.py`), so it is not a gate this objective runs;
- re-measured alone on the same machine under load ≈35: 5/5 runs failed 1–2 of its 3 budget assertions; on a quiet moment earlier the same file was `3 passed in 3.67s`. The residual is the machine's load, not this unit.

### 3.3 The new regression module has teeth (mutation check)

With the `_native_configuration` pin body temporarily replaced by `return None`:

```
FAILED tests/test_telegram_monitor_ambient_isolation.py::test_the_ordered_pair_is_independent_of_the_ambient_profile
FAILED tests/test_telegram_monitor_ambient_isolation.py::test_the_manager_only_case_is_independent_of_the_ambient_profile
2 failed in 7.90s
```

with each child reporting `1 failed in 0.75s` (the exact #438 signature). The file was then restored byte-identically (`diff -q` clean, `git diff --stat` = 25 insertions) and the module is `2 passed` again. So the regression fails without the fix and passes with it — not a decorative test.

---

## 4. Requirement coverage

| Assigned obligation | Check actually run | Observed result |
| --- | --- | --- |
| #437 part 1 — the tracked patch appears in the literal non-`specs/` manifest | manifest node + workflow-equality logic | RED `1 failed` → GREEN `1 passed`; 402 == 402, empty diff |
| Shared decision 16 — base contract file covered by the same manifest gate | same node + measured counts | RED `400 vs 402, two missing` → GREEN `402 == 402` |
| #437 part 2 — D15R fixture names an explicit distinct reviewer | D15R node on the provisioned runtime | RED `fixture-review-refused` → GREEN `1 passed`; boards 2 / tasks 8 / direct 2 |
| #437 part 2 — the review-independence rule is not weakened | source inspection of the fixture call and of the shipped `request_review`; the new bounded failure code | the shipped writer still owns the rule (explicit reviewer, self-review rejected); the fixture passes `reviewer=supervisor` and refuses (`fixture-review-reviewer-missing`) rather than inventing one |
| #438 — a prior native import must not let a manager-only case read the ambient profile | ordered pair and manager-only case under a language-configured disposable ambient profile; new isolation module | RED `1 failed, 1 passed` / `1 failed` → GREEN `2 passed` / `57 passed` |
| #438 — suite result independent of ambient operator profile configuration | the module and the pair under two different ambient profiles (live, language-configured disposable) | `57 passed` and `57 passed`; the isolation module re-runs both cases with a configured ambient home and fails without the pin (§3.3) |
| #438 — exact-precheck second invocation deterministic without weakening the lease checks | direct measurement of both layouts + the pinned assertion | both real gates asserted exactly; handoff/reporter/single-delivery checks unchanged |
| Card verification — touched nodes, lint, whitespace, no new skip | §3 rows | all listed checks green; `git diff` adds no skip |

## 5. Preserved

Every other manifest entry (the 400 pre-existing lines are unchanged byte for byte); the manifest comparison logic; the review-independence contract; `src/aether_agents/**` (zero product changes); `WRITER_REQUIREMENTS`; other units' files; the breakdown `tasks.md`; the canonical Objective Contract; `home/`; the operator's primary checkout, live runtime, XDG state, services, boards and credentials.

## 6. Remaining risk / notes for review

1. The exact-precheck regression pins two mutually exclusive real layouts; in any single run only one branch executes and the other is asserted by construction. The fence branch is deterministically covered by `tests/test_telegram_monitor_runtime.py::test_two_real_precheck_children_wake_exactly_one_narration`.
2. `configured_timezone_name()` reads ambient `HERMES_TIMEZONE`/`hermes_time` the same way `configured_owner_language()` reads `hermes_cli.config`. No measured failure involves it, and pinning it would change the store/cut clocks of existing regressions, so it was deliberately left as-is; if the canonical suite is ever reported order-dependent through the clock, the same pin extends to it.
3. `WRITER_REQUIREMENTS` still omits `reviewer`, so a runtime whose `request_review` lacks that keyword refuses later (`fixture-tasks` / `fixture-review-reviewer-missing`) instead of in the pre-write writer probe. Changing the required-writer surface is a capability statement about supported runtimes, so it was left to the owning card rather than widened here.
4. The new isolation module skips when the release-locked checkout is unavailable. CI's coverage step provides the checkout on `PYTHONPATH` but does not export `AETHER_EXACT_HERMES_CHECKOUT`, so that lane is exercised by the canonical bootstrap locally, as this card's verification requires; LC-INT may add the env var to that step if it wants CI coverage too.
5. Machine-load residuals were observed in `tests/test_observation_performance.py` and in one D16T stop/SIGTERM node (§3.1, §3.2). They are pre-existing and independent of this diff, but they will make any load-sensitive release gate noisy: LC-INT should run the integrated gates on a quiet machine (the fork suite ran concurrently here).

## 7. Environment limits

- Evidence produced on the disposable worktree `…/.worktrees/t_8a02a727` at base `410c172`; no live service, profile, board or runtime was touched.
- The exact-runtime Monitor cases need the provisioned interpreter (`AETHER_HERMES_PYTHON`); without it they skip, as at base.
- The machine was under load average 13–35 for most runs (another unit's fork test suite ran concurrently); counts are raw and attributed above, not smoothed.
- The "previously failing" order was reproduced with a disposable language-configured ambient profile, because the operator's live profile is not read (and must not be).

## 8. Candidate and closeout

- Branch: `aether-agents-2/t_8a02a727-lc-block-close-release-blockers-437-and` (local commits only).
- Code candidate: `8.1` below; this evidence record is committed in the same change set.
- No push, PR, merge, tag, release, issue mutation, activation or residue cleanup: those belong to LC-INT/LC-CLOSE.

### 8.1 Candidate revision

_(recorded after the commit; the branch tip is the record plus the code it describes)_
