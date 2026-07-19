"""Public coordination protocol API."""

from .protocol import (
    MAX_METADATA_ITEMS,
    MAX_PARTS,
    MAX_PAYLOAD_BYTES,
    MAX_REFERENCE_LENGTH,
    MAX_REFERENCES,
    AuthorityClass,
    ChannelRoute,
    Envelope,
    MessagePart,
    MessageType,
    ParticipantCard,
    ParticipantRoute,
    Principal,
    RoleRoute,
    Route,
    ValidationError,
)
from .schema import PROTOCOL_SCHEMA, validate_wire

__all__ = [
    "AuthorityClass", "ChannelRoute", "Envelope", "MAX_METADATA_ITEMS", "MAX_PARTS", "MAX_PAYLOAD_BYTES",
    "MAX_REFERENCE_LENGTH", "MAX_REFERENCES", "MessagePart", "MessageType", "ParticipantCard", "ParticipantRoute",
    "Principal", "PROTOCOL_SCHEMA", "RoleRoute", "Route", "ValidationError", "validate_wire",
]
