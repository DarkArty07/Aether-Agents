"""Behavioral checks for revision-scoped project knowledge, including native Graphify."""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from aether_agents.knowledge.common import KnowledgeError, stable_lock
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.graphify import GraphifyBackend
from aether_agents.knowledge.snapshots import KnowledgeStore, _sources
from aether_agents.observation.context import ProjectRegistry

PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def git_at(root: Path, *args: str) -> str:
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Knowledge Test",
            "-c",
            "user.email=test@example.invalid",
            *args,
        ],
        text=True,
    ).strip()


def project(tmp_path: Path, identity: str = PROJECT, folder: str = "alpha") -> tuple[Path, Path]:
    root = tmp_path / folder
    (root / ".aether").mkdir(parents=True)
    (root / ".aether/project.toml").write_text(
        f'schema_version = 1\nproject_id = "{identity}"\nname = "example"\n'
        'initialized_by = "1.0.0"\nforge = "local"\ncontract_root = "specs"\n'
    )
    (root / "module.py").write_text("def process_order():\n    return 7\n")
    (root / "README.md").write_text("# Orders\nThis module processes orders.\n")
    git_at(root, "init", "-q")
    git_at(root, "add", ".")
    git_at(root, "commit", "-qm", "fixture")
    state = tmp_path / "state"
    assert ProjectRegistry(state).register(identity, root, "example")
    return root, state


@pytest.fixture
def native_python() -> Path:
    raw = os.environ.get("AETHER_GRAPHIFY_PYTHON")
    if not raw:
        pytest.skip("AETHER_GRAPHIFY_PYTHON identifies the isolated native integration fixture")
    return Path(raw)


def test_binding_rejects_copied_project_and_other_uuid(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    second, _ = project(tmp_path, OTHER, "beta")
    with pytest.raises(KnowledgeError, match="another project"):
        resolve_context(PROJECT, "morfeo", state_root=state, root=second)
    assert resolve_context(PROJECT, "morfeo", state_root=state).root == root
    with pytest.raises(KnowledgeError):
        resolve_context(PROJECT, "administrator", state_root=state)


def test_worktree_verified_against_same_git_common_directory(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    worktree = tmp_path / "parallel work"
    git_at(root, "worktree", "add", "--detach", str(worktree), "HEAD")
    base = resolve_context(PROJECT, "morfeo", state_root=state)
    worker = resolve_context(PROJECT, "implementer", state_root=state, root=worktree)
    assert worker.source_revision == base.source_revision
    assert worker.view_id != base.view_id
    assert worker.root == worktree


def test_capture_excludes_symlinks_runtime_secrets_and_binary(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    (root / "home").mkdir()
    (root / "home/private.py").write_text("SECRET_CANARY = 'private'\n")
    (root / ".env").write_text("API_KEY=PRIVATE_CANARY\n")
    (root / "binary.py").write_bytes(b"binary\0canary")
    (root / "key.py").write_text("key = 'sk-" + "a" * 32 + "'\n")
    (root / "alias.py").symlink_to(root / "module.py")
    git_at(root, "add", ".")
    git_at(root, "commit", "-qm", "excluded inputs")
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    sources, excluded = _sources(ctx)
    assert "module.py" in sources
    assert {"home/private.py", ".env", "binary.py", "key.py", "alias.py"} <= set(excluded)
    assert not any(b"CANARY" in content for content in sources.values())


def test_lock_file_survives_release(tmp_path: Path) -> None:
    lock = tmp_path / "lock"
    with stable_lock(lock):
        inode = lock.stat().st_ino
    assert lock.exists()
    with stable_lock(lock):
        assert lock.stat().st_ino == inode


def test_native_update_query_dedup_and_dirty_state(tmp_path: Path, native_python: Path) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    assert not store.execute(ctx, "status", {})["available"]
    update = store.execute(ctx, "update", {"reason": "Initial map"})
    assert update["outcome"] == "updated"
    assert store.execute(ctx, "update", {"reason": "Already current"})["outcome"] == "unchanged"
    answer = store.execute(ctx, "query", {"question": "process_order"})
    assert "process_order" in answer["content"]
    assert answer["source_revision"] == ctx.source_revision
    (root / "module.py").write_text("def changed_not_committed():\n    return 8\n")
    status = store.execute(ctx, "status", {})
    assert status["freshness"] == "dirty_not_indexed"
    assert "module.py" in status["dirty_paths"]
    graph_answer = store.execute(ctx, "query", {"question": "process_order"})
    assert "process_order" in graph_answer["content"]


def test_three_roles_share_snapshot_without_lost_updates(
    tmp_path: Path, native_python: Path
) -> None:
    _root, state = project(tmp_path)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    contexts = [
        resolve_context(PROJECT, role, state_root=state)
        for role in ("morfeo", "supervisor", "implementer")
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(
            pool.map(
                lambda ctx: store.execute(ctx, "update", {"reason": "Collaborative refresh"}),
                contexts,
            )
        )
    assert sum(r["outcome"] == "updated" for r in results) == 1
    assert len({r["snapshot_id"] for r in results}) == 1


def test_two_projects_same_node_isolation_and_rename(
    tmp_path: Path, native_python: Path, monkeypatch
) -> None:
    a, state = project(tmp_path)
    b, _ = project(tmp_path, OTHER, "beta")
    (b / "module.py").rename(b / "beta_only.py")
    git_at(b, "add", "-A")
    git_at(b, "commit", "-qm", "different project source")
    monkeypatch.setenv("GRAPHIFY_OUT", str(a / "wrong-global-output"))
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    ca = resolve_context(PROJECT, "morfeo", state_root=state)
    cb = resolve_context(OTHER, "morfeo", state_root=state)
    store.execute(ca, "update", {"reason": "A"})
    store.execute(cb, "update", {"reason": "B"})
    assert (
        "beta_only.py" not in store.execute(ca, "query", {"question": "process_order"})["content"]
    )
    assert "beta_only.py" in store.execute(cb, "query", {"question": "process_order"})["content"]
    (a / "module.py").write_text("def replaced_function():\n    return 11\n")
    git_at(a, "add", "-A")
    git_at(a, "commit", "-qm", "new revision")
    newer = resolve_context(PROJECT, "implementer", state_root=state)
    assert not store.execute(newer, "status", {})["available"]
    store.execute(newer, "update", {"reason": "Changed function"})
    assert (
        "replaced_function"
        in store.execute(newer, "query", {"question": "replaced_function"})["content"]
    )
    assert "process_order" in store.execute(ca, "query", {"question": "process_order"})["content"]


def test_corrupt_graph_never_reported_as_current(tmp_path: Path, native_python: Path) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    update = store.execute(ctx, "update", {"reason": "Initial"})
    graph = (
        tmp_path / "cache/knowledge" / PROJECT / update["snapshot_id"] / "graphify-out/graph.json"
    )
    graph.write_text(json.dumps({"nodes": [], "links": []}))
    with pytest.raises(KnowledgeError) as error:
        store.execute(ctx, "query", {"question": "process_order"})
    assert error.value.code == "INDEX_CORRUPT"
