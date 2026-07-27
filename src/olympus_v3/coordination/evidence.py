from __future__ import annotations

import hashlib
import json
import os
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
    "installation_id", "project_id", "run_id", "task_id", "attempt",
    "contract_id", "contract_generation", "revocation_epoch", "message_id",
    "logical_session", "acp_session_id",
)
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


def verify_artifact(project_root: Path | str, evidence_identity: EvidenceIdentity) -> VerifiedArtifact:
    """Read and verify the kernel-derived task result artifact."""
    _, path = _artifact_path(Path(project_root), evidence_identity)
    try:
        raw = path.read_bytes()
    except (OSError, FileNotFoundError):
        _fail("artifact_missing")
    if len(raw) > _MAX_ARTIFACT_BYTES:
        _fail("artifact_invalid")
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
    )


def build_evidence_receipt(identity: EvidenceIdentity, artifact: VerifiedArtifact, terminal_status: str) -> EvidenceReceipt:
    """Construct a deterministic receipt; verifier metadata is code-owned."""
    if not isinstance(terminal_status, str) or terminal_status not in _TERMINAL_STATUSES:
        _fail("invalid_terminal_status")
    if artifact.evidence_identity != identity:
        _fail("artifact_mismatch")
    payload = {
        "schema": RECEIPT_SCHEMA,
        "verifier": {"identity": "kernel.artifact-verifier", "version": 1, "algorithm": "sha256-canonical-json"},
        "artifact": {"generation": artifact.generation, "relative_path": artifact.relative_path,
                     "digest": artifact.digest, "canonical_size_bytes": artifact.canonical_size_bytes,
                     "schema": artifact.schema, "result": _plain(artifact.result)},
        "terminal_status": terminal_status,
        "evidence_identity": {field: getattr(identity, field) for field in _IDENTITY_FIELDS},
    }
    canonical = _canonical(payload)
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    receipt_id = "sha256:" + hashlib.sha256(b"receipt:" + canonical).hexdigest()
    return EvidenceReceipt(RECEIPT_SCHEMA, "kernel.artifact-verifier", 1, "sha256-canonical-json", artifact, terminal_status, digest, receipt_id, canonical)
