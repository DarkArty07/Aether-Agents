"""Transactional editable reconciliation for Hermes interpreters.

Provides one package-owned operation to reconcile editable Hermes mappings
transactionally across every provisioned interpreter, capture private backups,
verify intended module origins via env -i / python -I canaries, and roll back
metadata atomically if any interpreter fails.

Targets are inspected before anything is mutated: a clean release installation
(or a missing distribution) is refused with ``NonEditableTargetError`` and a
receipt, so this authorized dirty-runtime reconciliation never converts or
damages a non-editable interpreter. Clean release installation stays strict
and separate.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

# Files and directories ignored when computing source tree digests
_IGNORE_TREE_PATTERNS = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".coverage",
        ".eggs",
    }
)


class EditableReconciliationError(RuntimeError):
    """Raised when editable reconciliation fails or is rolled back."""

    def __init__(
        self,
        message: str,
        *,
        receipt: EditableReconciliationReceipt | None = None,
    ) -> None:
        super().__init__(message)
        self.receipt = receipt


class NonEditableTargetError(EditableReconciliationError):
    """Raised when a target interpreter's Hermes distribution is not editable.

    The reconciliation refuses such a target before mutating anything: its
    receipt reports the refusal (interpreter status ``refused``) and the other
    targets stay untouched (``not_attempted``). A clean release installation is
    never silently converted into an editable one.
    """


class ForkPackagingError(RuntimeError):
    """Raised when maintained-fork packaging metadata is inconsistent with source."""


@dataclass(frozen=True, slots=True)
class ModuleCanaryResult:
    """Canary check result for one top-level module in one interpreter."""

    module: str
    found: bool
    origin: str | None
    is_source_origin: bool
    import_ok: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "found": self.found,
            "origin": self.origin,
            "is_source_origin": self.is_source_origin,
            "import_ok": self.import_ok,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class InterpreterReconciliationReceipt:
    """Per-interpreter reconciliation receipt."""

    interpreter: str
    site_packages: str
    distribution: str
    version: str
    direct_url: dict[str, Any]
    pre_fingerprints: dict[str, str]
    post_fingerprints: dict[str, str]
    canary_results: tuple[ModuleCanaryResult, ...]
    status: str  # "reconciled" | "rolled_back" | "refused" | "not_attempted"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "interpreter": self.interpreter,
            "site_packages": self.site_packages,
            "distribution": self.distribution,
            "version": self.version,
            "direct_url": self.direct_url,
            "pre_fingerprints": self.pre_fingerprints,
            "post_fingerprints": self.post_fingerprints,
            "canary_results": [r.to_dict() for r in self.canary_results],
            "status": self.status,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class EditableReconciliationReceipt:
    """Structured receipt for one logical editable reconciliation transaction."""

    status: str  # "reconciled" | "rolled_back" | "failed"
    source_path: str
    source_tree_sha256: str
    source_git_status: str | None
    offline: bool
    interpreters: tuple[InterpreterReconciliationReceipt, ...]
    rolled_back: bool
    rollback_reason: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_path": self.source_path,
            "source_tree_sha256": self.source_tree_sha256,
            "source_git_status": self.source_git_status,
            "offline": self.offline,
            "interpreters": [i.to_dict() for i in self.interpreters],
            "rolled_back": self.rolled_back,
            "rollback_reason": self.rollback_reason,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class ForkPackagingCheckResult:
    """Outcome of maintained-fork top-level packaging inventory validation."""

    source_path: str
    declared_py_modules: tuple[str, ...]
    discovered_intentional_modules: tuple[str, ...]
    missing_from_py_modules: tuple[str, ...]
    orphaned_in_py_modules: tuple[str, ...]
    is_coherent: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "declared_py_modules": list(self.declared_py_modules),
            "discovered_intentional_modules": list(self.discovered_intentional_modules),
            "missing_from_py_modules": list(self.missing_from_py_modules),
            "orphaned_in_py_modules": list(self.orphaned_in_py_modules),
            "is_coherent": self.is_coherent,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class _TargetInspection:
    """Read-only pre-flight inspection of one target interpreter."""

    interpreter: Path
    site_packages: Path
    dist_info_dir: Path | None
    editable_files: dict[str, Path]
    direct_url: dict[str, Any]
    version: str
    is_editable: bool
    reason: str | None


@dataclass
class _InterpreterStaging:
    interpreter: Path
    site_packages: Path
    dist_info_dir: Path | None
    editable_files: dict[str, Path]
    pre_fingerprints: dict[str, str]
    backup_dir: Path
    direct_url: dict[str, Any]


def _sha256_file(path: Path) -> str:
    """Compute sha256 digest of a single regular file."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_source_tree_sha256(root: Path) -> str:
    """Digest a source tree regular files, ignoring cache and egg-info build debris."""
    resolved = root.resolve()
    rows: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(resolved, followlinks=False):
        current = Path(dirpath)
        # Filter out ignored directories in-place
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in _IGNORE_TREE_PATTERNS and not d.endswith(".egg-info") and d != "build"
        )
        for name in sorted(filenames):
            if name.endswith(".pyc") or name.endswith(".pyo"):
                continue
            path = current / name
            if path.is_file() and not path.is_symlink():
                rel = path.relative_to(resolved).as_posix()
                rows.append((rel, _sha256_file(path)))
    encoded = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_git_status(source: Path) -> str | None:
    """Read git status --porcelain for the source if in a git repository, ignoring build debris."""
    resolved = source.resolve()
    git_dir = resolved / ".git"
    if not git_dir.exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=resolved,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            lines = [
                line
                for line in completed.stdout.splitlines()
                if not (
                    line.endswith(".egg-info/")
                    or ".egg-info/" in line
                    or line.endswith("__pycache__/")
                    or "__pycache__/" in line
                )
            ]
            return "\n".join(lines) + ("\n" if lines else "")
    except OSError:
        pass
    return None


