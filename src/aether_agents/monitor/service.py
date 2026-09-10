"""Hermes-free control service for the Aether Telegram monitor.

The public control surface is the ``aether monitor status|on|off|history`` CLI and the
matching native ``aether_monitor`` tool.  Both route through :class:`MonitorService` so
that the JSON envelope, the durable state transitions and the error taxonomy cannot
drift between the two entry points.

This module is Hermes-free by construction: it reads and writes the monitor's own
private state and delegates every native effect (existing Telegram destination,
native cron job lifecycle) to an injected :class:`NativeMonitorRuntime`.  The runtime
implementation lives in :mod:`aether_agents.monitor.runtime` and is imported lazily, so
``aether --help``/``aether monitor --help`` keep working when the managed Hermes runtime
is absent or broken.

Concurrency and privacy rules owned by the accepted MON-01..MON-04 units remain in
force: manual off is persisted before any native pause, the destination reference is an
opaque pinned binding, and no credential, chat identifier, message text or source
content crosses this boundary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence
from zoneinfo import ZoneInfo

from aether_agents.monitor.store import MonitorStore, MonitorStoreError

__all__ = [
    "ACTION_HISTORY",
    "ACTION_OFF",
    "ACTION_ON",
    "ACTION_STATUS",
    "ACTIONS",
    "DEFAULT_HISTORY_LIMIT",
    "MAX_HISTORY_LIMIT",
    "MONITOR_SCHEMA_VERSION",
    "MORFEO_PROFILE",
    "NATIVE_JOB_NAME",
    "NATIVE_SCHEDULE",
    "PRECHECK_SCRIPT_NAME",
    "MonitorActionError",
    "MonitorService",
    "NativeMonitorRuntime",
    "error_envelope",
    "result_envelope",
]

MONITOR_SCHEMA_VERSION = "aether.telegram-monitor.v1"

#: The monitor belongs to the provisioned Morfeo runtime only.
MORFEO_PROFILE = "morfeo"

ACTION_STATUS = "status"
ACTION_ON = "on"
ACTION_OFF = "off"
ACTION_HISTORY = "history"
ACTIONS = (ACTION_STATUS, ACTION_ON, ACTION_OFF, ACTION_HISTORY)

DEFAULT_HISTORY_LIMIT = 20
MAX_HISTORY_LIMIT = 200
MAX_STATUS_HISTORY = 25

#: Fixed native scheduling contract: one ordinary hourly job per installation.
NATIVE_SCHEDULE = "0 * * * *"
NATIVE_JOB_NAME = "Aether Telegram Monitor"
PRECHECK_SCRIPT_NAME = "aether_monitor_precheck.py"


class MonitorActionError(RuntimeError):
    """A bounded, destination-free control failure with a stable public code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NativeMonitorRuntime(Protocol):
    """Native effects the control service needs from a Hermes runtime.

    Every method is implemented inside the product runtime boundary (the plugin
    process or a validated runtime subprocess) and may raise
    :class:`MonitorActionError` with one of the stable public codes.
    """

    def runtime_identity(self) -> Mapping[str, Any]:
        """Return ``{"profile", "hermes_home", "timezone", "schedule"}`` for this runtime."""

        ...

    def resolve_destination(self) -> Mapping[str, Any]:
        """Resolve the exact existing Telegram home target, or fail closed."""

        ...

    def ensure_job(
        self,
        *,
        job_id: str | None,
        script_name: str,
        schedule: str,
        name: str,
    ) -> Mapping[str, Any]:
        """Create, adopt or reuse the single owned native job."""

        ...

    def pause_job(self, job_id: str) -> Mapping[str, Any]:
        """Pause the exact owned job; other jobs are never touched."""

        ...

    def resume_job(self, job_id: str) -> Mapping[str, Any]:
        """Resume the exact owned job; other jobs are never touched."""

        ...

    def job_state(self, job_id: str) -> Mapping[str, Any] | None:
        """Read-only state of the exact owned job, or ``None`` when it is absent."""

        ...


def result_envelope(action: str, result: Mapping[str, Any]) -> dict[str, Any]:
    """Build the fixed successful public envelope."""

    return {
        "schema_version": MONITOR_SCHEMA_VERSION,
        "ok": True,
        "action": action,
        "result": dict(result),
    }


def error_envelope(action: str, code: str, message: str) -> dict[str, Any]:
    """Build the fixed failing public envelope."""

    return {
        "schema_version": MONITOR_SCHEMA_VERSION,
        "ok": False,
        "action": action,
        "error": {"code": code, "message": message},
    }


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _local_text(value: datetime, timezone_name: str | None = None) -> str:
    return _zoned(value, timezone_name).isoformat(timespec="seconds")


