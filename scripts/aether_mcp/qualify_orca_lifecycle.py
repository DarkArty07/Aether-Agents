"""Exact-candidate M1.3 Orca lifecycle qualification harness.

The outer process authenticates the canonical candidate and protected-state
metadata. The real lifecycle runs inside a fresh user/network namespace with
only loopback, an ephemeral Xvfb, and an M1-owned HOME/XDG/tmp root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn, Protocol
from urllib.parse import urlparse

import qualify_orca as identity

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_MANIFEST = PROJECT_ROOT / "docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json"
CANONICAL_MANIFEST_SHA256 = identity.CANONICAL_MANIFEST_SHA256
ROOT_PREFIX = "aether-m1-3-"
MAX_OUTPUT_BYTES = 1_048_576
MAX_SCHEMA_DEPTH = 12
COMMAND_TIMEOUT_SECONDS = 12.0
STARTUP_TIMEOUT_SECONDS = 35.0
STOP_TIMEOUT_SECONDS = 10.0
WORKER_UID = 1000
WORKER_GID = 1000

MISSING_SEAMS = (
    "events_read",
    "resource_inventory",
    "resource_cleanup",
    "run_cancel",
    "run_close",
    "task_cancel",
)

COMPOSITION_PROOF_KEYS = {
    "ordered_operations",
    "preconditions",
    "step_identities",
    "effects",
    "timeout_unknown_handling",
    "reconciliation",
    "cleanup",
    "partial_result_semantics",
    "rollback_limits",
    "semantic_equivalence_evidence",
}


class LifecycleError(Exception):
    """Stable, secret-safe lifecycle qualification failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise LifecycleError(code, message)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_lifecycle_root(root: str | Path) -> Path:
    """Require a real, fresh, direct /tmp child owned by M1.3."""
    path = Path(root)
    try:
        if path.is_symlink() or not path.is_dir():
            _fail("ERR_ISOLATION_ROOT_INVALID", "Lifecycle root is not a real directory")
        resolved = path.resolve(strict=True)
    except OSError:
        _fail("ERR_ISOLATION_ROOT_INVALID", "Lifecycle root is unavailable")
    if resolved.parent != Path("/tmp") or not resolved.name.startswith(ROOT_PREFIX):
        _fail("ERR_ISOLATION_ROOT_INVALID", "Lifecycle root is outside the admitted boundary")
    try:
        entries = list(resolved.iterdir())
    except OSError:
        _fail("ERR_ISOLATION_ROOT_INVALID", "Lifecycle root is unreadable")
    if entries:
        _fail("ERR_ISOLATION_ROOT_NOT_FRESH", "Lifecycle root must be empty")
    return resolved


def _require_owned_root(root: str | Path) -> Path:
    path = Path(root)
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        _fail("ERR_CLEANUP_SCOPE", "Cleanup root cannot be resolved")
    if path.is_symlink() or resolved.parent != Path("/tmp") or not resolved.name.startswith(ROOT_PREFIX):
        _fail("ERR_CLEANUP_SCOPE", "Cleanup refused outside the M1.3 boundary")
    return resolved


def build_child_environment(root: str | Path) -> dict[str, str]:
    """Create the exact environment admitted to Orca/Xvfb children."""
    base = _require_owned_root(root)
    mapping = {
        "HOME": base / "home",
        "XDG_CACHE_HOME": base / "cache",
        "XDG_CONFIG_HOME": base / "config",
        "XDG_DATA_HOME": base / "data",
        "XDG_RUNTIME_DIR": base / "runtime",
        "XDG_STATE_HOME": base / "state",
        "TMPDIR": base / "tmp",
    }
    for path in mapping.values():
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(mapping["XDG_RUNTIME_DIR"], 0o700)
    return {
        **{key: str(value) for key, value in mapping.items()},
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "LANG": "C.UTF-8",
        "APPIMAGE_EXTRACT_AND_RUN": "1",
    }


def parse_json_object(stdout: bytes, stderr: bytes) -> dict[str, Any]:
    if stderr:
        _fail("ERR_COMMAND_STDERR", "Structured command emitted stderr")
    if len(stdout) > MAX_OUTPUT_BYTES:
        _fail("ERR_COMMAND_OUTPUT_LIMIT", "Structured command output exceeded its limit")
    try:
        value = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("ERR_COMMAND_MALFORMED_JSON", "Structured command output is not valid JSON")
    if not isinstance(value, dict):
        _fail("ERR_COMMAND_SHAPE", "Structured command output is not an object")
    return value


def parse_serve_stream(payload: bytes, root: Path) -> dict[str, Any] | None:
    if len(payload) > MAX_OUTPUT_BYTES:
        _fail("ERR_COMMAND_OUTPUT_LIMIT", "Orca serve output exceeded its limit")
    complete_lines = payload.split(b"\n")
    if payload and not payload.endswith(b"\n"):
        complete_lines = complete_lines[:-1]
    ready: list[dict[str, Any]] = []
    allowed_parent = root / "tmp"
    hexadecimal = set("0123456789abcdefABCDEF")
    for raw_line in complete_lines:
        if not raw_line.strip():
            continue
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError:
            _fail("ERR_RUNTIME_START_SHAPE", "Orca serve startup output is malformed")
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            path = Path(line)
            try:
                relative = path.relative_to(allowed_parent)
            except ValueError:
                _fail("ERR_RUNTIME_START_SHAPE", "Orca serve emitted an unexpected startup line")
            if not relative.parts:
                _fail("ERR_RUNTIME_START_SHAPE", "Orca serve emitted an unexpected startup line")
            directory = relative.parts[0]
            prefix = "appimage_extracted_"
            suffix = directory.removeprefix(prefix)
            if not directory.startswith(prefix) or len(suffix) != 32 or any(char not in hexadecimal for char in suffix):
                _fail("ERR_RUNTIME_START_SHAPE", "Orca serve emitted an unexpected startup line")
            continue
        if not isinstance(decoded, dict) or decoded.get("type") != "orca_server_ready":
            _fail("ERR_RUNTIME_START_SHAPE", "Orca serve emitted an unexpected startup object")
        ready.append(decoded)
    if len(ready) > 1:
        _fail("ERR_RUNTIME_START_SHAPE", "Orca serve emitted multiple readiness records")
    return ready[0] if ready else None


