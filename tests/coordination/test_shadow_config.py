from pathlib import Path

import pytest

from olympus_v3.config_loader import load_config


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "olympus_v3.yaml"
    path.write_text(content)
    return path


def test_coordination_is_disabled_when_config_file_is_absent(tmp_path):
    config = load_config(tmp_path / "missing.yaml")

    assert config.coordination.enabled is False
    assert config.coordination.mode == "shadow"


def test_coordination_explicit_false_matches_absent_default(tmp_path):
    config = load_config(write_config(tmp_path, "coordination:\n  enabled: false\n  mode: shadow\n"))

    assert config.coordination.enabled is False
    assert config.coordination.mode == "shadow"


def test_coordination_explicit_true_only_parses_configuration(tmp_path):
    config = load_config(write_config(tmp_path, "coordination:\n  enabled: true\n  mode: shadow\n"))

    assert config.coordination.enabled is True
    assert config.coordination.mode == "shadow"


@pytest.mark.parametrize(
    "content",
    [
        "coordination: true\n",
        "coordination:\n  enabled: sometimes\n",
        "coordination:\n  enabled: false\n  mode: active\n",
        "coordination:\n  enabled: false\n  unknown: value\n",
    ],
)
def test_malformed_coordination_configuration_fails_closed(tmp_path, content):
    with pytest.raises(ValueError, match="coordination"):
        load_config(write_config(tmp_path, content))


def test_loading_configuration_does_not_import_shadow_runtime(tmp_path, monkeypatch):
    import builtins

    imported = []
    original_import = builtins.__import__

    def recording_import(name, *args, **kwargs):
        if name.endswith("coordination.shadow"):
            imported.append(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", recording_import)
    load_config(write_config(tmp_path, "coordination:\n  enabled: true\n  mode: shadow\n"))

    assert imported == []


def test_tracked_template_documents_default_off_coordination():
    template = Path("home/olympus_v3.yaml.template").read_text()

    assert "coordination:" in template
    assert "enabled: false" in template
    assert "mode: shadow" in template


def test_tracked_profile_templates_do_not_enable_coordination():
    for template in Path("home/profiles").glob("*/config.yaml.template"):
        text = template.read_text()
        assert "enabled: true" not in text or "coordination:" not in text
