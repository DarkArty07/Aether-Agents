from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCANNER = ROOT / "scripts" / "check_public_artifacts.py"
ROOT_REPORTS = ("INTEGRATIONS.md", "INCOMPLETE_IMPLEMENTATIONS.md")
# Updated by the owner-authorized Graphify integration; retain byte-integrity coverage.
INTEGRATIONS_SHA256 = "b34ac51af0a9ae65d3b35fb1e724165042585b61bfe92ed3196369e853c86536"
# The canonical base manifest step asserts `VERSION` against an ERE quoted in the workflow.
_VERSION_GUARD_RE = re.compile(r"^\s*grep -Eq '(?P<pattern>[^']+)' VERSION$", re.MULTILINE)
# The accepted package identities mirror `.github/workflows/release.yml` (`Validate release
# tag`): a stable `X.Y.Z` or the RC form `X.Y.ZrcN` mapped from tag `vX.Y.Z-rc.N`, plus the
# pre-existing development form `X.Y.Z.devN`.  The tag/display identity `1.0.0-rc.1` is not a
# package identity, and the release workflow's own grammar (no leading zeros, RC number >= 1)
# bounds the numeric components here too.
ACCEPTED_PACKAGE_IDENTITIES = (
    "1.0.0",
    "1.0.0rc1",
    "1.0.0rc2",
    "1.0.0rc3",
    "1.0.0rc4",
    "1.0.0rc5",
    "1.0.0rc6",
    "1.0.0rc7",
    "1.0.0rc8",
    "1.0.0rc9",
    "1.0.0rc10",
    "1.0.0rc11",
    "1.0.0rc12",
    "1.0.0rc13",
    "1.0.0rc14",
    "2.30.4",
    "1.0.0.dev3",
)
REFUSED_PACKAGE_IDENTITIES = (
    "1.0.0-rc.1",
    "1.0.0rc",
    "1.0",
    "v1.0.0",
    "abc",
    "",
    "1.0.0.post1",
    "1.0.0rc0",
    "01.0.0",
)


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


