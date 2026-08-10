"""Idempotent, default-off local Aether MCP installation primitives.

The manifest is deliberately the ownership boundary: no command acts outside its
recorded paths, and configuration is restored byte-for-byte when untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aether_mcp.catalog import OrcaCatalog
from aether_mcp.protocol import CALLABLE_TOOL_NAMES

EXPECTED_APPIMAGE_SHA256 = "813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33"
INSTALL_VERSION = "0.23.0.dev0"
INSTALL_NAME = "aether-mcp"


class InstallError(RuntimeError):
    """Typed, secret-safe operational installation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _safe_path(value: str, *, directory: bool = False) -> Path:
    path = Path(value)
    if not path.is_absolute() or path.is_symlink() or (directory and path.exists() and not path.is_dir()):
        raise InstallError("INVALID_PATH")
    return path


def _config_entry(launcher: Path) -> str:
    return f"  aether_mcp:\n    command: {json.dumps(str(launcher))}\n    args: []\n    enabled: false\n"


def add_registration(original: str, launcher: Path) -> str:
    """Add exactly one entry without reserializing unrelated YAML."""
    lines = original.splitlines(keepends=True)
    top = [index for index, line in enumerate(lines) if line and not line[0].isspace() and line.rstrip().endswith(":")]
    starts = [index for index, line in enumerate(lines) if line == "mcp_servers:\n" or line.rstrip() == "mcp_servers:"]
    if starts:
        start = starts[0]
        end = next((index for index in top if index > start), len(lines))
        if any(line.startswith("  aether_mcp:") for line in lines[start + 1 : end]):
            raise InstallError("REGISTRATION_CONFLICT")
        lines[end:end] = _config_entry(launcher).splitlines(keepends=True)
        return "".join(lines)
    suffix = "" if not original or original.endswith("\n") else "\n"
    return original + suffix + "mcp_servers:\n" + _config_entry(launcher)


def remove_registration(current: str) -> str:
    lines = current.splitlines(keepends=True)
    start = next((index for index, line in enumerate(lines) if line.rstrip() == "mcp_servers:"), None)
    if start is None:
        return current
    top = [index for index, line in enumerate(lines) if line and not line[0].isspace() and line.rstrip().endswith(":")]
    end = next((index for index in top if index > start), len(lines))
    item = next((index for index in range(start + 1, end) if lines[index].startswith("  aether_mcp:")), None)
    if item is None:
        return current
    item_end = next(
        (
            index
            for index in range(item + 1, end)
            if lines[index].startswith("  ") and not lines[index].startswith("    ")
        ),
        end,
    )
    del lines[item:item_end]
    if not any(
        line.startswith("  ") and not line.startswith("    ") for line in lines[start + 1 : end - (item_end - item)]
    ):
        del lines[start : start + 1]
    return "".join(lines)


@dataclass(frozen=True)
class Installation:
    project_root: str
    hermes_home: str
    config_path: str
    appimage: str
    appimage_sha256: str
    extraction: str
    wrapper: str
    venv: str
    launcher: str
    state_root: str
    backup: str
    original_config_sha256: str
    registered_config_sha256: str
    repo_selector: str
    base_ref: str
    coordinator_handle: str
    catalog_digest: str
    tool_count: int
    version: str = INSTALL_VERSION

    @property
    def manifest_path(self) -> Path:
        return Path(self.hermes_home) / ".aether-mcp" / "installation.json"

    def write(self) -> None:
        _atomic_write(self.manifest_path, json.dumps(asdict(self), sort_keys=True, indent=2) + "\n")

    @classmethod
    def load(cls, hermes_home: Path) -> "Installation":
        try:
            raw = json.loads((hermes_home / ".aether-mcp" / "installation.json").read_text())
            return cls(**raw)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InstallError("INSTALLATION_NOT_FOUND") from exc


