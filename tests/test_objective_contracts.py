"""Objective Contract authoring and Hermes plugin regressions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
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

    # One executable contract version gets one deterministic, inspectable board.
    # Different projects/contracts cannot share it, and runtime routing stays outside
    # the portable Contract Handoff Envelope.
    assert alpha_first["execution_board"] == alpha_second["execution_board"]
    assert alpha_first["execution_board"] != beta_handoff["execution_board"]
    assert re.fullmatch(r"oc-[0-9a-f]{32}-[0-9a-f]{16}-v[0-9a-f]+", alpha_first["execution_board"])
    assert len(alpha_first["execution_board"]) <= 64
    assert alpha_first["execution_board"] not in alpha_first["envelope"]


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


def test_execution_board_identity_keeps_hermes_imports_lazy() -> None:
    root = Path(__file__).parents[1]
    script = """
import sys
import aether_agents.cli
from aether_agents.objective_contracts import ObjectiveContractStore
from aether_agents.objective_contracts.execution_boards import execution_board_slug
execution_board_slug('11111111-1111-4111-8111-111111111111', 'oc_aaaaaaaaaaaaaaaa', 1)
assert not any(name == 'hermes_cli' or name.startswith('hermes_cli.') for name in sys.modules)
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        (sys.executable, "-c", script),
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_execution_board_refuses_missing_runtime_project_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    for name in ("HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_HOME"):
        monkeypatch.delenv(name, raising=False)

    from hermes_cli import kanban_db

    from aether_agents.objective_contracts.execution_boards import (
        ExecutionBoardError,
        execution_board_slug,
    )
    from aether_agents.objective_contracts.hermes_plugin import (
        _provision_execution_board as provision_execution_board,
    )

    project = tmp_path / "unregistered"
    project.mkdir()
    slug = execution_board_slug(PROJECT_A, "oc_eeeeeeeeeeeeeeee", 1)
    with pytest.raises(ExecutionBoardError) as missing:
        provision_execution_board(
            project_id=PROJECT_A,
            project_root=project,
            contract_id="oc_eeeeeeeeeeeeeeee",
            version=1,
        )
    assert missing.value.code == "AETHER-EXECUTION-BOARD-PROJECT-MISSING"
    assert not kanban_db.kanban_db_path(slug).exists()
    assert not kanban_db.board_metadata_path(slug).exists()

    from hermes_cli import projects_db

    with projects_db.connect_closing() as connection:
        connection.execute(
            "INSERT INTO projects (id, slug, name, primary_path, created_at, archived) "
            "VALUES ('p_folder_only', 'folder-only', 'Folder only', NULL, 0, 0)"
        )
        connection.execute(
            "INSERT INTO project_folders (project_id, path, is_primary, added_at) "
            "VALUES ('p_folder_only', ?, 1, 0)",
            (str(project),),
        )
        connection.commit()
    with pytest.raises(ExecutionBoardError) as no_explicit_primary:
        provision_execution_board(
            project_id=PROJECT_A,
            project_root=project,
            contract_id="oc_eeeeeeeeeeeeeeee",
            version=1,
        )
    assert no_explicit_primary.value.code == "AETHER-EXECUTION-BOARD-PROJECT-MISSING"
    assert not kanban_db.kanban_db_path(slug).exists()

    with projects_db.connect_closing() as connection:
        connection.execute("DELETE FROM project_folders WHERE project_id = 'p_folder_only'")
        connection.execute("DELETE FROM projects WHERE id = 'p_folder_only'")
        connection.commit()
        for index in (1, 2):
            connection.execute(
                "INSERT INTO projects (id, slug, name, primary_path, created_at, archived) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (f"p_duplicate_{index}", f"duplicate-{index}", "Duplicate", str(project), index),
            )
        connection.commit()
    with pytest.raises(ExecutionBoardError) as duplicate:
        provision_execution_board(
            project_id=PROJECT_A,
            project_root=project,
            contract_id="oc_eeeeeeeeeeeeeeee",
            version=1,
        )
    assert duplicate.value.code == "AETHER-EXECUTION-BOARD-PROJECT-CONFLICT"
    assert not kanban_db.kanban_db_path(slug).exists()


