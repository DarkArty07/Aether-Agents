"""Regression tests for Aether's versioned policy-hook source and sync tool."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "policy" / "hooks" / "aether_pre_tool_policy.py"
SYNC = ROOT / "scripts" / "sync_policy_hooks.py"
PROFILES = ("morfeo", "supervisor", "implementer")


class PolicyHookSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-policy-hooks-")
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        self.backup = self.root / "backup"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_sync(self, action: str, *, check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SYNC),
                action,
                "--home",
                str(self.home),
                "--backup-dir",
                str(self.backup),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=check,
        )

    def target(self, profile: str) -> Path:
        return self.home / "profiles" / profile / "hooks" / CANONICAL.name

    def test_clean_home_can_install_check_and_restore(self) -> None:
        result = self.run_sync("install", check=True)
        report = json.loads(result.stdout)
        expected_hash = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
        self.assertEqual(report["canonical_sha256"], expected_hash)
        self.assertEqual(report["result"], "installed")

        for profile in PROFILES:
            target = self.target(profile)
            self.assertEqual(target.read_bytes(), CANONICAL.read_bytes())
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)

        checked = self.run_sync("check", check=True)
        check_report = json.loads(checked.stdout)
        self.assertEqual(check_report["result"], "in_sync")
        self.assertTrue(all(item["in_sync"] for item in check_report["profiles"]))

        restored = self.run_sync("restore", check=True)
        self.assertEqual(json.loads(restored.stdout)["result"], "restored")
        self.assertTrue(all(not self.target(profile).exists() for profile in PROFILES))

    def test_install_and_restore_preserve_previous_bytes_and_modes(self) -> None:
        previous: dict[str, tuple[bytes, int]] = {}
        for index, profile in enumerate(PROFILES):
            target = self.target(profile)
            target.parent.mkdir(parents=True, exist_ok=True)
            content = f"old-{profile}\n".encode()
            mode = 0o700 + index
            target.write_bytes(content)
            target.chmod(mode)
            previous[profile] = (content, mode)

        self.run_sync("install", check=True)
        manifest = json.loads((self.backup / "manifest.json").read_text())
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(set(manifest["profiles"]), set(PROFILES))
        self.run_sync("restore", check=True)

        for profile, (content, mode) in previous.items():
            target = self.target(profile)
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode)

    def test_check_detects_drift_and_restore_refuses_to_overwrite_it(self) -> None:
        self.run_sync("install", check=True)
        drifted = self.target("implementer")
        drifted.write_text("local change\n", encoding="utf-8")

        checked = self.run_sync("check")
        self.assertEqual(checked.returncode, 1)
        report = json.loads(checked.stdout)
        self.assertEqual(report["result"], "drift")
        by_profile = {item["profile"]: item for item in report["profiles"]}
        self.assertFalse(by_profile["implementer"]["in_sync"])

        before = {profile: self.target(profile).read_bytes() for profile in PROFILES}
        restored = self.run_sync("restore")
        self.assertEqual(restored.returncode, 2)
        after = {profile: self.target(profile).read_bytes() for profile in PROFILES}
        self.assertEqual(after, before)

    def test_restore_refuses_to_overwrite_mode_drift(self) -> None:
        self.run_sync("install", check=True)
        drifted = self.target("supervisor")
        drifted.chmod(0o700)

        checked = self.run_sync("check")
        self.assertEqual(checked.returncode, 1)
        restored = self.run_sync("restore")
        self.assertEqual(restored.returncode, 2)
        self.assertEqual(stat.S_IMODE(drifted.stat().st_mode), 0o700)

    def test_install_changes_only_hook_targets_and_backup(self) -> None:
        sentinel = self.home / "profiles" / "morfeo" / "config.yaml"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_bytes(b"model: unchanged\n")
        before = sentinel.read_bytes()

        self.run_sync("install", check=True)

        self.assertEqual(sentinel.read_bytes(), before)
        non_hook_files = {
            path.relative_to(self.home).as_posix()
            for path in self.home.rglob("*")
            if path.is_file() and path.name != CANONICAL.name
        }
        self.assertEqual(non_hook_files, {"profiles/morfeo/config.yaml"})

    def test_sync_tool_has_no_process_network_or_service_activation_surface(self) -> None:
        source = SYNC.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (
                node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")]
            )
        }
        self.assertTrue({"subprocess", "socket", "requests", "urllib"}.isdisjoint(imports))
        self.assertNotIn("systemctl", source)
        self.assertNotIn("gateway run", source)

    def test_versioned_sources_contain_no_secret_material_or_machine_home(self) -> None:
        secret_patterns = [
            rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            rb"\bgh[opsu]_[A-Za-z0-9]{20,}\b",
            rb"\bsk-[A-Za-z0-9]{20,}\b",
            rb"/home/[A-Za-z0-9._-]+/",
        ]
        for path in (CANONICAL, SYNC, Path(__file__)):
            data = path.read_bytes()
            for pattern in secret_patterns:
                self.assertIsNone(re.search(pattern, data), f"secret-like material in {path}")


class ImplementerPolicyRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-policy-runtime-")
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        self.backup = self.root / "backup"
        subprocess.run(
            [
                sys.executable,
                str(SYNC),
                "install",
                "--home",
                str(self.home),
                "--backup-dir",
                str(self.backup),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.hook = self.home / "profiles" / "implementer" / "hooks" / CANONICAL.name
        self.repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", "-b", "wt/test", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Aether test"],
            check=True,
        )
        (self.repo / "seed").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "seed"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", "seed"],
            check=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_hook(
        self,
        command: str,
        *,
        workspace: str | None = None,
        branch: str | None = "wt/test",
    ) -> subprocess.CompletedProcess[str]:
        payload = {
            "hook_event_name": "pre_tool_call",
            "tool_name": "terminal",
            "tool_input": {"command": command, "workdir": str(self.repo)},
            "extra": {},
            "cwd": str(self.repo),
        }
        env = os.environ.copy()
        if workspace == "":
            env.pop("HERMES_KANBAN_WORKSPACE", None)
        else:
            env["HERMES_KANBAN_WORKSPACE"] = workspace or str(self.repo)
        if branch is None:
            env.pop("HERMES_KANBAN_BRANCH", None)
        else:
            env["HERMES_KANBAN_BRANCH"] = branch
        return subprocess.run(
            [sys.executable, str(self.hook)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_read_only_branch_inspection_remains_allowed(self) -> None:
        commands = [
            "git branch --show-current",
            "pwd; git branch --show-current; git status --short --untracked-files=all",
            "git branch --show-current && git status --short",
        ]
        for command in commands:
            with self.subTest(command=command):
                result = self.run_hook(command)
                self.assertEqual(result.returncode, 0, result.stdout or result.stderr)

    def test_branch_and_history_mutations_remain_denied(self) -> None:
        commands = [
            "git branch topic",
            "git branch -d old",
            "git branch -m renamed",
            "git branch --set-upstream-to=origin/main",
            "git branch --show-current --delete old",
            "git branch --delete old --show-current",
            "git checkout main",
            "git switch main",
            "git worktree add /tmp/x topic",
            "git merge main",
            "git cherry-pick HEAD~1",
            "git revert HEAD",
            "git tag v1",
            "git reset --hard HEAD",
            "git push origin HEAD",
            "git pull",
            "git rebase main",
            "git commit --amend --no-edit",
            "git branch --show-current && git checkout main",
            'echo "$(git branch --show-current)"',
            "git branch --show-current | sh",
            "git branch --show-current\ngit status --short",
        ]
        for command in commands:
            with self.subTest(command=command):
                result = self.run_hook(command)
                self.assertEqual(result.returncode, 2)
                reason = json.loads(result.stdout)["reason"]
                self.assertTrue(reason.startswith("AETHER-IMPLEMENTER-BRANCH-HISTORY:"))

    def test_binding_guards_remain_fail_closed(self) -> None:
        cases = [("", None), (None, "wt/other")]
        for workspace, branch in cases:
            with self.subTest(workspace=workspace, branch=branch):
                result = self.run_hook(
                    "git branch --show-current", workspace=workspace, branch=branch
                )
                self.assertEqual(result.returncode, 2)
                reason = json.loads(result.stdout)["reason"]
                self.assertTrue(reason.startswith("AETHER-IMPLEMENTER-UNDECIDABLE:"))


class MorfeoTaskBoundPolicyRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-policy-morfeo-")
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        subprocess.run(
            [
                sys.executable,
                str(SYNC),
                "install",
                "--home",
                str(self.home),
                "--backup-dir",
                str(self.root / "backup"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.hook = self.home / "profiles" / "morfeo" / "hooks" / CANONICAL.name
        self.repo = self.root / "repo"
        self.workspace = self.root / "worktree"
        self.branch = "wt/t_morfeo"
        self.task_id = "t_morfeo"
        self.run_id = 7
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Aether test"],
            check=True,
        )
        contract = self.repo / "specs" / "example" / "spec.md"
        contract.parent.mkdir(parents=True)
        contract.write_text("# Baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", "seed"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "worktree",
                "add",
                "-q",
                "-b",
                self.branch,
                str(self.workspace),
            ],
            check=True,
        )
        self.board = self.root / "kanban.db"
        with sqlite3.connect(self.board) as conn:
            conn.executescript(
                """
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    assignee TEXT,
                    status TEXT,
                    workspace_kind TEXT,
                    workspace_path TEXT,
                    branch_name TEXT,
                    current_run_id INTEGER
                );
                CREATE TABLE task_runs (
                    id INTEGER PRIMARY KEY,
                    task_id TEXT,
                    profile TEXT,
                    status TEXT
                );
                """
            )
            conn.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.task_id,
                    "morfeo",
                    "running",
                    "worktree",
                    str(self.workspace),
                    self.branch,
                    self.run_id,
                ),
            )
            conn.execute(
                "INSERT INTO task_runs VALUES (?, ?, ?, ?)",
                (self.run_id, self.task_id, "morfeo", "running"),
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_hook(
        self,
        *,
        env_updates: Mapping[str, str | None] | None = None,
        path: str | None = None,
        cwd: Path | None = None,
        tool_name: str = "write_file",
        tool_input: Mapping[str, object] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if tool_input is None:
            tool_input = {
                "path": path or str(self.workspace / "specs" / "example" / "spec.md"),
                "content": "# Reconciled\n",
            }
        payload = {
            "hook_event_name": "pre_tool_call",
            "tool_name": tool_name,
            "tool_input": dict(tool_input),
            # Hermes uses this hook field for its conversation/session task id;
            # the durable Kanban identity is HERMES_KANBAN_TASK.
            "extra": {"task_id": "session-123"},
            "cwd": str(cwd or self.workspace),
        }
        env = os.environ.copy()
        env.update(
            {
                "AETHER_INTEGRATION_BRANCH": "main",
                "HERMES_KANBAN_DB": str(self.board),
                "HERMES_KANBAN_TASK": self.task_id,
                "HERMES_KANBAN_RUN_ID": str(self.run_id),
                "HERMES_KANBAN_WORKSPACE": str(self.workspace),
                "HERMES_KANBAN_BRANCH": self.branch,
            }
        )
        for key, value in (env_updates or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            [sys.executable, str(self.hook)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_exact_task_bound_morfeo_contract_write_is_allowed(self) -> None:
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stdout or result.stderr)

    def test_task_bound_write_without_run_identity_is_denied(self) -> None:
        result = self.run_hook(env_updates={"HERMES_KANBAN_RUN_ID": None})
        self.assertEqual(result.returncode, 2)
        self.assertIn("run binding is unavailable", json.loads(result.stdout)["reason"])

    def test_task_bound_write_requires_explicit_board_pin(self) -> None:
        result = self.run_hook(env_updates={"HERMES_KANBAN_DB": None})
        self.assertEqual(result.returncode, 2)
        self.assertIn("board path is unavailable", json.loads(result.stdout)["reason"])

    def test_task_bound_write_for_non_morfeo_assignment_is_denied(self) -> None:
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE tasks SET assignee = 'supervisor' WHERE id = ?", (self.task_id,))
        result = self.run_hook()
        self.assertEqual(result.returncode, 2)
        self.assertIn("task is not assigned to Morfeo", json.loads(result.stdout)["reason"])

    def test_task_bound_write_with_stale_run_is_denied(self) -> None:
        result = self.run_hook(env_updates={"HERMES_KANBAN_RUN_ID": "8"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("board run does not match", json.loads(result.stdout)["reason"])

    def test_task_bound_write_rejects_run_owned_by_another_task(self) -> None:
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE task_runs SET task_id = 't_other' WHERE id = ?", (self.run_id,))
        result = self.run_hook()
        self.assertEqual(result.returncode, 2)
        self.assertIn("active task run does not belong", json.loads(result.stdout)["reason"])

    def test_task_bound_write_rejects_missing_board_workspace(self) -> None:
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE tasks SET workspace_path = NULL WHERE id = ?", (self.task_id,))
        result = self.run_hook()
        self.assertEqual(result.returncode, 2)
        self.assertIn("board workspace is unavailable", json.loads(result.stdout)["reason"])

    def test_task_bound_write_requires_worktree_workspace_kind(self) -> None:
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE tasks SET workspace_kind = 'dir' WHERE id = ?", (self.task_id,))
        result = self.run_hook()
        self.assertEqual(result.returncode, 2)
        self.assertIn("not an isolated worktree", json.loads(result.stdout)["reason"])

    def test_task_bound_write_on_different_branch_is_denied(self) -> None:
        result = self.run_hook(env_updates={"HERMES_KANBAN_BRANCH": "wt/other"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("current branch does not match", json.loads(result.stdout)["reason"])

    def test_task_bound_write_outside_workspace_is_denied(self) -> None:
        result = self.run_hook(path=str(self.root / "outside.md"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the authorized workspace", json.loads(result.stdout)["reason"])

    def test_task_bound_relative_write_is_denied_even_if_payload_cwd_is_inside(self) -> None:
        result = self.run_hook(path="relative-write.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute paths", json.loads(result.stdout)["reason"])

    def test_task_bound_absolute_v4a_patch_is_allowed(self) -> None:
        target = self.workspace / "specs" / "example" / "spec.md"
        patch_text = (
            "*** Begin Patch\n"
            f"***Update File: {target}\n"
            "@@\n"
            "-# Baseline\n"
            "+# Reconciled\n"
            "*** End Patch"
        )
        result = self.run_hook(
            tool_name="patch",
            tool_input={"mode": "patch", "patch": patch_text},
        )
        self.assertEqual(result.returncode, 0, result.stdout or result.stderr)

    def test_task_bound_v4a_no_space_outside_add_is_denied(self) -> None:
        inside = self.workspace / "inside.md"
        outside = self.root / "outside.md"
        patch_text = (
            "*** Begin Patch\n"
            f"*** Add File: {inside}\n"
            "+inside\n"
            f"***Add File: {outside}\n"
            "+outside\n"
            "*** End Patch"
        )
        result = self.run_hook(
            tool_name="patch",
            tool_input={"mode": "patch", "patch": patch_text},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the authorized workspace", json.loads(result.stdout)["reason"])

    def test_task_bound_v4a_move_validates_both_endpoints(self) -> None:
        inside = self.workspace / "specs" / "example" / "spec.md"
        outside = self.root / "moved.md"
        patch_text = f"*** Begin Patch\n*** Move File: {inside} -> {outside}\n*** End Patch"
        result = self.run_hook(
            tool_name="patch",
            tool_input={"mode": "patch", "patch": patch_text},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the authorized workspace", json.loads(result.stdout)["reason"])

    def test_task_bound_v4a_unrecognized_operation_header_is_denied(self) -> None:
        target = self.workspace / "specs" / "example" / "spec.md"
        patch_text = f"*** Begin Patch\n*** Move to: {target}\n*** End Patch"
        result = self.run_hook(
            tool_name="patch",
            tool_input={"mode": "patch", "patch": patch_text},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized patch operation", json.loads(result.stdout)["reason"])

    def test_task_bound_write_rejects_nonlinked_checkout(self) -> None:
        standalone = self.root / "standalone"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(standalone)], check=True)
        standalone_branch = "wt/standalone"
        subprocess.run(
            ["git", "-C", str(standalone), "checkout", "-q", "-b", standalone_branch],
            check=True,
        )
        with sqlite3.connect(self.board) as conn:
            conn.execute(
                "UPDATE tasks SET workspace_path = ?, branch_name = ? WHERE id = ?",
                (str(standalone), standalone_branch, self.task_id),
            )
        result = self.run_hook(
            cwd=standalone,
            env_updates={
                "HERMES_KANBAN_WORKSPACE": str(standalone),
                "HERMES_KANBAN_BRANCH": standalone_branch,
            },
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a linked worktree", json.loads(result.stdout)["reason"])

    def test_supervisor_allows_merge_base_but_still_gates_merge(self) -> None:
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE tasks SET assignee = 'supervisor' WHERE id = ?", (self.task_id,))
            conn.execute("UPDATE task_runs SET profile = 'supervisor' WHERE id = ?", (self.run_id,))
        self.hook = self.home / "profiles" / "supervisor" / "hooks" / CANONICAL.name

        allowed = self.run_hook(
            tool_name="terminal",
            tool_input={"command": "git merge-base --is-ancestor HEAD HEAD", "workdir": str(self.workspace)},
        )
        self.assertEqual(allowed.returncode, 0, allowed.stdout or allowed.stderr)

        denied = self.run_hook(
            tool_name="terminal",
            tool_input={"command": "git merge main", "workdir": str(self.workspace)},
        )
        self.assertEqual(denied.returncode, 2)
        self.assertIn("not the project's main worktree", json.loads(denied.stdout)["reason"])

    def test_main_integration_write_remains_allowed_without_task_binding(self) -> None:
        result = self.run_hook(
            path=str(self.repo / "specs" / "example" / "spec.md"),
            cwd=self.repo,
            env_updates={
                "HERMES_KANBAN_DB": None,
                "HERMES_KANBAN_TASK": None,
                "HERMES_KANBAN_RUN_ID": None,
                "HERMES_KANBAN_WORKSPACE": None,
                "HERMES_KANBAN_BRANCH": None,
            },
        )
        self.assertEqual(result.returncode, 0, result.stdout or result.stderr)

    def test_main_integration_relative_write_is_denied(self) -> None:
        result = self.run_hook(
            path="specs/example/spec.md",
            cwd=self.repo,
            env_updates={
                "HERMES_KANBAN_DB": None,
                "HERMES_KANBAN_TASK": None,
                "HERMES_KANBAN_RUN_ID": None,
                "HERMES_KANBAN_WORKSPACE": None,
                "HERMES_KANBAN_BRANCH": None,
            },
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "structured writes require absolute paths", json.loads(result.stdout)["reason"]
        )


class RolePolicyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-policy-roles-")
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home"
        subprocess.run(
            [
                sys.executable,
                str(SYNC),
                "install",
                "--home",
                str(self.home),
                "--backup-dir",
                str(self.root / "backup"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_hook(
        self, profile: str, tool_name: str, tool_input: Mapping[str, object]
    ) -> subprocess.CompletedProcess[str]:
        hook = self.home / "profiles" / profile / "hooks" / CANONICAL.name
        payload = {
            "hook_event_name": "pre_tool_call",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "extra": {},
            "cwd": str(self.root),
        }
        return subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_morfeo_retains_bounded_operational_tool_surface(self) -> None:
        allowed = [
            ("process", {"action": "list"}),
            ("execute_code", {"code": "print('bounded')"}),
            ("delegate_task", {"goal": "bounded read-only analysis"}),
            ("cronjob", {"action": "list"}),
        ]
        for tool_name, tool_input in allowed:
            with self.subTest(tool=tool_name):
                result = self.run_hook("morfeo", tool_name, tool_input)
                self.assertEqual(result.returncode, 0, result.stdout or result.stderr)

    def test_morfeo_computer_use_remains_denied(self) -> None:
        result = self.run_hook("morfeo", "computer_use", {})
        self.assertEqual(result.returncode, 2)
        reason = json.loads(result.stdout)["reason"]
        self.assertTrue(reason.startswith("AETHER-MORFEO-UNRELATED-TOOLSET:"))

    def test_all_roles_load_the_same_canonical_bytes(self) -> None:
        expected = CANONICAL.read_bytes()
        for profile in PROFILES:
            with self.subTest(profile=profile):
                installed = self.home / "profiles" / profile / "hooks" / CANONICAL.name
                self.assertEqual(installed.read_bytes(), expected)
                result = self.run_hook(profile, "read_file", {"path": "README.md"})
                self.assertEqual(result.returncode, 0, result.stdout or result.stderr)


if __name__ == "__main__":
    unittest.main()
