import multiprocessing
import sqlite3

import pytest
from coordination_sqlite_proof import (
    APPLIED,
    CAS_CONFLICT,
    CONTENDED,
    STALE_FENCE,
    ProofDB,
    acquire_fence,
    append_event,
    apply_inbox,
    backup_and_verify,
    claim_outbox,
    create_contract,
    fail_outbox,
    rebuild_projection,
    send_outbox,
)


def make_db(tmp_path):
    return ProofDB(tmp_path / "proof.sqlite3")


def test_event_projection_outbox_are_atomic_on_injected_rollback(tmp_path):
    db = make_db(tmp_path)
    with pytest.raises(RuntimeError):
        append_event(db, "aggregate-1", "created", {"value": 7}, fail_after_event=True)
    assert db.events() == []
    assert db.projection("aggregate-1") is None
    assert db.outbox() == []


def test_two_writers_same_expected_version_have_one_applied_and_one_cas_conflict(tmp_path):
    db = make_db(tmp_path)
    assert append_event(db, "a", "set", {"value": 1}) == APPLIED
    barrier = multiprocessing.Barrier(2)

    def writer(path, result_queue):
        local = ProofDB(path)
        barrier.wait()
        result_queue.put(append_event(local, "a", "set", {"value": 2}, expected_version=1))
        local.close()

    queue = multiprocessing.Queue()
    processes = [multiprocessing.Process(target=writer, args=(str(db.path), queue)) for _ in range(2)]
    for process in processes:
        process.start()
    results = [queue.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
    assert sorted(results) == [APPLIED, CAS_CONFLICT]
    assert db.projection("a")["version"] == 2


def test_fence_is_monotonic_and_stale_fence_has_no_event(tmp_path):
    db = make_db(tmp_path)
    assert acquire_fence(db, "worker", 2) == 2
    assert acquire_fence(db, "worker", 1) == 2
    assert append_event(
        db, "a", "set", {"value": 1}, fence=1, fence_owner="worker"
    ) == STALE_FENCE
    assert db.events() == []


def test_duplicate_inbox_applies_once(tmp_path):
    db = make_db(tmp_path)
    assert apply_inbox(db, "message-1", "a", "set", {"value": 3}) == APPLIED
    assert apply_inbox(db, "message-1", "a", "set", {"value": 99}) == "DUPLICATE"
    assert len(db.events()) == 1
    assert db.projection("a")["value"] == 3


def test_inbox_and_event_roll_back_together_before_dedup_marker(tmp_path):
    db = make_db(tmp_path)
    with pytest.raises(RuntimeError, match="before inbox"):
        apply_inbox(
            db,
            "message-1",
            "a",
            "set",
            {"value": 3},
            fail_before_inbox=True,
        )
    assert db.events() == []
    assert db.projection("a") is None
    assert db.outbox() == []
    assert db.conn.execute("SELECT * FROM inbox").fetchall() == []
    assert apply_inbox(db, "message-1", "a", "set", {"value": 3}) == APPLIED


def test_outbox_lease_failure_expiry_retry_and_sent_keep_message_id(tmp_path):
    db = make_db(tmp_path)
    append_event(db, "a", "set", {"value": 1})
    message_id = db.outbox()[0]["message_id"]
    claimed = claim_outbox(db, "worker", lease_seconds=0)
    assert claimed[0]["message_id"] == message_id
    assert fail_outbox(db, message_id, "worker") == "FAILED"
    assert claim_outbox(db, "worker", lease_seconds=0)[0]["message_id"] == message_id
    assert send_outbox(db, message_id, "worker") == "SENT"
    assert send_outbox(db, message_id, "worker") == "SENT"
    assert db.outbox()[0]["message_id"] == message_id
    assert db.outbox()[0]["status"] == "SENT"


def test_authenticated_hash_chain_detects_payload_hash_and_auth_tamper(tmp_path):
    db = make_db(tmp_path)
    append_event(db, "a", "set", {"value": 1})
    for column, value in (("payload", '{"value":999}'), ("hash", "0" * 64), ("auth_tag", "0" * 64)):
        tampered = make_db(tmp_path / column)
        append_event(tampered, "a", "set", {"value": 1})
        tampered.conn.execute(f"UPDATE events SET {column} = ?", (value,))
        tampered.conn.commit()
        with pytest.raises(ValueError, match="integrity"):
            tampered.verify_events()
        tampered.close()


def test_projection_rebuild_is_deterministic(tmp_path):
    db = make_db(tmp_path)
    append_event(db, "a", "set", {"value": 1})
    append_event(db, "a", "set", {"value": 2})
    live = db.projection("a")
    assert rebuild_projection(db) == {"a": live}


def test_backup_artifact_passes_integrity_and_verification(tmp_path):
    db = make_db(tmp_path)
    append_event(db, "a", "set", {"value": 4})
    artifact = tmp_path / "backup.sqlite3"
    backup_and_verify(db, artifact)
    copied = sqlite3.connect(artifact)
    assert copied.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    copied.close()


def _contender(path, index, queue):
    db = ProofDB(path)
    result = append_event(db, "shared", "set", {"value": index}, expected_version=0)
    queue.put(result if result in {APPLIED, CAS_CONFLICT} else CONTENDED)
    db.close()


def test_process_contention_has_no_lost_committed_events(tmp_path):
    db = make_db(tmp_path)
    db.close()
    queue = multiprocessing.Queue()
    processes = [multiprocessing.Process(target=_contender, args=(str(tmp_path / "proof.sqlite3"), i, queue)) for i in range(2)]
    for process in processes:
        process.start()
    results = [queue.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
    assert set(results) <= {APPLIED, CAS_CONFLICT, CONTENDED}
    assert results.count(APPLIED) == 1
    check = ProofDB(tmp_path / "proof.sqlite3")
    assert len(check.events()) == 1


def test_contract_generation_is_immutable(tmp_path):
    db = make_db(tmp_path)
    assert create_contract(db, "coordination", 1, {"capability": "write"}) == "CREATED"
    assert create_contract(db, "coordination", 1, {"capability": "changed"}) == "IMMUTABLE"
    assert create_contract(db, "coordination", 0, {}) == "IMMUTABLE"
    assert create_contract(db, "coordination", 2, {"capability": "write"}) == "CREATED"
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("UPDATE contracts SET document='{}' WHERE name='coordination' AND generation=1")
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("DELETE FROM contracts")


def test_sentinels_are_not_addressed_or_changed(tmp_path):
    sentinels = [".aether", ".olympus", "gateway-state.json"]
    before = {name: "sentinel" for name in sentinels}
    for name in sentinels:
        (tmp_path / name).write_text("sentinel")
    db = make_db(tmp_path / "nested")
    append_event(db, "a", "set", {"value": 1})
    assert {name: (tmp_path / name).read_text() for name in sentinels} == before
    assert all(str(tmp_path / name) not in str(db.path) for name in sentinels)
