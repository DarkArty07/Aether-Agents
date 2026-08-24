"""Regression tests for the A1 observer release lifecycle (#221).

Every mutation in this module targets ``tmp_path``.  The real user installation,
profiles and services are deliberately outside the test surface.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import multiprocessing
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import zipfile
from pathlib import Path

import pytest
from observation_helpers import PROJECT_ID, TRACE_ID, complete_trace

import aether_agents.cli as cli_module
import aether_agents.lifecycle as lifecycle
from aether_agents.cli import main
from aether_agents.lifecycle import (
    HERMES_BASELINE,
    OBSERVATION_COMPATIBILITY,
    CheckoutEvidence,
    IntegrityError,
    LifecycleManager,
    PreparedRelease,
    ReleaseStore,
    verify_clean_checkout,
)
from aether_agents.observation.capture.journal import JournalWriter, list_segments, read_segment
from aether_agents.observation.checkpoint import (
    AuthorityContext,
    authority_context_from_state_root,
)
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import READ_MODEL_SCHEMA
from aether_agents.observation.reduce.ingest import reduce_trace
from aether_agents.observation.storage import ReadModel
from aether_agents.paths import ObservationPaths, atomic_private_write


def _allow_unit_manager_authority(
    manager: LifecycleManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep synthetic transition tests focused; real authority uses installed venvs."""

    monkeypatch.setattr(
        manager,
        "_assert_executing_active_manager_locked",
        lambda: manager.store.active(),
    )


def test_cli_lifecycle_separates_immutable_data_from_mutable_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "data"
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))

    manager = cli_module._lifecycle_manager()

    assert manager.store.root == data / "aether"
    assert manager.store.state_root == state / "aether"
    assert manager.store.releases == data / "aether" / "releases"
    assert manager.store.profile_homes == data / "aether" / "profiles"
    assert manager.store.transitions == state / "aether" / "transitions"


def _run_cas_transition(
    root: str,
    target_release_id: str,
    expected_active_release_id: str,
    start: object,
    results: object,
) -> None:
    """Spawn-safe contender used by the real cross-process CAS regression."""

    store = ReleaseStore(Path(root))
    start.wait()  # type: ignore[attr-defined]
    try:
        with store.mutation_lock():
            transition = store.begin_transition(
                kind="update",
                from_release_id=expected_active_release_id,
                to_release_id=target_release_id,
            )
            try:
                store.activate_existing(
                    target_release_id,
                    expected_active_release_id=expected_active_release_id,
                )
            except IntegrityError:
                store.finish_transition(
                    transition,
                    state="failed",
                    failure_code="ACTIVE_RELEASE_CAS_MISMATCH",
                )
                outcome = "stale"
            else:
                store.finish_transition(transition, state="committed")
                outcome = "committed"
    except BaseException as error:
        outcome = f"error:{type(error).__name__}"
    results.put(outcome)  # type: ignore[attr-defined]


def _hold_partial_transition(
    root: str,
    target_release_id: str,
    expected_active_release_id: str,
    entered: object,
    release: object,
) -> None:
    """Expose a pending/post-pointer boundary while retaining the process lock."""

    store = ReleaseStore(Path(root))
    with store.mutation_lock():
        transition = store.begin_transition(
            kind="update",
            from_release_id=expected_active_release_id,
            to_release_id=target_release_id,
        )
        store.activate_existing(
            target_release_id,
            expected_active_release_id=expected_active_release_id,
        )
        entered.set()  # type: ignore[attr-defined]
        if not release.wait(10):  # type: ignore[attr-defined]
            raise RuntimeError("test did not release held transition")
        store.finish_transition(transition, state="committed")


