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


def test_native_worker_semantic_prepare_pagination(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    files = []
    for i in range(6):
        fname = f"mod_{i}.py"
        (source_dir / fname).write_text(f"def func_{i}():\n    return {i}\n", encoding="utf-8")
        files.append(fname)

    graph_file = tmp_path / "graph.json"
    request = {"source_root": str(source_dir), "graph_path": str(graph_file)}

    # Default pagination
    res_default = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": files, "token_budget": 10},
        }
    )
    assert res_default["total_chunks"] == 6
    assert res_default["offset"] == 0
    assert res_default["limit"] == 25
    assert res_default["has_more"] is False
    assert len(res_default["chunks"]) == 6

    # Page 0 with limit 2
    res_p0 = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": files, "offset": 0, "limit": 2, "token_budget": 10},
        }
    )
    assert res_p0["total_chunks"] == 6
    assert res_p0["offset"] == 0
    assert res_p0["limit"] == 2
    assert res_p0["has_more"] is True
    assert len(res_p0["chunks"]) == 2
    assert res_p0["chunks"][0]["chunk_id"] == 0
    assert res_p0["chunks"][1]["chunk_id"] == 1

    # Page 1 with offset 2, limit 2
    res_p1 = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": files, "offset": 2, "limit": 2, "token_budget": 10},
        }
    )
    assert res_p1["offset"] == 2
    assert res_p1["has_more"] is True
    assert len(res_p1["chunks"]) == 2
    assert res_p1["chunks"][0]["chunk_id"] == 2
    assert res_p1["chunks"][1]["chunk_id"] == 3

    # Page 2 with offset 4, limit 2
    res_p2 = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": files, "offset": 4, "limit": 2, "token_budget": 10},
        }
    )
    assert res_p2["offset"] == 4
    assert res_p2["has_more"] is False
    assert len(res_p2["chunks"]) == 2
    assert res_p2["chunks"][0]["chunk_id"] == 4
    assert res_p2["chunks"][1]["chunk_id"] == 5

    # Offset beyond total
    res_empty = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": files, "offset": 10, "limit": 2, "token_budget": 10},
        }
    )
    assert res_empty["chunks"] == []
    assert res_empty["has_more"] is False

    # Limit clamped to 50
    res_clamped = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": files, "limit": 1000, "token_budget": 10},
        }
    )
    assert res_clamped["limit"] == 50

    # Empty files
    res_none = graph_worker.execute(
        {
            **request,
            "action": "semantic_prepare",
            "arguments": {"files": []},
        }
    )
    assert res_none["total_chunks"] == 0
    assert res_none["chunks"] == []
    assert res_none["has_more"] is False


# --- Additive overlay composition (#419) -----------------------------------

_OVERLAY_DERIVED_KEYS = ("community", "community_name", "norm_label")
_OVERLAY_ORIGIN_KEYS = ("_origin", "origin")


def _overlay_node(
    node_id: str,
    label: str,
    source_file: str,
    location: str,
    *,
    file_type: str = "document",
    node_kind: str = "heading",
    community: int = 0,
) -> dict:
    return {
        "id": node_id,
        "label": label,
        "_origin": "ast",
        "community": community,
        "community_name": source_file,
        "file_type": file_type,
        "node_kind": node_kind,
        "norm_label": label.lower(),
        "origin": "ast",
        "source_file": source_file,
        "source_location": location,
    }


def _overlay_link(source: str, target: str, relation: str, source_file: str, location: str) -> dict:
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "_origin": "ast",
        "confidence": "EXTRACTED",
        "confidence_score": 1.0,
        "origin": "ast",
        "source_file": source_file,
        "source_location": location,
        "weight": 1.0,
    }


