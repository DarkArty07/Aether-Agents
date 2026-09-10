#!/usr/bin/env python3
"""Qualify the Aether Telegram Monitor with a deterministic, offline-safe default.

The default lane is deterministic.  It exercises the shipped control parser, the
plugin registration surface, the packaged pre-check resource and the private monitor
state over disposable roots, and it proves by construction that it never imports a
native Hermes module, never calls a model and never invokes the Telegram sender.  It
therefore performs no external effect and can run anywhere.

``--live`` adds the provisioned qualification: it resolves the already provisioned
Morfeo runtime, enables the single owned native hourly job, waits for real wall-clock
hourly boundaries, and records due/cut/collection/narration/acknowledgment times plus
private message identifiers in the operator-selected output file outside Git.  Live
mode is bounded, restores the synthetic scope and the previous enablement, never kills
or restarts an agent, and never accepts a token, destination, provider or model input:
it uses only the existing configured destination and the existing model route.

The public summary contains revisions, timings, counts, case results and the qualified
scope only.  Private handles stay in ``--output``.  Telegram Bot API acceptance is
recorded as acceptance, never as proof that a human read the message.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aether_agents.monitor import commands as monitor_commands  # noqa: E402
from aether_agents.monitor import hermes_plugin  # noqa: E402
from aether_agents.monitor import runtime as monitor_runtime  # noqa: E402
from aether_agents.monitor.service import (  # noqa: E402
    ACTION_HISTORY,
    ACTION_OFF,
    ACTION_ON,
    ACTION_STATUS,
    ACTIONS,
    MONITOR_SCHEMA_VERSION,
    MonitorService,
)
from aether_agents.monitor.store import MonitorStore  # noqa: E402

SCHEMA_VERSION = "aether.telegram-monitor.qualification.v1"
DEFAULT_WAIT_HOURLY_BOUNDARIES = 2
MAX_WAIT_HOURLY_BOUNDARIES = 24
PRECHECK_RESOURCE = "resources/monitor/precheck.py"
NARRATION_RESOURCE = "resources/monitor/narration-context.md"
MONITOR_PLUGIN_ID = "aether-telegram-monitor"
MONITOR_PLUGIN_MODULE = "aether_agents.monitor.hermes_plugin"

#: Options that would introduce external identity or credentials; never accepted.
FORBIDDEN_OPTIONS = (
    "--token",
    "--bot-token",
    "--chat-id",
    "--chat",
    "--destination",
    "--recipient",
    "--provider",
    "--model",
    "--api-key",
    "--credential",
    "--credentials",
    "--session",
    "--profile",
)

#: Modules whose presence proves that a native Hermes boundary was touched.
NATIVE_MODULES = ("cron", "hermes_cli", "gateway", "hermes_constants", "tools.registry")

#: Slop added after the requested boundaries before the live wait fails closed.
BOUNDARY_SLOP = timedelta(minutes=30)


class QualificationError(RuntimeError):
    """A bounded qualification failure with a stable public code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _candidate_revision() -> str:
    """Return the candidate Git revision, or ``unknown`` outside a checkout."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _record(
    records: list[dict[str, Any]],
    check: str,
    status: str,
    detail: str,
) -> None:
    if status not in {"pass", "fail", "skip"}:
        raise ValueError(f"invalid check status: {status}")
    records.append({"check": check, "status": status, "detail": detail})


# ---------------------------------------------------------------------------
# Offline deterministic lane
# ---------------------------------------------------------------------------


def _check_cli_surface() -> tuple[str, str]:
    """The public parser exposes exactly the fixed monitor surface, Hermes-free."""

    from aether_agents.cli import _build_parser

    parser = _build_parser()
    monitor = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction) and "monitor" in action.choices:
            monitor = action.choices["monitor"]
    if monitor is None:
        return "fail", "the public parser exposes no monitor command family"
    children = None
    for action in monitor._actions:
        if isinstance(action, argparse._SubParsersAction):
            children = action.choices
    if children is None or tuple(children) != ACTIONS:
        return "fail", f"monitor actions are {None if children is None else tuple(children)}"
    for name, child in children.items():
        options = {
            option
            for action in child._actions
            for option in action.option_strings
            if option not in {"-h", "--help"}
        }
        expected = {"--json"} if name != ACTION_HISTORY else {"--json", "--limit"}
        if options != expected:
            return "fail", f"monitor {name} options are {sorted(options)}"
    leaked = sorted(
        option
        for action in parser._actions
        for option in action.option_strings
        if option in FORBIDDEN_OPTIONS
    )
    if leaked:
        return "fail", f"the parser mentions external-identity options: {leaked}"
    if "cron" in sys.modules or "hermes_cli" in sys.modules:
        return "fail", "building the parser imported a native Hermes module"
    return "pass", "aether monitor status|on|off|history with --json and history --limit"


def _check_plugin_surface() -> tuple[str, str]:
    """The plugin registers exactly two tools, three hooks and a Morfeo-only opt-in."""

    class Context:
        profile_name = "morfeo"

        def __init__(self) -> None:
            self.tools: list[dict[str, Any]] = []
            self.hooks: dict[str, list[Any]] = {}

        def get_config(self, key: str, default: Any = None) -> Any:
            return {"enabled": True, "language": "Spanish"}.get(key, default)

        def register_tool(self, **kwargs: Any) -> None:
            self.tools.append(dict(kwargs))

        def register_hook(self, name: str, callback: Any) -> None:
            self.hooks.setdefault(name, []).append(callback)

    context = Context()
    hermes_plugin.register(context)
    registered = {(tool["name"], tool["toolset"]) for tool in context.tools}
    expected = {
        (monitor_runtime.CONTROL_TOOL, monitor_runtime.CONTROL_TOOLSET),
        (monitor_runtime.REPORTER_TOOL, monitor_runtime.REPORTER_TOOLSET),
    }
    if registered != expected:
        return "fail", f"registered tools are {sorted(registered)}"
    hooks = sorted(context.hooks)
    if hooks != ["on_session_end", "post_llm_call", "post_tool_call"]:
        return "fail", f"registered hooks are {hooks}"
    for profile, enabled in (("implementer", True), ("supervisor", True), ("morfeo", False)):
        other = Context()
        object.__setattr__(other, "profile_name", profile)
        other.get_config = lambda key, default=None, _enabled=enabled: {  # type: ignore[method-assign]
            "enabled": _enabled
        }.get(key, default)
        hermes_plugin.register(other)
        if other.tools:
            return "fail", f"the monitor registers tools for {profile} enabled={enabled}"
    return "pass", "aether_monitor + aether_monitor_report_snapshot, Morfeo-only opt-in"


def _check_entry_point() -> tuple[str, str]:
    """Exactly one monitor entry point is declared, and no second name claims it."""

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entries = project["project"]["entry-points"]["hermes_agent.plugins"]
    matches = [name for name, module in entries.items() if "monitor" in module]
    if matches != [MONITOR_PLUGIN_ID]:
        return "fail", f"monitor entry points are {matches}"
    if entries[MONITOR_PLUGIN_ID] != MONITOR_PLUGIN_MODULE:
        return "fail", f"{MONITOR_PLUGIN_ID} points at {entries[MONITOR_PLUGIN_ID]}"
    return "pass", "exactly one aether-telegram-monitor entry point"


def _check_packaged_resources() -> tuple[str, str]:
    """The packaged pre-check and narration context ship byte-equal to source."""

    resources = ROOT / "src" / "aether_agents"
    precheck = resources / PRECHECK_RESOURCE
    narration = resources / NARRATION_RESOURCE
    for path in (precheck, narration):
        if not path.is_file():
            return "fail", f"packaged resource is missing: {path.relative_to(ROOT)}"
    marker = "from aether_agents.monitor.runtime import main_precheck"
    if marker not in precheck.read_text(encoding="utf-8"):
        return "fail", "the packaged pre-check does not call the shipped runtime"
    if not narration.read_text(encoding="utf-8").strip():
        return "fail", "the packaged narration context is empty"
    return "pass", "packaged pre-check and narration context are present and wired"


def _check_control_service(workspace: Path) -> tuple[str, str]:
    """The shipped control service keeps its envelope over a disposable state root."""

    store = MonitorStore(state_root=workspace / "state")
    store.configure(
        native_job_id="job-qualification-1",
        profile_binding="morfeo",
        destination_ref="telegram-home-" + "0" * 64,
        timezone_name="UTC",
    )
    service = MonitorService(store=store, native=None, timezone_name="UTC")
    status = service.execute(ACTION_STATUS)
    if not status.get("ok") or status.get("schema_version") != MONITOR_SCHEMA_VERSION:
        return "fail", "monitor status did not return the fixed envelope"
    if status["result"]["native_job"] is not None:
        return "fail", "a Hermes-free status claimed a native job"
    history = service.execute(ACTION_HISTORY, limit=3)
    if history.get("result") != {"limit": 3, "count": 0, "reports": []}:
        return "fail", f"empty history is {history.get('result')}"
    invalid = service.execute(ACTION_HISTORY, limit=500)
    if invalid.get("ok") is not False or invalid["error"]["code"] != "INVALID_LIMIT":
        return "fail", "an out-of-range history limit was not rejected"
    enabled = store.get_settings().enabled
    if enabled:
        return "fail", "the control check left the disposable monitor enabled"
    if store.state_root == Path(os.path.expanduser("~")):
        return "fail", "the control check used the operator home as state root"
    return "pass", "status/history/invalid-limit envelopes over a disposable state root"


def _check_precheck_resource(workspace: Path) -> tuple[str, str]:
    """The packaged pre-check is silent (no model) for a disabled monitor."""

    state_root = workspace / "precheck-state"
    state_root.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT / "src"),
        "XDG_STATE_HOME": str(state_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": os.environ.get("HOME", ""),
    }
    probe = (
        "import json, sys\n"
        "from aether_agents.monitor.runtime import main_precheck\n"
        "main_precheck()\n"
        "loaded = sorted(\n"
        "    name for name in sys.modules\n"
        "    if name.split('.')[0] in {'cron', 'hermes_cli', 'gateway', 'hermes_constants'}\n"
        ")\n"
        "print(json.dumps({'loaded': loaded}))\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "src" / "aether_agents" / PRECHECK_RESOURCE)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return "fail", f"the packaged pre-check did not run: {type(error).__name__}"
    if completed.returncode != 0:
        return "fail", "the packaged pre-check exited non-zero for a disabled monitor"
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return "fail", "the packaged pre-check printed no wake gate"
    try:
        gate = json.loads(lines[-1])
    except ValueError:
        return "fail", "the packaged pre-check printed no parsable wake gate"
    if gate.get("wakeAgent") is not False:
        return "fail", f"a disabled monitor emitted the wake gate {gate}"
    probe_run = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    if probe_run.returncode != 0:
        return "fail", "the shipped pre-check runtime could not be imported"
    try:
        loaded = json.loads(probe_run.stdout.strip().splitlines()[-1]).get("loaded")
    except (ValueError, IndexError):
        return "fail", "the pre-check probe returned no module report"
    if loaded:
        return "fail", f"the shipped pre-check runtime imported {loaded}"
    return "pass", 'disabled monitor emits {"wakeAgent": false} with no native import'


def _check_harness_options() -> tuple[str, str]:
    """The harness itself accepts no token, destination, provider or model input."""

    parser = _build_parser()
    options = sorted(
        option
        for action in parser._actions
        for option in action.option_strings
        if option not in {"-h", "--help"}
    )
    expected = ["--json", "--live", "--output", "--wait-hourly-boundaries"]
    if options != expected:
        return "fail", f"harness options are {options}"
    leaked = sorted(option for option in options if option in FORBIDDEN_OPTIONS)
    if leaked:
        return "fail", f"the harness accepts external-identity options: {leaked}"
    defaults = {action.dest: action.default for action in parser._actions}
    if defaults.get("wait_hourly_boundaries") != DEFAULT_WAIT_HOURLY_BOUNDARIES:
        return "fail", "the default hourly-boundary count changed"
    return "pass", "--live/--json/--output/--wait-hourly-boundaries, no external identity"


def _live_state_fingerprint() -> dict[str, Any]:
    """Fingerprint the operator's durable monitor state without creating it."""

    try:
        import aether_agents.paths as paths

        root = paths.state_root()
    except Exception:
        return {}
    watched = (
        root / "monitor" / "monitor.sqlite3",
        root / "monitor" / "monitor.sqlite3-wal",
        root / "projects" / "registry.json",
    )
    fingerprint: dict[str, Any] = {}
    for path in watched:
        try:
            stat = path.stat()
        except OSError:
            continue
        fingerprint[str(path)] = (stat.st_size, int(stat.st_mtime_ns))
    return fingerprint


