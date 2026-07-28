# v0.20.0 — External Correction Report (Phase 1)

> **Status:** `CORRECTION CANDIDATE VERIFIED` — not accepted. Prepared for a second, independent external audit.
> **Scope:** Phase 1 only, as defined in `EXTERNAL_LOGIC_AUDIT.md` §15 — *make the instrumentation truthful*. No new capability.
> **Branch:** `feature/v0.20.0-self-improvement-bootstrap`
> **Baseline:** `48635b41e8d20caf68742b066e9153b42ac2d883`
> **Worktree:** `/home/arty/Escritorio/agentes/aether-v020-isolated`
> **Date:** 2026-07-28
>
> **Independent review addendum:** The candidate at `89cba0e` was initially blocked because F-06 still accepted cross-project `project_root` redirection and F-03 still collapsed identical calls across model requests inside one turn. Both residual gaps were corrected in `b2cabfa` and accepted in `INDEPENDENT_PHASE1_REVIEW.md`. The finding dispositions below describe the original correction author's state before that independent amendment.

---

## 1. What this is, and what it is not

The external logic audit returned `TELEMETRY BOOTSTRAP, NOT YET SELF-IMPROVEMENT`. This correction does **not** change that verdict, and is not intended to. It closes the defects that made the instrumentation report things that were not true; it does not add an evaluator, candidate isolation, before/after comparison or rollback.

**v0.20.0 remains an instrumentation bootstrap. It is not causal self-improvement.** Phases 2 and 3 of the audit's remediation plan are deliberately unimplemented. §11 lists exactly what is still not claimable.

The self-referential risk in this work is obvious and was treated as the primary constraint: the audit's central finding (F-05) was that an implementation and the tests judging it had been changed together, leaving a green suite in a tree that failed two of its own safety properties. The rule adopted here was therefore **the 26 pre-existing test cases are not modified**. All new coverage lives in a separate file, and every correction had to satisfy the original contract as well as the new one. One intended fix was abandoned rather than break that rule (§8).

---

## 2. Baseline

| | |
|---|---|
| Branch | `feature/v0.20.0-self-improvement-bootstrap` |
| Baseline commit | `48635b41e8d20caf68742b066e9153b42ac2d883` |
| Baseline worktree state | clean (`git status --porcelain` → 0 entries) |
| Baseline test counts | 26 bootstrap · 943 coordination · 1163 full suite |
| Governing audit | `docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md` |

The audit was performed against the **main** worktree (`/home/arty/Escritorio/agentes/aether` @ `a88b5cc`), which carries an older, uncommitted copy of the same feature. That copy is stale and non-authoritative — see §12. This branch is the authoritative candidate and is the only tree corrected here.

---

## 3. Commits created

| # | Hash | Subject | Findings |
|---|---|---|---|
| 1 | `7d8cb32` | `fix(self-improvement): classify outcomes against real contracts` | F-01, F-02 |
| 2 | `49128dd` | `fix(self-improvement): scope ledger identity and version its schema` | F-03, F-15, F-16 |
| 3 | `c03e771` | `fix(self-improvement): preserve lifecycle and baseline integrity` | F-07, F-11, F-12, F-13, F-14, F-19 |
| 4 | `6bb541b` | `fix(self-improvement): surface measurement integrity in evidence` | F-24 |
| 5 | `ac2f263` | `docs(self-improvement): state instrumentation limits honestly` | F-08, F-09, F-17, F-20, F-21 |
| 6 | *(this report)* | `docs(self-improvement): add external correction report` | — |

Each of commits 1–4 carries its implementation and the tests that validate it. No commit contains tests decoupled from the behaviour they exercise. Commits 5 and 6 are documentation only.

