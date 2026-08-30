"""``aether observe`` command implementation.

Normative source: ``specs/002-aether-contract-observation/spec.md`` section 13.1 and
OBS-FR-067..070; the stable JSON envelope and exit codes are
``specs/001-aether-v1-productization/contracts/cli.md`` sections 3-4. The command is
read-only: it never mutates Kanban, SessionDB, canonical artifacts, or observation
state, and it makes no network or model call (OBS-FR-025/028).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, TextIO

from aether_agents.observation import query, report
from aether_agents.observation.contracts import canonical_json_str, validate_summary
from aether_agents.paths import ObservationPaths
from aether_agents.result import Envelope

__all__ = ["build_subparser", "run_observe"]

#: cli.md section 3: results that print to stdout in human mode; everything else (an
#: error/blocked/unsupported result) prints to stderr instead (section 1's general rule).
_STDOUT_RESULTS = ("ready", "changed", "no_change", "planned")


def _empty_state_report(data: dict[str, Any]) -> str:
    """Render the human projection of the canonical empty-state representation."""
    if data != {"state": "empty", "summary": None}:
        raise ValueError("invalid observation empty-state representation")
    return "No observed contract trace for this project yet."


def build_subparser(subparsers: "argparse._SubParsersAction") -> argparse.ArgumentParser:
    """Register ``observe`` on a top-level ``argparse`` subparsers action."""
    parser = subparsers.add_parser(
        "observe",
        help="Read-only causal review brief for one contract trace.",
        description="aether observe [REF] [--project PATH] [--since SUMMARY_ID] [--watch] [--json]",
    )
    parser.add_argument("ref", nargs="?", default=None, metavar="REF")
    parser.add_argument("--project", metavar="PATH", default=None)
    parser.add_argument("--since", metavar="SUMMARY_ID", default=None)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def _emit(
    envelope: Envelope, *, json_mode: bool, human: str, stdout: TextIO, stderr: TextIO
) -> int:
    if json_mode:
        # cli.md section 1: "--json emits exactly one UTF-8 JSON object to stdout and no
        # decorative output" — always stdout, regardless of the result value.
        print(canonical_json_str(envelope.to_json()), file=stdout)
        return envelope.exit_code
    target = stdout if envelope.result in _STDOUT_RESULTS else stderr
    print(human, file=target)
    return envelope.exit_code


def _fail(
    envelope: Envelope, *, result: str, failure_kind: str, code: str, message: str, **details: Any
) -> None:
    envelope.result = result  # type: ignore[assignment]
    envelope.failure_kind = failure_kind
    envelope.fail(code, message, **details)


def run_observe(
    args: argparse.Namespace,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Execute ``aether observe`` and return its documented process exit code."""
    envelope = Envelope(command="observe", result="ready")

    if args.watch and args.json:
        _fail(
            envelope,
            result="error",
            failure_kind="invalid_input",
            code="WATCH_JSON_UNSUPPORTED",
            message="--watch cannot be combined with --json",
        )
        return _emit(
            envelope,
            json_mode=True,
            human="error: --watch cannot be combined with --json",
            stdout=stdout,
            stderr=stderr,
        )

    try:
        project = query.resolve_project(explicit=args.project)
    except query.ProjectResolutionError as exc:
        _fail(
            envelope,
            result="error",
            failure_kind="missing_prerequisite",
            code="PROJECT_UNRESOLVED",
            message=str(exc),
        )
        return _emit(
            envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
        )

    paths = ObservationPaths.for_project(project.project_id)

    try:
        trace_id = query.resolve_trace(paths, args.ref)
    except query.NoOpenTraceError:
        if args.ref is not None:
            message = "no trace matches the given REF"
            _fail(
                envelope,
                result="error",
                failure_kind="invalid_input",
                code="TRACE_NOT_FOUND",
                message=message,
            )
            return _emit(
                envelope,
                json_mode=args.json,
                human=f"error: {message}",
                stdout=stdout,
                stderr=stderr,
            )
        envelope.data = {"state": "empty", "summary": None}
        human = _empty_state_report(envelope.data)
        return _emit(envelope, json_mode=args.json, human=human, stdout=stdout, stderr=stderr)
    except query.TraceAmbiguousError as exc:
        _fail(
            envelope,
            result="error",
            failure_kind="invalid_input",
            code="TRACE_AMBIGUOUS",
            message=str(exc),
            candidates=list(exc.candidates),
        )
        return _emit(
            envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
        )
    except query.TraceNotFoundError as exc:
        _fail(
            envelope,
            result="error",
            failure_kind="invalid_input",
            code="TRACE_NOT_FOUND",
            message=str(exc),
        )
        return _emit(
            envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
        )
    except query.StateUnreadableError as exc:
        _fail(
            envelope,
            result="error",
            failure_kind="runtime_failure",
            code="STATE_UNREADABLE",
            message=str(exc),
        )
        return _emit(
            envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
        )

    if args.watch:
        return _run_watch(paths, trace_id, json_mode=args.json, stdout=stdout, stderr=stderr)

    try:
        summary = query.load_summary(paths, trace_id)
    except query.StateUnreadableError as exc:
        _fail(
            envelope,
            result="error",
            failure_kind="runtime_failure",
            code="STATE_UNREADABLE",
            message=str(exc),
        )
        return _emit(
            envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
        )

    try:
        validate_summary(summary)
    except Exception:
        # jsonschema error text can echo payload values; never forward it verbatim
        # (section 8.3's "never quote the offending value" discipline).
        _fail(
            envelope,
            result="error",
            failure_kind="integrity_failure",
            code="SUMMARY_SCHEMA_INVALID",
            message="the produced summary does not conform to the normative schema",
        )
        return _emit(
            envelope,
            json_mode=args.json,
            human="error: produced summary failed schema validation",
            stdout=stdout,
            stderr=stderr,
        )

    previous: dict[str, Any] | None = None
    if args.since:
        try:
            previous = query.load_previous_summary(paths, args.since)
        except query.SummaryNotFoundError as exc:
            _fail(
                envelope,
                result="error",
                failure_kind="invalid_input",
                code="SINCE_SUMMARY_NOT_FOUND",
                message=str(exc),
            )
            return _emit(
                envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
            )
        except query.StateUnreadableError as exc:
            _fail(
                envelope,
                result="error",
                failure_kind="runtime_failure",
                code="STATE_UNREADABLE",
                message=str(exc),
            )
            return _emit(
                envelope, json_mode=args.json, human=f"error: {exc}", stdout=stdout, stderr=stderr
            )

        # OBS-FR-069: incompatible summary schemas return a bounded comparison error,
        # never a manufactured diff — the whole command fails rather than silently
        # showing an uncompared summary for an explicitly requested comparison.
        diff = report.diff_summaries(summary, previous)
        if not diff["comparable"]:
            _fail(
                envelope,
                result="error",
                failure_kind="integrity_failure",
                code="SINCE_COMPARISON_INCOMPATIBLE",
                message=diff["error"] or "incompatible summary schemas",
            )
            human = f"error: cannot compare against {args.since}: {diff['error']}"
            return _emit(envelope, json_mode=args.json, human=human, stdout=stdout, stderr=stderr)

        # Human and JSON projections must agree: overlay the review_brief facets the
        # schema itself carries (`since_summary_id`, `change_classes`) with this
        # explicit comparison before either projection renders (OBS-FR-067).
        summary["review_brief"]["since_summary_id"] = previous["summary_id"]
        summary["review_brief"]["change_classes"] = diff["change_classes"]
        from aether_agents.observation.identity import summary_id as make_summary_id

        # --since changes the deterministic review brief, so it also changes the
        # content-addressed identity of the returned summary projection.
        summary["summary_id"] = make_summary_id(summary)
        validate_summary(summary)

    envelope.data = {"state": "summary", "summary": summary}
    human = report.render_brief(summary, since=previous)
    return _emit(envelope, json_mode=args.json, human=human, stdout=stdout, stderr=stderr)


def _run_watch(
    paths: ObservationPaths,
    trace_id: str,
    *,
    json_mode: bool,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """``--watch``: stream a rendering each time OBS-FR-070's watched facets change."""
    try:
        for index, summary in enumerate(query.watch(paths, trace_id)):
            if json_mode:
                envelope = Envelope(
                    command="observe",
                    result="ready" if index == 0 else "changed",
                    data={"state": "summary", "summary": summary},
                )
                print(canonical_json_str(envelope.to_json()), file=stdout)
            else:
                print(report.render_brief(summary), file=stdout)
                print("---", file=stdout)
            stdout.flush()
    except KeyboardInterrupt:
        return 0
    except query.StateUnreadableError as exc:
        print(f"error: {exc}", file=stderr)
        return 6
    return 0
