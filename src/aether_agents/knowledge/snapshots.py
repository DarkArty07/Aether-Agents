"""Collaborative, revision-bound Graphify snapshots built from Git objects."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from aether_agents.paths import atomic_private_write, ensure_private_dir, read_private_bytes

from .common import (
    GRAPHIFY_VERSION,
    KnowledgeError,
    atomic_json,
    bounded,
    git,
    load_json,
    stable_lock,
)
from .context import KnowledgeContext
from .graphify import GraphifyBackend

MAX_FILES = 5000
MAX_FILE_BYTES = 256_000
MAX_SOURCE_BYTES = 32_000_000
MAX_GRAPH_BYTES = 64_000_000
_SCOPE_VERSION = "regular-tracked-v1"
_EXTENSIONS = frozenset(
    ".py .pyi .js .jsx .ts .tsx .go .rs .java .c .h .cpp .hpp .cs .rb .php .swift .kt "
    ".scala .lua .sh .sql .md .txt .rst .toml .yaml .yml .json .ini .cfg .html .css .vue .svelte".split()
)
_EXCLUDED_PARTS = frozenset(
    {
        "home",
        "node_modules",
        "vendor",
        ".git",
        ".venv",
        "venv",
        ".worktrees",
        "worktrees",
        "__pycache__",
        "logs",
        "sessions",
        "memories",
        "memory",
        "graphify-out",
        ".graphify",
        "dist",
        "build",
        ".cache",
        ".hermes",
        ".claude",
        ".codex",
        ".idea",
    }
)
_SECRET = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}|\bAKIA[A-Z0-9]{16}\b"
)
_SNAPSHOT_ID = re.compile(r"^[a-f0-9]{32}$")


def _relative(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or any(ord(c) < 32 for c in value)
    ):
        raise KnowledgeError("UNSAFE_PATH", "Source paths must be project-relative regular files.")
    return path.as_posix()


def _allowed(path: str) -> bool:
    pure = PurePosixPath(path)
    return (
        not any(part in _EXCLUDED_PARTS for part in pure.parts)
        and not pure.name.startswith((".env", "credentials", "secrets", "auth.json"))
        and pure.suffix.casefold() in _EXTENSIONS
        and not (pure.parts[:2] == (".aether", "objective-contracts") and "drafts" in pure.parts)
    )


def _sources(context: KnowledgeContext) -> tuple[dict[str, bytes], list[str]]:
    """Read only allowed regular blobs; no checkout, hooks, filters or source execution."""
    records: list[tuple[str, str]] = []
    excluded: list[str] = []
    tree = git(context.root, "ls-tree", "-rz", "--full-tree", context.source_revision)
    if len(tree) > 8_000_000:
        raise KnowledgeError(
            "SCOPE_UNAVAILABLE", "The source tree exceeds the configured scope limit."
        )
    for record in tree.split(b"\0"):
        if not record:
            continue
        meta, raw_path = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        try:
            path = _relative(raw_path.decode("utf-8"))
        except (UnicodeError, KnowledgeError):
            continue
        if mode not in ("100644", "100755") or kind != "blob" or not _allowed(path):
            excluded.append(path)
            continue
        records.append((path, oid))
    if len(records) > MAX_FILES:
        raise KnowledgeError("SCOPE_UNAVAILABLE", "Select a smaller corpus: too many source files.")
    if not records:
        raise KnowledgeError(
            "SCOPE_UNAVAILABLE", "No supported regular source files were selected."
        )
    oids = ("\n".join(oid for _, oid in records) + "\n").encode()
    sizes = git(
        context.root, "cat-file", "--batch-check=%(objectname) %(objectsize)", data=oids
    ).splitlines()
    selected: list[tuple[str, str, int]] = []
    total = 0
    for (path, oid), row in zip(records, sizes, strict=True):
        fields = row.decode().split()
        size = int(fields[1])
        if size > MAX_FILE_BYTES:
            excluded.append(path)
            continue
        total += size
        if total > MAX_SOURCE_BYTES:
            raise KnowledgeError(
                "SCOPE_UNAVAILABLE", "Select a smaller corpus: source byte limit exceeded."
            )
        selected.append((path, oid, size))
    if not selected:
        raise KnowledgeError("SCOPE_UNAVAILABLE", "All source files exceed the per-file limit.")
    blob_stream = git(
        context.root,
        "cat-file",
        "--batch",
        data=("\n".join(oid for _, oid, _ in selected) + "\n").encode(),
    )
    offset = 0
    sources: dict[str, bytes] = {}
    for path, oid, expected_size in selected:
        end = blob_stream.index(b"\n", offset)
        header = blob_stream[offset:end].decode().split()
        if header != [oid, "blob", str(expected_size)]:
            raise KnowledgeError(
                "SCOPE_UNAVAILABLE", "Git object capture did not match its manifest."
            )
        offset = end + 1
        content = blob_stream[offset : offset + expected_size]
        offset += expected_size + 1
        if (
            b"\0" in content
            or content.startswith(b"version https://git-lfs.github.com/spec/")
            or _SECRET.search(content)
        ):
            excluded.append(path)
            continue
        sources[path] = content
    return sources, excluded


def _dirty(context: KnowledgeContext) -> list[str]:
    changed = git(context.root, "diff", "--name-only", "-z", context.source_revision)
    new = git(context.root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({p.decode("utf-8", "replace") for p in (changed + new).split(b"\0") if p})[:500]


class KnowledgeStore:
    def __init__(
        self,
        state_root: Path,
        cache_root: Path,
        backend: GraphifyBackend | None,
        configuration: dict[str, Any] | None = None,
    ):
        self.state_root = state_root
        self.cache_root = cache_root
        self.backend = backend
        self._configuration = configuration

    def configuration(self) -> dict[str, Any]:
        if self._configuration is not None:
            return self._configuration
        config_file = self.state_root / "knowledge" / "component.json"
        try:
            return load_json(config_file)
        except Exception:
            return {}

    def _view(self, ctx: KnowledgeContext) -> Path:
        if not re.fullmatch(r"[a-f0-9-]{36}", ctx.project_id) or not re.fullmatch(
            r"[a-f0-9]{24}", ctx.view_id
        ):
            raise KnowledgeError("PROJECT_UNRESOLVED", "Invalid knowledge namespace.")
        if not re.fullmatch(r"[a-f0-9]{40,64}", ctx.source_revision):
            raise KnowledgeError("VIEW_MISMATCH", "Invalid source revision.")
        return self.state_root / "knowledge" / ctx.project_id / "views" / ctx.view_id

    def _pointer(self, ctx: KnowledgeContext) -> Path:
        return self._view(ctx) / (ctx.source_revision + ".json")

    def _snapshot(self, ctx: KnowledgeContext) -> tuple[Path, dict[str, Any]]:
        try:
            pointer = load_json(self._pointer(ctx))
        except FileNotFoundError as exc:
            raise KnowledgeError(
                "INDEX_MISSING", "This project revision has not been indexed."
            ) from exc
        if not isinstance(pointer, dict) or not _SNAPSHOT_ID.fullmatch(
            str(pointer.get("snapshot_id", ""))
        ):
            raise KnowledgeError("INDEX_CORRUPT", "Invalid knowledge snapshot pointer.")
        location = self.cache_root / "knowledge" / ctx.project_id / pointer["snapshot_id"]
        try:
            manifest = load_json(location / "manifest.json")
        except FileNotFoundError as exc:
            raise KnowledgeError(
                "INDEX_MISSING", "The cached snapshot was removed; rebuild this revision."
            ) from exc
        if not isinstance(manifest, dict) or not isinstance(manifest.get("inputs"), dict):
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot manifest has an invalid schema.")
        expected = (
            ctx.project_id,
            ctx.view_id,
            ctx.source_revision,
            GRAPHIFY_VERSION,
            _SCOPE_VERSION,
        )
        actual = tuple(
            manifest.get(k)
            for k in ("project_id", "view_id", "source_revision", "engine_version", "scope_version")
        )
        if actual != expected or manifest.get("complete") is not True:
            raise KnowledgeError(
                "INDEX_CORRUPT", "The snapshot does not belong to this project revision."
            )
        graph = location / "graphify-out" / "graph.json"
        if graph.is_symlink() or not graph.is_file() or graph.stat().st_size > MAX_GRAPH_BYTES:
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot graph is missing or unsafe.")
        try:
            graph_bytes = read_private_bytes(graph)
        except (OSError, ValueError) as exc:
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot graph path is unsafe.") from exc
        if hashlib.sha256(graph_bytes).hexdigest() != manifest.get("graph_sha256"):
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot graph changed after publication.")
        return location, manifest

    def _envelope(
        self, ctx: KnowledgeContext, action: str, manifest: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        dirty = _dirty(ctx)
        return {
            "schema_version": "aether.project-knowledge.v1",
            "ok": True,
            "action": action,
            "project_id": ctx.project_id,
            "view_id": ctx.view_id,
            "snapshot_id": manifest.get("snapshot_id") if manifest else None,
            "source_revision": ctx.source_revision,
            "freshness": "dirty_not_indexed" if dirty else "current",
            "coverage": manifest.get("coverage", {}) if manifest else {},
            "dirty_paths": dirty,
            "content": "",
            "references": [],
            "truncated": False,
            "warnings": ["Derived navigation only; verify current sources and tests."]
            + (
                ["Files changed since this indexed revision require direct inspection."]
                if dirty
                else []
            ),
        }

    def execute(
        self, context: KnowledgeContext, action: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        if action == "update":
            return self.update(context, arguments)
        if action not in (
            "status",
            "query",
            "explain",
            "neighbors",
            "community",
            "path",
            "impact",
            "stats",
            "god_nodes",
            "list_prs",
            "pr_impact",
            "triage_prs",
            "visualize",
        ):
            raise KnowledgeError("ARGUMENT_INVALID", "Unknown project knowledge action.")
        try:
            location, manifest = self._snapshot(context)
        except KnowledgeError as exc:
            if action != "status" or exc.code != "INDEX_MISSING":
                raise
            result = self._envelope(context, action)
            result.update(available=False, freshness="unknown")
            return result
        result = self._envelope(context, action, manifest)
        result["available"] = True
        if action == "status":
            result["excluded_count"] = manifest["excluded_count"]
            result["indexed_files"] = len(manifest["inputs"])
            if "semantic" in manifest:
                result["semantic"] = manifest["semantic"]
                result["semantic_pending"] = manifest["semantic"].get("state") not in (
                    "complete",
                    "disabled",
                )
            return result
        if action == "stats":
            if self.backend is None:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "Configure Graphify before graph queries."
                )
            native = self.backend.run(
                action,
                source_root=location / "sources",
                graph_path=location / "graphify-out" / "graph.json",
                arguments=arguments,
            )
            result["stats"] = native.get("stats", {})
            result["content"] = native.get("content", "")
            result["references"] = []
            result["truncated"] = False
            return result
        if action == "visualize":
            if self.backend is None:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "Configure Graphify before graph queries."
                )
            from .exports import export_visualization

            artifact, content = export_visualization(
                self.backend, location, manifest, context, self.cache_root, arguments
            )
            result["artifact"] = artifact
            result["content"] = content
            result["references"] = []
            result["truncated"] = False
            return result
        if action == "list_prs":
            from .github import execute_list_prs

            github_ctx, prs, content = execute_list_prs(context.root, context, arguments)
            result["github"] = github_ctx
            result["prs"] = prs
            result["content"], aether_truncated = bounded(
                content, arguments.get("budget_tokens", 2000)
            )
            result["references"] = []
            result["truncated"] = aether_truncated
            return result
        if action == "triage_prs":
            if self.backend is None:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "Configure Graphify before graph queries."
                )
            from .github import execute_triage_prs

            github_ctx, triaged_prs, overlap_pairs, content = execute_triage_prs(
                self.backend, location, context.root, context, arguments
            )
            result["github"] = github_ctx
            result["prs"] = triaged_prs
            result["community_overlaps"] = overlap_pairs
            result["content"], aether_truncated = bounded(
                content, arguments.get("budget_tokens", 2000)
            )
            result["references"] = []
            result["truncated"] = aether_truncated
            return result

        if action == "pr_impact":
            if self.backend is None:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "Configure Graphify before graph queries."
                )
            from .github import execute_pr_impact

            github_ctx, pr_summary, impact_info, worker_refs, content = execute_pr_impact(
                self.backend, location, context.root, context, arguments
            )
            result["github"] = github_ctx
            result["pr"] = pr_summary
            result["impact"] = impact_info
            native = {
                "content": content,
                "references": worker_refs,
            }
        else:
            if self.backend is None:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "Configure Graphify before graph queries."
                )
            native = self.backend.run(
                action,
                source_root=location / "sources",
                graph_path=location / "graphify-out" / "graph.json",
                arguments=arguments,
            )
            if "nodes" in native:
                result["nodes"] = native["nodes"]
            if "query_options" in native:
                result["query_options"] = native["query_options"]

        text = str(native.get("content", "")).replace(str(location / "sources") + "/", "")
        text = text.replace(str(location.resolve()), "<knowledge-snapshot>")
        text = text.replace(str(location), "<knowledge-snapshot>")
        result["budget_measurement"] = "UTF-8 byte cap; tokens estimated at four bytes each"
        refs: list[dict[str, str]] = []
        seen_refs: set[tuple[str, str]] = set()
        for ref in native.get("references", []):
            path_str = ref.get("path", "")
            if not path_str:
                continue
            path = Path(path_str)
            if path.is_absolute():
                try:
                    path = path.relative_to(location / "sources")
                except ValueError:
                    continue
            posix_path = path.as_posix()
            if posix_path in manifest["inputs"]:
                loc = str(ref.get("location", ""))
                key = (posix_path, loc)
                if key not in seen_refs:
                    seen_refs.add(key)
                    refs.append(
                        {
                            "path": posix_path,
                            "location": loc,
                            "revision": context.source_revision,
                        }
                    )
        ref_capped = len(refs) > 50
        result["references"] = refs[:50]
        if ref_capped:
            result["warnings"].append(
                "References capped at 50 items; additional visible sources omitted."
            )
        native_truncated = bool(native.get("truncated", False))
        result["content"], aether_truncated = bounded(text, arguments.get("budget_tokens", 2000))
        result["truncated"] = native_truncated or aether_truncated or ref_capped
        if native.get("over_budget_complete"):
            result["warnings"].append(
                "Complete native answer exceeds requested token budget; all nodes and edges shown."
            )
        if "resolved_node" in native:
            result["resolved_node"] = native["resolved_node"]
        if "community" in native:
            result["community"] = native["community"]
        if manifest["coverage"].get("documents") != "semantic":
            result["warnings"].append(
                "Documents have structural navigation only; semantic extraction is not enabled."
            )
        return result

    def update(self, ctx: KnowledgeContext, args: dict[str, Any]) -> dict[str, Any]:
        mode = args.get("mode", "configured")
        if mode not in ("structural", "configured"):
            raise KnowledgeError("ARGUMENT_INVALID", "Invalid update mode.")
        for path in args.get("changed_paths", []):
            _relative(path)
        if self.backend is None:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Configure Graphify before graph updates."
            )
        self.backend.probe()
        view = self._view(ctx)
        with stable_lock(view / "update.lock", timeout=10.0):
            cfg = self.configuration()
            sem_cfg = cfg.get("semantic", {})
            sem_enabled = bool(cfg.get("semantic_enabled") or sem_cfg.get("enabled"))

            existing_manifest = None
            existing_location = None
            try:
                existing_location, existing_manifest = self._snapshot(ctx)
            except KnowledgeError as exc:
                if exc.code not in ("INDEX_MISSING", "INDEX_CORRUPT"):
                    raise

            # Structural update preserves existing complete semantic snapshot
            if mode == "structural":
                if existing_manifest and existing_manifest.get("complete"):
                    result = self._envelope(ctx, "update", existing_manifest)
                    result.update(
                        outcome="unchanged",
                        indexed_revision=ctx.source_revision,
                        semantic_pending=False,
                        uncovered_paths=result["dirty_paths"],
                    )
                    if "semantic" in existing_manifest:
                        result["semantic"] = existing_manifest["semantic"]
                    return result

            # Configured update with already complete semantics produces zero model calls
            if mode == "configured" and existing_manifest and existing_manifest.get("complete"):
                sem_meta = existing_manifest.get("semantic", {})
                if (sem_enabled and sem_meta.get("state") == "complete") or (
                    not sem_enabled and sem_meta.get("state") in ("complete", "disabled")
                ):
                    result = self._envelope(ctx, "update", existing_manifest)
                    result.update(
                        outcome="unchanged",
                        indexed_revision=ctx.source_revision,
                        semantic_pending=False,
                        uncovered_paths=result["dirty_paths"],
                    )
                    if "semantic" in existing_manifest:
                        result["semantic"] = existing_manifest["semantic"]
                    return result

            sources, excluded = _sources(ctx)
            if not sources:
                raise KnowledgeError("SCOPE_UNAVAILABLE", "No supported non-secret text remains.")

            # Can enrich existing structural snapshot on same commit
            if (
                existing_manifest
                and existing_location
                and (existing_location / "graphify-out" / "graph.json").is_file()
            ):
                snapshot_id = str(existing_manifest["snapshot_id"])
                location = existing_location
                source_root = location / "sources"
                output = location / "graphify-out" / "graph.json"
                inputs = existing_manifest["inputs"]
            else:
                snapshot_id = uuid.uuid4().hex
                location = self.cache_root / "knowledge" / ctx.project_id / snapshot_id
                source_root = location / "sources"
                ensure_private_dir(source_root)
                inputs = {}
                for path, content in sources.items():
                    destination = source_root / path
                    ensure_private_dir(destination.parent)
                    atomic_private_write(destination, content)
                    inputs[path] = hashlib.sha256(content).hexdigest()
                output = location / "graphify-out" / "graph.json"
                self.backend.run("update", source_root=source_root, graph_path=output)

            if (
                output.is_symlink()
                or not output.is_file()
                or output.stat().st_size > MAX_GRAPH_BYTES
            ):
                raise KnowledgeError(
                    "INDEX_CORRUPT", "Graphify did not create a bounded regular graph."
                )
            graph_bytes = read_private_bytes(output)
            try:
                graph = json.loads(graph_bytes)
            except ValueError as exc:
                raise KnowledgeError("INDEX_CORRUPT", "Graphify created invalid JSON.") from exc
            if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
                raise KnowledgeError("INDEX_CORRUPT", "Graphify created an invalid graph schema.")
            # External symbols can lack sources; actual file references must stay in the corpus.
            for node in graph["nodes"]:
                if not isinstance(node, dict):
                    raise KnowledgeError("INDEX_CORRUPT", "Graphify created a malformed node.")
                value = node.get("source_file")
                if not value:
                    continue
                path = Path(str(value))
                if path.is_absolute():
                    try:
                        path = path.relative_to(source_root)
                    except ValueError as exc:
                        raise KnowledgeError(
                            "INDEX_CORRUPT", "A graph source escaped its captured project."
                        ) from exc
                if ".." in path.parts:
                    raise KnowledgeError(
                        "INDEX_CORRUPT", "A graph source escaped its captured project."
                    )

            # Semantic enrichment
            semantic_meta: dict[str, Any] = {"state": "disabled", "fingerprint": None}
            if mode == "configured" and sem_enabled:
                from .semantic import run_semantic_extraction

                try:
                    semantic_meta = run_semantic_extraction(
                        backend=self.backend,
                        source_root=source_root,
                        graph_path=output,
                        inputs=inputs,
                        cache_root=self.cache_root,
                        ctx=ctx,
                        configuration=cfg,
                    )
                except Exception:
                    # If refresh on existing complete snapshot failed: keep prior complete snapshot
                    if (
                        existing_manifest
                        and existing_manifest.get("semantic", {}).get("state") == "complete"
                    ):
                        result = self._envelope(ctx, "update", existing_manifest)
                        result.update(
                            outcome="unchanged",
                            indexed_revision=ctx.source_revision,
                            semantic_pending=False,
                            uncovered_paths=result["dirty_paths"],
                        )
                        result["warnings"].append(
                            "Refresh failed; retained previously complete snapshot."
                        )
                        return result
                    semantic_meta = {
                        "state": "unavailable",
                        "fingerprint": None,
                        "covered_paths": [],
                        "pending_paths": list(inputs.keys()),
                        "failed_paths": [],
                        "validated_chunk_ids": [],
                        "observed_usage": {},
                    }

            sem_state = semantic_meta.get("state")
            if sem_state == "complete":
                coverage = {"code": "structural", "documents": "semantic"}
                semantic_pending = False
            elif sem_state == "partial":
                coverage = {"code": "structural", "documents": "partial"}
                semantic_pending = True
            elif sem_state == "disabled":
                coverage = {"code": "structural", "documents": "structural_only"}
                semantic_pending = False
            else:
                coverage = {"code": "structural", "documents": "structural_only"}
                semantic_pending = True

            graph_bytes = read_private_bytes(output)
            manifest = {
                "schema_version": 1,
                "complete": True,
                "project_id": ctx.project_id,
                "view_id": ctx.view_id,
                "snapshot_id": snapshot_id,
                "source_revision": ctx.source_revision,
                "engine_version": GRAPHIFY_VERSION,
                "scope_version": _SCOPE_VERSION,
                "inputs": inputs,
                "input_sha256": hashlib.sha256(
                    json.dumps(inputs, sort_keys=True).encode()
                ).hexdigest(),
                "graph_sha256": hashlib.sha256(graph_bytes).hexdigest(),
                "coverage": coverage,
                "semantic": semantic_meta,
                "excluded_count": len(excluded),
                "created_at": time.time(),
                "publisher_role": ctx.role_id,
            }
            atomic_json(location / "manifest.json", manifest)
            atomic_json(
                self._pointer(ctx),
                {"snapshot_id": snapshot_id, "source_revision": ctx.source_revision},
            )
            result = self._envelope(ctx, "update", manifest)
            result.update(
                outcome="updated",
                indexed_revision=ctx.source_revision,
                semantic_pending=semantic_pending,
                uncovered_paths=result["dirty_paths"],
                excluded_count=len(excluded),
                indexed_files=len(inputs),
                semantic=semantic_meta,
            )
            return result
