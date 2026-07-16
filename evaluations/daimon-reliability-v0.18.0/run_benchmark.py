#!/usr/bin/env python3
"""Run isolated, reproducible Daimon reliability benchmark cases."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[1]
PHASES = ("baseline", "post")
AUTHORIZATION_PATTERN = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+")
ASSIGNMENT_PATTERN = re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s\"']+")
OPAQUE_SECRET_PATTERN = re.compile(r"(?i)\b(?:sk-[a-z0-9_-]{12,}|ghp_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|eyJ[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,})\b")


def redact(value: str) -> str:
    """Redact common credential forms without altering ordinary benchmark text."""
    result = AUTHORIZATION_PATTERN.sub(r"\1[REDACTED]", value)
    result = ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", result)
    return OPAQUE_SECRET_PATTERN.sub("[REDACTED]", result)


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("cases"), list):
        raise ValueError("cases.json must contain a cases array")
    return data["cases"]


def profile_metadata(profile: Path) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {"model": None, "provider": None}
    config = profile / "config.yaml"
    if not config.is_file():
        return metadata
    text = config.read_text(encoding="utf-8", errors="replace")
    model = re.search(r"^\s*default:\s*([^\s#]+)", text, re.MULTILINE)
    provider = re.search(r"^\s*provider:\s*([^\s#]+)", text, re.MULTILINE)
    metadata["model"] = model.group(1) if model else None
    metadata["provider"] = provider.group(1) if provider else None
    return metadata


def build_prompt(case: dict[str, Any], fixture_text: str, workdir: Path) -> str:
    return "\n".join((
        f"PROJECT_ROOT: {workdir}",
        "", "CONTEXT:",
        "You are executing one isolated Daimon reliability benchmark case.",
        "The project root is a disposable copy of a synthetic fixture, not the production repository.",
        "Fixture material follows verbatim:", fixture_text.rstrip(),
        "", "TASK:", case["prompt"],
        "", "CONSTRAINTS:",
        "Use only the disposable PROJECT_ROOT and supplied fixture material.",
        "Do not access the network, credentials, production files, or any path outside PROJECT_ROOT.",
        "Do not reuse or assume another benchmark case/session.",
        "Preserve uncertainty: do not claim actions or artifacts without evidence.",
        "", "OUTPUT FORMAT:",
        "Return the complete final response required by the task. Include concrete evidence and limitations.",
    )) + "\n"


def plan_case(case: dict[str, Any], project_root: Path, fixtures_root: Path) -> dict[str, Any]:
    fixture_rel = case.get("fixture", f"fixtures/{case['id']}/fixture.md")
    fixture = (HERE / fixture_rel).resolve()
    profile = project_root / "home" / "profiles" / case["agent"]
    if not fixture.is_file():
        raise ValueError(f"{case['id']}: fixture does not exist: {fixture}")
    if not profile.is_dir():
        raise ValueError(f"{case['id']}: profile does not exist: {profile}")
    fixture_text = fixture.read_text(encoding="utf-8")
    return {
        "case_id": case["id"], "agent": case["agent"], "profile": profile,
        "fixture": fixture.parent, "fixture_file": fixture,
        "prompt": build_prompt(case, fixture_text, Path("<disposable-workdir>")),
        "metadata": profile_metadata(profile),
    }


def snapshot_artifacts(workdir: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for path in workdir.rglob("*"):
        if path.is_file() and path.relative_to(workdir).as_posix() != "fixture.md":
            relative = path.relative_to(workdir).as_posix()
            content = path.read_text(encoding="utf-8", errors="replace")
            artifacts[relative] = {"exists": True, "content": redact(content)[:20000]}
    return artifacts


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def execute_case(case: dict[str, Any], phase: str, timeout: int, project_root: Path, dry_run: bool) -> dict[str, Any]:
    plan = plan_case(case, project_root, HERE / "fixtures")
    work_parent = Path(tempfile.gettempdir()) / "aether-daimon-reliability" / phase
    work_parent.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix=f"{case['id'].lower()}-", dir=work_parent))
    shutil.copytree(plan["fixture"], workdir, dirs_exist_ok=True)
    prompt = build_prompt(case, (workdir / "fixture.md").read_text(encoding="utf-8"), workdir)
    record: dict[str, Any] = {
        "schema_version": 1, "case_id": case["id"], "agent": case["agent"], "phase": phase,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "profile": str(plan["profile"]),
        "model": plan["metadata"]["model"], "provider": plan["metadata"]["provider"],
        "fixture_template": str(plan["fixture"]), "workdir": str(workdir), "prompt": redact(prompt),
        "command": ["hermes", "-z", "<prompt>"], "trace": None,
        "stdout": "", "stderr": "", "return_code": None, "elapsed_seconds": 0.0,
        "timed_out": False, "artifact_evidence": {},
    }
    if dry_run:
        record["status"] = "DRY_RUN"
        record["artifact_evidence"] = snapshot_artifacts(workdir)
        return record
    environment = os.environ.copy()
    environment["HERMES_HOME"] = str(plan["profile"])
    started = time.monotonic()
    try:
        completed = subprocess.run(
            ["hermes", "-z", prompt], cwd=workdir, env=environment, text=True,
            capture_output=True, timeout=timeout, check=False,
        )
        record["stdout"] = redact(completed.stdout)
        record["stderr"] = redact(completed.stderr)
        record["return_code"] = completed.returncode
        record["status"] = "COMPLETED" if completed.returncode == 0 else "FAILED"
    except subprocess.TimeoutExpired as exc:
        record["stdout"] = redact((exc.stdout or "") if isinstance(exc.stdout, str) else "")
        record["stderr"] = redact((exc.stderr or "") if isinstance(exc.stderr, str) else "")
        record["timed_out"] = True
        record["status"] = "TIMEOUT"
    except OSError as exc:
        record["stderr"] = redact(str(exc))
        record["status"] = "FAILED_TO_START"
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        record["artifact_evidence"] = snapshot_artifacts(workdir)
    return record


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=False, choices=PHASES)
    parser.add_argument("--agent", choices=("etalides", "athena", "ariadna", "ictinus", "daedalus", "hefesto"))
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def self_test() -> int:
    cases = load_cases(HERE / "cases.json")
    plans = [plan_case(case, DEFAULT_ROOT, HERE / "fixtures") for case in cases]
    assert len(plans) == 19
    assert all("PROJECT_ROOT:" in plan["prompt"] for plan in plans)
    assert all(plan["profile"].is_dir() and plan["fixture"].is_dir() for plan in plans)
    assert "[REDACTED]" in redact("token=not-a-real-secret-value")
    print("PASS: runner self-test (19 fixture/profile/prompt plans; redaction)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    if not args.phase:
        raise SystemExit("--phase is required unless --self-test is used")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    cases = load_cases(HERE / "cases.json")
    selected = [case for case in cases if (not args.agent or case["agent"] == args.agent) and (not args.case_id or case["id"] == args.case_id)]
    if not selected:
        raise SystemExit("no cases matched --agent/--case")
    results_dir = HERE / "results" / args.phase
    for case in selected:
        result_path = results_dir / f"{case['id']}.json"
        if args.resume and result_path.is_file():
            print(f"SKIP {case['id']}: existing result")
            continue
        record = execute_case(case, args.phase, args.timeout, DEFAULT_ROOT, args.dry_run)
        write_json(result_path, record)
        print(f"{record['status']} {case['id']} -> {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
