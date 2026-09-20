"""Comprehensive regressions for Hermes-owned gateway service boundary (rc5).

Covers:
- AC-1: Ownership boundary (no service bytes in ProjectionSpec/digests for rc5+, no HERMES_TUI_DIR required).
- AC-2: Hermes materialization seam (exact CLI invocation, isolated env/cwd, no rewrite loop, repeated refresh).
- AC-3: Semantic doctor (regular file, exact ExecStart, WorkingDirectory, HERMES_HOME, VIRTUAL_ENV,
        no duplicate/conflicting selectors, incidental tolerance, attributed invalid classes, service probe).
- AC-4: Transition atomicity and recovery (refresh failure restore, restart failure restore, 0 pending,
        uninstall via Hermes CLI, rc4->rc5 update, rc3 rollback, forward rc5 reactivation).
- Exact Hermes generator integration lane using authentic generator functions.
- Strict isolation guarantees: autouse live-unit guard, unconditional HOME redirection.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aether_agents.lifecycle import (
    AETHER_GATEWAY_UNIT,
    HERMES_BASELINE,
    MAINTAINED_FORK_BRANCH,
    MAINTAINED_FORK_REPOSITORY,
    OBSERVER_ENTRY_POINT,
    AetherPrebuildIdentity,
    AuthorityContext,
    IntegrityError,
    LifecycleManager,
    ProjectionRoots,
    ProjectionSpec,
    ReleaseRecord,
    ReleaseStore,
    ServiceController,
    _atomic_json,
    _is_branded_version,
    _is_hermes_owned_gateway_version,
)

_OPERATOR_HOME = Path(os.path.expanduser("~")).resolve()
_OPERATOR_UNIT_PATH = _OPERATOR_HOME / ".config" / "systemd" / "user" / AETHER_GATEWAY_UNIT


@pytest.fixture(autouse=True)
def _guard_operator_live_unit() -> Any:
    """Fail loudly if any test mutates or writes to the operator's live systemd unit."""
    pre_exists = _OPERATOR_UNIT_PATH.exists()
    pre_stat = _OPERATOR_UNIT_PATH.stat() if pre_exists else None
    pre_bytes = (
        _OPERATOR_UNIT_PATH.read_bytes()
        if pre_exists and not _OPERATOR_UNIT_PATH.is_symlink() and _OPERATOR_UNIT_PATH.is_file()
        else None
    )
    pre_sha = hashlib.sha256(pre_bytes).hexdigest() if pre_bytes is not None else None

    yield

    post_exists = _OPERATOR_UNIT_PATH.exists()
    assert post_exists == pre_exists, (
        f"CRITICAL: Operator live unit existence changed during test! "
        f"Before: {pre_exists}, After: {post_exists}"
    )
    if pre_exists and pre_stat is not None:
        post_stat = _OPERATOR_UNIT_PATH.stat()
        post_bytes = (
            _OPERATOR_UNIT_PATH.read_bytes()
            if not _OPERATOR_UNIT_PATH.is_symlink() and _OPERATOR_UNIT_PATH.is_file()
            else None
        )
        post_sha = hashlib.sha256(post_bytes).hexdigest() if post_bytes is not None else None
        assert post_sha == pre_sha, (
            f"CRITICAL: Operator live unit was modified during test!\n"
            f"Path: {_OPERATOR_UNIT_PATH}\n"
            f"Pre SHA: {pre_sha}\n"
            f"Post SHA: {post_sha}"
        )
        assert post_stat.st_mtime == pre_stat.st_mtime, (
            f"CRITICAL: Operator live unit mtime changed during test!\n"
            f"Path: {_OPERATOR_UNIT_PATH}\n"
            f"Pre mtime: {pre_stat.st_mtime}\n"
            f"Post mtime: {post_stat.st_mtime}"
        )


class RecordingServiceController(ServiceController):
    """Test controller that records restarts and reports configurable status."""

    def __init__(self, *, status_result: str = "active", available_result: bool = True) -> None:
        self.restarts: list[str] = []
        self.status_result = status_result
        self.available_result = available_result

    def available(self) -> bool:
        return self.available_result

    def restart(self, unit_name: str) -> str:
        self.restarts.append(unit_name)
        return "restarted"

    def status(self, unit_name: str) -> str:
        return self.status_result


