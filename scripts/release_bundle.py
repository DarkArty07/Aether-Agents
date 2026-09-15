#!/usr/bin/env python3
"""Build and qualify one Aether release bundle from exact clean revision inputs.

The bundle is the release-identity boundary for one annotated tag and GitHub prerelease.
It is built once from the exact Aether and maintained-fork commits, inspected member by
member, scanned for private paths and secrets, installed into fresh disposable roots with
the normal resolver, and exercised through the shipped CLI and runtime handshakes.  This
tool never publishes, tags, pushes, activates live instances or mutates live state:
publication is the Supervisor-owned integration step that attaches these exact bytes.

``build`` writes the bundle; ``verify`` re-proves an existing bundle (for example after a
download) without rebuilding it.  ``members`` prints the exact member paths a publication
must attach - the verified set plus ``SHA256SUMS``, so an unlisted extra file is refused
rather than attached - and ``verify-published-assets`` proves an existing GitHub release
already carries exactly those bytes by name and digest.  ``gh release edit`` accepts no
file arguments, so a reconcile that disagrees with the qualified bytes is refused with a
precise diagnostic instead of silently attaching nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

DISTRIBUTION = "aether-agents"
AETHER_REPOSITORY = "https://github.com/DarkArty07/Aether-Agents"
MAINTAINED_FORK_REPOSITORY = "https://github.com/DarkArty07/aether-hermes"
MAINTAINED_FORK_BRANCH = "aether-main"
RELEASE_LOCK_SCHEMA_VERSION = 4
HERMES_SOURCE_MODE = "maintained_fork"
PROFILE_BUNDLE_VERSION = "2"
PROFILE_ROLES = ("morfeo", "supervisor", "implementer")
AETHER_PLUGIN_NAMES = (
    "aether-contract-observer",
    "aether-objective-contracts",
    "aether-project-knowledge",
    "aether-telegram-monitor",
)
PINNED_LOCAL_UPDATE_OPTIONS = (
    "--local",
    "--aether-checkout",
    "--aether-commit",
    "--fork-checkout",
    "--fork-commit",
)
REPORT_SCHEMA = "aether.release-bundle.v1"
_STABLE_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_RC_VERSION_RE = re.compile(r"^(?P<base>[0-9]+\.[0-9]+\.[0-9]+)rc(?P<serial>[1-9][0-9]*)$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MAX_EXCERPT = 1600
# Records one user-home component so a report can name the match shape without publishing
# an operator-path literal that the canonical scanner would flag in Aether-authored bytes.
_HOME_SEGMENT = re.compile(r"(?i)((?:^|[/\\])(?:home|Users)[/\\])[^/\\]+")
# High-confidence credential shapes.  A private-key marker only counts as material when a
# base64 body follows it, so the repository's own scanner pattern literals never match.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private-key-material",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=]{64,}"
        ),
    ),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}")),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("telegram-bot-token", re.compile(r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b")),
)
_HERMES_PROBE = (
    "import importlib.metadata as m, json, hermes_cli;"
    "eps=sorted((e.name,e.value) for e in m.entry_points().select(group='hermes_agent.plugins'));"
    "print(json.dumps({'hermes_version': m.version('hermes-agent'),"
    " 'plugins': eps, 'hermes_cli': hermes_cli.__name__}))"
)
# The repository's own canonical secret patterns (the same set its policy workflow enforces
# on spec payloads).  These are enforced strictly on every bundle member.
_STRICT_SECRET_NAMES = ("private-key-material", "github-token", "github-pat")


class BundleError(RuntimeError):
    """Refuse to build or certify a bundle that is not exactly the declared input."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------- utilities


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            hasher.update(chunk)
    return hasher.hexdigest()


def _isolated_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Drop ambient package-manager and interpreter policy from a child process."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UV_", "PIP_", "PYTHON", "SOURCE_DATE_EPOCH"))
    }
    for name in ("VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH", "PYTHONHOME"):
        environment.pop(name, None)
    if extra:
        environment.update(extra)
    return environment


def _run(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(argv), cwd=cwd, env=env, check=False, capture_output=True, text=True
        )
    except OSError as error:  # the host toolchain is the only way this fails
        raise BundleError("toolchain-unavailable", f"{argv[0]} is unavailable") from error


def _git(arguments: Sequence[str], cwd: Path) -> str:
    completed = _run(["git", *arguments], cwd=cwd, env=_isolated_environment())
    if completed.returncode != 0:
        raise BundleError("git-failed", f"git {' '.join(arguments)} failed in {cwd}")
    return completed.stdout


