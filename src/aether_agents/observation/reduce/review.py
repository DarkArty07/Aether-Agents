"""The deterministic review brief.

Normative sources: OBS-FR-067, OBS-FR-068, OBS-FR-069; schema ``$defs.reviewBrief``.

Morfeo reads one conclusion, not a dashboard. The brief therefore carries exactly one
verdict, one primary reason code, priority-ordered findings, and exactly one next gate —
each citing source event, work, or acceptance references. It invokes no model.

Verdict precedence is stable and total (OBS-FR-068). Ties break by severity, then causal
position on the observed critical path, then earliest causal index, then stable reference.
"""

from __future__ import annotations

from typing import Any

from aether_agents.observation.contracts import ANOMALOUS_RUN_OUTCOMES

__all__ = ["build_review_brief"]

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def build_review_brief(summary: dict[str, Any]) -> dict[str, Any]:
    """Build the brief from an otherwise complete summary object."""
    findings = _findings(summary)
    verdict, reason = _verdict(summary, findings)
    critical_path = set(summary["process"]["critical_path"]["step_ids"])
    findings.sort(key=lambda f: _finding_key(f, critical_path))

    work_graph = summary["work_graph"]
    acceptance = summary["acceptance"]
    # Unknown/archived required units are not in the schema's bounded "open" status
    # bucket, but they are still unfinished until authoritative status is exactly done.
    unfinished_units = work_graph["required_units"] - work_graph["done_required_units"]
    unfinished_criteria = acceptance["criterion_count"] - len(
        [c for c in acceptance["criteria"] if c["state"] == "passed" and c["evidence_refs"]]
    )

    return {
        "verdict": verdict,
        "primary_reason_code": reason,
        "since_summary_id": None,
        "change_classes": [],
        "findings": findings[:32],
        "unfinished_required_units": max(0, unfinished_units),
        "unfinished_acceptance_criteria": max(0, unfinished_criteria),
        "evidence_status": _evidence_status(summary),
        "next_gate": _next_gate(summary, verdict),
    }


def _finding_key(finding: dict[str, Any], critical_path: set[str]) -> tuple:
    on_path = finding.get("on_critical_path")
    return (
        _SEVERITY_ORDER.get(finding["severity"], 9),
        0 if on_path else 1,
        finding["code"],
        ",".join(finding["evidence_refs"]),
    )


def _finding(
    severity: str,
    code: str,
    *,
    provenance: str = "deterministic_derived",
    on_critical_path: bool | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        # OBS-FR-064: a judgment-sourced finding must stay structurally distinguishable.
        "provenance": provenance,
        "on_critical_path": on_critical_path,
        "evidence_refs": sorted({str(e)[:128] for e in (evidence or [])}),
    }


