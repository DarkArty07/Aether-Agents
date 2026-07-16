#!/usr/bin/env python3
"""Score deterministic assertions from Daimon benchmark result evidence."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PHASES = ("baseline", "post")
TEXT_TYPES = {
    "response_contains_all",
    "response_contains_any",
    "response_contains_groups",
    "response_not_contains",
}
TRACE_TYPES = {"trace_contains", "function_invocation_required"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def response_text(result: dict[str, Any]) -> str:
    return str(result.get("stdout", ""))


def contains(text: str, value: str) -> bool:
    return value.casefold() in text.casefold()


def trace_text(result: dict[str, Any]) -> str | None:
    trace = result.get("trace")
    if trace is None:
        return None
    if isinstance(trace, str):
        return trace
    if isinstance(trace, list):
        return "\n".join(json.dumps(item, sort_keys=True, ensure_ascii=False) for item in trace)
    return None


def evaluate_assertion(assertion: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Return PASS/FAIL/INSUFFICIENT only from retained result evidence."""
    assertion_type = assertion.get("type")
    value = assertion.get("value")
    if assertion_type in TEXT_TYPES:
        text = response_text(result)
        if not text:
            return {"status": "INSUFFICIENT", "reason": "captured stdout is empty"}
        if assertion_type == "response_contains_all":
            expected = value if isinstance(value, list) else [value]
            missing = [item for item in expected if not isinstance(item, str) or not contains(text, item)]
            return {"status": "PASS" if not missing else "FAIL", "reason": "all response terms present" if not missing else f"missing response terms: {missing}"}
        if assertion_type == "response_contains_any":
            expected = value if isinstance(value, list) else [value]
            matched = [item for item in expected if isinstance(item, str) and contains(text, item)]
            return {"status": "PASS" if matched else "FAIL", "reason": f"matched response terms: {matched}" if matched else f"none of response terms found: {expected}"}
        if assertion_type == "response_contains_groups":
            if not isinstance(value, list) or not all(isinstance(group, list) for group in value):
                return {"status": "INSUFFICIENT", "reason": "contains_groups assertion has invalid value"}
            matched_groups = []
            missing_groups = []
            for group in value:
                matched = [item for item in group if isinstance(item, str) and contains(text, item)]
                if matched:
                    matched_groups.append(matched)
                else:
                    missing_groups.append(group)
            return {
                "status": "PASS" if not missing_groups else "FAIL",
                "reason": (
                    f"matched one response term per group: {matched_groups}"
                    if not missing_groups
                    else f"no response term matched groups: {missing_groups}"
                ),
            }
        if not isinstance(value, str):
            return {"status": "INSUFFICIENT", "reason": "not_contains assertion has invalid value"}
        return {"status": "FAIL" if contains(text, value) else "PASS", "reason": f"forbidden response term present: {value}" if contains(text, value) else "forbidden response term absent"}
    if assertion_type in TRACE_TYPES:
        trace = trace_text(result)
        if trace is None:
            return {"status": "INSUFFICIENT", "reason": "no captured tool/function trace"}
        terms = str(value).split("|")
        matched = [term for term in terms if contains(trace, term)]
        return {"status": "PASS" if matched else "FAIL", "reason": f"matched trace terms: {matched}" if matched else f"trace lacks: {terms}"}
    if assertion_type == "artifact_required":
        artifacts = result.get("artifact_evidence")
        if not isinstance(artifacts, dict):
            return {"status": "INSUFFICIENT", "reason": "no captured artifact evidence"}
        target = str(value).lstrip("/")
        evidence = artifacts.get(target)
        if not isinstance(evidence, dict):
            return {"status": "FAIL", "reason": f"artifact evidence lacks target: {target}"}
        content = evidence.get("content")
        if evidence.get("exists") is True and isinstance(content, str) and content.strip():
            return {"status": "PASS", "reason": f"captured non-empty artifact: {target}"}
        return {"status": "FAIL", "reason": f"artifact not confirmed non-empty: {target}"}
    return {"status": "INSUFFICIENT", "reason": f"unsupported assertion type: {assertion_type}"}


