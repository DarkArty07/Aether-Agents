"""Contract tests for A1's upstream-first Hermes release lock."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "specs"
    / "001-aether-v1-productization"
    / "contracts"
    / "release-lock.schema.json"
)


class ReleaseLockSourceModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        commit = "a" * 40
        digest = "b" * 64
        self.commit = commit
        self.digest = digest
        self.base = {
            "schema_version": 2,
            "aether": {
                "version": "1.0.0-rc.1",
                "package_version": "1.0.0rc1",
                "git_tag": "v1.0.0-rc.1",
                "git_commit": commit,
            },
            "profile_bundle": {
                "version": "1",
                "sha256": digest,
                "roles": ["morfeo", "supervisor", "implementer"],
            },
        }
        self.validator = jsonschema.Draft202012Validator(
            self.schema,
            format_checker=jsonschema.FormatChecker(),
        )

    def artifact(self, kind: str, filename: str) -> dict[str, str]:
        return {
            "kind": kind,
            "filename": filename,
            "url": f"https://example.invalid/{filename}",
            "sha256": self.digest,
            "provenance_url": "https://example.invalid/provenance",
        }

    def upstream_lock(self) -> dict[str, Any]:
        lock = copy.deepcopy(self.base)
        lock["hermes"] = {
            "source_mode": "upstream",
            "repository": "https://github.com/NousResearch/hermes-agent",
            "version": "0.20.5",
            "tag": "v2026.8.19",
            "commit": self.commit,
            "python_requires": ">=3.11,<3.14",
            "artifacts": [self.artifact("source", "hermes-agent.tar.gz")],
        }
        return lock

    def transitional_fork_lock(self) -> dict[str, Any]:
        lock = copy.deepcopy(self.base)
        lock["hermes"] = {
            "source_mode": "transitional_fork",
            "repository": "https://github.com/DarkArty07/hermes-agent",
            "version": "0.20.5",
            "tag": "aether-v0.20.5-1",
            "commit": self.commit,
            "python_requires": ">=3.11,<3.14",
            "upstream_base": {
                "repository": "https://github.com/NousResearch/hermes-agent",
                "tag": "v2026.8.19",
                "commit": self.commit,
            },
            "residual_patches": ["HLP-191"],
            "artifacts": [
                self.artifact("wheel", "hermes_agent.whl"),
                self.artifact("sdist", "hermes_agent.tar.gz"),
            ],
        }
        return lock

    def assert_valid(self, instance: dict[str, Any]) -> None:
        self.assertEqual(list(self.validator.iter_errors(instance)), [])

    def assert_invalid(self, instance: dict[str, Any]) -> None:
        self.assertNotEqual(list(self.validator.iter_errors(instance)), [])

    def test_upstream_mode_is_valid(self) -> None:
        self.assert_valid(self.upstream_lock())

    def test_transitional_fork_mode_is_valid(self) -> None:
        self.assert_valid(self.transitional_fork_lock())

    def test_fork_without_residual_patch_is_invalid(self) -> None:
        lock = self.transitional_fork_lock()
        lock["hermes"]["residual_patches"] = []
        self.assert_invalid(lock)

    def test_upstream_mode_cannot_point_to_fork(self) -> None:
        lock = self.upstream_lock()
        lock["hermes"]["repository"] = (
            "https://github.com/DarkArty07/hermes-agent"
        )
        self.assert_invalid(lock)

    def test_legacy_fork_only_shape_is_invalid(self) -> None:
        lock = self.upstream_lock()
        del lock["hermes"]["source_mode"]
        self.assert_invalid(lock)


if __name__ == "__main__":
    unittest.main()
