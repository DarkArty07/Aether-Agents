"""Final executable retirement contract for the Olympus package and surfaces."""

from __future__ import annotations

import ast
import tomllib
from importlib.machinery import PathFinder
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED_PATHS = (
    ROOT / "src" / "olympus_v3",
    ROOT / "src" / "olympus.py",
    ROOT / "home" / "olympus_v3.yaml.template",
)
RETIRED_PROFILE_PLUGIN_DIRS = tuple(
    ROOT / "home" / "profiles" / profile / "plugins" / "olympus_v3"
    for profile in ("ariadna", "athena", "daedalus", "etalides", "hefesto", "ictinus")
)
FORBIDDEN_EXECUTABLE_IMPORTS = ("olympus_v3", "olympus")


def test_olympus_source_templates_and_profile_plugins_are_absent() -> None:
    remaining = [str(path.relative_to(ROOT)) for path in (*RETIRED_PATHS, *RETIRED_PROFILE_PLUGIN_DIRS) if path.exists()]
    assert remaining == []


def test_olympus_packages_are_not_importable() -> None:
    for module in FORBIDDEN_EXECUTABLE_IMPORTS:
        spec = PathFinder.find_spec(module, [str(ROOT / "src")])
        assert spec is None, module


def test_python_and_profile_config_have_no_executable_olympus_references() -> None:
    hits: list[str] = []
    roots = (ROOT / "scripts", ROOT / "home" / "profiles")
    for base in roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".sh", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8")
            if "olympus_v3" in text or "olympus-v3" in text or "olympus-mcp" in text:
                hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def test_distribution_identity_is_aether_only() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    assert project["name"] == "aether-agents"
    assert project["version"] == "0.22.0"
    scripts = project.get("scripts", {})
    assert all("olympus" not in name and "olympus" not in target for name, target in scripts.items())
    dependencies = project["dependencies"]
    retired = ("agent-client-protocol", "langgraph", "langchain-core")
    assert not any(dependency.startswith(retired) for dependency in dependencies)


def test_no_aether_source_imports_olympus() -> None:
    hits: list[str] = []
    for path in (ROOT / "src" / "aether_agents").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name == "olympus" or name.startswith("olympus_v3") for name in names):
                hits.append(f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}")
    assert hits == []
