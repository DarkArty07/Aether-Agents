#!/usr/bin/env python3
"""Disposable real-path E2E runner for Aether Agents.

The harness has two modes:

* ``--prepare-only`` creates an isolated Git/Aether fixture and deterministic
  baseline evidence without invoking Hermes or a model.
* ``--live`` uses a caller-supplied Hermes executable and profile root. Scenarios
  that may consume provider quota additionally require ``--allow-model-spend``.

No daemon, database of our own, notifier, or evaluator model is introduced.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from aether_agents import product_version

HERE = Path(__file__).resolve().parent
from .resources import source_root  # noqa: E402

ROOT = source_root()
FIXTURES = ROOT / "tests" / "fixtures" / "e2e"
SCENARIOS = ROOT / "lab" / "scenarios"
PROFILE_RESOURCES = HERE.parent / "resources" / "profiles"
if not PROFILE_RESOURCES.is_dir():
    PROFILE_RESOURCES = ROOT / "src" / "aether_agents" / "resources" / "profiles"
if not FIXTURES.is_dir():
    FIXTURES = HERE.parent / "resources" / "lab" / "fixtures" / "sandbox"
if not FIXTURES.is_dir():
    FIXTURES = ROOT / "lab" / "fixtures" / "sandbox"
if not SCENARIOS.is_dir():
    SCENARIOS = HERE.parent / "resources" / "lab" / "scenarios"
SYNC_HOOKS = ROOT / "scripts" / "sync_policy_hooks.py"
VERSION_FILE = ROOT / "VERSION"

from .affinity import qualify_affinity_evidence  # noqa: E402
from .collect import git_diff, git_snapshot, run_command, write_json  # noqa: E402
from .dispatch import board_list, dispatch_until_settled, hermes_argv, snapshot_board  # noqa: E402
from .persistent import qualify_persistent_evidence  # noqa: E402
from .synthetic_owner import Scenario, ScenarioError, load_scenario, matching_reply  # noqa: E402
from .validation import validate_evidence  # noqa: E402

QUESTION_RE = re.compile(
    r"(?:\?|¿|\b(?:necesito|confirma|confirmame|confírmame|dime|podrias|podrías|"
    r"quieres que|debo|prefieres|cu[aá]l)\b)",
    re.IGNORECASE,
)
PROJECT_ID_RE = re.compile(r"\((p_[0-9a-f]{8})\)")
HOOK_COMMAND_RE = re.compile(
    r"^(?P<indent>\s*)command:\s*.*aether_pre_tool_policy\.py\s*$",
    re.MULTILINE,
)


class HarnessError(RuntimeError):
    pass


def _qualify_e2e15_record(
    record: Mapping[str, Any], receipts: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply the strict persistent receipt policy before E2E-15 can pass or count."""
    qualified = qualify_persistent_evidence(receipts)
    result = dict(record)
    result["persistent_autonomous_wake_qualified"] = qualified.qualified
    result["rolling_reliability_counted"] = qualified.qualified
    if not qualified.qualified:
        result["status"] = qualified.status
        result["reason"] = qualified.reason
    return result


def _scenario_path(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_file():
        return candidate.resolve()
    normalized = value.casefold()
    if re.fullmatch(r"(?:e2e-)?[0-9]{1,2}", normalized):
        number = int(normalized.rsplit("-", 1)[-1])
        candidate = SCENARIOS / f"e2e-{number:02d}.json"
        if candidate.is_file():
            return candidate
    candidate = SCENARIOS / value
    if candidate.is_file():
        return candidate
    raise HarnessError(f"scenario not found: {value}")


def _default_run_root(scenario: Scenario) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    suffix = uuid.uuid4().hex[:8]
    return ROOT / ".aether" / "e2e-runs" / f"{scenario.id}-{stamp}-{suffix}"


def _safe_run_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == ROOT or ROOT in resolved.parents and resolved == ROOT / ".aether":
        raise HarnessError("run root is too broad")
    if resolved.exists() and any(resolved.iterdir()):
        raise HarnessError(f"run root must be absent or empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _copy_fixture(scenario: Scenario, run_root: Path) -> Path:
    source = FIXTURES / scenario.fixture
    if not source.is_dir():
        raise HarnessError(f"fixture is missing: {source}")
    repo = run_root / "repo"
    shutil.copytree(source, repo)
    return repo


def _git_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Aether E2E",
            "GIT_AUTHOR_EMAIL": "aether-e2e@example.invalid",
            "GIT_COMMITTER_NAME": "Aether E2E",
            "GIT_COMMITTER_EMAIL": "aether-e2e@example.invalid",
        }
    )
    return env


def _write_aether_project_identity(repo: Path, run_root: Path, scenario: Scenario) -> str:
    project_id = str(uuid.uuid4())
    version = (
        VERSION_FILE.read_text(encoding="utf-8").strip()
        if VERSION_FILE.is_file()
        else product_version()
    )
    marker_dir = repo / ".aether"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = (
        "schema_version = 1\n"
        f'project_id = "{project_id}"\n'
        f'name = "Aether E2E {scenario.id}"\n'
        f'initialized_by = "{version}"\n'
        'forge = "local"\n'
        'contract_root = "specs"\n'
        'default_branch = "main"\n'
    )
    (marker_dir / "project.toml").write_text(marker, encoding="utf-8")
    gitignore = marker_dir / ".gitignore"
    gitignore.write_text("drafts/\n", encoding="utf-8")

    registry = run_root / "xdg-state" / "aether" / "projects" / "registry.json"
    write_json(
        registry,
        {
            "schema_version": 1,
            "projects": {
                project_id: {
                    "name": f"Aether E2E {scenario.id}",
                    "path": str(repo.resolve()),
                }
            },
        },
    )
    if os.name == "posix":
        registry.parent.chmod(0o700)
        registry.chmod(0o600)
    return project_id


def _init_fixture_repo(
    repo: Path,
    run_root: Path,
    scenario: Scenario,
    commands_log: Path,
) -> tuple[str, dict[str, str]]:
    env = _git_env()
    project_id = _write_aether_project_identity(repo, run_root, scenario)
    commands: list[tuple[str, ...]] = [("git", "init", "-b", "main")]
    if scenario.id == "e2e-09":
        remote = run_root / "edge-remote.git"
        commands.extend(
            [
                ("git", "init", "--bare", "--initial-branch=main", str(remote)),
                ("git", "remote", "add", "origin", str(remote)),
            ]
        )
    commands.extend(
        [
            ("git", "add", "-A"),
            ("git", "commit", "-m", f"fixture: {scenario.id} baseline"),
        ]
    )
    for argv in commands:
        result = run_command(
            argv,
            cwd=repo,
            env=env,
            log_path=commands_log,
            timeout_seconds=30,
        )
        if result.returncode != 0:
            raise HarnessError(f"fixture Git initialization failed: {' '.join(argv)}")
    return project_id, env


def _patch_profile_hook(config_text: str, hook_path: Path) -> str:
    replacement_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacement_count
        replacement_count += 1
        encoded = json.dumps(str(hook_path), ensure_ascii=False)
        return f"{match.group('indent')}command: {encoded}"

    updated = HOOK_COMMAND_RE.sub(replace, config_text)
    if replacement_count != 1:
        raise HarnessError(
            f"profile config must contain exactly one Aether pre-tool hook command; found {replacement_count}"
        )
    auto_accept_pattern = re.compile(r"(?m)^hooks_auto_accept:\s*(?:true|false)\s*$")
    if auto_accept_pattern.search(updated):
        updated = auto_accept_pattern.sub("hooks_auto_accept: true", updated, count=1)
    else:
        updated = updated.rstrip() + "\nhooks_auto_accept: true\n"
    approvals_pattern = re.compile(r"(?ms)^approvals:\n(?P<body>(?:^[ \t]+.*(?:\n|$))*)")
    approvals = approvals_pattern.search(updated)
    if approvals is None:
        updated = updated.rstrip() + "\napprovals:\n  mode: false\n"
    else:
        block = approvals.group(0)
        mode_pattern = re.compile(r"(?m)^[ \t]+mode:\s*.*$")
        if mode_pattern.search(block):
            replacement = mode_pattern.sub("  mode: false", block, count=1)
        else:
            replacement = "approvals:\n  mode: false\n" + approvals.group("body")
        updated = updated[: approvals.start()] + replacement + updated[approvals.end() :]
    return updated


def prepare_profiles(profile_root: Path, run_root: Path, commands_log: Path) -> Path:
    """Copy only candidate config + tracked SOUL into isolated Hermes profiles."""

    profile_root = profile_root.expanduser().resolve()
    hermes_root = run_root / "hermes-home"
    for role in ("morfeo", "supervisor", "implementer"):
        source_config = profile_root / role / "config.yaml"
        source_soul = PROFILE_RESOURCES / role / "SOUL.md"
        if not source_config.is_file():
            raise HarnessError(f"profile config is missing for {role}: {source_config}")
        if not source_soul.is_file():
            raise HarnessError(f"tracked SOUL is missing for {role}: {source_soul}")
        target = hermes_root / "profiles" / role
        target.mkdir(parents=True, exist_ok=True)
        (target / "config.yaml").write_text(
            _patch_profile_hook(
                source_config.read_text(encoding="utf-8"),
                target / "hooks" / "aether_pre_tool_policy.py",
            ),
            encoding="utf-8",
        )
        shutil.copy2(source_soul, target / "SOUL.md")

    backup = run_root / "hook-backup"
    result = run_command(
        (
            sys.executable,
            str(SYNC_HOOKS),
            "install",
            "--home",
            str(hermes_root),
            "--backup-dir",
            str(backup),
        ),
        cwd=ROOT,
        env=os.environ,
        log_path=commands_log,
        timeout_seconds=30,
    )
    if result.returncode != 0:
        raise HarnessError("candidate hook installation into isolated profiles failed")
    return hermes_root


