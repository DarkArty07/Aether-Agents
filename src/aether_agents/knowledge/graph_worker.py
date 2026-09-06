"""Private subprocess entry point; Graphify imports stay outside Hermes.

This file is executed by the configured component interpreter, not imported by
Aether. It adapts the fixed upstream functions, rather than maintaining another
graph search engine. The JSON request is produced only by the trusted adapter.
"""

from __future__ import annotations

import contextlib
import importlib.metadata
import io
import json
import os
import re
import sys
from pathlib import Path


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
    # 4. Residual mentions of context_filter, get_node, CLI: --budget, --budget
    text = re.sub(r"\bcontext_filter=\[[^\]]*\]", "narrower question", text)
    text = re.sub(r"\bcontext_filter\b", "question", text)
    text = re.sub(r"\bget_node\b", "explain", text)
    text = text.replace("CLI: --budget", "budget_tokens")
    text = text.replace("--budget", "budget_tokens")
    # 5. Remove any Graph: /path/to/graph.json (N nodes) | header prefix to keep snapshot path internal
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

        raw_content = _query_graph_text(
            G,
            args["question"],
            mode="bfs",
            depth=2,
            token_budget=budget,
            context_filters=[],
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
        content = normalize_recovery_wording(format_affected(G, node_arg, depth=depth))
        hits = affected_nodes(G, seed, depth=depth)

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
        arguments = {
            "source": args["source"],
            "target": args["target"],
            "max_hops": args.get("max_hops", 8),
            "undirected": False,
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
                _dg = nx.DiGraph()
                _dg.add_nodes_from(sorted(graph.nodes))
                _dg.add_edges_from(
                    sorted(
                        (d.get("_src", u), d.get("_tgt", v)) for u, v, d in graph.edges(data=True)
                    )
                )
                try:
                    path_nodes = nx.shortest_path(_dg, src_nid, tgt_nid)
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
                                datas = edge_datas(graph, u, v) or edge_datas(graph, v, u)
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
