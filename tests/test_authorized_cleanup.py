from __future__ import annotations

from aether_agents.observation import privacy
from aether_agents.observation.capture.hermes_plugin import _Observer
from aether_agents.observation.reduce import review


def test_review_module_drops_the_superseded_since_reducer_export() -> None:
    assert review.__all__ == ["build_review_brief"]
    assert not hasattr(review, "apply_since")
    assert not hasattr(review, "CHANGE_CLASSES")


def test_observer_drops_the_unused_run_id_wrapper() -> None:
    assert not hasattr(_Observer, "_run_id")
    assert privacy.native_run_id(1) == 1
