"""M4 bounded dispatch, messaging, retry and episode contracts."""

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
from aether_mcp.content_store import ProtectedContentStore, StaticKeyProvider
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
from aether_mcp.trace_store import TraceStore

CATALOG = Path(__file__).resolve().parents[2] / "schemas/orca/1.4.167/catalog.json"


class Provider:
    binding_digest = "a" * 64

    def __init__(self) -> None:
        self.provider_run = "run_m4"
        self.provider_task = "task_m4"
        self.task_status = "ready"
        self.dispatch_calls = 0
        self.model_dispatch_calls = 0
        self.retry_calls = 0
        self.message_calls: list[dict[str, Any]] = []
        self.stop_calls = 0

    def start_no_dispatch(self, **_kwargs: Any) -> ProviderStartResult:
        return ProviderStartResult("APPLIED", "request-start", self.provider_run, (("worker", self.provider_task),), "1" * 64)

    def inspect_run(self, *, provider_run_id: str) -> ProviderRunProjection:
        return ProviderRunProjection(
            provider_run_id,
            "terminal" if self.task_status in {"completed", "failed", "blocked"} else "running",
            (ProviderTaskProjection("worker", self.provider_task, self.task_status),),
            (),
            1,
            "fixture-provider",
        )

    def reconcile_start(self, **_kwargs: Any) -> ProviderStartResult | None:
        return None

    def cancel(self, **_kwargs: Any) -> ProviderEffectResult:
        self.task_status = "failed"
        return ProviderEffectResult("APPLIED", "request-cancel", (self.provider_task,), "2" * 64, True)

    def close(self, **_kwargs: Any) -> ProviderEffectResult:
        return ProviderEffectResult("APPLIED", "request-close", (), "3" * 64, True)

    def dispatch_fixture(self, **kwargs: Any) -> ProviderDispatchResult:
        self.dispatch_calls += 1
        self.task_status = "dispatched"
        return ProviderDispatchResult(
            outcome="APPLIED",
            provider_request_id=f"request-dispatch-{self.dispatch_calls}",
            provider_dispatch_id=f"dispatch_provider_{self.dispatch_calls}",
            worker_id=f"worker_provider_{self.dispatch_calls}",
            terminal_id=f"term_provider_{self.dispatch_calls}",
            worktree_id=f"worktree_provider_{self.dispatch_calls}",
            response_digest=f"{self.dispatch_calls + 3:x}" * 64,
        )

    def dispatch_model(self, **kwargs: Any) -> ProviderDispatchResult:
        self.model_dispatch_calls += 1
        self.task_status = "dispatched"
        return ProviderDispatchResult(
            outcome="APPLIED",
            provider_request_id=f"request-model-{self.model_dispatch_calls}",
            provider_dispatch_id=f"dispatch_model_{self.model_dispatch_calls}",
            worker_id=f"worker_model_{self.model_dispatch_calls}",
            terminal_id=f"term_model_{self.model_dispatch_calls}",
            worktree_id=f"worktree_model_{self.model_dispatch_calls}",
            response_digest="c" * 64,
        )

    def retry_fixture(self, **kwargs: Any) -> ProviderDispatchResult:
        self.retry_calls += 1
        self.task_status = "dispatched"
        return ProviderDispatchResult(
            outcome="APPLIED",
            provider_request_id=f"request-retry-{self.retry_calls}",
            provider_dispatch_id=f"dispatch_retry_{self.retry_calls}",
            worker_id=f"worker_retry_{self.retry_calls}",
            terminal_id=f"term_retry_{self.retry_calls}",
            worktree_id=f"worktree_retry_{self.retry_calls}",
            response_digest="8" * 64,
        )

    def send_worker_message(self, **kwargs: Any) -> ProviderMessageResult:
        self.message_calls.append(kwargs)
        if kwargs["kind"] == "completion_reference":
            self.task_status = "completed" if kwargs["outcome"] == "SUCCEEDED" else "failed"
        return ProviderMessageResult("APPLIED", f"message_provider_{len(self.message_calls)}", "9" * 64)

    def stop_worker(self, **_kwargs: Any) -> ProviderEffectResult:
        self.stop_calls += 1
        self.task_status = "failed"
        return ProviderEffectResult("APPLIED", "request-stop", (), "a" * 64, True)

    def cleanup_worker(self, **_kwargs: Any) -> ProviderEffectResult:
        return ProviderEffectResult("APPLIED", "request-cleanup", (), "b" * 64, True)