**Boundary deviation from the requested split.** The requested plan grouped F-03/F-15/F-16 as "ledger" and F-13/F-14/F-19 as "lifecycle". The `_SCHEMA` block in `ledger.py` is a single durable schema version: the `uncertainty` column, the scoped primary keys, the `turn_outcomes` table and the `baseline_dirty_digest` / `manifest_drifted` columns cannot be introduced across three commits without either three schema versions or a broken intermediate state. Commit 2 therefore carries the whole schema, and commit 3 carries the *behaviour* that populates the lifecycle columns. This is the "code demands another separation" case the instructions permit.

---

## 4. Finding-by-finding disposition

Statuses: **FIXED** · **PARTIALLY FIXED** · **DEFERRED** · **REJECTED** · **OUT OF SCOPE**.

| ID | Sev | Status | Evidence |
|---|:--:|---|---|
| **F-01** Harmonia classifier reads fields the kernel never emits | P0 | **FIXED** | `hooks.py` `_harmonia_classification` now reads `error.code` / `state` / `uncertainty`; imports `HARMONIA_ERROR_CODES`. Tests: `test_every_public_error_code_is_classified`, `test_every_durable_state_is_classified_post_admission`, `test_pre_admission_codes_are_the_only_ones_treated_as_effect_free`, `test_post_admission_state_set_tracks_the_kernel`, `test_uncertain_durable_effect_is_preserved`. Commit `7d8cb32`. |
| **F-02** failing payload recorded as success | P0 | **FIXED** | `_tool_outcome(result, host_status)` prefers Hermes' own `status`; local parser rejects `ok:false`, `success:false` and failure `status` strings. Tests: `test_failure_payloads_are_never_success` (5 cases), `test_host_status_wins_over_local_parsing`. Commit `7d8cb32`. |
| **F-03** global `tool_call_id` primary key | P0 | **FIXED** | Identity is `(session_id, turn_id, tool_call_id)` and `(session_id, turn_id, event_id)`. Tests: `test_identical_tool_call_ids_in_two_sessions_are_both_recorded`, `test_the_same_command_repeated_in_a_later_turn_is_counted_again`. Commit `49128dd`. |
| **F-04** no causal machinery: no evaluator, isolation, comparison or rollback | P0 | **OUT OF SCOPE** | Phase 2/3 by design. Not implemented. Now stated as unimplemented in `CYCLE.yaml` (`implementation_scope.deferred`, `gate_status.causal_before_after_acceptance: not_implemented_no_evaluator_or_comparison`), `AGENTS.md`, `IMPLEMENTATION_REPORT.md` and the generated evidence itself. |
| **F-05** implementation + tests + acceptance counts changed together | P0 | **PARTIALLY FIXED** | This branch is designated the single authoritative candidate; the 26 original cases were preserved byte-for-byte and new coverage added in a separate file. The stale copy in the main worktree is **recorded, not removed**, per instruction (§12). The structural fix — an evaluator the candidate cannot edit — is Phase 2. |
| **F-06** `AETHER_PROJECT_ROOT` / nested-repo isolation bypass | P1 | **FIXED (at baseline; preserved)** | Already corrected in `48635b4`. Verified not reintroduced: `grep AETHER_PROJECT_ROOT hooks.py` → absent; `_walk_to_project` still stops at the nearest `.git`; the three baseline isolation tests still pass unmodified. |
| **F-07** `candidate_version` not pinned to its directory | P1 | **FIXED** | `manifest.py` `_CANDIDATE_VERSION` derived from `_MANIFEST.parent.name`. Test: `test_candidate_version_must_match_its_release_directory`. Commit `c03e771`. |
| **F-08** authorizing a gate silently deletes the cycle | P1 | **PARTIALLY FIXED — remainder is a deferred product-owner decision** | See §8. Silence fixed (WARNING logged); interlock semantics unchanged by owner decision. Test: `test_identity_failure_with_a_manifest_present_is_reported`. Commit `c03e771` (log) + `ac2f263` (record). |
| **F-09** router telemetry structurally unreachable | P1 | **PARTIALLY FIXED** | The false claim is retired: `CYCLE.yaml` `provider.record_when_reported` now lists only `requested_model`, with the rest under `not_supplied_by_the_host_runtime`; `gate_status.router_telemetry_recorded: not_reachable_without_upstream_hook_change`. The capability itself requires a change to Hermes Agent's `post_llm_call` payload and is **not** attempted here. |
| **F-10** `post_llm_call` skips failed and interrupted turns | P1 | **DEFERRED** | Not fixed. Recording turn cost from `on_session_end` was not attempted because, with F-09 unresolved, there is no telemetry to record — the survivorship bias applies to a set of fields that are uniformly NULL. Should be fixed together with F-09. |
| **F-11** continued sessions produce no evidence | P1 | **FIXED** | Lazy initialization added to `post_tool_call` and `post_llm_call`. Tests: `test_session_evidence_survives_a_continuation`, `test_post_llm_call_tolerates_the_exact_kwargs_hermes_sends`. Commit `c03e771`. |
| **F-12** `_git_head` returns `unknown` for linked worktrees | P1 | **FIXED** | Loose refs resolved in both the private gitdir and the common dir. Test: `test_git_head_resolves_a_linked_worktree` (creates a real worktree). Commit `c03e771`. |
| **F-13** baseline records HEAD but not the dirty set | P1 | **FIXED** | `_baseline_dirty_digest` + `cycle_sessions.baseline_dirty_digest`. Test: `test_baseline_records_whether_the_worktree_was_clean`. Commits `49128dd` (column) + `c03e771` (behaviour). |
| **F-14** one interrupted turn latches the session forever | P1 | **FIXED** | `turn_outcomes` table; session status derived from the latest turn. Test: `test_interrupted_turn_does_not_permanently_poison_the_session`. Commits `49128dd` + `c03e771`. |
| **F-15** reused `session_id` merges evidence silently | P1 | **FIXED** | `start_session` compares digest and baseline on collision and raises. Test: `test_reused_session_id_under_a_different_manifest_is_refused`. Commit `49128dd`. |
| **F-16** no ledger schema migration | P1 | **FIXED** | `SCHEMA_VERSION = 2` via `PRAGMA user_version`; incompatible file refused with a recovery instruction. Test: `test_incompatible_ledger_schema_fails_loudly`. Commit `49128dd`. |
| **F-17** template leaves no coordination path | P1 | **PARTIALLY FIXED** | The documentation mismatch is fixed: `AGENTS.md` no longer claims every session participates, states that the plugin must be enabled explicitly, and states that the template has no general delegation path; `gate_status.automatic_participation_on_install: not_implemented`. The operational gap is **retained by explicit owner decision** — `talk_to` was removed deliberately and is not restored. |
| **F-18** no rollback mechanism | P1 | **OUT OF SCOPE** | Phase 3. Not implemented. |
| **F-19** manifest digested once, never re-verified | P2 | **FIXED** | Re-verified at `on_session_finalize`; `cycle_sessions.manifest_drifted` recorded and surfaced in the evidence. Test: `test_manifest_change_during_a_session_is_marked`. Commits `49128dd` + `c03e771`. |
| **F-20** documentation asserts unimplemented behaviour | P2 | **FIXED** | All eight rows corrected. See §6. Commit `ac2f263`. |
| **F-21** stale benchmark manifest digest | P2 | **FIXED** | Regenerated to `sha256:f31a60f2…` and now regenerated whenever the report changes. Commit `ac2f263`. |
| **F-22** `.aether/` directory is `0755` | P2 | **DEFERRED** | Not fixed. Database and its WAL/SHM sidecars are `0600`, so contents are protected and only the directory listing is world-readable. Left for a later pass to keep this one scoped to correctness of reported facts. |
| **F-23** order-dependent coordination test | P2 | **OUT OF SCOPE** | Pre-existing, outside `self_improvement`. Not reproduced in any run during this correction (9 consecutive full-suite runs green). Should be tracked separately. |
| **F-24** evidence proves activity volume, not quality | P2 | **PARTIALLY FIXED** | The projection now reports baseline cleanliness, manifest drift and uncertain durable effects, and states in its own text that it records no task, threshold, baseline or comparison and therefore supports no causal claim. The underlying gap is F-04 and remains open. Test: `test_release_evidence_declares_its_own_limits`. Commit `6bb541b`. |
| F-25 PID reuse defers reconciliation | P3 | **REJECTED** | Correctly identified in the audit as *not a defect*. The behaviour is conservative: a reused PID delays reconciliation and cannot fabricate a success. Unchanged. |
| F-26 `ensure_schema()` on every operation | P3 | **DEFERRED** | Not fixed. Cosmetic/performance only; no correctness impact. |

