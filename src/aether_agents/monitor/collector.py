"""Hourly reconciliation and bounded canonical snapshot construction.

``ReadOnlySources`` supplies normalized evidence; this module owns the monitor-owned
store interaction and the fixed ``aether.telegram-monitor.snapshot.v1`` mapping.  It
never invokes a model, opens a native source database itself, or advances source state.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .models import WorkItem
from .sources import (
    MAX_PROSE_CHARS,
    MAX_SNAPSHOT_CHARS,
    SNAPSHOT_SCHEMA,
    ReadOnlySources,
    SourceCollection,
    SourceItem,
)
from .store import MonitorStore, Snapshot

__all__ = [
    "CollectionDisabledError",
    "CollectionResult",
    "MonitorCollector",
    "SnapshotBoundsError",
    "build_bounded_snapshot",
]


class CollectionDisabledError(RuntimeError):
    """Collection was requested while the durable monitor switch is off."""


class SnapshotBoundsError(RuntimeError):
    """The canonical identity set cannot fit within the fixed snapshot bound."""


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """The committed monitor snapshot and its source diagnostics."""

    snapshot: Snapshot
    source: SourceCollection

    @property
    def report_id(self) -> str:
        return self.snapshot.report_id


def _utc(value: datetime | str | None, *, default_now: bool = False) -> str:
    if value is None:
        if not default_now:
            raise ValueError("timestamp is required")
        value = datetime.now(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be ISO-8601") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError("timestamp must be timezone-aware")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _fact_sort(value: Mapping[str, Any]) -> tuple[str, str]:
    return str(value.get("ref", "")), str(value.get("text", ""))


def _facts(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in sorted(values, key=_fact_sort):
        ref = raw.get("ref")
        text = raw.get("text")
        if not isinstance(ref, str) or not isinstance(text, str):
            continue
        key = (ref, text)
        if key in seen:
            continue
        seen.add(key)
        fact = {
            "ref": ref,
            "text": text[:MAX_PROSE_CHARS],
            "provenance": raw.get("provenance", "observed"),
            "status": raw.get("status", "verified"),
        }
        result.append(fact)
    return result


def _item_mapping(item: SourceItem) -> dict[str, Any]:
    value = item.to_snapshot()
    for field_name in ("resolved", "current", "next", "complications", "pending"):
        value[field_name] = _facts(value.get(field_name, ()))
    value["state_evidence_refs"] = sorted(
        ref for ref in value.get("state_evidence_refs", ()) if isinstance(ref, str)
    )
    value["coverage_gaps"] = sorted(
        gap for gap in value.get("coverage_gaps", ()) if isinstance(gap, str)
    )
    return value


def _canonical_payload(
    report_id: str,
    cutoff: str,
    collected: str,
    previous: str | None,
    items: Sequence[dict[str, Any]],
    gaps: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": SNAPSHOT_SCHEMA,
        "report_id": report_id,
        "cutoff_utc": cutoff,
        "collected_at_utc": collected,
        "previous_cutoff_utc": previous,
        "items": sorted(items, key=lambda item: str(item.get("work_key", ""))),
        "coverage_gaps": sorted(set(gaps)),
    }


def _encoded_size(value: Mapping[str, Any]) -> int:
    return len(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )


def _minimal_item(item: Mapping[str, Any], *, names: bool = True) -> dict[str, Any]:
    project_value = item.get("project")
    project: Mapping[str, Any] = project_value if isinstance(project_value, Mapping) else {}
    origin_value = item.get("origin_session")
    origin: Mapping[str, Any] = origin_value if isinstance(origin_value, Mapping) else {}
    contract_value = item.get("contract")
    contract: Mapping[str, Any] | None = (
        contract_value if isinstance(contract_value, Mapping) else None
    )
    project_id = str(project.get("id", ""))
    origin_id = str(origin.get("id", ""))
    result: dict[str, Any] = {
        "work_key": str(item.get("work_key", "")),
        "project": {"id": project_id, "name": str(project.get("name", "")) if names else ""},
        "origin_session": {
            "id": origin_id,
            "title": str(origin.get("title", "")) if names else "",
        },
        "contract": None,
        "observed_state": str(item.get("observed_state", "unknown")),
        "state_evidence_refs": list(item.get("state_evidence_refs", ()))[:8],
        "resolved": [],
        "current": [],
        "next": [],
        "complications": [],
        "pending": [],
        "coverage_gaps": sorted(
            set(str(gap) for gap in item.get("coverage_gaps", ()) if isinstance(gap, str))
            | {"SNAPSHOT_COMPACTED"}
        ),
    }
    if contract is not None:
        result["contract"] = {
            "id": str(contract.get("id", "")),
            "version": str(contract.get("version", "")),
            "title": str(contract.get("title", "")) if names else "",
        }
    # Identity and lifecycle timestamps are required when present, but are not prose.
    for key in ("started_at_utc", "ended_at_utc"):
        if isinstance(item.get(key), str):
            result[key] = item[key]
    return result


def build_bounded_snapshot(
    *,
    report_id: str,
    cutoff_utc: str,
    collected_at_utc: str,
    previous_cutoff_utc: str | None,
    source: SourceCollection,
    max_chars: int = MAX_SNAPSHOT_CHARS,
) -> dict[str, Any]:
    """Build a deterministic snapshot while retaining every item identity.

    Compaction removes source prose before identity.  If the identity set itself is
    unusually large, names are shortened to empty bounded display values but project,
    origin, contract and work keys remain present; a global diagnostic records the
    compaction.  This is preferable to silently dropping an active work identity.
    """
    if not isinstance(report_id, str) or not report_id:
        raise ValueError("report_id is required")
    cutoff_utc = _utc(cutoff_utc)
    collected_at_utc = _utc(collected_at_utc)
    previous_cutoff_utc = _utc(previous_cutoff_utc) if previous_cutoff_utc is not None else None
    if previous_cutoff_utc is not None and previous_cutoff_utc >= cutoff_utc:
        raise ValueError("previous cutoff must precede the snapshot cutoff")
    items = [_item_mapping(item) for item in source.items]
    payload = _canonical_payload(
        report_id,
        cutoff_utc,
        collected_at_utc,
        previous_cutoff_utc,
        items,
        source.coverage_gaps,
    )
    if _encoded_size(payload) <= max_chars:
        return payload

    compacted = [_minimal_item(item, names=True) for item in items]
    payload = _canonical_payload(
        report_id,
        cutoff_utc,
        collected_at_utc,
        previous_cutoff_utc,
        compacted,
        (*source.coverage_gaps, "SNAPSHOT_COMPACTED"),
    )
    if _encoded_size(payload) <= max_chars:
        return payload

    # The final identity-only pass drops empty narrative arrays and display names.  The
    # stable work/project/origin/contract IDs and observed lifecycle state remain, while
    # the global diagnostic tells the narrator why prose is absent.
    identity_only: list[dict[str, Any]] = []
    for item in items:
        project_value = item.get("project")
        project = project_value if isinstance(project_value, Mapping) else {}
        origin_value = item.get("origin_session")
        origin = origin_value if isinstance(origin_value, Mapping) else {}
        contract_value = item.get("contract")
        contract = contract_value if isinstance(contract_value, Mapping) else None
        compact_identity: dict[str, Any] = {
            "work_key": str(item.get("work_key", "")),
            "project": {"id": str(project.get("id", ""))},
            "origin_session": {"id": str(origin.get("id", ""))},
            "contract": (
                {
                    "id": str(contract.get("id", "")),
                    "version": str(contract.get("version", "")),
                }
                if contract is not None
                else None
            ),
            "observed_state": str(item.get("observed_state", "unknown")),
            "coverage_gaps": sorted(
                set(str(gap) for gap in item.get("coverage_gaps", ()) if isinstance(gap, str))
            ),
        }
        identity_only.append(compact_identity)
    payload = _canonical_payload(
        report_id,
        cutoff_utc,
        collected_at_utc,
        previous_cutoff_utc,
        identity_only,
        (*source.coverage_gaps, "SNAPSHOT_COMPACTED"),
    )
    if _encoded_size(payload) <= max_chars:
        return payload

    # This last pass keeps the fixed identity keys and strips optional timestamp/ref
    # fields.  It is deterministic and still preserves every work_key and native ID.
    reduced: list[dict[str, Any]] = []
    for item in identity_only:
        reduced_item = dict(item)
        reduced_item["state_evidence_refs"] = []
        reduced_item.pop("started_at_utc", None)
        reduced_item.pop("ended_at_utc", None)
        reduced.append(reduced_item)
    payload = _canonical_payload(
        report_id,
        cutoff_utc,
        collected_at_utc,
        previous_cutoff_utc,
        reduced,
        (*source.coverage_gaps, "SNAPSHOT_COMPACTED"),
    )
    if _encoded_size(payload) > max_chars:
        raise SnapshotBoundsError("active source identities exceed the canonical snapshot bound")
    return payload


class MonitorCollector:
    """Lease, read, normalize and persist one monitor collection cut."""

    def __init__(
        self,
        store: MonitorStore,
        sources: ReadOnlySources,
        *,
        clock: Any | None = None,
        owner_id: str | None = None,
    ) -> None:
        self.store = store
        self.sources = sources
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.owner_id = owner_id or f"collector:{os.getpid()}:{secrets.token_hex(6)}"

    def collect(
        self,
        *,
        cutoff_utc: datetime | str | None = None,
        collected_at_utc: datetime | str | None = None,
        direct_records: Sequence[Mapping[str, Any]] = (),
    ) -> CollectionResult | None:
        settings = self.store.get_settings()
        if not settings.enabled:
            raise CollectionDisabledError("monitor is disabled")
        cutoff = _utc(self.clock()) if cutoff_utc is None else _utc(cutoff_utc)
        collected = _utc(self.clock()) if collected_at_utc is None else _utc(collected_at_utc)
        previous = settings.last_cutoff_utc
        if previous is not None and _utc(cutoff) <= previous:
            raise ValueError("cutoff must advance beyond the persisted monitor watermark")
        source = self.sources.collect(
            previous_cutoff_utc=previous,
            cutoff_utc=cutoff,
            direct_records=direct_records,
        )
        lease = self.store.acquire_collection_lease(cutoff, owner_id=self.owner_id)
        if lease is None:
            return None
        report_id = "rpt_" + secrets.token_hex(16)
        work_items: list[WorkItem] = []
        payload_items: list[SourceItem] = []
        for item in source.items:
            existing = self.store.get_work_item(item.work_key)
            marker = existing.final_outcome_delivery_marker if existing is not None else None
            contract_id = item.contract.get("id") if item.contract is not None else None
            contract_version = item.contract.get("version") if item.contract is not None else None
            contract_title = item.contract.get("title") if item.contract is not None else None
            first_seen = item.started_at_utc or collected
            work_items.append(
                WorkItem(
                    work_key=item.work_key,
                    project_id=item.project_id,
                    project_name=item.project_name,
                    origin_session_id=item.origin_session_id,
                    origin_session_title=item.origin_session_title,
                    contract_id=contract_id,
                    contract_version=contract_version,
                    contract_title=contract_title,
                    first_seen_utc=first_seen,
                    started_at_utc=item.started_at_utc,
                    ended_at_utc=item.ended_at_utc,
                    observed_state=item.observed_state,
                    source_cursor=item.source_cursor,
                    final_outcome_delivery_marker=marker,
                    active=item.active,
                    last_seen_utc=collected,
                )
            )
            # A confirmed final outcome is retained in the store but no longer wakes
            # future narratives; a newly observed final always remains reportable.
            if not (item.terminal and marker is not None):
                payload_items.append(item)
        for work_item in work_items:
            self.store.upsert_work_item(work_item)
        payload_source = SourceCollection(
            items=tuple(payload_items),
            watermarks=source.watermarks,
            coverage_gaps=source.coverage_gaps,
        )
        payload = build_bounded_snapshot(
            report_id=report_id,
            cutoff_utc=cutoff,
            collected_at_utc=collected,
            previous_cutoff_utc=previous,
            source=payload_source,
        )
        snapshot = self.store.create_snapshot(
            report_id=report_id,
            cutoff_utc=cutoff,
            previous_cutoff_utc=previous,
            collected_at_utc=collected,
            watermarks=source.watermarks,
            payload=payload,
            coverage_gaps=source.coverage_gaps,
            lease=lease,
        )
        self.store.set_last_cutoff(cutoff)
        return CollectionResult(snapshot=snapshot, source=source)


# Names used by downstream integration code can remain stable without another class.
HourlyCollector = MonitorCollector
Collector = MonitorCollector
