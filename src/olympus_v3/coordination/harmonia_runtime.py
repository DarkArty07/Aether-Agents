"""Lazy, project-scoped Harmonia runtime composition.

Construction is default-off: no key lookup, directory, SQLite connection or ACP
operation occurs until ``get_or_create`` is called for an admitted project.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Protocol

from .closure import CompletionState
from .contracts import TaskState
from .harmonia_selection import (
    Candidate,
    KernelSelectionValidator,
    Prerequisite,
    SelectionAuthority,
    derive_projection,
    propose_selection,
)
from .harmonia_store import ProjectStoreIdentity, derive_project_store
from .kernel_dispatcher import DispatchRejected, KernelDispatcher, StaleFence
from .kernel_runtime import KernelRunService, KernelWriter
from .ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)
from .olympus_adapter import OlympusRuntimeAdapter
from .protocol import ValidationError
from .selection_commit import KernelSelectionCommitter, rebuild_selection_decisions

WRITER_ID = "hermes"
WRITER_KEY_ID = "harmonia-writer-v1"
INTEGRITY_KEY_ID = "harmonia-integrity-v1"
WRITER_RESOURCE = "harmonia-ledger-owner"
_WRITER_KEY_ENV = "AETHER_COORDINATION_WRITER_KEY_B64"
_INTEGRITY_KEY_ENV = "AETHER_COORDINATION_INTEGRITY_KEY_B64"
_MINIMUM_KEY_BYTES = 32
_WRITER_LEASE_TTL_NS = 3_600_000_000_000
_DISPATCH_LEASE_TTL_NS = 10_000_000_000
_DISPATCH_RENEWAL_MARGIN_NS = 3_000_000_000


class CoordinationKeyProviderUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("coordination keys unavailable")


@dataclass(frozen=True, slots=True)
class CoordinationKeys:
    writer_key: bytes = field(repr=False)
    integrity_key: bytes = field(repr=False)
    writer_id: str = WRITER_ID
    writer_key_id: str = WRITER_KEY_ID
    integrity_key_id: str = INTEGRITY_KEY_ID
    writer_resource: str = WRITER_RESOURCE

    def __post_init__(self) -> None:
        if len(self.writer_key) < _MINIMUM_KEY_BYTES or len(self.integrity_key) < _MINIMUM_KEY_BYTES:
            raise CoordinationKeyProviderUnavailable()


class CoordinationKeyProvider(Protocol):
    def load(self) -> CoordinationKeys: ...


class StaticCoordinationKeyProvider:
    """Test/injected provider; key bytes remain excluded from representations."""

    def __init__(self, writer_key: bytes, integrity_key: bytes) -> None:
        self._writer_key = bytes(writer_key)
        self._integrity_key = bytes(integrity_key)

    def load(self) -> CoordinationKeys:
        return CoordinationKeys(self._writer_key, self._integrity_key)


class EnvironmentCoordinationKeyProvider:
    """Load strict base64 keys from the server environment, never YAML/MCP."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = os.environ if environment is None else environment

    @staticmethod
    def _decode(value: object) -> bytes:
        if not isinstance(value, str) or not value:
            raise CoordinationKeyProviderUnavailable()
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise CoordinationKeyProviderUnavailable() from exc
        if len(decoded) < _MINIMUM_KEY_BYTES:
            raise CoordinationKeyProviderUnavailable()
        return decoded

    def load(self) -> CoordinationKeys:
        return CoordinationKeys(
            self._decode(self._environment.get(_WRITER_KEY_ENV)),
            self._decode(self._environment.get(_INTEGRITY_KEY_ENV)),
        )


