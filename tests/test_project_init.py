"""``aether init`` behavior: brownfield initialization and its refusals.

Covers FR-1334 and ``specs/001-aether-v1-productization/contracts/cli.md`` section 2.
The Hermes Project binding is exercised against a real ``projects.db`` schema fixture so
the read-only exact-path match is tested, not mocked.
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import tomllib
from pathlib import Path

import pytest

from aether_agents.commands.init import run_init
from aether_agents.objective_contracts import ObjectiveContractStore
from aether_agents.observation.context import ProjectRegistry
from aether_agents.project_marker import validate_project_marker

_PROJECTS_SCHEMA = """
CREATE TABLE projects (
    id            TEXT PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    description   TEXT,
    icon          TEXT,
    color         TEXT,
    board_slug    TEXT,
    primary_path  TEXT,
    created_at    INTEGER NOT NULL,
    archived      INTEGER NOT NULL DEFAULT 0
);
"""


def _git_repository(path: Path) -> Path:
    """Create a brownfield repository: real history, real content, no Aether marker."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(("git", "init", "-b", "main"), cwd=path, check=True, capture_output=True)
    subprocess.run(
        ("git", "config", "user.email", "test@example.invalid"),
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "Test"), cwd=path, check=True, capture_output=True
    )
    (path / "README.md").write_text("brownfield\n", encoding="utf-8")
    subprocess.run(("git", "add", "-A"), cwd=path, check=True, capture_output=True)
    subprocess.run(("git", "commit", "-m", "initial"), cwd=path, check=True, capture_output=True)
    return path


def _hermes_home(tmp_path: Path, projects: list[tuple[str, str, str, Path]]) -> Path:
    """Build a Hermes profile home holding ``(id, slug, name, primary_path)`` projects."""
    home = tmp_path / "hermes-home"
    home.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(home / "projects.db")
    connection.executescript(_PROJECTS_SCHEMA)
    for identifier, slug, name, primary in projects:
        connection.execute(
            "INSERT INTO projects (id, slug, name, primary_path, created_at, archived) "
            "VALUES (?, ?, ?, ?, 0, 0)",
            (identifier, slug, name, str(primary)),
        )
    connection.commit()
    connection.close()
    return home


def _args(path: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "path": str(path),
        "name": None,
        "forge": None,
        "hermes_project": None,
        "dry_run": False,
        "json": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.fixture()
def registry(tmp_path: Path) -> ProjectRegistry:
    return ProjectRegistry(tmp_path / "state")


def test_brownfield_init_writes_valid_marker_and_binds_one_hermes_project(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "changed", envelope.errors
    assert envelope.changed is True
    marker = tomllib.loads((repository / ".aether" / "project.toml").read_text(encoding="utf-8"))
    validate_project_marker(marker)
    assert marker["project_id"] == envelope.data["project_id"]
    assert marker["forge"] == "local"
    assert marker["contract_root"] == "specs"
    assert marker["default_branch"] == "main"
    assert "github" not in marker
    # FR-1334: the native binding is local identity and stays out of the portable marker.
    assert "hermes_project_id" not in marker
    assert envelope.data["hermes_project_id"] == "p_exact"
    assert registry.project_path(marker["project_id"]) == repository
    assert registry.verify_with_marker(marker["project_id"]) is True


def test_init_is_idempotent(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )
    first = run_init(_args(repository), registry=registry)
    marker_path = repository / ".aether" / "project.toml"
    original = marker_path.read_bytes()

    second = run_init(_args(repository), registry=registry)

    assert second.result == "no_change"
    assert second.changed is False
    assert second.data["project_id"] == first.data["project_id"]
    assert marker_path.read_bytes() == original


def test_exact_path_match_wins_over_identical_project_names(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Several Projects may share one human name; only the exact primary path binds."""
    repository = _git_repository(tmp_path / "repo")
    decoy = _git_repository(tmp_path / "decoy")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(
            _hermes_home(
                tmp_path,
                [
                    ("p_decoy", "same-name", "Same Name", decoy),
                    ("p_exact", "same-name-2", "Same Name", repository),
                    ("p_other", "same-name-3", "Same Name", tmp_path / "absent"),
                ],
            )
        ),
    )

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "changed", envelope.errors
    assert envelope.data["hermes_project_id"] == "p_exact"


def test_ambiguous_exact_matches_refuse_until_disambiguated(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(
            _hermes_home(
                tmp_path,
                [
                    ("p_one", "one", "Repo", repository),
                    ("p_two", "two", "Repo", repository),
                ],
            )
        ),
    )

    ambiguous = run_init(_args(repository), registry=registry)

    assert ambiguous.result == "error"
    assert ambiguous.errors[0].code == "AETHER-INIT-HERMES-PROJECT-AMBIGUOUS"
    assert not (repository / ".aether").exists()

    resolved = run_init(_args(repository, hermes_project="p_two"), registry=registry)

    assert resolved.result == "changed", resolved.errors
    assert resolved.data["hermes_project_id"] == "p_two"


def test_explicit_hermes_project_with_mismatched_path_is_refused(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    other = _git_repository(tmp_path / "other")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(
            _hermes_home(
                tmp_path,
                [
                    ("p_exact", "repo", "Repo", repository),
                    ("p_elsewhere", "other", "Other", other),
                ],
            )
        ),
    )

    envelope = run_init(_args(repository, hermes_project="p_elsewhere"), registry=registry)

    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-HERMES-PROJECT-PATH-MISMATCH"
    assert not (repository / ".aether").exists()


def test_missing_hermes_project_refuses_without_creating_one(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    home = _hermes_home(tmp_path, [])
    monkeypatch.setenv("HERMES_HOME", str(home))

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-HERMES-PROJECT-MISSING"
    assert not (repository / ".aether").exists()
    connection = sqlite3.connect(home / "projects.db")
    assert connection.execute("SELECT count(*) FROM projects").fetchone()[0] == 0
    connection.close()


def test_moved_repository_repoints_the_stale_binding(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", original)])),
    )
    first = run_init(_args(original), registry=registry)
    project_id = first.data["project_id"]

    moved = tmp_path / "moved"
    original.rename(moved)
    monkeypatch.setenv(
        "HERMES_HOME", str(_hermes_home(tmp_path / "second", [("p_exact", "repo", "Repo", moved)]))
    )

    envelope = run_init(_args(moved), registry=registry)

    assert envelope.result == "changed", envelope.errors
    assert envelope.data["project_id"] == project_id
    assert registry.project_path(project_id) == moved
    assert [note.code for note in envelope.warnings] == ["AETHER-INIT-PROJECT-RELOCATED"]


def test_conflicting_live_identity_is_refused(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A copied repository keeps the original's UUID; both live locations must not merge."""
    original = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", original)])),
    )
    first = run_init(_args(original), registry=registry)

    clone = _git_repository(tmp_path / "clone")
    (clone / ".aether").mkdir()
    (clone / ".aether" / "project.toml").write_bytes(
        (original / ".aether" / "project.toml").read_bytes()
    )
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path / "second", [("p_clone", "clone", "Clone", clone)])),
    )

    envelope = run_init(_args(clone), registry=registry)

    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-IDENTITY-CONFLICT"
    assert registry.project_path(first.data["project_id"]) == original


