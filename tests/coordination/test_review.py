from datetime import datetime, timedelta, timezone

import pytest

import aether_agents as coordination
from aether_agents.identity import ValidationError
from aether_agents.review import (
    MAX_REVIEW_ATTEMPTS,
    FindingKind,
    GateResult,
    ReviewerIdentity,
    ReviewEvidence,
    ReviewFinding,
    ReviewGate,
    ReviewWaiver,
    WaiverReplayCache,
    advance_attempt,
    evaluate_gate,
    sign_waiver,
    validate_reviewer,
)

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64
KEY = b"waiver-test-key-with-enough-entropy"
OWNER = ReviewerIdentity("owner", "runtime-owner", "credential-owner", "hefesto")
REVIEWER = ReviewerIdentity("reviewer", "runtime-reviewer", "credential-reviewer", "athena")


def gate(attempts=0):
    return ReviewGate("gate-1", "proj", "contract-1", "task-1", 2, HASH_A, "athena", attempts)


def evidence(evidence_id="ev-1", *, artifact_hash=HASH_A, generation=2):
    return ReviewEvidence(evidence_id, "gate-1", generation, artifact_hash, "tests/report", HASH_B)


def finding(kind=FindingKind.BLOCKING, *, attempt=1):
    return ReviewFinding(
        "finding-1",
        "gate-1",
        "criterion-1",
        kind,
        "precise claim",
        ("ev-1",),
        "high impact",
        "high",
        attempt,
    )


def waiver(*, nonce="nonce-1", artifact_hash=HASH_A, generation=2):
    value = ReviewWaiver(
        "finding-1",
        "gate-1",
        "contract-1",
        "artifact-1",
        artifact_hash,
        generation,
        "accepted risk",
        "documented rationale",
        "user-1",
        nonce,
        NOW,
        NOW + timedelta(minutes=5),
    )
    return sign_waiver(value, KEY)


def test_reviewer_independence_requires_distinct_control_identity_and_role():
    assert validate_reviewer(OWNER, REVIEWER, authorized_roles={"athena"})
    mutations = (
        ReviewerIdentity("owner", "runtime-reviewer", "credential-reviewer", "athena"),
        ReviewerIdentity("reviewer", "runtime-owner", "credential-reviewer", "athena"),
        ReviewerIdentity("reviewer", "runtime-reviewer", "credential-owner", "athena"),
        ReviewerIdentity("reviewer", "runtime-reviewer", "credential-reviewer", "hefesto"),
    )
    for candidate in mutations:
        with pytest.raises(ValidationError):
            validate_reviewer(OWNER, candidate, authorized_roles={"athena"})


def test_reviewer_authorization_and_explicit_self_review_fail_closed():
    with pytest.raises(ValidationError):
        validate_reviewer(OWNER, REVIEWER, authorized_roles={"athena"}, authorized=False)
    with pytest.raises(ValidationError):
        validate_reviewer(OWNER, REVIEWER, authorized_roles={"athena"}, self_review=True)


@pytest.mark.parametrize("attempts", [True, -1, 4, 1.5])
def test_review_attempt_bounds_reject_bool_negative_overflow_and_non_integer(attempts):
    with pytest.raises(ValidationError):
        gate(attempts)


def test_attempt_advance_is_stable_and_stops_after_three_total_executions():
    current = gate()
    for expected in (1, 2, 3):
        current = advance_attempt(current)
        assert current.attempts == expected
        assert current.gate_id == "gate-1" and current.task_id == "task-1"
    with pytest.raises(ValidationError, match="exhausted"):
        advance_attempt(current)
    assert MAX_REVIEW_ATTEMPTS == 3


def test_generation_and_artifact_binding_are_checked_before_gate_evaluation():
    with pytest.raises(ValidationError, match="generation"):
        evaluate_gate(
            gate(1),
            OWNER,
            REVIEWER,
            (),
            (evidence(),),
            current_generation=3,
            current_artifact_hash=HASH_A,
            authorized_roles={"athena"},
        )
    with pytest.raises(ValidationError, match="artifact"):
        evaluate_gate(
            gate(1),
            OWNER,
            REVIEWER,
            (),
            (evidence(),),
            current_generation=2,
            current_artifact_hash=HASH_B,
            authorized_roles={"athena"},
        )


