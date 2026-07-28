"""Exact result-envelope and local artifact verification for R8."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .pilot_model import MAX_RESULT_BYTES, PilotError, PilotManifest, PilotTask, resolve_inside

BEGIN = "AETHER_PILOT_RESULT_V1"
END = "END_AETHER_PILOT_RESULT_V1"
_REQUIRED = {
    "pilot_id",
    "task_id",
    "attempt",
    "session_id",
    "status",
    "changed_paths",
    "artifact_hashes",
    "verification",
    "findings",
    "recommendation",
}
_HASH = re.compile(r"^[0-9a-f]{64}$")


def encode_result(**payload: Any) -> str:
    return f"{BEGIN}\n{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n{END}"


def parse_and_verify_result(
    text: str,
    *,
    task: PilotTask,
    manifest: PilotManifest,
    attempt: int,
    session_id: str,
) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode()) > MAX_RESULT_BYTES:
        raise PilotError("invalid result envelope")
    match = re.fullmatch(rf"{BEGIN}\n([^\n]+)\n{END}", text.strip())
    if match is None:
        raise PilotError("invalid result envelope")
    try:
        data = json.loads(match.group(1))
    except (TypeError, json.JSONDecodeError) as exc:
        raise PilotError("invalid result JSON") from exc
    if not isinstance(data, dict) or set(data) != _REQUIRED:
        raise PilotError("invalid result schema")
    if (
        data["pilot_id"] != manifest.pilot_id
        or data["task_id"] != task.task_id
        or data["attempt"] != attempt
        or data["session_id"] != session_id
    ):
        raise PilotError("result binding mismatch")
    if data["status"] not in {"completed", "failed", "correction_required", "accepted"}:
        raise PilotError("invalid result status")
    if data["recommendation"] not in {"accept", "correction_required", "reject"}:
        raise PilotError("invalid result recommendation")
    allowed_pairs = {
        ("completed", "accept"),
        ("accepted", "accept"),
        ("completed", "correction_required"),
        ("correction_required", "correction_required"),
        ("failed", "reject"),
    }
    if (data["status"], data["recommendation"]) not in allowed_pairs:
        raise PilotError("invalid semantic result combination")
    if task.role in {"review", "completion"} and data["changed_paths"]:
        raise PilotError("read-only task reported writes")
    if (
        not isinstance(data["changed_paths"], list)
        or len(data["changed_paths"]) > 128
        or any(not isinstance(path, str) for path in data["changed_paths"])
        or len(set(data["changed_paths"])) != len(data["changed_paths"])
    ):
        raise PilotError("invalid changed paths")
    hashes = data["artifact_hashes"]
    if not isinstance(hashes, dict) or set(hashes) != set(data["changed_paths"]):
        raise PilotError("changed path/hash mismatch")
    if any(
        not isinstance(key, str) or not isinstance(value, str) or not _HASH.fullmatch(value)
        for key, value in hashes.items()
    ):
        raise PilotError("invalid artifact hash")
    if (
        not isinstance(data["verification"], list)
        or len(data["verification"]) > 32
        or any(
            not isinstance(item, dict)
            or set(item) != {"command", "exit_code"}
            or not isinstance(item["command"], str)
            or not 1 <= len(item["command"]) <= 256
            or isinstance(item["exit_code"], bool)
            or not isinstance(item["exit_code"], int)
            for item in data["verification"]
        )
    ):
        raise PilotError("invalid verification evidence")
    if not isinstance(data["findings"], list) or len(data["findings"]) > 64:
        raise PilotError("invalid findings")
    if data["recommendation"] == "accept" and (
        not data["verification"] or any(item["exit_code"] != 0 for item in data["verification"])
    ):
        raise PilotError("successful verification required")
    if data["recommendation"] == "accept" and any(
        isinstance(item, dict) and item.get("blocking") is True for item in data["findings"]
    ):
        raise PilotError("blocking finding cannot be accepted")
    _verify_artifacts(data, task=task, root=Path(manifest.root))
    return data


def _verify_artifacts(data: dict[str, Any], *, task: PilotTask, root: Path) -> None:
    hashes: dict[str, str] = data["artifact_hashes"]
    if task.permission == "write" and not set(task.required_artifacts).issubset(hashes):
        raise PilotError("required artifact missing")
    for relative, expected in hashes.items():
        if not _is_in_scope(relative, task.scopes):
            raise PilotError("artifact outside task scope")
        path = resolve_inside(root, relative, must_exist=True)
        if path.is_symlink() or not path.is_file():
            raise PilotError("invalid artifact")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise PilotError("artifact hash mismatch")


def _is_in_scope(relative: str, scopes: tuple[str, ...]) -> bool:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    for scope in scopes:
        allowed = Path(scope)
        if candidate == allowed:
            return True
        try:
            candidate.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


__all__ = ["BEGIN", "END", "encode_result", "parse_and_verify_result"]