**Totals:** 14 FIXED · 5 PARTIALLY FIXED · 3 DEFERRED · 3 OUT OF SCOPE · 1 REJECTED.

---

## 5. Defects reproduced before, behaviour after

Each row was reproduced against `48635b4` during the audit and is now pinned by a test.

| Finding | Before (reproduced) | After |
|---|---|---|
| F-01 | real success envelope → `('unknown','unknown')`; `admission_limit` → phase `unknown` | all 13 error codes and all 9 kernel states classified; `uncertainty` preserved |
| F-02 | `{"success": false}`, `{"ok": false}`, `{"status": "failed"}` → `'success'` | all → `'error'`; host verdict preferred |
| F-03 | two sessions emitting `call_1` → 1 row; `evidence_counts.tool_calls == 1` | 2 rows; count == 2; a repeated command in a later turn counted twice |
| F-07 | `candidate_version: 9.9.9` inside `docs/releases/v0.20.0/` accepted | `ManifestError` |
| F-08 | authorizing a gate → `verify_project_identity` returns `None`, no log, cycle vanishes | still refuses (by design), now logs a WARNING naming the root |
| F-11 | session whose first hook is `post_tool_call` → no record at all | record created, tool call stored |
| F-12 | `_git_head(linked worktree)` → `"unknown"` | equals `git rev-parse HEAD` |
| F-13 | only HEAD recorded; dirty tree 1170 vs clean 1163 indistinguishable | `clean` or `dirty:<n>:sha256:<digest>` recorded and surfaced |
| F-14 | ok → Ctrl-C → ok → ok left status `reconciliation_required` permanently | recovers to `active`, finalizes, interruption retained in `turn_outcomes` |
| F-15 | second `start_session` under a different digest silently kept the old row | `LedgerSchemaError` |
| F-16 | pre-existing v0 schema → 0 rows, warning only, session looks healthy | `LedgerSchemaError` with recovery instruction |
| F-19 | manifest edited mid-session → evidence accrues under stale digest, unnoticed | `manifest_drifted = 1`, WARNING logged, surfaced in evidence |
| F-24 | evidence = counts only | counts plus integrity, plus an explicit statement of what it cannot establish |

