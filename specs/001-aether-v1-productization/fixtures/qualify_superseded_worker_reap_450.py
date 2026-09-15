#!/usr/bin/env python3
"""Qualification canary for Aether #450 — a terminal non-current worker must not
outlive its run beside a successor.

The canary drives the real kanban surface (``claim_task``, ``block_task``,
``unblock_task``, ``_dispatch_once_locked``, ``_set_worker_pid``) on a
**disposable board** created under ``--scratch``. It never touches a live board:
``HERMES_HOME``, ``HERMES_KANBAN_DB``, ``HERMES_KANBAN_WORKSPACES_ROOT`` and
``HERMES_KANBAN_BOARD`` are all repointed into the scratch root before any DB
access, and the resolved DB path is asserted to be inside it.

Only the *worker binary* is a stub (a python process that appends to a marker
file inside the task workspace and dies on SIGTERM). Everything else — the
claim bookkeeping, the spawn-time ``(pid, start_time)`` record, the
out-of-band block, the dispatch tick, the reap and the lanes — is the real
code path under test.

Cases
-----
``coexist``
    Reproduce the incident shape: run 1 is claimed, the worker is spawned,
    the task is blocked from outside the worker, unblocked, and a second run
    is claimed and blocked from outside again — which trips the unblock-loop
    breaker, so the second run ends as ``block_loop_detected`` while its
    worker process is alive (this is exactly run 264 in #450). The task is
    then unblocked and a successor dispatch tick is run. Reports whether the
    stale process was still alive at the moment the successor was spawned,
    whether the fix reaped it first, and whether the stale process kept
    writing into the workspace after the successor started.

``current``
    Counter-case: a live worker whose run is *current* is never a candidate,
    no matter how long it has been running (duration alone must not kill live
    work).

Exit code is 0 when the case's expectation for the tree under test matches,
1 otherwise. The JSON verdict is printed and, with ``--json-out``, written.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

BOARD = "canary-450"

WORKER_STUB = '''\
import os
import sys
import time

marker = os.environ["CANARY_MARKER"]
deadline = time.time() + float(os.environ.get("CANARY_LIFETIME_SECONDS", "600"))
pid = os.getpid()
with open(marker, "a", buffering=1) as fh:
    fh.write(f"{pid} start {time.time():.3f}\\n")
    while time.time() < deadline:
        fh.write(f"{pid} tick {time.time():.3f}\\n")
        time.sleep(0.25)
'''


def _log(line: str) -> None:
    print(line, flush=True)


def _pin_scratch(scratch: Path) -> Path:
    """Repoint every kanban env var into ``scratch`` (never a live board)."""
    home = scratch / "home"
    board_db = home / "kanban" / "boards" / BOARD / "kanban.db"
    os.environ["HERMES_HOME"] = str(home)
    os.environ["HERMES_KANBAN_DB"] = str(board_db)
    os.environ["HERMES_KANBAN_WORKSPACES_ROOT"] = str(
        home / "kanban" / "boards" / BOARD / "workspaces"
    )
    os.environ["HERMES_KANBAN_BOARD"] = BOARD
    return board_db


def _assert_scratch_scope(kb, scratch: Path, db_path: Path) -> None:
    live = os.environ.get("CANARY_LIVE_BOARD_DB", "")
    if live and Path(live).resolve() == db_path.resolve():
        raise SystemExit("refusing to run: scratch DB resolved to the live board")
    if not str(db_path.resolve()).startswith(str(scratch.resolve())):
        raise SystemExit(f"refusing to run: DB {db_path} is outside {scratch}")
    _log(f"board db      : {db_path}")
    _log(f"kanban_db     : {kb.__file__}")


def _write_worker_stub(scratch: Path) -> Path:
    stub = scratch / "canary_worker_stub.py"
    stub.write_text(WORKER_STUB, encoding="utf-8")
    return stub


def _spawn_worker(scratch: Path, stub: Path, workspace: Path, marker: Path):
    """Spawn one stand-in worker the way ``_default_spawn`` spawns a real one."""
    env = dict(os.environ)
    env["CANARY_MARKER"] = str(marker)
    env["CANARY_LIFETIME_SECONDS"] = "600"
    return subprocess.Popen(
        [sys.executable, str(stub)],
        cwd=str(workspace),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _kill(proc) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def _marker_lines(marker: Path) -> list[tuple[int, str, float]]:
    if not marker.exists():
        return []
    out = []
    for line in marker.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 3:
            try:
                out.append((int(parts[0]), parts[1], float(parts[2])))
            except ValueError:
                continue
    return out


def _events(kb, conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT kind, payload, created_at FROM task_events WHERE task_id = ? "
        "ORDER BY id",
        (task_id,),
    ).fetchall()
    out = []
    for row in rows:
        try:
            payload = json.loads(row["payload"] or "{}")
        except (TypeError, ValueError):
            payload = {}
        out.append({"kind": row["kind"], "payload": payload,
                    "at": row["created_at"]})
    return out


def _new_task(kb, conn, scratch: Path, title: str) -> tuple[str, Path]:
    workspace = scratch / "ws" / title.replace(" ", "-")
    workspace.mkdir(parents=True, exist_ok=True)
    tid = kb.create_task(
        conn,
        title=title,
        assignee="canary-worker",
        workspace_kind="dir",
        workspace_path=str(workspace),
    )
    with kb.write_txn(conn):
        conn.execute("UPDATE tasks SET status = 'ready' WHERE id = ?", (tid,))
    return tid, workspace


def run_coexist(kb, scratch: Path) -> dict:
    """Reproduce #450, then run the successor tick."""
    stub = _write_worker_stub(scratch)
    marker = scratch / "worker-writes.log"
    report: dict = {"case": "coexist"}
    procs = []

    # The scratch board has no provisioned profiles; the lanes must still
    # consider this card spawnable, exactly as the real board does.
    from hermes_cli import profiles as _profiles
    _profiles.profile_exists = lambda _name: True

    with kb.connect_closing() as conn:
        # ---- task A: the incident's own shape -----------------------------
        # Two out-of-band blocks for the same cause trip the unblock-loop
        # breaker: the run is ended by the board (not by the worker) and the
        # card routes to triage. This is run 264 in #450.
        tid_a, ws_a = _new_task(kb, conn, scratch, "incident shape")
        claimed = kb.claim_task(conn, tid_a)
        assert claimed is not None
        proc_a1 = _spawn_worker(scratch, stub, ws_a, marker)
        procs.append(proc_a1)
        kb._set_worker_pid(conn, tid_a, proc_a1.pid)
        assert kb.block_task(conn, tid_a, reason="first out-of-band block",
                             kind="needs_input")
        assert kb.unblock_task(conn, tid_a)
        claimed = kb.claim_task(conn, tid_a)
        assert claimed is not None
        run_a2 = kb._current_run_id(conn, tid_a)
        proc_a2 = _spawn_worker(scratch, stub, ws_a, marker)
        procs.append(proc_a2)
        kb._set_worker_pid(conn, tid_a, proc_a2.pid)
        time.sleep(2.0)  # the worker is mid-run when the board ends it
        assert kb.block_task(
            conn, tid_a, reason="owner-reserved authority decision required",
            kind="needs_input",
        )
        events_a = _events(kb, conn, tid_a)
        terminal_a = next(
            (e for e in events_a if e["kind"] == "block_loop_detected"), None
        )
        run_a2_row = conn.execute(
            "SELECT status, outcome, ended_at, worker_pid FROM task_runs WHERE id = ?",
            (run_a2,),
        ).fetchone()
        task_a_row = conn.execute(
            "SELECT status, current_run_id, worker_pid FROM tasks WHERE id = ?",
            (tid_a,),
        ).fetchone()
        _log(f"task A       : run={run_a2} pid={proc_a2.pid} "
             f"event={terminal_a['kind'] if terminal_a else None} "
             f"run_status={run_a2_row['status']} task_status={task_a_row['status']}")
        _log(f"identity     : tasks.worker_pid={task_a_row['worker_pid']} "
             f"task_runs.worker_pid={run_a2_row['worker_pid']} "
             f"(cleared by the terminal transition)")
        assert kb._pid_alive(proc_a2.pid), "precondition: stale worker is alive"

        # ---- task B: a successor will be dispatched for it -----------------
        tid_b, ws_b = _new_task(kb, conn, scratch, "successor shape")
        claimed = kb.claim_task(conn, tid_b)
        assert claimed is not None
        run_b1 = kb._current_run_id(conn, tid_b)
        proc_b1 = _spawn_worker(scratch, stub, ws_b, marker)
        procs.append(proc_b1)
        kb._set_worker_pid(conn, tid_b, proc_b1.pid)
        time.sleep(2.0)
        assert kb.block_task(conn, tid_b, reason="out-of-band block",
                             kind="needs_input")
        run_b1_row = conn.execute(
            "SELECT status, ended_at, worker_pid FROM task_runs WHERE id = ?",
            (run_b1,),
        ).fetchone()
        _log(f"task B       : run={run_b1} pid={proc_b1.pid} "
             f"run_status={run_b1_row['status']} "
             f"task_status={kb.get_task(conn, tid_b).status}")
        assert kb._pid_alive(proc_b1.pid), "precondition: stale worker is alive"
        assert kb.unblock_task(conn, tid_b)

        # ---- the successor tick -------------------------------------------
        successor_started_at: list[float] = []
        observed: list[dict] = []
        stale_pids = [proc_a1.pid, proc_a2.pid, proc_b1.pid]

        def _successor_spawn(task, workspace_arg, **kwargs):
            successor_started_at.append(time.time())
            observed.append({
                "task": task.id,
                "at": successor_started_at[-1],
                "stale_alive_at_spawn": {
                    str(pid): kb._pid_alive(pid) for pid in stale_pids
                },
            })
            proc = _spawn_worker(scratch, stub, Path(workspace_arg), marker)
            procs.append(proc)
            return proc.pid

        result = kb._dispatch_once_locked(
            conn,
            max_spawn=1,
            reconcile_orphans=False,
            spawn_fn=_successor_spawn,
            failure_limit=5,
        )
        started_at = successor_started_at[0] if successor_started_at else None
        time.sleep(2.0)  # give a surviving stale worker time to keep writing

        reaped = list(getattr(result, "superseded_reaped", []) or [])
        held = list(getattr(result, "superseded_held", []) or [])
        lines = _marker_lines(marker)
        stale_after = {
            str(pid): len([row for row in lines
                           if row[0] == pid and row[2] > (started_at or 0)])
            for pid in stale_pids
        }
        events_by_task = {
            "A": [e["kind"] for e in _events(kb, conn, tid_a)],
            "B": [e["kind"] for e in _events(kb, conn, tid_b)],
        }
        report.update({
            "task_a": tid_a,
            "task_b": tid_b,
            "run_a2": run_a2,
            "run_b1": run_b1,
            "stale_pids": stale_pids,
            "incident_terminal_event": terminal_a["kind"] if terminal_a else None,
            "incident_run_row": dict(run_a2_row),
            "incident_task_row": dict(task_a_row),
            "successor_spawned": bool(observed),
            "successor_pids": [row[0] for row in result.spawned],
            "stale_alive_at_successor_spawn": (
                observed[0]["stale_alive_at_spawn"] if observed else None
            ),
            "superseded_reaped": reaped,
            "superseded_held": held,
            "stale_alive_after_tick": {
                str(pid): kb._pid_alive(pid) for pid in stale_pids
            },
            "stale_exit_codes": {
                str(proc.pid): proc.poll() for proc in (proc_a1, proc_a2, proc_b1)
            },
            "stale_workspace_writes_after_successor": stale_after,
            "event_kinds_by_task": events_by_task,
            "termination_events": [
                {"task": tid_a, "payload": e["payload"]}
                for e in _events(kb, conn, tid_a)
                if e["kind"] == "superseded_worker_termination"
            ] + [
                {"task": tid_b, "payload": e["payload"]}
                for e in _events(kb, conn, tid_b)
                if e["kind"] == "superseded_worker_termination"
            ],
        })
        _log(f"successor    : spawned={report['successor_pids']}")
        _log(f"stale at spawn: {json.dumps(report['stale_alive_at_successor_spawn'])}")
        _log(f"reap         : {json.dumps(reaped)}")
        _log(f"hold         : {json.dumps(held)}")
        _log(f"event kinds  : A={events_by_task['A']} B={events_by_task['B']}")
        _log(f"stale after  : alive={json.dumps(report['stale_alive_after_tick'])} "
             f"exit_codes={json.dumps(report['stale_exit_codes'])} "
             f"workspace_writes_after_successor="
             f"{json.dumps(report['stale_workspace_writes_after_successor'])}")

    for proc in procs:
        _kill(proc)
    return report


