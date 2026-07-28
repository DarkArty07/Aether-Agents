from __future__ import annotations

from dataclasses import dataclass

import pytest
from authorization_boundary_proof import (
    AUTHORIZATION_DIMENSIONS,
    DENIAL_GUARD_RAISED,
    DENIAL_GUARD_UNAVAILABLE,
    DENIAL_MALFORMED_DECISION,
    DENIAL_MISMATCH,
    DENIAL_STALE_AUTHORITY,
    FIXED_AUTHORITY,
    FIXED_REQUEST,
    authorize_then_dispatch,
)


@dataclass
class Harness:
    guard_calls: int = 0
    dispatch_calls: int = 0
    observer_flags: list[bool] | None = None

    def guard(self, _request: dict[str, object]) -> dict[str, object]:
        self.guard_calls += 1
        return {"decision": "allow", **FIXED_AUTHORITY}

    def dispatch(self, _request: dict[str, object], *, skip_pre_tool_call_hook: bool) -> str:
        self.dispatch_calls += 1
        if self.observer_flags is None:
            self.observer_flags = []
        self.observer_flags.append(skip_pre_tool_call_hook)
        return "fake-dispatch-result"


@pytest.fixture
def harness() -> Harness:
    return Harness()


def test_valid_authority_dispatches_once_and_forwards_observer_skip(harness: Harness) -> None:
    result = authorize_then_dispatch(
        FIXED_REQUEST,
        harness.guard,
        harness.dispatch,
        skip_pre_tool_call_hook=True,
    )

    assert result.allowed is True
    assert result.classification == "authorized"
    assert result.dispatch_result == "fake-dispatch-result"
    assert result.observer_skip_pre_tool_call_hook is True
    assert harness.guard_calls == 1
    assert harness.dispatch_calls == 1
    assert harness.observer_flags == [True]


def test_valid_authority_without_skip_forwards_false(harness: Harness) -> None:
    result = authorize_then_dispatch(FIXED_REQUEST, harness.guard, harness.dispatch)

    assert result.allowed is True
    assert harness.guard_calls == 1
    assert harness.dispatch_calls == 1
    assert harness.observer_flags == [False]


@pytest.mark.parametrize(
    ("name", "guard_factory", "expected_classification"),
    [
        ("guard raises", lambda h: _raising_guard(h, RuntimeError("guard failed")), DENIAL_GUARD_RAISED),
        ("timeout-like exception", lambda h: _raising_guard(h, TimeoutError("timed out")), DENIAL_GUARD_RAISED),
        ("guard unavailable", lambda _h: None, DENIAL_GUARD_UNAVAILABLE),
        ("malformed decision", lambda h: _fixed_result_guard(h, {"decision": "allow"}), DENIAL_MALFORMED_DECISION),
    ],
)
def test_fail_closed_guard_failures_never_dispatch(
    harness: Harness, name: str, guard_factory, expected_classification: str
) -> None:
    del name
    guard = guard_factory(harness)

    result = authorize_then_dispatch(
        FIXED_REQUEST,
        guard,
        harness.dispatch,
        skip_pre_tool_call_hook=True,
    )

    assert result.allowed is False
    assert result.classification == expected_classification
    assert result.dispatch_result is None
    assert result.observer_skip_pre_tool_call_hook is False
    assert harness.guard_calls == (1 if guard is not None else 0)
    assert harness.dispatch_calls == 0


def _raising_guard(harness: Harness, error: Exception):
    def guard(_request: dict[str, object]) -> dict[str, object]:
        harness.guard_calls += 1
        raise error

    return guard


def _fixed_result_guard(harness: Harness, result: dict[str, object]):
    def guard(_request: dict[str, object]) -> dict[str, object]:
        harness.guard_calls += 1
        return result

    return guard


@pytest.mark.parametrize("dimension", AUTHORIZATION_DIMENSIONS)
def test_any_required_dimension_mismatch_denies_without_dispatch(
    harness: Harness, dimension: str
) -> None:
    decision = {"decision": "allow", **FIXED_AUTHORITY}
    if isinstance(FIXED_REQUEST[dimension], int):
        decision[dimension] = FIXED_REQUEST[dimension] + 1
    else:
        decision[dimension] = f"wrong-{dimension}"

    def guard(_request: dict[str, object]) -> dict[str, object]:
        harness.guard_calls += 1
        return decision

    result = authorize_then_dispatch(FIXED_REQUEST, guard, harness.dispatch, skip_pre_tool_call_hook=True)

    assert result.allowed is False
    assert result.classification in {DENIAL_MISMATCH, DENIAL_STALE_AUTHORITY}
    assert harness.guard_calls == 1
    assert harness.dispatch_calls == 0


@pytest.mark.parametrize(
    "bad_authority",
    [
        {**FIXED_AUTHORITY, "revocation_epoch": 4},
        {**FIXED_AUTHORITY, "fencing_epoch": 6},
        {**FIXED_AUTHORITY, "revoked": True},
        {**FIXED_AUTHORITY, "expiration": 999},
    ],
)
def test_stale_revoked_or_expired_authority_denies(
    harness: Harness, bad_authority: dict[str, object]
) -> None:
    def guard(_request: dict[str, object]) -> dict[str, object]:
        harness.guard_calls += 1
        return {"decision": "allow", **bad_authority}

    result = authorize_then_dispatch(FIXED_REQUEST, guard, harness.dispatch, skip_pre_tool_call_hook=True)

    assert result.allowed is False
    assert result.classification == DENIAL_STALE_AUTHORITY
    assert harness.guard_calls == 1
    assert harness.dispatch_calls == 0


def test_missing_and_malformed_request_values_deny_before_dispatch(harness: Harness) -> None:
    for dimension in AUTHORIZATION_DIMENSIONS:
        request = dict(FIXED_REQUEST)
        request.pop(dimension)
        result = authorize_then_dispatch(request, harness.guard, harness.dispatch)
        assert result.allowed is False
        assert result.classification == DENIAL_MISMATCH

    for dimension, value in (
        ("identity/principal", ""),
        ("contract_generation", True),
        ("revocation_epoch", -1),
        ("expiration", "not-an-epoch"),
    ):
        request = dict(FIXED_REQUEST)
        request[dimension] = value
        result = authorize_then_dispatch(request, harness.guard, harness.dispatch)
        assert result.allowed is False
        assert result.classification == DENIAL_MISMATCH

    assert harness.guard_calls == 0
    assert harness.dispatch_calls == 0


def test_invalid_authority_with_skip_true_cannot_bypass_authorization(harness: Harness) -> None:
    def guard(_request: dict[str, object]) -> dict[str, object]:
        harness.guard_calls += 1
        return {"decision": "deny", **FIXED_AUTHORITY}

    result = authorize_then_dispatch(FIXED_REQUEST, guard, harness.dispatch, skip_pre_tool_call_hook=True)

    assert result.allowed is False
    assert result.classification == DENIAL_MALFORMED_DECISION
    assert harness.guard_calls == 1
    assert harness.dispatch_calls == 0


def test_production_boundary_requirements_are_documented() -> None:
    from authorization_boundary_proof import PRODUCTION_BOUNDARY_NOTE

    assert "E2-E4" in PRODUCTION_BOUNDARY_NOTE
    assert "authoritative boundary" in PRODUCTION_BOUNDARY_NOTE
    assert "direct model_tools calls" in PRODUCTION_BOUNDARY_NOTE
