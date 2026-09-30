"""Focused tests for EIH-B: gateway HERMES_BIN override and aether-kanban-worker launcher routing.

Covers plan sections 3.4 and 3.5, shared decisions 3, 5, 6, 12, and quickstart section 1:
- Plugin override sets HERMES_BIN only for a valid release launcher resolved outside
  runtime/current, leaves environment unchanged otherwise, and is idempotent.
- Launcher routing: with a stub hermes that records argv/environment, each section 3.5
  condition independently forces an exact pass-through; decision exceptions pass through;
  and a fully eligible attempt reaches the Claude adapter seam.
- Preserves unchanged argv tail and environment; never re-reads HERMES_BIN.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import aether_agents.kanban_worker_launcher as launcher
import aether_agents.objective_contracts.hermes_plugin as hermes_plugin
from aether_agents.lifecycle import HERMES_BASELINE


def _resolve_hermes_checkout() -> Path | None:
    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
    if configured:
        p = Path(configured).expanduser()
        if p.is_dir():
            return p
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cached = cache_home / "aether-agents" / "hermes" / HERMES_BASELINE.tag
    if cached.is_dir():
        return cached
    return None


HERMES_CHECKOUT = _resolve_hermes_checkout()
if HERMES_CHECKOUT and str(HERMES_CHECKOUT) not in sys.path:
    sys.path.insert(0, str(HERMES_CHECKOUT))


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure tests run with isolated environment and disposable roots."""
    # Scrub existing Kanban/Hermes environment
    for key in (
        "HERMES_BIN",
        "HERMES_HOME",
        "HERMES_KANBAN_HOME",
        "HERMES_KANBAN_DB",
        "HERMES_KANBAN_BOARD",
        "HERMES_KANBAN_TASK",
        "HERMES_KANBAN_RUN_ID",
        "HERMES_KANBAN_CLAIM_LOCK",
        "HERMES_KANBAN_WORKSPACE",
        "HERMES_PROFILE",
        "HERMES_KANBAN_GOAL_MODE",
        "HERMES_KANBAN_REVIEW_AFFINITY",
    ):
        monkeypatch.delenv(key, raising=False)


