"""Lazy, project-scoped Harmonia runtime composition.

Construction is default-off: no key lookup, directory, SQLite connection or ACP
operation occurs until ``get_or_create`` is called for an admitted project.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Protocol

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
                        self.dispatcher.record_evidence_with(current)
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
            dispatcher = KernelDispatcher(
                ledger=ledger,
                runtime=runtime,
                runtime_adapter=adapter,
                worker_id=keys.writer_id,
            )
            return ProjectRuntimeContext(identity, keys, ledger, runtime, adapter, dispatcher)
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
