from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from inspect import signature
from itertools import count

import pytest

from aether_agents.effects import (
    ApprovalReplayCache,
    EffectClass,
    EffectLifecycle,
    EffectReceipt,
    EffectSpec,
    SecretReference,
    TypedApproval,
    can_retry,
    sign_approval,
    transition_effect,
    verify_approval,
)
from aether_agents.identity import ValidationError

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64
KEY = b"approval-test-key-with-enough-entropy"
NONCES = count(1)


def advance(effect, lifecycle):
    if lifecycle is EffectLifecycle.PLANNED:
        return effect
    verified = None
    if effect.effect_class is EffectClass.E4:
        verified = verify_approval(
            approval(effect),
            effect,
            key=KEY,
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
    if lifecycle is EffectLifecycle.AUTHORIZED:
        return effect
    effect = transition_effect(effect, EffectLifecycle.AUTHORIZED, EffectLifecycle.EXECUTING)
    if lifecycle is EffectLifecycle.EXECUTING:
        return effect
    first = lifecycle
    if lifecycle in {
        EffectLifecycle.RECONCILED_SUCCEEDED,
        EffectLifecycle.RECONCILED_FAILED,
        EffectLifecycle.MANUAL_RESOLUTION,
    }:
        first = EffectLifecycle.UNKNOWN
    effect = transition_effect(effect, EffectLifecycle.EXECUTING, first)
    if first is lifecycle:
        return effect
    return transition_effect(effect, EffectLifecycle.UNKNOWN, lifecycle)


def spec(effect_class=EffectClass.E1, lifecycle=EffectLifecycle.PLANNED):
    effect = EffectSpec(
        "proj",
        "contract",
        2,
        "task",
        "write",
        "target/v1",
        "v1",
        effect_class,
        EffectLifecycle.PLANNED,
        HASH_A,
    )
    return advance(effect, lifecycle)


def approval(effect, *, nonce=None, artifact_hash=HASH_B, target=None):
    nonce = nonce or f"nonce-{next(NONCES)}"
    value = TypedApproval(
        "user-1",
        effect.effect_id,
        target or effect.target,
        effect.contract_id,
        effect.generation,
        HASH_A,
        artifact_hash,
        nonce,
        NOW,
        NOW + timedelta(minutes=5),
    )
    return sign_approval(value, KEY)


def test_effect_identity_binds_every_logical_operation_dimension():
    original = spec()
    assert original.effect_id == spec().effect_id
    assert original.idempotency_key == spec().idempotency_key
    variants = (
        EffectSpec(
            "other", "contract", 2, "task", "write", "target/v1", "v1", EffectClass.E1, precondition_hash=HASH_A
        ),
        EffectSpec("proj", "other", 2, "task", "write", "target/v1", "v1", EffectClass.E1, precondition_hash=HASH_A),
        EffectSpec("proj", "contract", 3, "task", "write", "target/v1", "v1", EffectClass.E1, precondition_hash=HASH_A),
        EffectSpec(
            "proj", "contract", 2, "other", "write", "target/v1", "v1", EffectClass.E1, precondition_hash=HASH_A
        ),
        EffectSpec("proj", "contract", 2, "task", "read", "target/v1", "v1", EffectClass.E1, precondition_hash=HASH_A),
        EffectSpec("proj", "contract", 2, "task", "write", "other", "v1", EffectClass.E1, precondition_hash=HASH_A),
        EffectSpec("proj", "contract", 2, "task", "write", "target/v1", "v2", EffectClass.E1, precondition_hash=HASH_A),
    )
    assert len({original.effect_id, *(item.effect_id for item in variants)}) == 8


@pytest.mark.parametrize("value", [True, -1, 1.5, "2"])
def test_generation_rejects_bool_negative_and_non_integer(value):
    with pytest.raises(ValidationError):
        EffectSpec("proj", "contract", value, "task", "write", "target", "v1", EffectClass.E1, precondition_hash=HASH_A)


def test_unknown_classes_states_and_bad_preconditions_fail_closed():
    with pytest.raises(ValidationError):
        EffectSpec("proj", "contract", 2, "task", "write", "target", "v1", "E1", precondition_hash=HASH_A)
    with pytest.raises(ValidationError):
        EffectSpec("proj", "contract", 2, "task", "write", "target", "v1", EffectClass.E1, "planned", HASH_A)
    with pytest.raises(ValidationError):
        EffectSpec(
            "proj", "contract", 2, "task", "write", "target", "v1", EffectClass.E1, precondition_hash="not-a-hash"
        )


def test_nonplanned_effect_state_cannot_be_asserted_by_direct_construction():
    with pytest.raises(ValidationError, match="transition"):
        EffectSpec(
            "proj",
            "contract",
            2,
            "task",
            "write",
            "target",
            "v1",
            EffectClass.E4,
            EffectLifecycle.SUCCEEDED,
            HASH_A,
        )


def test_e0_e1_retry_only_from_failed_with_same_preconditions():
    failed = spec(EffectClass.E1, EffectLifecycle.FAILED)
    assert can_retry(failed, EffectLifecycle.FAILED, precondition_hash=HASH_A)
    assert not can_retry(failed, EffectLifecycle.FAILED, precondition_hash=HASH_B)
    retried = transition_effect(failed, EffectLifecycle.FAILED, EffectLifecycle.AUTHORIZED, precondition_hash=HASH_A)
    assert retried.effect_id == failed.effect_id
    assert retried.idempotency_key == failed.idempotency_key


def test_e2_e3_require_reconciliation_before_retry():
    failed = spec(EffectClass.E2, EffectLifecycle.FAILED)
    assert not can_retry(failed, EffectLifecycle.FAILED, precondition_hash=HASH_A)
    with pytest.raises(ValidationError):
        transition_effect(failed, EffectLifecycle.FAILED, EffectLifecycle.AUTHORIZED, precondition_hash=HASH_A)
    reconciled = spec(EffectClass.E2, EffectLifecycle.RECONCILED_FAILED)
    assert can_retry(reconciled, EffectLifecycle.RECONCILED_FAILED, precondition_hash=HASH_A)
    assert (
        transition_effect(
            reconciled,
            EffectLifecycle.RECONCILED_FAILED,
            EffectLifecycle.AUTHORIZED,
            precondition_hash=HASH_A,
        ).lifecycle
        is EffectLifecycle.AUTHORIZED
    )


@pytest.mark.parametrize("state", [EffectLifecycle.FAILED, EffectLifecycle.UNKNOWN, EffectLifecycle.RECONCILED_FAILED])
def test_e4_never_retries_automatically(state):
    effect = spec(EffectClass.E4, state)
    assert not can_retry(effect, state, precondition_hash=HASH_A)
    with pytest.raises(ValidationError):
        transition_effect(effect, state, EffectLifecycle.AUTHORIZED, precondition_hash=HASH_A)


def test_unknown_outcome_is_only_resolved_by_reconciliation_or_manual_resolution():
    effect = spec(EffectClass.E3, EffectLifecycle.UNKNOWN)
    with pytest.raises(ValidationError):
        transition_effect(effect, EffectLifecycle.UNKNOWN, EffectLifecycle.FAILED)
    assert (
        transition_effect(effect, EffectLifecycle.UNKNOWN, EffectLifecycle.RECONCILED_SUCCEEDED).lifecycle
        is EffectLifecycle.RECONCILED_SUCCEEDED
    )
    assert (
        transition_effect(effect, EffectLifecycle.UNKNOWN, EffectLifecycle.MANUAL_RESOLUTION).lifecycle
        is EffectLifecycle.MANUAL_RESOLUTION
    )


def test_e4_authorization_requires_exact_signed_unexpired_single_use_approval():
    effect = spec(EffectClass.E4)
    signed = approval(effect)
    replay = ApprovalReplayCache()
    assert verify_approval(
        signed, effect, key=KEY, now=NOW, replay_cache=replay, artifact_hash=HASH_B, allowed_authorities={"user-1"}
    )
    with pytest.raises(ValidationError, match="replay"):
        verify_approval(
            signed, effect, key=KEY, now=NOW, replay_cache=replay, artifact_hash=HASH_B, allowed_authorities={"user-1"}
        )


@pytest.mark.parametrize(
    "mutation",
    [
        {"target": "other"},
        {"artifact_hash": HASH_A},
        {"allowed_authorities": {"other"}},
        {"now": NOW + timedelta(hours=1)},
        {"key": b"wrong-key-with-enough-entropy"},
    ],
)
def test_approval_binding_signature_authority_and_expiry_fail_closed(mutation):
    effect = spec(EffectClass.E4)
    signed = approval(effect)
    kwargs = dict(
        key=KEY, now=NOW, replay_cache=ApprovalReplayCache(), artifact_hash=HASH_B, allowed_authorities={"user-1"}
    )
    if "target" in mutation:
        effect = EffectSpec(
            "proj",
            "contract",
            2,
            "task",
            "write",
            mutation.pop("target"),
            "v1",
            EffectClass.E4,
            precondition_hash=HASH_A,
        )
    kwargs.update(mutation)
    with pytest.raises(ValidationError):
        verify_approval(signed, effect, **kwargs)


def test_e4_planned_to_authorized_requires_verified_approval():
    effect = spec(EffectClass.E4)
    with pytest.raises(ValidationError):
        transition_effect(effect, EffectLifecycle.PLANNED, EffectLifecycle.AUTHORIZED)
    verified = verify_approval(
        approval(effect),
        effect,
        key=KEY,
        now=NOW,
        replay_cache=ApprovalReplayCache(),
        artifact_hash=HASH_B,
        allowed_authorities={"user-1"},
    )
    authorized = transition_effect(
        effect,
        EffectLifecycle.PLANNED,
        EffectLifecycle.AUTHORIZED,
        verified_approval=verified,
    )
    assert authorized.lifecycle is EffectLifecycle.AUTHORIZED
    with pytest.raises(ValidationError, match="replay"):
        transition_effect(
            effect,
            EffectLifecycle.PLANNED,
            EffectLifecycle.AUTHORIZED,
            verified_approval=verified,
        )


def test_receipt_is_bound_to_effect_identity_target_and_terminal_state():
    effect = spec(EffectClass.E1, EffectLifecycle.SUCCEEDED)
    receipt = EffectReceipt(
        effect,
        "actor",
        NOW,
        EffectLifecycle.SUCCEEDED,
        "ok",
        "artifact/ref",
        HASH_B,
    )
    assert (
        receipt.effect_id,
        receipt.idempotency_key,
        receipt.project_id,
        receipt.contract_id,
        receipt.generation,
        receipt.task_id,
        receipt.target,
        receipt.effect_class,
        receipt.precondition_hash,
    ) == (
        effect.effect_id,
        effect.idempotency_key,
        effect.project_id,
        effect.contract_id,
        effect.generation,
        effect.task_id,
        effect.target,
        effect.effect_class,
        effect.precondition_hash,
    )
    assert "target" not in signature(EffectReceipt).parameters
    with pytest.raises((TypeError, ValidationError)):
        replace(receipt, target="other-target")
    with pytest.raises(FrozenInstanceError):
        receipt.target = "other-target"
    with pytest.raises(ValidationError):
        EffectReceipt(effect, "actor", NOW, EffectLifecycle.EXECUTING, "ok")


def test_receipt_contract_task_target_and_precondition_follow_originating_effect():
    first = spec(EffectClass.E1, EffectLifecycle.SUCCEEDED)
    second = advance(
        EffectSpec(
            "proj",
            "other-contract",
            2,
            "other-task",
            "write",
            "other-target",
            "v1",
            EffectClass.E1,
            EffectLifecycle.PLANNED,
            HASH_B,
        ),
        EffectLifecycle.SUCCEEDED,
    )
    first_receipt = EffectReceipt(first, "actor", NOW, EffectLifecycle.SUCCEEDED, "ok")
    second_receipt = EffectReceipt(second, "actor", NOW, EffectLifecycle.SUCCEEDED, "ok")
    assert first_receipt.effect_id != second_receipt.effect_id
    assert second_receipt.contract_id == "other-contract"
    assert second_receipt.task_id == "other-task"
    assert second_receipt.target == "other-target"
    assert second_receipt.precondition_hash == HASH_B


def test_secret_reference_is_opaque_bounded_and_project_scoped():
    assert SecretReference("proj", "ref-1").project_id == "proj"
    for bad in ("secret-value", "token", "x" * 129, " other"):
        with pytest.raises(ValidationError):
            SecretReference("proj", bad)
