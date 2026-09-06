"""Exercise the worker in the isolated engine environment, never inside Hermes.

Run this module with the qualified Graphify interpreter. The ordinary manager
suite reports the explicit missing-component skip instead of installing it.
"""

from __future__ import annotations

import importlib.metadata
import io
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("graphify", reason="Run in the isolated Graphify component environment")

from aether_agents.knowledge import graph_worker


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("native-worker")
    source = root / "sources"
    source.mkdir()
    (source / "order.py").write_text(
        "def charge():\n    return 1\n\ndef reserve():\n    return charge()\n"
    )
    (source / "README.md").write_text("# Reservations\n\nSee [implementation](order.py).\n")
    graph = root / "graphify-out/graph.json"
    with pytest.MonkeyPatch.context() as patch:
        home = root / "home"
        home.mkdir()
        patch.setenv("HOME", str(home))
        patch.setenv("GRAPHIFY_OUT", str(graph.parent))
        patch.setenv("GRAPHIFY_QUERY_LOG_DISABLE", "1")
        patch.chdir(source)
        request = {"source_root": str(source), "graph_path": str(graph)}
        result = graph_worker.execute({**request, "action": "update"})
        assert "built" in result["content"] and graph.is_file()
        yield request


@pytest.mark.parametrize(
    "action,arguments",
    [
        ("query", {"question": "reserve"}),
        ("explain", {"node": "reserve"}),
        ("impact", {"node": "charge", "depth": 2}),
        ("path", {"source": "reserve", "target": "charge"}),
        ("neighbors", {"node": "reserve"}),
        ("neighbors", {"node": "reserve", "relation": "calls"}),
        ("community", {"community_id": 0}),
    ],
)
def test_native_worker_query_contracts(corpus, action: str, arguments: dict) -> None:
    result = graph_worker.execute({**corpus, "action": action, "arguments": arguments})
    assert result["content"]
    assert isinstance(result["references"], list)
    assert len(result["references"]) > 0
    if action == "explain":
        assert "resolved_node" in result
        assert result["resolved_node"]["id"]
    if action == "community":
        assert "community" in result
        assert result["community"]["id"] == arguments["community_id"]


@pytest.mark.parametrize(
    "action,arguments",
    [
        ("neighbors", {"node": "DefinitelyMissingSentinel"}),
        ("community", {"community_id": 999999}),
        ("unsupported", {}),
    ],
)
def test_native_worker_rejects_unresolved_operations(corpus, action: str, arguments: dict) -> None:
    with pytest.raises(ValueError):
        graph_worker.execute({**corpus, "action": action, "arguments": arguments})


def test_native_save_and_reflect_preserve_answer_without_shared_sidecar(corpus) -> None:
    result = graph_worker.execute(
        {
            "action": "memory_save",
            "arguments": {
                "situation": "A corrected integration step",
                "lesson": "Call the verified interface.",
                "applicability": "Only this project's current interface.",
                "outcome": "corrected",
                "correction": "CORRECTED_NATIVE_SOLUTION",
                "source_nodes": ["charge"],
            },
        }
    )
    assert "Call the verified interface." in result["content"]
    reflected = graph_worker.execute(
        {"action": "memory_reflect", "arguments": {"notes": [result["content"]]}}
    )
    assert reflected["count"] == 1
    assert "CORRECTED_NATIVE_SOLUTION" in reflected["content"]
    assert not (Path(corpus["graph_path"]).parent / ".graphify_learning.json").exists()


def test_native_worker_path_reverse_recovery_wording(corpus) -> None:
    result = graph_worker.execute(
        {**corpus, "action": "path", "arguments": {"source": "charge", "target": "reserve"}}
    )
    assert result["content"]
    assert "No directed path found" in result["content"]
    for forbidden in (
        "undirected=true",
        "context_filter",
        "get_node",
        "--budget",
        "CLI:",
        "MCP",
        "Graph:",
    ):
        assert forbidden not in result["content"]
    assert any(t in result["content"] for t in ["explain", "question", "budget_tokens"])


