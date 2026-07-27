from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

ARTIFACT_RELATIVE_PATH = ".aether/evidence/{run_id}/{task_id}/{attempt}/result.json"
ARTIFACT_SCHEMA = "AETHER_TASK_RESULT_V1"
RECEIPT_SCHEMA = "AETHER_EVIDENCE_RECEIPT_V1"
_MAX_ARTIFACT_BYTES = 65536
_MAX_DEPTH = 32
_TERMINAL_STATUSES = frozenset({"completed", "error", "cancelled"})
_IDENTITY_FIELDS = (
    "installation_id", "project_id", "run_id", "task_id", "attempt", "contract_id",
    "contract_generation", "revocation_epoch", "message_id", "logical_session", "acp_session_id",
)
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        *_IDENTITY_FIELDS,
        "artifact",
        "verifier",
        "terminal",
        "receipt_payload_digest",
        "receipt_id",
    }
)
_HANDOFF_FIELDS = frozenset({
    "source_run_id", "source_task_id", "source_attempt", "source_receipt_id",
    "source_artifact_generation", "snapshot_relative_path", "snapshot_digest", "canonical_size_bytes",
})
_TOP_LEVEL_FIELDS = frozenset((*_IDENTITY_FIELDS, "schema", "artifact_generation", "result"))
_INTEGER_FIELDS = frozenset({"attempt", "contract_generation", "revocation_epoch", "artifact_generation"})