def test_invalid_existing_marker_is_preserved_not_overwritten(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )
    marker_path = repository / ".aether" / "project.toml"
    marker_path.parent.mkdir()
    marker_path.write_text('schema_version = 1\nname = "incomplete"\n', encoding="utf-8")
    original = marker_path.read_bytes()

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-MARKER-INVALID"
    assert marker_path.read_bytes() == original


def test_non_repository_and_subdirectory_are_refused(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_HOME", str(_hermes_home(tmp_path, [])))
    plain = tmp_path / "plain"
    plain.mkdir()

    not_a_repository = run_init(_args(plain), registry=registry)
    assert not_a_repository.result == "error"
    assert not_a_repository.errors[0].code == "AETHER-INIT-NOT-A-GIT-REPOSITORY"

    repository = _git_repository(tmp_path / "repo")
    nested = repository / "src"
    nested.mkdir()

    inside = run_init(_args(nested), registry=registry)
    assert inside.result == "error"
    assert inside.errors[0].code == "AETHER-INIT-NOT-REPOSITORY-ROOT"
    assert not (nested / ".aether").exists()


def test_dry_run_reports_the_plan_without_writing(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )

    envelope = run_init(_args(repository, dry_run=True), registry=registry)

    assert envelope.result == "planned"
    assert envelope.changed is False
    assert envelope.data["action"] == "create"
    assert envelope.data["hermes_project_id"] == "p_exact"
    assert not (repository / ".aether").exists()
    assert not registry.path.exists()


def test_github_remote_is_recorded_and_can_be_overridden(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    subprocess.run(
        ("git", "remote", "add", "origin", "git@github.com:Owner/Repo.git"),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )

    envelope = run_init(_args(repository, name="Custom Name"), registry=registry)

    assert envelope.result == "changed", envelope.errors
    marker = tomllib.loads((repository / ".aether" / "project.toml").read_text(encoding="utf-8"))
    validate_project_marker(marker)
    assert marker["forge"] == "github"
    assert marker["github"] == {"repository": "Owner/Repo"}
    assert marker["name"] == "Custom Name"

    forced = _git_repository(tmp_path / "forced")
    subprocess.run(
        ("git", "remote", "add", "origin", "git@github.com:Owner/Other.git"),
        cwd=forced,
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path / "second", [("p_forced", "forced", "Forced", forced)])),
    )
    local = run_init(_args(forced, forge="local"), registry=registry)

    assert local.result == "changed", local.errors
    local_marker = tomllib.loads((forced / ".aether" / "project.toml").read_text(encoding="utf-8"))
    validate_project_marker(local_marker)
    assert local_marker["forge"] == "local"
    assert "github" not in local_marker


def test_objective_contract_accepts_the_initialized_project_and_rejects_others(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The canary: an initialized project is contract-authorable, an unrelated id is not."""
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "HERMES_HOME",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )
    envelope = run_init(_args(repository), registry=registry)
    project_id = envelope.data["project_id"]

    store = ObjectiveContractStore(registry=registry)
    started = store.begin(
        project_id=project_id, title="Canary objective", session_id="s_canary_0001"
    )

    assert started["project_id"] == project_id
    # `begin` opens a draft; finalized versions land in `.aether/objective-contracts/`.
    assert (repository / ".aether" / "drafts" / f"{started['contract_id']}.json").is_file()

    with pytest.raises(Exception) as unknown:
        store.begin(
            project_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
            title="Wrong project",
            session_id="s_canary_0002",
        )
    assert "PROJECT" in str(getattr(unknown.value, "code", ""))
