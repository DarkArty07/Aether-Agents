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
A1_PLAN_PATH = ROOT / "specs" / "r13-synthesis-and-release" / "plan.md"
R6_SPEC_PATH = ROOT / "specs" / "r6-protocol-and-communication" / "spec.md"
R4_SPEC_PATH = ROOT / "specs" / "r4-hermes-boundary" / "spec.md"
R13_SPEC_PATH = ROOT / "specs" / "r13-synthesis-and-release" / "spec.md"


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


class CanonicalContractConsistencyTests(unittest.TestCase):
    def test_r4_roadmap_id_has_no_inherited_trailing_whitespace(self) -> None:
        roadmap_id = R4_SPEC_PATH.read_text(encoding="utf-8").splitlines()[2]

        self.assertEqual(roadmap_id, "**Roadmap ID**: R4")

    def test_release_lock_schema_and_plan_agree_on_version_two(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        plan = A1_PLAN_PATH.read_text(encoding="utf-8")

        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)
        self.assertIn("release-lock schema is integer `2`", plan)
        self.assertNotIn("requires downstream fork coordinates unconditionally", plan)

    def test_tui_subscription_is_not_claimed_as_delivery(self) -> None:
        r6 = R6_SPEC_PATH.read_text(encoding="utf-8")
        r13 = R13_SPEC_PATH.read_text(encoding="utf-8")

        self.assertIn("platform=tui", r6)
        self.assertIn("not evidence of notification or wake delivery", r6)
        self.assertIn("same persistent Morfeo", r6)
        self.assertIn("#212", r13)
        self.assertNotIn(
            "session is subscribed automatically, so its originator is resumed",
            r6,
        )


if __name__ == "__main__":
    unittest.main()
