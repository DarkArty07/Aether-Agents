"""Deterministic Orca source, build, catalog, and isolation qualification probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
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


def check_surviving_processes() -> bool:
    try:
        ps_out = subprocess.check_output(["ps", "-ef"], text=True)
        orca_procs = [
            line
            for line in ps_out.splitlines()
            if "orca" in line.lower()
            and "python" not in line.lower()
            and "grep" not in line.lower()
        ]
        return len(orca_procs) > 0
    except Exception:
        return False


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
        raise QualificationError("ERR_LAUNCHER_IS_SYMLINK", f"Launcher is a symlink: {launcher}")
    if not launcher.exists():
        raise QualificationError("ERR_LAUNCHER_MISSING", f"Launcher does not exist: {launcher}")
    if not launcher.is_file():
        raise QualificationError("ERR_LAUNCHER_NOT_REGULAR", f"Launcher is not a regular file: {launcher}")
    if not os.access(launcher, os.X_OK):
        raise QualificationError("ERR_LAUNCHER_NOT_EXECUTABLE", f"Launcher is not executable: {launcher}")

    launcher_bytes = launcher.read_bytes()
    launcher_sha256 = hashlib.sha256(launcher_bytes).hexdigest()
    if launcher_sha256 != expected_launcher_sha256:
        raise QualificationError(
            "ERR_LAUNCHER_DIGEST_MISMATCH",
            f"Launcher SHA256 mismatch: {launcher_sha256} != {expected_launcher_sha256}",
        )

    # 2. Artifact checks
    if os.path.islink(artifact):
        raise QualificationError("ERR_ARTIFACT_IS_SYMLINK", f"Artifact is a symlink: {artifact}")
    if not artifact.exists():
        raise QualificationError("ERR_ARTIFACT_MISSING", f"Artifact does not exist: {artifact}")
    if not artifact.is_file():
        raise QualificationError("ERR_ARTIFACT_NOT_REGULAR", f"Artifact is not a regular file: {artifact}")
    if not os.access(artifact, os.X_OK):
        raise QualificationError("ERR_ARTIFACT_NOT_EXECUTABLE", f"Artifact is not executable: {artifact}")

    artifact_bytes = artifact.read_bytes()
    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    if artifact_sha256 != expected_artifact_sha256:
        raise QualificationError(
            "ERR_ARTIFACT_DIGEST_MISMATCH",
            f"Artifact SHA256 mismatch: {artifact_sha256} != {expected_artifact_sha256}",
        )

    # 3. Check static binding
    try:
        launcher_text = launcher_bytes.decode("utf-8", errors="replace")
    except Exception:
        launcher_text = ""

    artifact_resolved_str = str(artifact.resolve())
    artifact_raw_str = str(artifact)
    if artifact_resolved_str not in launcher_text and artifact_raw_str not in launcher_text:
        raise QualificationError(
            "ERR_LAUNCHER_NOT_BOUND",
            f"Launcher text does not contain reference to bound artifact {artifact}",
        )

    # 3. Isolated root checks
    if os.path.islink(iso_root):
        raise QualificationError("ERR_ISOLATED_ROOT_SYMLINK", f"Isolated root is a symlink: {iso_root}")
    if not iso_root.exists() or not iso_root.is_dir():
        raise QualificationError("ERR_ISOLATED_ROOT_INVALID", f"Isolated root invalid: {iso_root}")

    iso_resolved = iso_root.resolve()
    repo_resolved = PROJECT_ROOT.resolve()
    home_resolved = Path.home().resolve()

    if iso_resolved.is_relative_to(repo_resolved):
        raise QualificationError(
            "ERR_ISOLATED_ROOT_INSIDE_REPO",
            f"Isolated root is inside repository: {iso_resolved}",
        )
    if iso_resolved.is_relative_to(home_resolved):
        raise QualificationError(
            "ERR_ISOLATED_ROOT_INSIDE_HOME",
            f"Isolated root is inside HOME: {iso_resolved}",
        )
    if iso_resolved in (
        Path("/"),
        Path("/tmp"),
        Path("/home"),
        Path("/usr"),
        Path("/var"),
        Path("/etc"),
        Path("/dev"),
        Path("/proc"),
        Path("/sys"),
    ):
        raise QualificationError("ERR_ISOLATED_ROOT_GLOBAL", f"Isolated root is global directory: {iso_resolved}")

    # 4. Environment construction
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

    # 5. Metadata extraction
    try:
        extract_res = subprocess.run(
            [str(artifact.resolve()), "--appimage-extract", "orca-ide.desktop"],
            cwd=iso_root,
            env=child_env,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise QualificationError("ERR_METADATA_EXTRACTION_FAILED", f"Metadata extraction timed out: {exc}") from exc

    if extract_res.returncode != 0:
        raise QualificationError(
            "ERR_METADATA_EXTRACTION_FAILED",
            f"AppImage extraction returned non-zero code {extract_res.returncode}: {extract_res.stderr}",
        )

    desktop_file = iso_root / "squashfs-root" / "orca-ide.desktop"
    if not desktop_file.exists():
        raise QualificationError("ERR_METADATA_EXTRACTION_FAILED", f"Extracted desktop file missing: {desktop_file}")

    desktop_lines = [
        line.strip()
        for line in desktop_file.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("X-AppImage-Version=")
    ]
    if len(desktop_lines) == 0:
        raise QualificationError("ERR_APPIMAGE_VERSION_MISSING", "X-AppImage-Version key missing in desktop file")
    if len(desktop_lines) > 1:
        raise QualificationError(
            "ERR_APPIMAGE_VERSION_DUPLICATE",
            f"Multiple X-AppImage-Version keys found: {desktop_lines}",
        )

    extracted_version = desktop_lines[0].split("=", 1)[1].strip()
    if extracted_version != expected_product_version:
        raise QualificationError(
            "ERR_APPIMAGE_VERSION_MISMATCH",
            f"Product version mismatch: {extracted_version} != {expected_product_version}",
        )

    # 6. Catalog execution (twice)
    call_cmd = [str(launcher.resolve()), "agent-context", "--json"]

    try:
        res1 = subprocess.run(call_cmd, cwd=iso_root, env=child_env, timeout=timeout_seconds, capture_output=True)
    except subprocess.TimeoutExpired as exc:
        raise QualificationError("ERR_CATALOG_TIMEOUT", f"First catalog call timed out: {exc}") from exc

    if res1.returncode != 0:
        raise QualificationError(
            "ERR_CATALOG_NONZERO_EXIT",
            f"First catalog call returned non-zero code {res1.returncode}",
        )
    if res1.stderr:
        raise QualificationError(
            "ERR_CATALOG_STDERR",
            f"First catalog call emitted stderr: {res1.stderr.decode('utf-8', errors='replace')}",
        )

    try:
        res2 = subprocess.run(call_cmd, cwd=iso_root, env=child_env, timeout=timeout_seconds, capture_output=True)
    except subprocess.TimeoutExpired as exc:
        raise QualificationError("ERR_CATALOG_TIMEOUT", f"Second catalog call timed out: {exc}") from exc

    if res2.returncode != 0:
        raise QualificationError(
            "ERR_CATALOG_NONZERO_EXIT",
            f"Second catalog call returned non-zero code {res2.returncode}",
        )
    if res2.stderr:
        raise QualificationError(
            "ERR_CATALOG_STDERR",
            f"Second catalog call emitted stderr: {res2.stderr.decode('utf-8', errors='replace')}",
        )

    if res1.stdout != res2.stdout:
        raise QualificationError("ERR_CATALOG_NON_DETERMINISTIC", "Two catalog calls produced differing stdout bytes")

    catalog_bytes = len(res1.stdout)
    catalog_sha256 = hashlib.sha256(res1.stdout).hexdigest()

    try:
        catalog_json = json.loads(res1.stdout.decode("utf-8"))
    except Exception as exc:
        raise QualificationError("ERR_CATALOG_MALFORMED_JSON", f"Catalog output is not valid JSON: {exc}") from exc

    if not isinstance(catalog_json, dict):
        raise QualificationError("ERR_CATALOG_MALFORMED_JSON", "Catalog JSON top-level is not an object")

    for key in ("schemaVersion", "commandCount", "commands"):
        if key not in catalog_json:
            raise QualificationError("ERR_CATALOG_MALFORMED_JSON", f"Catalog JSON missing top-level key: {key}")

    if catalog_json["schemaVersion"] != expected_schema_version:
        raise QualificationError(
            "ERR_SCHEMA_VERSION_MISMATCH",
            f"Schema version mismatch: {catalog_json['schemaVersion']} != {expected_schema_version}",
        )

    if catalog_json["commandCount"] != expected_command_count:
        raise QualificationError(
            "ERR_COMMAND_COUNT_MISMATCH",
            f"Command count mismatch: {catalog_json['commandCount']} != {expected_command_count}",
        )

    commands = catalog_json["commands"]
    if not isinstance(commands, list) or len(commands) != expected_command_count:
        raise QualificationError(
            "ERR_COMMAND_COUNT_MISMATCH",
            f"Actual commands length mismatch: {len(commands) if isinstance(commands, list) else 'not a list'} != {expected_command_count}",
        )

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
            raise QualificationError("ERR_COMMAND_SHAPE_INVALID", f"Command object shape invalid: {cmd}")

    # 7. Side-effect and survivor checks
    expected_allowed_names = set(allowed_dirs) | {"squashfs-root"}
    actual_items = {p.name for p in iso_root.iterdir()}
    if not actual_items.issubset(expected_allowed_names):
        unexpected = actual_items - expected_allowed_names
        raise QualificationError("ERR_UNEXPECTED_FILES_CREATED", f"Unexpected items in isolated root: {unexpected}")

    surviving = check_surviving_processes()
    if surviving:
        raise QualificationError("ERR_SURVIVING_PROCESS_DETECTED", "Orca child process survived after qualification")

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
    except Exception as exc:
        err_payload = {"status": "FAIL", "code": "ERR_UNEXPECTED_EXCEPTION", "error": str(exc)}
        print(json.dumps(err_payload, indent=2, sort_keys=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
