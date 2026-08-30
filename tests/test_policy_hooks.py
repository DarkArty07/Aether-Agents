"""Regression tests for Aether's minimal edge policy and sync tool."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

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

    def test_check_detects_byte_drift(self) -> None:
        self.run_sync("install", check=True)
        drifted = self.target("implementer")
        drifted.write_text("local change\n", encoding="utf-8")
        checked = self.run_sync("check")
        self.assertEqual(checked.returncode, 1)
        self.assertEqual(json.loads(checked.stdout)["result"], "drift")

    def test_check_detects_mode_drift(self) -> None:
        self.run_sync("install", check=True)
        drifted = self.target("supervisor")
        drifted.chmod(0o700)
        checked = self.run_sync("check")
        self.assertEqual(checked.returncode, 1)
        self.assertEqual(json.loads(checked.stdout)["result"], "drift")

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


class MinimalPolicyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="aether-minimal-policy-")
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

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def hook(self, role: str) -> Path:
        return self.home / "profiles" / role / "hooks" / CANONICAL.name

    def run_hook(
        self,
        role: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        *,
        use_public_args_shape: bool = False,
        payload_override: Any | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if payload_override is not None:
            payload = payload_override
        else:
            payload = {
                "hook_event_name": "pre_tool_call",
                "tool_name": tool_name,
                "extra": {},
            }
            payload["args" if use_public_args_shape else "tool_input"] = tool_input or {}
        return subprocess.run(
            [sys.executable, str(self.hook(role))],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=self.root,
            check=False,
        )

    def assert_allowed(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {})

    def assert_blocked(self, result: subprocess.CompletedProcess[str], code: str) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        reason = json.loads(result.stdout)["reason"]
        self.assertIn(f"-{code}:", reason)

    def test_policy_has_no_micro_authorization_dependencies(self) -> None:
        source = CANONICAL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (
                node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")]
            )
        }
        self.assertTrue({"sqlite3", "subprocess", "shlex"}.isdisjoint(imports))
        self.assertNotIn("HERMES_KANBAN_TASK", source)
        self.assertNotIn("HERMES_KANBAN_RUN_ID", source)
        self.assertNotIn("HERMES_KANBAN_WORKSPACE", source)
        self.assertNotIn("git", " ".join(sorted(imports)))
        self.assertLess(len(source.splitlines()), 320)

    def test_same_policy_bytes_are_installed_for_every_role(self) -> None:
        expected = CANONICAL.read_bytes()
        for role in PROFILES:
            self.assertEqual(self.hook(role).read_bytes(), expected)

    def test_ordinary_local_reversible_work_is_allowed_for_all_roles(self) -> None:
        cases = [
            ("terminal", {"command": "git status --short"}),
            ("terminal", {"command": "git branch topic"}),
            ("terminal", {"command": "git switch -c local-test"}),
            ("terminal", {"command": "git commit -am 'local change'"}),
            ("terminal", {"command": "git rebase main"}),
            ("terminal", {"command": "git merge feature/local"}),
            ("terminal", {"command": "git tag local-checkpoint"}),
            ("terminal", {"command": "rm -rf build/"}),
            ("terminal", {"command": "alembic upgrade head"}),
            ("terminal", {"command": "pytest -q"}),
            ("write_file", {"path": "specs/example/spec.md", "content": "local draft"}),
            ("patch", {"patch": "*** Begin Patch\n*** Add File: note.txt\n+ok\n*** End Patch"}),
            ("kanban_create", {"title": "ordinary local coordination", "body": "bounded"}),
            ("some_future_local_tool", {"value": "ordinary"}),
        ]
        for role in PROFILES:
            for tool_name, tool_input in cases:
                with self.subTest(role=role, tool_name=tool_name, tool_input=tool_input):
                    self.assert_allowed(self.run_hook(role, tool_name, tool_input))

    def test_public_args_payload_shape_is_accepted(self) -> None:
        result = self.run_hook(
            "morfeo",
            "terminal",
            {"command": "git status --short"},
            use_public_args_shape=True,
        )
        self.assert_allowed(result)

    def test_read_only_remote_api_is_not_misclassified_as_mutation(self) -> None:
        for command in (
            "gh api /repos/example/project",
            "gh api --method GET /repos/example/project",
            "curl https://example.invalid/health",
            "wget https://example.invalid/file",
        ):
            with self.subTest(command=command):
                self.assert_allowed(self.run_hook("supervisor", "terminal", {"command": command}))

    def test_redacted_or_example_secret_placeholders_are_allowed(self) -> None:
        for payload in (
            {"body": "api_key=[REDACTED]"},
            {"password": "example"},
            {"credential": "not-set"},
        ):
            with self.subTest(payload=payload):
                self.assert_allowed(self.run_hook("morfeo", "kanban_comment", payload))

    def test_durable_secret_material_is_blocked(self) -> None:
        secret_value = "value-" + "x" * 24
        result = self.run_hook(
            "implementer",
            "kanban_comment",
            {"password": secret_value},
        )
        self.assert_blocked(result, "DURABLE-SECRET")

    def test_high_confidence_secret_in_non_durable_tool_is_blocked(self) -> None:
        secret_value = "sk" + "-" + "A" * 24
        result = self.run_hook(
            "morfeo",
            "write_file",
            {"path": "notes.txt", "content": secret_value},
        )
        self.assert_blocked(result, "CREDENTIAL")

    def test_credential_acquisition_or_widening_is_blocked(self) -> None:
        commands = [
            "gh auth login",
            "aws configure",
            "ssh-keygen -t ed25519",
            "kubectl create secret generic app-secret",
        ]
        for role in PROFILES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assert_blocked(
                        self.run_hook(role, "terminal", {"command": command}),
                        "CREDENTIAL",
                    )

    def test_obvious_remote_mutation_is_blocked(self) -> None:
        commands = [
            "git push origin HEAD",
            "gh pr create --title test --body test",
            "gh api --method POST /repos/example/project/issues -f title=test",
            "npm publish",
            "docker push example/image:latest",
            "terraform apply -auto-approve",
            "kubectl apply -f deploy.yaml",
            "curl -X POST https://example.invalid/api -d '{}';",
        ]
        for role in PROFILES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assert_blocked(
                        self.run_hook(role, "terminal", {"command": command}),
                        "EXTERNAL-EFFECT",
                    )

    def test_only_high_confidence_local_destruction_is_blocked(self) -> None:
        commands = [
            "git reset --hard HEAD",
            "git clean -fdx",
            "rm -rf /",
            "wipefs -a /dev/sdz",
            "dd if=/dev/zero of=/dev/sdz bs=1M",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_blocked(
                    self.run_hook("morfeo", "terminal", {"command": command}),
                    "DESTRUCTIVE",
                )

        self.assert_allowed(self.run_hook("morfeo", "terminal", {"command": "rm -rf build/ dist/"}))
        self.assert_allowed(
            self.run_hook("implementer", "terminal", {"command": "git revert HEAD"})
        )

    def test_malformed_hook_invocation_fails_closed(self) -> None:
        malformed = [
            "not-json",
            [],
            {"hook_event_name": "post_tool_call", "tool_name": "terminal", "tool_input": {}},
            {"hook_event_name": "pre_tool_call", "tool_name": "", "tool_input": {}},
            {"hook_event_name": "pre_tool_call", "tool_name": "terminal", "tool_input": "bad"},
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                if payload == "not-json":
                    result = subprocess.run(
                        [sys.executable, str(self.hook("morfeo"))],
                        input="not-json",
                        text=True,
                        capture_output=True,
                        cwd=self.root,
                        check=False,
                    )
                else:
                    result = self.run_hook(
                        "morfeo",
                        "terminal",
                        payload_override=payload,
                    )
                self.assert_blocked(result, "PAYLOAD")


if __name__ == "__main__":
    unittest.main()
