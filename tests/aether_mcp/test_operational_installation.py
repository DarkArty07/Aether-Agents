"""TDD coverage for the default-off local operational installation."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "aether_mcp"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SCRIPTS))
import installation  # noqa: E402


def _fake_appimage(tmp_path: Path) -> Path:
    image = tmp_path / "Orca.AppImage"
    image.write_text(
        "#!/bin/sh\n"
        "mkdir -p squashfs-root/resources/app.asar.unpacked/out/cli\n"
        "touch squashfs-root/resources/app.asar.unpacked/out/cli/index.js\n"
        'printf \'#!/bin/sh\\ncase "$*" in *"worktree ps"*) echo \'\\\'\'{"ok":true,"result":{"worktrees":[],"totalCount":0,"truncated":false}}\'\\\'\';; *) echo \'\\\'\'{"ok":true,"result":{"runtime":{"appVersion":"1.4.167","state":"ready","reachable":true}}}\'\\\'\';; esac\\n\' > squashfs-root/AppRun\nchmod +x squashfs-root/AppRun\n'
    )
    image.chmod(0o700)
    return image


def _qualified_profile(root: Path) -> Path:
    profile = root / "profile"
    (profile / "hermes-home").mkdir(parents=True)
    for name in ("config", "cache", "data", "state"):
        (profile / "xdg" / name).mkdir(parents=True)
    return profile


def _fake_uv(tmp_path: Path) -> Path:
    uv = tmp_path / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = venv ]; then mkdir -p "$3/bin"; printf \'#!/bin/sh\\nexec python3 "$@"\\n\' > "$3/bin/python"; chmod +x "$3/bin/python"; fi\n'
        'if [ "$1" = pip ]; then d=$(dirname "$4"); printf \'#!/bin/sh\\nexec python3 -m aether_mcp "$@"\\n\' > "$d/aether-mcp"; chmod +x "$d/aether-mcp"; fi\n'
    )
    uv.chmod(0o700)
    return uv


def _installation_record(tmp_path: Path) -> installation.Installation:
    home = tmp_path / "home"
    base = home / ".aether-mcp"
    profile = tmp_path / "profile"
    return installation.Installation(
        project_root=str(tmp_path / "project"),
        hermes_home=str(home),
        config_path=str(home / "config.yaml"),
        appimage=str(tmp_path / "Orca.AppImage"),
        appimage_sha256="a" * 64,
        profile_root=str(profile),
        profile_id="default",
        orca_hermes_home=str(profile / "hermes-home"),
        orca_xdg_config_home=str(profile / "xdg" / "config"),
        orca_xdg_cache_home=str(profile / "xdg" / "cache"),
        orca_xdg_data_home=str(profile / "xdg" / "data"),
        orca_xdg_state_home=str(profile / "xdg" / "state"),
        extraction=str(base / "orca" / "1.4.167"),
        wrapper=str(base / "bin" / "orca-public-cli"),
        venv=str(base / "venv"),
        launcher=str(base / "bin" / "aether-mcp"),
        state_root=str(home / ".aether-mcp-state"),
        backup=str(base / "backups" / "config.yaml.pre-aether-mcp"),
        original_config_sha256="b" * 64,
        registered_config_sha256="c" * 64,
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        catalog_digest="d" * 64,
        tool_count=15,
    )


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _process_record(pid: int, ppid: int, *argv: str, executable: str | None = None) -> installation.ProcessRecord:
    return installation.ProcessRecord(
        pid=pid,
        ppid=ppid,
        pgid=pid,
        session_id=pid,
        start_time=pid * 10,
        argv=tuple(argv),
        executable=executable,
    )


def _setup_fake_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, image: Path | None = None
) -> tuple[installation.Installation, Path]:
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (home / "config.yaml").write_text("model: isolated\n")
    profile = _qualified_profile(tmp_path)
    image = image or _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "f" * 64})())}),
    )
    result = installation.setup(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    return result, home


def test_setup_stores_config_backup_with_private_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    config = home / "config.yaml"
    config.write_text("model: isolated\n")
    config.chmod(0o644)
    project = tmp_path / "project"
    project.mkdir()
    profile = _qualified_profile(tmp_path)
    image = _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "f" * 64})())}),
    )

    result = installation.setup(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )

    assert Path(result.backup).stat().st_mode & 0o777 == 0o600


def test_setup_status_and_rollback_are_idempotent_and_preserve_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, project, profile = tmp_path / "hermes", tmp_path / "project", tmp_path / "profile"
    for directory in (home, project, profile):
        directory.mkdir()
    original = "model: secret-value\nmcp_servers:\n  olympus:\n    enabled: true\n"
    (home / "config.yaml").write_text(original)
    image = _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "a" * 64})())}),
    )
    result = installation.setup(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    assert result.tool_count == 15
    assert result.profile_root == str(profile)
    configured = (home / "config.yaml").read_text()
    assert "olympus" in configured and "aether_mcp" in configured and "enabled: false" in configured
    assert (
        installation.setup(
            project_root=str(project),
            hermes_home=str(home),
            appimage=str(image),
            profile_root=str(profile),
            profile_id="default",
            repo_selector="path:/project",
            base_ref="main",
            coordinator_handle="term-test",
            uv=str(_fake_uv(tmp_path)),
        )
        == result
    )
    observed = installation.status(str(home))
    assert observed["registration"] == {"present": True, "enabled": False}
    assert observed["orca"]["profile_root"] == str(profile)
    wrapper = Path(result.wrapper).read_text()
    assert "ELECTRON_RUN_AS_NODE=1" in wrapper and "AppRun" in wrapper and "node" not in wrapper.split("exec", 1)[1]
    launcher = Path(result.launcher).read_text()
    assert str(result.venv + "/bin/python") in launcher
    assert "unset APPIMAGE_EXTRACT_AND_RUN" in wrapper
    assert "secret-value" not in str(observed)
    assert installation.rollback(str(home))["config_restored"] is True
    assert (home / "config.yaml").read_text() == original
    assert Path(result.state_root).is_dir()
    assert installation.rollback(str(home))["already_rolled_back"] is True


def test_setup_rejects_unqualified_appimage_before_config_mutation(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.yaml").write_text("x: y\n")
    project = tmp_path / "project"
    project.mkdir()
    profile = tmp_path / "profile"
    profile.mkdir()
    with pytest.raises(installation.InstallError, match="APPIMAGE_DIGEST_MISMATCH"):
        installation.setup(
            project_root=str(project),
            hermes_home=str(home),
            appimage=str(_fake_appimage(tmp_path)),
            profile_root=str(profile),
            profile_id="default",
            repo_selector="path:/project",
            base_ref="main",
            coordinator_handle="term-test",
        )
    assert (home / "config.yaml").read_text() == "x: y\n"


def test_setup_persists_explicit_profile_id_and_qualified_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, project = tmp_path / "hermes", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (home / "config.yaml").write_text("x: y\n")
    profile = _qualified_profile(tmp_path)
    image = _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "d" * 64})())}),
    )
    result = installation.setup(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    manifest = __import__("json").loads(result.manifest_path.read_text())
    assert manifest["profile_id"] == "default"
    assert manifest["orca_hermes_home"] == str(profile / "hermes-home")
    assert manifest["orca_xdg_config_home"] == str(profile / "xdg" / "config")
    launcher = Path(result.launcher).read_text()
    assert 'AETHER_PROFILE="default"' in launcher


@pytest.mark.parametrize("profile_id", ["", " ", "a/b", "../x", "bad alias"])
def test_setup_rejects_invalid_profile_id_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile_id: str
) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    original = "x: y\n"
    (home / "config.yaml").write_text(original)
    image = _fake_appimage(tmp_path)
    profile = _qualified_profile(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    with pytest.raises(installation.InstallError, match="INVALID_PROFILE_ID"):
        installation.setup(
            project_root=str(project),
            hermes_home=str(home),
            appimage=str(image),
            profile_root=str(profile),
            profile_id=profile_id,
            repo_selector="path:/project",
            base_ref="main",
            coordinator_handle="term-test",
            uv=str(_fake_uv(tmp_path)),
        )
    assert (home / "config.yaml").read_text() == original


def test_setup_conflicts_when_profile_id_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (home / "config.yaml").write_text("x: y\n")
    image = _fake_appimage(tmp_path)
    profile = _qualified_profile(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "e" * 64})())}),
    )
    kwargs = dict(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    installation.setup(**kwargs, profile_id="default")
    with pytest.raises(installation.InstallError, match="INSTALLATION_CONFLICT"):
        installation.setup(**kwargs, profile_id="other")


@pytest.mark.anyio
async def test_real_noneditable_install_handshake_does_not_touch_active_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The package is installed from its source tree, never as editable code."""
    if not __import__("shutil").which("uv"):
        pytest.skip("uv is required for the operational installation gate")
    home, profile = tmp_path / "hermes", tmp_path / "profile"
    home.mkdir()
    profile.mkdir()
    active = home / "config.yaml"
    active.write_text("mcp_servers:\n  olympus:\n    enabled: true\n")
    image = _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    result = installation.setup(
        project_root=str(ROOT),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector=f"path:{ROOT}",
        base_ref="main",
        coordinator_handle="term-test",
    )
    parameters = StdioServerParameters(command=result.launcher, args=[], env={"PATH": __import__("os").environ["PATH"]})
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
    assert len(listed.tools) == 15
    checked = await __import__("asyncio").to_thread(installation.doctor, str(home))
    assert checked["tool_count"] == 15 and checked["orca_ready"] is True and checked["ok"] is True
    assert "olympus" in active.read_text() and "enabled: false" in active.read_text()


