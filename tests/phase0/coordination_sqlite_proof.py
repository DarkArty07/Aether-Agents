"""Tests-only stdlib SQLite coordination feasibility proof."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
from pathlib import Path

APPLIED = "APPLIED"
CAS_CONFLICT = "CAS_CONFLICT"
CONTENDED = "CONTENDED"
STALE_FENCE = "STALE_FENCE"
DUPLICATE = "DUPLICATE"
_KEY = b"phase0-fixed-test-only-hmac-key"


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(previous: str, aggregate: str, version: int, kind: str, payload: str) -> str:
    material = "|".join((previous, aggregate, str(version), kind, payload)).encode()
    return hashlib.sha256(material).hexdigest()


def _auth(event_hash: str) -> str:
    return hmac.new(_KEY, event_hash.encode(), hashlib.sha256).hexdigest()


class ProofDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=0.25, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, aggregate TEXT NOT NULL,
                version INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL, hash TEXT NOT NULL, auth_tag TEXT NOT NULL,
                fence INTEGER NOT NULL DEFAULT 0, UNIQUE(aggregate, version)
            );
            CREATE TABLE IF NOT EXISTS projections (
                aggregate TEXT PRIMARY KEY, version INTEGER NOT NULL, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbox (
                message_id TEXT PRIMARY KEY, event_id INTEGER NOT NULL, status TEXT NOT NULL,
                lease_owner TEXT, lease_until REAL, attempts INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS inbox (
                message_id TEXT PRIMARY KEY, applied_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fences (
                owner TEXT PRIMARY KEY, token INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contracts (
                name TEXT NOT NULL, generation INTEGER NOT NULL, document TEXT NOT NULL,
                PRIMARY KEY(name, generation)
            );
            CREATE TRIGGER IF NOT EXISTS immutable_contracts_update
            BEFORE UPDATE ON contracts BEGIN SELECT RAISE(ABORT, 'immutable contract'); END;
            CREATE TRIGGER IF NOT EXISTS immutable_contracts_delete
            BEFORE DELETE ON contracts BEGIN SELECT RAISE(ABORT, 'immutable contract'); END;
            """
        )

    def close(self):
        self.conn.close()

    def events(self):
        return [dict(row) for row in self.conn.execute("SELECT * FROM events ORDER BY id")]

    def projection(self, aggregate):
        row = self.conn.execute("SELECT * FROM projections WHERE aggregate = ?", (aggregate,)).fetchone()
        if row is None:
            return None
        result = json.loads(row["value"])
        result["version"] = row["version"]
        return result

    def outbox(self):
        return [dict(row) for row in self.conn.execute("SELECT * FROM outbox ORDER BY event_id")]

    def verify_events(self):
        previous = "GENESIS"
        for event in self.events():
            expected = _digest(previous, event["aggregate"], event["version"], event["kind"], event["payload"])
            if event["hash"] != expected or event["auth_tag"] != _auth(event["hash"]):
                raise ValueError("event integrity failure")
            previous = event["hash"]
        return True


def _begin(db: ProofDB) -> bool:
    try:
        db.conn.execute("BEGIN IMMEDIATE")
        return True
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            return False
        raise


def append_event(db: ProofDB, aggregate: str, kind: str, value: dict, *, expected_version: int = 0,
                 fence: int = 0, fence_owner: str | None = None,
                 fail_after_event: bool = False):
    if not _begin(db):
        return CONTENDED
    return _append_event(db, aggregate, kind, value, expected_version=expected_version,
                         fence=fence, fence_owner=fence_owner,
                         fail_after_event=fail_after_event)


