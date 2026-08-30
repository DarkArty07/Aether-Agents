from __future__ import annotations

import json
from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest
from observation_helpers import EPOCH, EventFactory, complete_trace, native_pseudonym

from aether_agents.observation.checkpoint import AuthorityContext
from aether_agents.observation.contracts import (
    canonical_digest,
    canonical_json_bytes,
    validate_event,
)
from aether_agents.observation.reduce.process import build_process, causal_order
from aether_agents.observation.reduce.reconciliation import (
    ReconciliationReport,
    dedupe,
    derive_gaps,
)
from aether_agents.observation.reduce.reducer import ReductionInput, reduce_events


def test_complete_pipeline_matches_the_reviewed_golden_summary_byte_for_byte() -> None:
    expected = json.loads(
        (Path(__file__).parent / "fixtures" / "observation" / "complete-summary.json").read_text(
            encoding="utf-8"
        )
    )
    actual = complete_trace().summary()
    assert actual == expected
    assert canonical_json_bytes(actual) == canonical_json_bytes(expected)


def _tool_start(
    f: EventFactory,
    seconds: float,
    call_id: str,
    *,
    session: str = "session-1",
    actor: str = "implementer",
    name: str = "terminal.exec",
):
    return f.add(
        f.builder.tool_started(
            call_id=native_pseudonym("tool_call", call_id),
            name=name,
            category="terminal",
            occurred_at=f.at(seconds),
            session_id=native_pseudonym("session", session),
            turn_id=native_pseudonym("turn", "turn-1"),
            api_request_id=native_pseudonym("api_request", "request-1"),
            actor_kind="agent",
            actor_id=actor,
            profile=actor,
        )
    )


def _tool_end(
    f: EventFactory,
    seconds: float,
    call_id: str,
    status: str,
    *,
    duration_ms: int = 1000,
    session: str = "session-1",
    actor: str = "implementer",
    name: str = "terminal.exec",
    retry_of: str | None = None,
    approval: str | None = None,
    error_class: str | None = None,
):
    return f.add(
        f.builder.tool_terminal(
            call_id=native_pseudonym("tool_call", call_id),
            name=name,
            category="terminal",
            status=status,
            duration_ms=duration_ms,
            retry_of_call_id=(
                native_pseudonym("tool_call", retry_of) if retry_of is not None else None
            ),
            approval_outcome=approval,
            error_class=error_class,
            occurred_at=f.at(seconds),
            session_id=native_pseudonym("session", session),
            turn_id=native_pseudonym("turn", "turn-1"),
            api_request_id=native_pseudonym("api_request", "request-1"),
            actor_kind="agent",
            actor_id=actor,
            profile=actor,
        )
    )


def test_straight_line_creation_has_exact_origin_and_creation_duration() -> None:
    f = EventFactory()
    f.opened(0)
    f.contract("contract.executable", "passed", 2, semantic_delta="invariant")
    f.contract(
        "contract.persisted",
        "completed",
        5,
        revision=1,
        after_sha256="a" * 64,
        semantic_delta="revision",
    )
    summary = f.summary()
    assert summary["timestamps"]["started_at"].endswith("03:04:05.000Z")
    assert summary["duration"]["contract_creation_ms"] == 5000
    assert summary["duration"]["time_to_executable_ms"] == 2000
    assert summary["completion_state"] == "persisted"


def test_unknown_origin_never_uses_materialization_time_as_started_at() -> None:
    f = EventFactory()
    f.opened(0, origin=None)
    f.contract("contract.persisted", "completed", 4, revision=1, after_sha256="a" * 64)
    summary = f.summary()
    assert summary["timestamps"]["started_at"] is None
    for key in (
        "wall_ms",
        "contract_creation_ms",
        "time_to_first_action_ms",
        "time_to_completion_ms",
    ):
        assert summary["duration"][key] is None


def test_owner_clarification_wait_is_partitioned_without_double_counting() -> None:
    f = EventFactory()
    f.opened(0)
    f.contract("clarification.requested", "started", 1, ambiguity_ref="ambiguity-1")
    f.contract("clarification.resolved", "completed", 4, ambiguity_ref="ambiguity-1")
    summary = f.summary()
    assert summary["duration"]["wall_ms"] == 4000
    assert summary["duration"]["owner_wait_ms"] == 3000
    assert summary["duration"]["unclassified_ms"] == 1000
    assert summary["runtime_state"]["waiting"] == "none"


def test_parallel_tool_calls_keep_exact_totals_but_union_active_time() -> None:
    f = EventFactory()
    f.opened(0)
    _tool_start(f, 1, "call-a")
    _tool_start(f, 2, "call-b", name="file.read")
    _tool_end(f, 4, "call-a", "completed", duration_ms=3000)
    _tool_end(f, 5, "call-b", "completed", duration_ms=3000, name="file.read")
    summary = f.summary()
    assert summary["tools"]["total_calls"] == 2
    assert summary["tools"]["total_duration_ms"] == 6000
    assert summary["duration"]["active_ms"] == 4000
    assert summary["duration"]["overlap_ms"] == 2000


@pytest.mark.parametrize(
    "status", ["completed", "failed", "blocked", "cancelled", "timed_out", "interrupted", "unknown"]
)
def test_every_terminal_tool_outcome_remains_a_distinct_total(status: str) -> None:
    f = EventFactory()
    f.opened(0)
    _tool_start(f, 1, "call")
    _tool_end(f, 2, "call", status)
    tools = f.summary()["tools"]
    assert tools["total_calls"] == 1
    assert tools[status] == 1
    assert (
        sum(
            tools[key]
            for key in (
                "completed",
                "failed",
                "blocked",
                "cancelled",
                "timed_out",
                "interrupted",
                "unknown",
            )
        )
        == 1
    )


def test_tool_failure_and_linked_retry_are_counted_once_in_same_session() -> None:
    f = EventFactory()
    f.opened(0)
    _tool_start(f, 1, "first")
    _tool_end(f, 2, "first", "failed")
    _tool_start(f, 3, "retry")
    _tool_end(f, 4, "retry", "completed", retry_of="first")
    summary = f.summary()
    assert summary["tools"]["technical_retries"] == 1
    assert summary["flow"]["technical_retries"] == 1


def test_retry_reference_cannot_cross_native_sessions() -> None:
    f = EventFactory()
    f.opened(0)
    _tool_start(f, 1, "same-id", session="session-a")
    _tool_end(f, 2, "same-id", "failed", session="session-a")
    _tool_start(f, 3, "new", session="session-b")
    _tool_end(f, 4, "new", "completed", session="session-b", retry_of="same-id")
    assert f.summary()["flow"]["technical_retries"] == 0


def test_useful_revision_and_two_zero_delta_cycles_are_distinguishable() -> None:
    f = EventFactory()
    f.opened(0)
    for second in (1, 2, 3):
        f.contract(
            "contract.revision",
            "reported",
            second,
            revision=second,
            after_sha256="a" * 64,
            semantic_delta="none" if second > 1 else "revision",
        )
    flow = f.summary()["flow"]
    assert flow["useful_iterations"] == 1
    assert flow["cycles"] == 2
    assert flow["semantic_loops"] == 1


def test_initial_failure_is_not_regression_but_pass_to_fail_is() -> None:
    initial = EventFactory()
    initial.opened(0)
    initial.contract("invariant.failed", "failed", 1, invariant_key="OBS-INV-001")
    assert initial.summary()["flow"]["regressions"] == 0

    transitioned = EventFactory()
    transitioned.opened(0)
    transitioned.contract("invariant.passed", "passed", 1, invariant_key="OBS-INV-001")
    transitioned.contract("invariant.failed", "failed", 2, invariant_key="OBS-INV-001")
    summary = transitioned.summary()
    assert summary["flow"]["regressions"] == 1
    assert "REGRESSION" in {item["code"] for item in summary["review_brief"]["findings"]}


def test_parent_linked_owner_supersession_authorizes_changed_assertion() -> None:
    f = EventFactory()
    f.opened(0)
    f.contract("invariant.passed", "passed", 1, invariant_key="OBS-INV-001")
    decision = f.contract(
        "decision.superseded",
        "superseded",
        2,
        decision_refs=("decision-2",),
        supersedes_decision_ref="decision-1",
        semantic_delta="decision",
    )
    failed = f.builder.contract(
        event_type="invariant.failed",
        status="failed",
        invariant_key="OBS-INV-001",
        occurred_at=f.at(3),
        parent_event_id=decision["event_id"],
        source_kind="aether_checkpoint",
        actor_kind="agent",
        actor_id="morfeo",
        profile="morfeo",
        role="verification",
    )
    f.add(failed)
    assert f.summary()["flow"]["regressions"] == 0


def test_authorized_and_unexplained_reversions_are_separate() -> None:
    unexplained = EventFactory()
    unexplained.opened(0)
    for second, digest in ((1, "a" * 64), (2, "b" * 64), (3, "a" * 64)):
        unexplained.contract(
            "contract.revision", "reported", second, revision=second, after_sha256=digest
        )
    assert unexplained.summary()["flow"]["unexplained_reversions"] == 1

    authorized = EventFactory()
    authorized.opened(0)
    authorized.contract("contract.revision", "reported", 1, revision=1, after_sha256="a" * 64)
    authorized.contract("contract.revision", "reported", 2, revision=2, after_sha256="b" * 64)
    authorized.contract(
        "contract.revision",
        "reported",
        3,
        revision=3,
        after_sha256="a" * 64,
        supersedes_decision_ref="decision-1",
    )
    assert authorized.summary()["flow"]["authorized_reversions"] == 1
    assert authorized.summary()["flow"]["unexplained_reversions"] == 0


def test_subagent_requires_both_linked_start_and_terminal_observation() -> None:
    f = EventFactory()
    f.opened(0)
    f.event(
        "participant.joined",
        "started",
        1,
        actor_kind="subagent",
        actor_id="child-only-start",
        profile="implementer",
    )
    participants = f.summary()["participants"]
    assert "child-only-start" not in {record["actor_id"] for record in participants}
    assert "implementer-1" in {
        record["actor_id"] for record in complete_trace().summary()["participants"]
    }


def test_unpaired_tool_start_is_one_gap_and_zero_terminal_calls() -> None:
    f = EventFactory()
    f.opened(0)
    _tool_start(f, 1, "lost-terminal")
    summary = f.summary()
    assert summary["tools"]["total_calls"] == 0
    assert [gap["reason_code"] for gap in summary["coverage"]["gaps"]] == ["TOOL_SPAN_UNPAIRED"]


def test_producer_sequence_beats_reversed_wall_clock_and_surfaces_gap() -> None:
    f = EventFactory()
    f.opened(5)
    f.contract("contract.persisted", "completed", 4, revision=1, after_sha256="a" * 64)
    summary = f.summary()
    assert [event["event_id"] for event in causal_order(f.events)] == [
        f.events[0]["event_id"],
        f.events[1]["event_id"],
    ]
    assert summary["process"]["steps"][0]["evidence_event_ids"] == [f.events[1]["event_id"]]
    assert any(gap["class"] == "clock_anomaly" for gap in summary["coverage"]["gaps"])


