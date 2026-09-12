# MON-04 Implementation Evidence — native Telegram delivery

**Unit:** MON-04
**Task:** `t_a08bbd2b`
**Objective Contract:** `oc_f8c9fc9320587cf3@v1`
**Round-1 reviewed commit:** `c762b8b4af7accf2d92a5b24dcabe2d62b8a5843` (same-card Supervisor review returned changes)
**Base commit:** `9d107f2ab89f38fb65e273fafef1a55a84437b74`
**Candidate implementation tree SHA (before this evidence file):** `493fd107e1f80334e7c1bb920e350826c8f1b9fc`
**Status:** Rework round 1 complete and self-verified; ready for same-card Supervisor review.

## Review findings and resolutions

The round-1 review observed three defects against the reviewed candidate. Each is fixed in
this round and carried by a deterministic, non-network check.

1. **The selected native seam did not preserve MON-04's safe/exact boundary.** The adapter
   delegated to `_send_to_platform`, whose exact-baseline behavior chunks, retries
   internally, and falls back from `Message thread not found` to the general chat without
   the thread.
   *Resolution:* the adapter no longer calls `_send_to_platform`/`_send_telegram`. It calls
   the exact baseline's lower-level
   `tools/send_message_tool.py:190 _send_telegram_message_with_retry(bot, attempts=1, ...)`,
   which performs exactly one `bot.send_message(...)` call, keeps `message_thread_id`
   verbatim, and re-raises transport exceptions without internal replay or fallback.
   Chat-id normalization reuses
   `plugins/platforms/telegram/telegram_ids.py:23 normalize_telegram_chat_id`. The Bot is
   built with the same configured proxy the native path uses
   (`tools/send_message_tool.py:1371 resolve_proxy_url("TELEGRAM_PROXY", ...)`), falling
   back to the direct Bot without changing recipient. The adapter also mirrors Hermes'
   General-topic mapping (`plugins/platforms/telegram/adapter.py:1614
   _message_thread_id_for_send`, `_GENERAL_TOPIC_THREAD_ID = "1"` at `:666`) so a pinned
   General topic (`"1"`) omits `message_thread_id` instead of being rejected by the Bot API.
   *Checks:* `test_native_seam_uses_one_exact_bot_attempt_and_preserves_thread`;
   `test_native_seam_keeps_the_exact_thread_maps_general_topic_and_uses_configured_proxy`;
   and the exact-source probe `test_exact_hermes_single_attempt_seam_never_replays_or_falls_back`.

2. **The pinned target was resolved once and reused across parts and retries.** A
   deterministic probe changed the configured target after part 1 and the adapter still
   returned `confirmed` for the stale target.
   *Resolution:* `_target_for_attempt` re-reads the persisted settings and re-resolves the
   exact pinned target immediately before **every** transport attempt — after the
   lease/manual-off recheck, inside the retry loop, in both the sync and async paths. A
   changed destination, changed profile binding, disabled monitor, missing/unresolvable
   target, or foreign resolver exception fails closed before any send.
   *Checks:* `test_target_is_reresolved_between_multipart_parts_and_stale_pin_fails_closed`;
   `test_target_is_reresolved_after_retry_delay_before_replay`;
   `test_profile_binding_change_between_parts_fails_closed_without_send`.

3. **`_safe_token` was a syntax filter, not a privacy boundary.** A sender result with
   `error_class="BOT_SECRET"` persisted the foreign class, so arbitrary token-shaped
   credential/identifier text could cross the durable/public error boundary.
   *Resolution:* `_SAFE_ERROR_CLASSES` is a closed local taxonomy and `_safe_token` returns
   only an exact member; foreign result fields, native exception data, and adapter
   configuration exceptions (`DeliveryConfigurationError`) all map through it. Every
   error-class literal used in the module is a member of the closed set (verified by
   inspection of the module source).
   *Checks:* `test_foreign_error_classes_and_configuration_exceptions_use_closed_taxonomy`
   asserts canary absence from the returned `DeliveryRun`, the persisted delivery row, and
   the durable SQLite files (main, WAL, SHM); `test_native_error_text_is_reduced_to_a_safe_taxonomy_token`.

