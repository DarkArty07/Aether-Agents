"""SR-397 — write-capable probes cannot reach a foreign or live board.

The laboratory's disposable constructor exists (RR-267); this module pins the residual
SR-397 behavior: any write-capable helper constructs one disposable context and the
child-side gate resolves the effective home, board root, database, projects database and
workspaces before the first writer, refusing a mismatch with zero rows written.

The live board is never used.  The vulnerable pattern is reproduced against a disposable
*copy* standing in for the foreign target an inherited selector would reach.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Mapping

import pytest

from aether_agents import lab
from aether_agents.lab import dispatch, matrix, observation, persistent, runner

#: Modules whose helpers may invoke a native Kanban/board writer.
WRITE_CAPABLE_MODULES = (persistent, runner, observation, dispatch, matrix)


def _seed_board(path: Path, *, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS tasks "
            "(id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS task_events (id INTEGER PRIMARY KEY, kind TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO tasks VALUES ('t_canary', ?, 'done')", (title,))
        connection.execute("INSERT INTO task_events (kind) VALUES ('canary')")


def _snapshot(path: Path) -> dict[str, object]:
    """Byte digest plus per-table row counts and content digests."""

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


def _fake_hermes(path: Path, *, payload: str = "[]", marker: Path | None = None) -> Path:
    script = f"#!/bin/sh\nprintf '{payload}'\n"
    if marker is not None:
        script += f"touch {shlex.quote(str(marker))}\n"
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_disposable_boards(run_root: Path, hermes_root: Path, hermes: Path) -> dict[str, str]:
    return lab.isolated_hermes_env(run_root, hermes_root, hermes)


#: A child that resolves its board the way a native writer does: an explicit
#: HERMES_KANBAN_DB outranks HERMES_HOME.  It is the write surface the helpers gate.
_WRITER_CHILD = r"""
import json
import os
import sqlite3
import sys
from pathlib import Path

target = os.environ.get("HERMES_KANBAN_DB", "").strip()
if not target:
    target = str(Path(os.environ["HERMES_HOME"]) / "kanban.db")
with sqlite3.connect(target) as connection:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS tasks "
        "(id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT OR REPLACE INTO tasks VALUES ('t_writer', ?, 'done')", (sys.argv[1],)
    )
    connection.commit()
print(json.dumps({"target": str(Path(target).resolve())}))
"""


#: A native-session stand-in run through the real `run_persistent_session` launcher.
_SESSION_CHILD = r"""
import json
import os
import sqlite3
import sys
from pathlib import Path

marker = Path(sys.argv[1])
target = Path(os.environ["HERMES_KANBAN_DB"]).resolve()
marker.write_text(
    json.dumps(
        {
            "target": str(target),
            "home": str(Path(os.environ["HERMES_HOME"]).resolve()),
        }
    ),
    encoding="utf-8",
)
with sqlite3.connect(target) as connection:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS tasks "
        "(id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)"
    )
    connection.execute("INSERT OR REPLACE INTO tasks VALUES ('t_session', 'probe', 'done')")
    connection.commit()
"""


#: Child-side gate: refuse before the first writer, then write only when verified.
_GATED_WRITER_CHILD = r"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, sys.argv[1])
from aether_agents.lab import isolation

try:
    isolation.verify_child_writer_context([sys.argv[2], sys.argv[3]])
except isolation.HarnessError as error:
    print(json.dumps({"refused": str(error)}))
    raise SystemExit(3)
target = os.environ["HERMES_KANBAN_DB"]
with sqlite3.connect(target) as connection:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS tasks "
        "(id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)"
    )
    connection.execute("INSERT OR REPLACE INTO tasks VALUES ('t_gated', 'gated', 'done')")
    connection.commit()
print(json.dumps({"wrote": str(target)}))
"""


