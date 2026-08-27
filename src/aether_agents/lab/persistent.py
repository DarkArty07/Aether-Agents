"""Persistent Morfeo qualification primitives.

The one-shot runner is intentionally never accepted as proof of persistent wake.  This
module evaluates only bounded receipt metadata and can launch an explicitly supplied
native command under PTY for a separate, owner-authorized live probe.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class PersistentProbeResult:
    status: str
    reason: str
    native_surface: str
    same_session: bool
    native_same_session_wake: bool
    durable_report: bool
    owner_messages: int

    @property
    def qualified(self) -> bool:
        return self.status == "PASS"

    def to_evidence(self) -> dict[str, Any]:
        return {
            "schema_version": "aether.lab.evidence.v1",
            "kind": "persistent",
            "status": self.status,
            "mode": "live-persistent",
            "continuation_source": "native",
            "reason": self.reason,
            "native_same_session_wake": self.native_same_session_wake,
            "durable_report": self.durable_report,
            "owner_messages": self.owner_messages,
            "same_session": self.same_session,
        }


def qualify_persistent_evidence(receipts: Mapping[str, Any]) -> PersistentProbeResult:
    """Apply the strict E2E-15 proof rule to safe native receipt metadata."""
    source = str(receipts.get("continuation_source", "native"))
    surface = str(receipts.get("native_surface", "cli"))
    owner_messages = receipts.get("owner_messages", 0)
    if not isinstance(owner_messages, int) or isinstance(owner_messages, bool):
        owner_messages = 0
    if source in {"harness", "one-shot"}:
        return PersistentProbeResult(
            "CAPABILITY_WALL", "one_shot_continuation_non_qualifying", surface, False,
            False, False, owner_messages,
        )
    session_id = receipts.get("session_id")
    wake_session_id = receipts.get("wake_session_id", session_id)
    same_session = isinstance(session_id, str) and session_id == wake_session_id
    native_wake = receipts.get("native_board_event") is True
    durable_report = receipts.get("durable_report") is True
    if not native_wake:
        reason = "native_same_session_wake_unobserved"
    elif not same_session or owner_messages != 1 or not durable_report:
        reason = "same_session_or_owner_message_requirement_failed"
    else:
        return PersistentProbeResult(
            "PASS", "native_same_session_wake_verified", surface, True,
            True, True, owner_messages,
        )
    return PersistentProbeResult(
        "CAPABILITY_WALL", reason, surface, same_session, native_wake,
        durable_report, owner_messages,
    )


def run_persistent_session(
    argv: Sequence[str],
    *,
    owner_message: str,
    timeout_seconds: float = 120.0,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run a supplied native Hermes surface under PTY without claiming wake.

    The function intentionally returns a capability-wall receipt.  Native event/session
    reconciliation is a runtime-specific probe result, not inferred from PTY output.
    """
    if not argv:
        raise ValueError("native surface command is required")
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [str(item) for item in argv],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=cwd,
        env=os.environ.copy(),
        close_fds=True,
    )
    os.close(slave)
    started = time.monotonic()
    try:
        os.write(master, owner_message.encode("utf-8") + b"\n")
        while process.poll() is None and time.monotonic() - started < timeout_seconds:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    os.read(master, 4096)
                except OSError:
                    break
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
    finally:
        os.close(master)
    result = qualify_persistent_evidence(
        {
            "continuation_source": "native",
            "native_surface": Path(str(argv[0])).name,
            "native_board_event": False,
            "durable_report": False,
            "owner_messages": 1,
            "session_id": None,
        }
    )
    return result.to_evidence()


# Explicit aliases keep the Python-level API discoverable without introducing another
# CLI or service surface.
persistent_session_probe = qualify_persistent_evidence
probe_persistent_session = qualify_persistent_evidence
persistent_session_run = run_persistent_session