def _overlay_graph_data(directed: bool) -> dict:
    hyperedges = [
        {
            "id": "flow_structural",
            "nodes": ["order_reserve", "order_charge"],
            "relation": "flow",
            "confidence": "EXTRACTED",
            "_origin": "ast",
            "source_file": "order.py",
        }
    ]
    nodes = [
        _overlay_node("readme", "README.md", "README.md", "L1", node_kind="page"),
        _overlay_node("readme_reservations", "Reservations", "README.md", "L1"),
        _overlay_node("readme_current_documentation", "Current documentation", "README.md", "L3"),
        _overlay_node("readme_current_documentation_7", "Current documentation", "README.md", "L7"),
        _overlay_node(
            "readme_current_documentation_11", "Current documentation", "README.md", "L11"
        ),
        _overlay_node("docs_helper", "helper.md", "docs/helper.md", "L1", node_kind="page"),
        _overlay_node(
            "docs_helper_current_documentation", "Current documentation", "docs/helper.md", "L3"
        ),
        _overlay_node("order", "order.py", "order.py", "L1", file_type="code", node_kind="file"),
        _overlay_node("order_charge", "charge()", "order.py", "L1", file_type="code"),
        _overlay_node("order_reserve", "reserve()", "order.py", "L5", file_type="code"),
        _overlay_node("alpha", "alpha.py", "alpha.py", "L1", file_type="code", node_kind="file"),
        _overlay_node("alpha_retry", "Retry policy", "alpha.py", "L1", file_type="concept"),
        _overlay_node("beta", "beta.py", "beta.py", "L1", file_type="code", node_kind="file"),
        _overlay_node("beta_retry", "Retry policy", "beta.py", "L1", file_type="concept"),
    ]
    links = [
        _overlay_link("readme", "readme_reservations", "contains", "README.md", "L1"),
        _overlay_link(
            "readme_reservations", "readme_current_documentation", "contains", "README.md", "L3"
        ),
        _overlay_link(
            "readme_reservations", "readme_current_documentation_7", "contains", "README.md", "L7"
        ),
        _overlay_link(
            "readme_reservations", "readme_current_documentation_11", "contains", "README.md", "L11"
        ),
        _overlay_link(
            "docs_helper",
            "docs_helper_current_documentation",
            "contains",
            "docs/helper.md",
            "L3",
        ),
        _overlay_link("order", "order_charge", "contains", "order.py", "L1"),
        _overlay_link("order", "order_reserve", "contains", "order.py", "L5"),
        _overlay_link("order_reserve", "order_charge", "calls", "order.py", "L6"),
        _overlay_link("alpha", "alpha_retry", "references", "alpha.py", "L1"),
        _overlay_link("beta", "beta_retry", "references", "beta.py", "L1"),
    ]
    return {
        "directed": directed,
        "multigraph": False,
        "graph": {"hyperedges": hyperedges},
        "nodes": nodes,
        "links": links,
        "hyperedges": hyperedges,
    }


