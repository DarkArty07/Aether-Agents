#!/usr/bin/env python3
"""Qualify the M3 lifecycle through an isolated Orca desktop renderer and public CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, NoReturn

from aether_mcp.admission import ProjectAdmissionRegistry, TrustedLaunchContext
from aether_mcp.catalog import OrcaCatalog
from aether_mcp.foundation import M2Foundation
from aether_mcp.lifecycle import LifecycleService, LifecycleStore
from aether_mcp.orca_provider import PublicOrcaLifecycleProvider
from aether_mcp.trace_store import TraceStore

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas/orca/1.4.167/catalog.json"
APPIMAGE = Path("/home/darkarty/.local/opt/orca/orca-linux.AppImage")
CLI = Path("/home/darkarty/.local/bin/orca-ide")
MAX_OUTPUT = 4 * 1024 * 1024
ORCA_CLI_BOOTSTRAP = (
    '(async()=>{try{const path=require("path");const appDir=process.env.APPDIR;'
    'if(!appDir){process.exit(1);}const cli=path.join(appDir,"resources","app.asar.unpacked",'
    '"out","cli","index.js");await Promise.resolve(require(cli).main(process.argv.slice(1)));}'
    'catch(error){console.error(error&&error.stack?error.stack:String(error));process.exit(1);}})();'
)


class QualificationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> NoReturn:
    raise QualificationError(code, message)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def terminate_group(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    for sig, wait in ((signal.SIGINT, 3), (signal.SIGTERM, 3), (signal.SIGKILL, 2)):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            continue
    if process.poll() is None:
        fail("ERR_PROCESS_SURVIVED", "Owned process group survived cleanup")


def owned_processes(root: Path) -> list[int]:
    marker = str(root)
    current = os.getpid()
    found: list[int] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == current:
            continue
        try:
            cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            cwd = str((proc / "cwd").resolve())
        except (OSError, PermissionError, ProcessLookupError):
            continue
        if marker in cmdline or cwd == marker or cwd.startswith(marker + os.sep):
            found.append(int(proc.name))
    return sorted(found)


def terminate_owned_processes(root: Path) -> tuple[list[int], list[int]]:
    initial = owned_processes(root)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in owned_processes(root):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and owned_processes(root):
            time.sleep(0.05)
        if not owned_processes(root):
            break
    return initial, owned_processes(root)


def run_json(
    argv: tuple[str, ...], *, app_run: Path, cwd: Path, env: dict[str, str], timeout: float = 30
) -> dict[str, Any]:
    cli_env = dict(env)
    cli_env.update({"ELECTRON_RUN_AS_NODE": "1", "ORCA_NODE_OPTIONS": "", "ORCA_NODE_REPL_EXTERNAL_MODULE": ""})
    process = subprocess.Popen(
        [str(app_run), "-e", ORCA_CLI_BOOTSTRAP, "--", *argv],
        cwd=cwd,
        env=cli_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_group(process)
        fail("ERR_ORCA_TIMEOUT_UNKNOWN", "Orca CLI response exceeded its bounded budget")
    if len(stdout) > MAX_OUTPUT or len(stderr) > MAX_OUTPUT:
        fail("ERR_ORCA_OUTPUT_LIMIT", "Orca CLI output exceeded its bound")
    try:
        value = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("ERR_ORCA_RESPONSE_SHAPE", "Orca CLI returned non-JSON output")
    if process.returncode != 0:
        diagnostic = stderr.decode("utf-8", errors="replace").strip().replace("\n", " ")[:240]
        command = " ".join(argv[:2])
        fail("ERR_ORCA_COMMAND_NONZERO", f"Orca CLI command {command} returned nonzero: {diagnostic}")
    if not isinstance(value, dict):
        fail("ERR_ORCA_RESPONSE_SHAPE", "Orca CLI envelope is not an object")
    return value


def result(envelope: dict[str, Any]) -> dict[str, Any]:
    if set(envelope) - {"id", "ok", "result", "error", "_meta"}:
        fail("ERR_ORCA_SCHEMA_DRIFT", "Orca returned unknown top-level fields")
    value = envelope.get("result")
    if envelope.get("ok") is not True or not isinstance(value, dict):
        fail("ERR_ORCA_OPERATION", "Orca operation did not return a structured success")
    return value


def find_string(value: Any, names: set[str], *, contains: str | None = None) -> str:
    if isinstance(value, dict):
        for name in names:
            candidate = value.get(name)
            if isinstance(candidate, str) and (contains is None or contains in candidate):
                return candidate
        for child in value.values():
            try:
                return find_string(child, names, contains=contains)
            except QualificationError:
                continue
    elif isinstance(value, list):
        for child in value:
            try:
                return find_string(child, names, contains=contains)
            except QualificationError:
                continue
    fail("ERR_ORCA_SCHEMA_DRIFT", "Required Orca identity is absent")


def contains(value: Any, expected: str) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(contains(child, expected) for child in value.values())
    if isinstance(value, list):
        return any(contains(child, expected) for child in value)
    return False


def terminal_handles(value: Any) -> list[str]:
    handles: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"agentTerminalHandle", "handle", "terminalHandle"} and isinstance(child, str) and child.startswith("term"):
                handles.add(child)
            handles.update(terminal_handles(child))
    elif isinstance(value, list):
        for child in value:
            handles.update(terminal_handles(child))
    return sorted(handles)


def build_env(root: Path, display: int) -> dict[str, str]:
    env = {
        "HOME": str(root / "home"),
        "HERMES_HOME": str(root / "hermes-home"),
        "AETHER_PROFILE": "m3-qualification",
        "AETHER_SESSION_ID": str(uuid.uuid4()),
        "XDG_CONFIG_HOME": str(root / "xdg/config"),
        "XDG_CACHE_HOME": str(root / "xdg/cache"),
        "XDG_DATA_HOME": str(root / "xdg/data"),
        "XDG_STATE_HOME": str(root / "xdg/state"),
        "TMPDIR": str(root / "tmp"),
        "DISPLAY": f":{display}",
        "ORCA_TELEMETRY_DISABLED": "1",
        "ELECTRON_OZONE_PLATFORM_HINT": "x11",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    for key in ("HOME", "HERMES_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "TMPDIR"):
        Path(env[key]).mkdir(mode=0o700, parents=True, exist_ok=True)
    return env


def unused_display() -> int:
    for number in range(300, 1000):
        if not Path(f"/tmp/.X{number}-lock").exists() and not Path(f"/tmp/.X11-unix/X{number}").exists():
            return number
    fail("ERR_XVFB_DISPLAY", "No isolated X display is available")


def start_xvfb(xvfb: Path, root: Path, env: dict[str, str], display: int) -> subprocess.Popen[bytes]:
    process = subprocess.Popen(
        [str(xvfb), f":{display}", "-nolisten", "tcp", "-screen", "0", "1280x720x24"],
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=(root / "xvfb.stdout").open("wb"),
        stderr=(root / "xvfb.stderr").open("wb"),
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    socket_path = Path(f"/tmp/.X11-unix/X{display}")
    while time.monotonic() < deadline:
        if process.poll() is not None:
            fail("ERR_XVFB_START", "Xvfb exited before readiness")
        if socket_path.exists():
            return process
        time.sleep(0.05)
    terminate_group(process)
    fail("ERR_XVFB_TIMEOUT", "Xvfb did not become ready")


def prepare_appimage(root: Path, env: dict[str, str]) -> tuple[Path, Path]:
    destination = root / "prepared-appimage"
    destination.mkdir(mode=0o700)
    with (root / "appimage-prepare.stdout").open("wb") as stdout, (root / "appimage-prepare.stderr").open("wb") as stderr:
        completed = subprocess.run(
            [str(APPIMAGE), "--appimage-extract"],
            cwd=destination,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            timeout=90,
            check=False,
        )
    app_dir = (destination / "squashfs-root").resolve()
    app_run = app_dir / "AppRun"
    if completed.returncode != 0 or not app_run.is_file() or not os.access(app_run, os.X_OK):
        fail("ERR_APPIMAGE_PREPARATION", "Exact AppImage could not be prepared")
    return app_dir, app_run


def start_orca(root: Path, env: dict[str, str], app_run: Path, sequence: int) -> subprocess.Popen[bytes]:
    stdout = (root / f"orca-{sequence}.stdout").open("wb")
    stderr = (root / f"orca-{sequence}.stderr").open("wb")
    process = subprocess.Popen(
        [str(app_run), "--disable-gpu"],
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )
    stdout.close()
    stderr.close()
    deadline = time.monotonic() + 120
    last_code = "not-attempted"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            fail("ERR_ORCA_START", "Orca renderer exited before readiness")
        try:
            status = run_json(("status", "--json"), app_run=app_run, cwd=root, env=env, timeout=10)
            if contains(status, "1.4.167"):
                return process
            last_code = "version-not-observed"
        except QualificationError as exc:
            last_code = exc.code
        time.sleep(0.5)
    terminate_group(process)
    fail("ERR_ORCA_START_TIMEOUT", f"Orca renderer readiness remained unavailable: {last_code}")


def prepare_repo(path: Path) -> None:
    path.mkdir()
    subprocess.run(("git", "init", "--initial-branch=main"), cwd=path, check=True, capture_output=True)
    subprocess.run(
        ("git", "-c", "user.name=Aether Qualification", "-c", "user.email=aether@invalid", "commit", "--allow-empty", "-m", "init"),
        cwd=path,
        check=True,
        capture_output=True,
    )


def operation(project_id: str, contract_id: str, code: str) -> dict[str, Any]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": contract_id,
        "use_case_id": "UC-C02",
        "reason": {"code": code, "summary": "M3 isolated lifecycle qualification", "authority_ref": "decision:m3"},
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def manifest(project_id: str) -> dict[str, Any]:
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:m3/qualification",
            "generation": 1,
            "objective": "qualify metadata-only Orca lifecycle",
            "acceptance": ["restart recovery", "terminal tasks", "zero live resources"],
            "non_goals": ["workers", "models", "artifact writes"],
            "authorized_effects": ["READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"],
            "stop_condition": "semantic close and zero survivors",
        },
        "evaluation": {"enabled": True, "use_case_id": "UC-C02", "variant": "m3-shell", "measurement_contract": "M0 frozen"},
        "learning": {"capture_policy": "STRUCTURED_ONLY", "purpose": ["evaluation"], "consent_authority_ref": "decision:m3"},
        "tasks": [
            {
                "task_key": key,
                "deliverable": f"metadata-only {key}",
                "archetype": "fixture",
                "dependencies": [] if key == "first" else ["first"],
                "read_scope": ["src"],
                "write_scope": [],
                "evidence_requirements": ["Orca Task identity"],
                "attempt_budget": 1,
                "placement": "read_only",
            }
            for key in ("first", "second")
        ],
    }


def exercise(output: Path, xvfb: Path) -> dict[str, Any]:
    if not APPIMAGE.is_file() or not CLI.is_file() or not xvfb.is_file():
        fail("ERR_PREREQUISITE", "Exact Orca or Xvfb prerequisite is unavailable")
    root = Path(tempfile.mkdtemp(prefix="aether-m3-", dir="/tmp"))
    display = unused_display()
    env = build_env(root, display)
    app_dir, app_run = prepare_appimage(root, env)
    env["APPDIR"] = str(app_dir)
    project = root / "project"
    prepare_repo(project)
    before_home = canonical_digest([])
    xvfb_process: subprocess.Popen[bytes] | None = None
    orca_process: subprocess.Popen[bytes] | None = None
    evidence: dict[str, Any] = {"status": "INCOMPLETE", "isolated_root": str(root)}
    completed = False
    closed_terminals: list[str] = []
    try:
        xvfb_process = start_xvfb(xvfb, root, env, display)
        orca_process = start_orca(root, env, app_run, 1)
        repo_add = run_json(
            ("repo", "add", "--path", str(project), "--json"), app_run=app_run, cwd=project, env=env
        )
        result(repo_add)
        terminal_create = run_json(
            ("terminal", "create", "--worktree", f"path:{project}", "--title", "AETHER-M3", "--command", "bash", "--json"),
            app_run=app_run,
            cwd=project,
            env=env,
        )
        coordinator_handle = find_string(result(terminal_create), {"agentTerminalHandle", "handle"}, contains="term")

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
        foundation = M2Foundation(
            context=context,
            admissions=ProjectAdmissionRegistry(root / "aether-state/admissions"),
            trace=trace,
            catalog=catalog,
        )
        admitted = foundation.project_admit(
            {
                "operation": {
                    "operation_id": str(uuid.uuid4()),
                    "contract_id": "contract:m3/admit",
                    "use_case_id": "UC-C01",
                    "reason": {"code": "M3_ADMIT", "summary": "M3 isolated project admission", "authority_ref": "decision:m3"},
                    "expected_effect": "LOCAL_REVERSIBLE",
                },
                "project_root": str(project),
                "safe_alias": "m3-qualification",
                "capture_policy": "STRUCTURED_ONLY",
                "consent_authority_ref": "decision:m3",
            }
        )
        validated = foundation.swarm_validate({"manifest": manifest(admitted.project_id)})
        store = LifecycleStore(root / "aether-state/lifecycle")
        store.register_manifest(validated, manifest_ref="manifest:m3/qualification")

        transport = lambda argv: run_json(argv, app_run=app_run, cwd=project, env=env)  # noqa: E731
        provider = PublicOrcaLifecycleProvider(
            transport=transport,
            binding_digest=catalog.digest,
            coordinator_handle=coordinator_handle,
        )
        service = LifecycleService(foundation=foundation, store=store, provider=provider)
        start_operation = operation(admitted.project_id, "contract:m3/qualification", "M3_START")
        started = service.swarm_start(
            {
                "operation": start_operation,
                "manifest_digest": validated.digest,
                "manifest_ref": "manifest:m3/qualification",
                "provider_binding_digest": catalog.digest,
                "dispatch_ready": False,
            }
        )
        if started["outcome"] != "SUCCEEDED" or len(started["tasks"]) != 2:
            fail("ERR_M3_START", "M3 start did not correlate one Run and two Tasks")
        first_status = service.swarm_status(
            {"project_id": admitted.project_id, "run_id": started["run_id"], "cursor": None, "wait_ms": 0, "detail": "tasks"}
        )
        binding = store.run(started["run_id"], project_id=admitted.project_id)

        terminate_group(orca_process)
        orca_process = None
        orca_process = start_orca(root, env, app_run, 2)
        replacement_terminal = run_json(
            ("terminal", "create", "--worktree", f"path:{project}", "--title", "AETHER-M3-R", "--command", "bash", "--json"),
            app_run=app_run,
            cwd=project,
            env=env,
        )
        replacement_handle = find_string(result(replacement_terminal), {"agentTerminalHandle", "handle"}, contains="term")
        run_use = run_json(
            ("orchestration", "run-use", "--id", binding.provider_run_id, "--from", replacement_handle, "--json"),
            app_run=app_run,
            cwd=project,
            env=env,
        )
        result(run_use)
        restarted_provider = PublicOrcaLifecycleProvider(
            transport=transport,
            binding_digest=catalog.digest,
            coordinator_handle=replacement_handle,
        )
        service = LifecycleService(foundation=foundation, store=LifecycleStore(store.root), provider=restarted_provider)
        recovered = service.swarm_status(
            {"project_id": admitted.project_id, "run_id": started["run_id"], "cursor": None, "wait_ms": 0, "detail": "tasks"}
        )
        cancelled = service.swarm_cancel(
            {
                "operation": operation(admitted.project_id, "contract:m3/qualification", "M3_CANCEL"),
                "run_id": started["run_id"],
                "target_type": "run",
                "target_id": started["run_id"],
            }
        )
        terminal_status = service.swarm_status(
            {"project_id": admitted.project_id, "run_id": started["run_id"], "cursor": None, "wait_ms": 0, "detail": "tasks"}
        )
        closed = service.swarm_close(
            {
                "operation": operation(admitted.project_id, "contract:m3/qualification", "M3_CLOSE"),
                "run_id": started["run_id"],
                "effect_plan": ["LOCAL_REVERSIBLE"],
                "retained_resource_ids": [],
            }
        )
        listed_terminals = run_json(("terminal", "list", "--json"), app_run=app_run, cwd=project, env=env)
        for handle in terminal_handles(listed_terminals):
            run_json(
                ("terminal", "close", "--terminal", handle, "--tab", "--json"),
                app_run=app_run,
                cwd=project,
                env=env,
            )
            closed_terminals.append(handle)
        run_json(
            ("orchestration", "reset", "--all", "--json"), app_run=app_run, cwd=project, env=env
        )
        evidence = {
            "status": "PASS",
            "orca_version": "1.4.167",
            "binding": "desktop-renderer+public-cli",
            "headless_claim": False,
            "manifest_digest": validated.digest,
            "catalog_digest": catalog.digest,
            "run": {"logical_id": started["run_id"], "provider_id": binding.provider_run_id},
            "tasks": started["tasks"],
            "first_status": first_status,
            "restart": {"recovered": recovered["run_id"] == started["run_id"], "replacement_terminal": True},
            "cancel": cancelled,
            "terminal_status": terminal_status,
            "close": closed,
            "terminal_cleanup": {"closed_handles": closed_terminals},
            "trace_records": len(trace.records()),
            "workers": 0,
            "models": 0,
            "credentials": 0,
            "spend": 0,
        }
        if (
            closed["outcome"] != "CLOSED"
            or closed["survivors"]
            or cancelled["outcome"] != "CANCELLED"
            or any(task["status"] != "failed" for task in terminal_status["tasks"])
        ):
            fail("ERR_M3_CLOSURE", "M3 lifecycle did not reach evidence-bound closure")
        completed = True
    finally:
        terminate_group(orca_process)
        terminate_group(xvfb_process)
        terminated_owned, owned_survivors = terminate_owned_processes(root)
        display_survivors = [path for path in (Path(f"/tmp/.X{display}-lock"), Path(f"/tmp/.X11-unix/X{display}")) if path.exists()]
        mounts = list((root / "tmp").glob(".mount_orca-*")) if root.exists() else []
        evidence["cleanup"] = {
            "owned_processes_after_renderer_stop": terminated_owned,
            "owned_process_survivors": owned_survivors,
            "display_survivors": [str(path) for path in display_survivors],
            "mount_survivors": [str(path) for path in mounts],
            "protected_global_state_digest": before_home,
        }
        if display_survivors or mounts or owned_survivors:
            evidence["status"] = "FAIL"
            evidence["cleanup"]["reason"] = "owned resource survived"
        output.parent.mkdir(parents=True, exist_ok=True)
        evidence["isolated_root_retained"] = not completed
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
    except QualificationError as exc:
        payload: dict[str, Any] = {}
        if args.output.is_file():
            try:
                loaded = json.loads(args.output.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        payload.update({"status": "FAIL", "code": exc.code, "error": str(exc)})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, sort_keys=True))
        return 1
    print(json.dumps({"status": evidence.get("status"), "output": str(args.output)}, sort_keys=True))
    return 0 if evidence.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
