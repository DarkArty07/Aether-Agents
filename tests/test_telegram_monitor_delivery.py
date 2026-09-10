from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import pytest

from aether_agents.monitor.delivery import (
    DeliveryOutcome,
    PinnedTelegramTarget,
    PreDispatchError,
    TelegramDeliveryAdapter,
    canonical_target_reference,
)
from aether_agents.monitor.models import DeliveryState, WorkItem
from aether_agents.monitor.store import MonitorStore

UTC = timezone.utc
TARGET_CHAT = "configured-chat"
TARGET_THREAD = "configured-thread"
TARGET_REF = canonical_target_reference(TARGET_CHAT, TARGET_THREAD)


def _clock(value: datetime):
    current = value

    def now() -> datetime:
        return current

    return now


def _seed_report(
    tmp_path: Path, *, parts: list[str], enabled: bool = True
) -> tuple[MonitorStore, str]:
    store = MonitorStore(
        state_root=tmp_path / "state",
        clock=_clock(datetime(2026, 9, 10, 12, tzinfo=UTC)),
    )
    store.configure(
        native_job_id="owned-job",
        profile_binding="morfeo-profile",
        destination_ref=TARGET_REF,
    )
    store.set_enabled(enabled)
    cutoff = "2026-09-10T12:00:00.000000Z"
    lease = store.acquire_collection_lease(cutoff, owner_id="collector")
    assert lease is not None
    snapshot = store.create_snapshot(
        cutoff_utc=cutoff,
        previous_cutoff_utc=None,
        collected_at_utc=cutoff,
        watermarks={"project": "cursor"},
        payload={
            "schema_version": "aether.telegram-monitor.snapshot.v1",
            "report_id": "report-delivery",
            "cutoff_utc": cutoff,
            "items": [{"work_key": "work-one", "observed_state": "running"}],
        },
        coverage_gaps=(),
        report_id="report-delivery",
        lease=lease,
    )
    assert snapshot.report_id == "report-delivery"
    store.enqueue_deliveries(snapshot.report_id, parts)
    return store, snapshot.report_id


def _resolver(settings):
    assert settings.destination_ref == TARGET_REF
    return PinnedTelegramTarget(
        reference=TARGET_REF,
        chat_id=TARGET_CHAT,
        thread_id=TARGET_THREAD,
        profile_binding="morfeo-profile",
    )


def _adapter(store: MonitorStore, sender, **kwargs) -> TelegramDeliveryAdapter:
    return TelegramDeliveryAdapter(
        store,
        sender=sender,
        target_resolver=_resolver,
        sleep=kwargs.pop("sleep", lambda _delay: None),
        **kwargs,
    )


def test_explicit_native_message_id_confirms_parts_in_order_and_advances_coverage(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["part one", "part two"])
    store.upsert_work_item(
        WorkItem(
            work_key="work-one",
            project_id="project-one",
            origin_session_id="session-one",
            origin_session_title="Origin",
            first_seen_utc="2026-09-10T11:00:00Z",
            observed_state="completed",
            active=False,
        )
    )
    calls: list[tuple[str, str | None, str]] = []

    def sender(target: PinnedTelegramTarget, text: str):
        calls.append((target.chat_id, target.thread_id, text))
        return {"success": True, "message_id": f"msg-{len(calls)}"}

    result = _adapter(store, sender).deliver_report(
        report_id,
        ["part one", "part two"],
        coverage_markers={"work-one": report_id},
    )

    assert result.outcome is DeliveryOutcome.CONFIRMED
    assert result.coverage_advanced is True
    assert list(result.parts) == [
        {"outcome": "confirmed", "message_id": "msg-1"},
        {"outcome": "confirmed", "message_id": "msg-2"},
    ]
    assert calls == [
        (TARGET_CHAT, TARGET_THREAD, "part one"),
        (TARGET_CHAT, TARGET_THREAD, "part two"),
    ]
    assert store.get_work_item("work-one").final_outcome_delivery_marker == report_id  # type: ignore[union-attr]
    assert all(item.state is DeliveryState.CONFIRMED for item in store.list_deliveries(report_id))