def test_evidence_is_required_unique_and_bound_to_gate_generation_and_artifact():
    kwargs = dict(current_generation=2, current_artifact_hash=HASH_A, authorized_roles={"athena"})
    with pytest.raises(ValidationError, match="evidence"):
        evaluate_gate(gate(1), OWNER, REVIEWER, (), (), **kwargs)
    with pytest.raises(ValidationError, match="duplicate"):
        evaluate_gate(gate(1), OWNER, REVIEWER, (), (evidence(), evidence()), **kwargs)
    with pytest.raises(ValidationError):
        evaluate_gate(gate(1), OWNER, REVIEWER, (), (evidence(generation=3),), **kwargs)
    with pytest.raises(ValidationError):
        evaluate_gate(gate(1), OWNER, REVIEWER, (), (evidence(artifact_hash=HASH_B),), **kwargs)


@pytest.mark.parametrize("kind", [FindingKind.BLOCKING, FindingKind.INSUFFICIENT_EVIDENCE])
def test_blocking_and_insufficient_evidence_prevent_pass(kind):
    result = evaluate_gate(
        gate(1),
        OWNER,
        REVIEWER,
        (finding(kind),),
        (evidence(),),
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
    )
    assert result.result is GateResult.FAILED


@pytest.mark.parametrize("kind", [FindingKind.NON_BLOCKING, FindingKind.ADVISORY, FindingKind.OPERATIONAL])
def test_nonblocking_finding_classes_remain_visible_without_blocking(kind):
    result = evaluate_gate(
        gate(1),
        OWNER,
        REVIEWER,
        (finding(kind),),
        (evidence(),),
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
    )
    assert result.result is GateResult.PASSED


def test_finding_attempt_and_evidence_references_must_match_current_review():
    kwargs = dict(current_generation=2, current_artifact_hash=HASH_A, authorized_roles={"athena"})
    with pytest.raises(ValidationError):
        evaluate_gate(gate(2), OWNER, REVIEWER, (finding(attempt=1),), (evidence(),), **kwargs)
    broken = ReviewFinding(
        "finding-1", "gate-1", "criterion-1", FindingKind.BLOCKING, "claim", ("missing",), "impact", "high", 1
    )
    with pytest.raises(ValidationError):
        evaluate_gate(gate(1), OWNER, REVIEWER, (broken,), (evidence(),), **kwargs)


def test_valid_signed_waiver_is_exact_single_use_and_produces_waived_gate():
    result = evaluate_gate(
        gate(1),
        OWNER,
        REVIEWER,
        (finding(),),
        (evidence(),),
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
        signed_waiver=waiver(),
        waiver_key=KEY,
        waiver_now=NOW,
        waiver_replay_cache=WaiverReplayCache(),
        waiver_authorities={"user-1"},
    )
    assert result.result is GateResult.WAIVED


@pytest.mark.parametrize(
    "kwargs",
    [
        {"waiver_key": b"wrong-key-with-enough-entropy"},
        {"waiver_now": NOW + timedelta(hours=1)},
        {"waiver_authorities": {"other"}},
        {"signed_waiver": waiver(artifact_hash=HASH_B)},
        {"signed_waiver": waiver(generation=3)},
    ],
)
def test_waiver_signature_expiry_authority_artifact_and_generation_fail_closed(kwargs):
    base = dict(
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
        signed_waiver=waiver(),
        waiver_key=KEY,
        waiver_now=NOW,
        waiver_replay_cache=WaiverReplayCache(),
        waiver_authorities={"user-1"},
    )
    base.update(kwargs)
    with pytest.raises(ValidationError):
        evaluate_gate(gate(1), OWNER, REVIEWER, (finding(),), (evidence(),), **base)


def test_waiver_replay_is_rejected():
    cache = WaiverReplayCache()
    signed = waiver()
    kwargs = dict(
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
        signed_waiver=signed,
        waiver_key=KEY,
        waiver_now=NOW,
        waiver_replay_cache=cache,
        waiver_authorities={"user-1"},
    )
    assert evaluate_gate(gate(1), OWNER, REVIEWER, (finding(),), (evidence(),), **kwargs).result is GateResult.WAIVED
    with pytest.raises(ValidationError, match="replay"):
        evaluate_gate(gate(1), OWNER, REVIEWER, (finding(),), (evidence(),), **kwargs)


def test_no_public_gate_evaluation_bypass_exists():
    assert not hasattr(coordination, "final_gate")


def test_gate_evaluation_returns_authenticated_artifact_not_raw_enum():
    result = evaluate_gate(
        gate(1),
        OWNER,
        REVIEWER,
        (),
        (evidence(),),
        current_generation=2,
        current_artifact_hash=HASH_A,
        authorized_roles={"athena"},
    )
    assert result.result is GateResult.PASSED
    assert result.signature