---

## 6. Documentation corrections (F-20)

| Claim | Location | Correction |
|---|---|---|
| "Every Hermes session … participates" | `AGENTS.md` | Replaced: participation requires explicit `plugins.enabled`; no installation participates automatically. |
| "injects an identity warning" | `SELF_IMPROVEMENT_CYCLE.md` | Corrected: nothing is injected into the model turn; the operator is logged instead. |
| 11-state session machine | `SELF_IMPROVEMENT_CYCLE.md` | Marked as operating model; three states are persisted. |
| safe takeover / repair verification / Harmonia retry listed as implemented | `CYCLE.yaml` | Moved to `implementation_scope.deferred` with the reason. |
| `harmonia_outcome_classification: pass_deterministic_tests` | `CYCLE.yaml` | Now `pass_against_real_wire_contract`; the prior pass rested on a fabricated payload. |
| provider telemetry contract (8 fields) | `CYCLE.yaml` | Only `requested_model` is reachable; the rest listed under `not_supplied_by_the_host_runtime`. |
| "Full repository suite: 1163/1170 passed" | `IMPLEMENTATION_REPORT.md`, `BENCHMARK_REPORT.md` | Regenerated from the clean checkout: 1187. |
| stale manifest digest | `BENCHMARK_REPORT.md` | Regenerated; policy stated. |
| candidate name "Self-Improvement Cycle Bootstrap" | `CYCLE.yaml` + reports | Renamed **Self-Improvement Instrumentation**. |