def _append_event(db: ProofDB, aggregate: str, kind: str, value: dict, *, expected_version: int = 0,
                  fence: int = 0, fence_owner: str | None = None,
                  fail_after_event: bool = False, commit: bool = True):
    try:
        current = db.conn.execute("SELECT COALESCE(MAX(version), 0) FROM events WHERE aggregate = ?", (aggregate,)).fetchone()[0]
        if current != expected_version:
            db.conn.rollback()
            return CAS_CONFLICT
        if fence:
            owner = fence_owner or aggregate
            row = db.conn.execute("SELECT token FROM fences WHERE owner = ?", (owner,)).fetchone()
            token = row[0] if row else 0
            if fence < token:
                db.conn.rollback()
                return STALE_FENCE
        payload = _json(value)
        previous = db.conn.execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else "GENESIS"
        event_hash = _digest(previous_hash, aggregate, current + 1, kind, payload)
        cursor = db.conn.execute(
            "INSERT INTO events(aggregate,version,kind,payload,previous_hash,hash,auth_tag,fence) VALUES(?,?,?,?,?,?,?,?)",
            (aggregate, current + 1, kind, payload, previous_hash, event_hash, _auth(event_hash), fence),
        )
        db.conn.execute("INSERT OR REPLACE INTO projections VALUES(?,?,?)", (aggregate, current + 1, payload))
        db.conn.execute("INSERT INTO outbox VALUES(?,?,?,?,?,?)", (event_hash, cursor.lastrowid, "PENDING", None, None, 0))
        if fail_after_event:
            raise RuntimeError("injected rollback")
        if commit:
            db.conn.commit()
        return APPLIED
    except Exception:
        db.conn.rollback()
        raise


def acquire_fence(db: ProofDB, owner: str, requested: int) -> int:
    if not _begin(db):
        return CONTENDED
    row = db.conn.execute("SELECT token FROM fences WHERE owner = ?", (owner,)).fetchone()
    token = max(requested, row[0] if row else 0)
    db.conn.execute("INSERT OR REPLACE INTO fences VALUES(?,?)", (owner, token))
    db.conn.commit()
    return token


def apply_inbox(db: ProofDB, message_id: str, aggregate: str, kind: str, value: dict,
                *, fail_before_inbox: bool = False):
    if not _begin(db):
        return CONTENDED
    if db.conn.execute("SELECT 1 FROM inbox WHERE message_id = ?", (message_id,)).fetchone():
        db.conn.rollback()
        return DUPLICATE
    result = _append_event(db, aggregate, kind, value, commit=False)
    if result != APPLIED:
        db.conn.rollback()
        return result
    if fail_before_inbox:
        db.conn.rollback()
        raise RuntimeError("injected failure before inbox commit")
    db.conn.execute("INSERT INTO inbox VALUES(?,?)", (message_id, time.time()))
    db.conn.commit()
    return APPLIED


def claim_outbox(db: ProofDB, owner: str, lease_seconds: float = 30):
    if not _begin(db):
        return []
    now = time.time()
    rows = db.conn.execute(
        "SELECT * FROM outbox WHERE status IN ('PENDING','FAILED','LEASED') "
        "AND (status != 'LEASED' OR lease_until <= ?) ORDER BY event_id", (now,)
    ).fetchall()
    result = []
    for row in rows:
        db.conn.execute("UPDATE outbox SET status='LEASED', lease_owner=?, lease_until=?, attempts=attempts+1 WHERE message_id=?",
                        (owner, now + lease_seconds, row["message_id"]))
        result.append(dict(row) | {"status": "LEASED", "lease_owner": owner})
    db.conn.commit()
    return result


def fail_outbox(db: ProofDB, message_id: str, owner: str):
    db.conn.execute("UPDATE outbox SET status='FAILED', lease_owner=NULL, lease_until=NULL WHERE message_id=? AND lease_owner=?",
                    (message_id, owner))
    return "FAILED"


def send_outbox(db: ProofDB, message_id: str, owner: str):
    db.conn.execute("UPDATE outbox SET status='SENT', lease_owner=NULL, lease_until=NULL WHERE message_id=? AND (lease_owner=? OR status='SENT')",
                    (message_id, owner))
    db.conn.commit()
    return "SENT"


def rebuild_projection(db: ProofDB):
    rebuilt = {}
    for event in db.events():
        value = json.loads(event["payload"])
        value["version"] = event["version"]
        rebuilt[event["aggregate"]] = value
    return rebuilt


def backup_and_verify(db: ProofDB, artifact: str | Path):
    target = sqlite3.connect(artifact)
    db.conn.backup(target)
    target.execute("PRAGMA integrity_check").fetchone()
    target.commit()
    target.close()
    copied = ProofDB(artifact)
    copied.verify_events()
    copied.close()


def create_contract(db: ProofDB, name: str, generation: int, document: dict):
    try:
        latest = db.conn.execute("SELECT MAX(generation) FROM contracts WHERE name = ?", (name,)).fetchone()[0]
        if latest is not None and generation <= latest:
            return "IMMUTABLE"
        db.conn.execute("INSERT INTO contracts VALUES(?,?,?)", (name, generation, _json(document)))
        return "CREATED"
    except sqlite3.IntegrityError:
        return "IMMUTABLE"
