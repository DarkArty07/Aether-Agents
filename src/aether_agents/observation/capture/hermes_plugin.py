"""Hermes-facing adapter for Aether Contract Observation.

This is the sole module in the distribution that knows about Hermes.  It is
discovered through the official ``hermes_agent.plugins`` entry-point group and
projects public hook payloads into the bounded, content-free event contract.

Callbacks are observers only: they return no directive, never mutate native
objects, never copy prompts/results/errors into an event, and never make a
Hermes lifecycle action depend on observation succeeding.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import stat
import threading
import weakref
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from aether_agents.observation.capture.collector import (
    Collector,
    observing,
    reentrancy_guard,
)
from aether_agents.observation.capture.journal import list_segments, read_segment
from aether_agents.observation.context import (
    ObservationContextResolver,
    canonical_project_id,
)
from aether_agents.observation.contracts import (
    COLLECTOR_VERSION,
    NULL_RUNTIME_FINGERPRINT,
    RUN_OUTCOMES,
    RUN_STATUSES,
    CoverageClass,
    canonical_digest,
    canonical_json_bytes,
    canonical_json_str,
    compute_runtime_fingerprint,
    event_validator,
    fallback_tool_category,
    normalize_native_status,
    validate_event,
)
from aether_agents.observation.fingerprints import configuration_fingerprint_id
from aether_agents.observation.identity import (
    binding_ref,
    native_identity,
    parse_correlation_token,
)
from aether_agents.observation.privacy import (
    NativePseudonymKind,
    assert_clean,
    native_agent_task_ref,
    native_kanban_task_ref,
    native_profile_ref,
    native_pseudonym_ref,
    native_run_id,
    opaque_ref,
    safe_error_class,
    safe_ref,
)
from aether_agents.paths import (
    ObservationPaths,
    UnsafeObservationPath,
    _open_private_directory,
)

__all__ = ["register"]

PLUGIN_NAME = "aether-contract-observer"
OBSERVED_HOOKS = (
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
    "pre_api_request",
    "post_api_request",
    "api_request_error",
    "pre_tool_call",
    "post_tool_call",
    "pre_approval_request",
    "post_approval_response",
    "subagent_start",
    "subagent_stop",
    "kanban_task_claimed",
    "kanban_task_completed",
    "kanban_task_blocked",
    "on_kanban_worker_spawned",
    "on_kanban_worker_exited",
    "on_kanban_worker_stale_claim",
    "on_kanban_task_updated",
    "on_kanban_dispatch_tick",
    "on_skill_lifecycle",
)

_REGISTERED: weakref.WeakSet[Any] = weakref.WeakSet()
_REGISTERED_FALLBACK: set[int] = set()
_TRACE_RE = re.compile(r"^ctr_[a-f0-9]{32}$")
_NATIVE_RECONCILIATION_INTERVAL_S = 30.0
_NATIVE_RECONCILIATION_DEBOUNCE_S = 0.05
_RECONCILIATION_HOOKS = frozenset(
    {
        "post_tool_call",
        "kanban_task_claimed",
        "kanban_task_completed",
        "kanban_task_blocked",
        "on_kanban_worker_spawned",
        "on_kanban_worker_exited",
        "on_kanban_worker_stale_claim",
        "on_kanban_task_updated",
        "on_kanban_dispatch_tick",
    }
)
_KANBAN_TASK_ID_HOOKS = frozenset(
    {
        "kanban_task_claimed",
        "kanban_task_completed",
        "kanban_task_blocked",
        "on_kanban_worker_spawned",
        "on_kanban_worker_exited",
        "on_kanban_worker_stale_claim",
        "on_kanban_task_updated",
    }
)
_PSEUDONYM_PREFIX: dict[NativePseudonymKind, str] = {
    "session": "sid",
    "turn": "trn",
    "api_request": "api",
    "tool_call": "call",
    "approval_request": "apr",
}


def _resolve_runtime_root() -> Path | None:
    """Return the root of the Hermes distribution loaded by this process."""
    try:
        import hermes_cli  # type: ignore[import-not-found]
    except Exception:  # a missing runtime is a coverage fact
        return None
    location = getattr(hermes_cli, "__file__", None)
    return Path(location).resolve().parent.parent if location else None


def _resolve_category_normalizer() -> tuple[Callable[[str], str], str | None, bool]:
    """Use the locked runtime taxonomy, with a visibly degraded fallback."""
    try:
        from hermes_cli.observability.shared_metrics_contract import (  # type: ignore[import-not-found]
            tool_category,
        )
        from model_tools import get_toolset_for_tool  # type: ignore[import-not-found]
    except Exception:
        return fallback_tool_category, None, False

    def normalize(name: str) -> str:
        # Match Hermes's own relay adapter: resolve the registry-owned toolset,
        # then feed that metadata mapping to shared_metrics_contract.tool_category.
        # The native normalizer accepts a mapping, not a bare tool name.
        try:
            toolset = get_toolset_for_tool(name)
        except Exception:
            return fallback_tool_category(name)
        return tool_category({"toolset": toolset or "other"}) or "unknown"

    return (
        normalize,
        "hermes_cli.observability.shared_metrics_contract:tool_category",
        True,
    )


def _native_datetime(value: Any) -> datetime | None:
    """Accept only unambiguous native timestamps; do not repair bad values."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _pick(payload: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in payload and payload[name] is not None:
            return payload[name]
    return None


