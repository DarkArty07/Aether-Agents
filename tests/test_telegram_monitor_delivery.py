from __future__ import annotations

import asyncio
import inspect
import os
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

import aether_agents.monitor.delivery as delivery_module
from aether_agents.lifecycle import HERMES_BASELINE, verify_clean_checkout
from aether_agents.monitor.delivery import (
    DeliveryConfigurationError,
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


def _durable_bytes(db_path: Path) -> bytes:
    """Read every durable SQLite file so a persisted canary cannot hide in the WAL."""

    return b"".join(
        part.read_bytes()
        for part in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm"))
        if part.exists()
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


def _install_fake_native_telegram(
    monkeypatch: pytest.MonkeyPatch,
    *,
    normalize=lambda value: value,  # noqa: ANN001 - test double
    proxy: str | None = None,
    request_factory: object | None = None,
) -> tuple[list[dict[str, object]], list[int], list[object]]:
    """Install a deterministic stand-in for the native Hermes Telegram seam.

    Returns the recorded Bot send kwargs, the explicit attempt counts the seam received,
    and the constructed Bot objects.  No native module and no network is touched.
    """

    bot_calls: list[dict[str, object]] = []
    attempt_counts: list[int] = []
    bots: list[object] = []

    class FakeBot:
        def __init__(self, token: str, **options: object) -> None:
            self.token = token
            self.options = options
            bots.append(self)

        async def send_message(self, **kwargs: object) -> object:
            bot_calls.append(kwargs)
            return SimpleNamespace(message_id=321)

    class FakeHTTPXRequest:
        def __init__(self, **options: object) -> None:
            self.options = options

    async def one_shot(bot: FakeBot, *, attempts: int = 3, **kwargs: object) -> object:
        attempt_counts.append(attempts)
        return await bot.send_message(**kwargs)

    def package(name: str) -> types.ModuleType:
        module = types.ModuleType(name)
        module.__path__ = []  # type: ignore[attr-defined]
        return module

    telegram_module = types.ModuleType("telegram")
    telegram_module.Bot = FakeBot  # type: ignore[attr-defined]
    request_module = types.ModuleType("telegram.request")
    request_module.HTTPXRequest = request_factory or FakeHTTPXRequest  # type: ignore[attr-defined]

    ids_module = types.ModuleType("plugins.platforms.telegram.telegram_ids")
    ids_module.normalize_telegram_chat_id = normalize  # type: ignore[attr-defined]

    sender_module = types.ModuleType("tools.send_message_tool")
    sender_module._send_telegram_message_with_retry = one_shot  # type: ignore[attr-defined]

    gateway = package("gateway")
    gateway_platforms = package("gateway.platforms")
    gateway_base = types.ModuleType("gateway.platforms.base")
    gateway_base.resolve_proxy_url = lambda *_args, **_kwargs: proxy  # type: ignore[attr-defined]
    gateway.platforms = gateway_platforms  # type: ignore[attr-defined]
    gateway_platforms.base = gateway_base  # type: ignore[attr-defined]

    plugins = package("plugins")
    platforms = package("plugins.platforms")
    telegram_plugins = package("plugins.platforms.telegram")
    plugins.platforms = platforms  # type: ignore[attr-defined]
    platforms.telegram = telegram_plugins  # type: ignore[attr-defined]
    telegram_plugins.telegram_ids = ids_module  # type: ignore[attr-defined]

    tools = package("tools")
    tools.send_message_tool = sender_module  # type: ignore[attr-defined]

    for name, module in {
        "telegram": telegram_module,
        "telegram.request": request_module,
        "gateway": gateway,
        "gateway.platforms": gateway_platforms,
        "gateway.platforms.base": gateway_base,
        "plugins": plugins,
        "plugins.platforms": platforms,
        "plugins.platforms.telegram": telegram_plugins,
        "plugins.platforms.telegram.telegram_ids": ids_module,
        "tools": tools,
        "tools.send_message_tool": sender_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    return bot_calls, attempt_counts, bots


def test_native_seam_uses_one_exact_bot_attempt_and_preserves_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, attempt_counts, _bots = _install_fake_native_telegram(
        monkeypatch, normalize=lambda _value: 123
    )

    result = asyncio.run(
        delivery_module._send_exact_native_telegram(
            SimpleNamespace(token="BOT_SECRET_TOKEN"),
            PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, "42"),
            "one exact part",
        )
    )

    assert result == {"success": True, "message_id": 321}
    assert attempt_counts == [1]
    assert calls == [{"chat_id": 123, "text": "one exact part", "message_thread_id": 42}]
    assert "BOT_SECRET_TOKEN" not in repr(result)


def test_native_seam_keeps_the_exact_thread_maps_general_topic_and_uses_configured_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, attempt_counts, bots = _install_fake_native_telegram(
        monkeypatch, proxy="http://proxy.invalid:3128"
    )

    general = asyncio.run(
        delivery_module._send_exact_native_telegram(
            SimpleNamespace(token="token"),
            PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, "1"),
            "general topic part",
        )
    )
    assert general == {"success": True, "message_id": 321}
    assert calls[-1] == {"chat_id": TARGET_CHAT, "text": "general topic part"}

    assert bots[-1].options.keys() == {"request", "get_updates_request"}  # type: ignore[attr-defined]
    assert bots[-1].options["request"].options == {  # type: ignore[attr-defined]
        "proxy": "http://proxy.invalid:3128"
    }

    threaded = asyncio.run(
        delivery_module._send_exact_native_telegram(
            SimpleNamespace(token="token"),
            PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, "7"),
            "threaded part",
        )
    )
    assert threaded == {"success": True, "message_id": 321}
    assert calls[-1]["message_thread_id"] == 7
    assert attempt_counts == [1, 1]

    for invalid_thread in ("not-a-thread", "0", ""):
        with pytest.raises(DeliveryConfigurationError):
            asyncio.run(
                delivery_module._send_exact_native_telegram(
                    SimpleNamespace(token="token"),
                    PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, invalid_thread),
                    "invalid thread part",
                )
            )

    # A broken proxy helper falls back to the same direct Bot, never another recipient.
    broken_calls, _, broken_bots = _install_fake_native_telegram(
        monkeypatch,
        proxy="http://proxy.invalid:3128",
        request_factory=lambda **_options: (_ for _ in ()).throw(RuntimeError("no httpx")),
    )
    direct = asyncio.run(
        delivery_module._send_exact_native_telegram(
            SimpleNamespace(token="token"),
            PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, "42"),
            "direct part",
        )
    )
    assert direct == {"success": True, "message_id": 321}
    assert broken_bots[-1].options == {}  # type: ignore[attr-defined]
    assert broken_calls[-1]["message_thread_id"] == 42