def test_activation_changes_only_owned_flag_and_keeps_atomic_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, project, profile = tmp_path / "home", tmp_path / "project", tmp_path / "profile"
    for path in (home, project, profile):
        path.mkdir()
    original = "model: x\nmcp_servers:\n  other:\n    enabled: true\n"
    (home / "config.yaml").write_text(original)
    image = _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "b" * 64})())}),
    )
    result = installation.setup(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    before = (home / "config.yaml").read_text()
    activated = installation.activate(str(home))
    after = (home / "config.yaml").read_text()
    assert activated["changed"] is True and "other:\n    enabled: true" in after
    assert installation.status(str(home))["registration"] == {"present": True, "enabled": True}
    assert Path(activated["backup"]).read_text() == before
    assert Path(activated["backup"]).stat().st_mode & 0o777 == 0o600
    assert installation.activate(str(home))["changed"] is False
    assert installation.activate(str(home), enabled=False)["changed"] is True
    assert installation.rollback(str(home))["preserved_state_root"] == result.state_root


def test_doctor_rejects_false_positive_orca_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, project, profile = tmp_path / "home", tmp_path / "project", tmp_path / "profile"
    for path in (home, project, profile):
        path.mkdir()
    (home / "config.yaml").write_text("x: y\n")
    image = _fake_appimage(tmp_path)
    monkeypatch.setattr(installation, "EXPECTED_APPIMAGE_SHA256", hashlib.sha256(image.read_bytes()).hexdigest())
    monkeypatch.setattr(
        installation,
        "OrcaCatalog",
        type("Catalog", (), {"bundled": staticmethod(lambda: type("C", (), {"digest": "c" * 64})())}),
    )
    result = installation.setup(
        project_root=str(project),
        hermes_home=str(home),
        appimage=str(image),
        profile_root=str(profile),
        profile_id="default",
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    completed = __import__("subprocess").CompletedProcess([], 0, b'{"ok": true, "result": {}}', b"")
    monkeypatch.setattr(installation.subprocess, "run", lambda *args, **kwargs: completed)
    assert installation._parse_orca_status(completed) is False
    assert result.profile_root == str(profile)


def test_inventory_tracks_exact_root_descendants_but_not_prefix_lookalikes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _installation_record(tmp_path)
    monkeypatch.setattr(installation, "_ancestor_pids", lambda: set())
    monkeypatch.setattr(
        installation,
        "_process_snapshot",
        lambda: [
            _process_record(101, 1, record.launcher),
            _process_record(102, 101, "sleep", "60"),
            _process_record(103, 1, record.launcher + "-foreign"),
        ],
    )

    assert {item["pid"] for item in installation._owned_processes(record)} == {101, 102}


def test_run_owned_reaps_successful_orphan_descendant(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child.pid"
    command = tmp_path / "leaky-installer"
    command.write_text(f"#!/bin/sh\nsleep 60 </dev/null >/dev/null 2>&1 &\necho $! > {child_pid_file}\nexit 0\n")
    command.chmod(0o700)
    child_pid = 0
    try:
        with pytest.raises(installation.InstallError, match="INSTALLER_CHILD_SURVIVOR"):
            installation._run_owned((str(command),), timeout=5)
        deadline = time.monotonic() + 2
        while not child_pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        child_pid = int(child_pid_file.read_text())
        assert not _pid_exists(child_pid)
    finally:
        if child_pid and _pid_exists(child_pid):
            os.kill(child_pid, signal.SIGKILL)


def test_terminate_owned_skips_reused_pid_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(installation, "_process_start_time", lambda _pid: 999, raising=False)
    monkeypatch.setattr(installation.os, "kill", lambda pid, sig: signals.append((pid, sig)))

    installation._terminate_owned_processes([{"pid": 987654, "ppid": 1, "start_time": 123}])

    assert signals == []


def test_process_snapshot_captures_reusable_pid_identity() -> None:
    snapshot = installation._process_snapshot()
    assert snapshot is not None
    current = next(record for record in snapshot if record.pid == os.getpid())
    assert current.start_time == installation._process_start_time(os.getpid())
    assert current.argv


def test_inventory_reports_plausible_opaque_process_as_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _installation_record(tmp_path)
    opaque = installation.ProcessRecord(
        pid=404,
        ppid=1,
        pgid=404,
        session_id=404,
        start_time=4040,
        argv=(),
        executable=None,
        command_name="python3",
        inspectable=False,
    )
    monkeypatch.setattr(installation, "_ancestor_pids", lambda: set())
    monkeypatch.setattr(installation, "_process_snapshot", lambda: [opaque])
    monkeypatch.setattr(
        installation.subprocess,
        "run",
        lambda *args, **kwargs: __import__("subprocess").CompletedProcess([], 0, b'{"ok":true}', b""),
    )

    inventory = installation._resource_inventory(record)

    assert any(entry.get("state") == "UNKNOWN" and entry.get("unattributed_count") == 1 for entry in inventory)
    assert installation._owned_processes(record) is None


def test_inventory_rejects_false_positive_worktree_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _installation_record(tmp_path)
    monkeypatch.setattr(installation, "_process_snapshot", lambda: [])
    monkeypatch.setattr(
        installation.subprocess,
        "run",
        lambda *args, **kwargs: __import__("subprocess").CompletedProcess([], 0, b'{"ok":true,"result":{}}', b""),
    )

    inventory = installation._resource_inventory(record)

    assert inventory[0] == {"source": "orca_worktree_ps", "performed": True, "ok": False}


def test_extraction_does_not_inherit_appimage_extract_and_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = _fake_appimage(tmp_path)
    image.write_text(
        image.read_text().replace(
            "#!/bin/sh\n",
            '#!/bin/sh\nif [ "${APPIMAGE_EXTRACT_AND_RUN+x}" = x ]; then exit 77; fi\n',
            1,
        )
    )
    monkeypatch.setenv("APPIMAGE_EXTRACT_AND_RUN", "1")

    result, home = _setup_fake_install(tmp_path, monkeypatch, image=image)

    assert Path(result.extraction).is_dir()
    assert installation.rollback(str(home))["config_restored"] is True


def test_run_owned_timeout_reaps_descendant(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child.pid"
    command = tmp_path / "timed-out-installer"
    command.write_text(f"#!/bin/sh\nsleep 60 &\necho $! > {child_pid_file}\nwait\n")
    command.chmod(0o700)
    child_pid = 0
    try:
        with pytest.raises(installation.InstallError, match="INSTALLER_TIMEOUT"):
            installation._run_owned((str(command),), timeout=0.1)
        child_pid = int(child_pid_file.read_text())
        deadline = time.monotonic() + 2
        while _pid_exists(child_pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not _pid_exists(child_pid)
    finally:
        if child_pid and _pid_exists(child_pid):
            os.kill(child_pid, signal.SIGKILL)


def test_run_owned_rejects_unbounded_output(tmp_path: Path) -> None:
    command = tmp_path / "noisy-installer"
    command.write_text("#!/bin/sh\npython3 -c 'import sys; sys.stdout.write(\"x\" * 1048577)'\n")
    command.chmod(0o700)

    with pytest.raises(installation.InstallError, match="INSTALLER_OUTPUT_TOO_LARGE"):
        installation._run_owned((str(command),), timeout=5)


def test_wrapper_overrides_poisoned_ambient_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, _home = _setup_fake_install(tmp_path, monkeypatch)
    probe = tmp_path / "wrapper.env"
    Path(result.extraction, "AppRun").write_text(
        "#!/bin/sh\n"
        "printf 'HOME=%s\\nHERMES_HOME=%s\\nXDG_CONFIG_HOME=%s\\nXDG_CACHE_HOME=%s\\n"
        "XDG_DATA_HOME=%s\\nXDG_STATE_HOME=%s\\n' \"$HOME\" \"$HERMES_HOME\" \"$XDG_CONFIG_HOME\" "
        "\"$XDG_CACHE_HOME\" \"$XDG_DATA_HOME\" \"$XDG_STATE_HOME\" > \"$ORCA_ENV_PROBE\"\n"
        "echo '{\"ok\":true,\"result\":{\"runtime\":{\"appVersion\":\"1.4.167\",\"state\":\"ready\",\"reachable\":true}}}'\n"
    )
    Path(result.extraction, "AppRun").chmod(0o700)
    environment = dict(os.environ)
    for key in ("HOME", "HERMES_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        environment[key] = str(tmp_path / "foreign" / key.lower())
    environment["ORCA_ENV_PROBE"] = str(probe)

    completed = subprocess.run((result.wrapper, "status", "--json"), env=environment, capture_output=True, check=False)

    observed = dict(line.split("=", 1) for line in probe.read_text().splitlines())
    assert completed.returncode == 0
    assert observed == {
        "HOME": result.profile_root,
        "HERMES_HOME": result.orca_hermes_home,
        "XDG_CONFIG_HOME": result.orca_xdg_config_home,
        "XDG_CACHE_HOME": result.orca_xdg_cache_home,
        "XDG_DATA_HOME": result.orca_xdg_data_home,
        "XDG_STATE_HOME": result.orca_xdg_state_home,
    }
    launcher = Path(result.launcher).read_text()
    assert f'export HERMES_HOME="{result.hermes_home}"' in launcher
    assert result.orca_hermes_home not in launcher


def test_rollback_terminates_owned_tree_and_preserves_prefix_lookalike(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, home = _setup_fake_install(tmp_path, monkeypatch)
    child_pid_file = tmp_path / "owned-child.pid"
    owned_script = Path(result.venv) / "owned-tree.py"
    owned_script.write_text(
        "import subprocess,sys,time\n"
        "child=subprocess.Popen(['sleep','60'])\n"
        "open(sys.argv[1],'w').write(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    foreign_script = tmp_path / "aether-mcp-foreign"
    foreign_script.write_text("#!/bin/sh\nsleep 60\n")
    foreign_script.chmod(0o700)
    owned = subprocess.Popen((sys.executable, str(owned_script), str(child_pid_file)))
    foreign = subprocess.Popen((str(foreign_script),))
    child_pid = 0
    try:
        deadline = time.monotonic() + 2
        while not child_pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        child_pid = int(child_pid_file.read_text())

        rolled_back = installation.rollback(str(home))

        assert rolled_back["config_restored"] is True
        assert owned.wait(timeout=2) in (-signal.SIGTERM, -signal.SIGKILL)
        deadline = time.monotonic() + 2
        while _pid_exists(child_pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not _pid_exists(child_pid)
        assert foreign.poll() is None
    finally:
        for process in (owned, foreign):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
        if child_pid and _pid_exists(child_pid):
            os.kill(child_pid, signal.SIGKILL)


def test_inventory_excludes_invoking_ancestor_even_with_owned_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _installation_record(tmp_path)
    monkeypatch.setattr(installation, "_ancestor_pids", lambda: {701})
    monkeypatch.setattr(
        installation,
        "_process_snapshot",
        lambda: [_process_record(701, 1, record.launcher)],
    )

    assert installation._owned_processes(record) == []


def test_inventory_reports_shared_profile_orca_as_provider_not_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _installation_record(tmp_path)
    monkeypatch.setattr(installation, "_ancestor_pids", lambda: set())
    monkeypatch.setattr(
        installation,
        "_process_snapshot",
        lambda: [_process_record(702, 1, "orca", f"--profile={record.profile_root}")],
    )
    monkeypatch.setattr(
        installation.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 0, b'{"ok":true,"result":{"worktrees":[],"totalCount":0,"truncated":false}}', b""
        ),
    )

    inventory = installation._resource_inventory(record)
    processes = next(entry for entry in inventory if entry["source"] == "processes" and entry["performed"])

    assert processes["owned"] == []
    assert processes["provider"] == [{"pid": 702, "ppid": 1, "classification": "shared_orca_provider"}]


def test_rollback_cleanup_failure_keeps_manifest_for_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, home = _setup_fake_install(tmp_path, monkeypatch)
    survivor = {"pid": 703, "ppid": 1, "start_time": 7030}
    monkeypatch.setattr(installation, "_owned_processes", lambda _record: [survivor])
    monkeypatch.setattr(installation, "_terminate_owned_processes", lambda _owned: None)

    with pytest.raises(installation.InstallError, match="OWNED_PROCESS_CLEANUP_FAILED"):
        installation.rollback(str(home))

    assert result.manifest_path.is_file()
    assert Path(result.wrapper).is_file()
    assert "aether_mcp" not in (home / "config.yaml").read_text()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
