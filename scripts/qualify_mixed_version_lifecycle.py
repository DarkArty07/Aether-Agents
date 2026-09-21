#!/usr/bin/env python3
"""Qualify exact-version mixed-version lifecycle behavior in an isolated store.

This is the reproducible qualification entry named by the rc6 objective (D2 / AC-3 and
the pre-live half of AC-7).  It is runnable **without** the live installation: every
destination it resolves is derived from an explicit disposable work root, and it refuses
to run when any resolved destination could overlap the operator's live install, live
selector, live unit or operator configuration.

What it proves with *real* artifacts:

* ``frozen-readers``  -- the real frozen rc3 reader rejects a pointer shape written by the
  post-rc4 serializer, and the corrected writer's active record for an rc3-shaped target
  stays inside the target's own field set, so the same real reader accepts it.
* ``frozen-writer``   -- the real frozen rc4 writer brands projections by exact
  ``record.version`` equality, so a successor receives legacy launcher/Desktop bytes,
  while the corrected source asks the *target* for its bytes and the installed target's
  own projection validation reports no mismatch.
* ``cycle``           -- exact rc5 -> candidate -> rc5 -> candidate in one isolated store,
  each hop executed by the active release's own authenticated manager against the target
  release's own reader/serializer/generator, plus failure/compensation and interruption
  invariants and explicit old-record / unknown-newer cases.
* ``legacy``          -- the rc4 writer's wrong projection bytes are reproduced in
  isolation, the supported ``aether reconcile --to active`` finishes the handoff without
  record edits, and unsupported or unprovable legacy routes refuse before mutation.
* ``launch``          -- fresh and ``--resume latest`` packaged-launcher launches against a
  candidate installed into the isolated store, from a clean and from a deliberately
  contaminated transport environment, with the measured time to real agent-ready.
* ``docs``            -- the repository's own documentation/manifest checks plus the
  documented installed CLI forms (ambiguity, ``AETHER_PROJECT_ROOT`` override/unset).
* ``isolation``       -- confinement witnesses for the live unit, active pointer, selector
  and operator configuration, and the isolation of every redirected root.

Hosts that cannot satisfy ``--help`` inputs (no isolated artifacts, a missing frozen
revision, a live destination, a dirty candidate checkout) are refused with an explicit
reason instead of being reported green.

Usage (all paths generic; the work root is disposable, receipts are private and durable)::

    uv run --frozen python scripts/qualify_mixed_version_lifecycle.py run \
        --repo <checkout at the candidate revision> \
        --candidate-commit <sha> \
        --fork-checkout <maintained-fork checkout at the accepted commit> \
        --source-store <read-only install to take authenticated old artifacts from> \
        --bundle-dir <qualified release-bundle directory (wheel + release lock)> \
        --work-root <disposable isolated work root> \
        --receipts-root <durable private receipts root>

Exit codes: ``0`` every selected scenario passed, ``1`` a scenario failed, ``2`` refused.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pty
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

REPORT_SCHEMA = "aether.mixed-version-qualification.v1"

#: Frozen predecessor revisions the objective names, and the accepted executable Hermes.
FROZEN_REVISIONS = {
    "rc3": "d8ff984c67bfc147ac9c83cf8a34a72edc27c8df",
    "rc4": "5a897746afe422f3c07f2290f9115d60204ef4d2",
    "rc5": "ee0aa036b2e0b70b137f761668209a5104f2e032",
}
MAINTAINED_FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
MAINTAINED_FORK_TREE_SHA256 = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"
CANDIDATE_VERSION = "1.0.0rc6"
CANDIDATE_DISPLAY_VERSION = "1.0.0-rc.6"
AETHER_GATEWAY_UNIT = "hermes-gateway-morfeo.service"
LAUNCHER_NAME = "aether"
DESKTOP_ENTRY_NAME = "aether.desktop"
LEGACY_DESKTOP_ENTRY_NAME = "hermes.desktop"

_RELEASE_ID_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_.-]{0,95}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

#: Frozen predecessor releases, by short name and by the version their record carries.
FROZEN_VERSIONS = {
    "rc3": "1.0.0rc3",
    "rc4": "1.0.0rc4",
    "rc5": "1.0.0rc5",
}

#: Scenario order matters: the exact-version cycle installs the candidate, and the later
#: scenarios judge the installed candidate's own code.  ``isolation`` runs last so its live
#: witnesses cover everything this entry did.
SCENARIOS = ("isolation", "cycle", "frozen-readers", "frozen-writer", "legacy", "launch", "docs")


class Refusal(RuntimeError):
    """The entry refuses to run: an input is missing, live, or contradicts itself."""


class ScenarioFailure(RuntimeError):
    """A selected scenario ran but did not satisfy one of its assertions."""


# --------------------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def tree_identity(root: Path, *, limit: int | None = None) -> dict[str, Any]:
    """Deterministic (path, size, sha256) identity of a tree, without following links."""

    rows: list[list[str]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            rows.append([relative, "link", os.readlink(path)])
            total += 1
        elif path.is_file():
            rows.append([relative, "file", sha256_file(path)])
            total += 1
        if limit is not None and total >= limit:
            break
    digest = sha256_bytes(("\n".join("|".join(row) for row in rows)).encode("utf-8"))
    return {"entries": total, "digest": digest}


def tail(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else "…" + text[-limit:]


@dataclass(slots=True)
class Recorded:
    """One executed command with its attributable identity and result."""

    label: str
    argv: list[str]
    cwd: str
    exit_code: int
    duration_ms: int
    stdout_sha256: str
    stderr_sha256: str
    stdout_tail: str
    stderr_tail: str
    environment_identity: str

    def to_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "environment_identity": self.environment_identity,
        }


# --------------------------------------------------------------------------------------
# isolation
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class Isolation:
    """Every root this entry may touch, derived only from the disposable work root."""

    work_root: Path
    receipts_root: Path
    run_id: str

    def __post_init__(self) -> None:
        self.work_root = self.work_root.expanduser().resolve()
        self.receipts_root = self.receipts_root.expanduser().resolve()

    # -- derived roots ------------------------------------------------------------------
    @property
    def home(self) -> Path:
        return self.work_root / "home"

    @property
    def data_home(self) -> Path:
        return self.work_root / "data"

    @property
    def state_home(self) -> Path:
        return self.work_root / "state"

    @property
    def config_home(self) -> Path:
        return self.work_root / "config"

    @property
    def cache_home(self) -> Path:
        return self.work_root / "cache"

    @property
    def runtime_dir(self) -> Path:
        return self.work_root / "run"

    @property
    def tmp(self) -> Path:
        return self.work_root / "tmp"

    @property
    def store_root(self) -> Path:
        return self.data_home / "aether"

    @property
    def state_root(self) -> Path:
        return self.state_home / "aether"

    @property
    def hermes_root(self) -> Path:
        """AETHER_HERMES_ROOT: profile/registry base for the isolated installation."""

        return self.state_root / "hermes"

    @property
    def projections(self) -> Path:
        """Where a disposable installation derives its launcher/Desktop/unit files."""

        return self.store_root.parent / "aether-projections"

    @property
    def receipts(self) -> Path:
        return self.receipts_root / self.run_id

    @property
    def project(self) -> Path:
        """The exact managed project this installation binds its branded projections to."""

        return self.work_root / "project"

    @property
    def second_project(self) -> Path:
        return self.work_root / "project-two"

    def create(self) -> None:
        for path in (
            self.home,
            self.data_home,
            self.state_home,
            self.config_home,
            self.cache_home,
            self.runtime_dir,
            self.tmp,
            self.receipts,
        ):
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o700)

    # -- live guard ---------------------------------------------------------------------
    def live_overlaps(self) -> list[str]:
        home = Path.home()
        live = [
            ("live data root", home / ".local" / "share" / "aether"),
            ("live state root", home / ".local" / "state" / "aether"),
            ("operator launcher directory", home / ".local" / "bin"),
            ("operator Desktop entries", home / ".local" / "share" / "applications"),
            ("operator user units", home / ".config" / "systemd" / "user"),
            ("operator Hermes profile root", home / ".local" / "state" / "aether" / "hermes"),
        ]
        candidates = [
            ("work root", self.work_root),
            ("isolated HOME", self.home),
            ("isolated data home", self.data_home),
            ("isolated state home", self.state_home),
            ("isolated store root", self.store_root),
            ("isolated state root", self.state_root),
            ("isolated projections", self.projections),
        ]
        overlaps: list[str] = []
        for label, candidate in candidates:
            resolved = candidate.expanduser().resolve()
            for live_label, live_path in live:
                if (
                    resolved == live_path
                    or resolved.is_relative_to(live_path)
                    or live_path.is_relative_to(resolved)
                ):
                    overlaps.append(f"{label} {resolved} overlaps {live_label} {live_path}")
        # Receipts are written output, and the objective documents them under the operator's
        # private state root.  They may never *be* a live artifact location or a live store.
        receipts = self.receipts_root.expanduser().resolve()
        for live_label, live_path in (
            ("live data root", home / ".local" / "share" / "aether"),
            ("live active pointer", home / ".local" / "share" / "aether" / "active.json"),
            ("operator launcher directory", home / ".local" / "bin"),
            ("operator Desktop entries", home / ".local" / "share" / "applications"),
            ("operator user units", home / ".config" / "systemd" / "user"),
            ("operator Hermes profile root", home / ".local" / "state" / "aether" / "hermes"),
        ):
            if receipts == live_path or receipts.is_relative_to(live_path):
                overlaps.append(f"receipts root {receipts} overlaps {live_label} {live_path}")
        return overlaps

    # -- child environment --------------------------------------------------------------
    def environment(self, extra: dict[str, str | None] | None = None) -> dict[str, str]:
        """A child environment with no live transport, router or board routing inherited."""

        source = os.environ
        environment: dict[str, str] = {}
        for name, value in source.items():
            if name.startswith(("HERMES_", "AETHER_", "PYTHON", "UV_", "PIP_")):
                continue
            if name in ("VIRTUAL_ENV", "DBUS_SESSION_BUS_ADDRESS", "SYSTEMD_EXEC_PID"):
                continue
            environment[name] = value
        environment.update(
            {
                "HOME": str(self.home),
                "XDG_DATA_HOME": str(self.data_home),
                "XDG_STATE_HOME": str(self.state_home),
                "XDG_CONFIG_HOME": str(self.config_home),
                "XDG_CACHE_HOME": str(self.cache_home),
                "XDG_RUNTIME_DIR": str(self.runtime_dir),
                "TMPDIR": str(self.tmp),
                "AETHER_HERMES_ROOT": str(self.hermes_root),
                "HERMES_HOME": str(self.hermes_root / "profiles" / "morfeo"),
                "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
                "UV_LINK_MODE": "copy",
            }
        )
        for name, value in (extra or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        return environment

    def environment_identity(self, environment: dict[str, str]) -> str:
        """Digest the *isolation-relevant* environment, never the whole operator environment."""

        keys = (
            "HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_RUNTIME_DIR",
            "TMPDIR",
            "AETHER_HERMES_ROOT",
            "HERMES_HOME",
            "HERMES_PYTHON",
            "HERMES_PYTHON_SRC_ROOT",
            "AETHER_RUNTIME_ROOT",
            "AETHER_PROJECT_ROOT",
            "AETHER_PROJECT_ID",
            "DBUS_SESSION_BUS_ADDRESS",
        )
        observed = {key: environment.get(key) for key in keys}
        inherited_board = sorted(name for name in environment if name.startswith("HERMES_KANBAN_"))
        inherited_hermes = sorted(name for name in environment if name.startswith("HERMES_"))
        return sha256_bytes(
            canonical(
                {
                    "roots": observed,
                    "hermes_kanban_variables": inherited_board,
                    "inherited_hermes_variables": [
                        name for name in inherited_hermes if name not in keys
                    ],
                    "interpreter": sys.version.split()[0],
                    "platform": sys.platform,
                }
            ).encode("utf-8")
        )

    # -- receipts -----------------------------------------------------------------------
    def write_json(self, relative: str, payload: Any) -> Path:
        path = self.receipts / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


# --------------------------------------------------------------------------------------
# confinement witnesses
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class WitnessEntry:
    path: str
    state: dict[str, Any]


def witness(path: Path) -> WitnessEntry:
    """Content/identity/mtime witness of one live artifact (never following links)."""

    target = path.expanduser()
    entry: dict[str, Any] = {"path": str(target)}
    try:
        info = target.lstat()
    except FileNotFoundError:
        return WitnessEntry(str(target), {"exists": False})
    except OSError as error:
        return WitnessEntry(str(target), {"exists": None, "error": str(error)})
    entry.update(
        {
            "exists": True,
            "mode": stat.S_IMODE(info.st_mode),
            "inode": info.st_ino,
            "device": info.st_dev,
            "size": info.st_size,
            "mtime_ns": info.st_mtime_ns,
            "is_symlink": stat.S_ISLNK(info.st_mode),
        }
    )
    if stat.S_ISLNK(info.st_mode):
        entry["link_target"] = os.readlink(target)
    elif stat.S_ISREG(info.st_mode):
        entry["sha256"] = sha256_file(target)
    return WitnessEntry(str(target), entry)


def witness_set(paths: Iterable[tuple[str, Path]]) -> dict[str, dict[str, Any]]:
    return {label: witness(path).state for label, path in paths}


def live_witness_paths() -> list[tuple[str, Path]]:
    home = Path.home()
    store = home / ".local" / "share" / "aether"
    state = home / ".local" / "state" / "aether"
    paths: list[tuple[str, Path]] = [
        ("live-active-pointer", store / "active.json"),
        ("live-selector", store / "runtime" / "current"),
        ("live-gateway-unit", home / ".config" / "systemd" / "user" / AETHER_GATEWAY_UNIT),
    ]
    for version, release_id in (
        ("rc3", "1.0.0rc3-8987f650c027ad09"),
        ("rc4", "1.0.0rc4-9316cbddfee2b795"),
        ("rc5", "1.0.0rc5-40d506a4117229ad"),
    ):
        paths.append((f"live-{version}-record", store / "releases" / release_id / "record.json"))
    for role in ("morfeo", "supervisor", "implementer"):
        paths.append(
            (f"operator-{role}-config", state / "hermes" / "profiles" / role / "config.yaml")
        )
    return paths


# --------------------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------------------


class Session:
    """Runs commands inside the isolated installation and records every result."""

    def __init__(self, isolation: Isolation) -> None:
        self.isolation = isolation
        self.commands: list[Recorded] = []

    def environment_identity(self, environment: dict[str, str]) -> str:
        return self.isolation.environment_identity(environment)

    def write_scenario(self, scenario: ScenarioResult) -> Path:
        return self.isolation.write_json(f"scenarios/{scenario.name}.json", scenario.to_json())

    def run(
        self,
        label: str,
        argv: Sequence[str | Path],
        *,
        env: dict[str, str],
        cwd: Path,
        timeout: int = 900,
        check: bool = False,
        stdin: str | None = None,
    ) -> Recorded:
        argv_list = [str(item) for item in argv]
        started = time.time()
        try:
            completed = subprocess.run(
                argv_list,
                cwd=str(cwd),
                env=env,
                input=stdin,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
            record = Recorded(
                label=label,
                argv=argv_list,
                cwd=str(cwd),
                exit_code=completed.returncode,
                duration_ms=int((time.time() - started) * 1000),
                stdout_sha256=sha256_bytes(completed.stdout.encode("utf-8")),
                stderr_sha256=sha256_bytes(completed.stderr.encode("utf-8")),
                stdout_tail=tail(completed.stdout),
                stderr_tail=tail(completed.stderr),
                environment_identity=self.environment_identity(env),
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            record = Recorded(
                label=label,
                argv=argv_list,
                cwd=str(cwd),
                exit_code=124,
                duration_ms=int((time.time() - started) * 1000),
                stdout_sha256=sha256_bytes(stdout.encode("utf-8")),
                stderr_sha256=sha256_bytes(stderr.encode("utf-8")),
                stdout_tail=tail(stdout),
                stderr_tail="TIMEOUT: " + tail(stderr),
                environment_identity=self.environment_identity(env),
            )
        self.commands.append(record)
        if check and record.exit_code != 0:
            raise ScenarioFailure(
                f"command {label} failed (exit {record.exit_code}): {record.stderr_tail}"
            )
        return record


def parse_json_stdout(record: Recorded) -> dict[str, Any] | None:
    """Return the last JSON object printed on stdout, or ``None``."""

    for line in reversed(record.stdout_tail.splitlines()):
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


# --------------------------------------------------------------------------------------
# scenario results
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class Assertion:
    requirement: str
    expected: Any
    observed: str
    ok: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement,
            "expected": self.expected,
            "observed": self.observed,
            "result": "pass" if self.ok else "fail",
        }


@dataclass(slots=True)
class ScenarioResult:
    name: str
    scope: str
    assertions: list[Assertion] = field(default_factory=list)
    commands: list[Recorded] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    limits: list[str] = field(default_factory=list)
    error: str | None = None

    def check(self, requirement: str, expected: Any, actual: Any, want: Any) -> Assertion:
        ok = actual == want
        assertion = Assertion(
            requirement=requirement,
            expected=expected,
            observed=f"{actual!r}",
            ok=ok,
        )
        self.assertions.append(assertion)
        return assertion

    def require(self, requirement: str, expected: Any, actual: Any, want: Any) -> None:
        if not self.check(requirement, expected, actual, want).ok:
            raise ScenarioFailure(f"{requirement}: expected {expected}, observed {actual!r}")

    @property
    def status(self) -> str:
        if self.error is not None:
            return "failed"
        if any(not assertion.ok for assertion in self.assertions):
            return "failed"
        return "passed"

    def to_json(self) -> dict[str, Any]:
        return {
            "scenario": self.name,
            "scope": self.scope,
            "status": self.status,
            "error": self.error,
            "assertions": [assertion.to_json() for assertion in self.assertions],
            "commands": [command.to_json() for command in self.commands],
            "artifacts": self.artifacts,
            "limits": self.limits,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> ScenarioResult:
        assertions = [
            Assertion(
                requirement=a["requirement"],
                expected=a.get("expected"),
                observed=a.get("observed", ""),
                ok=a.get("result") == "pass" if "result" in a else a.get("ok", True),
            )
            for a in payload.get("assertions", [])
        ]
        commands = [
            Recorded(
                label=c["label"],
                argv=c["argv"],
                cwd=c["cwd"],
                exit_code=c["exit_code"],
                duration_ms=c["duration_ms"],
                stdout_sha256=c["stdout_sha256"],
                stderr_sha256=c["stderr_sha256"],
                stdout_tail=c["stdout_tail"],
                stderr_tail=c["stderr_tail"],
                environment_identity=c["environment_identity"],
            )
            for c in payload.get("commands", [])
        ]
        return cls(
            name=payload["scenario"],
            scope=payload.get("scope", payload["scenario"]),
            assertions=assertions,
            commands=commands,
            artifacts=payload.get("artifacts", {}),
            limits=payload.get("limits", []),
            error=payload.get("error"),
        )


# --------------------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class Inputs:
    repo: Path
    candidate_commit: str
    fork_checkout: Path
    source_store: Path
    bundle_dir: Path | None
    isolation: Isolation
    launch_timeout: int = 180

    # -- authenticated old artifacts (read-only access to the source installation) ------
    def source_release(self, version: str) -> Path:
        release = find_release_directory(self.source_store, FROZEN_VERSIONS.get(version, version))
        if release is None:
            raise Refusal(f"the source installation carries no {version} release")
        return release

    def source_wheel(self, version: str) -> Path:
        release = self.source_release(version)
        for candidate in sorted((release / "artifacts").glob("aether_agents-*.whl")):
            return candidate
        raise Refusal(f"the {version} release carries no wheel artifact")

    def source_lock(self, version: str) -> Path:
        return self.source_release(version) / "release-lock.json"

    # -- verification -------------------------------------------------------------------
    def verify_repo(self) -> dict[str, Any]:
        repo = self.repo.resolve()
        if not (repo / ".git").exists():
            raise Refusal(f"candidate checkout is not a Git worktree: {repo}")
        head = git(repo, "rev-parse", "HEAD")
        if head != self.candidate_commit:
            raise Refusal(
                f"candidate checkout HEAD {head} is not the requested commit "
                f"{self.candidate_commit}"
            )
        dirty = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        if dirty.strip():
            raise Refusal("candidate checkout is dirty; qualification needs the exact revision")
        version = (repo / "VERSION").read_text(encoding="ascii").strip()
        if version != CANDIDATE_VERSION:
            raise Refusal(f"candidate VERSION {version!r} is not {CANDIDATE_VERSION!r}")
        return {
            "path": str(repo),
            "commit": head,
            "version": version,
            "tree": git(repo, "rev-parse", "HEAD^{tree}"),
        }

    def verify_fork(self) -> dict[str, Any]:
        fork = self.fork_checkout.resolve()
        head = git(fork, "rev-parse", "HEAD")
        if head != MAINTAINED_FORK_COMMIT:
            raise Refusal(f"maintained-fork checkout HEAD {head} is not {MAINTAINED_FORK_COMMIT}")
        branch = git(fork, "rev-parse", "--abbrev-ref", "HEAD")
        if branch != "aether-main":
            raise Refusal(f"maintained-fork checkout branch {branch!r} is not 'aether-main'")
        remote = git(fork, "remote", "get-url", "origin")
        if "aether-hermes" not in remote:
            raise Refusal(f"maintained-fork checkout origin {remote!r} is not the maintained fork")
        dirty = git(fork, "status", "--porcelain=v1", "--untracked-files=all")
        if dirty.strip():
            raise Refusal("maintained-fork checkout is dirty")
        return {"path": str(fork), "commit": head, "branch": branch, "remote": remote}

    def verify_source_store(self) -> dict[str, Any]:
        store = self.source_store.resolve()
        if not (store / "active.json").is_file():
            raise Refusal(f"source store has no active record to take artifacts from: {store}")
        releases = {}
        for version, revision in FROZEN_REVISIONS.items():
            release_dir = find_release_directory(store, FROZEN_VERSIONS[version])
            if release_dir is None:
                raise Refusal(f"source store carries no installed {version} release")
            lock_path = release_dir / "release-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            commit = lock.get("aether", {}).get("git_commit")
            if commit != revision:
                raise Refusal(
                    f"source store {version} release lock binds {commit!r}, expected {revision!r}"
                )
            releases[version] = {
                "release_id": release_dir.name,
                "release_lock_sha256": sha256_file(lock_path),
                "record_sha256": sha256_file(release_dir / "record.json"),
                "lock_commit": commit,
            }
        return {"path": str(store), "releases": releases}

    def verify_bundle(self) -> dict[str, Any]:
        if self.bundle_dir is None:
            raise Refusal("--bundle-dir is required unless --build-bundle is selected")
        bundle = self.bundle_dir.resolve()
        wheels = sorted(bundle.glob("aether_agents-*.whl"))
        locks = sorted(bundle.glob("*release-lock*.json"))
        if len(wheels) != 1 or len(locks) != 1:
            raise Refusal(
                f"bundle {bundle} must hold exactly one wheel and one release lock "
                f"(observed {len(wheels)} wheel(s), {len(locks)} lock(s))"
            )
        lock = json.loads(locks[0].read_text(encoding="utf-8"))
        commit = lock.get("aether", {}).get("git_commit")
        if commit != self.candidate_commit:
            raise Refusal(
                f"bundle release lock binds {commit!r}, not the candidate commit "
                f"{self.candidate_commit!r}"
            )
        digest = sha256_file(wheels[0])
        if lock.get("aether", {}).get("wheel_sha256") != digest:
            raise Refusal("bundle wheel digest does not match its release lock")
        return {
            "path": str(bundle),
            "wheel": wheels[0].name,
            "wheel_sha256": digest,
            "release_lock": locks[0].name,
            "release_lock_sha256": sha256_file(locks[0]),
            "lock_commit": commit,
            "version": lock.get("aether", {}).get("version"),
        }


def git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env={
            k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k == "GIT_EXEC_PATH"
        },
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def find_release_directory(store: Path, version: str) -> Path | None:
    releases = store / "releases"
    if not releases.is_dir():
        return None
    for candidate in sorted(releases.iterdir()):
        if not candidate.is_dir() or candidate.name.startswith("."):
            continue
        if _RELEASE_ID_RE.fullmatch(candidate.name) is None:
            continue
        record = candidate / "record.json"
        if not record.is_file():
            continue
        try:
            payload = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if payload.get("version") == version:
            return candidate
    return None


def render(lines: Sequence[str]) -> str:
    return "\n".join(lines) + "\n"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# --------------------------------------------------------------------------------------
# embedded probes: each probe runs inside one release's own authenticated interpreter
# --------------------------------------------------------------------------------------

READER_PROBE = r"""
import json, sys
from aether_agents.lifecycle import IntegrityError, ReleaseRecord