def test_execution_board_rejects_raw_db_override_and_symlink_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.delenv("HERMES_KANBAN_BOARD", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_HOME", raising=False)

    from hermes_cli import kanban_db, projects_db

    from aether_agents.objective_contracts.execution_boards import (
        ExecutionBoardError,
        execution_board_slug,
    )
    from aether_agents.objective_contracts.hermes_plugin import (
        _provision_execution_board as provision_execution_board,
    )

    project = tmp_path / "repo"
    project.mkdir()
    with projects_db.connect_closing() as connection:
        runtime_project_id = projects_db.create_project(
            connection, name="Repo", primary_path=str(project)
        )

    contract_id = "oc_1212121212121212"
    slug = execution_board_slug(PROJECT_A, contract_id, 1)
    expected_db = kanban_db.board_dir(slug) / "kanban.db"
    override = tmp_path / "shared.db"
    override.write_bytes(b"shared-board-sentinel")
    monkeypatch.setenv("HERMES_KANBAN_DB", str(override))
    with pytest.raises(ExecutionBoardError) as raw_override:
        provision_execution_board(
            project_id=PROJECT_A,
            project_root=project,
            contract_id=contract_id,
            version=1,
        )
    assert raw_override.value.code == "AETHER-EXECUTION-BOARD-RAW-DB-OVERRIDE"
    assert override.read_bytes() == b"shared-board-sentinel"
    assert not expected_db.exists()

    monkeypatch.delenv("HERMES_KANBAN_DB")
    kanban_db.write_board_metadata(
        slug,
        default_workdir=str(project.resolve()),
        project_id=runtime_project_id,
    )
    target = tmp_path / "unrelated.db"
    target.write_bytes(b"unrelated-sentinel")
    expected_db.symlink_to(target)
    with pytest.raises(ExecutionBoardError) as symlink:
        provision_execution_board(
            project_id=PROJECT_A,
            project_root=project,
            contract_id=contract_id,
            version=1,
        )
    assert symlink.value.code == "AETHER-EXECUTION-BOARD-UNSAFE-PATH"
    assert target.read_bytes() == b"unrelated-sentinel"


def test_execution_boards_isolate_contracts_and_reject_identity_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two contract flows get distinct DBs; an occupied identity is never adopted."""
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    for name in ("HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_HOME"):
        monkeypatch.delenv(name, raising=False)

    from hermes_cli import kanban_db, projects_db

    from aether_agents.objective_contracts.execution_boards import (
        ExecutionBoardError,
        execution_board_slug,
    )
    from aether_agents.objective_contracts.hermes_plugin import (
        _provision_execution_board as provision_execution_board,
    )

    project = tmp_path / "repo"
    project.mkdir()
    subprocess.run(("git", "init", "-q"), cwd=project, check=True)
    with projects_db.connect_closing() as connection:
        runtime_project_id = projects_db.create_project(
            connection, name="Repo", primary_path=str(project)
        )

    first = provision_execution_board(
        project_id=PROJECT_A,
        project_root=project,
        contract_id="oc_aaaaaaaaaaaaaaaa",
        version=1,
    )
    second = provision_execution_board(
        project_id=PROJECT_A,
        project_root=project,
        contract_id="oc_bbbbbbbbbbbbbbbb",
        version=1,
    )
    amended = provision_execution_board(
        project_id=PROJECT_A,
        project_root=project,
        contract_id="oc_aaaaaaaaaaaaaaaa",
        version=2,
    )

    assert len({first["slug"], second["slug"], amended["slug"]}) == 3
    paths = {kanban_db.kanban_db_path(value["slug"]) for value in (first, second, amended)}
    assert len(paths) == 3
    assert all(path.is_file() for path in paths)
    assert all(
        kanban_db.read_board_metadata(value["slug"])["project_id"] == runtime_project_id
        for value in (first, second, amended)
    )

    import aether_agents.objective_contracts.hermes_plugin as board_plugin

    partial_contract = "oc_ffffffffffffffff"
    partial_slug = execution_board_slug(PROJECT_A, partial_contract, 1)
    partial_dir = kanban_db.board_dir(partial_slug)
    partial_dir.mkdir(parents=True)
    assert board_plugin._create_metadata_exclusive(
        partial_dir / "board.json",
        slug=partial_slug,
        project_root=project.resolve(),
        runtime_project_id=runtime_project_id,
        aether_project_id=PROJECT_A,
        contract_id=partial_contract,
        version=1,
    )
    assert not kanban_db.kanban_db_path(partial_slug).exists()
    recovered = provision_execution_board(
        project_id=PROJECT_A,
        project_root=project,
        contract_id="oc_ffffffffffffffff",
        version=1,
    )
    assert recovered["slug"] == partial_slug
    assert kanban_db.kanban_db_path(partial_slug).is_file()

    first_db = kanban_db.connect(board=first["slug"])
    second_db = kanban_db.connect(board=second["slug"])
    try:
        task_id = kanban_db.create_task(first_db, title="first-flow", board=first["slug"])
        assert kanban_db.get_task(first_db, task_id) is not None
        assert kanban_db.get_task(second_db, task_id) is None
    finally:
        first_db.close()
        second_db.close()

    occupied = execution_board_slug(PROJECT_B, "oc_cccccccccccccccc", 1)
    kanban_db.create_board(
        occupied,
        default_workdir=str(project.resolve()),
        project_id="p_wrong",
    )
    with pytest.raises(ExecutionBoardError) as conflict:
        provision_execution_board(
            project_id=PROJECT_B,
            project_root=project,
            contract_id="oc_cccccccccccccccc",
            version=1,
        )
    assert conflict.value.code == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"

    # Simulate a non-cooperating native writer winning exactly after Aether's
    # exists=False check. Exclusive creation must not overwrite its metadata.

    raced_contract = "oc_3434343434343434"
    raced_slug = execution_board_slug(PROJECT_A, raced_contract, 1)
    original_create = board_plugin._create_metadata_exclusive

    def native_wins(metadata_path: Path, **_kwargs: object) -> bool:
        kanban_db.write_board_metadata(
            raced_slug,
            name="Native winner",
            default_workdir=str(project.resolve()),
            project_id="p_wrong",
        )
        return original_create(
            metadata_path,
            slug=raced_slug,
            project_root=project.resolve(),
            runtime_project_id=runtime_project_id,
            aether_project_id=PROJECT_A,
            contract_id=raced_contract,
            version=1,
        )

    monkeypatch.setattr(board_plugin, "_create_metadata_exclusive", native_wins)
    with pytest.raises(ExecutionBoardError) as raced:
        provision_execution_board(
            project_id=PROJECT_A,
            project_root=project,
            contract_id=raced_contract,
            version=1,
        )
    assert raced.value.code == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"
    assert kanban_db.read_board_metadata(raced_slug)["project_id"] == "p_wrong"


def test_execution_board_provisioning_is_concurrently_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    for name in ("HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_HOME"):
        monkeypatch.delenv(name, raising=False)

    from hermes_cli import kanban_db, projects_db

    from aether_agents.objective_contracts.hermes_plugin import (
        _provision_execution_board as provision_execution_board,
    )

    project = tmp_path / "repo"
    project.mkdir()
    with projects_db.connect_closing() as connection:
        runtime_project_id = projects_db.create_project(
            connection, name="Repo", primary_path=str(project)
        )

    barrier = threading.Barrier(3)
    results: list[dict[str, str]] = []
    failures: list[BaseException] = []

    def provision() -> None:
        barrier.wait()
        try:
            results.append(
                provision_execution_board(
                    project_id=PROJECT_A,
                    project_root=project,
                    contract_id="oc_dddddddddddddddd",
                    version=1,
                )
            )
        except BaseException as exc:  # pragma: no cover - asserted empty below.
            failures.append(exc)

    threads = [threading.Thread(target=provision) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert failures == []
    assert len(results) == 2
    assert results[0] == results[1]
    matching = [board for board in kanban_db.list_boards() if board["slug"] == results[0]["slug"]]
    assert len(matching) == 1
    assert matching[0]["project_id"] == runtime_project_id


def test_plugin_prepare_handoff_provisions_one_project_scoped_board_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Hermes plugin turns one ready contract version into one isolated queue."""
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state-home"))
    for name in ("HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_HOME"):
        monkeypatch.delenv(name, raising=False)

    # Import after the isolated home is selected: these are Hermes runtime APIs, not
    # dependencies of Aether's portable store.
    from hermes_cli import kanban_db, projects_db

    registry = ProjectRegistry()
    project = _project(tmp_path, registry, PROJECT_A, "alpha")
    with projects_db.connect_closing() as connection:
        runtime_project_id = projects_db.create_project(
            connection, name="Alpha", primary_path=str(project)
        )

    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=project, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=project, check=True)
    store = ObjectiveContractStore(registry=registry, clock=lambda: FIXED)
    started = store.begin(project_id=PROJECT_A, title="Alpha", session_id="s1")
    revision = _complete(store, PROJECT_A, started["contract_id"], 1)
    final = store.finalize(
        project_id=PROJECT_A,
        contract_id=started["contract_id"],
        expected_revision=revision,
        session_id="s1",
    )

    from aether_agents.objective_contracts import hermes_plugin
    from aether_agents.objective_contracts.execution_boards import execution_board_slug

    args = {
        "action": "prepare_handoff",
        "project_id": PROJECT_A,
        "contract_id": final["contract_id"],
        "version": 1,
    }
    planned_slug = execution_board_slug(PROJECT_A, final["contract_id"], 1)
    not_ready = json.loads(
        hermes_plugin._handle(args, session_id="session-zero", author_profile="morfeo")
    )
    assert not_ready == {"handoff_ready": False, "reason": "NOT_IN_BASE"}
    assert not kanban_db.kanban_db_path(planned_slug).exists()

    subprocess.run(("git", "add", "."), cwd=project, check=True)
    subprocess.run(("git", "commit", "-qm", "test: contract"), cwd=project, check=True)

    first = json.loads(
        hermes_plugin._handle(args, session_id="session-one", author_profile="morfeo")
    )
    second = json.loads(
        hermes_plugin._handle(args, session_id="session-two", author_profile="morfeo")
    )

    assert first["handoff_ready"] is True
    assert first["execution_board"] == second["execution_board"]
    assert first["hermes_project_id"] == runtime_project_id
    metadata = kanban_db.read_board_metadata(first["execution_board"])
    assert metadata["project_id"] == runtime_project_id
    assert metadata["aether_project_id"] == PROJECT_A
    assert metadata["aether_contract_id"] == final["contract_id"]
    assert metadata["aether_contract_version"] == 1
    assert metadata["default_workdir"] == str(project.resolve())
    assert Path(metadata["db_path"]).is_file()
    assert first["execution_board"] not in first["envelope"]
    assert runtime_project_id not in first["envelope"]


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
    assert "`execution_board`" in morfeo_soul
    assert "`hermes_project_id`" in morfeo_soul
    assert "root card's `board` and `project`" in morfeo_soul
    assert "current/default board" in morfeo_soul

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


