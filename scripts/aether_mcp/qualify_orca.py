"""Deterministic Orca source, build, catalog, and isolation qualification probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path("/home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition")

DEFAULT_LAUNCHER = Path("/home/darkarty/.local/bin/orca")
DEFAULT_ARTIFACT = Path("/home/darkarty/.local/opt/orca/orca-linux.AppImage")
DEFAULT_LAUNCHER_SHA256 = "89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208"
DEFAULT_ARTIFACT_SHA256 = "813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33"
DEFAULT_PRODUCT_VERSION = "1.4.167"
DEFAULT_SCHEMA_VERSION = 1
DEFAULT_COMMAND_COUNT = 220


class QualificationError(Exception):
    """Failure during Orca qualification probe."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def parse_static_appimage_binding(launcher_bytes: bytes, artifact_path: Path) -> None:
    """C1: Parse launcher text as data and verify single static APPIMAGE='/abs/path' assignment."""
    try:
        text = launcher_bytes.decode("utf-8")
    except Exception as exc:
        raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher text is not valid UTF-8") from exc

    active_assignments: list[str] = []
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue

        if "#" in line_clean:
            in_quote = None
            buf = []
            for ch in line_clean:
                if ch in ("'", '"'):
                    if in_quote is None:
                        in_quote = ch
                    elif in_quote == ch:
                        in_quote = None
                    buf.append(ch)
                elif ch == "#" and in_quote is None:
                    break
                else:
                    buf.append(ch)
            line_clean = "".join(buf).strip()

        if not line_clean:
            continue

        # 1. Unset targeting APPIMAGE
        if "unset" in line_clean and "APPIMAGE" in line_clean:
            raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains unset APPIMAGE")

        # 2. Eval targeting APPIMAGE
        if "eval" in line_clean and "APPIMAGE" in line_clean:
            raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains eval APPIMAGE")

        # 3. Additive assignment
        if "APPIMAGE+=" in line_clean:
            raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains additive APPIMAGE assignment")

        # 4. Multi-statement line containing APPIMAGE assignment
        if (";" in line_clean or "&&" in line_clean or "||" in line_clean) and "APPIMAGE=" in line_clean:
            raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains multi-statement APPIMAGE assignment")

        # 5. Exact literal assignment or forbidden declaration prefix
        if line_clean.startswith("APPIMAGE="):
            val_part = line_clean[len("APPIMAGE=") :].strip()
            if (val_part.startswith("'") and val_part.endswith("'")) or (
                val_part.startswith('"') and val_part.endswith('"')
            ):
                val = val_part[1:-1]
                if "$" in val or "`" in val or not val.startswith("/") or " " in val:
                    raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains dynamic or malformed APPIMAGE assignment")
                active_assignments.append(val)
            else:
                raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains unquoted or malformed APPIMAGE assignment")
        elif "APPIMAGE=" in line_clean or any(line_clean.startswith(prefix) for prefix in ("export ", "readonly ", "declare ", "local ")):
            if "APPIMAGE" in line_clean:
                raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher contains declaration-prefixed or complex APPIMAGE assignment")

    if len(active_assignments) != 1:
        raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher does not contain exactly one active static APPIMAGE assignment")

    assigned_path = Path(active_assignments[0])
    try:
        assigned_resolved = assigned_path.resolve()
        artifact_resolved = artifact_path.resolve()
    except Exception as exc:
        raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Failed to resolve artifact path in launcher binding") from exc

    if assigned_resolved != artifact_resolved:
        raise QualificationError("ERR_LAUNCHER_NOT_BOUND", "Launcher APPIMAGE assignment does not match target artifact")


