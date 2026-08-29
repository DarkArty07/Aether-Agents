"""Parity tests for every active portable Aether project-marker reader."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from aether_agents.objective_contracts import ContractError, ObjectiveContractStore
from aether_agents.observation.context import ProjectRegistry, read_project_marker
from aether_agents.observation.query import ProjectResolutionError, resolve_project

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "aether_tui.py"
PROJECT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

_LOCAL_MARKER = f"""\
schema_version = 1
project_id = "{PROJECT_ID}"
name = "Marker fixture"
initialized_by = "1.0.0"
forge = "local"
contract_root = "specs"
default_branch = "main"
"""

_GITHUB_MARKER = f"""\
schema_version = 1
project_id = "{PROJECT_ID}"
name = "Marker fixture"
initialized_by = "1.0.0"
forge = "github"
contract_root = "specs"
default_branch = "main"

[github]
repository = "owner/repository"
"""

_INVALID_MARKERS = {
    "missing required field": _LOCAL_MARKER.replace('contract_root = "specs"\n', ""),
    "uppercase UUID": _LOCAL_MARKER.replace(PROJECT_ID, PROJECT_ID.upper()),
    "additional property": _LOCAL_MARKER + 'unexpected = "not allowed"\n',
    "github forge without github metadata": _LOCAL_MARKER.replace(
        'forge = "local"', 'forge = "github"'
    ),
    "local forge with github metadata": _LOCAL_MARKER
    + '\n[github]\nrepository = "owner/repository"\n',
    "wrong schema version": _LOCAL_MARKER.replace("schema_version = 1", "schema_version = 2"),
    "invalid name": _LOCAL_MARKER.replace('name = "Marker fixture"', 'name = "nested/name"'),
    "invalid initializer": _LOCAL_MARKER.replace(
        'initialized_by = "1.0.0"', 'initialized_by = "v1"'
    ),
    "invalid forge": _LOCAL_MARKER.replace('forge = "local"', 'forge = "gitlab"'),
    "wrong contract root": _LOCAL_MARKER.replace(
        'contract_root = "specs"', 'contract_root = "contracts"'
    ),
    "empty default branch": _LOCAL_MARKER.replace('default_branch = "main"', 'default_branch = ""'),
    "invalid github repository": _GITHUB_MARKER.replace(
        'repository = "owner/repository"', 'repository = "owner"'
    ),
    "additional github property": _GITHUB_MARKER + 'token = "not allowed"\n',
}


def _launcher_module():
    spec = importlib.util.spec_from_file_location("aether_tui_marker_validation", LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_marker(project: Path, marker: str) -> None:
    path = project / ".aether" / "project.toml"
    path.parent.mkdir(parents=True)
    path.write_text(marker, encoding="utf-8")


def _store_for(project: Path, tmp_path: Path) -> ObjectiveContractStore:
    subprocess.run(("git", "init", "-q"), cwd=project, check=True)
    registry = ProjectRegistry(root=tmp_path / "state")
    assert registry.register(PROJECT_ID, project, "marker-fixture")
    return ObjectiveContractStore(registry=registry)


@pytest.mark.parametrize("marker", (_LOCAL_MARKER, _GITHUB_MARKER), ids=("local", "github"))
def test_all_active_readers_accept_canonical_project_markers(tmp_path: Path, marker: str) -> None:
    project = tmp_path / "project"
    _write_marker(project, marker)
    store = _store_for(project, tmp_path)
    launcher = _launcher_module()

    parsed = read_project_marker(project)

    assert parsed is not None and parsed["project_id"] == PROJECT_ID
    assert resolve_project(explicit=project).project_id == PROJECT_ID
    assert launcher._portable_project_id(project) == PROJECT_ID
    assert (
        store.begin(project_id=PROJECT_ID, title="Marker parity", session_id="marker-session")[
            "project_id"
        ]
        == PROJECT_ID
    )


@pytest.mark.parametrize("marker", _INVALID_MARKERS.values(), ids=_INVALID_MARKERS)
def test_all_active_readers_reject_every_invalid_schema_marker(tmp_path: Path, marker: str) -> None:
    project = tmp_path / "project"
    _write_marker(project, marker)
    store = _store_for(project, tmp_path)
    launcher = _launcher_module()

    assert read_project_marker(project) is None
    with pytest.raises(ProjectResolutionError):
        resolve_project(explicit=project)
    with pytest.raises(launcher.ActivationError, match="project marker"):
        launcher._portable_project_id(project)
    with pytest.raises(ContractError, match="PROJECT-MARKER-INVALID"):
        store.begin(project_id=PROJECT_ID, title="Marker parity", session_id="marker-session")
