from __future__ import annotations

import gzip
import hashlib
import json
import multiprocessing
import os
import sqlite3
import stat
import threading
import time
from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest
from observation_helpers import (
    EPOCH,
    PROJECT_ID,
    TRACE_ID,
    EventFactory,
    complete_trace,
    native_pseudonym,
)

from aether_agents.lifecycle import HERMES_BASELINE, PreparedRelease, ReleaseStore
from aether_agents.observation import query as query_module
from aether_agents.observation import retention as retention_module
from aether_agents.observation import storage as storage_module
from aether_agents.observation.capture import journal as journal_module
from aether_agents.observation.capture.collector import Collector
from aether_agents.observation.capture.flusher import Flusher
from aether_agents.observation.capture.journal import (
    JournalWriter,
    epoch_is_unclean,
    list_segments,
    parse_segment_name,
    read_segment,
)
from aether_agents.observation.checkpoint import AuthorityContext, CheckpointSink
from aether_agents.observation.contracts import (
    EVENT_SCHEMA_VERSION,
    MAX_EVENT_LINE_BYTES,
    READ_MODEL_SCHEMA,
    canonical_json_bytes,
    sha256_hex,
)
from aether_agents.observation.reduce import ingest as ingest_module
from aether_agents.observation.reduce import upcast as upcast_module
from aether_agents.observation.reduce.ingest import ingest_pending, reduce_trace
from aether_agents.observation.reduce.reconciliation import dedupe
from aether_agents.observation.reduce.reducer import ReductionInput, reduce_events
from aether_agents.observation.reduce.upcast import UpcastResult
from aether_agents.observation.retention import (
    SegmentNotEligible,
    _deterministic_gzip,
    compact_segment,
    gzip_header_fields,
    iter_archive_events,
    recover_interrupted,
    verify_archive,
)
from aether_agents.observation.storage import ReadModel
from aether_agents.paths import ObservationPaths, UnsafeObservationPath


