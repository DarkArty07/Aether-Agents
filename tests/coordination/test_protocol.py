import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from olympus_v3.coordination import (
    MAX_METADATA_BYTES,
    MAX_NESTING_DEPTH,
    MAX_PARTS,
    MAX_PAYLOAD_BYTES,
    AuthorityClass,
    ChannelRoute,
    Envelope,
    MessagePart,
    MessageType,
    ParticipantCard,
    ParticipantRoute,
    Principal,
    RoleRoute,
    ValidationError,
)

PROJECT = "project-a"
OWNER = "hermes"
ACTOR = "hefesto"
PRINCIPAL = Principal(PROJECT, OWNER, ACTOR)
CARD = ParticipantCard(PRINCIPAL, "developer", "model-a", ("python", "testing"))
STAMP = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def make_envelope(**changes):
    values = {
        "message_id": "msg_12345678",
        "timestamp": STAMP,
        "sender": PRINCIPAL,
        "sender_card": CARD,
        "message_type": MessageType.CONTEXT,
        "authority": AuthorityClass.INFORMATIONAL,
        "project_id": PROJECT,
        "contract_id": "contract_12345678",
        "generation": 0,
        "task_id": "task_12345678",
        "correlation_id": "corr_12345678",
        "reply_to": None,
        "references": ("ref_12345678",),
        "parts": (MessagePart("text", "hello"),),
        "route": ChannelRoute("coordination"),
    }
    values.update(changes)
    return Envelope(**values)


def test_public_protocol_types_build_immutable_project_scoped_identity():
    assert PRINCIPAL.project_id == PROJECT
    assert CARD.role == "developer"
    assert isinstance(CARD.skills, tuple)
    with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
        PRINCIPAL.actor_id = "other"


def test_principal_requires_separate_nonempty_normalized_owner_and_actor():
    with pytest.raises(ValidationError):
        Principal(" project-a ", " Hermes ", "hefesto")
    with pytest.raises(ValidationError):
        Principal(PROJECT, OWNER, OWNER)
    with pytest.raises(ValidationError):
        Principal(PROJECT, "", ACTOR)


def test_participant_card_rejects_project_identity_or_mutable_duplicate_metadata():
    with pytest.raises(ValidationError):
        ParticipantCard(PRINCIPAL, "developer", "model-a", ["python"])
    with pytest.raises(ValidationError):
        ParticipantCard(PRINCIPAL, "developer", "model-a", ("python", "python"))
    with pytest.raises(ValidationError):
        ParticipantCard(PRINCIPAL, "developer", "model-a", ("python",), metadata={"x": []})


