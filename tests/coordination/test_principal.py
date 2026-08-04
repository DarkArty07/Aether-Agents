"""Tests for the project-scoped identity retained from the v0.19 protocol lab."""

from dataclasses import FrozenInstanceError

import pytest

from aether_agents.identity import Principal, ValidationError

PROJECT = "project-a"
OWNER = "hermes"
ACTOR = "hefesto"


def test_principal_is_immutable_and_project_scoped() -> None:
    principal = Principal(PROJECT, OWNER, ACTOR)

    assert principal.to_dict() == {
        "project_id": PROJECT,
        "owner_id": OWNER,
        "actor_id": ACTOR,
    }
    with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
        setattr(principal, "actor_id", "other")


def test_principal_requires_normalized_separate_owner_and_actor() -> None:
    with pytest.raises(ValidationError):
        Principal(" project-a ", OWNER, ACTOR)
    with pytest.raises(ValidationError):
        Principal(PROJECT, OWNER, OWNER)
    with pytest.raises(ValidationError):
        Principal(PROJECT, "", ACTOR)


def test_principal_round_trip_rejects_unknown_fields() -> None:
    principal = Principal(PROJECT, OWNER, ACTOR)

    assert Principal.from_dict(principal.to_dict()) == principal
    with pytest.raises(ValidationError):
        Principal.from_dict({**principal.to_dict(), "authority": "smuggled"})
