"""Removal contract for post-Olympus installation and documentation residue."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RETIRED_ACTIVE_PATHS = (
    ROOT / ".gitmodules",
    ROOT / ".graphify",
    ROOT / "honcho-server",
    ROOT / "docker-compose.yml",
    ROOT / "scripts" / "setup-honcho.sh",
    ROOT / "docs" / "honcho-setup.md",
    ROOT
    / "home"
    / "skills"
    / "autonomous-ai-agents"
    / "hermes-agent"
    / "references"
    / "honcho-integration.md",
)

CURRENT_PRODUCT_DOCS = (
    ROOT / "docs" / "product" / "README.md",
    ROOT / "docs" / "product" / "VISION.md",
    ROOT / "docs" / "product" / "MISSION.md",
    ROOT / "docs" / "product" / "OBJECTIVES.md",
    ROOT / "docs" / "product" / "SCOPE.md",
    ROOT / "docs" / "product" / "PRINCIPLES.md",
    ROOT / "docs" / "product" / "EXPERIENCE.md",
    ROOT / "docs" / "knowledge" / "AUTHORITY.md",
)


def test_retired_honcho_and_graphify_paths_are_absent() -> None:
    remaining = [str(path.relative_to(ROOT)) for path in RETIRED_ACTIVE_PATHS if path.exists()]
    assert remaining == []


def test_active_config_uses_builtin_memory_and_supported_placeholders() -> None:
    template = (ROOT / "home" / "config.yaml.template").read_text(encoding="utf-8")

    assert "provider: honcho" not in template
    assert "graphify:" not in template
    assert "graphify.serve" not in template

    placeholders = set(re.findall(r"__[A-Z0-9_]+__", template))
    assert placeholders <= {"__AETHER_ROOT__", "__HERMES_PYTHON__"}


def test_setup_and_makefile_have_no_retired_external_runtime_commands() -> None:
    setup = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "init_submodules" not in setup
    assert "git submodule" not in setup
    assert "setup-honcho" not in makefile
    assert "honcho-" not in makefile


def test_active_hermes_skill_does_not_advertise_retired_integrations() -> None:
    skill = (
        ROOT / "home" / "skills" / "autonomous-ai-agents" / "hermes-agent" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "mcp_servers.graphify" not in skill
    assert "graphify.serve" not in skill
    assert "provider: honcho" not in skill


def test_current_docs_do_not_assign_authority_to_retired_runtime() -> None:
    forbidden_claims = (
        "Olympus owns ACP lifecycle",
        "Olympus executes and owns",
        "Olympus should retain",
        "Olympus / ACPManager",
        "Olympus sessions and lifecycle facts",
        "Olympus lifecycle authority",
        "Harmonia and the coordination kernel manage",
        "Harmonia and the kernel own operational coordination",
    )
    hits: list[str] = []
    for path in CURRENT_PRODUCT_DOCS:
        text = path.read_text(encoding="utf-8")
        for claim in forbidden_claims:
            if claim in text:
                hits.append(f"{path.relative_to(ROOT)}: {claim}")

    assert hits == []


def test_current_entry_docs_do_not_advertise_removed_tools_or_services() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "guides" / "USER_PROFILE.md").read_text(encoding="utf-8")

    assert "make setup-honcho" not in readme
    assert "Graphify is the explicit exception" not in readme
    assert "uses [Honcho]" not in readme
    assert "Olympus v3" not in contributing
    assert "`aether_status`, `aether_update`, `aether_curate`" not in contributing
    assert "Current configuration and historical setup material still require" not in guide


def test_v019_multi_agent_model_is_explicitly_historical() -> None:
    model = (ROOT / "docs" / "knowledge" / "MULTI_AGENT_MODEL.md").read_text(encoding="utf-8")
    knowledge_index = (ROOT / "docs" / "knowledge" / "README.md").read_text(encoding="utf-8")

    assert "**Status:** HISTORICAL" in model
    assert "PDR-0011" in model
    assert "Historical v0.19" in knowledge_index


def test_current_documentation_indexes_do_not_plan_olympus_docs() -> None:
    index_paths = (
        ROOT / "docs" / "architecture" / "README.md",
        ROOT / "docs" / "reference" / "README.md",
        ROOT / "docs" / "contributing" / "README.md",
    )
    hits = [
        str(path.relative_to(ROOT))
        for path in index_paths
        if "OLYMPUS_" in path.read_text(encoding="utf-8")
    ]
    assert hits == []