def test_process_restart_keeps_compatibility_pairs_and_explicit_parent_order() -> None:
    f = EventFactory()
    f.opened(0)
    first = f.contract("contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64)
    resumed = f.builder.contract(
        event_type="trace.resumed",
        status="started",
        origin_message_id=7,
        occurred_at=f.at(-5),
        timestamp_source="reconciled",
        parent_event_id=first["event_id"],
    )
    f.add(resumed)
    revision = f.builder.contract(
        event_type="contract.revision",
        status="reported",
        revision=2,
        after_sha256="b" * 64,
        occurred_at=f.at(-4),
        parent_event_id=resumed["event_id"],
    )
    f.add(revision)
    for sequence, event in enumerate((resumed, revision)):
        event["producer_epoch"] = "prd_" + "9" * 32
        event["producer_seq"] = sequence
        event["collector_version"] = "9.9.9"
        event["runtime_fingerprint"] = "8" * 64
    summary = f.summary()
    assert summary["provenance"]["producer_count"] == 2
    assert len(summary["provenance"]["compatibility_pairs"]) == 2
    assert [step["evidence_event_ids"][0] for step in summary["process"]["steps"]] == [
        first["event_id"],
        revision["event_id"],
    ]


def test_tool_equations_reconcile_globally_by_name_and_actor() -> None:
    f = EventFactory()
    f.opened(0)
    for index, (name, actor, status) in enumerate(
        (
            ("file.read", "a", "completed"),
            ("file.read", "b", "failed"),
            ("terminal.exec", "a", "blocked"),
        ),
        1,
    ):
        _tool_start(f, index * 2 - 1, f"call-{index}", name=name, actor=actor)
        _tool_end(
            f, index * 2, f"call-{index}", status, name=name, actor=actor, duration_ms=index * 100
        )
    tools = f.summary()["tools"]
    statuses = (
        "completed",
        "failed",
        "blocked",
        "cancelled",
        "timed_out",
        "interrupted",
        "unknown",
    )
    assert tools["total_calls"] == sum(tools[key] for key in statuses)
    assert tools["total_calls"] == sum(bucket["calls"] for bucket in tools["by_name"])
    assert tools["total_duration_ms"] == sum(bucket["duration_ms"] for bucket in tools["by_name"])
    for actor in tools["by_actor"]:
        assert actor["calls"] == sum(actor[key] for key in statuses)
        assert actor["calls"] == sum(bucket["calls"] for bucket in actor["by_name"])


def test_full_pipeline_closes_only_after_graph_acceptance_and_morfeo_agree() -> None:
    summary = complete_trace().summary()
    assert summary["completion_state"] == "completed"
    assert summary["runtime_state"]["termination"] == "completed"
    assert summary["work_graph"]["all_required_done"]
    assert summary["acceptance"]["complete"]
    assert summary["review_brief"]["verdict"] == "completed"
    assert summary["review_brief"]["next_gate"]["kind"] == "none"


def _reduce_with_authority(fixture: EventFactory, authority: AuthorityContext) -> dict[str, object]:
    events = deepcopy(fixture.events)
    return reduce_events(
        ReductionInput(
            trace_id=fixture.trace_id,
            project_id=fixture.project_id,
            events=events,
            producer_count=len({event["producer_epoch"] for event in events}) or 1,
            authority_context=authority,
        )
    )


def _settled_trace(*, executable: bool = True, invariants: bool = True) -> EventFactory:
    fixture = EventFactory()
    fixture.opened(0)
    if executable:
        fixture.contract("contract.executable", "passed", 1, semantic_delta="invariant")
        if invariants:
            fixture.pass_executable_invariants(1.01)
    fixture.unit(
        "work_unit.bound",
        "reported",
        2,
        task_ref="root",
        relation="root",
        task_status="done",
    )
    fixture.acceptance(3)
    fixture.contract(
        "contract.completion_verified",
        "verified",
        4,
        evidence_refs=("evidence-1",),
        actor_id="morfeo",
        profile="morfeo",
    )
    return fixture


def test_authority_context_is_serializable_and_event_strings_cannot_grant_completion() -> None:
    product = AuthorityContext.product_default()
    assert AuthorityContext.from_record(product.to_record()) == product

    forged = _settled_trace()
    verification = next(
        event for event in forged.events if event["event_type"] == "contract.completion_verified"
    )
    verification["actor"] = {
        "kind": "agent",
        "id": "implementer",
        "profile": "implementer",
        "role": "verification",
    }
    forged_summary = forged.summary()
    assert forged_summary["completion_state"] == "completion_candidate"
    assert forged_summary["timestamps"]["completed_at"] is None
    assert "COMPLETION_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in forged_summary["coverage"]["gaps"]
    }
    verification_step = next(
        step
        for step in forged_summary["process"]["steps"]
        if step["kind"] == "terminal_verification"
    )
    assert verification_step["outcome"] == "unverified"
    assert verification_step["semantic_delta"] is None
    assert verification_step["coverage"] == "partial"

    missing_summary = _reduce_with_authority(_settled_trace(), AuthorityContext.unavailable())
    assert missing_summary["completion_state"] != "completed"
    assert "COMPLETION_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in missing_summary["coverage"]["gaps"]
    }


@pytest.mark.parametrize("claimed_role", [None, "implementation", "review"])
def test_completion_rejects_missing_or_forged_role_even_for_morfeo_identity(
    claimed_role: str | None,
) -> None:
    fixture = _settled_trace()
    verification = next(
        event for event in fixture.events if event["event_type"] == "contract.completion_verified"
    )
    verification["actor"]["role"] = claimed_role

    summary = fixture.summary()

    assert summary["completion_state"] != "completed"
    assert "COMPLETION_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_contract_executable_fact_cannot_substitute_for_each_required_invariant() -> None:
    fixture = _settled_trace(invariants=False)

    summary = fixture.summary()

    assert summary["completion_state"] != "completed"
    assert "EXECUTABLE_INVARIANTS_MISSING" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_required_invariant_checks_are_not_counted_as_contract_iterations() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.contract("contract.executable", "passed", 1, semantic_delta="invariant")
    fixture.pass_executable_invariants(1.01)

    summary = fixture.summary()

    assert summary["flow"]["useful_iterations"] == 0
    assert "useful_iteration" not in {item["kind"] for item in summary["flow"]["classifications"]}


def test_protected_fact_requires_product_checkpoint_provenance_even_with_spoofed_identity() -> None:
    fixture = _settled_trace()
    verification = next(
        event for event in fixture.events if event["event_type"] == "contract.completion_verified"
    )
    verification["actor"] = {
        "kind": "agent",
        "id": "morfeo",
        "profile": "morfeo",
        "role": "verification",
    }
    verification["source_kind"] = "hermes_hook"
    summary = fixture.summary()
    assert summary["completion_state"] != "completed"
    assert "COMPLETION_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_review_request_requires_supervision_authority() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "review.requested",
        "started",
        1,
        task_ref="review",
        relation="review",
        task_status="review",
        actor_id="implementer",
        profile="implementer",
    )["source_kind"] = "aether_checkpoint"
    summary = fixture.summary()
    assert "REVIEW_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_review_terminal_requires_prior_native_assignment_to_same_profile() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "review.approved",
        "passed",
        1,
        task_ref="review",
        relation="review",
        task_status="done",
        actor_id="supervisor",
        profile="supervisor",
    )
    summary = fixture.summary()
    assert "REVIEW_ASSIGNMENT_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_omitted_product_authority_defaults_to_unavailable_not_fixture_trust() -> None:
    fixture = _settled_trace()
    summary = reduce_events(
        ReductionInput(
            trace_id=fixture.trace_id,
            project_id=fixture.project_id,
            events=deepcopy(fixture.events),
            producer_count=1,
        )
    )
    # Missing product authority can never reach ``completed``.  With no accepted
    # verification fact the stricter, lower state is awaiting_final_verification.
    assert summary["completion_state"] == "awaiting_final_verification"
    assert "COMPLETION_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }
    assert "AUTHORITY_CONTEXT_UNAVAILABLE" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_authority_context_rejects_non_mapping_principals_as_malformed() -> None:
    with pytest.raises(ValueError, match="principal"):
        AuthorityContext.from_record(
            {
                "schema_version": "aether.authority-context.v1",
                "source": "active_release:1.0.0-aaaaaaaaaaaaaaaa",
                "principals": [1],
            }
        )


def test_non_success_terminal_requires_verified_product_authority() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.contract(
        "trace.failed",
        "failed",
        1,
        actor_id="implementer",
        profile="implementer",
        role="verification",
    )
    summary = fixture.summary()
    assert summary["completion_state"] == "open"
    assert summary["runtime_state"]["termination"] == "open"
    assert "TERMINAL_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


@pytest.mark.parametrize("root_count", [0, 2])
def test_completed_requires_exactly_one_bound_root(root_count: int) -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.contract("contract.executable", "passed", 1, semantic_delta="invariant")
    for index in range(root_count):
        fixture.unit(
            "work_unit.bound",
            "reported",
            2 + index,
            task_ref=f"root-{index}",
            relation="root",
            task_status="done",
        )
    if root_count == 0:
        fixture.unit(
            "work_unit.bound",
            "reported",
            2,
            task_ref="orphan",
            relation="implementation",
            task_status="done",
        )
    fixture.acceptance(5)
    fixture.contract("contract.completion_verified", "verified", 6)
    summary = fixture.summary()
    assert summary["completion_state"] != "completed"
    assert summary["work_graph"]["root_task_ref"] is None
    expected = "ROOT_TASK_MISSING" if root_count == 0 else "MULTIPLE_ROOT_TASKS"
    assert expected in {gap["reason_code"] for gap in summary["coverage"]["gaps"]}


@pytest.mark.parametrize("invariant_state", ["failed", "unknown", "absent"])
def test_failed_unknown_or_absent_completion_invariants_block_completion(
    invariant_state: str,
) -> None:
    fixture = _settled_trace(executable=invariant_state != "absent")
    if invariant_state != "absent":
        invariant = fixture.contract(
            "invariant.failed" if invariant_state == "failed" else "invariant.passed",
            invariant_state,
            3.5,
            invariant_key="OBS-INV-001",
        )
        # Place the invariant before verification in producer order as well as wall time.
        assert fixture.events.pop() is invariant
        fixture.events.insert(-1, invariant)
        for sequence, event in enumerate(fixture.events):
            event["producer_seq"] = sequence
    summary = fixture.summary()
    assert summary["completion_state"] != "completed"
    expected = {
        "failed": "CLOSURE_INVARIANT_FAILED",
        "unknown": "CLOSURE_INVARIANT_UNKNOWN",
        "absent": "EXECUTABLE_INVARIANTS_MISSING",
    }[invariant_state]
    assert expected in {gap["reason_code"] for gap in summary["coverage"]["gaps"]}


def test_contradictory_invariant_event_never_becomes_a_positive_fact() -> None:
    fixture = EventFactory()
    fixture.opened()
    event = fixture.contract(
        "invariant.passed",
        "passed",
        1,
        invariant_key="OBS-INV-001",
    )
    event["status"] = "failed"

    summary = fixture.summary()
    assert summary["invariants"][0]["state"] == "unknown"
    assert "INVARIANT_EVENT_CONTRADICTION" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_contradictory_completion_event_never_verifies_closure() -> None:
    fixture = _settled_trace()
    verification = next(
        event for event in fixture.events if event["event_type"] == "contract.completion_verified"
    )
    verification["status"] = "pending"

    summary = fixture.summary()
    assert summary["completion_state"] != "completed"
    assert "COMPLETION_EVENT_CONTRADICTION" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_contradictory_review_approval_never_becomes_approved() -> None:
    fixture = complete_trace()
    approval = next(event for event in fixture.events if event["event_type"] == "review.approved")
    approval["status"] = "failed"

    summary = fixture.summary()
    review = next(unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "review")
    assert review["review_state"] != "approved"
    assert "REVIEW_EVENT_CONTRADICTION" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_semantic_delta_after_verification_invalidates_verified_completion() -> None:
    fixture = _settled_trace()
    fixture.contract(
        "decision.recorded",
        "reported",
        5,
        decision_refs=("decision-after-verification",),
        semantic_delta="decision",
    )
    summary = fixture.summary()
    assert summary["completion_state"] == "completion_candidate"
    assert summary["timestamps"]["completed_at"] is None
    assert "VERIFICATION_PRECEDED_LIFECYCLE_DELTA" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_acceptance_evidence_delta_after_verification_requires_reverification() -> None:
    fixture = complete_trace()
    fixture.acceptance(19, evidence=("evidence-after-verification",))

    summary = fixture.summary()

    assert summary["acceptance"]["criteria"][0]["evidence_refs"] == ["evidence-after-verification"]
    assert summary["completion_state"] == "completion_candidate"
    assert summary["timestamps"]["completed_at"] is None
    assert "VERIFICATION_PRECEDED_LIFECYCLE_DELTA" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_premature_verification_never_fabricates_completed_timestamp() -> None:
    f = EventFactory()
    f.opened(0)
    f.contract("contract.executable", "passed", 0.5, semantic_delta="invariant")
    f.pass_executable_invariants(0.51)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="running"
    )
    f.contract(
        "contract.completion_verified",
        "verified",
        2,
        evidence_refs=("evidence",),
        actor_id="morfeo",
        profile="morfeo",
    )
    f.unit("work_unit.status", "completed", 3, task_ref="root", relation="root", task_status="done")
    f.acceptance(4)
    summary = f.summary()
    assert summary["completion_state"] == "completion_candidate"
    assert summary["timestamps"]["completed_at"] is None
    assert "VERIFICATION_PRECEDED_LIFECYCLE_DELTA" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_root_done_with_required_child_open_does_not_close() -> None:
    f = EventFactory()
    f.opened(0)
    f.unit("work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="done")
    f.unit(
        "work_unit.bound",
        "reported",
        2,
        task_ref="child",
        parent_task_refs=("root",),
        task_status="running",
    )
    f.acceptance(3)
    f.contract("contract.completion_verified", "verified", 4, evidence_refs=("evidence",))
    summary = f.summary()
    assert summary["completion_state"] == "executing"
    assert summary["timestamps"]["completed_at"] is None


def test_blocked_task_resumes_same_trace_and_preserves_wait_duration() -> None:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="blocked"
    )
    assert f.summary()["completion_state"] == "blocked"
    f.unit(
        "work_unit.status", "started", 4, task_ref="root", relation="root", task_status="running"
    )
    summary = f.summary()
    assert summary["completion_state"] == "executing"
    assert summary["duration"]["external_wait_ms"] == 3000
    assert summary["trace_id"] == f.trace_id