def remove_editable_build_debris(source: Path, dist_name: str | None = None) -> None:
    """Remove setuptools build debris (*.egg-info) created during editable install."""
    resolved = source.resolve()
    names_to_check = ["hermes_agent.egg-info"]
    if dist_name:
        normalized = dist_name.lower().replace("-", "_")
        names_to_check.append(f"{normalized}.egg-info")
        names_to_check.append(f"{dist_name}.egg-info")

    for entry in resolved.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            if entry.name.endswith(".egg-info") or entry.name in names_to_check:
                shutil.rmtree(entry)


def get_interpreter_site_packages(interpreter: Path) -> Path:
    """Resolve site-packages directory for an interpreter using env -i python -I."""
    resolved = interpreter.absolute()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise EditableReconciliationError(f"Interpreter {interpreter} is not an executable file")

    code = "import sysconfig; print(sysconfig.get_path('purelib'))"
    try:
        completed = subprocess.run(
            [str(resolved), "-I", "-c", code],
            capture_output=True,
            text=True,
            check=False,
            env={},
        )
    except OSError as error:
        raise EditableReconciliationError(f"Failed to execute interpreter {interpreter}") from error

    if completed.returncode != 0:
        raise EditableReconciliationError(
            f"Failed to query site-packages from {interpreter} (exit {completed.returncode}): {completed.stderr}"
        )
    sp_path = Path(completed.stdout.strip()).resolve()
    if not sp_path.is_dir():
        raise EditableReconciliationError(
            f"Resolved site-packages {sp_path} for {interpreter} is not a directory"
        )
    return sp_path


