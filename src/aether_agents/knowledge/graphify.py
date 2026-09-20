"""A bounded subprocess adapter to the separately installed Graphify component."""

from __future__ import annotations

import contextlib
import contextvars
import json
import os
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .common import KnowledgeError, clean_environment

_CANCEL_EVENT: contextvars.ContextVar[threading.Event | None] = contextvars.ContextVar(
    "aether_graphify_cancel_event", default=None
)


@contextlib.contextmanager
def graphify_cancel_scope(event: threading.Event | None):
    """Make one operation's cancellation visible to copied worker contexts."""
    token = _CANCEL_EVENT.set(event)
    try:
        yield
    finally:
        _CANCEL_EVENT.reset(token)


def _host_interrupt_requested() -> bool:
    """Read the optional Hermes host interrupt without making it a dependency."""
    try:
        from tools.interrupt import is_interrupted  # type: ignore[import-not-found,import-untyped]
    except Exception:
        return False
    try:
        return bool(is_interrupted())
    except Exception:
        return False


def _now() -> float:
    """Monotonic clock for the operation budget (patchable in tests)."""
    from . import semantic

    return semantic._now()


def run_bounded_graphify(
    backend: Any,
    action: str,
    *,
    deadline: float,
    cancel_event: threading.Event | None = None,
    reserve_seconds: float | None = None,
    source_root: Path | None = None,
    graph_path: Path | None = None,
    arguments: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute one Graphify action within the operation-wide budget and shared cancellation."""

    def _operation_timeout(message: str) -> KnowledgeError:
        error = KnowledgeError("TIMEOUT", message)
        error.operation_deadline_timeout = True  # type: ignore[attr-defined]
        return error

    if backend is None:
        raise KnowledgeError("COMPONENT_UNAVAILABLE", "Configure Graphify before graph updates.")

    operation_cancel = cancel_event or _CANCEL_EVENT.get()
    if (operation_cancel is not None and operation_cancel.is_set()) or _host_interrupt_requested():
        if operation_cancel is not None:
            operation_cancel.set()
        raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")

    now = _now()
    remaining = deadline - now
    if remaining <= 0:
        raise _operation_timeout("Operation budget exhausted before Graphify invocation.")

    actual_reserve = reserve_seconds if reserve_seconds is not None else min(5.0, remaining * 0.5)
    timeout = remaining - actual_reserve
    if timeout <= 0:
        raise _operation_timeout("Operation budget exhausted before Graphify invocation.")

    def _operation_budget_exhausted() -> bool:
        """True only when the operation's own remaining time is down to the reserve."""
        return _now() >= deadline - actual_reserve

    call_kwargs: dict[str, Any] = dict(kwargs)
    if source_root is not None:
        call_kwargs["source_root"] = source_root
    if graph_path is not None:
        call_kwargs["graph_path"] = graph_path
    if arguments is not None:
        call_kwargs["arguments"] = arguments

    try:
        result = backend.run(action, timeout=timeout, cancel_event=operation_cancel, **call_kwargs)
    except KnowledgeError as exc:
        # Only a TIMEOUT that consumed this operation's own budget is a deadline. A component
        # timeout while the operation still has time left stays a typed failure, so an
        # independent defect is never relabeled as operation exhaustion.
        if exc.code == "TIMEOUT" and _operation_budget_exhausted():
            exc.operation_deadline_timeout = True  # type: ignore[attr-defined]
        raise
    except TypeError as exc:
        msg = str(exc)
        if "cancel_event" in msg and "timeout" in msg:
            result = backend.run(action, **call_kwargs)
        elif "cancel_event" in msg:
            result = backend.run(action, timeout=timeout, **call_kwargs)
        elif "timeout" in msg:
            result = backend.run(action, cancel_event=operation_cancel, **call_kwargs)
        else:
            raise

    if (operation_cancel is not None and operation_cancel.is_set()) or _host_interrupt_requested():
        if operation_cancel is not None:
            operation_cancel.set()
        raise KnowledgeError("OPERATION_CANCELLED", "Knowledge update was cancelled.")

    if _now() >= deadline:
        raise _operation_timeout("Operation deadline exceeded after Graphify invocation.")

    return result


class GraphifyBackend:
    def __init__(self, python: Path, *, timeout: float = 60.0):
        # Do not resolve a venv interpreter symlink: doing so loses its environment.
        self.python = python.expanduser().absolute()
        self.timeout = min(max(float(timeout), 1.0), 600.0)

    def probe(self) -> dict[str, Any]:
        return self.run("probe")

    def run(
        self,
        action: str,
        *,
        source_root: Path | None = None,
        graph_path: Path | None = None,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        if not self.python.is_file():
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Configure the isolated Graphify component."
            )
        worker = Path(__file__).with_name("graph_worker.py")
        request = {
            "action": action,
            "source_root": str(source_root) if source_root else "",
            "graph_path": str(graph_path) if graph_path else "",
            "arguments": arguments or {},
        }
        encoded = json.dumps(request, ensure_ascii=False).encode("utf-8")
        if len(encoded) > 2_000_000:
            raise KnowledgeError(
                "SCOPE_UNAVAILABLE", "The component request exceeds its byte limit."
            )
        effective_timeout = (
            min(self.timeout, float(timeout)) if timeout is not None else self.timeout
        )
        if effective_timeout <= 0:
            raise KnowledgeError("TIMEOUT", "Graphify exceeded its execution limit.")
        operation_cancel = cancel_event or _CANCEL_EVENT.get()

        def terminate(process: subprocess.Popen[bytes]) -> None:
            """Kill the whole worker group, not only the Python parent."""
            with contextlib.suppress(ProcessLookupError):
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()

        with tempfile.TemporaryDirectory(prefix="aether-graphify-") as scratch:
            home = Path(scratch)
            try:
                process = subprocess.Popen(
                    [str(self.python), "-I", str(worker)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=home,
                    env=clean_environment(home),
                    start_new_session=(os.name == "posix"),
                )
            except OSError as exc:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "The Graphify process could not start."
                ) from exc
            try:
                result_holder: dict[str, Any] = {}

                def communicate() -> None:
                    try:
                        result_holder["value"] = process.communicate(encoded)
                    except BaseException as exc:  # pragma: no cover - defensive transport path
                        result_holder["error"] = exc

                exchange = threading.Thread(target=communicate, daemon=True)
                exchange.start()
                deadline = time.monotonic() + effective_timeout
                while exchange.is_alive():
                    if (
                        operation_cancel is not None and operation_cancel.is_set()
                    ) or _host_interrupt_requested():
                        terminate(process)
                        exchange.join()
                        raise KnowledgeError(
                            "OPERATION_CANCELLED", "Graphify operation was cancelled."
                        )
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        terminate(process)
                        exchange.join()
                        raise KnowledgeError("TIMEOUT", "Graphify exceeded its execution limit.")
                    exchange.join(min(0.025, remaining))
                if "error" in result_holder:
                    error = result_holder["error"]
                    if isinstance(error, subprocess.TimeoutExpired):
                        raise KnowledgeError(
                            "TIMEOUT", "Graphify exceeded its execution limit."
                        ) from error
                    raise error
                stdout, _stderr = result_holder["value"]
            except KnowledgeError:
                raise
            except BaseException:
                # Cancellation, timeout and host interrupts must not leave a detached indexer alive.
                if process.poll() is None:
                    terminate(process)
                with contextlib.suppress(Exception):
                    process.communicate()
                raise
        if len(stdout) > 2_000_000:
            raise KnowledgeError("RESULT_TOO_LARGE", "Graphify returned an oversized result.")
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeError) as exc:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Graphify returned an invalid response."
            ) from exc
        if not isinstance(result, dict) or not result.get("ok") or process.returncode:
            code = "COMPONENT_UNAVAILABLE" if action == "probe" else "INDEX_CORRUPT"
            msg = (
                result.get("error")
                or result.get("message")
                or "Graphify could not complete the requested operation."
                if isinstance(result, dict)
                else "Graphify could not complete the requested operation."
            )
            raise KnowledgeError(code, str(msg))
        if (
            operation_cancel is not None and operation_cancel.is_set()
        ) or _host_interrupt_requested():
            raise KnowledgeError("OPERATION_CANCELLED", "Graphify operation was cancelled.")
        if time.monotonic() >= deadline:
            raise KnowledgeError("TIMEOUT", "Graphify exceeded its execution limit.")
        return result
