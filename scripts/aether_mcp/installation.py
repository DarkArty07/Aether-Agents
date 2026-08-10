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
ORCA_PRODUCT_VERSION = "1.4.167"
MAX_ORCA_OUTPUT_BYTES = 1_048_576
ORCA_CLI_BOOTSTRAP = (
    '(async()=>{try{const path=require("path");const appDir=process.env.APPDIR;'
    'if(!appDir){throw new Error("missing APPDIR");}'
    'const cli=path.join(appDir,"resources","app.asar.unpacked","out","cli","index.js");'
    'await Promise.resolve(require(cli).main(process.argv.slice(1)));}'
    'catch(error){console.error(error&&error.stack?error.stack:String(error));process.exit(1);}})();'
)


class InstallError(RuntimeError):
    """Typed, secret-safe operational installation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
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


def _chmod_owned_directories(root: Path) -> None:
    """Normalize permissions after tools (notably uv/AppImage extraction) create trees."""
    for directory, _children, _files in os.walk(root):
        os.chmod(directory, 0o700)


def _config_entry(launcher: Path) -> str:
    return f"  aether_mcp:\n    command: {json.dumps(str(launcher))}\n    args: []\n    enabled: false\n"


def _registration(config: str) -> tuple[bool, bool]:
    """Return the actual named registration and its enabled value."""
    lines = config.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "mcp_servers:"), None)
    if start is None:
        return False, False
    end = next((i for i in range(start + 1, len(lines)) if lines[i] and not lines[i][0].isspace()), len(lines))
    item = next((i for i in range(start + 1, end) if lines[i].startswith("  aether_mcp:")), None)
    if item is None:
        return False, False
    item_end = next((i for i in range(item + 1, end) if lines[i].startswith("  ") and not lines[i].startswith("    ")), end)
    enabled = any(line.strip() == "enabled: true" for line in lines[item + 1 : item_end])
    return True, enabled


def set_registration_enabled(config: str, enabled: bool) -> str:
    """Change only the owned entry's enabled scalar, retaining all other bytes."""
    lines = config.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.rstrip() == "mcp_servers:"), None)
    if start is None:
        raise InstallError("REGISTRATION_NOT_FOUND")
    end = next((i for i in range(start + 1, len(lines)) if lines[i] and not lines[i][0].isspace()), len(lines))
    item = next((i for i in range(start + 1, end) if lines[i].startswith("  aether_mcp:")), None)
    if item is None:
        raise InstallError("REGISTRATION_NOT_FOUND")
    item_end = next((i for i in range(item + 1, end) if lines[i].startswith("  ") and not lines[i].startswith("    ")), end)
    flag = f"    enabled: {str(enabled).lower()}\n"
    existing = next((i for i in range(item + 1, item_end) if lines[i].lstrip().startswith("enabled:")), None)
    if existing is None:
        lines[item_end:item_end] = [flag]
    else:
        lines[existing] = flag
    return "".join(lines)


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
    profile_root: str
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
    if not repo_selector or not base_ref or not coordinator_handle or not 1 <= timeout_ms <= 600_000:
        raise InstallError("INVALID_INPUT")
    catalog = OrcaCatalog.bundled()
    existing_path = home / ".aether-mcp" / "installation.json"
    if existing_path.exists():
        existing = Installation.load(home)
        expected = {
            "project_root": str(root), "hermes_home": str(home), "config_path": str(home / "config.yaml"),
            "appimage": str(image), "appimage_sha256": observed, "profile_root": str(profile),
            "repo_selector": repo_selector, "base_ref": base_ref, "coordinator_handle": coordinator_handle,
            "catalog_digest": catalog.digest, "tool_count": len(CALLABLE_TOOL_NAMES), "version": INSTALL_VERSION,
        }
        if all(getattr(existing, key) == value for key, value in expected.items()):
            return existing
        raise InstallError("INSTALLATION_CONFLICT")
    config = home / "config.yaml"
    if not config.is_file():
        raise InstallError("CONFIG_NOT_FOUND")
    base = home / ".aether-mcp"
    extraction = base / "orca" / ORCA_PRODUCT_VERSION
    wrapper = base / "bin" / "orca-public-cli"
    venv = base / "venv"
    launcher = base / "bin" / "aether-mcp"
    # State/evidence is deliberately not inside the removable payload.
    state_root = home / ".aether-mcp-state"
    backup = base / "backups" / "config.yaml.pre-aether-mcp"
    original = config.read_text(encoding="utf-8")
    _atomic_write(backup, original, stat.S_IMODE(config.stat().st_mode))
    try:
        for owned in (base, extraction.parent, wrapper.parent, state_root, backup.parent):
            owned.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(owned, 0o700)
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
        app_run = extraction / "AppRun"
        if not public.is_file() or not app_run.is_file():
            raise InstallError("APPIMAGE_EXTRACTION_FAILED")
        _atomic_write(
            wrapper,
            "#!/bin/sh\nset -eu\nunset APPIMAGE_EXTRACT_AND_RUN NODE_OPTIONS NODE_REPL_EXTERNAL_MODULE\n"
            f"export APPDIR={json.dumps(str(extraction))}\nexport ELECTRON_RUN_AS_NODE=1\n"
            f"exec {json.dumps(str(app_run))} -e {json.dumps(ORCA_CLI_BOOTSTRAP)} -- \"$@\"\n",
            0o700,
        )
        subprocess.run((uv, "venv", "--clear", str(venv)), check=True, timeout=120, capture_output=True)
        subprocess.run(
            (uv, "pip", "install", "--python", str(venv / "bin" / "python"), str(root)),
            check=True,
            timeout=300,
            capture_output=True,
        )
        environment = {
            "AETHER_STATE_ROOT": str(state_root),
            "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
            "HERMES_HOME": str(home),
            "HOME": str(profile),
            "XDG_CONFIG_HOME": str(profile / "config"),
            "XDG_CACHE_HOME": str(profile / "cache"),
            "XDG_DATA_HOME": str(profile / "data"),
            "XDG_STATE_HOME": str(profile / "state"),
            "XDG_RUNTIME_DIR": str(profile / "runtime"),
            "AETHER_PROFILE_ROOT": str(profile),
            "AETHER_PROFILE": profile.name,
            "AETHER_TELEMETRY_DISABLED": "1",
            "DO_NOT_TRACK": "1",
            "AETHER_SESSION_ID": "${AETHER_SESSION_ID}",
            "AETHER_ORCA_CLI": str(wrapper),
            "AETHER_ORCA_COORDINATOR_HANDLE": coordinator_handle,
            "AETHER_ORCA_REPO_SELECTOR": repo_selector,
            "AETHER_ORCA_BASE_REF": base_ref,
            "AETHER_ORCA_BINDING_DIGEST": catalog.digest,
            "AETHER_ORCA_TIMEOUT_MS": str(timeout_ms),
        }
        for path in (profile, *(Path(environment[key]) for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR"))):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(path, 0o700)
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY"):
            value = os.environ.get(key)
            if value:
                environment[key] = value
        exports = "\n".join(
            f"export {key}={json.dumps(value)}" for key, value in environment.items() if key != "AETHER_SESSION_ID"
        )
        _atomic_write(
            launcher,
            "#!/bin/sh\nset -eu\n"
            + exports
            + f"\nexport AETHER_SESSION_ID=\"$({json.dumps(str(venv / 'bin' / 'python'))} -c 'import uuid; print(uuid.uuid4())')\"\nexec {json.dumps(str(venv / 'bin' / 'aether-mcp'))}\n",
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
            str(profile),
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
        _chmod_owned_directories(base)
        _chmod_owned_directories(state_root)
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
        "registration": dict(zip(("present", "enabled"), _registration(config), strict=True)),
        "paths": {
            key: getattr(installation, key)
            for key in ("config_path", "appimage", "venv", "launcher", "state_root", "wrapper", "extraction", "profile_root")
        },
        "hashes": {"appimage": installation.appimage_sha256, "catalog": installation.catalog_digest},
        "tool_count": installation.tool_count,
        "tool_names": sorted(CALLABLE_TOOL_NAMES),
        "orca": {"profile_root": installation.profile_root, "extraction": installation.extraction, "product_version": ORCA_PRODUCT_VERSION, "ready": Path(installation.wrapper).is_file()},
        "state_permissions": _permissions_ok(Path(installation.state_root)),
    }


def rollback(home: str) -> dict[str, Any]:
    home_path = _safe_path(home, directory=True)
    manifest = home_path / ".aether-mcp" / "installation.json"
    if not manifest.exists():
        return {"ok": True, "already_rolled_back": True, "preserved_state_root": str(home_path / ".aether-mcp-state")}
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
        "preserved_state_root": installation.state_root,
        "already_rolled_back": False,
    }


def activate(home: str, *, enabled: bool = True) -> dict[str, Any]:
    """Atomically toggle only the named registration; it never launches MCP."""
    installation = Installation.load(_safe_path(home, directory=True))
    config = Path(installation.config_path)
    original = config.read_text(encoding="utf-8")
    present, current = _registration(original)
    if not present:
        raise InstallError("REGISTRATION_NOT_FOUND")
    if current == enabled:
        return {"ok": True, "enabled": enabled, "changed": False}
    backup = Path(installation.hermes_home) / ".aether-mcp" / "backups" / "config.yaml.pre-activation"
    if not backup.exists():
        _atomic_write(backup, original, stat.S_IMODE(config.stat().st_mode))
    _atomic_write(config, set_registration_enabled(original, enabled), stat.S_IMODE(config.stat().st_mode))
    return {"ok": True, "enabled": enabled, "changed": True, "backup": str(backup)}


def _permissions_ok(path: Path) -> bool:
    try:
        return path.is_dir() and not (path.stat().st_mode & 0o077)
    except OSError:
        return False


def _parse_orca_status(completed: subprocess.CompletedProcess[bytes]) -> bool:
    if completed.returncode != 0 or completed.stderr or len(completed.stdout) > MAX_ORCA_OUTPUT_BYTES:
        return False
    try:
        envelope = json.loads(completed.stdout.decode("utf-8"))
        result = envelope["result"]
        runtime = result["runtime"]
        return bool(envelope["ok"]) and runtime["appVersion"] == ORCA_PRODUCT_VERSION and runtime["state"] == "ready" and bool(runtime["reachable"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return False


def _resource_inventory(installation: Installation) -> list[dict[str, Any]]:
    """Always query public worktree inventory and local attempt processes."""
    entries: list[dict[str, Any]] = []
    try:
        completed = subprocess.run((installation.wrapper, "worktree", "ps", "--json"), capture_output=True, check=False, timeout=30)
        entries.append({"source": "orca_worktree_ps", "performed": True, "ok": completed.returncode == 0})
    except (OSError, subprocess.SubprocessError):
        entries.append({"source": "orca_worktree_ps", "performed": True, "ok": False})
    try:
        completed = subprocess.run(("ps", "-eo", "pid=,args="), capture_output=True, check=False, timeout=10)
        owned = []
        for line in completed.stdout.decode("utf-8", "replace").splitlines():
            columns = line.strip().split(maxsplit=1)
            if len(columns) != 2 or not columns[0].isdigit() or int(columns[0]) == os.getpid():
                continue
            if installation.hermes_home in columns[1] or installation.extraction in columns[1]:
                owned.append(line.strip())
        entries.append({"source": "processes", "performed": True, "survivors": owned})
    except (OSError, subprocess.SubprocessError):
        entries.append({"source": "processes", "performed": True, "survivors": ["UNKNOWN"]})
    return entries


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

        async def handshake() -> set[str]:
            parameters = StdioServerParameters(
                command=installation.launcher, args=[], env={"PATH": os.environ.get("PATH", "")}
            )
            async with asyncio.timeout(timeout_seconds):
                async with stdio_client(parameters) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return {tool.name for tool in result.tools}

        tool_names = asyncio.run(handshake())
    except Exception as exc:
        raise InstallError("MCP_HANDSHAKE_FAILED") from exc
    if tool_names != CALLABLE_TOOL_NAMES:
        raise InstallError("MCP_TOOL_INVENTORY_MISMATCH")
    tool_count = len(tool_names)
    try:
        completed = subprocess.run(
            (installation.wrapper, "status", "--json"), capture_output=True, check=False, timeout=30
        )
        orca_ready = _parse_orca_status(completed)
    except (OSError, subprocess.SubprocessError):
        orca_ready = False
    owned_root = Path(installation.hermes_home) / ".aether-mcp"
    permissions_ok = all(_permissions_ok(path) for path in (owned_root, Path(installation.state_root))) and not (Path(installation.launcher).stat().st_mode & 0o077)
    inventory = _resource_inventory(installation)
    stale_resources = [entry for entry in inventory if entry.get("survivors")]
    return {
        "ok": orca_ready and permissions_ok and not stale_resources,
        "tool_count": tool_count,
        "orca_ready": orca_ready,
        "state_permissions_ok": permissions_ok,
        "stale_resources": stale_resources,
        "resource_inventory": inventory,
    }