def _zone(timezone_name: str | None) -> ZoneInfo | None:
    """Resolve an IANA zone name, or ``None`` for the process-local fallback."""

    if isinstance(timezone_name, str) and timezone_name.strip():
        try:
            return ZoneInfo(timezone_name.strip())
        except (KeyError, ValueError, OSError):
            return None
    return None


def _zoned(value: datetime, timezone_name: str | None) -> datetime:
    zone = _zone(timezone_name)
    return value.astimezone(zone) if zone is not None else value.astimezone()


def first_resolvable_zone(*names: Any) -> str | None:
    """Return the first candidate that is a real IANA zone name, or ``None``."""

    for name in names:
        if _zone(name) is not None and isinstance(name, str):
            return name.strip()
    return None


def hour_boundary(value: datetime, timezone_name: str | None = None) -> datetime:
    """Return the configured-zone wall-clock hour boundary containing ``value``."""

    local = _zoned(value, timezone_name)
    boundary = local.replace(minute=0, second=0, microsecond=0)
    return boundary


def next_hour_boundary(value: datetime, timezone_name: str | None = None) -> datetime:
    """Return the next future wall-clock hour boundary.

    Resuming monitoring schedules the next real boundary instead of replaying missed
    ones, and a late tick still resolves to the boundary it belongs to.
    """

    return hour_boundary(value, timezone_name) + timedelta(hours=1)


def _bounded_history_limit(limit: Any) -> int:
    if limit is None:
        return DEFAULT_HISTORY_LIMIT
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise MonitorActionError("INVALID_LIMIT", "history --limit must be an integer")
    if not 1 <= limit <= MAX_HISTORY_LIMIT:
        raise MonitorActionError(
            "INVALID_LIMIT", f"history --limit must be between 1 and {MAX_HISTORY_LIMIT}"
        )
    return limit


def delivery_counts(deliveries: Sequence[Any]) -> dict[str, int]:
    """Count per-part delivery states without exposing message text."""

    counts: dict[str, int] = {}
    for delivery in deliveries:
        state = getattr(getattr(delivery, "state", None), "value", None) or str(
            getattr(delivery, "state", "unknown")
        )
        counts[state] = counts.get(state, 0) + 1
    return dict(sorted(counts.items()))


