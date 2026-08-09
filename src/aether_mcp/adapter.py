"""Default-off Orca adapter planning, idempotency, and reconciliation foundation."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable, NoReturn

from .journal import DIGEST_RE, TOKEN_RE, JournalError, OperationJournal

QUALIFIED_MUTATIONS = frozenset({"run_create"})
RECEIPT_OUTCOMES = frozenset({"SUCCEEDED", "FAILED", "UNKNOWN"})
RECONCILE_OUTCOMES = frozenset({"APPLIED", "NOT_APPLIED", "UNKNOWN"})


class AdapterError(ValueError):
    """Stable default-off adapter failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise AdapterError(code, message)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_uuid(value: str, *, field: str) -> None:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        _fail("ERR_INVALID_ARGUMENT", f"{field} is not a UUID")
    if str(parsed) != value:
        _fail("ERR_INVALID_ARGUMENT", f"{field} is not canonical")


def _validate_digest(value: str, *, field: str) -> None:
    if DIGEST_RE.fullmatch(value) is None:
        _fail("ERR_INVALID_ARGUMENT", f"{field} is not a SHA-256 digest")


def _validate_text(value: str, *, field: str, maximum: int = 512) -> None:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > maximum:
        _fail("ERR_INVALID_ARGUMENT", f"{field} is empty or oversized")
    if value != value.strip() or any(ord(character) < 32 or ord(character) == 127 for character in value):
        _fail("ERR_INVALID_ARGUMENT", f"{field} contains control or boundary whitespace")


def _validate_token(value: str, *, field: str) -> None:
    if not isinstance(value, str) or TOKEN_RE.fullmatch(value) is None:
        _fail("ERR_INVALID_ARGUMENT", f"{field} is invalid")


@dataclass(frozen=True)
class ProviderBuildBinding:
    candidate_id: str
    product_version: str
    manifest_sha256: str
    catalog_sha256: str
    launcher_sha256: str
    appimage_sha256: str

    def __post_init__(self) -> None:
        _validate_token(self.candidate_id, field="candidate_id")
        _validate_token(self.product_version, field="product_version")
        for field in ("manifest_sha256", "catalog_sha256", "launcher_sha256", "appimage_sha256"):
            _validate_digest(getattr(self, field), field=field)

    @property
    def digest(self) -> str:
        return _digest(
            {
                "appimage_sha256": self.appimage_sha256,
                "candidate_id": self.candidate_id,
                "catalog_sha256": self.catalog_sha256,
                "launcher_sha256": self.launcher_sha256,
                "manifest_sha256": self.manifest_sha256,
                "product_version": self.product_version,
            }
        )


@dataclass(frozen=True)
class OperationRef:
    operation_id: str
    project_id: str
    contract_id: str
    principal_id: str

    def __post_init__(self) -> None:
        _validate_uuid(self.operation_id, field="operation_id")
        _validate_uuid(self.project_id, field="project_id")
        _validate_uuid(self.principal_id, field="principal_id")
        _validate_token(self.contract_id, field="contract_id")


@dataclass(frozen=True)
class CoordinatorBinding:
    principal_id: str
    project_id: str
    terminal_handle: str
    provider_build_digest: str
    admission_generation: int

    def __post_init__(self) -> None:
        _validate_uuid(self.principal_id, field="principal_id")
        _validate_uuid(self.project_id, field="project_id")
        _validate_token(self.terminal_handle, field="terminal_handle")
        _validate_digest(self.provider_build_digest, field="provider_build_digest")
        if not isinstance(self.admission_generation, int):
            _fail("ERR_INVALID_ARGUMENT", "admission_generation is not an integer")


@dataclass(frozen=True)
class AdapterPolicy:
    provider_build_digest: str
    coordinator_binding_qualified: bool
    qualified_mutations: frozenset[str]

    def __post_init__(self) -> None:
        _validate_digest(self.provider_build_digest, field="provider_build_digest")
        if not isinstance(self.coordinator_binding_qualified, bool):
            _fail("ERR_INVALID_ARGUMENT", "coordinator_binding_qualified is not boolean")
        if not self.qualified_mutations.issubset(QUALIFIED_MUTATIONS):
            _fail("ERR_INVALID_ARGUMENT", "qualified_mutations contains an unknown capability")

    @classmethod
    def r3_restricted(cls, build: ProviderBuildBinding) -> AdapterPolicy:
        return cls(
            provider_build_digest=build.digest,
            coordinator_binding_qualified=False,
            qualified_mutations=frozenset(),
        )


@dataclass(frozen=True)
class PlannedCall:
    operation: OperationRef | None
    capability: str
    effect: str
    argv: tuple[str, ...]
    provider_build_digest: str
    request_digest: str


@dataclass(frozen=True)
class ProviderReceipt:
    outcome: str
    project_id: str
    provider_request_id: str | None
    resource_ids: tuple[str, ...]
    response_digest: str | None


@dataclass(frozen=True)
class ReconciliationObservation:
    outcome: str
    project_id: str
    provider_request_id: str | None
    resource_ids: tuple[str, ...]
    response_digest: str | None