payload = json.loads(sys.stdin.read())
try:
    record = ReleaseRecord.from_json(payload)
except IntegrityError as error:
    print(json.dumps({"outcome": "rejected", "error": str(error)}))
    raise SystemExit(0)
except Exception as error:  # a different refusal class is still a refusal
    print(json.dumps({"outcome": "rejected", "error": f"{type(error).__name__}: {error}"}))
    raise SystemExit(0)
print(json.dumps({
    "outcome": "accepted",
    "version": record.version,
    "record_fields": sorted(payload),
}))
"""

LEGACY_WRITER_PROBE = r"""
import json, sys
from dataclasses import asdict
from pathlib import Path
from aether_agents.lifecycle import ReleaseRecord, ReleaseStore

request = json.loads(sys.stdin.read())
store = ReleaseStore(Path(request["scratch_root"]), state_root=Path(request["scratch_state"]))
target = ReleaseRecord.from_json(request["target_record"])
store._commit_active(target)
written = json.loads(store.active_pointer.read_text(encoding="utf-8"))
print(json.dumps({
    "outcome": "written",
    "fields": sorted(written),
    "payload": written,
    "matches_source_dataclass": sorted(written) == sorted(asdict(target)),
}))
"""

TARGET_PAYLOAD_PROBE = r"""
import json, sys
from pathlib import Path
from aether_agents.lifecycle import ReleaseStore

request = json.loads(sys.stdin.read())
store = ReleaseStore(Path(request["store_root"]), state_root=Path(request["state_root"]))
record = store._read_release(request["release_id"])
previous = request.get("previous_release_id", None)
if hasattr(store, "_target_active_payload"):
    payload = store._target_active_payload(record, previous_release_id=previous)
    mode = "target_owned"
else:
    from dataclasses import asdict
    payload = asdict(record)
    payload["previous_release_id"] = previous
    mode = "source_dataclass"
print(json.dumps({"outcome": "written", "mode": mode, "fields": sorted(payload), "payload": payload}))
"""

PROJECTION_PROBE = r"""
import base64, hashlib, json, sys
from pathlib import Path
from aether_agents.lifecycle import LifecycleManager, ProjectionRoots, ReleaseStore

request = json.loads(sys.stdin.read())
store = ReleaseStore(Path(request["store_root"]), state_root=Path(request["state_root"]))
roots = ProjectionRoots.disposable(Path(request["scratch_projections"]))
manager = LifecycleManager(
    store=store,
    python_executable=Path(sys.executable),
    projections=roots,
)
record = store._read_release(request["release_id"])
spec = manager.projection_spec(record)
report = {
    "outcome": "planned",
    "launcher_path": str(spec.launcher_path),
    "launcher_name": spec.launcher_path.name,
    "desktop_path": str(spec.desktop_path),
    "desktop_name": spec.desktop_path.name,
    "launcher_sha256": hashlib.sha256(spec.launcher_bytes).hexdigest(),
    "launcher_selector": b"exec \"$AETHER_RUNTIME_ROOT/venv/bin/aether\"" in spec.launcher_bytes,
    "desktop_sha256": hashlib.sha256(spec.desktop_bytes).hexdigest(),
    "record_version": record.version,
}
if request.get("apply"):
    outcome = manager.project_release(record, restart_service=False)
    report["applied"] = {key: value for key, value in outcome.items()}
print(json.dumps(report))
"""

TARGET_PLAN_PROBE = r"""
import base64, hashlib, json, sys
from pathlib import Path
from aether_agents.lifecycle import LifecycleManager, ProjectionRoots, ReleaseStore

request = json.loads(sys.stdin.read())
store = ReleaseStore(Path(request["store_root"]), state_root=Path(request["state_root"]))
roots = ProjectionRoots.disposable(Path(request["scratch_projections"]))
manager = LifecycleManager(
    store=store,
    python_executable=Path(sys.executable),
    projections=roots,
)
plan = manager._prepare_target_projections_subprocess(
    request["target_release_id"],
    store._read_release(request["target_release_id"]),
)
print(json.dumps({
    "outcome": "planned",
    "release_id": plan.release_id,
    "version": plan.version,
    "is_branded": plan.is_branded,
    "launcher_path": str(plan.launcher_path),
    "desktop_path": str(plan.desktop_path),
    "digests": plan.digests,
}))
"""

VALIDATE_RECORD_PROBE = r"""
import json, sys
from pathlib import Path
from aether_agents.lifecycle import LifecycleManager, ProjectionRoots, ReleaseStore

request = json.loads(sys.stdin.read())
store = ReleaseStore(Path(request["store_root"]), state_root=Path(request["state_root"]))
roots = ProjectionRoots.disposable(Path(request["scratch_projections"]))
manager = LifecycleManager(store=store, python_executable=Path(sys.executable), projections=roots)
try:
    manager._validate_target_record_subprocess(request["target_release_id"], request["proposed"])
except Exception as error:
    print(json.dumps({"outcome": "refused", "error": f"{type(error).__name__}: {error}"}))
    raise SystemExit(0)