def _part_summary(deliveries: Sequence[Any]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for delivery in deliveries:
        state = getattr(getattr(delivery, "state", None), "value", None) or str(
            getattr(delivery, "state", "unknown")
        )
        entry: dict[str, Any] = {"part_index": int(delivery.part_index), "state": state}
        if delivery.message_id is not None:
            entry["message_id"] = str(delivery.message_id)
        if delivery.last_error_class is not None:
            entry["error_class"] = str(delivery.last_error_class)
        parts.append(entry)
    return parts


class MonitorService:
    """Control and read the monitor through one shared, Hermes-free service."""

    def __init__(
        self,
        *,
        store: MonitorStore | None = None,
        native: NativeMonitorRuntime | None = None,
        clock: Any | None = None,
        timezone_name: str | None = None,
    ) -> None:
        self.store = store if store is not None else MonitorStore()
        self.native = native
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._timezone_name = timezone_name

    # -- public surface -------------------------------------------------------

    def execute(self, action: str, *, limit: Any = None) -> dict[str, Any]:
        """Execute one action and always return a complete public envelope."""

        if action not in ACTIONS:
            return error_envelope(
                str(action), "INVALID_ACTION", "action must be status, on, off or history"
            )
        try:
            if action == ACTION_STATUS:
                return result_envelope(action, self._status())
            if action == ACTION_ON:
                return result_envelope(action, self._on())
            if action == ACTION_OFF:
                return result_envelope(action, self._off())
            return result_envelope(action, self._history(_bounded_history_limit(limit)))
        except MonitorActionError as error:
            return error_envelope(action, error.code, error.message)
        except MonitorStoreError:
            return error_envelope(
                action,
                "STORE_UNAVAILABLE",
                "monitor state is unavailable; run 'aether doctor' before retrying",
            )
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return error_envelope(
                action,
                "MONITOR_OPERATION_FAILED",
                "the monitor operation could not be completed; no partial effect is claimed",
            )

    # -- native boundary ------------------------------------------------------

    def _native(
        self,
        operation: str,
        call: Callable[[], Any],
        *,
        code: str = "RUNTIME_UNAVAILABLE",
    ) -> Any:
        """Run one native effect, converting every failure into the bounded taxonomy.

        The runtime protocol promises :class:`MonitorActionError`, but a drifted or
        broken native runtime can raise anything.  Nothing may escape the fixed public
        JSON control interface, so an unexpected failure becomes one sanitized code
        whose message never carries native detail.
        """

        try:
            return call()
        except MonitorActionError:
            raise
        except Exception as error:
            raise MonitorActionError(
                code,
                f"the native runtime failed the monitor {operation}; "
                "the operation was not completed",
            ) from error

    @staticmethod
    def _native_mapping(
        operation: str, value: Any, *, code: str = "RUNTIME_UNAVAILABLE"
    ) -> Mapping[str, Any]:
        """Require one native effect result to be a usable mapping."""

        if not isinstance(value, Mapping):
            raise MonitorActionError(
                code, f"the native runtime returned an unusable monitor {operation} result"
            )
        return value

    # -- actions --------------------------------------------------------------

    def _status(self) -> dict[str, Any]:
        settings = self.store.get_settings()
        now = self.clock()
        # One clock: the IANA zone the native schedule actually cuts hours in
        # (configured first, then the persisted pin). `timezone`, `next_cut_local` and
        # `next_cut_utc` therefore always describe the same clock, and any difference
        # from the persisted pin is exposed instead of hidden.
        zone_name = first_resolvable_zone(self._timezone_name, settings.timezone)
        boundary = next_hour_boundary(now, zone_name)
        effective_zone = zone_name or now.astimezone().tzname() or "UTC"
        pinned_zone = (
            settings.timezone.strip()
            if isinstance(settings.timezone, str) and settings.timezone.strip()
            else None
        )
        runtime: dict[str, Any] = {"available": self.native is not None}
        if settings.profile_binding:
            runtime["profile"] = settings.profile_binding
        job: Mapping[str, Any] | None = None
        if settings.native_job_id:
            runtime["job_id"] = settings.native_job_id
            native = self.native
            if native is None:
                runtime["job_error"] = "RUNTIME_UNAVAILABLE"
            else:
                job_id = settings.native_job_id
                try:
                    job = self._native(
                        "job status read",
                        lambda: native.job_state(job_id),
                        code="JOB_OPERATION_FAILED",
                    )
                    if job is not None:
                        job = self._native_mapping("job status", job, code="JOB_OPERATION_FAILED")
                except MonitorActionError as error:
                    job = None
                    runtime["job_error"] = error.code
        snapshots = self.store.list_snapshots(limit=1)
        last_report = None
        coverage_gaps: list[str] = []
        outcomes: dict[str, int] = {}
        if snapshots:
            snapshot = snapshots[0]
            coverage_gaps = list(snapshot.coverage_gaps)
            narrative = self.store.get_narrative(snapshot.report_id)
            deliveries = self.store.list_deliveries(snapshot.report_id)
            outcomes = delivery_counts(deliveries)
            last_report = {
                "report_id": snapshot.report_id,
                "cutoff_utc": snapshot.cutoff_utc,
                "collected_at_utc": snapshot.collected_at_utc,
                "resolved_at_utc": snapshot.resolved_at_utc,
                "narrative_status": (None if narrative is None else str(narrative.attempt_status)),
                "parts": _part_summary(deliveries),
            }
        result: dict[str, Any] = {
            "enabled": bool(settings.enabled),
            "first_enabled_at_utc": settings.first_enabled_at_utc,
            "paused_at_utc": settings.paused_at_utc,
            "last_cutoff_utc": settings.last_cutoff_utc,
            "timezone": effective_zone,
            "pinned_timezone": pinned_zone,
            "timezone_drift": bool(pinned_zone and pinned_zone != effective_zone),
            "destination_pinned": bool(settings.destination_ref),
            "next_cut_utc": _utc_text(boundary),
            "next_cut_local": _local_text(boundary, zone_name),
            "native_job": dict(job) if job is not None else None,
            "runtime": runtime,
            "coverage_gaps": coverage_gaps,
            "last_report": last_report,
            "delivery_outcomes": outcomes,
        }
        return result

    def _on(self) -> dict[str, Any]:
        native = self.native
        if native is None:
            raise MonitorActionError(
                "RUNTIME_UNAVAILABLE",
                "the provisioned Morfeo runtime is unavailable; the monitor was not changed",
            )
        identity = self._native_mapping(
            "runtime identity read",
            self._native("runtime identity read", native.runtime_identity),
        )
        settings = self.store.get_settings()
        profile = identity.get("profile")
        profile_text = (
            str(profile).strip() if isinstance(profile, str) and profile.strip() else None
        )
        # The monitor only ever runs as the provisioned Morfeo monitor. A missing or
        # foreign identity fails closed *before* any pin, job or state mutation.
        if profile_text != MORFEO_PROFILE:
            raise MonitorActionError(
                "RUNTIME_MISMATCH",
                "the monitor can only be enabled from the provisioned Morfeo runtime; "
                "no job or destination was changed",
            )
        if settings.profile_binding and settings.profile_binding != profile_text:
            raise MonitorActionError(
                "RUNTIME_MISMATCH",
                "the monitor is bound to a different profile; no job or destination was changed",
            )
        destination = self._native_mapping(
            "destination read",
            self._native(
                "destination read",
                native.resolve_destination,
                code="DESTINATION_UNAVAILABLE",
            ),
            code="DESTINATION_UNAVAILABLE",
        )
        reference = destination.get("reference")
        if not isinstance(reference, str) or not reference:
            raise MonitorActionError(
                "DESTINATION_INVALID", "the existing Telegram destination is invalid"
            )
        if settings.enabled and settings.destination_ref and settings.destination_ref != reference:
            raise MonitorActionError(
                "DESTINATION_CHANGED",
                "the configured Telegram destination changed while the monitor was enabled; "
                "turn the monitor off before re-pinning it",
            )
        timezone_name = first_resolvable_zone(
            self._timezone_name, identity.get("timezone"), settings.timezone
        )
        timezone_name = timezone_name or "UTC"
        job = self._native_mapping(
            "job reconciliation",
            self._native(
                "job reconciliation",
                lambda: native.ensure_job(
                    job_id=settings.native_job_id,
                    script_name=PRECHECK_SCRIPT_NAME,
                    schedule=NATIVE_SCHEDULE,
                    name=NATIVE_JOB_NAME,
                ),
                code="JOB_OPERATION_FAILED",
            ),
            code="JOB_OPERATION_FAILED",
        )
        job_id = job.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise MonitorActionError(
                "JOB_OPERATION_FAILED", "the native job could not be identified"
            )
        self.store.configure(
            native_job_id=job_id,
            profile_binding=profile_text,
            destination_ref=reference,
            timezone_name=timezone_name,
        )
        # Native scheduling is resumed before the durable switch flips, so a failed
        # enable can never leave the monitor claiming "on" (or a racing pre-check
        # collecting) while the owned job is not actually scheduled.
        resumed = self._native_mapping(
            "job resume",
            self._native(
                "job resume",
                lambda: native.resume_job(job_id),
                code="JOB_OPERATION_FAILED",
            ),
            code="JOB_OPERATION_FAILED",
        )
        self.store.set_enabled(True)
        settings = self.store.get_settings()
        return {
            "enabled": True,
            "profile_binding": settings.profile_binding,
            "destination_pinned": True,
            "native_job": dict(resumed),
            "job_created": bool(job.get("created")),
            "first_enabled_at_utc": settings.first_enabled_at_utc,
            "next_cut_utc": _utc_text(next_hour_boundary(self.clock(), settings.timezone)),
        }

    def _off(self) -> dict[str, Any]:
        settings = self.store.get_settings()
        was_enabled = bool(settings.enabled)
        # Manual off is durable before any native pause so a racing precheck or send
        # rechecks the disabled switch and stops.
        self.store.set_enabled(False)
        native = self.native
        job: Mapping[str, Any] | None = None
        paused = False
        warning: str | None = None
        if settings.native_job_id:
            job_id = settings.native_job_id
            if native is None:
                warning = "RUNTIME_UNAVAILABLE"
            else:
                try:
                    job = self._native_mapping(
                        "job pause",
                        self._native(
                            "job pause",
                            lambda: native.pause_job(job_id),
                            code="JOB_OPERATION_FAILED",
                        ),
                        code="JOB_OPERATION_FAILED",
                    )
                    paused = True
                except MonitorActionError as error:
                    warning = error.code
        current = self.store.get_settings()
        result: dict[str, Any] = {
            "enabled": False,
            "changed": was_enabled,
            "job_paused": paused,
            "paused_at_utc": current.paused_at_utc,
        }
        if job is not None:
            result["native_job"] = dict(job)
        if warning is not None:
            result["warning"] = warning
        return result

    def _history(self, limit: int) -> dict[str, Any]:
        reports: list[dict[str, Any]] = []
        for snapshot in self.store.list_snapshots(limit=limit):
            narrative = self.store.get_narrative(snapshot.report_id)
            deliveries = self.store.list_deliveries(snapshot.report_id)
            reports.append(
                {
                    "report_id": snapshot.report_id,
                    "cutoff_utc": snapshot.cutoff_utc,
                    "previous_cutoff_utc": snapshot.previous_cutoff_utc,
                    "collected_at_utc": snapshot.collected_at_utc,
                    "resolved_at_utc": snapshot.resolved_at_utc,
                    "narrative_status": (
                        None if narrative is None else str(narrative.attempt_status)
                    ),
                    "parts": _part_summary(deliveries),
                    "coverage_gaps": list(snapshot.coverage_gaps),
                }
            )
        return {"limit": limit, "count": len(reports), "reports": reports}
