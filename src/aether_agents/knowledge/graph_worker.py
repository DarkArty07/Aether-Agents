"""Private subprocess entry point; Graphify imports stay outside Hermes.

This file is executed by the configured component interpreter, not imported by
Aether. It adapts the fixed upstream functions, rather than maintaining another
graph search engine. The JSON request is produced only by the trusted adapter.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def normalize_recovery_wording(text: str) -> str:
    # 1. Complete over budget recovery notice (checked first before shorter pattern)
    text = re.sub(
        r"raising --budget further will not shrink it\. Narrow with context_filter=\[[^\]]*\] or use get_node for a specific symbol to reduce size instead\.",
        "raising budget_tokens further will not shrink it. Narrow the question or call explain on a returned node to reduce size instead.",
        text,
    )
    # 2. Truncated header recovery notice
    text = re.sub(
        r"raise the token budget \(CLI: --budget\) or narrow the query \(e\.g\. context_filter=\[[^\]]*\], or get_node for a specific symbol\)\.",
        "raise budget_tokens (128-8000), narrow the question, or call explain on a returned node.",
        text,
    )
    # 3. Truncated footer recovery notice
    text = re.sub(
        r"Narrow with context_filter=\[[^\]]*\] or use get_node for a specific symbol",
        "Narrow the question, raise budget_tokens (128-8000), or call explain on a returned node",
        text,
    )
    text = re.sub(
        r"Narrow with relation_filter or use get_node for a specific symbol",
        "Narrow the question, raise budget_tokens (128-8000), or call explain on a returned node",
        text,
    )
    text = re.sub(
        r"Raise token_budget or use get_node for specific members",
        "Raise budget_tokens (128-8000), narrow the question, or call explain on a returned node",
        text,
    )
    # 4. Shortest path directed-path recovery notice
    text = re.sub(
        r"Retry with undirected=true to search ignoring edge direction\.",
        "Call explain on a returned node to inspect connections, or narrow the question.",
        text,
    )
    text = re.sub(
        r"Retry with undirected=true[^\.\n]*[\.\n]?",
        "Call explain on a returned node to inspect connections, or narrow the question.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bundirected\s*=\s*true\b", "explain on a returned node", text, flags=re.IGNORECASE
    )

    # 5. Strip unsupported MCP and CLI tool recovery phrasing
    text = re.sub(
        r"\b(?:[Uu]se\s+)?(?:the\s+)?MCP\s+(?:get_node|explain)(?:\s+tool)?\b",
        "call explain on a returned node",
        text,
    )
    text = re.sub(
        r"\b(?:[Uu]se\s+)?(?:the\s+)?get_node(?:\s+tool)?\b",
        "call explain on a returned node",
        text,
    )
    text = re.sub(
        r"\b(?:[Uu]se\s+)?(?:the\s+)?MCP\s+tool\b",
        "call explain on a returned node",
        text,
    )
    text = re.sub(r"\bMCP\s+([a-zA-Z0-9_]+)\s+tool\b", r"\1", text)
    text = re.sub(r"\bMCP\s*", "", text)

    # 6. Residual mentions of context_filter in recovery advice, get_node, CLI: --budget, --budget
    text = re.sub(r"\bcontext_filter=\[[^\]]*\]", "narrower question", text)
    text = re.sub(r"\brelation_filter\b", "question", text)
    text = re.sub(r"\btoken_budget\b", "budget_tokens", text)
    text = re.sub(r"\bget_node\b", "explain", text)
    text = text.replace("CLI: --budget", "budget_tokens")
    text = re.sub(r"\bCLI:\s*", "", text)
    text = text.replace("--budget", "budget_tokens")

    # 7. Remove any Graph: /path/to/graph.json (N nodes) | header prefix to keep snapshot path internal
    text = re.sub(r"^Graph:\s+[^\s|]+\s+\(\d+\s+nodes\)\s+\|\s+", "", text)
    return text


def _extract_subgraph_references(content: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in content.splitlines():
        if line.startswith("NODE "):
            m = re.search(r"\[src=([^\s\]]+)(?:\s+loc=([^\s\]]*))?", line)
            if m:
                p = m.group(1)
                loc = m.group(2) or ""
                if p and (p, loc) not in seen:
                    seen.add((p, loc))
                    refs.append({"path": p, "location": loc})
        elif line.startswith("EDGE "):
            m = re.search(r"\sat=([^:\s]+):(\S*)", line)
            if m:
                p = m.group(1)
                loc = m.group(2)
                if p and (p, loc) not in seen:
                    seen.add((p, loc))
                    refs.append({"path": p, "location": loc})
    return refs


def _sanitize_and_validate_fragment(
    raw_fragment: Any,
    allowed_sources: list[str] | None = None,
    allow_empty: bool = False,
    graph_path: Path | None = None,
    source_root: Path | None = None,
) -> dict[str, Any]:
    import graphify.build as _gbuild  # type: ignore[import-untyped]
    from graphify.build import build_from_json  # type: ignore[import-untyped]
    from graphify.semantic_cleanup import validate_semantic_fragment

    _load_existing_graph = getattr(_gbuild, "_load_existing_graph")

    if not isinstance(raw_fragment, dict):
        raise ValueError("Parsed model fragment must be a dictionary.")

    errors = validate_semantic_fragment(raw_fragment)
    if errors:
        raise ValueError(f"Semantic fragment schema validation failed: {'; '.join(errors)}")

    nodes = raw_fragment.get("nodes", [])
    edges = raw_fragment.get("edges", [])
    if not nodes and not edges and not allow_empty:
        raise ValueError("Hollow model fragment: both nodes and edges are empty.")

    allowed_set = set(allowed_sources) if allowed_sources else None

    sanitized_nodes = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        sf = node.get("source_file")
        if allowed_set is not None and sf and sf not in allowed_set:
            continue
        n = dict(node)
        n["_origin"] = "llm"
        n["origin"] = "llm"
        conf = str(n.get("confidence") or "").upper()
        if conf == "EXTRACTED" or not conf:
            n["confidence"] = "INFERRED"
        else:
            n["confidence"] = conf
        if not n.get("source_location"):
            n["source_location"] = None
        sanitized_nodes.append(n)

    sanitized_edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        sf = edge.get("source_file")
        if allowed_set is not None and sf and sf not in allowed_set:
            continue
        e = dict(edge)
        e["_origin"] = "llm"
        e["origin"] = "llm"
        conf = str(e.get("confidence") or "").upper()
        if conf == "EXTRACTED" or not conf:
            e["confidence"] = "INFERRED"
        else:
            e["confidence"] = conf
        if not e.get("source_location"):
            e["source_location"] = None
        sanitized_edges.append(e)

    sanitized_hyperedges = []
    for he in raw_fragment.get("hyperedges", []):
        if not isinstance(he, dict):
            continue
        sf = he.get("source_file")
        if allowed_set is not None and sf and sf not in allowed_set:
            continue
        h = dict(he)
        h["_origin"] = "llm"
        h["origin"] = "llm"
        conf = str(h.get("confidence") or "").upper()
        if conf == "EXTRACTED" or not conf:
            h["confidence"] = "INFERRED"
        else:
            h["confidence"] = conf
        sanitized_hyperedges.append(h)

    # Re-validate surviving elements for hollowness post-filter
    if not sanitized_nodes and not sanitized_edges and not allow_empty:
        raise ValueError("Hollow model fragment: no nodes or edges survived source validation.")

    # Endpoint integrity check: every surviving edge must bind to accepted fragment or structural nodes
    existing_nodes: list[dict] = []
    if graph_path and graph_path.is_file():
        loaded = _load_existing_graph(graph_path)
        if loaded is not None:
            existing_nodes = loaded[0]

    for edge in sanitized_edges:
        test_G = build_from_json(
            {"nodes": list(existing_nodes) + list(sanitized_nodes), "edges": [edge]},
            directed=True,
            root=source_root,
        )
        if test_G.number_of_edges() == 0:
            s_name = edge.get("source", edge.get("from"))
            t_name = edge.get("target", edge.get("to"))
            raise ValueError(
                f"Semantic edge endpoints do not bind to accepted fragment or structural nodes: '{s_name}' -> '{t_name}'."
            )

    return {
        "nodes": sanitized_nodes,
        "edges": sanitized_edges,
        "hyperedges": sanitized_hyperedges,
    }


def _parse_and_validate_semantic(
    model_text: str,
    allowed_sources: list[str] | None = None,
    allow_empty: bool = False,
    graph_path: Path | None = None,
    source_root: Path | None = None,
) -> dict[str, Any]:
    from graphify.llm import _parse_llm_json

    if not model_text or not isinstance(model_text, str):
        raise ValueError("model_text must be a non-empty string.")
    try:
        raw_fragment = _parse_llm_json(model_text)
    except Exception as exc:
        raise ValueError(f"Malformed model text: failed to parse JSON: {exc}") from exc

    if not raw_fragment.get("nodes") and not raw_fragment.get("edges"):
        try:
            parsed = json.loads(model_text.strip())
        except Exception:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", model_text, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception as exc:
                    raise ValueError(f"Malformed model text: invalid JSON: {exc}") from exc
            else:
                raise ValueError("Malformed model text: no valid JSON found.")
        if not parsed.get("nodes") and not parsed.get("edges") and not allow_empty:
            raise ValueError("Hollow model fragment: both nodes and edges are empty.")
        raw_fragment = parsed

    return _sanitize_and_validate_fragment(
        raw_fragment,
        allowed_sources=allowed_sources,
        allow_empty=allow_empty,
        graph_path=graph_path,
        source_root=source_root,
    )


def execute(request: dict) -> dict:
    if importlib.metadata.version("graphifyy") != "0.9.54":
        raise ValueError("The configured Graphify version is not qualified.")
    action = request["action"]
    if action == "probe":
        return {"version": "0.9.54", "python": sys.version.split()[0]}
    if action in ("memory_save", "memory_reflect"):
        import tempfile

        args = request.get("arguments", {})
        with tempfile.TemporaryDirectory(prefix="role-notes-") as temporary:
            root = Path(temporary)
            if action == "memory_save":
                from graphify.ingest import save_query_result

                note = save_query_result(
                    question=args["situation"],
                    answer=args["lesson"] + "\n\n## Applicability\n\n" + args["applicability"],
                    memory_dir=root / "notes",
                    source_nodes=args.get("source_nodes"),
                    outcome=args["outcome"],
                    correction=args.get("correction"),
                )
                return {"content": note.read_text(encoding="utf-8")}
            from graphify.reflect import reflect

            notes = root / "notes"
            notes.mkdir()
            for index, body in enumerate(args["notes"]):
                (notes / f"note_{index:06d}.md").write_text(body, encoding="utf-8")
            report, aggregate = reflect(notes, root / "LESSONS.md", graph_path=None)
            return {"content": report.read_text(encoding="utf-8"), "count": aggregate["total"]}
    graph_path = Path(request["graph_path"])
    source_root = Path(request["source_root"])
    os.environ["GRAPHIFY_OUT"] = str(graph_path.parent)
    os.environ["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    if action == "update":
        from graphify.watch import _rebuild_code

        if not _rebuild_code(source_root, no_cluster=False, block_on_lock=True):
            raise ValueError("Graphify did not complete structural extraction.")
        if not graph_path.is_file():
            raise ValueError("Graphify did not create a graph.")
        return {"content": "Structural graph built.", "references": []}

    args = request.get("arguments", {})
    budget = args.get("budget_tokens", 2000)

    if action == "stats":
        from graphify.serve import _communities_from_graph, _load_graph

        graph = _load_graph(str(graph_path))
        communities = _communities_from_graph(graph)
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
        community_count = len(communities)

        confidence_counts = {
            "EXTRACTED": 0,
            "INFERRED": 0,
            "AMBIGUOUS": 0,
            "UNKNOWN": 0,
        }
        for _, _, d in graph.edges(data=True):
            conf = d.get("confidence")
            if isinstance(conf, str) and conf.upper() in confidence_counts:
                confidence_counts[conf.upper()] += 1
            else:
                confidence_counts["UNKNOWN"] += 1

        origin_counts = {
            "structural": 0,
            "llm": 0,
            "unknown": 0,
        }

        def _classify(d: dict) -> str:
            o = str(d.get("origin") or d.get("_origin") or "").lower()
            if o in ("ast", "structural"):
                return "structural"
            if o in ("llm", "semantic"):
                return "llm"
            return "unknown"

        for _, d in graph.nodes(data=True):
            origin_counts[_classify(d)] += 1
        for _, _, d in graph.edges(data=True):
            origin_counts[_classify(d)] += 1

        content = (
            f"Graph stats: {node_count} nodes, {edge_count} edges across {community_count} communities. "
            f"Confidence: {confidence_counts['EXTRACTED']} extracted, {confidence_counts['INFERRED']} inferred, "
            f"{confidence_counts['AMBIGUOUS']} ambiguous, {confidence_counts['UNKNOWN']} unknown. "
            f"Origin: {origin_counts['structural']} structural, {origin_counts['llm']} llm, {origin_counts['unknown']} unknown."
        )
        return {
            "content": content,
            "references": [],
            "stats": {
                "node_count": node_count,
                "edge_count": edge_count,
                "community_count": community_count,
                "confidence_counts": confidence_counts,
                "origin_counts": origin_counts,
            },
        }

    if action == "god_nodes":
        from graphify.analyze import god_nodes
        from graphify.serve import _load_graph

        graph = _load_graph(str(graph_path))
        top_n = int(args.get("top_n", 10))
        exclude_hubs_percentile = args.get("exclude_hubs_percentile")
        god_kwargs: dict[str, Any] = {"top_n": top_n}
        if exclude_hubs_percentile is not None:
            god_kwargs["exclude_hubs_percentile"] = float(exclude_hubs_percentile)

        raw_gods = god_nodes(graph, **god_kwargs)
        node_entries = []
        references = []
        seen_refs = set()
        lines = [f"God nodes (top {len(raw_gods)} by degree):"]
        for i, item in enumerate(raw_gods, 1):
            nid = item["id"]
            node_data = graph.nodes.get(nid, {})
            cid = node_data.get("community")
            comm_id = int(cid) if cid is not None else None
            node_entry = {
                "id": nid,
                "label": item.get("label", nid),
                "degree": item.get("degree", graph.degree(nid)),
                "community_id": comm_id,
            }
            node_entries.append(node_entry)
            lines.append(
                f"{i}. `{node_entry['label']}` - {node_entry['degree']} edges (community: {comm_id})"
            )
            if node_data.get("source_file"):
                p = str(node_data["source_file"])
                loc = str(node_data.get("source_location") or "")
                if (p, loc) not in seen_refs:
                    seen_refs.add((p, loc))
                    references.append({"path": p, "location": loc})

        content = normalize_recovery_wording("\n".join(lines))
        return {
            "content": content,
            "references": references,
            "nodes": node_entries,
        }

    if action == "query":
        from graphify.reflect import load_learning_overlay
        from graphify.serve import _query_graph_text
        from networkx.readwrite import json_graph  # type: ignore[import-untyped]

        raw = json.loads(graph_path.read_text(encoding="utf-8"))
        if "links" not in raw and "edges" in raw:
            raw = dict(raw, links=raw["edges"])
        raw = dict(
            raw,
            links=[
                {
                    **link,
                    "_src": link.get("_src", link.get("source")),
                    "_tgt": link.get("_tgt", link.get("target")),
                }
                for link in raw.get("links", [])
            ],
        )
        try:
            G = json_graph.node_link_graph(raw, edges="links")
        except TypeError:
            G = json_graph.node_link_graph(raw)
        try:
            G.graph["_learning_overlay"] = load_learning_overlay(graph_path)
        except Exception:
            G.graph["_learning_overlay"] = {}

        traversal = str(args.get("traversal", "bfs")).lower()
        if traversal not in ("bfs", "dfs"):
            traversal = "bfs"
        depth = int(args.get("depth", 2))
        raw_cf = args.get("context_filter") or args.get("context_filters")
        if raw_cf is not None:
            context_filters = [raw_cf] if isinstance(raw_cf, str) else list(raw_cf)
        else:
            context_filters = []

        raw_content = _query_graph_text(
            G,
            args["question"],
            mode=traversal,
            depth=depth,
            token_budget=budget,
            context_filters=context_filters,
            graph_path=None,
        )
        native_truncated = "[!] TRUNCATED: showing " in raw_content
        over_budget_complete = "[i] Complete answer over budget: " in raw_content
        content = normalize_recovery_wording(raw_content)
        references = _extract_subgraph_references(content)
        return {
            "content": content,
            "references": references,
            "truncated": native_truncated,
            "over_budget_complete": over_budget_complete,
            "query_options": {
                "traversal": traversal,
                "depth": depth,
                "context_filter": context_filters,
            },
        }

    if action == "explain":
        from graphify.__main__ import main
        from graphify.build import edge_data
        from graphify.serve import _find_node, _load_graph, find_node_ambiguity

        G = _load_graph(str(graph_path))
        label = args["node"]
        matches = _find_node(G, label)
        if not matches:
            raise ValueError(f"No node matching '{label}' found.")
        rivals = find_node_ambiguity(G, label)
        if rivals:
            raise ValueError(
                f"Ambiguous: '{label}' matches {len(rivals)} nodes in different files."
            )
        nid = matches[0]
        d = G.nodes[nid]
        cid = d.get("community")
        cname = d.get("community_name")
        resolved_node = {
            "id": nid,
            "community_id": int(cid) if cid is not None else None,
            "community_name": str(cname) if cname else None,
        }

        sys.argv = ["graphify", "explain", label, "--graph", str(graph_path)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main()
        content = normalize_recovery_wording(output.getvalue())

        references = []
        seen = set()
        if d.get("source_file"):
            p = str(d["source_file"])
            loc = str(d.get("source_location") or "")
            seen.add((p, loc))
            references.append({"path": p, "location": loc})
        connections: list[tuple[str, str, dict]] = []
        for nb in G.successors(nid):
            _ed = edge_data(G, nid, nb)
            connections.append(("out" if _ed.get("_src", nid) == nid else "in", nb, _ed))
        for nb in G.predecessors(nid):
            _ed = edge_data(G, nb, nid)
            connections.append(("in" if _ed.get("_src", nb) == nb else "out", nb, _ed))
        connections.sort(key=lambda c: G.degree(c[1]), reverse=True)
        for direction, nb, edata in connections[:20]:
            if edata.get("source_file"):
                p = str(edata["source_file"])
                loc = str(edata.get("source_location") or "")
                if (p, loc) not in seen:
                    seen.add((p, loc))
                    references.append({"path": p, "location": loc})

        return {
            "content": content,
            "references": references,
            "resolved_node": resolved_node,
        }

    if action == "impact":
        from graphify.affected import affected_nodes, format_affected, load_graph, resolve_seed

        G = load_graph(graph_path)
        node_arg = args["node"]
        seed = resolve_seed(G, node_arg)
        if seed is None:
            raise ValueError(f"No unique node match for '{node_arg}'.")
        depth = int(args.get("depth", 2))
        relations = args.get("relations")
        impact_kwargs: dict[str, Any] = {"depth": depth}
        if relations is not None:
            impact_kwargs["relations"] = tuple(relations)

        content = normalize_recovery_wording(format_affected(G, node_arg, **impact_kwargs))
        hits = affected_nodes(G, seed, **impact_kwargs)

        references = []
        seen = set()
        seed_data = G.nodes[seed]
        if seed_data.get("source_file"):
            p = str(seed_data["source_file"])
            loc = str(seed_data.get("source_location") or "")
            seen.add((p, loc))
            references.append({"path": p, "location": loc})
        for hit in hits:
            hit_data = G.nodes[hit.node_id]
            if hit.via_location:
                ref_path = hit.via_file or hit_data.get("source_file") or ""
                ref_loc = hit.via_location or ""
            else:
                ref_path = hit_data.get("source_file") or ""
                ref_loc = hit_data.get("source_location") or ""
            if ref_path and ref_path != "-":
                p = str(ref_path)
                loc = str(ref_loc)
                if (p, loc) not in seen:
                    seen.add((p, loc))
                    references.append({"path": p, "location": loc})
        return {
            "content": content,
            "references": references,
        }

    if action == "path":
        import networkx as nx  # type: ignore[import-untyped]
        from graphify.serve import (
            _load_graph,
            _pick_scored_endpoint,
            _score_nodes,
            _shortest_path_text,
            edge_datas,
        )

        graph = _load_graph(str(graph_path))
        undirected = bool(args.get("undirected", False))
        arguments = {
            "source": args["source"],
            "target": args["target"],
            "max_hops": args.get("max_hops", 8),
            "undirected": undirected,
        }
        content = normalize_recovery_wording(_shortest_path_text(graph, arguments))
        references = []
        seen = set()
        src_scored = _score_nodes(graph, [t.lower() for t in args["source"].split()])
        tgt_scored = _score_nodes(graph, [t.lower() for t in args["target"].split()])
        if src_scored and tgt_scored:
            src_nid = _pick_scored_endpoint(graph, src_scored, args["source"])
            tgt_nid = _pick_scored_endpoint(graph, tgt_scored, args["target"])
            if src_nid != tgt_nid:
                if undirected:
                    _und = nx.Graph()
                    _und.add_nodes_from(sorted(graph.nodes))
                    _und.add_edges_from(sorted((min(u, v), max(u, v)) for u, v in graph.edges()))
                    search_graph = _und
                else:
                    _dg = nx.DiGraph()
                    _dg.add_nodes_from(sorted(graph.nodes))
                    _dg.add_edges_from(
                        sorted(
                            (d.get("_src", u), d.get("_tgt", v))
                            for u, v, d in graph.edges(data=True)
                        )
                    )
                    search_graph = _dg
                try:
                    path_nodes = nx.shortest_path(search_graph, src_nid, tgt_nid)
                    if len(path_nodes) - 1 <= int(args.get("max_hops", 8)):
                        for i in range(len(path_nodes)):
                            u = path_nodes[i]
                            if graph.nodes[u].get("source_file"):
                                p = str(graph.nodes[u]["source_file"])
                                loc = str(graph.nodes[u].get("source_location") or "")
                                if (p, loc) not in seen:
                                    seen.add((p, loc))
                                    references.append({"path": p, "location": loc})
                            if i + 1 < len(path_nodes):
                                v = path_nodes[i + 1]
                                datas = []
                                if graph.has_edge(u, v):
                                    datas = edge_datas(graph, u, v)
                                elif graph.has_edge(v, u):
                                    datas = edge_datas(graph, v, u)
                                for ed in datas:
                                    if ed.get("source_file"):
                                        p = str(ed["source_file"])
                                        loc = str(ed.get("source_location") or "")
                                        if (p, loc) not in seen:
                                            seen.add((p, loc))
                                            references.append({"path": p, "location": loc})
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass
        return {
            "content": content,
            "references": references,
        }

    if action == "visualize":
        from graphify.exporters.html import to_html
        from graphify.serve import _communities_from_graph, _load_graph
        from graphify.tree_html import write_tree_html

        fmt = str(args.get("format", "graph")).lower()
        detail = str(args.get("detail", "auto")).lower()
        export_path_str = request.get("export_path") or args.get("export_path")
        if not export_path_str:
            raise ValueError("export_path is required for visualize action.")
        export_path = Path(export_path_str)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        project_label = args.get("project_label") or request.get("project_label")
        if not project_label:
            pid = args.get("project_id") or request.get("project_id")
            rev = args.get("revision") or request.get("revision")
            if pid and rev:
                project_label = f"{pid} @ {rev}"
            elif pid:
                project_label = str(pid)
            elif rev:
                project_label = str(rev)

        graph = _load_graph(str(graph_path))
        total_nodes = graph.number_of_nodes()

        if fmt == "tree":
            write_tree_html(
                graph_path,
                export_path,
                project_label=project_label,
            )
            raw_bytes = export_path.read_bytes()
            external_assets = ["https://d3js.org/d3.v7.min.js"]
            rendered_nodes = total_nodes
            aggregated = False
        elif fmt == "graph":
            communities = _communities_from_graph(graph)
            if detail == "auto":
                node_limit = 5000
                aggregated = total_nodes > 5000
            else:
                node_limit = None
                aggregated = False
                os.environ["GRAPHIFY_VIZ_NODE_LIMIT"] = "50000"

            to_html(
                graph,
                communities,
                str(export_path),
                node_limit=node_limit,
            )
            html_text = export_path.read_text(encoding="utf-8")
            if project_label:
                import html as py_html

                escaped_label = py_html.escape(str(project_label))
                html_text = re.sub(
                    r"<title>graphify - [^<]*</title>",
                    f"<title>graphify - {escaped_label}</title>",
                    html_text,
                )
                html_text = html_text.replace(
                    '<div id="stats">',
                    f'<div id="stats"><span id="project-identity">{escaped_label}</span><br>',
                )
                export_path.write_text(html_text, encoding="utf-8")

            raw_bytes = export_path.read_bytes()
            external_assets = [
                "https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"
            ]
            if aggregated:
                match = re.search(
                    r"const RAW_NODES = (\[.*?\]);\nconst RAW_EDGES", html_text, re.DOTALL
                )
                rendered_nodes = len(json.loads(match.group(1))) if match else len(communities)
            else:
                rendered_nodes = total_nodes
        else:
            raise ValueError(f"Unsupported visualize format '{fmt}'.")

        artifact = {
            "format": fmt,
            "local_path": str(export_path),
            "bytes": len(raw_bytes),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "rendered_nodes": rendered_nodes,
            "total_nodes": total_nodes,
            "aggregated": aggregated,
            "external_assets": external_assets,
        }
        content = (
            f"Exported {fmt} visualization to {export_path.name} "
            f"({rendered_nodes}/{total_nodes} nodes rendered, aggregated={aggregated})."
        )
        return {
            "content": content,
            "references": [],
            "artifact": artifact,
        }

    if action in ("pr_impact", "compute_pr_impact"):
        from graphify.prs import compute_pr_impact
        from graphify.serve import _load_graph

        graph = _load_graph(str(graph_path))
        files = args.get("files", [])
        if not isinstance(files, list):
            raise ValueError("files must be a list of file paths.")

        # Index graph source files for matching
        graph_files = {
            str(d.get("source_file")) for _, d in graph.nodes(data=True) if d.get("source_file")
        }
        matched_files = []
        unmatched_files = []
        for f in files:
            is_match = any(
                src == f or src.endswith("/" + f) or f.endswith("/" + src) for src in graph_files
            )
            if is_match:
                matched_files.append(f)
            else:
                unmatched_files.append(f)

        communities_touched, nodes_affected = compute_pr_impact(files, graph)

        references = []
        seen_refs = set()
        for _, d in graph.nodes(data=True):
            src = d.get("source_file")
            if src and any(
                src == f or src.endswith("/" + f) or f.endswith("/" + src) for f in matched_files
            ):
                loc = str(d.get("source_location") or "")
                if (src, loc) not in seen_refs:
                    seen_refs.add((src, loc))
                    references.append({"path": str(src), "location": loc})
                    if len(references) >= 50:
                        break

        impact_info = {
            "files": len(files),
            "matched_files": matched_files,
            "unmatched_files": unmatched_files,
            "communities": communities_touched,
            "node_count": nodes_affected,
        }
        content = (
            f"PR impact: {len(matched_files)} matched files, {len(unmatched_files)} unmatched files, "
            f"{len(communities_touched)} communities touched, {nodes_affected} nodes affected."
        )
        return {
            "content": content,
            "references": references,
            "impact": impact_info,
        }

    if action == "semantic_prepare":
        from graphify.llm import (
            _extraction_system,
            _pack_chunks_by_tokens,
            _read_files,
            expand_oversized_files,
        )

        file_list = args.get("files", [])
        max_chars = int(args.get("max_chars", 100_000))
        token_budget = int(args.get("token_budget", 4000))
        file_paths = [source_root / f for f in file_list if (source_root / f).is_file()]
        expanded = expand_oversized_files(file_paths, max_chars=max_chars)
        packed_chunks = _pack_chunks_by_tokens(expanded, token_budget=token_budget)
        system_prompt = _extraction_system(deep=False)
        chunks = []
        for idx, chunk in enumerate(packed_chunks):
            user_prompt = _read_files(chunk, root=source_root)
            paths = []
            for item in chunk:
                p = getattr(item, "path", item)
                try:
                    rel = str(Path(p).relative_to(source_root))
                except ValueError:
                    rel = str(p)
                paths.append(rel)
            chunks.append(
                {
                    "chunk_id": idx,
                    "files": paths,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                }
            )
        content = f"Prepared {len(chunks)} semantic extraction chunks from {len(file_paths)} files."
        return {
            "content": content,
            "references": [],
            "chunks": chunks,
        }

    if action in ("semantic_parse", "semantic_validate"):
        model_text = args.get("model_text", "")
        parsed = _parse_and_validate_semantic(
            model_text=model_text,
            allowed_sources=args.get("allowed_sources"),
            allow_empty=bool(args.get("allow_empty", False)),
            graph_path=graph_path,
            source_root=source_root,
        )
        return {
            "content": f"Semantic fragment valid: {len(parsed.get('nodes', []))} nodes, {len(parsed.get('edges', []))} edges.",
            "references": [],
            "fragment": parsed,
        }

    if action == "semantic_apply":
        import graphify.build as _gbuild  # type: ignore[import-untyped]
        import graphify.cluster as cluster
        import graphify.export as export
        from graphify.build import build_from_json, build_merge  # type: ignore[import-untyped]

        _is_ast_tier = getattr(_gbuild, "_is_ast_tier")
        _load_existing_graph = getattr(_gbuild, "_load_existing_graph")

        model_text = args.get("model_text")
        fragment = args.get("fragment")
        if model_text is not None:
            fragment = _parse_and_validate_semantic(
                model_text=model_text,
                allowed_sources=args.get("allowed_sources"),
                allow_empty=bool(args.get("allow_empty", False)),
                graph_path=graph_path,
                source_root=source_root,
            )
        elif fragment is None:
            raise ValueError("model_text or fragment is required for semantic_apply.")
        else:
            fragment = _sanitize_and_validate_fragment(
                fragment,
                allowed_sources=args.get("allowed_sources"),
                allow_empty=bool(args.get("allow_empty", False)),
                graph_path=graph_path,
                source_root=source_root,
            )

        loaded = _load_existing_graph(graph_path)
        if loaded is None:
            existing_nodes, existing_edges, existing_hyperedges, existing_directed = (
                [],
                [],
                [],
                False,
            )
        else:
            existing_nodes, existing_edges, existing_hyperedges, existing_directed = loaded

        structural_pairs = set()
        structural_directed = set()
        structural_edge_records: dict[tuple[str, str], dict] = {}
        for e in existing_edges:
            if not isinstance(e, dict):
                continue
            is_structural = (
                e.get("_origin") in ("ast", "structural")
                or e.get("origin") in ("ast", "structural")
                or _is_ast_tier(e)
            )
            if is_structural:
                es = str(e.get("source", e.get("from", "")))
                et = str(e.get("target", e.get("to", "")))
                if es and et:
                    structural_directed.add((es, et))
                    structural_pairs.add(frozenset({es, et}))
                    structural_edge_records[(es, et)] = dict(e)

        raw_edges = fragment.get("edges", [])
        fragment_nodes = fragment.get("nodes", [])
        kept_edges = []
        omitted_edges = []
        for e in raw_edges:
            test_G = build_from_json(
                {"nodes": list(existing_nodes) + list(fragment_nodes), "edges": [e]},
                directed=True,
                root=source_root,
            )
            if test_G.number_of_edges() == 0:
                omitted_edges.append(e)
                continue
            norm_u, norm_v = list(test_G.edges())[0]
            if not existing_directed:
                is_collision = frozenset({norm_u, norm_v}) in structural_pairs
            else:
                is_collision = (
                    (norm_u, norm_v) in structural_directed
                    or (norm_v, norm_u) in structural_directed
                    or frozenset({norm_u, norm_v}) in structural_pairs
                )
            if is_collision:
                omitted_edges.append(e)
                continue
            kept_edges.append(e)

        fragment_to_merge = dict(fragment, edges=kept_edges)
        merged_G = build_merge([fragment_to_merge], graph_path=graph_path, root=source_root)

        # Guarantee every structural relation/site/provenance field is preserved
        for (es, et), orig_data in structural_edge_records.items():
            if merged_G.has_edge(es, et):
                edata = merged_G.get_edge_data(es, et)
                edata["_origin"] = orig_data.get("_origin", "ast")
                edata["origin"] = orig_data.get("origin", orig_data.get("_origin", "ast"))
                if orig_data.get("relation"):
                    edata["relation"] = orig_data["relation"]
                if orig_data.get("source_location"):
                    edata["source_location"] = orig_data["source_location"]
                if orig_data.get("confidence"):
                    edata["confidence"] = orig_data["confidence"]

        comms = cluster.cluster(merged_G)
        export.to_json(merged_G, comms, str(graph_path), force=True)

        applied_edges_count = 0
        for e in kept_edges:
            test_G = build_from_json(
                {"nodes": list(existing_nodes) + list(fragment_nodes), "edges": [e]},
                directed=True,
                root=source_root,
            )
            if test_G.number_of_edges() > 0:
                nu, nv = list(test_G.edges())[0]
                if merged_G.has_edge(nu, nv):
                    edata = merged_G.get_edge_data(nu, nv)
                    if edata.get("origin") == "llm" or edata.get("_origin") == "llm":
                        applied_edges_count += 1

        applied_nodes_count = 0
        for n in fragment_nodes:
            nid = n.get("id")
            if nid and nid in merged_G:
                applied_nodes_count += 1
            else:
                sf, label = n.get("source_file"), n.get("label")
                if sf and label:
                    if any(
                        merged_G.nodes[m].get("source_file") == sf
                        and merged_G.nodes[m].get("label") == label
                        for m in merged_G.nodes()
                    ):
                        applied_nodes_count += 1

        references = []
        seen = set()
        for node in fragment_nodes:
            if node.get("source_file"):
                p = str(node["source_file"])
                loc = str(node.get("source_location") or "")
                if (p, loc) not in seen:
                    seen.add((p, loc))
                    references.append({"path": p, "location": loc})

        content = (
            f"Applied semantic fragment: {applied_nodes_count} nodes, "
            f"{applied_edges_count} edges merged, {len(omitted_edges)} colliding structural edges preserved."
        )
        return {
            "content": content,
            "references": references,
            "applied_nodes": applied_nodes_count,
            "applied_edges": applied_edges_count,
            "omitted_edges": omitted_edges,
        }

    from graphify.serve import (
        _bfs,
        _communities_from_graph,
        _load_graph,
        _resolve_single_node,
        _subgraph_to_text,
    )

    graph = _load_graph(str(graph_path))
    community_info = None
    if action == "neighbors":
        node, error = _resolve_single_node(graph, args["node"])
        if error or node is None:
            raise ValueError(error or "Node not found.")
        undirected = graph.to_undirected()
        nodes, _edges = _bfs(undirected, [node], 1)
        relation = args.get("relation", "").casefold()
        edges = [
            (a, b)
            for a, b, data in graph.edges(data=True)
            if a in nodes
            and b in nodes
            and (a == node or b == node)
            and (not relation or relation in str(data.get("relation", "")).casefold())
        ]
        nodes = {node} | {n for edge in edges for n in edge}
    elif action == "community":
        cid = int(args["community_id"])
        nodes = set(_communities_from_graph(graph).get(cid, []))
        if not nodes:
            raise ValueError("Community not found in this snapshot.")
        edges = [(a, b) for a, b in graph.edges() if a in nodes and b in nodes]
        cname = next(
            (
                str(graph.nodes[n]["community_name"])
                for n in nodes
                if graph.nodes[n].get("community_name")
            ),
            None,
        )
        community_info = {
            "id": cid,
            "name": cname,
            "node_count": len(nodes),
        }
    else:
        raise ValueError("Unsupported knowledge operation.")

    raw_content = _subgraph_to_text(graph, nodes, edges, token_budget=budget)
    native_truncated = "[!] TRUNCATED: showing " in raw_content
    over_budget_complete = "[i] Complete answer over budget: " in raw_content
    content = normalize_recovery_wording(raw_content)
    references = _extract_subgraph_references(content)
    res = {
        "content": content,
        "references": references,
        "truncated": native_truncated,
        "over_budget_complete": over_budget_complete,
    }
    if community_info is not None:
        res["community"] = community_info
    return res


def main() -> int:
    request = json.loads(sys.stdin.buffer.read(2_000_001))
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = execute(request)
        response = {"ok": True, **result}
    except (Exception, SystemExit) as exc:
        response = {"ok": False, "error": type(exc).__name__, "message": str(exc)[:1000]}
    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