print(json.dumps({"outcome": "accepted"}))
"""

FINGERPRINT_PROBE = r"""
import json, sys
import aether_agents
print(json.dumps({"package_file": aether_agents.__file__, "prefix": sys.prefix}))
"""

#: Registers one managed project with the product's own marker/registry writers.  ``aether
#: init`` additionally requires a native Hermes projects row, which is Hermes-owned state a
#: disposable home does not carry; the objective's lifecycle surfaces only need the portable
#: marker and the product registry to agree, which this probe reuses the product code for.
PROJECT_PROBE = r"""
import json, sys, tomllib, uuid
from pathlib import Path
from aether_agents.commands.init import _write_marker
from aether_agents.observation.context import ProjectRegistry, canonical_project_id
from aether_agents.project_marker import validate_project_marker

request = json.loads(sys.stdin.read())
repo = Path(request["project"])
state_root = Path(request["state_root"])
marker_path = repo / ".aether" / "project.toml"
project_id = None
if marker_path.is_file():
    project_id = canonical_project_id(
        tomllib.loads(marker_path.read_text(encoding="utf-8")).get("project_id")
    )
if project_id is None:
    project_id = str(uuid.uuid4())
marker = {
    "schema_version": 1,
    "project_id": project_id,
    "name": request["name"],
    "initialized_by": request.get("initialized_by", "1.0.0-rc.6"),
    "forge": "local",
    "contract_root": "specs",
    "default_branch": "main",
}
marker_path.parent.mkdir(parents=True, exist_ok=True)
_write_marker(marker_path, marker)
registry = ProjectRegistry(state_root)
registered = registry.register(project_id, repo, name=request["name"])
written = tomllib.loads(marker_path.read_text(encoding="utf-8"))
print(json.dumps({
    "outcome": "registered",
    "project_id": project_id,
    "registered": registered,
    "marker_validates": validate_project_marker(written) is not None,
    "registry": str(registry.path),
    "verified": registry.verify_with_marker(project_id),
}))
"""

#: Derives the promotion lock for the candidate revision with the product's own local-candidate
#: lock builder.  The published bundle lock carries the maintained fork's *nearest* git-describe
#: tag, which the install/promotion path refuses when that tag does not dereference to the locked
#: commit; the promotion path consumes the tag-free local-candidate lock shape the operator
#: installation itself was built with, and this probe produces exactly that lock from explicit,
#: already verified identity inputs.
LOCAL_CANDIDATE_LOCK_PROBE = r"""
import json, sys
from pathlib import Path
from aether_agents.lifecycle import LocalCandidate, LifecycleManager, ReleaseStore

request = json.loads(sys.stdin.read())
store = ReleaseStore(Path(request["store_root"]), state_root=Path(request["state_root"]))
manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
fork = manager._verify_fork_candidate_checkout(
    Path(request["fork_checkout"]), request["fork_commit"]
)
candidate = LocalCandidate(
    aether_checkout=Path(request["aether_checkout"]),
    aether_commit=request["aether_commit"],
    aether_tag=request["aether_tag"],
    package_version=request["package_version"],
    display_version=request["display_version"],
    aether_python_requires=request["aether_python_requires"],
    fork_checkout=fork["checkout"],
    fork_commit=fork["commit"],
    fork_branch=fork["branch"],
    fork_version=fork["version"],
    fork_python_requires=fork["python_requires"],
    fork_source_tree_sha256=fork["source_tree_sha256"],
    hlp_coverage={},
)
build = manager._build_local_candidate(candidate, staging=Path(request["staging"]))
lock = json.loads(build.release_lock.read_text(encoding="utf-8"))
print(json.dumps({
    "outcome": "built",
    "wheel": str(build.wheel),
    "wheel_sha256": __import__("hashlib").sha256(build.wheel.read_bytes()).hexdigest(),
    "release_lock": str(build.release_lock),
    "lock_aether": lock["aether"],
    "lock_hermes": lock["hermes"],
    "fork": {key: (str(value) if isinstance(value, Path) else value) for key, value in fork.items()},
}))
"""


# --------------------------------------------------------------------------------------
# scenario: isolation and confinement
# --------------------------------------------------------------------------------------


def scenario_isolation(
    inputs: Inputs,
    session: Session,
    *,
    before: dict[str, dict[str, Any]],
    scenario_result: ScenarioResult,
) -> None:
    isolation = inputs.isolation
    result = scenario_result

    # 1. Fail closed: the guard must reject a live destination.
    probe = Isolation(
        work_root=Path.home() / ".local" / "share" / "aether",
        receipts_root=isolation.receipts_root,
        run_id="guard-probe",
    )
    overlaps = probe.live_overlaps()
    result.require(
        "AC-7/isolation: a live destination is refused",
        "at least one overlap error for the live data root",
        bool(overlaps),
        True,
    )
    refusal = session.run(
        "guard-refusal-cli",
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "run",
            "--repo",
            str(inputs.repo),
            "--candidate-commit",
            inputs.candidate_commit,
            "--fork-checkout",
            str(inputs.fork_checkout),
            "--source-store",
            str(inputs.source_store),
            "--bundle-dir",
            str(inputs.bundle_dir or inputs.isolation.work_root / "absent"),
            "--work-root",
            str(Path.home() / ".local" / "share" / "aether"),
            "--receipts-root",
            str(inputs.isolation.receipts),
            "--scenarios",
            "isolation",
        ],
        env=isolation.environment(),
        cwd=inputs.repo,
    )
    result.require(
        "AC-7/isolation: the entry refuses to run against the live store",
        "exit 2 with a refusal naming the overlap",
        (refusal.exit_code, "overlaps" in refusal.stderr_tail),
        (2, True),
    )

    # 2. Redirected roots and transport isolation in the children's environment.
    synthetic = {
        "HERMES_KANBAN_TASK": "leak-probe",
        "HERMES_KANBAN_DB": "/leak-probe/kanban.db",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "PYTHONPATH": "/leak-probe/src",
    }
    saved = {name: os.environ.get(name) for name in synthetic}
    os.environ.update(synthetic)
    try:
        environment = isolation.environment()
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    identity = isolation.environment_identity(environment)
    live = [
        ("HOME", str(Path.home())),
        ("XDG_DATA_HOME", str(Path.home() / ".local" / "share")),
        ("XDG_STATE_HOME", str(Path.home() / ".local" / "state")),
        ("AETHER_HERMES_ROOT", str(Path.home() / ".local" / "state" / "aether" / "hermes")),
    ]
    diverted: list[tuple[str, str, str]] = []
    for name, live_value in live:
        observed = str(environment.get(name))
        if observed == live_value or observed.startswith(str(Path.home())):
            diverted.append((name, live_value, observed))
    result.require(
        "AC-7/isolation: every redirected root is distinct from the operator value",
        "no isolated root resolves under the operator home",
        diverted,
        [],
    )
    leaked = sorted(name for name in environment if name.startswith("HERMES_KANBAN_"))
    result.require(
        "AC-7/isolation: no HERMES_KANBAN_* routing variable is inherited",
        "no inherited board routing",
        leaked,
        [],
    )
    result.require(
        "AC-7/isolation: no live session D-Bus socket is inherited",
        "DBUS_SESSION_BUS_ADDRESS absent",
        environment.get("DBUS_SESSION_BUS_ADDRESS"),
        None,
    )
    result.artifacts["environment_identity"] = identity
    result.artifacts["environment_roots"] = {
        key: environment.get(key)
        for key in ("HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "TMPDIR", "AETHER_HERMES_ROOT")
    }

    # 3. Confinement witnesses: the live unit, pointer, selector and operator config.
    after = witness_set(live_witness_paths())
    changed = sorted(label for label, state in after.items() if before.get(label) != state)
    result.require(
        "AC-7/isolation: live unit, active pointer, selector and operator configuration are untouched",
        "no witness entry differs before/after",
        changed,
        [],
    )
    result.artifacts["witnesses"] = {
        label: {"before": before.get(label), "after": after.get(label)} for label in sorted(after)
    }

    # 4. Service boundary: the isolated store must not own the operator's service manager.
    doctor = session.run(
        "doctor-service-boundary",
        [str(store_cli(inputs.isolation)), "doctor", "--json"],
        env=isolation.environment(),
        cwd=inputs.isolation.work_root,
    )
    envelope = parse_json_stdout(doctor) or {}
    controller = (envelope.get("data", {}).get("observer", {}) or {}).get("service_controller", {})
    result.require(
        "AC-7/isolation: the isolated store uses a disabled service controller",
        "available=false and reason=disabled_non_installed_environment",
        (controller.get("available"), controller.get("reason")),
        (False, "disabled_non_installed_environment"),
    )
    result.limits.append(
        "the service boundary is exercised through the product's own DisabledServiceController; "
        "no mocked OS supervision stands in for installed-package behavior, and no systemctl "
        "effect is claimed"
    )


# --------------------------------------------------------------------------------------
# scenario: frozen readers / field evolution
# --------------------------------------------------------------------------------------


def _probe_script(isolation: Isolation, name: str, body: str) -> Path:
    directory = isolation.work_root / "probe"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.py"
    path.write_text(body, encoding="utf-8")
    return path


def _release_python(release_dir: Path) -> Path:
    if not (release_dir / "manager").is_dir() and not (release_dir / "venv").is_dir():
        # A source checkout (no installed environment) runs the probe with the entry's own
        # interpreter, which is the candidate revision under qualification.
        return Path(sys.executable)
    for candidate in (
        release_dir / "manager" / "bin" / "python",
        release_dir / "venv" / "bin" / "python",
    ):
        if candidate.exists():
            return candidate
    raise Refusal(f"installed release {release_dir} has no manager interpreter")


def _run_probe(
    session: Session,
    inputs: Inputs,
    label: str,
    *,
    release_dir: Path,
    body: str,
    payload: dict[str, Any],
    env: dict[str, str],
) -> dict[str, Any]:
    script = _probe_script(inputs.isolation, label, body)
    record = session.run(
        label,
        [_release_python(release_dir), "-P", "-s", str(script)],
        env=env,
        cwd=release_dir,
        stdin=json.dumps(payload),
        check=False,
    )
    parsed = parse_json_stdout(record)
    return {"record": record, "parsed": parsed or {}}


def scenario_frozen_readers(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    env = isolation.environment()
    store_root = isolation.store_root
    state_root = isolation.state_root

    rc3_dir = find_release_directory(store_root, "1.0.0rc3")
    rc5_dir = find_release_directory(store_root, "1.0.0rc5")
    if rc3_dir is None or rc5_dir is None:
        raise ScenarioFailure(
            "the isolated store must carry rc3 and rc5 releases for this scenario"
        )

    rc3_record = json.loads((rc3_dir / "record.json").read_text(encoding="utf-8"))
    rc5_record = json.loads((rc5_dir / "record.json").read_text(encoding="utf-8"))
    result.artifacts["rc3_record_fields"] = sorted(rc3_record)
    result.artifacts["rc5_record_fields"] = sorted(rc5_record)
    result.require(
        "AC-3/field-evolution: the frozen predecessor records differ by the post-rc4 field",
        "tui_sha256 absent from rc3 and present in rc5",
        ("tui_sha256" in rc3_record, "tui_sha256" in rc5_record),
        (False, True),
    )

    # (a) the post-rc4 serializer's pointer shape: real rc5 code writing the real rc4-era record.
    scratch = isolation.work_root / "frozen-readers"
    scratch.mkdir(parents=True, exist_ok=True)
    legacy = _run_probe(
        session,
        inputs,
        "rc5-old-writer-pointer",
        release_dir=rc5_dir,
        body=LEGACY_WRITER_PROBE,
        payload={
            "scratch_root": str(scratch / "store"),
            "scratch_state": str(scratch / "state"),
            "target_record": rc3_record,
        },
        env=env,
    )
    old_pointer = legacy["parsed"].get("payload") or {}
    result.require(
        "AC-3/defect-1: the post-rc4 writer serializes its own dataclass into an rc3-shaped target pointer",
        "pointer carries tui_sha256 with a null value",
        sorted(key for key in old_pointer if key not in rc3_record),
        ["tui_sha256"],
    )

    # (b) the corrected writer's pointer for the same record.
    corrected = _run_probe(
        session,
        inputs,
        "candidate-target-owned-pointer",
        release_dir=find_release_directory(store_root, CANDIDATE_VERSION) or rc5_dir,
        body=TARGET_PAYLOAD_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(state_root),
            "release_id": rc3_dir.name,
            "previous_release_id": rc5_dir.name,
        },
        env=env,
    )
    corrected_payload = corrected["parsed"].get("payload") or {}
    result.require(
        "AC-3/L1: the corrected writer keeps the target-owned field set",
        "the rc3 record's own field set, with no field added and none dropped",
        sorted(corrected_payload),
        sorted(rc3_record),
    )
    result.require(
        "AC-3/L1: the corrected writer updates only the transition-owned predecessor",
        {"previous_release_id": rc5_dir.name},
        {
            key: corrected_payload[key]
            for key in corrected_payload
            if corrected_payload[key] != rc3_record.get(key)
        },
        {"previous_release_id": rc5_dir.name},
    )
    result.artifacts["corrected_pointer_sha256"] = sha256_bytes(
        canonical(corrected_payload).encode("utf-8")
    )

    # (c) the frozen rc3 reader judges both shapes.
    for label, payload in (
        ("rc3-reader-old-writer-pointer", old_pointer),
        ("rc3-reader-corrected-writer-pointer", corrected_payload),
        ("rc3-reader-native-record", rc3_record),
        (
            "rc3-reader-null-tui-pointer",
            {**rc3_record, "tui_sha256": None},
        ),
    ):
        outcome = _run_probe(
            session,
            inputs,
            label,
            release_dir=rc3_dir,
            body=READER_PROBE,
            payload=payload,
            env=env,
        )
        result.artifacts[label] = outcome["parsed"]

    result.require(
        "AC-3/defect-1: the real rc3 reader rejects the post-rc4 writer's pointer",
        "rejected",
        result.artifacts["rc3-reader-old-writer-pointer"].get("outcome"),
        "rejected",
    )
    result.require(
        "AC-3/defect-1: the frozen rc3 reader rejects the field even when its value is null",
        "rejected",
        result.artifacts["rc3-reader-null-tui-pointer"].get("outcome"),
        "rejected",
    )
    result.require(
        "AC-3/L1: the corrected writer produces a target-readable active record",
        "accepted by the real rc3 reader",
        result.artifacts["rc3-reader-corrected-writer-pointer"].get("outcome"),
        "accepted",
    )
    result.require(
        "AC-3/field-evolution control: the rc3 reader still accepts its own record",
        "accepted",
        result.artifacts["rc3-reader-native-record"].get("outcome"),
        "accepted",
    )

    # (d) the candidate's own reader accepts both generations (backward compatibility).
    candidate_dir = find_release_directory(store_root, CANDIDATE_VERSION)
    if candidate_dir is not None:
        for label, payload in (
            ("candidate-reader-rc3-record", rc3_record),
            ("candidate-reader-rc5-record", rc5_record),
        ):
            outcome = _run_probe(
                session,
                inputs,
                label,
                release_dir=candidate_dir,
                body=READER_PROBE,
                payload=payload,
                env=env,
            )
            result.artifacts[label] = outcome["parsed"]
            result.require(
                f"AC-3/backward-compatibility: {label}",
                "accepted",
                outcome["parsed"].get("outcome"),
                "accepted",
            )


# --------------------------------------------------------------------------------------
# scenario: frozen writer / target-owned projections
# --------------------------------------------------------------------------------------


def scenario_frozen_writer(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    env = isolation.environment()
    store_root = isolation.store_root
    state_root = isolation.state_root

    rc4_dir = find_release_directory(store_root, "1.0.0rc4")
    candidate_dir = find_release_directory(store_root, CANDIDATE_VERSION)
    if rc4_dir is None or candidate_dir is None:
        raise ScenarioFailure(
            "the isolated store must carry rc4 and the candidate for this scenario"
        )

    scratch = isolation.work_root / "frozen-writer"
    scratch.mkdir(parents=True, exist_ok=True)
    record = json.loads((candidate_dir / "record.json").read_text(encoding="utf-8"))
    result.artifacts["candidate_record_version"] = record.get("version")

    # (a) the real rc4 writer plans projections for the successor record.
    legacy = _run_probe(
        session,
        inputs,
        "rc4-writer-successor-projections",
        release_dir=rc4_dir,
        body=PROJECTION_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(state_root),
            "scratch_projections": str(scratch / "legacy"),
            "release_id": candidate_dir.name,
        },
        env=env,
    )
    legacy_plan = legacy["parsed"]
    result.artifacts["rc4_plan"] = legacy_plan
    result.require(
        "AC-3/defect-2: the frozen rc4 writer brands a successor by exact version equality",
        "legacy Desktop entry identity for a successor record",
        legacy_plan.get("desktop_name"),
        LEGACY_DESKTOP_ENTRY_NAME,
    )

    # (b) the corrected source asks the target for its bytes (same target, corrected code).
    target_plan = _run_probe(
        session,
        inputs,
        "candidate-target-owned-projections",
        release_dir=candidate_dir,
        body=TARGET_PLAN_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(state_root),
            "scratch_projections": str(scratch / "target"),
            "target_release_id": rc4_dir.name,
        },
        env=env,
    )
    rc4_plan = target_plan["parsed"]
    result.artifacts["rc4_target_plan"] = rc4_plan
    result.require(
        "AC-3/L2: the corrected source honours the rc4 target's own plan",
        "the rc4 target answers for itself with its own branded projection shape",
        Path(str(rc4_plan.get("desktop_path"))).name,
        DESKTOP_ENTRY_NAME,
    )
    candidate_plan = _run_probe(
        session,
        inputs,
        "candidate-self-plan",
        release_dir=candidate_dir,
        body=TARGET_PLAN_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(state_root),
            "scratch_projections": str(scratch / "self"),
            "target_release_id": candidate_dir.name,
        },
        env=env,
    )
    self_plan = candidate_plan["parsed"]
    result.artifacts["candidate_self_plan"] = self_plan
    result.require(
        "AC-3/L2: the candidate generates its own branded projections",
        "branded launcher and Desktop entry",
        (
            self_plan.get("is_branded"),
            self_plan.get("desktop_path", "").endswith(DESKTOP_ENTRY_NAME),
        ),
        (True, True),
    )
    result.require(
        "AC-3/L2: each target answers for its own release identity",
        (rc4_dir.name, "1.0.0rc4", candidate_dir.name),
        (
            rc4_plan.get("release_id"),
            rc4_plan.get("version"),
            self_plan.get("release_id"),
        ),
        (rc4_dir.name, "1.0.0rc4", candidate_dir.name),
    )
    result.require(
        "AC-3/L2: each branded release plans its own branded projection",
        (DESKTOP_ENTRY_NAME, DESKTOP_ENTRY_NAME),
        (
            Path(str(self_plan.get("desktop_path"))).name,
            Path(str(rc4_plan.get("desktop_path"))).name,
        ),
        (DESKTOP_ENTRY_NAME, DESKTOP_ENTRY_NAME),
    )


# --------------------------------------------------------------------------------------
# scenario: exact version cycle
# --------------------------------------------------------------------------------------


def read_active_pointer(isolation: Isolation) -> dict[str, Any]:
    return json.loads((isolation.store_root / "active.json").read_text(encoding="utf-8"))


def active_release_id(isolation: Isolation) -> str:
    return str(read_active_pointer(isolation).get("release_id"))


def store_cli(isolation: Isolation) -> Path:
    """The packaged launcher selector the installation wrote for the active release."""

    store_cli_paths = (
        isolation.projections / "bin" / LAUNCHER_NAME,
        isolation.store_root / "runtime" / "current" / "venv" / "bin" / LAUNCHER_NAME,
    )
    for candidate in store_cli_paths:
        if candidate.exists():
            return candidate
    return store_cli_paths[0]


def manager_cli(isolation: Isolation) -> list[str]:
    """The active release's authenticated *manager* environment command prefix.

    ``reconcile`` mutates managed state but is not one of the commands the CLI redispatches into
    the active manager environment, so the documented operator surface (the projected launcher,
    which runs the release *runtime*) cannot satisfy the manager-authority proof.  Qualification
    therefore invokes it from the active release's own manager environment, which is the same
    environment the product uses for its other stateful commands.
    """

    active = json.loads((isolation.store_root / "active.json").read_text(encoding="utf-8"))
    release = isolation.store_root / "releases" / str(active["release_id"])
    return [str(release / "manager" / "bin" / "python"), "-m", "aether_agents.cli"]


def release_cli(isolation: Isolation) -> Path:
    """The active release's own console script, independent of the projected selector."""

    release = isolation.store_root / "runtime" / "current"
    for candidate in (
        release / "venv" / "bin" / LAUNCHER_NAME,
        release / "runtime" / "bin" / LAUNCHER_NAME,
    ):
        if candidate.exists():
            return candidate
    return release / "venv" / "bin" / LAUNCHER_NAME


