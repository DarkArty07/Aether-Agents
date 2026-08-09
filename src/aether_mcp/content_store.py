"""Project-scoped encrypted rich-content store for M2.5."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, NoReturn, Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAX_PLAINTEXT_BYTES = 16 * 1024 * 1024
_ALLOWED_TYPES = {"model_visible_text", "tool_result", "artifact_excerpt", "worker_message"}
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|password|secret|token)\s*[=:]\s*[^\s;,]+"),
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ContentError(RuntimeError):
    """Stable protected-content failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise ContentError(code, message)


def _project_uuid(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        _fail("TRACE_INTEGRITY_FAILURE", "Project identity is invalid")
    if str(parsed) != value:
        _fail("TRACE_INTEGRITY_FAILURE", "Project identity is not canonical")
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class KeyProvider(Protocol):
    def key_for(self, project_id: str) -> bytes | None: ...


class StaticKeyProvider:
    """In-memory key provider for deterministic local tests; never persisted."""

    def __init__(self, keys: Mapping[str, bytes]) -> None:
        self._keys = dict(keys)

    def set_key(self, project_id: str, key: bytes) -> None:
        _project_uuid(project_id)
        if not isinstance(key, bytes) or len(key) != 32:
            _fail("TRACE_INTEGRITY_FAILURE", "Project key must be 256 bits")
        self._keys[project_id] = key

    def key_for(self, project_id: str) -> bytes | None:
        return self._keys.get(project_id)


@dataclass(frozen=True)
class ContentReference:
    content_ref: str
    content_type: str
    path: Path
    plaintext_bytes: int


class ProtectedContentStore:
    """AES-256-GCM store with redaction-before-write and project-scoped HMAC refs."""

    def __init__(self, root: Path, *, key_provider: KeyProvider, quota_bytes: int) -> None:
        if root.is_symlink() or not isinstance(quota_bytes, int) or quota_bytes < 1:
            _fail("TRACE_INTEGRITY_FAILURE", "Protected-content store configuration is invalid")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        self.root = root.resolve(strict=True)
        self.key_provider = key_provider
        self.quota_bytes = quota_bytes
        self.lock_path = self.root / ".content.lock"
        if not self.lock_path.exists():
            descriptor = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)

    def _key(self, project_id: str) -> bytes:
        _project_uuid(project_id)
        key = self.key_provider.key_for(project_id)
        if key is None:
            _fail("CAPTURE_DISABLED", "Full capture requires an admitted project key")
        if not isinstance(key, bytes) or len(key) != 32:
            _fail("TRACE_INTEGRITY_FAILURE", "Project key provider returned an invalid key")
        return key

    @staticmethod
    def _scope(key: bytes, project_id: str) -> str:
        return hmac.new(key, b"aether-project-scope\0" + project_id.encode(), hashlib.sha256).hexdigest()

    def _project_dir(self, key: bytes, project_id: str) -> Path:
        path = self.root / self._scope(key, project_id)
        if path.is_symlink():
            _fail("TRACE_INTEGRITY_FAILURE", "Project content directory cannot be a symlink")
        path.mkdir(mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
        return path

    @staticmethod
    def _redact(payload: bytes, secret_values: tuple[str, ...]) -> bytes:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            _fail("PRIVACY_POLICY_VIOLATION", "Rich capture must be redaction-compatible UTF-8")
        for secret in secret_values:
            if secret:
                text = text.replace(secret, "[REDACTED]")
        for pattern in _SECRET_PATTERNS:
            if pattern.groups:
                text = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
            else:
                text = pattern.sub("[REDACTED]", text)
        return text.encode("utf-8")

    @staticmethod
    def _ref(key: bytes, content_type: str, plaintext: bytes) -> str:
        return hmac.new(
            key,
            b"aether-content-ref\0" + content_type.encode() + b"\0" + plaintext,
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _aad(project_id: str, content_type: str, content_ref: str) -> bytes:
        return _canonical(
            {
                "content_ref": content_ref,
                "content_type": content_type,
                "project_id": project_id,
                "schema_version": 1,
            }
        )

    @staticmethod
    def _used_bytes(project_dir: Path) -> int:
        total = 0
        for path in project_dir.glob("*.blob"):
            try:
                info = path.stat(follow_symlinks=False)
            except OSError:
                _fail("TRACE_INTEGRITY_FAILURE", "Protected content inventory is unreadable")
            if not stat.S_ISREG(info.st_mode):
                _fail("TRACE_INTEGRITY_FAILURE", "Protected content path is not a regular file")
            total += info.st_size
        return total

    def put(
        self,
        *,
        project_id: str,
        content_type: str,
        payload: bytes,
        capture_policy: str,
        secret_values: tuple[str, ...] = (),
    ) -> ContentReference:
        if capture_policy != "FULL_EPISODE":
            _fail("CAPTURE_DISABLED", "Rich content capture is not enabled")
        if content_type not in _ALLOWED_TYPES:
            _fail("PRIVACY_POLICY_VIOLATION", "Content type is not admitted for model-visible capture")
        if not isinstance(payload, bytes) or len(payload) > _MAX_PLAINTEXT_BYTES:
            _fail("CAPTURE_QUOTA_EXCEEDED", "Rich content exceeds the per-item quota")
        key = self._key(project_id)
        plaintext = self._redact(payload, secret_values)
        content_ref = self._ref(key, content_type, plaintext)
        project_dir = self._project_dir(key, project_id)
        target = project_dir / f"{content_ref}.blob"
        if target.is_symlink():
            _fail("TRACE_INTEGRITY_FAILURE", "Protected content target cannot be a symlink")
        with self.lock_path.open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                if target.exists():
                    return ContentReference(content_ref, content_type, target, len(plaintext))
                nonce = os.urandom(12)
                ciphertext = AESGCM(key).encrypt(nonce, plaintext, self._aad(project_id, content_type, content_ref))
                envelope = _canonical(
                    {
                        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
                        "content_ref": content_ref,
                        "content_type": content_type,
                        "nonce": base64.b64encode(nonce).decode("ascii"),
                        "plaintext_bytes": len(plaintext),
                        "schema_version": 1,
                    }
                )
                if self._used_bytes(project_dir) + len(envelope) > self.quota_bytes:
                    _fail("CAPTURE_QUOTA_EXCEEDED", "Project rich-content quota is exhausted")
                temporary = project_dir / f".{uuid.uuid4()}.tmp"
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(envelope)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, target)
                    directory_fd = os.open(project_dir, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
                finally:
                    if temporary.exists():
                        temporary.unlink()
                return ContentReference(content_ref, content_type, target, len(plaintext))
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def get(self, *, project_id: str, content_ref: str) -> bytes:
        if not isinstance(content_ref, str) or _HEX64.fullmatch(content_ref) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Content reference is invalid")
        key = self._key(project_id)
        project_dir = self._project_dir(key, project_id)
        target = project_dir / f"{content_ref}.blob"
        if target.is_symlink() or not target.is_file():
            _fail("TRACE_INTEGRITY_FAILURE", "Protected content is unavailable for this project")
        try:
            envelope = json.loads(target.read_bytes())
            if set(envelope) != {
                "ciphertext",
                "content_ref",
                "content_type",
                "nonce",
                "plaintext_bytes",
                "schema_version",
            }:
                raise ValueError
            if envelope["schema_version"] != 1 or envelope["content_ref"] != content_ref:
                raise ValueError
            content_type = envelope["content_type"]
            if content_type not in _ALLOWED_TYPES:
                raise ValueError
            nonce = base64.b64decode(envelope["nonce"], validate=True)
            ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, self._aad(project_id, content_type, content_ref))
            if len(nonce) != 12 or len(plaintext) != envelope["plaintext_bytes"]:
                raise ValueError
            if self._ref(key, content_type, plaintext) != content_ref:
                raise ValueError
            return plaintext
        except (OSError, ValueError, TypeError, KeyError, InvalidTag, json.JSONDecodeError):
            _fail("TRACE_INTEGRITY_FAILURE", "Protected content authentication failed")

    def cleanup_orphans(self, *, project_id: str) -> int:
        key = self._key(project_id)
        project_dir = self._project_dir(key, project_id)
        removed = 0
        for path in project_dir.glob(".*.tmp"):
            if path.is_symlink() or not path.is_file():
                _fail("TRACE_INTEGRITY_FAILURE", "Orphan content path is unsafe")
            path.unlink()
            removed += 1
        return removed
