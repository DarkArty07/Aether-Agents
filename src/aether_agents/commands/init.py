"""``aether init`` command implementation.

Normative source: ``specs/001-aether-v1-productization/contracts/cli.md`` section 2
(``aether init``) and ``specs/r13-synthesis-and-release/spec.md`` FR-1334.

The command writes the portable ``.aether/project.toml`` marker validated against the
canonical ``project.schema.json``, and maps that UUID to exactly one native Hermes
Project in the local Aether registry.

Two boundaries are deliberate:

* Hermes is never imported. The native Project is resolved by opening the documented
  per-profile ``$HERMES_HOME/projects.db`` **read-only** and matching ``primary_path``
  exactly. Name, slug, cwd, and approximate-path matching are never used, because a
  real installation can hold several Projects sharing one human name.
* Hermes state is never written. When no Project matches, ``init`` refuses and reports
  the command the owner can run; creating a native Project is not this command's
  authority.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import tomllib
import uuid
from pathlib import Path
from typing import Any

from aether_agents import product_version
from aether_agents.observation.context import ProjectRegistry, canonical_project_id
from aether_agents.project_marker import ProjectMarkerValidationError, validate_project_marker
from aether_agents.result import Envelope

__all__ = ["build_subparser", "run_init"]

_GITHUB_REMOTE_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


class InitError(Exception):
    """A refusal carrying its stable envelope code and failure kind."""

    def __init__(self, code: str, message: str, *, failure_kind: str = "invalid_input") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.failure_kind = failure_kind


def build_subparser(subparsers: "argparse._SubParsersAction") -> argparse.ArgumentParser:
    """Register ``init`` on a top-level ``argparse`` subparsers action."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a Git repository as an Aether Project.",
        description=(
            "aether init [PATH] [--name NAME] [--forge local|github] "
            "[--hermes-project ID] [--dry-run] [--json]"
        ),
    )
    parser.add_argument(
        "path", nargs="?", default=None, metavar="PATH", help="Repository root (default: cwd)."
    )
    parser.add_argument("--name", default=None, help="Project name (default: directory name).")
    parser.add_argument(
        "--forge",
        choices=("local", "github"),
        default=None,
        help="Override the forge detected from the 'origin' remote.",
    )
    parser.add_argument(
        "--hermes-project",
        default=None,
        metavar="ID",
        help="Native Hermes Project id, required when the exact-path match is not unique.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def _git(root: Path, *arguments: str) -> str | None:
    """Run a read-only git command in ``root``; return stripped stdout or ``None``."""
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment.pop("GIT_DIR", None)
    environment.pop("GIT_WORK_TREE", None)
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _repository_root(path: Path) -> Path:
    """Resolve ``path`` to a directory that is exactly one Git repository root."""
    if not path.is_dir():
        raise InitError(
            "AETHER-INIT-PATH-INVALID",
            f"path is not an existing directory: {path}",
            failure_kind="invalid_input",
        )
    resolved = path.resolve()
    top_level = _git(resolved, "rev-parse", "--show-toplevel")
    if top_level is None:
        raise InitError(
            "AETHER-INIT-NOT-A-GIT-REPOSITORY",
            f"not a Git repository: {resolved}",
            failure_kind="missing_prerequisite",
        )
    if Path(top_level).resolve() != resolved:
        raise InitError(
            "AETHER-INIT-NOT-REPOSITORY-ROOT",
            f"path is inside a Git repository but is not its root: {Path(top_level).resolve()}",
            failure_kind="invalid_input",
        )
    return resolved


def _detect_forge(root: Path, requested: str | None) -> tuple[str, str | None]:
    """Return ``(forge, github_repository)`` from the ``origin`` remote."""
    remote = _git(root, "remote", "get-url", "origin")
    match = _GITHUB_REMOTE_RE.match(remote) if remote else None
    repository = match.group("repository") if match else None
    if requested == "github":
        if repository is None:
            raise InitError(
                "AETHER-INIT-FORGE-UNRESOLVED",
                "--forge github requires an 'origin' remote pointing at a GitHub repository",
                failure_kind="invalid_input",
            )
        return "github", repository
    if requested == "local":
        return "local", None
    return ("github", repository) if repository else ("local", None)


def _read_existing_marker(marker_path: Path) -> dict[str, Any] | None:
    """Return the validated existing marker, or ``None`` when absent.

    An unreadable or non-conforming marker is a refusal, never something to overwrite.
    """
    if not marker_path.exists():
        return None
    if marker_path.is_symlink() or not marker_path.is_file():
        raise InitError(
            "AETHER-INIT-MARKER-UNSAFE",
            "existing .aether/project.toml is not a regular file",
            failure_kind="integrity_failure",
        )
    try:
        marker = tomllib.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise InitError(
            "AETHER-INIT-MARKER-UNREADABLE",
            "existing .aether/project.toml is unreadable",
            failure_kind="integrity_failure",
        ) from exc
    try:
        validate_project_marker(marker)
    except ProjectMarkerValidationError as exc:
        raise InitError(
            "AETHER-INIT-MARKER-INVALID",
            "existing .aether/project.toml does not conform to the canonical schema; "
            "it is preserved unchanged",
            failure_kind="integrity_failure",
        ) from exc
    return marker


def _hermes_projects_db() -> Path:
    """The documented per-profile Hermes projects database path."""
    home = os.environ.get("HERMES_HOME")
    return (Path(home) if home else Path.home() / ".hermes") / "projects.db"


def _native_projects_for(root: Path) -> list[dict[str, str]]:
    """Every non-archived native Hermes Project whose primary path is exactly ``root``."""
    database = _hermes_projects_db()
    if not database.is_file():
        raise InitError(
            "AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE",
            f"Hermes projects database does not exist: {database}",
            failure_kind="missing_prerequisite",
        )
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise InitError(
            "AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE",
            "Hermes projects database cannot be opened read-only",
            failure_kind="missing_prerequisite",
        ) from exc
    try:
        rows = connection.execute(
            "SELECT id, slug, primary_path FROM projects WHERE archived = 0"
        ).fetchall()
    except sqlite3.Error as exc:
        raise InitError(
            "AETHER-INIT-HERMES-PROJECTS-UNREADABLE",
            "Hermes projects database does not expose the expected schema",
            failure_kind="integrity_failure",
        ) from exc
    finally:
        connection.close()

    matches: list[dict[str, str]] = []
    for identifier, slug, primary_path in rows:
        if not isinstance(primary_path, str) or not primary_path:
            continue
        try:
            candidate = Path(primary_path).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if candidate == root:
            matches.append({"id": str(identifier), "slug": str(slug)})
    return matches


def _resolve_hermes_project(root: Path, requested: str | None) -> dict[str, str]:
    """Bind exactly one native Hermes Project by exact primary-path match."""
    matches = _native_projects_for(root)
    if requested is not None:
        selected = [entry for entry in matches if entry["id"] == requested]
        if not selected:
            raise InitError(
                "AETHER-INIT-HERMES-PROJECT-PATH-MISMATCH",
                f"Hermes Project '{requested}' does not have {root} as its exact primary path",
                failure_kind="integrity_failure",
            )
        return selected[0]
    if not matches:
        raise InitError(
            "AETHER-INIT-HERMES-PROJECT-MISSING",
            f"no non-archived Hermes Project has {root} as its exact primary path; "
            f"create one with: hermes project create <NAME> --primary {root}",
            failure_kind="missing_prerequisite",
        )
    if len(matches) > 1:
        identifiers = ", ".join(sorted(entry["id"] for entry in matches))
        raise InitError(
            "AETHER-INIT-HERMES-PROJECT-AMBIGUOUS",
            f"several Hermes Projects claim {root} as their exact primary path "
            f"({identifiers}); re-run with --hermes-project ID",
            failure_kind="integrity_failure",
        )
    return matches[0]


def _render_marker(marker: dict[str, Any]) -> str:
    """Serialize the closed marker schema as TOML.

    The schema is a fixed, flat set of strings plus one optional ``[github]`` table, so
    a dedicated serializer avoids adding a write-side TOML dependency. ``json.dumps``
    produces exactly the escaping a TOML basic string requires for these values.
    """
    lines = [f"schema_version = {int(marker['schema_version'])}"]
    for key in ("project_id", "name", "initialized_by", "forge", "contract_root"):
        lines.append(f"{key} = {json.dumps(marker[key], ensure_ascii=False)}")
    if "default_branch" in marker:
        lines.append(f"default_branch = {json.dumps(marker['default_branch'], ensure_ascii=False)}")
    if "github" in marker:
        lines.append("")
        lines.append("[github]")
        lines.append(
            f"repository = {json.dumps(marker['github']['repository'], ensure_ascii=False)}"
        )
    return "\n".join(lines) + "\n"


def _write_marker(marker_path: Path, marker: dict[str, Any]) -> None:
    """Atomically write the marker as ordinary tracked project content."""
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = marker_path.with_name(f".{marker_path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(_render_marker(marker), encoding="utf-8")
        os.replace(temporary, marker_path)
    finally:
        temporary.unlink(missing_ok=True)


_TRACKED_PATHS = (".aether/project.toml", ".aether/objective-contracts/")
_IGNORED_PATHS = (".aether/drafts/",)

_IGNORE_BLOCK = """
# Aether project identity and finalized Objective Contracts (managed by `aether init`).
# Local drafts and every other .aether/ entry stay ignored.
!.aether/
/.aether/*
!/.aether/project.toml
!/.aether/objective-contracts/
!/.aether/objective-contracts/**
"""


def _is_ignored(root: Path, relative: str) -> bool:
    """Report whether Git currently excludes ``relative`` inside ``root``."""
    return _git(root, "check-ignore", "-q", relative) is not None


def _ignore_policy_satisfied(root: Path) -> bool:
    """The canonical layout requires tracked marker/finals and ignored drafts."""
    return not any(_is_ignored(root, path) for path in _TRACKED_PATHS) and all(
        _is_ignored(root, path) for path in _IGNORED_PATHS
    )


def _apply_ignore_policy(root: Path) -> None:
    """Append the canonical block so the marker and finalized contracts are trackable.

    Only ever appends: existing rules are never edited or removed, so unrelated project
    policy is preserved and other ``.aether/`` content stays ignored. The result is then
    verified with Git itself; if the policy is still unsatisfied the file is restored
    byte-for-byte and the caller refuses rather than reporting a usable project.
    """
    path = root / ".gitignore"
    original: bytes | None = None
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise InitError(
                "AETHER-INIT-IGNORE-POLICY-UNSAFE",
                ".gitignore is not a regular file; refusing to modify it",
                failure_kind="integrity_failure",
            )
        original = path.read_bytes()

    separator = b"" if original is None or original.endswith(b"\n") else b"\n"
    try:
        with path.open("ab") as handle:
            handle.write(separator + _IGNORE_BLOCK.encode("utf-8"))
    except OSError as exc:
        raise InitError(
            "AETHER-INIT-IGNORE-POLICY-UNWRITABLE",
            "could not update .gitignore to make the Aether marker trackable",
            failure_kind="runtime_failure",
        ) from exc

    if _ignore_policy_satisfied(root):
        return
    if original is None:
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(original)
    raise InitError(
        "AETHER-INIT-IGNORE-POLICY-CONFLICT",
        "existing Git ignore rules keep .aether/project.toml or "
        ".aether/objective-contracts/ excluded and cannot be corrected by appending; "
        "adjust the ignore policy so both are trackable, then re-run init",
        failure_kind="blocked",
    )


def _plan(root: Path, args: argparse.Namespace, registry: ProjectRegistry) -> dict[str, Any]:
    """Compute the full init decision without writing anything."""
    marker_path = root / ".aether" / "project.toml"
    existing = _read_existing_marker(marker_path)
    native = _resolve_hermes_project(root, args.hermes_project)

    if existing is not None:
        project_id = canonical_project_id(existing.get("project_id"))
        if project_id is None:
            raise InitError(
                "AETHER-INIT-MARKER-INVALID",
                "existing .aether/project.toml has no canonical project_id",
                failure_kind="integrity_failure",
            )
        registered = registry.project_path(project_id)
        if registered is not None and registered.resolve() != root:
            # The UUID is already bound elsewhere. Only a stale binding may be re-pointed:
            # if the other location still carries this identity, both are live and the
            # conflict is real.
            if registered.is_dir() and (registered / ".aether" / "project.toml").is_file():
                raise InitError(
                    "AETHER-INIT-IDENTITY-CONFLICT",
                    f"project identity is already registered at a different live "
                    f"location: {registered}",
                    failure_kind="integrity_failure",
                )
            return {
                "action": "reregister",
                "project_id": project_id,
                "marker": existing,
                "native": native,
                "previous_path": str(registered),
            }
        if registered is None:
            return {
                "action": "register",
                "project_id": project_id,
                "marker": existing,
                "native": native,
            }
        return {
            "action": "none",
            "project_id": project_id,
            "marker": existing,
            "native": native,
        }

    name = args.name or root.name
    forge, repository = _detect_forge(root, args.forge)
    marker: dict[str, Any] = {
        "schema_version": 1,
        "project_id": str(uuid.uuid4()),
        "name": name,
        "initialized_by": product_version(),
        "forge": forge,
        "contract_root": "specs",
    }
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    if branch:
        marker["default_branch"] = branch
    if repository is not None:
        marker["github"] = {"repository": repository}
    try:
        validate_project_marker(marker)
    except ProjectMarkerValidationError as exc:
        raise InitError(
            "AETHER-INIT-MARKER-INVALID",
            "the generated project marker does not conform to the canonical schema",
            failure_kind="internal_error",
        ) from exc
    return {
        "action": "create",
        "project_id": marker["project_id"],
        "marker": marker,
        "native": native,
    }


def run_init(args: argparse.Namespace, *, registry: ProjectRegistry | None = None) -> Envelope:
    """Execute ``aether init`` and return its result envelope."""
    envelope = Envelope(command="init", result="ready", manager_version=product_version())
    registry = registry or ProjectRegistry()
    try:
        root = _repository_root(Path(args.path) if args.path else Path.cwd())
        plan = _plan(root, args, registry)
    except InitError as error:
        envelope.result = "error"
        envelope.failure_kind = error.failure_kind
        envelope.fail(error.code, error.message)
        return envelope

    action = plan["action"]
    marker_path = root / ".aether" / "project.toml"
    ignore_fix_required = not _ignore_policy_satisfied(root)
    envelope.data = {
        "project_id": plan["project_id"],
        "project_path": str(root),
        "name": plan["marker"]["name"],
        "forge": plan["marker"]["forge"],
        "marker_path": str(marker_path),
        "hermes_project_id": plan["native"]["id"],
        "hermes_project_slug": plan["native"]["slug"],
        "ignore_policy": "update" if ignore_fix_required else "already_correct",
    }

    if args.dry_run:
        envelope.result = "planned"
        envelope.data["action"] = action
        return envelope

    if action == "none" and not ignore_fix_required:
        envelope.result = "no_change"
        return envelope

    # The ignore policy is corrected before the marker is written so the file never
    # lands in an excluded path, and a refusal here leaves the repository untouched.
    if ignore_fix_required:
        try:
            _apply_ignore_policy(root)
        except InitError as error:
            envelope.result = "error"
            envelope.failure_kind = error.failure_kind
            envelope.fail(error.code, error.message)
            return envelope

    if action == "create":
        _write_marker(marker_path, plan["marker"])
    if not registry.register(
        plan["project_id"],
        root,
        name=str(plan["marker"]["name"]),
        hermes_project_id=plan["native"]["id"],
    ):
        envelope.result = "error"
        envelope.failure_kind = "runtime_failure"
        envelope.fail(
            "AETHER-INIT-REGISTRY-WRITE-FAILED", "the local Aether project registry was not updated"
        )
        return envelope

    envelope.result = "changed"
    envelope.changed = True
    if action == "reregister":
        envelope.warn(
            "AETHER-INIT-PROJECT-RELOCATED",
            "the registry binding for this project identity was moved to this location.",
            previous_path=plan["previous_path"],
        )
    return envelope