def test_root_reports_are_tracked_immutable_and_privacy_safe(tmp_path: Path) -> None:
    tracked = subprocess.run(
        ("git", "ls-files", "--error-unmatch", *ROOT_REPORTS),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert tracked.returncode == 0, tracked.stderr

    integrations = ROOT / "INTEGRATIONS.md"
    assert integrations.stat().st_size == 9305
    assert hashlib.sha256(integrations.read_bytes()).hexdigest() == INTEGRATIONS_SHA256

    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    for report in ROOT_REPORTS:
        shutil.copyfile(ROOT / report, tmp_path / report)
    subprocess.run(("git", "add", *ROOT_REPORTS), cwd=tmp_path, check=True)

    completed = _run("--root", str(tmp_path), cwd=tmp_path)
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


def test_scanner_rejects_windows_user_home(tmp_path: Path) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    win_path = "C:\\" + "Users" + "\\operator\\repo\\file.txt"
    (tmp_path / "README.md").write_text(f"windows path: {win_path}\n", encoding="utf-8")
    subprocess.run(("git", "add", "README.md"), cwd=tmp_path, check=True)

    completed = _run("--root", str(tmp_path), cwd=tmp_path)
    assert completed.returncode == 1
    assert "windows-user-home" in completed.stderr


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


def test_readme_is_a_current_beta_portal_and_package_metadata_is_stable() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    incomplete = (ROOT / "INCOMPLETE_IMPLEMENTATIONS.md").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "multi-agent software-engineering product" in readme
    assert "[documentation index](docs/index.md)" in readme
    assert "`docs/capabilities.toml`](docs/capabilities.toml)" in readme
    assert "sole current implementation-status and traceability registry" in readme
    assert "documented transitional downstream" in readme
    # The wheel's METADATA embeds this portal. RC8 contains #495 guidance,
    # but neither source nor tag proves live activation or agent behavior.
    assert "releases/tag/v1.0.0-rc.8" not in readme
    assert "releases/tag/v1.0.0-rc.7" not in readme
    assert "releases/tag/v1.0.0-rc.6" not in readme
    assert "releases/tag/v1.0.0-rc.5" not in readme
    assert "`1.0.0rc14` / `1.0.0-rc.14`" in readme
    assert "local annotated tag identity is `v1.0.0-rc.14`" in readme
    assert "restores the new Morfeo SOUL and canonical contract skills" in readme
    assert (
        "neither this source nor a local tag proves what is installed or that agent behavior improved"
        in readme
    )
    assert "Query `aether doctor` for the active version" in readme
    assert "no tag is pushed and no GitHub/package publication is authorized" in readme
    assert "RC7 and earlier local tags remain immutable" in readme
    assert "releases/tag/v1.0.0-rc.1" in readme
    assert "published but rejected" in readme
    status = [line for line in readme.splitlines() if line.startswith("**Status:**")]
    assert len(status) == 1, f"expected exactly one status paragraph, found {len(status)}"
    assert "releases/tag/v1.0.0-rc.14" not in status[0]
    assert "releases/tag/v1.0.0-rc.13" not in status[0]
    assert "releases/tag/v1.0.0-rc.12" not in status[0]
    assert "releases/tag/v1.0.0-rc.10" not in status[0]
    assert "releases/tag/v1.0.0-rc.9" not in status[0]
    assert "releases/tag/v1.0.0-rc.8" not in status[0]
    assert "releases/tag/v1.0.0-rc.7" not in status[0]
    assert "releases/tag/v1.0.0-rc.6" not in status[0]
    assert "releases/tag/v1.0.0-rc.5" not in status[0]
    assert "release_impact = minor" in status[0]
    assert "release_action = prepare" in status[0]
    assert "release_channel = prerelease" in status[0]
    for time_bound in ("will be published", "not yet", "pending", "to be superseded"):
        assert time_bound not in status[0], f"status paragraph carries {time_bound!r}"
    assert "beta stabilization build, not a release candidate" not in readme
    assert "no release candidate has been published" not in readme
    assert "**not** stable `1.0.0`" in readme
    assert "a PyPI release or WSL2 qualification" in readme
    assert "#261 remains open" in readme
    assert "remain explicit unsupported placeholders" in readme
    assert "`aether reconcile` supports only its bounded `--to active` form" in readme
    assert "Historical snapshot" in incomplete
    assert "does not state the current implementation" in incomplete
    assert project["name"] == "aether-agents"
    assert "multi-agent software-engineering method" in project["description"]
    assert set(project["entry-points"]["hermes_agent.plugins"]) == {
        "aether-contract-observer",
        "aether-objective-contracts",
        "aether-project-knowledge",
        "aether-telegram-monitor",
    }


def test_historical_contract_oc_0084270d940c98d9_tombstone_preserves_locator() -> None:
    tombstone = ROOT / ".aether" / "objective-contracts" / "oc_0084270d940c98d9" / "tombstone.json"
    assert tombstone.is_file()
    assert not (ROOT / ".aether" / "objective-contracts" / "oc_0084270d940c98d9" / "v1.md").exists()
    payload = json.loads(tombstone.read_text(encoding="utf-8"))
    assert (
        payload["original_sha256"]
        == "7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb"
    )
    assert payload["historical_commit_locator"] == "dad66f7e592b6a172ba9168f63df5080e7a31ec2"
    assert (
        payload["superseding_safe_locator"]
        == ".aether/objective-contracts/oc_0084270d940c98d9/tombstone.json"
    )
    assert "403" in payload["reason"]


def test_canonical_base_manifest_matches_tracked_non_specs_files() -> None:
    policy_workflow = ROOT / ".github" / "workflows" / "policy.yml"
    assert policy_workflow.is_file()
    lines = policy_workflow.read_text(encoding="utf-8").splitlines()
    in_heredoc = False
    expected: list[str] = []
    for line in lines:
        if "cat >\"$expected\" <<'EOF'" in line:
            in_heredoc = True
            continue
        if in_heredoc and line.strip() == "EOF":
            in_heredoc = False
            break
        if in_heredoc:
            stripped = line.strip()
            if stripped:
                expected.append(stripped)
    assert expected, "Failed to extract expected manifest from policy workflow"
    expected.sort()

    git_ls = subprocess.run(
        ("git", "ls-files"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    actual = sorted(path for path in git_ls.stdout.splitlines() if not path.startswith("specs/"))
    assert expected == actual


def _canonical_base_manifest_version_pattern() -> str:
    """Return the single ERE the base manifest step applies to the `VERSION` file."""

    workflow = ROOT / ".github" / "workflows" / "policy.yml"
    patterns = _VERSION_GUARD_RE.findall(workflow.read_text(encoding="utf-8"))
    assert len(patterns) == 1, f"expected exactly one VERSION guard, found {patterns}"
    return patterns[0]


def test_canonical_base_manifest_guard_accepts_only_supported_package_identities() -> None:
    pattern = _canonical_base_manifest_version_pattern()

    for identity in ACCEPTED_PACKAGE_IDENTITIES:
        assert re.search(pattern, identity), f"guard refuses supported identity {identity!r}"
    for identity in REFUSED_PACKAGE_IDENTITIES:
        assert not re.search(pattern, identity), f"guard accepts unsupported identity {identity!r}"

    declared = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.search(pattern, declared), f"guard refuses the repository's own VERSION {declared!r}"