@pytest.fixture(scope="module")
def overlay_corpus(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("native-overlay")
    source = root / "sources"
    (source / "docs").mkdir(parents=True)
    (source / "README.md").write_text(
        "# Reservations\n\n"
        "## Current documentation\n\nfirst\n\n"
        "## Current documentation\n\nsecond\n\n"
        "## Current documentation\n\nthird\n\n"
        "See [implementation](order.py).\n",
        encoding="utf-8",
    )
    (source / "docs" / "helper.md").write_text(
        "# Helper\n\n## Current documentation\n\nshared label\n", encoding="utf-8"
    )
    (source / "order.py").write_text(
        "def charge():\n    return 1\n\n\ndef reserve():\n    return charge()\n", encoding="utf-8"
    )
    (source / "alpha.py").write_text("RETRY_POLICY = 'alpha'\n", encoding="utf-8")
    (source / "beta.py").write_text("RETRY_POLICY = 'beta'\n", encoding="utf-8")
    graph = root / "graphify-out" / "graph.json"
    graph.parent.mkdir(parents=True)
    graph.write_text(json.dumps(_overlay_graph_data(directed=False), indent=2), encoding="utf-8")
    return {"source_root": str(source), "graph_path": str(graph)}


def _structural_attrs(record: dict) -> dict:
    return {
        key: value
        for key, value in record.items()
        if key not in _OVERLAY_DERIVED_KEYS and key not in _OVERLAY_ORIGIN_KEYS
    }


def _prepare_overlay_request(overlay_corpus, tmp_path: Path) -> dict:
    import shutil

    graph_path = tmp_path / "graph.json"
    shutil.copy(overlay_corpus["graph_path"], graph_path)
    return {**overlay_corpus, "graph_path": str(graph_path)}


def _read_graph(graph_path: Path) -> dict:
    return json.loads(graph_path.read_text(encoding="utf-8"))


def test_native_compose_preserves_repeated_headings_and_cross_file_labels(
    overlay_corpus, tmp_path: Path
) -> None:
    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])
    baseline = _read_graph(graph_path)
    baseline_nodes = {node["id"]: node for node in baseline["nodes"]}
    baseline_links = {
        (link["source"], link["target"], link["relation"]): link for link in baseline["links"]
    }

    canary = {
        "nodes": [
            {
                "id": "notes_overview",
                "label": "Overview notes",
                "source_file": "README.md",
                "file_type": "document",
            }
        ],
        "edges": [],
    }
    result = graph_worker.execute(
        {**request, "action": "semantic_apply", "arguments": {"fragment": canary}}
    )

    after = _read_graph(graph_path)
    after_nodes = {node["id"]: node for node in after["nodes"]}
    assert set(baseline_nodes) <= set(after_nodes)
    for node_id, baseline_node in baseline_nodes.items():
        assert _structural_attrs(after_nodes[node_id]) == _structural_attrs(baseline_node)
        assert after_nodes[node_id]["_origin"] == baseline_node["_origin"]
        assert after_nodes[node_id]["origin"] == baseline_node["origin"]
    for node_id in (
        "readme_current_documentation",
        "readme_current_documentation_7",
        "readme_current_documentation_11",
        "docs_helper_current_documentation",
        "alpha_retry",
        "beta_retry",
    ):
        assert node_id in after_nodes

    after_links = {
        (link["source"], link["target"], link["relation"]): link for link in after["links"]
    }
    for key, baseline_link in baseline_links.items():
        assert key in after_links
        assert _structural_attrs(after_links[key]) == _structural_attrs(baseline_link)

    assert after_nodes["notes_overview"]["origin"] == "llm"
    assert after_nodes["notes_overview"]["_origin"] == "llm"
    assert [hyperedge["id"] for hyperedge in after["hyperedges"]] == ["flow_structural"]

    assert result["applied_nodes"] == 1
    assert result["applied_edges"] == 0
    assert result["applied_hyperedges"] == 0
    assert result["structural_preserved"] is True
    assert result["references"] == [{"path": "README.md", "location": ""}]
    assert re.fullmatch(r"[0-9a-f]{64}", result["structural_digest"])

    stats = graph_worker.execute({**request, "action": "stats"})
    assert stats["stats"]["origin_counts"]["llm"] >= 1
    assert stats["stats"]["origin_counts"]["structural"] > 0


def test_native_compose_requires_an_existing_structural_base(
    overlay_corpus, tmp_path: Path
) -> None:
    graph_path = tmp_path / "missing-graph.json"
    request = {**overlay_corpus, "graph_path": str(graph_path)}
    with pytest.raises(ValueError, match="[Nn]o structural base"):
        graph_worker.execute(
            {
                **request,
                "action": "semantic_compose",
                "arguments": {
                    "fragments": [
                        {
                            "nodes": [
                                {
                                    "id": "notes_overview",
                                    "label": "Overview notes",
                                    "source_file": "README.md",
                                    "file_type": "document",
                                }
                            ],
                            "edges": [],
                        }
                    ]
                },
            }
        )
    assert not graph_path.exists()


