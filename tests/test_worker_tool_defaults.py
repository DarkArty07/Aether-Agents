"""Portable worker tool selection: exclusions are native and credentials stay local."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "src/aether_agents/resources/profiles"


@pytest.mark.parametrize("role", ["implementer", "supervisor"])
def test_headless_worker_exclusions_preserve_scope(role: str) -> None:
    config = yaml.safe_load((PROFILES / role / "config.yaml").read_text())
    assert set(config["agent"]["disabled_toolsets"]) == {"computer_use", "clarify"}
    assert config["approvals"]["mode"] == "off"
    assert config["security"]["protected_instruction_files"] is False
    assert config["plugins"]["entries"]["aether-project-knowledge"]["settings"]["enabled"] is False
    assert "model" not in config
    assert "platform_toolsets" not in config  # Do not replace unrelated platform defaults.


@pytest.mark.parametrize("role", ["morfeo", "implementer", "supervisor"])
def test_roles_select_exa_without_shipping_credentials(role: str) -> None:
    config = yaml.safe_load((PROFILES / role / "config.yaml").read_text())
    assert config["web"] == {
        "backend": "exa",
        "search_backend": "exa",
        "extract_backend": "exa",
        "use_gateway": False,
    }
    assert "api_key" not in config["web"]
    if role == "morfeo":
        assert "disabled_toolsets" not in config.get("agent", {})


def test_tool_guide_explains_headless_scope_and_local_credentials() -> None:
    text = (ROOT / "docs/reference/plugins-and-tools.md").read_text()
    for term in ("agent.disabled_toolsets", "computer_use", "clarify", "EXA_API_KEY"):
        assert term in text
    assert "Existing profiles" in text
    assert "not a security sandbox" in text