def _git(path: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _clean_tagged_checkout(tmp_path: Path) -> tuple[Path, str]:
    checkout = tmp_path / "hermes"
    checkout.mkdir()
    _git(checkout, "init", "-q")
    _git(checkout, "config", "user.name", "Aether Test")
    _git(checkout, "config", "user.email", "aether@example.invalid")
    (checkout / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n\n'
        '[project]\nname = "hermes-agent"\nversion = "0.20.4"\n'
        'requires-python = ">=3.11,<3.14"\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["hermes_cli"]\n',
        encoding="utf-8",
    )
    (checkout / "hermes_cli").mkdir()
    (checkout / "hermes_cli" / "__init__.py").write_text("", encoding="utf-8")
    (checkout / ".gitignore").write_text("*.egg-info/\n.env\n", encoding="utf-8")
    subprocess.run(
        ["uv", "lock", "--offline"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
    _git(
        checkout,
        "add",
        ".gitignore",
        "pyproject.toml",
        "uv.lock",
        "hermes_cli/__init__.py",
    )
    _git(checkout, "commit", "-qm", "fixture")
    _git(checkout, "tag", "-a", "fixture-v1", "-m", "fixture tag")
    return checkout, _git(checkout, "rev-parse", "HEAD")


def _prepared_release(root: Path, version: str, payload: bytes) -> PreparedRelease:
    wheel = root / f"aether_agents-{version}-py3-none-any.whl"
    wheel.parent.mkdir(parents=True, exist_ok=True)
    wheel.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    stage = root / f"prepared-{version}"
    for environment in ("manager", "runtime"):
        marker = stage / environment / "aether-wheel.sha256"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(digest + "\n", encoding="ascii")
    synthetic_manager_python = (
        stage / "manager" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    synthetic_manager_python.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        shutil.copy2(sys.executable, synthetic_manager_python)
    else:
        source_root = Path(__file__).parents[1] / "src"
        synthetic_manager_python.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            f"source = {str(source_root)!r}\n"
            "environment = dict(os.environ)\n"
            "environment['PYTHONPATH'] = source\n"
            "os.execvpe(sys.executable, [sys.executable, *sys.argv[1:]], environment)\n",
            encoding="utf-8",
        )
        synthetic_manager_python.chmod(0o700)
    resources = Path(lifecycle.__file__).parent / "resources" / "profiles"
    for role in ("morfeo", "supervisor", "implementer"):
        profile = stage / "profiles" / role / "config.yaml"
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_bytes((resources / role / "config.yaml").read_bytes())
    (stage / "release.json").write_text(
        json.dumps(
            {
                "version": version,
                "wheel_filename": wheel.name,
                "wheel_sha256": digest,
                "hermes_tag": HERMES_BASELINE.tag,
                "hermes_commit": HERMES_BASELINE.commit,
                "observer_entry_point": HERMES_BASELINE.observer_entry_point,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    aether_identity = _aether_identity(version)
    return PreparedRelease(
        version=version,
        wheel=wheel,
        wheel_sha256=digest,
        stage=stage,
        hermes_tag=HERMES_BASELINE.tag,
        hermes_commit=HERMES_BASELINE.commit,
        aether_identity=aether_identity,
        prebuild_identity=lifecycle.AetherPrebuildIdentity.from_record(aether_identity).digest,
        installed_file_fingerprint=hashlib.sha256(b"installed:" + payload).hexdigest(),
    )


def _prepared_release_with_target_manager(
    root: Path,
    version: str,
    wheel: Path,
    *,
    observation_compatibility: dict[str, object],
) -> PreparedRelease:
    """Create a synthetic record whose manager executes the actual target wheel."""

    prepared = _prepared_release(root, version, wheel.read_bytes())
    manager = prepared.stage / "manager"
    shutil.rmtree(manager)
    environment = lifecycle._isolated_subprocess_environment()
    subprocess.run(
        ["uv", "--no-config", "venv", "--python", sys.executable, str(manager)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    manager_python = LifecycleManager._environment_python(manager)
    subprocess.run(
        [
            "uv",
            "--no-config",
            "pip",
            "install",
            "--python",
            str(manager_python),
            str(prepared.wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    (manager / "aether-wheel.sha256").write_text(
        prepared.wheel_sha256 + "\n",
        encoding="ascii",
    )
    return lifecycle.replace(
        prepared,
        observation_compatibility=observation_compatibility,
    )


def _aether_identity(version: str) -> dict[str, object]:
    return {
        "distribution": "aether-agents",
        "package_version": version,
        "git_tag": f"v{version}",
        "git_commit": "a" * 40,
        "python_requires": ">=3.11,<3.14",
        "observer": {
            "plugin_name": "aether-contract-observer",
            "group": "hermes_agent.plugins",
            "target": "aether_agents.observation.capture.hermes_plugin",
        },
    }


def _profile_bundle_sha256() -> str:
    profiles: dict[str, dict[str, str]] = {}
    for role in ("morfeo", "supervisor", "implementer"):
        source = Path(lifecycle.__file__).parent / "resources" / "profiles" / role / "config.yaml"
        profiles[role] = {
            "path": f"profiles/{role}/config.yaml",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    manifest = {
        "schema_version": 1,
        "observer_entry_point": HERMES_BASELINE.observer_entry_point,
        "roles": ["morfeo", "supervisor", "implementer"],
        "profiles": profiles,
    }
    encoded = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def _source_tree_sha256(checkout: Path, commit: str) -> str:
    with tempfile.TemporaryDirectory(dir=checkout.parent) as temporary:
        destination = Path(temporary) / "source"
        lifecycle._materialize_git_archive(checkout, commit, destination)
        return lifecycle._tree_sha256(destination)


def _write_release_lock(
    root: Path,
    version: str,
    *,
    hermes_checkout: Path | None = None,
    hermes_commit: str | None = None,
    source_tree_sha256: str | None = None,
    observation_compatibility: dict[str, object] | None = None,
) -> Path:
    path = root / f"release-lock-{version}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 3,
        "aether": {
            "version": version,
            **_aether_identity(version),
            "observer_requirements_sha256": hashlib.sha256(
                (
                    Path(lifecycle.__file__).parent / "resources" / "observer-requirements.txt"
                ).read_bytes()
            ).hexdigest(),
            "observation_compatibility": (observation_compatibility or OBSERVATION_COMPATIBILITY),
        },
        "hermes": {
            "source_mode": "upstream",
            "repository": "https://github.com/NousResearch/hermes-agent",
            "version": HERMES_BASELINE.version,
            "tag": HERMES_BASELINE.tag,
            "commit": HERMES_BASELINE.commit,
            "python_requires": HERMES_BASELINE.python_requires,
            "source_tree_sha256": (
                source_tree_sha256
                or (
                    _source_tree_sha256(
                        hermes_checkout,
                        hermes_commit or HERMES_BASELINE.commit,
                    )
                    if hermes_checkout is not None
                    else "d" * 64
                )
            ),
            "artifacts": [
                {
                    "kind": "source",
                    "filename": "hermes-agent.tar.gz",
                    "url": "https://example.invalid/hermes-agent.tar.gz",
                    "sha256": "b" * 64,
                    "provenance_url": "https://example.invalid/provenance",
                }
            ],
        },
        "profile_bundle": {
            "version": "1",
            "sha256": _profile_bundle_sha256(),
            "roles": ["morfeo", "supervisor", "implementer"],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _build_wheel(
    root: Path,
    version: str,
    *,
    projection_schema: str = READ_MODEL_SCHEMA,
) -> Path:
    """Build the current source at ``version`` without mutating the shared checkout."""

    repository = Path(__file__).parents[1]
    source = root / f"source-{version}"
    source.mkdir(parents=True)
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(repository / name, source / name)
    (source / "VERSION").write_text(version + "\n", encoding="ascii")
    shutil.copytree(repository / "src", source / "src")
    contracts_module = source / "src" / "aether_agents" / "observation" / "contracts.py"
    contracts_bytes = contracts_module.read_text(encoding="utf-8")
    contracts_module.write_text(
        contracts_bytes.replace(
            f'READ_MODEL_SCHEMA: Final = "{READ_MODEL_SCHEMA}"',
            f'READ_MODEL_SCHEMA: Final = "{projection_schema}"',
        ),
        encoding="utf-8",
    )
    contracts = source / "specs" / "002-aether-contract-observation" / "contracts"
    contracts.parent.mkdir(parents=True)
    shutil.copytree(
        repository / "specs" / "002-aether-contract-observation" / "contracts",
        contracts,
    )
    a1_contracts = source / "specs" / "001-aether-v1-productization" / "contracts"
    a1_contracts.mkdir(parents=True)
    for schema_name in ("release-lock.schema.json", "project.schema.json"):
        shutil.copy2(
            repository
            / "specs"
            / "001-aether-v1-productization"
            / "contracts"
            / schema_name,
            a1_contracts / schema_name,
        )
    output = root / f"dist-{version}"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output)],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    )
    [wheel] = output.glob("*.whl")
    return wheel


def _tamper_wheel_member(
    wheel: Path,
    output: Path,
    suffix: str,
    rewrite,
) -> Path:
    with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(output, "w") as target:
        matched = 0
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.endswith(suffix):
                data = rewrite(data)
                matched += 1
            target.writestr(info, data)
    assert matched == 1
    return output


def _exact_hermes_checkout() -> Path:
    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
    if configured:
        return Path(configured)
    spec = importlib.util.find_spec("hermes_cli.plugins")
    if spec is None or spec.origin is None:
        pytest.skip("exact Hermes checkout is not present")
    return Path(spec.origin).resolve().parents[1]


def _exercise_installed_plugin(
    *,
    runtime_python: Path,
    profile_home: Path,
    environment: dict[str, str],
    role: str,
) -> dict[str, object]:
    script = r"""
import importlib.metadata as metadata
import json
import os
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

entrypoints = [
    ep for ep in metadata.entry_points().select(group="hermes_agent.plugins")
    if ep.name == "aether-contract-observer"
]
if len(entrypoints) != 1:
    raise RuntimeError("observer entry point is not unique")
module = entrypoints[0].load()
manager = PluginManager(scope_key=os.environ["HERMES_HOME"])
manifest = PluginManifest(
    name="aether-contract-observer",
    key="aether-contract-observer",
    source="entrypoint",
)
module.register(PluginContext(manifest, manager))
registered = sum(len(callbacks) for callbacks in manager._hooks.values())
role = os.environ["AETHER_TEST_ROLE"]
token = os.environ["AETHER_TEST_TOKEN"]
manager.invoke_hook(
    "pre_tool_call",
    tool_name="kanban_create",
    tool_call_id=f"create-{role}",
    session_id=f"session-{role}",
    turn_id=f"turn-{role}",
    api_request_id=f"api-create-{role}",
    args={"idempotency_key": token, "body": f"RAW_COMMAND_{role}_MUST_NOT_PERSIST"},
)
manager.invoke_hook(
    "post_tool_call",
    tool_name="kanban_create",
    tool_call_id=f"create-{role}",
    session_id=f"session-{role}",
    turn_id=f"turn-{role}",
    api_request_id=f"api-create-{role}",
    status="success",
    args={"idempotency_key": token},
    result={
        "ok": True,
        "task_id": "t_aaaaaaaa",
        "project_id": os.environ["AETHER_PROJECT_ID"],
    },
)
manager.invoke_hook(
    "pre_api_request",
    api_request_id=f"api-{role}",
    session_id=f"session-{role}",
    turn_id=f"turn-{role}",
    task_id="t_aaaaaaaa",
    model="model-test",
    provider="provider-test",
    prompt=f"RAW_PROMPT_{role}_MUST_NOT_PERSIST",
    message_count=1,
    tool_count=1,
)
manager.invoke_hook(
    "post_api_request",
    api_request_id=f"api-{role}",
    session_id=f"session-{role}",
    turn_id=f"turn-{role}",
    task_id="t_aaaaaaaa",
    model="model-test",
    provider="provider-test",
    status="completed",
    response=f"RAW_RESPONSE_{role}_MUST_NOT_PERSIST",
    usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
)
unloaded = manager.unload(manifest)
remaining = sum(len(callbacks) for callbacks in manager._hooks.values())
print(json.dumps({"registered": registered, "remaining": remaining, "unloaded": unloaded}))
"""
    run_environment = dict(environment)
    run_environment.update(
        {
            "HERMES_HOME": str(profile_home),
            "AETHER_TEST_ROLE": role,
            "AETHER_TEST_TOKEN": f"aether.obs.v1:{TRACE_ID}:t_aaaaaaaa",
        }
    )
    completed = subprocess.run(
        [str(runtime_python), "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=run_environment,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_release_lock_uses_the_exact_public_hermes_baseline() -> None:
    assert HERMES_BASELINE.repository == "https://github.com/NousResearch/hermes-agent.git"
    assert HERMES_BASELINE.tag == "v2026.8.18"
    assert HERMES_BASELINE.tag_object == "9f13bbbf8423427e159c78066356ca0e27ca6b74"
    assert HERMES_BASELINE.commit == "e624e9fde561e1add9388384012b295fde669ade"
    assert HERMES_BASELINE.distribution == "hermes-agent"
    assert HERMES_BASELINE.version == "0.20.4"


def test_release_record_schema_three_binds_exact_observation_compatibility(
    tmp_path: Path,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")

    record = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))

    assert record.schema_version == 3
    assert record.observer == {
        "plugin_name": "aether-contract-observer",
        "group": "hermes_agent.plugins",
        "target": "aether_agents.observation.capture.hermes_plugin",
    }
    assert record.observation_compatibility == OBSERVATION_COMPATIBILITY
    assert (
        record.observation_compatibility["event_write_version"]
        in record.observation_compatibility["event_read_versions"]
    )
    assert (
        record.observation_compatibility["summary_write_version"]
        in record.observation_compatibility["summary_read_versions"]
    )
    assert (
        record.observation_compatibility["segment_manifest_write_version"]
        in record.observation_compatibility["segment_manifest_read_versions"]
    )
    assert len(record.prebuild_identity) == 64
    assert set(record.prebuild_identity) <= set("0123456789abcdef")
    assert record.aether_identity == _aether_identity("1.0.0")
    assert record.installed_file_fingerprint != record.prebuild_identity


def test_release_record_refuses_write_schema_outside_its_read_set(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    pointer = json.loads(store.active_pointer.read_text(encoding="utf-8"))
    pointer["observation_compatibility"]["event_read_versions"] = ["aether.observation.event.v999"]

    with pytest.raises(IntegrityError, match="observation compatibility"):
        lifecycle.ReleaseRecord.from_json(pointer)


def test_release_record_accepts_a_well_formed_future_projection_identity(
    tmp_path: Path,
) -> None:
    compatibility = {
        **OBSERVATION_COMPATIBILITY,
        "projection_schema_version": "aether.observation.projection.v2",
    }
    prepared = lifecycle.replace(
        _prepared_release(tmp_path / "r2", "1.1.0", b"wheel-two"),
        observation_compatibility=compatibility,
    )

    record = ReleaseStore(tmp_path / "state" / "aether").register(prepared)

    assert record.observation_compatibility == compatibility


def test_update_cannot_downgrade_projection_schema_without_explicit_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    prior = store.register(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    future_compatibility = {
        **OBSERVATION_COMPATIBILITY,
        "projection_schema_version": "aether.observation.projection.v2",
    }
    future_wheel = _build_wheel(
        tmp_path / "future-wheel",
        "1.1.0",
        projection_schema=future_compatibility["projection_schema_version"],
    )
    future = store.activate(
        _prepared_release_with_target_manager(
            tmp_path / "r2",
            "1.1.0",
            future_wheel,
            observation_compatibility=future_compatibility,
        )
    )
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )

    with pytest.raises(IntegrityError, match="projection schema downgrade"):
        manager.activate_existing(
            prior.release_id,
            transition_kind="update",
            expected_active_release_id=future.release_id,
        )

    assert store.active().release_id == future.release_id


def test_activation_materializes_three_explicit_profile_homes_under_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    prepared = _prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one")
    record = store.register(prepared)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )

    manager.activate_existing(
        record.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    for role in ("morfeo", "supervisor", "implementer"):
        home = store.profile_home(role)
        assert home == store.root / "profiles" / role
        assert (home / "config.yaml").read_bytes() == (
            Path(lifecycle.__file__).parent / "resources" / "profiles" / role / "config.yaml"
        ).read_bytes()
        activation = json.loads((home / "aether-observer.json").read_text(encoding="utf-8"))
        assert activation == {
            "schema_version": 1,
            "role": role,
            "release_id": record.release_id,
            "wheel_sha256": record.wheel_sha256,
            "prebuild_identity": record.prebuild_identity,
            "installed_file_fingerprint": record.installed_file_fingerprint,
            "observer": {
                "plugin_name": "aether-contract-observer",
                "group": "hermes_agent.plugins",
                "target": "aether_agents.observation.capture.hermes_plugin",
            },
        }
        assert str(home) not in os.environ.get("HERMES_HOME", "")


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow profile authority")
def test_profile_activation_validation_rejects_check_then_symlink_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    prepared = _prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one")
    record = store.register(prepared)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    manager.activate_existing(
        record.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    activation = store.profile_home("morfeo") / "aether-observer.json"
    external = tmp_path / "external-profile-activation.json"
    external_bytes = activation.read_bytes()
    external.write_bytes(external_bytes)
    external.chmod(0o600)
    original_is_symlink = Path.is_symlink
    swapped = False

    def check_then_swap(path: Path) -> bool:
        nonlocal swapped
        result = original_is_symlink(path)
        if path == activation and not swapped:
            activation.unlink()
            activation.symlink_to(external)
            swapped = True
        return result

    monkeypatch.setattr(Path, "is_symlink", check_then_swap)

    with pytest.raises(IntegrityError, match="profile activation"):
        manager._validate_profile_homes(record)

    assert swapped
    assert external.read_bytes() == external_bytes


def test_checkout_verification_rejects_wrong_revision_and_dirty_state(tmp_path: Path) -> None:
    checkout, commit = _clean_tagged_checkout(tmp_path)
    evidence = verify_clean_checkout(
        checkout,
        expected_tag="fixture-v1",
        expected_commit=commit,
    )
    assert evidence.commit == commit
    assert evidence.clean is True
    with pytest.raises(IntegrityError, match="commit"):
        verify_clean_checkout(
            checkout,
            expected_tag="fixture-v1",
            expected_commit="0" * 40,
        )

    (checkout / "pyproject.toml").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="dirty"):
        verify_clean_checkout(
            checkout,
            expected_tag="fixture-v1",
            expected_commit=commit,
        )


def test_release_source_contains_only_tracked_commit_bytes_and_has_stable_digest(
    tmp_path: Path,
) -> None:
    checkout, commit = _clean_tagged_checkout(tmp_path)
    (checkout / ".env").write_text("IGNORED_SECRET_MUST_NOT_COPY\n", encoding="utf-8")
    egg_info = checkout / "hermes_agent.egg-info"
    egg_info.mkdir()
    (egg_info / "PKG-INFO").write_text("ignored editable debris\n", encoding="utf-8")

    first = tmp_path / "first-source"
    second = tmp_path / "second-source"
    lifecycle._materialize_git_archive(checkout, commit, first)
    lifecycle._materialize_git_archive(checkout, commit, second)

    tracked = set(_git(checkout, "ls-tree", "-r", "--name-only", commit).splitlines())
    first_files = {
        path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()
    }
    assert first_files == tracked
    assert not (first / ".env").exists()
    assert not (first / "hermes_agent.egg-info").exists()
    assert lifecycle._tree_sha256(first) == lifecycle._tree_sha256(second)


@pytest.mark.parametrize("unsafe_kind", ("traversal", "symlink", "device"))
def test_release_source_archive_extraction_rejects_unsafe_members(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive_writer:
        if unsafe_kind == "traversal":
            member = tarfile.TarInfo("../escape")
            member.size = 1
            archive_writer.addfile(member, io.BytesIO(b"x"))
        elif unsafe_kind == "symlink":
            member = tarfile.TarInfo("alias")
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
            archive_writer.addfile(member)
        else:
            member = tarfile.TarInfo("device")
            member.type = tarfile.CHRTYPE
            archive_writer.addfile(member)
    archive = stream.getvalue()
    destination = tmp_path / "source"

    with pytest.raises(IntegrityError, match="archive"):
        lifecycle._extract_git_archive(archive, destination)

    assert not (tmp_path / "escape").exists()


def test_wheel_fingerprint_binds_runtime_metadata_schemas_and_entry_points(
    tmp_path: Path,
) -> None:
    wheel = _build_wheel(tmp_path / "build", "1.0.0")

    identity = LifecycleManager._inspect_wheel(wheel)

    assert "prebuild_identity" not in identity
    assert len(identity["installed_file_fingerprint"]) == 64
    assert identity["observation_compatibility"] == OBSERVATION_COMPATIBILITY
    assert identity["observer"] == {
        "plugin_name": "aether-contract-observer",
        "group": "hermes_agent.plugins",
        "target": "aether_agents.observation.capture.hermes_plugin",
    }
    assert set(identity["observation_schema_sha256"]) == {"event", "summary", "manifest"}
    assert all(len(digest) == 64 for digest in identity["observation_schema_sha256"].values())
    assert len(identity["observer_requirements_sha256"]) == 64


def test_wheel_rejects_unapproved_third_plugin_entry_point(tmp_path: Path) -> None:
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    tampered = _tamper_wheel_member(
        wheel,
        tmp_path / "third-plugin.whl",
        ".dist-info/entry_points.txt",
        lambda data: data.replace(
            b"[hermes_agent.plugins]\n",
            b"[hermes_agent.plugins]\nhostile-extra = hostile.plugin\n",
            1,
        ),
    )

    with pytest.raises(IntegrityError, match="Aether plugin entry-point set"):
        LifecycleManager._inspect_wheel(tampered)


def test_wheel_inspection_binds_the_targets_own_projection_schema(tmp_path: Path) -> None:
    future_schema = "aether.observation.projection.v2"
    wheel = _build_wheel(
        tmp_path / "future-build",
        "1.1.0",
        projection_schema=future_schema,
    )

    identity = LifecycleManager._inspect_wheel(wheel)

    assert identity["observation_compatibility"] == {
        **OBSERVATION_COMPATIBILITY,
        "projection_schema_version": future_schema,
    }
    future_compatibility = identity["observation_compatibility"]
    validated_lock = lifecycle.load_release_lock(
        _write_release_lock(
            tmp_path / "matching-lock",
            "1.1.0",
            observation_compatibility=future_compatibility,
        )
    )
    LifecycleManager._validate_observer_lock_binding(validated_lock, identity)
    prepared = _prepared_release_with_target_manager(
        tmp_path / "installed-target",
        "1.1.0",
        wheel,
        observation_compatibility=future_compatibility,
    )
    target_identity = LifecycleManager._installed_aether_identity(
        LifecycleManager._environment_python(prepared.stage / "manager")
    )
    assert target_identity["observation_compatibility"] == future_compatibility

    mismatched_lock = lifecycle.load_release_lock(
        _write_release_lock(tmp_path / "mismatched-lock", "1.1.0")
    )
    with pytest.raises(IntegrityError, match="compatibility disagrees"):
        LifecycleManager._validate_observer_lock_binding(mismatched_lock, identity)


def test_wheel_observer_dependency_lock_rejects_unhashed_or_unexpected_closure(
    tmp_path: Path,
) -> None:
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    tampered = _tamper_wheel_member(
        wheel,
        tmp_path / "tampered.whl",
        "aether_agents/resources/observer-requirements.txt",
        lambda _data: b"jsonschema==4.26.0\n",
    )

    with pytest.raises(IntegrityError, match="observer dependency lock"):
        LifecycleManager._inspect_wheel(tampered)


def test_observer_dependency_markers_define_the_effective_python_closure() -> None:
    before_313 = lifecycle._observer_locked_distributions_for_version((3, 12))
    python_313 = lifecycle._observer_locked_distributions_for_version((3, 13))

    assert before_313["typing-extensions"] == "4.16.0"
    assert "typing-extensions" not in python_313
    assert {
        name: version for name, version in before_313.items() if name != "typing-extensions"
    } == (python_313)


@pytest.mark.parametrize(
    ("suffix", "old", "new", "reason"),
    (
        (".dist-info/METADATA", b"jsonschema==4.26.0", b"jsonschema>=4.23  ", "dependencies"),
        (".dist-info/WHEEL", b"Tag: py3-none-any", b"Tag: cp311-none-any", "compatibility"),
        (
            ".dist-info/entry_points.txt",
            b"aether = aether_agents.cli:main",
            b"aether = hostile.cli:main      ",
            "CLI entry point",
        ),
        (
            ".dist-info/entry_points.txt",
            b"aether-contract-observer = aether_agents.observation.capture.hermes_plugin",
            b"aether-contract-observer = hostile.plugin.register                         ",
            "observer entry",
        ),
    ),
)
def test_wheel_runtime_metadata_tampering_is_rejected(
    tmp_path: Path,
    suffix: str,
    old: bytes,
    new: bytes,
    reason: str,
) -> None:
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    tampered = _tamper_wheel_member(
        wheel,
        tmp_path / "tampered.whl",
        suffix,
        lambda data: data.replace(old, new, 1),
    )

    with pytest.raises(IntegrityError, match=reason):
        LifecycleManager._inspect_wheel(tampered)


def test_setup_parser_requires_an_explicit_release_lock_for_local_wheel() -> None:
    parser = cli_module._build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["setup", "--wheel", "a.whl", "--hermes-checkout", "hermes"])

    parsed = parser.parse_args(
        [
            "setup",
            "--wheel",
            "a.whl",
            "--hermes-checkout",
            "hermes",
            "--release-lock",
            "release-lock.json",
        ]
    )
    assert parsed.release_lock == Path("release-lock.json")


def test_prebuild_identity_is_the_canonical_non_circular_six_field_tuple() -> None:
    base = _aether_identity("1.0.0")
    identity = lifecycle.AetherPrebuildIdentity.from_record(base)

    assert identity.to_record() == base
    assert (
        identity.digest
        == hashlib.sha256(
            json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    for field in (
        "distribution",
        "package_version",
        "git_tag",
        "git_commit",
        "python_requires",
        "observer",
    ):
        changed = json.loads(json.dumps(base))
        if field == "package_version":
            changed[field] = "1.0.1"
        elif field == "git_tag":
            changed[field] = "v1.0.1"
        elif field == "observer":
            changed[field]["target"] += ".forged"
        elif field == "git_commit":
            changed[field] = "d" * 40
        else:
            changed[field] = str(changed[field]) + ".changed"
        if field in {"distribution", "python_requires", "observer"}:
            with pytest.raises(IntegrityError):
                lifecycle.AetherPrebuildIdentity.from_record(changed)
        else:
            assert lifecycle.AetherPrebuildIdentity.from_record(changed).digest != identity.digest


def test_release_lock_identity_is_explicit_and_semantically_matches_the_wheel(
    tmp_path: Path,
) -> None:
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    release_lock = _write_release_lock(tmp_path, "1.0.0")

    identity = lifecycle.load_aether_prebuild_identity(release_lock)
    wheel_identity = LifecycleManager._inspect_wheel(wheel)
    LifecycleManager._validate_aether_identity(identity, wheel_identity)

    assert identity.package_version == wheel_identity["version"]
    assert identity.digest != wheel_identity["installed_file_fingerprint"]
    payload = json.loads(release_lock.read_text(encoding="utf-8"))
    payload["aether"]["package_version"] = "9.9.9"
    release_lock.write_text(json.dumps(payload), encoding="utf-8")
    forged = lifecycle.load_aether_prebuild_identity(release_lock)
    with pytest.raises(IntegrityError, match="wheel"):
        LifecycleManager._validate_aether_identity(forged, wheel_identity)

    payload["aether"]["package_version"] = "1.0.0"
    payload["aether"]["observer_requirements_sha256"] = "e" * 64
    release_lock.write_text(json.dumps(payload), encoding="utf-8")
    forged_lock = lifecycle.load_release_lock(release_lock)
    with pytest.raises(IntegrityError, match="observer dependency digest"):
        LifecycleManager._validate_observer_lock_binding(forged_lock, wheel_identity)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda lock: lock["profile_bundle"].__setitem__("untrusted", True),
        lambda lock: lock["profile_bundle"].__setitem__(
            "roles", ["implementer", "supervisor", "morfeo"]
        ),
        lambda lock: lock["hermes"]["artifacts"][0].__setitem__(
            "url", "http://example.invalid/hermes-agent.tar.gz"
        ),
        lambda lock: lock["hermes"]["artifacts"][0].__setitem__("filename", "../escape"),
        lambda lock: lock["hermes"]["artifacts"][0].__setitem__("sha256", "not-a-digest"),
    ),
)
def test_release_lock_loader_validates_the_complete_schema(
    tmp_path: Path,
    mutate: object,
) -> None:
    release_lock = _write_release_lock(tmp_path, "1.0.0")
    payload = json.loads(release_lock.read_text(encoding="utf-8"))
    mutate(payload)  # type: ignore[operator]
    release_lock.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(IntegrityError, match="schema"):
        lifecycle.load_aether_prebuild_identity(release_lock)


def test_candidate_uv_environment_scrubs_every_ambient_uv_pip_and_python_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UV_INDEX_URL", "https://hostile.invalid/simple")
    monkeypatch.setenv("UV_PROJECT", "/hostile/project")
    monkeypatch.setenv("UV_PYTHON", "/hostile/python")
    monkeypatch.setenv("PIP_CONFIG_FILE", "/hostile/pip.conf")
    monkeypatch.setenv("PIP_TRUSTED_HOST", "hostile.invalid")
    monkeypatch.setenv("PYTHONPATH", "/hostile/source")
    monkeypatch.setenv("PYTHONHOME", "/hostile/home")

    environment = lifecycle._isolated_subprocess_environment()

    assert not any(key.startswith(("UV_", "PIP_", "PYTHON")) for key in environment)


def test_hermes_install_consumes_the_tracked_lock_with_frozen_hash_bound_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout, _ = _clean_tagged_checkout(tmp_path)
    runtime_python = tmp_path / "runtime" / "bin" / "python"
    manager = LifecycleManager(
        store=ReleaseStore(tmp_path / "state" / "aether"),
        python_executable=Path(sys.executable),
    )
    calls: list[tuple[tuple[str, ...], Path | None]] = []

    requirements = tmp_path / "artifacts" / "hermes-requirements.txt"
    requirements.parent.mkdir()

    def record(*arguments: str, cwd: Path | None = None) -> None:
        calls.append((arguments, cwd))
        if "--output-file" in arguments:
            requirements.write_text("# locked export\n", encoding="utf-8")

    monkeypatch.setattr(
        manager,
        "_run_uv",
        record,
    )

    evidence = manager._install_hermes_from_lock(checkout, runtime_python, requirements)

    assert evidence == {
        "uv_lock_sha256": hashlib.sha256((checkout / "uv.lock").read_bytes()).hexdigest(),
        "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
    }
    assert calls == [
        (
            (
                "--no-config",
                "export",
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--output-file",
                str(requirements),
            ),
            checkout,
        ),
        (
            (
                "--no-config",
                "pip",
                "sync",
                "--require-hashes",
                "--strict",
                "--python",
                str(runtime_python),
                str(requirements),
            ),
            checkout,
        ),
        (
            (
                "--no-config",
                "pip",
                "install",
                "--python",
                str(runtime_python),
                "--editable",
                str(checkout),
                "--no-deps",
            ),
            checkout,
        ),
    ]


def test_manager_observer_dependencies_are_synced_from_hash_bound_wheel_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(manager, "_run_uv", lambda *arguments: calls.append(arguments))
    manager_python = tmp_path / "manager" / "bin" / "python"
    requirements = tmp_path / "observer-requirements.txt"
    requirements.write_bytes(
        (Path(lifecycle.__file__).parent / "resources" / "observer-requirements.txt").read_bytes()
    )

    manager._install_observer_dependencies(manager_python, requirements)

    assert calls == [
        (
            "--no-config",
            "pip",
            "sync",
            "--require-hashes",
            "--strict",
            "--python",
            str(manager_python),
            str(requirements),
        ),
    ]


@pytest.mark.integration
def test_prepare_release_installs_one_wheel_in_manager_and_exact_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout, fixture_commit = _clean_tagged_checkout(tmp_path)
    distribution_dir = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--out-dir", str(distribution_dir)],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    [wheel] = distribution_dir.glob("*.whl")

    # Checkout-shape mechanics are covered separately above.  This integration slice
    # substitutes only the public release provenance so it can exercise the expensive
    # dual installation without cloning the network in the ordinary unit suite.
    monkeypatch.setattr(
        lifecycle,
        "verify_clean_checkout",
        lambda *_args, **_kwargs: CheckoutEvidence(
            path=checkout,
            tag=HERMES_BASELINE.tag,
            tag_object=HERMES_BASELINE.tag_object,
            commit=HERMES_BASELINE.commit,
            clean=True,
        ),
    )
    materialize = lifecycle._materialize_git_archive
    monkeypatch.setattr(
        lifecycle,
        "_materialize_git_archive",
        lambda source, _commit, destination: materialize(source, fixture_commit, destination),
    )
    store = ReleaseStore(tmp_path / "state" / "aether")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    prepared = manager.prepare_release(
        wheel=wheel,
        hermes_checkout=checkout,
        release_lock=_write_release_lock(
            tmp_path,
            "0.24.0",
            hermes_checkout=checkout,
            hermes_commit=fixture_commit,
        ),
    )
    record = store.register(prepared)
    record = manager.activate_existing(
        record.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    release = store.release_path(record.release_id)
    isolated_environment = lifecycle._isolated_subprocess_environment()
    source_module = Path(lifecycle.__file__).parent / "__init__.py"
    source_module_bytes = source_module.read_bytes()
    expected_profiles = Path(lifecycle.__file__).parent / "resources" / "profiles"
    assert (release / "profile-bundle.json").is_file()
    assert {child.name for child in (release / "profiles").iterdir() if child.is_dir()} == {
        "morfeo",
        "supervisor",
        "implementer",
    }
    for role in ("morfeo", "supervisor", "implementer"):
        expected_profile = (expected_profiles / role / "config.yaml").read_bytes()
        assert (release / "profiles" / role / "config.yaml").read_bytes() == expected_profile
    assert manager.validate_release(record.release_id) == record
    release_manifest = json.loads((release / "release.json").read_text(encoding="utf-8"))
    assert release_manifest["schema_version"] == 3
    assert release_manifest["observation_compatibility"] == OBSERVATION_COMPATIBILITY
    assert release_manifest["prebuild_identity"] == record.prebuild_identity
    assert set(release_manifest["observation_schema_sha256"]) == {
        "event",
        "summary",
        "manifest",
    }

    original_manifest = dict(release_manifest)

    durable_lock = release / "release-lock.json"
    assert durable_lock.is_file()
    durable_lock_bytes = durable_lock.read_bytes()
    durable_lock.write_bytes(durable_lock_bytes + b"\n")
    with pytest.raises(IntegrityError, match="release lock digest"):
        manager.validate_release(record.release_id)
    durable_lock.write_bytes(durable_lock_bytes)

    observer_dependency_lock = release / "artifacts" / "observer-requirements.txt"
    observer_dependency_lock_bytes = observer_dependency_lock.read_bytes()
    observer_dependency_lock.write_bytes(observer_dependency_lock_bytes + b"\n")
    with pytest.raises(IntegrityError, match="observer dependency lock digest"):
        manager.validate_release(record.release_id)
    observer_dependency_lock.write_bytes(observer_dependency_lock_bytes)

    hermes_source = release / "hermes-source"
    locked_source = hermes_source / "pyproject.toml"
    locked_source_bytes = locked_source.read_bytes()
    locked_source.write_bytes(locked_source_bytes + b"\n# source drift\n")
    with pytest.raises(IntegrityError, match="Hermes source digest"):
        manager.validate_release(record.release_id)
    locked_source.write_bytes(locked_source_bytes)

    release_manifest["observation_compatibility"] = {
        **OBSERVATION_COMPATIBILITY,
        "event_read_versions": ["aether.observation.event.v999"],
    }
    (release / "release.json").write_text(
        json.dumps(release_manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(IntegrityError, match="observation compatibility"):
        manager.validate_release(record.release_id)
    (release / "release.json").write_text(
        json.dumps(original_manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    profile = release / "profiles" / "morfeo" / "config.yaml"
    expected_morfeo_profile = (expected_profiles / "morfeo" / "config.yaml").read_bytes()
    profile.write_bytes(expected_morfeo_profile + b"# drift\n")
    with pytest.raises(IntegrityError, match="profile configuration drift"):
        manager.validate_release(record.release_id)
    profile.write_bytes(expected_morfeo_profile)

    artifact = release / "artifacts" / record.wheel_filename
    artifact_bytes = artifact.read_bytes()
    artifact.write_bytes(artifact_bytes + b"tampered")
    with pytest.raises(IntegrityError, match="artifact digest"):
        manager.validate_release(record.release_id)
    artifact.write_bytes(artifact_bytes)

    runtime_marker = release / "runtime" / "aether-wheel.sha256"
    runtime_marker.write_text("f" * 64 + "\n", encoding="ascii")
    with pytest.raises(IntegrityError, match="runtime wheel identity mismatch"):
        manager.validate_release(record.release_id)
    runtime_marker.write_text(record.wheel_sha256 + "\n", encoding="ascii")

    runtime = release / "runtime"
    [entry_points] = [
        path
        for path in runtime.rglob("entry_points.txt")
        if path.parent.name.startswith("aether_agents-")
    ]
    entry_points_bytes = entry_points.read_bytes()
    entry_points.write_text(
        "[hermes_agent.plugins]\naether-contract-observer = hostile.module\n",
        encoding="utf-8",
    )
    with pytest.raises(IntegrityError, match="observer entry point"):
        manager.validate_release(record.release_id)
    entry_points.write_bytes(entry_points_bytes)

    [hermes_metadata] = [
        path for path in runtime.rglob("METADATA") if path.parent.name.startswith("hermes_agent-")
    ]
    hermes_metadata_bytes = hermes_metadata.read_bytes()
    hermes_metadata.write_bytes(
        hermes_metadata_bytes.replace(b"Version: 0.20.4", b"Version: 9.9.9", 1)
    )
    with pytest.raises(IntegrityError, match="Hermes distribution version"):
        manager.validate_release(record.release_id)
    hermes_metadata.write_bytes(hermes_metadata_bytes)

    manager_script = release / "manager" / "bin" / "aether"
    manager_version = subprocess.run(
        [str(manager_script), "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=isolated_environment,
    )
    assert manager_version.stdout.strip() == f"aether {record.version}"
    identities = []
    for environment in ("manager", "runtime"):
        python = release / environment / "bin" / "python"
        completed = subprocess.run(
            [
                str(python),
                "-c",
                ("import importlib.metadata as m; print(m.version('aether-agents'))"),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=isolated_environment,
        )
        identities.append(completed.stdout.strip())
    assert identities == [record.version, record.version]
    dependency_versions = []
    for environment in ("manager", "runtime"):
        python = release / environment / "bin" / "python"
        completed = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.metadata as m; print(m.version('jsonschema'))",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=isolated_environment,
        )
        dependency_versions.append(completed.stdout.strip())
    assert dependency_versions == ["4.26.0", "4.26.0"]
    runtime_python = release / "runtime" / "bin" / "python"
    hermes = subprocess.run(
        [
            str(runtime_python),
            "-c",
            "import importlib.metadata as m; print(m.version('hermes-agent'))",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=isolated_environment,
    )
    assert hermes.stdout.strip() == HERMES_BASELINE.version
    doctor_manager = LifecycleManager(
        store=store,
        python_executable=manager._environment_python(release / "manager"),
    )
    synthetic_runtime = doctor_manager.doctor()
    assert synthetic_runtime.ready is False
    assert "OBSERVER_HOOK_PROBE_FAILED" in synthetic_runtime.codes

    installed_module = subprocess.run(
        [
            str(runtime_python),
            "-c",
            "import aether_agents,pathlib; print(pathlib.Path(aether_agents.__file__))",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=isolated_environment,
    ).stdout.strip()
    installed_module_path = Path(installed_module).resolve(strict=True)
    assert installed_module_path.is_relative_to((release / "runtime").resolve(strict=True))
    assert installed_module_path != source_module.resolve(strict=True)
    installed_module_path.write_bytes(
        installed_module_path.read_bytes() + b"\n# tampered after activation\n"
    )
    assert source_module.read_bytes() == source_module_bytes
    tampered = manager.doctor()
    assert tampered.ready is False
    assert "INSTALLED_FILE_FINGERPRINT_MISMATCH" in tampered.codes


def test_update_rollback_reupdate_preserves_unknown_observation_bytes(tmp_path: Path) -> None:
    state = tmp_path / "state" / "aether"
    store = ReleaseStore(state)
    observations = state / "observations" / "projects" / "p" / "journal" / "closed"
    observations.mkdir(parents=True)
    unknown = observations / "future.jsonl"
    unknown_bytes = b'{"schema_version":"aether.observation.event.v999","opaque":true}\n'
    unknown.write_bytes(unknown_bytes)

    first = _prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one")
    second = _prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two")
    first_record = store.activate(first)
    second_record = store.activate(second)

    assert second_record.previous_release_id == first_record.release_id
    assert store.active().release_id == second_record.release_id
    assert unknown.read_bytes() == unknown_bytes

    rolled_back = store.rollback()
    assert rolled_back.release_id == first_record.release_id
    assert unknown.read_bytes() == unknown_bytes

    restored = store.activate_existing(second_record.release_id)
    assert restored.release_id == second_record.release_id
    assert unknown.read_bytes() == unknown_bytes


def test_active_release_is_the_only_default_authority_source(tmp_path: Path) -> None:
    state = tmp_path / "state" / "aether"
    store = ReleaseStore(state)

    assert authority_context_from_state_root(state) == AuthorityContext.unavailable()

    active = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    authority = authority_context_from_state_root(state)
    assert authority.source == f"active_release:{active.release_id}"
    assert {principal.profile for principal in authority.principals} == {
        "morfeo",
        "supervisor",
        "implementer",
    }
    assert all(principal.assigned_review_refs != ("*",) for principal in authority.principals)
    assert authority.permits(
        "contract.completion_verified",
        actor_id="morfeo",
        profile="morfeo",
        role="verification",
    )
    assert not authority.permits(
        "contract.completion_verified",
        actor_id="implementer",
        profile="implementer",
        role="implementation",
    )

    pointer = json.loads(store.active_pointer.read_text(encoding="utf-8"))
    pointer["authority_context"]["principals"][0]["role"] = "implementation"
    store.active_pointer.write_text(json.dumps(pointer), encoding="utf-8")
    assert authority_context_from_state_root(state) == AuthorityContext.unavailable()


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow authority confinement")
def test_active_pointer_swap_after_symlink_check_cannot_grant_release_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    pointer = store.active_pointer
    external = tmp_path / "external-active.json"
    external_bytes = pointer.read_bytes()
    external.write_bytes(external_bytes)
    original_is_symlink = Path.is_symlink
    swapped = False

    def check_then_swap(path: Path) -> bool:
        nonlocal swapped
        result = original_is_symlink(path)
        if path == pointer and not swapped:
            pointer.unlink()
            pointer.symlink_to(external)
            swapped = True
        return result

    monkeypatch.setattr(Path, "is_symlink", check_then_swap)
    with pytest.raises(IntegrityError) as rejected:
        store.active()

    assert swapped
    assert str(external) not in str(rejected.value)
    assert external.read_bytes() == external_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow authority confinement")
def test_release_record_swap_after_release_path_check_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    record = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    release = store.release_path(record.release_id)
    record_path = release / "record.json"
    external = tmp_path / "external-record.json"
    external_bytes = record_path.read_bytes()
    external.write_bytes(external_bytes)
    original_is_symlink = Path.is_symlink
    swapped = False

    def check_then_swap(path: Path) -> bool:
        nonlocal swapped
        result = original_is_symlink(path)
        if path == release and not swapped:
            record_path.unlink()
            record_path.symlink_to(external)
            swapped = True
        return result

    monkeypatch.setattr(Path, "is_symlink", check_then_swap)
    with pytest.raises(IntegrityError) as rejected:
        store._read_release(record.release_id)

    assert swapped
    assert str(external) not in str(rejected.value)
    assert external.read_bytes() == external_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow recovery confinement")
def test_transition_swap_after_symlink_check_cannot_govern_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    active = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    transition = store.begin_transition(
        kind="update",
        from_release_id=active.release_id,
        to_release_id="1.0.1-" + "a" * 16,
    )
    external = tmp_path / "external-transition.json"
    external_bytes = transition.read_bytes()
    external.write_bytes(external_bytes)
    original_is_symlink = Path.is_symlink
    swapped = False

    def check_then_swap(path: Path) -> bool:
        nonlocal swapped
        result = original_is_symlink(path)
        if path == transition and not swapped:
            transition.unlink()
            transition.symlink_to(external)
            swapped = True
        return result

    monkeypatch.setattr(Path, "is_symlink", check_then_swap)
    with pytest.raises(IntegrityError) as rejected:
        store._read_transition(transition)

    assert swapped
    assert str(external) not in str(rejected.value)
    assert external.read_bytes() == external_bytes


def test_failed_activation_never_replaces_the_previous_coherent_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = _prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two")

    def fail_before_replace(_record: object) -> None:
        raise OSError("injected pointer failure")

    monkeypatch.setattr(store, "_commit_active", fail_before_replace)
    with pytest.raises(OSError, match="injected pointer failure"):
        store.activate(second)

    assert store.active().release_id == first.release_id


def test_recovery_removes_only_incomplete_release_state_and_preserves_journals(
    tmp_path: Path,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    active = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    incomplete = store.releases / "1.0.1-aaaaaaaaaaaaaaaa"
    incomplete.mkdir()
    (incomplete / "partial").write_bytes(b"candidate-only")
    pointer_temp = store.root / ".active.json.123.tmp"
    pointer_temp.write_bytes(b"partial pointer")
    journal = store.root / "observations" / "projects" / "p" / "journal" / "future"
    journal.parent.mkdir(parents=True)
    journal.write_bytes(b"unknown newer bytes")

    recovered = store.recover()

    assert recovered == {
        "incomplete_releases_removed": 1,
        "pointer_temps_removed": 1,
    }
    assert store.active().release_id == active.release_id
    assert journal.read_bytes() == b"unknown newer bytes"


def test_activate_existing_revalidates_and_restores_previous_after_post_switch_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.register(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    target_validations = 0
    _allow_unit_manager_authority(manager, monkeypatch)

    def validate(release_id: str):
        nonlocal target_validations
        record = store._read_release(release_id)
        if release_id == second.release_id:
            target_validations += 1
            if target_validations == 2:
                raise IntegrityError("post-switch validation failed")
        return record

    monkeypatch.setattr(manager, "validate_release", validate)
    with pytest.raises(IntegrityError, match="post-switch"):
        manager.activate_existing(second.release_id, transition_kind="update")

    assert store.active().release_id == first.release_id
    journals = sorted((store.root / "transitions").glob("*.json"))
    assert len(journals) == 1
    transition = json.loads(journals[0].read_text(encoding="utf-8"))
    assert transition["state"] == "failed"
    assert transition["failure_code"] == "TRANSITION_VALIDATION_FAILED"


def test_failed_compensation_leaves_transition_pending_for_durable_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.register(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    target_validations = 0

    def fail_after_target_switch(release_id: str):
        nonlocal target_validations
        record = store._read_release(release_id)
        if release_id == second.release_id:
            target_validations += 1
            if target_validations == 2:
                raise IntegrityError("post-switch target validation failed")
        return record

    monkeypatch.setattr(manager, "validate_release", fail_after_target_switch)
    commit_active = store._commit_active
    compensation_failed = False

    def fail_first_source_restore(record, *, expected_active_release_id=lifecycle._CAS_UNSET):
        nonlocal compensation_failed
        if (
            record.release_id == first.release_id
            and expected_active_release_id == second.release_id
            and not compensation_failed
        ):
            compensation_failed = True
            raise OSError("injected source pointer restore failure")
        return commit_active(
            record,
            expected_active_release_id=expected_active_release_id,
        )

    monkeypatch.setattr(store, "_commit_active", fail_first_source_restore)
    with pytest.raises(IntegrityError, match="compensation failed"):
        manager.activate_existing(
            second.release_id,
            transition_kind="update",
            expected_active_release_id=first.release_id,
        )

    assert compensation_failed is True
    transition = max(store.transitions.glob("trn_*.json"))
    assert json.loads(transition.read_text(encoding="utf-8"))["state"] == "pending"

    monkeypatch.setattr(store, "_commit_active", commit_active)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    recovered = manager.recover()
    assert recovered["active_release_restored"] == 1
    assert recovered["pending_transitions_recovered"] == 1
    assert store.active().release_id == first.release_id
    assert json.loads(transition.read_text(encoding="utf-8"))["state"] == "recovered"


def test_lifecycle_selects_each_active_release_projection_and_recovers_pointer_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lifecycle owner, never an ordinary reader, selects project projections."""

    data = tmp_path / "data" / "aether"
    state = tmp_path / "state" / "aether"
    store = ReleaseStore(data, state_root=state)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state)
    fixture = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    try:
        for event in fixture.events:
            assert writer.append(event).accepted
    finally:
        writer.close()

    # A non-project directory is foreign state.  Enumeration must neither inspect its
    # payload nor create a projection below it.
    foreign = state / "observations" / "projects" / "not-a-project-uuid"
    foreign.mkdir(parents=True)
    sentinel = foreign / "opaque.bin"
    sentinel.write_bytes(b"must-remain-opaque")

    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )

    manager.recover()

    projection_name = paths.projection_db(READ_MODEL_SCHEMA).name
    assert paths.projection_pointer.read_text(encoding="ascii") == projection_name + "\n"
    with ReadModel.open(paths) as model:
        assert len(model.events_for_trace(TRACE_ID)) == len(fixture.events)
    assert sentinel.read_bytes() == b"must-remain-opaque"
    assert not (foreign / "projections").exists()

    future_name = "aether.observation.projection.v999.sqlite3"
    future = paths.projections / future_name
    future_bytes = b"opaque-future-projection-bytes"
    future.write_bytes(future_bytes)
    atomic_private_write(paths.projection_pointer, (future_name + "\n").encode("ascii"))

    # Recovery reconciles a drifted pointer to the active release's declared schema,
    # without opening or rewriting a projection owned by a newer reader.
    manager.recover()
    assert paths.projection_pointer.read_text(encoding="ascii") == projection_name + "\n"
    assert future.read_bytes() == future_bytes

    future_schema = "aether.observation.projection.v2"
    future_compatibility = {
        **OBSERVATION_COMPATIBILITY,
        "projection_schema_version": future_schema,
    }
    future_wheel = _build_wheel(
        tmp_path / "future-wheel",
        "1.1.0",
        projection_schema=future_schema,
    )
    second = store.register(
        _prepared_release_with_target_manager(
            tmp_path / "r2",
            "1.1.0",
            future_wheel,
            observation_compatibility=future_compatibility,
        )
    )
    updated = manager.activate_existing(
        second.release_id,
        transition_kind="update",
        expected_active_release_id=first.release_id,
    )
    assert updated.release_id == second.release_id
    future_projection_name = paths.projection_db(future_schema).name
    assert paths.projection_pointer.read_text(encoding="ascii") == future_projection_name + "\n"
    assert paths.projection_db(READ_MODEL_SCHEMA).is_file()
    assert paths.projection_db(future_schema).is_file()
    with ReadModel.open(paths) as old_reader:
        assert len(old_reader.events_for_trace(TRACE_ID)) == len(fixture.events)
    assert paths.projection_pointer.read_text(encoding="ascii") == future_projection_name + "\n"

    rolled_back = manager.rollback(expected_active_release_id=second.release_id)
    assert rolled_back.release_id == first.release_id
    assert paths.projection_pointer.read_text(encoding="ascii") == projection_name + "\n"
    assert future.read_bytes() == future_bytes

    # Crash after the target release and its v2 pointer became visible but before the
    # transition journal committed. Recovery restores the durable source release and
    # executes that previous release's v1 runner to converge the pointer.
    with store.mutation_lock():
        pending = store._begin_transition_locked(
            kind="update",
            from_release_id=first.release_id,
            to_release_id=second.release_id,
        )
        pending_expectations = manager._prepare_release_projections_locked(second)
        store._commit_active(
            lifecycle.replace(second, previous_release_id=first.release_id),
            expected_active_release_id=first.release_id,
        )
        manager._select_release_projections_locked(second, pending_expectations)
    assert paths.projection_pointer.read_text(encoding="ascii") == future_projection_name + "\n"

    recovery = manager.recover()
    assert recovery["active_release_restored"] == 1
    assert recovery["pending_transitions_recovered"] == 1
    assert store.active().release_id == first.release_id
    assert paths.projection_pointer.read_text(encoding="ascii") == projection_name + "\n"
    assert json.loads(pending.read_text(encoding="utf-8"))["state"] == "recovered"
    assert paths.projection_db(future_schema).is_file()

    reupdated = manager.activate_existing(
        second.release_id,
        transition_kind="update",
        expected_active_release_id=first.release_id,
    )
    assert reupdated.release_id == second.release_id
    assert paths.projection_pointer.read_text(encoding="ascii") == future_projection_name + "\n"
    assert future.read_bytes() == future_bytes


def test_projection_publish_failure_restores_release_and_every_project_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One project failure cannot leave release/profile and projection authority split."""

    data = tmp_path / "data" / "aether"
    state = tmp_path / "state" / "aether"
    store = ReleaseStore(data, state_root=state)
    project_ids = (PROJECT_ID, "22222222-2222-4222-8222-222222222222")
    project_paths = [
        ObservationPaths.for_project(project_id, root=state).ensure() for project_id in project_ids
    ]
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    future_schema = "aether.observation.projection.v2"
    future_compatibility = {
        **OBSERVATION_COMPATIBILITY,
        "projection_schema_version": future_schema,
    }
    future_wheel = _build_wheel(
        tmp_path / "future-wheel",
        "1.1.0",
        projection_schema=future_schema,
    )
    second = store.register(
        _prepared_release_with_target_manager(
            tmp_path / "r2",
            "1.1.0",
            future_wheel,
            observation_compatibility=future_compatibility,
        )
    )
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    manager.recover()

    future_name = "aether.observation.projection.v999.sqlite3"
    for index, paths in enumerate(project_paths):
        future = paths.projections / future_name
        future.write_bytes(f"future-{index}".encode("ascii"))

    materialize_profiles = manager._materialize_profile_homes
    injected = False

    def materialize_then_break_second_cas(record) -> None:
        nonlocal injected
        materialize_profiles(record)
        if record.release_id == second.release_id and not injected:
            atomic_private_write(
                project_paths[1].projection_pointer,
                (future_name + "\n").encode("ascii"),
            )
            injected = True

    monkeypatch.setattr(manager, "_materialize_profile_homes", materialize_then_break_second_cas)
    with pytest.raises(IntegrityError, match="projection transition"):
        manager.activate_existing(
            second.release_id,
            transition_kind="update",
            expected_active_release_id=first.release_id,
        )

    assert injected is True
    assert store.active().release_id == first.release_id
    expected_name = project_paths[0].projection_db(READ_MODEL_SCHEMA).name + "\n"
    assert [paths.projection_pointer.read_text(encoding="ascii") for paths in project_paths] == [
        expected_name,
        expected_name,
    ]
    assert [(paths.projections / future_name).read_bytes() for paths in project_paths] == [
        b"future-0",
        b"future-1",
    ]
    transitions = sorted(store.transitions.glob("trn_*.json"))
    assert json.loads(transitions[-1].read_text(encoding="utf-8"))["state"] == "failed"


def test_bootstrap_partial_projection_failure_restores_opaque_original_pointers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Initial-install compensation never opens or discards pre-existing projections."""

    state = tmp_path / "state" / "aether"
    store = ReleaseStore(tmp_path / "data" / "aether", state_root=state)
    project_ids = (PROJECT_ID, "22222222-2222-4222-8222-222222222222")
    project_paths = [
        ObservationPaths.for_project(project_id, root=state).ensure() for project_id in project_ids
    ]
    original_name = "aether.observation.projection.v999.sqlite3"
    original_bytes = [b"opaque-original-0", b"opaque-original-1"]
    for paths, payload in zip(project_paths, original_bytes, strict=True):
        (paths.projections / original_name).write_bytes(payload)
        atomic_private_write(
            paths.projection_pointer,
            (original_name + "\n").encode("ascii"),
        )

    target = store.register(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    materialize_profiles = manager._materialize_profile_homes
    sabotaged = False

    def materialize_then_remove_second_target(record) -> None:
        nonlocal sabotaged
        materialize_profiles(record)
        if not sabotaged:
            for candidate in project_paths[1].projection_files(READ_MODEL_SCHEMA):
                candidate.unlink(missing_ok=True)
            sabotaged = True

    monkeypatch.setattr(
        manager,
        "_materialize_profile_homes",
        materialize_then_remove_second_target,
    )
    with pytest.raises(IntegrityError, match="projection transition"):
        manager.activate_existing(
            target.release_id,
            transition_kind="install",
            expected_active_release_id=None,
        )

    assert sabotaged is True
    assert store.active(required=False) is None
    assert [paths.projection_pointer.read_text(encoding="ascii") for paths in project_paths] == [
        original_name + "\n",
        original_name + "\n",
    ]
    assert [
        (paths.projections / original_name).read_bytes() for paths in project_paths
    ] == original_bytes
    transition = max(store.transitions.glob("trn_*.json"))
    assert json.loads(transition.read_text(encoding="utf-8"))["state"] == "failed"


def test_lifecycle_rejects_unselect_output_not_bound_to_the_requested_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    record = store.register(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    desired = "aether.observation.projection.v999.sqlite3"
    wrong = "aether.observation.projection.v998.sqlite3"

    monkeypatch.setattr(
        lifecycle.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "operation": "unselect",
                    "target_schema": READ_MODEL_SCHEMA,
                    "project_count": 1,
                    "unselected_count": 1,
                    "projects": [
                        {
                            "project_id": PROJECT_ID,
                            "previous_pointer": READ_MODEL_SCHEMA + ".sqlite3",
                            "selected_pointer": wrong,
                        }
                    ],
                }
            ),
            stderr="",
        ),
    )

    with pytest.raises(IntegrityError, match="incoherent"):
        manager._run_projection_transition_locked(
            record,
            operation="unselect",
            expected_pointers={PROJECT_ID: desired},
        )


def test_rollback_remains_available_when_active_hermes_runtime_is_broken(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.activate(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)

    def validate(release_id: str):
        if release_id == second.release_id:
            raise IntegrityError("active Hermes import is broken")
        return store._read_release(release_id)

    monkeypatch.setattr(manager, "validate_release", validate)

    rolled_back = manager.rollback(expected_active_release_id=second.release_id)

    assert rolled_back.release_id == first.release_id
    assert store.active().release_id == first.release_id


def test_stale_expected_active_cas_refuses_without_touching_pointer(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.register(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    stale = "1.0.9-" + "f" * 16
    before = store.active_pointer.read_bytes()

    with pytest.raises(IntegrityError, match="active release changed concurrently"):
        store.activate_existing(
            second.release_id,
            expected_active_release_id=stale,
        )

    assert store.active_pointer.read_bytes() == before
    assert store.active().release_id == first.release_id


def test_mutation_lock_is_private_confined_and_rejects_hardlink_alias(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path / "owned" / "aether")
    store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    lock_file = store.mutation_lock_file
    assert lock_file.parent == store.root.parent
    assert lock_file.name == ".aether.lifecycle.lock"
    assert lock_file.is_file() and not lock_file.is_symlink()
    if os.name == "posix":
        status = lock_file.stat()
        assert status.st_nlink == 1
        assert stat.S_IMODE(status.st_mode) == 0o600

        hostile_store = ReleaseStore(tmp_path / "hostile" / "aether")
        hostile_store.root.parent.mkdir(parents=True)
        outside = tmp_path / "outside.lock"
        outside.write_bytes(b"outside-bytes")
        os.link(outside, hostile_store.mutation_lock_file)
        with pytest.raises(IntegrityError, match="private regular file"):
            hostile_store.activate(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
        assert outside.read_bytes() == b"outside-bytes"
        assert not hostile_store.active_pointer.exists()


def test_two_process_transitions_with_one_expected_active_have_one_commit(
    tmp_path: Path,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.register(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    third = store.register(_prepared_release(tmp_path / "r3", "1.0.2", b"wheel-three"))
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    contenders = [
        context.Process(
            target=_run_cas_transition,
            args=(
                str(store.root),
                target.release_id,
                first.release_id,
                start,
                results,
            ),
        )
        for target in (second, third)
    ]
    for contender in contenders:
        contender.start()
    start.set()
    outcomes = [results.get(timeout=10) for _ in contenders]
    for contender in contenders:
        contender.join(timeout=10)
        assert contender.exitcode == 0

    assert sorted(outcomes) == ["committed", "stale"]
    assert store.active().release_id in {second.release_id, third.release_id}
    journals = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (store.root / "transitions").glob("*.json")
    ]
    assert {journal["state"] for journal in journals} == {"committed", "failed"}
    assert {journal["failure_code"] for journal in journals if journal["state"] == "failed"} == {
        "ACTIVE_RELEASE_CAS_MISMATCH"
    }


def test_doctor_and_recover_wait_for_one_complete_transition_view(tmp_path: Path) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.register(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    context = multiprocessing.get_context("spawn")
    entered = context.Event()
    release = context.Event()
    writer = context.Process(
        target=_hold_partial_transition,
        args=(
            str(store.root),
            second.release_id,
            first.release_id,
            entered,
            release,
        ),
    )
    writer.start()
    try:
        assert entered.wait(2), "transition process did not reach its held boundary"
        manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
        observed: dict[str, object] = {}
        completed = threading.Event()

        def inspect_and_recover() -> None:
            observed["doctor"] = manager.doctor()
            observed["recover"] = store.recover()
            completed.set()

        reader = threading.Thread(target=inspect_and_recover, daemon=True)
        reader.start()
        assert completed.wait(0.25) is False
        release.set()
        reader.join(timeout=10)
        assert completed.is_set()
    finally:
        release.set()
        writer.join(timeout=10)
    assert writer.exitcode == 0
    doctor = observed["doctor"]
    assert doctor.active_release_id == second.release_id  # type: ignore[union-attr]
    assert observed["recover"] == {
        "incomplete_releases_removed": 0,
        "pointer_temps_removed": 0,
    }
    assert store.active().release_id == second.release_id
    [journal] = (store.root / "transitions").glob("*.json")
    assert json.loads(journal.read_text(encoding="utf-8"))["state"] == "committed"


def test_recover_uses_pending_transition_to_restore_last_coherent_active_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.register(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    transitions = store.root / "transitions"
    transitions.mkdir(mode=0o700)
    pending = transitions / ("trn_" + "1" * 32 + ".json")
    pending.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "transition_id": "trn_" + "1" * 32,
                "kind": "update",
                "state": "pending",
                "from_release_id": first.release_id,
                "to_release_id": second.release_id,
                "failure_code": None,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    pending.chmod(0o600)
    store._commit_active(second)
    store.active_pointer.write_text("{partial", encoding="utf-8")
    unknown = store.root / "observations" / "future.bin"
    unknown.parent.mkdir(parents=True)
    unknown.write_bytes(b"future-observation-bytes")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )

    with store.mutation_lock():
        recovered = manager._recover_locked()

    assert recovered["active_release_restored"] == 1
    assert recovered["pending_transitions_recovered"] == 1
    assert store.active().release_id == first.release_id
    assert unknown.read_bytes() == b"future-observation-bytes"
    assert json.loads(pending.read_text(encoding="utf-8"))["state"] == "recovered"


@pytest.mark.parametrize("pointer_switched", (False, True))
def test_initial_install_recovery_deactivates_only_aether_profile_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pointer_switched: bool,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    target = store.register(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    transition = store.begin_transition(
        kind="install",
        from_release_id=None,
        to_release_id=target.release_id,
    )
    manager._materialize_profile_homes(target)
    user_state = store.profile_home("morfeo") / "sessions.sqlite3"
    user_state.write_bytes(b"user-owned")
    if pointer_switched:
        store._commit_active(target, expected_active_release_id=None)

    recovered = manager.recover()

    assert recovered["pending_transitions_recovered"] == 1
    assert store.active(required=False) is None
    for role in ("morfeo", "supervisor", "implementer"):
        home = store.profile_home(role)
        assert not (home / "aether-observer.json").exists()
        assert not (home / "config.yaml").exists()
    assert user_state.read_bytes() == b"user-owned"
    assert json.loads(transition.read_text(encoding="utf-8"))["state"] == "recovered"


def test_rollback_uses_the_durable_predecessor_of_the_latest_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.activate(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    third = store.activate(_prepared_release(tmp_path / "r3", "1.0.2", b"wheel-three"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )

    reactivated = manager.activate_existing(
        second.release_id,
        transition_kind="update",
        expected_active_release_id=third.release_id,
    )
    assert reactivated.previous_release_id == third.release_id

    rolled_back = manager.rollback(expected_active_release_id=second.release_id)

    assert rolled_back.release_id == third.release_id
    assert rolled_back.previous_release_id == second.release_id
    assert first.release_id not in {
        rolled_back.release_id,
        rolled_back.previous_release_id,
    }


def test_pending_recovery_preserves_the_source_activation_predecessor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    second = store.activate(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))
    third = store.activate(_prepared_release(tmp_path / "r3", "1.0.2", b"wheel-three"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    manager.activate_existing(
        second.release_id,
        transition_kind="update",
        expected_active_release_id=third.release_id,
    )
    transition = store.begin_transition(
        kind="update",
        from_release_id=second.release_id,
        to_release_id=first.release_id,
    )
    store._commit_active(first, expected_active_release_id=second.release_id)

    manager.recover()

    restored = store.active()
    assert restored is not None
    assert restored.release_id == second.release_id
    assert restored.previous_release_id == third.release_id
    assert json.loads(transition.read_text(encoding="utf-8"))["state"] == "recovered"
    assert (
        manager.rollback(expected_active_release_id=second.release_id).release_id
        == third.release_id
    )


def test_doctor_reports_only_content_free_observer_state_and_permission_health(
    tmp_path: Path,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    record = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    observations = store.root / "observations"
    health = observations / "health" / "counters.json"
    journal = (
        observations / "projects" / "secret-project-id" / "journal" / "closed" / "secret.jsonl"
    )
    projection = (
        observations
        / "projects"
        / "secret-project-id"
        / "projections"
        / "aether.observation.projection.v1.sqlite3"
    )
    for path in (health, journal, projection):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"PRIVATE_REASON_CODE":2}\n' if path == health else "opaque\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
    journal.chmod(0o644)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    result = manager.doctor()

    assert result.active_release_id == record.release_id
    assert result.details["observer_state"] == {
        "health_counter_classes": 1,
        "health_counter_total": 2,
        "journal_file_count": 1,
        "project_count": 1,
        "projection_file_count": 1,
        "quarantine_file_count": 0,
        "projection_integrity_failures": 1,
        "summary_file_count": 0,
        "incomplete_summary_count": 0,
        "invalid_summary_count": 0,
    }
    assert "OBSERVATION_PERMISSION_MISMATCH" in result.codes
    rendered = json.dumps(result.details, sort_keys=True)
    assert "secret-project-id" not in rendered
    assert "secret.jsonl" not in rendered
    assert "PRIVATE_REASON_CODE" not in rendered


def test_doctor_inspects_projection_integrity_and_summary_coverage_without_content(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data" / "aether"
    state = tmp_path / "state" / "aether"
    store = ReleaseStore(data, state_root=state)
    paths = ObservationPaths.for_project(PROJECT_ID, root=state)
    fixture = complete_trace()
    with ReadModel.open(paths) as read_model:
        read_model.upsert_events(fixture.events)
    reduce_trace(paths, TRACE_ID)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    details, permissions_ok = manager._observer_state_details()

    assert permissions_ok is True
    assert details["projection_file_count"] == 1
    assert details["projection_integrity_failures"] == 0
    assert details["summary_file_count"] == 1
    assert details["incomplete_summary_count"] == 1
    assert details["invalid_summary_count"] == 0


def test_purge_refuses_unowned_root_and_any_symlinked_ancestor(tmp_path: Path) -> None:
    unowned = tmp_path / "unowned" / "aether"
    unowned.mkdir(parents=True)
    manager = LifecycleManager(store=ReleaseStore(unowned), python_executable=Path(sys.executable))
    with pytest.raises(IntegrityError, match="owned"):
        manager.uninstall(purge=True, confirmed=True)
    assert unowned.is_dir()

    if os.name != "posix":
        return
    real_parent = tmp_path / "real-parent"
    real_root = real_parent / "aether"
    real_store = ReleaseStore(real_root)
    real_store.activate(_prepared_release(tmp_path / "r3", "1.0.2", b"wheel-three"))
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(real_parent, target_is_directory=True)
    aliased = LifecycleManager(
        store=ReleaseStore(alias_parent / "aether"),
        python_executable=Path(sys.executable),
    )
    with pytest.raises(IntegrityError, match="symlink"):
        aliased.uninstall(purge=True, confirmed=True)
    assert real_root.is_dir()


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow purge authority")
def test_purge_refuses_ownership_marker_swapped_after_symlink_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "owned" / "aether"
    store = ReleaseStore(root)
    store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    sentinel = root / "user-sentinel"
    sentinel.write_bytes(b"must-not-delete")
    marker = store.ownership_marker
    external = tmp_path / "external-ownership.json"
    external_bytes = marker.read_bytes()
    external.write_bytes(external_bytes)
    external.chmod(0o600)
    original_is_symlink = Path.is_symlink
    swapped = False

    def check_then_swap(path: Path) -> bool:
        nonlocal swapped
        result = original_is_symlink(path)
        if path == marker and not swapped:
            marker.unlink()
            marker.symlink_to(external)
            swapped = True
        return result

    monkeypatch.setattr(Path, "is_symlink", check_then_swap)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    error: Exception | None = None
    try:
        manager.uninstall(purge=True, confirmed=True)
    except Exception as exc:
        error = exc

    assert isinstance(error, IntegrityError)
    assert swapped
    assert root.is_dir()
    assert sentinel.read_bytes() == b"must-not-delete"
    assert external.read_bytes() == external_bytes


def test_cli_setup_requires_explicit_opt_in_before_local_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wheel = tmp_path / "aether.whl"
    checkout = tmp_path / "hermes"
    wheel.write_bytes(b"wheel")
    checkout.mkdir()
    calls: list[str] = []

    class FakeManager:
        def active_manager_dispatch_target(self):
            return None

        def inspect_candidate(self, *, wheel: Path, hermes_checkout: Path, release_lock: Path):
            calls.append("inspect")
            return {
                "version": "1.0.0",
                "wheel_filename": wheel.name,
                "wheel_sha256": "a" * 64,
            }

        def install(self, *, wheel: Path, hermes_checkout: Path, release_lock: Path):
            calls.append("install")
            return type(
                "Record",
                (),
                {
                    "release_id": "1.0.0-" + "a" * 16,
                    "version": "1.0.0",
                    "wheel_sha256": "a" * 64,
                },
            )()

    monkeypatch.setattr(cli_module, "_lifecycle_manager", FakeManager)
    args = [
        "setup",
        "--wheel",
        str(wheel),
        "--hermes-checkout",
        str(checkout),
        "--release-lock",
        str(_write_release_lock(tmp_path, "1.0.0")),
        "--json",
    ]
    assert main(args) == 0
    planned = json.loads(capsys.readouterr().out)
    assert planned["result"] == "planned"
    assert calls == ["inspect"]

    assert main([*args[:-1], "--yes", "--json"]) == 0
    installed = json.loads(capsys.readouterr().out)
    assert installed["result"] == "changed"
    assert calls == ["inspect", "install"]


def test_non_active_manager_cannot_mutate_with_a_different_wheel_or_same_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching version string is not active-manager authority (A1-FR-063)."""

    store = ReleaseStore(tmp_path / "state" / "aether")
    active = store.activate(_prepared_release(tmp_path / "active", "1.0.0", b"wheel-one"))
    candidate = store.register(_prepared_release(tmp_path / "candidate", "1.0.0", b"wheel-two"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )

    with pytest.raises(IntegrityError, match="active manager"):
        manager.activate_existing(
            candidate.release_id,
            transition_kind="update",
            expected_active_release_id=active.release_id,
        )

    unavailable = tmp_path / "must-not-be-inspected-before-authority"
    with pytest.raises(IntegrityError, match="active manager"):
        manager.update(
            wheel=unavailable,
            hermes_checkout=unavailable,
            release_lock=unavailable,
            expected_active_release_id=active.release_id,
        )
    with pytest.raises(IntegrityError, match="active manager"):
        manager.rollback(expected_active_release_id=active.release_id)
    with pytest.raises(IntegrityError, match="active manager"):
        manager.uninstall(purge=False, confirmed=True)

    assert store.active().release_id == active.release_id
    assert store._read_release(candidate.release_id).wheel_sha256 == candidate.wheel_sha256


@pytest.mark.integration
@pytest.mark.hermes_exact
def test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One no-monkeypatch evidence lane for #221 against the exact public checkout."""

    checkout = _exact_hermes_checkout()
    evidence = verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    assert evidence.clean is True
    hermes_source_tree_sha256 = _source_tree_sha256(checkout, HERMES_BASELINE.commit)
    first_wheel = _build_wheel(tmp_path / "first-build", "1.0.0")
    second_wheel = _build_wheel(tmp_path / "second-build", "1.0.1")
    data_home = tmp_path / "data"
    state_home = tmp_path / "state"
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    store = ReleaseStore(data_home / "aether", state_root=state_home / "aether")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    first = manager.install(
        wheel=first_wheel,
        hermes_checkout=checkout,
        release_lock=_write_release_lock(
            tmp_path,
            "1.0.0",
            source_tree_sha256=hermes_source_tree_sha256,
        ),
        expected_active_release_id=None,
    )
    release = store.release_path(first.release_id)
    first_manager = LifecycleManager(
        store=store,
        python_executable=manager._environment_python(release / "manager"),
    )
    runtime_python = manager._environment_python(release / "runtime")
    environment = lifecycle._isolated_subprocess_environment()
    environment.update(
        {
            "XDG_DATA_HOME": str(data_home),
            "XDG_STATE_HOME": str(state_home),
            "AETHER_PROJECT_ID": PROJECT_ID,
        }
    )

    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(f'project_id = "{PROJECT_ID}"\n', encoding="utf-8")
    assert ProjectRegistry().register(PROJECT_ID, project, "lifecycle-exact")

    hook_results = {
        role: _exercise_installed_plugin(
            runtime_python=runtime_python,
            profile_home=store.profile_home(role),
            environment=environment,
            role=role,
        )
        for role in ("morfeo", "supervisor", "implementer")
    }
    assert hook_results == {
        role: {"registered": 22, "remaining": 0, "unloaded": True}
        for role in ("morfeo", "supervisor", "implementer")
    }

    paths = ObservationPaths.for_project(PROJECT_ID)
    journal_events = [
        json.loads(line)
        for segment in list_segments(paths)
        for line in read_segment(segment.path).lines
    ]
    journal_event_types = {
        event["event_type"] for event in journal_events if event.get("trace_id") == TRACE_ID
    }
    assert {
        "trace.opened",
        "tool.started",
        "tool.completed",
        "model.request_started",
        "model.request_completed",
    } <= journal_event_types
    query = subprocess.run(
        [
            str(release / "manager" / "bin" / "aether"),
            "observe",
            TRACE_ID,
            "--project",
            str(project),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    observed = json.loads(query.stdout)
    assert observed["data"]["state"] == "summary"
    assert observed["data"]["summary"]["trace_id"] == TRACE_ID
    assert observed["data"]["summary"]["source_event_count"] >= len(journal_event_types)
    with ReadModel.open(paths) as read_model:
        projected_event_types = {
            event["event_type"] for event in read_model.events_for_trace(TRACE_ID)
        }
        assert {
            "tool.started",
            "tool.completed",
            "model.request_started",
            "model.request_completed",
        } <= projected_event_types
        assert (
            read_model.latest_summary(TRACE_ID)["summary_id"]
            == observed["data"]["summary"]["summary_id"]
        )
    healthy = first_manager.doctor()
    assert healthy.ready is True
    assert healthy.details["hook_probe"] == {
        "expected_callbacks": 22,
        "registered_callbacks": 22,
        "remaining_callbacks": 0,
    }
    assert healthy.details["observer_state"]["projection_integrity_failures"] == 0
    assert healthy.details["observer_state"]["summary_file_count"] >= 1
    assert healthy.details["observer_state"]["incomplete_summary_count"] >= 1
    persisted = b"".join(
        path.read_bytes()
        for root in (store.root, store.state_root)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    for role in ("morfeo", "supervisor", "implementer"):
        assert f"RAW_COMMAND_{role}_MUST_NOT_PERSIST".encode() not in persisted
        assert f"RAW_PROMPT_{role}_MUST_NOT_PERSIST".encode() not in persisted
        assert f"RAW_RESPONSE_{role}_MUST_NOT_PERSIST".encode() not in persisted

    unknown = paths.closed / "future-v999.bin"
    unknown_bytes = b'{"schema_version":"aether.observation.event.v999","opaque":true}\n'
    unknown.write_bytes(unknown_bytes)
    second = first_manager.update(
        wheel=second_wheel,
        hermes_checkout=checkout,
        release_lock=_write_release_lock(
            tmp_path,
            "1.0.1",
            source_tree_sha256=hermes_source_tree_sha256,
        ),
        expected_active_release_id=first.release_id,
    )
    second_manager = LifecycleManager(
        store=store,
        python_executable=manager._environment_python(
            store.release_path(second.release_id) / "manager"
        ),
    )
    assert unknown.read_bytes() == unknown_bytes
    rolled_back = second_manager.rollback(expected_active_release_id=second.release_id)
    assert rolled_back.release_id == first.release_id
    assert unknown.read_bytes() == unknown_bytes
    restored = first_manager.activate_existing(
        second.release_id,
        transition_kind="update",
        expected_active_release_id=first.release_id,
    )
    assert restored.release_id == second.release_id
    assert unknown.read_bytes() == unknown_bytes

    active_runtime = store.release_path(second.release_id) / "runtime"
    hermes_package = subprocess.run(
        [
            str(manager._environment_python(active_runtime)),
            "-c",
            "import hermes_cli,pathlib;print(pathlib.Path(hermes_cli.__file__).parent)",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    broken = Path(hermes_package.stdout.strip())
    disabled = broken.with_name("hermes_cli.disabled")
    broken.rename(disabled)
    assert second_manager.doctor().ready is False
    recovered = second_manager.rollback(expected_active_release_id=second.release_id)
    assert recovered.release_id == first.release_id

    preserved = first_manager.uninstall(purge=False, confirmed=True)
    assert preserved.purged is False
    assert unknown.read_bytes() == unknown_bytes
    with pytest.raises(IntegrityError, match="no active release"):
        first_manager.uninstall(purge=True, confirmed=True)
    assert store.state_root.exists()


@pytest.mark.integration
def test_disposable_public_install_capture_query_update_rollback_uninstall_purge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise #221 without touching a live profile/service or claiming exact provenance."""

    checkout, fixture_commit = _clean_tagged_checkout(tmp_path)
    first_wheel = _build_wheel(tmp_path / "first-build", "1.0.0")
    second_wheel = _build_wheel(tmp_path / "second-build", "1.0.1")
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))
    monkeypatch.setattr(
        lifecycle,
        "verify_clean_checkout",
        lambda *_args, **_kwargs: CheckoutEvidence(
            path=checkout,
            tag=HERMES_BASELINE.tag,
            tag_object=HERMES_BASELINE.tag_object,
            commit=HERMES_BASELINE.commit,
            clean=True,
        ),
    )
    materialize = lifecycle._materialize_git_archive
    monkeypatch.setattr(
        lifecycle,
        "_materialize_git_archive",
        lambda source, _commit, destination: materialize(source, fixture_commit, destination),
    )
    hermes_source_tree_sha256 = _source_tree_sha256(checkout, fixture_commit)

    setup = [
        "setup",
        "--wheel",
        str(first_wheel),
        "--hermes-checkout",
        str(checkout),
        "--release-lock",
        str(
            _write_release_lock(
                tmp_path,
                "1.0.0",
                source_tree_sha256=hermes_source_tree_sha256,
            )
        ),
        "--yes",
        "--json",
    ]
    assert main(setup) == 0
    installed = json.loads(capsys.readouterr().out)
    assert installed["result"] == "changed"
    assert installed["active_version"] == "1.0.0"

    assert main(["doctor", "--json"]) == 4
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["result"] == "error"
    assert doctor["data"]["observer"]["profile_count"] == 3
    assert "OBSERVER_HOOK_PROBE_FAILED" in doctor["data"]["observer"]["diagnostic_codes"]

    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(f'project_id = "{PROJECT_ID}"\n', encoding="utf-8")
    assert ProjectRegistry().register(PROJECT_ID, project, "lifecycle-e2e")
    paths = ObservationPaths.for_project(PROJECT_ID)
    fixture = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    try:
        for event in fixture.events:
            assert writer.append(event).accepted
    finally:
        writer.close()
    assert main(["observe", TRACE_ID, "--project", str(project), "--json"]) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["result"] == "ready"

    # Stage locally without changing authority, then enter through the public source
    # launcher.  The child process cannot inherit either fixture monkeypatch, so a
    # successful switch proves it was the real installed 1.0.0 manager validating the
    # already immutable 1.0.1 release rather than this 0.24.0/source interpreter.
    source_manager = cli_module._lifecycle_manager()
    with source_manager.store.mutation_lock():
        staged = source_manager.store._register_locked(
            source_manager._prepare_release_locked(
                wheel=second_wheel,
                hermes_checkout=checkout,
                release_lock=_write_release_lock(
                    tmp_path,
                    "1.0.1",
                    source_tree_sha256=hermes_source_tree_sha256,
                ),
            )
        )
    assert source_manager.store.active().release_id == installed["data"]["active_release_id"]

    public_tool = tmp_path / "public-tool"
    subprocess.run(
        ["uv", "--no-config", "venv", "--python", sys.executable, str(public_tool)],
        check=True,
        capture_output=True,
        text=True,
        env=lifecycle._isolated_subprocess_environment(),
    )
    public_python = LifecycleManager._environment_python(public_tool)
    subprocess.run(
        [
            "uv",
            "--no-config",
            "pip",
            "install",
            "--python",
            str(public_python),
            str(first_wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=lifecycle._isolated_subprocess_environment(),
    )
    active_manager_python = LifecycleManager._environment_python(
        source_manager.store.release_path(installed["data"]["active_release_id"]) / "manager"
    )
    assert public_python != active_manager_python
    assert source_manager._installed_aether_identity(public_python) == (
        source_manager._installed_aether_identity(active_manager_python)
    )
    public_environment = lifecycle._isolated_subprocess_environment()
    public_environment.update(
        {
            "XDG_DATA_HOME": str(xdg),
            "XDG_STATE_HOME": str(xdg),
            # The public launcher can inherit ordinary user state, but its dispatch
            # child must scrub every ambient Python override.
            "PYTHONPATH": str(tmp_path / "ambient-pythonpath-must-not-reach-active"),
        }
    )
    public_update = subprocess.run(
        [str(public_tool / "bin" / "aether"), "update", staged.version, "--yes", "--json"],
        check=False,
        capture_output=True,
        text=True,
        env=public_environment,
    )
    assert public_update.returncode == 0, public_update.stderr
    updated = json.loads(public_update.stdout)
    assert updated["active_version"] == "1.0.1"
    assert updated["data"]["executing_manager_release_id"] == installed["data"]["active_release_id"]

    stale_manager = (
        source_manager.store.release_path(installed["data"]["active_release_id"])
        / "manager"
        / "bin"
        / "aether"
    )
    stale_rollback = subprocess.run(
        [str(stale_manager), "rollback", "--yes", "--json"],
        check=False,
        capture_output=True,
        text=True,
        env=public_environment,
    )
    assert stale_rollback.returncode == 4
    stale_payload = json.loads(stale_rollback.stdout)
    assert stale_payload["errors"][0]["code"] == "ACTIVE_MANAGER_AUTHORITY_REQUIRED"
    assert source_manager.store.active().release_id == updated["data"]["active_release_id"]

    assert main(["rollback", "--yes", "--json"]) == 0
    rolled_back = json.loads(capsys.readouterr().out)
    assert rolled_back["active_version"] == "1.0.0"

    retained = paths.closed / "retained-future.bin"
    retained.write_bytes(b"unknown-newer-observation-bytes")
    assert main(["uninstall", "--yes", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["observation_state_preserved"] is True
    assert retained.read_bytes() == b"unknown-newer-observation-bytes"

    assert main(["uninstall", "--purge", "--yes", "--json"]) == 4
    refused_purge = json.loads(capsys.readouterr().out)
    assert refused_purge["result"] == "error"
    assert refused_purge["errors"][0]["code"] == "ACTIVE_MANAGER_AUTHORITY_REQUIRED"
    assert retained.read_bytes() == b"unknown-newer-observation-bytes"


def test_doctor_detects_manager_runtime_wheel_divergence_without_importing_hermes(
    tmp_path: Path,
) -> None:
    store = ReleaseStore(tmp_path / "state" / "aether")
    release = _prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one")
    record = store.activate(release)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    incomplete = manager.doctor()
    assert incomplete.ready is False
    assert incomplete.active_release_id == record.release_id
    assert "INSTALLATION_EVIDENCE_MISSING" in incomplete.codes

    runtime_marker = store.release_path(record.release_id) / "runtime" / "aether-wheel.sha256"
    runtime_marker.write_text("f" * 64 + "\n", encoding="ascii")
    diverged = manager.doctor()
    assert diverged.ready is False
    assert "WHEEL_IDENTITY_MISMATCH" in diverged.codes

    non_python_manager = LifecycleManager(
        store=store,
        python_executable=Path("/bin/false"),
    ).doctor()
    assert non_python_manager.ready is False
    assert "EXECUTING_MANAGER_INVALID" in non_python_manager.codes


def test_cli_doctor_absence_is_integrity_error_not_protected_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    assert main(["doctor", "--json"]) == 4

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"] == "error"
    assert payload["errors"][0]["code"] == "LIFECYCLE_INTEGRITY_FAILED"
    assert "ACTIVE_RELEASE_INVALID" in payload["data"]["observer"]["diagnostic_codes"]


def test_uninstall_preserves_observation_state_and_purge_requires_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "xdg" / "aether"
    store = ReleaseStore(state)
    store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    retained = state / "observations" / "projects" / "p" / "journal" / "closed" / "x"
    retained.parent.mkdir(parents=True)
    retained.write_bytes(b"future bytes")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)

    result = manager.uninstall(purge=False, confirmed=False)
    assert result.purged is False
    assert retained.read_bytes() == b"future bytes"
    assert not (state / "active.json").exists()

    with pytest.raises(IntegrityError, match="confirmation"):
        manager.uninstall(purge=True, confirmed=False)
    assert retained.exists()

    with pytest.raises(IntegrityError, match="no active release"):
        manager.uninstall(purge=True, confirmed=True)
    assert retained.exists()

    purge_state = tmp_path / "purge" / "aether"
    purge_store = ReleaseStore(purge_state)
    purge_store.activate(_prepared_release(tmp_path / "purge-r1", "1.0.0", b"wheel-one"))
    purge_manager = LifecycleManager(
        store=purge_store,
        python_executable=Path(sys.executable),
    )
    _allow_unit_manager_authority(purge_manager, monkeypatch)
    purged = purge_manager.uninstall(purge=True, confirmed=True)
    assert purged.purged is True
    assert not purge_state.exists()
    assert tmp_path.exists()


@pytest.mark.parametrize("damage_mode", ["missing", "corrupt"])
def test_preserving_uninstall_deactivates_projection_without_opening_derived_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    damage_mode: str,
) -> None:
    state = tmp_path / "state" / "aether"
    store = ReleaseStore(state)
    active = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    paths = ObservationPaths.for_project(PROJECT_ID, root=state).ensure()
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    _allow_unit_manager_authority(manager, monkeypatch)
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    manager.recover()
    projection = paths.projection_db(READ_MODEL_SCHEMA)
    assert paths.projection_pointer.is_file()
    assert projection.is_file()
    corrupt_bytes = b"opaque-corrupt-projection-bytes"
    if damage_mode == "missing":
        projection.unlink()
    else:
        projection.write_bytes(corrupt_bytes)

    result = manager.uninstall(purge=False, confirmed=True)

    assert result.preserved_observations is True
    assert not paths.projection_pointer.exists()
    if damage_mode == "missing":
        assert not projection.exists()
    else:
        assert projection.read_bytes() == corrupt_bytes
    assert not store.active_pointer.exists()
    assert active.release_id not in {record.release_id for record in store.records()}


def test_uninstall_preserve_deactivates_profiles_without_deleting_user_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReleaseStore(tmp_path / "xdg" / "aether")
    prepared = _prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one")
    record = store.register(prepared)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    manager.activate_existing(
        record.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )
    user_state = store.profile_home("morfeo") / "sessions.sqlite3"
    user_state.write_bytes(b"user-owned-state")

    _allow_unit_manager_authority(manager, monkeypatch)
    result = manager.uninstall(purge=False, confirmed=True)

    assert result.purged is False
    for role in ("morfeo", "supervisor", "implementer"):
        home = store.profile_home(role)
        assert not (home / "aether-observer.json").exists()
        assert not (home / "config.yaml").exists()
    assert user_state.read_bytes() == b"user-owned-state"


def test_state_root_must_not_be_a_symlink_for_destructive_lifecycle(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "aether"
    if os.name != "posix":
        pytest.skip("symlink confinement is POSIX-qualified")
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IntegrityError, match="symlink"):
        ReleaseStore(root)


def test_cli_doctor_rollback_and_uninstall_use_the_stable_json_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))
    store = ReleaseStore(xdg / "aether")
    first = store.activate(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    store.activate(_prepared_release(tmp_path / "r2", "1.0.1", b"wheel-two"))

    assert main(["doctor", "--json"]) == 4
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["result"] == "error"
    assert doctor["data"]["observer"]["status"] == "unavailable"
    assert "INSTALLATION_EVIDENCE_MISSING" in doctor["data"]["observer"]["diagnostic_codes"]

    # Skeletal release bytes cannot authenticate a dispatch target.  Both stateful
    # commands therefore fail closed with the same integrity taxonomy; the real
    # installed-manager success envelope is covered by the disposable integration.
    assert main(["rollback", "--yes", "--json"]) == 4
    rollback = json.loads(capsys.readouterr().out)
    assert rollback["result"] == "error"
    assert rollback["errors"][0]["code"] == "ACTIVE_MANAGER_AUTHORITY_REQUIRED"
    assert store.active().release_id != first.release_id

    retained = xdg / "aether" / "observations" / "future.bin"
    retained.parent.mkdir(parents=True, exist_ok=True)
    retained.write_bytes(b"unknown newer bytes")
    assert main(["uninstall", "--yes", "--json"]) == 4
    uninstall = json.loads(capsys.readouterr().out)
    assert uninstall["result"] == "error"
    assert uninstall["errors"][0]["code"] == "ACTIVE_MANAGER_AUTHORITY_REQUIRED"
    assert retained.read_bytes() == b"unknown newer bytes"