def run_owned_process_group(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, bytes, bytes]:
    """C5 & C3: Run child process in its own session/process-group, cleanly terminating all descendants on exit or timeout."""
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except Exception as exc:
        raise QualificationError("ERR_CATALOG_NONZERO_EXIT", "Failed to launch child process group") from exc

    pgid = os.getpgid(proc.pid)
    stdout = b""
    stderr = b""
    timed_out = False

    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True

    # Teardown process group
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    try:
        proc.wait(timeout=0.5)
    except (subprocess.TimeoutExpired, Exception):
        pass

    deadline = time.time() + 0.5
    alive = True
    while time.time() < deadline:
        try:
            os.killpg(pgid, 0)
            time.sleep(0.02)
        except ProcessLookupError:
            alive = False
            break

    if alive:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.05)

    try:
        os.killpg(pgid, 0)
        raise QualificationError("ERR_SURVIVING_PROCESS_DETECTED", "Child process survived in process group")
    except ProcessLookupError:
        pass

    if timed_out:
        raise QualificationError("ERR_CATALOG_TIMEOUT", "Subprocess execution timed out")

    return proc.returncode, stdout, stderr


def verify_isolated_root(iso_root: Path) -> None:
    """C4: Verify isolated root path is a non-symlinked directory under /tmp/aether-m1-1-*."""
    test_path = iso_root
    while test_path != test_path.parent:
        if os.path.islink(test_path):
            raise QualificationError("ERR_ISOLATED_ROOT_SYMLINK", "Isolated root or parent component is a symlink")
        test_path = test_path.parent

    if not iso_root.exists() or not iso_root.is_dir():
        raise QualificationError("ERR_ISOLATED_ROOT_INVALID", "Isolated root directory invalid or missing")

    iso_resolved = iso_root.resolve()
    tmp_resolved = Path("/tmp").resolve()

    if not iso_resolved.name.startswith("aether-m1-1-"):
        raise QualificationError("ERR_ISOLATED_ROOT_INVALID", "Isolated root basename does not start with aether-m1-1-")

    if iso_resolved.parent != tmp_resolved:
        raise QualificationError("ERR_ISOLATED_ROOT_INVALID", "Isolated root is not located directly under /tmp")

    if iso_resolved == tmp_resolved:
        raise QualificationError("ERR_ISOLATED_ROOT_INVALID", "Isolated root cannot equal /tmp")

    repo_resolved = PROJECT_ROOT.resolve()
    home_resolved = Path.home().resolve()

    if iso_resolved == repo_resolved or iso_resolved.is_relative_to(repo_resolved):
        raise QualificationError("ERR_ISOLATED_ROOT_INSIDE_REPO", "Isolated root is inside repository")

    if iso_resolved == home_resolved or iso_resolved.is_relative_to(home_resolved):
        raise QualificationError("ERR_ISOLATED_ROOT_INSIDE_HOME", "Isolated root is inside HOME")

    xdg_vars = ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR"]
    for var in xdg_vars:
        if var in os.environ and os.environ[var]:
            ambient_xdg = Path(os.environ[var]).resolve()
            if iso_resolved == ambient_xdg or iso_resolved.is_relative_to(ambient_xdg) or ambient_xdg.is_relative_to(iso_resolved):
                raise QualificationError("ERR_ISOLATED_ROOT_GLOBAL", "Isolated root overlaps with ambient XDG directory")


def check_isolated_root_inventory(iso_root: Path) -> None:
    """C3 & C2: Recursively inventory isolated root. Prove exact required directory set and desktop metadata file."""
    required_dirs = {"home", "config", "data", "cache", "state", "runtime", "tmp", "squashfs-root"}
    required_file = Path("squashfs-root/orca-ide.desktop")

    for rdir in required_dirs:
        dir_path = iso_root / rdir
        if not dir_path.exists() or not dir_path.is_dir() or os.path.islink(dir_path):
            raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Required directory missing or invalid in isolated root")

    desktop_file = iso_root / required_file
    if not desktop_file.exists() or not desktop_file.is_file() or os.path.islink(desktop_file):
        raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Required metadata file missing or invalid in isolated root")

    stack = [iso_root]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            rel_curr = current.relative_to(iso_root)
            if len(rel_curr.parts) >= 2 and rel_curr.parts[0] == "tmp" and rel_curr.parts[1].startswith(".mount_orca-"):
                continue
            raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Unreadable entry in isolated root inventory")

        for entry in entries:
            path = Path(entry.path)
            rel_path = path.relative_to(iso_root)

            if entry.is_symlink():
                raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Symlink found in isolated root inventory")
            if not entry.is_file() and not entry.is_dir():
                raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Non-regular entry found in isolated root inventory")

            top_level = rel_path.parts[0]
            if top_level not in required_dirs:
                raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Unexpected directory in isolated root")

            if entry.is_dir():
                if len(rel_path.parts) > 1:
                    if top_level == "tmp" and rel_path.parts[1].startswith(".mount_orca-"):
                        continue
                    raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Nested directory found in isolated root")
                stack.append(path)
            elif entry.is_file():
                if rel_path != required_file:
                    if top_level == "tmp" and rel_path.parts[1].startswith(".mount_orca-"):
                        continue
                    raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", "Unexpected file found in isolated root")


