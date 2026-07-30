"""Default-off semantic effect model; this module never performs effects."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from typing import Any, Iterable

from .principal import ValidationError

_ID = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,127}$")
HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_TEXT = 1024
MAX_COLLECTION = 64
MIN_SIGNING_KEY_BYTES = 16
_TRANSITION_AUTHORITY = object()
_APPROVAL_VERIFICATION_KEY = secrets.token_bytes(32)
_RECEIPT_KEY = secrets.token_bytes(32)
_VERIFIED_APPROVALS_USED: set[str] = set()
_VERIFIED_APPROVALS_LOCK = Lock()


def _s(value: Any, name: str, max_len: int = MAX_TEXT) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_len
        or any(ord(char) < 32 for char in value)
    ):
        raise ValidationError(f"invalid {name}")
    return value


def _id(value: Any, name: str) -> str:
    value = _s(value, name, 128)
    if not _ID.fullmatch(value):
        raise ValidationError(f"invalid {name}")
    return value


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"invalid {name}")
    return value


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValidationError(f"invalid {name}")
    return value


def _hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValidationError(f"invalid {name}")
    return value


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise ValidationError("invalid canonical value") from exc


def _key(value: Any) -> bytes:
    if not isinstance(value, bytes) or len(value) < MIN_SIGNING_KEY_BYTES:
        raise ValidationError("invalid signing key")
    return value


class EffectClass(StrEnum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"


class EffectLifecycle(StrEnum):
    PLANNED = "planned"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    RECONCILED_SUCCEEDED = "reconciled_succeeded"
    RECONCILED_FAILED = "reconciled_failed"
    MANUAL_RESOLUTION = "manual_resolution"


EffectState = EffectLifecycle
_TERMINAL_RECEIPT_STATES = frozenset(
    {
        EffectLifecycle.SUCCEEDED,
        EffectLifecycle.FAILED,
        EffectLifecycle.UNKNOWN,
        EffectLifecycle.RECONCILED_SUCCEEDED,
        EffectLifecycle.RECONCILED_FAILED,
        EffectLifecycle.MANUAL_RESOLUTION,
    }
)


@dataclass(frozen=True, slots=True)
class SecretReference:
    project_id: str
    reference: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        object.__setattr__(self, "reference", _id(self.reference, "secret reference"))
        words = set(re.split(r"[._:/-]+", self.reference.lower()))
        if words.intersection({"secret", "password", "token", "key", "value"}):
            raise ValidationError("secret reference must be opaque")


@dataclass(frozen=True, slots=True)
class EffectSpec:
    project_id: str
    contract_id: str
    generation: int
    task_id: str
    operation: str
    target: str
    version: str
    effect_class: EffectClass
    lifecycle: EffectLifecycle = EffectLifecycle.PLANNED
    precondition_hash: str = "0" * 64
    _transition_authority: object | None = field(default=None, repr=False, compare=False, kw_only=True)

    def __post_init__(self) -> None:
        for attribute, name in (
            ("project_id", "project id"),
            ("contract_id", "contract id"),
            ("task_id", "task id"),
            ("operation", "operation"),
            ("target", "target"),
            ("version", "version"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "generation", _int(self.generation, "generation"))
        object.__setattr__(
            self,
            "precondition_hash",
            _hash(self.precondition_hash, "precondition hash"),
        )
        if not isinstance(self.effect_class, EffectClass) or not isinstance(self.lifecycle, EffectLifecycle):
            raise ValidationError("unknown effect class or lifecycle")
        if self.lifecycle is not EffectLifecycle.PLANNED and self._transition_authority is not _TRANSITION_AUTHORITY:
            raise ValidationError("nonplanned state requires validated transition")
        object.__setattr__(self, "_transition_authority", None)

    @property
    def effect_id(self) -> str:
        return hashlib.sha256(
            _canon(
                [
                    self.project_id,
                    self.contract_id,
                    self.generation,
                    self.task_id,
                    self.operation,
                    self.target,
                    self.version,
                ]
            )
        ).hexdigest()

    @property
    def idempotency_key(self) -> str:
        return f"{self.project_id}:{self.effect_id}"


@dataclass(frozen=True, slots=True)
class TypedApproval:
    authority_identity: str
    effect_id: str
    target: str
    contract_id: str
    generation: int
    contract_hash: str
    artifact_hash: str
    nonce: str
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for attribute, name in (
            ("authority_identity", "authority identity"),
            ("target", "target"),
            ("contract_id", "contract id"),
            ("nonce", "nonce"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "effect_id", _hash(self.effect_id, "effect id"))
        object.__setattr__(self, "generation", _int(self.generation, "generation"))
        object.__setattr__(self, "contract_hash", _hash(self.contract_hash, "contract hash"))
        object.__setattr__(self, "artifact_hash", _hash(self.artifact_hash, "artifact hash"))
        object.__setattr__(self, "issued_at", _utc(self.issued_at, "issued at"))
        object.__setattr__(self, "expires_at", _utc(self.expires_at, "expires at"))
        if self.expires_at <= self.issued_at:
            raise ValidationError("approval expiry")

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_identity": self.authority_identity,
            "effect_id": self.effect_id,
            "target": self.target,
            "contract_id": self.contract_id,
            "generation": self.generation,
            "contract_hash": self.contract_hash,
            "artifact_hash": self.artifact_hash,
            "nonce": self.nonce,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @property
    def canonical_hash(self) -> str:
        return hashlib.sha256(_canon(self.to_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class SignedApproval:
    approval: TypedApproval
    signature: str

    def __post_init__(self) -> None:
        if not isinstance(self.approval, TypedApproval):
            raise ValidationError("invalid signed approval")
        object.__setattr__(self, "signature", _hash(self.signature, "approval signature"))


@dataclass(frozen=True, slots=True)
class VerifiedApproval:
    effect_id: str
    approval_hash: str
    signature: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_id", _hash(self.effect_id, "verified effect id"))
        object.__setattr__(self, "approval_hash", _hash(self.approval_hash, "verified approval hash"))
        object.__setattr__(self, "signature", _hash(self.signature, "verification signature"))

    def payload(self) -> list[str]:
        return [self.effect_id, self.approval_hash]


class ApprovalReplayCache:
    """Atomic process-local nonce consumption for isolated/default-off R6.

    Shared durable replay remains a mandatory pre-runtime integration requirement.
    """

    def __init__(self) -> None:
        self._used: set[tuple[str, str, str]] = set()
        self._lock = Lock()

    def consume(self, approval: TypedApproval) -> None:
        if not isinstance(approval, TypedApproval):
            raise ValidationError("invalid approval replay input")
        key = (approval.authority_identity, approval.effect_id, approval.nonce)
        with self._lock:
            if key in self._used:
                raise ValidationError("approval replay")
            self._used.add(key)


def sign_approval(approval: TypedApproval, key: bytes) -> SignedApproval:
    if not isinstance(approval, TypedApproval):
        raise ValidationError("invalid approval")
    signature = hmac.new(_key(key), _canon(approval.to_dict()), hashlib.sha256).hexdigest()
    return SignedApproval(approval, signature)


def verify_approval(
    signed: SignedApproval,
    effect: EffectSpec,
    *,
    key: bytes,
    now: datetime,
    replay_cache: ApprovalReplayCache,
    artifact_hash: str,
    allowed_authorities: Iterable[str],
) -> VerifiedApproval:
    if not isinstance(signed, SignedApproval) or not isinstance(effect, EffectSpec):
        raise ValidationError("invalid approval verification")
    now = _utc(now, "approval verification time")
    artifact_hash = _hash(artifact_hash, "artifact hash")
    authorities = frozenset(_id(item, "approval authority") for item in allowed_authorities)
    approval = signed.approval
    expected = hmac.new(_key(key), _canon(approval.to_dict()), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signed.signature):
        raise ValidationError("invalid approval signature")
    if not approval.issued_at <= now < approval.expires_at:
        raise ValidationError("expired approval")
    if approval.authority_identity not in authorities:
        raise ValidationError("unauthorized approval authority")
    if (
        approval.effect_id != effect.effect_id
        or approval.target != effect.target
        or approval.contract_id != effect.contract_id
        or approval.generation != effect.generation
        or approval.contract_hash != effect.precondition_hash
        or approval.artifact_hash != artifact_hash
    ):
        raise ValidationError("approval binding mismatch")
    if not isinstance(replay_cache, ApprovalReplayCache):
        raise ValidationError("invalid approval replay cache")
    replay_cache.consume(approval)
    payload = [effect.effect_id, approval.canonical_hash]
    signature = hmac.new(_APPROVAL_VERIFICATION_KEY, _canon(payload), hashlib.sha256).hexdigest()
    return VerifiedApproval(effect.effect_id, approval.canonical_hash, signature)


def _verify_approval_artifact(value: VerifiedApproval | None, effect: EffectSpec) -> None:
    if not isinstance(value, VerifiedApproval) or value.effect_id != effect.effect_id:
        raise ValidationError("verified E4 approval required")
    expected = hmac.new(_APPROVAL_VERIFICATION_KEY, _canon(value.payload()), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, value.signature):
        raise ValidationError("invalid approval verification artifact")
    with _VERIFIED_APPROVALS_LOCK:
        if value.signature in _VERIFIED_APPROVALS_USED:
            raise ValidationError("verified approval replay")
        _VERIFIED_APPROVALS_USED.add(value.signature)


@dataclass(frozen=True, slots=True, init=False)
class EffectReceipt:
    effect_id: str
    idempotency_key: str
    project_id: str
    contract_id: str
    generation: int
    task_id: str
    operation: str
    version: str
    effect_class: EffectClass
    precondition_hash: str
    actor: str
    target: str
    timestamp: datetime
    state: EffectLifecycle
    result: str
    artifact_reference: str | None = None
    artifact_hash: str | None = None
    signature: str = ""

    def __init__(
        self,
        effect: EffectSpec,
        actor: str,
        timestamp: datetime,
        state: EffectLifecycle,
        result: str,
        artifact_reference: str | None = None,
        artifact_hash: str | None = None,
    ) -> None:
        if not isinstance(effect, EffectSpec):
            raise ValidationError("originating effect required")
        if (
            not isinstance(state, EffectLifecycle)
            or state not in _TERMINAL_RECEIPT_STATES
            or effect.lifecycle is not state
        ):
            raise ValidationError("invalid receipt state")
        object.__setattr__(self, "effect_id", effect.effect_id)
        object.__setattr__(self, "idempotency_key", effect.idempotency_key)
        object.__setattr__(self, "project_id", effect.project_id)
        object.__setattr__(self, "contract_id", effect.contract_id)
        object.__setattr__(self, "generation", effect.generation)
        object.__setattr__(self, "task_id", effect.task_id)
        object.__setattr__(self, "operation", effect.operation)
        object.__setattr__(self, "version", effect.version)
        object.__setattr__(self, "effect_class", effect.effect_class)
        object.__setattr__(self, "precondition_hash", effect.precondition_hash)
        object.__setattr__(self, "actor", _id(actor, "actor"))
        object.__setattr__(self, "target", effect.target)
        object.__setattr__(self, "timestamp", _utc(timestamp, "timestamp"))
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "result", _s(result, "result"))
        object.__setattr__(
            self,
            "artifact_reference",
            None if artifact_reference is None else _s(artifact_reference, "artifact reference"),
        )
        object.__setattr__(
            self,
            "artifact_hash",
            None if artifact_hash is None else _hash(artifact_hash, "artifact hash"),
        )
        object.__setattr__(self, "signature", "0" * 64)
        signature = hmac.new(_RECEIPT_KEY, _canon(self.payload()), hashlib.sha256).hexdigest()
        object.__setattr__(self, "signature", signature)

    def payload(self) -> list[object]:
        return [
            self.effect_id,
            self.idempotency_key,
            self.project_id,
            self.contract_id,
            self.generation,
            self.task_id,
            self.operation,
            self.version,
            self.effect_class.value,
            self.precondition_hash,
            self.actor,
            self.target,
            self.timestamp.isoformat(),
            self.state.value,
            self.result,
            self.artifact_reference,
            self.artifact_hash,
        ]


def _verify_receipt(value: EffectReceipt) -> None:
    if not isinstance(value, EffectReceipt):
        raise ValidationError("authenticated effect receipt required")
    expected = hmac.new(_RECEIPT_KEY, _canon(value.payload()), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, value.signature):
        raise ValidationError("invalid effect receipt signature")
    identity = hashlib.sha256(
        _canon(
            [
                value.project_id,
                value.contract_id,
                value.generation,
                value.task_id,
                value.operation,
                value.target,
                value.version,
            ]
        )
    ).hexdigest()
    if value.effect_id != identity or value.idempotency_key != f"{value.project_id}:{identity}":
        raise ValidationError("effect receipt identity mismatch")


def can_retry(
    effect: EffectSpec,
    state: EffectLifecycle,
    *,
    precondition_hash: str,
) -> bool:
    if not isinstance(effect, EffectSpec) or not isinstance(state, EffectLifecycle) or effect.lifecycle is not state:
        return False
    try:
        matches = _hash(precondition_hash, "precondition hash") == effect.precondition_hash
    except ValidationError:
        return False
    if not matches:
        return False
    if effect.effect_class in (EffectClass.E0, EffectClass.E1):
        return state is EffectLifecycle.FAILED
    if effect.effect_class in (EffectClass.E2, EffectClass.E3):
        return state is EffectLifecycle.RECONCILED_FAILED
    return False


def transition_effect(
    effect: EffectSpec,
    current: EffectLifecycle,
    next_state: EffectLifecycle,
    *,
    precondition_hash: str | None = None,
    verified_approval: VerifiedApproval | None = None,
) -> EffectSpec:
    if (
        not isinstance(effect, EffectSpec)
        or not isinstance(current, EffectLifecycle)
        or not isinstance(next_state, EffectLifecycle)
        or effect.lifecycle is not current
    ):
        raise ValidationError("invalid effect transition")

    ordinary = {
        EffectLifecycle.PLANNED: {EffectLifecycle.AUTHORIZED},
        EffectLifecycle.AUTHORIZED: {EffectLifecycle.EXECUTING},
        EffectLifecycle.EXECUTING: {
            EffectLifecycle.SUCCEEDED,
            EffectLifecycle.FAILED,
            EffectLifecycle.UNKNOWN,
        },
        EffectLifecycle.UNKNOWN: {
            EffectLifecycle.RECONCILED_SUCCEEDED,
            EffectLifecycle.RECONCILED_FAILED,
            EffectLifecycle.MANUAL_RESOLUTION,
        },
    }
    if next_state in ordinary.get(current, set()):
        if effect.effect_class is EffectClass.E4 and current is EffectLifecycle.PLANNED:
            _verify_approval_artifact(verified_approval, effect)
        return replace(effect, lifecycle=next_state, _transition_authority=_TRANSITION_AUTHORITY)

    if next_state is EffectLifecycle.AUTHORIZED:
        if precondition_hash is None or not can_retry(
            effect,
            current,
            precondition_hash=precondition_hash,
        ):
            raise ValidationError("effect retry is not authorized")
        return replace(effect, lifecycle=next_state, _transition_authority=_TRANSITION_AUTHORITY)

    raise ValidationError("illegal effect transition")


Effect = EffectSpec
Approval = TypedApproval
Receipt = EffectReceipt

__all__ = [
    "Approval",
    "ApprovalReplayCache",
    "Effect",
    "EffectClass",
    "EffectLifecycle",
    "EffectReceipt",
    "EffectSpec",
    "EffectState",
    "Receipt",
    "SecretReference",
    "SignedApproval",
    "TypedApproval",
    "VerifiedApproval",
    "can_retry",
    "sign_approval",
    "transition_effect",
    "verify_approval",
]