@pytest.mark.parametrize(
    "raw,expected_forbidden,expected_present",
    [
        (
            "Use the MCP get_node tool.",
            ["MCP", "get_node"],
            "explain",
        ),
        (
            "Use the MCP explain tool.",
            ["MCP"],
            "explain",
        ),
        (
            "Retry with undirected=true to search ignoring edge direction.",
            ["undirected=true"],
            "explain",
        ),
        (
            "Narrow with context_filter=['call'] or use get_node for a specific symbol",
            ["context_filter", "get_node"],
            "explain",
        ),
        (
            "raise the token budget (CLI: --budget) or narrow the query",
            ["CLI:", "--budget"],
            "budget_tokens",
        ),
    ],
)
def test_normalize_recovery_wording_strips_mcp_and_unsupported_recovery(
    raw: str, expected_forbidden: list[str], expected_present: str
) -> None:
    normalized = graph_worker.normalize_recovery_wording(raw)
    for f in expected_forbidden:
        assert f not in normalized
    assert expected_present in normalized


def test_native_worker_rejects_unqualified_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "99.0.0")
    with pytest.raises(ValueError, match="not qualified"):
        graph_worker.execute({"action": "probe"})


def test_worker_protocol_returns_only_one_json_result(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{"action":"probe"}')))
    assert graph_worker.main() == 0
    response = json.loads(capsys.readouterr().out)
    assert response["ok"] and response["version"] == "0.9.54"
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{"action":"invalid"}')))
    assert graph_worker.main() == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_native_worker_stats_and_god_nodes(corpus) -> None:
    res = graph_worker.execute({**corpus, "action": "stats"})
    assert "stats" in res
    stats = res["stats"]
    assert stats["node_count"] > 0
    assert stats["edge_count"] > 0
    assert stats["community_count"] > 0
    assert set(stats["confidence_counts"].keys()) == {
        "EXTRACTED",
        "INFERRED",
        "AMBIGUOUS",
        "UNKNOWN",
    }
    assert set(stats["origin_counts"].keys()) == {"structural", "llm", "unknown"}
    assert stats["confidence_counts"]["EXTRACTED"] > 0
    assert stats["origin_counts"]["structural"] > 0

    gods_res = graph_worker.execute({**corpus, "action": "god_nodes", "arguments": {"top_n": 5}})
    assert "nodes" in gods_res
    nodes = gods_res["nodes"]
    assert len(nodes) > 0
    for node in nodes:
        assert "id" in node
        assert "label" in node
        assert "degree" in node
        assert "community_id" in node
        assert node["community_id"] is None or isinstance(node["community_id"], int)
    degrees = [n["degree"] for n in nodes]
    assert degrees == sorted(degrees, reverse=True)
    assert len(gods_res["references"]) > 0


def test_native_worker_query_traversal_and_filters(corpus) -> None:
    res_bfs = graph_worker.execute(
        {**corpus, "action": "query", "arguments": {"question": "reserve", "traversal": "bfs"}}
    )
    res_dfs = graph_worker.execute(
        {**corpus, "action": "query", "arguments": {"question": "reserve", "traversal": "dfs"}}
    )
    assert "Traversal: BFS" in res_bfs["content"]
    assert "Traversal: DFS" in res_dfs["content"]
    assert res_bfs["query_options"]["traversal"] == "bfs"
    assert res_dfs["query_options"]["traversal"] == "dfs"

    res_filtered = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "reserve", "context_filter": ["call"]},
        }
    )
    assert "Context: call (explicit)" in res_filtered["content"]
    assert len(res_filtered["references"]) > 0

    # Unknown filter is empty-not-fallback
    res_unknown = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "reserve", "context_filter": ["nonexistent_context"]},
        }
    )
    assert "Context: nonexistent_context (explicit)" in res_unknown["content"]
    assert len(res_unknown["references"]) < len(res_filtered["references"])


