"""Removal contract for post-Olympus installation and documentation residue."""

from __future__ import annotations

import re
import tomllib
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

PROFILE_TEMPLATES = tuple(sorted((ROOT / "home" / "profiles").glob("*/config.yaml.template")))
PROFILE_AETHER_PLUGINS = tuple(sorted((ROOT / "home" / "profiles").glob("*/plugins/aether")))

CURRENT_NATIVE_CORE_SURFACES = (
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs" / "guides" / "INSTALLATION.md",
    ROOT / "website" / "index.html",
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


def test_disconnected_aether_native_runtime_and_profile_plugins_are_absent() -> None:
    retired = (ROOT / "src" / "aether_agents", ROOT / "src" / "olympus_v3", *PROFILE_AETHER_PLUGINS)
    remaining = [str(path.relative_to(ROOT)) for path in retired if path.exists()]

    assert len(PROFILE_AETHER_PLUGINS) == 0
    assert remaining == []
    src_entries = {path.name for path in (ROOT / "src").iterdir()}
    assert "aether_mcp" in src_entries
    assert src_entries <= {"aether_mcp", "aether_mcp.egg-info"}


def test_profile_templates_do_not_enable_aether_continuity_plugin() -> None:
    assert len(PROFILE_TEMPLATES) == 6
    enabled = [
        str(path.relative_to(ROOT))
        for path in PROFILE_TEMPLATES
        if re.search(r"(?m)^\s*-\s+aether\s*$", path.read_text(encoding="utf-8"))
    ]

    assert enabled == []


def test_repository_contains_only_bounded_aether_mcp_distribution() -> None:
    pyproject_path = ROOT / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    text = pyproject_path.read_text(encoding="utf-8").lower()

    assert pyproject["build-system"] == {
        "requires": ["setuptools==83.0.0"],
        "build-backend": "setuptools.build_meta",
    }
    assert pyproject["project"] == {
        "name": "aether-mcp",
        "version": "0.22.0.dev0",
        "requires-python": ">=3.11",
        "dependencies": ["mcp==1.28.1"],
        "scripts": {"aether-mcp": "aether_mcp.__main__:main"},
    }
    assert pyproject["tool"]["setuptools"]["packages"]["find"] == {"where": ["src"]}
    assert "aiosqlite" not in text
    assert "cryptography" not in text
    assert "aether-agents" not in text
    assert "olympus" not in text
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "0.22.0"


def test_operations_and_ci_do_not_install_import_or_build_removed_runtime() -> None:
    surfaces = (
        ROOT / "scripts" / "setup.sh",
        ROOT / "scripts" / "update.sh",
        ROOT / "Makefile",
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
        ROOT / ".github" / "workflows" / "test.yml",
        ROOT / ".github" / "workflows" / "release.yml",
    )
    forbidden = (
        "aether_agents",
        "install_aether_agents",
        "reinstall_aether_agents",
        "pip install -e .",
        'pip install -e ".[dev]"',
        "python -m build",
        "ruff check src",
        "compileall -q src",
    )
    hits: list[str] = []
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}: {needle}")

    assert hits == []


def test_ci_installs_declared_aether_mcp_distribution_dependencies() -> None:
    workflows = (
        ROOT / ".github" / "workflows" / "test.yml",
        ROOT / ".github" / "workflows" / "release.yml",
    )

    missing_project_install = [
        str(path.relative_to(ROOT))
        for path in workflows
        if "pip install ." not in path.read_text(encoding="utf-8")
    ]

    assert missing_project_install == []


def test_product_assets_ci_accepts_exact_bounded_mcp_source() -> None:
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")

    assert "assert not (root / 'src').exists()" not in workflow
    for relative_path in (
        "aether_mcp/__init__.py",
        "aether_mcp/__main__.py",
        "aether_mcp/server.py",
    ):
        assert relative_path in workflow


def test_current_surfaces_do_not_advertise_removed_native_core() -> None:
    forbidden_claims = (
        "remain under `src/aether_agents`",
        "`aether_agents` owns product semantics",
        "**`aether_agents`** — product identity",
        "installs the `aether_agents` package",
        "native <code>aether_agents</code> package owns",
        "src/aether_agents/     ←",
    )
    hits: list[str] = []
    for path in CURRENT_NATIVE_CORE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for claim in forbidden_claims:
            if claim in text:
                hits.append(f"{path.relative_to(ROOT)}: {claim}")

    assert hits == []
