"""M1.1b contract tests for the canonical exact-byte Orca qualifier."""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
QUALIFIER_DIR = ROOT / "scripts" / "aether_mcp"
if str(QUALIFIER_DIR) not in sys.path:
    sys.path.insert(0, str(QUALIFIER_DIR))

import qualify_orca as qualifier  # type: ignore[import-not-found]  # noqa: E402

QualificationError = qualifier.QualificationError
CANONICAL_MANIFEST = ROOT / "docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json"
REAL_LAUNCHER = Path("/home/darkarty/.local/bin/orca")
REAL_ARTIFACT = Path("/home/darkarty/.local/opt/orca/orca-linux.AppImage")
REAL_FIXTURE_AVAILABLE = (
    REAL_LAUNCHER.is_file()
    and os.access(REAL_LAUNCHER, os.X_OK)
    and REAL_ARTIFACT.is_file()
    and os.access(REAL_ARTIFACT, os.X_OK)
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _catalog_payload(command_count: int = 1) -> bytes:
    commands = [
        {
            "aliases": [],
            "argumentMode": "none",
            "command": f"command-{index}",
            "examples": [],
            "flags": [],
            "notes": [],
            "path": [],
            "positionalArgs": [],
            "summary": "synthetic",
            "usage": "synthetic",
        }
        for index in range(command_count)
    ]
    return json.dumps(
        {"schemaVersion": 1, "commandCount": command_count, "commands": commands},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _write_manifest(path: Path, manifest: dict[str, Any]) -> str:
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    return _sha(payload)


def _make_candidate(
    tmp_path: Path,
    *,
    catalog_payload: bytes | None = None,
    launcher_extra: str = "",
    artifact_extra: str = "",
    version: str = "1.4.167",
) -> tuple[Path, str, Path, Path, dict[str, Any]]:
    payload = catalog_payload if catalog_payload is not None else _catalog_payload()
    artifact = tmp_path / "synthetic.AppImage"
    launcher = tmp_path / "orca-synthetic"
    _write_executable(
        artifact,
        "#!/usr/bin/python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1:] == ['--appimage-extract', 'orca-ide.desktop']:\n"
        "    root = Path('squashfs-root')\n"
        "    root.mkdir(parents=True, exist_ok=True)\n"
        f"    (root / 'orca-ide.desktop').write_text('X-AppImage-Version={version}\\n')\n"
        + "\n".join(f"    {line}" for line in artifact_extra.splitlines())
        + "\n    raise SystemExit(0)\n"
        "raise SystemExit(2)\n",
    )
    _write_executable(
        launcher,
        "#!/usr/bin/python3\n"
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "import time\n"
        "from pathlib import Path\n"
        "if sys.argv[1:] == ['agent-context', '--json']:\n"
        + "\n".join(f"    {line}" for line in launcher_extra.splitlines())
        + ("\n" if launcher_extra else "")
        + f"    sys.stdout.buffer.write({payload!r})\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(2)\n",
    )

    template = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    manifest = copy.deepcopy(template)
    manifest["candidate_id"] = "synthetic-candidate"
    manifest["launcher"].update(
        {
            "path": str(launcher),
            "size_bytes": launcher.stat().st_size,
            "sha256": _sha(launcher.read_bytes()),
        }
    )
    manifest["appimage"].update(
        {
            "path": str(artifact),
            "size_bytes": artifact.stat().st_size,
            "sha256": _sha(artifact.read_bytes()),
        }
    )
    manifest["binding_review"].update(
        {
            "launcher_sha256": manifest["launcher"]["sha256"],
            "expected_appimage_path": str(artifact),
        }
    )
    manifest["product_version"]["value"] = "1.4.167"
    manifest["catalog"].update(
        {
            "schema_version": 1,
            "declared_command_count": 1,
            "actual_command_count": 1,
            "bytes": len(payload),
            "sha256": _sha(payload),
        }
    )
    manifest_path = tmp_path / "manifest.json"
    digest = _write_manifest(manifest_path, manifest)
    return manifest_path, digest, launcher, artifact, manifest


def _new_root() -> Path:
    root = Path("/tmp") / f"aether-m1-1b-test-{os.urandom(5).hex()}"
    root.mkdir()
    return root


@pytest.fixture
def iso_root() -> Path:
    root = _new_root()
    yield root
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def _run_fake(iso_root: Path, tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path, **kwargs)
    return qualifier.qualify_orca(
        isolated_root=iso_root,
        manifest_path=manifest_path,
        expected_manifest_sha256=digest,
    )


def _prepare_inventory(iso_root: Path, manifest: dict[str, Any]) -> None:
    for name in manifest["isolation"]["required_directories"]:
        (iso_root / name).mkdir(parents=True, exist_ok=True)
    for name in manifest["isolation"]["required_files"]:
        target = iso_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("X-AppImage-Version=1.4.167\n", encoding="utf-8")


def test_fake_candidate_qualifies_deterministically(iso_root: Path, tmp_path: Path) -> None:
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path)
    second_root = _new_root()
    try:
        first = qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
        second = qualifier.qualify_orca(
            isolated_root=second_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    finally:
        shutil.rmtree(second_root, ignore_errors=True)

    assert first == second
    assert first["status"] == "PASS"
    assert first["bounded_cleanup"]["final_inventory_exceptions"] == 0
    assert first["bounded_cleanup"]["verified"] is True


def test_production_cli_exposes_only_isolated_root() -> None:
    completed = subprocess.run(
        [sys.executable, str(QUALIFIER_DIR / "qualify_orca.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert completed.returncode == 0
    assert "--isolated-root" in completed.stdout
    for forbidden in (
        "--launcher",
        "--artifact",
        "--expected-launcher-sha256",
        "--expected-artifact-sha256",
        "--expected-product-version",
        "--expected-catalog-schema-version",
        "--expected-command-count",
        "--timeout",
    ):
        assert forbidden not in completed.stdout


def test_bash_semantics_parser_is_absent() -> None:
    assert not hasattr(qualifier, "parse_static_appimage_binding")


def test_manifest_digest_mismatch_fails_before_child(iso_root: Path, tmp_path: Path) -> None:
    manifest_path, _digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256="0" * 64,
        )
    assert captured.value.code == "ERR_MANIFEST_DIGEST_MISMATCH"
    assert not (iso_root / "squashfs-root").exists()


def test_manifest_missing_extra_and_wrong_types_fail_closed(tmp_path: Path) -> None:
    _path, _digest, _launcher, _artifact, base = _make_candidate(tmp_path)
    variants: list[dict[str, Any]] = []
    missing = copy.deepcopy(base)
    missing.pop("catalog")
    variants.append(missing)
    extra = copy.deepcopy(base)
    extra["unexpected"] = True
    variants.append(extra)
    wrong_type = copy.deepcopy(base)
    wrong_type["schema_version"] = "1"
    variants.append(wrong_type)
    relative_path = copy.deepcopy(base)
    relative_path["launcher"]["path"] = "relative/orca"
    variants.append(relative_path)
    broken_binding = copy.deepcopy(base)
    broken_binding["binding_review"]["launcher_sha256"] = "0" * 64
    variants.append(broken_binding)
    broad_exception = copy.deepcopy(base)
    broad_exception["isolation"]["final_inventory_exceptions"] = ["tmp/.mount_orca-*"]
    variants.append(broad_exception)

    for index, variant in enumerate(variants):
        path = tmp_path / f"invalid-{index}.json"
        digest = _write_manifest(path, variant)
        with pytest.raises(QualificationError) as captured:
            qualifier.load_manifest(path, digest)
        assert captured.value.code == "ERR_MANIFEST_INVALID"


@pytest.mark.parametrize(
    ("target", "expected"),
    (("launcher", "ERR_LAUNCHER_SIZE_MISMATCH"), ("artifact", "ERR_ARTIFACT_SIZE_MISMATCH")),
)
def test_one_byte_candidate_drift_fails_before_execution(
    iso_root: Path,
    tmp_path: Path,
    target: str,
    expected: str,
) -> None:
    manifest_path, digest, launcher, artifact, _manifest = _make_candidate(tmp_path)
    path = launcher if target == "launcher" else artifact
    path.write_bytes(path.read_bytes() + b"x")
    path.chmod(0o755)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == expected
    assert not (iso_root / "squashfs-root").exists()


def test_symlink_and_non_executable_candidate_rejected(iso_root: Path, tmp_path: Path) -> None:
    manifest_path, digest, launcher, artifact, manifest = _make_candidate(tmp_path)
    launcher.unlink()
    launcher.symlink_to(artifact)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_LAUNCHER_IS_SYMLINK"

    launcher.unlink()
    _write_executable(launcher, "#!/bin/sh\nexit 0\n")
    manifest["launcher"]["size_bytes"] = launcher.stat().st_size
    manifest["launcher"]["sha256"] = _sha(launcher.read_bytes())
    manifest["binding_review"]["launcher_sha256"] = manifest["launcher"]["sha256"]
    launcher.chmod(0o644)
    digest = _write_manifest(manifest_path, manifest)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_LAUNCHER_NOT_EXECUTABLE"


def test_isolated_root_prefix_and_symlink_fail_closed(tmp_path: Path) -> None:
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path)
    wrong = Path("/tmp") / f"wrong-prefix-{os.urandom(3).hex()}"
    wrong.mkdir()
    target = Path("/tmp") / f"aether-m1-1b-target-{os.urandom(3).hex()}"
    target.mkdir()
    link = Path("/tmp") / f"aether-m1-1b-link-{os.urandom(3).hex()}"
    link.symlink_to(target, target_is_directory=True)
    try:
        with pytest.raises(QualificationError) as captured:
            qualifier.qualify_orca(
                isolated_root=wrong,
                manifest_path=manifest_path,
                expected_manifest_sha256=digest,
            )
        assert captured.value.code == "ERR_ISOLATED_ROOT_INVALID"
        with pytest.raises(QualificationError) as captured:
            qualifier.qualify_orca(
                isolated_root=link,
                manifest_path=manifest_path,
                expected_manifest_sha256=digest,
            )
        assert captured.value.code == "ERR_ISOLATED_ROOT_SYMLINK"
    finally:
        shutil.rmtree(wrong, ignore_errors=True)
        shutil.rmtree(target, ignore_errors=True)
        link.unlink(missing_ok=True)


def test_real_fifo_executes_and_is_rejected(iso_root: Path, tmp_path: Path) -> None:
    _path, _digest, _launcher, _artifact, manifest = _make_candidate(tmp_path)
    _prepare_inventory(iso_root, manifest)
    fifo = iso_root / "home" / "required-fifo-test"
    os.mkfifo(fifo)
    assert fifo.is_fifo()
    try:
        with pytest.raises(QualificationError) as captured:
            qualifier.check_isolated_root_inventory(iso_root, manifest["isolation"])
        assert captured.value.code == "ERR_UNEXPECTED_FILES_CREATED"
    finally:
        fifo.unlink(missing_ok=True)


@pytest.mark.parametrize("kind", ("nested", "extra", "symlink", "missing"))
def test_exact_inventory_rejects_every_unadmitted_shape(
    iso_root: Path,
    tmp_path: Path,
    kind: str,
) -> None:
    _path, _digest, _launcher, _artifact, manifest = _make_candidate(tmp_path)
    _prepare_inventory(iso_root, manifest)
    if kind == "nested":
        path = iso_root / "home" / "nested"
        path.mkdir()
        (path / "file").write_text("x")
    elif kind == "extra":
        (iso_root / "extra").write_text("x")
    elif kind == "symlink":
        (iso_root / "home" / "link").symlink_to("/etc/passwd")
    else:
        shutil.rmtree(iso_root / "cache")
    with pytest.raises(QualificationError) as captured:
        qualifier.check_isolated_root_inventory(iso_root, manifest["isolation"])
    assert captured.value.code == "ERR_UNEXPECTED_FILES_CREATED"


def test_readable_mount_prefix_directory_rejected(iso_root: Path, tmp_path: Path) -> None:
    _path, _digest, _launcher, _artifact, manifest = _make_candidate(tmp_path)
    _prepare_inventory(iso_root, manifest)
    hidden = iso_root / "tmp" / ".mount_orca-hidden"
    hidden.mkdir()
    (hidden / "secret").write_text("synthetic")
    with pytest.raises(QualificationError) as captured:
        qualifier.wait_for_transient_fuse_cleanup(iso_root, manifest["isolation"])
    assert captured.value.code == "ERR_UNEXPECTED_FILES_CREATED"


def test_positive_enotconn_transient_disappears_and_passes(
    iso_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _path, _digest, _launcher, _artifact, manifest = _make_candidate(tmp_path)
    _prepare_inventory(iso_root, manifest)
    transient = iso_root / "tmp" / ".mount_orca-A1b2"
    transient.mkdir()
    real_scandir = os.scandir
    real_sleep = qualifier.time.sleep

    def fake_scandir(path: str | os.PathLike[str]) -> Any:
        if Path(path) == transient:
            raise OSError(errno.ENOTCONN, "synthetic disconnected endpoint")
        return real_scandir(path)

    def remove_then_sleep(seconds: float) -> None:
        transient.rmdir()
        monkeypatch.setattr(qualifier.os, "scandir", real_scandir)
        real_sleep(min(seconds, 0.001))

    monkeypatch.setattr(qualifier.os, "scandir", fake_scandir)
    monkeypatch.setattr(qualifier.time, "sleep", remove_then_sleep)
    qualifier.wait_for_transient_fuse_cleanup(iso_root, manifest["isolation"])
    qualifier.check_isolated_root_inventory(iso_root, manifest["isolation"])
    assert not transient.exists()


def test_enotconn_transient_timeout_rejected(
    iso_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _path, _digest, _launcher, _artifact, manifest = _make_candidate(tmp_path)
    _prepare_inventory(iso_root, manifest)
    transient = iso_root / "tmp" / ".mount_orca-timeout"
    transient.mkdir()
    real_scandir = os.scandir

    def fake_scandir(path: str | os.PathLike[str]) -> Any:
        if Path(path) == transient:
            raise OSError(errno.ENOTCONN, "synthetic disconnected endpoint")
        return real_scandir(path)

    manifest["isolation"]["cleanup_timeout_ms"] = 1
    manifest["isolation"]["cleanup_poll_interval_ms"] = 1
    monkeypatch.setattr(qualifier.os, "scandir", fake_scandir)
    monkeypatch.setattr(qualifier.time, "sleep", lambda _seconds: None)
    with pytest.raises(QualificationError) as captured:
        qualifier.wait_for_transient_fuse_cleanup(iso_root, manifest["isolation"])
    assert captured.value.code == "ERR_TRANSIENT_CLEANUP_TIMEOUT"


def test_wrong_errno_transient_rejected(
    iso_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _path, _digest, _launcher, _artifact, manifest = _make_candidate(tmp_path)
    _prepare_inventory(iso_root, manifest)
    transient = iso_root / "tmp" / ".mount_orca-wrong"
    transient.mkdir()
    real_scandir = os.scandir

    def fake_scandir(path: str | os.PathLike[str]) -> Any:
        if Path(path) == transient:
            raise OSError(errno.EACCES, "synthetic wrong errno")
        return real_scandir(path)

    monkeypatch.setattr(qualifier.os, "scandir", fake_scandir)
    with pytest.raises(QualificationError) as captured:
        qualifier.wait_for_transient_fuse_cleanup(iso_root, manifest["isolation"])
    assert captured.value.code == "ERR_UNEXPECTED_FILES_CREATED"


def test_child_environment_is_exact_and_ambient_canary_is_not_forwarded(iso_root: Path, tmp_path: Path) -> None:
    extra = """
root = Path(os.environ['TMPDIR']).parent
assert os.environ['HOME'] == str(root / 'home')
assert os.environ['XDG_CONFIG_HOME'] == str(root / 'config')
assert os.environ['XDG_DATA_HOME'] == str(root / 'data')
assert os.environ['XDG_CACHE_HOME'] == str(root / 'cache')
assert os.environ['XDG_STATE_HOME'] == str(root / 'state')
assert os.environ['XDG_RUNTIME_DIR'] == str(root / 'runtime')
assert 'AETHER_M1_SECRET_CANARY' not in os.environ
""".strip()
    os.environ["AETHER_M1_SECRET_CANARY"] = "synthetic-secret-canary"
    try:
        result = _run_fake(iso_root, tmp_path, launcher_extra=extra)
    finally:
        os.environ.pop("AETHER_M1_SECRET_CANARY", None)
    assert result["isolation_and_effects"]["ambient_environment_forwarded"] is False


def test_intercall_side_effect_is_caught_before_second_call(iso_root: Path, tmp_path: Path) -> None:
    counter = tmp_path / "counter"
    extra = f"""
count_path = Path({str(counter)!r})
count = int(count_path.read_text()) if count_path.exists() else 0
count_path.write_text(str(count + 1))
leak = Path(os.environ['HOME']) / 'concealed'
if count == 0:
    leak.write_text('synthetic')
else:
    leak.unlink(missing_ok=True)
""".strip()
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path, launcher_extra=extra)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_UNEXPECTED_FILES_CREATED"
    assert counter.read_text() == "1"


def test_malformed_catalog_rejected_without_payload_disclosure(iso_root: Path, tmp_path: Path) -> None:
    canary = b"SYNTHETIC_PRIVATE_CATALOG_CANARY"
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path, catalog_payload=canary)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_CATALOG_MALFORMED_JSON"
    assert canary.decode() not in captured.value.message


def test_catalog_stderr_rejected_without_canary_disclosure(iso_root: Path, tmp_path: Path) -> None:
    canary = "SYNTHETIC_STDERR_CANARY"
    extra = f"sys.stderr.write({canary!r})"
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path, launcher_extra=extra)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_CATALOG_STDERR"
    assert canary not in captured.value.message


def test_catalog_nondeterminism_rejected_at_first_differing_boundary(iso_root: Path, tmp_path: Path) -> None:
    counter = tmp_path / "catalog-counter"
    second = _catalog_payload().replace(b"synthetic", b"changedxx")
    extra = f"""
count_path = Path({str(counter)!r})
count = int(count_path.read_text()) if count_path.exists() else 0
count_path.write_text(str(count + 1))
if count:
    sys.stdout.buffer.write({second!r})
    raise SystemExit(0)
""".strip()
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path, launcher_extra=extra)
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_CATALOG_NON_DETERMINISTIC"


def test_version_mismatch_rejected(iso_root: Path, tmp_path: Path) -> None:
    manifest_path, digest, _launcher, _artifact, _manifest = _make_candidate(tmp_path, version="9.9.9")
    with pytest.raises(QualificationError) as captured:
        qualifier.qualify_orca(
            isolated_root=iso_root,
            manifest_path=manifest_path,
            expected_manifest_sha256=digest,
        )
    assert captured.value.code == "ERR_APPIMAGE_VERSION_MISMATCH"


@pytest.mark.parametrize(("mode", "expected"), (("timeout", "ERR_CHILD_TIMEOUT"), ("nonzero", None), ("success", None)))
def test_owned_process_group_reaps_descendants(tmp_path: Path, mode: str, expected: str | None) -> None:
    pid_file = tmp_path / f"{mode}.pid"
    script = tmp_path / f"child-{mode}"
    tail = "time.sleep(60)" if mode == "timeout" else ("raise SystemExit(4)" if mode == "nonzero" else "raise SystemExit(0)")
    _write_executable(
        script,
        "#!/usr/bin/python3\n"
        "import subprocess\n"
        "import time\n"
        "from pathlib import Path\n"
        "child = subprocess.Popen(['sleep', '60'])\n"
        f"Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        f"{tail}\n",
    )
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
    if expected:
        with pytest.raises(QualificationError) as captured:
            qualifier.run_owned_process_group([str(script)], tmp_path, env, 1)
        assert captured.value.code == expected
    else:
        code, _stdout, _stderr = qualifier.run_owned_process_group([str(script)], tmp_path, env, 2)
        assert code == (4 if mode == "nonzero" else 0)
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_unexpected_cli_exception_is_redacted(
    iso_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    canary = "SYNTHETIC_UNEXPECTED_EXCEPTION_CANARY"

    def fail(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError(canary)

    monkeypatch.setattr(qualifier, "qualify_orca", fail)
    monkeypatch.setattr(sys, "argv", ["qualify_orca.py", "--isolated-root", str(iso_root)])
    with pytest.raises(SystemExit) as captured:
        qualifier.main()
    output = capsys.readouterr()
    assert captured.value.code == 1
    assert canary not in output.out
    assert output.err == ""


@pytest.mark.skipif(not REAL_FIXTURE_AVAILABLE, reason="requires exact installed Orca candidate")
def test_real_candidate_twice_matches_committed_evidence() -> None:
    first_root = _new_root()
    second_root = _new_root()
    try:
        first = qualifier.qualify_orca(isolated_root=first_root)
        second = qualifier.qualify_orca(isolated_root=second_root)
        committed = json.loads((ROOT / "docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json").read_text())
    finally:
        shutil.rmtree(first_root, ignore_errors=True)
        shutil.rmtree(second_root, ignore_errors=True)
    assert first == second
    assert first == committed
    assert first["manifest_identity"]["manifest_sha256"] == qualifier.CANONICAL_MANIFEST_SHA256
    assert first["catalog_identity"] == {
        "schema_version": 1,
        "declared_command_count": 220,
        "actual_command_count": 220,
        "catalog_bytes": 153496,
        "catalog_sha256": "068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b",
        "determinism_verified": True,
    }
