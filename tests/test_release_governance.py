"""Regression tests for integration and release governance."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_governance.py"
SPEC = importlib.util.spec_from_file_location("check_release_governance", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
governance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = governance
SPEC.loader.exec_module(governance)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _init_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Aether Tests")
    (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "test: baseline")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")


def test_version_parser_orders_semver_and_rejects_loose_values() -> None:
    assert governance.Version.parse("0.20.0") > governance.Version.parse("0.19.5")
    assert governance.Version.parse("v0.20.0", tag=True) == governance.Version(0, 20, 0)
    with pytest.raises(ValueError):
        governance.Version.parse("0.20")
    with pytest.raises(ValueError):
        governance.Version.parse("0.20.0-beta")


def test_pull_requests_must_target_main() -> None:
    assert governance.validate_pr_target("main", "feature/example") == []
    assert governance.validate_pr_target("feature/parent", "docs/stacked") == [
        "ordinary PRs must target main; 'docs/stacked' currently targets 'feature/parent'"
    ]


def test_repository_policy_has_one_branching_model() -> None:
    assert governance.validate_policy(ROOT) == []


def test_next_version_preflight_requires_clean_synchronized_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init_repo(tmp_path)
    monkeypatch.setattr(governance, "_open_version_prs", lambda _root: [])

    assert governance.validate_next_version_preflight(tmp_path, "0.20.0") == []

    (tmp_path / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    errors = governance.validate_next_version_preflight(tmp_path, "0.20.0")
    assert "next-version preflight requires a clean working tree" in errors


def test_next_version_preflight_blocks_open_semver_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init_repo(tmp_path)
    monkeypatch.setattr(
        governance,
        "_open_version_prs",
        lambda _root: [
            {
                "number": 113,
                "headRefName": "feature/v0.19.0-autonomous-coordination-design",
                "baseRefName": "main",
                "isDraft": True,
            }
        ],
    )

    errors = governance.validate_next_version_preflight(tmp_path, "0.20.0")
    assert errors == [
        "open SemVer candidate PR #113 (feature/v0.19.0-autonomous-coordination-design -> main) must be merged, abandoned, or superseded first"
    ]


def test_release_boundary_requires_annotated_tag_on_current_main(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.20.0"\ndependencies = ["mcp>=1,<2"]\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "![Version](https://img.shields.io/badge/version-0.20.0-blue)\n",
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text("## 0.20.0\n\n- Fixture.\n", encoding="utf-8")
    notes = tmp_path / "docs" / "releases" / "v0.20.0" / "RELEASE_NOTES.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("# v0.20.0\n", encoding="utf-8")
    _git(tmp_path, "add", "pyproject.toml", "README.md", "CHANGELOG.md", "docs")
    _git(tmp_path, "commit", "-m", "release: prepare v0.20.0")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(tmp_path, "tag", "-a", "v0.20.0", "-m", "v0.20.0")

    assert governance.validate_release(tmp_path, "v0.20.0") == []