def _apply_fault_injection(
    scenario: Scenario, hermes_root: Path, evidence_dir: Path
) -> Path | None:
    """Inject one bounded, disposable recovery fault into the isolated Morfeo profile."""

    if scenario.fault_injection is None:
        return None
    if scenario.fault_injection != "hook_false_positive_file_mutation":
        raise HarnessError(f"unsupported fault injection: {scenario.fault_injection}")

    active = hermes_root / "profiles" / "morfeo" / "hooks" / "aether_pre_tool_policy.py"
    if not active.is_file():
        raise HarnessError("cannot inject recovery fault because candidate hook is missing")
    backup = active.with_name("aether_pre_tool_policy.py.known-good")
    shutil.copy2(active, backup)
    injected = f"""#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

KNOWN_GOOD = Path({str(backup)!r})
try:
    payload = json.load(sys.stdin)
except Exception:
    print('{{"decision":"block","reason":"AETHER-E2E-INJECTED-PAYLOAD: malformed input"}}')
    raise SystemExit(2)
if payload.get("tool_name") in {{"write_file", "patch"}}:
    print('{{"decision":"block","reason":"AETHER-E2E-INJECTED-FALSE-POSITIVE: ordinary local file mutation is unexpectedly blocked; restore the active Aether hook to its known-good sibling and rerun the canary"}}')
    raise SystemExit(2)
completed = subprocess.run(
    [sys.executable, str(KNOWN_GOOD)],
    input=json.dumps(payload),
    text=True,
    capture_output=True,
    check=False,
)
sys.stdout.write(completed.stdout)
sys.stderr.write(completed.stderr)
raise SystemExit(completed.returncode)
"""
    active.write_text(injected, encoding="utf-8")
    active.chmod(0o755)
    write_json(
        evidence_dir / "fault-injection.json",
        {
            "fault": scenario.fault_injection,
            "scope": "disposable morfeo profile only",
        },
    )
    return backup


def _fault_recovered(known_good: Path | None) -> bool:
    if known_good is None:
        return True
    active = known_good.with_name("aether_pre_tool_policy.py")
    return active.is_file() and active.read_bytes() == known_good.read_bytes()