def _setup_isolated_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    controller: ServiceController | None = None,
    hermes_runner: Any = None,
) -> tuple[LifecycleManager, Path]:
    isolated_home = (tmp_path / "home").resolve()
    isolated_config = isolated_home / ".config"
    isolated_systemd = isolated_config / "systemd" / "user"
    isolated_systemd.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(isolated_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(isolated_config))
    monkeypatch.setenv("XDG_DATA_HOME", str((tmp_path / "data").resolve()))
    monkeypatch.setenv("XDG_STATE_HOME", str((tmp_path / "state").resolve()))

    # Verify resolution of home does not touch operator's home
    assert Path.home().resolve() == isolated_home

    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    marker_dir = project_root / ".aether"
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / "project.toml").write_text('project_id = "test-proj"\n', encoding="utf-8")

    store = ReleaseStore(
        root=tmp_path / "data" / "aether",
        state_root=tmp_path / "state" / "aether",
    )
    from aether_agents.observation.context import ProjectRegistry

    registry = ProjectRegistry(store.state_root)
    registry.register("test-proj", project_root, name="test-proj")

    # Confine projections to isolated tmp_path
    projections = ProjectionRoots(
        launcher_dir=tmp_path / "projections" / "bin",
        desktop_dir=tmp_path / "projections" / "applications",
        service_dir=isolated_systemd,
        wsl_shortcuts_dir=tmp_path / "projections" / "windows-terminal",
    )
    assert tmp_path in projections.service_dir.parents
    assert projections.service_dir != _OPERATOR_UNIT_PATH.parent

    store._ensure_owned_root()
    manager = LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        service_controller=controller or RecordingServiceController(),
        projections=projections,
        project_root=project_root,
        hermes_runner=hermes_runner,
    )
    return manager, project_root


def _aether_identity(version: str) -> dict[str, Any]:
    tag_suffix = ""
    if "rc" in version:
        parts = version.split("rc")
        tag_suffix = f"-rc.{parts[1]}"
    elif "a" in version:
        parts = version.split("a")
        tag_suffix = f"-a.{parts[1]}"
    base_ver = version.split("rc")[0].split("a")[0]
    git_tag = f"v{base_ver}{tag_suffix}"
    return {
        "distribution": "aether-agents",
        "package_version": version,
        "git_tag": git_tag,
        "git_commit": "a" * 40,
        "python_requires": ">=3.11,<3.14",
        "observer": dict(OBSERVER_ENTRY_POINT),
    }


def _make_release(
    manager: LifecycleManager,
    version: str,
    release_suffix: str = "1111111111111111",
    *,
    previous_release_id: str | None = None,
) -> ReleaseRecord:
    release_id = f"{version}-{release_suffix}"
    rel_path = manager.store.release_path(release_id)
    rel_path.mkdir(parents=True, exist_ok=True)
    (rel_path / "venv" / "bin").mkdir(parents=True, exist_ok=True)
    (rel_path / "venv" / "bin" / "python").write_text("#!/bin/sh\nexit 0\n")
    (rel_path / "venv" / "bin" / "python").chmod(0o755)
    (rel_path / "venv" / "bin" / "aether").write_text("#!/bin/sh\nexit 0\n")
    (rel_path / "venv" / "bin" / "aether").chmod(0o755)

    # Prebuilt TUI
    (rel_path / "tui" / "dist").mkdir(parents=True, exist_ok=True)
    tui_bytes = b"console.log('rc-tui');\n"
    (rel_path / "tui" / "dist" / "entry.js").write_bytes(tui_bytes)
    tui_hash = hashlib.sha256(tui_bytes).hexdigest()

    # Artifacts and manifest
    (rel_path / "artifacts").mkdir(parents=True, exist_ok=True)
    wheel_name = f"aether_agents-{version}-py3-none-any.whl"
    wheel_bytes = b"PK\x05\x06" + b"\x00" * 18  # minimal zip
    (rel_path / "artifacts" / wheel_name).write_bytes(wheel_bytes)
    wheel_sha = hashlib.sha256(wheel_bytes).hexdigest()

    for env in ("manager", "runtime"):
        env_dir = rel_path / env
        (env_dir / "bin").mkdir(parents=True, exist_ok=True)
        py = env_dir / "bin" / "python"
        py.write_text("#!/bin/sh\nexit 0\n")
        py.chmod(0o755)
        (env_dir / "aether-wheel.sha256").write_text(wheel_sha + "\n")

    manifest = {
        "schema_version": 1,
        "release_id": release_id,
        "version": version,
        "wheel_filename": wheel_name,
        "wheel_sha256": wheel_sha,
        "installed_file_fingerprint": "a" * 64,
        "observation_compatibility": {
            "schema_version": 1,
            "events": {"min": 1, "max": 1},
            "summaries": {"min": 1, "max": 1},
        },
        "profiles": {"morfeo": {}, "supervisor": {}, "implementer": {}},
    }
    (rel_path / "release.json").write_text(json.dumps(manifest))

    identity = _aether_identity(version)
    record = ReleaseRecord(
        schema_version=3,
        release_id=release_id,
        version=version,
        wheel_filename=wheel_name,
        wheel_sha256=wheel_sha,
        hermes_tag=MAINTAINED_FORK_BRANCH,
        hermes_commit="a" * 40,
        observer_entry_point=HERMES_BASELINE.observer_entry_point,
        previous_release_id=previous_release_id,
        authority_context=AuthorityContext.for_active_release(release_id).to_record(),
        aether_identity=identity,
        prebuild_identity=AetherPrebuildIdentity.from_record(identity).digest,
        installed_file_fingerprint="a" * 64,
        hermes_repository=MAINTAINED_FORK_REPOSITORY,
        hermes_branch=MAINTAINED_FORK_BRANCH,
        hermes_source_tree_sha256="c" * 64,
        tui_sha256=tui_hash,
    )
    record.validate()

    # Ensure profile resources and homes exist
    for role in ("morfeo", "supervisor", "implementer"):
        prof_dir = rel_path / "profiles" / role
        prof_dir.mkdir(parents=True, exist_ok=True)
        (prof_dir / "config.yaml").write_text("model: test\n")
        (prof_dir / "SOUL.md").write_text("# Soul\n")
        manager.store.profile_home(role).mkdir(parents=True, exist_ok=True)

    # Publish record
    payload = {field: getattr(record, field) for field in record.__dataclass_fields__}
    manager.store.releases.mkdir(parents=True, exist_ok=True)
    _atomic_json(rel_path / "record.json", payload)
    _atomic_json(manager.store.releases / f"{release_id}.json", payload)
    return record


