"""Deterministic stdlib-only wire-shape metadata and validation."""

from typing import Any

from .protocol import Envelope, ValidationError

PROTOCOL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message_id", "timestamp", "sender", "sender_card", "message_type", "authority", "project_id",
        "contract_id", "generation", "task_id", "correlation_id", "reply_to", "references", "parts", "route",
    ],
    "limits": {
        "max_payload_bytes": 16384,
        "max_metadata_bytes": 8192,
        "max_nesting_depth": 8,
        "max_parts": 32,
        "max_references": 32,
        "max_reference_length": 256,
    },
    "routes": ["channel", "participant", "role"],
    "parts": ["text", "json"],
}


def validate_wire(value: Any) -> tuple[str, ...]:
    """Return stable, redacted validation messages; never include payload data."""
    try:
        Envelope.from_dict(value)
    except ValidationError as exc:
        return (str(exc),)
    return ()


__all__ = ["PROTOCOL_SCHEMA", "validate_wire"]