`SECURITY_REVIEW.md` was **not** modified: its content describes the security review performed at baseline and remains accurate for that scope.

---

## 7. Tests

### Added — `tests/test_self_improvement_contract.py`, 20 functions / 24 cases

`test_post_admission_state_set_tracks_the_kernel`, `test_every_public_error_code_is_classified`, `test_pre_admission_codes_are_the_only_ones_treated_as_effect_free`, `test_every_durable_state_is_classified_post_admission`, `test_uncertain_durable_effect_is_preserved`, `test_failure_payloads_are_never_success` (5 parametrised), `test_host_status_wins_over_local_parsing`, `test_identical_tool_call_ids_in_two_sessions_are_both_recorded`, `test_the_same_command_repeated_in_a_later_turn_is_counted_again`, `test_reused_session_id_under_a_different_manifest_is_refused`, `test_incompatible_ledger_schema_fails_loudly`, `test_session_evidence_survives_a_continuation`, `test_post_llm_call_tolerates_the_exact_kwargs_hermes_sends`, `test_git_head_resolves_a_linked_worktree`, `test_baseline_records_whether_the_worktree_was_clean`, `test_interrupted_turn_does_not_permanently_poison_the_session`, `test_candidate_version_must_match_its_release_directory`, `test_manifest_change_during_a_session_is_marked`, `test_identity_failure_with_a_manifest_present_is_reported`, `test_release_evidence_declares_its_own_limits`.

Two are **drift detectors** rather than behaviour tests, and are the load-bearing ones: `test_post_admission_state_set_tracks_the_kernel` asserts the plugin's state set equals `harmonia_service._STATES`, and `test_every_public_error_code_is_classified` iterates `HARMONIA_ERROR_CODES` and builds envelopes with the kernel's own `public_error`. A rename upstream now breaks the build instead of silently degrading every classification to `unknown` — which is exactly how F-01 survived undetected.

### Preserved — `tests/test_self_improvement.py`, 26 cases, unmodified

Verified byte-identical to `48635b4`:

```
$ git diff 48635b4 -- tests/test_self_improvement.py
(no output)
```

This includes the three isolation regressions that F-05 concerned (`test_environment_cannot_redirect_a_foreign_workspace_into_aether`, `test_nested_foreign_repository_cannot_inherit_parent_aether_identity`, `test_aether_subdirectory_resolves_the_nearest_repository_root`), which still pass.

---

## 8. Reverted decision — F-08, and why

An `authorization` redesign was implemented and then **reverted before any commit**. The intent was to let a granted gate be recorded as open rather than invalidate the manifest, so that the contract could describe its own successor state.

It was reverted because it would have required rewriting `test_rejects_contract_that_authorizes_activation_or_release` — an existing acceptance test asserting the opposite. Changing an implementation and the test that judges it in the same change is the precise failure F-05 describes. Under the rule adopted for this work, that made the change inadmissible regardless of its merit.

The product owner has since confirmed the disposition:

- the default-off interlock is **kept as designed**;
- `authorization` semantics are **not changed yet**;
- the WARNING when a `CYCLE.yaml` exists but fails validation is **kept**;
- **F-08 is recorded as a deferred product-owner decision, not a closed finding.**

What remains open: while the candidate is default-off, the manifest cannot represent a granted gate. An owner who authorizes one must understand that the cycle stops loading — now visibly, via the log, rather than silently. Deciding what an authorized gate should *do* is a product decision and is not made here.

---

## 9. Verification

All checks executed in a **temporary, clean worktree detached at the exact commit**, with `PYTHONPATH` pointing at that worktree's `src` — not the editable tree, and not the main worktree.

