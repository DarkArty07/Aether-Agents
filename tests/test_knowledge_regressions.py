"""Integration regressions for the audited Graphify adaptation boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_project_knowledge_engine import PROJECT, git_at, project
from test_project_knowledge_engine import native_python as native_python
from test_work_memory import payload

from aether_agents.knowledge.common import KnowledgeError, stable_lock
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.graphify import GraphifyBackend
from aether_agents.knowledge.memory import WorkMemoryStore
from aether_agents.knowledge.snapshots import KnowledgeStore


def test_native_markdown_and_all_graph_query_actions(tmp_path: Path, native_python: Path) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    updated = store.execute(ctx, "update", {"reason": "Map code and Markdown"})
    answer = store.execute(ctx, "query", {"question": "Orders"})
    assert "README.md" in answer["content"]
    graph_path = (
        tmp_path / "cache/knowledge" / PROJECT / updated["snapshot_id"] / "graphify-out/graph.json"
    )
    graph = json.loads(graph_path.read_text())
    function = next(node for node in graph["nodes"] if "process_order" in node["label"])
    for action, arguments in (
        ("explain", {"node": function["id"]}),
        ("neighbors", {"node": function["id"]}),
        ("impact", {"node": function["id"]}),
        ("community", {"community_id": 0}),
        ("path", {"source": function["id"], "target": function["id"]}),
    ):
        result = store.execute(ctx, action, arguments)
        assert result["ok"] and result["content"], action
        assert result["snapshot_id"] == updated["snapshot_id"]


def test_divergent_worktrees_never_overwrite_shared_project_revision(
    tmp_path: Path, native_python: Path
) -> None:
    root, state = project(tmp_path)
    other = tmp_path / "other-view"
    git_at(root, "worktree", "add", "--detach", str(other), "HEAD")
    (other / "module.py").write_text("def worker_only_change():\n    return 17\n")
    git_at(other, "add", "module.py")
    git_at(other, "commit", "-qm", "worker revision")
    main = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    worker = resolve_context(PROJECT, "implementer", state_root=state, root=other)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    first = store.execute(main, "update", {"reason": "Main view"})
    second = store.execute(worker, "update", {"reason": "Worker view"})
    assert first["snapshot_id"] != second["snapshot_id"]
    assert first["source_revision"] != second["source_revision"]
    main_answer = store.execute(main, "query", {"question": "process_order"})
    worker_answer = store.execute(worker, "query", {"question": "worker_only_change"})
    assert "process_order" in main_answer["content"]
    assert "worker_only_change" not in main_answer["content"]
    assert "worker_only_change" in worker_answer["content"]
    assert "process_order" not in worker_answer["content"]


def test_failed_new_snapshot_does_not_damage_previous_revision(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = project(tmp_path)
    backend = GraphifyBackend(native_python)
    store = KnowledgeStore(state, tmp_path / "cache", backend)
    old = resolve_context(PROJECT, "supervisor", state_root=state)
    first = store.execute(old, "update", {"reason": "Known good"})
    (root / "module.py").write_text("def next_revision():\n    return 23\n")
    git_at(root, "add", "module.py")
    git_at(root, "commit", "-qm", "next revision")
    new = resolve_context(PROJECT, "supervisor", state_root=state)
    original = backend.run

    def failing(action: str, **kwargs):
        if action == "update":
            raise KnowledgeError("TIMEOUT", "Synthetic build interruption")
        return original(action, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(backend, "run", failing)
        with pytest.raises(KnowledgeError, match="Synthetic build interruption"):
            store.execute(new, "update", {"reason": "Interrupted candidate"})
    assert not store.execute(new, "status", {})["available"]
    old_answer = store.execute(old, "query", {"question": "process_order"})
    assert old_answer["snapshot_id"] == first["snapshot_id"]
    assert "process_order" in old_answer["content"]


def test_published_graph_parent_cannot_be_replaced_by_alias(
    tmp_path: Path, native_python: Path
) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    built = store.execute(ctx, "update", {"reason": "Safe graph"})
    location = tmp_path / "cache/knowledge" / PROJECT / built["snapshot_id"]
    destination = tmp_path / "redirected-output"
    (location / "graphify-out").rename(destination)
    (location / "graphify-out").symlink_to(destination, target_is_directory=True)
    # No result may escape a redirected parent, even with unchanged graph bytes.
    with pytest.raises((KnowledgeError, OSError, ValueError)):
        store.execute(ctx, "query", {"question": "process_order"})


def test_role_notes_revalidate_uncommitted_source_changes(
    tmp_path: Path, native_python: Path
) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    memory = WorkMemoryStore(state, native_python)
    saved = memory.execute(ctx, "save", payload("Validate the order contract."))
    assert (
        memory.execute(ctx, "read", {"note_id": saved["note_id"]})["freshness"] == "same_revision"
    )
    (root / "module.py").write_text("def changed():\n    return 99\n")
    assert memory.execute(ctx, "read", {"note_id": saved["note_id"]})["freshness"] == "revalidate"
    found = memory.execute(ctx, "search", {"query": "order contract"})
    assert found["matches"][0]["freshness"] == "revalidate"


def test_reflection_uses_replacement_solution_not_just_correction_reason(
    tmp_path: Path, native_python: Path
) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "supervisor", state_root=state)
    memory = WorkMemoryStore(state, native_python)
    note = memory.execute(ctx, "save", payload("OLD_SOLUTION_SENTINEL"))
    memory.execute(
        ctx,
        "correct",
        {
            "note_id": note["note_id"],
            "expected_revision": 1,
            "reason": "The earlier attempt used the wrong interface.",
            "replacement": {
                "lesson": "NEW_SOLUTION_SENTINEL is the corrected procedure.",
                "applicability": "This component only.",
            },
            "evidence": [],
        },
    )
    reflection = memory.execute(ctx, "reflect", {})
    assert reflection["count"] == 1
    assert "NEW_SOLUTION_SENTINEL" in reflection["content"]
    assert "OLD_SOLUTION_SENTINEL" not in reflection["content"]
    assert not list(tmp_path.rglob(".graphify_learning.json"))


def test_native_reflection_request_preserves_utf8_without_ascii_expansion(
    native_python: Path,
) -> None:
    note = (
        '---\ntype: "query"\ndate: "2026-09-05"\nquestion: "Unicode result"\n'
        'outcome: "useful"\nsource_nodes: ["Component"]\n---\n\n' + "\U0001f4bb" * 200_000
    )
    result = GraphifyBackend(native_python).run("memory_reflect", arguments={"notes": [note]})
    assert result["count"] == 1


def test_component_rejects_oversized_request_before_execution() -> None:
    with pytest.raises(KnowledgeError) as failure:
        GraphifyBackend(Path(sys.executable)).run("probe", arguments={"text": "x" * 2_000_001})
    assert failure.value.code == "SCOPE_UNAVAILABLE"


def test_stable_lock_excludes_another_process_and_retains_its_inode(tmp_path: Path) -> None:
    lock = tmp_path / "update.lock"
    child = (
        "from pathlib import Path; import sys; "
        "from aether_agents.knowledge.common import stable_lock; "
        "lock = stable_lock(Path(sys.argv[1]), timeout=0.05); "
        "lock.__enter__(); lock.__exit__(None, None, None)"
    )
    with stable_lock(lock):
        inode = lock.stat().st_ino
        blocked = subprocess.run(
            [sys.executable, "-c", child, str(lock)], capture_output=True, text=True, timeout=10
        )
        assert blocked.returncode != 0
        assert "Another knowledge update is in progress" in blocked.stderr
    acquired = subprocess.run(
        [sys.executable, "-c", child, str(lock)], capture_output=True, text=True, timeout=10
    )
    assert acquired.returncode == 0, acquired.stderr
    assert lock.stat().st_ino == inode
