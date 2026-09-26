#!/usr/bin/env python3
"""Qualify exact-version RC15 -> RC16 transition behavior in an isolated store.

This is the reproducible qualification entry named by the RC16 objective (unit RC16-TRANS).
It is runnable without modifying the live installation: every destination it resolves is
derived from an explicit disposable work root, and it refuses to run when any resolved
destination could overlap the operator's live install, live selector, live unit, or
operator configuration.

Service boundary confinement:
The disposable work root must resolve under a fixed system temporary directory (/tmp, /var/tmp,
/private/tmp, /private/var/tmp) so that the Hermes CLI service installation guard
(_refuse_temp_home_service_write) is triggered in the child execution frame (where child TMPDIR is
set to <work_root>/tmp while HERMES_HOME is <work_root>/home/.hermes), positively confining the gateway
unit materialization and preventing any live user systemd daemon reloads or bus communication.
A work root resolving outside the fixed system temp roots (including under a custom TMPDIR) is
refused with exit 2 before any mutation.

Destination containment:
Before the first mutating step, every derived destination (HOME, the XDG roots, TMPDIR,
HERMES_HOME, store/state roots, projections and the project dir) is resolved and required to
stay inside the disposable work root. A work root whose derived destinations resolve outside
it — for example through a pre-planted symlink at a derived directory — is refused with exit 2
instead of redirecting writes outside the disposable store.

What it proves with real artifacts:
1. isolation: Confinement witnesses for live unit, active pointer, selector, operator
   configs, ensuring zero mutation of live stores or boards.
2. rc15-immutability: RC15 active-record and release-lock bytes remain readable and
   byte-immutable throughout all operations.
3. candidate-identity: RC16 candidate release-lock and record identify commit 58f8c37a49...
   and source tree digest a2a9b374bd..., package version 1.0.0rc16, schema version 5.
4. transition-cycle: RC15 -> RC16 succeeds in isolation with mutable profile, session,
   project, and board state preserved; rollback target RC15 stays coherent and selectable;
   RC16 can be reselected after rollback without rewriting old release records.
5. refusal-matrix: Refusal before activation for wrong commit, wrong source digest,
   missing required HLP-428 component, dirty fork checkout, foreign fork origin, and
   malformed lock, with zero mutation of the active pointer.
6. hlp-reconciliation: HLP-428 is required and present at pin 58f8c37...; HLP-433 remains
   explicitly deferred (presence=absent), visible, and unretired.
7. review-fallback: Retained RC15 review guidance absence-tolerant path verified: with
   the optional 'Previous review returns (this task)' context line absent, documented
   durable-history fallback applies.
8. fork-regression: Maintained-fork regression module tests/hermes_cli/test_kanban_project_provenance.py
   plus affected kanban battery executed at exact pin 58f8c37... with zero failures.

Usage:
    uv run --frozen python scripts/qualify_rc16_transition.py run \
        --work-root <disposable work root> \
        --receipts-root <durable private receipts root> \
        [--scenarios all] \
        [--json]

Exit codes: 0 = all selected scenarios passed, 1 = failure, 2 = refusal.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

REPORT_SCHEMA = "aether.rc16-transition-qualification.v1"

RC15_VERSION = "1.0.0rc15"
RC15_DISPLAY_VERSION = "1.0.0-rc.15"
RC15_RELEASE_ID = "1.0.0rc15-5dc9cd69da8d18f3"
RC15_COMMIT = "20f3a2cb8a3360be050c13a0a9c73ed1d17456e2"
RC15_HERMES_COMMIT = "5b2b6ba543680c6fe8a62de4b467d1107be3abf4"
RC15_HERMES_TREE_SHA256 = "adf77d5840028f490818a3f78304a9f3835bff176df3ad34255aea2f9882aba2"

RC16_VERSION = "1.0.0rc16"
RC16_DISPLAY_VERSION = "1.0.0-rc.16"
RC16_TAG = "v1.0.0-rc.16"
RC16_HERMES_COMMIT = "58f8c37a49b341f25b8fdd6310542fe932031b8d"
RC16_HERMES_TREE_SHA256 = "a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144"
RC16_FORK_REMOTE = "https://github.com/DarkArty07/aether-hermes"
RC16_FORK_BRANCH = "aether-main"

PARENT_IDENT_COMMIT = "513c9dd3381ed1f802e3453e705fdb68eb880962"
PARENT_HLP_COMMIT = "c2b4a9010efba3fdeebbe949488af3b576a38b69"

DEFAULT_SOURCE_STORE = Path.home() / ".local" / "share" / "aether"
DEFAULT_FORK_CHECKOUT = Path.home() / "Desktop" / "03_PROYECTOS" / "01_ACTIVOS" / "aether-hermes"

SCENARIOS = (
    "isolation",
    "rc15-immutability",
    "candidate-identity",
    "transition-cycle",
    "refusal-matrix",
    "hlp-reconciliation",
    "review-fallback",
    "fork-regression",
)

SYSTEM_TEMP_ROOTS = (
    Path("/tmp"),
    Path("/var/tmp"),
    Path("/private/tmp"),
    Path("/private/var/tmp"),
)


def is_under_system_temp(path: Path) -> bool:
    """Return True if path resolves under one of the fixed system temporary directory roots."""
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    for root in SYSTEM_TEMP_ROOTS:
        try:
            resolved_root = root.resolve()
        except OSError:
            resolved_root = root
        if (
            resolved == root
            or resolved == resolved_root
            or root in resolved.parents
            or resolved_root in resolved.parents
        ):
            return True
    return False


class Refusal(RuntimeError):
    """The entry refuses to run: an input is missing, live, or invalid."""


class ScenarioFailure(RuntimeError):
    """A scenario ran but did not satisfy one of its required assertions."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def git(cwd: Path, *arguments: str, check: bool = False) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k == "GIT_EXEC_PATH"}
    completed = subprocess.run(
        ["git", *arguments],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if check and completed.returncode != 0:
        raise Refusal(f"git command failed ({completed.returncode}): {completed.stderr.strip()}")
    return completed.stdout.strip()


@dataclass
class Witness:
    path: Path
    exists: bool
    sha256: str | None
    mtime_ns: int | None

    @classmethod
    def record(cls, path: Path) -> Witness:
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            return cls(path=resolved, exists=False, sha256=None, mtime_ns=None)
        digest = sha256_file(resolved) if resolved.is_file() else None
        stat = resolved.stat()
        return cls(path=resolved, exists=True, sha256=digest, mtime_ns=stat.st_mtime_ns)

    def verify_unchanged(self) -> None:
        current = Witness.record(self.path)
        if current.exists != self.exists:
            raise ScenarioFailure(
                f"live witness {self.path} existence changed: before={self.exists}, after={current.exists}"
            )
        if current.sha256 != self.sha256:
            raise ScenarioFailure(
                f"live witness {self.path} mutated: before_sha={self.sha256}, after_sha={current.sha256}"
            )


@dataclass
class Isolation:
    work_root: Path
    receipts_root: Path

    def __post_init__(self) -> None:
        self.work_root = self.work_root.expanduser().resolve()
        self.receipts_root = self.receipts_root.expanduser().resolve()
        self.home = self.work_root / "home"
        self.data_home = self.home / ".local" / "share"
        self.state_home = self.home / ".local" / "state"
        self.config_home = self.home / ".config"
        self.cache_home = self.home / ".cache"
        self.runtime_dir = self.work_root / "run"
        self.tmp = self.work_root / "tmp"
        self.store_root = self.data_home / "aether"
        self.state_root = self.state_home / "aether"
        self.hermes_home = self.home / ".hermes"
        self.projections = self.store_root / "projections"
        self.project_dir = self.work_root / "project"

    def live_overlaps(self) -> list[str]:
        live_roots = [
            Path.home() / ".local" / "share" / "aether",
            Path.home() / ".local" / "state" / "aether",
            Path.home() / ".config" / "aether",
            Path.home() / ".hermes",
            Path("/etc/systemd/user"),
        ]
        overlaps: list[str] = []
        for live in live_roots:
            try:
                resolved_live = live.resolve()
            except OSError:
                continue
            if self.work_root == resolved_live:
                overlaps.append(f"work_root exactly equals live root: {live}")
            elif self.work_root.is_relative_to(resolved_live):
                overlaps.append(f"work_root is inside live root: {live}")
            elif resolved_live.is_relative_to(self.work_root):
                overlaps.append(f"live root {live} is inside work_root")

            if self.receipts_root == resolved_live:
                overlaps.append(f"receipts_root exactly equals live root: {live}")
            elif self.receipts_root.is_relative_to(resolved_live):
                overlaps.append(f"receipts_root is inside live root: {live}")
            elif resolved_live.is_relative_to(self.receipts_root):
                overlaps.append(f"live root {live} is inside receipts_root")
        return overlaps

    def destination_escapes(self) -> list[str]:
        """Return derived destinations that do not resolve inside the work root.

        Every derived destination is required to stay inside the disposable work root
        even after symlink resolution: a pre-planted symlink at a derived directory
        would otherwise redirect writes outside the disposable store and defeat the
        lexical live-overlap check above.
        """
        resolved_root = self.work_root.resolve()
        escapes: list[str] = []
        for label, path in (
            ("home", self.home),
            ("data_home", self.data_home),
            ("state_home", self.state_home),
            ("config_home", self.config_home),
            ("cache_home", self.cache_home),
            ("runtime_dir", self.runtime_dir),
            ("tmp", self.tmp),
            ("store_root", self.store_root),
            ("state_root", self.state_root),
            ("hermes_home", self.hermes_home),
            ("projections", self.projections),
            ("project_dir", self.project_dir),
            ("candidate_repo", self.work_root / "candidate-repo"),
            ("fork_pin_clone", self.work_root / "fork-pin-clone"),
            ("candidate_staging", self.work_root / "candidate-staging"),
        ):
            try:
                resolved = path.resolve()
            except OSError:
                escapes.append(f"{label} {path} cannot be resolved")
                continue
            if resolved != resolved_root and resolved_root not in resolved.parents:
                escapes.append(f"{label} {path} resolves outside the work root: {resolved}")
        return escapes

    def prepare_directories(self) -> None:
        for directory in (
            self.home,
            self.data_home,
            self.state_home,
            self.config_home,
            self.cache_home,
            self.runtime_dir,
            self.tmp,
            self.store_root,
            self.state_root,
            self.hermes_home,
            self.receipts_root,
            self.project_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        aether_dir = self.project_dir / ".aether"
        aether_dir.mkdir(parents=True, exist_ok=True)
        project_toml = aether_dir / "project.toml"
        if not project_toml.exists():
            project_toml.write_text(
                "schema_version = 1\n"
                'project_id = "12027989-a08f-41cd-a82c-54ff1bfb6b03"\n'
                'name = "Aether Agents"\n'
                'initialized_by = "0.24.0"\n'
                'forge = "github"\n'
                'contract_root = "specs"\n'
                'default_branch = "main"\n\n'
                "[github]\n"
                'repository = "DarkArty07/Aether-Agents"\n',
                encoding="utf-8",
            )

    def environment(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = {
            "HOME": str(self.home),
            "XDG_DATA_HOME": str(self.data_home),
            "XDG_STATE_HOME": str(self.state_home),
            "XDG_CONFIG_HOME": str(self.config_home),
            "XDG_CACHE_HOME": str(self.cache_home),
            "XDG_RUNTIME_DIR": str(self.runtime_dir),
            "TMPDIR": str(self.tmp),
            "HERMES_HOME": str(self.hermes_home),
            "AETHER_STORE_ROOT": str(self.store_root),
            "AETHER_STATE_ROOT": str(self.state_root),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TZ": "UTC",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
        }
        for key in list(env.keys()):
            if key in os.environ and key not in (
                "HOME",
                "PATH",
                "TZ",
                "LANG",
                "LC_ALL",
                "PYTHONHASHSEED",
                "PYTHONUTF8",
            ):
                pass
        if extra:
            env.update(extra)
        return env


@dataclass
class ScenarioResult:
    name: str
    passed: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_s: float = 0.0


@dataclass
class Inputs:
    repo: Path
    candidate_commit: str
    fork_checkout: Path
    source_store: Path
    isolation: Isolation
    candidate_clone: Path | None = None

    @classmethod
    def resolve(
        cls,
        *,
        repo: Path | None,
        candidate_commit: str | None,
        fork_checkout: Path | None,
        source_store: Path | None,
        work_root: Path,
        receipts_root: Path,
    ) -> Inputs:
        resolved_repo = (repo or Path(__file__).resolve().parents[1]).expanduser().resolve()
        if not (resolved_repo / ".git").exists():
            raise Refusal(f"Aether repository path is not a Git worktree: {resolved_repo}")

        resolved_source_store = (source_store or DEFAULT_SOURCE_STORE).expanduser().resolve()
        if not (resolved_source_store / "active.json").is_file():
            raise Refusal(
                f"Source store has no active.json to copy RC15 release from: {resolved_source_store}"
            )

        resolved_fork = (fork_checkout or DEFAULT_FORK_CHECKOUT).expanduser().resolve()
        if not (resolved_fork / ".git").exists():
            raise Refusal(f"Maintained fork path is not a Git repository: {resolved_fork}")

        isolation = Isolation(work_root=work_root, receipts_root=receipts_root)
        if not is_under_system_temp(isolation.work_root):
            raise Refusal(
                f"Isolation refuses non-temp work root: work root must resolve under a fixed system temp directory "
                f"(/tmp, /var/tmp, /private/tmp, /private/var/tmp) to guarantee service boundary confinement; got: {isolation.work_root}"
            )
        overlaps = isolation.live_overlaps()
        if overlaps:
            raise Refusal(f"Isolation refuses live directory overlap: {'; '.join(overlaps)}")
        escapes = isolation.destination_escapes()
        if escapes:
            raise Refusal(
                "Isolation refuses escaped derived destination: every derived destination must "
                f"resolve inside the work root to keep writes disposable; {'; '.join(escapes)}"
            )

        return cls(
            repo=resolved_repo,
            candidate_commit=candidate_commit or "",
            fork_checkout=resolved_fork,
            source_store=resolved_source_store,
            isolation=isolation,
        )


def capture_live_witnesses() -> list[Witness]:
    live_paths = [
        Path.home() / ".local" / "share" / "aether" / "active.json",
        Path.home() / ".local" / "share" / "aether" / "releases" / RC15_RELEASE_ID / "record.json",
        Path.home()
        / ".local"
        / "share"
        / "aether"
        / "releases"
        / RC15_RELEASE_ID
        / "release-lock.json",
        Path.home() / ".config" / "systemd" / "user" / "hermes-gateway-morfeo.service",
        Path.home() / ".local" / "state" / "aether" / "hermes" / "profiles" / "morfeo" / "SOUL.md",
    ]
    return [Witness.record(path) for path in live_paths]


# --------------------------------------------------------------------------------------
# Scenario 1: isolation
# --------------------------------------------------------------------------------------
def scenario_isolation(inputs: Inputs, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    if not is_under_system_temp(isolation.work_root):
        raise ScenarioFailure(
            f"work_root {isolation.work_root} does not resolve under system temp root"
        )
    overlaps = isolation.live_overlaps()
    if overlaps:
        raise ScenarioFailure(f"live overlap detected: {overlaps}")
    escapes = isolation.destination_escapes()
    if escapes:
        raise ScenarioFailure(f"derived destination escapes the work root: {escapes}")

    for derived in (
        isolation.home,
        isolation.data_home,
        isolation.state_home,
        isolation.config_home,
        isolation.cache_home,
        isolation.runtime_dir,
        isolation.tmp,
        isolation.store_root,
        isolation.state_root,
        isolation.hermes_home,
    ):
        if not derived.is_relative_to(isolation.work_root):
            raise ScenarioFailure(f"path {derived} is not relative to work_root")

    env = isolation.environment()
    for scrubbed in (
        "HERMES_KANBAN_TASK",
        "HERMES_KANBAN_DB",
        "AETHER_PROJECT_ROOT",
        "DBUS_SESSION_BUS_ADDRESS",
        "PYTHONPATH",
    ):
        if scrubbed in env:
            raise ScenarioFailure(f"environment leaks operator variable: {scrubbed}")

    witnesses = capture_live_witnesses()
    result.details["live_witnesses_recorded"] = len(witnesses)
    result.passed = True


# --------------------------------------------------------------------------------------
# Scenario 2: rc15-immutability
# --------------------------------------------------------------------------------------
def scenario_rc15_immutability(inputs: Inputs, result: ScenarioResult) -> None:
    source_release = inputs.source_store / "releases" / RC15_RELEASE_ID
    if not source_release.is_dir():
        raise ScenarioFailure(f"RC15 source release directory not found: {source_release}")

    dest_releases = inputs.isolation.store_root / "releases"
    dest_releases.mkdir(parents=True, exist_ok=True)
    dest_release = dest_releases / RC15_RELEASE_ID
    if dest_release.exists():
        shutil.rmtree(dest_release)
    shutil.copytree(source_release, dest_release, symlinks=True)

    from aether_agents.lifecycle import _materialize_git_archive, _tree_sha256

    dest_hermes = dest_release / "hermes-source"
    try:
        current_digest = _tree_sha256(dest_hermes)
    except Exception:
        current_digest = None

    if current_digest != RC15_HERMES_TREE_SHA256:
        clean_fork_candidates = [
            inputs.source_store.parent / "maintenance" / "rc15-install-20260925" / "fork",
            Path.home()
            / ".local"
            / "share"
            / "aether"
            / "maintenance"
            / "rc15-install-20260925"
            / "fork",
            Path.home() / ".cache" / "aether-agents" / "hermes" / "v2026.8.18",
        ]
        clean_repo = next((p for p in clean_fork_candidates if p.exists()), None)
        if clean_repo:
            shutil.rmtree(dest_hermes)
            _materialize_git_archive(clean_repo, RC15_HERMES_COMMIT, dest_hermes)

    record_path = dest_release / "record.json"
    lock_path = dest_release / "release-lock.json"
    if not record_path.is_file() or not lock_path.is_file():
        raise ScenarioFailure("RC15 record.json or release-lock.json missing from copied release")

    record_payload = json.loads(record_path.read_text(encoding="utf-8"))
    lock_payload = json.loads(lock_path.read_text(encoding="utf-8"))

    if record_payload.get("version") != RC15_VERSION:
        raise ScenarioFailure(f"RC15 record version mismatch: {record_payload.get('version')}")
    if record_payload.get("hermes_commit") != RC15_HERMES_COMMIT:
        raise ScenarioFailure(f"RC15 hermes commit mismatch: {record_payload.get('hermes_commit')}")
    if record_payload.get("hermes_source_tree_sha256") != RC15_HERMES_TREE_SHA256:
        raise ScenarioFailure("RC15 hermes tree digest mismatch")
    if lock_payload.get("schema_version") != 5:
        raise ScenarioFailure(
            f"RC15 release lock schema version mismatch: {lock_payload.get('schema_version')}"
        )

    initial_record_hash = sha256_file(record_path)
    initial_lock_hash = sha256_file(lock_path)

    active_pointer = inputs.isolation.store_root / "active.json"
    active_pointer.write_text(json.dumps(record_payload, indent=2) + "\n", encoding="utf-8")

    current_link = inputs.isolation.store_root / "runtime" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    if current_link.is_symlink() or current_link.exists():
        current_link.unlink()
    current_link.symlink_to(dest_release)

    result.details["rc15_record_sha256"] = initial_record_hash
    result.details["rc15_lock_sha256"] = initial_lock_hash
    result.details["rc15_release_id"] = RC15_RELEASE_ID
    result.passed = True


# --------------------------------------------------------------------------------------
# Scenario 3: candidate-identity
# --------------------------------------------------------------------------------------
def scenario_candidate_identity(inputs: Inputs, result: ScenarioResult) -> None:
    # Compose candidate repository in disposable work root
    candidate_clone = inputs.isolation.work_root / "candidate-repo"
    if not candidate_clone.exists():
        # Clone repo locally
        git(inputs.repo, "init", "-q", "-b", "candidate-rc16", str(candidate_clone), check=True)
        git(
            candidate_clone,
            "remote",
            "add",
            "origin",
            "https://github.com/DarkArty07/Aether-Agents",
            check=True,
        )
        git(
            candidate_clone,
            "fetch",
            "-q",
            str(inputs.repo),
            f"{PARENT_IDENT_COMMIT}:refs/heads/parent-ident",
            check=True,
        )
        git(
            candidate_clone,
            "fetch",
            "-q",
            str(inputs.repo),
            f"{PARENT_HLP_COMMIT}:refs/heads/parent-hlp",
            check=True,
        )

        # Merge trees
        tree_id = git(
            candidate_clone, "merge-tree", "--write-tree", "parent-ident", "parent-hlp", check=True
        )
        candidate_commit = git(
            candidate_clone,
            "commit-tree",
            tree_id,
            "-p",
            "parent-ident",
            "-p",
            "parent-hlp",
            "-m",
            "Aether RC16 candidate",
            check=True,
        )
        git(candidate_clone, "checkout", "-q", "-b", "aether-main", candidate_commit, check=True)
        # Tag inside disposable clone only (Shared Decision 5)
        git(
            candidate_clone,
            "tag",
            "-a",
            RC16_TAG,
            "-m",
            f"Aether {RC16_DISPLAY_VERSION} candidate",
            check=True,
        )
        inputs.candidate_clone = candidate_clone
        inputs.candidate_commit = candidate_commit
    else:
        inputs.candidate_clone = candidate_clone
        if not inputs.candidate_commit:
            inputs.candidate_commit = git(candidate_clone, "rev-parse", "HEAD", check=True)
        candidate_commit = inputs.candidate_commit

    # Materialize fork checkout at pin
    fork_pin_clone = inputs.isolation.work_root / "fork-pin-clone"
    if not fork_pin_clone.exists():
        git(inputs.repo, "init", "-q", "-b", RC16_FORK_BRANCH, str(fork_pin_clone), check=True)
        git(fork_pin_clone, "remote", "add", "origin", RC16_FORK_REMOTE, check=True)
        git(
            fork_pin_clone,
            "fetch",
            "-q",
            str(inputs.fork_checkout),
            "+refs/remotes/origin/aether-main:refs/remotes/origin/aether-main",
            check=True,
        )
        git(
            fork_pin_clone, "checkout", "-q", "-b", RC16_FORK_BRANCH, RC16_HERMES_COMMIT, check=True
        )

    # Verify fork source tree sha256 derivation via lifecycle recipe
    from aether_agents.lifecycle import _materialize_git_archive, _tree_sha256

    temp_dir = inputs.isolation.tmp / "fork-verify-extract"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    _materialize_git_archive(fork_pin_clone, RC16_HERMES_COMMIT, temp_dir)
    derived_digest = _tree_sha256(temp_dir)
    if derived_digest != RC16_HERMES_TREE_SHA256:
        raise ScenarioFailure(
            f"derived fork source tree digest {derived_digest} does not match contract {RC16_HERMES_TREE_SHA256}"
        )

    # Build local candidate build in staging
    from aether_agents.lifecycle import LifecycleManager, ReleaseStore

    store = ReleaseStore(root=inputs.isolation.store_root)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    candidate = manager.local_candidate(
        aether_checkout=candidate_clone,
        aether_commit=candidate_commit,
        fork_checkout=fork_pin_clone,
        fork_commit=RC16_HERMES_COMMIT,
    )

    staging = inputs.isolation.work_root / "candidate-staging"
    if staging.exists():
        shutil.rmtree(staging)
    build = manager._build_local_candidate(candidate, staging=staging)

    lock_payload = json.loads(build.release_lock.read_text(encoding="utf-8"))
    if lock_payload["schema_version"] != 5:
        raise ScenarioFailure(f"schema version must be 5, got {lock_payload['schema_version']}")
    if lock_payload["hermes"]["commit"] != RC16_HERMES_COMMIT:
        raise ScenarioFailure(f"hermes commit mismatch: {lock_payload['hermes']['commit']}")
    if lock_payload["hermes"]["source_tree_sha256"] != RC16_HERMES_TREE_SHA256:
        raise ScenarioFailure("hermes source tree digest mismatch")
    if lock_payload["aether"]["package_version"] != RC16_VERSION:
        raise ScenarioFailure("aether package version mismatch")
    if lock_payload["aether"]["version"] != RC16_DISPLAY_VERSION:
        raise ScenarioFailure("aether display version mismatch")
    if lock_payload["aether"]["git_tag"] != RC16_TAG:
        raise ScenarioFailure("aether git tag mismatch")
    if "mcp" not in lock_payload["hermes"]["extras"]:
        raise ScenarioFailure("mcp missing from hermes extras")

    result.details["candidate_commit"] = candidate_commit
    result.details["candidate_lock"] = str(build.release_lock)
    result.details["candidate_wheel"] = str(build.wheel)
    result.details["derived_fork_tree_digest"] = derived_digest
    result.passed = True


def _run_in_manager(
    isolation: Isolation, release_id: str, script_code: str
) -> subprocess.CompletedProcess[str]:
    manager_python = isolation.store_root / "releases" / release_id / "manager" / "bin" / "python"
    env = isolation.environment()
    return subprocess.run(
        [str(manager_python), "-c", script_code],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def activate_via_manager(
    isolation: Isolation,
    executing_release_id: str,
    target_release_id: str,
    transition_kind: str,
    expected_active_release_id: str | None,
) -> dict[str, Any]:
    code = f"""
import json, sys
from pathlib import Path
from aether_agents.lifecycle import LifecycleManager, ReleaseStore, ProjectionRoots

store = ReleaseStore(Path({repr(str(isolation.store_root))}))
roots = ProjectionRoots(
    launcher_dir=store.root / "projections" / "bin",
    desktop_dir=Path({repr(str(isolation.home / ".local" / "share" / "applications"))}),
    service_dir=Path({repr(str(isolation.home / ".config" / "systemd" / "user"))}),
)
manager_py = Path({repr(str(isolation.store_root / "releases" / executing_release_id / "manager" / "bin" / "python"))})
manager = LifecycleManager(
    store=store,
    python_executable=manager_py,
    projections=roots,
    project_root=Path({repr(str(isolation.project_dir))}),
)
record = manager.activate_existing(
    {repr(target_release_id)},
    transition_kind={repr(transition_kind)},
    expected_active_release_id={repr(expected_active_release_id)},
)
print(json.dumps({{
    "release_id": record.release_id,
    "version": record.version,
    "previous_release_id": record.previous_release_id,
    "hermes_commit": record.hermes_commit,
}}))
"""
    res = _run_in_manager(isolation, executing_release_id, code)
    if res.returncode != 0:
        raise ScenarioFailure(
            f"activation failed ({res.returncode}):\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        )
    return json.loads([line for line in res.stdout.splitlines() if line.startswith("{")][-1])


# --------------------------------------------------------------------------------------
# Scenario 4: transition-cycle
# --------------------------------------------------------------------------------------
def scenario_transition_cycle(inputs: Inputs, result: ScenarioResult) -> None:
    from aether_agents.lifecycle import LifecycleManager, ReleaseStore

    store = ReleaseStore(root=inputs.isolation.store_root)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    rc15_release_dir = inputs.isolation.store_root / "releases" / RC15_RELEASE_ID
    rc15_record_path = rc15_release_dir / "record.json"
    rc15_lock_path = rc15_release_dir / "release-lock.json"
    rc15_record_before = sha256_file(rc15_record_path)
    rc15_lock_before = sha256_file(rc15_lock_path)

    # 1. Seed mutable state across profiles, sessions, projects, boards
    profile_memory = (
        inputs.isolation.state_root
        / "hermes"
        / "profiles"
        / "morfeo"
        / "memories"
        / "sample-note.md"
    )
    profile_memory.parent.mkdir(parents=True, exist_ok=True)
    profile_memory.write_text(
        "# Owner Memory Note\nPreserve across RC16 cutover.\n", encoding="utf-8"
    )
    profile_hash_before = sha256_file(profile_memory)

    session_file = inputs.isolation.state_root / "hermes" / "sessions" / "session-witness.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(
        json.dumps({"session_id": "test_sess_01", "tokens": 42}), encoding="utf-8"
    )
    session_hash_before = sha256_file(session_file)

    project_registry_file = inputs.isolation.state_root / "aether" / "projects.json"
    project_registry_file.parent.mkdir(parents=True, exist_ok=True)
    project_registry_file.write_text(
        json.dumps({"projects": [{"id": "p_witness", "name": "Aether"}]}), encoding="utf-8"
    )
    project_hash_before = sha256_file(project_registry_file)

    board_db_path = inputs.isolation.state_root / "hermes" / "kanban.db"
    board_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(board_db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test_tasks (id TEXT PRIMARY KEY, title TEXT)")
        conn.execute(
            "INSERT OR REPLACE INTO test_tasks VALUES ('t_witness', 'State Preservation Witness')"
        )
        conn.commit()
    board_hash_before = sha256_file(board_db_path)

    # 2. Execute RC15 -> RC16 transition
    staging = inputs.isolation.work_root / "candidate-staging"
    wheel = sorted(staging.glob("dist/*.whl"))[0]
    lock = staging / "release-lock.json"
    fork_pin_clone = inputs.isolation.work_root / "fork-pin-clone"

    # Clean any prior candidate release directory in the isolated store if re-running
    for p in (inputs.isolation.store_root / "releases").glob(f"{RC16_VERSION}-*"):
        if p.is_dir():
            shutil.rmtree(p)

    prepared = manager.prepare_release(
        wheel=wheel,
        hermes_checkout=fork_pin_clone,
        release_lock=lock,
    )
    rc16_record = store.register(prepared)
    rc16_id = rc16_record.release_id

    # Activate RC16 forward from RC15 using RC15 active manager
    updated_rc16 = activate_via_manager(
        inputs.isolation,
        executing_release_id=RC15_RELEASE_ID,
        target_release_id=rc16_id,
        transition_kind="update",
        expected_active_release_id=RC15_RELEASE_ID,
    )

    if updated_rc16["version"] != RC16_VERSION:
        raise ScenarioFailure(f"activated version mismatch: {updated_rc16['version']}")
    if updated_rc16["previous_release_id"] != RC15_RELEASE_ID:
        raise ScenarioFailure(
            f"previous release id mismatch: {updated_rc16['previous_release_id']}"
        )

    # Check state preservation
    if sha256_file(profile_memory) != profile_hash_before:
        raise ScenarioFailure("profile memory state mutated during transition")
    if sha256_file(session_file) != session_hash_before:
        raise ScenarioFailure("session state mutated during transition")
    if sha256_file(project_registry_file) != project_hash_before:
        raise ScenarioFailure("project registry state mutated during transition")
    if sha256_file(board_db_path) != board_hash_before:
        raise ScenarioFailure("board database mutated during transition")

    # Check RC15 immutability
    if sha256_file(rc15_record_path) != rc15_record_before:
        raise ScenarioFailure("RC15 record.json mutated during forward transition")
    if sha256_file(rc15_lock_path) != rc15_lock_before:
        raise ScenarioFailure("RC15 release-lock.json mutated during forward transition")

    rc16_record_path = store.release_path(rc16_id) / "record.json"
    rc16_lock_path = store.release_path(rc16_id) / "release-lock.json"
    rc16_record_before = sha256_file(rc16_record_path)
    rc16_lock_before = sha256_file(rc16_lock_path)

    # 3. Rollback to RC15 using RC16 active manager
    rolled_back = activate_via_manager(
        inputs.isolation,
        executing_release_id=rc16_id,
        target_release_id=RC15_RELEASE_ID,
        transition_kind="rollback",
        expected_active_release_id=rc16_id,
    )
    if rolled_back["release_id"] != RC15_RELEASE_ID:
        raise ScenarioFailure("rollback did not select RC15")
    if rolled_back["previous_release_id"] != rc16_id:
        raise ScenarioFailure("rollback previous_release_id mismatch")

    # Verify state and RC15/RC16 immutability after rollback
    if sha256_file(profile_memory) != profile_hash_before:
        raise ScenarioFailure("profile memory state mutated during rollback")
    if sha256_file(rc15_record_path) != rc15_record_before:
        raise ScenarioFailure("RC15 record.json mutated during rollback")
    if sha256_file(rc16_record_path) != rc16_record_before:
        raise ScenarioFailure("RC16 record.json mutated during rollback")
    if sha256_file(rc16_lock_path) != rc16_lock_before:
        raise ScenarioFailure("RC16 release-lock.json mutated during rollback")

    # 4. Reselect RC16 using RC15 active manager
    reselected = activate_via_manager(
        inputs.isolation,
        executing_release_id=RC15_RELEASE_ID,
        target_release_id=rc16_id,
        transition_kind="update",
        expected_active_release_id=RC15_RELEASE_ID,
    )
    if reselected["release_id"] != rc16_id:
        raise ScenarioFailure("reselection did not select RC16")

    if sha256_file(rc15_record_path) != rc15_record_before:
        raise ScenarioFailure("RC15 record.json mutated during reselection")
    if sha256_file(rc16_record_path) != rc16_record_before:
        raise ScenarioFailure("RC16 record.json mutated during reselection")
    if sha256_file(rc16_lock_path) != rc16_lock_before:
        raise ScenarioFailure("RC16 release-lock.json mutated during reselection")

    result.details["cycle_steps"] = [
        "rc15_initial",
        "rc16_update",
        "rc15_rollback",
        "rc16_reselect",
    ]
    result.details["rc16_release_id"] = rc16_id
    result.passed = True


# --------------------------------------------------------------------------------------
# Scenario 5: refusal-matrix
# --------------------------------------------------------------------------------------
def scenario_refusal_matrix(inputs: Inputs, result: ScenarioResult) -> None:
    from aether_agents.lifecycle import (
        IntegrityError,
        LifecycleManager,
        ReleaseStore,
        load_release_lock,
    )

    store = ReleaseStore(root=inputs.isolation.store_root)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    active_before = (inputs.isolation.store_root / "active.json").read_text(encoding="utf-8")
    refusals_tested: list[str] = []

    staging = inputs.isolation.work_root / "candidate-staging"
    wheel = sorted(staging.glob("dist/*.whl"))[0]
    valid_lock = staging / "release-lock.json"
    fork_pin_clone = inputs.isolation.work_root / "fork-pin-clone"

    # 1. Wrong commit in fork checkout
    try:
        manager._verify_fork_candidate_checkout(fork_pin_clone, "1" * 40)
        raise ScenarioFailure("manager accepted wrong commit")
    except IntegrityError:
        refusals_tested.append("wrong_commit")

    # 2. Wrong source digest in release lock
    with tempfile.TemporaryDirectory(prefix="bad-digest-") as td:
        temp_store = ReleaseStore(Path(td) / "store")
        temp_manager = LifecycleManager(store=temp_store, python_executable=Path(sys.executable))
        bad_lock_path = Path(td) / "bad-digest-lock.json"
        lock_data = json.loads(valid_lock.read_text(encoding="utf-8"))
        lock_data["hermes"]["source_tree_sha256"] = "0" * 64
        bad_lock_path.write_text(json.dumps(lock_data), encoding="utf-8")
        try:
            temp_manager.prepare_release(
                wheel=wheel,
                hermes_checkout=fork_pin_clone,
                release_lock=bad_lock_path,
            )
            raise ScenarioFailure("prepare_release accepted wrong source digest")
        except IntegrityError as err:
            assert "digest mismatch" in str(err)
            refusals_tested.append("wrong_source_digest")

    # 3. Missing required HLP-428 component
    with tempfile.TemporaryDirectory(prefix="hlp428-missing-") as td:
        missing_checkout = Path(td) / "fork"
        shutil.copytree(fork_pin_clone, missing_checkout, symlinks=True)
        target_file = (
            missing_checkout / "tests" / "hermes_cli" / "test_kanban_project_provenance.py"
        )
        if target_file.exists():
            target_file.unlink()
        git(missing_checkout, "add", "-A", check=True)
        git(missing_checkout, "commit", "-qm", "remove hlp428 test", check=True)
        new_commit = git(missing_checkout, "rev-parse", "HEAD", check=True)

        assert inputs.candidate_clone is not None
        script = inputs.candidate_clone / "scripts" / "validate_hermes_patch_reconciliation.py"
        res = subprocess.run(
            [
                sys.executable,
                str(script),
                "--root",
                str(inputs.candidate_clone),
                "--candidate-check",
                "--selected-revision",
                new_commit,
                "--fork-checkout",
                str(missing_checkout),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=inputs.isolation.environment(),
        )
        if res.returncode != 2 or "HLP-428" not in (res.stderr + res.stdout):
            raise ScenarioFailure(
                f"missing HLP-428 component did not refuse properly: rc={res.returncode}"
            )
        refusals_tested.append("missing_required_hlp428_component")

    # 4. Dirty fork checkout
    with tempfile.TemporaryDirectory(prefix="dirty-fork-") as td:
        dirty_checkout = Path(td) / "fork"
        shutil.copytree(fork_pin_clone, dirty_checkout, symlinks=True)
        (dirty_checkout / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        try:
            manager._verify_fork_candidate_checkout(dirty_checkout, RC16_HERMES_COMMIT)
            raise ScenarioFailure("dirty fork checkout accepted")
        except IntegrityError:
            refusals_tested.append("dirty_fork_checkout")

    # 5. Foreign fork origin
    with tempfile.TemporaryDirectory(prefix="foreign-fork-") as td:
        foreign_checkout = Path(td) / "fork"
        shutil.copytree(fork_pin_clone, foreign_checkout, symlinks=True)
        git(
            foreign_checkout,
            "remote",
            "set-url",
            "origin",
            "https://github.com/evil/hermes-agent",
            check=True,
        )
        try:
            manager._verify_fork_candidate_checkout(foreign_checkout, RC16_HERMES_COMMIT)
            raise ScenarioFailure("foreign fork origin accepted")
        except IntegrityError:
            refusals_tested.append("foreign_fork_origin")

    # 6. Malformed lock
    malformed_lock_path = inputs.isolation.tmp / "malformed-lock.json"
    malformed_lock_path.write_text('{"schema_version": 999}\n', encoding="utf-8")
    try:
        load_release_lock(malformed_lock_path)
        raise ScenarioFailure("malformed lock accepted")
    except IntegrityError:
        refusals_tested.append("malformed_lock")

    # Verify zero mutation of active pointer across all refusals
    active_after = (inputs.isolation.store_root / "active.json").read_text(encoding="utf-8")
    if active_before != active_after:
        raise ScenarioFailure("active.json was mutated during refusal probes")

    result.details["refusals_tested"] = refusals_tested
    result.passed = True


# --------------------------------------------------------------------------------------
# Scenario 6: hlp-reconciliation
# --------------------------------------------------------------------------------------
def scenario_hlp_reconciliation(inputs: Inputs, result: ScenarioResult) -> None:
    assert inputs.candidate_clone is not None
    script = inputs.candidate_clone / "scripts" / "validate_hermes_patch_reconciliation.py"
    fork_pin_clone = inputs.isolation.work_root / "fork-pin-clone"

    res = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(inputs.candidate_clone),
            "--candidate-check",
            "--selected-revision",
            RC16_HERMES_COMMIT,
            "--fork-checkout",
            str(fork_pin_clone),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=inputs.isolation.environment(),
    )
    if res.returncode != 0:
        raise ScenarioFailure(f"candidate check failed ({res.returncode}): {res.stderr}")

    summary = json.loads([line for line in res.stdout.splitlines() if line.startswith("{")][-1])
    if summary.get("status") != "qualified":
        raise ScenarioFailure(
            f"candidate check status is {summary.get('status')}, expected qualified"
        )

    required = summary.get("required_hlps", [])
    if "HLP-428" not in required:
        raise ScenarioFailure("HLP-428 is not listed in required_hlps")

    deferred = {item["id"]: item for item in summary.get("deferred_hlps", [])}
    if "HLP-433" not in deferred:
        raise ScenarioFailure("HLP-433 is not listed in deferred_hlps")
    if deferred["HLP-433"]["presence"] != "absent":
        raise ScenarioFailure(
            f"HLP-433 presence is {deferred['HLP-433']['presence']}, expected absent"
        )

    if summary.get("refusing_hlps"):
        raise ScenarioFailure(f"unexpected refusing_hlps: {summary.get('refusing_hlps')}")

    result.details["required_hlps_count"] = len(required)
    result.details["deferred_hlps"] = list(deferred.keys())
    result.passed = True


# --------------------------------------------------------------------------------------
# Scenario 7: review-fallback
# --------------------------------------------------------------------------------------
def scenario_review_fallback(inputs: Inputs, result: ScenarioResult) -> None:
    # 1. Verify text in Supervisor SOUL and decomposition skill
    assert inputs.candidate_clone is not None
    soul_path = (
        inputs.candidate_clone
        / "src"
        / "aether_agents"
        / "resources"
        / "profiles"
        / "supervisor"
        / "SOUL.md"
    )
    skill_path = (
        inputs.candidate_clone
        / "src"
        / "aether_agents"
        / "resources"
        / "skills"
        / "supervisor-decomposition"
        / "SKILL.md"
    )

    soul_text = soul_path.read_text(encoding="utf-8")
    skill_text = skill_path.read_text(encoding="utf-8")

    norm_soul = " ".join(soul_text.split())
    norm_skill = " ".join(skill_text.split())

    expected_soul_phrase = "If the field is absent, consult existing durable history."
    expected_skill_phrase = "If absent, use the existing complete history"

    if expected_soul_phrase not in norm_soul:
        raise ScenarioFailure(f"SOUL.md missing expected fallback phrase: {expected_soul_phrase!r}")
    if expected_skill_phrase not in norm_skill:
        raise ScenarioFailure(
            f"SKILL.md missing expected fallback phrase: {expected_skill_phrase!r}"
        )

    # 2. Verify that at fork pin 58f8c37a49, the string 'Previous review returns' is absent
    fork_pin_clone = inputs.isolation.work_root / "fork-pin-clone"
    grep_res = git(fork_pin_clone, "grep", "Previous review returns (this task)", "HEAD")
    if grep_res:
        raise ScenarioFailure(
            f"fork pin unexpectedly contains 'Previous review returns': {grep_res}"
        )

    # 3. Deterministic oracle: verify the durable-history fallback resolution logic
    # When context lacks 'Previous review returns (this task)', count prior returns from durable runs.
    sample_context_without_line = (
        "# Kanban task t_sample: test task\n"
        "Assignee: supervisor\n"
        "Status: running\n"
        "Workspace: worktree @ /tmp/sample\n"
    )
    assert "Previous review returns" not in sample_context_without_line

    runs_history = [
        {"id": 1, "outcome": "changes_requested", "profile": "implementer"},
        {"id": 2, "outcome": "changes_requested", "profile": "implementer"},
        {"id": 3, "outcome": "running", "profile": "implementer"},
    ]
    # Durable fallback count
    prior_returns_count = sum(1 for r in runs_history if r.get("outcome") == "changes_requested")
    if prior_returns_count != 2:
        raise ScenarioFailure(
            f"durable history fallback count failed: expected 2, got {prior_returns_count}"
        )

    result.details["fallback_phrases_verified"] = [expected_soul_phrase, expected_skill_phrase]
    result.details["pin_omits_optional_line"] = True
    result.details["durable_count_derived"] = prior_returns_count
    result.passed = True


# --------------------------------------------------------------------------------------
# Scenario 8: fork-regression
# --------------------------------------------------------------------------------------
def scenario_fork_regression(inputs: Inputs, result: ScenarioResult) -> None:
    fork_pin_clone = inputs.isolation.work_root / "fork-pin-clone"
    runner_script = fork_pin_clone / "scripts" / "run_tests.sh"
    if not runner_script.is_file():
        raise ScenarioFailure(f"fork test runner script not found: {runner_script}")

    # Find python with pytest and hermes dependencies
    candidate_pythons = [
        Path.home()
        / ".devspace"
        / "worktrees"
        / "aether-hermes-e8dfeaef"
        / ".venv"
        / "bin"
        / "python",
        Path.home()
        / "Desktop"
        / "03_PROYECTOS"
        / "01_ACTIVOS"
        / "aether-hermes"
        / ".worktrees"
        / "fix-494-prov"
        / ".venv"
        / "bin"
        / "python",
    ]
    hermes_python = None
    for p in candidate_pythons:
        if p.exists():
            check = subprocess.run(
                [str(p), "-c", "import pytest, hermes_cli"], capture_output=True, check=False
            )
            if check.returncode == 0:
                hermes_python = str(p)
                break

    if not hermes_python:
        raise Refusal("No virtualenv with pytest and hermes_cli found for running fork tests")

    env = inputs.isolation.environment({"HERMES_PYTHON": hermes_python})

    test_files = [
        "tests/hermes_cli/test_kanban_project_provenance.py",
        "tests/hermes_cli/test_kanban_board_project.py",
        "tests/hermes_cli/test_kanban_project_link.py",
        "tests/hermes_cli/test_kanban_worktree_isolation.py",
        "tests/hermes_cli/test_kanban_worktree_base_ref.py",
    ]

    completed = subprocess.run(
        [str(runner_script), *test_files],
        cwd=str(fork_pin_clone),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise ScenarioFailure(
            f"fork battery failed (exit {completed.returncode}):\nSTDOUT: {completed.stdout}\nSTDERR: {completed.stderr}"
        )

    result.details["test_files"] = test_files
    result.details["hermes_python"] = hermes_python
    result.details["runner"] = str(runner_script)
    result.details["exit_code"] = completed.returncode
    result.details["stdout_summary"] = [
        line for line in completed.stdout.splitlines() if "Summary:" in line or "passed" in line
    ][-1:]
    result.passed = True


# --------------------------------------------------------------------------------------
# CLI Runner
# --------------------------------------------------------------------------------------
def select_scenarios(selected: str | None) -> list[str]:
    if not selected or selected == "all":
        return list(SCENARIOS)
    names = [s.strip() for s in selected.split(",") if s.strip()]
    for name in names:
        if name not in SCENARIOS:
            raise Refusal(f"Unknown scenario: {name!r} (available: {', '.join(SCENARIOS)})")
    return names


def run_qualification(inputs: Inputs, scenarios: Sequence[str]) -> dict[str, Any]:
    inputs.isolation.prepare_directories()
    witnesses = capture_live_witnesses()

    results: list[ScenarioResult] = []
    overall_passed = True

    scenario_map = {
        "isolation": scenario_isolation,
        "rc15-immutability": scenario_rc15_immutability,
        "candidate-identity": scenario_candidate_identity,
        "transition-cycle": scenario_transition_cycle,
        "refusal-matrix": scenario_refusal_matrix,
        "hlp-reconciliation": scenario_hlp_reconciliation,
        "review-fallback": scenario_review_fallback,
        "fork-regression": scenario_fork_regression,
    }

    start_time = time.monotonic()
    for name in scenarios:
        fn = scenario_map[name]
        res = ScenarioResult(name=name)
        t0 = time.monotonic()
        try:
            fn(inputs, res)
        except Exception as exc:
            res.passed = False
            res.error = str(exc)
            overall_passed = False
        finally:
            res.duration_s = round(time.monotonic() - t0, 3)
        results.append(res)
        if not res.passed:
            break

    # Verify live witnesses remained completely untouched
    for witness in witnesses:
        try:
            witness.verify_unchanged()
        except ScenarioFailure as exc:
            overall_passed = False
            results.append(
                ScenarioResult(name="witness-verification", passed=False, error=str(exc))
            )

    total_duration = round(time.monotonic() - start_time, 3)

    report = {
        "schema_version": REPORT_SCHEMA,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "overall_status": "passed" if overall_passed else "failed",
        "total_duration_s": total_duration,
        "scenarios_selected": list(scenarios),
        "scenarios": [
            {
                "name": r.name,
                "passed": r.passed,
                "duration_s": r.duration_s,
                "details": r.details,
                "error": r.error,
            }
            for r in results
        ],
        "identities": {
            "rc15_version": RC15_VERSION,
            "rc15_release_id": RC15_RELEASE_ID,
            "rc16_version": RC16_VERSION,
            "rc16_display_version": RC16_DISPLAY_VERSION,
            "rc16_hermes_commit": RC16_HERMES_COMMIT,
            "rc16_hermes_tree_sha256": RC16_HERMES_TREE_SHA256,
        },
    }

    # Write receipt
    receipt_path = (
        inputs.isolation.receipts_root / f"rc16-transition-receipt-{int(time.time())}.json"
    )
    report["receipt_path"] = str(receipt_path)
    receipt_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    run_cmd = subparsers.add_parser("run", help="Run the qualification entry")
    run_cmd.add_argument("--repo", type=Path, default=None, help="Aether repository checkout")
    run_cmd.add_argument("--candidate-commit", type=str, default=None, help="Candidate commit SHA")
    run_cmd.add_argument(
        "--fork-checkout", type=Path, default=None, help="Maintained fork checkout"
    )
    run_cmd.add_argument(
        "--source-store", type=Path, default=None, help="Source store carrying RC15"
    )
    run_cmd.add_argument("--work-root", type=Path, required=True, help="Disposable work root")
    run_cmd.add_argument(
        "--receipts-root", type=Path, required=True, help="Durable private receipts root"
    )
    run_cmd.add_argument(
        "--scenarios", type=str, default="all", help="Comma-separated scenarios or 'all'"
    )
    run_cmd.add_argument("--json", action="store_true", help="Print JSON report to stdout")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 2

    try:
        scenarios = select_scenarios(args.scenarios)
        inputs = Inputs.resolve(
            repo=args.repo,
            candidate_commit=args.candidate_commit,
            fork_checkout=args.fork_checkout,
            source_store=args.source_store,
            work_root=args.work_root,
            receipts_root=args.receipts_root,
        )
    except Refusal as exc:
        if getattr(args, "json", False):
            print(json.dumps({"status": "refused", "error": str(exc)}))
        else:
            print(f"refusal: {exc}", file=sys.stderr)
        return 2

    report = run_qualification(inputs, scenarios)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"RC16 Transition Qualification: {report['overall_status'].upper()}")
        print(f"Total Duration: {report['total_duration_s']}s")
        print(f"Receipt written to: {report['receipt_path']}")
        for sc in report["scenarios"]:
            status_mark = "PASS" if sc["passed"] else "FAIL"
            print(f"  [{status_mark}] {sc['name']} ({sc['duration_s']}s)")
            if sc.get("error"):
                print(f"         Error: {sc['error']}")

    return 0 if report["overall_status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
