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


# --- Additive semantic overlay composition (#419) ---------------------------
#
# The committed graph.json is the immutable base of the semantic transaction.
# Composition re-adds every loaded baseline record verbatim and appends only
# explicit `origin=llm` additions, so Graphify global merge/dedup/ghost/re-key
# passes cannot rewrite structural identities, source/provenance attributes or
# edge endpoints/relation/site. A canonical projection of the loaded baseline is
# compared with the composed candidate before publication; any mismatch aborts
# without writing graph.json.

_OVERLAY_DERIVED_NODE_KEYS = frozenset({"community", "community_name", "norm_label"})
_OVERLAY_ENDPOINT_KEYS = frozenset({"source", "target", "from", "to", "_src", "_tgt"})
_OVERLAY_ORIGIN_KEYS = ("_origin", "origin")
_OVERLAY_MEMBER_SAMPLE = 5


def _is_hashable(value: Any) -> bool:
    """Mirror graphify.build._hashable for values coming from untrusted JSON."""
    try:
        hash(value)
    except TypeError:
        return False
    return True


def _coerce_record_id(value: Any) -> Any:
    """Mirror graphify.build._coerce_id: numeric ids become str, bool is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return str(value)


def _canonical_origin(item: dict) -> str:
    """Collapse the equivalent provenance spellings used by Graphify and Aether."""
    for key in _OVERLAY_ORIGIN_KEYS:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip().lower()
        if text in ("ast", "structural"):
            return "ast"
        return "llm" if text in ("llm", "semantic") else f"unrecognized:{text}"
    import graphify.build as _gbuild  # type: ignore[import-untyped]

    return "ast" if getattr(_gbuild, "_is_ast_tier")(item) else "llm"


def _overlay_anchor(member: dict) -> "tuple[str, str] | None":
    """(source_file, exact label) key used to prove an existing structural identity."""
    source_file = member.get("source_file")
    label = member.get("label")
    if not source_file or not isinstance(label, str) or not label.strip():
        return None
    return str(source_file), label.strip()


def _split_node_record(node: Any) -> "tuple[Any, dict[str, Any]] | None":
    if not isinstance(node, dict):
        return None
    node_id = _coerce_record_id(node.get("id"))
    if node_id is None or not _is_hashable(node_id):
        return None
    return node_id, _with_explicit_origin(
        {key: value for key, value in node.items() if key != "id"}
    )


def _with_explicit_origin(attributes: dict[str, Any]) -> dict[str, Any]:
    """Backfill Aether's explicit ``origin`` alias from the stored Graphify marker.

    Same self-heal Graphify applies to ``_origin`` on load: consumers then read
    one explicit tier field, and an absent alias cannot be mistaken for unknown
    provenance. The projection normalizes both spellings, so this is an alias
    write, not a provenance change.
    """
    stored = attributes.get("_origin")
    if stored is not None and attributes.get("origin") is None:
        return {**attributes, "origin": stored}
    return attributes


def _split_edge_record(edge: Any) -> "tuple[Any, Any, dict[str, Any]] | None":
    if not isinstance(edge, dict):
        return None
    source = _coerce_record_id(edge.get("_src", edge.get("source", edge.get("from"))))
    target = _coerce_record_id(edge.get("_tgt", edge.get("target", edge.get("to"))))
    if source is None or target is None:
        return None
    if not _is_hashable(source) or not _is_hashable(target):
        return None
    attributes = {key: value for key, value in edge.items() if key not in _OVERLAY_ENDPOINT_KEYS}
    return source, target, _with_explicit_origin(attributes)


def _normalize_base_records(
    nodes: list[Any], edges: list[Any], hyperedges: list[Any]
) -> "tuple[list[tuple[Any, dict[str, Any]]], list[tuple[Any, Any, dict[str, Any]]], list[dict]]":
    """Normalize the loaded base into graph-independent records.

    Endpoint keys are stripped from attribute dicts and edges are bound to
    ``(source, target)`` exactly as ``export.to_json`` persists them, so the same
    records drive both the candidate graph and the projection. A missing edge
    endpoint is materialized as an attribute-less record: an already-dangling
    baseline edge is preserved rather than silently dropped, and the projection
    stays self-consistent.
    """
    node_records: "list[tuple[Any, dict[str, Any]]]" = []
    node_ids: set[Any] = set()
    for node in nodes:
        split = _split_node_record(node)
        if split is None:
            continue
        node_id, attributes = split
        if node_id in node_ids:
            continue
        node_ids.add(node_id)
        node_records.append((node_id, attributes))
    edge_records: "list[tuple[Any, Any, dict[str, Any]]]" = []
    for edge in edges:
        split_edge = _split_edge_record(edge)
        if split_edge is None:
            continue
        source, target, attributes = split_edge
        edge_records.append((source, target, attributes))
        for endpoint in (source, target):
            if endpoint not in node_ids:
                node_ids.add(endpoint)
                node_records.append((endpoint, {}))
    hyperedge_records = [edge for edge in hyperedges if isinstance(edge, dict)]
    return node_records, edge_records, hyperedge_records


def _projection_sort_key(record: Any) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)


def _canonical_hyperedge(hyperedge: dict) -> dict:
    record = {key: value for key, value in hyperedge.items() if key not in _OVERLAY_ORIGIN_KEYS}
    record["#origin"] = _canonical_origin(hyperedge)
    members = record.get("nodes")
    if isinstance(members, list):
        record["nodes"] = sorted(
            members, key=lambda member: _projection_sort_key({"member": member})
        )
    return record


def _canonical_overlay_projection(
    node_records: "list[tuple[Any, dict[str, Any]]]",
    edge_records: "list[tuple[Any, Any, dict[str, Any]]]",
    hyperedge_records: "list[dict]",
    directed: bool,
) -> "tuple[str, str]":
    """Canonical projection of a graph and its SHA-256 digest.

    Node identity/attributes, edge endpoints/relation/site and graph direction
    are covered. Derived community fields and the additive ``confidence_score``
    written by ``export.to_json`` are excluded, and the equivalent
    ``origin=ast``/``_origin=ast`` aliases are normalized. Everything else is
    compared exactly, so an identity, source or provenance loss aborts
    publication.
    """
    nodes_payload = []
    for node_id, attributes in node_records:
        canonical = {
            key: value
            for key, value in attributes.items()
            if key not in _OVERLAY_DERIVED_NODE_KEYS and key not in _OVERLAY_ORIGIN_KEYS
        }
        canonical["#origin"] = _canonical_origin(attributes)
        nodes_payload.append({"id": node_id, "attributes": canonical})
    edges_payload = []
    for source, target, attributes in edge_records:
        canonical = {
            key: value
            for key, value in attributes.items()
            if key not in _OVERLAY_ENDPOINT_KEYS
            and key not in _OVERLAY_ORIGIN_KEYS
            and key != "confidence_score"
        }
        canonical["#origin"] = _canonical_origin(attributes)
        edges_payload.append({"source": source, "target": target, "attributes": canonical})
    hyperedges_payload = [_canonical_hyperedge(hyperedge) for hyperedge in hyperedge_records]
    payload = {
        "directed": bool(directed),
        "nodes": sorted(nodes_payload, key=_projection_sort_key),
        "edges": sorted(edges_payload, key=_projection_sort_key),
        "hyperedges": sorted(hyperedges_payload, key=_projection_sort_key),
    }
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compose_candidate_graph(
    node_records: "list[tuple[Any, dict[str, Any]]]",
    edge_records: "list[tuple[Any, Any, dict[str, Any]]]",
    hyperedge_records: list[dict],
    directed: bool,
    additions: dict,
) -> Any:
    """In-memory candidate graph: baseline records verbatim plus accepted overlay."""
    import networkx as nx  # type: ignore[import-untyped]

    graph = nx.DiGraph() if directed else nx.Graph()
    for node_id, attributes in node_records:
        graph.add_node(node_id, **dict(attributes))
    for source, target, attributes in edge_records:
        data = dict(attributes)
        data["_src"] = source
        data["_tgt"] = target
        graph.add_edge(source, target, **data)
    graph.graph["hyperedges"] = [
        *hyperedge_records,
        *(dict(hyperedge) for hyperedge in additions["hyperedges"]),
    ]
    for node in additions["nodes"]:
        graph.add_node(node["id"], **{key: value for key, value in node.items() if key != "id"})
    for edge in additions["edges"]:
        data = {key: value for key, value in edge.items() if key not in _OVERLAY_ENDPOINT_KEYS}
        data["_src"] = edge["source"]
        data["_tgt"] = edge["target"]
        graph.add_edge(edge["source"], edge["target"], **data)
    return graph


def _candidate_baseline_records(
    graph: Any,
    node_records: "list[tuple[Any, dict[str, Any]]]",
    edge_records: "list[tuple[Any, Any, dict[str, Any]]]",
    hyperedge_records: list[dict],
) -> "tuple[list[tuple[Any, dict[str, Any]]], list[tuple[Any, Any, dict[str, Any]]], list[dict]]":
    """Re-extract the baseline records back out of the composed candidate graph.

    Only the loaded baseline identities are projected, so overlay additions do
    not enter the comparison. A baseline record the candidate no longer carries
    surfaces as a placeholder, which the projection digests as a mismatch
    instead of ignoring the loss.
    """
    graph_nodes = {node_id: dict(attributes) for node_id, attributes in graph.nodes(data=True)}
    candidate_nodes = [
        (node_id, graph_nodes.get(node_id, {"#missing": True}))
        for node_id, _attributes in node_records
    ]
    graph_edges: "dict[tuple[Any, Any], dict]" = {}
    for source, target, attributes in graph.edges(data=True):
        graph_edges.setdefault(
            (attributes.get("_src", source), attributes.get("_tgt", target)), attributes
        )
    candidate_edges = []
    for source, target, _attributes in edge_records:
        attributes = graph_edges.get((source, target))
        candidate_edges.append(
            (
                source,
                target,
                {
                    key: value
                    for key, value in (attributes or {"#missing": True}).items()
                    if key not in _OVERLAY_ENDPOINT_KEYS
                },
            )
        )
    graph_hyperedges = [
        edge for edge in graph.graph.get("hyperedges", []) if isinstance(edge, dict)
    ]
    candidate_hyperedges = []
    for baseline_hyperedge in hyperedge_records:
        match = next(
            (edge for edge in graph_hyperedges if edge == baseline_hyperedge), {"#missing": True}
        )
        candidate_hyperedges.append(match)
    return candidate_nodes, candidate_edges, candidate_hyperedges


def _stamp_overlay_member(raw: dict, *, with_location: bool) -> dict:
    """Force the accepted-overlay provenance contract onto one incoming member."""
    member = dict(raw)
    member["_origin"] = "llm"
    member["origin"] = "llm"
    confidence = str(member.get("confidence") or "").upper()
    member["confidence"] = "INFERRED" if confidence in ("", "EXTRACTED") else confidence
    if with_location and not member.get("source_location"):
        member["source_location"] = None
    return member


def _edge_omission(edge: dict, source: Any, target: Any, reason: str) -> dict:
    return {
        "source": source,
        "target": target,
        "relation": edge.get("relation"),
        "reason": reason,
    }


def _hyperedge_members(hyperedge: dict) -> "list[Any] | None":
    for key in ("nodes", "members", "node_ids"):
        members = hyperedge.get(key)
        if isinstance(members, list):
            return list(members)
    return None


def _plan_overlay_additions(
    fragments: list[Any],
    *,
    allowed_sources: "list[str] | None",
    base_node_ids: set[Any],
    anchors: "dict[tuple[str, str], list[Any]]",
    base_directed_edges: "set[tuple[Any, Any]]",
    base_edge_pairs: "set[frozenset]",
    base_hyperedge_ids: set[Any],
) -> "tuple[dict, list[dict], list[dict], list[dict]]":
    """Decide which incoming members become overlay additions, in fragment order.

    Only uniquely proven label anchors (one existing identity for the exact
    source_file/label pair) are remapped onto an existing identity; ambiguous
    anchors, existing identities, edges that collide with an existing endpoint
    pair, self references, dangling endpoints and hyperedges whose members do not
    all resolve are omitted with a bounded reason instead of overwriting or
    silently dropping evidence.
    """
    allowed = set(allowed_sources) if allowed_sources else None
    additions: "dict[str, list[dict]]" = {"nodes": [], "edges": [], "hyperedges": []}
    omitted_nodes: list[dict] = []
    omitted_edges: list[dict] = []
    omitted_hyperedges: list[dict] = []
    remapped: dict[Any, Any] = {}
    known_ids = set(base_node_ids)
    added_edge_pairs: "set[frozenset]" = set()
    added_hyperedge_ids: set[Any] = set()

    def source_allowed(member: dict) -> bool:
        source_file = member.get("source_file")
        return allowed is None or not source_file or source_file in allowed

    for fragment in fragments:
        if not isinstance(fragment, dict):
            raise ValueError("Each semantic fragment must be a dictionary.")

        for raw_node in fragment.get("nodes") or []:
            if not isinstance(raw_node, dict):
                continue
            node = _stamp_overlay_member(raw_node, with_location=True)
            node_id = node.get("id")
            if not source_allowed(node):
                omitted_nodes.append({"id": node_id, "reason": "source_not_allowed"})
                continue
            if node_id is None or not _is_hashable(node_id):
                omitted_nodes.append({"id": node_id, "reason": "unusable_id"})
                continue
            if node_id in base_node_ids:
                omitted_nodes.append({"id": node_id, "reason": "existing_identity_collision"})
                continue
            if node_id in known_ids:
                omitted_nodes.append({"id": node_id, "reason": "duplicate_within_compose"})
                continue
            anchor = _overlay_anchor(node)
            matched = anchors.get(anchor, []) if anchor is not None else []
            if len(matched) == 1:
                remapped[node_id] = matched[0]
                omitted_nodes.append({"id": node_id, "reason": f"remapped_onto:{matched[0]}"})
                continue
            if len(matched) > 1:
                omitted_nodes.append({"id": node_id, "reason": "ambiguous_label_anchor"})
                continue
            additions["nodes"].append(node)
            known_ids.add(node_id)

        for raw_edge in fragment.get("edges") or []:
            if not isinstance(raw_edge, dict):
                continue
            edge = _stamp_overlay_member(raw_edge, with_location=True)
            source = edge.get("source", edge.get("from"))
            target = edge.get("target", edge.get("to"))
            if not source_allowed(edge):
                omitted_edges.append(_edge_omission(edge, source, target, "source_not_allowed"))
                continue
            if (
                source is None
                or target is None
                or not _is_hashable(source)
                or not _is_hashable(target)
            ):
                omitted_edges.append(_edge_omission(edge, source, target, "unusable_endpoint"))
                continue
            source = remapped.get(source, source)
            target = remapped.get(target, target)
            if source == target:
                omitted_edges.append(_edge_omission(edge, source, target, "self_reference"))
                continue
            if source not in known_ids or target not in known_ids:
                omitted_edges.append(_edge_omission(edge, source, target, "dangling_endpoint"))
                continue
            pair = frozenset((source, target))
            if (
                (source, target) in base_directed_edges
                or (target, source) in base_directed_edges
                or pair in base_edge_pairs
            ):
                omitted_edges.append(
                    _edge_omission(edge, source, target, "structural_edge_collision")
                )
                continue
            if pair in added_edge_pairs:
                omitted_edges.append(
                    _edge_omission(edge, source, target, "duplicate_within_compose")
                )
                continue
            accepted = dict(edge)
            accepted["source"] = source
            accepted["target"] = target
            additions["edges"].append(accepted)
            added_edge_pairs.add(pair)

        for raw_hyperedge in fragment.get("hyperedges") or []:
            if not isinstance(raw_hyperedge, dict):
                continue
            hyperedge = _stamp_overlay_member(raw_hyperedge, with_location=False)
            hyperedge_id = hyperedge.get("id")
            if not source_allowed(hyperedge):
                omitted_hyperedges.append({"id": hyperedge_id, "reason": "source_not_allowed"})
                continue
            if hyperedge_id is not None and hyperedge_id in base_hyperedge_ids:
                omitted_hyperedges.append(
                    {"id": hyperedge_id, "reason": "structural_hyperedge_collision"}
                )
                continue
            if hyperedge_id is not None and hyperedge_id in added_hyperedge_ids:
                omitted_hyperedges.append(
                    {"id": hyperedge_id, "reason": "duplicate_within_compose"}
                )
                continue
            members = _hyperedge_members(hyperedge)
            if not members:
                omitted_hyperedges.append({"id": hyperedge_id, "reason": "no_valid_members"})
                continue
            resolved: list[Any] = []
            unresolved: list[Any] = []
            for member in members:
                member_id = _coerce_record_id(member)
                if not _is_hashable(member_id):
                    unresolved.append(member)
                    continue
                member_id = remapped.get(member_id, member_id)
                if member_id in known_ids:
                    resolved.append(member_id)
                else:
                    unresolved.append(member)
            if unresolved:
                omitted_hyperedges.append(
                    {
                        "id": hyperedge_id,
                        "reason": "unresolved_members",
                        "members": unresolved[:_OVERLAY_MEMBER_SAMPLE],
                    }
                )
                continue
            accepted = {
                key: value for key, value in hyperedge.items() if key not in ("members", "node_ids")
            }
            accepted["nodes"] = resolved
            additions["hyperedges"].append(accepted)
            if hyperedge_id is not None:
                added_hyperedge_ids.add(hyperedge_id)

    return additions, omitted_nodes, omitted_edges, omitted_hyperedges


def _compose_additive_overlay(
    graph_path: Path,
    fragments: list[Any],
    *,
    allowed_sources: "list[str] | None" = None,
) -> dict[str, Any]:
    """One load, one in-memory overlay, one cluster/export publication transaction."""
    import graphify.build as _gbuild  # type: ignore[import-untyped]
    import graphify.cluster as cluster
    import graphify.export as export

    _load_existing_graph = getattr(_gbuild, "_load_existing_graph")
    loaded = _load_existing_graph(graph_path)
    if loaded is None:
        raise ValueError("No structural base graph exists for additive semantic composition.")
    node_records, edge_records, hyperedge_records = _normalize_base_records(
        loaded[0], loaded[1], loaded[2]
    )
    directed = bool(loaded[3])
    _baseline_text, baseline_digest = _canonical_overlay_projection(
        node_records, edge_records, hyperedge_records, directed
    )

    anchors: "dict[tuple[str, str], list[Any]]" = {}
    for node_id, attributes in node_records:
        anchor = _overlay_anchor(attributes)
        if anchor is not None:
            anchors.setdefault(anchor, []).append(node_id)

    base_directed_edges: "set[tuple[Any, Any]]" = set()
    base_edge_pairs: "set[frozenset]" = set()
    for source, target, _attributes in edge_records:
        base_directed_edges.add((source, target))
        base_edge_pairs.add(frozenset((source, target)))

    base_hyperedge_ids = {
        hyperedge.get("id") for hyperedge in hyperedge_records if hyperedge.get("id") is not None
    }

    additions, omitted_nodes, omitted_edges, omitted_hyperedges = _plan_overlay_additions(
        fragments,
        allowed_sources=allowed_sources,
        base_node_ids={node_id for node_id, _attributes in node_records},
        anchors=anchors,
        base_directed_edges=base_directed_edges,
        base_edge_pairs=base_edge_pairs,
        base_hyperedge_ids=base_hyperedge_ids,
    )

    structural_preserved = True
    if additions["nodes"] or additions["edges"] or additions["hyperedges"]:
        candidate = _compose_candidate_graph(
            node_records, edge_records, hyperedge_records, directed, additions
        )
        candidate_nodes, candidate_edges, candidate_hyperedges = _candidate_baseline_records(
            candidate, node_records, edge_records, hyperedge_records
        )
        _candidate_text, candidate_digest = _canonical_overlay_projection(
            candidate_nodes, candidate_edges, candidate_hyperedges, directed
        )
        structural_preserved = candidate_digest == baseline_digest
        if not structural_preserved:
            raise ValueError(
                "Structural projection changed during semantic composition; refusing to publish "
                f"(baseline {baseline_digest[:16]}, candidate {candidate_digest[:16]})."
            )
        communities = cluster.cluster(candidate)
        if not export.to_json(candidate, communities, str(graph_path), force=True):
            raise ValueError("Graphify refused to publish the composed semantic candidate.")

    references = []
    seen = set()
    for node in additions["nodes"]:
        if node.get("source_file"):
            path = str(node["source_file"])
            location = str(node.get("source_location") or "")
            if (path, location) not in seen:
                seen.add((path, location))
                references.append({"path": path, "location": location})

    content = (
        f"Composed semantic overlay: {len(additions['nodes'])} nodes, "
        f"{len(additions['edges'])} edges merged, {len(additions['hyperedges'])} hyperedges added; "
        f"omitted {len(omitted_nodes)} nodes, {len(omitted_edges)} edges and "
        f"{len(omitted_hyperedges)} hyperedges with bounded reasons."
    )
    return {
        "content": content,
        "references": references,
        "applied_nodes": len(additions["nodes"]),
        "applied_edges": len(additions["edges"]),
        "applied_hyperedges": len(additions["hyperedges"]),
        "omitted_nodes": omitted_nodes,
        "omitted_edges": omitted_edges,
        "omitted_hyperedges": omitted_hyperedges,
        "structural_digest": baseline_digest,
        "structural_preserved": structural_preserved,
    }


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
        offset = max(0, int(args.get("offset", 0)))
        raw_limit = args.get("limit", args.get("page_size", 25))
        limit = min(max(1, int(raw_limit)), 50) if raw_limit is not None else 25

        file_paths = [source_root / f for f in file_list if (source_root / f).is_file()]
        expanded = expand_oversized_files(file_paths, max_chars=max_chars)
        packed_chunks = _pack_chunks_by_tokens(expanded, token_budget=token_budget)
        total_chunks = len(packed_chunks)
        selected_chunks = packed_chunks[offset : offset + limit]

        system_prompt = _extraction_system(deep=False)
        chunks = []
        for i, chunk in enumerate(selected_chunks):
            chunk_id = offset + i
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
                    "chunk_id": chunk_id,
                    "files": paths,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                }
            )
        has_more = (offset + len(chunks)) < total_chunks
        content = (
            f"Prepared {len(chunks)} semantic extraction chunks "
            f"(offset {offset}, total {total_chunks}) from {len(file_paths)} files."
        )
        return {
            "content": content,
            "references": [],
            "chunks": chunks,
            "total_chunks": total_chunks,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
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

    if action in ("semantic_compose", "semantic_apply"):
        if action == "semantic_compose":
            fragments = args.get("fragments")
            if not isinstance(fragments, list):
                raise ValueError("fragments must be a list of validated semantic fragments.")
        else:
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
            fragments = [fragment]
        return _compose_additive_overlay(
            graph_path, fragments, allowed_sources=args.get("allowed_sources")
        )

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
