"""Collection side of Aether Contract Observation.

Only :mod:`aether_agents.observation.capture.hermes_plugin` is Hermes-facing. The
journal, flusher, and projectors stay Hermes-independent so the manager environment can
import them with no Hermes installed at all (OBS-FR-074).
"""

from __future__ import annotations
