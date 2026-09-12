"""Formal disposable qualification laboratory.

The public package stays Hermes-free and lazy at import time. Individual lanes are
loaded only when their Python-level entry point is requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LANE_EXPORTS = {
    "score_history": (".matrix", "score_history"),
    "live_observation": (".observation", "live_observation"),
    "prepare_observation_only": (".observation", "prepare_observation_only"),
    "PersistentProbeResult": (".persistent", "PersistentProbeResult"),
    "persistent_session_probe": (".persistent", "persistent_session_probe"),
    "persistent_session_run": (".persistent", "persistent_session_run"),
    "probe_persistent_session": (".persistent", "probe_persistent_session"),
    "qualify_persistent_evidence": (".persistent", "qualify_persistent_evidence"),
    "run_persistent_session": (".persistent", "run_persistent_session"),
    "AffinityQualification": (".affinity", "AffinityQualification"),
    "opaque_flow_id": (".affinity", "opaque_flow_id"),
    "qualify_affinity_evidence": (".affinity", "qualify_affinity_evidence"),
    "run_sqlite_boundary_fixture": (".affinity", "run_sqlite_boundary_fixture"),
    "HarnessError": (".runner", "HarnessError"),
    "ScenarioError": (".runner", "ScenarioError"),
    "isolated_hermes_env": (".runner", "isolated_hermes_env"),
    "live_run": (".runner", "live_run"),
    "prepare_only": (".runner", "prepare_only"),
    "native_python_for": (".isolation", "native_python_for"),
    "preflight_disposable_destinations": (".isolation", "preflight_disposable_destinations"),
    "require_verified_writer_context": (".isolation", "require_verified_writer_context"),
    "resolve_writer_roots": (".isolation", "resolve_writer_roots"),
    "scrub_inherited_identity": (".isolation", "scrub_inherited_identity"),
    "verify_child_writer_context": (".isolation", "verify_child_writer_context"),
    "verify_writer_context": (".isolation", "verify_writer_context"),
    "writer_root_problems": (".isolation", "writer_root_problems"),
    "Scenario": (".synthetic_owner", "Scenario"),
    "load_scenario": (".synthetic_owner", "load_scenario"),
    "matching_reply": (".synthetic_owner", "matching_reply"),
    "validate_scenario": (".synthetic_owner", "validate_scenario"),
    "fixture_manifest": (".validation", "fixture_manifest"),
    "scenario_bytes": (".validation", "scenario_bytes"),
    "schema_bytes": (".validation", "schema_bytes"),
    "validate_evidence": (".validation", "validate_evidence"),
    "validate_fixture_manifest": (".validation", "validate_fixture_manifest"),
}

__all__ = sorted(_LANE_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _LANE_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
