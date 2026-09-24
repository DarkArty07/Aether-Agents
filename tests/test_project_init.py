"""``aether init`` behavior: brownfield initialization and its refusals.

Covers FR-1334 and ``specs/001-aether-v1-productization/contracts/cli.md`` section 2.
The Hermes Project binding is exercised against a real ``projects.db`` schema fixture so
the read-only exact-path match is tested, not mocked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

from aether_agents import lifecycle
from aether_agents.commands import init as init_command
from aether_agents.commands.init import run_init
from aether_agents.objective_contracts import ObjectiveContractStore
from aether_agents.observation.context import ProjectRegistry
from aether_agents.paths import data_root, state_root
from aether_agents.project_marker import validate_project_marker

#: The published Aether RC ships this PEP 440 package version; the contract's display
#: and tag identity for the same release is ``_DISPLAY_IDENTITY``.
_PEP440_IDENTITY = "1.0.0rc1"
_DISPLAY_IDENTITY = "1.0.0-rc.1"

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


def _hermes_home(
    tmp_path: Path,
    projects: list[tuple[str, str, str, Path] | tuple[str, str, str, Path, int]],
) -> Path:
    """Build a Hermes profile home holding ``(id, slug, name, primary_path)`` projects."""
    hermes_root = tmp_path / "hermes-root"
    profile_home = hermes_root / "profiles" / "morfeo"
    profile_home.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(profile_home / "projects.db")
    connection.executescript(_PROJECTS_SCHEMA)
    for entry in projects:
        identifier, slug, name, primary = entry[0], entry[1], entry[2], entry[3]
        archived = entry[4] if len(entry) > 4 else 0
        connection.execute(
            "INSERT INTO projects (id, slug, name, primary_path, created_at, archived) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            (identifier, slug, name, str(primary), archived),
        )
    connection.commit()
    connection.close()
    return hermes_root


def _runtime_root(tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime"
    venv_bin = runtime / "venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    hermes_bin = venv_bin / "hermes"
    script = """#!/usr/bin/env python3
import os
import re
import sqlite3
import sys
import uuid
from pathlib import Path

if "--version" in sys.argv:
    print("Hermes Agent v0.20.1 (test)")
    sys.exit(0)

if len(sys.argv) >= 5 and sys.argv[1] == "project" and sys.argv[2] == "create":
    name = sys.argv[3]
    primary_idx = sys.argv.index("--primary")
    primary = sys.argv[primary_idx + 1]
    home = os.environ.get("HERMES_HOME")
    if not home:
        print("HERMES_HOME not set", file=sys.stderr)
        sys.exit(1)
    db_path = Path(home) / "projects.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS projects ("
        "id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, "
        "description TEXT, icon TEXT, color TEXT, board_slug TEXT, primary_path TEXT, "
        "created_at INTEGER NOT NULL, archived INTEGER NOT NULL DEFAULT 0)"
    )
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
    project_id = f"p_{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO projects (id, slug, name, primary_path, created_at, archived) "
        "VALUES (?, ?, ?, ?, 0, 0)",
        (project_id, slug, name, primary),
    )
    conn.commit()
    conn.close()
    print(f"Created project {slug} ({project_id})")
    sys.exit(0)

