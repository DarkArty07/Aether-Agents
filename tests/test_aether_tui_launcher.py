"""Regression tests for the reproducible Morfeo TUI launcher (#187)."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "aether_tui.py"


class MorfeoTuiLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-tui-launcher-")
        self.root = Path(self.tempdir.name) / "aether"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "home" / "profiles" / "morfeo").mkdir(parents=True)
        (self.root / "home" / ".venv-hermes" / "bin").mkdir(parents=True)
        (self.root / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        marker = self.root / ".aether" / "project.toml"
        marker.parent.mkdir(parents=True)
        marker.write_text(
            'project_id = "12027989-a08f-41cd-a82c-54ff1bfb6b03"\n',
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

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_check(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.launcher), "--check"],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
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

    def test_launch_executes_canonical_command_with_clean_python_env(self) -> None:
        module = self.load_module()
        dirty_env = {
            "PATH": os.environ.get("PATH", ""),
            "PWD": "/tmp/caller-directory",
            "HERMES_PROFILE": "wrong-profile",
            "PYTHONPATH": "/tmp/stale-pythonpath",
            "PYTHONHOME": "/tmp/stale-pythonhome",
            "KEEP_ME": "yes",
        }
        expected_root = self.root.resolve()
        expected_home = (self.root / "home" / "profiles" / "morfeo").resolve()
        expected_hermes = (self.root / "home" / ".venv-hermes" / "bin" / "hermes").resolve()

        with (
            patch.object(module.os, "environ", dirty_env),
            patch.object(module.os, "chdir") as chdir,
            patch.object(
                module.os, "execve", side_effect=RuntimeError("exec intercepted")
            ) as execve,
            self.assertRaisesRegex(RuntimeError, "exec intercepted"),
        ):
            module.main(["--resume", "latest"])

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
        self.assertEqual(called_env["KEEP_ME"], "yes")
        self.assertNotIn("HERMES_PROFILE", called_env)
        self.assertNotIn("PYTHONPATH", called_env)
        self.assertNotIn("PYTHONHOME", called_env)

    def test_check_rejects_missing_or_invalid_project_marker(self) -> None:
        marker = self.root / ".aether" / "project.toml"
        marker.unlink()
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("portable Aether project marker", result.stderr)

        marker.write_text('project_id = "not-a-uuid"\n', encoding="utf-8")
        result = self.run_check(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("valid project_id", result.stderr)

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
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(
                    "is controlled by the canonical Morfeo launcher",
                    result.stderr,
                )

    def test_versioned_launcher_contains_no_machine_specific_home(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"/home/[A-Za-z0-9._-]+/", source))
        self.assertEqual(stat.S_IMODE(LAUNCHER.stat().st_mode), 0o755)


if __name__ == "__main__":
    unittest.main()
