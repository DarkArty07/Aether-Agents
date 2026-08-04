"""Removal contract for the retired generic Olympus kernel lifecycle."""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_ROOT = ROOT / "src/olympus_v3/coordination"
RETIRED_KERNEL_FILES = (
    "__init__.py",
    "kernel_dispatcher.py",
    "kernel_runtime.py",
    "leases.py",
    "ledger.py",
    "olympus_adapter.py",
    "projections.py",
    "workflow.py",
)
RETIRED_KERNEL_TESTS = (
    "test_harmonia_admission.py",
    "test_harmonia_lease_lifecycle.py",
    "test_kernel_budget.py",
    "test_kernel_dispatcher.py",
    "test_kernel_fencing.py",
    "test_kernel_workflow.py",
    "test_kernel_workflow_security.py",
    "test_leases.py",
    "test_ledger.py",
    "test_ledger_atomicity.py",
    "test_ledger_authority.py",
    "test_ledger_contention.py",
    "test_ledger_input_hardening.py",
    "test_ledger_recovery.py",
    "test_ledger_transport_fencing.py",
    "test_legacy_experiment_retirement.py",
    "test_r11_closeout.py",
)


def test_generic_kernel_source_and_exclusive_tests_are_absent():
    source = [name for name in RETIRED_KERNEL_FILES if (KERNEL_ROOT / name).exists()]
    tests = [name for name in RETIRED_KERNEL_TESTS if (ROOT / "tests/coordination" / name).exists()]

    assert source == [], f"retired Olympus kernel files still shipped: {source}"
    assert tests == [], f"implementation-only kernel tests still shipped: {tests}"


def test_no_olympus_coordination_package_is_importable():
    assert importlib.util.find_spec("olympus_v3.coordination") is None


def test_no_active_source_or_script_imports_the_retired_kernel():
    importers = []
    for base in (ROOT / "src", ROOT / "scripts"):
        for path in base.rglob("*.py"):
            if KERNEL_ROOT in path.parents:
                continue
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    names = []
                if any(name == "olympus_v3.coordination" or name.startswith("olympus_v3.coordination.") for name in names):
                    importers.append(f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}")

    assert importers == [], f"active retired-kernel importers: {importers}"


def test_server_import_does_not_load_coordination_package():
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import olympus_v3.server; "
            "assert not any(name == 'olympus_v3.coordination' or "
            "name.startswith('olympus_v3.coordination.') for name in sys.modules)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
