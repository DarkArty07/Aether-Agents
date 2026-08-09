"""M2.4 transactional trace-store and receipt tests."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import uuid
from pathlib import Path

import pytest

from aether_mcp.adapter import AdapterRuntime, OperationRef, PlannedCall, ProviderReceipt
from aether_mcp.trace_store import StoreError, TraceStore


def _ids() -> tuple[str, str, str]:
    return str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())


def _call(operation_id: str, project_id: str, principal_id: str, digest: str) -> PlannedCall:
    return PlannedCall(
        operation=OperationRef(operation_id, project_id, "contract:test", principal_id),
        capability="run_create",
        effect="LOCAL_REVERSIBLE",
        argv=("orchestration", "run-create", "--json"),
        provider_build_digest="b" * 64,
        request_digest=digest,
    )


def test_schema_migrates_atomically_and_rejects_future_version(tmp_path: Path) -> None:
    store = TraceStore(tmp_path / "trace")
    assert store.schema_version == 2
    assert store.verify_integrity()["events"] == 0

    with sqlite3.connect(store.path) as connection:
        connection.execute("PRAGMA user_version = 99")
    with pytest.raises(StoreError) as captured:
        TraceStore(tmp_path / "trace")
    assert captured.value.code == "TRACE_INTEGRITY_FAILURE"


def test_version_one_store_migrates_forward_without_losing_operations(tmp_path: Path) -> None:
    root = tmp_path / "trace"
    store = TraceStore(root)
    operation_id, project_id, _ = _ids()
    store.prepare_intent(
        operation_id=operation_id,
        project_id=project_id,
        capability="run_create",
        request_digest="9" * 64,
    )
    with sqlite3.connect(store.path) as connection:
        connection.execute("DROP TABLE semantic_events")
        connection.execute("PRAGMA user_version = 1")

    migrated = TraceStore(root)
    assert migrated.schema_version == 2
    assert len(migrated.records_for(operation_id)) == 1
    assert migrated.verify_semantic_integrity()["events"] == 0


def test_intent_is_durable_before_effect_and_exact_replay_is_idempotent(tmp_path: Path) -> None:
    operation_id, project_id, _ = _ids()
    digest = hashlib.sha256(b"request").hexdigest()
    store = TraceStore(tmp_path / "trace")

    created, first = store.prepare_intent(operation_id=operation_id, project_id=project_id, capability="run_create", request_digest=digest)
    replayed, second = store.prepare_intent(operation_id=operation_id, project_id=project_id, capability="run_create", request_digest=digest)

    assert created is True
    assert replayed is False
    assert first == second
    assert first["phase"] == "INTENT"
    assert first["outcome"] == "PREPARED"
    assert TraceStore(tmp_path / "trace").records_for(operation_id) == [first]


def test_operation_id_reuse_with_different_input_fails_closed(tmp_path: Path) -> None:
    operation_id, project_id, _ = _ids()
    store = TraceStore(tmp_path / "trace")
    store.prepare_intent(operation_id=operation_id, project_id=project_id, capability="run_create", request_digest="a" * 64)

    with pytest.raises(StoreError) as captured:
        store.prepare_intent(operation_id=operation_id, project_id=project_id, capability="run_create", request_digest="c" * 64)
    assert captured.value.code == "IDEMPOTENCY_CONFLICT"


def test_provider_exception_becomes_unknown_and_requires_reconciliation(tmp_path: Path) -> None:
    operation_id, project_id, principal_id = _ids()
    store = TraceStore(tmp_path / "trace")
    runtime = AdapterRuntime(store)  # type: ignore[arg-type]

    def fail(_call: PlannedCall) -> ProviderReceipt:
        raise TimeoutError("delivery ambiguous")

    result = runtime.execute(_call(operation_id, project_id, principal_id, "d" * 64), fail)

    assert result.outcome == "UNKNOWN"
    records = store.records_for(operation_id)
    assert [record["phase"] for record in records] == ["INTENT", "RECEIPT"]
    assert records[-1]["error_code"] == "ERR_PROVIDER_EFFECT_UNKNOWN"
    assert store.verify_integrity()["events"] == 2


def test_store_failure_prevents_provider_effect(tmp_path: Path) -> None:
    operation_id, project_id, principal_id = _ids()
    store = TraceStore(tmp_path / "trace")
    runtime = AdapterRuntime(store)  # type: ignore[arg-type]
    called = False

    with sqlite3.connect(store.path, timeout=0, isolation_level=None) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")

        def provider(_call: PlannedCall) -> ProviderReceipt:
            nonlocal called
            called = True
            return ProviderReceipt("SUCCEEDED", project_id, "request:1", ("run:1",), "e" * 64)

        with pytest.raises(StoreError) as captured:
            runtime.execute(_call(operation_id, project_id, principal_id, "f" * 64), provider)
        assert captured.value.code == "TRACE_STORE_BUSY"
    assert called is False


def test_concurrent_first_intent_has_one_winner_and_one_replay(tmp_path: Path) -> None:
    operation_id, project_id, _ = _ids()
    root = tmp_path / "trace"
    TraceStore(root)
    barrier = threading.Barrier(2)
    outcomes: list[bool] = []
    errors: list[str] = []

    def worker() -> None:
        try:
            store = TraceStore(root)
            barrier.wait(timeout=5)
            created, _ = store.prepare_intent(operation_id=operation_id, project_id=project_id, capability="run_create", request_digest="1" * 64)
            outcomes.append(created)
        except BaseException as exc:  # pragma: no cover - diagnostic capture
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert sorted(outcomes) == [False, True]
    assert len(TraceStore(root).records_for(operation_id)) == 1


def test_hash_chain_detects_database_tampering(tmp_path: Path) -> None:
    operation_id, project_id, _ = _ids()
    store = TraceStore(tmp_path / "trace")
    store.prepare_intent(operation_id=operation_id, project_id=project_id, capability="run_create", request_digest="2" * 64)

    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE events SET outcome = 'SUCCEEDED' WHERE sequence = 1")

    with pytest.raises(StoreError) as captured:
        store.verify_integrity()
    assert captured.value.code == "TRACE_INTEGRITY_FAILURE"


def test_semantic_decisions_and_evidence_are_append_only_and_paginated(tmp_path: Path) -> None:
    operation_id, project_id, _ = _ids()
    run_id = str(uuid.uuid4())
    store = TraceStore(tmp_path / "trace")

    decision = store.append_semantic_event(
        operation_id=operation_id,
        project_id=project_id,
        run_id=run_id,
        kind="DECISION",
        payload={"kind": "route_selected", "decision": "direct", "authority_ref": "decision:test"},
    )
    evidence = store.append_semantic_event(
        operation_id=str(uuid.uuid4()),
        project_id=project_id,
        run_id=run_id,
        kind="EVIDENCE",
        payload={"evidence_type": "test_result", "reference": "artifact:result.json", "authority_ref": "decision:test"},
    )

    first = store.query_semantic(project_id=project_id, run_id=run_id, kinds=(), cursor=None, limit=1)
    second = store.query_semantic(project_id=project_id, run_id=run_id, kinds=(), cursor=first["next_cursor"], limit=1)
    assert first["events"] == [decision]
    assert second["events"] == [evidence]
    assert second["next_cursor"] is None
    assert store.verify_semantic_integrity()["events"] == 2


def test_semantic_trace_rejects_secret_shaped_and_oversized_payloads(tmp_path: Path) -> None:
    store = TraceStore(tmp_path / "trace")
    operation_id, project_id, _ = _ids()
    run_id = str(uuid.uuid4())

    for payload in (
        {"summary": "Authorization: Bearer abc.def.ghi"},
        {"summary": "x" * 70_000},
    ):
        with pytest.raises(StoreError) as captured:
            store.append_semantic_event(
                operation_id=operation_id,
                project_id=project_id,
                run_id=run_id,
                kind="DECISION",
                payload=payload,
            )
        assert captured.value.code == "PRIVACY_POLICY_VIOLATION"
    assert store.verify_semantic_integrity()["events"] == 0


def test_semantic_hash_chain_detects_payload_tampering(tmp_path: Path) -> None:
    store = TraceStore(tmp_path / "trace")
    operation_id, project_id, _ = _ids()
    store.append_semantic_event(
        operation_id=operation_id,
        project_id=project_id,
        run_id=None,
        kind="DECISION",
        payload={"decision": "original"},
    )
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE semantic_events SET payload_json='{}' WHERE sequence=1")
    with pytest.raises(StoreError) as captured:
        store.verify_semantic_integrity()
    assert captured.value.code == "TRACE_INTEGRITY_FAILURE"