def run_current(kb, scratch: Path, ticks: int = 4, interval: float = 6.0) -> dict:
    """Counter-case: a live worker whose run is current is never reaped."""
    stub = _write_worker_stub(scratch)
    marker = scratch / "worker-writes.log"
    report: dict = {"case": "current"}
    procs = []

    with kb.connect_closing() as conn:
        tid, workspace = _new_task(kb, conn, scratch, "long running task")
        claimed = kb.claim_task(conn, tid)
        assert claimed is not None
        run_id = kb._current_run_id(conn, tid)
        proc = _spawn_worker(scratch, stub, workspace, marker)
        procs.append(proc)
        kb._set_worker_pid(conn, tid, proc.pid)
        start = time.time()
        _log(f"current run  : id={run_id} pid={proc.pid} (no terminal transition)")

        observations = []
        for index in range(ticks):
            result = kb._dispatch_once_locked(
                conn,
                max_spawn=1,
                reconcile_orphans=False,
                spawn_fn=lambda task, workspace_arg, **kwargs: None,
                failure_limit=5,
            )
            observations.append({
                "tick": index + 1,
                "elapsed": round(time.time() - start, 3),
                "reaped": list(getattr(result, "superseded_reaped", []) or []),
                "held": list(getattr(result, "superseded_held", []) or []),
                "alive": kb._pid_alive(proc.pid),
            })
            _log(f"tick {index + 1}       : elapsed={observations[-1]['elapsed']}s "
                 f"reaped={observations[-1]['reaped']} "
                 f"held={observations[-1]['held']} "
                 f"worker_alive={observations[-1]['alive']}")
            if index + 1 < ticks:
                time.sleep(interval)

        events = _events(kb, conn, tid)
        report.update({
            "task_id": tid,
            "run_id": run_id,
            "worker_pid": proc.pid,
            "observations": observations,
            "worker_alive_at_end": kb._pid_alive(proc.pid),
            "worker_exit_code": proc.poll(),
            "event_kinds": [e["kind"] for e in events],
            "age_seconds": round(time.time() - start, 3),
        })
        _log(f"worker alive : {report['worker_alive_at_end']} "
             f"after {report['age_seconds']}s and {ticks} ticks")
        _log(f"event kinds  : {report['event_kinds']}")

    for proc in procs:
        _kill(proc)
    return report