print(f"Unknown command: {sys.argv}", file=sys.stderr)
sys.exit(1)
"""
    hermes_bin.write_text(script, encoding="utf-8")
    hermes_bin.chmod(0o755)
    return runtime


def _standin_snapshot(path: Path) -> dict[str, object]:
    """Byte digest plus per-table row counts and content digests for isolation witness."""
    with sqlite3.connect(path) as connection:
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        counts: dict[str, int] = {}
        digests: dict[str, str] = {}
        for table in tables:
            rows = [list(row) for row in connection.execute(f"SELECT * FROM {table}")]
            counts[table] = len(rows)
            payload = json.dumps(rows, sort_keys=True, ensure_ascii=True)
            digests[table] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {
        "bytes": hashlib.sha256(path.read_bytes()).hexdigest(),
        "counts": counts,
        "digests": digests,
    }


@pytest.fixture(autouse=True)
def isolate_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    fake_home = tmp_path / "user-home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(fake_home / ".local" / "share"))
    monkeypatch.setenv("XDG_STATE_HOME", str(fake_home / ".local" / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / ".config"))
    fake_tmp = tmp_path / "tmp"
    fake_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMPDIR", str(fake_tmp))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("AETHER_HERMES_ROOT", raising=False)
    monkeypatch.delenv("AETHER_RUNTIME_ROOT", raising=False)
    runtime = _runtime_root(tmp_path)
    monkeypatch.setenv("AETHER_RUNTIME_ROOT", str(runtime))

    fake_kanban = tmp_path / "kanban"
    fake_kanban.mkdir(parents=True, exist_ok=True)
    fake_workspaces = fake_kanban / "workspaces"
    fake_workspaces.mkdir(parents=True, exist_ok=True)
    standin_board = fake_kanban / "kanban.db"
    with sqlite3.connect(standin_board) as conn:
        conn.execute("CREATE TABLE _standin (id INT PRIMARY KEY, canary TEXT)")
        conn.execute("INSERT INTO _standin VALUES (1, 'witness')")
        conn.commit()
    standin_before = _standin_snapshot(standin_board)

    kanban_selectors = {
        "HERMES_KANBAN_DB": str(standin_board),
        "HERMES_KANBAN_BOARD": "isolated-test-board",
        "HERMES_KANBAN_TASK": "t_isolated_task",
        "HERMES_KANBAN_RUN_ID": "0",
        "HERMES_KANBAN_WORKSPACE": str(tmp_path / "workspace"),
        "HERMES_KANBAN_WORKSPACES_ROOT": str(fake_workspaces),
        "HERMES_KANBAN_CLAIM_LOCK": "isolated-claim-lock",
        "HERMES_KANBAN_BRANCH": "isolated-branch",
    }
    for k, v in kanban_selectors.items():
        monkeypatch.setenv(k, v)
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_KANBAN_") and k not in kanban_selectors:
            monkeypatch.delenv(k, raising=False)

    tmp_resolved = tmp_path.resolve()
    assert tmp_resolved in state_root().resolve().parents
    assert tmp_resolved in data_root().resolve().parents
    assert tmp_resolved in init_command._resolve_profile_home(tmp_path).resolve().parents
    assert tmp_resolved in Path(os.environ["HERMES_KANBAN_DB"]).resolve().parents
    assert tmp_resolved in Path(os.environ["HERMES_KANBAN_WORKSPACES_ROOT"]).resolve().parents
    assert tmp_resolved in Path(os.environ["TMPDIR"]).resolve().parents

    yield

    assert _standin_snapshot(standin_board) == standin_before
    assert tmp_resolved in state_root().resolve().parents
    assert tmp_resolved in data_root().resolve().parents
    assert tmp_resolved in init_command._resolve_profile_home(tmp_path).resolve().parents
    assert tmp_resolved in Path(os.environ["HERMES_KANBAN_DB"]).resolve().parents
    assert tmp_resolved in Path(os.environ["HERMES_KANBAN_WORKSPACES_ROOT"]).resolve().parents
    assert tmp_resolved in Path(os.environ["TMPDIR"]).resolve().parents


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
        "AETHER_HERMES_ROOT",
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


def test_marker_carries_the_release_identity_when_the_product_version_is_pep440(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The RC installs as ``1.0.0rc1``; the portable marker must stay schema-conforming.

    ``initialized_by`` is constrained to SemVer by the canonical project schema, so the
    writer records the release's display identity instead of the package version.
    """
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)])),
    )
    monkeypatch.setattr(init_command, "product_version", lambda: _PEP440_IDENTITY)

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "changed", envelope.errors
    marker = tomllib.loads((repository / ".aether" / "project.toml").read_text(encoding="utf-8"))
    validate_project_marker(marker)
    assert marker["initialized_by"] == _DISPLAY_IDENTITY


def test_the_marker_writer_normalizes_through_the_release_identity_converter() -> None:
    """One converter, shared with the release-lock identity path (never a second regex)."""
    assert init_command.display_version is lifecycle.display_version
    assert lifecycle.display_version(_PEP440_IDENTITY) == _DISPLAY_IDENTITY
    # A SemVer package version is already the display identity and passes through.
    assert lifecycle.display_version("0.24.0") == "0.24.0"


