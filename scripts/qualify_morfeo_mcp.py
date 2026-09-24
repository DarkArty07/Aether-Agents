"""Qualify Morfeo MCP against the pinned Hermes tree and a disposable install."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path

from aether_agents.lifecycle import _tree_sha256

PIN_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
PIN_TREE = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"
HOST_DUPLICATES = {
    "terminal",
    "process",
    "read_file",
    "write_file",
    "patch",
    "search_files",
    "execute_code",
}
ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        command, cwd=cwd, env=env, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or "command failed")


def _materialize(checkout: Path, destination: Path) -> str | None:
    if (checkout / ".git").exists():
        commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if commit != PIN_COMMIT:
            raise SystemExit(f"commit {commit} is not the pinned Hermes commit")
        destination.mkdir(parents=True)
        archive = subprocess.run(
            ["git", "-C", str(checkout), "archive", "HEAD"],
            check=False,
            capture_output=True,
        )
        if archive.returncode != 0:
            raise SystemExit(archive.stderr.decode())
        subprocess.run(["tar", "-x", "-C", str(destination)], input=archive.stdout, check=True)
        return commit
    import shutil

    shutil.copytree(
        checkout,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
        symlinks=False,
    )
    return None


def _export_mcp(source: Path) -> str:
    with tempfile.NamedTemporaryFile(prefix="morfeo-mcp-", suffix=".txt", delete=False) as handle:
        export = Path(handle.name)
    try:
        _run(
            [
                "uv",
                "export",
                "--frozen",
                "--no-dev",
                "--extra",
                "mcp",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--output-file",
                str(export),
            ],
            cwd=source,
        )
        text = export.read_text(encoding="utf-8")
    finally:
        export.unlink(missing_ok=True)
    if "mcp==1.28.1" not in text:
        raise SystemExit("locked export did not pin mcp==1.28.1")
    return text


def _layout(root: Path, source: Path, requirements: str) -> dict[str, Path]:
    data = root / "xdg-data"
    state = root / "xdg-state"
    venv = data / "aether" / "runtime" / "current" / "venv"
    profile = state / "aether" / "hermes" / "profiles" / "morfeo"
    project = root / "project"
    _run(["uv", "venv", "--python", sys.executable, str(venv)])
    requirement_path = root / "requirements.txt"
    requirement_path.write_text(requirements, encoding="utf-8")
    python = venv / "bin" / "python"
    _run(
        [
            "uv",
            "pip",
            "sync",
            "--require-hashes",
            "--strict",
            "--python",
            str(python),
            str(requirement_path),
        ],
        cwd=source,
    )
    _run(["uv", "build", "--wheel", "--out-dir", str(root / "dist")], cwd=ROOT)
    wheel = next((root / "dist").glob("*.whl"))
    _run(["uv", "pip", "install", "--python", str(python), "--no-deps", str(wheel)])
    _run(
        ["uv", "pip", "install", "--python", str(python), "--no-deps", "--editable", str(source)],
        env={**os.environ, "HERMES_NIX_BUILD": "1"},
    )
    profile.mkdir(parents=True)
    (profile / "SOUL.md").write_text(
        "# Morfeo\nDisposable qualification identity.\n", encoding="utf-8"
    )
    (profile / "memories").mkdir()
    (profile / "memories" / "USER.md").write_text(
        "Owner prefers concise notes.\n", encoding="utf-8"
    )
    (profile / "memories" / "MEMORY.md").write_text("Fixture memory line.\n", encoding="utf-8")
    (profile / "config.yaml").write_text(
        textwrap.dedent(
            """\
            toolsets:
              - kanban
            memory:
              memory_enabled: true
              user_profile_enabled: true
            plugins:
              enabled:
                - aether-contract-observer
                - aether-objective-contracts
              entries:
                aether-contract-observer:
                  allow_tool_override: true
                aether-objective-contracts:
                  allow_tool_override: true
                  settings:
                    author_profile: morfeo
            """
        ),
        encoding="utf-8",
    )
    project.mkdir()
    _run(["git", "init"], cwd=project)
    project_id = str(uuid.uuid4())
    marker = project / ".aether"
    marker.mkdir()
    (marker / "project.toml").write_text(
        textwrap.dedent(
            f"""\
            schema_version = 1
            project_id = "{project_id}"
            name = "Morfeo MCP fixture"
            initialized_by = "1.0.0"
            forge = "local"
            contract_root = "specs"
            default_branch = "main"
            """
        ),
        encoding="utf-8",
    )
    (project / "fixture.txt").write_text("morfeo-mcp-fixture-file\n", encoding="utf-8")
    (project / "AGENTS.md").write_text(
        "# Fixture project\nDisposable Morfeo MCP project context.\n", encoding="utf-8"
    )
    registry = state / "aether" / "projects"
    registry.mkdir(parents=True)
    (registry / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "projects": {project_id: {"name": "Morfeo MCP fixture", "path": str(project)}},
            }
        ),
        encoding="utf-8",
    )
    os.chmod(registry / "registry.json", 0o600)
    return {
        "python": python,
        "aether": venv / "bin" / "aether",
        "profile": profile,
        "project": project,
        "data": data,
        "state": state,
        "project_id": Path(project_id),
    }


def _env(paths: dict[str, Path]) -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "XDG_DATA_HOME": str(paths["data"]),
        "XDG_STATE_HOME": str(paths["state"]),
        "HERMES_QUIET": "1",
        "HERMES_REDACT_SECRETS": "true",
    }
    return environment


async def _session_calls(session, *, mode: str) -> dict:

    await session.initialize()
    listed = await session.list_tools()
    names = {tool.name for tool in listed.tools}
    if mode == "harness" and names & HOST_DUPLICATES:
        raise SystemExit(f"harness published host tools: {sorted(names & HOST_DUPLICATES)}")
    if mode == "chatbot" and not HOST_DUPLICATES <= names:
        missing = sorted(HOST_DUPLICATES - names)
        raise SystemExit(f"chatbot omitted host tools: {missing}")
    external = sorted(name for name in names if name.startswith("mcp__"))
    if external:
        raise SystemExit(f"external MCP tools published: {external}")
    if "morfeo_bootstrap" not in names:
        raise SystemExit("morfeo_bootstrap is missing")
    aether_tools = sorted(
        name
        for name in names
        if name.startswith("aether_")
        or name in {"objective_contract", "project_knowledge", "work_memory"}
    )
    if not aether_tools:
        raise SystemExit(f"no Aether plugin tool in {sorted(names)}")
    early = await session.call_tool("skills_list", {})
    early_text = _text(early)
    if "MORFEO_CONTEXT_REQUIRED" not in early_text:
        raise SystemExit(f"tool ran before bootstrap: {early_text[:200]}")
    boot = await session.call_tool("morfeo_bootstrap", {})
    payload = json.loads(_text(boot))
    for key in ("role", "mode", "project_id", "context_revision", "sections", "tools"):
        if key not in payload:
            raise SystemExit(f"bootstrap missing {key}")
    if payload["mode"] != mode or payload["role"] != "morfeo":
        raise SystemExit("bootstrap identity mismatch")
    sections = payload["sections"]
    for name in ("soul", "user", "memory", "project_context", "skills"):
        record = sections.get(name) or {}
        if "sha256" not in record or "bytes" not in record:
            raise SystemExit(f"section {name} has no identity")
    joined = json.dumps(payload)
    if "sk-" in joined or ".env" in joined:
        raise SystemExit("bootstrap leaked a secret marker")
    listed_again = await session.call_tool("skills_list", {})
    if "MORFEO_CONTEXT_REQUIRED" in _text(listed_again):
        raise SystemExit("skills_list stayed gated after bootstrap")
    return {"names": names, "bootstrap": payload, "skills": _text(listed_again)}


def _text(result) -> str:
    chunks = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _seed_search(paths: dict[str, Path]) -> None:
    script = """
