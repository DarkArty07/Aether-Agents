from __future__ import annotations

import sqlite3

import pytest

from olympus_v3.coordination import HMACIntegritySigner, HMACWriterAuthenticator, SQLiteLedger, StoreScope


def _old_outbox(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE outbox(
      installation_id TEXT NOT NULL, project_id TEXT NOT NULL, message_id TEXT NOT NULL, event_id TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('PENDING','LEASED','RETRY_WAIT','SENT','POISON')), attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT, lease_owner TEXT, lease_until INTEGER, transport_ack_at INTEGER, semantic_completion_event_id TEXT,
      PRIMARY KEY(installation_id,project_id,message_id));
    CREATE UNIQUE INDEX outbox_message_identity ON outbox(installation_id,project_id,message_id);
    CREATE INDEX outbox_claimable ON outbox(status, lease_until, attempts);
    """)
    rows = [
        ("install-a", "project-a", "msg-1", "event-1", "PENDING", 2, "old error", "worker-a", 101, 102, "completion-1"),
        ("install-a", "project-a", "msg-2", "event-2", "LEASED", 7, None, "worker-b", 202, 203, None),
    ]
    conn.executemany("INSERT INTO outbox VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return rows


def _ledger(path):
    return SQLiteLedger(
        path, StoreScope("install-a", "project-a"),
        writer_authenticator=HMACWriterAuthenticator({}),
        integrity_signer=HMACIntegritySigner(b"integrity"),
    )


def test_legacy_outbox_migration_preserves_rows_and_claim_indexes(tmp_path):
    path = tmp_path / "legacy.sqlite"
    rows = _old_outbox(path)
    ledger = _ledger(path)
    actual = ledger.conn.execute(
        "SELECT installation_id,project_id,message_id,event_id,status,attempts,last_error,lease_owner,lease_until,transport_ack_at,semantic_completion_event_id FROM outbox ORDER BY message_id"
    ).fetchall()
    assert [tuple(row) for row in actual] == rows
    columns = {row[1] for row in ledger.conn.execute("PRAGMA table_info(outbox)")}
    assert {"lease_epoch", "lease_token", "contract_id", "contract_generation", "revocation_epoch", "reconciliation_required"} <= columns
    indexes = {row[1] for row in ledger.conn.execute("PRAGMA index_list(outbox)")}
    assert {"outbox_message_identity", "outbox_claimable"} <= indexes
    ledger.close()


def test_legacy_outbox_migration_failure_rolls_back_and_reopens(tmp_path, monkeypatch):
    path = tmp_path / "legacy-failure.sqlite"
    rows = _old_outbox(path)
    original = SQLiteLedger._stage

    def fail_after_copy(self, point):
        if point == "after_outbox_legacy_copy":
            raise RuntimeError("injected migration crash")
        return original(self, point)

    monkeypatch.setattr(SQLiteLedger, "_stage", fail_after_copy)
    with pytest.raises(RuntimeError):
        _ledger(path)
    monkeypatch.setattr(SQLiteLedger, "_stage", original)
    reopened = _ledger(path)
    actual = reopened.conn.execute("SELECT message_id,status,attempts,last_error FROM outbox ORDER BY message_id").fetchall()
    assert [tuple(row) for row in actual] == [(r[2], r[4], r[5], r[6]) for r in rows]
    reopened.close()