def test_native_compose_exact_identity_collision_keeps_structural_records(
    overlay_corpus, tmp_path: Path
) -> None:
    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])
    before_bytes = graph_path.read_bytes()
    baseline = _read_graph(graph_path)
    baseline_node = next(node for node in baseline["nodes"] if node["id"] == "order_reserve")
    baseline_edge = next(link for link in baseline["links"] if link["relation"] == "calls")

    fragment = {
        "nodes": [
            {
                "id": "order_reserve",
                "label": "reserve()",
                "source_file": "order.py",
                "file_type": "code",
                "rationale": "model reasoning about reserve",
                "author": "llm-author",
                "source_url": "https://example.invalid/spec",
                "confidence": "EXTRACTED",
            }
        ],
        "edges": [],
    }
    result = graph_worker.execute(
        {**request, "action": "semantic_apply", "arguments": {"fragment": fragment}}
    )

    after = _read_graph(graph_path)
    node = next(item for item in after["nodes"] if item["id"] == "order_reserve")
    assert _structural_attrs(node) == _structural_attrs(baseline_node)
    assert node["_origin"] == "ast"
    assert node["origin"] == "ast"
    for forbidden in ("rationale", "author", "source_url", "confidence"):
        assert forbidden not in node
    edge = next(link for link in after["links"] if link["relation"] == "calls")
    assert _structural_attrs(edge) == _structural_attrs(baseline_edge)
    # Nothing was accepted, so no publication transaction rewrites the graph.
    assert graph_path.read_bytes() == before_bytes

    assert result["applied_nodes"] == 0
    assert result["applied_edges"] == 0
    assert result["structural_preserved"] is True
    assert [entry["id"] for entry in result["omitted_nodes"]] == ["order_reserve"]
    assert result["omitted_nodes"][0]["reason"] == "existing_identity_collision"


def test_native_compose_fuzzy_ghost_collision_remaps_without_copying_llm_fields(
    overlay_corpus, tmp_path: Path
) -> None:
    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])
    before_bytes = graph_path.read_bytes()
    baseline = _read_graph(graph_path)
    baseline_node = next(node for node in baseline["nodes"] if node["id"] == "order_reserve")
    baseline_edge = next(link for link in baseline["links"] if link["relation"] == "calls")

    fragment = {
        "nodes": [
            {
                "id": "ghost_reserve",
                "label": "reserve()",
                "source_file": "order.py",
                "file_type": "code",
                "rationale": "model reasoning about reserve",
                "author": "llm-author",
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
    result = graph_worker.execute(
        {**request, "action": "semantic_apply", "arguments": {"fragment": fragment}}
    )

    after = _read_graph(graph_path)
    after_ids = {node["id"] for node in after["nodes"]}
    assert not {"ghost_reserve", "ghost_charge"} & after_ids
    node = next(item for item in after["nodes"] if item["id"] == "order_reserve")
    assert _structural_attrs(node) == _structural_attrs(baseline_node)
    for forbidden in ("rationale", "author"):
        assert forbidden not in node
    edge = next(link for link in after["links"] if link["relation"] == "calls")
    assert _structural_attrs(edge) == _structural_attrs(baseline_edge)
    # Nothing was accepted, so no publication transaction rewrites the graph.
    assert graph_path.read_bytes() == before_bytes

    assert result["applied_nodes"] == 0
    assert result["applied_edges"] == 0
    assert result["structural_preserved"] is True
    reasons = {entry["id"]: entry["reason"] for entry in result["omitted_nodes"]}
    assert reasons == {
        "ghost_reserve": "remapped_onto:order_reserve",
        "ghost_charge": "remapped_onto:order_charge",
    }
    assert len(result["omitted_edges"]) == 1
    assert result["omitted_edges"][0]["reason"] == "structural_edge_collision"


def test_native_compose_reverse_direction_collision_omitted_with_reason(
    overlay_corpus, tmp_path: Path
) -> None:
    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])
    before_bytes = graph_path.read_bytes()
    baseline = _read_graph(graph_path)
    baseline_edge = next(link for link in baseline["links"] if link["relation"] == "calls")

    fragment = {
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
    result = graph_worker.execute(
        {**request, "action": "semantic_apply", "arguments": {"fragment": fragment}}
    )

    after = _read_graph(graph_path)
    calls_edges = [link for link in after["links"] if link["relation"] == "calls"]
    assert len(calls_edges) == 1
    assert _structural_attrs(calls_edges[0]) == _structural_attrs(baseline_edge)
    # Nothing was accepted, so no publication transaction rewrites the graph.
    assert graph_path.read_bytes() == before_bytes

    assert result["applied_edges"] == 0
    assert len(result["omitted_edges"]) == 1
    assert result["omitted_edges"][0]["reason"] == "structural_edge_collision"


def test_native_compose_hyperedges_remapped_or_rejected(overlay_corpus, tmp_path: Path) -> None:
    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])

    fragment = {
        "nodes": [
            {
                "id": "ghost_reserve",
                "label": "reserve()",
                "source_file": "order.py",
                "file_type": "code",
            },
            {
                "id": "guide_flow",
                "label": "Guide flow",
                "source_file": "README.md",
                "file_type": "document",
            },
        ],
        "edges": [],
        "hyperedges": [
            {
                "id": "flow_overlay",
                "nodes": ["ghost_reserve", "order_charge"],
                "relation": "flow",
                "confidence": "INFERRED",
                "source_file": "README.md",
            },
            {
                "id": "flow_structural",
                "nodes": ["order_reserve", "order_charge"],
                "relation": "flow",
                "confidence": "EXTRACTED",
                "source_file": "order.py",
            },
            {
                "id": "flow_missing",
                "nodes": ["guide_flow", "not_a_node"],
                "relation": "flow",
                "confidence": "INFERRED",
                "source_file": "README.md",
            },
            {
                "id": "flow_empty",
                "nodes": [],
                "relation": "flow",
                "confidence": "INFERRED",
                "source_file": "README.md",
            },
        ],
    }
    result = graph_worker.execute(
        {**request, "action": "semantic_compose", "arguments": {"fragments": [fragment]}}
    )
    assert result["applied_nodes"] == 1
    assert result["applied_edges"] == 0
    assert result["applied_hyperedges"] == 1
    assert result["structural_preserved"] is True
    omitted = {entry["id"]: entry["reason"] for entry in result["omitted_hyperedges"]}
    assert omitted == {
        "flow_structural": "structural_hyperedge_collision",
        "flow_missing": "unresolved_members",
        "flow_empty": "no_valid_members",
    }
    unresolved = next(
        entry for entry in result["omitted_hyperedges"] if entry["id"] == "flow_missing"
    )
    assert unresolved["members"] == ["not_a_node"]

    after = _read_graph(graph_path)
    hyperedges = {hyperedge["id"]: hyperedge for hyperedge in after["hyperedges"]}
    assert set(hyperedges) == {"flow_structural", "flow_overlay"}
    assert hyperedges["flow_structural"]["nodes"] == ["order_reserve", "order_charge"]
    assert hyperedges["flow_structural"]["_origin"] == "ast"
    assert hyperedges["flow_overlay"]["nodes"] == ["order_reserve", "order_charge"]
    assert hyperedges["flow_overlay"]["origin"] == "llm"
    assert hyperedges["flow_overlay"]["_origin"] == "llm"
    assert hyperedges["flow_overlay"]["confidence"] == "INFERRED"
    assert "not_a_node" not in json.dumps(after["hyperedges"])


