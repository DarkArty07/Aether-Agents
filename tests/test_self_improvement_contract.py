"""Contract regressions for defects found by the v0.20.0 external logic audit.

These live beside `test_self_improvement.py` rather than inside it on purpose:
the audit's central finding was that an implementation and the tests that judge
it were changed together, so the original 26-case contract stays untouched and
every correction has to satisfy it as well as the cases below.

Each test names the audit finding it pins.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest
import yaml

from olympus_v3.coordination.harmonia_contract import HARMONIA_ERROR_CODES, public_error
from olympus_v3.coordination.harmonia_service import _STATES as KERNEL_STATES
from olympus_v3.self_improvement import hooks as H
from olympus_v3.self_improvement.evidence import render_release_evidence
from olympus_v3.self_improvement.ledger import LedgerSchemaError, SelfImprovementLedger
from olympus_v3.self_improvement.manifest import ManifestError, load_cycle_manifest

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


def test_same_deterministic_call_repeated_in_one_turn_is_counted_per_request(tmp_path: Path, monkeypatch) -> None:
    """Tool-call indices reset on each model request inside one turn; request identity must disambiguate retries."""

    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)
    H.on_session_start("session-a", model="m", platform="cli")

    for request_id in ("request-before", "request-after"):
        H.on_post_tool_call(
            tool_name="terminal",
            args={"command": "pytest -q"},
            result='{"exit_code": 0}',
            task_id="t",
            session_id="session-a",
            tool_call_id="call_samecontent",
            turn_id="turn-1",
            api_request_id=request_id,
            duration_ms=1,
        )

    assert len(_ledger(root).tool_calls("session-a")) == 2


def test_duplicate_observer_delivery_remains_idempotent(tmp_path: Path, monkeypatch) -> None:
    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)
    H.on_session_start("session-a", model="m", platform="cli")

    kwargs = {
        "tool_name": "terminal",
        "args": {"command": "pytest -q"},
        "result": '{"exit_code": 0}',
        "task_id": "t",
        "session_id": "session-a",
        "tool_call_id": "call_samecontent",
        "turn_id": "turn-1",
        "api_request_id": "request-1",
        "duration_ms": 1,
    }
    H.on_post_tool_call(**kwargs)
    H.on_post_tool_call(**kwargs)

    assert len(_ledger(root).tool_calls("session-a")) == 1


# --------------------------------------------------------------------------
# F-06 — explicit project roots are assertions, never cross-project authority
# --------------------------------------------------------------------------


def test_explicit_project_root_cannot_redirect_a_foreign_repository(tmp_path: Path, monkeypatch) -> None:
    aether = _make_project(tmp_path / "canonical")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / ".git").mkdir()
    monkeypatch.chdir(foreign)

    H.on_session_start(
        "foreign-explicit-root",
        model="m",
        platform="cli",
        project_root=aether,
    )

    assert not (foreign / ".aether").exists()
    assert not (aether / ".aether").exists()


def test_explicit_project_root_may_confirm_the_discovered_aether_root(tmp_path: Path, monkeypatch) -> None:
    aether = _make_project(tmp_path / "canonical")
    nested = aether / "src" / "package"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    H.on_session_start(
        "matching-explicit-root",
        model="m",
        platform="cli",
        project_root=aether,
    )

    assert _ledger(aether).get_session("matching-explicit-root") is not None


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


# --------------------------------------------------------------------------
# F-11 — a continued session still produces evidence
# --------------------------------------------------------------------------


def test_session_evidence_survives_a_continuation(tmp_path: Path, monkeypatch) -> None:
    """`on_session_start` never fires on continuation, so later hooks must initialize."""

    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)

    H.on_post_tool_call(
        tool_name="terminal",
        args={},
        result='{"exit_code": 0}',
        task_id="t",
        session_id="resumed",
        tool_call_id="call_1",
        duration_ms=1,
    )

    ledger = _ledger(root)
    assert ledger.get_session("resumed") is not None
    assert len(ledger.tool_calls("resumed")) == 1


def test_post_llm_call_tolerates_the_exact_kwargs_hermes_sends(tmp_path: Path, monkeypatch) -> None:
    """Payload pinned to `agent/turn_finalizer.py`'s post_llm_call invocation."""

    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)

    H.on_post_llm_call(
        session_id="resumed",
        task_id="task-1",
        turn_id="turn-1",
        user_message="do the thing",
        assistant_response="done",
        conversation_history=[],
        model="gpt-5.6-sol",
        platform="cli",
    )

    rows = _ledger(root).model_calls("resumed")
    assert len(rows) == 1
    assert rows[0]["requested_model"] == "gpt-5.6-sol"


