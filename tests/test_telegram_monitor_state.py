from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import pytest

from aether_agents.monitor.models import DeliveryState, WorkItem
from aether_agents.monitor.store import (
    DuplicateRecordError,
    IdentityConflictError,
    ImmutableRecordError,
    LeaseLostError,
    MonitorStore,
    MonitorStoreError,
    UnsafeMonitorPath,
)

UTC = timezone.utc


def _clock(value: datetime):
    current = value

    def now() -> datetime:
        return current

    def set_now(next_value: datetime) -> None:
        nonlocal current
        current = next_value

    return now, set_now


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _item(first_seen: str, *, work_key: str = "work-alpha", active: bool = True) -> WorkItem:
    return WorkItem(
        work_key=work_key,
        project_id="project-alpha",
        origin_session_id="session-alpha",
        origin_session_title="Build session",
        contract_id="oc_abcdef0123456789",
        contract_version="v1",
        contract_title="Monitor objective",
        first_seen_utc=first_seen,
        observed_state="running",
        active=active,
    )


def _seed_report(store: MonitorStore, cutoff: str, *, report_id: str | None = None) -> str:
    store.set_enabled(True)
    lease = store.acquire_collection_lease(cutoff, owner_id="seed-collector")
    assert lease is not None
    snapshot = store.create_snapshot(
        cutoff_utc=cutoff,
        previous_cutoff_utc=None,
        collected_at_utc=cutoff,
        watermarks={"project-alpha": "cursor-1"},
        payload={
            "schema_version": "aether.telegram-monitor.snapshot.v1",
            "report_id": report_id or "generated",
            "cutoff_utc": cutoff,
            "items": [{"work_key": "work-alpha", "observed_state": "running"}],
        },
        coverage_gaps=(),
        report_id=report_id,
        lease=lease,
    )
    return snapshot.report_id


