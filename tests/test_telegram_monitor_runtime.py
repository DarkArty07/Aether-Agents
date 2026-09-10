"""Native runtime, wake gate, hooks and controls for the Telegram monitor (MON-05).

Every test runs against disposable monitor state, disposable Hermes homes and fake
native runtimes/transport.  No live profile, job, model or Telegram destination is
touched.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from aether_agents.monitor import reporting
from aether_agents.monitor import runtime as runtime_module
from aether_agents.monitor.delivery import (
    PinnedTelegramTarget,
    PreDispatchError,
    TelegramDeliveryAdapter,
    canonical_target_reference,
)
from aether_agents.monitor.models import WorkItem
from aether_agents.monitor.runtime import (
    NARRATION_LEASE_TTL_SECONDS,
    configured_owner_language,
    handle_post_llm_call,
    handle_post_tool_call,
    handle_session_end,
    handle_session_end_direct,
    load_direct_records,
    reporter_context,
    run_precheck,
    service_hour_boundary,
)
from aether_agents.monitor.service import MonitorActionError, MonitorService, next_hour_boundary
from aether_agents.monitor.store import MonitorStore
from aether_agents.observation.context import ProjectRegistry

UTC = timezone.utc
JOB_ID = "job-monitor-1"
PROFILE = "morfeo"
TARGET_CHAT = "configured-chat"
TARGET_THREAD = "configured-thread"
TARGET_REF = canonical_target_reference(TARGET_CHAT, TARGET_THREAD)
ANCHOR = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
PROJECT_ID = "11111111-1111-4111-8111-111111111111"
NATIVE_PROJECT_ID = "native-project-1"
SESSION_ID = "session-alpha"


# ---------------------------------------------------------------------------
# Fixtures and fakes
# ---------------------------------------------------------------------------


def _clock(value: datetime):
    current = value

    def now() -> datetime:
        return current

    return now


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _fact(
    ref: str, text: str, *, provenance: str = "observed", status: str = "verified"
) -> dict[str, Any]:
    return {"ref": ref, "text": text, "provenance": provenance, "status": status}


def _item(
    work_key: str = "work_alpha",
    *,
    state: str = "in_progress",
    project_id: str = "project-alpha",
    session_id: str = "session-origin",
) -> dict[str, Any]:
    return {
        "work_key": work_key,
        "project": {"id": project_id, "name": "Aether demo"},
        "origin_session": {"id": session_id, "title": "Origin session"},
        "contract": None,
        "observed_state": state,
        "state_evidence_refs": [f"{work_key}_state"],
        "resolved": [_fact(f"{work_key}_resolved", "The focused unit was verified.")],
        "current": [_fact(f"{work_key}_current", "The unit is being reviewed.")],
        "next": [
            _fact(
                f"{work_key}_next",
                "The next gate is independent review.",
                provenance="reported",
                status="unverified",
            )
        ],
        "complications": [],
        "pending": [_fact(f"{work_key}_pending", "Evidence remains pending.", status="unknown")],
        "coverage_gaps": [],
        "started_at_utc": "2026-09-10T11:10:00Z",
    }


def _payload(
    report_id: str, cutoff: datetime, *, items: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "schema_version": reporting.SNAPSHOT_SCHEMA_VERSION,
        "report_id": report_id,
        "cutoff_utc": _stamp(cutoff),
        "collected_at_utc": _stamp(cutoff + timedelta(minutes=1)),
        "previous_cutoff_utc": _stamp(cutoff - timedelta(hours=1)),
        "items": [_item()] if items is None else items,
        "coverage_gaps": [],
    }


def _narrative(report_id: str, work_key: str = "work_alpha", *, status: str = "in_progress"):
    return {
        "schema_version": reporting.NARRATIVE_SCHEMA_VERSION,
        "report_id": report_id,
        "items": [
            {
                "work_key": work_key,
                "resolved": [
                    {"ref": f"{work_key}_resolved", "text": "The focused unit was verified."}
                ],
                "current": [{"ref": f"{work_key}_current", "text": "The unit is being reviewed."}],
                "next": [
                    {"ref": f"{work_key}_next", "text": "The next gate is independent review."}
                ],
                "complications": [],
                "pending": [{"ref": f"{work_key}_pending", "text": "Evidence remains pending."}],
                "status": status,
            }
        ],
    }


_STORE_CLOCK = _clock(ANCHOR)


@pytest.fixture(autouse=True)
def _native_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep deterministic tests independent of the host's Hermes installation.

    The imported-runtime interface preflight has its own release-locked regression in
    ``test_telegram_monitor_cli_plugin.py``; here it is stubbed so the wake-gate
    behavior itself is what is exercised.
    """

    monkeypatch.setattr(runtime_module, "_module_problems", lambda: [])


def _store(
    tmp_path: Path, *, clock: Any | None = None, configured: bool = True, enabled: bool = True
) -> MonitorStore:
    store = MonitorStore(state_root=tmp_path / "state", clock=clock or _STORE_CLOCK)
    if configured:
        store.configure(
            native_job_id=JOB_ID,
            profile_binding=PROFILE,
            destination_ref=TARGET_REF,
            timezone_name="UTC",
        )
    if enabled:
        store.set_enabled(True)
    return store


