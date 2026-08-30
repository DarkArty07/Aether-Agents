"""Deterministic human/diff projections of one observation summary.

Normative source: ``specs/002-aether-contract-observation/spec.md`` section 9.9
(OBS-FR-067..070), section 13.1, section 7.5, OBS-D-010, OBS-FR-057, OBS-FR-064,
OBS-FR-065, OBS-FR-066; the object shape rendered here is
``contracts/observation-summary.schema.json``.

Every function in this module is a pure projection of an already-reduced summary dict.
It never computes a summary, never reads the filesystem, never calls a model, and never
reads the wall clock: the same summary (and, for :func:`diff_summaries`, the same pair of
summaries) always renders to byte-identical text. Colour is never emitted: this module
has no notion of a terminal, so "no colour unless stdout is a TTY" is satisfied by never
emitting an escape code at all; a caller that wants colour applies it itself.
"""

from __future__ import annotations

from typing import Any

__all__ = ["diff_summaries", "render_brief", "render_since"]

# ----------------------------------------------------------------------------------
# OBS-FR-064: a judgment-sourced attribution must be visually and structurally
# distinguishable from a natively derived fact. The literal substring "JUDGMENT" is the
# one consistent marker used everywhere a `provenance` value is rendered, so the
# distinction is trivially greppable and never rendered as if it were measurement.
# ----------------------------------------------------------------------------------
_PROVENANCE_TAG: dict[str, str] = {
    "native_observed": "[OBSERVED]",
    "deterministic_derived": "[DERIVED]",
    "actor_declared": "[JUDGMENT:DECLARED]",
    "morfeo_judgment": "[JUDGMENT:MORFEO]",
    "undeclared": "[UNDECLARED]",
}

#: OBS field-coverage classes (``exact|partial|estimated|unavailable|not_applicable``).
#: ``exact`` is the silent baseline; every other value must stay visible (task brief).
_COVERAGE_TAG: dict[str, str] = {
    "exact": "",
    "partial": " [PARTIAL]",
    "estimated": " [ESTIMATED]",
    "unavailable": " [UNAVAILABLE]",
    "not_applicable": " [N/A]",
}

#: OBS-FR-069's bounded change-class vocabulary (mirrors contracts.CHANGE_CLASSES).
_CHANGE_CLASSES = (
    "verdict",
    "next_gate",
    "required_work",
    "acceptance",
    "anomaly",
    "bottleneck",
    "defect",
    "process",
    "configuration",
    "coverage",
)


def _provenance_tag(value: str | None) -> str:
    if value is None:
        return "[UNKNOWN]"
    return _PROVENANCE_TAG.get(value, f"[{value.upper()}]")


def _coverage_tag(value: str | None) -> str:
    if value is None:
        return " [UNKNOWN]"
    return _COVERAGE_TAG.get(value, f" [{value.upper()}]")


