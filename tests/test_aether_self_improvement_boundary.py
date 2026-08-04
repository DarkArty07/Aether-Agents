"""Aether-native self-improvement boundary remains default-off and schema-compatible."""

from __future__ import annotations

import ast
import hashlib
import importlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OLD_PACKAGE = ROOT / "src/olympus_v3/self_improvement"
NATIVE_MODULES = (
    "causality",
    "evidence",
    "hooks",
    "ledger",
    "manifest",
    "promotion",
)
SELF_IMPROVEMENT_TESTS = (
    ROOT / "tests/test_self_improvement.py",
    ROOT / "tests/test_self_improvement_causality.py",
    ROOT / "tests/test_self_improvement_contract.py",
    ROOT / "tests/test_self_improvement_promotion.py",
)


def test_native_self_improvement_replaces_olympus_package_without_runtime_imports() -> None:
    package = importlib.import_module("aether_agents.self_improvement")
    modules = [importlib.import_module(f"aether_agents.self_improvement.{name}") for name in NATIVE_MODULES]

    assert package.__file__ is not None
    assert not OLD_PACKAGE.exists()
    for module in modules:
        assert module.__file__ is not None
        tree = ast.parse(Path(module.__file__).read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert not any(name.startswith("olympus_v3") for name in imported)


def test_self_improvement_ledger_schema_and_existing_bytes_are_preserved(tmp_path: Path) -> None:
    ledger_module = importlib.import_module("aether_agents.self_improvement.ledger")
    path = tmp_path / ".aether" / "self_improvement.db"
    original = ledger_module.SelfImprovementLedger(path)
    original.ensure_schema()
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    ledger_module.reset_schema_cache()
    reopened = ledger_module.SelfImprovementLedger(path)
    assert reopened.get_session("missing") is None
    after = hashlib.sha256(path.read_bytes()).hexdigest()

    assert ledger_module.SCHEMA_VERSION == 5
    assert after == before


def test_plugin_and_tests_target_native_package_while_plugin_remains_default_off() -> None:
    wrapper = ROOT / "home/plugins/aether-self-improvement/__init__.py"
    wrapper_content = wrapper.read_text()
    assert "from aether_agents.self_improvement.hooks import register" in wrapper_content
    assert "olympus_v3" not in wrapper_content

    for test_file in SELF_IMPROVEMENT_TESTS:
        assert "olympus_v3.self_improvement" not in test_file.read_text()

    config = yaml.safe_load((ROOT / "home/config.yaml.template").read_text())
    assert "aether-self-improvement" not in config.get("plugins", {}).get("enabled", [])