def _coalesce(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def _duration_ms(payload: dict[str, Any]) -> int | None:
    direct = _pick(payload, "duration_ms")
    if isinstance(direct, int) and not isinstance(direct, bool) and direct >= 0:
        return direct
    seconds = _pick(payload, "api_duration", "duration_seconds")
    if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and seconds >= 0:
        return int(round(float(seconds) * 1000))
    return None


def _structured_error_type(payload: dict[str, Any]) -> Any:
    direct = _pick(payload, "error_type", "error_code")
    if direct is not None:
        return direct
    error = payload.get("error")
    return error.get("type") if isinstance(error, dict) else None


def _safe_create_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Inspect one create call in memory and return only opaque binding facts."""
    args = payload.get("args")
    result = payload.get("result")
    parsed_result: Any = result
    if isinstance(result, str):
        try:
            parsed_result = json.loads(result)
        except (TypeError, ValueError):
            parsed_result = None
    args = args if isinstance(args, dict) else {}
    parsed_result = parsed_result if isinstance(parsed_result, dict) else {}

    parsed_token = parse_correlation_token(args.get("idempotency_key"))
    token = (
        f"aether.obs.v1:{parsed_token[0]}:{parsed_token[1]}" if parsed_token is not None else None
    )
    raw_parents = args.get("parents")
    if isinstance(raw_parents, str):
        raw_parents = [raw_parents]
    parent_values = raw_parents if isinstance(raw_parents, (list, tuple)) else ()
    parents = tuple(
        ref for item in parent_values if (ref := native_kanban_task_ref(item)) is not None
    )
    raw_task_ref = parsed_result.get("task_id")
    return {
        "token": token,
        "token_parts": parsed_token,
        "parents": tuple(dict.fromkeys(parents)),
        "parent_ids_rejected": len(parents) != len(parent_values),
        "task_ref": native_kanban_task_ref(raw_task_ref),
        "task_id_rejected": raw_task_ref is not None
        and native_kanban_task_ref(raw_task_ref) is None,
        "project_id": safe_ref(parsed_result.get("project_id")),
        "ok": parsed_result.get("ok") is True,
    }


def _bounded_dispatch_result(result: Any) -> dict[str, Any]:
    """Project counts/cap signals from ``DispatchResult`` without retaining IDs."""

    def values(name: str) -> tuple[Any, ...]:
        raw = getattr(result, name, ())
        return tuple(raw) if isinstance(raw, (list, tuple)) else ()

    spawned = values("spawned")
    capped = values("skipped_per_profile_capped")
    unassigned = values("skipped_unassigned")
    nonspawnable = values("skipped_nonspawnable")
    guarded = values("respawn_guarded")
    rate_limited = values("rate_limited")
    eligible = len(spawned) + len(capped) + len(unassigned) + len(nonspawnable) + len(guarded)
    running_samples = [
        item[2]
        for item in capped
        if isinstance(item, (list, tuple))
        and len(item) >= 3
        and isinstance(item[2], int)
        and not isinstance(item[2], bool)
        and item[2] >= 0
    ]
    causes: set[str] = set()
    if capped:
        causes.add("capacity_bound")
    if unassigned:
        causes.add("unassigned")
    if rate_limited:
        causes.add("provider_bound")
    return {
        "eligible_count": eligible,
        "running_count": max(running_samples) if running_samples else None,
        "bottleneck_class": next(iter(causes)) if len(causes) == 1 else "unknown",
    }


def _validated_retained_events(paths: ObservationPaths):
    """Yield only canonical, schema-valid events coherent with their owned segment.

    Retained bytes are a recovery source, not authority merely because they exist.
    This reader follows the same valid-prefix boundary as ingestion and rejects
    quarantine, unverified archives, cross-project rows, and filename/sequence
    contradictions before they can restore an in-memory trace or task binding.
    """
    for segment in list_segments(paths):
        if segment.state == "quarantine":
            continue
        if segment.state == "archive":
            from aether_agents.observation.retention import verify_archive

            manifest = segment.path.with_name(segment.path.name + ".manifest.json")
            if not verify_archive(manifest).ok:
                continue
        try:
            snapshot = read_segment(segment.path)
        except (OSError, EOFError, UnsafeObservationPath):
            continue
        if segment.last_seq is not None and (
            snapshot.trailing_fragment
            or not snapshot.lines
            or segment.last_seq != segment.first_seq + len(snapshot.lines) - 1
        ):
            continue
        for index, line in enumerate(snapshot.lines):
            try:
                event = json.loads(line.decode("utf-8"))
                if not isinstance(event, dict) or canonical_json_bytes(event) != line:
                    raise ValueError("retained event is not canonical")
                validate_event(event)
                assert_clean(event)
                if event.get("project_id") != paths.project_id:
                    raise ValueError("retained event belongs to another project")
                if event.get("producer_epoch") != segment.producer_epoch:
                    raise ValueError("retained event producer does not match segment")
                if event.get("producer_seq") != segment.first_seq + index:
                    raise ValueError("retained event sequence does not match segment")
            except Exception:
                # Mirror ingestion's valid-prefix rule. Bytes after a malformed row
                # cannot recover authority even if they happen to look plausible.
                break
            yield event


def _retained_binding_rows(
    paths: ObservationPaths,
) -> dict[str, list[tuple[str, int, str, str, str, str]]]:
    """Read binding rows without inventing an order between producer processes."""
    candidates: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
    for event in _validated_retained_events(paths):
        unit = event.get("work_unit")
        if not isinstance(unit, dict):
            continue
        event_type = event.get("event_type")
        if event_type not in ("work_unit.bound", "work_unit.unbound") or event.get(
            "source_kind"
        ) not in {"hermes_hook", "native_reconciliation"}:
            continue
        trace_id = event.get("trace_id")
        task_ref = native_kanban_task_ref(unit.get("task_ref"))
        epoch = event.get("producer_epoch")
        sequence = event.get("producer_seq")
        if (
            task_ref is None
            or not isinstance(trace_id, str)
            or not _TRACE_RE.fullmatch(trace_id)
            or not isinstance(epoch, str)
            or not isinstance(sequence, int)
        ):
            continue
        candidates.setdefault(task_ref, []).append(
            (
                epoch,
                sequence,
                str(event.get("event_id") or ""),
                event_type,
                str(unit.get("relation") or "unknown"),
                trace_id,
            )
        )
    return candidates


def _resolve_retained_binding(
    candidates: list[tuple[str, int, str, str, str, str]],
) -> tuple[str, str] | None:
    if not candidates:
        return None
    per_epoch: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
    for candidate in candidates:
        per_epoch.setdefault(candidate[0], []).append(candidate)
    resolved: list[tuple[str, str] | None] = []
    for rows in per_epoch.values():
        highest_sequence = max(row[1] for row in rows)
        latest = [row for row in rows if row[1] == highest_sequence]
        values = {None if row[3] == "work_unit.unbound" else (row[5], row[4]) for row in latest}
        if len(values) != 1:
            return None
        resolved.append(values.pop())
    # Independent producers may corroborate the same durable fact, but neither a clock
    # nor an opaque producer/event ID may resolve contradictory bind/unbind claims.
    return resolved[0] if resolved and all(value == resolved[0] for value in resolved) else None


def _retained_binding(paths: ObservationPaths, task_ref: str) -> tuple[str, str] | None:
    """Rebuild one worker binding from retained Aether journal evidence."""
    return _resolve_retained_binding(_retained_binding_rows(paths).get(task_ref, []))


def _retained_bindings(paths: ObservationPaths) -> dict[str, tuple[str, str]]:
    """Rebuild the latest append-only binding state without consulting SQLite."""
    bindings: dict[str, tuple[str, str]] = {}
    for task_ref, candidates in _retained_binding_rows(paths).items():
        resolved = _resolve_retained_binding(candidates)
        if resolved is not None:
            bindings[task_ref] = resolved
    return bindings


def _retained_trace_exists(paths: ObservationPaths, trace_id: str) -> bool:
    return any(event.get("trace_id") == trace_id for event in _validated_retained_events(paths))


def _verified_native_session_ids(
    candidate_ids: set[str],
) -> tuple[frozenset[str], bool]:
    """Resolve SessionDB provenance without ever returning content-bearing columns.

    SessionDB accepts legacy and externally supplied opaque IDs, so grammar alone is
    not authoritative.  Reconciliation retains a Kanban ``session_id`` only when the
    exact identifier also exists in the locked native SessionDB.
    """
    if not candidate_ids:
        return frozenset(), True
    try:
        from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

        path = get_hermes_home() / "state.db"
        with _open_verified_native_session_db(path) as connection:
            verified: set[str] = set()
            ordered = sorted(candidate_ids)
            for offset in range(0, len(ordered), 400):
                chunk = ordered[offset : offset + 400]
                marks = ",".join("?" for _ in chunk)
                for (session_id,) in connection.execute(
                    f"SELECT id FROM sessions WHERE id IN ({marks}) ORDER BY id",
                    chunk,
                ):
                    candidate = safe_ref(session_id, max_len=256)
                    if candidate in candidate_ids:
                        verified.add(candidate)
            return frozenset(verified), True
    except Exception:
        return frozenset(), False


def _same_owned_private_native_db(
    observed: os.stat_result,
    expected: os.stat_result,
) -> bool:
    """Return whether two stats describe one current-user private DB inode."""
    return (
        stat.S_ISREG(observed.st_mode)
        and observed.st_nlink == 1
        and observed.st_uid == os.getuid()
        and observed.st_mode & (stat.S_IRWXG | stat.S_IRWXO) == 0
        and (observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino)
    )


@contextmanager
def _open_verified_native_session_db(path: Path) -> Iterator[sqlite3.Connection]:
    """Open SessionDB through a held, private inode and revalidate its ancestry.

    Python's SQLite binding has no custom ``O_NOFOLLOW`` VFS.  On the supported
    POSIX runtime, ``/proc/self/fd`` lets SQLite duplicate an already verified
    descriptor instead of resolving the configured filename again.  The original
    name and every ancestor are checked both before any query and after the final
    query; a concurrent substitution therefore makes all read facts unavailable.
    """
    path = Path(path)
    if os.name != "posix":  # pragma: no cover - release qualification is POSIX
        raise UnsafeObservationPath("secure native SessionDB reads require POSIX")
    if path.name != "state.db":
        raise UnsafeObservationPath("native SessionDB filename is not canonical")

    parent_descriptor = _open_private_directory(path.parent)
    descriptor = -1
    connection: sqlite3.Connection | None = None
    try:
        opened_parent = os.fstat(parent_descriptor)
        if opened_parent.st_uid != os.getuid():
            raise UnsafeObservationPath("native SessionDB parent is not user-owned")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            except OSError:
                raise exc
            if stat.S_ISLNK(named.st_mode) or not stat.S_ISREG(named.st_mode):
                raise UnsafeObservationPath(
                    "native SessionDB is a symlink or non-regular file"
                ) from None
            raise

        opened = os.fstat(descriptor)
        named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not _same_owned_private_native_db(opened, opened) or not _same_owned_private_native_db(
            named, opened
        ):
            raise UnsafeObservationPath("native SessionDB is aliased, public, or replaced")

        proc_path = Path("/proc/self/fd") / str(descriptor)
        if not proc_path.exists():
            raise UnsafeObservationPath("secure native SessionDB descriptor path is unavailable")
        connection = sqlite3.connect(
            f"file:{proc_path}?mode=ro",
            uri=True,
            timeout=0.25,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        yield connection
        connection.close()
        connection = None

        after = os.fstat(descriptor)
        named_after = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not _same_owned_private_native_db(after, opened) or not _same_owned_private_native_db(
            named_after, opened
        ):
            raise UnsafeObservationPath("native SessionDB changed while reading")
        verification_descriptor = _open_private_directory(path.parent)
        try:
            verified_parent = os.fstat(verification_descriptor)
            if verified_parent.st_uid != os.getuid() or (
                verified_parent.st_dev,
                verified_parent.st_ino,
            ) != (opened_parent.st_dev, opened_parent.st_ino):
                raise UnsafeObservationPath("native SessionDB ancestor changed while reading")
        finally:
            os.close(verification_descriptor)
    finally:
        if connection is not None:
            connection.close()
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


class _NativeReconciliationWorker:
    """Plugin-owned, out-of-callback native-store reconciliation worker.

    Hook callbacks only set an in-memory event.  SQLite opens, native reads, and
    projected journal appends happen on this daemon thread after a small debounce,
    satisfying OBS-FR-082 even for hooks fired inside the Kanban dispatch lock.
    """

    def __init__(self, observer: "_Observer") -> None:
        self._observer = observer
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="aether-native-reconciliation",
            daemon=True,
        )
        self._thread.start()
        self._wake.set()

    def schedule(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(_NATIVE_RECONCILIATION_INTERVAL_S)
            self._wake.clear()
            if self._stop.wait(_NATIVE_RECONCILIATION_DEBOUNCE_S):
                return
            try:
                with reentrancy_guard() as entered:
                    if entered:
                        self._observer._reconcile_native()
            except Exception:
                collector = self._observer._collector
                if collector is not None:
                    collector.health.increment("NATIVE_RECONCILIATION_FAILED")


class _Observer:
    """Translate native public payloads into one project's event journal."""

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx
        self._collector: Collector | None = None
        self._resolver = ObservationContextResolver()
        self._category, self._normalizer_ref, self._native_normalizer = (
            _resolve_category_normalizer()
        )
        runtime_root = _resolve_runtime_root()
        self._runtime_fingerprint, self._compatibility_missing = compute_runtime_fingerprint(
            runtime_root
        )
        self._active_trace: str | None = None
        self._active_traces: set[str] = set()
        self._diagnosed_traces: set[str] = set()
        self._diagnosed_unbound_tasks: set[str] = set()
        self._diagnosed_native_rejections: set[tuple[str, str]] = set()
        self._native_seen: set[tuple[Any, ...]] = set()
        self._retained_restored = False
        self._pending_spans: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._pending_models: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._pending_approvals: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._configuration_seen: set[tuple[str, str]] = set()
        self._loaded_skills: dict[tuple[str, str], set[str]] = {}
        self._trace_skills: dict[str, set[str]] = {}
        self._registration_failures: set[str] = set()
        self._reconciler = _NativeReconciliationWorker(self)

        # Compile once at registration, not during the first observed call.
        event_validator()
        collector = self._resolve_collector({})
        if collector is not None:
            self._restore_launch_binding(collector)

    @staticmethod
    def _bounded_put(
        mapping: OrderedDict[Any, dict[str, Any]],
        key: Any,
        value: dict[str, Any],
        collector: Collector,
        *,
        limit: int = 4096,
    ) -> None:
        mapping[key] = value
        mapping.move_to_end(key)
        if len(mapping) > limit:
            mapping.popitem(last=False)
            collector.health.increment("PENDING_CORRELATION_EVICTED")

    def _pseudonymize_native_ref(
        self,
        collector: Collector,
        kind: NativePseudonymKind,
        value: Any,
        *,
        max_len: int = 256,
    ) -> str | None:
        """Project one structurally safe native ID into a keyed epoch namespace."""
        if value in (None, ""):
            return None
        candidate = safe_ref(value, max_len=max_len)
        if candidate is None:
            return None
        if not collector.fingerprint_key_ready:
            self._record_native_hook_rejection(
                collector,
                "IDENTITY_PSEUDONYM_KEY_UNAVAILABLE",
            )
            return None
        try:
            key_id = collector.keyring.key_id
            digest = collector.keyring.fingerprint(f"native_{kind}_id", candidate)
        except Exception:
            self._record_native_hook_rejection(
                collector,
                "IDENTITY_PSEUDONYM_KEY_UNAVAILABLE",
            )
            return None
        projected = f"{_PSEUDONYM_PREFIX[kind]}_{key_id}_{digest}"
        return native_pseudonym_ref(projected, kind=kind)

    def _session(self, collector: Collector, payload: dict[str, Any]) -> str:
        return (
            self._pseudonymize_native_ref(
                collector,
                "session",
                _pick(payload, "session_id"),
            )
            or ""
        )

    def _turn(self, collector: Collector, payload: dict[str, Any], *names: str) -> str | None:
        return self._pseudonymize_native_ref(
            collector,
            "turn",
            _pick(payload, *(names or ("turn_id",))),
        )

    def _api_request(self, collector: Collector, payload: dict[str, Any]) -> str | None:
        return self._pseudonymize_native_ref(
            collector,
            "api_request",
            _pick(payload, "api_request_id", "request_id"),
        )

    def _call_key(
        self,
        collector: Collector,
        payload: dict[str, Any],
    ) -> tuple[str, str] | None:
        call_id = self._pseudonymize_native_ref(
            collector,
            "tool_call",
            _pick(payload, "tool_call_id", "call_id"),
        )
        return (self._session(collector, payload), call_id) if call_id is not None else None

    def _model_key(
        self,
        collector: Collector,
        payload: dict[str, Any],
    ) -> tuple[str, str] | None:
        request_ref = self._api_request(collector, payload)
        return (self._session(collector, payload), request_ref) if request_ref is not None else None

    def _profile(self, payload: dict[str, Any]) -> str | None:
        # Most Kanban hooks carry profile_name directly. API/tool/session hooks do
        # not always do so, and Hermes exposes the active profile on PluginContext.
        # This is identity metadata only; HERMES_HOME or its absolute path is never
        # persisted.
        return native_profile_ref(_pick(payload, "profile_name", "profile")) or native_profile_ref(
            getattr(self._ctx, "profile_name", None)
        )

    @staticmethod
    def _attempt_count(payload: dict[str, Any], fallback: int = 1) -> int:
        retry = _pick(payload, "retry_count")
        if isinstance(retry, int) and not isinstance(retry, bool) and retry >= 0:
            return retry + 1
        return max(1, fallback)

    @staticmethod
    def _run_id(payload: dict[str, Any]) -> int | None:
        return native_run_id(_pick(payload, "run_id"))

    @staticmethod
    def _metadata_task_for_trace(collector: Collector, trace: str, task_ref: Any) -> str | None:
        task = native_kanban_task_ref(task_ref)
        return task if task is not None and collector.binder.trace_for(task) == trace else None

    def _restore_launch_binding(self, collector: Collector) -> None:
        task_ref = native_kanban_task_ref(os.environ.get("HERMES_KANBAN_TASK"))
        if task_ref is not None:
            retained = _retained_binding(collector.paths, task_ref)
            if retained is not None:
                trace_id, relation = retained
                collector.binder.restore(task_ref=task_ref, trace_id=trace_id, relation=relation)
                collector.restore_materialized_trace(trace_id)
                self._activate_trace(collector, trace_id)
                return

        trace_id = safe_ref(os.environ.get("AETHER_OBSERVATION_TRACE_ID"))
        if (
            trace_id is not None
            and _TRACE_RE.fullmatch(trace_id)
            and _retained_trace_exists(collector.paths, trace_id)
        ):
            collector.restore_materialized_trace(trace_id)
            self._activate_trace(collector, trace_id)

    def _activate_trace(self, collector: Collector, trace_id: str) -> None:
        self._active_traces.add(trace_id)
        # Payloads without a task/session binding may use an implicit trace only
        # when exactly one trace is active.  Multiple live contracts are a real
        # ambiguity, never a reason to attach by recency.
        self._active_trace = (
            next(iter(self._active_traces)) if len(self._active_traces) == 1 else None
        )
        self._emit_compatibility_diagnostics(collector, trace_id)

    def _resolve_collector(self, payload: dict[str, Any]) -> Collector | None:
        """Resolve exact project context; ambiguity writes no project event."""
        raw_candidates = (
            _pick(payload, "aether_project_id"),
            _pick(payload, "hermes_project_id", "project_id"),
            os.environ.get("AETHER_PROJECT_ID"),
        )
        if self._collector is not None and not any(raw_candidates):
            return self._collector
        resolution = self._resolver.resolve(
            task_binding=raw_candidates[0],
            session_binding=raw_candidates[1],
            launch_binding=raw_candidates[2],
        )
        if self._collector is not None:
            if resolution.resolved and resolution.project_id == self._collector.paths.project_id:
                return self._collector
            self._collector.record_unresolved_context(
                resolution.reason_code or "PROJECT_CONTEXT_CHANGED"
            )
            return None
        if not resolution.resolved:
            return None
        assert resolution.project_id is not None
        collector = Collector(
            paths=ObservationPaths.for_project(resolution.project_id),
            runtime_fingerprint=self._runtime_fingerprint,
            normalizer_ref=self._normalizer_ref,
        )
        collector.start(getattr(self._ctx, "spawn_task", None))
        self._collector = collector
        self._restore_all_retained_bindings(collector)
        self._reconciler.start()
        return collector

    def _restore_all_retained_bindings(self, collector: Collector) -> None:
        if self._retained_restored:
            return
        for task_ref, (trace_id, relation) in _retained_bindings(collector.paths).items():
            collector.binder.restore(
                task_ref=task_ref,
                trace_id=trace_id,
                relation=relation,
            )
            collector.restore_materialized_trace(trace_id)
        self._retained_restored = True

    def _emit_compatibility_diagnostics(self, collector: Collector, trace_id: str) -> None:
        if trace_id in self._diagnosed_traces:
            return
        self._diagnosed_traces.add(trace_id)
        builder = collector.builder_for(trace_id)
        if self._registration_failures:
            collector.emit(
                builder.coverage_gap(
                    gap_class=CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    reason_code="HOOK_REGISTRATION_PARTIAL",
                )
            )
            for hook_name in sorted(self._registration_failures):
                collector.emit(
                    builder.coverage_gap(
                        gap_class=CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                        reason_code="HOOK_MISSING_" + hook_name.upper(),
                    )
                )
        if self._compatibility_missing:
            collector.emit(
                builder.coverage_gap(
                    gap_class=CoverageClass.COMPATIBILITY_MISMATCH,
                    reason_code="RUNTIME_FINGERPRINT_INCOMPLETE",
                )
            )
        if not self._native_normalizer:
            collector.emit(
                builder.coverage_gap(
                    gap_class=CoverageClass.COMPATIBILITY_MISMATCH,
                    reason_code="NATIVE_TOOL_CATEGORY_UNAVAILABLE",
                )
            )
        if self._runtime_fingerprint == NULL_RUNTIME_FINGERPRINT:
            collector.emit(
                builder.coverage_gap(
                    gap_class=CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    reason_code="RUNTIME_TREE_UNREADABLE",
                )
            )

    def note_hook_registration_failure(self, hook_name: str) -> None:
        """Retain only bounded capability absence, never exception text."""

        if hook_name in self._registration_failures:
            return
        self._registration_failures.add(hook_name)
        if self._collector is not None:
            self._collector.health.increment("HOOK_REGISTRATION_FAILED")

    def _trace_for_payload(
        self,
        collector: Collector,
        payload: dict[str, Any],
        *,
        diagnose: bool = True,
    ) -> str | None:
        raw_task_ref = _pick(payload, "task_id")
        if raw_task_ref is None:
            return self._active_trace
        task_ref = native_agent_task_ref(raw_task_ref)
        if task_ref is None:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_AGENT_TASK_ID_REJECTED",
                trace_id=self._active_trace,
            )
            return self._active_trace
        trace = collector.binder.trace_for(task_ref)
        if trace is not None:
            return trace
        collector.health.increment("TASK_BINDING_UNRESOLVED")
        if (
            diagnose
            and self._active_trace is not None
            and task_ref not in self._diagnosed_unbound_tasks
        ):
            if len(self._diagnosed_unbound_tasks) < 1024:
                self._diagnosed_unbound_tasks.add(task_ref)
            collector.emit(
                collector.builder_for(self._active_trace).coverage_gap(
                    gap_class=CoverageClass.RECONCILIATION_AMBIGUOUS,
                    reason_code="TASK_BINDING_UNRESOLVED",
                )
            )
        return None

    def _record_native_hook_rejection(
        self,
        collector: Collector,
        reason_code: str,
        *,
        trace_id: str | None = None,
    ) -> None:
        """Materialize one bounded native-ingress rejection without raw values."""
        target = trace_id or self._active_trace
        if target is None:
            collector.health.increment(reason_code)
            return
        key = (target, reason_code)
        if key in self._diagnosed_native_rejections:
            return
        collector.health.increment(reason_code)
        if len(self._diagnosed_native_rejections) < 1024:
            self._diagnosed_native_rejections.add(key)
        collector.emit(
            collector.builder_for(target).coverage_gap(
                gap_class=CoverageClass.FORBIDDEN_PAYLOAD_REJECTED,
                reason_code=reason_code,
            )
        )

    def _record_native_payload_identity_rejections(
        self,
        collector: Collector,
        hook: str,
        payload: dict[str, Any],
    ) -> None:
        """Check public-hook identity columns before any domain event is built.

        The diagnostics contain only fixed reason codes.  Values with no locked
        producer grammar (notably SessionDB IDs) still pass the structural guard
        here; their durable provenance is corroborated during reconciliation.
        """
        raw_task = _pick(payload, "task_id")
        task_validator = (
            native_kanban_task_ref if hook in _KANBAN_TASK_ID_HOOKS else native_agent_task_ref
        )
        task_ref = task_validator(raw_task) if raw_task not in (None, "") else None
        trace_id = (
            collector.binder.trace_for(task_ref) if task_ref is not None else self._active_trace
        )
        if raw_task not in (None, "") and task_ref is None:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_TASK_ID_REJECTED"
                if hook in _KANBAN_TASK_ID_HOOKS
                else "NATIVE_AGENT_TASK_ID_REJECTED",
                trace_id=trace_id,
            )

        raw_run = _pick(payload, "run_id")
        if raw_run not in (None, "") and native_run_id(raw_run) is None:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_RUN_ID_REJECTED",
                trace_id=trace_id,
            )

        for name in ("profile_name", "profile", "assignee"):
            raw_profile = payload.get(name)
            if raw_profile not in (None, "") and native_profile_ref(raw_profile) is None:
                self._record_native_hook_rejection(
                    collector,
                    "NATIVE_HERMES_PROFILE_ID_REJECTED",
                    trace_id=trace_id,
                )
                break

        for name in ("session_id", "parent_session_id", "child_session_id"):
            raw_session = payload.get(name)
            if raw_session not in (None, "") and safe_ref(raw_session, max_len=256) is None:
                self._record_native_hook_rejection(
                    collector,
                    "NATIVE_HERMES_SESSION_ID_REJECTED",
                    trace_id=trace_id,
                )
                break

        for name in ("turn_id", "parent_turn_id"):
            raw_turn = payload.get(name)
            if raw_turn not in (None, "") and safe_ref(raw_turn, max_len=256) is None:
                self._record_native_hook_rejection(
                    collector,
                    "NATIVE_HERMES_TURN_ID_REJECTED",
                    trace_id=trace_id,
                )
                break

        if hook in {"pre_api_request", "post_api_request", "api_request_error"}:
            raw_request = _pick(payload, "api_request_id", "request_id")
            if raw_request not in (None, "") and safe_ref(raw_request, max_len=256) is None:
                self._record_native_hook_rejection(
                    collector,
                    "NATIVE_HERMES_API_REQUEST_ID_REJECTED",
                    trace_id=trace_id,
                )

        if hook in {"pre_tool_call", "post_tool_call"}:
            raw_call = _pick(payload, "tool_call_id", "call_id")
            if raw_call not in (None, "") and safe_ref(raw_call, max_len=256) is None:
                self._record_native_hook_rejection(
                    collector,
                    "NATIVE_PROVIDER_TOOL_CALL_ID_REJECTED",
                    trace_id=trace_id,
                )

        if hook in {"pre_approval_request", "post_approval_response"}:
            raw_request = _pick(payload, "request_id", "request_digest")
            if raw_request not in (None, "") and safe_ref(raw_request, max_len=256) is None:
                self._record_native_hook_rejection(
                    collector,
                    "NATIVE_APPROVAL_REQUEST_ID_REJECTED",
                    trace_id=trace_id,
                )

    def _read_native_board(
        self, collector: Collector
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[str, tuple[str, ...]],
        dict[str, tuple[dict[str, Any], ...]],
        frozenset[tuple[str, int]],
        tuple[tuple[str, str | None, str | None], ...],
    ]:
        """Read and type-check the locked Kanban allowlist through a read-only handle.

        Rejections carry only a fixed reason plus an already-validated task/trace
        reference.  Raw native values never cross this function's return boundary.
        """
        from hermes_cli.kanban_db import kanban_db_path  # type: ignore[import-not-found]

        rejections: set[tuple[str, str | None, str | None]] = set()

        def reject(
            reason_code: str,
            *,
            task_ref: str | None = None,
            trace_id: str | None = None,
        ) -> None:
            collector.health.increment(reason_code)
            if len(rejections) < 1024:
                rejections.add((reason_code, task_ref, trace_id))

        path = kanban_db_path()
        if not path.is_file():
            return {}, {}, {}, frozenset(), ()
        connection = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=0.25,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            rows = connection.execute(
                "SELECT id, assignee, status, created_at, started_at, completed_at, "
                "project_id, idempotency_key, max_runtime_seconds, "
                "last_heartbeat_at, current_run_id, session_id "
                "FROM tasks WHERE project_id=? AND status!='archived'",
                (collector.paths.project_id,),
            ).fetchall()
            tasks: dict[str, dict[str, Any]] = {}
            session_candidates: set[str] = set()
            for row in rows:
                task_id = native_kanban_task_ref(row["id"])
                token_parts = parse_correlation_token(row["idempotency_key"])
                explicit_trace = (
                    token_parts[0]
                    if token_parts is not None and _TRACE_RE.fullmatch(token_parts[0])
                    else None
                )
                if task_id is None:
                    reject(
                        "NATIVE_KANBAN_TASK_ID_REJECTED",
                        trace_id=explicit_trace,
                    )
                    continue
                projected = dict(row)
                projected["id"] = task_id
                projected["idempotency_key"] = (
                    f"aether.obs.v1:{token_parts[0]}:{token_parts[1]}"
                    if token_parts is not None
                    else None
                )

                raw_profile = projected.get("assignee")
                profile = native_profile_ref(raw_profile)
                if raw_profile is not None and profile is None:
                    reject(
                        "NATIVE_HERMES_PROFILE_ID_REJECTED",
                        task_ref=task_id,
                        trace_id=explicit_trace,
                    )
                projected["assignee"] = profile

                raw_current_run = projected.get("current_run_id")
                current_run = native_run_id(raw_current_run)
                if raw_current_run is not None and current_run is None:
                    reject(
                        "NATIVE_KANBAN_RUN_ID_REJECTED",
                        task_ref=task_id,
                        trace_id=explicit_trace,
                    )
                projected["current_run_id"] = current_run

                raw_session = projected.get("session_id")
                session_id = safe_ref(raw_session, max_len=256)
                if raw_session is not None and session_id is None:
                    reject(
                        "NATIVE_HERMES_SESSION_ID_REJECTED",
                        task_ref=task_id,
                        trace_id=explicit_trace,
                    )
                projected["session_id"] = session_id
                if session_id is not None:
                    session_candidates.add(session_id)
                tasks[task_id] = projected
            if not tasks:
                return (
                    {},
                    {},
                    {},
                    frozenset(),
                    tuple(
                        sorted(
                            rejections,
                            key=lambda item: (item[0], item[1] or "", item[2] or ""),
                        )
                    ),
                )

            parents: dict[str, list[str]] = {task_id: [] for task_id in tasks}
            runs: dict[str, list[dict[str, Any]]] = {task_id: [] for task_id in tasks}
            protocol_violations: set[tuple[str, int]] = set()
            task_ids = sorted(tasks)
            for offset in range(0, len(task_ids), 400):
                chunk = task_ids[offset : offset + 400]
                marks = ",".join("?" for _ in chunk)
                for row in connection.execute(
                    f"SELECT parent_id, child_id FROM task_links "
                    f"WHERE child_id IN ({marks}) ORDER BY parent_id, child_id",
                    chunk,
                ):
                    parent = native_kanban_task_ref(row["parent_id"])
                    child = native_kanban_task_ref(row["child_id"])
                    if child not in parents:
                        reject("NATIVE_KANBAN_TASK_ID_REJECTED")
                    elif parent is None:
                        reject("NATIVE_KANBAN_PARENT_ID_REJECTED", task_ref=child)
                    elif parent not in tasks:
                        reject("NATIVE_KANBAN_PARENT_PROVENANCE_REJECTED", task_ref=child)
                    else:
                        parents[child].append(parent)
                for row in connection.execute(
                    "SELECT id, task_id, profile, status, max_runtime_seconds, "
                    "last_heartbeat_at, started_at, ended_at, outcome "
                    f"FROM task_runs WHERE task_id IN ({marks}) "
                    "ORDER BY task_id, started_at, id",
                    chunk,
                ):
                    task_id = native_kanban_task_ref(row["task_id"])
                    if task_id not in runs:
                        reject("NATIVE_KANBAN_TASK_ID_REJECTED")
                        continue
                    run_id = native_run_id(row["id"])
                    if run_id is None:
                        reject("NATIVE_KANBAN_RUN_ID_REJECTED", task_ref=task_id)
                        continue
                    projected_run = dict(row)
                    projected_run["id"] = run_id
                    raw_profile = projected_run.get("profile")
                    profile = native_profile_ref(raw_profile)
                    if raw_profile is not None and profile is None:
                        reject("NATIVE_HERMES_PROFILE_ID_REJECTED", task_ref=task_id)
                    projected_run["profile"] = profile
                    runs[task_id].append(projected_run)
                for row in connection.execute(
                    "SELECT task_id, run_id FROM task_events "
                    f"WHERE task_id IN ({marks}) AND kind='protocol_violation' "
                    "ORDER BY task_id, run_id, id",
                    chunk,
                ):
                    task_id = native_kanban_task_ref(row["task_id"])
                    run_id = native_run_id(row["run_id"])
                    if task_id not in runs:
                        reject("NATIVE_KANBAN_TASK_ID_REJECTED")
                    elif run_id is None:
                        reject("NATIVE_KANBAN_RUN_ID_REJECTED", task_ref=task_id)
                    elif any(run["id"] == run_id for run in runs[task_id]):
                        protocol_violations.add((task_id, run_id))

            verified_sessions, session_source_available = _verified_native_session_ids(
                session_candidates
            )
            for task_id, task in tasks.items():
                session_id = task.get("session_id")
                if session_id is not None and session_id not in verified_sessions:
                    reject(
                        "NATIVE_HERMES_SESSION_ID_REJECTED"
                        if session_source_available
                        else "NATIVE_HERMES_SESSION_PROVENANCE_UNAVAILABLE",
                        task_ref=task_id,
                    )
                    task["session_id"] = None
                elif isinstance(session_id, str):
                    self._reconcile_owner_candidate(
                        collector,
                        session_id,
                        _native_datetime(task.get("created_at")),
                    )
                    projected_session = self._pseudonymize_native_ref(
                        collector,
                        "session",
                        session_id,
                    )
                    if projected_session is None:
                        reject(
                            "NATIVE_HERMES_SESSION_PSEUDONYM_UNAVAILABLE",
                            task_ref=task_id,
                        )
                    task["session_id"] = projected_session
                current_run_id = task.get("current_run_id")
                if current_run_id is not None and not any(
                    run["id"] == current_run_id for run in runs[task_id]
                ):
                    reject("NATIVE_KANBAN_RUN_PROVENANCE_REJECTED", task_ref=task_id)
                    task["current_run_id"] = None
            return (
                tasks,
                {key: tuple(dict.fromkeys(value)) for key, value in parents.items()},
                {key: tuple(value) for key, value in runs.items()},
                frozenset(protocol_violations),
                tuple(
                    sorted(
                        rejections,
                        key=lambda item: (item[0], item[1] or "", item[2] or ""),
                    )
                ),
            )
        finally:
            connection.close()

    def _reconcile_owner_candidate(
        self,
        collector: Collector,
        session_id: str | None,
        materialized_at: datetime | None,
    ) -> None:
        """Recover an origin only when SessionDB yields exactly one candidate.

        The observer never selects the nearest of multiple user messages.  Content,
        reasoning, tool JSON, display metadata, and origin JSON are never selected.
        """
        if session_id is None or materialized_at is None:
            return
        try:
            from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

            path = get_hermes_home() / "state.db"
            with _open_verified_native_session_db(path) as connection:
                session = connection.execute(
                    "SELECT id, parent_session_id, profile_name, started_at, ended_at, "
                    "message_count, tool_call_count, input_tokens, output_tokens, "
                    "cache_read_tokens, cache_write_tokens, reasoning_tokens, "
                    "last_activity_at, last_activity_provenance "
                    "FROM sessions WHERE id=?",
                    (session_id,),
                ).fetchone()
                if session is None:
                    return
                candidates = connection.execute(
                    "SELECT id, timestamp FROM messages "
                    "WHERE session_id=? AND role='user' AND active=1 AND timestamp<=? "
                    "ORDER BY id LIMIT 2",
                    (session_id, materialized_at.timestamp()),
                ).fetchall()
        except Exception:
            collector.health.increment("SESSION_RECONCILIATION_FAILED")
            return
        if len(candidates) == 1:
            occurred_at = _native_datetime(candidates[0]["timestamp"])
            projected_session = self._pseudonymize_native_ref(
                collector,
                "session",
                session_id,
            )
            if occurred_at is not None and projected_session is not None:
                collector.candidates.observe(
                    projected_session,
                    int(candidates[0]["id"]),
                    occurred_at,
                )
        elif len(candidates) > 1:
            collector.health.increment("ORIGIN_MULTIPLE_CANDIDATES")

    @staticmethod
    def _native_run_terminal(run: dict[str, Any]) -> tuple[str, str, str]:
        raw_status = safe_ref(run.get("status")) or "unknown"
        raw_outcome = safe_ref(run.get("outcome"))
        run_status = (
            raw_status
            if raw_status
            in {
                "running",
                "done",
                "blocked",
                "crashed",
                "timed_out",
                "failed",
                "released",
                "rate_limited",
                "stale",
                "review_requested",
                "changes_requested",
                "scheduled",
            }
            else "unknown"
        )
        run_outcome = (
            raw_outcome
            if raw_outcome
            in {
                "completed",
                "blocked",
                "crashed",
                "timed_out",
                "failed",
                "spawn_failed",
                "gave_up",
                "reclaimed",
                "protocol_violation",
                "rate_limited",
                "stale",
                "review_requested",
                "changes_requested",
                "scheduled",
            }
            else "unknown"
        )
        status = run_outcome if run_outcome != "unknown" else run_status
        if status == "done":
            status = "completed"
        elif status == "protocol_violation":
            status = "failed"
        if status not in {
            "completed",
            "blocked",
            "crashed",
            "timed_out",
            "spawn_failed",
            "gave_up",
            "reclaimed",
            "failed",
            "released",
            "rate_limited",
            "stale",
            "review_requested",
            "changes_requested",
            "scheduled",
        }:
            status = "unknown"
        return status, run_status, run_outcome

    def _emit_native_once(
        self,
        collector: Collector,
        signature: tuple[Any, ...],
        event: dict[str, Any],
    ) -> bool:
        if signature in self._native_seen:
            return False
        outcome = collector.emit(event)
        if outcome.accepted:
            self._native_seen.add(signature)
            return True
        return False

    def _emit_native_rejections(
        self,
        collector: Collector,
        rejections: tuple[tuple[str, str | None, str | None], ...],
    ) -> None:
        """Attach content-free ingress failures only through explicit trace evidence."""
        for reason_code, task_ref, explicit_trace in rejections:
            candidates: set[str] = set()
            if task_ref is not None:
                bound = collector.binder.trace_for(task_ref)
                if bound is not None:
                    candidates.add(bound)
            if explicit_trace is not None and _retained_trace_exists(
                collector.paths, explicit_trace
            ):
                candidates.add(explicit_trace)
            if len(candidates) != 1:
                continue
            trace_id = candidates.pop()
            self._emit_native_once(
                collector,
                ("native_ingress_rejected", trace_id, reason_code, task_ref),
                collector.builder_for(trace_id).coverage_gap(
                    gap_class=CoverageClass.FORBIDDEN_PAYLOAD_REJECTED,
                    reason_code=reason_code,
                    source_hook="kanban_read",
                    monotonic=False,
                ),
            )

    def _reconcile_native(self) -> None:
        """Reconcile durable Kanban/SessionDB facts outside every hook callback."""
        collector = self._collector
        if collector is None:
            return
        try:
            (
                tasks,
                parents,
                runs_by_task,
                protocol_violations,
                native_rejections,
            ) = self._read_native_board(collector)
        except Exception:
            collector.health.increment("KANBAN_RECONCILIATION_FAILED")
            return
        if not tasks:
            self._emit_native_rejections(collector, native_rejections)
            return

        # Recover strict-token roots.  Hermes documents that idempotency keys are
        # not unique, so zero/multiple matches never bind by recency.
        token_groups: dict[tuple[str, str], list[str]] = {}
        for task_id, task in tasks.items():
            parsed = parse_correlation_token(task.get("idempotency_key"))
            if parsed is not None and _TRACE_RE.fullmatch(parsed[0]):
                token_groups.setdefault(parsed, []).append(task_id)

        live_root_traces: list[str] = []
        for token_parts, task_ids in sorted(token_groups.items()):
            trace_id, unit_ref = token_parts
            if len(task_ids) != 1:
                collector.health.increment("BINDING_TOKEN_REUSED")
                if _retained_trace_exists(collector.paths, trace_id):
                    builder = collector.builder_for(trace_id)
                    self._emit_native_once(
                        collector,
                        ("token_ambiguity", trace_id, unit_ref),
                        builder.coverage_gap(
                            gap_class=CoverageClass.RECONCILIATION_AMBIGUOUS,
                            reason_code="BINDING_TOKEN_REUSED",
                            source_kind="native_reconciliation",
                            source_hook="kanban_read",
                            monotonic=False,
                        ),
                    )
                continue
            task_id = task_ids[0]
            task = tasks[task_id]
            materialized_at = _native_datetime(task.get("created_at"))
            session_id = native_pseudonym_ref(task.get("session_id"), kind="session")
            if not collector.ensure_trace_opened(
                trace_id,
                session_lineage=(session_id,) if session_id else (),
                materialized_at=materialized_at,
                materialization_ref=binding_ref(trace_id, task_id),
                source_kind="native_reconciliation",
                source_hook="kanban_read",
            ):
                continue
            already = collector.binder.trace_for(task_id)
            decision = collector.binder.bind_root(
                trace_id=trace_id,
                task_ref=task_id,
                token=f"aether.obs.v1:{trace_id}:{unit_ref}",
                project_id=collector.paths.project_id,
            )
            if not decision.bound:
                collector.health.increment(decision.reason_code or "BINDING_UNRESOLVED")
                continue
            if already is None:
                builder = collector.builder_for(trace_id)
                self._emit_native_once(
                    collector,
                    ("binding", trace_id, task_id, "root"),
                    builder.work_unit(
                        event_type="work_unit.bound",
                        status="reported",
                        task_ref=task_id,
                        relation="root",
                        required=None,
                        binding=binding_ref(trace_id, task_id),
                        parent_task_refs=parents.get(task_id, ()),
                        task_status=safe_ref(task.get("status")) or "unknown",
                        occurred_at=materialized_at,
                        timestamp_source="native",
                        monotonic=False,
                        source_kind="native_reconciliation",
                        source_hook="kanban_read",
                        session_id=session_id,
                        actor_kind="agent",
                        actor_id=native_profile_ref(task.get("assignee")) or "unknown",
                        profile=native_profile_ref(task.get("assignee")),
                    ),
                )
            if task.get("status") not in ("done", "archived"):
                live_root_traces.append(trace_id)

        # Native descendants inherit only through durable parent edges. Iterate to
        # a fixed point so a newly seen multi-level subtree binds in one scan.
        changed = True
        while changed:
            changed = False
            for task_id in sorted(tasks):
                if collector.binder.trace_for(task_id) is not None:
                    continue
                parent_refs = parents.get(task_id, ())
                if not parent_refs:
                    continue
                decision = collector.binder.inherit(
                    task_ref=task_id,
                    parent_task_refs=parent_refs,
                    relation="unknown",
                    project_id=collector.paths.project_id,
                )
                if not decision.bound or decision.trace_id is None:
                    continue
                changed = True
                task = tasks[task_id]
                builder = collector.builder_for(decision.trace_id)
                self._emit_native_once(
                    collector,
                    ("binding", decision.trace_id, task_id, "other"),
                    builder.work_unit(
                        event_type="work_unit.bound",
                        status="reported",
                        task_ref=task_id,
                        relation="unknown",
                        required=None,
                        binding=decision.binding or binding_ref(decision.trace_id, task_id),
                        parent_task_refs=decision.parent_task_refs,
                        task_status=safe_ref(task.get("status")) or "unknown",
                        occurred_at=_native_datetime(task.get("created_at")),
                        timestamp_source="native",
                        monotonic=False,
                        source_kind="native_reconciliation",
                        source_hook="kanban_read",
                        session_id=native_pseudonym_ref(task.get("session_id"), kind="session"),
                        actor_kind="agent",
                        actor_id=native_profile_ref(task.get("assignee")) or "unknown",
                        profile=native_profile_ref(task.get("assignee")),
                    ),
                )

        self._emit_native_rejections(collector, native_rejections)

        # Reconstruct every bound run attempt plus the latest task/heartbeat state.
        for task_id in sorted(tasks):
            trace_id = collector.binder.trace_for(task_id)
            if trace_id is None:
                continue
            task = tasks[task_id]
            task_runs = runs_by_task.get(task_id, ())
            relation = "root" if collector.binder.root_for(trace_id) == task_id else "unknown"
            profile = native_profile_ref(task.get("assignee"))
            builder = collector.builder_for(trace_id)
            for run in task_runs:
                run_id = run.get("id")
                if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
                    continue
                run_profile = native_profile_ref(run.get("profile")) or profile
                started_at = _native_datetime(run.get("started_at"))
                self._emit_native_once(
                    collector,
                    ("run", trace_id, run_id, "started"),
                    builder.work_unit(
                        event_type="run.started",
                        status="started",
                        task_ref=task_id,
                        relation=relation,
                        required=None,
                        binding=binding_ref(trace_id, task_id),
                        parent_task_refs=parents.get(task_id, ()),
                        task_status=safe_ref(task.get("status")) or "unknown",
                        run_status="running",
                        occurred_at=started_at,
                        timestamp_source="native",
                        monotonic=False,
                        source_kind="native_reconciliation",
                        source_hook="kanban_read",
                        run_id=run_id,
                        session_id=native_pseudonym_ref(task.get("session_id"), kind="session"),
                        actor_kind="agent",
                        actor_id=run_profile or "unknown",
                        profile=run_profile,
                    ),
                )
                ended_at = _native_datetime(run.get("ended_at"))
                if ended_at is not None:
                    status, run_status, run_outcome = self._native_run_terminal(run)
                    if (task_id, run_id) in protocol_violations:
                        status = "failed"
                        run_status = "failed"
                        run_outcome = "protocol_violation"
                    self._emit_native_once(
                        collector,
                        ("run", trace_id, run_id, "finished", status),
                        builder.work_unit(
                            event_type="run.finished",
                            status=status,
                            task_ref=task_id,
                            relation=relation,
                            required=None,
                            binding=binding_ref(trace_id, task_id),
                            parent_task_refs=parents.get(task_id, ()),
                            task_status=safe_ref(task.get("status")) or "unknown",
                            run_status=run_status,
                            run_outcome=run_outcome,
                            occurred_at=ended_at,
                            timestamp_source="native",
                            monotonic=False,
                            source_kind="native_reconciliation",
                            source_hook="kanban_read",
                            run_id=run_id,
                            session_id=native_pseudonym_ref(task.get("session_id"), kind="session"),
                            actor_kind="agent",
                            actor_id=run_profile or "unknown",
                            profile=run_profile,
                        ),
                    )

            latest = task_runs[-1] if task_runs else None
            current_run_id = task.get("current_run_id")
            if not isinstance(current_run_id, int) and latest is not None:
                current_run_id = latest.get("id")
            run_status = safe_ref(latest.get("status")) if latest is not None else None
            run_status = (
                run_status
                if run_status
                in {
                    "running",
                    "done",
                    "blocked",
                    "crashed",
                    "timed_out",
                    "failed",
                    "released",
                    "rate_limited",
                    "stale",
                    "review_requested",
                    "changes_requested",
                    "scheduled",
                }
                else None
            )
            raw_outcome = safe_ref(latest.get("outcome")) if latest is not None else None
            run_outcome = (
                raw_outcome
                if raw_outcome
                in {
                    "completed",
                    "blocked",
                    "crashed",
                    "timed_out",
                    "spawn_failed",
                    "gave_up",
                    "reclaimed",
                    "rate_limited",
                    "stale",
                    "review_requested",
                    "changes_requested",
                    "scheduled",
                }
                else None
            )
            task_status = safe_ref(task.get("status")) or "unknown"
            occurred_at = _native_datetime(
                task.get("completed_at")
                if task_status == "done"
                else task.get("last_heartbeat_at")
                if task_status == "running"
                else (latest or {}).get("ended_at")
                if latest is not None
                else task.get("started_at") or task.get("created_at")
            )
            event_status = {
                "done": "completed",
                "running": "started",
                "blocked": "blocked",
            }.get(task_status, "reported")
            state_event = builder.work_unit(
                event_type="work_unit.status",
                status=event_status,
                task_ref=task_id,
                relation=relation,
                required=None,
                binding=binding_ref(trace_id, task_id),
                parent_task_refs=parents.get(task_id, ()),
                task_status=task_status,
                run_status=run_status,
                run_outcome=run_outcome,
                occurred_at=occurred_at,
                timestamp_source="native",
                monotonic=False,
                source_kind="native_reconciliation",
                source_hook="kanban_read",
                run_id=current_run_id,
                session_id=native_pseudonym_ref(task.get("session_id"), kind="session"),
                actor_kind="agent",
                actor_id=profile or "unknown",
                profile=profile,
            )
            self._emit_native_once(
                collector,
                (
                    "task_state",
                    trace_id,
                    task_id,
                    current_run_id,
                    task_status,
                    run_status,
                    run_outcome,
                    state_event.get("occurred_at"),
                ),
                state_event,
            )

        current_task = native_kanban_task_ref(os.environ.get("HERMES_KANBAN_TASK"))
        if current_task is not None:
            current_trace = collector.binder.trace_for(current_task)
            if current_trace is not None:
                self._activate_trace(collector, current_trace)
        elif self._active_trace is None and len(set(live_root_traces)) == 1:
            self._activate_trace(collector, live_root_traces[0])

    def dispatch(self, hook: str, payload: dict[str, Any]) -> None:
        """Dispatch one public hook and always return no directive."""
        if observing():
            if self._collector is not None:
                self._collector.stats.reentrant_skips += 1
            return
        handler = getattr(self, f"_on_{hook}", None)
        if handler is None:
            return
        collector = self._resolve_collector(payload)
        if collector is not None:
            self._record_native_payload_identity_rejections(collector, hook, payload)
            handler(collector, payload)
            if hook in _RECONCILIATION_HOOKS:
                self._reconciler.schedule()

    # -- tools and root binding -------------------------------------------------
    def _tool_metadata(
        self,
        collector: Collector,
        payload: dict[str, Any],
        key: tuple[str, str],
        name: str,
    ) -> dict[str, Any]:
        return {
            "call_id": key[1],
            "name": name,
            "category": self._category(name),
            "session_id": key[0] or None,
            "turn_id": self._turn(collector, payload),
            "api_request_id": self._api_request(collector, payload),
            "task_id": native_agent_task_ref(_pick(payload, "task_id")),
            "profile": self._profile(payload),
            "occurred_at": datetime.now(timezone.utc),
            "event_id": None,
            "trace_id": None,
        }

    def _trace_for_create(self, collector: Collector, projection: dict[str, Any]) -> str | None:
        parent_traces = {
            trace
            for parent in projection["parents"]
            if (trace := collector.binder.trace_for(parent)) is not None
        }
        if len(parent_traces) == 1:
            return next(iter(parent_traces))
        token_parts = projection.get("token_parts")
        if token_parts is not None and _TRACE_RE.fullmatch(token_parts[0]):
            return self._active_trace if self._active_trace in (None, token_parts[0]) else None
        return self._active_trace

    def _emit_tool_start(self, collector: Collector, trace: str, metadata: dict[str, Any]) -> None:
        event = collector.builder_for(trace).tool_started(
            call_id=metadata["call_id"],
            name=metadata["name"],
            category=metadata["category"],
            occurred_at=metadata.get("occurred_at"),
            session_id=metadata.get("session_id"),
            turn_id=metadata.get("turn_id"),
            api_request_id=metadata.get("api_request_id"),
            task_id=self._metadata_task_for_trace(collector, trace, metadata.get("task_id")),
            actor_kind="agent",
            actor_id=metadata.get("profile") or "unknown",
            profile=metadata.get("profile"),
        )
        outcome = collector.emit(event)
        if outcome.accepted:
            metadata["event_id"] = event["event_id"]
            metadata["trace_id"] = trace

    def _emit_tool_terminal(
        self,
        collector: Collector,
        trace: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        status, recognized = normalize_native_status(_pick(payload, "status", "outcome"))
        builder = collector.builder_for(trace)
        collector.emit(
            builder.tool_terminal(
                call_id=metadata["call_id"],
                name=metadata["name"],
                category=metadata["category"],
                status=status,
                duration_ms=_duration_ms(payload),
                error_class=safe_error_class(_structured_error_type(payload)),
                session_id=metadata.get("session_id"),
                turn_id=metadata.get("turn_id"),
                api_request_id=metadata.get("api_request_id"),
                task_id=self._metadata_task_for_trace(collector, trace, metadata.get("task_id")),
                parent_event_id=metadata.get("event_id"),
                actor_kind="agent",
                actor_id=metadata.get("profile") or "unknown",
                profile=metadata.get("profile"),
            )
        )
        if not recognized:
            collector.emit(
                builder.coverage_gap(
                    gap_class=CoverageClass.COMPATIBILITY_MISMATCH,
                    reason_code="UNKNOWN_NATIVE_TOOL_STATUS",
                )
            )

    def _on_pre_tool_call(self, collector: Collector, payload: dict[str, Any]) -> None:
        key = self._call_key(collector, payload)
        name = safe_ref(_pick(payload, "tool_name", "name"))
        if key is None or name is None:
            return
        metadata = self._tool_metadata(collector, payload, key, name)
        is_create = "kanban_create" in name
        projection = _safe_create_projection(payload) if is_create else None
        trace = (
            self._trace_for_create(collector, projection)
            if projection is not None
            else self._trace_for_payload(collector, payload)
        )
        if trace is not None:
            self._emit_tool_start(collector, trace, metadata)
        elif not is_create:
            return
        self._bounded_put(self._pending_spans, key, metadata, collector)

    def _on_post_tool_call(self, collector: Collector, payload: dict[str, Any]) -> None:
        key = self._call_key(collector, payload)
        name = safe_ref(_pick(payload, "tool_name", "name"))
        if key is None or name is None:
            return
        pending = self._pending_spans.pop(key, None)
        if "kanban_create" in name:
            self._finish_create_call(collector, payload, key, name, pending)
            return
        trace = (
            pending.get("trace_id")
            if pending is not None and isinstance(pending.get("trace_id"), str)
            else self._trace_for_payload(collector, payload)
        )
        if isinstance(trace, str):
            self._emit_tool_terminal(
                collector,
                trace,
                payload,
                pending or self._tool_metadata(collector, payload, key, name),
            )

    def _finish_create_call(
        self,
        collector: Collector,
        payload: dict[str, Any],
        key: tuple[str, str],
        name: str,
        pending: dict[str, Any] | None,
    ) -> None:
        projection = _safe_create_projection(payload)
        status, _ = normalize_native_status(_pick(payload, "status", "outcome"))
        rejection_trace = (
            pending.get("trace_id")
            if pending is not None and isinstance(pending.get("trace_id"), str)
            else self._active_trace
        )
        if projection["task_id_rejected"]:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_TASK_ID_REJECTED",
                trace_id=rejection_trace,
            )
        if projection["parent_ids_rejected"]:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_PARENT_ID_REJECTED",
                trace_id=rejection_trace,
            )
        successful = (
            projection["task_ref"] is not None
            and not projection["parent_ids_rejected"]
            and projection["ok"]
            and status == "completed"
        )
        if not successful:
            trace = (
                pending.get("trace_id")
                if pending is not None and isinstance(pending.get("trace_id"), str)
                else self._active_trace
            )
            if isinstance(trace, str):
                self._emit_tool_terminal(
                    collector,
                    trace,
                    payload,
                    pending or self._tool_metadata(collector, payload, key, name),
                )
            return

        task_ref = projection["task_ref"]
        parents = projection["parents"]
        token_parts = projection["token_parts"]
        candidate_trace: str | None = None
        if parents:
            parent_traces = {
                trace
                for parent in parents
                if (trace := collector.binder.trace_for(parent)) is not None
            }
            if len(parent_traces) == 1:
                candidate_trace = next(iter(parent_traces))
        elif token_parts is not None and _TRACE_RE.fullmatch(token_parts[0]):
            candidate_trace = token_parts[0]
        else:
            candidate_trace = self._active_trace

        result_project = canonical_project_id(projection.get("project_id"))
        project_id = result_project or collector.paths.project_id
        if candidate_trace is not None and candidate_trace != self._active_trace:
            if not collector.ensure_trace_opened(
                candidate_trace,
                session_lineage=(key[0],) if key[0] else (),
                materialized_at=datetime.now(timezone.utc),
                materialization_ref=binding_ref(candidate_trace, task_ref),
                source_kind="hermes_hook",
                source_hook="post_tool_call",
            ):
                candidate_trace = None

        if parents:
            decision = collector.binder.inherit(
                task_ref=task_ref,
                parent_task_refs=parents,
                relation="unknown",
                project_id=project_id,
            )
        elif candidate_trace is not None:
            decision = collector.binder.bind_root(
                trace_id=candidate_trace,
                task_ref=task_ref,
                token=projection["token"],
                project_id=project_id,
            )
        else:
            decision = None

        trace = decision.trace_id if decision is not None and decision.bound else None
        if trace is None:
            diagnostic_trace = (
                pending.get("trace_id")
                if pending is not None and isinstance(pending.get("trace_id"), str)
                else self._active_trace
            )
            reason = decision.reason_code if decision is not None else "BINDING_NO_TRACE_CONTEXT"
            collector.health.increment(reason or "BINDING_UNRESOLVED")
            if isinstance(diagnostic_trace, str):
                collector.emit(
                    collector.builder_for(diagnostic_trace).coverage_gap(
                        gap_class=CoverageClass.RECONCILIATION_AMBIGUOUS,
                        reason_code=reason or "BINDING_UNRESOLVED",
                    )
                )
                self._emit_tool_terminal(
                    collector,
                    diagnostic_trace,
                    payload,
                    pending or self._tool_metadata(collector, payload, key, name),
                )
            return

        self._activate_trace(collector, trace)
        metadata = pending or self._tool_metadata(collector, payload, key, name)
        if pending is not None and metadata.get("trace_id") != trace:
            metadata["event_id"] = None
            metadata["trace_id"] = None
            self._emit_tool_start(collector, trace, metadata)
        self._emit_tool_terminal(collector, trace, payload, metadata)
        assert decision is not None and decision.task_ref is not None
        collector.emit(
            collector.builder_for(trace).work_unit(
                event_type="work_unit.bound",
                status="reported",
                task_ref=decision.task_ref,
                relation=decision.relation,
                required=None,
                binding=decision.binding or binding_ref(trace, decision.task_ref),
                parent_task_refs=decision.parent_task_refs,
                source_hook="post_tool_call",
                session_id=key[0] or None,
                actor_kind="agent",
                actor_id=self._profile(payload) or "unknown",
                profile=self._profile(payload),
            )
        )

    # -- model/configuration ----------------------------------------------------
    def _on_pre_api_request(self, collector: Collector, payload: dict[str, Any]) -> None:
        key = self._model_key(collector, payload)
        trace = self._trace_for_payload(collector, payload)
        if key is None or trace is None:
            return
        started_at = _native_datetime(_pick(payload, "started_at"))
        attempt = self._attempt_count(payload)
        profile = self._profile(payload)
        builder = collector.builder_for(trace)
        event = builder.model_request(
            state="started",
            request_ref=key[1],
            model=_pick(payload, "model"),
            provider=_pick(payload, "provider"),
            started_at=started_at,
            message_count=_pick(payload, "message_count"),
            tool_count=_pick(payload, "tool_count"),
            attempt_count=attempt,
            usage_coverage="unavailable",
            source_hook="pre_api_request",
            occurred_at=started_at,
            timestamp_source="native" if started_at is not None else "collector",
            session_id=key[0] or None,
            turn_id=self._turn(collector, payload),
            api_request_id=key[1],
            task_id=native_agent_task_ref(_pick(payload, "task_id")),
            actor_kind="agent",
            actor_id=profile or "unknown",
            profile=profile,
        )
        outcome = collector.emit(event)
        pending = {
            "trace_id": trace,
            "event_id": event["event_id"] if outcome.accepted else None,
            "attempt_count": attempt,
            "started_at": started_at,
            "model": opaque_ref(_pick(payload, "model")),
            "provider": opaque_ref(_pick(payload, "provider")),
            "message_count": _pick(payload, "message_count"),
            "tool_count": _pick(payload, "tool_count"),
            "task_id": native_agent_task_ref(_pick(payload, "task_id")),
            "turn_id": self._turn(collector, payload),
            "profile": profile,
        }
        self._bounded_put(self._pending_models, key, pending, collector)
        self._emit_request_configuration(collector, trace, key[1], payload, event["event_id"])

    def _emit_request_configuration(
        self,
        collector: Collector,
        trace: str,
        request_ref: str,
        payload: dict[str, Any],
        parent_event_id: str,
    ) -> None:
        builder = collector.builder_for(trace)
        if not collector.fingerprint_key_ready:
            collector.emit(
                builder.coverage_gap(
                    gap_class=CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    reason_code="FINGERPRINT_KEY_UNAVAILABLE",
                    parent_event_id=parent_event_id,
                )
            )
            return
        collector.record_fingerprint_epoch_boundary(trace, parent_event_id=parent_event_id)
        model = opaque_ref(_pick(payload, "model"))
        provider = opaque_ref(_pick(payload, "provider"))
        prompt = payload.get("system_prompt")
        prompt_fp = (
            collector.keyring.fingerprint("system_prompt", prompt)
            if isinstance(prompt, str)
            else None
        )
        raw_tool_count = _pick(payload, "tool_count")
        has_tool_count = (
            isinstance(raw_tool_count, int)
            and not isinstance(raw_tool_count, bool)
            and raw_tool_count >= 0
        )
        coverage = {
            "model": "exact" if model is not None else "unavailable",
            "provider": "exact" if provider is not None else "unavailable",
            "prompt_fingerprint": "exact" if prompt_fp is not None else "unavailable",
            "observed_skills": "unavailable",
            "declared_toolset": "unavailable",
            "effective_tool_surface": "partial" if has_tool_count else "unavailable",
            "global_concurrency": "unavailable",
            "per_profile_concurrency": "unavailable",
        }
        fields = {
            "scope": "request",
            "model": model,
            "provider": provider,
            "system_prompt_fingerprint": prompt_fp,
            "field_coverage": coverage,
            "observer_version": COLLECTOR_VERSION,
            "fingerprint_key_id": collector.keyring.key_id,
            "runtime_fingerprint": self._runtime_fingerprint,
        }
        common = {
            "parent_event_id": parent_event_id,
            "source_hook": "pre_api_request",
            "session_id": self._session(collector, payload) or None,
            "api_request_id": request_ref,
            "task_id": native_agent_task_ref(_pick(payload, "task_id")),
            "actor_kind": "agent",
            "actor_id": self._profile(payload) or "unknown",
            "profile": self._profile(payload),
        }
        profile = self._profile(payload)
        for scope, participant_ref in (
            ("trace", None),
            ("participant", profile),
        ):
            if scope == "participant" and participant_ref is None:
                continue
            scoped_fields = {
                **fields,
                "scope": scope,
                "participant_ref": participant_ref,
            }
            fingerprint_id = configuration_fingerprint_id(scoped_fields)
            cache_key = (trace, fingerprint_id)
            if cache_key in self._configuration_seen:
                continue
            outcome = collector.emit(
                builder.configuration(
                    fingerprint_id=fingerprint_id,
                    scope=scope,
                    participant_ref=participant_ref,
                    fingerprint_key_id=collector.keyring.key_id,
                    observer_version=COLLECTOR_VERSION,
                    field_coverage=coverage,
                    model=model,
                    provider=provider,
                    system_prompt_fingerprint=prompt_fp,
                    **common,
                )
            )
            if outcome.accepted:
                self._configuration_seen.add(cache_key)
        collector.emit(
            builder.tool_surface(
                request_ref=request_ref,
                completeness="partial" if has_tool_count else "unavailable",
                fingerprint_key_id=collector.keyring.key_id,
                observed_tool_count=raw_tool_count,
                **common,
            )
        )

    def _on_post_api_request(self, collector: Collector, payload: dict[str, Any]) -> None:
        key = self._model_key(collector, payload)
        if key is None:
            return
        pending = self._pending_models.pop(key, None)
        trace = (
            pending.get("trace_id")
            if pending is not None
            else self._trace_for_payload(collector, payload)
        )
        if not isinstance(trace, str):
            return
        usage = payload.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        tokens = {
            name: usage.get(name)
            for name in (
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "reasoning_tokens",
                "total_tokens",
            )
        }
        if tokens["input_tokens"] is None:
            tokens["input_tokens"] = usage.get("prompt_tokens")
        present = [
            value
            for value in tokens.values()
            if isinstance(value, int) and not isinstance(value, bool)
        ]
        coverage = "exact" if len(present) >= 2 else ("partial" if present else "unavailable")
        started_at = _native_datetime(_pick(payload, "started_at")) or (
            pending.get("started_at") if pending is not None else None
        )
        ended_at = _native_datetime(_pick(payload, "ended_at"))
        profile = self._profile(payload) or (pending.get("profile") if pending else None)
        collector.emit(
            collector.builder_for(trace).model_request(
                state="completed",
                request_ref=key[1],
                model=_coalesce(_pick(payload, "model"), pending.get("model") if pending else None),
                provider=_coalesce(
                    _pick(payload, "provider"), pending.get("provider") if pending else None
                ),
                response_model=_pick(payload, "response_model"),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=_duration_ms(payload),
                finish_reason=_pick(payload, "finish_reason"),
                message_count=_coalesce(
                    _pick(payload, "message_count"),
                    pending.get("message_count") if pending else None,
                ),
                tool_count=_coalesce(
                    _pick(payload, "tool_count"),
                    pending.get("tool_count") if pending else None,
                ),
                attempt_count=self._attempt_count(
                    payload, pending.get("attempt_count", 1) if pending else 1
                ),
                tokens=tokens,
                usage_coverage=coverage,
                occurred_at=ended_at,
                timestamp_source="native" if ended_at is not None else "collector",
                session_id=key[0] or None,
                turn_id=self._turn(collector, payload)
                or (pending.get("turn_id") if pending else None),
                api_request_id=key[1],
                task_id=native_agent_task_ref(_pick(payload, "task_id"))
                or (pending.get("task_id") if pending else None),
                parent_event_id=pending.get("event_id") if pending else None,
                actor_kind="agent",
                actor_id=profile or "unknown",
                profile=profile,
            )
        )

    def _on_api_request_error(self, collector: Collector, payload: dict[str, Any]) -> None:
        key = self._model_key(collector, payload)
        if key is None:
            return
        pending = self._pending_models.pop(key, None)
        trace = (
            pending.get("trace_id")
            if pending is not None
            else self._trace_for_payload(collector, payload)
        )
        if not isinstance(trace, str):
            return
        started_at = _native_datetime(_pick(payload, "started_at")) or (
            pending.get("started_at") if pending is not None else None
        )
        ended_at = _native_datetime(_pick(payload, "ended_at"))
        profile = self._profile(payload) or (pending.get("profile") if pending else None)
        collector.emit(
            collector.builder_for(trace).model_request(
                state="failed",
                request_ref=key[1],
                model=_coalesce(_pick(payload, "model"), pending.get("model") if pending else None),
                provider=_coalesce(
                    _pick(payload, "provider"), pending.get("provider") if pending else None
                ),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=_duration_ms(payload),
                attempt_count=self._attempt_count(
                    payload, pending.get("attempt_count", 1) if pending else 1
                ),
                structured_reason_code=safe_error_class(_structured_error_type(payload)),
                usage_coverage="unavailable",
                occurred_at=ended_at,
                timestamp_source="native" if ended_at is not None else "collector",
                session_id=key[0] or None,
                turn_id=self._turn(collector, payload)
                or (pending.get("turn_id") if pending else None),
                api_request_id=key[1],
                task_id=native_agent_task_ref(_pick(payload, "task_id"))
                or (pending.get("task_id") if pending else None),
                parent_event_id=pending.get("event_id") if pending else None,
                actor_kind="agent",
                actor_id=profile or "unknown",
                profile=profile,
            )
        )

    # -- approval waits --------------------------------------------------------
    def _approval_wait_id(self, collector: Collector, payload: dict[str, Any]) -> str | None:
        request_id = _pick(payload, "request_id", "request_digest")
        if request_id in (None, ""):
            request_id = canonical_digest(
                {
                    "session": self._session(collector, payload),
                    "turn": self._turn(collector, payload),
                    "call": self._pseudonymize_native_ref(
                        collector,
                        "tool_call",
                        _pick(payload, "tool_call_id", "call_id"),
                    ),
                    "pattern": safe_ref(_pick(payload, "pattern_key"), max_len=256),
                    "surface": safe_ref(_pick(payload, "surface")),
                }
            )
        return self._pseudonymize_native_ref(
            collector,
            "approval_request",
            request_id,
        )

    def _on_pre_approval_request(self, collector: Collector, payload: dict[str, Any]) -> None:
        trace = self._trace_for_payload(collector, payload)
        if trace is None:
            return
        wait_id = self._approval_wait_id(collector, payload)
        if wait_id is None:
            return
        event = collector.builder_for(trace).wait(
            started=True,
            wait_id=wait_id,
            kind="approval",
            source_hook="pre_approval_request",
            session_id=self._session(collector, payload) or None,
            turn_id=self._turn(collector, payload),
            actor_kind="owner",
            actor_id="approval",
            identity=native_identity(kind="approval.wait", wait=wait_id, phase="started"),
        )
        outcome = collector.emit(event)
        self._bounded_put(
            self._pending_approvals,
            wait_id,
            {
                "trace_id": trace,
                "event_id": event["event_id"] if outcome.accepted else None,
            },
            collector,
        )

    def _on_post_approval_response(self, collector: Collector, payload: dict[str, Any]) -> None:
        wait_id = self._approval_wait_id(collector, payload)
        if wait_id is None:
            return
        pending = self._pending_approvals.pop(wait_id, None)
        trace = (
            pending.get("trace_id")
            if pending is not None
            else self._trace_for_payload(collector, payload)
        )
        if not isinstance(trace, str):
            return
        builder = collector.builder_for(trace)
        ended = builder.wait(
            started=False,
            wait_id=wait_id,
            kind="approval",
            source_hook="post_approval_response",
            parent_event_id=pending.get("event_id") if pending else None,
            session_id=self._session(collector, payload) or None,
            turn_id=self._turn(collector, payload),
            actor_kind="owner",
            actor_id="approval",
            identity=native_identity(kind="approval.wait", wait=wait_id, phase="ended"),
        )
        ended_outcome = collector.emit(ended)

        # The locked public hook exposes a bounded decision enum. A denial is one of
        # the two native facts OBS-FR-062 permits to establish policy_denial; command,
        # description, session key, and pattern text are deliberately discarded.
        choice = _pick(payload, "choice")
        if choice in ("deny", "smart_deny"):
            evidence = tuple(
                ref
                for ref in (
                    pending.get("event_id") if pending else None,
                    ended["event_id"] if ended_outcome.accepted else None,
                )
                if isinstance(ref, str)
            )
            # Attribution requires durable evidence.  If both wait observations
            # failed open, the collector has already emitted a coverage diagnostic
            # and must not persist an unsupported derived fact.
            if not evidence:
                return
            collector.emit(
                builder.attribution(
                    kind="defect",
                    attribution_class="policy_denial",
                    provenance="native_observed",
                    evidence_refs=evidence,
                    source_hook="post_approval_response",
                    session_id=self._session(collector, payload) or None,
                    turn_id=self._turn(collector, payload),
                    actor_kind="system" if choice == "smart_deny" else "owner",
                    actor_id="approval",
                    parent_event_id=(ended["event_id"] if ended_outcome.accepted else evidence[-1]),
                    identity=native_identity(kind="approval.denied", wait=wait_id, choice=choice),
                )
            )

    # -- Kanban graph ----------------------------------------------------------
    def _work_unit_transition(
        self,
        collector: Collector,
        payload: dict[str, Any],
        *,
        source_hook: str,
        event_type: str,
        status: str,
        task_status: str | None = None,
        run_status: str | None = None,
        run_outcome: str | None = None,
    ) -> None:
        task_ref = native_kanban_task_ref(_pick(payload, "task_id"))
        if task_ref is None:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_TASK_ID_REJECTED",
            )
            return
        trace = collector.binder.trace_for(task_ref)
        if trace is None:
            self._trace_for_payload(collector, payload)
            return
        raw_run_id = _pick(payload, "run_id")
        run_id = native_run_id(raw_run_id)
        if event_type in ("run.started", "run.finished") and run_id is None:
            if raw_run_id is None:
                collector.emit(
                    collector.builder_for(trace).coverage_gap(
                        gap_class=CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                        reason_code="RUN_ID_UNAVAILABLE",
                    )
                )
            return
        raw_parents = _pick(payload, "parent_task_ids")
        parent_values = raw_parents if isinstance(raw_parents, (list, tuple)) else ()
        parents = tuple(
            ref for item in parent_values if (ref := native_kanban_task_ref(item)) is not None
        )
        if len(parents) != len(parent_values):
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_PARENT_ID_REJECTED",
                trace_id=trace,
            )
        profile = self._profile(payload)
        collector.emit(
            collector.builder_for(trace).work_unit(
                event_type=event_type,
                status=status,
                task_ref=task_ref,
                relation="unknown",
                required=None,
                binding=binding_ref(trace, task_ref),
                parent_task_refs=tuple(dict.fromkeys(parents)),
                task_status=task_status,
                run_status=run_status,
                run_outcome=run_outcome,
                run_id=run_id,
                source_hook=source_hook,
                session_id=self._session(collector, payload) or None,
                actor_kind="agent",
                actor_id=profile or native_profile_ref(_pick(payload, "assignee")) or "unknown",
                profile=profile,
            )
        )

    def _on_kanban_task_claimed(self, collector: Collector, payload: dict[str, Any]) -> None:
        self._work_unit_transition(
            collector,
            payload,
            source_hook="kanban_task_claimed",
            event_type="work_unit.status",
            status="started",
            task_status="running",
            run_status="running",
        )

    def _on_kanban_task_completed(self, collector: Collector, payload: dict[str, Any]) -> None:
        self._work_unit_transition(
            collector,
            payload,
            source_hook="kanban_task_completed",
            event_type="work_unit.status",
            status="completed",
            task_status="done",
            run_status="done",
            run_outcome="completed",
        )

    def _on_kanban_task_blocked(self, collector: Collector, payload: dict[str, Any]) -> None:
        self._work_unit_transition(
            collector,
            payload,
            source_hook="kanban_task_blocked",
            event_type="work_unit.status",
            status="blocked",
            task_status="blocked",
            run_status="blocked",
            run_outcome="blocked",
        )

    def _on_on_kanban_worker_spawned(self, collector: Collector, payload: dict[str, Any]) -> None:
        self._work_unit_transition(
            collector,
            payload,
            source_hook="on_kanban_worker_spawned",
            event_type="run.started",
            status="started",
            run_status="running",
        )

    def _on_on_kanban_worker_exited(self, collector: Collector, payload: dict[str, Any]) -> None:
        native = _pick(payload, "outcome", "status")
        status, recognized = normalize_native_status(native)
        if native == "rate_limited":
            status = "released"
        elif not recognized:
            status = "unknown"
        run_outcome = (
            native if native in RUN_OUTCOMES else status if status in RUN_OUTCOMES else "unknown"
        )
        run_status = (
            native
            if native in RUN_STATUSES
            else "done"
            if run_outcome == "completed"
            else status
            if status in RUN_STATUSES
            else "unknown"
        )
        self._work_unit_transition(
            collector,
            payload,
            source_hook="on_kanban_worker_exited",
            event_type="run.finished",
            status=status,
            run_status=run_status,
            run_outcome=run_outcome,
        )

    def _on_on_kanban_worker_stale_claim(
        self, collector: Collector, payload: dict[str, Any]
    ) -> None:
        self._work_unit_transition(
            collector,
            payload,
            source_hook="on_kanban_worker_stale_claim",
            event_type="run.finished",
            status="reclaimed",
            run_status="released",
            run_outcome="reclaimed",
        )

    def _on_on_kanban_task_updated(self, collector: Collector, payload: dict[str, Any]) -> None:
        # Locked Hermes deliberately supplies changed field names, not values.
        # Reconciliation reads authoritative state outside the callback.
        task_ref = native_kanban_task_ref(_pick(payload, "task_id"))
        if task_ref is None:
            self._record_native_hook_rejection(
                collector,
                "NATIVE_KANBAN_TASK_ID_REJECTED",
            )
        elif collector.binder.trace_for(task_ref) is None:
            collector.health.increment("TASK_UPDATE_BINDING_UNRESOLVED")

    def _on_on_kanban_dispatch_tick(self, collector: Collector, payload: dict[str, Any]) -> None:
        if self._active_trace is None:
            collector.health.increment("DISPATCH_TRACE_UNRESOLVED")
            return
        projection = _bounded_dispatch_result(payload.get("result"))
        collector.emit(
            collector.builder_for(self._active_trace).dispatch(
                tick_ref="tick_" + secrets.token_hex(16),
                outcome=safe_ref(_pick(payload, "outcome")) or "observed",
                bottleneck_class=projection["bottleneck_class"],
                eligible_count=projection["eligible_count"],
                running_count=projection["running_count"],
                global_limit=_pick(payload, "global_limit", "max_concurrent"),
                per_profile_limit=_pick(payload, "per_profile_limit"),
                actor_kind="system",
                actor_id=self._profile(payload) or "dispatcher",
                profile=self._profile(payload),
            )
        )

    # -- participant/session/skills -------------------------------------------
    def _subagent_link(
        self,
        collector: Collector,
        payload: dict[str, Any],
        child: str,
        action: str,
    ) -> dict[str, Any]:
        return {
            "call_id": child,
            "name": f"subagent.{action}",
            "category": "delegation",
            "target_kind": "session",
            "target_ref": self._pseudonymize_native_ref(
                collector,
                "session",
                _pick(payload, "parent_session_id"),
            ),
        }

    def _on_subagent_start(self, collector: Collector, payload: dict[str, Any]) -> None:
        trace = self._trace_for_payload(collector, payload)
        child = self._pseudonymize_native_ref(
            collector,
            "session",
            _pick(payload, "child_session_id"),
        )
        if trace is None or child is None:
            return
        builder = collector.builder_for(trace)
        joined = builder.build(
            "participant.joined",
            status="started",
            source_hook="subagent_start",
            actor_kind="subagent",
            actor_id=child,
            profile=self._profile(payload),
            role=safe_ref(_pick(payload, "child_role", "role")),
            session_id=child,
            turn_id=self._turn(collector, payload, "parent_turn_id"),
            task_id=native_agent_task_ref(_pick(payload, "task_id")),
            tool=self._subagent_link(collector, payload, child, "start"),
        )
        outcome = collector.emit(joined)
        if not outcome.accepted or not collector.fingerprint_key_ready:
            return
        collector.record_fingerprint_epoch_boundary(trace, parent_event_id=joined["event_id"])
        coverage = {
            "model": "unavailable",
            "provider": "unavailable",
            "prompt_fingerprint": "unavailable",
            "observed_skills": "unavailable",
            "declared_toolset": "unavailable",
            "effective_tool_surface": "unavailable",
            "global_concurrency": "unavailable",
            "per_profile_concurrency": "unavailable",
        }
        fields = {
            "scope": "participant",
            "participant_ref": child,
            "field_coverage": coverage,
            "observer_version": COLLECTOR_VERSION,
            "fingerprint_key_id": collector.keyring.key_id,
            "runtime_fingerprint": self._runtime_fingerprint,
        }
        collector.emit(
            builder.configuration(
                fingerprint_id=configuration_fingerprint_id(fields),
                scope="participant",
                participant_ref=child,
                fingerprint_key_id=collector.keyring.key_id,
                observer_version=COLLECTOR_VERSION,
                field_coverage=coverage,
                parent_event_id=joined["event_id"],
                source_hook="subagent_start",
                session_id=child,
                task_id=native_agent_task_ref(_pick(payload, "task_id")),
                actor_kind="subagent",
                actor_id=child,
                profile=self._profile(payload),
            )
        )

    def _on_subagent_stop(self, collector: Collector, payload: dict[str, Any]) -> None:
        trace = self._trace_for_payload(collector, payload)
        child = self._pseudonymize_native_ref(
            collector,
            "session",
            _pick(payload, "child_session_id"),
        )
        if trace is None or child is None:
            return
        status, _ = normalize_native_status(_pick(payload, "child_status", "status", "outcome"))
        collector.emit(
            collector.builder_for(trace).build(
                "participant.left",
                status=status,
                source_hook="subagent_stop",
                actor_kind="subagent",
                actor_id=child,
                profile=self._profile(payload),
                role=safe_ref(_pick(payload, "child_role", "role")),
                session_id=child,
                turn_id=self._turn(collector, payload, "parent_turn_id"),
                task_id=native_agent_task_ref(_pick(payload, "task_id")),
                tool=self._subagent_link(collector, payload, child, "stop"),
            )
        )

    def _on_on_skill_lifecycle(self, collector: Collector, payload: dict[str, Any]) -> None:
        trace = self._trace_for_payload(collector, payload)
        skill = safe_ref(_pick(payload, "skill_name", "skill"))
        phase = _pick(payload, "action", "phase", "event")
        if trace is None or skill is None or phase not in ("loaded", "load", "used"):
            return
        builder = collector.builder_for(trace)
        loaded = builder.build(
            "skill.loaded",
            status="completed",
            source_hook="on_skill_lifecycle",
            session_id=self._session(collector, payload) or None,
            task_id=native_agent_task_ref(_pick(payload, "task_id")),
            actor_kind="agent",
            actor_id=self._profile(payload) or "unknown",
            profile=self._profile(payload),
            tool={
                "call_id": "skill_" + canonical_digest({"skill": skill})[:40],
                "name": "skill.load",
                "category": "skill",
                "target_kind": "skill",
                "target_ref": skill,
            },
        )
        outcome = collector.emit(loaded)
        if not outcome.accepted or not collector.fingerprint_key_ready:
            return

        profile = self._profile(payload) or "unknown"
        participant_skills = self._loaded_skills.setdefault((trace, profile), set())
        trace_skills = self._trace_skills.setdefault(trace, set())
        participant_changed = skill not in participant_skills
        trace_changed = skill not in trace_skills
        participant_skills.add(skill)
        trace_skills.add(skill)
        collector.record_fingerprint_epoch_boundary(trace, parent_event_id=loaded["event_id"])
        coverage = {
            "model": "unavailable",
            "provider": "unavailable",
            "prompt_fingerprint": "unavailable",
            "observed_skills": "exact",
            "declared_toolset": "unavailable",
            "effective_tool_surface": "unavailable",
            "global_concurrency": "unavailable",
            "per_profile_concurrency": "unavailable",
        }
        for scope, participant_ref, names, changed in (
            ("participant", profile, participant_skills, participant_changed),
            ("trace", None, trace_skills, trace_changed),
        ):
            if not changed:
                continue
            skill_fingerprint = collector.keyring.fingerprint("observed_skill_set", sorted(names))
            fields = {
                "scope": scope,
                "participant_ref": participant_ref,
                "observed_skill_set_fingerprint": skill_fingerprint,
                "field_coverage": coverage,
                "observer_version": COLLECTOR_VERSION,
                "fingerprint_key_id": collector.keyring.key_id,
                "runtime_fingerprint": self._runtime_fingerprint,
            }
            collector.emit(
                builder.configuration(
                    fingerprint_id=configuration_fingerprint_id(fields),
                    scope=scope,
                    participant_ref=participant_ref,
                    fingerprint_key_id=collector.keyring.key_id,
                    observer_version=COLLECTOR_VERSION,
                    field_coverage=coverage,
                    observed_skill_set_fingerprint=skill_fingerprint,
                    parent_event_id=loaded["event_id"],
                    source_hook="on_skill_lifecycle",
                    session_id=self._session(collector, payload) or None,
                    task_id=native_agent_task_ref(_pick(payload, "task_id")),
                    actor_kind="agent",
                    actor_id=profile,
                    profile=self._profile(payload),
                )
            )

    def _on_on_session_start(self, collector: Collector, payload: dict[str, Any]) -> None:
        message_id = _pick(payload, "message_id")
        session_id = self._pseudonymize_native_ref(
            collector,
            "session",
            _pick(payload, "session_id"),
        )
        occurred = _native_datetime(_pick(payload, "created_at", "timestamp"))
        if session_id is not None and message_id is not None:
            collector.candidates.observe(
                session_id, message_id, occurred or datetime.now(timezone.utc)
            )

    def _on_on_session_end(self, collector: Collector, payload: dict[str, Any]) -> None:
        collector.note_expired_candidates(datetime.now(timezone.utc))

    def _on_on_session_finalize(self, collector: Collector, payload: dict[str, Any]) -> None:
        collector.note_expired_candidates(datetime.now(timezone.utc))

    def _on_on_session_reset(self, collector: Collector, payload: dict[str, Any]) -> None:
        collector.note_expired_candidates(datetime.now(timezone.utc))

    def unload(self) -> None:
        """Stop only plugin-owned work and preserve flushed segment bytes."""
        self._reconciler.stop()
        if self._collector is not None:
            self._collector.stop()
            self._collector = None


