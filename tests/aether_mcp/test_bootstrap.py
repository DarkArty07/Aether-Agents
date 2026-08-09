"""Behavior contract for the default-off, zero-tool Aether MCP bootstrap."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import LATEST_PROTOCOL_VERSION

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
PYTHON = Path(sys.executable)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _candidate_env(tmp_path: Path | None = None) -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", "")}
    env["PYTHONPATH"] = str(SRC)
    if tmp_path is not None:
        env["HOME"] = str(tmp_path)
        env["TMPDIR"] = str(tmp_path)
        env["AETHER_MCP_TEST_CANARY"] = "synthetic-m2-1a-canary"
    return env


def _children(pid: int) -> set[int]:
    children = Path(f"/proc/{pid}/task/{pid}/children")
    if not children.exists():
        return set()
    return {int(value) for value in children.read_text(encoding="ascii").split()}


def _socket_fds(pid: int) -> list[str]:
    fd_root = Path(f"/proc/{pid}/fd")
    return [str(fd) for fd in fd_root.iterdir() if os.readlink(fd).startswith("socket:[")]


def test_static_package_metadata_imports_without_side_effects(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())
    completed = subprocess.run(
        [
            str(PYTHON),
            "-c",
            (
                "import aether_mcp; "
                "assert aether_mcp.__version__ == '0.22.0.dev0'; "
                "assert aether_mcp.PROTOCOL_ID == 'aether.mcp/v1alpha2'; "
                "assert aether_mcp.SERVER_NAME == 'aether-mcp'"
            ),
        ],
        cwd=tmp_path,
        env=_candidate_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert set(tmp_path.iterdir()) == before


@pytest.mark.anyio
async def test_real_stdio_handshake_exposes_metadata_and_zero_tools() -> None:
    parameters = StdioServerParameters(
        command=str(PYTHON),
        args=["-m", "aether_mcp"],
        env=_candidate_env(),
        cwd=ROOT,
    )
    async with asyncio.timeout(10):
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()

    assert initialized.serverInfo.name == "aether-mcp"
    assert initialized.serverInfo.version == "1.28.1"
    assert initialized.protocolVersion
    assert initialized.protocolVersion == LATEST_PROTOCOL_VERSION
    assert initialized.instructions is not None
    for marker in (
        "aether.mcp/v1alpha2",
        "0.22.0.dev0",
        "default-off",
        "no tools registered",
    ):
        assert marker in initialized.instructions
    assert tools.tools == []


def test_eof_is_clean_and_leaves_no_child(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [str(PYTHON), "-m", "aether_mcp"],
        cwd=ROOT,
        env=_candidate_env(tmp_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdin is not None
    process.stdin.close()
    process.wait(timeout=5)
    assert process.stdout is not None
    assert process.stderr is not None
    assert process.returncode == 0
    assert process.stdout.read() == ""
    assert process.stderr.read() == ""
    assert _children(process.pid) == set()


def test_waiting_stdio_process_has_no_socket_or_file_effect(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())
    process = subprocess.Popen(
        [str(PYTHON), "-m", "aether_mcp"],
        cwd=ROOT,
        env=_candidate_env(tmp_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                break
            time.sleep(0.01)
        assert process.poll() is None
        assert _socket_fds(process.pid) == []
        assert _children(process.pid) == set()
        assert set(tmp_path.iterdir()) == before
    finally:
        assert process.stdin is not None
        process.stdin.close()
        process.wait(timeout=5)
    assert process.returncode == 0
    assert set(tmp_path.iterdir()) == before