@pytest.mark.parametrize(
    "outcome", ["crashed", "timed_out", "spawn_failed", "gave_up", "reclaimed"]
)
def test_anomalous_run_outcomes_do_not_close_trace(outcome: str) -> None:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="running"
    )
    f.unit(
        "run.started",
        "started",
        2,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=1,
    )
    f.unit(
        "run.finished",
        outcome if outcome in ("crashed", "timed_out", "spawn_failed", "gave_up") else "released",
        3,
        task_ref="root",
        relation="root",
        task_status="ready",
        run_status="released",
        run_outcome=outcome,
        run_id=1,
    )
    summary = f.summary()
    assert summary["runtime_state"]["termination"] == "open"
    assert summary["completion_state"] != "completed"
    assert summary["work_graph"]["run_totals"][outcome] == 1


def test_recovered_run_anomaly_never_becomes_current_liveness_evidence() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    fixture.unit(
        "run.started",
        "started",
        2,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=1,
    )
    first_finish = fixture.unit(
        "run.finished",
        "crashed",
        3,
        task_ref="root",
        relation="root",
        task_status="ready",
        run_status="released",
        run_outcome="crashed",
        run_id=1,
    )
    second_start = fixture.unit(
        "run.started",
        "started",
        4,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=2,
    )
    second_start["parent_event_id"] = first_finish["event_id"]
    fixture.unit(
        "run.finished",
        "completed",
        5,
        task_ref="root",
        relation="root",
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=2,
    )["parent_event_id"] = second_start["event_id"]

    summary = fixture.summary()

    assert summary["work_graph"]["run_totals"]["crashed"] == 1
    assert summary["work_graph"]["units"][0]["latest_run_outcome"] == "completed"
    assert summary["runtime_state"]["anomalies"] == "clear"
    assert summary["runtime_state"]["liveness"] == "unknown"


@pytest.mark.parametrize(
    "outcome",
    ["rate_limited", "stale", "review_requested", "changes_requested", "scheduled"],
)
def test_each_native_run_outcome_has_a_distinct_machine_readable_total(outcome: str) -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    fixture.unit(
        "run.started",
        "started",
        2,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=1,
    )
    fixture.unit(
        "run.finished",
        "reported",
        3,
        task_ref="root",
        relation="root",
        task_status="ready",
        run_status=outcome,
        run_outcome=outcome,
        run_id=1,
    )
    summary = fixture.summary()
    assert summary["work_graph"]["run_totals"][outcome] == 1
    assert summary["work_graph"]["run_totals"]["unknown"] == 0


def test_review_rework_records_regression_then_clears_open_finding_after_approval() -> None:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="review", relation="review", task_status="review"
    )
    f.unit(
        "review.requested", "started", 2, task_ref="review", relation="review", task_status="review"
    )
    f.unit("review.approved", "passed", 3, task_ref="review", relation="review", task_status="done")
    f.unit(
        "review.changes_requested",
        "rejected",
        4,
        task_ref="review",
        relation="review",
        task_status="review",
    )
    f.unit("review.approved", "passed", 5, task_ref="review", relation="review", task_status="done")
    summary = f.summary()
    assert summary["flow"]["regressions"] == 1
    assert "REGRESSION" not in {item["code"] for item in summary["review_brief"]["findings"]}
    assert "review_rework" in [round_["trigger"] for round_ in summary["process"]["rounds"]]


def test_unbound_same_project_work_is_excluded_from_contract_graph() -> None:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="running"
    )
    f.unit("work_unit.unbound", "released", 2, task_ref="unrelated", task_status="running")
    summary = f.summary()
    units = summary["work_graph"]["units"]
    assert [unit["task_ref"] for unit in units] == ["root"]
    assert summary["coverage"]["complete"] is False
    assert "UNBOUND_WORK_UNIT_OBSERVED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_acceptance_requires_evidence_even_when_native_state_says_passed() -> None:
    f = EventFactory()
    f.opened(0)
    f.acceptance(1, evidence=())
    summary = f.summary()
    assert not summary["acceptance"]["complete"]
    assert summary["review_brief"]["unfinished_acceptance_criteria"] == 1
    assert "ACCEPTANCE_PASSED_WITHOUT_EVIDENCE" in {
        finding["code"] for finding in summary["review_brief"]["findings"]
    }


@pytest.mark.parametrize(
    ("event_type", "expected"),
    (
        ("trace.cancelled", "cancelled"),
        ("trace.abandoned", "abandoned"),
        ("trace.failed", "failed"),
    ),
)
def test_non_success_terminal_outcomes_close_distinctly(event_type: str, expected: str) -> None:
    f = EventFactory()
    f.opened(0)
    f.contract(
        event_type,
        expected if expected != "abandoned" else "unknown",
        1,
        actor_id="morfeo",
        profile="morfeo",
    )
    summary = f.summary()
    assert summary["completion_state"] == expected
    assert summary["runtime_state"]["termination"] == expected
    assert summary["acceptance"]["complete"] is False


@pytest.mark.parametrize(
    ("event_type", "valid_status"),
    (
        ("trace.cancelled", "cancelled"),
        ("trace.abandoned", "unknown"),
        ("trace.failed", "failed"),
    ),
)
def test_contradictory_non_success_terminal_status_never_terminates(
    event_type: str, valid_status: str
) -> None:
    fixture = EventFactory()
    fixture.opened(0)
    terminal = fixture.contract(event_type, valid_status, 1)
    terminal["status"] = "completed"

    summary = fixture.summary()

    assert summary["completion_state"] == "open"
    assert summary["runtime_state"]["termination"] == "open"
    assert "TERMINAL_EVENT_CONTRADICTION" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_heartbeat_only_activity_cannot_create_verified_progress() -> None:
    f = EventFactory()
    f.opened(0)
    f.event("participant.joined", "started", 1, actor_id="worker", profile="implementer")
    f.event("participant.left", "completed", 2, actor_id="worker", profile="implementer")
    summary = f.summary()
    assert summary["runtime_state"]["progress"] == "no_verified_progress"
    assert summary["timestamps"]["last_verified_progress_at"] is None


def test_first_native_heartbeat_snapshot_cannot_create_verified_progress() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        0.5,
        task_ref="t_deadbeef",
        relation="root",
        task_status="unknown",
        run_status="unknown",
    )
    heartbeat = fixture.unit(
        "work_unit.status",
        "started",
        1,
        task_ref="t_deadbeef",
        relation="root",
        task_status="running",
        run_status="running",
    )
    heartbeat["source_kind"] = "native_reconciliation"
    heartbeat["source_hook"] = "kanban_read"
    heartbeat["timestamp_source"] = "native"
    validate_event(heartbeat)

    summary = fixture.summary()

    assert summary["runtime_state"]["liveness"] == "alive"
    assert summary["runtime_state"]["progress"] == "no_verified_progress"
    assert summary["timestamps"]["last_verified_progress_at"] is None
    assert summary["timestamps"]["execution_started_at"] is None


def test_unassigned_review_attempt_is_not_projected_as_exact_approval() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "review.requested",
        "started",
        1,
        task_ref="review-unit",
        relation="review",
        task_status="review",
        actor_id="supervisor",
        profile="supervisor",
    )
    fixture.unit(
        "review.approved",
        "passed",
        2,
        task_ref="review-unit",
        relation="review",
        task_status="done",
        actor_id="supervisor",
        profile="supervisor",
    )

    summary = fixture.summary()
    [review] = [step for step in summary["process"]["steps"] if step["kind"] == "review"]

    assert review["outcome"] == "unverified"
    assert review["semantic_delta"] is None
    assert review["coverage"] == "partial"
    assert "REVIEW_ASSIGNMENT_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def _parallel_fixture(*, adjacent: bool = False) -> EventFactory:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 0.1, task_ref="root", relation="root", task_status="running"
    )
    for task in ("a", "b"):
        f.unit(
            "work_unit.bound",
            "reported",
            0.2,
            task_ref=task,
            parent_task_refs=("root",),
            task_status="running",
        )
    f.unit(
        "run.started",
        "started",
        1,
        task_ref="a",
        parent_task_refs=("root",),
        task_status="running",
        run_status="running",
        run_id=1,
    )
    f.unit(
        "run.finished",
        "completed",
        2,
        task_ref="a",
        parent_task_refs=("root",),
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=1,
    )
    b_started = f.unit(
        "run.started",
        "started",
        2 if adjacent else 1.5,
        task_ref="b",
        parent_task_refs=("root",),
        task_status="running",
        run_status="running",
        run_id=2,
    )
    b_finished = f.unit(
        "run.finished",
        "completed",
        3,
        task_ref="b",
        parent_task_refs=("root",),
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=2,
    )
    for sequence, event in enumerate((b_started, b_finished)):
        event["producer_epoch"] = "prd_" + "7" * 32
        event["producer_seq"] = sequence
    return f


def test_parallel_fanout_reconstructs_one_wave_with_peak_two() -> None:
    process = _parallel_fixture().summary()["process"]
    assert any(wave["deployed_unit_count"] == 2 for wave in process["waves"])
    assert max(wave["peak_parallelism"] for wave in process["waves"]) == 2


def test_adjacent_half_open_spans_are_not_reported_as_parallel() -> None:
    process = _parallel_fixture(adjacent=True).summary()["process"]
    assert all(wave["peak_parallelism"] == 1 for wave in process["waves"])


def test_overlapping_timestamps_without_a_shared_explicit_parent_do_not_create_a_wave() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    for task, epoch in (("a", "7"), ("b", "8")):
        fixture.unit(
            "work_unit.bound",
            "reported",
            0.5,
            task_ref=task,
            task_status="running",
        )
        started = fixture.unit(
            "run.started",
            "started",
            1,
            task_ref=task,
            task_status="running",
            run_status="running",
            run_id=1,
        )
        finished = fixture.unit(
            "run.finished",
            "completed",
            3,
            task_ref=task,
            task_status="done",
            run_status="done",
            run_outcome="completed",
            run_id=1,
        )
        for sequence, event in enumerate((started, finished)):
            event["producer_epoch"] = "prd_" + epoch * 32
            event["producer_seq"] = sequence

    process = fixture.summary()["process"]

    assert all(wave["deployed_unit_count"] == 1 for wave in process["waves"])


def test_cross_producer_attempt_order_does_not_create_a_retry_predecessor() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        0.5,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    for run_id, epoch, start, end in ((1, "7", 1, 2), (2, "8", 3, 4)):
        started = fixture.unit(
            "run.started",
            "started",
            start,
            task_ref="root",
            relation="root",
            task_status="running",
            run_status="running",
            run_id=run_id,
        )
        finished = fixture.unit(
            "run.finished",
            "completed",
            end,
            task_ref="root",
            relation="root",
            task_status="done",
            run_status="done",
            run_outcome="completed",
            run_id=run_id,
        )
        for sequence, event in enumerate((started, finished)):
            event["producer_epoch"] = "prd_" + epoch * 32
            event["producer_seq"] = sequence

    run_steps = [step for step in fixture.summary()["process"]["steps"] if step["run_refs"]]

    assert len(run_steps) == 2
    assert run_steps[1]["predecessor_step_ids"] == []


