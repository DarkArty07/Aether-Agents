"""Optional read-only GitHub integration for project knowledge."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .common import KnowledgeError, git
from .context import KnowledgeContext
from .graphify import GraphifyBackend

_REPO_RE = re.compile(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?(?:\s|$)")


def resolve_github_repository(root: Path) -> str:
    """Resolve and verify GitHub repository from project marker and git remotes."""
    marker = root / ".aether" / "project.toml"
    if not marker.is_file():
        raise KnowledgeError("GITHUB_UNAVAILABLE", "Missing .aether/project.toml project marker.")
    import tomllib

    try:
        parsed = tomllib.loads(marker.read_text(encoding="utf-8"))
    except Exception as exc:
        raise KnowledgeError("GITHUB_UNAVAILABLE", "Cannot parse .aether/project.toml.") from exc

    if parsed.get("forge") != "github":
        raise KnowledgeError(
            "GITHUB_UNAVAILABLE", f"Project forge is '{parsed.get('forge')}', expected 'github'."
        )

    github_sec = parsed.get("github")
    if not isinstance(github_sec, dict) or not github_sec.get("repository"):
        raise KnowledgeError(
            "GITHUB_UNAVAILABLE", "Missing [github].repository in .aether/project.toml."
        )

    configured_repo = str(github_sec["repository"]).strip().strip("/")
    if "/" not in configured_repo:
        raise KnowledgeError(
            "GITHUB_UNAVAILABLE", f"Invalid repository format '{configured_repo}'."
        )

    try:
        remotes = git(root, "remote", "-v").decode("utf-8", "replace")
    except Exception as exc:
        raise KnowledgeError("GITHUB_UNAVAILABLE", "Cannot inspect git remotes.") from exc

    found_repos = set()
    for match in _REPO_RE.finditer(remotes):
        found_repos.add(f"{match.group('owner')}/{match.group('repo')}")

    if not found_repos:
        raise KnowledgeError(
            "GITHUB_UNAVAILABLE", "No GitHub remote found in local git repository."
        )

    matched = any(r.lower() == configured_repo.lower() for r in found_repos)
    if not matched:
        raise KnowledgeError(
            "PROJECT_CONFLICT",
            f"Configured repository '{configured_repo}' does not match git remotes {sorted(found_repos)}.",
        )

    if not shutil.which("gh"):
        raise KnowledgeError("GITHUB_UNAVAILABLE", "The 'gh' CLI is not installed or available.")

    return configured_repo


def _gh_environment() -> dict[str, str]:
    """Isolate environment for gh subprocess matching repo git conventions."""
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GH_PROMPT_DISABLED": "1",
        "NO_COLOR": "1",
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GH_HOST",
    ):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _run_gh(root: Path, args: list[str]) -> Any:
    """Execute bounded gh command with structured output in bound repository."""
    try:
        completed = subprocess.run(
            ["gh", *args],
            cwd=root,
            env=_gh_environment(),
            capture_output=True,
            timeout=30,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise KnowledgeError("GITHUB_UNAVAILABLE", "GitHub CLI request timed out.") from exc
    except OSError as exc:
        raise KnowledgeError("GITHUB_UNAVAILABLE", f"GitHub CLI execution failed: {exc}") from exc

    if completed.returncode != 0:
        err = completed.stderr.strip() or completed.stdout.strip() or "Unknown error"
        raise KnowledgeError("GITHUB_UNAVAILABLE", f"GitHub CLI error: {err}")

    try:
        return json.loads(completed.stdout)
    except Exception as exc:
        raise KnowledgeError("GITHUB_UNAVAILABLE", "Failed to parse GitHub CLI output.") from exc


def _parse_pr_summary(raw: dict[str, Any]) -> dict[str, Any]:
    ci_status = None
    rollup = raw.get("statusCheckRollup")
    if isinstance(rollup, list) and rollup:
        states = {
            item.get("status") or item.get("conclusion") or item.get("state")
            for item in rollup
            if isinstance(item, dict)
        }
        ci_status = "SUCCESS" if states == {"SUCCESS"} or states == {"COMPLETED"} else "PENDING"
    elif isinstance(rollup, dict):
        ci_status = str(rollup.get("state") or "")

    return {
        "number": int(raw["number"]),
        "title": str(raw.get("title", "")),
        "head_branch": str(raw.get("headRefName", "")),
        "base_branch": str(raw.get("baseRefName", "")),
        "head_sha": str(raw.get("headRefOid", "")),
        "base_sha": str(raw.get("baseRefOid", "")),
        "draft": bool(raw.get("isDraft", False)),
        "ci_status": ci_status,
        "review_state": raw.get("reviewDecision"),
        "updated_at": str(raw.get("updatedAt", "")),
    }


def execute_list_prs(
    root: Path,
    ctx: KnowledgeContext,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """List open PRs with bounded parameters."""
    repo = resolve_github_repository(root)
    limit = int(arguments.get("limit", 20))
    limit = min(max(limit, 1), 50)
    base = arguments.get("base")

    args = [
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--json",
        "number,title,headRefName,baseRefName,headRefOid,baseRefOid,isDraft,statusCheckRollup,reviewDecision,updatedAt",
        "--limit",
        str(limit),
    ]
    if base:
        args.extend(["--base", str(base)])

    raw_list = _run_gh(root, args)
    if not isinstance(raw_list, list):
        raise KnowledgeError("GITHUB_UNAVAILABLE", "Unexpected gh pr list response shape.")

    prs = [_parse_pr_summary(p) for p in raw_list]
    import time

    github_ctx = {
        "repository": repo,
        "observed_at": time.time(),
        "graph_revision": ctx.source_revision,
    }

    if not prs:
        content = f"No open pull requests found for repository {repo}."
    else:
        lines = [f"Open pull requests for {repo} ({len(prs)} shown):"]
        for p in prs:
            lines.append(
                f"- #{p['number']}: {p['title']} ({p['head_branch']} -> {p['base_branch']}) [{p['head_sha'][:8]}]"
            )
        content = "\n".join(lines)

    return github_ctx, prs, content


def execute_pr_impact(
    backend: GraphifyBackend,
    location: Path,
    root: Path,
    ctx: KnowledgeContext,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], str]:
    """Compute impact of a single PR against the current graph."""
    repo = resolve_github_repository(root)
    pr_number = int(arguments["pr_number"])

    # Fetch PR details and files
    args = [
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        "number,title,headRefName,baseRefName,headRefOid,baseRefOid,isDraft,statusCheckRollup,reviewDecision,updatedAt,files",
    ]
    raw = _run_gh(root, args)
    if not isinstance(raw, dict):
        raise KnowledgeError("GITHUB_UNAVAILABLE", "Unexpected gh pr view response shape.")

    pr_summary = _parse_pr_summary(raw)
    head_before = pr_summary["head_sha"]

    raw_files = raw.get("files", [])
    file_paths = []
    if isinstance(raw_files, list):
        for f in raw_files:
            if isinstance(f, dict) and f.get("path"):
                file_paths.append(str(f["path"]))

    total_files = len(file_paths)
    truncated = False
    # Bounded file pagination check (max 500 files for impact)
    if len(file_paths) > 500:
        file_paths = file_paths[:500]
        truncated = True

    graph_file = location / "graphify-out" / "graph.json"
    source_root = location / "sources"

    worker_res = backend.run(
        "pr_impact",
        source_root=source_root,
        graph_path=graph_file,
        arguments={"files": file_paths},
    )

    # Verify PR head SHA after multi-call analysis
    check_args = ["pr", "view", str(pr_number), "--repo", repo, "--json", "headRefOid"]
    head_check = _run_gh(root, check_args)
    head_after = head_check.get("headRefOid") if isinstance(head_check, dict) else None
    if head_after != head_before:
        # Retry once if head moved
        raw = _run_gh(root, args)
        pr_summary = _parse_pr_summary(raw)
        head_retry = pr_summary["head_sha"]
        file_paths = [
            str(f["path"]) for f in raw.get("files", []) if isinstance(f, dict) and f.get("path")
        ]
        total_files = len(file_paths)
        truncated = len(file_paths) > 500
        if truncated:
            file_paths = file_paths[:500]
        worker_res = backend.run(
            "pr_impact",
            source_root=source_root,
            graph_path=graph_file,
            arguments={"files": file_paths},
        )
        head_check = _run_gh(root, check_args)
        head_final = head_check.get("headRefOid") if isinstance(head_check, dict) else None
        if head_final != head_retry:
            raise KnowledgeError(
                "GITHUB_UNAVAILABLE", f"PR #{pr_number} head SHA moved during analysis."
            )

    import time

    github_ctx = {
        "repository": repo,
        "observed_at": time.time(),
        "graph_revision": ctx.source_revision,
    }
    impact_info = worker_res.get("impact", {})
    if truncated:
        impact_info["truncated"] = True
        impact_info["total_files"] = total_files
        impact_info["analyzed_files"] = len(file_paths)
        impact_info["warning"] = (
            f"PR touches {total_files} files; analysis truncated to first 500 files."
        )

    unmatched = impact_info.get("unmatched_files", [])
    if unmatched:
        impact_info["unmatched_warning"] = (
            f"{len(unmatched)} files are not indexed in the knowledge graph."
        )

    references = worker_res.get("references", [])
    content = str(worker_res.get("content", ""))
    if truncated:
        content += (
            f"\nWarning: PR touches {total_files} files; analysis truncated to first 500 files."
        )
    if unmatched:
        content += f"\nNotice: {len(unmatched)} unanalyzed files are not present in the graph."

    return github_ctx, pr_summary, impact_info, references, content


def execute_triage_prs(
    backend: GraphifyBackend,
    location: Path,
    root: Path,
    ctx: KnowledgeContext,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    """Triage PRs with per-PR impact and community overlap detection."""
    github_ctx, prs, _ = execute_list_prs(root, ctx, arguments)
    repo = github_ctx["repository"]

    graph_file = location / "graphify-out" / "graph.json"
    source_root = location / "sources"

    triaged_prs = []
    for p in prs:
        pr_num = p["number"]
        files: list[str] = []
        truncated = False
        try:
            view_raw = _run_gh(
                root,
                [
                    "pr",
                    "view",
                    str(pr_num),
                    "--repo",
                    repo,
                    "--json",
                    "files",
                ],
            )
            files = [
                str(f["path"])
                for f in view_raw.get("files", [])
                if isinstance(f, dict) and f.get("path")
            ]
            total_files = len(files)
            if len(files) > 200:
                files = files[:200]
                truncated = True
            worker_res = backend.run(
                "pr_impact",
                source_root=source_root,
                graph_path=graph_file,
                arguments={"files": files},
            )
            impact = worker_res.get("impact", {})
            if truncated:
                impact["truncated"] = True
                impact["total_files"] = total_files
                impact["analyzed_files"] = len(files)
        except Exception as exc:
            # Failure must NOT masquerade as zero impact
            impact = {
                "status": "unavailable",
                "error": str(exc),
                "files": len(files) if files else None,
                "matched_files": [],
                "unmatched_files": files,
                "communities": [],
                "node_count": None,
            }
        triaged_pr = dict(p, impact=impact)
        triaged_prs.append(triaged_pr)

    # Detect community overlaps between PR pairs
    overlap_pairs = []
    for i in range(len(triaged_prs)):
        for j in range(i + 1, len(triaged_prs)):
            c_i = set(triaged_prs[i].get("impact", {}).get("communities", []))
            c_j = set(triaged_prs[j].get("impact", {}).get("communities", []))
            shared = sorted(list(c_i & c_j))
            if shared:
                overlap_pairs.append(
                    {
                        "pr_a": triaged_prs[i]["number"],
                        "pr_b": triaged_prs[j]["number"],
                        "shared_communities": shared,
                    }
                )

    lines = [f"PR Triage for {repo} ({len(triaged_prs)} PRs analyzed):"]
    for p in triaged_prs:
        imp = p.get("impact", {})
        if imp.get("status") == "unavailable":
            lines.append(
                f"- #{p['number']}: {p['title']} (impact analysis unavailable: {imp.get('error', 'unknown error')})"
            )
        else:
            unmatched = imp.get("unmatched_files", [])
            unmatched_note = f", {len(unmatched)} unanalyzed files" if unmatched else ""
            lines.append(
                f"- #{p['number']}: {p['title']} touches communities {imp.get('communities', [])} "
                f"({imp.get('node_count', 0)} nodes affected{unmatched_note})"
            )
    if overlap_pairs:
        lines.append("\nCommunity overlaps detected (potential conflict):")
        for o in overlap_pairs:
            lines.append(
                f"  * PR #{o['pr_a']} and PR #{o['pr_b']} share communities: {o['shared_communities']}"
            )
    else:
        lines.append("\nNo community overlaps between open PRs.")

    content = "\n".join(lines)
    return github_ctx, triaged_prs, overlap_pairs, content
