from pathlib import Path

import pytest

from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)


@pytest.fixture
def ledger(tmp_path: Path):
    now = [100]
    scope = StoreScope("install-a", "project-a")
    auth = HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"})
    db = SQLiteLedger(
        tmp_path / "coord.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=lambda: now[0],
    )
    ledger_lease = db.acquire_lease("ledger", "writer-a", ttl=100)
    context = WriterContext(scope, "writer-a", "key-a", "ledger", ledger_lease.lease.epoch, ledger_lease.lease.expires_at)
    draft = db.draft("aggregate-a", "state.set", {"value": 1}, writer=context)
    signed = auth.sign(draft, context)
    assert db.append(signed, context, message_id="message-a").status is Result.APPLIED
    yield db, now, scope
    db.close()


def snapshot(db: SQLiteLedger):
    tables = ("events", "projections", "inbox", "outbox")
    return {table: [dict(row) for row in db.conn.execute(f"SELECT * FROM {table} ORDER BY rowid")] for table in tables}


def transport_lease(db: SQLiteLedger, owner: str = "transport-a", ttl: int = 100):
    outcome = db.acquire_lease("outbox", owner, ttl=ttl)
    assert outcome.lease is not None
    return outcome.lease


def test_missing_or_wrong_fence_cannot_claim_and_rejections_are_atomic(ledger):
    db, now, _ = ledger
    lease = transport_lease(db)
    before = snapshot(db)

    assert db.claim_outbox("transport-a", lease=None) == []
    assert db.mark_outbox_retry("message-a", "transport-a", lease=None) is Result.STALE_FENCE
    assert db.mark_outbox_sent("message-a", "transport-a", lease=None) is Result.STALE_FENCE
    wrong = lease.__class__(lease.scope, lease.resource, lease.owner, lease.epoch, lease.expires_at, "wrong-token")
    assert db.claim_outbox("transport-a", lease=wrong) == []
    assert snapshot(db) == before


def test_expired_and_taken_over_fences_cannot_claim_or_mutate(ledger):
    db, now, _ = ledger
    old = transport_lease(db, ttl=10)
    claimed = db.claim_outbox("transport-a", lease=old, lease_ns=1000)
    assert len(claimed) == 1
    before = snapshot(db)

    now[0] = 111
    assert db.check_lease(old).status.value == "LEASE_EXPIRED"
    assert db.mark_outbox_retry("message-a", "transport-a", lease=old) is Result.LEASE_EXPIRED
    assert db.mark_outbox_sent("message-a", "transport-a", lease=old) is Result.LEASE_EXPIRED
    assert snapshot(db) == before

    takeover = transport_lease(db, owner="transport-b", ttl=100)
    assert takeover.epoch == old.epoch + 1
    before_takeover = snapshot(db)
    assert db.claim_outbox("transport-a", lease=old) == []
    assert db.mark_outbox_retry("message-a", "transport-a", lease=old) is Result.STALE_FENCE
    assert db.mark_outbox_sent("message-a", "transport-a", lease=old) is Result.STALE_FENCE
    assert snapshot(db) == before_takeover


def test_new_fence_is_the_single_cas_winner_and_old_fence_stays_rejected(ledger):
    db, now, _ = ledger
    old = transport_lease(db, ttl=10)
    claimed = db.claim_outbox("transport-a", lease=old, lease_ns=1000)
    assert claimed[0]["attempts"] == 1
    now[0] = 111
    new = transport_lease(db, owner="transport-b", ttl=100)

    assert db.mark_outbox_retry("message-a", "transport-a", lease=old) is Result.STALE_FENCE
    assert db.mark_outbox_retry("message-a", "transport-b", lease=new) is Result.STALE_FENCE
    assert snapshot(db)["outbox"][0]["status"] == "LEASED"


def test_bounded_failure_poison_is_one_verified_event_without_recursive_outbox(ledger, tmp_path):
    db, now, _ = ledger
    lease = transport_lease(db, ttl=1000)
    first = db.claim_outbox("transport-a", lease=lease, lease_ns=1000, max_attempts=2)
    assert first[0]["message_id"] == "message-a"
    assert (
        db.mark_outbox_retry(
            "message-a",
            "transport-a",
            lease=lease,
            backoff_ns=1,
            max_attempts=2,
        )
        is Result.RETRY_SCHEDULED
    )

    now[0] += 2
    second = db.claim_outbox("transport-a", lease=lease, now=now[0], lease_ns=1000, max_attempts=2)
    assert second[0]["message_id"] == "message-a"
    assert db.mark_outbox_retry("message-a", "transport-a", lease=lease, max_attempts=2, error="permanent") is Result.POISON_TERMINATED
    poison = db.outbox()[0]
    assert poison["status"] == "POISON"
    assert poison["message_id"] == "message-a"
    assert db.conn.execute("SELECT COUNT(*) FROM events WHERE kind='outbox.poison'").fetchone()[0] == 1
    assert db.conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1
    assert db.mark_outbox_retry("message-a", "transport-a", lease=lease, max_attempts=2) is Result.STALE_FENCE
    assert db.conn.execute("SELECT COUNT(*) FROM events WHERE kind='outbox.poison'").fetchone()[0] == 1
    assert db.verify_chain()
    assert db.verify_projections()
    db.checkpoint()
    assert db.verify_checkpoints()
    artifact = db.backup(tmp_path / "poison.sqlite")
    prepared = db.prepare_restore(artifact)
    assert prepared.artifact == artifact


def test_transport_ack_does_not_complete_execution_contract(ledger):
    db, _, _ = ledger
    lease = transport_lease(db)
    assert db.claim_outbox("transport-a", lease=lease)[0]["status"] == "LEASED"
    assert db.mark_outbox_sent("message-a", "transport-a", lease=lease) is Result.TRANSPORT_ACKNOWLEDGED
    row = db.outbox()[0]
    assert row["status"] == "SENT"
    assert row["transport_ack_at"] is not None
    assert row["semantic_completion_event_id"] is None
    assert db.complete_outbox("message-a", "completion-event") is Result.APPLIED
    assert db.outbox()[0]["semantic_completion_event_id"] == "completion-event"
