"""Focused MON-02 tests for exact source identity, read-only state, and bounded cuts."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from aether_agents.monitor import sources as sources_module
from aether_agents.monitor.collector import (
    MonitorCollector,
    SnapshotBoundsError,
    build_bounded_snapshot,
)
from aether_agents.monitor.sources import (
    ReadOnlySourceError,
    ReadOnlySources,
    SourceCollection,
    SourceItem,
    _read_board_bindings,
    _resolve_board_paths,
    enumerate_project_bindings,
    open_read_only_sqlite,
)
from aether_agents.monitor.store import MonitorStore
from aether_agents.observation.context import ProjectRegistry

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
PROJECT_B = "22222222-2222-4222-8222-222222222222"
CONTRACT_ID = "oc_abcdef0123456789"
CONTRACT_B = "oc_1234567890abcdef"
CONTRACT_C = "oc_fedcba9876543210"
NATIVE_PROJECT = "p_native"
NATIVE_PROJECT_B = "p_native_b"
ORIGIN = "origin-1"
ORIGIN_B = "origin-2"
ORIGIN_C = "origin-3"
FINALIZER = "finalizer-1"
FINALIZER_B = "finalizer-2"
FINALIZER_C = "finalizer-3"
BOARD_SLUG = "oc-11111111111141118111111111111111-abcdef0123456789-v1"
BOARD_SLUG_B = "oc-22222222222242228222222222222222-1234567890abcdef-v1"
BOARD_SLUG_C = "oc-11111111111141118111111111111111-fedcba9876543210-v1"


_PROJECT_SCHEMA = """
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    primary_path TEXT,
    archived INTEGER NOT NULL DEFAULT 0
)
"""

_BOARD_SCHEMA = """
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    project_id TEXT,
    session_id TEXT,
    created_at REAL,
    started_at REAL,
    completed_at REAL,
    workspace_path TEXT,
    current_run_id INTEGER,
    session_affinity TEXT,
    block_kind TEXT,
    last_heartbeat_at REAL,
    max_runtime_seconds INTEGER,
    result TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE task_links (parent_id TEXT NOT NULL, child_id TEXT NOT NULL);
