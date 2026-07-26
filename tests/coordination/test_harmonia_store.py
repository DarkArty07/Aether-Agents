from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from pathlib import Path

from olympus_v3.acp_manager import ACPManager
from olympus_v3.coordination.harmonia_store import (
    InspectionCategory,
    ProjectInspector,
    derive_project_store,
)


def _create_store(identity, *, run_id: str = "run-" + "a" * 32, wal: bool = False):
    identity.store_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(identity.store_path)
    if wal:
        connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(
        """
        CREATE TABLE events(
          installation_id TEXT NOT NULL, project_id TEXT NOT NULL, sequence INTEGER NOT NULL,
          event_id TEXT NOT NULL, server_time INTEGER NOT NULL, aggregate TEXT NOT NULL,
          version INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
          previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL, writer_id TEXT NOT NULL,
          key_id TEXT NOT NULL, resource TEXT NOT NULL, fence INTEGER NOT NULL,
          writer_proof TEXT NOT NULL, auth_tag TEXT NOT NULL, encoding_version INTEGER NOT NULL,
          contract_id TEXT, contract_generation INTEGER, revocation_epoch INTEGER
        );
        CREATE TABLE projections(
          installation_id TEXT NOT NULL, project_id TEXT NOT NULL, aggregate TEXT NOT NULL,
          version INTEGER NOT NULL, value TEXT NOT NULL, reducer_version TEXT NOT NULL,
          source_sequence INTEGER NOT NULL, source_hash TEXT NOT NULL
        );
        CREATE TABLE outbox(
          installation_id TEXT NOT NULL, project_id TEXT NOT NULL, message_id TEXT NOT NULL,
          event_id TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL,
          last_error TEXT, lease_owner TEXT, lease_epoch INTEGER, lease_token TEXT,
          lease_until INTEGER, transport_ack_at INTEGER, semantic_completion_event_id TEXT,
          contract_id TEXT, contract_generation INTEGER, revocation_epoch INTEGER,
          reconciliation_required INTEGER NOT NULL
        );
        CREATE TABLE contract_versions(
          installation_id TEXT NOT NULL, project_id TEXT NOT NULL, contract_id TEXT NOT NULL,
          generation INTEGER NOT NULL, document TEXT NOT NULL, revocation_epoch INTEGER NOT NULL
        );
        CREATE TABLE contract_heads(
          installation_id TEXT NOT NULL, project_id TEXT NOT NULL, contract_id TEXT NOT NULL,
          generation INTEGER NOT NULL, revocation_epoch INTEGER NOT NULL
        );
        """
    )
    payload = json.dumps(
        {
            "run_id": run_id,
            "contract_id": "contract-" + "b" * 32,
            "mode": "kernel",
            "request_id": "slice-2",
            "request_digest": "sha256:" + "c" * 64,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    connection.execute(
        """INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            identity.installation_id,
            identity.project_id,
            1,
            "event-1",
            1,
            "run:" + run_id,
            1,
            "run.created",
            payload,
            "0" * 64,
            "1" * 64,
            "hermes",
            "harmonia-writer-v1",
            "harmonia-ledger-owner",
            1,
            "proof",
            "tag",
            1,
            "contract-" + "b" * 32,
            0,
            0,
        ),
    )
    connection.commit()
    return connection


def _fingerprint(directory: Path):
    if not directory.exists():
        return None
    result = {}
    for path in sorted(directory.iterdir()):
        stat = path.stat()
        result[path.name] = (
            stat.st_mode,
            stat.st_size,
            stat.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        )
    return result


def test_equivalent_distinct_and_symlink_roots_have_expected_project_identity(tmp_path):
    aether_home = tmp_path / "aether-home"
    root_a = tmp_path / "projects" / "a"
    root_b = tmp_path / "projects" / "b"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)
    alias = tmp_path / "alias-a"
    alias.symlink_to(root_a, target_is_directory=True)

    direct = derive_project_store(aether_home, root_a)
    equivalent = derive_project_store(aether_home / ".", root_a / ".")
    symlinked = derive_project_store(aether_home, alias)
    distinct = derive_project_store(aether_home, root_b)

    assert direct == equivalent == symlinked
    assert direct.project_id != distinct.project_id
    assert direct.canonical_project_root == Path(ACPManager._canonical_project_root(str(alias)))
    assert len(direct.installation_id) == 64
    assert len(direct.project_id) == 64


def test_store_path_is_derived_under_aether_home_and_caller_cannot_supply_it(tmp_path):
    aether_home = tmp_path / "aether-home"
    project = tmp_path / "project"
    project.mkdir()

    identity = derive_project_store(aether_home, project)

    assert identity.store_path == (
        aether_home.resolve()
        / ".olympus"
        / "projects"
        / identity.project_id
        / "coordination-v0.19.1.sqlite"
    )
    assert set(inspect.signature(ProjectInspector).parameters) == {"identity"}


def test_absent_status_creates_no_parent_database_wal_or_shm(tmp_path):
    aether_home = tmp_path / "absent-home"
    project = tmp_path / "project"
    project.mkdir()
    identity = derive_project_store(aether_home, project)
    inspector = ProjectInspector(identity)

    before = _fingerprint(aether_home)
    result = inspector.inspect_run("run-" + "a" * 32)
    after = _fingerprint(aether_home)

    assert result.category is InspectionCategory.NOT_FOUND
    assert result.snapshot is None
    assert before is None and after is None


def test_active_wal_status_reads_committed_run_without_changing_store_fingerprint(tmp_path):
    aether_home = tmp_path / "aether-home"
    project = tmp_path / "project"
    project.mkdir()
    identity = derive_project_store(aether_home, project)
    run_id = "run-" + "a" * 32
    writer = _create_store(identity, run_id=run_id, wal=True)
    try:
        before = _fingerprint(identity.store_path.parent)
        result = ProjectInspector(identity).inspect_run(run_id)
        after = _fingerprint(identity.store_path.parent)
    finally:
        writer.close()

    assert result.category is InspectionCategory.FOUND
    assert result.snapshot is not None
    assert result.snapshot.run_id == run_id
    assert [event["kind"] for event in result.snapshot.events] == ["run.created"]
    assert result.snapshot.outbox == ()
    assert before == after


def test_cross_project_run_lookup_does_not_fall_back_to_another_store(tmp_path):
    aether_home = tmp_path / "aether-home"
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    identity_a = derive_project_store(aether_home, root_a)
    identity_b = derive_project_store(aether_home, root_b)
    connection = _create_store(identity_a)
    connection.close()

    result = ProjectInspector(identity_b).inspect_run("run-" + "a" * 32)

    assert result.category is InspectionCategory.NOT_FOUND
    assert not identity_b.store_path.parent.exists()


def test_missing_corrupt_and_incompatible_stores_are_categorized(tmp_path):
    aether_home = tmp_path / "aether-home"
    missing_root = tmp_path / "missing-project"
    corrupt_root = tmp_path / "corrupt-project"
    incompatible_root = tmp_path / "incompatible-project"
    for root in (missing_root, corrupt_root, incompatible_root):
        root.mkdir()

    missing = derive_project_store(aether_home, missing_root)
    corrupt = derive_project_store(aether_home, corrupt_root)
    incompatible = derive_project_store(aether_home, incompatible_root)

    corrupt.store_path.parent.mkdir(parents=True)
    corrupt.store_path.write_bytes(b"not sqlite")
    incompatible.store_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(incompatible.store_path)
    connection.execute("CREATE TABLE unrelated(value TEXT)")
    connection.commit()
    connection.close()

    assert ProjectInspector(missing).inspect_run("run-" + "a" * 32).category is InspectionCategory.NOT_FOUND
    assert ProjectInspector(corrupt).inspect_run("run-" + "a" * 32).category is InspectionCategory.STORAGE_CORRUPT
    assert (
        ProjectInspector(incompatible).inspect_run("run-" + "a" * 32).category
        is InspectionCategory.SCHEMA_INCOMPATIBLE
    )
