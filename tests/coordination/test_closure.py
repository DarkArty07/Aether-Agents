from copy import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import count

import pytest

from olympus_v3.coordination.closure import (
    CleanupStep,
    ClosureDecision,
    ClosureEvidence,
    ClosureProposal,
    CompletionAuthority,
    CompletionState,
    cleanup_plan,
    validate_closure,
)
from olympus_v3.coordination.effects import (
    ApprovalReplayCache,
    EffectClass,
    EffectLifecycle,
    EffectReceipt,
    EffectSpec,
    TypedApproval,
    sign_approval,
    transition_effect,
    verify_approval,
)
from olympus_v3.coordination.protocol import ValidationError
from olympus_v3.coordination.review import (
    FindingKind,
    GateResult,
    ReviewerIdentity,
    ReviewEvidence,
    ReviewFinding,
    ReviewGate,
    ReviewWaiver,
    WaiverReplayCache,
    evaluate_gate,
    sign_waiver,
)

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64
APPROVAL_KEY = b"approval-test-key-with-enough-entropy"
WAIVER_KEY = b"waiver-test-key-with-enough-entropy"
OWNER = ReviewerIdentity("owner", "runtime-owner", "credential-owner", "hefesto")
REVIEWER = ReviewerIdentity("reviewer", "runtime-reviewer", "credential-reviewer", "athena")
NONCES = count(1)


def evidence(evidence_id="ev-1"):
    return ClosureEvidence(evidence_id, "artifact/ref", HASH_A)


def proposal(
    state=CompletionState.COMPLETED,
    *,
    owner="owner",
    generation=2,
    authority=CompletionAuthority.HERMES,
    accepted_outcome="",
    unmet_criteria=(),
    residual_risks=(),
    authority_decision="decision-1",
):
    return ClosureProposal(
        "proj",
        "contract",
        "task",
        owner,
        generation,
        state,
        (evidence(),),
        authority,
        accepted_outcome,
        unmet_criteria,
        residual_risks,
        authority_decision,
    )


def gate_evaluation(result=GateResult.PASSED, *, project="proj"):
    gate = ReviewGate("gate-1", project, "contract", "task", 2, HASH_A, "athena", 1)
    review_evidence = ReviewEvidence("review-ev", "gate-1", 2, HASH_A, "tests/report", HASH_B)
    findings = ()
    kwargs = {}
    if result in (GateResult.FAILED, GateResult.WAIVED):
        findings = (
            ReviewFinding(
                "finding-1",
                "gate-1",
                "criterion-1",
                FindingKind.BLOCKING,
                "precise claim",
                ("review-ev",),
                "high impact",
                "high",
                1,
            ),
        )
    if result is GateResult.WAIVED:
        waiver = ReviewWaiver(
            "finding-1",
            "gate-1",
            "contract",
            "artifact-1",
            HASH_A,
            2,
            "accepted risk",
            "documented rationale",
            "user-1",
            "nonce-1",
            NOW,
            NOW + timedelta(minutes=5),
        )
        kwargs = {
            "signed_waiver": sign_waiver(waiver, WAIVER_KEY),
            "waiver_key": WAIVER_KEY,
            "waiver_now": NOW,
            "waiver_replay_cache": WaiverReplayCache(),
            "waiver_authorities": {"user-1"},
        }
    return evaluate_gate(
        gate,
        OWNER,
        REVIEWER,
        findings,
        (review_evidence,),
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
        **kwargs,
    )


