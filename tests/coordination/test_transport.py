from datetime import UTC, datetime

import pytest

from olympus_v3.coordination import (
    AuthorityClass,
    AuthorizationDenial,
    AuthorizationResult,
    Channel,
    ChannelACL,
    ChannelPublishContext,
    ChannelRoute,
    DeliveryClass,
    Envelope,
    IdentityRegistry,
    KeyPurpose,
    MessagePart,
    MessageType,
    NativeTransportAdapter,
    ParticipantCard,
    ParticipantRoute,
    Principal,
    RoleRoute,
    TransportStatus,
    WorkloadBinding,
    issue_identity_credential,
)

PROJECT = "project-a"
SENDER = Principal(PROJECT, "hermes", "owner")
WORKER_A = Principal(PROJECT, "hefesto-a", "worker")
WORKER_B = Principal(PROJECT, "hefesto-b", "worker")
CARD = ParticipantCard(SENDER, "owner", "model-a", ("coordination",))
STAMP = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


def envelope(route=None, **changes):
    values = {
        "message_id": "message_12345678",
        "timestamp": STAMP,
        "sender": SENDER,
        "sender_card": CARD,
        "message_type": MessageType.REQUEST,
        "authority": AuthorityClass.REQUEST,
        "project_id": PROJECT,
        "contract_id": "contract_12345678",
        "generation": 1,
        "task_id": "task_12345678",
        "correlation_id": "correlation_12345678",
        "reply_to": None,
        "references": (),
        "parts": (MessagePart("text", "work"),),
        "route": route or ParticipantRoute(WORKER_A),
    }
    values.update(changes)
    return Envelope(**values)


def cards():
    return (
        ParticipantCard(WORKER_B, "worker", "model-a", ("coordination",)),
        ParticipantCard(WORKER_A, "worker", "model-a", ("coordination",)),
    )


def channel_context(*, publish=True, contract_id="contract_12345678"):
    registry = IdentityRegistry(clock=lambda: 1000)
    registry.register_key("issuer-key", b"issuer-secret-material-00000001", purpose=KeyPurpose.ISSUER, ttl=10_000)
    registry.register_key("holder-key", b"holder-secret-material-00000001", purpose=KeyPurpose.HOLDER, ttl=10_000)
    registry.register_identity("identity-a", ttl=10_000)
    credential = issue_identity_credential(
        registry,
        WorkloadBinding("install-a", PROJECT, "owner", "hermes", "session-a", "runtime-a"),
        issuer="aether-issuer",
        audience="olympus-r4",
        key_id="issuer-key",
        identity_id="identity-a",
        holder_key_id="holder-key",
        not_before=1000,
        expires_at=2000,
    )
    channel = Channel("coordination", PROJECT, contract_id, 1, 0, DeliveryClass.DURABLE, True)
    acl = ChannelACL(
        "coordination",
        PROJECT,
        contract_id,
        1,
        0,
        frozenset(("identity-a",)),
        frozenset(("identity-a",)) if publish else frozenset(),
    )
    return ChannelPublishContext(
        registry,
        credential,
        channel,
        acl,
        "aether-issuer",
        "olympus-r4",
        1500,
        1,
        0,
    )


def test_transport_is_default_off_and_performs_no_io():
    adapter = NativeTransportAdapter()
    receipt = adapter.submit(
        envelope(),
        AuthorizationResult(True),
        current_generation=1,
        participants=(WORKER_A,),
    )

    assert receipt.status is TransportStatus.REJECTED
    assert receipt.reason == "coordination_disabled"
    assert adapter.pending_count == 0


def test_direct_and_role_anycast_routes_resolve_deterministically():
    direct = NativeTransportAdapter(enabled=True)
    assert direct.submit(
        envelope(), AuthorizationResult(True), current_generation=1, participants=(WORKER_A,)
    ).status is TransportStatus.QUEUED
    assert direct.next_batch(limit=1, now=100)[0].participant == WORKER_A

    role = NativeTransportAdapter(enabled=True)
    result = role.submit(
        envelope(RoleRoute("worker")),
        AuthorizationResult(True),
        current_generation=1,
        participants=(WORKER_B, WORKER_A),
        cards=cards(),
    )
    assert result.status is TransportStatus.QUEUED
    assert role.next_batch(limit=1, now=100)[0].participant == WORKER_A


