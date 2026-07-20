"""Isolated R4 workload identity: bindings, issuer credentials, and holder proof.

This module is default-off and isolated from R1-R3 wiring. The fixed HMAC-SHA256
primitives here are structural, test-scope proof-of-possession only. They do not
constitute production key custody, runtime attestation, or asymmetric workload
identity, and must not be treated as such outside isolated tests.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from .protocol import ValidationError

ENCODING_VERSION = 1
ALGORITHM = "HMAC-SHA256"
_MAX_INT = (1 << 63) - 1
_MIN_KEY_BYTES = 16
_MAX_KEY_BYTES = 4096
MAX_CREDENTIAL_TTL = 86_400
MAX_PROOF_SUBJECT_BYTES = 65_536
MAX_PROOF_SUBJECT_DEPTH = 16
MAX_PROOF_SUBJECT_ITEMS = 2_048

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class KeyPurpose(StrEnum):
    ISSUER = "issuer"
    HOLDER = "holder"


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _int(value: Any, label: str, *, minimum: int = 0, maximum: int = _MAX_INT) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or value > maximum:
        raise ValidationError(f"invalid {label}")
    return value


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError("invalid canonical payload") from exc


@dataclass(frozen=True, slots=True)
class WorkloadBinding:
    installation_id: str
    project_id: str
    role: str
    profile: str
    session_id: str
    runtime_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "installation_id", _id(self.installation_id, "installation id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        object.__setattr__(self, "role", _id(self.role, "role"))
        object.__setattr__(self, "profile", _id(self.profile, "profile"))
        object.__setattr__(self, "session_id", _id(self.session_id, "session id"))
        object.__setattr__(self, "runtime_id", _id(self.runtime_id, "runtime id"))

    def to_dict(self) -> dict[str, str]:
        return {
            "installation_id": self.installation_id,
            "project_id": self.project_id,
            "role": self.role,
            "profile": self.profile,
            "session_id": self.session_id,
            "runtime_id": self.runtime_id,
        }

    @classmethod
    def from_dict(cls, value: Any) -> WorkloadBinding:
        _fields(value, {"installation_id", "project_id", "role", "profile", "session_id", "runtime_id"}, "workload binding")
        return cls(**value)


def _credential_signing_claims(
    binding: WorkloadBinding,
    issuer: str,
    audience: str,
    key_id: str,
    identity_id: str,
    holder_key_id: str,
    revocation_epoch: int,
    not_before: int,
    expires_at: int,
) -> dict[str, Any]:
    return {
        "encoding_version": ENCODING_VERSION,
        "binding": binding.to_dict(),
        "issuer": issuer,
        "audience": audience,
        "key_id": key_id,
        "identity_id": identity_id,
        "holder_key_id": holder_key_id,
        "revocation_epoch": revocation_epoch,
        "not_before": not_before,
        "expires_at": expires_at,
    }


@dataclass(frozen=True, slots=True)
class IdentityCredential:
    binding: WorkloadBinding
    issuer: str
    audience: str
    key_id: str
    identity_id: str
    holder_key_id: str
    revocation_epoch: int
    not_before: int
    expires_at: int
    signature: str
    encoding_version: int = ENCODING_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.binding, WorkloadBinding):
            raise ValidationError("invalid credential binding")
        object.__setattr__(self, "issuer", _id(self.issuer, "issuer"))
        object.__setattr__(self, "audience", _id(self.audience, "audience"))
        object.__setattr__(self, "key_id", _id(self.key_id, "key id"))
        object.__setattr__(self, "identity_id", _id(self.identity_id, "identity id"))
        object.__setattr__(self, "holder_key_id", _id(self.holder_key_id, "holder key id"))
        object.__setattr__(self, "revocation_epoch", _int(self.revocation_epoch, "revocation epoch"))
        object.__setattr__(self, "not_before", _int(self.not_before, "not_before"))
        object.__setattr__(self, "expires_at", _int(self.expires_at, "expires_at"))
        if self.expires_at <= self.not_before:
            raise ValidationError("credential expires_at must be after not_before")
        if self.expires_at - self.not_before > MAX_CREDENTIAL_TTL:
            raise ValidationError("credential validity exceeds maximum TTL")
        object.__setattr__(self, "signature", _hex64(self.signature, "credential signature"))
        if self.encoding_version != ENCODING_VERSION:
            raise ValidationError("unsupported credential encoding version")

    def signing_claims(self) -> dict[str, Any]:
        return _credential_signing_claims(
            self.binding, self.issuer, self.audience, self.key_id, self.identity_id,
            self.holder_key_id, self.revocation_epoch, self.not_before, self.expires_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding": self.binding.to_dict(),
            "issuer": self.issuer,
            "audience": self.audience,
            "key_id": self.key_id,
            "identity_id": self.identity_id,
            "holder_key_id": self.holder_key_id,
            "revocation_epoch": self.revocation_epoch,
            "not_before": self.not_before,
            "expires_at": self.expires_at,
            "signature": self.signature,
            "encoding_version": self.encoding_version,
        }

    @classmethod
    def from_dict(cls, value: Any) -> IdentityCredential:
        fields = {
            "binding", "issuer", "audience", "key_id", "identity_id", "holder_key_id",
            "revocation_epoch", "not_before", "expires_at", "signature", "encoding_version",
        }
        _fields(value, fields, "identity credential")
        return cls(
            WorkloadBinding.from_dict(value["binding"]), value["issuer"], value["audience"], value["key_id"],
            value["identity_id"], value["holder_key_id"], value["revocation_epoch"], value["not_before"],
            value["expires_at"], value["signature"], value["encoding_version"],
        )


@dataclass(frozen=True, slots=True)
class HolderProof:
    holder_key_id: str
    challenge: str
    request_digest: str
    signature: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "holder_key_id", _id(self.holder_key_id, "holder key id"))
        object.__setattr__(self, "challenge", _hex64(self.challenge, "challenge"))
        object.__setattr__(self, "request_digest", _hex64(self.request_digest, "request digest"))
        object.__setattr__(self, "signature", _hex64(self.signature, "proof signature"))

    def to_dict(self) -> dict[str, str]:
        return {
            "holder_key_id": self.holder_key_id,
            "challenge": self.challenge,
            "request_digest": self.request_digest,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, value: Any) -> HolderProof:
        _fields(value, {"holder_key_id", "challenge", "request_digest", "signature"}, "holder proof")
        return cls(**value)


def _validate_proof_subject(
    value: Any,
    *,
    depth: int = 0,
    seen: set[int] | None = None,
    count: list[int] | None = None,
) -> None:
    if depth > MAX_PROOF_SUBJECT_DEPTH:
        raise ValidationError("proof subject exceeds maximum depth")
    if seen is None:
        seen = set()
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > MAX_PROOF_SUBJECT_ITEMS:
        raise ValidationError("proof subject exceeds maximum items")
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str):
            if len(value) > MAX_PROOF_SUBJECT_BYTES or len(value.encode("utf-8")) > MAX_PROOF_SUBJECT_BYTES:
                raise ValidationError("proof subject string exceeds maximum bytes")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        _int(value, "proof subject integer")
        return
    if not isinstance(value, (dict, list)):
        raise ValidationError("proof subject contains unsupported value")
    identity = id(value)
    if identity in seen:
        raise ValidationError("proof subject contains a cycle")
    seen.add(identity)
    try:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str) or len(key.encode("utf-8")) > 128:
                    raise ValidationError("invalid proof subject key")
                _validate_proof_subject(child, depth=depth + 1, seen=seen, count=count)
        else:
            for child in value:
                _validate_proof_subject(child, depth=depth + 1, seen=seen, count=count)
    finally:
        seen.remove(identity)


def _proof_transcript(challenge: str, subject_canonical: Any, request_digest: str) -> bytes:
    _validate_proof_subject(subject_canonical)
    subject_bytes = _canonical_json(subject_canonical)
    if len(subject_bytes) > MAX_PROOF_SUBJECT_BYTES:
        raise ValidationError("proof subject exceeds maximum bytes")
    return _canonical_json({
        "encoding_version": ENCODING_VERSION,
        "challenge": challenge,
        "subject": subject_canonical,
        "request_digest": request_digest,
    })


class _KeyRecord:
    __slots__ = ("secret", "purpose", "active", "expires_at")

    def __init__(self, secret: bytes, purpose: KeyPurpose, expires_at: int) -> None:
        self.secret = secret
        self.purpose = purpose
        self.active = True
        self.expires_at = expires_at


class _IdentityRecord:
    __slots__ = ("active", "revocation_epoch", "expires_at")

    def __init__(self, expires_at: int) -> None:
        self.active = True
        self.revocation_epoch = 0
        self.expires_at = expires_at


class IdentityRegistry:
    """Deterministic-clock registry of issuer/holder keys and identity revocation state.

    Every lookup fails closed (returns None) for unknown, inactive, revoked, or
    TTL-expired records; callers must never treat an absent record as authorized.
    """

    def __init__(self, *, clock: Callable[[], int]):
        self._clock = clock
        self._keys: dict[str, _KeyRecord] = {}
        self._identities: dict[str, _IdentityRecord] = {}

    def register_key(self, key_id: str, secret: bytes, *, purpose: KeyPurpose, ttl: int) -> None:
        key_id = _id(key_id, "key id")
        if not isinstance(secret, (bytes, bytearray)) or not (_MIN_KEY_BYTES <= len(secret) <= _MAX_KEY_BYTES):
            raise ValidationError("invalid key material")
        if not isinstance(purpose, KeyPurpose):
            raise ValidationError("invalid key purpose")
        now = _int(self._clock(), "clock")
        ttl = _int(ttl, "key ttl", minimum=1, maximum=_MAX_INT - now)
        self._keys[key_id] = _KeyRecord(bytes(secret), purpose, now + ttl)

    def revoke_key(self, key_id: str) -> None:
        record = self._keys.get(_id(key_id, "key id"))
        if record is None:
            raise ValidationError("unknown key")
        record.active = False

    def rotate_key(self, old_key_id: str, new_key_id: str, secret: bytes, *, ttl: int) -> None:
        old_key_id = _id(old_key_id, "key id")
        record = self._keys.get(old_key_id)
        if record is None:
            raise ValidationError("unknown key")
        purpose = record.purpose
        self.revoke_key(old_key_id)
        self.register_key(new_key_id, secret, purpose=purpose, ttl=ttl)

    def _active_key(self, key_id: Any, purpose: KeyPurpose) -> bytes | None:
        if not isinstance(key_id, str):
            return None
        record = self._keys.get(key_id)
        if record is None or not record.active or record.purpose is not purpose:
            return None
        if record.expires_at <= self._clock():
            return None
        return record.secret

    def is_key_active(self, key_id: Any, *, purpose: KeyPurpose) -> bool:
        """Return key status without exposing key material."""
        if not isinstance(purpose, KeyPurpose):
            return False
        return self._active_key(key_id, purpose) is not None

    def register_identity(self, identity_id: str, *, ttl: int) -> None:
        identity_id = _id(identity_id, "identity id")
        now = _int(self._clock(), "clock")
        ttl = _int(ttl, "identity ttl", minimum=1, maximum=_MAX_INT - now)
        self._identities[identity_id] = _IdentityRecord(now + ttl)

    def revoke_identity(self, identity_id: str) -> None:
        record = self._identities.get(_id(identity_id, "identity id"))
        if record is None:
            raise ValidationError("unknown identity")
        record.active = False

    def advance_identity_epoch(self, identity_id: str) -> None:
        record = self._identities.get(_id(identity_id, "identity id"))
        if record is None:
            raise ValidationError("unknown identity")
        record.revocation_epoch += 1

    def active_identity_epoch(self, identity_id: Any) -> int | None:
        if not isinstance(identity_id, str):
            return None
        record = self._identities.get(identity_id)
        if record is None or not record.active:
            return None
        if record.expires_at <= self._clock():
            return None
        return record.revocation_epoch


def issue_identity_credential(
    registry: IdentityRegistry,
    binding: WorkloadBinding,
    *,
    issuer: str,
    audience: str,
    key_id: str,
    identity_id: str,
    holder_key_id: str,
    not_before: int,
    expires_at: int,
) -> IdentityCredential:
    if not isinstance(registry, IdentityRegistry) or not isinstance(binding, WorkloadBinding):
        raise ValidationError("invalid credential issuance input")
    secret = registry._active_key(key_id, KeyPurpose.ISSUER)
    if secret is None:
        raise ValidationError("unknown or inactive issuer key")
    if registry._active_key(holder_key_id, KeyPurpose.HOLDER) is None:
        raise ValidationError("unknown or inactive holder key")
    epoch = registry.active_identity_epoch(identity_id)
    if epoch is None:
        raise ValidationError("unknown or inactive identity")
    issuer = _id(issuer, "issuer")
    claims = _credential_signing_claims(binding, issuer, audience, key_id, identity_id, holder_key_id, epoch, not_before, expires_at)
    signature = hmac.new(secret, _canonical_json(claims), hashlib.sha256).hexdigest()
    return IdentityCredential(binding, issuer, audience, key_id, identity_id, holder_key_id, epoch, not_before, expires_at, signature)


def verify_identity_credential(registry: IdentityRegistry, credential: IdentityCredential, *, audience: str, now: int) -> bool:
    """Verify issuer signature, validity window, and live identity/key state. Never raises."""
    if not isinstance(registry, IdentityRegistry) or not isinstance(credential, IdentityCredential):
        return False
    try:
        audience = _id(audience, "audience")
        now = _int(now, "now")
    except ValidationError:
        return False
    if credential.audience != audience:
        return False
    if not (credential.not_before <= now < credential.expires_at):
        return False
    secret = registry._active_key(credential.key_id, KeyPurpose.ISSUER)
    if secret is None:
        return False
    if registry._active_key(credential.holder_key_id, KeyPurpose.HOLDER) is None:
        return False
    epoch = registry.active_identity_epoch(credential.identity_id)
    if epoch is None or epoch != credential.revocation_epoch:
        return False
    expected = hmac.new(secret, _canonical_json(credential.signing_claims()), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, credential.signature)


def create_holder_proof(
    registry: IdentityRegistry, holder_key_id: str, *, challenge: str, subject_canonical: Any, request_digest: str,
) -> HolderProof:
    if not isinstance(registry, IdentityRegistry):
        raise ValidationError("invalid registry")
    secret = registry._active_key(holder_key_id, KeyPurpose.HOLDER)
    if secret is None:
        raise ValidationError("unknown or inactive holder key")
    challenge = _hex64(challenge, "challenge")
    request_digest = _hex64(request_digest, "request digest")
    signature = hmac.new(secret, _proof_transcript(challenge, subject_canonical, request_digest), hashlib.sha256).hexdigest()
    return HolderProof(holder_key_id, challenge, request_digest, signature)


def verify_holder_proof(
    registry: IdentityRegistry,
    proof: HolderProof,
    *,
    expected_holder_key_id: str,
    subject_canonical: Any,
    request_digest: str,
) -> bool:
    """Verify a holder proof transcript. Never raises; fails closed on any mismatch."""
    if not isinstance(registry, IdentityRegistry) or not isinstance(proof, HolderProof):
        return False
    if proof.holder_key_id != expected_holder_key_id or proof.request_digest != request_digest:
        return False
    secret = registry._active_key(proof.holder_key_id, KeyPurpose.HOLDER)
    if secret is None:
        return False
    try:
        transcript = _proof_transcript(proof.challenge, subject_canonical, request_digest)
    except (ValidationError, TypeError, ValueError, RecursionError, MemoryError):
        return False
    expected = hmac.new(secret, transcript, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, proof.signature)


__all__ = [
    "ALGORITHM",
    "ENCODING_VERSION",
    "HolderProof",
    "IdentityCredential",
    "IdentityRegistry",
    "KeyPurpose",
    "MAX_CREDENTIAL_TTL",
    "MAX_PROOF_SUBJECT_BYTES",
    "MAX_PROOF_SUBJECT_DEPTH",
    "MAX_PROOF_SUBJECT_ITEMS",
    "ValidationError",
    "WorkloadBinding",
    "create_holder_proof",
    "issue_identity_credential",
    "verify_holder_proof",
    "verify_identity_credential",
]