def test_pre_dispatch_failure_honors_retry_after_and_never_exceeds_three_attempts(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["retry me"])
    responses = iter(
        [
            {"outcome": "failed", "error_class": "rate-limit", "retry_after": 7},
            {"success": True, "message_id": "accepted-1"},
        ]
    )
    calls: list[str] = []
    delays: list[float] = []

    def sender(_target: PinnedTelegramTarget, text: str):
        calls.append(text)
        return next(responses)

    result = _adapter(store, sender, sleep=delays.append).deliver_report(report_id, ["retry me"])

    assert result.outcome is DeliveryOutcome.CONFIRMED
    assert calls == ["retry me", "retry me"]
    assert delays == [7.0]
    assert store.get_delivery(report_id, 0).attempts == 2  # type: ignore[union-attr]

    store2, report2 = _seed_report(tmp_path / "max", parts=["never accepted"])
    attempts: list[str] = []

    def always_fails(_target: PinnedTelegramTarget, text: str):
        attempts.append(text)
        return {"outcome": "failed", "error_class": "temporary", "retry_after": 0}

    exhausted = _adapter(store2, always_fails).deliver_report(report2, ["never accepted"])
    assert exhausted.outcome is DeliveryOutcome.FAILED
    assert exhausted.parts == ({"outcome": "failed", "error_class": "temporary"},)
    assert len(attempts) == 3
    assert store2.get_delivery(report2, 0).attempts == 3  # type: ignore[union-attr]


def test_timeout_empty_and_post_dispatch_results_are_uncertain_without_retry(
    tmp_path: Path,
) -> None:
    cases = [
        (None, "sender-empty-result"),
        ({"outcome": "uncertain", "error_class": "timeout"}, "timeout"),
        (
            {"outcome": "failed", "dispatch": "after", "error_class": "network"},
            "dispatch-uncertain",
        ),
    ]
    for index, (response, error_class) in enumerate(cases):
        store, report_id = _seed_report(tmp_path / str(index), parts=["ambiguous"])
        calls: list[str] = []

        def sender(_target: PinnedTelegramTarget, text: str):
            calls.append(text)
            return response

        result = _adapter(store, sender).deliver_report(report_id, ["ambiguous"])
        assert result.outcome is DeliveryOutcome.UNCERTAIN
        assert result.parts == ({"outcome": "uncertain", "error_class": error_class},)
        assert len(calls) == 1
        assert store.get_delivery(report_id, 0).state is DeliveryState.UNCERTAIN  # type: ignore[union-attr]


def test_native_error_text_is_reduced_to_a_safe_taxonomy_token(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["redact error"])

    def sender(_target: PinnedTelegramTarget, _text: str):
        return {
            "error": "HTTP 400 for chat_id=-100123456789 token=BOT_SECRET /private/path",
        }

    result = _adapter(store, sender).deliver_report(report_id, ["redact error"])

    assert result.outcome is DeliveryOutcome.UNCERTAIN
    assert result.parts == ({"outcome": "uncertain", "error_class": "dispatch-uncertain"},)
    assert "-100123456789" not in repr(result)
    assert "BOT_SECRET" not in repr(result)
    assert "/private/path" not in repr(result)
    persisted = store.get_delivery(report_id, 0)
    assert persisted is not None
    assert persisted.last_error_class == "dispatch-uncertain"
    assert persisted.last_error_message is None


