#!/usr/bin/env python3
"""Qualify M4 with one deterministic no-model Orca worker and one retry."""

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
from aether_mcp.content_store import ProtectedContentStore, StaticKeyProvider
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


def operation(project_id: str, contract: str, code: str) -> dict[str, Any]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": contract,
        "use_case_id": "UC-C03",
        "reason": {"code": code, "summary": "M4 deterministic worker qualification", "authority_ref": "decision:m4"},
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def manifest(project_id: str) -> dict[str, Any]:
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m4/qualification",
            "generation": 1,
            "objective": "qualify one deterministic worker with retry",
            "acceptance": ["failed first attempt", "question reply", "validated artifact", "sealed episode"],
            "non_goals": ["external model", "credentials", "spend"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "semantic close and zero survivors",
        },
        "evaluation": {"enabled": True, "use_case_id": "UC-C03", "variant": "fixture-retry", "measurement_contract": "M0 frozen"},
        "learning": {"capture_policy": "FULL_EPISODE", "purpose": ["dogfood", "evaluation"], "consent_authority_ref": "decision:m4"},
        "tasks": [
            {
                "task_key": "worker",
                "deliverable": "write one deterministic artifact",
                "archetype": "fixture",
                "dependencies": [],
                "read_scope": ["README.md"],
                "write_scope": ["out"],
                "evidence_requirements": ["artifact digest", "exit-code digest"],
                "attempt_budget": 2,
                "placement": "child_worktree",
            }
        ],
    }


def wait_file(path: Path, timeout: float = 20) -> bytes:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if path.is_file():
                return path.read_bytes()
        except OSError:
            pass
        time.sleep(0.05)
    raise QualificationError(f"fixture output did not appear: {path.name}")


def message(
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
            "operation": operation(project_id, "contract:m4/qualification", f"M4_{kind.upper()}"),
            "run_id": run_id,
            "sender_id": sender,
            "recipient_id": recipient,
            "kind": kind,
            "payload": json.dumps(payload, sort_keys=True, separators=(",", ":")),
            "safe_summary": f"M4 {kind}",
            "decision_required": decision_required,
            "blocking_effect": "LOCAL_REVERSIBLE" if decision_required else None,
        }
    )


