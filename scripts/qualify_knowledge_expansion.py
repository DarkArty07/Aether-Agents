#!/usr/bin/env python3
"""Run deterministic and optional live qualification for knowledge expansion.

The default lane uses temporary Git repositories and the production knowledge
service.  It never calls an auxiliary model or GitHub.  ``--live-auxiliary``
adds the provisioned auxiliary and, when a real project id is supplied, the
read-only GitHub checks.  Missing optional access is reported as a skip rather
than as a successful live qualification.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aether_agents.knowledge.common import KnowledgeError  # noqa: E402
from aether_agents.knowledge.component import configure  # noqa: E402
from aether_agents.knowledge.context import resolve_context  # noqa: E402
from aether_agents.knowledge.service import (  # noqa: E402
    KNOWLEDGE_ACTIONS,
    MEMORY_ACTIONS,
    KnowledgeService,
    validate_arguments,
)
from aether_agents.observation.context import ProjectRegistry  # noqa: E402

FIXTURE_PROJECTS = (
    ("11111111-1111-4111-8111-111111111111", "alpha"),
    ("22222222-2222-4222-8222-222222222222", "beta"),
)
UNAVAILABLE_CODES = frozenset(
    {
        "COMPONENT_UNAVAILABLE",
        "GITHUB_UNAVAILABLE",
        "INDEX_MISSING",
        "PROJECT_CONFLICT",
        "PROJECT_UNRESOLVED",
        "VIEW_MISMATCH",
    }
)


def _run_git(root: Path, *arguments: str) -> str:
    command = [
        "git",
        "-c",
        "user.name=Aether qualification",
        "-c",
        "user.email=qualification@example.invalid",
        *arguments,
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git failed"
        raise RuntimeError(f"fixture git command failed: {detail}")
    return completed.stdout.strip()


def _make_fixture(root: Path, project_id: str, prefix: str) -> None:
    (root / ".aether").mkdir(parents=True)
    (root / ".aether" / "project.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'project_id = "{project_id}"',
                f'name = "{prefix} qualification fixture"',
                'initialized_by = "1.0.0"',
                'forge = "local"',
                'contract_root = "specs"',
                "",
            )
        ),
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {prefix.title()} qualification\n\n"
        f"Requirement: the {prefix} workflow must call {prefix}_process.\n",
        encoding="utf-8",
    )
    (root / "workflow.py").write_text(
        f"def {prefix}_helper(value: int) -> int:\n"
        "    return value + 1\n\n"
        f"def {prefix}_process(value: int) -> int:\n"
        f"    return {prefix}_helper(value)\n",
        encoding="utf-8",
    )
    _run_git(root, "init", "-q")
    _run_git(root, "add", ".")
    _run_git(root, "commit", "-qm", f"Create {prefix} qualification fixture")


def _catalog_examples() -> tuple[dict[str, Any], dict[str, Any]]:
    project_examples = {
        "status": {"action": "status"},
        "query": {
            "action": "query",
            "question": "Where is the workflow implemented?",
            "budget_tokens": 256,
            "traversal": "dfs",
            "depth": 2,
            "context_filter": ["CALLS"],
        },
        "explain": {"action": "explain", "node": "workflow_process"},
        "neighbors": {"action": "neighbors", "node": "workflow_process"},
        "community": {"action": "community", "community_id": 1},
        "path": {
            "action": "path",
            "source": "workflow_process",
            "target": "workflow_helper",
            "max_hops": 6,
            "undirected": True,
        },
        "impact": {
            "action": "impact",
            "node": "workflow_process",
            "depth": 2,
            "relations": ["CALLS"],
        },
        "update": {"action": "update", "reason": "Refresh the committed fixture"},
        "stats": {"action": "stats"},
        "god_nodes": {"action": "god_nodes", "top_n": 3},
        "list_prs": {"action": "list_prs", "limit": 3},
        "pr_impact": {"action": "pr_impact", "pr_number": 1},
        "triage_prs": {"action": "triage_prs", "limit": 3},
        "visualize": {"action": "visualize", "format": "graph", "detail": "auto"},
    }
    memory_examples = {
        "save": {
            "action": "save",
            "idempotency_key": "qualification-memory-example-01",
            "situation": "A qualification fixture was refreshed.",
            "lesson": "Run the production service path before inspecting derived output.",
            "applicability": "The deterministic qualification lane.",
            "outcome": "useful",
            "evidence": [],
        },
        "search": {"action": "search", "query": "qualification", "limit": 5},
        "read": {"action": "read", "note_id": "wn_11111111111111111111111111111111"},
        "correct": {
            "action": "correct",
            "note_id": "wn_11111111111111111111111111111111",
            "expected_revision": 1,
            "reason": "The qualification boundary changed.",
            "replacement": {
                "lesson": "Re-run the production service path after the boundary changes.",
                "applicability": "The deterministic qualification lane.",
            },
            "evidence": [],
        },
        "reflect": {"action": "reflect"},
    }
    return project_examples, memory_examples


def _validate_catalog() -> dict[str, Any]:
    project_examples, memory_examples = _catalog_examples()
    if tuple(KNOWLEDGE_ACTIONS) != tuple(project_examples):
        raise RuntimeError("project knowledge example catalog does not match the 14-action catalog")
    if tuple(MEMORY_ACTIONS) != tuple(memory_examples):
        raise RuntimeError("work memory example catalog does not match the 5-action catalog")
    for action, arguments in project_examples.items():
        validate_arguments("project_knowledge", arguments)
    for action, arguments in memory_examples.items():
        validate_arguments("work_memory", arguments)

    invalid_cases = (
        ("project_knowledge", {"action": "query", "question": "x", "undirected": True}),
        (
            "project_knowledge",
            {"action": "path", "source": "a", "target": "b", "context_filter": ["x"]},
        ),
        ("project_knowledge", {"action": "visualize", "format": "tree", "detail": "full"}),
        ("work_memory", {"action": "search", "query": "x", "limit": 21}),
        ("project_knowledge", {"action": "status", "project_id": "secret"}),
    )
    rejected = 0
    for tool, arguments in invalid_cases:
        try:
            validate_arguments(tool, arguments)
        except KnowledgeError:
            rejected += 1
        else:
            raise RuntimeError(f"invalid example was accepted: {tool}/{arguments['action']}")
    return {
        "project_actions": len(KNOWLEDGE_ACTIONS),
        "memory_actions": len(MEMORY_ACTIONS),
        "validated_examples": len(project_examples) + len(memory_examples),
        "rejected_boundary_cases": rejected,
    }


def _active_component() -> tuple[Path | None, dict[str, Any]]:
    service = KnowledgeService()
    try:
        configuration = service.configuration()
    except KnowledgeError as exc:
        return None, {"status": "skipped", "reason": exc.code}
    value = configuration.get("python")
    if (
        not configuration.get("enabled")
        or not isinstance(value, str)
        or not Path(value).is_absolute()
        or not Path(value).is_file()
    ):
        return None, {"status": "skipped", "reason": "COMPONENT_UNAVAILABLE"}
    if configuration.get("graphify_version") != "0.9.54":
        return None, {"status": "skipped", "reason": "GRAPHIFY_VERSION_MISMATCH"}
    return Path(value), {
        "status": "available",
        "python_version": configuration.get("python_version"),
    }


def _call(
    service: KnowledgeService,
    context: Any,
    action: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    result = service.execute(context, "project_knowledge", {"action": action, **arguments})
    if result.get("ok") is not True:
        error = result.get("error", {})
        raise KnowledgeError(
            str(error.get("code", "QUALIFICATION_FAILED")),
            str(error.get("message", "Knowledge operation failed.")),
        )
    return result


def _memory_call(
    service: KnowledgeService,
    context: Any,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    result = service.execute(context, "work_memory", arguments)
    if result.get("ok") is not True:
        error = result.get("error", {})
        raise KnowledgeError(
            str(error.get("code", "QUALIFICATION_FAILED")),
            str(error.get("message", "Memory operation failed.")),
        )
    return result


def _artifact_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: artifact.get(key)
        for key in (
            "id",
            "format",
            "bytes",
            "sha256",
            "rendered_nodes",
            "total_nodes",
            "aggregated",
        )
    }


def _fixture_report(
    service: KnowledgeService,
    contexts: list[tuple[str, Any]],
) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for project_id, context in contexts:
        prefix = "alpha" if project_id == FIXTURE_PROJECTS[0][0] else "beta"
        before = _call(service, context, "status", {})
        update = _call(
            service,
            context,
            "update",
            {"reason": "Deterministic qualification refresh", "mode": "structural"},
        )
        query = _call(
            service,
            context,
            "query",
            {"question": f"{prefix}_process", "traversal": "dfs", "depth": 2},
        )
        if prefix not in str(query.get("content", "")):
            raise RuntimeError(f"query did not return the bound {prefix} fixture")

        explain = _call(service, context, "explain", {"node": f"{prefix}_process"})
        neighbors = _call(service, context, "neighbors", {"node": f"{prefix}_process"})
        impact = _call(
            service,
            context,
            "impact",
            {"node": f"{prefix}_process", "depth": 2, "relations": ["CALLS"]},
        )
        path = _call(
            service,
            context,
            "path",
            {
                "source": f"{prefix}_process",
                "target": f"{prefix}_helper",
                "max_hops": 6,
                "undirected": True,
            },
        )
        stats = _call(service, context, "stats", {})
        gods = _call(service, context, "god_nodes", {"top_n": 3})
        resolved = explain.get("resolved_node", {})
        community_id = resolved.get("community_id")
        if community_id is None:
            for node in gods.get("nodes", []):
                if node.get("community_id") is not None:
                    community_id = node["community_id"]
                    break
        community: dict[str, Any] | None = None
        if community_id is not None:
            community = _call(service, context, "community", {"community_id": int(community_id)})
        graph_artifact = _call(
            service,
            context,
            "visualize",
            {"format": "graph", "detail": "auto"},
        )
        tree_artifact = _call(service, context, "visualize", {"format": "tree"})

        save = _memory_call(
            service,
            context,
            {
                "action": "save",
                "idempotency_key": f"qualification-{prefix}-memory-01",
                "situation": "A deterministic fixture was refreshed.",
                "lesson": "Inspect production service output after a committed refresh.",
                "applicability": "Knowledge expansion qualification.",
                "outcome": "useful",
                "evidence": [],
            },
        )
        note_id = str(save["note_id"])
        search = _memory_call(
            service, context, {"action": "search", "query": "production service", "limit": 5}
        )
        search_matches = [m for m in search.get("matches", []) if isinstance(m, dict)]
        if not any(str(item.get("note_id")) == note_id for item in search_matches):
            raise RuntimeError(
                f"saved note {note_id} not found in work_memory search matches: {search_matches}"
            )
        read = _memory_call(service, context, {"action": "read", "note_id": note_id})
        corrected = _memory_call(
            service,
            context,
            {
                "action": "correct",
                "note_id": note_id,
                "expected_revision": int(read["revision"]),
                "reason": "Record the qualification boundary precisely.",
                "replacement": {
                    "lesson": "Inspect production service output after a committed refresh.",
                    "applicability": "This deterministic knowledge expansion qualification.",
                },
                "evidence": [],
            },
        )
        reflect = _memory_call(service, context, {"action": "reflect"})
        reports.append(
            {
                "project_id": project_id,
                "status_before_update": before.get("available"),
                "update_outcome": update.get("outcome"),
                "source_revision": context.source_revision,
                "query_options": query.get("query_options", {}),
                "resolved_node": resolved,
                "community_checked": community is not None,
                "action_checks": {
                    "query": bool(query.get("content")),
                    "explain": bool(explain.get("content")),
                    "neighbors": bool(neighbors.get("content")),
                    "impact": bool(impact.get("content")),
                    "path": bool(path.get("content")),
                    "stats": stats.get("stats", {}),
                    "god_nodes": len(gods.get("nodes", [])),
                    "visualize_graph": _artifact_summary(graph_artifact["artifact"]),
                    "visualize_tree": _artifact_summary(tree_artifact["artifact"]),
                },
                "memory_checks": {
                    "search_hits": len(search_matches),
                    "read_note_id": read.get("note_id"),
                    "corrected_revision": corrected.get("revision"),
                    "reflection_count": reflect.get("count"),
                },
            }
        )
    return {"fixtures": reports, "projects_isolated": len(reports) == 2}


def _run_offline(component_python: Path | None) -> dict[str, Any]:
    if component_python is None:
        return {"status": "skipped", "reason": "COMPONENT_UNAVAILABLE"}
    with tempfile.TemporaryDirectory(prefix="aether-knowledge-qualification-") as temporary:
        workspace = Path(temporary)
        state = workspace / "state"
        cache = workspace / "cache"
        registry = ProjectRegistry(state)
        contexts: list[tuple[str, Any]] = []
        for project_id, prefix in FIXTURE_PROJECTS:
            root = workspace / prefix
            _make_fixture(root, project_id, prefix)
            if not registry.register(project_id, root, f"{prefix} qualification fixture"):
                raise RuntimeError(f"could not register {prefix} fixture")
        service = KnowledgeService(state_root=state, cache_root=cache)
        try:
            configure(service, component_python, ownership="external", semantic_enabled=False)
            for project_id, _prefix in FIXTURE_PROJECTS:
                contexts.append(
                    (
                        project_id,
                        resolve_context(project_id, "implementer", state_root=state),
                    )
                )
            return {"status": "passed", **_fixture_report(service, contexts)}
        except KnowledgeError as exc:
            if exc.code == "COMPONENT_UNAVAILABLE":
                return {"status": "skipped", "reason": exc.code}
            raise


def _run_live_auxiliary(component_python: Path | None) -> dict[str, Any]:
    if component_python is None:
        return {"status": "skipped", "reason": "COMPONENT_UNAVAILABLE"}
    with tempfile.TemporaryDirectory(prefix="aether-knowledge-live-") as temporary:
        workspace = Path(temporary)
        state = workspace / "state"
        cache = workspace / "cache"
        registry = ProjectRegistry(state)
        contexts: list[tuple[str, Any]] = []
        for project_id, prefix in FIXTURE_PROJECTS:
            root = workspace / prefix
            _make_fixture(root, project_id, prefix)
            if not registry.register(project_id, root, f"{prefix} live fixture"):
                raise RuntimeError(f"could not register {prefix} live fixture")
        service = KnowledgeService(state_root=state, cache_root=cache)
        try:
            configure(
                service,
                component_python,
                ownership="external",
                semantic_enabled=True,
                semantic_auxiliary_task="web_extract",
            )
        except KnowledgeError as exc:
            if exc.code == "COMPONENT_UNAVAILABLE":
                return {"status": "skipped", "reason": exc.code}
            raise
        for project_id, _prefix in FIXTURE_PROJECTS:
            contexts.append(
                (
                    project_id,
                    resolve_context(project_id, "implementer", state_root=state),
                )
            )
        semantic_reports = []
        for project_id, context in contexts:
            result = _call(
                service,
                context,
                "update",
                {"reason": "Live auxiliary qualification", "mode": "configured"},
            )
            semantic = result.get("semantic", {})
            usage = semantic.get("observed_usage", {})
            if semantic.get("state") != "complete":
                return {
                    "status": "skipped",
                    "reason": "AUXILIARY_UNAVAILABLE",
                    "state": semantic.get("state"),
                }
            total_tokens = usage.get("total_tokens", 0)
            if not isinstance(total_tokens, (int, float)) or total_tokens <= 0:
                raise RuntimeError("live auxiliary completed without nonempty usage evidence")
            prefix = "alpha" if project_id == FIXTURE_PROJECTS[0][0] else "beta"
            foreign = "beta" if prefix == "alpha" else "alpha"
            covered_paths = {str(path) for path in semantic.get("covered_paths", [])}
            if not {"README.md", "workflow.py"}.issubset(covered_paths):
                raise RuntimeError("live auxiliary did not cover both fixture document and code")
            query = _call(
                service,
                context,
                "query",
                {"question": f"{prefix}_process", "traversal": "bfs", "depth": 2},
            )
            query_content = str(query.get("content", ""))
            if prefix not in query_content or foreign in query_content:
                raise RuntimeError("live semantic result crossed the fixture project boundary")
            semantic_reports.append(
                {
                    "project_id": project_id,
                    "state": semantic.get("state"),
                    "covered_paths": sorted(covered_paths),
                    "usage_tokens_observed": True,
                    "source_code_query_checked": True,
                    "coverage": result.get("coverage", {}),
                }
            )
        return {"status": "passed", "projects": semantic_reports}


def _run_github(project_id: str | None, pr_number: int | None) -> dict[str, Any]:
    if not project_id:
        return {"status": "skipped", "reason": "PROJECT_ID_REQUIRED"}
    service = KnowledgeService()
    try:
        context = resolve_context(project_id, "supervisor", state_root=service.state_root)
        listed = service.execute(
            context,
            "project_knowledge",
            {"action": "list_prs", "limit": 5},
        )
        triaged = service.execute(
            context,
            "project_knowledge",
            {"action": "triage_prs", "limit": 5},
        )
        if listed.get("ok") is not True or triaged.get("ok") is not True:
            raise KnowledgeError(
                "GITHUB_UNAVAILABLE", "Read-only GitHub qualification returned an error."
            )
        report: dict[str, Any] = {
            "status": "passed",
            "listed": len(listed.get("prs", [])),
            "triaged": len(triaged.get("prs", [])),
        }
        if pr_number is None:
            report["pr_impact"] = {"status": "skipped", "reason": "PR_NUMBER_NOT_SUPPLIED"}
        else:
            impact = service.execute(
                context,
                "project_knowledge",
                {"action": "pr_impact", "pr_number": pr_number},
            )
            if impact.get("ok") is not True:
                raise KnowledgeError("GITHUB_UNAVAILABLE", "Read-only PR impact returned an error.")
            impact_info = impact.get("impact") or {}
            files_value = impact_info.get("files", 0)
            files_count = (
                len(files_value) if isinstance(files_value, list) else int(files_value or 0)
            )
            matched = impact_info.get("matched_files") or []
            unmatched = impact_info.get("unmatched_files") or []
            report["pr_impact"] = {
                "status": "passed",
                "files": files_count,
                "matched_files": len(matched) if isinstance(matched, list) else matched,
                "unmatched_files": len(unmatched) if isinstance(unmatched, list) else unmatched,
            }
        return report
    except KnowledgeError as exc:
        if exc.code in UNAVAILABLE_CODES:
            return {"status": "skipped", "reason": exc.code}
        raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-auxiliary",
        action="store_true",
        help="Use the configured auxiliary and optional read-only GitHub checks.",
    )
    parser.add_argument(
        "--project-id",
        help="Existing registered project UUID for optional read-only GitHub checks.",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="Existing read-only pull request number for optional impact analysis.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit one machine-readable JSON report."
    )
    arguments = parser.parse_args()
    if arguments.pr_number is not None and arguments.pr_number < 1:
        parser.error("--pr-number must be positive")
    return arguments


def _plain_report(report: dict[str, Any]) -> str:
    lines = [f"knowledge expansion qualification: {report['status']}"]
    catalog = report.get("catalog", {})
    if catalog:
        lines.append(
            f"catalog: {catalog.get('project_actions')} project actions, "
            f"{catalog.get('memory_actions')} memory actions"
        )
    offline = report.get("offline", {})
    lines.append(f"offline: {offline.get('status', 'not-run')}")
    live = report.get("live")
    if live is not None:
        lines.append(f"live auxiliary: {live.get('auxiliary', {}).get('status', 'not-run')}")
        lines.append(f"live GitHub: {live.get('github', {}).get('status', 'not-run')}")
    for skip in report.get("skips", []):
        lines.append(f"skip: {skip}")
    return "\n".join(lines)


def main() -> int:
    arguments = _parse_args()
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "failed",
        "mode": "live" if arguments.live_auxiliary else "offline",
    }
    try:
        report["catalog"] = _validate_catalog()
        component_python, component_report = _active_component()
        report["component"] = component_report
        report["offline"] = _run_offline(component_python)
        if report["offline"].get("status") == "failed":
            raise RuntimeError("offline qualification failed")
        if report["offline"].get("status") == "skipped":
            report.setdefault("skips", []).append(
                f"offline:{report['offline'].get('reason', 'unavailable')}"
            )
        if arguments.live_auxiliary:
            auxiliary = _run_live_auxiliary(component_python)
            github = _run_github(arguments.project_id, arguments.pr_number)
            report["live"] = {"auxiliary": auxiliary, "github": github}
            if auxiliary.get("status") == "skipped":
                report.setdefault("skips", []).append(
                    f"auxiliary:{auxiliary.get('reason', 'unavailable')}"
                )
            if github.get("status") == "skipped":
                report.setdefault("skips", []).append(
                    f"github:{github.get('reason', 'unavailable')}"
                )
        report["status"] = "passed_with_skips" if report.get("skips") else "passed"
    except (KnowledgeError, RuntimeError, OSError, ValueError) as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["status"] = "failed"
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output if arguments.json else _plain_report(report))
    return 0 if report["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