def _make_executable(path: Path, content: str = "#!/bin/sh\nexit 0\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)


# ---------------------------------------------------------------------------
# Part A: Plugin HERMES_BIN override tests (plan section 3.4)
# ---------------------------------------------------------------------------


class DummyContext:
    def __init__(self, profile_name: str = "morfeo", author_profile: str = "morfeo") -> None:
        self.profile_name = profile_name
        self._author_profile = author_profile
        self.registered_tools: list[dict[str, Any]] = []

    def get_config(self, key: str, default: Any = None) -> Any:
        if key == "author_profile":
            return self._author_profile
        return default

    def register_tool(self, **kwargs: Any) -> None:
        self.registered_tools.append(kwargs)


def test_plugin_override_sets_hermes_bin_for_valid_release_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid release launcher outside runtime/current sets os.environ['HERMES_BIN']."""
    release_scripts = tmp_path / "releases" / "1.0.0" / "runtime" / "bin"
    launcher_file = release_scripts / "aether-kanban-worker"
    _make_executable(launcher_file)

    monkeypatch.setattr(
        hermes_plugin,
        "_resolve_running_release_launcher",
        lambda scripts_dir=None: launcher_file.resolve(),
    )

    ctx = DummyContext()
    hermes_plugin.register(ctx)

    assert os.environ.get("HERMES_BIN") == str(launcher_file.resolve())


def test_plugin_override_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated registration sets identical HERMES_BIN and is idempotent."""
    launcher_file = tmp_path / "releases" / "1.0.0" / "runtime" / "bin" / "aether-kanban-worker"
    _make_executable(launcher_file)

    monkeypatch.setattr(
        hermes_plugin,
        "_resolve_running_release_launcher",
        lambda scripts_dir=None: launcher_file.resolve(),
    )

    ctx = DummyContext()
    hermes_plugin.register(ctx)
    first_bin = os.environ.get("HERMES_BIN")
    hermes_plugin.register(ctx)
    second_bin = os.environ.get("HERMES_BIN")

    assert first_bin == second_bin == str(launcher_file.resolve())


def test_plugin_override_leaves_env_unchanged_when_launcher_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing launcher leaves HERMES_BIN unchanged."""
    empty_scripts = tmp_path / "releases" / "1.0.0" / "bin"
    empty_scripts.mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(empty_scripts / "python"))

    hermes_plugin._configure_hermes_bin_override(scripts_dir=empty_scripts)
    assert "HERMES_BIN" not in os.environ


def test_plugin_override_leaves_env_unchanged_when_launcher_not_executable(
    tmp_path: Path,
) -> None:
    """Non-executable launcher leaves HERMES_BIN unchanged."""
    scripts_dir = tmp_path / "releases" / "1.0.0" / "bin"
    scripts_dir.mkdir(parents=True)
    launcher_file = scripts_dir / "aether-kanban-worker"
    launcher_file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    # Remove execute permissions
    launcher_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

    hermes_plugin._configure_hermes_bin_override(scripts_dir=scripts_dir)
    assert "HERMES_BIN" not in os.environ


def test_plugin_override_leaves_env_unchanged_when_launcher_is_directory(
    tmp_path: Path,
) -> None:
    """A directory named aether-kanban-worker is not a regular file and is ignored."""
    scripts_dir = tmp_path / "releases" / "1.0.0" / "bin"
    launcher_dir = scripts_dir / "aether-kanban-worker"
    launcher_dir.mkdir(parents=True)

    hermes_plugin._configure_hermes_bin_override(scripts_dir=scripts_dir)
    assert "HERMES_BIN" not in os.environ


def test_plugin_override_rejects_path_passing_through_runtime_current(
    tmp_path: Path,
) -> None:
    """A path literally passing through runtime/current is refused."""
    current_scripts = tmp_path / "runtime" / "current" / "venv" / "bin"
    launcher_file = current_scripts / "aether-kanban-worker"
    _make_executable(launcher_file)

    resolved = hermes_plugin._resolve_running_release_launcher(scripts_dir=current_scripts)
    assert resolved is None

    hermes_plugin._configure_hermes_bin_override(scripts_dir=current_scripts)
    assert "HERMES_BIN" not in os.environ


def test_plugin_override_resolves_symlinks_outside_runtime_current(
    tmp_path: Path,
) -> None:
    """A symlink from runtime/current to releases/<target> resolves to the release path."""
    release_dir = tmp_path / "releases" / "1.0.0rc17-xyz" / "runtime"
    release_scripts = release_dir / "bin"
    launcher_file = release_scripts / "aether-kanban-worker"
    _make_executable(launcher_file)

    # Symlink: runtime/current -> releases/1.0.0rc17-xyz/runtime
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    current_link = runtime_dir / "current"
    current_link.symlink_to(release_dir, target_is_directory=True)

    symlinked_scripts = current_link / "bin"
    resolved = hermes_plugin._resolve_running_release_launcher(scripts_dir=symlinked_scripts)
    assert resolved is not None
    assert resolved == launcher_file.resolve()
    assert "runtime/current" not in resolved.as_posix()


def test_plugin_override_not_triggered_for_non_morfeo_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profiles other than Morfeo do not set HERMES_BIN."""
    launcher_file = tmp_path / "releases" / "1.0.0" / "bin" / "aether-kanban-worker"
    _make_executable(launcher_file)
    monkeypatch.setattr(
        hermes_plugin,
        "_resolve_running_release_launcher",
        lambda scripts_dir=None: launcher_file.resolve(),
    )

    ctx = DummyContext(profile_name="supervisor")
    hermes_plugin.register(ctx)
    assert "HERMES_BIN" not in os.environ

    ctx2 = DummyContext(profile_name="morfeo", author_profile="other")
    hermes_plugin.register(ctx2)
    assert "HERMES_BIN" not in os.environ


# ---------------------------------------------------------------------------
# Part B: Launcher routing and eligibility tests (plan section 3.5)
# ---------------------------------------------------------------------------


class HarnessTestHarness:
    """Builds a hermetic, disposable environment for testing launcher routing."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.tmp_path = tmp_path
        self.monkeypatch = monkeypatch

        # Directories
        self.kanban_home = tmp_path / "kanban_home"
        self.board_slug = "oc-test-board-v1"
        self.board_dir = self.kanban_home / "kanban" / "boards" / self.board_slug
        self.board_dir.mkdir(parents=True)

        self.workspace_dir = tmp_path / "workspaces" / "t_test1234"
        self.workspace_dir.mkdir(parents=True)

        # Database and metadata
        self.db_path = self.board_dir / "kanban.db"
        self.metadata_path = self.board_dir / "board.json"
        self._init_database()
        self._init_metadata()

        # Tools on PATH: stub hermes and stub claude
        self.bin_dir = tmp_path / "bin"
        self.bin_dir.mkdir(parents=True)
        self.hermes_log_file = tmp_path / "hermes_recorded.json"
        self._create_stub_hermes()
        self._create_stub_claude()

        # Update PATH with clean isolated paths so only self.bin_dir supplies hermes/claude
        current_path = os.environ.get("PATH", "")
        clean_paths = [
            p
            for p in current_path.split(os.pathsep)
            if p and not (Path(p) / "hermes").exists() and not (Path(p) / "claude").exists()
        ]
        isolated_path = os.pathsep.join(
            [str(self.bin_dir), str(Path(sys.executable).parent), *clean_paths]
        )
        self.monkeypatch.setenv("PATH", isolated_path)

        # Set standard eligible environment
        self.task_id = "t_test1234"
        self.run_id = 42
        self.claim_lock = "test-host:12345"

        self.monkeypatch.setenv("HERMES_KANBAN_HOME", str(self.kanban_home))
        self.monkeypatch.setenv("HERMES_KANBAN_TASK", self.task_id)
        self.monkeypatch.setenv("HERMES_KANBAN_RUN_ID", str(self.run_id))
        self.monkeypatch.setenv("HERMES_KANBAN_CLAIM_LOCK", self.claim_lock)
        self.monkeypatch.setenv("HERMES_KANBAN_DB", str(self.db_path))
        self.monkeypatch.setenv("HERMES_KANBAN_BOARD", self.board_slug)
        self.monkeypatch.setenv("HERMES_KANBAN_WORKSPACE", str(self.workspace_dir))
        self.monkeypatch.setenv("HERMES_PROFILE", "implementer")

        self.default_argv = [
            "-p",
            "implementer",
            "--cli",
            "--accept-hooks",
            "--toolsets",
            "aether_contracts",
        ]

    def _init_database(self, source_status: str | None = None) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                run_id INTEGER,
                kind TEXT NOT NULL,
                payload TEXT,
                created_at INTEGER NOT NULL
            )
            """
        )
        payload: dict[str, Any] = {
            "lock": "test-host:12345",
            "expires": 9999999999,
            "run_id": 42,
        }
        if source_status:
            payload["source_status"] = source_status
        conn.execute(
            "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            ("t_test1234", 42, "claimed", json.dumps(payload), 1000),
        )
        conn.commit()
        conn.close()

    def _init_metadata(
        self,
        *,
        contract_id: str = "oc_f1ea2c4a2e0662da",
        project_id: str = "12027989-a08f-41cd-a82c-54ff1bfb6b03",
        version: int = 1,
        harness: str = "claude-code",
        archived: bool = False,
    ) -> None:
        data = {
            "slug": self.board_slug,
            "name": f"Objective {contract_id}@v{version}",
            "aether_contract_id": contract_id,
            "aether_project_id": project_id,
            "aether_contract_version": version,
            "aether_implementer_harness": harness,
            "archived": archived,
        }
        self.metadata_path.write_text(json.dumps(data), encoding="utf-8")

    def _create_stub_hermes(self) -> None:
        hermes_bin = self.bin_dir / "hermes"
        script = (
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "log_path = " + repr(str(self.hermes_log_file)) + "\n"
            "with open(log_path, 'w', encoding='utf-8') as f:\n"
            "    json.dump({'argv': sys.argv, 'env': dict(os.environ)}, f)\n"
            "sys.exit(0)\n"
        )
        _make_executable(hermes_bin, script)

    def _create_stub_claude(self) -> None:
        claude_bin = self.bin_dir / "claude"
        _make_executable(claude_bin, f"#!{sys.executable}\nimport sys\nsys.exit(0)\n")

    def read_hermes_recording(self) -> dict[str, Any] | None:
        if not self.hermes_log_file.exists():
            return None
        return json.loads(self.hermes_log_file.read_text(encoding="utf-8"))