def score(cases: list[dict[str, Any]], results_dir: Path) -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    missing: list[str] = []
    for case in cases:
        path = results_dir / f"{case['id']}.json"
        if not path.is_file():
            missing.append(case["id"])
            continue
        try:
            result = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            missing.append(case["id"])
            outcomes.append({"case_id": case["id"], "agent": case["agent"], "result_error": str(exc), "assertions": []})
            continue
        assertion_outcomes = []
        for assertion in case["deterministic_assertions"]:
            scored = evaluate_assertion(assertion, result)
            assertion_outcomes.append({"id": assertion["id"], "type": assertion["type"], **scored})
        outcomes.append({"case_id": case["id"], "agent": case["agent"], "result_path": str(path), "run_status": result.get("status"), "assertions": assertion_outcomes})
    counts = Counter(item["status"] for outcome in outcomes for item in outcome["assertions"])
    by_agent: dict[str, dict[str, int]] = defaultdict(lambda: {"PASS": 0, "FAIL": 0, "INSUFFICIENT": 0})
    by_case: dict[str, dict[str, int]] = {}
    hard_failures: list[dict[str, str]] = []
    for outcome in outcomes:
        case_counts = Counter(item["status"] for item in outcome["assertions"])
        by_case[outcome["case_id"]] = dict(case_counts)
        for item in outcome["assertions"]:
            by_agent[outcome["agent"]][item["status"]] += 1
            if item["status"] == "FAIL":
                hard_failures.append({"case_id": outcome["case_id"], "assertion_id": item["id"], "reason": item["reason"]})
    return {
        "schema_version": 1, "missing_results": missing, "counts": dict(counts),
        "by_agent": dict(by_agent), "by_case": by_case, "hard_gate_failures": hard_failures,
        "cases": outcomes,
    }


def render_markdown(summary: dict[str, Any], phase: str) -> str:
    lines = [f"# Daimon Reliability Benchmark — {phase}", "", "## Summary", "", "| Status | Count |", "|---|---:|"]
    for status in ("PASS", "FAIL", "INSUFFICIENT"):
        lines.append(f"| {status} | {summary['counts'].get(status, 0)} |")
    lines.extend(["", f"Missing required results: {len(summary['missing_results'])}", f"Hard gate failures: {len(summary['hard_gate_failures'])}", "", "## By agent", "", "| Agent | PASS | FAIL | INSUFFICIENT |", "|---|---:|---:|---:|"])
    for agent in sorted(summary["by_agent"]):
        data = summary["by_agent"][agent]
        lines.append(f"| {agent} | {data.get('PASS', 0)} | {data.get('FAIL', 0)} | {data.get('INSUFFICIENT', 0)} |")
    lines.extend(["", "## By case", "", "| Case | PASS | FAIL | INSUFFICIENT |", "|---|---:|---:|---:|"])
    for case_id in sorted(summary["by_case"]):
        data = summary["by_case"][case_id]
        lines.append(f"| {case_id} | {data.get('PASS', 0)} | {data.get('FAIL', 0)} | {data.get('INSUFFICIENT', 0)} |")
    if summary["missing_results"]:
        lines.extend(["", "## Missing required results", "", *[f"- {case_id}" for case_id in summary["missing_results"]]])
    if summary["hard_gate_failures"]:
        lines.extend(["", "## Hard gate failures", "", *[f"- {item['case_id']} / {item['assertion_id']}: {item['reason']}" for item in summary["hard_gate_failures"]]])
    return "\n".join(lines) + "\n"


def write_outputs(directory: Path, summary: dict[str, Any], phase: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (directory / "SUMMARY.md").write_text(render_markdown(summary, phase), encoding="utf-8")


def self_test() -> int:
    text_result = {"stdout": "one two", "trace": None}
    assert evaluate_assertion({"type": "response_contains_all", "value": ["one", "two"]}, text_result)["status"] == "PASS"
    assert evaluate_assertion({"type": "response_contains_any", "value": ["zero", "two"]}, text_result)["status"] == "PASS"
    assert evaluate_assertion({"type": "response_contains_groups", "value": [["zero", "one"], ["two", "three"]]}, text_result)["status"] == "PASS"
    assert evaluate_assertion({"type": "response_contains_groups", "value": [["one"], ["zero"]]}, text_result)["status"] == "FAIL"
    assert evaluate_assertion({"type": "response_not_contains", "value": "zero"}, text_result)["status"] == "PASS"
    assert evaluate_assertion({"type": "trace_contains", "value": "pytest"}, text_result)["status"] == "INSUFFICIENT"
    traced = {"stdout": "ok", "trace": [{"tool": "write_file", "success": True}], "artifact_evidence": {".aether/CONTEXT.md": {"exists": True, "content": "contenido"}}}
    assert evaluate_assertion({"type": "trace_contains", "value": "write_file"}, traced)["status"] == "PASS"
    assert evaluate_assertion({"type": "function_invocation_required", "value": "write_file|patch"}, traced)["status"] == "PASS"
    assert evaluate_assertion({"type": "artifact_required", "value": ".aether/CONTEXT.md"}, traced)["status"] == "PASS"
    assert evaluate_assertion({"type": "artifact_required", "value": "missing.txt"}, traced)["status"] == "FAIL"
    print("PASS: scorer self-test (text, trace, function, artifact assertion types)")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=False, choices=PHASES)
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    if not args.phase:
        raise SystemExit("--phase is required unless --self-test is used")
    data = load_json(HERE / "cases.json")
    summary = score(data["cases"], HERE / "results" / args.phase)
    write_outputs(HERE / "results" / args.phase, summary, args.phase)
    if summary["hard_gate_failures"]:
        return 1
    if summary["missing_results"] and not args.allow_incomplete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