import os
from hermes_state import SessionDB
db = SessionDB()
session_id = db.create_session(
    "fixture-search",
    "mcp",
    profile_name="morfeo",
    cwd=os.environ["QUALIFY_PROJECT"],
    git_repo_root=os.environ["QUALIFY_PROJECT"],
)
db.append_message(session_id, "user", "morfeo-mcp-search-fixture")
"""
    environment = _env(paths)
    environment["HERMES_HOME"] = str(paths["profile"])
    environment["QUALIFY_PROJECT"] = str(paths["project"])
    _run([str(paths["python"]), "-c", script], env=environment)


async def _stateful(session) -> None:
    memory = await session.call_tool(
        "memory",
        {"action": "add", "target": "memory", "content": "qualification memory entry"},
    )
    if "qualification memory entry" not in _text(memory) and "success" not in _text(memory).lower():
        raise SystemExit(f"memory call failed: {_text(memory)[:400]}")
    found = await session.call_tool("session_search", {"query": "morfeo-mcp-search-fixture"})
    if "morfeo-mcp-search-fixture" not in _text(found):
        raise SystemExit(f"session_search missed fixture: {_text(found)[:400]}")
    listed = await session.call_tool("delegate_task", {"action": "list"})
    if "MORFEO_CONTEXT_REQUIRED" in _text(listed):
        raise SystemExit("delegate_task was not bootstrapped")
    names = {tool.name for tool in (await session.list_tools()).tools}
    if "aether_observe" in names:
        observed = await session.call_tool("aether_observe", {})
        if "MORFEO_CONTEXT_REQUIRED" in _text(observed):
            raise SystemExit("aether_observe stayed gated")
    if "kanban_list" in names:
        board = await session.call_tool("kanban_list", {})
        if "MORFEO_CONTEXT_REQUIRED" in _text(board):
            raise SystemExit("kanban_list stayed gated")


async def _stdio(paths: dict[str, Path]) -> dict:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    parameters = StdioServerParameters(
        command=str(paths["aether"]),
        args=[
            "mcp",
            "morfeo",
            "serve",
            "--mode",
            "harness",
            "--transport",
            "stdio",
            "--project",
            str(paths["project"]),
        ],
        env=_env(paths),
        cwd=str(paths["project"]),
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            result = await _session_calls(session, mode="harness")
            await _stateful(session)
            return result


async def _http(paths: dict[str, Path], port: int) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    process = await asyncio.create_subprocess_exec(
        str(paths["aether"]),
        "mcp",
        "morfeo",
        "serve",
        "--mode",
        "chatbot",
        "--transport",
        "streamable-http",
        "--project",
        str(paths["project"]),
        "--port",
        str(port),
        cwd=str(paths["project"]),
        env=_env(paths),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        await _wait_port(port)
        async with streamablehttp_client(url) as (read_a, write_a, _a):
            async with ClientSession(read_a, write_a) as first:
                first_result = await _session_calls(first, mode="chatbot")
                read = await first.call_tool("read_file", {"path": "fixture.txt"})
                if "morfeo-mcp-fixture-file" not in _text(read):
                    raise SystemExit(f"read_file failed: {_text(read)[:300]}")
                async with streamablehttp_client(url) as (read_b, write_b, _b):
                    async with ClientSession(read_b, write_b) as second:
                        await second.initialize()
                        early = await second.call_tool("skills_list", {})
                        if "MORFEO_CONTEXT_REQUIRED" not in _text(early):
                            raise SystemExit("second client inherited bootstrap")
                        second_result = await second.call_tool("morfeo_bootstrap", {})
                        if not json.loads(_text(second_result)).get("context_revision"):
                            raise SystemExit("second client bootstrap has no revision")
                        if not first_result["bootstrap"].get("context_revision"):
                            raise SystemExit("first client bootstrap has no revision")
    finally:
        process.terminate()
        await process.wait()


async def _wait_port(port: int) -> None:
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            await asyncio.sleep(0.1)
    raise SystemExit("streamable HTTP server did not accept connections")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    args = parser.parse_args(argv)
    checkout = args.checkout.resolve()
    with tempfile.TemporaryDirectory(prefix="morfeo-mcp-qualify-") as temporary:
        root = Path(temporary)
        source = root / "hermes-source"
        commit = _materialize(checkout, source)
        digest = _tree_sha256(source)
        if digest != PIN_TREE:
            raise SystemExit(f"tree digest {digest} is not the pinned Hermes tree")
        requirements = _export_mcp(source)
        paths = _layout(root, source, requirements)
        # Path values are strings except project_id stored awkwardly; normalize.
        paths["project_id"] = Path(str(paths["project_id"]))
        _seed_search(paths)
        asyncio.run(_stdio(paths))
        asyncio.run(_http(paths, _free_port()))
        database = paths["profile"] / "state.db"
        import sqlite3

        rows = (
            sqlite3.connect(database)
            .execute("select source, profile_name, cwd, git_repo_root from sessions")
            .fetchall()
        )
        project = str(paths["project"])
        matched = [
            row
            for row in rows
            if row[0] == "mcp" and row[1] == "morfeo" and row[2] == project and row[3] == project
        ]
        if len(matched) < 2:
            raise SystemExit(f"expected disposable Morfeo MCP sessions, found {rows}")
    print(f"qualified hermes pin {commit or PIN_COMMIT} tree {PIN_TREE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