def test_inherited_raw_selector_mutates_the_foreign_copy_not_the_live_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED reproduction: the pre-fix environment reaches a foreign board copy.

    The live board is represented by a disposable original; the copy is the exact
    foreign target an inherited ``HERMES_KANBAN_DB`` would reach.  The vulnerable
    environment is the historical ``os.environ.copy()`` fallback: only ``HERMES_HOME``
    is re-pointed, the raw selector survives.
    """

    live_board = tmp_path / "live" / "kanban.db"
    _seed_board(live_board, title="live canary")
    live_before = _snapshot(live_board)
    foreign_copy = tmp_path / "foreign" / "kanban.db"
    foreign_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live_board, foreign_copy)

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hostile-home"))
    monkeypatch.setenv("HERMES_KANBAN_DB", str(foreign_copy))
    vulnerable_child_env = dict(os.environ.copy())

    completed = subprocess.run(
        [sys.executable, "-c", _WRITER_CHILD, "inherited selector"],
        env=vulnerable_child_env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["target"] == str(foreign_copy.resolve())
    assert "t_writer" in {
        str(row[0]) for row in sqlite3.connect(foreign_copy).execute("SELECT id FROM tasks")
    }
    # The live-board snapshot is byte-identical with unchanged table counts/digests:
    # the reproduction happened on the disposable copy only.
    assert _snapshot(live_board) == live_before


def test_persistent_session_refuses_without_a_declared_disposable_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No write-capable helper falls back to the ambient process environment."""

    foreign_copy = tmp_path / "foreign" / "kanban.db"
    _seed_board(foreign_copy, title="foreign canary")
    foreign_before = _snapshot(foreign_copy)
    marker = tmp_path / "SESSION_INVOKED"
    script = tmp_path / "session.py"
    script.write_text(_SESSION_CHILD, encoding="utf-8")

    monkeypatch.setenv("HERMES_KANBAN_DB", str(foreign_copy))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hostile-home"))
    ambient_before = dict(os.environ)

    with pytest.raises(lab.HarnessError, match="disposable"):
        persistent.run_persistent_session(
            [sys.executable, str(script), str(marker)],
            owner_message="one owner message",
            timeout_seconds=1,
            poll_seconds=0.02,
        )

    assert not marker.exists(), "the child must not be launched without a verified context"
    assert _snapshot(foreign_copy) == foreign_before
    assert dict(os.environ) == ambient_before
    assert "os.environ.copy()" not in inspect.getsource(persistent)


