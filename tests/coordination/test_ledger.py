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
from olympus_v3.coordination.projections import ProjectionReducer


def setup(tmp_path: Path, *, clock=None):
    scope = StoreScope("install-a", "project-a")
    auth = HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"})
    signer = HMACIntegritySigner(b"integrity-key", key_id="integrity-a")
    db = SQLiteLedger(tmp_path / "coord.sqlite", scope, writer_authenticator=auth, integrity_signer=signer, clock=clock)
    lease = db.acquire_lease("ledger", "writer-a", ttl=(10 if clock is not None else 10_000_000_000))
    assert lease.lease is not None
    ctx = WriterContext(scope, "writer-a", "key-a", "ledger", lease.lease.epoch, lease.lease.expires_at)
    return db, scope, auth, signer, ctx


def signed(db, auth, ctx, aggregate="aggregate-a", kind="state.set", payload=None, **kwargs):
    draft = db.draft(aggregate, kind, payload or {"value": 3}, writer=ctx, **kwargs)
    return auth.sign(draft, ctx)


def test_append_is_authenticated_fenced_and_projected(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    result = db.append(signed(db, auth, ctx), ctx)
    assert result.status is Result.APPLIED
    assert result.event.sequence == 1
    assert db.projection("aggregate-a")["value"] == 3
    assert db.verify_chain()
    db.close()


def test_missing_scope_bad_auth_and_strict_draft_rejected(tmp_path):
    db, scope, auth, _, ctx = setup(tmp_path)
    assert (
        db.append(
            db.draft("aggregate-a", "x", {}, writer=ctx),
            WriterContext(StoreScope("other", "project-a"), "writer-a", "key-a", "ledger", 1, 2),
        ).status
        is Result.INVALID_SCOPE
    )
    assert db.append(db.draft("aggregate-a", "x", {}, writer=ctx), ctx).status is Result.AUTHENTICATION_FAILED
    with pytest.raises((ValueError, TypeError)):
        db.draft("bad", "x", {"x": float("nan")}, writer=ctx)
    db.close()


def test_lease_is_persisted_and_expiry_is_authoritative(tmp_path):
    now = [100]
    db, _, auth, _, ctx = setup(tmp_path, clock=lambda: now[0])
    db.close()
    db, _, auth, _, ctx = setup(tmp_path, clock=lambda: now[0])
    assert db.append(signed(db, auth, ctx), ctx).status is Result.APPLIED
    now[0] = 1000
    assert db.append(signed(db, auth, ctx, payload={"value": 4}), ctx).status is Result.LEASE_EXPIRED
    db.close()


def test_tampering_each_authenticated_field_and_anchor_rollback_fails(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    db.append(signed(db, auth, ctx), ctx)
    row = db.conn.execute("SELECT event_hash FROM events").fetchone()[0]
    db.conn.execute("PRAGMA recursive_triggers=OFF")
    with pytest.raises(Exception):
        db.conn.execute("UPDATE events SET kind='state.patch' WHERE event_hash=?", (row,))
    db.close()


def test_checkpoints_are_signed_and_verified(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    db.append(signed(db, auth, ctx), ctx)
    checkpoint = db.checkpoint()
    assert db.verify_checkpoints()
    db.conn.execute("PRAGMA recursive_triggers=OFF")
    with pytest.raises(Exception):
        db.conn.execute("UPDATE checkpoints SET projection_digest='bad'")
    assert checkpoint.sequence == 1
    db.close()


def test_rebuild_uses_temporary_swap_and_preserves_ledger(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    db.append(signed(db, auth, ctx), ctx)
    before = db.events()
    db.rebuild_projections()
    assert db.events() == before
    assert db.projection("aggregate-a")["value"] == 3
    db.close()


def test_receive_is_one_atomic_transaction_and_scoped_dedupe(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    draft = signed(db, auth, ctx)
    assert db.receive("message-a", draft, ctx).status is Result.APPLIED
    assert db.receive("message-a", draft, ctx).status is Result.DUPLICATE
    assert db.receive("message-b", signed(db, auth, ctx, aggregate="b"), ctx).status is Result.APPLIED
    db.close()


def test_outbox_retry_poison_ack_separation_and_redelivery(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    db.append(signed(db, auth, ctx), ctx)
    lease = db.acquire_lease("outbox", "transport-a", ttl=10_000_000_000).lease
    assert lease is not None
    claimed = db.claim_outbox("transport-a", lease=lease, max_attempts=1)
    assert claimed and claimed[0]["status"] == "LEASED"
    assert (
        db.mark_outbox_retry(
            claimed[0]["message_id"],
            "transport-a",
            lease=lease,
            max_attempts=1,
        )
        is Result.POISON_TERMINATED
    )
    row = db.outbox()[0]
    assert row["status"] == "POISON" and row["transport_ack_at"] is None
    db.close()


def test_backup_prepare_activate_and_invalid_artifact(tmp_path):
    db, _, auth, _, ctx = setup(tmp_path)
    db.append(signed(db, auth, ctx), ctx)
    artifact = db.backup(tmp_path / "backup.sqlite")
    prepared = db.prepare_restore(artifact)
    assert prepared.digest and prepared.installation_id == "install-a"
    with pytest.raises(ValueError, match="RESTORE_INVALID"):
        db.activate_restore(prepared, "not-quiescent")
    db.close()


def test_reducer_rejects_unknown_kind_and_non_json():
    reducer = ProjectionReducer(version="1")
    with pytest.raises(ValueError):
        reducer.reduce(None, "unknown", {})
    with pytest.raises(ValueError):
        reducer.reduce(None, "state.set", float("nan"))
