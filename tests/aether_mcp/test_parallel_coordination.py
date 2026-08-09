"""M5 deterministic parallel overlap, handoff and integration contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest

from aether_mcp.admission import ProjectAdmissionRegistry, TrustedLaunchContext
from aether_mcp.catalog import OrcaCatalog
from aether_mcp.coordination import (
    CoordinationError,
    ProviderDispatchResult,
    ProviderMessageResult,
    WorkerService,
    WorkerStore,
)
from aether_mcp.foundation import M2Foundation
from aether_mcp.lifecycle import (
    LifecycleService,
    LifecycleStore,
    ProviderEffectResult,
    ProviderRunProjection,
    ProviderStartResult,
    ProviderTaskProjection,
)
from aether_mcp.manifest import ManifestError
from aether_mcp.trace_store import TraceStore

CATALOG = Path(__file__).resolve().parents[2] / "schemas/orca/1.4.167/catalog.json"


class ParallelProvider:
    binding_digest = "a" * 64

    def __init__(self) -> None:
        self.statuses = {"alpha": "ready", "beta": "ready"}
        self.task_ids = {"alpha": "task_parallel_alpha", "beta": "task_parallel_beta"}
        self.dispatches = 0
        self.messages: list[dict[str, Any]] = []

    def start_no_dispatch(self, **_kwargs: Any) -> ProviderStartResult:
        return ProviderStartResult(
            "APPLIED",
            "request-start",
            "run_parallel",
            tuple((key, value) for key, value in self.task_ids.items()),
            "1" * 64,
        )

    def inspect_run(self, *, provider_run_id: str) -> ProviderRunProjection:
        terminal = all(status in {"completed", "failed", "blocked"} for status in self.statuses.values())
        return ProviderRunProjection(
            provider_run_id,
            "terminal" if terminal else "running",
            tuple(ProviderTaskProjection(key, self.task_ids[key], status) for key, status in self.statuses.items()),
            (),
            1,
            "parallel-fixture",
        )

    def reconcile_start(self, **_kwargs: Any) -> None:
        return None

    def cancel(self, *, target_type: str, provider_target_id: str, **_kwargs: Any) -> ProviderEffectResult:
        if target_type == "run":
            self.statuses = {key: "failed" for key in self.statuses}
        else:
            for key, value in self.task_ids.items():
                if value == provider_target_id:
                    self.statuses[key] = "failed"
        return ProviderEffectResult("APPLIED", "request-cancel", (), "2" * 64, True)

    def close(self, **_kwargs: Any) -> ProviderEffectResult:
        return ProviderEffectResult("APPLIED", "request-close", (), "3" * 64, True)

    def dispatch_fixture(self, *, provider_task_id: str, **_kwargs: Any) -> ProviderDispatchResult:
        self.dispatches += 1
        key = next(key for key, value in self.task_ids.items() if value == provider_task_id)
        self.statuses[key] = "dispatched"
        return ProviderDispatchResult(
            "APPLIED",
            f"request-dispatch-{self.dispatches}",
            f"dispatch_parallel_{key}",
            f"worker_parallel_{key}",
            f"term_parallel_{key}",
            f"worktree_parallel_{key}",
            f"{self.dispatches + 3:x}" * 64,
        )

    def retry_fixture(self, **_kwargs: Any) -> ProviderDispatchResult:
        raise AssertionError("retry is outside this M5 test")

    def send_worker_message(self, *, provider_task_id: str, kind: str, outcome: str | None, **kwargs: Any) -> ProviderMessageResult:
        self.messages.append({"provider_task_id": provider_task_id, "kind": kind, "outcome": outcome, **kwargs})
        if kind == "completion_reference":
            key = next(key for key, value in self.task_ids.items() if value == provider_task_id)
            self.statuses[key] = "completed" if outcome == "SUCCEEDED" else "failed"
        return ProviderMessageResult("APPLIED", f"message_parallel_{len(self.messages)}", "9" * 64)

    def stop_worker(self, **_kwargs: Any) -> ProviderEffectResult:
        return ProviderEffectResult("APPLIED", "request-stop", (), "a" * 64, True)

    def cleanup_worker(self, **_kwargs: Any) -> ProviderEffectResult:
        return ProviderEffectResult("APPLIED", "request-cleanup", (), "b" * 64, True)


def op(project_id: str, code: str) -> dict[str, Any]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": "contract:m5",
        "use_case_id": "UC-C05",
        "reason": {"code": code, "summary": "M5 parallel fixture", "authority_ref": "decision:m5"},
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def manifest(project_id: str, *, conflict: bool = False) -> dict[str, Any]:
    tasks = []
    for key in ("alpha", "beta"):
        scope = "out/shared" if conflict else f"out/{key}"
        tasks.append(
            {
                "task_key": key,
                "deliverable": f"produce {key}",
                "archetype": "fixture",
                "dependencies": [],
                "read_scope": ["README.md"],
                "write_scope": [scope],
                "evidence_requirements": ["artifact digest"],
                "attempt_budget": 1,
                "placement": "child_worktree",
            }
        )
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m5",
            "generation": 1,
            "objective": "two deterministic workers",
            "acceptance": ["proved overlap", "artifact handoff", "coordinator integration"],
            "non_goals": ["models", "credentials"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "integrated and closed",
        },
        "evaluation": {"enabled": True, "use_case_id": "UC-C05", "variant": "fixture", "measurement_contract": "M0 frozen"},
        "learning": {"capture_policy": "STRUCTURED_ONLY", "purpose": ["evaluation"], "consent_authority_ref": "decision:m5"},
        "tasks": tasks,
    }


def runtime(tmp_path: Path, *, conflict: bool = False) -> tuple[WorkerService, ParallelProvider, dict[str, Any], str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("fixture\n")
    (project / "out/alpha").mkdir(parents=True)
    (project / "out/beta").mkdir(parents=True)
    subprocess.run(("git", "init", "--initial-branch=main"), cwd=project, check=True, capture_output=True)
    subprocess.run(("git", "add", "README.md"), cwd=project, check=True, capture_output=True)
    subprocess.run(
        ("git", "-c", "user.name=Aether", "-c", "user.email=aether@invalid", "commit", "-m", "init"),
        cwd=project,
        check=True,
        capture_output=True,
    )
    home = tmp_path / "home"
    home.mkdir()
    context = TrustedLaunchContext.from_environment(
        {
            "AETHER_COORDINATOR_PRINCIPAL": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "HERMES_HOME": str(home),
            "AETHER_PROFILE": "m5-test",
            "AETHER_SESSION_ID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        }
    )
    trace = TraceStore(tmp_path / "trace")
    foundation = M2Foundation(
        context=context,
        admissions=ProjectAdmissionRegistry(tmp_path / "admissions"),
        trace=trace,
        catalog=OrcaCatalog.load(CATALOG),
    )
    admitted = foundation.project_admit(
        {
            "operation": {
                "operation_id": str(uuid.uuid4()),
                "contract_id": "contract:admit",
                "use_case_id": "UC-C01",
                "reason": {"code": "ADMIT", "summary": "m5 test", "authority_ref": "decision:m5"},
                "expected_effect": "LOCAL_REVERSIBLE",
            },
            "project_root": str(project),
            "safe_alias": "m5-test",
            "capture_policy": "STRUCTURED_ONLY",
            "consent_authority_ref": "decision:m5",
        }
    )
    validated = foundation.swarm_validate({"manifest": manifest(admitted.project_id, conflict=conflict)})
    lifecycle_store = LifecycleStore(tmp_path / "lifecycle")
    lifecycle_store.register_manifest(validated, manifest_ref="manifest:m5")
    provider = ParallelProvider()
    lifecycle = LifecycleService(foundation=foundation, store=lifecycle_store, provider=provider)
    started = lifecycle.swarm_start(
        {
            "operation": op(admitted.project_id, "START"),
            "manifest_digest": validated.digest,
            "manifest_ref": "manifest:m5",
            "provider_binding_digest": provider.binding_digest,
            "dispatch_ready": False,
        }
    )
    service = WorkerService(
        lifecycle=lifecycle,
        store=WorkerStore(tmp_path / "workers"),
        provider=provider,
        content_store=None,
    )
    return service, provider, started, admitted.project_id, project


def dispatch(service: WorkerService, started: dict[str, Any], project_id: str, key: str) -> dict[str, Any]:
    return service.swarm_dispatch(
        {"operation": op(project_id, f"DISPATCH_{key.upper()}"), "run_id": started["run_id"], "task_keys": [key]}
    )["dispatches"][0]


def complete(
    service: WorkerService,
    *,
    started: dict[str, Any],
    project_id: str,
    project: Path,
    attempt: dict[str, Any],
    outcome: str,
) -> str:
    path = project / f"out/{attempt['task_key']}/result.json"
    path.write_text(json.dumps({"worker": attempt["task_key"]}, sort_keys=True) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    service.swarm_message(
        {
            "operation": op(project_id, f"COMPLETE_{attempt['task_key'].upper()}"),
            "run_id": started["run_id"],
            "sender_id": attempt["dispatch_id"],
            "recipient_id": "coordinator",
            "kind": "completion_reference",
            "payload": json.dumps(
                {
                    "artifact_path": f"out/{attempt['task_key']}/result.json",
                    "artifact_digest": digest,
                    "evidence_digest": digest,
                    "outcome": outcome,
                },
                sort_keys=True,
            ),
            "safe_summary": "completion",
            "decision_required": False,
            "blocking_effect": None,
        }
    )
    return digest


def test_disjoint_parallel_dispatch_and_existing_scope_conflict(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = runtime(tmp_path / "ok")
    alpha = dispatch(service, started, project_id, "alpha")
    beta = dispatch(service, started, project_id, "beta")
    assert alpha["dispatch_id"] != beta["dispatch_id"]
    assert provider.dispatches == 2

    with pytest.raises(ManifestError) as error:
        runtime(tmp_path / "conflict", conflict=True)
    assert error.value.code == "WRITE_SCOPE_CONFLICT"


def test_handoff_requires_immutable_predecessor_evidence_and_routes_to_peer(tmp_path: Path) -> None:
    service, provider, started, project_id, project = runtime(tmp_path)
    alpha = dispatch(service, started, project_id, "alpha")
    beta = dispatch(service, started, project_id, "beta")
    handoff = {
        "operation": op(project_id, "HANDOFF"),
        "run_id": started["run_id"],
        "sender_id": alpha["dispatch_id"],
        "recipient_id": beta["dispatch_id"],
        "kind": "dependency_handoff",
        "payload": json.dumps({"artifact_digest": "d" * 64, "evidence_digest": "e" * 64}),
        "safe_summary": "alpha handoff",
        "decision_required": False,
        "blocking_effect": None,
    }
    with pytest.raises(CoordinationError) as early:
        service.swarm_message(handoff)
    assert early.value.code == "EVIDENCE_REQUIRED"

    alpha_digest = complete(
        service, started=started, project_id=project_id, project=project, attempt=alpha, outcome="SUCCEEDED"
    )
    peer_question = service.swarm_message(
        {
            "operation": op(project_id, "PEER_QUESTION"),
            "run_id": started["run_id"],
            "sender_id": beta["dispatch_id"],
            "recipient_id": alpha["dispatch_id"],
            "kind": "technical_question",
            "payload": json.dumps({"thread_id": "m5-peer", "question": "handoff?"}),
            "safe_summary": "peer question",
            "decision_required": True,
            "blocking_effect": "LOCAL_REVERSIBLE",
        }
    )
    handoff["operation"] = op(project_id, "HANDOFF_READY")
    handoff["payload"] = json.dumps(
        {"artifact_digest": alpha_digest, "evidence_digest": alpha_digest, "reply_to": peer_question["message_id"]}
    )
    sent = service.swarm_message(handoff)
    assert sent["outcome"] == "SENT"
    assert provider.messages[-1]["provider_reply_to"] == "message_parallel_2"


def test_partial_failure_does_not_block_peer_and_coordinator_integrates(tmp_path: Path) -> None:
    service, _provider, started, project_id, project = runtime(tmp_path)
    alpha = dispatch(service, started, project_id, "alpha")
    beta = dispatch(service, started, project_id, "beta")
    complete(service, started=started, project_id=project_id, project=project, attempt=alpha, outcome="FAILED")
    beta_digest = complete(
        service, started=started, project_id=project_id, project=project, attempt=beta, outcome="SUCCEEDED"
    )
    with pytest.raises(CoordinationError) as failed_component:
        service.integrate_artifacts(
            run_id=started["run_id"], output_path="integration/result.json", component_dispatch_ids=(alpha["dispatch_id"], beta["dispatch_id"])
        )
    assert failed_component.value.code == "EVIDENCE_REQUIRED"

    # A separate all-success Run proves coordinator-owned integration.
    service2, _provider2, started2, project_id2, project2 = runtime(tmp_path / "success")
    alpha2 = dispatch(service2, started2, project_id2, "alpha")
    beta2 = dispatch(service2, started2, project_id2, "beta")
    alpha_digest = complete(
        service2, started=started2, project_id=project_id2, project=project2, attempt=alpha2, outcome="SUCCEEDED"
    )
    beta_digest2 = complete(
        service2, started=started2, project_id=project_id2, project=project2, attempt=beta2, outcome="SUCCEEDED"
    )
    integrated = service2.integrate_artifacts(
        run_id=started2["run_id"],
        output_path="integration/result.json",
        component_dispatch_ids=(alpha2["dispatch_id"], beta2["dispatch_id"]),
    )
    assert integrated["component_digests"] == sorted([alpha_digest, beta_digest2])
    assert (project2 / "integration/result.json").is_file()
    assert beta_digest != ""