def test_dispatch_sampling_requires_saturation_for_capacity_claim() -> None:
    f = _parallel_fixture()
    first_tick = f.add(
        f.builder.dispatch(
            tick_ref="tick-1",
            outcome="ok",
            bottleneck_class="capacity_bound",
            eligible_count=4,
            running_count=1,
            global_limit=3,
            precision_ms=1000,
            occurred_at=f.at(1.6),
        )
    )
    second_tick = f.add(
        f.builder.dispatch(
            tick_ref="tick-2",
            outcome="ok",
            bottleneck_class="capacity_bound",
            eligible_count=4,
            running_count=3,
            global_limit=3,
            precision_ms=1000,
            occurred_at=f.at(1.8),
        )
    )
    for sequence, event in enumerate((first_tick, second_tick)):
        event["producer_epoch"] = "prd_" + "8" * 32
        event["producer_seq"] = sequence
    bottlenecks = f.summary()["bottlenecks"]
    assert [item["class"] for item in bottlenecks] == ["unknown", "capacity_bound"]


def test_partial_surface_never_claims_never_used_but_exact_surface_may() -> None:
    partial = EventFactory()
    partial.opened(0)
    partial.add(
        partial.builder.tool_surface(
            request_ref=native_pseudonym("api_request", "request-1"),
            completeness="partial",
            fingerprint_key_id="fpk_" + "1" * 32,
            observed_tool_count=2,
            granted_tool_refs=("file.read", "terminal.exec"),
            never_used_tool_refs=("terminal.exec",),
            occurred_at=partial.at(1),
        )
    )
    assert partial.summary()["capability_evidence"]["never_used_tool_refs"] == []

    exact = EventFactory()
    exact.opened(0)
    exact.add(
        exact.builder.tool_surface(
            request_ref=native_pseudonym("api_request", "request-1"),
            completeness="exact",
            fingerprint_key_id="fpk_" + "1" * 32,
            observed_tool_count=2,
            granted_tool_refs=("file.read", "terminal.exec"),
            never_used_tool_refs=("terminal.exec",),
            occurred_at=exact.at(1),
        )
    )
    assert exact.summary()["capability_evidence"]["never_used_tool_refs"] == ["terminal.exec"]


def test_configuration_preserves_field_level_coverage_and_distinct_scopes() -> None:
    f = EventFactory()
    f.opened(0)
    f.add(
        f.builder.configuration(
            fingerprint_id="a" * 64,
            scope="participant",
            participant_ref="implementer-1",
            fingerprint_key_id="fpk_" + "1" * 32,
            observer_version="1.0.0",
            model="model-a",
            provider="provider-a",
            field_coverage={
                "model": "exact",
                "system_prompt": "unavailable",
                "tool_surface": "partial",
            },
            occurred_at=f.at(1),
        )
    )
    record = f.summary()["configuration_fingerprints"][0]
    assert record["scope"] == "participant"
    assert record["field_coverage"] == {
        "model": "exact",
        "system_prompt": "unavailable",
        "tool_surface": "partial",
    }


def test_configuration_key_epoch_change_is_a_coverage_boundary_not_a_delta() -> None:
    f = EventFactory()
    f.opened(0)
    for index, key_digit in enumerate(("1", "2"), start=1):
        f.add(
            f.builder.configuration(
                fingerprint_id=key_digit * 64,
                scope="trace",
                fingerprint_key_id="fpk_" + key_digit * 32,
                observer_version="1.0.0",
                field_coverage={"model": "unavailable"},
                occurred_at=f.at(index),
            )
        )
    summary = f.summary()
    assert "FINGERPRINT_KEY_EPOCH_BOUNDARY" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_model_economics_reconcile_attempts_tokens_and_sessions() -> None:
    f = EventFactory()
    f.opened(0)
    for session, attempt, state, second in (
        ("session-a", 1, "completed", 1),
        ("session-a", 2, "failed", 2),
        ("session-b", 1, "completed", 3),
    ):
        f.add(
            f.builder.model_request(
                state=state,
                request_ref=native_pseudonym("api_request", "same-request"),
                model="model-a",
                provider="provider-a",
                duration_ms=100,
                finish_reason="stop" if state == "completed" else "error",
                message_count=2,
                tool_count=1,
                attempt_count=attempt,
                tokens={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                usage_coverage="exact",
                occurred_at=f.at(second),
                session_id=native_pseudonym("session", session),
            )
        )
    economics = f.summary()["model_context_economics"]
    assert economics["request_count"] == 2
    assert economics["attempt_count"] == 3
    assert economics["failed_request_count"] == 1
    assert economics["tokens"]["total_tokens"] == 45
    assert economics["token_coverage"] == "exact"
    assert economics["context_signal_coverage"] == "unavailable"


def test_closed_defect_derivations_and_judgment_provenance_remain_distinct() -> None:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="running"
    )
    f.unit(
        "run.started",
        "started",
        2,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=1,
    )
    f.unit(
        "run.finished",
        "crashed",
        3,
        task_ref="root",
        relation="root",
        task_status="ready",
        run_status="crashed",
        run_outcome="crashed",
        run_id=1,
    )
    _tool_start(f, 4, "denied")
    _tool_end(f, 5, "denied", "blocked", approval="denied")
    f.add(
        f.builder.attribution(
            kind="defect",
            attribution_class="contract_ambiguity",
            provenance="morfeo_judgment",
            evidence_refs=(f.events[-1]["event_id"],),
            occurred_at=f.at(6),
        )
    )
    defects = f.summary()["defect_attributions"]
    assert {(item["class"], item["provenance"]) for item in defects} >= {
        ("runtime_failure", "deterministic_derived"),
        ("policy_denial", "native_observed"),
        ("contract_ambiguity", "morfeo_judgment"),
    }


def test_review_brief_precedence_prefers_active_block_over_review_and_anomaly() -> None:
    f = EventFactory()
    f.opened(0)
    f.unit(
        "work_unit.bound", "reported", 1, task_ref="root", relation="root", task_status="blocked"
    )
    f.unit(
        "work_unit.bound",
        "reported",
        1.1,
        task_ref="review",
        relation="review",
        task_status="review",
    )
    f.unit(
        "review.changes_requested",
        "rejected",
        2,
        task_ref="review",
        relation="review",
        task_status="review",
    )
    f.contract("invariant.failed", "failed", 3, invariant_key="OBS-INV-001")
    brief = f.summary()["review_brief"]
    assert brief["verdict"] == "blocked"
    assert brief["primary_reason_code"] == "WORK_UNIT_BLOCKED"
    assert brief["next_gate"]["kind"] == "dependency_resolution"


def test_repeated_reduction_is_byte_equivalent_and_contains_no_productivity_score() -> None:
    f = complete_trace()
    one = f.summary()
    two = f.summary()
    assert canonical_json_bytes(one) == canonical_json_bytes(two)

    def keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from keys(nested)

    assert "productivity_score" not in set(keys(one))
    assert one["improvement_evidence"]["strength"] == "anecdotal"
    assert one["improvement_evidence"]["automated_recommendation"] is None


def test_reconciliation_deduplicates_complete_native_identity_only() -> None:
    f = EventFactory()
    f.opened(0)
    first = _tool_start(f, 1, "call")
    duplicate = deepcopy(first)
    duplicate["event_id"] = "evt_" + "f" * 32
    duplicate["source_kind"] = "native_reconciliation"
    report = dedupe([duplicate, first])
    assert report.duplicates_dropped == 1
    assert report.events[0]["source_kind"] == "hermes_hook"

    incomplete_a = deepcopy(first)
    incomplete_a["event_id"] = "evt_" + "a" * 32
    incomplete_a["session_id"] = None
    incomplete_b = deepcopy(incomplete_a)
    incomplete_b["event_id"] = "evt_" + "b" * 32
    assert len(dedupe([incomplete_a, incomplete_b]).events) == 2


def test_reconciliation_reports_sequence_gap_and_unclean_tail_independently() -> None:
    f = EventFactory()
    first = f.opened(0)
    second = f.contract("contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64)
    second["producer_seq"] = 2
    report = dedupe([first, second])
    gaps = derive_gaps(report, unclean_epochs=(EPOCH,))
    assert {gap["reason_code"] for gap in gaps} >= {
        "PRODUCER_SEQUENCE_GAP",
        "UNCLEAN_PRODUCER_TAIL",
    }


def test_sequence_gap_detection_does_not_rescan_all_sequences_for_each_value() -> None:
    class EqualityProbe(int):
        comparisons = 0

        def __eq__(self, other: object) -> bool:
            type(self).comparisons += 1
            return bool(super().__eq__(other))

        __hash__ = int.__hash__

    event_count = 128
    report = ReconciliationReport(
        events=[
            {"producer_epoch": EPOCH, "producer_seq": EqualityProbe(sequence)}
            for sequence in range(event_count)
        ]
    )

    assert derive_gaps(report) == []
    assert EqualityProbe.comparisons <= event_count * 4


def test_unknown_work_classification_and_task_envelope_mismatch_are_not_invented() -> None:
    unknown = EventFactory()
    unknown.opened(0)
    event = unknown.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="unknown-unit",
        relation="implementation",
        required=True,
        task_status="running",
    )
    event["work_unit"]["relation"] = None
    event["work_unit"]["required"] = None
    summary = _reduce_with_authority(unknown, AuthorityContext.product_default())
    assert summary["work_graph"]["units"][0]["relation"] == "unknown"
    assert summary["work_graph"]["units"][0]["required"] is None
    assert summary["work_graph"]["all_required_done"] is False
    assert "WORK_UNIT_CLASSIFICATION_UNKNOWN" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }

    mismatch = EventFactory()
    mismatch.opened(0)
    event = mismatch.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="work-unit-ref",
        relation="root",
        task_status="running",
    )
    event["task_id"] = "different-envelope-ref"
    mismatch_summary = _reduce_with_authority(mismatch, AuthorityContext.product_default())
    assert mismatch_summary["work_graph"]["units"] == []
    assert "TASK_WORK_UNIT_MISMATCH" in {
        gap["reason_code"] for gap in mismatch_summary["coverage"]["gaps"]
    }


def test_native_identity_conflicting_terminals_are_preserved_as_ambiguity() -> None:
    fixture = EventFactory()
    completed = _tool_end(fixture, 1, "same-native-call", "completed")
    failed = deepcopy(completed)
    failed["event_id"] = "evt_" + "f" * 32
    failed["event_type"] = "tool.failed"
    failed["status"] = "failed"
    failed["source_kind"] = "native_reconciliation"

    report = dedupe([completed, failed])
    assert len(report.events) == 2
    assert report.duplicates_dropped == 0
    assert "NATIVE_TERMINAL_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(report)}


def test_same_native_status_coordinates_with_incompatible_outcomes_are_ambiguous() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        0.5,
        task_ref="t_deadbeef",
        relation="root",
        task_status="running",
        run_status="running",
    )
    completed = fixture.unit(
        "work_unit.status",
        "completed",
        1,
        task_ref="t_deadbeef",
        relation="root",
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=1,
    )
    completed["source_kind"] = "native_reconciliation"
    completed["source_hook"] = "kanban_read"
    completed["timestamp_source"] = "native"
    completed["producer_epoch"] = "prd_" + "a" * 32
    completed["producer_seq"] = 0
    failed = deepcopy(completed)
    failed["event_id"] = "evt_" + "f" * 32
    failed["producer_epoch"] = "prd_" + "f" * 32
    failed["status"] = "failed"
    failed["work_unit"]["run_status"] = "failed"
    failed["work_unit"]["run_outcome"] = "failed"
    validate_event(completed)
    validate_event(failed)

    summaries = []
    for pair in permutations((completed, failed)):
        report = dedupe(deepcopy(pair))
        assert "NATIVE_TERMINAL_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(report)}
        summaries.append(
            reduce_events(
                ReductionInput(
                    trace_id=fixture.trace_id,
                    project_id=fixture.project_id,
                    events=deepcopy([*fixture.events[:2], *pair]),
                    producer_count=3,
                    authority_context=AuthorityContext.product_default(),
                )
            )
        )

    assert summaries[0] == summaries[1]
    for summary in summaries:
        [root] = summary["work_graph"]["units"]
        assert root["task_status"] == "unknown"
        assert root["latest_run_status"] == "unknown"
        assert root["latest_run_outcome"] == "unknown"