def _findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    work_graph = summary["work_graph"]
    acceptance = summary["acceptance"]
    flow = summary["flow"]
    coverage = summary["coverage"]
    runtime = summary["runtime_state"]

    for unit in work_graph["units"]:
        if not unit["required"]:
            continue
        if unit["review_state"] == "changes_requested":
            findings.append(
                _finding(
                    "high",
                    "REVIEW_CHANGES_REQUESTED",
                    evidence=unit["evidence_event_ids"][:4] + [unit["task_ref"]],
                )
            )
        if unit["task_status"] == "blocked":
            findings.append(_finding("high", "WORK_UNIT_BLOCKED", evidence=[unit["task_ref"]]))
        if unit["latest_run_outcome"] in ANOMALOUS_RUN_OUTCOMES and unit["task_status"] != "done":
            # A crash the pipeline already recovered from stays in `defect_attributions`
            # as history; it does not remain an open finding forever.
            findings.append(
                _finding(
                    "medium",
                    f"RUN_{str(unit['latest_run_outcome']).upper()}",
                    evidence=[unit["task_ref"]],
                )
            )

    for criterion in acceptance["criteria"]:
        if criterion["state"] == "failed":
            findings.append(
                _finding("critical", "ACCEPTANCE_FAILED", evidence=[criterion["criterion_ref"]])
            )
        elif criterion["state"] == "passed" and not criterion["evidence_refs"]:
            findings.append(
                _finding(
                    "high",
                    "ACCEPTANCE_PASSED_WITHOUT_EVIDENCE",
                    evidence=[criterion["criterion_ref"]],
                )
            )

    for invariant in summary["invariants"]:
        if invariant["state"] == "failed":
            findings.append(_finding("high", "INVARIANT_FAILED", evidence=[invariant["key"]]))

    if flow["semantic_loops"] and summary["completion_state"] != "completed":
        findings.append(
            _finding(
                "medium",
                "SEMANTIC_LOOP",
                evidence=_classification_evidence(flow, "semantic_loop"),
            )
        )
    # A regression is reported while the thing it broke is still broken. Once the review
    # is approved, the invariant passes, and acceptance holds, it is recorded history in
    # `flow`, not an open finding blocking the verdict.
    if flow["regressions"] and _regression_unresolved(summary):
        findings.append(
            _finding("high", "REGRESSION", evidence=_classification_evidence(flow, "regression"))
        )
    if flow["unexplained_reversions"]:
        findings.append(
            _finding(
                "high",
                "UNEXPLAINED_REVERSION",
                evidence=_classification_evidence(flow, "unexplained_reversion"),
            )
        )

    if not coverage["complete"]:
        findings.append(
            _finding(
                "medium",
                "COVERAGE_INCOMPLETE",
                evidence=[gap["event_id"] for gap in coverage["gaps"][:4]],
            )
        )

    # A verified-complete contract has, by construction, a settled graph, approved
    # reviews, and evidenced acceptance (OBS-D-013). Anomalies recorded along the way stay
    # in `flow`, `defect_attributions`, and `run_totals` as history; they are not open
    # findings, because there is nothing left for the reader to act on.
    settled = summary["completion_state"] == "completed"
    for defect in summary["defect_attributions"]:
        if defect["class"] == "undeclared" or settled:
            continue
        severity = "high" if defect["class"] == "runtime_failure" else "medium"
        findings.append(
            _finding(
                severity,
                f"DEFECT_{defect['class'].upper()}",
                provenance=defect["provenance"],
                evidence=defect["evidence_refs"][:4],
            )
        )

    if runtime["waiting"] == "owner":
        findings.append(_finding("high", "AWAITING_OWNER", evidence=_open_owner_wait_refs(summary)))

    if summary["improvement_evidence"]["strength"] == "anecdotal":
        findings.append(
            _finding(
                "info",
                "EVIDENCE_ANECDOTAL_SINGLE_TRACE",
                evidence=[summary["trace_id"]],
            )
        )

    # OBS-FR-067: every finding cites a source reference. A finding that cannot name one
    # is not evidence, so it is not reported at all.
    return [finding for finding in findings if finding["evidence_refs"]]


def _open_owner_wait_refs(summary: dict[str, Any]) -> list[str]:
    """Cite the unfinished owner-wait step that put the trace in an owner wait."""
    refs = [
        step["step_id"]
        for step in summary["process"]["steps"]
        if step["ended_at"] is None
        and (step["kind"].startswith("wait_owner") or step["kind"] == "owner_clarification")
    ]
    return refs or [summary["trace_id"]]


def _regression_unresolved(summary: dict[str, Any]) -> bool:
    """True while something a regression broke is still unsatisfied."""
    if any(unit["review_state"] == "changes_requested" for unit in summary["work_graph"]["units"]):
        return True
    if any(invariant["state"] == "failed" for invariant in summary["invariants"]):
        return True
    return any(criterion["state"] == "failed" for criterion in summary["acceptance"]["criteria"])


def _classification_evidence(flow: dict[str, Any], kind: str) -> list[str]:
    for classification in flow["classifications"]:
        if classification["kind"] == kind:
            return classification["evidence_event_ids"][:4]
    return []