def test_store_uses_private_contained_path_and_hardens_existing_database(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    store = MonitorStore(state_root=state_root)

    assert store.db_path == state_root / "monitor" / "monitor.sqlite3"
    assert stat.S_IMODE(state_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.db_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600

    store.db_path.chmod(0o644)
    MonitorStore(state_root=state_root)
    assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600


def test_store_rejects_traversal_symlink_and_hard_linked_database(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        MonitorStore(state_root=Path("relative-state"))

    outside = tmp_path / "outside"
    outside.mkdir()
    symlink_root = tmp_path / "symlink-state"
    symlink_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises((UnsafeMonitorPath, OSError)):
        MonitorStore(state_root=symlink_root)

    hardlink_root = tmp_path / "hardlink-state"
    monitor_dir = hardlink_root / "monitor"
    monitor_dir.mkdir(parents=True)
    database = monitor_dir / "monitor.sqlite3"
    database.write_bytes(b"not a database")
    os.link(database, monitor_dir / "database-alias")
    with pytest.raises((UnsafeMonitorPath, OSError)):
        MonitorStore(state_root=hardlink_root)


def test_settings_off_is_durable_and_configuration_is_private(tmp_path: Path) -> None:
    now, _ = _clock(datetime(2026, 9, 9, 12, tzinfo=UTC))
    root = tmp_path / "state"
    first = MonitorStore(state_root=root, clock=now)
    first.configure(
        native_job_id="job-monitor",
        profile_binding="morfeo",
        destination_ref="configured-home",
        timezone="Europe/Madrid",
    )
    enabled = first.set_enabled(True)
    assert enabled.enabled is True
    assert enabled.native_job_id == "job-monitor"
    assert enabled.destination_ref == "configured-home"

    disabled = first.set_enabled(False)
    assert disabled.enabled is False
    restarted = MonitorStore(state_root=root, clock=now)
    assert restarted.get_settings().enabled is False
    assert restarted.get_settings().destination_ref == "configured-home"


def test_work_item_identity_is_immutable_but_observed_state_and_watermark_change(
    tmp_path: Path,
) -> None:
    now = _stamp(datetime(2026, 9, 9, 12, tzinfo=UTC))
    store = MonitorStore(state_root=tmp_path / "state")
    original = _item(now)
    stored = store.upsert_work_item(original)
    assert stored == original

    changed = replace(
        original,
        observed_state="blocked",
        source_cursor="cursor-2",
        active=False,
        ended_at_utc=now,
    )
    updated = store.upsert_work_item(changed)
    assert updated.observed_state == "blocked"
    assert updated.source_cursor == "cursor-2"
    assert updated.active is False

    with sqlite3.connect(store.db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE work_items SET project_id = ? WHERE work_key = ?",
                ("project-other", original.work_key),
            )

    with pytest.raises(IdentityConflictError):
        store.upsert_work_item(replace(original, project_id="project-other"))


def test_snapshot_ids_and_cutoffs_are_unique_and_payload_is_immutable(tmp_path: Path) -> None:
    cutoff = "2026-09-09T12:00:00Z"
    store = MonitorStore(state_root=tmp_path / "state")
    store.set_enabled(True)
    lease = store.acquire_collection_lease(cutoff, owner_id="collector-alpha")
    assert lease is not None
    payload = {"items": [{"work_key": "work-alpha", "current": ["waiting"]}]}
    snapshot = store.create_snapshot(
        cutoff_utc=cutoff,
        previous_cutoff_utc=None,
        collected_at_utc=cutoff,
        watermarks={"project-alpha": "cursor-1"},
        payload=payload,
        coverage_gaps=("late source",),
        report_id="report-alpha",
        lease=lease,
    )
    payload["items"].append({"work_key": "mutated-after-write"})
    persisted = store.get_snapshot(snapshot.report_id)
    assert persisted is not None
    assert persisted.payload == {"items": [{"work_key": "work-alpha", "current": ["waiting"]}]}
    with sqlite3.connect(store.db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE snapshots SET payload_json = ? WHERE report_id = ?",
                ("{}", snapshot.report_id),
            )

    with pytest.raises(ImmutableRecordError):
        store.create_snapshot(
            cutoff_utc=cutoff,
            previous_cutoff_utc=None,
            collected_at_utc=cutoff,
            watermarks={"project-alpha": "different"},
            payload={"different": True},
            report_id="report-alpha",
            lease="any-token",
        )
    with pytest.raises(DuplicateRecordError):
        store.create_snapshot(
            cutoff_utc=cutoff,
            previous_cutoff_utc=None,
            collected_at_utc=cutoff,
            watermarks={},
            payload={"other": True},
            report_id="report-beta",
            lease="any-token",
        )
    assert hashlib.sha256(snapshot.payload_json.encode()).hexdigest() == snapshot.digest


def test_snapshot_resolution_is_explicit_and_rejects_unresolved_parts(tmp_path: Path) -> None:
    store = MonitorStore(state_root=tmp_path / "state")
    resolved_id = _seed_report(store, "2026-09-09T12:00:00Z", report_id="report-idle")
    resolved = store.mark_snapshot_resolved(resolved_id)
    assert resolved.resolved_at_utc is not None

    pending_id = _seed_report(store, "2026-09-09T13:00:00Z", report_id="report-pending-resolve")
    store.enqueue_deliveries(pending_id, ["pending"])
    with pytest.raises(MonitorStoreError):
        store.mark_snapshot_resolved(pending_id)


def test_collection_lease_fences_duplicate_workers(tmp_path: Path) -> None:
    cutoff = "2026-09-09T13:00:00Z"
    root = tmp_path / "state"
    MonitorStore(state_root=root).set_enabled(True)
    stores = [MonitorStore(state_root=root), MonitorStore(state_root=root)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(
            pool.map(
                lambda pair: pair[0].acquire_collection_lease(cutoff, owner_id=pair[1]),
                zip(stores, ("collector-a", "collector-b")),
            )
        )
    assert sum(lease is not None for lease in leases) == 1


def test_delivery_lease_fences_concurrent_senders_and_allows_writes_during_slow_call(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"
    store = MonitorStore(state_root=root)
    store.set_enabled(True)
    report_id = _seed_report(store, "2026-09-09T14:00:00Z", report_id="report-send")
    store.enqueue_deliveries(report_id, ["part one", "part two"])
    with sqlite3.connect(store.db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE deliveries SET text_hash = ? WHERE report_id = ? AND part_index = 0",
                ("changed", report_id),
            )
    stores = [MonitorStore(state_root=root), MonitorStore(state_root=root)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(
            pool.map(
                lambda pair: pair[0].claim_delivery(report_id, 0, owner_id=pair[1]),
                zip(stores, ("sender-a", "sender-b")),
            )
        )
    claimed = [lease for lease in leases if lease is not None]
    assert len(claimed) == 1

    entered = Event()
    release = Event()

    def fake_slow_external_call() -> None:
        entered.set()
        assert release.wait(2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        slow = pool.submit(fake_slow_external_call)
        assert entered.wait(2)
        setting_write = pool.submit(store.set_enabled, False)
        assert setting_write.result(timeout=2).enabled is False
        release.set()
        slow.result(timeout=2)


def test_manual_off_is_rechecked_after_lease_before_dispatch(tmp_path: Path) -> None:
    root = tmp_path / "state"
    store = MonitorStore(state_root=root)
    store.set_enabled(True)
    report_id = _seed_report(store, "2026-09-09T15:00:00Z", report_id="report-off-race")
    store.enqueue_deliveries(report_id, ["part"])
    lease = store.claim_delivery(report_id, 0, owner_id="sender")
    assert lease is not None

    store.set_enabled(False)
    assert store.can_dispatch_delivery(lease) is False
    store.suppress_delivery(lease, reason="monitor disabled")
    suppressed = store.get_delivery(report_id, 0)
    assert suppressed is not None
    assert suppressed.state is DeliveryState.SUPPRESSED


def test_restart_recovers_expired_sending_as_uncertain_and_does_not_retry_blindly(
    tmp_path: Path,
) -> None:
    initial = datetime(2026, 9, 9, 16, tzinfo=UTC)
    now, set_now = _clock(initial)
    root = tmp_path / "state"
    store = MonitorStore(state_root=root, clock=now)
    store.set_enabled(True)
    report_id = _seed_report(store, _stamp(initial), report_id="report-crash")
    store.enqueue_deliveries(report_id, ["part"])
    lease = store.claim_delivery(report_id, 0, owner_id="sender", ttl_seconds=5)
    assert lease is not None
    sending = store.get_delivery(report_id, 0)
    assert sending is not None
    assert sending.state is DeliveryState.SENDING

    set_now(initial + timedelta(seconds=6))
    restarted = MonitorStore(state_root=root, clock=now)
    recovered = restarted.get_delivery(report_id, 0)
    assert recovered.state is DeliveryState.UNCERTAIN
    assert recovered.last_error_class == "dispatch-uncertain"
    assert restarted.claim_delivery(report_id, 0, owner_id="retry") is None


def test_restart_recovers_sending_from_dead_owner_before_lease_expiry(tmp_path: Path) -> None:
    initial = datetime(2026, 9, 9, 16, tzinfo=UTC)
    now, _ = _clock(initial)
    root = tmp_path / "state"
    store = MonitorStore(state_root=root, clock=now)
    store.set_enabled(True)
    report_id = _seed_report(store, _stamp(initial), report_id="report-dead-owner")
    store.enqueue_deliveries(report_id, ["part"])
    lease = store.claim_delivery(report_id, 0, owner_id="sender", ttl_seconds=600)
    assert lease is not None
    assert lease.owner_process_id == os.getpid()
    with sqlite3.connect(store.db_path) as connection:
        connection.execute(
            "UPDATE leases SET owner_pid = ? WHERE token = ?",
            (99_999_999, lease.token),
        )

    restarted = MonitorStore(state_root=root, clock=now)
    recovered = restarted.get_delivery(report_id, 0)
    assert recovered is not None
    assert recovered.state is DeliveryState.UNCERTAIN


def test_stale_resolved_history_is_purged_but_pending_uncertain_and_work_survive(
    tmp_path: Path,
) -> None:
    initial = datetime(2026, 9, 9, 17, tzinfo=UTC)
    now, set_now = _clock(initial)
    root = tmp_path / "state"
    store = MonitorStore(state_root=root, clock=now)
    store.set_enabled(True)
    old_cutoff = _stamp(initial - timedelta(days=31))

    confirmed_id = _seed_report(store, old_cutoff, report_id="report-confirmed")
    store.enqueue_deliveries(confirmed_id, ["confirmed"])
    confirmed_lease = store.claim_delivery(confirmed_id, 0, owner_id="sender")
    assert confirmed_lease is not None
    store.complete_delivery(confirmed_lease, outcome="confirmed", message_id="message-1")

    pending_id = _seed_report(store, old_cutoff.replace("17:", "18:"), report_id="report-pending")
    store.enqueue_deliveries(pending_id, ["pending"])

    uncertain_id = _seed_report(
        store, old_cutoff.replace("17:", "19:"), report_id="report-uncertain"
    )
    store.enqueue_deliveries(uncertain_id, ["uncertain"])
    uncertain_lease = store.claim_delivery(uncertain_id, 0, owner_id="sender", ttl_seconds=1)
    assert uncertain_lease is not None
    set_now(initial + timedelta(seconds=2))
    MonitorStore(state_root=root, clock=now)

    store.upsert_work_item(_item(old_cutoff, active=True))
    set_now(initial + timedelta(days=1))
    assert store.purge_resolved() == 0
    assert store.get_snapshot(confirmed_id) is not None
    set_now(initial + timedelta(days=31))
    assert store.purge_resolved() == 1
    assert store.get_snapshot(confirmed_id) is None
    assert store.get_snapshot(pending_id) is not None
    assert store.get_snapshot(uncertain_id) is not None
    retained_item = store.get_work_item("work-alpha")
    assert retained_item is not None
    assert retained_item.active is True


def test_source_database_is_not_opened_or_modified(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("create table source_rows (value text)")
        connection.execute("insert into source_rows values ('untouched')")
    before_bytes = source.read_bytes()
    before_stat = source.stat()

    store = MonitorStore(state_root=tmp_path / "state")
    store.set_enabled(True)
    _seed_report(store, "2026-09-09T20:00:00Z", report_id="report-private")

    after_stat = source.stat()
    assert source.read_bytes() == before_bytes
    assert (after_stat.st_size, after_stat.st_mtime_ns, after_stat.st_ino) == (
        before_stat.st_size,
        before_stat.st_mtime_ns,
        before_stat.st_ino,
    )
    with sqlite3.connect(source) as connection:
        assert connection.execute("select value from source_rows").fetchone() == ("untouched",)


def test_narrative_outbox_and_watermark_survive_restart(tmp_path: Path) -> None:
    root = tmp_path / "state"
    store = MonitorStore(state_root=root)
    report_id = _seed_report(store, "2026-09-09T21:00:00Z", report_id="report-persist")
    item = store.upsert_work_item(_item("2026-09-09T20:00:00Z"))
    updated = store.upsert_work_item(replace(item, source_cursor={"event": 4}))
    assert updated.source_cursor == {"event": 4}
    narrative = store.put_narrative(
        report_id,
        structured_result={"status": "waiting", "pending": ["review"]},
        narrator_session_id="narrator-session",
        attempt_status="accepted",
    )
    deliveries = store.enqueue_deliveries(report_id, ["header\nwaiting"])
    assert deliveries[0].text_hash == hashlib.sha256(b"header\nwaiting").hexdigest()

    restarted = MonitorStore(state_root=root)
    assert restarted.get_narrative(report_id) == narrative
    assert restarted.list_deliveries(report_id) == deliveries
    restarted_item = restarted.get_work_item("work-alpha")
    assert restarted_item is not None
    assert restarted_item.source_cursor == {"event": 4}


def test_unicode_snapshot_limit_is_character_bounded(tmp_path: Path) -> None:
    store = MonitorStore(state_root=tmp_path / "state")
    store.set_enabled(True)
    cutoff = "2026-09-09T22:00:00Z"
    lease = store.acquire_collection_lease(cutoff, owner_id="unicode-collector")
    assert lease is not None
    payload = {"text": "😀" * 8_000}
    snapshot = store.create_snapshot(
        cutoff_utc=cutoff,
        previous_cutoff_utc=None,
        collected_at_utc=cutoff,
        watermarks={},
        payload=payload,
        report_id="report-unicode",
        lease=lease,
    )
    assert snapshot.payload["text"] == payload["text"]


def test_expired_lease_cannot_commit_a_late_receipt(tmp_path: Path) -> None:
    initial = datetime(2026, 9, 9, 23, tzinfo=UTC)
    now, set_now = _clock(initial)
    root = tmp_path / "state"
    store = MonitorStore(state_root=root, clock=now)
    store.set_enabled(True)
    report_id = _seed_report(store, _stamp(initial), report_id="report-fence")
    store.enqueue_deliveries(report_id, ["part"])
    lease = store.claim_delivery(report_id, 0, owner_id="sender", ttl_seconds=1)
    assert lease is not None
    set_now(initial + timedelta(seconds=2))
    with pytest.raises(LeaseLostError):
        store.complete_delivery(lease, outcome="confirmed", message_id="late-message")
    recovered = store.get_delivery(report_id, 0)
    assert recovered is not None
    assert recovered.state is DeliveryState.UNCERTAIN


def test_failed_delivery_remains_unresolved_for_later_retry_and_retention(
    tmp_path: Path,
) -> None:
    initial = datetime(2026, 9, 10, tzinfo=UTC)
    now, set_now = _clock(initial)
    root = tmp_path / "state"
    store = MonitorStore(state_root=root, clock=now)
    store.set_enabled(True)
    old_cutoff = _stamp(initial - timedelta(days=31))
    report_id = _seed_report(store, old_cutoff, report_id="report-failed")
    store.enqueue_deliveries(report_id, ["part"])
    lease = store.claim_delivery(report_id, 0, owner_id="sender")
    assert lease is not None
    failed = store.complete_delivery(
        lease,
        outcome="failed",
        error_class="pre-dispatch",
        error_message="temporary transport refusal",
    )
    assert failed.state is DeliveryState.FAILED
    failed_snapshot = store.get_snapshot(report_id)
    assert failed_snapshot is not None
    assert failed_snapshot.resolved_at_utc is None
    set_now(initial + timedelta(days=1))
    assert store.purge_resolved() == 0
    assert store.get_snapshot(report_id) is not None


def test_old_completed_work_is_bounded_but_active_or_unreported_work_is_retained(
    tmp_path: Path,
) -> None:
    initial = datetime(2026, 9, 11, tzinfo=UTC)
    now, _ = _clock(initial)
    store = MonitorStore(state_root=tmp_path / "state", clock=now)
    old = _stamp(initial - timedelta(days=31))
    completed = replace(
        _item(old, work_key="completed-work", active=False),
        ended_at_utc=old,
        final_outcome_delivery_marker="report-completed",
    )
    active = _item(old, work_key="active-work", active=True)
    unreported = replace(
        _item(old, work_key="unreported-work", active=False),
        ended_at_utc=old,
    )
    pending_report = _seed_report(store, old, report_id="report-pending-work")
    store.enqueue_deliveries(pending_report, ["pending report"])
    pending_work = replace(
        _item(old, work_key="pending-work", active=False),
        ended_at_utc=old,
        final_outcome_delivery_marker=pending_report,
    )
    store.upsert_work_item(completed)
    store.upsert_work_item(active)
    store.upsert_work_item(unreported)
    store.upsert_work_item(pending_work)

    store.purge_resolved()
    assert store.get_work_item("completed-work") is None
    assert store.get_work_item("active-work") is not None
    assert store.get_work_item("unreported-work") is not None
    assert store.get_work_item("pending-work") is not None


def test_stale_collection_lease_cannot_commit_and_current_owner_can(tmp_path: Path) -> None:
    initial = datetime(2026, 9, 9, 14, 0, 0, tzinfo=UTC)
    now, set_now = _clock(initial)
    root = tmp_path / "state"
    store_a = MonitorStore(state_root=root, clock=now)
    store_b = MonitorStore(state_root=root, clock=now)
    store_a.set_enabled(True)

    cutoff = "2026-09-09T14:00:00.000000Z"
    lease_a = store_a.acquire_collection_lease(cutoff, owner_id="collector-a", ttl_seconds=10)
    assert lease_a is not None

    # Clock advances past lease A TTL (15s > 10s)
    set_now(initial + timedelta(seconds=15))

    # Collector B acquires replacement collection lease
    lease_b = store_b.acquire_collection_lease(cutoff, owner_id="collector-b", ttl_seconds=60)
    assert lease_b is not None
    assert lease_b.token != lease_a.token

    # Stale collector A attempts to commit snapshot
    with pytest.raises(LeaseLostError):
        store_a.create_snapshot(
            cutoff_utc=cutoff,
            previous_cutoff_utc=None,
            collected_at_utc=cutoff,
            watermarks={"project-alpha": "cursor-stale"},
            payload={"schema_version": "aether.telegram-monitor.snapshot.v1", "items": []},
            report_id="stale-report",
            lease=lease_a,
        )
    assert store_a.get_snapshot("stale-report") is None

    # Current owner B successfully commits snapshot
    snapshot_b = store_b.commit_snapshot(
        lease_b,
        cutoff_utc=cutoff,
        previous_cutoff_utc=None,
        collected_at_utc=cutoff,
        watermarks={"project-alpha": "cursor-current"},
        payload={"schema_version": "aether.telegram-monitor.snapshot.v1", "items": []},
        report_id="current-report",
    )
    assert snapshot_b.report_id == "current-report"
    assert store_b.get_snapshot("current-report") is not None

    # Expired collector A attempting again is rejected by duplicate cutoff
    with pytest.raises(DuplicateRecordError):
        store_a.create_snapshot(
            cutoff_utc=cutoff,
            previous_cutoff_utc=None,
            collected_at_utc=cutoff,
            watermarks={},
            payload={"items": []},
            report_id="stale-report-retry",
            lease=lease_a,
        )

    # Manual-off semantics: disabled store rejects snapshot commit even with valid lease
    next_cutoff = "2026-09-09T15:00:00.000000Z"
    lease_c = store_b.acquire_collection_lease(next_cutoff, owner_id="collector-b", ttl_seconds=60)
    assert lease_c is not None
    store_b.set_enabled(False)
    with pytest.raises(LeaseLostError):
        store_b.commit_snapshot(
            lease_c,
            cutoff_utc=next_cutoff,
            previous_cutoff_utc=cutoff,
            collected_at_utc=next_cutoff,
            watermarks={},
            payload={"items": []},
            report_id="disabled-report",
        )
    assert store_b.get_snapshot("disabled-report") is None


def test_utc_timestamp_normalization_and_fractional_ordering_boundaries(tmp_path: Path) -> None:
    initial = datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC)
    now, set_now = _clock(initial)
    root = tmp_path / "state"
    store = MonitorStore(state_root=root, clock=now)
    store.set_enabled(True)

    # 1. Advancing last_cutoff from whole seconds to fractional seconds is accepted
    store.set_last_cutoff("2026-09-09T12:00:00Z")
    settings = store.set_last_cutoff("2026-09-09T12:00:00.500000Z")
    assert settings.last_cutoff_utc == "2026-09-09T12:00:00.500000Z"

    # Backwards movement is rejected
    with pytest.raises(ValueError, match="cannot move backwards"):
        store.set_last_cutoff("2026-09-09T12:00:00.250000Z")
    with pytest.raises(ValueError, match="cannot move backwards"):
        store.set_last_cutoff("2026-09-09T12:00:00Z")

    # Further forward movement with fractional seconds is accepted
    settings = store.set_last_cutoff("2026-09-09T12:00:00.750000Z")
    assert settings.last_cutoff_utc == "2026-09-09T12:00:00.750000Z"

    # 2. Snapshot cutoff ordering with fractional vs whole timestamps
    cutoff_fractional = "2026-09-09T12:00:00.500000Z"
    cutoff_whole = "2026-09-09T12:00:00Z"

    # Previous preceding cutoff: accepted
    lease_frac = store.acquire_collection_lease(cutoff_fractional, owner_id="collector-frac")
    assert lease_frac is not None
    snap = store.create_snapshot(
        cutoff_utc=cutoff_fractional,
        previous_cutoff_utc=cutoff_whole,
        collected_at_utc=cutoff_fractional,
        watermarks={},
        payload={"items": []},
        report_id="report-frac",
        lease=lease_frac,
    )
    assert snap.cutoff_utc == "2026-09-09T12:00:00.500000Z"
    assert snap.previous_cutoff_utc == "2026-09-09T12:00:00.000000Z"

    # Previous after or equal to cutoff: rejected
    lease_bad = store.acquire_collection_lease("2026-09-09T13:00:00.000000Z", owner_id="collector")
    assert lease_bad is not None
    with pytest.raises(ValueError, match="previous cutoff must precede"):
        store.create_snapshot(
            cutoff_utc="2026-09-09T13:00:00.000000Z",
            previous_cutoff_utc="2026-09-09T13:00:00.500000Z",
            collected_at_utc="2026-09-09T13:00:00.000000Z",
            watermarks={},
            payload={"items": []},
            report_id="report-bad-order",
            lease=lease_bad,
        )

    # 3. Fractional TTL lease eligibility, dispatch, and recovery
    report_id = _seed_report(store, "2026-09-09T14:00:00Z", report_id="report-frac-ttl")
    store.enqueue_deliveries(report_id, ["part-frac-ttl"])

    # Acquire lease with fractional TTL (0.5s)
    lease_deliv = store.claim_delivery(report_id, 0, owner_id="sender-frac", ttl_seconds=0.5)
    assert lease_deliv is not None

    # Before 0.5s expires (e.g. 0.2s): valid, can dispatch, not expired
    set_now(initial + timedelta(seconds=0.2))
    assert store.can_dispatch_delivery(lease_deliv) is True

    # At 0.6s (> 0.5s): expired, cannot dispatch, completion raises LeaseLostError
    set_now(initial + timedelta(seconds=0.6))
    assert store.can_dispatch_delivery(lease_deliv) is False
    with pytest.raises(LeaseLostError):
        store.complete_delivery(lease_deliv, outcome="confirmed", message_id="msg-late")

    # Recovery marks it uncertain
    restarted = MonitorStore(state_root=root, clock=now)
    recovered = restarted.get_delivery(report_id, 0)
    assert recovered is not None
    assert recovered.state is DeliveryState.UNCERTAIN
