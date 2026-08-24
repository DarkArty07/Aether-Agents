"""Single-wheel packaging and isolated manager/runtime qualification."""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCHEMA_NAMES = (
    "observation-event.schema.json",
    "observation-summary.schema.json",
    "observation-segment-manifest.schema.json",
)
PROFILE_NAMES = ("morfeo", "supervisor", "implementer")


def test_build_backend_is_exact_dev_only_and_locked() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

    assert project["build-system"]["requires"] == ["hatchling==1.27.0"]
    assert "hatchling==1.27.0" in project["dependency-groups"]["dev"]
    assert all("hatchling" not in requirement for requirement in project["project"]["dependencies"])

    packages = {package["name"]: package for package in lock["package"]}
    assert packages["hatchling"]["version"] == "1.27.0"
    locked_dev = packages["aether-agents"]["metadata"]["requires-dev"]["dev"]
    assert {item["name"]: item.get("specifier") for item in locked_dev}["hatchling"] == ("==1.27.0")


def test_packaging_isolation_uses_the_executing_interpreter_not_a_repo_virtualenv() -> None:
    source = Path(__file__).read_text(encoding="utf-8")

    assert "source_python = Path(sys.executable)" in source
    forbidden = "source_python = ROOT / " + '".venv"'
    assert forbidden not in source