def _check_live_state_untouched(before: Mapping[str, Any]) -> tuple[str, str]:
    """The offline lane did not write the operator's durable monitor state."""

    after = _live_state_fingerprint()
    if after != dict(before):
        return "fail", "the offline lane changed the operator's durable monitor state"
    if not before:
        return "pass", "no operator monitor state exists to disturb (disposable roots used)"
    return "pass", f"the operator's durable monitor state is byte-identical ({len(before)} files)"


def _check_no_external_effects(modules_before: frozenset[str]) -> tuple[str, str]:
    """No native Hermes or Telegram transport module entered this process."""

    loaded = sorted(
        name
        for name in set(sys.modules) - set(modules_before)
        if name.split(".")[0] in NATIVE_MODULES
    )
    if loaded:
        return "fail", f"the offline lane imported {loaded}"
    return "pass", "no native Hermes or transport module was imported"


def run_offline(workspace: Path) -> dict[str, Any]:
    """Run the deterministic lane and return the qualification summary."""

    modules_before = frozenset(sys.modules)
    live_state_before = _live_state_fingerprint()
    records: list[dict[str, Any]] = []
    checks: Sequence[tuple[str, Callable[[], tuple[str, str]]]] = (
        ("harness-options", _check_harness_options),
        ("cli-surface", _check_cli_surface),
        ("plugin-surface", _check_plugin_surface),
        ("plugin-entry-point", _check_entry_point),
        ("packaged-resources", _check_packaged_resources),
        ("control-service", lambda: _check_control_service(workspace)),
        ("packaged-precheck", lambda: _check_precheck_resource(workspace)),
        ("no-external-effects", lambda: _check_no_external_effects(modules_before)),
        ("live-state-untouched", lambda: _check_live_state_untouched(live_state_before)),
    )
    for check, run in checks:
        try:
            status, detail = run()
        except Exception as error:  # A failed check is a result, not a crash.
            status, detail = "fail", f"{type(error).__name__}: {error}"
        _record(records, check, status, detail)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "offline",
        "candidate_revision": _candidate_revision(),
        "started_at_utc": _utc_text(_utc_now()),
        "checks": records,
        "external_effects": {"model_calls": 0, "telegram_sends": 0},
        "qualified_scope": [
            "deterministic control surface, plugin registration and packaging",
            "packaged pre-check idle gate without a native Hermes import",
        ],
        "unqualified_scope": [
            "real provisioned model narration and Telegram delivery",
            "two real native wall-clock hourly boundaries and the live idle skip",
            "native cron activation of this installation",
        ],
        "notes": [
            "Live qualification is owned by MON-INT and requires --live with --output.",
            "Telegram Bot API acceptance is not proof that a human read a message.",
        ],
    }