def _stub_healthy_runtime(
    manager: LifecycleManager,
    monkeypatch: pytest.MonkeyPatch,
    record: ReleaseRecord,
) -> None:
    monkeypatch.setattr(manager, "_validate_profile_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_validate_profile_homes", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_preflight_profile_homes", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_materialize_profile_homes", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_capture_profile_product_state", lambda *_a, **_k: {})
    monkeypatch.setattr(manager, "_restore_profile_product_state", lambda *_a, **_k: None)
    monkeypatch.setattr(
        manager,
        "_installed_aether_identity",
        lambda *_a, **_k: {
            "distribution": "aether-agents",
            "version": record.version,
            "fingerprint": "a" * 64,
        },
    )
    monkeypatch.setattr(
        manager,
        "_installed_distribution_version",
        lambda *_a, **_k: HERMES_BASELINE.version,
    )
    monkeypatch.setattr(
        manager,
        "_release_hermes_source",
        lambda *_a, **_k: type(
            "Source",
            (),
            {"version": HERMES_BASELINE.version, "commit": "a" * 40},
        )(),
    )
    monkeypatch.setattr(
        manager,
        "_observer_hook_probe",
        lambda *_a, **_k: (
            {
                "expected_callbacks": 22,
                "registered_callbacks": 22,
                "remaining_callbacks": 0,
            },
            True,
        ),
    )
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: manager.store._read_release(release_id),
    )
    monkeypatch.setattr(
        manager,
        "_assert_executing_active_manager_locked",
        lambda: manager.store.active(),
    )
    monkeypatch.setattr(manager, "_run_projection_transition_locked", lambda *_a, **_k: {})
    monkeypatch.setattr(manager, "_prepare_release_projections_locked", lambda *_a, **_k: {})
    monkeypatch.setattr(manager, "_select_release_projections_locked", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_reconcile_release_projections_locked", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_deactivate_release_projections_locked", lambda *_a, **_k: None)


def _generate_valid_hermes_unit(
    runtime_current: Path,
    profile_home: Path,
    *,
    with_tui_dir: bool = False,
    extra_incidental: str = "",
) -> bytes:
    python = f"{runtime_current}/venv/bin/python"
    tui_line = f'Environment="HERMES_TUI_DIR={runtime_current}/tui"\n' if with_tui_dir else ""
    content = f"""[Unit]
Description=Hermes Agent Gateway - Messaging Platform Integration
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0{extra_incidental}

[Service]
Type=simple
ExecStart={python} -m hermes_cli.main --profile morfeo gateway run
WorkingDirectory={profile_home}
Environment="PATH={runtime_current}/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="VIRTUAL_ENV={runtime_current}/venv"
Environment="HERMES_HOME={profile_home}"
{tui_line}Restart=always
RestartSec=5
RestartForceExitStatus=75
RestartPreventExitStatus=78
KillMode=mixed
KillSignal=SIGTERM
ExecReload=/bin/kill -USR1 $MAINPID
ExecStopPost=-{python} -m gateway.cgroup_cleanup
TimeoutStopSec=90
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""
    return content.encode("utf-8")


# =========================================================================
# AC-1: Ownership boundary
# =========================================================================


def test_ac1_ownership_projection_spec_and_digests_rc5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rc5-and-newer releases omit service_bytes and service digest in ProjectionSpec."""
    manager, project_root = _setup_isolated_manager(tmp_path, monkeypatch)
    rc5_record = _make_release(manager, "1.0.0rc5")
    spec_rc5 = manager.projection_spec(rc5_record)

    # 1. service_bytes is empty and service is omitted from digests
    assert spec_rc5.service_bytes == b""
    digests_rc5 = spec_rc5.digests()
    assert "service" not in digests_rc5
    assert "launcher" in digests_rc5
    assert "desktop" in digests_rc5

    # 2. Aether-owned projections remain intact
    launcher_text = spec_rc5.launcher_bytes.decode("utf-8")
    assert "export HERMES_TUI_DIR=" in launcher_text
    assert "AETHER_RUNTIME_ROOT/tui" in launcher_text

    desktop_text = spec_rc5.desktop_bytes.decode("utf-8")
    assert "Name=Aether" in desktop_text
    assert f"--project {project_root}" in desktop_text
    assert "[Desktop Action Continue]" in desktop_text

    # 3. For rc4, service_bytes and service digest are present
    rc4_record = _make_release(manager, "1.0.0rc4")
    spec_rc4 = manager.projection_spec(rc4_record)
    assert spec_rc4.service_bytes != b""
    assert "service" in spec_rc4.digests()

    # 4. For rc3, service_bytes and service digest are present (without HERMES_TUI_DIR)
    rc3_record = _make_release(manager, "1.0.0rc3")
    spec_rc3 = manager.projection_spec(rc3_record)
    assert spec_rc3.service_bytes != b""
    assert "service" in spec_rc3.digests()
    assert b"HERMES_TUI_DIR" not in spec_rc3.service_bytes


