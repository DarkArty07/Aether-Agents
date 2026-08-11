"""M2.3 trusted coordinator and project-admission tests."""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest

from aether_mcp.admission import AdmissionError, ProjectAdmissionRegistry, TrustedLaunchContext


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(path: Path) -> Path:
    path.mkdir()
    _git("init", "--initial-branch=main", cwd=path)
    _git("-c", "user.name=Aether Test", "-c", "user.email=aether@test.invalid", "commit", "--allow-empty", "-m", "init", cwd=path)
    return path


def _context(home: Path, *, principal_id: str | None = None, profile: str = "hermes") -> TrustedLaunchContext:
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    return TrustedLaunchContext.from_environment(
        {
            "AETHER_COORDINATOR_PRINCIPAL": principal_id or str(uuid.uuid4()),
            "HERMES_HOME": str(home),
            "AETHER_PROFILE": profile,
            "AETHER_SESSION_ID": str(uuid.uuid4()),
        }
    )


def test_launch_context_requires_server_environment_and_canonical_home(tmp_path: Path) -> None:
    with pytest.raises(AdmissionError, match="trusted launch") as captured:
        TrustedLaunchContext.from_environment({})
    assert captured.value.code == "PRINCIPAL_UNAUTHENTICATED"

    real = tmp_path / "real-home"
    real.mkdir()
    alias = tmp_path / "alias-home"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(AdmissionError) as captured:
        _context(alias)
    assert captured.value.code == "PRINCIPAL_UNAUTHENTICATED"


def test_admission_generates_immutable_id_without_writing_project(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    before = _git("status", "--porcelain=v1", cwd=repo)
    registry = ProjectAdmissionRegistry(tmp_path / "state", full_episode_enabled=False)
    context = _context(tmp_path / "home")

    admitted = registry.admit(
        context=context,
        project_root=repo,
        safe_alias="sample",
        capture_policy="DISABLED",
        consent_authority_ref="decision:test",
    )

    assert str(uuid.UUID(admitted.project_id)) == admitted.project_id
    assert admitted.project_root == repo.resolve()
    assert admitted.profile_id == "hermes"
    assert admitted.capture_policy == "DISABLED"
    assert _git("status", "--porcelain=v1", cwd=repo) == before
    assert not (repo / ".aether").exists()


def test_same_repo_sibling_worktree_correlates_one_project_with_distinct_placements(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    sibling = tmp_path / "sibling"
    _git("worktree", "add", "-b", "sibling", str(sibling), cwd=repo)
    context = _context(tmp_path / "home")
    registry = ProjectAdmissionRegistry(tmp_path / "state")

    first = registry.admit(context=context, project_root=repo, safe_alias=None, capture_policy="DISABLED", consent_authority_ref="decision:test")
    second = registry.admit(context=context, project_root=sibling, safe_alias=None, capture_policy="DISABLED", consent_authority_ref="decision:test")
    inspected = registry.inspect(context=context, project_id=first.project_id)

    assert first.project_id == second.project_id
    assert {placement.project_root for placement in inspected.placements} == {repo.resolve(), sibling.resolve()}
    assert len({placement.placement_id for placement in inspected.placements}) == 2


def test_foreign_principal_and_profile_fail_without_enumeration(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    registry = ProjectAdmissionRegistry(tmp_path / "state")
    owner = _context(tmp_path / "owner")
    project = registry.admit(context=owner, project_root=repo, safe_alias=None, capture_policy="DISABLED", consent_authority_ref="decision:test")

    strangers = (
        _context(tmp_path / "other-home"),
        _context(tmp_path / "owner", principal_id=str(uuid.uuid4()), profile="other"),
    )
    for stranger in strangers:
        with pytest.raises(AdmissionError) as captured:
            registry.inspect(context=stranger, project_id=project.project_id)
        assert captured.value.code == "PROJECT_NOT_ADMITTED"
        assert project.project_id not in str(captured.value)


def test_symlink_project_root_and_non_git_root_are_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    alias = tmp_path / "repo-link"
    alias.symlink_to(repo, target_is_directory=True)
    registry = ProjectAdmissionRegistry(tmp_path / "state")
    context = _context(tmp_path / "home")

    for root in (alias, tmp_path / "not-git"):
        root.mkdir(exist_ok=True) if root.name == "not-git" else None
        with pytest.raises(AdmissionError) as captured:
            registry.admit(context=context, project_root=root, safe_alias=None, capture_policy="DISABLED", consent_authority_ref="decision:test")
        assert captured.value.code in {"PROJECT_NOT_ADMITTED", "PROJECT_IDENTITY_MISMATCH"}


def test_inspection_detects_moved_or_replaced_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    registry = ProjectAdmissionRegistry(tmp_path / "state")
    context = _context(tmp_path / "home")
    project = registry.admit(context=context, project_root=repo, safe_alias=None, capture_policy="DISABLED", consent_authority_ref="decision:test")

    moved = tmp_path / "moved"
    os.rename(repo, moved)
    _repo(repo)

    with pytest.raises(AdmissionError) as captured:
        registry.inspect(context=context, project_id=project.project_id)
    assert captured.value.code == "PROJECT_IDENTITY_MISMATCH"


def test_registry_rejects_capture_escalation_and_future_schema(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    context = _context(tmp_path / "home")
    state = tmp_path / "state"
    registry = ProjectAdmissionRegistry(state)
    registry.admit(context=context, project_root=repo, safe_alias=None, capture_policy="DISABLED", consent_authority_ref="decision:test")

    with pytest.raises(AdmissionError) as captured:
        registry.admit(context=context, project_root=repo, safe_alias=None, capture_policy="FULL_EPISODE", consent_authority_ref="decision:other")
    assert captured.value.code == "CAPTURE_POLICY_ESCALATION"

    import sqlite3

    with sqlite3.connect(state / "admissions.sqlite3") as connection:
        connection.execute("PRAGMA user_version = 999")
    with pytest.raises(AdmissionError) as captured:
        ProjectAdmissionRegistry(state)
    assert captured.value.code == "PROJECT_IDENTITY_MISMATCH"


def test_full_episode_is_rejected_before_project_admission_without_a_key_provider(tmp_path: Path) -> None:
    registry = ProjectAdmissionRegistry(tmp_path / "state", full_episode_enabled=False)
    context = _context(tmp_path / "home")

    with pytest.raises(AdmissionError) as captured:
        registry.admit(
            context=context,
            project_root=tmp_path / "not-an-admitted-project",
            safe_alias=None,
            capture_policy="FULL_EPISODE",
            consent_authority_ref="decision:test",
        )

    assert captured.value.code == "CAPTURE_DISABLED"
