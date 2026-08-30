"""Supervised durability outside the agent path.

Normative decisions: OBS-D-027, OBS-FR-031, OBS-FR-082.

The Hermes callback appends and returns. It never waits for ``fsync``, because power-loss
durability cannot be guaranteed without potentially stalling the observed agent, and the
accepted priority is non-intrusion plus honest loss visibility. This module owns the
other half of that bargain: a plugin-owned supervised task that flushes periodically,
flushes sooner when a contract-critical fact is pending, and attempts one bounded final
flush during graceful teardown.

It is deliberately dumb. It holds no schema knowledge, cancels only its own task, and
every failure becomes a health counter rather than an exception in the agent loop.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from aether_agents.observation.capture.journal import JournalWriter

__all__ = ["Flusher", "FlusherStats"]

#: Ordinary tool spans may remain unsynced this long; a contract-critical fact does not.
DEFAULT_INTERVAL_S = 5.0
DEFAULT_CRITICAL_INTERVAL_S = 0.25
#: A bounded teardown attempt: graceful unload must not hang a shutting-down runtime.
DEFAULT_TEARDOWN_TIMEOUT_S = 2.0


@dataclass(slots=True)
class FlusherStats:
    """Content-free counters, safe to surface through ``aether doctor``."""

    flushes: int = 0
    critical_flushes: int = 0
    failures: int = 0
    final_flush_attempted: bool = False
    final_flush_succeeded: bool = False


@dataclass
class Flusher:
    """Periodic bounded flush/fsync for one journal writer."""

    writer: JournalWriter
    interval_s: float = DEFAULT_INTERVAL_S
    critical_interval_s: float = DEFAULT_CRITICAL_INTERVAL_S
    teardown_timeout_s: float = DEFAULT_TEARDOWN_TIMEOUT_S
    stats: FlusherStats = field(default_factory=FlusherStats)
    failure_notifier: Callable[[str], None] | None = None

    _task: Any = field(default=None, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    # -- start / stop --------------------------------------------------------------
    def start(self, spawn_task: Callable[[Any], Any] | None = None) -> None:
        """Start supervision.

        ``spawn_task`` is Hermes's ``ctx.spawn_task``. It is used only when an event loop
        actually exists; otherwise a daemon thread supervises the same loop so a
        non-async surface (CLI, cron, worker) still gets durability.
        """
        if self._task is not None or self._thread is not None:
            return
        self._stop.clear()
        if spawn_task is not None and self._event_loop_running():
            self._task = spawn_task(self._run_async())
            return
        self._thread = threading.Thread(
            target=self._run_sync, name="aether-observation-flusher", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Cancel only this plugin's supervised work and attempt one final flush."""
        self._stop.set()
        wake = getattr(self.writer, "wake_flusher", None)
        if callable(wake):
            wake()
        task = self._task
        self._task = None
        if task is not None:
            try:
                task.cancel()
            except Exception:  # noqa: BLE001 - teardown must not raise into Hermes
                pass
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=self.teardown_timeout_s)
        self.final_flush()

    def final_flush(self) -> bool:
        """One bounded final flush during graceful unload. Never raises."""
        self.stats.final_flush_attempted = True
        completed = threading.Event()
        outcome: list[bool] = []

        def run() -> None:
            try:
                outcome.append(bool(self.writer.flush()))
            except Exception:  # noqa: BLE001 - diagnostic is content-free
                outcome.append(False)
            finally:
                completed.set()

        worker = threading.Thread(target=run, name="aether-observation-final-flush", daemon=True)
        worker.start()
        if not completed.wait(max(0.0, self.teardown_timeout_s)):
            self.stats.final_flush_succeeded = False
            self._note_failure("JOURNAL_FINAL_FLUSH_TIMEOUT")
            return False
        succeeded = bool(outcome and outcome[0])
        self.stats.final_flush_succeeded = succeeded
        if not succeeded:
            self._note_failure("JOURNAL_FINAL_FLUSH_FAILED")
        return succeeded

    # -- loops ---------------------------------------------------------------------
    def _tick(self) -> None:
        critical = self.writer.critical_pending
        try:
            succeeded = self.writer.flush()
        except Exception:  # noqa: BLE001 - a flush failure is a counter, never a raise
            self._note_failure("JOURNAL_FLUSH_FAILED")
            return
        if succeeded:
            self.stats.flushes += 1
            if critical:
                self.stats.critical_flushes += 1
        else:
            self._note_failure("JOURNAL_FLUSH_FAILED")

    def _note_failure(self, reason_code: str) -> None:
        self.stats.failures += 1
        if self.failure_notifier is not None:
            try:
                self.failure_notifier(reason_code)
            except Exception:  # noqa: BLE001 - health accounting is fail-open
                pass

    def _sleep_interval(self) -> float:
        return self.critical_interval_s if self.writer.critical_pending else self.interval_s

    def _run_sync(self) -> None:
        while not self._stop.is_set():
            self._wait_for_request(self._sleep_interval())
            if self._stop.is_set():
                break
            self._tick()

    async def _run_async(self) -> None:
        try:
            while not self._stop.is_set():
                await asyncio.to_thread(self._wait_for_request, self._sleep_interval())
                if self._stop.is_set():
                    break
                self._tick()
        except asyncio.CancelledError:  # pragma: no cover - cooperative teardown
            raise

    @staticmethod
    def _event_loop_running() -> bool:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return False
        return True

    def _wait_for_request(self, timeout_s: float) -> bool:
        wait = getattr(self.writer, "wait_for_flush_request", None)
        if callable(wait):
            return bool(wait(timeout_s))
        return self._stop.wait(timeout_s)