def test_native_worker_impact_relations(corpus) -> None:
    res_calls = graph_worker.execute(
        {
            **corpus,
            "action": "impact",
            "arguments": {"node": "charge", "relations": ["calls"]},
        }
    )
    assert len(res_calls["references"]) > 0

    # Unknown filter is empty-not-fallback
    res_unknown = graph_worker.execute(
        {
            **corpus,
            "action": "impact",
            "arguments": {"node": "charge", "relations": ["unknown_relation_sentinel"]},
        }
    )
    assert "0 affected" in res_unknown["content"] or "No affected nodes" in res_unknown["content"]
    assert len(res_unknown["references"]) <= 1


def test_native_worker_path_undirected_vs_directed(corpus) -> None:
    res_dir = graph_worker.execute(
        {
            **corpus,
            "action": "path",
            "arguments": {"source": "charge", "target": "reserve", "undirected": False},
        }
    )
    assert "No directed path found" in res_dir["content"]
    assert len(res_dir["references"]) == 0

    res_undir = graph_worker.execute(
        {
            **corpus,
            "action": "path",
            "arguments": {"source": "charge", "target": "reserve", "undirected": True},
        }
    )
    assert "Shortest path" in res_undir["content"]
    assert len(res_undir["references"]) > 0
    assert res_undir["content"] != res_dir["content"]


def test_native_worker_visualize_both_formats_and_integrity(corpus, tmp_path: Path) -> None:
    import hashlib
    import subprocess

    graph_path = Path(corpus["graph_path"])
    sha_before = hashlib.sha256(graph_path.read_bytes()).hexdigest()

    export_graph = tmp_path / "graph.html"
    res_graph = graph_worker.execute(
        {
            **corpus,
            "action": "visualize",
            "arguments": {"format": "graph", "detail": "auto", "export_path": str(export_graph)},
        }
    )
    assert export_graph.is_file()
    assert res_graph["artifact"]["format"] == "graph"
    assert res_graph["artifact"]["bytes"] == export_graph.stat().st_size
    assert res_graph["artifact"]["sha256"] == hashlib.sha256(export_graph.read_bytes()).hexdigest()
    assert res_graph["artifact"]["rendered_nodes"] > 0
    assert any("vis-network" in a for a in res_graph["artifact"]["external_assets"])

    # Check JS syntax with node
    html_content = export_graph.read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html_content, re.DOTALL)
    assert len(scripts) > 0
    for idx, s in enumerate(scripts):
        script_file = tmp_path / f"graph_script_{idx}.js"
        script_file.write_text(s, encoding="utf-8")
        proc = subprocess.run(["node", "--check", str(script_file)], capture_output=True)
        assert proc.returncode == 0, f"JS check failed: {proc.stderr.decode()}"

    export_tree = tmp_path / "tree.html"
    res_tree = graph_worker.execute(
        {
            **corpus,
            "action": "visualize",
            "arguments": {
                "format": "tree",
                "export_path": str(export_tree),
                "project_label": "TestProject",
            },
        }
    )
    assert export_tree.is_file()
    assert res_tree["artifact"]["format"] == "tree"
    assert res_tree["artifact"]["bytes"] == export_tree.stat().st_size
    assert any("d3" in a for a in res_tree["artifact"]["external_assets"])
    tree_html_content = export_tree.read_text(encoding="utf-8")
    assert "TestProject" in tree_html_content

    # Check tree JS syntax
    tree_scripts = re.findall(
        r"<script(?![^>]*src=)[^>]*>(.*?)</script>", tree_html_content, re.DOTALL
    )
    assert len(tree_scripts) > 0
    for idx, s in enumerate(tree_scripts):
        script_file = tmp_path / f"tree_script_{idx}.js"
        script_file.write_text(s, encoding="utf-8")
        proc = subprocess.run(["node", "--check", str(script_file)], capture_output=True)
        assert proc.returncode == 0, f"Tree JS check failed: {proc.stderr.decode()}"

    sha_after = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    assert sha_before == sha_after, "Snapshot graph.json bytes must remain unchanged by visualize"


