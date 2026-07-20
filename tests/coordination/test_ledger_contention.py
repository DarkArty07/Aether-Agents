import multiprocessing as mp
import os
import sqlite3
from pathlib import Path

from olympus_v3.coordination.leases import Lease, LeaseResult
from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)

SCOPE = StoreScope("install-a", "project-a")
WRITER_KEYS = {("writer-a", "key-a"): b"writer-key"}


def ledger(path: str | Path, *, clock: int, busy_timeout_ms: int = 250) -> SQLiteLedger:
    return SQLiteLedger(
        path,
        SCOPE,
        writer_authenticator=HMACWriterAuthenticator(WRITER_KEYS),
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=lambda: clock,
        busy_timeout_ms=busy_timeout_ms,
    )


def signed_append(db: SQLiteLedger, lease: Lease, aggregate: str):
    context = WriterContext(SCOPE, "writer-a", "key-a", lease.resource, lease.epoch, lease.expires_at)
    auth = HMACWriterAuthenticator(WRITER_KEYS)
    draft = db.draft(aggregate, "state.set", {"value": aggregate}, writer=context)
    return db.append(auth.sign(draft, context), context)


def hold_write_lock(path: str, ready, release) -> None:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("BEGIN IMMEDIATE")
    ready.set()
    release.wait(10)
    connection.rollback()
    connection.close()


def acquire_worker(path: str, owner: str, barrier, results) -> None:
    db = ledger(path, clock=100, busy_timeout_ms=2000)
    barrier.wait()
    outcome = db.acquire_lease("harmonia", owner, ttl=100)
    results.put((owner, outcome.status.value, outcome.lease.epoch if outcome.lease else None))
    db.close()


def append_worker(path: str, lease: Lease, aggregate: str, barrier, results) -> None:
    db = ledger(path, clock=100, busy_timeout_ms=2000)
    barrier.wait()
    outcome = signed_append(db, lease, aggregate)
    results.put(outcome.status.value)
    db.close()


def crashing_writer(path: str, lease: Lease) -> None:
    db = ledger(path, clock=100, busy_timeout_ms=2000)

    def terminate_after_insert(stage: str) -> None:
        if stage == "after_event_insert":
            os._exit(73)

    db.fault = terminate_after_insert
    signed_append(db, lease, "crashed-aggregate")
    os._exit(74)


def takeover_worker(path: str, results) -> None:
    db = ledger(path, clock=111, busy_timeout_ms=2000)
    outcome = db.acquire_lease("ledger", "writer-b", ttl=100)
    lease = outcome.lease
    results.put(
        (
            outcome.status.value,
            lease.owner if lease else None,
            lease.epoch if lease else None,
            lease.token if lease else None,
        )
    )
    db.close()


def join(processes) -> None:
    for process in processes:
        process.join(10)
        assert not process.is_alive(), f"subprocess {process.pid} did not terminate"
        assert process.exitcode == 0


def test_busy_lease_acquisition_is_bounded_contended_not_exception(tmp_path: Path):
    path = tmp_path / "coord.sqlite"
    db = ledger(path, clock=100, busy_timeout_ms=50)
    context = mp.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    holder = context.Process(target=hold_write_lock, args=(str(path), ready, release))
    holder.start()
    assert ready.wait(5)
    try:
        outcome = db.acquire_lease("harmonia", "owner-a", ttl=100)
        assert outcome.status is LeaseResult.CONTENDED
        assert outcome.lease is None
    finally:
        release.set()
        holder.join(10)
        db.close()
    assert holder.exitcode == 0


def test_busy_lease_renewal_is_bounded_contended_and_does_not_mutate(tmp_path: Path):
    path = tmp_path / "renew.sqlite"
    db = ledger(path, clock=100, busy_timeout_ms=50)
    acquired = db.acquire_lease("harmonia", "owner-a", ttl=100)
    assert acquired.lease is not None
    lease = acquired.lease
    context = mp.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    holder = context.Process(target=hold_write_lock, args=(str(path), ready, release))
    holder.start()
    assert ready.wait(5)
    try:
        outcome = db.renew_lease(lease, "owner-a", ttl=200, token=lease.token)
        assert outcome.status is LeaseResult.CONTENDED
        assert outcome.lease is None
    finally:
        release.set()
        holder.join(10)
    assert holder.exitcode == 0
    assert db.check_lease(lease).lease == lease
    db.close()