def test_completion_event_id_conflict_neutralizes_authority_in_any_order() -> None:
    fixture = complete_trace()
    verification = next(
        event for event in fixture.events if event["event_type"] == "contract.completion_verified"
    )
    forged = deepcopy(verification)
    forged["actor"] = {
        "kind": "agent",
        "id": "implementer-8",
        "profile": "implementer",
        "role": "implementation",
    }
    validate_event(forged)
    # Exercise the dangerous canonical representative: the authorized bytes win the
    # existing digest tie-break, so an EVENT_ID_CONFLICT used to remain `completed`.
    assert canonical_digest(verification) < canonical_digest(forged)
    base = [event for event in fixture.events if event is not verification]

    summaries = [
        reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                producer_count=1,
                authority_context=AuthorityContext.product_default(),
            )
        )
        for pair in permutations((verification, forged))
    ]

    assert summaries[0] == summaries[1]
    for summary in summaries:
        assert summary["completion_state"] != "completed"
        assert summary["runtime_state"]["termination"] == "open"
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
        assert "EVENT_ID_CONFLICT" in reasons
        assert "COMPLETION_AUTHORITY_UNVERIFIED" in reasons


def test_conflicting_repeated_event_id_is_a_reproducible_gap() -> None:
    fixture = EventFactory()
    first = fixture.contract(
        "contract.revision",
        "reported",
        1,
        revision=1,
        after_sha256="a" * 64,
    )
    second = deepcopy(first)
    second["contract"]["revision"] = 2
    second["contract"]["after_sha256"] = "b" * 64

    forward = dedupe([first, second])
    reverse = dedupe([second, first])

    assert "EVENT_ID_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(forward)}
    assert forward.events == reverse.events


def test_duplicate_producer_sequence_is_not_turned_into_a_causal_edge() -> None:
    fixture = EventFactory()
    first = fixture.contract(
        "contract.revision",
        "reported",
        1,
        revision=1,
        after_sha256="a" * 64,
    )
    second = fixture.contract(
        "decision.recorded",
        "reported",
        2,
        decision_refs=("decision-1",),
        semantic_delta="decision",
    )
    second["producer_epoch"] = first["producer_epoch"]
    second["producer_seq"] = first["producer_seq"]

    report = dedupe([first, second])
    assert "PRODUCER_SEQUENCE_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(report)}
    assert all(not step["predecessor_step_ids"] for step in build_process([first, second])["steps"])


def test_product_owned_exact_classification_survives_native_unknown_in_any_order() -> None:
    fixture = EventFactory()
    native = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="implementation",
        task_status="done",
    )
    native["source_kind"] = "native_reconciliation"
    native["work_unit"]["relation"] = "unknown"
    native["work_unit"]["required"] = None
    exact = deepcopy(native)
    exact["event_id"] = "evt_" + "f" * 32
    exact["producer_epoch"] = "prd_" + "f" * 32
    exact["source_kind"] = "aether_checkpoint"
    exact["parent_event_id"] = native["event_id"]
    exact["actor"] = {
        "kind": "agent",
        "id": "supervisor",
        "profile": "supervisor",
        "role": "supervision",
    }
    exact["work_unit"]["relation"] = "root"
    exact["work_unit"]["required"] = True

    report = dedupe([native, exact])
    assert len(report.events) == 2
    assert "NATIVE_IDENTITY_CONFLICT" not in {gap["reason_code"] for gap in derive_gaps(report)}

    summaries = []
    for events in ([native, exact], [exact, native]):
        summaries.append(
            reduce_events(
                ReductionInput(
                    trace_id=fixture.trace_id,
                    project_id=fixture.project_id,
                    events=deepcopy(events),
                    producer_count=2,
                    authority_context=AuthorityContext.product_default(),
                )
            )
        )
    for summary in summaries:
        unit = summary["work_graph"]["units"][0]
        assert unit["relation"] == "root"
        assert unit["required"] is True
        assert "WORK_UNIT_CLASSIFICATION_UNKNOWN" not in {
            gap["reason_code"] for gap in summary["coverage"]["gaps"]
        }
    assert summaries[0]["completion_state"] == summaries[1]["completion_state"]


def test_native_dedupe_preserves_explicit_classification_parent_in_every_permutation() -> None:
    fixture = EventFactory()
    target = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="unknown",
        required=None,
        task_status="done",
        actor_id="supervisor",
        profile="supervisor",
    )
    target["event_id"] = "evt_" + "c" * 32
    duplicate = deepcopy(target)
    duplicate["event_id"] = "evt_" + "a" * 32
    duplicate["producer_epoch"] = "prd_" + "e" * 32
    duplicate["producer_seq"] = 0
    classification = deepcopy(target)
    classification["event_id"] = "evt_" + "f" * 32
    classification["producer_epoch"] = "prd_" + "f" * 32
    classification["producer_seq"] = 0
    classification["source_kind"] = "aether_checkpoint"
    classification["parent_event_id"] = target["event_id"]
    classification["actor"]["role"] = "supervision"
    classification["work_unit"]["relation"] = "root"
    classification["work_unit"]["required"] = True

    summaries = []
    for order in permutations((target, duplicate, classification)):
        report = dedupe(deepcopy(order))
        retained_ids = {event["event_id"] for event in report.events}
        assert target["event_id"] in retained_ids
        assert duplicate["event_id"] not in retained_ids
        assert report.duplicates_dropped == 1
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy(list(order)),
                producer_count=3,
                authority_context=AuthorityContext.product_default(),
            )
        )
        unit = summary["work_graph"]["units"][0]
        assert unit["relation"] == "root"
        assert unit["required"] is True
        summaries.append(summary)
    assert len({summary["summary_id"] for summary in summaries}) == 1


def test_native_dedupe_preserves_every_explicit_parent_target() -> None:
    fixture = EventFactory()
    first = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    second = deepcopy(first)
    second["event_id"] = "evt_" + "e" * 32
    second["producer_epoch"] = "prd_" + "e" * 32
    second["producer_seq"] = 0

    classifications = []
    for index, parent in enumerate((first, second)):
        classification = deepcopy(first)
        classification["event_id"] = "evt_" + ("d" if index == 0 else "f") * 32
        classification["producer_epoch"] = "prd_" + ("d" if index == 0 else "f") * 32
        classification["producer_seq"] = 0
        classification["source_kind"] = "aether_checkpoint"
        classification["parent_event_id"] = parent["event_id"]
        classification["actor"]["role"] = "supervision"
        classification["work_unit"]["relation"] = "root"
        classification["work_unit"]["required"] = True
        classifications.append(classification)

    expected_ids = {
        first["event_id"],
        second["event_id"],
        *(classification["event_id"] for classification in classifications),
    }
    for order in permutations((first, second, *classifications)):
        report = dedupe(deepcopy(order))
        assert {event["event_id"] for event in report.events} == expected_ids


def test_conflicting_product_classifications_degrade_to_unknown_in_any_order() -> None:
    fixture = EventFactory()
    native = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    review = deepcopy(native)
    review["event_id"] = "evt_" + "e" * 32
    review["producer_epoch"] = "prd_" + "e" * 32
    review["source_kind"] = "aether_checkpoint"
    review["parent_event_id"] = native["event_id"]
    review["actor"]["role"] = "supervision"
    review["work_unit"]["relation"] = "review"
    review["work_unit"]["required"] = True
    implementation = deepcopy(review)
    implementation["event_id"] = "evt_" + "f" * 32
    implementation["producer_epoch"] = "prd_" + "f" * 32
    implementation["work_unit"]["relation"] = "implementation"

    summaries = []
    for events in (
        [native, review, implementation],
        [implementation, native, review],
    ):
        summaries.append(
            reduce_events(
                ReductionInput(
                    trace_id=fixture.trace_id,
                    project_id=fixture.project_id,
                    events=deepcopy(events),
                    producer_count=3,
                    authority_context=AuthorityContext.product_default(),
                )
            )
        )
    for summary in summaries:
        unit = summary["work_graph"]["units"][0]
        assert unit["relation"] == "unknown"
        assert unit["required"] is None
        assert "NATIVE_IDENTITY_CONFLICT" in {
            gap["reason_code"] for gap in summary["coverage"]["gaps"]
        }
    assert summaries[0]["work_graph"] == summaries[1]["work_graph"]


def _independent_conflicting_event(
    fixture: EventFactory,
    event: dict[str, object],
    *,
    identity_digit: str,
    seconds: float,
) -> dict[str, object]:
    conflict = deepcopy(event)
    conflict["event_id"] = "evt_" + identity_digit * 32
    conflict["producer_epoch"] = "prd_" + identity_digit * 32
    conflict["producer_seq"] = 0
    timestamp = fixture.at(seconds).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    conflict["occurred_at"] = timestamp
    conflict["recorded_at"] = timestamp
    conflict["monotonic_ns"] = 1
    validate_event(conflict)
    return conflict


def _order_before_event(
    fixture: EventFactory,
    event: dict[str, object],
    *,
    event_type: str,
    task_ref: str,
) -> None:
    successor = next(
        candidate
        for candidate in fixture.events
        if candidate["event_type"] == event_type
        and (candidate.get("work_unit") or {}).get("task_ref") == task_ref
    )
    successor["parent_event_id"] = event["event_id"]
    validate_event(successor)


def test_conflicting_native_parentage_neutralizes_graph_authority_in_any_order() -> None:
    fixture = complete_trace()
    original = next(
        event
        for event in fixture.events
        if event["event_type"] == "work_unit.bound"
        and (event.get("work_unit") or {}).get("task_ref") == "review"
    )
    conflict = _independent_conflicting_event(
        fixture,
        original,
        identity_digit="d",
        seconds=13,
    )
    conflict["work_unit"]["parent_task_refs"] = ["root"]
    validate_event(conflict)
    _order_before_event(
        fixture,
        conflict,
        event_type="review.requested",
        task_ref="review",
    )
    base = [event for event in fixture.events if event is not original]

    summaries = []
    for pair in permutations((original, conflict)):
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                producer_count=2,
                authority_context=AuthorityContext.product_default(),
            )
        )
        review = next(
            unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "review"
        )
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
        review_steps = [
            step for step in summary["process"]["steps"] if "review" in step["task_refs"]
        ]

        assert summary["completion_state"] != "completed"
        assert summary["runtime_state"]["termination"] == "open"
        assert summary["coverage"]["complete"] is False
        assert {"NATIVE_IDENTITY_CONFLICT", "WORK_UNIT_PARENTAGE_CONFLICT"} <= reasons
        assert review["relation"] == "unknown"
        assert review["required"] is None
        assert review["parent_task_refs"] == []
        assert all(step["predecessor_step_ids"] == [] for step in review_steps)
        summaries.append(summary)

    assert summaries[0] == summaries[1]


def test_conflicting_root_bindings_neutralize_root_authority_in_any_order() -> None:
    fixture = complete_trace()
    original = next(
        event
        for event in fixture.events
        if event["event_type"] == "work_unit.bound"
        and (event.get("work_unit") or {}).get("task_ref") == "root"
    )
    conflict = _independent_conflicting_event(
        fixture,
        original,
        identity_digit="e",
        seconds=4.5,
    )
    conflict["work_unit"]["binding_ref"] = "bnd_root_fedcba9876543210"
    validate_event(conflict)
    _order_before_event(
        fixture,
        conflict,
        event_type="work_unit.bound",
        task_ref="impl",
    )
    base = [event for event in fixture.events if event is not original]

    summaries = []
    for pair in permutations((original, conflict)):
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                producer_count=2,
                authority_context=AuthorityContext.product_default(),
            )
        )
        root = next(unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "root")
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}

        assert summary["completion_state"] != "completed"
        assert summary["runtime_state"]["termination"] == "open"
        assert summary["coverage"]["complete"] is False
        assert "WORK_UNIT_BINDING_CONFLICT" in reasons
        assert summary["work_graph"]["root_task_ref"] is None
        assert root["relation"] == "unknown"
        assert root["required"] is None
        assert root["parent_task_refs"] == []
        summaries.append(summary)

    assert summaries[0] == summaries[1]


