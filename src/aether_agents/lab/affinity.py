"""Qualification helpers for the real per-flow Supervisor session lane.

This module does not implement session affinity. Hermes owns the lease, generation,
resume and notification lifecycle. The laboratory only reduces bounded receipts from
that lifecycle to compact evidence and refuses to call an incomplete trace a pass.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

_FLOW_ID_RE = re.compile(r"^aether\.flow\.v1:[0-9a-f]{64}$", re.ASCII)
_SAFE_TEXT_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,256}$")
_INPUT_ROUTES = frozenset({"input", "origin_signal_input"})
_REVISION_ROUTES = frozenset({"revision", "origin_signal_revision"})
_TERMINAL_ROUTES = frozenset({"terminal", "flow_terminal"})
_ROUTES = _INPUT_ROUTES | _REVISION_ROUTES | _TERMINAL_ROUTES
_INTERNAL_ROUTES = _ROUTES | {"suppressed"}


@dataclass(frozen=True, slots=True)
class AffinityQualification:
    """Compact result of the E2E-16 receipt checks."""

    status: str
    reason: str
    facts: dict[str, Any]

    @property
    def qualified(self) -> bool:
        return self.status == "PASS"

    def to_evidence(self) -> dict[str, Any]:
        """Return schema-valid evidence without prompts, paths, or raw output."""
        evidence: dict[str, Any] = {
            "schema_version": "aether.lab.evidence.v1",
            "kind": "run",
            "scenario": "e2e-16",
            "status": self.status,
            "mode": "live-persistent",
            "expected_route": "pipeline",
            "rolling_reliability_counted": False,
            "reason": self.reason,
        }
        if self.facts:
            evidence["affinity"] = dict(self.facts)
        return evidence


def opaque_flow_id(project_id: str, contract_id: str, version: int) -> str:
    """Derive the same portable opaque flow identity as Aether handoff code."""
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id is required")
    if not isinstance(contract_id, str) or not contract_id.strip():
        raise ValueError("contract_id is required")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("version must be a positive integer")
    material = json.dumps(
        [project_id, contract_id, version],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return "aether.flow.v1:" + hashlib.sha256(material).hexdigest()


_SQLITE_FIXTURE_WORKER = r'''
import json
import os
import sqlite3
import sys

database, mode, flow_id, session_id = sys.argv[1:]
with sqlite3.connect(database, timeout=10) as connection:
    if mode == "first":
        connection.execute(
            "CREATE TABLE affinity (flow_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, generation INTEGER NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE observations (kind TEXT NOT NULL, pid INTEGER NOT NULL, session_id TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO affinity VALUES (?, ?, 1)", (flow_id, session_id)
        )
        connection.execute(
            "INSERT INTO observations VALUES (?, ?, ?)", ("initial", os.getpid(), session_id)
        )
    elif mode == "resume":
        row = connection.execute(
            "SELECT session_id, generation FROM affinity WHERE flow_id = ?", (flow_id,)
        ).fetchone()
        if row is None or row[0] != session_id:
            raise SystemExit("resume lost the durable session")
        connection.execute(
            "UPDATE affinity SET generation = 2 WHERE flow_id = ? AND generation = 1",
            (flow_id,),
        )
        connection.execute(
            "INSERT INTO observations VALUES (?, ?, ?)", ("resume", os.getpid(), row[0])
        )
    elif mode == "stale":
        updated = connection.execute(
            "UPDATE affinity SET generation = 3 WHERE flow_id = ? AND generation = 1",
            (flow_id,),
        ).rowcount
        if updated:
            raise SystemExit("stale generation unexpectedly wrote")
        connection.execute(
            "INSERT INTO observations VALUES (?, ?, ?)", ("stale-rejected", os.getpid(), session_id)
        )
    else:
        raise SystemExit("unknown fixture phase")
print(json.dumps({"pid": os.getpid(), "mode": mode}, sort_keys=True))
'''


def run_sqlite_boundary_fixture(root: Path) -> dict[str, Any]:
    """Exercise durable session fencing across three real child processes.

    This is a deterministic integration fixture for the laboratory tests. It is
    intentionally not a substitute for the live Hermes lane: the live lane must
    still provide its own receipts before qualification can return ``PASS``.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    database = root / "affinity.sqlite3"
    flow_id = opaque_flow_id("fixture-project", "oc_fixture", 1)
    session_id = "fixture-supervisor-session"
    process_ids: list[int] = []
    for mode in ("first", "resume", "stale"):
        completed = subprocess.run(
            [sys.executable, "-c", _SQLITE_FIXTURE_WORKER, str(database), mode, flow_id, session_id],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"SQLite affinity fixture phase failed: {mode}")
        try:
            process_ids.append(int(json.loads(completed.stdout)["pid"]))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"SQLite affinity fixture emitted invalid receipt: {mode}") from exc

    with sqlite3.connect(database) as connection:
        affinity_row = connection.execute(
            "SELECT session_id, generation FROM affinity WHERE flow_id = ?", (flow_id,)
        ).fetchone()
        observations = connection.execute(
            "SELECT kind, pid, session_id FROM observations ORDER BY rowid"
        ).fetchall()
    return {
        "flow_id": flow_id,
        "process_count": len(process_ids),
        "process_ids": process_ids,
        "same_session": bool(affinity_row and affinity_row[0] == session_id),
        "generation": affinity_row[1] if affinity_row else None,
        "prior_tool_evidence_observed": bool(
            observations and observations[0][0] == "initial"
        ),
        "stale_generation_rejected": bool(
            observations and observations[-1][0] == "stale-rejected"
        ),
    }


