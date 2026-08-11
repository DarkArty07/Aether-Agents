"""Integrated M2 foundation services remain internal and default-off."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from aether_mcp.admission import ProjectAdmissionRegistry, TrustedLaunchContext
from aether_mcp.catalog import OrcaCatalog
from aether_mcp.foundation import M2Foundation
from aether_mcp.protocol import CALLABLE_TOOL_NAMES, TOOL_SCHEMAS
from aether_mcp.trace_store import TraceStore

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas/orca/1.4.167/catalog.json"


def _repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(("git", "init", "--initial-branch=main"), cwd=path, check=True, capture_output=True)
    subprocess.run(
        ("git", "-c", "user.name=Aether Test", "-c", "user.email=aether@test.invalid", "commit", "--allow-empty", "-m", "init"),
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def _operation(project_id: str, *, effect: str = "LOCAL_APPEND_ONLY") -> dict[str, object]:
    return {
        "operation_id": str(uuid.uuid4()),
        "project_id": project_id,
        "contract_id": "contract:test/1",
        "use_case_id": None,
        "reason": {"code": "TEST", "summary": "bounded foundation test", "authority_ref": "decision:test"},
        "expected_effect": effect,
    }


def test_integrated_m2_services_admit_validate_trace_and_plan_read_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    home = tmp_path / "home"
    home.mkdir()
    context = TrustedLaunchContext.from_environment(
        {
            "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
            "HERMES_HOME": str(home),
            "AETHER_PROFILE": "hermes",
            "AETHER_SESSION_ID": str(uuid.uuid4()),
        }
    )
    foundation = M2Foundation(
        context=context,
        admissions=ProjectAdmissionRegistry(tmp_path / "admissions"),
        trace=TraceStore(tmp_path / "trace"),
        catalog=OrcaCatalog.load(CATALOG),
    )
    admission_operation = _operation(str(uuid.uuid4()), effect="LOCAL_REVERSIBLE")
    admission_operation.pop("project_id")
    project = foundation.project_admit(
        {
            "operation": admission_operation,
            "project_root": str(repo),
            "safe_alias": "sample",
            "capture_policy": "DISABLED",
            "consent_authority_ref": "decision:test",
        }
    )
    inspected = foundation.project_inspect({"project_id": project.project_id})
    assert inspected.project_id == project.project_id

    manifest = {
        "protocol": "aether.mcp/v1alpha2",
        "project_id": project.project_id,
        "contract": {
            "contract_id": "contract:test/1",
            "generation": 1,
            "objective": "validation only",
            "acceptance": ["validated"],
            "non_goals": ["dispatch"],
            "authorized_effects": ["READ_ONLY"],
            "stop_condition": "validated",
        },
        "evaluation": {"enabled": False, "use_case_id": None, "variant": None, "measurement_contract": None},
        "learning": {"capture_policy": "DISABLED", "purpose": [], "consent_authority_ref": "decision:test"},
        "tasks": [{
            "task_key": "inspect",
            "deliverable": "projection",
            "archetype": "fixture",
            "dependencies": [],
            "read_scope": ["src"],
            "write_scope": [],
            "evidence_requirements": ["digest"],
            "attempt_budget": 1,
            "placement": "read_only",
        }],
    }
    validated = foundation.swarm_validate({"manifest": manifest})
    assert validated.project_id == project.project_id
    assert validated.manifest_ref == f"manifest:{validated.digest}"
    assert validated.provider_binding_digest == foundation.catalog.digest

    run_id = str(uuid.uuid4())
    decision_request = {
        "action": "record_decision",
        "project_id": project.project_id,
        "run_id": run_id,
        "operation": _operation(project.project_id),
        "mode": None,
        "filters": None,
        "cursor": None,
        "limit": None,
        "decision": {
            "kind": "route_selected",
            "decision": "use direct validation",
            "rationale": "M3 has not started",
            "authority_ref": "decision:test",
            "affected_ids": ["task:inspect"],
            "prior_generation": None,
        },
        "evidence": None,
    }
    foundation.swarm_trace(decision_request)
    query = dict(decision_request)
    query.update({"action": "query", "operation": None, "mode": "decisions", "filters": {}, "cursor": None, "limit": 10, "decision": None})
    result = foundation.swarm_trace(query)
    assert [event["kind"] for event in result["events"]] == ["DECISION"]

    search = foundation.orca_search({"project_id": project.project_id, "query": "run show", "effect": "READ_ONLY", "limit": 10})
    assert search[0].command_id == "orchestration.run_show"
    plan = foundation.orca_call(
        {
            "project_id": project.project_id,
            "command_id": "orchestration.run_show",
            "arguments": {"id": "run_123456789abc"},
            "catalog_digest": foundation.catalog.digest,
            "schema_bundle_digest": None,
            "expected_effect": "READ_ONLY",
            "reason": {"code": "TEST", "summary": "read-only projection", "authority_ref": "decision:test"},
            "operation": None,
        }
    )
    assert plan.argv[-1] == "--json"
    assert CALLABLE_TOOL_NAMES == frozenset(TOOL_SCHEMAS)
