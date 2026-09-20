"""Collaborative, revision-bound Graphify snapshots built from Git objects."""

from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import re
import threading
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
from .graphify import (
    GraphifyBackend,
    _host_interrupt_requested,
    graphify_cancel_scope,
)

MAX_FILES = 5000
MAX_FILE_BYTES = 256_000
MAX_SOURCE_BYTES = 32_000_000
MAX_GRAPH_BYTES = 64_000_000
_SCOPE_VERSION = "regular-tracked-v1"
SNAPSHOT_INTEGRITY_VERSION = "aether.project-knowledge.integrity.v1"
SEMANTIC_PIPELINE_VERSION = "aether.semantic-pipeline.v2"
SEMANTIC_CACHE_VERSION = "aether.semantic-cache.v2"
_OPERATION_SCHEMA_VERSION = 1
_CANCEL_EVENT: contextvars.ContextVar[threading.Event | None] = contextvars.ContextVar(
    "aether_knowledge_cancel_event", default=None
)
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


def _bounded_count(value: Any, *, maximum: int = MAX_FILES) -> int | None:
    """Return a safe count for warning metadata without exposing arbitrary values."""
    if isinstance(value, list):
        return min(len(value), maximum)
    if type(value) is int and 0 <= value <= maximum:
        return value
    return None