@pytest.fixture(scope="module")
def built_distribution(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("aether-dist")
    subprocess.run(
        ["uv", "build", "--out-dir", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    [wheel] = output.glob("*.whl")
    [sdist] = output.glob("*.tar.gz")
    return wheel, sdist


def test_wheel_has_one_official_observer_entrypoint_and_all_profile_opt_ins(
    built_distribution: tuple[Path, Path],
) -> None:
    wheel, _ = built_distribution
    with zipfile.ZipFile(wheel) as archive:
        entry_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        )
        parser = configparser.ConfigParser()
        parser.read_string(archive.read(entry_name).decode("utf-8"))
        assert dict(parser["hermes_agent.plugins"]) == {
            "aether-contract-observer": "aether_agents.observation.capture.hermes_plugin"
        }
        for profile in PROFILE_NAMES:
            data = archive.read(f"aether_agents/resources/profiles/{profile}/config.yaml").decode(
                "utf-8"
            )
            assert data.splitlines() == [
                "plugins:",
                "  enabled:",
                "    - aether-contract-observer",
            ]
        assert not any("aether_observer" in name for name in archive.namelist())


def test_wheel_and_sdist_schemas_are_exact_normative_bytes(
    built_distribution: tuple[Path, Path],
) -> None:
    wheel, sdist = built_distribution
    with zipfile.ZipFile(wheel) as wheel_archive, tarfile.open(sdist, "r:gz") as source_archive:
        source_prefix = source_archive.getnames()[0].split("/", 1)[0]
        for name in SCHEMA_NAMES:
            normative = (
                ROOT / "specs" / "002-aether-contract-observation" / "contracts" / name
            ).read_bytes()
            wheel_bytes = wheel_archive.read(f"aether_agents/resources/schemas/{name}")
            member = source_archive.extractfile(
                f"{source_prefix}/specs/002-aether-contract-observation/contracts/{name}"
            )
            assert member is not None
            sdist_bytes = member.read()
            assert wheel_bytes == sdist_bytes == normative
            assert hashlib.sha256(wheel_bytes).digest() == hashlib.sha256(normative).digest()

        release_lock_name = "release-lock.schema.json"
        release_lock = (
            ROOT / "specs" / "001-aether-v1-productization" / "contracts" / release_lock_name
        ).read_bytes()
        wheel_release_lock = wheel_archive.read(
            f"aether_agents/resources/schemas/{release_lock_name}"
        )
        source_member = source_archive.extractfile(
            f"{source_prefix}/specs/001-aether-v1-productization/contracts/{release_lock_name}"
        )
        assert source_member is not None
        assert wheel_release_lock == source_member.read() == release_lock

        observer_lock_name = "observer-requirements.txt"
        observer_lock = (
            ROOT / "src" / "aether_agents" / "resources" / observer_lock_name
        ).read_bytes()
        wheel_observer_lock = wheel_archive.read(f"aether_agents/resources/{observer_lock_name}")
        source_observer_lock = source_archive.extractfile(
            f"{source_prefix}/src/aether_agents/resources/{observer_lock_name}"
        )
        assert source_observer_lock is not None
        assert wheel_observer_lock == source_observer_lock.read() == observer_lock


def test_packaged_observer_dependency_lock_matches_the_tracked_uv_lock() -> None:
    def logical_requirements(data: str) -> list[str]:
        result: list[str] = []
        pending = ""
        for row in data.splitlines():
            stripped = row.strip()
            if not stripped or stripped.startswith("#"):
                continue
            continued = stripped.endswith("\\")
            part = stripped[:-1].rstrip() if continued else stripped
            pending = f"{pending} {part}".strip()
            if not continued:
                result.append(pending)
                pending = ""
        assert not pending
        return result

    exported = subprocess.run(
        [
            "uv",
            "--no-config",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements.txt",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    packaged = (
        ROOT / "src" / "aether_agents" / "resources" / "observer-requirements.txt"
    ).read_text(encoding="ascii")

    assert logical_requirements(packaged) == logical_requirements(exported)


def _installed_fingerprint(python: Path) -> dict[str, object]:
    script = r"""
import hashlib, importlib, importlib.metadata, json
d = importlib.metadata.distribution('aether-agents')
rows = {}
for item in d.files or ():
    name = str(item)
    if not (name.startswith('aether_agents/') or name.endswith('.dist-info/entry_points.txt')):
        continue
    path = d.locate_file(item)
    if path.is_file():
        rows[name] = hashlib.sha256(path.read_bytes()).hexdigest()
eps = sorted(
    ep
    for ep in importlib.metadata.entry_points().select(group='hermes_agent.plugins')
    if ep.dist and ep.dist.metadata['Name'] == 'aether-agents'
)
if len(eps) != 1:
    raise RuntimeError('observer entry point is not unique')
observer = importlib.import_module('aether_agents.observation.capture.hermes_plugin')
loaded = eps[0].load()
package_root = d.locate_file('').resolve()
observer_path = __import__('pathlib').Path(observer.__file__).resolve()
print(json.dumps({
    'name': d.metadata['Name'],
    'version': d.version,
    'files': rows,
    'entrypoints': [(ep.name, ep.value) for ep in eps],
    'observer_module': observer.__name__,
    'observer_from_install': observer_path.is_relative_to(package_root),
    'entrypoint_loaded_observer': loaded is observer,
    'register_callable': callable(loaded.register),
}, sort_keys=True))
"""
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [str(python), "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=python.parent.parent,
        env=environment,
    )
    return json.loads(completed.stdout)


def test_same_wheel_installs_in_isolated_manager_and_runtime_without_path_shadowing(
    built_distribution: tuple[Path, Path], tmp_path: Path
) -> None:
    wheel, _ = built_distribution
    manager = tmp_path / "manager"
    runtime = tmp_path / "runtime"
    source_python = Path(sys.executable)
    for target in (manager, runtime):
        subprocess.run(
            ["uv", "venv", "--python", str(source_python), str(target)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    subprocess.run(
        ["uv", "pip", "install", "--python", str(manager / "bin" / "python"), str(wheel)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(runtime / "bin" / "python"),
            str(wheel),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for target in (manager, runtime):
        subprocess.run(
            ["uv", "pip", "check", "--python", str(target / "bin" / "python")],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

    manager_identity = _installed_fingerprint(manager / "bin" / "python")
    runtime_identity = _installed_fingerprint(runtime / "bin" / "python")
    assert manager_identity == runtime_identity
    assert manager_identity["name"] == "aether-agents"
    assert manager_identity["entrypoints"] == [
        ["aether-contract-observer", "aether_agents.observation.capture.hermes_plugin"]
    ]
    assert manager_identity["observer_module"] == (
        "aether_agents.observation.capture.hermes_plugin"
    )
    assert manager_identity["observer_from_install"] is True
    assert manager_identity["entrypoint_loaded_observer"] is True
    assert manager_identity["register_callable"] is True

    # Both wheel installs necessarily contain a console-script wrapper. Authority is
    # installation context: the public PATH selects the manager wrapper and never the
    # runtime-local copy (OBS-FR-076).
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(manager / "bin"), str(runtime / "bin"), env["PATH"]))
    selected = subprocess.run(
        ["sh", "-c", "command -v aether"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    assert Path(selected).resolve() == (manager / "bin" / "aether").resolve()

    broken = tmp_path / "broken-hermes"
    broken.mkdir()
    (broken / "hermes_cli.py").write_text(
        "raise RuntimeError('Hermes deliberately broken')\n", encoding="utf-8"
    )
    manager_env = env.copy()
    manager_env["PYTHONPATH"] = str(broken)
    version = subprocess.run(
        [str(manager / "bin" / "aether"), "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=manager_env,
    )
    assert version.stdout.strip().startswith("aether ")
    help_result = subprocess.run(
        [str(manager / "bin" / "aether"), "observe", "--help"],
        check=True,
        capture_output=True,
        text=True,
        env=manager_env,
    )
    assert "--since" in help_result.stdout and "--watch" in help_result.stdout

    # External provenance can name and hash the one wheel; that final digest is not
    # embedded inside its own metadata or package resources.
    wheel_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    with zipfile.ZipFile(wheel) as archive:
        uncompressed = b"".join(archive.read(name) for name in archive.namelist())
    assert wheel_digest.encode("ascii") not in uncompressed
