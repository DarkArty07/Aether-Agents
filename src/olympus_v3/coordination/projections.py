"""Deterministic, fail-closed projection reduction."""

from __future__ import annotations

import json
from typing import Any


class ProjectionReducer:
    def __init__(self, *, version: str = "1") -> None:
        if not isinstance(version, str) or not version.strip():
            raise ValueError("invalid reducer version")
        self.version = version

    @staticmethod
    def _json(value: Any) -> Any:
        try:
            return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("nondeterministic or non-JSON projection") from exc

    def reduce(self, current: Any, kind: str, payload: Any) -> Any:
        if not isinstance(kind, str):
            raise ValueError("unknown event kind")
        if kind in {"state.set", "contract.advance"}:
            value = payload
        elif kind == "state.patch":
            if not isinstance(current, dict) or not isinstance(payload, dict):
                raise ValueError("state.patch requires objects")
            value = {**current, **payload}
        elif kind == "outbox.poison":
            value = {"poison": payload}
        elif kind in {
            "budget.reserved",
            "budget.committed",
            "budget.spent",
            "budget.released",
            "budget.retry_admitted",
            "budget.retry_task",
            "budget.replan_task",
        }:
            value = {**(current or {}), **payload}
        elif kind in {
            "run.created",
            "task.created",
            "task.released",
            "task.admitted",
            "task.ready",
            "task.dispatched",
            "attempt.started",
            "session.bound",
            "dispatch.staged",
            "dispatch.unknown",
            "cancel.intent",
            "attempt.orphaned",
            "attempt.superseded",
            "observation.accepted",
            "reconciliation.completed",
            "runtime.terminal.observed",
            "cleanup.requested",
            "cleanup.completed",
            "cleanup.unknown",
            "evidence.receipt.recorded",
            "close.requested",
        }:
            if kind in {
                "dispatch.staged",
                "dispatch.unknown",
                "cancel.intent",
                "observation.accepted",
                "reconciliation.completed",
                "runtime.terminal.observed",
                "cleanup.requested",
                "cleanup.completed",
                "cleanup.unknown",
                "evidence.receipt.recorded",
            }:
                value = {**(current or {}), **payload}
            else:
                from .workflow import reduce_workflow_projection

                value = reduce_workflow_projection(current, kind, payload)

        else:
            raise ValueError("unknown event kind")
        return self._json(value)

    def rebuild(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        from .budget import validate_budget_history
        from .workflow import validate_workflow_history

        runs, _, _, _ = validate_workflow_history(events)
        validate_budget_history(events, runs=runs)
        result: dict[str, Any] = {}
        last: dict[str, int] = {}
        for event in events:
            aggregate = event["aggregate"]
            version = int(event["version"])
            if version != last.get(aggregate, 0) + 1:
                raise ValueError("aggregate sequence mismatch")
            result[aggregate] = self.reduce(result.get(aggregate), event["kind"], json.loads(event["payload"]))
            last[aggregate] = version
        return result


__all__ = ["ProjectionReducer"]