def _fmt_ms(value: int | None) -> str:
    """Render a millisecond duration without any locale- or timezone-dependent step."""
    if value is None:
        return "unknown"
    seconds, ms = divmod(value, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{value}ms ({hours}h{minutes:02d}m{seconds:02d}s)"
    if minutes:
        return f"{value}ms ({minutes}m{seconds:02d}s)"
    return f"{value}ms ({seconds}.{ms:03d}s)"


def _fmt_ts(value: str | None) -> str:
    return value if value else "unknown"


def _fmt_bool(value: bool | None) -> str:
    return {True: "yes", False: "no", None: "unknown"}[value]


def _refs(items: list[str] | tuple[str, ...], limit: int = 6) -> str:
    if not items:
        return "none"
    shown = list(items[:limit])
    text = ", ".join(shown)
    remaining = len(items) - len(shown)
    if remaining > 0:
        text += f" (+{remaining} more)"
    return text


def _clip(line: str, width: int) -> str:
    if len(line) <= width or width <= 3:
        return line
    return line[: width - 3] + "..."


def _participant_lookup(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["actor_id"]: p for p in summary.get("participants", [])}


def _participant_label(participants: dict[str, dict[str, Any]], ref: str | None) -> str:
    if ref is None:
        return "unknown participant"
    participant = participants.get(ref)
    if participant is None:
        return ref
    label = participant.get("profile") or participant.get("role") or participant["actor_kind"]
    return f"{label} ({ref})"


def _participant_matches(
    participants: dict[str, dict[str, Any]], ref: str | None, needle: str
) -> bool:
    if ref is None:
        return False
    participant = participants.get(ref)
    if participant is None:
        return needle in ref.lower()
    haystack = " ".join(
        value
        for value in (
            participant.get("profile"),
            participant.get("role"),
            participant["actor_kind"],
        )
        if value
    ).lower()
    return needle in haystack


# ----------------------------------------------------------------------------------
# Section builders. Each returns already-formatted lines; render_brief joins them in
# the OBS-FR-057 / cli.md section 13.1 order and clips every line to `width`.
# ----------------------------------------------------------------------------------


def _section_conclusion(summary: dict[str, Any]) -> list[str]:
    brief = summary["review_brief"]
    gate = brief["next_gate"]
    return [
        "CONCLUSION",
        f"  verdict: {brief['verdict'].upper().replace('_', ' ')}",
        f"  completion state: {summary['completion_state']}",
        f"  primary reason: {brief['primary_reason_code']}",
        f"  next gate (exactly one): {gate['kind']} -> {gate['target_ref'] or 'n/a'} "
        f"(evidence: {_refs(gate['evidence_refs'])})",
        f"  evidence status: {brief['evidence_status']}",
        f"  unfinished: {brief['unfinished_required_units']} required unit(s), "
        f"{brief['unfinished_acceptance_criteria']} acceptance criterion/criteria",
    ]


def _section_process(summary: dict[str, Any]) -> list[str]:
    process = summary["process"]
    steps = process["steps"]
    waves = process["waves"]
    rounds = process["rounds"]
    participants = _participant_lookup(summary)
    steps_by_id = {s["step_id"]: s for s in steps}

    lines = ["PROCESS RECONSTRUCTION (OBS-FR-051..057)"]

    for role_name in ("morfeo", "supervisor"):
        role_steps = [
            s
            for s in steps
            if _participant_matches(participants, s.get("participant_ref"), role_name)
        ]
        lines.append(f"  What {role_name.capitalize()} did:")
        if not role_steps:
            lines.append(f"    - no observed {role_name} action")
            continue
        for step in sorted(role_steps, key=lambda s: s["index"]):
            delta = _fmt_bool(step.get("semantic_delta"))
            lines.append(
                f"    - step {step['step_id']} [{step['index']}] {step['kind']} -> {step['outcome']} "
                f"(semantic delta: {delta}){_coverage_tag(step['coverage'])}"
            )

    lines.append("  Execution rounds, in order:")
    if not rounds:
        lines.append("    - no execution round observed")
    for round_ in sorted(rounds, key=lambda r: r["index"]):
        marker = " [REVIEW/REWORK RETURN]" if round_["trigger"] == "review_rework" else ""
        lines.append(
            f"    Round {round_['index']} [{round_['round_id']}]{marker} trigger={round_['trigger']} "
            f"outcome={round_['outcome']} deployed_units={round_['deployed_unit_count']} "
            f"duration={_fmt_ms(round_['duration_ms'])}"
        )
        round_waves = [w for w in waves if w["round_id"] == round_["round_id"]]
        for wave in round_waves:
            agents = _refs(
                [_participant_label(participants, ref) for ref in wave["participant_refs"]]
            )
            lines.append(
                f"      Wave {wave['wave_id']}: barrier={wave['barrier']} "
                f"deployed_units={wave['deployed_unit_count']} peak_parallelism={wave['peak_parallelism']} "
                f"duration={_fmt_ms(wave['duration_ms'])}"
            )
            lines.append(f"        agents/units: {agents}")
            lines.append(
                f"        eligible_observed={wave['eligible_unit_count_observed']} "
                f"ready_not_running={wave['ready_but_not_running_count_observed']} "
                f"({_fmt_ms(wave['ready_but_not_running_ms_observed'])}) "
                f"limits(global={wave['global_limit']}, per_profile={wave['per_profile_limit']}) "
                f"sampling_precision={wave['sampling_precision_ms']}ms"
            )
        direct_steps = [
            steps_by_id[sid]
            for sid in round_["step_ids"]
            if sid in steps_by_id and steps_by_id[sid].get("wave_id") is None
        ]
        for step in direct_steps:
            lines.append(
                f"      Step {step['step_id']} [{step['index']}] {step['kind']} by "
                f"{_participant_label(participants, step.get('participant_ref'))} -> "
                f"{step['outcome']}{_coverage_tag(step['coverage'])}"
            )

    review_returns = [
        u for u in summary["work_graph"]["units"] if u["review_state"] == "changes_requested"
    ]
    lines.append("  Review/rework returns:")
    if not review_returns:
        lines.append("    - none observed")
    else:
        for unit in review_returns:
            lines.append(f"    - {unit['task_ref']} ({unit['relation']}): changes requested")

    critical_path = process["critical_path"]
    lines.append(f"  Critical path{_coverage_tag(critical_path['coverage'])}:")
    if not critical_path["step_ids"]:
        lines.append("    - no critical-path step observed")
    else:
        for step_id in critical_path["step_ids"]:
            step = steps_by_id.get(step_id)
            if step is None:
                lines.append(f"    - {step_id} (unresolved step reference)")
            else:
                lines.append(
                    f"    - {step_id}: {step['kind']} by {_participant_label(participants, step.get('participant_ref'))}"
                )
    return lines


def _section_tools(summary: dict[str, Any]) -> list[str]:
    tools = summary["tools"]
    anomalous = (
        tools["failed"]
        + tools["blocked"]
        + tools["cancelled"]
        + tools["timed_out"]
        + tools["interrupted"]
        + tools["unknown"]
        + tools["technical_retries"]
    ) > 0
    lines = [
        "TOOL TOTALS, AGGREGATE (after the process reconstruction; summarized unless anomalous)"
    ]
    lines.append(
        f"  calls={tools['total_calls']} duration={_fmt_ms(tools['total_duration_ms'])} "
        f"completed={tools['completed']} failed={tools['failed']} blocked={tools['blocked']} "
        f"cancelled={tools['cancelled']} timed_out={tools['timed_out']} interrupted={tools['interrupted']} "
        f"unknown={tools['unknown']} technical_retries={tools['technical_retries']}"
    )
    if not anomalous:
        lines.append("  no tool anomaly observed; per-tool/per-actor detail omitted")
        return lines
    lines.append("  ANOMALY OBSERVED — full breakdown follows")
    for bucket in tools["by_name"]:
        lines.append(
            f"    - {bucket['name']}: calls={bucket['calls']} duration={_fmt_ms(bucket['duration_ms'])} "
            f"completed={bucket['completed']} failed={bucket['failed']} blocked={bucket['blocked']} "
            f"cancelled={bucket['cancelled']} timed_out={bucket['timed_out']} interrupted={bucket['interrupted']} "
            f"unknown={bucket['unknown']}"
        )
    for actor in tools["by_actor"]:
        lines.append(
            f"    - actor {actor['actor_kind']}:{actor['actor_id']}: calls={actor['calls']} "
            f"duration={_fmt_ms(actor['total_duration_ms'])} failed={actor['failed']} blocked={actor['blocked']}"
        )
    return lines


def _section_current_state(summary: dict[str, Any]) -> list[str]:
    rs = summary["runtime_state"]
    return [
        "CURRENT STATE (six independent dimensions, section 7.5 / OBS-FR-044 — never collapsed)",
        f"  liveness:    {rs['liveness']}",
        f"  activity:    {rs['activity']}",
        f"  progress:    {rs['progress']}",
        f"  waiting:     {rs['waiting']}",
        f"  anomalies:   {rs['anomalies']}",
        f"  termination: {rs['termination']}",
    ]


def _section_verified_progress(summary: dict[str, Any]) -> list[str]:
    flow = summary["flow"]
    dur = summary["duration"]
    ts = summary["timestamps"]
    return [
        "VERIFIED PROGRESS",
        f"  last verified progress at: {_fmt_ts(ts['last_verified_progress_at'])}",
        f"  useful iterations: {flow['useful_iterations']}  revisions: {flow['revision_count']}",
        "  lifecycle milestones:",
        f"    started={_fmt_ts(ts['started_at'])} first_action={_fmt_ts(ts['first_action_at'])} "
        f"executable={_fmt_ts(ts['executable_at'])} persisted={_fmt_ts(ts['persisted_at'])}",
        f"    handed_off={_fmt_ts(ts['handed_off_at'])} execution_started={_fmt_ts(ts['execution_started_at'])}",
        f"    completed={_fmt_ts(ts['completed_at'])} terminated={_fmt_ts(ts['terminated_at'])} "
        f"closed={_fmt_ts(ts['closed_at'])}",
        "  duration breakdown (unioned wall time; unclassified stays visible, never folded into active/wait):",
        f"    wall={_fmt_ms(dur['wall_ms'])} active={_fmt_ms(dur['active_ms'])} "
        f"owner_wait={_fmt_ms(dur['owner_wait_ms'])} external_wait={_fmt_ms(dur['external_wait_ms'])}",
        f"    review_wait={_fmt_ms(dur['review_wait_ms'])} unclassified={_fmt_ms(dur['unclassified_ms'])} "
        f"overlap={_fmt_ms(dur['overlap_ms'])}",
        f"    contract_creation={_fmt_ms(dur['contract_creation_ms'])} "
        f"dispatch_latency={_fmt_ms(dur['dispatch_latency_ms'])} execution={_fmt_ms(dur['execution_ms'])} "
        f"handoff_latency={_fmt_ms(dur['handoff_latency_ms'])}",
    ]


def _section_blockers(summary: dict[str, Any]) -> list[str]:
    lines = ["BLOCKERS & ANOMALIES"]
    findings = summary["review_brief"]["findings"]
    if not findings:
        lines.append("  - no finding reported")
    for finding in findings:
        lines.append(
            f"  - [{finding['severity'].upper()}] {finding['code']} {_provenance_tag(finding['provenance'])} "
            f"critical_path={_fmt_bool(finding['on_critical_path'])} evidence={_refs(finding['evidence_refs'])}"
        )
    bottlenecks = summary["bottlenecks"]
    lines.append("  Bottleneck attributions:")
    if not bottlenecks:
        lines.append("    - none observed")
    for bottleneck in bottlenecks:
        lines.append(
            f"    - {bottleneck['class']} {_provenance_tag(bottleneck['provenance'])} "
            f"duration={_fmt_ms(bottleneck['duration_ms'])} evidence={_refs(bottleneck['evidence_refs'])}"
        )
    defects = summary["defect_attributions"]
    lines.append("  Defect attributions:")
    if not defects:
        lines.append("    - none observed")
    for defect in defects:
        lines.append(
            f"    - {defect['class']} {_provenance_tag(defect['provenance'])} evidence={_refs(defect['evidence_refs'])}"
        )
    return lines


def _section_unfinished(summary: dict[str, Any]) -> list[str]:
    wg = summary["work_graph"]
    acc = summary["acceptance"]
    lines = ["UNFINISHED REQUIRED WORK & ACCEPTANCE"]
    lines.append(
        f"  required units: {wg['required_units']}  done={wg['done_required_units']} "
        f"open={wg['open_required_units']} blocked={wg['blocked_required_units']} "
        f"in_review={wg['review_required_units']} all_required_done={wg['all_required_done']}"
    )
    open_units = [u for u in wg["units"] if u["required"] and u["task_status"] != "done"]
    if open_units:
        lines.append("  open required units:")
        for unit in open_units:
            lines.append(
                f"    - {unit['task_ref']} ({unit['relation']}): status={unit['task_status']} "
                f"review={unit['review_state']}"
            )
    lines.append(
        f"  acceptance criteria: {acc['criterion_count']} passed={acc['passed']} failed={acc['failed']} "
        f"pending={acc['pending']} unknown={acc['unknown']} complete={acc['complete']}"
    )
    for criterion in acc["criteria"]:
        if criterion["state"] != "passed":
            lines.append(f"    - {criterion['criterion_ref']}: {criterion['state']}")
    return lines


def _section_critical_path_evidence(summary: dict[str, Any]) -> list[str]:
    cp = summary["process"]["critical_path"]
    waves = summary["process"]["waves"]
    lines = ["CRITICAL PATH & ACCELERATION EVIDENCE (OBS-FR-056 — facts only, no recommendation)"]
    lines.append(
        f"  duration={_fmt_ms(cp['duration_ms'])} dispatch_wait={_fmt_ms(cp['dispatch_wait_ms'])} "
        f"dependency_wait={_fmt_ms(cp['dependency_wait_ms'])} review_wait={_fmt_ms(cp['review_wait_ms'])} "
        f"rework={_fmt_ms(cp['rework_ms'])}{_coverage_tag(cp['coverage'])}"
    )
    if not waves:
        lines.append("  no parallel wave observed")
        return lines
    peak = max(w["peak_parallelism"] for w in waves)
    max_eligible = max((w["eligible_unit_count_observed"] or 0) for w in waves)
    max_deployed = max(w["deployed_unit_count"] for w in waves)
    limits = sorted(
        {
            (w["global_limit"], w["per_profile_limit"])
            for w in waves
            if w["global_limit"] is not None or w["per_profile_limit"] is not None
        }
    )
    lines.append(
        f"  observed peak parallelism={peak}  max eligible units observed={max_eligible}  "
        f"max deployed units={max_deployed}"
    )
    lines.append(
        f"  captured concurrency limits (global, per_profile): {limits if limits else 'none captured'}"
    )
    return lines


def _section_configuration(summary: dict[str, Any]) -> list[str]:
    lines = ["CONFIGURATION / TOOL / MODEL COVERAGE"]
    fingerprints = summary["configuration_fingerprints"]
    if not fingerprints:
        lines.append("  - no configuration fingerprint recorded")
    for fp in fingerprints:
        lines.append(
            f"  - scope={fp['scope']} participant={fp['participant_ref'] or 'trace-level'} "
            f"model={fp['model'] or 'unknown'} provider={fp['provider'] or 'unknown'} "
            f"key_id={fp['fingerprint_key_id']}"
        )
        for field_name in sorted(fp["field_coverage"]):
            coverage = fp["field_coverage"][field_name]
            if coverage != "exact":
                lines.append(f"      {field_name}:{_coverage_tag(coverage)}")

    cap = summary["capability_evidence"]
    lines.append(
        f"  tool surface coverage={cap['surface_coverage']} observed_tool_count={cap['observed_tool_count']}"
    )
    lines.append(f"    granted={_refs(cap['granted_tool_refs'])}")
    lines.append(f"    used={_refs(cap['used_tool_refs'])}")
    if cap["surface_coverage"] == "exact":
        lines.append(f"    never_used={_refs(cap['never_used_tool_refs'])}")
    else:
        lines.append("    never_used: unavailable (surface coverage is not exact; OBS-FR-059)")
    lines.append(
        f"    failed={_refs(cap['failed_tool_refs'])}  denied={_refs(cap['denied_tool_refs'])}"
    )
    lines.append(f"    loaded skills={_refs(cap['loaded_skill_refs'])}")

    mce = summary["model_context_economics"]
    lines.append(
        f"  model requests={mce['request_count']} failed={mce['failed_request_count']} "
        f"attempts={mce['attempt_count']} duration={_fmt_ms(mce['duration_ms'])}"
    )
    tokens = mce["tokens"]
    lines.append(
        f"    tokens: input={tokens['input_tokens']} output={tokens['output_tokens']} "
        f"cache_read={tokens['cache_read_tokens']} cache_write={tokens['cache_write_tokens']} "
        f"total={tokens['total_tokens']}{_coverage_tag(mce['token_coverage'])}"
    )
    return lines


def _section_execution_quality(summary: dict[str, Any]) -> list[str]:
    flow = summary["flow"]
    mce = summary["model_context_economics"]
    lines = ["EXECUTION QUALITY"]
    lines.append(
        f"  useful_iterations={flow['useful_iterations']} technical_retries={flow['technical_retries']} "
        f"cycles={flow['cycles']} semantic_loops={flow['semantic_loops']} regressions={flow['regressions']}"
    )
    lines.append(
        f"  authorized_reversions={flow['authorized_reversions']} "
        f"unexplained_reversions={flow['unexplained_reversions']} "
        f"owner_direction_changes={flow['owner_direction_changes']}"
    )
    invariants = summary["invariants"]
    not_passed = [i for i in invariants if i["state"] != "passed"]
    lines.append(f"  invariants: {len(invariants)} recorded, {len(not_passed)} not passed")
    for inv in not_passed:
        lines.append(f"    - {inv['key']}: {inv['state']}")
    lines.append(
        f"  protocol_violations={mce['protocol_violation_count']} "
        f"invalid_arguments={mce['invalid_argument_count']}{_coverage_tag(mce['invalid_argument_coverage'])} "
        f"turns={mce['turns']} turns_without_semantic_delta={mce['turns_without_semantic_delta']}"
    )
    if mce["finish_reasons"]:
        parts = ", ".join(
            f"{key}={mce['finish_reasons'][key]}" for key in sorted(mce["finish_reasons"])
        )
        lines.append(f"  finish reasons: {parts}")
    return lines


def _section_evidence_coverage(summary: dict[str, Any]) -> list[str]:
    coverage = summary["coverage"]
    provenance = summary["provenance"]
    improvement = summary["improvement_evidence"]
    lines = ["EVIDENCE COVERAGE"]
    lines.append(f"  source events analyzed: {summary['source_event_count']}")
    lines.append(f"  coverage complete={coverage['complete']} gap_count={coverage['gap_count']}")
    for gap in coverage["gaps"]:
        lines.append(f"    - {gap['class']} ({gap['reason_code']}) evt={gap['event_id']}")
    lines.append(f"  producers={provenance['producer_count']}")
    for pair in provenance["compatibility_pairs"]:
        lines.append(
            f"    - collector={pair['collector_version']} runtime_fingerprint={pair['runtime_fingerprint'][:12]}.."
        )

    # OBS-FR-065: a single-trace signal is always labeled anecdotal, never presented as
    # an established pattern; insufficient_evidence stays a first-class visible value.
    # OBS-FR-066: `automated_recommendation` is schema-fixed to null and is never
    # mentioned in prose here — there is nothing to render.
    count = improvement["supporting_trace_count"]
    strength = improvement["strength"]
    if count == 1 or strength == "anecdotal":
        label = "ANECDOTAL (single trace observed — not an established pattern)"
    else:
        label = strength
    lines.append(f"  improvement evidence: supporting_trace_count={count} strength={label}")
    if count == 1 and strength != "anecdotal":
        lines.append(
            f"    (coverage note: stored strength={strength!r} disagrees with supporting_trace_count=1)"
        )
    return lines


def _section_next_decision(summary: dict[str, Any]) -> list[str]:
    gate = summary["review_brief"]["next_gate"]
    return [
        "NEXT DECISION REQUIRED",
        f"  {gate['kind']} -> {gate['target_ref'] or 'n/a'}  (evidence: {_refs(gate['evidence_refs'])})",
    ]


def render_since(current: dict[str, Any], previous: dict[str, Any]) -> str:
    """Render the OBS-FR-069 "changes since" block for one prior summary.

    Pure function of the two summaries; used standalone and by :func:`render_brief`
    when its ``since`` argument is supplied.
    """
    diff = diff_summaries(current, previous)
    prev_id = previous.get("summary_id", "unknown")
    if not diff["comparable"]:
        return f"Changes since {prev_id}: COMPARISON UNAVAILABLE ({diff['error']})."
    lines = [f"Changes since {prev_id}:"]
    if diff["fingerprint_boundary"]:
        lines.append(
            "  - configuration fingerprint key epoch differs (comparison boundary, not a configuration change)"
        )
    if not diff["change_classes"]:
        lines.append(
            "  - no semantic change detected (token/tool-count growth alone does not count)"
        )
    else:
        for change_class in diff["change_classes"]:
            lines.append(f"  - {change_class}")
    return "\n".join(lines)


def render_brief(
    summary: dict[str, Any], *, since: dict[str, Any] | None = None, width: int = 100
) -> str:
    """Render the default ``aether observe`` human review brief (OBS-FR-057).

    Section order is normative: conclusion; causal process reconstruction; aggregate
    tool totals (summarized unless anomalous); current state (six independent
    dimensions); verified progress; blockers/anomalies; unfinished required work and
    acceptance; critical-path/acceleration evidence; configuration/tool/model coverage;
    execution quality; evidence coverage; next decision.
    """
    lines: list[str] = []
    contract_id = summary.get("contract_id")
    lines.append(f"Aether contract observation — trace {summary['trace_id']}")
    if contract_id:
        lines.append(f"Contract: {contract_id}")
    lines.append(
        f"Summary: {summary['summary_id']}  |  as of {summary['as_of']}  |  reducer {summary['reducer_version']}"
    )
    lines.append("")

    lines.extend(_section_conclusion(summary))
    if since is not None:
        lines.append("")
        lines.append(render_since(summary, since))
    lines.append("")
    lines.extend(_section_process(summary))
    lines.append("")
    lines.extend(_section_tools(summary))
    lines.append("")
    lines.extend(_section_current_state(summary))
    lines.append("")
    lines.extend(_section_verified_progress(summary))
    lines.append("")
    lines.extend(_section_blockers(summary))
    lines.append("")
    lines.extend(_section_unfinished(summary))
    lines.append("")
    lines.extend(_section_critical_path_evidence(summary))
    lines.append("")
    lines.extend(_section_configuration(summary))
    lines.append("")
    lines.extend(_section_execution_quality(summary))
    lines.append("")
    lines.extend(_section_evidence_coverage(summary))
    lines.append("")
    lines.extend(_section_next_decision(summary))

    clipped: list[str] = []
    for line in lines:
        for physical in line.split("\n"):
            clipped.append(_clip(physical, width))
    return "\n".join(clipped)


def diff_summaries(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Compare two summaries of the same trace per OBS-FR-069.

    Reports only semantic changes in verdict, next gate, required work/acceptance,
    anomaly/bottleneck/defect set, process structure, comparable configuration
    fingerprint, or coverage. Token/tool-count growth alone is never a semantic change
    unless it creates an anomaly or coverage transition (those two are compared, raw
    counters are not). A different ``fingerprint_key_id`` is reported as a comparison
    boundary, never as a configuration change. Incompatible summary schema versions or a
    mismatched trace return a bounded comparison error instead of a manufactured diff.
    """
    result: dict[str, Any] = {
        "comparable": True,
        "error": None,
        "trace_id": current.get("trace_id"),
        "current_summary_id": current.get("summary_id"),
        "previous_summary_id": previous.get("summary_id"),
        "change_classes": [],
        "fingerprint_boundary": False,
        "details": [],
    }

    if current.get("schema_version") != previous.get("schema_version"):
        result["comparable"] = False
        result["error"] = "SCHEMA_VERSION_INCOMPATIBLE"
        return result
    if current.get("trace_id") != previous.get("trace_id"):
        result["comparable"] = False
        result["error"] = "DIFFERENT_TRACE"
        return result

    changes: set[str] = set()
    details: list[dict[str, Any]] = []

    cur_brief = current.get("review_brief", {})
    prev_brief = previous.get("review_brief", {})

    if cur_brief.get("verdict") != prev_brief.get("verdict"):
        changes.add("verdict")
        details.append(
            {"class": "verdict", "from": prev_brief.get("verdict"), "to": cur_brief.get("verdict")}
        )

    cur_gate = cur_brief.get("next_gate", {})
    prev_gate = prev_brief.get("next_gate", {})
    if (cur_gate.get("kind"), cur_gate.get("target_ref")) != (
        prev_gate.get("kind"),
        prev_gate.get("target_ref"),
    ):
        changes.add("next_gate")
        details.append(
            {"class": "next_gate", "from": prev_gate.get("kind"), "to": cur_gate.get("kind")}
        )

    if (
        cur_brief.get("unfinished_required_units"),
        cur_brief.get("unfinished_acceptance_criteria"),
    ) != (
        prev_brief.get("unfinished_required_units"),
        prev_brief.get("unfinished_acceptance_criteria"),
    ):
        changes.add("required_work")
        details.append({"class": "required_work"})

    def _criteria_signature(summary: dict[str, Any]) -> frozenset:
        return frozenset(
            (c["criterion_ref"], c["state"])
            for c in summary.get("acceptance", {}).get("criteria", [])
        )

    if _criteria_signature(current) != _criteria_signature(previous):
        changes.add("acceptance")
        details.append({"class": "acceptance"})

    def _finding_signature(summary: dict[str, Any]) -> frozenset:
        return frozenset(
            (f["code"], f["severity"]) for f in summary.get("review_brief", {}).get("findings", [])
        )

    anomaly_changed = current.get("runtime_state", {}).get("anomalies") != previous.get(
        "runtime_state", {}
    ).get("anomalies") or _finding_signature(current) != _finding_signature(previous)
    if anomaly_changed:
        changes.add("anomaly")
        details.append({"class": "anomaly"})

    def _bottleneck_signature(summary: dict[str, Any]) -> frozenset:
        return frozenset((b["class"], b["provenance"]) for b in summary.get("bottlenecks", []))

    if _bottleneck_signature(current) != _bottleneck_signature(previous):
        changes.add("bottleneck")
        details.append({"class": "bottleneck"})

    def _defect_signature(summary: dict[str, Any]) -> frozenset:
        return frozenset(
            (d["class"], d["provenance"]) for d in summary.get("defect_attributions", [])
        )

    if _defect_signature(current) != _defect_signature(previous):
        changes.add("defect")
        details.append({"class": "defect"})

    def _process_signature(summary: dict[str, Any]) -> tuple:
        process = summary.get("process", {})
        rounds = tuple(sorted((r["index"], r["trigger"]) for r in process.get("rounds", [])))
        waves = tuple(sorted((w["round_id"], w["barrier"]) for w in process.get("waves", [])))
        steps = tuple(sorted((s["index"], s["kind"]) for s in process.get("steps", [])))
        critical_path = tuple(process.get("critical_path", {}).get("step_ids", []))
        return (rounds, waves, steps, critical_path)

    if _process_signature(current) != _process_signature(previous):
        changes.add("process")
        details.append({"class": "process"})

    # OBS-FR-058/069: a differing `fingerprint_key_id` is a comparison boundary, not a
    # configuration change, so it is tracked separately from `changes`.
    fingerprint_boundary = False

    def _fingerprint_index(summary: dict[str, Any]) -> dict[tuple, dict[str, Any]]:
        return {
            (fp["scope"], fp["participant_ref"]): fp
            for fp in summary.get("configuration_fingerprints", [])
        }

    cur_fps = _fingerprint_index(current)
    prev_fps = _fingerprint_index(previous)
    comparable_fields = (
        "model",
        "provider",
        "system_prompt_fingerprint",
        "observed_skill_set_fingerprint",
        "declared_toolset_fingerprint",
        "effective_tool_surface_fingerprint",
        "global_concurrency_limit",
        "per_profile_concurrency_limit",
    )
    for key in set(cur_fps) & set(prev_fps):
        cur_fp, prev_fp = cur_fps[key], prev_fps[key]
        if cur_fp.get("fingerprint_key_id") != prev_fp.get("fingerprint_key_id"):
            fingerprint_boundary = True
            continue
        if any(
            cur_fp.get(field_name) != prev_fp.get(field_name) for field_name in comparable_fields
        ):
            changes.add("configuration")
            details.append({"class": "configuration", "scope": key[0]})
    result["fingerprint_boundary"] = fingerprint_boundary

    cur_coverage = current.get("coverage", {})
    prev_coverage = previous.get("coverage", {})
    coverage_changed = cur_coverage.get("complete") != prev_coverage.get("complete")
    if not coverage_changed:
        cur_gap_classes = frozenset(g["class"] for g in cur_coverage.get("gaps", []))
        prev_gap_classes = frozenset(g["class"] for g in prev_coverage.get("gaps", []))
        coverage_changed = cur_gap_classes != prev_gap_classes
    if coverage_changed:
        changes.add("coverage")
        details.append({"class": "coverage"})

    result["change_classes"] = sorted(changes)
    result["details"] = details
    return result