def test_baseline_eligible_attempt_reaches_adapter_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When all section 3.5 conditions hold, the launcher calls the Claude adapter seam."""
    import types

    env = HarnessTestHarness(tmp_path, monkeypatch)

    mock_run_attempt = MagicMock(return_value=0)
    adapter_mod = types.ModuleType("aether_agents.claude_code_adapter")
    setattr(adapter_mod, "run_attempt", mock_run_attempt)
    monkeypatch.setitem(sys.modules, "aether_agents.claude_code_adapter", adapter_mod)

    assert launcher.is_eligible_for_claude_code(env.default_argv) is True

    result = launcher.main(env.default_argv)
    assert result == 0

    mock_run_attempt.assert_called_once()
    called_argv, called_env = mock_run_attempt.call_args[0]
    assert called_argv[0] == "aether-kanban-worker"
    assert called_argv[1:] == env.default_argv
    assert called_env["HERMES_KANBAN_TASK"] == env.task_id
    assert called_env["HERMES_PROFILE"] == "implementer"

    # Confirm stub hermes was never invoked
    assert env.read_hermes_recording() is None


def test_eligible_returns_adapter_exit_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The launcher returns adapter exit status codes directly (0, 76, 143)."""
    import types

    env = HarnessTestHarness(tmp_path, monkeypatch)

    for code in (0, 76, 143):
        mock_run_attempt = MagicMock(return_value=code)
        adapter_mod = types.ModuleType("aether_agents.claude_code_adapter")
        setattr(adapter_mod, "run_attempt", mock_run_attempt)
        monkeypatch.setitem(sys.modules, "aether_agents.claude_code_adapter", adapter_mod)

        result = launcher.main(env.default_argv)
        assert result == code