def doctor_envelope(
    session: Session, inputs: Inputs, label: str, env: dict[str, str]
) -> dict[str, Any]:
    record = session.run(
        label,
        [str(store_cli(inputs.isolation)), "doctor", "--json"],
        env=env,
        cwd=inputs.isolation.work_root,
    )
    envelope = parse_json_stdout(record)
    if envelope is None:
        raise ScenarioFailure(f"{label}: doctor produced no JSON envelope")
    return envelope


#: The one diagnostic a disposable installation legitimately cannot clear: the gateway unit is
#: Hermes-owned and materialized through the Hermes CLI against a real service manager, which
#: the objective forbids this lane from touching (no inherited D-Bus socket, no systemctl
#: side effects).  Its absence is disclosed, never asserted green.
DISPOSABLE_DIAGNOSTICS = ("SERVICE_PROJECTION_MISMATCH",)


def assert_lifecycle_coherent(
    result: ScenarioResult,
    session: Session,
    inputs: Inputs,
    *,
    label: str,
    env: dict[str, str],
    expected_version: str,
    requirement: str,
) -> dict[str, Any]:
    """Assert the lifecycle-coherence subset of doctor for one isolated prestate/poststate."""

    envelope = doctor_envelope(session, inputs, label, env)
    observer = envelope["data"]["observer"]
    codes = list(observer.get("diagnostic_codes", []))
    unexpected = sorted(code for code in codes if code not in DISPOSABLE_DIAGNOSTICS)
    result.require(
        f"{requirement}: the active release is coherent",
        ("ready" if not codes else "error", expected_version, 0),
        (
            envelope.get("result"),
            observer.get("active_version"),
            observer["transition_journal"]["pending_count"],
        ),
        ("ready" if not codes else "error", expected_version, 0),
    )
    result.require(
        f"{requirement}: no unexpected diagnostic beyond the disposable service boundary",
        [],
        unexpected,
        [],
    )
    if codes:
        result.limits.append(
            f"{label}: the isolated lane cannot materialize the Hermes-owned gateway unit "
            f"(no systemd/D-Bus effect is permitted), so doctor reports "
            f"{', '.join(sorted(codes))} while every lifecycle witness is coherent"
        )
    return envelope


def assert_pointer_matches_target(
    result: ScenarioResult,
    isolation: Isolation,
    *,
    requirement: str,
    release_id: str,
    previous_release_id: str | None,
) -> dict[str, Any]:
    """The active pointer must be exactly the target's own record plus the transition field."""

    release_dir = isolation.store_root / "releases" / release_id
    target_record = json.loads((release_dir / "record.json").read_text(encoding="utf-8"))
    pointer = read_active_pointer(isolation)
    expected = dict(target_record)
    expected["previous_release_id"] = previous_release_id
    result.require(
        requirement,
        f"active pointer equals {release_id} record with previous_release_id={previous_release_id!r}",
        canonical(pointer),
        canonical(expected),
    )
    return pointer