def _judge(kb, report: dict) -> tuple[bool, list[str]]:
    """Return (ok, reasons) for the shape the tested tree must produce."""
    reasons: list[str] = []
    has_fix = hasattr(kb.DispatchResult(), "superseded_reaped")
    report["tree_has_fix"] = has_fix

    if report["case"] == "coexist":
        stale_keys = [str(pid) for pid in report["stale_pids"]]
        alive_at_spawn = report["stale_alive_at_successor_spawn"] or {}
        alive_after = report["stale_alive_after_tick"] or {}
        writes = report["stale_workspace_writes_after_successor"] or {}
        if not report["successor_spawned"]:
            reasons.append("the successor was never spawned")
        if report["incident_terminal_event"] != "block_loop_detected":
            reasons.append(
                "expected the loop-breaker terminal event, got "
                f"{report['incident_terminal_event']!r}"
            )
        if report["incident_run_row"]["ended_at"] is None:
            reasons.append("the incident-shaped run was not durably terminal")
        if report["incident_task_row"]["worker_pid"] is not None:
            reasons.append("task still carried worker_pid after terminalization")
        if has_fix:
            reaped_pids = {
                entry.get("prev_pid") for entry in report["superseded_reaped"]
            }
            missing = sorted(set(report["stale_pids"]) - reaped_pids)
            if missing:
                reasons.append(f"stale workers not reaped: {missing}")
            if any(
                entry.get("terminated") is not True
                for entry in report["superseded_reaped"]
            ):
                reasons.append("a reaped worker was not reported terminated")
            if any(alive_at_spawn.get(key) for key in stale_keys):
                reasons.append("a stale worker was alive when the successor started")
            if any(alive_after.get(key) for key in stale_keys):
                reasons.append("a stale worker survived the tick")
            if any(writes.get(key) for key in stale_keys):
                reasons.append(
                    "a stale worker kept writing after the successor started"
                )
            if len(report["termination_events"]) < len(report["stale_pids"]):
                reasons.append(
                    "expected one durable termination event per stale worker"
                )
        else:
            if not all(alive_at_spawn.get(key) for key in stale_keys):
                reasons.append(
                    "the unfixed tree did not reproduce the coexistence precondition"
                )
            if not any(writes.get(key) for key in stale_keys):
                reasons.append(
                    "the unfixed tree did not keep mutating the workspace "
                    "after the successor started"
                )
            if report["termination_events"]:
                reasons.append("an unfixed tree emitted a termination event")
    elif report["case"] == "current":
        if not report["worker_alive_at_end"]:
            reasons.append("a live current worker was killed")
        if any(row["reaped"] for row in report["observations"]):
            reasons.append("the reap treated a current run as a candidate")
        if any(row["held"] for row in report["observations"]):
            reasons.append("the spawn gate treated a current run as a candidate")
        if "superseded_worker_termination" in report["event_kinds"]:
            reasons.append("a termination event was emitted for a current run")
    else:  # pragma: no cover - argparse restricts the value
        reasons.append(f"unknown case {report['case']!r}")
    return (not reasons, reasons)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("coexist", "current"), required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    scratch = args.scratch.resolve()
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    board_db = _pin_scratch(scratch)
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from hermes_cli import kanban_db as kb  # noqa: E402  (env pinned above)

    kb.init_db()
    _assert_scratch_scope(kb, scratch, kb.kanban_db_path())
    live = os.environ.get("CANARY_LIVE_BOARD_DB")
    if live:
        _log(f"live board    : {live} (untouched)")

    _log(f"case          : {args.case}")
    if args.case == "coexist":
        report = run_coexist(kb, scratch)
    else:
        report = run_current(kb, scratch)

    ok, reasons = _judge(kb, report)
    report["verdict"] = "pass" if ok else "fail"
    report["reasons"] = reasons
    _log(f"verdict       : {report['verdict']}")
    for reason in reasons:
        _log(f"  - {reason}")

    if args.json_out:
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        _log(f"verdict file  : {args.json_out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