class EvidenceVerificationError(Exception):
    """A fail-closed, public-safe artifact verification failure."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EvidenceIdentity:
    installation_id: str
    project_id: str
    run_id: str
    task_id: str
    attempt: int
    contract_id: str
    contract_generation: int
    revocation_epoch: int
    message_id: str
    logical_session: str
    acp_session_id: str


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    evidence_identity: EvidenceIdentity
    generation: int
    relative_path: str
    digest: str
    canonical_size_bytes: int
    schema: str
    result: Mapping[str, Any]
    canonical_bytes: bytes


@dataclass(frozen=True, slots=True)
class HandoffSnapshot:
    source_run_id: str
    source_task_id: str
    source_attempt: int
    source_receipt_id: str
    source_artifact_generation: int
    snapshot_relative_path: str
    snapshot_digest: str
    canonical_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in (
            "source_run_id", "source_task_id", "source_attempt", "source_receipt_id",
            "source_artifact_generation", "snapshot_relative_path", "snapshot_digest", "canonical_size_bytes",
        )}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HandoffSnapshot":
        if not isinstance(value, Mapping) or frozenset(value) != _HANDOFF_FIELDS:
            _fail("handoff_invalid")
        try:
            snapshot = cls(*(value[key] for key in (
                "source_run_id", "source_task_id", "source_attempt", "source_receipt_id",
                "source_artifact_generation", "snapshot_relative_path", "snapshot_digest", "canonical_size_bytes",
            )))
            if (
                not all(isinstance(item, str) and item for item in (snapshot.source_run_id, snapshot.source_task_id, snapshot.source_receipt_id, snapshot.snapshot_relative_path, snapshot.snapshot_digest))
                or isinstance(snapshot.source_attempt, bool) or snapshot.source_attempt < 1
                or snapshot.source_artifact_generation != 1
                or not _digest_matches(snapshot.snapshot_digest, "sha256:")
                or isinstance(snapshot.canonical_size_bytes, bool) or not isinstance(snapshot.canonical_size_bytes, int)
                or not 0 < snapshot.canonical_size_bytes <= _MAX_ARTIFACT_BYTES
                or snapshot.snapshot_relative_path != str(Path(snapshot.snapshot_relative_path))
                or not snapshot.snapshot_relative_path.startswith(f".aether/evidence/{snapshot.source_run_id}/handoffs/{snapshot.source_task_id}/{snapshot.source_receipt_id}/")
                or not snapshot.snapshot_relative_path.endswith(f"{snapshot.snapshot_digest[7:]}.json")
            ):
                _fail("handoff_invalid")
            for component in (snapshot.source_run_id, snapshot.source_task_id, snapshot.source_receipt_id):
                _safe_component(component)
            return snapshot
        except (KeyError, TypeError, AttributeError):
            _fail("handoff_invalid")


@dataclass(frozen=True, slots=True)
class EvidenceReceipt:
    schema: str
    identity: str
    version: int
    algorithm: str
    artifact: VerifiedArtifact
    terminal_status: str
    receipt_payload_digest: str
    receipt_id: str
    canonical_payload: bytes
    handoff: HandoffSnapshot | None = None

    def event_payload(self) -> dict[str, Any]:
        """Return a fresh, exact ledger payload including verifier-owned identifiers."""
        payload = json.loads(self.canonical_payload)
        payload["receipt_payload_digest"] = self.receipt_payload_digest
        payload["receipt_id"] = self.receipt_id
        return payload


def _fail(code: str) -> NoReturn:
    raise EvidenceVerificationError(code)


def _reject_constants(value: str) -> Any:
    _fail("artifact_invalid")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("artifact_invalid")
        result[key] = value
    return result


def _depth(value: Any, current: int = 1) -> int:
    if isinstance(value, dict):
        return max([current, *(_depth(item, current + 1) for item in value.values())])
    if isinstance(value, list):
        return max([current, *(_depth(item, current + 1) for item in value)])
    return current


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        _fail("artifact_invalid")


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _safe_component(value: str | int) -> str:
    text = str(value)
    if not text or text in {".", ".."} or "/" in text or "\\" in text or os.path.isabs(text):
        _fail("artifact_escape")
    return text


def _artifact_path(project_root: Path, evidence_identity: EvidenceIdentity) -> tuple[Path, Path]:
    try:
        root = project_root.resolve(strict=True)
    except (FileNotFoundError, OSError):
        _fail("artifact_missing")
    relative = Path(ARTIFACT_RELATIVE_PATH.format(
        run_id=_safe_component(evidence_identity.run_id),
        task_id=_safe_component(evidence_identity.task_id),
        attempt=_safe_component(evidence_identity.attempt),
    ))
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        _fail("artifact_missing")
    except OSError:
        _fail("artifact_invalid")
    if not candidate.is_file() or candidate.is_symlink():
        _fail("artifact_escape" if candidate.is_symlink() else "artifact_invalid")
    try:
        resolved.relative_to(root)
    except ValueError:
        _fail("artifact_escape")
    if resolved != candidate:
        _fail("artifact_escape")
    return root, candidate


def _read_artifact(root: Path, path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        _fail("artifact_missing")
    except OSError:
        _fail("artifact_invalid")
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _fail("artifact_invalid")
        try:
            opened_path = Path(f"/proc/self/fd/{descriptor}").resolve(strict=True)
            opened_path.relative_to(root)
        except (FileNotFoundError, OSError, ValueError):
            _fail("artifact_escape")
        if opened_path != path:
            _fail("artifact_escape")
        chunks: list[bytes] = []
        total = 0
        while total <= _MAX_ARTIFACT_BYTES:
            chunk = os.read(descriptor, min(65536, _MAX_ARTIFACT_BYTES - total + 1))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total > _MAX_ARTIFACT_BYTES:
            _fail("artifact_invalid")
        return b"".join(chunks)
    except OSError:
        _fail("artifact_invalid")
    finally:
        os.close(descriptor)


def verify_artifact(project_root: Path | str, evidence_identity: EvidenceIdentity) -> VerifiedArtifact:
    """Read and verify the kernel-derived task result artifact."""
    root, path = _artifact_path(Path(project_root), evidence_identity)
    raw = _read_artifact(root, path)
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constants)
        if not isinstance(document, dict) or _depth(document) > _MAX_DEPTH:
            _fail("artifact_invalid")
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        _fail("artifact_invalid")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("artifact_invalid")
    if document["schema"] != ARTIFACT_SCHEMA:
        _fail("artifact_invalid")
    for field in _INTEGER_FIELDS:
        if isinstance(document[field], bool) or not isinstance(document[field], int):
            _fail("artifact_invalid")
    if document["artifact_generation"] != 1:
        _fail("stale_artifact")
    for field in _IDENTITY_FIELDS:
        if document[field] != getattr(evidence_identity, field):
            _fail("artifact_mismatch")
    if not isinstance(document["result"], dict):
        _fail("artifact_invalid")
    canonical = _canonical(document)
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return VerifiedArtifact(
        evidence_identity=evidence_identity,
        generation=1,
        relative_path=str(path.relative_to(Path(project_root).resolve(strict=True))),
        digest=digest,
        canonical_size_bytes=len(canonical),
        schema=ARTIFACT_SCHEMA,
        result=_freeze(document["result"]),
        canonical_bytes=canonical,
    )


def materialize_captured_result(
    project_root: Path | str,
    evidence_identity: EvidenceIdentity,
    result: Mapping[str, Any],
) -> VerifiedArtifact:
    """Atomically persist a read-only worker's structured ACP result.

    The worker supplies only the bounded ``result`` mapping. Kernel-owned
    identity fields and the destination path are derived from authenticated
    dispatch state and cannot be selected by the worker.
    """
    if not isinstance(result, Mapping):
        _fail("artifact_invalid")
    document = {
        "schema": ARTIFACT_SCHEMA,
        **{field: getattr(evidence_identity, field) for field in _IDENTITY_FIELDS},
        "artifact_generation": 1,
        "result": _plain(result),
    }
    if _depth(document) > _MAX_DEPTH:
        _fail("artifact_invalid")
    raw = _canonical(document)
    if len(raw) > _MAX_ARTIFACT_BYTES:
        _fail("artifact_invalid")

    try:
        root = Path(project_root).resolve(strict=True)
    except (FileNotFoundError, OSError):
        _fail("artifact_missing")
    relative = Path(
        ARTIFACT_RELATIVE_PATH.format(
            run_id=_safe_component(evidence_identity.run_id),
            task_id=_safe_component(evidence_identity.task_id),
            attempt=_safe_component(evidence_identity.attempt),
        )
    )
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.resolve(strict=True).relative_to(root)
    except (FileNotFoundError, OSError, ValueError):
        _fail("artifact_escape")
    if os.path.lexists(path):
        existing = verify_artifact(root, evidence_identity)
        if existing.canonical_bytes != raw:
            _fail("stale_artifact")
        return existing

    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            existing = verify_artifact(root, evidence_identity)
            if existing.canonical_bytes != raw:
                _fail("stale_artifact")
            return existing
    except EvidenceVerificationError:
        raise
    except OSError:
        _fail("artifact_invalid")
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return verify_artifact(root, evidence_identity)


def _snapshot_parent_fd(root: Path, relative: Path, *, create: bool) -> tuple[int, str]:
    """Traverse below root with directory FDs so no parent symlink is followed."""
    if relative.is_absolute() or not relative.name or any(part in {"", ".", ".."} for part in relative.parts):
        _fail("handoff_escape")
    descriptor: int | None = None
    try:
        root = root.resolve(strict=True)
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        for component in relative.parent.parts:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor, relative.name
    except (FileNotFoundError, NotADirectoryError, OSError, ValueError):
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        _fail("handoff_publish_failed" if create else "handoff_missing")


def _snapshot_read(root: Path, snapshot: HandoffSnapshot) -> bytes:
    parent_fd, filename = _snapshot_parent_fd(root, Path(snapshot.snapshot_relative_path), create=False)
    try:
        descriptor = os.open(filename, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
    except (FileNotFoundError, OSError, ValueError):
        os.close(parent_fd)
        _fail("handoff_missing")
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _fail("handoff_invalid")
        chunks = []
        remaining = _MAX_ARTIFACT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(descriptor)
        os.close(parent_fd)
    if len(data) != snapshot.canonical_size_bytes:
        _fail("handoff_size_mismatch")
    if "sha256:" + hashlib.sha256(data).hexdigest() != snapshot.snapshot_digest:
        _fail("handoff_digest_mismatch")
    return data


def create_handoff_snapshot(project_root: Path | str, identity: EvidenceIdentity, receipt_id: str, artifact: VerifiedArtifact) -> HandoffSnapshot:
    """Exclusively publish the canonical bytes accepted by the verifier."""
    if artifact.evidence_identity != identity or not isinstance(receipt_id, str):
        _fail("handoff_invalid")
    root = Path(project_root).resolve(strict=True)
    relative = Path(".aether/evidence") / _safe_component(identity.run_id) / "handoffs" / _safe_component(identity.task_id) / _safe_component(receipt_id) / (artifact.digest[7:] + ".json")
    parent_fd, filename = _snapshot_parent_fd(root, relative, create=True)
    try:
        try:
            descriptor = os.open(
                filename,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o444,
                dir_fd=parent_fd,
            )
        except FileExistsError:
            descriptor = None
        except (OSError, ValueError):
            _fail("handoff_publish_failed")
        if descriptor is not None:
            try:
                remaining = memoryview(artifact.canonical_bytes)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written <= 0:
                        _fail("handoff_publish_failed")
                    remaining = remaining[written:]
                os.fchmod(descriptor, 0o444)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    snapshot = HandoffSnapshot(identity.run_id, identity.task_id, identity.attempt, receipt_id, artifact.generation, str(relative), artifact.digest, len(artifact.canonical_bytes))
    if _snapshot_read(root, snapshot) != artifact.canonical_bytes:
        _fail("handoff_conflict")
    return snapshot


def validate_handoff_snapshot(project_root: Path | str, snapshot: HandoffSnapshot) -> None:
    if not isinstance(snapshot, HandoffSnapshot):
        _fail("handoff_invalid")
    _snapshot_read(Path(project_root), snapshot)


def build_evidence_receipt(identity: EvidenceIdentity, artifact: VerifiedArtifact, terminal_status: str, handoff: HandoffSnapshot | None = None) -> EvidenceReceipt:
    """Construct a deterministic receipt; verifier metadata is code-owned."""
    if not isinstance(terminal_status, str) or terminal_status not in _TERMINAL_STATUSES:
        _fail("invalid_terminal_status")
    if artifact.evidence_identity != identity:
        _fail("artifact_mismatch")
    payload = {
        "schema": RECEIPT_SCHEMA,
        **{field: getattr(identity, field) for field in _IDENTITY_FIELDS},
        "artifact": {"generation": artifact.generation, "relative_path": artifact.relative_path, "digest": artifact.digest, "canonical_size_bytes": artifact.canonical_size_bytes, "schema": artifact.schema},
        "verifier": {"identity": "kernel.artifact-verifier", "version": 1, "algorithm": "sha256-canonical-json"},
        "terminal": {"technical_status": terminal_status},
    }
    if handoff is not None:
        if (handoff.source_run_id, handoff.source_task_id, handoff.source_attempt, handoff.source_artifact_generation) != (identity.run_id, identity.task_id, identity.attempt, artifact.generation):
            _fail("handoff_invalid")
        payload["handoff"] = handoff.to_dict()
    canonical = _canonical(payload)
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    id_canonical = _canonical({key: value for key, value in payload.items() if key != "handoff"})
    receipt_id = "receipt:" + hashlib.sha256(b"AETHER_EVIDENCE_RECEIPT_V1\0" + id_canonical).hexdigest()
    return EvidenceReceipt(RECEIPT_SCHEMA, "kernel.artifact-verifier", 1, "sha256-canonical-json", artifact, terminal_status, digest, receipt_id, canonical, handoff)


def _digest_matches(value: Any, prefix: str) -> bool:
    if not isinstance(value, str) or not value.startswith(prefix) or len(value) != len(prefix) + 64:
        return False
    try:
        suffix = value[len(prefix) :]
        int(suffix, 16)
    except ValueError:
        return False
    return suffix == suffix.lower()


def validate_evidence_receipt_payload(payload: Any) -> None:
    """Fail closed unless a ledger payload is an exact verifier-owned receipt."""
    if not isinstance(payload, dict) or frozenset(payload) not in {_RECEIPT_FIELDS, _RECEIPT_FIELDS | {"handoff"}}:
        _fail("receipt_invalid")
    if payload.get("schema") != RECEIPT_SCHEMA:
        _fail("receipt_invalid")
    for field in _IDENTITY_FIELDS:
        value = payload.get(field)
        if field in {"attempt", "contract_generation", "revocation_epoch"}:
            if isinstance(value, bool) or not isinstance(value, int) or value < (1 if field == "attempt" else 0):
                _fail("receipt_invalid")
        elif not isinstance(value, str) or not value:
            _fail("receipt_invalid")
    try:
        for field in ("run_id", "task_id"):
            _safe_component(payload[field])
        expected_path = ARTIFACT_RELATIVE_PATH.format(
            run_id=payload["run_id"], task_id=payload["task_id"], attempt=payload["attempt"]
        )
    except (EvidenceVerificationError, KeyError):
        _fail("receipt_invalid")
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict) or frozenset(artifact) != {
        "generation",
        "relative_path",
        "digest",
        "canonical_size_bytes",
        "schema",
    }:
        _fail("receipt_invalid")
    size = artifact.get("canonical_size_bytes")
    if (
        isinstance(artifact.get("generation"), bool)
        or artifact.get("generation") != 1
        or artifact.get("relative_path") != expected_path
        or artifact.get("schema") != ARTIFACT_SCHEMA
        or not _digest_matches(artifact.get("digest"), "sha256:")
        or isinstance(size, bool)
        or not isinstance(size, int)
        or not 0 < size <= _MAX_ARTIFACT_BYTES
    ):
        _fail("receipt_invalid")
    verifier = payload.get("verifier")
    if not isinstance(verifier, dict) or verifier != {
        "identity": "kernel.artifact-verifier",
        "version": 1,
        "algorithm": "sha256-canonical-json",
    } or isinstance(verifier["version"], bool):
        _fail("receipt_invalid")
    terminal = payload.get("terminal")
    if not isinstance(terminal, dict) or frozenset(terminal) != {"technical_status"}:
        _fail("receipt_invalid")
    if terminal.get("technical_status") not in _TERMINAL_STATUSES:
        _fail("receipt_invalid")
    if not _digest_matches(payload.get("receipt_payload_digest"), "sha256:"):
        _fail("receipt_invalid")
    if not _digest_matches(payload.get("receipt_id"), "receipt:"):
        _fail("receipt_invalid")
    handoff = payload.get("handoff")
    if handoff is not None:
        try:
            HandoffSnapshot.from_dict(handoff)
            if (
                handoff.get("source_receipt_id") != payload.get("receipt_id")
                or handoff.get("source_run_id") != payload.get("run_id")
                or handoff.get("source_task_id") != payload.get("task_id")
                or handoff.get("source_attempt") != payload.get("attempt")
                or handoff.get("source_artifact_generation") != artifact.get("generation")
                or handoff.get("snapshot_digest") != artifact.get("digest")
                or handoff.get("canonical_size_bytes") != artifact.get("canonical_size_bytes")
            ):
                _fail("receipt_invalid")
        except EvidenceVerificationError:
            _fail("receipt_invalid")
    base = {key: value for key, value in payload.items() if key not in {"receipt_id", "receipt_payload_digest"}}
    canonical = _canonical(base)
    expected_digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    id_base = {key: value for key, value in base.items() if key != "handoff"}
    expected_id = "receipt:" + hashlib.sha256(b"AETHER_EVIDENCE_RECEIPT_V1\0" + _canonical(id_base)).hexdigest()
    if payload["receipt_payload_digest"] != expected_digest or payload["receipt_id"] != expected_id:
        _fail("receipt_invalid")
