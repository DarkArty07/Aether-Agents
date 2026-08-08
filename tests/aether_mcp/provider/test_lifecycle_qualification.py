"""M1.3 contract tests for isolated Orca lifecycle qualification."""

from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
QUALIFIER_DIR = ROOT / "scripts" / "aether_mcp"
if str(QUALIFIER_DIR) not in sys.path:
    sys.path.insert(0, str(QUALIFIER_DIR))

import qualify_orca_lifecycle as lifecycle  # type: ignore[import-not-found]  # noqa: E402

LifecycleError = lifecycle.LifecycleError
REAL_LAUNCHER = Path("/home/darkarty/.local/bin/orca")
REAL_ARTIFACT = Path("/home/darkarty/.local/opt/orca/orca-linux.AppImage")
REAL_XVFB = Path("/tmp/aether-m13-xvfb-toolchain/root/usr/bin/Xvfb")
REAL_FIXTURE_AVAILABLE = (
    REAL_LAUNCHER.is_file()
    and os.access(REAL_LAUNCHER, os.X_OK)
    and REAL_ARTIFACT.is_file()
    and os.access(REAL_ARTIFACT, os.X_OK)
)


def _new_root(prefix: str = "aether-m1-3-test-") -> Path:
    root = Path("/tmp") / f"{prefix}{os.urandom(6).hex()}"
    root.mkdir(mode=0o700)
    return root


@pytest.fixture
def lifecycle_root() -> Iterator[Path]:
    root = _new_root()
    yield root
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def _error_code(exc: pytest.ExceptionInfo[Exception]) -> str:
    return str(getattr(exc.value, "code"))


def test_lifecycle_root_must_be_fresh_direct_tmp_child(lifecycle_root: Path, tmp_path: Path) -> None:
    lifecycle.validate_lifecycle_root(lifecycle_root)

    nested = lifecycle_root / "nested"
    nested.mkdir()
    with pytest.raises(LifecycleError) as exc:
        lifecycle.validate_lifecycle_root(nested)
    assert _error_code(exc) == "ERR_ISOLATION_ROOT_INVALID"

    wrong_prefix = Path("/tmp") / f"wrong-{os.urandom(5).hex()}"
    wrong_prefix.mkdir()
    try:
        with pytest.raises(LifecycleError) as exc:
            lifecycle.validate_lifecycle_root(wrong_prefix)
        assert _error_code(exc) == "ERR_ISOLATION_ROOT_INVALID"
    finally:
        wrong_prefix.rmdir()

    target = tmp_path / "target"
    target.mkdir()
    link = Path("/tmp") / f"aether-m1-3-test-link-{os.urandom(5).hex()}"
    link.symlink_to(target, target_is_directory=True)
    try:
        with pytest.raises(LifecycleError) as exc:
            lifecycle.validate_lifecycle_root(link)
        assert _error_code(exc) == "ERR_ISOLATION_ROOT_INVALID"
    finally:
        link.unlink()