# ---------------------------------------------------------------------------
# Live provisioned lane (bounded; owned by MON-INT)
# ---------------------------------------------------------------------------


def _control(action: str, *, limit: int | None = None) -> dict[str, Any]:
    """Execute one control action through the shipped validated boundary."""

    envelope = monitor_commands.execute_action(action, limit=limit)
    if not isinstance(envelope, dict) or envelope.get("schema_version") != MONITOR_SCHEMA_VERSION:
        raise QualificationError("control-envelope", f"monitor {action} returned no envelope")
    if not envelope.get("ok"):
        error = envelope.get("error") or {}
        raise QualificationError(
            str(error.get("code") or "control-failed"),
            str(error.get("message") or f"monitor {action} failed"),
        )
    return envelope


def _runtime_python() -> Path:
    interpreter = monitor_commands.runtime_interpreter()
    if interpreter is None:
        raise QualificationError(
            "runtime-unavailable",
            "no provisioned Morfeo runtime interpreter could be resolved; "
            "set AETHER_HERMES_PYTHON for this installation",
        )
    return interpreter


def _runtime_execute(interpreter: Path, body: str, *, timeout: int = 300) -> dict[str, Any]:
    """Run a bounded JSON probe inside the provisioned runtime interpreter."""

    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for name in ("HERMES_HOME", "XDG_STATE_HOME", "AETHER_HERMES_PYTHON", "HERMES_TIMEZONE"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    completed = subprocess.run(
        [str(interpreter), "-c", body],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=timeout,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or not lines:
        detail = completed.stderr.strip().splitlines()
        raise QualificationError(
            "runtime-probe-failed",
            f"the runtime probe failed ({detail[-1] if detail else 'no output'})",
        )
    try:
        payload = json.loads(lines[-1])
    except ValueError as error:
        raise QualificationError(
            "runtime-probe-failed", "the runtime probe returned no JSON"
        ) from error
    if not isinstance(payload, dict):
        raise QualificationError("runtime-probe-failed", "the runtime probe returned no object")
    return payload


_BOARD_DDL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    project_id TEXT,
    session_id TEXT,
    created_at REAL,
    started_at REAL,
    completed_at REAL,
    workspace_path TEXT,
    current_run_id INTEGER,
    session_affinity TEXT,
    block_kind TEXT,
    last_heartbeat_at REAL,
    max_runtime_seconds INTEGER,
    result TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS task_links (parent_id TEXT NOT NULL, child_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY,
    task_id TEXT,
    status TEXT,
    outcome TEXT,
    started_at REAL,
    ended_at REAL,
    last_heartbeat_at REAL,
    summary TEXT,
    error TEXT,
    profile TEXT
);
CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY,
    task_id TEXT,
    run_id INTEGER,
    kind TEXT,
    payload TEXT,
    created_at REAL
);
"""

_SESSION_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    display_name TEXT,
    cwd TEXT,
    git_repo_root TEXT,
    started_at REAL,
    ended_at REAL,
    last_activity_at REAL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp REAL
);
"""

_SCOPE_PROBE = r"""
import json
import sqlite3
from pathlib import Path

scope = Path(SCOPE_ROOT)
hermes = Path(HERMES_HOME)
state = Path(STATE_ROOT)
payload = {"projects": [], "boards": [], "registry": [], "errors": []}

_BOARD_SCHEMA = json.loads(BOARD_SCHEMA_JSON)
_SESSION_SCHEMA = json.loads(SESSION_SCHEMA_JSON)

try:
    from aether_agents.observation.context import ProjectRegistry
    from hermes_cli import projects_db

    registry = ProjectRegistry(state)
    connection = sqlite3.connect(projects_db.projects_db_path())
    try:
        connection.executescript(
            "CREATE TABLE IF NOT EXISTS projects ("
            " id TEXT PRIMARY KEY, slug TEXT NOT NULL, name TEXT NOT NULL,"
            " primary_path TEXT, archived INTEGER NOT NULL DEFAULT 0);"
            "CREATE TABLE IF NOT EXISTS project_folders ("
            " project_id TEXT, path TEXT, label TEXT, is_primary INTEGER, added_at TEXT);"
        )
    except sqlite3.Error as error:
        payload["errors"].append(f"native-projects-schema: {error}")
    sessions_path = hermes / "state.db"
    sessions = sqlite3.connect(sessions_path)
    sessions.executescript(_SESSION_SCHEMA)
    for entry in json.loads(SCOPE_MANIFEST):
        project_id = entry["project_id"]
        native_id = entry["native_project_id"]
        project_root = Path(entry["path"])
        if not registry.register(project_id, project_root, entry["name"], native_id):
            payload["errors"].append(f"registry-register: {project_id}")
        existing = projects_db.find_by_primary_path(connection, str(project_root))
        if existing is not None:
            native_id = existing.id
        else:
            native_id = projects_db.create_project(
                connection,
                name=entry["name"],
                primary_path=str(project_root),
                board_slug=entry["board_slug"],
            )
        payload["projects"].append(
            {"project_id": project_id, "native_project_id": native_id, "path": str(project_root)}
        )
        payload["registry"].append(project_id)
        for session in entry["sessions"]:
            sessions.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session["id"],
                    session["source"],
                    session["title"],
                    session["title"],
                    str(project_root),
                    str(project_root),
                    session["started_at"],
                    session["ended_at"],
                    session["last_activity_at"],
                ),
            )
        board_dir = hermes / "kanban" / "boards" / entry["board_slug"]
        board_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(
            json.dumps(
                {
                    "slug": entry["board_slug"],
                    "name": entry["name"],
                    "project_id": native_id,
                    "default_workdir": str(project_root.resolve()),
                    "aether_project_id": project_id,
                    "aether_contract_id": entry["contract_id"],
                    "aether_contract_version": 1,
                }
            ),
            encoding="utf-8",
        )
        board_db = board_dir / "kanban.db"
        board = sqlite3.connect(board_db)
        board.executescript(_BOARD_SCHEMA)
        board.executemany(
            "INSERT OR REPLACE INTO tasks (id, title, status, project_id, session_id,"
            " created_at, started_at, completed_at, workspace_path, current_run_id,"
            " session_affinity, last_heartbeat_at, max_runtime_seconds) VALUES"
            " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    entry["root_task_id"],
                    entry["root_title"],
                    entry["root_status"],
                    native_id,
                    entry["origin_session"],
                    entry["created_at"],
                    entry["created_at"],
                    entry["root_completed_at"],
                    str(project_root),
                    1,
                    json.dumps({"flow_id": entry["flow_id"]}),
                    entry["created_at"],
                    3600,
                ),
                (
                    entry["child_task_id"],
                    entry["child_title"],
                    entry["child_status"],
                    native_id,
                    entry["origin_session"],
                    entry["created_at"],
                    entry["created_at"],
                    None,
                    str(project_root),
                    2,
                    json.dumps({"flow_id": entry["flow_id"]}),
                    entry["created_at"],
                    3600,
                ),
            ],
        )
        board.execute(
            "INSERT OR REPLACE INTO task_links (parent_id, child_id) VALUES (?, ?)",
            (entry["root_task_id"], entry["child_task_id"]),
        )
        board.execute(
            "INSERT OR REPLACE INTO task_runs (id, task_id, status, outcome, started_at,"
            " ended_at, last_heartbeat_at, summary, error, profile) VALUES"
            " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                entry["root_task_id"],
                "completed",
                "completed",
                entry["created_at"],
                entry["created_at"] + 60,
                entry["created_at"] + 60,
                entry["short_result"],
                None,
                "implementer",
            ),
        )
        board.commit()
        board.close()
        payload["boards"].append(entry["board_slug"])
    sessions.commit()
    sessions.close()
    connection.commit()
    connection.close()
except Exception as error:  # surfaced to the operator, never swallowed
    payload["errors"].append(f"{type(error).__name__}: {error}")
print(json.dumps(payload))
"""


def _scope_manifest(scope_root: Path, stamp: str) -> list[dict[str, Any]]:
    """Build the honest synthetic scope manifest for two labelled projects."""

    manifest: list[dict[str, Any]] = []
    now = _utc_now()
    created = now.timestamp()
    for index, letter in enumerate(("A", "B"), start=1):
        project_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"aether-monitor-qualification-{stamp}-{letter}")
        )
        contract_id = (
            f"oc_{uuid.uuid5(uuid.NAMESPACE_URL, 'contract-' + stamp + '-' + letter).hex[:16]}"
        )
        project_root = scope_root / "projects" / f"synthetic-{letter.lower()}"
        board_slug = f"oc-{project_id.replace('-', '')}-{contract_id[3:]}-v1"
        manifest.append(
            {
                "letter": letter,
                "project_id": project_id,
                "name": f"Aether Telegram Monitor qualification (synthetic {letter})",
                "path": str(project_root),
                "contract_id": contract_id,
                "contract_title": f"Synthetic qualification objective {letter}",
                "board_slug": board_slug,
                "flow_id": f"flow-qualification-{stamp}-{letter}",
                "origin_session": f"qualification-origin-{stamp}-{letter}",
                "origin_title": f"Synthetic qualification origin session {letter}",
                "finalizer_session": f"qualification-finalizer-{stamp}-{letter}",
                "root_task_id": f"t_{uuid.uuid5(uuid.NAMESPACE_URL, 'root-' + stamp + letter).hex[:8]}",
                "child_task_id": f"t_{uuid.uuid5(uuid.NAMESPACE_URL, 'child-' + stamp + letter).hex[:8]}",
                "root_title": f"[synthetic] qualification root {letter}",
                "child_title": f"[synthetic] qualification work {letter}",
                "child_status": "running" if letter == "A" else "done",
                "root_status": "running",
                "created_at": created,
                "root_completed_at": None,
                "short_result": "synthetic qualification result (no private data)",
                "sessions": [
                    {
                        "id": f"qualification-origin-{stamp}-{letter}",
                        "source": "tui",
                        "title": f"Synthetic qualification origin session {letter}",
                        "started_at": created,
                        "ended_at": None,
                        "last_activity_at": created,
                    },
                    {
                        "id": f"qualification-finalizer-{stamp}-{letter}",
                        "source": "tui",
                        "title": f"Synthetic qualification finalizer session {letter}",
                        "started_at": created,
                        "ended_at": created + 60,
                        "last_activity_at": created + 60,
                    },
                ],
                "direct_session": f"qualification-direct-{stamp}",
            }
        )
    return manifest


