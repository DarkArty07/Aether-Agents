"""Isolated R4 capability claims and the single canonical authorization boundary.

Default-off and isolated from R1-R3 dispatch. `authorize` performs no side effects on
any denied path and drives no external runtime state; wiring a dispatcher to its
result is out of scope for R4 (deferred to R5). HMAC-SHA256 here is the same
structural, test-scope proof-of-possession described in `identity.py` -- not
production key custody or attestation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .contracts import ContractState, ExecutionContract, assert_current_generation, is_role_permitted
from .identity import (
    ENCODING_VERSION,
    HolderProof,
    IdentityCredential,
    IdentityRegistry,
    KeyPurpose,
    ValidationError,
    WorkloadBinding,
    verify_holder_proof,
    verify_identity_credential,
)
from .protocol import Principal

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_TARGET = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,255}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_INT = (1 << 63) - 1
_MAX_PERMISSIONS = 32
MAX_CAPABILITY_TTL = 86_400


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _target(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _TARGET.fullmatch(value):
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


def _tokens(values: Any, label: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(values, tuple) or (not allow_empty and not values) or len(values) > _MAX_PERMISSIONS:
        raise ValidationError(f"invalid {label}")
    result = tuple(_token(value, label) for value in values)
    if len(set(result)) != len(result):
        raise ValidationError(f"duplicate {label}")
    return result


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError("invalid canonical payload") from exc


@dataclass(frozen=True, slots=True)
class CapabilityClaim:
    capability_id: str
    identity_id: str
    installation_id: str
    project_id: str
    contract_id: str
    generation: int
    task_id: str
    audience: str
    target: str
    permissions: tuple[str, ...]
    effect_classes: tuple[str, ...]
    fence_epoch: int
    revocation_epoch: int
    not_before: int
    expires_at: int
    nonce: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability_id", _id(self.capability_id, "capability id"))
        object.__setattr__(self, "identity_id", _id(self.identity_id, "identity id"))
        object.__setattr__(self, "installation_id", _id(self.installation_id, "installation id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        object.__setattr__(self, "contract_id", _id(self.contract_id, "contract id"))
        object.__setattr__(self, "generation", _int(self.generation, "generation"))
        object.__setattr__(self, "task_id", _id(self.task_id, "task id"))
        object.__setattr__(self, "audience", _id(self.audience, "audience"))
        if self.audience == "*":
            raise ValidationError("wildcard audience is not permitted")
        object.__setattr__(self, "target", _target(self.target, "target"))
        object.__setattr__(self, "permissions", _tokens(self.permissions, "permissions", allow_empty=False))
        object.__setattr__(self, "effect_classes", _tokens(self.effect_classes, "effect classes", allow_empty=True))
        object.__setattr__(self, "fence_epoch", _int(self.fence_epoch, "fence epoch", minimum=1))
        object.__setattr__(self, "revocation_epoch", _int(self.revocation_epoch, "revocation epoch"))
        object.__setattr__(self, "not_before", _int(self.not_before, "not_before"))
        object.__setattr__(self, "expires_at", _int(self.expires_at, "expires_at"))
        if self.expires_at <= self.not_before:
            raise ValidationError("capability expires_at must be after not_before")
        if self.expires_at - self.not_before > MAX_CAPABILITY_TTL:
            raise ValidationError("capability validity exceeds maximum TTL")
        object.__setattr__(self, "nonce", _hex64(self.nonce, "nonce"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "identity_id": self.identity_id,
            "installation_id": self.installation_id,
            "project_id": self.project_id,
            "contract_id": self.contract_id,
            "generation": self.generation,
            "task_id": self.task_id,
            "audience": self.audience,
            "target": self.target,
            "permissions": list(self.permissions),
            "effect_classes": list(self.effect_classes),
            "fence_epoch": self.fence_epoch,
            "revocation_epoch": self.revocation_epoch,
            "not_before": self.not_before,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, value: Any) -> CapabilityClaim:
        fields = {
            "capability_id", "identity_id", "installation_id", "project_id", "contract_id", "generation",
            "task_id", "audience", "target", "permissions", "effect_classes", "fence_epoch", "revocation_epoch",
            "not_before", "expires_at", "nonce",
        }
        _fields(value, fields, "capability claim")
        if not isinstance(value["permissions"], list) or not isinstance(value["effect_classes"], list):
            raise ValidationError("invalid capability claim collections")
        values = dict(value)
        values["permissions"] = tuple(values["permissions"])
        values["effect_classes"] = tuple(values["effect_classes"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class SignedCapability:
    claim: CapabilityClaim
    issuer: str
    key_id: str
    signature: str
    encoding_version: int = ENCODING_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.claim, CapabilityClaim):
            raise ValidationError("invalid signed capability claim")
        object.__setattr__(self, "issuer", _id(self.issuer, "issuer"))
        object.__setattr__(self, "key_id", _id(self.key_id, "key id"))
        object.__setattr__(self, "signature", _hex64(self.signature, "capability signature"))
        if self.encoding_version != ENCODING_VERSION:
            raise ValidationError("unsupported capability encoding version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "issuer": self.issuer,
            "key_id": self.key_id,
            "signature": self.signature,
            "encoding_version": self.encoding_version,
        }

    @classmethod
    def from_dict(cls, value: Any) -> SignedCapability:
        _fields(value, {"claim", "issuer", "key_id", "signature", "encoding_version"}, "signed capability")
        return cls(CapabilityClaim.from_dict(value["claim"]), value["issuer"], value["key_id"], value["signature"], value["encoding_version"])


def _capability_signing_claims(claim: CapabilityClaim, issuer: str, key_id: str) -> dict[str, Any]:
    return {"encoding_version": ENCODING_VERSION, "claim": claim.to_dict(), "issuer": issuer, "key_id": key_id}


def issue_capability(registry: IdentityRegistry, claim: CapabilityClaim, *, issuer: str, key_id: str) -> SignedCapability:
    if not isinstance(registry, IdentityRegistry) or not isinstance(claim, CapabilityClaim):
        raise ValidationError("invalid capability issuance input")
    issuer = _id(issuer, "issuer")
    secret = registry._active_key(key_id, KeyPurpose.ISSUER)
    if secret is None:
        raise ValidationError("unknown or inactive issuer key")
    signature = hmac.new(secret, _canonical_json(_capability_signing_claims(claim, issuer, key_id)), hashlib.sha256).hexdigest()
    return SignedCapability(claim, issuer, key_id, signature)


def verify_capability_signature(registry: IdentityRegistry, signed: SignedCapability) -> bool:
    """Verify issuer signature over the claim, issuer, and key_id together. Never raises; fails closed."""
    if not isinstance(registry, IdentityRegistry) or not isinstance(signed, SignedCapability):
        return False
    secret = registry._active_key(signed.key_id, KeyPurpose.ISSUER)
    if secret is None:
        return False
    expected = hmac.new(
        secret, _canonical_json(_capability_signing_claims(signed.claim, signed.issuer, signed.key_id)), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signed.signature)


@dataclass(frozen=True, slots=True)
class AuthoritySnapshot:
    """Immutable, caller-supplied ground truth for one authorization decision.

    R4 never fetches or mutates contract/lease state; callers own producing this
    snapshot from live R1-R3 state (deferred wiring is R5 scope).
    """

    installation_id: str
    project_id: str
    contract: ExecutionContract
    fence_epoch: int
    fence_expires_at: int
    issuer_ceiling: tuple[str, ...]
    project_ceiling: tuple[str, ...]
    task_grants: Mapping[str, tuple[str, ...]]
    trusted_issuer: str
    audience: str
    issuer_effect_ceiling: tuple[str, ...]
    project_effect_ceiling: tuple[str, ...]
    task_effect_grants: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "installation_id", _id(self.installation_id, "installation id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        if not isinstance(self.contract, ExecutionContract) or self.contract.project_id != self.project_id:
            raise ValidationError("invalid snapshot contract")
        if self.contract.status is not ContractState.ACTIVE:
            raise ValidationError("only an active contract can authorize capabilities")
        object.__setattr__(self, "fence_epoch", _int(self.fence_epoch, "fence epoch", minimum=1))
        object.__setattr__(self, "fence_expires_at", _int(self.fence_expires_at, "fence expiry", minimum=1))
        object.__setattr__(self, "issuer_ceiling", _tokens(self.issuer_ceiling, "issuer ceiling", allow_empty=True))
        object.__setattr__(self, "project_ceiling", _tokens(self.project_ceiling, "project ceiling", allow_empty=True))
        object.__setattr__(self, "trusted_issuer", _id(self.trusted_issuer, "trusted issuer"))
        object.__setattr__(self, "audience", _id(self.audience, "audience"))
        object.__setattr__(
            self, "issuer_effect_ceiling", _tokens(self.issuer_effect_ceiling, "issuer effect ceiling", allow_empty=True)
        )
        object.__setattr__(
            self, "project_effect_ceiling", _tokens(self.project_effect_ceiling, "project effect ceiling", allow_empty=True)
        )
        if not isinstance(self.task_grants, Mapping):
            raise ValidationError("invalid task grants")
        grants: dict[str, tuple[str, ...]] = {}
        for task_id, permissions in self.task_grants.items():
            grants[_id(task_id, "task id")] = _tokens(permissions, "task grant", allow_empty=True)
        object.__setattr__(self, "task_grants", MappingProxyType(grants))
        if not isinstance(self.task_effect_grants, Mapping):
            raise ValidationError("invalid task effect grants")
        effect_grants: dict[str, tuple[str, ...]] = {}
        for task_id, effects in self.task_effect_grants.items():
            effect_grants[_id(task_id, "task id")] = _tokens(effects, "task effect grant", allow_empty=True)
        object.__setattr__(self, "task_effect_grants", MappingProxyType(effect_grants))


class AuthorizationDenial(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN_KEY = "UNKNOWN_KEY"
    REVOKED = "REVOKED"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"
    BAD_SIGNATURE = "BAD_SIGNATURE"
    BAD_PROOF = "BAD_PROOF"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    STALE_AUTHORITY = "STALE_AUTHORITY"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    REPLAYED = "REPLAYED"


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    granted: bool
    reason: AuthorizationDenial | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.granted, bool):
            raise ValidationError("invalid authorization result")
        if self.granted and self.reason is not None:
            raise ValidationError("granted result must not carry a denial reason")
        if not self.granted and not isinstance(self.reason, AuthorizationDenial):
            raise ValidationError("denied result requires a denial reason")


class ReplayCache:
    """In-memory, clock-scoped single-use guard for (capability, proof, request) tuples."""

    def __init__(self, *, clock: Callable[[], int]):
        self._clock = clock
        self._entries: dict[str, int] = {}
        self._lock = Lock()

    def consume(self, key: str, *, expires_at: int) -> bool:
        """Mark `key` used. Returns False (and leaves state unchanged) if already used."""
        try:
            key = _id(key, "replay key")
            now = _int(self._clock(), "clock")
            expires_at = _int(expires_at, "replay expiry", minimum=now + 1)
        except ValidationError:
            return False
        with self._lock:
            for stale in [existing for existing, exp in self._entries.items() if exp <= now]:
                del self._entries[stale]
            if key in self._entries:
                return False
            self._entries[key] = expires_at
            return True


def _deny(reason: AuthorizationDenial) -> AuthorizationResult:
    return AuthorizationResult(False, reason)


def authorize(
    registry: IdentityRegistry,
    *,
    principal: Principal,
    request_binding: WorkloadBinding,
    credential: IdentityCredential,
    capability: SignedCapability,
    proof: HolderProof,
    snapshot: AuthoritySnapshot,
    audience: str,
    request_target: str,
    request_permission: str,
    request_effect_class: str | None,
    request_digest: str,
    replay_cache: ReplayCache,
    now: int,
) -> AuthorizationResult:
    """The single canonical authorization boundary. Never raises; always fails closed.

    No path -- granted or denied -- mutates contract, lease, or ledger state. The only
    stateful side effect on the granted path is marking the replay cache entry used.
    """
    if not isinstance(registry, IdentityRegistry) or not isinstance(replay_cache, ReplayCache):
        return _deny(AuthorizationDenial.INVALID_INPUT)
    if not isinstance(principal, Principal) or not isinstance(credential, IdentityCredential):
        return _deny(AuthorizationDenial.INVALID_INPUT)
    if not isinstance(capability, SignedCapability) or not isinstance(proof, HolderProof):
        return _deny(AuthorizationDenial.INVALID_INPUT)
    if not isinstance(snapshot, AuthoritySnapshot) or not isinstance(request_binding, WorkloadBinding):
        return _deny(AuthorizationDenial.INVALID_INPUT)
    try:
        audience = _id(audience, "audience")
        request_target = _target(request_target, "request target")
        request_permission = _token(request_permission, "request permission")
        if request_effect_class is not None:
            request_effect_class = _token(request_effect_class, "request effect class")
        request_digest = _hex64(request_digest, "request digest")
        now = _int(now, "now")
    except ValidationError:
        return _deny(AuthorizationDenial.INVALID_INPUT)

    claim = capability.claim

    if not (credential.not_before <= now < credential.expires_at):
        return _deny(AuthorizationDenial.NOT_YET_VALID if now < credential.not_before else AuthorizationDenial.EXPIRED)
    if not (claim.not_before <= now < claim.expires_at):
        return _deny(AuthorizationDenial.NOT_YET_VALID if now < claim.not_before else AuthorizationDenial.EXPIRED)

    if not verify_identity_credential(registry, credential, audience=audience, now=now):
        if credential.audience != audience:
            return _deny(AuthorizationDenial.BINDING_MISMATCH)
        identity_epoch = registry.active_identity_epoch(credential.identity_id)
        if identity_epoch is None or identity_epoch != credential.revocation_epoch:
            return _deny(AuthorizationDenial.REVOKED)
        if not registry.is_key_active(credential.key_id, purpose=KeyPurpose.ISSUER) or not registry.is_key_active(
            credential.holder_key_id, purpose=KeyPurpose.HOLDER
        ):
            return _deny(AuthorizationDenial.UNKNOWN_KEY)
        return _deny(AuthorizationDenial.BAD_SIGNATURE)

    if not verify_capability_signature(registry, capability):
        if not registry.is_key_active(capability.key_id, purpose=KeyPurpose.ISSUER):
            return _deny(AuthorizationDenial.UNKNOWN_KEY)
        return _deny(AuthorizationDenial.BAD_SIGNATURE)

    if credential.issuer != snapshot.trusted_issuer or capability.issuer != snapshot.trusted_issuer:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if audience != snapshot.audience or credential.audience != snapshot.audience or claim.audience != snapshot.audience:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if claim.identity_id != credential.identity_id:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if claim.audience != audience:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if credential.issuer != capability.issuer:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if credential.binding != request_binding:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if request_binding.installation_id != snapshot.installation_id or claim.installation_id != snapshot.installation_id:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if request_binding.project_id != snapshot.project_id or claim.project_id != snapshot.project_id or principal.project_id != snapshot.project_id:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if request_binding.role != principal.actor_id:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)
    if principal not in snapshot.contract.participants:
        return _deny(AuthorizationDenial.BINDING_MISMATCH)

    if claim.contract_id != snapshot.contract.contract_id:
        return _deny(AuthorizationDenial.STALE_AUTHORITY)
    try:
        assert_current_generation(claim.generation, claim.revocation_epoch, snapshot.contract.generation, snapshot.contract.revocation_epoch)
    except ValidationError:
        return _deny(AuthorizationDenial.STALE_AUTHORITY)
    if claim.fence_epoch != snapshot.fence_epoch:
        return _deny(AuthorizationDenial.STALE_AUTHORITY)
    if snapshot.fence_expires_at <= now:
        return _deny(AuthorizationDenial.STALE_AUTHORITY)

    if claim.target != request_target:
        return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if request_permission not in claim.permissions:
        return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if request_effect_class is not None and request_effect_class not in claim.effect_classes:
        return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if request_effect_class is not None:
        if request_effect_class not in snapshot.issuer_effect_ceiling:
            return _deny(AuthorizationDenial.PERMISSION_DENIED)
        if request_effect_class not in snapshot.project_effect_ceiling:
            return _deny(AuthorizationDenial.PERMISSION_DENIED)
        if request_effect_class not in snapshot.task_effect_grants.get(claim.task_id, ()):
            return _deny(AuthorizationDenial.PERMISSION_DENIED)
        if request_effect_class not in snapshot.contract.side_effect_policy.allowed_effects:
            return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if request_permission not in snapshot.issuer_ceiling:
        return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if request_permission not in snapshot.project_ceiling:
        return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if request_permission not in snapshot.task_grants.get(claim.task_id, ()):
        return _deny(AuthorizationDenial.PERMISSION_DENIED)
    if not is_role_permitted(snapshot.contract, principal, request_permission):
        return _deny(AuthorizationDenial.PERMISSION_DENIED)

    if proof.holder_key_id != credential.holder_key_id:
        return _deny(AuthorizationDenial.BAD_PROOF)
    if proof.request_digest != request_digest:
        return _deny(AuthorizationDenial.BAD_PROOF)
    if not verify_holder_proof(
        registry, proof, expected_holder_key_id=credential.holder_key_id,
        subject_canonical=capability.to_dict(), request_digest=request_digest,
    ):
        return _deny(AuthorizationDenial.BAD_PROOF)

    replay_key = hashlib.sha256(_canonical_json({
        "capability_id": claim.capability_id, "nonce": claim.nonce,
        "challenge": proof.challenge, "request_digest": request_digest,
    })).hexdigest()
    replay_expiry = min(credential.expires_at, claim.expires_at)
    if not replay_cache.consume(replay_key, expires_at=replay_expiry):
        return _deny(AuthorizationDenial.REPLAYED)

    return AuthorizationResult(True, None)


__all__ = [
    "AuthorizationDenial",
    "AuthorizationResult",
    "AuthoritySnapshot",
    "CapabilityClaim",
    "MAX_CAPABILITY_TTL",
    "ReplayCache",
    "SignedCapability",
    "authorize",
    "issue_capability",
    "verify_capability_signature",
]