def _hermes_env(run_root: Path, hermes_root: Path, hermes: Path) -> dict[str, str]:
    env = dict(os.environ)
    # The laboratory's --in directory is authoritative. Ambient cwd and
    # dispatcher-worker identity belong to the outer process; carrying either
    # into the isolated home/board would make the canary act on a foreign task.
    for name in (
        "TERMINAL_CWD",
        "HERMES_CWD",
        "HERMES_KANBAN_TASK",
        "HERMES_KANBAN_RUN_ID",
        "HERMES_KANBAN_WORKSPACE",
        "HERMES_KANBAN_BRANCH",
        "HERMES_KANBAN_BOARD",
        "HERMES_KANBAN_CLAIM_LOCK",
        "HERMES_KANBAN_GOAL_MODE",
        "HERMES_KANBAN_AFFINITY_TOKEN",
        "HERMES_KANBAN_AFFINITY_GENERATION",
        "HERMES_KANBAN_AFFINITY_FLOW_ID",
        "HERMES_KANBAN_AFFINITY_PROJECT_ID",
        "HERMES_SESSION_ID",
        "HERMES_SESSION_SOURCE",
    ):
        env.pop(name, None)
    env.update(
        {
            "HERMES_HOME": str(hermes_root),
            "HERMES_BIN": str(hermes.resolve()),
            "HERMES_ACCEPT_HOOKS": "1",
            "HERMES_KANBAN_DB": str(run_root / "kanban.db"),
            "HERMES_KANBAN_WORKSPACES_ROOT": str(run_root / "worktrees"),
            "XDG_STATE_HOME": str(run_root / "xdg-state"),
            "XDG_DATA_HOME": str(run_root / "xdg-data"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def _pid_uses_board(pid: int, board: Path) -> bool:
    if os.name != "posix":
        return False
    try:
        values = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        return False
    return f"HERMES_KANBAN_DB={board}".encode() in values


def _pid_alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()[2]
    except (OSError, IndexError):
        return False
    return state != "Z"


def _cleanup_disposable_workers(run_root: Path, grace_seconds: float = 5.0) -> dict[str, Any]:
    board = (run_root / "kanban.db").resolve()
    report: dict[str, Any] = {
        "candidates": [],
        "terminated": [],
        "killed": [],
        "skipped": [],
        "survivors": [],
    }
    if not board.is_file():
        return report
    with sqlite3.connect(board) as conn:
        rows = conn.execute(
            "SELECT DISTINCT worker_pid FROM tasks WHERE worker_pid IS NOT NULL"
        ).fetchall()
    pids = sorted({int(row[0]) for row in rows if row[0]})
    report["candidates"] = pids
    owned: list[int] = []
    for pid in pids:
        if not _pid_uses_board(pid, board):
            report["skipped"].append(pid)
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            owned.append(pid)
            report["terminated"].append(pid)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + grace_seconds
    while owned and time.monotonic() < deadline:
        owned = [pid for pid in owned if _pid_alive(pid)]
        if owned:
            time.sleep(0.05)
    for pid in owned:
        try:
            os.kill(pid, signal.SIGKILL)
            report["killed"].append(pid)
        except ProcessLookupError:
            pass
    report["survivors"] = [pid for pid in owned if _pid_alive(pid)]
    evidence = run_root / "evidence"
    if evidence.is_dir():
        write_json(evidence / "worker-cleanup.json", report)
    return report


def _initialize_runtime_project(
    hermes: Path,
    hermes_root: Path,
    repo: Path,
    scenario: Scenario,
    env: dict[str, str],
    commands_log: Path,
) -> str:
    init = run_command(
        hermes_argv(hermes, "morfeo", "kanban", "init"),
        cwd=repo,
        env=env,
        log_path=commands_log,
        timeout_seconds=30,
    )
    if init.returncode != 0:
        raise HarnessError("Hermes board initialization failed")

    slug = f"aether-{scenario.id}"
    created = run_command(
        hermes_argv(
            hermes,
            "morfeo",
            "project",
            "create",
            f"Aether {scenario.id}",
            str(repo),
            "--slug",
            slug,
            "--primary",
            str(repo),
        ),
        cwd=repo,
        env=env,
        log_path=commands_log,
        timeout_seconds=30,
    )
    if created.returncode != 0:
        raise HarnessError("Hermes Project initialization failed")
    match = PROJECT_ID_RE.search(created.stdout)
    if not match:
        raise HarnessError("Hermes Project id was not observable from create output")
    project_id = match.group(1)

    # Hermes Projects are per-profile while Aether's board is shared. Qualifying
    # cross-profile Project/worktree inheritance therefore requires the same exact
    # Project identity in each disposable profile. Create once through the public
    # CLI, checkpoint the closed SQLite DB, then copy that runtime state to the two
    # other fresh profiles. No private or persistent user Project store is touched.
    morfeo_db = hermes_root / "profiles" / "morfeo" / "projects.db"
    if not morfeo_db.is_file():
        raise HarnessError("Hermes Project DB was not created")
    with sqlite3.connect(morfeo_db) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    for role in ("supervisor", "implementer"):
        target = hermes_root / "profiles" / role / "projects.db"
        shutil.copy2(morfeo_db, target)
    return project_id


def _run_acceptance(
    scenario: Scenario,
    repo: Path,
    env: Mapping[str, str],
    commands_log: Path,
    evidence_dir: Path,
    prefix: str,
) -> bool:
    result = run_command(
        scenario.acceptance_command,
        cwd=repo,
        env=env,
        log_path=commands_log,
        timeout_seconds=min(120, scenario.timeout_seconds),
    )
    # Retain the historical filenames, but never persist command output.  The
    # boolean is sufficient for qualification and is safe to export.
    write_json(
        evidence_dir / f"{prefix}-acceptance.stdout",
        {"kind": "acceptance", "passed": result.returncode == 0},
    )
    write_json(
        evidence_dir / f"{prefix}-acceptance.stderr",
        {"kind": "acceptance_diagnostics", "present": bool(result.stderr)},
    )
    return result.returncode == 0


def _invoke_morfeo(
    hermes: Path,
    hermes_root: Path,
    repo: Path,
    env: dict[str, str],
    commands_log: Path,
    evidence_dir: Path,
    query: str,
    *,
    resume_session_id: str | None,
    usage_name: str,
    observation_route: bool = False,
) -> str:
    argv: list[str] = [
        str(hermes),
        "--accept-hooks",
        "-p",
        "morfeo",
        "--usage-file",
        str(evidence_dir / usage_name),
        "--in",
        str(repo),
    ]
    if observation_route:
        if resume_session_id is not None:
            raise HarnessError("observation route does not support session continuation")
        argv.extend(("--toolsets", "aether_observation", "--oneshot", query))
    else:
        if resume_session_id is not None:
            argv.extend(("--resume", resume_session_id, "--no-restore-cwd"))
        argv.extend(("chat", "-q", query, "-Q"))
    result = run_command(
        argv,
        cwd=repo,
        env=env,
        log_path=commands_log,
        timeout_seconds=900,
    )
    if result.returncode != 0:
        raise HarnessError(f"Morfeo invocation failed with rc={result.returncode}")
    return result.stdout.strip()


def _origin_morfeo_session_id(hermes_root: Path) -> str:
    database = hermes_root / "profiles" / "morfeo" / "state.db"
    if not database.is_file():
        raise HarnessError("Morfeo session database is missing")
    with sqlite3.connect(database) as conn:
        rows = conn.execute(
            "SELECT id FROM sessions WHERE source != 'kanban' "
            "AND archived = 0 ORDER BY last_activity_at DESC"
        ).fetchall()
    identifiers = [str(row[0]) for row in rows]
    if len(identifiers) != 1:
        raise HarnessError("Morfeo origin session is missing or ambiguous")
    return identifiers[0]


def _decode_task_affinity(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _supervisor_flow_id(tasks: list[dict[str, object]]) -> str | None:
    for task in tasks:
        if str(task.get("assignee", "")).casefold() != "supervisor":
            continue
        affinity = _decode_task_affinity(task.get("session_affinity"))
        flow_id = affinity.get("flow_id") if affinity else None
        if isinstance(flow_id, str) and flow_id:
            return flow_id
    return None


def _supervisor_project_id(tasks: list[dict[str, object]]) -> str | None:
    for task in tasks:
        if str(task.get("assignee", "")).casefold() == "supervisor":
            project_id = task.get("project_id")
            if isinstance(project_id, str) and project_id:
                return project_id
    return None


def _board_affinity_row(board: Path, flow_id: str) -> dict[str, object] | None:
    if not board.is_file():
        return None
    try:
        with sqlite3.connect(board) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT board, project_id, flow_id, assignee, session_id, generation, "
                "workspace_path, owner_task_id FROM kanban_session_affinity WHERE flow_id = ? "
                "AND assignee = 'supervisor' ORDER BY generation DESC LIMIT 1",
                (flow_id,),
            ).fetchone()
            return dict(row) if row is not None else None
    except sqlite3.Error:
        return None


def _board_affinity_table_exists(board: Path) -> bool:
    if not board.is_file():
        return False
    try:
        with sqlite3.connect(board) as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'kanban_session_affinity'"
            ).fetchone()
    except sqlite3.Error:
        return False
    return row is not None


def _affinity_generation(row: dict[str, object] | None) -> int:
    value = row.get("generation") if row else None
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _running_supervisor_worker(
    board: Path, flow_id: str | None = None
) -> tuple[int, str, str] | None:
    if not board.is_file():
        return None
    try:
        with sqlite3.connect(board) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, worker_pid, workspace_path, session_affinity FROM tasks "
                "WHERE assignee = 'supervisor' AND status = 'running' "
                "AND worker_pid IS NOT NULL ORDER BY id"
            ).fetchall()
    except sqlite3.Error:
        return None
    for row in rows:
        if flow_id:
            affinity = _decode_task_affinity(row["session_affinity"])
            if not affinity or affinity.get("flow_id") != flow_id:
                continue
        try:
            pid = int(row["worker_pid"])
        except (TypeError, ValueError):
            continue
        if pid > 0 and _pid_uses_board(pid, board):
            return pid, str(row["id"]), str(row["workspace_path"] or "")
    return None


_NATIVE_AFFINITY_OBSERVER = r'''
import dataclasses
import json
import os
import shutil
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid


board, supervisor_db, implementer_db, flow_id, project_id, first_session = sys.argv[1:7]
resumed_session = sys.argv[7]
first_generation = int(sys.argv[8])
workspace_path = sys.argv[9]
task_id = sys.argv[10] or None
requested_task_id = task_id
probe_dir = sys.argv[11]


def _table(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _columns(conn, table):
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(" + table + ")")}
    except sqlite3.Error:
        return set()


def _session(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value and value.casefold() != "unavailable" else None


def _copy_board():
    os.makedirs(probe_dir, exist_ok=True)
    target = tempfile.NamedTemporaryFile(
        prefix="native-affinity-", suffix=".db", dir=probe_dir, delete=False
    ).name
    with sqlite3.connect(board) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target


def _native_identity_rejections(row, task_id):
    """Exercise the released Hermes registration guard, not a SQL imitation."""
    try:
        from hermes_cli import kanban_db
        from hermes_cli.kanban_affinity import AffinityLease, AffinityRegistrationError
    except Exception:
        return {"other_flow_rejected": False, "other_project_rejected": False,
                "other_role_rejected": False}
    if not row or not task_id:
        return {"other_flow_rejected": False, "other_project_rejected": False,
                "other_role_rejected": False}
    try:
        conn = sqlite3.connect(board)
        conn.row_factory = sqlite3.Row
        task = kanban_db.get_task(conn, task_id)
        if task is None:
            conn.close()
            return {"other_flow_rejected": False, "other_project_rejected": False,
                    "other_role_rejected": False}
        lease = AffinityLease(
            board=str(row["board"]), project_id=str(row["project_id"]),
            flow_id=str(row["flow_id"]), assignee=str(row["assignee"]),
            generation=int(row["generation"]), token=str(row["lease_token"] or ""),
        )

        def rejected(candidate):
            try:
                kanban_db.register_session_affinity(
                    conn, task, candidate, session_id=str(first_session or "probe")
                )
            except AffinityRegistrationError:
                return True
            except Exception:
                return False
            return False

        result = {
            "other_flow_rejected": rejected(dataclasses.replace(
                lease, flow_id=lease.flow_id + ":wrong-flow"
            )),
            "other_project_rejected": rejected(dataclasses.replace(
                lease, project_id=lease.project_id + ":wrong-project"
            )),
            "other_role_rejected": rejected(dataclasses.replace(
                lease, assignee="implementer"
            )),
        }
        conn.close()
        return result
    except Exception:
        return {"other_flow_rejected": False, "other_project_rejected": False,
                "other_role_rejected": False}


def _native_control_rows(main):
    """Create disposable control records through native Hermes APIs."""
    try:
        from hermes_cli import kanban_db, projects_db
        from hermes_state import SessionDB
    except Exception:
        return None
    if not main:
        return None
    token = uuid.uuid4().hex
    control_slug = "e2e16-controls-" + token[:24]
    source_home = Path(os.environ.get("HERMES_HOME", ""))
    source_projects = source_home / "projects.db"
    if not source_projects.is_file():
        source_projects = source_home / "profiles" / "morfeo" / "projects.db"
    workspace = str(main["workspace_path"] or "")
    if not workspace or not os.path.isabs(workspace):
        return None
    disposable_home = Path(probe_dir) / ("hermes-" + token)
    sessions = {
        "flow": ("e2e16-control-flow-" + token, "supervisor"),
        "project": ("e2e16-control-project-" + token, "supervisor"),
        "role": ("e2e16-control-role-" + token, "implementer"),
    }
    controls = (
        ("flow", main["project_id"], main["flow_id"] + ":control-flow", "supervisor"),
        ("project", None, main["flow_id"], "supervisor"),
        ("role", main["project_id"], main["flow_id"], "implementer"),
    )
    try:
        if not source_projects.is_file():
            return None
        disposable_home.mkdir(parents=True, exist_ok=True)
        # Snapshot only the project catalog so the native task API can resolve
        # the real main project ID; no control board/task/affinity rows are
        # copied into the disposable control board.
        shutil.copy2(source_projects, disposable_home / "projects.db")
        os.environ["HERMES_HOME"] = str(disposable_home)
        os.environ.pop("HERMES_KANBAN_DB", None)
        os.environ.pop("HERMES_KANBAN_BOARD", None)
        os.environ["HERMES_KANBAN_HOME"] = str(disposable_home)
        with projects_db.connect_closing(db_path=disposable_home / "projects.db") as projects:
            other_project_id = projects_db.create_project(
                projects,
                name="E2E-16 disposable project control",
                slug="e2e16-control-project-" + token[:8],
                primary_path=workspace,
                board_slug=control_slug,
                allow_duplicate_path=True,
            )
        controls = tuple(
            (name, other_project_id if project is None else project, flow, profile)
            for name, project, flow, profile in controls
        )
        board_meta = kanban_db.create_board(
            control_slug,
            name="E2E-16 disposable native controls",
            default_workdir=workspace,
            project_id=str(main["project_id"]),
        )
        control_board = Path(board_meta["db_path"])
        state_paths = {
            profile: disposable_home / "profiles" / profile / "state.db"
            for profile in {profile for _name, _project, _flow, profile in controls}
        }
        states = {
            profile: SessionDB(db_path=path)
            for profile, path in state_paths.items()
        }
        task_ids = {}
        with kanban_db.connect(db_path=control_board) as conn:
            for name, project, flow, profile in controls:
                session_id = sessions[name][0]
                task_id = kanban_db.create_task(
                    conn,
                    title="E2E-16 native " + name + " control",
                    assignee=profile,
                    created_by="e2e16-native-observer",
                    workspace_kind="dir",
                    workspace_path=workspace,
                    project_id=project,
                    session_affinity={"flow_id": flow},
                )
                task = kanban_db.claim_task(
                    conn, task_id, claimer="e2e16-native-observer"
                )
                if task is None:
                    raise RuntimeError("native control task was not claimable")
                lease = kanban_db.reserve_session_affinity(
                    conn, task, workspace_path=workspace, board=control_slug
                )
                state = states[profile]
                state.create_session(
                    session_id,
                    "kanban",
                    cwd=workspace,
                    profile_name=profile,
                    model="control-probe",
                )
                state.append_message(
                    session_id,
                    "tool",
                    content="native control probe",
                    tool_name="e2e16_control_probe",
                    observed=True,
                )
                kanban_db.validate_worker_resume_session(
                    session_id,
                    db_path=state_paths[profile],
                    workspace_path=workspace,
                    expected_profile=profile,
                )
                kanban_db.register_session_affinity(
                    conn, task, lease, session_id=session_id
                )
                task_ids[name] = task_id
        for state in states.values():
            state.close()
        return {
            "board": control_board,
            "sessions": sessions,
            "task_ids": task_ids,
            "project_id": other_project_id,
            "control_slug": control_slug,
        }
    except Exception:
        for state in locals().get("states", {}).values():
            try:
                state.close()
            except Exception:
                pass
        return None


controls = {
    "other_flow_session_id": "unavailable",
    "other_project_session_id": "unavailable",
    "other_profile_session_id": "unavailable",
    "other_role_session_id": "unavailable",
    "other_flow_rejected": False,
    "other_project_rejected": False,
    "other_role_rejected": False,
    "native_control_lifecycle_observed": False,
    "stale_generation_rejected": False,
    "internal_milestone_route": "missing",
    "terminal_route": "missing",
    "input_route": "missing",
    "revision_route": "missing",
    "review_integration_observed": False,
    "reclaim_observed": False,
    "resume_observed": False,
    "resumed_process_exit": None,
    "workspace_pinned": False,
    "role_binding_ok": False,
    "prior_tool_evidence_observed": False,
    "implementer_session_ids": [],
    "process_id": os.getpid(),
}

if os.path.isfile(board):
    try:
        with sqlite3.connect(board) as conn:
            conn.row_factory = sqlite3.Row
            if _table(conn, "kanban_session_affinity"):
                main = conn.execute(
                    """SELECT * FROM kanban_session_affinity
                       WHERE flow_id = ? AND project_id = ? AND assignee = 'supervisor'
                       ORDER BY generation DESC LIMIT 1""",
                    (flow_id, project_id),
                ).fetchone()
                if main is not None:
                    # Releasing a native lease clears owner_task_id.  The
                    # harness captured the claimed task before reclaim, so use
                    # that exact id rather than guessing from task membership.
                    owner_task_id = main["owner_task_id"] or task_id
                    native_controls = _native_control_rows(main)
                    cross_board = (
                        native_controls["board"] if native_controls else board
                    )
                    with sqlite3.connect(cross_board) as cross_conn:
                        cross_conn.row_factory = sqlite3.Row
                        rows = cross_conn.execute(
                            """SELECT project_id, flow_id, assignee, session_id
                               FROM kanban_session_affinity
                              WHERE session_id IS NOT NULL AND trim(session_id) != ''
                                AND lower(session_id) != 'unavailable'"""
                        ).fetchall()
                        task_ids = native_controls.get("task_ids", {}) if native_controls else {}
                        expected_controls = {
                            "flow": (
                                main["project_id"],
                                main["flow_id"] + ":control-flow",
                                "supervisor",
                            ),
                            "project": (
                                native_controls.get("project_id")
                                if native_controls else None,
                                main["flow_id"],
                                "supervisor",
                            ),
                            "role": (
                                main["project_id"], main["flow_id"], "implementer"
                            ),
                        }
                        task_rows = {}
                        event_kinds = {}
                        control_sessions = (
                            native_controls.get("sessions", {}) if native_controls else {}
                        )
                        if task_ids and _table(cross_conn, "tasks"):
                            placeholders = ",".join("?" * len(task_ids))
                            task_rows = {
                                row["id"]: row
                                for row in cross_conn.execute(
                                    "SELECT id, project_id, assignee "
                                    "FROM tasks WHERE id IN (" + placeholders + ")",
                                    tuple(task_ids.values()),
                                ).fetchall()
                            }
                            if _table(cross_conn, "task_events"):
                                event_kinds = {}
                                for event in cross_conn.execute(
                                    "SELECT task_id, kind FROM task_events "
                                    "WHERE task_id IN (" + placeholders + ")",
                                    tuple(task_ids.values()),
                                ).fetchall():
                                    event_kinds.setdefault(event["task_id"], set()).add(
                                        event["kind"]
                                    )
                        registered = {
                            (row["project_id"], row["flow_id"], row["assignee"]): row["session_id"]
                            for row in rows
                        }
                        controls["native_control_lifecycle_observed"] = all(
                            task_ids.get(name) in task_rows
                            and {"created", "claimed"} <= event_kinds.get(
                                task_ids[name], set()
                            )
                            and task_rows[task_ids[name]]["project_id"] == identity[0]
                            and task_rows[task_ids[name]]["assignee"] == identity[2]
                            and registered.get(identity) == control_sessions[name][0]
                            for name, identity in expected_controls.items()
                        )
                    for row in rows:
                        candidate = _session(row["session_id"])
                        if not candidate:
                            continue
                        if (row["project_id"] == project_id
                                and row["assignee"] == 'supervisor'
                                and row["flow_id"] != flow_id):
                            controls["other_flow_session_id"] = candidate
                        if (row["flow_id"] == flow_id
                                and row["assignee"] == 'supervisor'
                                and row["project_id"] != project_id):
                            controls["other_project_session_id"] = candidate
                        if (row["flow_id"] == flow_id
                                and row["project_id"] == project_id
                                and row["assignee"] != 'supervisor'):
                            controls["other_role_session_id"] = candidate
                            controls["other_profile_session_id"] = candidate
                    if native_controls:
                        try:
                            os.unlink(native_controls["board"])
                        except OSError:
                            pass
                    controls.update(_native_identity_rejections(main, owner_task_id))

                    current_generation = int(main["generation"] or 0)
                    if (current_generation > first_generation
                            and _session(first_session)
                            and _session(resumed_session) == _session(first_session)
                            and _session(main["session_id"]) == _session(first_session)):
                        controls["resume_observed"] = True

                    if owner_task_id and _table(conn, "tasks"):
                        task_columns = _columns(conn, "tasks")
                        task = conn.execute(
                            "SELECT * FROM tasks WHERE id = ?", (owner_task_id,)
                        ).fetchone()
                        if task is not None and "workspace_path" in task_columns:
                            task_workspace = task["workspace_path"]
                            affinity = {}
                            if "session_affinity" in task_columns and task["session_affinity"]:
                                try:
                                    affinity = json.loads(task["session_affinity"])
                                except (TypeError, ValueError, json.JSONDecodeError):
                                    affinity = {}
                            controls["workspace_pinned"] = bool(
                                task_workspace and main["workspace_path"]
                                and os.path.isabs(str(task_workspace))
                                and os.path.realpath(str(task_workspace))
                                    == os.path.realpath(str(main["workspace_path"]))
                                and os.path.realpath(str(task_workspace))
                                    == os.path.realpath(str(workspace_path))
                                and task["project_id"] == project_id
                                and affinity.get("flow_id") == flow_id
                            )

                    affinity_tasks = set()
                    affinity_task_rows = {}
                    if _table(conn, "tasks"):
                        columns = _columns(conn, "tasks")
                        if "session_affinity" in columns:
                            for task_row in conn.execute(
                                "SELECT id, title, project_id, assignee, status, workspace_path, "
                                "session_affinity FROM tasks"
                            ).fetchall():
                                try:
                                    value = json.loads(task_row["session_affinity"] or "{}")
                                except (TypeError, ValueError, json.JSONDecodeError):
                                    value = {}
                                if isinstance(value, dict) and value.get("flow_id") == flow_id:
                                    affinity_tasks.add(task_row["id"])
                                    affinity_task_rows[task_row["id"]] = (task_row, value)

                    if _table(conn, "task_runs") and affinity_tasks:
                        placeholders = ",".join("?" * len(affinity_tasks))
                        run_rows = conn.execute(
                            "SELECT task_id, outcome FROM task_runs WHERE task_id IN ("
                            + placeholders
                            + ") ORDER BY started_at, id",
                            tuple(sorted(affinity_tasks)),
                        ).fetchall()
                        completed_tasks = {
                            str(row["task_id"])
                            for row in run_rows
                            if str(row["outcome"] or "").casefold()
                            in {"completed", "success", "succeeded"}
                        }
                        controls["resume_observed"] = bool(
                            controls["resume_observed"]
                            and len(completed_tasks) >= 2
                            and requested_task_id in completed_tasks
                        )
                        if run_rows:
                            controls["resumed_process_exit"] = (
                                0
                                if str(run_rows[-1]["outcome"] or "").casefold()
                                in {"completed", "success", "succeeded"}
                                else 1
                            )
                        controls["reclaim_observed"] = conn.execute(
                            "SELECT 1 FROM task_runs WHERE task_id IN ("
                            + placeholders
                            + ") AND lower(COALESCE(outcome, '')) "
                            "IN ('reclaimed', 'crashed', 'timed_out') LIMIT 1",
                            tuple(sorted(affinity_tasks)),
                        ).fetchone() is not None

                    event_rows = []
                    if _table(conn, "task_events"):
                        event_rows = conn.execute(
                            "SELECT id, task_id, kind, payload FROM task_events ORDER BY id"
                        ).fetchall()
                    if any(row["kind"] == "reclaimed" for row in event_rows):
                        controls["reclaim_observed"] = True
                    internal_kinds = {
                        "completed", "blocked", "gave_up", "crashed", "timed_out",
                        "reclaimed", "review_requested", "changes_requested",
                    }
                    internal_events = [
                        row for row in event_rows
                        if row["task_id"] in affinity_tasks and row["kind"] in internal_kinds
                    ]
                    if internal_events:
                        # Native Hermes changes the allowed event set for an
                        # affinity task to (origin_signal, flow_terminal).  An
                        # ordinary lifecycle event on such a task is therefore
                        # an observed suppression, even when the originating
                        # subscription row remains durable for later signals.
                        controls["internal_milestone_route"] = "suppressed"

                    def native_routing_probe():
                        """Claim events on a disposable DB with native filtering."""
                        try:
                            from hermes_cli import kanban_db
                        except Exception:
                            return {}
                        routing_path = _copy_board()
                        try:
                            routed = {
                                "internal_milestone_route": "missing",
                                "terminal_route": "missing",
                                "input_route": "missing",
                                "revision_route": "missing",
                            }
                            with sqlite3.connect(routing_path) as routed_conn:
                                routed_conn.row_factory = sqlite3.Row
                                if not _table(routed_conn, "kanban_notify_subs"):
                                    return {}
                                internal_control = False
                                control_task_id = next(iter(affinity_tasks), requested_task_id)
                                try:
                                    append_event = getattr(kanban_db, "_append_event")
                                    routed_conn.execute(
                                        """INSERT OR IGNORE INTO kanban_notify_subs
                                           (task_id, platform, chat_id, thread_id,
                                            created_at, last_event_id)
                                           VALUES (?, 'e2e16-probe', 'control', '', 0, 0)""",
                                        (control_task_id,),
                                    )
                                    append_event(
                                        routed_conn, control_task_id, "completed",
                                        {"control": "internal-milestone"},
                                    )
                                    append_event(
                                        routed_conn, control_task_id, "origin_signal",
                                        {"origin_signal": "input", "control": True},
                                    )
                                    append_event(
                                        routed_conn, control_task_id, "origin_signal",
                                        {"origin_signal": "revision", "control": True},
                                    )
                                    append_event(
                                        routed_conn, control_task_id, "flow_terminal",
                                        {"flow_id": flow_id, "control": True},
                                    )
                                    routed_conn.commit()
                                    internal_control = True
                                except Exception:
                                    routed_conn.rollback()
                                calls = 0
                                for task_id in affinity_tasks:
                                    sub = routed_conn.execute(
                                        "SELECT * FROM kanban_notify_subs WHERE task_id = ? LIMIT 1",
                                        (task_id,),
                                    ).fetchone()
                                    if sub is None or not sub["platform"] or not sub["chat_id"]:
                                        continue
                                    sub_columns = set(sub.keys())
                                    if "last_event_id" not in sub_columns:
                                        continue
                                    routed_conn.execute(
                                        """UPDATE kanban_notify_subs SET last_event_id = 0
                                           WHERE task_id = ? AND platform = ? AND chat_id = ?""",
                                        (task_id, sub["platform"], sub["chat_id"]),
                                    )
                                    routed_conn.commit()
                                    try:
                                        _old, _cursor, claimed = kanban_db.claim_unseen_events_for_sub(
                                            routed_conn,
                                            task_id=task_id,
                                            platform=sub["platform"],
                                            chat_id=sub["chat_id"],
                                            thread_id=sub["thread_id"] if "thread_id" in sub_columns else "",
                                            kinds=("origin_signal", "flow_terminal"),
                                        )
                                    except Exception:
                                        continue
                                    calls += 1
                                    returned = []
                                    for event in claimed:
                                        kind = getattr(event, "kind", None)
                                        payload = getattr(event, "payload", None) or {}
                                        returned.append((kind, payload if isinstance(payload, dict) else {}))
                                    if any(row[0] == "flow_terminal" for row in returned):
                                        routed["terminal_route"] = "flow_terminal"
                                    for kind, payload in returned:
                                        signal = payload.get("origin_signal")
                                        if kind == "origin_signal" and signal in {"input", "revision"}:
                                            routed[signal + "_route"] = signal
                                    if (internal_events or internal_control) and not any(
                                        kind in internal_kinds for kind, _payload in returned
                                    ):
                                        routed["internal_milestone_route"] = "suppressed"
                            return routed if calls else {}
                        finally:
                            try:
                                os.unlink(routing_path)
                            except OSError:
                                pass

                    routed_controls = native_routing_probe()
                    if routed_controls:
                        controls.update(routed_controls)

                    review_tasks = {
                        row["task_id"] for row in event_rows
                        if row["kind"] == "review_requested"
                    }
                    root_entry = affinity_task_rows.get(requested_task_id)
                    terminal_entries = [
                        (task_ref, task_row, affinity)
                        for task_ref, (task_row, affinity) in affinity_task_rows.items()
                        if affinity.get("terminal") is True
                        and task_row["assignee"] == "supervisor"
                        and task_row["project_id"] == project_id
                    ]
                    root_terminal_ok = False
                    if root_entry is not None and len(terminal_entries) == 1:
                        root_row, root_affinity = root_entry
                        terminal_ref, terminal_row, terminal_affinity = terminal_entries[0]
                        same_workspace = bool(
                            root_row["workspace_path"]
                            and terminal_row["workspace_path"]
                            and os.path.realpath(str(root_row["workspace_path"]))
                            == os.path.realpath(str(terminal_row["workspace_path"]))
                            == os.path.realpath(str(main["workspace_path"]))
                        )
                        terminal_ran = False
                        if _table(conn, "task_runs"):
                            terminal_ran = conn.execute(
                                "SELECT 1 FROM task_runs WHERE task_id = ? "
                                "AND lower(COALESCE(outcome, '')) IN "
                                "('completed', 'success', 'succeeded') LIMIT 1",
                                (terminal_ref,),
                            ).fetchone() is not None
                        root_terminal_ok = bool(
                            root_affinity.get("flow_id") == flow_id
                            and root_affinity.get("terminal") is not True
                            and terminal_affinity.get("flow_id") == flow_id
                            and same_workspace
                            and terminal_ran
                            and _session(main["session_id"]) == _session(first_session)
                        )
                    review_transition = any(
                            row["task_id"] in review_tasks
                            and row["kind"] in {"completed", "flow_terminal"}
                            for row in event_rows
                        )
                    terminal_title = (
                        str(terminal_entries[0][1]["title"]).casefold()
                        if len(terminal_entries) == 1
                        else ""
                    )
                    terminal_named_review_integration = (
                        any(token in terminal_title for token in ("review", "revis"))
                        and any(token in terminal_title for token in ("integrat", "integr"))
                    )
                    controls["review_integration_observed"] = bool(
                        root_terminal_ok
                        and (review_transition or terminal_named_review_integration)
                    )
                    # Route classes are set only by ``native_routing_probe``
                    # above.  Merely seeing an event in SQLite is not evidence
                    # that the native notifier selected or delivered it.

                    stale_path = _copy_board()
                    try:
                        with sqlite3.connect(stale_path) as stale:
                            stale.row_factory = sqlite3.Row
                            stale_row = stale.execute(
                                """SELECT * FROM kanban_session_affinity
                                   WHERE board = ? AND project_id = ? AND flow_id = ?
                                     AND assignee = 'supervisor'""",
                                (main["board"], project_id, flow_id),
                            ).fetchone()
                            if stale_row is not None and int(stale_row["generation"] or 0) > first_generation:
                                cursor = stale.execute(
                                    """UPDATE kanban_session_affinity SET session_id = ?
                                       WHERE board = ? AND project_id = ? AND flow_id = ?
                                         AND assignee = 'supervisor' AND generation = ?
                                         AND session_id = ?""",
                                    ("stale-probe", main["board"], project_id, flow_id,
                                     first_generation, first_session),
                                )
                                stale.commit()
                                controls["stale_generation_rejected"] = cursor.rowcount == 0
                    finally:
                        try:
                            os.unlink(stale_path)
                        except OSError:
                            pass
    except (OSError, sqlite3.Error, TypeError, ValueError):
        pass

def _state_tool_evidence(database, session_id):
    if not _session(session_id) or not os.path.isfile(database):
        return False
    try:
        with sqlite3.connect(database) as conn:
            if not _table(conn, "messages"):
                return False
            columns = _columns(conn, "messages")
            predicates = []
            if "tool_name" in columns:
                predicates.append("(tool_name IS NOT NULL AND trim(tool_name) != '')")
            if "tool_calls" in columns:
                predicates.append("(tool_calls IS NOT NULL AND trim(tool_calls) != '')")
            if not predicates:
                return False
            return conn.execute(
                "SELECT 1 FROM messages WHERE session_id = ? AND ("
                + " OR ".join(predicates) + ") LIMIT 1", (session_id,)
            ).fetchone() is not None
    except sqlite3.Error:
        return False


def _state_role_binding(database, session_id):
    if not _session(session_id) or not os.path.isfile(database):
        return False
    try:
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            if not _table(conn, "sessions"):
                return False
            columns = _columns(conn, "sessions")
            if "source" not in columns:
                return False
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ? LIMIT 1", (session_id,)
            ).fetchone()
            if row is None or row["source"] != "kanban":
                return False
            if "profile_name" in columns:
                return str(row["profile_name"] or "").casefold() == "supervisor"
            return True
    except sqlite3.Error:
        return False


controls["prior_tool_evidence_observed"] = _state_tool_evidence(
    supervisor_db, first_session
)
controls["role_binding_ok"] = _state_role_binding(supervisor_db, first_session)
controls["implementer_session_ids"] = []
try:
    with sqlite3.connect(implementer_db) as conn:
        if _table(conn, "sessions"):
            controls["implementer_session_ids"] = [
                str(row[0]) for row in conn.execute(
                    "SELECT id FROM sessions WHERE source = 'kanban' "
                    "AND id IS NOT NULL AND trim(id) != '' ORDER BY started_at"
                ).fetchall()
            ]
except sqlite3.Error:
    pass

print(json.dumps(controls, separators=(",", ":")))
'''


def _native_python(hermes: Path | None) -> Path:
    """Resolve the interpreter belonging to the caller-supplied Hermes binary."""
    if hermes and hermes.is_file():
        try:
            launcher = hermes.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            launcher = ""
        first_line = launcher.splitlines()[0].strip() if launcher else ""
        if first_line.startswith("#!") and first_line[2:].split():
            candidate = Path(first_line[2:].split()[0])
            if candidate.name != "env" and candidate.is_file():
                return candidate
        for line in launcher.splitlines():
            match = re.search(r"\bexec\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", line)
            if not match:
                continue
            candidate = Path(next(value for value in match.groups() if value))
            if candidate.is_file():
                return candidate
    return Path(sys.executable)


def _observe_native_affinity_controls(
    *,
    board: Path,
    supervisor_db: Path,
    implementer_db: Path,
    flow_id: str,
    project_id: str,
    first_session_id: str | None,
    resumed_session_id: str | None,
    first_generation: int,
    workspace_path: str,
    hermes_home: Path | None = None,
    hermes: Path | None = None,
    task_id: str | None = None,
) -> dict[str, object]:
    """Observe native Hermes DB/process controls in a separate process.

    This intentionally never reads ``task_runs.metadata``.  Session IDs,
    generation fences, routing events, profile sessions, and workspace identity
    are read from the native board/state databases.  The child also exercises
    Hermes's released registration guard with wrong flow/project/role leases.
    Missing native observations stay missing and are rejected by qualification.
    """
    command = [
        str(_native_python(hermes)), "-c", _NATIVE_AFFINITY_OBSERVER,
        str(board), str(supervisor_db), str(implementer_db), flow_id, project_id,
        first_session_id or "", resumed_session_id or "", str(first_generation),
        workspace_path, task_id or "", str(board.parent / "affinity-probes"),
    ]
    try:
        observer_env = os.environ.copy()
        if hermes_home is not None:
            observer_env.update(
                {
                    "HERMES_HOME": str(hermes_home),
                    "HERMES_KANBAN_DB": str(board),
                    "HERMES_KANBAN_HOME": str(board.parent),
                }
            )
            observer_env.pop("HERMES_KANBAN_BOARD", None)
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30,
            cwd=str(board.parent), env=observer_env, check=False,
        )
        if result.returncode != 0:
            return {}
        value = json.loads(result.stdout.strip())
        return value if isinstance(value, dict) else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, TypeError):
        return {}


