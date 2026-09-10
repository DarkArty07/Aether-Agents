"""Native runtime, wake gate, hooks and controls for the Telegram monitor (MON-05).

Every test runs against disposable monitor state, disposable Hermes homes and fake
native runtimes/transport.  No live profile, job, model or Telegram destination is
touched.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import textwrap
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
from aether_agents.monitor.service import (
    NATIVE_JOB_NAME,
    NATIVE_SCHEDULE,
    PRECHECK_SCRIPT_NAME,
    MonitorActionError,
    MonitorService,
    next_hour_boundary,
)
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


def _hold_narration_lease(
    store: MonitorStore, report_id: str = "report-alpha", cutoff: datetime | None = None
):
    """Simulate a *live* pre-check/narration lease plus its handoff."""

    cutoff = cutoff or ANCHOR
    lease = store.acquire_collection_lease(
        cutoff,
        owner_id=runtime_module._narration_owner(JOB_ID),
        ttl_seconds=NARRATION_LEASE_TTL_SECONDS,
    )
    assert lease is not None
    snapshot = store.get_snapshot(report_id)
    assert snapshot is not None
    assert runtime_module._write_handoff(
        store,
        report_id=report_id,
        cutoff_utc=snapshot.cutoff_utc,
        job_id=JOB_ID,
        lease=lease,
        holder="precheck",
    )
    return lease


def _handoff_from_dead_precheck(
    store: MonitorStore, report_id: str = "report-alpha", cutoff: datetime | None = None
):
    """Simulate the pre-check child exiting after it handed the report over.

    The child's lease row is then owned by a dead process, exactly as it is when the
    real packaged pre-check finishes and the native scheduler starts the reporter
    session in a different process.
    """

    lease = _hold_narration_lease(store, report_id, cutoff)
    assert store.release_collection_lease(lease)
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
    # The pending narration lease is what the reporter session must later present, and
    # the cross-process handoff is what lets it survive the pre-check child exiting.
    assert runtime_module._read_handoff(store, "report-cut-1") is not None
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
    _handoff_from_dead_precheck(store)
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
    _handoff_from_dead_precheck(store)

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
    _handoff_from_dead_precheck(store)
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
    # The delivered interval releases its narration lease and handoff.
    assert runtime_module._read_handoff(store, "report-alpha", require_fresh=False) is None
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
    _handoff_from_dead_precheck(store)
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
    _handoff_from_dead_precheck(store)
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
                (
                    "session-telegram",
                    "telegram",
                    "Gateway conversation",
                    "Gateway conversation",
                    str(project),
                    str(project),
                    1788955200.0,
                    None,
                    1788958800.0,
                ),
                (
                    "session-tool-source",
                    "tool",
                    "Sub-agent run",
                    "Sub-agent run",
                    str(project),
                    str(project),
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
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "terminal"},
        store=store,
        profile_name=PROFILE,
    )
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "read_file"},
        store=store,
        profile_name=PROFILE,
    )
    runtime_module.handle_post_llm_call_direct(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "assistant_response": "Turn finished."},
        store=store,
        profile_name=PROFILE,
    )
    handle_session_end_direct(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "completed": True},
        store=store,
        profile_name=PROFILE,
    )
    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-2", "tool_name": "terminal"},
        store=store,
        profile_name=PROFILE,
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
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "terminal"},
        store=store,
        profile_name=PROFILE,
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
            profile_name=PROFILE,
        )
        record = load_direct_records(store)[0]
        assert "summary" not in record, text

    runtime_module.handle_post_llm_call_direct(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "assistant_response": "x" * 4_000},
        store=store,
        profile_name=PROFILE,
    )
    records = load_direct_records(store)
    assert len(records) == 1
    summary = records[0]["summary"]
    assert len(summary) == runtime_module._DIRECT_SUMMARY_CHARS
    assert summary.endswith("\u2026")


def test_direct_turn_end_requires_an_enrolled_interval(tmp_path: Path, direct_home: Path) -> None:
    store = _store(tmp_path)

    handle_session_end_direct(
        {"session_id": SESSION_ID, "turn_id": "never-enrolled", "completed": True},
        store=store,
        profile_name=PROFILE,
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


# ---------------------------------------------------------------------------
# Cross-process pending-narration handoff
# ---------------------------------------------------------------------------


def test_precheck_child_handoff_reaches_the_exact_reporter(tmp_path: Path) -> None:
    """A real pre-check child process hands its pending lease to the reporter session.

    The pre-check runs in a child process that exits before the reporter session starts,
    so its lease row has a dead owner and would be recovered by any later acquisition.
    The private handoff is what keeps the exact reporter eligible.
    """

    state_root = tmp_path / "aether"
    home = tmp_path / "hermes-home"
    home.mkdir()
    store = MonitorStore(state_root=state_root, clock=_STORE_CLOCK)
    store.configure(
        native_job_id=JOB_ID,
        profile_binding=PROFILE,
        destination_ref=TARGET_REF,
        timezone_name="UTC",
    )
    store.set_enabled(True)
    _seed_report(store, narrative_status="pending")
    cutoff_text = store.get_snapshot("report-alpha").cutoff_utc

    driver = tmp_path / "precheck-child.py"
    driver.write_text(
        textwrap.dedent(
            """
            from aether_agents.monitor import runtime as monitor_runtime

            # The imported-runtime preflight has its own release-locked regression;
            # this probe exercises the cross-process handoff mechanics themselves.
            monitor_runtime._module_problems = lambda: []
            raise SystemExit(monitor_runtime.main_precheck())
            """
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(driver)],
        cwd=Path(__file__).parents[1],
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
            "XDG_STATE_HOME": str(tmp_path),
            "HERMES_HOME": str(home),
        },
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, completed.stderr
    assert json.loads(lines[-1]) == {
        "wakeAgent": True,
        "reason": "pending-report",
        "report_id": "report-alpha",
        "cutoff_utc": cutoff_text,
        "job_id": JOB_ID,
    }
    assert "BEGIN AETHER TELEGRAM MONITOR SNAPSHOT" in completed.stdout

    # The child is gone; the handoff is the only cross-process transfer evidence.
    parent = MonitorStore(state_root=state_root, clock=_STORE_CLOCK)
    handoff = runtime_module._read_handoff(parent, "report-alpha")
    assert handoff is not None and handoff["holder"] == "precheck"

    response = json.dumps(_narrative("report-alpha"))
    accepted = handle_post_llm_call(
        _reporter_payload(assistant_response=response), store=parent, profile_name=PROFILE
    )
    assert accepted == "report-alpha"
    claimed = runtime_module._read_handoff(parent, "report-alpha")
    assert claimed is not None and claimed["holder"] == "reporter"

    sender = _Sender()
    run = handle_session_end(
        _reporter_payload(completed=True),
        store=parent,
        profile_name=PROFILE,
        delivery=_adapter(parent, sender),
    )
    assert run is not None
    expected_parts = reporting.render_parts(
        _payload("report-alpha", ANCHOR), _narrative("report-alpha")
    )
    assert sender.calls == expected_parts
    assert parent.get_snapshot("report-alpha").resolved_at_utc is not None
    assert runtime_module._read_handoff(parent, "report-alpha", require_fresh=False) is None

    repeat = _Sender()
    assert (
        handle_session_end(
            _reporter_payload(completed=True),
            store=parent,
            profile_name=PROFILE,
            delivery=_adapter(parent, repeat),
        )
        is None
    )
    assert repeat.calls == []


def test_reporter_requires_the_exact_precheck_handoff(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    cutoff_text = store.get_snapshot("report-alpha").cutoff_utc
    lease = store.acquire_collection_lease(
        ANCHOR,
        owner_id=runtime_module._narration_owner(JOB_ID),
        ttl_seconds=NARRATION_LEASE_TTL_SECONDS,
    )
    assert lease is not None
    # The pre-check child then exits; only the handoff can carry the report forward.
    assert store.release_collection_lease(lease)
    response = json.dumps(_narrative("report-alpha"))

    # A dead lease row alone is not cross-process evidence: no handoff, no narration.
    assert (
        handle_post_llm_call(
            _reporter_payload(assistant_response=response), store=store, profile_name=PROFILE
        )
        is None
    )
    assert store.get_narrative("report-alpha").attempt_status == "pending"

    # A handoff for a different owned job is not this report's transfer.
    assert runtime_module._write_handoff(
        store,
        report_id="report-alpha",
        cutoff_utc=cutoff_text,
        job_id="job-other",
        lease=lease,
        holder="precheck",
    )
    assert (
        handle_post_llm_call(
            _reporter_payload(assistant_response=response), store=store, profile_name=PROFILE
        )
        is None
    )

    # An expired handoff fails closed even with a matching job identity.
    expired = SimpleNamespace(
        token=lease.token,
        acquired_at_utc=lease.acquired_at_utc,
        expires_at_utc="2020-01-01T00:00:00.000000Z",
    )
    assert runtime_module._write_handoff(
        store,
        report_id="report-alpha",
        cutoff_utc=cutoff_text,
        job_id=JOB_ID,
        lease=expired,
        holder="precheck",
    )
    assert (
        handle_post_llm_call(
            _reporter_payload(assistant_response=response), store=store, profile_name=PROFILE
        )
        is None
    )

    # The exact handoff transfers the pending report to the reporter.
    assert runtime_module._write_handoff(
        store,
        report_id="report-alpha",
        cutoff_utc=cutoff_text,
        job_id=JOB_ID,
        lease=lease,
        holder="precheck",
    )
    assert (
        handle_post_llm_call(
            _reporter_payload(assistant_response=response), store=store, profile_name=PROFILE
        )
        == "report-alpha"
    )
    assert store.get_narrative("report-alpha").attempt_status == "accepted"


def test_reporter_claim_is_fenced_to_the_exact_session(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    _handoff_from_dead_precheck(store)
    session_a = f"cron_{JOB_ID}_20260910_120000"
    session_b = f"cron_{JOB_ID}_20260910_130000"
    response = json.dumps(_narrative("report-alpha"))

    # Reporter A takes the live claim and persists the accepted narrative.
    assert (
        handle_post_llm_call(
            _reporter_payload(session_id=session_a, assistant_response=response),
            store=store,
            profile_name=PROFILE,
        )
        == "report-alpha"
    )
    snapshot = store.get_snapshot("report-alpha")
    assert snapshot is not None

    # A second session of the same job can neither claim nor deliver that live report.
    assert (
        runtime_module._claim_pending_lease(store, snapshot, job_id=JOB_ID, session_id=session_b)
        is None
    )
    sender = _Sender()
    assert (
        handle_session_end(
            _reporter_payload(session_id=session_b, completed=True),
            store=store,
            profile_name=PROFILE,
            delivery=_adapter(store, sender),
        )
        is None
    )
    assert sender.calls == []

    # A's own next hook may refresh its claim and delivers exactly once.
    run = handle_session_end(
        _reporter_payload(session_id=session_a, completed=True),
        store=store,
        profile_name=PROFILE,
        delivery=_adapter(store, sender),
    )
    assert run is not None
    assert len(sender.calls) == len(
        reporting.render_parts(_payload("report-alpha", ANCHOR), _narrative("report-alpha"))
    )


def test_reporter_claim_loses_to_a_live_foreign_narration(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_report(store, narrative_status="pending")
    cutoff_text = store.get_snapshot("report-alpha").cutoff_utc
    assert runtime_module._write_handoff(
        store,
        report_id="report-alpha",
        cutoff_utc=cutoff_text,
        job_id=JOB_ID,
        lease=SimpleNamespace(
            token="precheck-token",
            acquired_at_utc=_stamp(ANCHOR),
            expires_at_utc="2099-01-01T00:00:00.000000Z",
        ),
        holder="precheck",
    )
    live = store.acquire_collection_lease(
        ANCHOR, owner_id="another-live-narration", ttl_seconds=NARRATION_LEASE_TTL_SECONDS
    )
    assert live is not None

    response = json.dumps(_narrative("report-alpha"))
    assert (
        handle_post_llm_call(
            _reporter_payload(assistant_response=response), store=store, profile_name=PROFILE
        )
        is None
    )
    assert store.get_narrative("report-alpha").attempt_status == "pending"
    # The foreign narration keeps its lease untouched.
    assert (
        store.acquire_collection_lease(
            ANCHOR, owner_id="probe", ttl_seconds=NARRATION_LEASE_TTL_SECONDS
        )
        is None
    )


# ---------------------------------------------------------------------------
# Exact Morfeo identity
# ---------------------------------------------------------------------------


def test_reporter_context_requires_the_exact_profile(tmp_path: Path) -> None:
    store = _store(tmp_path)
    session = f"cron_{JOB_ID}_20260910_120000"

    assert reporter_context(store, profile_name=None, session_id=session, platform="cron") is None
    assert (
        reporter_context(store, profile_name="implementer", session_id=session, platform="cron")
        is None
    )
    assert reporter_context(store, profile_name=PROFILE, session_id=session, platform="cron") == {
        "job_id": JOB_ID,
        "session_id": session,
        "profile": PROFILE,
    }


def test_on_requires_the_exact_morfeo_identity_before_any_mutation(tmp_path: Path) -> None:
    for index, profile in enumerate((None, "implementer", "supervisor")):
        store = _store(tmp_path / f"case-{index}", configured=False, enabled=False)
        native = _FakeNative(profile=profile)

        result = MonitorService(store=store, native=native, clock=_clock(ANCHOR)).execute("on")

        assert result["ok"] is False
        assert result["error"]["code"] == "RUNTIME_MISMATCH", profile
        settings = store.get_settings()
        assert settings.enabled is False
        assert settings.native_job_id is None
        assert settings.destination_ref is None
        assert settings.profile_binding is None
        assert native.calls == []


class _FailingResumeNative(_FakeNative):
    def resume_job(self, job_id: str) -> Mapping[str, Any]:
        self.calls.append(("resume", job_id))
        raise MonitorActionError("JOB_OPERATION_FAILED", "the native job resume failed")


def test_failed_enable_never_flips_the_monitor_on(tmp_path: Path) -> None:
    store = _OrderingStore(state_root=tmp_path / "state", clock=_STORE_CLOCK)
    native = _FailingResumeNative(events=store.events)

    result = MonitorService(store=store, native=native, clock=_clock(ANCHOR)).execute("on")

    assert result["ok"] is False
    assert result["error"]["code"] == "JOB_OPERATION_FAILED"
    settings = store.get_settings()
    assert settings.enabled is False
    assert settings.first_enabled_at_utc is None
    # The binding is durable so a retry reuses the same job, but nothing enabled.
    assert settings.native_job_id == JOB_ID
    assert settings.destination_ref == TARGET_REF
    assert store.events.count("enabled:True") == 0
    assert [call for call in native.calls if call[0] == "resume"] == [("resume", JOB_ID)]

    # A racing pre-check still sees a disabled monitor and does nothing.
    collector = _FakeCollector(store, error=AssertionError("disabled ticks never collect"))
    code, output, _ = _run_precheck(store, collector)
    assert code == 0
    assert _gate_line(output) == {"reason": "disabled", "wakeAgent": False}
    assert collector.calls == []


# ---------------------------------------------------------------------------
# Configured timezone
# ---------------------------------------------------------------------------


def test_configured_timezone_comes_from_native_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _HermesTime:
        @staticmethod
        def get_timezone():
            from zoneinfo import ZoneInfo

            return ZoneInfo("Asia/Kolkata")

    monkeypatch.setitem(sys.modules, "hermes_time", _HermesTime)
    assert runtime_module.configured_timezone_name() == "Asia/Kolkata"

    class _Unconfigured:
        @staticmethod
        def get_timezone():
            return None

    monkeypatch.setitem(sys.modules, "hermes_time", _Unconfigured)
    monkeypatch.setenv("HERMES_TIMEZONE", "America/New_York")
    assert runtime_module.configured_timezone_name() == "America/New_York"

    monkeypatch.setenv("HERMES_TIMEZONE", "   ")
    monkeypatch.setattr(runtime_module, "local_timezone_name", lambda: "UTC")
    assert runtime_module.configured_timezone_name() == "UTC"


def test_precheck_cuts_hours_in_the_configured_native_zone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The persisted setting is the default UTC; the native configured zone wins because
    # that is the clock the native cron actually fires on.
    store = _store(tmp_path)
    late = datetime(2026, 9, 10, 12, 45, tzinfo=UTC)
    monkeypatch.setattr(runtime_module, "configured_timezone_name", lambda: "Asia/Kolkata")
    collector = _FakeCollector(store, items=[_item()])

    code, output, _ = _run_precheck(store, collector, clock=_clock(late))

    assert code == 0
    assert _gate_line(output)["wakeAgent"] is True
    # 12:45Z is 18:15 IST; the IST hour cut is 12:30Z, not the UTC-grid 12:00Z cut.
    assert collector.calls == [datetime(2026, 9, 10, 12, 30, tzinfo=UTC)]
    assert service_hour_boundary(late, timezone_name="Asia/Kolkata") == collector.calls[0]


def test_status_renders_the_next_cut_in_the_persisted_zone(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.configure(
        native_job_id=JOB_ID,
        profile_binding=PROFILE,
        destination_ref=TARGET_REF,
        timezone_name="Asia/Kolkata",
    )
    service = MonitorService(
        store=store, native=_FakeNative(), clock=_clock(datetime(2026, 9, 10, 12, 45, tzinfo=UTC))
    )

    result = service.execute("status")["result"]

    assert result["timezone"] == "Asia/Kolkata"
    assert result["next_cut_utc"] == _stamp(datetime(2026, 9, 10, 13, 30, tzinfo=UTC))
    assert result["next_cut_local"] == "2026-09-10T19:00:00+05:30"


def test_status_keeps_a_resolvable_persisted_zone_over_a_local_label(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.configure(
        native_job_id=JOB_ID,
        profile_binding=PROFILE,
        destination_ref=TARGET_REF,
        timezone_name="Asia/Kolkata",
    )
    service = MonitorService(
        store=store,
        native=_FakeNative(),
        clock=_clock(datetime(2026, 9, 10, 12, 45, tzinfo=UTC)),
        timezone_name="CEST",
    )

    result = service.execute("status")["result"]

    # A local abbreviation is not a zone: the real persisted IANA zone still renders.
    assert result["next_cut_utc"] == _stamp(datetime(2026, 9, 10, 13, 30, tzinfo=UTC))
    assert result["next_cut_local"] == "2026-09-10T19:00:00+05:30"


def test_on_pins_the_resolvable_configured_zone(tmp_path: Path) -> None:
    store = _store(tmp_path, configured=False, enabled=False)
    native = _FakeNative(profile=PROFILE)

    result = MonitorService(
        store=store, native=native, clock=_clock(ANCHOR), timezone_name="Asia/Kolkata"
    ).execute("on")

    assert result["ok"] is True
    assert store.get_settings().timezone == "Asia/Kolkata"


def test_hour_boundary_follows_the_configured_zone_across_a_dst_fold() -> None:
    # Europe/Madrid folds 2026-10-25 03:00 CEST back to 02:00 CET.
    first_fold = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    second_fold = datetime(2026, 10, 25, 1, 30, tzinfo=UTC)

    first = service_hour_boundary(first_fold, timezone_name="Europe/Madrid")
    second = service_hour_boundary(second_fold, timezone_name="Europe/Madrid")

    assert (first.hour, first.utcoffset()) == (2, timedelta(hours=2))
    assert (second.hour, second.utcoffset()) == (2, timedelta(hours=1))
    assert _stamp(first) < _stamp(second)
    # A future boundary still follows the configured wall clock.
    assert next_hour_boundary(
        datetime(2026, 10, 25, 0, 30, tzinfo=UTC), timezone_name="Europe/Madrid"
    ) == second + timedelta(hours=1)


# ---------------------------------------------------------------------------
# Native job ownership and reconciliation
# ---------------------------------------------------------------------------


def _native_job(
    job_id: str = "job-owned",
    *,
    name: str = NATIVE_JOB_NAME,
    prompt: str | None = None,
    schedule: str = NATIVE_SCHEDULE,
    script: str | None = PRECHECK_SCRIPT_NAME,
    deliver: str = "local",
    enabled_toolsets: list[str] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": job_id,
        "name": name,
        "prompt": runtime_module._JOB_PROMPT if prompt is None else prompt,
        "skills": [],
        "skill": None,
        "model": None,
        "provider": None,
        "provider_snapshot": None,
        "model_snapshot": None,
        "base_url": None,
        "script": script,
        "no_agent": False,
        "monitor_script": None,
        "monitor_url": None,
        "monitor_state": None,
        "context_from": None,
        "schedule": {"kind": "cron", "expr": schedule, "display": schedule},
        "schedule_display": schedule,
        "repeat": {"times": None, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "paused_at": None,
        "paused_reason": None,
        "created_at": "2026-09-10T00:00:00+00:00",
        "next_run_at": None,
        "last_run_at": None,
        "last_status": None,
        "last_error": None,
        "last_delivery_error": None,
        "failure_streak": 0,
        "deliver": deliver,
        "origin": None,
        "enabled_toolsets": (
            list(runtime_module.REPORTER_JOB_TOOLSETS)
            if enabled_toolsets is None
            else enabled_toolsets
        ),
        "workdir": None,
        "attach_to_session": False,
    }
    record.update(overrides)
    return record


class _FakeCronModule:
    """Native-shaped cron API used to exercise the owned-job lifecycle."""

    def __init__(
        self,
        jobs: list[dict[str, Any]] | None = None,
        *,
        list_error: bool = False,
        update_returns_none: bool = False,
    ) -> None:
        self.jobs = [dict(job) for job in (jobs or [])]
        self.list_error = list_error
        self.update_returns_none = update_returns_none
        self.create_calls: list[dict[str, Any]] = []
        self.updates: list[tuple[str, dict[str, Any]]] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        for job in self.jobs:
            if job.get("id") == job_id:
                return dict(job)
        return None

    def list_jobs(self, include_disabled: bool = False) -> list[dict[str, Any]]:
        if self.list_error:
            raise RuntimeError("native inventory unavailable")
        return [dict(job) for job in self.jobs]

    def create_job(self, **kwargs: Any) -> dict[str, Any]:
        record = _native_job(
            job_id=f"job-created-{len(self.jobs)}",
            name=kwargs.get("name"),
            prompt=kwargs.get("prompt"),
            schedule=kwargs.get("schedule", NATIVE_SCHEDULE),
            script=kwargs.get("script"),
            deliver=kwargs.get("deliver", "local"),
            enabled_toolsets=kwargs.get("enabled_toolsets"),
            no_agent=kwargs.get("no_agent", False),
            attach_to_session=kwargs.get("attach_to_session", False),
        )
        self.create_calls.append(dict(kwargs))
        self.jobs.append(record)
        return dict(record)

    def update_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        for index, job in enumerate(self.jobs):
            if job.get("id") != job_id:
                continue
            if self.update_returns_none:
                return None
            merged = {**job, **updates}
            skills = [str(item) for item in (merged.get("skills") or []) if str(item)]
            merged["skills"] = skills
            merged["skill"] = skills[0] if skills else None
            self.jobs[index] = merged
            self.updates.append((job_id, dict(updates)))
            return dict(merged)
        return None

    def pause_job(self, job_id: str) -> dict[str, Any] | None:
        self.pause_calls.append(job_id)
        for job in self.jobs:
            if job.get("id") == job_id:
                job["enabled"] = False
                job["state"] = "paused"
                return dict(job)
        return None

    def resume_job(self, job_id: str) -> dict[str, Any] | None:
        self.resume_calls.append(job_id)
        for job in self.jobs:
            if job.get("id") == job_id:
                job["enabled"] = True
                job["state"] = "scheduled"
                return dict(job)
        return None


@pytest.fixture
def job_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "job-home"
    home.mkdir()
    monkeypatch.setattr(runtime_module, "hermes_home", lambda: home)
    return home


def _cron_runtime(monkeypatch: pytest.MonkeyPatch, cron: _FakeCronModule) -> Any:
    monkeypatch.setattr(runtime_module, "_cron_jobs", lambda: cron)
    return runtime_module.HermesRuntime()


def test_ensure_job_refuses_same_name_adoption_without_a_persisted_id(
    tmp_path: Path, job_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cron = _FakeCronModule([_native_job("job-foreign")])
    runtime = _cron_runtime(monkeypatch, cron)

    with pytest.raises(MonitorActionError) as error:
        runtime.ensure_job(
            job_id=None,
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )

    assert error.value.code == "JOB_CONFLICT"
    assert cron.create_calls == [] and cron.updates == []
    assert [job["id"] for job in cron.jobs] == ["job-foreign"]


def test_ensure_job_rejects_replaced_ids_and_inventory_failures(
    tmp_path: Path, job_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replaced = _FakeCronModule([_native_job("job-owned", name="Unrelated operator job")])
    runtime = _cron_runtime(monkeypatch, replaced)
    with pytest.raises(MonitorActionError) as conflict:
        runtime.ensure_job(
            job_id="job-owned",
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )
    assert conflict.value.code == "JOB_CONFLICT"
    assert replaced.updates == [] and replaced.create_calls == []

    # A second job claiming the monitor name makes the inventory ambiguous.
    duplicated = _FakeCronModule([_native_job("job-owned"), _native_job("job-duplicate")])
    runtime = _cron_runtime(monkeypatch, duplicated)
    with pytest.raises(MonitorActionError) as ambiguous:
        runtime.ensure_job(
            job_id="job-owned",
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )
    assert ambiguous.value.code == "JOB_CONFLICT"
    assert duplicated.updates == [] and duplicated.create_calls == []

    # A persisted ID that vanished while a same-name job exists is ambiguous.
    missing = _FakeCronModule([_native_job("job-somewhere-else")])
    runtime = _cron_runtime(monkeypatch, missing)
    with pytest.raises(MonitorActionError) as replaced_id:
        runtime.ensure_job(
            job_id="job-gone",
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )
    assert replaced_id.value.code == "JOB_CONFLICT"
    assert missing.create_calls == []

    # An unreadable inventory never creates a duplicate.
    broken = _FakeCronModule(list_error=True)
    runtime = _cron_runtime(monkeypatch, broken)
    with pytest.raises(MonitorActionError) as unreadable:
        runtime.ensure_job(
            job_id=None,
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )
    assert unreadable.value.code == "JOB_OPERATION_FAILED"
    assert broken.create_calls == []


def test_ensure_job_reconciles_the_full_fixed_shape(
    tmp_path: Path, job_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    drifted = _native_job(
        "job-owned",
        prompt="hijacked prompt",
        model="some/model",
        provider="some-provider",
        base_url="https://example.invalid",
        origin={"platform": "telegram"},
        skills=["some-skill"],
        context_from=["other-job"],
        workdir=str(tmp_path / "elsewhere"),
        enabled_toolsets=["terminal"],
        no_agent=True,
        attach_to_session=True,
    )
    cron = _FakeCronModule([drifted])
    runtime = _cron_runtime(monkeypatch, cron)

    result = runtime.ensure_job(
        job_id="job-owned",
        script_name=PRECHECK_SCRIPT_NAME,
        schedule=NATIVE_SCHEDULE,
        name=NATIVE_JOB_NAME,
    )

    assert result["created"] is False and result["id"] == "job-owned"
    assert len(cron.updates) == 1
    job_id, updates = cron.updates[0]
    assert job_id == "job-owned"
    assert set(updates) >= {
        "prompt",
        "model",
        "provider",
        "base_url",
        "origin",
        "skills",
        "context_from",
        "workdir",
        "enabled_toolsets",
        "no_agent",
        "attach_to_session",
    }
    repaired = cron.get_job("job-owned")
    assert repaired["prompt"] == runtime_module._JOB_PROMPT
    assert repaired["model"] is None and repaired["provider"] is None
    assert repaired["base_url"] is None and repaired["origin"] is None
    assert repaired["skills"] == [] and repaired["skill"] is None
    assert repaired["context_from"] is None and repaired["workdir"] is None
    assert repaired["enabled_toolsets"] == [
        runtime_module.REPORTER_TOOLSET,
        runtime_module.NO_MCP_SENTINEL,
    ]
    assert repaired["no_agent"] is False and repaired["attach_to_session"] is False
    assert (
        runtime._drift(repaired, script_name=PRECHECK_SCRIPT_NAME, schedule=NATIVE_SCHEDULE) == {}
    )

    # A second enable finds no drift and performs no second update.
    again = runtime.ensure_job(
        job_id="job-owned",
        script_name=PRECHECK_SCRIPT_NAME,
        schedule=NATIVE_SCHEDULE,
        name=NATIVE_JOB_NAME,
    )
    assert again["created"] is False
    assert len(cron.updates) == 1


def test_ensure_job_creation_carries_and_validates_the_fixed_shape(
    tmp_path: Path, job_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cron = _FakeCronModule()
    runtime = _cron_runtime(monkeypatch, cron)

    result = runtime.ensure_job(
        job_id=None,
        script_name=PRECHECK_SCRIPT_NAME,
        schedule=NATIVE_SCHEDULE,
        name=NATIVE_JOB_NAME,
    )

    assert result["created"] is True
    request = cron.create_calls[0]
    assert request["name"] == NATIVE_JOB_NAME
    assert request["prompt"] == runtime_module._JOB_PROMPT
    assert request["schedule"] == NATIVE_SCHEDULE
    assert request["script"] == PRECHECK_SCRIPT_NAME
    assert request["deliver"] == "local"
    assert request["enabled_toolsets"] == [
        runtime_module.REPORTER_TOOLSET,
        runtime_module.NO_MCP_SENTINEL,
    ]
    assert request["no_agent"] is False and request["attach_to_session"] is False

    class _BrokenCreate(_FakeCronModule):
        def create_job(self, **kwargs: Any) -> dict[str, Any]:
            self.create_calls.append(dict(kwargs))
            return {"id": "job-broken", "name": NATIVE_JOB_NAME}

    broker = _BrokenCreate()
    runtime = _cron_runtime(monkeypatch, broker)
    with pytest.raises(MonitorActionError) as error:
        runtime.ensure_job(
            job_id=None,
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )
    assert error.value.code == "JOB_OPERATION_FAILED"


def test_ensure_job_fails_when_the_native_update_does_not_apply(
    tmp_path: Path, job_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    drifted = _native_job("job-owned", prompt="hijacked prompt")
    cron = _FakeCronModule([drifted], update_returns_none=True)
    runtime = _cron_runtime(monkeypatch, cron)

    with pytest.raises(MonitorActionError) as error:
        runtime.ensure_job(
            job_id="job-owned",
            script_name=PRECHECK_SCRIPT_NAME,
            schedule=NATIVE_SCHEDULE,
            name=NATIVE_JOB_NAME,
        )

    assert error.value.code == "JOB_OPERATION_FAILED"
    assert cron.get_job("job-owned")["prompt"] == "hijacked prompt"


def test_pause_and_resume_revalidate_ownership(
    tmp_path: Path, job_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cron = _FakeCronModule(
        [
            _native_job("job-owned"),
            _native_job("job-unrelated", name="Unrelated operator job", script=None),
        ]
    )
    runtime = _cron_runtime(monkeypatch, cron)

    with pytest.raises(MonitorActionError) as conflict:
        runtime.pause_job("job-unrelated")
    assert conflict.value.code == "JOB_CONFLICT"
    assert cron.pause_calls == []
    assert cron.get_job("job-unrelated")["enabled"] is True

    with pytest.raises(MonitorActionError) as missing:
        runtime.resume_job("job-absent")
    assert missing.value.code == "JOB_OPERATION_FAILED"
    assert cron.resume_calls == []

    assert runtime.pause_job("job-owned")["state"] == "paused"
    assert cron.get_job("job-owned")["enabled"] is False
    assert runtime.resume_job("job-owned")["state"] == "active"
    assert cron.get_job("job-owned")["enabled"] is True
    assert cron.get_job("job-unrelated")["enabled"] is True


# ---------------------------------------------------------------------------
# Direct enrollment sources
# ---------------------------------------------------------------------------


def test_direct_enrollment_rejects_gateway_service_and_foreign_profiles(
    tmp_path: Path, direct_home: Path
) -> None:
    store = _store(tmp_path)

    for session_id in ("session-telegram", "session-tool-source"):
        handle_post_tool_call(
            {"session_id": session_id, "turn_id": "turn-x", "tool_name": "terminal"},
            store=store,
            profile_name=PROFILE,
        )
    assert load_direct_records(store) == []

    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "terminal"},
        store=store,
        profile_name="implementer",
    )
    assert load_direct_records(store) == []

    handle_post_tool_call(
        {"session_id": SESSION_ID, "turn_id": "turn-1", "tool_name": "terminal"},
        store=store,
        profile_name=PROFILE,
    )
    records = load_direct_records(store)
    assert len(records) == 1 and records[0]["session_id"] == SESSION_ID