def test_channel_publish_uses_canonical_identity_capability_and_acl_boundary():
    allowed = NativeTransportAdapter(enabled=True)
    receipt = allowed.submit(
        envelope(ChannelRoute("coordination")),
        AuthorizationResult(True),
        current_generation=1,
        channel_context=channel_context(),
    )
    assert receipt.status is TransportStatus.QUEUED
    intent = allowed.next_batch(limit=1, now=100)[0]
    assert intent.channel_id == "coordination"
    assert intent.participant is None

    denied = NativeTransportAdapter(enabled=True)
    receipt = denied.submit(
        envelope(ChannelRoute("coordination")),
        AuthorizationResult(True),
        current_generation=1,
        channel_context=channel_context(publish=False),
    )
    assert receipt.status is TransportStatus.REJECTED
    assert receipt.reason == "channel_publish_denied"

    cross_contract = NativeTransportAdapter(enabled=True)
    receipt = cross_contract.submit(
        envelope(ChannelRoute("coordination")),
        AuthorizationResult(True),
        current_generation=1,
        channel_context=channel_context(contract_id="contract_other1"),
    )
    assert receipt.status is TransportStatus.REJECTED
    assert receipt.reason == "channel_scope_mismatch"


def test_capability_generation_and_target_fail_closed_without_retry():
    adapter = NativeTransportAdapter(enabled=True)
    denied = AuthorizationResult(False, AuthorizationDenial.PERMISSION_DENIED)
    cases = (
        adapter.submit(envelope(), denied, current_generation=1, participants=(WORKER_A,)),
        adapter.submit(envelope(message_id="message_22345678"), AuthorizationResult(True), current_generation=2, participants=(WORKER_A,)),
        adapter.submit(envelope(message_id="message_32345678"), AuthorizationResult(True), current_generation=1, participants=()),
    )
    assert tuple(item.reason for item in cases) == (
        "capability_denied",
        "stale_generation",
        "unknown_participant",
    )
    assert adapter.pending_count == 0


def test_request_requires_correlation_and_transport_enforces_total_payload_limit():
    adapter = NativeTransportAdapter(enabled=True, max_payload_bytes=1024)
    no_correlation = adapter.submit(
        envelope(message_type=MessageType.CONTEXT, correlation_id=None),
        AuthorizationResult(True),
        current_generation=1,
        participants=(WORKER_A,),
    )
    oversized = adapter.submit(
        envelope(message_id="message_42345678", parts=(MessagePart("text", "x" * 1000),)),
        AuthorizationResult(True),
        current_generation=1,
        participants=(WORKER_A,),
    )
    assert no_correlation.status is TransportStatus.QUEUED
    assert oversized.reason == "payload_limit_exceeded"

    request_adapter = NativeTransportAdapter(enabled=True)
    malformed = envelope(message_type=MessageType.REQUEST, correlation_id=None)
    assert request_adapter.submit(
        malformed, AuthorizationResult(True), current_generation=1, participants=(WORKER_A,)
    ).reason == "correlation_required"


def test_backpressure_and_duplicate_message_ids_are_terminal_rejections():
    adapter = NativeTransportAdapter(enabled=True, max_pending=1)
    first = adapter.submit(envelope(), AuthorizationResult(True), current_generation=1, participants=(WORKER_A,))
    duplicate = adapter.submit(envelope(), AuthorizationResult(True), current_generation=1, participants=(WORKER_A,))
    second = adapter.submit(
        envelope(message_id="message_52345678"), AuthorizationResult(True), current_generation=1, participants=(WORKER_A,)
    )
    assert first.status is TransportStatus.QUEUED
    assert duplicate.reason == "duplicate_message"
    assert second.reason == "backpressure"


def test_ack_and_nack_have_bounded_retry_and_terminal_poison_state():
    adapter = NativeTransportAdapter(enabled=True, max_attempts=2, retry_delay_seconds=10)
    adapter.submit(envelope(), AuthorizationResult(True), current_generation=1, participants=(WORKER_A,))

    first = adapter.next_batch(limit=1, now=100)[0]
    assert first.attempt == 1
    retry = adapter.nack(first.message_id, now=100, reason="temporary_failure")
    assert retry.status is TransportStatus.RETRY_WAIT
    assert adapter.next_batch(limit=1, now=109) == ()

    second = adapter.next_batch(limit=1, now=110)[0]
    assert second.attempt == 2
    terminal = adapter.nack(second.message_id, now=110, reason="temporary_failure")
    assert terminal.status is TransportStatus.NACKED
    assert adapter.pending_count == 0

    ack_adapter = NativeTransportAdapter(enabled=True)
    ack_adapter.submit(envelope(), AuthorizationResult(True), current_generation=1, participants=(WORKER_A,))
    intent = ack_adapter.next_batch(limit=1, now=1)[0]
    assert ack_adapter.ack(intent.message_id).status is TransportStatus.ACKED
    with pytest.raises(ValueError):
        ack_adapter.ack(intent.message_id)
