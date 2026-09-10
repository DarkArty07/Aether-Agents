# MON-04 Implementation Evidence — native Telegram delivery

**Unit:** MON-04
**Task:** `t_a08bbd2b`
**Objective Contract:** `oc_f8c9fc9320587cf3@v1`
**Base commit:** `9d107f2ab89f38fb65e273fafef1a55a84437b74`
**Candidate implementation tree SHA (before evidence file):** `771d7606e338fd0a2ea381b25966aa8e717295f0`
**Status:** Implemented and self-verified; ready for same-card Supervisor review.

## Scope and changed paths

Only the assigned MON-04 paths are changed:

- `src/aether_agents/monitor/delivery.py`
- `tests/test_telegram_monitor_delivery.py`
- `specs/telegram-monitor/evidence/MON-04.md`

The new non-`specs/` path inventory for MON-06 is the delivery adapter and its focused
regression test. No store/model/reporting/source/runtime/CLI/plugin/profile/policy,
Objective Contract, source database, Hermes checkout, or live profile was modified.

## Implemented behavior

- Added one lazy `TelegramDeliveryAdapter` around the existing native Hermes standalone
  sender. The module imports no Hermes/gateway code at load time; the native boundary is
  resolved only when a real sender is needed.
- Inspected the selected exact Hermes source at revision
  `e624e9fde561e1add9388384012b295fde669ade` (`v2026.8.18`). The maintained sender is
  `tools/send_message_tool.py::_send_to_platform(platform, pconfig, chat_id, message,
  thread_id=None, ...)`, and its successful Telegram result contains an explicit
  `success` flag and `message_id`. The adapter uses that existing path and does not edit
  or copy Hermes.
- The adapter accepts only a pinned target whose opaque reference matches both the
  persisted monitor setting and the target's canonical chat/thread binding. Missing,
  changed, malformed, profile-mismatched, or unresolved targets fail closed before the
  sender is called. It never accepts an outbox/source recipient or fallback destination.
- Rendered parts are checked against the immutable store text hashes and sent in index
  order. Confirmed parts are skipped on restart; a confirmed native response must include
  a message ID. Timeout, empty, unknown-exception, post-dispatch, and unclassified native
  errors become durable `uncertain` outcomes and are never blindly replayed.
- Explicit pre-dispatch failures are retryable with bounded `retry_after` delay and no
  more than three attempts per part. Multipart delivery stops at the first non-confirmed
  part while preserving already-confirmed and failed/uncertain state for a later tick.
- Store delivery leases fence concurrent callers and are rechecked after claim so manual
  off suppresses a claimed part without invoking the sender. Coverage markers advance
  only after every delivery part is durably confirmed.
- Sender error text is reduced to a stable sanitized taxonomy; error messages, target
  values, credential-shaped text, paths, and raw sender exceptions are not persisted or
  returned in public adapter results.

## Requirement-to-evidence mapping

