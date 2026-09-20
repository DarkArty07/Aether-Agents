"""Regressions for release-owned TUI preparation, binding, doctor, and branded projections.

Covers LG-LIFE obligations:
- Disposable candidate preparation builds/stages TUI outside hermes-source.
- Hash-binding and provenance in release record, manifest, and store.
- Agreement across launcher, service, desktop, WSL entries, update, rollback, and doctor.
- Fail-closed doctor on altered/missing TUI or launcher bytes.
- Projection failure restores prior opaque state.
- Locked-source inventory and hashes identical before/after launch.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import aether_agents.lifecycle as lifecycle
from aether_agents.lifecycle import (
    AETHER_GATEWAY_UNIT,
    MAINTAINED_FORK_BRANCH,
    MAINTAINED_FORK_REPOSITORY,
    DisabledServiceController,
    IntegrityError,
    LifecycleManager,
    ProjectionRoots,
    ReleaseRecord,
    ReleaseStore,
)
from aether_agents.observation.checkpoint import AuthorityContext

FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
_CHECKOUT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> str:
    """Run one fixture Git command with no ambient repository binding inherited.

    A fixture is never allowed to read whatever repository the surrounding process
    environment happens to name; the tests that set ``GIT_DIR`` on purpose depend on it.
    """

    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    )
    return result.stdout.strip()


def _this_repository_git_entry() -> Path:
    """This checkout's own ``.git`` entry, derived from the test file rather than the cwd."""

    entry = _CHECKOUT / ".git"
    assert entry.exists()
    return entry


def _this_repository_object_directory() -> Path:
    """The object store this checkout's Git commands resolve, linked worktree included."""

    common = _git(_CHECKOUT, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common) / "objects"


