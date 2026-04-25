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
    project_root: Path  # Resolved from AETHER_HOME — Daimons' working directory
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> OlympusConfig:
        """Load configuration from environment variables and defaults."""
        aether_home_env = os.environ.get("AETHER_HOME")
        if aether_home_env:
            aether_home = Path(aether_home_env)
        else:
            # Generic fallback: use "home" directory relative to the repo root
            # (src/olympus/../../home -> project_root/home)
            _here = Path(__file__).resolve()
            aether_home = _here.parent.parent.parent / "home"

        # Project root is always AETHER_HOME's parent directory.
        # This is where .eter/ lives and where Daimons should operate.
        project_root = aether_home.parent

        profiles_dir = aether_home / "profiles"
        log_dir = aether_home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            aether_home=aether_home,
            profiles_dir=profiles_dir,
            project_root=project_root,
            log_level=os.environ.get("OLYMPUS_LOG_LEVEL", "INFO"),
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