def _write_closed_segment(tmp_path, *, events=None, epoch: str = EPOCH):
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory(epoch=epoch)
    if events is None:
        factory.opened(0)
        factory.contract("contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64)
        events = factory.events
    writer = JournalWriter(paths=paths, producer_epoch=epoch)
    writer.open()
    for event in events:
        assert writer.append(event).accepted
    closed = writer.close()
    assert closed is not None
    reference = parse_segment_name(closed)
    assert reference is not None
    return paths, reference


def _activate_test_release(state_root, fixture_root) -> None:
    wheel = fixture_root / "aether_agents-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"authority-fixture-wheel")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    stage = fixture_root / "prepared-release"
    for environment in ("manager", "runtime"):
        marker = stage / environment / "aether-wheel.sha256"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(digest + "\n", encoding="ascii")
    aether_identity = {
        "distribution": "aether-agents",
        "package_version": "1.0.0",
        "git_tag": "v1.0.0",
        "git_commit": "a" * 40,
        "python_requires": ">=3.11,<3.14",
        "observer": {
            "plugin_name": "aether-contract-observer",
            "group": "hermes_agent.plugins",
            "target": "aether_agents.observation.capture.hermes_plugin",
        },
    }
    ReleaseStore(state_root).activate(
        PreparedRelease(
            version="1.0.0",
            wheel=wheel,
            wheel_sha256=digest,
            stage=stage,
            hermes_tag=HERMES_BASELINE.tag,
            hermes_commit=HERMES_BASELINE.commit,
            aether_identity=aether_identity,
            prebuild_identity=hashlib.sha256(
                json.dumps(aether_identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            installed_file_fingerprint=hashlib.sha256(
                b"installed:authority-fixture-wheel"
            ).hexdigest(),
        )
    )


def test_journal_appends_canonical_lf_lines_and_cleanly_closes(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    data = segment.path.read_bytes()
    assert data.endswith(b"\n")
    read = read_segment(segment.path)
    assert len(read.lines) == 2 and read.trailing_fragment == b""
    records = [json.loads(line) for line in read.lines]
    assert [record["producer_seq"] for record in records] == [0, 1]
    assert {record["producer_epoch"] for record in records} == {EPOCH}
    assert list_segments(paths) == [segment]


def test_journal_and_state_permissions_are_private_on_posix(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    if os.name != "posix":
        pytest.skip("POSIX permission invariant")
    assert stat.S_IMODE(paths.project.stat().st_mode) == 0o700
    assert stat.S_IMODE(segment.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(paths.lock_file(EPOCH).stat().st_mode) == 0o600


def test_callback_append_path_never_calls_fsync(monkeypatch, tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    event = EventFactory().opened(0)
    calls = []
    original = os.fsync
    monkeypatch.setattr(os, "fsync", lambda descriptor: calls.append(descriptor))
    try:
        assert writer.append(event).accepted
        assert calls == []
    finally:
        monkeypatch.setattr(os, "fsync", original)
        writer.close()


def test_threshold_rotation_never_runs_fsync_in_append(monkeypatch, tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(
        paths=paths,
        producer_epoch=EPOCH,
        max_segment_events=1,
    )
    writer.open()
    fsync_entered = threading.Event()
    release_fsync = threading.Event()
    original_fsync = journal_module.os.fsync

    def blocking_fsync(fd: int) -> None:
        fsync_entered.set()
        release_fsync.wait(timeout=2.0)
        original_fsync(fd)

    monkeypatch.setattr(journal_module.os, "fsync", blocking_fsync)
    outcome: list[object] = []
    completed = threading.Event()

    def append_threshold_event() -> None:
        try:
            outcome.append(writer.append(EventFactory().opened(0)))
        finally:
            completed.set()

    append_thread = threading.Thread(target=append_threshold_event, daemon=True)
    append_thread.start()
    completed_in_budget = completed.wait(timeout=0.5)
    called_in_append = fsync_entered.is_set()
    release_fsync.set()
    append_thread.join(timeout=2.0)
    monkeypatch.setattr(journal_module.os, "fsync", original_fsync)

    assert writer.flush()
    writer.close()
    stored = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]

    assert completed_in_budget, "threshold rotation blocked append on fsync"
    assert not called_in_append, "threshold rotation called fsync from append"
    assert len(outcome) == 1 and outcome[0].accepted
    assert [event["event_id"] for event in stored] == [EventFactory().opened(0)["event_id"]]


def test_append_fails_open_while_flusher_holds_writer_lock(monkeypatch, tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    factory = EventFactory()
    assert writer.append(factory.opened(0)).accepted
    assert writer.flush()

    fsync_entered = threading.Event()
    release_fsync = threading.Event()
    original_fsync = journal_module.os.fsync

    def blocking_fsync(fd: int) -> None:
        if fd == writer._segment_fd:
            fsync_entered.set()
            release_fsync.wait(timeout=2.0)
        original_fsync(fd)

    monkeypatch.setattr(journal_module.os, "fsync", blocking_fsync)
    flush_thread = threading.Thread(target=writer.flush, daemon=True)
    flush_thread.start()
    assert fsync_entered.wait(timeout=1.0)

    outcome: list[object] = []
    completed = threading.Event()

    def append_event() -> None:
        try:
            outcome.append(
                writer.append(
                    factory.contract(
                        "contract.persisted",
                        "completed",
                        1,
                        revision=1,
                        after_sha256="a" * 64,
                    )
                )
            )
        finally:
            completed.set()

    append_thread = threading.Thread(target=append_event, daemon=True)
    append_thread.start()
    completed_in_budget = completed.wait(timeout=0.5)
    release_fsync.set()
    flush_thread.join(timeout=2.0)
    append_thread.join(timeout=2.0)
    monkeypatch.setattr(journal_module.os, "fsync", original_fsync)
    writer.close()

    assert completed_in_budget, "append inherited the flusher's fsync latency"
    assert len(outcome) == 1
    assert not outcome[0].accepted
    assert outcome[0].reason_code == "JOURNAL_BUSY"
    assert outcome[0].coverage_class == "observer_io_failure"


def test_collector_busy_diagnostic_does_not_wait_for_writer_lock_twice(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.writer.open()
    monkeypatch.setattr(journal_module, "APPEND_LOCK_TIMEOUT_S", 0.1)
    monkeypatch.setattr(collector.health, "increment", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(collector.writer, "_validate_append_event", lambda _event: None)

    fsync_entered = threading.Event()
    release_fsync = threading.Event()
    original_fsync = journal_module.os.fsync

    def blocking_fsync(fd: int) -> None:
        if fd == collector.writer._segment_fd:
            fsync_entered.set()
            release_fsync.wait(timeout=2.0)
        original_fsync(fd)

    monkeypatch.setattr(journal_module.os, "fsync", blocking_fsync)
    flush_thread = threading.Thread(target=collector.writer.flush, daemon=True)
    flush_thread.start()
    assert fsync_entered.wait(timeout=1.0)

    event = EventFactory().opened(0)
    started = time.monotonic()
    outcome = collector.emit(event)
    elapsed = time.monotonic() - started
    release_fsync.set()
    flush_thread.join(timeout=2.0)
    monkeypatch.setattr(journal_module.os, "fsync", original_fsync)
    collector.writer.close()

    assert not outcome.accepted and outcome.reason_code == "JOURNAL_BUSY"
    assert elapsed < 0.16, "coverage diagnostic repeated the bounded writer-lock wait"


def test_durable_snapshot_does_not_hold_writer_lock_during_pread(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0)).accepted
    assert writer.flush()

    pread_entered = threading.Event()
    release_pread = threading.Event()
    original_pread = journal_module.os.pread

    def blocking_pread(fd: int, length: int, offset: int) -> bytes:
        pread_entered.set()
        release_pread.wait(timeout=2.0)
        return original_pread(fd, length, offset)

    monkeypatch.setattr(journal_module.os, "pread", blocking_pread)
    snapshot_thread = threading.Thread(target=writer.durable_snapshot, daemon=True)
    snapshot_thread.start()
    assert pread_entered.wait(timeout=1.0)

    append_result: list[object] = []
    append_completed = threading.Event()

    def append_event() -> None:
        try:
            append_result.append(writer.append(EventFactory().opened(1)))
        finally:
            append_completed.set()

    append_thread = threading.Thread(target=append_event, daemon=True)
    append_thread.start()
    completed_in_budget = append_completed.wait(timeout=0.5)
    release_pread.set()
    snapshot_thread.join(timeout=2.0)
    append_thread.join(timeout=2.0)
    writer.close()

    assert completed_in_budget, "snapshot pread retained the writer lock"
    assert len(append_result) == 1 and append_result[0].accepted


def test_oversized_canonical_line_is_rejected_before_any_partial_append(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    event = factory.builder.contract(
        event_type="evidence.added",
        status="reported",
        evidence_refs=tuple(f"evidence-{index:05d}" for index in range(5000)),
        occurred_at=factory.at(0),
    )
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    active = writer.active_segment
    assert active is not None
    outcome = writer.append(event)
    assert not outcome.accepted and outcome.reason_code == "LINE_TOO_LARGE"
    assert outcome.byte_length > MAX_EVENT_LINE_BYTES
    assert active.read_bytes() == b""
    writer.close()


def test_short_write_preserves_torn_source_and_moves_next_append_to_fresh_epoch(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    first = factory.opened(0)
    second = factory.contract(
        "contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64
    )
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    damaged = writer.active_segment
    assert damaged is not None
    monkeypatch.setattr(writer, "_write_all", lambda line: max(1, len(line) // 2))
    outcome = writer.append(first)
    assert not outcome.accepted and outcome.reason_code == "SHORT_WRITE"
    assert writer.producer_epoch != EPOCH
    assert damaged.exists()
    monkeypatch.setattr(writer, "_write_all", JournalWriter._write_all.__get__(writer))
    assert writer.append(second).accepted
    assert writer.close() is not None
    assert any(
        segment.producer_epoch == EPOCH and segment.is_active for segment in list_segments(paths)
    )


def test_retrying_critical_damaged_tail_never_promotes_or_erases_unclean_coverage(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(factory.opened(0), critical=True).accepted
    damaged = writer.active_segment
    assert damaged is not None

    original_write = journal_module.os.write

    def partial_write(descriptor: int, payload: bytes) -> int:
        fragment = payload[: max(1, len(payload) // 2)]
        return original_write(descriptor, fragment)

    monkeypatch.setattr(journal_module.os, "write", partial_write)
    outcome = writer.append(
        factory.contract(
            "contract.persisted",
            "completed",
            1,
            revision=1,
            after_sha256="a" * 64,
        )
    )
    monkeypatch.setattr(journal_module.os, "write", original_write)
    assert not outcome.accepted and outcome.reason_code == "SHORT_WRITE"
    before_retry = read_segment(damaged)
    assert before_retry.trailing_fragment
    assert writer.critical_pending

    assert writer.flush()
    assert not writer.critical_pending
    assert damaged.exists()
    assert read_segment(damaged) == before_retry
    assert epoch_is_unclean(paths, EPOCH)
    assert not list(paths.closed.glob(f"{EPOCH}.*.jsonl"))


def test_enospc_degrades_coverage_without_escaping_into_the_contract_path(
    monkeypatch, tmp_path
) -> None:
    """A full journal is an observer gap, never a Hermes/contract exception."""
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    damaged = writer.active_segment
    assert damaged is not None

    original_write = os.write

    def full_disk(_descriptor, _payload):
        raise OSError(28, "synthetic ENOSPC")

    monkeypatch.setattr(os, "write", full_disk)
    outcome = writer.append(EventFactory().opened(0))
    monkeypatch.setattr(os, "write", original_write)

    assert not outcome.accepted
    assert outcome.reason_code == "SHORT_WRITE"
    assert outcome.coverage_class == "observer_io_failure"
    assert writer.degraded and writer.io_failure_count == 1
    assert damaged.exists()
    # Once storage is available again, capture continues in a fresh producer epoch.
    assert writer.append(EventFactory().opened(1)).accepted
    assert writer.close() is not None


def test_failed_close_fsync_leaves_active_segment_for_unclean_tail_detection(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0)).accepted
    original = os.fsync
    monkeypatch.setattr(
        os, "fsync", lambda _descriptor: (_ for _ in ()).throw(OSError("synthetic"))
    )
    try:
        assert writer.close() is None
    finally:
        monkeypatch.setattr(os, "fsync", original)
    assert epoch_is_unclean(paths, EPOCH)
    assert any(segment.is_active for segment in list_segments(paths))


def test_failed_critical_flush_preserves_urgency_until_successful_retry(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted
    assert writer.critical_pending

    original_fsync = os.fsync
    attempts = 0

    def fail_once(descriptor: int) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("synthetic file fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_once)
    try:
        assert not writer.flush()
        assert writer.critical_pending
        assert writer.flush()
        assert not writer.critical_pending
    finally:
        monkeypatch.setattr(os, "fsync", original_fsync)
        writer.close()


@pytest.mark.skipif(os.name != "posix", reason="dirfd durability is POSIX-only")
def test_critical_flush_rejects_replaced_observations_ancestor(tmp_path: Path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted

    displaced = tmp_path / "displaced-observations"
    replacement = tmp_path / "replacement-observations"
    os.replace(paths.observations, displaced)
    paths.ensure()

    assert not writer.flush(), "a routed replacement directory cannot acknowledge durability"
    assert writer.critical_pending

    os.replace(paths.observations, replacement)
    os.replace(displaced, paths.observations)
    assert writer.flush(), "restoring the inode-bound route makes the debt retryable"
    assert not writer.critical_pending
    assert writer.close() is not None


@pytest.mark.skipif(os.name != "posix", reason="inode-bound snapshots are POSIX-only")
def test_durable_snapshot_rejects_hardlinked_inode_after_ancestor_swap(tmp_path: Path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted
    assert writer.flush()
    source = writer.active_segment
    assert source is not None and writer.durable_snapshot() is not None

    displaced = tmp_path / "displaced-observations"
    replacement = tmp_path / "replacement-observations"
    os.replace(paths.observations, displaced)
    paths.ensure()
    original_source = displaced / source.relative_to(paths.observations)
    os.link(original_source, source)

    assert writer.durable_snapshot() is None

    source.unlink()
    os.replace(paths.observations, replacement)
    os.replace(displaced, paths.observations)
    assert writer.close() is not None


@pytest.mark.skipif(os.name != "posix", reason="dirfd durability is POSIX-only")
def test_critical_close_rejects_spoof_after_observations_ancestor_swap(tmp_path: Path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted
    source = writer.active_segment
    assert source is not None

    displaced = tmp_path / "displaced-observations"
    replacement = tmp_path / "replacement-observations"
    os.replace(paths.observations, displaced)
    paths.ensure()
    source.write_bytes((displaced / source.relative_to(paths.observations)).read_bytes())

    assert writer.close() is None, "close cannot publish a same-name file from a replacement tree"
    assert writer.critical_pending

    os.replace(paths.observations, replacement)
    os.replace(displaced, paths.observations)
    assert writer.flush(), "the original inode remains available for supervised durability retry"
    assert not writer.critical_pending


@pytest.mark.skipif(os.name != "posix", reason="dirfd mutation fencing is POSIX-only")
def test_close_never_moves_spoof_when_ancestor_swaps_at_publish(
    monkeypatch, tmp_path: Path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted
    source = writer.active_segment
    assert source is not None

    displaced = tmp_path / "displaced-observations"
    replacement = tmp_path / "replacement-observations"
    sentinel = b"replacement-tree-spoof-must-not-move"
    original_replace = journal_module.os.replace
    swapped = False

    def swap_at_publish(source_arg, target_arg, *args, **kwargs) -> None:
        nonlocal swapped
        if not swapped and Path(os.fspath(target_arg)).name.endswith(".jsonl"):
            os.replace(paths.observations, displaced)
            paths.ensure()
            (paths.active / source.name).write_bytes(sentinel)
            swapped = True
        original_replace(source_arg, target_arg, *args, **kwargs)

    monkeypatch.setattr(journal_module.os, "replace", swap_at_publish)
    assert writer.close() is None
    assert swapped and writer.critical_pending
    assert (paths.active / source.name).read_bytes() == sentinel
    assert not list(paths.closed.glob("*.jsonl"))

    monkeypatch.setattr(journal_module.os, "replace", original_replace)
    os.replace(paths.observations, replacement)
    os.replace(displaced, paths.observations)
    assert writer.flush()
    assert not writer.critical_pending


def test_rotated_segment_fsync_debt_survives_later_segment_flush(monkeypatch, tmp_path) -> None:
    """A new segment cannot acknowledge durability the failed old segment never got."""
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(
        paths=paths,
        producer_epoch=EPOCH,
        max_segment_events=1,
    )
    writer.open()
    original_fsync = os.fsync
    failed_descriptor: int | None = None

    def fail_first_segment_once(descriptor: int) -> None:
        nonlocal failed_descriptor
        if failed_descriptor is None:
            failed_descriptor = descriptor
            raise OSError("synthetic rotated segment fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(
        "aether_agents.observation.capture.journal.os.fsync",
        fail_first_segment_once,
    )
    try:
        assert writer.append(EventFactory().opened(0), critical=True).accepted
        assert writer.critical_pending
        assert not writer.flush(), "overall flush must report the unresolved older durability debt"
        assert writer.critical_pending, (
            "a later segment flush falsely acknowledged an older undurable critical event"
        )
        assert writer.degraded and writer.io_failure_count == 1
    finally:
        writer.close()


def test_deferred_rotation_keeps_critical_debt_when_rename_directory_fsync_fails(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(
        paths=paths,
        producer_epoch=EPOCH,
        max_segment_events=1,
    )
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted
    assert writer.critical_pending

    original_directory_fsync = writer._fsync_directory
    directory_fsync_calls = 0

    def fail_rotation_directory_fsync(directory) -> None:
        nonlocal directory_fsync_calls
        directory_fsync_calls += 1
        if directory_fsync_calls == 2:
            raise OSError("synthetic rotation directory fsync failure")
        original_directory_fsync(directory)

    monkeypatch.setattr(writer, "_fsync_directory", fail_rotation_directory_fsync)
    assert not writer.flush()
    assert writer.critical_pending
    assert writer.degraded and writer.io_failure_count == 1

    monkeypatch.setattr(writer, "_fsync_directory", original_directory_fsync)
    assert writer.flush(), "a supervised retry must durably clear the older segment debt"
    assert not writer.critical_pending
    writer.close()


def test_supervised_flush_retries_rotated_critical_debt_with_no_follow(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(
        paths=paths,
        producer_epoch=EPOCH,
        max_segment_events=1,
    )
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted

    original_directory_fsync = writer._fsync_directory
    directory_fsync_calls = 0

    def fail_closed_directory_once(directory) -> None:
        nonlocal directory_fsync_calls
        directory_fsync_calls += 1
        if directory_fsync_calls == 2:
            raise OSError("synthetic closed-directory fsync failure")
        original_directory_fsync(directory)

    monkeypatch.setattr(writer, "_fsync_directory", fail_closed_directory_once)
    assert not writer.flush()
    assert writer.critical_pending
    debt_path = next(paths.closed.glob("*.jsonl"))

    monkeypatch.setattr(writer, "_fsync_directory", original_directory_fsync)
    writer.close()  # Close the empty successor; only the older debt remains.

    original_open = journal_module.os.open
    retry_open_flags: list[int] = []
    retried_directories: list[object] = []

    def record_open(path, flags, mode=0o777, *, dir_fd=None):
        if Path(path).name == debt_path.name and dir_fd is not None:
            retry_open_flags.append(flags)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def record_directory_fsync(directory) -> None:
        retried_directories.append(directory)
        original_directory_fsync(directory)

    monkeypatch.setattr(journal_module.os, "open", record_open)
    monkeypatch.setattr(writer, "_fsync_directory", record_directory_fsync)

    assert writer.flush()
    assert not writer.critical_pending
    assert retry_open_flags
    assert retry_open_flags[0] & getattr(os, "O_NOFOLLOW", 0)
    assert paths.closed in retried_directories
    assert paths.active in retried_directories


def test_critical_debt_follows_verified_inode_from_active_to_closed(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted
    source = writer.active_segment
    assert source is not None
    expected_identity = (source.stat().st_dev, source.stat().st_ino)

    original_fsync = journal_module.os.fsync
    monkeypatch.setattr(
        journal_module.os,
        "fsync",
        lambda _descriptor: (_ for _ in ()).throw(OSError("synthetic file fsync failure")),
    )
    assert writer.close() is None
    assert writer.critical_pending
    monkeypatch.setattr(journal_module.os, "fsync", original_fsync)

    target = paths.closed / f"{EPOCH}.0-0.jsonl"
    os.replace(source, target)
    assert (target.stat().st_dev, target.stat().st_ino) == expected_identity

    retried_directories: list[object] = []
    original_directory_fsync = writer._fsync_directory

    def record_directory_fsync(directory) -> None:
        retried_directories.append(directory)
        original_directory_fsync(directory)

    monkeypatch.setattr(writer, "_fsync_directory", record_directory_fsync)
    assert writer.flush()
    assert not writer.critical_pending
    assert paths.closed in retried_directories
    assert paths.active in retried_directories
    assert writer.flush(), "a completed debt retry must remain idempotent"


def test_critical_debt_retry_rejects_replaced_path_and_repeated_fsync_failure(
    monkeypatch,
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(
        paths=paths,
        producer_epoch=EPOCH,
        max_segment_events=1,
    )
    writer.open()
    assert writer.append(EventFactory().opened(0), critical=True).accepted

    original_directory_fsync = writer._fsync_directory
    directory_fsync_calls = 0

    def fail_closed_directory_once(directory) -> None:
        nonlocal directory_fsync_calls
        directory_fsync_calls += 1
        if directory_fsync_calls == 2:
            raise OSError("synthetic closed-directory fsync failure")
        original_directory_fsync(directory)

    monkeypatch.setattr(writer, "_fsync_directory", fail_closed_directory_once)
    assert not writer.flush()
    debt_path = next(paths.closed.glob("*.jsonl"))
    monkeypatch.setattr(writer, "_fsync_directory", original_directory_fsync)
    writer.close()

    preserved = paths.closed / "preserved-original"
    os.replace(debt_path, preserved)
    debt_path.symlink_to(paths.locks)
    assert not writer.flush(), "a replaced path must never acknowledge the original inode"
    assert writer.critical_pending
    assert debt_path.is_symlink()

    debt_path.unlink()
    os.replace(preserved, debt_path)
    original_fsync = journal_module.os.fsync
    failed_retries = 0

    def fail_expected_inode(descriptor: int) -> None:
        nonlocal failed_retries
        opened = os.fstat(descriptor)
        expected = debt_path.stat()
        if (opened.st_dev, opened.st_ino) == (expected.st_dev, expected.st_ino):
            failed_retries += 1
            raise OSError("synthetic repeated debt fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(journal_module.os, "fsync", fail_expected_inode)
    assert not writer.flush()
    assert writer.critical_pending
    assert failed_retries == 1

    monkeypatch.setattr(journal_module.os, "fsync", original_fsync)
    assert writer.flush()
    assert not writer.critical_pending


def test_critical_append_wakes_flusher_without_waiting_for_ordinary_interval(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    flushed = threading.Event()
    original_flush = writer.flush

    def observed_flush() -> bool:
        result = original_flush()
        flushed.set()
        return result

    monkeypatch.setattr(writer, "flush", observed_flush)
    flusher = Flusher(
        writer=writer,
        interval_s=10.0,
        critical_interval_s=0.01,
        teardown_timeout_s=0.1,
    )
    flusher.start()
    try:
        assert writer.append(EventFactory().opened(0), critical=True).accepted
        assert flushed.wait(0.75), "critical append did not wake the sleeping flusher"
    finally:
        flusher.stop()
        writer.close()


def test_flusher_stop_is_bounded_when_final_fsync_is_blocked() -> None:
    release = threading.Event()

    class BlockedWriter:
        critical_pending = False

        @staticmethod
        def flush() -> bool:
            release.wait()
            return True

    flusher = Flusher(
        writer=BlockedWriter(),  # type: ignore[arg-type]
        interval_s=60.0,
        teardown_timeout_s=0.05,
    )
    flusher.start()
    stopper = threading.Thread(target=flusher.stop, daemon=True)
    started = time.monotonic()
    stopper.start()
    try:
        stopper.join(0.3)
        assert not stopper.is_alive(), "stop retried a blocked fsync synchronously"
        assert time.monotonic() - started < 0.3
        assert flusher.stats.final_flush_attempted
        assert not flusher.stats.final_flush_succeeded
    finally:
        release.set()
        stopper.join(1.0)


def test_live_epoch_lock_prevents_false_unclean_diagnostic(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    try:
        assert writer.append(EventFactory().opened(0)).accepted
        assert not epoch_is_unclean(paths, EPOCH)
    finally:
        writer.close()


@pytest.mark.skipif(os.name != "posix", reason="dirfd lock fencing is POSIX-only")
def test_epoch_lock_open_rejects_observations_ancestor_swap(monkeypatch, tmp_path: Path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    paths.ensure()
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    lock_path = paths.lock_file(EPOCH)
    displaced = tmp_path / "displaced-observations"
    replacement = tmp_path / "replacement-observations"
    original_open = journal_module.os.open
    swapped = False

    def swap_before_lock_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if not swapped and Path(os.fspath(path)).name == lock_path.name:
            os.replace(paths.observations, displaced)
            paths.ensure()
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(journal_module.os, "open", swap_before_lock_open)
    try:
        with pytest.raises(UnsafeObservationPath):
            writer.open()
        assert swapped
        assert not lock_path.exists(), "the replaced tree must never receive the producer lock"
    finally:
        monkeypatch.setattr(journal_module.os, "open", original_open)
        if writer.active_segment is not None:
            writer.close()
        os.replace(paths.observations, replacement)
        os.replace(displaced, paths.observations)


@pytest.mark.skipif(os.name != "posix", reason="dirfd lock fencing is POSIX-only")
def test_epoch_diagnostic_cannot_follow_ancestor_swap_to_an_unlocked_lock(
    monkeypatch, tmp_path: Path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0)).accepted
    lock_path = paths.lock_file(EPOCH)
    displaced = tmp_path / "displaced-observations"
    replacement = tmp_path / "replacement-observations"
    original_open = journal_module.os.open
    swapped = False

    def swap_before_diagnostic_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if not swapped and Path(os.fspath(path)).name == lock_path.name:
            os.replace(paths.observations, displaced)
            paths.ensure()
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(journal_module.os, "open", swap_before_diagnostic_open)
    try:
        assert not epoch_is_unclean(paths, EPOCH)
        assert swapped
    finally:
        monkeypatch.setattr(journal_module.os, "open", original_open)
        os.replace(paths.observations, replacement)
        os.replace(displaced, paths.observations)
        writer.close()


def test_two_producers_create_independent_segments_without_global_sequence(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    epochs = ("prd_" + "4" * 32, "prd_" + "5" * 32)
    writers = [JournalWriter(paths=paths, producer_epoch=epoch) for epoch in epochs]
    for writer in writers:
        writer.open()
        assert writer.append(EventFactory().opened(0)).producer_seq == 0
    for writer in writers:
        writer.close()
    assert {segment.producer_epoch for segment in list_segments(paths)} == set(epochs)


def test_incremental_ingest_is_idempotent_and_reduction_retains_summary(tmp_path) -> None:
    paths, _ = _write_closed_segment(tmp_path)
    first = ingest_pending(paths)
    second = ingest_pending(paths)
    assert first.events_inserted == 2
    assert second.events_inserted == 0 and second.lines_seen == 0
    summary = reduce_trace(paths, TRACE_ID)
    assert summary["source_event_count"] == 2
    assert (paths.summaries / f"{summary['summary_id']}.json").is_file()
    with ReadModel.open(paths) as model:
        assert model.latest_summary(TRACE_ID)["summary_id"] == summary["summary_id"]


@pytest.mark.skipif(os.name != "posix", reason="link confinement uses POSIX inode semantics")
@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_ingest_rejects_linked_segment_outside_project_without_reading_it(
    tmp_path, link_kind
) -> None:
    _, external_segment = _write_closed_segment(tmp_path / "outside")
    external = external_segment.path
    before = external.read_bytes()

    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "target")
    paths.ensure()
    linked = paths.closed / external.name
    if link_kind == "symlink":
        linked.symlink_to(external)
    else:
        os.link(external, linked)

    report = ingest_pending(paths)

    assert report.segments_seen == 1
    assert report.events_inserted == 0
    assert report.corrupt_segments == 1
    assert external.read_bytes() == before
    with ReadModel.open(paths) as model:
        assert model.events_for_trace(TRACE_ID) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX component-wise no-follow confinement")
def test_journal_listing_and_read_reject_symlinked_state_ancestor(tmp_path: Path) -> None:
    state = tmp_path / "state"
    paths, segment = _write_closed_segment(state)
    external_state = tmp_path / "external-state"
    state.rename(external_state)
    state.symlink_to(external_state, target_is_directory=True)
    external_segment = external_state / segment.path.relative_to(state)
    external_bytes = external_segment.read_bytes()

    with pytest.raises(UnsafeObservationPath):
        list_segments(paths)
    with pytest.raises(UnsafeObservationPath):
        read_segment(segment.path)

    assert external_segment.read_bytes() == external_bytes


def test_journal_sqlite_reduce_trace_uses_coherent_active_release_authority(
    tmp_path,
) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    fixture = complete_trace()
    paths, _ = _write_closed_segment(state_root, events=fixture.events)

    report = ingest_pending(paths)
    assert report.events_inserted == len(fixture.events)
    summary = reduce_trace(paths, TRACE_ID)

    assert summary["completion_state"] == "completed"
    assert "AUTHORITY_CONTEXT_UNAVAILABLE" not in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_checkpoint_sink_resolves_morfeo_from_coherent_active_release(tmp_path) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        result = CheckpointSink(collector).emit(
            "contract_completion_verified",
            trace_id=TRACE_ID,
            contract_id="contract-1",
            evidence_refs=("evidence/result.json",),
        )
        assert result.accepted
    finally:
        collector.stop()

    events = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        event["event_type"] == "contract.completion_verified"
        and event["actor"]["profile"] == "morfeo"
        for event in events
    )


def test_checkpoint_sink_derives_review_authority_from_durable_native_assignment(
    tmp_path,
) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    factory = EventFactory()
    assignment = factory.unit(
        "work_unit.bound",
        "reported",
        2,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    assert assignment["source_kind"] == "hermes_hook"
    assert assignment["actor"]["role"] is None
    assert assignment["work_unit"]["required"] is None
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    native_collector = Collector(
        paths=paths,
        runtime_fingerprint="3" * 64,
        producer_epoch="prd_" + "f" * 32,
    )
    native_collector.start()
    try:
        assert native_collector.emit(assignment).accepted
    finally:
        native_collector.stop()
    assert any(segment.state == "closed" for segment in list_segments(paths))

    classification_collector = Collector(
        paths=paths,
        runtime_fingerprint="3" * 64,
        producer_epoch="prd_" + "e" * 32,
    )
    classification_collector.start()
    try:
        classified = CheckpointSink(classification_collector).emit(
            "work_unit_classified",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            relation="review",
            required=True,
            occurred_at=factory.at(2),
        )
        assert classified.accepted
    finally:
        classification_collector.stop()
    classification_event = next(
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["event_type"] == "work_unit.bound"
        and json.loads(line)["source_kind"] == "aether_checkpoint"
    )
    assert classification_event["parent_event_id"] == assignment["event_id"]

    collector = Collector(
        paths=paths,
        runtime_fingerprint="3" * 64,
        producer_epoch="prd_" + "0" * 32,
    )
    collector.start()
    try:
        sink = CheckpointSink(collector)
        requested = sink.emit(
            "review_requested",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            relation="review",
            required=True,
            occurred_at=factory.at(2),
        )
        assert requested.accepted
        assert collector.writer.flush()
        forged = sink.emit(
            "review_approved",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            profile="morfeo",
            role="verification",
        )
        assert not forged.accepted
        assert forged.reason_code == "CHECKPOINT_REFERENCE_UNKNOWN"
        result = sink.emit(
            "review_approved",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            occurred_at=factory.at(2),
        )
        assert result.accepted
    finally:
        collector.stop()

    events = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]
    approved = next(event for event in events if event["event_type"] == "review.approved")
    requested_event = next(event for event in events if event["event_type"] == "review.requested")
    assert approved["actor"] == {
        "kind": "agent",
        "id": "supervisor",
        "profile": "supervisor",
        "role": "supervision",
    }
    assert requested_event["parent_event_id"] == classification_event["event_id"]
    assert approved["parent_event_id"] == requested_event["event_id"]
    ingest = ingest_pending(paths)
    with ReadModel.open(paths) as model:
        assert "EVENT_IDENTITY_COLLISION" not in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }
        stored_bindings = [
            event
            for event in model.events_for_trace(TRACE_ID)
            if event["event_type"] == "work_unit.bound"
        ]
        assert len(stored_bindings) == 2
        assert any(
            event["source_kind"] == "hermes_hook"
            and event["actor"]["profile"] == "supervisor"
            and event["actor"]["role"] is None
            for event in stored_bindings
        )
        assert any(
            event["source_kind"] == "aether_checkpoint"
            and event["work_unit"]["relation"] == "review"
            and event["work_unit"]["required"] is True
            for event in stored_bindings
        )
        projected = model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE trace_id=? AND task_ref=?",
            (TRACE_ID, "review-unit"),
        ).fetchone()
        assert projected == ("review", 1)
    assert ingest.corrupt_segments == 0
    summary = reduce_trace(paths, TRACE_ID)
    review = next(
        unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "review-unit"
    )
    assert review["relation"] == "review"
    assert review["required"] is True
    assert review["review_state"] == "approved"

    causal_events = [
        event
        for event in events
        if event["event_type"] in {"work_unit.bound", "review.requested", "review.approved"}
    ]
    permutation_summaries = [
        reduce_events(
            ReductionInput(
                trace_id=TRACE_ID,
                project_id=PROJECT_ID,
                events=deepcopy(list(order)),
                producer_count=3,
                authority_context=AuthorityContext.for_active_release("test-release"),
            )
        )
        for order in permutations(causal_events)
    ]
    assert len({candidate["summary_id"] for candidate in permutation_summaries}) == 1
    assert all(
        candidate["work_graph"]["units"][0]["review_state"] == "approved"
        for candidate in permutation_summaries
    )


def test_checkpoint_sink_uses_only_fsynced_active_evidence_without_rotation(
    tmp_path,
) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    factory = EventFactory()
    assignment = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        assert collector.emit(assignment).accepted
        assert collector.writer.flush()
        sink = CheckpointSink(collector)
        assert sink.emit(
            "work_unit_classified",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            relation="review",
            required=True,
            occurred_at=factory.at(2),
        ).accepted
        assert collector.writer.flush()
        assert sink.emit(
            "review_requested",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            occurred_at=factory.at(3),
        ).accepted
        assert collector.writer.flush()
        assert sink.emit(
            "review_approved",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            occurred_at=factory.at(4),
        ).accepted
    finally:
        collector.stop()

    events = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]
    native = next(
        event
        for event in events
        if event["event_type"] == "work_unit.bound" and event["source_kind"] == "hermes_hook"
    )
    classified = next(
        event
        for event in events
        if event["event_type"] == "work_unit.bound" and event["source_kind"] == "aether_checkpoint"
    )
    requested = next(event for event in events if event["event_type"] == "review.requested")
    approved = next(event for event in events if event["event_type"] == "review.approved")
    assert classified["parent_event_id"] == native["event_id"]
    assert requested["parent_event_id"] == classified["event_id"]
    assert approved["parent_event_id"] == requested["event_id"]


def test_checkpoint_sink_never_uses_unflushed_active_assignment(tmp_path) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    assignment = EventFactory().unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.writer.open()
    try:
        assert collector.emit(assignment).accepted
        result = CheckpointSink(collector).emit(
            "work_unit_classified",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            relation="review",
            required=True,
        )
        assert not result.accepted
        assert result.reason_code == "CHECKPOINT_AUTHORITY_UNVERIFIED"
    finally:
        collector.writer.close()


def test_checkpoint_sink_fails_open_while_active_fsync_holds_writer_lock(
    tmp_path,
    monkeypatch,
) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    factory = EventFactory()
    assignment = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.writer.open()
    assert collector.emit(assignment).accepted
    assert collector.writer.flush()

    fsync_entered = threading.Event()
    release_fsync = threading.Event()
    original_fsync = journal_module.os.fsync

    def blocking_fsync(fd: int) -> None:
        if fd == collector.writer._segment_fd:
            fsync_entered.set()
            release_fsync.wait(timeout=2.0)
        original_fsync(fd)

    monkeypatch.setattr(journal_module.os, "fsync", blocking_fsync)
    flush_thread = threading.Thread(target=collector.writer.flush, daemon=True)
    flush_thread.start()
    assert fsync_entered.wait(timeout=1.0)

    result: list[object] = []
    completed = threading.Event()

    def emit_checkpoint() -> None:
        try:
            result.append(
                CheckpointSink(collector).emit(
                    "work_unit_classified",
                    trace_id=TRACE_ID,
                    task_ref="review-unit",
                    binding_ref="bnd_review_unit_0123456789abcdef",
                    relation="review",
                    required=True,
                )
            )
        finally:
            completed.set()

    checkpoint_thread = threading.Thread(target=emit_checkpoint, daemon=True)
    checkpoint_thread.start()
    completed_in_budget = completed.wait(timeout=0.5)
    release_fsync.set()
    flush_thread.join(timeout=2.0)
    checkpoint_thread.join(timeout=2.0)
    collector.writer.close()

    assert completed_in_budget, "checkpoint waited for the writer lock held by fsync"
    assert len(result) == 1
    assert not result[0].accepted
    assert result[0].reason_code == "CHECKPOINT_AUTHORITY_UNVERIFIED"


@pytest.mark.parametrize("classification_first", (False, True))
def test_exact_classification_never_rebinds_a_native_unbound_unit(
    tmp_path,
    classification_first: bool,
) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    factory = EventFactory()
    assignment = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    unbound = factory.unit(
        "work_unit.unbound",
        "reported",
        2,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )

    native_epoch = "prd_" + ("2" if classification_first else "1") * 32
    classification_epoch = "prd_" + ("1" if classification_first else "2") * 32

    def persist_native() -> None:
        native_collector = Collector(
            paths=paths,
            runtime_fingerprint="3" * 64,
            producer_epoch=native_epoch,
        )
        native_collector.start()
        try:
            assert native_collector.emit(assignment).accepted
            assert native_collector.emit(unbound).accepted
        finally:
            native_collector.stop()

    def persist_classification() -> None:
        classification_collector = Collector(
            paths=paths,
            runtime_fingerprint="3" * 64,
            producer_epoch=classification_epoch,
        )
        classification_collector.start()
        try:
            assert (
                CheckpointSink(classification_collector)
                .emit(
                    "work_unit_classified",
                    trace_id=TRACE_ID,
                    task_ref="review-unit",
                    binding_ref="bnd_review_unit_0123456789abcdef",
                    relation="review",
                    required=True,
                    occurred_at=factory.at(3),
                )
                .accepted
            )
        finally:
            classification_collector.stop()

    # Product classification needs the durable native fact before it can be emitted.
    # The producer epochs deliberately make ingestion visit the two segments in either
    # order, proving projection is not last-ingest-wins.
    persist_native()
    persist_classification()

    approval_collector = Collector(
        paths=paths,
        runtime_fingerprint="3" * 64,
        producer_epoch="prd_" + "3" * 32,
    )
    approval_collector.start()
    try:
        approval = CheckpointSink(approval_collector).emit(
            "review_approved",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
            occurred_at=factory.at(4),
        )
        assert not approval.accepted
        assert approval.reason_code == "CHECKPOINT_AUTHORITY_UNVERIFIED"
    finally:
        approval_collector.stop()

    ingest = ingest_pending(paths)
    assert ingest.corrupt_segments == 0
    with ReadModel.open(paths) as model:
        projected = model._conn.execute(
            "SELECT relation, required, bound_at, unbound_at FROM bound_work_unit "
            "WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone()
        assert projected == (
            "review",
            1,
            assignment["occurred_at"],
            unbound["occurred_at"],
        )
        [classification_event] = [
            event
            for event in model.events_for_trace(TRACE_ID)
            if event["event_type"] == "work_unit.bound"
            and event["source_kind"] == "aether_checkpoint"
        ]
        assert classification_event["parent_event_id"] == unbound["event_id"]
    summary = reduce_trace(paths, TRACE_ID)
    assert all(unit["task_ref"] != "review-unit" for unit in summary["work_graph"]["units"])
    assert "UNBOUND_WORK_UNIT_OBSERVED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


@pytest.mark.parametrize(
    "conflict",
    (
        "missing_classification",
        "native_unbound",
        "binding",
        "classification",
        "principal",
        "native_relation",
        "native_required",
    ),
)
def test_checkpoint_sink_rejects_conflicting_durable_review_evidence(
    tmp_path,
    conflict: str,
) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    factory = EventFactory()
    native_events = [
        factory.unit(
            "work_unit.bound",
            "reported",
            1,
            task_ref="review-unit",
            relation="root" if conflict == "native_relation" else "unknown",
            required=False if conflict == "native_required" else None,
            actor_id="supervisor",
            profile="supervisor",
        )
    ]
    if conflict == "native_unbound":
        native_events.append(
            factory.unit(
                "work_unit.unbound",
                "reported",
                2,
                task_ref="review-unit",
                relation="unknown",
                required=None,
                actor_id="supervisor",
                profile="supervisor",
            )
        )
    elif conflict == "binding":
        native_events.append(
            factory.add(
                factory.builder.work_unit(
                    event_type="work_unit.bound",
                    status="reported",
                    task_ref="review-unit",
                    relation="unknown",
                    required=None,
                    binding="bnd_review_other_0123456789abcdef",
                    occurred_at=factory.at(2),
                    actor_kind="agent",
                    actor_id="supervisor",
                    profile="supervisor",
                    source_kind="hermes_hook",
                )
            )
        )
    elif conflict == "principal":
        native_events.append(
            factory.unit(
                "work_unit.bound",
                "reported",
                2,
                task_ref="review-unit",
                relation="unknown",
                required=None,
                actor_id="morfeo",
                profile="morfeo",
            )
        )

    native_collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    native_collector.start()
    try:
        for event in native_events:
            assert native_collector.emit(event).accepted
    finally:
        native_collector.stop()

    if conflict != "missing_classification":
        classification_collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
        classification_collector.start()
        try:
            sink = CheckpointSink(classification_collector)
            if conflict == "classification":
                assert sink.emit(
                    "work_unit_classified",
                    trace_id=TRACE_ID,
                    task_ref="review-unit",
                    binding_ref="bnd_review_unit_0123456789abcdef",
                    relation="implementation",
                    required=True,
                ).accepted
            classification_result = sink.emit(
                "work_unit_classified",
                trace_id=TRACE_ID,
                task_ref="review-unit",
                binding_ref="bnd_review_unit_0123456789abcdef",
                relation="review",
                required=True,
            )
            if conflict == "binding":
                assert not classification_result.accepted
                assert classification_result.reason_code == "CHECKPOINT_AUTHORITY_UNVERIFIED"
            else:
                assert classification_result.accepted
        finally:
            classification_collector.stop()

    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        result = CheckpointSink(collector).emit(
            "review_approved",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            binding_ref="bnd_review_unit_0123456789abcdef",
        )
        assert not result.accepted
        assert result.reason_code == "CHECKPOINT_AUTHORITY_UNVERIFIED"
    finally:
        collector.stop()

    if conflict in {"native_relation", "native_required"}:
        ingest = ingest_pending(paths)
        assert ingest.corrupt_segments == 0
        with ReadModel.open(paths, authority_context=AuthorityContext.product_default()) as model:
            projected = model._conn.execute(
                "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
                ("bnd_review_unit_0123456789abcdef",),
            ).fetchone()
            assert projected == ("unknown", None)
        summary = reduce_trace(paths, TRACE_ID)
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
        assert "NATIVE_IDENTITY_CONFLICT" in reasons
        assert "EVENT_IDENTITY_COLLISION" not in reasons
        [unit] = summary["work_graph"]["units"]
        assert unit["relation"] == "unknown"
        assert unit["required"] is None


def test_event_and_all_derivations_roll_back_before_diagnostic_then_replay_repairs(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    event = EventFactory().opened(0)
    with ReadModel.open(paths) as model:
        original_derive = model._derive

        def fail_after_partial_derive(candidate) -> None:
            original_derive(candidate)
            raise RuntimeError("private derive detail must not persist")

        monkeypatch.setattr(model, "_derive", fail_after_partial_derive)
        with pytest.raises(RuntimeError):
            model.upsert_event(event)

        for table in ("observation_event", "observation_trace", "participant_contribution"):
            assert model._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

        assert model.record_derived_gap(
            diagnostic_id="dia_" + "1" * 64,
            trace_id=TRACE_ID,
            coverage_class="corrupt_segment",
            reason_code="EVENT_DERIVATION_FAILED",
            event_ref=event["event_id"],
        )
        assert model._conn.execute("SELECT COUNT(*) FROM derived_diagnostic").fetchone()[0] == 1
        assert model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0] == 0

        monkeypatch.setattr(model, "_derive", original_derive)
        assert model.upsert_event(event)
        assert model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0] == 1
        assert model._conn.execute("SELECT COUNT(*) FROM observation_trace").fetchone()[0] == 1


def test_successful_single_event_replay_clears_only_its_transient_derivation_gap(
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    repaired = factory.opened(0)
    unrelated = factory.contract(
        "contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64
    )
    repaired_diagnostic = "dia_" + "1" * 64
    unrelated_reason = "dia_" + "2" * 64
    unrelated_event = "dia_" + "3" * 64

    with ReadModel.open(paths) as model:
        assert model.record_derived_gap(
            diagnostic_id=repaired_diagnostic,
            trace_id=TRACE_ID,
            coverage_class="corrupt_segment",
            reason_code="EVENT_DERIVATION_FAILED",
            event_ref=repaired["event_id"],
        )
        assert model.record_derived_gap(
            diagnostic_id=unrelated_reason,
            trace_id=TRACE_ID,
            coverage_class="corrupt_segment",
            reason_code="EVENT_STORAGE_FAILED",
            event_ref=repaired["event_id"],
        )
        assert model.record_derived_gap(
            diagnostic_id=unrelated_event,
            trace_id=TRACE_ID,
            coverage_class="corrupt_segment",
            reason_code="EVENT_DERIVATION_FAILED",
            event_ref=unrelated["event_id"],
        )

        assert model.upsert_event(repaired)

        remaining = {
            row[0]
            for row in model._conn.execute(
                "SELECT diagnostic_id FROM derived_diagnostic ORDER BY diagnostic_id"
            )
        }
        assert repaired_diagnostic not in remaining
        assert remaining == {unrelated_reason, unrelated_event}


def test_replay_detects_legacy_raw_row_without_derivation_and_rebuilds_projection(
    tmp_path,
) -> None:
    event = EventFactory().opened(0)
    paths, _segment = _write_closed_segment(tmp_path, events=[event])
    with ReadModel.open(paths) as model:
        assert model._insert_event_row(event)
        model._conn.commit()
        assert model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0] == 1
        assert model._conn.execute("SELECT COUNT(*) FROM observation_trace").fetchone()[0] == 0

    report = ingest_pending(paths)
    assert report.events_inserted == 1
    with ReadModel.open(paths) as model:
        assert model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0] == 1
        assert model._conn.execute("SELECT COUNT(*) FROM observation_trace").fetchone()[0] == 1


def test_bulk_event_ingest_isolates_one_failure_and_replay_repairs_it(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    first = factory.opened(0)
    second = factory.contract(
        "contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64
    )
    third = factory.contract("contract.executable", "passed", 2, semantic_delta="invariant")
    with ReadModel.open(paths) as model:
        original_derive = model._derive

        def fail_second(candidate) -> None:
            original_derive(candidate)
            if candidate["event_id"] == second["event_id"]:
                raise RuntimeError("private failure detail must not persist")

        monkeypatch.setattr(model, "_derive", fail_second)
        assert model.upsert_events((first, second, third)) == 2
        assert [event["event_id"] for event in model.events_for_trace(TRACE_ID)] == [
            first["event_id"],
            third["event_id"],
        ]
        assert "EVENT_DERIVATION_FAILED" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }
        projection_bytes = b"".join(
            candidate.read_bytes()
            for candidate in paths.projection_files(READ_MODEL_SCHEMA)
            if candidate.exists()
        )
        assert b"private failure detail must not persist" not in projection_bytes

        monkeypatch.setattr(model, "_derive", original_derive)
        assert model.upsert_events((first, second, third)) == 1
        assert {event["event_id"] for event in model.events_for_trace(TRACE_ID)} == {
            first["event_id"],
            second["event_id"],
            third["event_id"],
        }
        assert "EVENT_DERIVATION_FAILED" not in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_bulk_event_ingest_commits_valid_invalid_valid_and_replay_repairs_validation(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    first = factory.opened(0)
    rejected = factory.contract(
        "contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64
    )
    third = factory.contract("contract.executable", "passed", 2, semantic_delta="invariant")
    original_validate = storage_module.validate_event

    def reject_middle(candidate) -> None:
        if candidate["event_id"] == rejected["event_id"]:
            raise ValueError("private validation detail must not persist")
        original_validate(candidate)

    with ReadModel.open(paths) as model:
        monkeypatch.setattr(storage_module, "validate_event", reject_middle)
        assert model.upsert_events((first, rejected, third)) == 2
        assert [event["event_id"] for event in model.events_for_trace(TRACE_ID)] == [
            first["event_id"],
            third["event_id"],
        ]
        assert "EVENT_VALIDATION_FAILED" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }
        projection_bytes = b"".join(
            candidate.read_bytes()
            for candidate in paths.projection_files(READ_MODEL_SCHEMA)
            if candidate.exists()
        )
        assert b"private validation detail must not persist" not in projection_bytes

        monkeypatch.setattr(storage_module, "validate_event", original_validate)
        assert model.upsert_events((first, rejected, third)) == 1
        assert {event["event_id"] for event in model.events_for_trace(TRACE_ID)} == {
            first["event_id"],
            rejected["event_id"],
            third["event_id"],
        }
        assert "EVENT_VALIDATION_FAILED" not in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_ingest_classifies_unexpected_upcast_failure_without_copying_exception_text(
    monkeypatch, tmp_path
) -> None:
    paths, _segment = _write_closed_segment(tmp_path, events=[EventFactory().opened(0)])

    def explode(_raw):
        raise ValueError("do-not-copy-private-upcast-detail")

    monkeypatch.setattr(ingest_module, "upcast_event", explode)
    report = ingest_pending(paths)
    assert report.events_inserted == 0
    assert report.corrupt_segments == 1
    with ReadModel.open(paths) as model:
        assert "EVENT_UPCAST_FAILED" in {gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)}
    projection_bytes = b"".join(
        child.read_bytes() for child in paths.projections.iterdir() if child.is_file()
    )
    assert b"do-not-copy-private-upcast-detail" not in projection_bytes


def test_upcaster_transform_exception_has_stable_content_free_classification(monkeypatch) -> None:
    raw = EventFactory().opened(0)
    raw["schema_version"] = "aether.observation.event.v0"

    def explode(_event):
        raise ValueError("do-not-copy-transform-detail")

    monkeypatch.setitem(upcast_module._UPCASTERS, raw["schema_version"], explode)
    result = upcast_module.upcast_event(raw)
    assert result.status == "malformed"
    assert result.reason_code == "UPCAST_FAILED"
    assert "do-not-copy" not in repr(result)


def test_corrupt_line_stops_at_valid_prefix_and_never_mutates_source(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    with segment.path.open("ab") as handle:
        handle.write(b'{"malformed":\n')
    before = segment.path.read_bytes()
    report = ingest_pending(paths)
    after = segment.path.read_bytes()
    assert report.events_inserted == 2 and report.corrupt_segments == 1
    assert sha256_hex(before) == sha256_hex(after)
    with ReadModel.open(paths) as model:
        assert "SEGMENT_LINE_MALFORMED" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_unknown_newer_schema_is_quarantined_by_byte_range_without_rewrite(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path).ensure()
    event = EventFactory().opened(0)
    event["schema_version"] = "aether.observation.event.v999"
    line = canonical_json_bytes(event) + b"\n"
    source = paths.closed / f"{EPOCH}.0-0.jsonl"
    source.write_bytes(line)
    before = source.read_bytes()
    report = ingest_pending(paths)
    assert report.quarantined_events == 1 and report.events_inserted == 0
    assert source.read_bytes() == before
    with ReadModel.open(paths) as model:
        rows = model.list_quarantine()
    assert len(rows) == 1
    assert rows[0]["byte_offset"] == 0 and rows[0]["byte_length"] == len(line)
    assert rows[0]["event_schema_version"] == "aether.observation.event.v999"


def test_update_rollback_reupdate_uses_per_version_projections_and_immutable_source(
    monkeypatch, tmp_path
) -> None:
    """A future reader can ingest bytes an older reader quarantined, then roll back."""
    from aether_agents.observation.reduce import ingest as ingest_module

    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path).ensure()
    future_raw = EventFactory().opened(0)
    future_raw["schema_version"] = "aether.observation.event.v999"
    line = canonical_json_bytes(future_raw) + b"\n"
    source = paths.closed / f"{EPOCH}.0-0.jsonl"
    source.write_bytes(line)
    source_digest = sha256_hex(source.read_bytes())

    rolled_back = ingest_pending(paths)
    assert rolled_back.quarantined_events == 1
    old_projection = paths.projection_db(READ_MODEL_SCHEMA)
    assert old_projection.is_file()
    with ReadModel.open(paths, schema=READ_MODEL_SCHEMA) as old_model:
        old_model.publish_projection(expected_active=None)

    future_event = deepcopy(future_raw)
    future_event["schema_version"] = EVENT_SCHEMA_VERSION
    future_schema = "aether.observation.projection.v999"
    original_open = ReadModel.open.__func__

    def open_future(cls, opened_paths, *, schema=future_schema):
        return original_open(cls, opened_paths, schema=schema)

    monkeypatch.setattr(ReadModel, "open", classmethod(open_future))
    monkeypatch.setattr(
        ingest_module,
        "upcast_event",
        lambda _raw: UpcastResult(future_event, "ok"),
    )
    updated = ingest_module.ingest_pending(paths)
    assert updated.events_inserted == 1
    future_projection = paths.projection_db(future_schema)
    assert future_projection.is_file() and future_projection != old_projection
    assert sha256_hex(source.read_bytes()) == source_digest
    with original_open(ReadModel, paths, schema=future_schema) as future_model:
        future_model.publish_projection(expected_active=old_projection.name)

    # Merely opening an old reader cannot downgrade the active projection.
    with original_open(ReadModel, paths, schema=READ_MODEL_SCHEMA) as old_model:
        assert old_model.events_for_trace(TRACE_ID) == []
        assert len(old_model.list_quarantine()) == 1
    assert paths.projection_pointer.read_text().strip() == future_projection.name
    assert future_projection.is_file()

    # Explicit rollback CAS-selects the prior compatible projection while preserving
    # the newer projection and immutable source for a later re-update.
    with original_open(ReadModel, paths, schema=READ_MODEL_SCHEMA) as old_model:
        old_model.publish_projection(expected_active=future_projection.name)
    assert paths.projection_pointer.read_text().strip() == old_projection.name
    assert future_projection.is_file()

    # Re-update explicitly reselects the compatible projection and sees the event.
    with original_open(ReadModel, paths, schema=future_schema) as future_model:
        assert len(future_model.events_for_trace(TRACE_ID)) == 1
        future_model.publish_projection(expected_active=old_projection.name)
    assert paths.projection_pointer.read_text().strip() == future_projection.name
    assert sha256_hex(source.read_bytes()) == source_digest


def test_identity_collision_is_diagnostic_not_silent_deduplication(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path).ensure()
    first = EventFactory(epoch="prd_" + "1" * 32).opened(0)
    second = deepcopy(first)
    second["producer_epoch"] = "prd_" + "2" * 32
    second["producer_seq"] = 0
    second["actor"]["id"] = "different"
    (paths.closed / f"{first['producer_epoch']}.0-0.jsonl").write_bytes(
        canonical_json_bytes(first) + b"\n"
    )
    second_path = paths.closed / f"{second['producer_epoch']}.0-0.jsonl"
    second_path.write_bytes(canonical_json_bytes(second) + b"\n")
    before = second_path.read_bytes()
    report = ingest_pending(paths)
    assert report.events_inserted == 1 and report.corrupt_segments == 1
    assert second_path.read_bytes() == before
    with ReadModel.open(paths) as model:
        assert "EVENT_IDENTITY_COLLISION" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_contiguous_active_tail_with_released_lock_is_still_incomplete(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    assert writer.append(EventFactory().opened(0)).accepted
    # Simulate process death after the last complete append: kernel closes the file
    # descriptor and releases the advisory lock, but no clean rename occurs.
    assert writer._segment_fd is not None
    os.close(writer._segment_fd)
    writer._segment_fd = None
    writer._release_epoch_lock()
    report = ingest_pending(paths)
    assert report.unclean_epochs == 1
    summary = reduce_trace(paths, TRACE_ID)
    assert not summary["coverage"]["complete"]
    assert "UNCLEAN_PRODUCER_TAIL" in {gap["reason_code"] for gap in summary["coverage"]["gaps"]}


def test_read_model_indexes_all_normative_logical_tables_and_rebuilds_safely(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = complete_trace()
    with ReadModel.open(paths) as model:
        assert model.upsert_events(factory.events) == len(factory.events)
        assert model.upsert_events(factory.events) == 0
        summary = factory.summary()
        assert model.record_summary(summary)
        db_path = model.path
    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        connection.close()
    required = {
        "observation_trace",
        "observation_event",
        "contract_decision",
        "contract_revision",
        "tool_span",
        "participant_contribution",
        "bound_work_unit",
        "work_unit_run",
        "process_step",
        "process_wave",
        "execution_round",
        "configuration_fingerprint",
        "model_request_economics",
        "tool_surface_snapshot",
        "dispatch_observation",
        "bottleneck_interval",
        "defect_attribution",
        "review_transition",
        "acceptance_criterion",
        "invariant_transition",
        "coverage_gap",
        "observation_summary",
    }
    assert required <= tables
    assert not paths.projection_pointer.exists()


def test_projection_pointer_changes_only_by_explicit_owner_cas_and_rollback_preserves_newer(
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    old_schema = READ_MODEL_SCHEMA
    future_schema = "aether.observation.projection.v999"
    old_path = paths.projection_db(old_schema)
    future_path = paths.projection_db(future_schema)

    with ReadModel.open(paths, schema=old_schema) as old_model:
        assert not paths.projection_pointer.exists()
        old_model.publish_projection(expected_active=None)
    assert paths.projection_pointer.read_text().strip() == old_path.name

    with ReadModel.open(paths, schema=future_schema) as future_model:
        assert paths.projection_pointer.read_text().strip() == old_path.name
        future_model.publish_projection(expected_active=old_path.name)
    assert paths.projection_pointer.read_text().strip() == future_path.name

    with ReadModel.open(paths, schema=old_schema) as old_model:
        with pytest.raises(storage_module.ProjectionPointerConflict):
            old_model.publish_projection(expected_active=None)
        assert paths.projection_pointer.read_text().strip() == future_path.name
        old_model.publish_projection(expected_active=future_path.name)

    assert paths.projection_pointer.read_text().strip() == old_path.name
    assert future_path.is_file()


def test_projection_pointer_owner_can_cas_unpublish_initial_selection(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with ReadModel.open(paths) as model:
        target = model.path.name
        model.publish_projection(expected_active=None)
        with pytest.raises(storage_module.ProjectionPointerConflict):
            model.unpublish_projection(expected_active="aether.observation.projection.v999.sqlite3")
        assert paths.projection_pointer.read_text().strip() == target

        model.unpublish_projection(expected_active=target)
        assert not paths.projection_pointer.exists()
        model.unpublish_projection(expected_active=target)
        assert not paths.projection_pointer.exists()


def test_projection_pointer_unpublish_retry_reproves_directory_durability(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with ReadModel.open(paths) as model:
        target = model.path.name
        model.publish_projection(expected_active=None)
        original_fsync = storage_module.os.fsync
        rejected = False

        def reject_first_directory_fsync(descriptor: int) -> None:
            nonlocal rejected
            if not rejected and stat.S_ISDIR(os.fstat(descriptor).st_mode):
                rejected = True
                raise OSError("synthetic unpublish directory fsync interruption")
            original_fsync(descriptor)

        monkeypatch.setattr(storage_module.os, "fsync", reject_first_directory_fsync)
        with pytest.raises(OSError, match="unpublish directory fsync"):
            model.unpublish_projection(expected_active=target)
        assert not paths.projection_pointer.exists()

        monkeypatch.setattr(storage_module.os, "fsync", original_fsync)
        model.unpublish_projection(expected_active=target)
        assert not paths.projection_pointer.exists()


def test_rebuild_file_fsync_precedes_atomic_publish_and_directory_fsync(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    events: list[tuple[str, str]] = []
    original_fsync = storage_module.os.fsync
    original_replace = storage_module.os.replace

    def record_fsync(descriptor: int) -> None:
        mode = os.fstat(descriptor).st_mode
        events.append(("fsync", "directory" if stat.S_ISDIR(mode) else "file"))
        original_fsync(descriptor)

    def record_replace(source, target, *args, **kwargs) -> None:
        events.append(("replace", os.fspath(target)))
        original_replace(source, target, *args, **kwargs)

    with ReadModel.open(paths) as model:
        monkeypatch.setattr(storage_module.os, "fsync", record_fsync)
        monkeypatch.setattr(storage_module.os, "replace", record_replace)
        model.rebuild()

    target = paths.projection_db(READ_MODEL_SCHEMA).name
    replace_index = events.index(("replace", target))
    assert ("fsync", "file") in events[:replace_index]
    assert ("fsync", "directory") in events[replace_index + 1 :]


def test_rebuild_atomic_rename_failure_preserves_previous_projection_for_retry(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    event = EventFactory().opened(0)
    model = ReadModel.open(paths)
    assert model.upsert_event(event)
    model.publish_projection(expected_active=None)
    pointer_before = paths.projection_pointer.read_bytes()
    original_replace = storage_module.os.replace

    def interrupt_database_replace(source, target, *args, **kwargs) -> None:
        if os.fspath(target) == model.path.name:
            raise OSError("synthetic projection rename interruption")
        original_replace(source, target, *args, **kwargs)

    monkeypatch.setattr(storage_module.os, "replace", interrupt_database_replace)
    with pytest.raises(OSError, match="rename interruption"):
        model.rebuild()

    assert paths.projection_pointer.read_bytes() == pointer_before
    with sqlite3.connect(model.path) as previous:
        assert previous.execute(
            "SELECT COUNT(*) FROM observation_event WHERE event_id=?",
            (event["event_id"],),
        ).fetchone() == (1,)

    monkeypatch.setattr(storage_module.os, "replace", original_replace)
    model.rebuild()
    assert model.events_for_trace(TRACE_ID) == []
    model.close()


def test_rebuild_retry_cleans_only_owned_stale_candidates(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    model = ReadModel.open(paths)
    token = "a" * 32
    prefix = f".{model.path.name}.rebuild-{token}.tmp"
    stale = tuple(paths.projections / f"{prefix}{suffix}" for suffix in ("", "-journal"))
    for candidate in stale:
        candidate.write_bytes(b"interrupted-candidate")
    unknown = paths.projections / f".{model.path.name}.rebuild-not-owned.tmp"
    unknown.write_bytes(b"preserve-unknown")

    model.rebuild()

    assert all(not candidate.exists() for candidate in stale)
    assert unknown.read_bytes() == b"preserve-unknown"
    model.close()


def test_rebuild_waits_for_open_reader_before_publishing_candidate(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    owner = ReadModel.open(paths)
    reader = ReadModel.open(paths)
    entered = threading.Event()
    finished = threading.Event()
    failures: list[BaseException] = []
    original_rebuild = owner._rebuild_locked

    def rebuild_after_signal() -> None:
        entered.set()
        try:
            original_rebuild()
        except BaseException as error:  # pragma: no branch - asserted below
            failures.append(error)
        finally:
            finished.set()

    worker = threading.Thread(target=rebuild_after_signal, daemon=True)
    worker.start()
    assert entered.wait(timeout=1.0)
    assert not finished.wait(timeout=0.2)
    reader.close()
    assert finished.wait(timeout=2.0)
    worker.join(timeout=1.0)
    assert failures == []
    owner.close()


@pytest.mark.parametrize("failure_phase", ("connect", "ddl"))
def test_rebuild_interruption_keeps_previous_projection_and_pointer_retriable(
    monkeypatch, tmp_path, failure_phase: str
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    event = EventFactory().opened(0)
    model = ReadModel.open(paths)
    assert model.upsert_event(event)
    model.publish_projection(expected_active=None)
    db_path = model.path
    pointer_before = paths.projection_pointer.read_bytes()
    original_connect = storage_module._connect_projection
    original_create_schema = model._create_schema

    if failure_phase == "connect":

        def interrupted_connect(_path: Path, **_descriptor_args):
            raise OSError("synthetic candidate connect interruption")

        monkeypatch.setattr(storage_module, "_connect_projection", interrupted_connect)
    else:

        def interrupted_ddl() -> None:
            raise sqlite3.OperationalError("synthetic candidate DDL interruption")

        monkeypatch.setattr(model, "_create_schema", interrupted_ddl)

    expected = "candidate connect" if failure_phase == "connect" else "candidate DDL"
    with pytest.raises((OSError, sqlite3.OperationalError), match=expected):
        model.rebuild()

    assert paths.projection_pointer.read_bytes() == pointer_before
    assert db_path.is_file()
    with sqlite3.connect(db_path) as previous:
        assert previous.execute(
            "SELECT COUNT(*) FROM observation_event WHERE event_id=?",
            (event["event_id"],),
        ).fetchone() == (1,)

    monkeypatch.setattr(storage_module, "_connect_projection", original_connect)
    monkeypatch.setattr(model, "_create_schema", original_create_schema)
    model.rebuild()
    assert paths.projection_pointer.read_bytes() == pointer_before
    assert model.events_for_trace(TRACE_ID) == []
    model.close()


def test_projection_pointer_fsyncs_file_and_directory_before_publish_returns(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    original_fsync = os.fsync
    synced_modes: list[int] = []

    def record_fsync(descriptor: int) -> None:
        synced_modes.append(os.fstat(descriptor).st_mode)
        original_fsync(descriptor)

    monkeypatch.setattr(storage_module.os, "fsync", record_fsync)
    with ReadModel.open(paths) as model:
        model.publish_projection(expected_active=None)
    assert any(stat.S_ISREG(mode) for mode in synced_modes), "pointer file was never fsynced"
    assert any(stat.S_ISDIR(mode) for mode in synced_modes), (
        "projection directory was never fsynced"
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow pointer confinement")
def test_projection_pointer_swap_after_hardening_cannot_govern_version_fence(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with ReadModel.open(paths) as model:
        model.publish_projection(expected_active=None)
    pointer = paths.projection_pointer
    external = tmp_path / "external-projection-pointer"
    external_bytes = b"aether.observation.projection.v999.sqlite3\n"
    external.write_bytes(external_bytes)
    original_harden = storage_module.harden_file
    swapped = False

    def harden_then_swap(path: Path) -> None:
        nonlocal swapped
        original_harden(path)
        if Path(path) == pointer and not swapped:
            pointer.unlink()
            pointer.symlink_to(external)
            swapped = True

    monkeypatch.setattr(storage_module, "harden_file", harden_then_swap)
    with ReadModel.open(paths) as model:
        with pytest.raises(UnsafeObservationPath):
            model.publish_projection(expected_active=paths.projection_db(READ_MODEL_SCHEMA).name)

    assert swapped
    assert pointer.is_symlink()
    assert external.read_bytes() == external_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX private-file modes")
def test_read_model_open_hardens_database_and_live_sqlite_sidecars(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)

    with ReadModel.open(paths):
        projection_files = paths.projection_files(READ_MODEL_SCHEMA)
        assert all(candidate.exists() for candidate in projection_files)
        assert {stat.S_IMODE(candidate.stat().st_mode) for candidate in projection_files} == {0o600}


@pytest.mark.skipif(os.name != "posix", reason="POSIX link confinement")
@pytest.mark.parametrize("link_kind", ["hardlink", "symlink"])
def test_read_model_rejects_preexisting_link_before_sqlite_can_mutate_target(
    tmp_path, link_kind
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path).ensure()
    external = tmp_path / f"external-{link_kind}.sqlite3"
    connection = sqlite3.connect(external)
    try:
        connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel VALUES ('unchanged')")
        connection.commit()
    finally:
        connection.close()
    before = external.read_bytes()
    projection = paths.projection_db(READ_MODEL_SCHEMA)
    if link_kind == "hardlink":
        os.link(external, projection)
    else:
        os.symlink(external, projection)

    with pytest.raises(UnsafeObservationPath):
        ReadModel.open(paths)

    assert external.read_bytes() == before
    connection = sqlite3.connect(f"file:{external}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert tables == {"sentinel"}
        assert connection.execute("SELECT value FROM sentinel").fetchone() == ("unchanged",)
    finally:
        connection.close()


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor confinement")
def test_read_model_rejects_db_symlink_swap_before_external_bytes_change(
    monkeypatch, tmp_path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path).ensure()
    projection = paths.projection_db(READ_MODEL_SCHEMA)
    displaced = tmp_path / "displaced-projection.sqlite3"
    external = tmp_path / "external-swap.sqlite3"
    connection = sqlite3.connect(external)
    try:
        connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel VALUES ('unchanged')")
        connection.commit()
    finally:
        connection.close()
    before = external.read_bytes()
    real_connect = storage_module.sqlite3.connect
    swapped = False

    def swap_then_connect(database, *args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            if projection.exists() and not projection.is_symlink():
                projection.rename(displaced)
            projection.symlink_to(external)
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(storage_module.sqlite3, "connect", swap_then_connect)
    with pytest.raises(UnsafeObservationPath):
        ReadModel.open(paths)

    assert swapped
    assert external.read_bytes() == before


@pytest.mark.skipif(os.name != "posix", reason="POSIX component-wise SQLite confinement")
def test_read_model_rejects_projection_ancestor_swap_before_external_bytes_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    detached_state = tmp_path / "detached-state"
    external_state = tmp_path / "external-state"
    paths = ObservationPaths.for_project(PROJECT_ID, root=state).ensure()
    projection = paths.projection_db(READ_MODEL_SCHEMA)
    external_projection = external_state / projection.relative_to(state)
    external_projection.parent.mkdir(parents=True)
    connection = sqlite3.connect(external_projection)
    try:
        connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel VALUES ('unchanged')")
        connection.commit()
    finally:
        connection.close()
    before = external_projection.read_bytes()
    before_mtime_ns = external_projection.stat().st_mtime_ns
    real_connect_projection = storage_module._connect_projection
    swapped = False

    def swap_ancestor_then_connect(db_path: Path):
        nonlocal swapped
        if not swapped:
            state.rename(detached_state)
            state.symlink_to(external_state, target_is_directory=True)
            swapped = True
        return real_connect_projection(db_path)

    monkeypatch.setattr(storage_module, "_connect_projection", swap_ancestor_then_connect)

    with pytest.raises(UnsafeObservationPath):
        ReadModel.open(paths)

    assert swapped
    assert external_projection.read_bytes() == before
    assert external_projection.stat().st_mtime_ns == before_mtime_ns


def test_projection_pointer_directory_fsync_failure_is_not_silenced(monkeypatch, tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    original_fsync = os.fsync

    def reject_directory_fsync(descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("synthetic projection directory fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(storage_module.os, "fsync", reject_directory_fsync)
    with pytest.raises(OSError, match="projection directory"):
        with ReadModel.open(paths) as model:
            model.publish_projection(expected_active=None)


def test_projection_pointer_retry_reproves_directory_durability(monkeypatch, tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    original_fsync_directory = ReadModel._fsync_directory

    def reject_first_boundary(_directory) -> None:
        raise OSError("synthetic first pointer durability failure")

    monkeypatch.setattr(ReadModel, "_fsync_directory", staticmethod(reject_first_boundary))
    with pytest.raises(OSError, match="first pointer durability"):
        with ReadModel.open(paths) as model:
            model.publish_projection(expected_active=None)
    assert paths.projection_pointer.exists()

    calls = 0

    def record_retry_boundary(directory) -> None:
        nonlocal calls
        calls += 1
        original_fsync_directory(directory)

    monkeypatch.setattr(ReadModel, "_fsync_directory", staticmethod(record_retry_boundary))
    with ReadModel.open(paths) as model:
        model.publish_projection(expected_active=None)
    assert calls == 1


def test_trace_close_is_not_success_until_reducer_settles_graph_and_acceptance(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    fixture = complete_trace()
    with ReadModel.open(paths) as model:
        model.upsert_events(fixture.events)
        [row] = model.list_traces()
        assert row["termination"] == "open"
        summary = fixture.summary()
        assert summary["runtime_state"]["termination"] == "completed"
        model.record_summary(summary)
        [row] = model.list_traces()
        assert row["termination"] == "completed"


@pytest.mark.parametrize(
    ("event_type", "status"),
    (
        ("trace.cancelled", "cancelled"),
        ("trace.abandoned", "unknown"),
        ("trace.failed", "failed"),
    ),
)
@pytest.mark.parametrize(
    ("authority_available", "actor_id", "profile", "role"),
    (
        (True, "implementer", "implementer", "implementation"),
        (False, "morfeo", "morfeo", "verification"),
    ),
    ids=("unauthorized-implementer", "authority-unavailable"),
)
def test_raw_terminal_event_cannot_hide_trace_before_authoritative_reduction(
    tmp_path,
    event_type: str,
    status: str,
    authority_available: bool,
    actor_id: str,
    profile: str,
    role: str,
) -> None:
    state_root = tmp_path / "aether"
    if authority_available:
        _activate_test_release(state_root, tmp_path)
    fixture = EventFactory()
    fixture.opened(0)
    fixture.contract(
        event_type,
        status,
        1,
        actor_id=actor_id,
        profile=profile,
        role=role,
    )
    paths, _ = _write_closed_segment(state_root, events=fixture.events)

    report = ingest_pending(paths)

    assert report.events_inserted == 2
    assert query_module.resolve_trace(paths, None) == TRACE_ID
    with ReadModel.open(paths) as model:
        [raw_row] = model.list_traces()
        assert raw_row["termination"] == "open"

    summary = query_module.load_summary(paths, TRACE_ID)
    assert summary["runtime_state"]["termination"] == "open"
    assert "TERMINAL_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }
    if not authority_available:
        assert "AUTHORITY_CONTEXT_UNAVAILABLE" in {
            gap["reason_code"] for gap in summary["coverage"]["gaps"]
        }


def test_read_model_retains_native_envelopes_without_double_derivation(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    factory.opened(0)
    captured = factory.add(
        factory.builder.tool_started(
            call_id=native_pseudonym("tool_call", "native-call"),
            name="terminal",
            category="terminal",
            session_id=native_pseudonym("session", "session-1"),
            occurred_at=factory.at(1),
        )
    )
    reconciled = deepcopy(captured)
    reconciled["event_id"] = "evt_" + "d" * 32
    reconciled["producer_epoch"] = "prd_" + "e" * 32
    reconciled["producer_seq"] = 0
    reconciled["source_kind"] = "native_reconciliation"
    reconciled["recorded_at"] = factory.at(2).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    with ReadModel.open(paths) as model:
        assert model.upsert_event(captured)
        assert model.upsert_event(reconciled)
        assert len(model.events_for_trace(TRACE_ID)) == 2
        assert model._conn.execute(
            "SELECT event_count FROM observation_trace WHERE trace_id=?",
            (TRACE_ID,),
        ).fetchone() == (1,)
        assert model._conn.execute(
            "SELECT action_total FROM participant_contribution WHERE trace_id=?",
            (TRACE_ID,),
        ).fetchone() == (1,)
        assert model._conn.execute("SELECT COUNT(*) FROM tool_span").fetchone() == (1,)
        reconciled_events = dedupe(model.events_for_trace(TRACE_ID))
        assert reconciled_events.duplicates_dropped == 1
        assert reconciled_events.events[0]["source_kind"] == "hermes_hook"


def test_native_identity_index_migrates_and_rebuilds_as_non_unique(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    captured = factory.add(
        factory.builder.tool_started(
            call_id=native_pseudonym("tool_call", "migration-call"),
            name="terminal",
            category="terminal",
            session_id=native_pseudonym("session", "session-1"),
            occurred_at=factory.at(1),
        )
    )
    reconciled = deepcopy(captured)
    reconciled["event_id"] = "evt_" + "d" * 32
    reconciled["producer_epoch"] = "prd_" + "e" * 32
    reconciled["producer_seq"] = 0
    reconciled["source_kind"] = "native_reconciliation"

    with ReadModel.open(paths) as model:
        assert model.upsert_event(captured)
        model._conn.execute("DROP INDEX idx_event_native_identity")
        model._conn.execute(
            "CREATE UNIQUE INDEX idx_event_native_identity "
            "ON observation_event(trace_id, native_identity_key) "
            "WHERE native_identity_key IS NOT NULL"
        )
        model._conn.commit()

    with ReadModel.open(paths) as model:
        [index] = [
            row
            for row in model._conn.execute("PRAGMA index_list('observation_event')")
            if row[1] == "idx_event_native_identity"
        ]
        assert index[2] == 0
        assert model.upsert_event(reconciled)
        assert len(model.events_for_trace(TRACE_ID)) == 2

        model.rebuild()
        assert model.upsert_events((captured, reconciled)) == 2
        assert len(model.events_for_trace(TRACE_ID)) == 2


@pytest.mark.parametrize("reverse", (False, True))
def test_read_model_preserves_native_assignment_and_exact_classification_in_any_order(
    tmp_path,
    reverse: bool,
) -> None:
    factory = EventFactory()
    native = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    exact = deepcopy(native)
    exact["event_id"] = "evt_" + "f" * 32
    exact["producer_epoch"] = "prd_" + "f" * 32
    exact["source_kind"] = "aether_checkpoint"
    exact["parent_event_id"] = native["event_id"]
    exact["actor"] = {
        "kind": "agent",
        "id": "supervisor",
        "profile": "supervisor",
        "role": "supervision",
    }
    exact["work_unit"]["relation"] = "review"
    exact["work_unit"]["required"] = True
    events = [native, exact]
    if reverse:
        events.reverse()

    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with ReadModel.open(paths, authority_context=AuthorityContext.product_default()) as model:
        assert model.upsert_events(events) == 2
        stored = [
            event
            for event in model.events_for_trace(TRACE_ID)
            if event["event_type"] == "work_unit.bound"
        ]
        assert len(stored) == 2
        assert {event["source_kind"] for event in stored} == {
            "hermes_hook",
            "aether_checkpoint",
        }
        projected = model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone()
        assert projected == ("review", 1)
        assert "EVENT_IDENTITY_COLLISION" not in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


@pytest.mark.parametrize(
    ("authority_context", "actor_id"),
    (
        (AuthorityContext.product_default(), "intruder"),
        (AuthorityContext.unavailable(), "supervisor"),
    ),
)
@pytest.mark.parametrize("reverse", (False, True))
def test_read_model_rejects_unverified_product_classification_in_any_order(
    tmp_path,
    authority_context: AuthorityContext,
    actor_id: str,
    reverse: bool,
) -> None:
    factory = EventFactory()
    native = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    product = deepcopy(native)
    product["event_id"] = "evt_" + "f" * 32
    product["producer_epoch"] = "prd_" + "f" * 32
    product["producer_seq"] = 0
    product["source_kind"] = "aether_checkpoint"
    product["parent_event_id"] = native["event_id"]
    product["actor"] = {
        "kind": "agent",
        "id": actor_id,
        "profile": "supervisor",
        "role": "supervision",
    }
    product["work_unit"]["relation"] = "review"
    product["work_unit"]["required"] = True
    events = [native, product]
    if reverse:
        events.reverse()

    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with ReadModel.open(paths, authority_context=authority_context) as model:
        assert model.upsert_events(events) == 2
        projected = model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone()
        assert projected == ("unknown", None)
        assert "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_read_model_reprojects_when_product_authority_changes(tmp_path) -> None:
    factory = EventFactory()
    native = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    exact = deepcopy(native)
    exact["event_id"] = "evt_" + "f" * 32
    exact["producer_epoch"] = "prd_" + "f" * 32
    exact["producer_seq"] = 0
    exact["source_kind"] = "aether_checkpoint"
    exact["parent_event_id"] = native["event_id"]
    exact["actor"]["role"] = "supervision"
    exact["work_unit"]["relation"] = "review"
    exact["work_unit"]["required"] = True
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)

    with ReadModel.open(paths, authority_context=AuthorityContext.product_default()) as model:
        assert model.upsert_events((native, exact)) == 2
        assert model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone() == ("review", 1)

    with ReadModel.open(paths, authority_context=AuthorityContext.unavailable()) as model:
        assert model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone() == ("unknown", None)
        assert "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }

    with ReadModel.open(paths, authority_context=AuthorityContext.product_default()) as model:
        assert model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone() == ("review", 1)
        assert "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED" not in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_ingest_preserves_explicit_native_parent_target_in_every_permutation(
    tmp_path,
) -> None:
    factory = EventFactory()
    target = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="unknown",
        required=None,
        task_status="done",
        actor_id="supervisor",
        profile="supervisor",
    )
    target["event_id"] = "evt_" + "c" * 32
    duplicate = deepcopy(target)
    duplicate["event_id"] = "evt_" + "a" * 32
    duplicate["producer_epoch"] = "prd_" + "e" * 32
    duplicate["producer_seq"] = 0
    classification = deepcopy(target)
    classification["event_id"] = "evt_" + "f" * 32
    classification["producer_epoch"] = "prd_" + "f" * 32
    classification["producer_seq"] = 0
    classification["source_kind"] = "aether_checkpoint"
    classification["parent_event_id"] = target["event_id"]
    classification["actor"]["role"] = "supervision"
    classification["work_unit"]["relation"] = "root"
    classification["work_unit"]["required"] = True

    summary_ids = set()
    expected_ids = {target["event_id"], duplicate["event_id"], classification["event_id"]}
    for index, order in enumerate(permutations((target, duplicate, classification))):
        state_root = tmp_path / f"permutation-{index}"
        state_root.mkdir()
        _activate_test_release(state_root, state_root)
        paths = ObservationPaths.for_project(PROJECT_ID, root=state_root).ensure()
        inserted = 0
        for event in deepcopy(order):
            segment = paths.closed / f"{event['producer_epoch']}.0-0.jsonl"
            segment.write_bytes(canonical_json_bytes(event) + b"\n")
            ingest = ingest_pending(paths)
            inserted += ingest.events_inserted
            assert ingest.corrupt_segments == 0
        assert inserted == 3
        with ReadModel.open(paths) as model:
            stored = model.events_for_trace(TRACE_ID)
            assert {event["event_id"] for event in stored} == expected_ids
            assert model._conn.execute(
                "SELECT COUNT(*) FROM event_derivation WHERE event_id IN (?, ?, ?)",
                tuple(sorted(expected_ids)),
            ).fetchone() == (3,)
            action_total, actions_json = model._conn.execute(
                "SELECT action_total, actions_json FROM participant_contribution "
                "WHERE trace_id=? AND actor_id=?",
                (TRACE_ID, "supervisor"),
            ).fetchone()
            assert action_total == 2
            assert json.loads(actions_json)["work_unit.bound"] == 2
            assert model._conn.execute(
                "SELECT event_count FROM observation_trace WHERE trace_id=?",
                (TRACE_ID,),
            ).fetchone() == (2,)
            assert model._conn.execute(
                "SELECT relation, required FROM bound_work_unit WHERE trace_id=? AND task_ref=?",
                (TRACE_ID, "root"),
            ).fetchone() == ("root", 1)
        summary = reduce_trace(paths, TRACE_ID)
        unit = summary["work_graph"]["units"][0]
        assert unit["relation"] == "root"
        assert unit["required"] is True
        summary_ids.add(summary["summary_id"])
    assert len(summary_ids) == 1


def test_read_model_preserves_two_explicit_duplicate_parent_targets(tmp_path) -> None:
    factory = EventFactory()
    first = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    second = deepcopy(first)
    second["event_id"] = "evt_" + "e" * 32
    second["producer_epoch"] = "prd_" + "e" * 32
    second["producer_seq"] = 0
    classifications = []
    for marker, parent in (("d", first), ("f", second)):
        classification = deepcopy(first)
        classification["event_id"] = "evt_" + marker * 32
        classification["producer_epoch"] = "prd_" + marker * 32
        classification["producer_seq"] = 0
        classification["source_kind"] = "aether_checkpoint"
        classification["parent_event_id"] = parent["event_id"]
        classification["actor"]["role"] = "supervision"
        classification["work_unit"]["relation"] = "root"
        classification["work_unit"]["required"] = True
        classifications.append(classification)
    events = (first, second, *classifications)
    expected_ids = {event["event_id"] for event in events}

    representative_orders = (
        events,
        tuple(reversed(events)),
        (classifications[0], second, classifications[1], first),
        (second, classifications[1], first, classifications[0]),
    )
    for index, order in enumerate(representative_orders):
        paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / str(index))
        with ReadModel.open(
            paths,
            authority_context=AuthorityContext.product_default(),
        ) as model:
            assert model.upsert_events(deepcopy(order)) == 4
            assert {event["event_id"] for event in model.events_for_trace(TRACE_ID)} == expected_ids
            assert model._conn.execute(
                "SELECT relation, required FROM bound_work_unit WHERE trace_id=? AND task_ref=?",
                (TRACE_ID, "root"),
            ).fetchone() == ("root", 1)


def test_ingest_loads_product_authority_before_projecting_classification(tmp_path) -> None:
    state_root = tmp_path / "aether"
    _activate_test_release(state_root, tmp_path)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    factory = EventFactory()
    native = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    forged = deepcopy(native)
    forged["event_id"] = "evt_" + "f" * 32
    forged["producer_epoch"] = "prd_" + "f" * 32
    forged["producer_seq"] = 0
    forged["source_kind"] = "aether_checkpoint"
    forged["parent_event_id"] = native["event_id"]
    forged["actor"] = {
        "kind": "agent",
        "id": "intruder",
        "profile": "supervisor",
        "role": "supervision",
    }
    forged["work_unit"]["relation"] = "review"
    forged["work_unit"]["required"] = True

    native_collector = Collector(
        paths=paths,
        runtime_fingerprint="3" * 64,
        producer_epoch="prd_" + "1" * 32,
    )
    native_collector.start()
    try:
        assert native_collector.emit(native).accepted
    finally:
        native_collector.stop()
    forged_collector = Collector(
        paths=paths,
        runtime_fingerprint="3" * 64,
        producer_epoch="prd_" + "2" * 32,
    )
    forged_collector.start()
    try:
        assert forged_collector.emit(forged).accepted
    finally:
        forged_collector.stop()

    report = ingest_pending(paths)
    assert report.corrupt_segments == 0
    with ReadModel.open(paths) as model:
        projected = model._conn.execute(
            "SELECT relation, required FROM bound_work_unit WHERE binding_ref=?",
            ("bnd_review_unit_0123456789abcdef",),
        ).fetchone()
        assert projected == ("unknown", None)
        assert "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED" in {
            gap["reason_code"] for gap in model.derived_gaps(TRACE_ID)
        }


def test_read_model_never_resurrects_unbound_state_for_any_ingest_permutation(
    tmp_path,
) -> None:
    factory = EventFactory()
    native_bound = factory.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    native_unbound = factory.unit(
        "work_unit.unbound",
        "reported",
        2,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    native_unbound["parent_event_id"] = native_bound["event_id"]
    exact = deepcopy(native_bound)
    exact["event_id"] = "evt_" + "f" * 32
    exact["producer_epoch"] = "prd_" + "f" * 32
    exact["producer_seq"] = 0
    exact["source_kind"] = "aether_checkpoint"
    exact["parent_event_id"] = native_unbound["event_id"]
    exact["actor"] = {
        "kind": "agent",
        "id": "supervisor",
        "profile": "supervisor",
        "role": "supervision",
    }
    exact["work_unit"]["relation"] = "review"
    exact["work_unit"]["required"] = True

    for index, order in enumerate(permutations((native_bound, native_unbound, exact))):
        paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / str(index))
        with ReadModel.open(paths, authority_context=AuthorityContext.product_default()) as model:
            assert model.upsert_events(order) == 3
            projected = model._conn.execute(
                "SELECT relation, required, bound_at, unbound_at "
                "FROM bound_work_unit WHERE binding_ref=?",
                ("bnd_review_unit_0123456789abcdef",),
            ).fetchone()
            assert projected == (
                "review",
                1,
                native_bound["occurred_at"],
                native_unbound["occurred_at"],
            )


def test_read_model_native_identity_conflict_becomes_reproducible_gap(tmp_path) -> None:
    factory = EventFactory()
    opened = factory.opened(0)
    completed = factory.add(
        factory.builder.tool_terminal(
            call_id=native_pseudonym("tool_call", "native-conflict"),
            name="terminal",
            category="terminal",
            status="completed",
            occurred_at=factory.at(1),
            session_id=native_pseudonym("session", "session-1"),
            actor_kind="agent",
            actor_id="implementer",
            profile="implementer",
        )
    )
    failed = deepcopy(completed)
    failed["event_id"] = "evt_" + "f" * 32
    failed["event_type"] = "tool.failed"
    failed["status"] = "failed"
    failed["source_kind"] = "native_reconciliation"
    paths, _ = _write_closed_segment(tmp_path, events=[opened, completed, failed])

    report = ingest_pending(paths)

    assert report.events_inserted == 3
    assert report.duplicate_events == 0
    assert report.corrupt_segments == 0
    with ReadModel.open(paths) as model:
        assert [event["event_id"] for event in model.events_for_trace(TRACE_ID)] == [
            opened["event_id"],
            completed["event_id"],
            failed["event_id"],
        ]
    summary = reduce_trace(paths, TRACE_ID)
    assert "NATIVE_TERMINAL_CONFLICT" in {gap["reason_code"] for gap in summary["coverage"]["gaps"]}


def test_deterministic_gzip_has_fixed_header_and_bytes() -> None:
    data = b'{"synthetic":true}\n'
    one = _deterministic_gzip(data)
    two = _deterministic_gzip(data)
    assert one == two and gzip.decompress(one) == data
    assert gzip_header_fields(one) == {
        "compression_method": 8,
        "flags": 0,
        "mtime": 0,
        "extra_flags": 2,
        "os_byte": 255,
    }


@pytest.mark.skipif(os.name != "posix", reason="link confinement uses POSIX inode semantics")
@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_compaction_rejects_linked_source_outside_project_without_touching_it(
    tmp_path, link_kind
) -> None:
    _, external_segment = _write_closed_segment(tmp_path / "outside")
    external = external_segment.path
    before = external.read_bytes()

    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "target")
    paths.ensure()
    linked = paths.closed / external.name
    if link_kind == "symlink":
        linked.symlink_to(external)
    else:
        os.link(external, linked)
    segment = parse_segment_name(linked)
    assert segment is not None

    with pytest.raises(UnsafeObservationPath):
        compact_segment(paths, segment)

    assert external.read_bytes() == before
    assert linked.exists()
    assert list(paths.archive.iterdir()) == []


def test_closed_segment_compaction_is_lossless_and_deletes_only_verified_source(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    original = segment.path.read_bytes()
    result = compact_segment(paths, segment)
    assert not segment.path.exists()
    assert verify_archive(result.manifest_path).ok
    assert gzip.decompress(result.archive_path.read_bytes()) == original
    events = list(iter_archive_events(result.archive_path))
    assert [event["producer_seq"] for event in events] == [0, 1]
    assert result.manifest["event_count"] == result.manifest["line_count"] == 2


@pytest.mark.skipif(os.name != "posix", reason="ancestor fencing uses POSIX dirfd semantics")
def test_compaction_never_replaces_files_in_swapped_archive_ancestor(monkeypatch, tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path / "state")
    outside_archive = tmp_path / "outside-archive"
    outside_archive.mkdir()
    parked_archive = tmp_path / "parked-archive"
    archive_name = segment.path.name + ".gz"
    manifest_name = archive_name + ".manifest.json"
    sentinel = b"outside-file-must-not-be-replaced"
    (outside_archive / archive_name).write_bytes(sentinel)
    (outside_archive / manifest_name).write_bytes(sentinel)
    original_replace = retention_module.os.replace
    swapped = False

    def swap_archive_before_first_replace(source, target, *args, **kwargs) -> None:
        nonlocal swapped
        if not swapped and os.fspath(target) == archive_name:
            for temporary in paths.archive.iterdir():
                if ".tmp-" in temporary.name:
                    (outside_archive / temporary.name).write_bytes(temporary.read_bytes())
            paths.archive.rename(parked_archive)
            outside_archive.rename(paths.archive)
            swapped = True
        elif not swapped and Path(os.fspath(target)).name == archive_name:
            for temporary in paths.archive.iterdir():
                if ".tmp-" in temporary.name:
                    (outside_archive / temporary.name).write_bytes(temporary.read_bytes())
            paths.archive.rename(parked_archive)
            outside_archive.rename(paths.archive)
            swapped = True
        original_replace(source, target, *args, **kwargs)

    monkeypatch.setattr(retention_module.os, "replace", swap_archive_before_first_replace)

    with pytest.raises(UnsafeObservationPath):
        compact_segment(paths, segment)

    assert segment.path.exists(), "ancestor replacement must preserve the only source"
    assert (paths.archive / archive_name).read_bytes() == sentinel
    assert (paths.archive / manifest_name).read_bytes() == sentinel


def test_compaction_retry_with_stale_closed_segment_reference_is_idempotent(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    first = compact_segment(paths, segment)

    retried = compact_segment(paths, segment)

    assert retried.archive_path == first.archive_path
    assert retried.manifest_path == first.manifest_path
    assert retried.manifest == first.manifest
    assert verify_archive(retried.manifest_path).ok
    assert not segment.path.exists()


def test_compaction_propagates_directory_fsync_failure_and_keeps_source(
    monkeypatch, tmp_path
) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    original_fsync = os.fsync

    def reject_directory_fsync(descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("synthetic compaction directory fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(retention_module.os, "fsync", reject_directory_fsync)
    with pytest.raises(OSError, match="compaction directory"):
        compact_segment(paths, segment)
    assert segment.path.exists(), "source was removed before archive durability was proven"


def test_compaction_completes_all_archive_fsync_boundaries_before_source_unlink(
    monkeypatch, tmp_path
) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    original_fsync_directory = retention_module._fsync_directory
    archive_calls = 0

    def reject_second_archive_boundary(directory) -> None:
        nonlocal archive_calls
        if directory == paths.archive:
            archive_calls += 1
            if archive_calls == 2:
                raise OSError("synthetic final archive durability failure")
        original_fsync_directory(directory)

    monkeypatch.setattr(retention_module, "_fsync_directory", reject_second_archive_boundary)
    with pytest.raises(OSError, match="final archive durability"):
        compact_segment(paths, segment)
    assert segment.path.exists()


def test_compaction_restores_exact_source_after_closed_directory_fsync_failure(
    monkeypatch, tmp_path
) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    before = segment.path.read_bytes()
    original_fsync_directory = retention_module._fsync_directory

    def reject_closed_directory(directory) -> None:
        if directory == paths.closed:
            raise OSError("synthetic closed directory durability failure")
        original_fsync_directory(directory)

    monkeypatch.setattr(retention_module, "_fsync_directory", reject_closed_directory)
    with pytest.raises(OSError, match="closed directory durability"):
        compact_segment(paths, segment)
    assert segment.path.read_bytes() == before
    monkeypatch.setattr(retention_module, "_fsync_directory", original_fsync_directory)
    retried = compact_segment(paths, segment)
    assert not segment.path.exists()
    assert verify_archive(retried.manifest_path).ok


@pytest.mark.skipif(os.name != "posix", reason="process storage fencing uses POSIX flock")
@pytest.mark.parametrize("competing_operation", ["ingest", "recovery"])
def test_compaction_ingest_and_recovery_share_one_cross_process_transition_lock(
    monkeypatch, tmp_path, competing_operation
) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    context = multiprocessing.get_context("fork")
    archive_fsync_entered = context.Event()
    release_compaction = context.Event()
    original_fsync_directory = retention_module._fsync_directory

    def gated_fsync_directory(directory) -> None:
        if directory == paths.archive and not archive_fsync_entered.is_set():
            archive_fsync_entered.set()
            release_compaction.wait(5.0)
        original_fsync_directory(directory)

    monkeypatch.setattr(retention_module, "_fsync_directory", gated_fsync_directory)

    def compact_worker() -> None:
        compact_segment(paths, segment)

    def competing_worker() -> None:
        if competing_operation == "ingest":
            ingest_pending(paths)
        else:
            recover_interrupted(paths)

    compactor = context.Process(target=compact_worker)
    competitor = context.Process(target=competing_worker)
    compactor.start()
    try:
        assert archive_fsync_entered.wait(3.0), "compactor did not reach the rename boundary"
        competitor.start()
        competitor.join(0.3)
        assert competitor.is_alive(), "storage transition ran concurrently with compaction"
    finally:
        release_compaction.set()
        compactor.join(5.0)
        if competitor.pid is not None:
            competitor.join(5.0)
        for process in (compactor, competitor):
            if process.is_alive():
                process.terminate()
                process.join(1.0)
    assert compactor.exitcode == 0
    assert competitor.exitcode == 0


def test_active_segment_is_never_eligible_for_compaction(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    try:
        assert writer.append(EventFactory().opened(0)).accepted
        reference = parse_segment_name(writer.active_segment)
        assert reference is not None
        with pytest.raises(SegmentNotEligible):
            compact_segment(paths, reference)
    finally:
        writer.close()


def test_archive_corruption_is_detected_without_deleting_any_recovered_source(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    result = compact_segment(paths, segment)
    recovered_source = paths.closed / result.manifest["source_name"]
    recovered_source.write_bytes(gzip.decompress(result.archive_path.read_bytes()))
    archive = bytearray(result.archive_path.read_bytes())
    archive[-5] ^= 0x01
    result.archive_path.write_bytes(bytes(archive))
    assert not verify_archive(result.manifest_path).ok
    report = recover_interrupted(paths)
    assert recovered_source.exists()
    assert report.left_for_manual_review


@pytest.mark.skipif(os.name != "posix", reason="link confinement uses POSIX inode semantics")
@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_recovery_leaves_linked_source_for_manual_review_without_reading_it(
    tmp_path, link_kind
) -> None:
    paths, segment = _write_closed_segment(tmp_path / "state")
    original = segment.path.read_bytes()
    result = compact_segment(paths, segment)
    source = paths.closed / result.manifest["source_name"]
    external = tmp_path / "external-source.jsonl"
    external.write_bytes(original)
    before = external.read_bytes()
    if link_kind == "symlink":
        source.symlink_to(external)
    else:
        os.link(external, source)

    report = recover_interrupted(paths)

    assert report.completed_deletions == 0
    assert result.archive_path.name in report.left_for_manual_review
    assert source.exists()
    assert external.read_bytes() == before


def test_recovery_removes_temps_orphans_and_finishes_verified_source_deletion(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    original = segment.path.read_bytes()
    result = compact_segment(paths, segment)
    # Recreate the safe interrupted state after final verification but before source
    # deletion, plus harmless earlier-stage debris.
    source = paths.closed / result.manifest["source_name"]
    source.write_bytes(original)
    (paths.archive / "leftover.tmp-deadbeef.gz").write_bytes(b"temporary")
    orphan = paths.archive / (result.manifest["source_name"] + ".orphan.jsonl.gz")
    orphan_source = paths.closed / orphan.name[: -len(".gz")]
    orphan_source.write_bytes(original)
    orphan.write_bytes(b"orphan")
    report = recover_interrupted(paths)
    assert report.removed_temp_files == 1
    assert report.removed_orphan_files == 1
    assert report.completed_deletions == 1
    assert not source.exists() and not orphan.exists()


@pytest.mark.skipif(os.name != "posix", reason="ancestor fencing uses POSIX dirfd semantics")
def test_recovery_never_unlinks_file_in_swapped_archive_ancestor(monkeypatch, tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path / "state")
    original = segment.path.read_bytes()
    result = compact_segment(paths, segment)
    source = paths.closed / result.manifest["source_name"]
    source.write_bytes(original)
    temporary_name = "leftover.tmp-ancestor-swap.gz"
    (paths.archive / temporary_name).write_bytes(b"owned-temporary")
    outside_archive = tmp_path / "outside-archive"
    outside_archive.mkdir()
    sentinel = b"outside-file-must-not-be-unlinked"
    (outside_archive / temporary_name).write_bytes(sentinel)
    parked_archive = tmp_path / "parked-archive"
    original_unlink = retention_module.os.unlink
    swapped = False

    def swap_archive_before_unlink(target, *args, **kwargs) -> None:
        nonlocal swapped
        if not swapped and Path(os.fspath(target)).name == temporary_name:
            paths.archive.rename(parked_archive)
            outside_archive.rename(paths.archive)
            swapped = True
        original_unlink(target, *args, **kwargs)

    monkeypatch.setattr(retention_module.os, "unlink", swap_archive_before_unlink)

    report = recover_interrupted(paths)

    assert (paths.archive / temporary_name).read_bytes() == sentinel
    assert source.exists(), "detached archive evidence cannot authorize source deletion"
    assert report.completed_deletions == 0


def test_recovery_reproves_archive_directory_durability_before_source_cleanup(
    monkeypatch, tmp_path
) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    original = segment.path.read_bytes()
    result = compact_segment(paths, segment)
    source = paths.closed / result.manifest["source_name"]
    source.write_bytes(original)
    original_fsync_directory = retention_module._fsync_directory

    def reject_archive_directory(directory) -> None:
        if directory == paths.archive:
            raise OSError("synthetic archive durability uncertainty")
        original_fsync_directory(directory)

    monkeypatch.setattr(retention_module, "_fsync_directory", reject_archive_directory)
    report = recover_interrupted(paths)
    assert source.exists()
    assert result.archive_path.name in report.left_for_manual_review


def test_recovery_is_idempotent_after_finishing_verified_source_cleanup(tmp_path) -> None:
    paths, segment = _write_closed_segment(tmp_path)
    original = segment.path.read_bytes()
    result = compact_segment(paths, segment)
    source = paths.closed / result.manifest["source_name"]
    source.write_bytes(original)

    first = recover_interrupted(paths)
    second = recover_interrupted(paths)
    assert first.completed_deletions == 1
    assert second.removed_temp_files == 0
    assert second.removed_orphan_files == 0
    assert second.completed_deletions == 0
    assert second.left_for_manual_review == ()


def test_no_automatic_pruning_surface_exists() -> None:
    import aether_agents.observation.retention as retention

    public = set(retention.__all__)
    assert not public & {"prune", "delete_old", "expire", "vacuum_sources"}
