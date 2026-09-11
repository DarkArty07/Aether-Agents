"""Immutable value objects for the Telegram monitor state boundary.

The monitor store persists these records in its private database.  They deliberately
contain identifiers, bounded metadata and validated JSON mappings only; source database
rows and transport credentials are not part of this model.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class DeliveryState(StrEnum):
    """Durable per-part delivery outcomes."""

    PENDING = "pending"
    SENDING = "sending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True, slots=True)
class MonitorSettings:
    """Installation-local monitor controls and native binding metadata."""

    schema_version: str
    enabled: bool
    native_job_id: str | None
    profile_binding: str | None
    destination_ref: str | None
    first_enabled_at_utc: str | None
    timezone: str
    last_cutoff_utc: str | None
    paused_at_utc: str | None
    updated_at_utc: str


@dataclass(frozen=True, slots=True)
class WorkItem:
    """One stable source-work identity and its monitor-owned cursor."""

    work_key: str
    project_id: str
    origin_session_id: str
    origin_session_title: str
    first_seen_utc: str
    project_name: str | None = None
    contract_id: str | None = None
    contract_version: str | None = None
    contract_title: str | None = None
    board_binding: Mapping[str, Any] | None = None
    started_at_utc: str | None = None
    ended_at_utc: str | None = None
    observed_state: str = "unknown"
    source_cursor: Any = None
    final_outcome_delivery_marker: str | None = None
    active: bool = True
    last_seen_utc: str | None = None


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Immutable bounded evidence cut for one UTC cutoff."""

    report_id: str
    cutoff_utc: str
    previous_cutoff_utc: str | None
    collected_at_utc: str
    watermarks: Mapping[str, Any]
    payload: Mapping[str, Any]
    coverage_gaps: tuple[str, ...]
    digest: str
    resolved_at_utc: str | None = None

    @property
    def payload_json(self) -> str:
        """Return the canonical JSON representation used for the digest."""
        import json

        return json.dumps(
            self.payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


@dataclass(frozen=True, slots=True)
class Narrative:
    """One validated Morfeo result associated with an immutable snapshot."""

    report_id: str
    structured_result: Mapping[str, Any] | None
    narrator_session_id: str | None
    attempt_status: str
    created_at_utc: str
    updated_at_utc: str


@dataclass(frozen=True, slots=True)
class Delivery:
    """Durable state for one ordered rendered report part."""

    report_id: str
    part_index: int
    text_hash: str
    state: DeliveryState
    attempts: int
    created_at_utc: str
    updated_at_utc: str
    last_error_class: str | None = None
    last_error_message: str | None = None
    message_id: str | None = None
    lease_owner: str | None = None
    lease_token: str | None = None


@dataclass(frozen=True, slots=True)
class Lease:
    """Short transactional claim; it must not be held across external calls."""

    lease_key: str
    lease_kind: str
    owner_id: str
    token: str
    acquired_at_utc: str
    expires_at_utc: str
    report_id: str | None = None
    part_index: int | None = None
    owner_process_id: int | None = None


# Stable descriptive aliases for downstream units that prefer record-oriented names.
MonitorWorkItem = WorkItem
HourlySnapshot = Snapshot
NarrativeRecord = Narrative
DeliveryRecord = Delivery
TransactionLease = Lease
DeliveryLease = Lease
