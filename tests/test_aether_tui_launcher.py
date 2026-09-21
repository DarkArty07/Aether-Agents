"""Regression and unit tests for the packaged Morfeo TUI launcher (LG-CLI / #480)."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
_SRC = ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aether_agents.cli import main as cli_main  # noqa: E402
from aether_agents.observation.context import ProjectRegistry  # noqa: E402

LAUNCHER = ROOT / "scripts" / "aether_tui.py"
EXPECTED_PLAN_KEYS = [
    "command",
    "cwd",
    "hermes_executable",
    "hermes_home",
    "project_id",
    "repo_root",
    "required_toolsets",
    "result",
    "tui_dir",
]


class MorfeoTuiLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-tui-launcher-")
        self._orig_state = os.environ.get("XDG_STATE_HOME")
        self._orig_data = os.environ.get("XDG_DATA_HOME")
        self._orig_project_root = os.environ.get("AETHER_PROJECT_ROOT")
        self._orig_project_id = os.environ.get("AETHER_PROJECT_ID")
        self._orig_hermes_root = os.environ.get("AETHER_HERMES_ROOT")
        self._orig_runtime_root = os.environ.get("AETHER_RUNTIME_ROOT")

        os.environ["XDG_STATE_HOME"] = str(Path(self.tempdir.name) / "state")
        os.environ["XDG_DATA_HOME"] = str(Path(self.tempdir.name) / "data")
        os.environ.pop("AETHER_PROJECT_ROOT", None)
        os.environ.pop("AETHER_PROJECT_ID", None)
        os.environ.pop("AETHER_HERMES_ROOT", None)
        os.environ.pop("AETHER_RUNTIME_ROOT", None)

        self.root = Path(self.tempdir.name) / "aether"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "home" / "profiles" / "morfeo").mkdir(parents=True)
        (self.root / "home" / ".venv-hermes" / "bin").mkdir(parents=True)
        (self.root / "home" / "tui").mkdir(parents=True)
        (self.root / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        marker = self.root / ".aether" / "project.toml"
        marker.parent.mkdir(parents=True)
        marker.write_text(
            "\n".join(
                (
                    "schema_version = 1",
                    'project_id = "12027989-a08f-41cd-a82c-54ff1bfb6b03"',
                    'name = "Aether launcher fixture"',
                    'initialized_by = "1.0.0"',
                    'forge = "local"',
                    'contract_root = "specs"',
                    'default_branch = "main"',
                    "",
                )
            ),
            encoding="utf-8",
        )
        (self.root / "home" / "profiles" / "morfeo" / "SOUL.md").write_text(
            "# Morfeo\n", encoding="utf-8"
        )
        (self.root / "home" / "profiles" / "morfeo" / "config.yaml").write_text(
            "toolsets:\n  - kanban\n  - file\n  - terminal\n",
            encoding="utf-8",
        )
        venv_dir = self.root / "home" / ".venv-hermes"
        (venv_dir / "bin").mkdir(parents=True, exist_ok=True)
        (venv_dir / "pyvenv.cfg").write_text(
            f"home = {sys.base_prefix}/bin\ninclude-system-site-packages = false\nversion = {sys.version.split()[0]}\n",
            encoding="utf-8",
        )
        hermes = venv_dir / "bin" / "hermes"
        hermes.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes.chmod(0o755)
        py = venv_dir / "bin" / "python"
        py.symlink_to(sys.executable)
        shutil.copy2(LAUNCHER, self.root / "scripts" / LAUNCHER.name)
        self.launcher = self.root / "scripts" / LAUNCHER.name

        self.registry = ProjectRegistry()
        self.registry.register(
            "12027989-a08f-41cd-a82c-54ff1bfb6b03",
            self.root,
            name="launcher-fixture",
        )

    def tearDown(self) -> None:
        if self._orig_state is not None:
            os.environ["XDG_STATE_HOME"] = self._orig_state
        else:
            os.environ.pop("XDG_STATE_HOME", None)
        if self._orig_data is not None:
            os.environ["XDG_DATA_HOME"] = self._orig_data
        else:
            os.environ.pop("XDG_DATA_HOME", None)
        if self._orig_project_root is not None:
            os.environ["AETHER_PROJECT_ROOT"] = self._orig_project_root
        else:
            os.environ.pop("AETHER_PROJECT_ROOT", None)
        if self._orig_project_id is not None:
            os.environ["AETHER_PROJECT_ID"] = self._orig_project_id
        else:
            os.environ.pop("AETHER_PROJECT_ID", None)
        if self._orig_hermes_root is not None:
            os.environ["AETHER_HERMES_ROOT"] = self._orig_hermes_root
        else:
            os.environ.pop("AETHER_HERMES_ROOT", None)
        if self._orig_runtime_root is not None:
            os.environ["AETHER_RUNTIME_ROOT"] = self._orig_runtime_root
        else:
            os.environ.pop("AETHER_RUNTIME_ROOT", None)
        self.tempdir.cleanup()

    def _shim_env(self, env: dict[str, str] | None = None) -> dict[str, str]:
        """Bare-python subprocesses need the packaged launcher on sys.path."""

        merged = dict(os.environ)
        for k in list(merged.keys()):
            if k.startswith("COV_CORE_") or k.startswith("COVERAGE_"):
                merged.pop(k, None)
        if env is not None:
            merged.update(env)
        existing = merged.get("PYTHONPATH", "")
        src = str(ROOT / "src")
        merged["PYTHONPATH"] = src if not existing else os.pathsep.join((src, existing))
        return merged

    def run_check(
        self, cwd: Path, *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        merged = self._shim_env(env)
        return subprocess.run(
            [sys.executable, str(self.launcher), "--check"],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            env=merged,
        )

    def load_module(self):
        spec = importlib.util.spec_from_file_location("aether_tui_tested", self.launcher)
        if spec is None or spec.loader is None:
            self.fail("unable to load launcher module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_check_is_independent_of_calling_directory(self) -> None:
        reports = []
        for cwd in (self.root, self.root.parent, Path("/tmp")):
            result = self.run_check(cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            reports.append(json.loads(result.stdout))

        self.assertEqual(reports[0], reports[1])
        self.assertEqual(reports[1], reports[2])
        report = reports[0]
        self.assertEqual(report["result"], "ready")
        self.assertEqual(report["repo_root"], str(self.root.resolve()))
        self.assertEqual(
            report["hermes_home"],
            str((self.root / "home" / "profiles" / "morfeo").resolve()),
        )
        self.assertEqual(report["cwd"], str(self.root.resolve()))
        self.assertEqual(report["project_id"], "12027989-a08f-41cd-a82c-54ff1bfb6b03")
        self.assertEqual(report["required_toolsets"], ["file", "kanban"])
        self.assertEqual(report["tui_dir"], str((self.root / "home" / "tui").resolve()))
        self.assertEqual(
            report["command"],
            [
                str((self.root / "home" / ".venv-hermes" / "bin" / "hermes").resolve()),
                "--tui",
                "--in",
                str(self.root.resolve()),
            ],
        )

    def test_check_fails_visibly_when_required_toolset_is_missing(self) -> None:
        config = self.root / "home" / "profiles" / "morfeo" / "config.yaml"
        config.write_text("toolsets:\n  - file\n", encoding="utf-8")

        result = self.run_check(self.root)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("missing required Morfeo toolsets: kanban", result.stderr)

    def test_check_fails_visibly_when_tui_directory_is_missing(self) -> None:
        shutil.rmtree(self.root / "home" / "tui")
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Morfeo TUI directory does not exist", result.stderr)

    def test_check_fails_visibly_when_profile_or_executable_is_missing(self) -> None:
        profile = self.root / "home" / "profiles" / "morfeo"
        moved = profile.with_name("morfeo.missing")
        profile.rename(moved)
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Morfeo profile directory does not exist", result.stderr)
        moved.rename(profile)

        hermes = self.root / "home" / ".venv-hermes" / "bin" / "hermes"
        hermes.chmod(0o644)
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Hermes executable is not executable", result.stderr)

    def test_check_supports_separated_runtime_and_state_roots(self) -> None:
        project = Path(self.tempdir.name) / "project"
        profile = Path(self.tempdir.name) / "state" / "hermes" / "profiles" / "morfeo"
        runtime = Path(self.tempdir.name) / "runtime" / "current"
        hermes = runtime / "venv" / "bin" / "hermes"
        tui = runtime / "tui"

        project.mkdir(parents=True)
        (project / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        (project / ".aether").mkdir()
        sep_marker = (
            (self.root / ".aether" / "project.toml")
            .read_text(encoding="utf-8")
            .replace(
                "12027989-a08f-41cd-a82c-54ff1bfb6b03",
                "33333333-3333-4333-8333-333333333333",
            )
        )
        (project / ".aether" / "project.toml").write_text(sep_marker, encoding="utf-8")

        profile.mkdir(parents=True)
        shutil.copy2(self.root / "home/profiles/morfeo/config.yaml", profile / "config.yaml")
        shutil.copy2(self.root / "home/profiles/morfeo/SOUL.md", profile / "SOUL.md")
        hermes.parent.mkdir(parents=True)
        hermes.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes.chmod(0o755)
        tui.mkdir(parents=True)

        environment = dict(os.environ)
        environment.update(
            {
                "AETHER_PROJECT_ROOT": str(project),
                "AETHER_HERMES_ROOT": str(Path(self.tempdir.name) / "state" / "hermes"),
                "AETHER_RUNTIME_ROOT": str(runtime),
            }
        )
        result = self.run_check(Path("/tmp"), env=environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["repo_root"], str(project.resolve()))
        self.assertEqual(report["hermes_home"], str(profile.resolve()))
        self.assertEqual(report["hermes_executable"], str(hermes.resolve()))
        self.assertEqual(report["tui_dir"], str(tui.resolve()))
        self.assertEqual(
            report["command"],
            [str(hermes.resolve()), "--tui", "--in", str(project.resolve())],
        )

    def test_separated_runtime_paths_must_be_absolute(self) -> None:
        environment = dict(os.environ)
        environment["AETHER_PROJECT_ROOT"] = "relative/project"

        result = self.run_check(self.root, env=environment)

        self.assertEqual(result.returncode, 2)
        self.assertIn("AETHER_PROJECT_ROOT must be an absolute path", result.stderr)

    def test_launch_executes_canonical_command_with_clean_python_and_hermes_env(
        self,
    ) -> None:
        module = self.load_module()
        dirty_env = {
            "PATH": os.environ.get("PATH", ""),
            "PWD": "/tmp/caller-directory",
            "XDG_STATE_HOME": os.environ.get("XDG_STATE_HOME", ""),
            "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME", ""),
            "HERMES_PROFILE": "wrong-profile",
            "PYTHONPATH": "/tmp/stale-pythonpath",
            "PYTHONHOME": "/tmp/stale-pythonhome",
            "PYTHONSTARTUP": "/tmp/stale-startup",
            "HERMES_TUI_DIR": "/tmp/ambient-tui",
            "HERMES_TUI_PORT": "9999",
            "HERMES_SESSION_ID": "session-12345",
            "HERMES_KANBAN_TASK": "t_abc123",
            "HERMES_KANBAN_DB": "/tmp/kanban.db",
            "HERMES_TASK_ID": "task-xyz",
            "HERMES_CRON_JOB": "cron-1",
            "CUSTOM_API_KEY": "keep-this-credential",
            "KEEP_ME": "yes",
        }
        expected_root = self.root.resolve()
        expected_home = (self.root / "home" / "profiles" / "morfeo").resolve()
        expected_hermes = (self.root / "home" / ".venv-hermes" / "bin" / "hermes").resolve()
        expected_tui = (self.root / "home" / "tui").resolve()

        with (
            patch.object(module.os, "environ", dirty_env),
            patch.object(module.os, "chdir") as chdir,
            patch.object(
                module.os, "execve", side_effect=RuntimeError("exec intercepted")
            ) as execve,
            self.assertRaisesRegex(RuntimeError, "exec intercepted"),
        ):
            module.main(["--project", str(self.root), "--resume", "latest"])

        chdir.assert_called_once_with(expected_root)
        command = [
            str(expected_hermes),
            "--tui",
            "--in",
            str(expected_root),
            "--resume",
            "latest",
        ]
        called_executable, called_command, called_env = execve.call_args.args
        self.assertEqual(called_executable, str(expected_hermes))
        self.assertEqual(called_command, command)
        self.assertEqual(called_env["HERMES_HOME"], str(expected_home))
        self.assertEqual(called_env["PWD"], str(expected_root))
        self.assertEqual(called_env["AETHER_PROJECT_ID"], "12027989-a08f-41cd-a82c-54ff1bfb6b03")
        self.assertEqual(called_env["HERMES_TUI_DIR"], str(expected_tui))
        self.assertEqual(called_env["CUSTOM_API_KEY"], "keep-this-credential")
        self.assertEqual(called_env["KEEP_ME"], "yes")
        expected_py = self.root / "home" / ".venv-hermes" / "bin" / "python"
        self.assertEqual(called_env["HERMES_PYTHON"], str(expected_py))
        self.assertNotEqual(called_env["HERMES_PYTHON"], str(expected_py.resolve()))
        self.assertNotIn("HERMES_PROFILE", called_env)
        self.assertNotIn("PYTHONPATH", called_env)
        self.assertNotIn("PYTHONHOME", called_env)
        self.assertNotIn("PYTHONSTARTUP", called_env)
        self.assertNotIn("HERMES_TUI_PORT", called_env)
        self.assertNotIn("HERMES_SESSION_ID", called_env)
        self.assertNotIn("HERMES_KANBAN_TASK", called_env)
        self.assertNotIn("HERMES_KANBAN_DB", called_env)
        self.assertNotIn("HERMES_TASK_ID", called_env)
        self.assertNotIn("HERMES_CRON_JOB", called_env)

    def test_check_rejects_missing_or_invalid_project_marker(self) -> None:
        marker = self.root / ".aether" / "project.toml"
        marker.unlink()
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("portable Aether project marker", result.stderr)

        marker.write_text('project_id = "not-a-uuid"\n', encoding="utf-8")
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("canonical schema", result.stderr)

    def test_reserved_binding_arguments_are_rejected(self) -> None:
        for argument in (
            "--in=/tmp",
            "--profile",
            "--tui",
            "--cli",
            "--toolsets=file",
            "-t",
            "--safe-mode",
            "--ignore-user-config",
            "--ignore-rules",
        ):
            with self.subTest(argument=argument):
                result = subprocess.run(
                    [sys.executable, str(self.launcher), "--check", argument],
                    cwd=self.root,
                    text=True,
                    capture_output=True,
                    check=False,
                    env=self._shim_env(),
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(
                    "is controlled by the canonical Morfeo launcher",
                    result.stderr,
                )

    def test_versioned_launcher_contains_no_machine_specific_home(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"/home/[A-Za-z0-9._-]+/", source))
        self.assertTrue(bool(LAUNCHER.stat().st_mode & stat.S_IXUSR))

        packaged = ROOT / "src" / "aether_agents" / "launcher.py"
        packaged_source = packaged.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"/home/[A-Za-z0-9._-]+/", packaged_source))

    def test_json_mode_non_mutating_plan_keys(self) -> None:
        from aether_agents.launcher import main as launcher_main

        buffer = io.StringIO()
        with (
            redirect_stdout(buffer),
            patch.object(os, "execve") as execve,
        ):
            code = launcher_main(["--json", "--project", str(self.root)])
            self.assertEqual(code, 0)
            execve.assert_not_called()

        plan = json.loads(buffer.getvalue())
        self.assertEqual(sorted(plan.keys()), EXPECTED_PLAN_KEYS)
        self.assertEqual(plan["result"], "ready")
        self.assertEqual(plan["project_id"], "12027989-a08f-41cd-a82c-54ff1bfb6b03")
        self.assertEqual(plan["repo_root"], str(self.root.resolve()))
        self.assertEqual(plan["cwd"], str(self.root.resolve()))
        self.assertEqual(plan["tui_dir"], str((self.root / "home" / "tui").resolve()))

    def test_cli_bare_dispatch_and_clean_installed_path(self) -> None:
        # CLI aether [--project PATH] [--json] dispatches to packaged launcher
        buffer = io.StringIO()
        with (
            redirect_stdout(buffer),
            patch.object(os, "execve") as execve,
        ):
            code = cli_main(["--project", str(self.root), "--json"])
            self.assertEqual(code, 0)
            execve.assert_not_called()

        plan = json.loads(buffer.getvalue())
        self.assertEqual(plan["result"], "ready")
        self.assertEqual(plan["project_id"], "12027989-a08f-41cd-a82c-54ff1bfb6b03")

    def test_cli_main_resume_latest_json(self) -> None:
        # Installed CLI `aether --project PATH --json --resume latest` (two-token)
        buffer = io.StringIO()
        with (
            redirect_stdout(buffer),
            patch.object(os, "execve") as execve,
        ):
            code = cli_main(["--project", str(self.root), "--json", "--resume", "latest"])
            self.assertEqual(code, 0)
            execve.assert_not_called()

        plan = json.loads(buffer.getvalue())
        self.assertEqual(plan["result"], "ready")
        self.assertIn("--resume", plan["command"])
        idx = plan["command"].index("--resume")
        self.assertEqual(plan["command"][idx + 1], "latest")

        # Also verify bare --resume (expands to latest)
        buffer_bare = io.StringIO()
        with (
            redirect_stdout(buffer_bare),
            patch.object(os, "execve") as execve,
        ):
            code = cli_main(["--project", str(self.root), "--json", "--resume"])
            self.assertEqual(code, 0)
            execve.assert_not_called()

        plan_bare = json.loads(buffer_bare.getvalue())
        self.assertEqual(plan_bare["result"], "ready")
        self.assertIn("--resume", plan_bare["command"])
        idx = plan_bare["command"].index("--resume")
        self.assertEqual(plan_bare["command"][idx + 1], "latest")

    def test_cli_main_resume_latest_exec(self) -> None:
        # Installed CLI `aether --project PATH --resume latest` executes with --resume latest
        with (
            patch.object(os, "chdir"),
            patch.object(os, "execve", side_effect=RuntimeError("exec intercepted")) as execve,
            self.assertRaisesRegex(RuntimeError, "exec intercepted"),
        ):
            cli_main(["--project", str(self.root), "--resume", "latest"])

        _exec, command, _env = execve.call_args.args
        self.assertIn("--resume", command)
        idx = command.index("--resume")
        self.assertEqual(command[idx + 1], "latest")

    def test_cli_main_empty_project_fails_visibly_no_assertion_no_cwd_guess(self) -> None:
        # Empty --project string must return exit 2, print visible error, never raise, never guess cwd
        err_buffer = io.StringIO()
        with (
            redirect_stdout(io.StringIO()),
            patch("sys.stderr", err_buffer),
            patch.object(Path, "cwd", return_value=self.root),
        ):
            code = cli_main(["--project", "", "--json"])
            self.assertEqual(code, 2)
            self.assertIn("project path must not be empty", err_buffer.getvalue())

    def test_cli_main_empty_project_root_env_fails_visibly_no_assertion_no_cwd_guess(self) -> None:
        # AETHER_PROJECT_ROOT="" must return exit 2, print visible error, never raise, never guess cwd
        err_buffer = io.StringIO()
        with (
            redirect_stdout(io.StringIO()),
            patch("sys.stderr", err_buffer),
            patch.dict(os.environ, {"AETHER_PROJECT_ROOT": ""}),
            patch.object(Path, "cwd", return_value=self.root),
        ):
            code = cli_main(["--json"])
            self.assertEqual(code, 2)
            self.assertIn("AETHER_PROJECT_ROOT must not be empty", err_buffer.getvalue())

    def test_cli_subprocess_resume_latest_and_empty_identity(self) -> None:
        sub_env = dict(os.environ)
        for k in list(sub_env.keys()):
            if k.startswith("COV_CORE_") or k.startswith("COVERAGE_"):
                sub_env.pop(k, None)
        sub_env["PYTHONPATH"] = str(ROOT / "src")

        # 1. --resume latest produces ready plan through full CLI subprocess
        res1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "aether_agents.cli",
                "--project",
                str(self.root),
                "--json",
                "--resume",
                "latest",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=sub_env,
        )
        self.assertEqual(res1.returncode, 0)
        plan = json.loads(res1.stdout)
        self.assertEqual(plan["result"], "ready")
        self.assertIn("--resume", plan["command"])
        idx = plan["command"].index("--resume")
        self.assertEqual(plan["command"][idx + 1], "latest")

        # 2. empty --project fails visibly with exit 2, no AssertionError
        res2 = subprocess.run(
            [sys.executable, "-m", "aether_agents.cli", "--project", "", "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=sub_env,
        )
        self.assertEqual(res2.returncode, 2)
        self.assertIn("project path must not be empty", res2.stderr)
        self.assertNotIn("AssertionError", res2.stderr)

        # 3. empty AETHER_PROJECT_ROOT fails visibly with exit 2, no AssertionError
        sub_env["AETHER_PROJECT_ROOT"] = ""
        res3 = subprocess.run(
            [sys.executable, "-m", "aether_agents.cli", "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=sub_env,
        )
        self.assertEqual(res3.returncode, 2)
        self.assertIn("AETHER_PROJECT_ROOT must not be empty", res3.stderr)
        self.assertNotIn("AssertionError", res3.stderr)

    def test_project_resolution_conflict_between_marker_and_explicit_env(self) -> None:
        from aether_agents.launcher import ActivationError, inspect_activation

        with patch.dict(
            os.environ,
            {"AETHER_PROJECT_ID": "99999999-9999-4999-8999-999999999999"},
        ):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("conflicts with project marker", str(ctx.exception))

    def test_project_resolution_conflict_between_marker_and_registry(self) -> None:
        from aether_agents.launcher import ActivationError, inspect_activation

        other_path = Path(self.tempdir.name) / "other_project"
        other_path.mkdir(parents=True)
        # Re-register with a different path in the isolated registry
        self.registry.register(
            "12027989-a08f-41cd-a82c-54ff1bfb6b03",
            other_path,
            name="conflicting",
        )

        with self.assertRaises(ActivationError) as ctx:
            inspect_activation(project=self.root)
        self.assertIn("conflicts with registered path", str(ctx.exception))

    def test_project_resolution_via_verified_aether_project_id(self) -> None:
        from aether_agents.launcher import ActivationError, inspect_activation

        pid = "12027989-a08f-41cd-a82c-54ff1bfb6b03"

        with patch.dict(os.environ, {"AETHER_PROJECT_ID": pid}):
            plan = inspect_activation()
            self.assertEqual(plan["project_id"], pid)
            self.assertEqual(plan["repo_root"], str(self.root.resolve()))

        # Unregistered ID fails visibly
        with patch.dict(
            os.environ,
            {"AETHER_PROJECT_ID": "00000000-0000-4000-8000-000000000000"},
        ):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("is not registered", str(ctx.exception))

    def test_project_resolution_current_repo_marker(self) -> None:
        from aether_agents.launcher import ActivationError, inspect_activation

        pid = "12027989-a08f-41cd-a82c-54ff1bfb6b03"

        # When registered and agreed:
        with patch.object(Path, "cwd", return_value=self.root):
            plan = inspect_activation()
            self.assertEqual(plan["project_id"], pid)
            self.assertEqual(plan["repo_root"], str(self.root.resolve()))

        # When repository marker is NOT agreed in registry (clean state):
        clean_state = Path(self.tempdir.name) / "clean_state"
        with (
            patch.dict(os.environ, {"XDG_STATE_HOME": str(clean_state)}),
            patch.object(Path, "cwd", return_value=self.root),
        ):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn(
                "project registry and repository marker do not agree",
                str(ctx.exception),
            )

    def test_project_resolution_sole_registered_project(self) -> None:
        from aether_agents.launcher import ActivationError, inspect_activation

        pid = "12027989-a08f-41cd-a82c-54ff1bfb6b03"
        non_repo_dir = Path(self.tempdir.name) / "empty_dir"
        non_repo_dir.mkdir(parents=True)

        with patch.object(Path, "cwd", return_value=non_repo_dir):
            plan = inspect_activation()
            self.assertEqual(plan["project_id"], pid)
            self.assertEqual(plan["repo_root"], str(self.root.resolve()))

        # Add a second project -> ambiguous identity
        second_dir = Path(self.tempdir.name) / "second_project"
        second_dir.mkdir(parents=True)
        self.registry.register(
            "22222222-2222-4222-8222-222222222222",
            second_dir,
            name="second-project",
        )
        with patch.object(Path, "cwd", return_value=non_repo_dir):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("ambiguous project identity", str(ctx.exception))

    def test_additional_error_and_flag_handling(self) -> None:
        from aether_agents.launcher import ActivationError, _absolute_env_path, inspect_activation
        from aether_agents.launcher import main as launcher_main

        # _absolute_env_path returns None on empty
        self.assertIsNone(_absolute_env_path("NON_EXISTENT_VAR_XYZ"))

        # main with --project missing argument
        err_buf = io.StringIO()
        with redirect_stdout(err_buf):
            code = launcher_main(["--project"])
            self.assertEqual(code, 2)

        # main with --project=PATH syntax
        out_buf = io.StringIO()
        with redirect_stdout(out_buf), patch.object(os, "execve"):
            code = launcher_main(["--json", f"--project={self.root}"])
            self.assertEqual(code, 0)
        self.assertIn('"result": "ready"', out_buf.getvalue())

        # inspect_activation with extra_args containing --project
        plan1 = inspect_activation(["--project", str(self.root)])
        self.assertEqual(plan1["result"], "ready")

        plan2 = inspect_activation([f"--project={self.root}"])
        self.assertEqual(plan2["result"], "ready")

        # Empty AETHER_PROJECT_ID
        with patch.dict(os.environ, {"AETHER_PROJECT_ID": ""}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("AETHER_PROJECT_ID must not be empty", str(ctx.exception))

        # Invalid AETHER_PROJECT_ID UUID
        with patch.dict(os.environ, {"AETHER_PROJECT_ID": "not-a-uuid"}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("not a valid canonical UUID", str(ctx.exception))

        # Missing config.yaml
        config = self.root / "home" / "profiles" / "morfeo" / "config.yaml"
        config_bak = config.with_suffix(".bak")
        config.rename(config_bak)
        try:
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("Morfeo config does not exist", str(ctx.exception))
        finally:
            config_bak.rename(config)

        # Missing SOUL.md
        soul = self.root / "home" / "profiles" / "morfeo" / "SOUL.md"
        soul_bak = soul.with_suffix(".bak")
        soul.rename(soul_bak)
        try:
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("Morfeo SOUL does not exist", str(ctx.exception))
        finally:
            soul_bak.rename(soul)

        # Unreadable marker (corrupt TOML)
        marker = self.root / ".aether" / "project.toml"
        orig_marker = marker.read_text(encoding="utf-8")
        marker.write_text("[invalid toml", encoding="utf-8")
        try:
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("portable Aether project marker is unreadable", str(ctx.exception))
        finally:
            marker.write_text(orig_marker, encoding="utf-8")

        # Missing AGENTS.md
        agents = self.root / "AGENTS.md"
        agents_bak = agents.with_suffix(".bak")
        agents.rename(agents_bak)
        try:
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("Aether repository marker does not exist", str(ctx.exception))
        finally:
            agents_bak.rename(agents)

        # Relative AETHER_RUNTIME_ROOT
        with patch.dict(os.environ, {"AETHER_RUNTIME_ROOT": "relative/runtime"}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("must be an absolute path", str(ctx.exception))

        # AETHER_PROJECT_ROOT used when project arg is None
        with patch.dict(os.environ, {"AETHER_PROJECT_ROOT": str(self.root)}):
            p = inspect_activation()
            self.assertEqual(p["result"], "ready")

        # inspect_activation with trailing --project without value
        with self.assertRaises(ActivationError):
            inspect_activation(["--project"])

        # Empty registry and not in project directory
        clean_state_2 = Path(self.tempdir.name) / "clean_state_2"
        empty_dir = Path(self.tempdir.name) / "empty_dir_2"
        empty_dir.mkdir(parents=True)
        with (
            patch.dict(os.environ, {"XDG_STATE_HOME": str(clean_state_2)}),
            patch.object(Path, "cwd", return_value=empty_dir),
        ):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("registry is empty", str(ctx.exception))

        # Registered path for AETHER_PROJECT_ID does not exist
        missing_dir = Path(self.tempdir.name) / "missing_proj_dir"
        self.registry.register(
            "44444444-4444-4444-8444-444444444444",
            missing_dir,
            name="missing-proj",
        )
        with patch.dict(os.environ, {"AETHER_PROJECT_ID": "44444444-4444-4444-8444-444444444444"}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("does not exist", str(ctx.exception))

        # Empty project paths and environment variables
        with self.assertRaises(ActivationError) as ctx:
            inspect_activation(project="")
        self.assertIn("project path must not be empty", str(ctx.exception))

        empty_path = Path("")
        if getattr(empty_path, "_raw_paths", None) is not None:
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=empty_path)
            self.assertIn("project path must not be empty", str(ctx.exception))

        with self.assertRaises(ActivationError) as ctx:
            inspect_activation(["--project", ""])
        self.assertIn("project path must not be empty", str(ctx.exception))

        with self.assertRaises(ActivationError) as ctx:
            inspect_activation(["--project="])
        self.assertIn("project path must not be empty", str(ctx.exception))

        with patch.dict(os.environ, {"AETHER_PROJECT_ROOT": ""}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation()
            self.assertIn("AETHER_PROJECT_ROOT must not be empty", str(ctx.exception))

        with patch.dict(os.environ, {"AETHER_HERMES_ROOT": ""}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("AETHER_HERMES_ROOT must not be empty", str(ctx.exception))

        with patch.dict(os.environ, {"AETHER_RUNTIME_ROOT": ""}):
            with self.assertRaises(ActivationError) as ctx:
                inspect_activation(project=self.root)
            self.assertIn("AETHER_RUNTIME_ROOT must not be empty", str(ctx.exception))


class TuiPreservationTests(unittest.TestCase):
    """Preservation tests proving Aether launch surfaces deliver release-owned TUI (rc5/AC-5)."""

    _wheel_temp_dir: tempfile.TemporaryDirectory[str] | None = None
    _venv_dir: Path | None = None
    console_script: Path | None = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._wheel_temp_dir = tempfile.TemporaryDirectory(prefix="aether-tui-preserve-wheel-")
        wheel_out = Path(cls._wheel_temp_dir.name) / "dist"
        wheel_out.mkdir(parents=True)
        venv_path = Path(cls._wheel_temp_dir.name) / "venv"

        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(wheel_out)],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
        )
        wheels = sorted(wheel_out.glob("*.whl"))
        if not wheels:
            raise RuntimeError("No wheel produced by uv build")
        wheel = wheels[0]

        subprocess.run(
            ["uv", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )
        python_bin = venv_path / "bin" / "python"
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python_bin), str(wheel)],
            check=True,
            capture_output=True,
        )
        cls._venv_dir = venv_path
        cls.console_script = venv_path / "bin" / "aether"
        if not cls.console_script.is_file():
            raise RuntimeError(f"Console script not found at {cls.console_script}")

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._wheel_temp_dir is not None:
            cls._wheel_temp_dir.cleanup()

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-tui-preserve-")
        self.temp_path = Path(self.tempdir.name)
        self.data_dir = self.temp_path / "data"
        self.state_dir = self.temp_path / "state"

        # Set up isolated project
        self.project_dir = self.temp_path / "project"
        self.project_dir.mkdir(parents=True)
        (self.project_dir / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        (self.project_dir / ".aether").mkdir()
        self.project_id = "12027989-a08f-41cd-a82c-54ff1bfb6b03"
        (self.project_dir / ".aether" / "project.toml").write_text(
            "\n".join(
                (
                    "schema_version = 1",
                    f'project_id = "{self.project_id}"',
                    'name = "Aether launcher fixture"',
                    'initialized_by = "1.0.0"',
                    'forge = "local"',
                    'contract_root = "specs"',
                    'default_branch = "main"',
                    "",
                )
            ),
            encoding="utf-8",
        )

        # Register project in isolated registry
        registry = ProjectRegistry(root=self.state_dir / "aether")
        registry.register(
            self.project_id,
            self.project_dir,
            name="launcher-preserve-fixture",
        )

        # Set up Morfeo profile
        self.profile_dir = self.state_dir / "aether" / "hermes" / "profiles" / "morfeo"
        self.profile_dir.mkdir(parents=True)
        (self.profile_dir / "config.yaml").write_text(
            "toolsets:\n  - file\n  - kanban\n", encoding="utf-8"
        )
        (self.profile_dir / "SOUL.md").write_text("# Morfeo\n", encoding="utf-8")

        # Set up prepared release
        self.release_id = "1.0.0rc4-" + "b" * 16
        self.release_dir = self.data_dir / "aether" / "releases" / self.release_id
        self.tui_dir = self.release_dir / "tui"
        self.tui_dir.mkdir(parents=True)
        (self.tui_dir / "index.html").write_text("<html>TUI</html>", encoding="utf-8")
        (self.tui_dir / "dist").mkdir(parents=True)
        (self.tui_dir / "dist" / "entry.js").write_text(
            "console.log('tui-v1');\n", encoding="utf-8"
        )

        # Stub executable for Hermes
        self.venv_dir = self.release_dir / "venv"
        self.venv_bin = self.venv_dir / "bin"
        self.venv_bin.mkdir(parents=True)
        (self.venv_dir / "pyvenv.cfg").write_text(
            f"home = {sys.base_prefix}/bin\ninclude-system-site-packages = false\nversion = {sys.version.split()[0]}\n",
            encoding="utf-8",
        )
        self.hermes_stub = self.venv_bin / "hermes"
        self.hermes_stub.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "out = os.environ.get('AETHER_TEST_STUB_OUTPUT')\n"
            "if out:\n"
            "    data = {\n"
            "        'argv': sys.argv,\n"
            "        'cwd': os.getcwd(),\n"
            "        'environ': dict(os.environ),\n"
            "    }\n"
            "    with open(out, 'w', encoding='utf-8') as f:\n"
            "        json.dump(data, f)\n"
            "sys.exit(0)\n",
            encoding="utf-8",
        )
        self.hermes_stub.chmod(0o755)

        self.python_stub = self.venv_bin / "python"
        self.python_stub.symlink_to(sys.executable)

        # Locked hermes-source tree
        self.hermes_source_dir = self.release_dir / "hermes-source"
        self.hermes_source_dir.mkdir(parents=True)
        (self.hermes_source_dir / "package.json").write_text(
            json.dumps({"name": "hermes-tui", "version": "1.0.0"}, indent=2),
            encoding="utf-8",
        )
        (self.hermes_source_dir / "tsconfig.json").write_text(
            json.dumps({"compilerOptions": {"target": "es2022"}}, indent=2),
            encoding="utf-8",
        )
        (self.hermes_source_dir / "pyproject.toml").write_text(
            '[project]\nname = "hermes-agent"\nversion = "0.20.4"\n',
            encoding="utf-8",
        )
        (self.hermes_source_dir / "README.md").write_text(
            "# Hermes Locked Source\n", encoding="utf-8"
        )
        src_dir = self.hermes_source_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "index.ts").write_text("export const name = 'hermes';\n", encoding="utf-8")

        # Symlink runtime/current -> releases/<release_id>
        runtime_dir = self.data_dir / "aether" / "runtime"
        runtime_dir.mkdir(parents=True)
        self.runtime_current = runtime_dir / "current"
        self.runtime_current.symlink_to(f"../releases/{self.release_id}")

        self.expected_tui_dir = (self.runtime_current / "tui").resolve()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _assert_bound_target_python(self, bound_python: str | None) -> None:
        self.assertIsNotNone(bound_python)
        # 1. Must be the absolute lexical path within the target venv (not dereferenced to base interpreter)
        self.assertEqual(bound_python, str(self.python_stub))
        self.assertNotEqual(bound_python, str(self.python_stub.resolve()))
        # 2. Must execute and report sys.prefix and purelib inside the target release venv
        probe = subprocess.run(
            [
                str(bound_python),
                "-c",
                "import sys, sysconfig; print(sys.prefix); print(sysconfig.get_paths().get('purelib', ''))",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
        self.assertGreaterEqual(len(lines), 2)
        reported_prefix = Path(lines[0]).resolve()
        reported_purelib = Path(lines[1]).resolve()
        target_venv_res = self.venv_dir.resolve()
        self.assertEqual(reported_prefix, target_venv_res)
        self.assertTrue(reported_purelib.is_relative_to(target_venv_res))

    def _make_clean_env(self, stub_out_path: Path) -> dict[str, str]:
        env = dict(os.environ)
        for k in list(env.keys()):
            if (
                k.startswith("COV_CORE_")
                or k.startswith("COVERAGE_")
                or k.startswith("PYTHON")
                or k == "VIRTUAL_ENV"
                or k.startswith("HERMES_")
                or k.startswith("_HERMES_")
            ):
                env.pop(k, None)
        env["XDG_DATA_HOME"] = str(self.data_dir)
        env["XDG_STATE_HOME"] = str(self.state_dir)
        env["AETHER_TEST_STUB_OUTPUT"] = str(stub_out_path)
        env["CUSTOM_CREDENTIAL_KEY"] = "retained-secret"
        return env

    def _make_contaminated_env(self, stub_out_path: Path) -> dict[str, str]:
        env = self._make_clean_env(stub_out_path)
        # Inherited stale transport selectors and active-session transport paths
        env["HERMES_PYTHON"] = "/opt/stale-backend/venv/bin/python"
        env["HERMES_PYTHON_SRC_ROOT"] = "/opt/stale-backend/hermes-source"
        env["HERMES_TUI_GATEWAY_URL"] = "ws://127.0.0.1:9999"
        env["HERMES_TUI_SIDECAR_URL"] = "ws://127.0.0.1:9998"
        env["HERMES_TUI_ACTIVE_SESSION_FILE"] = "/tmp/stale-session.json"
        env["HERMES_RPC_SOCKET"] = "/tmp/stale-rpc.sock"
        env["HERMES_RPC_DIR"] = "/tmp/stale-rpc"
        env["HERMES_RPC_TOKEN"] = "stale-rpc-token"
        env["HERMES_SESSION_ID"] = "stale-session-123"
        env["HERMES_SESSION_KEY"] = "stale-session-key"
        env["HERMES_UI_SESSION_ID"] = "stale-ui-session-id"
        env["HERMES_CWD"] = "/tmp/stale-cwd"
        env["HERMES_BIN"] = "/tmp/stale-bin/hermes"
        env["VIRTUAL_ENV"] = "/opt/stale-backend/venv"
        env["_HERMES_GATEWAY"] = "1"
        env["HERMES_GATEWAY_SESSION"] = "stale-gw-session"
        env["HERMES_DESKTOP_READY_FILE"] = "/tmp/stale-desktop.ready"
        env["HERMES_PROFILE"] = "dirty-profile"
        env["PYTHONBREAKPOINT"] = "custom-breakpoint"
        env["PYTHONWARNINGS"] = "error"
        env["HERMES_TUI_DIR"] = "/tmp/stale-ambient-tui"
        env["HERMES_TUI_PORT"] = "9999"
        env["HERMES_KANBAN_TASK"] = "t_stale456"
        env["HERMES_KANBAN_DB"] = "/tmp/stale-kanban.db"
        env["HERMES_TASK_ID"] = "stale-task"
        env["HERMES_CRON_JOB"] = "stale-cron"
        return env

    def _make_env(self, stub_out_path: Path) -> dict[str, str]:
        return self._make_contaminated_env(stub_out_path)

    def _hermes_source_inventory(self) -> dict[str, tuple[str, str]]:
        """Compute regular-file type and sha256 inventory of locked hermes-source."""
        inv: dict[str, tuple[str, str]] = {}
        for root, _dirs, files in os.walk(self.hermes_source_dir):
            for filename in sorted(files):
                full_path = Path(root) / filename
                rel_path = str(full_path.relative_to(self.hermes_source_dir))
                if full_path.is_file() and not full_path.is_symlink():
                    sha = hashlib.sha256(full_path.read_bytes()).hexdigest()
                    inv[rel_path] = ("file", sha)
        return inv

    def test_real_packaged_launcher_executes_stub_hermes_fresh_and_resume_latest(
        self,
    ) -> None:
        """Prove packaged launcher exports HERMES_TUI_DIR to stub Hermes for fresh and resume."""
        stub_out_fresh = self.temp_path / "stub_fresh.json"
        env_fresh = self._make_env(stub_out_fresh)
        env_fresh["PYTHONPATH"] = str(ROOT / "src")

        # 1. Fresh launch
        res_fresh = subprocess.run(
            [
                sys.executable,
                "-m",
                "aether_agents.launcher",
                "--project",
                str(self.project_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env_fresh,
        )
        self.assertEqual(res_fresh.returncode, 0, res_fresh.stderr)
        self.assertTrue(stub_out_fresh.is_file())
        data_fresh = json.loads(stub_out_fresh.read_text(encoding="utf-8"))

        received_env = data_fresh["environ"]
        self.assertEqual(
            received_env.get("HERMES_TUI_DIR"),
            str(self.expected_tui_dir),
        )
        self.assertEqual(
            received_env.get("HERMES_HOME"),
            str(self.profile_dir.resolve()),
        )
        self.assertEqual(
            received_env.get("AETHER_PROJECT_ID"),
            self.project_id,
        )
        self.assertEqual(
            received_env.get("PWD"),
            str(self.project_dir.resolve()),
        )
        self.assertEqual(
            received_env.get("CUSTOM_CREDENTIAL_KEY"),
            "retained-secret",
        )
        self.assertNotIn("HERMES_PROFILE", received_env)
        self.assertNotIn("PYTHONBREAKPOINT", received_env)
        self.assertNotIn("PYTHONWARNINGS", received_env)
        self.assertFalse(any(k.startswith("PYTHON") for k in received_env))
        self.assertNotIn("HERMES_TUI_PORT", received_env)
        self.assertNotIn("HERMES_SESSION_ID", received_env)
        self.assertNotIn("HERMES_KANBAN_TASK", received_env)
        self.assertNotIn("HERMES_KANBAN_DB", received_env)
        self.assertNotIn("HERMES_TASK_ID", received_env)
        self.assertNotIn("HERMES_CRON_JOB", received_env)
        self._assert_bound_target_python(received_env.get("HERMES_PYTHON"))
        self.assertEqual(
            received_env.get("HERMES_PYTHON_SRC_ROOT"),
            str(self.hermes_source_dir.resolve()),
        )
        self.assertNotIn("HERMES_TUI_GATEWAY_URL", received_env)
        self.assertNotIn("HERMES_TUI_SIDECAR_URL", received_env)
        self.assertNotIn("HERMES_TUI_ACTIVE_SESSION_FILE", received_env)
        self.assertNotIn("HERMES_RPC_SOCKET", received_env)
        self.assertNotIn("HERMES_RPC_DIR", received_env)
        self.assertNotIn("HERMES_RPC_TOKEN", received_env)
        self.assertNotIn("HERMES_SESSION_KEY", received_env)
        self.assertNotIn("HERMES_UI_SESSION_ID", received_env)
        self.assertNotIn("HERMES_CWD", received_env)
        self.assertNotIn("HERMES_BIN", received_env)
        self.assertNotIn("VIRTUAL_ENV", received_env)
        self.assertNotIn("_HERMES_GATEWAY", received_env)
        self.assertNotIn("HERMES_GATEWAY_SESSION", received_env)
        self.assertNotIn("HERMES_DESKTOP_READY_FILE", received_env)
        self.assertEqual(data_fresh["cwd"], str(self.project_dir.resolve()))
        self.assertEqual(
            data_fresh["argv"],
            [
                str(self.hermes_stub.resolve()),
                "--tui",
                "--in",
                str(self.project_dir.resolve()),
            ],
        )

        # 2. Continuation launch (--resume latest)
        stub_out_resume = self.temp_path / "stub_resume.json"
        env_resume = self._make_env(stub_out_resume)
        env_resume["PYTHONPATH"] = str(ROOT / "src")

        res_resume = subprocess.run(
            [
                sys.executable,
                "-m",
                "aether_agents.launcher",
                "--project",
                str(self.project_dir),
                "--resume",
                "latest",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env_resume,
        )
        self.assertEqual(res_resume.returncode, 0, res_resume.stderr)
        self.assertTrue(stub_out_resume.is_file())
        data_resume = json.loads(stub_out_resume.read_text(encoding="utf-8"))
        self.assertEqual(
            data_resume["environ"].get("HERMES_TUI_DIR"),
            str(self.expected_tui_dir),
        )
        self.assertEqual(
            data_resume["argv"],
            [
                str(self.hermes_stub.resolve()),
                "--tui",
                "--in",
                str(self.project_dir.resolve()),
                "--resume",
                "latest",
            ],
        )

    def test_installed_wheel_console_script_lane_fresh_and_resume_latest(
        self,
    ) -> None:
        """Prove installed-wheel console script exports HERMES_TUI_DIR for fresh and resume."""
        self.assertIsNotNone(self.console_script)
        assert self.console_script is not None

        # 1. Fresh launch via installed console script
        stub_out_fresh = self.temp_path / "wheel_stub_fresh.json"
        env_fresh = self._make_env(stub_out_fresh)

        res_fresh = subprocess.run(
            [
                str(self.console_script),
                "--project",
                str(self.project_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env_fresh,
        )
        self.assertEqual(res_fresh.returncode, 0, res_fresh.stderr)
        self.assertTrue(stub_out_fresh.is_file())
        data_fresh = json.loads(stub_out_fresh.read_text(encoding="utf-8"))

        received_env = data_fresh["environ"]
        self.assertEqual(
            received_env.get("HERMES_TUI_DIR"),
            str(self.expected_tui_dir),
        )
        self.assertEqual(
            received_env.get("HERMES_HOME"),
            str(self.profile_dir.resolve()),
        )
        self.assertEqual(
            received_env.get("AETHER_PROJECT_ID"),
            self.project_id,
        )
        self.assertEqual(
            received_env.get("CUSTOM_CREDENTIAL_KEY"),
            "retained-secret",
        )
        self.assertNotIn("HERMES_PROFILE", received_env)
        self.assertNotIn("PYTHONBREAKPOINT", received_env)
        self.assertNotIn("PYTHONWARNINGS", received_env)
        self.assertFalse(any(k.startswith("PYTHON") for k in received_env))
        self._assert_bound_target_python(received_env.get("HERMES_PYTHON"))
        self.assertEqual(
            received_env.get("HERMES_PYTHON_SRC_ROOT"),
            str(self.hermes_source_dir.resolve()),
        )
        self.assertNotIn("HERMES_TUI_GATEWAY_URL", received_env)
        self.assertNotIn("HERMES_TUI_SIDECAR_URL", received_env)
        self.assertNotIn("HERMES_TUI_ACTIVE_SESSION_FILE", received_env)
        self.assertNotIn("HERMES_RPC_SOCKET", received_env)
        self.assertNotIn("HERMES_RPC_DIR", received_env)
        self.assertNotIn("HERMES_RPC_TOKEN", received_env)
        self.assertNotIn("HERMES_SESSION_KEY", received_env)
        self.assertNotIn("HERMES_UI_SESSION_ID", received_env)
        self.assertNotIn("HERMES_CWD", received_env)
        self.assertNotIn("HERMES_BIN", received_env)
        self.assertNotIn("VIRTUAL_ENV", received_env)
        self.assertNotIn("_HERMES_GATEWAY", received_env)
        self.assertNotIn("HERMES_GATEWAY_SESSION", received_env)
        self.assertNotIn("HERMES_DESKTOP_READY_FILE", received_env)
        self.assertEqual(data_fresh["cwd"], str(self.project_dir.resolve()))
        self.assertEqual(
            data_fresh["argv"],
            [
                str(self.hermes_stub.resolve()),
                "--tui",
                "--in",
                str(self.project_dir.resolve()),
            ],
        )

        # 2. Continuation launch via installed console script
        stub_out_resume = self.temp_path / "wheel_stub_resume.json"
        env_resume = self._make_env(stub_out_resume)

        res_resume = subprocess.run(
            [
                str(self.console_script),
                "--project",
                str(self.project_dir),
                "--resume",
                "latest",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env_resume,
        )
        self.assertEqual(res_resume.returncode, 0, res_resume.stderr)
        self.assertTrue(stub_out_resume.is_file())
        data_resume = json.loads(stub_out_resume.read_text(encoding="utf-8"))
        self.assertEqual(
            data_resume["environ"].get("HERMES_TUI_DIR"),
            str(self.expected_tui_dir),
        )
        self._assert_bound_target_python(data_resume["environ"].get("HERMES_PYTHON"))
        self.assertEqual(
            data_resume["environ"].get("HERMES_PYTHON_SRC_ROOT"),
            str(self.hermes_source_dir.resolve()),
        )
        self.assertNotIn("HERMES_RPC_SOCKET", data_resume["environ"])
        self.assertNotIn("HERMES_TUI_GATEWAY_URL", data_resume["environ"])
        self.assertNotIn("VIRTUAL_ENV", data_resume["environ"])
        self.assertEqual(
            data_resume["argv"],
            [
                str(self.hermes_stub.resolve()),
                "--tui",
                "--in",
                str(self.project_dir.resolve()),
                "--resume",
                "latest",
            ],
        )

    def test_aether_project_json_non_mutating_and_reports_release_identity(
        self,
    ) -> None:
        """Prove aether --project <root> --json is non-mutating and reports projection identity."""
        self.assertIsNotNone(self.console_script)
        assert self.console_script is not None

        def _full_snapshot() -> dict[str, tuple[str, int, str]]:
            snap: dict[str, tuple[str, int, str]] = {}
            for base in (self.project_dir, self.data_dir, self.state_dir):
                for root, _dirs, files in os.walk(base):
                    for fname in files:
                        p = Path(root) / fname
                        rel = str(p.relative_to(self.temp_path))
                        if p.is_file() and not p.is_symlink():
                            b = p.read_bytes()
                            snap[rel] = ("file", len(b), hashlib.sha256(b).hexdigest())
                        elif p.is_symlink():
                            snap[rel] = ("symlink", 0, os.readlink(p))
            return snap

        before_snapshot = _full_snapshot()
        env = self._make_env(self.temp_path / "unused.json")

        # Run via installed console script
        res = subprocess.run(
            [
                str(self.console_script),
                "--project",
                str(self.project_dir),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(res.returncode, 0, res.stderr)

        after_snapshot = _full_snapshot()
        self.assertEqual(
            before_snapshot,
            after_snapshot,
            "aether --project <root> --json modified filesystem state",
        )

        plan = json.loads(res.stdout)
        self.assertEqual(plan["result"], "ready")
        self.assertEqual(plan["project_id"], self.project_id)
        self.assertEqual(plan["repo_root"], str(self.project_dir.resolve()))
        self.assertEqual(plan["cwd"], str(self.project_dir.resolve()))
        self.assertEqual(plan["hermes_home"], str(self.profile_dir.resolve()))
        self.assertEqual(plan["tui_dir"], str(self.expected_tui_dir))
        self.assertEqual(plan["hermes_executable"], str(self.hermes_stub.resolve()))
        self.assertEqual(
            plan["command"],
            [
                str(self.hermes_stub.resolve()),
                "--tui",
                "--in",
                str(self.project_dir.resolve()),
            ],
        )

    def test_launch_creates_no_build_artefacts_and_leaves_locked_hermes_source_unchanged(
        self,
    ) -> None:
        """Prove launch creates no npm/build artefacts and hermes-source inventory is unchanged."""
        self.assertIsNotNone(self.console_script)
        assert self.console_script is not None

        pre_inventory = self._hermes_source_inventory()
        self.assertTrue(len(pre_inventory) >= 5, "Hermes source tree should have locked files")

        env = self._make_env(self.temp_path / "stub_launch.json")

        # 1. Fresh launch
        res1 = subprocess.run(
            [
                str(self.console_script),
                "--project",
                str(self.project_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(res1.returncode, 0, res1.stderr)

        # 2. Continuation launch
        res2 = subprocess.run(
            [
                str(self.console_script),
                "--project",
                str(self.project_dir),
                "--resume",
                "latest",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(res2.returncode, 0, res2.stderr)

        post_inventory = self._hermes_source_inventory()
        self.assertEqual(
            pre_inventory,
            post_inventory,
            "Launch modified the locked hermes-source tree",
        )

        # Assert no npm or build artifacts were created anywhere
        forbidden_patterns = (
            "node_modules",
            "package-lock.json",
            "*.tsbuildinfo",
            ".npm",
            ".turbo",
            "npm-debug.log*",
        )
        for base in (self.hermes_source_dir, self.release_dir, self.project_dir):
            for pat in forbidden_patterns:
                matches = list(base.glob(f"**/{pat}"))
                self.assertEqual(
                    matches,
                    [],
                    f"Unexpected build/npm artifact found matching {pat}: {matches}",
                )

    def test_desktop_and_wsl_projections_point_to_stable_aether_entry_point(
        self,
    ) -> None:
        """Prove Desktop and WSL projections target stable aether entry point and resume latest."""
        from aether_agents.lifecycle import (
            MAINTAINED_FORK_BRANCH,
            MAINTAINED_FORK_REPOSITORY,
            AetherPrebuildIdentity,
            AuthorityContext,
            DisabledServiceController,
            LifecycleManager,
            ProjectionRoots,
            ReleaseRecord,
            ReleaseStore,
        )

        store = ReleaseStore(
            root=self.data_dir / "aether",
            state_root=self.state_dir / "aether",
        )
        projections_root = self.temp_path / "projections"
        projections = ProjectionRoots.disposable(projections_root)

        manager = LifecycleManager(
            store=store,
            python_executable=Path(sys.executable),
            service_controller=DisabledServiceController(),
            projections=projections,
            project_root=self.project_dir,
        )

        identity = {
            "distribution": "aether-agents",
            "package_version": "1.0.0rc4",
            "git_tag": "v1.0.0-rc.4",
            "git_commit": "a" * 40,
            "python_requires": ">=3.11,<3.14",
            "observer": {
                "plugin_name": "aether-contract-observer",
                "group": "hermes_agent.plugins",
                "target": "aether_agents.observation.capture.hermes_plugin",
            },
        }
        record = ReleaseRecord(
            schema_version=3,
            release_id=self.release_id,
            version="1.0.0rc4",
            wheel_filename="aether_agents-1.0.0rc4-py3-none-any.whl",
            wheel_sha256="a" * 64,
            hermes_tag=MAINTAINED_FORK_BRANCH,
            hermes_commit="a" * 40,
            observer_entry_point="aether-contract-observer=aether_agents.observation.capture.hermes_plugin",
            previous_release_id=None,
            authority_context=AuthorityContext.for_active_release(self.release_id).to_record(),
            aether_identity=identity,
            prebuild_identity=AetherPrebuildIdentity.from_record(identity).digest,
            installed_file_fingerprint="e" * 64,
            hermes_repository=MAINTAINED_FORK_REPOSITORY,
            hermes_branch=MAINTAINED_FORK_BRANCH,
            hermes_source_tree_sha256="c" * 64,
            tui_sha256="d" * 64,
        )
        record.validate()

        # 1. With explicit project_root
        spec = manager.projection_spec(record, project_root=self.project_dir)

        # Linux Desktop entry assertions
        desktop_text = spec.desktop_bytes.decode("utf-8")
        expected_desktop_exec = (
            f"Exec={spec.runtime_current}/venv/bin/aether --project {self.project_dir.resolve()}"
        )
        self.assertIn(expected_desktop_exec, desktop_text)
        self.assertIn("Actions=Continue;", desktop_text)
        self.assertIn("[Desktop Action Continue]", desktop_text)
        self.assertIn("Name=Continue Aether", desktop_text)
        expected_desktop_continue = f"Exec={spec.runtime_current}/venv/bin/aether --project {self.project_dir.resolve()} --resume latest"
        self.assertIn(expected_desktop_continue, desktop_text)

        # WSL Windows Terminal shortcuts assertions
        self.assertIn("aether", spec.wsl_shortcuts)
        self.assertIn("continue_aether", spec.wsl_shortcuts)

        _aether_cmd_path, aether_cmd_bytes = spec.wsl_shortcuts["aether"]
        _continue_cmd_path, continue_cmd_bytes = spec.wsl_shortcuts["continue_aether"]

        aether_cmd_text = aether_cmd_bytes.decode("utf-8")
        continue_cmd_text = continue_cmd_bytes.decode("utf-8")

        self.assertIn("wt.exe", aether_cmd_text)
        self.assertIn("wsl.exe", aether_cmd_text)
        self.assertIn(
            f'"{spec.runtime_current}/venv/bin/aether" --project "{self.project_dir.resolve()}"',
            aether_cmd_text,
        )
        self.assertNotIn("--resume latest", aether_cmd_text)

        self.assertIn("wt.exe", continue_cmd_text)
        self.assertIn("wsl.exe", continue_cmd_text)
        self.assertIn(
            f'"{spec.runtime_current}/venv/bin/aether" --project "{self.project_dir.resolve()}" --resume latest',
            continue_cmd_text,
        )

        # 2. With default project resolution (via manager.project_root)
        spec_default = manager.projection_spec(record)
        self.assertEqual(spec.desktop_bytes, spec_default.desktop_bytes)
        self.assertEqual(
            spec.wsl_shortcuts["aether"][1],
            spec_default.wsl_shortcuts["aether"][1],
        )
        self.assertEqual(
            spec.wsl_shortcuts["continue_aether"][1],
            spec_default.wsl_shortcuts["continue_aether"][1],
        )

    def test_launch_scrubs_inherited_transport_and_binds_target_in_clean_and_contaminated_envs(
        self,
    ) -> None:
        """Prove packaged launch scrubs transport selectors and binds target identities in both clean and contaminated envs."""
        for env_kind, env_factory in [
            ("clean", self._make_clean_env),
            ("contaminated", self._make_contaminated_env),
        ]:
            with self.subTest(env=env_kind):
                # 1. Fresh launch
                stub_out_fresh = self.temp_path / f"stub_sub_{env_kind}_fresh.json"
                env_fresh = env_factory(stub_out_fresh)
                env_fresh["PYTHONPATH"] = str(ROOT / "src")

                res_fresh = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "aether_agents.launcher",
                        "--project",
                        str(self.project_dir),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env_fresh,
                )
                self.assertEqual(
                    res_fresh.returncode,
                    0,
                    f"{env_kind} fresh launch stderr: {res_fresh.stderr}",
                )
                self.assertTrue(stub_out_fresh.is_file())
                data_fresh = json.loads(stub_out_fresh.read_text(encoding="utf-8"))
                rec_fresh = data_fresh["environ"]

                # Assert resolved identities
                self._assert_bound_target_python(rec_fresh.get("HERMES_PYTHON"))
                self.assertEqual(
                    rec_fresh.get("HERMES_PYTHON_SRC_ROOT"),
                    str(self.hermes_source_dir.resolve()),
                )
                self.assertEqual(
                    rec_fresh.get("HERMES_TUI_DIR"),
                    str(self.expected_tui_dir),
                )
                self.assertEqual(
                    rec_fresh.get("HERMES_HOME"),
                    str(self.profile_dir.resolve()),
                )
                self.assertEqual(
                    rec_fresh.get("AETHER_PROJECT_ID"),
                    self.project_id,
                )
                self.assertEqual(
                    rec_fresh.get("PWD"),
                    str(self.project_dir.resolve()),
                )
                self.assertEqual(data_fresh["cwd"], str(self.project_dir.resolve()))
                self.assertEqual(
                    data_fresh["argv"],
                    [
                        str(self.hermes_stub.resolve()),
                        "--tui",
                        "--in",
                        str(self.project_dir.resolve()),
                    ],
                )
                self.assertEqual(rec_fresh.get("CUSTOM_CREDENTIAL_KEY"), "retained-secret")

                # Scrub assertions
                self.assertNotIn("HERMES_TUI_GATEWAY_URL", rec_fresh)
                self.assertNotIn("HERMES_TUI_SIDECAR_URL", rec_fresh)
                self.assertNotIn("HERMES_TUI_ACTIVE_SESSION_FILE", rec_fresh)
                self.assertNotIn("HERMES_RPC_SOCKET", rec_fresh)
                self.assertNotIn("HERMES_RPC_DIR", rec_fresh)
                self.assertNotIn("HERMES_RPC_TOKEN", rec_fresh)
                self.assertNotIn("HERMES_SESSION_ID", rec_fresh)
                self.assertNotIn("HERMES_SESSION_KEY", rec_fresh)
                self.assertNotIn("HERMES_UI_SESSION_ID", rec_fresh)
                self.assertNotIn("HERMES_CWD", rec_fresh)
                self.assertNotIn("HERMES_BIN", rec_fresh)
                self.assertNotIn("VIRTUAL_ENV", rec_fresh)
                self.assertNotIn("_HERMES_GATEWAY", rec_fresh)
                self.assertNotIn("HERMES_GATEWAY_SESSION", rec_fresh)
                self.assertNotIn("HERMES_DESKTOP_READY_FILE", rec_fresh)
                self.assertNotIn("HERMES_PROFILE", rec_fresh)
                self.assertFalse(any(k.startswith("PYTHON") for k in rec_fresh))

                # 2. Resume latest launch
                stub_out_resume = self.temp_path / f"stub_sub_{env_kind}_resume.json"
                env_resume = env_factory(stub_out_resume)
                env_resume["PYTHONPATH"] = str(ROOT / "src")

                res_resume = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "aether_agents.launcher",
                        "--project",
                        str(self.project_dir),
                        "--resume",
                        "latest",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env_resume,
                )
                self.assertEqual(
                    res_resume.returncode,
                    0,
                    f"{env_kind} resume launch stderr: {res_resume.stderr}",
                )
                self.assertTrue(stub_out_resume.is_file())
                data_resume = json.loads(stub_out_resume.read_text(encoding="utf-8"))
                rec_resume = data_resume["environ"]

                self._assert_bound_target_python(rec_resume.get("HERMES_PYTHON"))
                self.assertEqual(
                    rec_resume.get("HERMES_PYTHON_SRC_ROOT"),
                    str(self.hermes_source_dir.resolve()),
                )
                self.assertEqual(
                    rec_resume.get("HERMES_TUI_DIR"),
                    str(self.expected_tui_dir),
                )
                self.assertEqual(
                    rec_resume.get("HERMES_HOME"),
                    str(self.profile_dir.resolve()),
                )
                self.assertEqual(
                    rec_resume.get("AETHER_PROJECT_ID"),
                    self.project_id,
                )
                self.assertEqual(
                    rec_resume.get("PWD"),
                    str(self.project_dir.resolve()),
                )
                self.assertEqual(
                    data_resume["argv"],
                    [
                        str(self.hermes_stub.resolve()),
                        "--tui",
                        "--in",
                        str(self.project_dir.resolve()),
                        "--resume",
                        "latest",
                    ],
                )

    def test_bare_aether_launch_in_project_cwd_clean_and_contaminated(
        self,
    ) -> None:
        """Prove bare aether (without --project) inside project cwd works in clean and contaminated envs."""
        for env_kind, env_factory in [
            ("clean", self._make_clean_env),
            ("contaminated", self._make_contaminated_env),
        ]:
            with self.subTest(env=env_kind):
                stub_out = self.temp_path / f"stub_bare_{env_kind}.json"
                env = env_factory(stub_out)
                env["PYTHONPATH"] = str(ROOT / "src")

                res = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "aether_agents.launcher",
                    ],
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env,
                )
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertTrue(stub_out.is_file())
                data = json.loads(stub_out.read_text(encoding="utf-8"))
                rec = data["environ"]

                self._assert_bound_target_python(rec.get("HERMES_PYTHON"))
                self.assertEqual(
                    rec.get("HERMES_PYTHON_SRC_ROOT"),
                    str(self.hermes_source_dir.resolve()),
                )
                self.assertEqual(rec.get("HERMES_TUI_DIR"), str(self.expected_tui_dir))
                self.assertEqual(rec.get("HERMES_HOME"), str(self.profile_dir.resolve()))
                self.assertEqual(rec.get("AETHER_PROJECT_ID"), self.project_id)
                self.assertEqual(rec.get("PWD"), str(self.project_dir.resolve()))
                self.assertEqual(data["cwd"], str(self.project_dir.resolve()))
                self.assertNotIn("HERMES_RPC_SOCKET", rec)
                self.assertNotIn("HERMES_TUI_GATEWAY_URL", rec)
                self.assertNotIn("VIRTUAL_ENV", rec)

    def test_regression_contaminated_parent_cannot_select_old_backend(
        self,
    ) -> None:
        """Reproduction oracle: contaminated parent env cannot select old backend or stale transport."""
        stub_out = self.temp_path / "stub_reproduction.json"
        env = self._make_contaminated_env(stub_out)
        env["PYTHONPATH"] = str(ROOT / "src")

        old_backend_python = "/opt/stale-backend/venv/bin/python"
        old_backend_source = "/opt/stale-backend/hermes-source"
        old_rpc_socket = "/tmp/stale-rpc.sock"
        old_gateway_url = "ws://127.0.0.1:9999"

        self.assertEqual(env["HERMES_PYTHON"], old_backend_python)
        self.assertEqual(env["HERMES_PYTHON_SRC_ROOT"], old_backend_source)
        self.assertEqual(env["HERMES_RPC_SOCKET"], old_rpc_socket)
        self.assertEqual(env["HERMES_TUI_GATEWAY_URL"], old_gateway_url)

        res = subprocess.run(
            [
                sys.executable,
                "-m",
                "aether_agents.launcher",
                "--project",
                str(self.project_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(stub_out.is_file())
        data = json.loads(stub_out.read_text(encoding="utf-8"))
        rec = data["environ"]

        # Crucial reproduction assertion: child NEVER inherits old backend python or source
        self.assertNotEqual(rec.get("HERMES_PYTHON"), old_backend_python)
        self.assertNotEqual(rec.get("HERMES_PYTHON_SRC_ROOT"), old_backend_source)
        self._assert_bound_target_python(rec.get("HERMES_PYTHON"))
        self.assertEqual(rec.get("HERMES_PYTHON_SRC_ROOT"), str(self.hermes_source_dir.resolve()))
        self.assertNotIn("HERMES_RPC_SOCKET", rec)
        self.assertNotIn("HERMES_TUI_GATEWAY_URL", rec)
        self.assertNotIn("VIRTUAL_ENV", rec)

    def test_target_python_supports_regular_file_executable_stub_secondary_case(self) -> None:
        """Secondary case: regular-file executable stub inside release venv is accepted if probe passes."""
        from aether_agents.launcher import _resolve_target_python

        temp_dir = self.temp_path / "secondary_release"
        venv_dir = temp_dir / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        hermes_file = venv_bin / "hermes"
        hermes_file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes_file.chmod(0o755)

        stub_py = venv_bin / "python"
        stub_script = (
            f"#!{sys.executable}\n"
            "import sys\n"
            "from pathlib import Path\n"
            "if '-c' in sys.argv:\n"
            "    v = Path(__file__).resolve().parent.parent\n"
            "    print(v)\n"
            "    print(v / 'lib' / 'python3.13' / 'site-packages')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )
        stub_py.write_text(stub_script, encoding="utf-8")
        stub_py.chmod(0o755)

        self.assertFalse(stub_py.is_symlink())
        resolved = _resolve_target_python(hermes_file)
        self.assertEqual(resolved, stub_py)

    def test_target_python_rejects_foreign_or_failing_interpreter(self) -> None:
        """Foreign interpreter or failing probe must raise ActivationError and never bind silently."""
        from aether_agents.launcher import ActivationError, _resolve_target_python

        temp_dir = self.temp_path / "foreign_release"
        venv_dir = temp_dir / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        hermes_file = venv_bin / "hermes"
        hermes_file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes_file.chmod(0o755)

        stub_py = venv_bin / "python"
        # 1. Foreign interpreter that reports sys.prefix outside target venv
        foreign_script = (
            f"#!{sys.executable}\n"
            "import sys\n"
            "if '-c' in sys.argv:\n"
            "    print('/opt/foreign-prefix')\n"
            "    print('/opt/foreign-prefix/lib/site-packages')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )
        stub_py.write_text(foreign_script, encoding="utf-8")
        stub_py.chmod(0o755)

        with self.assertRaises(ActivationError) as ctx:
            _resolve_target_python(hermes_file)
        self.assertIn("could not be verified inside target venv", str(ctx.exception))

        # 2. Non-executable candidate
        stub_py.chmod(0o644)
        with self.assertRaises(ActivationError) as ctx:
            _resolve_target_python(hermes_file)
        self.assertIn("could not be verified inside target venv", str(ctx.exception))

        # 3. Probe failure / exit 1
        failing_script = f"#!{sys.executable}\nimport sys\nsys.exit(1)\n"
        stub_py.write_text(failing_script, encoding="utf-8")
        stub_py.chmod(0o755)
        with self.assertRaises(ActivationError) as ctx:
            _resolve_target_python(hermes_file)
        self.assertIn("could not be verified inside target venv", str(ctx.exception))

    def test_target_python_probe_isolated_from_project_local_imports(self) -> None:
        """Probe verdict must be invariant to project-local sysconfig/sitecustomize in cwd."""
        from aether_agents.launcher import (
            ActivationError,
            _probe_venv_interpreter,
            _resolve_target_python,
        )

        poison_dir = self.temp_path / "poisoned_project"
        poison_dir.mkdir(parents=True)

        target_dir = self.temp_path / "foreign_target"
        target_venv = target_dir / "venv"
        target_bin = target_venv / "bin"
        target_bin.mkdir(parents=True)
        hermes_file = target_bin / "hermes"
        hermes_file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes_file.chmod(0o755)

        # Foreign interpreter symlinked to base sys.executable with NO pyvenv.cfg
        foreign_py = target_bin / "python"
        foreign_py.symlink_to(sys.executable)

        # Write poisoned sysconfig.py and sitecustomize.py in poison_dir that attempt to spoof the target venv
        (poison_dir / "sysconfig.py").write_text(
            f"import sys\n"
            f"sys.prefix = '{target_venv}'\n"
            f"def get_paths():\n"
            f"    return {{'purelib': '{target_venv}/lib/python3.13/site-packages'}}\n",
            encoding="utf-8",
        )
        (poison_dir / "sitecustomize.py").write_text(
            f"import sys\nsys.prefix = '{target_venv}'\n",
            encoding="utf-8",
        )

        orig_cwd = os.getcwd()
        try:
            os.chdir(poison_dir)
            # 1. Foreign interpreter must be rejected despite poisoned cwd
            self.assertFalse(_probe_venv_interpreter(foreign_py, [target_venv]))
            with self.assertRaises(ActivationError):
                _resolve_target_python(hermes_file)

            # 2. Legitimate venv must pass even from poisoned cwd
            valid_dir = self.temp_path / "valid_release"
            valid_venv = valid_dir / "venv"
            valid_bin = valid_venv / "bin"
            valid_bin.mkdir(parents=True)
            (valid_venv / "pyvenv.cfg").write_text(
                f"home = {sys.base_prefix}/bin\ninclude-system-site-packages = false\nversion = {sys.version.split()[0]}\n",
                encoding="utf-8",
            )
            valid_hermes = valid_bin / "hermes"
            valid_hermes.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            valid_hermes.chmod(0o755)
            valid_py = valid_bin / "python"
            valid_py.symlink_to(sys.executable)

            resolved = _resolve_target_python(valid_hermes)
            self.assertEqual(resolved, valid_py)
            self.assertTrue(_probe_venv_interpreter(valid_py, [valid_venv]))
        finally:
            os.chdir(orig_cwd)

    def test_target_python_rejects_cross_release_fallback_via_ambient_root(self) -> None:
        """A launcher run from another release's venv must not bind that release's interpreter.

        Exercises the ``sys.executable`` fallback branch with the ambient release's interpreter as
        the running one (``sys.executable`` patched to it), which is exactly the observed
        cross-release fallback path. The ambient interpreter is a usable venv interpreter (positive
        control below), so failing closed here is attributable to accepted venvs being derived from
        the selected target alone, not to a broken probe.
        """
        from aether_agents.launcher import (
            ActivationError,
            _probe_venv_interpreter,
            _resolve_target_python,
        )

        # Ambient release in XDG_DATA_HOME
        data_home = self.temp_path / "fake_xdg_data"
        ambient_venv = data_home / "aether" / "runtime" / "releases" / "other-1.0.0rc5" / "venv"
        ambient_bin = ambient_venv / "bin"
        ambient_bin.mkdir(parents=True)
        (ambient_venv / "pyvenv.cfg").write_text(
            f"home = {sys.base_prefix}/bin\ninclude-system-site-packages = false\nversion = {sys.version.split()[0]}\n",
            encoding="utf-8",
        )
        ambient_python = ambient_bin / "python"
        ambient_python.symlink_to(sys.executable)
        current_dir = data_home / "aether" / "runtime" / "current"
        current_dir.mkdir(parents=True)
        (current_dir / "venv").symlink_to(ambient_venv)

        # Selected target store with hermes but NO python
        selected_dir = self.temp_path / "selected_store"
        selected_venv = selected_dir / "venv"
        selected_bin = selected_venv / "bin"
        selected_bin.mkdir(parents=True)
        selected_hermes = selected_bin / "hermes"
        selected_hermes.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        selected_hermes.chmod(0o755)

        # Positive control: the ambient interpreter verifies inside its own venv, so the assertion
        # below cannot pass merely because the ambient release is unusable.
        self.assertTrue(_probe_venv_interpreter(ambient_python, [ambient_venv]))

        old_xdg = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = str(data_home)
        try:
            # The launcher process itself runs from the ambient release venv (defect setup).
            with patch.object(sys, "executable", str(ambient_python)):
                with self.assertRaises(ActivationError) as ctx:
                    _resolve_target_python(selected_hermes)
            self.assertIn("could not be verified inside target venv", str(ctx.exception))
        finally:
            if old_xdg is not None:
                os.environ["XDG_DATA_HOME"] = old_xdg
            else:
                os.environ.pop("XDG_DATA_HOME", None)

    def test_target_python_rejects_split_corroboration_across_independent_roots(self) -> None:
        """Probe and resolver must reject an interpreter reporting prefix in root A and purelib in root B."""
        from aether_agents.launcher import (
            ActivationError,
            _probe_venv_interpreter,
            _resolve_target_python,
        )

        root_a = self.temp_path / "split_root_a" / "venv"
        root_b = self.temp_path / "split_root_b" / "venv"
        root_a_bin = root_a / "bin"
        root_a_bin.mkdir(parents=True)
        root_b.mkdir(parents=True)

        hermes_file = root_a_bin / "hermes"
        hermes_file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes_file.chmod(0o755)

        stub_py = root_a_bin / "python"
        # Split script: prefix in root_a, purelib in root_b
        split_script = (
            f"#!{sys.executable}\n"
            "import sys\n"
            "if '-c' in sys.argv:\n"
            f"    print('{root_a}')\n"
            f"    print('{root_b}/lib/python3.13/site-packages')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )
        stub_py.write_text(split_script, encoding="utf-8")
        stub_py.chmod(0o755)

        # Both roots present in target_venvs, but neither contains both prefix and purelib
        self.assertFalse(_probe_venv_interpreter(stub_py, [root_a, root_b]))
        with self.assertRaises(ActivationError) as ctx:
            _resolve_target_python(hermes_file)
        self.assertIn("could not be verified inside target venv", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