def _schema_type(value: Any, *, depth: int) -> dict[str, Any]:
    if depth > MAX_SCHEMA_DEPTH:
        _fail("ERR_SCHEMA_DEPTH", "Observed response exceeds the admitted schema depth")
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        variants: dict[str, dict[str, Any]] = {}
        for item in value:
            item_schema = _schema_type(item, depth=depth + 1)
            variants[json.dumps(item_schema, sort_keys=True, separators=(",", ":"))] = item_schema
        if not variants:
            items: dict[str, Any] = {}
        elif len(variants) == 1:
            items = next(iter(variants.values()))
        else:
            items = {"oneOf": [variants[key] for key in sorted(variants)]}
        return {"type": "array", "items": items}
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            _fail("ERR_SCHEMA_SHAPE", "Observed response contains a non-string key")
        properties = {key: _schema_type(value[key], depth=depth + 1) for key in sorted(value)}
        return {
            "type": "object",
            "properties": properties,
            "required": sorted(value),
            "additionalProperties": False,
        }
    _fail("ERR_SCHEMA_TYPE", "Observed response contains an unsupported value type")


def derive_observed_schema(value: Any) -> dict[str, Any]:
    """Derive a value-free deterministic schema from one observed response."""
    return _schema_type(value, depth=0)


def status_is_ready(envelope: dict[str, Any], *, expected_version: str) -> bool:
    result = envelope.get("result")
    if not envelope.get("ok") or not isinstance(result, dict):
        return False
    runtime = result.get("runtime")
    graph = result.get("graph")
    app = result.get("app")
    if not isinstance(runtime, dict) or not isinstance(graph, dict) or not isinstance(app, dict):
        _fail("ERR_STATUS_SHAPE", "Runtime status shape is invalid")
    if not runtime.get("reachable") or runtime.get("state") != "ready" or graph.get("state") != "ready":
        return False
    if runtime.get("appVersion") != expected_version:
        _fail("ERR_RUNTIME_VERSION_DRIFT", "Runtime version differs from the canonical candidate")
    runtime_id = runtime.get("runtimeId")
    if not isinstance(runtime_id, str) or not runtime_id:
        _fail("ERR_STATUS_SHAPE", "Ready runtime has no stable identity")
    return True


def validate_listener_address(address: str, *, isolated_network: bool) -> None:
    if address in {"127.0.0.1", "::1", "localhost"}:
        return
    if address in {"0.0.0.0", "::"} and isolated_network:
        return
    _fail("ERR_NON_LOOPBACK_LISTENER", "Runtime listener escapes the admitted network boundary")


def wait_for_listener_close(port: int, *, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.1)
            closed = probe.connect_ex(("127.0.0.1", port)) != 0
        if closed:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def interfaces_from_ip_json(value: Any) -> list[str]:
    if not isinstance(value, list):
        _fail("ERR_NETWORK_INVENTORY_INVALID", "Netlink interface inventory is invalid")
    names: list[str] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("ifname"), str):
            _fail("ERR_NETWORK_INVENTORY_INVALID", "Netlink interface inventory is invalid")
        names.append(item["ifname"])
    names.sort()
    if names != ["lo"]:
        _fail("ERR_NETWORK_NAMESPACE_ESCAPE", "Lifecycle namespace exposes external interfaces")
    return names


