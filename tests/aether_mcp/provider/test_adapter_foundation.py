from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aether_mcp.adapter import (
    AdapterError,
    AdapterPolicy,
    AdapterRuntime,
    CoordinatorBinding,
    OperationRef,
    OrcaCommandPlanner,
    ProviderBuildBinding,
    ProviderReceipt,
    ReconciliationObservation,
)
from aether_mcp.journal import JournalError, OperationJournal
from aether_mcp.protocol import CALLABLE_TOOL_NAMES, TOOL_SCHEMAS

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
FOREIGN_PROJECT_ID = "22222222-2222-4222-8222-222222222222"
PRINCIPAL_ID = "33333333-3333-4333-8333-333333333333"
OPERATION_ID = "44444444-4444-4444-8444-444444444444"


def _error_code(exc: pytest.ExceptionInfo[BaseException]) -> str | None:
    return getattr(exc.value, "code", None)


def _build(*, manifest: str = "a" * 64) -> ProviderBuildBinding:
    return ProviderBuildBinding(
        candidate_id="orca-linux-appimage-1.4.167",
        product_version="1.4.167",
        manifest_sha256=manifest,
        catalog_sha256="b" * 64,
        launcher_sha256="c" * 64,
        appimage_sha256="d" * 64,
    )


def _operation(*, operation_id: str = OPERATION_ID) -> OperationRef:
    return OperationRef(
        operation_id=operation_id,
        project_id=PROJECT_ID,
        contract_id="contract:r4/1",
        principal_id=PRINCIPAL_ID,
    )


def _coordinator(build: ProviderBuildBinding, *, project_id: str = PROJECT_ID) -> CoordinatorBinding:
    return CoordinatorBinding(
        principal_id=PRINCIPAL_ID,
        project_id=project_id,
        terminal_handle="term-coordinator-1",
        provider_build_digest=build.digest,
        admission_generation=1,
    )


def _planner(*, restricted: bool = False) -> tuple[OrcaCommandPlanner, ProviderBuildBinding]:
    build = _build()
    policy = (
        AdapterPolicy.r3_restricted(build)
        if restricted
        else AdapterPolicy(
            provider_build_digest=build.digest,
            coordinator_binding_qualified=True,
            qualified_mutations=frozenset({"run_create"}),
        )
    )
    return OrcaCommandPlanner(build=build, policy=policy), build


def _planned_run(*, operation_id: str = OPERATION_ID, objective: str = "bounded synthetic run"):
    planner, build = _planner()
    return planner.plan_run_create(
        operation=_operation(operation_id=operation_id),
        coordinator=_coordinator(build),
        objective=objective,
    )


def _success_receipt(call) -> ProviderReceipt:
    return ProviderReceipt(
        outcome="SUCCEEDED",
        project_id=PROJECT_ID,
        provider_request_id="request-1",
        resource_ids=("run-1",),
        response_digest="e" * 64,
    )


def test_r3_policy_allows_exact_status_but_rejects_every_mutation() -> None:
    planner, build = _planner(restricted=True)
    status = planner.plan_status()
    assert status.argv == ("status", "--json")
    assert status.effect == "READ_ONLY"
    assert status.provider_build_digest == build.digest

    with pytest.raises(AdapterError) as exc:
        planner.plan_run_create(
            operation=_operation(),
            coordinator=_coordinator(build),
            objective="must remain unavailable",
        )
    assert _error_code(exc) == "ERR_COORDINATOR_BINDING_UNQUALIFIED"


def test_m2_desktop_qualified_policy_admits_only_run_create() -> None:
    build = _build()
    policy = AdapterPolicy.m2_desktop_qualified(build)
    assert policy.coordinator_binding_qualified is True
    assert policy.qualified_mutations == frozenset({"run_create"})


