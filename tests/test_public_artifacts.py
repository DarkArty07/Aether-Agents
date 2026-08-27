from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCANNER = ROOT / "scripts" / "check_public_artifacts.py"


def _run(*arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCANNER), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_tracked_public_surface_contains_no_operator_paths() -> None:
    completed = _run("--root", str(ROOT))
    assert completed.returncode == 0, completed.stderr


def test_scanner_rejects_user_home_and_private_desktop_layout(tmp_path: Path) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    private = "/" + "home" + "/operator/" + "Desk" + "top/" + "agentes/product"
    (tmp_path / "README.md").write_text(f"private evidence: {private}\n", encoding="utf-8")
    subprocess.run(("git", "add", "README.md"), cwd=tmp_path, check=True)

    completed = _run("--root", str(tmp_path), cwd=tmp_path)
    assert completed.returncode == 1
    assert "absolute-user-home" in completed.stderr
    assert "operator-desktop-layout" in completed.stderr


def test_scanner_checks_wheel_and_sdist_members(tmp_path: Path) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("portable\n", encoding="utf-8")
    subprocess.run(("git", "add", "README.md"), cwd=tmp_path, check=True)
    private = "/" + "home" + "/operator/private-runtime"

    wheel = tmp_path / "candidate.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("package/metadata.txt", "portable\n")
    sdist = tmp_path / "candidate.tar.gz"
    payload = tmp_path / "evidence.txt"
    payload.write_text(private + "\n", encoding="utf-8")
    with tarfile.open(sdist, "w:gz") as archive:
        archive.add(payload, arcname="candidate/evidence.txt")

    completed = _run(
        "--root",
        str(tmp_path),
        "--artifact",
        str(wheel),
        "--artifact",
        str(sdist),
        cwd=tmp_path,
    )
    assert completed.returncode == 1
    assert "candidate.tar.gz!candidate/evidence.txt: absolute-user-home" in completed.stderr