def test_raised_pre_dispatch_error_is_retryable_but_unknown_exception_is_not(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["known failure"])
    attempts = 0

    def sender(_target: PinnedTelegramTarget, _text: str):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PreDispatchError("service-busy", retry_after=2)
        return {"success": True, "message_id": "accepted"}

    delays: list[float] = []
    result = _adapter(store, sender, sleep=delays.append).deliver_report(
        report_id, ["known failure"]
    )
    assert result.outcome is DeliveryOutcome.CONFIRMED
    assert attempts == 2
    assert delays == [2.0]

    store2, report2 = _seed_report(tmp_path / "unknown", parts=["maybe sent"])

    def unknown_failure(_target: PinnedTelegramTarget, _text: str):
        raise RuntimeError("transport stopped after possible dispatch")

    uncertain = _adapter(store2, unknown_failure).deliver_report(report2, ["maybe sent"])
    assert uncertain.outcome is DeliveryOutcome.UNCERTAIN
    assert uncertain.parts == ({"outcome": "uncertain", "error_class": "dispatch-uncertain"},)
    assert store2.get_delivery(report2, 0).attempts == 1  # type: ignore[union-attr]


def test_multipart_partial_failure_restart_skips_confirmed_part_and_coverage_waits(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["first", "second", "third"])
    store.upsert_work_item(
        WorkItem(
            work_key="work-one",
            project_id="project-one",
            origin_session_id="session-one",
            origin_session_title="Origin",
            first_seen_utc="2026-09-10T11:00:00Z",
            observed_state="completed",
            active=False,
        )
    )
    first_calls: list[str] = []

    def first_tick(_target: PinnedTelegramTarget, text: str):
        first_calls.append(text)
        if text == "first":
            return {"success": True, "message_id": "first-id"}
        return {"outcome": "failed", "error_class": "pre-dispatch", "retry_after": 0}

    first = _adapter(store, first_tick).deliver_report(
        report_id,
        ["first", "second", "third"],
        coverage_markers={"work-one": report_id},
    )
    assert first.outcome is DeliveryOutcome.PARTIAL
    assert first.coverage_advanced is False
    assert first_calls == ["first", "second", "second", "second"]
    assert [item.state for item in store.list_deliveries(report_id)] == [
        DeliveryState.CONFIRMED,
        DeliveryState.FAILED,
        DeliveryState.PENDING,
    ]

    restarted_calls: list[str] = []

    def restarted(_target: PinnedTelegramTarget, text: str):
        restarted_calls.append(text)
        return {"success": True, "message_id": f"restart-{text}"}

    second = _adapter(store, restarted).deliver_report(
        report_id,
        ["first", "second", "third"],
        coverage_markers={"work-one": report_id},
    )
    assert second.outcome is DeliveryOutcome.CONFIRMED
    assert second.coverage_advanced is True
    assert restarted_calls == ["second", "third"]
    assert store.get_work_item("work-one").final_outcome_delivery_marker == report_id  # type: ignore[union-attr]


def test_concurrent_invocation_is_fenced_and_only_one_sender_runs(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["one"])
    entered = Event()
    release = Event()
    calls: list[str] = []

    def slow_sender(_target: PinnedTelegramTarget, text: str):
        calls.append(text)
        entered.set()
        assert release.wait(2)
        return {"success": True, "message_id": "one-id"}

    adapter_a = _adapter(store, slow_sender, owner_id="sender-a")
    adapter_b = _adapter(store, slow_sender, owner_id="sender-b")
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(adapter_a.deliver_report, report_id, ["one"])
        assert entered.wait(2)
        result_b = adapter_b.deliver_report(report_id, ["one"])
        release.set()
        result_a = future_a.result(timeout=2)

    assert result_b.outcome is DeliveryOutcome.FAILED
    assert result_b.parts == ({"outcome": "failed", "error_class": "delivery-lease-busy"},)
    assert result_a.outcome is DeliveryOutcome.CONFIRMED
    assert calls == ["one"]


def test_manual_off_after_lease_recheck_suppresses_without_sender_call(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["do not send"])
    called = False
    original = store.can_dispatch_delivery

    def turn_off_before_recheck(lease):
        store.set_enabled(False)
        return original(lease)

    store.can_dispatch_delivery = turn_off_before_recheck  # type: ignore[method-assign]

    def sender(_target: PinnedTelegramTarget, _text: str):
        nonlocal called
        called = True
        return {"success": True, "message_id": "must-not-exist"}

    result = _adapter(store, sender).deliver_report(report_id, ["do not send"])
    assert result.outcome is DeliveryOutcome.SUPPRESSED
    assert result.parts == ({"outcome": "suppressed", "error_class": "monitor-disabled"},)
    assert called is False
    assert store.get_delivery(report_id, 0).state is DeliveryState.SUPPRESSED  # type: ignore[union-attr]


