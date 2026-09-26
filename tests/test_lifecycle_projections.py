"""Focused regressions for the Aether 1.0 local candidate route and XDG projections.

Every mutation targets ``tmp_path``: the disposable roots, the disposable board-free
profiles and a synthetic maintained-fork-shaped checkout.  The live installation, the
live state root and the user systemd manager are deliberately outside this surface; the
service seam is exercised through an explicit fake controller.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

import aether_agents.lifecycle as lifecycle
from aether_agents.lifecycle import (
    AETHER_GATEWAY_UNIT,
    MAINTAINED_FORK_BRANCH,
    MAINTAINED_FORK_REPOSITORY,
    DisabledServiceController,
    IntegrityError,
    LifecycleManager,
    ProjectionRoots,
    ReleaseRecord,
    ReleaseStore,
)
from aether_agents.observation.checkpoint import AuthorityContext
from aether_agents.paths import (
    applications_dir,
    data_root,
    state_root,
    systemd_user_dir,
    user_bin_dir,
)


class RecordingServiceController(DisabledServiceController):
    """Records every restart request without ever reaching a live user manager."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def available(self) -> bool:
        return True

    def restart(self, unit_name: str) -> str:
        self.calls.append(unit_name)
        return "restarted"


def _git(path: Path, *arguments: str) -> str:
    """Run one fixture Git command with no ambient repository binding inherited."""

    completed = subprocess.run(
        ["git", *arguments],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    )
    return completed.stdout.strip()


def _write_stub_reconciliation(
    checkout: Path, *, exit_code: int = 0, refusing: bool = False
) -> None:
    script = checkout / "scripts" / "validate_hermes_patch_reconciliation.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    summary = json.dumps(
        {
            "status": "current" if exit_code == 0 else "stale",
            "selected_source": {"present": 29, "partial": 0, "absent": 0, "unverified": 0},
            "records": 29,
            "refusing": (
                [
                    {
                        "id": "HLP-420",
                        "kind": "selected_source",
                        "detail": "Declared source path(s) missing at the selected revision.",
                    }
                ]
                if refusing
                else []
            ),
            "unverified": [],
        }
    )
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"print({summary!r})\n"
        + (
            'sys.stderr.write("reconciliation validation failed: stale evidence\\n")\n'
            if exit_code != 0
            else ""
        )
        + f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def _aether_candidate(
    root: Path,
    *,
    version: str = "1.0.0rc1",
    tag: str = "v1.0.0-rc.1",
    requires_python: str = ">=3.11,<3.14",
    remote: str = "https://github.com/DarkArty07/Aether-Agents",
    dirty: bool = False,
    create_tag: bool = True,
    stub_exit_code: int = 0,
    stub_refusing: bool = False,
) -> tuple[Path, str]:
    checkout = root / "aether-checkout"
    checkout.mkdir(parents=True)
    _git(checkout, "init", "-q", "-b", "main")
    _git(checkout, "config", "user.name", "Aether Test")
    _git(checkout, "config", "user.email", "aether@example.invalid")
    _git(checkout, "remote", "add", "origin", remote)
    (checkout / "VERSION").write_text(version + "\n", encoding="ascii")
    (checkout / "pyproject.toml").write_text(
        '[project]\nname = "aether-agents"\nversion = '
        f'"{version}"\nrequires-python = "{requires_python}"\n',
        encoding="utf-8",
    )
    _write_stub_reconciliation(checkout, exit_code=stub_exit_code, refusing=stub_refusing)
    _git(checkout, "add", "VERSION", "pyproject.toml", "scripts")
    _git(checkout, "commit", "-qm", "candidate")
    if create_tag:
        _git(checkout, "tag", "-a", tag, "-m", "candidate tag")
    if dirty:
        (checkout / "VERSION").write_text("9.9.9\n", encoding="ascii")
    return checkout, _git(checkout, "rev-parse", "HEAD")


def _fork_candidate(
    root: Path,
    *,
    version: str = "0.20.1",
    branch: str = MAINTAINED_FORK_BRANCH,
    remote: str = MAINTAINED_FORK_REPOSITORY,
    dirty: bool = False,
) -> tuple[Path, str]:
    checkout = root / "fork-checkout"
    checkout.mkdir(parents=True)
    _git(checkout, "init", "-q", "-b", branch)
    _git(checkout, "config", "user.name", "Aether Test")
    _git(checkout, "config", "user.email", "aether@example.invalid")
    _git(checkout, "remote", "add", "origin", remote)
    (checkout / "pyproject.toml").write_text(
        f'[project]\nname = "hermes-agent"\nversion = "{version}"\n'
        'requires-python = ">=3.11,<3.14"\n',
        encoding="utf-8",
    )
    (checkout / "agent").mkdir()
    (checkout / "agent" / "runtime_cwd.py").write_text("SOURCE = 1\n", encoding="utf-8")
    _git(checkout, "add", "pyproject.toml", "agent")
    _git(checkout, "commit", "-qm", "fork candidate")
    if dirty:
        (checkout / "agent" / "runtime_cwd.py").write_text("SOURCE = 2\n", encoding="utf-8")
    return checkout, _git(checkout, "rev-parse", "HEAD")


def _manager(
    root: Path,
    *,
    controller=None,
    project_root: Path | None = None,
) -> LifecycleManager:
    store = ReleaseStore(root / "data" / "aether", state_root=root / "state" / "aether")
    if project_root is None:
        project_root = root / "project"
        marker_dir = project_root / ".aether"
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / "project.toml").write_text(
            'project_id = "test-project-id"\n', encoding="utf-8"
        )
        from aether_agents.observation.context import ProjectRegistry

        registry = ProjectRegistry(store.state_root)
        registry.register("test-project-id", project_root, name="test-project")
    return LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        service_controller=controller or DisabledServiceController(),
        projections=ProjectionRoots.disposable(root / "operator-projections"),
        project_root=project_root,
    )