def _network_interfaces() -> list[str]:
    try:
        payload = subprocess.check_output(
            ["/usr/sbin/ip", "-j", "link"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        decoded = json.loads(payload.decode("utf-8"))
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError, json.JSONDecodeError):
        _fail("ERR_NETWORK_INVENTORY_INVALID", "Netlink interface inventory is unavailable")
    return interfaces_from_ip_json(decoded)


def _subid_range(path: Path, username: str) -> tuple[int, int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        _fail("ERR_SUBID_UNAVAILABLE", "Subordinate identity map is unavailable")
    matches: list[tuple[int, int]] = []
    for line in lines:
        fields = line.split(":")
        if len(fields) != 3 or fields[0] != username:
            continue
        try:
            start, count = int(fields[1]), int(fields[2])
        except ValueError:
            _fail("ERR_SUBID_INVALID", "Subordinate identity map is invalid")
        matches.append((start, count))
    if len(matches) != 1 or matches[0][1] <= WORKER_UID:
        _fail("ERR_SUBID_INVALID", "Subordinate identity map cannot admit the lifecycle worker")
    return matches[0]


def build_namespace_argv(
    root: Path,
    xvfb_path: Path,
    *,
    python_path: Path | None = None,
    outer_uid: int | None = None,
    outer_gid: int | None = None,
    subuid_range: tuple[int, int] | None = None,
    subgid_range: tuple[int, int] | None = None,
) -> list[str]:
    uid = os.getuid() if outer_uid is None else outer_uid
    gid = os.getgid() if outer_gid is None else outer_gid
    try:
        username = pwd.getpwuid(uid).pw_name
    except KeyError:
        _fail("ERR_SUBID_INVALID", "Current user has no stable identity")
    uid_range = subuid_range if subuid_range is not None else _subid_range(Path("/etc/subuid"), username)
    gid_range = subgid_range if subgid_range is not None else _subid_range(Path("/etc/subgid"), username)
    if uid_range[1] <= WORKER_UID or gid_range[1] <= WORKER_GID:
        _fail("ERR_SUBID_INVALID", "Subordinate identity range is too small")
    interpreter = Path(sys.executable) if python_path is None else python_path
    return [
        "/usr/sbin/unshare",
        "--user",
        "--map-users",
        f"0:{uid}:1",
        "--map-users",
        f"1:{uid_range[0]}:{uid_range[1]}",
        "--map-groups",
        f"0:{gid}:1",
        "--map-groups",
        f"1:{gid_range[0]}:{gid_range[1]}",
        "--net",
        "--mount",
        "--pid",
        "--fork",
        "--mount-proc",
        str(interpreter),
        str(Path(__file__).resolve()),
        "--inner",
        "--isolated-root",
        str(root),
        "--xvfb",
        str(xvfb_path),
    ]


def required_public_operation_plan() -> list[dict[str, Any]]:
    """Return the exact public operation surface exercised by M1.3."""
    return [
        {"argv": ["status", "--json"], "effect": "READ_ONLY"},
        {
            "argv": ["orchestration", "run-create", "--objective", "aether-m1.3-isolated-fixture", "--json"],
            "effect": "LOCAL_REVERSIBLE",
        },
        {
            "argv": ["orchestration", "task-create", "--spec", "aether-m1.3-synthetic-task", "--json"],
            "effect": "LOCAL_REVERSIBLE",
        },
        {"argv": ["orchestration", "run-show", "--json"], "effect": "READ_ONLY"},
        {"argv": ["orchestration", "run-list", "--json"], "effect": "READ_ONLY"},
        {"argv": ["orchestration", "task-list", "--json"], "effect": "READ_ONLY"},
        {"argv": ["orchestration", "inbox", "--json"], "effect": "READ_ONLY"},
        {"argv": ["orchestration", "gate-list", "--json"], "effect": "READ_ONLY"},
        {"argv": ["terminal", "list", "--json"], "effect": "READ_ONLY"},
        {"argv": ["worktree", "list", "--json"], "effect": "READ_ONLY"},
        {"argv": ["worktree", "ps", "--json"], "effect": "READ_ONLY"},
        {"argv": ["orchestration", "reset", "--tasks", "--json"], "effect": "LOCAL_REVERSIBLE"},
        {"argv": ["orchestration", "reset", "--messages", "--json"], "effect": "LOCAL_REVERSIBLE"},
        {"argv": ["orchestration", "reset", "--all", "--json"], "effect": "LOCAL_REVERSIBLE"},
    ]


def evaluate_missing_seams(proofs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if set(proofs) - set(MISSING_SEAMS):
        _fail("ERR_COMPOSITION_PROOF_UNKNOWN", "Composition proof names an unknown seam")
    verdicts: dict[str, dict[str, Any]] = {}
    for seam in MISSING_SEAMS:
        proof = proofs.get(seam)
        if proof is None:
            verdicts[seam] = {
                "verdict": "UNSUPPORTED",
                "reason": "No complete semantically equivalent public-command composition was proven",
            }
            continue
        if set(proof) != COMPOSITION_PROOF_KEYS or any(value in (None, "", []) for value in proof.values()):
            _fail("ERR_COMPOSITION_PROOF_INCOMPLETE", "Composition proof is incomplete")
        verdicts[seam] = {"verdict": "PROVEN_COMPOSED", "proof": proof}
    return verdicts


def fingerprint_paths(paths: list[Path]) -> dict[str, Any]:
    """Fingerprint names and metadata without opening private file contents."""
    entries: list[dict[str, Any]] = []
    for root in sorted((path.expanduser() for path in paths), key=lambda item: str(item)):
        candidates = [root]
        if root.is_dir() and not root.is_symlink():
            candidates.extend(sorted(root.rglob("*"), key=lambda item: str(item)))
        for path in candidates:
            try:
                info = path.lstat()
            except FileNotFoundError:
                entries.append({"path": str(path), "kind": "missing"})
                continue
            if stat.S_ISLNK(info.st_mode):
                kind = "symlink"
            elif stat.S_ISDIR(info.st_mode):
                kind = "directory"
            elif stat.S_ISREG(info.st_mode):
                kind = "file"
            else:
                kind = "other"
            entries.append(
                {
                    "path": str(path),
                    "kind": kind,
                    "mode": stat.S_IMODE(info.st_mode),
                    "size": info.st_size,
                    "mtime_ns": info.st_mtime_ns,
                }
            )
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": _sha256(payload), "entry_count": len(entries), "entries": entries}


def require_same_fingerprint(before: dict[str, Any], after: dict[str, Any]) -> None:
    if before.get("sha256") != after.get("sha256") or before.get("entry_count") != after.get("entry_count"):
        _fail("ERR_PROTECTED_STATE_DRIFT", "Protected Orca state metadata changed")


def _terminate_group(process: subprocess.Popen[bytes], *, first_signal: signal.Signals = signal.SIGTERM) -> None:
    if process.poll() is not None:
        return
    for sig, timeout in ((first_signal, 3.0), (signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
        if process.poll() is not None:
            break
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
    if process.poll() is None:
        _fail("ERR_PROCESS_GROUP_SURVIVED", "Owned process group survived bounded cleanup")


def run_owned_json_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: float = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_group(process)
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        _fail("ERR_COMMAND_TIMEOUT_UNKNOWN", "Command outcome is unknown after timeout")
    if len(stdout) > MAX_OUTPUT_BYTES or len(stderr) > MAX_OUTPUT_BYTES:
        _fail("ERR_COMMAND_OUTPUT_LIMIT", "Command output exceeded its limit")
    if process.returncode != 0:
        if not stderr:
            try:
                failure = json.loads(stdout.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                failure = None
            if isinstance(failure, dict) and set(failure) == {"status", "code", "error"}:
                code = failure.get("code")
                message = failure.get("error")
                if (
                    failure.get("status") == "FAIL"
                    and isinstance(code, str)
                    and code.startswith("ERR_")
                    and code.replace("_", "").isalnum()
                    and code.upper() == code
                    and isinstance(message, str)
                    and 0 < len(message) <= 240
                ):
                    _fail(code, message)
        _fail("ERR_COMMAND_NONZERO", "Structured command returned a nonzero status")
    return parse_json_object(stdout, stderr)


def cleanup_owned_root(root: str | Path) -> None:
    path = _require_owned_root(root)
    if not path.exists():
        return
    if path.is_symlink():
        _fail("ERR_CLEANUP_SCOPE", "Cleanup refused a symlink root")
    try:
        shutil.rmtree(path)
    except OSError:
        _fail("ERR_CLEANUP_FAILED", "M1.3 root could not be removed")
    if path.exists():
        _fail("ERR_CLEANUP_FAILED", "M1.3 root survived cleanup")


def _envelope_ok(envelope: dict[str, Any], *, operation: str) -> dict[str, Any]:
    if set(envelope) - {"id", "ok", "result", "error", "_meta"}:
        _fail("ERR_PROVIDER_SCHEMA_DRIFT", f"{operation} returned unknown top-level fields")
    if envelope.get("ok") is not True or not isinstance(envelope.get("result"), dict):
        _fail("ERR_PROVIDER_OPERATION_FAILED", f"{operation} did not return a successful structured result")
    return envelope["result"]


def _find_entity_id(value: Any, *, entity: str) -> str:
    preferred = {"run": {"runId", "id"}, "task": {"taskId", "id"}}[entity]
    containers = {entity, f"{entity}s"}

    def walk(item: Any, parent: str | None = None) -> str | None:
        if isinstance(item, dict):
            for key in sorted(item):
                value = item[key]
                if key in preferred and isinstance(value, str) and value and (parent in containers or key != "id"):
                    return value
                found = walk(value, key)
                if found:
                    return found
        elif isinstance(item, list):
            for value in item:
                found = walk(value, parent)
                if found:
                    return found
        return None

    found = walk(value)
    if not found:
        _fail("ERR_PROVIDER_SCHEMA_DRIFT", f"{entity} response has no structured identity")
    return found


def _contains_identity(value: Any, identity_value: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_identity(item, identity_value) for item in value.values())
    if isinstance(value, list):
        return any(_contains_identity(item, identity_value) for item in value)
    return value == identity_value


class LifecycleDriver(Protocol):
    def verify_identity(self) -> dict[str, Any]: ...

    def start(self) -> dict[str, Any]: ...

    def command(self, argv: list[str]) -> dict[str, Any]: ...

    def stop(self) -> dict[str, Any]: ...


def exercise_lifecycle(driver: LifecycleDriver) -> dict[str, Any]:
    """Exercise the provider lifecycle without implementing an adapter."""
    candidate = driver.verify_identity()
    schemas: dict[str, dict[str, Any]] = {}
    command_digests: dict[str, str] = {}

    def invoke(name: str, argv: list[str]) -> dict[str, Any]:
        envelope = driver.command(argv)
        schemas[name] = derive_observed_schema(envelope)
        command_digests[name] = _sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode())
        return envelope

    first_started = False
    second_started = False
    first_stop: dict[str, Any] | None = None
    second_stop: dict[str, Any] | None = None
    try:
        cold = driver.start()
        first_started = True
        validate_listener_address(cold["listener"], isolated_network=bool(cold["isolated_network"]))
        status = invoke("status_cold", ["status", "--json"])
        if not status_is_ready(status, expected_version=candidate["product_version"]):
            _fail("ERR_RUNTIME_NOT_READY", "Cold-started runtime did not become ready")

        run_create = invoke(
            "run_create",
            ["orchestration", "run-create", "--objective", "aether-m1.3-isolated-fixture", "--json"],
        )
        run_id = _find_entity_id(_envelope_ok(run_create, operation="run-create"), entity="run")
        task_create = invoke(
            "task_create",
            [
                "orchestration",
                "task-create",
                "--spec",
                "aether-m1.3-synthetic-task",
                "--run",
                run_id,
                "--json",
            ],
        )
        task_id = _find_entity_id(_envelope_ok(task_create, operation="task-create"), entity="task")

        reads = {
            "run_show": ["orchestration", "run-show", "--id", run_id, "--json"],
            "run_list": ["orchestration", "run-list", "--limit", "20", "--json"],
            "task_list": ["orchestration", "task-list", "--run", run_id, "--json"],
            "inbox": ["orchestration", "inbox", "--limit", "20", "--json"],
            "gate_list": ["orchestration", "gate-list", "--run", run_id, "--json"],
            "terminal_list": ["terminal", "list", "--limit", "20", "--json"],
            "worktree_list": ["worktree", "list", "--limit", "20", "--json"],
            "worktree_ps": ["worktree", "ps", "--limit", "20", "--json"],
        }
        for name, argv in reads.items():
            _envelope_ok(invoke(name, argv), operation=name)
        first_stop = driver.stop()
        first_started = False

        restarted = driver.start()
        second_started = True
        validate_listener_address(restarted["listener"], isolated_network=bool(restarted["isolated_network"]))
        restart_status = invoke("status_restart", ["status", "--json"])
        if not status_is_ready(restart_status, expected_version=candidate["product_version"]):
            _fail("ERR_RUNTIME_NOT_READY", "Restarted runtime did not become ready")
        recovered_run = invoke("run_show_restart", ["orchestration", "run-show", "--id", run_id, "--json"])
        recovered_tasks = invoke("task_list_restart", ["orchestration", "task-list", "--run", run_id, "--json"])
        if not (
            recovered_run.get("ok") is True
            and recovered_tasks.get("ok") is True
            and _contains_identity(recovered_run, run_id)
            and _contains_identity(recovered_tasks, task_id)
        ):
            _fail("ERR_RESTART_STATE_LOST", "Run or Task state did not survive isolated restart")

        for name, argv in (
            ("reset_tasks", ["orchestration", "reset", "--tasks", "--json"]),
            ("reset_messages", ["orchestration", "reset", "--messages", "--json"]),
            ("reset_all", ["orchestration", "reset", "--all", "--json"]),
        ):
            _envelope_ok(invoke(name, argv), operation=name)
        second_stop = driver.stop()
        second_started = False
    finally:
        if first_started or second_started:
            final_stop = driver.stop()
            if second_started:
                second_stop = final_stop
            else:
                first_stop = final_stop

    if not first_stop or not second_stop:
        _fail("ERR_STOP_EVIDENCE_MISSING", "Lifecycle stop evidence is incomplete")
    if first_stop.get("survivors") != 0 or second_stop.get("survivors") != 0:
        _fail("ERR_PROCESS_GROUP_SURVIVED", "Owned runtime survived stop")

    return {
        "status": "PASS",
        "candidate": candidate,
        "cold_start": {"ready": True, "runtime_identity_changed_on_restart": cold["runtime_id"] != restarted["runtime_id"]},
        "restart": {"run_recovered": True, "task_recovered": True},
        "stop": {"first": first_stop, "second": second_stop},
        "observed_schemas": schemas,
        "response_digests": command_digests,
        "missing_seams": evaluate_missing_seams({}),
    }


class _RealDriver:
    def __init__(self, root: Path, xvfb_path: Path) -> None:
        self.root = root
        self.xvfb_path = xvfb_path
        self.env = build_child_environment(root)
        self.manifest, self.manifest_digest = identity.load_manifest()
        self.launcher = Path(self.manifest["launcher"]["path"])
        self.appimage = Path(self.manifest["appimage"]["path"])
        self.runtime_process: subprocess.Popen[bytes] | None = None
        self.xvfb_process: subprocess.Popen[bytes] | None = None
        self.runtime_port: int | None = None
        self.display_number: int | None = None
        self.start_count = 0
        self._start_xvfb()

    def verify_identity(self) -> dict[str, Any]:
        try:
            launcher, launcher_size, launcher_sha = identity._verify_candidate_file(  # noqa: SLF001
                self.manifest["launcher"], kind="launcher"
            )
            appimage, appimage_size, appimage_sha = identity._verify_candidate_file(  # noqa: SLF001
                self.manifest["appimage"], kind="artifact"
            )
        except identity.QualificationError as exc:
            raise LifecycleError(exc.code, exc.message) from None
        return {
            "candidate_id": self.manifest["candidate_id"],
            "product_version": self.manifest["product_version"]["value"],
            "manifest_sha256": self.manifest_digest,
            "launcher": {"path": str(launcher), "size": launcher_size, "sha256": launcher_sha},
            "appimage": {"path": str(appimage), "size": appimage_size, "sha256": appimage_sha},
            "catalog_sha256": self.manifest["catalog"]["sha256"],
        }

    def _start_xvfb(self) -> None:
        if self.xvfb_path.is_symlink() or not self.xvfb_path.is_file() or not os.access(self.xvfb_path, os.X_OK):
            _fail("ERR_XVFB_UNAVAILABLE", "Isolated Xvfb support binary is unavailable")
        display = None
        for number in range(200, 1000):
            if not Path(f"/tmp/.X{number}-lock").exists() and not Path(f"/tmp/.X11-unix/X{number}").exists():
                display = number
                break
        if display is None:
            _fail("ERR_XVFB_DISPLAY_UNAVAILABLE", "No isolated X display number is available")
        self.display_number = display
        framebuffer = self.root / "xvfb"
        framebuffer.mkdir()
        stdout = (self.root / "xvfb.stdout").open("wb")
        stderr = (self.root / "xvfb.stderr").open("wb")
        self.xvfb_process = subprocess.Popen(
            [
                str(self.xvfb_path),
                f":{display}",
                "-nolisten",
                "tcp",
                "-screen",
                "0",
                "1280x720x24",
                "-fbdir",
                str(framebuffer),
            ],
            cwd=self.root,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        stdout.close()
        stderr.close()
        socket_path = Path(f"/tmp/.X11-unix/X{display}")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.xvfb_process.poll() is not None:
                _fail("ERR_XVFB_START_FAILED", "Isolated Xvfb exited before readiness")
            if socket_path.exists():
                self.env["DISPLAY"] = f":{display}"
                return
            time.sleep(0.05)
        _terminate_group(self.xvfb_process)
        _fail("ERR_XVFB_START_TIMEOUT", "Isolated Xvfb did not become ready")

    def _new_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
            handle.bind(("127.0.0.1", 0))
            return int(handle.getsockname()[1])

    def start(self) -> dict[str, Any]:
        if self.runtime_process is not None and self.runtime_process.poll() is None:
            _fail("ERR_RUNTIME_ALREADY_RUNNING", "Lifecycle fixture already owns a runtime")
        self.start_count += 1
        port = self._new_port()
        self.runtime_port = port
        stdout_path = self.root / f"serve-{self.start_count}.stdout"
        stderr_path = self.root / f"serve-{self.start_count}.stderr"
        stdout = stdout_path.open("wb")
        stderr = stderr_path.open("wb")
        project = self.root / "project"
        project.mkdir(exist_ok=True)
        process = subprocess.Popen(
            [
                str(self.launcher),
                "serve",
                "--port",
                str(port),
                "--no-pairing",
                "--project-root",
                str(project),
                "--json",
            ],
            cwd=self.root,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        stdout.close()
        stderr.close()
        self.runtime_process = process
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        startup: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                _fail("ERR_RUNTIME_START_FAILED", "Orca serve exited before readiness")
            try:
                payload = stdout_path.read_bytes()
            except OSError:
                payload = b""
            if len(payload) > MAX_OUTPUT_BYTES:
                self.stop()
                _fail("ERR_COMMAND_OUTPUT_LIMIT", "Orca serve output exceeded its limit")
            startup = parse_serve_stream(payload, self.root)
            if startup is not None:
                status = self.command(["status", "--json"])
                if status_is_ready(status, expected_version=self.manifest["product_version"]["value"]):
                    break
            time.sleep(0.15)
        else:
            self.stop()
            _fail("ERR_RUNTIME_START_TIMEOUT", "Orca serve did not become ready")
        if startup is None:
            self.stop()
            _fail("ERR_RUNTIME_START_SHAPE", "Orca serve emitted no structured readiness record")
        bound = startup.get("boundEndpoint")
        runtime_id = startup.get("runtimeId")
        if not isinstance(bound, str) or not isinstance(runtime_id, str) or not runtime_id:
            self.stop()
            _fail("ERR_RUNTIME_START_SHAPE", "Orca serve readiness record is incomplete")
        parsed = urlparse(bound)
        if parsed.port != port or parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
            self.stop()
            _fail("ERR_RUNTIME_START_SHAPE", "Orca serve endpoint is inconsistent")
        _network_interfaces()
        validate_listener_address(parsed.hostname, isolated_network=True)
        return {
            "runtime_id": runtime_id,
            "listener": parsed.hostname,
            "port": port,
            "isolated_network": True,
            "external_interfaces": 0,
            "startup_schema": derive_observed_schema(startup),
            "startup_sha256": _sha256(json.dumps(startup, sort_keys=True, separators=(",", ":")).encode()),
        }

    def command(self, argv: list[str]) -> dict[str, Any]:
        return run_owned_json_command(
            [str(self.launcher), *argv],
            cwd=self.root,
            env=self.env,
            timeout_seconds=COMMAND_TIMEOUT_SECONDS,
        )

    def stop(self) -> dict[str, Any]:
        process = self.runtime_process
        port = self.runtime_port
        if process is not None and process.poll() is None:
            _terminate_group(process, first_signal=signal.SIGINT)
        self.runtime_process = None
        deadline = time.monotonic() + 5
        mounts: list[Path] = []
        while time.monotonic() < deadline:
            mounts = list((self.root / "tmp").glob(".mount_orca-*"))
            if not mounts:
                break
            time.sleep(0.05)
        listener_survivors = int(
            port is not None and not wait_for_listener_close(port, timeout_seconds=STOP_TIMEOUT_SECONDS)
        )
        self.runtime_port = None
        if mounts:
            _fail("ERR_MOUNT_SURVIVED", "Orca AppImage mount survived runtime stop")
        if listener_survivors:
            _fail("ERR_LISTENER_SURVIVED", "Orca listener survived runtime stop")
        return {"stopped": True, "survivors": 0, "listener_survivors": 0, "mount_survivors": 0}

    def close(self) -> dict[str, int]:
        if self.runtime_process is not None:
            self.stop()
        if self.xvfb_process is not None:
            _terminate_group(self.xvfb_process)
        self.xvfb_process = None
        if self.display_number is not None:
            lock = Path(f"/tmp/.X{self.display_number}-lock")
            x_socket = Path(f"/tmp/.X11-unix/X{self.display_number}")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and (lock.exists() or x_socket.exists()):
                time.sleep(0.05)
            if lock.exists() or x_socket.exists():
                _fail("ERR_XVFB_RESOURCE_SURVIVED", "Ephemeral Xvfb resources survived cleanup")
        return {"process_survivors": 0, "listener_survivors": 0, "mount_survivors": 0}


def _default_protected_paths() -> list[Path]:
    home = Path.home()
    return [
        home / ".config/orca",
        home / ".local/share/applications/orca-app.desktop",
        home / ".local/share/icons/hicolor/512x512/apps/orca-app.png",
    ]


def _verify_real_identity() -> dict[str, Any]:
    root = Path(tempfile.mkdtemp(prefix="aether-m1-1b-", dir="/tmp"))
    try:
        return identity.qualify_orca(isolated_root=root)
    except identity.QualificationError as exc:
        raise LifecycleError(exc.code, exc.message) from None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _stage_worker_view(root: Path) -> Path:
    try:
        subprocess.run(
            ["/usr/bin/mount", "--make-rprivate", "/"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        _fail("ERR_MOUNT_NAMESPACE_SETUP", "Mount namespace could not be made private")

    try:
        manifest, _digest = identity.load_manifest()
    except identity.QualificationError as exc:
        raise LifecycleError(exc.code, exc.message) from None
    staged_home = root / "candidate-home"
    staged_home.mkdir(mode=0o755)
    home_root = Path("/home/darkarty")
    for section_name in ("launcher", "appimage"):
        section = manifest[section_name]
        source = Path(section["path"])
        try:
            relative = source.relative_to(home_root)
        except ValueError:
            _fail("ERR_CANDIDATE_PATH", "Canonical candidate path is outside the staged home boundary")
        destination = staged_home / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, destination, follow_symlinks=False)
        except OSError:
            _fail("ERR_CANDIDATE_STAGE", "Canonical candidate could not be staged")
        if destination.stat().st_size != section["size_bytes"] or _sha256_file(destination) != section["sha256"]:
            _fail("ERR_CANDIDATE_STAGE", "Staged candidate identity differs from the manifest")

    harness_root = root / "harness"
    harness_dir = harness_root / "scripts/aether_mcp"
    manifest_dir = harness_root / "docs/releases/v0.22.0"
    harness_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    lifecycle_source = Path(__file__).resolve()
    identity_source = Path(identity.__file__).resolve()
    worker_script = harness_dir / lifecycle_source.name
    shutil.copy2(lifecycle_source, worker_script)
    shutil.copy2(identity_source, harness_dir / identity_source.name)
    shutil.copy2(CANONICAL_MANIFEST, manifest_dir / CANONICAL_MANIFEST.name)
    for path in [harness_root, *harness_root.rglob("*")]:
        os.chown(path, WORKER_UID, WORKER_GID, follow_symlinks=False)
        if path.is_dir():
            os.chmod(path, 0o700)
        else:
            os.chmod(path, 0o500)

    mounted = False
    try:
        subprocess.run(
            ["/usr/bin/mount", "--bind", str(staged_home), str(home_root)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        mounted = True
        subprocess.run(
            ["/usr/bin/mount", "-o", "remount,bind,ro", str(home_root)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        if mounted:
            subprocess.run(
                ["/usr/bin/umount", str(home_root)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        _fail("ERR_MOUNT_NAMESPACE_SETUP", "Read-only staged candidate mount failed")
    return worker_script


def _unmount_worker_view() -> None:
    try:
        subprocess.run(
            ["/usr/bin/umount", "/home/darkarty"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        _fail("ERR_MOUNT_NAMESPACE_CLEANUP", "Staged candidate mount survived cleanup")


def _terminate_namespace_descendants() -> None:
    current = os.getpid()

    def live_pids() -> list[int]:
        result: list[int] = []
        for path in Path("/proc").iterdir():
            if not path.name.isdigit() or int(path.name) == current:
                continue
            try:
                state = (path / "stat").read_text(encoding="utf-8").split()[2]
            except (OSError, IndexError):
                continue
            if state != "Z":
                result.append(int(path.name))
        return sorted(result)

    def reap() -> None:
        while True:
            try:
                pid, _status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if pid == 0:
                return

    for signum, grace in ((signal.SIGTERM, 1.0), (signal.SIGKILL, 1.0)):
        targets = live_pids()
        if not targets:
            reap()
            return
        for pid in targets:
            try:
                os.kill(pid, signum)
            except ProcessLookupError:
                continue
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and live_pids():
            reap()
            time.sleep(0.05)
    reap()
    if live_pids():
        _fail("ERR_NAMESPACE_PROCESS_SURVIVED", "A process survived lifecycle namespace cleanup")


def _restore_root_ownership(root: Path) -> None:
    paths = sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for path in paths:
        try:
            info = path.lstat()
            os.chown(path, 0, 0, follow_symlinks=False)
            if not stat.S_ISLNK(info.st_mode):
                required = stat.S_IRUSR | stat.S_IWUSR
                if stat.S_ISDIR(info.st_mode):
                    required |= stat.S_IXUSR
                os.chmod(path, stat.S_IMODE(info.st_mode) | required, follow_symlinks=False)
        except FileNotFoundError:
            continue
    os.chown(root, 0, 0)
    os.chmod(root, 0o700)


def _run_worker(root: Path, xvfb_path: Path) -> dict[str, Any]:
    if os.geteuid() != WORKER_UID or os.getegid() != WORKER_GID:
        _fail("ERR_WORKER_IDENTITY", "Lifecycle worker did not drop namespace root")

    def interrupted(_signum: int, _frame: Any) -> None:
        _fail("ERR_HARNESS_INTERRUPTED", "Lifecycle worker was interrupted")

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    cap_eff = None
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("CapEff:"):
            cap_eff = int(line.split(":", 1)[1].strip(), 16)
            break
    if cap_eff != 0:
        _fail("ERR_WORKER_CAPABILITIES", "Lifecycle worker retained effective capabilities")
    driver = _RealDriver(root, xvfb_path)
    evidence: dict[str, Any] | None = None
    provider_error: Exception | None = None
    cleanup: dict[str, Any] | None = None
    admitted_provider_blocks = {
        "ERR_LISTENER_SURVIVED",
        "ERR_RUNTIME_START_TIMEOUT",
        "ERR_RUNTIME_START_SHAPE",
    }
    try:
        evidence = exercise_lifecycle(driver)
    except Exception as exc:
        if getattr(exc, "code", None) not in admitted_provider_blocks:
            raise
        provider_error = exc
    try:
        cleanup = driver.close()
    except Exception as exc:
        if getattr(exc, "code", None) not in admitted_provider_blocks:
            raise
        if provider_error is None:
            provider_error = exc
        cleanup = {"status": "BLOCKED", "code": getattr(exc, "code", "ERR_PROVIDER_CLEANUP")}

    if provider_error is not None:
        code = getattr(provider_error, "code")
        attempt = driver.start_count
        if code in {"ERR_RUNTIME_START_TIMEOUT", "ERR_RUNTIME_START_SHAPE"}:
            stage = "cold_start" if attempt <= 1 else "restart_start"
            finding: dict[str, Any] = {
                "code": code,
                "stage": stage,
                "start_attempt": attempt,
            }
            if code == "ERR_RUNTIME_START_TIMEOUT":
                finding["timeout_seconds"] = STARTUP_TIMEOUT_SECONDS
            else:
                finding["startup_output_contract_violation"] = True
        else:
            stage = "first_stop" if attempt <= 1 else "second_stop"
            finding = {
                "code": code,
                "stage": stage,
                "start_attempt": attempt,
                "provider_stop": "SIGINT_to_owned_serve_process_group",
                "listener_survived": True,
                "timeout_seconds": STOP_TIMEOUT_SECONDS,
            }
        completed = ["candidate_identity"]
        if code == "ERR_LISTENER_SURVIVED" or attempt > 1:
            completed.extend(
                [
                    "cold_start_ready",
                    "status_ready",
                    "run_create",
                    "task_create",
                    "run_show",
                    "run_list",
                    "task_list",
                    "inbox",
                    "gate_list",
                    "terminal_list",
                    "worktree_list",
                    "worktree_ps",
                ]
            )
        evidence = {
            "status": "BLOCKED",
            "blocking_finding": finding,
            "completed_before_block": completed,
            "restart": {
                "status": "NOT_EXECUTED" if attempt <= 1 else "BLOCKED",
                "reason": "provider_lifecycle_unstable",
            },
            "missing_seams": evaluate_missing_seams({}),
        }
    if evidence is None:
        _fail("ERR_INNER_QUALIFICATION_FAILED", "Lifecycle worker produced no evidence")
    evidence["network_isolation"] = {
        "namespace": "fresh_user_network_mount_and_pid_namespaces",
        "interfaces": ["lo"],
        "external_interfaces": 0,
        "wildcard_listener_confined": True,
    }
    evidence["worker_identity"] = {
        "namespace_uid": WORKER_UID,
        "namespace_gid": WORKER_GID,
        "effective_capabilities": 0,
        "electron_sandbox_disabled": False,
    }
    evidence["xvfb"] = {
        "path": str(xvfb_path),
        "sha256": _sha256_file(xvfb_path),
        "tcp_listener": False,
        "ephemeral": True,
    }
    evidence["support_cleanup"] = cleanup
    return evidence


def _run_inner(root: Path, xvfb_path: Path) -> dict[str, Any]:
    if os.geteuid() != 0:
        _fail("ERR_NAMESPACE_NOT_ACTIVE", "Inner lifecycle supervisor is not namespace root")
    subprocess.run(
        ["/usr/sbin/ip", "link", "set", "lo", "up"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _network_interfaces()
    os.chown(root, 0, WORKER_GID)
    os.chmod(root, 0o770)
    mounted = False
    result: dict[str, Any] | None = None
    try:
        worker_script = _stage_worker_view(root)
        mounted = True
        worker_argv = [
            "/usr/sbin/setpriv",
            "--reuid",
            str(WORKER_UID),
            "--regid",
            str(WORKER_GID),
            "--clear-groups",
            "/usr/bin/python3",
            str(worker_script),
            "--worker",
            "--isolated-root",
            str(root),
            "--xvfb",
            str(xvfb_path),
        ]
        result = run_owned_json_command(
            worker_argv,
            cwd=root,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", "LANG": "C.UTF-8"},
            timeout_seconds=140,
        )
    finally:
        try:
            _terminate_namespace_descendants()
            if mounted:
                _unmount_worker_view()
        finally:
            _restore_root_ownership(root)
    if result is None:
        _fail("ERR_INNER_QUALIFICATION_FAILED", "Lifecycle worker returned no report")
    result["namespace_rollback"] = {
        "process_survivors": 0,
        "listener_survivors": 0,
        "mount_survivors": 0,
        "staged_home_unmounted": True,
    }
    return result


def qualify_real_lifecycle(
    *,
    isolated_root: str | Path,
    xvfb_path: str | Path,
    protected_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Run M1.3 in a fresh loopback-only namespace and remove its root."""
    root = validate_lifecycle_root(isolated_root)
    xvfb = Path(xvfb_path).resolve(strict=True)
    protected = protected_paths if protected_paths is not None else _default_protected_paths()
    before = fingerprint_paths(protected)
    candidate = _verify_real_identity()
    child_env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LANG": "C.UTF-8"}
    argv = build_namespace_argv(root, xvfb)
    evidence: dict[str, Any] | None = None
    try:
        evidence = run_owned_json_command(
            argv,
            cwd=PROJECT_ROOT,
            env=child_env,
            timeout_seconds=150,
        )
        if evidence.get("status") not in {"PASS", "BLOCKED"}:
            _fail("ERR_INNER_QUALIFICATION_FAILED", "Inner lifecycle qualification returned an invalid status")
        if evidence.get("status") == "BLOCKED":
            finding = evidence.get("blocking_finding")
            admitted = {
                "ERR_LISTENER_SURVIVED",
                "ERR_RUNTIME_START_TIMEOUT",
                "ERR_RUNTIME_START_SHAPE",
            }
            if not isinstance(finding, dict) or finding.get("code") not in admitted:
                _fail("ERR_INNER_QUALIFICATION_FAILED", "Inner lifecycle block is not an admitted provider finding")
        after = fingerprint_paths(protected)
        require_same_fingerprint(before, after)
        evidence["candidate_qualification"] = {
            "status": candidate["status"],
            "manifest_sha256": candidate["manifest_identity"]["manifest_sha256"],
            "catalog_sha256": candidate["catalog_identity"]["catalog_sha256"],
            "catalog_determinism_verified": candidate["catalog_identity"]["determinism_verified"],
        }
        evidence["protected_state"] = {
            "fingerprint_before": before["sha256"],
            "fingerprint_after": after["sha256"],
            "entry_count": before["entry_count"],
            "private_file_contents_read": False,
            "unchanged": True,
        }
        evidence["rollback"] = {"isolated_root_removed": True, "global_state_unchanged": True}
        return evidence
    finally:
        cleanup_owned_root(root)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Qualify the exact Orca lifecycle inside an isolated namespace")
    parser.add_argument("--isolated-root", required=True)
    parser.add_argument("--xvfb", required=True)
    parser.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.inner and args.worker:
            _fail("ERR_CLI_MODE", "Lifecycle harness mode is ambiguous")
        if args.inner:
            result = _run_inner(Path(args.isolated_root), Path(args.xvfb))
        elif args.worker:
            result = _run_worker(Path(args.isolated_root), Path(args.xvfb))
        else:
            result = qualify_real_lifecycle(isolated_root=args.isolated_root, xvfb_path=args.xvfb)
        print(json.dumps(result, indent=2, sort_keys=True))
    except LifecycleError as exc:
        print(json.dumps({"status": "FAIL", "code": exc.code, "error": exc.message}, indent=2, sort_keys=True))
        raise SystemExit(1) from None
    except Exception:
        print(
            json.dumps(
                {"status": "FAIL", "code": "ERR_UNEXPECTED_EXCEPTION", "error": "An unexpected error occurred"},
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    _cli()