| Obligation | Check executed | Observed result |
| --- | --- | --- |
| Explicit accepted native receipt | `test_explicit_native_message_id_confirms_parts_in_order_and_advances_coverage`; `test_async_native_sender_is_lazy_and_explicit_ack_is_required` | Parts were invoked in order, message IDs were persisted, and coverage advanced only after all parts confirmed; async sender worked through the same seam. |
| Pre-dispatch retry and retry-after/max-three bound | `test_pre_dispatch_failure_honors_retry_after_and_never_exceeds_three_attempts`; `test_raised_pre_dispatch_error_is_retryable_but_unknown_exception_is_not` | Retry-after was honored; attempts were exactly bounded at three; unknown exceptions were not replayed. |
| Ambiguous outcomes are uncertain | `test_timeout_empty_and_post_dispatch_results_are_uncertain_without_retry`; `test_raised_pre_dispatch_error_is_retryable_but_unknown_exception_is_not`; `test_native_error_text_is_reduced_to_a_safe_taxonomy_token` | Timeout, empty, post-dispatch, unknown transport, and native unclassified error results were persisted as uncertain with no blind retry. |
| Multipart partial/restart semantics | `test_multipart_partial_failure_restart_skips_confirmed_part_and_coverage_waits` | Confirmed part was not resent; failed and pending parts remained durable; coverage advanced only on the later all-confirmed run. |
| Concurrent invocation and lease fencing | `test_concurrent_invocation_is_fenced_and_only_one_sender_runs` | One sender held the delivery lease; the concurrent invocation observed `delivery-lease-busy` and did not send. |
| Manual off before/after lease recheck | `test_manual_off_after_lease_recheck_suppresses_without_sender_call`; `test_off_before_send_persists_no_send_and_resumes_after_on` | Off-after-lease persisted suppression without a sender call; off-before-send preserved pending work and re-enabled delivery after on. |
| Exact pinned destination/no alternative | `test_missing_changed_or_ambiguous_destination_fails_closed_without_alternative` | Missing, changed, alternate-chat-with-same-pin, and profile-mismatched targets failed before sender invocation; no target value appeared in the result. |
| Immutable rendered parts and privacy | `test_rendered_part_hash_mismatch_and_canaries_never_reach_sender_or_receipt`; `test_native_error_text_is_reduced_to_a_safe_taxonomy_token` | Changed text was rejected before dispatch; seeded path/token/chat canaries were absent from returned and persisted error state. |
| Native cron is not a second send path | Source inspection of the exact Hermes sender and fixed `plan.md`/task decisions; adapter contains no cron registration or automatic delivery call | This unit only calls the selected native standalone sender on explicit adapter invocation; runtime/`deliver=local` wiring remains owned by MON-05. |

## Verification record

All commands were run in the assigned worktree with the locked `uv` environment.

- Focused MON-04 plus dependency regression suite:
  `uv run --frozen pytest -q tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py`
  → **96 passed in 2.30s**.
- Owned and relevant Ruff lint:
  `uv run --frozen ruff check src/aether_agents/monitor tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py`
  → **All checks passed**.
- Owned and relevant formatting:
  `uv run --frozen ruff format --check src/aether_agents/monitor tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py`
  → **8 files already formatted**.
- Owned type check:
  `uv run --frozen mypy src/aether_agents/monitor`
  → **Success: no issues found in 5 source files**; only the existing optional-module override note was emitted.
- Bytecode and whitespace checks:
  `uv run --frozen python -m compileall -q src/aether_agents/monitor tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_reporting.py && git diff --check`
  → **passed**.
- Exact native-source resolution probe:
  `PYTHONPATH=<exact Hermes checkout> uv run --frozen python -c ...`
  → **passed**; resolved `gateway/config.py` and `tools/send_message_tool.py` from the exact checkout, reported revision `e624e9fde561e1add9388384012b295fde669ade`, and inspected the `_send_to_platform` signature without invoking a sender or network.

No live model, Telegram transport, profile/job activation, source mutation, credential
operation, dependency/lockfile change, publication, push, PR, merge, or issue mutation was
run. The adapter's deterministic sender fakes are boundary tests, not live Telegram
qualification; AC-7 live qualification remains owned by MON-INT.

## Compatibility and residual risk

**Unit compatibility impact: `none`.** The delivery adapter is an additive monitor-owned
module and does not alter existing imports or Hermes behavior. It consumes the reviewed
MON-01 store leases/outbox and MON-03 rendered-part contract without changing either.

Remaining integrated risk is limited to MON-05 wiring the adapter into the exact Morfeo
runtime/`deliver=local` lifecycle and MON-INT's provisioned qualification. The native
sender's generic `{error: ...}` result cannot prove pre-dispatch failure, so the adapter
correctly treats that result as uncertain rather than retrying it; a future runtime change
would need an explicit pre-dispatch acknowledgment to enable retry for that path.
Independent Supervisor review and integrated qualification remain outstanding.