def _write_scope_projects(scope_root: Path, manifest: Sequence[dict[str, Any]]) -> None:
    """Materialize the synthetic project markers, contracts and Git roots."""

    for entry in manifest:
        project_root = Path(entry["path"])
        project_root.mkdir(parents=True, exist_ok=True)
        (project_root / ".aether").mkdir(parents=True, exist_ok=True)
        (project_root / ".aether" / "project.toml").write_text(
            "\n".join(
                (
                    "schema_version = 1",
                    f'project_id = "{entry["project_id"]}"',
                    f'name = "{entry["name"]}"',
                    'initialized_by = "1.0.0"',
                    'forge = "local"',
                    'contract_root = "specs"',
                    "",
                )
            ),
            encoding="utf-8",
        )
        contract_dir = project_root / ".aether" / "objective-contracts" / entry["contract_id"]
        contract_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "artifact_type": "aether.objective-contract.v1",
            "project_id": entry["project_id"],
            "contract_id": entry["contract_id"],
            "version": 1,
            "status": "final",
            "title": entry["contract_title"],
            "created_at_utc": _utc_text(_utc_now()),
            "created_at_local": _utc_text(_utc_now()),
            "finalized_at_utc": _utc_text(_utc_now()),
            "finalized_at_local": _utc_text(_utc_now()),
            "author_profile": "morfeo",
            "created_in_session": entry["origin_session"],
            "finalized_in_session": entry["finalizer_session"],
            "supersedes": None,
            "change_reason": None,
            "observation_trace_id": None,
        }
        lines = ["---"] + [f"{key}: {json.dumps(value)}" for key, value in metadata.items()]
        lines += [
            "---",
            "",
            f"# Objective Contract: {entry['contract_title']}",
            "",
            "synthetic",
            "",
        ]
        (contract_dir / "v1.md").write_text("\n".join(lines), encoding="utf-8")
        (project_root / "README.md").write_text(
            f"# {entry['name']}\n\nSynthetic qualification fixture created by\n"
            "`scripts/qualify_telegram_monitor.py --live`; removed on exit.\n",
            encoding="utf-8",
        )
        _git(project_root, "init", "-q")
        _git(project_root, "add", ".")
        _git(project_root, "commit", "-qm", "Create synthetic monitor qualification project")