def test_persistent_session_constructs_the_disposable_context_and_writes_only_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GREEN: the safe single-board variant writes to the disposable target only."""

    live_board = tmp_path / "live" / "kanban.db"
    _seed_board(live_board, title="live canary")
    live_before = _snapshot(live_board)
    foreign_copy = tmp_path / "foreign" / "kanban.db"
    foreign_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live_board, foreign_copy)
    foreign_before = _snapshot(foreign_copy)

    marker = tmp_path / "SESSION_INVOKED"
    script = tmp_path / "session.py"
    script.write_text(_SESSION_CHILD, encoding="utf-8")
    run_root = tmp_path / "run"
    run_root.mkdir()

    monkeypatch.setenv("HERMES_KANBAN_DB", str(foreign_copy))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hostile-home"))
    parent_env_before = dict(os.environ)

    persistent.run_persistent_session(
        [sys.executable, str(script), str(marker)],
        owner_message="one owner message",
        timeout_seconds=0.5,
        poll_seconds=0.02,
        run_root=run_root,
    )

    assert marker.is_file(), "the disposable session child ran"
    receipt = json.loads(marker.read_text(encoding="utf-8"))
    disposable_board = run_root / "kanban.db"
    assert receipt["target"] == str(disposable_board.resolve())
    assert receipt["home"] == str((run_root / "hermes-home").resolve())
    assert "t_session" in {
        str(row[0]) for row in sqlite3.connect(disposable_board).execute("SELECT id FROM tasks")
    }
    assert _snapshot(foreign_copy) == foreign_before
    assert _snapshot(live_board) == live_before
    assert dict(os.environ) == parent_env_before


def test_pre_write_gate_refuses_a_mismatch_with_zero_rows_written(tmp_path: Path) -> None:
    """The effective-root gate refuses before any writer, deterministically."""

    from aether_agents.lab import isolation

    run_root = tmp_path / "run"
    run_root.mkdir()
    hermes_root = tmp_path / "hermes-home"
    hermes = _fake_hermes(tmp_path / "hermes")
    env = _write_disposable_boards(run_root, hermes_root, hermes)
    assert env["HERMES_KANBAN_DB"] == str(run_root / "kanban.db")

    foreign_copy = tmp_path / "foreign" / "kanban.db"
    _seed_board(foreign_copy, title="foreign canary")
    foreign_before = _snapshot(foreign_copy)
    tampered = dict(env, HERMES_KANBAN_DB=str(foreign_copy))

    problems = isolation.writer_root_problems(
        isolation.resolve_writer_roots(tampered, native=False),
        private_roots=[run_root, hermes_root],
    )
    assert problems == ["kanban_db-escape"]
    with pytest.raises(lab.HarnessError, match="kanban_db-escape"):
        isolation.verify_writer_context(
            isolation.resolve_writer_roots(tampered, native=False),
            private_roots=[run_root, hermes_root],
        )
    # The composite gate the helpers call refuses too, and the helper does not launch.
    with pytest.raises(lab.HarnessError):
        isolation.require_verified_writer_context(
            run_root=run_root, hermes_root=hermes_root, environ=tampered
        )
    marker = tmp_path / "SESSION_INVOKED"
    script = tmp_path / "session.py"
    script.write_text(_SESSION_CHILD, encoding="utf-8")
    with pytest.raises(lab.HarnessError):
        persistent.run_persistent_session(
            [sys.executable, str(script), str(marker)],
            owner_message="one owner message",
            env=tampered,
            run_root=run_root,
            hermes_root=hermes_root,
            timeout_seconds=1,
            poll_seconds=0.02,
        )
    assert not marker.exists()
    assert _snapshot(foreign_copy) == foreign_before


def test_fallback_refuses_a_hermes_home_below_the_platform_native_home(tmp_path: Path) -> None:
    """The env-derived form models ``get_default_hermes_root()``'s native-home branch.

    A ``HERMES_HOME`` that resolves under the platform-native home is never the kanban
    root the loaded revision uses — that home is — so a non-profile subdirectory of the
    real Hermes home cannot be waved through as disposable.  Round-1 review reproduction:
    the pre-fix fallback returned no problems and a PASS receipt while the native
    resolvers escaped to the live root.
    """

    from aether_agents.lab import isolation

    synth_home = tmp_path / "synth"
    lab_home = synth_home / ".hermes" / "labs" / "x"
    lab_home.mkdir(parents=True)
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("HERMES_", "AETHER_", "XDG_"))
    }
    env["HOME"] = str(synth_home)
    env["HERMES_HOME"] = str(lab_home)

    roots = isolation.resolve_writer_roots(env, native=False)
    assert Path(str(roots["hermes_home"])).resolve() == lab_home.resolve()
    assert Path(str(roots["kanban_home"])).resolve() == (synth_home / ".hermes").resolve()
    problems = isolation.writer_root_problems(roots, private_roots=[lab_home])
    assert problems == [
        "boards_root-escape",
        "kanban_db-escape",
        "kanban_home-escape",
        "workspaces_root-escape",
    ]
    with pytest.raises(lab.HarnessError, match="kanban_home-escape"):
        isolation.verify_writer_context(roots, private_roots=[lab_home])
    with pytest.raises(lab.HarnessError):
        isolation.require_verified_writer_context(
            run_root=lab_home, hermes_root=lab_home, environ=env
        )

    if importlib.util.find_spec("hermes_cli") is None:
        return
    # The native child probe (the confirmation the fallback models) resolves the same
    # roots, so the derived refusal matches native behavior instead of being stricter.
    complete, probed = isolation.probe_child_writer_roots(Path(sys.executable), env, cwd=tmp_path)
    assert complete is True
    assert {name: Path(str(value)).resolve() for name, value in probed.items()} == {
        name: Path(str(value)).resolve() for name, value in roots.items()
    }
    assert isolation.writer_root_problems(probed, private_roots=[lab_home]) == problems


def test_fallback_models_the_branch_order_of_the_loaded_revision(tmp_path: Path) -> None:
    """Profile, unset-home, unfaithful-home and override branches of the derived root."""

    from aether_agents.lab import isolation

    base = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("HERMES_", "AETHER_", "XDG_"))
    }
    synth = tmp_path / "synth"
    profile_home = synth / "deploy" / "profiles" / "coder"
    profile_home.mkdir(parents=True)

    # A <root>/profiles/<name> home outside the native home anchors on <root>.
    env = dict(base, HOME=str(synth), HERMES_HOME=str(profile_home))
    roots = isolation.resolve_writer_roots(env, native=False)
    assert Path(str(roots["kanban_home"])).resolve() == (synth / "deploy").resolve()
    assert (
        Path(str(roots["boards_root"])).resolve()
        == (synth / "deploy" / "kanban" / "boards").resolve()
    )

    # An unset HERMES_HOME anchors on the platform-native home.
    env = dict(base, HOME=str(synth))
    env.pop("HERMES_HOME", None)
    roots = isolation.resolve_writer_roots(env, native=False)
    assert Path(str(roots["hermes_home"])).resolve() == (synth / ".hermes").resolve()
    assert Path(str(roots["kanban_home"])).resolve() == (synth / ".hermes").resolve()

    # A mapping without HOME cannot show the native home: the anchored roots refuse.
    env = dict(base, HERMES_HOME=str(tmp_path / "custom"))
    env.pop("HOME", None)
    problems = isolation.writer_root_problems(
        isolation.resolve_writer_roots(env, native=False), private_roots=[tmp_path]
    )
    assert problems == [
        "boards_root-unresolved",
        "kanban_db-unresolved",
        "kanban_home-unresolved",
        "workspaces_root-unresolved",
    ]

    # HERMES_KANBAN_HOME anchors every kanban root even without a faithful native home.
    env = dict(
        base,
        HERMES_HOME=str(tmp_path / "custom"),
        HERMES_KANBAN_HOME=str(tmp_path / "run"),
    )
    env.pop("HOME", None)
    roots = isolation.resolve_writer_roots(env, native=False)
    assert Path(str(roots["kanban_home"])).resolve() == (tmp_path / "run").resolve()
    assert Path(str(roots["kanban_db"])).resolve() == (tmp_path / "run" / "kanban.db").resolve()


def test_child_probe_never_hands_python_source_to_a_non_python_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The child probe is only run under an interpreter that names itself Python.

    A shell shebang runner would be handed Python source, which can block (an ambient
    ``import`` command) instead of failing, so it is skipped and the faithful
    environment-derived form is used.  The probe must not even be spawned.
    """

    from aether_agents.lab import isolation

    shell_launcher = _fake_hermes(tmp_path / "hermes")
    assert isolation.native_python_for(shell_launcher) == Path("/bin/sh")

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("the probe source must not be handed to a non-Python runner")

    monkeypatch.setattr(isolation.subprocess, "run", _forbidden)
    assert isolation.probe_child_writer_roots(
        isolation.native_python_for(shell_launcher), dict(os.environ), cwd=tmp_path
    ) == (False, {})