# --------------------------------------------------------------------------
# F-12 / F-13 — baselines are attributable
# --------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _seeded_repo(root: Path) -> Path:
    root.mkdir()
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "audit@example.invalid", cwd=root)
    _git("config", "user.name", "audit", cwd=root)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "seed.txt", cwd=root)
    _git("commit", "-qm", "seed", cwd=root)
    return root


def test_git_head_resolves_a_linked_worktree(tmp_path: Path) -> None:
    """Candidate isolation runs in worktrees, where `.git` is a file."""

    repo = _seeded_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    _git("worktree", "add", "-q", "-b", "candidate", str(linked), cwd=repo)

    expected = subprocess.run(
        ["git", "-C", str(linked), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()

    assert H._git_head(linked) == expected
    assert H._git_head(repo) == expected


def test_baseline_records_whether_the_worktree_was_clean(tmp_path: Path) -> None:
    repo = _seeded_repo(tmp_path / "repo")

    assert H._baseline_dirty_digest(repo) == "clean"

    (repo / "unrelated.txt").write_text("someone else's work\n", encoding="utf-8")
    dirty = H._baseline_dirty_digest(repo)

    assert dirty.startswith("dirty:1:sha256:")


# --------------------------------------------------------------------------
# F-14 — an interruption is recorded, not latched forever
# --------------------------------------------------------------------------


def test_interrupted_turn_does_not_permanently_poison_the_session(tmp_path: Path, monkeypatch) -> None:
    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)
    H.on_session_start("s", model="m", platform="cli")
    ledger = _ledger(root)

    H.on_session_end(session_id="s", completed=True, interrupted=False, model="m", platform="cli")
    H.on_session_end(session_id="s", completed=False, interrupted=True, model="m", platform="cli")
    assert ledger.get_session("s")["status"] == "reconciliation_required"

    H.on_session_end(session_id="s", completed=True, interrupted=False, model="m", platform="cli")
    assert ledger.get_session("s")["status"] == "active"

    H.on_session_finalize(session_id="s", platform="cli")
    session = ledger.get_session("s")

    assert session["status"] == "finalized"
    # The interruption stays visible even though the session recovered.
    assert ledger.turn_outcomes("s") == ["completed", "interrupted", "completed"]


# --------------------------------------------------------------------------
# F-07 / F-19 — manifest identity and mid-session drift
# --------------------------------------------------------------------------


def test_candidate_version_must_match_its_release_directory(tmp_path: Path) -> None:
    def bump(payload: dict) -> None:
        payload["semver"]["candidate_version"] = "9.9.9"

    root = _make_project(tmp_path / "aether", mutate=bump)

    with pytest.raises(ManifestError, match="does not match its release directory"):
        load_cycle_manifest(root)


def test_manifest_change_during_a_session_is_marked(tmp_path: Path, monkeypatch) -> None:
    root = _make_project(tmp_path / "aether")
    monkeypatch.chdir(root)
    H.on_session_start("s", model="m", platform="cli")

    manifest_path = root / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["semver"]["candidate_name"] = "Swapped Mid-Session"
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    H.on_session_finalize(session_id="s", platform="cli")

    assert _ledger(root).get_session("s")["manifest_drifted"] == 1


def test_identity_failure_with_a_manifest_present_is_reported(tmp_path: Path, monkeypatch, caplog) -> None:
    """Granting a gate must not look identical to a corrupt file."""

    def authorize(payload: dict) -> None:
        payload["authorization"]["harmonia_activation"] = "authorized"

    root = _make_project(tmp_path / "aether", mutate=authorize)
    monkeypatch.chdir(root)

    with caplog.at_level("WARNING", logger="olympus_v3.self_improvement"):
        H.on_session_start("s", model="m", platform="cli")

    assert not (root / ".aether").exists()
    assert any("failed verification" in record.message for record in caplog.records)


# --------------------------------------------------------------------------
# F-24 — the evidence states what it cannot establish
# --------------------------------------------------------------------------


def test_release_evidence_declares_its_own_limits(tmp_path: Path) -> None:
    root = _make_project(tmp_path / "aether")
    manifest = load_cycle_manifest(root)
    ledger = _ledger(root)
    ledger.start_session(
        session_id="s",
        project_root=root,
        candidate_version=manifest.candidate_version,
        manifest_digest=manifest.digest,
        baseline_commit=BASELINE_COMMIT,
        baseline_dirty_digest="dirty:3:sha256:" + "0" * 64,
        logical_provider=manifest.logical_provider,
        requested_model="m",
        platform="cli",
        process_id=os.getpid(),
    )

    rendered = render_release_evidence(manifest, ledger)

    assert "Activity volume is not improvement." in rendered
    assert "no causal claim about" in rendered
    assert "Sessions without a clean baseline worktree: 1" in rendered