## Scope and changed paths

Only the assigned MON-04 paths are changed:

- `src/aether_agents/monitor/delivery.py`
- `tests/test_telegram_monitor_delivery.py`
- `specs/telegram-monitor/evidence/MON-04.md`

The new non-`specs/` path inventory for MON-06 remains the delivery adapter and its focused
regression test. No store/model/reporting/source/runtime/CLI/plugin/profile/policy,
Objective Contract, source database, Hermes checkout, or live profile was modified.

## Implemented behavior

- One lazy `TelegramDeliveryAdapter` around the existing native Hermes Telegram transport.
  The module imports no Hermes/gateway code at load time; the native boundary is resolved
  only when a real sender is needed. Missing native modules fail closed as
  `native-sender-unavailable` rather than degrading to another transport.
- Default native sender: one exact Bot API call per attempt through the release-locked
  `_send_telegram_message_with_retry(attempts=1)` seam with Hermes' chat-id normalization,
  General-topic mapping, and configured proxy. Only a returned native response carrying a
  message ID is `confirmed`; a successful response without a message ID is `uncertain`.
- The adapter accepts only a pinned target whose opaque reference matches both the
  persisted monitor setting and the target's canonical chat/thread binding, re-verified
  before each attempt. Missing, changed, malformed, profile-mismatched, or unresolved
  targets fail closed before the sender is called; the adapter never accepts an
  outbox/source recipient or fallback destination.
- Rendered parts are checked against the immutable store text hashes and sent in index
  order. Confirmed parts are skipped on restart. Explicit pre-dispatch failures are
  retryable with bounded `retry_after` delay and no more than three attempts per part.
  Timeout, empty, post-dispatch, raised transport exceptions, and unclassified native
  results become durable `uncertain` outcomes and are never blindly replayed.
- Store delivery leases fence concurrent callers and are rechecked after claim, so manual
  off suppresses a claimed part without invoking the sender. Coverage markers advance only
  after every delivery part is durably confirmed.
- Error text is reduced to the closed local taxonomy; error messages, target values,
  credential-shaped text, paths, and raw sender exceptions are not persisted or returned.

## Requirement-to-evidence mapping