def test_child_side_gate_refuses_before_writing_and_allows_the_disposable_target(
    tmp_path: Path,
) -> None:
    """The child-side gate resolves the roots and refuses with zero rows written."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    hermes_root = tmp_path / "hermes-home"
    hermes = _fake_hermes(tmp_path / "hermes")
    env = _write_disposable_boards(run_root, hermes_root, hermes)
    foreign_copy = tmp_path / "foreign" / "kanban.db"
    _seed_board(foreign_copy, title="foreign canary")
    foreign_before = _snapshot(foreign_copy)
    source_root = str(Path(lab.__file__).resolve().parents[1])

    tampered = dict(env, HERMES_KANBAN_DB=str(foreign_copy))
    refused = subprocess.run(
        [
            sys.executable,
            "-c",
            _GATED_WRITER_CHILD,
            source_root,
            str(run_root),
            str(hermes_root),
        ],
        env=tampered,
        text=True,
        capture_output=True,
        check=False,
    )
    assert refused.returncode == 3, refused.stdout + refused.stderr
    assert "kanban_db-escape" in json.loads(refused.stdout)["refused"]
    assert _snapshot(foreign_copy) == foreign_before

    safe = subprocess.run(
        [
            sys.executable,
            "-c",
            _GATED_WRITER_CHILD,
            source_root,
            str(run_root),
            str(hermes_root),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert safe.returncode == 0, safe.stdout + safe.stderr
    assert json.loads(safe.stdout)["wrote"] == str(run_root / "kanban.db")
    assert "t_gated" in {
        str(row[0])
        for row in sqlite3.connect(run_root / "kanban.db").execute("SELECT id FROM tasks")
    }
    assert _snapshot(foreign_copy) == foreign_before


def test_child_gate_resolves_every_effective_root_with_the_native_modules(
    tmp_path: Path,
) -> None:
    """Native child resolution covers home, board root, DB, projects DB and workspaces."""

    if importlib.util.find_spec("hermes_cli") is None:
        pytest.skip("native Hermes modules are unavailable to this interpreter")

    from aether_agents.lab import isolation

    run_root = tmp_path / "run"
    run_root.mkdir()
    hermes_root = tmp_path / "hermes-home"
    hermes = _fake_hermes(tmp_path / "hermes")
    env = _write_disposable_boards(run_root, hermes_root, hermes)
    child = r"""
