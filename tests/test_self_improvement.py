"""Behavioral contract for the v0.20.0 Aether self-improvement bootstrap."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from olympus_v3.self_improvement.evidence import (
    aggregate_next_version_signal,
    render_release_evidence,
)
from olympus_v3.self_improvement.hooks import (
    on_post_llm_call,
    on_post_tool_call,
    on_pre_llm_call,
    on_session_end,
    on_session_finalize,
    on_session_start,
    register,
    reset_runtime_state,
)
from olympus_v3.self_improvement.ledger import SelfImprovementLedger
from olympus_v3.self_improvement.manifest import load_cycle_manifest, verify_project_identity

CANDIDATE_VERSION = "0.20.0"
BASELINE_COMMIT = "a" * 40


def _manifest_payload() -> dict:
    return {
        "schema_version": 1,
        "status": "implementation_in_progress",
        "approved_on": "2026-07-28",
        "owner": "Christopher (DarkArty07)",
        "semver": {
            "last_official_release": "0.18.2",
            "technical_predecessor": "0.19.5",
            "technical_predecessor_state": "closed_viable_bounded_unpublished",
            "candidate_version": CANDIDATE_VERSION,
            "candidate_name": "Self-Improvement Cycle Bootstrap",
            "next_minor_scope": "undecided_pending_evidence",
        },
        "hypothesis": {
            "statement": "Every verified Aether session contributes deterministic evidence without presuming the next minor."
        },
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


def _make_project(tmp_path: Path, *, name: str = "aether") -> Path:
    root = tmp_path / name
    manifest = root / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(yaml.safe_dump(_manifest_payload(), sort_keys=False), encoding="utf-8")
    (root / "AGENTS.md").write_text("# Aether Agents — Project Context\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "olympus-mcp"\n', encoding="utf-8")
    git = root / ".git"
    git.mkdir()
    (git / "HEAD").write_text(BASELINE_COMMIT + "\n", encoding="utf-8")
    return root


def _ledger(root: Path) -> SelfImprovementLedger:
    return SelfImprovementLedger(root / ".aether" / "self_improvement.db")


@pytest.fixture(autouse=True)
def isolated_runtime_state():
    reset_runtime_state()
    yield
    reset_runtime_state()


class TestCycleManifest:
    def test_loads_strict_approved_candidate_contract(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)

        manifest = load_cycle_manifest(root)

        assert manifest.schema_version == 1
        assert manifest.candidate_version == CANDIDATE_VERSION
        assert manifest.next_minor_scope == "undecided_pending_evidence"
        assert manifest.logical_provider == "custom:aether-router"
        assert manifest.ledger_path == root / ".aether" / "self_improvement.db"
        assert manifest.digest.startswith("sha256:")
        assert len(manifest.digest) == 71

    def test_rejects_manifest_that_presumes_a_next_minor_architecture(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        path = root / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml"
        payload = _manifest_payload()
        payload["semver"]["next_minor_scope"] = "llm_harmonia"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

        assert verify_project_identity(root) is None
        assert not (root / ".aether").exists()

    def test_rejects_contract_that_authorizes_activation_or_release(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        path = root / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml"
        payload = _manifest_payload()
        payload["authorization"]["runtime_restart"] = "authorized"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

        assert verify_project_identity(root) is None
        assert not (root / ".aether").exists()

    def test_non_aether_project_never_initializes_storage(self, tmp_path: Path) -> None:
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        (foreign / "pyproject.toml").write_text('[project]\nname = "foreign"\n', encoding="utf-8")

        assert verify_project_identity(foreign) is None
        assert not (foreign / ".aether").exists()


class TestSelfImprovementLedger:
    def test_session_initialization_is_exactly_once(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        manifest = load_cycle_manifest(root)
        ledger = _ledger(root)
        fields = {
            "session_id": "session-a",
            "project_root": root,
            "candidate_version": manifest.candidate_version,
            "manifest_digest": manifest.digest,
            "baseline_commit": BASELINE_COMMIT,
            "logical_provider": manifest.logical_provider,
            "requested_model": "gpt-5.6-sol",
            "platform": "cli",
        }

        assert ledger.start_session(**fields) is True
        assert ledger.start_session(**fields) is False
        assert ledger.session_count() == 1
        assert ledger.get_session("session-a")["status"] == "active"

    def test_abandoned_session_requires_reconciliation(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        manifest = load_cycle_manifest(root)
        ledger = _ledger(root)
        common = {
            "project_root": root,
            "candidate_version": manifest.candidate_version,
            "manifest_digest": manifest.digest,
            "baseline_commit": BASELINE_COMMIT,
            "logical_provider": manifest.logical_provider,
            "requested_model": "gpt-5.6-sol",
            "platform": "cli",
        }
        ledger.start_session(session_id="old", runtime_instance="old-runtime", process_id=os.getpid(), **common)
        ledger.start_session(session_id="new", runtime_instance="new-runtime", process_id=os.getpid(), **common)

        assert ledger.mark_abandoned_sessions(
            current_session_id="new",
            current_runtime_instance="new-runtime",
            current_process_id=os.getpid(),
            protected_session_ids=set(),
        ) == 1
        assert ledger.get_session("old")["status"] == "reconciliation_required"
        assert ledger.get_session("new")["status"] == "active"

    def test_live_concurrent_session_is_not_reconciled(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        manifest = load_cycle_manifest(root)
        ledger = _ledger(root)
        common = {
            "project_root": root,
            "candidate_version": manifest.candidate_version,
            "manifest_digest": manifest.digest,
            "baseline_commit": BASELINE_COMMIT,
            "logical_provider": manifest.logical_provider,
            "requested_model": "gpt-5.6-sol",
            "platform": "cli",
        }
        ledger.start_session(session_id="live", runtime_instance="live-runtime", process_id=99999, **common)
        ledger.start_session(
            session_id="current", runtime_instance="current-runtime", process_id=os.getpid(), **common
        )

        reconciled = ledger.mark_abandoned_sessions(
            current_session_id="current",
            current_runtime_instance="current-runtime",
            current_process_id=os.getpid(),
            protected_session_ids=set(),
            process_alive=lambda pid: pid == 99999,
        )

        assert reconciled == 0
        assert ledger.get_session("live")["status"] == "active"

    def test_interrupted_session_cannot_be_relabelled_finalized(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        manifest = load_cycle_manifest(root)
        ledger = _ledger(root)
        ledger.start_session(
            session_id="interrupted",
            project_root=root,
            candidate_version=manifest.candidate_version,
            manifest_digest=manifest.digest,
            baseline_commit=BASELINE_COMMIT,
            logical_provider=manifest.logical_provider,
            requested_model="gpt-5.6-sol",
            platform="cli",
        )

        ledger.record_turn_outcome("interrupted", completed=False, interrupted=True)
        ledger.finalize_session("interrupted")

        session = ledger.get_session("interrupted")
        assert session["status"] == "reconciliation_required"
        assert session["last_turn_outcome"] == "interrupted"
        assert session["finalized_at"] is not None

    def test_coordination_observation_rolls_back_as_one_transaction(self, tmp_path: Path) -> None:
        root = _make_project(tmp_path)
        manifest = load_cycle_manifest(root)
        ledger = _ledger(root)
        ledger.start_session(
            session_id="session-a",
            project_root=root,
            candidate_version=manifest.candidate_version,
            manifest_digest=manifest.digest,
            baseline_commit=BASELINE_COMMIT,
            logical_provider=manifest.logical_provider,
            requested_model="gpt-5.6-sol",
            platform="cli",
        )
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
                tool_call_id="harmonia-atomic",
                tool_name="mcp__olympus_v3__harmonia",
                duration_ms=3,
                outcome="error",
                coordination={
                    "system": "harmonia",
                    "action": "start",
                    "phase": "pre_admission",
                    "outcome": "invalid_request",
                },
            )

        assert ledger.tool_calls("session-a") == []
        assert ledger.coordination_events("session-a") == []


class TestPluginHooks:
    def test_new_session_initializes_once_and_injects_context_without_memory(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)

        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")
        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")
        context = on_pre_llm_call(
            session_id="session-a",
            user_message="Implement the feature",
            conversation_history=[],
            is_first_turn=True,
            model="gpt-5.6-sol",
            platform="cli",
        )

        ledger = _ledger(root)
        assert ledger.session_count() == 1
        assert context is not None
        assert context["context"].startswith("[Aether Self-Improvement Cycle]")
        assert "Candidate: v0.20.0" in context["context"]
        assert "custom:aether-router" in context["context"]
        assert "talk_to fallback is forbidden" in context["context"]
        assert "Use Harmonia" not in context["context"]
        assert "Orca transition candidate" in context["context"]
        assert "Next minor architecture: undecided" in context["context"]

    def test_context_is_only_injected_on_first_turn(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)
        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")

        assert on_pre_llm_call(
            session_id="session-a",
            user_message="continue",
            conversation_history=[],
            is_first_turn=False,
            model="gpt-5.6-sol",
            platform="cli",
        ) is None

    def test_tool_measurement_never_persists_arguments_results_or_secrets(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)
        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")
        secret = "sk-super-secret-material"

        on_post_tool_call(
            tool_name="terminal",
            args={"command": "curl", "authorization": secret},
            result='{"output":"' + secret + '","exit_code":0}',
            task_id="task-a",
            session_id="session-a",
            tool_call_id="tool-a",
            duration_ms=12,
        )
        on_post_tool_call(
            tool_name="terminal",
            args={"command": "curl", "authorization": secret},
            result='{"output":"' + secret + '","exit_code":0}',
            task_id="task-a",
            session_id="session-a",
            tool_call_id="tool-a",
            duration_ms=12,
        )

        ledger = _ledger(root)
        rows = ledger.tool_calls("session-a")
        assert rows == [{"tool_call_id": "tool-a", "tool_name": "terminal", "duration_ms": 12, "outcome": "success"}]
        ledger.checkpoint()
        assert all(secret.encode() not in path.read_bytes() for path in (root / ".aether").glob("self_improvement.db*"))

    def test_missing_router_telemetry_remains_unknown(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)
        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")

        on_post_llm_call(
            session_id="session-a",
            user_message="hello",
            assistant_response="response that must not be stored",
            conversation_history=[],
            model="gpt-5.6-sol",
            platform="cli",
            turn_id="turn-a",
        )

        row = _ledger(root).model_calls("session-a")[0]
        assert row["requested_model"] == "gpt-5.6-sol"
        assert row["resolved_route"] is None
        assert row["resolved_model"] is None
        assert row["input_tokens"] is None
        assert row["output_tokens"] is None
        db_text = (root / ".aether" / "self_improvement.db").read_bytes()
        assert b"response that must not be stored" not in db_text

    def test_interruption_and_finalize_preserve_reconciliation_state(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)
        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")

        on_session_end(
            session_id="session-a",
            completed=False,
            interrupted=True,
            model="gpt-5.6-sol",
            platform="cli",
        )
        on_session_finalize(session_id="session-a", platform="cli")

        session = _ledger(root).get_session("session-a")
        assert session["status"] == "reconciliation_required"
        assert session["finalized_at"] is not None

    def test_new_session_recovers_prior_unfinalized_session(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)
        on_session_start("old", model="gpt-5.6-sol", platform="cli")
        reset_runtime_state()

        on_session_start("new", model="gpt-5.6-sol", platform="cli")

        ledger = _ledger(root)
        assert ledger.get_session("old")["status"] == "reconciliation_required"
        assert ledger.get_session("new")["status"] == "active"

    def test_concurrent_sessions_in_same_runtime_remain_active(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)

        on_session_start("first", model="gpt-5.6-sol", platform="cli")
        on_session_start("second", model="gpt-5.6-sol", platform="cli")

        ledger = _ledger(root)
        assert ledger.get_session("first")["status"] == "active"
        assert ledger.get_session("second")["status"] == "active"

    def test_harmonia_outcomes_are_classified_without_contract_payloads(self, tmp_path: Path, monkeypatch) -> None:
        root = _make_project(tmp_path)
        monkeypatch.chdir(root)
        on_session_start("session-a", model="gpt-5.6-sol", platform="cli")
        secret = "«redacted:sk-…»"

        on_post_tool_call(
            tool_name="mcp__olympus_v3__harmonia",
            args={"action": "start", "contract": {"objective": secret}},
            result='{"success":false,"error":{"code":"invalid_request"}}',
            task_id="task-a",
            session_id="session-a",
            tool_call_id="harmonia-1",
            duration_ms=5,
        )
        on_post_tool_call(
            tool_name="mcp__olympus_v3__harmonia",
            args={"action": "start", "contract": {"objective": secret}},
            result='{"success":false,"error":{"code":"feature_disabled"}}',
            task_id="task-a",
            session_id="session-a",
            tool_call_id="harmonia-2",
            duration_ms=7,
        )

        events = _ledger(root).coordination_events("session-a")
        assert events == [
            {
                "event_id": "harmonia-1",
                "system": "harmonia",
                "action": "start",
                "phase": "pre_admission",
                "outcome": "invalid_request",
                "duration_ms": 5,
            },
            {
                "event_id": "harmonia-2",
                "system": "harmonia",
                "action": "start",
                "phase": "pre_admission",
                "outcome": "feature_disabled",
                "duration_ms": 7,
            },
        ]
        _ledger(root).checkpoint()
        assert all(secret.encode() not in path.read_bytes() for path in (root / ".aether").glob("self_improvement.db*"))

    def test_foreign_workspace_does_not_create_or_mutate_aether_storage(self, tmp_path: Path, monkeypatch) -> None:
        aether = _make_project(tmp_path)
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        monkeypatch.chdir(foreign)
        monkeypatch.setenv("HERMES_HOME", str(aether / "home"))

        on_session_start("foreign-session", model="gpt-5.6-sol", platform="cli")

        assert not (foreign / ".aether").exists()
        assert not (aether / ".aether").exists()

    def test_environment_cannot_redirect_a_foreign_workspace_into_aether(self, tmp_path: Path, monkeypatch) -> None:
        aether = _make_project(tmp_path / "canonical")
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        (foreign / ".git").mkdir()
        monkeypatch.chdir(foreign)
        monkeypatch.setenv("AETHER_PROJECT_ROOT", str(aether))

        on_session_start("foreign-env-session", model="gpt-5.6-sol", platform="cli")

        assert not (foreign / ".aether").exists()
        assert not (aether / ".aether").exists()

    def test_nested_foreign_repository_cannot_inherit_parent_aether_identity(self, tmp_path: Path, monkeypatch) -> None:
        aether = _make_project(tmp_path)
        foreign = aether / "nested-foreign"
        foreign.mkdir()
        (foreign / ".git").mkdir()
        monkeypatch.chdir(foreign)

        on_session_start("nested-foreign-session", model="gpt-5.6-sol", platform="cli")

        assert not (foreign / ".aether").exists()
        assert not (aether / ".aether").exists()

    def test_aether_subdirectory_resolves_the_nearest_repository_root(self, tmp_path: Path, monkeypatch) -> None:
        aether = _make_project(tmp_path)
        subdirectory = aether / "src" / "package"
        subdirectory.mkdir(parents=True)
        monkeypatch.chdir(subdirectory)

        on_session_start("aether-subdirectory-session", model="gpt-5.6-sol", platform="cli")

        session = _ledger(aether).get_session("aether-subdirectory-session")
        assert session is not None
        assert session["status"] == "active"

    def test_registers_only_observer_and_context_hooks(self) -> None:
        ctx = Mock()

        register(ctx)

        names = [call.args[0] for call in ctx.register_hook.call_args_list]
        assert names == [
            "on_session_start",
            "pre_llm_call",
            "post_tool_call",
            "post_llm_call",
            "on_session_end",
            "on_session_finalize",
        ]
        assert "pre_tool_call" not in names


def test_plugin_is_discoverable_but_not_enabled_in_template() -> None:
    root = Path(__file__).resolve().parents[1]
    plugin_manifest = yaml.safe_load(
        (root / "home" / "plugins" / "aether-self-improvement" / "plugin.yaml").read_text(encoding="utf-8")
    )
    config = yaml.safe_load((root / "home" / "config.yaml.template").read_text(encoding="utf-8"))

    assert plugin_manifest["name"] == "aether-self-improvement"
    assert set(plugin_manifest["provides_hooks"]) == {
        "on_session_start",
        "pre_llm_call",
        "post_tool_call",
        "post_llm_call",
        "on_session_end",
        "on_session_finalize",
    }
    assert "aether-self-improvement" not in config.get("plugins", {}).get("enabled", [])
    assert config["mcp_servers"]["olympus_v3"]["tools"]["exclude"] == ["talk_to"]


def test_ledger_schema_contains_no_payload_columns(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    ledger = _ledger(root)
    ledger.ensure_schema()

    with sqlite3.connect(ledger.path) as connection:
        for table in ("cycle_sessions", "tool_calls", "model_calls", "coordination_events"):
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            assert not {"args", "arguments", "result", "response", "prompt", "content"} & columns


def test_ledger_is_private_and_refuses_symlinked_storage(tmp_path: Path) -> None:
    root = _make_project(tmp_path / "private")
    ledger = _ledger(root)
    ledger.ensure_schema()
    assert ledger.path.stat().st_mode & 0o777 == 0o600

    linked_root = _make_project(tmp_path / "linked")
    external = tmp_path / "external"
    external.mkdir()
    (linked_root / ".aether").symlink_to(external, target_is_directory=True)
    linked_ledger = _ledger(linked_root)

    with pytest.raises(RuntimeError, match="must not be a symlink"):
        linked_ledger.ensure_schema()
    assert not (external / "self_improvement.db").exists()


def test_release_evidence_is_deterministic_and_never_approves_a_version(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    manifest = load_cycle_manifest(root)
    ledger = _ledger(root)
    common = {
        "project_root": root,
        "candidate_version": manifest.candidate_version,
        "manifest_digest": manifest.digest,
        "baseline_commit": BASELINE_COMMIT,
        "logical_provider": manifest.logical_provider,
        "requested_model": "gpt-5.6-sol",
        "platform": "cli",
        "runtime_instance": "evidence-runtime",
        "process_id": os.getpid(),
    }
    ledger.start_session(session_id="complete", **common)
    ledger.record_turn_outcome("complete", completed=True, interrupted=False)
    ledger.finalize_session("complete", next_version_signal="PATCH_CANDIDATE")
    ledger.start_session(session_id="needs-review", **common)
    ledger.record_turn_outcome("needs-review", completed=False, interrupted=True)

    assert aggregate_next_version_signal(ledger) == "REQUIRES_MORE_EVIDENCE"
    first = render_release_evidence(manifest, ledger)
    second = render_release_evidence(manifest, ledger)

    assert first == second
    assert "# v0.20.0 Self-Improvement Evidence" in first
    assert "Manifest digest:" in first
    assert "REQUIRES_MORE_EVIDENCE" in first
    assert "This evidence does not approve a merge, tag, release, deployment, or next-minor architecture." in first
