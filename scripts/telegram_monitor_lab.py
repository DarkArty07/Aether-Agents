"""D13 isolated native-runtime laboratory context for the Telegram Monitor qualification.

The laboratory is the qualification substrate owned by
``specs/telegram-monitor/qualification-isolation.md``: one private, exclusive root outside
every Git worktree that gives the monitor's own native code a private ``HOME``,
``HERMES_HOME``, XDG roots, temporary directory, working directory and Aether state root.
Inside it the shipped product and native Hermes code run unchanged — one lab monitor job,
one bounded supervised instance of the native cron scheduler, the existing provisioned
model and Telegram route — while this installation's registered projects, boards,
sessions, cron jobs and monitor state stay where they are and are never hidden, swapped or
restored.

Two properties are the whole point of this module, and both are enforced before the
harness may spend anything:

* **Containment.**  Every mutable root a lab child could write to is redirected inside the
  lab root, and :func:`context_problems` refuses a context in which any of them resolves
  outside it.  There is no code in this module — and none in the harness — that renames,
  unlinks, quarantines or replaces an entry of the operator's project registry.
* **Borrowed access, no new secrets.**  The lab reuses only the access this installation
  already provisioned for the exact route and destination
  (:func:`required_access`, :func:`collect_access`) and passes it to lab children through
  their process environment only.  No credential is acquired, refreshed, widened or
  written into the lab root, a test file or a receipt; :func:`access_fingerprint` reports
  the borrowed names and their presence, never a value.
* **Resolved writer surface.**  The synthetic scope is seeded only through native writers
  whose presence and accepted keywords are resolved in the provisioned runtime before the
  first write (:data:`WRITER_REQUIREMENTS`), together with the loaded artifact digests and
  entry points of the modules the laboratory depends on (:data:`WRITER_ARTIFACT_MODULES`)
  and the roots those modules effectively resolve (:data:`WRITER_EFFECTIVE_ROOTS`).  An
  incompatible revision refuses fail-closed
  (:func:`writer_problems`, e.g. ``writer-interface-missing:…`` or
  ``writer-root-escape:…``) instead of failing mid-lane after the laboratory was created.

Configuration is a decision-only projection of the provisioned Morfeo profile
(:func:`minimal_config`): model, provider, fallback, toolset, limits, timezone and
transport decisions are preserved, while sessions, memories, jobs, boards, the project
registry, authentication stores and every credential are not copied.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:  # pragma: no cover - import-order bootstrap
    sys.path.insert(0, str(SOURCE_ROOT))

from aether_agents.paths import ensure_private_dir  # noqa: E402

__all__ = [
    "ACCESS_ENV_NAMES",
    "LAB_CONFIG_NAME",
    "LAB_FILE_MODE",
    "LAB_MODE",
    "LAB_PROFILE",
    "LAB_RECORD_NAME",
    "LabError",
    "LabPlan",
    "WRITER_ARTIFACT_MODULES",
    "WRITER_REQUIREMENTS",
    "access_fingerprint",
    "build_plan",
    "child_environment",
    "collect_access",
    "config_digest",
    "context_problems",
    "create_root",
    "minimal_config",
    "path_problems",
    "plan_record",
    "required_access",
    "writer_problems",
    "writer_summary",
    "write_config",
    "write_plugin_metadata",
    "write_record",
]

#: The laboratory is a private subtree of the operator's Aether state root.  It is never
#: placed inside a Git worktree and never inside the monitor's own state directories.
LAB_SUBDIRECTORY = ("monitor", "lab")
LAB_PROFILE = "morfeo"
LAB_RECORD_NAME = "lab.json"
LAB_CONFIG_NAME = "config.yaml"
LAB_MODE = 0o700
LAB_FILE_MODE = 0o600

#: ``<stamp>-<random>``: the name is unguessable enough to be created exclusively.
_LAB_NAME = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$", re.ASCII)

#: Private roots every lab child is given, relative to the lab root.
LAB_HOME_DIR = "home"
LAB_HERMES_DIR = "hermes"
LAB_PLUGINS_META_DIR = "plugins_meta"
LAB_TMP_DIR = "tmp"
LAB_WORK_DIR = "work"
LAB_XDG_DIRS: Mapping[str, str] = {
    "XDG_STATE_HOME": "xdg-state",
    "XDG_DATA_HOME": "xdg-data",
    "XDG_CONFIG_HOME": "xdg-config",
    "XDG_CACHE_HOME": "xdg-cache",
    "XDG_RUNTIME_DIR": "xdg-runtime",
}

#: Inherited production routing selectors.  A lab child must never see these: they decide
#: which board, session, tenant or state tree native code reads and writes, so an inherited
#: value would send lab writes back into this installation.  Nothing else is stripped — in
#: particular the delegated identity and the guard/approval policy of the operator's
#: environment stay visible to the lab children.
INHERITED_SELECTORS: tuple[str, ...] = (
    "HERMES_HOME",
    "HERMES_PROFILE",
    "HERMES_SESSION_ID",
    "HERMES_TENANT",
    "HERMES_KANBAN_DB",
    "HERMES_KANBAN_BOARD",
    "HERMES_KANBAN_TASK",
    "HERMES_KANBAN_RUN_ID",
    "HERMES_KANBAN_WORKSPACES_ROOT",
    "HERMES_KANBAN_GOAL_MAX_TURNS",
    "TMPDIR",
    "AETHER_MONITOR_QUALIFICATION_SCHEDULE",
    *LAB_XDG_DIRS,
)
INHERITED_SELECTOR_PREFIXES: tuple[str, ...] = ("HERMES_KANBAN_",)

#: Access the lab children may receive through their process environment only.  The
#: provisioned profile's ``.env`` is the operator's own source; the names below are the
#: transport names the existing Telegram route needs and are always required.
ACCESS_ENV_NAMES: tuple[str, ...] = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_HOME_CHANNEL",
    "TELEGRAM_HOME_CHANNEL_THREAD_ID",
    "TELEGRAM_HOME_CHANNEL_NAME",
)
#: Always required: without the token or the destination route there is no lab run.
ACCESS_REQUIRED: tuple[str, ...] = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL")

#: Secret-bearing keys that are never projected into the lab configuration.
_SECRET_KEYS = ("api_key", "token", "secret", "password", "credential")

#: Sections projected from the provisioned profile: decisions only, no state, no secrets.
_CONFIG_SECTIONS = (
    "model",
    "providers",
    "fallback_providers",
    "toolsets",
    "timezone",
    "gateway",
    "plugins",
)

#: Pinned candidate monitor distribution metadata written to the lab's plugins_meta directory.
PLUGIN_DIST_NAME = "aether_agents_candidate_monitor-0.24.0.dist-info"
PLUGIN_ENTRY_POINT_TEXT = """[hermes_agent.plugins]
aether-telegram-monitor = aether_agents.monitor.hermes_plugin
"""
PLUGIN_METADATA_TEXT = """Metadata-Version: 2.1
Name: aether-agents-candidate-monitor
Version: 0.24.0
"""
_AGENT_DECISION_KEYS = (
    "name",
    "role",
    "max_turns",
    "api_max_retries",
    "reasoning_effort",
    "tool_use_enforcement",
    "verify_on_stop",
    "image_input_mode",
    "keep_alive",
)


class LabError(RuntimeError):
    """A bounded laboratory failure with a stable public code.

    ``message`` stays sanitized (it can reach the public summary); ``detail`` carries
    private diagnostics that only the operator-selected receipt receives.
    """

    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


@dataclass(frozen=True)
class LabPlan:
    """The private laboratory layout, resolved but not yet created."""

    stamp: str
    token: str
    state_root: Path
    root: Path
    home: Path
    hermes_home: Path
    profile_home: Path
    plugins_meta: Path
    tmp: Path
    cwd: Path
    xdg: Mapping[str, Path]

    @property
    def lab_state_root(self) -> Path:
        """The Aether state root a lab child resolves (``XDG_STATE_HOME/aether``)."""

        return Path(self.xdg["XDG_STATE_HOME"]) / "aether"

    @property
    def lab_hermes_state(self) -> Path:
        """The native Hermes state tree a lab child resolves."""

        return self.hermes_home

    def named_roots(self) -> Mapping[str, Path]:
        return {
            "home": self.home,
            "hermes_home": self.hermes_home,
            "profile_home": self.profile_home,
            "plugins_meta": self.plugins_meta,
            "tmp": self.tmp,
            "cwd": self.cwd,
            **{name: Path(path) for name, path in self.xdg.items()},
        }


def build_plan(state_root: Path | str, stamp: str, *, token: str | None = None) -> LabPlan:
    """Resolve the laboratory layout under ``state_root`` for one run.

    The name is ``<stamp>-<random>``: unique enough to be created exclusively, and never
    derived from an operator input.
    """

    root_state = Path(state_root).expanduser()
    if not root_state.is_absolute():
        raise LabError("lab-plan", "the Aether state root must be absolute to host the laboratory")
    if _LAB_NAME.fullmatch(stamp) is None and not re.fullmatch(
        r"^[0-9]{8}T[0-9]{6}Z", stamp, re.ASCII
    ):
        raise LabError("lab-plan", "the laboratory stamp is not a UTC timestamp")
    token = token or os.urandom(6).hex()
    if re.fullmatch(r"[0-9a-f]{12}", token, re.ASCII) is None:
        raise LabError("lab-plan", "the laboratory name token is not 12 hexadecimal digits")
    name = f"{stamp}-{token}"
    if _LAB_NAME.fullmatch(name) is None:
        raise LabError("lab-plan", "the laboratory name is not the documented shape")
    root = root_state.joinpath(*LAB_SUBDIRECTORY) / name
    profile_home = root / LAB_HERMES_DIR / "profiles" / LAB_PROFILE
    return LabPlan(
        stamp=stamp,
        token=token,
        state_root=root_state,
        root=root,
        home=root / LAB_HOME_DIR,
        hermes_home=profile_home,
        profile_home=profile_home,
        plugins_meta=root / LAB_PLUGINS_META_DIR,
        tmp=root / LAB_TMP_DIR,
        cwd=root / LAB_WORK_DIR,
        xdg={name: root / relative for name, relative in LAB_XDG_DIRS.items()},
    )


def plan_record(plan: LabPlan) -> dict[str, Any]:
    """Return the durable laboratory record written inside the lab root."""

    return {
        "schema_version": "aether.telegram-monitor.qualification-lab.v1",
        "stamp": plan.stamp,
        "profile": LAB_PROFILE,
        "root": str(plan.root),
        "roots": {name: str(path) for name, path in plan.named_roots().items()},
        "state_root": str(plan.lab_state_root),
        "retained": True,
    }


def path_problems(plan: LabPlan, *, inside_repository: Callable[[Path], bool]) -> list[str]:
    """Read-only laboratory layout checks; every problem is fail-closed.

    ``inside_repository`` is the harness' own Git containment predicate, so the lab root
    and its private parents can never be placed inside a worktree or the checkout.
    """

    problems: list[str] = []
    if not plan.root.is_absolute():
        problems.append("lab-root-not-absolute")
    if inside_repository(plan.root):
        problems.append("lab-root-inside-repository")
    if plan.root == plan.state_root:
        problems.append("lab-root-is-state-root")
    if plan.lab_state_root == plan.state_root:
        problems.append("lab-state-root-aliases-production")
    if plan.root.exists() or plan.root.is_symlink():
        problems.append("lab-root-exists")
    for parent in (plan.root.parent, plan.root.parent.parent):
        try:
            if parent.is_symlink():
                problems.append(f"lab-parent-symlink:{parent.name}")
        except OSError:
            problems.append(f"lab-parent-unreadable:{parent.name}")
    return problems


def create_root(plan: LabPlan) -> dict[str, Any]:
    """Create the private laboratory root exclusively and return its record.

    Every component is created with mode ``0700`` and verified afterwards to be a real
    directory owned by this process and reachable without following a symlink.  An
    existing root is never adopted or reused: the caller refuses with the bounded
    ``lab-root-exists`` code instead.
    """

    try:
        # ``ensure_private_dir`` hardens exactly the components it creates plus the leaf,
        # so the operator's own state directories are never re-moded by the laboratory.
        ensure_private_dir(plan.root.parent)
    except (OSError, ValueError) as error:
        raise LabError(
            "lab-root-unavailable",
            "the private laboratory root could not be prepared",
            detail={"error": type(error).__name__},
        ) from error
    try:
        plan.root.mkdir(mode=LAB_MODE)
    except FileExistsError as error:
        raise LabError(
            "lab-root-exists",
            "the laboratory root already exists; a lab is created exclusively and never reused",
        ) from error
    except OSError as error:
        raise LabError(
            "lab-root-unavailable",
            "the private laboratory root could not be created",
            detail={"error": type(error).__name__},
        ) from error
    _harden_directory(plan.root)
    hermes_dir = plan.root / LAB_HERMES_DIR
    hermes_dir.mkdir(parents=True, exist_ok=True)
    _harden_directory(hermes_dir)
    profiles_dir = hermes_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    _harden_directory(profiles_dir)
    for path in plan.named_roots().values():
        path.mkdir(parents=True, exist_ok=True)
        _harden_directory(path)
    plan.profile_home.mkdir(parents=True, exist_ok=True)
    _harden_directory(plan.profile_home)
    # The lab's own Aether state root exists before the first child runs, so the product
    # resolves it inside the laboratory and the retention check has a real object.
    plan.lab_state_root.mkdir(parents=True, exist_ok=True)
    _harden_directory(plan.lab_state_root)
    write_plugin_metadata(plan)
    record = plan_record(plan)
    write_record(plan, record)
    problems = [
        name for name, path in plan.named_roots().items() if not path.is_dir() or path.is_symlink()
    ]
    if problems:
        raise LabError(
            "lab-root-incomplete",
            "a private laboratory root is missing or is not a real directory",
            detail={"roots": problems},
        )
    for name, path in plan.named_roots().items():
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
        except OSError as error:
            raise LabError(
                "lab-root-unreadable",
                "a private laboratory root could not be verified",
                detail={"root": name, "error": type(error).__name__},
            ) from error
        if mode != LAB_MODE:
            raise LabError(
                "lab-root-not-private",
                "a private laboratory root is not restricted to the current user",
                detail={"root": name},
            )
    return record


def _harden_directory(path: Path, *, exclusive: bool = True) -> None:
    try:
        info = path.stat()
    except OSError as error:
        raise LabError(
            "lab-root-unavailable",
            "a private laboratory directory could not be inspected",
            detail={"error": type(error).__name__},
        ) from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise LabError(
            "lab-root-not-private",
            "a laboratory path component is a symlink or not a directory",
            detail={"exclusive": exclusive},
        )
    os.chmod(path, LAB_MODE)
    after = path.stat()
    if stat.S_IMODE(after.st_mode) != LAB_MODE:
        raise LabError(
            "lab-root-not-private",
            "a laboratory directory could not be restricted to the current user",
        )


def minimal_config(provisioned: Mapping[str, Any]) -> dict[str, Any]:
    """Project the provisioned profile onto the decisions a lab child needs.

    Nothing from the operator's runtime state is copied: no sessions, memories, cron jobs,
    boards, project registry, authentication store or credential.  ``gateway`` is reduced
    to the transport decisions; a transport secret is never projected.
    """

    config: dict[str, Any] = {}
    for section in _CONFIG_SECTIONS:
        if section not in provisioned:
            continue
        # Every projected section is copied through the recursive projection, so a
        # secret-bearing key is dropped at any depth — ``model.api_key`` and
        # ``gateway.platforms.<platform>.token`` included.  ``key_env`` entries survive
        # because they name an environment variable and carry no value.
        config[section] = _project(provisioned[section])
    agent = provisioned.get("agent")
    if isinstance(agent, Mapping):
        config["agent"] = {key: agent[key] for key in _AGENT_DECISION_KEYS if key in agent}
    plugins = config.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
    enabled_plugins = plugins.get("enabled")
    if not isinstance(enabled_plugins, list):
        enabled_plugins = []
    else:
        enabled_plugins = list(enabled_plugins)
    if "aether-telegram-monitor" not in enabled_plugins:
        enabled_plugins.append("aether-telegram-monitor")
    plugins["enabled"] = enabled_plugins

    entries = plugins.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    else:
        entries = dict(entries)
    monitor_entry = entries.get("aether-telegram-monitor")
    if not isinstance(monitor_entry, dict):
        monitor_entry = {}
    else:
        monitor_entry = dict(monitor_entry)
    monitor_settings = monitor_entry.get("settings")
    if not isinstance(monitor_settings, dict):
        monitor_settings = {}
    else:
        monitor_settings = dict(monitor_settings)
    monitor_settings["enabled"] = True
    monitor_entry["settings"] = monitor_settings
    entries["aether-telegram-monitor"] = monitor_entry
    plugins["entries"] = entries
    config["plugins"] = plugins
    return config


def _project(value: Any) -> Any:
    """Copy a provisioned decision subtree without any secret-bearing key, at any depth."""

    if isinstance(value, Mapping):
        return {
            str(key): _project(child)
            for key, child in value.items()
            if str(key) not in _SECRET_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_project(item) for item in value]
    return value


def config_digest(config: Mapping[str, Any]) -> str:
    """Digest the decision-only configuration (it carries no credential by construction)."""

    encoded = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def required_access(config: Mapping[str, Any]) -> tuple[str, ...]:
    """The environment names a lab child needs for the exact provisioned route.

    The destination and model transport names are fixed by the shipped interfaces; the
    provisioned provider decisions add the credential names they declare through
    ``key_env``.  No value is read here.
    """

    names: list[str] = list(ACCESS_ENV_NAMES)
    providers = config.get("providers")
    if isinstance(providers, Mapping):
        for entry in providers.values():
            if isinstance(entry, Mapping):
                key_env = entry.get("key_env")
                if isinstance(key_env, str) and key_env.strip():
                    names.append(key_env.strip())
    model = config.get("model")
    if isinstance(model, Mapping):
        key_env = model.get("key_env")
        if isinstance(key_env, str) and key_env.strip():
            names.append(key_env.strip())
    ordered: list[str] = []
    for name in (*names, *ACCESS_REQUIRED):
        if name not in ordered:
            ordered.append(name)
    return tuple(ordered)


def collect_access(
    *,
    names: Sequence[str],
    environ: Mapping[str, str],
    env_files: Iterable[Path],
    required: Sequence[str] = ACCESS_REQUIRED,
) -> dict[str, str]:
    """Borrow the already provisioned access values into memory, for one lab run.

    Values come from the operator's own process environment or from the provisioned
    profile environment file, and are never written to the lab root, a test file or a
    receipt.  ``required`` names that cannot be borrowed are a fail-closed preflight gap:
    the laboratory must not start live spending without the exact provisioned route.  A
    declared but genuinely absent optional name (a destination without a thread) is
    simply not carried.
    """

    from_files: dict[str, str] = {}
    for path in env_files:
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in from_files:
                from_files[key] = _unquote(value.strip())
    access: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = environ.get(name) or from_files.get(name)
        if isinstance(value, str) and value.strip():
            access[name] = value
        elif name in required:
            missing.append(name)
    if missing:
        raise LabError(
            "lab-access-missing",
            "the already provisioned access for the exact route and destination is "
            "unavailable in this private process context; no credential is acquired or "
            "refreshed for the laboratory",
            detail={"missing": sorted(missing)},
        )
    return access


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def access_fingerprint(access: Mapping[str, str]) -> dict[str, Any]:
    """Report which borrowed names are present, never a value or a value digest."""

    return {
        "names": sorted(access),
        "present": {name: bool(value) for name, value in sorted(access.items())},
    }


def child_environment(
    plan: LabPlan,
    *,
    base: Mapping[str, str],
    access: Mapping[str, str],
    repository_src: Path,
) -> dict[str, str]:
    """Build the private environment a lab child runs with.

    Every mutable root is redirected inside the lab root, every inherited production
    routing selector is removed, and the borrowed access is carried in the process
    environment only.  Nothing here is written to disk.
    """

    environment: dict[str, str] = {}
    for name, value in base.items():
        if name in INHERITED_SELECTORS:
            continue
        if any(name.startswith(prefix) for prefix in INHERITED_SELECTOR_PREFIXES):
            continue
        environment[name] = value
    environment["HOME"] = str(plan.home)
    environment["HERMES_HOME"] = str(plan.hermes_home)
    environment["TMPDIR"] = str(plan.tmp)
    for name, path in plan.xdg.items():
        environment[name] = str(path)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    existing_pythonpath = base.get("PYTHONPATH", "")
    parts = [str(repository_src), str(plan.plugins_meta)]
    if existing_pythonpath:
        parts.append(existing_pythonpath)
    environment["PYTHONPATH"] = os.pathsep.join(parts)
    environment.update({name: value for name, value in access.items()})
    return environment


def context_problems(plan: LabPlan, environment: Mapping[str, str]) -> list[str]:
    """Fail-closed verification that a built child context writes only inside the lab.

    A redirected root that is missing, relative, a symlink or that resolves outside the
    laboratory root means an inherited selector or a link would send lab writes into this
    installation: the lab refuses before any effect.
    """

    problems: list[str] = []
    root = plan.root
    try:
        resolved_root = root.resolve(strict=False)
    except OSError:
        return ["lab-root-unresolvable"]
    for name, expected in (
        ("HOME", plan.home),
        ("HERMES_HOME", plan.hermes_home),
        ("TMPDIR", plan.tmp),
        *((key, Path(path)) for key, path in plan.xdg.items()),
    ):
        value = environment.get(name)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{name}-unset")
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            problems.append(f"{name}-not-absolute")
            continue
        if candidate != expected:
            problems.append(f"{name}-not-lab")
            continue
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            problems.append(f"{name}-unresolvable")
            continue
        if resolved != resolved_root and resolved_root not in resolved.parents:
            problems.append(f"{name}-escapes-lab")
    try:
        resolved_meta = plan.plugins_meta.resolve(strict=False)
    except OSError:
        problems.append("plugins-meta-unresolvable")
    else:
        if resolved_meta != resolved_root and resolved_root not in resolved_meta.parents:
            problems.append("plugins-meta-escapes-lab")
    pythonpath = environment.get("PYTHONPATH", "")
    pythonpath_parts = [p for p in pythonpath.split(os.pathsep) if p]
    if not pythonpath_parts:
        problems.append("pythonpath-unset")
    elif str(plan.plugins_meta) not in pythonpath_parts:
        problems.append("plugins-meta-not-in-pythonpath")
    return problems


#: The native writer surface the shipped-writer fixture depends on.  Each entry is
#: ``(qualified name, required parameters)``: the fixture may only seed the synthetic
#: scope through calls whose presence *and* accepted keywords are resolved inside the
#: created private laboratory before the first write, so an incompatible revision refuses
#: fail-closed instead of failing mid-lane after the first writer call.
WRITER_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hermes_state.SessionDB.create_session", ("cwd", "git_repo_root", "profile_name")),
    ("hermes_state.SessionDB.set_session_title", ()),
    ("hermes_cli.kanban_db.create_board", ("name", "default_workdir", "project_id")),
    ("hermes_cli.kanban_db.connect", ()),
    (
        "hermes_cli.kanban_db.create_task",
        (
            "title",
            "body",
            "assignee",
            "created_by",
            "workspace_kind",
            "workspace_path",
            "initial_status",
            "session_id",
            "board",
        ),
    ),
    ("hermes_cli.kanban_db.link_tasks", ()),
    ("hermes_cli.kanban_db.complete_task", ("result", "summary")),
    ("hermes_cli.kanban_db.request_review", ("summary", "with_reason")),
    ("hermes_cli.projects_db.connect", ()),
    ("hermes_cli.projects_db.create_project", ("name", "primary_path", "board_slug")),
)

#: Loaded modules whose resolved artifact digest and entry points are recorded as the
#: laboratory's exact-candidate loading evidence (D13 §Laboratory bootstrap 2).  A module
#: without a readable file digest refuses the lane: a source branch name is not evidence.
WRITER_ARTIFACT_MODULES: tuple[str, ...] = (
    "hermes_state",
    "hermes_cli.kanban_db",
    "hermes_cli.projects_db",
    "cron.scheduler_provider",
    "cron.jobs",
    "aether_agents.monitor.runtime",
    "aether_agents.monitor.delivery",
    "gateway.config",
)

#: Entry points whose accepted keywords are validated by a second funnel: the effective
#: keyword set is the union of the entry point's own parameters and its funnel's.  The
#: session store is the case that needs this — ``create_session(session_id, source,
#: **kwargs)`` forwards to ``_insert_session_row``, which owns the accepted keywords.
WRITER_PARAMETER_FUNNELS: Mapping[str, tuple[str, ...]] = {
    "hermes_state.SessionDB.create_session": ("hermes_state.SessionDB._insert_session_row",),
}

#: Effective roots a lab child must resolve inside the laboratory before its first write.
#: ``HERMES_HOME`` alone is not enough: an inherited explicit board/session selector would
#: otherwise send native writes back into this installation.  Each value is
#: ``module:callable`` and is resolved, never assumed.
WRITER_EFFECTIVE_ROOTS: tuple[tuple[str, str], ...] = (
    ("hermes_home", "hermes_constants:get_hermes_home"),
    ("kanban_home", "hermes_cli.kanban_db:kanban_home"),
    ("kanban_db", "hermes_cli.kanban_db:kanban_db_path"),
    ("boards_root", "hermes_cli.kanban_db:boards_root"),
    ("projects_db", "hermes_cli.projects_db:projects_db_path"),
)


def writer_problems(payload: Mapping[str, Any], *, lab_root: Path | str) -> list[str]:
    """Fail-closed verification of the native writer surface a lab child will use.

    ``payload`` is the laboratory's own read-only child probe: the resolved writer
    interfaces, the loaded artifact digests and the effective roots the child actually
    resolves.  Every problem is a bounded code, and the caller refuses the lane before any
    effect when any is present.
    """

    problems: list[str] = []
    interfaces = payload.get("writers")
    interfaces = interfaces if isinstance(interfaces, Mapping) else {}
    for name, parameters in WRITER_REQUIREMENTS:
        entry = interfaces.get(name)
        if not isinstance(entry, Mapping) or not entry.get("present"):
            problems.append(f"writer-interface-missing:{name}")
            continue
        accepted = entry.get("parameters")
        accepted = {str(item) for item in accepted} if isinstance(accepted, Sequence) else set()
        for parameter in parameters:
            if parameter not in accepted:
                problems.append(f"writer-parameter-missing:{name}:{parameter}")
    artifacts = payload.get("artifacts")
    artifacts = artifacts if isinstance(artifacts, Mapping) else {}
    for module in WRITER_ARTIFACT_MODULES:
        entry = artifacts.get(module)
        digest = entry.get("sha256") if isinstance(entry, Mapping) else None
        if not isinstance(digest, str) or len(digest) != 64:
            problems.append(f"writer-artifact-missing:{module}")
    problems.extend(_effective_root_problems(payload, lab_root=lab_root))
    return problems


def _effective_root_problems(payload: Mapping[str, Any], *, lab_root: Path | str) -> list[str]:
    """A lab child whose effective root escapes the laboratory is refused, not trusted."""

    problems: list[str] = []
    try:
        resolved_lab = Path(lab_root).resolve(strict=False)
    except OSError:
        return ["writer-root-unresolvable"]
    effective = payload.get("effective")
    effective = effective if isinstance(effective, Mapping) else {}
    for name, _ in WRITER_EFFECTIVE_ROOTS:
        value = effective.get(name)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"writer-root-unset:{name}")
            continue
        try:
            resolved = Path(value).resolve(strict=False)
        except OSError:
            problems.append(f"writer-root-unresolvable:{name}")
            continue
        if resolved != resolved_lab and resolved_lab not in resolved.parents:
            problems.append(f"writer-root-escape:{name}")
    return problems


def writer_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The decision-only projection of the writer probe: names, counts and digests.

    No interpreter path, module path, home or handle leaves this function — the receipt may
    carry the full probe, while the public summary may carry only this.
    """

    interfaces = payload.get("writers")
    interfaces = interfaces if isinstance(interfaces, Mapping) else {}
    artifacts = payload.get("artifacts")
    artifacts = artifacts if isinstance(artifacts, Mapping) else {}
    effective = payload.get("effective")
    effective = effective if isinstance(effective, Mapping) else {}
    wanted = {name for name, _ in WRITER_REQUIREMENTS}
    return {
        "required_interfaces": sorted(wanted),
        "present_interfaces": sorted(
            name
            for name, entry in interfaces.items()
            if isinstance(entry, Mapping) and entry.get("present")
        ),
        "artifact_modules": sorted(artifacts),
        "artifact_digests": {
            str(module): str(entry.get("sha256"))
            for module, entry in sorted(artifacts.items())
            if isinstance(entry, Mapping) and entry.get("sha256")
        },
        "installed_distributions": payload.get("installed_distributions"),
        "entry_points": sorted(
            str(name) for name in (payload.get("entry_points") or ()) if isinstance(name, str)
        ),
        "effective_roots_resolved": sorted(str(name) for name in effective),
    }