def test_main_reads_sys_argv_when_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When argv is omitted, main reads sys.argv directly."""
    import types

    env = HarnessTestHarness(tmp_path, monkeypatch)

    mock_run_attempt = MagicMock(return_value=0)
    adapter_mod = types.ModuleType("aether_agents.claude_code_adapter")
    setattr(adapter_mod, "run_attempt", mock_run_attempt)
    monkeypatch.setitem(sys.modules, "aether_agents.claude_code_adapter", adapter_mod)

    monkeypatch.setattr(sys, "argv", ["/opt/aether/bin/aether-kanban-worker", *env.default_argv])
    result = launcher.main()
    assert result == 0

    mock_run_attempt.assert_called_once()
    called_argv, _ = mock_run_attempt.call_args[0]
    assert called_argv[0] == "/opt/aether/bin/aether-kanban-worker"
    assert called_argv[1:] == env.default_argv


def test_passthrough_never_imports_claude_code_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On an ineligible attempt, claude_code_adapter is never imported."""
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_PROFILE", "supervisor")  # not eligible

    monkeypatch.delitem(sys.modules, "aether_agents.claude_code_adapter", raising=False)

    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv
    assert "aether_agents.claude_code_adapter" not in sys.modules


def test_passthrough_preserves_argv_tail_and_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When not eligible, pass-through execs hermes with unchanged argv tail and environment."""
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_PROFILE", "supervisor")
    monkeypatch.setenv("CUSTOM_TEST_VAR", "test-value-12345")

    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][0] == str(env.bin_dir / "hermes")
    assert rec["argv"][1:] == env.default_argv
    assert rec["env"]["CUSTOM_TEST_VAR"] == "test-value-12345"
    assert rec["env"]["HERMES_PROFILE"] == "supervisor"


def _run_launcher_subprocess(env_harness: HarnessTestHarness, argv: list[str]) -> dict[str, Any]:
    """Execute the launcher in a subprocess and return the recorded Hermes invocation."""
    import subprocess

    cmd = [sys.executable, "-m", "aether_agents.kanban_worker_launcher", *argv]
    env = dict(os.environ)
    if HERMES_CHECKOUT:
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = f"{HERMES_CHECKOUT}:{existing}" if existing else str(HERMES_CHECKOUT)

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Subprocess failed with code {result.returncode}: {result.stderr}"
    )
    recorded = env_harness.read_hermes_recording()
    assert recorded is not None, "Hermes stub was not executed by pass-through"
    return recorded


# ---------------------------------------------------------------------------
# Individual condition tests forcing exact pass-through
# ---------------------------------------------------------------------------


def test_condition_1_missing_task_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_KANBAN_TASK")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False

    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_1_missing_run_id_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_KANBAN_RUN_ID")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_1_missing_claim_lock_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_KANBAN_CLAIM_LOCK")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_1_missing_db_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_KANBAN_DB")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_1_missing_board_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_KANBAN_BOARD")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_1_missing_workspace_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_KANBAN_WORKSPACE")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_1_workspace_not_existing_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_KANBAN_WORKSPACE", str(tmp_path / "non_existent_workspace"))
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_2_profile_not_implementer_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_PROFILE", "supervisor")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv

    monkeypatch.setenv("HERMES_PROFILE", "morfeo")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False


def test_condition_3_board_json_missing_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    env.metadata_path.unlink()
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_board_json_corrupt_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    env.metadata_path.write_text("{broken json", encoding="utf-8")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_board_json_symlink_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    real_meta = tmp_path / "real_board.json"
    env.metadata_path.rename(real_meta)
    env.metadata_path.symlink_to(real_meta)

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_board_dir_symlink_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    real_dir = tmp_path / "real_dir"
    env.board_dir.rename(real_dir)
    env.board_dir.symlink_to(real_dir, target_is_directory=True)

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_database_symlink_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    real_db = tmp_path / "real_kanban.db"
    env.db_path.rename(real_db)
    env.db_path.symlink_to(real_db)

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_board_redirection_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Board path resolved outside canonical boards_root / board_slug is rejected."""
    env = HarnessTestHarness(tmp_path, monkeypatch)
    other_dir = tmp_path / "other_boards" / "redirected_board"
    other_dir.mkdir(parents=True)
    shutil.copy(env.db_path, other_dir / "kanban.db")
    shutil.copy(env.metadata_path, other_dir / "board.json")

    monkeypatch.setenv("HERMES_KANBAN_DB", str(other_dir / "kanban.db"))
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_missing_contract_identity_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    # Write metadata missing aether_contract_id
    data = {
        "slug": env.board_slug,
        "aether_project_id": "12027989-a08f-41cd-a82c-54ff1bfb6b03",
        "aether_contract_version": 1,
        "aether_implementer_harness": "claude-code",
    }
    env.metadata_path.write_text(json.dumps(data), encoding="utf-8")

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_harness_not_claude_code_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    # Absent or "hermes" harness
    env._init_metadata(harness="hermes")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_3_archived_board_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    env._init_metadata(archived=True)
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_4_goal_mode_is_1_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_KANBAN_GOAL_MODE", "1")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_5_claimed_event_review_status_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    # Re-init db with source_status: "review"
    env.db_path.unlink()
    env._init_database(source_status="review")

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_5_missing_current_run_claim_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A work claim recorded for another run is not evidence for this attempt.

    The database holds a work claim for run 10 only. Querying run 11 must be
    ineligible, so the attempt passes through to Hermes (plan section 3.5,
    condition 5).
    """
    env = HarnessTestHarness(tmp_path, monkeypatch)
    env.db_path.unlink()
    env._init_database()
    conn = sqlite3.connect(env.db_path)
    conn.execute("UPDATE task_events SET run_id = 10 WHERE kind = 'claimed'")
    conn.commit()
    conn.close()
    monkeypatch.setenv("HERMES_KANBAN_RUN_ID", "11")

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_5_review_affinity_set_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_KANBAN_REVIEW_AFFINITY", "affinity-token")
    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_condition_5_argv_has_resume_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    argv = [*env.default_argv, "--resume"]
    assert launcher.is_eligible_for_claude_code(argv) is False
    rec = _run_launcher_subprocess(env, argv)
    assert rec["argv"][1:] == argv


def test_condition_6_argv_has_model_override_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    argv = [*env.default_argv, "-m", "custom-model"]
    assert launcher.is_eligible_for_claude_code(argv) is False
    rec = _run_launcher_subprocess(env, argv)
    assert rec["argv"][1:] == argv


def test_condition_6_argv_has_provider_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    argv = [*env.default_argv, "--provider", "openrouter"]
    assert launcher.is_eligible_for_claude_code(argv) is False
    rec = _run_launcher_subprocess(env, argv)
    assert rec["argv"][1:] == argv


def test_condition_6_argv_has_reasoning_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    argv = [*env.default_argv, "--reasoning", "high"]
    assert launcher.is_eligible_for_claude_code(argv) is False
    rec = _run_launcher_subprocess(env, argv)
    assert rec["argv"][1:] == argv


def test_condition_7_claude_not_on_path_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    claude_bin = env.bin_dir / "claude"
    claude_bin.unlink()

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_decision_exception_unreadable_database_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    # Corrupt database bytes
    env.db_path.write_bytes(b"not a valid sqlite database file")

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_decision_exception_missing_events_table_forces_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = HarnessTestHarness(tmp_path, monkeypatch)
    env.db_path.unlink()
    # Create empty db without task_events table
    conn = sqlite3.connect(env.db_path)
    conn.execute("CREATE TABLE other_table (id INT)")
    conn.commit()
    conn.close()

    assert launcher.is_eligible_for_claude_code(env.default_argv) is False
    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][1:] == env.default_argv


def test_passthrough_never_rereads_hermes_bin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass-through executes hermes or module, never looping back to HERMES_BIN."""
    env = HarnessTestHarness(tmp_path, monkeypatch)
    # Set HERMES_BIN pointing to a nonexistent or self path
    monkeypatch.setenv("HERMES_BIN", "/nonexistent/fake/aether-kanban-worker")
    monkeypatch.setenv("HERMES_PROFILE", "supervisor")  # not eligible

    rec = _run_launcher_subprocess(env, env.default_argv)
    assert rec["argv"][0] == str(env.bin_dir / "hermes")
    assert rec["argv"][1:] == env.default_argv
    # The recorded environment retains the inherited HERMES_BIN without launcher re-evaluating it
    assert rec["env"]["HERMES_BIN"] == "/nonexistent/fake/aether-kanban-worker"


def test_passthrough_module_fallback_when_hermes_not_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When hermes is not on PATH, pass-through falls back to sys.executable -m hermes_cli.main."""
    env = HarnessTestHarness(tmp_path, monkeypatch)
    # Remove stub hermes
    (env.bin_dir / "hermes").unlink()

    execv_calls: list[tuple[str, list[str]]] = []

    def mock_execv(target: str, cmd: list[str]) -> None:
        execv_calls.append((target, cmd))
        sys.exit(0)

    monkeypatch.setattr(os, "execv", mock_execv)

    with pytest.raises(SystemExit):
        launcher.pass_through_to_hermes(env.default_argv)

    assert len(execv_calls) == 1
    target, cmd = execv_calls[0]
    assert target == sys.executable
    assert cmd == [sys.executable, "-m", "hermes_cli.main", *env.default_argv]
