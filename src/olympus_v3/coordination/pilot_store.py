"""Transactional, pilot-local SQLite state for R8."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from .pilot_model import (
    CANONICAL_CONTROL_ROOT,
    MAX_GLOBAL_RETRIES,
    MAX_TASK_ATTEMPTS,
    PilotError,
    PilotManifest,
    TaskStatus,
)

SCHEMA_VERSION = 3


class PilotStore:
    def __init__(self, path: Path, *, control_root: Path = CANONICAL_CONTROL_ROOT) -> None:
        self.path = Path(path)
        control_root = Path(control_root)
        if not self.path.is_absolute():
            raise PilotError("pilot store path must be absolute")
        if not control_root.is_absolute() or control_root != control_root.resolve(strict=False):
            raise PilotError("invalid control root")
        try:
            self.path.resolve(strict=False).relative_to(control_root)
        except ValueError as exc:
            raise PilotError("pilot store outside control root") from exc
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        try:
            self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None, timeout=1.0)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA busy_timeout=1000")
            self._initialize()
        except sqlite3.DatabaseError as exc:
            raise PilotError("pilot store unavailable") from exc

    def _initialize(self) -> None:
        with self._lock:
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise PilotError("pilot store corrupt")
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(
                    task_id TEXT PRIMARY KEY,
                    task_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    assignee TEXT NOT NULL,
                    session_id TEXT UNIQUE,
                    terminal_reason TEXT
                );
                CREATE TABLE IF NOT EXISTS intents(
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    session_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    PRIMARY KEY(task_id, attempt),
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                );
                CREATE TABLE IF NOT EXISTS events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    task_id TEXT,
                    attempt INTEGER,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence(
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    PRIMARY KEY(task_id, attempt),
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                );
                CREATE TABLE IF NOT EXISTS readonly_baselines(
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    PRIMARY KEY(task_id, attempt),
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                );
                """
            )
            self.db.execute(
                "INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
            row = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None or row[0] != str(SCHEMA_VERSION):
                raise PilotError("pilot schema mismatch")

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def install(self, manifest: PilotManifest) -> None:
        if not isinstance(manifest, PilotManifest):
            raise PilotError("invalid pilot manifest")
        with self._transaction():
            existing = self._meta("manifest_hash")
            if existing is not None:
                if existing != manifest.manifest_hash or self._meta("pilot_root") != manifest.root:
                    raise PilotError("pilot manifest mismatch")
                return
            self._set_meta("manifest_hash", manifest.manifest_hash)
            self._set_meta("manifest_json", manifest.canonical_json())
            self._set_meta("pilot_root", manifest.root)
            self._set_meta("generation", str(manifest.generation))
            self._set_meta("global_retries", "0")
            self._set_meta("pilot_status", "active")
            for task in manifest.tasks:
                payload = json.dumps(task.payload(), sort_keys=True, separators=(",", ":"))
                task_hash = hashlib.sha256(payload.encode()).hexdigest()
                self.db.execute(
                    "INSERT INTO tasks(task_id,task_hash,state,assignee) VALUES(?,?,?,?)",
                    (task.task_id, task_hash, TaskStatus.PENDING.value, task.assignee),
                )
            self.append_event("pilot_installed", None, 0, {"manifest_hash": manifest.manifest_hash})

    def verify_manifest(self, manifest: PilotManifest) -> None:
        if (
            self._meta("manifest_hash") != manifest.manifest_hash
            or self._meta("pilot_root") != manifest.root
            or self._meta("generation") != str(manifest.generation)
        ):
            raise PilotError("pilot manifest mismatch")

    def task(self, task_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise PilotError("unknown pilot task")
        return dict(row)

    def ready(self, manifest: PilotManifest) -> tuple[str, ...]:
        accepted = set(self.accepted())
        ready: list[str] = []
        for task in manifest.tasks:
            row = self.task(task.task_id)
            if (
                row["state"] in {TaskStatus.PENDING.value, TaskStatus.CORRECTION_REQUIRED.value}
                and set(task.depends_on) <= accepted
            ):
                ready.append(task.task_id)
        return tuple(ready)

    def running(self) -> tuple[str, ...]:
        return tuple(
            row[0]
            for row in self.db.execute(
                "SELECT task_id FROM tasks WHERE state IN (?,?) ORDER BY task_id",
                (TaskStatus.INTENT_RECORDED.value, TaskStatus.RUNNING.value),
            )
        )

    def accepted(self) -> tuple[str, ...]:
        return tuple(
            row[0]
            for row in self.db.execute(
                "SELECT task_id FROM tasks WHERE state=? ORDER BY task_id",
                (TaskStatus.ACCEPTED.value,),
            )
        )

    def record_intent(self, task_id: str, session_id: str) -> int:
        with self._transaction():
            row = self.task(task_id)
            if row["state"] not in {TaskStatus.PENDING.value, TaskStatus.CORRECTION_REQUIRED.value}:
                raise PilotError("task is not dispatchable")
            attempt = int(row["attempt"]) + 1
            if attempt > MAX_TASK_ATTEMPTS:
                raise PilotError("task attempt budget exhausted")
            retries = int(self._meta("global_retries") or "0")
            if attempt > 1:
                retries += 1
                if retries > MAX_GLOBAL_RETRIES:
                    raise PilotError("global retry budget exhausted")
                self._set_meta("global_retries", str(retries))
            self.db.execute(
                "UPDATE tasks SET state=?,attempt=?,session_id=?,terminal_reason=NULL WHERE task_id=?",
                (TaskStatus.INTENT_RECORDED.value, attempt, session_id, task_id),
            )
            self.db.execute(
                "INSERT INTO intents(task_id,attempt,session_id,status) VALUES(?,?,?,?)",
                (task_id, attempt, session_id, "recorded"),
            )
            self.append_event("dispatch_intent", task_id, attempt, {"session_id": session_id})
            return attempt

    def mark_running(self, task_id: str, attempt: int, session_id: str) -> None:
        with self._transaction():
            row = self.task(task_id)
            if (
                row["state"] != TaskStatus.INTENT_RECORDED.value
                or row["attempt"] != attempt
                or row["session_id"] != session_id
            ):
                raise PilotError("dispatch receipt binding mismatch")
            self.db.execute(
                "UPDATE tasks SET state=? WHERE task_id=?",
                (TaskStatus.RUNNING.value, task_id),
            )
            self.db.execute(
                "UPDATE intents SET status='sent' WHERE task_id=? AND attempt=?",
                (task_id, attempt),
            )
            self.append_event("dispatch_sent", task_id, attempt, {"session_id": session_id})

    def record_readonly_baseline(self, task_id: str, attempt: int, snapshot: dict[str, str]) -> None:
        payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self._transaction():
            row = self.task(task_id)
            if row["state"] != TaskStatus.INTENT_RECORDED.value or row["attempt"] != attempt:
                raise PilotError("read-only baseline state mismatch")
            self.db.execute(
                "INSERT INTO readonly_baselines(task_id,attempt,payload,payload_hash) VALUES(?,?,?,?)",
                (task_id, attempt, payload, digest),
            )

    def readonly_baseline(self, task_id: str, attempt: int) -> dict[str, str]:
        row = self.db.execute(
            "SELECT payload,payload_hash FROM readonly_baselines WHERE task_id=? AND attempt=?",
            (task_id, attempt),
        ).fetchone()
        if row is None or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            raise PilotError("read-only baseline unavailable")
        value = json.loads(row[0])
        if not isinstance(value, dict) or any(
            not isinstance(key, str) or not isinstance(item, str) for key, item in value.items()
        ):
            raise PilotError("invalid read-only baseline")
        return value

    def mark_blocked(self, task_id: str, reason: str) -> None:
        if not isinstance(reason, str) or not reason:
            raise PilotError("invalid terminal reason")
        with self._transaction():
            row = self.task(task_id)
            self.db.execute(
                "UPDATE tasks SET state=?,terminal_reason=? WHERE task_id=?",
                (TaskStatus.BLOCKED.value, reason, task_id),
            )
            self.append_event("task_blocked", task_id, int(row["attempt"]), {"reason": reason})

    def _accept_verified_evidence(
        self,
        task_id: str,
        attempt: int,
        payload: dict[str, Any],
        *,
        verified: bool,
    ) -> None:
        if verified is not True:
            raise PilotError("verified evidence required")
        if payload.get("status") not in {"completed", "accepted"} and payload.get("recommendation") == "accept":
            raise PilotError("invalid semantic result combination")
        if payload.get("recommendation") == "accept" and (
            not payload.get("verification") or any(item.get("exit_code") != 0 for item in payload["verification"])
        ):
            raise PilotError("successful verification required")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        with self._transaction():
            row = self.task(task_id)
            if row["state"] != TaskStatus.RUNNING.value or row["attempt"] != attempt:
                raise PilotError("evidence state mismatch")
            self.db.execute(
                "INSERT INTO evidence(task_id,attempt,payload,payload_hash) VALUES(?,?,?,?)",
                (task_id, attempt, encoded, digest),
            )
            next_state = (
                TaskStatus.ACCEPTED.value
                if payload["recommendation"] == "accept"
                else TaskStatus.CORRECTION_REQUIRED.value
            )
            self.db.execute("UPDATE tasks SET state=? WHERE task_id=?", (next_state, task_id))
            self.append_event("evidence_accepted", task_id, attempt, {"payload_hash": digest})

    def evidence(self, task_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload,payload_hash FROM evidence WHERE task_id=? ORDER BY attempt DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            raise PilotError("evidence corruption")
        return json.loads(row[0])

    def append_event(self, kind: str, task_id: str | None, attempt: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        event_id = hashlib.sha256(f"{kind}:{task_id}:{attempt}:{digest}".encode()).hexdigest()
        self.db.execute(
            "INSERT INTO events(event_id,task_id,attempt,kind,payload,payload_hash) VALUES(?,?,?,?,?,?)",
            (event_id, task_id, attempt, kind, encoded, digest),
        )

    def verify_integrity(self) -> None:
        with self._lock:
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise PilotError("pilot store corrupt")
            for row in self.db.execute("SELECT payload,payload_hash FROM events"):
                if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                    raise PilotError("pilot event corruption")
            for row in self.db.execute("SELECT payload,payload_hash FROM evidence"):
                if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                    raise PilotError("pilot evidence corruption")
            for row in self.db.execute("SELECT payload,payload_hash FROM readonly_baselines"):
                if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                    raise PilotError("pilot baseline corruption")

    def snapshot(self) -> dict[str, Any]:
        return {
            "manifest_hash": self._meta("manifest_hash"),
            "status": self._meta("pilot_status"),
            "global_retries": int(self._meta("global_retries") or "0"),
            "tasks": [dict(row) for row in self.db.execute("SELECT * FROM tasks ORDER BY rowid")],
        }

    def _meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def _set_meta(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    class _Transaction:
        def __init__(self, store: "PilotStore") -> None:
            self.store = store

        def __enter__(self) -> None:
            self.store._lock.acquire()
            try:
                self.store.db.execute("BEGIN IMMEDIATE")
            except Exception:
                self.store._lock.release()
                raise

        def __exit__(self, kind: Any, value: Any, traceback: Any) -> None:
            try:
                if kind is None:
                    self.store.db.commit()
                else:
                    self.store.db.rollback()
            finally:
                self.store._lock.release()

    def _transaction(self) -> "PilotStore._Transaction":
        return self._Transaction(self)


__all__ = ["PilotStore", "SCHEMA_VERSION"]
