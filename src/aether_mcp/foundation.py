"""Integrated M2 foundation services used by the operational MCP facade."""

from __future__ import annotations

from typing import Any

from .admission import ProjectAdmission, ProjectAdmissionRegistry, TrustedLaunchContext
from .catalog import CatalogEntry, CatalogPlan, OrcaCatalog
from .manifest import ValidatedManifest, validate_swarm_manifest
from .protocol import validate_request
from .trace_store import TraceStore


class M2Foundation:
    """Trusted M2 project, trace, validation, and read-only provider boundary."""

    def __init__(
        self,
        *,
        context: TrustedLaunchContext,
        admissions: ProjectAdmissionRegistry,
        trace: TraceStore,
        catalog: OrcaCatalog,
    ) -> None:
        if not isinstance(context, TrustedLaunchContext):
            raise TypeError("trusted launch context is required")
        self.context = context
        self.admissions = admissions
        self.trace = trace
        self.catalog = catalog

    def _project(self, project_id: str) -> ProjectAdmission:
        return self.admissions.inspect(context=self.context, project_id=project_id)

    def project_admit(self, arguments: dict[str, Any]) -> ProjectAdmission:
        admitted = validate_request("project_admit", arguments)
        return self.admissions.admit(
            context=self.context,
            project_root=admitted["project_root"],
            safe_alias=admitted["safe_alias"],
            capture_policy=admitted["capture_policy"],
            consent_authority_ref=admitted["consent_authority_ref"],
        )

    def project_inspect(self, arguments: dict[str, Any]) -> ProjectAdmission:
        admitted = validate_request("project_inspect", arguments)
        return self._project(admitted["project_id"])

    def swarm_validate(self, arguments: dict[str, Any]) -> ValidatedManifest:
        admitted = validate_request("swarm_validate", arguments)
        validated = validate_swarm_manifest(admitted["manifest"])
        self._project(validated.project_id)
        return validated

    def swarm_trace(self, arguments: dict[str, Any]) -> dict[str, Any]:
        admitted = validate_request("swarm_trace", arguments)
        project_id = admitted["project_id"]
        self._project(project_id)
        action = admitted["action"]
        if action == "query":
            mode = admitted["mode"]
            kinds: tuple[str, ...]
            if mode == "decisions":
                kinds = ("DECISION",)
            elif mode == "evidence":
                kinds = ("EVIDENCE",)
            else:
                kinds = ()
            return self.trace.query_semantic(
                project_id=project_id,
                run_id=admitted["run_id"],
                kinds=kinds,
                cursor=admitted["cursor"],
                limit=admitted["limit"],
            )
        operation = admitted["operation"]
        payload_key = "decision" if action == "record_decision" else "evidence"
        event = self.trace.append_semantic_event(
            operation_id=operation["operation_id"],
            project_id=project_id,
            run_id=admitted["run_id"],
            kind="DECISION" if payload_key == "decision" else "EVIDENCE",
            payload=admitted[payload_key],
        )
        return {"event": event}

    def orca_search(self, arguments: dict[str, Any]) -> tuple[CatalogEntry, ...]:
        admitted = validate_request("orca_search", arguments)
        self._project(admitted["project_id"])
        if admitted["effect"] not in {None, "READ_ONLY"}:
            return ()
        return self.catalog.search(admitted["query"], limit=admitted["limit"])

    def orca_describe(self, arguments: dict[str, Any]) -> CatalogEntry:
        admitted = validate_request("orca_describe", arguments)
        self._project(admitted["project_id"])
        return self.catalog.describe(
            admitted["command_id"],
            catalog_digest=admitted["catalog_digest"],
        )

    def orca_call(self, arguments: dict[str, Any]) -> CatalogPlan:
        admitted = validate_request("orca_call", arguments)
        self._project(admitted["project_id"])
        return self.catalog.plan_read_only(
            admitted["command_id"],
            admitted["arguments"],
            catalog_digest=admitted["catalog_digest"],
        )