def test_init_is_idempotent(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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


def test_missing_hermes_project_creates_exactly_one_native_project_when_none_exists(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When zero active and zero archived projects exist, init creates exactly one."""
    repository = _git_repository(tmp_path / "repo")
    hermes_root = _hermes_home(tmp_path, [])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "changed", envelope.errors
    assert envelope.changed is True
    assert envelope.data["hermes_project_action"] == "create"
    created_id = envelope.data["hermes_project_id"]
    assert created_id is not None
    assert (repository / ".aether" / "project.toml").is_file()

    db_path = hermes_root / "profiles" / "morfeo" / "projects.db"
    connection = sqlite3.connect(db_path)
    rows = connection.execute("SELECT id, primary_path, archived FROM projects").fetchall()
    connection.close()
    assert len(rows) == 1
    assert rows[0][0] == created_id
    assert Path(rows[0][1]).resolve() == repository.resolve()
    assert rows[0][2] == 0
    assert registry.project_path(envelope.data["project_id"]) == repository.resolve()


def test_missing_hermes_project_refuses_when_runtime_unavailable(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When native creation is needed but runtime is unavailable, refuse before mutation."""
    repository = _git_repository(tmp_path / "repo")
    hermes_root = _hermes_home(tmp_path, [])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))
    monkeypatch.setenv("AETHER_RUNTIME_ROOT", str(tmp_path / "absent-runtime"))

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-HERMES-RUNTIME-UNAVAILABLE"
    assert not (repository / ".aether").exists()
    assert not registry.path.exists()
    db_path = hermes_root / "profiles" / "morfeo" / "projects.db"
    connection = sqlite3.connect(db_path)
    assert connection.execute("SELECT count(*) FROM projects").fetchone()[0] == 0
    connection.close()


def test_moved_repository_repoints_the_stale_binding(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", original)])),
    )
    first = run_init(_args(original), registry=registry)
    project_id = first.data["project_id"]

    moved = tmp_path / "moved"
    original.rename(moved)
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
        str(_hermes_home(tmp_path / "second", [("p_exact", "repo", "Repo", moved)])),
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
        "AETHER_HERMES_ROOT",
        str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", original)])),
    )
    first = run_init(_args(original), registry=registry)

    clone = _git_repository(tmp_path / "clone")
    (clone / ".aether").mkdir()
    (clone / ".aether" / "project.toml").write_bytes(
        (original / ".aether" / "project.toml").read_bytes()
    )
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [])))
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
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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
        "AETHER_HERMES_ROOT",
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


# --- Ignore policy (issue #278) -------------------------------------------------
#
# `.aether/project.toml` and `.aether/objective-contracts/` are canonically tracked and
# `.aether/drafts/` is canonically ignored (specs/003-objective-contracts/spec.md).
# Initialization that leaves the marker excluded produces a project that looks healthy
# but can never reach `prepare_handoff`, which requires both in Git HEAD.


def _ignored(root: Path, relative: str) -> bool:
    return (
        subprocess.run(
            ("git", "check-ignore", "-q", relative), cwd=root, capture_output=True
        ).returncode
        == 0
    )


def _init_with_ignore(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch, rule: str, **kw
):
    repository = _git_repository(tmp_path / "repo")
    (repository / ".gitignore").write_text(f"node_modules/\n{rule}\n", encoding="utf-8")
    subprocess.run(("git", "add", "-A"), cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ("git", "commit", "-m", "ignore policy"), cwd=repository, check=True, capture_output=True
    )
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )
    return repository, run_init(_args(repository, **kw), registry=registry)


@pytest.mark.parametrize("rule", [".aether/", ".aether/*", "**/.aether/**", "/.aether"])
def test_init_makes_the_marker_trackable_under_pre_existing_ignore_rules(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch, rule: str
) -> None:
    """A pre-existing rule must not yield a successful-but-unusable project."""
    repository, envelope = _init_with_ignore(tmp_path, registry, monkeypatch, rule)

    assert envelope.result == "changed", envelope.errors
    assert envelope.data["ignore_policy"] == "update"
    assert not _ignored(repository, ".aether/project.toml")
    assert not _ignored(repository, ".aether/objective-contracts/")
    assert not _ignored(repository, ".aether/objective-contracts/oc_abc/v1.md")
    assert not _ignored(repository, ".aether/skills/example/SKILL.md")
    # Drafts stay local, and unrelated project policy is untouched.
    assert _ignored(repository, ".aether/drafts/x.json")
    assert _ignored(repository, ".worktrees/")
    assert _ignored(repository, ".worktrees/task-1/file.txt")
    assert _ignored(repository, "node_modules/pkg/index.js")
    assert "node_modules/" in (repository / ".gitignore").read_text(encoding="utf-8")


