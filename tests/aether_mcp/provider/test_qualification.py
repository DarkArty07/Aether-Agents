"""Deterministic qualification tests for Orca launcher, AppImage, version, catalog, and isolation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from aether_mcp.qualify_orca import QualificationError, qualify_orca  # noqa: E402

REAL_LAUNCHER = Path("/home/darkarty/.local/bin/orca")
REAL_ARTIFACT = Path("/home/darkarty/.local/opt/orca/orca-linux.AppImage")
REAL_LAUNCHER_SHA256 = "89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208"
REAL_ARTIFACT_SHA256 = "813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33"
REAL_VERSION = "1.4.167"
REAL_SCHEMA_VERSION = 1
REAL_COMMAND_COUNT = 220


def make_temp_isolated_root() -> Path:
    base = Path("/tmp") / f"aether-m1-1-test-{os.urandom(4).hex()}"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def iso_root() -> Path:
    root = make_temp_isolated_root()
    yield root
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def test_qualification_pass_deterministic(iso_root: Path) -> None:
    res1 = qualify_orca(
        launcher_path=REAL_LAUNCHER,
        artifact_path=REAL_ARTIFACT,
        isolated_root=iso_root,
        expected_launcher_sha256=REAL_LAUNCHER_SHA256,
        expected_artifact_sha256=REAL_ARTIFACT_SHA256,
        expected_product_version=REAL_VERSION,
        expected_schema_version=REAL_SCHEMA_VERSION,
        expected_command_count=REAL_COMMAND_COUNT,
    )
    assert res1["status"] == "PASS"
    assert res1["product_version_identity"]["product_version"] == REAL_VERSION
    assert res1["catalog_identity"]["schema_version"] == 1
    assert res1["catalog_identity"]["actual_command_count"] == 220
    assert res1["catalog_identity"]["determinism_verified"] is True


def test_absent_launcher(iso_root: Path) -> None:
    fake_launcher = iso_root / "nonexistent_launcher"
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_MISSING"


def test_launcher_symlink(iso_root: Path) -> None:
    link = iso_root / "launcher_link"
    os.symlink(REAL_LAUNCHER, link)
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=link,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_IS_SYMLINK"


def test_launcher_digest_mismatch(iso_root: Path) -> None:
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256="0" * 64,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_DIGEST_MISMATCH"


def test_launcher_bound_to_different_artifact(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "other-linux.AppImage"
    fake_art.write_bytes(REAL_ARTIFACT.read_bytes())
    fake_art.chmod(0o755)

    # Launcher that points to REAL_ARTIFACT, but we pass fake_art as artifact_path
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_NOT_BOUND"


def test_absent_or_non_executable_artifact(iso_root: Path, tmp_path: Path) -> None:
    missing_art = iso_root / "missing.AppImage"
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=missing_art,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_ARTIFACT_MISSING"

    non_exec_art = tmp_path / "non_exec.AppImage"
    non_exec_art.write_bytes(b"content")
    non_exec_art.chmod(0o644)
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=non_exec_art,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256="d0e452314c80861dd7b1a2ee6f8373b98471e49c7f66a2f2dd90f23023249767",
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_ARTIFACT_NOT_EXECUTABLE"


def test_artifact_digest_mismatch(iso_root: Path) -> None:
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256="1" * 64,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_ARTIFACT_DIGEST_MISMATCH"


def test_absent_duplicate_or_mismatched_appimage_version(iso_root: Path, tmp_path: Path) -> None:
    # Mismatched version expectation
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version="9.9.9",
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_APPIMAGE_VERSION_MISMATCH"


def test_nonzero_metadata_extraction(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "bad_extract.AppImage"
    fake_art.write_text("#!/bin/sh\nexit 1\n")
    fake_art.chmod(0o755)

    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]
    fake_launcher = tmp_path / "fake_orca"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_METADATA_EXTRACTION_FAILED"


def test_ambient_repository_or_symlinked_isolated_root(tmp_path: Path) -> None:
    # Symlinked isolated root
    link_root = tmp_path / "link_iso"
    real_target = make_temp_isolated_root()
    os.symlink(real_target, link_root)

    try:
        with pytest.raises(QualificationError) as exc_info:
            qualify_orca(
                launcher_path=REAL_LAUNCHER,
                artifact_path=REAL_ARTIFACT,
                isolated_root=link_root,
                expected_launcher_sha256=REAL_LAUNCHER_SHA256,
                expected_artifact_sha256=REAL_ARTIFACT_SHA256,
                expected_product_version=REAL_VERSION,
                expected_schema_version=REAL_SCHEMA_VERSION,
                expected_command_count=REAL_COMMAND_COUNT,
            )
        assert exc_info.value.code == "ERR_ISOLATED_ROOT_SYMLINK"
    finally:
        shutil.rmtree(real_target, ignore_errors=True)

    # Repository isolated root
    repo_iso = ROOT / "tests" / "fake_iso"
    repo_iso.mkdir(exist_ok=True)
    try:
        with pytest.raises(QualificationError) as exc_info:
            qualify_orca(
                launcher_path=REAL_LAUNCHER,
                artifact_path=REAL_ARTIFACT,
                isolated_root=repo_iso,
                expected_launcher_sha256=REAL_LAUNCHER_SHA256,
                expected_artifact_sha256=REAL_ARTIFACT_SHA256,
                expected_product_version=REAL_VERSION,
                expected_schema_version=REAL_SCHEMA_VERSION,
                expected_command_count=REAL_COMMAND_COUNT,
            )
        assert exc_info.value.code == "ERR_ISOLATED_ROOT_INSIDE_REPO"
    finally:
        shutil.rmtree(repo_iso, ignore_errors=True)


def test_child_environment_does_not_receive_forbidden_ambient_variables(iso_root: Path) -> None:
    # Set canary forbidden env vars in process
    os.environ["SECRET_CANARY_TOKEN"] = "CANARY_SECRET_12345"
    os.environ["NODE_OPTIONS"] = "--max-old-space-size=4096"
    os.environ["PYTHONPATH"] = "/forbidden/path"

    res = qualify_orca(
        launcher_path=REAL_LAUNCHER,
        artifact_path=REAL_ARTIFACT,
        isolated_root=iso_root,
        expected_launcher_sha256=REAL_LAUNCHER_SHA256,
        expected_artifact_sha256=REAL_ARTIFACT_SHA256,
        expected_product_version=REAL_VERSION,
        expected_schema_version=REAL_SCHEMA_VERSION,
        expected_command_count=REAL_COMMAND_COUNT,
    )
    assert res["isolation_and_effects"]["ambient_environment_forwarded"] is False


def test_malformed_json_and_human_prose(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_prose"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  echo 'This is human prose help text, not JSON'\n  exit 0\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_CATALOG_MALFORMED_JSON"


def test_catalog_stderr_or_nonzero_exit(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_err"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  echo 'Error output' >&2\n  exit 1\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code in ("ERR_CATALOG_STDERR", "ERR_CATALOG_NONZERO_EXIT")


def test_catalog_timeout(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_sleep"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  sleep 15\n  exit 0\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
            timeout_seconds=1,
        )
    assert exc_info.value.code == "ERR_CATALOG_TIMEOUT"


def test_schema_version_mismatch(iso_root: Path) -> None:
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=999,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_SCHEMA_VERSION_MISMATCH"


def test_command_count_mismatch(iso_root: Path) -> None:
    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=50,
        )
    assert exc_info.value.code == "ERR_COMMAND_COUNT_MISMATCH"


def test_duplicate_command_names(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    json_payload = (
        '{"schemaVersion": 1, "commandCount": 2, "commands": ['
        '{"command": "dup", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""},'
        '{"command": "dup", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}'
        ']}'
    )
    fake_launcher = tmp_path / "orca_dup"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  printf '%s' '{json_payload}'\n  exit 0\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=1,
            expected_command_count=2,
        )
    assert exc_info.value.code == "ERR_DUPLICATE_COMMAND_NAME"


def test_missing_required_command_fields(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    json_payload = '{"schemaVersion": 1, "commandCount": 1, "commands": [{"command": "cmd1"}]}'
    fake_launcher = tmp_path / "orca_missing_fields"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  printf '%s' '{json_payload}'\n  exit 0\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=1,
            expected_command_count=1,
        )
    assert exc_info.value.code == "ERR_COMMAND_SHAPE_INVALID"


def test_differing_catalog_bytes(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    # Stateful launcher that returns different output on second call
    counter_file = tmp_path / "call_count"
    counter_file.write_text("0")
    script = f"""#!/bin/sh
