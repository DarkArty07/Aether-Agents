"""Canonical exact-byte Orca candidate qualification probe."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_MANIFEST = PROJECT_ROOT / "docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json"
CANONICAL_MANIFEST_RELATIVE = "docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json"
CANONICAL_MANIFEST_SHA256 = "186e7409a9d942319a802d2a6ac1b4cec95f0ab2c48c97907ec7729a3faa8cfe"


class QualificationError(Exception):
    """Safe, stable failure from the candidate qualification boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise QualificationError(code, message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        _fail("ERR_CANDIDATE_READ_FAILED", "Candidate bytes could not be read")
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _expect_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    return value


def _expect_exact_keys(value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")


def _expect_string(value: Any, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    return value


def _expect_int(value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    return value


def _expect_bool(value: Any) -> bool:
    if not isinstance(value, bool):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    return value


def _expect_string_list(value: Any, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    if any(not isinstance(item, str) or not item for item in value):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    if len(set(value)) != len(value):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest shape is invalid")
    return value


def _validate_manifest(data: dict[str, Any]) -> dict[str, Any]:
    _expect_exact_keys(
        data,
        {
            "schema_version",
            "candidate_id",
            "qualification_policy",
            "launcher",
            "appimage",
            "binding_review",
            "product_version",
            "catalog",
            "isolation",
            "authorized_child_operations",
        },
    )
    if _expect_int(data["schema_version"], minimum=1) != 1:
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest schema is unsupported")
    _expect_string(data["candidate_id"])
    if _expect_string(data["qualification_policy"]) != "candidate_specific_exact_bytes_v1":
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest policy is unsupported")

    launcher = _expect_object(data["launcher"])
    _expect_exact_keys(launcher, {"path", "size_bytes", "sha256", "kind", "executable_required"})
    launcher_path = Path(_expect_string(launcher["path"]))
    if not launcher_path.is_absolute():
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest path is invalid")
    _expect_int(launcher["size_bytes"], minimum=1)
    if not re.fullmatch(r"[0-9a-f]{64}", _expect_string(launcher["sha256"])):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest digest is invalid")
    if _expect_string(launcher["kind"]) != "bash_wrapper" or not _expect_bool(launcher["executable_required"]):
        _fail("ERR_MANIFEST_INVALID", "Canonical launcher policy is invalid")

    appimage = _expect_object(data["appimage"])
    _expect_exact_keys(appimage, {"path", "size_bytes", "sha256", "executable_required"})
    appimage_path = Path(_expect_string(appimage["path"]))
    if not appimage_path.is_absolute():
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest path is invalid")
    _expect_int(appimage["size_bytes"], minimum=1)
    if not re.fullmatch(r"[0-9a-f]{64}", _expect_string(appimage["sha256"])):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest digest is invalid")
    if not _expect_bool(appimage["executable_required"]):
        _fail("ERR_MANIFEST_INVALID", "Canonical AppImage policy is invalid")

    binding = _expect_object(data["binding_review"])
    _expect_exact_keys(binding, {"method", "launcher_sha256", "expected_appimage_path", "acceptance_record"})
    if _expect_string(binding["method"]) != "manual_static_review_of_exact_launcher_bytes":
        _fail("ERR_MANIFEST_INVALID", "Canonical binding review is invalid")
    if binding["launcher_sha256"] != launcher["sha256"]:
        _fail("ERR_MANIFEST_INVALID", "Canonical binding review is inconsistent")
    if binding["expected_appimage_path"] != appimage["path"]:
        _fail("ERR_MANIFEST_INVALID", "Canonical binding review is inconsistent")
    _expect_string(binding["acceptance_record"])

    version = _expect_object(data["product_version"])
    _expect_exact_keys(version, {"value", "source", "extract_member"})
    _expect_string(version["value"])
    if _expect_string(version["source"]) != "orca-ide.desktop / X-AppImage-Version":
        _fail("ERR_MANIFEST_INVALID", "Canonical version source is invalid")
    if _expect_string(version["extract_member"]) != "orca-ide.desktop":
        _fail("ERR_MANIFEST_INVALID", "Canonical extraction member is invalid")

    catalog = _expect_object(data["catalog"])
    _expect_exact_keys(
        catalog,
        {
            "command",
            "schema_version",
            "declared_command_count",
            "actual_command_count",
            "bytes",
            "sha256",
            "required_command_keys",
        },
    )
    if _expect_string_list(catalog["command"], nonempty=True) != ["agent-context", "--json"]:
        _fail("ERR_MANIFEST_INVALID", "Canonical catalog command is invalid")
    _expect_int(catalog["schema_version"], minimum=1)
    declared = _expect_int(catalog["declared_command_count"], minimum=1)
    actual = _expect_int(catalog["actual_command_count"], minimum=1)
    if declared != actual:
        _fail("ERR_MANIFEST_INVALID", "Canonical catalog counts are inconsistent")
    _expect_int(catalog["bytes"], minimum=1)
    if not re.fullmatch(r"[0-9a-f]{64}", _expect_string(catalog["sha256"])):
        _fail("ERR_MANIFEST_INVALID", "Canonical catalog digest is invalid")
    _expect_string_list(catalog["required_command_keys"], nonempty=True)

    isolation = _expect_object(data["isolation"])
    _expect_exact_keys(
        isolation,
        {
            "root_parent",
            "root_prefix",
            "required_directories",
            "required_files",
            "process_timeout_seconds",
            "cleanup_timeout_ms",
            "cleanup_poll_interval_ms",
            "transient_fuse_name_regex",
            "transient_fuse_condition",
            "final_inventory_exceptions",
        },
    )
    if _expect_string(isolation["root_parent"]) != "/tmp":
        _fail("ERR_MANIFEST_INVALID", "Canonical isolation parent is invalid")
    if _expect_string(isolation["root_prefix"]) != "aether-m1-1b-":
        _fail("ERR_MANIFEST_INVALID", "Canonical isolation prefix is invalid")
    required_directories = _expect_string_list(isolation["required_directories"], nonempty=True)
    if set(required_directories) != {"cache", "config", "data", "home", "runtime", "squashfs-root", "state", "tmp"}:
        _fail("ERR_MANIFEST_INVALID", "Canonical isolation inventory is invalid")
    if _expect_string_list(isolation["required_files"], nonempty=True) != ["squashfs-root/orca-ide.desktop"]:
        _fail("ERR_MANIFEST_INVALID", "Canonical isolation inventory is invalid")
    _expect_int(isolation["process_timeout_seconds"], minimum=1)
    cleanup_timeout = _expect_int(isolation["cleanup_timeout_ms"], minimum=1)
    poll_interval = _expect_int(isolation["cleanup_poll_interval_ms"], minimum=1)
    if poll_interval > cleanup_timeout:
        _fail("ERR_MANIFEST_INVALID", "Canonical cleanup policy is invalid")
    if _expect_string(isolation["transient_fuse_name_regex"]) != r"^\.mount_orca-[A-Za-z0-9]+$":
        _fail("ERR_MANIFEST_INVALID", "Canonical cleanup matcher is invalid")
    if (
        _expect_string(isolation["transient_fuse_condition"])
        != "direct_tmp_child_real_directory_scandir_errno_ENOTCONN_then_must_disappear"
    ):
        _fail("ERR_MANIFEST_INVALID", "Canonical cleanup condition is invalid")
    if isolation["final_inventory_exceptions"] != []:
        _fail("ERR_MANIFEST_INVALID", "Canonical inventory exceptions are forbidden")

    operations = data["authorized_child_operations"]
    if not isinstance(operations, list) or len(operations) != 2:
        _fail("ERR_MANIFEST_INVALID", "Canonical child operations are invalid")
    extract = _expect_object(operations[0])
    _expect_exact_keys(extract, {"executable", "arguments"})
    if extract != {"executable": "appimage", "arguments": ["--appimage-extract", version["extract_member"]]}:
        _fail("ERR_MANIFEST_INVALID", "Canonical child operations are invalid")
    catalog_op = _expect_object(operations[1])
    _expect_exact_keys(catalog_op, {"executable", "arguments", "exact_calls"})
    if catalog_op != {"executable": "launcher", "arguments": catalog["command"], "exact_calls": 2}:
        _fail("ERR_MANIFEST_INVALID", "Canonical child operations are invalid")

    return data


def load_manifest(
    manifest_path: str | Path = CANONICAL_MANIFEST,
    expected_manifest_sha256: str = CANONICAL_MANIFEST_SHA256,
) -> tuple[dict[str, Any], str]:
    """Load one exact manifest after authenticating its committed bytes."""
    path = Path(manifest_path)
    try:
        payload = path.read_bytes()
    except OSError:
        _fail("ERR_MANIFEST_MISSING", "Canonical manifest is unavailable")
    digest = _sha256_bytes(payload)
    if digest != expected_manifest_sha256:
        _fail("ERR_MANIFEST_DIGEST_MISMATCH", "Canonical manifest digest mismatch")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("ERR_MANIFEST_INVALID", "Canonical manifest is not valid JSON")
    return _validate_manifest(_expect_object(decoded)), digest


def _verify_candidate_file(section: dict[str, Any], *, kind: str) -> tuple[Path, int, str]:
    path = Path(section["path"])
    prefix = "LAUNCHER" if kind == "launcher" else "ARTIFACT"
    if path.is_symlink():
        _fail(f"ERR_{prefix}_IS_SYMLINK", "Candidate path is a symlink")
    if not path.exists():
        _fail(f"ERR_{prefix}_MISSING", "Candidate path is missing")
    if not path.is_file():
        _fail(f"ERR_{prefix}_NOT_REGULAR", "Candidate path is not a regular file")
    if section["executable_required"] and not os.access(path, os.X_OK):
        _fail(f"ERR_{prefix}_NOT_EXECUTABLE", "Candidate path is not executable")
    try:
        size = path.stat().st_size
    except OSError:
        _fail("ERR_CANDIDATE_READ_FAILED", "Candidate identity could not be read")
    if size != section["size_bytes"]:
        _fail(f"ERR_{prefix}_SIZE_MISMATCH", "Candidate size mismatch")
    digest = _sha256_file(path)
    if digest != section["sha256"]:
        _fail(f"ERR_{prefix}_DIGEST_MISMATCH", "Candidate digest mismatch")
    return path, size, digest


def run_owned_process_group(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, bytes, bytes]:
    """Run one exact argv in an owned process group and reap descendants."""
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
        except Exception:
            _fail("ERR_CHILD_LAUNCH_FAILED", "Qualified child could not be launched")

        pgid = proc.pid
        timed_out = False
        try:
            proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            group_alive = True
            if not timed_out:
                natural_deadline = time.monotonic() + 0.5
                while time.monotonic() < natural_deadline:
                    try:
                        os.killpg(pgid, 0)
                    except ProcessLookupError:
                        group_alive = False
                        break
                    time.sleep(0.02)
            if group_alive:
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    group_alive = False
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass

            deadline = time.monotonic() + 0.5
            while group_alive and time.monotonic() < deadline:
                try:
                    os.killpg(pgid, 0)
                except ProcessLookupError:
                    group_alive = False
                    break
                time.sleep(0.02)
            if group_alive:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    group_alive = False
                deadline = time.monotonic() + 0.5
                while group_alive and time.monotonic() < deadline:
                    try:
                        os.killpg(pgid, 0)
                    except ProcessLookupError:
                        group_alive = False
                        break
                    time.sleep(0.02)
                if group_alive:
                    _fail("ERR_SURVIVING_PROCESS_DETECTED", "Qualified child process survived cleanup")

        # The exact AppImage can finish its process group just before the kernel
        # completes mount teardown. This bounded settle happens before the
        # post-child boundary; it does not admit or ignore any filesystem entry.
        time.sleep(0.1)
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read()
        stderr = stderr_file.read()

    if timed_out:
        _fail("ERR_CHILD_TIMEOUT", "Qualified child exceeded its bounded timeout")
    return proc.returncode, stdout, stderr


def verify_isolated_root(iso_root: Path, isolation: dict[str, Any]) -> None:
    """Require one direct, non-symlink child of the frozen isolation parent."""
    current = iso_root
    while current != current.parent:
        if current.is_symlink():
            _fail("ERR_ISOLATED_ROOT_SYMLINK", "Isolated root contains a symlink component")
        current = current.parent
    if not iso_root.exists() or not iso_root.is_dir():
        _fail("ERR_ISOLATED_ROOT_INVALID", "Isolated root is unavailable")
    resolved = iso_root.resolve()
    parent = Path(isolation["root_parent"]).resolve()
    if resolved.parent != parent or not resolved.name.startswith(isolation["root_prefix"]):
        _fail("ERR_ISOLATED_ROOT_INVALID", "Isolated root is outside the admitted boundary")


def wait_for_transient_fuse_cleanup(iso_root: Path, isolation: dict[str, Any]) -> None:
    """Wait only for a positively identified disconnected direct FUSE endpoint."""
    tmp_root = iso_root / "tmp"
    try:
        entries = list(os.scandir(tmp_root))
    except OSError:
        _fail("ERR_UNEXPECTED_FILES_CREATED", "Isolated temporary directory is unreadable")
    matcher = re.compile(isolation["transient_fuse_name_regex"])
    for entry in entries:
        if not matcher.fullmatch(entry.name):
            continue
        path = Path(entry.path)
        try:
            mode = os.lstat(path).st_mode
        except OSError:
            _fail("ERR_UNEXPECTED_FILES_CREATED", "Transient candidate type is invalid")
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            _fail("ERR_UNEXPECTED_FILES_CREATED", "Transient candidate type is invalid")
        try:
            with os.scandir(path) as contents:
                list(contents)
        except OSError as exc:
            if exc.errno != errno.ENOTCONN:
                _fail("ERR_UNEXPECTED_FILES_CREATED", "Transient candidate is not a disconnected endpoint")
        else:
            _fail("ERR_UNEXPECTED_FILES_CREATED", "Readable transient-prefixed directory is forbidden")

        deadline = time.monotonic() + isolation["cleanup_timeout_ms"] / 1000
        while time.monotonic() < deadline:
            try:
                os.lstat(path)
            except FileNotFoundError:
                break
            except OSError:
                _fail("ERR_UNEXPECTED_FILES_CREATED", "Transient endpoint cleanup state is invalid")
            time.sleep(isolation["cleanup_poll_interval_ms"] / 1000)
        else:
            _fail("ERR_TRANSIENT_CLEANUP_TIMEOUT", "Disconnected transient endpoint did not disappear")


def check_isolated_root_inventory(iso_root: Path, isolation: dict[str, Any]) -> None:
    """Require exact recursive directory/file equality with zero exceptions."""
    expected_dirs = {Path(item) for item in isolation["required_directories"]}
    expected_files = {Path(item) for item in isolation["required_files"]}
    seen_dirs: set[Path] = set()
    seen_files: set[Path] = set()
    stack = [iso_root]

    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            _fail("ERR_UNEXPECTED_FILES_CREATED", "Isolated root inventory is unreadable")
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(iso_root)
            if entry.is_symlink():
                _fail("ERR_UNEXPECTED_FILES_CREATED", "Symlink found in isolated root")
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError:
                _fail("ERR_UNEXPECTED_FILES_CREATED", "Isolated root entry type is unreadable")
            if stat.S_ISDIR(mode):
                seen_dirs.add(relative)
                stack.append(path)
            elif stat.S_ISREG(mode):
                seen_files.add(relative)
            else:
                _fail("ERR_UNEXPECTED_FILES_CREATED", "Non-regular entry found in isolated root")

    if seen_dirs != expected_dirs or seen_files != expected_files:
        _fail("ERR_UNEXPECTED_FILES_CREATED", "Isolated root inventory differs from the canonical manifest")


def _post_child_boundary(iso_root: Path, isolation: dict[str, Any]) -> None:
    wait_for_transient_fuse_cleanup(iso_root, isolation)
    check_isolated_root_inventory(iso_root, isolation)


def _catalog_identity(payload: bytes, catalog: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
    if len(payload) != catalog["bytes"] or _sha256_bytes(payload) != catalog["sha256"]:
        _fail("ERR_CATALOG_IDENTITY_MISMATCH", "Catalog bytes differ from the canonical manifest")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("ERR_CATALOG_MALFORMED_JSON", "Catalog output is not valid JSON")
    if not isinstance(decoded, dict) or set(("schemaVersion", "commandCount", "commands")) - set(decoded):
        _fail("ERR_CATALOG_MALFORMED_JSON", "Catalog object shape is invalid")
    if decoded["schemaVersion"] != catalog["schema_version"]:
        _fail("ERR_SCHEMA_VERSION_MISMATCH", "Catalog schema version mismatch")
    if decoded["commandCount"] != catalog["declared_command_count"]:
        _fail("ERR_COMMAND_COUNT_MISMATCH", "Catalog declared command count mismatch")
    commands = decoded["commands"]
    if not isinstance(commands, list) or len(commands) != catalog["actual_command_count"]:
        _fail("ERR_COMMAND_COUNT_MISMATCH", "Catalog command list length mismatch")
    required = set(catalog["required_command_keys"])
    names: list[str] = []
    for command in commands:
        if not isinstance(command, dict) or not required.issubset(command):
            _fail("ERR_COMMAND_SHAPE_INVALID", "Catalog command shape is invalid")
        name = command.get("command")
        if not isinstance(name, str):
            _fail("ERR_COMMAND_SHAPE_INVALID", "Catalog command identity is invalid")
        names.append(name)
    if len(names) != len(set(names)):
        _fail("ERR_DUPLICATE_COMMAND_NAME", "Catalog contains duplicate command identities")
    return decoded, len(payload), _sha256_bytes(payload)


def qualify_orca(
    *,
    isolated_root: str | Path,
    manifest_path: str | Path = CANONICAL_MANIFEST,
    expected_manifest_sha256: str = CANONICAL_MANIFEST_SHA256,
) -> dict[str, Any]:
    """Qualify only the exact candidate admitted by an authenticated manifest."""
    manifest, manifest_digest = load_manifest(manifest_path, expected_manifest_sha256)
    launcher, launcher_size, launcher_digest = _verify_candidate_file(manifest["launcher"], kind="launcher")
    appimage, appimage_size, appimage_digest = _verify_candidate_file(manifest["appimage"], kind="artifact")
    iso_root = Path(isolated_root)
    isolation = manifest["isolation"]
    verify_isolated_root(iso_root, isolation)

    for directory in isolation["required_directories"]:
        if directory != "squashfs-root":
            (iso_root / directory).mkdir(parents=True, exist_ok=True)
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
    timeout = isolation["process_timeout_seconds"]

    extract_args = manifest["authorized_child_operations"][0]["arguments"]
    code, _stdout, _stderr = run_owned_process_group([str(appimage), *extract_args], iso_root, child_env, timeout)
    if code != 0:
        _fail("ERR_METADATA_EXTRACTION_FAILED", "AppImage metadata extraction failed")
    desktop = iso_root / manifest["isolation"]["required_files"][0]
    try:
        lines = [line.strip() for line in desktop.read_text(encoding="utf-8").splitlines()]
    except Exception:
        _fail("ERR_METADATA_EXTRACTION_FAILED", "AppImage metadata is unavailable")
    version_lines = [line for line in lines if line.startswith("X-AppImage-Version=")]
    if len(version_lines) != 1:
        _fail("ERR_APPIMAGE_VERSION_INVALID", "AppImage version metadata is invalid")
    if version_lines[0].split("=", 1)[1].strip() != manifest["product_version"]["value"]:
        _fail("ERR_APPIMAGE_VERSION_MISMATCH", "AppImage version mismatch")
    _post_child_boundary(iso_root, isolation)

    catalog_args = manifest["authorized_child_operations"][1]["arguments"]
    outputs: list[bytes] = []
    for call_number in range(2):
        code, stdout, stderr = run_owned_process_group([str(launcher), *catalog_args], iso_root, child_env, timeout)
        if code != 0:
            _fail("ERR_CATALOG_NONZERO_EXIT", "Catalog child returned a nonzero status")
        if stderr:
            _fail("ERR_CATALOG_STDERR", "Catalog child emitted stderr")
        outputs.append(stdout)
        _post_child_boundary(iso_root, isolation)
        if call_number == 1 and outputs[0] != outputs[1]:
            _fail("ERR_CATALOG_NON_DETERMINISTIC", "Catalog output changed between exact probes")

    _catalog, catalog_bytes, catalog_digest = _catalog_identity(outputs[0], manifest["catalog"])
    _, final_launcher_size, final_launcher_digest = _verify_candidate_file(manifest["launcher"], kind="launcher")
    _, final_appimage_size, final_appimage_digest = _verify_candidate_file(manifest["appimage"], kind="artifact")
    if (final_launcher_size, final_launcher_digest) != (launcher_size, launcher_digest):
        _fail("ERR_LAUNCHER_DIGEST_MISMATCH", "Launcher identity changed during qualification")
    if (final_appimage_size, final_appimage_digest) != (appimage_size, appimage_digest):
        _fail("ERR_ARTIFACT_DIGEST_MISMATCH", "AppImage identity changed during qualification")

    manifest_display = (
        CANONICAL_MANIFEST_RELATIVE
        if Path(manifest_path).resolve() == CANONICAL_MANIFEST.resolve()
        else str(Path(manifest_path))
    )
    return {
        "status": "PASS",
        "manifest_identity": {
            "candidate_id": manifest["candidate_id"],
            "qualification_policy": manifest["qualification_policy"],
            "manifest_path": manifest_display,
            "manifest_sha256": manifest_digest,
        },
        "binding_review": {
            "method": manifest["binding_review"]["method"],
            "launcher_sha256": launcher_digest,
            "expected_appimage_path": manifest["binding_review"]["expected_appimage_path"],
            "accepted_by_manifest": True,
        },
        "launcher_identity": {
            "launcher_path": str(launcher),
            "launcher_type": "Bash wrapper",
            "launcher_size_bytes": launcher_size,
            "launcher_sha256": launcher_digest,
        },
        "bound_appimage_identity": {
            "appimage_path": str(appimage),
            "appimage_size_bytes": appimage_size,
            "appimage_sha256": appimage_digest,
            "statically_bound": True,
            "manifest_bound": True,
        },
        "product_version_identity": {
            "product_version": manifest["product_version"]["value"],
            "metadata_source": manifest["product_version"]["source"],
        },
        "catalog_identity": {
            "schema_version": manifest["catalog"]["schema_version"],
            "declared_command_count": manifest["catalog"]["declared_command_count"],
            "actual_command_count": manifest["catalog"]["actual_command_count"],
            "catalog_bytes": catalog_bytes,
            "catalog_sha256": catalog_digest,
            "determinism_verified": True,
        },
        "bounded_cleanup": {
            "timeout_ms": isolation["cleanup_timeout_ms"],
            "poll_interval_ms": isolation["cleanup_poll_interval_ms"],
            "transient_fuse_condition": isolation["transient_fuse_condition"],
            "final_inventory_exceptions": 0,
            "verified": True,
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
    parser = argparse.ArgumentParser(description="Qualify the canonical Orca candidate without lifecycle effects.")
    parser.add_argument("--isolated-root", required=True, help="Fresh direct /tmp child with the canonical prefix")
    args = parser.parse_args()
    try:
        result = qualify_orca(isolated_root=args.isolated_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0)
    except QualificationError as exc:
        print(json.dumps({"status": "FAIL", "code": exc.code, "error": exc.message}, indent=2, sort_keys=True))
        raise SystemExit(1) from None
    except Exception:
        print(
            json.dumps(
                {"status": "FAIL", "code": "ERR_UNEXPECTED_EXCEPTION", "error": "An unexpected error occurred"},
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