class _HarmoniaKernelDispatcher(KernelDispatcher):
    """Kernel-owned closure hook for the already-declared fixed successor edge."""

    def __init__(self, *args, after_close=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._after_close = after_close

    async def finalize_close(self, *, authority=None):
        result = await super().finalize_close(authority=authority)
        if self._after_close is not None:
            await self._after_close()
        return result


@dataclass(slots=True)
class ProjectRuntimeContext:
    identity: ProjectStoreIdentity
    keys: CoordinationKeys
    ledger: SQLiteLedger
    runtime: KernelRunService
    adapter: OlympusRuntimeAdapter
    dispatcher: KernelDispatcher
    closed: bool = False
    monitor_tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    async def _stage_committed_selections(self) -> None:
        """Reconcile authenticated selections through the existing kernel dispatcher."""
        if self.runtime is None:
            return
        decisions = rebuild_selection_decisions(self.ledger)
        events = self.ledger.events()
        staged_payloads = [
            json.loads(event["payload"])
            for event in events
            if event["kind"] == "dispatch.staged"
        ]
        for decision in sorted(decisions.values(), key=lambda item: (item.run_id, item.selection_epoch)):
            try:
                run = self.runtime.run(decision.run_id)
                contract = self.ledger.read_contract(run.contract_id)
                target = self.runtime.task(decision.run_id, decision.selected_task_id)
            except (KeyError, ValueError):
                continue
            if (
                contract is None
                or run.contract_id != decision.contract_id
                or contract.status.value != "active"
                or contract.generation != decision.contract_generation
                or contract.revocation_epoch != decision.revocation_epoch
                or contract.task_worker_bindings is None
                or decision.selected_task_id not in contract.task_worker_bindings
                or contract.task_worker_bindings[decision.selected_task_id].actor_id != decision.resolved_worker_id
                or target.prerequisites is None
                or len(target.prerequisites) != 1
                or target.state not in {TaskState.PROPOSED, TaskState.RUNNING}
            ):
                continue
            source_id = target.prerequisites[0]
            source_stage = next(
                (
                    payload for payload in staged_payloads
                    if payload.get("run_id") == decision.run_id and payload.get("task_id") == source_id
                ),
                None,
            )
            if source_stage is None:
                continue
            try:
                envelope = self.dispatcher.stage_successor(
                    decision.run_id, source_id, decision.selected_task_id,
                    project_root=source_stage["project_root"], plan_revision=decision.plan_revision,
                    selection_epoch=decision.selection_epoch, selection_proposal_id=decision.proposal_id,
                    selection_worker_id=decision.resolved_worker_id,
                )
                dispatched = await self.dispatcher.dispatch_with(envelope.authority)
                if isinstance(dispatched, Mapping) and dispatched.get("accepted") is True:
                    await self.start_monitor(envelope.authority)
            except (DispatchRejected, StaleFence):
                continue

    async def _commit_bounded_selection(self, run_id: str, source_id: str) -> None:
        """Project and commit one bounded choice, using only kernel state."""
        run = self.runtime.run(run_id)
        contract = self.ledger.read_contract(run.contract_id)
        if contract is None or contract.selection_policy_id is None:
            return
        source = self.runtime.task(run_id, source_id)
        if source.state is not TaskState.CLOSED:
            return
        events = self.ledger.events()
        source_stage = next((json.loads(e["payload"]) for e in events
                             if e["kind"] == "dispatch.staged"
                             and json.loads(e["payload"]).get("run_id") == run_id
                             and json.loads(e["payload"]).get("task_id") == source_id), None)
        receipt = next((json.loads(e["payload"]) for e in reversed(events)
                        if e["kind"] == "evidence.receipt.recorded"
                        and json.loads(e["payload"]).get("run_id") == run_id
                        and json.loads(e["payload"]).get("task_id") == source_id), None)
        cleanup = next((json.loads(e["payload"]) for e in reversed(events)
                        if e["kind"] == "cleanup.completed"
                        and json.loads(e["payload"]).get("run_id") == run_id
                        and json.loads(e["payload"]).get("task_id") == source_id), None)
        if source_stage is None or receipt is None or cleanup is None or contract.task_worker_bindings is None:
            return
        prior = rebuild_selection_decisions(self.ledger)
        if (run_id, 1) in prior:
            return
        authority = SelectionAuthority(
            self.identity.installation_id, self.identity.project_id, run_id, contract.contract_id,
            contract.generation, contract.revocation_epoch, 1,
            source_stage.get("plan_revision"), source_stage.get("snapshot_digest"),
        )
        candidates = []
        for task_id in contract.selection_candidate_task_ids:
            task = self.runtime.task(run_id, task_id)
            attempts = self.runtime.attempts(run_id, task_id)
            if task.state is not TaskState.PROPOSED or attempts:
                return
            principal = contract.task_worker_bindings.get(task_id)
            if principal is None:
                return
            binding_digest = "sha256:" + hashlib.sha256(
                json.dumps(principal.to_dict(), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            candidates.append(Candidate(task_id, principal.actor_id, binding_digest,
                (Prerequisite(source_id, receipt["receipt_id"], cleanup.get("message_id", "cleanup:" + source_id), TaskState.CLOSED),),
                TaskState.PROPOSED, True))
        try:
            projection = derive_projection(
                authority, tuple(candidates), approved_task_ids=contract.selection_candidate_task_ids,
                bindings={task_id: contract.task_worker_bindings[task_id].actor_id for task_id in contract.selection_candidate_task_ids},
            )
            proposal = propose_selection(projection)
            validator = KernelSelectionValidator(authority, tuple(candidates),
                approved_task_ids=contract.selection_candidate_task_ids,
                bindings={task_id: contract.task_worker_bindings[task_id].actor_id for task_id in contract.selection_candidate_task_ids})
            writer = self.dispatcher._writer.context
            KernelSelectionCommitter(self.ledger, writer).commit(proposal, projection, validator)
        except (KeyError, ValueError, ValidationError, DispatchRejected, StaleFence):
            return

    async def _stage_fixed_successors(self) -> None:
        if self.runtime is None:
            return
        committed_runs = {decision.run_id for decision in rebuild_selection_decisions(self.ledger).values()}
        events = self.ledger.events()
        created = [json.loads(event["payload"]) for event in events if event["kind"] == "task.created"]
        for successor in created:
            if successor.get("run_id") in committed_runs:
                continue
            prerequisites = tuple(successor.get("prerequisites", ()))
            if len(prerequisites) != 1:
                continue
            source_id, successor_id = prerequisites[0], successor["task_id"]
            try:
                source = self.runtime.task(successor["run_id"], source_id)
                target = self.runtime.task(successor["run_id"], successor_id)
                contract = self.ledger.read_contract(self.runtime.run(successor["run_id"]).contract_id)
            except (KeyError, ValueError):
                continue
            if (contract is None or contract.task_worker_bindings is None or successor_id not in contract.task_worker_bindings
                    or contract.selection_policy_id is not None):
                continue
            if source.state is not TaskState.CLOSED or target.state not in {TaskState.PROPOSED, TaskState.RUNNING}:
                continue
            staged = next((json.loads(event["payload"]) for event in events
                           if event["kind"] == "dispatch.staged"
                           and json.loads(event["payload"]).get("run_id") == successor["run_id"]
                           and json.loads(event["payload"]).get("task_id") == source_id), None)
            if staged is None:
                continue
            try:
                envelope = self.dispatcher.stage_successor(
                    successor["run_id"], source_id, successor_id,
                    project_root=staged["project_root"], plan_revision=staged["plan_revision"],
                )
                dispatched = await self.dispatcher.dispatch_with(envelope.authority)
                if isinstance(dispatched, Mapping) and dispatched.get("accepted") is True:
                    await self.start_monitor(envelope.authority)
            except DispatchRejected:
                continue

    async def _after_source_close(self) -> None:
        """Selection commit precedes committed dispatch; fixed fallback is last."""
        for event in self.ledger.events():
            if event["kind"] != "run.created":
                continue
            run_id = json.loads(event["payload"]).get("run_id")
            if not run_id:
                continue
            try:
                contract = self.ledger.read_contract(self.runtime.run(run_id).contract_id)
                if contract is None or contract.selection_policy_id is None:
                    continue
                source = next((task_id for task_id in contract.task_worker_bindings or {}
                               if task_id not in contract.selection_candidate_task_ids), None)
                if source:
                    await self._commit_bounded_selection(run_id, source)
            except (KeyError, ValueError):
                continue
        await self._stage_committed_selections()
        await self._stage_fixed_successors()

    async def start_monitor(self, authority: Any, *, clock=None, poll_interval: float = 1.0):
        if self.closed:
            raise RuntimeError("runtime context is closed")
        existing = self.monitor_tasks.get(authority.message_id)
        if existing is not None and not existing.done():
            return existing
        clock = clock or self.ledger.clock
        if isinstance(poll_interval, bool) or not isinstance(poll_interval, (int, float)) or poll_interval < 0:
            raise ValueError("non-negative poll interval required")

        async def monitor():
            current = authority
            try:
                while True:
                    lease = self.ledger.lease(current.lease_resource)
                    if lease is None:
                        return
                    if lease.expires_at <= clock() + _DISPATCH_RENEWAL_MARGIN_NS:
                        renewed = self.dispatcher.renew_with(current, ttl=_DISPATCH_LEASE_TTL_NS)
                        renewed_lease = renewed.lease
                        if renewed_lease is None:
                            return
                        current = replace(current, lease_until=renewed_lease.expires_at)
                    observed = await self.dispatcher.observe_with(current)
                    status = observed.status
                    if status in {"completed", "error", "cancelled"}:
                        self.dispatcher.record_terminal_with(
                            current,
                            type("TerminalObservation", (), {
                                "status": status,
                                "logical_session": current.logical_session,
                                "acp_session_id": observed.acp_session_id,
                                "message_id": current.message_id,
                            })(),
                        )
                        self.dispatcher.materialize_response_result_with(current, observed.progress)
                        self.dispatcher.record_evidence_with(current)
                        if self.runtime is None:
                            return
                        proposed = {
                            "completed": CompletionState.COMPLETED,
                            "error": CompletionState.FAILED,
                            "cancelled": CompletionState.CANCELLED,
                        }[status]
                        self.runtime.request_close(
                            authority=current,
                            proposed_state=proposed,
                            command_id="monitor-close:" + current.message_id,
                        )
                        cleanup = await self.dispatcher.cleanup_once(authority=current)
                        if not isinstance(cleanup, Mapping) or cleanup.get("outcome") != "completed":
                            return
                        await self.dispatcher.finalize_close(authority=current)
                        return
                    if poll_interval:
                        await asyncio.sleep(poll_interval)
                    else:
                        await asyncio.sleep(0)
            except (DispatchRejected, StaleFence):
                return
            finally:
                self.monitor_tasks.pop(authority.message_id, None)

        task = asyncio.create_task(monitor())
        self.monitor_tasks[authority.message_id] = task
        return task

    async def resume_monitors(self) -> None:
        terminal_ids = {
            json.loads(event["payload"]).get("message_id")
            for event in self.ledger.events()
            if event["kind"] == "runtime.terminal.observed"
        }
        receipt_ids = {
            json.loads(event["payload"]).get("message_id")
            for event in self.ledger.events()
            if event["kind"] == "evidence.receipt.recorded"
        }
        for event in self.ledger.events():
            if event["kind"] != "dispatch.staged":
                continue
            payload = json.loads(event["payload"])
            message_id = payload.get("message_id")
            if message_id in terminal_ids:
                if message_id not in receipt_ids:
                    try:
                        self.dispatcher.record_evidence_with(self.dispatcher._envelope(payload).authority)
                    except (DispatchRejected, StaleFence):
                        pass
                continue
            binding = any(
                item["kind"] == "session.bound"
                and json.loads(item["payload"]).get("message_id") == payload.get("message_id")
                for item in self.ledger.events()
            )
            if binding:
                await self.start_monitor(self.dispatcher._envelope(payload).authority)
        if self.runtime is None:
            return
        for event in self.ledger.events():
            if event["kind"] == "run.created":
                run_id = json.loads(event["payload"]).get("run_id")
                if run_id:
                    try:
                        contract = self.ledger.read_contract(self.runtime.run(run_id).contract_id)
                        if contract is not None and contract.selection_policy_id is not None:
                            source = next((task_id for task_id in contract.task_worker_bindings or {}
                                           if task_id not in contract.selection_candidate_task_ids), None)
                            if source is not None:
                                await self._commit_bounded_selection(run_id, source)
                    except (KeyError, ValueError):
                        pass
        await self._stage_committed_selections()
        await self._stage_fixed_successors()

    async def aclose(self) -> None:
        if self.closed:
            return
        self.closed = True
        tasks = tuple(self.monitor_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.monitor_tasks.clear()
        self.ledger.close()


class ProjectRuntimeRegistry:
    """Own at most one writable kernel context for each canonical project."""

    def __init__(
        self,
        aether_home: str | Path,
        manager: Any,
        key_provider: CoordinationKeyProvider,
    ) -> None:
        if not callable(getattr(key_provider, "load", None)):
            raise TypeError("coordination key provider required")
        required_manager_methods = ("spawn_agent", "send_message", "poll", "close")
        if any(not callable(getattr(manager, name, None)) for name in required_manager_methods):
            raise TypeError("public ACP manager required")
        self._aether_home = Path(aether_home).expanduser().resolve()
        self._manager = manager
        self._key_provider = key_provider
        self._contexts: dict[str, ProjectRuntimeContext] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._closed = False

    @property
    def context_count(self) -> int:
        return len(self._contexts)

    async def get_or_create(self, project_root: str | Path) -> ProjectRuntimeContext:
        if self._closed:
            raise RuntimeError("runtime registry is closed")
        identity = derive_project_store(self._aether_home, project_root)
        current = self._contexts.get(identity.project_id)
        if current is not None:
            return current
        lock = self._locks.setdefault(identity.project_id, asyncio.Lock())
        async with lock:
            current = self._contexts.get(identity.project_id)
            if current is not None:
                return current
            context = self._build_context(identity)
            self._contexts[identity.project_id] = context
            await context.resume_monitors()
            return context

    def _build_context(self, identity: ProjectStoreIdentity) -> ProjectRuntimeContext:
        keys = self._key_provider.load()
        scope = StoreScope(identity.installation_id, identity.project_id)
        authenticator = HMACWriterAuthenticator({(keys.writer_id, keys.writer_key_id): keys.writer_key})
        signer = HMACIntegritySigner(keys.integrity_key, key_id=keys.integrity_key_id)
        ledger: SQLiteLedger | None = None
        try:
            ledger = SQLiteLedger(
                identity.store_path,
                scope,
                writer_authenticator=authenticator,
                integrity_signer=signer,
            )
            lease = ledger.acquire_lease(
                keys.writer_resource,
                keys.writer_id,
                ttl=_WRITER_LEASE_TTL_NS,
            ).lease
            if lease is None:
                raise RuntimeError("coordination writer lease unavailable")
            writer_context = WriterContext(
                scope,
                keys.writer_id,
                keys.writer_key_id,
                keys.writer_resource,
                lease.epoch,
                lease.expires_at,
            )
            runtime = KernelRunService(ledger, writer=KernelWriter(writer_context, authenticator))
            adapter = OlympusRuntimeAdapter(self._manager, project_id=identity.project_id, enabled=True)
            dispatcher = _HarmoniaKernelDispatcher(
                ledger=ledger,
                runtime=runtime,
                runtime_adapter=adapter,
                worker_id=keys.writer_id,
            )
            context = ProjectRuntimeContext(identity, keys, ledger, runtime, adapter, dispatcher)
            dispatcher._after_close = context._after_source_close
            return context
        except Exception:
            if ledger is not None:
                ledger.close()
            raise

    async def close(self, *, timeout_seconds: float = 5.0) -> tuple[BaseException, ...]:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("positive close timeout required")
        contexts = tuple(self._contexts.values())
        self._contexts.clear()
        self._closed = True
        if not contexts:
            return ()
        outcomes = await asyncio.gather(
            *(asyncio.wait_for(context.aclose(), timeout=timeout_seconds) for context in contexts),
            return_exceptions=True,
        )
        return tuple(outcome for outcome in outcomes if isinstance(outcome, BaseException))
