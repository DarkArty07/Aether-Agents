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