def find_editable_metadata(
    site_packages: Path,
    dist_name: str,
) -> tuple[Path | None, dict[str, Path], dict[str, Path]]:
    """Discover editable dist-info, associated files, and generated mapping artifacts.

    Returns the dist-info directory (if any), every file belonging to the editable
    metadata set (dist-info contents plus generated artifacts), and the generated
    editable mapping artifacts themselves (``__editable__*`` / ``_editable_impl_*``).
    """
    normalized = dist_name.lower().replace("-", "_")
    dist_info_dir: Path | None = None

    for entry in site_packages.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            name_lower = entry.name.lower()
            if name_lower.startswith(
                (f"{normalized}-", f"{dist_name.lower()}-")
            ) and name_lower.endswith(".dist-info"):
                dist_info_dir = entry
                break

    dist_info_files: dict[str, Path] = {}
    if dist_info_dir is not None:
        for rootpath, _, filenames in os.walk(dist_info_dir):
            for fname in filenames:
                fpath = Path(rootpath) / fname
                rel = fpath.relative_to(site_packages).as_posix()
                dist_info_files[rel] = fpath

    # Look for .pth and finder files associated with the editable distribution
    editable_artifacts: dict[str, Path] = {}
    pth_patterns = [
        f"__editable__.{dist_name}-*.pth",
        f"__editable__.{normalized}-*.pth",
        f"_editable_impl_{normalized}.pth",
        f"_editable_impl_{dist_name}.pth",
    ]
    for pattern in pth_patterns:
        for pth in site_packages.glob(pattern):
            rel = pth.relative_to(site_packages).as_posix()
            editable_artifacts[rel] = pth

    finder_patterns = [
        f"__editable___{normalized}_*_finder.py",
        f"__editable___{dist_name.lower()}_*_finder.py",
        f"__editable___*_{normalized}_finder.py",
    ]
    for pattern in finder_patterns:
        for finder in site_packages.glob(pattern):
            rel = finder.relative_to(site_packages).as_posix()
            editable_artifacts[rel] = finder

    editable_files = {**dist_info_files, **editable_artifacts}
    return dist_info_dir, editable_files, editable_artifacts


def _read_distribution_version(dist_info_dir: Path | None, fallback: str) -> str:
    """Read the ``Version`` field from a dist-info METADATA file without side effects."""
    if dist_info_dir is not None:
        metadata_path = dist_info_dir / "METADATA"
        if metadata_path.is_file():
            try:
                for line in metadata_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
            except (OSError, UnicodeDecodeError):
                pass
    return fallback


