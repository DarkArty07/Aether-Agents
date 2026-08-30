"""Bottleneck and defect attribution with explicit provenance.

Normative sources: OBS-D-017, OBS-FR-061, OBS-FR-062, OBS-FR-064.

The rule that shapes this module: native block kinds, run outcomes, dispatcher skip
reasons, policy denials, and tool error classes already carry most of the taxonomy without
asking anyone for anything. Only the residual semantic distinction needs judgment.

So a class is derived mechanically ONLY where the spec closes the mapping:

* ``runtime_failure`` from ``spawn_failed | crashed | timed_out`` and nothing else;
* ``policy_denial`` from a structured tool or approval denial and nothing else;
* ``capacity_bound`` only with a native cap signal AND a saturated running count.

``capability``, ``needs_input``, ``protocol_violation``, ``changes_requested`` and
``skipped_unassigned`` are evidence, not proof of the corresponding semantic defect. They
stay ``actor_declared``, ``morfeo_judgment``, or ``undeclared`` — and ``undeclared`` is a
valid value, not a coverage gap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aether_agents.observation.contracts import ANOMALOUS_RUN_OUTCOMES
from aether_agents.observation.identity import attribution_id

if TYPE_CHECKING:  # pragma: no cover
    from aether_agents.observation.reduce.reducer import _TraceState

__all__ = ["build_bottlenecks", "build_defects"]

#: Native run outcomes whose runtime meaning is closed.
_RUNTIME_FAILURE_OUTCOMES = ("spawn_failed", "crashed", "timed_out")


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def build_bottlenecks(trace: "_TraceState") -> list[dict[str, Any]]:
    """One class per dispatch-tick-observed interval where eligible work was not running."""
    records: list[dict[str, Any]] = []
    ticks = sorted(trace.dispatch_ticks, key=lambda t: t["at"])

    for position, tick in enumerate(ticks):
        eligible, running = tick["eligible"], tick["running"]
        if not isinstance(eligible, int) or not isinstance(running, int):
            continue
        if eligible <= running:
            continue  # Nothing was ready-but-not-running at this sample.
        following = ticks[position + 1]["at"] if position + 1 < len(ticks) else None
        klass = tick["bottleneck_class"]
        if klass == "capacity_bound" and not _capacity_evidenced(tick):
            # Waiting alone is insufficient evidence for a capacity claim.
            klass = "unknown"
        duration = int((following - tick["at"]).total_seconds() * 1000) if following else None
        records.append(
            {
                "attribution_id": attribution_id("bottleneck", _iso(tick["at"]), klass),
                "class": klass,
                # The dispatcher observed it directly; the interval to the next tick is
                # derived, which is why sampling precision travels with the value.
                "provenance": "native_observed",
                "started_at": _iso(tick["at"]),
                "ended_at": _iso(following),
                "duration_ms": duration,
                "sampling_precision_ms": tick["precision_ms"] or duration,
                "evidence_refs": sorted(tick["evidence"]),
            }
        )

    for declared in trace.attributions:
        if declared.get("kind") != "bottleneck":
            continue
        records.append(
            {
                "attribution_id": attribution_id(
                    "bottleneck", declared.get("event_id"), declared.get("class")
                ),
                "class": declared.get("class") or "unknown",
                "provenance": declared.get("provenance") or "actor_declared",
                "started_at": declared.get("started_at"),
                "ended_at": declared.get("ended_at"),
                "duration_ms": None,
                "sampling_precision_ms": declared.get("precision_ms"),
                "evidence_refs": sorted(
                    set(declared.get("evidence_refs") or []) | {declared["event_id"]}
                ),
            }
        )

    records.sort(key=lambda r: (r["started_at"] or "", r["class"], r["attribution_id"]))
    return records


def _capacity_evidenced(tick: dict[str, Any]) -> bool:
    """A native per-profile or global cap plus a saturated running count (OBS-FR-061)."""
    cap = tick.get("global_limit") or tick.get("per_profile_limit")
    running = tick.get("running")
    return isinstance(cap, int) and cap > 0 and isinstance(running, int) and running >= cap


def build_defects(trace: "_TraceState") -> list[dict[str, Any]]:
    """Bounded defect classes, each carrying how it was established."""
    records: list[dict[str, Any]] = []

    for task_ref in sorted(trace.units):
        unit = trace.units[task_ref]
        # Every attempt is attributed, not just the latest: a later successful retry does
        # not erase the runtime failure that forced it.
        for position, outcome in enumerate(unit.get("run_outcome_history") or []):
            if outcome in _RUNTIME_FAILURE_OUTCOMES:
                klass, provenance = "runtime_failure", "deterministic_derived"
            elif outcome in ANOMALOUS_RUN_OUTCOMES:
                # `gave_up` and `reclaimed` are evidence of an anomaly, not proof of a
                # runtime defect, so their semantic cause stays undeclared.
                klass, provenance = "undeclared", "undeclared"
            else:
                continue
            records.append(
                {
                    "attribution_id": attribution_id("defect", task_ref, position, outcome),
                    "class": klass,
                    "provenance": provenance,
                    "evidence_refs": sorted(set(unit["evidence"]))[:32],
                }
            )

    for span in trace.tool_spans:
        error_class = str(span.get("error_class") or "").lower()
        denied = span["approval_outcome"] == "denied" or (
            span["status"] == "blocked"
            and any(marker in error_class for marker in ("policy", "approval", "denied"))
        )
        if denied:
            records.append(
                {
                    "attribution_id": attribution_id("defect", span["call_id"], "policy_denial"),
                    "class": "policy_denial",
                    "provenance": "native_observed",
                    "evidence_refs": [span["event_id"]],
                }
            )

    for declared in trace.attributions:
        if declared.get("kind") != "defect":
            continue
        records.append(
            {
                "attribution_id": attribution_id(
                    "defect", declared.get("event_id"), declared.get("class")
                ),
                "class": declared.get("class") or "undeclared",
                # A declaration or Morfeo's judgment stays labelled as such, so it can
                # never be mistaken for a native measurement.
                "provenance": declared.get("provenance") or "actor_declared",
                "evidence_refs": sorted(
                    set(declared.get("evidence_refs") or []) | {declared["event_id"]}
                ),
            }
        )

    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        unique.setdefault(record["attribution_id"], record)
    return [unique[key] for key in sorted(unique)]