def test_native_worker_pr_impact_without_network(corpus) -> None:
    res = graph_worker.execute(
        {
            **corpus,
            "action": "pr_impact",
            "arguments": {"files": ["order.py"]},
        }
    )
    assert "impact" in res
    impact = res["impact"]
    assert impact["files"] == 1
    assert impact["matched_files"] == ["order.py"]
    assert len(impact["communities"]) > 0
    assert impact["node_count"] > 0
    assert len(res["references"]) > 0

    res_unmatched = graph_worker.execute(
        {
            **corpus,
            "action": "pr_impact",
            "arguments": {"files": ["nonexistent_file.py"]},
        }
    )
    assert res_unmatched["impact"]["matched_files"] == []
    assert res_unmatched["impact"]["unmatched_files"] == ["nonexistent_file.py"]
    assert res_unmatched["impact"]["communities"] == []
    assert res_unmatched["impact"]["node_count"] == 0


def test_native_worker_semantic_prepare_parse_and_apply(corpus, tmp_path: Path) -> None:
    import shutil

    res_prep = graph_worker.execute(
        {
            **corpus,
            "action": "semantic_prepare",
            "arguments": {"files": ["README.md", "order.py"]},
        }
    )
    assert "chunks" in res_prep
    assert len(res_prep["chunks"]) > 0
    chunk = res_prep["chunks"][0]
    assert chunk["system_prompt"]
    assert chunk["user_prompt"]

    # Reject malformed model text
    with pytest.raises(ValueError, match="[Mm]alformed|[Jj][Ss][Oo][Nn]|Invalid"):
        graph_worker.execute(
            {
                **corpus,
                "action": "semantic_parse",
                "arguments": {"model_text": "Not a json payload at all!"},
            }
        )

    # Reject hollow model text
    with pytest.raises(ValueError, match="[Hh]ollow"):
        graph_worker.execute(
            {
                **corpus,
                "action": "semantic_parse",
                "arguments": {"model_text": '{"nodes": [], "edges": []}'},
            }
        )

    # Prepare temporary graph copy for semantic apply
    temp_graph = tmp_path / "semantic-test-graph.json"
    shutil.copy(corpus["graph_path"], temp_graph)
    custom_corpus = {**corpus, "graph_path": str(temp_graph)}

    # Valid model text with new doc node and a colliding edge
    valid_model_text = """```json
{
  "nodes": [
    {
      "id": "order_guide",
      "label": "Order Guide",
      "file_type": "document",
      "source_file": "README.md"
    }
  ],
  "edges": [
    {
      "source": "order_guide",
      "target": "order_reserve",
      "relation": "references",
      "confidence": "EXTRACTED"
    },
    {
      "source": "order_reserve",
      "target": "order_charge",
      "relation": "conceptually_related_to",
      "confidence": "EXTRACTED",
      "source_file": "order.py"
    }
  ]
}
```"""

    apply_res = graph_worker.execute(
        {
            **custom_corpus,
            "action": "semantic_apply",
            "arguments": {"model_text": valid_model_text},
        }
    )
    assert apply_res["applied_nodes"] == 1
    assert apply_res["applied_edges"] >= 1
    # Colliding edge between order_reserve and order_charge should be omitted
    assert len(apply_res["omitted_edges"]) >= 1

    # Verify merged graph properties
    from graphify.serve import _load_graph

    G = _load_graph(str(temp_graph))
    assert "order_guide" in G
    assert G.nodes["order_guide"]["_origin"] == "llm"

    # Preexisting structural edge relation preserved
    edata = G.get_edge_data("order_reserve", "order_charge")
    assert edata["relation"] == "calls"
    assert edata["_origin"] == "ast"
