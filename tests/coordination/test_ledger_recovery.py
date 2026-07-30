import os
import shutil
import sqlite3
import stat
from pathlib import Path

import pytest

from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    TrustedAnchorStore,
    WriterContext,
)
from olympus_v3.coordination.projections import ProjectionReducer

AUTHENTICATED_EVENT_TAMPERS = {
    "encoding_version": 2,
    "installation_id": "install-evil",
    "project_id": "project-evil",
    "sequence": 2,
    "server_time": 1,
    "event_id": "event-evil",
    "aggregate": "aggregate-evil",
    "version": 2,
    "kind": "state.patch",
    "payload": '{"value":999}',
    "previous_hash": "BAD",
    "event_hash": "0" * 64,
    "writer_id": "writer-evil",
    "key_id": "key-evil",
    "resource": "other",
    "fence": 2,
    "writer_proof": "bad-proof",
    "auth_tag": "bad-tag",
}


def setup(tmp_path: Path, *, reducer: ProjectionReducer | None = None):
    scope = StoreScope("install-a", "project-a")
    auth = HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"})
    signer = HMACIntegritySigner(b"integrity-key", key_id="integrity-a")
    path = tmp_path / "coord.sqlite"
    db = SQLiteLedger(
        path,
        scope,
        writer_authenticator=auth,
        integrity_signer=signer,
        reducer=reducer,
    )
    lease = db.acquire_lease("ledger", "writer-a", ttl=10_000_000_000).lease
    assert lease is not None
    context = WriterContext(scope, "writer-a", "key-a", "ledger", lease.epoch, lease.expires_at)
    return db, scope, auth, signer, context


def append(db: SQLiteLedger, auth: HMACWriterAuthenticator, context: WriterContext, value: int):
    current = db.projection("aggregate-a")
    expected_version = current["version"] if current else 0
    draft = db.draft(
        "aggregate-a",
        "state.set",
        {"value": value},
        writer=context,
        expected_version=expected_version,
    )
    result = db.append(auth.sign(draft, context), context)
    assert result.status is Result.APPLIED
    return result.event


def copy_database(db: SQLiteLedger, target: Path) -> Path:
    destination = sqlite3.connect(target)
    try:
        db.conn.backup(destination)
    finally:
        destination.close()
    return target


def tamper(path: Path, table: str, column: str, value) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"DROP TRIGGER IF EXISTS immutable_{table}_update")
        connection.execute(f"UPDATE {table} SET {column}=?", (value,))
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize(("column", "value"), AUTHENTICATED_EVENT_TAMPERS.items())
def test_copied_artifact_rejects_every_authenticated_event_field_tamper(tmp_path, column, value):
    db, scope, auth, signer, context = setup(tmp_path)
    append(db, auth, context, 1)
    artifact = copy_database(db, tmp_path / f"tampered-{column}.sqlite")
    tamper(artifact, "events", column, value)

    probe = SQLiteLedger(artifact, scope, writer_authenticator=auth, integrity_signer=signer)
    with pytest.raises(ValueError, match=Result.INTEGRITY_FAILURE.value):
        probe.verify_chain()
    probe.close()
    db.close()


@pytest.mark.parametrize(
    ("column", "value"),
    {
        "encoding_version": 2,
        "sequence": 2,
        "event_hash": "0" * 64,
        "projection_digest": "0" * 64,
        "key_id": "integrity-evil",
        "created_at": 1,
        "signature": "bad-signature",
    }.items(),
)
def test_checkpoint_rejects_field_tamper_in_copied_artifact(tmp_path, column, value):
    db, scope, auth, signer, context = setup(tmp_path)
    append(db, auth, context, 1)
    db.checkpoint()
    artifact = copy_database(db, tmp_path / f"checkpoint-{column}.sqlite")
    tamper(artifact, "checkpoints", column, value)

    probe = SQLiteLedger(artifact, scope, writer_authenticator=auth, integrity_signer=signer)
    with pytest.raises(ValueError, match=Result.INTEGRITY_FAILURE.value):
        probe.verify_checkpoints()
    probe.close()
    db.close()


def test_checkpoint_covers_reconstructed_projection_not_mutable_projection_table(tmp_path):
    db, _, auth, _, context = setup(tmp_path)
    append(db, auth, context, 1)
    db.checkpoint()
    db.conn.execute("UPDATE projections SET value='{}'")
    db.conn.commit()

    with pytest.raises(ValueError, match=Result.PROJECTION_MISMATCH.value):
        db.verify_checkpoints()
    db.close()


def test_projection_verification_uses_one_snapshot_during_concurrent_append(tmp_path, monkeypatch):
    writer, scope, auth, signer, context = setup(tmp_path)
    append(writer, auth, context, 1)
    reader = SQLiteLedger(
        writer.path,
        scope,
        writer_authenticator=auth,
        integrity_signer=signer,
    )
    original_projection_digest = reader._projection_digest
    concurrent_append_committed = False

    def projection_digest_after_concurrent_append():
        nonlocal concurrent_append_committed
        if not concurrent_append_committed:
            append(writer, auth, context, 2)
            concurrent_append_committed = True
        return original_projection_digest()

    monkeypatch.setattr(reader, "_projection_digest", projection_digest_after_concurrent_append)
    try:
        assert reader.verify_projections()
        assert concurrent_append_committed
        assert writer.verify_projections()
    finally:
        reader.close()
        writer.close()


