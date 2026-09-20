"""Regression and unit tests for the packaged Morfeo TUI launcher (LG-CLI / #480)."""

from __future__ import annotations

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

from aether_agents.cli import main as cli_main
from aether_agents.observation.context import ProjectRegistry

ROOT = Path(__file__).resolve().parents[1]
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
        hermes = self.root / "home" / ".venv-hermes" / "bin" / "hermes"
        hermes.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hermes.chmod(0o755)
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

    def run_check(
        self, cwd: Path, *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        merged = dict(os.environ)
        for k in list(merged.keys()):
            if k.startswith("COV_CORE_") or k.startswith("COVERAGE_"):
                merged.pop(k, None)
        if env is not None:
            merged.update(env)
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
                sub_env = dict(os.environ)
                for k in list(sub_env.keys()):
                    if k.startswith("COV_CORE_") or k.startswith("COVERAGE_"):
                        sub_env.pop(k, None)
                result = subprocess.run(
                    [sys.executable, str(self.launcher), "--check", argument],
                    cwd=self.root,
                    text=True,
                    capture_output=True,
                    check=False,
                    env=sub_env,
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

        with self.assertRaises(ActivationError) as ctx:
            inspect_activation(project=Path(""))
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


if __name__ == "__main__":
    unittest.main()
