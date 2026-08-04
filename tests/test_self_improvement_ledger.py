"""Contracts for the inert, project-local self-improvement ledger."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from aether_agents.self_improvement.ledger import LedgerSchemaError, SelfImprovementLedger

BASELINE_COMMIT = "a" * 40
MANIFEST_DIGEST = "sha256:" + "b" * 64


def _ledger(root: Path) -> SelfImprovementLedger:
    return SelfImprovementLedger(root / ".aether" / "self_improvement.db")


def _start(ledger: SelfImprovementLedger, root: Path, session_id: str, **overrides: object) -> bool:
    fields: dict[str, object] = {
        "session_id": session_id,
        "project_root": root,
        "candidate_version": "0.22.0",
        "manifest_digest": MANIFEST_DIGEST,
        "baseline_commit": BASELINE_COMMIT,
        "logical_provider": "unbound",
        "requested_model": "unreported",
        "platform": "test",
    }
    fields.update(overrides)
    return ledger.start_session(**fields)  # type: ignore[arg-type]


def test_session_identity_is_exactly_once_and_rejects_drift(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    assert _start(ledger, tmp_path, "session-a") is True
    assert _start(ledger, tmp_path, "session-a") is False
    assert ledger.session_count() == 1

    with pytest.raises(LedgerSchemaError, match="different manifest digest"):
        _start(ledger, tmp_path, "session-a", manifest_digest="sha256:" + "c" * 64)


def test_schema_is_private_and_contains_no_payload_columns(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.ensure_schema()

    assert ledger.path.parent.stat().st_mode & 0o777 == 0o700
    assert ledger.path.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(ledger.path) as connection:
        for table in ("cycle_sessions", "tool_calls", "model_calls", "coordination_events"):
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            assert not {"args", "arguments", "result", "response", "prompt", "content"} & columns


def test_symlinked_storage_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "linked"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (root / ".aether").symlink_to(external, target_is_directory=True)

    with pytest.raises(RuntimeError, match="must not be a symlink"):
        _ledger(root).ensure_schema()
    assert not (external / "self_improvement.db").exists()


def test_tool_identity_is_scoped_and_duplicate_delivery_is_idempotent(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _start(ledger, tmp_path, "session-a")
    _start(ledger, tmp_path, "session-b")

    for session_id in ("session-a", "session-b"):
        assert ledger.record_tool_call(
            session_id=session_id,
            turn_id="turn-1",
            api_request_id="request-1",
            tool_call_id="call-same",
            tool_name="terminal",
            duration_ms=1,
            outcome="success",
        ) is True
    assert ledger.record_tool_call(
        session_id="session-a",
        turn_id="turn-1",
        api_request_id="request-1",
        tool_call_id="call-same",
        tool_name="terminal",
        duration_ms=1,
        outcome="success",
    ) is False
    assert ledger.record_tool_call(
        session_id="session-a",
        turn_id="turn-1",
        api_request_id="request-2",
        tool_call_id="call-same",
        tool_name="terminal",
        duration_ms=1,
        outcome="success",
    ) is True

    assert len(ledger.tool_calls("session-a")) == 2
    assert len(ledger.tool_calls("session-b")) == 1


def test_tool_and_coordination_observation_roll_back_atomically(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _start(ledger, tmp_path, "session-a")
    with sqlite3.connect(ledger.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER force_coordination_failure
            BEFORE INSERT ON coordination_events
            BEGIN
                SELECT RAISE(ABORT, 'forced coordination failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced coordination failure"):
        ledger.record_tool_observation(
            session_id="session-a",
            tool_call_id="execution-atomic",
            tool_name="execution",
            duration_ms=3,
            outcome="error",
            coordination={
                "system": "execution",
                "action": "start",
                "phase": "pre_admission",
                "outcome": "invalid_request",
            },
        )

    assert ledger.tool_calls("session-a") == []
    assert ledger.coordination_events("session-a") == []


def test_abandoned_and_interrupted_sessions_require_reconciliation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _start(ledger, tmp_path, "old", runtime_instance="old-runtime", process_id=99_999)
    _start(ledger, tmp_path, "current", runtime_instance="current-runtime", process_id=os.getpid())

    assert ledger.mark_abandoned_sessions(
        current_session_id="current",
        current_runtime_instance="current-runtime",
        current_process_id=os.getpid(),
        process_alive=lambda _pid: False,
    ) == 1
    old = ledger.get_session("old")
    assert old is not None
    assert old["status"] == "reconciliation_required"

    ledger.record_turn_outcome("current", completed=False, interrupted=True)
    ledger.finalize_session("current")
    current = ledger.get_session("current")
    assert current is not None
    assert current["status"] == "reconciliation_required"
    assert current["last_turn_outcome"] == "interrupted"
