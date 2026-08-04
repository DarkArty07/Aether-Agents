"""Aether-native continuity package independent of Olympus runtime state."""

from __future__ import annotations

import ast
import hashlib
import importlib
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
OLD_PATHS = (
    ROOT / "src/olympus_v3/aether_db.py",
    ROOT / "src/olympus_v3/aether_hooks/__init__.py",
    ROOT / "src/olympus_v3/aether_hooks/hooks.py",
)
PROFILE_PLUGINS = tuple((ROOT / "home/profiles").glob("*/plugins/aether/__init__.py"))


def native_modules():
    database = importlib.import_module("aether_agents.continuity.database")
    hooks = importlib.import_module("aether_agents.continuity.hooks")
    return database, hooks


def test_continuity_package_replaces_olympus_sources_without_runtime_imports() -> None:
    database, hooks = native_modules()

    assert database.AetherDBSync
    assert hooks.register
    assert not any(path.exists() for path in OLD_PATHS)
    assert database.__file__ is not None
    assert hooks.__file__ is not None
    for source in (Path(database.__file__), Path(hooks.__file__)):
        tree = ast.parse(source.read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert not any(name.startswith("olympus_v3") for name in imported)


def test_existing_database_is_byte_preserved_by_native_readers(tmp_path: Path) -> None:
    database, _ = native_modules()
    path = tmp_path / ".aether" / "aether.db"
    original = database.AetherDBSync(path)
    original.ensure_tables()
    original.insert_session("session-existing", agent="hefesto", model="model", platform="cli")
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    reopened = database.AetherDBSync(path)
    sessions = reopened.get_recent_sessions(limit=10)
    state = reopened.get_hot_state()
    after = hashlib.sha256(path.read_bytes()).hexdigest()

    assert sessions[0]["session_id"] == "session-existing"
    assert state["id"] == 1
    assert after == before


def test_hooks_bind_the_session_argument_and_explicit_result_without_olympus_db() -> None:
    _, hooks = native_modules()
    db = Mock()
    db.get_hot_state.return_value = {"total_sessions": 2}

    with (
        patch.object(hooks, "_get_aether_db", return_value=db),
        patch.object(hooks, "_detect_agent_name", return_value="hefesto"),
    ):
        hooks.on_session_start(session_id="native-session", model="model", platform="cli")
        hooks.on_post_tool_call(
            tool_name="write_file",
            args={"path": "/project/file.py"},
            result="ok",
            task_id="task",
            session_id="native-session",
            tool_call_id="call",
            duration_ms=1,
        )
        hooks.on_session_end(
            session_id="native-session",
            completed=True,
            interrupted=False,
            model="model",
            platform="cli",
            result_summary="explicit result",
        )

    assert db.insert_session.call_args.kwargs["session_id"] == "native-session"
    assert db.insert_file_change.call_args.kwargs["session_id"] == "native-session"
    status_call, result_call = db.update_session.call_args_list
    assert status_call.kwargs == {"session_id": "native-session", "status": "completed"}
    assert result_call.kwargs == {"session_id": "native-session", "result_summary": "explicit result"}
    assert db.update_hot_state.call_args.kwargs["last_result"] == "explicit result"


def test_profile_plugins_delegate_to_native_continuity() -> None:
    assert len(PROFILE_PLUGINS) == 6
    for wrapper in PROFILE_PLUGINS:
        content = wrapper.read_text()
        assert "from aether_agents.continuity.hooks import register" in content
        assert "olympus_v3" not in content
