#!/usr/bin/env python3
"""Reproduce Aether Contract Observation release evidence.

The runner never consults a private/editable Hermes installation.  Its only accepted
runtime source is the public annotated tag and commit locked below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
for source_root in (ROOT / "src", ROOT / "tests"):
    value = str(source_root)
    if value not in sys.path:
        sys.path.insert(0, value)

from observation_helpers import PROJECT_ID, TRACE_ID, EventFactory  # noqa: E402

from aether_agents.lifecycle import (  # noqa: E402
    HERMES_BASELINE,
    _materialize_git_archive,
    _tree_sha256,
    verify_clean_checkout,
)
from aether_agents.observation.reduce.reducer import (  # noqa: E402
    ReductionInput,
    reduce_events,
)

MINIMUM_OBSERVATION_TESTS = 119
EXPECTED_CORE_TESTS = 452
EXPECTED_CORE_NODE_MANIFEST_SHA256 = (
    "4a755f76cd74da6abe0b2e32901a7c253398f1ea154aef21cdea2d4d50cdf7b4"
)
PLUGIN_CALLBACK_COUNT = 22
TEN_THOUSAND_REDUCTION_LIMIT_S = 2.0
CALLBACK_P95_LIMIT_MS = 5.0
CALLBACK_P99_LIMIT_MS = 20.0
VALIDATION_RESULTS_SCHEMA_VERSION = 1
VALIDATION_RESULTS_BLOCK_BEGIN = "<!-- BEGIN AETHER_OBSERVATION_QUALIFICATION_RESULTS_V1 -->"
VALIDATION_RESULTS_BLOCK_END = "<!-- END AETHER_OBSERVATION_QUALIFICATION_RESULTS_V1 -->"
_RESULT_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$", re.ASCII)
CORE_TESTS = (
    "tests/test_observation_contracts.py",
    "tests/test_observation_journal_storage.py",
    "tests/test_observation_reducer.py",
    "tests/test_observation_cli_plugin.py",
    "tests/test_observation_packaging.py",
    "tests/test_observation_path_confinement.py",
    "tests/test_observation_performance.py",
    "tests/test_projection_transition_runner.py",
)
# Lifecycle and qualification are separate release lanes: the former creates two
# isolated installations and the latter executes this manifest plus the real-Hermes
# harness.  Including either recursively here would duplicate expensive gates and
# make the core node identity depend on its own runner.
_PYTEST_OUTCOME_RE = re.compile(
    r"(?<![0-9])(?P<count>[0-9]+) "
    r"(?P<outcome>passed|failed|skipped|deselected|xfailed|xpassed|errors?|rerun)",
    re.ASCII,
)


def contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "hermes": {
            "repository": HERMES_BASELINE.repository,
            "tag": HERMES_BASELINE.tag,
            "tag_object": HERMES_BASELINE.tag_object,
            "commit": HERMES_BASELINE.commit,
            "distribution": HERMES_BASELINE.distribution,
            "version": HERMES_BASELINE.version,
        },
        "minimum_observation_tests": MINIMUM_OBSERVATION_TESTS,
        "expected_core_tests": EXPECTED_CORE_TESTS,
        "expected_core_node_manifest_sha256": EXPECTED_CORE_NODE_MANIFEST_SHA256,
        "core_test_files": list(CORE_TESTS),
        "plugin_callback_count": PLUGIN_CALLBACK_COUNT,
        "validation_results": {
            "schema_version": VALIDATION_RESULTS_SCHEMA_VERSION,
            "block_begin": VALIDATION_RESULTS_BLOCK_BEGIN,
            "block_end": VALIDATION_RESULTS_BLOCK_END,
        },
    }


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=env,
        check=False,
        capture_output=capture,
        text=True,
    )
    if completed.returncode != 0:
        executable = Path(str(arguments[0])).name or "command"
        stdout_tail = _content_free_stream_tail(completed.stdout)
        stderr_tail = _content_free_stream_tail(completed.stderr)
        raise RuntimeError(
            f"command failed ({executable} exit {completed.returncode}): "
            f"stdout_tail={stdout_tail}; stderr_tail={stderr_tail}"
        )
    return completed


def _content_free_stream_tail(stream: str | None) -> str:
    """Describe a bounded stream tail without echoing command/test payload bytes."""
    if not stream:
        return "[empty]"
    tail = stream[-8192:]
    lines = tail.splitlines()[-8:]
    described: list[str] = []
    for line in lines:
        outcomes: dict[str, int] = {}
        for match in _PYTEST_OUTCOME_RE.finditer(line):
            outcome = match.group("outcome")
            outcomes[outcome] = outcomes.get(outcome, 0) + int(match.group("count"))
        if outcomes:
            fields = ",".join(f"{name}={outcomes[name]}" for name in sorted(outcomes))
            described.append(f"pytest-summary({fields})")
            continue
        encoded = line.encode("utf-8", errors="replace")
        described.append(
            f"line(chars={len(line)},sha256={hashlib.sha256(encoded).hexdigest()[:16]})"
        )
    return "[" + ",".join(described or ["empty"]) + "]"


def _require_single_passed_harness(completed: subprocess.CompletedProcess[str]) -> None:
    outcomes: dict[str, int] = {}
    for match in _PYTEST_OUTCOME_RE.finditer(
        "\n".join((completed.stdout or "", completed.stderr or ""))
    ):
        outcome = match.group("outcome")
        outcomes[outcome] = outcomes.get(outcome, 0) + int(match.group("count"))
    if outcomes != {"passed": 1}:
        safe_outcomes = ",".join(f"{name}={outcomes[name]}" for name in sorted(outcomes))
        raise RuntimeError(
            "qualification harness must execute exactly one passed test without skips "
            f"(outcomes={safe_outcomes or 'none'})"
        )


def checkout_exact(path: Path) -> dict[str, Any]:
    expanded = path.expanduser()
    target = expanded.absolute()
    for component in (target, *target.parents):
        if component.is_symlink():
            raise RuntimeError("checkout target path must not contain a symlink")
    if target.exists():
        if not (target / ".git").is_dir():
            raise RuntimeError("checkout target exists and is not a Git checkout")
        status = _run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=target
        ).stdout.strip()
        if status:
            raise RuntimeError("refusing to alter a dirty Hermes checkout")
        _run(["git", "fetch", "--force", "origin", f"refs/tags/{HERMES_BASELINE.tag}"], cwd=target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                HERMES_BASELINE.repository,
                str(target),
            ],
            cwd=target.parent,
        )
    _run(["git", "checkout", "--detach", HERMES_BASELINE.commit], cwd=target)
    evidence = verify_clean_checkout(
        target,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    _prioritize_hermes_source(evidence.path)
    return {
        "path": str(evidence.path),
        "tag": evidence.tag,
        "tag_object": evidence.tag_object,
        "commit": evidence.commit,
        "clean": evidence.clean,
    }


def _prioritize_hermes_source(source: Path) -> None:
    """Put one authenticated source first and evict any preloaded Hermes modules."""

    resolved = source.resolve(strict=True)
    sys.path[:] = [entry for entry in sys.path if entry != str(resolved)]
    sys.path.insert(0, str(resolved))
    for name in tuple(sys.modules):
        if name == "hermes_cli" or name.startswith("hermes_cli."):
            del sys.modules[name]


def _materialize_qualification_source(checkout: Path, destination: Path) -> dict[str, Any]:
    """Create the only Hermes tree qualification is allowed to execute."""

    evidence = verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    _materialize_git_archive(evidence.path, evidence.commit, destination)
    return {
        "path": str(destination),
        "sha256": _tree_sha256(destination),
        "tag": evidence.tag,
        "tag_object": evidence.tag_object,
        "commit": evidence.commit,
        "source_kind": "git_archive_tracked_commit",
    }


def _qualification_environment(source: Path) -> dict[str, str]:
    resolved = source.resolve(strict=True)
    environment = os.environ.copy()
    environment.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    environment.pop("PYTHONHOME", None)
    # Pytest adds this project's ``src`` through its checked-in configuration.
    # Exporting it here would leak into package-isolation subprocesses, causing
    # an installed-runtime probe (or tamper test) to resolve and mutate the source
    # checkout.  Discard every ambient editable tree and expose only exact Hermes.
    environment["PYTHONPATH"] = str(resolved)
    environment["AETHER_QUALIFICATION_TRACKED_SOURCE"] = str(resolved)
    environment["AETHER_QUALIFICATION_SOURCE_COMMIT"] = HERMES_BASELINE.commit
    return environment


def _collection_manifest(stdout: str) -> tuple[int, str]:
    match = re.search(r"(?P<count>[0-9]+) tests? collected", stdout)
    if match is None:
        raise RuntimeError("pytest collection output did not contain an exact test count")
    count = int(match.group("count"))
    nodes = sorted(
        line.strip() for line in stdout.splitlines() if line.startswith("tests/") and "::" in line
    )
    if len(nodes) != count:
        raise RuntimeError("pytest collection manifest count mismatch")
    digest = hashlib.sha256(("\n".join(nodes) + "\n").encode("utf-8")).hexdigest()
    return count, digest


def _measured_harness(stdout: str) -> dict[str, Any]:
    prefix = "AETHER_HARNESS_RESULT="
    rows = [line[len(prefix) :] for line in stdout.splitlines() if line.startswith(prefix)]
    if len(rows) != 1:
        raise RuntimeError("qualification harness did not emit one measured result")
    try:
        result = json.loads(rows[0])
    except json.JSONDecodeError as error:
        raise RuntimeError("qualification harness result is malformed") from error
    expected = {
        "plugin_callback_count": PLUGIN_CALLBACK_COUNT,
        "unload_hook_count": 0,
        "tool_events_captured": True,
        "api_events_captured": True,
        "raw_payload_absent": True,
    }
    if result != expected:
        raise RuntimeError("qualification harness measured contract mismatch")
    return result


def run_tests(checkout: Path, python: Path) -> dict[str, Any]:
    evidence = verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    with tempfile.TemporaryDirectory(prefix="aether-hermes-qualified-") as temporary:
        source = Path(temporary) / "hermes-source"
        qualified_source = _materialize_qualification_source(checkout, source)
        environment = _qualification_environment(source)
        collected = _run(
            [str(python), "-m", "pytest", "--collect-only", "-q", *CORE_TESTS],
            env=environment,
        )
        collected_count, node_manifest_sha256 = _collection_manifest(collected.stdout)
        if collected_count != EXPECTED_CORE_TESTS:
            raise RuntimeError(
                "observation suite collection differs from locked manifest count "
                f"({collected_count} != {EXPECTED_CORE_TESTS})"
            )
        if node_manifest_sha256 != EXPECTED_CORE_NODE_MANIFEST_SHA256:
            raise RuntimeError(
                "observation suite node manifest differs from locked identity "
                f"({node_manifest_sha256} != {EXPECTED_CORE_NODE_MANIFEST_SHA256})"
            )
        completed = _run(
            [str(python), "-m", "pytest", "-q", *CORE_TESTS],
            env=environment,
        )
        outcomes: dict[str, int] = {}
        for match in _PYTEST_OUTCOME_RE.finditer(completed.stdout):
            outcome = match.group("outcome")
            outcomes[outcome] = outcomes.get(outcome, 0) + int(match.group("count"))
        if outcomes != {"passed": EXPECTED_CORE_TESTS}:
            raise RuntimeError("observation suite did not execute its exact collected manifest")
        count = outcomes["passed"]
        if count < MINIMUM_OBSERVATION_TESTS:
            raise RuntimeError(
                f"observation suite executed {count}, below historical floor "
                f"{MINIMUM_OBSERVATION_TESTS}"
            )
        harness = _run(
            [
                str(python),
                "-m",
                "pytest",
                "-s",
                "-q",
                (
                    "tests/test_observation_qualification.py::"
                    "test_real_plugin_context_captures_tool_and_api_then_unloads_every_hook"
                ),
            ],
            env=environment,
        )
        _require_single_passed_harness(harness)
        measured = _measured_harness(harness.stdout)
    return {
        "passed": count,
        "collected": collected_count,
        "expected": EXPECTED_CORE_TESTS,
        "node_manifest_sha256": node_manifest_sha256,
        "minimum": MINIMUM_OBSERVATION_TESTS,
        "core_output": completed.stdout.strip(),
        "real_plugin_context": harness.stdout.strip(),
        **measured,
        "qualified_source": qualified_source,
        "hermes_checkout": {
            "path": str(evidence.path),
            "tag": evidence.tag,
            "tag_object": evidence.tag_object,
            "commit": evidence.commit,
            "clean": evidence.clean,
        },
        "machine": _machine(),
    }


def _stress_events(count: int) -> list[dict[str, Any]]:
    if count < 2:
        raise ValueError("event count must be at least two")
    factory = EventFactory()
    opened = factory.opened()
    state = factory.unit(
        "work_unit.status",
        "started",
        1,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    events = [opened]
    for sequence in range(1, count):
        event = deepcopy(state)
        event["event_id"] = f"evt_{sequence + 1:032x}"
        event["producer_seq"] = sequence
        event["monotonic_ns"] = sequence + 1
        # Each sample represents a distinct native state observation. Repeating the
        # original native timestamp would truthfully describe one duplicated fact and
        # reconciliation would (correctly) collapse the benchmark workload.
        observed_at = factory.at(sequence / 1000).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        event["occurred_at"] = observed_at
        event["recorded_at"] = observed_at
        events.append(event)
    return events


def _incremental_stress_events(count: int) -> list[dict[str, Any]]:
    """Representative O(n) journal/projection stream of independent tool spans."""
    if count < 2:
        raise ValueError("event count must be at least two")
    factory = EventFactory()
    factory.opened()
    key_epoch = "fpk_" + "1" * 32
    session_ref = f"sid_{key_epoch}_" + "2" * 64
    for sequence in range(1, count):
        call_index = (sequence - 1) // 2
        envelope = {
            "call_id": f"call_{key_epoch}_{call_index:064x}",
            "name": "terminal",
            "category": "terminal",
            "session_id": session_ref,
            "task_id": "t_aaaaaaaa",
            "actor_kind": "agent",
            "actor_id": "implementer",
            "profile": "implementer",
            "occurred_at": factory.at(sequence / 1000),
        }
        if sequence % 2:
            event = factory.builder.tool_started(**envelope)
        else:
            event = factory.builder.tool_terminal(
                **envelope,
                status="completed",
                duration_ms=1,
            )
        factory.add(event)
    return factory.events


def _machine() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unavailable",
        "cpu_count": os.cpu_count(),
    }


def measure_reduction(event_count: int) -> dict[str, Any]:
    events = _stress_events(event_count)
    started = perf_counter()
    summary = reduce_events(
        ReductionInput(
            trace_id=TRACE_ID,
            project_id=PROJECT_ID,
            events=events,
            producer_count=1,
        )
    )
    elapsed = perf_counter() - started
    return {
        "mode": "full_reduction",
        "event_count": event_count,
        "source_event_count": summary["source_event_count"],
        "seconds": elapsed,
        "events_per_second": event_count / elapsed,
        "machine": _machine(),
    }


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    return ordered[ceil(len(ordered) * fraction) - 1]


def _latency_metrics(samples: list[float], *, pairs: int) -> dict[str, Any]:
    if not samples:
        raise ValueError("latency measurement requires samples")
    return {
        "sample_count": len(samples),
        "phases": {"pre": pairs, "post": pairs},
        "p50_ms": _percentile(samples, 0.50),
        "p95_ms": _percentile(samples, 0.95),
        "p99_ms": _percentile(samples, 0.99),
        "max_ms": max(samples),
    }


def measure_callbacks(call_pairs: int = 500) -> dict[str, Any]:
    """Measure the real Hermes manager/context → projector → journal callback path."""

    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

    from aether_agents.observation.capture import hermes_plugin
    from aether_agents.observation.capture.journal import list_segments, read_segment
    from aether_agents.observation.context import ProjectRegistry
    from aether_agents.observation.identity import correlation_token
    from aether_agents.paths import ObservationPaths

    if call_pairs < 10:
        raise ValueError("callback benchmark needs at least ten call pairs")
    with tempfile.TemporaryDirectory(prefix="aether-callback-") as temporary:
        root = Path(temporary)
        project = root / "project"
        marker = project / ".aether" / "project.toml"
        marker.parent.mkdir(parents=True)
        marker.write_text(f'project_id = "{PROJECT_ID}"\n', encoding="utf-8")
        previous_environment = {
            key: os.environ.get(key)
            for key in ("XDG_STATE_HOME", "AETHER_PROJECT_ID", "HERMES_HOME")
        }
        os.environ["XDG_STATE_HOME"] = str(root / "state")
        os.environ["AETHER_PROJECT_ID"] = PROJECT_ID
        os.environ["HERMES_HOME"] = str(root / "hermes" / "profiles" / "morfeo")
        original_start = hermes_plugin._NativeReconciliationWorker.start
        hermes_plugin._NativeReconciliationWorker.start = lambda self: None
        try:
            if not ProjectRegistry().register(PROJECT_ID, project, "qualification-benchmark"):
                raise RuntimeError("benchmark project registry refused exact project")
            manager = PluginManager(scope_key=str(root / "hermes"))
            manifest = PluginManifest(
                name="aether-contract-observer",
                key="aether-contract-observer",
                source="entrypoint",
            )
            context = PluginContext(manifest, manager)
            hermes_plugin.register(context)
            callback_count = sum(len(callbacks) for callbacks in manager._hooks.values())
            if callback_count != PLUGIN_CALLBACK_COUNT:
                raise RuntimeError(
                    f"real PluginContext registered {callback_count}, expected "
                    f"{PLUGIN_CALLBACK_COUNT}"
                )
            token = correlation_token(TRACE_ID, "t_aaaaaaaa")
            manager.invoke_hook(
                "pre_tool_call",
                tool_name="kanban_create",
                tool_call_id="create-1",
                session_id="session-1",
                turn_id="turn-0",
                api_request_id="request-0",
                args={"idempotency_key": token},
            )
            manager.invoke_hook(
                "post_tool_call",
                tool_name="kanban_create",
                tool_call_id="create-1",
                session_id="session-1",
                turn_id="turn-0",
                api_request_id="request-0",
                status="success",
                args={"idempotency_key": token},
                result={"ok": True, "task_id": "t_aaaaaaaa", "project_id": PROJECT_ID},
            )
            tool_samples: list[float] = []
            for index in range(call_pairs):
                payload = {
                    "tool_name": "terminal",
                    "tool_call_id": f"call-{index}",
                    "session_id": "session-1",
                    "turn_id": f"turn-{index + 1}",
                    "api_request_id": f"request-{index + 1}",
                    "task_id": "t_aaaaaaaa",
                }
                started = perf_counter()
                manager.invoke_hook("pre_tool_call", **payload)
                tool_samples.append((perf_counter() - started) * 1000)
                started = perf_counter()
                manager.invoke_hook("post_tool_call", **payload, status="success")
                tool_samples.append((perf_counter() - started) * 1000)
            api_samples: list[float] = []
            for index in range(call_pairs):
                api_payload = {
                    "api_request_id": f"api-request-{index}",
                    "session_id": "session-1",
                    "turn_id": f"api-turn-{index}",
                    "task_id": "t_aaaaaaaa",
                    "model": "model-1",
                    "provider": "provider-1",
                    "prompt": (
                        "RAW_PROMPT_MUST_NOT_PERSIST"
                        if index == 0
                        else "synthetic qualification prompt"
                    ),
                    "message_count": 1,
                    "tool_count": 1,
                }
                started = perf_counter()
                manager.invoke_hook("pre_api_request", **api_payload)
                api_samples.append((perf_counter() - started) * 1000)
                started = perf_counter()
                manager.invoke_hook(
                    "post_api_request",
                    **api_payload,
                    status="completed",
                    response=(
                        "RAW_RESPONSE_MUST_NOT_PERSIST"
                        if index == 0
                        else "synthetic qualification response"
                    ),
                    usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
                )
                api_samples.append((perf_counter() - started) * 1000)
            manager.unload(manifest)
            unload_count = sum(len(callbacks) for callbacks in manager._hooks.values())
            paths = ObservationPaths.for_project(PROJECT_ID, root=root / "state" / "aether")
            disk = b"".join(
                line
                for segment in list_segments(paths)
                for line in read_segment(segment.path).lines
            )
        finally:
            hermes_plugin._NativeReconciliationWorker.start = original_start
            for key, previous in previous_environment.items():
                if previous is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous
    surfaces = {
        "tool": _latency_metrics(tool_samples, pairs=call_pairs),
        "api": _latency_metrics(api_samples, pairs=call_pairs),
    }
    p95_surface = max(surfaces, key=lambda name: (surfaces[name]["p95_ms"], name))
    p99_surface = max(surfaces, key=lambda name: (surfaces[name]["p99_ms"], name))
    worst = {
        "p95_ms": surfaces[p95_surface]["p95_ms"],
        "p95_surface": p95_surface,
        "p99_ms": surfaces[p99_surface]["p99_ms"],
        "p99_surface": p99_surface,
    }
    return {
        "sample_count": sum(surface["sample_count"] for surface in surfaces.values()),
        "plugin_callback_count": callback_count,
        "unload_hook_count": unload_count,
        "surfaces": surfaces,
        "worst": worst,
        # Compatibility aliases: stable claims can continue reading the worst tail.
        "p95_ms": worst["p95_ms"],
        "p99_ms": worst["p99_ms"],
        "raw_prompt_absent": b"RAW_PROMPT_MUST_NOT_PERSIST" not in disk,
        "raw_response_absent": b"RAW_RESPONSE_MUST_NOT_PERSIST" not in disk,
        "machine": _machine(),
    }


def measure_out_of_band_flush(
    sample_count: int = 20,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Measure supervised journal fsync separately from every Hermes callback."""
    from aether_agents.observation.capture.flusher import Flusher
    from aether_agents.observation.capture.journal import JournalWriter
    from aether_agents.observation.identity import new_producer_epoch
    from aether_agents.paths import ObservationPaths

    if sample_count < 3:
        raise ValueError("flush benchmark requires at least three samples")
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if root is None:
        temporary = tempfile.TemporaryDirectory(prefix="aether-flush-")
        state_root = Path(temporary.name)
    else:
        state_root = root
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root / "aether")
    writer = JournalWriter(
        paths=paths,
        producer_epoch=new_producer_epoch(),
        max_segment_events=sample_count + 1,
    )
    flusher = Flusher(writer=writer)
    samples: list[float] = []
    try:
        writer.open()
        events = _stress_events(sample_count + 1)[1:]
        for event in events:
            outcome = writer.append(event, critical=True)
            if not outcome.accepted:
                raise RuntimeError("flush benchmark journal append was rejected")
            started = perf_counter()
            flusher._tick()
            samples.append((perf_counter() - started) * 1000)
        successful = flusher.stats.flushes
    finally:
        writer.close_bounded(2.0)
        if temporary is not None:
            temporary.cleanup()
    return {
        "sample_count": len(samples),
        "successful_flushes": successful,
        "execution_path": "supervised_out_of_band",
        "surface": "Flusher._tick to JournalWriter.flush/fsync",
        "synchronous_callback_fsync": False,
        "p50_ms": _percentile(samples, 0.50),
        "p95_ms": _percentile(samples, 0.95),
        "p99_ms": _percentile(samples, 0.99),
        "max_ms": max(samples),
        "machine": _machine(),
    }


