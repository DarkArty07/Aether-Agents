"""M5.4 model-worker liveness gate contracts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts/aether_mcp"
sys.path.insert(0, str(SCRIPTS))

import qualify_m5_model_swarm as qualifier  # noqa: E402

from aether_mcp.orca_provider import ModelWorkerObservation  # noqa: E402


class ProbeProvider:
    def __init__(self, observations: list[ModelWorkerObservation]) -> None:
        self.observations = observations
        self.observe_calls = 0
        self.enter_calls: list[str] = []

    def observe_model_worker(self, _provider_dispatch_id: str) -> ModelWorkerObservation:
        index = min(self.observe_calls, len(self.observations) - 1)
        self.observe_calls += 1
        return self.observations[index]

    def submit_model_worker_enter(self, terminal_id: str) -> object:
        self.enter_calls.append(terminal_id)
        return object()


def observation(
    *,
    source: str = "terminal",
    activity: bool = False,
    idle: bool = False,
    blocked: str | None = None,
) -> ModelWorkerObservation:
    return ModelWorkerObservation(
        source=source,
        activity_observed=activity,
        idle_hint=idle,
        blocked_reason=blocked,
        response_digest="a" * 64,
        response_bytes=123,
    )


def target(tmp_path: Path) -> dict[str, qualifier.ModelWorkerTarget]:
    worktree = tmp_path / "worker"
    worktree.mkdir()
    return {
        "backend": qualifier.ModelWorkerTarget(
            provider_dispatch_id="dispatch_backend",
            terminal_id="term_backend",
            worktree=worktree,
        )
    }


def test_liveness_accepts_initial_working_marker_without_terminal_recovery(tmp_path: Path) -> None:
    targets = target(tmp_path)
    marker = targets["backend"].worktree / "backend/model-result.json"
    marker.parent.mkdir()
    marker.write_text('{"task":"backend","status":"working","started_at_ns":1}', encoding="utf-8")
    provider = ProbeProvider([observation()])

    result = qualifier.wait_model_liveness(
        provider,
        targets,
        timeout=0.05,
        nudge_after=0,
        poll_interval=0.001,
    )

    assert result["backend"]["acknowledged_by"] == "working_marker"
    assert result["backend"]["started_at_ns"] == 1
    assert result["backend"]["submit_recovery_count"] == 0
    assert provider.observe_calls == 0
    assert provider.enter_calls == []


def test_liveness_uses_one_empty_enter_then_accepts_transcript_activity(tmp_path: Path) -> None:
    provider = ProbeProvider(
        [
            observation(idle=True),
            observation(source="transcript", activity=True),
        ]
    )

    result = qualifier.wait_model_liveness(
        provider,
        target(tmp_path),
        timeout=0.1,
        nudge_after=0,
        poll_interval=0.001,
    )

    assert result["backend"]["acknowledged_by"] == "public_transcript"
    assert result["backend"]["submit_recovery_count"] == 1
    assert provider.enter_calls == ["term_backend"]


def test_liveness_fails_immediately_on_public_blocked_reason(tmp_path: Path) -> None:
    provider = ProbeProvider([observation(blocked="auth")])

    with pytest.raises(qualifier.QualificationError, match="ERR_MODEL_TERMINAL_BLOCKED:backend:auth"):
        qualifier.wait_model_liveness(
            provider,
            target(tmp_path),
            timeout=0.1,
            nudge_after=0,
            poll_interval=0.001,
        )

    assert provider.enter_calls == []


def test_liveness_timeout_is_sanitized_and_never_resends_prompt(tmp_path: Path) -> None:
    provider = ProbeProvider([observation()])

    with pytest.raises(qualifier.QualificationError) as caught:
        qualifier.wait_model_liveness(
            provider,
            target(tmp_path),
            timeout=0.01,
            nudge_after=0,
            poll_interval=0.001,
        )

    message = str(caught.value)
    assert "ERR_MODEL_PROMPT_NOT_ACKNOWLEDGED" in message
    assert "SECRET_PROMPT" not in message
    assert provider.enter_calls == []


def test_baseline_allows_only_the_orca_generated_legacy_sentinel() -> None:
    assert qualifier.baseline_runs_admitted([])
    assert qualifier.baseline_runs_admitted([{"id": "run_legacy_local", "legacy": 1}])
    assert not qualifier.baseline_runs_admitted([{"id": "run_other", "legacy": 1}])
    assert not qualifier.baseline_runs_admitted([{"id": "run_legacy_local", "legacy": 0}])
    assert not qualifier.baseline_runs_admitted(
        [
            {"id": "run_legacy_local", "legacy": 1},
            {"id": "run_other", "legacy": 0},
        ]
    )


def test_model_interval_uses_witnessed_start_when_final_marker_omits_it() -> None:
    report, source = qualifier.resolve_model_interval(
        "frontend",
        {"task": "frontend", "status": "passed", "finished_at_ns": 20},
        {"acknowledged_by": "working_marker", "started_at_ns": 10},
    )

    assert source == "initial_working_marker"
    assert report["started_at_ns"] == 10
    assert report["finished_at_ns"] == 20


def test_model_interval_rejects_final_marker_that_contradicts_witnessed_start() -> None:
    with pytest.raises(qualifier.QualificationError, match="frontend timing report is invalid"):
        qualifier.resolve_model_interval(
            "frontend",
            {"task": "frontend", "status": "passed", "started_at_ns": 11, "finished_at_ns": 20},
            {"acknowledged_by": "working_marker", "started_at_ns": 10},
        )


def test_model_interval_requires_final_start_without_marker_witness() -> None:
    with pytest.raises(qualifier.QualificationError, match="backend timing report is invalid"):
        qualifier.resolve_model_interval(
            "backend",
            {"task": "backend", "status": "passed", "finished_at_ns": 20},
            {"acknowledged_by": "public_transcript"},
        )


def test_transcript_worker_read_command_uses_orca_public_limit_flag() -> None:
    command = qualifier.worker_read_command("dispatch_model_1", limit=20_000)

    assert command == (
        "orchestration",
        "worker-read",
        "--dispatch",
        "dispatch_model_1",
        "--source",
        "auto",
        "--limit",
        "20000",
        "--json",
    )
    assert "--chars" not in command
