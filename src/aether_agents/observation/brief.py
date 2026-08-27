"""Bounded, privacy-safe projections of validated Contract Observation summaries."""

from __future__ import annotations

import importlib.resources
import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator

from aether_agents.observation import query, report
from aether_agents.observation.contracts import canonical_json_str, validate_summary
from aether_agents.observation.privacy import assert_clean
from aether_agents.paths import ObservationPaths

SCHEMA_VERSION = "aether.observation.brief.v1"
LIMITS = {"status": 2048, "changes": 2048, "diagnose": 4096}
MAX_FINDINGS = 5


class BriefError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    packaged = importlib.resources.files("aether_agents").joinpath(
        "resources/schemas/observation-brief.schema.json"
    )
    try:
        raw = packaged.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        root = __import__("pathlib").Path(__file__).resolve().parents[3]
        raw = (
            root / "specs/002-aether-contract-observation/contracts/observation-brief.schema.json"
        ).read_text(encoding="utf-8")
    return Draft202012Validator(json.loads(raw))


def _base(action: str, summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "action": action,
        "state": "ready",
        "project_id": summary["project_id"],
        "trace_id": summary["trace_id"],
        "contract_id": summary.get("contract_id"),
        "summary_id": summary["summary_id"],
        "as_of": summary["as_of"],
    }


def _status(summary: dict[str, Any]) -> dict[str, Any]:
    work = summary["work_graph"]
    acceptance = summary["acceptance"]
    value = _base("status", summary)
    value.update(
        {
            "completion_state": summary["completion_state"],
            "runtime_state": dict(summary["runtime_state"]),
            "work": {
                key: work[key]
                for key in (
                    "total_units",
                    "required_units",
                    "done_required_units",
                    "open_required_units",
                    "blocked_required_units",
                    "review_required_units",
                    "all_required_done",
                )
            },
            "acceptance": {
                key: acceptance[key]
                for key in ("complete", "criterion_count", "passed", "failed", "pending", "unknown")
            },
        }
    )
    return value


def _changes(summary: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    diff = report.diff_summaries(summary, previous)
    value = _base("changes", summary)
    value.update(
        {
            "previous_summary_id": previous["summary_id"],
            "comparable": diff["comparable"],
            "comparison_error": diff["error"],
            "change_classes": list(diff["change_classes"]),
            "fingerprint_boundary": diff["fingerprint_boundary"],
        }
    )
    return value


def _codes(items: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(item[key]) for item in items if item.get(key)})[:MAX_FINDINGS]


def _diagnose(summary: dict[str, Any]) -> dict[str, Any]:
    brief = summary["review_brief"]
    gate = brief["next_gate"]
    value = _base("diagnose", summary)
    value.update(
        {
            "verdict": brief["verdict"],
            "primary_reason_code": brief["primary_reason_code"],
            "evidence_status": brief["evidence_status"],
            "unfinished_required_units": brief["unfinished_required_units"],
            "unfinished_acceptance_criteria": brief["unfinished_acceptance_criteria"],
            "next_gate": {"kind": gate["kind"], "target_ref": gate["target_ref"]},
            "coverage": {
                "complete": summary["coverage"]["complete"],
                "gap_count": summary["coverage"]["gap_count"],
                "reason_codes": _codes(summary["coverage"]["gaps"], "reason_code"),
            },
            "finding_codes": _codes(brief["findings"], "code"),
            "bottleneck_classes": _codes(summary["bottlenecks"], "class"),
            "defect_classes": _codes(summary["defect_attributions"], "class"),
        }
    )
    return value


def _empty(action: str, project_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "action": action,
        "state": "empty",
        "project_id": project_id,
        "trace_id": None,
        "contract_id": None,
        "summary_id": None,
    }


def _validate_and_bound(value: dict[str, Any], action: str) -> dict[str, Any]:
    assert_clean(value)
    errors = sorted(_validator().iter_errors(value), key=lambda error: tuple(error.path))
    if errors:
        raise BriefError("BRIEF_SCHEMA_INVALID", "curated observation failed schema validation")
    if len(canonical_json_str(value).encode("utf-8")) > LIMITS[action]:
        raise BriefError("BRIEF_OUTPUT_LIMIT", "curated observation exceeds its output limit")
    return value


def observe(args: dict[str, Any], *, profile_name: str) -> dict[str, Any]:
    if profile_name != "morfeo":
        raise BriefError(
            "AETHER-OBSERVE-ROLE-DENIED", "curated observation is restricted to Morfeo"
        )
    action = args.get("action")
    if action not in LIMITS:
        raise BriefError(
            "AETHER-OBSERVE-ACTION-INVALID", "action must be status, changes or diagnose"
        )
    if action == "changes" and not args.get("since_summary_id"):
        raise BriefError("AETHER-OBSERVE-SINCE-REQUIRED", "changes requires since_summary_id")
    try:
        project = query.resolve_project(explicit=args.get("project"))
    except query.ProjectResolutionError:
        raise BriefError(
            "AETHER-OBSERVE-PROJECT-UNRESOLVED", "project could not be resolved"
        ) from None
    paths = ObservationPaths.for_project(project.project_id)
    try:
        trace_id = query.resolve_trace(paths, args.get("ref"))
    except query.NoOpenTraceError:
        if args.get("ref"):
            raise BriefError("AETHER-OBSERVE-TRACE-NOT-FOUND", "no trace matches ref") from None
        return _validate_and_bound(_empty(action, project.project_id), action)
    except query.TraceAmbiguousError:
        raise BriefError(
            "AETHER-OBSERVE-TRACE-AMBIGUOUS", "more than one open trace matches"
        ) from None
    except query.TraceNotFoundError:
        raise BriefError("AETHER-OBSERVE-TRACE-NOT-FOUND", "no trace matches ref") from None
    except query.StateUnreadableError:
        raise BriefError(
            "AETHER-OBSERVE-STATE-UNREADABLE", "observation state is unreadable"
        ) from None
    try:
        summary = query.load_summary(paths, trace_id)
        validate_summary(summary)
        if action == "status":
            value = _status(summary)
        elif action == "diagnose":
            value = _diagnose(summary)
        else:
            previous = query.load_previous_summary(paths, str(args["since_summary_id"]))
            validate_summary(previous)
            value = _changes(summary, previous)
    except query.SummaryNotFoundError:
        raise BriefError("AETHER-OBSERVE-SINCE-NOT-FOUND", "prior summary was not found") from None
    except query.StateUnreadableError:
        raise BriefError(
            "AETHER-OBSERVE-STATE-UNREADABLE", "observation state is unreadable"
        ) from None
    except BriefError:
        raise
    except Exception:
        raise BriefError("AETHER-OBSERVE-SUMMARY-INVALID", "summary failed validation") from None
    return _validate_and_bound(value, action)
