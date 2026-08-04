"""Removal contracts for the retired Harmonia public/runtime wrapper."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
from pathlib import Path

from olympus_v3 import config_loader, server

ROOT = Path(__file__).resolve().parents[1]
COORDINATION = ROOT / "src" / "olympus_v3" / "coordination"
RETIRED_MODULES = {
    "olympus_v3.coordination.harmonia_contract": COORDINATION / "harmonia_contract.py",
    "olympus_v3.coordination.harmonia_runtime": COORDINATION / "harmonia_runtime.py",
    "olympus_v3.coordination.harmonia_selection": COORDINATION / "harmonia_selection.py",
    "olympus_v3.coordination.harmonia_service": COORDINATION / "harmonia_service.py",
    "olympus_v3.coordination.harmonia_store": COORDINATION / "harmonia_store.py",
    "olympus_v3.coordination.selection_commit": COORDINATION / "selection_commit.py",
}


def test_harmonia_tool_is_absent_from_the_public_server() -> None:
    names = {
        tool.name
        for tool in asyncio.run(server.list_tools())  # type: ignore[arg-type,call-arg]
    }

    assert "harmonia" not in names


def test_retired_harmonia_modules_and_demo_are_absent() -> None:
    for module_name, source_path in RETIRED_MODULES.items():
        assert importlib.util.find_spec(module_name) is None
        assert not source_path.exists()
    assert not (ROOT / "scripts" / "run_harmonia_bounded_demo.py").exists()


def test_legacy_harmonia_configuration_is_absent() -> None:
    config = config_loader.load_config(ROOT / "does-not-exist.yaml")

    assert not hasattr(config_loader, "CoordinationConfig")
    assert not hasattr(config, "coordination")


def test_production_code_does_not_import_retired_harmonia_modules() -> None:
    retired_names = set(RETIRED_MODULES)
    importers: list[tuple[str, str]] = []
    for source_path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in retired_names:
                        importers.append((str(source_path.relative_to(ROOT)), alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module in retired_names:
                importers.append((str(source_path.relative_to(ROOT)), node.module))

    assert importers == []