def _git(root: Path, *arguments: str) -> None:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Aether monitor qualification",
            "-c",
            "user.email=qualification@example.invalid",
            *arguments,
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git failed"
        raise QualificationError("scope-git", f"synthetic scope git command failed: {detail}")


def _scope_prepare(interpreter: Path, scope_root: Path, stamp: str) -> dict[str, Any]:
    manifest = _scope_manifest(scope_root, stamp)
    _write_scope_projects(scope_root, manifest)
    body = (
        f"SCOPE_ROOT = {str(scope_root)!r}\n"
        f"HERMES_HOME = {str(monitor_runtime.hermes_home())!r}\n"
        f"STATE_ROOT = {str(MonitorStore().state_root)!r}\n"
        f"BOARD_SCHEMA_JSON = {json.dumps(_BOARD_DDL)!r}\n"
        f"SESSION_SCHEMA_JSON = {json.dumps(_SESSION_DDL)!r}\n"
        f"SCOPE_MANIFEST = {json.dumps(json.dumps(manifest))!r}\n" + _SCOPE_PROBE
    )
    payload = _runtime_execute(interpreter, body)
    if payload.get("errors"):
        raise QualificationError("scope-create", f"synthetic scope failed: {payload['errors']}")
    return {
        "manifest": manifest,
        "projects": payload.get("projects", []),
        "boards": payload.get("boards", []),
    }


