"""Removal contracts for the retired Olympus consulting workflow."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLYMPUS = ROOT / "src" / "olympus_v3"
RETIRED_MODULES = {
    "olympus_v3.consult_action": OLYMPUS / "consult_action.py",
    "olympus_v3.consulting_db": OLYMPUS / "consulting_db.py",
}


def test_retired_consult_modules_are_absent() -> None:
    for module_name, source_path in RETIRED_MODULES.items():
        assert importlib.util.find_spec(module_name) is None
        assert not source_path.exists()


def test_server_no_longer_claims_retired_consult_composition() -> None:
    server_source = (OLYMPUS / "server.py").read_text(encoding="utf-8")

    assert "consult_action.py" not in server_source
    assert "consulting_db" not in server_source
