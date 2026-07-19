"""Tests-only fail-closed authorization boundary feasibility proof.

Production must expose E2-E4 only through this authoritative boundary.  Direct
``model_tools`` calls cannot be enforcement-authoritative: an observer skip
flag may suppress observation, but it must never bypass this guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

AUTHORIZATION_DIMENSIONS = (
    "identity/principal",
    "project",
    "contract_id",
    "contract_generation",
    "task_id",
    "audience",
    "target",
    "effect_class",
    "revocation_epoch",
    "fencing_epoch",
    "expiration",
)

FIXED_REQUEST: dict[str, object] = {
    "identity/principal": "principal-0",
    "project": "project-0",
    "contract_id": "contract-0",
    "contract_generation": 3,
    "task_id": "task-0",
    "audience": "audience-0",
    "target": "target-0",
    "effect_class": "E4",
    "revocation_epoch": 7,
    "fencing_epoch": 11,
    "expiration": 2000,
}
FIXED_AUTHORITY = dict(FIXED_REQUEST)
FIXED_NOW = 1000

DENIAL_GUARD_RAISED = "denied.guard_raised"
DENIAL_GUARD_UNAVAILABLE = "denied.guard_unavailable"
DENIAL_MALFORMED_DECISION = "denied.malformed_decision"
DENIAL_MISMATCH = "denied.authorization_mismatch"
DENIAL_STALE_AUTHORITY = "denied.stale_revoked_or_expired"

PRODUCTION_BOUNDARY_NOTE = (
    "Production must expose E2-E4 only through this authoritative boundary; "
    "direct model_tools calls cannot be enforcement-authoritative."
)


@dataclass(frozen=True)
class BoundaryResult:
    allowed: bool
    classification: str
    dispatch_result: Any = None
    observer_skip_pre_tool_call_hook: bool = False


def _valid_dimension_values(values: Mapping[str, object]) -> bool:
    if set(values) != set(AUTHORIZATION_DIMENSIONS):
        return False
    for dimension in AUTHORIZATION_DIMENSIONS:
        value = values[dimension]
        if dimension in {"contract_generation", "revocation_epoch", "fencing_epoch", "expiration"}:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return False
        elif not isinstance(value, str) or not value:
            return False
    return True


def _deny(classification: str) -> BoundaryResult:
    return BoundaryResult(allowed=False, classification=classification)


def authorize_then_dispatch(
    request: Mapping[str, object],
    guard: Callable[[Mapping[str, object]], Mapping[str, object]] | None,
    dispatcher: Callable[..., Any],
    *,
    skip_pre_tool_call_hook: bool = False,
    now: int = FIXED_NOW,
) -> BoundaryResult:
    """Authorize every required dimension before invoking the fake dispatcher."""
    if not _valid_dimension_values(request):
        return _deny(DENIAL_MISMATCH)
    if guard is None or not callable(guard):
        return _deny(DENIAL_GUARD_UNAVAILABLE)

    try:
        raw_decision = guard(request)
    except Exception:
        return _deny(DENIAL_GUARD_RAISED)

    if not isinstance(raw_decision, Mapping):
        return _deny(DENIAL_MALFORMED_DECISION)
    if raw_decision.get("decision") != "allow":
        return _deny(DENIAL_MALFORMED_DECISION)
    if set(raw_decision) - {*AUTHORIZATION_DIMENSIONS, "decision", "revoked"}:
        return _deny(DENIAL_MALFORMED_DECISION)
    authority = {dimension: raw_decision.get(dimension) for dimension in AUTHORIZATION_DIMENSIONS}
    if not _valid_dimension_values(authority):
        return _deny(DENIAL_MALFORMED_DECISION)
    if raw_decision.get("revoked", False) is not False:
        return _deny(DENIAL_STALE_AUTHORITY)
    if authority["revocation_epoch"] < request["revocation_epoch"]:
        return _deny(DENIAL_STALE_AUTHORITY)
    if authority["fencing_epoch"] < request["fencing_epoch"]:
        return _deny(DENIAL_STALE_AUTHORITY)
    if authority["expiration"] <= now:
        return _deny(DENIAL_STALE_AUTHORITY)
    if any(authority[dimension] != request[dimension] for dimension in AUTHORIZATION_DIMENSIONS):
        return _deny(DENIAL_MISMATCH)

    dispatch_result = dispatcher(request, skip_pre_tool_call_hook=skip_pre_tool_call_hook)
    return BoundaryResult(
        allowed=True,
        classification="authorized",
        dispatch_result=dispatch_result,
        observer_skip_pre_tool_call_hook=skip_pre_tool_call_hook,
    )
