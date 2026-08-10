"""TDD coverage for the default-off local operational installation."""

from __future__ import annotations

import hashlib
import sys
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
        "printf '#!/bin/sh\\necho {}\\n' > squashfs-root/orca-ide\nchmod +x squashfs-root/orca-ide\n"
    )
    image.chmod(0o700)
    return image


def _fake_uv(tmp_path: Path) -> Path:
    uv = tmp_path / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = venv ]; then mkdir -p "$3/bin"; printf \'#!/bin/sh\\nexec python3 "$@"\\n\' > "$3/bin/python"; chmod +x "$3/bin/python"; fi\n'
        'if [ "$1" = pip ]; then d=$(dirname "$4"); printf \'#!/bin/sh\\nexec python3 -m aether_mcp "$@"\\n\' > "$d/aether-mcp"; chmod +x "$d/aether-mcp"; fi\n'
    )
    uv.chmod(0o700)
    return uv


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
        repo_selector="path:/project",
        base_ref="main",
        coordinator_handle="term-test",
        uv=str(_fake_uv(tmp_path)),
    )
    assert result.tool_count == 15
    configured = (home / "config.yaml").read_text()
    assert "olympus" in configured and "aether_mcp" in configured and "enabled: false" in configured
    assert (
        installation.setup(
            project_root=str(project),
            hermes_home=str(home),
            appimage=str(image),
            profile_root=str(profile),
            repo_selector="path:/project",
            base_ref="main",
            coordinator_handle="term-test",
            uv=str(_fake_uv(tmp_path)),
        )
        == result
    )
    observed = installation.status(str(home))
    assert observed["registration"] == {"present": True, "enabled": False}
    assert "secret-value" not in str(observed)
    assert installation.rollback(str(home))["config_restored"] is True
    assert (home / "config.yaml").read_text() == original


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
            repo_selector="path:/project",
            base_ref="main",
            coordinator_handle="term-test",
        )
    assert (home / "config.yaml").read_text() == "x: y\n"


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
    assert (await __import__("asyncio").to_thread(installation.doctor, str(home)))["tool_count"] == 15
    assert "olympus" in active.read_text() and "enabled: false" in active.read_text()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
