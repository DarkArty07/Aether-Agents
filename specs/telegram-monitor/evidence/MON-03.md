# Implementation Evidence — MON-03

**Status:** D12-aligned bounded implementation complete; self-review complete; ready for same-card Supervisor review.

- **Unit:** MON-03 — bounded Morfeo narrative structure, fidelity prompt and rendering
- **Task:** `t_d4dba852`
- **Objective Contract:** `oc_f8c9fc9320587cf3@v1`
- **Verified base:** `da7bcef5854763bf5b70a5540f707722c158dfbb`
- **Source-owned D12 clarification:** `dfc127ff65ff3f368a15c26bc18c50128a1acd03`
- **Supervisor decomposition reconciliation:** `2631fa586858dbfc527f215c20921134a2881f9c`
- **Implementation candidate:** `dc19fe31d3c7cf21dbf35cb6669f495f39ee97e2`
  (`fix(monitor): close typed reporting and compaction boundaries`; receipt is updated in a following commit).
- **Flow reconciliation provenance:** merge `ae6c671df450e3b7b0c99a996ea228919842f4ea`
  preserves the source clarification; its tree was already present through the equivalent
  imported source commit and therefore produced no duplicate tree change here.
- **Prior reviewed candidates:**
  - `995f32096128afd8ffbd4da8ef86209952ab664c` — superseded after round-1 adversarial review.
  - `c132d19603c5c082e52c67e5d4652d05a76f5dac` through `be7548bd71cad5a624fea355bb528fe4b9373adc` — superseded by subsequent review corrections.

The candidate SHA identifies the delivered code, resource, and tests. This receipt is
intentionally updated in a following documentation commit, so it does not make a
self-referential claim about the commit that contains the receipt itself.

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
| Bound the model snapshot at 24,000 Unicode characters while retaining all work identities, validating source relations before compaction, and preserving reference closure or emitting explicit relation coverage notices | `test_compaction_preserves_all_work_identities_and_is_bounded`; `test_compaction_omits_excess_state_refs_before_identity_limit`; `test_compaction_preserves_relation_closure_or_drops_links_with_coverage` | Passed; 35 work identities and a 12-item/128-state-ref-per-item case retain every identity within 24,000 characters; oversized detail is compacted deterministically; related remedy/verification candidates are retained atomically or their links are removed with explicit coverage |
| Package bounded canonical English context; keep snapshot data delimited and prevent instruction-like source text from becoming model instructions | `test_prompt_uses_packaged_english_context_and_bounded_data_delimiter`; `test_selected_source_canaries_fail_before_prompt`; `test_spanish_instruction_canary_fails_before_prompt_or_output`; packaged-wheel resource probe | Passed; selected absolute-path, role-label, transcript, credential, token, PII, and Spanish instruction/destination canaries fail before prompt construction; the prompt explicitly delegates prose fidelity to Morfeo |
| Validate exactly one narrative envelope against exact report/work/source references and reject malformed, duplicate, unknown, mixed, misplaced, or source-authority-mismatched claims | `test_valid_narrative_requires_exact_items_and_renders_source_owned_identity`; `test_unknown_report_work_and_source_refs_are_rejected`; `test_mixed_work_ref_is_rejected_even_when_text_looks_plausible`; `test_linked_evidence_refs_cannot_cross_work_identity`; `test_state_evidence_refs_cannot_be_narrative_claim_refs` | Passed; report/work/ref identity, same-work linked evidence, source section, provenance, and status are enforced, and state-only evidence refs remain renderer/header evidence rather than narrative claims |
| Enforce typed whole-work status equality and verified evidence for canonical completion without certifying arbitrary prose semantics | `test_model_status_matches_canonical_observed_state_or_unknown_mapping`; `test_noncanonical_source_states_map_to_unknown_without_completion_authority`; `test_model_status_tokens_require_exact_canonical_spelling`; `test_completed_status_requires_verified_observed_resolution_evidence`; `test_fabricated_completion_requires_verified_observed_completion_evidence`; `test_readiness_observed_states_cannot_ground_terminal_completion`; `test_noncompletion_terminal_statuses_must_match_observed_state` | Passed; model status must equal the exact closed canonical observed lifecycle or deterministic `unknown` mapping; case/separator/whitespace variants cannot authorize completion, and only exact observed `completed` plus verified observed resolution permits `completed`. Readiness, milestone, and free-form prose are not lifecycle authority |
| Render immutable project, origin-session, contract/no-contract, report period, local offset, observed/reported labels, no-evidence labels, and linked remedy/verification evidence | `test_valid_narrative_requires_exact_items_and_renders_source_owned_identity`; `test_contractless_identity_and_missing_times_are_explicit`; `test_complication_links_render_remedy_and_verification_evidence` | Passed; offset timestamps are converted to true UTC under UTC labels, local offset remains explicit, and headers are generated from the snapshot |
| Preserve bounded prose and prompt privacy/instruction safety while leaving completion, forecast, percentage, and time semantics to Morfeo's quality qualification | `test_semantic_prose_is_quality_input_not_a_deterministic_claim_gate`; `test_unsafe_canaries_fail_before_prompt_or_output`; `test_legitimate_pending_readiness_and_delivery_controls_preserved`; `test_source_and_narrative_limits_are_enforced` | Passed; historical English/Spanish semantic cases remain bounded prompt/output data, while privacy/instruction canaries, shape, and length limits fail closed. The prompt forbids invented completion/time/percentage/deadline claims; actual semantic fidelity is a MON-06/MON-INT live corpus obligation |
| Keep every prompt-bound coverage-gap shape bounded and privacy-safe while preserving semantic diagnostics and compaction notices | `test_coverage_gap_semantics_remain_data_while_privacy_stays_structural`; `test_compaction_preserves_all_work_identities_and_is_bounded`; `test_legitimate_pending_readiness_and_delivery_controls_preserved` | Passed; string, coded-message, and fact-shaped gaps preserve arbitrary diagnostic prose and `[COMPACTED]` notices, while unsafe content is rejected and no gap becomes a claimable narrative source |
| Split one accepted narrative deterministically into ordered <=3,500-Unicode-character parts, repeating identity and part markers without another narration | `test_parts_are_ordered_bounded_unicode_and_repeat_identity_without_second_narration`; direct Unicode split assertions | Passed; every part is bounded, ordered, identity-prefixed, and deterministic |
| Narration failure emits only the fixed labeled service notice and does not mark progress coverage | `test_narration_failure_is_fixed_labeled_notice_and_does_not_use_reason`; `test_narration_failure_notice_parts_are_bounded_and_repeat_identity` | Passed; unbounded calls return the fixed notice, bounded calls return ordered <=3,500-character parts with repeated identity and no supplied failure reason |
| Reporting is pure and does not call Hermes, model, Telegram, tools, or network | `test_reporting_module_is_pure_and_has_no_network_or_hermes_imports`; module imports only standard-library modules; no runtime integration imports | Passed; no Hermes/network/tool client import or call exists in the unit |

