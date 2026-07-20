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
        else:
            raise ValueError("unknown event kind")
        return self._json(value)

    def rebuild(self, events: list[dict[str, Any]]) -> dict[str, Any]:
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