def _seed_report(
    store: MonitorStore,
    *,
    report_id: str = "report-alpha",
    cutoff: datetime | None = None,
    items: list[dict[str, Any]] | None = None,
    resolved: bool = False,
    narrative_status: str | None = None,
    narrator_session_id: str | None = None,
    structured: Mapping[str, Any] | None = None,
):
    cutoff = cutoff or ANCHOR
    payload = _payload(report_id, cutoff, items=items)
    for item in payload["items"]:
        store.upsert_work_item(
            WorkItem(
                work_key=item["work_key"],
                project_id=item["project"]["id"],
                project_name=item["project"]["name"],
                origin_session_id=item["origin_session"]["id"],
                origin_session_title=item["origin_session"]["title"],
                first_seen_utc=_stamp(cutoff - timedelta(hours=2)),
                started_at_utc=item.get("started_at_utc"),
                observed_state=item["observed_state"],
                source_cursor={"work": item["work_key"]},
                active=item["observed_state"] not in {"completed", "failed"},
                last_seen_utc=_stamp(cutoff),
            )
        )
    lease = store.acquire_collection_lease(cutoff, owner_id="collector")
    assert lease is not None
    snapshot = store.create_snapshot(
        report_id=report_id,
        cutoff_utc=cutoff,
        previous_cutoff_utc=cutoff - timedelta(hours=1),
        collected_at_utc=cutoff + timedelta(minutes=1),
        watermarks={"sessions": {}},
        payload=payload,
        coverage_gaps=(),
        lease=lease,
    )
    store.set_last_cutoff(cutoff)
    if narrative_status is not None:
        store.put_narrative(
            report_id,
            structured_result=structured,
            narrator_session_id=narrator_session_id,
            attempt_status=narrative_status,
        )
    if resolved:
        store.mark_snapshot_resolved(report_id)
    return snapshot


def _hold_narration_lease(store: MonitorStore, cutoff: datetime | None = None):
    """Simulate the pre-check's pending-narration lease for a reporter session."""

    lease = store.acquire_collection_lease(
        cutoff or ANCHOR,
        owner_id=runtime_module._narration_owner(JOB_ID),
        ttl_seconds=NARRATION_LEASE_TTL_SECONDS,
    )
    assert lease is not None
    return lease


class _FakeCollector:
    """Deterministic collector that persists one real snapshot in the store."""

    def __init__(
        self,
        store: MonitorStore,
        *,
        items: list[dict[str, Any]] | None = None,
        idle: bool = False,
        error: BaseException | None = None,
        in_progress: bool = False,
    ) -> None:
        self.store = store
        self.items = items
        self.idle = idle
        self.error = error
        self.in_progress = in_progress
        self.calls: list[datetime] = []

    def collect(self, *, cutoff_utc: datetime, direct_records=()):
        self.calls.append(cutoff_utc)
        if self.error is not None:
            raise self.error
        if self.in_progress:
            return None
        report_id = "report-cut-1"
        source = SimpleNamespace(idle=self.idle)
        lease = self.store.acquire_collection_lease(cutoff_utc, owner_id="collector")
        assert lease is not None
        snapshot = self.store.create_snapshot(
            report_id=report_id,
            cutoff_utc=cutoff_utc,
            previous_cutoff_utc=None,
            collected_at_utc=cutoff_utc,
            watermarks={},
            payload=_payload(
                report_id, cutoff_utc, items=None if self.items is None else self.items
            ),
            coverage_gaps=(),
            lease=lease,
        )
        self.store.set_last_cutoff(cutoff_utc)
        if self.idle:
            source = SimpleNamespace(idle=True, items=(), coverage_gaps=())
            return SimpleNamespace(report_id=report_id, snapshot=snapshot, source=source)
        source = SimpleNamespace(idle=False, items=tuple(self.items or ()), coverage_gaps=())
        return SimpleNamespace(report_id=report_id, snapshot=snapshot, source=source)