def exercise(output: Path, xvfb: Path) -> dict[str, Any]:
    require(APPIMAGE.is_file() and CLI.is_file() and FIXTURE.is_file() and xvfb.is_file(), "M4 prerequisites unavailable")
    root = Path(tempfile.mkdtemp(prefix="aether-m4-", dir="/tmp"))
    display = unused_display()
    env = build_env(root, display)
    app_dir, app_run = prepare_appimage(root, env)
    env["APPDIR"] = str(app_dir)
    project = root / "project"
    prepare_repo(project)
    (project / "out").mkdir()
    xvfb_process: subprocess.Popen[bytes] | None = None
    orca_process: subprocess.Popen[bytes] | None = None
    evidence: dict[str, Any] = {"status": "INCOMPLETE", "isolated_root": str(root)}
    completed = False
    try:
        xvfb_process = start_xvfb(xvfb, root, env, display)
        orca_process = start_orca(root, env, app_run, 1)
        result(run_json(("repo", "add", "--path", str(project), "--json"), app_run=app_run, cwd=project, env=env))
        coordinator = find_string(
            result(
                run_json(
                    ("terminal", "create", "--worktree", f"path:{project}", "--title", "AETHER-M4", "--command", "bash", "--json"),
                    app_run=app_run,
                    cwd=project,
                    env=env,
                )
            ),
            {"agentTerminalHandle", "handle"},
            contains="term",
        )

        context = TrustedLaunchContext.from_environment(
            {
                "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
                "HERMES_HOME": env["HERMES_HOME"],
                "AETHER_PROFILE": env["AETHER_PROFILE"],
                "AETHER_SESSION_ID": env["AETHER_SESSION_ID"],
            }
        )
        trace = TraceStore(root / "aether-state/trace")
        catalog = OrcaCatalog.load(CATALOG)
        admissions = ProjectAdmissionRegistry(root / "aether-state/admissions")
        foundation = M2Foundation(context=context, admissions=admissions, trace=trace, catalog=catalog)
        admitted = foundation.project_admit(
            {
                "operation": {
                    "operation_id": str(uuid.uuid4()),
                    "contract_id": "contract:m4/admit",
                    "use_case_id": "UC-C01",
                    "reason": {"code": "M4_ADMIT", "summary": "M4 isolated project", "authority_ref": "decision:m4"},
                    "expected_effect": "LOCAL_REVERSIBLE",
                },
                "project_root": str(project),
                "safe_alias": "m4-qualification",
                "capture_policy": "FULL_EPISODE",
                "consent_authority_ref": "decision:m4",
            }
        )
        validated = foundation.swarm_validate({"manifest": manifest(admitted.project_id)})
        lifecycle_store = LifecycleStore(root / "aether-state/lifecycle")
        lifecycle_store.register_manifest(validated, manifest_ref="manifest:m4/qualification")

        fixture_control = {"cancel": False}

        def fixture_command(dispatch_id: str, worktree: str, _spec: dict[str, Any], generation: int) -> str:
            mode = "success" if fixture_control["cancel"] else ("fail-after" if generation == 1 else "question")
            args = [
                "python3",
                str(FIXTURE),
                "--root",
                worktree,
                "--artifact",
                "out/result.json",
                "--worker",
                dispatch_id,
                "--mode",
                mode,
                "--timeout",
                "30",
            ]
            if generation == 2:
                args.extend(("--question-file", "out/question.json", "--answer-file", "out/answer.txt"))
            if fixture_control["cancel"]:
                args.extend(("--release-file", "out/release"))
            return f"mkdir -p out; {shlex.join(args)}; rc=$?; printf '%s\\n' \"$rc\" > out/exit-code"

        transport = lambda argv: run_json(argv, app_run=app_run, cwd=project, env=env)  # noqa: E731
        fixture_runtime = FixtureRuntimeConfig(
            repo_selector=f"path:{project}",
            base_ref="HEAD",
            command_builder=fixture_command,
        )
        provider = PublicOrcaLifecycleProvider(
            transport=transport,
            binding_digest=catalog.digest,
            coordinator_handle=coordinator,
            fixture_runtime=fixture_runtime,
        )
        lifecycle = LifecycleService(foundation=foundation, store=lifecycle_store, provider=provider)
        started = lifecycle.swarm_start(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_START"),
                "manifest_digest": validated.digest,
                "manifest_ref": "manifest:m4/qualification",
                "provider_binding_digest": catalog.digest,
                "dispatch_ready": False,
            }
        )
        content = ProtectedContentStore(
            root / "aether-state/content",
            key_provider=StaticKeyProvider({admitted.project_id: b"m" * 32}),
            quota_bytes=2_000_000,
        )
        worker_store = WorkerStore(root / "aether-state/workers")
        service = WorkerService(lifecycle=lifecycle, store=worker_store, provider=provider, content_store=content)
        first = service.swarm_dispatch(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_DISPATCH"),
                "run_id": started["run_id"],
                "task_keys": ["worker"],
            }
        )["dispatches"][0]
        first_attempt = worker_store.attempt(first["dispatch_id"])
        first_root = Path(first_attempt.worktree_id[5:])
        first_exit = wait_file(first_root / "out/exit-code")
        require(first_exit.strip() == b"22", "first fixture attempt did not fail after artifact")
        first_artifact = wait_file(first_root / "out/result.json")
        first_digest = hashlib.sha256(first_artifact).hexdigest()
        failed_message = message(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            sender=first["dispatch_id"],
            recipient="coordinator",
            kind="completion_reference",
            payload={
                "artifact_path": "out/result.json",
                "artifact_digest": first_digest,
                "evidence_digest": hashlib.sha256(first_exit).hexdigest(),
                "outcome": "FAILED",
                "worktree_id": first_attempt.worktree_id,
            },
        )
        retried = service.swarm_retry(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_RETRY"),
                "run_id": started["run_id"],
                "task_id": first["task_id"],
                "dispatch_id": first["dispatch_id"],
                "prior_outcome": "FAILED",
                "correction_summary": "retry deterministic fixture in question mode",
                "contract_generation": 1,
            }
        )
        second_attempt = worker_store.attempt(retried["dispatch_id"])
        second_root = Path(second_attempt.worktree_id[5:])
        wait_file(second_root / "out/question.json")
        question = message(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            sender=retried["dispatch_id"],
            recipient="coordinator",
            kind="technical_question",
            payload={"thread_id": "thread-m4", "question": "approved-value?"},
            decision_required=True,
        )

        terminate_group(orca_process)
        orca_process = None
        orca_process = start_orca(root, env, app_run, 2)
        replacement = find_string(
            result(
                run_json(
                    ("terminal", "create", "--worktree", f"path:{project}", "--title", "AETHER-M4-R", "--command", "bash", "--json"),
                    app_run=app_run,
                    cwd=project,
                    env=env,
                )
            ),
            {"agentTerminalHandle", "handle"},
            contains="term",
        )
        run_binding = lifecycle_store.run(started["run_id"], project_id=admitted.project_id)
        result(
            run_json(
                ("orchestration", "run-use", "--id", run_binding.provider_run_id, "--from", replacement, "--json"),
                app_run=app_run,
                cwd=project,
                env=env,
            )
        )
        provider = PublicOrcaLifecycleProvider(
            transport=transport,
            binding_digest=catalog.digest,
            coordinator_handle=replacement,
            fixture_runtime=fixture_runtime,
        )
        lifecycle = LifecycleService(foundation=foundation, store=LifecycleStore(lifecycle_store.root), provider=provider)
        service = WorkerService(
            lifecycle=lifecycle,
            store=WorkerStore(worker_store.root),
            provider=provider,
            content_store=content,
        )
        reply = message(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            sender="coordinator",
            recipient=retried["dispatch_id"],
            kind="reply",
            payload={"thread_id": "thread-m4", "reply_to": question["message_id"], "answer": "approved"},
        )
        (second_root / "out/answer.txt").write_text("approved\n", encoding="utf-8")
        second_exit = wait_file(second_root / "out/exit-code")
        require(second_exit.strip() == b"0", "retry fixture did not succeed")
        second_artifact = wait_file(second_root / "out/result.json")
        second_digest = hashlib.sha256(second_artifact).hexdigest()
        completion = message(
            service,
            project_id=admitted.project_id,
            run_id=started["run_id"],
            sender=retried["dispatch_id"],
            recipient="coordinator",
            kind="completion_reference",
            payload={
                "artifact_path": "out/result.json",
                "artifact_digest": second_digest,
                "evidence_digest": hashlib.sha256(second_exit).hexdigest(),
                "outcome": "SUCCEEDED",
                "worktree_id": second_attempt.worktree_id,
            },
        )
        closed = service.swarm_close(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_CLOSE"),
                "run_id": started["run_id"],
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
        episode = service.seal_episode(
            run_id=started["run_id"], final_state_digest=second_digest, labels=("fixture-pass", "retry-pass")
        )
        replayed = service.replay_episode(episode["episode_id"])
        require(closed["outcome"] == "CLOSED" and not closed["survivors"], "M4 aggregate close failed")
        require(episode["capture_complete"] is True and len(replayed["replayed_content"]) >= 3, "M4 episode replay incomplete")
        require(not first_root.exists() and not second_root.exists(), "M4 worker worktree survived close")

        fixture_control["cancel"] = True
        cancel_started = lifecycle.swarm_start(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_CANCEL_START"),
                "manifest_digest": validated.digest,
                "manifest_ref": "manifest:m4/qualification",
                "provider_binding_digest": catalog.digest,
                "dispatch_ready": False,
            }
        )
        cancel_dispatch = service.swarm_dispatch(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_CANCEL_DISPATCH"),
                "run_id": cancel_started["run_id"],
                "task_keys": ["worker"],
            }
        )["dispatches"][0]
        cancel_attempt = worker_store.attempt(cancel_dispatch["dispatch_id"])
        cancel_root = Path(cancel_attempt.worktree_id[5:])
        wait_file(cancel_root / "out/result.json")
        cancel_dispatch_receipt = service.swarm_cancel(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_CANCEL_DISPATCH_EXACT"),
                "run_id": cancel_started["run_id"],
                "target_type": "dispatch",
                "target_id": cancel_dispatch["dispatch_id"],
            }
        )
        cancel_run_receipt = service.swarm_cancel(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_CANCEL_RUN"),
                "run_id": cancel_started["run_id"],
                "target_type": "run",
                "target_id": cancel_started["run_id"],
            }
        )
        cancel_closed = service.swarm_close(
            {
                "operation": operation(admitted.project_id, "contract:m4/qualification", "M4_CANCEL_CLOSE"),
                "run_id": cancel_started["run_id"],
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
        require(
            cancel_dispatch_receipt["outcome"] == "CANCELLED"
            and cancel_run_receipt["outcome"] == "CANCELLED"
            and cancel_closed["outcome"] == "CLOSED"
            and not cancel_root.exists(),
            "M4 real cancellation did not close cleanly",
        )

        listed = run_json(("terminal", "list", "--json"), app_run=app_run, cwd=project, env=env)
        coordinator_closes = terminal_handles(listed)
        run_json(
            ("terminal", "stop", "--worktree", f"path:{project}", "--json"),
            app_run=app_run,
            cwd=project,
            env=env,
        )
        run_json(("orchestration", "reset", "--all", "--json"), app_run=app_run, cwd=project, env=env)
        evidence = {
            "status": "PASS",
            "orca_version": "1.4.167",
            "binding": "desktop-renderer+public-cli",
            "headless_claim": False,
            "run_id": started["run_id"],
            "provider_run_id": run_binding.provider_run_id,
            "first_attempt": {"dispatch_id": first["dispatch_id"], "outcome": failed_message["outcome"], "exit_code": 22},
            "retry": {"dispatch_id": retried["dispatch_id"], "generation": retried["generation"], "exit_code": 0},
            "question": question,
            "reply": reply,
            "completion": completion,
            "restart_recovered": True,
            "close": closed,
            "episode": {
                "episode_id": episode["episode_id"],
                "manifest_digest": episode["episode_manifest_digest"],
                "capture_complete": episode["capture_complete"],
                "content_refs": len(episode["content_refs"]),
                "replay_items": len(replayed["replayed_content"]),
            },
            "cancellation": {
                "dispatch": cancel_dispatch_receipt,
                "run": cancel_run_receipt,
                "close": cancel_closed,
            },
            "terminal_cleanup": coordinator_closes,
            "workers": 1,
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
        evidence = exercise(args.output.resolve(), args.xvfb.resolve())
    except Exception as exc:
        payload: dict[str, Any] = {}
        if args.output.is_file():
            try:
                loaded = json.loads(args.output.read_text())
                if isinstance(loaded, dict):
                    payload.update(loaded)
            except Exception:
                pass
        payload.update({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:500]})
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(json.dumps(payload, sort_keys=True))
        return 1
    print(json.dumps({"status": evidence.get("status"), "output": str(args.output)}, sort_keys=True))
    return 0 if evidence.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
