from __future__ import annotations

from pathlib import Path

import pytest

from olympus_v3.config_loader import CoordinationConfig, load_config


def _write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "olympus_v3.yaml"
    path.write_text(content)
    return path


def test_coordination_defaults_are_legacy_and_harmonia_is_disabled(tmp_path):
    config = load_config(tmp_path / "missing.yaml")

    assert config.coordination == CoordinationConfig(
        enabled=False,
        mode="legacy",
        allowed_modes=("legacy",),
        project_allowlist=(),
        max_active_runs=0,
    )


def test_coordination_parses_default_off_harmonia_capability(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    path = _write_config(
        tmp_path,
        "coordination:\n"
        "  enabled: true\n"
        "  mode: legacy\n"
        "  allowed_modes: [legacy, kernel-single-task]\n"
        f"  project_allowlist: [{root}]\n"
        "  max_active_runs: 1\n",
    )

    coordination = load_config(path).coordination

    assert coordination.enabled is True
    assert coordination.mode == "legacy"
    assert coordination.allowed_modes == ("legacy", "kernel-single-task")
    assert coordination.project_allowlist == (str(root.resolve()),)
    assert coordination.max_active_runs == 1


def test_explicit_v0190_shadow_config_remains_parseable_but_does_not_allow_harmonia(tmp_path):
    coordination = load_config(
        _write_config(tmp_path, "coordination:\n  enabled: true\n  mode: shadow\n")
    ).coordination

    assert coordination.enabled is True
    assert coordination.mode == "shadow"
    assert coordination.allowed_modes == ("legacy",)
    assert "kernel-single-task" not in coordination.allowed_modes
    assert coordination.max_active_runs == 0


@pytest.mark.parametrize(
    "content",
    [
        "coordination:\n  enabled: false\n  mode: active\n",
        "coordination:\n  enabled: false\n  mode: shadow\n  allowed_modes: [legacy, kernel-single-task]\n",
        "coordination:\n  enabled: false\n  allowed_modes: legacy\n",
        "coordination:\n  enabled: false\n  allowed_modes: [legacy, unknown]\n",
        "coordination:\n  enabled: false\n  allowed_modes: [legacy, legacy]\n",
        "coordination:\n  enabled: false\n  project_allowlist: /tmp\n",
        "coordination:\n  enabled: false\n  project_allowlist: [relative/path]\n",
        "coordination:\n  enabled: false\n  max_active_runs: 2\n",
        "coordination:\n  enabled: false\n  max_active_runs: true\n",
        "coordination:\n  enabled: false\n  unknown: value\n",
    ],
)
def test_malformed_harmonia_configuration_fails_closed(tmp_path, content):
    with pytest.raises(ValueError, match="coordination"):
        load_config(_write_config(tmp_path, content))
