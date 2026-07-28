#!/usr/bin/env python3
"""Fail-closed checks for Aether branch integration and release boundaries."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

SEMVER = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)
SEMVER_TAG = re.compile(
    r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)
VERSION_BRANCH = re.compile(
    r"^(?:feature|release)/v?(?P<version>\d+\.\d+\.\d+)(?:[-/].*)?$"
)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str, *, tag: bool = False) -> "Version":
        match = (SEMVER_TAG if tag else SEMVER).fullmatch(value)
        if not match:
            kind = "vX.Y.Z tag" if tag else "X.Y.Z version"
            raise ValueError(f"expected {kind}, got {value!r}")
        return cls(*(int(match.group(name)) for name in ("major", "minor", "patch")))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class GovernanceError(RuntimeError):
    """A release-governance invariant failed."""


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        command = " ".join(args)
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GovernanceError(f"command failed: {command}: {detail}")
    return completed


def _git(root: Path, *args: str) -> str:
    return _run(("git", *args), cwd=root).stdout.strip()


def _package_version(root: Path) -> Version:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    raw = payload.get("project", {}).get("version")
    if not isinstance(raw, str):
        raise GovernanceError("pyproject.toml does not define project.version")
    try:
        return Version.parse(raw)
    except ValueError as exc:
        raise GovernanceError(str(exc)) from exc


def validate_pr_target(base: str, head: str) -> list[str]:
    errors: list[str] = []
    if base != "main":
        errors.append(
            f"ordinary PRs must target main; {head!r} currently targets {base!r}"
        )
    if head == "main":
        errors.append("main cannot be used as the head branch of its own PR")
    return errors


def validate_policy(root: Path) -> list[str]:
    errors: list[str] = []
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    contributing = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    contributor_index = (root / "docs/contributing/README.md").read_text(encoding="utf-8")
    test_workflow = (root / ".github/workflows/test.yml").read_text(encoding="utf-8")
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    policy_texts = {
        "AGENTS.md": agents,
        "CONTRIBUTING.md": contributing,
        "docs/contributing/README.md": contributor_index,
    }
    forbidden = {
        "Feature → dev": "obsolete dev branching model remains",
        "dev → main (release)": "merge to main is still conflated with release",
        "feature → dev → main": "obsolete three-branch model remains",
        "Target `dev`": "pull requests are still directed to dev",
    }
    for relative, text in policy_texts.items():
        for needle, message in forbidden.items():
            if needle in text:
                errors.append(f"{relative}: {message}")

    required = {
        "Latest integrated, tested repository state": "main integration identity missing",
        "Standing GitHub Automation Authority": "standing GitHub authority missing",
        "Merge to `main` does not imply activation": "integration/publication split missing",
        "ODR-0001-main-integration-and-release-automation.md": "governing ODR reference missing",
    }
    for needle, message in required.items():
        if needle not in agents:
            errors.append(message)

    if "branches: [main, dev]" in test_workflow:
        errors.append("test workflow still treats removed dev branch as active")

    dependencies = pyproject.get("project", {}).get("dependencies", [])
    mcp_specs = [item for item in dependencies if isinstance(item, str) and item.startswith("mcp")]
    if not mcp_specs or not any("<2" in item for item in mcp_specs):
        errors.append("pyproject must cap mcp below 2.0 until the server migrates to the 2.x API")

    for relative in (
        "docs/decisions/ODR-0001-main-integration-and-release-automation.md",
        ".github/workflows/release-governance.yml",
        ".github/workflows/release.yml",
    ):
        if not (root / relative).is_file():
            errors.append(f"required governance artifact missing: {relative}")
    return errors


def validate_release(root: Path, tag_name: str) -> list[str]:
    errors: list[str] = []
    try:
        tag_version = Version.parse(tag_name, tag=True)
    except ValueError as exc:
        return [str(exc)]

    package_version = _package_version(root)
    if tag_version != package_version:
        errors.append(
            f"tag {tag_name} disagrees with pyproject version {package_version}"
        )

    readme = (root / "README.md").read_text(encoding="utf-8")
    if f"version-{package_version}-" not in readme:
        errors.append(f"README version badge does not contain {package_version}")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog_pattern = re.compile(
        rf"(?m)^##\s+(?:\[)?v?{re.escape(str(package_version))}(?:\])?(?:\s|$)"
    )
    if not changelog_pattern.search(changelog):
        errors.append(f"CHANGELOG has no release heading for {package_version}")

    release_notes = root / "docs" / "releases" / f"v{package_version}" / "RELEASE_NOTES.md"
    if not release_notes.is_file():
        errors.append(f"release notes are missing: {release_notes.relative_to(root)}")

    if _git(root, "status", "--porcelain"):
        errors.append("release validation requires a clean working tree")

    tag_type = _git(root, "cat-file", "-t", f"refs/tags/{tag_name}")
    if tag_type != "tag":
        errors.append(f"{tag_name} must be an annotated tag, got {tag_type!r}")

    tag_commit = _git(root, "rev-parse", f"refs/tags/{tag_name}^{{commit}}")
    main_commit = _git(root, "rev-parse", "refs/remotes/origin/main^{commit}")
    if tag_commit != main_commit:
        errors.append(
            f"release tag must point to current origin/main: tag={tag_commit}, main={main_commit}"
        )
    return errors


def _latest_semver_tag(root: Path) -> Version | None:
    output = _git(root, "tag", "--sort=-v:refname")
    for line in output.splitlines():
        if SEMVER_TAG.fullmatch(line.strip()):
            return Version.parse(line.strip(), tag=True)
    return None


def _open_version_prs(root: Path) -> list[dict[str, object]]:
    if shutil.which("gh") is None:
        raise GovernanceError("gh is required to verify open version PRs")
    completed = _run(
        (
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            "200",
            "--json",
            "number,headRefName,baseRefName,isDraft,title,url",
        ),
        cwd=root,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, list):
        raise GovernanceError("gh pr list returned an unexpected payload")
    return [item for item in payload if isinstance(item, dict)]


def validate_next_version_preflight(root: Path, raw_version: str) -> list[str]:
    errors: list[str] = []
    try:
        next_version = Version.parse(raw_version)
    except ValueError as exc:
        return [str(exc)]

    branch = _git(root, "branch", "--show-current")
    if branch != "main":
        errors.append(f"next-version preflight must run on main, got {branch!r}")

    if _git(root, "status", "--porcelain"):
        errors.append("next-version preflight requires a clean working tree")

    local_head = _git(root, "rev-parse", "HEAD")
    remote_main = _git(root, "rev-parse", "refs/remotes/origin/main")
    if local_head != remote_main:
        errors.append(
            f"local main is not synchronized with origin/main: local={local_head}, remote={remote_main}"
        )

    latest = _latest_semver_tag(root)
    if latest is not None and next_version <= latest:
        errors.append(
            f"next version {next_version} must be greater than latest published {latest}"
        )

    try:
        open_prs = _open_version_prs(root)
    except (GovernanceError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        return errors

    for pr in open_prs:
        head = str(pr.get("headRefName", ""))
        match = VERSION_BRANCH.fullmatch(head)
        if not match:
            continue
        base = str(pr.get("baseRefName", ""))
        number = pr.get("number", "?")
        errors.append(
            f"open SemVer candidate PR #{number} ({head} -> {base}) must be merged, abandoned, or superseded first"
        )
    return errors


def _print_result(errors: list[str]) -> int:
    if not errors:
        print("release_governance=PASS")
        return 0
    print("release_governance=FAIL", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the script's parent repository)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("policy", help="validate static repository governance")

    pr_parser = subparsers.add_parser("pr", help="validate a pull-request target")
    pr_parser.add_argument("--base", required=True)
    pr_parser.add_argument("--head", required=True)

    release_parser = subparsers.add_parser("release", help="validate a release tag")
    release_parser.add_argument("--tag", required=True)

    next_parser = subparsers.add_parser(
        "preflight-next-version",
        help="block a new SemVer candidate when integration is unresolved",
    )
    next_parser.add_argument("--version", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.repo_root.resolve()
    try:
        if args.command == "policy":
            errors = validate_policy(root)
        elif args.command == "pr":
            errors = validate_pr_target(args.base, args.head)
        elif args.command == "release":
            errors = validate_release(root, args.tag)
        elif args.command == "preflight-next-version":
            errors = validate_next_version_preflight(root, args.version)
        else:  # pragma: no cover - argparse enforces this
            raise GovernanceError(f"unsupported command: {args.command}")
    except (GovernanceError, FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        errors = [str(exc)]
    return _print_result(errors)


if __name__ == "__main__":
    raise SystemExit(main())