def test_mutation_requires_exact_build_principal_project_and_generation() -> None:
    planner, build = _planner()
    foreign_build = _build(manifest="f" * 64)
    cases = [
        _coordinator(foreign_build),
        CoordinatorBinding(
            principal_id=PRINCIPAL_ID,
            project_id=FOREIGN_PROJECT_ID,
            terminal_handle="term-coordinator-1",
            provider_build_digest=build.digest,
            admission_generation=1,
        ),
        CoordinatorBinding(
            principal_id="55555555-5555-4555-8555-555555555555",
            project_id=PROJECT_ID,
            terminal_handle="term-coordinator-1",
            provider_build_digest=build.digest,
            admission_generation=1,
        ),
        CoordinatorBinding(
            principal_id=PRINCIPAL_ID,
            project_id=PROJECT_ID,
            terminal_handle="term-coordinator-1",
            provider_build_digest=build.digest,
            admission_generation=0,
        ),
    ]
    expected = [
        "ERR_PROVIDER_BUILD_MISMATCH",
        "ERR_COORDINATOR_SCOPE_MISMATCH",
        "ERR_COORDINATOR_PRINCIPAL_MISMATCH",
        "ERR_COORDINATOR_BINDING_STALE",
    ]
    for binding, code in zip(cases, expected, strict=True):
        with pytest.raises(AdapterError) as exc:
            planner.plan_run_create(
                operation=_operation(),
                coordinator=binding,
                objective="bounded",
            )
        assert _error_code(exc) == code


def test_mutation_requires_a_structured_coordinator_binding() -> None:
    planner, _build_binding = _planner()
    with pytest.raises(AdapterError) as exc:
        planner.plan_run_create(
            operation=_operation(),
            coordinator=None,  # type: ignore[arg-type]
            objective="bounded",
        )
    assert _error_code(exc) == "ERR_COORDINATOR_BINDING_REQUIRED"


def test_structured_argv_is_exact_and_rejects_control_characters() -> None:
    call = _planned_run(objective="one bounded objective")
    assert call.argv == (
        "orchestration",
        "run-create",
        "--objective",
        "one bounded objective",
        "--from",
        "term-coordinator-1",
        "--json",
    )
    assert call.capability == "run_create"
    assert call.effect == "LOCAL_REVERSIBLE"

    planner, build = _planner()
    for invalid in ("line one\n--from forged", "nul\x00payload", ""):
        with pytest.raises(AdapterError) as exc:
            planner.plan_run_create(
                operation=_operation(),
                coordinator=_coordinator(build),
                objective=invalid,
            )
        assert _error_code(exc) == "ERR_INVALID_ARGUMENT"