def test_conflicting_native_run_terminals_invalidate_graph_in_any_order() -> None:
    fixture = complete_trace()
    completed = next(
        event
        for event in fixture.events
        if event["event_type"] == "run.finished"
        and (event.get("work_unit") or {}).get("task_ref") == "impl"
        and event.get("run_id") == 1
    )
    failed = _independent_conflicting_event(
        fixture,
        completed,
        identity_digit="f",
        seconds=10.5,
    )
    failed["status"] = "failed"
    failed["work_unit"]["task_status"] = "done"
    failed["work_unit"]["run_status"] = "failed"
    failed["work_unit"]["run_outcome"] = "failed"
    validate_event(failed)
    _order_before_event(
        fixture,
        failed,
        event_type="work_unit.bound",
        task_ref="review",
    )
    base = [event for event in fixture.events if event is not completed]

    summaries = []
    for pair in permutations((completed, failed)):
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                producer_count=2,
                authority_context=AuthorityContext.product_default(),
            )
        )
        implementation = next(
            unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "impl"
        )
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}

        assert summary["completion_state"] != "completed"
        assert summary["runtime_state"]["termination"] == "open"
        assert summary["coverage"]["complete"] is False
        assert "NATIVE_TERMINAL_CONFLICT" in reasons
        assert implementation["task_status"] == "unknown"
        assert implementation["latest_run_status"] == "unknown"
        assert implementation["latest_run_outcome"] == "unknown"
        assert summary["work_graph"]["run_totals"]["completed"] == 1
        assert summary["work_graph"]["run_totals"]["failed"] == 1
        summaries.append(summary)

    assert summaries[0] == summaries[1]


def test_conflicting_run_event_id_retains_bounded_graph_ambiguity_in_any_order() -> None:
    fixture = complete_trace()
    completed = next(
        event
        for event in fixture.events
        if event["event_type"] == "run.finished"
        and (event.get("work_unit") or {}).get("task_ref") == "impl"
        and event.get("run_id") == 1
    )
    failed = _independent_conflicting_event(
        fixture,
        completed,
        identity_digit="a",
        seconds=10.5,
    )
    failed["event_id"] = completed["event_id"]
    failed["status"] = "failed"
    failed["work_unit"]["task_status"] = "done"
    failed["work_unit"]["run_status"] = "failed"
    failed["work_unit"]["run_outcome"] = "failed"
    validate_event(failed)
    _order_before_event(
        fixture,
        failed,
        event_type="work_unit.bound",
        task_ref="review",
    )
    base = [event for event in fixture.events if event is not completed]

    summaries = []
    for pair in permutations((completed, failed)):
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                producer_count=2,
                authority_context=AuthorityContext.product_default(),
            )
        )
        implementation = next(
            unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "impl"
        )
        totals = summary["work_graph"]["run_totals"]
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}

        assert summary["completion_state"] != "completed"
        assert summary["runtime_state"]["termination"] == "open"
        assert summary["coverage"]["complete"] is False
        assert "EVENT_ID_CONFLICT" in reasons
        assert implementation["task_status"] == "unknown"
        assert implementation["latest_run_status"] == "unknown"
        assert implementation["latest_run_outcome"] == "unknown"
        assert totals["completed"] == 0
        assert totals["failed"] == 0
        assert totals["unknown"] == 1
        summaries.append(summary)

    assert summaries[0] == summaries[1]


def test_producer_sequence_conflict_neutralizes_only_involved_work_status() -> None:
    fixture = complete_trace()
    root_status = next(
        event
        for event in fixture.events
        if event["event_type"] == "work_unit.status"
        and (event.get("work_unit") or {}).get("task_ref") == "root"
    )
    collision = fixture.event(
        "participant.joined",
        "started",
        15.5,
        actor_id="observer",
        profile="implementer",
    )
    collision["producer_seq"] = root_status["producer_seq"]
    validate_event(collision)
    base = [event for event in fixture.events if event not in (root_status, collision)]

    summaries = []
    for pair in permutations((root_status, collision)):
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                producer_count=1,
                authority_context=AuthorityContext.product_default(),
            )
        )
        root = next(unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "root")
        implementation = next(
            unit for unit in summary["work_graph"]["units"] if unit["task_ref"] == "impl"
        )
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}

        assert summary["completion_state"] != "completed"
        assert summary["runtime_state"]["termination"] == "open"
        assert summary["coverage"]["complete"] is False
        assert "PRODUCER_SEQUENCE_CONFLICT" in reasons
        assert root["relation"] == "root"
        assert root["required"] is True
        assert root["task_status"] == "unknown"
        assert implementation["task_status"] == "done"
        summaries.append(summary)

    assert summaries[0] == summaries[1]


def test_non_graph_event_id_conflict_does_not_gate_settled_work_graph() -> None:
    fixture = complete_trace()
    completed = _tool_end(fixture, 19, "non-graph-conflict", "completed")
    failed = deepcopy(completed)
    failed["event_type"] = "tool.failed"
    failed["status"] = "failed"
    validate_event(failed)
    base = [event for event in fixture.events if event is not completed]

    summaries = []
    for pair in permutations((completed, failed)):
        summary = reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy([*base, *pair]),
                authority_context=AuthorityContext.product_default(),
            )
        )
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}

        assert "EVENT_ID_CONFLICT" in reasons
        assert summary["completion_state"] == "completed"
        assert summary["runtime_state"]["termination"] == "completed"
        summaries.append(summary)

    assert summaries[0] == summaries[1]


@pytest.mark.parametrize("unauthorized_first", (False, True))
def test_unauthorized_product_classification_never_supplies_positive_semantics(
    unauthorized_first: bool,
) -> None:
    fixture = EventFactory()
    native = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    forged = deepcopy(native)
    forged["event_id"] = "evt_" + "e" * 32
    forged["producer_epoch"] = "prd_" + ("0" if unauthorized_first else "f") * 32
    forged["producer_seq"] = 0
    forged["source_kind"] = "aether_checkpoint"
    forged["actor"] = {
        "kind": "agent",
        "id": "intruder",
        "profile": "supervisor",
        "role": "supervision",
    }
    forged["work_unit"]["relation"] = "review"
    forged["work_unit"]["required"] = True
    native["producer_epoch"] = "prd_" + ("f" if unauthorized_first else "0") * 32

    summary = reduce_events(
        ReductionInput(
            trace_id=fixture.trace_id,
            project_id=fixture.project_id,
            events=[forged, native],
            producer_count=2,
            authority_context=AuthorityContext.product_default(),
        )
    )

    [unit] = summary["work_graph"]["units"]
    assert unit["relation"] == "unknown"
    assert unit["required"] is None
    assert "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }


def test_product_classification_authority_conflict_is_preserved_and_deterministic() -> None:
    fixture = EventFactory()
    native = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    authorized = deepcopy(native)
    authorized["event_id"] = "evt_" + "d" * 32
    authorized["producer_epoch"] = "prd_" + "d" * 32
    authorized["producer_seq"] = 0
    authorized["source_kind"] = "aether_checkpoint"
    authorized["parent_event_id"] = native["event_id"]
    authorized["actor"]["role"] = "supervision"
    authorized["work_unit"]["relation"] = "review"
    authorized["work_unit"]["required"] = True
    forged = deepcopy(authorized)
    forged["event_id"] = "evt_" + "e" * 32
    forged["producer_epoch"] = "prd_" + "e" * 32
    forged["actor"]["id"] = "intruder"

    summaries = []
    for order in permutations((native, authorized, forged)):
        report = dedupe(deepcopy(order))
        assert len(report.events) == 3
        assert "NATIVE_IDENTITY_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(report)}
        summaries.append(
            reduce_events(
                ReductionInput(
                    trace_id=fixture.trace_id,
                    project_id=fixture.project_id,
                    events=deepcopy(order),
                    producer_count=3,
                    authority_context=AuthorityContext.product_default(),
                )
            )
        )

    assert len({summary["summary_id"] for summary in summaries}) == 1
    for summary in summaries:
        [unit] = summary["work_graph"]["units"]
        assert unit["relation"] == "review"
        assert unit["required"] is True
        assert "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED" in {
            gap["reason_code"] for gap in summary["coverage"]["gaps"]
        }


def test_product_classification_parent_conflict_is_preserved_in_any_order() -> None:
    fixture = EventFactory()
    native = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    first = deepcopy(native)
    first["event_id"] = "evt_" + "d" * 32
    first["producer_epoch"] = "prd_" + "d" * 32
    first["producer_seq"] = 0
    first["source_kind"] = "aether_checkpoint"
    first["parent_event_id"] = native["event_id"]
    first["actor"]["role"] = "supervision"
    first["work_unit"]["relation"] = "review"
    first["work_unit"]["required"] = True
    second = deepcopy(first)
    second["event_id"] = "evt_" + "e" * 32
    second["producer_epoch"] = "prd_" + "e" * 32
    second["parent_event_id"] = "evt_" + "f" * 32

    summaries = []
    for order in permutations((native, first, second)):
        report = dedupe(deepcopy(order))
        assert len(report.events) == 3
        assert "NATIVE_IDENTITY_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(report)}
        summaries.append(
            reduce_events(
                ReductionInput(
                    trace_id=fixture.trace_id,
                    project_id=fixture.project_id,
                    events=deepcopy(order),
                    producer_count=3,
                    authority_context=AuthorityContext.product_default(),
                )
            )
        )

    assert len({summary["summary_id"] for summary in summaries}) == 1
    for summary in summaries:
        [unit] = summary["work_graph"]["units"]
        assert unit["relation"] == "review"
        assert unit["required"] is True


def test_native_assignment_conflict_cannot_authorize_review_in_any_permutation() -> None:
    fixture = EventFactory()
    supervisor = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    supervisor["producer_epoch"] = "prd_" + "c" * 32
    supervisor["producer_seq"] = 0
    implementer = deepcopy(supervisor)
    implementer["event_id"] = "evt_" + "c" * 32
    implementer["producer_epoch"] = "prd_" + "d" * 32
    implementer["actor"]["id"] = "implementer"
    implementer["actor"]["profile"] = "implementer"

    classification = deepcopy(supervisor)
    classification["event_id"] = "evt_" + "d" * 32
    classification["producer_epoch"] = "prd_" + "e" * 32
    classification["source_kind"] = "aether_checkpoint"
    classification["parent_event_id"] = supervisor["event_id"]
    classification["actor"]["role"] = "supervision"
    classification["work_unit"]["relation"] = "review"
    classification["work_unit"]["required"] = True

    approval = fixture.unit(
        "review.approved",
        "passed",
        2,
        task_ref="review-unit",
        relation="review",
        required=True,
        actor_id="supervisor",
        profile="supervisor",
    )
    approval["event_id"] = "evt_" + "e" * 32
    approval["producer_epoch"] = "prd_" + "f" * 32
    approval["producer_seq"] = 0
    approval["parent_event_id"] = classification["event_id"]

    summaries = []
    for order in permutations((supervisor, implementer, classification, approval)):
        report = dedupe(deepcopy(order))
        assert len(report.events) == 4
        assert "NATIVE_IDENTITY_CONFLICT" in {gap["reason_code"] for gap in derive_gaps(report)}
        summaries.append(
            reduce_events(
                ReductionInput(
                    trace_id=fixture.trace_id,
                    project_id=fixture.project_id,
                    events=deepcopy(order),
                    producer_count=4,
                    authority_context=AuthorityContext.product_default(),
                )
            )
        )

    assert len({summary["summary_id"] for summary in summaries}) == 1
    for summary in summaries:
        [unit] = summary["work_graph"]["units"]
        assert unit["review_state"] != "approved"
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
        assert "WORK_UNIT_ASSIGNMENT_CONFLICT" in reasons
        assert "REVIEW_ASSIGNMENT_UNVERIFIED" in reasons