APPIMAGE='{fake_art}'
if [ "$1" = "agent-context" ]; then
  c=$(cat '{counter_file}')
  c=$((c + 1))
  echo "$c" > '{counter_file}'
  if [ "$c" -eq 1 ]; then
    printf '%s' '{{"schemaVersion": 1, "commandCount": 1, "commands": [{{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}}]}}'
  else
    printf '%s' '{{"schemaVersion": 1, "commandCount": 1, "commands": [{{"command": "c2", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}}]}}'
  fi
  exit 0
fi
"""
    fake_launcher = tmp_path / "orca_diff"
    fake_launcher.write_text(script)
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=1,
            expected_command_count=1,
        )
    assert exc_info.value.code == "ERR_CATALOG_NON_DETERMINISTIC"


def test_secret_canary_never_appears(iso_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    canary = "SUPER_SECRET_CANARY_VALUE_999"
    os.environ["SECRET_CANARY"] = canary

    res = qualify_orca(
        launcher_path=REAL_LAUNCHER,
        artifact_path=REAL_ARTIFACT,
        isolated_root=iso_root,
        expected_launcher_sha256=REAL_LAUNCHER_SHA256,
        expected_artifact_sha256=REAL_ARTIFACT_SHA256,
        expected_product_version=REAL_VERSION,
        expected_schema_version=REAL_SCHEMA_VERSION,
        expected_command_count=REAL_COMMAND_COUNT,
    )
    captured = capsys.readouterr()
    assert canary not in str(res)
    assert canary not in captured.out
    assert canary not in captured.err


def test_no_files_outside_allowlist(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  touch dirty_file_in_root\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    json_payload = '{"schemaVersion": 1, "commandCount": 1, "commands": [{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}]}'
    fake_launcher = tmp_path / "orca_dirty"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  printf '%s' '{json_payload}'\n  exit 0\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=fake_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=art_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=1,
            expected_command_count=1,
        )
    assert exc_info.value.code == "ERR_UNEXPECTED_FILES_CREATED"


def test_no_surviving_child_process(iso_root: Path) -> None:
    res = qualify_orca(
        launcher_path=REAL_LAUNCHER,
        artifact_path=REAL_ARTIFACT,
        isolated_root=iso_root,
        expected_launcher_sha256=REAL_LAUNCHER_SHA256,
        expected_artifact_sha256=REAL_ARTIFACT_SHA256,
        expected_product_version=REAL_VERSION,
        expected_schema_version=REAL_SCHEMA_VERSION,
        expected_command_count=REAL_COMMAND_COUNT,
    )
    assert res["isolation_and_effects"]["surviving_processes_detected"] is False
