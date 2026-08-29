"""Regression coverage for E2E-15 persistent-wake qualification."""

from __future__ import annotations

import pytest

from aether_agents.lab import matrix, runner


def _record(*, route: str, status: str = "PASS") -> dict[str, object]:
    return {
        "mode": "live-oneshot",
        "status": status,
        "expected_route": route,
        "guard_caused_manual_recovery": False,
        "observed_protected_edge_violation": False,
        "aether_self_modification": False,
    }


def test_score_history_excludes_unqualified_e2e15_claiming_pass_and_count() -> None:
    routes = ["direct", "pipeline", "safety", "recovery"]
    history = [_record(route=routes[index % len(routes)]) for index in range(19)]
    history[2] = _record(route="safety", status="FAIL")
    history.append(
        {
            **_record(route="pipeline"),
            "scenario": "e2e-15",
            "persistent_autonomous_wake_qualified": False,
            "rolling_reliability_counted": True,
        }
    )

    gate = matrix.score_history(history)

    assert gate["live_run_count"] == 19
    assert gate["window_size"] == 19
    assert gate["passed"] is False


def test_score_history_excludes_stale_e2e15_missing_qualification_fields() -> None:
    routes = ["direct", "pipeline", "safety", "recovery"]
    history = [_record(route=routes[index % len(routes)]) for index in range(19)]
    history[2] = _record(route="safety", status="FAIL")
    history.append({**_record(route="pipeline"), "scenario": "e2e-15"})

    gate = matrix.score_history(history)

    assert gate["live_run_count"] == 19
    assert gate["window_size"] == 19
    assert gate["passed"] is False


@pytest.mark.parametrize(
    ("receipts", "reason"),
    [
        (
            {"continuation_source": "one-shot", "native_surface": "hermes"},
            "one_shot_continuation_non_qualifying",
        ),
        (
            {
                "continuation_source": "native",
                "native_board_event": False,
                "durable_report": False,
                "owner_messages": 1,
                "session_id": "session-1",
            },
            "native_same_session_wake_unobserved",
        ),
    ],
)
def test_e2e15_unqualified_receipts_are_capability_wall_and_non_counted(
    receipts: dict[str, object], reason: str
) -> None:
    record = runner._qualify_e2e15_record(
        {"scenario": "e2e-15", "status": "PASS", "rolling_reliability_counted": True},
        receipts,
    )

    assert record["status"] == "CAPABILITY_WALL"
    assert record["reason"] == reason
    assert record["persistent_autonomous_wake_qualified"] is False
    assert record["rolling_reliability_counted"] is False


def test_e2e15_accepts_only_already_qualified_native_persistent_receipt() -> None:
    record = runner._qualify_e2e15_record(
        {"scenario": "e2e-15", "status": "PASS"},
        {
            "continuation_source": "native",
            "native_board_event": True,
            "durable_report": True,
            "owner_messages": 1,
            "session_id": "session-1",
            "wake_session_id": "session-1",
        },
    )

    assert record["status"] == "PASS"
    assert record["persistent_autonomous_wake_qualified"] is True
    assert record["rolling_reliability_counted"] is True
