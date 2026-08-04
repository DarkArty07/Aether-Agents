"""Aether-native authority boundary independent of Olympus lifecycle code."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NATIVE_ROOT = ROOT / "src" / "aether_agents"
LEGACY_SEMANTIC_MODULES = (
    "principal.py",
    "contracts.py",
    "budget.py",
    "evidence.py",
    "effects.py",
    "review.py",
    "closure.py",
)


def test_native_package_exposes_aether_owned_authority() -> None:
    native = importlib.import_module("aether_agents")

    assert {
        "Principal",
        "ExecutionContract",
        "BudgetState",
        "EvidenceReceipt",
        "Effect",
        "ReviewGate",
        "ClosureDecision",
    } <= set(native.__all__)


def test_native_sources_do_not_import_execution_substrates() -> None:
    assert NATIVE_ROOT.is_dir()
    forbidden: list[tuple[str, str]] = []
    for path in NATIVE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                names = []
            for name in names:
                if name == "olympus_v3" or name.startswith("olympus_v3.") or name == "orca" or name.startswith("orca."):
                    forbidden.append((str(path.relative_to(ROOT)), name))

    assert forbidden == []


def test_budget_history_requires_caller_owned_run_and_task_projection() -> None:
    budget = importlib.import_module("aether_agents.contracts.budget")
    events = [
        {
            "aggregate": "budget:run-a",
            "kind": "budget.reserved",
            "payload": {
                "run_id": "run-a",
                "contract_id": "contract-a",
                "command_id": "reserve-a",
                "reservation_id": "reservation-a",
                "amount": 4,
                "obligations": [],
            },
        }
    ]

    with pytest.raises(budget.BudgetTransitionError, match="run and task projection required"):
        budget.validate_budget_history(events, authorized=10)

    budget.validate_budget_history(
        events,
        authorized=10,
        runs={"run-a": "contract-a"},
        tasks={},
    )
    state, _, _ = budget.reduce_budget(events, 10)
    assert (state.available, state.reserved, state.committed, state.spent) == (6, 4, 0, 0)


def test_legacy_semantic_module_files_are_absent() -> None:
    legacy_root = ROOT / "src" / "olympus_v3" / "coordination"
    remaining = [name for name in LEGACY_SEMANTIC_MODULES if (legacy_root / name).exists()]

    assert remaining == []
