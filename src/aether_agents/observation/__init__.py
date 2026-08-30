"""Aether Contract Observation — the local, metadata-only telemetry layer.

Normative design: ``specs/002-aether-contract-observation/spec.md`` (feature 002),
evidence in ``research.md``, schemas in ``contracts/``.

The layer is a read model plus Aether-owned contract metadata. It never activates
work, completes a task, changes a gate, approves an effect, alters credentials, or
overrides the owner (spec section 2), and it makes no outbound or non-loopback
network request (OBS-FR-028).
"""

from __future__ import annotations

__all__ = ["COLLECTOR_VERSION", "REDUCER_VERSION", "READ_MODEL_SCHEMA"]

from aether_agents.observation.contracts import (  # noqa: F401
    COLLECTOR_VERSION,
    READ_MODEL_SCHEMA,
    REDUCER_VERSION,
)