CREATE TABLE task_runs (
    id INTEGER PRIMARY KEY,
    task_id TEXT,
    status TEXT,
    outcome TEXT,
    started_at REAL,
    ended_at REAL,
    last_heartbeat_at REAL,
    summary TEXT,
    error TEXT,
    profile TEXT
);
CREATE TABLE task_events (
    id INTEGER PRIMARY KEY,
    task_id TEXT,
    run_id INTEGER,
    kind TEXT,
    payload TEXT,
    created_at REAL
);
"""

_SESSION_SCHEMA = """
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    display_name TEXT,
    cwd TEXT,
    git_repo_root TEXT,
    started_at REAL,
    ended_at REAL,
    last_activity_at REAL
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp REAL
);
"""


def _write_project(
    project: Path, *, name: str = "Collision Name", project_id: str = PROJECT_ID
) -> None:
    (project / ".aether").mkdir(parents=True, exist_ok=True)
    (project / ".aether" / "project.toml").write_text(
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


def _write_contract(
    project: Path,
    *,
    project_id: str = PROJECT_ID,
    contract_id: str = CONTRACT_ID,
    origin: str = ORIGIN,
    finalized: str = FINALIZER,
    metadata_overrides: dict[str, Any] | None = None,
) -> None:
    contract_dir = project / ".aether" / "objective-contracts" / contract_id
    contract_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "artifact_type": "aether.objective-contract.v1",
        "project_id": project_id,
        "contract_id": contract_id,
        "version": 1,
        "status": "final",
        "title": "Bound fixture objective",
        "created_at_utc": "2026-09-09T12:00:00Z",
        "created_at_local": "2026-09-09T06:00:00-06:00",
        "finalized_at_utc": "2026-09-09T12:05:00Z",
        "finalized_at_local": "2026-09-09T06:05:00-06:00",
        "author_profile": "morfeo",
        "created_in_session": origin,
        "finalized_in_session": finalized,
        "supersedes": None,
        "change_reason": None,
        "observation_trace_id": "ctr_" + "1" * 32,
    }
    if metadata_overrides is not None:
        metadata.update(metadata_overrides)
    lines = ["---"] + [f"{key}: {json.dumps(value)}" for key, value in metadata.items()]
    lines += [
        "---",
        "",
        "# Objective Contract: Bound fixture objective",
        "",
        "## Objective",
        "",
        "fixture",
        "",
    ]
    (contract_dir / "v1.md").write_text("\n".join(lines), encoding="utf-8")


def _sqlite(path: Path, script: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(script)
        connection.commit()


def _fixture(tmp_path: Path) -> dict[str, Any]:
    project = tmp_path / "project"
    project.mkdir()
    _write_project(project)
    _write_contract(project)

    state = tmp_path / "aether-state"
    registry = ProjectRegistry(state)
    assert registry.register(PROJECT_ID, project, "Registry Collision Name", NATIVE_PROJECT)

    hermes = tmp_path / "hermes"
    hermes.mkdir()
    projects_db = hermes / "projects.db"
    _sqlite(projects_db, _PROJECT_SCHEMA)
    with sqlite3.connect(projects_db) as connection:
        connection.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, 0)",
            (NATIVE_PROJECT, "fixture", "Native Collision Name", str(project)),
        )
        connection.commit()

    session_db = hermes / "origin-state.db"
    _sqlite(session_db, _SESSION_SCHEMA)
    with sqlite3.connect(session_db) as connection:
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ORIGIN,
                "tui",
                "Origin build session",
                "Origin build session",
                str(project),
                str(project),
                1788955200.0,
                None,
                1788958800.0,
            ),
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "cron-report",
                "cron",
                "Monitor report",
                "Monitor report",
                str(project),
                str(project),
                1,
                None,
                1,
            ),
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                FINALIZER,
                "tui",
                "Contract finalizer session",
                "Contract finalizer session",
                str(project),
                str(project),
                1788955200.0,
                1788955500.0,
                1788955500.0,
            ),
        )
        connection.executemany(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
            [
                (1, ORIGIN, "user", "private transcript", 1788955200.0),
                (2, "cron-report", "assistant", "private report", 1788955201.0),
            ],
        )
        connection.commit()

    board_dir = tmp_path / "board" / BOARD_SLUG
    board_dir.mkdir(parents=True)
    (board_dir / "board.json").write_text(
        json.dumps(
            {
                "slug": BOARD_SLUG,
                "name": "Collision Board",
                "project_id": NATIVE_PROJECT,
                "default_workdir": str(project.resolve()),
                "aether_project_id": PROJECT_ID,
                "aether_contract_id": CONTRACT_ID,
                "aether_contract_version": 1,
            }
        ),
        encoding="utf-8",
    )
    board_db = board_dir / "kanban.db"
    _sqlite(board_db, _BOARD_SCHEMA)
    with sqlite3.connect(board_db) as connection:
        connection.executemany(
            "INSERT INTO tasks (id, title, status, project_id, session_id, created_at, started_at, completed_at, workspace_path, current_run_id, session_affinity, last_heartbeat_at, max_runtime_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "t_11111111",
                    "Root completed",
                    "done",
                    NATIVE_PROJECT,
                    ORIGIN,
                    1788955200,
                    1788955200,
                    1788957000,
                    str(project),
                    1,
                    '{"flow_id":"flow-1"}',
                    1788957000,
                    120,
                ),
                (
                    "t_22222222",
                    "Terminal review",
                    "review",
                    NATIVE_PROJECT,
                    ORIGIN,
                    1788955200,
                    1788957000,
                    None,
                    str(project),
                    2,
                    '{"flow_id":"flow-1", "terminal": true}',
                    1788958800,
                    120,
                ),
            ],
        )
        connection.execute("INSERT INTO task_links VALUES (?, ?)", ("t_11111111", "t_22222222"))
        connection.executemany(
            "INSERT INTO task_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    "t_11111111",
                    "done",
                    "completed",
                    1788955200,
                    1788957000,
                    1788957000,
                    "root verified",
                    None,
                    "implementer",
                ),
                (
                    2,
                    "t_22222222",
                    "running",
                    None,
                    1788957000,
                    None,
                    1788958800,
                    None,
                    None,
                    "supervisor",
                ),
            ],
        )
        connection.execute(
            "INSERT INTO task_events VALUES (?, ?, ?, ?, ?, ?)",
            (1, "t_22222222", 2, "review_requested", '{"code":"REVIEW_WAIT"}', 1788958800),
        )
        connection.commit()

    return {
        "project": project,
        "state": state,
        "registry": registry,
        "projects_db": projects_db,
        "session_db": session_db,
        "board_db": board_db,
        "board_dir": board_dir,
        "hermes": hermes,
    }


def _sources(fixture: dict[str, Any]) -> ReadOnlySources:
    return ReadOnlySources(
        registry=fixture["registry"],
        native_projects_path=fixture["projects_db"],
        board_paths=[(BOARD_SLUG, fixture["board_db"])],
        session_db_paths=[fixture["session_db"]],
        hermes_home=fixture["hermes"],
    )


def _insert_session(
    fixture: dict[str, Any],
    session_id: str,
    project: Path,
    *,
    source: str = "tui",
    title: str | None = None,
) -> None:
    with sqlite3.connect(fixture["session_db"]) as connection:
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                source,
                title or session_id,
                title or session_id,
                str(project),
                str(project),
                1788955200.0,
                None,
                1788958800.0,
            ),
        )
        connection.commit()


def _write_bound_board(
    fixture: dict[str, Any],
    *,
    project: Path,
    project_id: str,
    native_project_id: str,
    contract_id: str,
    board_slug: str,
    origin: str,
    finalized: str,
    task_id: str,
    status: str = "queued",
    title: str = "Additional bound work",
) -> Path:
    _write_contract(
        project,
        project_id=project_id,
        contract_id=contract_id,
        origin=origin,
        finalized=finalized,
    )
    _insert_session(fixture, origin, project, title=f"{origin} session")
    _insert_session(fixture, finalized, project, title=f"{finalized} session")
    board_dir = fixture["board_dir"].parent / board_slug
    board_dir.mkdir(parents=True)
    (board_dir / "board.json").write_text(
        json.dumps(
            {
                "slug": board_slug,
                "project_id": native_project_id,
                "default_workdir": str(project.resolve()),
                "aether_project_id": project_id,
                "aether_contract_id": contract_id,
                "aether_contract_version": 1,
            }
        ),
        encoding="utf-8",
    )
    board_db = board_dir / "kanban.db"
    _sqlite(board_db, _BOARD_SCHEMA)
    with sqlite3.connect(board_db) as connection:
        connection.execute(
            "INSERT INTO tasks (id, title, status, project_id, session_id, created_at, started_at, workspace_path, session_affinity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                title,
                status,
                native_project_id,
                origin,
                1788955200,
                1788955200,
                str(project),
                '{"flow_id":"additional-flow"}',
            ),
        )
        connection.commit()
    return board_db


def _write_conflicting_session_db(
    tmp_path: Path, session_ids: tuple[str, ...] = (ORIGIN, FINALIZER)
) -> Path:
    conflict_db = tmp_path / "conflicting-sessions.db"
    foreign = tmp_path / "conflicting-session-project"
    foreign.mkdir()
    _sqlite(conflict_db, _SESSION_SCHEMA)
    with sqlite3.connect(conflict_db) as connection:
        connection.executemany(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    session_id,
                    "tui",
                    f"Conflicting {session_id} session",
                    f"Conflicting {session_id} session",
                    str(foreign),
                    str(foreign),
                    1788955200.0,
                    None,
                    1788958800.0,
                )
                for session_id in session_ids
            ],
        )
        connection.commit()
    return conflict_db


def _monitor_store(root: Path, *, now: str = "2026-09-09T11:00:00+00:00") -> MonitorStore:
    instant = datetime.fromisoformat(now)
    store = MonitorStore(state_root=root, clock=lambda: instant)
    store.configure(native_job_id="job", profile_binding="morfeo", destination_ref="home")
    store.set_enabled(True)
    return store


def test_project_and_board_identity_is_exact_and_root_done_is_not_closure(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert len(source.items) == 1
    item = source.items[0]
    assert item.project_id == PROJECT_ID
    assert item.contract is not None and item.contract["id"] == CONTRACT_ID
    assert item.origin_session_id == ORIGIN
    assert item.observed_state == "review"
    assert any(fact["text"] == "REVIEW_GATE" for fact in item.next)
    assert "cron-report" not in item.origin_session_id
    assert not any("private" in json.dumps(fact) for fact in item.current)
    assert not source.idle


def test_contract_origin_and_finalizer_are_distinct_verified_sessions(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert len(source.items) == 1
    assert source.items[0].origin_session_id == ORIGIN
    assert ORIGIN != FINALIZER
    assert not any(gap.startswith("CONTRACT_FINALIZED_") for gap in source.coverage_gaps)


@pytest.mark.parametrize(
    ("mutation", "expected_gap"),
    (
        ("missing", "CONTRACT_FINALIZED_SESSION_MISSING"),
        ("reporter", "CONTRACT_FINALIZED_SESSION_CONFLICT"),
        ("foreign", "CONTRACT_FINALIZED_PROJECT_CONFLICT"),
    ),
)
def test_finalized_contract_session_must_be_present_nonreporter_and_project_bound(
    tmp_path: Path, mutation: str, expected_gap: str
) -> None:
    fixture = _fixture(tmp_path)
    if mutation == "missing":
        with sqlite3.connect(fixture["session_db"]) as connection:
            connection.execute("DELETE FROM sessions WHERE id = ?", (FINALIZER,))
            connection.commit()
    elif mutation == "reporter":
        with sqlite3.connect(fixture["session_db"]) as connection:
            connection.execute("UPDATE sessions SET source = ? WHERE id = ?", ("cron", FINALIZER))
            connection.commit()
    else:
        foreign = tmp_path / "foreign-finalizer"
        foreign.mkdir()
        with sqlite3.connect(fixture["session_db"]) as connection:
            connection.execute(
                "UPDATE sessions SET cwd = ?, git_repo_root = ? WHERE id = ?",
                (str(foreign), str(foreign), FINALIZER),
            )
            connection.commit()

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert source.items == ()
    assert expected_gap in source.coverage_gaps
    assert not source.idle


@pytest.mark.parametrize(
    ("mutation", "expected_gap"),
    (
        ("missing_id", "BOARD_NATIVE_PROJECT_MISSING"),
        ("conflicting_id", "BOARD_NATIVE_PROJECT_CONFLICT"),
        ("missing_path", "BOARD_PROJECT_PATH_MISSING"),
        ("conflicting_path", "BOARD_PROJECT_PATH_CONFLICT"),
    ),
)
def test_board_requires_canonical_native_project_id_and_root_path(
    tmp_path: Path, mutation: str, expected_gap: str
) -> None:
    fixture = _fixture(tmp_path)
    metadata_path = fixture["board_dir"] / "board.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if mutation == "missing_id":
        del metadata["project_id"]
    elif mutation == "conflicting_id":
        metadata["project_id"] = "foreign-native-project"
    elif mutation == "missing_path":
        del metadata["default_workdir"]
    else:
        foreign = tmp_path / "foreign-board-root"
        foreign.mkdir()
        metadata["default_workdir"] = str(foreign)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert source.items == ()
    assert expected_gap in source.coverage_gaps
    assert not source.idle


@pytest.mark.parametrize(
    ("mutation", "expected_gap"),
    (
        ("contract_id", "BOARD_CONTRACT_CONFLICT"),
        ("contract_version", "BOARD_CONTRACT_CONFLICT"),
        ("slug", "BOARD_IDENTITY_CONFLICT"),
    ),
)
def test_board_contract_aliases_and_metadata_slug_must_agree(
    tmp_path: Path, mutation: str, expected_gap: str
) -> None:
    fixture = _fixture(tmp_path)
    metadata_path = fixture["board_dir"] / "board.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if mutation == "contract_id":
        metadata["contract_id"] = CONTRACT_B
    elif mutation == "contract_version":
        metadata["contract_version"] = 2
    else:
        metadata["slug"] = BOARD_SLUG_B
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert source.items == ()
    assert expected_gap in source.coverage_gaps
    assert not source.idle


@pytest.mark.parametrize(
    ("conflicted_session", "pipeline_gap"),
    (
        (ORIGIN, "CONTRACT_ORIGIN_SESSION_MISSING"),
        (FINALIZER, "CONTRACT_FINALIZED_SESSION_MISSING"),
    ),
)
def test_conflicted_session_ids_are_not_used_for_pipeline_or_direct_resolution(
    tmp_path: Path, conflicted_session: str, pipeline_gap: str
) -> None:
    fixture = _fixture(tmp_path)
    conflict_db = _write_conflicting_session_db(tmp_path, (conflicted_session,))
    direct = {
        "project_id": PROJECT_ID,
        "native_project_id": NATIVE_PROJECT,
        "project_path": str(fixture["project"]),
        "session_id": conflicted_session,
        "interval_id": "conflicted-direct",
        "outcome": "completed",
    }
    source = ReadOnlySources(
        registry=fixture["registry"],
        native_projects_path=fixture["projects_db"],
        board_paths=[(BOARD_SLUG, fixture["board_db"])],
        session_db_paths=[fixture["session_db"], conflict_db],
        hermes_home=fixture["hermes"],
    ).collect(cutoff_utc="2026-09-09T14:00:00Z", direct_records=[direct])

    assert source.items == ()
    assert "SESSION_ID_CONFLICT" in source.coverage_gaps
    assert pipeline_gap in source.coverage_gaps
    assert "DIRECT_SESSION_MISSING" in source.coverage_gaps
    assert not source.idle


@pytest.mark.parametrize(
    ("role", "session_id", "pipeline_gap"),
    (
        ("creator", "supervisor-session", "TASK_CREATOR_SESSION_MISSING"),
        ("worker", "worker-session", "WORKER_SESSION_MISSING"),
    ),
)
def test_conflicted_creator_or_worker_session_is_not_used(
    tmp_path: Path, role: str, session_id: str, pipeline_gap: str
) -> None:
    fixture = _fixture(tmp_path)
    _insert_session(fixture, session_id, fixture["project"], title=f"{role} session")
    with sqlite3.connect(fixture["board_db"]) as connection:
        if role == "creator":
            connection.execute("UPDATE tasks SET session_id = ?", (session_id,))
        else:
            connection.execute("ALTER TABLE task_runs ADD COLUMN worker_session_id TEXT")
            connection.execute("UPDATE task_runs SET worker_session_id = ?", (session_id,))
        connection.commit()
    conflict_db = _write_conflicting_session_db(tmp_path, (session_id,))
    direct = {
        "project_id": PROJECT_ID,
        "native_project_id": NATIVE_PROJECT,
        "project_path": str(fixture["project"]),
        "session_id": session_id,
        "interval_id": f"conflicted-{role}",
        "outcome": "completed",
    }
    source = ReadOnlySources(
        registry=fixture["registry"],
        native_projects_path=fixture["projects_db"],
        board_paths=[(BOARD_SLUG, fixture["board_db"])],
        session_db_paths=[fixture["session_db"], conflict_db],
        hermes_home=fixture["hermes"],
    ).collect(cutoff_utc="2026-09-09T14:00:00Z", direct_records=[direct])

    assert source.items == ()
    assert "SESSION_ID_CONFLICT" in source.coverage_gaps
    assert pipeline_gap in source.coverage_gaps
    assert "DIRECT_SESSION_MISSING" in source.coverage_gaps
    assert not source.idle


def test_two_bound_projects_with_colliding_names_are_kept_separate(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    project_b = tmp_path / "project-b"
    project_b.mkdir()
    _write_project(project_b, project_id=PROJECT_B)
    _write_contract(
        project_b,
        project_id=PROJECT_B,
        contract_id=CONTRACT_B,
        origin=ORIGIN_B,
        finalized=FINALIZER_B,
    )
    registry: ProjectRegistry = fixture["registry"]
    assert registry.register(PROJECT_B, project_b, "Registry Collision Name", NATIVE_PROJECT_B)

    with sqlite3.connect(fixture["projects_db"]) as connection:
        connection.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, 0)",
            (NATIVE_PROJECT_B, "fixture-b", "Native Collision Name", str(project_b)),
        )
        connection.commit()
    with sqlite3.connect(fixture["session_db"]) as connection:
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ORIGIN_B,
                "tui",
                "Origin B session",
                "Origin B session",
                str(project_b),
                str(project_b),
                1788955200.0,
                None,
                1788958800.0,
            ),
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                FINALIZER_B,
                "tui",
                "Finalizer B session",
                "Finalizer B session",
                str(project_b),
                str(project_b),
                1788955200.0,
                1788955500.0,
                1788955500.0,
            ),
        )
        connection.commit()

    board_b_dir = tmp_path / "board" / BOARD_SLUG_B
    board_b_dir.mkdir(parents=True)
    (board_b_dir / "board.json").write_text(
        json.dumps(
            {
                "slug": BOARD_SLUG_B,
                "project_id": NATIVE_PROJECT_B,
                "default_workdir": str(project_b.resolve()),
                "aether_project_id": PROJECT_B,
                "aether_contract_id": CONTRACT_B,
                "aether_contract_version": 1,
            }
        ),
        encoding="utf-8",
    )
    board_b = board_b_dir / "kanban.db"
    _sqlite(board_b, _BOARD_SCHEMA)
    with sqlite3.connect(board_b) as connection:
        connection.execute(
            "INSERT INTO tasks (id, title, status, project_id, session_id, created_at, started_at, session_affinity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "t_33333333",
                "Project B blocked",
                "blocked",
                NATIVE_PROJECT_B,
                ORIGIN_B,
                1788955200,
                1788955200,
                '{"flow_id":"flow-b"}',
            ),
        )
        connection.commit()

    source = ReadOnlySources(
        registry=registry,
        native_projects_path=fixture["projects_db"],
        board_paths=[(BOARD_SLUG, fixture["board_db"]), (BOARD_SLUG_B, board_b)],
        session_db_paths=[fixture["session_db"]],
        hermes_home=fixture["hermes"],
    ).collect(cutoff_utc="2026-09-09T14:00:00Z")
    assert len(source.items) == 2
    identities = {
        (item.project_id, item.origin_session_id, item.contract["id"])
        for item in source.items
        if item.contract
    }
    assert identities == {(PROJECT_ID, ORIGIN, CONTRACT_ID), (PROJECT_B, ORIGIN_B, CONTRACT_B)}
    assert {item.project_name for item in source.items} == {"Collision Name"}
    assert {item.observed_state for item in source.items} == {"review", "blocked"}


def test_same_project_multiple_contracts_and_origins_stay_distinct(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    board_c = _write_bound_board(
        fixture,
        project=fixture["project"],
        project_id=PROJECT_ID,
        native_project_id=NATIVE_PROJECT,
        contract_id=CONTRACT_C,
        board_slug=BOARD_SLUG_C,
        origin=ORIGIN_C,
        finalized=FINALIZER_C,
        task_id="t_44444444",
        status="queued",
        title="Second contract queued",
    )
    source = ReadOnlySources(
        registry=fixture["registry"],
        native_projects_path=fixture["projects_db"],
        board_paths=[(BOARD_SLUG, fixture["board_db"]), (BOARD_SLUG_C, board_c)],
        session_db_paths=[fixture["session_db"]],
        hermes_home=fixture["hermes"],
    ).collect(cutoff_utc="2026-09-09T14:00:00Z")

    identities = {
        (item.project_id, item.origin_session_id, item.contract["id"])
        for item in source.items
        if item.contract is not None
    }
    assert identities == {
        (PROJECT_ID, ORIGIN, CONTRACT_ID),
        (PROJECT_ID, ORIGIN_C, CONTRACT_C),
    }
    assert len({item.work_key for item in source.items}) == 2
    assert {item.observed_state for item in source.items} == {"review", "queued"}
    assert source.coverage_gaps == ()


def test_root_done_without_terminal_affinity_is_not_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    with sqlite3.connect(fixture["board_db"]) as connection:
        connection.execute("DELETE FROM task_events")
        connection.execute("DELETE FROM task_runs WHERE task_id = ?", ("t_22222222",))
        connection.execute("DELETE FROM task_links")
        connection.execute("DELETE FROM tasks WHERE id = ?", ("t_22222222",))
        connection.commit()
    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")
    assert len(source.items) == 1
    assert source.items[0].observed_state == "waiting"
    assert "TERMINAL_CLOSURE_UNRESOLVED" in source.items[0].coverage_gaps
    assert not source.idle


def test_direct_turn_ended_without_contract_and_reporter_are_normalized(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    records = [
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": ORIGIN,
            "interval_id": "interval-1",
            "outcome": "completed",
            "started_at": "2026-09-09T13:00:00-06:00",
            "ended_at": "2026-09-09T13:10:00-06:00",
            "summary": "Turn outcome, not project acceptance.",
        },
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": "cron-report",
            "interval_id": "interval-report",
            "outcome": "completed",
        },
    ]
    source = _sources(fixture).collect(
        cutoff_utc="2026-09-09T14:00:00Z",
        direct_records=records,
    )
    direct = [item for item in source.items if item.contract is None]
    assert len(direct) == 1
    assert direct[0].observed_state == "turn_ended_completed"
    assert any(fact["text"] == "TURN_ENDED_COMPLETED" for fact in direct[0].current)
    assert any(fact["text"] == "PROJECT_ACCEPTANCE_NOT_OBSERVED" for fact in direct[0].next)


def test_contract_origin_creator_and_worker_sessions_are_separately_bound(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _insert_session(fixture, "supervisor-session", fixture["project"], title="Supervisor creator")
    _insert_session(fixture, "worker-session", fixture["project"], title="Worker execution")
    with sqlite3.connect(fixture["board_db"]) as connection:
        connection.execute("ALTER TABLE task_runs ADD COLUMN worker_session_id TEXT")
        connection.execute(
            "UPDATE tasks SET session_id = ?",
            ("supervisor-session",),
        )
        connection.execute(
            "UPDATE task_runs SET worker_session_id = ?",
            ("worker-session",),
        )
        connection.commit()

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert len(source.items) == 1
    assert source.items[0].origin_session_id == ORIGIN
    assert "CONTRACT_ORIGIN_CONFLICT" not in source.coverage_gaps
    assert "TASK_CREATOR_PROJECT_CONFLICT" not in source.coverage_gaps
    assert "WORKER_SESSION_PROJECT_CONFLICT" not in source.coverage_gaps


@pytest.mark.parametrize(
    ("status", "expected_state"),
    (
        ("queued", "queued"),
        ("triage", "triage"),
        ("blocked", "blocked"),
        ("review", "review"),
        ("running", "running"),
        ("failed", "failed"),
        ("done", "completed"),
    ),
)
def test_task_lifecycle_states_and_stale_failure_diagnostics(
    tmp_path: Path, status: str, expected_state: str
) -> None:
    fixture = _fixture(tmp_path)
    completed = 1788960600 if status in {"failed", "done"} else None
    heartbeat = 1788955200 if status == "running" else 1788958800
    with sqlite3.connect(fixture["board_db"]) as connection:
        connection.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, last_heartbeat_at = ? WHERE id = ?",
            (status, completed, heartbeat, "t_22222222"),
        )
        connection.commit()

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")
    assert len(source.items) == 1
    item = source.items[0]
    assert item.observed_state == expected_state
    if status == "running":
        assert "TASK_STALE" in item.coverage_gaps
        assert any(fact["text"] == "TASK_STALE" for fact in item.complications)
    if status == "failed":
        assert any(fact["text"] == "TASK_FAILURE_FAILED" for fact in item.complications)
    if status == "done":
        assert any(fact["text"] == "FLOW_TERMINAL_CONFIRMED" for fact in item.resolved)


def test_direct_work_requires_exact_native_project_and_session_binding(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    foreign = tmp_path / "foreign-project"
    foreign.mkdir()
    _insert_session(fixture, "foreign-session", foreign, title="Foreign session")
    records = [
        {
            "project_id": PROJECT_ID,
            "session_id": ORIGIN,
            "interval_id": "missing-native-binding",
            "outcome": "completed",
        },
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": "foreign-session",
            "interval_id": "wrong-session-binding",
            "outcome": "completed",
        },
    ]

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z", direct_records=records)

    assert not any(item.contract is None for item in source.items)
    assert "DIRECT_NATIVE_PROJECT_CONFLICT" in source.coverage_gaps
    assert "DIRECT_SESSION_PROJECT_CONFLICT" in source.coverage_gaps
    assert not source.idle


def test_direct_continuation_intervals_remain_distinct_and_no_contract(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    records = [
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": ORIGIN,
            "interval_id": "interval-1",
            "outcome": "completed",
            "started_at": "2026-09-09T13:00:00Z",
            "ended_at": "2026-09-09T13:10:00Z",
        },
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": ORIGIN,
            "interval_id": "interval-2",
            "outcome": "interrupted",
            "started_at": "2026-09-09T13:30:00Z",
            "ended_at": "2026-09-09T13:40:00Z",
        },
    ]

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z", direct_records=records)

    assert {item.work_key for item in source.items if item.contract is None} == {
        f"direct:{PROJECT_ID}:{ORIGIN}:interval-1",
        f"direct:{PROJECT_ID}:{ORIGIN}:interval-2",
    }
    assert all(
        item.observed_state.startswith("turn_ended_")
        for item in source.items
        if item.contract is None
    )


def test_first_enable_suppresses_completed_history(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    with sqlite3.connect(fixture["board_db"]) as connection:
        connection.execute(
            "UPDATE tasks SET status = 'done', completed_at = ?, current_run_id = ? WHERE id = ?",
            (1788957600, 2, "t_22222222"),
        )
        connection.execute(
            "UPDATE task_runs SET status = 'done', outcome = 'completed', ended_at = ? WHERE id = ?",
            (1788957600, 2),
        )
        connection.commit()
    store = _monitor_store(tmp_path / "monitor-state", now="2026-09-09T14:00:00+00:00")
    result = MonitorCollector(store, _sources(fixture), owner_id="first-enable").collect(
        cutoff_utc="2026-09-09T14:30:00Z", collected_at_utc="2026-09-09T14:30:05Z"
    )

    assert result is not None
    assert result.source.items == ()
    assert result.source.idle
    assert result.snapshot.payload["items"] == []


def test_between_cut_final_is_reported_once_then_persisted_watermark_is_idle(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    monitor_root = tmp_path / "monitor-state"
    store = _monitor_store(monitor_root)
    collector = MonitorCollector(store, _sources(fixture), owner_id="cut-collector")
    first = collector.collect(
        cutoff_utc="2026-09-09T13:10:00Z", collected_at_utc="2026-09-09T13:10:05Z"
    )
    assert first is not None
    assert first.source.items and first.source.items[0].observed_state == "review"

    with sqlite3.connect(fixture["board_db"]) as connection:
        connection.execute(
            "UPDATE tasks SET status = 'done', completed_at = ?, current_run_id = ? WHERE id = ?",
            (1788960600, 3, "t_22222222"),
        )
        connection.execute(
            "INSERT INTO task_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                3,
                "t_22222222",
                "done",
                "completed",
                1788960600,
                1788960600,
                1788960600,
                "terminal outcome",
                None,
                "implementer",
            ),
        )
        connection.execute(
            "INSERT INTO task_events VALUES (?, ?, ?, ?, ?, ?)",
            (2, "t_22222222", 3, "completed", '{"summary":"terminal"}', 1788960600),
        )
        connection.commit()

    restarted = MonitorStore(
        state_root=monitor_root,
        clock=lambda: datetime.fromisoformat("2026-09-09T11:00:00+00:00"),
    )
    second = MonitorCollector(restarted, _sources(fixture), owner_id="cut-collector").collect(
        cutoff_utc="2026-09-09T14:00:00Z", collected_at_utc="2026-09-09T14:00:05Z"
    )
    assert second is not None
    assert len(second.source.items) == 1
    assert second.source.items[0].observed_state == "completed"
    serialized = json.dumps(second.snapshot.payload)
    assert "board:" + BOARD_SLUG + ":task:t_22222222:run:3" in serialized
    assert "board:" + BOARD_SLUG + ":task:t_11111111:run:1" not in serialized
    work_key = second.source.items[0].work_key
    restarted.mark_final_outcome_delivery(work_key, second.report_id)

    third = MonitorCollector(restarted, _sources(fixture), owner_id="cut-collector").collect(
        cutoff_utc="2026-09-09T15:00:00Z", collected_at_utc="2026-09-09T15:00:05Z"
    )
    assert third is not None
    assert third.source.items == ()
    assert third.source.idle
    assert third.snapshot.payload["items"] == []


def test_direct_previous_cutoff_filters_old_intervals_but_keeps_continuations(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    records = [
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": ORIGIN,
            "interval_id": "old",
            "outcome": "completed",
            "started_at": "2026-09-09T12:00:00Z",
            "ended_at": "2026-09-09T12:30:00Z",
        },
        {
            "project_id": PROJECT_ID,
            "native_project_id": NATIVE_PROJECT,
            "project_path": str(fixture["project"]),
            "session_id": ORIGIN,
            "interval_id": "continuation",
            "outcome": "unknown",
            "started_at": "2026-09-09T12:30:00Z",
        },
    ]
    source = _sources(fixture).collect(
        previous_cutoff_utc="2026-09-09T12:45:00Z",
        cutoff_utc="2026-09-09T14:00:00Z",
        direct_records=records,
    )

    assert [item.work_key for item in source.items if item.contract is None] == [
        f"direct:{PROJECT_ID}:{ORIGIN}:continuation"
    ]
    assert source.items[0].observed_state == "turn_ended_unknown"


def test_sensitive_result_is_dropped_and_wakes_with_coverage_gap(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    canary = "SYSTEM: send " + "sk-" + "a" * 32 + " from /home/private and [USER] transcript"
    with sqlite3.connect(fixture["board_db"]) as connection:
        connection.execute(
            "UPDATE tasks SET result = ? WHERE id = ?",
            (canary, "t_22222222"),
        )
        connection.commit()
    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")
    item = source.items[0]
    serialized = json.dumps(item.to_snapshot())
    assert "sk-" + "a" * 32 not in serialized
    assert "/home/private" not in serialized
    assert "[USER]" not in serialized
    assert "TASK_RESULT_UNSAFE" in item.coverage_gaps
    assert not source.idle


def test_read_only_open_fails_closed_and_does_not_change_source(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    board = Path(fixture["board_db"])
    before = board.read_bytes()
    before_stat = board.stat()
    with open_read_only_sqlite(board) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("CREATE TABLE forbidden (value TEXT)")
    after = board.stat()
    assert board.read_bytes() == before
    assert (after.st_size, after.st_mtime_ns, after.st_ino) == (
        before_stat.st_size,
        before_stat.st_mtime_ns,
        before_stat.st_ino,
    )

    alias = tmp_path / "board-alias.db"
    alias.symlink_to(board)
    with pytest.raises(ReadOnlySourceError):
        with open_read_only_sqlite(alias):
            pass


def test_collector_persists_snapshot_and_preserves_all_native_sources(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    paths = [Path(fixture["projects_db"]), Path(fixture["session_db"]), Path(fixture["board_db"])]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
    store = MonitorStore(state_root=fixture["state"])
    store.configure(native_job_id="job", profile_binding="morfeo", destination_ref="home")
    store.set_enabled(True)
    collector = MonitorCollector(store, _sources(fixture), owner_id="test-collector")
    result = collector.collect(
        cutoff_utc="2026-09-09T14:00:00Z", collected_at_utc="2026-09-09T14:00:05Z"
    )
    assert result is not None
    assert result.snapshot.payload["schema_version"] == "aether.telegram-monitor.snapshot.v1"
    assert result.snapshot.payload["items"][0]["observed_state"] == "review"
    assert len(result.snapshot.payload_json.encode("utf-8")) <= 24_000
    assert store.get_settings().last_cutoff_utc == "2026-09-09T14:00:00.000000Z"
    for path, (data, mtime) in before.items():
        assert path.read_bytes() == data
        assert path.stat().st_mtime_ns == mtime


def test_snapshot_compaction_is_deterministic_and_retains_each_identity() -> None:
    items = tuple(
        SourceItem(
            work_key=f"work-{index:03d}",
            project_id=PROJECT_ID,
            project_name="P" * 200,
            origin_session_id=f"session-{index:03d}",
            origin_session_title="S" * 200,
            contract={"id": CONTRACT_ID, "version": "v1", "title": "C" * 200},
            observed_state="running",
            current=(
                {
                    "ref": f"ref-{index}",
                    "text": "long source text " * 100,
                    "provenance": "observed",
                    "status": "verified",
                },
            ),
        )
        for index in range(100)
    )
    source = SourceCollection(items=items, watermarks={"source": 100})
    first = build_bounded_snapshot(
        report_id="rpt_" + "1" * 32,
        cutoff_utc="2026-09-09T14:00:00Z",
        collected_at_utc="2026-09-09T14:00:01Z",
        previous_cutoff_utc=None,
        source=source,
    )
    second = build_bounded_snapshot(
        report_id="rpt_" + "1" * 32,
        cutoff_utc="2026-09-09T14:00:00Z",
        collected_at_utc="2026-09-09T14:00:01Z",
        previous_cutoff_utc=None,
        source=SourceCollection(items=tuple(reversed(items)), watermarks={"source": 100}),
    )
    assert first == second
    assert len(json.dumps(first, ensure_ascii=False).encode()) <= 24_000
    assert {item["work_key"] for item in first["items"]} == {
        f"work-{index:03d}" for index in range(100)
    }
    assert "SNAPSHOT_COMPACTED" in first["coverage_gaps"] or any(
        "SNAPSHOT_COMPACTED" in item["coverage_gaps"] for item in first["items"]
    )


def test_malformed_native_project_and_marker_is_a_coverage_gap_not_idle(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    state = tmp_path / "state"
    registry = ProjectRegistry(state)
    assert registry.register(PROJECT_ID, project, "bad")
    projects_db = tmp_path / "projects.db"
    _sqlite(projects_db, _PROJECT_SCHEMA)
    with sqlite3.connect(projects_db) as connection:
        connection.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, 0)",
            (NATIVE_PROJECT, "bad", "bad", str(project)),
        )
        connection.commit()
    bindings, gaps = enumerate_project_bindings(registry, native_projects_path=projects_db)
    assert bindings == ()
    assert "PROJECT_MARKER_INVALID" in gaps
    source = ReadOnlySources(
        registry=registry, native_projects_path=projects_db, board_paths=[]
    ).collect(cutoff_utc="2026-09-09T14:00:00Z")
    assert source.items == ()
    assert not source.idle
    assert source.coverage_gaps


def test_active_identity_bound_can_fail_when_compaction_cannot_fit() -> None:
    huge = SourceCollection(
        items=tuple(
            SourceItem(
                work_key=f"x-{i}" + "z" * 5000,
                project_id=PROJECT_ID,
                project_name="P",
                origin_session_id=f"s-{i}",
                origin_session_title="S",
                contract=None,
                observed_state="running",
            )
            for i in range(20)
        ),
        watermarks={},
    )
    with pytest.raises(SnapshotBoundsError):
        build_bounded_snapshot(
            report_id="rpt_" + "2" * 32,
            cutoff_utc="2026-09-09T14:00:00Z",
            collected_at_utc="2026-09-09T14:00:01Z",
            previous_cutoff_utc=None,
            source=huge,
            max_chars=1_000,
        )


def test_root_without_default_board_store_produces_no_phantom_metadata_gap(
    tmp_path: Path,
) -> None:
    """A root that has no default board store must not produce a BOARD_METADATA_UNREADABLE gap."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    paths = _resolve_board_paths(board_paths=None, hermes_home=hermes_home)
    assert "default" not in [slug for slug, _ in paths]
    _, gaps = _read_board_bindings([], board_paths=None, hermes_home=hermes_home)
    assert "BOARD_METADATA_UNREADABLE" not in gaps


