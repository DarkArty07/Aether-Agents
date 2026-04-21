"""Olympus discovery — scans Daimon profiles from AETHER_HOME and builds agent registry."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from .config import DaimonProfile, OlympusConfig, get_config

logger = logging.getLogger("olympus.discovery")


def discover_agents(config: OlympusConfig | None = None) -> dict[str, DaimonProfile]:
    """Scan profiles directory for Daimon configs with agent: field.

    Returns a dict mapping agent name -> DaimonProfile.
    """
    if config is None:
        config = get_config()

    profiles_dir = config.profiles_dir
    agents: dict[str, DaimonProfile] = {}

    if not profiles_dir.exists():
        logger.warning(f"Profiles directory does not exist: {profiles_dir}")
        return agents

    for profile_dir in sorted(profiles_dir.iterdir()):
        if not profile_dir.is_dir():
            continue

        config_path = profile_dir / "config.yaml"
        # Also support config.yml
        if not config_path.exists():
            config_path = profile_dir / "config.yml"
        if not config_path.exists():
            logger.debug(f"No config.yaml in {profile_dir.name}, skipping")
            continue

        try:
            profile_data = _load_profile(config_path)
        except Exception as e:
            logger.error(f"Error loading {config_path}: {e}")
            continue

        agent_data = profile_data.get("agent")
        if not agent_data or not isinstance(agent_data, dict):
            logger.debug(f"No agent: field in {profile_dir.name}/config.yaml, skipping")
            continue

        name = agent_data.get("name", profile_dir.name)
        role = agent_data.get("role", "unknown")
        description = agent_data.get("description", "")
        capabilities = agent_data.get("capabilities", [])
        launch_command = agent_data.get("launch_command", "hermes acp")
        keep_alive = agent_data.get("keep_alive", True)

        profile = DaimonProfile(
            name=name,
            role=role,
            description=description,
            capabilities=capabilities,
            launch_command=launch_command,
            keep_alive=keep_alive,
            profile_path=profile_dir.resolve(),
        )
        agents[name] = profile
        logger.info(f"Discovered Daimon: {name} ({role}) — keep_alive={keep_alive}")

    return agents


def _load_profile(path: Path) -> dict:
    """Load a YAML config file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}