| Obligation | Check executed | Observed result |
| --- | --- | --- |
| Explicit accepted native receipt | `test_explicit_native_message_id_confirms_parts_in_order_and_advances_coverage`; `test_async_native_sender_is_lazy_and_explicit_ack_is_required`; `test_native_seam_uses_one_exact_bot_attempt_and_preserves_thread` | Parts were invoked in order, message IDs were persisted, and coverage advanced only after all parts confirmed; one exact Bot call with the pinned chat/thread. |
| One-attempt exact native seam (review finding 1) | `test_exact_hermes_single_attempt_seam_never_replays_or_falls_back` (`hermes_exact`) | Against the verified `v2026.8.18` @ `e624e9f` source: `attempts=1` produced exactly one Bot call for accepted, `Message thread not found`, `503 Service Unavailable`, and timeout cases (exception re-raised, thread preserved, no fallback); the native default (`attempts=3`) replayed the same 503 twice with stubbed sleep, which is why the adapter pins one attempt. |
| General-topic and proxy parity | `test_native_seam_keeps_the_exact_thread_maps_general_topic_and_uses_configured_proxy` | Thread `"1"` omitted `message_thread_id`; thread `"7"` sent it; invalid threads failed closed; a configured proxy built the proxied Bot while a broken proxy helper fell back to the direct Bot with the same chat/thread. |
| Pre-dispatch retry and retry-after/max-three bound | `test_pre_dispatch_failure_honors_retry_after_and_never_exceeds_three_attempts`; `test_raised_pre_dispatch_error_is_retryable_but_unknown_exception_is_not` | Retry-after was honored; attempts were exactly bounded at three; unknown exceptions were not replayed. |
| Ambiguous outcomes are uncertain | `test_timeout_empty_and_post_dispatch_results_are_uncertain_without_retry`; `test_raised_pre_dispatch_error_is_retryable_but_unknown_exception_is_not`; `test_native_error_text_is_reduced_to_a_safe_taxonomy_token` | Timeout, empty, post-dispatch, unknown transport, and native unclassified error results were persisted as uncertain with no blind retry. |
| Per-attempt target re-resolution (review finding 2) | `test_target_is_reresolved_between_multipart_parts_and_stale_pin_fails_closed`; `test_target_is_reresolved_after_retry_delay_before_replay`; `test_profile_binding_change_between_parts_fails_closed_without_send` | After part 1 changed the resolver's target, part 2 failed with `destination-changed` without a send and the run was `partial`; a destination change during the retry-after delay stopped the replay after exactly one transport call; a profile-binding change after part 1 made part 2 fail with `profile-binding-changed` without a send. |
| Multipart partial/restart semantics | `test_multipart_partial_failure_restart_skips_confirmed_part_and_coverage_waits` | Confirmed part was not resent; failed and pending parts remained durable; coverage advanced only on the later all-confirmed run. |
| Concurrent invocation and lease fencing | `test_concurrent_invocation_is_fenced_and_only_one_sender_runs` | One sender held the delivery lease; the concurrent invocation observed `delivery-lease-busy` and did not send. |
| Manual off before/after lease recheck | `test_manual_off_after_lease_recheck_suppresses_without_sender_call`; `test_off_before_send_persists_no_send_and_resumes_after_on` | Off-after-lease persisted suppression without a sender call; off-before-send preserved pending work and re-enabled delivery after on. |
| Exact pinned destination/no alternative | `test_missing_changed_or_ambiguous_destination_fails_closed_without_alternative` | Missing, changed, alternate-chat-with-same-pin, and profile-mismatched targets failed before sender invocation; no target value appeared in the result. |
| Immutable rendered parts and privacy | `test_rendered_part_hash_mismatch_and_canaries_never_reach_sender_or_receipt`; `test_native_error_text_is_reduced_to_a_safe_taxonomy_token` | Changed text was rejected before dispatch; seeded path/token/chat canaries were absent from returned and persisted error state. |
| Closed sanitized taxonomy (review finding 3) | `test_foreign_error_classes_and_configuration_exceptions_use_closed_taxonomy` | Foreign error classes and foreign configuration-exception classes were replaced by `sender-failure`/`destination-unavailable` in the run result, the persisted row, and the durable SQLite bytes; the canaries never appeared. |
| Native cron is not a second send path | Source inspection of the exact Hermes sender and fixed `plan.md`/task decisions; adapter contains no cron registration or automatic delivery call | This unit only calls the selected native Telegram transport on explicit adapter invocation; runtime/`deliver=local` wiring remains owned by MON-05. |

## Verification record

All commands were run in the assigned worktree with the locked `uv` environment.

- Focused MON-04 plus dependency regression suite:
  `uv run --frozen pytest -q tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py`
  → **103 passed in 2.70s**.
- Same suite through the exact-Hermes bootstrap lane:
  `uv run --frozen python scripts/run_tests.py -- tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py -q`
  → **103 passed in 2.43s** (bootstrap verifies the release-locked checkout first).
- Supplementary full-repository regression through the same bootstrap lane:
  `uv run --frozen python scripts/run_tests.py -- -q`
  → **1 failed, 1186 passed, 60 skipped, 373 subtests passed in 214.42s**; the sole failure
  is the pre-existing public-artifact issue #364 (`oc_0084270d940c98d9` absolute-user-home
  and operator-desktop-layout), which is unchanged from base and unrelated to MON-04.
  The plain lane without the bootstrap stops at collection because
  `tests/test_same_card_phase_predicates.py` imports the unavailable `hermes_cli` — a
  pre-existing environment limitation already documented by MON-01.