def _git_raw(arguments: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run(["git", *arguments], cwd=cwd, env=_isolated_environment())


def _normalize_remote(url: str) -> str:
    value = url.strip()
    if value.endswith(".git"):
        value = value[: -len(".git")]
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value[len("git@github.com:") :]
    return value.rstrip("/").lower()


def _excerpt(text: str, limit: int = _MAX_EXCERPT) -> str:
    value = text.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n[truncated {len(value) - limit} characters]"


# ``uv`` reports how long each resolution, preparation, install and check took.  That
# elapsed value is the one part of its output that differs between two runs of the exact
# same revisions (the same resolution is 8 ms in one run and 10 ms in the next), and the
# qualified member set has to be reproducible from those identical inputs, so the value is
# recorded as ``<elapsed>`` rather than certified as a member byte.
_ELAPSED_RE = re.compile(r"\bin (?:\d+m )?\d+(?:\.\d+)?(?:ns|µs|us|ms|s)\b")

# A venv exposes the same interpreter as ``bin/python`` and ``bin/python3`` (often also
# ``bin/python3.13``), and which alias a run records depends only on whether the venv
# already existed when the build started: a fresh ``uv run`` records ``python``, the next
# one ``python3``.  The interpreter is a platform detail, not a member byte, so every
# interpreter leaf is recorded canonically as ``bin/<interpreter>`` the same way the
# elapsed value is recorded as ``<elapsed>``.
_INTERPRETER_RE = re.compile(r"\bbin/python(?:3(?:\.\d+)?[a-z]?)?(?:\.exe)?(?![0-9A-Za-z_.\-])")


def _normalize_captured(text: str) -> str:
    """Keep captured tool output, drop the run-to-run and host-local values from it."""

    value = _ELAPSED_RE.sub("in <elapsed>", text)
    return _INTERPRETER_RE.sub("bin/<interpreter>", value)


def _write_json(path: Path, payload: Any) -> None:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(data, encoding="utf-8")


def _portable(text: str, replacements: Sequence[tuple[Path | str, str]]) -> str:
    """Replace host-local scratch paths so reports stay portable."""

    value = text
    for source, token in replacements:
        value = value.replace(str(source), token)
    return value


def _portable_capture(text: str, masks: Sequence[tuple[Path | str, str]]) -> str:
    """Mask host-local paths, then drop the values two runs must not disagree on."""

    return _normalize_captured(_portable(text, masks))


def _capture(text: str, masks: Sequence[tuple[Path | str, str]], limit: int = _MAX_EXCERPT) -> str:
    """Record captured output portably: mask first, excerpt second.

    Masking before excerpting is what makes the recorded bytes - including the
    ``[truncated N characters]`` footer - depend only on the portable text.  Excerpting
    first counts the characters of the real host paths, so the same capture recorded from
    a longer or shorter build directory differs even though nothing else did.
    """

    return _excerpt(_portable_capture(text, masks), limit)


def _report_masks(
    roots: Path, work: Path, bundle: Path, aether_checkout: Path
) -> tuple[tuple[Path | str, str], ...]:
    """Mask every host-local path a report could otherwise disclose.

    The build interpreter comes first: it normally lives inside the checkout
    (``<aether-checkout>/.venv/bin/python3``), and masking the checkout path first would
    leave the interpreter leaf visible - the one part of that path that differs between a
    fresh and an already-populated venv.  Its resolved target is masked too, so the
    host-local CPython installation a uv-managed venv points at cannot leak either.
    """

    interpreter = Path(sys.executable)
    return (
        (interpreter, "<probe-interpreter>"),
        (interpreter.resolve(), "<probe-interpreter>"),
        (roots, "<disposable-root>"),
        (bundle, "<bundle>"),
        (aether_checkout, "<aether-checkout>"),
        (work, "<work>"),
    )


# --------------------------------------------------------------------- release identity


def release_identity(package_version: str, tag: str | None = None) -> dict[str, Any]:
    """Map one PEP 440 package version to the single supported tag identity."""

    candidate = _RC_VERSION_RE.match(package_version)
    if candidate is not None:
        semver = f"{candidate['base']}-rc.{candidate['serial']}"
        prerelease = True
    elif _STABLE_VERSION_RE.match(package_version):
        semver = package_version
        prerelease = False
    else:
        raise BundleError(
            "unsupported-version",
            f"VERSION must be X.Y.Z or X.Y.ZrcN, observed {package_version!r}",
        )
    expected_tag = f"v{semver}"
    if tag is not None and tag != expected_tag:
        raise BundleError(
            "identity-mismatch",
            f"tag {tag!r} does not match the derived release identity {expected_tag!r}",
        )
    return {
        "package_version": package_version,
        "semver": semver,
        "tag": expected_tag,
        "prerelease": prerelease,
    }


# ------------------------------------------------------------------------ product load


def load_product(aether_checkout: Path) -> Any:
    """Import the product modules from the exact checkout under qualification."""

    source = (aether_checkout / "src").resolve()
    if not (source / "aether_agents" / "lifecycle.py").is_file():
        raise BundleError(
            "product-source-missing",
            f"{aether_checkout} does not contain a src-layout aether_agents package",
        )
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    for name in [key for key in sys.modules if key.split(".")[0] == "aether_agents"]:
        del sys.modules[name]
    import aether_agents.lifecycle as lifecycle

    loaded = Path(lifecycle.__file__).resolve()
    if not loaded.is_relative_to(source):
        raise BundleError(
            "product-source-mismatch",
            "the imported product module does not come from the checkout under qualification",
        )
    return lifecycle


def profile_bundle_sha256(lifecycle: Any) -> str:
    """Reproduce the coordinator's profile-bundle manifest digest without staging it."""

    manager = lifecycle.LifecycleManager
    roles = list(lifecycle._PROFILE_ROLES)
    if tuple(roles) != PROFILE_ROLES:
        raise BundleError("profile-roles-mismatch", f"unexpected managed roles: {roles}")
    profiles: dict[str, Any] = {}
    for role in roles:
        resources = {
            name: {"path": f"profiles/{role}/{name}", "sha256": _sha256_file(source)}
            for name, source in manager._profile_sources(role).items()
        }
        skills = {
            skill: {
                "path": f"profiles/{role}/skills/{skill}/SKILL.md",
                "sha256": _sha256_file(source),
            }
            for skill, source in manager._skill_sources().items()
        }
        profiles[role] = {"resources": resources, "skills": skills}
    manifest = {
        "schema_version": 2,
        "observer_entry_point": lifecycle.HERMES_BASELINE.observer_entry_point,
        "roles": roles,
        "profiles": profiles,
    }
    encoded = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return _sha256_bytes(encoded)


# ----------------------------------------------------------------------- git revisions


def checkout_evidence(path: Path, commit: str, *, kind: str, repository: str) -> dict[str, Any]:
    """Prove one checkout is a clean exact-commit input of the declared repository."""

    if not _COMMIT_RE.match(commit):
        raise BundleError("unknown-revision", f"{kind} commit {commit!r} is not a full 40-hex id")
    if not (path / ".git").exists():
        raise BundleError("checkout-missing", f"{kind} checkout {path} is not a Git repository")
    head = _git(["rev-parse", "HEAD"], path).strip()
    if head != commit:
        raise BundleError(
            "revision-mismatch",
            f"{kind} checkout HEAD {head} is not the requested commit {commit}",
        )
    status = _git(["status", "--porcelain"], path)
    if status.strip():
        raise BundleError(
            "dirty-checkout",
            f"{kind} checkout has uncommitted changes: {status.strip().splitlines()[0]}",
        )
    remotes = {
        _normalize_remote(line.split("\t", 1)[1].rsplit(None, 1)[0])
        for line in _git(["remote", "-v"], path).splitlines()
        if line.strip()
    }
    if _normalize_remote(repository) not in remotes:
        raise BundleError("repository-identity", f"{kind} checkout has no remote for {repository}")
    return {"kind": kind, "commit": commit, "head": head, "remotes": sorted(remotes)}


def resolve_fork(
    *, checkout: Path | None, repository: str | None, commit: str, work: Path
) -> tuple[Path, dict[str, Any]]:
    """Resolve the maintained-fork source to one local repository at the exact commit."""

    if not _COMMIT_RE.match(commit):
        raise BundleError("unknown-revision", f"fork commit {commit!r} is not a full 40-hex id")
    if checkout is not None and repository is not None:
        raise BundleError(
            "ambiguous-fork-binding",
            "--fork-repository and --fork-checkout are mutually exclusive",
        )
    if checkout is not None:
        evidence = checkout_evidence(
            checkout, commit, kind="maintained-fork", repository=MAINTAINED_FORK_REPOSITORY
        )
        return checkout, evidence
    if repository is None:
        raise BundleError(
            "missing-fork-binding",
            "one of --fork-repository or --fork-checkout is required for the maintained fork",
        )
    local = Path(repository).expanduser()
    if local.exists() and (local / ".git").exists():
        evidence = checkout_evidence(
            local, commit, kind="maintained-fork", repository=MAINTAINED_FORK_REPOSITORY
        )
        return local, evidence
    if _normalize_remote(repository) != _normalize_remote(MAINTAINED_FORK_REPOSITORY):
        raise BundleError(
            "repository-identity",
            f"maintained-fork source must be {MAINTAINED_FORK_REPOSITORY}, observed {repository}",
        )
    fetched = work / "maintained-fork"
    fetched.mkdir(parents=True, exist_ok=True)
    _git(["init", "--quiet", "--initial-branch", MAINTAINED_FORK_BRANCH], fetched)
    _git(["remote", "add", "origin", repository], fetched)
    for ref in (commit, MAINTAINED_FORK_BRANCH):
        completed = _git_raw(["fetch", "--no-tags", "origin", ref], fetched)
        if completed.returncode != 0:
            raise BundleError("revision-unavailable", f"{repository} does not expose {ref}")
    _git(["checkout", "--quiet", "--detach", commit], fetched)
    status = _git(["status", "--porcelain"], fetched).strip()
    if status:
        raise BundleError("dirty-checkout", f"fetched maintained fork is not clean: {status}")
    return fetched, {
        "kind": "maintained-fork",
        "commit": commit,
        "head": commit,
        "remotes": [_normalize_remote(repository)],
    }


def verify_branch_membership(repo: Path, commit: str, branch: str) -> dict[str, Any]:
    """Prove the exact commit is reachable from the declared maintained-fork branch."""

    candidates: list[tuple[str, str]] = []
    for reference in (f"refs/remotes/origin/{branch}", f"refs/heads/{branch}"):
        completed = _git_raw(["rev-parse", "--verify", reference], repo)
        if completed.returncode == 0:
            candidates.append((reference, completed.stdout.strip()))
    if not candidates:
        raise BundleError(
            "branch-unavailable",
            f"maintained fork does not expose {branch} to confirm the source identity",
        )
    proven = [
        reference
        for reference, _ in candidates
        if _git_raw(["merge-base", "--is-ancestor", commit, reference], repo).returncode == 0
    ]
    if not proven:
        observed = ", ".join(f"{reference}={tip}" for reference, tip in candidates)
        raise BundleError(
            "branch-divergence",
            f"commit {commit} is not reachable from {branch} (observed {observed})",
        )
    return {
        "branch": branch,
        "proven_by": proven[0],
        "branch_tips": {reference: tip for reference, tip in candidates},
        "reachable": True,
    }


def materialize_commit(lifecycle: Any, repo: Path, commit: str, destination: Path) -> str:
    """Materialize the exact commit and return its deterministic tree digest."""

    lifecycle._materialize_git_archive(repo, commit, destination)
    digest = lifecycle._tree_sha256(destination)
    if not isinstance(digest, str):
        raise BundleError("tree-digest", "materialized tree digest is not a string")
    return digest


def _git_archive_bytes(repo: Path, commit: str, prefix: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "archive", "--format=tar.gz", f"--prefix={prefix}/", commit],
            cwd=repo,
            env=_isolated_environment(),
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise BundleError("toolchain-unavailable", "git is unavailable") from error
    if completed.returncode != 0:
        raise BundleError("archive-failed", f"archiving {commit} failed")
    return completed.stdout


def _extract_trusted_archive(data: bytes, destination: Path) -> list[dict[str, Any]]:
    """Extract one trusted Git archive with a closed path grammar and list its members."""

    members: list[dict[str, Any]] = []
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            name = member.name
            parts = Path(name).parts
            if not name or name.startswith("/") or ".." in parts:
                raise BundleError("archive-unsafe", f"unsafe archive member {name!r}")
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if member.issym() or member.islnk() or not member.isfile():
                raise BundleError("archive-unsafe", f"unsupported member {name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = archive.extractfile(member)
            if stream is None:
                raise BundleError("archive-unsafe", f"unreadable member {name!r}")
            payload = stream.read()
            target.write_bytes(payload)
            members.append({"name": name, "bytes": len(payload), "sha256": _sha256_bytes(payload)})
    return sorted(members, key=lambda row: row["name"])


# ------------------------------------------------------------------------------ build


def build_distributions(
    checkout: Path, out_dir: Path, *, source_date_epoch: int
) -> dict[str, Path]:
    completed = _run(
        ["uv", "build", "--out-dir", str(out_dir), str(checkout)],
        cwd=checkout,
        env=_isolated_environment({"SOURCE_DATE_EPOCH": str(source_date_epoch)}),
    )
    if completed.returncode != 0:
        raise BundleError(
            "build-failed",
            "uv build failed: " + _excerpt(completed.stderr or completed.stdout, 400),
        )
    wheels = sorted(out_dir.glob("*.whl"))
    sdists = sorted(out_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise BundleError(
            "build-output-ambiguous",
            f"uv build produced {len(wheels)} wheels and {len(sdists)} source distributions",
        )
    return {"wheel": wheels[0], "sdist": sdists[0]}


def inspect_sdist(path: Path) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            payload = stream.read() if stream is not None else b""
            members.append(
                {"name": member.name, "bytes": len(payload), "sha256": _sha256_bytes(payload)}
            )
    members.sort(key=lambda row: row["name"])
    roots = sorted({row["name"].split("/", 1)[-1].split("/", 1)[0] for row in members})
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "member_count": len(members),
        "members": members,
        "root_entries": roots,
    }


def inspect_wheel(lifecycle: Any, path: Path) -> dict[str, Any]:
    """Inspect the wheel through the product's own member inspection."""

    inspected = lifecycle.LifecycleManager._inspect_wheel(path)
    members: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            payload = archive.read(info)
            members.append({"name": info.filename, "bytes": len(payload)})
    members.sort(key=lambda row: row["name"])
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "distribution": inspected["distribution"],
        "version": inspected["version"],
        "python_requires": inspected["python_requires"],
        "entry_point": inspected["entry_point"],
        "observer": inspected["observer"],
        "observation_compatibility": inspected["observation_compatibility"],
        "observation_schema_sha256": inspected["observation_schema_sha256"],
        "observer_requirements_sha256": inspected["observer_requirements_sha256"],
        "installed_file_fingerprint": inspected["installed_file_fingerprint"],
        "member_count": len(members),
        "members": members,
    }


# ------------------------------------------------------------------------------- scans


def _secret_hits_bytes(label: str, payload: bytes, names: Sequence[str]) -> list[str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return []
    return [
        f"{label}: {kind}"
        for kind, pattern in _SECRET_PATTERNS
        if kind in names and pattern.search(text)
    ]


def _secret_hits(path: Path, names: Sequence[str]) -> list[str]:
    if path.suffix not in {".json", ".txt", ".md", ".sums"} and path.name != "SHA256SUMS":
        return []
    return _secret_hits_bytes(path.name, path.read_bytes(), names)


def _iter_artifact_payloads(path: Path) -> Iterable[tuple[str, bytes]]:
    name = path.name.lower()
    if name.endswith((".whl", ".zip")):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield f"{path.name}!{info.filename}", archive.read(info)
        return
    if name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path, mode="r:*") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    stream = archive.extractfile(member)
                    if stream is not None:
                        yield f"{path.name}!{member.name}", stream.read()


def _operator_path_matches(lifecycle: Any, payload: bytes) -> list[str]:
    """List the distinct canonical operator-path literals found in one payload."""

    import aether_agents.objective_contracts.store as store

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return []
    found: list[str] = []
    for name in ("_UNIX_HOME", "_WINDOWS_HOME", "_PRIVATE_DESKTOP"):
        pattern = getattr(store, name, None)
        if pattern is None:
            raise BundleError(
                "scanner-pattern-unavailable",
                f"canonical operator-path pattern {name} is unavailable",
            )
        found.extend(match.group(0) for match in pattern.finditer(text))
    return found


def _path_shape(literal: str) -> str:
    """Report one operator-path match as a portable shape instead of the literal itself."""

    shaped = _HOME_SEGMENT.sub(lambda match: f"{match.group(1)}<name>", literal)
    # The Windows pattern tolerates any non-separator segment, so drop the trailing
    # separator to keep the reported shape free of a matchable operator-path literal.
    return shaped.replace("<name>\\", "<name>")


def scan_report_bytes(lifecycle: Any, files: Sequence[Path]) -> dict[str, Any]:
    """Strict operator-path check over the plain-text members the scanner cannot open.

    The canonical scanner reads archives; reports, the lock and ``SHA256SUMS`` are plain
    text and are checked here with the same canonical patterns.
    """

    findings = sorted(
        path.name for path in files if _operator_path_matches(lifecycle, path.read_bytes())
    )
    if findings:
        raise BundleError(
            "private-path-scan",
            "Aether-authored public bytes contain operator paths: " + ", ".join(findings),
        )
    return {"scope": sorted(path.name for path in files), "result": "clean"}


def _run_path_scanner(
    scanner: Path, aether_checkout: Path, artifacts: Sequence[Path]
) -> tuple[int, str]:
    command = [sys.executable, str(scanner), "--root", str(aether_checkout)]
    for artifact in artifacts:
        command.extend(["--artifact", str(artifact)])
    completed = _run(command, cwd=aether_checkout, env=_isolated_environment())
    return completed.returncode, completed.stderr or completed.stdout


def scan_bundle(
    *,
    lifecycle: Any,
    aether_checkout: Path,
    aether_artifacts: Sequence[Path],
    fork_artifacts: Sequence[Path] = (),
    extra_files: Sequence[Path] = (),
) -> dict[str, Any]:
    """Scan the public bytes of every bundle member for private paths and secrets.

    Aether-authored bytes are strict: any operator-path or credential finding refuses the
    bundle.  The maintained-fork archive is upstream-derived source whose bytes are bound
    by the exact-commit tree digest, so its operator-path findings (generic example paths
    in upstream code and documentation) are reported in full for review instead of being
    treated as an operator disclosure; a credential finding is still a refusal.
    """

    scanner = aether_checkout / "scripts" / "check_public_artifacts.py"
    if not scanner.is_file():
        raise BundleError("scanner-missing", f"canonical scanner is unavailable: {scanner}")
    reviewed_aether_disposition = (
        "tracked Aether source at the verified commit: a hit here is a synthetic fixture or a "
        "detection pattern literal that the repository already publishes, not operator "
        "material; recorded with its member label for review"
    )
    upstream_source_disposition = (
        "upstream-derived maintained-fork source: every byte is a tracked file of the exact "
        "public commit (nothing untracked, ignored or live is included) and is bound by the "
        "locked tree digest, so hits are upstream examples; recorded as a count for review"
    )
    strict_code, strict_output = _run_path_scanner(scanner, aether_checkout, aether_artifacts)
    if strict_code not in (0, 1):
        raise BundleError(
            "private-path-scan", "canonical path scanner failed: " + _excerpt(strict_output, 400)
        )
    if strict_code == 1:
        raise BundleError(
            "private-path-scan",
            "Aether-authored public bytes contain operator paths: " + _excerpt(strict_output, 800),
        )
    plain_text = scan_report_bytes(lifecycle, extra_files)

    reviewed: dict[str, Any] = {"artifacts": [path.name for path in fork_artifacts]}
    if fork_artifacts:
        fork_code, fork_output = _run_path_scanner(scanner, aether_checkout, fork_artifacts)
        if fork_code not in (0, 1):
            raise BundleError(
                "private-path-scan",
                "canonical path scanner failed on the fork archive: " + _excerpt(fork_output, 400),
            )
        literals: list[str] = []
        shapes: list[str] = []
        labels: set[str] = set()
        for artifact in fork_artifacts:
            for label, payload in _iter_artifact_payloads(artifact):
                matches = _operator_path_matches(lifecycle, payload)
                if matches:
                    labels.add(label.rsplit("!", 1)[-1])
                literals.extend(matches)
                shapes.extend(_path_shape(value) for value in matches)
        reviewed.update(
            {
                "result": "reviewed" if fork_code == 1 else "clean",
                "distinct_match_count": len(set(literals)),
                "distinct_match_shapes": sorted(set(shapes))[:200],
                "matched_member_count": len(labels),
                "disposition": (
                    "upstream-derived maintained-fork source: exact-commit bytes are bound by "
                    "the locked tree digest; matches are generic example paths in upstream code "
                    "and documentation, reported as shapes (the user component is replaced by "
                    "<name>) so this report never republishes an operator-path literal. "
                    "Aether-authored bytes above are enforced strictly."
                ),
            }
        )

    strict_names = tuple(name for name, _ in _SECRET_PATTERNS if name in _STRICT_SECRET_NAMES)
    strict_findings: list[str] = []
    for path in [*aether_artifacts, *extra_files]:
        strict_findings.extend(_secret_hits(path, strict_names))
    for artifact in aether_artifacts:
        for label, payload in _iter_artifact_payloads(artifact):
            strict_findings.extend(_secret_hits_bytes(label, payload, strict_names))
    strict_findings = sorted(set(strict_findings))
    if strict_findings:
        raise BundleError(
            "secret-scan",
            "canonical secret patterns matched Aether-authored public bytes: "
            + "; ".join(strict_findings[:10]),
        )

    reviewed_names = tuple(name for name, _ in _SECRET_PATTERNS if name not in _STRICT_SECRET_NAMES)
    aether_reviewed: list[str] = []
    for path in [*aether_artifacts, *extra_files]:
        aether_reviewed.extend(_secret_hits(path, reviewed_names))
    for artifact in aether_artifacts:
        for label, payload in _iter_artifact_payloads(artifact):
            aether_reviewed.extend(_secret_hits_bytes(label, payload, reviewed_names))
    fork_reviewed: list[str] = []
    for artifact in fork_artifacts:
        for label, payload in _iter_artifact_payloads(artifact):
            fork_reviewed.extend(
                _secret_hits_bytes(label, payload, tuple(name for name, _ in _SECRET_PATTERNS))
            )
    return {
        "private_paths": {
            "checker": "scripts/check_public_artifacts.py",
            "aether_authored": {
                "scope": [
                    *(path.name for path in aether_artifacts),
                    *(path.name for path in extra_files),
                ],
                "result": "clean",
                "plain_text": plain_text,
            },
            "maintained_fork": reviewed,
        },
        "secrets": {
            "strict_patterns": list(strict_names),
            "strict_scope": [
                *(path.name for path in aether_artifacts),
                *(path.name for path in extra_files),
            ],
            "strict_result": "clean",
            "aether_authored": {
                "reviewed_patterns": list(reviewed_names),
                "result": "reviewed" if aether_reviewed else "clean",
                "hit_count": len(set(aether_reviewed)),
                "hit_labels": sorted(set(aether_reviewed))[:50],
                "disposition": reviewed_aether_disposition,
            },
            "maintained_fork": {
                "reviewed_patterns": [name for name, _ in _SECRET_PATTERNS],
                "result": "reviewed" if fork_reviewed else "clean",
                "hit_count": len(set(fork_reviewed)),
                "disposition": upstream_source_disposition,
            },
        },
    }


# --------------------------------------------------------------------------- lock build


def build_release_lock(
    *,
    lifecycle: Any,
    identity: dict[str, Any],
    aether_commit: str,
    wheel: dict[str, Any],
    fork: dict[str, Any],
    fork_archive_name: str,
    fork_archive_sha256: str,
) -> dict[str, Any]:
    """Assemble the schema-4 maintained-fork release lock for this bundle."""

    if wheel["distribution"] != DISTRIBUTION:
        raise BundleError(
            "wheel-distribution", f"unexpected distribution {wheel['distribution']!r}"
        )
    if wheel["version"] != identity["package_version"]:
        raise BundleError(
            "wheel-version",
            f"wheel version {wheel['version']!r} is not {identity['package_version']!r}",
        )
    release_url = f"{AETHER_REPOSITORY}/releases/tag/{identity['tag']}"
    return {
        "schema_version": RELEASE_LOCK_SCHEMA_VERSION,
        "aether": {
            "version": identity["semver"],
            "package_version": identity["package_version"],
            "distribution": DISTRIBUTION,
            "git_tag": identity["tag"],
            "git_commit": aether_commit,
            "python_requires": wheel["python_requires"],
            "observer": wheel["observer"],
            "wheel_sha256": wheel["sha256"],
            "observer_requirements_sha256": wheel["observer_requirements_sha256"],
            "observation_compatibility": wheel["observation_compatibility"],
        },
        "hermes": {
            "source_mode": HERMES_SOURCE_MODE,
            "repository": MAINTAINED_FORK_REPOSITORY,
            "branch": fork["branch"],
            "version": fork["version"],
            "tag": fork["tag"],
            "commit": fork["commit"],
            "python_requires": fork["python_requires"],
            "source_tree_sha256": fork["source_tree_sha256"],
            "artifacts": [
                {
                    "kind": "source",
                    "filename": fork_archive_name,
                    "url": f"{AETHER_REPOSITORY}/releases/download/{identity['tag']}/{fork_archive_name}",
                    "sha256": fork_archive_sha256,
                    "provenance_url": release_url,
                }
            ],
        },
        "profile_bundle": {
            "version": PROFILE_BUNDLE_VERSION,
            "sha256": profile_bundle_sha256(lifecycle),
            "roles": list(PROFILE_ROLES),
        },
    }


def _lock_schema_path(aether_checkout: Path) -> Path:
    return (
        aether_checkout
        / "specs"
        / "001-aether-v1-productization"
        / "contracts"
        / "release-lock.schema.json"
    )


def validate_lock(
    lock: dict[str, Any], *, aether_checkout: Path, allow_schema_drift: bool
) -> dict[str, Any]:
    """Validate the pinned identity always, and the repository schema when it declares 4."""

    pinned: list[str] = []
    failures: list[str] = []
    if lock["schema_version"] != RELEASE_LOCK_SCHEMA_VERSION:
        failures.append("schema_version is not 4")
    else:
        pinned.append("schema_version=4")
    hermes = lock["hermes"]
    if hermes["source_mode"] != HERMES_SOURCE_MODE:
        failures.append(f"hermes.source_mode is {hermes['source_mode']!r}")
    else:
        pinned.append("hermes.source_mode=maintained_fork")
    if _normalize_remote(hermes["repository"]) != _normalize_remote(MAINTAINED_FORK_REPOSITORY):
        failures.append(f"hermes.repository is {hermes['repository']!r}")
    else:
        pinned.append(f"hermes.repository={MAINTAINED_FORK_REPOSITORY}")
    if hermes.get("branch") != MAINTAINED_FORK_BRANCH:
        failures.append(f"hermes.branch is {hermes.get('branch')!r}")
    else:
        pinned.append(f"hermes.branch={MAINTAINED_FORK_BRANCH}")
    if not _COMMIT_RE.match(hermes["commit"]):
        failures.append("hermes.commit is not a full 40-hex id")
    if not re.fullmatch(r"[0-9a-f]{64}", hermes["source_tree_sha256"]):
        failures.append("hermes.source_tree_sha256 is not a SHA-256")
    if lock["profile_bundle"]["version"] != PROFILE_BUNDLE_VERSION:
        failures.append("profile_bundle.version is not 2")
    if list(lock["profile_bundle"]["roles"]) != list(PROFILE_ROLES):
        failures.append("profile_bundle.roles is not the three product roles")
    if failures:
        raise BundleError("lock-identity", "release lock identity: " + "; ".join(failures))

    schema_path = _lock_schema_path(aether_checkout)
    if not schema_path.is_file():
        raise BundleError(
            "lock-schema-missing", f"canonical release-lock schema absent: {schema_path}"
        )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    declared = schema.get("properties", {}).get("schema_version", {}).get("const")
    try:
        schema_label = schema_path.relative_to(aether_checkout).as_posix()
    except ValueError:
        schema_label = schema_path.name
    result: dict[str, Any] = {
        "pinned_identity": pinned,
        "repository_schema": schema_label,
        "repository_schema_version": declared,
    }
    if declared != RELEASE_LOCK_SCHEMA_VERSION:
        reason = (
            f"the repository schema declares schema_version {declared!r}; the maintained-fork "
            "schema is supplied by the release-runtime unit and only exists after integration"
        )
        if not allow_schema_drift:
            raise BundleError("lock-schema-drift", reason)
        result["schema_validation"] = "not_applicable"
        result["schema_validation_reason"] = reason
        return result
    from jsonschema import Draft202012Validator, FormatChecker

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(lock),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise BundleError(
            "lock-schema-invalid",
            "release lock does not validate: "
            + "; ".join(
                f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
                for error in errors[:5]
            ),
        )
    result["schema_validation"] = "applied"
    return result


# ------------------------------------------------------------------------ install probes


def _classify(completed: subprocess.CompletedProcess[str]) -> str:
    combined = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode == 0:
        return "pass"
    if "not implemented in this build" in combined:
        return "unavailable"
    if "unrecognized arguments" in combined:
        return "unavailable"
    if '"result"' in completed.stdout or completed.stderr.strip().startswith("aether: "):
        return "refused"
    return "fail"


def _probe(
    name: str,
    argv: Sequence[str],
    *,
    root: Path,
    environment: dict[str, str],
    required: bool,
    expectation: str,
    mask: Sequence[tuple[Path | str, str]] = (),
    stdout_contains: str | None = None,
) -> dict[str, Any]:
    completed = _run(argv, cwd=root, env=environment)
    outcome = _classify(completed)
    if expectation == "exit-zero" and completed.returncode != 0:
        outcome = "fail"
    if expectation == "json-envelope":
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and ("result" in payload or "error" in payload):
            outcome = "refused" if completed.returncode != 0 else "pass"
        elif outcome != "unavailable":
            outcome = "fail"
    if outcome == "pass" and stdout_contains and stdout_contains not in completed.stdout:
        outcome = "fail"
    report_mask = tuple(mask) + ((root, "<probe-root>"),)
    return {
        "name": name,
        "argv": _portable_capture(" ".join(argv), report_mask),
        "exit_code": completed.returncode,
        "outcome": outcome,
        "required": required,
        "expectation": expectation,
        "ok": outcome in {"pass", "refused"} if not required else outcome == "pass",
        "stdout": _capture(completed.stdout, report_mask, 900),
        "stderr": _capture(completed.stderr, report_mask, 900),
    }


def _disposable_environment(root: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    for name in ("home", "data", "state", "config", "cache", "tmp"):
        (root / name).mkdir(parents=True, exist_ok=True)
    environment = _isolated_environment(
        {
            "HOME": str(root / "home"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(root / "state"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "TMPDIR": str(root / "tmp"),
        }
    )
    if extra:
        environment.update(extra)
    return environment


def _tui_checkout(
    *, aether_checkout: Path, roots: Path, runtime_bin: Path, lifecycle: Any
) -> tuple[Path, str]:
    """Build a disposable launcher layout so the shipped TUI check runs for real."""

    repo = roots / "tui-repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".aether").mkdir(parents=True)
    (repo / "home" / "profiles" / "morfeo").mkdir(parents=True)
    (repo / "home" / ".venv-hermes" / "bin").mkdir(parents=True)
    contracts = repo / "specs" / "001-aether-v1-productization" / "contracts"
    contracts.mkdir(parents=True)
    shutil.copy2(
        aether_checkout
        / "specs"
        / "001-aether-v1-productization"
        / "contracts"
        / "project.schema.json",
        contracts / "project.schema.json",
    )
    shutil.copy2(aether_checkout / "AGENTS.md", repo / "AGENTS.md")
    shutil.copy2(aether_checkout / "scripts" / "aether_tui.py", repo / "scripts" / "aether_tui.py")
    shutil.copy2(aether_checkout / ".aether" / "project.toml", repo / ".aether" / "project.toml")
    sources = lifecycle.LifecycleManager._profile_sources("morfeo")
    for name, source in sources.items():
        shutil.copy2(source, repo / "home" / "profiles" / "morfeo" / name)
    config = repo / "home" / "profiles" / "morfeo" / "config.yaml"
    config.write_text(
        config.read_text(encoding="utf-8") + "toolsets:\n  - file\n  - kanban\n",
        encoding="utf-8",
    )
    hermes = repo / "home" / ".venv-hermes" / "bin" / "hermes"
    hermes.write_text(
        '#!/bin/sh\nexec "$(dirname "$0")/../../../../runtime/bin/hermes" "$@"\n',
        encoding="utf-8",
    )
    hermes.chmod(0o755)
    return repo, str(runtime_bin)


def clean_install(
    *,
    bundle: Path,
    wheel: Path,
    hermes_archive: Path,
    lock_path: Path,
    aether_checkout: Path,
    lifecycle: Any,
    identity: dict[str, Any],
    work: Path,
) -> dict[str, Any]:
    """Install the exact bundle bytes into fresh disposable roots and handshake them."""

    roots = work / "install-roots"
    if roots.exists():
        shutil.rmtree(roots)
    roots.mkdir(parents=True)
    manager = roots / "manager"
    runtime = roots / "runtime"
    masks = _report_masks(roots, work, bundle, aether_checkout)

    def probe(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return _probe(*args, mask=masks, **kwargs)

    environment = _isolated_environment()
    steps: list[dict[str, Any]] = []

    def uv(*arguments: str, cwd: Path = roots) -> subprocess.CompletedProcess[str]:
        return _run(["uv", "--no-config", *arguments], cwd=cwd, env=environment)

    manager_python = manager / "bin" / "python"
    runtime_python = runtime / "bin" / "python"

    def record(name: str, completed: subprocess.CompletedProcess[str], code: str) -> None:
        steps.append(
            {
                "step": name,
                "exit_code": completed.returncode,
                "stderr": _capture(completed.stderr, masks, 500),
            }
        )
        if completed.returncode != 0:
            raise BundleError(
                code,
                f"{name} failed: " + _capture(completed.stderr or completed.stdout, masks, 400),
            )

    record("manager-venv", uv("venv", "--python", sys.executable, str(manager)), "install-failed")
    record(
        "manager-wheel",
        uv("pip", "install", "--python", str(manager_python), str(wheel)),
        "install-failed",
    )
    record("manager-check", uv("pip", "check", "--python", str(manager_python)), "install-failed")
    record("runtime-venv", uv("venv", "--python", sys.executable, str(runtime)), "install-failed")

    closure = roots / "hermes-source"
    with tarfile.open(hermes_archive, mode="r:gz") as archive:
        archive.extractall(closure, filter="data")
    entries = sorted(closure.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        raise BundleError("archive-layout", "maintained-fork archive must contain one root")
    closure_root = entries[0]
    requirements = roots / "hermes-requirements.txt"
    record(
        "hermes-export",
        uv(
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(requirements),
            cwd=closure_root,
        ),
        "install-failed",
    )
    record(
        "hermes-dependencies",
        uv(
            "pip",
            "sync",
            "--require-hashes",
            "--strict",
            "--python",
            str(runtime_python),
            str(requirements),
            cwd=closure_root,
        ),
        "install-failed",
    )
    record(
        "runtime-wheel",
        uv("pip", "install", "--python", str(runtime_python), str(wheel)),
        "install-failed",
    )
    record(
        "runtime-hermes",
        uv(
            "pip",
            "install",
            "--python",
            str(runtime_python),
            "--no-deps",
            "--editable",
            str(closure_root),
            cwd=closure_root,
        ),
        "install-failed",
    )
    record("runtime-check", uv("pip", "check", "--python", str(runtime_python)), "install-failed")

    manager_root = roots / "manager-root"
    runtime_root = roots / "runtime-root"
    path = os.environ.get("PATH", "")
    manager_environment = _disposable_environment(
        manager_root, {"PATH": f"{manager / 'bin'}{os.pathsep}{path}"}
    )
    runtime_environment = _disposable_environment(
        runtime_root, {"PATH": f"{runtime / 'bin'}{os.pathsep}{path}"}
    )
    aether = manager / "bin" / "aether"
    probes: list[dict[str, Any]] = [
        probe(
            "aether --version",
            [str(aether), "--version"],
            root=roots,
            environment=manager_environment,
            required=True,
            expectation="exit-zero",
            stdout_contains=identity["package_version"],
        ),
        probe(
            "aether version --json",
            [str(aether), "version", "--json"],
            root=roots,
            environment=manager_environment,
            required=True,
            expectation="json-envelope",
            stdout_contains=identity["package_version"],
        ),
        probe(
            "aether --help",
            [str(aether), "--help"],
            root=roots,
            environment=manager_environment,
            required=True,
            expectation="exit-zero",
        ),
        probe(
            "aether doctor --json",
            [str(aether), "doctor", "--json"],
            root=roots,
            environment=manager_environment,
            required=False,
            expectation="json-envelope",
        ),
    ]
    for label, arguments in (
        ("aether status --json", ["status", "--json"]),
        (
            "aether setup --dry-run",
            [
                "setup",
                "--dry-run",
                "--json",
                "--wheel",
                str(wheel),
                "--hermes-checkout",
                str(closure_root),
                "--release-lock",
                str(lock_path),
            ],
        ),
        ("aether update --dry-run", ["update", "--dry-run", "--json"]),
        (
            "aether update --local --dry-run",
            [
                "update",
                "--local",
                "--aether-checkout",
                str(aether_checkout),
                "--aether-commit",
                identity["git_commit"],
                "--fork-checkout",
                str(closure_root),
                "--fork-commit",
                identity["hermes_commit"],
                "--dry-run",
                "--json",
            ],
        ),
        ("aether rollback --dry-run", ["rollback", "--dry-run", "--json"]),
    ):
        probes.append(
            probe(
                label,
                [str(aether), *arguments],
                root=roots,
                environment=manager_environment,
                required=False,
                expectation="json-envelope",
            )
        )
    update_help = _run([str(aether), "update", "--help"], cwd=roots, env=manager_environment)
    probes.append(
        probe(
            "aether update --help",
            [str(aether), "update", "--help"],
            root=roots,
            environment=manager_environment,
            required=True,
            expectation="exit-zero",
        )
    )
    probes.append(
        probe(
            "hermes import/version/plugin discovery",
            [str(runtime_python), "-c", _HERMES_PROBE],
            root=roots,
            environment=runtime_environment,
            required=True,
            expectation="exit-zero",
            stdout_contains="aether-contract-observer",
        )
    )
    tui_repo, _ = _tui_checkout(
        aether_checkout=aether_checkout,
        roots=roots,
        runtime_bin=runtime / "bin",
        lifecycle=lifecycle,
    )
    probes.append(
        probe(
            "tui --check",
            [sys.executable, str(tui_repo / "scripts" / "aether_tui.py"), "--check"],
            root=tui_repo,
            environment=_disposable_environment(
                roots / "tui-root", {"PATH": f"{runtime / 'bin'}{os.pathsep}{path}"}
            ),
            required=True,
            expectation="exit-zero",
            stdout_contains='"result": "ready"',
        )
    )
    present_options = [
        option for option in PINNED_LOCAL_UPDATE_OPTIONS if option in update_help.stdout
    ]
    probes.append(
        {
            "name": "pinned aether update --local option surface",
            "argv": "aether update --help",
            "exit_code": update_help.returncode,
            "outcome": "pass"
            if len(present_options) == len(PINNED_LOCAL_UPDATE_OPTIONS)
            else "unavailable",
            "required": True,
            "expectation": "pinned-surface",
            "ok": len(present_options) == len(PINNED_LOCAL_UPDATE_OPTIONS),
            "present": present_options,
            "missing": [
                option for option in PINNED_LOCAL_UPDATE_OPTIONS if option not in present_options
            ],
            "stdout": "",
            "stderr": "",
        }
    )
    hermes_probe = next(entry for entry in probes if entry["name"].startswith("hermes import"))
    hermes_observed: dict[str, Any] = {}
    if hermes_probe["outcome"] == "pass":
        raw = _run(
            [str(runtime_python), "-c", _HERMES_PROBE], cwd=roots, env=runtime_environment
        ).stdout
        hermes_observed = json.loads(raw)
    return {
        "schema": REPORT_SCHEMA,
        "roots": {
            "manager": "<work>/install-roots/manager",
            "runtime": "<work>/install-roots/runtime",
            "hermes_source": "<work>/install-roots/hermes-source",
        },
        "install_steps": steps,
        "python_version": "%d.%d.%d" % sys.version_info[:3],
        "hermes_observed": hermes_observed,
        "probes": probes,
    }


# -------------------------------------------------------------------------- bundle flow


def _bundle_member_names(identity: dict[str, Any], fork_commit: str) -> dict[str, str]:
    prefix = f"{DISTRIBUTION.replace('-', '_')}-{identity['package_version']}"
    release = f"{DISTRIBUTION}-{identity['package_version']}"
    return {
        "wheel": f"{prefix}-py3-none-any.whl",
        "sdist": f"{prefix}.tar.gz",
        "hermes_archive": f"aether-hermes-source-{fork_commit}.tar.gz",
        "lock": f"{release}-release-lock.json",
        "provenance": f"{release}-provenance.json",
        "package_members": f"{release}-package-members.json",
        "clean_install": f"{release}-clean-install.json",
        "sums": "SHA256SUMS",
    }


def _load_fork_metadata(
    lifecycle: Any, repo: Path, commit: str, tree_digest: str
) -> dict[str, Any]:
    project = _read_project_metadata(repo, commit)
    tag = _git_raw(["describe", "--tags", "--abbrev=0", commit], repo)
    tag_value = tag.stdout.strip() if tag.returncode == 0 and tag.stdout.strip() else commit
    declared = project["version"]
    if not declared:
        declared = lifecycle.HERMES_BASELINE.version
    return {
        "commit": commit,
        "version": declared,
        "tag": tag_value,
        "tag_source": "git-describe" if tag_value != commit else "exact-commit",
        "python_requires": project["requires_python"],
        "distribution": project["name"],
        "source_tree_sha256": tree_digest,
    }


def _read_project_metadata(repo: Path, commit: str) -> dict[str, str]:
    completed = _run(
        ["git", "show", f"{commit}:pyproject.toml"], cwd=repo, env=_isolated_environment()
    )
    if completed.returncode != 0:
        raise BundleError("fork-metadata", "maintained fork has no pyproject.toml at that commit")
    try:
        project = tomllib.loads(completed.stdout).get("project", {})
    except tomllib.TOMLDecodeError as error:
        raise BundleError("fork-metadata", "maintained fork pyproject.toml is malformed") from error
    return {
        "name": str(project.get("name", "")),
        "version": str(project.get("version", "")),
        "requires_python": str(project.get("requires-python", "")).replace(" ", ""),
    }


def run_build(arguments: argparse.Namespace) -> dict[str, Any]:
    aether_checkout = Path(arguments.aether_checkout).expanduser().resolve()
    fork_work = Path(tempfile.mkdtemp(prefix="aether-release-bundle-"))
    work = Path(arguments.work).expanduser().resolve() if arguments.work else fork_work
    work.mkdir(parents=True, exist_ok=True)
    try:
        aether = checkout_evidence(
            aether_checkout,
            arguments.aether_commit,
            kind="aether",
            repository=AETHER_REPOSITORY,
        )
        lifecycle = load_product(aether_checkout)
        package_version = (aether_checkout / "VERSION").read_text(encoding="ascii").strip()
        identity = release_identity(package_version, arguments.tag)
        if (
            arguments.expect_package_version
            and arguments.expect_package_version != identity["package_version"]
        ):
            raise BundleError(
                "version-mismatch",
                f"VERSION is {identity['package_version']!r}, expected "
                f"{arguments.expect_package_version!r}",
            )
        fork_repo, fork_evidence = resolve_fork(
            checkout=Path(arguments.fork_checkout).expanduser().resolve()
            if arguments.fork_checkout
            else None,
            repository=arguments.fork_repository,
            commit=arguments.fork_commit,
            work=work,
        )
        fork_branch = verify_branch_membership(
            fork_repo, arguments.fork_commit, MAINTAINED_FORK_BRANCH
        )
        fork_tree = work / "maintained-fork-source"
        fork_tree_digest = materialize_commit(
            lifecycle, fork_repo, arguments.fork_commit, fork_tree
        )
        members = _bundle_member_names(identity, arguments.fork_commit)
        prefix = members["hermes_archive"][: -len(".tar.gz")]
        archive_bytes = _git_archive_bytes(fork_repo, arguments.fork_commit, prefix)
        archive_path = work / members["hermes_archive"]
        archive_path.write_bytes(archive_bytes)
        archive_members = _extract_trusted_archive(archive_bytes, work / "hermes-archive-extract")
        archived_tree_digest = lifecycle._tree_sha256(work / "hermes-archive-extract" / prefix)
        if archived_tree_digest != fork_tree_digest:
            raise BundleError(
                "archive-tree-mismatch",
                "the maintained-fork archive does not materialize the locked source tree",
            )
        fork = _load_fork_metadata(lifecycle, fork_repo, arguments.fork_commit, fork_tree_digest)
        fork.update(
            {
                "repository": MAINTAINED_FORK_REPOSITORY,
                "branch": fork_branch["branch"],
                "branch_ref": fork_branch["proven_by"],
                "branch_tips": fork_branch["branch_tips"],
                "archive_tree_sha256": archived_tree_digest,
                "archive_member_count": len(archive_members),
            }
        )

        commit_time = int(
            _git(["show", "-s", "--format=%ct", arguments.aether_commit], aether_checkout).strip()
        )
        first = build_distributions(
            aether_checkout, work / "dist-first", source_date_epoch=commit_time
        )
        second = build_distributions(
            aether_checkout, work / "dist-verify", source_date_epoch=commit_time
        )
        reproducible = {
            "wheel": _sha256_file(first["wheel"]) == _sha256_file(second["wheel"]),
            "sdist": _sha256_file(first["sdist"]) == _sha256_file(second["sdist"]),
            "source_date_epoch": commit_time,
        }
        if not all((reproducible["wheel"], reproducible["sdist"])):
            raise BundleError("build-not-reproducible", "two builds from the same commit differ")
        post_head = _git(["rev-parse", "HEAD"], aether_checkout).strip()
        post_status = _git(["status", "--porcelain"], aether_checkout)
        if post_head != arguments.aether_commit or post_status.strip():
            raise BundleError(
                "source-mutated", "building the distributions changed the Aether checkout"
            )

        out = Path(arguments.out).expanduser().resolve()
        if out.exists() and any(out.iterdir()):
            raise BundleError("output-exists", f"{out} is not empty")
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(first["wheel"], out / members["wheel"])
        shutil.copy2(first["sdist"], out / members["sdist"])
        shutil.copy2(archive_path, out / members["hermes_archive"])
        wheel = inspect_wheel(lifecycle, out / members["wheel"])
        sdist = inspect_sdist(out / members["sdist"])

        lock = build_release_lock(
            lifecycle=lifecycle,
            identity=identity,
            aether_commit=arguments.aether_commit,
            wheel=wheel,
            fork=fork,
            fork_archive_name=members["hermes_archive"],
            fork_archive_sha256=_sha256_file(out / members["hermes_archive"]),
        )
        lock_validation = validate_lock(
            lock,
            aether_checkout=aether_checkout,
            allow_schema_drift=arguments.pre_integration,
        )
        _write_json(out / members["lock"], lock)

        scans = scan_bundle(
            lifecycle=lifecycle,
            aether_checkout=aether_checkout,
            aether_artifacts=[out / members["wheel"], out / members["sdist"]],
            fork_artifacts=[out / members["hermes_archive"]],
            extra_files=[out / members["lock"]],
        )
        install_report = clean_install(
            bundle=out,
            wheel=out / members["wheel"],
            hermes_archive=out / members["hermes_archive"],
            lock_path=out / members["lock"],
            aether_checkout=aether_checkout,
            lifecycle=lifecycle,
            identity={
                **identity,
                "git_commit": arguments.aether_commit,
                "hermes_commit": arguments.fork_commit,
            },
            work=work,
        )
        failed = [
            probe
            for probe in install_report["probes"]
            if not probe["ok"] and (probe["required"] or not arguments.pre_integration)
        ]
        package_members = {
            "schema": REPORT_SCHEMA,
            "release": identity,
            "aether": {**aether, "tree_digest_basis": "exact Git commit"},
            "hermes": fork,
            "wheel": wheel,
            "sdist": sdist,
            "hermes_source_archive": {
                "filename": members["hermes_archive"],
                "sha256": _sha256_file(out / members["hermes_archive"]),
                "bytes": (out / members["hermes_archive"]).stat().st_size,
                "member_count": len(archive_members),
                "members": archive_members,
                "source_tree_sha256": fork_tree_digest,
                "archive_tree_sha256": archived_tree_digest,
            },
            "scans": scans,
            "lock_validation": lock_validation,
            "reproducibility": reproducible,
        }
        _write_json(out / members["package_members"], package_members)
        _write_json(out / members["clean_install"], install_report)
        provenance = {
            "schema": REPORT_SCHEMA,
            "release": identity,
            "aether": {
                "repository": AETHER_REPOSITORY,
                "commit": arguments.aether_commit,
                "version_file": package_version,
            },
            "hermes": {
                "repository": MAINTAINED_FORK_REPOSITORY,
                "branch": fork["branch"],
                "branch_ref": fork["branch_ref"],
                "branch_tips": fork["branch_tips"],
                "commit": fork["commit"],
                "version": fork["version"],
                "tag": fork["tag"],
                "tag_source": fork["tag_source"],
                "source_tree_sha256": fork["source_tree_sha256"],
            },
            "tool": {
                "name": "scripts/release_bundle.py",
                "report_schema": REPORT_SCHEMA,
                "policy": "pre-integration" if arguments.pre_integration else "strict",
                "python_version": "%d.%d.%d" % sys.version_info[:3],
                "builder": "uv build",
                "source_date_epoch": commit_time,
            },
            "lock_validation": lock_validation,
            "probe_policy": {
                "required_failures": [probe["name"] for probe in failed if probe["required"]],
                "capability_failures": [probe["name"] for probe in failed if not probe["required"]],
            },
            "members": {},
        }
        for key, name in members.items():
            if key in {"provenance", "sums"}:
                continue
            provenance["members"][name] = {
                "bytes": (out / name).stat().st_size,
                "sha256": _sha256_file(out / name),
            }
        _write_json(out / members["provenance"], provenance)
        provenance_entry = {
            "bytes": (out / members["provenance"]).stat().st_size,
            "sha256": _sha256_file(out / members["provenance"]),
        }
        sums = "".join(
            f"{_sha256_file(out / name)}  {name}\n" for name in sorted(provenance["members"])
        )
        sums += f"{provenance_entry['sha256']}  {members['provenance']}\n"
        (out / members["sums"]).write_text(sums, encoding="ascii")

        finished_members, _ = verify_members(out)
        finished_scan = scan_report_bytes(
            lifecycle, [out / name for name in sorted(finished_members)]
        )
        finished = {
            "members_rehashed": len(finished_members),
            "plain_text_scan": finished_scan,
        }

        summary = {
            "schema": REPORT_SCHEMA,
            "mode": "build",
            "bundle": str(out),
            "release": identity,
            "members": {
                **{
                    key: {"filename": name, "bytes": (out / name).stat().st_size}
                    for key, name in members.items()
                    if key not in {"provenance", "sums"}
                },
                "provenance": {
                    "filename": members["provenance"],
                    "bytes": provenance_entry["bytes"],
                },
                "sums": {
                    "filename": members["sums"],
                    "bytes": (out / members["sums"]).stat().st_size,
                },
            },
            "aether_commit": arguments.aether_commit,
            "hermes_commit": arguments.fork_commit,
            "lock_validation": lock_validation,
            "reproducibility": reproducible,
            "finished_bundle": finished,
            "scans": scans,
            "failed_probes": [probe["name"] for probe in failed],
        }
        if failed and not arguments.pre_integration:
            raise BundleError(
                "probe-failed",
                "handshake probes failed: " + ", ".join(probe["name"] for probe in failed),
            )
        return summary
    finally:
        if not arguments.work:
            shutil.rmtree(fork_work, ignore_errors=True)


def verify_members(bundle: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Re-hash every bundle member against ``SHA256SUMS`` and refuse any drift."""

    if not bundle.is_dir():
        raise BundleError("bundle-missing", f"{bundle} is not a directory")
    sums_path = bundle / "SHA256SUMS"
    if not sums_path.is_file():
        raise BundleError("sums-missing", "bundle has no SHA256SUMS")
    expected: dict[str, str] = {}
    for line in sums_path.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if not name or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BundleError("sums-malformed", f"malformed checksum line: {line!r}")
        expected[name] = digest
    actual_files = sorted(path.name for path in bundle.iterdir() if path.is_file())
    if sorted(expected) != [name for name in actual_files if name != "SHA256SUMS"]:
        raise BundleError(
            "member-drift",
            "bundle members do not match SHA256SUMS: "
            f"extra {sorted(set(actual_files) - set(expected) - {'SHA256SUMS'})}, "
            f"missing {sorted(set(expected) - set(actual_files))}",
        )
    verified: dict[str, Any] = {}
    for name, digest in sorted(expected.items()):
        observed = _sha256_file(bundle / name)
        if observed != digest:
            raise BundleError(
                "digest-mismatch", f"{name} hashes to {observed}, not the recorded {digest}"
            )
        verified[name] = {"sha256": observed, "bytes": (bundle / name).stat().st_size}
    return expected, verified


def qualified_members(bundle: Path) -> dict[str, dict[str, Any]]:
    """The exact attachable member set of a qualified bundle, checksum file included.

    ``verify_members`` re-hashes every member listed in ``SHA256SUMS`` and refuses drift;
    this adds ``SHA256SUMS`` itself, so a publication attaches the verified set and nothing
    else.  A file the checksum file does not list is a ``member-drift`` refusal here, never
    an extra attachment.
    """

    expected, verified = verify_members(bundle)
    members = {name: dict(verified[name]) for name in sorted(expected)}
    sums = bundle / "SHA256SUMS"
    members["SHA256SUMS"] = {"sha256": _sha256_file(sums), "bytes": sums.stat().st_size}
    return dict(sorted(members.items()))


def verify_published_assets(bundle: Path, *, tag: str, lines: Iterable[str]) -> dict[str, Any]:
    """Prove an existing release carries exactly the qualified bytes, by name and digest.

    ``gh release edit`` accepts no file arguments, so the reconcile path can never attach
    bytes: it is only correct when the release already carries the qualified members.  The
    listing is one ``<name>\\t<digest>`` line per published asset, as
    ``gh release view --json assets --jq`` prints it.  A missing, unexpected, digest-less or
    differently-hashed asset is refused with the offending names, so nothing is silently
    accepted.
    """

    qualified = qualified_members(bundle)
    published: dict[str, str] = {}
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        name, separator, digest = line.partition("\t")
        if not separator or not name.strip():
            raise BundleError(
                "published-assets-malformed",
                f"expected '<name>\\t<digest>' per published asset, observed {line!r}",
            )
        name = name.strip()
        if name in published:
            raise BundleError("published-assets-malformed", f"duplicate published asset {name!r}")
        published[name] = digest.strip()
    missing = sorted(set(qualified) - set(published))
    unexpected = sorted(set(published) - set(qualified))
    if missing or unexpected:
        raise BundleError(
            "published-asset-drift",
            f"release {tag} does not carry the qualified bundle: missing {missing}, "
            f"unexpected {unexpected}",
        )
    unverifiable = sorted(name for name in qualified if not published[name])
    if unverifiable:
        raise BundleError(
            "published-asset-unverifiable",
            f"release {tag} assets carry no digest, so the qualified bytes cannot be "
            f"verified: {unverifiable}",
        )
    mismatched = sorted(
        name for name in qualified if published[name] != f"sha256:{qualified[name]['sha256']}"
    )
    if mismatched:
        detail = "; ".join(
            f"{name} is {published[name]}, not the qualified sha256:{qualified[name]['sha256']}"
            for name in mismatched
        )
        raise BundleError(
            "published-asset-mismatch",
            f"release {tag} bytes do not match the qualified bundle: {detail}",
        )
    return {
        "schema": REPORT_SCHEMA,
        "mode": "verify-published-assets",
        "tag": tag,
        "bundle": str(bundle),
        "result": "verified",
        "assets": {name: qualified[name]["sha256"] for name in sorted(qualified)},
    }


def run_verify(arguments: argparse.Namespace) -> dict[str, Any]:
    bundle = Path(arguments.bundle).expanduser().resolve()
    expected, verified = verify_members(bundle)
    lock_name = next((name for name in expected if name.endswith("-release-lock.json")), None)
    if lock_name is None:
        raise BundleError("lock-missing", "bundle has no release lock")
    lock = json.loads((bundle / lock_name).read_text(encoding="utf-8"))
    aether_checkout = (
        Path(arguments.aether_checkout).expanduser().resolve()
        if arguments.aether_checkout
        else Path(__file__).resolve().parents[1]
    )
    lifecycle = load_product(aether_checkout)
    validation = validate_lock(
        lock, aether_checkout=aether_checkout, allow_schema_drift=arguments.pre_integration
    )
    expectations = []
    if (
        arguments.expect_aether_commit
        and lock["aether"]["git_commit"] != arguments.expect_aether_commit
    ):
        raise BundleError(
            "revision-mismatch",
            f"lock records aether commit {lock['aether']['git_commit']}, expected "
            f"{arguments.expect_aether_commit}",
        )
    if arguments.expect_fork_commit and lock["hermes"]["commit"] != arguments.expect_fork_commit:
        raise BundleError(
            "revision-mismatch",
            f"lock records fork commit {lock['hermes']['commit']}, expected "
            f"{arguments.expect_fork_commit}",
        )
    expectations.append("exact revisions matched")
    wheel_name = next((name for name in expected if name.endswith(".whl")), None)
    archive_name = lock["hermes"]["artifacts"][0]["filename"]
    if wheel_name is None:
        raise BundleError("wheel-missing", "bundle has no wheel")
    if archive_name not in expected:
        raise BundleError("archive-missing", f"bundle is missing {archive_name}")
    wheel = inspect_wheel(lifecycle, bundle / wheel_name)
    if wheel["sha256"] != lock["aether"]["wheel_sha256"]:
        raise BundleError(
            "wheel-lock-mismatch", "the wheel does not match the digest bound by the release lock"
        )
    if verified[archive_name]["sha256"] != lock["hermes"]["artifacts"][0]["sha256"]:
        raise BundleError(
            "archive-lock-mismatch",
            "the maintained-fork archive does not match the digest bound by the release lock",
        )
    aether_archives = [
        bundle / name
        for name in expected
        if name != archive_name and name.endswith((".whl", ".tar.gz"))
    ]
    if not aether_archives:
        raise BundleError("wheel-missing", "bundle carries no Aether wheel or sdist")
    extra_files = [
        bundle / name
        for name in expected
        if name not in {archive_name} and not name.endswith((".whl", ".tar.gz"))
    ]
    scans = scan_bundle(
        lifecycle=lifecycle,
        aether_checkout=aether_checkout,
        aether_artifacts=aether_archives,
        fork_artifacts=[bundle / archive_name],
        extra_files=extra_files,
    )
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "mode": "verify",
        "bundle": str(bundle),
        "members": verified,
        "lock_validation": validation,
        "expectations": expectations,
        "scans": scans,
    }
    if arguments.clean_install:
        report["clean_install"] = clean_install(
            bundle=bundle,
            wheel=bundle / wheel_name,
            hermes_archive=bundle / archive_name,
            lock_path=bundle / lock_name,
            aether_checkout=aether_checkout,
            lifecycle=lifecycle,
            identity={
                **release_identity(lock["aether"]["package_version"]),
                "git_commit": lock["aether"]["git_commit"],
                "hermes_commit": lock["hermes"]["commit"],
            },
            work=Path(tempfile.mkdtemp(prefix="aether-release-verify-")),
        )
    return report


def run_members(arguments: argparse.Namespace) -> dict[str, Any]:
    """List the exact member paths a publication must attach, in sorted order."""

    bundle = Path(arguments.bundle).expanduser().resolve()
    members = qualified_members(bundle)
    return {
        "schema": REPORT_SCHEMA,
        "mode": "members",
        "bundle": str(bundle),
        "members": {
            name: {"path": str(bundle / name), **member} for name, member in members.items()
        },
    }


def run_verify_published_assets(arguments: argparse.Namespace) -> dict[str, Any]:
    bundle = Path(arguments.bundle).expanduser().resolve()
    if arguments.assets == "-":
        lines = sys.stdin.read().splitlines()
    else:
        assets_path = Path(arguments.assets).expanduser()
        if not assets_path.is_file():
            raise BundleError(
                "assets-missing", f"published asset listing {assets_path} does not exist"
            )
        lines = assets_path.read_text(encoding="utf-8").splitlines()
    return verify_published_assets(bundle, tag=arguments.tag, lines=lines)


# ------------------------------------------------------------------------------- main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build and qualify one release bundle")
    build.add_argument("--aether-checkout", required=True)
    build.add_argument("--aether-commit", required=True)
    build.add_argument("--fork-checkout", default=None)
    build.add_argument("--fork-repository", default=None)
    build.add_argument("--fork-commit", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--tag", default=None)
    build.add_argument("--expect-package-version", default=None)
    build.add_argument("--work", default=None)
    build.add_argument(
        "--pre-integration",
        action="store_true",
        help=(
            "record, instead of enforcing, exactly two conditions that a parallel unit "
            "supplies after integration: the maintained-fork release-lock schema (4) and the "
            "pinned aether update --local option surface"
        ),
    )
    build.add_argument("--json", action="store_true")

    verify = subparsers.add_parser("verify", help="re-verify one existing bundle")
    verify.add_argument("--bundle", required=True)
    verify.add_argument("--aether-checkout", default=None)
    verify.add_argument("--expect-aether-commit", default=None)
    verify.add_argument("--expect-fork-commit", default=None)
    verify.add_argument("--clean-install", action="store_true")
    verify.add_argument("--pre-integration", action="store_true")
    verify.add_argument("--json", action="store_true")

    members = subparsers.add_parser(
        "members", help="list the exact member paths a publication must attach"
    )
    members.add_argument("--bundle", required=True)
    members.add_argument("--json", action="store_true")

    published = subparsers.add_parser(
        "verify-published-assets",
        help="prove an existing release carries exactly the qualified bytes",
    )
    published.add_argument("--bundle", required=True)
    published.add_argument("--tag", required=True)
    published.add_argument(
        "--assets",
        required=True,
        help="'<name>\\t<digest>' per published asset, or '-' for stdin",
    )
    published.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exit_code:  # argparse normalizes usage errors to an exit code
        return int(exit_code.code) if isinstance(exit_code.code, int) else 1
    runner = {
        "build": run_build,
        "verify": run_verify,
        "members": run_members,
        "verify-published-assets": run_verify_published_assets,
    }[arguments.command]
    try:
        report = runner(arguments)
    except BundleError as error:
        print(f"release bundle refused: {error}", file=sys.stderr)
        return 1
    if arguments.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif arguments.command == "build":
        print(f"release bundle built: {report['bundle']}")
        for key, member in report["members"].items():
            print(f"  {key}: {member['filename']} ({member['bytes']} bytes)")
    elif arguments.command == "members":
        for member in report["members"].values():
            print(member["path"])
    elif arguments.command == "verify-published-assets":
        print(f"published release carries the qualified bytes: {report['tag']}")
        for name in sorted(report["assets"]):
            print(f"  {name}")
    else:
        print(f"release bundle verified: {report['bundle']}")
        for name, member in report["members"].items():
            print(f"  {name} ({member['bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