def register(ctx: Any) -> None:
    """Official Hermes plugin entry point, idempotent per manager generation."""
    try:
        if ctx in _REGISTERED:
            return
        _REGISTERED.add(ctx)
    except TypeError:
        # Small test/future facades may be unhashable or non-weak-referenceable.
        # Keep a bounded process-lifetime fallback for those unusual contexts.
        generation = id(ctx)
        if generation in _REGISTERED_FALLBACK:
            return
        _REGISTERED_FALLBACK.add(generation)
    observer = _Observer(ctx)

    def make_callback(hook_name: str) -> Callable[..., None]:
        def callback(**payload: Any) -> None:
            try:
                observer.dispatch(hook_name, payload)
            except Exception:
                collector = observer._collector  # same-module diagnostic boundary
                if collector is not None:
                    collector.stats.callback_errors += 1
                    collector.health.increment("CALLBACK_EXCEPTION")
                # Hermes's public plugin manager isolates callback exceptions.
                raise

        callback.__name__ = f"aether_observe_{hook_name}"
        return callback

    register_hook = getattr(ctx, "register_hook", None)
    if callable(register_hook):
        for hook_name in OBSERVED_HOOKS:
            try:
                register_hook(hook_name, make_callback(hook_name))
            except Exception:
                # A missing future/older hook reduces coverage; plugin load continues.
                observer.note_hook_registration_failure(hook_name)
                continue

    register_tool = getattr(ctx, "register_tool", None)
    get_config = getattr(ctx, "get_config", None)
    curated_tool_enabled = False
    if getattr(ctx, "profile_name", "") == "morfeo" and callable(get_config):
        try:
            curated_tool_enabled = get_config("curated_tool", False) is True
        except Exception:
            # Optional query access is fail-closed. Passive capture must still
            # load when profile config is unavailable or temporary.
            curated_tool_enabled = False
    if callable(register_tool) and curated_tool_enabled:
        from aether_agents.observation.brief import BriefError, observe

        def tool_handler(args: dict[str, Any], **_runtime: Any) -> str:
            try:
                value = observe(args, profile_name=getattr(ctx, "profile_name", ""))
                return canonical_json_str(value)
            except BriefError as exc:
                return canonical_json_str(
                    {"success": False, "error": {"code": exc.code, "message": str(exc)}}
                )

        register_tool(
            name="aether_observe",
            toolset="aether_observation",
            description=(
                "Read a bounded curated status, semantic change set, or diagnosis from "
                "Aether Contract Observation; never returns logs or raw payloads."
            ),
            schema={
                "name": "aether_observe",
                "description": (
                    "Read compact deterministic Contract Observation for the current project. "
                    "Use status normally, changes with since_summary_id, and diagnose only for "
                    "blockage or anomaly. Output is capped and contains no raw logs/events."
                ),
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["status", "changes", "diagnose"]},
                        "ref": {"type": "string", "maxLength": 128},
                        "project": {"type": "string", "maxLength": 4096},
                        "since_summary_id": {
                            "type": "string",
                            "pattern": "^sum_[a-f0-9]{64}$",
                        },
                    },
                },
            },
            handler=tool_handler,
            check_fn=lambda: getattr(ctx, "profile_name", "") == "morfeo",
        )

    on_unload = getattr(ctx, "on_unload", None)
    if callable(on_unload):
        on_unload(observer.unload)
