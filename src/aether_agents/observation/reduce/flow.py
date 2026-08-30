"""Deterministic flow classification.

Normative sources: spec section 11 (state signature and classification order),
OBS-D-003, OBS-FR-017..024.

Progress is measured by explicit semantic deltas — never by heartbeat frequency, token
volume, wall time, or tool-call count. The normalized state signature makes state equality
deterministic by excluding timestamps and participant identities entirely, so two states
are equal exactly when the contract's meaning is equal.

The precedence order below is normative and total: every transition receives exactly one
primary classification, and classification never changes task status or artifact content.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from aether_agents.observation.contracts import WORK_UNIT_RELATIONS, canonical_digest

if TYPE_CHECKING:  # pragma: no cover
    from aether_agents.observation.reduce.reducer import _TraceState

__all__ = ["classify_flow", "state_signature"]


def state_signature(state: dict[str, Any]) -> str:
    """SHA-256 over the canonical normalized state (spec section 11.1).

    Arrays are sorted, duplicate references removed, timestamps and participant
    identities excluded.
    """
    return canonical_digest(
        {
            "accepted_decision_ids": sorted(set(state["decisions"])),
            "unresolved_material_ambiguity_ids": sorted(set(state["ambiguities"])),
            "evidence_refs": sorted(set(state["evidence"])),
            "invariant_results": dict(sorted(state["invariants"].items())),
            "current_contract_artifact_sha256": state["artifact"],
            "required_work_units": sorted(
                (
                    {
                        "task_id": task,
                        "relation": unit["relation"],
                        "task_status": unit["task_status"],
                        "latest_run_outcome": unit["latest_run_outcome"],
                    }
                    for task, unit in state["units"].items()
                    if unit["required"]
                ),
                key=lambda item: item["task_id"],
            ),
            "required_reviews": sorted(
                (
                    {"task_id": task, "state": unit["review_state"]}
                    for task, unit in state["units"].items()
                    if unit["required"] and unit["review_state"] != "not_required"
                ),
                key=lambda item: item["task_id"],
            ),
            "acceptance_criteria": sorted(
                (
                    {
                        "criterion_ref": ref,
                        "state": record["state"],
                        "evidence_refs": sorted(set(record["evidence_refs"])),
                    }
                    for ref, record in state["criteria"].items()
                ),
                key=lambda item: item["criterion_ref"],
            ),
        }
    )


#: Spec section 11.2, applied in this exact order.
PRECEDENCE = (
    "owner_direction_change",
    "authorized_reversion",
    "technical_retry",
    "regression",
    "useful_iteration",
    "cycle",
    "semantic_loop",
)

#: Every kind the summary schema can carry. Reversions are counted outside the precedence
#: walk (they short-circuit it), so the reported set is deliberately wider.
REPORTED_KINDS = PRECEDENCE + ("unexplained_reversion",)


def classify_flow(trace: "_TraceState") -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Replay the trace and classify every normalized-state transition."""
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = {}
    derived_gaps: list[dict[str, str]] = []

    state: dict[str, Any] = {
        "decisions": set(),
        "ambiguities": set(),
        "evidence": set(),
        "invariants": {},
        "artifact": None,
        "units": {},
        "criteria": {},
    }
    artifact_history: list[str] = []
    superseded_now = False
    revisions = 0
    previous_signature = state_signature(state)
    last_transition: tuple[str, str] | None = None
    consecutive_cycles = 0
    pending_retry_calls: set[tuple[str, str]] = set()
    owner_supersession_events: set[str] = set()

    for event in trace.events:
        event_type = str(event.get("event_type") or "")
        event_id = str(event.get("event_id") or "")
        contract = event.get("contract") or {}
        unit = event.get("work_unit")
        if isinstance(unit, dict):
            envelope_task = event.get("task_id")
            unit_task = unit.get("task_ref")
            if (
                isinstance(envelope_task, str)
                and isinstance(unit_task, str)
                and envelope_task != unit_task
            ):
                continue

        if event_type.startswith("acceptance."):
            acceptance = event.get("acceptance") or {}
            assigned = acceptance.get("review_task_ref") or acceptance.get("assigned_task_ref")
            if not trace._authorized(
                event, task_ref=assigned if isinstance(assigned, str) else None
            ):
                continue
        if event_type in ("review.approved", "review.changes_requested"):
            task_ref = (event.get("work_unit") or {}).get("task_ref")
            if not trace._authorized(
                event, task_ref=task_ref if isinstance(task_ref, str) else None
            ):
                continue

        # Tool retries are linked to the call they repeat, so a provider failure never
        # reads as the contract reasoning going in circles (OBS-FR-019).
        tool = event.get("tool") or {}
        session_id = str(event.get("session_id") or "")
        if event_type == "tool.failed" and isinstance(tool.get("call_id"), str):
            pending_retry_calls.add((session_id, tool["call_id"]))
        retry_ref = tool.get("retry_of_call_id")
        retry_key = (session_id, retry_ref) if isinstance(retry_ref, str) else None
        retry_link = retry_key is not None and retry_key in pending_retry_calls
        if retry_link:
            counts["technical_retry"] += 1
            evidence.setdefault("technical_retry", []).append(event_id)
            pending_retry_calls.discard(retry_key)
            continue

        superseded_now = False
        was_satisfied = _was_satisfied(state, event, event_type)
        authorized_change = (
            isinstance(contract.get("supersedes_decision_ref"), str)
            or event.get("parent_event_id") in owner_supersession_events
        )
        changed = _apply(state, event, event_type, contract)
        if event_type == "contract.revision":
            revisions += 1
            after = contract.get("after_sha256")
            if isinstance(after, str):
                reverted = (
                    bool(artifact_history)
                    and after != artifact_history[-1]
                    and after in artifact_history[:-1]
                )
                artifact_history.append(after)
                if reverted:
                    authorized = authorized_change
                    kind = "authorized_reversion" if authorized else "unexplained_reversion"
                    counts[kind] += 1
                    evidence.setdefault(kind, []).append(event_id)
                    previous_signature = state_signature(state)
                    continue
        if event_type == "decision.superseded":
            superseded_now = True
            owner_supersession_events.add(event_id)

        if not changed:
            continue

        signature = state_signature(state)
        transition = (previous_signature, signature)
        delta = signature != previous_signature

        if superseded_now:
            # A changed owner decision with a valid supersession edge is a direction
            # change, not a regression (OBS-FR-023).
            kind = "owner_direction_change"
        elif was_satisfied and not authorized_change:
            kind = "regression"
        elif delta:
            # OBS-FR-018 classifies a non-zero delta "according to its phase". A contract
            # or artifact delta is an iteration; a bound-work, run, review, or acceptance
            # delta is verified progress, already carried by `last_verified_progress_at`
            # and the work graph. Counting the latter as iterations would inflate the
            # contract's revision story with ordinary execution mechanics.
            kind = "useful_iteration" if _is_contract_phase(event_type) else None
        else:
            kind = "cycle"

        if kind is None:
            previous_signature = signature
            consecutive_cycles = 0
            last_transition = transition
            continue

        if kind == "cycle":
            if last_transition == transition:
                consecutive_cycles += 1
            else:
                consecutive_cycles = 1
            if consecutive_cycles >= 2:
                # Two consecutive zero-delta cycles over the same normalized transition
                # is the smallest useful deterministic loop signal (OBS-D-003).
                counts["semantic_loop"] += 1 if consecutive_cycles == 2 else 0
                evidence.setdefault("semantic_loop", []).append(event_id)
        else:
            consecutive_cycles = 0

        counts[kind] += 1
        evidence.setdefault(kind, []).append(event_id)
        last_transition = transition
        previous_signature = signature

    classifications = [
        {
            "kind": kind,
            "count": counts[kind],
            "evidence_event_ids": sorted(set(evidence.get(kind, []))),
        }
        for kind in REPORTED_KINDS
        if counts.get(kind)
    ]
    flow = {
        "revision_count": revisions,
        "useful_iterations": counts.get("useful_iteration", 0),
        "technical_retries": counts.get("technical_retry", 0),
        "cycles": counts.get("cycle", 0),
        "semantic_loops": counts.get("semantic_loop", 0),
        "regressions": counts.get("regression", 0),
        "authorized_reversions": counts.get("authorized_reversion", 0),
        "unexplained_reversions": counts.get("unexplained_reversion", 0),
        "owner_direction_changes": counts.get("owner_direction_change", 0),
        "classifications": classifications,
    }
    return flow, derived_gaps