def terminal_effect(effect_class=EffectClass.E1, state=EffectLifecycle.SUCCEEDED, *, project="proj"):
    effect = EffectSpec(
        project,
        "contract",
        2,
        "task",
        "write",
        "target/v1",
        "v1",
        effect_class,
        precondition_hash=HASH_A,
    )
    verified = None
    if effect_class is EffectClass.E4:
        approval = TypedApproval(
            "user-1",
            effect.effect_id,
            effect.target,
            effect.contract_id,
            effect.generation,
            HASH_A,
            HASH_B,
            f"approval-{next(NONCES)}",
            NOW,
            NOW + timedelta(minutes=5),
        )
        verified = verify_approval(
            sign_approval(approval, APPROVAL_KEY),
            effect,
            key=APPROVAL_KEY,
            now=NOW,
            replay_cache=ApprovalReplayCache(),
            artifact_hash=HASH_B,
            allowed_authorities={"user-1"},
        )
    effect = transition_effect(
        effect,
        EffectLifecycle.PLANNED,
        EffectLifecycle.AUTHORIZED,
        verified_approval=verified,
    )
    effect = transition_effect(effect, EffectLifecycle.AUTHORIZED, EffectLifecycle.EXECUTING)
    first = state
    if state in {
        EffectLifecycle.RECONCILED_SUCCEEDED,
        EffectLifecycle.RECONCILED_FAILED,
        EffectLifecycle.MANUAL_RESOLUTION,
    }:
        first = EffectLifecycle.UNKNOWN
    effect = transition_effect(effect, EffectLifecycle.EXECUTING, first)
    if first is not state:
        effect = transition_effect(effect, EffectLifecycle.UNKNOWN, state)
    return effect


def effects(effect_class=EffectClass.E1, state=EffectLifecycle.SUCCEEDED, *, project="proj"):
    effect = terminal_effect(effect_class, state, project=project)
    return (EffectReceipt(effect, "actor", NOW, state, "result"),)


def validate(value, **overrides):
    kwargs = dict(
        current_owner="owner",
        current_generation=2,
        required_gates={"gate-1"},
        gate_results=(gate_evaluation(),),
        required_evidence={"ev-1"},
        effect_results=effects(),
        decision_authority=CompletionAuthority.HERMES,
        automatic_allowed=False,
        technical_status="completed",
        critical_evidence=True,
        integrity=True,
        secret_violation=False,
    )
    kwargs.update(overrides)
    return validate_closure(value, **kwargs)


def test_owner_proposal_is_never_final_and_owner_generation_are_exact():
    value = proposal()
    assert value.is_final is False
    with pytest.raises(ValidationError, match="owner"):
        validate(value, current_owner="other")
    with pytest.raises(ValidationError, match="generation"):
        validate(value, current_generation=3)


def test_cleanup_order_is_exact_and_immutable():
    assert cleanup_plan() == (
        CleanupStep.STOP_ADMISSION,
        CleanupStep.REVOKE_CAPABILITIES,
        CleanupStep.RECONCILE_EFFECTS_SESSIONS,
        CleanupStep.RELEASE_LEASE,
        CleanupStep.PUBLISH_CONTINUITY,
        CleanupStep.IDLE_SHUTDOWN,
    )


def test_completed_requires_exact_evidence_authenticated_gate_and_reconciled_receipts():
    decision = validate(proposal())
    assert isinstance(decision, ClosureDecision)
    assert decision.state is CompletionState.COMPLETED
    with pytest.raises(ValidationError, match="evidence"):
        validate(proposal(), required_evidence={"missing"})
    with pytest.raises(ValidationError, match="gate"):
        validate(proposal(), gate_results=(gate_evaluation(GateResult.FAILED),))
    assert validate(proposal(), gate_results=(gate_evaluation(GateResult.WAIVED),)).state is CompletionState.COMPLETED
    with pytest.raises(ValidationError, match="effect"):
        validate(proposal(), effect_results=effects(EffectClass.E2, EffectLifecycle.UNKNOWN))


def test_gate_evaluation_signature_and_scope_cannot_be_forged():
    evaluation = gate_evaluation()
    forged = replace(evaluation, result=GateResult.WAIVED)
    with pytest.raises(ValidationError, match="signature"):
        validate(proposal(), gate_results=(forged,))
    with pytest.raises(ValidationError, match="binding"):
        validate(proposal(), gate_results=(gate_evaluation(project="other"),))


def test_effect_receipt_signature_and_scope_cannot_be_forged():
    receipt = effects()[0]
    forged = copy(receipt)
    object.__setattr__(forged, "target", "other-target")
    with pytest.raises(ValidationError, match="signature"):
        validate(proposal(), effect_results=(forged,))
    with pytest.raises(ValidationError, match="binding"):
        validate(proposal(), effect_results=effects(project="other"))


