"""Tests for transactional Hermes editable reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from aether_agents.hermes_editable import (
    EditableReconciliationError,
    ForkPackagingError,
    NonEditableTargetError,
    assert_fork_packaging_coherent,
    check_fork_packaging_inventory,
    compute_source_tree_sha256,
    get_git_status,
    get_interpreter_site_packages,
    reconcile_hermes_editable,
    verify_editable_mapping,
)


def _create_disposable_venv(path: Path) -> Path:
    """Create a fast, disposable virtualenv using uv."""
    completed = subprocess.run(
        ["uv", "venv", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, f"uv venv failed: {completed.stderr}"
    python_path = path / "bin" / "python"
    assert python_path.is_file(), f"Python binary not found at {python_path}"
    return python_path


def _create_disposable_hermes_fork(
    path: Path,
    *,
    modules: list[str],
    version: str = "0.20.4",
) -> Path:
    """Initialize a minimal disposable Hermes fork repository."""
    path.mkdir(parents=True, exist_ok=True)
    pyproject_content = f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-agent"
version = "{version}"
dependencies = []

[tool.setuptools]
py-modules = {json.dumps(modules)}
"""
    (path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    for mod in modules:
        mod_file = path / f"{mod}.py"
        mod_file.write_text(f"# Module {mod}\nIDENTIFIER = {repr(mod)}\n", encoding="utf-8")

    # Initialize git repo and make initial commit
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "agent@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial release"], cwd=path, check=True)

    return path


