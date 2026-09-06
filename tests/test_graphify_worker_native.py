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


def test_native_worker_query_traversal_and_filters(tmp_path: Path) -> None:
    from networkx.readwrite import json_graph

    # Purpose-built graph where native depth-limited BFS and DFS select different nodes/edges:
    # root connects to node_A and node_B
    # node_B connects to node_A
    # node_A connects to leaf (with context='special')
    # BFS depth 2 visits: root, node_A, node_B, leaf (4 nodes)
    # DFS depth 2 visits: root, node_B, node_A (leaf is at depth 3 via B->A and skipped; 3 nodes)
    root = tmp_path / "traversal-corpus"
    source = root / "sources"
    source.mkdir(parents=True)
    (source / "pipeline.py").write_text("def root():\n    pass\n")
    graph_dir = root / "graphify-out"
    graph_dir.mkdir(parents=True)
    graph_path = graph_dir / "graph.json"

    import networkx as nx

    G = nx.Graph()
    G.add_node(
        "root", label="root", source_file="pipeline.py", source_location="L1", file_type="code"
    )
    G.add_node(
        "node_A", label="node_A", source_file="pipeline.py", source_location="L10", file_type="code"
    )
    G.add_node(
        "node_B", label="node_B", source_file="pipeline.py", source_location="L20", file_type="code"
    )
    G.add_node(
        "leaf", label="leaf", source_file="pipeline.py", source_location="L30", file_type="code"
    )

    G.add_edge(
        "root",
        "node_A",
        relation="calls",
        confidence="EXTRACTED",
        source_file="pipeline.py",
        context="special",
    )
    G.add_edge(
        "root", "node_B", relation="calls", confidence="EXTRACTED", source_file="pipeline.py"
    )
    G.add_edge(
        "node_B", "node_A", relation="calls", confidence="EXTRACTED", source_file="pipeline.py"
    )
    G.add_edge(
        "node_A",
        "leaf",
        relation="calls",
        confidence="EXTRACTED",
        source_file="pipeline.py",
        context="special",
    )

    data = json_graph.node_link_data(G, edges="links")
    data["directed"] = False
    graph_path.write_text(json.dumps(data), encoding="utf-8")
    corpus = {"graph_path": str(graph_path), "source_root": str(source)}

    res_bfs = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "root", "traversal": "bfs", "depth": 2},
        }
    )
    res_dfs = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "root", "traversal": "dfs", "depth": 2},
        }
    )
    assert "Traversal: BFS" in res_bfs["content"]
    assert "Traversal: DFS" in res_dfs["content"]
    assert res_bfs["query_options"]["traversal"] == "bfs"
    assert res_dfs["query_options"]["traversal"] == "dfs"

    # Prove BFS and DFS select different result sets
    assert "4 nodes found" in res_bfs["content"]
    assert "3 nodes found" in res_dfs["content"]
    assert "leaf" in res_bfs["content"]
    assert "leaf" not in res_dfs["content"]
    assert any("L30" in r.get("location", "") for r in res_bfs["references"])
    assert not any("L30" in r.get("location", "") for r in res_dfs["references"])

    # Prove depth changes the returned set
    res_d1 = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "root", "traversal": "bfs", "depth": 1},
        }
    )
    assert "3 nodes found" in res_d1["content"]
    assert "leaf" not in res_d1["content"]

    # Explicit context filtering selects only matching edges
    res_filtered = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "root", "context_filter": ["special"]},
        }
    )
    assert "Context: special (explicit)" in res_filtered["content"]
    assert "3 nodes found" in res_filtered["content"]
    assert "leaf" in res_filtered["content"]
    assert "node_B" not in res_filtered["content"]

    # Unknown filter is empty-not-fallback (only seed node returned, 0 edges traversed)
    res_unknown = graph_worker.execute(
        {
            **corpus,
            "action": "query",
            "arguments": {"question": "root", "context_filter": ["nonexistent_context"]},
        }
    )
    assert "Context: nonexistent_context (explicit)" in res_unknown["content"]
    assert "1 nodes found" in res_unknown["content"]
    assert "node_A" not in res_unknown["content"]
    assert "node_B" not in res_unknown["content"]
    assert "leaf" not in res_unknown["content"]


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

    import networkx as nx
    from networkx.readwrite import json_graph

    graph_path = Path(corpus["graph_path"])
    sha_before = hashlib.sha256(graph_path.read_bytes()).hexdigest()

    export_graph = tmp_path / "graph.html"
    res_graph = graph_worker.execute(
        {
            **corpus,
            "action": "visualize",
            "arguments": {
                "format": "graph",
                "detail": "auto",
                "export_path": str(export_graph),
                "project_label": "TestProject @ rev1",
            },
        }
    )
    assert export_graph.is_file()
    assert res_graph["artifact"]["format"] == "graph"
    assert res_graph["artifact"]["bytes"] == export_graph.stat().st_size
    assert res_graph["artifact"]["sha256"] == hashlib.sha256(export_graph.read_bytes()).hexdigest()
    assert res_graph["artifact"]["rendered_nodes"] > 0
    assert any("vis-network" in a for a in res_graph["artifact"]["external_assets"])

    # Graph HTML identifies supplied project/revision
    html_content = export_graph.read_text(encoding="utf-8")
    assert "<title>graphify - TestProject @ rev1</title>" in html_content
    assert "TestProject @ rev1" in html_content

    # Check JS syntax with node
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
                "project_label": "TestProject @ rev1",
            },
        }
    )
    assert export_tree.is_file()
    assert res_tree["artifact"]["format"] == "tree"
    assert res_tree["artifact"]["bytes"] == export_tree.stat().st_size
    assert any("d3" in a for a in res_tree["artifact"]["external_assets"])
    tree_html_content = export_tree.read_text(encoding="utf-8")
    assert "TestProject @ rev1" in tree_html_content

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

    # Real aggregation above 5,000 nodes (detail=auto) vs full rendering (detail=full)
    large_graph_path = tmp_path / "large_graph.json"
    G_large = nx.Graph()
    for i in range(5005):
        cid = i % 5
        G_large.add_node(f"node_{i}", label=f"node_{i}", community=cid, source_file="order.py")
    for i in range(5000):
        G_large.add_edge(f"node_{i}", f"node_{i + 1}", relation="calls", confidence="EXTRACTED")
    data_large = json_graph.node_link_data(G_large, edges="links")
    data_large["directed"] = False
    large_graph_path.write_text(json.dumps(data_large), encoding="utf-8")
    large_sha_before = hashlib.sha256(large_graph_path.read_bytes()).hexdigest()

    export_large_auto = tmp_path / "large_auto.html"
    res_large_auto = graph_worker.execute(
        {
            **corpus,
            "graph_path": str(large_graph_path),
            "action": "visualize",
            "arguments": {
                "format": "graph",
                "detail": "auto",
                "export_path": str(export_large_auto),
                "project_label": "LargeProject @ auto",
            },
        }
    )
    assert export_large_auto.is_file()
    assert res_large_auto["artifact"]["aggregated"] is True
    assert res_large_auto["artifact"]["rendered_nodes"] < 5005
    assert res_large_auto["artifact"]["total_nodes"] == 5005
    auto_html = export_large_auto.read_text(encoding="utf-8")
    assert "<title>graphify - LargeProject @ auto</title>" in auto_html

    export_large_full = tmp_path / "large_full.html"
    res_large_full = graph_worker.execute(
        {
            **corpus,
            "graph_path": str(large_graph_path),
            "action": "visualize",
            "arguments": {
                "format": "graph",
                "detail": "full",
                "export_path": str(export_large_full),
                "project_label": "LargeProject @ full",
            },
        }
    )
    assert export_large_full.is_file()
    assert res_large_full["artifact"]["aggregated"] is False
    assert res_large_full["artifact"]["rendered_nodes"] == 5005
    assert res_large_full["artifact"]["total_nodes"] == 5005
    full_html = export_large_full.read_text(encoding="utf-8")
    assert "<title>graphify - LargeProject @ full</title>" in full_html

    large_sha_after = hashlib.sha256(large_graph_path.read_bytes()).hexdigest()
    assert large_sha_before == large_sha_after, (
        "Snapshot graph.json bytes must remain unchanged by large visualize"
    )

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

    # Reject out-of-scope-only fragment
    out_of_scope_text = json.dumps(
        {
            "nodes": [{"id": "other_func", "label": "other_func", "source_file": "other.py"}],
            "edges": [],
        }
    )
    with pytest.raises(ValueError, match="[Hh]ollow|source validation"):
        graph_worker.execute(
            {
                **corpus,
                "action": "semantic_parse",
                "arguments": {
                    "model_text": out_of_scope_text,
                    "allowed_sources": ["README.md"],
                },
            }
        )

    # Reject ghost-only edge with dangling endpoints
    ghost_edge_text = json.dumps(
        {
            "nodes": [],
            "edges": [{"source": "ghost_a", "target": "ghost_b", "relation": "calls"}],
        }
    )
    with pytest.raises(ValueError, match="do not bind to accepted fragment or structural nodes"):
        graph_worker.execute(
            {
                **corpus,
                "action": "semantic_parse",
                "arguments": {"model_text": ghost_edge_text},
            }
        )

    # Model node confidence EXTRACTED demoted to INFERRED
    node_extracted_text = json.dumps(
        {
            "nodes": [
                {
                    "id": "test_node",
                    "label": "Test Node",
                    "source_file": "README.md",
                    "confidence": "EXTRACTED",
                }
            ],
            "edges": [],
        }
    )
    parse_res = graph_worker.execute(
        {
            **corpus,
            "action": "semantic_parse",
            "arguments": {"model_text": node_extracted_text},
        }
    )
    parsed_node = parse_res["fragment"]["nodes"][0]
    assert parsed_node["confidence"] == "INFERRED"
    assert parsed_node["_origin"] == "llm"
    assert parsed_node["origin"] == "llm"

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
    assert edata["origin"] in ("ast", "structural")

    # Regression: Normalized collision with ghost IDs remapping to AST pair
    normalized_collision_fragment = {
        "nodes": [
            {
                "id": "ghost_reserve",
                "label": "reserve()",
                "source_file": "order.py",
                "file_type": "code",
            },
            {
                "id": "ghost_charge",
                "label": "charge()",
                "source_file": "order.py",
                "file_type": "code",
            },
        ],
        "edges": [
            {
                "source": "ghost_reserve",
                "target": "ghost_charge",
                "relation": "calls",
                "confidence": "EXTRACTED",
                "source_file": "order.py",
            }
        ],
    }
    apply_nc = graph_worker.execute(
        {
            **custom_corpus,
            "action": "semantic_apply",
            "arguments": {"fragment": normalized_collision_fragment},
        }
    )
    assert apply_nc["applied_nodes"] == 0
    assert apply_nc["applied_edges"] == 0
    assert "0 nodes" in apply_nc["content"]
    assert "0 edges merged" in apply_nc["content"]
    assert len(apply_nc["omitted_edges"]) == 1
    G_nc = _load_graph(str(temp_graph))
    assert "ghost_reserve" not in G_nc
    assert "ghost_charge" not in G_nc
    assert G_nc.nodes["order_reserve"]["_origin"] == "ast"
    assert G_nc.nodes["order_reserve"]["origin"] in ("ast", "structural")
    assert G_nc.nodes["order_charge"]["_origin"] == "ast"
    assert G_nc.nodes["order_charge"]["origin"] in ("ast", "structural")
    ed_nc = G_nc.get_edge_data("order_reserve", "order_charge")
    assert ed_nc["_origin"] == "ast"
    assert ed_nc["origin"] in ("ast", "structural")
    assert ed_nc["confidence"] == "EXTRACTED"

    # Regression: Reverse-direction exact-ID collision
    reverse_collision_fragment = {
        "nodes": [],
        "edges": [
            {
                "source": "order_charge",
                "target": "order_reserve",
                "relation": "calls",
                "confidence": "EXTRACTED",
                "source_file": "order.py",
            }
        ],
    }
    apply_rev = graph_worker.execute(
        {
            **custom_corpus,
            "action": "semantic_apply",
            "arguments": {"fragment": reverse_collision_fragment},
        }
    )
    assert apply_rev["applied_edges"] == 0
    assert len(apply_rev["omitted_edges"]) == 1
    G_rev = _load_graph(str(temp_graph))
    ed_rev = G_rev.get_edge_data("order_reserve", "order_charge")
    assert ed_rev["_origin"] == "ast"
    assert ed_rev["origin"] in ("ast", "structural")
    assert ed_rev["confidence"] == "EXTRACTED"