def _write_fork_tree(root: Path, marker: str) -> None:
    """Write a minimal maintained-fork-shaped tree whose ui-tui build emits ``marker``."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps({"name": "hermes-agent", "workspaces": ["ui-tui"]}) + "\n",
        encoding="utf-8",
    )
    tui = root / "ui-tui"
    tui.mkdir(parents=True, exist_ok=True)
    marker_in_shell = marker.replace("\\", "\\\\").replace('"', '\\"')
    (tui / "package.json").write_text(
        json.dumps(
            {
                "name": "ui-tui",
                "version": "1.0.0",
                "scripts": {
                    "build": (
                        "node -e \"const fs=require('fs'); "
                        "fs.mkdirSync('dist',{recursive:true}); "
                        f"fs.writeFileSync('dist/entry.js','{marker_in_shell}\\n')\""
                    )
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    hermes_cli = root / "hermes_cli"
    hermes_cli.mkdir(parents=True, exist_ok=True)
    (hermes_cli / "__init__.py").write_text("", encoding="utf-8")
    (root / "hermes_constants.py").write_text(
        "import shutil\n"
        "\n"
        "def find_node_executable(binary: str = 'node') -> str | None:\n"
        "    return shutil.which(binary)\n",
        encoding="utf-8",
    )
    (hermes_cli / "main.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "from hermes_constants import find_node_executable\n"
        "\n"
        "def _make_tui_argv(tui_dir: Path, tui_dev: bool) -> tuple[list[str], Path]:\n"
        "    external = os.environ.get('HERMES_TUI_DIR')\n"
        "    if not tui_dev and external:\n"
        "        entry = Path(external) / 'dist' / 'entry.js'\n"
        "        if entry.is_file():\n"
        "            return [find_node_executable('node') or 'node', str(entry)], Path(external)\n"
        "    return [find_node_executable('node') or 'node', str(tui_dir / 'dist' / 'entry.js')], tui_dir\n",
        encoding="utf-8",
    )


def _disposable_fork_source(
    root: Path, marker: str = 'console.log("TUI READY");'
) -> tuple[Path, str]:
    """Create a tiny exact-commit fork fixture for deterministic unit tests."""

    checkout = root / "maintained-fork"
    checkout.mkdir()
    _git(checkout, "init", "-q", "-b", "aether-main")
    _git(checkout, "config", "user.name", "Aether Test")
    _git(checkout, "config", "user.email", "aether@example.invalid")
    _write_fork_tree(checkout, marker)
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-qm", "disposable fork fixture")
    return checkout, _git(checkout, "rev-parse", "HEAD")


class RecordingServiceController(DisabledServiceController):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def available(self) -> bool:
        return True

    def restart(self, unit_name: str) -> str:
        self.calls.append(unit_name)
        return "restarted"


def _manager(
    tmp_path: Path,
    *,
    controller: lifecycle.ServiceController | None = None,
    project_root: Path | None = None,
) -> LifecycleManager:
    store = ReleaseStore(
        root=tmp_path / "data" / "aether",
        state_root=tmp_path / "state" / "aether",
    )
    projections = ProjectionRoots.disposable(tmp_path / "projections")
    if project_root is None:
        project_root = tmp_path / "project"
        project_root.mkdir(parents=True, exist_ok=True)
    return LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        service_controller=controller or DisabledServiceController(),
        projections=projections,
        project_root=project_root,
    )


def _aether_identity(version: str) -> dict[str, object]:
    return {
        "distribution": "aether-agents",
        "package_version": version,
        "git_tag": "v1.0.0-rc.4",
        "git_commit": "a" * 40,
        "python_requires": ">=3.11,<3.14",
        "observer": {
            "plugin_name": "aether-contract-observer",
            "group": "hermes_agent.plugins",
            "target": "aether_agents.observation.capture.hermes_plugin",
        },
    }


def _record_with_tui(
    store: ReleaseStore,
    release_id: str,
    tui_sha256: str | None = None,
) -> ReleaseRecord:
    from aether_agents.lifecycle import AetherPrebuildIdentity

    identity = _aether_identity("1.0.0rc4")
    record = ReleaseRecord(
        schema_version=3,
        release_id=release_id,
        version="1.0.0rc4",
        wheel_filename="aether_agents-1.0.0rc4-py3-none-any.whl",
        wheel_sha256="a" * 64,
        hermes_tag=MAINTAINED_FORK_BRANCH,
        hermes_commit=FORK_COMMIT,
        observer_entry_point=(
            "aether-contract-observer=aether_agents.observation.capture.hermes_plugin"
        ),
        previous_release_id=None,
        authority_context=AuthorityContext.for_active_release(release_id).to_record(),
        aether_identity=identity,
        prebuild_identity=AetherPrebuildIdentity.from_record(identity).digest,
        installed_file_fingerprint="e" * 64,
        hermes_repository=MAINTAINED_FORK_REPOSITORY,
        hermes_branch=MAINTAINED_FORK_BRANCH,
        hermes_source_tree_sha256="c" * 64,
        tui_sha256=tui_sha256,
    )
    record.validate()
    release = store.release_path(release_id)
    release.mkdir(parents=True, exist_ok=True)
    (release / "venv").symlink_to("runtime")
    if tui_sha256 is not None:
        tui_dir = release / "tui" / "dist"
        tui_dir.mkdir(parents=True, exist_ok=True)
        entry = tui_dir / "entry.js"
        entry.write_bytes(b"console.log('tui');\n")
    return record


def _publish_record(manager: LifecycleManager, record: ReleaseRecord) -> None:
    from aether_agents.lifecycle import _atomic_json

    payload = {field: getattr(record, field) for field in record.__dataclass_fields__}
    _atomic_json(manager.store.release_path(record.release_id) / "record.json", payload)
    _atomic_json(manager.store.active_pointer, payload)


# --------------------------------------------------------------------------- tests


def test_tui_disposable_build_and_staging(tmp_path: Path) -> None:
    """Disposable TUI build records digest/provenance and does not touch fork source."""
    from aether_agents.lifecycle import build_tui_in_disposable_workspace

    fork_source, fork_commit = _disposable_fork_source(tmp_path)
    destination = tmp_path / "tui-output"
    receipt = build_tui_in_disposable_workspace(
        fork_source,
        fork_commit,
        destination,
    )

    entry = destination / "dist" / "entry.js"
    assert entry.is_file()
    digest = hashlib.sha256(entry.read_bytes()).hexdigest()
    assert receipt["tui_sha256"] == digest
    assert receipt["entry_path"] == "dist/entry.js"
    assert "node_version" in receipt
    assert "npm_version" in receipt

    provenance_file = destination / "provenance.json"
    assert provenance_file.is_file()
    provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    assert provenance["entry_sha256"] == digest
    assert provenance["hermes_commit"] == fork_commit


def test_tui_build_refuses_unavailable_commit_without_fallback(tmp_path: Path) -> None:
    """Preparation fails when the supplied fork cannot archive the requested commit."""
    from aether_agents.lifecycle import build_tui_in_disposable_workspace

    fork_source, _ = _disposable_fork_source(tmp_path)
    with pytest.raises(IntegrityError, match="failed to extract git archive"):
        build_tui_in_disposable_workspace(fork_source, FORK_COMMIT, tmp_path / "tui-output")


def test_tui_build_stages_materialized_tree_without_repository(tmp_path: Path) -> None:
    """An exact-commit tree with no repository of its own is copied and built as supplied."""
    from aether_agents.lifecycle import build_tui_in_disposable_workspace

    tree = tmp_path / "hermes-source" / "hermes-agent"
    _write_fork_tree(tree, "MATERIALIZED-TREE-ENTRY")

    destination = tmp_path / "tui-output"
    receipt = build_tui_in_disposable_workspace(tree, FORK_COMMIT, destination)

    entry = destination / "dist" / "entry.js"
    assert entry.read_text(encoding="utf-8") == "MATERIALIZED-TREE-ENTRY\n"
    assert receipt["tui_sha256"] == hashlib.sha256(entry.read_bytes()).hexdigest()
    assert receipt["source"] == "materialized-tree"
    provenance = json.loads((destination / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["hermes_commit"] == FORK_COMMIT
    assert provenance["source"] == "materialized-tree"

    # The supplied tree is read only: the build happens in the disposable copy.
    assert not (tree / "node_modules").exists()
    assert not (tree / "ui-tui" / "node_modules").exists()
    assert not (tree / "ui-tui" / "dist").exists()


def test_tui_build_never_archives_an_enclosing_repository(tmp_path: Path) -> None:
    """A non-repository tree nested in another repository is built from its own bytes."""
    from aether_agents.lifecycle import build_tui_in_disposable_workspace

    enclosing = tmp_path / "enclosing-repo"
    _write_fork_tree(enclosing, "ENCLOSING-REPOSITORY-ENTRY")
    _git(enclosing, "init", "-q", "-b", "main")
    _git(enclosing, "config", "user.name", "Aether Test")
    _git(enclosing, "config", "user.email", "aether@example.invalid")
    _git(enclosing, "add", ".")
    _git(enclosing, "commit", "-qm", "enclosing tree")
    enclosing_commit = _git(enclosing, "rev-parse", "HEAD")

    nested = enclosing / "vendor" / "hermes-agent"
    _write_fork_tree(nested, "NESTED-TREE-ENTRY")

    destination = tmp_path / "tui-output"
    receipt = build_tui_in_disposable_workspace(nested, enclosing_commit, destination)

    entry = destination / "dist" / "entry.js"
    assert entry.read_text(encoding="utf-8") == "NESTED-TREE-ENTRY\n"
    assert receipt["source"] == "materialized-tree"


def test_tui_build_archives_the_requested_commit_from_its_own_git_entry(tmp_path: Path) -> None:
    """A checkout whose ``.git`` is a worktree pointer archives its own requested commit."""
    from aether_agents.lifecycle import build_tui_in_disposable_workspace

    checkout, requested = _disposable_fork_source(tmp_path, marker="REQUESTED-COMMIT-ENTRY")
    linked = tmp_path / "linked-fork"
    _git(checkout, "worktree", "add", "-q", str(linked), requested)
    assert (linked / ".git").is_file()

    _write_fork_tree(checkout, "LATER-COMMIT-ENTRY")
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-qm", "later tree")
    assert _git(checkout, "rev-parse", "HEAD") != requested

    destination = tmp_path / "tui-output"
    receipt = build_tui_in_disposable_workspace(linked, requested, destination)

    entry = destination / "dist" / "entry.js"
    assert entry.read_text(encoding="utf-8") == "REQUESTED-COMMIT-ENTRY\n"
    assert receipt["source"] == "git-archive"


def test_tui_build_refuses_tree_without_ui_tui(tmp_path: Path) -> None:
    """A supplied tree that cannot contain the TUI build fails closed, not through npm noise."""
    from aether_agents.lifecycle import build_tui_in_disposable_workspace

    tree = tmp_path / "hermes-source" / "hermes-agent"
    tree.mkdir(parents=True)
    (tree / "package.json").write_text('{"name": "hermes-agent"}\n', encoding="utf-8")

    with pytest.raises(IntegrityError, match="does not contain ui-tui"):
        build_tui_in_disposable_workspace(tree, FORK_COMMIT, tmp_path / "tui-output")


def test_checkout_git_inspection_binds_to_the_supplied_directory(tmp_path: Path) -> None:
    """Supplied-checkout Git inspection never resolves an enclosing repository."""
    checkout, commit = _disposable_fork_source(tmp_path)
    nested = checkout / "vendor" / "extracted-tree"
    nested.mkdir(parents=True)
    (nested / "marker.txt").write_text("nested\n", encoding="utf-8")

    assert lifecycle._git(nested, "rev-parse", "--is-inside-work-tree", check=False) != "true"
    assert lifecycle._git(checkout, "rev-parse", "HEAD") == commit


def test_source_materialization_never_archives_an_enclosing_repository(tmp_path: Path) -> None:
    """Source digest materialization fails closed for a supplied non-repository directory."""
    checkout, commit = _disposable_fork_source(tmp_path)
    nested = checkout / "vendor" / "extracted-tree"
    nested.mkdir(parents=True)
    (nested / "marker.txt").write_text("nested\n", encoding="utf-8")

    with pytest.raises(IntegrityError, match="archive failed"):
        lifecycle._materialize_git_archive(nested, commit, tmp_path / "materialized")


def test_git_environment_deletes_ambient_repository_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A supplied-tree Git call cannot inherit an ambient repository binding.

    The isolated copy keeps ``GIT_*`` from the process environment, so the bindings have to
    be deleted from that mapping: an overlay that merely omits them leaves the inherited
    ``GIT_DIR`` in place and Git addresses whatever repository it names.
    """

    checkout, _ = _disposable_fork_source(tmp_path)
    supplied_non_repository = tmp_path / "supplied-non-repository"
    supplied_non_repository.mkdir()

    monkeypatch.setenv("GIT_DIR", str(_this_repository_git_entry()))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(_this_repository_object_directory()))
    monkeypatch.setenv("GIT_ALTERNATE_OBJECT_DIRECTORIES", str(_this_repository_object_directory()))

    checkout_environment = lifecycle._git_environment(checkout)
    assert "GIT_DIR" not in checkout_environment
    assert "GIT_OBJECT_DIRECTORY" not in checkout_environment
    assert "GIT_ALTERNATE_OBJECT_DIRECTORIES" not in checkout_environment
    assert "GIT_CEILING_DIRECTORIES" not in checkout_environment

    fenced_environment = lifecycle._git_environment(supplied_non_repository)
    assert "GIT_DIR" not in fenced_environment
    assert "GIT_OBJECT_DIRECTORY" not in fenced_environment
    assert "GIT_ALTERNATE_OBJECT_DIRECTORIES" not in fenced_environment
    # The only binding left is the deliberate ceiling that fences discovery at the tree.
    assert fenced_environment["GIT_CEILING_DIRECTORIES"] == str(
        supplied_non_repository.resolve().parent
    )


