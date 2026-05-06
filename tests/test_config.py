import os
import pytest
from olympus.config import OlympusConfig, DaimonProfile, get_config, reset_config
from pathlib import Path


def test_daimon_profile_defaults():
    p = DaimonProfile(name="test", role="test", description="desc")
    assert p.launch_command == "hermes acp"
    assert p.keep_alive is True
    assert p.profile_path == Path()


def test_config_from_env(monkeypatch):
    reset_config()
    monkeypatch.setenv("AETHER_HOME", "/tmp/test_aether")
    config = OlympusConfig.from_env()
    assert config.aether_home == Path("/tmp/test_aether")
    assert config.project_root == Path("/tmp")
    assert config.profiles_dir == Path("/tmp/test_aether/profiles")
    reset_config()


def test_config_default_aether_home():
    reset_config()
    # Without AETHER_HOME env var, it resolves relative to the source file
    config = OlympusConfig.from_env()
    # Just verify it resolves to something
    assert config.aether_home is not None
    assert config.project_root == config.aether_home.parent
    reset_config()


def test_config_get_reset():
    """get_config() returns the same singleton; reset_config() clears it."""
    reset_config()
    c1 = get_config()
    c2 = get_config()
    assert c1 is c2  # same singleton
    reset_config()
    c3 = get_config()
    assert c3 is not c1  # new instance after reset
    reset_config()
