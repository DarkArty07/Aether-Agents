"""Olympus v3 Config Loader — reads Hermes profile and v3 settings.

Simplified from v2: removes Pi Agent specific config (backend, .pi/ directories).
Reads Daimon profiles from hermes-agent profiles directory.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("olympus_v3.config")


@dataclass
class DaimonProfile:
    """Configuration for a single Daimon agent."""
    name: str
    profile_path: Path
    has_config: bool = False
    has_soul: bool = False

    @property
    def launch_command(self) -> list[str]:
        """Build the spawn command for this profile."""
        hermes_bin = (
            os.environ.get("HERMES_BIN")
            or os.path.expanduser("~/.local/bin/hermes")
            or "hermes"
        )
        return [hermes_bin, "acp", "--profile", self.name]


@dataclass
class OlympusV3Config:
    """Olympus v3 configuration."""
    profiles_dir: Path = field(default_factory=lambda: _default_profiles_dir())
    db_path: Path = field(default_factory=lambda: _default_db_path())
    poll_interval: int = 15
    stall_timeout: int = 45
    max_poll_iterations: int = 200
    aether_home: Path = field(default_factory=lambda: _default_aether_home())
    daimons: dict[str, DaimonProfile] = field(default_factory=dict)


def _default_aether_home() -> Path:
    """Resolve AETHER_HOME from env or default."""
    env = os.environ.get("AETHER_HOME")
    if env:
        return Path(env)
    return Path.cwd()


def _default_profiles_dir() -> Path:
    """Resolve profiles directory from HERMES_HOME or AETHER_HOME.
    
    Priority: HERMES_HOME parent > AETHER_HOME/profiles > ~/.hermes parent
    HERMES_HOME points to the profile dir itself (e.g., .../profiles/hermes),
    so its parent is the profiles directory.
    """
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home).parent
    aether_home = os.environ.get("AETHER_HOME")
    if aether_home:
        return Path(aether_home) / "profiles"
    return Path(os.path.expanduser("~/.hermes")).parent


def _default_db_path() -> Path:
    """Resolve database path from env, HERMES_HOME, or AETHER_HOME."""
    env = os.environ.get("OLYMPUS_DB_PATH")
    if env:
        return Path(env)
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home).parent / ".olympus" / "olympus_v3.db"
    aether_home = os.environ.get("AETHER_HOME")
    if aether_home:
        return Path(aether_home) / ".olympus" / "olympus_v3.db"
    return Path(os.path.expanduser("~/.hermes")).parent / ".olympus" / "olympus_v3.db"


def load_config(config_path: Path | None = None) -> OlympusV3Config:
    """Load Olympus v3 configuration.

    Reads from AETHER_HOME/olympus_v3.yaml if it exists,
    otherwise uses defaults from environment variables.
    """
    config = OlympusV3Config()

    # Try loading YAML config
    if config_path is None:
        config_path = config.aether_home / "olympus_v3.yaml"

    if config_path and config_path.exists():
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            if "poll_interval" in data:
                config.poll_interval = int(data["poll_interval"])
            if "stall_timeout" in data:
                config.stall_timeout = int(data["stall_timeout"])
            if "max_poll_iterations" in data:
                config.max_poll_iterations = int(data["max_poll_iterations"])
            if "db_path" in data:
                config.db_path = Path(data["db_path"])
            if "profiles_dir" in data:
                config.profiles_dir = Path(data["profiles_dir"])

            logger.info("Loaded config from %s", config_path)
        except Exception as e:
            logger.warning("Failed to load config from %s: %s", config_path, e)

    # Discover Daimon profiles
    if config.profiles_dir.exists():
        for profile_dir in sorted(config.profiles_dir.iterdir()):
            if not profile_dir.is_dir():
                continue
            config_path_in_profile = profile_dir / "config.yaml"
            soul_path = profile_dir / "SOUL.md"
            if not (config_path_in_profile.exists() or soul_path.exists()):
                continue

            profile = DaimonProfile(
                name=profile_dir.name,
                profile_path=profile_dir,
                has_config=config_path_in_profile.exists(),
                has_soul=soul_path.exists(),
            )
            config.daimons[profile.name] = profile

    logger.info("Discovered %d Daimon profiles in %s", len(config.daimons), config.profiles_dir)
    return config


# Module-level config singleton
_config: OlympusV3Config | None = None


def get_config() -> OlympusV3Config:
    """Get or create the module-level config singleton."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset config (useful for testing)."""
    global _config
    _config = None
