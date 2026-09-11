# MON-D16U Implementation Evidence — truthful narration oracle and deterministic guard

**Unit:** D16U — make the qualification harness's narration oracle truthful and guard it deterministically
**Task:** `t_16d33dc6`
**Objective Contract:** `oc_f8c9fc9320587cf3@v4`
**Base commit:** `e6bae9959a84993686c18c05e76724c708aa61d5` (`e6bae99`)
**Candidate implementation commit:** `312ef41ca1fdd4d24fba388145fd0d33084235dd` (`312ef41`)
**Phase:** Implementer unit; **no live effect performed**. No `--live` run, model call, Telegram send, real laboratory/production job enablement, scheduler started outside a test, profile/config/credential/provider mutation, retained-laboratory cleanup, push, PR or issue mutation was performed.

## Source findings and measured defect

The defect was measured directly on the retained v7 laboratory (`20260911T192140Z-323d4532323e`, receipt `telegram-monitor-live-v7.json`, sha256 `cfc1f4a7…`, documented in `MON-V4-INT-finding-v7.md` attached to `t_e814cfc3`):

- **Defect:** `_boundary_record` (`scripts/qualify_telegram_monitor.py:2495` at base) refused with `multiple-narrations` whenever:
  ```python
  narrative.updated_at_utc != narrative.created_at_utc
  ```
- **Measurement and attribution:** The shipped product legitimately executes a two-phase write for each narrated digest:
  1. `put_narrative(..., attempt_status="pending")` — the pre-check hand-off state written upon snapshot collection (`src/aether_agents/monitor/runtime.py:979` and `:1236`). In SQLite, this inserts the row with `created_at_utc = now_1` and `updated_at_utc = now_1`.
  2. `put_narrative(..., attempt_status="accepted")` — the validated narration written by the post-LLM hook once the model response validates (`src/aether_agents/monitor/runtime.py:1494`). Because `MonitorStore.put_narrative` (`src/aether_agents/monitor/store.py:1013-1039`) is an upsert that advances `updated_at_utc = now_2` while preserving `created_at_utc = now_1`, every successfully narrated digest has `updated_at_utc != created_at_utc`.
  - In retained laboratory v7: row created `19:22:23.975295Z` (130 ms post-collection), updated `19:24:07.902643Z` (the narration turn), with exactly one narrator session (`cron_98cb12ee33ad_20260911_132224`), one native scheduler execution, and one render delivered as three confirmed parts (Bot API ids 4448, 4449, 4450).
  - The canonical contract specifies: "one smoke plus at most one normal narration per active lab digest" (`qualification-isolation.md:132`) and "At most one narration is attempted per enabled digest" (`docs/guides/telegram-monitor.md:33`). The pre-check pending row is a hand-off state, not a second narration attempt or write. The harness oracle was unsatisfiable for the initial smoke and both scheduled boundaries.

## Bounded implementation

The diff is strictly confined to `scripts/qualify_telegram_monitor.py`, `tests/test_telegram_monitor_cli_plugin.py`, and `docs/guides/telegram-monitor.md`. `src/aether_agents/**` is byte-identical (0 product changes).

### Truthful narration oracle (`scripts/qualify_telegram_monitor.py`)

- `scripts/qualify_telegram_monitor.py:2495-2507`: `ordered = sorted(deliveries, key=lambda delivery: delivery.part_index)` and delivery confirmation checks (`states == ["confirmed"]` and `message_id is not None`) run first to establish confirmed delivery parts.
- `scripts/qualify_telegram_monitor.py:2508-2519`: The oracle asserts `narrative.attempt_status == "accepted"` and `narrative.structured_result is not None`, and requires a non-empty `narrative.narrator_session_id`.
- `scripts/qualify_telegram_monitor.py:2520-2556`: Narration lifecycle and timing checks:
  1. Computes `render_created = min(delivery.created_at_utc)` across all ordered parts (falling back to `updated_at_utc` if mock objects lack `created_at_utc`).
  2. Lifecycle monotonicity: asserts `narrative_updated >= narrative_created`. If `narrative_updated < narrative_created`, raises `QualificationError("multiple-narrations", "narrative update timestamp predates creation")`.
  3. Delivery sequencing: asserts `narrative_updated <= render_created`. If `narrative_updated > render_created`, raises `QualificationError("multiple-narrations", "a single digest produced more than one narration write")`.
- `scripts/qualify_telegram_monitor.py:2638-2650`: `narration_writes` is derived truthfully from observed state (`1` when `narrative.attempt_status == "accepted" and narrative.structured_result is not None`, else `0`) rather than hard-coded.