```
$ git worktree add --detach <tmp> <final>
$ cd <tmp> && git status --porcelain | wc -l
0

$ PYTHONPATH=<tmp>/src python -m pytest tests/test_self_improvement.py -q
26 passed

$ PYTHONPATH=<tmp>/src python -m pytest tests/test_self_improvement_contract.py -q
24 passed

$ PYTHONPATH=<tmp>/src python -m pytest tests/coordination/ -q
943 passed

$ PYTHONPATH=<tmp>/src python -m pytest tests/ -q
1187 passed

$ python -m ruff check src/ tests/
All checks passed!

$ python -m compileall -q src tests
OK

$ PYTHONPATH=<tmp>/src python -c "verify_project_identity(Path('.'))"
loads: True | version: 0.20.0 | name: Self-Improvement Instrumentation
digest: sha256:f31a60f234ed127d27759c56f2a9769233654b920d5ed0996ef8d2f177ff1f8d

$ git diff --check 48635b4
(no output — no whitespace errors)

$ git diff --name-status 48635b4 | grep -v '^M'
A	docs/releases/v0.20.0/EXTERNAL_CORRECTION_REPORT.md
A	docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md
A	tests/test_self_improvement_contract.py
```

**Lint scope.** `ruff check src/ tests/` is clean. `ruff check .` reports 155 errors, all outside the change: 132 in `home/skills/`, 20 at repository root, 12 in `home/profiles/`, 9 in `scripts/`, 2 in `evaluations/`. Zero are in `src/` or `tests/`. The repository's own CI lints `ruff check src/` (`.github/workflows/test.yml:32`), so these are pre-existing and out of scope.

**Documentation links.** One dangling reference was found by the clean-worktree check and fixed: commits 1–5 cite `docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md`, which existed only in the main worktree. The audit is now committed to this branch so the candidate is self-contained for the next reviewer. It is a verbatim copy and describes the main worktree as it stood at `a88b5cc`; nothing in it was edited.

**Baseline comparison.** Baseline 1163 → candidate 1187 = +24, matching exactly the 24 new cases. No pre-existing test was removed, skipped or altered.

---

## 10. Claims that are now valid

1. The Harmonia admission phase recorded for a coordination event reflects the kernel's real response contract, for every public error code and every durable state.
2. A tool result reporting failure is not recorded as a success.
3. Two sessions running the same command each contribute a distinct measurement, and a command repeated in a later turn is counted twice.
4. A resumed session records evidence.
5. `baseline_commit` is correct in a linked worktree.
6. The evidence states whether each session's baseline worktree was clean.
7. An interrupted turn is preserved in the session's history without permanently blocking it.
8. A reused session identifier cannot silently merge evidence across manifests or baselines.
9. An incompatible ledger cannot silently produce a session with zero evidence.
10. A manifest changed mid-session is detected and recorded.
11. The manifest cannot declare a candidate version other than the one its directory names.
12. `CYCLE.yaml`'s `gate_status` reports a pass only where a test exercises a real payload or a real production call path.
13. The generated release evidence states what it does not establish.
14. The 26-case acceptance contract that existed before this work still passes, unmodified.

## 11. Claims that are still invalid

1. **"Aether improves itself."** No evaluator, candidate isolation, comparison or rollback exists (F-04, F-18).
2. **"The cycle produces a next-version signal from evidence."** The signal remains a constant `REQUIRES_MORE_EVIDENCE`; no production path assigns another value.
3. **"Release evidence demonstrates quality."** It reports activity counts plus integrity flags. It records no task, acceptance threshold, baseline measurement or comparison.
4. **"Router telemetry is recorded."** Only `requested_model` is reachable (F-09).
5. **"Efficiency is measured."** Failed and interrupted turns are still excluded from model-call records (F-10), on top of F-09.
6. **"Every Hermes session participates."** The plugin is enabled nowhere.
7. **"An installation has a coordination path."** By owner decision, the template excludes `talk_to` while Harmonia is default-off (F-17).
8. **"A durable Harmonia admission always leaves a trace."** A crash between admission and `post_tool_call` still leaves none.
9. **"Failure causes are classified."** `framework_defect` / `contract_defect` / `worker_defect` / `configuration_state` exist in documentation only.
10. **"Safe takeover, repair verification and retry are implemented."** They are instructions injected into the first model turn.
11. **"Phase 1 is accepted."** It is a verified correction candidate awaiting independent review.

