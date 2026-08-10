"""Idempotent, default-off local Aether MCP installation primitives.

The manifest is deliberately the ownership boundary: no command acts outside its
recorded paths, and configuration is restored byte-for-byte when untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time
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
PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ORCA_CLI_BOOTSTRAP = (
    '(async()=>{try{const path=require("path");const appDir=process.env.APPDIR;'
    'if(!appDir){throw new Error("missing APPDIR");}'
    'const cli=path.join(appDir,"resources","app.asar.unpacked","out","cli","index.js");'
    "await Promise.resolve(require(cli).main(process.argv.slice(1)));}"
    "catch(error){console.error(error&&error.stack?error.stack:String(error));process.exit(1);}})();"
)


class InstallError(RuntimeError):
    """Typed, secret-safe operational installation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OrcaProfileLayout:
    root: Path

    @property
    def hermes_home(self) -> Path:
        return self.root / "hermes-home"

    @property
    def xdg_config_home(self) -> Path:
        return self.root / "xdg" / "config"

    @property
    def xdg_cache_home(self) -> Path:
        return self.root / "xdg" / "cache"

    @property
    def xdg_data_home(self) -> Path:
        return self.root / "xdg" / "data"

    @property
    def xdg_state_home(self) -> Path:
        return self.root / "xdg" / "state"

    def directories(self) -> tuple[Path, ...]:
        return (
            self.root,
            self.hermes_home,
            self.xdg_config_home,
            self.xdg_cache_home,
            self.xdg_data_home,
            self.xdg_state_home,
        )