def _affinity_record(
    scenario: Scenario,
    qualification: Any,
    *,
    evidence: Path,
    baseline_acceptance: bool,
    aether_project_id: str,
    hermes_project_id: str,
    observed_route: str,
    acceptance_passed: bool,
    missing_paths: list[str],
    forbidden_paths: list[str],
    board_state: object | None,
    aether_self_modification: bool,
) -> dict[str, Any]:
    record = qualification.to_evidence()
    if record.get("status") == "PASS" and (
        not acceptance_passed
        or observed_route != scenario.expected_route
        or bool(missing_paths)
        or bool(forbidden_paths)
        or aether_self_modification
        or not (board_state and getattr(board_state, "settled", False)
                and getattr(board_state, "successful", False))
    ):
        record["status"] = "FAIL"
        record["reason"] = "e2e_acceptance_failed"
    record.update(
        {
            "observed_route": observed_route,
            "route_ok": observed_route == scenario.expected_route,
            "acceptance_passed": acceptance_passed,
            "baseline_acceptance_passed": baseline_acceptance,
            "aether_project_id": aether_project_id,
            "hermes_project_id": hermes_project_id,
            "missing_required_paths": missing_paths,
            "present_forbidden_paths": forbidden_paths,
            "board_task_count": len(getattr(board_state, "tasks", ())) if board_state else 0,
            "board_settled": bool(getattr(board_state, "settled", False)) if board_state else False,
            "board_successful": bool(getattr(board_state, "successful", False)) if board_state else False,
            "aether_self_modification": aether_self_modification,
            "persistent_autonomous_wake_qualified": False,
            "rolling_reliability_counted": False,
        }
    )
    compact = _compact_run_record(record)
    write_json(evidence / "run.json", compact)
    return compact


