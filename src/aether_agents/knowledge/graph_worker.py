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
import sys
from pathlib import Path


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
    if action == "path":
        from graphify.serve import _load_graph, _shortest_path_text

        graph = _load_graph(str(graph_path))
        return {
            "content": _shortest_path_text(
                graph,
                {
                    "source": args["source"],
                    "target": args["target"],
                    "max_hops": args.get("max_hops", 8),
                    "undirected": False,
                },
            ),
            "references": [],
        }
    if action in ("query", "explain", "impact"):
        from graphify.__main__ import main

        if action == "query":
            argv = ["query", args["question"], "--budget", str(budget)]
        elif action == "explain":
            argv = ["explain", args["node"]]
        else:
            argv = ["affected", args["node"], "--depth", str(args.get("depth", 2))]
        sys.argv = ["graphify", *argv, "--graph", str(graph_path)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main()
        return {"content": output.getvalue(), "references": []}

    from graphify.serve import (
        _bfs,
        _communities_from_graph,
        _load_graph,
        _resolve_single_node,
        _subgraph_to_text,
    )

    graph = _load_graph(str(graph_path))
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
        nodes = set(_communities_from_graph(graph).get(args["community_id"], []))
        if not nodes:
            raise ValueError("Community not found in this snapshot.")
        edges = [(a, b) for a, b in graph.edges() if a in nodes and b in nodes]
    else:
        raise ValueError("Unsupported knowledge operation.")
    content = _subgraph_to_text(graph, nodes, edges, token_budget=budget)
    references = [
        {
            "path": str(graph.nodes[n].get("source_file", "")),
            "location": str(graph.nodes[n].get("source_location", "")),
        }
        for n in sorted(nodes)[:100]
        if graph.nodes[n].get("source_file")
    ]
    return {"content": content, "references": references}


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