def _text(receipts: Mapping[str, Any], key: str) -> str | None:
    value = receipts.get(key)
    if not isinstance(value, str) or _SAFE_TEXT_RE.fullmatch(value.strip()) is None:
        return None
    return value.strip()


def _observed_session(receipts: Mapping[str, Any], key: str) -> str | None:
    value = _text(receipts, key)
    if value is None or value.casefold() == "unavailable":
        return None
    return value


def _boolean(receipts: Mapping[str, Any], key: str) -> bool:
    return receipts.get(key) is True


def _exit_code(receipts: Mapping[str, Any], key: str) -> int | None:
    value = receipts.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _route(receipts: Mapping[str, Any], key: str) -> str:
    value = receipts.get(key)
    return value if isinstance(value, str) and value in _INTERNAL_ROUTES else "invalid"


def _session_ids(receipts: Mapping[str, Any]) -> list[str]:
    values = receipts.get("implementer_session_ids", [])
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if candidate.casefold() == "unavailable":
            continue
        if _SAFE_TEXT_RE.fullmatch(candidate):
            result.append(candidate)
    return result


def _facts(receipts: Mapping[str, Any]) -> dict[str, Any]:
    first = _observed_session(receipts, "first_supervisor_session_id")
    resumed = _observed_session(receipts, "resumed_supervisor_session_id")
    implementers = _session_ids(receipts)
    flow_candidate = _text(receipts, "flow_id")
    flow_id = flow_candidate if flow_candidate and _FLOW_ID_RE.fullmatch(flow_candidate) else None
    first_exit = _exit_code(receipts, "first_process_exit")
    resumed_exit = _exit_code(receipts, "resumed_process_exit")
    session_reused = bool(first and resumed and first == resumed)
    return {
        "flow_id": flow_id or "unavailable",
        "first_supervisor_session_id": first or "unavailable",
        "resumed_supervisor_session_id": resumed or "unavailable",
        "implementer_session_ids": implementers,
        "other_flow_session_id": _observed_session(receipts, "other_flow_session_id") or "unavailable",
        "other_project_session_id": _observed_session(receipts, "other_project_session_id") or "unavailable",
        "other_role_session_id": (
            _observed_session(receipts, "other_role_session_id")
            or _observed_session(receipts, "other_profile_session_id")
            or "unavailable"
        ),
        "first_process_exit": first_exit if first_exit is not None else 125,
        "resumed_process_exit": resumed_exit if resumed_exit is not None else 125,
        "resume_invoked": _boolean(receipts, "resume_invoked"),
        "workspace_pinned": _boolean(receipts, "workspace_pinned"),
        "prior_tool_evidence_observed": _boolean(receipts, "prior_tool_evidence_observed"),
        "reconstructed_input_sent": (
            receipts.get("reconstructed_input_sent") is True
            or receipts.get("reconstructed_prompt_sent") is True
        ),
        "stale_generation_rejected": _boolean(receipts, "stale_generation_rejected"),
        "implementer_fresh": _boolean(receipts, "implementer_fresh"),
        "internal_milestone_route": _route(receipts, "internal_milestone_route"),
        "terminal_route": _route(receipts, "terminal_route"),
        "input_route": _route(receipts, "input_route"),
        "revision_route": _route(receipts, "revision_route"),
        "flow_binding_ok": _boolean(receipts, "flow_binding_ok"),
        "project_binding_ok": _boolean(receipts, "project_binding_ok"),
        "role_binding_ok": _boolean(receipts, "role_binding_ok")
        or _boolean(receipts, "profile_binding_ok"),
        "other_flow_rejected": _boolean(receipts, "other_flow_rejected"),
        "other_project_rejected": _boolean(receipts, "other_project_rejected"),
        "other_role_rejected": _boolean(receipts, "other_role_rejected"),
        "native_control_lifecycle_observed": _boolean(
            receipts, "native_control_lifecycle_observed"
        ),
        "review_integration_observed": _boolean(receipts, "review_integration_observed"),
        "reclaim_succeeded": _boolean(receipts, "reclaim_succeeded"),
        "session_reused": session_reused,
    }