def _packaged_role_souls() -> dict[str, str]:
    root = Path(__file__).parents[1]
    profiles = root / "src" / "aether_agents" / "resources" / "profiles"
    return {
        role: (profiles / role / "SOUL.md").read_text(encoding="utf-8")
        for role in ("morfeo", "supervisor", "implementer")
    }


def _normalized_markdown(text: str) -> str:
    return " ".join(text.split())


def test_packaged_role_souls_define_canonical_skill_precedence_without_skill_lists() -> None:
    root = Path(__file__).parents[1]
    profiles = root / "src" / "aether_agents" / "resources" / "profiles"
    assert {path.name for path in profiles.iterdir() if path.is_dir()} == {
        "morfeo",
        "supervisor",
        "implementer",
    }

    required = (
        "Aether Canonical Skills",
        "Project Canonical Skills",
        "Learned Profile Skills",
        ".aether/skills/<name>/SKILL.md",
        "current owner instruction",
        "constitution/design/stage specs/Objective Contract",
        "repository operating rules",
        "procedure, never authority",
        "Project Canonical",
        "Aether Canonical",
        "Learned Profile",
    )
    for soul in _packaged_role_souls().values():
        normalized = _normalized_markdown(soul)
        assert all(clause in normalized for clause in required)
        assert "src/aether_agents/resources/skills/" not in normalized
        assert "git/github closeout" not in normalized.lower()
        assert "semver/release" not in normalized.lower()