def test_native_compose_single_load_cluster_export_without_build_merge(
    overlay_corpus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import graphify.build as gbuild
    import graphify.cluster as gcluster
    import graphify.export as gexport

    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])

    counts = {"load": 0, "cluster": 0, "export": 0}
    real_load = gbuild._load_existing_graph  # type: ignore[attr-defined]

    def counting_load(path):
        counts["load"] += 1
        return real_load(path)

    real_cluster = gcluster.cluster

    def counting_cluster(*args, **kwargs):
        counts["cluster"] += 1
        return real_cluster(*args, **kwargs)

    real_export = gexport.to_json

    def counting_export(*args, **kwargs):
        counts["export"] += 1
        return real_export(*args, **kwargs)

    def forbidden_build_merge(*args, **kwargs):
        raise AssertionError("build_merge must never run for semantic composition")

    monkeypatch.setattr(gbuild, "_load_existing_graph", counting_load)
    monkeypatch.setattr(gcluster, "cluster", counting_cluster)
    monkeypatch.setattr(gexport, "to_json", counting_export)
    monkeypatch.setattr(gbuild, "build_merge", forbidden_build_merge)

    fragments = [
        {
            "nodes": [
                {
                    "id": f"note_{index}",
                    "label": f"Note {index}",
                    "source_file": "README.md",
                    "file_type": "document",
                }
            ],
            "edges": [
                {
                    "source": f"note_{index}",
                    "target": "readme_reservations",
                    "relation": "references",
                    "confidence": "INFERRED",
                    "source_file": "README.md",
                }
            ],
        }
        for index in range(3)
    ]
    result = graph_worker.execute(
        {**request, "action": "semantic_compose", "arguments": {"fragments": fragments}}
    )
    assert result["applied_nodes"] == 3
    assert result["applied_edges"] == 3
    assert counts == {"load": 1, "cluster": 1, "export": 1}

    after = _read_graph(graph_path)
    assert {"note_0", "note_1", "note_2"} <= {node["id"] for node in after["nodes"]}

    # The compatibility wrapper forwards the single model fragment through the
    # same overlay transaction (never build_merge). Its strict validation keeps
    # the endpoint-binding oracle, so it reads the base once for validation and
    # once for the compose transaction — exactly the two reads the previous
    # wrapper performed (validation + merge).
    wrapper = graph_worker.execute(
        {
            **request,
            "action": "semantic_apply",
            "arguments": {
                "model_text": json.dumps(
                    {
                        "nodes": [
                            {
                                "id": "note_wrapper",
                                "label": "Wrapper note",
                                "source_file": "README.md",
                                "file_type": "document",
                            }
                        ],
                        "edges": [],
                    }
                )
            },
        }
    )
    assert wrapper["applied_nodes"] == 1
    assert wrapper["structural_preserved"] is True
    assert counts == {"load": 3, "cluster": 2, "export": 2}