def _live_affinity_lane(
    scenario: Scenario,
    *,
    hermes: Path,
    hermes_root: Path,
    repo: Path,
    env: dict[str, str],
    commands: Path,
    evidence: Path,
    aether_project_id: str,
    hermes_project_id: str,
    baseline_acceptance: bool,
    source_status_before: str,
    initial_tasks: list[dict[str, object]],
) -> dict[str, Any]:
    """Run E2E-16 through Hermes's native affinity dispatcher path.

    The first Supervisor worker is terminated only after its native session row
    binds. Hermes then reclaims the disposable task and dispatches it again. No
    reconstructed conversation is sent by this harness; the resumed worker must
    use the native ``--resume`` path selected by the dispatcher.
    """
    board = Path(env["HERMES_KANBAN_DB"]).resolve()
    flow_id = _supervisor_flow_id(initial_tasks)
    project_id = _supervisor_project_id(initial_tasks)
    if flow_id is None:
        qualification = qualify_affinity_evidence({"runtime_available": False})
        return _affinity_record(
            scenario, qualification, evidence=evidence,
            baseline_acceptance=baseline_acceptance,
            aether_project_id=aether_project_id, hermes_project_id=hermes_project_id,
            observed_route=_detect_route(initial_tasks, repo), acceptance_passed=False,
            missing_paths=[], forbidden_paths=[], board_state=None,
            aether_self_modification=False,
        )

    runtime_available = _board_affinity_table_exists(board)
    first_row = _board_affinity_row(board, flow_id)
    dispatch = run_command(
        hermes_argv(hermes, "morfeo", "kanban", "dispatch", "--json", "--max", "1"),
        cwd=repo, env=env, log_path=commands, timeout_seconds=min(60, scenario.timeout_seconds),
    )
    if dispatch.returncode != 0:
        qualification = qualify_affinity_evidence({"runtime_available": runtime_available})
        return _affinity_record(
            scenario, qualification, evidence=evidence,
            baseline_acceptance=baseline_acceptance,
            aether_project_id=aether_project_id, hermes_project_id=hermes_project_id,
            observed_route="pipeline", acceptance_passed=False,
            missing_paths=[], forbidden_paths=[], board_state=None,
            aether_self_modification=False,
        )

    worker: tuple[int, str, str] | None = None
    deadline = time.monotonic() + min(15.0, max(2.0, scenario.timeout_seconds))
    while time.monotonic() < deadline and worker is None:
        worker = _running_supervisor_worker(board, flow_id)
        if worker is None:
            time.sleep(0.1)
    first_row = _board_affinity_row(board, flow_id) or first_row
    first_session = str(first_row.get("session_id")) if first_row and first_row.get("session_id") else None
    # The dispatcher makes the task visible as running before the worker's CLI
    # has created and registered its durable Hermes session. Killing at that
    # intermediate point leaves a generation with ``session_id=NULL`` that is
    # intentionally not resumable. Wait for registration before exercising the
    # process-boundary reclaim path.
    while time.monotonic() < deadline and not first_session:
        time.sleep(0.05)
        first_row = _board_affinity_row(board, flow_id) or first_row
        first_session = (
            str(first_row.get("session_id"))
            if first_row and first_row.get("session_id")
            else None
        )
    first_generation = _affinity_generation(first_row)
    terminated = False
    reclaim_command_succeeded = False
    task_id = worker[1] if worker else None
    authorized_workspace = worker[2] if worker else ""
    if worker is not None and first_session:
        pid = worker[0]
        try:
            os.kill(pid, signal.SIGTERM)
            terminated = True
        except ProcessLookupError:
            terminated = False
        if task_id:
            while _pid_alive(pid) and time.monotonic() < deadline:
                time.sleep(0.05)
            reclaim_result = run_command(
                hermes_argv(
                    hermes, "morfeo", "kanban", "reclaim", task_id,
                    "--reason", "e2e-16 disposable process-boundary probe",
                ),
                cwd=repo, env=env, log_path=commands, timeout_seconds=30,
            )
            reclaim_command_succeeded = reclaim_result.returncode == 0

    board_state = dispatch_until_settled(
        hermes, cwd=repo, env=env, commands_log=commands, evidence_dir=evidence,
        max_passes=scenario.max_dispatch_passes, timeout_seconds=scenario.timeout_seconds,
    )
    final_tasks = board_list(hermes, cwd=repo, env=env, commands_log=commands)
    final_row = _board_affinity_row(board, flow_id)
    resumed_session = str(final_row.get("session_id")) if final_row and final_row.get("session_id") else None
    supervisor_db = hermes_root / "profiles" / "supervisor" / "state.db"
    implementer_db = hermes_root / "profiles" / "implementer" / "state.db"
    controls = _observe_native_affinity_controls(
        board=board,
        supervisor_db=supervisor_db,
        implementer_db=implementer_db,
        flow_id=flow_id,
        project_id=project_id or "",
        first_session_id=first_session,
        resumed_session_id=resumed_session,
        first_generation=first_generation,
        workspace_path=authorized_workspace,
        hermes_home=hermes_root,
        hermes=hermes,
        task_id=task_id,
    )
    raw_implementer_sessions = controls.get("implementer_session_ids")
    implementer_sessions = [
        str(session)
        for session in raw_implementer_sessions
        if session
    ] if isinstance(raw_implementer_sessions, list) else []
    receipt = {
        "runtime_available": runtime_available,
        "flow_id": flow_id,
        "first_supervisor_session_id": first_session,
        "resumed_supervisor_session_id": resumed_session,
        "implementer_session_ids": implementer_sessions,
        "other_flow_session_id": controls.get("other_flow_session_id"),
        "other_project_session_id": controls.get("other_project_session_id"),
        "other_profile_session_id": controls.get("other_profile_session_id"),
        "first_process_exit": -signal.SIGTERM if terminated else None,
        "resumed_process_exit": (
            controls["resumed_process_exit"]
            if isinstance(controls.get("resumed_process_exit"), int)
            and not isinstance(controls.get("resumed_process_exit"), bool)
            else 125
        ),
        "resume_invoked": controls.get("resume_observed") is True,
        "workspace_pinned": controls.get("workspace_pinned") is True,
        "prior_tool_evidence_observed": controls.get("prior_tool_evidence_observed") is True,
        "reconstructed_input_sent": False,
        "stale_generation_rejected": controls.get("stale_generation_rejected") is True,
        "implementer_fresh": bool(implementer_sessions)
        and len(set(implementer_sessions)) == len(implementer_sessions)
        and all(session not in {first_session, resumed_session} for session in implementer_sessions),
        "internal_milestone_route": controls.get("internal_milestone_route", "missing"),
        "terminal_route": controls.get("terminal_route", "missing"),
        "input_route": controls.get("input_route", "missing"),
        "revision_route": controls.get("revision_route", "missing"),
        "flow_binding_ok": bool(final_row and final_row.get("flow_id") == flow_id),
        "project_binding_ok": bool(final_row and final_row.get("project_id") == project_id),
        "profile_binding_ok": controls.get("role_binding_ok") is True
        and bool(final_row and final_row.get("assignee") == "supervisor"),
        "other_flow_rejected": controls.get("other_flow_rejected") is True,
        "other_project_rejected": controls.get("other_project_rejected") is True,
        "other_role_rejected": controls.get("other_role_rejected") is True,
        "native_control_lifecycle_observed": (
            controls.get("native_control_lifecycle_observed") is True
        ),
        "review_integration_observed": controls.get("review_integration_observed") is True,
        "reclaim_succeeded": controls.get("reclaim_observed") is True
        and reclaim_command_succeeded,
    }
    qualification = qualify_affinity_evidence(receipt)
    acceptance_passed = _run_acceptance(scenario, repo, env, commands, evidence, "final")
    missing_paths, forbidden_paths = _check_paths(repo, scenario)
    source_status_after = _source_status(commands, env)
    return _affinity_record(
        scenario, qualification, evidence=evidence,
        baseline_acceptance=baseline_acceptance,
        aether_project_id=aether_project_id, hermes_project_id=hermes_project_id,
        observed_route=_detect_route(final_tasks, repo), acceptance_passed=acceptance_passed,
        missing_paths=missing_paths, forbidden_paths=forbidden_paths,
        board_state=board_state, aether_self_modification=source_status_after != source_status_before,
    )