def _operation(project_id: str, contract: str, code: str) -> dict[str, Any]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": contract,
        "use_case_id": "UC-C03",
        "reason": {"code": code, "summary": "M4 deterministic fixture", "authority_ref": "decision:m4"},
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def _manifest(project_id: str, *, archetype: str = "fixture") -> dict[str, Any]:
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m4",
            "generation": 1,
            "objective": "one deterministic worker",
            "acceptance": ["validated artifact", "sealed episode"],
            "non_goals": ["models", "external effects"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "semantic close",
        },
        "evaluation": {"enabled": True, "use_case_id": "UC-C03", "variant": "fixture", "measurement_contract": "M0 frozen"},
        "learning": {"capture_policy": "FULL_EPISODE", "purpose": ["dogfood", "evaluation"], "consent_authority_ref": "decision:m4"},
        "tasks": [
            {
                "task_key": "worker",
                "deliverable": "write deterministic artifact",
                "archetype": archetype,
                "dependencies": [],
                "read_scope": ["src"],
                "write_scope": ["out"],
                "evidence_requirements": ["artifact digest", "fixture result"],
                "attempt_budget": 2,
                "placement": "child_worktree",
            }
        ],
    }


def _runtime(
    tmp_path: Path, *, archetype: str = "fixture"
) -> tuple[WorkerService, Provider, dict[str, Any], str, Path]:
    project = tmp_path / "project"
    project.mkdir()
    (project / "out").mkdir()
    (project / "README.md").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(("git", "init", "--initial-branch=main"), cwd=project, check=True, capture_output=True)
    subprocess.run(("git", "add", "README.md"), cwd=project, check=True, capture_output=True)
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=Aether Test",
            "-c",
            "user.email=aether@invalid",
            "commit",
            "-m",
            "init",
        ),
        cwd=project,
        check=True,
        capture_output=True,
    )
    (tmp_path / "home").mkdir()
    context = TrustedLaunchContext.from_environment(
        {
            "AETHER_COORDINATOR_PRINCIPAL": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "HERMES_HOME": str(tmp_path / "home"),
            "AETHER_PROFILE": "m4-test",
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
                "reason": {"code": "ADMIT", "summary": "m4 test admission", "authority_ref": "decision:m4"},
                "expected_effect": "LOCAL_REVERSIBLE",
            },
            "project_root": str(project),
            "safe_alias": "m4-test",
            "capture_policy": "FULL_EPISODE",
            "consent_authority_ref": "decision:m4",
        }
    )
    validated = foundation.swarm_validate(
        {"manifest": _manifest(admitted.project_id, archetype=archetype)}
    )
    lifecycle_store = LifecycleStore(tmp_path / "lifecycle")
    lifecycle_store.register_manifest(validated, manifest_ref="manifest:m4")
    provider = Provider()
    lifecycle = LifecycleService(foundation=foundation, store=lifecycle_store, provider=provider)
    started = lifecycle.swarm_start(
        {
            "operation": _operation(admitted.project_id, "contract:m4", "START"),
            "manifest_digest": validated.digest,
            "manifest_ref": "manifest:m4",
            "provider_binding_digest": provider.binding_digest,
            "dispatch_ready": False,
        }
    )
    content = ProtectedContentStore(
        tmp_path / "content",
        key_provider=StaticKeyProvider({admitted.project_id: b"k" * 32}),
        quota_bytes=2_000_000,
    )
    service = WorkerService(
        lifecycle=lifecycle,
        store=WorkerStore(tmp_path / "workers"),
        provider=provider,
        content_store=content,
    )
    return service, provider, started, admitted.project_id, project


def _dispatch(service: WorkerService, started: dict[str, Any], project_id: str) -> dict[str, Any]:
    return service.swarm_dispatch(
        {
            "operation": _operation(project_id, "contract:m4", "DISPATCH"),
            "run_id": started["run_id"],
            "task_keys": ["worker"],
        }
    )


def _message(
    service: WorkerService,
    *,
    project_id: str,
    run_id: str,
    sender: str,
    recipient: str,
    kind: str,
    payload: dict[str, Any],
    decision_required: bool = False,
) -> dict[str, Any]:
    return service.swarm_message(
        {
            "operation": _operation(project_id, "contract:m4", f"MESSAGE_{kind.upper()}"),
            "run_id": run_id,
            "sender_id": sender,
            "recipient_id": recipient,
            "kind": kind,
            "payload": json.dumps(payload, sort_keys=True),
            "safe_summary": kind,
            "decision_required": decision_required,
            "blocking_effect": "LOCAL_REVERSIBLE" if decision_required else None,
        }
    )