def test_root_with_unreadable_or_unbound_default_store_preserves_gap(
    tmp_path: Path,
) -> None:
    """A default store that exists but is unreadable or unbound keeps existing gap behavior."""
    # 1. Unreadable default store (kanban.db exists, but no board.json metadata)
    hermes_unreadable = tmp_path / "hermes_unreadable"
    hermes_unreadable.mkdir()
    (hermes_unreadable / "kanban.db").touch()
    paths = _resolve_board_paths(board_paths=None, hermes_home=hermes_unreadable)
    assert ("default", hermes_unreadable / "kanban.db") in paths
    _, gaps = _read_board_bindings([], board_paths=None, hermes_home=hermes_unreadable)
    assert "BOARD_METADATA_UNREADABLE" in gaps

    # 2. Unbound default store (kanban.db and board.json exist, but unbound/missing project id)
    hermes_unbound = tmp_path / "hermes_unbound"
    (hermes_unbound / "kanban" / "boards" / "default").mkdir(parents=True)
    (hermes_unbound / "kanban.db").touch()
    (hermes_unbound / "kanban" / "boards" / "default" / "board.json").write_text(
        json.dumps({"slug": "default", "name": "Default"}),
        encoding="utf-8",
    )
    _, unbound_gaps = _read_board_bindings([], board_paths=None, hermes_home=hermes_unbound)
    assert "BOARD_PROJECT_UNBOUND" in unbound_gaps


