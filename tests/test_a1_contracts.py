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
    ROOT / "specs" / "001-aether-v1-productization" / "contracts" / "release-lock.schema.json"
)
A1_PLAN_PATH = ROOT / "specs" / "r13-synthesis-and-release" / "plan.md"
R6_SPEC_PATH = ROOT / "specs" / "r6-protocol-and-communication" / "spec.md"
R4_SPEC_PATH = ROOT / "specs" / "r4-hermes-boundary" / "spec.md"
R13_SPEC_PATH = ROOT / "specs" / "r13-synthesis-and-release" / "spec.md"
DESIGN_PATH = ROOT / "DESIGN.md"
ROADMAP_PATH = ROOT / "ROADMAP.md"
A1_SPEC_PATH = ROOT / "specs" / "001-aether-v1-productization" / "spec.md"
A1_PRODUCT_PLAN_PATH = ROOT / "specs" / "001-aether-v1-productization" / "plan.md"
OBS_SPEC_PATH = ROOT / "specs" / "002-aether-contract-observation" / "spec.md"
OBS_RESEARCH_PATH = ROOT / "specs" / "002-aether-contract-observation" / "research.md"


class ReleaseLockSourceModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        commit = "a" * 40
        digest = "b" * 64
        self.commit = commit
        self.digest = digest
        self.base = {
            "schema_version": 3,
            "aether": {
                "version": "1.0.0-rc.1",
                "package_version": "1.0.0rc1",
                "distribution": "aether-agents",
                "git_tag": "v1.0.0-rc.1",
                "git_commit": commit,
                "python_requires": ">=3.11,<3.14",
                "observer": {
                    "plugin_name": "aether-contract-observer",
                    "group": "hermes_agent.plugins",
                    "target": "aether_agents.observation.capture.hermes_plugin",
                },
                "wheel_sha256": digest,
                "observer_requirements_sha256": digest,
                "observation_compatibility": {
                    "event_write_version": "aether.observation.event.v1",
                    "event_read_versions": ["aether.observation.event.v1"],
                    "summary_write_version": "aether.observation.summary.v1",
                    "summary_read_versions": ["aether.observation.summary.v1"],
                    "segment_manifest_write_version": "aether.observation.segment-manifest.v1",
                    "segment_manifest_read_versions": ["aether.observation.segment-manifest.v1"],
                    "projection_schema_version": "aether.observation.projection.v1",
                },
            },
            "profile_bundle": {
                "version": "2",
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
            "source_tree_sha256": self.digest,
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
            "source_tree_sha256": self.digest,
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
        lock["hermes"]["repository"] = "https://github.com/DarkArty07/hermes-agent"
        self.assert_invalid(lock)

    def test_legacy_fork_only_shape_is_invalid(self) -> None:
        lock = self.upstream_lock()
        del lock["hermes"]["source_mode"]
        self.assert_invalid(lock)

    def test_source_tree_digest_is_required_and_artifact_paths_are_closed(self) -> None:
        missing_digest = self.upstream_lock()
        del missing_digest["hermes"]["source_tree_sha256"]
        self.assert_invalid(missing_digest)

        escaping_artifact = self.upstream_lock()
        escaping_artifact["hermes"]["artifacts"][0]["filename"] = "../secret.tar.gz"
        self.assert_invalid(escaping_artifact)

    def test_observer_dependency_lock_digest_is_required(self) -> None:
        lock = self.upstream_lock()
        del lock["aether"]["observer_requirements_sha256"]

        self.assert_invalid(lock)

    def test_observation_write_versions_must_belong_to_their_read_sets(self) -> None:
        fields = (
            ("event_write_version", "event_read_versions", "aether.observation.event.v2"),
            (
                "summary_write_version",
                "summary_read_versions",
                "aether.observation.summary.v2",
            ),
            (
                "segment_manifest_write_version",
                "segment_manifest_read_versions",
                "aether.observation.segment-manifest.v2",
            ),
        )
        for write_field, read_field, newer in fields:
            with self.subTest(write_field=write_field):
                lock = self.upstream_lock()
                compatibility = lock["aether"]["observation_compatibility"]
                compatibility[write_field] = newer
                self.assertNotIn(newer, compatibility[read_field])
                self.assert_invalid(lock)


class CanonicalContractConsistencyTests(unittest.TestCase):
    def test_r4_roadmap_id_has_no_inherited_trailing_whitespace(self) -> None:
        roadmap_id = R4_SPEC_PATH.read_text(encoding="utf-8").splitlines()[2]

        self.assertEqual(roadmap_id, "**Roadmap ID**: R4")

    def test_release_lock_schema_and_plan_agree_on_version_three(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        plan = A1_PLAN_PATH.read_text(encoding="utf-8")

        self.assertEqual(schema["properties"]["schema_version"]["const"], 3)
        self.assertIn("release-lock schema is integer `3`", plan)
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


class ObservationNormativeDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.design = DESIGN_PATH.read_text(encoding="utf-8")
        self.roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
        self.a1_spec = A1_SPEC_PATH.read_text(encoding="utf-8")
        self.a1_plan = A1_PRODUCT_PLAN_PATH.read_text(encoding="utf-8")
        self.observation = OBS_SPEC_PATH.read_text(encoding="utf-8")
        self.research = OBS_RESEARCH_PATH.read_text(encoding="utf-8")

    def test_product_definition_metadata_matches_the_pd76_stabilization_baseline(self) -> None:
        self.assertIn("accepted current conceptual design through PD-76", self.design)
        self.assertIn("`DESIGN.md` through PD-76", self.roadmap)
        self.assertIn("**Product-definition version**: `PD-74`", self.a1_spec)
        self.assertIn("PD-74 reliability gate", self.roadmap)
        self.assertNotIn(
            "product source: this contract authorizes planning only",
            self.a1_plan,
        )

    def test_verified_completion_requires_exact_product_owned_authority(self) -> None:
        required_contract = (
            "actor identity, profile, and role are resolved from product-owned "
            "context and never trusted from the event payload"
        )
        self.assertIn(required_contract, self.observation)
        self.assertIn("the assigned review authority", self.observation)
        self.assertIn("every OBS-INV-001 through OBS-INV-010", self.observation)
        self.assertIn("invalidates the prior verification", self.observation)
        self.assertIn("a fresh authoritative Morfeo verification", self.observation)

    def test_process_and_coverage_contract_forbids_temporal_causality(self) -> None:
        self.assertIn(
            "A wave exists only when explicit durable parent/dependency references",
            self.observation,
        )
        self.assertIn("Timestamp overlap never creates wave membership", self.observation)
        self.assertIn("`missing_hook_refs`", self.observation)
        self.assertIn("terminal-without-start", self.observation)
        self.assertIn("missing `turn_id` or `api_request_id`", self.observation)
        self.assertIn("heartbeat recency is `fresh`, `stale`, or `unknown`", self.observation)

    def test_storage_contract_covers_atomic_failure_boundaries(self) -> None:
        self.assertIn("`critical_pending` remains set", self.observation)
        self.assertIn("per-event savepoint", self.observation)
        self.assertIn("event row and all derived rows commit atomically", self.observation)
        self.assertIn("must not downgrade the active projection pointer", self.observation)
        self.assertIn("archive and manifest are durable and replay-verified", self.observation)

    def test_privacy_and_paths_are_structural_at_every_sink(self) -> None:
        for sink in ("queue", "logs", "journal", "SQLite", "summary", "retry"):
            self.assertIn(sink, self.observation)
        self.assertIn("before any sink can observe the native payload", self.observation)
        self.assertIn("`XDG_STATE_HOME` MUST be absolute", self.observation)
        self.assertIn("hard links", self.observation)
        self.assertIn("DB, WAL, and SHM", self.observation)
        self.assertIn("`0600`", self.observation)

    def test_exact_hermes_qualification_and_external_trace_gate_are_explicit(self) -> None:
        exact_baseline = "`v2026.8.18` (`e624e9fde561e1add9388384012b295fde669ade`)"
        self.assertIn(exact_baseline, self.observation)
        self.assertIn("22 registered callbacks", self.observation)
        self.assertIn("119 observation tests", self.observation)
        self.assertIn("zero hooks after unload", self.observation)
        self.assertIn("antecedent only and is non-qualifying", self.research)
        self.assertIn("#195` — curated semantic progress: **CLOSED", self.roadmap)
        self.assertIn("observation lane was executed separately", self.roadmap)


if __name__ == "__main__":
    unittest.main()