## Verification receipt

Commands were run in the assigned worktree against candidate
`dc19fe31d3c7cf21dbf35cb6669f495f39ee97e2`:

- `uv run --frozen pytest -q tests/test_telegram_monitor_reporting.py` — **61 passed**.
- `uv run --frozen python scripts/run_tests.py -- tests/test_telegram_monitor_reporting.py -q` — **61 passed** with the repository's exact-Hermes bootstrap.
- `uv run --frozen ruff check src/aether_agents/monitor/reporting.py tests/test_telegram_monitor_reporting.py` — **passed**.
- `uv run --frozen ruff format --check src/aether_agents/monitor/reporting.py tests/test_telegram_monitor_reporting.py` — **2 files already formatted**.
- `uv run --frozen mypy src/aether_agents/monitor/reporting.py` — **no issues** (with the repository's existing unused-config note).
- `uv run --frozen python -m compileall -q src tests` — **passed**.
- `uv build` — **built** source distribution and wheel; both contain the reporting module and narration resource.
- Disposable wheel/sdist resource probe — **passed**; both artifacts contain the reporting module and canonical narration context.
- `uv run --frozen python scripts/check_documentation.py --root .` — **passed**.
- `git diff --check` and `git diff --cached --check` — **passed** for the candidate commit.
- Full `uv run --frozen python scripts/run_tests.py` — **1 failed, 1,144 passed, 60 skipped** in 182.55s; the sole failure is the pre-existing public-artifact scan for finalized contract `oc_0084270d940c98d9/v1.md` (`absolute-user-home` and `operator-desktop-layout`, issue #364). `tests/test_telegram_monitor_reporting.py` passed as part of this run.
- `uv run --frozen python scripts/check_public_artifacts.py --root .` — the same known baseline issue #364 only.
- Project-knowledge status/query — status reported `available=false` and query returned `INDEX_MISSING`; one configured update for candidate `dc19fe31d3c7cf21dbf35cb6669f495f39ee97e2` timed out. No profile, provider, or semantic-provider change was made; direct source inspection and executable tests remained authoritative.

No model, Telegram, cron, profile, activation, credential, or network qualification was
performed by this unit.

## Compatibility and remaining risk

**Unit compatibility impact: minor/additive.** The candidate adds a new reporting module,
resource, and tests without changing existing imports, CLI/tool shapes, entry points, or
native behavior. Aggregate release action/channel remain Supervisor-owned; this unit makes
no release or publication decision.

No live model invocation, Telegram send, cron/profile mutation, activation, or network
qualification was authorized for this implementation unit. Integration with the accepted
state/source/delivery/runtime units, live identity and transport qualification, and final
Supervisor acceptance remain outstanding and are not claimed here.
