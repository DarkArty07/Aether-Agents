#!/usr/bin/env python3
"""Qualify M5.4 with two bounded real Codex workers through public Orca CLI."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from qualify_m3_lifecycle import (
    APPIMAGE,
    CLI,
    build_env,
    find_string,
    prepare_appimage,
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
from aether_mcp.coordination import CoordinationError, WorkerService, WorkerStore
from aether_mcp.foundation import M2Foundation
from aether_mcp.lifecycle import LifecycleService, LifecycleStore
from aether_mcp.manifest import ManifestError, validate_swarm_manifest
from aether_mcp.orca_provider import ModelRuntimeConfig, PublicOrcaLifecycleProvider
from aether_mcp.trace_store import TraceStore

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas/orca/1.4.167/catalog.json"
EXPECTED_MODEL = "gpt-5.6-terra"
MAX_WORKER_SECONDS = 600
MODEL_LIVENESS_SECONDS = 90
MODEL_SUBMIT_RECOVERY_AFTER_SECONDS = 5


class QualificationError(RuntimeError):
    """Bounded qualification failure with no permission expansion."""


def fail(message: str) -> NoReturn:
    raise QualificationError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def baseline_runs_admitted(runs: list[dict[str, Any]]) -> bool:
    return len(runs) <= 1 and all(
        run.get("id") == "run_legacy_local" and run.get("legacy") == 1 for run in runs
    )


def operation(project_id: str, code: str, *, effect: str = "LOCAL_REVERSIBLE") -> dict[str, Any]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": "contract:m5.4/model-qualification",
        "use_case_id": "UC-C03",
        "reason": {
            "code": code,
            "summary": "M5.4 bounded real-model qualification",
            "authority_ref": "owner:2026-08-09:okay-hazlo",
        },
        "expected_effect": effect,
    }


def task_prompt(task: str) -> str:
    verifier = "python3 acceptance/verify_backend.py" if task == "backend" else "node acceptance/verify_frontend.mjs"
    return (
        f"Implement the {task} discount preview increment. Do not ask questions and do not use the web. "
        f"Your write scope is only {task}/; never edit contract/, acceptance/, the other worker scope, "
        "integration/, git config, or files outside this worktree. Your FIRST command must create "
        f"{task}/model-result.json with task='{task}', model='{EXPECTED_MODEL}', status='working', and "
        "started_at_ns=time.time_ns() using python3. Read README.md, contract/discount-v1.json and the "
        f"read-only verifier. Implement the required code under {task}/ using only installed standard tools. "
        f"Run `{verifier}`. LAST, update {task}/model-result.json with status='passed', finished_at_ns=time.time_ns(), "
        "the verifier command, and its zero exit code. Do not commit. Stop after the passing verifier."
    )


def worker_read_command(provider_dispatch_id: str, *, limit: int) -> tuple[str, ...]:
    require(bool(provider_dispatch_id) and limit > 0, "worker-read command inputs are invalid")
    return (
        "orchestration",
        "worker-read",
        "--dispatch",
        provider_dispatch_id,
        "--source",
        "auto",
        "--limit",
        str(limit),
        "--json",
    )


def manifest(project_id: str) -> dict[str, Any]:
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m5.4/model-qualification",
            "generation": 1,
            "objective": "deliver backend and accessible frontend discount preview increments in parallel",
            "acceptance": [
                "two real Codex workers dispatched before polling",
                "independent scopes and real execution overlap",
                "both frozen verifiers pass",
                "coordinator integration and zero survivors",
            ],
            "non_goals": ["web access", "external effects", "retry", "publication", "activation"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "one attempt per worker, semantic close, and zero survivors",
        },
        "evaluation": {
            "enabled": True,
            "use_case_id": "UC-C03",
            "variant": "model-backed-codex-parallel",
            "measurement_contract": "M0 frozen",
        },
        "learning": {
            "capture_policy": "STRUCTURED_ONLY",
            "purpose": ["evaluation"],
            "consent_authority_ref": "owner:2026-08-09:okay-hazlo",
        },
        "tasks": [
            {
                "task_key": key,
                "deliverable": task_prompt(key),
                "archetype": "model",
                "dependencies": [],
                "read_scope": ["README.md", "contract", "acceptance"],
                "write_scope": [key],
                "evidence_requirements": ["frozen verifier", "artifact digest", "model timing"],
                "attempt_budget": 1,
                "placement": "child_worktree",
            }
            for key in ("backend", "frontend")
        ],
    }


def prepare_fixture(project: Path) -> None:
    (project / "contract").mkdir(parents=True)
    (project / "acceptance").mkdir()
    (project / "backend").mkdir()
    (project / "frontend").mkdir()
    (project / "integration").mkdir()
    (project / "README.md").write_text(
        "# M5.4 discount preview fixture\n\n"
        "Two independent workers implement the frozen contract. contract/ and acceptance/ are read-only.\n"
        "No network, dependencies, publication, deployment, credential access, or writes outside the assigned scope.\n",
        encoding="utf-8",
    )
    contract = {
        "schema_version": "discount.preview/v1",
        "endpoint": {"method": "POST", "path": "/discount-preview"},
        "input": {"subtotal_cents": "non-negative integer", "coupon": "null or SAVE5"},
        "rules": {
            "threshold_cents": 10_000,
            "threshold_discount_bps": 1_000,
            "save5_discount_bps": 500,
            "maximum_discount_bps": 1_500,
            "rounding": "floor integer cents",
        },
        "output": ["subtotal_cents", "discount_cents", "total_cents", "discount_bps"],
    }
    (project / "contract/discount-v1.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (project / "acceptance/verify_backend.py").write_text(
        '''#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "backend/server.py"
assert target.is_file(), "backend/server.py missing"
spec = importlib.util.spec_from_file_location("discount_backend", target)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.calculate_discount(5_000, None) == {"subtotal_cents": 5000, "discount_cents": 0, "total_cents": 5000, "discount_bps": 0}
assert module.calculate_discount(20_000, None) == {"subtotal_cents": 20000, "discount_cents": 2000, "total_cents": 18000, "discount_bps": 1000}
assert module.calculate_discount(20_000, "SAVE5") == {"subtotal_cents": 20000, "discount_cents": 3000, "total_cents": 17000, "discount_bps": 1500}
for invalid in [(-1, None), (1.5, None), (1000, "BAD")]:
    try:
        module.calculate_discount(*invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(f"invalid input accepted: {invalid}")
status, headers, body = module.handle_request("POST", "/discount-preview", json.dumps({"subtotal_cents": 20000, "coupon": "SAVE5"}).encode())
assert status == 200
assert headers.get("content-type") == "application/json"
assert json.loads(body) == {"subtotal_cents": 20000, "discount_cents": 3000, "total_cents": 17000, "discount_bps": 1500}
status, _, body = module.handle_request("POST", "/discount-preview", b"{}")
assert status == 400 and json.loads(body)["error"] == "invalid_request"
print("backend_acceptance=PASS")
''',
        encoding="utf-8",
    )
    (project / "acceptance/verify_frontend.mjs").write_text(
        r'''import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import path from "node:path";

const target = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../frontend/discount-preview.mjs");
const module = await import(pathToFileURL(target).href);
assert.deepEqual(module.calculatePreview(5000, null), {subtotalCents:5000, discountCents:0, totalCents:5000, discountBps:0});
assert.deepEqual(module.calculatePreview(20000, null), {subtotalCents:20000, discountCents:2000, totalCents:18000, discountBps:1000});
assert.deepEqual(module.calculatePreview(20000, "SAVE5"), {subtotalCents:20000, discountCents:3000, totalCents:17000, discountBps:1500});
for (const value of [[-1, null], [1.5, null], [1000, "BAD"]]) {
  assert.throws(() => module.calculatePreview(...value));
}
const html = module.renderDiscountPreview(20000, "SAVE5");
assert.match(html, /<output[^>]*aria-live=["']polite["']/i);
assert.match(html, /Discount/i);
assert.match(html, /Total/i);
assert.match(html, /30\.00/);
assert.match(html, /170\.00/);
console.log("frontend_acceptance=PASS");
''',
        encoding="utf-8",
    )
    subprocess.run(("git", "init", "--initial-branch=main"), cwd=project, check=True, capture_output=True)
    subprocess.run(("git", "add", "."), cwd=project, check=True, capture_output=True)
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=Aether M5.4 Fixture",
            "-c",
            "user.email=aether-m54@invalid",
            "commit",
            "-m",
            "test: freeze model-backed discount fixture",
        ),
        cwd=project,
        check=True,
        capture_output=True,
    )


class RecordingTransport:
    def __init__(self, *, app_run: Path, cwd: Path, env: dict[str, str]) -> None:
        self.app_run = app_run
        self.cwd = cwd
        self.env = env
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: tuple[str, ...]) -> dict[str, Any]:
        self.calls.append(argv)
        return run_json(argv, app_run=self.app_run, cwd=self.cwd, env=self.env, timeout=150)


def account_summary(envelope: dict[str, Any]) -> dict[str, Any]:
    value = result(envelope)
    codex_block = value.get("codex", {})
    selected = codex_block.get("systemDefault") if isinstance(codex_block, dict) else None
    if not isinstance(selected, dict):
        selected = None

    def walk(item: Any) -> None:
        nonlocal selected
        if selected is not None:
            return
        if isinstance(item, dict):
            if item.get("provider") == "codex" and item.get("isSystemDefault") is True:
                selected = item
                return
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    if selected is None:
        walk(value)
    require(selected is not None and selected.get("hasAuth") is True, "System Codex OAuth is unavailable")
    assert selected is not None

    def safe_limits(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                key: safe_limits(child)
                for key, child in item.items()
                if key in {"rateLimits", "weekly", "fiveHour", "usedPercent", "resetAt", "windowMinutes"}
            }
        if isinstance(item, list):
            return [safe_limits(child) for child in item]
        if isinstance(item, (str, int, float, bool)) or item is None:
            return item
        return None

    return {
        "account_ref": "system-default-codex-oauth",
        "provider": "codex",
        "auth_source": selected.get("authSource") or selected.get("authKind"),
        "has_auth": True,
        "is_system_default": True,
        "limits": safe_limits(value.get("rateLimits", {}).get("codex", {})),
    }


def configured_model(env: dict[str, str]) -> str:
    target = Path(env["XDG_CONFIG_HOME"]) / "orca/codex-runtime-home/home/.orca-config-settings-baseline.json"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not target.is_file():
        time.sleep(0.1)
    require(target.is_file(), "Isolated Orca Codex model baseline is unavailable")
    value = json.loads(target.read_text(encoding="utf-8"))
    model = value.get("settings", {}).get("model")
    if isinstance(model, str) and model.startswith('"') and model.endswith('"'):
        model = json.loads(model)
    require(model == EXPECTED_MODEL, f"Unexpected Codex model: {model!r}")
    return model


def denial(code: str, action: Any, expected: str) -> dict[str, Any]:
    try:
        action()
    except (ManifestError, CoordinationError) as exc:
        require(exc.code == expected, f"{code} returned {exc.code}, expected {expected}")
        return {"case": code, "code": exc.code, "provider_effects": 0}
    fail(f"{code} was not denied")


def run_acceptance(worktree: Path, command: tuple[str, ...]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=worktree, capture_output=True, text=True, timeout=30, check=False)
    output = (completed.stdout + completed.stderr).strip()
    require(completed.returncode == 0, f"Frozen verifier failed: {output[:300]}")
    return {"command": list(command), "exit_code": completed.returncode, "output_digest": hashlib.sha256(output.encode()).hexdigest()}


def changed_paths(worktree: Path) -> list[str]:
    tracked = subprocess.run(
        ("git", "diff", "--name-only", "HEAD"), cwd=worktree, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    untracked = subprocess.run(
        ("git", "ls-files", "--others", "--exclude-standard"),
        cwd=worktree,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return sorted(set(tracked + untracked))


@dataclass(frozen=True)
class ModelWorkerTarget:
    provider_dispatch_id: str
    terminal_id: str
    worktree: Path


def _model_liveness_marker(task_key: str, target: ModelWorkerTarget) -> dict[str, Any] | None:
    path = target.worktree / task_key / "model-result.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        value.get("task") == task_key
        and value.get("status") in {"working", "passed"}
        and isinstance(value.get("started_at_ns"), int)
        and value["started_at_ns"] > 0
    ):
        return {
            "status": str(value["status"]),
            "started_at_ns": value["started_at_ns"],
        }
    return None


def wait_model_liveness(
    provider: Any,
    targets: dict[str, ModelWorkerTarget],
    *,
    timeout: float,
    nudge_after: float,
    poll_interval: float,
) -> dict[str, dict[str, Any]]:
    started = time.monotonic()
    deadline = started + timeout
    acknowledged: dict[str, dict[str, Any]] = {}
    observations: dict[str, dict[str, Any]] = {}
    submit_recoveries = {key: 0 for key in targets}
    while time.monotonic() < deadline:
        now = time.monotonic()
        for key, target in targets.items():
            if key in acknowledged:
                continue
            marker = _model_liveness_marker(key, target)
            if marker is not None:
                acknowledged[key] = {
                    "acknowledged_by": "working_marker",
                    "marker_status": marker["status"],
                    "started_at_ns": marker["started_at_ns"],
                    "submit_recovery_count": submit_recoveries[key],
                }
                continue
            observation = provider.observe_model_worker(target.provider_dispatch_id)
            observations[key] = {
                "source": observation.source,
                "activity_observed": observation.activity_observed,
                "idle_hint": observation.idle_hint,
                "blocked_reason": observation.blocked_reason,
                "response_digest": observation.response_digest,
                "response_bytes": observation.response_bytes,
            }
            if observation.blocked_reason is not None:
                fail(f"ERR_MODEL_TERMINAL_BLOCKED:{key}:{observation.blocked_reason}")
            if observation.activity_observed:
                acknowledged[key] = {
                    "acknowledged_by": "public_transcript",
                    "marker_status": None,
                    "submit_recovery_count": submit_recoveries[key],
                    "observation": observations[key],
                }
                continue
            if (
                now - started >= nudge_after
                and observation.idle_hint
                and submit_recoveries[key] == 0
            ):
                provider.submit_model_worker_enter(target.terminal_id)
                submit_recoveries[key] = 1
        if len(acknowledged) == len(targets):
            return acknowledged
        time.sleep(poll_interval)
    safe_summary = {
        key: {
            "observation": observations.get(key),
            "submit_recovery_count": submit_recoveries[key],
        }
        for key in sorted(targets)
        if key not in acknowledged
    }
    fail(
        "ERR_MODEL_PROMPT_NOT_ACKNOWLEDGED:"
        + json.dumps(safe_summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )


def resolve_model_interval(
    task_key: str,
    report: dict[str, Any],
    liveness: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    witnessed_start = liveness.get("started_at_ns")
    reported_start = report.get("started_at_ns")
    finished_at = report.get("finished_at_ns")
    if isinstance(witnessed_start, int):
        if reported_start is not None and reported_start != witnessed_start:
            fail(f"{task_key} timing report is invalid")
        started_at = witnessed_start
        source = "initial_working_marker"
    else:
        if not isinstance(reported_start, int):
            fail(f"{task_key} timing report is invalid")
        started_at = reported_start
        source = "final_model_report"
    if not isinstance(finished_at, int) or started_at >= finished_at:
        fail(f"{task_key} timing report is invalid")
    normalized = dict(report)
    normalized["started_at_ns"] = started_at
    return normalized, source


def wait_model_results(worktrees: dict[str, Path], timeout: float) -> dict[str, dict[str, Any]]:
    deadline = time.monotonic() + timeout
    results: dict[str, dict[str, Any]] = {}
    while time.monotonic() < deadline:
        for key, worktree in worktrees.items():
            target = worktree / key / "model-result.json"
            if key in results or not target.is_file():
                continue
            try:
                value = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if value.get("status") == "passed" and isinstance(value.get("finished_at_ns"), int):
                results[key] = value
        if len(results) == len(worktrees):
            return results
        time.sleep(1)
    fail("Model worker completion exceeded the 10-minute hard stop")


def complete_attempt(
    service: WorkerService,
    *,
    project_id: str,
    run_id: str,
    dispatch: dict[str, Any],
    worktree: Path,
    verification: dict[str, Any],
) -> dict[str, Any]:
    artifact_path = f"{dispatch['task_key']}/model-result.json"
    artifact = (worktree / artifact_path).read_bytes()
    artifact_digest = hashlib.sha256(artifact).hexdigest()
    evidence_digest = canonical_digest(verification)
    response = service.swarm_message(
        {
            "operation": operation(project_id, f"M54_COMPLETE_{dispatch['task_key'].upper()}"),
            "run_id": run_id,
            "sender_id": dispatch["dispatch_id"],
            "recipient_id": "coordinator",
            "kind": "completion_reference",
            "payload": json.dumps(
                {
                    "artifact_path": artifact_path,
                    "artifact_digest": artifact_digest,
                    "evidence_digest": evidence_digest,
                    "outcome": "SUCCEEDED",
                    "worktree_id": f"path:{worktree}",
                },
                sort_keys=True,
            ),
            "safe_summary": f"M5.4 {dispatch['task_key']} completion",
            "decision_required": False,
            "blocking_effect": None,
        }
    )
    require(response["outcome"] == "TECHNICALLY_COMPLETED", "Completion was not recorded")
    return {"artifact_digest": artifact_digest, "evidence_digest": evidence_digest, "message": response}


def exercise(
    output: Path,
    xvfb: Path,
    *,
    preflight_only: bool,
    existing_runtime: bool,
    existing_app_run: Path | None,
) -> dict[str, Any]:
    require(CLI.is_file(), "Orca CLI is unavailable")
    if not existing_runtime:
        require(APPIMAGE.is_file() and xvfb.is_file(), "M5.4 runtime prerequisites unavailable")
    host_home = Path.home().resolve()
    root = Path(tempfile.mkdtemp(prefix="aether-m54-model-", dir="/tmp"))
    root.chmod(0o700)
    display = 9999 if existing_runtime else unused_display()
    env = build_env(root, display)
    env["PATH"] = f"{host_home}/.local/bin:{env['PATH']}"
    env["AETHER_PROFILE"] = "m54-model-qualification"
    app_run: Path
    if existing_runtime:
        require(existing_app_run is not None and existing_app_run.is_file(), "Existing Orca AppRun is unavailable")
        assert existing_app_run is not None
        env["HOME"] = str(host_home)
        env["XDG_CONFIG_HOME"] = str(host_home / ".config")
        app_run = existing_app_run
        env["APPDIR"] = str(app_run.parent)
    else:
        host_codex_home = host_home / ".codex"
        require(host_codex_home.is_dir(), "Existing system Codex home is unavailable")
        (Path(env["HOME"]) / ".codex").symlink_to(host_codex_home, target_is_directory=True)
        shared_codex_runtime = host_home / ".config/orca/codex-runtime-home"
        require(shared_codex_runtime.is_dir(), "Existing Orca Codex runtime is unavailable")
        isolated_orca_config = Path(env["XDG_CONFIG_HOME"]) / "orca"
        isolated_orca_config.mkdir(mode=0o700, parents=True, exist_ok=True)
        (isolated_orca_config / "codex-runtime-home").symlink_to(
            shared_codex_runtime, target_is_directory=True
        )
        app_dir, app_run = prepare_appimage(root, env)
        env["APPDIR"] = str(app_dir)
    project = root / "fixture"
    prepare_fixture(project)
    evidence: dict[str, Any] = {
        "schema_version": "aether.m5.4-model-evidence/v1alpha1",
        "status": "INCOMPLETE",
        "authorized_at": "2026-08-09",
        "limits": {
            "provider": "codex",
            "agent": "codex-cli",
            "expected_model": EXPECTED_MODEL,
            "workers": 2,
            "attempts_per_worker": 1,
            "max_seconds_per_worker": MAX_WORKER_SECONDS,
            "payg_spend_authorized": False,
            "web_access": False,
        },
        "isolated_root": str(root),
    }
    xvfb_process: subprocess.Popen[bytes] | None = None
    orca_process: subprocess.Popen[bytes] | None = None
    coordinator: str | None = None
    transport: RecordingTransport | None = None
    account_before: dict[str, Any] | None = None
    try:
        codex_version = subprocess.run(
            ("codex", "--version"),
            cwd=project,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        codex_version_text = codex_version.stdout.strip()
        require(
            codex_version.returncode == 0 and codex_version_text.startswith("codex-cli "),
            "Codex CLI version is unavailable in the worker environment",
        )
        evidence["limits"]["codex_cli_version"] = codex_version_text.removeprefix("codex-cli ")
        if not existing_runtime:
            xvfb_process = start_xvfb(xvfb, root, env, display)
            orca_process = start_orca(root, env, app_run, 1)
        else:
            status = run_json(("status", "--json"), app_run=app_run, cwd=project, env=env)
            require(result(status)["runtime"]["state"] == "ready", "Existing Orca runtime is not ready")
        account_before = account_summary(
            run_json(("account", "list", "--json"), app_run=app_run, cwd=project, env=env)
        )
        model = configured_model(env)
        initial_terminals = terminal_handles(
            run_json(("terminal", "list", "--limit", "100", "--json"), app_run=app_run, cwd=project, env=env)
        )
        initial_runs = result(
            run_json(("orchestration", "run-list", "--json"), app_run=app_run, cwd=project, env=env)
        )
        baseline_runs = initial_runs.get("runs", [])
        require(not initial_terminals, "Orca baseline contains terminals")
        require(baseline_runs_admitted(baseline_runs), "Orca baseline contains non-legacy Runs")
        evidence["preflight"] = {
            "account": account_before,
            "configured_model": model,
            "terminal_count": 0,
            "run_count": len(baseline_runs),
            "baseline_run_ids": [run["id"] for run in baseline_runs],
            "profile_state": "persistent-with-post-run-metadata-rollback" if existing_runtime else "isolated-xdg",
            "home_usage": "existing system OAuth and Orca profile" if existing_runtime else "temporary HOME with only .codex linked to the existing authorized account",
            "shared_state_boundary": "persistent Orca metadata is restored from the post-reset baseline after the live run" if existing_runtime else "Codex account/model runtime only; Orca orchestration and Aether state remain isolated",
        }
        if preflight_only:
            evidence["status"] = "PASS_PREFLIGHT_NO_MODEL_CALL"
            return evidence

        result(run_json(("repo", "add", "--path", str(project), "--json"), app_run=app_run, cwd=project, env=env))
        coordinator = find_string(
            result(
                run_json(
                    (
                        "terminal",
                        "create",
                        "--worktree",
                        f"path:{project}",
                        "--title",
                        "AETHER-M5.4-COORDINATOR",
                        "--command",
                        "bash",
                        "--json",
                    ),
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
                    "contract_id": "contract:m5.4/admission",
                    "use_case_id": "UC-C01",
                    "reason": {
                        "code": "M54_ADMIT",
                        "summary": "admit disposable M5.4 fixture",
                        "authority_ref": "owner:2026-08-09:okay-hazlo",
                    },
                    "expected_effect": "LOCAL_REVERSIBLE",
                },
                "project_root": str(project),
                "safe_alias": "m54-model-qualification",
                "capture_policy": "STRUCTURED_ONLY",
                "consent_authority_ref": "owner:2026-08-09:okay-hazlo",
            }
        )
        valid_manifest = manifest(admitted.project_id)
        validated = foundation.swarm_validate({"manifest": valid_manifest})
        lifecycle_store = LifecycleStore(root / "aether-state/lifecycle")
        lifecycle_store.register_manifest(validated, manifest_ref="manifest:m5.4/model-qualification")
        transport = RecordingTransport(app_run=app_run, cwd=project, env=env)
        provider = PublicOrcaLifecycleProvider(
            transport=transport,
            binding_digest=catalog.digest,
            coordinator_handle=coordinator,
            model_runtime=ModelRuntimeConfig(
                repo_selector=f"path:{project}",
                base_ref="main",
                agent="codex",
                expected_model=EXPECTED_MODEL,
                timeout_ms=MAX_WORKER_SECONDS * 1000,
            ),
        )
        lifecycle = LifecycleService(foundation=foundation, store=lifecycle_store, provider=provider)
        store = WorkerStore(root / "aether-state/workers")
        service = WorkerService(lifecycle=lifecycle, store=store, provider=provider, content_store=None)
        started = lifecycle.swarm_start(
            {
                "operation": operation(admitted.project_id, "M54_START"),
                "manifest_digest": validated.digest,
                "manifest_ref": "manifest:m5.4/model-qualification",
                "provider_binding_digest": catalog.digest,
                "dispatch_ready": False,
            }
        )

        invalid_overlap = copy.deepcopy(valid_manifest)
        invalid_overlap["tasks"][1]["write_scope"] = ["backend"]
        invalid_forbidden = copy.deepcopy(valid_manifest)
        invalid_forbidden["tasks"][0]["archetype"] = "etalides"
        invalid_cycle = copy.deepcopy(valid_manifest)
        invalid_cycle["tasks"][0]["dependencies"] = ["frontend"]
        invalid_cycle["tasks"][1]["dependencies"] = ["backend"]
        denials = [
            denial("overlapping_write_scope", lambda: validate_swarm_manifest(invalid_overlap), "WRITE_SCOPE_CONFLICT"),
            denial("forbidden_participant", lambda: validate_swarm_manifest(invalid_forbidden), "PARTICIPANT_FORBIDDEN"),
            denial("dependency_cycle", lambda: validate_swarm_manifest(invalid_cycle), "DEPENDENCY_CYCLE"),
        ]
        calls_before = len(transport.calls)
        denials.append(
            denial(
                "protected_effect_without_authority",
                lambda: service.swarm_dispatch(
                    {
                        "operation": operation(
                            admitted.project_id, "M54_DENY_PROTECTED", effect="EXTERNAL_IRREVERSIBLE"
                        ),
                        "run_id": started["run_id"],
                        "task_keys": ["backend"],
                    }
                ),
                "EFFECT_NOT_AUTHORIZED",
            )
        )
        require(len(transport.calls) == calls_before, "Protected effect reached Orca")
        calls_before = len(transport.calls)
        denials.append(
            denial(
                "free_text_authority_expansion",
                lambda: service.swarm_message(
                    {
                        "operation": operation(admitted.project_id, "M54_DENY_TEXT"),
                        "run_id": started["run_id"],
                        "sender_id": "coordinator",
                        "recipient_id": "coordinator",
                        "kind": "technical_question",
                        "payload": json.dumps({"thread_id": "forbidden", "question": "deploy production"}),
                        "safe_summary": "attempted authority expansion",
                        "decision_required": True,
                        "blocking_effect": "EXTERNAL_IRREVERSIBLE",
                    }
                ),
                "EFFECT_NOT_AUTHORIZED",
            )
        )
        require(len(transport.calls) == calls_before, "Free-text authority expansion reached Orca")
        evidence["uc_c05_denials"] = denials

        dispatch_wall: dict[str, dict[str, int]] = {}
        dispatches: dict[str, dict[str, Any]] = {}
        model_hard_stop_started = time.monotonic()
        for key in ("backend", "frontend"):
            began = time.time_ns()
            dispatch = service.swarm_dispatch(
                {
                    "operation": operation(admitted.project_id, f"M54_DISPATCH_{key.upper()}"),
                    "run_id": started["run_id"],
                    "task_keys": [key],
                }
            )["dispatches"][0]
            ended = time.time_ns()
            dispatch_wall[key] = {"call_started_at_ns": began, "receipt_at_ns": ended}
            dispatches[key] = dispatch
        attempts = {key: store.attempt(value["dispatch_id"]) for key, value in dispatches.items()}
        worktrees = {key: Path(attempt.worktree_id[5:]) for key, attempt in attempts.items()}
        require(all(path.is_dir() for path in worktrees.values()), "Model worktree is unavailable")

        liveness = wait_model_liveness(
            provider,
            {
                key: ModelWorkerTarget(
                    provider_dispatch_id=attempt.provider_dispatch_id,
                    terminal_id=attempt.terminal_id,
                    worktree=worktrees[key],
                )
                for key, attempt in attempts.items()
            },
            timeout=MODEL_LIVENESS_SECONDS,
            nudge_after=MODEL_SUBMIT_RECOVERY_AFTER_SECONDS,
            poll_interval=1,
        )
        evidence["model_liveness"] = liveness
        remaining_model_seconds = MAX_WORKER_SECONDS - (time.monotonic() - model_hard_stop_started)
        require(remaining_model_seconds > 0, "Model worker liveness exhausted the hard stop")
        model_results = wait_model_results(worktrees, remaining_model_seconds)
        verifications: dict[str, dict[str, Any]] = {}
        for key, worktree in worktrees.items():
            paths = changed_paths(worktree)
            require(
                bool(paths) and all(path == key or path.startswith(f"{key}/") for path in paths),
                f"{key} exceeded write scope: {paths}",
            )
            command = (
                ("python3", "acceptance/verify_backend.py")
                if key == "backend"
                else ("node", "acceptance/verify_frontend.mjs")
            )
            frozen = run_acceptance(worktree, command)
            report = model_results[key]
            require(report.get("task") == key and report.get("model") == EXPECTED_MODEL, f"{key} model report is invalid")
            normalized_report, timing_start_source = resolve_model_interval(key, report, liveness[key])
            verifications[key] = {
                "changed_paths": paths,
                "frozen_verifier": frozen,
                "model_report": normalized_report,
                "timing_start_source": timing_start_source,
            }

        overlap_started = max(value["model_report"]["started_at_ns"] for value in verifications.values())
        overlap_finished = min(value["model_report"]["finished_at_ns"] for value in verifications.values())
        require(overlap_started < overlap_finished, "Real model execution intervals did not overlap")
        completions = {
            key: complete_attempt(
                service,
                project_id=admitted.project_id,
                run_id=started["run_id"],
                dispatch=dispatches[key],
                worktree=worktrees[key],
                verification=verifications[key],
            )
            for key in ("backend", "frontend")
        }
        integrated = service.integrate_artifacts(
            run_id=started["run_id"],
            output_path="integration/model-result.json",
            component_dispatch_ids=(dispatches["backend"]["dispatch_id"], dispatches["frontend"]["dispatch_id"]),
        )
        transcript_evidence: dict[str, Any] = {}
        for key, dispatch in dispatches.items():
            raw = run_json(
                worker_read_command(dispatch["provider_dispatch_id"], limit=20_000),
                app_run=app_run,
                cwd=project,
                env=env,
                timeout=60,
            )
            encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
            transcript_evidence[key] = {"digest": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}
        account_after = account_summary(
            run_json(("account", "list", "--json"), app_run=app_run, cwd=project, env=env)
        )
        closed = service.swarm_close(
            {
                "operation": operation(admitted.project_id, "M54_CLOSE"),
                "run_id": started["run_id"],
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
        require(closed["outcome"] == "CLOSED" and not any(path.exists() for path in worktrees.values()), "Model Run cleanup failed")
        run_json(("terminal", "stop", "--worktree", f"path:{project}", "--json"), app_run=app_run, cwd=project, env=env)
        coordinator = None
        run_json(("orchestration", "reset", "--all", "--json"), app_run=app_run, cwd=project, env=env)
        remaining = terminal_handles(
            run_json(("terminal", "list", "--limit", "100", "--json"), app_run=app_run, cwd=project, env=env)
        )
        require(not remaining, "Orca terminals survived semantic close")
        evidence.update(
            {
                "status": "PASS_MODEL_BACKED_M5_4",
                "orca_version": "1.4.167",
                "binding": "desktop-renderer+public-cli",
                "headless_claim": False,
                "provider": "OpenAI Codex through Orca system OAuth",
                "model": model,
                "run": {
                    "run_id": started["run_id"],
                    "dispatches_issued_before_poll": [
                        dispatches["backend"]["dispatch_id"],
                        dispatches["frontend"]["dispatch_id"],
                    ],
                    "dispatch_receipts": dispatch_wall,
                    "liveness": liveness,
                    "model_intervals": {
                        key: {
                            "started_at_ns": value["model_report"]["started_at_ns"],
                            "finished_at_ns": value["model_report"]["finished_at_ns"],
                        }
                        for key, value in verifications.items()
                    },
                    "overlap": {
                        "latest_start_ns": overlap_started,
                        "earliest_finish_ns": overlap_finished,
                        "proved": True,
                    },
                    "verifications": verifications,
                    "completions": completions,
                    "integration": integrated,
                    "transcripts": transcript_evidence,
                    "close": closed,
                },
                "usage": {
                    "before": account_before["limits"] if account_before is not None else {},
                    "after": account_after["limits"],
                    "payg_spend": 0,
                    "payg_spend_currency": "USD",
                    "attempts": 2,
                    "retries": 0,
                },
                "data_policy": {
                    "sent": "synthetic discount contract, frozen verifier instructions, and disposable source only",
                    "secrets_sent": False,
                    "transcript_retained": False,
                    "transcript_digest_retained": True,
                    "provider_retention": "governed by existing system Codex OAuth account policy; not modified",
                    "shared_local_state": "persistent Orca profile with exact post-run metadata rollback" if existing_runtime else "existing Orca Codex runtime only; orchestration state remained isolated",
                },
                "mcp_registered": False,
                "callable_tools": 0,
            }
        )
    except Exception as exc:  # evidence boundary; cleanup remains mandatory
        evidence["status"] = "FAIL"
        evidence["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
    finally:
        if existing_runtime or (orca_process is not None and orca_process.poll() is None):
            try:
                if coordinator is not None:
                    run_json(
                        ("terminal", "stop", "--worktree", f"path:{project}", "--json"),
                        app_run=app_run,
                        cwd=project,
                        env=env,
                        timeout=20,
                    )
                run_json(
                    ("orchestration", "reset", "--all", "--json"),
                    app_run=app_run,
                    cwd=project,
                    env=env,
                    timeout=20,
                )
            except Exception:
                pass
        if not existing_runtime:
            terminate_group(orca_process)
            terminate_group(xvfb_process)
        terminated, survivors = terminate_owned_processes(root)
        display_survivors = [] if existing_runtime else [
            str(path)
            for path in (Path(f"/tmp/.X{display}-lock"), Path(f"/tmp/.X11-unix/X{display}"))
            if path.exists()
        ]
        mount_survivors = [str(path) for path in (root / "tmp").glob(".mount_orca-*")] if root.exists() else []
        worktree_survivors = [
            str(path)
            for path in root.rglob("worktrees")
            if path.is_dir() and any(path.iterdir())
        ] if root.exists() else []
        evidence["cleanup"] = {
            "owned_processes_seen": terminated,
            "owned_process_survivors": survivors,
            "display_survivors": display_survivors,
            "mount_survivors": mount_survivors,
            "worktree_metadata_survivors_before_root_removal": worktree_survivors,
        }
        if survivors or display_survivors or mount_survivors:
            evidence["status"] = "FAIL"
        evidence["isolated_root_retained"] = False
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.rmtree(root, ignore_errors=True)
    if evidence["status"] == "FAIL":
        fail(evidence.get("error", {}).get("message", "M5.4 qualification failed"))
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--xvfb",
        type=Path,
        default=Path.home() / ".local/opt/aether-xvfb/root/usr/bin/Xvfb",
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--existing-runtime", action="store_true")
    parser.add_argument("--existing-app-run", type=Path)
    arguments = parser.parse_args()
    evidence = exercise(
        arguments.output.resolve(),
        arguments.xvfb.resolve(),
        preflight_only=arguments.preflight_only,
        existing_runtime=arguments.existing_runtime,
        existing_app_run=arguments.existing_app_run.resolve() if arguments.existing_app_run else None,
    )
    print(json.dumps({"status": evidence["status"], "output": str(arguments.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