def test_materialize_git_archive_refuses_ambient_repository_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ambient binding cannot make a supplied non-repository archive another repository."""

    supplied = tmp_path / "supplied-non-repository"
    supplied.mkdir()
    (supplied / "ONLY-SUPPLIED.txt").write_text("supplied\n", encoding="utf-8")
    destination = tmp_path / "materialized"

    monkeypatch.setenv("GIT_DIR", str(_this_repository_git_entry()))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(_this_repository_object_directory()))

    with pytest.raises(IntegrityError, match="archive failed"):
        lifecycle._materialize_git_archive(supplied, FORK_COMMIT, destination)
    assert not destination.exists()

    # Separately, with only the object directory pointed at this checkout.
    monkeypatch.delenv("GIT_DIR")
    with pytest.raises(IntegrityError, match="archive failed"):
        lifecycle._materialize_git_archive(supplied, FORK_COMMIT, destination)
    assert not destination.exists()


def test_source_materialization_binds_a_supplied_checkout_under_ambient_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With an ambient binding set, a supplied checkout still archives only its own commit."""

    checkout, commit = _disposable_fork_source(tmp_path, marker="SUPPLIED-CHECKOUT-ENTRY")
    monkeypatch.setenv("GIT_DIR", str(_this_repository_git_entry()))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(_this_repository_object_directory()))

    destination = tmp_path / "materialized"
    lifecycle._materialize_git_archive(checkout, commit, destination)

    entry = destination / "ui-tui" / "package.json"
    assert entry.is_file()
    assert "SUPPLIED-CHECKOUT-ENTRY" in entry.read_text(encoding="utf-8")
    assert not (destination / "pyproject.toml").exists()


