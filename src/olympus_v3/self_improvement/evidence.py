"""Deterministic, non-authorizing release-evidence projection."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping

from olympus_v3.self_improvement.ledger import SelfImprovementLedger
from olympus_v3.self_improvement.manifest import CycleManifest

_SIGNAL_PRECEDENCE = ("MINOR_CAPABILITY_SIGNAL", "PATCH_CANDIDATE", "NONE")


def aggregate_next_version_signal(ledger: SelfImprovementLedger) -> str:
    """Aggregate recorded signals without converting evidence into approval."""

    sessions = ledger.sessions()
    if not sessions or any(session["status"] != "finalized" for session in sessions):
        return "REQUIRES_MORE_EVIDENCE"
    signals = {str(session["next_version_signal"]) for session in sessions}
    if "REQUIRES_MORE_EVIDENCE" in signals:
        return "REQUIRES_MORE_EVIDENCE"
    for signal in _SIGNAL_PRECEDENCE:
        if signal in signals:
            return signal
    return "REQUIRES_MORE_EVIDENCE"


def _count_lines(values: Mapping[str, int]) -> list[str]:
    if not values:
        return ["- none: 0"]
    return [f"- {name}: {values[name]}" for name in sorted(values)]


def render_release_evidence(manifest: CycleManifest, ledger: SelfImprovementLedger) -> str:
    """Render a stable markdown projection containing only ledger aggregates."""

    counts = ledger.evidence_counts()
    signal = aggregate_next_version_signal(ledger)
    lines = [
        f"# v{manifest.candidate_version} Self-Improvement Evidence",
        "",
        "## Contract",
        "",
        f"- Candidate: `{manifest.candidate_name}`",
        f"- Manifest digest: `{manifest.digest}`",
        f"- Logical provider: `{manifest.logical_provider}`",
        f"- Next-version signal: `{signal}`",
        "",
        "## Session states",
        "",
        *_count_lines(counts["session_statuses"]),
        "",
        "## Measurements",
        "",
        f"- Tool calls: {counts['tool_calls']}",
        f"- Model calls: {counts['model_calls']}",
        f"- Model calls with unknown route: {counts['model_calls_missing_route']}",
        "",
        "## Coordination outcomes",
        "",
        *_count_lines(counts["coordination_outcomes"]),
        "",
        "## Authority boundary",
        "",
        "This evidence does not approve a merge, tag, release, deployment, or next-minor architecture.",
        "Product-owner approval and the versioned release gates remain required.",
        "",
    ]
    return "\n".join(lines)


def write_release_evidence(manifest: CycleManifest, ledger: SelfImprovementLedger) -> str:
    """Atomically write the deterministic projection to the manifest-approved path."""

    content = render_release_evidence(manifest, ledger)
    destination = manifest.release_evidence_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return content
