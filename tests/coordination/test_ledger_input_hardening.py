from pathlib import Path
from typing import cast

import pytest

from olympus_v3.coordination import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    LeaseManager,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)

SCOPE = StoreScope("install-a", "project-a")


def ledger(path: Path, *, authenticator=None) -> SQLiteLedger:
    return SQLiteLedger(
        path,
        SCOPE,
        writer_authenticator=authenticator or HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"}),
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=lambda: 100,
    )


def writer(db: SQLiteLedger):
    outcome = db.acquire_lease("ledger", "writer-a", ttl=1000)
    assert outcome.lease is not None
    lease = outcome.lease
    return WriterContext(SCOPE, "writer-a", "key-a", "ledger", lease.epoch, lease.expires_at)


def append_message(db: SQLiteLedger):
    auth = cast(HMACWriterAuthenticator, db.writer_authenticator)
    context = writer(db)
    draft = auth.sign(db.draft("aggregate-a", "state.set", {"value": 1}, writer=context), context)
    assert db.append(draft, context, message_id="message-a").status is Result.APPLIED
    return context


@pytest.mark.parametrize("ttl", (0, -1, True, 1.5, 2**63))
def test_ledger_lease_rejects_invalid_ttl_without_mutation(tmp_path, ttl):
    db = ledger(tmp_path / "coord.sqlite")
    outcome = db.acquire_lease("ledger", "writer-a", ttl=ttl)
    assert outcome.status.value == "INVALID_INPUT"
    assert outcome.lease is None
    assert db.conn.execute("SELECT COUNT(*) FROM leases").fetchone()[0] == 0
    db.close()


@pytest.mark.parametrize("ttl", (0, -1, True, 1.5, 2**63))
def test_standalone_lease_manager_rejects_invalid_ttl_without_mutation(tmp_path, ttl):
    manager = LeaseManager(str(tmp_path / "lease.sqlite"), SCOPE, clock=lambda: 100)
    outcome = manager.acquire(SCOPE, "ledger", "writer-a", ttl=ttl)
    assert outcome.status.value == "INVALID_INPUT"
    assert outcome.lease is None
    manager.close()


@pytest.mark.parametrize("resource,owner", (("", "writer-a"), ("Ledger", "writer-a"), ("ledger", ""), ("ledger", "w" * 129)))
def test_lease_identifiers_are_bounded_and_fail_closed(tmp_path, resource, owner):
    db = ledger(tmp_path / "coord.sqlite")
    outcome = db.acquire_lease(resource, owner, ttl=100)
    assert outcome.status.value == "INVALID_INPUT"
    assert db.conn.execute("SELECT COUNT(*) FROM leases").fetchone()[0] == 0
    db.close()


@pytest.mark.parametrize("aggregate,kind", (("", "state.set"), ("Aggregate", "state.set"), ("a" * 129, "state.set"), ("aggregate-a", ""), ("aggregate-a", "💥")))
def test_draft_identifiers_are_bounded_and_fail_closed(tmp_path, aggregate, kind):
    db = ledger(tmp_path / "coord.sqlite")
    context = writer(db)
    with pytest.raises(ValueError, match="invalid"):
        db.draft(aggregate, kind, {"value": 1}, writer=context)
    assert db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    db.close()


def test_writer_context_wrong_types_raise_documented_validation_error():
    with pytest.raises(ValueError, match="invalid writer context"):
        WriterContext(SCOPE, 7, "key-a", "ledger", 1, 100)  # type: ignore[arg-type]


def test_oversized_payload_is_rejected_before_transaction(tmp_path):
    db = ledger(tmp_path / "coord.sqlite")
    context = writer(db)
    with pytest.raises(ValueError, match="payload"):
        db.draft("aggregate-a", "state.set", {"value": "x" * 16_385}, writer=context)
    assert db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    db.close()


def test_invalid_message_id_returns_typed_result_without_mutation(tmp_path):
    db = ledger(tmp_path / "coord.sqlite")
    auth = cast(HMACWriterAuthenticator, db.writer_authenticator)
    context = writer(db)
    draft = auth.sign(db.draft("aggregate-a", "state.set", {"value": 1}, writer=context), context)
    result = db.append(draft, context, message_id="")
    assert result.status.value == "INVALID_INPUT"
    assert db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    db.close()


def test_transport_bounds_reject_invalid_values_without_mutation(tmp_path):
    db = ledger(tmp_path / "coord.sqlite")
    append_message(db)
    transport = db.acquire_lease("outbox-transport", "transport-a", ttl=1000).lease
    assert transport is not None
    before = [tuple(row) for row in db.conn.execute("SELECT * FROM outbox")]

    with pytest.raises(ValueError, match="invalid input"):
        db.claim_outbox("transport-a", lease=transport, lease_ns=0)
    with pytest.raises(ValueError, match="invalid input"):
        db.claim_outbox("transport-a", lease=transport, max_attempts=0)
    assert db.mark_outbox_retry("message-a", "transport-a", lease=transport, error="x" * 4097).value == "INVALID_INPUT"
    assert db.mark_outbox_retry("message-a", "transport-a", lease=transport, backoff_ns=0).value == "INVALID_INPUT"
    assert db.mark_outbox_sent("", "transport-a", lease=transport).value == "INVALID_INPUT"
    assert [tuple(row) for row in db.conn.execute("SELECT * FROM outbox")] == before
    db.close()


class RaisingAuthenticator:
    def verify(self, draft, context):
        raise RuntimeError("auth backend failed")


class RaisingSigner:
    key_id = "integrity"

    def sign(self, value):
        raise RuntimeError("signer backend failed")

    def verify(self, value, signature):
        return False


def test_authenticator_exception_is_terminal_typed_and_has_no_mutation(tmp_path):
    db = ledger(tmp_path / "coord.sqlite", authenticator=RaisingAuthenticator())
    context = writer(db)
    draft = db.draft("aggregate-a", "state.set", {"value": 1}, writer=context)
    result = db.append(draft, context)
    assert result.status is Result.INTEGRITY_FAILURE
    assert db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    db.close()


def test_poison_signer_exception_is_terminal_and_rolls_back_every_table(tmp_path):
    db = ledger(tmp_path / "coord.sqlite")
    append_message(db)
    lease = db.acquire_lease("outbox", "transport-a", ttl=1000).lease
    assert lease is not None
    assert db.claim_outbox("transport-a", lease=lease, max_attempts=1)
    before = {
        table: [tuple(row) for row in db.conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        for table in ("events", "projections", "outbox")
    }
    db.integrity_signer = RaisingSigner()

    assert db.mark_outbox_retry("message-a", "transport-a", lease=lease, max_attempts=1) is Result.INTEGRITY_FAILURE
    assert not db.conn.in_transaction
    after = {
        table: [tuple(row) for row in db.conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        for table in before
    }
    assert after == before
    db.close()