@pytest.mark.parametrize(
    "override,match",
    [
        ({"integrity": False}, "integrity"),
        ({"critical_evidence": False}, "evidence"),
        ({"secret_violation": True}, "secret"),
        ({"effect_results": effects(EffectClass.E4, EffectLifecycle.UNKNOWN)}, "E4"),
    ],
)
def test_nonwaivable_fail_closed_conditions_raise_without_finalizing(override, match):
    with pytest.raises(ValidationError, match=match):
        validate(proposal(), **override)


def test_technical_completion_is_evidence_not_semantic_completion():
    assert validate(proposal(), technical_status="completed").state is CompletionState.COMPLETED
    with pytest.raises(ValidationError, match="technical"):
        validate(proposal(), technical_status="running")
    with pytest.raises(ValidationError):
        validate(proposal(), technical_status=True)


def test_partial_completion_requires_accepted_outcome_unmet_criteria_risk_and_authority_decision():
    value = proposal(
        CompletionState.PARTIALLY_COMPLETED,
        accepted_outcome="accepted subset",
        unmet_criteria=("criterion-2",),
        residual_risks=("risk-1",),
    )
    assert validate(value).state is CompletionState.PARTIALLY_COMPLETED
    for field in ("accepted_outcome", "unmet_criteria", "residual_risks", "authority_decision"):
        kwargs = dict(
            state=CompletionState.PARTIALLY_COMPLETED,
            accepted_outcome="accepted subset",
            unmet_criteria=("criterion-2",),
            residual_risks=("risk-1",),
            authority_decision="decision-1",
        )
        kwargs[field] = "" if field in ("accepted_outcome", "authority_decision") else ()
        with pytest.raises(ValidationError):
            proposal(**kwargs)


def test_failed_and_cancelled_are_real_final_states_with_authority_decision():
    assert validate(proposal(CompletionState.FAILED), technical_status="error").state is CompletionState.FAILED
    assert (
        validate(proposal(CompletionState.CANCELLED), technical_status="cancelled").state is CompletionState.CANCELLED
    )


def test_reserved_completion_authority_is_enforced_exactly():
    with pytest.raises(ValidationError, match="authority"):
        validate(proposal(authority=CompletionAuthority.USER), decision_authority=CompletionAuthority.HERMES)
    assert (
        validate(proposal(authority=CompletionAuthority.USER), decision_authority=CompletionAuthority.USER).state
        is CompletionState.COMPLETED
    )


def test_automatic_completion_is_explicit_and_low_risk_only():
    value = proposal(authority=CompletionAuthority.AUTOMATIC)
    with pytest.raises(ValidationError, match="automatic"):
        validate(value, decision_authority=CompletionAuthority.AUTOMATIC)
    assert (
        validate(value, decision_authority=CompletionAuthority.AUTOMATIC, automatic_allowed=True).state
        is CompletionState.COMPLETED
    )
    with pytest.raises(ValidationError, match="automatic"):
        validate(
            value,
            decision_authority=CompletionAuthority.AUTOMATIC,
            automatic_allowed=True,
            effect_results=effects(EffectClass.E2),
        )


def test_duplicate_gates_evidence_and_effects_are_rejected():
    gate = gate_evaluation()
    with pytest.raises(ValidationError, match="duplicate gate"):
        validate(proposal(), gate_results=(gate, gate))
    duplicate_evidence = ClosureProposal(
        "proj",
        "contract",
        "task",
        "owner",
        2,
        CompletionState.COMPLETED,
        (evidence(), evidence()),
        CompletionAuthority.HERMES,
        authority_decision="decision-1",
    )
    with pytest.raises(ValidationError, match="duplicate evidence"):
        validate(duplicate_evidence)
    receipt = effects()[0]
    with pytest.raises(ValidationError, match="duplicate effect"):
        validate(proposal(), effect_results=(receipt, receipt))


def test_bool_is_rejected_for_generation_and_security_flags():
    with pytest.raises(ValidationError):
        proposal(generation=True)
    with pytest.raises(ValidationError):
        validate(proposal(), integrity=1)


def test_no_public_forgeable_closure_assertion_dtos_exist():
    import olympus_v3.coordination as coordination

    assert not hasattr(coordination, "ClosureGate")
    assert not hasattr(coordination, "EffectClosure")
