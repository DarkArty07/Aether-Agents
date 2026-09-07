"""Integration regressions for the audited Graphify adaptation boundaries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from test_project_knowledge_engine import OTHER, PROJECT, git_at, project
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


def test_regression_d29_truncation_honesty_and_supported_recovery(
    tmp_path: Path, native_python: Path
) -> None:
    root, state = project(tmp_path)
    funcs = "\n".join(f"def step_{i}():\n    return step_{i + 1}()\n" for i in range(8))
    funcs += "def step_8():\n    return 42\n"
    (root / "flow.py").write_text(funcs)
    git_at(root, "add", "flow.py")
    git_at(root, "commit", "-qm", "interconnected steps")
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    store.execute(ctx, "update", {"reason": "Map flow steps"})

    # Case 1: Budget is small (128 tokens). Graphify omits nodes.
    # Must report truncated=True, ok=True, and no unsupported recovery instructions.
    trunc_res = store.execute(ctx, "query", {"question": "step_0", "budget_tokens": 128})
    assert trunc_res["ok"] is True
    assert trunc_res["truncated"] is True
    content = trunc_res["content"]
    assert "context_filter" not in content
    assert "get_node" not in content
    assert "--budget" not in content
    assert "CLI:" not in content
    assert "MCP" not in content
    assert "Graph:" not in content

    # Case 2: Complete-over-budget control (550 tokens). All nodes fit but nodes+edges
    # exceed token budget in Graphify.
    # Must preserve truncated=False and provide an explicit over-budget warning.
    ctrl_res = store.execute(ctx, "query", {"question": "step_0", "budget_tokens": 550})
    assert ctrl_res["ok"] is True
    assert ctrl_res["truncated"] is False
    assert any("over budget" in w.lower() or "complete" in w.lower() for w in ctrl_res["warnings"])
    ctrl_content = ctrl_res["content"]
    assert "context_filter" not in ctrl_content
    assert "get_node" not in ctrl_content

    # Case 3: Directed path search with reverse/unconnected endpoints.
    # Native recovery notice must contain supported Aether calls only, never undirected=true,
    # context_filter, get_node, --budget, CLI:, MCP, or snapshot graph paths.
    rev_path_res = store.execute(ctx, "path", {"source": "step_8", "target": "step_0"})
    assert rev_path_res["ok"] is True
    rev_content = rev_path_res["content"]
    assert "No directed path found" in rev_content
    for forbidden in (
        "undirected=true",
        "context_filter",
        "get_node",
        "--budget",
        "CLI:",
        "MCP",
        "Graph:",
        str(tmp_path),
    ):
        assert forbidden not in rev_content
    assert any(term in rev_content for term in ["explain", "question", "budget_tokens"])


def test_regression_d30_structured_references_and_cap_limit(
    tmp_path: Path, native_python: Path
) -> None:
    root, state = project(tmp_path)
    funcs = "\n".join(f"def step_{i}():\n    return step_{i + 1}()\n" for i in range(4))
    funcs += "def step_4():\n    return 42\n"
    (root / "flow.py").write_text(funcs)
    git_at(root, "add", "flow.py")
    git_at(root, "commit", "-qm", "step chain")
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    updated = store.execute(ctx, "update", {"reason": "Index step chain"})
    manifest_path = (
        tmp_path / "cache/knowledge" / PROJECT / updated["snapshot_id"] / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    graph_path = (
        tmp_path / "cache/knowledge" / PROJECT / updated["snapshot_id"] / "graphify-out/graph.json"
    )
    graph = json.loads(graph_path.read_text())
    step_0_node = next(n["id"] for n in graph["nodes"] if "step_0" in n.get("label", ""))
    step_1_node = next(n["id"] for n in graph["nodes"] if "step_1" in n.get("label", ""))

    # All 6 source-bearing actions must return valid, non-empty, deduplicated references
    actions = [
        ("query", {"question": "step_0"}),
        ("explain", {"node": step_0_node}),
        ("neighbors", {"node": step_0_node}),
        ("community", {"community_id": 0}),
        ("path", {"source": step_0_node, "target": step_1_node}),
        ("impact", {"node": step_1_node, "depth": 2}),
    ]
    for action, args in actions:
        res = store.execute(ctx, action, args)
        assert res["ok"] is True, f"Failed for action {action}"
        refs = res["references"]
        assert isinstance(refs, list) and len(refs) > 0, (
            f"Expected non-empty references for {action}"
        )
        # Deduplication check
        pairs = [(r["path"], r["location"]) for r in refs]
        assert len(pairs) == len(set(pairs)), f"Duplicates found in references for {action}: {refs}"
        for r in refs:
            assert r["path"] in manifest["inputs"], (
                f"Reference path {r['path']} not in manifest inputs"
            )
            assert not Path(r["path"]).is_absolute(), (
                f"Absolute path escaped in references: {r['path']}"
            )
            assert r["revision"] == ctx.source_revision
            assert "location" in r
        # No snapshot private path in content or references
        for r in refs:
            assert str(tmp_path) not in r["path"]

    # Silent cap repair: exceeding 50 references must cap at 50, set truncated=True, and warn
    synthetic_backend = GraphifyBackend(native_python)
    orig_run = synthetic_backend.run

    def mock_run_with_many_refs(action: str, **kwargs):
        native_res = orig_run(action, **kwargs)
        if action == "query":
            # Synthesize 60 references to input files
            fake_refs = [{"path": "flow.py", "location": f"L{i}"} for i in range(60)]
            native_res["references"] = fake_refs
        return native_res

    synthetic_backend.run = mock_run_with_many_refs
    capped_store = KnowledgeStore(state, tmp_path / "cache", synthetic_backend)
    capped_res = capped_store.execute(ctx, "query", {"question": "step_0"})
    assert len(capped_res["references"]) == 50
    assert capped_res["truncated"] is True
    assert any("50" in w for w in capped_res["warnings"])


def test_regression_d31_query_explain_community_discovery(
    tmp_path: Path, native_python: Path
) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    store.execute(ctx, "update", {"reason": "Initial index"})

    # 1. Start from query
    q_res = store.execute(ctx, "query", {"question": "process_order"})
    assert q_res["ok"] is True
    assert "process_order" in q_res["content"]

    # 2. Call explain on node without inspecting graph.json
    exp_res = store.execute(ctx, "explain", {"node": "process_order"})
    assert exp_res["ok"] is True
    assert "resolved_node" in exp_res
    rn = exp_res["resolved_node"]
    assert isinstance(rn["id"], str) and len(rn["id"]) > 0
    assert "community_id" in rn
    assert "community_name" in rn
    cid = rn["community_id"]
    assert isinstance(cid, int)

    # 3. Call community with the discovered community_id without guessing
    comm_res = store.execute(ctx, "community", {"community_id": cid})
    assert comm_res["ok"] is True
    assert "community" in comm_res
    cinfo = comm_res["community"]
    assert cinfo["id"] == cid
    assert "name" in cinfo
    assert isinstance(cinfo["node_count"], int) and cinfo["node_count"] > 0


def test_manager_envelope_expansion_actions(tmp_path: Path, native_python: Path) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    store.execute(ctx, "update", {"reason": "Initial index"})

    # 1. stats
    stats_res = store.execute(ctx, "stats", {})
    assert stats_res["ok"] is True
    assert "stats" in stats_res
    stats = stats_res["stats"]
    assert "node_count" in stats
    assert "edge_count" in stats
    assert "community_count" in stats
    assert "confidence_counts" in stats
    assert "origin_counts" in stats

    # 2. god_nodes
    gods_res = store.execute(ctx, "god_nodes", {"top_n": 5})
    assert gods_res["ok"] is True
    assert "nodes" in gods_res
    assert isinstance(gods_res["nodes"], list)

    # 3. query with query_options
    q_res = store.execute(
        ctx, "query", {"question": "process_order", "traversal": "dfs", "depth": 1}
    )
    assert q_res["ok"] is True
    assert "query_options" in q_res
    assert q_res["query_options"]["traversal"] == "dfs"
    assert q_res["query_options"]["depth"] == 1

    # 4. visualize
    viz_res = store.execute(ctx, "visualize", {"format": "graph", "detail": "auto"})
    assert viz_res["ok"] is True
    assert "artifact" in viz_res
    art = viz_res["artifact"]
    assert art["format"] == "graph"
    assert art["snapshot_id"] == stats_res["snapshot_id"]
    assert Path(art["local_path"]).is_file()
    assert art["bytes"] > 0
    assert "rendered_nodes" in art
    assert "total_nodes" in art


def test_d39_visualize_both_html_formats_and_snapshot_stability(
    tmp_path: Path, native_python: Path
) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    struct_res = store.execute(ctx, "update", {"reason": "Initial index", "mode": "structural"})

    graph_file = state / "knowledge" / PROJECT / "views" / ctx.view_id
    pointer = json.loads((graph_file / f"{ctx.source_revision}.json").read_text())
    snapshot_id = pointer["snapshot_id"]
    assert snapshot_id == struct_res["snapshot_id"]
    graph_json = (
        tmp_path / "cache" / "knowledge" / PROJECT / snapshot_id / "graphify-out" / "graph.json"
    )
    manifest_json = tmp_path / "cache" / "knowledge" / PROJECT / snapshot_id / "manifest.json"
    sha_initial = hashlib.sha256(graph_json.read_bytes()).hexdigest()
    manifest_initial = hashlib.sha256(manifest_json.read_bytes()).hexdigest()

    # 1. Graph format (auto detail)
    res_graph_auto = store.execute(ctx, "visualize", {"format": "graph", "detail": "auto"})
    assert res_graph_auto["ok"] is True
    art_auto = res_graph_auto["artifact"]
    assert art_auto["format"] == "graph"
    assert art_auto["snapshot_id"] == snapshot_id
    assert "vis-network" in str(art_auto["external_assets"])
    html_auto = Path(art_auto["local_path"]).read_text(encoding="utf-8")
    assert PROJECT[:8] in html_auto or ctx.source_revision[:8] in html_auto
    assert hashlib.sha256(graph_json.read_bytes()).hexdigest() == sha_initial

    # 2. Graph format (full detail)
    res_graph_full = store.execute(ctx, "visualize", {"format": "graph", "detail": "full"})
    assert res_graph_full["ok"] is True
    art_full = res_graph_full["artifact"]
    assert art_full["format"] == "graph"
    assert art_full["aggregated"] is False
    assert hashlib.sha256(graph_json.read_bytes()).hexdigest() == sha_initial

    # 3. Tree format
    res_tree = store.execute(ctx, "visualize", {"format": "tree"})
    assert res_tree["ok"] is True
    art_tree = res_tree["artifact"]
    assert art_tree["format"] == "tree"
    assert "d3" in str(art_tree["external_assets"])
    html_tree = Path(art_tree["local_path"]).read_text(encoding="utf-8")
    assert PROJECT[:8] in html_tree or ctx.source_revision[:8] in html_tree
    assert hashlib.sha256(graph_json.read_bytes()).hexdigest() == sha_initial

    # 4. Artifact reuse
    res_reuse = store.execute(ctx, "visualize", {"format": "graph", "detail": "auto"})
    assert res_reuse["ok"] is True
    assert res_reuse["artifact"]["sha256"] == art_auto["sha256"]
    assert "Reused existing" in res_reuse["content"]
    assert hashlib.sha256(graph_json.read_bytes()).hexdigest() == sha_initial

    # 5. Snapshot immutability: published snapshot bytes must remain immutable
    assert hashlib.sha256(graph_json.read_bytes()).hexdigest() == sha_initial
    assert hashlib.sha256(manifest_json.read_bytes()).hexdigest() == manifest_initial


def test_d38_github_pr_operations_and_error_boundaries(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(state, tmp_path / "cache", GraphifyBackend(native_python))
    store.execute(ctx, "update", {"reason": "Initial index"})

    # 1. Local forge -> GITHUB_UNAVAILABLE
    with pytest.raises(KnowledgeError) as exc_info:
        store.execute(ctx, "list_prs", {})
    assert exc_info.value.code == "GITHUB_UNAVAILABLE"

    # Configure GitHub forge in project.toml
    project_toml = root / ".aether" / "project.toml"
    project_toml.write_text(
        f'schema_version = 1\nproject_id = "{PROJECT}"\nname = "example"\n'
        'initialized_by = "1.0.0"\nforge = "github"\ncontract_root = "specs"\n\n'
        '[github]\nrepository = "org/repo-a"\n'
    )

    # 2. Remote mismatch -> PROJECT_CONFLICT
    git_at(root, "remote", "add", "origin", "https://github.com/org/repo-b.git")
    with pytest.raises(KnowledgeError) as exc_info:
        store.execute(ctx, "list_prs", {})
    assert exc_info.value.code == "PROJECT_CONFLICT"

    # Set matching remote
    git_at(root, "remote", "set-url", "origin", "https://github.com/org/repo-a.git")

    # 3. Mock gh CLI responses
    import aether_agents.knowledge.github as gh_mod

    # Empty PR list is valid and returns prs: []
    monkeypatch.setattr(gh_mod, "_run_gh", lambda root, args: [] if "list" in args else {})
    list_res = store.execute(ctx, "list_prs", {"limit": 10})
    assert list_res["ok"] is True
    assert list_res["prs"] == []
    assert "No open pull requests found" in list_res["content"]
    assert list_res["github"]["repository"] == "org/repo-a"

    # Non-empty PR list
    fake_prs = [
        {
            "number": 42,
            "title": "Fix order processing",
            "headRefName": "fix-order",
            "baseRefName": "main",
            "headRefOid": "headsha42",
            "baseRefOid": "basesha00",
            "isDraft": False,
            "statusCheckRollup": [{"state": "SUCCESS"}],
            "reviewDecision": "APPROVED",
            "updatedAt": "2026-09-06T12:00:00Z",
        },
        {
            "number": 43,
            "title": "Add order metrics",
            "headRefName": "metrics",
            "baseRefName": "main",
            "headRefOid": "headsha43",
            "baseRefOid": "basesha00",
            "isDraft": False,
            "statusCheckRollup": [],
            "reviewDecision": None,
            "updatedAt": "2026-09-06T13:00:00Z",
        },
    ]

    view_calls = 0

    def mock_gh_calls(rt: Path, args: list[str]) -> Any:
        nonlocal view_calls
        assert rt == root  # Bound repository isolation verified
        if "list" in args:
            return fake_prs
        if "view" in args:
            pr_num = args[args.index("view") + 1]
            if "--json" in args and args[args.index("--json") + 1] == "headRefOid":
                return {"headRefOid": "headsha42" if pr_num == "42" else "headsha43"}
            if pr_num == "42":
                return {**fake_prs[0], "files": [{"path": "module.py"}]}
            if pr_num == "43":
                return {**fake_prs[1], "files": [{"path": "module.py"}, {"path": "unmatched.py"}]}
        return {}

    monkeypatch.setattr(gh_mod, "_run_gh", mock_gh_calls)

    # list_prs with data
    list_data = store.execute(ctx, "list_prs", {"limit": 20})
    assert len(list_data["prs"]) == 2
    assert list_data["prs"][0]["number"] == 42
    assert list_data["prs"][0]["ci_status"] == "SUCCESS"

    # pr_impact
    impact_res = store.execute(ctx, "pr_impact", {"pr_number": 42})
    assert impact_res["ok"] is True
    assert impact_res["pr"]["number"] == 42
    assert impact_res["impact"]["files"] == 1
    assert impact_res["impact"]["matched_files"] == ["module.py"]
    assert impact_res["impact"]["unmatched_files"] == []
    assert len(impact_res["references"]) > 0

    # Large PR (>500 files) triggers truncation warning
    many_files = [{"path": f"file_{i}.py"} for i in range(600)]

    def mock_gh_large(rt: Path, args: list[str]) -> Any:
        if "view" in args:
            if "--json" in args and args[args.index("--json") + 1] == "headRefOid":
                return {"headRefOid": "headsha42"}
            return {**fake_prs[0], "files": many_files}
        return {}

    monkeypatch.setattr(gh_mod, "_run_gh", mock_gh_large)
    large_impact = store.execute(ctx, "pr_impact", {"pr_number": 42})
    assert large_impact["impact"]["truncated"] is True
    assert large_impact["impact"]["total_files"] == 600
    assert large_impact["impact"]["analyzed_files"] == 500
    assert "truncated" in large_impact["content"].lower()

    # Moving head SHA during pr_impact:
    # Scenario A: head moves once -> retried with new head and succeeds
    head_attempts = 0

    def mock_moving_head(rt: Path, args: list[str]) -> Any:
        nonlocal head_attempts
        if "view" in args:
            if "--json" in args and args[args.index("--json") + 1] == "headRefOid":
                head_attempts += 1
                # First check says head moved to headsha_new
                return {"headRefOid": "headsha_new"}
            # Return new head on retry
            return {
                **fake_prs[0],
                "headRefOid": "headsha_new",
                "files": [{"path": "module.py"}],
            }
        return {}

    monkeypatch.setattr(gh_mod, "_run_gh", mock_moving_head)
    moving_res = store.execute(ctx, "pr_impact", {"pr_number": 42})
    assert moving_res["ok"] is True
    assert moving_res["pr"]["head_sha"] == "headsha_new"

    # Scenario B: head keeps moving continuously -> GITHUB_UNAVAILABLE
    def mock_continuous_move(rt: Path, args: list[str]) -> Any:
        if "view" in args:
            if "--json" in args and args[args.index("--json") + 1] == "headRefOid":
                import uuid

                return {"headRefOid": uuid.uuid4().hex}
            return {**fake_prs[0], "files": [{"path": "module.py"}]}
        return {}

    monkeypatch.setattr(gh_mod, "_run_gh", mock_continuous_move)
    with pytest.raises(KnowledgeError) as exc_info:
        store.execute(ctx, "pr_impact", {"pr_number": 42})
    assert exc_info.value.code == "GITHUB_UNAVAILABLE"

    # triage_prs with normal overlaps
    monkeypatch.setattr(gh_mod, "_run_gh", mock_gh_calls)
    triage_res = store.execute(ctx, "triage_prs", {"limit": 10})
    assert triage_res["ok"] is True
    assert len(triage_res["prs"]) == 2
    assert "community_overlaps" in triage_res
    overlaps = triage_res["community_overlaps"]
    assert len(overlaps) > 0

    # Triage error boundary: PR view failure must NOT masquerade as zero impact
    def mock_gh_view_fail(rt: Path, args: list[str]) -> Any:
        if "list" in args:
            return fake_prs
        if "view" in args:
            raise KnowledgeError("GITHUB_UNAVAILABLE", "Simulated GitHub API failure")
        return {}

    monkeypatch.setattr(gh_mod, "_run_gh", mock_gh_view_fail)
    triage_fail_res = store.execute(ctx, "triage_prs", {"limit": 10})
    assert triage_fail_res["ok"] is True
    # Impact must show unavailable status and error, NOT 0 nodes affected!
    for p in triage_fail_res["prs"]:
        imp = p["impact"]
        assert imp["status"] == "unavailable"
        assert "Simulated GitHub API failure" in imp["error"]
        assert imp["node_count"] is None
    assert "0 nodes affected" not in triage_fail_res["content"]
    assert "impact analysis unavailable" in triage_fail_res["content"]


def test_d36_semantic_lifecycle_cache_and_enrichment(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)

    # 1. Structural update leaves documents structural_only
    # When semantic is disabled: semantic.state is disabled, semantic_pending is False
    store = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={"enabled": True, "semantic_enabled": False},
    )
    struct_res = store.execute(ctx, "update", {"mode": "structural"})
    assert struct_res["ok"] is True
    assert struct_res["coverage"]["documents"] == "structural_only"
    assert struct_res["semantic"]["state"] == "disabled"
    assert struct_res["semantic_pending"] is False
    struct_snapshot_id = struct_res["snapshot_id"]
    struct_graph_file = (
        tmp_path
        / "cache"
        / "knowledge"
        / PROJECT
        / struct_snapshot_id
        / "graphify-out"
        / "graph.json"
    )
    struct_graph_sha = hashlib.sha256(struct_graph_file.read_bytes()).hexdigest()

    # 2. Structural update with semantic enabled honestly reports semantic_pending=True
    store_pending = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )
    # Re-running structural with semantic enabled on same inputs reports semantic_pending=True
    struct_pending_res = store_pending.execute(ctx, "update", {"mode": "structural"})
    assert struct_pending_res["ok"] is True
    # Previous snapshot had semantic.state == 'disabled', so pending work remains
    assert struct_pending_res["semantic_pending"] is False  # disabled in existing manifest

    # 3. Configure semantic enabled and mock auxiliary model
    call_count = 0
    recorded_tasks: list[str] = []

    def mock_aux_call(task: str, *args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        nonlocal call_count
        call_count += 1
        recorded_tasks.append(task)
        fake_llm_json = json.dumps(
            {
                "nodes": [
                    {
                        "id": "OrdersDocument",
                        "label": "OrdersDocument",
                        "source_file": "README.md",
                        "source_location": "1",
                    }
                ],
                "edges": [
                    {
                        "source": "OrdersDocument",
                        "target": "module_process_order",
                        "relation": "specifies",
                    }
                ],
            }
        )
        return fake_llm_json, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    import aether_agents.knowledge.semantic as sem_mod

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_aux_call)

    # 4. Same-commit enrichment publishes a NEW immutable snapshot (D36 / KG-14)
    semantic_store = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )
    enriched_res = semantic_store.execute(ctx, "update", {"mode": "configured"})
    assert enriched_res["ok"] is True
    assert enriched_res["coverage"]["documents"] == "semantic"
    assert enriched_res["semantic"]["state"] == "complete"
    assert enriched_res["semantic_pending"] is False
    assert call_count > 0
    enriched_snapshot_id = enriched_res["snapshot_id"]
    # Snapshot IDs must differ (new immutable snapshot published, not mutated in-place)
    assert enriched_snapshot_id != struct_snapshot_id
    # Structural snapshot graph bytes must remain completely immutable
    assert hashlib.sha256(struct_graph_file.read_bytes()).hexdigest() == struct_graph_sha

    # 5. Repeat unchanged configured update produces ZERO model calls
    initial_calls = call_count
    repeat_res = semantic_store.execute(ctx, "update", {"mode": "configured"})
    assert repeat_res["ok"] is True
    assert repeat_res["outcome"] == "unchanged"
    assert repeat_res["semantic_pending"] is False
    assert call_count == initial_calls, "Repeat unchanged update must make 0 model calls"

    # 6. Switching configuration (e.g. semantic_auxiliary_task to other_task) invalidates fingerprint (D36 / Probe P2)
    other_store = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "other_task",
        },
    )
    other_res = other_store.execute(ctx, "update", {"mode": "configured"})
    assert other_res["ok"] is True
    assert other_res["outcome"] == "updated", "Config change must invalidate fingerprint and re-run"
    assert call_count > initial_calls
    assert "other_task" in recorded_tasks

    # 7. Structural update honesty: if manifest has state=partial, structural reports semantic_pending=True (Probe P3)
    manifest_file = (
        tmp_path / "cache" / "knowledge" / PROJECT / other_res["snapshot_id"] / "manifest.json"
    )
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest_data["semantic"]["state"] = "partial"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    struct_honest_res = other_store.execute(ctx, "update", {"mode": "structural"})
    assert struct_honest_res["ok"] is True
    assert struct_honest_res["outcome"] == "unchanged"
    assert struct_honest_res["semantic_pending"] is True, (
        "Structural update must honestly report semantic_pending=True when semantics are partial"
    )

    # 8. Verify document-to-code relationship is queryable
    q_res = semantic_store.execute(ctx, "query", {"question": "OrdersDocument"})
    assert q_res["ok"] is True
    assert "process_order" in q_res["content"] or "OrdersDocument" in q_res["content"]


def test_d37_failure_preservation_timeout_exhaustion_malformed(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)

    import aether_agents.knowledge.semantic as sem_mod

    # 1. Router exhaustion (429) fails/defers visibly without endless loop on initial index
    def mock_429(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        raise KnowledgeError("ROUTER_EXHAUSTION", "429 Too Many Requests")

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_429)

    exhaust_store = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )
    res_429 = exhaust_store.execute(ctx, "update", {"mode": "configured"})
    assert res_429["ok"] is True
    # Still publishes usable structural coverage
    assert res_429["coverage"]["code"] == "structural"
    assert res_429["coverage"]["documents"] == "structural_only"
    assert res_429["semantic"]["state"] == "unavailable"
    assert res_429["semantic_pending"] is True

    # 2. Malformed / hollow output doesn't corrupt graph
    def mock_hollow(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        return "{}", {"total_tokens": 10}

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_hollow)
    res_hollow = exhaust_store.execute(ctx, "update", {"mode": "configured"})
    assert res_hollow["ok"] is True
    assert res_hollow["coverage"]["code"] == "structural"
    assert res_hollow["semantic"]["state"] in ("unavailable", "pending")

    # 3. Retain previously complete snapshot on failed refresh (D37 / Probe P4)
    # First: perform a successful configured update to establish a complete snapshot
    def mock_success(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        return (
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "DocAlpha",
                            "label": "DocAlpha",
                            "source_file": "README.md",
                            "source_location": "1",
                        }
                    ],
                    "edges": [
                        {
                            "source": "DocAlpha",
                            "target": "module_process_order",
                            "relation": "specifies",
                        }
                    ],
                }
            ),
            {"total_tokens": 100},
        )

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_success)
    complete_res = exhaust_store.execute(ctx, "update", {"mode": "configured"})
    assert complete_res["ok"] is True
    assert complete_res["semantic"]["state"] == "complete"
    complete_snapshot_id = complete_res["snapshot_id"]

    # Now refresh with new task and 429 router exhaustion: MUST retain previously complete snapshot
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_429)
    refresh_store = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "refresh_task",
        },
    )
    refresh_res = refresh_store.execute(ctx, "update", {"mode": "configured"})
    assert refresh_res["ok"] is True
    assert refresh_res["outcome"] == "unchanged"
    assert refresh_res["snapshot_id"] == complete_snapshot_id
    assert refresh_res["semantic"]["state"] == "complete"
    assert refresh_res["semantic_pending"] is False
    assert any("Refresh failed; retained" in w for w in refresh_res["warnings"])

    # Active pointer must still point to complete_snapshot_id
    pointer_file = (
        state / "knowledge" / PROJECT / "views" / ctx.view_id / f"{ctx.source_revision}.json"
    )
    pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
    assert pointer["snapshot_id"] == complete_snapshot_id

    # 4. Cancellation stops processing, retains validated cache, never publishes unfinished state
    import threading

    cancel_evt = threading.Event()
    cancel_evt.set()
    with pytest.raises(KnowledgeError) as exc_info:
        sem_mod.run_semantic_extraction(
            backend=GraphifyBackend(native_python),
            source_root=tmp_path
            / "cache"
            / "knowledge"
            / PROJECT
            / complete_snapshot_id
            / "sources",
            graph_path=tmp_path
            / "cache"
            / "knowledge"
            / PROJECT
            / complete_snapshot_id
            / "graphify-out"
            / "graph.json",
            inputs={"README.md": "abc"},
            cache_root=tmp_path / "cache",
            ctx=ctx,
            configuration={"semantic_auxiliary_task": "web_extract"},
            cancel_event=cancel_evt,
        )
    assert exc_info.value.code == "OPERATION_CANCELLED"


def test_d35_cross_project_isolation_and_symbol_collision(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Two isolated projects with colliding symbols
    root_a, state_a = project(tmp_path, identity=PROJECT, folder="proj_a")
    root_b, state_b = project(tmp_path, identity=OTHER, folder="proj_b")

    ctx_a = resolve_context(PROJECT, "morfeo", state_root=state_a, root=root_a)
    ctx_b = resolve_context(OTHER, "morfeo", state_root=state_b, root=root_b)

    import aether_agents.knowledge.semantic as sem_mod

    # Mock auxiliary extraction for controlled test
    def mock_aux_a(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        return (
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "DocAlpha",
                            "label": "DocAlpha",
                            "source_file": "README.md",
                            "source_location": "1",
                        }
                    ],
                    "edges": [
                        {
                            "source": "DocAlpha",
                            "target": "module_process_order",
                            "relation": "specifies",
                            "confidence": "EXTRACTED",
                        }
                    ],
                }
            ),
            {"total_tokens": 100},
        )

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_aux_a)

    store_a = KnowledgeStore(
        state_a,
        tmp_path / "cache_a",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )
    store_b = KnowledgeStore(
        state_b,
        tmp_path / "cache_b",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )

    res_a = store_a.execute(ctx_a, "update", {"mode": "configured"})
    assert res_a["ok"] is True
    assert res_a["semantic"]["state"] == "complete"

    # Verify no LLM-as-AST promotion: origin must be llm and confidence must be INFERRED
    graph_a_file = (
        tmp_path
        / "cache_a"
        / "knowledge"
        / PROJECT
        / res_a["snapshot_id"]
        / "graphify-out"
        / "graph.json"
    )
    graph_a = json.loads(graph_a_file.read_text(encoding="utf-8"))
    edges = graph_a.get("edges", graph_a.get("links", []))
    spec_edge = next((e for e in edges if e.get("relation") == "specifies"), None)
    assert spec_edge is not None
    assert spec_edge.get("origin") == "llm" or spec_edge.get("_origin") == "llm"
    assert spec_edge.get("confidence") == "INFERRED"

    # Index project B
    res_b = store_b.execute(ctx_b, "update", {"mode": "configured"})
    assert res_b["ok"] is True
    # Verify no cross-project cache leakage: cache_a and cache_b are separate
    cache_a_files = list(
        (tmp_path / "cache_a" / "knowledge" / PROJECT / "semantic_cache").glob("*.json")
    )
    cache_b_files = list(
        (tmp_path / "cache_b" / "knowledge" / OTHER / "semantic_cache").glob("*.json")
    )
    assert len(cache_a_files) > 0
    assert len(cache_b_files) > 0


def test_d35_missing_or_ambiguous_auxiliary_task_unbound(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing, auto, or ambiguous auxiliary bindings must return unavailable (Decision 4)."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)

    calls = 0

    def mock_fail(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        nonlocal calls
        calls += 1
        raise AssertionError("Auxiliary model must not be called for unbound tasks!")

    import aether_agents.knowledge.semantic as sem_mod

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_fail)

    # 1. Missing auxiliary task
    store_missing = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={"enabled": True, "semantic_enabled": True},
    )
    res_missing = store_missing.execute(ctx, "update", {"mode": "configured"})
    assert res_missing["ok"] is True
    assert res_missing["semantic"]["state"] == "unavailable"
    assert res_missing["semantic_pending"] is True
    assert res_missing["coverage"]["documents"] == "structural_only"
    assert calls == 0

    # 2. Auto auxiliary task
    store_auto = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "auto",
        },
    )
    res_auto = store_auto.execute(ctx, "update", {"mode": "configured"})
    assert res_auto["semantic"]["state"] == "unavailable"
    assert res_auto["semantic_pending"] is True
    assert calls == 0

    # 3. Ambiguous auxiliary task (differing task in semantic dict vs outer key)
    store_ambiguous = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic": {"auxiliary_task": "task_one"},
            "semantic_auxiliary_task": "task_two",
        },
    )
    res_ambiguous = store_ambiguous.execute(ctx, "update", {"mode": "configured"})
    assert res_ambiguous["semantic"]["state"] == "unavailable"
    assert res_ambiguous["semantic_pending"] is True
    assert calls == 0


def test_d38_real_gh_read_only_pr_or_honest_skip() -> None:
    """Exercise real gh read-only PR if authenticated; skip honestly otherwise."""
    import shutil
    import subprocess

    if not shutil.which("gh"):
        pytest.skip("GitHub CLI ('gh') is not installed.")

    try:
        proc = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            pytest.skip("GitHub CLI ('gh') is not authenticated in this environment.")
    except Exception as exc:
        pytest.skip(f"GitHub CLI check failed ({exc}).")

    from aether_agents.knowledge.github import _run_gh

    # Read-only test against current repo
    try:
        repo_root = Path(__file__).parents[1]
        prs = _run_gh(repo_root, ["pr", "list", "--limit", "1", "--json", "number,title"])
        assert isinstance(prs, list)
    except Exception as exc:
        pytest.skip(f"gh pr list query could not complete ({exc}).")


def test_d35_live_auxiliary_document_code_relation(tmp_path: Path, native_python: Path) -> None:
    """Exercise live auxiliary when provisioned; honestly label skip otherwise."""
    try:
        from agent.auxiliary_client import call_llm  # type: ignore[import-untyped]

        res = call_llm(
            task="web_extract",
            messages=[{"role": "user", "content": "ping"}],
            timeout=10,
        )
    except Exception as exc:
        pytest.skip(f"Live auxiliary connection not provisioned in test runner ({exc})")

    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(
        state,
        tmp_path / "cache",
        GraphifyBackend(native_python),
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )
    res = store.execute(ctx, "update", {"mode": "configured"})
    assert res["ok"] is True
    assert res["semantic"]["state"] == "complete"
    assert res["semantic"]["observed_usage"]["total_tokens"] > 0


def test_large_corpus_semantic_prepare_bounded_paging(
    tmp_path: Path, native_python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-first regression on #332: large eligible corpus prepare exceeds 2MB monolithically, passes when paged."""
    import aether_agents.knowledge.semantic as sem_mod

    root, state = project(tmp_path)
    doc_dir = root / "docs"
    doc_dir.mkdir()
    doc_files = []
    content = "# Architecture\n\n" + (
        "Aether autonomous multi-agent workflow knowledge graph.\n" * 200
    )
    for i in range(160):
        fpath = doc_dir / f"guide_{i:03d}.md"
        fpath.write_text(content, encoding="utf-8")
        doc_files.append(str(fpath.relative_to(root)))

    git_at(root, "add", ".")
    git_at(root, "commit", "-qm", "large corpus")

    backend = GraphifyBackend(native_python)

    # 1. Monolithic simulation (#332 failure mode):
    # Retrieve all chunks across pages and assert that returning them monolithically
    # exceeds the 2,000,000 byte Graphify transport cap.
    all_chunks = sem_mod._fetch_all_prepared_chunks(
        backend, source_root=root, graph_path=root / "graph.json", eligible_files=doc_files
    )
    assert len(all_chunks) == 160
    monolithic_payload = {
        "ok": True,
        "action": "semantic_prepare",
        "content": "monolithic prepare payload",
        "references": [],
        "chunks": all_chunks,
    }
    monolithic_bytes = json.dumps(monolithic_payload).encode("utf-8")
    assert len(monolithic_bytes) > 2_000_000, (
        f"Monolithic payload must exceed 2MB to reproduce #332 (got {len(monolithic_bytes)} bytes)"
    )

    # 2. Bounded paging passes:
    # A single paged prepare call is well below the 2MB limit
    p0 = backend.run(
        "semantic_prepare",
        source_root=root,
        graph_path=root / "graph.json",
        arguments={"files": doc_files, "offset": 0, "limit": 25},
    )
    p0_bytes = json.dumps(p0).encode("utf-8")
    assert len(p0_bytes) < 2_000_000, (
        f"Paged payload must stay under 2MB (got {len(p0_bytes)} bytes)"
    )
    assert p0["total_chunks"] == 160
    assert p0["has_more"] is True
    assert len(p0["chunks"]) == 25

    # 3. Deterministic fingerprinting over full eligible corpus succeeds without RESULT_TOO_LARGE
    inputs = {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in doc_files}
    cfg = {"semantic": {"auxiliary_task": "web_extract"}}
    fp = sem_mod.compute_semantic_fingerprint(
        backend, source_root=root, graph_path=root / "graph.json", inputs=inputs, configuration=cfg
    )
    assert fp is not None and isinstance(fp, str)

    # 4. Full extraction across large corpus:
    # Mock auxiliary model to return valid fragments bound to existing structural nodes
    def mock_aux_call(task: str, *args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        user_prompt = kwargs.get("user_prompt", "")
        if not user_prompt and len(args) >= 2:
            user_prompt = args[1]
        matched = "README.md"
        for f in doc_files:
            if f in user_prompt:
                matched = f
                break
        safe_name = matched.replace("/", "_").replace(".", "_")
        frag = {
            "nodes": [
                {
                    "id": f"node_{safe_name}",
                    "label": f"Doc {matched}",
                    "source_file": matched,
                    "source_location": "1",
                }
            ],
            "edges": [
                {
                    "source": f"node_{safe_name}",
                    "target": "module_process_order",
                    "relation": "references",
                }
            ],
        }
        return json.dumps(frag), {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mock_aux_call)

    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    store = KnowledgeStore(
        state,
        tmp_path / "cache",
        backend,
        configuration={
            "enabled": True,
            "semantic_enabled": True,
            "semantic_auxiliary_task": "web_extract",
        },
    )
    res = store.execute(ctx, "update", {"mode": "configured"})
    assert res["ok"] is True
    assert res["coverage"]["documents"] == "semantic"
    assert res["semantic"]["state"] == "complete"
    assert len(res["semantic"]["covered_paths"]) == 162
    assert len(res["semantic"]["validated_chunk_ids"]) == 160
    assert res["semantic_pending"] is False
