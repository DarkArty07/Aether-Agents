"""Tests for native query parity, honest transient codes, and corruption fail-closed.

Satisfies:
(e) Under controlled contention the native tool and CLI return fixed codes within bounds
    and succeed once contention clears; settled state returns equivalent brief/summary.
(f) Genuine corruption/privacy failures stay errors with no raw exception, path, or payload leak.
"""

from __future__ import annotations

import argparse
import io
import json
import threading
from pathlib import Path
from typing import Any

import pytest
from observation_helpers import (
    PROJECT_ID,
    TRACE_ID,
    complete_trace,
    project_marker,
)

from aether_agents.commands.observe import run_observe
from aether_agents.observation import brief
from aether_agents.observation.capture.journal import JournalWriter
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.locking import project_lock
from aether_agents.observation.reduce.ingest import IngestReport
from aether_agents.paths import ObservationPaths


def _setup_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, ObservationPaths]:
    state = tmp_path / "state"
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(project_marker(PROJECT_ID), encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    ProjectRegistry().register(PROJECT_ID, project, "parity-fixture")
    paths = ObservationPaths.for_project(PROJECT_ID)
    paths.ensure()
    return project, paths


def _write_trace(paths: ObservationPaths) -> None:
    fixture = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    for ev in fixture.events:
        writer.append(ev)
    writer.close()


def _run_cli_json(
    project: Path, ref: str | None = None, since: str | None = None
) -> tuple[int, dict[str, Any]]:
    args = argparse.Namespace(
        project=str(project),
        ref=ref,
        since=since,
        watch=False,
        json=True,
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run_observe(args, stdout=stdout, stderr=stderr)
    out = stdout.getvalue().strip()
    data = json.loads(out) if out else {}
    return exit_code, data


def test_controlled_lock_contention_and_recovery_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(e) Contention returns AETHER-OBSERVE-BUSY / STATE_BUSY; clears on release."""
    project, paths = _setup_project(tmp_path, monkeypatch)
    _write_trace(paths)

    lock_acquired = threading.Event()
    lock_release = threading.Event()

    def hold_lock() -> None:
        with project_lock(paths, "storage-transition"):
            lock_acquired.set()
            lock_release.wait(timeout=10.0)

    holder = threading.Thread(target=hold_lock, daemon=True)
    holder.start()
    assert lock_acquired.wait(timeout=2.0)

    try:
        # 1. Native tool under contention: returns AETHER-OBSERVE-BUSY
        with pytest.raises(brief.BriefError) as exc_info:
            brief.observe(
                {"action": "status", "project": str(project), "ref": TRACE_ID},
                profile_name="morfeo",
            )
        assert exc_info.value.code == "AETHER-OBSERVE-BUSY"
        assert "maintenance lock busy" in str(exc_info.value)
        # Verify no path or lock details leak
        assert str(paths.root) not in str(exc_info.value)

        # 2. CLI under contention: returns STATE_BUSY, exit code 6
        exit_code, envelope = _run_cli_json(project, ref=TRACE_ID)
        assert exit_code == 6
        assert envelope["result"] == "error"
        assert envelope["errors"][0]["code"] == "STATE_BUSY"
        assert "maintenance lock busy" in envelope["errors"][0]["message"]
        assert str(paths.root) not in envelope["errors"][0]["message"]
    finally:
        lock_release.set()
        holder.join(timeout=2.0)

    # 3. Once contention clears, both succeed with semantic parity
    native_result = brief.observe(
        {"action": "status", "project": str(project), "ref": TRACE_ID},
        profile_name="morfeo",
    )
    assert native_result["state"] == "ready"
    assert native_result["action"] == "status"

    exit_code, cli_envelope = _run_cli_json(project, ref=TRACE_ID)
    assert exit_code == 0
    assert cli_envelope["result"] == "ready"
    cli_summary = cli_envelope["data"]["summary"]

    # Semantic parity
    assert native_result["summary_id"] == cli_summary["summary_id"]
    assert native_result["project_id"] == cli_summary["project_id"]
    assert native_result["trace_id"] == cli_summary["trace_id"]
    assert native_result["completion_state"] == cli_summary["completion_state"]


def test_catchup_incomplete_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(e) Incomplete catch-up returns AETHER-OBSERVE-CATCHUP-INCOMPLETE / CATCHUP_INCOMPLETE."""
    from aether_agents.observation.reduce import ingest as ingest_module

    project, paths = _setup_project(tmp_path, monkeypatch)
    _write_trace(paths)

    def mock_incomplete(*_args: Any, **_kwargs: Any) -> IngestReport:
        return IngestReport(incomplete=True, lock_timed_out=False)

    monkeypatch.setattr(ingest_module, "ingest_pending", mock_incomplete)

    # Native tool
    with pytest.raises(brief.BriefError) as exc_info:
        brief.observe(
            {"action": "status", "project": str(project), "ref": TRACE_ID},
            profile_name="morfeo",
        )
    assert exc_info.value.code == "AETHER-OBSERVE-CATCHUP-INCOMPLETE"
    assert "observation catch-up incomplete" in str(exc_info.value)

    # CLI
    exit_code, envelope = _run_cli_json(project, ref=TRACE_ID)
    assert exit_code == 6
    assert envelope["result"] == "error"
    assert envelope["errors"][0]["code"] == "CATCHUP_INCOMPLETE"
    assert "observation catch-up incomplete" in envelope["errors"][0]["message"]


def test_genuine_corruption_stays_fail_closed_with_no_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(f) Genuine corruption fails closed with no raw exception, path or payload leak."""
    from aether_agents.observation.reduce import ingest as ingest_module

    project, paths = _setup_project(tmp_path, monkeypatch)
    _write_trace(paths)

    # Simulate genuine unrecoverable SQLite corruption
    def mock_corrupt(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("disk I/O error at /internal/private/db.sqlite")

    monkeypatch.setattr(ingest_module, "ingest_pending", mock_corrupt)

    # Native tool
    with pytest.raises(brief.BriefError) as exc_info:
        brief.observe(
            {"action": "status", "project": str(project), "ref": TRACE_ID},
            profile_name="morfeo",
        )
    assert exc_info.value.code == "AETHER-OBSERVE-STATE-UNREADABLE"
    assert "/internal/private" not in str(exc_info.value)
    assert "OSError" not in str(exc_info.value)

    # CLI
    exit_code, envelope = _run_cli_json(project, ref=TRACE_ID)
    assert exit_code == 6
    assert envelope["result"] == "error"
    assert envelope["errors"][0]["code"] == "STATE_UNREADABLE"
    assert "/internal/private" not in envelope["errors"][0]["message"]


def test_project_ref_resolution_and_empty_state_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native tool and CLI have exact parity for unresolved project, missing ref, and empty state."""
    project, paths = _setup_project(tmp_path, monkeypatch)

    # 1. Missing / invalid project
    bogus_project = tmp_path / "bogus"
    with pytest.raises(brief.BriefError) as exc_info:
        brief.observe(
            {"action": "status", "project": str(bogus_project)},
            profile_name="morfeo",
        )
    assert exc_info.value.code == "AETHER-OBSERVE-PROJECT-UNRESOLVED"

    exit_code, envelope = _run_cli_json(bogus_project)
    assert exit_code == 3  # missing prerequisite
    assert envelope["errors"][0]["code"] == "PROJECT_UNRESOLVED"

    # 2. Empty state (project valid, but no trace)
    native_empty = brief.observe(
        {"action": "status", "project": str(project)},
        profile_name="morfeo",
    )
    assert native_empty["state"] == "empty"
    assert native_empty["trace_id"] is None

    exit_code, cli_empty = _run_cli_json(project)
    assert exit_code == 0
    assert cli_empty["data"]["state"] == "empty"
    assert cli_empty["data"]["summary"] is None

    # 3. Non-existent ref specified
    with pytest.raises(brief.BriefError) as exc_info:
        brief.observe(
            {
                "action": "status",
                "project": str(project),
                "ref": "ctr_ffffffffffffffffffffffffffffffff",
            },
            profile_name="morfeo",
        )
    assert exc_info.value.code == "AETHER-OBSERVE-TRACE-NOT-FOUND"

    exit_code, cli_not_found = _run_cli_json(project, ref="ctr_ffffffffffffffffffffffffffffffff")
    assert exit_code == 2  # invalid input
    assert cli_not_found["errors"][0]["code"] == "TRACE_NOT_FOUND"
