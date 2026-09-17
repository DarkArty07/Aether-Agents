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
import subprocess
import sys
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
    completed = subprocess.run(
        ["git", *arguments],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
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
) -> LifecycleManager:
    store = ReleaseStore(root / "data" / "aether", state_root=root / "state" / "aether")
    return LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        service_controller=controller or DisabledServiceController(),
        projections=ProjectionRoots.disposable(root / "operator-projections"),
    )


def _operator_destination_witnesses() -> dict[str, tuple[int, int, str | None]]:
    """Hash/mtime witnesses for the operator's real launcher, Desktop entry and unit."""

    witnessed: dict[str, tuple[int, int, str | None]] = {}
    for path in (
        Path(user_bin_dir()) / "aether",
        Path(applications_dir()) / "hermes.desktop",
        Path(systemd_user_dir()) / AETHER_GATEWAY_UNIT,
    ):
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

    identity = _aether_identity("1.0.0rc1")
    record = ReleaseRecord(
        schema_version=3,
        release_id=release_id,
        version="1.0.0rc1",
        wheel_filename="aether_agents-1.0.0rc1-py3-none-any.whl",
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
    )
    record.validate()
    release = store.release_path(release_id)
    release.mkdir(parents=True, exist_ok=True)
    (release / "venv").symlink_to("runtime")
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


def _release_manager_python(store: ReleaseStore, record: ReleaseRecord) -> None:
    """Give one synthetic release the bundle and manager interpreter activation needs."""

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
    python = release / "manager" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True, exist_ok=True)
    source_root = Path(__file__).parents[1] / "src"
    python.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        f"source = {str(source_root)!r}\n"
        "environment = dict(os.environ)\n"
        "environment['PYTHONPATH'] = source\n"
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
) -> LifecycleManager:
    """One disposable manager authorized for synthetic transitions only."""

    manager = _manager(tmp_path, controller=controller)
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
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    record = _record(store)
    _publish_record(manager, record)

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
