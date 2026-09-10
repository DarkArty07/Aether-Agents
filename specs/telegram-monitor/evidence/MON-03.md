# Implementation Evidence — MON-03

**Status:** bounded implementation complete; self-review complete; ready for same-card Supervisor review.

- **Unit:** MON-03 — bounded Morfeo narrative validation and rendering
- **Task:** `t_d4dba852`
- **Objective Contract:** `oc_f8c9fc9320587cf3@v1`
- **Verified base:** `da7bcef5854763bf5b70a5540f707722c158dfbb`
- **Implementation candidate:** `a9ca8b59b543eaaa2ee0086ce37b7575113428d1`
- **Commit:** `a9ca8b5` — `feat(monitor): add bounded narrative reporting`

## Scope and changed paths

The unit adds only the pure reporting module, the canonical English narration resource,
and focused deterministic tests:

- `src/aether_agents/monitor/reporting.py`
- `src/aether_agents/resources/monitor/narration-context.md`
- `tests/test_telegram_monitor_reporting.py`
- this evidence file: `specs/telegram-monitor/evidence/MON-03.md`

New non-`specs/` paths for MON-06's literal policy-manifest inventory are exactly the
first three paths above. No store row classes, source adapters, delivery, runtime, CLI,
entry-point, profile, SOUL, policy, Objective Contract, or source database was changed.

## Requirement-to-evidence matrix

| Obligation | Check actually run | Observed result |
| --- | --- | --- |
| Consume the fixed `aether.telegram-monitor.snapshot.v1` mapping, preserve optional contract/no-contract identity, validate timestamps and bounds, and deterministically order inputs | `test_snapshot_is_normalized_deterministically_and_contract_is_optional`; `test_contractless_identity_and_missing_times_are_explicit`; focused suite | Passed; optional contract stays explicit, missing item times render as unknown, item/fact order is stable |
| Bound source excerpts at 1,200 characters and narrative prose at 600 characters | `test_source_and_narrative_limits_are_enforced` | Passed; over-limit source and model prose are rejected closed |
| Keep the model snapshot at 24,000 Unicode characters while retaining all work identities and emitting compaction coverage notices | `test_compaction_preserves_all_work_identities_and_is_bounded` | Passed; 35 work identities retained, canonical JSON is within 24,000 characters, compaction is deterministic and labeled |
| Package bounded canonical English context; keep snapshot data delimited and prevent instruction-like source text from becoming model instructions | `test_prompt_uses_packaged_english_context_and_bounded_data_delimiter`; packaged-wheel resource probe | Passed; resource loads from the built wheel and prompt labels the bounded snapshot as data |
| Validate exactly one narrative envelope against exact report/work/source references and reject malformed, duplicate, unknown, mixed, misplaced, or source-authority-mismatched claims | `test_valid_narrative_requires_exact_items_and_renders_source_owned_identity`; `test_unknown_report_work_and_source_refs_are_rejected`; `test_mixed_work_ref_is_rejected_even_when_text_looks_plausible` | Passed; report/work/ref identity and source section/provenance/status are enforced |
| Reject fabricated completion unless the observed item is terminal and has verified observed resolution evidence | `test_fabricated_completion_requires_verified_observed_completion_evidence` | Passed; in-progress and unsupported completion claims fail, evidenced terminal resolution is accepted |
| Render immutable project, origin-session, contract/no-contract, report period, local offset, observed/reported labels, no-evidence labels, and linked remedy/verification evidence | `test_valid_narrative_requires_exact_items_and_renders_source_owned_identity`; `test_contractless_identity_and_missing_times_are_explicit`; `test_complication_links_render_remedy_and_verification_evidence` | Passed; headers are generated from the snapshot, not model output |
| Reject percentages, ETA/forecast claims, CPU/agent-hour claims, prompt injection, credential/token/path/PII/raw-transcript canaries | `test_forbidden_claims_and_unsafe_canaries_fail_before_prompt_or_output`; `test_narration_failure_is_fixed_labeled_notice_and_does_not_use_reason` | Passed; unsafe/forbidden content fails closed and error reason is not rendered |
| Split one accepted narrative deterministically into ordered <=3,500-Unicode-character parts, repeating identity and part markers without another narration | `test_parts_are_ordered_bounded_unicode_and_repeat_identity_without_second_narration`; direct Unicode split assertions | Passed; every part is bounded, ordered, identity-prefixed, and deterministic |
| Narration failure emits only the fixed labeled service notice and does not mark progress coverage | `test_narration_failure_is_fixed_labeled_notice_and_does_not_use_reason` | Passed; notice contains service/no-progress labels and no supplied failure reason |
| Reporting is pure and does not call Hermes, model, Telegram, tools, or network | `test_reporting_module_is_pure_and_has_no_network_or_hermes_imports`; module imports only standard-library modules; no runtime integration imports | Passed; no Hermes/network/tool client import or call exists in the unit |

## Verification receipt

Commands were run in the assigned worktree against the candidate source:

- `uv run --frozen pytest -q tests/test_telegram_monitor_reporting.py` — **14 passed**.
- `uv run --frozen python scripts/run_tests.py -- tests/test_telegram_monitor_reporting.py -q` — **14 passed** with the repository's exact-Hermes bootstrap.
- `uv run --frozen ruff check src/aether_agents/monitor/reporting.py tests/test_telegram_monitor_reporting.py` — **passed**.
- `uv run --frozen ruff format --check src/aether_agents/monitor/reporting.py tests/test_telegram_monitor_reporting.py` — **2 files already formatted**.
- `uv run --frozen mypy src/aether_agents/monitor/reporting.py` — **no issues**. The broader `uv run --frozen mypy src/aether_agents` check also passed for **54 source files**.
- `uv run --frozen python -m compileall -q src tests` — **passed**.
- `uv build` — **built** source distribution and wheel; both contain the reporting module and narration resource.
- Disposable installed-wheel resource probe — **passed**; packaged narration context loaded successfully.
- `uv run --frozen python scripts/check_documentation.py --root .` — **passed**; this unit changes no registered public documentation surface.
- `git diff --check` and `git diff --cached --check` — **passed** before commit.

Two broader checks exposed the documented pre-existing baseline limitation rather than a
MON-03 failure:

- Direct `uv run --frozen pytest -q` cannot collect `tests/test_same_card_phase_predicates.py`
  because the manager environment does not provide `hermes_cli`; the exact-Hermes repository
  runner above passes the focused unit.
- `tests/test_telegram_monitor_reporting.py tests/test_documentation.py tests/test_public_artifacts.py`
  produced **25 passed, 1 failed**: the existing public-artifact scanner failure for finalized
  contract `oc_0084270d940c98d9/v1.md` (issue #364). MON-03 did not touch that contract.

## Compatibility and remaining risk

**Unit compatibility impact: minor/additive.** The candidate adds a new reporting module,
resource, and tests without changing existing imports, CLI/tool shapes, entry points, or
native behavior. Aggregate release action/channel remain Supervisor-owned; this unit makes
no release or publication decision.

No live model invocation, Telegram send, cron/profile mutation, activation, or network
qualification was authorized for this implementation unit. Integration with the accepted
state/source/delivery/runtime units, live identity and transport qualification, and final
Supervisor acceptance remain outstanding and are not claimed here.