def test_projection_spec_branded_actions_and_tui_env(tmp_path: Path) -> None:
    """Projections generate branded Aether/Continue Aether actions, WSL adapters, and HERMES_TUI_DIR."""
    project_root = tmp_path / "my-project"
    project_root.mkdir(parents=True, exist_ok=True)
    manager = _manager(tmp_path, project_root=project_root)
    record = _record_with_tui(manager.store, "1.0.0rc4-" + "a" * 16, "f" * 64)

    spec = manager.projection_spec(record)

    # 1. Launcher projection sets HERMES_TUI_DIR
    launcher_text = spec.launcher_bytes.decode("utf-8")
    assert "export HERMES_TUI_DIR=" in launcher_text
    assert "AETHER_RUNTIME_ROOT/tui" in launcher_text
    assert 'exec "$AETHER_RUNTIME_ROOT/venv/bin/aether" "$@"' in launcher_text

    # 2. Service projection sets HERMES_TUI_DIR
    service_text = spec.service_bytes.decode("utf-8")
    assert f'Environment="HERMES_TUI_DIR={spec.runtime_current}/tui"' in service_text

    # 3. Linux Desktop entry has Aether and Continue Aether
    desktop_text = spec.desktop_bytes.decode("utf-8")
    assert "Name=Aether" in desktop_text
    assert "Terminal=true" in desktop_text
    assert f"Exec={spec.runtime_current}/venv/bin/aether --project {project_root}" in desktop_text
    assert "Actions=Continue;" in desktop_text
    assert "[Desktop Action Continue]" in desktop_text
    assert "Name=Continue Aether" in desktop_text
    assert f"--project {project_root} --resume latest" in desktop_text

    # 4. WSL Windows Terminal shortcuts generated in disposable roots
    assert "aether" in spec.wsl_shortcuts
    assert "continue_aether" in spec.wsl_shortcuts
    aether_cmd_path, aether_cmd_bytes = spec.wsl_shortcuts["aether"]
    continue_cmd_path, continue_cmd_bytes = spec.wsl_shortcuts["continue_aether"]

    aether_cmd_text = aether_cmd_bytes.decode("utf-8")
    continue_cmd_text = continue_cmd_bytes.decode("utf-8")
    assert "wt.exe" in aether_cmd_text
    assert "wsl.exe" in aether_cmd_text
    assert f'--project "{project_root}"' in aether_cmd_text
    assert "--resume latest" not in aether_cmd_text

    assert "wt.exe" in continue_cmd_text
    assert "wsl.exe" in continue_cmd_text
    assert f'--project "{project_root}" --resume latest' in continue_cmd_text