def _operator_destination_witnesses() -> dict[str, tuple[int, int, str | None]]:
    """Hash/mtime witnesses for the operator's real launcher, Desktop entry and unit."""

    witnessed: dict[str, tuple[int, int, str | None]] = {}
    candidate_paths = [
        Path(user_bin_dir()) / "aether",
        Path(applications_dir()) / "hermes.desktop",
        Path(applications_dir()) / "aether.desktop",
        Path(systemd_user_dir()) / AETHER_GATEWAY_UNIT,
    ]
    operator_wsl = lifecycle.detect_wsl_shortcuts_dir()
    if operator_wsl is not None:
        candidate_paths.extend(
            [
                operator_wsl / "Aether.cmd",
                operator_wsl / "Continue-Aether.cmd",
            ]
        )
    for path in candidate_paths:
        if not path.is_file():
            witnessed[str(path)] = (0, 0, None)
            continue
        info = path.stat()
        witnessed[str(path)] = (
            info.st_mtime_ns,
            info.st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return witnessed


def _aether_identity(version: str) -> dict[str, object]:
    return {
        "distribution": "aether-agents",
        "package_version": version,
        "git_tag": "v1.0.0-rc.1",
        "git_commit": "a" * 40,
        "python_requires": ">=3.11,<3.14",
        "observer": {
            "plugin_name": "aether-contract-observer",
            "group": "hermes_agent.plugins",
            "target": "aether_agents.observation.capture.hermes_plugin",
        },
    }


def _record(store: ReleaseStore, release_id: str = "1.0.0rc1-" + "a" * 16) -> ReleaseRecord:
    from aether_agents.lifecycle import AetherPrebuildIdentity

    version = release_id.split("-")[0]
    tui_bytes = b"console.log('mock-tui');\n"
    tui_hash = hashlib.sha256(tui_bytes).hexdigest()
    identity = _aether_identity(version)
    record = ReleaseRecord(
        schema_version=3,
        release_id=release_id,
        version=version,
        wheel_filename=f"aether_agents-{version}-py3-none-any.whl",
        wheel_sha256="a" * 64,
        hermes_tag=MAINTAINED_FORK_BRANCH,
        hermes_commit="b" * 40,
        observer_entry_point=(
            "aether-contract-observer=aether_agents.observation.capture.hermes_plugin"
        ),
        previous_release_id=None,
        authority_context=AuthorityContext.for_active_release(release_id).to_record(),
        aether_identity=identity,
        prebuild_identity=AetherPrebuildIdentity.from_record(identity).digest,
        installed_file_fingerprint="e" * 64,
        hermes_repository=MAINTAINED_FORK_REPOSITORY,
        hermes_branch=MAINTAINED_FORK_BRANCH,
        hermes_source_tree_sha256="c" * 64,
        tui_sha256=tui_hash,
    )
    record.validate()
    release = store.release_path(release_id)
    release.mkdir(parents=True, exist_ok=True)
    (release / "venv").symlink_to("runtime")
    tui_entry = release / "tui" / "dist" / "entry.js"
    tui_entry.parent.mkdir(parents=True, exist_ok=True)
    tui_entry.write_bytes(tui_bytes)
    return record


def _publish_record(manager: LifecycleManager, record: ReleaseRecord) -> None:
    """Publish one coherent record the store can read back privately."""

    from aether_agents.lifecycle import _atomic_json

    payload = {field: getattr(record, field) for field in record.__dataclass_fields__}
    _atomic_json(manager.store.release_path(record.release_id) / "record.json", payload)
    _atomic_json(manager.store.active_pointer, payload)


# --------------------------------------------------------------------------- preview


def test_local_candidate_preview_is_read_only_and_reports_exact_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    aether, aether_commit = _aether_candidate(tmp_path)
    fork, fork_commit = _fork_candidate(tmp_path)
    manager = _manager(tmp_path)
    before = sorted(path.name for path in manager.store.root.rglob("*"))

    candidate = manager.local_candidate(
        aether_checkout=aether,
        aether_commit=aether_commit,
        fork_checkout=fork,
        fork_commit=fork_commit,
    )

    record = candidate.to_record()
    assert record["mode"] == "local"
    assert record["aether"]["commit"] == aether_commit
    assert record["aether"]["tag"] == "v1.0.0-rc.1"
    assert record["aether"]["package_version"] == "1.0.0rc1"
    assert record["aether"]["display_version"] == "1.0.0-rc.1"
    assert record["fork"]["commit"] == fork_commit
    assert record["fork"]["branch"] == MAINTAINED_FORK_BRANCH
    assert record["fork"]["repository"] == MAINTAINED_FORK_REPOSITORY
    assert record["target"]["version"] == "1.0.0-rc.1"
    assert record["hlp_coverage"]["status"] == "current"
    assert record["artifacts"][0]["sha256"] == candidate.fork_source_tree_sha256
    # Nothing was staged, registered or activated by the preview.
    assert not manager.store.releases.exists()
    assert not manager.store.active_pointer.exists()
    assert before == sorted(path.name for path in manager.store.root.rglob("*"))


def test_local_candidate_refuses_dirty_or_mismatched_checkouts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    fork, fork_commit = _fork_candidate(tmp_path)

    dirty_aether, dirty_commit = _aether_candidate(tmp_path / "dirty", dirty=True)
    with pytest.raises(IntegrityError, match="dirty"):
        manager.local_candidate(
            aether_checkout=dirty_aether,
            aether_commit=dirty_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    clean_aether, clean_commit = _aether_candidate(tmp_path / "clean")
    with pytest.raises(IntegrityError, match="commit mismatch"):
        manager.local_candidate(
            aether_checkout=clean_aether,
            aether_commit="0" * 40,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    dirty_fork, dirty_fork_commit = _fork_candidate(tmp_path / "fork-dirty", dirty=True)
    with pytest.raises(IntegrityError, match="dirty"):
        manager.local_candidate(
            aether_checkout=clean_aether,
            aether_commit=clean_commit,
            fork_checkout=dirty_fork,
            fork_commit=dirty_fork_commit,
        )


def test_local_candidate_refuses_wrong_repository_branch_and_untagged_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    fork, fork_commit = _fork_candidate(tmp_path)

    foreign, foreign_commit = _aether_candidate(
        tmp_path / "foreign", remote="https://github.com/Example/other"
    )
    with pytest.raises(IntegrityError, match="origin is not the Aether repository"):
        manager.local_candidate(
            aether_checkout=foreign,
            aether_commit=foreign_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    untagged, untagged_commit = _aether_candidate(tmp_path / "untagged", create_tag=False)
    with pytest.raises(IntegrityError, match="annotated release tag"):
        manager.local_candidate(
            aether_checkout=untagged,
            aether_commit=untagged_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    mismatched, mismatched_commit = _aether_candidate(tmp_path / "mismatched", tag="v9.9.9")
    with pytest.raises(IntegrityError, match="does not match VERSION"):
        manager.local_candidate(
            aether_checkout=mismatched,
            aether_commit=mismatched_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    wrong_branch, wrong_branch_commit = _fork_candidate(tmp_path / "fork-branch", branch="main")
    aether, aether_commit = _aether_candidate(tmp_path / "aether-ok")
    with pytest.raises(IntegrityError, match="branch mismatch"):
        manager.local_candidate(
            aether_checkout=aether,
            aether_commit=aether_commit,
            fork_checkout=wrong_branch,
            fork_commit=wrong_branch_commit,
        )


def test_local_candidate_refuses_incompatible_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    fork, fork_commit = _fork_candidate(tmp_path)
    aether, aether_commit = _aether_candidate(
        tmp_path,
        requires_python=f"<{sys.version_info.major}.{sys.version_info.minor}",
    )

    with pytest.raises(IntegrityError, match="incompatible with the"):
        manager.local_candidate(
            aether_checkout=aether,
            aether_commit=aether_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )


def test_local_candidate_refuses_missing_or_unreconciled_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    fork, fork_commit = _fork_candidate(tmp_path)

    stale, stale_commit = _aether_candidate(tmp_path / "stale", stub_exit_code=2)
    with pytest.raises(IntegrityError, match="not current"):
        manager.local_candidate(
            aether_checkout=stale,
            aether_commit=stale_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    unreconciled, unreconciled_commit = _aether_candidate(
        tmp_path / "unreconciled", stub_refusing=True
    )
    with pytest.raises(IntegrityError, match="not present at the maintained-fork candidate"):
        manager.local_candidate(
            aether_checkout=unreconciled,
            aether_commit=unreconciled_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )


def test_cli_local_route_requires_the_complete_pinned_surface() -> None:
    from aether_agents.cli import _build_parser

    args = _build_parser().parse_args(
        ["update", "--local", "--aether-checkout", "/tmp/a", "--aether-commit", "a" * 40]
    )
    with pytest.raises(IntegrityError, match="--fork-checkout"):
        from aether_agents.cli import _local_candidate_arguments

        _local_candidate_arguments(args)

    conflicting = _build_parser().parse_args(
        [
            "update",
            "--local",
            "--wheel",
            "/tmp/w.whl",
            "--aether-checkout",
            "/tmp/a",
            "--aether-commit",
            "a" * 40,
            "--fork-checkout",
            "/tmp/f",
            "--fork-commit",
            "b" * 40,
        ]
    )
    with pytest.raises(IntegrityError, match="mutually exclusive"):
        from aether_agents.cli import _local_candidate_arguments

        _local_candidate_arguments(conflicting)


# ----------------------------------------------------------------------- projections


def test_projection_follows_the_selector_and_reports_coherence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _manager(tmp_path, controller=controller)
    record = _record(manager.store)
    _install_record(manager, record)
    _release_manager_python(manager.store, record)

    outcome = manager.project_release(record, restart_service=True)

    assert controller.calls == [AETHER_GATEWAY_UNIT]
    assert outcome["service_restart"] == "restarted"
    spec = manager.projection_spec(record)
    assert spec.runtime_current.is_symlink()
    assert spec.runtime_current.resolve() == spec.release
    assert spec.launcher_path.read_bytes() == spec.launcher_bytes
    assert os.access(spec.launcher_path, os.X_OK)
    assert spec.desktop_path.read_bytes() == spec.desktop_bytes
    assert spec.service_path.read_bytes() == spec.service_bytes
    assert str(spec.runtime_current) in spec.desktop_bytes.decode("utf-8")
    assert str(spec.runtime_current) in spec.service_bytes.decode("utf-8")
    # The selector hosts the same ``venv`` the project launcher and Desktop entry use.
    assert spec.runtime_current.resolve() / "venv" == spec.release / "venv"
    assert os.readlink(spec.release / "venv") == "runtime"
    assert manager.projection_status(record)["mismatches"] == []


def _write_stub_entry_point(runtime_root: Path) -> Path:
    """Install an echo stub where the launcher execs the selected release binary."""

    executable = runtime_root / "venv" / "bin" / "aether"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text(
        "#!/bin/sh\n"
        'printf "runtime_root=%s\\n" "${AETHER_RUNTIME_ROOT:-}"\n'
        'printf "hermes_root=%s\\n" "${AETHER_HERMES_ROOT:-}"\n'
        'printf "arguments=%s\\n" "$*"\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def test_projected_launcher_parses_and_forwards_arguments_to_the_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The projected entry point must be valid bash *and* reach the selected release.

    Content equality plus the executable bit would accept a ``chmod +x`` script that
    cannot run at all: the pre-``1.0.0rc1`` template closed the ``${VAR:-default}``
    quote *before* the brace, so ``bash -n`` rejected the projected launcher with exit 2
    while ``projection_status`` still compared bytes and called it coherent.  The
    projected bytes are therefore parsed and executed here, and the stub release behind
    ``runtime/current`` must receive both the operator arguments and the resolved roots.
    """

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    spec = manager.projection_spec(_record(manager.store))
    spec.launcher_path.parent.mkdir(parents=True, exist_ok=True)
    spec.launcher_path.write_bytes(spec.launcher_bytes)
    spec.launcher_path.chmod(0o755)

    data_home = tmp_path / "data"
    runtime_current = data_home / "aether" / "runtime" / "current"
    state_home = tmp_path / "state"
    _write_stub_entry_point(runtime_current)
    environment = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "XDG_DATA_HOME": str(data_home),
        "XDG_STATE_HOME": str(state_home),
    }
    # The default-resolution case must not inherit an operator override; the explicit
    # override below is set deliberately.
    environment.pop("AETHER_RUNTIME_ROOT", None)
    environment.pop("AETHER_HERMES_ROOT", None)

    parsed = subprocess.run(
        ["bash", "-n", str(spec.launcher_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert parsed.returncode == 0, parsed.stderr

    executed = subprocess.run(
        [str(spec.launcher_path), "update", "--local"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert executed.returncode == 0, executed.stderr
    assert executed.stdout.splitlines() == [
        f"runtime_root={runtime_current}",
        f"hermes_root={state_home / 'aether' / 'hermes'}",
        "arguments=update --local",
    ]

    # The ``:-`` default must stay overridable, which the pre-fix quoting also broke.
    override = tmp_path / "override"
    _write_stub_entry_point(override)
    overridden = subprocess.run(
        [str(spec.launcher_path), "--json"],
        env={**environment, "AETHER_RUNTIME_ROOT": str(override)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert overridden.returncode == 0, overridden.stderr
    assert overridden.stdout.splitlines() == [
        f"runtime_root={override}",
        f"hermes_root={state_home / 'aether' / 'hermes'}",
        "arguments=--json",
    ]


def test_doctor_reports_fail_closed_projection_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    store = manager.store
    record = _record(store)
    _publish_record(manager, record)
    _release_manager_python(store, record)
    manager.project_release(record, restart_service=False)

    spec = manager.projection_spec(record)
    (spec.release / "runtime").mkdir(parents=True, exist_ok=True)
    spec.launcher_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    spec.desktop_path.unlink()
    spec.runtime_current.unlink()
    other_release = store.release_path(record.release_id).parent / ("1.0.0rc1-" + "f" * 16)
    other_release.mkdir()
    spec.runtime_current.symlink_to(other_release)

    status = manager.projection_status(record)
    assert "launcher_projection_mismatch" in status["mismatches"]
    assert "desktop_projection_missing" in status["mismatches"]
    assert "runtime_pointer_mismatch" in status["mismatches"]


def test_projection_status_rejects_incoherent_hermes_refreshed_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor must not treat prefix/decoy/wrong-argv units as coherent selectors."""

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    record = _record(manager.store)
    _publish_record(manager, record)
    _release_manager_python(manager.store, record)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    runtime = str(spec.runtime_current)
    profile_home = str(manager.store.profile_home("morfeo"))
    python = f"{runtime}/venv/bin/python"
    exec_start = f"ExecStart={python} -m hermes_cli.main --profile morfeo gateway run"
    selector_tail = (
        f"WorkingDirectory={profile_home}\n"
        f'Environment="PATH={runtime}/venv/bin:/usr/bin"\n'
        f'Environment="VIRTUAL_ENV={runtime}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
        f'Environment="HERMES_TUI_DIR={runtime}/tui"\n'
        f"ExecStopPost=-{python} -m gateway.cgroup_cleanup\n"
    )

    coherent = (
        "[Unit]\n"
        "Description=Hermes Agent Gateway - Messaging Platform Integration\n"
        "[Service]\n"
        f"{exec_start}\n"
        f"{selector_tail}"
    ).encode()
    spec.service_path.write_bytes(coherent)
    assert "service_projection_mismatch" not in manager.projection_status(record)["mismatches"]

    for payload in (
        (
            f"ExecStart={python}-evil -m hermes_cli.main --profile morfeo gateway run\n"
            f"{selector_tail}"
        ).encode(),
        (
            f"# {exec_start}\n"
            f"# WorkingDirectory={profile_home}\n"
            f'# Environment="VIRTUAL_ENV={runtime}/venv"\n'
            f'# Environment="HERMES_HOME={profile_home}"\n'
            "ExecStart=/usr/bin/false\n"
            f"{selector_tail}"
        ).encode(),
        (
            f"ExecStart={python} -m evil_module --profile morfeo gateway run\n{selector_tail}"
        ).encode(),
    ):
        spec.service_path.write_bytes(payload)
        status = manager.projection_status(record)
        assert "service_projection_mismatch" in status["mismatches"], payload


def test_recovery_reprojects_a_partial_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    record = _record(manager.store)
    _publish_record(manager, record)
    _release_manager_python(manager.store, record)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    # Simulate a transition interrupted after the record was written but before the
    # selector followed it.
    spec.runtime_current.unlink()
    other = manager.store.releases / ("1.0.0rc1-" + "d" * 16)
    other.mkdir()
    spec.runtime_current.symlink_to(other)
    assert manager.projection_status(record)["mismatches"]

    result: dict[str, int] = {}
    manager._reconcile_projections_locked(result)

    assert result["projections_reconciled"] == 1
    assert manager.projection_status(record)["mismatches"] == []


def test_rollback_and_uninstall_preserve_user_state_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    store = manager.store
    observations = store.state_root / "observations" / "project"
    observations.mkdir(parents=True)
    payload = b"captured-before-update"
    (observations / "journal.bin").write_bytes(payload)
    before = hashlib.sha256((observations / "journal.bin").read_bytes()).hexdigest()

    record = _record(store)
    _install_record(manager, record)
    _release_manager_python(store, record)
    manager.project_release(record, restart_service=False)

    assert hashlib.sha256((observations / "journal.bin").read_bytes()).hexdigest() == before
    assert manager.preserved_state_report()["preserved"] == ["observations"]
    manager._deactivate_lifecycle_projections(record)

    assert hashlib.sha256((observations / "journal.bin").read_bytes()).hexdigest() == before
    assert (observations / "journal.bin").read_bytes() == payload
    spec = manager.projection_spec(record)
    assert not spec.runtime_current.exists()
    assert not spec.launcher_path.exists()
    assert not spec.desktop_path.exists()
    assert not spec.service_path.exists()


def test_deactivation_never_removes_foreign_projection_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    record = _record(manager.store)
    _install_record(manager, record)
    _release_manager_python(manager.store, record)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    spec.launcher_path.write_text("#!/bin/sh\n# owner-managed\n", encoding="utf-8")

    manager._deactivate_lifecycle_projections(record)

    assert spec.launcher_path.read_text(encoding="utf-8") == "#!/bin/sh\n# owner-managed\n"
    assert not spec.desktop_path.exists()


def test_deactivation_removes_selector_coherent_hermes_refreshed_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hermes-refreshed units that still select the release must be removable debris."""

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    record = _record(manager.store)
    _publish_record(manager, record)
    _release_manager_python(manager.store, record)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    runtime = str(spec.runtime_current)
    profile_home = str(manager.store.profile_home("morfeo"))
    python = f"{runtime}/venv/bin/python"
    exec_start = f"ExecStart={python} -m hermes_cli.main --profile morfeo gateway run"
    hermes_refreshed = (
        "[Unit]\n"
        "Description=Hermes Agent Gateway - Messaging Platform Integration\n"
        "[Service]\n"
        f"{exec_start}\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="PATH={runtime}/venv/bin:/usr/bin"\n'
        f'Environment="VIRTUAL_ENV={runtime}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
        f'Environment="HERMES_TUI_DIR={runtime}/tui"\n'
        f"ExecStopPost=-{python} -m gateway.cgroup_cleanup\n"
    ).encode()
    spec.service_path.write_bytes(hermes_refreshed)
    assert hermes_refreshed != spec.service_bytes
    assert "service_projection_mismatch" not in manager.projection_status(record)["mismatches"]

    manager._deactivate_lifecycle_projections(record)

    assert not spec.service_path.exists()
    assert not spec.launcher_path.exists()
    assert not spec.desktop_path.exists()
    assert not spec.runtime_current.exists()


def test_deactivation_preserves_incoherent_service_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Units that no longer select the release stay fail-closed (not deleted)."""

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _manager(tmp_path)
    record = _record(manager.store)
    _publish_record(manager, record)
    _release_manager_python(manager.store, record)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    runtime = str(spec.runtime_current)
    profile_home = str(manager.store.profile_home("morfeo"))
    incoherent = (
        f"ExecStart={runtime}/venv/bin/python -m evil_module --profile morfeo gateway run\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="VIRTUAL_ENV={runtime}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode()
    spec.service_path.write_bytes(incoherent)
    assert "service_projection_mismatch" in manager.projection_status(record)["mismatches"]

    manager._deactivate_lifecycle_projections(record)

    assert spec.service_path.read_bytes() == incoherent
    assert not spec.launcher_path.exists()
    assert not spec.desktop_path.exists()


# ------------------------------------------------- interruption, recovery, rollback


def test_tree_projection_encoding_is_the_documented_canonical_recipe(tmp_path: Path) -> None:
    """Pin the lock's tree recipe: materialized bytes, DFS row order, exclusions.

    The digest is ``sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=True))``
    over ``(posix-relative-path, sha256(file bytes))`` rows in ``os.walk`` DFS order with
    per-level sorted names, ``__pycache__`` excluded. It is deliberately not a Git blob
    projection (a ``.gitattributes`` line-ending rewrite changes the materialized bytes)
    and not a global path sort (the two orders differ for these trees), because the
    validator re-derives the lock value with exactly this recipe.
    """

    root = tmp_path / "source"
    (root / "agent").mkdir(parents=True)
    (root / "agent" / "z.py").write_bytes(b"subdirectory file\n")
    (root / "agentic.txt").write_bytes(b"top-level file\n")
    (root / "alpha.ps1").write_bytes(b"CRLF materialized\r\n")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "ignored.pyc").write_bytes(b"cache debris\n")

    rows = [
        ("agentic.txt", hashlib.sha256(b"top-level file\n").hexdigest()),
        ("alpha.ps1", hashlib.sha256(b"CRLF materialized\r\n").hexdigest()),
        ("agent/z.py", hashlib.sha256(b"subdirectory file\n").hexdigest()),
    ]
    expected = hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    sorted_variant = hashlib.sha256(
        json.dumps(sorted(rows), separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()

    assert lifecycle._tree_sha256(root) == expected
    assert sorted_variant != expected, "the DFS recipe must differ from a global path sort"

    link = root / "linked.txt"
    link.symlink_to(root / "agentic.txt")
    with pytest.raises(IntegrityError, match="non-regular file"):
        lifecycle._tree_sha256(root)
    link.unlink()

    assert lifecycle._tree_sha256(root) == expected


def _materialize_packaged_resources(package: Path) -> None:
    """Copy the normative bytes the release wheel force-includes as package resources.

    An installed release reads its observation schemas from ``resources/schemas``
    inside its own package.  A bare copy of the source tree does not carry them, so an
    emulated install has to reproduce the wheel's mapping instead of falling back to
    the checkout's ``specs/`` copy.
    """

    repo_root = Path(__file__).resolve().parents[1]
    build = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    mapping = build["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    for source, destination in mapping.items():
        if not destination.startswith("aether_agents/"):
            continue
        target = package.parent / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / source, target)


def _release_manager_python(store: ReleaseStore, record: ReleaseRecord) -> None:
    """Give one synthetic release the bundle and manager interpreter activation needs.

    The synthetic manager environment mirrors an installed release: its interpreter
    reaches the product package from inside the release tree, never from the invoking
    project directory, so the target's own code answers for the target.
    """

    release = store.release_path(record.release_id)
    release.mkdir(parents=True, exist_ok=True)
    venv = release / "venv"
    if not venv.is_symlink() and not venv.exists():
        venv.symlink_to("runtime")
    resources = Path(lifecycle.__file__).parent / "resources"
    for role in ("morfeo", "supervisor", "implementer"):
        profile = release / "profiles" / role
        profile.mkdir(parents=True, exist_ok=True)
        for name in ("config.yaml", "SOUL.md"):
            (profile / name).write_bytes((resources / "profiles" / role / name).read_bytes())
        for skill_name in lifecycle._CANONICAL_SKILLS:
            skill = profile / "skills" / skill_name / "SKILL.md"
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_bytes((resources / "skills" / skill_name / "SKILL.md").read_bytes())
    site_packages = release / "manager" / "site-packages"
    installed_package = site_packages / "aether_agents"
    if not installed_package.is_dir():
        shutil.copytree(Path(lifecycle.__file__).parent, installed_package)
    _materialize_packaged_resources(installed_package)
    python = release / "manager" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        f"import_root = {str(site_packages)!r}\n"
        "environment = dict(os.environ)\n"
        "environment['PYTHONPATH'] = import_root\n"
        "os.execvpe(sys.executable, [sys.executable, *sys.argv[1:]], environment)\n",
        encoding="utf-8",
    )
    python.chmod(0o700)


def _install_record(manager: LifecycleManager, record: ReleaseRecord) -> None:
    """Publish one release record without selecting it as the active release."""

    from aether_agents.lifecycle import _atomic_json

    payload = {field: getattr(record, field) for field in record.__dataclass_fields__}
    _atomic_json(manager.store.release_path(record.release_id) / "record.json", payload)


def _activation_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    controller=None,
    project_root=None,
) -> LifecycleManager:
    """One disposable manager authorized for synthetic transitions only."""

    manager = _manager(tmp_path, controller=controller, project_root=project_root)
    store = manager.store
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    monkeypatch.setattr(
        manager,
        "_assert_executing_active_manager_locked",
        lambda: store.active(),
    )
    return manager


def test_interrupted_service_projection_restores_and_recovers_the_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interruption at the selector/service projection stays recoverable after restart."""

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = _record(store, "1.0.0rc1-" + "a" * 16)
    target = _record(store, "1.0.0rc1-" + "b" * 16)
    _publish_record(manager, prior)
    _install_record(manager, target)
    _release_manager_python(store, prior)
    _release_manager_python(store, target)

    prior_projections = manager.project_release(prior, restart_service=False)
    assert prior_projections["runtime_current"]

    def _interrupt(spec) -> str:
        raise IntegrityError("simulated interruption at the service projection")

    monkeypatch.setattr(manager, "_restart_service", _interrupt)
    with pytest.raises(IntegrityError, match="service projection"):
        manager.activate_existing(
            target.release_id,
            transition_kind="update",
            expected_active_release_id=prior.release_id,
        )

    # The interruption never promoted the target and never restarted a service.
    restored = store.active()
    assert restored is not None
    assert restored.release_id == prior.release_id
    assert manager.projection_status(restored)["mismatches"] == []
    spec = manager.projection_spec(restored)
    assert spec.runtime_current.resolve() == store.release_path(prior.release_id)
    assert controller.calls == []
    assert manager.service_plan()["controller_available"] is True

    # A reopened manager reconciles the same durable state without a second transition.
    reopened = _activation_manager(tmp_path, monkeypatch, controller=controller)
    result = reopened.recover()
    reopened_active = reopened.store.active()
    assert reopened_active is not None
    assert reopened_active.release_id == prior.release_id
    assert reopened.projection_status(reopened_active)["mismatches"] == []
    assert result.get("projections_reconciled", 0) in {0, 1}


def test_local_preparation_interruption_publishes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interruption before candidate publication leaves no staging or release state."""

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _activation_manager(tmp_path, monkeypatch)
    store = manager.store
    prior = _record(store, "1.0.0rc1-" + "a" * 16)
    _publish_record(manager, prior)
    _release_manager_python(store, prior)
    manager.project_release(prior, restart_service=False)
    aether, aether_commit = _aether_candidate(tmp_path)
    fork, fork_commit = _fork_candidate(tmp_path)

    def _interrupt(*_args, **_kwargs):
        raise IntegrityError("simulated interruption before candidate publication")

    monkeypatch.setattr(manager, "_build_local_candidate", _interrupt)
    with pytest.raises(IntegrityError, match="before candidate publication"):
        manager.update_local(
            aether_checkout=aether,
            aether_commit=aether_commit,
            fork_checkout=fork,
            fork_commit=fork_commit,
        )

    active = store.active()
    assert active is not None
    assert active.release_id == prior.release_id
    staging = store.root / "staging"
    assert not staging.exists() or not list(staging.iterdir())
    assert sorted(path.name for path in store.releases.iterdir()) == [prior.release_id]
    assert not manager.projection_status(active)["mismatches"]


def test_local_update_preserves_mutable_state_bytes_and_rolls_back_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update and rollback move code/runtime/service only; mutable state keeps its bytes."""

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = _record(store, "1.0.0rc1-" + "a" * 16)
    target = _record(store, "1.0.0rc1-" + "b" * 16)
    _install_record(manager, prior)
    _install_record(manager, target)
    _release_manager_python(store, prior)
    _release_manager_python(store, target)

    manager.activate_existing(
        prior.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    mutable = {
        "observations/projects/p/journal/future.jsonl": b'{"schema_version":"v999"}\n',
        "hermes/profiles/morfeo/sessions.sqlite3": b"session-bytes-owned-by-the-user",
        "hermes/profiles/morfeo/memories/note.md": b"owner memory bytes\n",
        "monitor/state.json": b'{"paused":true}\n',
    }
    for relative, payload in mutable.items():
        path = store.state_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    before = {
        relative: hashlib.sha256((store.state_root / relative).read_bytes()).hexdigest()
        for relative in mutable
    }

    updated = manager.activate_existing(
        target.release_id,
        transition_kind="update",
        expected_active_release_id=prior.release_id,
    )
    assert updated.release_id == target.release_id
    assert controller.calls == [AETHER_GATEWAY_UNIT, AETHER_GATEWAY_UNIT]
    assert (store.root / "runtime" / "current").resolve() == store.release_path(target.release_id)

    rolled_back = manager.rollback()
    assert rolled_back.release_id == prior.release_id
    assert (store.root / "runtime" / "current").resolve() == store.release_path(prior.release_id)
    assert controller.calls == [AETHER_GATEWAY_UNIT] * 3

    restored = manager.activate_existing(
        target.release_id,
        transition_kind="update",
        expected_active_release_id=prior.release_id,
    )
    assert restored.release_id == target.release_id

    observed = {
        relative: hashlib.sha256((store.state_root / relative).read_bytes()).hexdigest()
        for relative in mutable
    }
    assert observed == before
    for relative, payload in mutable.items():
        assert (store.state_root / relative).read_bytes() == payload


# ------------------------------------------------------------------ isolation (#439)


def test_disposable_lane_cannot_reach_the_operator_unit_or_systemctl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative control: a disposable store owns no operator destination.

    This test runs with the ambient environment on purpose (no HOME/XDG redirection),
    so the witnesses below are the operator's real launcher, Desktop entry and user
    unit.  It reproduces the shape that produced #439 -- a disposable store with the
    default service seam -- and proves the lifecycle derives confined destinations and
    a disabled controller instead of writing the live unit.
    """

    witnesses = _operator_destination_witnesses()
    monkeypatch.setattr(
        lifecycle.SystemdUserController,
        "restart",
        lambda self, unit_name: pytest.fail("a disposable lane reached the user manager"),
    )

    store = ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether")
    proj = tmp_path / "project"
    (proj / ".aether").mkdir(parents=True, exist_ok=True)
    (proj / ".aether" / "project.toml").write_text('project_id = "test-p"\n', encoding="utf-8")
    from aether_agents.observation.context import ProjectRegistry

    ProjectRegistry(store.state_root).register("test-p", proj, name="test-p")
    manager = LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        project_root=proj,
    )
    record = _record(store)
    _publish_record(manager, record)
    _release_manager_python(store, record)

    assert manager.installed_environment is False
    assert isinstance(manager.service_controller, DisabledServiceController)

    spec = manager.projection_spec(record)
    assert spec.launcher_path.parent != Path(user_bin_dir())
    assert spec.desktop_path.parent != Path(applications_dir())
    assert spec.service_path.parent != Path(systemd_user_dir())
    for destination in (spec.launcher_path, spec.desktop_path, spec.service_path):
        assert tmp_path in destination.parents

    outcome = manager.project_release(record, restart_service=True)
    assert outcome["service_restart"] == "disabled_non_installed_environment"
    assert manager.service_plan()["controller_available"] is False
    assert manager.projection_status(record)["mismatches"] == []
    manager._reconcile_projections_locked({})
    manager._deactivate_lifecycle_projections(record)

    assert not spec.launcher_path.exists()
    assert not spec.desktop_path.exists()
    assert not spec.service_path.exists()
    assert _operator_destination_witnesses() == witnesses


def test_installed_environment_is_the_only_operator_projection_owner() -> None:
    """The ambient installation keeps the real destinations and the systemd seam."""

    ambient_data = Path.home() / ".local" / "share" / "aether"
    ambient_state = Path.home() / ".local" / "state" / "aether"
    installed = LifecycleManager(
        store=ReleaseStore(ambient_data, state_root=ambient_state),
        python_executable=Path(sys.executable),
    )
    ambient = ambient_data == data_root() and ambient_state == state_root()

    assert installed.installed_environment is ambient
    if ambient:
        assert isinstance(installed.service_controller, lifecycle.SystemdUserController)
        assert installed.projection_roots() == ProjectionRoots.operator()
        assert installed.disabled_service_reason is None
    else:
        assert isinstance(installed.service_controller, DisabledServiceController)
        assert installed.disabled_service_reason == "disabled_non_installed_environment"


def _load_frozen_rc3_release_record():
    """Load the authentic frozen rc3 ReleaseRecord from commit d8ff984c."""
    rc3_code = subprocess.check_output(
        [
            "git",
            "show",
            "d8ff984c67bfc147ac9c83cf8a34a72edc27c8df:src/aether_agents/lifecycle.py",
        ],
        text=True,
    )
    import importlib.util
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        mod_path = Path(td) / "rc3_lifecycle.py"
        mod_path.write_text(rc3_code, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("rc3_lifecycle", str(mod_path))
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules["rc3_lifecycle"] = mod
        spec.loader.exec_module(mod)
        return mod.ReleaseRecord, mod.IntegrityError


def test_target_compatible_active_record_preserves_target_field_shape_and_reader_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oracle (a): target record owns field shape; absence vs null preserved; rc3 reader proves compatibility."""
    rc3_ReleaseRecord, rc3_IntegrityError = _load_frozen_rc3_release_record()

    store = ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether")
    store._ensure_owned_root()
    release_id = "1.0.0rc3-3333333333333333"
    rel_path = store.release_path(release_id)
    rel_path.mkdir(parents=True, exist_ok=True)

    # rc3 payload does NOT have tui_sha256; prebuild_identity is absent
    rc3_target_payload = {
        "schema_version": 2,
        "release_id": release_id,
        "version": "1.0.0rc3",
        "wheel_filename": "aether_agents-1.0.0rc3-py3-none-any.whl",
        "wheel_sha256": "3" * 64,
        "hermes_tag": "v2026.8.18",
        "hermes_commit": "a" * 40,
        "observer_entry_point": "aether-contract-observer=aether_agents.observation.capture.hermes_plugin",
        "previous_release_id": None,
        "authority_context": AuthorityContext.for_active_release(release_id).to_record(),
        "observation_compatibility": {
            "event_write_version": "aether.observation.event.v1",
            "event_read_versions": ["aether.observation.event.v1"],
            "summary_write_version": "aether.observation.summary.v1",
            "summary_read_versions": ["aether.observation.summary.v1"],
            "segment_manifest_write_version": "aether.observation.segment-manifest.v1",
            "segment_manifest_read_versions": ["aether.observation.segment-manifest.v1"],
            "projection_schema_version": "aether.observation.projection.v1",
        },
        "observer": {
            "plugin_name": "aether-contract-observer",
            "group": "hermes_agent.plugins",
            "target": "aether_agents.observation.capture.hermes_plugin",
        },
        "hermes_repository": "https://github.com/DarkArty07/aether-hermes",
        "hermes_branch": "aether-main",
        "hermes_source_tree_sha256": "c" * 64,
    }
    # Write immutable target record.json
    (rel_path / "record.json").write_text(
        json.dumps(rc3_target_payload, indent=2), encoding="utf-8"
    )

    # Parse record using current ReleaseRecord
    current_record = ReleaseRecord.from_json(rc3_target_payload)
    assert current_record.tui_sha256 is None

    # Commit as active with predecessor "1.0.0rc2-2222222222222222"
    predecessor_id = "1.0.0rc2-2222222222222222"
    current_record_with_pred = replace(current_record, previous_release_id=predecessor_id)
    store._commit_active(current_record_with_pred)

    # Read the actual persisted bytes in active_pointer
    active_text = store.active_pointer.read_text(encoding="utf-8")
    active_json = json.loads(active_text)

    # 1. tui_sha256 MUST NOT be in active_json
    assert "tui_sha256" not in active_json
    # 2. prebuild_identity was absent in target record, MUST remain absent
    assert "prebuild_identity" not in active_json
    # 3. previous_release_id updated to actual predecessor
    assert active_json["previous_release_id"] == predecessor_id

    # 4. Proved through the frozen rc3 reader path:
    rc3_read = rc3_ReleaseRecord.from_json(active_json)
    assert rc3_read.release_id == release_id
    assert rc3_read.previous_release_id == predecessor_id

    # 5. Proof of defect (RED/GREEN): if tui_sha256 is added (even as null), rc3 reader rejects it
    defective_payload = dict(active_json)
    defective_payload["tui_sha256"] = None
    with pytest.raises(rc3_IntegrityError, match="malformed active release record"):
        rc3_ReleaseRecord.from_json(defective_payload)


def test_transition_compensation_restores_byte_exact_previous_record_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oracle (b): compensation restores byte-exact previous active-record bytes (hash-compared)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = _record(store, "1.0.0rc1-" + "a" * 16)
    target = _record(store, "1.0.0rc1-" + "b" * 16)
    _install_record(manager, prior)
    _install_record(manager, target)
    _release_manager_python(store, prior)
    _release_manager_python(store, target)

    manager.activate_existing(
        prior.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )
    before_bytes = store.active_pointer.read_bytes()
    before_sha256 = hashlib.sha256(before_bytes).hexdigest()
    before_symlink = os.readlink(store.root / "runtime" / "current")

    def _fail_restart(*_args, **_kwargs):
        raise IntegrityError("simulated restart failure triggering compensation")

    monkeypatch.setattr(manager, "_restart_service", _fail_restart)

    with pytest.raises(IntegrityError, match="simulated restart failure"):
        manager.activate_existing(
            target.release_id,
            transition_kind="update",
            expected_active_release_id=prior.release_id,
        )

    after_bytes = store.active_pointer.read_bytes()
    after_sha256 = hashlib.sha256(after_bytes).hexdigest()
    assert after_sha256 == before_sha256
    assert after_bytes == before_bytes
    assert os.readlink(store.root / "runtime" / "current") == before_symlink


def test_incompatible_or_malformed_target_refuses_with_zero_byte_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oracle (c): incompatible target refuses before cutover with 0 byte change to record, selector, projections, unit."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = _record(store, "1.0.0rc1-" + "a" * 16)
    _install_record(manager, prior)
    _release_manager_python(store, prior)

    manager.activate_existing(
        prior.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    spec = manager.projection_spec(prior)
    witnessed_paths = [
        store.active_pointer,
        store.root / "runtime" / "current",
        spec.launcher_path,
        spec.desktop_path,
        spec.service_path,
    ]
    before_hashes = {
        p: (
            hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() and not p.is_symlink()
            else (os.readlink(p) if p.is_symlink() else None)
        )
        for p in witnessed_paths
    }

    # Case 1: Target has unknown keys in record.json
    bad_target = _record(store, "1.0.0rc1-" + "c" * 16)
    _install_record(manager, bad_target)
    _release_manager_python(store, bad_target)
    bad_record_path = store.release_path(bad_target.release_id) / "record.json"
    bad_payload = json.loads(bad_record_path.read_text(encoding="utf-8"))
    bad_payload["unknown_future_field_not_in_schema"] = "disallowed"
    bad_record_path.write_text(json.dumps(bad_payload), encoding="utf-8")

    with pytest.raises(IntegrityError):
        manager.activate_existing(
            bad_target.release_id,
            transition_kind="update",
            expected_active_release_id=prior.release_id,
        )

    after_hashes = {
        p: (
            hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() and not p.is_symlink()
            else (os.readlink(p) if p.is_symlink() else None)
        )
        for p in witnessed_paths
    }
    assert after_hashes == before_hashes


def test_reconcile_to_active_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Oracle (d): reconcile --to active --dry-run is non-mutating; --yes reconciles only already-active release."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    active_rec = _record(store, "1.0.0rc1-" + "a" * 16)
    _install_record(manager, active_rec)
    _release_manager_python(store, active_rec)

    manager.activate_existing(
        active_rec.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    spec = manager.projection_spec(active_rec)
    spec.desktop_path.write_text("tampered desktop file\n", encoding="utf-8")
    assert manager.projection_status(active_rec)["mismatches"] != []

    desktop_before = spec.desktop_path.read_bytes()

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)
    monkeypatch.setattr(manager, "executing_active_manager", lambda: active_rec)

    # 1. Unsupported modes refuse with code 3
    assert cli_main(["reconcile", "--to", "installed", "--json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "unsupported"

    assert cli_main(["reconcile", "--json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "unsupported"

    # 2. Dry run preview is non-mutating: byte-identical before and after
    assert cli_main(["reconcile", "--to", "active", "--dry-run", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "planned"
    assert "desktop_projection_mismatch" in out["data"]["mismatches"]
    assert spec.desktop_path.read_bytes() == desktop_before

    # 3. Apply with --yes
    assert cli_main(["reconcile", "--to", "active", "--yes", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "changed"
    assert out["changed"] is True
    assert manager.projection_status(active_rec)["mismatches"] == []
    assert spec.desktop_path.read_bytes() == spec.desktop_bytes

    # 4. Idempotency: second run reports no_change
    assert cli_main(["reconcile", "--to", "active", "--yes", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "no_change"
    assert out["changed"] is False


def test_reconcile_repairs_rc4_wrong_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Oracle (e): rc4 wrong projection (legacy hermes.desktop) is repaired by supported reconcile --to active."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    manager = _activation_manager(
        tmp_path, monkeypatch, controller=controller, project_root=project_root
    )
    store = manager.store

    # Active release is rc5
    rc5_rec = _record(store, "1.0.0rc5-" + "5" * 16)
    _install_record(manager, rc5_rec)
    _release_manager_python(store, rc5_rec)

    manager.activate_existing(
        rc5_rec.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    spec = manager.projection_spec(rc5_rec)
    service_content = (
        "[Unit]\nDescription=Hermes Gateway\n\n[Service]\n"
        f"ExecStart={spec.runtime_current}/venv/bin/python -m hermes_cli.main --profile morfeo gateway run\n"
        f"WorkingDirectory={manager.store.profile_home('morfeo')}\n"
        f'Environment="HERMES_HOME={manager.store.profile_home("morfeo")}"\n'
        f'Environment="VIRTUAL_ENV={spec.runtime_current}/venv"\n'
    ).encode("utf-8")
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec.service_path.write_bytes(service_content)

    roots = manager.projection_roots()
    legacy_desktop = roots.desktop_dir / lifecycle._LEGACY_DESKTOP_ENTRY_NAME

    # Simulate rc4 writer defect: hermes.desktop present, aether.desktop missing
    spec.desktop_path.unlink(missing_ok=True)
    legacy_desktop.write_text("[Desktop Entry]\nName=Hermes\n", encoding="utf-8")
    assert legacy_desktop.is_file()
    assert not spec.desktop_path.is_file()

    status = manager.projection_status(rc5_rec)
    assert "legacy_desktop_entry_present" in status["mismatches"]
    assert "desktop_projection_missing" in status["mismatches"]

    active_bytes_before = store.active_pointer.read_bytes()

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)
    monkeypatch.setattr(manager, "executing_active_manager", lambda: rc5_rec)

    assert cli_main(["reconcile", "--to", "active", "--yes", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "changed"

    # Verifications:
    # 1. aether.desktop exists and is branded
    assert spec.desktop_path.is_file()
    assert "Name=Aether" in spec.desktop_path.read_text(encoding="utf-8")
    # 2. legacy desktop is removed
    assert not legacy_desktop.exists()
    # 3. active.json was not edited or mutated
    assert store.active_pointer.read_bytes() == active_bytes_before
    # 4. projection status is 100% clean
    assert manager.projection_status(rc5_rec)["mismatches"] == []
    assert "PROJECTIONS_INCOHERENT" not in manager.doctor().codes


def test_legacy_route_refusal_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Oracle (f)/Item 6: unauthenticated legacy route refuses before mutation without touching managed files."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store

    # Active release is an unauthenticated legacy rc3 release (no installed_file_fingerprint)
    legacy_rec = _record(store, "1.0.0rc3-" + "3" * 16)
    legacy_rec = replace(
        legacy_rec,
        schema_version=2,
        installed_file_fingerprint=None,
        aether_identity=None,
        prebuild_identity=None,
        tui_sha256=None,
    )
    _install_record(manager, legacy_rec)
    _release_manager_python(store, legacy_rec)

    # Directly commit as active pointer
    store._commit_active(legacy_rec)
    spec = manager.projection_spec(legacy_rec)

    witnessed_paths = [
        store.active_pointer,
        spec.launcher_path,
        spec.desktop_path,
    ]
    before_hashes = {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in witnessed_paths if p.is_file()
    }

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)

    # Active reconcile refuses because rc3 cannot prove active manager authority
    assert cli_main(["reconcile", "--to", "active", "--yes", "--json"]) == 4
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "error"
    assert out["errors"][0]["code"] == "RECONCILE_REFUSED"

    after_hashes = {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in witnessed_paths if p.is_file()
    }
    assert after_hashes == before_hashes


def _hostile_target_package_source() -> str:
    """Source of a permissive stand-in that answers for a target wherever it is imported.

    It is the fixture's stand-in for project-local code: every identity comparison
    succeeds, so anything built from it is self-consistent but nobody authenticated it.
    """

    return f'''
"""Permissive stand-in package that answers for a target from an unauthenticated path."""

from pathlib import Path


class IntegrityError(Exception):
    pass


class _StandInRecord:
    def __init__(self, release_id):
        self.release_id = release_id
        self.version = "0.0.0+spoofed"

    def __getattr__(self, name):
        return None

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class ReleaseRecord:
    @staticmethod
    def from_json(payload):
        release_id = payload.get("release_id") if isinstance(payload, dict) else "spoofed"
        return _StandInRecord(release_id)


class ReleaseStore:
    def __init__(self, *args, **kwargs):
        self.releases = Path("/spoofed/releases")

    def release_path(self, release_id):
        return self.releases / release_id

    def _read_release(self, release_id):
        return _StandInRecord(release_id)


class ProjectionRoots:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _StandInSpec:
    def __init__(self, roots):
        self.launcher_path = Path(roots.launcher_dir) / {lifecycle._LAUNCHER_NAME!r}
        self.launcher_bytes = b"#!/bin/sh\\n# spoofed-by-cwd\\n"
        self.desktop_path = Path(roots.desktop_dir) / {lifecycle._DESKTOP_ENTRY_NAME!r}
        self.desktop_bytes = b"spoofed desktop\\n"
        self.service_path = Path(roots.service_dir) / {lifecycle.AETHER_GATEWAY_UNIT!r}
        self.service_bytes = b"spoofed unit\\n"
        self.wsl_shortcuts = {{}}


class LifecycleManager:
    def __init__(self, **kwargs):
        self.roots = kwargs.get("projections")

    def projection_spec(self, record, project_root=None):
        return _StandInSpec(self.roots)
'''


def test_target_runner_answers_only_from_the_target_release_not_the_invoking_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The target boundary is not spoofable from the launcher's own working directory.

    ``python -c`` normally puts the current directory first on ``sys.path``, so a
    project-local ``aether_agents`` package would answer for the selected target: it
    would accept a record the target's real reader refuses and it would supply the
    projected bytes.  The child is isolated and proves its own import provenance.
    """

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _activation_manager(tmp_path, monkeypatch)
    store = manager.store
    target = _record(store, "1.0.0rc5-" + "d" * 16)
    _install_record(manager, target)
    _release_manager_python(store, target)

    record_path = store.release_path(target.release_id) / "record.json"
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert "unknown_future_field_not_in_schema" not in payload
    spoofed = dict(payload)
    spoofed["unknown_future_field_not_in_schema"] = "disallowed"

    hostile = tmp_path / "hostile-project"
    (hostile / "aether_agents").mkdir(parents=True)
    (hostile / "aether_agents" / "__init__.py").write_text("", encoding="utf-8")
    (hostile / "aether_agents" / "lifecycle.py").write_text(
        _hostile_target_package_source(),
        encoding="utf-8",
    )

    # The exact target reader rejects the added key from a neutral directory...
    with pytest.raises(IntegrityError, match="RECORD_SYNTAX_REJECTED"):
        manager._validate_target_record_subprocess(target.release_id, spoofed)

    # ...and a hostile working directory cannot answer in the target's place.
    monkeypatch.chdir(hostile)
    with pytest.raises(IntegrityError, match="RECORD_SYNTAX_REJECTED"):
        manager._validate_target_record_subprocess(target.release_id, spoofed)

    # Projection bytes are equally owned by the target release, not by cwd.
    plan = manager._prepare_target_projections_subprocess(target.release_id, target)
    expected = manager.projection_spec(store._read_release(target.release_id))
    assert plan.launcher_bytes == expected.launcher_bytes
    assert plan.desktop_bytes == expected.desktop_bytes
    assert b"spoofed-by-cwd" not in plan.launcher_bytes
    assert b"spoofed" not in plan.desktop_bytes


def test_unavailable_target_projection_plan_refuses_before_any_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A target that cannot produce its plan stops the transition before any byte moves.

    Swallowing that failure would complete the transition with the executing source's
    own projection bytes and without any target-side validation, which is the
    rc5-shaped "completed broken" outcome the transition must refuse.
    """

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = _record(store, "1.0.0rc1-" + "a" * 16)
    target = _record(store, "1.0.0rc1-" + "b" * 16)
    _install_record(manager, prior)
    _install_record(manager, target)
    _release_manager_python(store, prior)
    _release_manager_python(store, target)

    manager.activate_existing(
        prior.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    spec = manager.projection_spec(prior)
    witnessed_paths = [
        store.active_pointer,
        store.root / "runtime" / "current",
        spec.launcher_path,
        spec.desktop_path,
        spec.service_path,
    ]
    before_hashes = {
        p: (
            hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() and not p.is_symlink()
            else (os.readlink(p) if p.is_symlink() else None)
        )
        for p in witnessed_paths
    }
    before_bytes = store.active_pointer.read_bytes()
    before_calls = list(controller.calls)

    prepare_target_plan = manager._prepare_target_projections_subprocess

    def _refuse_the_target(*args, **kwargs):
        if args and args[0] == target.release_id:
            raise IntegrityError("simulated unavailable target projection plan")
        return prepare_target_plan(*args, **kwargs)

    monkeypatch.setattr(manager, "_prepare_target_projections_subprocess", _refuse_the_target)

    with pytest.raises(IntegrityError, match="simulated unavailable target projection plan"):
        manager.activate_existing(
            target.release_id,
            transition_kind="update",
            expected_active_release_id=prior.release_id,
        )

    # The refused transition promoted nothing and interrupted nothing.
    restored = store.active()
    assert restored is not None
    assert restored.release_id == prior.release_id
    assert store.active_pointer.read_bytes() == before_bytes
    assert manager.projection_status(restored)["mismatches"] == []
    after_hashes = {
        p: (
            hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() and not p.is_symlink()
            else (os.readlink(p) if p.is_symlink() else None)
        )
        for p in witnessed_paths
    }
    assert after_hashes == before_hashes
    assert controller.calls == before_calls


def test_unreadable_target_record_refuses_instead_of_synthesizing_a_pointer(
    tmp_path: Path,
) -> None:
    """A target with no immutable record refuses; source dataclass defaults never leak.

    The pointer's field shape belongs to the target.  When the target's immutable
    ``record.json`` is absent or unsafe there is nothing to persist, so the transition
    must refuse instead of serializing this process's own field set into it.
    """

    store = ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether")
    store._ensure_owned_root()
    record = _record(store, "1.0.0rc1-" + "e" * 16)
    release = store.release_path(record.release_id)
    release.mkdir(parents=True, exist_ok=True)
    payload = {field: getattr(record, field) for field in record.__dataclass_fields__}
    lifecycle._atomic_json(release / "record.json", payload)

    # Sanity: with its own immutable record present the target owns the field set.
    assert store._target_active_payload(record)["release_id"] == record.release_id

    (release / "record.json").unlink()
    with pytest.raises(IntegrityError, match="no immutable record"):
        store._target_active_payload(record)

    # A symlinked record is not an immutable target record either.
    elsewhere = tmp_path / "borrowed-record.json"
    elsewhere.write_text(json.dumps(payload), encoding="utf-8")
    (release / "record.json").symlink_to(elsewhere)
    with pytest.raises(IntegrityError, match="no immutable record"):
        store._target_active_payload(record)


def test_reconcile_to_active_dispatches_to_active_manager_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The entry-point invocation of reconcile --to active reaches the active manager.

    Regression for RC6-LIFE-2: verify that an entry point running outside the active
    manager dispatches reconcile --to active to the authenticated manager environment
    rather than running locally and failing authority proof.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    active_rec = _record(store, "1.0.0rc6-" + "6" * 16)
    _install_record(manager, active_rec)

    probe_python = tmp_path / "manager-bin-python"
    witness_file = tmp_path / "probe_witness.json"
    probe_python.write_text(
        f"#!{sys.executable}\n"
        "import sys, json\n"
        f"witness = {str(witness_file)!r}\n"
        "with open(witness, 'w', encoding='utf-8') as f:\n"
        "    json.dump({'executable': sys.executable, 'argv': sys.argv[1:]}, f)\n"
        "is_yes = '--yes' in sys.argv\n"
        "envelope = {\n"
        "    'schema_version': 1,\n"
        "    'command': 'reconcile',\n"
        "    'result': 'changed' if is_yes else 'planned',\n"
        "    'changed': is_yes,\n"
        "    'manager_version': '1.0.0rc6',\n"
        "    'active_version': '1.0.0-rc.6',\n"
        "    'warnings': [] if is_yes else [{'code': 'CONFIRMATION_REQUIRED', 'message': 'Re-run with --yes'}],\n"
        "    'errors': [],\n"
        "    'data': {\n"
        "        'mode': 'active',\n"
        f"        'active_release_id': '{active_rec.release_id}',\n"
        "        'mismatches': [] if is_yes else ['desktop_projection_mismatch'],\n"
        "        'projections_reconciled': 1 if is_yes else 0,\n"
        "    },\n"
        "}\n"
        "print(json.dumps(envelope))\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    probe_python.chmod(0o755)

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)
    monkeypatch.setattr(
        manager, "active_manager_dispatch_target", lambda: (active_rec, probe_python)
    )

    # 1. Preview without --yes dispatches to active manager and reports planned
    exit_code = cli_main(["reconcile", "--to", "active", "--json"])
    assert exit_code == 0
    assert witness_file.is_file()
    witness_data = json.loads(witness_file.read_text(encoding="utf-8"))
    assert witness_data["argv"] == [
        "-m",
        "aether_agents.cli",
        "reconcile",
        "--to",
        "active",
        "--json",
    ]
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "reconcile"
    assert out["result"] == "planned"
    assert out["changed"] is False

    # 2. Preview with --dry-run dispatches to active manager
    assert cli_main(["reconcile", "--to", "active", "--dry-run", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "planned"
    assert out["changed"] is False

    # 3. Apply with --yes dispatches to active manager and applies
    assert cli_main(["reconcile", "--to", "active", "--yes", "--json"]) == 0
    witness_data = json.loads(witness_file.read_text(encoding="utf-8"))
    assert "--yes" in witness_data["argv"]
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "changed"
    assert out["changed"] is True
    assert out["data"]["projections_reconciled"] == 1


def test_reconcile_refuses_when_no_active_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reconcile refuses with code 4 when no active manager exists."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _activation_manager(tmp_path, monkeypatch)

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)
    monkeypatch.setattr(manager, "active_manager_dispatch_target", lambda: None)
    monkeypatch.setattr(
        manager,
        "executing_active_manager",
        lambda: (_ for _ in ()).throw(IntegrityError("no active manager")),
    )

    exit_code = cli_main(["reconcile", "--to", "active", "--json"])
    assert exit_code == 4
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "error"
    assert out["errors"][0]["code"] == "ACTIVE_MANAGER_AUTHORITY_REQUIRED"
    assert "no active manager can authorize reconciliation" in out["errors"][0]["message"]


def test_reconcile_unsupported_mode_without_active_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsupported modes refuse with code 3 even before product bootstrap."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _activation_manager(tmp_path, monkeypatch)

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)
    monkeypatch.setattr(manager, "active_manager_dispatch_target", lambda: None)

    assert cli_main(["reconcile", "--to", "installed", "--json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "unsupported"
    assert out["errors"][0]["code"] == "UNSUPPORTED_RECONCILE_MODE"

    assert cli_main(["reconcile", "--json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "unsupported"
    assert out["errors"][0]["code"] == "UNSUPPORTED_RECONCILE_MODE"


def test_reconcile_stale_managed_manager_refuses_recursion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale managed manager refuses with code 4 instead of recursively dispatching."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    manager = _activation_manager(tmp_path, monkeypatch)

    from aether_agents.cli import main as cli_main

    monkeypatch.setattr("aether_agents.cli._lifecycle_manager", lambda: manager)
    monkeypatch.setattr(manager, "executing_manager_is_release_scoped", lambda: True)
    monkeypatch.setattr(
        manager,
        "executing_active_manager",
        lambda: (_ for _ in ()).throw(IntegrityError("stale managed manager")),
    )

    exit_code = cli_main(["reconcile", "--to", "active", "--json"])
    assert exit_code == 4
    out = json.loads(capsys.readouterr().out)
    assert out["result"] == "error"
    assert out["errors"][0]["code"] == "ACTIVE_MANAGER_AUTHORITY_REQUIRED"
    assert "stale managed manager" in out["errors"][0]["message"]


RC12_COMMIT = "7817ec919941edd88fe501c23ba624d254d484c6"
RC13_HERMES_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
RC13_HERMES_TREE = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"


def test_rc12_reader_accepts_rc13_schema5_and_activates_forward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A disposable rc12 manager accepts an rc13 schema-5 target and moves forward.

    The rc12 reader is the exact live commit. The rc13 manager then activates that
    target in an isolated store. Mutable state stays put and the Hermes pin does not move.
    """

    import importlib.util
    import io
    import tarfile

    repo = Path(__file__).resolve().parents[1]
    extract = tmp_path / "rc12-source"
    extract.mkdir()
    archive = subprocess.run(
        [
            "git",
            "archive",
            RC12_COMMIT,
            "src/aether_agents",
            "specs/001-aether-v1-productization/contracts/release-lock.schema.json",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(extract, filter="data")
    (extract / "VERSION").write_text("1.0.0rc12\n", encoding="utf-8")

    helper_path = Path(__file__).with_name("test_observation_lifecycle.py")
    spec = importlib.util.spec_from_file_location("rc13_forward_lock_helper", helper_path)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    lock_path = helper._write_release_lock(
        tmp_path,
        "1.0.0rc13",
        hermes_commit=RC13_HERMES_COMMIT,
        source_tree_sha256=RC13_HERMES_TREE,
    )
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 5
    payload["hermes"]["extras"] = ["mcp"]
    payload["aether"]["package_version"] = "1.0.0rc13"
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    probe = tmp_path / "rc12_probe.py"
    probe.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "from aether_agents.lifecycle import load_release_lock\n"
        "loaded = load_release_lock(Path(sys.argv[1]))\n"
        "print(json.dumps({\n"
        "    'extras': list(loaded.hermes_extras),\n"
        "    'commit': loaded.effective_hermes_source.commit,\n"
        "    'tree': loaded.hermes_source_tree_sha256,\n"
        "}))\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(extract / "src")
    env.pop("AETHER_RUNTIME_ROOT", None)
    completed = subprocess.run(
        [sys.executable, str(probe), str(lock_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    accepted = json.loads(completed.stdout)
    assert accepted == {
        "extras": ["mcp"],
        "commit": RC13_HERMES_COMMIT,
        "tree": RC13_HERMES_TREE,
    }

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = replace(
        _record(store, "1.0.0rc12-" + "a" * 16),
        hermes_commit=RC13_HERMES_COMMIT,
        hermes_source_tree_sha256=RC13_HERMES_TREE,
    )
    target = replace(
        _record(store, "1.0.0rc13-" + "b" * 16),
        hermes_commit=RC13_HERMES_COMMIT,
        hermes_source_tree_sha256=RC13_HERMES_TREE,
    )
    prior.validate()
    target.validate()
    _install_record(manager, prior)
    _install_record(manager, target)
    _release_manager_python(store, prior)
    _release_manager_python(store, target)
    manager.activate_existing(
        prior.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )
    mutable = store.state_root / "hermes" / "profiles" / "morfeo" / "memories" / "note.md"
    mutable.parent.mkdir(parents=True, exist_ok=True)
    mutable.write_bytes(b"owner memory bytes\n")
    before = hashlib.sha256(mutable.read_bytes()).hexdigest()
    active_before = store.active_pointer.read_bytes()

    updated = manager.activate_existing(
        target.release_id,
        transition_kind="update",
        expected_active_release_id=prior.release_id,
    )

    assert updated.version == "1.0.0rc13"
    assert updated.hermes_commit == RC13_HERMES_COMMIT
    assert updated.hermes_source_tree_sha256 == RC13_HERMES_TREE
    assert updated.release_id != prior.release_id
    assert store.release_path(prior.release_id).is_dir()
    assert (store.root / "runtime" / "current").resolve() == store.release_path(target.release_id)
    assert hashlib.sha256(mutable.read_bytes()).hexdigest() == before
    assert store.active_pointer.read_bytes() != active_before
    assert updated.previous_release_id == prior.release_id


def test_rc12_reader_accepts_rc14_schema5_and_activates_forward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A disposable rc12 manager accepts an rc14 schema-5 target and moves forward.

    Required HLP paths are present in a disposable fork. HLP-428 and HLP-433 stay
    deferred and do not block. Mutable state stays put and the Hermes pin does not move.
    """

    import importlib.util
    import io
    import tarfile

    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "rc14_hlp_validator",
        repo / "scripts" / "validate_hermes_patch_reconciliation.py",
    )
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    entries = (
        repo
        / "specs"
        / "001-aether-v1-productization"
        / "evidence"
        / "hermes-patch-reconciliation"
        / "entries"
    )
    records = [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(entries.glob("HLP-*.json"))
    ]
    fork = tmp_path / "fork"
    fork.mkdir()
    _git(fork, "init", "-q", "-b", "aether-main")
    _git(fork, "config", "user.name", "Aether Test")
    _git(fork, "config", "user.email", "aether@example.invalid")
    _git(fork, "remote", "add", "origin", "https://github.com/DarkArty07/aether-hermes")
    for record in records:
        if record.get("candidate_requirement") == "deferred":
            continue
        for relative in validator._selected_source_paths(record, repo):
            destination = fork / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_text("present\n", encoding="utf-8")
    _git(fork, "add", "-A")
    _git(fork, "commit", "-qm", "required sources")
    revision = _git(fork, "rev-parse", "HEAD")
    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "validate_hermes_patch_reconciliation.py"),
            "--root",
            str(repo),
            "--candidate-check",
            "--json",
            "--selected-revision",
            revision,
            "--fork-checkout",
            str(fork),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(
        [line for line in completed.stdout.splitlines() if line.startswith("{")][-1]
    )
    deferred = {item["id"]: item for item in summary["deferred_hlps"]}
    assert set(deferred) == {"HLP-433"}
    assert deferred["HLP-433"]["missing"] == []
    assert summary["refusing_hlps"] == []
    assert summary["status"] == "qualified"
    assert "HLP-427" in summary["required_hlps"]
    assert "HLP-428" in summary["required_hlps"]

    extract = tmp_path / "rc12-source"
    extract.mkdir()
    archive = subprocess.run(
        [
            "git",
            "archive",
            RC12_COMMIT,
            "src/aether_agents",
            "specs/001-aether-v1-productization/contracts/release-lock.schema.json",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(extract, filter="data")
    (extract / "VERSION").write_text("1.0.0rc12\n", encoding="utf-8")

    helper_path = Path(__file__).with_name("test_observation_lifecycle.py")
    helper_spec = importlib.util.spec_from_file_location("rc14_forward_lock_helper", helper_path)
    assert helper_spec is not None and helper_spec.loader is not None
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    lock_path = helper._write_release_lock(
        tmp_path,
        "1.0.0rc14",
        hermes_commit=RC13_HERMES_COMMIT,
        source_tree_sha256=RC13_HERMES_TREE,
    )
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 5
    payload["hermes"]["extras"] = ["mcp"]
    payload["aether"]["package_version"] = "1.0.0rc14"
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    probe = tmp_path / "rc12_probe.py"
    probe.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "from aether_agents.lifecycle import load_release_lock\n"
        "loaded = load_release_lock(Path(sys.argv[1]))\n"
        "print(json.dumps({\n"
        "    'extras': list(loaded.hermes_extras),\n"
        "    'commit': loaded.effective_hermes_source.commit,\n"
        "    'tree': loaded.hermes_source_tree_sha256,\n"
        "}))\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(extract / "src")
    env.pop("AETHER_RUNTIME_ROOT", None)
    probed = subprocess.run(
        [sys.executable, str(probe), str(lock_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert probed.returncode == 0, probed.stderr
    assert json.loads(probed.stdout) == {
        "extras": ["mcp"],
        "commit": RC13_HERMES_COMMIT,
        "tree": RC13_HERMES_TREE,
    }

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    controller = RecordingServiceController()
    manager = _activation_manager(tmp_path, monkeypatch, controller=controller)
    store = manager.store
    prior = replace(
        _record(store, "1.0.0rc12-" + "a" * 16),
        hermes_commit=RC13_HERMES_COMMIT,
        hermes_source_tree_sha256=RC13_HERMES_TREE,
    )
    target = replace(
        _record(store, "1.0.0rc14-" + "b" * 16),
        hermes_commit=RC13_HERMES_COMMIT,
        hermes_source_tree_sha256=RC13_HERMES_TREE,
    )
    prior.validate()
    target.validate()
    _install_record(manager, prior)
    _install_record(manager, target)
    prior_record = (store.release_path(prior.release_id) / "record.json").read_bytes()
    target_record = (store.release_path(target.release_id) / "record.json").read_bytes()
    _release_manager_python(store, prior)
    _release_manager_python(store, target)
    manager.activate_existing(
        prior.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )
    mutable = store.state_root / "hermes" / "profiles" / "morfeo" / "memories" / "note.md"
    mutable.parent.mkdir(parents=True, exist_ok=True)
    mutable.write_bytes(b"owner memory bytes\n")
    before = hashlib.sha256(mutable.read_bytes()).hexdigest()

    updated = manager.activate_existing(
        target.release_id,
        transition_kind="update",
        expected_active_release_id=prior.release_id,
    )

    assert updated.version == "1.0.0rc14"
    assert updated.hermes_commit == RC13_HERMES_COMMIT
    assert updated.release_id != prior.release_id
    assert hashlib.sha256(mutable.read_bytes()).hexdigest() == before
    assert (store.release_path(prior.release_id) / "record.json").read_bytes() == prior_record
    assert (store.release_path(target.release_id) / "record.json").read_bytes() == target_record
    assert updated.previous_release_id == prior.release_id