- Exact-seam subset executed, not skipped:
  `uv run --frozen pytest -v tests/test_telegram_monitor_delivery.py -k "exact_hermes or general_topic"`
  → **2 passed, 20 deselected**; `test_exact_hermes_single_attempt_seam_never_replays_or_falls_back`
  resolved the checkout through `AETHER_EXACT_HERMES_CHECKOUT` in the bootstrap lane and
  through `$XDG_CACHE_HOME/aether-agents/hermes/v2026.8.18` in the plain lane, and
  `verify_clean_checkout` confirmed tag `v2026.8.18`, tag object
  `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`.
- Owned and relevant Ruff lint:
  `uv run --frozen ruff check src/aether_agents/monitor tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py`
  → **All checks passed**.
- Owned and relevant formatting:
  `uv run --frozen ruff format --check src/aether_agents/monitor tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py`
  → **8 files already formatted**.
- Owned type check:
  `uv run --frozen mypy src/aether_agents/monitor`
  → **Success: no issues found in 5 source files**; only the pre-existing unused
  optional-module override note was emitted.
- Bytecode and whitespace checks:
  `uv run --frozen python -m compileall -q src tests && git diff --check`
  → **passed**.
- Exact native-source behavior probe this round: the release-locked helper was exercised
  directly with a fake Bot: `attempts=1` produced one call for a success, one call then
  raise for `503 Service Unavailable`, and one call then raise for `Message thread not
  found`; the default `attempts=3` replayed the 503. The same probe is captured
  deterministically by `test_exact_hermes_single_attempt_seam_never_replays_or_falls_back`.
- Native source inspection of the actually loaded maintained checkout (observed revision
  `9ceb0858abfd1d3c3b32bd6f76e98d14ed7a2fbd`) found the same
  `_send_telegram_message_with_retry(bot, *, attempts=3, **kwargs)` helper
  (`tools/send_message_tool.py:183`) and the same General-topic mapping
  (`plugins/platforms/telegram/adapter.py:1212`), so the pinned seam exists in both the
  selected release and the local transitional runtime; no Hermes file was modified.

No live model, Telegram transport, profile/job activation, source mutation, credential
operation, dependency/lockfile change, publication, push, PR, merge, or issue mutation was
run. The adapter's deterministic sender fakes are boundary tests, not live Telegram
qualification; AC-7 live qualification remains owned by MON-INT.

## Compatibility and residual risk

**Unit compatibility impact: `none`.** The delivery adapter is an additive monitor-owned
module and does not alter existing imports or Hermes behavior. It consumes the reviewed
MON-01 store leases/outbox and MON-03 rendered-part contract without changing either.

Residual risks, stated honestly:

- The one-attempt seam is a private (underscored) helper of the selected release. It is
  present identically in the selected release and in the local transitional runtime, and a
  runtime without it fails closed as `native-sender-unavailable`; the plan's capability
  preflight for the deployed runtime remains MON-05 work.
- The native helper cannot document whether a raised transport exception happened before
  or after dispatch, so the default adapter records such exceptions as `uncertain` and
  never replays them. Bounded retry therefore applies to sender results that explicitly
  mark a pre-dispatch failure (the adapter protocol); this intentionally favors D8's
  "no ambiguous automatic replay" over recovering a possibly-dispatched send.
- The `hermes_exact` probe skips when the release-locked checkout is unavailable
  (environment fact, matching the repository's existing convention); both lanes were
  exercised here and the test executed rather than skipped.

Remaining integrated risk is limited to MON-05 wiring the adapter into the exact Morfeo
runtime/`deliver=local` lifecycle and MON-INT's provisioned qualification. Independent
Supervisor review remains outstanding.
