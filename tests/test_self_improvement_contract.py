"""Contract regressions for defects found by the v0.20.0 external logic audit.

These live beside `test_self_improvement.py` rather than inside it on purpose:
the audit's central finding was that an implementation and the tests that judge
it were changed together, so the original 26-case contract stays untouched and
every correction has to satisfy it as well as the cases below.

Each test names the audit finding it pins.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import yaml

from olympus_v3.coordination.harmonia_contract import HARMONIA_ERROR_CODES, public_error
from olympus_v3.coordination.harmonia_service import _STATES as KERNEL_STATES
from olympus_v3.self_improvement import hooks as H
from olympus_v3.self_improvement.ledger import LedgerSchemaError, SelfImprovementLedger

BASELINE_COMMIT = "a" * 40


def _manifest_payload() -> dict:
    return {
        "schema_version": 1,
        "status": "implemented_default_off",
        "approved_on": "2026-07-28",
        "owner": "Christopher (DarkArty07)",
        "semver": {
            "last_official_release": "0.18.2",
            "technical_predecessor": "0.19.5",
            "technical_predecessor_state": "closed_viable_bounded_unpublished",
            "candidate_version": "0.20.0",
            "candidate_name": "Self-Improvement Instrumentation",
            "next_minor_scope": "undecided_pending_evidence",
        },
        "hypothesis": {"statement": "Deterministic evidence without presuming the next minor."},
        "runtime_contract": {
            "project_root_required": True,
            "talk_to_available_to_hermes": False,
            "harmonia_when_applicable": True,
            "ceremonial_harmonia_runs_forbidden": True,
            "direct_framework_repair_inside_aether": True,
            "harmonia_retry_after_framework_repair": True,
            "cross_project_aether_mutation_forbidden": True,
            "direct_takeover_requires_cleanup_verification": True,
        },
        "provider": {
            "logical_provider": "custom:aether-router",
            "current_hermes_model": "gpt-5.6-sol",
            "provider_is_acceptance_authority": False,
            "missing_telemetry_value": "unknown",
            "secrets_in_evidence_forbidden": True,
        },
        "next_version_signals": {
            "allowed": ["NONE", "PATCH_CANDIDATE", "MINOR_CAPABILITY_SIGNAL", "REQUIRES_MORE_EVIDENCE"],
            "automatically_approves_version": False,
            "product_owner_approval_required": True,
            "llm_coordinator_presumed": False,
        },
        "persistence": {
            "decision": "docs/decisions/PDR-0009-semver-self-improvement-cycle.md",
            "operating_model": "docs/knowledge/SELF_IMPROVEMENT_CYCLE.md",
            "incoming_agent_context": "AGENTS.md",
            "operational_ledger_target": ".aether/self_improvement.db",
            "release_evidence_target": "docs/releases/v0.20.0/SELF_IMPROVEMENT_EVIDENCE.md",
            "context_projection_is_sole_authority": False,
        },
        "authorization": {
            "documentation_alignment": "authorized",
            "implementation_plan": "authorized",
            "source_or_plugin_implementation": "authorized",
            "harmonia_activation": "not_authorized",
            "coordination_key_creation": "not_authorized",
            "runtime_restart": "not_authorized",
            "merge": "not_authorized",
            "tag": "not_authorized",
            "release": "not_authorized",
            "deployment": "not_authorized",
            "publication": "not_authorized",
        },
    }


def _make_project(root: Path, *, mutate=None) -> Path:
    manifest = root / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = _manifest_payload()
    if mutate is not None:
        mutate(payload)
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    (root / "AGENTS.md").write_text("# Aether Agents — Project Context\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "olympus-mcp"\n', encoding="utf-8")
    git = root / ".git"
    git.mkdir(exist_ok=True)
    (git / "HEAD").write_text(BASELINE_COMMIT + "\n", encoding="utf-8")
    return root


def _ledger(root: Path) -> SelfImprovementLedger:
    return SelfImprovementLedger(root / ".aether" / "self_improvement.db")


@pytest.fixture(autouse=True)
def isolated_runtime_state():
    H.reset_runtime_state()
    yield
    H.reset_runtime_state()


# --------------------------------------------------------------------------
# F-01 — the classifier must match Harmonia's real wire contract
# --------------------------------------------------------------------------


def test_post_admission_state_set_tracks_the_kernel() -> None:
    """A kernel state rename must break the build, not silently degrade evidence."""

    assert H._POST_ADMISSION_STATES == KERNEL_STATES


def test_every_public_error_code_is_classified() -> None:
    for code in HARMONIA_ERROR_CODES:
        envelope = json.dumps(public_error("start", code))
        phase, outcome, _ = H._harmonia_classification(envelope)

        assert outcome == code, f"{code} lost its identity"
        assert phase != "unknown", f"{code} was not assigned an admission phase"


def test_pre_admission_codes_are_the_only_ones_treated_as_effect_free() -> None:
    """Anything that can surface after admission must not be downgraded."""

    for code in HARMONIA_ERROR_CODES:
        phase, _, _ = H._harmonia_classification(json.dumps(public_error("start", code)))
        expected = "pre_admission" if code in H._PRE_ADMISSION_CODES else "post_admission"

        assert phase == expected, f"{code} classified as {phase}"


def test_every_durable_state_is_classified_post_admission() -> None:
    for state in KERNEL_STATES:
        envelope = json.dumps({"action": "status", "ok": True, "state": state, "error": None})
        phase, outcome, _ = H._harmonia_classification(envelope)

        assert (phase, outcome) == ("post_admission", state)


def test_uncertain_durable_effect_is_preserved() -> None:
    envelope = json.dumps(
        {
            "action": "status",
            "ok": True,
            "state": "reconciliation_required",
            "uncertainty": "terminal_evidence_absent",
            "error": None,
        }
    )

    assert H._harmonia_classification(envelope) == (
        "post_admission",
        "reconciliation_required",
        "terminal_evidence_absent",
    )


# --------------------------------------------------------------------------
# F-02 — a failing tool result is never recorded as a success
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        '{"success": false}',
        '{"ok": false, "error": null}',
        '{"status": "failed"}',
        '{"ok": false, "state": "reconciliation_required"}',
        '{"exit_code": 1}',
    ],
)
def test_failure_payloads_are_never_success(payload: str) -> None:
    assert H._tool_outcome(payload) == "error"


def test_host_status_wins_over_local_parsing() -> None:
    """Hermes already classifies every result; re-deriving it was strictly worse."""

    assert H._tool_outcome('{"anything": true}', "error") == "error"
    assert H._tool_outcome('{"anything": true}', "blocked") == "error"
    assert H._tool_outcome('{"exit_code": 0}', "ok") == "success"


# --------------------------------------------------------------------------
# F-03 — tool identity is scoped, not global
# --------------------------------------------------------------------------


def test_identical_tool_call_ids_in_two_sessions_are_both_recorded(tmp_path: Path, monkeypatch) -> None:
    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)
    H.on_session_start("session-a", model="m", platform="cli")
    H.on_session_start("session-b", model="m", platform="cli")

    for session_id in ("session-a", "session-b"):
        H.on_post_tool_call(
            tool_name="terminal",
            args={},
            result='{"exit_code": 0}',
            task_id="t",
            session_id=session_id,
            tool_call_id="call_deadbeef",
            duration_ms=1,
        )

    ledger = _ledger(root)
    assert len(ledger.tool_calls("session-a")) == 1
    assert len(ledger.tool_calls("session-b")) == 1
    assert ledger.evidence_counts()["tool_calls"] == 2


def test_the_same_command_repeated_in_a_later_turn_is_counted_again(tmp_path: Path, monkeypatch) -> None:
    """The verify-then-retry step reruns one command; both runs are evidence."""

    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)
    H.on_session_start("session-a", model="m", platform="cli")

    for turn in ("turn-1", "turn-2"):
        H.on_post_tool_call(
            tool_name="terminal",
            args={"command": "pytest -q"},
            result='{"exit_code": 0}',
            task_id="t",
            session_id="session-a",
            tool_call_id="call_samecontent",
            turn_id=turn,
            duration_ms=1,
        )

    assert len(_ledger(root).tool_calls("session-a")) == 2


# --------------------------------------------------------------------------
# F-15 / F-16 — ledger identity and durability
# --------------------------------------------------------------------------


def test_reused_session_id_under_a_different_manifest_is_refused(tmp_path: Path) -> None:
    root = _make_project(tmp_path / "aether")
    ledger = _ledger(root)
    common = {
        "project_root": root,
        "candidate_version": "0.20.0",
        "logical_provider": "custom:aether-router",
        "requested_model": "m",
        "platform": "cli",
    }
    ledger.start_session(session_id="s", manifest_digest="sha256:aaa", baseline_commit=BASELINE_COMMIT, **common)

    with pytest.raises(LedgerSchemaError, match="different manifest digest"):
        ledger.start_session(
            session_id="s", manifest_digest="sha256:bbb", baseline_commit=BASELINE_COMMIT, **common
        )


def test_incompatible_ledger_schema_fails_loudly(tmp_path: Path) -> None:
    """A silent no-op left a healthy-looking session with zero evidence."""

    root = _make_project(tmp_path / "aether")
    (root / ".aether").mkdir()
    path = root / ".aether" / "self_improvement.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE cycle_sessions (session_id TEXT PRIMARY KEY, legacy_col TEXT)")

    with pytest.raises(LedgerSchemaError, match="ledger schema"):
        SelfImprovementLedger(path).ensure_schema()