class _FakeNative:
    """Deterministic native monitor runtime; never touches a real Hermes install."""

    def __init__(
        self,
        *,
        profile: str | None = PROFILE,
        job_id: str = JOB_ID,
        created: bool = True,
        destination_error: MonitorActionError | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.profile = profile
        self.job_id = job_id
        self.created = created
        self.destination_error = destination_error
        self.events = events if events is not None else []
        self.calls: list[tuple[str, str | None]] = []

    def runtime_identity(self) -> Mapping[str, Any]:
        return {
            "profile": self.profile,
            "hermes_home": "/private/hermes-home",
            "timezone": "UTC",
            "schedule": "0 * * * *",
        }

    def resolve_destination(self) -> Mapping[str, Any]:
        self.events.append("resolve")
        if self.destination_error is not None:
            raise self.destination_error
        return {"reference": TARGET_REF, "thread_present": True}

    def ensure_job(self, *, job_id, script_name, schedule, name) -> Mapping[str, Any]:
        self.calls.append(("ensure", job_id))
        self.events.append(f"ensure:{job_id or 'new'}")
        return {
            "id": self.job_id,
            "name": name,
            "schedule": schedule,
            "state": "active",
            "created": job_id is None and self.created,
        }

    def pause_job(self, job_id: str) -> Mapping[str, Any]:
        self.calls.append(("pause", job_id))
        self.events.append(f"pause:{job_id}")
        return {
            "id": job_id,
            "name": "Aether Telegram Monitor",
            "state": "paused",
            "created": False,
        }

    def resume_job(self, job_id: str) -> Mapping[str, Any]:
        self.calls.append(("resume", job_id))
        self.events.append(f"resume:{job_id}")
        return {
            "id": job_id,
            "name": "Aether Telegram Monitor",
            "state": "active",
            "created": False,
        }

    def job_state(self, job_id: str) -> Mapping[str, Any] | None:
        self.calls.append(("state", job_id))
        return {
            "id": job_id,
            "name": "Aether Telegram Monitor",
            "state": "active",
            "created": False,
        }


class _OrderingStore(MonitorStore):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.events: list[str] = []

    def set_enabled(self, enabled: bool):
        self.events.append(f"enabled:{enabled}")
        return super().set_enabled(enabled)


class _Sender:
    """Fake injected transport: records text, replays scripted results."""

    def __init__(self, results: list[Any] | None = None) -> None:
        self.results = list(results or [])
        self.calls: list[str] = []

    def __call__(self, target: PinnedTelegramTarget, text: str) -> Any:
        self.calls.append(text)
        if self.results:
            result = self.results.pop(0)
            if isinstance(result, BaseException):
                raise result
            return result
        return {"success": True, "message_id": f"mid-{len(self.calls)}"}


def _target_resolver(settings):
    assert settings.destination_ref == TARGET_REF
    return PinnedTelegramTarget(TARGET_REF, TARGET_CHAT, TARGET_THREAD, settings.profile_binding)


def _adapter(store: MonitorStore, sender: Any) -> TelegramDeliveryAdapter:
    return TelegramDeliveryAdapter(
        store, sender=sender, target_resolver=_target_resolver, sleep=lambda _delay: None
    )


def _gate_line(output: str) -> dict[str, Any]:
    lines = [line for line in output.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    assert isinstance(payload, dict)
    return payload


def _run_precheck(store: MonitorStore, collector: Any, **kwargs: Any) -> tuple[int, str, Any]:
    """Run one pre-check with captured stdout; returns (code, output, collector)."""

    buffer: list[str] = []

    class _Stream:
        def write(self, value: str) -> None:
            buffer.append(value)

    code = run_precheck(store=store, collector=collector, stream=_Stream(), **kwargs)
    return code, "".join(buffer), collector


# ---------------------------------------------------------------------------
# Pre-check wake gate
# ---------------------------------------------------------------------------


def test_precheck_disabled_is_silent_and_never_touches_sources(tmp_path: Path) -> None:
    store = _store(tmp_path, enabled=False)
    collector = _FakeCollector(store, error=AssertionError("collector must not run"))

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    assert _gate_line(output) == {"reason": "disabled", "wakeAgent": False}
    assert collector.calls == []


def test_precheck_idle_resolves_the_report_and_skips_inference(tmp_path: Path) -> None:
    store = _store(tmp_path)
    collector = _FakeCollector(store, idle=True)

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    assert _gate_line(output)["wakeAgent"] is False
    assert _gate_line(output)["reason"] == "idle"
    snapshots = store.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].resolved_at_utc is not None
    assert store.get_narrative(snapshots[0].report_id) is None
    assert collector.calls, "one collection still happened before the idle gate"


def test_precheck_ongoing_work_wakes_with_bounded_context_and_pending_lease(tmp_path: Path) -> None:
    store = _store(tmp_path)
    collector = _FakeCollector(store, items=[_item()])

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    gate = _gate_line(output)
    assert gate["wakeAgent"] is True
    assert gate["report_id"] == "report-cut-1"
    block = output.split("--- BEGIN AETHER TELEGRAM MONITOR SNAPSHOT ---", 1)
    assert len(block) == 2, "the narration context carries the canonical snapshot block"
    snapshot_json = block[1].split("--- END AETHER TELEGRAM MONITOR SNAPSHOT ---", 1)[0].strip()
    assert len(snapshot_json) <= reporting.MAX_MODEL_SNAPSHOT_CHARS
    payload = json.loads(snapshot_json)
    assert payload["items"][0]["work_key"] == "work_alpha"
    narrative = store.get_narrative("report-cut-1")
    assert narrative is not None and narrative.attempt_status == "pending"
    # The pending narration lease is what the reporter session must later present.
    assert (
        store.acquire_collection_lease(
            collector.calls[0],
            owner_id=runtime_module._narration_owner(JOB_ID),
            ttl_seconds=NARRATION_LEASE_TTL_SECONDS,
        )
        is None
    )


def test_precheck_source_failure_wakes_instead_of_looking_idle(tmp_path: Path) -> None:
    store = _store(tmp_path)
    collector = _FakeCollector(store, error=RuntimeError("source exploded"))

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    gate = _gate_line(output)
    assert gate["wakeAgent"] is True
    assert gate["reason"] == "collection-error"


def test_precheck_runtime_mismatch_is_observable_and_never_idle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    collector = _FakeCollector(store, items=[_item()])
    monkeypatch.setattr(
        runtime_module, "_module_problems", lambda: ["hook:on_session_end", "cron.jobs.create_job"]
    )

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    gate = _gate_line(output)
    assert gate == {"reason": "runtime-mismatch", "wakeAgent": True}
    assert "hook:on_session_end" in output
    assert collector.calls == []
    assert store.list_snapshots() == ()


def test_precheck_uses_the_local_wall_clock_hour_and_suppresses_a_repeat_tick(
    tmp_path: Path,
) -> None:
    late = ANCHOR.replace(minute=59, second=30)
    store = _store(tmp_path, clock=_clock(late))
    collector = _FakeCollector(store, items=[_item()])

    code, output, _ = _run_precheck(store, collector, clock=_clock(late))

    assert code == 0
    assert _gate_line(output)["wakeAgent"] is True
    assert len(collector.calls) == 1
    expected_cutoff = service_hour_boundary(late)
    assert collector.calls[0] == expected_cutoff
    snapshot = store.get_snapshot("report-cut-1")
    assert snapshot is not None and snapshot.cutoff_utc == _stamp(expected_cutoff)

    # While that cut still owns a live narration, a repeat tick neither narrates nor
    # collects a second report in the same hour.
    second = _FakeCollector(store, items=[_item()])
    code, output, _ = _run_precheck(store, second, clock=_clock(late))
    assert code == 0
    assert _gate_line(output)["reason"] == "narration-in-progress"
    assert second.calls == []

    # Once the report is resolved, the same hour is simply already collected.
    store.mark_snapshot_resolved("report-cut-1")
    third = _FakeCollector(store, items=[_item()])
    code, output, _ = _run_precheck(store, third, clock=_clock(late))
    assert code == 0
    assert _gate_line(output) == {"reason": "already-collected", "wakeAgent": False}
    assert third.calls == []


def test_precheck_collection_and_gate_stay_well_inside_the_start_bound(tmp_path: Path) -> None:
    store = _store(tmp_path)
    collector = _FakeCollector(store, items=[_item()])

    started = time.monotonic()
    code, output, _ = _run_precheck(store, collector)
    elapsed = time.monotonic() - started

    assert code == 0
    assert _gate_line(output)["wakeAgent"] is True
    assert elapsed < 30.0, "deterministic pre-check work must stay far below the 120s bound"


# ---------------------------------------------------------------------------
# Recovery of unfinished reports
# ---------------------------------------------------------------------------


def test_precheck_resumes_an_unfinished_report_instead_of_collecting_again(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    collector = _FakeCollector(store, error=AssertionError("must not collect a second cut"))

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    gate = _gate_line(output)
    assert gate["wakeAgent"] is True
    assert gate["reason"] == "pending-report"
    assert gate["report_id"] == "report-alpha"
    assert "BEGIN AETHER TELEGRAM MONITOR SNAPSHOT" in output
    assert collector.calls == []
    assert len(store.list_snapshots()) == 1


def test_precheck_waits_while_a_live_narration_owns_the_report(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    _hold_narration_lease(store)
    collector = _FakeCollector(store, error=AssertionError("must not collect a second cut"))

    code, output, _ = _run_precheck(store, collector)

    assert code == 0
    gate = _gate_line(output)
    assert gate["wakeAgent"] is False
    assert gate["reason"] == "narration-in-progress"
    assert collector.calls == []


def test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    structured = _narrative("report-alpha")
    _seed_report(store, narrative_status="accepted", structured=structured)
    parts = reporting.render_parts(_payload("report-alpha", ANCHOR), structured)
    store.enqueue_deliveries("report-alpha", parts)
    failing = _Sender([PreDispatchError("network-reset", retry_after=0.0)] * 3)
    _adapter(store, failing).deliver_report("report-alpha", parts)
    failed_part = store.get_delivery("report-alpha", 0)
    assert failed_part is not None and failed_part.state.value == "failed"

    collector = _FakeCollector(store, error=AssertionError("recovery must precede collection"))
    sender = _Sender()
    code, output, _ = _run_precheck(store, collector, delivery=_adapter(store, sender))

    assert code == 0
    assert sender.calls == parts
    retried = store.get_delivery("report-alpha", 0)
    assert retried is not None and retried.state.value == "confirmed"
    snapshot = store.get_snapshot("report-alpha")
    assert snapshot is not None and snapshot.resolved_at_utc is not None
    narrative = store.get_narrative("report-alpha")
    assert narrative is not None and narrative.attempt_status == "accepted"
    assert collector.calls == []


def test_precheck_sends_one_labeled_service_notice_for_failed_narration(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="failed")
    collector = _FakeCollector(store, error=AssertionError("recovery must precede collection"))
    sender = _Sender()

    code, output, _ = _run_precheck(store, collector, delivery=_adapter(store, sender))

    assert code == 0
    assert len(sender.calls) == 1
    notice = sender.calls[0]
    assert "[SERVICE NOTICE]" in notice
    assert "[NO PROGRESS COVERAGE]" in notice
    assert "report-alpha" in notice
    narrative = store.get_narrative("report-alpha")
    assert narrative is not None and narrative.attempt_status == "failed"
    assert store.get_snapshot("report-alpha").resolved_at_utc is not None

    # A second pre-check never adds a second notice for the same cut.
    repeat = _Sender()
    code, output, _ = _run_precheck(store, collector, delivery=_adapter(store, repeat))
    assert code == 0
    assert repeat.calls == []
    assert len(store.list_deliveries("report-alpha")) == 1


# ---------------------------------------------------------------------------
# Reporter sessions
# ---------------------------------------------------------------------------


def _reporter_payload(
    *, session_id: str | None = None, platform: str = "cron", **extra: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session_id": session_id or f"cron_{JOB_ID}_20260910_120000",
        "platform": platform,
        "turn_id": "turn-1",
        "task_id": "task-1",
    }
    payload.update(extra)
    return payload


def test_reporter_context_requires_the_exact_owned_cron_binding(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert reporter_context(
        store,
        profile_name=PROFILE,
        session_id=f"cron_{JOB_ID}_20260910_120000",
        platform="cron",
    ) == {
        "job_id": JOB_ID,
        "session_id": f"cron_{JOB_ID}_20260910_120000",
        "profile": PROFILE,
    }
    for session_id, platform, profile in (
        ("cron_other-job_20260910_120000", "cron", PROFILE),
        (f"cron_{JOB_ID}_20260910_120000", "telegram", PROFILE),
        (f"cron_{JOB_ID}_20260910_120000", "cron", "implementer"),
        (f"session-{JOB_ID}", "cron", PROFILE),
    ):
        assert (
            reporter_context(store, profile_name=profile, session_id=session_id, platform=platform)
            is None
        ), (session_id, platform, profile)

    disabled = _store(tmp_path / "off", enabled=False)
    assert (
        reporter_context(
            disabled,
            profile_name=PROFILE,
            session_id=f"cron_{JOB_ID}_20260910_120000",
            platform="cron",
        )
        is None
    )


def test_post_llm_call_persists_only_a_validated_narrator_result(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    _hold_narration_lease(store)
    response = json.dumps(_narrative("report-alpha"))

    accepted = handle_post_llm_call(
        _reporter_payload(assistant_response=response), store=store, profile_name=PROFILE
    )

    assert accepted == "report-alpha"
    narrative = store.get_narrative("report-alpha")
    assert narrative is not None
    assert narrative.attempt_status == "accepted"
    assert narrative.structured_result is not None
    assert narrative.narrator_session_id == f"cron_{JOB_ID}_20260910_120000"

    # A foreign session never writes a narrative.
    _seed_report(
        store,
        report_id="report-beta",
        cutoff=ANCHOR + timedelta(hours=1),
        items=[_item(work_key="work_beta")],
        narrative_status="pending",
    )
    foreign = handle_post_llm_call(
        _reporter_payload(
            session_id="cron_other_20260910_120000",
            assistant_response=json.dumps(_narrative("report-beta", "work_beta")),
        ),
        store=store,
        profile_name=PROFILE,
    )
    assert foreign is None
    beta = store.get_narrative("report-beta")
    assert beta is not None and beta.attempt_status == "pending"
    assert store.get_narrative("report-alpha").attempt_status == "accepted"


def test_post_llm_call_rejects_malformed_or_fabricated_narratives(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    _hold_narration_lease(store)

    fabricated = dict(_narrative("report-alpha"))
    fabricated["items"] = [
        {
            "work_key": "work_alpha",
            "resolved": [{"ref": "work_alpha_current", "text": "Shipped."}],
            "current": [],
            "next": [],
            "complications": [],
            "pending": [],
            "status": "in_progress",
        }
    ]
    result = handle_post_llm_call(
        _reporter_payload(assistant_response=json.dumps(fabricated)),
        store=store,
        profile_name=PROFILE,
    )

    assert result == "report-alpha"
    narrative = store.get_narrative("report-alpha")
    assert narrative is not None and narrative.attempt_status == "rejected"
    assert narrative.structured_result is None


def test_session_end_delivers_only_for_the_owned_reporter_and_advances_on_confirm(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    structured = _narrative("report-alpha", status="completed")
    _seed_report(
        store,
        items=[_item(state="completed")],
        narrative_status="accepted",
        structured=structured,
        narrator_session_id=f"cron_{JOB_ID}_20260910_120000",
    )
    _hold_narration_lease(store)
    sender = _Sender()

    foreign = handle_session_end(
        _reporter_payload(session_id="cron_other_20260910_120000", completed=True),
        store=store,
        profile_name=PROFILE,
        delivery=_adapter(store, sender),
    )
    assert foreign is None
    assert sender.calls == []

    run = handle_session_end(
        _reporter_payload(completed=True),
        store=store,
        profile_name=PROFILE,
        language="Spanish",
        delivery=_adapter(store, sender),
    )

    assert run is not None
    parts = reporting.render_parts(
        _payload("report-alpha", ANCHOR, items=[_item(state="completed")]),
        structured,
        owner_language="Spanish",
    )
    assert sender.calls == parts
    assert store.get_delivery("report-alpha", 0).state.value == "confirmed"
    assert store.get_snapshot("report-alpha").resolved_at_utc is not None
    work = store.get_work_item("work_alpha")
    assert work is not None
    assert work.final_outcome_delivery_marker == "report-alpha"
    # A repeat session-end for the same reporter never sends the digest twice.
    repeat = _Sender()
    again = handle_session_end(
        _reporter_payload(completed=True),
        store=store,
        profile_name=PROFILE,
        language="Spanish",
        delivery=_adapter(store, repeat),
    )
    assert again is None
    assert repeat.calls == []


def test_session_end_sends_only_a_notice_for_rejected_narration(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(
        store,
        items=[_item(state="completed")],
        narrative_status="rejected",
        narrator_session_id=f"cron_{JOB_ID}_20260910_120000",
    )
    _hold_narration_lease(store)
    sender = _Sender()

    run = handle_session_end(
        _reporter_payload(completed=True),
        store=store,
        profile_name=PROFILE,
        delivery=_adapter(store, sender),
    )

    assert run is not None
    assert len(sender.calls) == 1
    assert "[SERVICE NOTICE]" in sender.calls[0]
    narrative = store.get_narrative("report-alpha")
    assert narrative is not None and narrative.attempt_status == "failed"
    work = store.get_work_item("work_alpha")
    assert work is None or work.final_outcome_delivery_marker is None


def test_manual_off_blocks_narration_delivery_and_retry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    structured = _narrative("report-alpha")
    _seed_report(
        store,
        narrative_status="accepted",
        structured=structured,
        narrator_session_id=f"cron_{JOB_ID}_20260910_120000",
    )
    _hold_narration_lease(store)
    store.set_enabled(False)
    sender = _Sender()

    run = handle_session_end(
        _reporter_payload(completed=True),
        store=store,
        profile_name=PROFILE,
        delivery=_adapter(store, sender),
    )

    # Manual off blocks the racing send; the report stays pending and durable.
    assert run is None
    assert sender.calls == []
    assert store.list_deliveries("report-alpha") == ()
    snapshot = store.get_snapshot("report-alpha")
    assert snapshot is not None and snapshot.resolved_at_utc is None

    # Re-enabling resumes the preserved report without another narration.
    store.set_enabled(True)
    collector = _FakeCollector(store, error=AssertionError("recovery precedes collection"))
    resumed = _Sender()
    code, output, _ = _run_precheck(store, collector, delivery=_adapter(store, resumed))
    assert code == 0
    assert len(resumed.calls) == 1
    delivered = store.get_delivery("report-alpha", 0)
    assert delivered is not None and delivered.state.value == "confirmed"


# ---------------------------------------------------------------------------
# Control surface
# ---------------------------------------------------------------------------


def test_on_is_idempotent_and_reuses_the_single_owned_job(tmp_path: Path) -> None:
    store = _store(tmp_path, configured=False, enabled=False)
    native = _FakeNative()
    service = MonitorService(store=store, native=native, clock=_clock(ANCHOR))

    first = service.execute("on")
    second = service.execute("on")

    assert first["ok"] is True and second["ok"] is True
    assert first["result"]["native_job"]["id"] == JOB_ID
    assert first["result"]["job_created"] is True
    assert second["result"]["job_created"] is False
    assert [call for call in native.calls if call[0] == "ensure"] == [
        ("ensure", None),
        ("ensure", JOB_ID),
    ]
    settings = store.get_settings()
    assert settings.enabled is True
    assert settings.native_job_id == JOB_ID
    assert settings.profile_binding == PROFILE
    assert settings.destination_ref == TARGET_REF
    assert settings.first_enabled_at_utc is not None


def test_off_persists_disabled_before_pausing_the_exact_job(tmp_path: Path) -> None:
    store = _OrderingStore(state_root=tmp_path / "state", clock=_STORE_CLOCK)
    store.configure(
        native_job_id=JOB_ID,
        profile_binding=PROFILE,
        destination_ref=TARGET_REF,
        timezone_name="UTC",
    )
    store.set_enabled(True)
    store.events.clear()
    native = _FakeNative(events=store.events)
    events: list[str] = store.events

    result = MonitorService(store=store, native=native, clock=_clock(ANCHOR)).execute("off")

    assert result["ok"] is True
    assert events.index("enabled:False") < events.index(f"pause:{JOB_ID}")
    assert [call for call in native.calls if call[0] == "pause"] == [("pause", JOB_ID)]
    assert store.get_settings().enabled is False

    # Restart/activity cannot re-enable the monitor: `on` is the only writer.
    resumed = MonitorService(store=store, native=_FakeNative(), clock=_clock(ANCHOR)).execute(
        "status"
    )
    assert resumed["result"]["enabled"] is False


def test_on_fails_closed_on_missing_or_changed_destination(tmp_path: Path) -> None:
    store = _store(tmp_path, configured=False, enabled=False)
    native = _FakeNative(
        destination_error=MonitorActionError(
            "DESTINATION_MISSING", "no existing Telegram home conversation is configured"
        )
    )

    result = MonitorService(store=store, native=native, clock=_clock(ANCHOR)).execute("on")

    assert result["ok"] is False
    assert result["error"]["code"] == "DESTINATION_MISSING"
    assert native.calls == []
    assert store.get_settings().enabled is False
    assert store.get_settings().destination_ref is None


def test_on_rejects_a_different_profile_or_changed_pin(tmp_path: Path) -> None:
    store = _store(tmp_path)
    mismatch = MonitorService(
        store=store, native=_FakeNative(profile="implementer"), clock=_clock(ANCHOR)
    ).execute("on")
    assert mismatch["ok"] is False
    assert mismatch["error"]["code"] == "RUNTIME_MISMATCH"

    other = _FakeNative()
    other.resolve_destination = lambda: {"reference": "telegram-home-" + "b" * 64}  # type: ignore[method-assign]
    changed = MonitorService(store=store, native=other, clock=_clock(ANCHOR)).execute("on")
    assert changed["ok"] is False
    assert changed["error"]["code"] == "DESTINATION_CHANGED"
    assert store.get_settings().destination_ref == TARGET_REF


def test_status_and_history_report_bounded_operational_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="failed")
    store.enqueue_deliveries("report-alpha", ["notice part"])
    service = MonitorService(store=store, native=_FakeNative(), clock=_clock(ANCHOR))

    status = service.execute("status")
    history = service.execute("history", limit=5)

    assert status["ok"] is True
    assert status["schema_version"] == "aether.telegram-monitor.v1"
    result = status["result"]
    assert result["enabled"] is True
    assert result["destination_pinned"] is True
    assert result["native_job"]["id"] == JOB_ID
    assert result["next_cut_utc"] == _stamp(next_hour_boundary(ANCHOR))
    assert result["last_report"]["report_id"] == "report-alpha"
    assert result["last_report"]["narrative_status"] == "failed"
    assert result["delivery_outcomes"] == {"pending": 1}

    assert history["ok"] is True
    assert history["result"]["limit"] == 5
    assert history["result"]["count"] == 1
    record = history["result"]["reports"][0]
    assert record["report_id"] == "report-alpha"
    assert "payload" not in record and "structured_result" not in record
    assert record["parts"] == [{"part_index": 0, "state": "pending"}]

    bounded = service.execute("history", limit=0)
    assert bounded["ok"] is False and bounded["error"]["code"] == "INVALID_LIMIT"


def test_next_hour_boundary_is_always_a_future_wall_clock_hour() -> None:
    just_before = ANCHOR.replace(minute=59, second=59, microsecond=999_999)
    assert service_hour_boundary(ANCHOR) == ANCHOR
    assert next_hour_boundary(ANCHOR) == ANCHOR + timedelta(hours=1)
    assert next_hour_boundary(just_before) == ANCHOR + timedelta(hours=1)
    for value in (ANCHOR, just_before, ANCHOR + timedelta(minutes=30, seconds=1)):
        boundary = service_hour_boundary(value)
        assert boundary.minute == boundary.second == boundary.microsecond == 0
        assert boundary <= value < next_hour_boundary(value)
        assert next_hour_boundary(value) - boundary == timedelta(hours=1)


@pytest.mark.skipif(sys.platform == "win32", reason="time.tzset is POSIX-only")
def test_hour_boundary_follows_the_wall_clock_across_a_dst_fold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "Europe/Madrid")
    time.tzset()
    try:
        first_fold = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
        second_fold = datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
        first = service_hour_boundary(first_fold)
        second = service_hour_boundary(second_fold)
        assert (first.year, first.month, first.day, first.hour) == (2026, 10, 25, 2)
        assert (second.year, second.month, second.day, second.hour) == (2026, 10, 25, 2)
        assert first.utcoffset() != second.utcoffset()
        # The persisted UTC cutoff stays monotonic across the fold.
        assert _stamp(first) < _stamp(second)
    finally:
        if previous is None:
            monkeypatch.delenv("TZ", raising=False)
        else:
            monkeypatch.setenv("TZ", previous)
        time.tzset()


# ---------------------------------------------------------------------------
# Direct project-bound work
# ---------------------------------------------------------------------------

_SESSION_SCHEMA = """
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    display_name TEXT,
    cwd TEXT,
    git_repo_root TEXT,
    started_at REAL,
    ended_at REAL,
    last_activity_at REAL
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp REAL
);
"""

_PROJECTS_SCHEMA = """
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT,
    primary_path TEXT,
    archived INTEGER DEFAULT 0
);
"""


@pytest.fixture
def direct_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Disposable Hermes home plus a marker-verified registered project."""

    project = tmp_path / "project"
    (project / ".aether").mkdir(parents=True)
    (project / ".aether" / "project.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'project_id = "{PROJECT_ID}"',
                'name = "Direct work project"',
                'initialized_by = "1.0.0"',
                'forge = "local"',
                'contract_root = "specs"',
                "",
            )
        ),
        encoding="utf-8",
    )
    state = tmp_path / "state"
    registry = ProjectRegistry(state)
    assert registry.register(PROJECT_ID, project, "Direct work project", NATIVE_PROJECT_ID)

    home = tmp_path / "hermes-home"
    home.mkdir()
    with sqlite3.connect(home / "projects.db") as connection:
        connection.executescript(_PROJECTS_SCHEMA)
        connection.execute(
            "INSERT INTO projects VALUES (?, ?, ?, 0)",
            (NATIVE_PROJECT_ID, "direct", str(project)),
        )
        connection.commit()
    with sqlite3.connect(home / "state.db") as connection:
        connection.executescript(_SESSION_SCHEMA)
        connection.executemany(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    SESSION_ID,
                    "tui",
                    "Direct session",
                    "Direct session",
                    str(project),
                    str(project),
                    1788955200.0,
                    None,
                    1788958800.0,
                ),
                (
                    "session-elsewhere",
                    "tui",
                    "Unbound session",
                    "Unbound session",
                    str(tmp_path / "unbound"),
                    str(tmp_path / "unbound"),
                    1788955200.0,
                    None,
                    1788958800.0,
                ),
            ],
        )
        connection.commit()
    monkeypatch.setattr(runtime_module, "hermes_home", lambda: home)
    return state


def test_direct_enrollment_requires_an_exact_project_bound_session(
    tmp_path: Path, direct_home: Path
) -> None:
    store = _store(tmp_path)

    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "kanban_show"},
        store=store,
        profile_name=PROFILE,
    )
    handle_post_tool_call(
        {"session_id": "session-elsewhere", "turn_id": "turn-2", "tool_name": "terminal"},
        store=store,
        profile_name=PROFILE,
    )
    handle_post_tool_call(
        {
            "session_id": f"cron_{JOB_ID}_20260910_120000",
            "turn_id": "turn-3",
            "tool_name": "terminal",
        },
        store=store,
        profile_name=PROFILE,
    )
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-4", "tool_name": "aether_monitor"},
        store=store,
        profile_name=PROFILE,
    )

    records = load_direct_records(store)
    assert len(records) == 1
    record = records[0]
    assert record["session_id"] == SESSION_ID
    assert record["interval_id"] == "turn-1"
    assert record["project_id"] == PROJECT_ID
    assert record["native_project_id"] == NATIVE_PROJECT_ID
    assert record["outcome"] == "unknown"


def test_direct_turn_end_marks_flags_and_continuation_opens_a_new_interval(
    tmp_path: Path, direct_home: Path
) -> None:
    store = _store(tmp_path)
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "terminal"}, store=store
    )
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "read_file"}, store=store
    )
    runtime_module.handle_post_llm_call_direct(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "assistant_response": "Turn finished."},
        store=store,
    )
    handle_session_end_direct(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "completed": True}, store=store
    )
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-2", "tool_name": "terminal"}, store=store
    )

    records = {record["interval_id"]: record for record in load_direct_records(store)}
    assert set(records) == {"turn-1", "turn-2"}
    assert records["turn-1"]["outcome"] == "completed"
    assert records["turn-1"]["ended_at"]
    assert records["turn-1"]["summary"] == "Turn finished."
    assert records["turn-2"]["outcome"] == "unknown"
    assert "ended_at" not in records["turn-2"]


def test_direct_records_reject_unsafe_reported_summaries(tmp_path: Path, direct_home: Path) -> None:
    store = _store(tmp_path)
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "terminal"}, store=store
    )

    # Assembled at runtime so this regression never contains a private-path literal.
    home_like_path = "/" + "home" + "/" + "operator" + "/notes.txt"
    for text in (
        "see https://example.invalid/private",
        f"write to {home_like_path}",
        "mail owner@example.invalid",
    ):
        runtime_module.handle_post_llm_call_direct(
            {"session_id": SESSION_ID, "turn_id": "turn-1", "assistant_response": text},
            store=store,
        )
        record = load_direct_records(store)[0]
        assert "summary" not in record, text

    runtime_module.handle_post_llm_call_direct(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "assistant_response": "x" * 4_000},
        store=store,
    )
    records = load_direct_records(store)
    assert len(records) == 1
    summary = records[0]["summary"]
    assert len(summary) == runtime_module._DIRECT_SUMMARY_CHARS
    assert summary.endswith("\u2026")


def test_direct_turn_end_requires_an_enrolled_interval(tmp_path: Path, direct_home: Path) -> None:
    store = _store(tmp_path)

    handle_session_end_direct(
        {"session_id": SESSION_ID, "turn_id": "never-enrolled", "completed": True}, store=store
    )

    assert load_direct_records(store) == []


def test_configured_owner_language_prefers_plugin_settings(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "\n".join(
            (
                "plugins:",
                "  entries:",
                "    aether-telegram-monitor:",
                "      settings:",
                "        language: Spanish",
                "",
            )
        ),
        encoding="utf-8",
    )

    class _ConfigModule:
        @staticmethod
        def load_config_readonly():
            import yaml

            return yaml.safe_load(config.read_text(encoding="utf-8"))

    monkeypatch.setitem(sys.modules, "hermes_cli.config", _ConfigModule)
    assert configured_owner_language() == "Spanish"

    monkeypatch.setenv("AETHER_MONITOR_LANGUAGE", "French")
    config.write_text("plugins: {}\n", encoding="utf-8")
    assert configured_owner_language() == "French"
