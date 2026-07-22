import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from olympus_v3.coordination import (
    AdmissionDecision,
    AdmissionProposal,
    AdmissionStatus,
    AnycastAssignment,
    HarmoniaPlan,
    HarmoniaProjection,
    HarmoniaTask,
    Principal,
    ShadowConfig,
    ShadowSessionCorrelation,
    TaskState,
    compare_shadow,
    observe_olympus_session,
)
from olympus_v3.coordination.shadow_store import DurableShadowCorrelationRegistry

ROOT = "/tmp/project-a"
WORKER = Principal("project-a", "owner-a", "hefesto")


class DB:
    async def get_session(self, session_id):
        return {
            "session_id": session_id,
            "agent": "hefesto",
            "status": "completed",
            "metadata": '{"profile":"hefesto","project_root":"/tmp/project-a"}',
        }

    async def get_latest_turn(self, session_id):
        return {"content": "AETHER_SHADOW_V1 task_id=task-a participant=hefesto technical_status=completed"}


def correlation(**changes):
    proposal = AdmissionProposal(
        "task-a", "objective", "user", ("src",), (), "hefesto", "implement", ("gate",), 1, 1, 30, 1, "e1", 1, 100, ()
    )
    plan = HarmoniaPlan(
        (AdmissionDecision("task-a", AdmissionStatus.ADMITTED, (), proposal),),
        (AnycastAssignment("task-a", WORKER),),
        (),
        HarmoniaProjection(1, (HarmoniaTask(proposal, TaskState.READY, WORKER, 0, ()),)),
    )
    evidence = asyncio.run(
        observe_olympus_session(
            DB(),
            session_id="actual-a",
            task_id="task-a",
            participant=WORKER,
            project_root=ROOT,
            project_id="project-a",
            contract_id="contract-a",
            generation=3,
        )
    )
    return (
        ShadowSessionCorrelation.from_evidence(plan, evidence)
        if not changes
        else replace(ShadowSessionCorrelation.from_evidence(plan, evidence), **changes)
    )


def test_persists_and_replays_after_close(tmp_path):
    path = tmp_path / "shadow.db"
    item = correlation()
    first = DurableShadowCorrelationRegistry(path)
    assert first.consume(item) is True
    first.close()
    second = DurableShadowCorrelationRegistry(path)
    assert second.consume(item) is True
    second.close()


def test_complete_binding_and_both_identity_reuse_fail_closed(tmp_path):
    r = DurableShadowCorrelationRegistry(tmp_path / "x.db")
    item = correlation()
    assert r.consume(item)
    assert not r.consume(correlation(actual_session_id="actual-b"))
    assert not r.consume(correlation(predicted_session_id="predicted-b"))
    assert not r.consume(correlation(evidence_signature="different"))


def test_root_alias_is_equivalent(tmp_path):
    r = DurableShadowCorrelationRegistry(tmp_path / "x.db")
    item = correlation()
    assert r.consume(item)
    assert r.consume(correlation(project_root="/tmp/project-a/./"))


def test_context_binding_rejects_project_contract_generation(tmp_path):
    r = DurableShadowCorrelationRegistry(tmp_path / "x.db")
    item = correlation()
    assert r.consume(item)
    with pytest.raises(Exception, match="cross-project"):
        r.consume(correlation(project_id="other"))
    for field, value in (("contract_id", "other"), ("generation", 4), ("task_id", "other")):
        assert not r.consume(correlation(**{field: value}))


def test_capacity_counts_unique_bindings(tmp_path):
    r = DurableShadowCorrelationRegistry(tmp_path / "x.db", max_entries=1)
    item = correlation()
    assert r.consume(item)
    assert r.consume(item)
    assert not r.consume(correlation(actual_session_id="actual-b", predicted_session_id="predicted-b"))