def _verdict(summary: dict[str, Any], findings: list[dict[str, Any]]) -> tuple[str, str]:
    """Stable precedence, highest authority first."""
    completion = summary["completion_state"]
    runtime = summary["runtime_state"]
    work_graph = summary["work_graph"]
    acceptance = summary["acceptance"]
    codes = {finding["code"] for finding in findings}

    # 1. Authoritative terminal resolution.
    if completion == "failed":
        return "terminal_failure", "TERMINAL_FAILURE"
    if completion == "cancelled":
        return "cancelled", "OWNER_CANCELLED"
    if completion == "abandoned":
        return "abandoned", "OWNER_ABANDONED"

    # 2. An active owner, dependency, provider, or policy block.
    if runtime["waiting"] == "owner":
        return "blocked", "AWAITING_OWNER"
    if work_graph["blocked_required_units"]:
        return "blocked", "WORK_UNIT_BLOCKED"
    if runtime["waiting"] in ("dependency", "provider_backoff", "approval"):
        return "blocked", f"BLOCKED_{runtime['waiting'].upper()}"
    if "DEFECT_POLICY_DENIAL" in codes:
        return "blocked", "POLICY_DENIAL"

    # 3. Required review changes.
    if "REVIEW_CHANGES_REQUESTED" in codes:
        return "changes_requested", "REVIEW_CHANGES_REQUESTED"

    # 4. Any other evidence-backed anomaly.
    anomaly_codes = [
        code
        for code in sorted(codes)
        if code
        in {
            "ACCEPTANCE_FAILED",
            "ACCEPTANCE_PASSED_WITHOUT_EVIDENCE",
            "INVARIANT_FAILED",
            "REGRESSION",
            "UNEXPLAINED_REVERSION",
            "SEMANTIC_LOOP",
            "COVERAGE_INCOMPLETE",
        }
        or code.startswith(("RUN_", "DEFECT_"))
    ]
    if anomaly_codes:
        return "attention", anomaly_codes[0]

    # 5. Unfinished required work or acceptance.
    if work_graph["open_required_units"] or not acceptance["complete"]:
        if work_graph["required_units"] or acceptance["criterion_count"]:
            return "work_remaining", "REQUIRED_WORK_OPEN"

    # 6-7. Settled mechanical state, then verified completion.
    if completion == "completion_candidate":
        return "completion_candidate", "AWAITING_MORFEO_VERIFICATION"
    if completion == "completed":
        return "completed", "VERIFIED_COMPLETION"
    if summary["source_event_count"] == 0:
        return "unknown", "NO_EVIDENCE"
    return "work_remaining", "IN_PROGRESS"


def _evidence_status(summary: dict[str, Any]) -> str:
    if summary["source_event_count"] == 0:
        return "unavailable"
    if not summary["coverage"]["complete"]:
        return "partial"
    surface = summary["capability_evidence"]["surface_coverage"]
    tokens = summary["model_context_economics"]["token_coverage"]
    if "unavailable" in (surface, tokens) or "partial" in (surface, tokens):
        return "partial"
    return "complete"


def _next_gate(summary: dict[str, Any], verdict: str) -> dict[str, Any]:
    """Exactly one gate. It names what must happen next, not a list of options."""
    work_graph = summary["work_graph"]
    acceptance = summary["acceptance"]
    runtime = summary["runtime_state"]

    if verdict in ("terminal_failure", "cancelled", "abandoned", "completed"):
        return {"kind": "none", "target_ref": None, "evidence_refs": []}
    if verdict == "completion_candidate":
        return {
            "kind": "morfeo_verification",
            "target_ref": summary.get("contract_id") or work_graph["root_task_ref"],
            "evidence_refs": [],
        }
    if runtime["waiting"] == "owner":
        return {"kind": "owner_decision", "target_ref": None, "evidence_refs": []}

    blocked = [
        unit
        for unit in work_graph["units"]
        if unit["required"] and unit["task_status"] == "blocked"
    ]
    if blocked:
        return {
            "kind": "dependency_resolution",
            "target_ref": blocked[0]["task_ref"],
            "evidence_refs": blocked[0]["evidence_event_ids"][:4],
        }
    rework = [
        unit
        for unit in work_graph["units"]
        if unit["required"] and unit["review_state"] == "changes_requested"
    ]
    if rework:
        return {
            "kind": "rework",
            "target_ref": rework[0]["task_ref"],
            "evidence_refs": rework[0]["evidence_event_ids"][:4],
        }
    pending_review = [
        unit
        for unit in work_graph["units"]
        if unit["required"] and unit["review_state"] == "pending"
    ]
    if pending_review:
        return {
            "kind": "review",
            "target_ref": pending_review[0]["task_ref"],
            "evidence_refs": pending_review[0]["evidence_event_ids"][:4],
        }
    open_units = [
        unit
        for unit in work_graph["units"]
        if unit["required"] and unit["task_status"] in ("triage", "todo", "scheduled", "ready")
    ]
    if open_units:
        return {
            "kind": "dispatch",
            "target_ref": open_units[0]["task_ref"],
            "evidence_refs": open_units[0]["evidence_event_ids"][:4],
        }
    running = [
        unit
        for unit in work_graph["units"]
        if unit["required"] and unit["task_status"] == "running"
    ]
    if running:
        return {
            "kind": "implementation",
            "target_ref": running[0]["task_ref"],
            "evidence_refs": running[0]["evidence_event_ids"][:4],
        }
    unfinished = [
        criterion
        for criterion in acceptance["criteria"]
        if criterion["state"] != "passed" or not criterion["evidence_refs"]
    ]
    if unfinished:
        return {
            "kind": "acceptance_verification",
            "target_ref": unfinished[0]["criterion_ref"],
            "evidence_refs": [unfinished[0]["last_event_id"]],
        }
    return {"kind": "unknown", "target_ref": None, "evidence_refs": []}
