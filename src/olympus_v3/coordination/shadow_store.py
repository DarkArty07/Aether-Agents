"""Disposable SQLite persistence for default-off shadow correlation evidence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from .protocol import Principal, ValidationError
from .shadow import MAX_SHADOW_ASSIGNMENTS, ShadowSessionCorrelation, _canonical_root

_SCHEMA_VERSION = 1


class DurableShadowCorrelationRegistry:
    """A bounded, restart-safe implementation of the shadow ``consume`` protocol."""

    def __init__(
        self, path: str | Path, *, max_entries: int = MAX_SHADOW_ASSIGNMENTS, busy_timeout_ms: int = 250
    ) -> None:
        if (
            isinstance(max_entries, bool)
            or not isinstance(max_entries, int)
            or not 1 <= max_entries <= MAX_SHADOW_ASSIGNMENTS
        ):
            raise ValidationError("invalid shadow registry bound")
        if (
            isinstance(busy_timeout_ms, bool)
            or not isinstance(busy_timeout_ms, int)
            or not 0 <= busy_timeout_ms <= 5000
        ):
            raise ValidationError("invalid shadow busy timeout")
        self._path = str(path)
        self._max_entries = max_entries
        self._lock = Lock()
        self._conn = sqlite3.connect(self._path, timeout=busy_timeout_ms / 1000, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._initialize()

    def _initialize(self) -> None:
        try:
            integrity = self._conn.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise ValidationError("corrupt shadow store")
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS shadow_store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS shadow_correlations (
                    id INTEGER PRIMARY KEY, actual_session_id TEXT NOT NULL UNIQUE,
                    predicted_session_id TEXT NOT NULL UNIQUE, evidence_signature TEXT NOT NULL, binding TEXT NOT NULL
                );
            """)
            self._conn.execute(
                "INSERT OR IGNORE INTO shadow_store_meta VALUES ('schema_version', ?)",
                (str(_SCHEMA_VERSION),),
            )
            row = self._conn.execute("SELECT value FROM shadow_store_meta WHERE key='schema_version'").fetchone()
            if row is None or row[0] != str(_SCHEMA_VERSION):
                raise ValidationError("invalid shadow store schema version")
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            raise ValidationError("corrupt shadow store") from exc

    @staticmethod
    def _binding(c: ShadowSessionCorrelation) -> dict[str, Any]:
        if not isinstance(c, ShadowSessionCorrelation):
            raise ValidationError("invalid shadow correlation")
        values = (
            c.task_id,
            c.project_root,
            c.predicted_session_id,
            c.actual_session_id,
            c.evidence_signature,
            c.project_id,
            c.contract_id,
            c.generation,
        )
        if any(not isinstance(v, str) or not v or v != v.strip() for v in values[:5]):
            raise ValidationError("invalid shadow correlation")
        if not isinstance(c.participant, Principal):
            raise ValidationError("invalid shadow correlation participant")
        if c.project_id is None or c.contract_id is None or c.generation is None:
            raise ValidationError("incomplete shadow correlation context")
        if c.project_id != c.participant.project_id:
            raise ValidationError("cross-project shadow correlation")
        if isinstance(c.generation, bool) or not isinstance(c.generation, int) or c.generation < 0:
            raise ValidationError("invalid shadow correlation generation")
        return {
            "task_id": c.task_id,
            "project_root": _canonical_root(c.project_root),
            "project_id": c.project_id,
            "contract_id": c.contract_id,
            "generation": c.generation,
            "owner_id": c.participant.owner_id,
            "actor_id": c.participant.actor_id,
            "participant_project_id": c.participant.project_id,
            "predicted_session_id": c.predicted_session_id,
            "actual_session_id": c.actual_session_id,
            "evidence_signature": c.evidence_signature,
        }

    def consume(self, correlation: ShadowSessionCorrelation) -> bool:
        binding = self._binding(correlation)
        encoded = json.dumps(binding, sort_keys=True, separators=(",", ":"))
        with self._lock:
            return self._consume_locked(binding, encoded)

    def _consume_locked(self, binding: dict[str, Any], encoded: str) -> bool:
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            integrity = self._conn.execute("PRAGMA quick_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise ValidationError("corrupt shadow store")
            rows = self._conn.execute(
                "SELECT actual_session_id, predicted_session_id, evidence_signature, binding FROM shadow_correlations WHERE actual_session_id=? OR predicted_session_id=?",
                (binding["actual_session_id"], binding["predicted_session_id"]),
            ).fetchall()
            for actual, predicted, signature, stored in rows:
                try:
                    parsed = json.loads(stored)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValidationError("corrupt shadow correlation record") from exc
                if (
                    not isinstance(parsed, dict)
                    or parsed.get("actual_session_id") != actual
                    or parsed.get("predicted_session_id") != predicted
                    or parsed.get("evidence_signature") != signature
                ):
                    raise ValidationError("corrupt shadow correlation record")
                if parsed == binding:
                    self._conn.commit()
                    return True
                self._conn.rollback()
                return False
            count = self._conn.execute("SELECT COUNT(*) FROM shadow_correlations").fetchone()[0]
            if count >= self._max_entries:
                self._conn.rollback()
                return False
            self._conn.execute(
                "INSERT INTO shadow_correlations(actual_session_id,predicted_session_id,evidence_signature,binding) VALUES (?,?,?,?)",
                (binding["actual_session_id"], binding["predicted_session_id"], binding["evidence_signature"], encoded),
            )
            self._conn.commit()
            return True
        except ValidationError:
            self._conn.rollback()
            raise
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return False
        except sqlite3.OperationalError:
            self._conn.rollback()
            return False
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            raise ValidationError("corrupt shadow store") from exc

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