def qualify_affinity_evidence(receipts: Mapping[str, Any]) -> AffinityQualification:
    """Apply the complete E2E-16 acceptance rule to bounded runtime receipts."""
    if not isinstance(receipts, Mapping):
        raise TypeError("affinity receipts must be a mapping")
    if receipts.get("runtime_available") is not True:
        return AffinityQualification(
            "CAPABILITY_WALL",
            "runtime_prerequisite_unavailable",
            {},
        )

    facts = _facts(receipts)
    required = {
        "flow_id": bool(_FLOW_ID_RE.fullmatch(facts["flow_id"])),
        "same_session": facts["session_reused"],
        "distinct_implementer": bool(facts["implementer_session_ids"])
        and len(set(facts["implementer_session_ids"])) == len(facts["implementer_session_ids"])
        and not {
            facts["first_supervisor_session_id"],
            facts["resumed_supervisor_session_id"],
        }.intersection(facts["implementer_session_ids"]),
        "distinct_other_sessions": (
            all(
                facts[key] != "unavailable"
                for key in (
                    "other_flow_session_id",
                    "other_project_session_id",
                    "other_role_session_id",
                )
            )
            and len(
                {
                    facts["other_flow_session_id"],
                    facts["other_project_session_id"],
                    facts["other_role_session_id"],
                }
            )
            == 3
            and not {
                facts["first_supervisor_session_id"],
                facts["resumed_supervisor_session_id"],
            }.intersection(
                {
                    facts["other_flow_session_id"],
                    facts["other_project_session_id"],
                    facts["other_role_session_id"],
                }
            )
        ),
        "resume": facts["resume_invoked"],
        "workspace": facts["workspace_pinned"],
        "prior_evidence": facts["prior_tool_evidence_observed"],
        "no_reconstructed_input": not facts["reconstructed_input_sent"],
        "stale_generation": facts["stale_generation_rejected"],
        "implementer_fresh": facts["implementer_fresh"],
        "bindings": facts["flow_binding_ok"]
        and facts["project_binding_ok"]
        and facts["role_binding_ok"],
        "other_flow": facts["other_flow_rejected"],
        "other_project": facts["other_project_rejected"],
        "other_role": facts["other_role_rejected"],
        "native_control_lifecycle": facts["native_control_lifecycle_observed"],
        "review_integration": facts["review_integration_observed"],
        "reclaim": facts["reclaim_succeeded"],
        "internal_suppressed": facts["internal_milestone_route"] == "suppressed",
        "terminal_routed": facts["terminal_route"] in _TERMINAL_ROUTES,
        "input_routed": facts["input_route"] in _INPUT_ROUTES,
        "revision_routed": facts["revision_route"] in _REVISION_ROUTES,
        "process_boundary": facts["first_process_exit"] != 125
        and facts["resumed_process_exit"] != 125,
    }
    facts["controls_passed"] = all(required.values())
    status = "PASS" if facts["controls_passed"] else "FAIL"
    reason = "same_session_resume_verified" if status == "PASS" else "affinity_acceptance_failed"
    return AffinityQualification(status, reason, facts)