def _resolve_exact_hermes_checkout() -> Path:
    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
    if configured:
        return Path(configured).expanduser()
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "aether-agents" / "hermes" / HERMES_BASELINE.tag


@pytest.mark.hermes_exact
def test_exact_hermes_single_attempt_seam_never_replays_or_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Probe the release-locked Hermes helper the adapter pins to exactly one attempt."""

    checkout = _resolve_exact_hermes_checkout()
    if not checkout.exists():
        pytest.skip(f"exact Hermes checkout unavailable at {checkout}")
    verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    monkeypatch.syspath_prepend(str(checkout))
    native = pytest.importorskip("tools.send_message_tool")
    assert Path(native.__file__).resolve().is_relative_to(checkout.resolve())
    assert (
        inspect.signature(native._send_telegram_message_with_retry).parameters["attempts"].default
        == 3
    )

    class FakeBot:
        def __init__(self, error: Exception | None = None) -> None:
            self.error = error
            self.calls: list[dict[str, object]] = []

        async def send_message(self, **kwargs: object) -> object:
            self.calls.append(kwargs)
            if self.error is not None and len(self.calls) == 1:
                raise self.error
            return SimpleNamespace(message_id=321)

    def send(bot: FakeBot, **kwargs: object) -> object:
        return asyncio.run(native._send_telegram_message_with_retry(bot, attempts=1, **kwargs))

    accepted = FakeBot()
    message = send(accepted, chat_id=123, text="part", message_thread_id=42)
    assert getattr(message, "message_id", None) == 321
    assert accepted.calls == [{"chat_id": 123, "text": "part", "message_thread_id": 42}]

    for error in (
        Exception("Bad Request: Message thread not found"),
        Exception("503 Service Unavailable"),
        TimeoutError("request timed out"),
    ):
        bot = FakeBot(error=error)
        with pytest.raises(type(error)):
            send(bot, chat_id=123, text="part", message_thread_id=42)
        assert len(bot.calls) == 1
        assert bot.calls[0]["message_thread_id"] == 42

    # The native default (three attempts) replays a possibly dispatched 503 internally,
    # which is exactly why the adapter passes ``attempts=1`` and owns retry accounting.
    slept: list[float] = []

    class FakeAsyncIO:
        @staticmethod
        async def sleep(delay: float) -> None:
            slept.append(delay)

    monkeypatch.setattr(native, "asyncio", FakeAsyncIO())
    replayed = FakeBot(error=Exception("503 Service Unavailable"))
    recovered = asyncio.run(
        native._send_telegram_message_with_retry(
            replayed, chat_id=123, text="part", message_thread_id=42
        )
    )
    assert recovered.message_id == 321  # type: ignore[attr-defined]
    assert len(replayed.calls) == 2
    assert slept == [1.0]


def test_target_is_reresolved_between_multipart_parts_and_stale_pin_fails_closed(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["first", "second"])
    changed_ref = canonical_target_reference("changed-chat", "changed-thread")
    current_target = [PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, TARGET_THREAD)]
    sent: list[tuple[str, str | None, str]] = []

    def resolver(_settings):
        return current_target[0]

    def sender(target: PinnedTelegramTarget, text: str):
        sent.append((target.chat_id, target.thread_id, text))
        if text == "first":
            current_target[0] = PinnedTelegramTarget(changed_ref, "changed-chat", "changed-thread")
        return {"success": True, "message_id": "first-id"}

    adapter = TelegramDeliveryAdapter(
        store,
        sender=sender,
        target_resolver=resolver,
        sleep=lambda _delay: None,
    )
    result = adapter.deliver_report(report_id, ["first", "second"])

    assert result.outcome is DeliveryOutcome.PARTIAL
    assert result.parts == (
        {"outcome": "confirmed", "message_id": "first-id"},
        {"outcome": "failed", "error_class": "destination-changed"},
    )
    assert sent == [(TARGET_CHAT, TARGET_THREAD, "first")]
    assert store.get_delivery(report_id, 1).state is DeliveryState.FAILED  # type: ignore[union-attr]


def test_profile_binding_change_between_parts_fails_closed_without_send(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["first", "second"])
    sent: list[str] = []

    def sender(_target: PinnedTelegramTarget, text: str):
        sent.append(text)
        store.configure(
            native_job_id="owned-job",
            profile_binding="other-profile",
            destination_ref=TARGET_REF,
        )
        return {"success": True, "message_id": "first-id"}

    result = _adapter(store, sender).deliver_report(report_id, ["first", "second"])

    assert result.outcome is DeliveryOutcome.PARTIAL
    assert result.parts == (
        {"outcome": "confirmed", "message_id": "first-id"},
        {"outcome": "failed", "error_class": "profile-binding-changed"},
    )
    assert sent == ["first"]
    assert store.get_delivery(report_id, 1).state is DeliveryState.FAILED  # type: ignore[union-attr]


def test_target_is_reresolved_after_retry_delay_before_replay(tmp_path: Path) -> None:
    store, report_id = _seed_report(tmp_path, parts=["retry once"])
    changed_ref = canonical_target_reference("changed-chat", "changed-thread")
    current_target = [PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, TARGET_THREAD)]
    sent: list[str] = []
    delays: list[float] = []

    def resolver(_settings):
        return current_target[0]

    def sender(_target: PinnedTelegramTarget, text: str):
        sent.append(text)
        return {"outcome": "failed", "error_class": "rate-limit", "retry_after": 4}

    def sleep(delay: float) -> None:
        delays.append(delay)
        current_target[0] = PinnedTelegramTarget(changed_ref, "changed-chat", "changed-thread")

    adapter = TelegramDeliveryAdapter(
        store,
        sender=sender,
        target_resolver=resolver,
        sleep=sleep,
    )
    result = adapter.deliver_report(report_id, ["retry once"])

    assert result.outcome is DeliveryOutcome.FAILED
    assert result.parts == ({"outcome": "failed", "error_class": "destination-changed"},)
    assert sent == ["retry once"]
    assert delays == [4.0]
    assert store.get_delivery(report_id, 0).attempts == 2  # type: ignore[union-attr]


def test_foreign_error_classes_and_configuration_exceptions_use_closed_taxonomy(
    tmp_path: Path,
) -> None:
    store, report_id = _seed_report(tmp_path, parts=["foreign result"])

    def foreign_result(_target: PinnedTelegramTarget, _text: str):
        return {
            "outcome": "failed",
            "dispatch": "before",
            "error_class": "BOT_SECRET_TOKEN /private/credential",
        }

    result = _adapter(store, foreign_result, max_attempts=1).deliver_report(
        report_id, ["foreign result"]
    )
    assert result.parts == ({"outcome": "failed", "error_class": "sender-failure"},)
    assert "BOT_SECRET_TOKEN" not in repr(result)
    assert "/private/credential" not in repr(result)
    assert store.get_delivery(report_id, 0).last_error_class == "sender-failure"  # type: ignore[union-attr]
    durable = _durable_bytes(store.db_path)
    assert b"BOT_SECRET_TOKEN" not in durable
    assert b"/private/credential" not in durable

    store2, report2 = _seed_report(tmp_path / "exception", parts=["foreign exception"])

    def foreign_exception(_target: PinnedTelegramTarget, _text: str):
        raise DeliveryConfigurationError("CONFIG_SECRET_TOKEN")

    result2 = _adapter(store2, foreign_exception, max_attempts=1).deliver_report(
        report2, ["foreign exception"]
    )
    assert result2.parts == ({"outcome": "failed", "error_class": "destination-unavailable"},)
    assert "CONFIG_SECRET_TOKEN" not in repr(result2)
    assert store2.get_delivery(report2, 0).last_error_class == "destination-unavailable"  # type: ignore[union-attr]
    assert b"CONFIG_SECRET_TOKEN" not in _durable_bytes(store2.db_path)