def setup(
    *,
    project_root: str,
    hermes_home: str,
    appimage: str,
    profile_root: str,
    repo_selector: str,
    base_ref: str,
    coordinator_handle: str,
    uv: str = "uv",
    timeout_ms: int = 600000,
) -> Installation:
    root, home, image, profile = (
        _safe_path(project_root, directory=True),
        _safe_path(hermes_home, directory=True),
        _safe_path(appimage),
        _safe_path(profile_root, directory=True),
    )
    if not root.is_dir() or not home.is_dir() or not image.is_file() or not profile.is_dir():
        raise InstallError("INVALID_PATH")
    observed = digest(image)
    if observed != EXPECTED_APPIMAGE_SHA256:
        raise InstallError("APPIMAGE_DIGEST_MISMATCH")
    if not repo_selector or not base_ref or not coordinator_handle:
        raise InstallError("INVALID_INPUT")
    existing_path = home / ".aether-mcp" / "installation.json"
    if existing_path.exists():
        existing = Installation.load(home)
        if existing.appimage_sha256 == observed and existing.config_path == str(home / "config.yaml"):
            return existing
        raise InstallError("INSTALLATION_CONFLICT")
    config = home / "config.yaml"
    if not config.is_file():
        raise InstallError("CONFIG_NOT_FOUND")
    base = home / ".aether-mcp"
    extraction = base / "orca" / "1.4.167"
    wrapper = base / "bin" / "orca-public-cli"
    venv = base / "venv"
    launcher = base / "bin" / "aether-mcp"
    state_root = base / "state"
    backup = base / "backups" / "config.yaml.pre-aether-mcp"
    original = config.read_text(encoding="utf-8")
    _atomic_write(backup, original, stat.S_IMODE(config.stat().st_mode))
    try:
        extraction.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not extraction.exists():
            temporary = Path(tempfile.mkdtemp(prefix="aether-mcp-extract-", dir=extraction.parent))
            try:
                subprocess.run(
                    (str(image), "--appimage-extract"), cwd=temporary, check=True, timeout=120, capture_output=True
                )
                extracted = temporary / "squashfs-root"
                if not extracted.is_dir():
                    raise InstallError("APPIMAGE_EXTRACTION_FAILED")
                os.replace(extracted, extraction)
            finally:
                shutil.rmtree(temporary, ignore_errors=True)
        public = extraction / "resources" / "app.asar.unpacked" / "out" / "cli" / "index.js"
        if not public.is_file():
            raise InstallError("APPIMAGE_EXTRACTION_FAILED")
        node = shutil.which("node")
        if node is None:
            raise InstallError("PUBLIC_CLI_UNAVAILABLE")
        bootstrap = (
            '(async()=>{try{const path=require("path");const appDir=process.env.APPDIR;'
            'const cli=path.join(appDir,"resources","app.asar.unpacked","out","cli","index.js");'
            "await Promise.resolve(require(cli).main(process.argv.slice(1)));}"
            "catch(error){console.error(error&&error.stack?error.stack:String(error));process.exit(1);}})();"
        )
        _atomic_write(
            wrapper,
            f'#!/bin/sh\nexport APPDIR={json.dumps(str(extraction))}\nexec {json.dumps(node)} -e {json.dumps(bootstrap)} "$@"\n',
            0o700,
        )
        subprocess.run((uv, "venv", "--clear", str(venv)), check=True, timeout=120, capture_output=True)
        subprocess.run(
            (uv, "pip", "install", "--python", str(venv / "bin" / "python"), str(root)),
            check=True,
            timeout=300,
            capture_output=True,
        )
        catalog = OrcaCatalog.bundled()
        environment = {
            "AETHER_STATE_ROOT": str(state_root),
            "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
            "HERMES_HOME": str(home),
            "AETHER_PROFILE": profile.name,
            "AETHER_SESSION_ID": "${AETHER_SESSION_ID}",
            "AETHER_ORCA_CLI": str(wrapper),
            "AETHER_ORCA_COORDINATOR_HANDLE": coordinator_handle,
            "AETHER_ORCA_REPO_SELECTOR": repo_selector,
            "AETHER_ORCA_BASE_REF": base_ref,
            "AETHER_ORCA_BINDING_DIGEST": catalog.digest,
            "AETHER_ORCA_TIMEOUT_MS": str(timeout_ms),
        }
        exports = "\n".join(
            f"export {key}={json.dumps(value)}" for key, value in environment.items() if key != "AETHER_SESSION_ID"
        )
        _atomic_write(
            launcher,
            "#!/bin/sh\nset -eu\nexport AETHER_SESSION_ID=\"$(python3 -c 'import uuid; print(uuid.uuid4())')\"\n"
            + exports
            + f"\nexec {json.dumps(str(venv / 'bin' / 'aether-mcp'))}\n",
            0o700,
        )
        updated = add_registration(original, launcher)
        _atomic_write(config, updated, stat.S_IMODE(config.stat().st_mode))
        installation = Installation(
            str(root),
            str(home),
            str(config),
            str(image),
            observed,
            str(extraction),
            str(wrapper),
            str(venv),
            str(launcher),
            str(state_root),
            str(backup),
            hashlib.sha256(original.encode()).hexdigest(),
            hashlib.sha256(updated.encode()).hexdigest(),
            repo_selector,
            base_ref,
            coordinator_handle,
            catalog.digest,
            len(CALLABLE_TOOL_NAMES),
        )
        installation.write()
        return installation
    except Exception:
        if config.read_text(encoding="utf-8") != original:
            _atomic_write(config, original, stat.S_IMODE(config.stat().st_mode))
        shutil.rmtree(base, ignore_errors=True)
        raise


