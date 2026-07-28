"""Deterministic, local-only R7 shadow-system benchmark over real coordination APIs."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from olympus_v3.coordination import (
    AdmissionDecision,
    AdmissionProposal,
    AdmissionStatus,
    AnycastAssignment,
    DurableShadowCorrelationRegistry,
    HarmoniaPlan,
    HarmoniaProjection,
    HarmoniaTask,
    Principal,
    ShadowCondition,
    ShadowConfig,
    ShadowCorrelationRegistry,
    ShadowObservation,
    ShadowSessionCorrelation,
    TaskState,
    compare_shadow,
    observe_olympus_session,
)

SCHEMA_VERSION = "r7-shadow-benchmark-v2"
PROJECT = "project-a"
CONTRACT = "contract-a"
GENERATION = 3
ROOT = "/tmp/r7-project-a"
WORKER = Principal(PROJECT, "instance-a", "hefesto")
SCENARIOS = (
    "clean_single_task",
    "dependency_chain",
    "parallel_independent",
    "duplicate_dispatch",
    "runtime_unavailable_restored",
    "restart_rebuild_durable_registry",
    "budget_rejection",
    "reviewer_violation",
    "unknown_effect",
    "feature_disabled_rollback",
)
_CONDITION = {
    "duplicate_dispatch": ShadowCondition.DUPLICATE_DELIVERY,
    "budget_rejection": ShadowCondition.BUDGET_EXHAUSTED,
    "reviewer_violation": ShadowCondition.REVIEWER_VIOLATION,
    "unknown_effect": ShadowCondition.UNKNOWN_EFFECT,
}


@dataclass
class FakeOlympusDB:
    """Read-only fixture exposing the same public evidence methods as OlympusDB."""

    task_id: str
    session_id: str
    status: str = "completed"
    reads: int = 0

    async def get_session(self, session_id: str) -> dict:
        self.reads += 1
        return {
            "session_id": session_id,
            "agent": WORKER.actor_id,
            "status": self.status,
            "metadata": json.dumps({"profile": WORKER.actor_id, "project_root": ROOT}),
        }

    async def get_latest_turn(self, _session_id: str) -> dict:
        self.reads += 1
        return {
            "content": (
                f"AETHER_SHADOW_V1 task_id={self.task_id} participant={WORKER.actor_id} technical_status={self.status}"
            )
        }


def _proposal(task_id: str, dependencies: tuple[str, ...] = ()) -> AdmissionProposal:
    return AdmissionProposal(
        task_id,
        "observe",
        "user",
        ("src",),
        (),
        "hefesto",
        "implement",
        ("gate",),
        1,
        1,
        30,
        1,
        "e1",
        1,
        100,
        dependencies,
    )


def _plan(specs: Iterable[tuple[str, tuple[str, ...]]]) -> HarmoniaPlan:
    proposals = tuple(_proposal(task_id, dependencies) for task_id, dependencies in specs)
    decisions = tuple(AdmissionDecision(item.task_id, AdmissionStatus.ADMITTED, (), item) for item in proposals)
    assignments = tuple(AnycastAssignment(item.task_id, WORKER) for item in proposals)
    projection = HarmoniaProjection(
        1,
        tuple(HarmoniaTask(item, TaskState.READY, WORKER, 0, ()) for item in proposals),
    )
    return HarmoniaPlan(decisions, assignments, (), projection)


async def _evidence(
    task_id: str,
    session_id: str,
    *,
    conditions: tuple[ShadowCondition, ...] = (),
) -> tuple[object, int]:
    db = FakeOlympusDB(task_id, session_id)
    item = await observe_olympus_session(
        db,
        session_id=session_id,
        task_id=task_id,
        participant=WORKER,
        project_root=ROOT,
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
        conditions=conditions,
    )
    return item, db.reads


def _compare(
    plan: HarmoniaPlan,
    task_id: str,
    registry: object,
    *,
    session_id: str | None = None,
    conditions: tuple[ShadowCondition, ...] = (),
) -> tuple[object, int]:
    actual = session_id or f"actual-{task_id}"
    item, reads = asyncio.run(_evidence(task_id, actual, conditions=conditions))
    correlation = ShadowSessionCorrelation.from_evidence(plan, item)
    report = compare_shadow(
        plan,
        item,
        project_root=ROOT,
        config=ShadowConfig(True),
        project_id=PROJECT,
        contract_id=CONTRACT,
        generation=GENERATION,
        expected_status="completed",
        correlation=correlation,
        registry=registry,
    )
    return report, reads


def _summary(
    name: str,
    reports: list[object],
    *,
    started_ns: int,
    observer_reads: int,
    store_writes: int,
    storage_growth: int,
    recovery_ms: float,
    injected_failure: bool,
    rollback: bool = False,
) -> dict:
    mismatches = tuple(reason for report in reports for reason in report.mismatches)
    mismatch_detected = bool(mismatches and mismatches != ("feature_disabled",))
    final = reports[-1]
    return {
        "scenario": name,
        "outcome": "disabled" if rollback else ("mismatch" if mismatch_detected else "observed"),
        "agreement": {
            "assignment": final.assignment_agreement,
            "participant": final.participant_agreement,
            "session": final.session_agreement,
            "status": final.status_agreement,
        },
        "mismatches": list(mismatches),
        "injected_failure": injected_failure,
        "mismatch_detected": mismatch_detected,
        "semantic_complete": any(report.semantic_complete for report in reports),
        "observer_reads": observer_reads,
        "session_derivations": len(reports) if not rollback else 0,
        "store_writes": store_writes,
        "rollback": rollback,
        "observation_latency_overhead_ms": (time.perf_counter_ns() - started_ns) / 1_000_000,
        "storage_growth_bytes": storage_growth,
        "recovery_time_ms": recovery_ms,
        # Counting rule: one manual inspection avoided when an injected fault is
        # identified with its typed mismatch; clean/disabled paths count zero.
        "manual_reconciliation_steps_avoided": int(injected_failure and mismatch_detected),
        "lifecycle_effect_calls": 0,
    }


def run_scenario(name: str, workdir: Path) -> dict:
    if name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {name}")
    workdir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter_ns()

    if name == "feature_disabled_rollback":
        report = compare_shadow(
            _plan((("task-a", ()),)),
            ShadowObservation("task-a", WORKER, "unread", "completed"),
            project_root=ROOT,
        )
        return _summary(
            name,
            [report],
            started_ns=started,
            observer_reads=0,
            store_writes=0,
            storage_growth=0,
            recovery_ms=0.0,
            injected_failure=False,
            rollback=True,
        )

    if name == "dependency_chain":
        reports = []
        reads = 0
        completed: tuple[str, ...] = ()
        for index in range(3):
            task_id = f"task-{index}"
            dependencies = completed[-1:] if completed else ()
            stage = _plan(((task_id, dependencies),))
            report, count = _compare(stage, task_id, ShadowCorrelationRegistry())
            reports.append(report)
            reads += count
            completed += (task_id,)
        return _summary(
            name,
            reports,
            started_ns=started,
            observer_reads=reads,
            store_writes=0,
            storage_growth=0,
            recovery_ms=0.0,
            injected_failure=False,
        )

    if name == "parallel_independent":
        specs = tuple((f"task-{index}", ()) for index in range(3))
        parallel_plan = _plan(specs)
        registry = ShadowCorrelationRegistry()
        reports = []
        reads = 0
        for task_id, _ in specs:
            report, count = _compare(parallel_plan, task_id, registry)
            reports.append(report)
            reads += count
        return _summary(
            name,
            reports,
            started_ns=started,
            observer_reads=reads,
            store_writes=0,
            storage_growth=0,
            recovery_ms=0.0,
            injected_failure=False,
        )

    if name == "runtime_unavailable_restored":
        scenario_plan = _plan((("task-a", ()),))
        registry = ShadowCorrelationRegistry()
        failed, reads_a = _compare(
            scenario_plan,
            "task-a",
            registry,
            conditions=(ShadowCondition.RUNTIME_UNAVAILABLE,),
        )
        recovery_started = time.perf_counter_ns()
        restored, reads_b = _compare(scenario_plan, "task-a", registry)
        recovery_ms = (time.perf_counter_ns() - recovery_started) / 1_000_000
        return _summary(
            name,
            [failed, restored],
            started_ns=started,
            observer_reads=reads_a + reads_b,
            store_writes=0,
            storage_growth=0,
            recovery_ms=recovery_ms,
            injected_failure=True,
        )

    if name == "restart_rebuild_durable_registry":
        path = workdir / "shadow.sqlite"
        before = path.stat().st_size if path.exists() else 0
        scenario_plan = _plan((("task-a", ()),))
        first = DurableShadowCorrelationRegistry(path)
        initial, reads_a = _compare(scenario_plan, "task-a", first)
        first.close()
        recovery_started = time.perf_counter_ns()
        second = DurableShadowCorrelationRegistry(path)
        rebuilt, reads_b = _compare(scenario_plan, "task-a", second)
        second.close()
        recovery_ms = (time.perf_counter_ns() - recovery_started) / 1_000_000
        growth = max(path.stat().st_size - before, 0)
        return _summary(
            name,
            [initial, rebuilt],
            started_ns=started,
            observer_reads=reads_a + reads_b,
            store_writes=1,
            storage_growth=growth,
            recovery_ms=recovery_ms,
            injected_failure=False,
        )

    scenario_plan = _plan((("task-a", ()),))
    condition = _CONDITION.get(name)
    conditions = (condition,) if condition else ()
    report, reads = _compare(scenario_plan, "task-a", ShadowCorrelationRegistry(), conditions=conditions)
    return _summary(
        name,
        [report],
        started_ns=started,
        observer_reads=reads,
        store_writes=0,
        storage_growth=0,
        recovery_ms=0.0,
        injected_failure=condition is not None,
    )


def run_benchmark(output: Path, repetitions: int = 5) -> dict:
    if isinstance(repetitions, bool) or repetitions < 5:
        raise ValueError("repetitions must be at least 5")
    with tempfile.TemporaryDirectory(prefix="r7-shadow-") as temp:
        root = Path(temp)
        runs = {
            name: [run_scenario(name, root / f"{name}-{index}") for index in range(repetitions)] for name in SCENARIOS
        }
    injected = [run for items in runs.values() for run in items if run["injected_failure"]]
    clean = [run for items in runs.values() for run in items if not run["injected_failure"] and not run["rollback"]]
    true_positive = sum(run["mismatch_detected"] for run in injected)
    false_positive = sum(run["mismatch_detected"] for run in clean)
    report = {
        "schema_version": SCHEMA_VERSION,
        "repetitions": repetitions,
        "execution": {"mode": "isolated-local-real-apis", "real_probe_count": 0, "external_effects": 0},
        "scenarios": list(SCENARIOS),
        "scenario_runs": runs,
        "injected_failure_runs": len(injected),
        "detected_failure_runs": true_positive,
        "mismatch_detection_recall": true_positive / len(injected) if injected else 1.0,
        "clean_false_positive_rate": false_positive / len(clean) if clean else 0.0,
        "observation_latency_overhead_ms": {
            name: sum(item["observation_latency_overhead_ms"] for item in values) / repetitions
            for name, values in runs.items()
        },
        "storage_growth_bytes": {
            name: max(item["storage_growth_bytes"] for item in values) for name, values in runs.items()
        },
        "recovery_time_ms": {name: max(item["recovery_time_ms"] for item in values) for name, values in runs.items()},
        "manual_reconciliation_steps_avoided": sum(
            item["manual_reconciliation_steps_avoided"] for values in runs.values() for item in values
        ),
        "lifecycle_effect_calls": sum(item["lifecycle_effect_calls"] for values in runs.values() for item in values),
        "cost": "unknown",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    report = run_benchmark(args.output, args.repetitions)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "schema_version": report["schema_version"],
                "scenarios": len(report["scenarios"]),
                "runs": report["repetitions"] * len(report["scenarios"]),
                "detected_failure_runs": report["detected_failure_runs"],
                "lifecycle_effect_calls": report["lifecycle_effect_calls"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
