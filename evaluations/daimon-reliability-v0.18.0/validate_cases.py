#!/usr/bin/env python3
"""Validate the static v0.18.0 Daimon reliability benchmark case contract."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "cases.json"
REQUIRED_AGENTS = ("etalides", "athena", "ariadna", "ictinus", "daedalus", "hefesto")
REQUIRED_CASE_KEYS = {
    "id", "agent", "case_type", "prompt", "safety", "expected_behaviors",
    "forbidden_behaviors", "deterministic_assertions", "manual_rubric", "evidence_requirements",
}
VALID_TYPES = {"positive", "boundary_ambiguity", "failure_calibration", "justified_blocker", "mitigated_non_blocker", "optional_hardening", "operational_issue"}

def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)

def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())

def main() -> None:
    try:
        data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {CASES_PATH}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        fail("root must be an object with a cases array")
    cases = data["cases"]
    if len(cases) < 18:
        fail(f"expected at least 18 cases; found {len(cases)}")
    ids = set()
    counts: Counter[str] = Counter()
    types_by_agent: dict[str, set[str]] = {agent: set() for agent in REQUIRED_AGENTS}
    for index, item in enumerate(cases, start=1):
        if not isinstance(item, dict):
            fail(f"case {index} must be an object")
        missing = REQUIRED_CASE_KEYS - item.keys()
        if missing:
            fail(f"case {index} missing keys: {', '.join(sorted(missing))}")
        if not nonempty_string(item["id"]) or item["id"] in ids:
            fail(f"case {index} has missing or duplicate id")
        ids.add(item["id"])
        agent = item["agent"]
        if agent not in REQUIRED_AGENTS:
            fail(f"case {item['id']} has unknown agent {agent!r}")
        counts[agent] += 1
        if item["case_type"] not in VALID_TYPES:
            fail(f"case {item['id']} has invalid case_type")
        types_by_agent[agent].add(item["case_type"])
        if not nonempty_string(item["prompt"]):
            fail(f"case {item['id']} has no prompt")
        for key in ("expected_behaviors", "forbidden_behaviors", "deterministic_assertions", "evidence_requirements"):
            if not isinstance(item[key], list) or not item[key]:
                fail(f"case {item['id']} requires a non-empty {key} list")
        if not isinstance(item["safety"], dict) or item["safety"].get("mode") != "synthetic_or_read_only":
            fail(f"case {item['id']} must declare synthetic_or_read_only safety")
        rubric = item["manual_rubric"]
        if not isinstance(rubric, dict) or not nonempty_string(rubric.get("pass")) or not nonempty_string(rubric.get("fail")):
            fail(f"case {item['id']} needs explicit manual pass and fail rubric")
        for assertion in item["deterministic_assertions"]:
            if not isinstance(assertion, dict) or not all(nonempty_string(assertion.get(k)) for k in ("id", "type", "pass_when")):
                fail(f"case {item['id']} has an incomplete deterministic assertion")
    coverage_map = {
        "positive": "positive",
        "mitigated_non_blocker": "positive",
        "boundary_ambiguity": "boundary_ambiguity",
        "optional_hardening": "boundary_ambiguity",
        "failure_calibration": "failure_calibration",
        "justified_blocker": "failure_calibration",
        "operational_issue": "failure_calibration",
    }
    for agent in REQUIRED_AGENTS:
        if counts[agent] < 3:
            fail(f"{agent} requires at least 3 cases; found {counts[agent]}")
        coverage = {coverage_map[case_type] for case_type in types_by_agent[agent]}
        if not {"positive", "boundary_ambiguity", "failure_calibration"} <= coverage:
            fail(f"{agent} must have positive, boundary/ambiguity, and failure/calibration coverage")
    if counts["athena"] < 4:
        fail(f"athena requires at least 4 cases; found {counts['athena']}")
    athena_types = types_by_agent["athena"]
    for required in ("justified_blocker", "mitigated_non_blocker", "optional_hardening", "operational_issue"):
        if required not in athena_types:
            fail(f"athena missing required {required} case")
    print(f"PASS: {len(cases)} cases validated")
    print("Case counts by agent:")
    for agent in REQUIRED_AGENTS:
        print(f"- {agent}: {counts[agent]}")
    print("Athena required gate cases: 4/4")

if __name__ == "__main__":
    main()