def test_role_souls_assign_onboarding_issue_and_publication_boundaries() -> None:
    souls = _packaged_role_souls()
    morfeo = souls["morfeo"]
    supervisor = souls["supervisor"]
    implementer = souls["implementer"]

    assert "root `AGENTS.md`" in morfeo
    assert "root `agents.md` is absent" in morfeo.lower()
    assert "onboard" in morfeo.lower()
    assert "constitution confirmation" in morfeo
    assert "brownfield" in morfeo
    assert "preserve" in morfeo and "reconcile" in morfeo
    assert "project policy uses Issues" in morfeo
    assert "canonical issue" in morfeo and "non-duplicate" in morfeo
    assert "direct-route closeout" in morfeo
    assert "pipeline branch" in morfeo and "fully closed" in morfeo

    assert "independent review" in supervisor
    assert "AGENTS.md coherence" in supervisor
    assert "release_impact" in supervisor
    assert "release_action" in supervisor
    assert "release_channel" in supervisor
    assert "normal branch push" in supervisor
    assert "required checks" in supervisor
    assert "green merge without bypass" in supervisor
    assert "terminal evidence" in supervisor
    assert "non-applicability reason" in supervisor
    assert "residue cleanup" in supervisor
    assert "local integration alone is not success" in supervisor.lower()

    assert "local commits and evidence" in implementer
    assert "compatibility impact" in implementer
    assert "invalidates guidance" in implementer
    assert "specific non-applicability reason" in implementer
    assert "never publish" in implementer
    assert "never push" in implementer
    assert "never open or merge" in implementer
    assert "never mutate issues" in implementer