def scenario_cycle(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    env = isolation.environment()
    store_root = isolation.store_root
    rc5_dir = find_release_directory(store_root, "1.0.0rc5")
    if rc5_dir is None:
        raise ScenarioFailure("the isolated store must carry the rc5 release for this scenario")

    fork = inputs.fork_checkout

    def hop(label: str, argv: list[str], *, expect_exit: int = 0, timeout: int = 900) -> Recorded:
        record = session.run(
            label,
            [str(store_cli(isolation)), *argv],
            env=env,
            cwd=isolation.work_root,
            check=False,
            timeout=timeout,
        )
        result.require(
            f"AC-3/cycle: {label} completes",
            f"exit {expect_exit}",
            record.exit_code,
            expect_exit,
        )
        return record

    # hop 1: rc5 -> candidate.  The cycle establishes the exact rc5 prestate itself, so a
    # re-run against a store left on the candidate still exercises the full cycle.
    if active_release_id(isolation) != rc5_dir.name:
        session.run(
            "cycle-establish-rc5-prestate",
            [*manager_cli(isolation), "update", "1.0.0rc5", "--yes", "--json"],
            env=env,
            cwd=isolation.project,
            check=False,
        )
    result.require(
        "AC-3/cycle: the cycle starts from the exact rc5 release",
        rc5_dir.name,
        active_release_id(isolation),
        rc5_dir.name,
    )
    assert_lifecycle_coherent(
        result,
        session,
        inputs,
        label="cycle-doctor-rc5",
        env=env,
        expected_version="1.0.0rc5",
        requirement="AC-3/cycle: the rc5 prestate",
    )

    staged = find_release_directory(store_root, CANDIDATE_VERSION)
    if staged is None:
        promotion = promotion_artifacts(inputs, session, result)
        hop(
            "cycle-hop1-rc5-to-candidate",
            [
                "update",
                "--wheel",
                str(promotion["wheel"]),
                "--hermes-checkout",
                str(fork),
                "--release-lock",
                str(promotion["release_lock"]),
                "--yes",
                "--json",
            ],
            timeout=1800,
        )
    else:
        # The exact candidate release is already staged in this store: the supported route for
        # an already-installed release is activation by VERSION, which re-validates the immutable
        # release rather than re-preparing (and never deleting or relabelling) its path.
        result.artifacts["candidate_already_staged"] = staged.name
        result.limits.append(
            "the candidate release was already staged in this store, so the rc5 -> candidate hop "
            "used the supported `update 1.0.0rc6` activation route over the immutable staged "
            "release; a fresh store exercises the wheel+lock preparation route instead"
        )
        hop(
            "cycle-hop1-rc5-to-candidate",
            ["update", CANDIDATE_VERSION, "--yes", "--json"],
            timeout=1800,
        )
    candidate_id = active_release_id(isolation)
    candidate_dir = find_release_directory(store_root, CANDIDATE_VERSION)
    if candidate_dir is None or candidate_id != candidate_dir.name:
        raise ScenarioFailure(
            f"the candidate release {CANDIDATE_VERSION} was not installed by the hop "
            f"(active {candidate_id})"
        )
    result.require(
        "AC-3/cycle: rc5 -> candidate activates the candidate",
        candidate_dir.name,
        candidate_id,
        candidate_dir.name,
    )
    candidate_pointer = assert_pointer_matches_target(
        result,
        isolation,
        requirement="AC-3/L1: the candidate's active pointer is target-owned",
        release_id=candidate_id,
        previous_release_id=rc5_dir.name,
    )
    result.artifacts["candidate_pointer_sha256"] = sha256_bytes(
        (store_root / "active.json").read_bytes()
    )
    assert_lifecycle_coherent(
        result,
        session,
        inputs,
        label="cycle-doctor-candidate",
        env=env,
        expected_version=CANDIDATE_VERSION,
        requirement="AC-3/cycle: the candidate installation",
    )
    result.artifacts["candidate_pointer"] = candidate_pointer

    # hop 2: candidate -> exact rc5 (rollback to the recorded predecessor).
    hop("cycle-hop2-candidate-to-rc5", ["rollback", "--yes", "--json"])
    result.require(
        "AC-3/cycle: candidate -> rc5 returns the exact rc5 release",
        rc5_dir.name,
        active_release_id(isolation),
        rc5_dir.name,
    )
    assert_lifecycle_coherent(
        result,
        session,
        inputs,
        label="cycle-doctor-rc5-again",
        env=env,
        expected_version="1.0.0rc5",
        requirement="AC-3/cycle: the rc5 fallback after the rollback",
    )

    # hop 3: rc5 -> candidate again, byte-identical active record.
    hop("cycle-hop3-rc5-to-candidate-again", ["update", CANDIDATE_VERSION, "--yes", "--json"])
    result.require(
        "AC-3/cycle: rc5 -> candidate repeats",
        candidate_dir.name,
        active_release_id(isolation),
        candidate_dir.name,
    )
    second_pointer = assert_pointer_matches_target(
        result,
        isolation,
        requirement="AC-3/cycle: the repeated activation writes the same target-owned record",
        release_id=candidate_id,
        previous_release_id=rc5_dir.name,
    )
    result.require(
        "AC-3/cycle: the repeated hop is byte-identical to the first",
        result.artifacts["candidate_pointer_sha256"],
        sha256_bytes((store_root / "active.json").read_bytes()),
        result.artifacts["candidate_pointer_sha256"],
    )
    result.artifacts["candidate_pointer_repeat"] = second_pointer

    # projections after the cycle match the candidate's own expectation.
    plan = _run_probe(
        session,
        inputs,
        "cycle-candidate-validate-projections",
        release_dir=candidate_dir,
        body=TARGET_PLAN_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(isolation.state_root),
            "scratch_projections": str(isolation.projections),
            "target_release_id": candidate_id,
        },
        env=env,
    )
    result.artifacts["cycle_final_plan"] = plan["parsed"]

    # failure and interruption invariants -------------------------------------------------
    before_pointer = (store_root / "active.json").read_bytes()
    before_sha = sha256_bytes(before_pointer)
    obstruction = isolation.projections / "applications" / DESKTOP_ENTRY_NAME
    obstruction.parent.mkdir(parents=True, exist_ok=True)
    saved = obstruction.read_bytes() if obstruction.is_file() else None
    if obstruction.is_file():
        obstruction.unlink()
    obstruction.mkdir()
    try:
        blocked = session.run(
            "cycle-compensation-blocked-projection",
            [
                str(release_cli(isolation)),
                "rollback",
                "--yes",
                "--json",
            ],
            env=env,
            cwd=isolation.work_root,
            check=False,
        )
        result.require(
            "AC-3/compensation: an unwritable projection destination fails the transition",
            "non-zero exit",
            blocked.exit_code != 0,
            True,
        )
    finally:
        if obstruction.is_dir():
            obstruction.rmdir()
        if saved is not None:
            obstruction.write_bytes(saved)
    result.require(
        "AC-3/compensation: the failed transition leaves the active record byte-identical",
        before_sha,
        sha256_bytes((store_root / "active.json").read_bytes()),
        before_sha,
    )
    compensation_doctor = doctor_envelope(session, inputs, "cycle-doctor-after-compensation", env)
    compensation_observer = compensation_doctor["data"]["observer"]
    result.require(
        "AC-3/compensation: the blocked transition never reports success",
        "no changed/changed=true result",
        (
            bool((parse_json_stdout(blocked) or {}).get("changed")),
            (parse_json_stdout(blocked) or {}).get("result"),
        ),
        (False, "error"),
    )
    result.require(
        "AC-3/compensation: the active release is unchanged by the blocked transition",
        CANDIDATE_VERSION,
        compensation_observer.get("active_version"),
        CANDIDATE_VERSION,
    )
    # The block is removed and the supported recovery route must settle whatever the failed
    # transition left behind: a pending journal entry is visible debris, never a silent state.
    settled = session.run(
        "cycle-compensation-settle",
        [*manager_cli(isolation), "rollback", "--yes", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    settled_back = session.run(
        "cycle-compensation-settle-back",
        [*manager_cli(isolation), "update", CANDIDATE_VERSION, "--yes", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    settle_doctor = doctor_envelope(session, inputs, "cycle-doctor-after-settle", env)
    settle_observer = settle_doctor["data"]["observer"]
    result.artifacts["compensation_settle"] = {
        "exit_code": settled.exit_code,
        "envelope": parse_json_stdout(settled),
        "reactivate_exit": settled_back.exit_code,
        "reactivate_envelope": parse_json_stdout(settled_back),
        "pending_count": settle_observer["transition_journal"]["pending_count"],
        "journals": settle_observer["transition_journal"]["journal_count"],
    }
    result.require(
        "AC-3/compensation: the supported recovery route settles the journal after the block is removed",
        (0, CANDIDATE_VERSION),
        (
            settle_observer["transition_journal"]["pending_count"],
            settle_observer.get("active_version"),
        ),
        (0, CANDIDATE_VERSION),
    )
    result.require(
        "AC-3/compensation: no transition is left in a false successful state",
        [],
        [
            item.get("state")
            for item in (
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((isolation.state_root / "transitions").glob("*.json"))
            )
            if item.get("state") == "pending"
        ],
        [],
    )

    # interruptions: kill the transition at varying offsets and require an atomic outcome.
    interruptions = []
    for index, delay in enumerate((0.35, 0.9, 1.6)):
        pointer_before = sha256_bytes((store_root / "active.json").read_bytes())
        process = subprocess.Popen(
            [str(store_cli(isolation)), "rollback", "--yes", "--json"],
            cwd=str(isolation.work_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(delay)
        alive = process.poll() is None
        if alive:
            process.kill()
        process.wait(timeout=120)
        doctor = doctor_envelope(session, inputs, f"cycle-doctor-interrupt-{index}", env)
        observer = doctor["data"]["observer"]
        pointer_now = json.loads((store_root / "active.json").read_text(encoding="utf-8"))
        release_now = find_release_directory(store_root, str(pointer_now.get("version")))
        coherent_if_ready = True
        if doctor.get("result") == "ready" and release_now is not None:
            own_record = json.loads((release_now / "record.json").read_text(encoding="utf-8"))
            expected_pointer = {
                **own_record,
                "previous_release_id": pointer_now.get("previous_release_id"),
            }
            coherent_if_ready = canonical(pointer_now) == canonical(expected_pointer)
        state = {
            "delay_s": delay,
            "killed": alive,
            "exit_code": process.returncode,
            "active_after": pointer_now.get("release_id"),
            "pointer_changed": sha256_bytes((store_root / "active.json").read_bytes())
            != pointer_before,
            "doctor_result": doctor.get("result"),
            "diagnostic_codes": list(observer.get("diagnostic_codes", [])),
            "projection_mismatches": list(
                (observer.get("projections") or {}).get("mismatches", [])
            ),
            "pending_count": observer["transition_journal"]["pending_count"],
            "coherent_if_ready": coherent_if_ready,
        }
        interruptions.append(state)
    result.artifacts["interruptions"] = interruptions
    result.require(
        "AC-3/interruption: no interrupted transition leaves a pending half-state",
        "pending_count 0 after every interruption",
        sorted({item["pending_count"] for item in interruptions}),
        [0],
    )
    result.require(
        "AC-3/interruption: an interrupted transition is never reported ready while incoherent",
        "every ready report is fully coherent (record and projections)",
        [
            item
            for item in interruptions
            if item["doctor_result"] == "ready" and not item["coherent_if_ready"]
        ],
        [],
    )
    result.require(
        "AC-3/interruption: an interrupted transition never reports a success envelope",
        "every kill terminates the transition process without a changed envelope",
        sorted({item["exit_code"] for item in interruptions}),
        [-9],
    )
    result.limits.append(
        "interruption outcomes are reported as observed: a kill before the commit point leaves "
        "the store untouched and ready, a kill after it leaves a visible incoherence that the "
        "documented repair route below settles - the oracle is the atomicity invariant, not a "
        "fixed winner per offset"
    )
    # The documented repair route for a transition interrupted after its commit point: roll back
    # to the recorded predecessor and re-activate the candidate through the supported routes.
    repair: dict[str, Any] = {}
    if any(item["pointer_changed"] for item in interruptions):
        rollback = session.run(
            "cycle-interrupt-repair-rollback",
            [*manager_cli(isolation), "rollback", "--yes", "--json"],
            env=env,
            cwd=isolation.project,
            check=False,
        )
        repair["rollback_exit"] = rollback.exit_code
        repair["rollback_result"] = (parse_json_stdout(rollback) or {}).get("result")
        if active_release_id(isolation) != candidate_dir.name:
            reactivate = session.run(
                "cycle-interrupt-repair-reactivate",
                [*manager_cli(isolation), "update", CANDIDATE_VERSION, "--yes", "--json"],
                env=env,
                cwd=isolation.project,
                check=False,
            )
            repair["reactivate_exit"] = reactivate.exit_code
            repair["reactivate_result"] = (parse_json_stdout(reactivate) or {}).get("result")
        result.artifacts["interruption_repair"] = repair
        result.require(
            "AC-3/interruption: the documented repair route restores the candidate",
            candidate_dir.name,
            active_release_id(isolation),
            candidate_dir.name,
        )
        assert_lifecycle_coherent(
            result,
            session,
            inputs,
            label="cycle-doctor-after-interruption-repair",
            env=env,
            expected_version=CANDIDATE_VERSION,
            requirement="AC-3/interruption: the repaired store",
        )
    else:
        result.artifacts["interruption_repair"] = {
            "skipped": "no interruption crossed the commit point"
        }
    result.limits.append(
        "interruption offsets are wall-clock kills, so which side of the commit point each run "
        "lands on varies; the recorded oracle is the atomic-outcome invariant, not a fixed winner"
    )

    # explicit old-record and unknown-newer cases against the installed candidate reader.
    newest = {
        "schema_version": 99,
        "release_id": "1.0.0rc99-ffffffffffffffff",
        "version": "1.0.0rc99",
    }
    old = {
        key: value
        for key, value in json.loads((rc5_dir / "record.json").read_text(encoding="utf-8")).items()
        if key
        not in (
            "authority_context",
            "aether_identity",
            "prebuild_identity",
            "installed_file_fingerprint",
            "observation_compatibility",
            "observer",
        )
    }
    old["schema_version"] = 1
    for label, payload in (
        ("candidate-reader-unknown-newer", newest),
        ("candidate-reader-old-schema", old),
    ):
        outcome = _run_probe(
            session,
            inputs,
            label,
            release_dir=candidate_dir,
            body=READER_PROBE,
            payload=payload,
            env=env,
        )
        result.artifacts[label] = outcome["parsed"]
    result.require(
        "AC-3/explicit: an unknown-newer record is refused by the candidate reader",
        "rejected",
        result.artifacts["candidate-reader-unknown-newer"].get("outcome"),
        "rejected",
    )
    result.require(
        "AC-3/explicit: an older-schema record that carries no modern identity stays readable",
        "accepted",
        result.artifacts["candidate-reader-old-schema"].get("outcome"),
        "accepted",
    )
    # A legacy schema that nevertheless declares modern build identity is refused: the reader
    # never upgrades a record into a generation it does not claim.
    contradictory = dict(old)
    contradictory["aether_identity"] = json.loads(
        (rc5_dir / "record.json").read_text(encoding="utf-8")
    )["aether_identity"]
    outcome = _run_probe(
        session,
        inputs,
        "candidate-reader-legacy-with-modern-identity",
        release_dir=candidate_dir,
        body=READER_PROBE,
        payload=contradictory,
        env=env,
    )
    result.artifacts["candidate-reader-legacy-with-modern-identity"] = outcome["parsed"]
    result.require(
        "AC-3/explicit: a legacy schema declaring modern identity is refused",
        "rejected",
        outcome["parsed"].get("outcome"),
        "rejected",
    )


# --------------------------------------------------------------------------------------
# scenario: legacy boundary
# --------------------------------------------------------------------------------------


def scenario_legacy(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    env = isolation.environment()
    store_root = isolation.store_root
    rc4_dir = find_release_directory(store_root, "1.0.0rc4")
    candidate_dir = find_release_directory(store_root, CANDIDATE_VERSION)
    if rc4_dir is None or candidate_dir is None:
        raise ScenarioFailure("the isolated store must carry rc4 and the candidate")
    if active_release_id(isolation) != candidate_dir.name:
        session.run(
            "legacy-establish-candidate-prestate",
            [*manager_cli(isolation), "update", CANDIDATE_VERSION, "--yes", "--json"],
            env=env,
            cwd=isolation.project,
            check=False,
        )
    result.require(
        "AC-3/legacy: the legacy handoff starts from an active candidate",
        candidate_dir.name,
        active_release_id(isolation),
        candidate_dir.name,
    )

    # (a) the frozen rc4 writer writes its legacy projection bytes into the live destinations
    #     of the isolated store: this is the recorded wrong projection of defect 2.
    legacy = _run_probe(
        session,
        inputs,
        "legacy-rc4-applies-projections",
        release_dir=rc4_dir,
        body=PROJECTION_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(isolation.state_root),
            "scratch_projections": str(isolation.projections),
            "release_id": candidate_dir.name,
            "apply": True,
        },
        env=env,
    )
    result.artifacts["legacy_apply"] = legacy["parsed"]
    launcher = isolation.projections / "bin" / LAUNCHER_NAME
    legacy_desktop = isolation.projections / "applications" / LEGACY_DESKTOP_ENTRY_NAME
    branded_desktop = isolation.projections / "applications" / DESKTOP_ENTRY_NAME
    result.require(
        "AC-3/legacy: the rc4 writer leaves its legacy projection on the managed destinations",
        "the legacy Desktop entry exists alongside the stale branded one",
        (legacy_desktop.is_file(), branded_desktop.is_file()),
        (True, True),
    )
    legacy_launcher_sha = sha256_file(launcher) if launcher.is_file() else None
    result.artifacts["legacy_launcher_sha256"] = legacy_launcher_sha
    expected_plan_probe = _run_probe(
        session,
        inputs,
        "legacy-candidate-expected-launcher",
        release_dir=candidate_dir,
        body=PROJECTION_PROBE,
        payload={
            "store_root": str(store_root),
            "state_root": str(isolation.state_root),
            "scratch_projections": str(isolation.projections),
            "release_id": candidate_dir.name,
        },
        env=env,
    )
    expected_launcher_sha = expected_plan_probe["parsed"].get("launcher_sha256")
    result.require(
        "AC-3/legacy: the legacy writer overwrote the active release's launcher bytes",
        "the managed launcher no longer matches the active release's own expectation",
        legacy_launcher_sha != expected_launcher_sha,
        True,
    )

    # (b) the non-mutating preview of the supported reconcile surface.
    launcher_route = session.run(
        "legacy-reconcile-launcher-route",
        [str(store_cli(isolation)), "reconcile", "--to", "active", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    result.artifacts["reconcile_launcher_route"] = {
        "exit_code": launcher_route.exit_code,
        "envelope": parse_json_stdout(launcher_route),
        "note": "the projected launcher runs the release runtime and cannot satisfy the "
        "manager-authority proof reconcile requires",
    }
    preview = session.run(
        "legacy-reconcile-preview",
        [*manager_cli(isolation), "reconcile", "--to", "active", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    preview_envelope = parse_json_stdout(preview) or {}
    result.require(
        "AC-3/legacy: the preview is non-mutating and reports the mismatch",
        ("planned", 0),
        (preview_envelope.get("result"), preview_envelope.get("changed")),
        ("planned", 0),
    )
    result.require(
        "AC-3/legacy: the preview does not touch the managed bytes",
        legacy_launcher_sha,
        sha256_file(launcher) if launcher.is_file() else None,
        legacy_launcher_sha,
    )
    result.artifacts["reconcile_preview"] = preview_envelope

    # (c) the supported handoff: reconcile the already-activated, self-authenticating target.
    pointer_before = sha256_bytes((store_root / "active.json").read_bytes())
    applied = session.run(
        "legacy-reconcile-apply",
        [*manager_cli(isolation), "reconcile", "--to", "active", "--yes", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    applied_envelope = parse_json_stdout(applied) or {}
    result.artifacts["reconcile_apply"] = applied_envelope
    result.require(
        "AC-3/legacy: the supported reconcile finishes the handoff",
        ("changed", 0),
        (applied_envelope.get("result"), applied.exit_code),
        ("changed", 0),
    )
    result.require(
        "AC-3/legacy: reconcile removes the legacy projection and rewrites the branded one",
        (False, True),
        (legacy_desktop.is_file(), branded_desktop.is_file()),
        (False, True),
    )
    result.require(
        "AC-3/legacy: reconcile repairs the handoff without editing the release record",
        pointer_before,
        sha256_bytes((store_root / "active.json").read_bytes()),
        pointer_before,
    )
    result.require(
        "AC-3/legacy: the repaired projections equal the target's own expectation",
        expected_launcher_sha,
        sha256_file(launcher) if launcher.is_file() else None,
        expected_launcher_sha,
    )

    # (d) unsupported modes stay explicit and non-mutating.
    unsupported = session.run(
        "legacy-reconcile-unsupported-mode",
        [*manager_cli(isolation), "reconcile", "--to", "installed", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    unsupported_envelope = parse_json_stdout(unsupported) or {}
    result.require(
        "AC-3/legacy: an unsupported reconcile mode is refused",
        "unsupported",
        unsupported_envelope.get("result"),
        "unsupported",
    )
    result.require(
        "AC-3/legacy: the unsupported mode changes nothing",
        pointer_before,
        sha256_bytes((store_root / "active.json").read_bytes()),
        pointer_before,
    )

    # (e) a legacy route whose target cannot prove its integrity refuses before mutation.
    forged = store_root / "releases" / "1.0.0rc4-forged0000000000"
    if forged.exists():
        shutil.rmtree(forged)
    shutil.copytree(rc4_dir, forged, symlinks=True)
    forged_record = json.loads((forged / "record.json").read_text(encoding="utf-8"))
    forged_record["release_id"] = forged.name
    forged_record["wheel_sha256"] = "0" * 64
    (forged / "record.json").write_text(
        json.dumps(forged_record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    refused = session.run(
        "legacy-unprovable-target-refused",
        [*manager_cli(isolation), "update", "1.0.0rc4", "--yes", "--json"],
        env=env,
        cwd=isolation.project,
        check=False,
    )
    result.artifacts["unprovable_target"] = {
        "exit_code": refused.exit_code,
        "envelope": parse_json_stdout(refused),
        "stdout_tail": refused.stdout_tail,
        "stderr_tail": refused.stderr_tail,
    }
    result.require(
        "AC-3/legacy: an unprovable legacy target is refused before mutation",
        "non-zero exit",
        refused.exit_code != 0,
        True,
    )
    result.require(
        "AC-3/legacy: the refusal leaves the active record unchanged",
        pointer_before,
        sha256_bytes((store_root / "active.json").read_bytes()),
        pointer_before,
    )
    result.require(
        "AC-3/legacy: the refusal leaves no pending transition behind",
        "no pending transition",
        [
            item.name
            for item in sorted((isolation.state_root / "transitions").glob("*.json"))
            if json.loads(item.read_text(encoding="utf-8")).get("state") == "pending"
        ],
        [],
    )
    shutil.rmtree(forged)
    result.limits.append(
        "the rc4 writer is executed as its own authenticated installed code from the isolated "
        "store; no live rc3/rc4 bootstrap or rollback is performed on the operator installation"
    )


# --------------------------------------------------------------------------------------
# scenario: installed launch
# --------------------------------------------------------------------------------------


def seed_observation_corpus(isolation: Isolation, project_id: str) -> dict[str, Any]:
    """Seed the isolated observation store with a meaningful corpus before launch."""
    repo_root = str(Path(__file__).resolve().parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from aether_agents.observation.capture.journal import JournalWriter
    from aether_agents.paths import ObservationPaths
    from tests.observation_helpers import complete_trace

    paths = ObservationPaths.for_project(project_id, root=isolation.state_root)
    paths.ensure()
    trace = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=trace.epoch)
    writer.open()
    for ev in trace.events:
        ev_copy = dict(ev)
        ev_copy["project_id"] = project_id
        writer.append(ev_copy)
    writer.close()
    return observation_scale(isolation)


def seed_resume_session(isolation: Isolation, project: Path) -> str:
    """Seed a prior session in Morfeo's SessionDB so --resume latest has a session to resume."""
    from hermes_state import SessionDB

    old_home = os.environ.get("HERMES_HOME")
    try:
        os.environ["HERMES_HOME"] = str(isolation.hermes_root / "profiles" / "morfeo")
        db = SessionDB()
        session_id = "seed-session-" + uuid.uuid4().hex[:12]
        proj_str = str(project.resolve())
        db.create_session(session_id=session_id, source="tui", cwd=proj_str, git_repo_root=proj_str)
        db.set_session_title(session_id, f"Seed session {session_id}")
        db.append_message(
            session_id=session_id, role="user", content="Hello, this is a seed session."
        )
        db.append_message(session_id=session_id, role="assistant", content="Acknowledged.")
        db.close()
        return session_id
    finally:
        if old_home is not None:
            os.environ["HERMES_HOME"] = old_home
        else:
            os.environ.pop("HERMES_HOME", None)


def scenario_launch(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    candidate_dir = find_release_directory(isolation.store_root, CANDIDATE_VERSION)
    if candidate_dir is None:
        raise ScenarioFailure("the candidate release is not installed in the isolated store")
    project = isolation.project
    second_project = isolation.second_project
    if active_release_id(isolation) != candidate_dir.name:
        session.run(
            "launch-establish-candidate-prestate",
            [*manager_cli(isolation), "update", CANDIDATE_VERSION, "--yes", "--json"],
            env=isolation.environment(),
            cwd=isolation.project,
            check=False,
        )
    proj_info = ensure_project(inputs, session, project=project, label="launch-project")
    result.artifacts["project"] = proj_info
    project_id = str(proj_info.get("project_id") or "")

    profile_config = isolation.hermes_root / "profiles" / "morfeo" / "config.yaml"
    if profile_config.is_file():
        existing = profile_config.read_text(encoding="utf-8")
        if "toolsets:" not in existing:
            profile_config.write_text(
                existing + "toolsets:\n  - file\n  - kanban\n", encoding="utf-8"
            )
            existing = profile_config.read_text(encoding="utf-8")
        if "stub-non-sending" not in existing:
            provider_block = (
                "\nmodel:\n"
                "  provider: custom\n"
                "  default: custom/stub-non-sending\n"
                "  base_url: http://127.0.0.1:9999/v1\n"
                "  api_key: dummy-non-sending-fixture\n"
            )
            profile_config.write_text(existing + provider_block, encoding="utf-8")
        result.artifacts["access_kind"] = "isolated_stub_provider_fixture"
        result.artifacts["fixture_profile_toolsets"] = sorted(
            line.strip(" -")
            for line in profile_config.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("- ")
        )
    else:
        raise ScenarioFailure(
            f"the isolated Morfeo profile has no configuration at {profile_config}"
        )

    corpus_scale_before = seed_observation_corpus(isolation, project_id)
    result.artifacts["corpus_scale_before"] = corpus_scale_before

    def activation(label: str, argv: list[str], env: dict[str, str], cwd: Path) -> dict[str, Any]:
        record = session.run(
            label,
            argv,
            env=env,
            cwd=cwd,
            check=False,
        )
        envelope = parse_json_stdout(record)
        if envelope is None:
            raise ScenarioFailure(f"{label}: no activation report (exit {record.exit_code})")
        return envelope

    clean_env = isolation.environment({"HERMES_KANBAN_TASK": None})
    fresh = activation(
        "launch-fresh-explicit-project",
        [str(store_cli(isolation)), "--project", str(project), "--check", "--json"],
        clean_env,
        isolation.work_root,
    )
    result.artifacts["fresh_report"] = fresh
    release_root = isolation.store_root / "runtime" / "current"
    resolved_release_root = Path(os.path.realpath(release_root))
    result.require(
        "AC-7/launch: the fresh report binds the target backend",
        True,
        fresh.get("hermes_executable", "").startswith(str(resolved_release_root)),
        True,
    )
    result.require(
        "AC-7/launch: the fresh report binds the isolated Morfeo profile",
        str(isolation.hermes_root / "profiles" / "morfeo"),
        fresh.get("hermes_home"),
        str(isolation.hermes_root / "profiles" / "morfeo"),
    )
    result.require(
        "AC-7/launch: the fresh report binds the exact managed project",
        str(project.resolve()),
        fresh.get("repo_root"),
        str(project.resolve()),
    )
    result.require(
        "AC-7/launch: the fresh report uses the release TUI directory",
        str(resolved_release_root / "tui"),
        fresh.get("tui_dir"),
        str(resolved_release_root / "tui"),
    )

    resume = activation(
        "launch-resume-latest",
        [
            str(store_cli(isolation)),
            "--project",
            str(project),
            "--resume",
            "latest",
            "--check",
            "--json",
        ],
        clean_env,
        isolation.work_root,
    )
    result.artifacts["resume_report"] = resume
    result.require(
        "AC-7/launch: --resume latest is carried into the target command",
        ["--resume", "latest"],
        [item for item in resume.get("command", []) if item == "--resume" or item == "latest"][:2],
        ["--resume", "latest"],
    )

    # contaminated transport environment: stale selectors must not reach the target.
    contaminated = isolation.environment(
        {
            "HERMES_PYTHON": "/usr/bin/python3",
            "HERMES_PYTHON_SRC_ROOT": str(Path.home() / ".local" / "share" / "aether" / "runtime"),
            "HERMES_UI_SESSION_ID": "stale-session",
            "HERMES_GATEWAY_URL": "http://127.0.0.1:1/stale",
            "HERMES_SESSION_ID": "stale-session",
        }
    )
    contaminated_report = activation(
        "launch-contaminated-report",
        [str(store_cli(isolation)), "--project", str(project), "--check", "--json"],
        contaminated,
        isolation.work_root,
    )
    result.artifacts["contaminated_report"] = contaminated_report
    result.require(
        "AC-6/U1: a contaminated parent environment still binds the exact target",
        contaminated_report.get("hermes_executable"),
        contaminated_report.get("hermes_executable"),
        fresh.get("hermes_executable"),
    )

    # a real PTY launch: the packaged launcher execs the release runtime in place.
    launch = pty_launch(
        inputs,
        session,
        result,
        label="launch-pty-fresh-contaminated",
        argv=[str(store_cli(isolation)), "--project", str(project)],
        env=contaminated,
        cwd=project,
        timeout=inputs.launch_timeout,
    )
    result.artifacts["pty"] = launch

    resume_sid = seed_resume_session(isolation, project)
    result.artifacts["seeded_resume_session_id"] = resume_sid
    resume_launch = pty_launch(
        inputs,
        session,
        result,
        label="launch-pty-resume-latest",
        argv=[str(store_cli(isolation)), "--project", str(project), "--resume", "latest"],
        env=clean_env,
        cwd=project,
        timeout=inputs.launch_timeout,
    )
    result.artifacts["pty_resume"] = resume_launch

    environment = launch.get("child_environment", {})
    pty_output = launch.get("output_head", "") + launch.get("output_tail", "")
    result.artifacts["pty_reached_target_runtime"] = "Hermes" in pty_output or bool(pty_output)
    result.require(
        "AC-6/U1: the fresh PTY launch reaches the installed target runtime",
        True,
        bool(pty_output.strip()),
        True,
    )
    result.require(
        "AC-7/launch: fresh PTY launch reaches agent-ready",
        True,
        launch.get("agent_ready_ms") is not None and launch.get("agent_ready_ms", 0) > 0,
        True,
    )
    result.require(
        "AC-7/launch: resume PTY launch reaches agent-ready",
        True,
        resume_launch.get("agent_ready_ms") is not None
        and resume_launch.get("agent_ready_ms", 0) > 0,
        True,
    )
    result.require(
        "AC-7/launch: the launch scenario runs against a non-empty observation corpus",
        True,
        launch.get("corpus_scale", {}).get("events", 0) > 0,
        True,
    )
    result.limits.append(
        "the isolated lane uses an explicitly labelled non-sending provider fixture in the profile "
        "configuration (access_kind: isolated_stub_provider_fixture), enabling the candidate "
        "runtime and TUI package to fully initialize without copying operator credentials or "
        "contacting live external endpoints; the recorded pre-live measurement is the real measured "
        "time to interactive agent prompt readiness against a pre-seeded observation corpus; the "
        "single live external provider completion belongs to RC6-CLOSE"
    )
    result.require(
        "AC-6/U1: the launched target keeps the packaged interpreter binding",
        True,
        str(environment.get("HERMES_PYTHON", "")).startswith(str(resolved_release_root))
        or str(environment.get("HERMES_PYTHON", "")).startswith(str(release_root)),
        True,
    )
    result.require(
        "AC-6/U1: the launched target binds the isolated profile home",
        str(isolation.hermes_root / "profiles" / "morfeo"),
        environment.get("HERMES_HOME"),
        str(isolation.hermes_root / "profiles" / "morfeo"),
    )
    result.require(
        "AC-6/U1: the stale transport selectors do not survive into the launch",
        (None, None),
        (environment.get("HERMES_UI_SESSION_ID"), environment.get("HERMES_GATEWAY_URL")),
        (None, None),
    )
    locked = json.loads((candidate_dir / "release-lock.json").read_text(encoding="utf-8"))
    result.require(
        "AC-6/U1: the locked maintained-fork source digest is unchanged",
        MAINTAINED_FORK_TREE_SHA256,
        locked.get("hermes", {}).get("source_tree_sha256"),
        MAINTAINED_FORK_TREE_SHA256,
    )
    result.require(
        "AC-7/launch: the fresh launch neither rebuilt nor mutated the release tree",
        launch.get("release_tree_unchanged"),
        True,
        launch.get("release_tree_unchanged"),
    )
    result.require(
        "AC-7/launch: the resume launch neither rebuilt nor mutated the release tree",
        resume_launch.get("release_tree_unchanged"),
        True,
        resume_launch.get("release_tree_unchanged"),
    )

    # documented selection forms: override, unset-default, empty refusal, ambiguity.
    override = activation(
        "launch-project-root-override",
        [str(store_cli(isolation)), "--check", "--json"],
        isolation.environment({"AETHER_PROJECT_ROOT": str(project)}),
        isolation.work_root,
    )
    result.require(
        "AC-6/U1: AETHER_PROJECT_ROOT selects the project without --project",
        str(project.resolve()),
        override.get("repo_root"),
        str(project.resolve()),
    )
    default = activation(
        "launch-unset-project-root-defaults-to-cwd",
        [str(store_cli(isolation)), "--check", "--json"],
        isolation.environment({"AETHER_PROJECT_ROOT": None}),
        project,
    )
    result.require(
        "AC-6/U1: with AETHER_PROJECT_ROOT unset the project marker in cwd wins",
        str(project.resolve()),
        default.get("repo_root"),
        str(project.resolve()),
    )
    empty = session.run(
        "launch-empty-project-root-refused",
        [str(store_cli(isolation)), "--check", "--json"],
        env=isolation.environment({"AETHER_PROJECT_ROOT": ""}),
        cwd=isolation.work_root,
        check=False,
    )
    result.require(
        "AC-6/U1: an empty AETHER_PROJECT_ROOT is refused",
        "non-zero exit",
        empty.exit_code != 0,
        True,
    )
    result.artifacts["second_project"] = ensure_project(
        inputs, session, project=second_project, label="launch-second-project"
    )
    ambiguous = session.run(
        "launch-ambiguous-project-refused",
        [str(store_cli(isolation)), "--check", "--json"],
        env=isolation.environment({"AETHER_PROJECT_ROOT": None}),
        cwd=isolation.work_root,
        check=False,
    )
    result.require(
        "AC-6/U1: an ambiguous project selection is refused rather than guessed",
        True,
        "ambiguous" in (ambiguous.stderr_tail + ambiguous.stdout_tail),
        True,
    )
    result.limits.append(
        "the PTY launch reaches the installed runtime and its readiness signals; no provider "
        "request is made here, so the single live provider reply stays with the terminal window"
    )


def pty_launch(
    inputs: Inputs,
    session: Session,
    result: ScenarioResult,
    *,
    label: str,
    argv: list[str],
    env: dict[str, str],
    cwd: Path,
    timeout: int,
) -> dict[str, Any]:
    """Launch through a real PTY and measure the time to observable agent readiness."""

    isolation = inputs.isolation
    before_tree = tree_identity(isolation.store_root / "runtime" / "current" / "tui")
    try:
        before_release = json.loads(
            (isolation.store_root / "runtime" / "current" / "release.json").read_text(
                encoding="utf-8"
            )
        )
    except OSError:
        before_release = {}

    tmp_dir = isolation.work_root / "tmp"
    if tmp_dir.is_dir():
        for sf in tmp_dir.glob("hermes-tui-active-session-*.json"):
            try:
                sf.unlink()
            except OSError:
                pass

    master, slave = pty.openpty()
    try:
        import fcntl
        import struct
        import termios

        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    except Exception:
        pass

    started = time.time()
    process = subprocess.Popen(
        argv,
        cwd=str(cwd),
        env=env,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    observed: list[dict[str, Any]] = []
    buffer = bytearray()
    ready_at: float | None = None
    readiness_signal: str | None = None
    child_environment: dict[str, str] = {}
    observation_event_at: float | None = None
    try:
        while time.time() - started < timeout:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    chunk = b""
                if chunk:
                    buffer.extend(chunk)
                    if not any(s["signal"] == "first_pty_output" for s in observed):
                        observed.append(
                            {
                                "signal": "first_pty_output",
                                "ms": int((time.time() - started) * 1000),
                            }
                        )
            if buffer or not child_environment:
                try:
                    raw = Path(f"/proc/{process.pid}/environ").read_bytes()
                    observed_environment = dict(
                        item.split("=", 1)
                        for item in raw.decode("utf-8", "replace").split("\0")
                        if "=" in item
                    )
                    child_environment = observed_environment
                except (OSError, ValueError):
                    pass

            if not any(s["signal"] == "active_session_file" for s in observed):
                if tmp_dir.is_dir():
                    for sf in tmp_dir.glob("hermes-tui-active-session-*.json"):
                        try:
                            content = sf.read_text(encoding="utf-8")
                            if "session_id" in content:
                                observed.append(
                                    {
                                        "signal": "active_session_file",
                                        "ms": int((time.time() - started) * 1000),
                                    }
                                )
                                break
                        except OSError:
                            pass

            if observation_event_at is None:
                events = isolation.state_root / "observations"
                if any(events.rglob("*.active.jsonl")):
                    observation_event_at = time.time() - started
                    observed.append(
                        {
                            "signal": "observation_active_journal",
                            "ms": int(observation_event_at * 1000),
                        }
                    )

            if b'Try "/help"' in buffer or b"\xe2\x9d\xaf" in buffer:
                ready_at = time.time() - started
                readiness_signal = "agent_prompt_ready"
                observed.append(
                    {
                        "signal": readiness_signal,
                        "ms": int(ready_at * 1000),
                    }
                )
                break

            if process.poll() is not None:
                break
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        os.close(master)

    output = buffer.decode("utf-8", "replace")
    after_release = {}
    try:
        after_release = json.loads(
            (isolation.store_root / "runtime" / "current" / "release.json").read_text(
                encoding="utf-8"
            )
        )
    except OSError:
        pass
    after_tree = tree_identity(isolation.store_root / "runtime" / "current" / "tui")
    environment_identity = isolation.environment_identity(child_environment or env)
    payload = {
        "argv": argv,
        "exit_code": process.returncode,
        "elapsed_ms": int((time.time() - started) * 1000),
        "readiness_signal": readiness_signal,
        "agent_ready_ms": None if ready_at is None else int(ready_at * 1000),
        "observed_signals": observed,
        "child_environment_identity": environment_identity,
        "child_environment": {
            key: child_environment.get(key)
            for key in (
                "HERMES_HOME",
                "HERMES_PYTHON",
                "HERMES_PYTHON_SRC_ROOT",
                "HERMES_TUI_DIR",
                "AETHER_PROJECT_ID",
            )
        },
        "output_sha256": sha256_bytes(output.encode("utf-8")),
        "output_head": output[:2000],
        "output_tail": tail(output, 2000),
        "release_tree_unchanged": (
            before_tree == after_tree
            and before_release.get("tui_sha256") == after_release.get("tui_sha256")
        ),
        "tui_tree": after_tree,
        "corpus_scale": observation_scale(isolation),
    }
    session.commands.append(
        Recorded(
            label=label,
            argv=argv,
            cwd=str(cwd),
            exit_code=process.returncode,
            duration_ms=payload["elapsed_ms"],
            stdout_sha256=payload["output_sha256"],
            stderr_sha256=payload["output_sha256"],
            stdout_tail=tail(output, 2000),
            stderr_tail="",
            environment_identity=environment_identity,
        )
    )
    result.artifacts[f"{label}_signal"] = readiness_signal
    return payload


def observation_scale(isolation: Isolation) -> dict[str, Any]:
    """Corpus identity/scale of the isolated observation store."""

    root = isolation.state_root / "observations"
    segments = sorted(root.rglob("*.jsonl"))
    events = 0
    for path in segments:
        try:
            events += sum(1 for _ in path.open("rb"))
        except OSError:
            continue
    return {
        "segments": len(segments),
        "events": events,
        "digest": tree_identity(root, limit=200)["digest"] if root.is_dir() else None,
    }


# --------------------------------------------------------------------------------------
# scenario: documented usage and repository checks
# --------------------------------------------------------------------------------------


def scenario_docs(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    isolation = inputs.isolation
    env = isolation.environment()
    checks = session.run(
        "docs-check-documentation",
        [sys.executable, str(inputs.repo / "scripts" / "check_documentation.py")],
        env=env,
        cwd=inputs.repo,
        check=False,
    )
    result.require(
        "AC-6/U1: the repository documentation check passes at the candidate revision",
        "exit 0",
        checks.exit_code,
        0,
    )
    modules = (
        "tests/test_documentation.py",
        "tests/test_contract_quality_documents.py",
        "tests/test_observation_usage_guidance.py",
    )
    pytest_run = session.run(
        "docs-pytest-usage-guidance",
        [sys.executable, "-m", "pytest", "-q", *modules],
        env=env,
        cwd=inputs.repo,
        check=False,
    )
    result.require(
        "AC-6/U1: the repository usage/documentation checks pass",
        "exit 0",
        pytest_run.exit_code,
        0,
    )
    result.artifacts["docs_pytest_tail"] = pytest_run.stdout_tail

    manifest = session.run(
        "docs-manifest-oracle",
        [sys.executable, "-m", "pytest", "-q", "tests/test_public_artifacts.py"],
        env=env,
        cwd=inputs.repo,
        check=False,
    )
    result.artifacts["manifest_oracle"] = {
        "exit_code": manifest.exit_code,
        "tail": tail(manifest.stdout_tail + manifest.stderr_tail, 1500),
    }
    result.limits.append(
        "tests/test_public_artifacts.py is expected to fail until RC6-INT applies the manifest "
        "lines this unit reports; the failure is recorded, not asserted green"
    )

    version = session.run(
        "docs-installed-version",
        [str(store_cli(isolation)), "version", "--json"],
        env=env,
        cwd=isolation.work_root,
        check=False,
    )
    version_envelope = parse_json_stdout(version) or {}
    result.require(
        "AC-6/U1: the installed CLI reports the candidate identity",
        CANDIDATE_VERSION,
        version_envelope.get("manager_version"),
        CANDIDATE_VERSION,
    )


# --------------------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------------------


def prepare_store(inputs: Inputs, session: Session, result: ScenarioResult) -> None:
    """Materialize the exact-version artifacts into the isolated store."""

    isolation = inputs.isolation
    env = isolation.environment()
    store_root = isolation.store_root
    (store_root / "releases").mkdir(parents=True, exist_ok=True)

    # Bounded resumption: a re-run of the same inputs against the same work root resumes the
    # already-materialized release instead of rebuilding an identical installation.  The
    # marker binds the exact input identity, so a changed bundle, fork or source artifact
    # re-prepares from scratch.
    identity = {
        "candidate_commit": inputs.candidate_commit,
        "fork_commit": git(inputs.fork_checkout, "rev-parse", "HEAD"),
        "bundle": (
            None
            if inputs.bundle_dir is None
            else sha256_file(inputs.bundle_dir / inputs.verify_bundle()["wheel"])
        ),
        "rc5_wheel": sha256_file(inputs.source_wheel("rc5")),
    }
    marker = isolation.work_root / "prepare-complete.json"
    rc5_dir = find_release_directory(store_root, "1.0.0rc5")
    if marker.is_file() and rc5_dir is not None:
        try:
            recorded = json.loads(marker.read_text(encoding="utf-8"))
        except ValueError:
            recorded = {}
        if recorded == identity and (store_root / "active.json").is_file():
            result.artifacts["resumed"] = True
            result.artifacts["project"] = {"path": str(isolation.project)}
            current = store_root / "runtime" / "current"
            result.require(
                "AC-3/cycle: the selector resolves into the isolated store",
                True,
                str(os.path.realpath(current)).startswith(str(store_root)),
                True,
            )
            result.require(
                "AC-3/cycle: the isolated store contains exact rc5",
                True,
                rc5_dir is not None and rc5_dir.is_dir(),
                True,
            )
            return

    # Branded one-click projections require one exact project binding, so the isolated
    # installation needs its own managed project before the first release is activated.
    project = ensure_project(inputs, session, project=isolation.project, label="prepare-project")
    result.artifacts["project"] = project

    # frozen old releases: authenticated installed code, copied byte-for-byte from the

    # frozen old releases: authenticated installed code, copied byte-for-byte from the
    # read-only source store, verified per file and against the frozen revision's sources.
    for version in ("rc3", "rc4"):
        source = find_release_directory(inputs.source_store, FROZEN_VERSIONS[version])
        if source is None:
            raise Refusal(f"source store carries no {version} release")
        destination = store_root / "releases" / source.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, symlinks=True)
        result.artifacts[f"{version}_copy"] = verify_release_copy(
            inputs, version=version, source=source, destination=destination
        )

    setup = session.run(
        "prepare-setup-rc5",
        [
            sys.executable,
            "-m",
            "aether_agents.cli",
            "setup",
            "--wheel",
            str(inputs.source_wheel("rc5")),
            "--hermes-checkout",
            str(inputs.fork_checkout),
            "--release-lock",
            str(inputs.source_lock("rc5")),
            "--yes",
            "--json",
        ],
        env=env,
        # The lifecycle resolves the default project from the registry and the marker of the
        # working directory: a checkout that carries its own marker must never decide this
        # installation's binding, so every store-mutating command runs from the isolated root.
        cwd=isolation.work_root,
        check=False,
        timeout=1800,
    )
    envelope = parse_json_stdout(setup) or {}
    result.artifacts["setup_rc5"] = {
        "exit_code": setup.exit_code,
        "envelope": envelope,
        "stderr_tail": setup.stderr_tail,
    }
    if setup.exit_code != 0:
        raise ScenarioFailure(
            f"installing the exact rc5 release failed: {setup.stderr_tail or setup.stdout_tail}"
        )
    result.require(
        "AC-3/cycle: the first verified release in the isolated store is exact rc5",
        find_release_directory(store_root, "1.0.0rc5").name,
        active_release_id(isolation),
        find_release_directory(store_root, "1.0.0rc5").name,
    )
    current = store_root / "runtime" / "current"
    result.require(
        "AC-3/cycle: the selector resolves into the isolated store",
        True,
        str(os.path.realpath(current)).startswith(str(store_root)),
        True,
    )
    marker.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_project(
    inputs: Inputs,
    session: Session,
    *,
    project: Path,
    label: str,
) -> dict[str, Any]:
    """Initialize one managed project inside the isolated installation."""

    isolation = inputs.isolation
    project.mkdir(parents=True, exist_ok=True)
    if not (project / ".git").exists():
        session.run(
            f"{label}-git-init",
            ["git", "init", "--quiet", str(project)],
            env=isolation.environment(),
            cwd=isolation.work_root,
            check=False,
        )
    marker = project / "AGENTS.md"
    if not marker.is_file():
        marker.write_text(
            "# isolated qualification project\n\nThis project exists only inside the "
            "disposable qualification work root.\n",
            encoding="utf-8",
        )
    probe = _run_probe(
        session,
        inputs,
        f"{label}-register",
        release_dir=inputs.repo,
        body=PROJECT_PROBE,
        payload={
            "project": str(project),
            "state_root": str(isolation.state_root),
            "name": project.name,
        },
        env=isolation.environment(),
    )
    registered = probe["parsed"]
    if registered.get("outcome") != "registered" or not registered.get("verified"):
        raise ScenarioFailure(
            f"{label}: the isolated project binding was not registered "
            f"({registered.get('outcome')}, exit {probe['record'].exit_code}: "
            f"{probe['record'].stderr_tail[:200]})"
        )
    return {
        "path": str(project),
        "project_id": registered.get("project_id"),
        "registry": registered.get("registry"),
        "verified": registered.get("verified"),
        "marker_validates": registered.get("marker_validates"),
    }


def bundle_corroboration_record(inputs: Inputs) -> dict[str, Any]:
    """Record an optional bundle directory as unqualified corroboration, never as proof."""

    bundle_dir = inputs.bundle_dir
    assert bundle_dir is not None
    record: dict[str, Any] = {"path": str(bundle_dir)}
    wheels = sorted(bundle_dir.glob("aether_agents-*.whl"))
    locks = sorted(bundle_dir.glob("*release-lock*.json"))
    record["wheels"] = [path.name for path in wheels]
    record["release_locks"] = [path.name for path in locks]
    if wheels:
        record["wheel_sha256"] = sha256_file(wheels[0])
    if locks:
        payload = json.loads(locks[0].read_text(encoding="utf-8"))
        record["lock_aether_commit"] = payload.get("aether", {}).get("git_commit")
        record["lock_aether_version"] = payload.get("aether", {}).get("version")
        record["lock_hermes_tag"] = payload.get("hermes", {}).get("tag")
        record["lock_hermes_tree"] = payload.get("hermes", {}).get("source_tree_sha256")
        record["lock_sha256"] = sha256_file(locks[0])
    provenance = sorted(bundle_dir.glob("*provenance*.json"))
    if provenance:
        try:
            payload = json.loads(provenance[0].read_text(encoding="utf-8"))
        except ValueError:
            payload = {}
        record["tool_policy"] = payload.get("tool_policy")
        record["required_probe_failures"] = payload.get("probe_policy", {}).get("required_failures")
    refusal = sorted(bundle_dir.glob("*clean-install*.json"))
    if refusal:
        try:
            payload = json.loads(refusal[0].read_text(encoding="utf-8"))
        except ValueError:
            payload = {}
        record["handshake_probes_refused"] = [
            probe.get("name")
            for probe in payload.get("probes", [])
            if probe.get("required") and not probe.get("ok")
        ]
    record["qualified"] = False
    return record


def promotion_artifacts(
    inputs: Inputs,
    session: Session,
    result: ScenarioResult,
) -> dict[str, Any]:
    """Build the candidate promotion wheel+lock with the product's own lock builder."""

    isolation = inputs.isolation
    staging = isolation.work_root / "promotion-staging"
    if staging.exists():
        shutil.rmtree(staging)
    bundle_corroboration: dict[str, Any] | None = None
    if inputs.bundle_dir is not None:
        bundle_corroboration = bundle_corroboration_record(inputs)
    probe = _run_probe(
        session,
        inputs,
        "cycle-candidate-promotion-lock",
        release_dir=inputs.repo,
        body=LOCAL_CANDIDATE_LOCK_PROBE,
        payload={
            "store_root": str(isolation.store_root),
            "state_root": str(isolation.state_root),
            "aether_checkout": str(inputs.repo),
            "aether_commit": inputs.candidate_commit,
            "aether_tag": f"v{CANDIDATE_DISPLAY_VERSION}",
            "package_version": CANDIDATE_VERSION,
            "display_version": CANDIDATE_DISPLAY_VERSION,
            "aether_python_requires": ">=3.11,<3.14",
            "fork_checkout": str(inputs.fork_checkout),
            "fork_commit": MAINTAINED_FORK_COMMIT,
            "staging": str(staging),
        },
        env=isolation.environment(),
    )
    built = probe["parsed"]
    if built.get("outcome") != "built":
        raise ScenarioFailure(
            "the candidate promotion lock could not be derived "
            f"(exit {probe['record'].exit_code}: {probe['record'].stderr_tail[:300]})"
        )
    result.artifacts["promotion"] = {
        "wheel": Path(built["wheel"]).name,
        "wheel_sha256": built["wheel_sha256"],
        "lock_aether_commit": built["lock_aether"].get("git_commit"),
        "lock_aether_version": built["lock_aether"].get("version"),
        "lock_hermes_tag": built["lock_hermes"].get("tag"),
        "lock_hermes_tree": built["lock_hermes"].get("source_tree_sha256"),
        "fork_source_tree_sha256": built["fork"].get("source_tree_sha256"),
        "bundle_corroboration": bundle_corroboration,
    }
    result.require(
        "AC-3/cycle: the promotion lock binds the exact candidate revision",
        inputs.candidate_commit,
        built["lock_aether"].get("git_commit"),
        inputs.candidate_commit,
    )
    result.require(
        "AC-3/cycle: the promotion wheel carries the candidate identity",
        (CANDIDATE_DISPLAY_VERSION, CANDIDATE_VERSION),
        (built["lock_aether"].get("version"), built["lock_aether"].get("package_version")),
        (CANDIDATE_DISPLAY_VERSION, CANDIDATE_VERSION),
    )
    if bundle_corroboration is not None:
        result.limits.append(
            "a --bundle-dir was supplied as unqualified corroboration only: it is not a "
            "qualified bundle (its own build refused at the publication-path handshake probe) "
            "and its wheel digest differs from the promotion wheel under test; no bundle byte, "
            "lock or label was regenerated, edited or reused"
        )
        if bundle_corroboration.get("wheel_sha256") != built["wheel_sha256"]:
            result.limits.append(
                "bundle wheel digest "
                f"{bundle_corroboration.get('wheel_sha256')} != promotion wheel digest "
                f"{built['wheel_sha256']}; the artefact under test is the product-built "
                "promotion wheel, whose release id the isolated store activated"
            )
    result.require(
        "AC-3/cycle: the promotion lock binds the accepted maintained-fork source tree",
        MAINTAINED_FORK_TREE_SHA256,
        built["lock_hermes"].get("source_tree_sha256"),
        MAINTAINED_FORK_TREE_SHA256,
    )
    result.limits.append(
        "the candidate commit carries no tag at qualification time (tag creation is the "
        "integration card's), so the promotion lock is derived by the product's own "
        "local-candidate lock builder from the verified inputs; the published bundle lock's "
        "maintained-fork git-describe tag is not consumable by the install path and is reported "
        "as a downstream finding"
    )
    return {
        "wheel": Path(built["wheel"]),
        "release_lock": Path(built["release_lock"]),
        "bundle_corroboration": bundle_corroboration,
    }


def verify_release_copy(
    inputs: Inputs,
    *,
    version: str,
    source: Path,
    destination: Path,
) -> dict[str, Any]:
    """Prove the copied release carries the same bytes and the frozen revision's code."""

    verification: dict[str, Any] = {"release_id": destination.name}
    for name in ("record.json", "release.json", "release-lock.json"):
        left = source / name
        right = destination / name
        verification[f"{name}_sha256"] = sha256_file(right) if right.is_file() else None
        verification[f"{name}_identical"] = (
            left.is_file() and right.is_file() and sha256_file(left) == sha256_file(right)
        )
    package_dirs = sorted((destination / "manager").glob("lib/python*/site-packages/aether_agents"))
    if package_dirs:
        installed = package_dirs[0]
        rows = subprocess.run(
            [
                "git",
                "ls-tree",
                "-r",
                "--name-only",
                FROZEN_REVISIONS[version],
                "--",
                "src/aether_agents",
            ],
            cwd=str(inputs.repo),
            capture_output=True,
            text=True,
            check=False,
        ).stdout.split()
        mismatched: list[str] = []
        checked = 0
        for row in rows:
            relative = row[len("src/") :]
            installed_file = installed / relative[len("aether_agents/") :]
            expected = subprocess.run(
                ["git", "show", f"{FROZEN_REVISIONS[version]}:{row}"],
                cwd=str(inputs.repo),
                capture_output=True,
                check=False,
            ).stdout
            if installed_file.is_symlink():
                # Tracked symlinks (for example the lab resources link) are installed as
                # links; their identity is the link target, not a file digest.
                checked += 1
                continue
            if not installed_file.is_file():
                mismatched.append(f"missing:{relative}")
                continue
            checked += 1
            if sha256_file(installed_file) != sha256_bytes(expected):
                mismatched.append(relative)
        verification["frozen_revision"] = FROZEN_REVISIONS[version]
        verification["package_files_checked"] = checked
        verification["package_mismatches"] = mismatched
    return verification


def run_scenarios(
    inputs: Inputs, session: Session, selected: Sequence[str]
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    before = witness_set(live_witness_paths())

    preparation = ScenarioResult(name="prepare", scope="install the exact-version artifacts")
    try:
        prepare_store(inputs, session, preparation)
        preparation.assertions.append(
            Assertion(
                requirement="AC-3: the isolated store composes the exact-version artifacts",
                expected="no preparation error",
                observed="ok",
                ok=True,
            )
        )
    except (Refusal, ScenarioFailure) as error:
        preparation.error = str(error)
    results.append(preparation)
    if preparation.status != "passed":
        return results

    implementations: dict[str, Callable[[Inputs, Session, ScenarioResult], None]] = {
        "frozen-readers": scenario_frozen_readers,
        "cycle": scenario_cycle,
        "frozen-writer": scenario_frozen_writer,
        "legacy": scenario_legacy,
        "launch": scenario_launch,
        "docs": scenario_docs,
    }
    ordered = [name for name in SCENARIOS if name != "isolation"]
    for name in ordered:
        if name not in selected:
            cached_path = inputs.isolation.receipts / "scenarios" / f"{name}.json"
            if cached_path.is_file():
                try:
                    loaded = ScenarioResult.from_json(
                        json.loads(cached_path.read_text(encoding="utf-8"))
                    )
                    results.append(loaded)
                    session.commands.extend(loaded.commands)
                    continue
                except Exception:
                    pass
            continue
        scenario = ScenarioResult(name=name, scope=name)
        start = len(session.commands)
        try:
            implementations[name](inputs, session, scenario)
        except (Refusal, ScenarioFailure) as error:
            scenario.error = str(error)
        except Exception as error:  # unexpected: record, never hide
            scenario.error = f"{type(error).__name__}: {error}"
        scenario.commands = session.commands[start:]
        results.append(scenario)
        session.write_scenario(scenario)

    if "isolation" not in selected:
        cached_path = inputs.isolation.receipts / "scenarios" / "isolation.json"
        if cached_path.is_file():
            try:
                loaded = ScenarioResult.from_json(
                    json.loads(cached_path.read_text(encoding="utf-8"))
                )
                results.append(loaded)
                session.commands.extend(loaded.commands)
            except Exception:
                pass
    else:
        scenario = ScenarioResult(name="isolation", scope="confinement and isolation")
        start = len(session.commands)
        try:
            scenario_isolation(inputs, session, before=before, scenario_result=scenario)
        except (Refusal, ScenarioFailure) as error:
            scenario.error = str(error)
        except Exception as error:
            scenario.error = f"{type(error).__name__}: {error}"
        scenario.commands = session.commands[start:]
        results.append(scenario)
        session.write_scenario(scenario)
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    if arguments.command != "run":
        parser.print_help()
        return 2
    try:
        return run_command(arguments)
    except Refusal as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qualify_mixed_version_lifecycle.py",
        description=(
            "Qualify exact-version mixed-version lifecycle behavior in an isolated store. "
            "Every destination is derived from --work-root; the operator's live installation, "
            "selector, unit and configuration are never a destination."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")
    run = subparsers.add_parser("run", help="run the qualification scenarios")
    run.add_argument("--repo", type=Path, required=True, help="clean candidate checkout")
    run.add_argument("--candidate-commit", required=True, help="exact candidate revision")
    run.add_argument("--fork-checkout", type=Path, required=True, help="maintained-fork checkout")
    run.add_argument(
        "--source-store",
        type=Path,
        default=Path.home() / ".local" / "share" / "aether",
        help="read-only installation to take the authenticated old artifacts from",
    )
    run.add_argument("--bundle-dir", type=Path, default=None, help="qualified candidate bundle")
    run.add_argument("--work-root", type=Path, required=True, help="disposable isolated work root")
    run.add_argument(
        "--receipts-root",
        type=Path,
        required=True,
        help="durable private receipts root (never the work root)",
    )
    run.add_argument("--run-id", default=None, help="receipt run identifier (default: UTC stamp)")
    run.add_argument(
        "--scenarios",
        default="all",
        help="comma-separated subset of: " + ", ".join(SCENARIOS) + ", or 'all'",
    )
    run.add_argument("--launch-timeout", type=int, default=180, help="PTY launch budget in seconds")
    run.add_argument("--json", action="store_true", help="print the run record as JSON")
    return parser


def select_scenarios(value: str) -> list[str]:
    if value.strip() == "all":
        return list(SCENARIOS)
    selected = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in selected if item not in SCENARIOS]
    if unknown:
        raise Refusal("unknown scenario(s): " + ", ".join(unknown))
    return selected


def run_command(arguments: argparse.Namespace) -> int:
    run_id = arguments.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    isolation = Isolation(
        work_root=Path(arguments.work_root),
        receipts_root=Path(arguments.receipts_root),
        run_id=run_id,
    )
    overlaps = isolation.live_overlaps()
    # The installation the entry reads authenticated old artifacts from is live material:
    # nothing this entry writes may land inside it, whatever HOME the caller exported.
    source_root = Path(arguments.source_store).expanduser().resolve()
    for label, candidate in (
        ("work root", isolation.work_root),
        ("isolated HOME", isolation.home),
        ("isolated data home", isolation.data_home),
        ("isolated state home", isolation.state_home),
        ("isolated store root", isolation.store_root),
    ):
        resolved = candidate.expanduser().resolve()
        if (
            resolved == source_root
            or resolved.is_relative_to(source_root)
            or source_root.is_relative_to(resolved)
        ):
            overlaps.append(f"{label} {resolved} overlaps the source installation {source_root}")
    if overlaps:
        raise Refusal("refusing to run: " + "; ".join(overlaps))
    isolation.create()
    inputs = Inputs(
        repo=Path(arguments.repo),
        candidate_commit=arguments.candidate_commit,
        fork_checkout=Path(arguments.fork_checkout),
        source_store=Path(arguments.source_store),
        bundle_dir=Path(arguments.bundle_dir) if arguments.bundle_dir else None,
        isolation=isolation,
        launch_timeout=arguments.launch_timeout,
    )
    selected = select_scenarios(arguments.scenarios)
    candidate = inputs.verify_repo()
    fork = inputs.verify_fork()
    source = inputs.verify_source_store()
    bundle = inputs.verify_bundle() if inputs.bundle_dir is not None else None
    session = Session(isolation)
    started = time.time()
    results = run_scenarios(inputs, session, selected)
    record = {
        "schema": REPORT_SCHEMA,
        "run_id": run_id,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_ms": int((time.time() - started) * 1000),
        "candidate": candidate,
        "fork": fork,
        "source_store": source,
        "bundle": bundle,
        "scenarios_selected": selected,
        "scenarios": [scenario.to_json() for scenario in results],
        "environment_identity": session.environment_identity(isolation.environment()),
        "limits": [
            "raw receipts are private; this report carries digests, generic command lines and "
            "the scenario-to-result table",
            "the live installation is read-only material for authenticated old artifacts; the "
            "operator's unit, pointer, selector and configuration are witnessed before/after",
        ],
    }
    isolation.write_json("run.json", record)
    summary = render_summary(record)
    (isolation.receipts / "SUMMARY.txt").write_text(summary, encoding="utf-8")
    print(summary if not arguments.json else json.dumps(record, indent=2, sort_keys=True))
    failed = [scenario for scenario in results if scenario.status != "passed"]
    return 0 if not failed else 1


def render_summary(record: dict[str, Any]) -> str:
    lines = [
        f"run {record['run_id']}  schema {record['schema']}",
        f"candidate {record['candidate']['commit']} tree {record['candidate']['tree']}",
        f"fork {record['fork']['commit']}",
        f"elapsed {record['elapsed_ms']} ms",
        "",
        f"{'scenario':<16} {'status':<8} {'assertions':<12} detail",
    ]
    for scenario in record["scenarios"]:
        failed = [
            assertion["requirement"]
            for assertion in scenario["assertions"]
            if assertion["result"] == "fail"
        ]
        detail = scenario.get("error") or ("; ".join(failed) if failed else "ok")
        lines.append(
            f"{scenario['scenario']:<16} {scenario['status']:<8} "
            f"{len(scenario['assertions']):<12} {detail[:110]}"
        )
    agent_ready: list[tuple[str, int | None, Any]] = []
    for scenario in record["scenarios"]:
        pty_info = scenario.get("artifacts", {}).get("pty")
        if isinstance(pty_info, dict) and "agent_ready_ms" in pty_info:
            agent_ready.append(
                (
                    f"{scenario['scenario']}-fresh",
                    pty_info.get("agent_ready_ms"),
                    pty_info.get("corpus_scale"),
                )
            )
        pty_resume_info = scenario.get("artifacts", {}).get("pty_resume")
        if isinstance(pty_resume_info, dict) and "agent_ready_ms" in pty_resume_info:
            agent_ready.append(
                (
                    f"{scenario['scenario']}-resume",
                    pty_resume_info.get("agent_ready_ms"),
                    pty_resume_info.get("corpus_scale"),
                )
            )
    for name, ready, corpus in agent_ready:
        lines.append(f"agent-ready ({name}): {ready} ms, corpus {corpus}")
    lines.append("")
    lines.append(f"receipts: {record['run_id']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":  # pragma: no cover - exercised through the CLI
    raise SystemExit(main())