def test_init_leaves_other_aether_content_ignored(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repositories that already hid local state in .aether/ must keep hiding it."""
    repository, envelope = _init_with_ignore(tmp_path, registry, monkeypatch, ".aether/")

    assert envelope.result == "changed", envelope.errors
    assert _ignored(repository, ".aether/aether.db")
    assert _ignored(repository, ".aether/locks/lock")


def test_init_does_not_unignore_nested_aether_directories(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The appended block is anchored: only the repository root's .aether/ is affected.

    `!.aether/` is unanchored by necessity — it must neutralize an unanchored directory
    exclusion — so this pins that it re-includes the *directory entry* only, and never
    exposes a sub-project's ignored `.aether/` content.
    """
    repository, envelope = _init_with_ignore(tmp_path, registry, monkeypatch, "**/.aether/**")
    assert envelope.result == "changed", envelope.errors

    nested = repository / "sub" / "mod" / ".aether"
    nested.mkdir(parents=True)
    (nested / "aether.db").write_text("local\n", encoding="utf-8")
    (nested / "project.toml").write_text("local\n", encoding="utf-8")

    assert not _ignored(repository, ".aether/project.toml")
    assert _ignored(repository, "sub/mod/.aether/aether.db")
    assert _ignored(repository, "sub/mod/.aether/project.toml")


def test_init_does_not_touch_an_already_correct_ignore_policy(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _git_repository(tmp_path / "repo")
    policy = (
        "node_modules/\n/.worktrees/\n/.aether/*\n!/.aether/project.toml\n"
        "!/.aether/objective-contracts/\n!/.aether/objective-contracts/**\n"
        "!/.aether/skills/\n!/.aether/skills/**\n"
    )
    (repository / ".gitignore").write_text(policy, encoding="utf-8")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )

    envelope = run_init(_args(repository), registry=registry)

    assert envelope.result == "changed", envelope.errors
    assert envelope.data["ignore_policy"] == "already_correct"
    assert (repository / ".gitignore").read_text(encoding="utf-8") == policy


def test_dry_run_reports_the_ignore_effect_without_mutating(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, envelope = _init_with_ignore(
        tmp_path, registry, monkeypatch, ".aether/", dry_run=True
    )

    assert envelope.result == "planned"
    assert envelope.changed is False
    assert envelope.data["ignore_policy"] == "update"
    assert (repository / ".gitignore").read_text(encoding="utf-8") == "node_modules/\n.aether/\n"
    assert not (repository / ".aether" / "project.toml").exists()
    assert _ignored(repository, ".aether/project.toml")


def test_repairing_the_ignore_policy_alone_is_reported_as_a_change(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An already-initialized project whose marker is ignored must still be repaired."""
    repository, first = _init_with_ignore(tmp_path, registry, monkeypatch, ".aether/")
    assert first.result == "changed", first.errors
    project_id = first.data["project_id"]

    # Re-introduce the exclusion the way the original defect left it.
    (repository / ".gitignore").write_text("node_modules/\n.aether/\n", encoding="utf-8")
    assert _ignored(repository, ".aether/project.toml")

    repaired = run_init(_args(repository), registry=registry)

    assert repaired.result == "changed", repaired.errors
    assert repaired.data["ignore_policy"] == "update"
    assert repaired.data["project_id"] == project_id
    assert not _ignored(repository, ".aether/project.toml")


def test_idempotent_rerun_preserves_marker_bytes_and_ignore_file(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, first = _init_with_ignore(tmp_path, registry, monkeypatch, ".aether/")
    assert first.result == "changed", first.errors
    marker_bytes = (repository / ".aether" / "project.toml").read_bytes()
    ignore_bytes = (repository / ".gitignore").read_bytes()

    second = run_init(_args(repository), registry=registry)

    assert second.result == "no_change"
    assert second.data["ignore_policy"] == "already_correct"
    assert (repository / ".aether" / "project.toml").read_bytes() == marker_bytes
    assert (repository / ".gitignore").read_bytes() == ignore_bytes


def test_prepare_handoff_is_ready_after_init_authoring_and_an_ordinary_commit(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The #278 end-to-end canary: no `git add -f`, no manual marker or registry edit."""
    repository, envelope = _init_with_ignore(tmp_path, registry, monkeypatch, ".aether/")
    assert envelope.result == "changed", envelope.errors
    project_id = envelope.data["project_id"]

    store = ObjectiveContractStore(registry=registry)
    started = store.begin(project_id=project_id, title="Handoff canary", session_id="s_canary_0278")
    contract_id = started["contract_id"]
    revision = started["revision"]
    for section in (
        "owner_intent",
        "objective",
        "decisions_and_assumptions",
        "in_scope",
        "out_of_scope",
        "authority",
        "deliverables",
        "acceptance_criteria",
        "testing_standard",
        "stop_conditions",
        "canonical_references",
    ):
        result = store.set_section(
            project_id=project_id,
            contract_id=contract_id,
            section=section,
            content=f"Canary content for {section}.",
            expected_revision=revision,
            session_id="s_canary_0278",
        )
        revision = result["revision"]
    final = store.finalize(
        project_id=project_id,
        contract_id=contract_id,
        expected_revision=revision,
        session_id="s_canary_0278",
    )
    final_relative = f".aether/objective-contracts/{contract_id}/v{final['version']}.md"

    # The ordinary workflow: plain `git add`, no force.
    subprocess.run(("git", "add", "-A"), cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ("git", "commit", "-m", "aether: project identity and contract"),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    tracked = subprocess.run(
        ("git", "ls-files", ".aether"), cwd=repository, capture_output=True, text=True, check=True
    ).stdout.split()
    assert ".aether/project.toml" in tracked
    assert final_relative in tracked
    assert not any(entry.startswith(".aether/drafts/") for entry in tracked)

    handoff = store.prepare_handoff(
        project_id=project_id, contract_id=contract_id, version=final["version"]
    )
    assert handoff["handoff_ready"] is True, handoff


def test_init_preserves_existing_agents_and_does_not_invent_missing_guidance(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _git_repository(tmp_path / "existing")
    agents = existing / "AGENTS.md"
    original = "# Existing project rules\n\nKeep this exact guidance.\n"
    agents.write_text(original, encoding="utf-8")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
        str(
            _hermes_home(
                tmp_path / "existing-home", [("p_existing", "existing", "Existing", existing)]
            )
        ),
    )

    initialized = run_init(_args(existing), registry=registry)

    assert initialized.result == "changed", initialized.errors
    assert agents.read_text(encoding="utf-8") == original

    missing = _git_repository(tmp_path / "missing")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT",
        str(
            _hermes_home(tmp_path / "missing-home", [("p_missing", "missing", "Missing", missing)])
        ),
    )

    initialized = run_init(_args(missing), registry=registry)

    assert initialized.result == "changed", initialized.errors
    assert not (missing / "AGENTS.md").exists()


def test_project_canonical_skill_is_discoverable_from_root_agents_convention(
    tmp_path: Path,
) -> None:
    repository = _git_repository(tmp_path / "repo")
    agents = repository / "AGENTS.md"
    agents.write_text(
        (Path(__file__).parents[1] / "AGENTS.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    skill = repository / ".aether" / "skills" / "example" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\n---\n# Example\n", encoding="utf-8")

    guidance = agents.read_text(encoding="utf-8")

    assert ".aether/skills/<skill-name>/SKILL.md" in guidance
    assert skill.is_file()
    assert skill.read_text(encoding="utf-8").startswith("---\nname: example")


# --- Worktrees ignore policy (issue #284) ---------------------------------------


def test_init_ignores_project_worktrees_and_keeps_owner_status_clean(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fresh brownfield init + project-linked task worktree leaves git status clean."""
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )

    envelope = run_init(_args(repository), registry=registry)
    assert envelope.result == "changed", envelope.errors
    assert _ignored(repository, ".worktrees/")
    assert _ignored(repository, ".worktrees/t_12345678/")
    assert _ignored(repository, ".worktrees/t_12345678/file.py")

    # Simulate a project-linked task worktree materialized at .worktrees/<task-id>
    task_worktree = repository / ".worktrees" / "t_12345678"
    subprocess.run(
        ("git", "worktree", "add", "-b", "wt/t_12345678", str(task_worktree)),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    # Commit a change inside the worktree
    (task_worktree / "solution.py").write_text("print('hello')\n", encoding="utf-8")
    subprocess.run(
        ("git", "add", "solution.py"), cwd=task_worktree, check=True, capture_output=True
    )
    subprocess.run(
        ("git", "commit", "-m", "work in progress"),
        cwd=task_worktree,
        check=True,
        capture_output=True,
    )

    # In the owner checkout, .worktrees/ must NOT appear in git status
    status = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert ".worktrees" not in status

    # Removing the worktree works cleanly
    subprocess.run(
        ("git", "worktree", "remove", str(task_worktree)),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    assert not task_worktree.exists()


def test_init_refuses_when_worktrees_is_already_tracked(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tracked or conflicting .worktrees refuses rather than hiding tracked content."""
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )

    # Case 1: .worktrees is a tracked file
    worktrees_file = repository / ".worktrees"
    worktrees_file.write_text("conflict file\n", encoding="utf-8")
    subprocess.run(("git", "add", ".worktrees"), cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ("git", "commit", "-m", "tracked worktrees file"),
        cwd=repository,
        check=True,
        capture_output=True,
    )

    envelope = run_init(_args(repository), registry=registry)
    assert envelope.result == "error"
    assert envelope.failure_kind == "blocked"
    assert envelope.errors[0].code == "AETHER-INIT-WORKTREES-CONFLICT"
    assert ".worktrees is already tracked in Git" in envelope.errors[0].message
    assert not (repository / ".gitignore").exists() or "/.worktrees/" not in (
        repository / ".gitignore"
    ).read_text(encoding="utf-8")

    # Dry-run also refuses
    dry_run = run_init(_args(repository, dry_run=True), registry=registry)
    assert dry_run.result == "error"
    assert dry_run.errors[0].code == "AETHER-INIT-WORKTREES-CONFLICT"


def test_init_refuses_when_worktrees_directory_content_is_tracked(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files inside .worktrees/ tracked or staged refuse initialization."""
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )

    worktrees_dir = repository / ".worktrees" / "nested"
    worktrees_dir.mkdir(parents=True)
    (worktrees_dir / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(("git", "add", ".worktrees"), cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ("git", "commit", "-m", "tracked worktrees dir"),
        cwd=repository,
        check=True,
        capture_output=True,
    )

    envelope = run_init(_args(repository), registry=registry)
    assert envelope.result == "error"
    assert envelope.failure_kind == "blocked"
    assert envelope.errors[0].code == "AETHER-INIT-WORKTREES-CONFLICT"


def test_init_refuses_when_worktrees_is_staged_in_index(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staged .worktrees file before commit also refuses initialization."""
    repository = _git_repository(tmp_path / "repo")
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )

    worktrees_dir = repository / ".worktrees"
    worktrees_dir.mkdir(parents=True)
    (worktrees_dir / "staged.txt").write_text("staged\n", encoding="utf-8")
    subprocess.run(("git", "add", ".worktrees"), cwd=repository, check=True, capture_output=True)

    envelope = run_init(_args(repository), registry=registry)
    assert envelope.result == "error"
    assert envelope.failure_kind == "blocked"
    assert envelope.errors[0].code == "AETHER-INIT-WORKTREES-CONFLICT"


def test_init_preserves_unrelated_ignore_rules_when_ignoring_worktrees(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing ignore rules for unrelated paths are preserved byte-for-byte."""
    repository = _git_repository(tmp_path / "repo")
    initial_ignore = "# Custom rules\nbuild/\n*.log\nnode_modules/\n"
    (repository / ".gitignore").write_text(initial_ignore, encoding="utf-8")
    subprocess.run(("git", "add", ".gitignore"), cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ("git", "commit", "-m", "custom gitignore"), cwd=repository, check=True, capture_output=True
    )
    monkeypatch.setenv(
        "AETHER_HERMES_ROOT", str(_hermes_home(tmp_path, [("p_exact", "repo", "Repo", repository)]))
    )

    envelope = run_init(_args(repository), registry=registry)
    assert envelope.result == "changed", envelope.errors
    content = (repository / ".gitignore").read_text(encoding="utf-8")
    assert content.startswith(initial_ignore)
    assert "/.worktrees/" in content
    assert _ignored(repository, "build/out.bin")
    assert _ignored(repository, "app.log")
    assert _ignored(repository, "node_modules/pkg/index.js")
    assert _ignored(repository, ".worktrees/")


def test_unborn_git_root_init(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unborn Git root (git init, no commits) is accepted without creating commits or remotes."""
    repo = tmp_path / "unborn-repo"
    repo.mkdir()
    subprocess.run(("git", "init", "-b", "main"), cwd=repo, check=True, capture_output=True)

    # Verify HEAD^{commit} fails before init
    head_before = subprocess.run(
        ("git", "rev-parse", "--verify", "HEAD^{commit}"),
        cwd=repo,
        capture_output=True,
    )
    assert head_before.returncode != 0

    hermes_root = _hermes_home(tmp_path, [])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "changed", envelope.errors
    assert envelope.changed is True

    # Verify HEAD^{commit} STILL fails after init (no commit created)
    head_after = subprocess.run(
        ("git", "rev-parse", "--verify", "HEAD^{commit}"),
        cwd=repo,
        capture_output=True,
    )
    assert head_after.returncode != 0

    # Verify no git remotes created
    remotes = subprocess.run(("git", "remote"), cwd=repo, capture_output=True, text=True)
    assert remotes.stdout.strip() == ""

    # Verify marker
    marker_path = repo / ".aether" / "project.toml"
    assert marker_path.is_file()
    marker = tomllib.loads(marker_path.read_text(encoding="utf-8"))
    validate_project_marker(marker)
    assert marker["project_id"] == envelope.data["project_id"]
    assert marker["default_branch"] == "main"
    assert "hermes_project_id" not in marker

    # Verify native project in projects.db
    db_path = hermes_root / "profiles" / "morfeo" / "projects.db"
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, primary_path FROM projects").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == envelope.data["hermes_project_id"]
    assert Path(rows[0][1]).resolve() == repo.resolve()

    # Verify registry
    assert registry.project_path(marker["project_id"]) == repo.resolve()


def test_dry_run_purity_byte_level(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preview stays pure: no native project, no marker, no registry entry, no .gitignore mutation."""
    repo = _git_repository(tmp_path / "repo")
    gitignore = repo / ".gitignore"
    gitignore.write_text("existing-rule/\n", encoding="utf-8")
    before_bytes = gitignore.read_bytes()

    hermes_root = _hermes_home(tmp_path, [])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo, dry_run=True), registry=registry)
    assert envelope.result == "planned"
    assert envelope.changed is False
    assert envelope.data["hermes_project_action"] == "create"
    assert envelope.data["hermes_project_id"] is None

    # .gitignore unchanged byte-for-byte
    assert gitignore.read_bytes() == before_bytes
    # No .aether directory
    assert not (repo / ".aether").exists()
    # No registry file
    assert not registry.path.exists()
    # projects.db still empty
    db_path = hermes_root / "profiles" / "morfeo" / "projects.db"
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT count(*) FROM projects").fetchone()[0] == 0
    conn.close()


def test_retry_after_interruption_following_native_creation(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interruption after native creation permits exact-path retry without duplicate or cleanup."""
    repo = _git_repository(tmp_path / "repo")
    # Simulate native project already created in projects.db, but marker not yet written
    hermes_root = _hermes_home(tmp_path, [("p_interrupted", "repo", "Repo", repo)])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    # Retry proceeds
    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "changed"
    assert envelope.data["hermes_project_id"] == "p_interrupted"
    assert envelope.data["hermes_project_action"] == "reuse"

    # Exactly one project in database (no duplicate)
    db_path = hermes_root / "profiles" / "morfeo" / "projects.db"
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT count(*) FROM projects").fetchone()[0] == 1
    conn.close()

    # Marker and registry completed
    assert (repo / ".aether" / "project.toml").is_file()
    assert registry.project_path(envelope.data["project_id"]) == repo.resolve()


def test_refuse_archived_exact_path_match(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An archived exact-path match is a visible identity conflict, refusing replacement."""
    repo = _git_repository(tmp_path / "repo")
    hermes_root = _hermes_home(tmp_path, [("p_archived", "repo", "Repo", repo, 1)])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-HERMES-PROJECT-ARCHIVED"
    assert not (repo / ".aether").exists()


def test_refuse_cross_profile_path(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Paths inside a Hermes profile directory are refused."""
    hermes_root = _hermes_home(tmp_path, [])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    profile_home = hermes_root / "profiles" / "morfeo"
    repo_in_profile = _git_repository(profile_home / "nested-repo")

    envelope = run_init(_args(repo_in_profile), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-CROSS-PROFILE-PATH"
    assert not (repo_in_profile / ".aether").exists()


def test_refuse_plain_directory_actionable_guidance(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain non-Git directory is refused with actionable git init guidance and zero mutation."""
    hermes_root = _hermes_home(tmp_path, [])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))
    plain = tmp_path / "plain-folder"
    plain.mkdir()

    envelope = run_init(_args(plain), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-NOT-A-GIT-REPOSITORY"
    assert "git init" in envelope.errors[0].message
    assert list(plain.iterdir()) == []


def test_refuse_symlinked_gitignore(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlinked .gitignore is refused before modification."""
    repo = _git_repository(tmp_path / "repo")
    target = tmp_path / "external-ignore"
    target.write_text("some-rule/\n", encoding="utf-8")
    (repo / ".gitignore").symlink_to(target)

    hermes_root = _hermes_home(tmp_path, [("p_exact", "repo", "Repo", repo)])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-IGNORE-POLICY-UNSAFE"


def test_init_creates_native_project_when_projects_db_absent(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When projects.db does not exist at all, it counts as zero matches and create succeeds."""
    repo = _git_repository(tmp_path / "repo")
    hermes_root = tmp_path / "fresh-hermes-root"
    (hermes_root / "profiles" / "morfeo").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "changed", envelope.errors
    assert envelope.data["hermes_project_action"] == "create"
    assert (repo / ".aether" / "project.toml").is_file()
    assert (hermes_root / "profiles" / "morfeo" / "projects.db").is_file()


def test_refuse_when_projects_db_unreadable_or_corrupt(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Genuinely unreadable / corrupt projects.db keeps projects-unavailable refusal."""
    repo = _git_repository(tmp_path / "repo")
    hermes_root = tmp_path / "corrupt-hermes-root"
    profile_home = hermes_root / "profiles" / "morfeo"
    profile_home.mkdir(parents=True, exist_ok=True)
    (profile_home / "projects.db").write_bytes(b"not a valid sqlite database header at all")
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code in (
        "AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE",
        "AETHER-INIT-HERMES-PROJECTS-UNREADABLE",
    )
    assert not (repo / ".aether").exists()


def test_refuse_when_projects_db_schema_invalid(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A SQLite db lacking expected projects schema refuses with unreadable error."""
    repo = _git_repository(tmp_path / "repo")
    hermes_root = tmp_path / "invalid-schema-root"
    profile_home = hermes_root / "profiles" / "morfeo"
    profile_home.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(profile_home / "projects.db")
    conn.execute("CREATE TABLE wrong_table (id INT)")
    conn.close()
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-HERMES-PROJECTS-UNREADABLE"
    assert not (repo / ".aether").exists()


def test_brownfield_preservation_with_dirty_state(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing governance, uncommitted files, branches, remotes are preserved."""
    repo = _git_repository(tmp_path / "repo")
    (repo / "AGENTS.md").write_text("# Custom Agents\n", encoding="utf-8")
    (repo / "dirty.txt").write_text("uncommitted content\n", encoding="utf-8")
    subprocess.run(
        ("git", "remote", "add", "origin", "git@github.com:TestOrg/repo.git"),
        cwd=repo,
        check=True,
        capture_output=True,
    )
    hermes_root = _hermes_home(tmp_path, [("p_exact", "repo", "Repo", repo)])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "changed", envelope.errors

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# Custom Agents\n"
    assert (repo / "dirty.txt").read_text(encoding="utf-8") == "uncommitted content\n"
    assert (repo / "README.md").read_text(encoding="utf-8") == "brownfield\n"
    remotes = subprocess.run(("git", "remote", "-v"), cwd=repo, capture_output=True, text=True)
    assert "TestOrg/repo.git" in remotes.stdout


def test_refuse_dangling_symlinked_gitignore(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dangling symlink for .gitignore is refused before modification; target is not created."""
    repo = _git_repository(tmp_path / "repo")
    target = tmp_path / "nonexistent-ignore-target"
    (repo / ".gitignore").symlink_to(target)

    hermes_root = _hermes_home(tmp_path, [("p_exact", "repo", "Repo", repo)])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    # Real run refuses before any write
    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-IGNORE-POLICY-UNSAFE"
    assert (repo / ".gitignore").is_symlink()
    assert not target.exists()

    # Dry-run also refuses safely without creating target
    dry_envelope = run_init(_args(repo, dry_run=True), registry=registry)
    assert dry_envelope.result == "error"
    assert dry_envelope.errors[0].code == "AETHER-INIT-IGNORE-POLICY-UNSAFE"
    assert (repo / ".gitignore").is_symlink()
    assert not target.exists()


def test_refuse_symlinked_or_dangling_marker(
    tmp_path: Path, registry: ProjectRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlinked or dangling symlinked marker is refused with AETHER-INIT-MARKER-UNSAFE."""
    repo = _git_repository(tmp_path / "repo")
    aether_dir = repo / ".aether"
    aether_dir.mkdir(parents=True, exist_ok=True)
    marker_path = aether_dir / "project.toml"

    missing_target = tmp_path / "missing-marker.toml"
    marker_path.symlink_to(missing_target)

    hermes_root = _hermes_home(tmp_path, [("p_exact", "repo", "Repo", repo)])
    monkeypatch.setenv("AETHER_HERMES_ROOT", str(hermes_root))

    # Dangling symlink refusal
    envelope = run_init(_args(repo), registry=registry)
    assert envelope.result == "error"
    assert envelope.errors[0].code == "AETHER-INIT-MARKER-UNSAFE"
    assert marker_path.is_symlink()
    assert not missing_target.exists()

    # Live symlink refusal
    marker_path.unlink()
    live_target = tmp_path / "live-marker.toml"
    live_target.write_text("name = 'live'\nproject_id = '01234567-89ab-cdef-0123-456789abcdef'\n")
    marker_path.symlink_to(live_target)

    envelope_live = run_init(_args(repo), registry=registry)
    assert envelope_live.result == "error"
    assert envelope_live.errors[0].code == "AETHER-INIT-MARKER-UNSAFE"
    assert marker_path.is_symlink()