def test_external_anchor_rejects_missing_mismatch_and_short_rollback(tmp_path):
    db, scope, auth, signer, context = setup(tmp_path)
    first = append(db, auth, context, 1)
    second = append(db, auth, context, 2)
    assert first is not None and second is not None

    missing = TrustedAnchorStore()
    with pytest.raises(ValueError, match=Result.ANCHOR_UNAVAILABLE.value):
        db.verify_chain(missing)

    mismatch = TrustedAnchorStore()
    mismatch.put(scope, second.sequence, "0" * 64)
    with pytest.raises(ValueError, match=Result.ANCHOR_ROLLBACK.value):
        db.verify_chain(mismatch)

    trusted = TrustedAnchorStore()
    trusted.put(scope, second.sequence, second.event_hash)
    old = db.backup(tmp_path / "old.sqlite")
    rolled_back = tmp_path / "rolled-back.sqlite"
    shutil.copy2(old, rolled_back)
    connection = sqlite3.connect(rolled_back)
    connection.execute("DROP TRIGGER immutable_events_delete")
    connection.execute("DELETE FROM events WHERE sequence=2")
    connection.commit()
    connection.close()
    probe = SQLiteLedger(rolled_back, scope, writer_authenticator=auth, integrity_signer=signer)
    with pytest.raises(ValueError, match=Result.ANCHOR_ROLLBACK.value):
        probe.verify_chain(trusted)
    probe.close()
    db.close()


def test_trusted_anchor_cannot_equivocate_at_same_sequence():
    scope = StoreScope("install-a", "project-a")
    store = TrustedAnchorStore()
    store.put(scope, 3, "a" * 64)
    store.put(scope, 3, "a" * 64)

    with pytest.raises(ValueError, match="anchor rollback"):
        store.put(scope, 3, "b" * 64)
    assert store.get(scope) == (3, "a" * 64)


def test_rebuild_is_equivalent_preserves_events_and_rejects_reducer_mismatch(tmp_path):
    db, scope, auth, signer, context = setup(tmp_path)
    append(db, auth, context, 1)
    before_events = db.events()
    expected = db.projection("aggregate-a")
    db.conn.execute("DELETE FROM projections")
    db.rebuild_projections()
    assert db.projection("aggregate-a") == expected
    assert db.events() == before_events
    db.close()

    incompatible = SQLiteLedger(
        tmp_path / "coord.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=signer,
        reducer=ProjectionReducer(version="2"),
    )
    with pytest.raises(ValueError, match="reducer version"):
        incompatible.rebuild_projections()
    assert incompatible.events() == before_events
    incompatible.close()


def test_backup_is_verified_private_and_collision_safe(tmp_path):
    db, _, auth, _, context = setup(tmp_path)
    append(db, auth, context, 1)
    db.checkpoint()
    target = db.backup(tmp_path / "backup.sqlite")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    connection = sqlite3.connect(target)
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    connection.close()
    with pytest.raises(FileExistsError):
        db.backup(target)
    db.close()


def test_backup_does_not_overwrite_artifact_created_during_publication(tmp_path, monkeypatch):
    db, _, auth, _, context = setup(tmp_path)
    append(db, auth, context, 1)
    target = tmp_path / "raced-backup.sqlite"
    original_chmod = os.chmod

    def create_competing_artifact(path, mode):
        original_chmod(path, mode)
        if Path(path).name.startswith(".backup-"):
            target.write_bytes(b"competitor")

    monkeypatch.setattr("olympus_v3.coordination.ledger.os.chmod", create_competing_artifact)
    with pytest.raises(FileExistsError):
        db.backup(target)
    assert target.read_bytes() == b"competitor"
    db.close()


def test_prepare_restore_verifies_chain_checkpoint_anchor_and_projection(tmp_path):
    db, scope, auth, _, context = setup(tmp_path)
    event = append(db, auth, context, 1)
    assert event is not None
    db.checkpoint()
    anchor = TrustedAnchorStore()
    anchor.put(scope, event.sequence, event.event_hash)
    artifact = db.backup(tmp_path / "restore.sqlite", anchor)
    tamper(artifact, "events", "payload", '{"value":999}')

    with pytest.raises(ValueError, match=Result.RESTORE_INVALID.value):
        db.prepare_restore(artifact, anchor)
    db.close()


def test_restore_activation_requires_closed_store_matching_token_and_untampered_artifact(tmp_path):
    db, scope, auth, signer, context = setup(tmp_path)
    append(db, auth, context, 1)
    artifact = db.backup(tmp_path / "restore.sqlite")
    prepared = db.prepare_restore(artifact)

    with pytest.raises(ValueError, match=Result.RESTORE_INVALID.value):
        db.activate_restore(prepared, prepared.quiescence_token)
    db.close()
    with pytest.raises(ValueError, match=Result.RESTORE_INVALID.value):
        db.activate_restore(prepared, "wrong-token")

    db.activate_restore(prepared, prepared.quiescence_token)
    assert stat.S_IMODE((tmp_path / "coord.sqlite").stat().st_mode) == 0o600
    restored = SQLiteLedger(
        tmp_path / "coord.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=signer,
    )
    assert restored.verify_chain()
    assert restored.verify_checkpoints()
    assert restored.verify_projections()
    projection = restored.projection("aggregate-a")
    assert projection is not None and projection["value"] == 1
    restored.close()