import importlib.util
import json
import sys

sys.path.insert(0, sys.argv[1])
from aether_agents.lab import isolation

payload = {
    "native": importlib.util.find_spec("hermes_cli") is not None,
    "roots": {
        name: str(value)
        for name, value in isolation.resolve_writer_roots().items()
    },
}
payload["receipt"] = isolation.verify_child_writer_context([sys.argv[2], sys.argv[3]])
print(json.dumps(payload))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            str(Path(lab.__file__).resolve().parents[1]),
            str(run_root),
            str(hermes_root),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["native"] is True
    assert set(payload["roots"]) == set(isolation.WRITER_ROOT_NAMES)
    assert payload["receipt"]["verified_roots"] == ",".join(sorted(isolation.WRITER_ROOT_NAMES))
    assert payload["receipt"]["private_root_count"] == "2"
    private = [run_root.resolve(), hermes_root.resolve()]
    for name, value in payload["roots"].items():
        resolved = Path(value).resolve()
        assert any(resolved == root or root in resolved.parents for root in private), (
            f"{name} resolved outside the private roots: {resolved}"
        )
    roots = payload["roots"]
    assert Path(roots["kanban_db"]).resolve() == (run_root / "kanban.db").resolve()
    assert Path(roots["boards_root"]).resolve() == (hermes_root / "kanban" / "boards").resolve()
    assert Path(roots["projects_db"]).resolve() == (hermes_root / "projects.db").resolve()
    assert Path(roots["workspaces_root"]).resolve() == (run_root / "worktrees").resolve()

    tampered_env = dict(env, HERMES_KANBAN_DB=str(tmp_path / "outside" / "kanban.db"))
    refused = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            str(Path(lab.__file__).resolve().parents[1]),
            str(run_root),
            str(hermes_root),
        ],
        env=tampered_env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert refused.returncode != 0
    assert "kanban_db-escape" in refused.stderr