def test_projection_cycle_and_selector_agreement(tmp_path: Path) -> None:
    """Projecting, updating, rolling back, and uninstalling maintain exact selector coherence."""
    controller = RecordingServiceController()
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    manager = _manager(tmp_path, controller=controller, project_root=project_root)

    tui_bytes = b"console.log('tui-v1');\n"
    tui_hash = hashlib.sha256(tui_bytes).hexdigest()
    record1 = _record_with_tui(manager.store, "1.0.0rc4-" + "1" * 16, tui_hash)
    (manager.store.release_path(record1.release_id) / "tui" / "dist" / "entry.js").write_bytes(
        tui_bytes
    )
    _publish_record(manager, record1)

    outcome = manager.project_release(record1, restart_service=True)
    assert outcome["service_restart"] == "restarted"
    assert controller.calls == [AETHER_GATEWAY_UNIT]
    spec1 = manager.projection_spec(record1)

    assert spec1.runtime_current.is_symlink()
    assert spec1.runtime_current.resolve() == spec1.release
    current_tui = spec1.runtime_current / "tui" / "dist" / "entry.js"
    assert current_tui.is_file()
    assert current_tui.read_bytes() == tui_bytes

    # Check status is clean
    status = manager.projection_status(record1)
    assert status["mismatches"] == []

    # Verify deactivation removes projections
    manager._deactivate_lifecycle_projections(record1)
    assert not spec1.launcher_path.exists()
    assert not spec1.desktop_path.exists()
    assert not spec1.service_path.exists()
    for _, (wsl_path, _) in spec1.wsl_shortcuts.items():
        assert not wsl_path.exists()


