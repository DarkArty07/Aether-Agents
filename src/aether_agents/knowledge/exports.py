"""Native visualization exports for project knowledge graphs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from aether_agents.paths import ensure_private_dir, read_private_bytes

from .common import KnowledgeError
from .context import KnowledgeContext
from .graphify import GraphifyBackend


def export_visualization(
    backend: GraphifyBackend,
    location: Path,
    manifest: dict[str, Any],
    ctx: KnowledgeContext,
    cache_root: Path,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Render and export graph or tree visualization to a managed path."""
    fmt = str(arguments.get("format", "graph")).lower()
    detail = str(arguments.get("detail", "auto")).lower()
    if fmt not in ("graph", "tree"):
        raise KnowledgeError("ARGUMENT_INVALID", f"Unsupported visualization format '{fmt}'.")
    if fmt == "tree" and "detail" in arguments:
        raise KnowledgeError("ARGUMENT_INVALID", "Detail is only valid for graph format.")
    if detail not in ("auto", "full"):
        raise KnowledgeError("ARGUMENT_INVALID", f"Unsupported detail level '{detail}'.")

    snapshot_id = str(manifest["snapshot_id"])
    exports_dir = cache_root / "knowledge" / ctx.project_id / "exports" / snapshot_id
    ensure_private_dir(exports_dir)

    filename = "tree.html" if fmt == "tree" else f"graph_{detail}.html"
    export_file = exports_dir / filename
    metadata_file = exports_dir / f"{filename}.json"

    graph_file = location / "graphify-out" / "graph.json"
    sha_before = hashlib.sha256(read_private_bytes(graph_file)).hexdigest()

    # Reuse identical existing artifact if present and valid
    if export_file.is_file() and metadata_file.is_file():
        try:
            cached_meta = json.loads(metadata_file.read_text(encoding="utf-8"))
            file_bytes = export_file.read_bytes()
            if hashlib.sha256(file_bytes).hexdigest() == cached_meta.get("sha256"):
                content = (
                    f"Reused existing {fmt} visualization from {filename} "
                    f"({cached_meta['rendered_nodes']}/{cached_meta['total_nodes']} nodes rendered, "
                    f"aggregated={cached_meta['aggregated']})."
                )
                return cached_meta, content
        except Exception:
            pass

    project_label = f"{ctx.project_id} @ {ctx.source_revision[:8]}"
    worker_res = backend.run(
        "visualize",
        source_root=location / "sources",
        graph_path=graph_file,
        arguments={
            "format": fmt,
            "detail": detail,
            "export_path": str(export_file),
            "project_label": project_label,
        },
    )

    sha_after = hashlib.sha256(read_private_bytes(graph_file)).hexdigest()
    if sha_before != sha_after:
        raise KnowledgeError("INDEX_CORRUPT", "Snapshot graph changed during visualization.")

    worker_artifact = worker_res.get("artifact", {})
    raw_bytes = export_file.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    artifact = {
        "id": f"{snapshot_id}_{fmt}_{detail if fmt == 'graph' else 'tree'}",
        "format": fmt,
        "view": ctx.view_id,
        "revision": ctx.source_revision,
        "snapshot_id": snapshot_id,
        "local_path": str(export_file),
        "bytes": len(raw_bytes),
        "sha256": sha256,
        "rendered_nodes": worker_artifact.get("rendered_nodes", 0),
        "total_nodes": worker_artifact.get("total_nodes", 0),
        "aggregated": bool(worker_artifact.get("aggregated", False)),
        "external_assets": worker_artifact.get("external_assets", []),
    }

    metadata_file.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    content = str(worker_res.get("content", f"Exported {fmt} visualization to {filename}."))
    return artifact, content
