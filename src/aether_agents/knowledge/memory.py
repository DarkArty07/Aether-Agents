"""Durable role/project experiences with native Graphify note rendering.

Only current note revisions participate in retrieval and reflection. Graphify's
optional learning sidecar is never written beside a shared technical graph.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from aether_agents.paths import atomic_private_write, ensure_private_dir, read_private_bytes

from .common import ROLES, KnowledgeError, atomic_json, bounded, git, load_json, stable_lock
from .context import KnowledgeContext
from .graphify import GraphifyBackend

_NOTE_ID = re.compile(r"^wn_[a-f0-9]{32}$")
_SAVE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,159}$")
_SECRETS = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}|\bAKIA[A-Z0-9]{16}\b"
)


def _text(args: dict[str, Any], name: str, maximum: int = 8192) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise KnowledgeError(
            "ARGUMENT_INVALID", f"{name} must be nonempty text of at most {maximum} characters."
        )
    if _SECRETS.search(value):
        raise KnowledgeError(
            "SENSITIVE_CONTENT", "Do not store credentials or private keys in work notes."
        )
    return value.strip()


def _is_dirty(ctx: KnowledgeContext) -> bool:
    changed = git(ctx.root, "diff", "--name-only", "-z", ctx.source_revision)
    new = git(ctx.root, "ls-files", "--others", "--exclude-standard", "-z")
    return bool(any(p for p in (changed + new).split(b"\0") if p))


def _validate_record_metadata(record: dict[str, Any]) -> None:
    source_rev = record.get("source_revision")
    if not isinstance(source_rev, str) or not re.fullmatch(r"[a-f0-9]{40,64}", source_rev):
        raise KnowledgeError("MEMORY_CORRUPT", "Note source revision is invalid.")
    markdown_sha = record.get("markdown_sha256")
    if not isinstance(markdown_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", markdown_sha):
        raise KnowledgeError("MEMORY_CORRUPT", "Note markdown hash is missing or invalid.")
    actor = record.get("actor")
    if not isinstance(actor, dict) or not all(
        isinstance(actor.get(k), str) for k in ("session_id", "task_id", "run_id")
    ):
        raise KnowledgeError("MEMORY_CORRUPT", "Note actor metadata is invalid.")
    for field in ("situation", "lesson", "applicability"):
        val = record.get(field)
        if not isinstance(val, str):
            raise KnowledgeError("MEMORY_CORRUPT", f"Note {field} is invalid.")
    outcome = record.get("outcome")
    if outcome not in ("useful", "dead_end", "corrected"):
        raise KnowledgeError("MEMORY_CORRUPT", "Note outcome is invalid.")
    source_nodes = record.get("source_nodes")
    if not isinstance(source_nodes, list) or any(not isinstance(n, str) for n in source_nodes):
        raise KnowledgeError("MEMORY_CORRUPT", "Note source nodes are invalid.")
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(e, dict) for e in evidence):
        raise KnowledgeError("MEMORY_CORRUPT", "Note evidence is invalid.")
    verification = record.get("verification")
    if not isinstance(verification, str):
        raise KnowledgeError("MEMORY_CORRUPT", "Note verification is invalid.")
    updated_at = record.get("updated_at")
    if not isinstance(updated_at, (int, float)):
        raise KnowledgeError("MEMORY_CORRUPT", "Note timestamp is invalid.")


def _verify_note_content(path: Path, record: dict[str, Any]) -> bytes:
    try:
        raw = read_private_bytes(path / "note.md")
    except (FileNotFoundError, OSError):
        raise KnowledgeError("MEMORY_CORRUPT", "A note changed outside its recorded revision.")
    if hashlib.sha256(raw).hexdigest() != record.get("markdown_sha256"):
        raise KnowledgeError("MEMORY_CORRUPT", "A note changed outside its recorded revision.")
    return raw


class WorkMemoryStore:
    def __init__(
        self,
        state_root: Path,
        backend_python: Path | None = None,
        *,
        backend: GraphifyBackend | None = None,
    ):
        self.state_root = state_root
        self.backend = backend
        if self.backend is None and backend_python is not None:
            self.backend = GraphifyBackend(backend_python)

    def _namespace(self, ctx: KnowledgeContext) -> Path:
        try:
            identity = str(uuid.UUID(ctx.project_id))
        except (ValueError, AttributeError) as exc:
            raise KnowledgeError("PROJECT_UNRESOLVED", "Invalid project identity.") from exc
        if identity != ctx.project_id or ctx.role_id not in ROLES:
            raise KnowledgeError("PROJECT_UNRESOLVED", "Invalid work-memory namespace.")
        root = self.state_root / "knowledge" / identity / "memory" / ctx.role_id
        # Checking an existing namespace must not accept a redirection.
        for path in [root, *root.parents]:
            if path.is_symlink():
                raise KnowledgeError("UNSAFE_PATH", "Work-memory state must not contain symlinks.")
            if path == self.state_root:
                break
        return root

    def _index(self, root: Path) -> dict[str, Any]:
        try:
            value = load_json(root / "index.json")
        except FileNotFoundError:
            return {"generation": 0, "heads": {}}
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("heads"), dict)
            or type(value.get("generation")) is not int
        ):
            raise KnowledgeError("MEMORY_CORRUPT", "The work-memory index is invalid.")
        return value

    def _record(self, root: Path, note_id: str, revision: int) -> tuple[Path, dict[str, Any]]:
        if not _NOTE_ID.fullmatch(note_id) or type(revision) is not int or revision < 1:
            raise KnowledgeError("ARGUMENT_INVALID", "Invalid note identity or revision.")
        path = root / "notes" / note_id / str(revision)
        if any(parent.is_symlink() for parent in (root / "notes", path.parent, path)):
            raise KnowledgeError("UNSAFE_PATH", "A work-note directory is redirected.")
        try:
            # Valid character-bounded corrections can exceed 100 KB in UTF-8.
            # Retain the shared bounded artifact limit rather than rejecting
            # records that our public schema and writer both accept.
            record = load_json(path / "record.json")
        except FileNotFoundError as exc:
            raise KnowledgeError("NOTE_MISSING", "This work note is not available.") from exc
        except KnowledgeError as exc:
            if exc.code == "INDEX_CORRUPT":
                raise KnowledgeError("MEMORY_CORRUPT", "The work note record is corrupt.") from exc
            raise
        if not isinstance(record, dict) or record.get("schema_version") != "aether.work-note.v1":
            raise KnowledgeError("MEMORY_CORRUPT", "The work note has an invalid schema.")
        if (
            record.get("note_id") != note_id
            or record.get("revision") != revision
            or record.get("role_id") != root.name
            or record.get("project_id") != root.parent.parent.name
        ):
            raise KnowledgeError("MEMORY_CORRUPT", "Note identity does not match its storage.")
        _validate_record_metadata(record)
        return path, record

    def _native(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.backend is None:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Configure Graphify before saving or reflecting notes."
            )
        return self.backend.run(action, arguments=args)

    def _evidence(self, ctx: KnowledgeContext, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list) or len(raw) > 20:
            raise KnowledgeError(
                "ARGUMENT_INVALID", "evidence must be a list with at most 20 references."
            )
        evidence = []
        for item in raw:
            if not isinstance(item, dict) or set(item) - {"path", "revision", "locator", "result"}:
                raise KnowledgeError(
                    "ARGUMENT_INVALID", "Evidence accepts path, revision, locator and result only."
                )
            path = item.get("path", "")
            if not isinstance(path, str) or not path or len(path) > 500:
                raise KnowledgeError(
                    "ARGUMENT_INVALID", "Evidence requires a project-relative path."
                )
            pure = PurePosixPath(path)
            if (
                pure.is_absolute()
                or ".." in pure.parts
                or "\\" in path
                or any(ord(c) < 32 for c in path)
            ):
                raise KnowledgeError("UNSAFE_PATH", "Evidence may not escape the bound project.")
            revision = item.get("revision", ctx.source_revision)
            if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40,64}", revision):
                raise KnowledgeError(
                    "ARGUMENT_INVALID", "Evidence revision must be a full Git commit."
                )
            source_exists = False
            try:
                if git(ctx.root, "cat-file", "-t", revision).strip() == b"commit":
                    # Object existence alone also accepts trees, gitlinks and
                    # symlink blobs. Inspect the exact committed entry instead
                    # of following the working tree or interpreting path globs.
                    entries = git(
                        ctx.root,
                        "--literal-pathspecs",
                        "ls-tree",
                        "--full-tree",
                        "-z",
                        revision,
                        "--",
                        pure.as_posix(),
                    )
                    for entry in entries.split(b"\0"):
                        metadata, _, name = entry.partition(b"\t")
                        if name == pure.as_posix().encode() and tuple(metadata.split()[:2]) in {
                            (b"100644", b"blob"),
                            (b"100755", b"blob"),
                        }:
                            source_exists = True
                            break
            except KnowledgeError:
                pass
            fields = {key: str(item.get(key, ""))[:1500] for key in ("locator", "result")}
            if _SECRETS.search(json.dumps(fields)):
                raise KnowledgeError("SENSITIVE_CONTENT", "Evidence must not contain credentials.")
            evidence.append(
                {
                    "path": pure.as_posix(),
                    "revision": revision,
                    **fields,
                    "source_exists": source_exists,
                    "result_independently_verified": False,
                }
            )
        return evidence

    @staticmethod
    def _save_key(args: dict[str, Any]) -> str:
        value = _text(args, "idempotency_key", 160)
        if not _SAVE_KEY.fullmatch(value):
            raise KnowledgeError(
                "ARGUMENT_INVALID",
                "idempotency_key must be 8-160 opaque ASCII letters, digits, dots, colons, underscores or hyphens.",
            )
        return value

    def _prepare_payload(
        self, ctx: KnowledgeContext, args: dict[str, Any], *, correcting: bool = False
    ) -> dict[str, Any]:
        situation = _text(args, "situation", 4096)
        lesson = _text(args, "lesson", 16000)
        applicability = _text(args, "applicability", 16000 if correcting else 4096)
        outcome = args.get("outcome")
        if outcome not in ("useful", "dead_end", "corrected"):
            raise KnowledgeError(
                "ARGUMENT_INVALID", "outcome must be useful, dead_end or corrected."
            )
        evidence = self._evidence(ctx, args.get("evidence", []))
        nodes = args.get("source_nodes", [])
        if (
            not isinstance(nodes, list)
            or len(nodes) > 10
            or any(not isinstance(n, str) or len(n) > 500 for n in nodes)
        ):
            raise KnowledgeError(
                "ARGUMENT_INVALID", "source_nodes must contain at most ten bounded strings."
            )
        if any(_SECRETS.search(node) for node in nodes):
            raise KnowledgeError("SENSITIVE_CONTENT", "Source labels must not contain credentials.")
        return {
            "situation": situation,
            "lesson": lesson,
            "applicability": applicability,
            "outcome": outcome,
            "evidence": evidence,
            "source_nodes": nodes,
        }

    @staticmethod
    def _save_fingerprint(ctx: KnowledgeContext, payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            {"source_revision": ctx.source_revision, "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(canonical).hexdigest()

    def _publish(
        self,
        ctx: KnowledgeContext,
        root: Path,
        index: dict[str, Any],
        note_id: str,
        revision: int,
        args: dict[str, Any],
        *,
        correction: str | None = None,
        prepared_payload: dict[str, Any] | None = None,
        idempotency_key_sha256: str | None = None,
        creation_payload_sha256: str | None = None,
    ) -> dict[str, Any]:
        payload = prepared_payload or self._prepare_payload(
            ctx, args, correcting=correction is not None
        )
        situation = payload["situation"]
        lesson = payload["lesson"]
        applicability = payload["applicability"]
        outcome = payload["outcome"]
        evidence = payload["evidence"]
        nodes = payload["source_nodes"]
        note = self._native(
            "memory_save",
            {
                "situation": situation,
                "lesson": lesson,
                "applicability": applicability,
                "outcome": outcome,
                "source_nodes": nodes,
                "correction": lesson if correction is not None else None,
            },
        )
        record = {
            "schema_version": "aether.work-note.v1",
            "note_id": note_id,
            "revision": revision,
            "project_id": ctx.project_id,
            "role_id": ctx.role_id,
            "source_revision": ctx.source_revision,
            "actor": {
                "session_id": ctx.session_id,
                "task_id": ctx.task_id,
                "run_id": ctx.run_id,
            },
            "situation": situation,
            "lesson": lesson,
            "applicability": applicability,
            "outcome": outcome,
            "source_nodes": nodes,
            "evidence": evidence,
            "verification": "reported",
            "correction_reason": correction,
            "supersedes_revision": revision - 1 if revision > 1 else None,
            "updated_at": time.time(),
        }
        if idempotency_key_sha256 is not None:
            record["idempotency_key_sha256"] = idempotency_key_sha256
        if creation_payload_sha256 is not None:
            record["creation_payload_sha256"] = creation_payload_sha256
        destination = root / "notes" / note_id / str(revision)
        if any(parent.is_symlink() for parent in (root / "notes", destination.parent, destination)):
            raise KnowledgeError("UNSAFE_PATH", "A note destination is redirected.")
        if destination.exists():
            if index["heads"].get(note_id, 0) >= revision:
                raise KnowledgeError(
                    "REVISION_CONFLICT", "This immutable note revision already exists."
                )
            # An interrupted publication can leave a revision no reader could acquire.
            shutil.rmtree(destination)
        ensure_private_dir(destination)
        markdown = str(note["content"]).encode()
        atomic_private_write(destination / "note.md", markdown)
        record["markdown_sha256"] = hashlib.sha256(markdown).hexdigest()
        atomic_json(destination / "record.json", record)
        index["heads"][note_id] = revision
        index["generation"] += 1
        atomic_json(root / "index.json", index)
        (root / "reflection.json").unlink(missing_ok=True)
        return {
            "note_id": note_id,
            "revision": revision,
            "generation": index["generation"],
            "source_revision": ctx.source_revision,
            "verification": "reported",
        }

    def execute(self, ctx: KnowledgeContext, action: str, args: dict[str, Any]) -> dict[str, Any]:
        root = self._namespace(ctx)
        result: dict[str, Any] = {
            "schema_version": "aether.work-memory.v1",
            "ok": True,
            "action": action,
            "project_id": ctx.project_id,
            "role_id": ctx.role_id,
        }
        if action in ("save", "correct", "reflect", "delete"):
            with stable_lock(root / "write.lock", timeout=10):
                index = self._index(root)
                if action == "save":
                    save_key = self._save_key(args)
                    prepared = self._prepare_payload(ctx, args)
                    key_sha256 = hashlib.sha256(save_key.encode()).hexdigest()
                    payload_sha256 = self._save_fingerprint(ctx, prepared)
                    note_id = "wn_" + key_sha256[:32]
                    current = index["heads"].get(note_id)
                    if current is not None:
                        _path, existing = self._record(root, note_id, current)
                        if (
                            existing.get("idempotency_key_sha256") != key_sha256
                            or existing.get("creation_payload_sha256") != payload_sha256
                        ):
                            raise KnowledgeError(
                                "IDEMPOTENCY_CONFLICT",
                                "This idempotency key is already bound to a different work note.",
                            )
                        result.update(
                            note_id=note_id,
                            revision=current,
                            generation=index["generation"],
                            source_revision=existing["source_revision"],
                            verification=existing["verification"],
                            idempotent_replay=True,
                        )
                    else:
                        result.update(
                            self._publish(
                                ctx,
                                root,
                                index,
                                note_id,
                                1,
                                args,
                                prepared_payload=prepared,
                                idempotency_key_sha256=key_sha256,
                                creation_payload_sha256=payload_sha256,
                            )
                        )
                        result["idempotent_replay"] = False
                elif action == "correct":
                    note_id = _text(args, "note_id", 40)
                    current = index["heads"].get(note_id)
                    if current is None:
                        raise KnowledgeError(
                            "NOTE_MISSING", "The note is not in this role/project namespace."
                        )
                    if (
                        type(args.get("expected_revision")) is not int
                        or args["expected_revision"] != current
                    ):
                        raise KnowledgeError(
                            "REVISION_CONFLICT",
                            "Read the current revision before correcting this note.",
                        )
                    _path, old = self._record(root, note_id, current)
                    replacement = args.get("replacement")
                    if not isinstance(replacement, dict) or set(replacement) - {
                        "lesson",
                        "applicability",
                    }:
                        raise KnowledgeError(
                            "ARGUMENT_INVALID", "replacement requires lesson and applicability."
                        )
                    payload = {
                        "situation": old["situation"],
                        **replacement,
                        "outcome": "corrected",
                        "evidence": args.get("evidence", []),
                        "source_nodes": old["source_nodes"],
                    }
                    result.update(
                        self._publish(
                            ctx,
                            root,
                            index,
                            note_id,
                            current + 1,
                            payload,
                            correction=_text(args, "reason", 16000),
                            idempotency_key_sha256=old.get("idempotency_key_sha256"),
                            creation_payload_sha256=old.get("creation_payload_sha256"),
                        )
                    )
                elif action == "reflect":
                    result.update(self._reflect(ctx, root, index))
                else:
                    note_id = _text(args, "note_id", 40)
                    if not _NOTE_ID.fullmatch(note_id):
                        raise KnowledgeError("ARGUMENT_INVALID", "Invalid note identity.")
                    if note_id not in index["heads"]:
                        raise KnowledgeError(
                            "NOTE_MISSING", "This note is not in the selected namespace."
                        )
                    del index["heads"][note_id]
                    index["generation"] += 1
                    atomic_json(root / "index.json", index)
                    (root / "reflection.json").unlink(missing_ok=True)
                    note_root = root / "notes" / note_id
                    if note_root.is_symlink() or note_root.parent.is_symlink():
                        raise KnowledgeError("UNSAFE_PATH", "A note deletion target is redirected.")
                    shutil.rmtree(note_root)
                    result.update(
                        deleted=note_id,
                        generation=index["generation"],
                        warning="Copies already exported or in external backups are not removed.",
                    )
            return result
        index = self._index(root)
        if action == "search":
            query = _text(args, "query", 2000)
            limit = args.get("limit", 5)
            if type(limit) is not int or not 1 <= limit <= 20:
                raise KnowledgeError("ARGUMENT_INVALID", "limit must be between 1 and 20.")
            terms = set(re.findall(r"\w+", query.casefold()))
            candidates = []
            if len(index["heads"]) > 10000:
                raise KnowledgeError(
                    "SCOPE_UNAVAILABLE", "This namespace exceeds the lexical search limit."
                )
            for note_id, revision in index["heads"].items():
                path, record = self._record(root, note_id, revision)
                _verify_note_content(path, record)
                corpus = " ".join(
                    str(record[k]) for k in ("situation", "lesson", "applicability", "source_nodes")
                ).casefold()
                score = sum(min(corpus.count(term), 10) for term in terms if len(term) >= 2)
                if score:
                    candidates.append((score, record["updated_at"], record))
            candidates.sort(key=lambda value: (value[0], value[1]), reverse=True)
            dirty = _is_dirty(ctx)
            matches: list[dict[str, Any]] = []
            budget = args.get("budget_tokens", 2000)
            bounded("", budget)
            for _score, _stamp, record in candidates[:limit]:
                match = {
                    "note_id": record["note_id"],
                    "revision": record["revision"],
                    "situation": record["situation"][:400],
                    "excerpt": record["lesson"][:600],
                    "source_revision": record["source_revision"],
                    "freshness": "same_revision"
                    if record["source_revision"] == ctx.source_revision and not dirty
                    else "revalidate",
                    "verification": record["verification"],
                }
                if len(json.dumps([*matches, match], ensure_ascii=False).encode()) > min(
                    budget * 4, 32768
                ):
                    break
                matches.append(match)
            result.update(
                matches=matches,
                total_matches=len(candidates),
                generation=index["generation"],
                truncated=len(matches) < len(candidates),
                budget_measurement="UTF-8 byte cap; token estimate",
            )
            return result
        if action == "read":
            note_id = _text(args, "note_id", 40)
            revision = index["heads"].get(note_id)
            if revision is None:
                raise KnowledgeError(
                    "NOTE_MISSING", "The note is not in this role/project namespace."
                )
            path, record = self._record(root, note_id, revision)
            raw = _verify_note_content(path, record)
            offset = 0
            cursor = args.get("cursor")
            if cursor:
                if not isinstance(cursor, str) or not re.fullmatch(r"[0-9]+:[0-9]+", cursor):
                    raise KnowledgeError("ARGUMENT_INVALID", "Invalid note cursor.")
                cursor_revision, offset = map(int, cursor.split(":"))
                if cursor_revision != revision or offset > len(raw):
                    raise KnowledgeError(
                        "REVISION_CONFLICT", "The note changed while it was being read."
                    )
            if offset < len(raw) and raw[offset] & 0xC0 == 0x80:
                raise KnowledgeError(
                    "ARGUMENT_INVALID", "A note cursor must begin at a UTF-8 boundary."
                )
            page = raw[offset : offset + 8000]
            content = page.decode("utf-8", errors="ignore")
            consumed = len(content.encode())
            next_cursor = (
                f"{revision}:{offset + consumed}" if offset + consumed < len(raw) else None
            )
            dirty = _is_dirty(ctx)
            result.update(
                note_id=note_id,
                revision=revision,
                content=content,
                next_cursor=next_cursor,
                source_revision=record["source_revision"],
                verification=record["verification"],
                freshness="same_revision"
                if record["source_revision"] == ctx.source_revision and not dirty
                else "revalidate",
                evidence=record["evidence"],
                actor=record["actor"],
            )
            return result
        if action == "export":
            # Administrative caller chooses destination; agent tool never exposes it.
            notes = [
                self._record(root, note_id, revision)[1]
                for note_id, revision in index["heads"].items()
            ]
            result.update(generation=index["generation"], notes=notes)
            return result
        raise KnowledgeError("ARGUMENT_INVALID", "Unknown work-memory action.")

    def _reflect(self, ctx: KnowledgeContext, root: Path, index: dict[str, Any]) -> dict[str, Any]:
        day = int(time.time() // 86400)
        originals = []
        total = 0
        for note_id, revision in index["heads"].items():
            path, record = self._record(root, note_id, revision)
            raw = _verify_note_content(path, record)
            total += len(raw)
            if total > 1_000_000:
                raise KnowledgeError(
                    "SCOPE_UNAVAILABLE",
                    "The current-note generation exceeds the reflection budget.",
                )
            originals.append(raw.decode())
        try:
            cached = load_json(root / "reflection.json")
        except FileNotFoundError:
            cached = {}
        if cached.get("generation") == index["generation"] and cached.get("day") == day:
            return {**cached, "reused": True}
        reflected = self._native("memory_reflect", {"notes": originals})
        content, truncated = bounded(reflected["content"], 3000)
        result = {
            "generation": index["generation"],
            "day": day,
            "content": content,
            "truncated": truncated,
            "count": reflected["count"],
            "warning": "Signal aggregation only. Search/read original notes for complete solutions; revalidate old sources.",
        }
        atomic_json(root / "reflection.json", result)
        return {**result, "reused": False}
