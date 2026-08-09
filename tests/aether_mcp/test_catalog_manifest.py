"""M2.6 read-only provider catalog and manifest-validation tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from aether_mcp.catalog import CatalogError, OrcaCatalog
from aether_mcp.manifest import ManifestError, validate_swarm_manifest

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas/orca/1.4.167/catalog.json"


def _manifest() -> dict[str, object]:
    project_id = str(uuid.uuid4())
    return {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project_id,
        "contract": {
            "contract_id": "contract:test/1",
            "generation": 1,
            "objective": "validate without starting a Run",
            "acceptance": ["DAG accepted"],
            "non_goals": ["dispatch"],
            "authorized_effects": ["READ_ONLY"],
            "stop_condition": "validation result recorded",
        },
        "evaluation": {"enabled": False, "use_case_id": None, "variant": None, "measurement_contract": None},
        "learning": {"capture_policy": "DISABLED", "purpose": [], "consent_authority_ref": "decision:test"},
        "tasks": [
            {
                "task_key": "inspect",
                "deliverable": "read-only projection",
                "archetype": "fixture",
                "dependencies": [],
                "read_scope": ["src"],
                "write_scope": [],
                "evidence_requirements": ["catalog digest"],
                "attempt_budget": 1,
                "placement": "read_only",
            },
            {
                "task_key": "summarize",
                "deliverable": "summary",
                "archetype": "fixture",
                "dependencies": ["inspect"],
                "read_scope": ["src"],
                "write_scope": [],
                "evidence_requirements": ["manifest digest"],
                "attempt_budget": 1,
                "placement": "read_only",
            },
        ],
    }


def test_versioned_catalog_is_canonical_and_contains_read_only_public_commands() -> None:
    catalog = OrcaCatalog.load(CATALOG)
    bundled = OrcaCatalog.bundled()

    assert catalog.product_version == "1.4.167"
    assert bundled.digest == catalog.digest
    assert len(catalog.digest) == 64
    assert catalog.search("status", limit=10)[0].command_id == "status"
    described = catalog.describe("orchestration.run_show", catalog_digest=catalog.digest)
    assert described.effect == "READ_ONLY"
    assert described.argv_prefix == ("orchestration", "run-show")
    assert all(entry.effect == "READ_ONLY" for entry in catalog.entries)
    assert {"orchestration.run_create", "terminal.send", "terminal.close"}.isdisjoint(entry.command_id for entry in catalog.entries)


def test_catalog_digest_and_unknown_arguments_fail_closed(tmp_path: Path) -> None:
    catalog = OrcaCatalog.load(CATALOG)
    with pytest.raises(CatalogError) as captured:
        catalog.describe("status", catalog_digest="0" * 64)
    assert captured.value.code == "PROVIDER_SCHEMA_DRIFT"

    with pytest.raises(CatalogError) as captured:
        catalog.plan_read_only("orchestration.run_show", {"unexpected": "value"}, catalog_digest=catalog.digest)
    assert captured.value.code == "INVALID_INPUT"

    altered = tmp_path / "catalog.json"
    payload = json.loads(CATALOG.read_text())
    payload["commands"][0]["description"] = "tampered"
    altered.write_text(json.dumps(payload))
    with pytest.raises(CatalogError) as captured:
        OrcaCatalog.load(altered)
    assert captured.value.code == "PROVIDER_SCHEMA_DRIFT"


def test_read_only_call_plans_exact_argv_without_shell_or_mutation() -> None:
    catalog = OrcaCatalog.load(CATALOG)
    plan = catalog.plan_read_only(
        "orchestration.run_show",
        {"id": "run_123456789abc"},
        catalog_digest=catalog.digest,
    )
    assert plan.argv == ("orchestration", "run-show", "--id", "run_123456789abc", "--json")
    assert plan.effect == "READ_ONLY"
    assert all(token not in {";", "&&", "|", ">", "<"} for token in plan.argv)


def test_provider_envelope_is_bounded_and_validated() -> None:
    catalog = OrcaCatalog.load(CATALOG)
    payload = b'{"id":"request:1","ok":true,"result":{"runs":[]},"_meta":{"runtimeId":"runtime:1"}}'
    parsed = catalog.parse_response("orchestration.run_list", payload)
    assert parsed["result"] == {"runs": []}

    for invalid in (b"not-json", b'{"ok":false}', b"{" + b"x" * 1_100_000 + b"}"):
        with pytest.raises(CatalogError) as captured:
            catalog.parse_response("orchestration.run_list", invalid)
        assert captured.value.code == "PROVIDER_RESPONSE_INVALID"


def test_manifest_validation_returns_deterministic_digest_and_topological_order() -> None:
    manifest = _manifest()
    first = validate_swarm_manifest(manifest)
    second = validate_swarm_manifest(json.loads(json.dumps(manifest)))

    assert first.digest == second.digest
    assert first.topological_order == ("inspect", "summarize")
    assert first.project_id == manifest["project_id"]


def test_manifest_rejects_cycles_unknown_dependencies_and_write_conflicts() -> None:
    cycle = _manifest()
    cycle["tasks"][0]["dependencies"] = ["summarize"]  # type: ignore[index]
    with pytest.raises(ManifestError) as captured:
        validate_swarm_manifest(cycle)
    assert captured.value.code == "DEPENDENCY_CYCLE"

    unknown = _manifest()
    unknown["tasks"][1]["dependencies"] = ["missing"]  # type: ignore[index]
    with pytest.raises(ManifestError) as captured:
        validate_swarm_manifest(unknown)
    assert captured.value.code == "MANIFEST_INVALID"

    conflict = _manifest()
    conflict["tasks"][0]["write_scope"] = ["src/shared.py"]  # type: ignore[index]
    conflict["tasks"][1]["dependencies"] = []  # type: ignore[index]
    conflict["tasks"][1]["write_scope"] = ["src/shared.py"]  # type: ignore[index]
    with pytest.raises(ManifestError) as captured:
        validate_swarm_manifest(conflict)
    assert captured.value.code == "WRITE_SCOPE_CONFLICT"


def test_manifest_rejects_forbidden_participant_and_protected_effect_before_provider() -> None:
    forbidden = _manifest()
    forbidden["tasks"][0]["archetype"] = "etalides"  # type: ignore[index]
    with pytest.raises(ManifestError) as captured:
        validate_swarm_manifest(forbidden)
    assert captured.value.code == "PARTICIPANT_FORBIDDEN"

    protected = _manifest()
    protected["contract"]["authorized_effects"] = ["READ_ONLY", "EXTERNAL_IRREVERSIBLE"]  # type: ignore[index]
    with pytest.raises(ManifestError) as captured:
        validate_swarm_manifest(protected)
    assert captured.value.code == "EFFECT_NOT_AUTHORIZED"