def test_dispatch_is_exact_replay_safe_and_persists_new_attempt(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = _runtime(tmp_path)
    request = {
        "operation": _operation(project_id, "contract:m4", "DISPATCH"),
        "run_id": started["run_id"],
        "task_keys": ["worker"],
    }
    first = service.swarm_dispatch(request)
    repeated = service.swarm_dispatch(request)
    assert first["dispatches"] == repeated["dispatches"]
    assert first["replayed"] is False and repeated["replayed"] is True
    assert provider.dispatch_calls == 1
    attempt = service.store.attempt(first["dispatches"][0]["dispatch_id"])
    assert attempt.generation == 1 and attempt.state == "ACTIVE"


def test_dispatch_routes_explicit_model_archetype_without_fixture_fallback(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = _runtime(tmp_path, archetype="model")
    result = _dispatch(service, started, project_id)
    assert result["outcome"] == "DISPATCHED"
    assert provider.model_dispatch_calls == 1
    assert provider.dispatch_calls == 0
    assert result["dispatches"][0]["provider_dispatch_id"] == "dispatch_model_1"


def test_model_retry_fails_closed_without_fixture_fallback(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = _runtime(tmp_path, archetype="model")
    first = _dispatch(service, started, project_id)["dispatches"][0]
    service.store.mark_terminal(first["dispatch_id"], state="FAILED", evidence_digest="f" * 64)
    with pytest.raises(CoordinationError) as captured:
        service.swarm_retry(
            {
                "operation": _operation(project_id, "contract:m4", "MODEL_RETRY"),
                "run_id": started["run_id"],
                "task_id": first["task_id"],
                "dispatch_id": first["dispatch_id"],
                "prior_outcome": "FAILED",
                "correction_summary": "must not fall back to fixture",
                "contract_generation": 1,
            }
        )
    assert captured.value.code == "RETRY_FORBIDDEN"
    assert provider.retry_calls == 0
    assert provider.dispatch_calls == 0


def test_question_reply_correlation_and_completion_evidence(tmp_path: Path) -> None:
    service, provider, started, project_id, project = _runtime(tmp_path)
    dispatch = _dispatch(service, started, project_id)["dispatches"][0]
    logical_dispatch = dispatch["dispatch_id"]
    question = _message(
        service,
        project_id=project_id,
        run_id=started["run_id"],
        sender=logical_dispatch,
        recipient="coordinator",
        kind="technical_question",
        payload={"thread_id": "thread-1", "question": "approved?"},
        decision_required=True,
    )
    assert question["outcome"] == "SENT"
    reply = _message(
        service,
        project_id=project_id,
        run_id=started["run_id"],
        sender="coordinator",
        recipient=logical_dispatch,
        kind="reply",
        payload={"thread_id": "thread-1", "reply_to": question["message_id"], "answer": "yes"},
    )
    assert reply["outcome"] == "SENT"

    artifact = project / "out/result.json"
    artifact.write_text('{"safe":"secret=fixture-secret"}\n', encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with pytest.raises(CoordinationError) as missing:
        _message(
            service,
            project_id=project_id,
            run_id=started["run_id"],
            sender=logical_dispatch,
            recipient="coordinator",
            kind="completion_reference",
            payload={"artifact_path": "out/result.json", "artifact_digest": artifact_digest, "outcome": "SUCCEEDED"},
        )
    assert missing.value.code == "EVIDENCE_REQUIRED"

    completed = _message(
        service,
        project_id=project_id,
        run_id=started["run_id"],
        sender=logical_dispatch,
        recipient="coordinator",
        kind="completion_reference",
        payload={
            "artifact_path": "out/result.json",
            "artifact_digest": artifact_digest,
            "evidence_digest": "e" * 64,
            "outcome": "SUCCEEDED",
        },
    )
    assert completed["outcome"] == "TECHNICALLY_COMPLETED"
    assert service.store.attempt(logical_dispatch).state == "TECHNICAL_COMPLETE"
    assert len(provider.message_calls) == 3


def test_sender_recipient_thread_and_fenced_authority_rejections(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = _runtime(tmp_path)
    logical_dispatch = _dispatch(service, started, project_id)["dispatches"][0]["dispatch_id"]
    with pytest.raises(CoordinationError) as expanded_effect:
        service.swarm_message(
            {
                "operation": _operation(project_id, "contract:m4", "MESSAGE_EXPAND_EFFECT"),
                "run_id": started["run_id"],
                "sender_id": logical_dispatch,
                "recipient_id": "coordinator",
                "kind": "technical_question",
                "payload": json.dumps({"thread_id": "forbidden", "question": "deploy production"}),
                "safe_summary": "attempted authority expansion",
                "decision_required": True,
                "blocking_effect": "EXTERNAL_IRREVERSIBLE",
            }
        )
    assert expanded_effect.value.code == "EFFECT_NOT_AUTHORIZED"
    assert not provider.message_calls
    with pytest.raises(CoordinationError) as wrong_sender:
        _message(
            service,
            project_id=project_id,
            run_id=started["run_id"],
            sender="unknown-worker",
            recipient="coordinator",
            kind="progress",
            payload={"phase": "x"},
        )
    assert wrong_sender.value.code == "PRINCIPAL_UNAUTHORIZED"
    with pytest.raises(CoordinationError) as orphan_reply:
        _message(
            service,
            project_id=project_id,
            run_id=started["run_id"],
            sender="coordinator",
            recipient=logical_dispatch,
            kind="reply",
            payload={"thread_id": "missing", "reply_to": str(uuid.uuid4()), "answer": "x"},
        )
    assert orphan_reply.value.code == "MESSAGE_CORRELATION_INVALID"

    service.store.fence(logical_dispatch, reason="test fence")
    with pytest.raises(CoordinationError) as late:
        _message(
            service,
            project_id=project_id,
            run_id=started["run_id"],
            sender=logical_dispatch,
            recipient="coordinator",
            kind="progress",
            payload={"phase": "late"},
        )
    assert late.value.code == "STALE_ATTEMPT"


def test_retry_creates_new_generation_and_old_attempt_loses_authority(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = _runtime(tmp_path)
    first = _dispatch(service, started, project_id)["dispatches"][0]
    service.store.mark_terminal(first["dispatch_id"], state="FAILED", evidence_digest="f" * 64)
    retried = service.swarm_retry(
        {
            "operation": _operation(project_id, "contract:m4", "RETRY"),
            "run_id": started["run_id"],
            "task_id": first["task_id"],
            "dispatch_id": first["dispatch_id"],
            "prior_outcome": "FAILED",
            "correction_summary": "retry deterministic fixture",
            "contract_generation": 1,
        }
    )
    assert retried["dispatch_id"] != first["dispatch_id"]
    assert retried["generation"] == 2
    assert provider.retry_calls == 1
    assert service.store.attempt(first["dispatch_id"]).state == "FENCED"
    with pytest.raises(CoordinationError) as late:
        _message(
            service,
            project_id=project_id,
            run_id=started["run_id"],
            sender=first["dispatch_id"],
            recipient="coordinator",
            kind="progress",
            payload={"phase": "stale"},
        )
    assert late.value.code == "STALE_ATTEMPT"


def test_episode_seals_only_after_semantic_close_and_replays_redacted_content(tmp_path: Path) -> None:
    service, _provider, started, project_id, project = _runtime(tmp_path)
    dispatch = _dispatch(service, started, project_id)["dispatches"][0]
    artifact = project / "out/result.json"
    artifact.write_text('{"api_key":"sk-fixturesecret123456789"}\n', encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    _message(
        service,
        project_id=project_id,
        run_id=started["run_id"],
        sender=dispatch["dispatch_id"],
        recipient="coordinator",
        kind="completion_reference",
        payload={
            "artifact_path": "out/result.json",
            "artifact_digest": digest,
            "evidence_digest": "d" * 64,
            "outcome": "SUCCEEDED",
        },
    )
    with pytest.raises(CoordinationError) as open_run:
        service.seal_episode(run_id=started["run_id"], final_state_digest="c" * 64, labels=("fixture-pass",))
    assert open_run.value.code == "RUN_NOT_CLOSED"

    service.swarm_close(
        {
            "operation": _operation(project_id, "contract:m4", "CLOSE"),
            "run_id": started["run_id"],
            "effect_plan": ["LOCAL_REVERSIBLE"],
            "retained_resource_ids": [],
        }
    )
    sealed = service.seal_episode(run_id=started["run_id"], final_state_digest="c" * 64, labels=("fixture-pass",))
    assert sealed["capture_complete"] is True
    replayed = service.replay_episode(sealed["episode_id"])
    serialized = json.dumps(replayed, sort_keys=True)
    assert "sk-fixturesecret" not in serialized
    assert "[REDACTED]" in serialized


def test_dispatch_cancel_fences_and_stops_exact_worker(tmp_path: Path) -> None:
    service, provider, started, project_id, _project = _runtime(tmp_path)
    dispatch = _dispatch(service, started, project_id)["dispatches"][0]
    cancelled = service.swarm_cancel(
        {
            "operation": _operation(project_id, "contract:m4", "CANCEL"),
            "run_id": started["run_id"],
            "target_type": "dispatch",
            "target_id": dispatch["dispatch_id"],
        }
    )
    assert cancelled["outcome"] == "CANCELLED"
    assert provider.stop_calls == 1
    assert service.store.attempt(dispatch["dispatch_id"]).state == "FENCED"