def test_late_independent_assignee_conflict_invalidates_prior_review_approval() -> None:
    fixture = EventFactory()
    supervisor = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    supervisor["producer_epoch"] = "prd_" + "a" * 32
    supervisor["producer_seq"] = 0
    classification = deepcopy(supervisor)
    classification["event_id"] = "evt_" + "b" * 32
    classification["producer_epoch"] = "prd_" + "b" * 32
    classification["source_kind"] = "aether_checkpoint"
    classification["parent_event_id"] = supervisor["event_id"]
    classification["actor"]["role"] = "supervision"
    classification["work_unit"]["relation"] = "review"
    classification["work_unit"]["required"] = True
    requested = fixture.unit(
        "review.requested",
        "started",
        2,
        task_ref="review-unit",
        relation="review",
        required=True,
        actor_id="supervisor",
        profile="supervisor",
    )
    requested["event_id"] = "evt_" + "c" * 32
    requested["producer_epoch"] = "prd_" + "c" * 32
    requested["producer_seq"] = 0
    requested["parent_event_id"] = classification["event_id"]
    approved = fixture.unit(
        "review.approved",
        "passed",
        3,
        task_ref="review-unit",
        relation="review",
        required=True,
        actor_id="supervisor",
        profile="supervisor",
    )
    approved["event_id"] = "evt_" + "d" * 32
    approved["producer_epoch"] = "prd_" + "d" * 32
    approved["producer_seq"] = 0
    approved["parent_event_id"] = requested["event_id"]
    implementer = deepcopy(supervisor)
    implementer["event_id"] = "evt_" + "f" * 32
    implementer["producer_epoch"] = "prd_" + "f" * 32
    implementer["actor"]["id"] = "implementer"
    implementer["actor"]["profile"] = "implementer"

    summaries = [
        reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy(list(order)),
                producer_count=5,
                authority_context=AuthorityContext.product_default(),
            )
        )
        for order in permutations((supervisor, classification, requested, approved, implementer))
    ]

    assert len({summary["summary_id"] for summary in summaries}) == 1
    for summary in summaries:
        [unit] = summary["work_graph"]["units"]
        assert unit["review_state"] == "pending"
        [review_step] = [step for step in summary["process"]["steps"] if step["kind"] == "review"]
        assert review_step["outcome"] == "unverified"
        assert review_step["semantic_delta"] is None
        assert review_step["coverage"] == "partial"
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
        assert "WORK_UNIT_ASSIGNMENT_CONFLICT" in reasons
        assert "REVIEW_ASSIGNMENT_UNVERIFIED" in reasons


def test_unbound_unit_rejects_forged_review_terminal_in_any_permutation() -> None:
    fixture = EventFactory()
    bound = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    bound["producer_epoch"] = "prd_" + "c" * 32
    bound["producer_seq"] = 0
    unbound = fixture.unit(
        "work_unit.unbound",
        "reported",
        2,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    unbound["producer_epoch"] = bound["producer_epoch"]
    unbound["producer_seq"] = 1
    unbound["parent_event_id"] = bound["event_id"]

    classification = deepcopy(bound)
    classification["event_id"] = "evt_" + "d" * 32
    classification["producer_epoch"] = "prd_" + "d" * 32
    classification["producer_seq"] = 0
    classification["source_kind"] = "aether_checkpoint"
    classification["parent_event_id"] = unbound["event_id"]
    classification["actor"]["role"] = "supervision"
    classification["work_unit"]["relation"] = "review"
    classification["work_unit"]["required"] = True

    approval = fixture.unit(
        "review.approved",
        "passed",
        3,
        task_ref="review-unit",
        relation="review",
        required=True,
        actor_id="supervisor",
        profile="supervisor",
    )
    approval["event_id"] = "evt_" + "e" * 32
    approval["producer_epoch"] = "prd_" + "e" * 32
    approval["producer_seq"] = 0
    approval["parent_event_id"] = classification["event_id"]

    summaries = [
        reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy(list(order)),
                producer_count=3,
                authority_context=AuthorityContext.product_default(),
            )
        )
        for order in permutations((bound, unbound, classification, approval))
    ]

    assert len({summary["summary_id"] for summary in summaries}) == 1
    for summary in summaries:
        assert summary["work_graph"]["units"] == []
        assert "REVIEW_ASSIGNMENT_UNVERIFIED" in {
            gap["reason_code"] for gap in summary["coverage"]["gaps"]
        }


