import asyncio
from dataclasses import FrozenInstanceError, replace

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
    ShadowObservation,
    ShadowSessionCorrelation,
    TaskState,
    compare_shadow,
    observe_olympus_session,
    verify_shadow_report,
)

PROJECT = "project-a"
ROOT = "/tmp/project-a"
CONTRACT = "contract-a"
GENERATION = 3
WORKER = Principal(PROJECT, "instance-a", "hefesto")


def make_plan(task_id="task-a", worker=WORKER):
    item = AdmissionProposal(
        task_id,
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
    decision = AdmissionDecision(task_id, AdmissionStatus.ADMITTED, (), item)
    return HarmoniaPlan(
        (decision,),
        (AnycastAssignment(task_id, worker),),
        (),
        HarmoniaProjection(1, (HarmoniaTask(item, TaskState.READY, worker, 0, ()),)),
    )


class FakeDB:
    def __init__(self, *, session_id="actual-session", status="completed", agent="hefesto", root=ROOT, response=None):
        self.reads = 0
        self.row = {
            "session_id": session_id,
            "agent": agent,
            "status": status,
            "metadata": f'{{"profile":"{agent}","project_root":"{root}"}}',
        }
        self.turn = {
            "content": response or f"AETHER_SHADOW_V1 task_id=task-a participant={agent} technical_status={status}"
        }

    async def get_session(self, session_id):
        self.reads += 1
        return self.row

    async def get_latest_turn(self, session_id):
        self.reads += 1
        return self.turn


async def evidence(db=None, **kwargs):
    values = dict(
        session_id="actual-session",
        task_id="task-a",
        participant=WORKER,
        project_root=ROOT,
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
    )
    values.update(kwargs)
    return await observe_olympus_session(db or FakeDB(), **values)


def compare(plan, item, *, correlation=None, registry=None, expected_status="completed", **kwargs):
    return compare_shadow(
        plan,
        item,
        project_root=ROOT,
        config=ShadowConfig(True),
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
        expected_status=expected_status,
        correlation=correlation,
        registry=registry,
        **kwargs,
    )


def test_default_off_does_not_read_db_or_derive_session(monkeypatch):
    db = FakeDB()

    def forbidden(*args, **kwargs):
        raise AssertionError("disabled shadow must not touch runtime")

    monkeypatch.setattr(
        "olympus_v3.coordination.olympus_adapter.OlympusRuntimeAdapter._session_id",
        forbidden,
    )
    report = compare_shadow(make_plan(), ShadowObservation("task-a", WORKER, "x", "completed"), project_root=ROOT)
    assert report.mismatches == ("feature_disabled",)
    assert report.semantic_complete is False
    assert db.reads == 0
    assert verify_shadow_report(report)


def test_verified_olympus_evidence_correlates_actual_and_predicted_sessions():
    item = asyncio.run(evidence())
    plan = make_plan()
    correlation = ShadowSessionCorrelation.from_evidence(plan, item)
    report = compare(plan, item, correlation=correlation, registry=ShadowCorrelationRegistry())
    assert (
        report.assignment_agreement,
        report.participant_agreement,
        report.session_agreement,
        report.status_agreement,
    ) == (True, True, True, True)
    assert report.mismatches == ()
    assert report.correlation.actual_session_id == "actual-session"
    assert report.correlation.predicted_session_id != "actual-session"
    assert verify_shadow_report(report)
    assert report.semantic_complete is False


def test_untrusted_observation_cannot_become_agreement_evidence():
    observation = ShadowObservation("task-a", WORKER, "borrowed", "completed", PROJECT, CONTRACT, GENERATION)
    report = compare(make_plan(), observation)
    assert report.session_agreement is False
    assert report.mismatches == ("unverified_evidence",)


def test_forged_evidence_and_report_signatures_fail_closed():
    item = asyncio.run(evidence())
    forged = replace(item, actual_session_id="borrowed")
    report = compare(make_plan(), forged)
    assert report.mismatches == ("unverified_evidence",)
    valid_correlation = ShadowSessionCorrelation.from_evidence(make_plan(), item)
    valid = compare(make_plan(), item, correlation=valid_correlation, registry=ShadowCorrelationRegistry())
    assert not verify_shadow_report(replace(valid, session_agreement=False))
    with pytest.raises(FrozenInstanceError):
        valid.semantic_complete = True


@pytest.mark.parametrize("status", ["sent", "running", "review", "closed"])
def test_status_is_compared_to_explicit_expected_status(status):
    db = FakeDB(status=status)
    item = asyncio.run(evidence(db, session_id="actual-session"))
    correlation = ShadowSessionCorrelation.from_evidence(make_plan(), item)
    report = compare(make_plan(), item, correlation=correlation, registry=ShadowCorrelationRegistry())
    assert report.status_agreement is False
    assert "status_mismatch" in report.mismatches


@pytest.mark.parametrize(
    "changes",
    [
        {"project_id": "other-project"},
        {"contract_id": "other-contract"},
        {"generation": GENERATION - 1},
        {"project_root": "/tmp/project-a/../other"},
    ],
)
def test_context_mismatch_is_fail_closed(changes):
    item = asyncio.run(evidence())
    correlation = ShadowSessionCorrelation.from_evidence(make_plan(), item)
    values = dict(
        project_root=ROOT,
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
    )
    values.update(changes)
    report = compare_shadow(
        make_plan(),
        item,
        config=ShadowConfig(True),
        expected_status="completed",
        correlation=correlation,
        registry=ShadowCorrelationRegistry(),
        **values,
    )
    assert report.session_agreement is False
    assert "context_mismatch" in report.mismatches


def test_root_alias_is_canonicalized_consistently():
    item = asyncio.run(evidence(project_root="/tmp/project-a/../project-a"))
    correlation = ShadowSessionCorrelation.from_evidence(make_plan(), item)
    report = compare(make_plan(), item, correlation=correlation, registry=ShadowCorrelationRegistry())
    assert report.session_agreement is True


def test_duplicate_actual_session_cannot_bind_to_another_task():
    registry = ShadowCorrelationRegistry()
    first = asyncio.run(evidence())
    first_corr = ShadowSessionCorrelation.from_evidence(make_plan(), first)
    assert compare(make_plan(), first, correlation=first_corr, registry=registry).session_agreement
    second_db = FakeDB(response="AETHER_SHADOW_V1 task_id=task-b participant=hefesto technical_status=completed")
    second = asyncio.run(evidence(second_db, task_id="task-b"))
    second_plan = make_plan("task-b")
    second_corr = ShadowSessionCorrelation.from_evidence(second_plan, second)
    report = compare(second_plan, second, correlation=second_corr, registry=registry)
    assert report.session_agreement is False
    assert "correlation_mismatch" in report.mismatches


@pytest.mark.parametrize(
    "condition",
    [
        ShadowCondition.DUPLICATE_DELIVERY,
        ShadowCondition.RUNTIME_UNAVAILABLE,
        ShadowCondition.REVIEWER_VIOLATION,
        ShadowCondition.BUDGET_EXHAUSTED,
    ],
)
def test_failure_matrix_is_observational_and_fail_closed(condition):
    item = asyncio.run(evidence(conditions=(condition,)))
    correlation = ShadowSessionCorrelation.from_evidence(make_plan(), item)
    report = compare(make_plan(), item, correlation=correlation, registry=ShadowCorrelationRegistry())
    assert report.status_agreement is False
    assert condition.value in report.mismatches
    assert report.semantic_complete is False


@pytest.mark.parametrize("latency", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_latency_is_rejected(latency):
    with pytest.raises(Exception, match="invalid shadow latency"):
        asyncio.run(evidence(latency_ms=latency))


def test_olympus_evidence_rejects_wrong_agent_root_or_response_binding():
    for db in (
        FakeDB(agent="etalides"),
        FakeDB(root="/tmp/other"),
        FakeDB(response="unbound response"),
    ):
        with pytest.raises(Exception, match="unbound Olympus session evidence"):
            asyncio.run(evidence(db))


@pytest.mark.parametrize(
    "response",
    [
        "SHADOW_OK task_id=task-ab participant=hefesto technical_status=completed",
        "SHADOW_OK task_id=task-a participant=hefestoX technical_status=completed",
        "prefix SHADOW_OK task_id=task-a participant=hefesto technical_status=completed",
        "SHADOW_OK task_id=task-a task_id=task-a participant=hefesto technical_status=completed",
        "SHADOW_OK participant=hefesto task_id=task-a technical_status=completed",
        "SHADOW_OK task_id=task-a participant=hefesto technical_status=completed suffix",
    ],
)
def test_olympus_evidence_requires_one_exact_versioned_response_envelope(response):
    with pytest.raises(Exception, match="unbound Olympus session evidence"):
        asyncio.run(evidence(FakeDB(response=response)))


def test_same_binding_duplicate_is_idempotent_but_registry_is_bounded():
    item = asyncio.run(evidence())
    correlation = ShadowSessionCorrelation.from_evidence(make_plan(), item)
    registry = ShadowCorrelationRegistry(max_entries=1)
    assert registry.consume(correlation)
    assert registry.consume(correlation)
    second = replace(correlation, actual_session_id="another-session")
    assert registry.consume(second) is False


def test_enabled_comparison_requires_complete_expected_context():
    report = compare_shadow(
        make_plan(),
        ShadowObservation("task-a", WORKER, "x", "completed"),
        project_root=ROOT,
        config=ShadowConfig(True),
    )
    assert report.mismatches == ("unverified_evidence",)
    assert report.session_agreement is False