def test_doctor_fail_closed_on_altered_or_missing_tui_bytes(tmp_path: Path) -> None:
    """Doctor reports fail-closed codes when TUI entry.js is missing or altered."""
    manager = _manager(tmp_path)
    tui_bytes = b"console.log('original-tui');\n"
    tui_hash = hashlib.sha256(tui_bytes).hexdigest()
    record = _record_with_tui(manager.store, "1.0.0rc4-" + "a" * 16, tui_hash)
    tui_entry = manager.store.release_path(record.release_id) / "tui" / "dist" / "entry.js"
    tui_entry.write_bytes(tui_bytes)
    _publish_record(manager, record)
    manager.project_release(record, restart_service=False)

    # Clean check
    status = manager.projection_status(record)
    assert "tui_asset_missing" not in status["mismatches"]
    assert "tui_asset_mismatch" not in status["mismatches"]

    # Altered TUI bytes
    tui_entry.write_bytes(b"console.log('tampered-tui');\n")
    status_altered = manager.projection_status(record)
    assert "tui_asset_mismatch" in status_altered["mismatches"]

    # Missing TUI bytes
    tui_entry.unlink()
    status_missing = manager.projection_status(record)
    assert "tui_asset_missing" in status_missing["mismatches"]


def test_projection_failure_restores_prior_opaque_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any failure during projection writing or switching restores the previous state."""
    manager = _manager(tmp_path)
    record1 = _record_with_tui(manager.store, "1.0.0rc4-" + "1" * 16)
    _publish_record(manager, record1)
    manager.project_release(record1, restart_service=False)

    spec1 = manager.projection_spec(record1)
    prior_launcher = spec1.launcher_path.read_bytes()
    prior_desktop = spec1.desktop_path.read_bytes()
    prior_target = spec1.runtime_current.resolve()

    record2 = _record_with_tui(manager.store, "1.0.0rc4-" + "2" * 16)
    spec2 = manager.projection_spec(record2)

    # Force failure on service projection
    original_write = manager._write_projection

    def failing_write(path: Path, data: bytes, *, mode: int) -> None:
        if path == spec2.service_path:
            raise IntegrityError("simulated projection write failure")
        original_write(path, data, mode=mode)

    monkeypatch.setattr(manager, "_write_projection", failing_write)

    with pytest.raises(IntegrityError, match="simulated projection write failure"):
        manager.project_release(record2, restart_service=False)

    # Prior state must be restored
    assert spec1.launcher_path.read_bytes() == prior_launcher
    assert spec1.desktop_path.read_bytes() == prior_desktop
    assert spec1.runtime_current.resolve() == prior_target


def test_locked_source_inventory_and_hashes_identical_after_tui_launch(tmp_path: Path) -> None:
    """Locked-source inventory and hashes identical before/after a real PTY launch with HERMES_TUI_DIR."""
    fork_source, fork_commit = _disposable_fork_source(tmp_path)
    source_dir = tmp_path / "hermes-source"
    archive = subprocess.run(
        ["git", "-C", str(fork_source), "archive", fork_commit],
        stdout=subprocess.PIPE,
        check=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-x"], input=archive.stdout, cwd=source_dir, check=True)

    # Inventory and hashes before launch (ignoring __pycache__ if any)
    def snapshot_tree(root: Path) -> dict[str, str]:
        results: dict[str, str] = {}
        for path in sorted(root.rglob("*")):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and not path.name.endswith(".pyc")
            ):
                rel = str(path.relative_to(root))
                results[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        return results

    before = snapshot_tree(source_dir)

    # Set up prebuilt TUI
    tui_dir = tmp_path / "prebuilt-tui"
    (tui_dir / "dist").mkdir(parents=True, exist_ok=True)
    stub_entry = tui_dir / "dist" / "entry.js"
    stub_entry.write_text("console.log('TUI READY'); process.exit(0);\n", encoding="utf-8")

    # Run Hermes PTY launch via python importing hermes_cli or invoking _make_tui_argv
    script = (
        "import sys, os, types, pty\n"
        "sys.dont_write_bytecode = True\n"
        "sys.modules['dotenv'] = types.ModuleType('dotenv')\n"
        "sys.modules['dotenv'].load_dotenv = lambda *a, **k: None\n"
        f"sys.path.insert(0, {str(source_dir)!r})\n"
        "os.environ['HERMES_TUI_DIR'] = "
        f"{str(tui_dir)!r}\n"
        "from hermes_cli.main import _make_tui_argv\n"
        f"argv, cwd = _make_tui_argv({str(source_dir / 'ui-tui')!r}, False)\n"
        "print('TUI_ARGV:', argv)\n"
        f"assert {str(stub_entry)!r} in argv\n"
        "import subprocess\n"
        "master, slave = pty.openpty()\n"
        "res = subprocess.run(argv, stdin=slave, stdout=slave, stderr=slave, check=False)\n"
        "os.close(master); os.close(slave)\n"
        "print('PTY_EXIT:', res.returncode)\n"
    )

    env = {**os.environ, "HERMES_TUI_DIR": str(tui_dir), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, "-B", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "TUI_ARGV:" in proc.stdout

    # Now verify locked source is unchanged
    after = snapshot_tree(source_dir)
    assert set(before.keys()) == set(after.keys())
    assert before == after
    assert not (source_dir / "node_modules").exists()
    assert not (source_dir / "ui-tui" / "node_modules").exists()


def test_operator_wsl_projections_and_legacy_desktop_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operator projections emit WSL adapters and clean up legacy hermes.desktop."""
    wsl_dir = tmp_path / "wsl-desktop"
    wsl_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AETHER_WSL_SHORTCUTS_DIR", str(wsl_dir))

    roots = ProjectionRoots(
        launcher_dir=tmp_path / "bin",
        desktop_dir=tmp_path / "applications",
        service_dir=tmp_path / "systemd",
        wsl_shortcuts_dir=lifecycle.detect_wsl_shortcuts_dir(),
    )
    assert roots.wsl_shortcuts_dir == wsl_dir

    # Pre-populate legacy hermes.desktop
    roots.desktop_dir.mkdir(parents=True, exist_ok=True)
    legacy_desktop = roots.desktop_dir / "hermes.desktop"
    legacy_desktop.write_text("[Desktop Entry]\nName=Legacy Hermes\n", encoding="utf-8")

    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    store = ReleaseStore(
        root=tmp_path / "data" / "aether",
        state_root=tmp_path / "state" / "aether",
    )
    manager = LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        service_controller=DisabledServiceController(),
        projections=roots,
        project_root=project_root,
    )

    tui_bytes = b"console.log('tui-op');\n"
    tui_hash = hashlib.sha256(tui_bytes).hexdigest()
    record = _record_with_tui(manager.store, "1.0.0rc4-" + "2" * 16, tui_hash)
    (manager.store.release_path(record.release_id) / "tui" / "dist" / "entry.js").write_bytes(
        tui_bytes
    )
    _publish_record(manager, record)

    spec = manager.projection_spec(record)
    assert "aether" in spec.wsl_shortcuts
    assert "continue_aether" in spec.wsl_shortcuts

    # Project release
    manager.project_release(record, restart_service=False)

    # Legacy desktop removed, aether.desktop created
    assert not legacy_desktop.exists()
    assert spec.desktop_path.is_file()

    # WSL adapters created
    aether_cmd, _ = spec.wsl_shortcuts["aether"]
    continue_cmd, _ = spec.wsl_shortcuts["continue_aether"]
    assert aether_cmd.is_file()
    assert continue_cmd.is_file()

    # Deactivate removes projections and adapters
    manager._deactivate_lifecycle_projections(record)
    assert not spec.desktop_path.exists()
    assert not aether_cmd.exists()
    assert not continue_cmd.exists()