_SCOPE_RESTORE_PROBE = r"""
import json
import shutil
import sqlite3
from pathlib import Path

scope_root = Path(SCOPE_ROOT)
hermes = Path(HERMES_HOME)
state_root = Path(STATE_ROOT)
manifest = json.loads(SCOPE_MANIFEST)
payload = {"removed": [], "errors": []}
try:
    from aether_agents.observation.context import ProjectRegistry
    from hermes_cli import projects_db

    registry = ProjectRegistry(state_root)
    registry_path = registry.path
    current = json.loads(registry_path.read_text(encoding="utf-8"))
    projects = current.get("projects", {})
    connection = sqlite3.connect(projects_db.projects_db_path())
    for entry in manifest:
        projects.pop(entry["project_id"], None)
        row = projects_db.find_by_primary_path(connection, entry["path"])
        if row is not None:
            projects_db.delete_project(connection, row.id)
        board_dir = hermes / "kanban" / "boards" / entry["board_slug"]
        if board_dir.exists():
            shutil.rmtree(board_dir, ignore_errors=True)
        shutil.rmtree(Path(entry["path"]), ignore_errors=True)
        payload["removed"].append(entry["board_slug"])
    registry_path.write_text(
        json.dumps({"schema_version": 1, "projects": projects}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    connection.commit()
    connection.close()
    shutil.rmtree(scope_root, ignore_errors=True)
except Exception as error:
    payload["errors"].append(f"{type(error).__name__}: {error}")
print(json.dumps(payload))
"""


def _scope_remove(interpreter: Path, scope: dict[str, Any]) -> None:
    """Remove the synthetic scope: native projects, boards, registry entries, files."""

    manifest = list(scope.get("manifest", []))
    if not manifest:
        return
    scope_root = Path(manifest[0]["path"]).parents[1]
    body = (
        f"SCOPE_ROOT = {str(scope_root)!r}\n"
        f"HERMES_HOME = {str(monitor_runtime.hermes_home())!r}\n"
        f"STATE_ROOT = {str(MonitorStore().state_root)!r}\n"
        f"SCOPE_MANIFEST = {json.dumps(json.dumps(manifest))!r}\n" + _SCOPE_RESTORE_PROBE
    )
    payload = _runtime_execute(interpreter, body)
    scope["removed"] = payload.get("removed", [])
    scope["removal_errors"] = payload.get("errors", [])
    if payload.get("errors"):
        raise QualificationError(
            "scope-restore", f"synthetic scope restore failed: {payload['errors']}"
        )


def _wait_for_boundaries(
    wait_boundaries: int,
    *,
    deadline: datetime,
    stream: Any,
) -> dict[str, Any]:
    """Wait for real native hourly cuts and collect their private evidence."""

    store = MonitorStore()
    started = _utc_now()
    settings = store.get_settings()
    baseline_cutoff = settings.last_cutoff_utc
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    while len(evidence) < wait_boundaries:
        if _utc_now() > deadline:
            raise QualificationError(
                "boundary-timeout",
                f"only {len(evidence)} of {wait_boundaries} real hourly boundaries completed "
                "before the bounded wait expired",
            )
        for snapshot in reversed(store.list_snapshots(limit=12)):
            if snapshot.cutoff_utc in seen or snapshot.cutoff_utc == baseline_cutoff:
                continue
            narrative = store.get_narrative(snapshot.report_id)
            deliveries = store.list_deliveries(snapshot.report_id)
            states = sorted({str(delivery.state) for delivery in deliveries})
            if not states or not all(
                state in {"confirmed", "failed", "uncertain", "suppressed"} for state in states
            ):
                continue
            seen.add(snapshot.cutoff_utc)
            evidence.append(
                {
                    "cutoff_utc": snapshot.cutoff_utc,
                    "previous_cutoff_utc": snapshot.previous_cutoff_utc,
                    "collected_at_utc": snapshot.collected_at_utc,
                    "collected_lateness_seconds": _seconds_between(
                        snapshot.cutoff_utc, snapshot.collected_at_utc
                    ),
                    "narration_status": None if narrative is None else narrative.attempt_status,
                    "narration_count": 0 if narrative is None else 1,
                    "delivery_states": states,
                    "message_ids": sorted(
                        str(delivery.message_id)
                        for delivery in deliveries
                        if delivery.message_id is not None
                    ),
                    "acknowledged_at_utc": max(
                        (delivery.updated_at_utc for delivery in deliveries),
                        default=None,
                    ),
                    "report_id": snapshot.report_id,
                }
            )
        if len(evidence) >= wait_boundaries:
            break
        print(
            f"waiting for real hourly boundaries: {len(evidence)}/{wait_boundaries}",
            file=stream,
            flush=True,
        )
        time.sleep(30)
    return {
        "started_at_utc": _utc_text(started),
        "ended_at_utc": _utc_text(_utc_now()),
        "boundaries": evidence,
    }


