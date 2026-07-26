"""Project-scoped Harmonia store identity and cold read-only inspection.

The inspector intentionally does not construct :class:`SQLiteLedger`: its
constructor creates directories, enables WAL and runs migrations. Status reads
must have no such authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

_STORE_FILENAME = "coordination-v0.19.1.sqlite"
_REQUIRED_SCHEMA: dict[str, frozenset[str]] = {
    "events": frozenset(
        {
            "installation_id",
            "project_id",
            "sequence",
            "event_id",
            "aggregate",
            "version",
            "kind",
            "payload",
            "contract_id",
            "contract_generation",
            "revocation_epoch",
        }
    ),
    "projections": frozenset(
        {"installation_id", "project_id", "aggregate", "version", "value", "reducer_version"}
    ),
    "outbox": frozenset(
        {
            "installation_id",
            "project_id",
            "message_id",
            "event_id",
            "status",
            "attempts",
            "contract_id",
            "contract_generation",
            "revocation_epoch",
            "reconciliation_required",
        }
    ),
    "contract_versions": frozenset(
        {
            "installation_id",
            "project_id",
            "contract_id",
            "generation",
            "document",
            "revocation_epoch",
        }
    ),
    "contract_heads": frozenset(
        {"installation_id", "project_id", "contract_id", "generation", "revocation_epoch"}
    ),
}


def _domain_digest(domain: str, value: str) -> str:
    return hashlib.sha256((domain + "\0" + value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectStoreIdentity:
    canonical_aether_home: Path
    canonical_project_root: Path
    installation_id: str
    project_id: str
    store_path: Path


class InspectionCategory(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    STORAGE_CORRUPT = "storage_corrupt"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"


@dataclass(frozen=True, slots=True)
class HarmoniaRunSnapshot:
    run_id: str
    events: tuple[dict[str, Any], ...]
    outbox: tuple[dict[str, Any], ...]
    contract_document: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class InspectionResult:
    category: InspectionCategory
    snapshot: HarmoniaRunSnapshot | None = None


def derive_project_store(aether_home: str | Path, project_root: str | Path) -> ProjectStoreIdentity:
    """Derive all project storage identity without creating filesystem state."""
    canonical_home = Path(aether_home).expanduser().resolve()
    canonical_root = Path(project_root).expanduser().resolve()
    installation_id = _domain_digest("olympus-installation-v1", str(canonical_home))
    project_id = _domain_digest("olympus-project-v1", str(canonical_root))
    store_path = canonical_home / ".olympus" / "projects" / project_id / _STORE_FILENAME
    return ProjectStoreIdentity(canonical_home, canonical_root, installation_id, project_id, store_path)


class ProjectInspector:
    """Known-query, URI read-only inspector for one derived project store."""

    def __init__(self, identity: ProjectStoreIdentity) -> None:
        if not isinstance(identity, ProjectStoreIdentity):
            raise TypeError("identity must be a ProjectStoreIdentity")
        self.identity = identity

    def inspect_run(self, run_id: str) -> InspectionResult:
        path = self.identity.store_path
        if not path.parent.is_dir() or not path.is_file():
            return InspectionResult(InspectionCategory.NOT_FOUND)

        with tempfile.TemporaryDirectory(prefix="harmonia-inspect-") as temporary:
            snapshot_path = Path(temporary) / _STORE_FILENAME
            if not self._copy_stable_store(path, snapshot_path):
                return InspectionResult(InspectionCategory.STORAGE_CORRUPT)
            connection: sqlite3.Connection | None = None
            try:
                connection = sqlite3.connect(
                    snapshot_path.as_uri() + "?mode=ro", uri=True, isolation_level=None
                )
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only=ON")
                if not self._schema_is_compatible(connection):
                    return InspectionResult(InspectionCategory.SCHEMA_INCOMPATIBLE)
                snapshot = self._read_snapshot(connection, run_id)
                if snapshot is None:
                    return InspectionResult(InspectionCategory.NOT_FOUND)
                return InspectionResult(InspectionCategory.FOUND, snapshot)
            except (json.JSONDecodeError, sqlite3.DatabaseError, TypeError, ValueError):
                return InspectionResult(InspectionCategory.STORAGE_CORRUPT)
            finally:
                if connection is not None:
                    connection.close()

    @staticmethod
    def _copy_stable_store(source: Path, destination: Path) -> bool:
        """Copy a stable DB/WAL view without opening or mutating the source."""
        for _attempt in range(3):
            source_files = [source]
            wal = Path(str(source) + "-wal")
            if wal.is_file():
                source_files.append(wal)
            try:
                before = {path.name: ProjectInspector._file_fingerprint(path) for path in source_files}
                for path in source_files:
                    suffix = "-wal" if path == wal else ""
                    target = Path(str(destination) + suffix)
                    shutil.copyfile(path, target)
                    os.chmod(target, 0o600)
                current_files = [source]
                if wal.is_file():
                    current_files.append(wal)
                after = {path.name: ProjectInspector._file_fingerprint(path) for path in current_files}
                if before == after:
                    return True
            except OSError:
                return False
            for suffix in ("", "-wal", "-shm"):
                Path(str(destination) + suffix).unlink(missing_ok=True)
        return False

    @staticmethod
    def _file_fingerprint(path: Path) -> tuple[int, int, str]:
        stat = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return stat.st_size, stat.st_mtime_ns, digest.hexdigest()

    @staticmethod
    def _schema_is_compatible(connection: sqlite3.Connection) -> bool:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = {str(row[0]) for row in rows}
        if not set(_REQUIRED_SCHEMA).issubset(tables):
            return False
        for table, required_columns in _REQUIRED_SCHEMA.items():
            columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
            if not required_columns.issubset(columns):
                return False
        return True

    def _read_snapshot(self, connection: sqlite3.Connection, run_id: str) -> HarmoniaRunSnapshot | None:
        scope = (self.identity.installation_id, self.identity.project_id)
        rows = connection.execute(
            """SELECT sequence,event_id,aggregate,version,kind,payload,contract_id,
                      contract_generation,revocation_epoch
               FROM events
               WHERE installation_id=? AND project_id=?
               ORDER BY sequence""",
            scope,
        ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload"])
            if not isinstance(payload, dict):
                raise ValueError("invalid event payload")
            if payload.get("run_id") != run_id:
                continue
            events.append(
                {
                    "sequence": row["sequence"],
                    "event_id": row["event_id"],
                    "aggregate": row["aggregate"],
                    "version": row["version"],
                    "kind": row["kind"],
                    "payload": payload,
                    "contract_id": row["contract_id"],
                    "contract_generation": row["contract_generation"],
                    "revocation_epoch": row["revocation_epoch"],
                }
            )
        if not any(
            event["kind"] == "run.created" and event["aggregate"] == "run:" + run_id for event in events
        ):
            return None

        message_ids = {
            event["payload"].get("message_id")
            for event in events
            if event["kind"] == "dispatch.staged" and isinstance(event["payload"].get("message_id"), str)
        }
        outbox: list[dict[str, Any]] = []
        for row in connection.execute(
            """SELECT message_id,event_id,status,attempts,last_error,transport_ack_at,
                      semantic_completion_event_id,contract_id,contract_generation,
                      revocation_epoch,reconciliation_required
               FROM outbox
               WHERE installation_id=? AND project_id=?
               ORDER BY message_id""",
            scope,
        ).fetchall():
            if row["message_id"] in message_ids:
                outbox.append(dict(row))

        run_created = next(event for event in events if event["kind"] == "run.created")
        contract_id = run_created["payload"].get("contract_id")
        contract_document = self._read_contract(connection, contract_id) if isinstance(contract_id, str) else None
        return HarmoniaRunSnapshot(run_id, tuple(events), tuple(outbox), contract_document)

    def _read_contract(self, connection: sqlite3.Connection, contract_id: str) -> dict[str, Any] | None:
        row = connection.execute(
            """SELECT versions.document
               FROM contract_heads AS heads
               JOIN contract_versions AS versions
                 ON versions.installation_id=heads.installation_id
                AND versions.project_id=heads.project_id
                AND versions.contract_id=heads.contract_id
                AND versions.generation=heads.generation
               WHERE heads.installation_id=? AND heads.project_id=? AND heads.contract_id=?""",
            (self.identity.installation_id, self.identity.project_id, contract_id),
        ).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        if not isinstance(value, dict):
            raise ValueError("invalid contract document")
        return value