def test_ac1_hermes_owned_version_boundary_ordering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Boundary test asserting rc5-and-newer includes stable 1.0.0 and subsequent releases."""
    # Historical pre-rc5 versions: Aether owns the service unit
    for ver in ("1.0.0rc1", "1.0.0rc2", "1.0.0rc3", "1.0.0rc4", "1.0.0-rc.4", "0.9.0"):
        assert _is_hermes_owned_gateway_version(ver) is False, f"Expected False for {ver}"

    # rc5 and subsequent rc candidates
    for ver in ("1.0.0rc5", "1.0.0-rc.5", "1.0.0rc6", "1.0.0-rc.6"):
        assert _is_hermes_owned_gateway_version(ver) is True, f"Expected True for {ver}"

    # Stable 1.0.0 and subsequent releases must remain Hermes-owned
    for ver in ("1.0.0", "1.0.1", "1.1.0", "2.0.0"):
        assert _is_hermes_owned_gateway_version(ver) is True, f"Expected True for {ver}"

    # Verify branded versions
    for ver in ("1.0.0rc1", "1.0.0rc2", "1.0.0rc3", "0.9.0", "1.0.0"):
        assert _is_branded_version(ver) is False, f"Expected False for {ver}"
    for ver in ("1.0.0rc4", "1.0.0-rc.4", "1.0.0rc5", "1.0.0-rc.5", "1.0.0rc6"):
        assert _is_branded_version(ver) is True, f"Expected True for {ver}"

    # End-to-end ProjectionSpec check for stable 1.0.0
    manager, project_root = _setup_isolated_manager(tmp_path, monkeypatch)
    record_1_0_0 = _make_release(manager, "1.0.0")
    spec_1_0_0 = manager.projection_spec(record_1_0_0)
    assert spec_1_0_0.service_bytes == b""
    digests_1_0_0 = spec_1_0_0.digests()
    assert "service" not in digests_1_0_0
    assert "launcher" in digests_1_0_0
    assert "desktop" in digests_1_0_0


# =========================================================================
# AC-2: Hermes materialization seam
# =========================================================================


def test_ac2_hermes_materialization_seam_invoked_on_setup_and_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Projecting an rc5 release materializes the unit via the exact Hermes CLI command."""
    commands_run: list[tuple[list[str], dict[str, str], Path]] = []

    def mock_runner(
        cmd: list[str], env: dict[str, str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        commands_run.append((cmd, env, cwd))
        # Simulate Hermes writing the unit file
        runtime_current = Path(cmd[0]).parent.parent.parent
        profile_home = Path(env["HERMES_HOME"])
        unit_data = _generate_valid_hermes_unit(runtime_current, profile_home)
        unit_dest = (
            Path(env.get("HOME", str(Path.home())))
            / ".config"
            / "systemd"
            / "user"
            / AETHER_GATEWAY_UNIT
        )
        assert str(unit_dest).startswith(str(tmp_path)), f"Leaked unit destination: {unit_dest}"
        assert unit_dest != _OPERATOR_UNIT_PATH, "Must not write operator live unit!"
        unit_dest.parent.mkdir(parents=True, exist_ok=True)
        unit_dest.write_bytes(unit_data)
        return subprocess.CompletedProcess(cmd, 0, "Installed service", "")

    controller = RecordingServiceController()
    manager, _ = _setup_isolated_manager(
        tmp_path,
        monkeypatch,
        controller=controller,
        hermes_runner=mock_runner,
    )
    rc5_record = _make_release(manager, "1.0.0rc5")

    outcome = manager.project_release(rc5_record, restart_service=True)
    assert outcome["service_restart"] == "restarted"
    assert controller.restarts == [AETHER_GATEWAY_UNIT]

    # Verify exact command invoked
    assert len(commands_run) == 1
    cmd, env, cwd = commands_run[0]
    expected_python = str(manager.store.root / "runtime" / "current" / "venv" / "bin" / "python")
    assert cmd == [
        expected_python,
        "-m",
        "hermes_cli.main",
        "--profile",
        "morfeo",
        "gateway",
        "install",
        "--force",
        "--no-start-now",
        "--start-on-login",
    ]
    assert env["HERMES_HOME"] == str(manager.store.profile_home("morfeo"))
    assert "VIRTUAL_ENV" not in env
    assert cwd == manager.store.profile_home("morfeo")

    # Verify unit is present and projection_status is clean
    spec = manager.projection_spec(rc5_record)
    assert tmp_path in spec.service_path.parents
    assert spec.service_path.is_file()
    status = manager.projection_status(rc5_record)
    assert status["mismatches"] == []


def test_ac2_repeated_hermes_refresh_leaves_doctor_ready_and_no_rewrite_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated Hermes gateway start/restart refreshes leave doctor ready with zero Aether rewrite."""
    controller = RecordingServiceController()
    manager, _ = _setup_isolated_manager(
        tmp_path,
        monkeypatch,
        controller=controller,
    )
    record = _make_release(manager, "1.0.0rc5")
    _stub_healthy_runtime(manager, monkeypatch, record)
    manager.store._commit_active(record, expected_active_release_id=None)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    manager._switch_runtime_current(spec.release)
    profile_home = manager.store.profile_home("morfeo")

    # 1. First materialization/refresh by Hermes
    initial_unit = _generate_valid_hermes_unit(spec.runtime_current, profile_home)
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec.service_path.write_bytes(initial_unit)
    assert manager.projection_status(record)["mismatches"] == []
    assert manager.doctor().ready is True

    # 2. Second refresh by Hermes (e.g. gateway start/restart called again)
    # Hermes rewrites only if content changed or touches with incidental updates
    refreshed_unit = _generate_valid_hermes_unit(
        spec.runtime_current,
        profile_home,
        extra_incidental="\n# Refresh timestamp comment",
    )
    spec.service_path.write_bytes(refreshed_unit)

    # Invariants still hold: doctor remains ready
    status = manager.projection_status(record)
    assert status["mismatches"] == []
    assert manager.doctor().ready is True

    refreshed_bytes = spec.service_path.read_bytes()

    # 3. Aether runs project_release / reconcile - must NOT rewrite or overwrite the Hermes unit
    manager.project_release(record, restart_service=False)
    assert spec.service_path.read_bytes() == refreshed_bytes, (
        "Aether must not overwrite Hermes unit"
    )
    assert manager.doctor().ready is True


# =========================================================================
# AC-3: Semantic doctor
# =========================================================================


def test_ac3_semantic_doctor_accepts_exact_hermes_unit_and_incidental_differences(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Semantic doctor is ready with Hermes-generated units and ignores incidental differences."""
    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch)
    record = _make_release(manager, "1.0.0rc5")
    _stub_healthy_runtime(manager, monkeypatch, record)
    manager.store._commit_active(record, expected_active_release_id=None)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    manager._switch_runtime_current(spec.release)

    profile_home = manager.store.profile_home("morfeo")

    # 1. Exact unit without HERMES_TUI_DIR
    unit_bytes = _generate_valid_hermes_unit(spec.runtime_current, profile_home)
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec.service_path.write_bytes(unit_bytes)
    assert manager.projection_status(record)["mismatches"] == []
    assert manager.doctor().ready is True

    # 2. Unit with HERMES_TUI_DIR is also accepted (neither required nor rejected)
    unit_with_tui = _generate_valid_hermes_unit(
        spec.runtime_current, profile_home, with_tui_dir=True
    )
    spec.service_path.write_bytes(unit_with_tui)
    assert manager.projection_status(record)["mismatches"] == []
    assert manager.doctor().ready is True

    # 3. Incidental Description / PATH / timeout / watchdog differences
    unit_incidental = _generate_valid_hermes_unit(
        spec.runtime_current,
        profile_home,
        extra_incidental="\nWatchdogSec=120\nTimeoutStartSec=60",
    )
    spec.service_path.write_bytes(unit_incidental)
    assert manager.projection_status(record)["mismatches"] == []
    assert manager.doctor().ready is True


def test_ac3_semantic_doctor_attributes_each_invalid_selector_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each invalid selector class fails visibly with the attributed diagnostic string."""
    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch)
    record = _make_release(manager, "1.0.0rc5")
    manager.store._commit_active(record, expected_active_release_id=None)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    manager._switch_runtime_current(spec.release)
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)

    profile_home = manager.store.profile_home("morfeo")
    python = f"{spec.runtime_current}/venv/bin/python"

    # Helper to test a unit payload
    def check_failure(payload: bytes, expected_mismatch: str) -> None:
        spec.service_path.write_bytes(payload)
        status = manager.projection_status(record)
        assert expected_mismatch in status["mismatches"], (
            f"Expected {expected_mismatch} in {status['mismatches']}"
        )
        doctor = manager.doctor()
        assert doctor.ready is False
        assert "SERVICE_PROJECTION_MISMATCH" in doctor.codes

    # a. Wrong runtime Python
    bad_py = _generate_valid_hermes_unit(Path("/wrong/runtime"), profile_home)
    check_failure(bad_py, "service_projection_wrong_runtime_python")

    # b. Wrong profile
    wrong_prof = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile hestia gateway run\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="VIRTUAL_ENV={spec.runtime_current}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode("utf-8")
    check_failure(wrong_prof, "service_projection_wrong_profile")

    # c. Wrong WorkingDirectory
    wrong_work = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile morfeo gateway run\n"
        f"WorkingDirectory=/wrong/working/dir\n"
        f'Environment="VIRTUAL_ENV={spec.runtime_current}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode("utf-8")
    check_failure(wrong_work, "service_projection_wrong_working_directory")

    # d. Wrong home (HERMES_HOME)
    wrong_home = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile morfeo gateway run\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="VIRTUAL_ENV={spec.runtime_current}/venv"\n'
        f'Environment="HERMES_HOME=/wrong/hermes/home"\n'
    ).encode("utf-8")
    check_failure(wrong_home, "service_projection_wrong_home")

    # e. Wrong VIRTUAL_ENV
    wrong_venv = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile morfeo gateway run\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="VIRTUAL_ENV=/wrong/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode("utf-8")
    check_failure(wrong_venv, "service_projection_wrong_virtual_env")

    # f. Missing VIRTUAL_ENV
    missing_venv = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile morfeo gateway run\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode("utf-8")
    check_failure(missing_venv, "service_projection_missing_virtual_env")

    # g. Conflicting / duplicate selector lines
    dup_exec = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile morfeo gateway run\n"
        f"ExecStart=/bin/sh -c 'evil'\n"
        f"WorkingDirectory={profile_home}\n"
        f'Environment="VIRTUAL_ENV={spec.runtime_current}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode("utf-8")
    check_failure(dup_exec, "service_projection_conflicting_selectors")

    dup_work = (
        f"[Service]\nExecStart={python} -m hermes_cli.main --profile morfeo gateway run\n"
        f"WorkingDirectory={profile_home}\n"
        f"WorkingDirectory=/duplicate/dir\n"
        f'Environment="VIRTUAL_ENV={spec.runtime_current}/venv"\n'
        f'Environment="HERMES_HOME={profile_home}"\n'
    ).encode("utf-8")
    check_failure(dup_work, "service_projection_conflicting_selectors")

    # h. Absent unit file
    spec.service_path.unlink(missing_ok=True)
    status_missing = manager.projection_status(record)
    assert "service_projection_missing" in status_missing["mismatches"]
    doctor_missing = manager.doctor()
    assert doctor_missing.ready is False
    assert "SERVICE_PROJECTION_MISMATCH" in doctor_missing.codes

    # i. Non-regular unit path: symlink
    real_file = tmp_path / "actual_file.service"
    real_file.write_bytes(_generate_valid_hermes_unit(spec.runtime_current, profile_home))
    spec.service_path.unlink(missing_ok=True)
    os.symlink(str(real_file), str(spec.service_path))
    status_symlink = manager.projection_status(record)
    assert "service_projection_not_regular" in status_symlink["mismatches"]

    # j. Non-regular unit path: directory
    spec.service_path.unlink(missing_ok=True)
    spec.service_path.mkdir(parents=True, exist_ok=True)
    status_dir = manager.projection_status(record)
    assert "service_projection_not_regular" in status_dir["mismatches"]
    spec.service_path.rmdir()


def test_ac3_service_availability_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Doctor separately probes service availability/running status."""
    controller = RecordingServiceController(status_result="inactive", available_result=True)
    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch, controller=controller)
    record = _make_release(manager, "1.0.0rc5")
    _stub_healthy_runtime(manager, monkeypatch, record)
    manager.store._commit_active(record, expected_active_release_id=None)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    manager._switch_runtime_current(spec.release)

    # Valid unit file on disk
    profile_home = manager.store.profile_home("morfeo")
    unit_bytes = _generate_valid_hermes_unit(spec.runtime_current, profile_home)
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec.service_path.write_bytes(unit_bytes)

    # With service inactive, doctor must fail with SERVICE_UNAVAILABLE
    doctor = manager.doctor()
    assert doctor.ready is False
    assert "SERVICE_UNAVAILABLE" in doctor.codes
    assert "service_unavailable" in doctor.details["projections"]["mismatches"]
    assert doctor.details["service_controller"]["unit_status"] == "inactive"

    # When service becomes active, doctor is ready
    controller.status_result = "active"
    doctor_active = manager.doctor()
    assert doctor_active.ready is True
    assert "SERVICE_UNAVAILABLE" not in doctor_active.codes