def _seconds_between(cutoff: str, moment: str | None) -> float | None:
    start = _parse_utc(cutoff)
    end = _parse_utc(moment)
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


def _confirm_idle_skip(*, deadline: datetime, stream: Any) -> dict[str, Any]:
    """Wait for one real tick with no monitored work and no inference."""

    store = MonitorStore()
    settings = store.get_settings()
    baseline_cutoff = settings.last_cutoff_utc
    baseline_reports = {snapshot.report_id for snapshot in store.list_snapshots(limit=50)}
    while _utc_now() <= deadline:
        settings = store.get_settings()
        current = settings.last_cutoff_utc
        if current is not None and current != baseline_cutoff:
            fresh = [
                snapshot
                for snapshot in store.list_snapshots(limit=50)
                if snapshot.report_id not in baseline_reports and snapshot.cutoff_utc == current
            ]
            narratives = [store.get_narrative(snapshot.report_id) for snapshot in fresh]
            inference = [item for item in narratives if item is not None and item.structured_result]
            if fresh and not inference:
                return {
                    "cutoff_utc": current,
                    "idle_confirmed": True,
                    "narratives": 0,
                    "inference_calls": 0,
                }
            return {
                "cutoff_utc": current,
                "idle_confirmed": False,
                "narratives": len([item for item in narratives if item is not None]),
                "inference_calls": len(inference),
            }
        print("waiting for the no-work hourly boundary", file=stream, flush=True)
        time.sleep(30)
    raise QualificationError(
        "idle-timeout", "no no-work hourly boundary was observed before the bounded wait expired"
    )


def run_live(args: argparse.Namespace, stream: Any) -> dict[str, Any]:
    """Run the bounded provisioned qualification. Owned by MON-INT."""

    if args.output is None:
        raise QualificationError(
            "output-required",
            "--live requires --output outside the repository: private receipts are never public",
        )
    output = Path(args.output).expanduser()
    if _inside_repository(output):
        raise QualificationError(
            "output-inside-repository",
            "the live output file must live outside the repository checkout",
        )
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        # A test process must never enable the monitor, create a native job or send a
        # real message: refuse before the first live effect, after output policy.
        raise QualificationError(
            "test-process-refused",
            "the live qualification refuses to run inside a test process",
        )
    interpreter = _runtime_python()
    started = _utc_now()
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    state_root = MonitorStore().state_root
    scope_root = state_root / "monitor" / "qualification" / stamp
    scope_root.mkdir(parents=True, exist_ok=True)
    store = MonitorStore()
    prior = store.get_settings()
    prior_enabled = bool(prior.enabled)
    prior_job_id = prior.native_job_id
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": "live",
        "candidate_revision": _candidate_revision(),
        "started_at_utc": _utc_text(started),
        "runtime_interpreter": str(interpreter),
        "prior_state": {
            "enabled": prior_enabled,
            "native_job_id": prior_job_id,
            "destination_pinned": bool(prior.destination_ref),
        },
        "scope": None,
        "boundaries": None,
        "idle": None,
        "restore": {},
        "errors": [],
    }
    scope: dict[str, Any] | None = None
    try:
        status = _control(ACTION_STATUS)
        record["status_before"] = _sanitize_status(status["result"])
        scope = _scope_prepare(interpreter, scope_root, stamp)
        record["scope"] = {
            "projects": [entry["project_id"] for entry in scope["manifest"]],
            "boards": list(scope["boards"]),
            "root": str(scope_root),
        }
        enabled = _control(ACTION_ON)
        record["enable"] = _sanitize_status(enabled["result"])
        next_cut = _parse_utc(enabled["result"].get("next_cut_utc"))
        if next_cut is None:
            raise QualificationError("enable-invalid", "the monitor reported no next cut")
        deadline = next_cut + timedelta(hours=args.wait_hourly_boundaries) + BOUNDARY_SLOP
        record["boundaries"] = _wait_for_boundaries(
            args.wait_hourly_boundaries, deadline=deadline, stream=stream
        )
        for boundary in record["boundaries"]["boundaries"]:
            if boundary["narration_count"] > 1:
                raise QualificationError(
                    "multiple-narrations", "a single digest produced more than one narration"
                )
            if "confirmed" not in boundary["delivery_states"]:
                raise QualificationError(
                    "delivery-unconfirmed",
                    "an hourly boundary completed without a confirmed native Telegram delivery",
                )
        _scope_remove(interpreter, scope)
        scope = None
        record["idle"] = _confirm_idle_skip(
            deadline=deadline + timedelta(hours=1) + BOUNDARY_SLOP, stream=stream
        )
    finally:
        restore: dict[str, Any] = {}
        if scope is not None:
            try:
                _scope_remove(interpreter, scope)
                restore["scope_removed"] = True
            except QualificationError as error:
                restore["scope_removed"] = False
                restore["scope_error"] = error.message
                record["errors"].append(error.message)
        try:
            if not prior_enabled:
                _control(ACTION_OFF)
            restore["enabled_restored"] = True
        except QualificationError as error:
            restore["enabled_restored"] = False
            restore["enable_error"] = error.message
            record["errors"].append(error.message)
        record["restore"] = restore
        record["ended_at_utc"] = _utc_text(_utc_now())
    record["public_summary"] = _public_live_summary(record)
    _write_private_output(output, record)
    record["output"] = str(output)
    return record