def test_off_before_send_persists_no_send_and_resumes_after_on(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["pending"])
    store.set_enabled(False)
    called: list[str] = []

    def sender(_target: PinnedTelegramTarget, text: str):
        called.append(text)
        return {"success": True, "message_id": "later"}

    suppressed = _adapter(store, sender).deliver_report(report_id, ["pending"])
    assert suppressed.outcome is DeliveryOutcome.SUPPRESSED
    assert called == []
    assert store.get_delivery(report_id, 0).state is DeliveryState.PENDING  # type: ignore[union-attr]

    store.set_enabled(True)
    resumed = _adapter(store, sender).deliver_report(report_id, ["pending"])
    assert resumed.outcome is DeliveryOutcome.CONFIRMED
    assert called == ["pending"]


@pytest.mark.parametrize(
    ("resolver", "error"),
    [
        (lambda _settings: None, "destination-missing"),
        (
            lambda _settings: PinnedTelegramTarget("different-pin", TARGET_CHAT, TARGET_THREAD),
            "destination-changed",
        ),
        (
            lambda _settings: PinnedTelegramTarget(TARGET_REF, "another-chat", TARGET_THREAD),
            "destination-changed",
        ),
        (
            lambda _settings: PinnedTelegramTarget(
                TARGET_REF, TARGET_CHAT, TARGET_THREAD, "other-profile"
            ),
            "profile-binding-changed",
        ),
    ],
)
def test_missing_changed_or_ambiguous_destination_fails_closed_without_alternative(
    tmp_path: Path,
    resolver,
    error: str,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["private report"])
    called = False

    def sender(_target: PinnedTelegramTarget, _text: str):
        nonlocal called
        called = True
        return {"success": True, "message_id": "wrong"}

    adapter = TelegramDeliveryAdapter(
        store,
        sender=sender,
        target_resolver=resolver,
        sleep=lambda _delay: None,
    )
    result = adapter.deliver_report(report_id, ["private report"])
    assert result.outcome is DeliveryOutcome.FAILED
    assert result.error_class == error
    assert result.parts == ()
    assert called is False
    assert TARGET_CHAT not in repr(result)
    assert TARGET_THREAD not in repr(result)


def test_rendered_part_hash_mismatch_and_canaries_never_reach_sender_or_receipt(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["safe rendered text"])
    called = False

    def sender(_target: PinnedTelegramTarget, _text: str):
        nonlocal called
        called = True
        return {"success": True, "message_id": "unexpected"}

    result = _adapter(store, sender).deliver_report(
        report_id,
        ["safe rendered text with SECRET_CANARY /private/path and token=abc"],
    )
    assert result.outcome is DeliveryOutcome.FAILED
    assert result.error_class == "outbox-text-changed"
    assert called is False
    assert "SECRET_CANARY" not in repr(result)
    assert "/private/path" not in repr(result)
    assert store.get_delivery(report_id, 0).state is DeliveryState.PENDING  # type: ignore[union-attr]


def test_async_native_sender_is_lazy_and_explicit_ack_is_required(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["async part"])
    imported = False
    calls: list[tuple[str, str | None, str]] = []

    async def sender(target: PinnedTelegramTarget, text: str):
        calls.append((target.chat_id, target.thread_id, text))
        await asyncio.sleep(0)
        return {"success": True, "message_id": 42}

    result = asyncio.run(_adapter(store, sender).deliver_report_async(report_id, ["async part"]))
    assert result.outcome is DeliveryOutcome.CONFIRMED
    assert calls == [(TARGET_CHAT, TARGET_THREAD, "async part")]
    assert imported is False