---

## 12. Warning — the main worktree holds a stale, non-authoritative copy

`/home/arty/Escritorio/agentes/aether` contains an **uncommitted, older and less safe** copy of `src/olympus_v3/self_improvement/` and `tests/test_self_improvement.py`:

- it honours `AETHER_PROJECT_ROOT` and walks past a nearer foreign `.git`, so a foreign session can initialise and mutate the Aether ledger (audit F-06);
- three isolation regressions present here are **absent** there, so its suite reports 23/23 green while failing two safety properties this branch enforces;
- it does not contain any correction in this report.

It was **deliberately left untouched**: that worktree carries concurrent, non-attributable work including Hermes prompt versioning, and the instruction for this task was explicit that nothing in it may be deleted, overwritten, synchronised or modified. It is recorded here as stale and non-authoritative.

**The authoritative candidate is this branch.** Anyone enabling the plugin from the main worktree's `PYTHONPATH` would load the vulnerable copy.

---

## 13. Files changed

Against `48635b4`:

```
 AGENTS.md                                          |   8 +-
 docs/knowledge/SELF_IMPROVEMENT_CYCLE.md           |   9 +-
 docs/releases/v0.20.0/BENCHMARK_REPORT.md          |  30 +-
 docs/releases/v0.20.0/CYCLE.yaml                   |  59 ++-
 docs/releases/v0.20.0/IMPLEMENTATION_REPORT.md     |  32 +-
 docs/releases/v0.20.0/SELF_IMPROVEMENT_EVIDENCE.md |  17 +-
 src/olympus_v3/self_improvement/evidence.py        |  13 +
 src/olympus_v3/self_improvement/hooks.py           | 183 ++++++--
 src/olympus_v3/self_improvement/ledger.py          | 171 ++++++--
 src/olympus_v3/self_improvement/manifest.py        |  41 +-
 tests/test_self_improvement_contract.py            | 481 +++++++++++++++++++++
```

Plus, in the report commit: `docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md` (copied verbatim) and this file.

Not modified: `tests/test_self_improvement.py`, `docs/releases/v0.20.0/SECURITY_REVIEW.md`, `home/config.yaml.template`, `home/plugins/`, `home/SOUL.md`, anything under `src/olympus_v3/coordination/`.

`.aether/self_improvement.db` was created in this worktree when regenerating the release evidence. It is gitignored and is not part of any commit.

---

## 14. Statement of confinement

No file in `/home/arty/Escritorio/agentes/aether` was created, deleted, modified, overwritten or synchronised. The only interaction with that path was reading `docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md` in order to copy it into this branch.

No push, merge, rebase, tag, release, activation, restart, deployment or publication was performed. Phases 2 and 3 were not implemented.

---

## 15. Status

**`CORRECTION CANDIDATE VERIFIED`** — verified against a clean checkout of the final commit, and explicitly **not** declared accepted by the party that produced it. Acceptance requires an independent external audit of this branch.


---

## 16. Independent disposition

The required second review is complete. It initially rejected this candidate's F-03 and F-06 dispositions after reproducing two residual gaps: same-turn calls still collided across model requests, and an explicit `project_root` could still redirect a foreign repository. Commit `b2cabfa` corrects both without modifying the preserved 26-case baseline.

The independent result is recorded in `INDEPENDENT_PHASE1_REVIEW.md` with final verdict:

**`PHASE 1 ACCEPTED — TRUTHFUL INSTRUMENTATION ONLY`**

This acceptance does not change the audit's architectural verdict. v0.20.0 remains default-off instrumentation, not causal self-improvement; Phases 2 and 3 remain unimplemented.
