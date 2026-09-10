"""Native-evidence classification for exact-session knowledge bindings (TS-373).

The matrix pins the classification decided before precedence: absent, empty and
ordinary non-Git native workspaces fall through to the exact-session explicit binding,
while a usable native project checkout, an ancestor subdirectory and an attached
worktree resolve through Git. Missing, malformed, contradictory, unregistered and
unreadable evidence keeps failing closed instead of being treated as absent.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from test_project_knowledge_engine import OTHER, PROJECT, git_at, project

from aether_agents.knowledge import bindings
from aether_agents.knowledge.bindings import bind_session, context_for_session
from aether_agents.knowledge.common import KnowledgeError, atomic_json
from aether_agents.knowledge.context import resolve_context

SESSION = "exact-session"


def native_home(tmp_path: Path, cwd: str | None) -> Path:
    """Build one native Hermes home whose exact session row records ``cwd``."""
    home = tmp_path / "native-home"
    home.mkdir(exist_ok=True)
    with sqlite3.connect(home / "state.db") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, cwd TEXT)")
        connection.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?)", (SESSION, cwd))
    return home


def plain_directory(tmp_path: Path) -> Path:
    plain = tmp_path / "operator-notes"
    plain.mkdir(exist_ok=True)
    return plain


@pytest.mark.parametrize("kind", ["null", "empty", "plain-directory"])
def test_explicit_binding_resolves_for_ordinary_native_workspace(tmp_path: Path, kind: str) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    cwd = {"null": None, "empty": "", "plain-directory": str(plain_directory(tmp_path))}[kind]
    context = context_for_session(state, "morfeo", SESSION, hermes_home=native_home(tmp_path, cwd))
    assert context.project_id == PROJECT
    assert context.root == root
    assert context.session_id == SESSION


def test_native_project_workspace_still_resolves_without_binding(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    context = context_for_session(
        state, "morfeo", SESSION, hermes_home=native_home(tmp_path, str(root))
    )
    assert context.project_id == PROJECT
    assert context.root == root


def test_native_subdirectory_resolves_the_registered_root(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    nested = root / "package" / "inner"
    nested.mkdir(parents=True)
    context = context_for_session(
        state, "implementer", SESSION, hermes_home=native_home(tmp_path, str(nested))
    )
    assert context.project_id == PROJECT
    assert context.root == root


def test_native_attached_worktree_resolves_its_own_view(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    worktree = tmp_path / "attached worktree"
    git_at(root, "worktree", "add", "--detach", str(worktree), "HEAD")
    context = context_for_session(
        state, "implementer", SESSION, hermes_home=native_home(tmp_path, str(worktree))
    )
    primary = resolve_context(PROJECT, "morfeo", state_root=state)
    assert context.project_id == PROJECT
    assert context.root == worktree
    assert context.source_revision == primary.source_revision
    assert context.view_id != primary.view_id


@pytest.mark.parametrize("kind", ["null", "empty", "plain-directory"])
def test_ordinary_native_workspace_without_binding_stays_unresolved(
    tmp_path: Path, kind: str
) -> None:
    _root, state = project(tmp_path)
    cwd = {"null": None, "empty": "", "plain-directory": str(plain_directory(tmp_path))}[kind]
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=native_home(tmp_path, cwd))
    assert failure.value.code == "PROJECT_UNRESOLVED"


@pytest.mark.parametrize("kind", ["null", "empty", "plain-directory"])
def test_binding_of_another_session_is_never_reused(tmp_path: Path, kind: str) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", "bound-session", root=root)
    cwd = {"null": None, "empty": "", "plain-directory": str(plain_directory(tmp_path))}[kind]
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=native_home(tmp_path, cwd))
    assert failure.value.code == "PROJECT_UNRESOLVED"


def test_binding_of_another_role_is_never_reused(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    home = native_home(tmp_path, str(plain_directory(tmp_path)))
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "supervisor", SESSION, hermes_home=home)
    assert failure.value.code == "PROJECT_UNRESOLVED"


def test_usable_native_project_conflicting_with_binding_is_rejected(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    other, _ = project(tmp_path, OTHER, "beta")
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=native_home(tmp_path, str(other)))
    assert failure.value.code == "PROJECT_CONFLICT"


@pytest.mark.parametrize("kind", ["empty-git-directory", "broken-git-metadata"])
def test_malformed_git_metadata_never_falls_back(tmp_path: Path, kind: str) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    broken = tmp_path / kind
    broken.mkdir()
    if kind == "empty-git-directory":
        (broken / ".git").mkdir()
    else:
        (broken / ".git").write_text("gitdir: /nonexistent/git-directory\n")
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(
            state, "morfeo", SESSION, hermes_home=native_home(tmp_path, str(broken))
        )
    assert failure.value.code == "VIEW_MISMATCH"


def test_malformed_project_marker_never_falls_back(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    (root / ".aether/project.toml").write_text('schema_version = 1\nproject_id = "not-a-uuid"\n')
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=native_home(tmp_path, str(root)))
    assert failure.value.code == "PROJECT_UNRESOLVED"


def test_bare_repository_workspace_never_falls_back(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    bare = tmp_path / "bare-repository.git"
    bare.mkdir()
    git_at(bare, "init", "--bare", "-q")
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=native_home(tmp_path, str(bare)))
    assert failure.value.code == "VIEW_MISMATCH"


def test_copied_unregistered_checkout_never_falls_back(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    copied = tmp_path / "copied-checkout"
    shutil.copytree(root, copied)
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(
            state, "morfeo", SESSION, hermes_home=native_home(tmp_path, str(copied))
        )
    assert failure.value.code == "VIEW_MISMATCH"


def test_missing_native_workspace_path_never_falls_back(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    home = native_home(tmp_path, str(tmp_path / "removed-directory"))
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=home)
    assert failure.value.code == "VIEW_MISMATCH"


def test_relative_native_workspace_never_falls_back(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    home = native_home(tmp_path, "relative/workspace")
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=home)
    assert failure.value.code == "VIEW_MISMATCH"


@pytest.mark.parametrize("kind", ["not-a-database", "missing-sessions-table"])
def test_unreadable_native_evidence_never_falls_back(tmp_path: Path, kind: str) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    home = tmp_path / "native-home"
    home.mkdir()
    if kind == "not-a-database":
        (home / "state.db").write_bytes(b"not a sqlite database\n")
    else:
        with sqlite3.connect(home / "state.db") as connection:
            connection.execute("CREATE TABLE unrelated (id TEXT PRIMARY KEY)")
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=home)
    assert failure.value.code == "PROJECT_UNRESOLVED"


def test_missing_native_state_database_stays_unresolved(tmp_path: Path) -> None:
    _root, state = project(tmp_path)
    home = tmp_path / "native-home"
    home.mkdir()
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=home)
    assert failure.value.code == "PROJECT_UNRESOLVED"


def test_corrupted_explicit_binding_payload_stays_rejected(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    binding = next(path for path in state.rglob("*.json") if "session_id" in path.read_text())
    record = json.loads(binding.read_text())
    record["session_id"] = "another-session"
    atomic_json(binding, record)
    home = native_home(tmp_path, str(plain_directory(tmp_path)))
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=home)
    assert failure.value.code == "PROJECT_CONFLICT"


def test_unclear_git_probe_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)

    def unusable(*_args: object, **_kwargs: object) -> object:
        raise OSError("git is unavailable")

    monkeypatch.setattr(bindings.subprocess, "run", unusable)
    home = native_home(tmp_path, str(plain_directory(tmp_path)))
    with pytest.raises(KnowledgeError) as failure:
        context_for_session(state, "morfeo", SESSION, hermes_home=home)
    assert failure.value.code == "VIEW_MISMATCH"


def test_isolated_native_tool_resolves_plain_cwd_explicit_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real tool boundary in a disposable lab home for the reported TS-373 scenario."""
    pytest.importorskip("hermes_cli.plugins")
    graphify = os.environ.get("AETHER_GRAPHIFY_PYTHON")
    if not graphify:
        pytest.skip("AETHER_GRAPHIFY_PYTHON identifies the isolated native component fixture")

    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
    from tools.registry import registry

    from aether_agents.knowledge.component import configure
    from aether_agents.knowledge.hermes_plugin import register
    from aether_agents.knowledge.service import KnowledgeService
    from aether_agents.lab import isolated_hermes_env

    root, state = project(tmp_path)
    bind_session(state, PROJECT, "morfeo", SESSION, root=root)
    plain = plain_directory(tmp_path)
    lab_root = tmp_path / "isolated-lab"
    hermes_home = lab_root / "profiles" / "morfeo"
    hermes_home.mkdir(parents=True)
    with sqlite3.connect(hermes_home / "state.db") as connection:
        connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)")
        connection.execute("INSERT INTO sessions VALUES (?, ?)", (SESSION, str(plain)))
    import yaml

    (hermes_home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "plugins": {
                    "entries": {
                        "aether-project-knowledge": {
                            "settings": {
                                "enabled": True,
                                "state_root": str(state),
                                "cache_root": str(tmp_path / "cache"),
                            }
                        }
                    }
                }
            }
        )
    )
    for name, value in isolated_hermes_env(lab_root, hermes_home, Path(sys.executable)).items():
        monkeypatch.setenv(name, value)
    assert os.environ["HERMES_HOME"] == str(hermes_home)
    assert os.environ["HERMES_KANBAN_DB"] == str(lab_root / "kanban.db")
    configure(KnowledgeService(state, tmp_path / "cache"), Path(graphify))

    manager = PluginManager(scope_key=str(hermes_home))
    manifest = PluginManifest(
        name="aether-project-knowledge", key="aether-project-knowledge", source="entrypoint"
    )
    context = PluginContext(manifest, manager)
    assert context.profile_name == "morfeo"
    register(context)
    try:
        knowledge = registry.get_entry("project_knowledge", scope=manager.scope_key)
        memory = registry.get_entry("work_memory", scope=manager.scope_key)
        assert knowledge is not None and memory is not None
        status = json.loads(knowledge.handler({"action": "status"}, session_id=SESSION))
        assert status["ok"] and status["project_id"] == PROJECT
        assert status["view_id"] == resolve_context(PROJECT, "morfeo", state_root=state).view_id
        update = json.loads(
            knowledge.handler(
                {"action": "update", "reason": "TS-373 isolated native resolution"},
                session_id=SESSION,
            )
        )
        assert update["outcome"] == "updated"
        answer = json.loads(
            knowledge.handler({"action": "query", "question": "process_order"}, session_id=SESSION)
        )
        assert "process_order" in answer["content"]
        saved = json.loads(
            memory.handler(
                {
                    "action": "save",
                    "idempotency_key": "ts-373-isolated-native",
                    "situation": "Native session whose recorded cwd is not a Git checkout.",
                    "lesson": "The exact-session explicit binding still identifies the project.",
                    "applicability": "Isolated TS-373 verification fixture.",
                    "outcome": "useful",
                    "evidence": [],
                },
                session_id=SESSION,
            )
        )
        assert saved["ok"] and saved["project_id"] == PROJECT
        read = json.loads(
            memory.handler({"action": "read", "note_id": saved["note_id"]}, session_id=SESSION)
        )
        assert read["revision"] == saved["revision"]
        assert "explicit binding" in read["content"]
        assert not (lab_root / "kanban.db").exists()
    finally:
        assert manager.unload(manifest)
