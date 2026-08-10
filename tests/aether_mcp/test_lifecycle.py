"""M3 manifest-bound lifecycle contracts, written before production implementation."""

from __future__ import annotations

import subprocess
import threading
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from aether_mcp.admission import ProjectAdmissionRegistry, TrustedLaunchContext
from aether_mcp.catalog import OrcaCatalog
from aether_mcp.foundation import M2Foundation
from aether_mcp.lifecycle import (
    LifecycleError,
    LifecycleService,
    LifecycleStore,
    ProviderEffectResult,
    ProviderRunProjection,
    ProviderStartResult,
    ProviderTaskProjection,
)
from aether_mcp.manifest import ValidatedManifest
from aether_mcp.trace_store import TraceStore

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas/orca/1.4.167/catalog.json"


def _repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(("git", "init", "--initial-branch=main"), cwd=path, check=True, capture_output=True)
    subprocess.run(
        ("git", "-c", "user.name=Aether Test", "-c", "user.email=aether@test.invalid", "commit", "--allow-empty", "-m", "init"),
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def _operation(project_id: str, *, operation_id: str | None = None) -> dict[str, object]:
    return {
        "operation_id": operation_id or str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": "contract:m3/1",
        "use_case_id": "UC-C01",
        "reason": {"code": "M3_TEST", "summary": "bounded lifecycle test", "authority_ref": "decision:m3"},
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def _manifest(project_id: str, *, task_keys: tuple[str, ...] = ("inspect", "summarize")) -> dict[str, object]:
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m3/1",
            "generation": 1,
            "objective": "exercise lifecycle without workers",
            "acceptance": ["Run and Tasks correlate exactly"],
            "non_goals": ["dispatch workers"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "zero survivors",
        },
        "evaluation": {"enabled": False, "use_case_id": "UC-C01", "variant": "m3", "measurement_contract": None},
        "learning": {"capture_policy": "STRUCTURED_ONLY", "purpose": ["evaluation"], "consent_authority_ref": "decision:m3"},
        "tasks": [
            {
                "task_key": key,
                "deliverable": f"metadata for {key}",
                "archetype": "fixture",
                "dependencies": [] if index == 0 else [task_keys[index - 1]],
                "read_scope": ["src"],
                "write_scope": [],
                "evidence_requirements": ["provider task identity"],
                "attempt_budget": 2,
                "placement": "read_only",
            }
            for index, key in enumerate(task_keys)
        ],
    }


def _start_args(validated: ValidatedManifest, project_id: str, *, operation_id: str | None = None) -> dict[str, object]:
    return {
        "operation": _operation(project_id, operation_id=operation_id),
        "manifest_digest": validated.digest,
        "manifest_ref": "manifest:m3/1",
        "provider_binding_digest": "a" * 64,
        "dispatch_ready": False,
    }


class FakeLifecycleProvider:
    binding_digest = "a" * 64

    def __init__(self) -> None:
        self.start_calls = 0
        self.cancel_calls = 0
        self.close_calls = 0
        self.reconcile_calls = 0
        self.fail_start: str | None = None
        self.cleanup_complete = True
        self.live_resources: tuple[str, ...] = ()
        self.task_status = "pending"
        self.accepted: dict[str, ProviderStartResult] = {}
        self.intent_was_durable = False
        self.trace: TraceStore | None = None

    def _projection(self, result: ProviderStartResult) -> ProviderRunProjection:
        return ProviderRunProjection(
            provider_run_id=result.provider_run_id or "run_missing",
            status="running" if self.task_status not in {"completed", "failed", "cancelled"} else "terminal",
            tasks=tuple(
                ProviderTaskProjection(task_key=key, provider_task_id=provider_id, status=self.task_status)
                for key, provider_id in result.provider_tasks
            ),
            live_resource_ids=self.live_resources,
            coordinator_generation=1,
            source="orca-public-cli",
        )

    def start_no_dispatch(
        self,
        *,
        operation_id: str,
        logical_run_id: str,
        manifest: ValidatedManifest,
    ) -> ProviderStartResult:
        self.start_calls += 1
        if self.trace is not None:
            self.intent_was_durable = self.trace.records_for(operation_id)[-1]["outcome"] == "PREPARED"
        if self.fail_start == "timeout":
            accepted = ProviderStartResult(
                outcome="APPLIED",
                provider_request_id=f"request-{operation_id[:8]}",
                provider_run_id=f"run_{logical_run_id.replace('-', '')[:12]}",
                provider_tasks=tuple((key, f"task_{index}_{key}") for index, key in enumerate(manifest.topological_order)),
                response_digest="b" * 64,
            )
            self.accepted[logical_run_id] = accepted
            raise TimeoutError("response lost after acceptance")
        tasks = tuple((key, f"task_{index}_{key}") for index, key in enumerate(manifest.topological_order))
        if self.fail_start == "partial":
            tasks = tasks[:-1]
        result = ProviderStartResult(
            outcome="PARTIAL" if self.fail_start == "partial" else "APPLIED",
            provider_request_id=f"request-{operation_id[:8]}",
            provider_run_id=f"run_{logical_run_id.replace('-', '')[:12]}",
            provider_tasks=tasks,
            response_digest="b" * 64,
        )
        self.accepted[logical_run_id] = result
        return result

    def inspect_run(self, *, provider_run_id: str) -> ProviderRunProjection:
        result = next(item for item in self.accepted.values() if item.provider_run_id == provider_run_id)
        return self._projection(result)

    def reconcile_start(self, *, operation_id: str, logical_run_id: str) -> ProviderStartResult | None:
        self.reconcile_calls += 1
        return self.accepted.get(logical_run_id)

    def cancel(self, *, provider_run_id: str, target_type: str, provider_target_id: str) -> ProviderEffectResult:
        self.cancel_calls += 1
        self.task_status = "cancelled"
        return ProviderEffectResult("APPLIED", f"cancel-{self.cancel_calls}", (provider_target_id,), "c" * 64, True)

    def close(self, *, provider_run_id: str, effect_plan: tuple[str, ...]) -> ProviderEffectResult:
        self.close_calls += 1
        return ProviderEffectResult(
            "APPLIED" if self.cleanup_complete else "FAILED",
            f"close-{self.close_calls}",
            () if self.cleanup_complete else self.live_resources,
            "d" * 64,
            self.cleanup_complete,
        )


@pytest.fixture()
def system(tmp_path: Path):
    repo = _repo(tmp_path / "repo")
    home = tmp_path / "home"
    home.mkdir()
    context = TrustedLaunchContext.from_environment(
        {
            "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
            "HERMES_HOME": str(home),
            "AETHER_PROFILE": "hermes",
            "AETHER_SESSION_ID": str(uuid.uuid4()),
        }
    )
    trace = TraceStore(tmp_path / "trace")
    foundation = M2Foundation(
        context=context,
        admissions=ProjectAdmissionRegistry(tmp_path / "admissions"),
        trace=trace,
        catalog=OrcaCatalog.load(CATALOG),
    )
    admission = foundation.project_admit(
        {
            "operation": {
                "operation_id": str(uuid.uuid4()),
                "contract_id": "contract:m3/admit",
                "use_case_id": None,
                "reason": {"code": "M3_ADMIT", "summary": "admit test project", "authority_ref": "decision:m3"},
                "expected_effect": "LOCAL_REVERSIBLE",
            },
            "project_root": str(repo),
            "safe_alias": "m3-test",
            "capture_policy": "STRUCTURED_ONLY",
            "consent_authority_ref": "decision:m3",
        }
    )
    validated = foundation.swarm_validate({"manifest": _manifest(admission.project_id)})
    store = LifecycleStore(tmp_path / "lifecycle")
    store.register_manifest(validated, manifest_ref="manifest:m3/1")
    provider = FakeLifecycleProvider()
    provider.trace = trace
    service = LifecycleService(foundation=foundation, store=store, provider=provider)
    return admission, validated, trace, store, provider, service


def test_start_persists_intent_correlates_exact_tasks_and_replays_once(system) -> None:
    admission, validated, trace, store, provider, service = system
    operation_id = str(uuid.uuid4())
    request = _start_args(validated, admission.project_id, operation_id=operation_id)

    first = service.swarm_start(request)
    second = service.swarm_start(request)

    assert provider.intent_was_durable is True
    assert provider.start_calls == 1
    assert first["outcome"] == "SUCCEEDED"
    assert first["replayed"] is False
    assert second["replayed"] is True
    assert first["run_id"] == second["run_id"]
    assert first["tasks"] == second["tasks"]
    assert [task["task_key"] for task in first["tasks"]] == list(validated.topological_order)
    assert all(uuid.UUID(task["task_id"]) for task in first["tasks"])
    binding = store.run(first["run_id"], project_id=admission.project_id)
    assert binding.provider_run_id.startswith("run_")
    assert [record["phase"] for record in trace.records_for(operation_id)] == ["INTENT", "RECEIPT"]


def test_start_rejects_dispatch_manifest_drift_and_conflicting_replay(system) -> None:
    admission, validated, _trace, _store, provider, service = system
    request = _start_args(validated, admission.project_id)

    with pytest.raises(LifecycleError) as exc:
        service.swarm_start({**request, "dispatch_ready": True})
    assert exc.value.code == "EFFECT_NOT_AUTHORIZED"

    with pytest.raises(LifecycleError) as exc:
        service.swarm_start({**request, "manifest_digest": "f" * 64})
    assert exc.value.code == "MANIFEST_INVALID"

    service.swarm_start(request)
    assert isinstance(request["operation"], dict)
    changed_operation: dict[str, Any] = dict(request["operation"])
    changed_operation["reason"] = {
        "code": "M3_TEST",
        "summary": "different canonical request",
        "authority_ref": "decision:m3",
    }
    with pytest.raises(LifecycleError) as exc:
        service.swarm_start({**request, "operation": changed_operation})
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    assert provider.start_calls == 1


def test_partial_start_and_timeout_stay_unknown_without_duplicate_effect(system) -> None:
    admission, validated, trace, _store, provider, service = system
    provider.fail_start = "partial"
    partial_request = _start_args(validated, admission.project_id)
    partial = service.swarm_start(partial_request)
    assert partial["outcome"] == "UNKNOWN"
    assert partial["tasks"] == []

    provider.fail_start = "timeout"
    operation_id = str(uuid.uuid4())
    request = _start_args(validated, admission.project_id, operation_id=operation_id)
    first = service.swarm_start(request)
    second = service.swarm_start(request)
    assert first["outcome"] == second["outcome"] == "UNKNOWN"
    assert provider.start_calls == 2  # one partial operation plus one timed-out operation
    assert trace.records_for(operation_id)[-1]["error_code"] == "DELIVERY_UNKNOWN"


def test_unknown_start_reconciles_after_restart_without_reexecution(system) -> None:
    admission, validated, trace, store, provider, service = system
    provider.fail_start = "timeout"
    operation_id = str(uuid.uuid4())
    request = _start_args(validated, admission.project_id, operation_id=operation_id)
    unknown = service.swarm_start(request)
    assert unknown["outcome"] == "UNKNOWN"

    provider.fail_start = None
    restarted = LifecycleService(foundation=service.foundation, store=LifecycleStore(store.root), provider=provider)
    reconcile = restarted.swarm_reconcile(
        {
            "operation": _operation(admission.project_id),
            "run_id": unknown["run_id"],
            "target_type": "operation",
            "target_id": operation_id,
            "mode": "observe",
            "evidence_sources": ["orca.run-list", "orca.task-list"],
        }
    )
    assert reconcile["outcome"] == "SUCCEEDED"
    assert provider.start_calls == 1
    assert provider.reconcile_calls == 1
    assert store.run(unknown["run_id"], project_id=admission.project_id).provider_run_id.startswith("run_")
    assert trace.records_for(operation_id)[-1]["phase"] == "RECONCILE"


def test_status_is_source_labelled_and_rejects_provider_identity_drift(system) -> None:
    admission, validated, _trace, _store, provider, service = system
    started = service.swarm_start(_start_args(validated, admission.project_id))
    status = service.swarm_status(
        {"project_id": admission.project_id, "run_id": started["run_id"], "cursor": None, "wait_ms": 0, "detail": "tasks"}
    )
    assert status["source"] == "orca-public-cli"
    assert status["run_id"] == started["run_id"]
    assert {task["task_id"] for task in status["tasks"]} == {task["task_id"] for task in started["tasks"]}

    accepted = provider.accepted[started["run_id"]]
    provider.accepted[started["run_id"]] = replace(
        accepted,
        provider_tasks=(("forged", accepted.provider_tasks[0][1]),) + accepted.provider_tasks[1:],
    )
    with pytest.raises(LifecycleError) as exc:
        service.swarm_status(
            {"project_id": admission.project_id, "run_id": started["run_id"], "cursor": None, "wait_ms": 0, "detail": "tasks"}
        )
    assert exc.value.code == "PROVIDER_RESPONSE_INVALID"


def test_cancel_and_close_require_terminal_state_and_zero_survivors(system) -> None:
    admission, validated, _trace, _store, provider, service = system
    started = service.swarm_start(_start_args(validated, admission.project_id))
    run_id = started["run_id"]

    with pytest.raises(LifecycleError) as exc:
        service.swarm_close(
            {
                "operation": _operation(admission.project_id),
                "run_id": run_id,
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
    assert exc.value.code == "CLEANUP_INCOMPLETE"
    assert provider.close_calls == 0

    cancel_request = {
        "operation": _operation(admission.project_id),
        "run_id": run_id,
        "target_type": "run",
        "target_id": run_id,
    }
    cancelled = service.swarm_cancel(cancel_request)
    replayed = service.swarm_cancel(cancel_request)
    assert cancelled["outcome"] == "CANCELLED"
    assert replayed["replayed"] is True
    assert provider.cancel_calls == 1

    provider.live_resources = ("terminal-live",)
    provider.cleanup_complete = False
    failed = service.swarm_close(
        {
            "operation": _operation(admission.project_id),
            "run_id": run_id,
            "effect_plan": ["LOCAL_REVERSIBLE"],
            "retained_resource_ids": [],
        }
    )
    assert failed["outcome"] == "CLEANUP_FAILED"

    provider.live_resources = ()
    provider.cleanup_complete = True
    closed = service.swarm_close(
        {
            "operation": _operation(admission.project_id),
            "run_id": run_id,
            "effect_plan": ["LOCAL_REVERSIBLE"],
            "retained_resource_ids": [],
        }
    )
    assert closed["outcome"] == "CLOSED"
    assert closed["survivors"] == []


def test_two_reconcilers_commit_only_one_terminal_observation(system) -> None:
    admission, validated, trace, _store, provider, service = system
    provider.fail_start = "timeout"
    operation_id = str(uuid.uuid4())
    unknown = service.swarm_start(_start_args(validated, admission.project_id, operation_id=operation_id))
    provider.fail_start = None
    request = {
        "operation": _operation(admission.project_id),
        "run_id": unknown["run_id"],
        "target_type": "operation",
        "target_id": operation_id,
        "mode": "observe",
        "evidence_sources": ["orca.run-list"],
    }
    outcomes: list[str] = []

    def reconcile() -> None:
        outcomes.append(service.swarm_reconcile(request)["outcome"])

    threads = [threading.Thread(target=reconcile) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes == ["SUCCEEDED", "SUCCEEDED"]
    assert [record["phase"] for record in trace.records_for(operation_id)].count("RECONCILE") == 1