def test_service_unit_drift_on_missing_or_tampered_hermes_tui_dir(tmp_path: Path) -> None:
    """Service unit dropping or altering HERMES_TUI_DIR is detected as drift."""
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    manager = _manager(tmp_path, project_root=project_root)

    tui_bytes = b"console.log('tui-service');\n"
    tui_hash = hashlib.sha256(tui_bytes).hexdigest()
    record = _record_with_tui(manager.store, "1.0.0rc4-" + "3" * 16, tui_hash)
    (manager.store.release_path(record.release_id) / "tui" / "dist" / "entry.js").write_bytes(
        tui_bytes
    )
    _publish_record(manager, record)

    manager.project_release(record, restart_service=False)
    spec = manager.projection_spec(record)

    # Baseline status is clean
    assert manager.projection_status(record)["mismatches"] == []

    # Strip Environment="HERMES_TUI_DIR=..." from service unit
    lines = spec.service_path.read_text(encoding="utf-8").splitlines()
    stripped_lines = [line for line in lines if not line.startswith('Environment="HERMES_TUI_DIR=')]
    tampered_bytes = ("\n".join(stripped_lines) + "\n").encode("utf-8")
    spec.service_path.write_bytes(tampered_bytes)

    assert not manager._service_unit_selects_release(tampered_bytes, spec)
    status = manager.projection_status(record)
    assert "service_projection_mismatch" in status["mismatches"]