def test_authorized_shaped_review_without_causal_parents_never_becomes_positive() -> None:
    fixture = EventFactory()
    native = fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="review-unit",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    native["producer_epoch"] = "prd_" + "0" * 32
    native["producer_seq"] = 0
    classification = deepcopy(native)
    classification["event_id"] = "evt_" + "d" * 32
    classification["producer_epoch"] = "prd_" + "1" * 32
    classification["source_kind"] = "aether_checkpoint"
    classification["actor"]["role"] = "supervision"
    classification["work_unit"]["relation"] = "review"
    classification["work_unit"]["required"] = True
    requested = fixture.unit(
        "review.requested",
        "started",
        2,
        task_ref="review-unit",
        relation="review",
        required=True,
        actor_id="supervisor",
        profile="supervisor",
    )
    requested["producer_epoch"] = "prd_" + "2" * 32
    requested["producer_seq"] = 0
    approved = fixture.unit(
        "review.approved",
        "passed",
        3,
        task_ref="review-unit",
        relation="review",
        required=True,
        actor_id="supervisor",
        profile="supervisor",
    )
    approved["producer_epoch"] = "prd_" + "3" * 32
    approved["producer_seq"] = 0

    summaries = [
        reduce_events(
            ReductionInput(
                trace_id=fixture.trace_id,
                project_id=fixture.project_id,
                events=deepcopy(list(order)),
                producer_count=4,
                authority_context=AuthorityContext.product_default(),
            )
        )
        for order in permutations((native, classification, requested, approved))
    ]

    assert len({summary["summary_id"] for summary in summaries}) == 1
    for summary in summaries:
        [unit] = summary["work_graph"]["units"]
        assert unit["relation"] == "unknown"
        assert unit["required"] is None
        assert unit["review_state"] != "approved"
        reasons = {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
        assert "WORK_UNIT_CLASSIFICATION_BINDING_UNVERIFIED" in reasons
        assert "REVIEW_ASSIGNMENT_UNVERIFIED" in reasons


def test_independent_producers_are_permutation_deterministic_without_wall_clock_order() -> None:
    fixture = EventFactory()
    first = fixture.contract(
        "contract.revision",
        "reported",
        20,
        revision=1,
        after_sha256="a" * 64,
    )
    second = fixture.contract(
        "contract.revision",
        "reported",
        10,
        revision=2,
        after_sha256="b" * 64,
    )
    first["producer_epoch"], first["producer_seq"] = "prd_" + "1" * 32, 0
    second["producer_epoch"], second["producer_seq"] = "prd_" + "2" * 32, 0

    original_order = [event["event_id"] for event in causal_order([first, second])]
    assert original_order == [first["event_id"], second["event_id"]]
    assert [event["event_id"] for event in causal_order([second, first])] == original_order

    first["occurred_at"], second["occurred_at"] = (
        second["occurred_at"],
        first["occurred_at"],
    )
    assert [event["event_id"] for event in causal_order([second, first])] == original_order
    assert all(not step["predecessor_step_ids"] for step in build_process([second, first])["steps"])


def _round_causal_facts(process: dict[str, object]) -> set[tuple[str, frozenset[str], object]]:
    """Compare round membership/edges without treating presentation IDs as causality."""
    rounds = process["rounds"]
    assert isinstance(rounds, list)
    evidence_by_round = {
        round_["round_id"]: frozenset(round_["evidence_event_ids"]) for round_ in rounds
    }
    return {
        (
            round_["trigger"],
            evidence_by_round[round_["round_id"]],
            evidence_by_round.get(round_["previous_round_id"]),
        )
        for round_ in rounds
    }


def _independent_runs_and_direction_change(direction_epoch: str) -> dict[str, object]:
    fixture = EventFactory()
    fixture.opened(0)
    starts_and_finishes: list[tuple[dict[str, object], dict[str, object]]] = []
    for run_id, task_ref, epoch, second in (
        (1, "root-a", "a", 1),
        (2, "root-b", "b", 3),
    ):
        started = fixture.unit(
            "run.started",
            "started",
            second,
            task_ref=task_ref,
            relation="root",
            task_status="running",
            run_status="running",
            run_id=run_id,
        )
        finished = fixture.unit(
            "run.finished",
            "completed",
            second + 1,
            task_ref=task_ref,
            relation="root",
            task_status="done",
            run_status="done",
            run_outcome="completed",
            run_id=run_id,
        )
        for sequence, event in enumerate((started, finished)):
            event["producer_epoch"] = "prd_" + epoch * 32
            event["producer_seq"] = sequence
        starts_and_finishes.append((started, finished))

    direction = fixture.contract(
        "decision.superseded",
        "superseded",
        2.5,
        decision_refs=("decision-new",),
        supersedes_decision_ref="decision-old",
        semantic_delta="decision",
    )
    direction["producer_epoch"] = direction_epoch
    direction["producer_seq"] = 0
    process = build_process(fixture.events)

    round_by_evidence = {
        event_id: round_
        for round_ in process["rounds"]
        for event_id in round_["evidence_event_ids"]
    }
    for started, finished in starts_and_finishes:
        run_round = round_by_evidence[started["event_id"]]
        assert run_round["trigger"] == "initial_dispatch"
        assert run_round["previous_round_id"] is None
        assert finished["event_id"] in run_round["evidence_event_ids"]
        assert direction["event_id"] not in run_round["evidence_event_ids"]
    direction_round = round_by_evidence[direction["event_id"]]
    assert direction_round["trigger"] == "owner_direction_change"
    assert direction_round["previous_round_id"] is None
    assert direction_round["evidence_event_ids"] == [direction["event_id"]]
    return process


def test_independent_direction_trigger_cannot_partition_unrelated_run_spans() -> None:
    before = _independent_runs_and_direction_change("prd_" + "0" * 32)
    after = _independent_runs_and_direction_change("prd_" + "f" * 32)

    assert _round_causal_facts(before) == _round_causal_facts(after)


def test_two_explicit_task_roots_do_not_create_a_previous_round_edge() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    starts: list[dict[str, object]] = []
    for run_id, root, branch, second in (
        (1, "root-a", "branch-a", 1),
        (2, "root-b", "branch-b", 2),
    ):
        fixture.unit(
            "work_unit.bound",
            "reported",
            second - 0.2,
            task_ref=root,
            relation="root",
            task_status="running",
        )
        fixture.unit(
            "work_unit.bound",
            "reported",
            second - 0.1,
            task_ref=branch,
            parent_task_refs=(root,),
            task_status="running",
        )
        starts.append(
            fixture.unit(
                "run.started",
                "started",
                second,
                task_ref=branch,
                parent_task_refs=(root,),
                task_status="running",
                run_status="running",
                run_id=run_id,
            )
        )

    process = build_process(fixture.events)
    containing = [
        round_
        for round_ in process["rounds"]
        if any(start["event_id"] in round_["evidence_event_ids"] for start in starts)
    ]
    assert len(containing) == 2
    assert {round_["trigger"] for round_ in containing} == {"initial_dispatch"}
    assert all(round_["previous_round_id"] is None for round_ in containing)


def test_conflicting_parentage_cannot_merge_independent_root_rounds() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    starts: list[dict[str, object]] = []
    for run_id, root, second in ((1, "root-a", 1), (2, "root-b", 2)):
        fixture.unit(
            "work_unit.bound",
            "reported",
            second - 0.1,
            task_ref=root,
            relation="root",
            task_status="running",
        )
        starts.append(
            fixture.unit(
                "run.started",
                "started",
                second,
                task_ref=root,
                relation="root",
                task_status="running",
                run_status="running",
                run_id=run_id,
            )
        )

    bridge = fixture.unit(
        "work_unit.bound",
        "reported",
        0.3,
        task_ref="bridge",
        parent_task_refs=("root-a",),
        task_status="running",
    )
    conflict = _independent_conflicting_event(
        fixture,
        bridge,
        identity_digit="e",
        seconds=0.4,
    )
    conflict["work_unit"]["parent_task_refs"] = ["root-b"]
    validate_event(conflict)
    fixture.events.append(conflict)

    process = build_process(fixture.events)
    containing = [
        round_
        for round_ in process["rounds"]
        if any(start["event_id"] in round_["evidence_event_ids"] for start in starts)
    ]

    assert len(containing) == 2
    assert all(round_["trigger"] == "initial_dispatch" for round_ in containing)
    assert all(round_["previous_round_id"] is None for round_ in containing)


def test_unlinked_attempts_of_one_child_never_share_a_round_or_wave() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        0.1,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    fixture.unit(
        "work_unit.bound",
        "reported",
        0.2,
        task_ref="child",
        parent_task_refs=("root",),
        task_status="running",
    )
    starts: list[dict[str, object]] = []
    for run_id, epoch, second, outcome in (
        (1, "7", 1, "timed_out"),
        (2, "8", 3, "completed"),
    ):
        started = fixture.unit(
            "run.started",
            "started",
            second,
            task_ref="child",
            parent_task_refs=("root",),
            task_status="running",
            run_status="running",
            run_id=run_id,
        )
        finished = fixture.unit(
            "run.finished",
            outcome,
            second + 1,
            task_ref="child",
            parent_task_refs=("root",),
            task_status="ready" if outcome == "timed_out" else "done",
            run_status="timed_out" if outcome == "timed_out" else "done",
            run_outcome=outcome,
            run_id=run_id,
        )
        for sequence, event in enumerate((started, finished)):
            event["producer_epoch"] = "prd_" + epoch * 32
            event["producer_seq"] = sequence
        starts.append(started)

    process = build_process(fixture.events)
    containing = [
        round_
        for round_ in process["rounds"]
        if any(start["event_id"] in round_["evidence_event_ids"] for start in starts)
    ]
    assert len(containing) == 2
    assert all(round_["trigger"] == "initial_dispatch" for round_ in containing)
    assert all(round_["previous_round_id"] is None for round_ in containing)
    assert all(len(round_["wave_ids"]) == 1 for round_ in containing)
    assert containing[0]["wave_ids"] != containing[1]["wave_ids"]


def test_unique_durable_parent_task_links_implementation_to_review_critical_path() -> None:
    process = complete_trace().summary()["process"]
    implementation = next(
        step
        for step in process["steps"]
        if step["kind"] == "implementation" and step["task_refs"] == ["impl"]
    )
    review = next(
        step
        for step in process["steps"]
        if step["kind"] == "review" and step["task_refs"] == ["review"]
    )

    assert review["predecessor_step_ids"] == [implementation["step_id"]]
    assert process["critical_path"]["step_ids"] == [
        implementation["step_id"],
        review["step_id"],
    ]
    assert process["critical_path"]["duration_ms"] == 6000
    assert process["critical_path"]["review_wait_ms"] == 2000


def test_ambiguous_parent_task_attempts_cannot_select_a_review_predecessor() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    for run_id, epoch, start in ((1, "7", 1), (2, "8", 3)):
        started = fixture.unit(
            "run.started",
            "started",
            start,
            task_ref="impl",
            parent_task_refs=("root",),
            task_status="running",
            run_status="running",
            run_id=run_id,
        )
        finished = fixture.unit(
            "run.finished",
            "completed",
            start + 1,
            task_ref="impl",
            parent_task_refs=("root",),
            task_status="done",
            run_status="done",
            run_outcome="completed",
            run_id=run_id,
        )
        for sequence, event in enumerate((started, finished)):
            event["producer_epoch"] = "prd_" + epoch * 32
            event["producer_seq"] = sequence
    fixture.unit(
        "review.requested",
        "started",
        5,
        task_ref="review",
        relation="review",
        parent_task_refs=("impl",),
        task_status="review",
    )
    fixture.unit(
        "review.approved",
        "passed",
        7,
        task_ref="review",
        relation="review",
        parent_task_refs=("impl",),
        task_status="done",
    )

    process = build_process(fixture.events)
    implementation_steps = [
        step
        for step in process["steps"]
        if step["kind"] == "implementation" and step["task_refs"] == ["impl"]
    ]
    review = next(step for step in process["steps"] if step["kind"] == "review")

    assert len(implementation_steps) == 2
    assert review["predecessor_step_ids"] == []


def test_explicit_trigger_edge_assigns_descendant_span_and_previous_round() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    first_start = fixture.unit(
        "run.started",
        "started",
        1,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=1,
    )
    first_finish = fixture.unit(
        "run.finished",
        "completed",
        2,
        task_ref="root",
        relation="root",
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=1,
    )
    direction = fixture.builder.contract(
        event_type="decision.superseded",
        status="superseded",
        decision_refs=("decision-new",),
        supersedes_decision_ref="decision-old",
        semantic_delta="decision",
        occurred_at=fixture.at(3),
        parent_event_id=first_finish["event_id"],
        source_kind="aether_checkpoint",
        actor_kind="agent",
        actor_id="morfeo",
        profile="morfeo",
        role="verification",
    )
    fixture.add(direction)
    second_start = fixture.unit(
        "run.started",
        "started",
        4,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=2,
    )
    second_start["parent_event_id"] = direction["event_id"]
    second_finish = fixture.unit(
        "run.finished",
        "completed",
        5,
        task_ref="root",
        relation="root",
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=2,
    )

    process = build_process(fixture.events)
    round_by_evidence = {
        event_id: round_
        for round_ in process["rounds"]
        for event_id in round_["evidence_event_ids"]
    }
    initial = round_by_evidence[first_start["event_id"]]
    changed = round_by_evidence[direction["event_id"]]
    assert first_finish["event_id"] in initial["evidence_event_ids"]
    assert changed["trigger"] == "owner_direction_change"
    assert changed["previous_round_id"] == initial["round_id"]
    assert second_start["event_id"] in changed["evidence_event_ids"]
    assert second_finish["event_id"] in changed["evidence_event_ids"]


def test_opaque_producer_epoch_cannot_decide_verification_freshness() -> None:
    states: list[tuple[str, set[str]]] = []
    for independent_epoch in ("prd_" + "0" * 32, "prd_" + "f" * 32):
        fixture = _settled_trace()
        delta = fixture.contract(
            "decision.recorded",
            "reported",
            5,
            decision_refs=("independent-decision",),
            semantic_delta="decision",
        )
        delta["producer_epoch"] = independent_epoch
        delta["producer_seq"] = 0
        summary = fixture.summary()
        states.append(
            (
                summary["completion_state"],
                {gap["reason_code"] for gap in summary["coverage"]["gaps"]},
            )
        )

    assert states[0] == states[1]
    assert states[0][0] == "completion_candidate"
    assert "VERIFICATION_FRESHNESS_UNPROVEN" in states[0][1]


def test_anomalous_terminal_without_retry_edge_does_not_create_redispatch_round() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        0.5,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    for run_id, epoch, outcome, start in (
        (1, "7", "timed_out", 1),
        (2, "8", "completed", 3),
    ):
        started = fixture.unit(
            "run.started",
            "started",
            start,
            task_ref="root",
            relation="root",
            task_status="running",
            run_status="running",
            run_id=run_id,
        )
        finished = fixture.unit(
            "run.finished",
            outcome,
            start + 1,
            task_ref="root",
            relation="root",
            task_status="done" if outcome == "completed" else "ready",
            run_status="done" if outcome == "completed" else "timed_out",
            run_outcome=outcome,
            run_id=run_id,
        )
        for sequence, event in enumerate((started, finished)):
            event["producer_epoch"] = "prd_" + epoch * 32
            event["producer_seq"] = sequence

    process = fixture.summary()["process"]
    assert "redispatch" not in {round_["trigger"] for round_ in process["rounds"]}
    assert process["critical_path"]["rework_ms"] == 0


def test_dispatch_without_declared_limits_degrades_coverage() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.add(
        fixture.builder.dispatch(
            tick_ref="tick-without-limits",
            outcome="ok",
            bottleneck_class="unknown",
            eligible_count=2,
            running_count=1,
            global_limit=None,
            per_profile_limit=None,
            precision_ms=1000,
            occurred_at=fixture.at(1),
        )
    )

    assert "DISPATCH_LIMITS_UNAVAILABLE" in {
        gap["reason_code"] for gap in fixture.summary()["coverage"]["gaps"]
    }


def test_terminal_without_start_and_model_without_terminal_degrade_coverage() -> None:
    terminal = EventFactory()
    terminal.opened(0)
    _tool_end(terminal, 1, "terminal-only", "completed")
    terminal_summary = terminal.summary()
    assert "TOOL_TERMINAL_WITHOUT_START" in {
        gap["reason_code"] for gap in terminal_summary["coverage"]["gaps"]
    }

    model = EventFactory()
    model.opened(0)
    model.add(
        model.builder.model_request(
            state="started",
            request_ref=native_pseudonym("api_request", "request-without-terminal"),
            model="model-a",
            provider="provider-a",
            attempt_count=1,
            occurred_at=model.at(1),
            session_id=native_pseudonym("session", "session-a"),
        )
    )
    model_summary = model.summary()
    reasons = {gap["reason_code"] for gap in model_summary["coverage"]["gaps"]}
    assert reasons >= {
        "MODEL_SPAN_UNPAIRED",
        "TURN_ID_MISSING",
        "API_REQUEST_ID_MISSING",
    }
    assert model_summary["model_context_economics"]["request_count"] == 0


def test_missing_turn_and_request_ids_are_independent_coverage_gaps() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.add(
        fixture.builder.tool_started(
            call_id=native_pseudonym("tool_call", "missing-identifiers"),
            name="file.read",
            category="file",
            occurred_at=fixture.at(1),
            session_id=native_pseudonym("session", "session-a"),
        )
    )
    fixture.add(
        fixture.builder.tool_terminal(
            call_id=native_pseudonym("tool_call", "missing-identifiers"),
            name="file.read",
            category="file",
            status="completed",
            occurred_at=fixture.at(2),
            session_id=native_pseudonym("session", "session-a"),
        )
    )
    reasons = {gap["reason_code"] for gap in fixture.summary()["coverage"]["gaps"]}
    assert reasons >= {"TURN_ID_MISSING", "API_REQUEST_ID_MISSING"}


@pytest.mark.parametrize(
    ("heartbeat_age_seconds", "expected"),
    [(0, "alive"), (121, "stale"), (None, "unknown")],
)
def test_liveness_uses_versioned_native_heartbeat_recency(
    heartbeat_age_seconds: int | None, expected: str
) -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "started",
        0.5,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
    )
    if heartbeat_age_seconds is not None:
        status = fixture.unit(
            "work_unit.status",
            "started",
            1,
            task_ref="root",
            relation="root",
            task_status="running",
            run_status="running",
        )
        status["source_kind"] = "native_reconciliation"
        status["timestamp_source"] = "native"
        if heartbeat_age_seconds:
            fixture.event("participant.joined", "started", 1 + heartbeat_age_seconds)
    summary = fixture.summary()
    assert summary["runtime_state"]["liveness"] == expected
    assert summary["runtime_state"]["progress"] == "verified"
    assert summary["timestamps"]["last_verified_progress_at"] == fixture.events[1]["occurred_at"]


def test_protocol_violation_outcome_is_not_folded_away_as_generic_success() -> None:
    fixture = EventFactory()
    fixture.opened(0)
    fixture.unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    fixture.unit(
        "run.started",
        "started",
        2,
        task_ref="root",
        relation="root",
        task_status="running",
        run_status="running",
        run_id=1,
    )
    terminal = fixture.unit(
        "run.finished",
        "unknown",
        3,
        task_ref="root",
        relation="root",
        task_status="ready",
        run_status="released",
        run_outcome="unknown",
        run_id=1,
    )
    terminal["work_unit"]["run_outcome"] = "protocol_violation"
    summary = _reduce_with_authority(fixture, AuthorityContext.product_default())
    assert summary["work_graph"]["run_totals"]["protocol_violation"] == 1
    assert summary["model_context_economics"]["protocol_violation_count"] == 1
    assert "protocol_correction" not in {
        round_["trigger"] for round_ in summary["process"]["rounds"]
    }
    assert "RUN_PROTOCOL_VIOLATION" in {gap["reason_code"] for gap in summary["coverage"]["gaps"]}