def test_iso_dates_in_task_result_do_not_produce_task_result_unsafe() -> None:
    """ISO dates (YYYY-MM-DD) in task results must not be rejected as phone numbers."""
    from aether_agents.monitor.sources import _safe_text

    text = "Phase two rollout will finish by 2099-12-31 according to the latest draft."
    assert _safe_text(text, limit=1200) is not None


def test_profile_shaped_hermes_home_resolves_kanban_boards_and_is_not_idle(
    tmp_path: Path,
) -> None:
    """A profile-shaped HERMES_HOME (<root>/profiles/morfeo) resolves boards under <root>/kanban/boards."""
    project = tmp_path / "project"
    project.mkdir()
    _write_project(project)
    _write_contract(project)

    state_root = tmp_path / "aether-state"
    registry = ProjectRegistry(state_root)
    assert registry.register(PROJECT_ID, project, "Registry Project", NATIVE_PROJECT)

    hermes_root = tmp_path / "hermes"
    profile_home = hermes_root / "profiles" / "morfeo"
    profile_home.mkdir(parents=True)

    for pdb_path in (profile_home / "projects.db", hermes_root / "projects.db"):
        _sqlite(pdb_path, _PROJECT_SCHEMA)
        with sqlite3.connect(pdb_path) as conn:
            conn.execute(
                "INSERT INTO projects VALUES (?, ?, ?, ?, 0)",
                (NATIVE_PROJECT, "fixture", "Native Project", str(project)),
            )
            conn.commit()

    for sdb_path in (profile_home / "state.db",):
        _sqlite(sdb_path, _SESSION_SCHEMA)
        with sqlite3.connect(sdb_path) as conn:
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ORIGIN,
                    "tui",
                    "Origin session",
                    "Origin session",
                    str(project),
                    str(project),
                    1788955200.0,
                    None,
                    1788958800.0,
                ),
            )
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    FINALIZER,
                    "tui",
                    "Finalizer session",
                    "Finalizer session",
                    str(project),
                    str(project),
                    1788955200.0,
                    1788955500.0,
                    1788955500.0,
                ),
            )
            conn.commit()

    board_dir = hermes_root / "kanban" / "boards" / BOARD_SLUG
    board_dir.mkdir(parents=True)
    (board_dir / "board.json").write_text(
        json.dumps(
            {
                "slug": BOARD_SLUG,
                "name": "Collision Board",
                "project_id": NATIVE_PROJECT,
                "default_workdir": str(project.resolve()),
                "aether_project_id": PROJECT_ID,
                "aether_contract_id": CONTRACT_ID,
                "aether_contract_version": 1,
            }
        ),
        encoding="utf-8",
    )
    board_db = board_dir / "kanban.db"
    _sqlite(board_db, _BOARD_SCHEMA)
    with sqlite3.connect(board_db) as conn:
        conn.execute(
            "INSERT INTO tasks ("
            "id, title, status, project_id, session_id, created_at, started_at, completed_at, "
            "workspace_path, current_run_id, session_affinity, last_heartbeat_at, max_runtime_seconds"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "t_11111111",
                "Root completed",
                "done",
                NATIVE_PROJECT,
                ORIGIN,
                1788955200,
                1788955200,
                1788957000,
                str(project),
                1,
                '{"flow_id":"flow-1"}',
                1788957000,
                120,
            ),
        )
        conn.execute(
            "INSERT INTO task_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                "t_11111111",
                "done",
                "completed",
                1788955200,
                1788957000,
                1788957000,
                "root verified",
                None,
                "implementer",
            ),
        )
        conn.commit()

    # 1. Profile-shaped home (<root>/profiles/morfeo) resolves boards and collection is not idle
    resolved_paths_profile = _resolve_board_paths(board_paths=None, hermes_home=profile_home)
    assert any(slug == BOARD_SLUG for slug, _ in resolved_paths_profile)

    sources_profile = ReadOnlySources(state_root=state_root, hermes_home=profile_home)
    collection_profile = sources_profile.collect(cutoff_utc="2026-09-09T15:00:00Z")
    assert len(collection_profile.items) > 0
    assert collection_profile.idle is False

    # 2. Plain-root control (<root>) preserving non-profile resolution
    resolved_paths_plain = _resolve_board_paths(board_paths=None, hermes_home=hermes_root)
    assert any(slug == BOARD_SLUG for slug, _ in resolved_paths_plain)

    sources_plain = ReadOnlySources(state_root=state_root, hermes_home=hermes_root)
    collection_plain = sources_plain.collect(cutoff_utc="2026-09-09T15:00:00Z")
    assert len(collection_plain.items) > 0
    assert collection_plain.idle is False