def test_doctor_fails_closed_when_tui_is_none_or_missing(tmp_path: Path) -> None:
    """Doctor reports fail-closed mismatches when TUI asset is missing, even with tui_sha256=None."""
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    manager = _manager(tmp_path, project_root=project_root)

    # Published record with tui_sha256=None and no tui asset
    record = _record_with_tui(manager.store, "1.0.0rc4-" + "4" * 16, None)
    _publish_record(manager, record)

    status = manager.projection_status(record)
    assert "tui_asset_missing" in status["mismatches"]

    # An unbound asset is also a doctor failure, not a clean projection.
    unbound_entry = manager.store.release_path(record.release_id) / "tui" / "dist" / "entry.js"
    unbound_entry.parent.mkdir(parents=True, exist_ok=True)
    unbound_entry.write_bytes(b"unbound-tui")
    manager.project_release(record, restart_service=False)
    doctor = manager.doctor()
    assert "TUI_ASSET_UNBOUND" in doctor.codes


def test_exact_project_binding_fails_closed_without_exact_marker_or_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Projection spec fails closed unless the project binding is exact and verified."""
    # Run in an isolated directory without a marker
    isolated_dir = tmp_path / "empty-dir"
    isolated_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(isolated_dir)
    monkeypatch.delenv("AETHER_PROJECT_ID", raising=False)

    store = ReleaseStore(
        root=tmp_path / "data" / "aether",
        state_root=tmp_path / "state" / "aether",
    )
    manager = LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        service_controller=DisabledServiceController(),
        projections=ProjectionRoots.disposable(tmp_path / "projections"),
        # project_root is explicitly None
    )
    record = _record_with_tui(manager.store, "1.0.0rc4-" + "5" * 16, "a" * 64)

    # Must fail closed with IntegrityError (not fall back to store parent or guess)
    with pytest.raises(IntegrityError, match="exact project binding"):
        manager.projection_spec(record)

    # A marker without an agreeing registry entry is not an implicit binding.
    marker_only = tmp_path / "marker-only"
    (marker_only / ".aether").mkdir(parents=True, exist_ok=True)
    (marker_only / ".aether" / "project.toml").write_text(
        'project_id = "marker-without-registry"\n', encoding="utf-8"
    )
    monkeypatch.chdir(marker_only)
    with pytest.raises(IntegrityError, match="exact project binding"):
        manager.projection_spec(record)

    # Explicit project root succeeds
    valid_project = tmp_path / "valid-proj"
    valid_project.mkdir(parents=True, exist_ok=True)
    spec = manager.projection_spec(record, project_root=valid_project)
    assert f"--project {valid_project}" in spec.desktop_bytes.decode("utf-8")
