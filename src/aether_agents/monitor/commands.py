"""``aether monitor`` command surface.

The parser and help text are Hermes-free: ``aether monitor --help`` works even when the
managed Hermes runtime is absent or broken, exactly like the observation and knowledge
commands.  Executing an action tries the current interpreter first and otherwise uses a
validated product-runtime subprocess, because creating or pausing the native cron job
requires the Hermes runtime that the manager interpreter deliberately does not depend on.

The public contract is fixed:

* ``aether monitor status|on|off|history`` with ``--json`` on every action,
* ``history --limit N`` as the only option,
* one JSON envelope ``{"schema_version": "aether.telegram-monitor.v1", "ok", "action",
  "result"|"error"}`` and no credential, destination, provider or model argument.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from aether_agents.monitor.service import (
    ACTION_HISTORY,
    ACTION_OFF,
    ACTION_ON,
    ACTION_STATUS,
    ACTIONS,
    MONITOR_SCHEMA_VERSION,
    MonitorService,
    error_envelope,
)

__all__ = ["build_subparser", "run_monitor"]

#: Explicit private override for the interpreter that owns the Hermes runtime.
RUNTIME_PYTHON_ENV = "AETHER_HERMES_PYTHON"
_RUNTIME_PROBE = "import cron.jobs, hermes_cli.plugins, aether_agents.monitor.runtime"
_RUNTIME_TIMEOUT = 120
_PROBE_TIMEOUT = 60

_HELP = "Control the Aether Telegram Monitor."


def build_subparser(subparsers: Any) -> None:
    """Register the ``monitor`` command family on the public parser."""

    parser = subparsers.add_parser("monitor", help=_HELP)
    children = parser.add_subparsers(dest="monitor_command", required=True)
    for name in ACTIONS:
        child = children.add_parser(name)
        child.add_argument("--json", action="store_true")
        if name == ACTION_HISTORY:
            child.add_argument(
                "--limit",
                type=int,
                default=None,
                help="Maximum interval records to return (1-200).",
            )


def _isolated_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("HERMES_KANBAN_"):
            environment.pop(name, None)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        environment.pop(name, None)
    return environment


def _runtime_python_candidates() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get(RUNTIME_PYTHON_ENV, "").strip()
    if override:
        candidates.append(Path(override).expanduser())
    hermes = shutil.which("hermes")
    if hermes:
        executable = Path(hermes).resolve()
        sibling = "python.exe" if os.name == "nt" else "python3"
        candidates.append(executable.parent / sibling)
        candidates.append(executable.parent / "python")
    candidates.append(Path(sys.executable))
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _probe_runtime(interpreter: Path) -> bool:
    try:
        completed = subprocess.run(
            [str(interpreter), "-c", _RUNTIME_PROBE],
            check=False,
            capture_output=True,
            text=True,
            env=_isolated_environment(),
            timeout=_PROBE_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def runtime_interpreter() -> Path | None:
    """Return the validated product-runtime interpreter, or ``None``."""

    for candidate in _runtime_python_candidates():
        try:
            if not candidate.is_file():
                continue
        except OSError:
            continue
        if _probe_runtime(candidate):
            return candidate
    return None


def _valid_envelope(value: Any, action: str) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("schema_version") != MONITOR_SCHEMA_VERSION:
        return None
    if value.get("action") != action:
        return None
    ok = value.get("ok")
    if not isinstance(ok, bool):
        return None
    if ok:
        result = value.get("result")
        if not isinstance(result, Mapping):
            return None
        return {
            "schema_version": MONITOR_SCHEMA_VERSION,
            "ok": True,
            "action": action,
            "result": dict(result),
        }
    error = value.get("error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("code")
    message = error.get("message")
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    return {
        "schema_version": MONITOR_SCHEMA_VERSION,
        "ok": False,
        "action": action,
        "error": {"code": code, "message": message},
    }


def _run_runtime_subprocess(action: str, limit: int | None) -> dict[str, Any] | None:
    interpreter = runtime_interpreter()
    if interpreter is None:
        return None
    command = [str(interpreter), "-m", "aether_agents.monitor.runtime", "--action", action]
    if limit is not None:
        command.extend(("--limit", str(limit)))
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=_isolated_environment(),
            timeout=_RUNTIME_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode not in (0, 1):
        return None
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except ValueError:
        return None
    return _valid_envelope(payload, action)


def execute_action(action: str, *, limit: int | None = None) -> dict[str, Any]:
    """Execute one control action through the best available runtime boundary."""

    from aether_agents.monitor import runtime as monitor_runtime

    if monitor_runtime.hermes_available():
        envelope = monitor_runtime.execute_action(action, limit=limit)
        validated = _valid_envelope(envelope, action)
        if validated is not None:
            return validated
    subprocess_envelope = _run_runtime_subprocess(action, limit)
    if subprocess_envelope is not None:
        return subprocess_envelope
    if action in (ACTION_STATUS, ACTION_HISTORY):
        # Without a Hermes runtime the durable monitor state is still readable; the
        # native job column is reported as unavailable instead of being guessed.
        fallback = MonitorService().execute(action, limit=limit)
        validated = _valid_envelope(fallback, action)
        if validated is not None:
            return validated
    return error_envelope(
        action,
        "RUNTIME_UNAVAILABLE",
        "the provisioned Hermes runtime is unavailable; the monitor state was not changed",
    )


def _human(action: str, envelope: Mapping[str, Any]) -> str:
    if not envelope.get("ok"):
        error = envelope.get("error") or {}
        return f"error: {error.get('code')}: {error.get('message')}"
    result = envelope.get("result") or {}
    if action == ACTION_STATUS:
        lines = [
            f"Telegram Monitor: {'on' if result.get('enabled') else 'off'}",
            f"  next cut (UTC): {result.get('next_cut_utc')}",
            f"  next cut (local): {result.get('next_cut_local')}",
            f"  timezone: {result.get('timezone')}",
            f"  destination pinned: {bool(result.get('destination_pinned'))}",
        ]
        job = result.get("native_job")
        if isinstance(job, Mapping):
            lines.append(
                f"  native job: {job.get('id')} [{job.get('state')}] {job.get('schedule')}"
            )
        else:
            lines.append("  native job: unavailable")
        gaps = result.get("coverage_gaps") or []
        if gaps:
            lines.append(f"  coverage gaps: {', '.join(str(item) for item in gaps)}")
        last = result.get("last_report")
        if isinstance(last, Mapping):
            lines.append(
                "  last report: "
                f"{last.get('report_id')} cutoff={last.get('cutoff_utc')} "
                f"narrative={last.get('narrative_status')}"
            )
        outcomes = result.get("delivery_outcomes") or {}
        if outcomes:
            summary = ", ".join(f"{key}={value}" for key, value in sorted(outcomes.items()))
            lines.append(f"  delivery outcomes: {summary}")
        return "\n".join(lines)
    if action == ACTION_ON:
        return (
            "Telegram Monitor on"
            f" (job {result.get('native_job', {}).get('id') if isinstance(result.get('native_job'), Mapping) else 'n/a'})"
        )
    if action == ACTION_OFF:
        warning = result.get("warning")
        suffix = f" (warning: {warning})" if warning else ""
        return f"Telegram Monitor off{suffix}"
    reports = result.get("reports") or []
    lines = [f"Telegram Monitor history: {result.get('count')} of limit {result.get('limit')}"]
    for report in reports:
        if isinstance(report, Mapping):
            lines.append(
                f"  {report.get('report_id')} cutoff={report.get('cutoff_utc')} "
                f"narrative={report.get('narrative_status')} "
                f"resolved={report.get('resolved_at_utc')}"
            )
    return "\n".join(lines)


def run_monitor(args: argparse.Namespace) -> int:
    """Execute the parsed ``aether monitor`` command."""

    action = getattr(args, "monitor_command", None)
    limit = getattr(args, "limit", None)
    json_mode = bool(getattr(args, "json", False))
    if not isinstance(action, str) or action not in ACTIONS:
        print("aether: error: a monitor action is required", file=sys.stderr)
        return 2
    envelope = execute_action(action, limit=limit)
    if json_mode:
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True))
    else:
        text = _human(action, envelope)
        target = sys.stdout if envelope.get("ok") else sys.stderr
        print(text, file=target)
    return 0 if envelope.get("ok") else 1