def test_participant_card_metadata_is_deeply_immutable():
    card = ParticipantCard(PRINCIPAL, "developer", "model-a", ("python",), {"tier": "safe"})
    assert isinstance(card.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        card.metadata["tier"] = "unsafe"


def test_participant_card_accepts_real_model_and_qualified_skill_names():
    card = ParticipantCard(
        PRINCIPAL,
        "developer",
        "openai-codex/gpt-5.6-luna",
        ("software-development/test-driven-development",),
    )

    assert card.model == "openai-codex/gpt-5.6-luna"


def test_participant_card_metadata_has_aggregate_and_nesting_bounds():
    with pytest.raises(ValidationError):
        ParticipantCard(PRINCIPAL, "developer", "model-a", ("python",), {"note": "x" * MAX_METADATA_BYTES})

    nested = "leaf"
    for _ in range(MAX_NESTING_DEPTH + 1):
        nested = (nested,)
    with pytest.raises(ValidationError):
        ParticipantCard(PRINCIPAL, "developer", "model-a", ("python",), {"nested": nested})


def test_parts_keep_authority_separate_and_reject_unknown_or_malformed_payloads():
    part = MessagePart("json", {"answer": 1})
    assert part.payload == {"answer": 1}
    with pytest.raises(ValidationError):
        MessagePart("unknown", "x")
    with pytest.raises(ValidationError):
        MessagePart("json", {1: "not-json"})
    with pytest.raises(ValidationError):
        MessagePart("text", "x" * (MAX_PAYLOAD_BYTES + 1))


def test_envelope_happy_path_and_nested_immutability():
    envelope = make_envelope()
    assert envelope.route == ChannelRoute("coordination")
    assert isinstance(envelope.references, tuple)
    assert envelope.to_dict() == Envelope.from_dict(envelope.to_dict()).to_dict()
    with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
        envelope.generation = 2


def test_routes_require_exactly_one_valid_target():
    with pytest.raises(ValidationError):
        make_envelope(route=None)
    with pytest.raises(ValidationError):
        make_envelope(route=(ChannelRoute("a"), ParticipantRoute(PRINCIPAL)))
    with pytest.raises(ValidationError):
        ChannelRoute("")
    with pytest.raises(ValidationError):
        make_envelope(route=ParticipantRoute(Principal("other", OWNER, ACTOR)))
    with pytest.raises(ValidationError):
        RoleRoute(" ")


def test_envelope_rejects_sender_project_card_and_generation_mismatches():
    with pytest.raises(ValidationError):
        make_envelope(project_id="other")
    with pytest.raises(ValidationError):
        make_envelope(sender=Principal(PROJECT, OWNER, "other"))
    with pytest.raises(ValidationError):
        make_envelope(sender_card=ParticipantCard(Principal(PROJECT, OWNER, "other"), "reviewer", "model-a", ("python",)))
    with pytest.raises(ValidationError):
        make_envelope(generation=-1)


def test_envelope_rejects_malformed_ids_timestamp_correlation_and_references():
    for field in ("message_id", "contract_id", "correlation_id"):
        with pytest.raises(ValidationError):
            make_envelope(**{field: "bad"})
    with pytest.raises(ValidationError):
        make_envelope(timestamp=datetime.now())
    with pytest.raises(ValidationError):
        make_envelope(reply_to="reply_12345678", correlation_id=None)
    with pytest.raises(ValidationError):
        make_envelope(references=("ref_12345678", "ref_12345678"))


def test_envelope_accepts_normalized_uuid_style_ids_starting_with_a_digit():
    envelope = make_envelope(message_id="7b7b5f64-550a-4c4f-8888-0123456789ab")

    assert envelope.message_id.startswith("7")


def test_envelope_rejects_part_and_reference_count_bounds():
    with pytest.raises(ValidationError):
        make_envelope(parts=tuple(MessagePart("text", "x") for _ in range(MAX_PARTS + 1)))
    with pytest.raises(ValidationError):
        make_envelope(references=tuple(f"ref_{i:08d}" for i in range(33)))


def test_wire_round_trip_is_json_safe_and_strict_about_unknown_fields():
    wire = make_envelope().to_dict()
    assert isinstance(wire, dict)
    assert all(isinstance(value, (str, int, list, dict, type(None))) for value in wire.values())
    wire["unexpected"] = True
    with pytest.raises(ValidationError):
        Envelope.from_dict(wire)


def test_wire_input_rejects_authority_smuggling_and_malformed_routes():
    wire = make_envelope().to_dict()
    wire["parts"][0]["authority"] = "authorized_control"
    with pytest.raises(ValidationError):
        Envelope.from_dict(wire)
    wire = make_envelope().to_dict()
    wire["route"] = {"kind": "unknown", "channel": "coordination"}
    with pytest.raises(ValidationError):
        Envelope.from_dict(wire)
    wire = make_envelope().to_dict()
    wire["route"] = {"kind": ["channel"], "channel": "coordination"}
    with pytest.raises(ValidationError):
        Envelope.from_dict(wire)
    wire = make_envelope().to_dict()
    wire["route"] = {"channel": "coordination"}
    with pytest.raises(ValidationError):
        Envelope.from_dict(wire)


def test_schema_metadata_is_deterministic_and_machine_checkable():
    from olympus_v3.coordination.schema import PROTOCOL_SCHEMA, validate_wire

    first = json.dumps(PROTOCOL_SCHEMA, sort_keys=True, separators=(",", ":"))
    second = json.dumps(PROTOCOL_SCHEMA, sort_keys=True, separators=(",", ":"))
    assert first == second
    assert validate_wire(make_envelope().to_dict()) == ()
    assert validate_wire({"bad": True})
