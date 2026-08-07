"""Deterministic qualification tests for Orca launcher, AppImage, version, catalog, and isolation."""

from __future__ import annotations

import os
import shutil
import signal
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
    iso_root2 = make_temp_isolated_root()
    try:
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
        res2 = qualify_orca(
            launcher_path=REAL_LAUNCHER,
            artifact_path=REAL_ARTIFACT,
            isolated_root=iso_root2,
            expected_launcher_sha256=REAL_LAUNCHER_SHA256,
            expected_artifact_sha256=REAL_ARTIFACT_SHA256,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
        assert res1 == res2
        assert res1["status"] == "PASS"
        assert res1["product_version_identity"]["product_version"] == REAL_VERSION
        assert res1["catalog_identity"]["schema_version"] == 1
        assert res1["catalog_identity"]["actual_command_count"] == 220
        assert res1["catalog_identity"]["determinism_verified"] is True
    finally:
        if iso_root2.exists():
            shutil.rmtree(iso_root2, ignore_errors=True)


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


def test_missing_appimage_version(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'Name=Orca' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_no_ver"
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
    assert exc_info.value.code == "ERR_APPIMAGE_VERSION_MISSING"


def test_duplicate_appimage_version(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167\nX-AppImage-Version=1.4.168' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_dup_ver"
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
    assert exc_info.value.code == "ERR_APPIMAGE_VERSION_DUPLICATE"


def test_mismatched_appimage_version(iso_root: Path) -> None:
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


def test_catalog_stderr_zero_exit(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    payload = '{"schemaVersion": 1, "commandCount": 1, "commands": [{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}]}'
    fake_launcher = tmp_path / "orca_err_zero"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  echo 'Warning output' >&2\n  printf '%s' '{payload}'\n  exit 0\nfi\n")
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
    assert exc_info.value.code == "ERR_CATALOG_STDERR"


def test_catalog_nonzero_exit(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_nonzero"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  exit 1\nfi\n")
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
    assert exc_info.value.code == "ERR_CATALOG_NONZERO_EXIT"


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


def test_declared_command_count_mismatch(iso_root: Path) -> None:
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


def test_actual_command_list_length_mismatch(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    json_payload = '{"schemaVersion": 1, "commandCount": 2, "commands": [{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}]}'
    fake_launcher = tmp_path / "orca_len_mismatch"
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


def test_child_environment_does_not_receive_forbidden_ambient_variables(iso_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    canary_sec = "CANARY_SECRET_12345"
    monkeypatch.setenv("SECRET_CANARY_TOKEN", canary_sec)
    monkeypatch.setenv("NODE_OPTIONS", "--max-old-space-size=4096")
    monkeypatch.setenv("PYTHONPATH", "/forbidden/path")

    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    # Launcher script that fails if ambient env vars leak into child env
    check_script = f"""#!/bin/sh
APPIMAGE='{fake_art}'
if [ "$1" = "agent-context" ]; then
  if [ -n "$SECRET_CANARY_TOKEN" ] || [ -n "$NODE_OPTIONS" ] || [ -n "$PYTHONPATH" ]; then
    echo "Leaked environment variable detected" >&2
    exit 1
  fi
  printf '%s' '{{"schemaVersion": 1, "commandCount": 1, "commands": [{{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}}]}}'
  exit 0
fi
"""
    fake_launcher = tmp_path / "orca_env_check"
    fake_launcher.write_text(check_script)
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    res = qualify_orca(
        launcher_path=fake_launcher,
        artifact_path=fake_art,
        isolated_root=iso_root,
        expected_launcher_sha256=launch_sha,
        expected_artifact_sha256=art_sha,
        expected_product_version=REAL_VERSION,
        expected_schema_version=1,
        expected_command_count=1,
    )
    assert res["isolation_and_effects"]["ambient_environment_forwarded"] is False


# --- REPRODUCER TESTS FOR CORRECTIONS C1 to C5 ---

def test_c1_comment_only_launcher_binding_rejected(iso_root: Path, tmp_path: Path) -> None:
    real_art = tmp_path / "real-linux.AppImage"
    real_art.write_bytes(REAL_ARTIFACT.read_bytes())
    real_art.chmod(0o755)
    real_sha = subprocess.check_output(["sha256sum", str(real_art)]).decode().split()[0]

    fake_art = tmp_path / "other-linux.AppImage"
    fake_art.write_bytes(b"other content")
    fake_art.chmod(0o755)

    # Launcher has comment with real_art, but active APPIMAGE points to fake_art
    script = f"""#!/bin/bash
# APPIMAGE='{real_art}'
APPIMAGE='{fake_art}'
"""
    fake_launcher = tmp_path / "orca_comment_only"
    fake_launcher.write_text(script)
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=fake_launcher,
            artifact_path=real_art,
            isolated_root=iso_root,
            expected_launcher_sha256=launch_sha,
            expected_artifact_sha256=real_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_NOT_BOUND"


def test_c1_duplicate_or_dynamic_appimage_assignment_rejected(iso_root: Path, tmp_path: Path) -> None:
    real_art = tmp_path / "real-linux.AppImage"
    real_art.write_bytes(REAL_ARTIFACT.read_bytes())
    real_art.chmod(0o755)
    real_sha = subprocess.check_output(["sha256sum", str(real_art)]).decode().split()[0]

    # Dynamic assignment
    script_dynamic = f"#!/bin/bash\nAPPIMAGE=\"$MY_PATH/{real_art.name}\"\n"
    launcher_dyn = tmp_path / "orca_dyn"
    launcher_dyn.write_text(script_dynamic)
    launcher_dyn.chmod(0o755)
    dyn_sha = subprocess.check_output(["sha256sum", str(launcher_dyn)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=launcher_dyn,
            artifact_path=real_art,
            isolated_root=iso_root,
            expected_launcher_sha256=dyn_sha,
            expected_artifact_sha256=real_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_NOT_BOUND"

    # Duplicate assignment
    script_dup = f"#!/bin/bash\nAPPIMAGE='{real_art}'\nAPPIMAGE='{real_art}'\n"
    launcher_dup = tmp_path / "orca_dup_assign"
    launcher_dup.write_text(script_dup)
    launcher_dup.chmod(0o755)
    dup_sha = subprocess.check_output(["sha256sum", str(launcher_dup)]).decode().split()[0]

    with pytest.raises(QualificationError) as exc_info:
        qualify_orca(
            launcher_path=launcher_dup,
            artifact_path=real_art,
            isolated_root=iso_root,
            expected_launcher_sha256=dup_sha,
            expected_artifact_sha256=real_sha,
            expected_product_version=REAL_VERSION,
            expected_schema_version=REAL_SCHEMA_VERSION,
            expected_command_count=REAL_COMMAND_COUNT,
        )
    assert exc_info.value.code == "ERR_LAUNCHER_NOT_BOUND"


def test_c2_nested_side_effect_file_rejected(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    payload = '{"schemaVersion": 1, "commandCount": 1, "commands": [{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}]}'
    fake_launcher = tmp_path / "orca_nested_file"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  mkdir -p \"$HOME/nested_dir\"\n  touch \"$HOME/nested_dir/leaked.txt\"\n  printf '%s' '{payload}'\n  exit 0\nfi\n")
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


def test_c2_symlink_in_isolated_root_rejected(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  ln -s /etc/passwd squashfs-root/symlink_file\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    payload = '{"schemaVersion": 1, "commandCount": 1, "commands": [{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}]}'
    fake_launcher = tmp_path / "orca_symlink_file"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  printf '%s' '{payload}'\n  exit 0\nfi\n")
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


def test_c2_unexpected_entry_type_in_isolated_root_rejected(iso_root: Path, tmp_path: Path) -> None:
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/extra_file.txt\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    payload = '{"schemaVersion": 1, "commandCount": 1, "commands": [{"command": "c1", "aliases": [], "argumentMode": "none", "examples": [], "flags": [], "notes": [], "path": [], "positionalArgs": [], "summary": "", "usage": ""}]}'
    fake_launcher = tmp_path / "orca_extra_file"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  printf '%s' '{payload}'\n  exit 0\nfi\n")
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


def test_c3_canary_not_leaked_in_stderr_failure(iso_root: Path, tmp_path: Path) -> None:
    canary = "SUPER_SECRET_CANARY_IN_STDERR_9999"
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_canary_err"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  echo '{canary}' >&2\n  exit 1\nfi\n")
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
    assert canary not in exc_info.value.message
    assert canary not in str(exc_info.value)


def test_c3_canary_not_leaked_in_malformed_json(iso_root: Path, tmp_path: Path) -> None:
    canary = "SUPER_SECRET_CANARY_IN_JSON_8888"
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_canary_json"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  echo '{{ {canary}: bad_json }}'\n  exit 0\nfi\n")
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
    assert canary not in exc_info.value.message
    assert canary not in str(exc_info.value)


def test_c3_canary_not_leaked_in_malformed_command(iso_root: Path, tmp_path: Path) -> None:
    canary = "SUPER_SECRET_CANARY_IN_CMD_7777"
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    payload = f'{{"schemaVersion": 1, "commandCount": 1, "commands": [{{"command": "{canary}"}}]}}'
    fake_launcher = tmp_path / "orca_canary_cmd"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  printf '%s' '{payload}'\n  exit 0\nfi\n")
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
    assert canary not in exc_info.value.message
    assert canary not in str(exc_info.value)


def test_c3_canary_not_leaked_in_unexpected_version(iso_root: Path, tmp_path: Path) -> None:
    canary = "SUPER_SECRET_CANARY_IN_VERSION_6666"
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text(f"#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version={canary}' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_canary_ver"
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
    assert canary not in exc_info.value.message
    assert canary not in str(exc_info.value)


def test_c3_canary_not_leaked_in_cli_execution(iso_root: Path, tmp_path: Path) -> None:
    canary = "SUPER_SECRET_CANARY_IN_CLI_5555"
    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    fake_launcher = tmp_path / "orca_cli_canary"
    fake_launcher.write_text(f"#!/bin/sh\nAPPIMAGE='{fake_art}'\nif [ \"$1\" = \"agent-context\" ]; then\n  echo '{canary}' >&2\n  exit 1\nfi\n")
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "aether_mcp" / "qualify_orca.py"),
        "--launcher", str(fake_launcher),
        "--artifact", str(fake_art),
        "--isolated-root", str(iso_root),
        "--expected-launcher-sha256", launch_sha,
        "--expected-artifact-sha256", art_sha,
        "--expected-product-version", REAL_VERSION,
        "--expected-catalog-schema-version", "1",
        "--expected-command-count", "1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode != 0
    assert proc.stderr == ""
    assert canary not in proc.stdout


def test_c4_root_outside_tmp_rejected(tmp_path: Path) -> None:
    # Directory outside /tmp with valid prefix
    out_root = tmp_path / "aether-m1-1-out-dir"
    out_root.mkdir()
    try:
        with pytest.raises(QualificationError) as exc_info:
            qualify_orca(
                launcher_path=REAL_LAUNCHER,
                artifact_path=REAL_ARTIFACT,
                isolated_root=out_root,
                expected_launcher_sha256=REAL_LAUNCHER_SHA256,
                expected_artifact_sha256=REAL_ARTIFACT_SHA256,
                expected_product_version=REAL_VERSION,
                expected_schema_version=REAL_SCHEMA_VERSION,
                expected_command_count=REAL_COMMAND_COUNT,
            )
        assert exc_info.value.code == "ERR_ISOLATED_ROOT_INVALID"
    finally:
        shutil.rmtree(out_root, ignore_errors=True)


def test_c4_ambient_xdg_root_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    xdg_cfg = Path("/tmp") / f"aether-m1-1-xdg-{os.urandom(4).hex()}"
    xdg_cfg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_cfg))

    try:
        with pytest.raises(QualificationError) as exc_info:
            qualify_orca(
                launcher_path=REAL_LAUNCHER,
                artifact_path=REAL_ARTIFACT,
                isolated_root=xdg_cfg,
                expected_launcher_sha256=REAL_LAUNCHER_SHA256,
                expected_artifact_sha256=REAL_ARTIFACT_SHA256,
                expected_product_version=REAL_VERSION,
                expected_schema_version=REAL_SCHEMA_VERSION,
                expected_command_count=REAL_COMMAND_COUNT,
            )
        assert exc_info.value.code in ("ERR_ISOLATED_ROOT_GLOBAL", "ERR_ISOLATED_ROOT_INVALID")
    finally:
        shutil.rmtree(xdg_cfg, ignore_errors=True)


def test_c4_symlink_path_component_in_root_rejected() -> None:
    base_target = Path("/tmp") / f"aether-m1-1-real-{os.urandom(4).hex()}"
    base_target.mkdir()
    link_path = Path("/tmp") / f"aether-m1-1-symlink-{os.urandom(4).hex()}"
    os.symlink(base_target, link_path)

    try:
        with pytest.raises(QualificationError) as exc_info:
            qualify_orca(
                launcher_path=REAL_LAUNCHER,
                artifact_path=REAL_ARTIFACT,
                isolated_root=link_path,
                expected_launcher_sha256=REAL_LAUNCHER_SHA256,
                expected_artifact_sha256=REAL_ARTIFACT_SHA256,
                expected_product_version=REAL_VERSION,
                expected_schema_version=REAL_SCHEMA_VERSION,
                expected_command_count=REAL_COMMAND_COUNT,
            )
        assert exc_info.value.code == "ERR_ISOLATED_ROOT_SYMLINK"
    finally:
        if link_path.is_symlink():
            link_path.unlink()
        shutil.rmtree(base_target, ignore_errors=True)


def test_c5_timeout_descendant_process_terminated_and_reaped(iso_root: Path, tmp_path: Path) -> None:
    pid_file = tmp_path / "child_pid.txt"

    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    # Launcher spawns a background descendant sleep process and waits
    script = f"""#!/bin/sh
APPIMAGE='{fake_art}'
if [ "$1" = "agent-context" ]; then
  sleep 30 &
  echo $! > '{pid_file}'
  wait
  exit 0
fi
"""
    fake_launcher = tmp_path / "orca_sleep_child"
    fake_launcher.write_text(script)
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    child_pid = None
    try:
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
                timeout_seconds=1,
            )
        assert exc_info.value.code == "ERR_CATALOG_TIMEOUT"

        if pid_file.exists():
            child_pid = int(pid_file.read_text().strip())
            # Verify child pid no longer exists
            with pytest.raises(OSError):
                os.kill(child_pid, 0)
    finally:
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except OSError:
                pass


def test_c5_process_group_cleanup_on_nonzero_exit(iso_root: Path, tmp_path: Path) -> None:
    pid_file = tmp_path / "child_pid_err.txt"

    fake_art = tmp_path / "art.AppImage"
    fake_art.write_text("#!/bin/sh\nif [ \"$1\" = \"--appimage-extract\" ]; then\n  mkdir -p squashfs-root\n  echo 'X-AppImage-Version=1.4.167' > squashfs-root/orca-ide.desktop\n  exit 0\nfi\n")
    fake_art.chmod(0o755)
    art_sha = subprocess.check_output(["sha256sum", str(fake_art)]).decode().split()[0]

    script = f"""#!/bin/sh
APPIMAGE='{fake_art}'
if [ "$1" = "agent-context" ]; then
  sleep 30 >/dev/null 2>&1 &
  echo $! > '{pid_file}'
  exit 1
fi
"""
    fake_launcher = tmp_path / "orca_child_err"
    fake_launcher.write_text(script)
    fake_launcher.chmod(0o755)
    launch_sha = subprocess.check_output(["sha256sum", str(fake_launcher)]).decode().split()[0]

    child_pid = None
    try:
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
        assert exc_info.value.code == "ERR_CATALOG_NONZERO_EXIT"

        if pid_file.exists():
            child_pid = int(pid_file.read_text().strip())
            with pytest.raises(OSError):
                os.kill(child_pid, 0)
    finally:
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except OSError:
                pass