def inspect_editable_target(interpreter: Path, dist_name: str) -> _TargetInspection:
    """Inspect one interpreter's Hermes installation without mutating anything.

    Classifies the installed distribution from its PEP 610 ``direct_url`` identity
    and the generated editable mapping files. ``is_editable`` is True only for an
    installed distribution whose ``dir_info.editable`` is true or that carries
    generated ``__editable__*`` / ``_editable_impl_*`` artifacts; a clean release
    installation or a missing distribution is reported as non-editable so the
    caller can refuse it before any mutation.
    """
    site_packages = get_interpreter_site_packages(interpreter)
    dist_info_dir, editable_files, editable_artifacts = find_editable_metadata(
        site_packages, dist_name
    )

    direct_url_info: dict[str, Any] = {}
    if dist_info_dir is not None:
        direct_url_path = dist_info_dir / "direct_url.json"
        if direct_url_path.is_file():
            try:
                parsed = json.loads(direct_url_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                parsed = None
            if isinstance(parsed, dict):
                direct_url_info = parsed

    dir_info = direct_url_info.get("dir_info")
    editable_by_direct_url = isinstance(dir_info, dict) and dir_info.get("editable") is True
    editable_by_artifacts = bool(editable_artifacts)

    if dist_info_dir is None:
        is_editable = False
        reason = (
            f"{dist_name} is not installed in {interpreter}: no "
            f"{dist_name.lower().replace('-', '_')}*.dist-info in {site_packages}"
        )
    elif editable_by_direct_url or editable_by_artifacts:
        is_editable = True
        reason = None
    else:
        is_editable = False
        reason = (
            f"{dist_name} in {interpreter} is not an editable installation "
            "(no PEP 610 dir_info.editable and no generated editable mapping "
            "files); refusing to convert a clean release installation"
        )

    return _TargetInspection(
        interpreter=interpreter,
        site_packages=site_packages,
        dist_info_dir=dist_info_dir,
        editable_files=editable_files,
        direct_url=direct_url_info,
        version=_read_distribution_version(dist_info_dir, ""),
        is_editable=is_editable,
        reason=reason,
    )


def compute_file_fingerprints(files: dict[str, Path]) -> dict[str, str]:
    """Compute sha256 fingerprints for a set of relative file paths."""
    fingerprints: dict[str, str] = {}
    for rel_name, path in sorted(files.items()):
        if path.is_file() and not path.is_symlink():
            fingerprints[rel_name] = _sha256_file(path)
    return fingerprints


def create_private_backup(files: dict[str, Path], backup_dir: Path) -> None:
    """Store private backup of editable files before reconciliation."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    for rel_name, src_path in files.items():
        if src_path.is_file() and not src_path.is_symlink():
            dest = backup_dir / rel_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest)


def restore_private_backup(
    backup_dir: Path,
    site_packages: Path,
    pre_files: dict[str, Path],
    dist_name: str,
) -> None:
    """Restore private backup into site-packages, removing any new files."""
    # First, find whatever editable files exist now in site-packages
    _, current_files, _ = find_editable_metadata(site_packages, dist_name)
    # Remove files that were not in pre_files or are newly created
    for rel_name, path in current_files.items():
        if path.exists() and not path.is_symlink():
            if path.is_file():
                path.unlink(missing_ok=True)

    # Remove dist-info dirs that were created anew
    normalized = dist_name.lower().replace("-", "_")
    for entry in site_packages.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            name_lower = entry.name.lower()
            if name_lower.startswith(
                (f"{normalized}-", f"{dist_name.lower()}-")
            ) and name_lower.endswith(".dist-info"):
                shutil.rmtree(entry)

    # Now copy back everything from backup_dir
    if backup_dir.exists():
        for rootpath, _, filenames in os.walk(backup_dir):
            for fname in filenames:
                src = Path(rootpath) / fname
                rel = src.relative_to(backup_dir).as_posix()
                dest = site_packages / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)


def run_interpreter_canary(
    interpreter: Path,
    source: Path,
    expected_modules: Sequence[str],
    *,
    verify_imports: bool = True,
) -> tuple[bool, tuple[ModuleCanaryResult, ...]]:
    """Execute env -i / python -I canary verifying module resolution and origin."""
    resolved_interp = interpreter.absolute()
    resolved_source = source.resolve()

    canary_script = """
import importlib.util
import json
import os
import sys
from pathlib import Path

expected = json.loads(sys.argv[1])
source_root = Path(sys.argv[2]).resolve()
verify_import = (sys.argv[3] == "1")

results = []
all_ok = True

for mod_name in expected:
    spec = importlib.util.find_spec(mod_name)
    if spec is None:
        results.append({
            "module": mod_name,
            "found": False,
            "origin": None,
            "is_source_origin": False,
            "import_ok": False,
            "error": "find_spec returned None",
        })
        all_ok = False
        continue

    origin_str = str(spec.origin) if spec.origin else None
    if not origin_str:
        results.append({
            "module": mod_name,
            "found": True,
            "origin": None,
            "is_source_origin": False,
            "import_ok": False,
            "error": "ModuleSpec has no origin",
        })
        all_ok = False
        continue

    origin_path = Path(origin_str).resolve()
    try:
        origin_path.relative_to(source_root)
        is_source = True
    except ValueError:
        is_source = False

    if not is_source:
        results.append({
            "module": mod_name,
            "found": True,
            "origin": str(origin_path),
            "is_source_origin": False,
            "import_ok": False,
            "error": f"Origin {origin_path} not within source {source_root}",
        })
        all_ok = False
        continue

    import_ok = True
    import_err = None
    if verify_import:
        try:
            importlib.import_module(mod_name)
        except Exception as exc:
            import_ok = False
            import_err = f"{type(exc).__name__}: {exc}"
            all_ok = False

    results.append({
        "module": mod_name,
        "found": True,
        "origin": str(origin_path),
        "is_source_origin": True,
        "import_ok": import_ok,
        "error": import_err,
    })

print(json.dumps({"all_ok": all_ok, "results": results}))
"""

    args = [
        str(resolved_interp),
        "-I",
        "-c",
        canary_script,
        json.dumps(list(expected_modules)),
        str(resolved_source),
        "1" if verify_imports else "0",
    ]

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            env={},
        )
    except OSError as error:
        raise EditableReconciliationError(f"Failed to execute canary on {interpreter}") from error

    if completed.returncode != 0:
        return False, (
            ModuleCanaryResult(
                module="<canary_process>",
                found=False,
                origin=None,
                is_source_origin=False,
                import_ok=False,
                error=f"Process exited {completed.returncode}: {completed.stderr}",
            ),
        )

    try:
        payload = json.loads(completed.stdout.strip())
        results = tuple(
            ModuleCanaryResult(
                module=item["module"],
                found=item["found"],
                origin=item["origin"],
                is_source_origin=item["is_source_origin"],
                import_ok=item["import_ok"],
                error=item.get("error"),
            )
            for item in payload["results"]
        )
        return payload["all_ok"], results
    except (json.JSONDecodeError, KeyError) as error:
        return False, (
            ModuleCanaryResult(
                module="<canary_parse>",
                found=False,
                origin=None,
                is_source_origin=False,
                import_ok=False,
                error=f"Failed to parse canary output: {completed.stdout} ({error})",
            ),
        )


def check_fork_packaging_inventory(
    source: Path,
    intentional_modules: Sequence[str] | None = None,
) -> ForkPackagingCheckResult:
    """Verify that intentional top-level modules are declared in tool.setuptools.py-modules."""
    resolved_source = source.resolve()
    pyproject_path = resolved_source / "pyproject.toml"
    if not pyproject_path.is_file():
        raise ForkPackagingError(f"pyproject.toml missing in {source}")

    with pyproject_path.open("rb") as handle:
        data = tomllib.load(handle)

    tool_setuptools = data.get("tool", {}).get("setuptools", {})
    declared_py_modules = tuple(tool_setuptools.get("py-modules", []))

    if intentional_modules is not None:
        discovered_intentional = tuple(intentional_modules)
    else:
        # Auto-discover root .py files (excluding setup.py, conftest.py, and dotfiles)
        discovered: list[str] = []
        for path in resolved_source.glob("*.py"):
            if path.name.startswith(".") or path.name in ("setup.py", "conftest.py"):
                continue
            discovered.append(path.stem)
        discovered_intentional = tuple(sorted(discovered))

    missing = tuple(m for m in discovered_intentional if m not in declared_py_modules)
    orphaned = tuple(
        m
        for m in declared_py_modules
        if not (resolved_source / f"{m}.py").is_file()
        and not (resolved_source / m / "__init__.py").is_file()
    )

    is_coherent = (len(missing) == 0) and (len(orphaned) == 0)
    err: str | None = None
    if missing:
        err = f"Intentional top-level modules missing from pyproject.toml py-modules: {missing}"
    elif orphaned:
        err = f"Declared py-modules missing on disk in source: {orphaned}"

    return ForkPackagingCheckResult(
        source_path=str(resolved_source),
        declared_py_modules=declared_py_modules,
        discovered_intentional_modules=discovered_intentional,
        missing_from_py_modules=missing,
        orphaned_in_py_modules=orphaned,
        is_coherent=is_coherent,
        error=err,
    )


def assert_fork_packaging_coherent(
    source: Path,
    intentional_modules: Sequence[str] | None = None,
) -> None:
    """Raise ForkPackagingError if intentional top-level modules are missing from py-modules."""
    result = check_fork_packaging_inventory(source, intentional_modules)
    if not result.is_coherent:
        raise ForkPackagingError(result.error or "Maintained fork packaging is incoherent")


def verify_editable_mapping(
    interpreter: Path,
    source: Path,
    expected_modules: Sequence[str],
    *,
    verify_imports: bool = True,
) -> tuple[ModuleCanaryResult, ...]:
    """Verify that an interpreter resolves all expected modules from the editable source."""
    ok, results = run_interpreter_canary(
        interpreter,
        source,
        expected_modules,
        verify_imports=verify_imports,
    )
    if not ok:
        failures = [r.module for r in results if not r.found or not r.is_source_origin]
        raise EditableReconciliationError(
            f"Editable mapping verification failed for modules: {failures}",
        )
    return results


def reconcile_hermes_editable(
    source: Path | str,
    interpreters: Sequence[Path | str],
    *,
    offline: bool = True,
    expected_modules: Sequence[str] | None = None,
    verify_imports: bool = True,
    raise_on_failure: bool = True,
    _fault_injection: dict[str, Any] | None = None,
) -> EditableReconciliationReceipt:
    """Reconcile editable Hermes mappings transactionally across all given interpreters.

    Parameters:
        source: Explicit verified Hermes source directory.
        interpreters: Explicit sequence of one or more interpreter paths.
        offline: Whether to enforce offline installation (--offline).
        expected_modules: Explicit sequence of top-level modules to verify via canaries.
        verify_imports: Whether canaries attempt actual importlib.import_module.
        raise_on_failure: Whether to raise EditableReconciliationError on failure or
            rollback. Pre-mutation refusals always raise, regardless of this flag.
        _fault_injection: Private test hook for deterministic failure simulation.

    Raises:
        NonEditableTargetError: A target interpreter's Hermes distribution is not an
            editable install (or is missing). Raised before any source or
            site-packages mutation, with a refusal receipt attached.

    Returns:
        EditableReconciliationReceipt recording pre/post fingerprints and status.
    """
    resolved_source = Path(source).resolve()
    if not resolved_source.is_dir():
        raise EditableReconciliationError(f"Hermes source directory {source} does not exist")

    pyproject_path = resolved_source / "pyproject.toml"
    if not pyproject_path.is_file():
        raise EditableReconciliationError(f"pyproject.toml not found in {source}")

    with pyproject_path.open("rb") as handle:
        try:
            pyproject_data = tomllib.load(handle)
        except Exception as err:
            raise EditableReconciliationError(f"Malformed pyproject.toml in {source}") from err

    project_section = pyproject_data.get("project", {})
    dist_name = project_section.get("name", "hermes-agent")
    expected_version = project_section.get("version", "")

    if expected_modules is None:
        tool_setuptools = pyproject_data.get("tool", {}).get("setuptools", {})
        modules_list = tool_setuptools.get("py-modules", [])
        if not modules_list:
            discovered = [
                p.stem
                for p in resolved_source.glob("*.py")
                if not p.name.startswith(".") and p.name not in ("setup.py", "conftest.py")
            ]
            modules_list = sorted(discovered)
        resolved_expected_modules = tuple(modules_list)
    else:
        resolved_expected_modules = tuple(expected_modules)

    if not interpreters:
        raise EditableReconciliationError("At least one interpreter must be provided")

    resolved_interpreters: list[Path] = []
    seen: set[Path] = set()
    for raw_interp in interpreters:
        interp_path = Path(raw_interp).absolute()
        if interp_path not in seen:
            if not interp_path.is_file() or not os.access(interp_path, os.X_OK):
                raise EditableReconciliationError(f"Interpreter {raw_interp} is not executable")
            seen.add(interp_path)
            resolved_interpreters.append(interp_path)

    # 1. Read-only pre-flight: classify every target before touching anything.
    # A non-editable (clean release) target is refused before the source or any
    # site-packages is mutated, so this operation never converts a release install.
    inspections = [inspect_editable_target(interp, dist_name) for interp in resolved_interpreters]
    refused_targets = [insp for insp in inspections if not insp.is_editable]
    if refused_targets:
        refusal_receipt = EditableReconciliationReceipt(
            status="failed",
            source_path=str(resolved_source),
            source_tree_sha256=compute_source_tree_sha256(resolved_source),
            source_git_status=get_git_status(resolved_source),
            offline=offline,
            interpreters=tuple(
                InterpreterReconciliationReceipt(
                    interpreter=str(insp.interpreter),
                    site_packages=str(insp.site_packages),
                    distribution=dist_name,
                    version=insp.version or expected_version,
                    direct_url=insp.direct_url,
                    pre_fingerprints=compute_file_fingerprints(insp.editable_files),
                    post_fingerprints={},
                    canary_results=(),
                    status="refused" if not insp.is_editable else "not_attempted",
                    error=insp.reason,
                )
                for insp in inspections
            ),
            rolled_back=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        raise NonEditableTargetError(
            "Editable reconciliation refused before any mutation; non-editable "
            "target(s): "
            + "; ".join(f"{insp.interpreter}: {insp.reason}" for insp in refused_targets),
            receipt=refusal_receipt,
        )

    # 2. Clean pre-existing build debris and capture source fingerprints
    remove_editable_build_debris(resolved_source, dist_name)
    source_tree_sha256 = compute_source_tree_sha256(resolved_source)
    source_git_status = get_git_status(resolved_source)

    # 3. Collect pre-fingerprints and create private backups
    backup_root = Path(tempfile.mkdtemp(prefix="aether-editable-backup-"))
    os.chmod(backup_root, 0o700)

    interpreter_data: list[_InterpreterStaging] = []
    try:
        for idx, insp in enumerate(inspections):
            interp_backup_dir = backup_root / f"interp_{idx}"
            create_private_backup(insp.editable_files, interp_backup_dir)

            interpreter_data.append(
                _InterpreterStaging(
                    interpreter=insp.interpreter,
                    site_packages=insp.site_packages,
                    dist_info_dir=insp.dist_info_dir,
                    editable_files=insp.editable_files,
                    pre_fingerprints=compute_file_fingerprints(insp.editable_files),
                    backup_dir=interp_backup_dir,
                    direct_url=insp.direct_url,
                )
            )

        # 4. Transactional execution: update all interpreters
        modified_interpreters: list[int] = []
        try:
            for idx, stage in enumerate(interpreter_data):
                interp = stage.interpreter

                # Fault injection check before reinstall
                if _fault_injection and _fault_injection.get("fail_at_interpreter") == idx:
                    if _fault_injection.get("phase") == "pre_reinstall":
                        raise EditableReconciliationError(
                            f"Simulated fault before reinstall on interpreter {interp}"
                        )

                # Execute forced editable reinstall
                # Build isolated subprocess environment (NO PYTHONPATH)
                env = {
                    k: v
                    for k, v in os.environ.items()
                    if not k.startswith(("UV_", "PIP_", "PYTHON"))
                }
                env.pop("VIRTUAL_ENV", None)
                env.pop("CONDA_PREFIX", None)
                env["UV_LINK_MODE"] = "copy"
                if offline:
                    env["UV_OFFLINE"] = "1"

                uv_args = [
                    "uv",
                    "--no-config",
                    "pip",
                    "install",
                    "--reinstall",
                    "--python",
                    str(interp),
                    "--editable",
                    str(resolved_source),
                    "--no-deps",
                ]
                if offline:
                    uv_args.append("--offline")

                try:
                    completed = subprocess.run(
                        uv_args,
                        cwd=resolved_source,
                        capture_output=True,
                        text=True,
                        check=False,
                        env=env,
                    )
                except OSError as error:
                    raise EditableReconciliationError(
                        f"Failed to execute uv pip install on {interp}"
                    ) from error

                if completed.returncode != 0:
                    raise EditableReconciliationError(
                        f"uv pip install failed on {interp} (exit {completed.returncode}): {completed.stderr}"
                    )

                modified_interpreters.append(idx)
                # Remove build debris immediately
                remove_editable_build_debris(resolved_source, dist_name)

                # Fault injection check after reinstall
                if _fault_injection and _fault_injection.get("fail_at_interpreter") == idx:
                    if _fault_injection.get("phase") == "post_reinstall":
                        raise EditableReconciliationError(
                            f"Simulated fault after reinstall on interpreter {interp}"
                        )

                # Verify source tree and status are preserved
                current_tree_sha256 = compute_source_tree_sha256(resolved_source)
                if current_tree_sha256 != source_tree_sha256:
                    raise EditableReconciliationError(
                        f"Source tree sha256 changed during installation for {interp}"
                    )
                current_git_status = get_git_status(resolved_source)
                if current_git_status != source_git_status:
                    raise EditableReconciliationError(
                        f"Source git status changed during installation for {interp}: "
                        f"before={repr(source_git_status)} after={repr(current_git_status)}"
                    )

            # 4. Execute canaries for all interpreters
            all_canary_results: list[tuple[ModuleCanaryResult, ...]] = []
            for idx, stage in enumerate(interpreter_data):
                interp = stage.interpreter

                if _fault_injection and _fault_injection.get("fail_at_interpreter") == idx:
                    if _fault_injection.get("phase") == "canary":
                        raise EditableReconciliationError(
                            f"Simulated canary fault on interpreter {interp}"
                        )

                canary_ok, canary_results = run_interpreter_canary(
                    interp,
                    resolved_source,
                    resolved_expected_modules,
                    verify_imports=verify_imports,
                )
                all_canary_results.append(canary_results)
                if not canary_ok:
                    failures = [
                        r.module
                        for r in canary_results
                        if not r.found or not r.is_source_origin or not r.import_ok
                    ]
                    raise EditableReconciliationError(
                        f"Canary check failed on {interp} for modules: {failures}"
                    )

            # 5. Success! Collect post-fingerprints and construct success receipt
            interp_receipts: list[InterpreterReconciliationReceipt] = []
            for idx, stage in enumerate(interpreter_data):
                sp = stage.site_packages
                dist_info_dir, editable_files, _ = find_editable_metadata(sp, dist_name)

                post_direct_url: dict[str, Any] = {}
                if dist_info_dir is not None:
                    direct_url_path = dist_info_dir / "direct_url.json"
                    if direct_url_path.is_file():
                        try:
                            post_direct_url = json.loads(
                                direct_url_path.read_text(encoding="utf-8")
                            )
                        except Exception:
                            pass
                observed_version = _read_distribution_version(dist_info_dir, expected_version)

                post_fp = compute_file_fingerprints(editable_files)
                interp_receipts.append(
                    InterpreterReconciliationReceipt(
                        interpreter=str(stage.interpreter),
                        site_packages=str(sp),
                        distribution=dist_name,
                        version=observed_version,
                        direct_url=post_direct_url,
                        pre_fingerprints=stage.pre_fingerprints,
                        post_fingerprints=post_fp,
                        canary_results=all_canary_results[idx],
                        status="reconciled",
                    )
                )

            receipt = EditableReconciliationReceipt(
                status="reconciled",
                source_path=str(resolved_source),
                source_tree_sha256=source_tree_sha256,
                source_git_status=source_git_status,
                offline=offline,
                interpreters=tuple(interp_receipts),
                rolled_back=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            return receipt

        except Exception as error:
            # ROLLBACK TRANSACTION
            rollback_reason = str(error)
            rolled_back_receipts: list[InterpreterReconciliationReceipt] = []

            for idx, stage in enumerate(interpreter_data):
                interp = stage.interpreter
                sp = stage.site_packages
                backup_dir = stage.backup_dir
                restore_private_backup(backup_dir, sp, stage.editable_files, dist_name)
                _, restored_files, _ = find_editable_metadata(sp, dist_name)
                restored_fp = compute_file_fingerprints(restored_files)

                rolled_back_receipts.append(
                    InterpreterReconciliationReceipt(
                        interpreter=str(interp),
                        site_packages=str(sp),
                        distribution=dist_name,
                        version=expected_version,
                        direct_url=stage.direct_url,
                        pre_fingerprints=stage.pre_fingerprints,
                        post_fingerprints=restored_fp,
                        canary_results=(),
                        status="rolled_back",
                        error=rollback_reason if idx in modified_interpreters else None,
                    )
                )

            remove_editable_build_debris(resolved_source, dist_name)
            receipt = EditableReconciliationReceipt(
                status="rolled_back",
                source_path=str(resolved_source),
                source_tree_sha256=source_tree_sha256,
                source_git_status=source_git_status,
                offline=offline,
                interpreters=tuple(rolled_back_receipts),
                rolled_back=True,
                rollback_reason=rollback_reason,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            if raise_on_failure:
                raise EditableReconciliationError(
                    f"Editable reconciliation failed and was rolled back: {rollback_reason}",
                    receipt=receipt,
                ) from error
            return receipt

    finally:
        shutil.rmtree(backup_root, ignore_errors=True)
