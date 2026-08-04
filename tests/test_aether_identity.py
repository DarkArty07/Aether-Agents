"""Canonical Aether project, profile and execution-domain identity."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aether_agents import identity
from aether_agents.continuity import hooks


def repository(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / ".git").mkdir()
    return path


def test_project_aliases_resolve_to_one_canonical_identity(tmp_path: Path) -> None:
    root = repository(tmp_path / "project")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)

    direct = identity.resolve_project_identity(root)
    linked = identity.resolve_project_identity(alias)

    assert direct == linked
    assert direct.root == root.resolve(strict=True)
    assert direct.project_id.startswith("project:sha256:")


def test_project_identity_rejects_missing_relative_file_and_non_repository_roots(tmp_path: Path) -> None:
    regular_file = tmp_path / "file"
    regular_file.write_text("not a directory")
    non_repository = tmp_path / "directory"
    non_repository.mkdir()

    with pytest.raises(identity.IdentityError):
        identity.resolve_project_identity(tmp_path / "missing")
    with pytest.raises(identity.IdentityError):
        identity.resolve_project_identity(regular_file)
    with pytest.raises(identity.IdentityError):
        identity.resolve_project_identity(Path("relative"))
    with pytest.raises(identity.IdentityError):
        identity.resolve_project_identity(non_repository)

    generic = identity.resolve_project_identity(non_repository, require_repository=False)
    assert generic.root == non_repository.resolve(strict=True)


def test_recorded_project_root_may_only_confirm_the_active_identity(tmp_path: Path) -> None:
    active_root = repository(tmp_path / "active")
    foreign_root = repository(tmp_path / "foreign")
    active = identity.resolve_project_identity(active_root)
    alias = tmp_path / "alias"
    alias.symlink_to(active_root, target_is_directory=True)

    assert identity.confirm_recorded_project_root(str(alias), active) == active.root
    with pytest.raises(identity.IdentityMismatchError):
        identity.confirm_recorded_project_root(str(foreign_root), active)
    with pytest.raises(identity.IdentityError):
        identity.confirm_recorded_project_root(str(tmp_path / "stale"), active)


def test_profile_identity_is_canonical_and_separate_from_project_identity(tmp_path: Path) -> None:
    profile = tmp_path / "profiles" / "hefesto"
    profile.mkdir(parents=True)
    alias = tmp_path / "profile-alias"
    alias.symlink_to(profile, target_is_directory=True)

    direct = identity.resolve_profile_identity(profile)
    linked = identity.resolve_profile_identity(alias)

    assert direct == linked
    assert direct.home == profile.resolve(strict=True)
    assert direct.name == "hefesto"
    assert direct.profile_id.startswith("profile:sha256:")


def test_identity_records_reject_forged_fields_during_direct_construction(tmp_path: Path) -> None:
    root = repository(tmp_path / "project").resolve(strict=True)
    profile = tmp_path / "profiles" / "hermes"
    profile.mkdir(parents=True)
    canonical_profile = profile.resolve(strict=True)

    with pytest.raises(identity.IdentityError):
        identity.ProjectIdentity(root=root, project_id="project:sha256:forged", repository=True)
    with pytest.raises(identity.IdentityError):
        identity.ProfileIdentity(
            home=canonical_profile,
            profile_id="profile:sha256:forged",
            name="hermes",
        )


def test_identity_binding_requires_an_explicit_allowed_execution_domain(tmp_path: Path) -> None:
    root = repository(tmp_path / "project")
    profile = tmp_path / "profiles" / "hermes"
    profile.mkdir(parents=True)

    binding = identity.bind_identity(
        project_root=root,
        hermes_home=profile,
        execution_domain=identity.ExecutionDomain.SYNTHETIC,
        allowed_project_roots=(root,),
    )

    assert binding.project.root == root.resolve(strict=True)
    assert binding.profile.home == profile.resolve(strict=True)
    assert binding.execution_domain is identity.ExecutionDomain.SYNTHETIC

    with pytest.raises(identity.IdentityMismatchError):
        identity.bind_identity(
            project_root=root,
            hermes_home=profile,
            execution_domain=identity.ExecutionDomain.LIVE,
            allowed_project_roots=(repository(tmp_path / "other"),),
        )
    with pytest.raises(identity.IdentityError):
        identity.bind_identity(project_root=root, hermes_home=profile, execution_domain="auto")  # type: ignore[arg-type]


def test_continuity_hook_preserves_stale_recorded_root_instead_of_overwriting_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "active")
    stale = tmp_path / "missing-old-root"
    db = Mock()
    db.get_hot_state.return_value = {"project_root": str(stale)}
    monkeypatch.setenv("AETHER_HOME", str(root))
    hooks._turn_counter = 0  # type: ignore[attr-defined]

    try:
        with patch.object(hooks, "_get_aether_db", return_value=db):
            hooks.on_post_llm_call(
                session_id="session",
                user_message="request",
                assistant_response="response",
                conversation_history=[],
                model="model",
                platform="cli",
            )
    finally:
        hooks._turn_counter = 0  # type: ignore[attr-defined]

    updates = db.update_hot_state.call_args.kwargs
    assert updates["last_request"] == "request"
    assert "project_root" not in updates


def test_continuity_hook_canonicalizes_matching_alias_and_ignores_mismatched_root_for_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "active")
    alias = tmp_path / "active-alias"
    alias.symlink_to(root, target_is_directory=True)
    db = Mock()
    db.get_hot_state.return_value = {"project_root": str(alias)}
    monkeypatch.setenv("AETHER_HOME", str(alias))
    hooks._turn_counter = 0  # type: ignore[attr-defined]

    try:
        with patch.object(hooks, "_get_aether_db", return_value=db):
            hooks.on_post_llm_call(
                session_id="session",
                user_message="request",
                assistant_response="response",
                conversation_history=[],
                model="model",
                platform="cli",
            )
            assert hooks._make_relative(str(root / "src" / "module.py")) == "src/module.py"  # type: ignore[attr-defined]
    finally:
        hooks._turn_counter = 0  # type: ignore[attr-defined]

    assert db.update_hot_state.call_args.kwargs["project_root"] == str(root.resolve(strict=True))