### Documentation alignment (`docs/guides/telegram-monitor.md`)

- `docs/guides/telegram-monitor.md:375, 381`: Replaced "single-write narration" phrasing with "one accepted narration" and "with an accepted Morfeo narrative" to reflect the shipped product's two-phase write lifecycle while maintaining the requirement of at most one accepted narration.

### Deterministic guard and unit tests (`tests/test_telegram_monitor_cli_plugin.py`)

- `tests/test_telegram_monitor_cli_plugin.py:1274, 1282`: Added `created: str = "2026-09-10T14:00:40.000000Z"` to `_fake_delivery` SimpleNamespace.
- `tests/test_telegram_monitor_cli_plugin.py:1602-1644`: In `test_boundary_record_validates_expectations_and_failures`:
  - Verified that the legitimate pending→accepted write (`created=14:00:20`, `updated=14:00:35` before render at `14:00:40`) passes `_boundary_record` with `narration_writes == 1` and `narration_status == "accepted"`.
  - Verified that a second write after render (`updated=14:00:50`) is refused with `multiple-narrations`.
  - Verified that an inverted timestamp (`updated < created`) is refused with `multiple-narrations`.
- `tests/test_telegram_monitor_cli_plugin.py:1671-1811`: Added `test_narration_oracle_guards_shipped_two_phase_write`:
  - Drives a real `MonitorStore`, acquires a collection lease, and creates a snapshot.
  - Drives the real shipped two-phase write: `put_narrative(..., attempt_status="pending")` then `put_narrative(..., attempt_status="accepted")`.
  - Enqueues deliveries via `reporting.render_parts` and confirms them via `store.claim_delivery` + `store.complete_delivery`.
  - Evaluates both smoke (`cutoff_mode="not-after"`) and scheduled boundary (`cutoff_mode="exact"`) oracles; both pass with `narration_writes == 1`.
  - Drives a second `put_narrative(..., attempt_status="accepted")` call through `MonitorStore` (post-render re-narration write) and asserts both smoke and boundary oracles refuse it with `QualificationError("multiple-narrations")`.

## Chosen detection and honest limits

The chosen detection combines multiple orthogonal signals present in durable storage and run evidence:

1. **`narrative.updated_at_utc <= min(delivery.created_at_utc)`:**
   - *What it proves:* The accepted narration write occurred before delivery parts were rendered and enqueued into the outbox. Any subsequent narration write (re-narration, late callback, or duplicate attempt post-render) advances `narrative.updated_at_utc` past `min(delivery.created_at_utc)` and is refused with `multiple-narrations`.
   - *What it cannot prove:* It cannot detect multiple rapid writes that occur entirely *before* delivery parts are enqueued, because SQLite `narratives` is an upsert table with one row per `report_id`.
2. **`narrative.created_at_utc <= narrative.updated_at_utc`:**
   - *What it proves:* The two-phase lifecycle ordering holds (pending hand-off at `created_at_utc` was followed by or coincident with accepted write at `updated_at_utc`).
   - *What it cannot prove:* Does not record intermediate states between creation and final update.
3. **`narrative.attempt_status == "accepted"` and non-empty `narrative.narrator_session_id`:**
   - *What it proves:* Narration was accepted by the post-LLM validation hook and tied to a single native narrator session identifier (`cron_<job_id>_<timestamp>`).
   - *What it cannot prove:* Does not inspect the internal LLM interaction transcript directly.
4. **`run_evidence["count"] == 1` and report identity presence (`_boundary_record:2583-2603`):**
   - *What it proves:* The native scheduler recorded exactly one job run for this boundary window, and that single run record explicitly references the report ID.
   - *What it cannot prove:* Sub-process details beyond what the scheduler logs.

In synthesis: A single native job execution (`run_evidence`) bound to a single narrator session (`narrator_session_id`), transitioning through the legitimate two-phase lifecycle (`created_at_utc <= updated_at_utc`), producing an accepted narrative before delivery enqueue (`updated_at_utc <= render_created`), with all delivery parts confirmed. Any re-narration or duplicate narration write post-render is detected and refused.

## Acceptance coverage

