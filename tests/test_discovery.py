import os
import pytest
import yaml
from pathlib import Path
from olympus.config import OlympusConfig, DaimonProfile
from olympus.discovery import discover_agents
import tempfile


def test_discover_agents_empty(tmp_path):
    config = OlympusConfig(
        aether_home=tmp_path,
        profiles_dir=tmp_path / "profiles",
        project_root=tmp_path.parent,
    )
    (tmp_path / "profiles").mkdir(exist_ok=True)
    agents = discover_agents(config)
    assert len(agents) == 0


def test_discover_agents_with_profile(tmp_path):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    hefesto_dir = profiles_dir / "hefesto"
    hefesto_dir.mkdir()
    config_data = {
        "agent": {
            "name": "hefesto",
            "role": "implementer",
            "description": "Code implementation Daimon",
        }
    }
    with open(hefesto_dir / "config.yaml", "w") as f:
        yaml.dump(config_data, f)
    
    config = OlympusConfig(
        aether_home=tmp_path,
        profiles_dir=profiles_dir,
        project_root=tmp_path.parent,
    )
    agents = discover_agents(config)
    assert "hefesto" in agents
    assert agents["hefesto"].role == "implementer"


def test_discover_agents_skips_non_agent_dirs(tmp_path):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    # Create a dir WITHOUT agent: field
    other_dir = profiles_dir / "other"
    other_dir.mkdir()
    with open(other_dir / "config.yaml", "w") as f:
        yaml.dump({"some_key": "some_value"}, f)
    
    config = OlympusConfig(
        aether_home=tmp_path,
        profiles_dir=profiles_dir,
        project_root=tmp_path.parent,
    )
    agents = discover_agents(config)
    assert len(agents) == 0


def test_discover_agents_skips_missing_config(tmp_path):
    """Directories without config.yaml should be skipped entirely."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    empty_dir = profiles_dir / "empty"
    empty_dir.mkdir()
    # No config.yaml in this directory
    
    config = OlympusConfig(
        aether_home=tmp_path,
        profiles_dir=profiles_dir,
        project_root=tmp_path.parent,
    )
    agents = discover_agents(config)
    assert len(agents) == 0


def test_discover_agents_missing_profiles_dir(tmp_path):
    """When profiles_dir does not exist, returns empty dict without error."""
    config = OlympusConfig(
        aether_home=tmp_path,
        profiles_dir=tmp_path / "nonexistent",
        project_root=tmp_path.parent,
    )
    agents = discover_agents(config)
    assert len(agents) == 0
