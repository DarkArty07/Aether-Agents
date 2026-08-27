#!/usr/bin/env python3
"""Run and score Aether's disposable E2E canary/matrix without adding a service.

Suites:
- canary: 01, 03, 07, 08, 11
- full: 01..15 once
- reliability: full matrix plus the five canaries again (20 runs total)

Only live PASS/FAIL results enter the rolling reliability score. Prepare-only runs
validate fixtures/harness construction but never count as agent reliability evidence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from .observation import prepare_observation_only
from .resources import source_root
from .validation import validate_evidence

HERE = Path(__file__).resolve().parent
ROOT = source_root()
RUNNER_MODULE = "aether_agents.lab.runner"

CANARY = (1, 3, 7, 8, 11)
FULL = tuple(range(1, 16))
SUITES = {
    "canary": CANARY,
    "full": FULL,
    "reliability": FULL + CANARY,
    "observation": (),
}
SERIAL_SCENARIOS = frozenset({15})


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def _read_history(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def score_history(records: list[dict[str, Any]]) -> dict[str, Any]:
    live = [record for record in records if str(record.get("mode", "")).startswith("live")]
    window = live[-20:]
    last_ten = live[-10:]
    passes = sum(record.get("status") == "PASS" for record in window)
    required_routes = {"direct", "pipeline", "safety", "recovery"}
    observed_routes = {str(record.get("expected_route")) for record in window}
    gate = {
        "live_run_count": len(live),
        "window_size": len(window),
        "window_passes": passes,
        "last_ten_consecutive": len(last_ten) == 10
        and all(record.get("status") == "PASS" for record in last_ten),
        "zero_guard_manual_recovery": len(window) == 20
        and all(record.get("guard_caused_manual_recovery") is False for record in window),
        "zero_observed_protected_edge_violations": len(window) == 20
        and all(record.get("observed_protected_edge_violation") is False for record in window),
        "zero_aether_self_modification": len(window) == 20
        and all(record.get("aether_self_modification") is False for record in window),
        "representative_routes_present": required_routes <= observed_routes,
    }
    gate["passed"] = (
        len(window) == 20
        and passes >= 19
        and gate["last_ten_consecutive"]
        and gate["zero_guard_manual_recovery"]
        and gate["zero_observed_protected_edge_violations"]
        and gate["zero_aether_self_modification"]
        and gate["representative_routes_present"]
    )
    return gate


def _suite_root(base: Path | None, suite: str) -> Path:
    if base is not None:
        root = base.expanduser().resolve()
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        root = ROOT / ".aether" / "e2e-matrix" / f"{suite}-{stamp}-{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=tuple(SUITES), default="canary")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--matrix-root", type=Path, default=None)
    parser.add_argument(
        "--history",
        type=Path,
        default=ROOT / ".aether" / "e2e-history.jsonl",
        help="Append-only summary history; ignored by Git under .aether/",
    )
    parser.add_argument("--hermes", type=Path, default=None)
    parser.add_argument("--profile-root", type=Path, default=None)
    parser.add_argument("--allow-model-spend", action="store_true")
    parser.add_argument("--stop-on-failure", action="store_true")
    parser.add_argument(
        "--parallel",
        type=int,
        default=2,
        help="Concurrent independent roots (hard maximum: 2; persistent lanes stay serial)",
    )
    return parser


def _compact_result(payload: dict[str, Any], *, number: int, suite: str) -> dict[str, Any]:
    """Drop paths, IDs, and all non-contract fields from one matrix row."""
    allowed = {
        "scenario", "status", "mode", "expected_route", "observed_route", "route_ok",
        "acceptance_passed", "baseline_acceptance_passed", "owner_interventions",
        "expected_owner_interventions", "owner_interventions_ok", "harness_continuations",
        "guard_denials_ok", "observed_protected_edge_violation", "aether_self_modification",
        "fault_recovered", "missing_required_paths", "present_forbidden_paths", "board_task_count",
        "board_settled", "board_successful", "persistent_autonomous_wake_qualified",
        "rolling_reliability_counted",
    }
    result = {key: payload[key] for key in allowed if key in payload}
    result.setdefault("scenario", f"e2e-{number:02d}")
    result.setdefault("status", "FAIL")
    result.setdefault("mode", "prepare-only")
    result.setdefault("expected_route", "direct")
    result.update({"suite": suite, "isolation_verified": True})
    return result


def _run_scenario(
    number: int,
    *,
    index: int,
    suite: str,
    matrix_root: Path,
    prepare: bool,
    hermes: Path | None,
    profile_root: Path | None,
) -> dict[str, Any]:
    run_root = matrix_root / f"{index:02d}-e2e-{number:02d}"
    command = [sys.executable, "-m", RUNNER_MODULE, f"e2e-{number:02d}", "--run-root", str(run_root)]
    if prepare:
        command.append("--prepare-only")
    else:
        command.extend(
            [
                "--live",
                "--hermes",
                str(hermes),
                "--profile-root",
                str(profile_root),
                "--allow-model-spend",
            ]
        )
    child_env = dict(os.environ)
    source_path = ROOT / "src"
    if source_path.is_dir():
        prior_path = child_env.get("PYTHONPATH")
        child_env["PYTHONPATH"] = (
            str(source_path) if not prior_path else f"{source_path}{os.pathsep}{prior_path}"
        )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=child_env,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    summary = _compact_result(payload, number=number, suite=suite)
    if completed.returncode not in {0, 1}:
        summary["status"] = "FAIL"
        summary["reason"] = "runner_failed"
    summary["matrix_index"] = index
    summary["parallel"] = 1
    summary["parallel_peak"] = 1
    validate_evidence({**summary, "kind": "run", "schema_version": "aether.lab.evidence.v1"})
    return summary


def _append_results(results: list[dict[str, Any]], history: Path) -> None:
    for result in results:
        _append_jsonl(history, result)


def _run_parallel_batch(
    batch: list[tuple[int, int]],
    *,
    suite: str,
    matrix_root: Path,
    prepare: bool,
    hermes: Path | None,
    profile_root: Path | None,
    parallel: int,
) -> list[dict[str, Any]]:
    roots = [matrix_root / f"{index:02d}-e2e-{number:02d}" for index, number in batch]
    if len(roots) != len(set(roots)):
        raise ValueError("matrix scheduled duplicate disposable run roots")
    if len(batch) == 1:
        results = [
            _run_scenario(
                batch[0][1], index=batch[0][0], suite=suite, matrix_root=matrix_root,
                prepare=prepare, hermes=hermes, profile_root=profile_root,
            )
        ]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(parallel, 2)) as executor:
            futures = [
                executor.submit(
                    _run_scenario,
                    number,
                    index=index,
                    suite=suite,
                    matrix_root=matrix_root,
                    prepare=prepare,
                    hermes=hermes,
                    profile_root=profile_root,
                )
                for index, number in batch
            ]
            results = [future.result() for future in futures]
    peak = min(len(batch), parallel, 2)
    for result in results:
        result["parallel"] = peak
        result["parallel_peak"] = peak
        result["isolation_verified"] = len(roots) == len(set(roots))
    return results


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.parallel not in {1, 2}:
        print("MATRIX_ERROR: --parallel must be 1 or 2", file=sys.stderr)
        return 3
    if args.live and (args.hermes is None or args.profile_root is None):
        print("MATRIX_ERROR: --live requires --hermes and --profile-root", file=sys.stderr)
        return 3
    if args.live and not args.allow_model_spend:
        print(
            "MATRIX_ERROR: live matrix may consume provider quota; --allow-model-spend is required",
            file=sys.stderr,
        )
        return 3

    try:
        matrix_root = _suite_root(args.matrix_root, args.suite)
    except FileExistsError:
        print("MATRIX_ERROR: matrix root must not already exist", file=sys.stderr)
        return 3

    results: list[dict[str, Any]] = []
    if args.suite == "observation":
        try:
            result = prepare_observation_only(matrix_root / "observation") if args.prepare_only else {
                "schema_version": "aether.lab.evidence.v1",
                "kind": "observation",
                "status": "CAPABILITY_WALL",
                "mode": "live-persistent",
                "suite": "observation",
                "reason": "live_observation_requires_explicit_runtime_authority",
            }
        except (OSError, ValueError, RuntimeError):
            result = {
                "schema_version": "aether.lab.evidence.v1",
                "kind": "observation",
                "status": "FAIL",
                "mode": "prepare-only",
                "suite": "observation",
                "reason": "observation_preparation_failed",
            }
        validate_evidence(result)
        results.append(result)
    else:
        batch: list[tuple[int, int]] = []
        for index, number in enumerate(SUITES[args.suite], start=1):
            if number in SERIAL_SCENARIOS:
                if batch:
                    results.extend(
                        _run_parallel_batch(
                            batch, suite=args.suite, matrix_root=matrix_root,
                            prepare=args.prepare_only, hermes=args.hermes,
                            profile_root=args.profile_root, parallel=args.parallel,
                        )
                    )
                    batch = []
                results.extend(
                    _run_parallel_batch(
                        [(index, number)], suite=args.suite, matrix_root=matrix_root,
                        prepare=args.prepare_only, hermes=args.hermes,
                        profile_root=args.profile_root, parallel=1,
                    )
                )
                if args.stop_on_failure and results[-1].get("status") not in {"PASS", "PREPARED"}:
                    break
                continue
            batch.append((index, number))
            if len(batch) == args.parallel:
                results.extend(
                    _run_parallel_batch(
                        batch, suite=args.suite, matrix_root=matrix_root,
                        prepare=args.prepare_only, hermes=args.hermes,
                        profile_root=args.profile_root, parallel=args.parallel,
                    )
                )
                batch = []
                if args.stop_on_failure and any(
                    item.get("status") not in {"PASS", "PREPARED"} for item in results
                ):
                    break
        if batch:
            results.extend(
                _run_parallel_batch(
                    batch, suite=args.suite, matrix_root=matrix_root,
                    prepare=args.prepare_only, hermes=args.hermes,
                    profile_root=args.profile_root, parallel=args.parallel,
                )
            )

    _append_results(results, args.history)
    history = _read_history(args.history)
    gate = score_history(history)
    mode = "prepare-only" if args.prepare_only else "live-oneshot"
    status = "PREPARED" if args.prepare_only and all(item.get("status") == "PREPARED" for item in results) else (
        "PASS" if not args.prepare_only and all(item.get("status") == "PASS" for item in results) else "FAIL"
    )
    report = {
        "schema_version": "aether.lab.evidence.v1",
        "kind": "matrix",
        "status": status,
        "mode": mode,
        "suite": args.suite,
        "runs": results,
        "rolling_reliability_gate": gate,
        "parallel": args.parallel,
        "isolation_verified": all(item.get("isolation_verified", True) for item in results),
    }
    validate_evidence(report)
    (matrix_root / "matrix.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if status in {"PREPARED", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