@dataclass(frozen=True)
class ExecutionResult:
    outcome: str
    replayed: bool
    resource_ids: tuple[str, ...]


class OrcaCommandPlanner:
    """Build exact argv tuples; it never executes subprocesses or reads ambient env."""

    def __init__(self, *, build: ProviderBuildBinding, policy: AdapterPolicy) -> None:
        if policy.provider_build_digest != build.digest:
            _fail("ERR_PROVIDER_BUILD_MISMATCH", "Adapter policy is bound to another provider build")
        self.build = build
        self.policy = policy

    def plan_status(self) -> PlannedCall:
        argv = ("status", "--json")
        request_digest = _digest(
            {
                "argv": argv,
                "capability": "status",
                "effect": "READ_ONLY",
                "provider_build_digest": self.build.digest,
            }
        )
        return PlannedCall(
            operation=None,
            capability="status",
            effect="READ_ONLY",
            argv=argv,
            provider_build_digest=self.build.digest,
            request_digest=request_digest,
        )

    def plan_run_create(
        self,
        *,
        operation: OperationRef,
        coordinator: CoordinatorBinding,
        objective: str,
    ) -> PlannedCall:
        if not self.policy.coordinator_binding_qualified:
            _fail(
                "ERR_COORDINATOR_BINDING_UNQUALIFIED",
                "R3 did not qualify a trusted coordinator binding",
            )
        if "run_create" not in self.policy.qualified_mutations:
            _fail("ERR_CAPABILITY_UNQUALIFIED", "run_create is not qualified")
        if not isinstance(coordinator, CoordinatorBinding):
            _fail("ERR_COORDINATOR_BINDING_REQUIRED", "Coordinator binding is missing or malformed")
        if coordinator.provider_build_digest != self.build.digest:
            _fail("ERR_PROVIDER_BUILD_MISMATCH", "Coordinator is bound to another provider build")
        if coordinator.project_id != operation.project_id:
            _fail("ERR_COORDINATOR_SCOPE_MISMATCH", "Coordinator is bound to another project")
        if coordinator.principal_id != operation.principal_id:
            _fail("ERR_COORDINATOR_PRINCIPAL_MISMATCH", "Coordinator is bound to another principal")
        if coordinator.admission_generation < 1:
            _fail("ERR_COORDINATOR_BINDING_STALE", "Coordinator admission generation is stale")
        _validate_text(objective, field="objective")
        argv = (
            "orchestration",
            "run-create",
            "--objective",
            objective,
            "--from",
            coordinator.terminal_handle,
            "--json",
        )
        request_digest = _digest(
            {
                "argv": argv,
                "capability": "run_create",
                "contract_id": operation.contract_id,
                "effect": "LOCAL_REVERSIBLE",
                "operation_id": operation.operation_id,
                "principal_id": operation.principal_id,
                "project_id": operation.project_id,
                "provider_build_digest": self.build.digest,
            }
        )
        return PlannedCall(
            operation=operation,
            capability="run_create",
            effect="LOCAL_REVERSIBLE",
            argv=argv,
            provider_build_digest=self.build.digest,
            request_digest=request_digest,
        )