def test_release_conclusions_stay_separate_from_compatibility_and_channel() -> None:
    souls = _packaged_role_souls()
    lifecycle = (Path(__file__).parents[1] / "docs" / "guides" / "lifecycle.md").read_text(
        encoding="utf-8"
    )
    authority = (Path(__file__).parents[1] / "docs" / "roles-and-authority.md").read_text(
        encoding="utf-8"
    )
    for source in (souls["supervisor"], lifecycle, authority):
        assert "release_impact = none|patch|minor|major" in source
        assert "release_action = defer|prepare|publish" in source
        assert "release_channel = none|prerelease|stable" in source
    combined = lifecycle + authority + souls["supervisor"]
    assert "Prerelease is not a compatibility impact" in combined
    assert "merge does not imply a release" in combined
    assert "compatibility impact" in combined


def test_terminal_pipeline_closeout_rejects_local_integration_as_success() -> None:
    root = Path(__file__).parents[1]
    sources = [
        (root / "docs" / "roles-and-authority.md").read_text(encoding="utf-8"),
        (root / "docs" / "guides" / "lifecycle.md").read_text(encoding="utf-8"),
        (root / "docs" / "guides" / "execution.md").read_text(encoding="utf-8"),
    ]
    combined = "\n".join(sources)
    normalized = _normalized_markdown(combined).lower()
    for clause in (
        "acceptance",
        "normal branch push",
        "pull request",
        "required checks",
        "objective-caused CI",
        "green merge without bypass",
        "issue/milestone reconciliation",
        "remote merged-branch cleanup",
        "local objective branch/worktree cleanup",
        "durable evidence",
        "final evidence",
        "concrete non-applicability reason",
        "active/unmerged/review/concurrent/unrelated work is preserved",
    ):
        assert clause.lower() in normalized
    assert "local integration alone is not terminal" in normalized


def test_policy_distinguishes_routine_closeout_from_protected_variants() -> None:
    path = Path(__file__).parents[1] / "docs" / "guides" / "policy-and-recovery.md"
    policy = path.read_text(encoding="utf-8").lower()
    assert "routine closeout" in policy
    assert "existing credentials" in policy
    assert "credential acquisition/widening" in policy
    assert "settings mutation" in policy
    assert "force/history rewrite" in policy
    assert "package publication" in policy
    assert "deployment" in policy
