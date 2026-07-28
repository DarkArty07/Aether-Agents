"""Run an explicit, disposable v0.19.5 bounded Harmonia lifecycle demo."""
from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from olympus_v3.acp_manager import ACPManager
from olympus_v3.config_loader import CoordinationConfig
from olympus_v3.coordination.contracts import TaskState
from olympus_v3.coordination.harmonia_runtime import ProjectRuntimeRegistry, StaticCoordinationKeyProvider
from olympus_v3.coordination.harmonia_service import HarmoniaService

POLICY_ID = "lowest-canonical-eligible-task-id"


class DeterministicACPManager:
    """Local ACP seam with the same artifact/poll/cleanup surface as ACPManager."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.sessions: set[str] = set()
        self.statuses: dict[str, str] = {}
        self.calls: list[tuple[str, str]] = []

    async def spawn_agent(self, *, agent_name: str, session_id: str, project_root: str) -> str:
        self.calls.append(("spawn", agent_name))
        self.sessions.add(session_id)
        return session_id

    async def send_message(self, session_id: str, prompt: str) -> None:
        self.calls.append(("send", session_id))
        payload = json.loads(prompt)
        artifact = payload["result_artifact"]
        document = artifact["document"]
        document["result"] = {"answer": "deterministic demo result"}
        destination = self.root / artifact["relative_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(document, sort_keys=True, separators=(",", ":")))
        self.statuses[session_id] = "completed"

    async def poll(self, session_id: str) -> dict[str, str]:
        return {"status": self.statuses.get(session_id, "working")}

    async def close(self, session_id: str, *, terminal_status: str) -> None:
        self.calls.append(("close", session_id))

    async def cleanup_persisted(self, session_id: str, *, terminal_status: str, project_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            raise RuntimeError("cleanup requested for unknown session")
        self.sessions.discard(session_id)
        return {
            "status": terminal_status,
            "project_id": project_id,
            "acp_session_id": session_id,
            "survivors": {
                "logical_manager_session": False,
                "acp_mapping": False,
                "prompt_task": False,
                "pid_session_mapping": False,
            },
        }


def bounded_payload(
    root: Path,
    source_worker: str,
    candidate_worker_a: str,
    candidate_worker_b: str,
    *,
    response_delivery: bool = False,
) -> dict[str, Any]:
    permissions = ["read", "return_evidence"] if response_delivery else ["read"]
    return {
        "action": "start", "project_root": str(root), "request_id": "bounded-demo",
        "plan_revision": 1, "snapshot_digest": "sha256:" + "a" * 64,
        "contract": {
            "objective": "isolated bounded selection demo", "expected_outcome": "one candidate completes",
            "included_scopes": ["demo"], "excluded_scopes": [], "time_seconds": 60,
            "model_budget": 10, "qa_reserve": 1, "recovery_reserve": 1, "escalation_conditions": ["demo"],
            "selection_policy_id": POLICY_ID, "selection_candidate_task_ids": ["task-c", "task-b"],
            "tasks": [
                {"task_id": "task-a", "worker": source_worker, "worker_permissions": permissions, "prerequisites": []},
                {"task_id": "task-c", "worker": candidate_worker_a, "worker_permissions": permissions, "prerequisites": ["task-a"]},
                {"task_id": "task-b", "worker": candidate_worker_b, "worker_permissions": permissions, "prerequisites": ["task-a"]},
            ],
        },
    }


def _event_payloads(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [json.loads(event["payload"]) for event in events if event["kind"] == kind]


async def run_demo(
    root: Path,
    manager: Any,
    workers: tuple[str, str, str],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    home = root / ".aether-home"
    config = CoordinationConfig(True, "legacy", ("legacy", "kernel-single-task"), (str(root),), 1)
    registry = ProjectRuntimeRegistry(home, manager, StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32))
    service = HarmoniaService(aether_home=home, config=config, registry=registry, discovered_workers=set(workers))
    try:
        started = await service.handle(bounded_payload(
            root,
            *workers,
            response_delivery=not isinstance(manager, DeterministicACPManager),
        ))
        if not started.get("ok"):
            raise RuntimeError(f"bounded start failed: {started}")
        context = await registry.get_or_create(root)
        run_id = started["run_id"]
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            source_state = context.runtime.task(run_id, "task-a").state
            selected_state = context.runtime.task(run_id, "task-b").state
            if source_state is TaskState.CLOSED and selected_state is TaskState.CLOSED:
                break
            await asyncio.sleep(0.01 if isinstance(manager, DeterministicACPManager) else 0.25)
        else:
            raise TimeoutError("bounded demo did not close source and selected tasks before timeout")
        status = await service.handle({"action": "status", "project_root": str(root), "run_id": run_id})
        events = context.ledger.events()
        selection = _event_payloads(events, "task.selection.committed")
        selected_dispatches = [p for p in _event_payloads(events, "dispatch.staged") if p.get("task_id") == "task-b"]
        unselected_dispatches = [p for p in _event_payloads(events, "dispatch.staged") if p.get("task_id") == "task-c"]
        selected_attempts = [p for p in _event_payloads(events, "attempt.started") if p.get("task_id") == "task-b"]
        unselected_attempts = [p for p in _event_payloads(events, "attempt.started") if p.get("task_id") == "task-c"]
        cleanups = _event_payloads(events, "cleanup.completed")
        # The candidate IDs, not worker order, determine the selected task.
        expected_worker = next(p["resolved_worker_id"] for p in selection) if selection else None
        source_closed = context.runtime.task(run_id, "task-a").state is TaskState.CLOSED
        selected_closed = context.runtime.task(run_id, "task-b").state is TaskState.CLOSED
        sessions = getattr(manager, "sessions", None)
        durable_cleanup_complete = len(cleanups) == 2 and source_closed and selected_closed
        result = {
            "committed": len(selection) == 1,
            "source_task_id": "task-a", "candidate_task_ids": ["task-c", "task-b"],
            "selected_task_id": selection[0].get("selected_task_id") if selection else None,
            "resolved_worker": expected_worker,
            "selection_events": len(selection), "selected_dispatches": len(selected_dispatches),
            "unselected_dispatches": len(unselected_dispatches), "selected_attempts": len(selected_attempts),
            "unselected_attempts": len(unselected_attempts), "selection": status.get("selection"),
            "cleanup_completed": len(cleanups),
            "sessions_remaining": len(sessions) if sessions is not None else None,
            "no_survivors": durable_cleanup_complete and (sessions is None or len(sessions) == 0),
            "source_closed": source_closed,
            "selected_closed": selected_closed,
            "adapter_sends": len([call for call in getattr(manager, "calls", ()) if call[0] == "send"]),
        }
        invariants = {
            "committed": result["committed"], "selected_task_id": result["selected_task_id"] == "task-b",
            "selected_dispatches": result["selected_dispatches"] == 1, "unselected_dispatches": result["unselected_dispatches"] == 0,
            "selected_attempts": result["selected_attempts"] == 1, "unselected_attempts": result["unselected_attempts"] == 0,
            "cleanup_completed": result["cleanup_completed"] == 2,
            "source_closed": result["source_closed"],
            "selected_closed": result["selected_closed"],
            "no_survivors": result["no_survivors"], "status_committed": bool(result["selection"] and result["selection"].get("committed")),
        }
        result["invariants"] = invariants
        if not all(invariants.values()):
            raise RuntimeError(json.dumps(result, sort_keys=True))
        return result
    finally:
        await registry.close()


def _real_manager(root: Path) -> tuple[Any, Any]:
    from olympus_v3.config_loader import DaimonProfile, load_config
    from olympus_v3.db import OlympusDB
    config = load_config()
    if set(config.daimons) == {"home"} and (config.aether_home / "home" / "profiles").is_dir():
        config.profiles_dir = config.aether_home / "home" / "profiles"
        config.daimons = {
            path.name: DaimonProfile(path.name, path, (path / "config.yaml").exists(), (path / "SOUL.md").exists())
            for path in sorted(config.profiles_dir.iterdir()) if path.is_dir()
        }
    config.db_path = root / "olympus.db"
    database = OlympusDB(config.db_path)
    return ACPManager(config.profiles_dir, database), database


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--mode", choices=("fake", "real-acp-manager"), default="fake")
    value.add_argument("--confirm-isolated-demo", action="store_true")
    value.add_argument("--confirm-real-acp-dispatch", action="store_true")
    value.add_argument("--source-worker", default="hefesto")
    value.add_argument("--candidate-worker-a", default="ictinus")
    value.add_argument("--candidate-worker-b", default="daedalus")
    value.add_argument("--timeout-seconds", type=float, default=600.0)
    return value


def main() -> int:
    args = parser().parse_args()
    if not args.confirm_isolated_demo:
        parser().error("refusing to run: pass --confirm-isolated-demo")
    if args.mode == "real-acp-manager" and not args.confirm_real_acp_dispatch:
        parser().error("refusing real dispatch: pass --confirm-real-acp-dispatch")
    with tempfile.TemporaryDirectory(prefix="harmonia-v0195-demo-") as directory:
        root = Path(directory) / "project"
        root.mkdir()
        if args.mode == "fake":
            result = asyncio.run(run_demo(
                root,
                DeterministicACPManager(root),
                (args.source_worker, args.candidate_worker_a, args.candidate_worker_b),
                timeout_seconds=args.timeout_seconds,
            ))
        else:
            manager, database = _real_manager(root)
            async def real_run() -> dict[str, Any]:
                await database.connect()
                try:
                    return await run_demo(
                        root,
                        manager,
                        (args.source_worker, args.candidate_worker_a, args.candidate_worker_b),
                        timeout_seconds=args.timeout_seconds,
                    )
                finally:
                    await database.close()
            result = asyncio.run(real_run())
        result.update({"mode": args.mode, "isolated_root": str(root)})
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