| Obligation | Check and observed result | Evidence location |
| --- | --- | --- |
| Legitimate pending→accepted digest accepted | **PASS**: Digest with `created_at_utc != updated_at_utc` before render creation satisfies smoke and boundary oracles; `narration_writes == 1`, `narration_status == "accepted"`. | `tests/test_telegram_monitor_cli_plugin.py:1602-1620, 1749-1779` |
| Second narration write refused | **PASS**: Second write after render enqueue (`updated_at_utc > render_created`) raises `QualificationError("multiple-narrations")` for both smoke and boundary modes. | `tests/test_telegram_monitor_cli_plugin.py:1622-1633, 1781-1810` |
| Inverted narrative timestamps refused | **PASS**: Timestamp inversion (`updated_at_utc < created_at_utc`) raises `QualificationError("multiple-narrations")`. | `tests/test_telegram_monitor_cli_plugin.py:1634-1644` |
| Truthful receipt labels | **PASS**: `narration_writes` reports observed accepted count (`1` when accepted with structured result, `0` otherwise). | `scripts/qualify_telegram_monitor.py:2638-2642`, `tests/test_telegram_monitor_cli_plugin.py:1559, 1618, 1759, 1778` |
| Deterministic guard for shipped two-phase write | **PASS**: `test_narration_oracle_guards_shipped_two_phase_write` drives real `MonitorStore` pending→accepted write and asserts oracle behavior without live effects. | `tests/test_telegram_monitor_cli_plugin.py:1671-1811` |
| Replay of retained v7 evidence | **PASS**: Replay of v7 evidence on laboratory copy builds smoke entry for `rpt_437a1b3d8aba7a749b305c6da3a9c6fd` cleanly. | See section "Replay of retained v7 evidence" below |
| Offline deterministic lane | **PASS**: `ok: true`, 12/12 checks, `external_effects: {model_calls: 0, telegram_sends: 0}`. | `TMPDIR=/tmp uv run --frozen python scripts/qualify_telegram_monitor.py --json` |
| Focused monitor lane | **PASS**: 330 passed, 5 skipped. | `PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_*.py` |

## Fail-before / pass-after

Measured first-hand against base `e6bae9959a84993686c18c05e76724c708aa61d5`:

| Behavior-bearing check | Base `e6bae99` observation | Candidate `312ef41` observation |
| --- | --- | --- |
| Retained v7 evidence replay (`_boundary_record` on v7 smoke snapshot) | **FAIL**: `QualificationError: ('multiple-narrations', 'a single digest produced more than one narration write')`, `detail: {'created_at_utc': '2026-09-11T19:22:23.975295Z', 'updated_at_utc': '2026-09-11T19:24:07.902643Z'}` | **PASS**: `SMOKE ORACLE CHAIN: PASS (TRUTHFUL ORACLE)`. Smoke entry for `rpt_437a1b3d8aba7a749b305c6da3a9c6fd` built with `narration_status: accepted, narration_writes: 1, delivery_states: ['confirmed'], part_count: 3`. |
| Shipped two-phase write acceptance (`test_narration_oracle_guards_shipped_two_phase_write`) | **FAIL**: `QualificationError: ('multiple-narrations', 'a single digest produced more than one narration write')`, `detail: {'created_at_utc': '2026-09-11T19:44:24.267458Z', 'updated_at_utc': '2026-09-11T19:44:24.267910Z'}` | **PASS**: `smoke_record["narration_writes"] == 1`, `smoke_record["narration_status"] == "accepted"`, `boundary_record["narration_writes"] == 1`. |
| Simulated second narration refusal (`test_boundary_record_validates_expectations_and_failures`) | **PASS**: Failed on any `updated != created` (coincidentally caught `updated=14:00:50` by over-refusing legitimate writes). | **PASS**: Specifically detects `updated_at_utc > render_created` and `updated_at_utc < created_at_utc`, raising `multiple-narrations` while accepting legitimate prior writes. |

## Replay of retained v7 evidence

The retained v7 laboratory (`/home/darkarty/.local/state/aether/monitor/lab/20260911T192140Z-323d4532323e`) was copied to `/tmp/v7replay_test/labcopy` (retained root kept pristine and read-only). The real v7 smoke snapshot (`rpt_437a1b3d8aba7a749b305c6da3a9c6fd`), narrative, confirmed deliveries, job record, and run evidence were evaluated through the truthful `_boundary_record` oracle:

