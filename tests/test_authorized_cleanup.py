from __future__ import annotations

from aether_agents import lab
from aether_agents.lab import resources, synthetic_owner, validation
from aether_agents.observation import privacy
from aether_agents.observation.capture.hermes_plugin import _Observer
from aether_agents.observation.reduce import review


def test_review_module_drops_the_superseded_since_reducer_export() -> None:
    assert review.__all__ == ["build_review_brief"]
    assert not hasattr(review, "apply_since")
    assert not hasattr(review, "CHANGE_CLASSES")


def test_lab_validation_drops_the_duplicate_scenario_validator() -> None:
    assert not hasattr(validation, "validate_scenario")
    assert lab.validate_scenario is synthetic_owner.validate_scenario


def test_lab_resources_drop_the_unused_schema_wrapper() -> None:
    assert not hasattr(resources, "schema_resource")
    assert resources.resource_bytes("schemas/scenario.schema.json") == lab.schema_bytes("scenario")


def test_observer_drops_the_unused_run_id_wrapper() -> None:
    assert not hasattr(_Observer, "_run_id")
    assert privacy.native_run_id(1) == 1