def _initial_editable_install(python: Path, source: Path) -> None:
    """Perform initial editable install into a disposable venv."""
    completed = subprocess.run(
        [
            "uv",
            "--no-config",
            "pip",
            "install",
            "--link-mode=copy",
            "--python",
            str(python),
            "--editable",
            str(source),
            "--no-deps",
            "--offline",
        ],
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, f"Initial editable install failed: {completed.stderr}"


def _non_editable_wheel_install(python: Path, source: Path, work_dir: Path) -> None:
    """Install the disposable fork as a clean, non-editable release wheel."""
    wheel_dir = work_dir / "wheels"
    built = subprocess.run(
        ["uv", "build", "--wheel", "--offline", "--out-dir", str(wheel_dir)],
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, f"uv build --wheel failed: {built.stderr}"
    wheels = sorted(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected exactly one built wheel, found: {wheels}"

    installed = subprocess.run(
        [
            "uv",
            "--no-config",
            "pip",
            "install",
            "--link-mode=copy",
            "--python",
            str(python),
            "--no-deps",
            "--offline",
            str(wheels[0]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert installed.returncode == 0, f"Non-editable wheel install failed: {installed.stderr}"


def test_red_green_editable_reconciliation(tmp_path: Path) -> None:
    """1. RED/GREEN on disposable maintained-fork source + disposable venvs.

    - install editable without hermes_state_compaction in the top-level inventory;
    - add the source file and update pyproject.toml without reinstalling;
    - python -I reports find_spec absent (RED);
    - Run reconcile_hermes_editable;
    - Both interpreters resolve every intended top-level module from exact source under env -i and python -I (GREEN).
    """
    initial_modules = ["hermes_constants", "hermes_state"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=initial_modules)

    venv1 = _create_disposable_venv(tmp_path / "venv1")
    venv2 = _create_disposable_venv(tmp_path / "venv2")
    interpreters = [venv1, venv2]

    for interp in interpreters:
        _initial_editable_install(interp, fork_dir)

    # Both interpreters resolve initial modules
    for interp in interpreters:
        results = verify_editable_mapping(interp, fork_dir, initial_modules)
        assert len(results) == 2
        assert all(r.found and r.is_source_origin for r in results)

    # Now add hermes_state_compaction.py and update pyproject.toml WITHOUT reinstalling
    new_module = "hermes_state_compaction"
    all_intended_modules = [*initial_modules, new_module]
    (fork_dir / f"{new_module}.py").write_text(
        f"# Module {new_module}\nIDENTIFIER = {repr(new_module)}\n",
        encoding="utf-8",
    )
    pyproject_path = fork_dir / "pyproject.toml"
    new_pyproject = f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-agent"
version = "0.20.4"
dependencies = []

[tool.setuptools]
py-modules = {json.dumps(all_intended_modules)}
"""
    pyproject_path.write_text(new_pyproject, encoding="utf-8")

    # RED: python -I reports find_spec is None before reconciliation
    for interp in interpreters:
        check_proc = subprocess.run(
            [
                str(interp),
                "-I",
                "-c",
                f"import importlib.util; print(importlib.util.find_spec({repr(new_module)}))",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={},
        )
        assert check_proc.returncode == 0
        assert check_proc.stdout.strip() == "None", "Expected find_spec to be None (RED)"

    # GREEN: Run transactional editable reconciliation operation
    receipt = reconcile_hermes_editable(
        source=fork_dir,
        interpreters=interpreters,
        offline=True,
        expected_modules=all_intended_modules,
    )

    assert receipt.status == "reconciled"
    assert not receipt.rolled_back
    assert len(receipt.interpreters) == 2

    # Verify both interpreters resolve every intended module under env -i and python -I from exact source
    for interp in interpreters:
        results = verify_editable_mapping(interp, fork_dir, all_intended_modules)
        assert len(results) == 3
        for res in results:
            assert res.found, f"Module {res.module} not found in {interp}"
            assert res.is_source_origin, f"Module {res.module} origin not in source: {res.origin}"
            assert res.import_ok, f"Module {res.module} failed import: {res.error}"
            assert Path(res.origin or "").resolve() == (fork_dir / f"{res.module}.py").resolve()


def test_atomic_rollback_on_later_interpreter_failure(tmp_path: Path) -> None:
    """2. Atomic rollback: force a later interpreter to fail and prove earlier interpreters' metadata is restored."""
    initial_modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=initial_modules)

    venv1 = _create_disposable_venv(tmp_path / "venv1")
    venv2 = _create_disposable_venv(tmp_path / "venv2")
    interpreters = [venv1, venv2]

    for interp in interpreters:
        _initial_editable_install(interp, fork_dir)

    # Capture pre-reconciliation state on interpreter 1
    sp1 = get_interpreter_site_packages(venv1)
    finder_files_before = list(sp1.glob("__editable___hermes_agent_*_finder.py"))
    assert len(finder_files_before) == 1
    finder_hash_before = hashlib.sha256(finder_files_before[0].read_bytes()).hexdigest()

    # Update source with new module
    new_module = "hermes_state_compaction"
    all_intended = [*initial_modules, new_module]
    (fork_dir / f"{new_module}.py").write_text("MAGIC = 999\n", encoding="utf-8")
    (fork_dir / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-agent"
version = "0.20.4"
dependencies = []

[tool.setuptools]
py-modules = {json.dumps(all_intended)}
""",
        encoding="utf-8",
    )

    # Force failure on interpreter 2 (idx 1) after interpreter 1 was updated
    with pytest.raises(EditableReconciliationError) as exc_info:
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=interpreters,
            offline=True,
            expected_modules=all_intended,
            _fault_injection={"fail_at_interpreter": 1, "phase": "pre_reinstall"},
        )

    # Verify receipt reports rollback
    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "rolled_back"
    assert receipt.rolled_back is True
    assert "Simulated fault" in (receipt.rollback_reason or "")

    # Prove earlier interpreter 1's metadata is restored
    finder_files_after = list(sp1.glob("__editable___hermes_agent_*_finder.py"))
    assert len(finder_files_after) == 1
    finder_hash_after = hashlib.sha256(finder_files_after[0].read_bytes()).hexdigest()
    assert finder_hash_after == finder_hash_before, "Interpreter 1 finder was not restored"

    # Verify interpreter 1 still reports find_spec as None for the new module
    proc = subprocess.run(
        [
            str(venv1),
            "-I",
            "-c",
            f"import importlib.util; print(importlib.util.find_spec({repr(new_module)}))",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "None", "Interpreter 1 state should have been rolled back"


def test_source_preservation_across_reconciliation(tmp_path: Path) -> None:
    """3. Source preservation: source bytes and git status/tree fingerprints are byte-identical across reconciliation."""
    modules = ["hermes_constants", "hermes_state"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")
    _initial_editable_install(venv, fork_dir)

    # Introduce intentional uncommitted dirty source modifications
    (fork_dir / "untracked_note.txt").write_text("uncommitted scratch file\n", encoding="utf-8")
    with (fork_dir / "hermes_constants.py").open("a", encoding="utf-8") as handle:
        handle.write("\nEXTRA_CONSTANT = 'dirty_value'\n")

    # Capture source status and tree digests before reconciliation
    status_before = get_git_status(fork_dir)
    assert status_before is not None
    assert "M hermes_constants.py" in status_before
    assert "?? untracked_note.txt" in status_before
    tree_sha_before = compute_source_tree_sha256(fork_dir)

    # Reconcile
    receipt = reconcile_hermes_editable(
        source=fork_dir,
        interpreters=[venv],
        offline=True,
        expected_modules=modules,
    )

    assert receipt.status == "reconciled"

    # Verify byte-identical preservation of git status and tree hash
    status_after = get_git_status(fork_dir)
    tree_sha_after = compute_source_tree_sha256(fork_dir)

    assert status_after == status_before, "Git status changed across reconciliation"
    assert tree_sha_after == tree_sha_before, "Tree sha256 changed across reconciliation"
    assert receipt.source_tree_sha256 == tree_sha_before, "Receipt did not record correct tree hash"
    assert receipt.source_git_status == status_before, "Receipt did not record correct git status"

    # Verify build debris (hermes_agent.egg-info) was cleanly removed
    assert not (fork_dir / "hermes_agent.egg-info").exists()


def test_offline_mode_reconciliation(tmp_path: Path) -> None:
    """4. Offline mode: the selected offline reinstall path works without network."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")
    _initial_editable_install(venv, fork_dir)

    receipt = reconcile_hermes_editable(
        source=fork_dir,
        interpreters=[venv],
        offline=True,
        expected_modules=modules,
    )

    assert receipt.status == "reconciled"
    assert receipt.offline is True


def test_maintained_fork_packaging_coverage(tmp_path: Path) -> None:
    """5. Maintained-fork packaging coverage: fails when an intentional top-level module is missing from built/editable mapping."""
    declared = ["hermes_constants", "hermes_state"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=declared)

    # Coherent check
    result_ok = check_fork_packaging_inventory(fork_dir, intentional_modules=declared)
    assert result_ok.is_coherent
    assert len(result_ok.missing_from_py_modules) == 0
    assert_fork_packaging_coherent(fork_dir, intentional_modules=declared)

    # Add an intentional module to source but forget to declare it in py-modules
    intentional_with_compaction = [*declared, "hermes_state_compaction"]
    (fork_dir / "hermes_state_compaction.py").write_text("COMPACT = 1\n", encoding="utf-8")

    # The check MUST FAIL reporting the missing module
    result_missing = check_fork_packaging_inventory(
        fork_dir, intentional_modules=intentional_with_compaction
    )
    assert not result_missing.is_coherent
    assert "hermes_state_compaction" in result_missing.missing_from_py_modules

    with pytest.raises(ForkPackagingError) as exc:
        assert_fork_packaging_coherent(fork_dir, intentional_modules=intentional_with_compaction)
    assert "hermes_state_compaction" in str(exc.value)

    # Auto-discovery mode also catches it
    result_auto = check_fork_packaging_inventory(fork_dir)
    assert not result_auto.is_coherent
    assert "hermes_state_compaction" in result_auto.missing_from_py_modules


def test_input_validation_and_safety_checks(tmp_path: Path) -> None:
    """Input validation and safety invariants."""
    # 1. Non-existent source
    with pytest.raises(EditableReconciliationError, match="does not exist"):
        reconcile_hermes_editable(
            source=tmp_path / "nonexistent",
            interpreters=[sys.executable],
        )

    # 2. Source missing pyproject.toml
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(EditableReconciliationError, match="pyproject.toml not found"):
        reconcile_hermes_editable(
            source=empty_dir,
            interpreters=[sys.executable],
        )

    # 3. Empty interpreters list
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=["hermes_constants"])
    with pytest.raises(EditableReconciliationError, match="At least one interpreter"):
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=[],
        )

    # 4. Non-executable interpreter
    with pytest.raises(EditableReconciliationError, match="not executable"):
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=[tmp_path / "not_an_executable"],
        )


def test_canary_origin_validation(tmp_path: Path) -> None:
    """Canary rejects modules whose origin does not resolve to the source directory."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")
    _initial_editable_install(venv, fork_dir)

    # Point canary check to an unrelated expected module that exists in Python stdlib (e.g. 'json')
    # but whose origin will be under the stdlib path, NOT under fork_dir
    with pytest.raises(EditableReconciliationError, match="Canary check failed"):
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=[venv],
            expected_modules=["json"],
        )


def test_atomic_rollback_on_canary_failure(tmp_path: Path) -> None:
    """Canary failure on second interpreter triggers full rollback across all interpreters."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)

    venv1 = _create_disposable_venv(tmp_path / "venv1")
    venv2 = _create_disposable_venv(tmp_path / "venv2")
    interpreters = [venv1, venv2]

    for interp in interpreters:
        _initial_editable_install(interp, fork_dir)

    sp1 = get_interpreter_site_packages(venv1)
    finder1_before = list(sp1.glob("__editable___hermes_agent_*_finder.py"))[0].read_bytes()

    with pytest.raises(EditableReconciliationError) as exc_info:
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=interpreters,
            expected_modules=modules,
            _fault_injection={"fail_at_interpreter": 1, "phase": "canary"},
        )

    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "rolled_back"
    assert receipt.rolled_back is True
    assert "Simulated canary fault" in (receipt.rollback_reason or "")

    finder1_after = list(sp1.glob("__editable___hermes_agent_*_finder.py"))[0].read_bytes()
    assert finder1_after == finder1_before, "Interpreter 1 was not restored after canary fault"


def test_non_editable_target_refused_before_mutation(tmp_path: Path) -> None:
    """A clean release (non-editable) target is refused before anything is mutated.

    Regression pin for the round-1 review: previously the operation converted a
    non-editable install and, on failure, reported ``rolled_back`` while the
    installed module file was gone. Now the distribution identity is inspected
    first and a non-editable target is refused without any mutation.
    """
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")
    _non_editable_wheel_install(venv, fork_dir, tmp_path)

    sp = get_interpreter_site_packages(venv)
    module_path = sp / "hermes_constants.py"
    dist_info_dir = next(sp.glob("hermes_agent-*.dist-info"))
    pre_files = [module_path, *(p for p in sorted(dist_info_dir.rglob("*")) if p.is_file())]
    pre_payloads = {p.relative_to(sp).as_posix(): p.read_bytes() for p in pre_files}

    def resolved_origin() -> Path:
        completed = subprocess.run(
            [
                str(venv),
                "-I",
                "-c",
                "import importlib.util; print(importlib.util.find_spec('hermes_constants').origin)",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={},
        )
        assert completed.returncode == 0, completed.stderr
        return Path(completed.stdout.strip()).resolve()

    # Pre-condition: a real clean release install, resolving from site-packages.
    assert resolved_origin() == module_path.resolve()
    status_before = get_git_status(fork_dir)
    egg_info_before = (fork_dir / "hermes_agent.egg-info").exists()

    with pytest.raises(NonEditableTargetError) as exc_info:
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=[venv],
            offline=True,
            expected_modules=modules,
        )

    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "failed"
    assert receipt.rolled_back is False
    assert receipt.interpreters[0].status == "refused"
    assert "not an editable installation" in (receipt.interpreters[0].error or "")
    assert receipt.interpreters[0].direct_url, "Refusal receipt must record the observed identity"
    assert receipt.interpreters[0].direct_url.get("dir_info", {}).get("editable") is not True
    assert "refused before any mutation" in str(exc_info.value)

    # No site-packages mutation: pre-existing files byte-identical, no new artifacts.
    for rel, payload in pre_payloads.items():
        assert (sp / rel).is_file(), f"Refusal removed {rel}"
        assert (sp / rel).read_bytes() == payload, f"Refusal modified {rel}"
    assert not list(sp.glob("__editable__*")), "Refusal created editable mapping artifacts"
    assert not list(sp.glob("_editable_impl_hermes*"))
    assert resolved_origin() == module_path.resolve(), "Refusal changed resolution"

    # No source mutation: status and build debris are unchanged.
    assert get_git_status(fork_dir) == status_before
    assert (fork_dir / "hermes_agent.egg-info").exists() == egg_info_before


def test_mixed_targets_refused_without_mutating_editable_target(tmp_path: Path) -> None:
    """One non-editable target refuses the transaction before ANY interpreter is touched."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    editable_venv = _create_disposable_venv(tmp_path / "venv-editable")
    release_venv = _create_disposable_venv(tmp_path / "venv-release")
    _initial_editable_install(editable_venv, fork_dir)
    _non_editable_wheel_install(release_venv, fork_dir, tmp_path)

    editable_sp = get_interpreter_site_packages(editable_venv)
    editable_artifacts = [
        *sorted(editable_sp.glob("__editable__*")),
        *sorted(editable_sp.glob("_editable_impl_hermes*")),
    ]
    assert editable_artifacts, "Expected the editable pre-state to carry mapping artifacts"
    artifacts_before = {p.name: p.read_bytes() for p in editable_artifacts}
    editable_dist_info = next(editable_sp.glob("hermes_agent-*.dist-info"))
    dist_info_before = {
        p.relative_to(editable_sp).as_posix(): p.read_bytes()
        for p in sorted(editable_dist_info.rglob("*"))
        if p.is_file()
    }

    release_sp = get_interpreter_site_packages(release_venv)
    release_module = release_sp / "hermes_constants.py"
    release_before = release_module.read_bytes()

    with pytest.raises(NonEditableTargetError) as exc_info:
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=[editable_venv, release_venv],
            offline=True,
            expected_modules=modules,
        )

    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "failed"
    assert receipt.rolled_back is False
    assert [entry.status for entry in receipt.interpreters] == ["not_attempted", "refused"]

    # The editable target was never converted, reinstalled or otherwise touched.
    for name, payload in artifacts_before.items():
        assert (editable_sp / name).read_bytes() == payload, f"Editable artifact {name} changed"
    for rel, payload in dist_info_before.items():
        assert (editable_sp / rel).read_bytes() == payload, f"Editable metadata {rel} changed"
    assert release_module.read_bytes() == release_before

    # The editable target still resolves every module from the exact source.
    completed = subprocess.run(
        [
            str(editable_venv),
            "-I",
            "-c",
            "import importlib.util; print(importlib.util.find_spec('hermes_constants').origin)",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )
    assert completed.returncode == 0, completed.stderr
    assert Path(completed.stdout.strip()).resolve() == (fork_dir / "hermes_constants.py").resolve()


def test_missing_distribution_target_refused(tmp_path: Path) -> None:
    """A target interpreter without the Hermes distribution is refused before mutation."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")

    with pytest.raises(NonEditableTargetError) as exc_info:
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=[venv],
            offline=True,
            expected_modules=modules,
        )

    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "failed"
    assert receipt.rolled_back is False
    assert receipt.interpreters[0].status == "refused"
    assert "not installed" in (receipt.interpreters[0].error or "")

    # Nothing was created in either the source or the interpreter.
    assert not (fork_dir / "hermes_agent.egg-info").exists()
    assert get_git_status(fork_dir) == ""
    sp = get_interpreter_site_packages(venv)
    assert not list(sp.glob("__editable__*"))
    assert not list(sp.glob("hermes_agent-*.dist-info"))