```
SMOKE ORACLE CHAIN: PASS (TRUTHFUL ORACLE)
{
 "cutoff_utc": "2026-09-11T19:22:00.000000Z",
 "expected_cutoff_utc": "2026-09-11T19:22:23.845656Z",
 "previous_cutoff_utc": null,
 "collected_at_utc": "2026-09-11T19:22:23.845656Z",
 "collected_lateness_seconds": 23.846,
 "narration_status": "accepted",
 "narration_writes": 1,
 "narration_created_at_utc": "2026-09-11T19:22:23.975295Z",
 "narration_lateness_seconds": 23.975,
 "narrator_session_id": "cron_98cb12ee33ad_20260911_132224",
 "delivery_states": [
  "confirmed"
 ],
 "part_count": 3,
 "part_attempts": [
  1,
  1,
  1
 ],
 "message_ids": [
  "4448",
  "4449",
  "4450"
 ],
 "acknowledged_at_utc": "2026-09-11T19:24:11.046336Z",
 "ack_lateness_seconds": 131.046,
 "report_id": "rpt_437a1b3d8aba7a749b305c6da3a9c6fd",
 "item_states": {
  "direct:49b04749-3f78-520b-830a-b5ac4ca1a46c:qualification-direct-20260911T192140Z:qualification-turn-20260911T192140Z-1": "turn_ended_unknown",
  "pipeline:49b04749-3f78-520b-830a-b5ac4ca1a46c:oc_feeb89c0750158cf:qualification-origin-20260911T192140Z-a": "running",
  "pipeline:4da1b3f7-8880-5596-ae43-8ae15ea9baa1:oc_f725adb1848b5966:qualification-origin-20260911T192140Z-b": "review"
 },
 "coverage_gaps": [],
 "native_run_files": 1,
 "job_last_status": "ok"
}
```

## Verification commands and observed results

1. **Branch and base verification:**
   - `git log --oneline -4`: `e6bae99` at tip.
   - `git status`: clean.
2. **Deterministic lane:**
   - Command: `TMPDIR=/tmp uv run --frozen python scripts/qualify_telegram_monitor.py --json`
   - Result: `ok: true`, 12/12 checks pass, `external_effects: {"model_calls": 0, "telegram_sends": 0}`, check set unchanged.
3. **Focused monitor test lane:**
   - Command: `PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_*.py`
   - Result: `330 passed, 5 skipped in 20.76s` (pass count increased from 329 to 330 with the added guard test).
4. **Full runner:**
   - Command: `uv run --frozen python scripts/run_tests.py`
   - Result: `2 failed, 1516 passed, 69 skipped in 286.14s`. The two failed tests are the two known pre-existing findings only:
     - `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths` (pre-existing `oc_0084270d940c98d9/v1.md` rows)
     - `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer` (documented pre-existing)
5. **Type checking:**
   - Command: `uv run --frozen mypy src/aether_agents`
   - Result: `Success: no issues found in 65 source files`.
6. **Documentation check:**
   - Command: `uv run --frozen python scripts/check_documentation.py`
   - Result: `documentation validation passed`.
7. **Code formatting and linting (policy job path list):**
   - Command: `uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py`
   - Result: `All checks passed!`.
   - Command: `uv run --frozen ruff format --check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py`
   - Result: `150 files already formatted`.
8. **Bytecode compilation:**
   - Command: `python3 -m compileall src scripts tests`
   - Result: all files compiled clean.
9. **Package build:**
   - Command: `uv build`
   - Result: `Successfully built dist/aether_agents-0.24.0.tar.gz` and `dist/aether_agents-0.24.0-py3-none-any.whl`.
10. **Git diff check:**
    - Command: `git diff --check e6bae99`
    - Result: exit 0, no whitespace or formatting errors.
11. **Public artifact scan:**
    - Command: `python3 scripts/check_public_artifacts.py`
    - Result: only the two documented pre-existing `oc_0084270d940c98d9/v1.md` rows.
12. **Policy manifest emulation:**
    - Command: bash script emulating `.github/workflows/policy.yml` lines 26–440.
    - Result: `Diff exit: 0`, 377 paths in base manifest exact match, 172 spec rows validated.

## Preservation, compatibility and residual risk

- **Preserved unchanged:** Every design document, Objective Contract `oc_f8c9fc9320587cf3@v4`, all prior evidence records, harness public CLI (`--json`, `--live`, `--wait-hourly-boundaries 2`, `--output`), production schedule `0 * * * *`, `src/aether_agents/**` (zero product code changes), D14/D14R/D15R/D16/D16R/D16S/D16T semantics, retained laboratories (`20260911T125411Z-1181c8ac8baf`, `20260911T155646Z-8cd41cdb6427`, `20260911T192140Z-323d4532323e`), private evidence directory and receipts, and operator registry/boards/sessions/jobs/state.
- **Unit compatibility conclusion:** The change is confined to qualification harness narration oracle evaluation, truthful receipt reporting, documentation alignment in the operator guide, and associated regression tests. Production behavior is completely unaffected.
- **Residual risk:** The laboratory has still never crossed its first *scheduled* cut, and the D12 semantic corpus, the idle cut and the production-hourly oracle remain unexercised. The next live attempt stays a single, separately authorized attempt; a failure after job/scheduler/model/Telegram effects begin stops the experiment with evidence and no automatic rerun.