def status(home: str) -> dict[str, Any]:
    installation = Installation.load(_safe_path(home, directory=True))
    config = Path(installation.config_path).read_text(encoding="utf-8")
    return {
        "ok": True,
        "version": installation.version,
        "registration": {"present": "  aether_mcp:" in config, "enabled": False},
        "paths": {
            key: getattr(installation, key)
            for key in ("config_path", "venv", "launcher", "state_root", "wrapper", "extraction")
        },
        "hashes": {"appimage": installation.appimage_sha256, "catalog": installation.catalog_digest},
        "tool_count": installation.tool_count,
        "orca": {"profile_root": installation.extraction, "ready": Path(installation.wrapper).is_file()},
        "state_ready": Path(installation.state_root).is_dir(),
    }


def rollback(home: str) -> dict[str, Any]:
    home_path = _safe_path(home, directory=True)
    installation = Installation.load(home_path)
    config = Path(installation.config_path)
    current = config.read_text(encoding="utf-8")
    registered_hash = hashlib.sha256(current.encode()).hexdigest()
    backup = Path(installation.backup).read_text(encoding="utf-8")
    restored = backup if registered_hash == installation.registered_config_sha256 else remove_registration(current)
    _atomic_write(config, restored, stat.S_IMODE(config.stat().st_mode))
    shutil.rmtree(home_path / ".aether-mcp", ignore_errors=True)
    return {
        "ok": True,
        "config_restored": hashlib.sha256(restored.encode()).hexdigest() == installation.original_config_sha256,
    }


def doctor(home: str, *, timeout_seconds: float = 15.0) -> dict[str, Any]:
    """Exercise the installed stdio endpoint and only public Orca status."""
    installation = Installation.load(_safe_path(home, directory=True))
    for path in (installation.launcher, installation.wrapper, installation.venv):
        if not Path(path).exists():
            raise InstallError("INSTALLATION_INCOMPLETE")
    try:
        import asyncio

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def handshake() -> int:
            parameters = StdioServerParameters(
                command=installation.launcher, args=[], env={"PATH": os.environ.get("PATH", "")}
            )
            async with asyncio.timeout(timeout_seconds):
                async with stdio_client(parameters) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return len(result.tools)

        tool_count = asyncio.run(handshake())
    except Exception as exc:
        raise InstallError("MCP_HANDSHAKE_FAILED") from exc
    if tool_count != len(CALLABLE_TOOL_NAMES):
        raise InstallError("MCP_TOOL_INVENTORY_MISMATCH")
    try:
        completed = subprocess.run(
            (installation.wrapper, "status", "--json"), capture_output=True, check=False, timeout=30
        )
        orca_ready = completed.returncode == 0 and len(completed.stdout) <= 1_048_576
    except (OSError, subprocess.SubprocessError):
        orca_ready = False
    owned_root = Path(installation.hermes_home) / ".aether-mcp"
    permissions_ok = all(not (Path(path).stat().st_mode & 0o077) for path in (owned_root, installation.launcher))
    return {
        "ok": orca_ready and permissions_ok,
        "tool_count": tool_count,
        "orca_ready": orca_ready,
        "state_permissions_ok": permissions_ok,
        "stale_resources": [],
    }
