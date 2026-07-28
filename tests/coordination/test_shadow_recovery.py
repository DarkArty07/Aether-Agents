"""R7 advanced fail-closed recovery matrix; no test executes runtime effects."""

import asyncio

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
    ShadowCondition,
    ShadowConfig,
    ShadowCorrelationRegistry,
    ShadowSessionCorrelation,
    TaskState,
    compare_shadow,
    observe_olympus_session,
)
from olympus_v3.coordination.leases import LeaseManager, LeaseResult
from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)

PROJECT = "project-a"
ROOT = "/tmp/project-a"
CONTRACT = "contract-a"
GENERATION = 3
WORKER = Principal(PROJECT, "instance-a", "hefesto")


class FakeDB:
    def __init__(self, *, status="completed", response=True):
        self.row = {
            "session_id": "actual-session",
            "agent": "hefesto",
            "status": status,
            "metadata": '{"profile":"hefesto","project_root":"/tmp/project-a"}',
        }
        self.turn = (
            {"content": f"AETHER_SHADOW_V1 task_id=task-a participant=hefesto technical_status={status}"}
            if response
            else None
        )

    async def get_session(self, _session_id):
        return self.row

    async def get_latest_turn(self, _session_id):
        return self.turn


def plan():
    proposal = AdmissionProposal(
        "task-a",
        "objective",
        "user",
        ("src",),
        (),
        "hefesto",
        "implement",
        ("gate",),
        1,
        1,
        30,
        1,
        "e1",
        1,
        100,
        (),
    )
    decision = AdmissionDecision("task-a", AdmissionStatus.ADMITTED, (), proposal)
    return HarmoniaPlan(
        (decision,),
        (AnycastAssignment("task-a", WORKER),),
        (),
        HarmoniaProjection(1, (HarmoniaTask(proposal, TaskState.READY, WORKER, 0, ()),)),
    )


async def evidence(*conditions):
    return await observe_olympus_session(
        FakeDB(),
        session_id="actual-session",
        task_id="task-a",
        participant=WORKER,
        project_root=ROOT,
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
        conditions=conditions,
    )


def report_for(*conditions):
    item = asyncio.run(evidence(*conditions))
    correlation = ShadowSessionCorrelation.from_evidence(plan(), item)
    return compare_shadow(
        plan(),
        item,
        project_root=ROOT,
        config=ShadowConfig(True),
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
        expected_status="completed",
        correlation=correlation,
        registry=ShadowCorrelationRegistry(),
    )


@pytest.mark.parametrize(
    "condition",
    [
        ShadowCondition.STALE_LEASE,
        ShadowCondition.REVOCATION_RACE,
        ShadowCondition.LEDGER_TAMPERED,
        ShadowCondition.PROJECTION_REBUILT,
        ShadowCondition.UNKNOWN_EFFECT,
        ShadowCondition.PARTIAL_EVIDENCE,
    ],
)
def test_advanced_recovery_conditions_are_typed_and_fail_closed(condition):
    report = report_for(condition)

    assert report.status_agreement is False
    assert condition.value in report.mismatches
    assert report.semantic_complete is False


def test_stale_lease_after_takeover_is_observed_without_runtime_action(tmp_path):
    now = [100]
    scope = StoreScope("install-a", PROJECT)
    manager = LeaseManager(str(tmp_path / "lease.sqlite"), scope, clock=lambda: now[0])
    first = manager.acquire(scope, "harmonia", "owner-a", ttl=10).lease
    assert first is not None
    now[0] = 111
    takeover = manager.acquire(scope, "harmonia", "owner-b", ttl=10)

    assert takeover.status is LeaseResult.ACQUIRED
    assert manager.check(first).status is LeaseResult.STALE_FENCE
    report = report_for(ShadowCondition.STALE_LEASE)
    assert report.mismatches[-1] == "stale_lease"
    manager.close()


def test_tampered_ledger_rejects_then_projection_rebuild_is_observational(tmp_path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"})
    signer = HMACIntegritySigner(b"integrity-key")
    ledger = SQLiteLedger(tmp_path / "ledger.sqlite", scope, writer_authenticator=auth, integrity_signer=signer)
    lease = ledger.acquire_lease("ledger", "writer-a", ttl=10_000_000_000).lease
    assert lease is not None
    writer = WriterContext(scope, "writer-a", "key-a", "ledger", lease.epoch, lease.expires_at)
    draft = ledger.draft("aggregate-a", "state.set", {"value": 1}, writer=writer, expected_version=0)
    assert ledger.append(auth.sign(draft, writer), writer).status is Result.APPLIED
    expected = ledger.projection("aggregate-a")
    ledger.conn.execute("DELETE FROM projections")
    ledger.rebuild_projections()

    assert ledger.projection("aggregate-a") == expected
    assert report_for(ShadowCondition.PROJECTION_REBUILT).semantic_complete is False
    ledger.conn.execute("DROP TRIGGER immutable_events_update")
    ledger.conn.execute("UPDATE events SET payload='{}'")
    with pytest.raises(ValueError, match=Result.INTEGRITY_FAILURE.value):
        ledger.verify_chain()
    assert "ledger_tampered" in report_for(ShadowCondition.LEDGER_TAMPERED).mismatches
    ledger.close()


def test_missing_olympus_turn_fails_before_any_agreement():
    with pytest.raises(Exception, match="missing Olympus session evidence"):
        asyncio.run(
            observe_olympus_session(
                FakeDB(response=False),
                session_id="actual-session",
                task_id="task-a",
                participant=WORKER,
                project_root=ROOT,
                project_id=PROJECT,
                contract_id=CONTRACT,
                generation=GENERATION,
            )
        )


def test_multiple_recovery_conditions_remain_bounded_and_nonsemantic():
    conditions = (
        ShadowCondition.RUNTIME_UNAVAILABLE,
        ShadowCondition.REVOCATION_RACE,
        ShadowCondition.UNKNOWN_EFFECT,
    )
    report = report_for(*conditions)

    assert set(item.value for item in conditions) <= set(report.mismatches)
    assert report.semantic_complete is False