def test_real_canary_failure_rolls_back_metadata_faithfully(tmp_path: Path) -> None:
    """A real (non-injected) canary failure restores every touched interpreter byte-for-byte."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv1 = _create_disposable_venv(tmp_path / "venv1")
    venv2 = _create_disposable_venv(tmp_path / "venv2")
    interpreters = [venv1, venv2]
    for interp in interpreters:
        _initial_editable_install(interp, fork_dir)

    # Update source with a new module and force a real canary failure with a bogus
    # expected module: the reinstall succeeds, the canary fails on its own.
    (fork_dir / "hermes_state_compaction.py").write_text("COMPACT = 1\n", encoding="utf-8")
    (fork_dir / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-agent"
version = "0.20.4"
dependencies = []

[tool.setuptools]
py-modules = {json.dumps([*modules, "hermes_state_compaction"])}
""",
        encoding="utf-8",
    )

    pre_state: dict[Path, tuple[Path, dict[str, bytes]]] = {}
    for interp in interpreters:
        sp = get_interpreter_site_packages(interp)
        dist_info = next(sp.glob("hermes_agent-*.dist-info"))
        entries = [
            *sorted(sp.glob("__editable__*")),
            *sorted(sp.glob("_editable_impl_hermes*")),
            *(p for p in sorted(dist_info.rglob("*")) if p.is_file()),
        ]
        pre_state[interp] = (
            sp,
            {p.relative_to(sp).as_posix(): p.read_bytes() for p in entries},
        )

    with pytest.raises(EditableReconciliationError) as exc_info:
        reconcile_hermes_editable(
            source=fork_dir,
            interpreters=interpreters,
            offline=True,
            expected_modules=["hermes_constants", "module_that_does_not_exist_anywhere"],
        )

    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "rolled_back"
    assert receipt.rolled_back is True
    assert "Canary check failed" in (receipt.rollback_reason or "")

    for interp, (sp, entries) in pre_state.items():
        for rel, payload in entries.items():
            assert (sp / rel).is_file(), f"{rel} missing after rollback for {interp}"
            assert (sp / rel).read_bytes() == payload, f"{rel} not restored for {interp}"

    # The new module is not resolvable again on either interpreter.
    for interp in interpreters:
        completed = subprocess.run(
            [
                str(interp),
                "-I",
                "-c",
                "import importlib.util as u; print(u.find_spec('hermes_state_compaction'))",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={},
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.strip() == "None", "Rollback did not restore the pre-state mapping"


def test_reconcile_raise_on_failure_false(tmp_path: Path) -> None:
    """When raise_on_failure=False, return the rolled-back receipt without raising."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")
    _initial_editable_install(venv, fork_dir)

    receipt = reconcile_hermes_editable(
        source=fork_dir,
        interpreters=[venv],
        expected_modules=modules,
        raise_on_failure=False,
        _fault_injection={"fail_at_interpreter": 0, "phase": "pre_reinstall"},
    )
    assert receipt.status == "rolled_back"
    assert receipt.rolled_back is True
    assert "Simulated fault" in (receipt.rollback_reason or "")


def test_receipt_structure_and_serialization(tmp_path: Path) -> None:
    """Receipt carries all required source and metadata fingerprints and serializes to dict/json."""
    modules = ["hermes_constants"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=modules)
    venv = _create_disposable_venv(tmp_path / "venv")
    _initial_editable_install(venv, fork_dir)

    receipt = reconcile_hermes_editable(
        source=fork_dir,
        interpreters=[venv],
        expected_modules=modules,
    )
    assert receipt.status == "reconciled"
    assert receipt.source_path == str(fork_dir.resolve())
    assert receipt.source_tree_sha256
    assert receipt.offline is True
    assert len(receipt.interpreters) == 1

    interp_rec = receipt.interpreters[0]
    assert interp_rec.distribution == "hermes-agent"
    assert interp_rec.version == "0.20.4"
    assert interp_rec.direct_url.get("dir_info", {}).get("editable") is True
    assert interp_rec.pre_fingerprints
    assert interp_rec.post_fingerprints
    assert len(interp_rec.canary_results) == 1

    # Verify serialization
    data = receipt.to_dict()
    assert data["status"] == "reconciled"
    serialized = json.dumps(data)
    assert isinstance(serialized, str)


def test_fork_packaging_orphaned_module_detected(tmp_path: Path) -> None:
    """Packaging check catches declared py-modules that do not exist on disk."""
    declared = ["hermes_constants", "nonexistent_module"]
    fork_dir = _create_disposable_hermes_fork(tmp_path / "fork", modules=["hermes_constants"])

    # Overwrite pyproject.toml to declare nonexistent_module
    (fork_dir / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-agent"
version = "0.20.4"
dependencies = []

[tool.setuptools]
py-modules = {json.dumps(declared)}
""",
        encoding="utf-8",
    )

    result = check_fork_packaging_inventory(fork_dir)
    assert not result.is_coherent
    assert "nonexistent_module" in result.orphaned_in_py_modules

    with pytest.raises(ForkPackagingError, match="Declared py-modules missing on disk"):
        assert_fork_packaging_coherent(fork_dir)
