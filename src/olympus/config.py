"""Olympus configuration — loads Aether ecosystem settings from environment and config files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DaimonProfile:
    """Represents a discovered Daimon from its profile config.yaml."""

    name: str
    role: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    launch_command: str = "hermes acp"
    keep_alive: bool = True
    profile_path: Path = Path()  # HERMES_HOME for this Daimon


@dataclass
class OlympusConfig:
    """Configuration for the Olympus MCP Server."""

    aether_home: Path
    profiles_dir: Path
    log_level: str = "INFO"
    log_file: Path | None = None
    session_timeout: int = 300  # seconds
    shutdown_timeout: int = 5  # seconds for graceful shutdown

    @classmethod
    def from_env(cls) -> OlympusConfig:
        """Load configuration from environment variables and defaults."""
        aether_home = Path(os.environ.get(
            "AETHER_HOME",
            "/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/home",
        ))
        profiles_dir = aether_home / "profiles"
        log_dir = aether_home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            aether_home=aether_home,
            profiles_dir=profiles_dir,
            log_level=os.environ.get("OLYMPUS_LOG_LEVEL", "INFO"),
            log_file=log_dir / "olympus.log",
        )


# Global config singleton — loaded once at startup
_config: OlympusConfig | None = None


def get_config() -> OlympusConfig:
    """Get the global Olympus configuration, loading it if necessary."""
    global _config
    if _config is None:
        _config = OlympusConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset configuration — mainly for testing."""
    global _config
    _config = None