class AdapterRuntime:
    """Append-before-effect execution and read-only reconciliation coordinator."""

    def __init__(self, journal: OperationJournal) -> None:
        self.journal = journal

    @staticmethod
    def _operation(call: PlannedCall) -> OperationRef:
        if call.operation is None:
            _fail("ERR_OPERATION_REQUIRED", "Journaled execution requires an operation identity")
        return call.operation

    @staticmethod
    def _result_from_record(record: dict[str, Any], *, replayed: bool) -> ExecutionResult:
        outcome = record["outcome"]
        if outcome == "PREPARED":
            outcome = "UNKNOWN"
        return ExecutionResult(
            outcome=outcome,
            replayed=replayed,
            resource_ids=tuple(record["resource_ids"]),
        )

    def execute(
        self,
        call: PlannedCall,
        executor: Callable[[PlannedCall], ProviderReceipt],
    ) -> ExecutionResult:
        operation = self._operation(call)
        try:
            prepared, record = self.journal.prepare_intent(
                operation_id=operation.operation_id,
                project_id=operation.project_id,
                capability=call.capability,
                request_digest=call.request_digest,
            )
        except JournalError as exc:
            if exc.code == "ERR_OPERATION_CONFLICT":
                _fail("ERR_OPERATION_CONFLICT", "Operation identity was reused with a different request")
            raise
        if not prepared:
            return self._result_from_record(record, replayed=True)
        try:
            receipt = executor(call)
        except Exception:
            self.journal.append_event(
                operation_id=operation.operation_id,
                project_id=operation.project_id,
                capability=call.capability,
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=call.request_digest,
                error_code="ERR_PROVIDER_EFFECT_UNKNOWN",
            )
            return ExecutionResult(outcome="UNKNOWN", replayed=False, resource_ids=())
        try:
            self._validate_receipt(receipt, project_id=operation.project_id)
        except AdapterError:
            self.journal.append_event(
                operation_id=operation.operation_id,
                project_id=operation.project_id,
                capability=call.capability,
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=call.request_digest,
                error_code="ERR_PROVIDER_RECEIPT_SCOPE",
            )
            raise
        error_code = None
        if receipt.outcome == "FAILED":
            error_code = "ERR_PROVIDER_OPERATION_FAILED"
        elif receipt.outcome == "UNKNOWN":
            error_code = "ERR_PROVIDER_EFFECT_UNKNOWN"
        record = self.journal.append_event(
            operation_id=operation.operation_id,
            project_id=operation.project_id,
            capability=call.capability,
            phase="RECEIPT",
            outcome=receipt.outcome,
            request_digest=call.request_digest,
            response_digest=receipt.response_digest,
            provider_request_id=receipt.provider_request_id,
            resource_ids=receipt.resource_ids,
            error_code=error_code,
        )
        return self._result_from_record(record, replayed=False)

    def reconcile(
        self,
        operation_id: str,
        probe: Callable[[dict[str, Any]], ReconciliationObservation],
    ) -> ExecutionResult:
        _validate_uuid(operation_id, field="operation_id")
        records = self.journal.records_for(operation_id)
        if not records:
            _fail("ERR_OPERATION_NOT_FOUND", "Operation has no journal intent")
        latest = records[-1]
        if latest["outcome"] in {"SUCCEEDED", "FAILED", "NOT_APPLIED"}:
            return self._result_from_record(latest, replayed=True)
        correlation = {
            "operation_id": operation_id,
            "project_id": latest["project_id"],
            "capability": latest["capability"],
            "request_digest": latest["request_digest"],
            "provider_request_id": latest["provider_request_id"],
            "resource_ids": tuple(latest["resource_ids"]),
        }
        try:
            observation = probe(correlation)
        except Exception:
            record = self.journal.append_event(
                operation_id=operation_id,
                project_id=latest["project_id"],
                capability=latest["capability"],
                phase="RECONCILE",
                outcome="UNKNOWN",
                request_digest=latest["request_digest"],
                error_code="ERR_RECONCILIATION_UNKNOWN",
            )
            return self._result_from_record(record, replayed=False)
        self._validate_observation(observation, project_id=latest["project_id"])
        outcome = "SUCCEEDED" if observation.outcome == "APPLIED" else observation.outcome
        record = self.journal.append_event(
            operation_id=operation_id,
            project_id=latest["project_id"],
            capability=latest["capability"],
            phase="RECONCILE",
            outcome=outcome,
            request_digest=latest["request_digest"],
            response_digest=observation.response_digest,
            provider_request_id=observation.provider_request_id,
            resource_ids=observation.resource_ids,
            error_code="ERR_RECONCILIATION_UNKNOWN" if outcome == "UNKNOWN" else None,
        )
        return self._result_from_record(record, replayed=False)

    @staticmethod
    def _validate_receipt(receipt: ProviderReceipt, *, project_id: str) -> None:
        if not isinstance(receipt, ProviderReceipt):
            _fail("ERR_PROVIDER_RECEIPT_SHAPE", "Provider receipt is not structured")
        if receipt.project_id != project_id:
            _fail("ERR_PROVIDER_RECEIPT_SCOPE", "Provider receipt belongs to another project")
        if receipt.outcome not in RECEIPT_OUTCOMES:
            _fail("ERR_PROVIDER_RECEIPT_SHAPE", "Provider receipt outcome is invalid")
        AdapterRuntime._validate_provider_fields(
            receipt.provider_request_id,
            receipt.resource_ids,
            receipt.response_digest,
        )

    @staticmethod
    def _validate_observation(observation: ReconciliationObservation, *, project_id: str) -> None:
        if not isinstance(observation, ReconciliationObservation):
            _fail("ERR_RECONCILIATION_SHAPE", "Reconciliation observation is not structured")
        if observation.project_id != project_id:
            _fail("ERR_RECONCILIATION_SCOPE", "Reconciliation observation belongs to another project")
        if observation.outcome not in RECONCILE_OUTCOMES:
            _fail("ERR_RECONCILIATION_SHAPE", "Reconciliation outcome is invalid")
        AdapterRuntime._validate_provider_fields(
            observation.provider_request_id,
            observation.resource_ids,
            observation.response_digest,
        )

    @staticmethod
    def _validate_provider_fields(
        provider_request_id: str | None,
        resource_ids: tuple[str, ...],
        response_digest: str | None,
    ) -> None:
        if provider_request_id is not None:
            _validate_token(provider_request_id, field="provider_request_id")
        if not isinstance(resource_ids, tuple) or len(resource_ids) > 64:
            _fail("ERR_PROVIDER_RECEIPT_SHAPE", "Provider resource identities are invalid")
        for resource_id in resource_ids:
            _validate_token(resource_id, field="resource_id")
        if response_digest is not None:
            _validate_digest(response_digest, field="response_digest")