def _run_owned(
    command: tuple[str, ...], *, timeout: int, env: dict[str, str] | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run an installer child in a new session and reap its entire group on failure."""
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        child = subprocess.Popen(
            command, stdout=stdout_file, stderr=stderr_file, start_new_session=True, env=env, cwd=cwd
        )
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _terminate_group(child.pid, child)
            raise InstallError("INSTALLER_TIMEOUT") from exc
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read(MAX_ORCA_OUTPUT_BYTES + 1)
        stderr = stderr_file.read(MAX_ORCA_OUTPUT_BYTES + 1)
        if len(stdout) > MAX_ORCA_OUTPUT_BYTES or len(stderr) > MAX_ORCA_OUTPUT_BYTES:
            _terminate_group(child.pid)
            raise InstallError("INSTALLER_OUTPUT_TOO_LARGE")
        if child.returncode:
            _terminate_group(child.pid)
            raise subprocess.CalledProcessError(child.returncode, command, stdout, stderr)
        if not _wait_group_exit(child.pid, 0.5):
            _terminate_group(child.pid)
            raise InstallError("INSTALLER_CHILD_SURVIVOR")
        return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)


def _group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_group_exit(pgid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _group_exists(pgid):
            return True
        time.sleep(0.05)
    return not _group_exists(pgid)


def _terminate_group(pid: int, leader: subprocess.Popen[bytes] | None = None) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    if leader is not None:
        try:
            leader.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
    if _wait_group_exit(pid, 2):
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    if leader is not None:
        try:
            leader.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
    _wait_group_exit(pid, 2)


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
    item_end = next(
        (i for i in range(item + 1, end) if lines[i].startswith("  ") and not lines[i].startswith("    ")), end
    )
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
    item_end = next(
        (i for i in range(item + 1, end) if lines[i].startswith("  ") and not lines[i].startswith("    ")), end
    )
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
    profile_id: str
    orca_hermes_home: str
    orca_xdg_config_home: str
    orca_xdg_cache_home: str
    orca_xdg_data_home: str
    orca_xdg_state_home: str
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
    profile_id: str,
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
    if not PROFILE_ID.fullmatch(profile_id):
        raise InstallError("INVALID_PROFILE_ID")
    layout = OrcaProfileLayout(profile)
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
            "project_root": str(root),
            "hermes_home": str(home),
            "config_path": str(home / "config.yaml"),
            "appimage": str(image),
            "appimage_sha256": observed,
            "profile_root": str(profile),
            "profile_id": profile_id,
            "orca_hermes_home": str(layout.hermes_home),
            "orca_xdg_config_home": str(layout.xdg_config_home),
            "orca_xdg_cache_home": str(layout.xdg_cache_home),
            "orca_xdg_data_home": str(layout.xdg_data_home),
            "orca_xdg_state_home": str(layout.xdg_state_home),
            "repo_selector": repo_selector,
            "base_ref": base_ref,
            "coordinator_handle": coordinator_handle,
            "catalog_digest": catalog.digest,
            "tool_count": len(CALLABLE_TOOL_NAMES),
            "version": INSTALL_VERSION,
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
    _atomic_write(backup, original)
    try:
        for owned in (base, extraction.parent, wrapper.parent, state_root, backup.parent):
            owned.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(owned, 0o700)
        if not extraction.exists():
            temporary = Path(tempfile.mkdtemp(prefix="aether-mcp-extract-", dir=extraction.parent))
            try:
                extraction_env = dict(os.environ)
                extraction_env.pop("APPIMAGE_EXTRACT_AND_RUN", None)
                _run_owned((str(image), "--appimage-extract"), timeout=120, env=extraction_env, cwd=temporary)
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
            f"export HOME={json.dumps(str(profile))}\nexport HERMES_HOME={json.dumps(str(layout.hermes_home))}\n"
            f"export XDG_CONFIG_HOME={json.dumps(str(layout.xdg_config_home))}\nexport XDG_CACHE_HOME={json.dumps(str(layout.xdg_cache_home))}\n"
            f"export XDG_DATA_HOME={json.dumps(str(layout.xdg_data_home))}\nexport XDG_STATE_HOME={json.dumps(str(layout.xdg_state_home))}\n"
            "export ORCA_TELEMETRY_DISABLED=1\n"
            f"export APPDIR={json.dumps(str(extraction))}\nexport ELECTRON_RUN_AS_NODE=1\n"
            f'exec {json.dumps(str(app_run))} -e {json.dumps(ORCA_CLI_BOOTSTRAP)} -- "$@"\n',
            0o700,
        )
        _run_owned((uv, "venv", "--clear", str(venv)), timeout=120)
        _run_owned((uv, "pip", "install", "--python", str(venv / "bin" / "python"), str(root)), timeout=300)
        environment = {
            "AETHER_STATE_ROOT": str(state_root),
            "AETHER_COORDINATOR_PRINCIPAL": str(uuid.uuid4()),
            "HERMES_HOME": str(home),
            "AETHER_PROFILE_ROOT": str(profile),
            "AETHER_PROFILE": profile_id,
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
        for path in layout.directories():
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
            project_root=str(root),
            hermes_home=str(home),
            config_path=str(config),
            appimage=str(image),
            appimage_sha256=observed,
            profile_root=str(profile),
            profile_id=profile_id,
            orca_hermes_home=str(layout.hermes_home),
            orca_xdg_config_home=str(layout.xdg_config_home),
            orca_xdg_cache_home=str(layout.xdg_cache_home),
            orca_xdg_data_home=str(layout.xdg_data_home),
            orca_xdg_state_home=str(layout.xdg_state_home),
            extraction=str(extraction),
            wrapper=str(wrapper),
            venv=str(venv),
            launcher=str(launcher),
            state_root=str(state_root),
            backup=str(backup),
            original_config_sha256=hashlib.sha256(original.encode()).hexdigest(),
            registered_config_sha256=hashlib.sha256(updated.encode()).hexdigest(),
            repo_selector=repo_selector,
            base_ref=base_ref,
            coordinator_handle=coordinator_handle,
            catalog_digest=catalog.digest,
            tool_count=len(CALLABLE_TOOL_NAMES),
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
            for key in (
                "config_path",
                "appimage",
                "venv",
                "launcher",
                "state_root",
                "wrapper",
                "extraction",
                "profile_root",
                "orca_hermes_home",
                "orca_xdg_config_home",
                "orca_xdg_cache_home",
                "orca_xdg_data_home",
                "orca_xdg_state_home",
            )
        },
        "hashes": {"appimage": installation.appimage_sha256, "catalog": installation.catalog_digest},
        "tool_count": installation.tool_count,
        "tool_names": sorted(CALLABLE_TOOL_NAMES),
        "orca": {
            "profile_root": installation.profile_root,
            "profile_id": installation.profile_id,
            "extraction": installation.extraction,
            "product_version": ORCA_PRODUCT_VERSION,
            "ready": Path(installation.wrapper).is_file(),
        },
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
    owned = _owned_processes(installation)
    if owned is None:
        raise InstallError("PROCESS_INVENTORY_UNKNOWN")
    _terminate_owned_processes(owned)
    survivors = _owned_processes(installation)
    if survivors is None or survivors:
        raise InstallError("OWNED_PROCESS_CLEANUP_FAILED")
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
        _atomic_write(backup, original)
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
        return (
            bool(envelope["ok"])
            and runtime["appVersion"] == ORCA_PRODUCT_VERSION
            and runtime["state"] == "ready"
            and bool(runtime["reachable"])
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return False


@dataclass(frozen=True)
class ProcessRecord:
    pid: int
    ppid: int
    pgid: int
    session_id: int
    start_time: int
    argv: tuple[str, ...]
    executable: str | None
    command_name: str = ""
    inspectable: bool = True
    state: str = "S"


def _process_stat_fields(pid: int) -> list[str] | None:
    try:
        raw = Path("/proc", str(pid), "stat").read_text()
    except OSError:
        return None
    closing = raw.rfind(")")
    if closing < 0:
        return None
    fields = raw[closing + 2 :].split()
    return fields if len(fields) > 19 else None


def _ancestor_pids() -> set[int]:
    result: set[int] = set()
    current = os.getpid()
    while current and current not in result:
        result.add(current)
        fields = _process_stat_fields(current)
        if fields is None:
            break
        try:
            current = int(fields[1])
        except ValueError:
            break
    return result


def _process_snapshot() -> list[ProcessRecord] | None:
    """Same-user bounded proc snapshot; never return raw command lines to callers."""
    try:
        owner = os.getuid()
        records: list[ProcessRecord] = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                status = (entry / "status").read_text()
                uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
                if int(uid_line.split()[1]) != owner:
                    continue
                command_name = next(line for line in status.splitlines() if line.startswith("Name:")).split(maxsplit=1)[1]
                fields = _process_stat_fields(int(entry.name))
                if fields is None:
                    if entry.exists():
                        return None
                    continue
                try:
                    raw = (entry / "cmdline").read_bytes()
                except PermissionError:
                    raw = b""
                if len(raw) > 65_536:
                    return None
                argv = tuple(part.decode("utf-8", "replace") for part in raw.split(b"\0") if part)
                try:
                    executable = os.readlink(entry / "exe")
                except (FileNotFoundError, PermissionError):
                    executable = None
                records.append(
                    ProcessRecord(
                        pid=int(entry.name),
                        ppid=int(fields[1]),
                        pgid=int(fields[2]),
                        session_id=int(fields[3]),
                        start_time=int(fields[19]),
                        argv=argv,
                        executable=executable,
                        command_name=command_name,
                        inspectable=bool(argv or executable),
                        state=fields[0],
                    )
                )
            except FileNotFoundError:
                continue
            except PermissionError:
                if entry.exists():
                    return None
            except (OSError, StopIteration, ValueError, IndexError):
                if entry.exists():
                    return None
        return records
    except (OSError, ValueError):
        return None


def _record_is_exactly_owned(record: ProcessRecord, installation: Installation) -> bool:
    files = (installation.launcher, installation.wrapper)
    directories = (installation.venv, installation.extraction)
    values = (*record.argv, *((record.executable,) if record.executable else ()))
    return any(value in files or any(value == root or value.startswith(root + os.sep) for root in directories) for value in values)


def _classify_owned(records: list[ProcessRecord], installation: Installation) -> list[dict[str, int]]:
    ancestors = _ancestor_pids()
    owned_pids = {record.pid for record in records if record.pid not in ancestors and _record_is_exactly_owned(record, installation)}
    changed = True
    while changed:
        changed = False
        for record in records:
            if record.pid not in ancestors and record.pid not in owned_pids and record.ppid in owned_pids:
                owned_pids.add(record.pid)
                changed = True
    return [
        {"pid": record.pid, "ppid": record.ppid, "start_time": record.start_time}
        for record in records
        if record.pid in owned_pids
    ]


def _plausible_opaque_records(
    records: list[ProcessRecord], installation: Installation, owned: list[dict[str, int]]
) -> list[ProcessRecord]:
    owned_pids = {record["pid"] for record in owned}
    ancestors = _ancestor_pids()
    plausible_names = {"aether-mcp", "python", "python3", "node", "electron", "apprun", "sh", "dash", "bash"}
    return [
        record
        for record in records
        if record.pid not in ancestors
        and record.pid not in owned_pids
        and not record.inspectable
        and record.state != "Z"
        and (record.command_name.lower() in plausible_names or record.command_name.lower().startswith("python"))
    ]


def _owned_processes(installation: Installation) -> list[dict[str, int]] | None:
    records = _process_snapshot()
    if records is None:
        return None
    owned = _classify_owned(records, installation)
    if _plausible_opaque_records(records, installation, owned):
        return None
    return owned


def _process_start_time(pid: int) -> int | None:
    fields = _process_stat_fields(pid)
    if fields is None:
        return None
    try:
        return int(fields[19])
    except ValueError:
        return None


def _process_identity_alive(process: dict[str, int]) -> bool:
    expected = process.get("start_time")
    if expected is None:
        return Path("/proc", str(process["pid"])).exists()
    return _process_start_time(process["pid"]) == expected


def _terminate_owned_processes(owned: list[dict[str, int]]) -> None:
    for process in owned:
        if not _process_identity_alive(process):
            continue
        try:
            os.kill(process["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if not any(_process_identity_alive(item) for item in owned):
            return
        time.sleep(0.05)
    for process in owned:
        if not _process_identity_alive(process):
            continue
        try:
            os.kill(process["pid"], signal.SIGKILL)
        except ProcessLookupError:
            pass


def _parse_orca_worktree_ps(completed: subprocess.CompletedProcess[bytes]) -> bool:
    if completed.returncode != 0 or completed.stderr or len(completed.stdout) > MAX_ORCA_OUTPUT_BYTES:
        return False
    try:
        envelope = json.loads(completed.stdout.decode("utf-8"))
        result = envelope["result"]
        worktrees = result["worktrees"]
        return (
            envelope["ok"] is True
            and isinstance(worktrees, list)
            and isinstance(result["totalCount"], int)
            and result["totalCount"] >= len(worktrees)
            and isinstance(result["truncated"], bool)
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return False


def _resource_inventory(installation: Installation) -> list[dict[str, Any]]:
    """Classify exact installation processes and shared provider state truthfully."""
    entries: list[dict[str, Any]] = []
    try:
        completed = subprocess.run(
            (installation.wrapper, "worktree", "ps", "--json"), capture_output=True, check=False, timeout=30
        )
        entries.append({"source": "orca_worktree_ps", "performed": True, "ok": _parse_orca_worktree_ps(completed)})
    except (OSError, subprocess.SubprocessError):
        entries.append({"source": "orca_worktree_ps", "performed": True, "ok": False})
    snapshot = _process_snapshot()
    if snapshot is None:
        entries.append({"source": "processes", "performed": False, "state": "UNKNOWN"})
    else:
        classified_owned = _classify_owned(snapshot, installation)
        owned = [dict(record, classification="installed_mcp") for record in classified_owned]
        shared = [
            {"pid": record.pid, "ppid": record.ppid, "classification": "shared_orca_provider"}
            for record in snapshot
            if any(installation.profile_root in value for value in (*record.argv, *((record.executable,) if record.executable else ())))
            and any("orca" in value.lower() for value in (*record.argv, *((record.executable,) if record.executable else ())))
            and not _record_is_exactly_owned(record, installation)
        ]
        entries.append({"source": "processes", "performed": True, "owned": owned, "provider": shared})
        opaque = _plausible_opaque_records(snapshot, installation, classified_owned)
        if opaque:
            entries.append(
                {"source": "processes", "performed": False, "state": "UNKNOWN", "unattributed_count": len(opaque)}
            )
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
    permissions_ok = all(_permissions_ok(path) for path in (owned_root, Path(installation.state_root))) and not (
        Path(installation.launcher).stat().st_mode & 0o077
    )
    inventory = _resource_inventory(installation)
    inventory_unknown = any(entry.get("state") == "UNKNOWN" for entry in inventory)
    inventory_failed = any(entry.get("source") == "orca_worktree_ps" and entry.get("ok") is False for entry in inventory)
    stale_resources = [entry for entry in inventory if entry.get("owned")]
    return {
        "ok": orca_ready and permissions_ok and not stale_resources and not inventory_unknown and not inventory_failed,
        "tool_count": tool_count,
        "orca_ready": orca_ready,
        "state_permissions_ok": permissions_ok,
        "stale_resources": stale_resources,
        "resource_inventory": inventory,
    }