def test_corrupt_record_is_rejected(tmp_path):
    path = tmp_path / "x.db"
    r = DurableShadowCorrelationRegistry(path)
    assert r.consume(correlation())
    r.close()
    con = sqlite3.connect(path)
    con.execute("UPDATE shadow_correlations SET evidence_signature='not-a-valid-signature'")
    con.commit()
    con.close()
    r = DurableShadowCorrelationRegistry(path)
    with pytest.raises(Exception, match="corrupt"):
        r.consume(correlation())


def test_contention_allows_one_binding_and_rejects_conflict(tmp_path):
    path = tmp_path / "x.db"
    items = [correlation(actual_session_id=f"actual-{i}", predicted_session_id=f"predicted-{i}") for i in range(8)]

    def consume(item):
        r = DurableShadowCorrelationRegistry(path, busy_timeout_ms=1000)
        try:
            return r.consume(item)
        finally:
            r.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(consume, items))
    assert all(results)
    r = DurableShadowCorrelationRegistry(path)
    assert not r.consume(correlation(actual_session_id="actual-0", predicted_session_id="other"))
    r.close()


def test_compare_shadow_uses_durable_registry_across_recreation(tmp_path):
    path = tmp_path / "x.db"
    item = asyncio.run(
        observe_olympus_session(
            DB(),
            session_id="actual-a",
            task_id="task-a",
            participant=WORKER,
            project_root=ROOT,
            project_id="project-a",
            contract_id="contract-a",
            generation=3,
        )
    )
    assignment_plan = correlation_plan()
    correlation_item = ShadowSessionCorrelation.from_evidence(assignment_plan, item)
    first = DurableShadowCorrelationRegistry(path)
    first_report = compare_shadow(
        assignment_plan,
        item,
        project_root=ROOT,
        config=ShadowConfig(True),
        project_id="project-a",
        contract_id="contract-a",
        generation=3,
        expected_status="completed",
        correlation=correlation_item,
        registry=first,
    )
    first.close()
    second = DurableShadowCorrelationRegistry(path)
    second_report = compare_shadow(
        assignment_plan,
        item,
        project_root=ROOT,
        config=ShadowConfig(True),
        project_id="project-a",
        contract_id="contract-a",
        generation=3,
        expected_status="completed",
        correlation=correlation_item,
        registry=second,
    )
    second.close()

    assert first_report.session_agreement is True
    assert second_report.session_agreement is True


def correlation_plan():
    proposal = AdmissionProposal(
        "task-a", "objective", "user", ("src",), (), "hefesto", "implement", ("gate",), 1, 1, 30, 1, "e1", 1, 100, ()
    )
    return HarmoniaPlan(
        (AdmissionDecision("task-a", AdmissionStatus.ADMITTED, (), proposal),),
        (AnycastAssignment("task-a", WORKER),),
        (),
        HarmoniaProjection(1, (HarmoniaTask(proposal, TaskState.READY, WORKER, 0, ()),)),
    )


def test_invalid_project_binding_is_rejected_before_persistence(tmp_path):
    registry = DurableShadowCorrelationRegistry(tmp_path / "x.db")
    with pytest.raises(Exception, match="cross-project"):
        registry.consume(correlation(project_id="other-project"))
    registry.close()


def test_schema_version_mismatch_and_non_database_file_fail_closed(tmp_path):
    path = tmp_path / "version.db"
    registry = DurableShadowCorrelationRegistry(path)
    registry.close()
    con = sqlite3.connect(path)
    con.execute("UPDATE shadow_store_meta SET value='999' WHERE key='schema_version'")
    con.commit()
    con.close()
    with pytest.raises(Exception, match="schema version"):
        DurableShadowCorrelationRegistry(path)

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not sqlite")
    with pytest.raises(Exception, match="corrupt shadow store"):
        DurableShadowCorrelationRegistry(corrupt)


def test_locked_store_fails_closed_without_partial_insert(tmp_path):
    path = tmp_path / "locked.db"
    registry = DurableShadowCorrelationRegistry(path, busy_timeout_ms=0)
    blocker = sqlite3.connect(path, isolation_level=None)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        assert registry.consume(correlation()) is False
    finally:
        blocker.rollback()
        blocker.close()
    assert registry.consume(correlation()) is True
    registry.close()
