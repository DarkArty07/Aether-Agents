#!/usr/bin/env python3
"""Qualify deterministic M5 parallel coordination through exact public Orca CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from qualify_m3_lifecycle import (
    APPIMAGE,
    CLI,
    build_env,
    find_string,
    prepare_appimage,
    prepare_repo,
    result,
    run_json,
    start_orca,
    start_xvfb,
    terminal_handles,
    terminate_group,
    terminate_owned_processes,
    unused_display,
)

from aether_mcp.admission import ProjectAdmissionRegistry, TrustedLaunchContext
from aether_mcp.catalog import OrcaCatalog
from aether_mcp.coordination import WorkerService, WorkerStore
from aether_mcp.foundation import M2Foundation
from aether_mcp.lifecycle import LifecycleService, LifecycleStore
from aether_mcp.orca_provider import FixtureRuntimeConfig, PublicOrcaLifecycleProvider
from aether_mcp.trace_store import TraceStore

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas/orca/1.4.167/catalog.json"
FIXTURE = ROOT / "tests/fixtures/aether_mcp/deterministic_worker.py"


class QualificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QualificationError(message)


def operation(project_id: str, code: str) -> dict[str, Any]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": "contract:m5/qualification",
        "use_case_id": "UC-C05",
        "reason": {"code": code, "summary": "M5 deterministic parallel qualification", "authority_ref": "decision:m5"},
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def manifest(project_id: str) -> dict[str, Any]:
    tasks = []
    for key in ("alpha", "beta"):
        tasks.append(
            {
                "task_key": key,
                "deliverable": f"produce deterministic {key} artifact",
                "archetype": "fixture",
                "dependencies": [],
                "read_scope": ["README.md"],
                "write_scope": [f"out/{key}"],
                "evidence_requirements": ["artifact digest", "barrier overlap"],
                "attempt_budget": 1,
                "placement": "child_worktree",
            }
        )
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m5/qualification",
            "generation": 1,
            "objective": "prove two deterministic Orca workers overlap and clean up",
            "acceptance": ["overlap", "handoff", "integration", "partial failure cancel", "zero survivors"],
            "non_goals": ["models", "credentials", "activation"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "M5 deterministic evidence sealed",
        },
        "evaluation": {"enabled": True, "use_case_id": "UC-C05", "variant": "parallel-fixture", "measurement_contract": "M0 frozen"},
        "learning": {"capture_policy": "STRUCTURED_ONLY", "purpose": ["evaluation"], "consent_authority_ref": "decision:m5"},
        "tasks": tasks,
    }


def wait_file(path: Path, timeout: float = 40.0) -> bytes:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return path.read_bytes()
        time.sleep(0.05)
    raise QualificationError(f"Timed out waiting for {path.name}")


def message(
    service: WorkerService,
    *,
    project_id: str,
    run_id: str,
    sender: str,
    recipient: str,
    kind: str,
    payload: dict[str, Any],
    code: str,
    decision_required: bool = False,
) -> dict[str, Any]:
    return service.swarm_message(
        {
            "operation": operation(project_id, code),
            "run_id": run_id,
            "sender_id": sender,
            "recipient_id": recipient,
            "kind": kind,
            "payload": json.dumps(payload, sort_keys=True),
            "safe_summary": f"M5 {kind}",
            "decision_required": decision_required,
            "blocking_effect": "LOCAL_REVERSIBLE" if decision_required else None,
        }
    )


def complete(
    service: WorkerService,
    *,
    project_id: str,
    run_id: str,
    dispatch: dict[str, Any],
    attempt_root: Path,
    attempt_worktree_id: str,
    outcome: str,
    code: str,
) -> tuple[str, int]:
    artifact = wait_file(attempt_root / f"out/{dispatch['task_key']}/result.json")
    exit_code = int(wait_file(attempt_root / "out/exit-code").strip())
    digest = hashlib.sha256(artifact).hexdigest()
    response = message(
        service,
        project_id=project_id,
        run_id=run_id,
        sender=dispatch["dispatch_id"],
        recipient="coordinator",
        kind="completion_reference",
        payload={
            "artifact_path": f"out/{dispatch['task_key']}/result.json",
            "artifact_digest": digest,
            "evidence_digest": hashlib.sha256(str(exit_code).encode()).hexdigest(),
            "outcome": outcome,
            "worktree_id": attempt_worktree_id,
        },
        code=code,
    )
    require(response["outcome"] == "TECHNICALLY_COMPLETED", "Worker completion was not recorded")
    return digest, exit_code


def exercise(output: Path, xvfb: Path) -> dict[str, Any]:
    root = Path(tempfile.mkdtemp(prefix="aether-m5-", dir="/tmp"))
    display = unused_display()
    env = build_env(root, display)
    app_dir, app_run = prepare_appimage(root, env)
    env["APPDIR"] = str(app_dir)
    project = root / "project"
    prepare_repo(project)
    evidence: dict[str, Any] = {"status": "INCOMPLETE", "isolated_root": str(root)}
    xvfb_process: subprocess.Popen[bytes] | None = None
    orca_process: subprocess.Popen[bytes] | None = None
    completed = False
    try:
        xvfb_process = start_xvfb(xvfb, root, env, display)
        orca_process = start_orca(root, env, app_run, 1)
        result(run_json(("repo", "add", "--path", str(project), "--json"), app_run=app_run, cwd=project, env=env))
        coordinator_value = run_json(
            ("terminal", "create", "--worktree", f"path:{project}", "--title", "M5 coordinator", "--command", "bash", "--json"),
            app_run=app_run,
            cwd=project,
            env=env,
        )
        coordinator = find_string(
            result(coordinator_value), {"agentTerminalHandle", "handle"}, contains="term"
        )

        context = TrustedLaunchContext.from_environment(
            {
                "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
                "HERMES_HOME": env["HERMES_HOME"],
                "AETHER_PROFILE": env["AETHER_PROFILE"],
                "AETHER_SESSION_ID": env["AETHER_SESSION_ID"],
            }
        )
        catalog = OrcaCatalog.load(CATALOG)
        foundation = M2Foundation(
            context=context,
            admissions=ProjectAdmissionRegistry(root / "aether-state/admissions"),
            trace=TraceStore(root / "aether-state/trace"),
            catalog=catalog,
        )
        admitted = foundation.project_admit(
            {
                "operation": {
                    "operation_id": str(uuid.uuid4()),
                    "contract_id": "contract:m5/admission",
                    "use_case_id": "UC-C01",
                    "reason": {"code": "M5_ADMIT", "summary": "admit M5 isolated root", "authority_ref": "decision:m5"},
                    "expected_effect": "LOCAL_REVERSIBLE",
                },
                "project_root": str(project),
                "safe_alias": "m5-qualification",
                "capture_policy": "STRUCTURED_ONLY",
                "consent_authority_ref": "decision:m5",
            }
        )
        validated = foundation.swarm_validate({"manifest": manifest(admitted.project_id)})
        lifecycle_store = LifecycleStore(root / "aether-state/lifecycle")
        lifecycle_store.register_manifest(validated, manifest_ref="manifest:m5/qualification")
        mode = {"partial": False}
        barrier = root / "shared-barrier"
        barrier.mkdir(mode=0o700)

        def fixture_command(dispatch_id: str, worktree: str, spec: dict[str, Any], _generation: int) -> str:
            key = spec["task_key"]
            if mode["partial"]:
                worker_mode = "fail-after" if key == "alpha" else "success"
            else:
                worker_mode = "barrier"
            args = [
                "python3",
                str(FIXTURE),
                "--root",
                worktree,
                "--artifact",
                f"out/{key}/result.json",
                "--worker",
                key,
                "--mode",
                worker_mode,
                "--timeout",
                "30",
            ]
            if not mode["partial"]:
                args.extend(("--barrier-dir", str(barrier), "--shared-root", str(root), "--peers", "2"))
            elif key == "beta":
                args.extend(("--release-file", "out/release"))
            return f"mkdir -p out/{key}; {shlex.join(args)}; rc=$?; printf '%s\\n' \"$rc\" > out/exit-code"

        transport = lambda argv: run_json(argv, app_run=app_run, cwd=project, env=env)  # noqa: E731
        runtime = FixtureRuntimeConfig(repo_selector=f"path:{project}", base_ref="HEAD", command_builder=fixture_command)
        provider = PublicOrcaLifecycleProvider(
            transport=transport, binding_digest=catalog.digest, coordinator_handle=coordinator, fixture_runtime=runtime
        )
        lifecycle = LifecycleService(foundation=foundation, store=lifecycle_store, provider=provider)
        worker_store = WorkerStore(root / "aether-state/workers")
        service = WorkerService(lifecycle=lifecycle, store=worker_store, provider=provider, content_store=None)

        started = lifecycle.swarm_start(
            {
                "operation": operation(admitted.project_id, "M5_START"),
                "manifest_digest": validated.digest,
                "manifest_ref": "manifest:m5/qualification",
                "provider_binding_digest": catalog.digest,
                "dispatch_ready": False,
            }
        )
        alpha = service.swarm_dispatch(
            {"operation": operation(admitted.project_id, "M5_DISPATCH_ALPHA"), "run_id": started["run_id"], "task_keys": ["alpha"]}
        )["dispatches"][0]
        beta = service.swarm_dispatch(
            {"operation": operation(admitted.project_id, "M5_DISPATCH_BETA"), "run_id": started["run_id"], "task_keys": ["beta"]}
        )["dispatches"][0]
        alpha_attempt = worker_store.attempt(alpha["dispatch_id"])
        beta_attempt = worker_store.attempt(beta["dispatch_id"])
        alpha_root = Path(alpha_attempt.worktree_id[5:])
        beta_root = Path(beta_attempt.worktree_id[5:])

        # Polling begins only after both public Dispatch receipts exist.
        alpha_ready = wait_file(barrier / "alpha.ready")
        beta_ready = wait_file(barrier / "beta.ready")
        alpha_overlap = wait_file(barrier / "alpha.overlap")
        beta_overlap = wait_file(barrier / "beta.overlap")
        ready_latest = max((barrier / "alpha.ready").stat().st_mtime_ns, (barrier / "beta.ready").stat().st_mtime_ns)
        overlap_earliest = min((barrier / "alpha.overlap").stat().st_mtime_ns, (barrier / "beta.overlap").stat().st_mtime_ns)
        require(ready_latest <= overlap_earliest, "Workers did not overlap at the barrier")

        peer_question = message(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            sender=beta["dispatch_id"],
            recipient=alpha["dispatch_id"],
            kind="technical_question",
            payload={"thread_id": "m5-handoff", "question": "provide alpha artifact evidence"},
            code="M5_PEER_QUESTION",
            decision_required=True,
        )

        alpha_digest, alpha_exit = complete(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            dispatch=alpha,
            attempt_root=alpha_root,
            attempt_worktree_id=alpha_attempt.worktree_id,
            outcome="SUCCEEDED",
            code="M5_COMPLETE_ALPHA",
        )
        handoff = message(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            sender=alpha["dispatch_id"],
            recipient=beta["dispatch_id"],
            kind="dependency_handoff",
            payload={
                "artifact_digest": alpha_digest,
                "evidence_digest": hashlib.sha256(str(alpha_exit).encode()).hexdigest(),
                "reply_to": peer_question["message_id"],
            },
            code="M5_HANDOFF_ALPHA_BETA",
        )
        beta_digest, beta_exit = complete(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            dispatch=beta,
            attempt_root=beta_root,
            attempt_worktree_id=beta_attempt.worktree_id,
            outcome="SUCCEEDED",
            code="M5_COMPLETE_BETA",
        )
        integrated = service.integrate_artifacts(
            run_id=started["run_id"],
            output_path="integration/result.json",
            component_dispatch_ids=(alpha["dispatch_id"], beta["dispatch_id"]),
        )
        integrated_bytes = (project / "integration/result.json").read_bytes()
        require(hashlib.sha256(integrated_bytes).hexdigest() == integrated["artifact_digest"], "Integration digest mismatch")
        success_closed = service.swarm_close(
            {
                "operation": operation(admitted.project_id, "M5_CLOSE_SUCCESS"),
                "run_id": started["run_id"],
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
        require(success_closed["outcome"] == "CLOSED" and not alpha_root.exists() and not beta_root.exists(), "Success Run cleanup failed")

        mode["partial"] = True
        partial = lifecycle.swarm_start(
            {
                "operation": operation(admitted.project_id, "M5_PARTIAL_START"),
                "manifest_digest": validated.digest,
                "manifest_ref": "manifest:m5/qualification",
                "provider_binding_digest": catalog.digest,
                "dispatch_ready": False,
            }
        )
        partial_alpha = service.swarm_dispatch(
            {"operation": operation(admitted.project_id, "M5_PARTIAL_ALPHA"), "run_id": partial["run_id"], "task_keys": ["alpha"]}
        )["dispatches"][0]
        partial_beta = service.swarm_dispatch(
            {"operation": operation(admitted.project_id, "M5_PARTIAL_BETA"), "run_id": partial["run_id"], "task_keys": ["beta"]}
        )["dispatches"][0]
        partial_alpha_attempt = worker_store.attempt(partial_alpha["dispatch_id"])
        partial_beta_attempt = worker_store.attempt(partial_beta["dispatch_id"])
        partial_alpha_root = Path(partial_alpha_attempt.worktree_id[5:])
        partial_beta_root = Path(partial_beta_attempt.worktree_id[5:])
        _partial_digest, partial_exit = complete(
            service,
            project_id=admitted.project_id,
            run_id=partial["run_id"],
            dispatch=partial_alpha,
            attempt_root=partial_alpha_root,
            attempt_worktree_id=partial_alpha_attempt.worktree_id,
            outcome="FAILED",
            code="M5_PARTIAL_ALPHA_FAILED",
        )
        wait_file(partial_beta_root / "out/beta/result.json")
        run_cancel = service.swarm_cancel(
            {
                "operation": operation(admitted.project_id, "M5_PARTIAL_RUN_CANCEL"),
                "run_id": partial["run_id"],
                "target_type": "run",
                "target_id": partial["run_id"],
            }
        )
        beta_cancel = service.swarm_cancel(
            {
                "operation": operation(admitted.project_id, "M5_PARTIAL_BETA_CANCEL"),
                "run_id": partial["run_id"],
                "target_type": "dispatch",
                "target_id": partial_beta["dispatch_id"],
            }
        )
        partial_closed = service.swarm_close(
            {
                "operation": operation(admitted.project_id, "M5_PARTIAL_CLOSE"),
                "run_id": partial["run_id"],
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
        require(
            partial_exit == 22
            and run_cancel["outcome"] == "CANCELLED"
            and beta_cancel["outcome"] == "CANCELLED"
            and partial_closed["outcome"] == "CLOSED"
            and not partial_alpha_root.exists()
            and not partial_beta_root.exists(),
            "Partial failure/cancel cleanup failed",
        )

        listed = run_json(("terminal", "list", "--json"), app_run=app_run, cwd=project, env=env)
        coordinator_handles = terminal_handles(listed)
        run_json(("terminal", "stop", "--worktree", f"path:{project}", "--json"), app_run=app_run, cwd=project, env=env)
        run_json(("orchestration", "reset", "--all", "--json"), app_run=app_run, cwd=project, env=env)
        evidence = {
            "status": "PASS_DETERMINISTIC_M5",
            "orca_version": "1.4.167",
            "binding": "desktop-renderer+public-cli",
            "headless_claim": False,
            "success_run": {
                "run_id": started["run_id"],
                "dispatches_issued_before_poll": [alpha["dispatch_id"], beta["dispatch_id"]],
                "alpha_exit": alpha_exit,
                "beta_exit": beta_exit,
                "alpha_digest": alpha_digest,
                "beta_digest": beta_digest,
                "handoff": handoff,
                "peer_question": peer_question,
                "integration": integrated,
                "close": success_closed,
            },
            "overlap": {
                "alpha_ready": json.loads(alpha_ready),
                "beta_ready": json.loads(beta_ready),
                "alpha_overlap": json.loads(alpha_overlap),
                "beta_overlap": json.loads(beta_overlap),
                "ready_latest_ns": ready_latest,
                "overlap_earliest_ns": overlap_earliest,
                "proved": True,
            },
            "partial_failure_cancel": {
                "run_id": partial["run_id"],
                "alpha_exit": partial_exit,
                "run_cancel": run_cancel,
                "beta_cancel": beta_cancel,
                "close": partial_closed,
            },
            "model_backed_gate": {
                "status": "UNKNOWN_NOT_AUTHORIZED",
                "reason": "No provider, model, credentials, budget or stop limit was authorized for M5.4",
                "substituted_by_fixture": False,
            },
            "coordinator_terminals_cleaned": coordinator_handles,
            "workers": 2,
            "external_models": 0,
            "credentials": 0,
            "spend": 0,
            "mcp_registered": False,
            "callable_tools": 0,
        }
        completed = True
    finally:
        terminate_group(orca_process)
        terminate_group(xvfb_process)
        terminated, survivors = terminate_owned_processes(root)
        displays = [str(path) for path in (Path(f"/tmp/.X{display}-lock"), Path(f"/tmp/.X11-unix/X{display}")) if path.exists()]
        mounts = [str(path) for path in (root / "tmp").glob(".mount_orca-*")] if root.exists() else []
        evidence["cleanup"] = {
            "owned_processes_after_renderer_stop": terminated,
            "owned_process_survivors": survivors,
            "display_survivors": displays,
            "mount_survivors": mounts,
        }
        if survivors or displays or mounts:
            evidence["status"] = "FAIL"
        evidence["isolated_root_retained"] = not completed
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if completed:
            shutil.rmtree(root, ignore_errors=True)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--xvfb", type=Path, required=True)
    args = parser.parse_args()
    try:
        for required in (APPIMAGE, CLI, CATALOG, FIXTURE, args.xvfb):
            if not required.exists():
                raise QualificationError(f"Required file is unavailable: {required}")
        value = exercise(args.output.resolve(), args.xvfb.resolve())
    except Exception as exc:
        value: dict[str, Any] = {}
        if args.output.exists():
            try:
                value = json.loads(args.output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                value = {}
        value.update({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(value, sort_keys=True))
        return 1
    print(json.dumps({"status": value["status"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