#: Contract-authoring phase. Everything else is execution mechanics.
_CONTRACT_PHASE_PREFIXES = (
    "contract.",
    "decision.",
    "evidence.",
    "clarification.",
)


def _is_contract_phase(event_type: str) -> bool:
    return event_type.startswith(_CONTRACT_PHASE_PREFIXES)


def _apply(
    state: dict[str, Any], event: dict[str, Any], event_type: str, contract: dict[str, Any]
) -> bool:
    """Fold one event into the normalized state. Returns whether state could change."""
    if event_type == "decision.recorded":
        state["decisions"].update(contract.get("decision_refs") or [])
        return True
    if event_type == "decision.superseded":
        for ref in contract.get("decision_refs") or []:
            state["decisions"].discard(ref)
        superseded = contract.get("supersedes_decision_ref")
        if isinstance(superseded, str):
            state["decisions"].discard(superseded)
        return True
    if event_type == "decision.rejected":
        for ref in contract.get("decision_refs") or []:
            state["decisions"].discard(ref)
        return True
    if event_type == "evidence.added":
        state["evidence"].update(contract.get("evidence_refs") or [])
        return True
    if event_type == "evidence.rejected":
        for ref in contract.get("evidence_refs") or []:
            state["evidence"].discard(ref)
        return True
    if event_type == "clarification.requested":
        ambiguity = contract.get("ambiguity_ref")
        if isinstance(ambiguity, str):
            state["ambiguities"].add(ambiguity)
        return True
    if event_type == "clarification.resolved":
        ambiguity = contract.get("ambiguity_ref")
        if isinstance(ambiguity, str):
            state["ambiguities"].discard(ambiguity)
        return True
    if event_type in ("invariant.passed", "invariant.failed"):
        key = contract.get("invariant_key")
        if isinstance(key, str):
            state["invariants"][key] = (
                "unknown"
                if event.get("status") == "unknown"
                else "passed"
                if event_type.endswith("passed")
                else "failed"
            )
        return True
    if event_type == "contract.revision":
        after = contract.get("after_sha256")
        if isinstance(after, str):
            state["artifact"] = after
        return True
    if event_type in ("acceptance.declared", "acceptance.evaluated"):
        acceptance = event.get("acceptance") or {}
        ref = acceptance.get("criterion_ref")
        if isinstance(ref, str):
            state["criteria"][ref] = {
                "state": acceptance.get("state") or "unknown",
                "evidence_refs": list(acceptance.get("evidence_refs") or []),
            }
        return True
    if event_type.startswith(("work_unit.", "run.", "review.")):
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if not isinstance(task_ref, str):
            return False
        relation = unit.get("relation")
        required = unit.get("required")
        if relation not in WORK_UNIT_RELATIONS or not isinstance(required, bool):
            return False
        record = state["units"].setdefault(
            task_ref,
            {
                "relation": relation,
                "required": required,
                "task_status": "unknown",
                "latest_run_outcome": None,
                "review_state": "not_required",
            },
        )
        if record["relation"] != relation or record["required"] != required:
            return False
        if unit.get("task_status"):
            record["task_status"] = unit["task_status"]
        if unit.get("run_outcome"):
            record["latest_run_outcome"] = unit["run_outcome"]
        if event_type == "review.requested":
            record["review_state"] = "pending"
        elif event_type == "review.approved":
            record["review_state"] = "approved"
        elif event_type == "review.changes_requested":
            record["review_state"] = "changes_requested"
        return True
    return False


def _was_satisfied(state: dict[str, Any], event: dict[str, Any], event_type: str) -> bool:
    """Whether this transition is breaking a previously satisfied assertion."""
    if event_type == "invariant.failed":
        key = (event.get("contract") or {}).get("invariant_key")
        return isinstance(key, str) and state["invariants"].get(key) == "passed"
    if event_type == "review.changes_requested":
        task_ref = (event.get("work_unit") or {}).get("task_ref")
        record = state["units"].get(task_ref) if isinstance(task_ref, str) else None
        return isinstance(record, dict) and record.get("review_state") == "approved"
    if event_type == "acceptance.evaluated":
        acceptance = event.get("acceptance") or {}
        ref = acceptance.get("criterion_ref")
        previous = state["criteria"].get(ref) if isinstance(ref, str) else None
        return (
            acceptance.get("state") == "failed"
            and isinstance(previous, dict)
            and previous.get("state") == "passed"
        )
    return False
