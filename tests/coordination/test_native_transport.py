from datetime import UTC, datetime

from olympus_v3.coordination import (
    AuthorityClass,
    Envelope,
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Lease,
    LedgerNativeTransport,
    MessagePart,
    MessageType,
    ParticipantCard,
    ParticipantRoute,
    Principal,
    Result,
    SQLiteLedger,
    StoreScope,
    TransportStatus,
    WriterContext,
)

PROJECT = "project-a"
SENDER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hefesto", "worker")
CARD = ParticipantCard(SENDER, "owner", "model-a", ("coordination",))


def envelope(message_id="message_12345678"):
    return Envelope(
        message_id,
        datetime(2026, 7, 20, 12, 0, tzinfo=UTC),
        SENDER,
        CARD,
        MessageType.REQUEST,
        AuthorityClass.REQUEST,
        PROJECT,
        "contract_12345678",
        1,
        "task_12345678",
        "correlation_12345678",
        None,
        (),
        (MessagePart("text", "work"),),
        ParticipantRoute(WORKER),
    )


def ledger_setup(tmp_path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"})
    db = SQLiteLedger(
        tmp_path / "coord.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key", key_id="integrity-a"),
        clock=lambda: 100,
    )
    writer_lease = db.acquire_lease("ledger", "writer-a", ttl=10_000).lease
    assert writer_lease is not None
    writer = WriterContext(scope, "writer-a", "key-a", "ledger", writer_lease.epoch, writer_lease.expires_at)
    outbox_lease = db.acquire_lease("outbox", "native-a", ttl=10_000).lease
    assert outbox_lease is not None
    return db, auth, writer, outbox_lease


def signed(db, auth, writer, value):
    payload = {"contract_id": value.contract_id, "envelope": value.to_dict()}
    return auth.sign(
        db.draft(value.message_id, "state.set", payload, writer=writer),
        writer,
    )


def test_native_transport_is_default_off_and_does_not_touch_ledger(tmp_path):
    db, auth, writer, lease = ledger_setup(tmp_path)
    value = envelope()
    adapter = LedgerNativeTransport(db, owner="native-a", lease=lease)

    receipt = adapter.stage(value, signed(db, auth, writer, value), writer)

    assert receipt.status is TransportStatus.REJECTED
    assert receipt.reason == "coordination_disabled"
    assert db.events() == []
    assert db.outbox() == []
    db.close()


def test_stage_is_atomic_deduplicated_and_claim_rehydrates_envelope(tmp_path):
    db, auth, writer, lease = ledger_setup(tmp_path)
    value = envelope()
    adapter = LedgerNativeTransport(db, owner="native-a", lease=lease, enabled=True)
    draft = signed(db, auth, writer, value)

    first = adapter.stage(value, draft, writer)
    duplicate = adapter.stage(value, draft, writer)
    claimed = adapter.claim(now=100)

    assert first.status is TransportStatus.QUEUED
    assert first.ledger_result is Result.APPLIED
    assert duplicate.reason == "duplicate_message"
    assert len(db.events()) == 1 and len(db.outbox()) == 1
    assert claimed[0].envelope == value
    assert claimed[0].attempt == 1
    db.close()


def test_ack_uses_existing_fenced_outbox_operation(tmp_path):
    db, auth, writer, lease = ledger_setup(tmp_path)
    value = envelope()
    adapter = LedgerNativeTransport(db, owner="native-a", lease=lease, enabled=True)
    adapter.stage(value, signed(db, auth, writer, value), writer)
    dispatch = adapter.claim(now=100)[0]

    receipt = adapter.ack(dispatch.message_id)

    assert receipt.status is TransportStatus.ACKED
    assert receipt.ledger_result is Result.TRANSPORT_ACKNOWLEDGED
    assert db.outbox()[0]["status"] == "SENT"
    db.close()


def test_nack_uses_existing_retry_and_poison_transitions(tmp_path):
    db, auth, writer, lease = ledger_setup(tmp_path)
    value = envelope()
    adapter = LedgerNativeTransport(db, owner="native-a", lease=lease, enabled=True, max_attempts=1)
    adapter.stage(value, signed(db, auth, writer, value), writer)
    dispatch = adapter.claim(now=100)[0]

    receipt = adapter.nack(dispatch.message_id, now=100, error="transport failure")

    assert receipt.status is TransportStatus.NACKED
    assert receipt.ledger_result is Result.POISON_TERMINATED
    assert db.outbox()[0]["status"] == "POISON"
    db.close()


def test_stage_rejects_unbound_payload_and_stale_outbox_lease(tmp_path):
    db, auth, writer, lease = ledger_setup(tmp_path)
    value = envelope()
    adapter = LedgerNativeTransport(db, owner="native-a", lease=lease, enabled=True)
    wrong = auth.sign(db.draft(value.message_id, "state.set", {"value": 3}, writer=writer), writer)

    receipt = adapter.stage(value, wrong, writer)
    assert receipt.status is TransportStatus.REJECTED
    assert receipt.reason == "envelope_binding_mismatch"
    assert db.events() == []

    adapter.stage(value, signed(db, auth, writer, value), writer)
    stale = Lease(lease.scope, lease.resource, lease.owner, lease.epoch, lease.expires_at, "stale-token")
    stale_adapter = LedgerNativeTransport(db, owner="native-a", lease=stale, enabled=True)
    assert stale_adapter.claim(now=100) == ()
    db.close()