# ---------------------------------------------------------------------------
# D18 — active contract resolution from the execution-board ``worktree_base_ref``
# ---------------------------------------------------------------------------

_CONTRACT_RELATIVE = Path(".aether") / "objective-contracts" / CONTRACT_ID / "v1.md"
_VALID_SHA = "0123456789abcdef0123456789abcdef01234567"
_WRITE_GIT_SUBCOMMANDS = frozenset(
    {
        "add",
        "checkout",
        "commit",
        "fetch",
        "gc",
        "prune",
        "repack",
        "reset",
        "restore",
        "rm",
        "stash",
        "switch",
        "update-ref",
        "worktree",
    }
)


def _git(project: Path, *arguments: str) -> str:
    """Run one Git command against a disposable test repository."""
    completed = subprocess.run(
        ("git", "-C", str(project), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_init(project: Path) -> None:
    subprocess.run(
        ("git", "init", "-q", "-b", "main"), cwd=project, check=True, capture_output=True
    )
    subprocess.run(
        ("git", "config", "user.email", "test@example.invalid"),
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "Test"), cwd=project, check=True, capture_output=True
    )


def _git_commit_all(project: Path, message: str) -> str:
    subprocess.run(("git", "add", "-A"), cwd=project, check=True, capture_output=True)
    subprocess.run(("git", "commit", "-qm", message), cwd=project, check=True, capture_output=True)
    return _git(project, "rev-parse", "HEAD")


def _git_commit_removal(project: Path, relative_path: str, message: str) -> str:
    subprocess.run(
        ("git", "rm", "-q", "-r", relative_path), cwd=project, check=True, capture_output=True
    )
    subprocess.run(("git", "commit", "-qm", message), cwd=project, check=True, capture_output=True)
    return _git(project, "rev-parse", "HEAD")


def _set_board_metadata(board_dir: Path, **updates: Any) -> None:
    path = board_dir / "board.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata.update(updates)
    path.write_text(json.dumps(metadata), encoding="utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref_project_bindings(fixture: dict[str, Any]) -> tuple[Any, ...]:
    projects, gaps = enumerate_project_bindings(
        fixture["registry"],
        native_projects_path=fixture["projects_db"],
        hermes_home=fixture["hermes"],
    )
    assert gaps == ()
    return projects


def _read_ref_board(fixture: dict[str, Any]) -> tuple[tuple[Any, ...], tuple[str, ...]]:
    return _read_board_bindings(
        _ref_project_bindings(fixture),
        board_paths=[(BOARD_SLUG, fixture["board_db"])],
        hermes_home=fixture["hermes"],
    )


def _base_ref_fixture(
    tmp_path: Path,
    *,
    contract_at_ref: bool = True,
    contract_mutations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the fixture set with the finalized contract committed only at a base ref.

    The project is a real Git repository.  The commit recorded as ``base_ref`` carries
    the marker and, unless ``contract_at_ref`` is false, the contract blob.  The
    registered primary checkout never holds an acceptable contract: when the base-ref
    contract is deliberately mutated, the canonical bytes remain only as a mutable
    worktree copy, so any fallback to the primary artifact would be observable.
    """
    fixture = _fixture(tmp_path)
    project = fixture["project"]
    _git_init(project)
    if not contract_at_ref:
        shutil.rmtree(project / ".aether" / "objective-contracts")
    elif contract_mutations is not None:
        _write_contract(project, metadata_overrides=contract_mutations)
    base_ref = _git_commit_all(project, "test: finalized contract at the execution-board base ref")
    if contract_at_ref and contract_mutations is None:
        _git_commit_removal(
            project,
            ".aether/objective-contracts",
            "test: primary checkout without the finalized contract",
        )
    else:
        _write_contract(project)
    fixture["base_ref"] = base_ref
    _set_board_metadata(fixture["board_dir"], worktree_base_ref=base_ref)
    return fixture


def test_board_contract_resolves_from_validated_base_ref_without_primary_artifact(
    tmp_path: Path,
) -> None:
    """A contract committed only at the board base ref binds and produces a work item."""
    fixture = _base_ref_fixture(tmp_path)
    assert not (fixture["project"] / _CONTRACT_RELATIVE).exists()

    bindings, gaps = _read_ref_board(fixture)
    assert gaps == ()
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.slug == BOARD_SLUG
    assert binding.project.project_id == PROJECT_ID
    assert binding.contract_id == CONTRACT_ID
    assert binding.contract_version == "v1"
    assert binding.contract_title == "Bound fixture objective"
    assert binding.created_in_session == ORIGIN
    assert binding.finalized_in_session == FINALIZER

    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")
    assert "BOARD_BASE_REF_UNREADABLE" not in source.coverage_gaps
    assert "FINAL_CONTRACT_UNREADABLE" not in source.coverage_gaps
    assert len(source.items) == 1
    item = source.items[0]
    assert item.project_id == PROJECT_ID
    assert item.origin_session_id == ORIGIN
    assert item.contract == {
        "id": CONTRACT_ID,
        "version": "v1",
        "title": "Bound fixture objective",
    }
    assert item.observed_state == "review"


def test_base_ref_contract_bytes_are_authoritative_over_a_valid_primary_copy(
    tmp_path: Path,
) -> None:
    """Differing-but-valid bytes resolve from the base ref, never from the mutable copy."""
    fixture = _base_ref_fixture(tmp_path, contract_mutations={"title": "Base ref objective"})
    primary_text = (fixture["project"] / _CONTRACT_RELATIVE).read_text(encoding="utf-8")
    assert '"Bound fixture objective"' in primary_text

    bindings, gaps = _read_ref_board(fixture)
    assert gaps == ()
    assert len(bindings) == 1
    assert bindings[0].contract_title == "Base ref objective"


@pytest.mark.parametrize(
    "invalid_ref",
    [_VALID_SHA.upper(), _VALID_SHA[:39], _VALID_SHA[:8]],
    ids=["uppercase", "truncated", "abbreviated"],
)
def test_present_but_invalid_base_ref_format_fails_closed_without_primary_fallback(
    tmp_path: Path, invalid_ref: str
) -> None:
    """A present-but-invalid ref is a labeled gap even though the mutable copy is valid."""
    fixture = _base_ref_fixture(tmp_path, contract_at_ref=False)
    assert (fixture["project"] / _CONTRACT_RELATIVE).is_file()
    _set_board_metadata(fixture["board_dir"], worktree_base_ref=invalid_ref)

    bindings, gaps = _read_ref_board(fixture)
    assert bindings == ()
    assert gaps == ("BOARD_BASE_REF_UNREADABLE",)


def test_base_ref_to_unknown_commit_is_a_labeled_gap_for_that_board(tmp_path: Path) -> None:
    """An unreachable base ref object never falls back to another commit or the checkout."""
    fixture = _base_ref_fixture(tmp_path)
    _set_board_metadata(fixture["board_dir"], worktree_base_ref="0" * 40)

    bindings, gaps = _read_ref_board(fixture)
    assert bindings == ()
    assert gaps == ("BOARD_BASE_REF_UNREADABLE",)


def test_base_ref_without_contract_blob_does_not_use_mutable_worktree_artifact(
    tmp_path: Path,
) -> None:
    """Mutable-worktree-only contract bytes cannot substitute for the base-ref object."""
    fixture = _base_ref_fixture(tmp_path, contract_at_ref=False)
    assert (fixture["project"] / _CONTRACT_RELATIVE).is_file()

    bindings, gaps = _read_ref_board(fixture)
    assert bindings == ()
    assert gaps == ("BOARD_BASE_REF_UNREADABLE",)


def test_base_ref_marker_project_mismatch_is_a_labeled_gap(tmp_path: Path) -> None:
    """A marker at the base ref whose UUID disagrees with board metadata is rejected."""
    fixture = _fixture(tmp_path)
    project = fixture["project"]
    _git_init(project)
    _write_project(project, project_id=PROJECT_B)
    base_ref = _git_commit_all(
        project, "test: foreign project marker at the execution-board base ref"
    )
    _write_project(project)
    _set_board_metadata(fixture["board_dir"], worktree_base_ref=base_ref)

    bindings, gaps = _read_ref_board(fixture)
    assert bindings == ()
    assert gaps == ("BOARD_BASE_REF_UNREADABLE",)


@pytest.mark.parametrize(
    "mutations",
    [
        {"status": "draft"},
        {"artifact_type": "aether.objective-contract.v2"},
        {"contract_id": CONTRACT_B},
        {"version": 2},
        {"project_id": PROJECT_B},
        {"created_in_session": ""},
        {"finalized_in_session": ""},
        {"title": ""},
    ],
    ids=[
        "status",
        "artifact-type",
        "contract-id",
        "version",
        "project-id",
        "created-session",
        "finalized-session",
        "title",
    ],
)
def test_base_ref_contract_identity_mismatch_is_a_labeled_gap(
    tmp_path: Path, mutations: dict[str, Any]
) -> None:
    """A base-ref contract whose identity disagrees with board metadata is a gap."""
    fixture = _base_ref_fixture(tmp_path, contract_mutations=mutations)
    assert (fixture["project"] / _CONTRACT_RELATIVE).is_file()

    bindings, gaps = _read_ref_board(fixture)
    assert bindings == ()
    assert gaps == ("BOARD_BASE_REF_UNREADABLE",)


def test_invalid_board_base_ref_does_not_erase_a_valid_base_ref_binding(
    tmp_path: Path,
) -> None:
    """Unrelated invalid boards keep their own gap without suppressing valid bindings."""
    fixture = _base_ref_fixture(tmp_path)
    stale_board_db = _write_bound_board(
        fixture,
        project=fixture["project"],
        project_id=PROJECT_ID,
        native_project_id=NATIVE_PROJECT,
        contract_id=CONTRACT_C,
        board_slug=BOARD_SLUG_C,
        origin=ORIGIN_C,
        finalized=FINALIZER_C,
        task_id="t_33333333",
        title="Stale board work",
    )
    _set_board_metadata(stale_board_db.parent, worktree_base_ref="not-a-sha")
    sources = ReadOnlySources(
        registry=fixture["registry"],
        native_projects_path=fixture["projects_db"],
        board_paths=[(BOARD_SLUG, fixture["board_db"]), (BOARD_SLUG_C, stale_board_db)],
        session_db_paths=[fixture["session_db"]],
        hermes_home=fixture["hermes"],
    )

    source = sources.collect(cutoff_utc="2026-09-09T14:00:00Z")

    assert "BOARD_BASE_REF_UNREADABLE" in source.coverage_gaps
    assert len(source.items) == 1
    item = source.items[0]
    assert item.project_id == PROJECT_ID
    assert item.origin_session_id == ORIGIN
    assert item.contract is not None and item.contract["id"] == CONTRACT_ID


def test_base_ref_collection_reads_objects_without_touching_repository_or_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Collection reads Git objects only, leaving the repository and sources unchanged."""
    fixture = _base_ref_fixture(tmp_path)
    project = fixture["project"]
    sqlite_paths = (fixture["board_db"], fixture["session_db"], fixture["projects_db"])
    before_status = _git(project, "status", "--porcelain=v1", "--untracked-files=all")
    before_refs = _git(project, "for-each-ref", "--format=%(refname) %(objectname)")
    before_digests = {path: _digest(path) for path in sqlite_paths}

    recorded: list[list[str]] = []
    real_run = subprocess.run

    def _recording_run(command: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(command, (list, tuple)) and command and command[0] == "git":
            recorded.append([str(part) for part in command])
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(sources_module.subprocess, "run", _recording_run)
    source = _sources(fixture).collect(cutoff_utc="2026-09-09T14:00:00Z")
    monkeypatch.undo()

    assert len(source.items) == 1
    assert recorded, "the base-ref contract must be read through a Git object read"
    for command in recorded:
        assert command[0] == "git"
        assert "show" in command
        assert not _WRITE_GIT_SUBCOMMANDS.intersection(command)
        assert fixture["base_ref"] in command[-1]
    assert _git(project, "status", "--porcelain=v1", "--untracked-files=all") == before_status
    assert _git(project, "for-each-ref", "--format=%(refname) %(objectname)") == before_refs
    assert {path: _digest(path) for path in sqlite_paths} == before_digests
    assert not (project / _CONTRACT_RELATIVE).exists()
