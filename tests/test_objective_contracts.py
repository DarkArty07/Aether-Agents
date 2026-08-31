"""Objective Contract authoring and Hermes plugin regressions."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from aether_agents.objective_contracts import (
    REQUIRED_SECTIONS,
    ContractError,
    ObjectiveContractStore,
)
from aether_agents.observation.context import ProjectRegistry

PROJECT_A = "11111111-1111-4111-8111-111111111111"
PROJECT_B = "22222222-2222-4222-8222-222222222222"
FIXED = datetime(2026, 8, 24, 15, 30, tzinfo=timezone(timedelta(hours=-6)))


def _project(tmp_path: Path, registry: ProjectRegistry, project_id: str, name: str) -> Path:
    root = tmp_path / name
    marker = root / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'project_id = "{project_id}"',
                f'name = "{name}"',
                'initialized_by = "1.0.0"',
                'forge = "local"',
                'contract_root = "specs"',
                "",
            )
        ),
        encoding="utf-8",
    )
    (root / "specs").mkdir()
    subprocess.run(("git", "init", "-q"), cwd=root, check=True)
    assert registry.register(project_id, root, name)
    return root


def _store(tmp_path: Path) -> tuple[ObjectiveContractStore, ProjectRegistry]:
    registry = ProjectRegistry(root=tmp_path / "state")
    return ObjectiveContractStore(registry=registry, clock=lambda: FIXED), registry


def _complete(
    store: ObjectiveContractStore, project_id: str, contract_id: str, revision: int
) -> int:
    for section in REQUIRED_SECTIONS:
        result = store.set_section(
            project_id=project_id,
            contract_id=contract_id,
            expected_revision=revision,
            section=section,
            content=f"Accepted {section.replace('_', ' ')}.",
            session_id="session-final",
        )
        revision = result["revision"]
    return revision


def test_contract_sections_accept_unicode_multiline_prose_beyond_observation_metadata_limits(
    tmp_path: Path,
) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(
        project_id=PROJECT_A,
        title="Retirar confinamiento inválido",
        session_id="s1",
    )
    content = (
        "El propietario decidió retirar una guardia de terminal que bloquea trabajo legítimo.\n\n"
        + "La decisión conserva contratos, Git, credenciales y Kanban. " * 12
    )
    assert len(content) > 512

    updated = store.set_section(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=1,
        section="owner_intent",
        content=content,
        session_id="s1",
    )

    assert updated["revision"] == 2
    assert (
        store.show(project_id=PROJECT_A, contract_id=started["contract_id"])["sections"][
            "owner_intent"
        ]
        == content.strip()
    )


def test_begin_binds_project_and_records_system_provenance(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    result = store.begin(
        project_id=PROJECT_A,
        title="Ship alpha",
        session_id="session-create",
    )

    assert result["project_id"] == PROJECT_A
    assert result["revision"] == 1
    assert result["status"] == "draft"
    draft = json.loads((project / result["draft_path"]).read_text(encoding="utf-8"))
    assert draft["created_at_utc"] == "2026-08-24T21:30:00Z"
    assert draft["created_at_local"] == "2026-08-24T15:30:00-06:00"
    assert draft["author_profile"] == "morfeo"
    assert draft["created_in_session"] == "session-create"


def test_interleaved_contracts_never_cross_project_roots(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    alpha = _project(tmp_path, registry, PROJECT_A, "alpha")
    beta = _project(tmp_path, registry, PROJECT_B, "beta")
    first = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    second = store.begin(project_id=PROJECT_B, title="Beta", session_id="s1")

    first_update = store.set_section(
        project_id=PROJECT_A,
        contract_id=first["contract_id"],
        expected_revision=1,
        section="objective",
        content="Change alpha only.",
        session_id="s1",
    )
    second_update = store.set_section(
        project_id=PROJECT_B,
        contract_id=second["contract_id"],
        expected_revision=1,
        section="objective",
        content="Change beta only.",
        session_id="s1",
    )

    assert (alpha / first_update["draft_path"]).is_file()
    assert not (beta / first_update["draft_path"]).exists()
    assert (beta / second_update["draft_path"]).is_file()
    assert not (alpha / second_update["draft_path"]).exists()


def test_marker_conflict_revision_conflict_and_truncation_make_zero_writes(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    draft = project / started["draft_path"]
    before = draft.read_bytes()

    marker = project / ".aether" / "project.toml"
    marker.write_text(marker.read_text().replace(PROJECT_A, PROJECT_B), encoding="utf-8")
    with pytest.raises(ContractError, match="PROJECT-CONFLICT"):
        store.set_section(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            expected_revision=1,
            section="objective",
            content="Must not land.",
            session_id="s1",
        )
    assert draft.read_bytes() == before

    marker.write_text(marker.read_text().replace(PROJECT_B, PROJECT_A), encoding="utf-8")
    with pytest.raises(ContractError, match="REVISION-CONFLICT"):
        store.set_section(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            expected_revision=99,
            section="objective",
            content="Must not land.",
            session_id="s1",
        )
    with pytest.raises(ContractError, match="TRUNCATED"):
        store.set_section(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            expected_revision=1,
            section="objective",
            content="An incomplete objective ...[truncated]",
            session_id="s1",
        )
    with pytest.raises(ContractError, match="SECRET"):
        store.set_section(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            expected_revision=1,
            section="objective",
            content="api_key = sk-abcdefghijklmnopqrstuvwxyz123456",
            session_id="s1",
        )
    assert draft.read_bytes() == before


def test_finalize_requires_complete_contract_and_preserves_session_boundary(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="session-create")

    with pytest.raises(ContractError, match="INCOMPLETE"):
        store.finalize(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            expected_revision=1,
            session_id="session-final",
        )

    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    final = store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=revision,
        session_id="session-final",
    )
    artifact = project / final["relative_path"]
    content = artifact.read_text(encoding="utf-8")
    assert final["version"] == 1 and final["status"] == "final"
    assert final["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert 'created_in_session: "session-create"' in content
    assert 'finalized_in_session: "session-final"' in content
    assert re.search(r'observation_trace_id: "ctr_[a-f0-9]{32}"', content)
    assert re.fullmatch(r"ctr_[a-f0-9]{32}", final["observation_trace_id"])
    assert "## Testing Standard" in content


def test_supersede_creates_v2_without_changing_v1(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    first = store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=revision,
        session_id="s1",
    )
    first_path = project / first["relative_path"]
    first_bytes = first_path.read_bytes()

    amended = store.supersede(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        version=1,
        change_reason="Clarify acceptance.",
        session_id="s2",
    )
    updated = store.set_section(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=amended["revision"],
        section="acceptance_criteria",
        content="Precise acceptance.",
        session_id="s2",
    )
    second = store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=updated["revision"],
        session_id="s2",
    )

    assert second["version"] == 2
    assert first_path.read_bytes() == first_bytes
    second_text = (project / second["relative_path"]).read_text(encoding="utf-8")
    assert 'supersedes: "' + started["contract_id"] + '@v1"' in second_text
    assert "Precise acceptance." in second_text


def test_supersede_rejects_secret_change_reason(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=revision,
        session_id="s1",
    )
    with pytest.raises(ContractError, match="SECRET"):
        store.supersede(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            version=1,
            change_reason="credential material: " + "sk-" + "a" * 20,
            session_id="s2",
        )


def test_finalize_never_replaces_preexisting_version(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    target = project / ".aether" / "objective-contracts" / started["contract_id"] / "v1.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"preexisting\n")

    with pytest.raises(ContractError, match="IMMUTABLE"):
        store.finalize(
            project_id=PROJECT_A,
            contract_id=started["contract_id"],
            expected_revision=revision,
            session_id="s1",
        )
    assert target.read_bytes() == b"preexisting\n"


def test_prepare_handoff_requires_final_bytes_in_git_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    subprocess.run(("git", "init", "-q"), cwd=project, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=project, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=project, check=True)
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    final = store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=revision,
        session_id="s1",
    )

    not_ready = store.prepare_handoff(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        version=1,
    )
    assert not_ready == {"handoff_ready": False, "reason": "NOT_IN_BASE"}

    subprocess.run(
        ("git", "add", ".aether/project.toml", final["relative_path"]), cwd=project, check=True
    )
    subprocess.run(("git", "commit", "-qm", "test: contract"), cwd=project, check=True)
    calls: list[tuple[str, ...]] = []
    original_git = store._git

    def spy(root: Path, *args: str):
        calls.append(args)
        return original_git(root, *args)

    monkeypatch.setattr(store, "_git", spy)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "poison"))
    ready = store.prepare_handoff(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        version=1,
    )
    assert ready["handoff_ready"] is True
    assert ready["sha256"] == final["sha256"]
    assert ready["relative_path"] == final["relative_path"]
    assert ready["observation_trace_id"] == final["observation_trace_id"]
    assert ready["root_idempotency_key"] == (f"aether.obs.v1:{final['observation_trace_id']}:root")
    monkeypatch.delenv("GIT_DIR")
    assert (
        ready["base_commit"]
        == subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=project, text=True).strip()
    )
    assert len(ready["envelope"]) < 1000
    assert ("rev-parse", "--verify", "HEAD^{commit}") in calls
    assert not any(args[0] == "show" and args[1].startswith("HEAD:") for args in calls)
    marker = project / ".aether" / "project.toml"
    marker.write_text(
        marker.read_text().replace('name = "alpha"', 'name = "drifted"'), encoding="utf-8"
    )
    drifted = store.prepare_handoff(
        project_id=PROJECT_A, contract_id=started["contract_id"], version=1
    )
    assert drifted == {"handoff_ready": False, "reason": "NOT_IN_BASE"}
    monkeypatch.delenv("GIT_DIR", raising=False)
    subprocess.run(("git", "checkout", "--", ".aether/project.toml"), cwd=project, check=True)
    final_path = project / final["relative_path"]
    text = final_path.read_text(encoding="utf-8")
    final_path.write_text(text.replace("## Canonical References", "## Removed"), encoding="utf-8")
    subprocess.run(("git", "add", final["relative_path"]), cwd=project, check=True)
    subprocess.run(("git", "commit", "-qm", "test: malformed contract"), cwd=project, check=True)
    with pytest.raises(ContractError, match="FINAL-INVALID"):
        store.prepare_handoff(project_id=PROJECT_A, contract_id=started["contract_id"], version=1)


def test_prepare_handoff_returns_stable_distinct_opaque_flow_ids(
    tmp_path: Path,
) -> None:
    store, registry = _store(tmp_path)
    alpha = _project(tmp_path, registry, PROJECT_A, "alpha")
    beta = _project(tmp_path, registry, PROJECT_B, "beta")

    def ready(project_id: str, project: Path, title: str) -> dict[str, Any]:
        subprocess.run(
            ("git", "config", "user.email", "test@example.invalid"), cwd=project, check=True
        )
        subprocess.run(("git", "config", "user.name", "Test"), cwd=project, check=True)
        started = store.begin(project_id=project_id, title=title, session_id="s1")
        revision = _complete(store, project_id, started["contract_id"], 1)
        final = store.finalize(
            project_id=project_id,
            contract_id=started["contract_id"],
            expected_revision=revision,
            session_id="s1",
        )
        subprocess.run(("git", "add", "."), cwd=project, check=True)
        subprocess.run(("git", "commit", "-qm", "test: contract"), cwd=project, check=True)
        return store.prepare_handoff(
            project_id=project_id,
            contract_id=final["contract_id"],
            version=final["version"],
        )

    alpha_first = ready(PROJECT_A, alpha, "Alpha")
    alpha_second = store.prepare_handoff(
        project_id=PROJECT_A,
        contract_id=alpha_first["contract_id"],
        version=alpha_first["version"],
    )
    beta_handoff = ready(PROJECT_B, beta, "Beta")

    assert alpha_first["flow_id"] == alpha_second["flow_id"]
    assert alpha_first["flow_id"] != beta_handoff["flow_id"]
    assert re.fullmatch(r"aether\.flow\.v1:[0-9a-f]{64}", alpha_first["flow_id"])
    assert PROJECT_A not in alpha_first["flow_id"]
    assert alpha_first["contract_id"] not in alpha_first["flow_id"]


def test_prepare_handoff_keeps_flow_id_out_of_short_envelope_and_body(
    tmp_path: Path,
) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=project, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=project, check=True)
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    final = store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=revision,
        session_id="s1",
    )
    subprocess.run(("git", "add", "."), cwd=project, check=True)
    subprocess.run(("git", "commit", "-qm", "test: contract"), cwd=project, check=True)

    handoff = store.prepare_handoff(
        project_id=PROJECT_A,
        contract_id=final["contract_id"],
        version=final["version"],
    )

    assert handoff["flow_id"]
    assert handoff["flow_id"] not in handoff["envelope"]
    assert "session_affinity" not in handoff["envelope"]
    assert "flow_id" not in handoff["envelope"]


def test_validate_reports_missing_then_complete_without_finalizing(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")

    incomplete = store.validate(project_id=PROJECT_A, contract_id=started["contract_id"])
    assert incomplete["valid"] is False
    assert incomplete["missing_sections"] == list(REQUIRED_SECTIONS)
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    complete = store.validate(project_id=PROJECT_A, contract_id=started["contract_id"])
    assert complete["valid"] is True
    assert complete["revision"] == revision


def test_project_requires_complete_marker_and_exact_git_root(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    marker = project / ".aether" / "project.toml"
    marker.write_text(marker.read_text().replace('contract_root = "specs"\n', ""), encoding="utf-8")
    with pytest.raises(ContractError, match="PROJECT-MARKER-INVALID"):
        store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")

    marker.write_text(marker.read_text() + 'contract_root = "specs"\n', encoding="utf-8")
    nested = project / "nested"
    nested.mkdir()
    assert registry.register(PROJECT_A, nested, "wrong-root")
    (nested / ".aether").mkdir()
    (nested / ".aether" / "project.toml").write_bytes(marker.read_bytes())
    with pytest.raises(ContractError, match="PROJECT-GIT-ROOT"):
        store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")


def test_symlinked_contract_storage_is_rejected(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / ".aether" / "drafts").symlink_to(outside, target_is_directory=True)

    with pytest.raises((ContractError, ValueError), match="PATH|private|symlink"):
        store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    assert list(outside.iterdir()) == []


def test_concurrent_expected_revision_has_one_winner(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def update(content: str) -> None:
        barrier.wait()
        try:
            store.set_section(
                project_id=PROJECT_A,
                contract_id=started["contract_id"],
                expected_revision=1,
                section="objective",
                content=content,
                session_id="s1",
            )
            outcomes.append("ok")
        except ContractError as exc:
            outcomes.append(exc.code)

    threads = [threading.Thread(target=update, args=(content,)) for content in ("First", "Second")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 1
    assert outcomes.count("AETHER-OBJECTIVE-CONTRACT-REVISION-CONFLICT") == 1
    assert store.show(project_id=PROJECT_A, contract_id=started["contract_id"])["revision"] == 2


def test_plugin_registers_one_morfeo_only_transactional_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    registry = ProjectRegistry()
    _project(tmp_path, registry, PROJECT_A, "alpha")
    registered: dict[str, object] = {}

    class Context:
        profile_name = "morfeo"

        def get_config(self, key: str, default: object = None) -> object:
            return "morfeo" if key == "author_profile" else default

        def register_tool(self, **kwargs: object) -> None:
            registered.update(kwargs)

    from aether_agents.objective_contracts import hermes_plugin

    context = Context()
    hermes_plugin.register(context)
    assert registered["name"] == "objective_contract"
    assert registered["toolset"] == "aether_contracts"
    schema = registered["schema"]
    assert isinstance(schema, dict)
    assert set(schema["parameters"]["properties"]["action"]["enum"]) == {
        "begin",
        "set_section",
        "show",
        "list",
        "validate",
        "finalize",
        "supersede",
        "prepare_handoff",
    }
    handler = registered["handler"]
    raw = handler(
        {"action": "begin", "project_id": PROJECT_A, "title": "Alpha"},
        session_id="session-from-hermes",
    )
    result = json.loads(raw)
    assert result["created_in_session"] == "session-from-hermes"

    context.profile_name = "supervisor"
    denied_runtime = json.loads(
        handler({"action": "list", "project_id": PROJECT_A}, session_id="session-from-hermes")
    )
    assert denied_runtime["error"]["code"] == "AETHER-OBJECTIVE-CONTRACT-ROLE-DENIED"

    denied: dict[str, object] = {}

    class WrongRole(Context):
        profile_name = "supervisor"

        def get_config(self, key: str, default: object = None) -> object:
            return "supervisor" if key == "author_profile" else default

        def register_tool(self, **kwargs: object) -> None:
            denied.update(kwargs)

    hermes_plugin.register(WrongRole())
    assert denied == {}


def test_product_resources_enable_authoring_only_for_morfeo() -> None:
    root = Path(__file__).parents[1]
    profiles = root / "src" / "aether_agents" / "resources" / "profiles"
    morfeo = yaml.safe_load((profiles / "morfeo" / "config.yaml").read_text())
    supervisor = yaml.safe_load((profiles / "supervisor" / "config.yaml").read_text())
    implementer = yaml.safe_load((profiles / "implementer" / "config.yaml").read_text())

    assert "aether-objective-contracts" in morfeo["plugins"]["enabled"]
    assert (
        morfeo["plugins"]["entries"]["aether-objective-contracts"]["settings"]["author_profile"]
        == "morfeo"
    )
    assert "aether-objective-contracts" not in supervisor["plugins"]["enabled"]
    assert "aether-objective-contracts" not in implementer["plugins"]["enabled"]
    assert supervisor["approvals"]["mode"] == "off"
    assert implementer["approvals"]["mode"] == "off"
    assert morfeo.get("approvals", {}).get("mode") != "off"
    assert supervisor["security"]["protected_instruction_files"] is False
    assert implementer["security"]["protected_instruction_files"] is False
    assert morfeo.get("security", {}).get("protected_instruction_files", True) is True

    soul = (profiles / "morfeo" / "SOUL.md").read_text(encoding="utf-8")
    assert "For every pipeline handoff" in soul
    assert "These requirements do not apply to bounded direct work" in soul
    assert "Supervisor root handoff without `goal_mode`" in soul

    supervisor_soul = (profiles / "supervisor" / "SOUL.md").read_text(encoding="utf-8")
    assert "Never assign Implementer a unit whose acceptance requires creating" in supervisor_soul
    assert "finalized, checkpointed contract read-only" in supervisor_soul


def test_product_resources_bind_contract_flows_without_widening_role_sessions() -> None:
    root = Path(__file__).parents[1]
    profiles = root / "src" / "aether_agents" / "resources" / "profiles"
    morfeo_soul = (profiles / "morfeo" / "SOUL.md").read_text(encoding="utf-8")
    supervisor_soul = (profiles / "supervisor" / "SOUL.md").read_text(encoding="utf-8")
    implementer_soul = (profiles / "implementer" / "SOUL.md").read_text(encoding="utf-8")

    assert "`flow_id`" in morfeo_soul
    assert "`session_affinity`" in morfeo_soul
    assert "`terminal=false`" in morfeo_soul
    assert "envelope or child bodies" in morfeo_soul
    assert "root_idempotency_key" in morfeo_soul

    assert "same-profile Supervisor" in supervisor_soul
    assert "Implementer cards" in supervisor_soul
    assert "fresh session" in supervisor_soul
    assert "`terminal=true`" in supervisor_soul
    assert "root and all implementation units" in supervisor_soul
    assert "needs-owner" in supervisor_soul
    assert "needs-contract-revision" in supervisor_soul
    assert "internal" in supervisor_soul
    assert "do not signal the origin" in supervisor_soul

    assert "session_affinity" not in implementer_soul
    assert "same-profile Supervisor" not in implementer_soul