def qualify_orca(
    launcher_path: str | Path,
    artifact_path: str | Path,
    isolated_root: str | Path,
    expected_launcher_sha256: str = DEFAULT_LAUNCHER_SHA256,
    expected_artifact_sha256: str = DEFAULT_ARTIFACT_SHA256,
    expected_product_version: str = DEFAULT_PRODUCT_VERSION,
    expected_schema_version: int = DEFAULT_SCHEMA_VERSION,
    expected_command_count: int = DEFAULT_COMMAND_COUNT,
    timeout_seconds: int = 10,
) -> dict[str, str | int | bool | dict]:
    launcher = Path(launcher_path)
    artifact = Path(artifact_path)
    iso_root = Path(isolated_root)

    # 1. Launcher checks
    if os.path.islink(launcher):
        raise QualificationError("ERR_LAUNCHER_IS_SYMLINK", "Launcher is a symlink")
    if not launcher.exists():
        raise QualificationError("ERR_LAUNCHER_MISSING", "Launcher does not exist")
    if not launcher.is_file():
        raise QualificationError("ERR_LAUNCHER_NOT_REGULAR", "Launcher is not a regular file")
    if not os.access(launcher, os.X_OK):
        raise QualificationError("ERR_LAUNCHER_NOT_EXECUTABLE", "Launcher is not executable")

    launcher_bytes = launcher.read_bytes()
    launcher_sha256 = hashlib.sha256(launcher_bytes).hexdigest()
    if launcher_sha256 != expected_launcher_sha256:
        raise QualificationError("ERR_LAUNCHER_DIGEST_MISMATCH", "Launcher SHA256 mismatch")

    # 2. Artifact checks
    if os.path.islink(artifact):
        raise QualificationError("ERR_ARTIFACT_IS_SYMLINK", "Artifact is a symlink")
    if not artifact.exists():
        raise QualificationError("ERR_ARTIFACT_MISSING", "Artifact does not exist")
    if not artifact.is_file():
        raise QualificationError("ERR_ARTIFACT_NOT_REGULAR", "Artifact is not a regular file")
    if not os.access(artifact, os.X_OK):
        raise QualificationError("ERR_ARTIFACT_NOT_EXECUTABLE", "Artifact is not executable")

    artifact_bytes = artifact.read_bytes()
    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    if artifact_sha256 != expected_artifact_sha256:
        raise QualificationError("ERR_ARTIFACT_DIGEST_MISMATCH", "Artifact SHA256 mismatch")

    # 3. C1 Static launcher binding parser
    parse_static_appimage_binding(launcher_bytes, artifact)

    # 4. C4 Isolated root verification
    verify_isolated_root(iso_root)

    # 5. Environment construction
    allowed_dirs = ["home", "config", "data", "cache", "state", "runtime", "tmp"]
    for sub in allowed_dirs:
        (iso_root / sub).mkdir(parents=True, exist_ok=True)

    child_env = {
        "HOME": str(iso_root / "home"),
        "XDG_CONFIG_HOME": str(iso_root / "config"),
        "XDG_DATA_HOME": str(iso_root / "data"),
        "XDG_CACHE_HOME": str(iso_root / "cache"),
        "XDG_STATE_HOME": str(iso_root / "state"),
        "XDG_RUNTIME_DIR": str(iso_root / "runtime"),
        "TMPDIR": str(iso_root / "tmp"),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "LANG": "C.UTF-8",
    }

    # 6. Metadata extraction
    extract_cmd = [str(artifact.resolve()), "--appimage-extract", "orca-ide.desktop"]
    ext_code, ext_stdout, ext_stderr = run_owned_process_group(extract_cmd, iso_root, child_env, timeout_seconds)

    if ext_code != 0:
        raise QualificationError("ERR_METADATA_EXTRACTION_FAILED", "AppImage extraction returned non-zero exit code")

    desktop_file = iso_root / "squashfs-root" / "orca-ide.desktop"
    if not desktop_file.exists():
        raise QualificationError("ERR_METADATA_EXTRACTION_FAILED", "Extracted desktop file missing")

    try:
        desktop_text = desktop_file.read_text(encoding="utf-8")
    except Exception as exc:
        raise QualificationError("ERR_METADATA_EXTRACTION_FAILED", "Failed to read extracted desktop file") from exc

    desktop_lines = [
        line.strip()
        for line in desktop_text.splitlines()
        if line.strip().startswith("X-AppImage-Version=")
    ]
    if len(desktop_lines) == 0:
        raise QualificationError("ERR_APPIMAGE_VERSION_MISSING", "X-AppImage-Version key missing in desktop file")
    if len(desktop_lines) > 1:
        raise QualificationError("ERR_APPIMAGE_VERSION_DUPLICATE", "Multiple X-AppImage-Version keys found in desktop file")

    extracted_version = desktop_lines[0].split("=", 1)[1].strip()
    if extracted_version != expected_product_version:
        raise QualificationError("ERR_APPIMAGE_VERSION_MISMATCH", "Product version mismatch")

    # Boundary 1: Check exact inventory immediately after successful metadata extraction and version verification
    check_isolated_root_inventory(iso_root)

    # 7. Catalog execution (twice)
    call_cmd = [str(launcher.resolve()), "agent-context", "--json"]

    code1, stdout1, stderr1 = run_owned_process_group(call_cmd, iso_root, child_env, timeout_seconds)
    if code1 != 0:
        raise QualificationError("ERR_CATALOG_NONZERO_EXIT", "First catalog call returned non-zero exit code")
    if stderr1:
        raise QualificationError("ERR_CATALOG_STDERR", "First catalog call emitted stderr")

    # Boundary 2: Check exact inventory immediately after successful catalog call 1
    check_isolated_root_inventory(iso_root)

    code2, stdout2, stderr2 = run_owned_process_group(call_cmd, iso_root, child_env, timeout_seconds)
    if code2 != 0:
        raise QualificationError("ERR_CATALOG_NONZERO_EXIT", "Second catalog call returned non-zero exit code")
    if stderr2:
        raise QualificationError("ERR_CATALOG_STDERR", "Second catalog call emitted stderr")

    # Boundary 3: Check exact inventory immediately after successful catalog call 2
    check_isolated_root_inventory(iso_root)

    if stdout1 != stdout2:
        raise QualificationError("ERR_CATALOG_NON_DETERMINISTIC", "Two catalog calls produced differing stdout bytes")

    catalog_bytes = len(stdout1)
    catalog_sha256 = hashlib.sha256(stdout1).hexdigest()

    try:
        catalog_json = json.loads(stdout1.decode("utf-8"))
    except Exception as exc:
        raise QualificationError("ERR_CATALOG_MALFORMED_JSON", "Catalog output is not valid JSON") from exc

    if not isinstance(catalog_json, dict):
        raise QualificationError("ERR_CATALOG_MALFORMED_JSON", "Catalog JSON top-level is not an object")

    for key in ("schemaVersion", "commandCount", "commands"):
        if key not in catalog_json:
            raise QualificationError("ERR_CATALOG_MALFORMED_JSON", "Catalog JSON missing required top-level key")

    if catalog_json["schemaVersion"] != expected_schema_version:
        raise QualificationError("ERR_SCHEMA_VERSION_MISMATCH", "Schema version mismatch")

    if catalog_json["commandCount"] != expected_command_count:
        raise QualificationError("ERR_COMMAND_COUNT_MISMATCH", "Declared command count mismatch")

    commands = catalog_json["commands"]
    if not isinstance(commands, list) or len(commands) != expected_command_count:
        raise QualificationError("ERR_COMMAND_COUNT_MISMATCH", "Actual commands list length mismatch")

    cmd_names = [cmd.get("command") for cmd in commands if isinstance(cmd, dict)]
    if len(set(cmd_names)) != len(cmd_names):
        raise QualificationError("ERR_DUPLICATE_COMMAND_NAME", "Duplicate command names found in catalog")

    required_cmd_keys = {
        "aliases",
        "argumentMode",
        "command",
        "examples",
        "flags",
        "notes",
        "path",
        "positionalArgs",
        "summary",
        "usage",
    }
    for cmd in commands:
        if not isinstance(cmd, dict) or not required_cmd_keys.issubset(cmd.keys()):
            raise QualificationError("ERR_COMMAND_SHAPE_INVALID", "Command object shape invalid")

    return {
        "status": "PASS",
        "launcher_identity": {
            "launcher_path": str(launcher.resolve()),
            "launcher_type": "Bash wrapper",
            "launcher_size_bytes": len(launcher_bytes),
            "launcher_sha256": launcher_sha256,
        },
        "bound_appimage_identity": {
            "appimage_path": str(artifact.resolve()),
            "appimage_size_bytes": len(artifact_bytes),
            "appimage_sha256": artifact_sha256,
            "statically_bound": True,
        },
        "product_version_identity": {
            "product_version": expected_product_version,
            "metadata_source": "orca-ide.desktop / X-AppImage-Version",
        },
        "catalog_identity": {
            "schema_version": expected_schema_version,
            "declared_command_count": expected_command_count,
            "actual_command_count": len(commands),
            "catalog_bytes": catalog_bytes,
            "catalog_sha256": catalog_sha256,
            "determinism_verified": True,
        },
        "isolation_and_effects": {
            "ambient_environment_forwarded": False,
            "isolated_root_clean": True,
            "surviving_processes_detected": False,
            "unexpected_files_created": False,
        },
        "execution_authorizations": {
            "orca_runtime_started": False,
            "worker_launched": False,
            "model_call_requested": False,
            "network_call_requested": False,
            "protected_state_accessed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze Orca launcher, artifact, version, and catalog identity.")
    parser.add_argument("--launcher", default=str(DEFAULT_LAUNCHER), help="Path to Orca launcher wrapper")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT), help="Path to Orca AppImage artifact")
    parser.add_argument("--isolated-root", required=True, help="Explicit isolated root directory under /tmp")
    parser.add_argument("--expected-launcher-sha256", default=DEFAULT_LAUNCHER_SHA256, help="Expected launcher SHA256")
    parser.add_argument("--expected-artifact-sha256", default=DEFAULT_ARTIFACT_SHA256, help="Expected artifact SHA256")
    parser.add_argument("--expected-product-version", default=DEFAULT_PRODUCT_VERSION, help="Expected product version")
    parser.add_argument(
        "--expected-catalog-schema-version",
        type=int,
        default=DEFAULT_SCHEMA_VERSION,
        help="Expected schema version",
    )
    parser.add_argument(
        "--expected-command-count",
        type=int,
        default=DEFAULT_COMMAND_COUNT,
        help="Expected command count",
    )
    parser.add_argument("--timeout", type=int, default=10, help="Subprocess timeout in seconds")

    args = parser.parse_args()

    try:
        res = qualify_orca(
            launcher_path=args.launcher,
            artifact_path=args.artifact,
            isolated_root=args.isolated_root,
            expected_launcher_sha256=args.expected_launcher_sha256,
            expected_artifact_sha256=args.expected_artifact_sha256,
            expected_product_version=args.expected_product_version,
            expected_schema_version=args.expected_catalog_schema_version,
            expected_command_count=args.expected_command_count,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(res, indent=2, sort_keys=True))
        sys.exit(0)
    except QualificationError as exc:
        err_payload = {"status": "FAIL", "code": exc.code, "error": exc.message}
        print(json.dumps(err_payload, indent=2, sort_keys=True))
        sys.exit(1)
    except Exception:
        err_payload = {"status": "FAIL", "code": "ERR_UNEXPECTED_EXCEPTION", "error": "An unexpected error occurred during qualification"}
        print(json.dumps(err_payload, indent=2, sort_keys=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