def test_child_environment_is_exact_and_rooted(lifecycle_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/forbidden/home")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("API_TOKEN", "forbidden")
    env = lifecycle.build_child_environment(lifecycle_root)

    assert set(env) == {
        "HOME",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_STATE_HOME",
        "TMPDIR",
        "PATH",
        "LANG",
        "APPIMAGE_EXTRACT_AND_RUN",
    }
    assert env["APPIMAGE_EXTRACT_AND_RUN"] == "1"
    for key in (
        "HOME",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_STATE_HOME",
        "TMPDIR",
    ):
        assert Path(env[key]).is_relative_to(lifecycle_root)
    assert "DISPLAY" not in env
    assert "API_TOKEN" not in env


def test_parse_json_envelope_rejects_stderr_malformed_and_non_object() -> None:
    good = b'{"id":"x","ok":true,"result":{},"_meta":{"runtimeId":"r"}}\n'
    assert lifecycle.parse_json_object(good, b"")["ok"] is True

    for stdout, stderr, code in (
        (good, b"warning", "ERR_COMMAND_STDERR"),
        (b"not-json", b"", "ERR_COMMAND_MALFORMED_JSON"),
        (b"[]", b"", "ERR_COMMAND_SHAPE"),
    ):
        with pytest.raises(LifecycleError) as exc:
            lifecycle.parse_json_object(stdout, stderr)
        assert _error_code(exc) == code


def test_serve_stream_allows_only_owned_extraction_paths_then_one_ready_object(lifecycle_root: Path) -> None:
    extracted = lifecycle_root / "tmp" / ("appimage_extracted_" + "a" * 32)
    line = str(extracted / "resources" / "app.asar")
    assert lifecycle.parse_serve_stream((line + "\n").encode(), lifecycle_root) is None

    ready = {
        "type": "orca_server_ready",
        "schemaVersion": 1,
        "runtimeId": "runtime-1",
        "endpoint": "ws://0.0.0.0:1234",
        "boundEndpoint": "ws://0.0.0.0:1234",
        "advertisedEndpoint": "ws://127.0.0.1:1234",
        "managedWslCliReconciliation": "settled",
        "pairing": {"available": False, "reason": "disabled_by_operator", "guidance": "fixture"},
    }
    payload = (line + "\n" + json.dumps(ready) + "\n").encode()
    assert lifecycle.parse_serve_stream(payload, lifecycle_root) == ready

    with pytest.raises(LifecycleError) as exc:
        lifecycle.parse_serve_stream(b"unexpected prose\n", lifecycle_root)
    assert _error_code(exc) == "ERR_RUNTIME_START_SHAPE"

    with pytest.raises(LifecycleError) as exc:
        lifecycle.parse_serve_stream((json.dumps(ready) + "\n" + json.dumps(ready) + "\n").encode(), lifecycle_root)
    assert _error_code(exc) == "ERR_RUNTIME_START_SHAPE"


def test_status_exit_zero_is_not_readiness_and_version_is_pinned() -> None:
    not_running = {
        "id": "local-status",
        "ok": True,
        "result": {
            "app": {"running": False, "pid": None},
            "runtime": {"state": "not_running", "reachable": False, "runtimeId": None},
            "graph": {"state": "not_running"},
        },
        "_meta": {"runtimeId": "none"},
    }
    assert lifecycle.status_is_ready(not_running, expected_version="1.4.167") is False

    ready = json.loads(json.dumps(not_running))
    ready["result"]["app"] = {"running": True, "pid": 123}
    ready["result"]["runtime"] = {
        "state": "ready",
        "reachable": True,
        "runtimeId": "runtime-1",
        "appVersion": "1.4.167",
        "capabilities": [],
    }
    ready["result"]["graph"] = {"state": "ready"}
    ready["_meta"] = {"runtimeId": "runtime-1"}
    assert lifecycle.status_is_ready(ready, expected_version="1.4.167") is True

    ready["result"]["runtime"]["appVersion"] = "9.9.9"
    with pytest.raises(LifecycleError) as exc:
        lifecycle.status_is_ready(ready, expected_version="1.4.167")
    assert _error_code(exc) == "ERR_RUNTIME_VERSION_DRIFT"


def test_schema_derivation_is_deterministic_bounded_and_secret_free() -> None:
    value = {"b": [1, 2], "a": {"x": True, "y": None}}
    first = lifecycle.derive_observed_schema(value)
    second = lifecycle.derive_observed_schema(json.loads(json.dumps(value)))
    assert first == second
    assert list(first["properties"]) == ["a", "b"]
    assert "1" not in json.dumps(first)
    assert "2" not in json.dumps(first)

    deep: Any = None
    for _ in range(20):
        deep = {"x": deep}
    with pytest.raises(LifecycleError) as exc:
        lifecycle.derive_observed_schema(deep)
    assert _error_code(exc) == "ERR_SCHEMA_DEPTH"


def test_listener_policy_rejects_wildcard_without_network_namespace() -> None:
    lifecycle.validate_listener_address("127.0.0.1", isolated_network=False)
    lifecycle.validate_listener_address("::1", isolated_network=False)
    lifecycle.validate_listener_address("0.0.0.0", isolated_network=True)

    with pytest.raises(LifecycleError) as exc:
        lifecycle.validate_listener_address("0.0.0.0", isolated_network=False)
    assert _error_code(exc) == "ERR_NON_LOOPBACK_LISTENER"


def test_network_namespace_inventory_uses_netlink_payload() -> None:
    assert lifecycle.interfaces_from_ip_json([{"ifname": "lo", "flags": ["LOOPBACK", "UP"]}]) == ["lo"]
    with pytest.raises(LifecycleError) as exc:
        lifecycle.interfaces_from_ip_json(
            [
                {"ifname": "lo", "flags": ["LOOPBACK", "UP"]},
                {"ifname": "ens160", "flags": ["BROADCAST", "UP"]},
            ]
        )
    assert _error_code(exc) == "ERR_NETWORK_NAMESPACE_ESCAPE"


def test_namespace_argv_uses_explicit_subids_and_never_disables_sandbox(lifecycle_root: Path) -> None:
    argv = lifecycle.build_namespace_argv(
        lifecycle_root,
        Path("/tmp/xvfb-fixture"),
        python_path=Path("/tmp/python-fixture"),
        outer_uid=1000,
        outer_gid=1000,
        subuid_range=(100000, 65536),
        subgid_range=(100000, 65536),
    )
    assert "--map-root-user" not in argv
    assert "--no-sandbox" not in argv
    assert "--mount" in argv
    assert "--pid" in argv
    assert "--fork" in argv
    assert "--mount-proc" in argv
    assert ["--map-users", "0:1000:1"] == argv[argv.index("--map-users") : argv.index("--map-users") + 2]
    assert "1:100000:65536" in argv
    assert "--inner" in argv


def test_required_operation_plan_has_no_forbidden_effects() -> None:
    plan = lifecycle.required_public_operation_plan()
    flattened = [tuple(step["argv"]) for step in plan]
    assert ("status", "--json") in flattened
    assert ("orchestration", "run-create") in [item[:2] for item in flattened]
    assert ("orchestration", "task-create") in [item[:2] for item in flattened]
    assert ("orchestration", "reset") in [item[:2] for item in flattened]
    assert ("terminal", "list", "--json") in flattened
    assert ("worktree", "list", "--json") in flattened
    assert ("worktree", "ps", "--json") in flattened

    forbidden = {
        "dispatch",
        "worker-start",
        "terminal-create",
        "terminal-send",
        "worktree-create",
        "worktree-rm",
        "account",
        "environment",
        "open",
    }
    assert not any(token in forbidden for argv in flattened for token in argv)


def test_missing_seams_are_unsupported_without_complete_proof() -> None:
    verdicts = lifecycle.evaluate_missing_seams({})
    assert set(verdicts) == set(lifecycle.MISSING_SEAMS)
    assert all(item["verdict"] == "UNSUPPORTED" for item in verdicts.values())

    incomplete = {
        "events_read": {
            "ordered_operations": [],
            "preconditions": [],
        }
    }
    with pytest.raises(LifecycleError) as exc:
        lifecycle.evaluate_missing_seams(incomplete)
    assert _error_code(exc) == "ERR_COMPOSITION_PROOF_INCOMPLETE"


def test_complete_composition_proof_must_be_explicit() -> None:
    proof = {
        "ordered_operations": [["orchestration", "inbox", "--json"]],
        "preconditions": ["isolated_run"],
        "step_identities": ["events_read:1"],
        "effects": ["READ_ONLY"],
        "timeout_unknown_handling": "fail_closed",
        "reconciliation": ["repeat_read_with_cursor"],
        "cleanup": ["none_read_only"],
        "partial_result_semantics": "explicit",
        "rollback_limits": "read_only",
        "semantic_equivalence_evidence": "fixture_digest",
    }
    verdicts = lifecycle.evaluate_missing_seams({"events_read": proof})
    assert verdicts["events_read"]["verdict"] == "PROVEN_COMPOSED"
    assert verdicts["run_cancel"]["verdict"] == "UNSUPPORTED"


def test_fingerprint_detects_drift_without_returning_contents(tmp_path: Path) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()
    secret = protected / "private.json"
    secret.write_text('{"token":"do-not-return"}', encoding="utf-8")

    before = lifecycle.fingerprint_paths([protected])
    encoded = json.dumps(before, sort_keys=True)
    assert "do-not-return" not in encoded
    assert "token" not in encoded

    secret.write_text('{"token":"changed"}', encoding="utf-8")
    after = lifecycle.fingerprint_paths([protected])
    with pytest.raises(LifecycleError) as exc:
        lifecycle.require_same_fingerprint(before, after)
    assert _error_code(exc) == "ERR_PROTECTED_STATE_DRIFT"


def test_cleanup_owned_root_is_idempotent_and_refuses_foreign_root(lifecycle_root: Path, tmp_path: Path) -> None:
    (lifecycle_root / "partial").mkdir()
    (lifecycle_root / "partial" / "state").write_text("fixture", encoding="utf-8")
    lifecycle.cleanup_owned_root(lifecycle_root)
    lifecycle.cleanup_owned_root(lifecycle_root)
    assert not lifecycle_root.exists()

    foreign = tmp_path / "aether-m1-3-test-foreign"
    foreign.mkdir()
    with pytest.raises(LifecycleError) as exc:
        lifecycle.cleanup_owned_root(foreign)
    assert _error_code(exc) == "ERR_CLEANUP_SCOPE"
    assert foreign.exists()


def test_command_timeout_is_unknown_and_kills_owned_process_group(lifecycle_root: Path, tmp_path: Path) -> None:
    child_pid_file = lifecycle_root / "child.pid"
    executable = tmp_path / "hang.py"
    executable.write_text(
        "#!/usr/bin/python3\n"
        "import subprocess,time,sys\n"
        f"p=subprocess.Popen(['sleep','60']);open({str(child_pid_file)!r},'w').write(str(p.pid))\n"
        "sys.stdout.flush();time.sleep(60)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    with pytest.raises(LifecycleError) as exc:
        lifecycle.run_owned_json_command(
            [str(executable)],
            cwd=lifecycle_root,
            env=lifecycle.build_child_environment(lifecycle_root),
            timeout_seconds=0.2,
        )
    assert _error_code(exc) == "ERR_COMMAND_TIMEOUT_UNKNOWN"

    deadline = time.monotonic() + 3
    while not child_pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert child_pid_file.exists()
    child_pid = int(child_pid_file.read_text())
    deadline = time.monotonic() + 3
    while Path(f"/proc/{child_pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not Path(f"/proc/{child_pid}").exists()


def test_listener_shutdown_waits_for_bounded_async_close() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]
    thread = threading.Thread(target=lambda: (time.sleep(0.15), server.close()), daemon=True)
    thread.start()
    assert lifecycle.wait_for_listener_close(port, timeout_seconds=1.0) is True
    thread.join(timeout=1)

    survivor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    survivor.bind(("127.0.0.1", 0))
    survivor.listen()
    survivor_port = survivor.getsockname()[1]
    try:
        assert lifecycle.wait_for_listener_close(survivor_port, timeout_seconds=0.1) is False
    finally:
        survivor.close()


def test_structured_child_failure_preserves_stable_error_code(lifecycle_root: Path, tmp_path: Path) -> None:
    executable = tmp_path / "fail.py"
    executable.write_text(
        "#!/usr/bin/python3\n"
        "import json\n"
        "print(json.dumps({'status':'FAIL','code':'ERR_SYNTHETIC','error':'safe failure'}))\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    with pytest.raises(LifecycleError) as exc:
        lifecycle.run_owned_json_command(
            [str(executable)],
            cwd=lifecycle_root,
            env=lifecycle.build_child_environment(lifecycle_root),
        )
    assert _error_code(exc) == "ERR_SYNTHETIC"


class _FakeDriver:
    def __init__(self, *, recover: bool = True) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.starts = 0
        self.stops = 0
        self.recover = recover

    def verify_identity(self) -> dict[str, Any]:
        self.calls.append(("verify_identity",))
        return {"candidate_id": "synthetic", "product_version": "1.4.167"}

    def start(self) -> dict[str, Any]:
        self.starts += 1
        self.calls.append(("start", str(self.starts)))
        return {"runtime_id": f"runtime-{self.starts}", "listener": "0.0.0.0", "isolated_network": True}

    def command(self, argv: list[str]) -> dict[str, Any]:
        self.calls.append(tuple(argv))
        command = tuple(argv)
        envelope: dict[str, Any] = {"id": "fixture", "ok": True, "result": {}, "_meta": {"runtimeId": "r"}}
        if command[:2] == ("orchestration", "run-create"):
            envelope["result"] = {"run": {"id": "run-1"}}
        elif command[:2] == ("orchestration", "task-create"):
            envelope["result"] = {"task": {"id": "task-1", "runId": "run-1"}}
        elif command[:2] == ("orchestration", "run-show"):
            if self.starts > 1 and not self.recover:
                return {"id": "fixture", "ok": False, "error": {"code": "not_found"}, "_meta": {"runtimeId": "r"}}
            envelope["result"] = {"run": {"id": "run-1"}}
        elif command[:2] == ("orchestration", "task-list"):
            envelope["result"] = {"tasks": [{"id": "task-1", "runId": "run-1"}]}
        elif command == ("status", "--json"):
            envelope["result"] = {
                "app": {"running": True, "pid": 1},
                "runtime": {
                    "state": "ready",
                    "reachable": True,
                    "runtimeId": f"runtime-{self.starts}",
                    "appVersion": "1.4.167",
                    "capabilities": [],
                },
                "graph": {"state": "ready"},
            }
        return envelope

    def stop(self) -> dict[str, Any]:
        self.stops += 1
        self.calls.append(("stop", str(self.stops)))
        return {"stopped": True, "survivors": 0}


def test_lifecycle_state_machine_proves_restart_and_stops_twice() -> None:
    driver = _FakeDriver()
    evidence = lifecycle.exercise_lifecycle(driver)
    assert evidence["status"] == "PASS"
    assert evidence["cold_start"]["ready"] is True
    assert evidence["restart"]["run_recovered"] is True
    assert evidence["restart"]["task_recovered"] is True
    assert driver.starts == 2
    assert driver.stops == 2
    assert ("orchestration", "reset", "--tasks", "--json") in driver.calls
    assert ("orchestration", "reset", "--messages", "--json") in driver.calls


def test_lifecycle_state_machine_fails_closed_when_restart_loses_run() -> None:
    driver = _FakeDriver(recover=False)
    with pytest.raises(LifecycleError) as exc:
        lifecycle.exercise_lifecycle(driver)
    assert _error_code(exc) == "ERR_RESTART_STATE_LOST"
    assert driver.stops == 2


@pytest.mark.skipif(not REAL_FIXTURE_AVAILABLE, reason="canonical Orca candidate is not installed")
def test_real_candidate_lifecycle_executes_without_skip_and_cleans() -> None:
    assert REAL_XVFB.is_file() and os.access(REAL_XVFB, os.X_OK), "real M1.3 fixture requires isolated Xvfb"
    root = _new_root(prefix="aether-m1-3-real-")
    try:
        evidence = lifecycle.qualify_real_lifecycle(
            isolated_root=root,
            xvfb_path=REAL_XVFB,
        )
        assert evidence["status"] in {"PASS", "BLOCKED"}
        if evidence["status"] == "BLOCKED":
            finding = evidence["blocking_finding"]
            assert finding["code"] in {
                "ERR_LISTENER_SURVIVED",
                "ERR_RUNTIME_START_TIMEOUT",
                "ERR_RUNTIME_START_SHAPE",
            }
            if finding["code"] == "ERR_LISTENER_SURVIVED":
                assert finding["stage"] in {"first_stop", "second_stop"}
                assert finding["listener_survived"] is True
            elif finding["code"] == "ERR_RUNTIME_START_TIMEOUT":
                assert finding["stage"] in {"cold_start", "restart_start"}
                assert finding["timeout_seconds"] == lifecycle.STARTUP_TIMEOUT_SECONDS
            else:
                assert finding["stage"] in {"cold_start", "restart_start"}
                assert finding["startup_output_contract_violation"] is True
        else:
            assert evidence["cold_start"]["ready"] is True
            assert evidence["restart"]["run_recovered"] is True
            assert evidence["restart"]["task_recovered"] is True
        assert evidence["network_isolation"]["external_interfaces"] == 0
        assert evidence["worker_identity"]["effective_capabilities"] == 0
        assert evidence["worker_identity"]["electron_sandbox_disabled"] is False
        assert evidence["namespace_rollback"]["process_survivors"] == 0
        assert evidence["namespace_rollback"]["listener_survivors"] == 0
        assert evidence["namespace_rollback"]["mount_survivors"] == 0
        assert evidence["protected_state"]["unchanged"] is True
        assert evidence["rollback"]["isolated_root_removed"] is True
        assert all(item["verdict"] == "UNSUPPORTED" for item in evidence["missing_seams"].values())
    finally:
        lifecycle.cleanup_owned_root(root)
    assert not root.exists()
