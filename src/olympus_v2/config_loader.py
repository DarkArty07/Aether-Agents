"""Olympus v2 Config Loader — reads Hermes config and builds per-agent Pi RPC spawn arguments.

Reads the `daimons:` section from AETHER_HOME/config.yaml to determine which agents
use the pi_rpc backend (vs. ACP). For each pi_rpc agent, builds the full spawn
command with resolved paths for system prompts, skills, extensions, and working directory.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("olympus_v2.config")

# Backend types
BACKEND_ACP = "acp"
BACKEND_PI_RPC = "pi_rpc"


@dataclass
class PiDaimonConfig:
    """Configuration for a single Daimon that uses the Pi RPC backend."""

    name: str
    role: str
    description: str
    backend: str = BACKEND_PI_RPC
    provider: str = ""
    model: str = ""
    thinking: str = "medium"
    tools: list[str] = field(default_factory=lambda: ["read", "write", "edit", "bash"])
    agent_dir: Path = Path()  # Resolved absolute path to the agent's directory
    skills_dir: Path | None = None
    extension_path: Path | None = None
    system_prompt_path: Path | None = None
    cwd: Path | None = None  # Working directory for the Pi process
    project_root: Path = Path()  # Derived from AETHER_HOME parent

    def build_spawn_args(self, session_dir: str | None = None) -> list[str]:
        """Build the full `pi` command arguments for spawning this agent in RPC mode.

        Args:
            session_dir: If provided, use --session-dir for persistent sessions
                (required for tool execution). If None, uses --no-session (ephemeral).
        
        Returns a list of command-line arguments suitable for subprocess.Popen.
        """
        args = [
            "pi",
            "--mode", "rpc",
        ]
        
        if session_dir:
            args.extend(["--session-dir", session_dir])
        else:
            args.append("--no-session")

        if self.thinking:
            args.extend(["--thinking", self.thinking])

        if self.system_prompt_path and self.system_prompt_path.exists():
            args.extend(["--system-prompt", str(self.system_prompt_path)])

        if self.skills_dir and self.skills_dir.exists():
            args.extend(["--skill", str(self.skills_dir)])

        if self.extension_path and self.extension_path.exists():
            args.extend(["--extension", str(self.extension_path)])

        if self.tools:
            args.extend(["--tools", ",".join(self.tools)])

        return args


@dataclass
class OlympusV2Config:
    """Top-level configuration for the Olympus v2 MCP server."""

    aether_home: Path
    project_root: Path
    poll_interval: int = 15
    daimons: dict[str, PiDaimonConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> OlympusV2Config:
        """Load configuration from environment variables and config files.

        Reads AETHER_HOME/config.yaml for the daimons: section and olympus_v2 settings.
        Falls back to sensible defaults if config is missing or malformed.
        """
        aether_home_env = os.environ.get("AETHER_HOME")
        if aether_home_env:
            aether_home = Path(aether_home_env)
        else:
            _here = Path(__file__).resolve()
            aether_home = _here.parent.parent.parent.parent / "home"

        project_root = aether_home.parent

        config_path = aether_home / "config.yaml"
        poll_interval = 15
        daimons: dict[str, PiDaimonConfig] = {}

        if config_path.exists():
            try:
                with open(config_path) as f:
                    cfg = yaml.safe_load(f) or {}
                if isinstance(cfg, dict):
                    # Read poll_interval from olympus section (shared with v1)
                    olympus_cfg = cfg.get("olympus", {})
                    if isinstance(olympus_cfg, dict):
                        poll_interval = int(olympus_cfg.get("poll_interval", 15))

                    # Read daimons section
                    daimons_cfg = cfg.get("daimons", {})
                    if isinstance(daimons_cfg, dict):
                        daimons = _parse_daimons(daimons_cfg, aether_home, project_root)
            except Exception as e:
                logger.warning(f"Error reading config from {config_path}: {e}")

        return cls(
            aether_home=aether_home,
            project_root=project_root,
            poll_interval=poll_interval,
            daimons=daimons,
        )


def _parse_daimons(
    daimons_cfg: dict[str, Any],
    aether_home: Path,
    project_root: Path,
) -> dict[str, PiDaimonConfig]:
    """Parse the daimons: section from config.yaml into PiDaimonConfig objects.

    Each entry looks like:
        daimons:
          hefesto:
            backend: pi_rpc
            provider: opencode-go
            model: deepseek-v4-flash
            thinking: medium
            tools: [read, write, edit, bash]

    The agent_dir is resolved relative to aether_home/profiles/{name} or
    aether_home/profiles/hermes/.pi-daimons/{name}/ depending on backend.
    """
    daimons: dict[str, PiDaimonConfig] = {}
    profiles_dir = aether_home / "profiles"

    for name, cfg in daimons_cfg.items():
        if not isinstance(cfg, dict):
            logger.warning(f"Skipping invalid daimon config for {name}: expected dict")
            continue

        backend = cfg.get("backend", BACKEND_ACP)

        # Only process pi_rpc backends; ACP agents are handled by Olympus v1
        if backend != BACKEND_PI_RPC:
            logger.debug(f"Skipping {name}: backend={backend} (not pi_rpc)")
            continue

        # Resolve agent_dir: pi_rpc agents live in .pi-daimons subdirectory
        # under the hermes profile, or directly under profiles/
        agent_dir_config = cfg.get("agent_dir")
        if agent_dir_config:
            agent_dir = Path(agent_dir_config)
            if not agent_dir.is_absolute():
                agent_dir = aether_home / agent_dir
        else:
            # Default: home/.pi-daimons/{name}/ (home-level, not profile-specific)
            agent_dir = aether_home / ".pi-daimons" / name

        # Resolve system prompt path
        system_prompt_path = agent_dir / ".pi" / "SYSTEM.md"

        # Resolve skills directory
        skills_dir_config = cfg.get("skills_dir")
        if skills_dir_config:
            skills_dir = Path(skills_dir_config)
            if not skills_dir.is_absolute():
                skills_dir = aether_home / skills_dir
        else:
            # Default: profiles/{name}/skills (the ACP agent's skills)
            skills_dir = profiles_dir / name / "skills"
            if not skills_dir.exists():
                # Fallback: no skills
                skills_dir = None

        # Resolve extension path
        extension_config = cfg.get("extension")
        if extension_config:
            extension_path = Path(extension_config)
            if not extension_path.is_absolute():
                extension_path = agent_dir / extension_config
        else:
            # Default: look for .pi/extensions/{name}.ts in agent_dir
            default_ext = agent_dir / ".pi" / "extensions" / f"{name}.ts"
            extension_path = default_ext if default_ext.exists() else None

        # Resolve working directory
        cwd_config = cfg.get("cwd")
        if cwd_config:
            cwd = Path(cwd_config)
            if not cwd.is_absolute():
                cwd = project_root / cwd_config
        else:
            cwd = agent_dir

        daimon = PiDaimonConfig(
            name=name,
            role=cfg.get("role", name),
            description=cfg.get("description", ""),
            backend=BACKEND_PI_RPC,
            provider=cfg.get("provider", ""),
            model=cfg.get("model", ""),
            thinking=cfg.get("thinking", "medium"),
            tools=cfg.get("tools", ["read", "write", "edit", "bash"]),
            agent_dir=agent_dir,
            skills_dir=skills_dir,
            extension_path=extension_path,
            system_prompt_path=system_prompt_path,
            cwd=cwd,
            project_root=project_root,
        )

        daimons[name] = daimon
        logger.info(
            f"Configured Pi Daimon: {name} "
            f"(provider={daimon.provider}, model={daimon.model}, "
            f"agent_dir={agent_dir})"
        )

    return daimons


# Global config singleton
_config: OlympusV2Config | None = None


def get_config() -> OlympusV2Config:
    """Get the global Olympus v2 configuration, loading it if necessary."""
    global _config
    if _config is None:
        _config = OlympusV2Config.from_env()
    return _config


def reset_config() -> None:
    """Reset configuration — mainly for testing."""
    global _config
    _config = None