def test_native_compose_digest_mismatch_aborts_without_writing(
    overlay_corpus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    request = _prepare_overlay_request(overlay_corpus, tmp_path)
    graph_path = Path(request["graph_path"])
    before_bytes = graph_path.read_bytes()

    original = graph_worker._compose_candidate_graph

    def lossy_compose(*args, **kwargs):
        candidate = original(*args, **kwargs)
        candidate.remove_node("readme_current_documentation_7")
        return candidate

    monkeypatch.setattr(graph_worker, "_compose_candidate_graph", lossy_compose)
    arguments = {
        "fragments": [
            {
                "nodes": [
                    {
                        "id": "notes_overview",
                        "label": "Overview notes",
                        "source_file": "README.md",
                        "file_type": "document",
                    }
                ],
                "edges": [],
            }
        ]
    }
    with pytest.raises(ValueError, match="[Ss]tructural projection changed"):
        graph_worker.execute({**request, "action": "semantic_compose", "arguments": arguments})
    assert graph_path.read_bytes() == before_bytes

    monkeypatch.setattr(
        sys,
        "stdin",
        SimpleNamespace(
            buffer=io.BytesIO(
                json.dumps(
                    {**request, "action": "semantic_compose", "arguments": arguments}
                ).encode("utf-8")
            )
        ),
    )
    assert graph_worker.main() == 1
    response = json.loads(capsys.readouterr().out)
    assert response["ok"] is False
    assert "Structural projection changed" in response["message"]
    assert graph_path.read_bytes() == before_bytes


def test_native_compose_preserves_directed_graph_direction(overlay_corpus, tmp_path: Path) -> None:
    graph_path = tmp_path / "directed-graph.json"
    graph_path.write_text(
        json.dumps(_overlay_graph_data(directed=True), indent=2), encoding="utf-8"
    )
    request = {**overlay_corpus, "graph_path": str(graph_path)}
    baseline = _read_graph(graph_path)
    baseline_links = {
        (link["source"], link["target"], link["relation"]) for link in baseline["links"]
    }

    canary = {
        "nodes": [
            {
                "id": "notes_overview",
                "label": "Overview notes",
                "source_file": "README.md",
                "file_type": "document",
            }
        ],
        "edges": [],
    }
    result = graph_worker.execute(
        {**request, "action": "semantic_compose", "arguments": {"fragments": [canary]}}
    )
    assert result["applied_nodes"] == 1
    assert result["structural_preserved"] is True

    after = _read_graph(graph_path)
    assert after["directed"] is True
    after_links = {(link["source"], link["target"], link["relation"]) for link in after["links"]}
    assert baseline_links <= after_links