def test_append_before_effect_and_success_receipt_are_hash_chained(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()
    events: list[str] = []

    def execute(planned) -> ProviderReceipt:
        records = journal.records()
        assert records[-1]["phase"] == "INTENT"
        assert records[-1]["outcome"] == "PREPARED"
        events.append("effect")
        return _success_receipt(planned)

    result = runtime.execute(call, execute)
    assert result.outcome == "SUCCEEDED"
    assert result.replayed is False
    assert events == ["effect"]
    records = journal.records()
    assert [record["phase"] for record in records] == ["INTENT", "RECEIPT"]
    assert records[1]["previous_hash"] == records[0]["record_hash"]
    raw = journal.path.read_text(encoding="utf-8")
    assert "term-coordinator-1" not in raw
    assert "bounded synthetic run" not in raw


def test_atomic_intent_preparation_fences_duplicate_before_effect(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    call = _planned_run()
    operation = call.operation
    assert operation is not None
    first_new, first = journal.prepare_intent(
        operation_id=operation.operation_id,
        project_id=operation.project_id,
        capability=call.capability,
        request_digest=call.request_digest,
    )
    second_new, second = journal.prepare_intent(
        operation_id=operation.operation_id,
        project_id=operation.project_id,
        capability=call.capability,
        request_digest=call.request_digest,
    )
    assert first_new is True
    assert second_new is False
    assert first["record_hash"] == second["record_hash"]
    assert len(journal.records()) == 1


def test_success_replay_does_not_execute_provider_twice(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()
    calls = 0

    def execute(planned) -> ProviderReceipt:
        nonlocal calls
        calls += 1
        return _success_receipt(planned)

    first = runtime.execute(call, execute)
    second = runtime.execute(call, execute)
    assert first.outcome == second.outcome == "SUCCEEDED"
    assert first.replayed is False
    assert second.replayed is True
    assert calls == 1
    assert len(journal.records()) == 2


def test_timeout_becomes_unknown_and_same_operation_is_never_reexecuted(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()
    calls = 0

    def timeout(_planned) -> ProviderReceipt:
        nonlocal calls
        calls += 1
        raise TimeoutError("synthetic timeout")

    first = runtime.execute(call, timeout)
    second = runtime.execute(call, timeout)
    assert first.outcome == second.outcome == "UNKNOWN"
    assert first.replayed is False
    assert second.replayed is True
    assert calls == 1
    records = journal.records()
    assert [record["outcome"] for record in records] == ["PREPARED", "UNKNOWN"]
    assert records[-1]["error_code"] == "ERR_PROVIDER_EFFECT_UNKNOWN"


def test_same_operation_with_changed_payload_is_conflict(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    first = _planned_run(objective="first objective")
    changed = _planned_run(objective="changed objective")
    runtime.execute(first, _success_receipt)

    with pytest.raises(AdapterError) as exc:
        runtime.execute(changed, _success_receipt)
    assert _error_code(exc) == "ERR_OPERATION_CONFLICT"
    assert len(journal.records()) == 2


def test_unknown_reconciles_to_applied_without_reexecuting_effect(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()
    runtime.execute(call, lambda _planned: (_ for _ in ()).throw(TimeoutError()))
    probes = 0

    def probe(correlation: dict[str, Any]) -> ReconciliationObservation:
        nonlocal probes
        probes += 1
        assert correlation["operation_id"] == OPERATION_ID
        assert correlation["request_digest"] == call.request_digest
        return ReconciliationObservation(
            outcome="APPLIED",
            project_id=PROJECT_ID,
            provider_request_id="request-1",
            resource_ids=("run-1",),
            response_digest="e" * 64,
        )

    first = runtime.reconcile(OPERATION_ID, probe)
    second = runtime.reconcile(OPERATION_ID, probe)
    assert first.outcome == second.outcome == "SUCCEEDED"
    assert first.replayed is False
    assert second.replayed is True
    assert probes == 1
    assert journal.records()[-1]["phase"] == "RECONCILE"


def test_foreign_provider_receipt_fails_closed_and_preserves_unknown(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()

    def foreign(_planned) -> ProviderReceipt:
        return ProviderReceipt(
            outcome="SUCCEEDED",
            project_id=FOREIGN_PROJECT_ID,
            provider_request_id="request-foreign",
            resource_ids=("run-foreign",),
            response_digest="f" * 64,
        )

    with pytest.raises(AdapterError) as exc:
        runtime.execute(call, foreign)
    assert _error_code(exc) == "ERR_PROVIDER_RECEIPT_SCOPE"
    assert journal.records()[-1]["outcome"] == "UNKNOWN"


def test_malformed_provider_receipt_fails_closed_and_preserves_unknown(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()

    with pytest.raises(AdapterError) as exc:
        runtime.execute(call, lambda _planned: {"ok": True})  # type: ignore[arg-type,return-value]
    assert _error_code(exc) == "ERR_PROVIDER_RECEIPT_SHAPE"
    assert journal.records()[-1]["outcome"] == "UNKNOWN"


def test_reconciliation_not_applied_is_terminal_for_same_operation(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    call = _planned_run()
    runtime.execute(call, lambda _planned: (_ for _ in ()).throw(TimeoutError()))
    probes = 0

    def probe(_correlation: dict[str, Any]) -> ReconciliationObservation:
        nonlocal probes
        probes += 1
        return ReconciliationObservation(
            outcome="NOT_APPLIED",
            project_id=PROJECT_ID,
            provider_request_id=None,
            resource_ids=(),
            response_digest="e" * 64,
        )

    assert runtime.reconcile(OPERATION_ID, probe).outcome == "NOT_APPLIED"
    assert runtime.reconcile(OPERATION_ID, probe).replayed is True
    assert probes == 1


def test_hash_chain_tampering_is_detected(tmp_path: Path) -> None:
    journal = OperationJournal(tmp_path / "journal")
    runtime = AdapterRuntime(journal)
    runtime.execute(_planned_run(), _success_receipt)
    raw = journal.path.read_text(encoding="utf-8")
    journal.path.write_text(raw.replace('"outcome":"PREPARED"', '"outcome":"SUCCEEDED"', 1), encoding="utf-8")

    with pytest.raises(JournalError) as exc:
        journal.records()
    assert _error_code(exc) == "ERR_JOURNAL_TAMPERED"


def test_journal_rejects_symlink_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    journal_link = tmp_path / "journal-link"
    journal_link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(JournalError) as exc:
        OperationJournal(journal_link)
    assert _error_code(exc) == "ERR_JOURNAL_SCOPE"


def test_adapter_foundation_exposes_only_the_approved_mcp_tools() -> None:
    assert CALLABLE_TOOL_NAMES == frozenset(TOOL_SCHEMAS)
