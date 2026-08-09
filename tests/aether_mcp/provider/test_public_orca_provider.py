"""Exact public Orca CLI adapter contracts for M3."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aether_mcp.lifecycle import LifecycleError
from aether_mcp.manifest import validate_swarm_manifest
from aether_mcp.orca_provider import PublicOrcaLifecycleProvider

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "33333333-3333-4333-8333-333333333333"


def _manifest():
    return validate_swarm_manifest(
        {
            "protocol": "aether.mcp/v1alpha2",
            "project_id": PROJECT_ID,
            "contract": {
                "contract_id": "contract:m3/provider",
                "generation": 1,
                "objective": "provider lifecycle",
                "acceptance": ["exact correlation"],
                "non_goals": ["workers"],
                "authorized_effects": ["READ_ONLY", "LOCAL_REVERSIBLE"],
                "stop_condition": "terminal tasks",
            },
            "evaluation": {"enabled": False, "use_case_id": "UC-C02", "variant": "shell", "measurement_contract": None},
            "learning": {"capture_policy": "STRUCTURED_ONLY", "purpose": ["evaluation"], "consent_authority_ref": "decision:m3"},
            "tasks": [
                {
                    "task_key": "first",
                    "deliverable": "first metadata task",
                    "archetype": "fixture",
                    "dependencies": [],
                    "read_scope": ["src"],
                    "write_scope": [],
                    "evidence_requirements": ["identity"],
                    "attempt_budget": 1,
                    "placement": "read_only",
                },
                {
                    "task_key": "second",
                    "deliverable": "second metadata task",
                    "archetype": "fixture",
                    "dependencies": ["first"],
                    "read_scope": ["src"],
                    "write_scope": [],
                    "evidence_requirements": ["identity"],
                    "attempt_budget": 1,
                    "placement": "read_only",
                },
            ],
        }
    )


class Transport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.tasks: list[dict[str, Any]] = []

    def __call__(self, argv: tuple[str, ...]) -> dict[str, Any]:
        self.calls.append(argv)
        if argv[:2] == ("orchestration", "run-create"):
            objective = argv[argv.index("--objective") + 1]
            return {"id": "req-run", "ok": True, "result": {"run": {"id": "run_public_1", "objective": objective}}}
        if argv[:2] == ("orchestration", "task-create"):
            spec = argv[argv.index("--spec") + 1]
            task_id = f"task_public_{len(self.tasks) + 1}"
            task = {"id": task_id, "taskId": task_id, "spec": spec, "status": "pending"}
            self.tasks.append(task)
            return {"id": f"req-task-{len(self.tasks)}", "ok": True, "result": {"task": task}}
        if argv[:2] == ("orchestration", "run-show"):
            return {"id": "req-show", "ok": True, "result": {"run": {"id": "run_public_1", "status": "running"}}}
        if argv[:2] == ("orchestration", "run-list"):
            return {
                "id": "req-list",
                "ok": True,
                "result": {"runs": [{"id": "run_public_1", "objective": f"aether-run:{RUN_ID}:{OPERATION_ID}"}]},
            }
        if argv[:2] == ("orchestration", "task-list"):
            return {"id": "req-tasks", "ok": True, "result": {"tasks": list(self.tasks)}}
        if argv[:2] == ("orchestration", "task-update"):
            task_id = argv[argv.index("--id") + 1]
            for task in self.tasks:
                if task["id"] == task_id:
                    task["status"] = "failed"
            return {"id": "req-update", "ok": True, "result": {"task": {"id": task_id, "status": "failed"}}}
        raise AssertionError(argv)


def test_public_provider_builds_structured_argv_and_correlates_tasks() -> None:
    transport = Transport()
    provider = PublicOrcaLifecycleProvider(
        transport=transport,
        binding_digest="a" * 64,
        coordinator_handle="term-coordinator-1",
    )
    manifest = _manifest()
    result = provider.start_no_dispatch(operation_id=OPERATION_ID, logical_run_id=RUN_ID, manifest=manifest)

    assert result.outcome == "APPLIED"
    assert result.provider_run_id == "run_public_1"
    assert result.provider_tasks == (("first", "task_public_1"), ("second", "task_public_2"))
    assert transport.calls[0] == (
        "orchestration", "run-create", "--objective", f"aether-run:{RUN_ID}:{OPERATION_ID}",
        "--from", "term-coordinator-1", "--json",
    )
    assert json.loads(transport.calls[2][transport.calls[2].index("--deps") + 1]) == ["task_public_1"]


def test_public_provider_reads_status_cancels_and_reconciles_by_exact_marker() -> None:
    transport = Transport()
    provider = PublicOrcaLifecycleProvider(transport=transport, binding_digest="a" * 64, coordinator_handle="term-coordinator-1")
    manifest = _manifest()
    result = provider.start_no_dispatch(operation_id=OPERATION_ID, logical_run_id=RUN_ID, manifest=manifest)

    projection = provider.inspect_run(provider_run_id=result.provider_run_id or "")
    assert projection.source == "orca-public-cli"
    assert [task.task_key for task in projection.tasks] == ["first", "second"]
    reconciled = provider.reconcile_start(operation_id=OPERATION_ID, logical_run_id=RUN_ID)
    assert reconciled is not None
    assert reconciled.outcome == "APPLIED"
    assert reconciled.provider_run_id == result.provider_run_id
    assert reconciled.provider_tasks == result.provider_tasks

    cancelled = provider.cancel(provider_run_id="run_public_1", target_type="run", provider_target_id="run_public_1")
    assert cancelled.outcome == "APPLIED"
    assert len([call for call in transport.calls if call[:2] == ("orchestration", "task-update")]) == 2


def test_public_provider_rejects_unbounded_or_malformed_envelopes() -> None:
    def malformed(_argv: tuple[str, ...]) -> dict[str, Any]:
        return {"ok": True, "result": {"run": {"id": "run_1"}}, "unexpected": "drift"}

    provider = PublicOrcaLifecycleProvider(transport=malformed, binding_digest="a" * 64, coordinator_handle="term-1")
    with pytest.raises(LifecycleError) as exc:
        provider.start_no_dispatch(operation_id=OPERATION_ID, logical_run_id=RUN_ID, manifest=_manifest())
    assert exc.value.code == "PROVIDER_SCHEMA_DRIFT"