def test_repeated_spawn_race_has_exactly_one_lease_winner(tmp_path: Path):
    context = mp.get_context("spawn")
    for attempt in range(5):
        path = tmp_path / f"lease-race-{attempt}.sqlite"
        initializer = ledger(path, clock=100)
        initializer.close()
        barrier = context.Barrier(3)
        results = context.Queue()
        processes = [
            context.Process(target=acquire_worker, args=(str(path), owner, barrier, results))
            for owner in ("owner-a", "owner-b")
        ]
        for process in processes:
            process.start()
        barrier.wait()
        join(processes)
        outcomes = [results.get(timeout=2) for _ in processes]
        assert sorted(item[1] for item in outcomes) == [LeaseResult.ACQUIRED.value, LeaseResult.CONTENDED.value]
        assert [item[2] for item in outcomes if item[1] == LeaseResult.ACQUIRED.value] == [1]


def test_repeated_spawn_cas_has_one_applied_and_one_conflict(tmp_path: Path):
    path = tmp_path / "cas-race.sqlite"
    db = ledger(path, clock=100)
    acquired = db.acquire_lease("ledger", "writer-a", ttl=1000)
    assert acquired.lease is not None
    lease = acquired.lease
    db.close()

    context = mp.get_context("spawn")
    for attempt in range(5):
        barrier = context.Barrier(3)
        results = context.Queue()
        aggregate = f"aggregate-{attempt}"
        processes = [
            context.Process(target=append_worker, args=(str(path), lease, aggregate, barrier, results))
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        barrier.wait()
        join(processes)
        assert sorted(results.get(timeout=2) for _ in processes) == [Result.APPLIED.value, Result.CAS_CONFLICT.value]

    verified = ledger(path, clock=100)
    assert verified.verify_chain()
    assert len(verified.events()) == 5
    verified.close()


def test_process_death_rolls_back_partial_transaction_and_next_writer_recovers(tmp_path: Path):
    path = tmp_path / "writer-death.sqlite"
    db = ledger(path, clock=100)
    acquired = db.acquire_lease("ledger", "writer-a", ttl=1000)
    assert acquired.lease is not None
    lease = acquired.lease
    db.close()

    context = mp.get_context("spawn")
    process = context.Process(target=crashing_writer, args=(str(path), lease))
    process.start()
    process.join(10)
    assert not process.is_alive()
    assert process.exitcode == 73

    recovered = ledger(path, clock=100)
    assert recovered.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    for table in ("events", "projections", "inbox", "outbox"):
        assert recovered.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert signed_append(recovered, lease, "recovered-aggregate").status is Result.APPLIED
    assert recovered.verify_chain()
    recovered.close()


def test_subprocess_takeover_permanently_rejects_old_fence(tmp_path: Path):
    path = tmp_path / "takeover.sqlite"
    db = ledger(path, clock=100)
    acquired = db.acquire_lease("ledger", "writer-a", ttl=10)
    assert acquired.lease is not None
    old = acquired.lease
    db.close()

    context = mp.get_context("spawn")
    results = context.Queue()
    process = context.Process(target=takeover_worker, args=(str(path), results))
    process.start()
    join([process])
    status, owner, epoch, token = results.get(timeout=2)
    assert (status, owner, epoch) == (LeaseResult.ACQUIRED.value, "writer-b", old.epoch + 1)
    assert token != old.token

    current = ledger(path, clock=111)
    assert current.check_lease(old).status is LeaseResult.STALE_FENCE
    assert signed_append(current, old, "old-fence").status is Result.STALE_FENCE
    current.close()

    much_later = ledger(path, clock=10_000)
    assert much_later.check_lease(old).status is LeaseResult.STALE_FENCE
    assert signed_append(much_later, old, "old-fence-later").status is Result.STALE_FENCE
    much_later.close()
