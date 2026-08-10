"""Operational M1 MCP facade contract."""

from __future__ import annotations

import json
import stat
import subprocess
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aether_mcp import protocol, server
from aether_mcp.catalog import OrcaCatalog
from aether_mcp.runtime import OperationalRuntime, PublicOrcaTransport

TOOLS = (
    "project_admit", "project_inspect", "swarm_validate", "swarm_start",
    "swarm_status", "swarm_dispatch", "swarm_message", "swarm_reconcile",
    "swarm_retry", "swarm_cancel", "swarm_close", "swarm_trace",
    "orca_search", "orca_describe", "orca_call",
)


def test_operational_server_registers_only_the_approved_tools_without_bootstrapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AETHER_STATE_ROOT", str(tmp_path / "state"))
    before = set(tmp_path.iterdir())

    operational = server.create_server()

    assert tuple(tool.name for tool in operational._tool_manager.list_tools()) == TOOLS
    assert protocol.CALLABLE_TOOL_NAMES == frozenset(TOOLS)
    assert set(tmp_path.iterdir()) == before


def _runtime_environment(tmp_path: Path) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir()
    wrapper = tmp_path / "orca-public-cli"
    wrapper.write_text("#!/bin/sh\nexit 0\n")
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    return {
        "AETHER_STATE_ROOT": str(tmp_path / "state"),
        "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
        "HERMES_HOME": str(home),
        "AETHER_PROFILE": "hermes",
        "AETHER_SESSION_ID": str(uuid.uuid4()),
        "AETHER_ORCA_CLI": str(wrapper),
        "AETHER_ORCA_COORDINATOR_HANDLE": "term-coordinator",
        "AETHER_ORCA_REPO_SELECTOR": "path:/tmp/source",
        "AETHER_ORCA_BASE_REF": "main",
        "AETHER_ORCA_TIMEOUT_MS": "600000",
    }


def test_runtime_requires_absolute_public_cli_and_binds_model_and_catalog(tmp_path: Path) -> None:
    environment = _runtime_environment(tmp_path)
    runtime = OperationalRuntime(environment)
    _foundation, lifecycle, _worker = runtime._build()

    assert lifecycle.provider.binding_digest == OrcaCatalog.bundled().digest
    assert lifecycle.provider.model_runtime is not None
    assert lifecycle.provider.model_runtime.agent == "codex"
    assert lifecycle.provider.model_runtime.expected_model == "gpt-5.6-terra"

    relative = dict(environment, AETHER_ORCA_CLI="orca", AETHER_STATE_ROOT=str(tmp_path / "relative-state"))
    response = OperationalRuntime(relative).invoke("project_inspect", {"project_id": str(uuid.uuid4())})
    assert response["error"]["code"] == "CAPABILITY_UNAVAILABLE"

    mismatched = dict(environment, AETHER_ORCA_BINDING_DIGEST="0" * 64, AETHER_STATE_ROOT=str(tmp_path / "mismatched-state"))
    response = OperationalRuntime(mismatched).invoke("project_inspect", {"project_id": str(uuid.uuid4())})
    assert response["error"]["code"] == "PROVIDER_SCHEMA_DRIFT"


def test_public_transport_bounds_stderr_and_preserves_timeout_as_unknown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    executable = tmp_path / "orca-public-cli"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    transport = PublicOrcaTransport(str(executable))

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, b"{}", b"x" * (4 * 1024 * 1024 + 1)),
    )
    with pytest.raises(protocol.ProtocolError) as captured:
        transport(("status", "--json"))
    assert captured.value.code == "PROVIDER_RESPONSE_INVALID"

    def timed_out(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired("orca", 30)

    monkeypatch.setattr(subprocess, "run", timed_out)
    with pytest.raises(protocol.ProtocolError) as captured:
        transport(("status", "--json"))
    assert captured.value.code == "DELIVERY_UNKNOWN"


def test_runtime_preserves_cleanup_failed_protocol_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = OperationalRuntime({})
    foundation, lifecycle, worker = MagicMock(), MagicMock(), MagicMock()
    lifecycle.swarm_status.return_value = {"outcome": "CLEANUP_FAILED"}
    monkeypatch.setattr(runtime, "_build", lambda: (foundation, lifecycle, worker))

    response = runtime.invoke(
        "swarm_status",
        {"project_id": str(uuid.uuid4()), "run_id": str(uuid.uuid4()), "cursor": None, "wait_ms": 0, "detail": "summary"},
    )

    assert response["ok"] is True
    assert response["outcome"] == "CLEANUP_FAILED"


@pytest.mark.anyio
async def test_facade_returns_a_stable_secret_safe_error_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AETHER_STATE_ROOT", str(tmp_path / "state"))
    operational = server.create_server()
    request = {"project_id": "SYNTHETIC-SECRET-DO-NOT-ECHO", "unexpected": "SYNTHETIC-SECRET-DO-NOT-ECHO"}

    response = await operational._tool_manager.call_tool("project_inspect", request)

    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_INPUT"
    assert "SYNTHETIC-SECRET-DO-NOT-ECHO" not in json.dumps(response)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