def _event_count_label(count: int) -> str:
    return {
        20: "twenty",
        40: "forty",
        1_000: "one_thousand",
        2_000: "two_thousand",
        10_000: "ten_thousand",
        100_000: "one_hundred_thousand",
    }.get(count, f"events_{count}")


def measure_incremental_pipeline(
    event_counts: Sequence[int] = (10_000, 100_000),
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Measure real cursor-based journal ingest and SQLite derivation at each size.

    SQLite projection is incremental. The canonical summary reducer still consumes the
    complete retained event set, so its separately timed phase is explicitly labelled
    ``full_reduction`` rather than being misreported as an incremental reducer.
    """
    from aether_agents.observation.capture.journal import JournalWriter
    from aether_agents.observation.identity import new_producer_epoch
    from aether_agents.observation.reduce.ingest import ingest_pending, reduce_trace
    from aether_agents.paths import ObservationPaths

    targets = tuple(event_counts)
    if not targets or any(count < 2 for count in targets):
        raise ValueError("incremental benchmark requires event counts of at least two")
    if tuple(sorted(set(targets))) != targets:
        raise ValueError("incremental benchmark event counts must be strictly increasing")

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if root is None:
        temporary = tempfile.TemporaryDirectory(prefix="aether-incremental-")
        state_root = Path(temporary.name)
    else:
        state_root = root
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root / "aether")
    events = _incremental_stress_events(targets[-1])
    writer = JournalWriter(
        paths=paths,
        producer_epoch=new_producer_epoch(),
        max_segment_bytes=1 << 60,
        max_segment_events=targets[-1] + 1,
    )
    normative_counts_complete = {10_000, 100_000}.issubset(targets)
    result: dict[str, Any] = {
        "mode": "incremental_journal_sqlite_projection",
        "scope": (
            "normative_10k_100k_pipeline"
            if normative_counts_complete
            else "bounded_real_pipeline_probe"
        ),
        "fixture": "one trace, one producer, paired native tool spans",
        "summary_reduction_mode": "full_reduction",
        "full_reduction_100k_recorded_separately": True,
        "normative_event_counts": [10_000, 100_000],
        "normative_counts_complete": normative_counts_complete,
        "event_counts": list(targets),
        "machine": _machine(),
    }
    previous = 0
    try:
        writer.open()
        for target in targets:
            append_started = perf_counter()
            for event in events[previous:target]:
                outcome = writer.append(event)
                if not outcome.accepted:
                    raise RuntimeError("incremental benchmark journal append was rejected")
            append_seconds = perf_counter() - append_started

            ingest_started = perf_counter()
            report = ingest_pending(paths)
            ingest_seconds = perf_counter() - ingest_started
            if report.events_inserted != target - previous:
                raise RuntimeError("incremental benchmark inserted an unexpected event count")

            reduction_started = perf_counter()
            summary = reduce_trace(paths, TRACE_ID)
            full_reduction_seconds = perf_counter() - reduction_started
            if summary["source_event_count"] != target:
                raise RuntimeError("incremental benchmark reduced an unexpected event count")

            result[_event_count_label(target)] = {
                "event_count": target,
                "new_events": target - previous,
                "events_inserted": report.events_inserted,
                "source_event_count": summary["source_event_count"],
                "journal_append_seconds": append_seconds,
                "incremental_ingest_seconds": ingest_seconds,
                "full_reduction_seconds": full_reduction_seconds,
            }
            previous = target
    finally:
        writer.close_bounded(2.0)
        if temporary is not None:
            temporary.cleanup()
    return result


def _enforce_performance_budgets(ten_thousand: dict[str, Any], callback: dict[str, Any]) -> None:
    reduction_seconds = ten_thousand.get("seconds")
    if not isinstance(reduction_seconds, (int, float)) or isinstance(reduction_seconds, bool):
        raise RuntimeError("10,000-event full reduction did not report a numeric duration")
    if reduction_seconds > TEN_THOUSAND_REDUCTION_LIMIT_S:
        raise RuntimeError(
            f"10,000-event full reduction exceeded {TEN_THOUSAND_REDUCTION_LIMIT_S:.1f}s budget"
        )
    for field, limit, label in (
        ("p95_ms", CALLBACK_P95_LIMIT_MS, "callback p95"),
        ("p99_ms", CALLBACK_P99_LIMIT_MS, "callback p99"),
    ):
        measured = callback.get(field)
        if not isinstance(measured, (int, float)) or isinstance(measured, bool):
            raise RuntimeError(f"{label} did not report a numeric duration")
        if measured > limit:
            raise RuntimeError(f"{label} exceeded {limit:.1f}ms budget")


def _require_normative_incremental_evidence(result: dict[str, Any]) -> None:
    expected = ((10_000, "ten_thousand"), (100_000, "one_hundred_thousand"))
    if result.get("mode") != "incremental_journal_sqlite_projection":
        raise RuntimeError("incremental pipeline did not exercise journal and SQLite projection")
    if result.get("summary_reduction_mode") != "full_reduction":
        raise RuntimeError("incremental pipeline did not label full summary reduction honestly")
    if result.get("normative_counts_complete") is not True:
        raise RuntimeError("incremental pipeline must retain 10,000 and 100,000-event evidence")
    counts = result.get("event_counts")
    if not isinstance(counts, list) or not {10_000, 100_000}.issubset(counts):
        raise RuntimeError("incremental pipeline must retain 10,000 and 100,000-event evidence")
    for count, label in expected:
        measurement = result.get(label)
        if not isinstance(measurement, dict) or any(
            measurement.get(field) != count for field in ("event_count", "source_event_count")
        ):
            raise RuntimeError("incremental pipeline must retain 10,000 and 100,000-event evidence")


def measure_all(checkout: Path) -> dict[str, Any]:
    evidence = verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    prior_path = list(sys.path)
    prior_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "hermes_cli" or name.startswith("hermes_cli.")
    }
    try:
        with tempfile.TemporaryDirectory(prefix="aether-hermes-benchmark-") as temporary:
            source = Path(temporary) / "hermes-source"
            qualified_source = _materialize_qualification_source(evidence.path, source)
            _prioritize_hermes_source(source)
            ten_thousand = measure_reduction(10_000)
            one_hundred_thousand = measure_reduction(100_000)
            callback = measure_callbacks()
            _enforce_performance_budgets(ten_thousand, callback)
            flush = measure_out_of_band_flush()
            incremental_pipeline = measure_incremental_pipeline()
            _require_normative_incremental_evidence(incremental_pipeline)
    finally:
        sys.path[:] = prior_path
        for name in tuple(sys.modules):
            if name == "hermes_cli" or name.startswith("hermes_cli."):
                del sys.modules[name]
        sys.modules.update(prior_modules)
    return {
        "schema_version": 1,
        "contract": contract(),
        "reduction": {
            "mode": "full_reduction",
            "ten_thousand": ten_thousand,
            "one_hundred_thousand": one_hundred_thousand,
        },
        "callback": callback,
        "flush": flush,
        "incremental_pipeline": incremental_pipeline,
        "qualified_source": qualified_source,
    }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    """Atomically retain one raw machine result without rewriting evidence prose."""
    target = path.expanduser().absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(payload))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        if os.name == "posix":
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _extract_validation_results_block(report_text: str) -> dict[str, Any]:
    """Read the single v1 JSON fence embedded in an owner-authored report."""
    report_lines = report_text.splitlines()
    begin_indexes = [
        index for index, line in enumerate(report_lines) if line == VALIDATION_RESULTS_BLOCK_BEGIN
    ]
    end_indexes = [
        index for index, line in enumerate(report_lines) if line == VALIDATION_RESULTS_BLOCK_END
    ]
    if len(begin_indexes) != 1 or len(end_indexes) != 1:
        raise RuntimeError("implementation validation lacks one versioned results block")
    begin, end = begin_indexes[0], end_indexes[0]
    if end <= begin:
        raise RuntimeError("implementation validation results block markers are reversed")
    lines = report_lines[begin + 1 : end]
    if len(lines) < 3 or lines[0].strip() != "```json" or lines[-1].strip() != "```":
        raise RuntimeError("implementation validation results block is not a JSON fence")
    try:
        payload = json.loads("\n".join(lines[1:-1]))
    except json.JSONDecodeError as error:
        raise RuntimeError("implementation validation results block is invalid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError("implementation validation results block must be an object")
    if payload.get("schema_version") != VALIDATION_RESULTS_SCHEMA_VERSION:
        raise RuntimeError("implementation validation results block has unsupported version")
    results = payload.get("results")
    claims = payload.get("claims")
    if (isinstance(results, dict)) == (isinstance(claims, dict)):
        raise RuntimeError(
            "implementation validation results block must contain exactly one of results or claims"
        )
    return payload


def _load_labeled_results(results: dict[str, Path]) -> dict[str, Any]:
    if not results:
        raise ValueError("at least one qualification output is required")
    loaded: dict[str, Any] = {}
    for label, path in sorted(results.items()):
        if _RESULT_LABEL_RE.fullmatch(label) is None:
            raise ValueError("invalid qualification result label")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"qualification output {label} is not readable JSON") from error
        if not isinstance(payload, dict):
            raise RuntimeError(f"qualification output {label} must be a JSON object")
        loaded[label] = payload
    return loaded


def _assert_claim_subset(claimed: Any, actual: Any) -> None:
    """Require every claimed JSON value while ignoring unclaimed runtime evidence."""
    if isinstance(claimed, dict):
        if not isinstance(actual, dict):
            raise RuntimeError("claimed qualification value differs from supplied outputs")
        for key, value in claimed.items():
            if key not in actual:
                raise RuntimeError("claimed qualification value differs from supplied outputs")
            _assert_claim_subset(value, actual[key])
        return
    if isinstance(claimed, list):
        if not isinstance(actual, list) or claimed != actual:
            raise RuntimeError("claimed qualification value differs from supplied outputs")
        return
    if type(claimed) is not type(actual) or claimed != actual:
        raise RuntimeError("claimed qualification value differs from supplied outputs")


def contrast_validation_report(report: Path, results: dict[str, Path]) -> dict[str, Any]:
    """Contrast supplied outputs with a v1 report block; never generate or edit it."""
    try:
        report_bytes = report.read_bytes()
        report_text = report_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise RuntimeError("implementation validation report is not readable UTF-8") from error
    embedded = _extract_validation_results_block(report_text)
    loaded = _load_labeled_results(results)
    actual = {"schema_version": VALIDATION_RESULTS_SCHEMA_VERSION, "results": loaded}
    if "claims" in embedded:
        if set(embedded["claims"]) != set(loaded):
            raise RuntimeError("qualification claim labels do not match supplied outputs")
        _assert_claim_subset(embedded["claims"], loaded)
    elif embedded != actual:
        raise RuntimeError(
            "implementation validation results block does not match supplied qualification outputs"
        )
    actual_bytes = _canonical_json(actual).encode("utf-8")
    return {
        "schema_version": VALIDATION_RESULTS_SCHEMA_VERSION,
        "matched": True,
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "results_sha256": hashlib.sha256(actual_bytes).hexdigest(),
        "result_labels": sorted(actual["results"]),
    }


def _parse_result_arguments(values: Sequence[str]) -> dict[str, Path]:
    results: dict[str, Path] = {}
    for value in values:
        label, separator, raw_path = value.partition("=")
        if not separator or not raw_path or _RESULT_LABEL_RE.fullmatch(label) is None:
            raise ValueError("--result must use a bounded LABEL=PATH value")
        if label in results:
            raise ValueError("duplicate qualification result label")
        results[label] = Path(raw_path)
    return results


def _emit(payload: dict[str, Any], *, json_mode: bool, output: Path | None = None) -> None:
    if output is not None:
        _write_json_artifact(output, payload)
    if json_mode:
        print(_canonical_json(payload))
    else:
        print(json.dumps(payload, sort_keys=True, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract_parser = subparsers.add_parser("contract")
    contract_parser.add_argument("--json", action="store_true")
    checkout_parser = subparsers.add_parser("checkout")
    checkout_parser.add_argument("--path", type=Path, required=True)
    checkout_parser.add_argument("--json", action="store_true")
    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("--checkout", type=Path, required=True)
    test_parser.add_argument("--python", type=Path, default=Path(sys.executable))
    test_parser.add_argument("--output", type=Path)
    test_parser.add_argument("--json", action="store_true")
    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--checkout", type=Path, required=True)
    benchmark_parser.add_argument("--output", type=Path)
    benchmark_parser.add_argument("--json", action="store_true")
    contrast_parser = subparsers.add_parser("contrast-validation")
    contrast_parser.add_argument("--report", type=Path, required=True)
    contrast_parser.add_argument(
        "--result",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        required=True,
    )
    contrast_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "contract":
        payload = contract()
    elif args.command == "checkout":
        payload = checkout_exact(args.path)
    elif args.command == "test":
        payload = run_tests(args.checkout, args.python)
    elif args.command == "benchmark":
        payload = measure_all(args.checkout)
    else:
        try:
            result_inputs = _parse_result_arguments(args.result)
        except ValueError as error:
            raise SystemExit(str(error)) from error
        payload = contrast_validation_report(args.report, result_inputs)
    _emit(payload, json_mode=args.json, output=getattr(args, "output", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