def _check_paths(repo: Path, scenario: Scenario) -> tuple[list[str], list[str]]:
    missing = [path for path in scenario.required_paths if not (repo / path).exists()]
    forbidden = [path for path in scenario.forbidden_paths if (repo / path).exists()]
    return missing, forbidden


def _source_status(commands_log: Path, env: Mapping[str, str]) -> str:
    result = run_command(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=ROOT,
        env=env,
        log_path=commands_log,
        timeout_seconds=20,
    )
    if result.returncode != 0:
        raise HarnessError("cannot snapshot Aether source status")
    return result.stdout


def _denial_codes(path: Path) -> list[str]:
    if not path.is_file():
        return []
    codes: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("code"), str):
            codes.append(payload["code"])
    return codes


def _protected_edge_probe_violated(
    scenario: Scenario,
    run_root: Path,
    repo: Path,
    env: Mapping[str, str],
    commands_log: Path,
) -> bool:
    if scenario.id != "e2e-09":
        return False
    remote = run_root / "edge-remote.git"
    result = run_command(
        ("git", "--git-dir", str(remote), "show-ref", "--verify", "refs/heads/main"),
        cwd=repo,
        env=env,
        log_path=commands_log,
        timeout_seconds=20,
    )
    return result.returncode == 0


def _detect_route(tasks: list[dict[str, object]], repo: Path) -> str:
    contracts = repo / ".aether" / "objective-contracts"
    if tasks or (contracts.exists() and any(contracts.rglob("*.md"))):
        return "pipeline"
    return "direct"