def _inside_repository(candidate: Path) -> bool:
    try:
        resolved = candidate.resolve()
        root = ROOT.resolve()
    except OSError:
        return False
    return root == resolved or root in resolved.parents


def _sanitize_status(result: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a control result to the fields that are safe in public evidence."""

    job = result.get("native_job") if isinstance(result.get("native_job"), Mapping) else None
    return {
        "enabled": bool(result.get("enabled")),
        "destination_pinned": bool(result.get("destination_pinned")),
        "timezone": result.get("timezone"),
        "next_cut_utc": result.get("next_cut_utc"),
        "native_job": (
            None
            if job is None
            else {
                "present": True,
                "schedule": job.get("schedule"),
                "paused": bool(job.get("paused")),
            }
        ),
    }


def _public_live_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    boundaries = ((record.get("boundaries") or {}).get("boundaries")) or []
    return {
        "candidate_revision": record.get("candidate_revision"),
        "runtime_interpreter_recorded": bool(record.get("runtime_interpreter")),
        "boundaries_observed": len(boundaries),
        "confirmed_deliveries": sum(
            1 for boundary in boundaries if "confirmed" in boundary.get("delivery_states", [])
        ),
        "narration_counts": [boundary.get("narration_count") for boundary in boundaries],
        "idle_confirmed": bool((record.get("idle") or {}).get("idle_confirmed")),
        "scope_restored": bool((record.get("restore") or {}).get("scope_removed")),
        "enabled_restored": bool((record.get("restore") or {}).get("enabled_restored")),
        "acceptance_notice": (
            "Telegram Bot API acceptance is recorded as acceptance, "
            "not as proof that the human read the message"
        ),
        "errors": list(record.get("errors") or []),
    }


def _write_private_output(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qualify_telegram_monitor.py",
        description=(
            "Qualify the Aether Telegram Monitor. The default lane is deterministic and "
            "performs no external effect; --live adds the provisioned hourly qualification."
        ),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run the provisioned qualification (owned by MON-INT; real model and Telegram).",
    )
    parser.add_argument("--json", action="store_true", help="Print the summary as one JSON object.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Operator-selected protected file for private live receipts (required with --live).",
    )
    parser.add_argument(
        "--wait-hourly-boundaries",
        type=int,
        default=DEFAULT_WAIT_HOURLY_BOUNDARIES,
        metavar="N",
        help=(
            "Real native hourly boundaries required by --live "
            f"(1-{MAX_WAIT_HOURLY_BOUNDARIES}, default {DEFAULT_WAIT_HOURLY_BOUNDARIES})."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else sys.argv[1:])
    except SystemExit as error:
        return int(error.code) if isinstance(error.code, int) else 2
    if not 1 <= args.wait_hourly_boundaries <= MAX_WAIT_HOURLY_BOUNDARIES:
        print(
            f"qualify-telegram-monitor: --wait-hourly-boundaries must be between 1 and "
            f"{MAX_WAIT_HOURLY_BOUNDARIES}",
            file=sys.stderr,
        )
        return 2
    if args.live and args.output is None:
        print("qualify-telegram-monitor: --live requires --output", file=sys.stderr)
        return 2
    workspace = (
        Path(os.environ.get("TMPDIR", "/tmp")) / f"aether-monitor-qualification-{os.getpid()}"
    )
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        if args.live:
            record = run_live(args, sys.stderr)
            summary: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "mode": "live",
                "output": record.get("output"),
                **(record.get("public_summary") or {}),
            }
            ok = not summary.get("errors") and bool(summary.get("idle_confirmed"))
        else:
            summary = run_offline(workspace)
            ok = all(record["status"] == "pass" for record in summary["checks"])
    except QualificationError as error:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": {"code": error.code, "message": error.message},
        }
        ok = False
    except Exception as error:  # never leak a traceback into the piecemeal interface
        summary = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": {"code": "qualification-failed", "message": f"{type(error).__name__}"},
        }
        ok = False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    summary["ok"] = ok and "error" not in summary
    if args.output is not None and not args.live:
        _write_private_output(Path(args.output).expanduser(), summary)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        _print_human(summary)
    return 0 if summary.get("ok") else 1


def _print_human(summary: Mapping[str, Any]) -> None:
    if "error" in summary:
        error = summary["error"]
        print(f"qualification failed: {error['code']}: {error['message']}")
        return
    if summary.get("mode") == "offline":
        for record in summary["checks"]:
            print(f"[{record['status']}] {record['check']}: {record['detail']}")
        print("offline qualification: no model call and no Telegram send")
        return
    public = summary.get("public_summary") or {}
    print(
        f"live qualification: boundaries={public.get('boundaries_observed')} "
        f"confirmed={public.get('confirmed_deliveries')} idle={public.get('idle_confirmed')}"
    )
    print(f"private receipts written to {summary.get('output')}")


if __name__ == "__main__":
    raise SystemExit(main())