def _semantic_integrity(manifest: dict[str, Any]) -> tuple[bool, str]:
    """Classify whether a semantic overlay is covered by the v1 integrity envelope."""
    semantic = manifest.get("semantic")
    if not isinstance(semantic, dict):
        return False, "missing"
    if manifest.get("_base_integrity_invalid") is True:
        return False, "inconsistent"
    if manifest.get("integrity_version") != SNAPSHOT_INTEGRITY_VERSION:
        return False, "legacy"
    if not re.fullmatch(r"[a-f0-9]{32}", str(manifest.get("base_structural_snapshot_id", ""))):
        return False, "inconsistent"
    for key in ("base_structural_digest", "structural_digest", "pipeline_version"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            return False, "inconsistent"
    pipeline = semantic.get("pipeline")
    if not isinstance(pipeline, dict):
        return False, "legacy"
    if pipeline.get("version") != manifest.get("pipeline_version"):
        return False, "inconsistent"
    if semantic.get("cache_version") not in (None, SEMANTIC_CACHE_VERSION):
        return False, "inconsistent"
    if semantic.get("version") not in (None, manifest.get("pipeline_version")):
        return False, "inconsistent"
    if semantic.get("state") not in {"disabled", "pending", "complete", "partial", "unavailable"}:
        return False, "inconsistent"
    return True, ""


def semantic_snapshot_warnings(manifest: dict[str, Any] | None) -> list[str]:
    """Describe immutable snapshot state, never the current component configuration."""
    if not isinstance(manifest, dict):
        return [
            "Semantic snapshot state is unknown or inconsistent; current document results are structural."
        ]
    semantic = manifest.get("semantic")
    trusted, integrity_reason = _semantic_integrity(manifest)
    if not isinstance(semantic, dict):
        return [
            "Semantic snapshot state is unknown or inconsistent; current document results are structural."
        ]
    if not trusted:
        if integrity_reason == "legacy":
            return [
                "Legacy semantic snapshot is not trusted; current document results are structural."
            ]
        return [
            "Semantic snapshot state is unknown or inconsistent; current document results are structural."
        ]

    state = semantic.get("state")
    coverage = manifest.get("coverage")
    documents = coverage.get("documents") if isinstance(coverage, dict) else None
    if state == "complete":
        if documents == "semantic":
            return []
        return [
            "Semantic snapshot state is unknown or inconsistent; current document results are structural."
        ]
    if state == "partial":
        counts: list[str] = []
        for label, key in (
            ("covered", "covered_paths"),
            ("pending", "pending_paths"),
            ("failed", "failed_paths"),
        ):
            count = _bounded_count(semantic.get(key))
            if count is not None:
                counts.append(f"{label}={count}")
        suffix = f" ({', '.join(counts)})" if counts else ""
        return [
            "Documents have partial semantic coverage; remaining paths stay structural"
            + suffix
            + "."
        ]
    if state == "pending":
        return [
            "Semantic enrichment is pending for this snapshot; current document results are structural."
        ]
    if state == "unavailable":
        category = semantic.get("reason_category")
        if not isinstance(category, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", category):
            category = None
        suffix = f" (reason={category})" if category else ""
        return [
            "Semantic enrichment was unavailable when this snapshot was built; current results are structural"
            + suffix
            + "."
        ]
    if state == "disabled":
        return ["Semantic extraction was disabled when this snapshot was built."]
    return [
        "Semantic snapshot state is unknown or inconsistent; current document results are structural."
    ]


# Private alias retained for focused lifecycle tests and downstream callers.
_semantic_warnings = semantic_snapshot_warnings


@contextlib.contextmanager
def knowledge_cancel_scope(event: threading.Event | None):
    token = _CANCEL_EVENT.set(event)
    try:
        yield
    finally:
        _CANCEL_EVENT.reset(token)


def _now() -> float:
    """Monotonic clock for the operation budget (patchable in tests)."""
    from . import semantic

    return semantic._now()


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

    def _operation_path(self, ctx: KnowledgeContext) -> Path:
        return self._view(ctx) / "operation.json"

    def _load_operation(self, ctx: KnowledgeContext) -> dict[str, Any] | None:
        try:
            operation = load_json(self._operation_path(ctx), limit=64_000)
        except FileNotFoundError:
            return None
        except KnowledgeError:
            return {"phase": "unknown", "outcome": "invalid"}
        if not isinstance(operation, dict):
            return {"phase": "unknown", "outcome": "invalid"}
        if operation.get("source_revision") not in (None, ctx.source_revision):
            return None
        # Operation metadata is deliberately content-free and bounded before exposure.
        allowed = {
            key: operation[key]
            for key in (
                "schema_version",
                "operation_id",
                "phase",
                "source_revision",
                "input_sha256",
                "candidate_snapshot_id",
                "base_structural_snapshot_id",
                "outcome",
                "terminal_outcome",
                "failure_category",
                "published_snapshot_id",
            )
            if key in operation
        }
        allowed["active"] = operation.get("outcome") == "running"
        return allowed

    def _write_operation(
        self,
        ctx: KnowledgeContext,
        *,
        operation_id: str,
        phase: str,
        outcome: str,
        source_revision: str,
        input_sha256: str | None = None,
        candidate_snapshot_id: str | None = None,
        base_structural_snapshot_id: str | None = None,
        terminal_outcome: str | None = None,
        failure_category: str | None = None,
        published_snapshot_id: str | None = None,
    ) -> None:
        data: dict[str, Any] = {
            "schema_version": _OPERATION_SCHEMA_VERSION,
            "operation_id": operation_id,
            "phase": phase,
            "source_revision": source_revision,
            "input_sha256": input_sha256,
            "candidate_snapshot_id": candidate_snapshot_id,
            "base_structural_snapshot_id": base_structural_snapshot_id,
            "outcome": outcome,
            "terminal_outcome": terminal_outcome,
        }
        if failure_category:
            data["failure_category"] = failure_category[:64]
        if published_snapshot_id:
            data["published_snapshot_id"] = published_snapshot_id
        atomic_json(self._operation_path(ctx), data)

    def _safe_finish_operation(
        self,
        ctx: KnowledgeContext,
        *,
        operation_id: str,
        phase: str,
        source_revision: str,
        outcome: str,
        terminal_outcome: str,
        input_sha256: str | None = None,
        candidate_snapshot_id: str | None = None,
        base_structural_snapshot_id: str | None = None,
        failure_category: str | None = None,
        published_snapshot_id: str | None = None,
    ) -> None:
        with contextlib.suppress(Exception):
            self._write_operation(
                ctx,
                operation_id=operation_id,
                phase=phase,
                outcome=outcome,
                source_revision=source_revision,
                input_sha256=input_sha256,
                candidate_snapshot_id=candidate_snapshot_id,
                base_structural_snapshot_id=base_structural_snapshot_id,
                terminal_outcome=terminal_outcome,
                failure_category=failure_category,
                published_snapshot_id=published_snapshot_id,
            )

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
        if (
            actual != expected
            or manifest.get("snapshot_id") != pointer.get("snapshot_id")
            or manifest.get("complete") is not True
        ):
            raise KnowledgeError(
                "INDEX_CORRUPT", "The snapshot does not belong to this project revision."
            )
        graph = location / "graphify-out" / "graph.json"
        try:
            graph_is_file = graph.is_file()
            graph_size = graph.stat().st_size if graph_is_file else 0
        except OSError as exc:
            raise KnowledgeError(
                "INDEX_CORRUPT", "The snapshot graph is missing or unsafe."
            ) from exc
        if graph.is_symlink() or not graph_is_file or graph_size > MAX_GRAPH_BYTES:
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot graph is missing or unsafe.")
        try:
            graph_bytes = read_private_bytes(graph)
        except (OSError, ValueError) as exc:
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot graph path is unsafe.") from exc
        if hashlib.sha256(graph_bytes).hexdigest() != manifest.get("graph_sha256"):
            raise KnowledgeError("INDEX_CORRUPT", "The snapshot graph changed after publication.")
        if isinstance(manifest.get("semantic"), dict) and not self._base_is_valid(ctx, manifest):
            manifest["_base_integrity_invalid"] = True
        return location, manifest

    def _manifest_for_recovery(self, ctx: KnowledgeContext) -> tuple[Path, dict[str, Any]] | None:
        """Read only pointer/manifest identity when the published graph is corrupt."""
        try:
            pointer = load_json(self._pointer(ctx), limit=64_000)
            snapshot_id = str(pointer.get("snapshot_id", "")) if isinstance(pointer, dict) else ""
            if not _SNAPSHOT_ID.fullmatch(snapshot_id):
                return None
            location = self._cache_location(ctx, snapshot_id)
            manifest = load_json(location / "manifest.json")
            if not isinstance(manifest, dict):
                return None
            if (
                manifest.get("project_id") != ctx.project_id
                or manifest.get("view_id") != ctx.view_id
                or manifest.get("source_revision") != ctx.source_revision
            ):
                return None
            return location, manifest
        except (FileNotFoundError, KnowledgeError, OSError, ValueError):
            return None

    def _envelope(
        self, ctx: KnowledgeContext, action: str, manifest: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        dirty = _dirty(ctx)
        operation = self._load_operation(ctx)
        warnings = ["Derived navigation only; verify current sources and tests."]
        if manifest is not None:
            # Snapshot wording is selected from immutable manifest state, never from the
            # configuration that happens to be loaded now.
            warnings.extend(semantic_snapshot_warnings(manifest))
        if operation and operation.get("active") and action != "update":
            warnings.append(
                "A knowledge update is in progress or was interrupted; this result comes "
                "from the last immutable snapshot."
            )
        if dirty:
            warnings.append("Files changed since this indexed revision require direct inspection.")
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
            "operation": operation,
            "warnings": warnings,
        }

    def execute(
        self,
        context: KnowledgeContext,
        action: str,
        arguments: dict[str, Any],
        *,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        cancel_event = cancel_event or _CANCEL_EVENT.get()
        if action == "update":
            return self.update(context, arguments, cancel_event=cancel_event)
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
                trusted, _reason = _semantic_integrity(manifest)
                result["semantic_trusted"] = trusted
                result["semantic_pending"] = (
                    manifest["semantic"].get("state")
                    not in (
                        "complete",
                        "disabled",
                    )
                    or not trusted
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
        return result

    def _backend_run(
        self,
        action: str,
        *,
        cancel_event: threading.Event | None = None,
        deadline: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if self.backend is None:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Configure Graphify before graph updates."
            )
        if deadline is not None:
            from .graphify import run_bounded_graphify

            return run_bounded_graphify(
                self.backend,
                action,
                deadline=deadline,
                cancel_event=cancel_event,
                **kwargs,
            )
        if cancel_event is None:
            return self.backend.run(action, **kwargs)
        try:
            return self.backend.run(action, cancel_event=cancel_event, **kwargs)
        except TypeError as exc:
            # Small test doubles and older private adapters may not expose the additive
            # keyword. Do not hide a TypeError raised by the action itself.
            if "cancel_event" not in str(exc):
                raise
            return self.backend.run(action, **kwargs)

    def _base_location(self, ctx: KnowledgeContext, base_id: str) -> Path:
        return self.cache_root / "knowledge" / ctx.project_id / base_id

    def _write_structural_base(
        self,
        ctx: KnowledgeContext,
        *,
        base_id: str,
        graph_bytes: bytes,
        inputs: dict[str, str],
        input_sha256: str,
    ) -> str:
        digest = hashlib.sha256(graph_bytes).hexdigest()
        location = self._base_location(ctx, base_id)
        graph_path = location / "graphify-out" / "graph.json"
        atomic_private_write(graph_path, graph_bytes)
        atomic_json(
            location / "manifest.json",
            {
                "schema_version": 1,
                "kind": "structural-base",
                "complete": True,
                "integrity_version": SNAPSHOT_INTEGRITY_VERSION,
                "project_id": ctx.project_id,
                "view_id": ctx.view_id,
                "snapshot_id": base_id,
                "source_revision": ctx.source_revision,
                "engine_version": GRAPHIFY_VERSION,
                "scope_version": _SCOPE_VERSION,
                "inputs": inputs,
                "input_sha256": input_sha256,
                "graph_sha256": digest,
                "created_at": time.time(),
            },
        )
        return digest

    def _base_is_valid(self, ctx: KnowledgeContext, manifest: dict[str, Any]) -> bool:
        base_id = str(manifest.get("base_structural_snapshot_id", ""))
        if not _SNAPSHOT_ID.fullmatch(base_id):
            return False
        try:
            base_location = self._base_location(ctx, base_id)
            base_manifest = load_json(base_location / "manifest.json")
            base_graph = base_location / "graphify-out" / "graph.json"
            if (
                not isinstance(base_manifest, dict)
                or base_manifest.get("kind") != "structural-base"
            ):
                return False
            if (
                base_manifest.get("project_id") != ctx.project_id
                or base_manifest.get("view_id") != ctx.view_id
                or base_manifest.get("source_revision") != ctx.source_revision
                or base_manifest.get("inputs") != manifest.get("inputs")
            ):
                return False
            if base_graph.is_symlink() or not base_graph.is_file():
                return False
            payload = read_private_bytes(base_graph)
            digest = hashlib.sha256(payload).hexdigest()
            return (
                len(payload) <= MAX_GRAPH_BYTES
                and digest == base_manifest.get("graph_sha256")
                and digest == manifest.get("base_structural_digest")
            )
        except (KnowledgeError, OSError, ValueError):
            return False

    def _restore_structural_base(
        self,
        ctx: KnowledgeContext,
        *,
        base_id: str,
        graph_path: Path,
        inputs: dict[str, str],
    ) -> str | None:
        if not _SNAPSHOT_ID.fullmatch(base_id):
            return None
        location = self._base_location(ctx, base_id)
        try:
            base_manifest = load_json(location / "manifest.json")
            base_graph = location / "graphify-out" / "graph.json"
            if (
                not isinstance(base_manifest, dict)
                or base_manifest.get("kind") != "structural-base"
            ):
                return None
            if (
                base_manifest.get("project_id") != ctx.project_id
                or base_manifest.get("view_id") != ctx.view_id
                or base_manifest.get("source_revision") != ctx.source_revision
                or base_manifest.get("inputs") != inputs
            ):
                return None
            if base_graph.is_symlink() or not base_graph.is_file():
                return None
            payload = read_private_bytes(base_graph)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != base_manifest.get("graph_sha256") or len(payload) > MAX_GRAPH_BYTES:
                return None
            atomic_private_write(graph_path, payload)
            return digest
        except (KnowledgeError, OSError, ValueError):
            return None

    def _validate_candidate(
        self,
        ctx: KnowledgeContext,
        location: Path,
        manifest: dict[str, Any],
        *,
        inputs: dict[str, str],
    ) -> tuple[dict[str, Any], bytes]:
        if manifest.get("integrity_version") != SNAPSHOT_INTEGRITY_VERSION:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate integrity metadata is missing.")
        if manifest.get("project_id") != ctx.project_id or manifest.get("view_id") != ctx.view_id:
            raise KnowledgeError(
                "INDEX_CORRUPT", "Candidate identity does not match the bound view."
            )
        if (
            manifest.get("source_revision") != ctx.source_revision
            or manifest.get("inputs") != inputs
        ):
            raise KnowledgeError(
                "INDEX_CORRUPT", "Candidate inputs do not match the bound revision."
            )
        if manifest.get("complete") is not True or not _SNAPSHOT_ID.fullmatch(
            str(manifest.get("snapshot_id", ""))
        ):
            raise KnowledgeError("INDEX_CORRUPT", "Candidate manifest is not publishable.")
        semantic = manifest.get("semantic")
        trusted, _reason = _semantic_integrity(manifest)
        if not trusted or not isinstance(semantic, dict):
            raise KnowledgeError("INDEX_CORRUPT", "Candidate semantic integrity is invalid.")
        graph = location / "graphify-out" / "graph.json"
        try:
            graph_is_file = graph.is_file()
            graph_size = graph.stat().st_size if graph_is_file else 0
        except OSError as exc:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate graph is missing or unsafe.") from exc
        if graph.is_symlink() or not graph_is_file or graph_size > MAX_GRAPH_BYTES:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate graph is missing or unsafe.")
        graph_bytes = read_private_bytes(graph)
        if hashlib.sha256(graph_bytes).hexdigest() != manifest.get("graph_sha256"):
            raise KnowledgeError(
                "INDEX_CORRUPT", "Candidate graph digest does not match its manifest."
            )
        base_id = str(manifest.get("base_structural_snapshot_id"))
        base_location = self._base_location(ctx, base_id)
        base_manifest = load_json(base_location / "manifest.json")
        base_graph = base_location / "graphify-out" / "graph.json"
        try:
            base_is_file = base_graph.is_file()
            base_size = base_graph.stat().st_size if base_is_file else 0
        except OSError as exc:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate structural base is invalid.") from exc
        if not isinstance(base_manifest, dict) or base_manifest.get("inputs") != inputs:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate structural base is invalid.")
        if base_graph.is_symlink() or not base_is_file or base_size > MAX_GRAPH_BYTES:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate structural base is invalid.")
        base_bytes = read_private_bytes(base_graph)
        base_digest = hashlib.sha256(base_bytes).hexdigest()
        if base_manifest.get("graph_sha256") != base_digest:
            raise KnowledgeError("INDEX_CORRUPT", "Candidate structural base is invalid.")
        if base_digest != manifest.get("base_structural_digest"):
            raise KnowledgeError(
                "INDEX_CORRUPT", "Candidate structural base digest does not match."
            )
        return manifest, graph_bytes

    def _publish_candidate(self, ctx: KnowledgeContext, manifest: dict[str, Any]) -> None:
        manifest_path = self._cache_location(ctx, str(manifest["snapshot_id"])) / "manifest.json"
        manifest_bytes = read_private_bytes(manifest_path)
        atomic_json(
            self._pointer(ctx),
            {
                "schema_version": 1,
                "snapshot_id": manifest["snapshot_id"],
                "source_revision": ctx.source_revision,
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            },
        )

    def _cache_location(self, ctx: KnowledgeContext, snapshot_id: str) -> Path:
        if not _SNAPSHOT_ID.fullmatch(snapshot_id):
            raise KnowledgeError("INDEX_CORRUPT", "Invalid snapshot identity.")
        return self.cache_root / "knowledge" / ctx.project_id / snapshot_id

    def _semantic_versions(self, semantic_meta: dict[str, Any]) -> tuple[str, str]:
        pipeline = semantic_meta.get("pipeline")
        pipeline_version = (
            pipeline.get("version") if isinstance(pipeline, dict) else None
        ) or SEMANTIC_PIPELINE_VERSION
        cache_version = semantic_meta.get("cache_version") or SEMANTIC_CACHE_VERSION
        semantic_meta["pipeline_version"] = pipeline_version
        semantic_meta["cache_version"] = cache_version
        semantic_meta.setdefault("version", pipeline_version)
        if not isinstance(semantic_meta.get("pipeline"), dict):
            semantic_meta["pipeline"] = {"version": pipeline_version}
        else:
            semantic_meta["pipeline"]["version"] = pipeline_version
        return str(pipeline_version), str(cache_version)

    @contextlib.contextmanager
    def _operation_scope(self, ctx: KnowledgeContext, operation_id: str):
        state: dict[str, Any] = {
            "phase": "prepare",
            "input_sha256": None,
            "candidate": None,
            "base": None,
        }
        self._write_operation(
            ctx,
            operation_id=operation_id,
            phase="prepare",
            outcome="running",
            source_revision=ctx.source_revision,
        )
        try:
            yield state
        except BaseException as exc:
            category = exc.code if isinstance(exc, KnowledgeError) else type(exc).__name__.lower()
            terminal = "cancelled" if category == "OPERATION_CANCELLED" else "failed"
            self._safe_finish_operation(
                ctx,
                operation_id=operation_id,
                phase=str(state["phase"]),
                source_revision=ctx.source_revision,
                outcome=terminal,
                terminal_outcome=terminal,
                input_sha256=state.get("input_sha256"),
                candidate_snapshot_id=state.get("candidate"),
                base_structural_snapshot_id=state.get("base"),
                failure_category=category,
            )
            raise
        else:
            terminal = str(
                state.get("terminal") or ("published" if state.get("published") else "completed")
            )
            self._safe_finish_operation(
                ctx,
                operation_id=operation_id,
                phase=str(state["phase"]),
                source_revision=ctx.source_revision,
                outcome=terminal,
                terminal_outcome=terminal,
                input_sha256=state.get("input_sha256"),
                candidate_snapshot_id=state.get("candidate"),
                base_structural_snapshot_id=state.get("base"),
                failure_category=state.get("failure_category"),
                published_snapshot_id=state.get("published"),
            )

    def _operation_phase(
        self,
        ctx: KnowledgeContext,
        operation_id: str,
        state: dict[str, Any],
        phase: str,
        *,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """Record one lifecycle boundary, then refuse to continue past a cancellation."""
        state["phase"] = phase
        self._write_operation(
            ctx,
            operation_id=operation_id,
            phase=phase,
            outcome="running",
            source_revision=ctx.source_revision,
            input_sha256=state.get("input_sha256"),
            candidate_snapshot_id=state.get("candidate"),
            base_structural_snapshot_id=state.get("base"),
        )
        if cancel_event is not None and cancel_event.is_set():
            raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")

    def update(
        self,
        ctx: KnowledgeContext,
        args: dict[str, Any],
        *,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        started_at = _now()
        mode = args.get("mode", "configured")
        if mode not in ("structural", "configured"):
            raise KnowledgeError("ARGUMENT_INVALID", "Invalid update mode.")
        for path in args.get("changed_paths", []):
            _relative(path)
        if self.backend is None:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Configure Graphify before graph updates."
            )
        cfg = self.configuration()
        req_deadline = args.get("deadline_seconds")
        cfg_deadline = cfg.get("deadline_seconds")
        budget = 300.0
        if req_deadline is not None:
            try:
                budget = min(budget, float(req_deadline))
            except (TypeError, ValueError):
                pass
        if cfg_deadline is not None:
            try:
                budget = min(budget, float(cfg_deadline))
            except (TypeError, ValueError):
                pass
        budget = max(0.0, min(budget, 300.0))
        deadline = started_at + budget
        view = self._view(ctx)
        operation_cancel = cancel_event or threading.Event()
        operation_id = uuid.uuid4().hex
        with (
            stable_lock(view / "update.lock", timeout=10.0),
            self._operation_scope(ctx, operation_id) as operation,
        ):

            def _deadline_result(
                manifest: dict[str, Any] | None = None,
                semantic: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
                operation["terminal"] = "deadline"
                operation["failure_category"] = "deadline"
                result = self._envelope(ctx, "update", manifest)
                result.update(
                    outcome="unchanged" if manifest is not None else "pending",
                    semantic_pending=True,
                    uncovered_paths=result["dirty_paths"],
                )
                result["warnings"].append(
                    "Operation deadline reached; no candidate snapshot was published."
                )
                if semantic is not None:
                    result["semantic"] = semantic
                return result

            try:
                self._backend_run("probe", deadline=deadline, cancel_event=operation_cancel)
            except KnowledgeError as exc:
                if getattr(exc, "operation_deadline_timeout", False):
                    return _deadline_result()
                raise
            if operation_cancel.is_set():
                raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")
            if _now() >= deadline:
                return _deadline_result()
            sem_cfg = cfg.get("semantic", {})
            sem_enabled = bool(cfg.get("semantic_enabled") or sem_cfg.get("enabled"))

            existing_manifest = None
            existing_location = None
            existing_snapshot_valid = True
            try:
                existing_location, existing_manifest = self._snapshot(ctx)
            except KnowledgeError as exc:
                existing_snapshot_valid = False
                if exc.code not in ("INDEX_MISSING", "INDEX_CORRUPT"):
                    raise
                recovered = self._manifest_for_recovery(ctx)
                if recovered is not None:
                    existing_location, existing_manifest = recovered

            sources, excluded = _sources(ctx)
            if not sources:
                raise KnowledgeError("SCOPE_UNAVAILABLE", "No supported non-secret text remains.")

            inputs = {
                path: hashlib.sha256(content).hexdigest() for path, content in sources.items()
            }
            input_sha256 = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
            if operation_cancel.is_set():
                raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")
            if _now() >= deadline:
                return _deadline_result(existing_manifest)
            operation["input_sha256"] = input_sha256
            self._operation_phase(
                ctx, operation_id, operation, "prepare", cancel_event=operation_cancel
            )

            # Check if existing snapshot matches the exact current inputs. A legacy or
            # incomplete semantic envelope is deliberately not eligible for the fast path.
            existing_semantic = (
                existing_manifest.get("semantic") if isinstance(existing_manifest, dict) else None
            )
            existing_trusted = (
                _semantic_integrity(existing_manifest)[0]
                if isinstance(existing_manifest, dict) and isinstance(existing_semantic, dict)
                else False
            )
            same_inputs = (
                existing_manifest is not None
                and existing_location is not None
                and existing_manifest.get("complete") is True
                and existing_manifest.get("source_revision") == ctx.source_revision
                and existing_manifest.get("inputs") == inputs
                and existing_snapshot_valid
                and existing_trusted
                and self._base_is_valid(ctx, existing_manifest)
                and (existing_location / "graphify-out" / "graph.json").is_file()
            )

            if same_inputs and existing_manifest is not None and existing_location is not None:
                existing_sem = existing_manifest.get("semantic", {})
                existing_sem_state = existing_sem.get("state")

                if mode == "structural":
                    # Structural update preserves existing snapshot without running LLM.
                    # Honestly report whether semantic work remains pending or partial.
                    if not sem_enabled or existing_sem_state == "disabled":
                        semantic_pending = False
                    elif existing_sem_state == "complete":
                        semantic_pending = False
                    else:
                        semantic_pending = True

                    result = self._envelope(ctx, "update", existing_manifest)
                    result.update(
                        outcome="unchanged",
                        indexed_revision=ctx.source_revision,
                        semantic_pending=semantic_pending,
                        uncovered_paths=result["dirty_paths"],
                    )
                    if "semantic" in existing_manifest:
                        result["semantic"] = existing_manifest["semantic"]
                    operation["terminal"] = "unchanged"
                    return result

                if mode == "configured":
                    if not sem_enabled:
                        if existing_sem_state in ("complete", "disabled"):
                            result = self._envelope(ctx, "update", existing_manifest)
                            result.update(
                                outcome="unchanged",
                                indexed_revision=ctx.source_revision,
                                semantic_pending=False,
                                uncovered_paths=result["dirty_paths"],
                            )
                            if "semantic" in existing_manifest:
                                result["semantic"] = existing_manifest["semantic"]
                            operation["terminal"] = "unchanged"
                            return result
                    else:
                        # Semantic is enabled: compare expected fingerprint
                        from .semantic import compute_semantic_fingerprint

                        expected_fp = compute_semantic_fingerprint(
                            backend=self.backend,
                            source_root=existing_location / "sources",
                            graph_path=existing_location / "graphify-out" / "graph.json",
                            inputs=inputs,
                            configuration=cfg,
                            deadline=deadline,
                            cancel_event=operation_cancel,
                        )
                        if (
                            expected_fp is not None
                            and existing_sem_state == "complete"
                            and existing_sem.get("fingerprint") == expected_fp
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
                            operation["terminal"] = "unchanged"
                            return result

            # Create a brand-new immutable snapshot directory (never mutate in-place).
            new_snapshot_id = uuid.uuid4().hex
            operation["candidate"] = new_snapshot_id
            new_location = self.cache_root / "knowledge" / ctx.project_id / new_snapshot_id
            new_source_root = new_location / "sources"
            ensure_private_dir(new_source_root)
            for path, content in sources.items():
                destination = new_source_root / path
                ensure_private_dir(destination.parent)
                atomic_private_write(destination, content)

            new_output = new_location / "graphify-out" / "graph.json"
            ensure_private_dir(new_output.parent)
            self._operation_phase(
                ctx, operation_id, operation, "validate", cancel_event=operation_cancel
            )
            base_id = uuid.uuid4().hex
            operation["base"] = base_id
            structural_digest = None
            # A prior v1 snapshot may carry a pure base. Prefer it when recovering a
            # legacy/corrupt semantic overlay; otherwise ask Graphify for a fresh base.
            prior_base_id = (
                str(existing_manifest.get("base_structural_snapshot_id", ""))
                if isinstance(existing_manifest, dict)
                else ""
            )
            if mode == "structural" and prior_base_id:
                structural_digest = self._restore_structural_base(
                    ctx,
                    base_id=prior_base_id,
                    graph_path=new_output,
                    inputs=inputs,
                )
            if structural_digest is None:
                try:
                    self._backend_run(
                        "update",
                        source_root=new_source_root,
                        graph_path=new_output,
                        deadline=deadline,
                        cancel_event=operation_cancel,
                    )
                except KnowledgeError as exc:
                    if getattr(exc, "operation_deadline_timeout", False):
                        return _deadline_result(existing_manifest)
                    raise
            if operation_cancel.is_set():
                raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")
            if _now() >= deadline:
                return _deadline_result(existing_manifest)

            try:
                output_is_file = new_output.is_file()
                output_size = new_output.stat().st_size if output_is_file else 0
            except OSError as exc:
                raise KnowledgeError(
                    "INDEX_CORRUPT", "Graphify did not create a bounded regular graph."
                ) from exc
            if new_output.is_symlink() or not output_is_file or output_size > MAX_GRAPH_BYTES:
                raise KnowledgeError(
                    "INDEX_CORRUPT", "Graphify did not create a bounded regular graph."
                )
            graph_bytes = read_private_bytes(new_output)
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
                        path = path.relative_to(new_source_root)
                    except ValueError as exc:
                        raise KnowledgeError(
                            "INDEX_CORRUPT", "A graph source escaped its captured project."
                        ) from exc
                if ".." in path.parts:
                    raise KnowledgeError(
                        "INDEX_CORRUPT", "A graph source escaped its captured project."
                    )
            if structural_digest is None:
                structural_digest = self._write_structural_base(
                    ctx,
                    base_id=base_id,
                    graph_bytes=graph_bytes,
                    inputs=inputs,
                    input_sha256=input_sha256,
                )
            else:
                # Recovery used an old base id; retain it as the published candidate's
                # reference and record a fresh base manifest only when necessary.
                base_id = prior_base_id
                operation["base"] = base_id

            from .semantic import _ELIGIBLE_EXTENSIONS

            eligible_files = [
                p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS
            ]
            semantic_meta: dict[str, Any] = {"state": "disabled", "fingerprint": None}
            semantic_failed_or_incomplete = False

            if mode == "structural":
                if sem_enabled:
                    semantic_meta = {
                        "state": "pending",
                        "fingerprint": None,
                        "covered_paths": [],
                        "pending_paths": sorted(eligible_files),
                        "failed_paths": [],
                        "validated_chunk_ids": [],
                        "observed_usage": {},
                    }
                else:
                    semantic_meta = {
                        "state": "disabled",
                        "fingerprint": None,
                        "covered_paths": [],
                        "pending_paths": [],
                        "failed_paths": [],
                        "validated_chunk_ids": [],
                        "observed_usage": {},
                    }
            elif mode == "configured":
                if not sem_enabled:
                    semantic_meta = {
                        "state": "disabled",
                        "fingerprint": None,
                        "covered_paths": [],
                        "pending_paths": [],
                        "failed_paths": [],
                        "validated_chunk_ids": [],
                        "observed_usage": {},
                    }
                else:
                    from .semantic import run_semantic_extraction

                    self._operation_phase(
                        ctx, operation_id, operation, "compose", cancel_event=operation_cancel
                    )

                    def revalidate_legacy_fragment(fragment: dict[str, Any]) -> bool:
                        if not isinstance(fragment, dict):
                            return False
                        try:
                            checked = self._backend_run(
                                "semantic_validate",
                                source_root=new_source_root,
                                graph_path=new_output,
                                arguments={
                                    "model_text": json.dumps(fragment, ensure_ascii=False),
                                    "allowed_sources": list(inputs),
                                    "allow_empty": False,
                                },
                                deadline=deadline,
                                cancel_event=operation_cancel,
                            )
                        except Exception:
                            return False
                        return bool(checked.get("ok") and isinstance(checked.get("fragment"), dict))

                    try:
                        with graphify_cancel_scope(operation_cancel):
                            semantic_meta = run_semantic_extraction(
                                backend=self.backend,
                                source_root=new_source_root,
                                graph_path=new_output,
                                inputs=inputs,
                                cache_root=self.cache_root,
                                ctx=ctx,
                                configuration=cfg,
                                cancel_event=operation_cancel,
                                legacy_cache_revalidator=revalidate_legacy_fragment,
                                operation_deadline=deadline,
                            )
                        if operation_cancel.is_set() and not (
                            isinstance(semantic_meta, dict)
                            and semantic_meta.get("pipeline", {}).get("deadline_exhausted")
                        ):
                            raise KnowledgeError(
                                "OPERATION_CANCELLED", "Semantic extraction was cancelled."
                            )
                        if _now() >= deadline:
                            semantic_failed_or_incomplete = True
                            if isinstance(semantic_meta, dict):
                                semantic_meta.setdefault("pipeline", {})["deadline_exhausted"] = (
                                    True
                                )
                                semantic_meta["reason_category"] = "deadline"
                        if semantic_meta.get("state") != "complete":
                            semantic_failed_or_incomplete = True
                    except KnowledgeError as exc:
                        if exc.code == "OPERATION_CANCELLED":
                            raise
                        semantic_failed_or_incomplete = True
                        deadline_exc = getattr(exc, "operation_deadline_timeout", False)
                        reason_cat = "deadline" if deadline_exc else exc.code.lower()
                        semantic_meta = {
                            "state": "pending" if deadline_exc else "unavailable",
                            "fingerprint": None,
                            "covered_paths": [],
                            "pending_paths": sorted(eligible_files),
                            "failed_paths": [],
                            "validated_chunk_ids": [],
                            "reason_category": reason_cat,
                            "pipeline": {
                                "deadline_exhausted": deadline_exc,
                                "operation_wide": deadline_exc,
                            },
                            "observed_usage": {},
                        }
                    except Exception as exc:
                        semantic_failed_or_incomplete = True
                        semantic_meta = {
                            "state": "unavailable",
                            "fingerprint": None,
                            "covered_paths": [],
                            "pending_paths": sorted(eligible_files),
                            "failed_paths": [],
                            "validated_chunk_ids": [],
                            "reason_category": type(exc).__name__.lower(),
                            "observed_usage": {},
                        }

            operation_deadline_exhausted = _now() >= deadline or (
                isinstance(semantic_meta, dict)
                and semantic_meta.get("pipeline", {}).get("operation_wide") is True
                and semantic_meta.get("pipeline", {}).get("deadline_exhausted") is True
            )
            if operation_deadline_exhausted:
                return _deadline_result(existing_manifest, semantic_meta)

            # If semantic refresh failed or was incomplete on an existing complete snapshot:
            # retain the prior complete snapshot and keep the new candidate as diagnostic evidence.
            if (
                semantic_failed_or_incomplete
                and same_inputs
                and existing_manifest is not None
                and existing_manifest.get("semantic", {}).get("state") == "complete"
            ):
                with contextlib.suppress(Exception):
                    atomic_json(
                        new_location / "candidate-operation.json",
                        {
                            "schema_version": _OPERATION_SCHEMA_VERSION,
                            "integrity_version": SNAPSHOT_INTEGRITY_VERSION,
                            "source_revision": ctx.source_revision,
                            "input_sha256": input_sha256,
                            "candidate_snapshot_id": new_snapshot_id,
                            "base_structural_snapshot_id": base_id,
                            "terminal_outcome": "not_published",
                            "reason_category": semantic_meta.get("reason_category", "incomplete"),
                        },
                    )
                result = self._envelope(ctx, "update", existing_manifest)
                result.update(
                    outcome="unchanged",
                    indexed_revision=ctx.source_revision,
                    semantic_pending=False,
                    uncovered_paths=result["dirty_paths"],
                )
                result["warnings"].append("Refresh failed; retained previously complete snapshot.")
                if "semantic" in existing_manifest:
                    result["semantic"] = existing_manifest["semantic"]
                operation["terminal"] = "retained"
                return result

            sem_state = semantic_meta.get("state")
            compose_receipt = semantic_meta.get("compose")
            if sem_state == "complete" and isinstance(compose_receipt, dict):
                if compose_receipt.get("structural_preserved") is False or (
                    compose_receipt.get("invoked") and not compose_receipt.get("structural_digest")
                ):
                    sem_state = "unavailable"
                    semantic_meta["state"] = sem_state
                    semantic_meta["reason_category"] = "integrity"
                    semantic_failed_or_incomplete = True
            if sem_state == "unavailable":
                restored_digest = self._restore_structural_base(
                    ctx,
                    base_id=base_id,
                    graph_path=new_output,
                    inputs=inputs,
                )
                if restored_digest is None:
                    raise KnowledgeError(
                        "INDEX_CORRUPT", "Semantic failure could not restore the structural base."
                    )
                structural_digest = restored_digest
            pipeline_version, cache_version = self._semantic_versions(semantic_meta)
            semantic_meta["integrity_version"] = SNAPSHOT_INTEGRITY_VERSION
            semantic_meta["base_structural_snapshot_id"] = base_id
            semantic_meta["base_structural_digest"] = structural_digest
            semantic_digest = semantic_meta.get("structural_digest")
            if not isinstance(semantic_digest, str) or not semantic_digest:
                semantic_digest = structural_digest
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

            graph_bytes = read_private_bytes(new_output)
            manifest = {
                "schema_version": 1,
                "integrity_version": SNAPSHOT_INTEGRITY_VERSION,
                "pipeline_version": pipeline_version,
                "cache_version": cache_version,
                "complete": True,
                "project_id": ctx.project_id,
                "view_id": ctx.view_id,
                "snapshot_id": new_snapshot_id,
                "source_revision": ctx.source_revision,
                "engine_version": GRAPHIFY_VERSION,
                "scope_version": _SCOPE_VERSION,
                "inputs": inputs,
                "input_sha256": input_sha256,
                "graph_sha256": hashlib.sha256(graph_bytes).hexdigest(),
                "base_structural_snapshot_id": base_id,
                "base_structural_digest": structural_digest,
                "structural_digest": semantic_digest,
                "coverage": coverage,
                "semantic": semantic_meta,
                "excluded_count": len(excluded),
                "created_at": time.time(),
                "publisher_role": ctx.role_id,
            }
            if (cancel_event is not None and cancel_event.is_set()) or _host_interrupt_requested():
                raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")
            if _now() >= deadline:
                raise KnowledgeError(
                    "TIMEOUT", "Operation deadline exceeded before pointer publication."
                )
            self._operation_phase(
                ctx, operation_id, operation, "manifest", cancel_event=cancel_event
            )
            atomic_json(new_location / "manifest.json", manifest)
            self._validate_candidate(ctx, new_location, manifest, inputs=inputs)
            if (cancel_event is not None and cancel_event.is_set()) or _host_interrupt_requested():
                raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")
            if _now() >= deadline:
                raise KnowledgeError(
                    "TIMEOUT", "Operation deadline exceeded before pointer publication."
                )
            self._operation_phase(
                ctx, operation_id, operation, "pointer", cancel_event=cancel_event
            )
            self._publish_candidate(ctx, manifest)
            operation["published"] = new_snapshot_id
            self._safe_finish_operation(
                ctx,
                operation_id=operation_id,
                phase="pointer",
                source_revision=ctx.source_revision,
                outcome="published",
                terminal_outcome="published",
                input_sha256=input_sha256,
                candidate_snapshot_id=new_snapshot_id,
                base_structural_snapshot_id=base_id,
                published_snapshot_id=new_snapshot_id,
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