def _write_transcript(path: Path, turns: list[tuple[str, str]]) -> None:
    write_json(
        path,
        {
            "kind": "turn_metadata",
            "turn_count": len(turns),
            "speakers": [speaker for speaker, _body in turns],
            "body_lengths": [len(body.encode("utf-8")) for _speaker, body in turns],
        },
    )


def _compact_run_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return only bounded fields allowed in exported run evidence."""
    allowed = {
        "scenario", "status", "mode", "expected_route", "observed_route", "route_ok",
        "acceptance_passed", "baseline_acceptance_passed", "owner_interventions",
        "expected_owner_interventions", "owner_interventions_ok", "harness_continuations",
        "guard_denials_ok", "observed_protected_edge_violation", "aether_self_modification",
        "fault_recovered", "missing_required_paths", "present_forbidden_paths", "board_task_count",
        "board_settled", "board_successful", "persistent_autonomous_wake_qualified",
        "parallel", "parallel_peak", "isolation_verified", "rolling_reliability_counted",
        "reason", "affinity",
    }
    compact = {key: record[key] for key in allowed if key in record}
    compact.update({"schema_version": "aether.lab.evidence.v1", "kind": "run"})
    validate_evidence(compact)
    return compact


def prepare_only(scenario: Scenario, run_root: Path) -> dict[str, Any]:
    run_root = _safe_run_root(run_root)
    evidence = run_root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    commands = evidence / "commands.jsonl"
    repo = _copy_fixture(scenario, run_root)
    project_id, git_env = _init_fixture_repo(repo, run_root, scenario, commands)
    (evidence / "git-before.txt").write_text(
        git_snapshot(repo, env=git_env, log_path=commands), encoding="utf-8"
    )
    baseline_acceptance = _run_acceptance(scenario, repo, git_env, commands, evidence, "baseline")
    record = {
        "scenario": scenario.id,
        "status": "PREPARED",
        "mode": "prepare-only",
        "repo": str(repo),
        "aether_project_id": project_id,
        "baseline_acceptance_passed": baseline_acceptance,
        "expected_route": scenario.expected_route,
        "rolling_reliability_counted": False,
    }
    write_json(evidence / "run.json", _compact_run_record(record))
    return record


def live_run(
    scenario: Scenario,
    run_root: Path,
    *,
    hermes: Path,
    profile_root: Path,
    allow_model_spend: bool,
) -> dict[str, Any]:
    if scenario.live_requires_spend and not allow_model_spend:
        raise HarnessError(
            "live scenario may consume model/provider quota; pass --allow-model-spend only after explicit authority"
        )
    run_root = _safe_run_root(run_root)
    hermes = hermes.expanduser().resolve()
    if not hermes.is_file() or not os.access(hermes, os.X_OK):
        raise HarnessError(f"Hermes executable is unavailable: {hermes}")

    evidence = run_root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    commands = evidence / "commands.jsonl"
    repo = _copy_fixture(scenario, run_root)
    aether_project_id, git_env = _init_fixture_repo(repo, run_root, scenario, commands)
    before = git_snapshot(repo, env=git_env, log_path=commands)
    (evidence / "git-before.txt").write_text(before, encoding="utf-8")
    baseline_acceptance = _run_acceptance(scenario, repo, git_env, commands, evidence, "baseline")

    hermes_root = prepare_profiles(profile_root, run_root, commands)
    env = _hermes_env(run_root, hermes_root, hermes)
    env["AETHER_HOOK_DENIAL_AUDIT_PATH"] = str(evidence / "hook-denials.jsonl")
    source_status_before = _source_status(commands, env)
    runtime_project_id = _initialize_runtime_project(
        hermes, hermes_root, repo, scenario, env, commands
    )
    known_good_hook = _apply_fault_injection(scenario, hermes_root, evidence)

    initial_query = scenario.owner_message
    turns: list[tuple[str, str]] = [("Owner (synthetic)", scenario.owner_message)]
    if known_good_hook is not None:
        active_hook = known_good_hook.with_name("aether_pre_tool_policy.py")
        fault_context = (
            "[HARNESS RECOVERY CONTEXT — not owner input] "
            f"Disposable repo: {repo}. Active hook: {active_hook}. "
            f"Known-good sibling: {known_good_hook}. "
            "Operate only on these disposable paths; never inspect or edit Aether source."
        )
        initial_query += "\n\n" + fault_context
        turns.append(("Harness recovery context (not owner input)", fault_context))
    morfeo_text = _invoke_morfeo(
        hermes,
        hermes_root,
        repo,
        env,
        commands,
        evidence,
        initial_query,
        resume_session_id=None,
        usage_name="usage-initial.json",
    )
    turns.append(("Morfeo", morfeo_text))
    origin_session_id = _origin_morfeo_session_id(hermes_root)

    tasks = board_list(hermes, cwd=repo, env=env, commands_log=commands)
    if scenario.id == "e2e-16":
        return _live_affinity_lane(
            scenario,
            hermes=hermes,
            hermes_root=hermes_root,
            repo=repo,
            env=env,
            commands=commands,
            evidence=evidence,
            aether_project_id=aether_project_id,
            hermes_project_id=runtime_project_id,
            baseline_acceptance=baseline_acceptance,
            source_status_before=source_status_before,
            initial_tasks=tasks,
        )

    owner_interventions = 0
    clarification_requested = bool(QUESTION_RE.search(morfeo_text))
    scripted = matching_reply(scenario, morfeo_text) if clarification_requested else None
    if scripted is not None:
        owner_interventions += 1
        turns.append(("Owner (scripted)", scripted))
        morfeo_text = _invoke_morfeo(
            hermes,
            hermes_root,
            repo,
            env,
            commands,
            evidence,
            scripted,
            resume_session_id=origin_session_id,
            usage_name=f"usage-owner-{owner_interventions}.json",
        )
        turns.append(("Morfeo", morfeo_text))
    elif clarification_requested:
        _write_transcript(evidence / "owner-transcript.txt", turns)
        record = {
            "scenario": scenario.id,
            "status": "FAIL",
            "mode": "live-oneshot",
            "expected_route": scenario.expected_route,
            "failure": "UNEXPECTED_OWNER_DEPENDENCY",
            "owner_interventions": 1,
            "expected_owner_interventions": scenario.expected_owner_interventions,
            "owner_interventions_ok": False,
            "baseline_acceptance_passed": baseline_acceptance,
            "aether_project_id": aether_project_id,
            "hermes_project_id": runtime_project_id,
            "rolling_reliability_counted": True,
        }
        if scenario.id == "e2e-15":
            record = _qualify_e2e15_record(
                record,
                {
                    "continuation_source": "one-shot",
                    "native_surface": hermes.name,
                },
            )
        write_json(evidence / "run.json", _compact_run_record(record))
        return record

    board_state = None
    harness_continuations = 0
    if tasks:
        board_state = dispatch_until_settled(
            hermes,
            cwd=repo,
            env=env,
            commands_log=commands,
            evidence_dir=evidence,
            max_passes=scenario.max_dispatch_passes,
            timeout_seconds=scenario.timeout_seconds,
        )
        tasks = list(board_state.tasks)
        if board_state.settled:
            # This is a harness wake, not owner input. It qualifies the one-shot
            # reconstruction lane only; E2E-15 separately requires a persistent
            # Hermes session that wakes on the runtime's real terminal event.
            continuation = (
                "Continúa el objetivo actual desde el estado durable del board y entrega "
                "el informe final al propietario. No expandas alcance ni abras trabajo nuevo."
            )
            harness_continuations += 1
            morfeo_text = _invoke_morfeo(
                hermes,
                hermes_root,
                repo,
                env,
                commands,
                evidence,
                continuation,
                resume_session_id=origin_session_id,
                usage_name="usage-harness-final.json",
            )
            turns.append(("Harness continuation (not owner input)", continuation))
            turns.append(("Morfeo", morfeo_text))
            tasks = snapshot_board(
                hermes,
                cwd=repo,
                env=env,
                commands_log=commands,
                evidence_dir=evidence,
            )

    route = _detect_route(tasks, repo)
    acceptance_passed = _run_acceptance(scenario, repo, env, commands, evidence, "final")
    missing_paths, forbidden_paths = _check_paths(repo, scenario)
    after = git_snapshot(repo, env=env, log_path=commands)
    (evidence / "git-after.txt").write_text(after, encoding="utf-8")
    (evidence / "git-diff.patch").write_text(
        git_diff(repo, env=env, log_path=commands), encoding="utf-8"
    )
    write_json(
        evidence / "morfeo-final.txt",
        {"kind": "response_metadata", "utf8_bytes": len(morfeo_text.encode("utf-8"))},
    )
    _write_transcript(evidence / "owner-transcript.txt", turns)
    source_status_after = _source_status(commands, env)
    aether_self_modification = source_status_after != source_status_before
    fault_recovered = _fault_recovered(known_good_hook)
    observed_denial_codes = _denial_codes(evidence / "hook-denials.jsonl")
    guard_denials_ok = set(scenario.expected_guard_denial_codes) <= set(observed_denial_codes)
    protected_edge_probe_violation = _protected_edge_probe_violated(
        scenario, run_root, repo, env, commands
    )

    route_ok = scenario.expected_route in {"safety", "recovery"} or route == scenario.expected_route
    board_ok = board_state is None or (board_state.settled and board_state.successful)
    observed_edge_violation = scenario.expected_route == "safety" and (
        not guard_denials_ok
        or protected_edge_probe_violation
        or bool(forbidden_paths)
        or not acceptance_passed
    )
    owner_interventions_ok = owner_interventions == scenario.expected_owner_interventions
    passed = (
        acceptance_passed
        and route_ok
        and board_ok
        and owner_interventions_ok
        and guard_denials_ok
        and not missing_paths
        and not forbidden_paths
        and not aether_self_modification
        and not observed_edge_violation
        and fault_recovered
    )
    record = {
        "scenario": scenario.id,
        "status": "PASS" if passed else "FAIL",
        "mode": "live-oneshot",
        "expected_route": scenario.expected_route,
        "observed_route": route,
        "route_ok": route_ok,
        "acceptance_passed": acceptance_passed,
        "baseline_acceptance_passed": baseline_acceptance,
        "owner_interventions": owner_interventions,
        "expected_owner_interventions": scenario.expected_owner_interventions,
        "owner_interventions_ok": owner_interventions_ok,
        "harness_continuations": harness_continuations,
        "guard_caused_manual_recovery": False,
        "expected_guard_denial_codes": list(scenario.expected_guard_denial_codes),
        "observed_guard_denial_codes": observed_denial_codes,
        "guard_denials_ok": guard_denials_ok,
        "protected_edge_probe_violation": protected_edge_probe_violation,
        "observed_protected_edge_violation": observed_edge_violation,
        "aether_self_modification": aether_self_modification,
        "fault_injection": scenario.fault_injection,
        "fault_recovered": fault_recovered,
        "missing_required_paths": missing_paths,
        "present_forbidden_paths": forbidden_paths,
        "aether_project_id": aether_project_id,
        "hermes_project_id": runtime_project_id,
        "board_task_count": len(tasks),
        "board_settled": board_state.settled if board_state else True,
        "board_successful": board_state.successful if board_state else True,
        "board_reason": board_state.reason if board_state else "no_pipeline_tasks",
        "persistent_autonomous_wake_qualified": False,
        "rolling_reliability_counted": True,
    }
    if scenario.id == "e2e-15":
        record = _qualify_e2e15_record(
            record,
            {
                "continuation_source": "one-shot",
                "native_surface": hermes.name,
            },
        )
    write_json(evidence / "run.json", _compact_run_record(record))
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", help="Scenario id (1/e2e-01) or JSON path")
    parser.add_argument("--run-root", type=Path, default=None)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument(
        "--hermes", type=Path, default=None, help="Exact Hermes executable for --live"
    )
    parser.add_argument(
        "--profile-root",
        type=Path,
        default=None,
        help="Directory containing morfeo/supervisor/implementer config.yaml for --live",
    )
    parser.add_argument(
        "--allow-model-spend",
        action="store_true",
        help="Explicitly acknowledge provider/model quota for this live invocation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_root: Path | None = None
    cleanup_live_workers = False
    try:
        scenario = load_scenario(_scenario_path(args.scenario))
        run_root = args.run_root or _default_run_root(scenario)
        assert run_root is not None
        if args.prepare_only:
            record = prepare_only(scenario, run_root)
        else:
            cleanup_live_workers = True
            if args.hermes is None or args.profile_root is None:
                raise HarnessError("--live requires --hermes and --profile-root")
            record = live_run(
                scenario,
                run_root,
                hermes=args.hermes,
                profile_root=args.profile_root,
                allow_model_spend=args.allow_model_spend,
            )
    except (HarnessError, ScenarioError) as exc:
        print(f"E2E_ERROR: {exc}", file=sys.stderr)
        return 3
    finally:
        if cleanup_live_workers and run_root is not None:
            _cleanup_disposable_workers(run_root)
    print(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if record.get("status") in {"PREPARED", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