# =========================================================================
# AC-4: Atomicity, recovery, and transitions
# =========================================================================


def test_ac4_transition_refresh_failure_restores_opaque_state_and_zero_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure during Hermes materialization restores previous selector, Aether files, and prior unit."""
    controller = RecordingServiceController()
    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch, controller=controller)
    r1 = _make_release(manager, "1.0.0rc5", "1111111111111111")
    r2 = _make_release(manager, "1.0.0rc5", "2222222222222222")
    _stub_healthy_runtime(manager, monkeypatch, r1)
    _stub_healthy_runtime(manager, monkeypatch, r2)

    # Initial activation of r1
    manager._switch_runtime_current(manager.store.release_path(r1.release_id))
    manager.store._commit_active(r1, expected_active_release_id=None)
    spec1 = manager.projection_spec(r1)
    profile_home = manager.store.profile_home("morfeo")
    prior_unit_bytes = _generate_valid_hermes_unit(spec1.runtime_current, profile_home)
    spec1.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec1.service_path.write_bytes(prior_unit_bytes)

    # Runner that fails on r2 materialization
    def failing_runner(
        cmd: list[str], env: dict[str, str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, "", "Simulated Hermes CLI failure")

    manager._hermes_runner = failing_runner

    with pytest.raises(IntegrityError, match="Hermes gateway service materialization failed"):
        manager.activate_existing(
            r2.release_id,
            transition_kind="update",
            expected_active_release_id=r1.release_id,
        )

    # Verify prior state is restored
    active = manager.store.active()
    assert active is not None
    assert active.release_id == r1.release_id
    assert spec1.service_path.read_bytes() == prior_unit_bytes
    assert spec1.runtime_current.resolve() == manager.store.release_path(r1.release_id)

    # Verify zero pending transitions in journal
    reopened, _ = _setup_isolated_manager(tmp_path, monkeypatch, controller=controller)
    _stub_healthy_runtime(reopened, monkeypatch, r1)
    recovered = reopened.recover()
    assert recovered.get("projections_reconciled", 0) in (0, 1)
    # Check journal has no pending entries
    for trn_file in manager.store.transitions.glob("trn_*.json"):
        payload = manager.store._read_transition(trn_file)
        assert payload["state"] != "pending"


def test_ac4_transition_restart_failure_restores_opaque_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure during service restart restores previous selector, Aether files, and prior unit."""
    controller = RecordingServiceController()
    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch, controller=controller)
    r1 = _make_release(manager, "1.0.0rc5", "1111111111111111")
    r2 = _make_release(manager, "1.0.0rc5", "2222222222222222")
    _stub_healthy_runtime(manager, monkeypatch, r1)
    _stub_healthy_runtime(manager, monkeypatch, r2)

    manager._switch_runtime_current(manager.store.release_path(r1.release_id))
    manager.store._commit_active(r1, expected_active_release_id=None)
    spec1 = manager.projection_spec(r1)
    profile_home = manager.store.profile_home("morfeo")
    prior_unit_bytes = _generate_valid_hermes_unit(spec1.runtime_current, profile_home)
    spec1.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec1.service_path.write_bytes(prior_unit_bytes)

    # Runner succeeds, but restart raises
    def mock_runner(
        cmd: list[str], env: dict[str, str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "Installed", "")

    manager._hermes_runner = mock_runner

    def failing_restart(spec: ProjectionSpec) -> str:
        raise IntegrityError("simulated restart failure")

    manager._restart_service = failing_restart  # type: ignore[assignment]

    with pytest.raises(IntegrityError, match="simulated restart failure"):
        manager.activate_existing(
            r2.release_id,
            transition_kind="update",
            expected_active_release_id=r1.release_id,
        )

    # Prior state restored
    assert manager.store.active().release_id == r1.release_id
    assert spec1.service_path.read_bytes() == prior_unit_bytes
    assert spec1.runtime_current.resolve() == manager.store.release_path(r1.release_id)


def test_ac4_uninstall_invokes_hermes_gateway_uninstall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normal uninstall asks Hermes CLI to remove its unit instead of unlinking directly."""
    commands_run: list[list[str]] = []

    def mock_runner(
        cmd: list[str], env: dict[str, str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        commands_run.append(cmd)
        if "uninstall" in cmd and "gateway" in cmd:
            unit = (
                Path(env.get("HOME", str(Path.home())))
                / ".config"
                / "systemd"
                / "user"
                / AETHER_GATEWAY_UNIT
            )
            unit.unlink(missing_ok=True)
        return subprocess.CompletedProcess(cmd, 0, "Uninstalled", "")

    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch, hermes_runner=mock_runner)
    record = _make_release(manager, "1.0.0rc5")
    _stub_healthy_runtime(manager, monkeypatch, record)
    manager.store._commit_active(record, expected_active_release_id=None)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    manager._switch_runtime_current(spec.release)

    # Unit file exists on disk
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec.service_path.write_text("[Unit]\nDescription=Test\n", encoding="utf-8")

    result = manager.uninstall(purge=False, confirmed=True)
    assert result.purged is False

    # Verify Hermes CLI was asked to uninstall
    assert any("uninstall" in cmd and "gateway" in cmd for cmd in commands_run)
    assert not spec.service_path.exists()


def test_ac4_rc4_update_rc3_rollback_forward_rc5_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full lifecycle transition cycle: rc4 -> rc5 update -> rc3 rollback -> forward rc5."""
    commands_run: list[str] = []

    def mock_runner(
        cmd: list[str], env: dict[str, str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        commands_run.append(" ".join(cmd))
        runtime_current = Path(cmd[0]).parent.parent.parent
        profile_home = Path(env["HERMES_HOME"])
        unit_data = _generate_valid_hermes_unit(runtime_current, profile_home)
        unit_dest = (
            Path(env.get("HOME", str(Path.home())))
            / ".config"
            / "systemd"
            / "user"
            / AETHER_GATEWAY_UNIT
        )
        assert str(unit_dest).startswith(str(tmp_path)), f"Leaked unit destination: {unit_dest}"
        assert unit_dest != _OPERATOR_UNIT_PATH, "Must not write operator live unit!"
        unit_dest.parent.mkdir(parents=True, exist_ok=True)
        unit_dest.write_bytes(unit_data)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    controller = RecordingServiceController()
    manager, _ = _setup_isolated_manager(
        tmp_path,
        monkeypatch,
        controller=controller,
        hermes_runner=mock_runner,
    )

    rc3 = _make_release(manager, "1.0.0rc3", "3333333333333333")
    rc4 = _make_release(manager, "1.0.0rc4", "4444444444444444", previous_release_id=rc3.release_id)
    rc5 = _make_release(manager, "1.0.0rc5", "5555555555555555", previous_release_id=rc3.release_id)
    _stub_healthy_runtime(manager, monkeypatch, rc3)
    _stub_healthy_runtime(manager, monkeypatch, rc4)
    _stub_healthy_runtime(manager, monkeypatch, rc5)

    # Start at rc4
    manager._switch_runtime_current(manager.store.release_path(rc4.release_id))
    manager.store._commit_active(rc4, expected_active_release_id=None)

    # 1. Update rc4 -> rc5
    selected_rc5 = manager.activate_existing(
        rc5.release_id,
        transition_kind="update",
        expected_active_release_id=rc4.release_id,
    )
    assert selected_rc5.release_id == rc5.release_id
    assert manager.doctor().ready is True
    assert manager.projection_status(rc5)["mismatches"] == []

    # 2. Rollback rc5 -> rc3 (qualification rollback target)
    selected_rc3 = manager.activate_existing(
        rc3.release_id,
        transition_kind="rollback",
        expected_active_release_id=rc5.release_id,
    )
    assert selected_rc3.release_id == rc3.release_id
    assert manager.projection_status(rc3)["mismatches"] == []

    # 3. Forward reactivation rc3 -> rc5
    reactivated_rc5 = manager.activate_existing(
        rc5.release_id,
        transition_kind="update",
        expected_active_release_id=rc3.release_id,
    )
    assert reactivated_rc5.release_id == rc5.release_id
    assert manager.doctor().ready is True
    assert manager.projection_status(rc5)["mismatches"] == []


# =========================================================================
# Real Hermes Generator Integration Lane
# =========================================================================


def test_real_hermes_generator_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Integrate the authentic Hermes generator to prove genuinely generated units pass semantic doctor."""
    hermes_cache = _OPERATOR_HOME / ".cache" / "aether-agents" / "hermes" / "v2026.8.18"
    if not hermes_cache.is_dir():
        pytest.skip(f"Hermes baseline checkout not found at {hermes_cache}")

    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch)
    record = _make_release(manager, "1.0.0rc5")
    _stub_healthy_runtime(manager, monkeypatch, record)
    manager.store._commit_active(record, expected_active_release_id=None)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    manager._switch_runtime_current(spec.release)

    # Set up environment for authentic Hermes generator
    profile_home = manager.store.profile_home("morfeo")
    monkeypatch.syspath_prepend(str(hermes_cache))
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setenv("VIRTUAL_ENV", str(spec.runtime_current / "venv"))

    # Import real generator
    from hermes_cli import gateway as hermes_gateway
    from hermes_cli.gateway import generate_systemd_unit, get_service_name

    monkeypatch.setattr(
        hermes_gateway, "get_python_path", lambda: f"{spec.runtime_current}/venv/bin/python"
    )
    monkeypatch.setattr(hermes_gateway, "_detect_venv_dir", lambda: spec.runtime_current / "venv")

    assert get_service_name() == "hermes-gateway-morfeo"
    real_unit_text = generate_systemd_unit()

    # The authentic unit must be accepted by semantic doctor
    spec.service_path.parent.mkdir(parents=True, exist_ok=True)
    spec.service_path.write_text(real_unit_text, encoding="utf-8")

    status = manager.projection_status(record)
    assert status["mismatches"] == [], f"Genuine unit had mismatches: {status['mismatches']}"
    assert manager.doctor().ready is True


def test_isolation_guarantee_no_operator_state_touched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves that isolated fixtures never touch live operator files or live XDG destinations."""
    live_unit_before = (
        _OPERATOR_UNIT_PATH.read_bytes()
        if _OPERATOR_UNIT_PATH.is_file() and not _OPERATOR_UNIT_PATH.is_symlink()
        else None
    )

    controller = RecordingServiceController()
    manager, _ = _setup_isolated_manager(tmp_path, monkeypatch, controller=controller)
    record = _make_release(manager, "1.0.0rc5")
    _stub_healthy_runtime(manager, monkeypatch, record)
    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)
    assert tmp_path in spec.service_path.parents
    assert tmp_path in spec.launcher_path.parents
    assert tmp_path in spec.desktop_path.parents

    live_unit_after = (
        _OPERATOR_UNIT_PATH.read_bytes()
        if _OPERATOR_UNIT_PATH.is_file() and not _OPERATOR_UNIT_PATH.is_symlink()
        else None
    )
    assert live_unit_before == live_unit_after