def test_canonical_multi_board_context_inside_the_lab_receives_the_intended_write(
    tmp_path: Path,
) -> None:
    """GREEN: the canonical multi-board variant keeps `board=` writes inside the lab."""

    if importlib.util.find_spec("hermes_cli") is None:
        pytest.skip("native Hermes modules are unavailable to this interpreter")

    run_root = tmp_path / "run"
    run_root.mkdir()
    hermes_root = run_root / "hermes-home"
    hermes = _fake_hermes(tmp_path / "hermes")
    env = _write_disposable_boards(run_root, hermes_root, hermes)
    env.pop("HERMES_KANBAN_DB", None)
    env["HERMES_KANBAN_HOME"] = str(run_root)
    assert "HERMES_KANBAN_DB" not in env
    (run_root / "work").mkdir()
    witness = tmp_path / "witness" / "kanban.db"
    _seed_board(witness, title="witness canary")
    witness_before = _snapshot(witness)
    child = r"""
import json
import os
import sys

sys.path.insert(0, sys.argv[1])
from aether_agents.lab import isolation
from hermes_cli import kanban_db

registry = isolation.verify_child_writer_context([sys.argv[2], sys.argv[3]])
kanban_db.create_board(
    "oc-multi-board-v1", name="laboratory board", default_workdir=sys.argv[4]
)
with kanban_db.connect(board="oc-multi-board-v1") as connection:
    task_id = kanban_db.create_task(
        connection,
        title="multi-board laboratory task",
        assignee="implementer",
        board="oc-multi-board-v1",
    )
print(json.dumps({"task": task_id, "receipt": registry}))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            str(Path(lab.__file__).resolve().parents[1]),
            str(run_root),
            str(hermes_root),
            str(run_root / "work"),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["task"]
    board_db = run_root / "kanban" / "boards" / "oc-multi-board-v1" / "kanban.db"
    assert board_db.is_file(), "the canonical board= write stayed inside the laboratory"
    assert run_root.resolve() in board_db.resolve().parents
    assert _snapshot(witness) == witness_before


def test_every_write_capable_helper_constructs_or_verifies_a_context() -> None:
    """No write-capable helper inherits the ambient environment without the gate."""

    from aether_agents.lab import isolation

    allowed = (
        "require_verified_writer_context(",
        "isolated_hermes_env(",
        "verify_child_writer_context(",
        "scrub_inherited_identity(",
    )
    for module in WRITE_CAPABLE_MODULES:
        source = inspect.getsource(module)
        assert "os.environ.copy()" not in source, module.__name__
        assert any(token in source for token in allowed), module.__name__

    assert isinstance(
        getattr(lab, "require_verified_writer_context"), type(isolation.verify_writer_context)
    )
    assert lab.isolated_hermes_env is isolation.isolated_hermes_env
    assert runner.isolated_hermes_env is isolation.isolated_hermes_env
    assert persistent.isolated_hermes_env is isolation.isolated_hermes_env


def test_dispatch_refuses_an_undeclared_context_before_any_dispatch(tmp_path: Path) -> None:
    """No caller reaches the native dispatch writer without declared disposable roots."""

    invoked = tmp_path / "DISPATCH_INVOKED"
    hermes = _fake_hermes(tmp_path / "hermes", marker=invoked)
    env: Mapping[str, str] = _write_disposable_boards(
        tmp_path / "run", tmp_path / "hermes-home", hermes
    )

    with pytest.raises(lab.HarnessError, match="disposable"):
        dispatch.dispatch_until_settled(
            hermes,
            cwd=tmp_path,
            env=env,
            commands_log=tmp_path / "commands.jsonl",
            evidence_dir=tmp_path / "evidence",
            max_passes=1,
            timeout_seconds=5,
        )

    assert not invoked.exists(), "the native dispatch writer ran without a declared context"


def test_dispatch_consumes_the_native_child_probe_before_dispatching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dispatch writer verifies through the provisioned interpreter, not only the fallback."""

    from aether_agents.lab import isolation

    run_root = tmp_path / "run"
    run_root.mkdir()
    hermes_root = run_root / "hermes-home"
    hermes = _fake_hermes(tmp_path / "hermes")
    env: Mapping[str, str] = _write_disposable_boards(run_root, hermes_root, hermes)
    foreign = {name: tmp_path / "outside" / name for name in isolation.WRITER_ROOT_NAMES}
    monkeypatch.setattr(
        isolation, "probe_child_writer_roots", lambda *args, **kwargs: (True, dict(foreign))
    )

    with pytest.raises(lab.HarnessError, match="escape"):
        dispatch.dispatch_until_settled(
            hermes,
            cwd=tmp_path,
            env=env,
            commands_log=tmp_path / "commands.jsonl",
            evidence_dir=tmp_path / "evidence",
            max_passes=1,
            timeout_seconds=5,
            run_root=run_root,
            hermes_root=hermes_root,
        )


def test_dispatch_writer_verifies_the_declared_disposable_roots(tmp_path: Path) -> None:
    """The dispatcher helper itself refuses an escaping context before dispatching."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    hermes_root = tmp_path / "hermes-home"
    hermes = _fake_hermes(tmp_path / "hermes")
    env: Mapping[str, str] = _write_disposable_boards(run_root, hermes_root, hermes)
    tampered = dict(env, HERMES_KANBAN_DB=str(tmp_path / "outside" / "kanban.db"))

    with pytest.raises(lab.HarnessError):
        dispatch.dispatch_until_settled(
            hermes,
            cwd=tmp_path,
            env=tampered,
            commands_log=tmp_path / "commands.jsonl",
            evidence_dir=tmp_path / "evidence",
            max_passes=1,
            timeout_seconds=5,
            run_root=run_root,
            hermes_root=hermes_root,
        )

    result = dispatch.dispatch_until_settled(
        hermes,
        cwd=tmp_path,
        env=env,
        commands_log=tmp_path / "commands.jsonl",
        evidence_dir=tmp_path / "evidence",
        max_passes=1,
        timeout_seconds=5,
        run_root=run_root,
        hermes_root=hermes_root,
    )
    assert result.reason == "no_tasks"