def write_config(plan: LabPlan, text: str) -> Path:
    """Write the decision-only lab configuration ``0600`` inside the private root.

    ``text`` is produced by the provisioned runtime probe, which owns the native
    configuration format; :func:`serialize_config` is the deterministic fallback the
    offline lane can exercise without a native import.
    """

    path = plan.profile_home / LAB_CONFIG_NAME
    _write_private(path, text)
    return path


def write_plugin_metadata(plan: LabPlan) -> Path:
    """Write the laboratory-scoped pinned candidate plugin distribution metadata."""

    dist_dir = plan.plugins_meta / PLUGIN_DIST_NAME
    dist_dir.mkdir(parents=True, exist_ok=True)
    _harden_directory(dist_dir)
    ep_file = dist_dir / "entry_points.txt"
    meta_file = dist_dir / "METADATA"
    _write_private(ep_file, PLUGIN_ENTRY_POINT_TEXT)
    _write_private(meta_file, PLUGIN_METADATA_TEXT)
    return dist_dir


def serialize_config(config: Mapping[str, Any]) -> str:
    """Serialize the decision mapping for the lab configuration file.

    The mapping holds plain scalars, lists and mappings only, so a JSON document is a valid
    YAML 1.1/1.2 document and the native loader reads it unchanged.
    """

    return json.dumps(config, indent=2, sort_keys=True) + "\n"


def write_record(plan: LabPlan, record: Mapping[str, Any]) -> Path:
    """Write the laboratory record ``0600`` inside the private root."""

    path = plan.root / LAB_RECORD_NAME
    _write_private(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
    return path


def _write_private(path: Path, text: str) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
            LAB_FILE_MODE,
        )
    except OSError as error:
        raise LabError(
            "lab-write",
            "a private laboratory file could not be written",
            detail={"error": type(error).__name__},
        ) from error
    try:
        os.fchmod(descriptor, LAB_FILE_MODE)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(text)
    except OSError as error:
        raise LabError(
            "lab-write",
            "a private laboratory file could not be written",
            detail={"error": type(error).__name__},
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
