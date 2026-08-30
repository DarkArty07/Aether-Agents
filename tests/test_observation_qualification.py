"""Release qualification regressions for the exact Hermes baseline (#220)."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from observation_helpers import PROJECT_ID, TRACE_ID, project_marker

from aether_agents.lifecycle import HERMES_BASELINE, IntegrityError, verify_clean_checkout
from aether_agents.observation.capture.journal import list_segments, read_segment
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import validate_event
from aether_agents.observation.identity import correlation_token
from aether_agents.observation.privacy import assert_clean
from aether_agents.paths import ObservationPaths

ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "qualify_observation.py"
WORKFLOW = ROOT / ".github" / "workflows" / "policy.yml"
RESULTS_BLOCK_BEGIN = "<!-- BEGIN AETHER_OBSERVATION_QUALIFICATION_RESULTS_V1 -->"
RESULTS_BLOCK_END = "<!-- END AETHER_OBSERVATION_QUALIFICATION_RESULTS_V1 -->"


def _events(paths: ObservationPaths) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for segment in list_segments(paths):
        events.extend(json.loads(line) for line in read_segment(segment.path).lines)
    return events


def _load_runner(name: str):
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _skip_unless_runtime_is_exact_baseline(checkout: Path) -> None:
    """These lanes import the *installed* plugin, so the runtime itself must be the baseline.

    Unlike the lifecycle lane, they cannot be redirected at another checkout:
    `hermes_cli.plugins` is imported from whatever is installed. Under the
    declared transitional_fork mode the runtime carries the local patch set and
    a newer commit, so it can never be the locked baseline (#234). Skipping
    states that honestly instead of failing on an environment fact that says
    nothing about Aether.
    """

    try:
        verify_clean_checkout(
            checkout,
            expected_tag=HERMES_BASELINE.tag,
            expected_commit=HERMES_BASELINE.commit,
            expected_tag_object=HERMES_BASELINE.tag_object,
        )
    except (IntegrityError, OSError, subprocess.SubprocessError) as error:
        pytest.skip(
            "installed Hermes runtime is not the locked baseline "
            f"({HERMES_BASELINE.tag} @ {HERMES_BASELINE.commit[:12]}): {error}"
        )


@pytest.mark.hermes_exact
def test_real_plugin_context_captures_tool_and_api_then_unloads_every_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    from aether_agents.observation.capture import hermes_plugin

    checkout = Path(plugins.__file__).resolve().parents[1]
    tracked_source = os.environ.get("AETHER_QUALIFICATION_TRACKED_SOURCE")
    if tracked_source is None:
        _skip_unless_runtime_is_exact_baseline(checkout)
        evidence = verify_clean_checkout(
            checkout,
            expected_tag=HERMES_BASELINE.tag,
            expected_commit=HERMES_BASELINE.commit,
            expected_tag_object=HERMES_BASELINE.tag_object,
        )
        assert evidence.clean and evidence.commit == HERMES_BASELINE.commit
    else:
        assert checkout == Path(tracked_source).resolve(strict=True)
        assert os.environ["AETHER_QUALIFICATION_SOURCE_COMMIT"] == HERMES_BASELINE.commit
    dispatch = hermes_plugin._Observer.dispatch

    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(project_marker(PROJECT_ID), encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes" / "profiles" / "morfeo"))
    assert ProjectRegistry().register(PROJECT_ID, project, "qualification")
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)

    manager = plugins.PluginManager(scope_key=str(tmp_path / "hermes"))
    manifest = plugins.PluginManifest(
        name="aether-contract-observer",
        key="aether-contract-observer",
        source="entrypoint",
    )
    context = plugins.PluginContext(manifest, manager)
    hermes_plugin.register(context)
    assert set(manager._hooks) == set(hermes_plugin.OBSERVED_HOOKS)
    assert all(len(callbacks) == 1 for callbacks in manager._hooks.values())
    assert sum(len(callbacks) for callbacks in manager._hooks.values()) == 22

    token = correlation_token(TRACE_ID, "t_aaaaaaaa")
    assert (
        manager.invoke_hook(
            "pre_tool_call",
            tool_name="kanban_create",
            tool_call_id="create-1",
            session_id="session-1",
            turn_id="turn-1",
            api_request_id="api-0",
            args={"idempotency_key": token, "body": "RAW_PROMPT_MUST_NOT_PERSIST"},
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "post_tool_call",
            tool_name="kanban_create",
            tool_call_id="create-1",
            session_id="session-1",
            turn_id="turn-1",
            api_request_id="api-0",
            status="success",
            args={"idempotency_key": token},
            result={"ok": True, "task_id": "t_aaaaaaaa", "project_id": PROJECT_ID},
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "pre_tool_call",
            tool_name="terminal",
            tool_call_id="malicious-tool-1",
            session_id="session-1",
            turn_id="turn-1",
            api_request_id="api-tool-1",
            task_id="t_aaaaaaaa",
            args={
                "command": "RAW_TOOL_COMMAND_MUST_NOT_PERSIST",
                "prompt": "RAW_TOOL_PROMPT_MUST_NOT_PERSIST",
            },
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "post_tool_call",
            tool_name="terminal",
            tool_call_id="malicious-tool-1",
            session_id="session-1",
            turn_id="turn-1",
            api_request_id="api-tool-1",
            task_id="t_aaaaaaaa",
            status="success",
            args={"command": "RAW_TOOL_COMMAND_MUST_NOT_PERSIST"},
            result={"stdout": "RAW_TOOL_RESULT_MUST_NOT_PERSIST"},
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "pre_api_request",
            api_request_id="api-1",
            session_id="session-1",
            turn_id="turn-1",
            task_id="t_aaaaaaaa",
            model="model-1",
            provider="provider-1",
            prompt="RAW_PROMPT_MUST_NOT_PERSIST",
            system_prompt="RAW_SYSTEM_PROMPT_MUST_NOT_PERSIST",
            message_count=1,
            tool_count=1,
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "post_api_request",
            api_request_id="api-1",
            session_id="session-1",
            turn_id="turn-1",
            task_id="t_aaaaaaaa",
            model="model-1",
            provider="provider-1",
            status="completed",
            response="RAW_RESPONSE_MUST_NOT_PERSIST",
            usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "subagent_start",
            child_session_id="child-session-1",
            child_role="implementation",
            parent_session_id="session-1",
            parent_turn_id="turn-1",
            task_id="t_aaaaaaaa",
            prompt="RAW_SUBAGENT_PROMPT_MUST_NOT_PERSIST",
            instructions="RAW_SUBAGENT_INSTRUCTIONS_MUST_NOT_PERSIST",
        )
        == []
    )
    assert (
        manager.invoke_hook(
            "subagent_stop",
            child_session_id="child-session-1",
            child_role="implementation",
            parent_session_id="session-1",
            parent_turn_id="turn-1",
            task_id="t_aaaaaaaa",
            status="completed",
            output="RAW_SUBAGENT_OUTPUT_MUST_NOT_PERSIST",
            error="RAW_SUBAGENT_ERROR_MUST_NOT_PERSIST",
        )
        == []
    )

    assert manager.unload(manifest) is True
    assert hermes_plugin._Observer.dispatch is dispatch
    assert sum(len(callbacks) for callbacks in manager._hooks.values()) == 0
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state" / "aether")
    recorded = _events(paths)
    event_types = {event["event_type"] for event in recorded}
    assert {
        "tool.started",
        "tool.completed",
        "model.request_started",
        "model.request_completed",
        "participant.joined",
        "participant.left",
    } <= event_types
    for event in recorded:
        validate_event(event)
        assert_clean(event)
    persisted = json.dumps(recorded, sort_keys=True).encode()
    for raw in (
        b"RAW_PROMPT_MUST_NOT_PERSIST",
        b"RAW_RESPONSE_MUST_NOT_PERSIST",
        b"RAW_SYSTEM_PROMPT_MUST_NOT_PERSIST",
        b"RAW_TOOL_COMMAND_MUST_NOT_PERSIST",
        b"RAW_TOOL_PROMPT_MUST_NOT_PERSIST",
        b"RAW_TOOL_RESULT_MUST_NOT_PERSIST",
        b"RAW_SUBAGENT_PROMPT_MUST_NOT_PERSIST",
        b"RAW_SUBAGENT_INSTRUCTIONS_MUST_NOT_PERSIST",
        b"RAW_SUBAGENT_OUTPUT_MUST_NOT_PERSIST",
        b"RAW_SUBAGENT_ERROR_MUST_NOT_PERSIST",
    ):
        assert raw not in persisted
    print(
        "AETHER_HARNESS_RESULT="
        + json.dumps(
            {
                "plugin_callback_count": 22,
                "unload_hook_count": 0,
                "tool_events_captured": {
                    "tool.started",
                    "tool.completed",
                }
                <= event_types,
                "api_events_captured": {
                    "model.request_started",
                    "model.request_completed",
                }
                <= event_types,
                "raw_payload_absent": True,
            },
            sort_keys=True,
        )
    )


def test_qualification_runner_and_ci_execute_instead_of_trusting_a_fixture() -> None:
    assert RUNNER.is_file()
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "contract", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    contract = json.loads(completed.stdout)
    assert contract["hermes"] == {
        "repository": "https://github.com/NousResearch/hermes-agent.git",
        "tag": "v2026.8.18",
        "tag_object": "9f13bbbf8423427e159c78066356ca0e27ca6b74",
        "commit": "e624e9fde561e1add9388384012b295fde669ade",
        "distribution": "hermes-agent",
        "version": "0.20.4",
    }
    assert contract["minimum_observation_tests"] == 119
    assert contract["expected_core_tests"] == 450
    assert contract["expected_core_node_manifest_sha256"] == (
        "e0cb8eadd90d74d28d36e8060531d61b181bc9abf093c976ea2d07355c048fb8"
    )
    assert contract["core_test_files"] == [
        "tests/test_observation_contracts.py",
        "tests/test_observation_journal_storage.py",
        "tests/test_observation_reducer.py",
        "tests/test_observation_cli_plugin.py",
        "tests/test_observation_packaging.py",
        "tests/test_observation_path_confinement.py",
        "tests/test_projection_transition_runner.py",
    ]
    assert not any(
        name.endswith(("test_observation_lifecycle.py", "test_observation_qualification.py"))
        for name in contract["core_test_files"]
    )
    assert contract["plugin_callback_count"] == 22
    assert contract["validation_results"] == {
        "schema_version": 1,
        "block_begin": RESULTS_BLOCK_BEGIN,
        "block_end": RESULTS_BLOCK_END,
    }

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "qualify_observation.py checkout" in workflow
    assert "python-version: ['3.11', '3.12', '3.13']" in workflow
    assert "ruff check" in workflow
    assert "ruff format --check" in workflow
    assert "uv build" in workflow
    assert '--output "${RUNNER_TEMP}/observation-benchmark-python-3.11.json"' in workflow
    assert "uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7" in workflow
    assert "name: observation-benchmark-python-3.11" in workflow
    assert "path: ${{ runner.temp }}/observation-benchmark-python-3.11.json" in workflow
    assert "qualify_observation.py contrast-validation" in workflow
    assert (
        "--report specs/002-aether-contract-observation/evidence/implementation-validation.md"
        in workflow
    )
    assert '--result "tests=${RUNNER_TEMP}/observation-tests-python-3.11.json"' in workflow
    assert '--result "benchmark=${RUNNER_TEMP}/observation-benchmark-python-3.11.json"' in workflow
    assert (
        '--output "${RUNNER_TEMP}/observation-tests-python-${{ matrix.python-version }}.json"'
        in workflow
    )
    assert "name: observation-tests-python-${{ matrix.python-version }}" in workflow
    assert (
        "path: ${{ runner.temp }}/observation-tests-python-${{ matrix.python-version }}.json"
        in workflow
    )
    exact_pythonpath = 'PYTHONPATH="${RUNNER_TEMP}/hermes-v2026.8.18"'
    assert exact_pythonpath in workflow
    assert f'{exact_pythonpath[:-1]}:${{PWD}}/src:${{PWD}}/tests"' not in workflow
    assert workflow.count("qualify_observation.py benchmark") == 1
    assert 'AETHER_RUN_DEEP_QUALIFICATION: "0"' in workflow


def test_locked_core_manifest_matches_the_actual_collected_nodes() -> None:
    module = _load_runner("qualify_observation_locked_manifest")
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *module.CORE_TESTS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    count, digest = module._collection_manifest(completed.stdout)
    assert count == module.EXPECTED_CORE_TESTS
    assert digest == module.EXPECTED_CORE_NODE_MANIFEST_SHA256


def test_policy_workflow_pins_every_action_and_confines_spec_files() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    expected_actions = {
        "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1 # v7",
        "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1 # v6",
        "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7",
        "astral-sh/setup-uv": "94527f2e458b27549849d47d273a16bec83a01e9 # v7",
    }
    for action, revision in expected_actions.items():
        assert f"uses: {action}@{revision}" in workflow
        assert f"uses: {action}@v" not in workflow
    assert "version: 0.12.3" in workflow
    assert "git ls-files -s specs" in workflow
    assert "mode != '100644'" in workflow
    assert "suffix not in {'.json', '.md'}" in workflow


def test_ci_whitespace_gate_checks_committed_review_range() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "fetch-depth: 0" in workflow
    assert 'git diff --check "${{ github.event.pull_request.base.sha }}...HEAD"' in workflow
    assert 'git diff-tree --check --root --no-commit-id -r "$GITHUB_SHA"' in workflow
    assert "\n          git diff --check\n" not in workflow


def test_test_qualification_result_can_be_retained_atomically_for_report_contrast(
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location("qualify_observation_output", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "python-3.11.json"

    args = module._parser().parse_args(
        [
            "test",
            "--checkout",
            "/tmp/hermes-exact",
            "--output",
            str(output),
        ]
    )

    assert args.output == output


@pytest.mark.parametrize(
    "harness_output",
    (
        "1 skipped in 0.01s\n",
        "no tests ran in 0.01s\n",
        "1 passed, 1 skipped in 0.01s\n",
        "2 passed in 0.01s\n",
    ),
)
def test_run_tests_rejects_an_omitted_skipped_or_non_single_harness_before_claiming_hooks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    harness_output: str,
) -> None:
    module = _load_runner("qualify_observation_harness_gate")
    evidence = SimpleNamespace(
        path=tmp_path,
        tag=HERMES_BASELINE.tag,
        tag_object=HERMES_BASELINE.tag_object,
        commit=HERMES_BASELINE.commit,
        clean=True,
    )
    monkeypatch.setattr(module, "verify_clean_checkout", lambda *_args, **_kwargs: evidence)
    monkeypatch.setattr(
        module,
        "_materialize_qualification_source",
        lambda _checkout, destination: {
            "path": str(destination),
            "sha256": "a" * 64,
            "commit": HERMES_BASELINE.commit,
        },
    )
    monkeypatch.setattr(module, "_qualification_environment", lambda _checkout: {})
    nodes = "\n".join(
        f"tests/test_observation_contracts.py::test_{index}"
        for index in range(module.EXPECTED_CORE_TESTS)
    )
    manifest_digest = hashlib.sha256(
        ("\n".join(sorted(nodes.splitlines())) + "\n").encode()
    ).hexdigest()
    monkeypatch.setattr(module, "EXPECTED_CORE_NODE_MANIFEST_SHA256", manifest_digest)
    results = iter(
        (
            subprocess.CompletedProcess(
                ["pytest"],
                0,
                f"{nodes}\n{module.EXPECTED_CORE_TESTS} tests collected in 0.10s\n",
                "",
            ),
            subprocess.CompletedProcess(
                ["pytest"], 0, f"{module.EXPECTED_CORE_TESTS} passed in 1.00s\n", ""
            ),
            subprocess.CompletedProcess(["pytest"], 0, harness_output, ""),
        )
    )
    monkeypatch.setattr(module, "_run", lambda *_args, **_kwargs: next(results))

    with pytest.raises(RuntimeError, match="qualification harness"):
        module.run_tests(tmp_path, Path(sys.executable))


def test_run_tests_reports_measured_harness_values_and_exact_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_runner("qualify_observation_measured_harness")
    monkeypatch.setattr(
        module,
        "verify_clean_checkout",
        lambda *_args, **_kwargs: SimpleNamespace(
            path=tmp_path,
            tag=HERMES_BASELINE.tag,
            tag_object=HERMES_BASELINE.tag_object,
            commit=HERMES_BASELINE.commit,
            clean=True,
        ),
    )
    monkeypatch.setattr(
        module,
        "_materialize_qualification_source",
        lambda _checkout, destination: {
            "path": str(destination),
            "sha256": "c" * 64,
            "commit": HERMES_BASELINE.commit,
        },
    )
    monkeypatch.setattr(module, "_qualification_environment", lambda _source: {})
    nodes = "\n".join(
        f"tests/test_observation_contracts.py::test_{index}"
        for index in range(module.EXPECTED_CORE_TESTS)
    )
    manifest_digest = hashlib.sha256(
        ("\n".join(sorted(nodes.splitlines())) + "\n").encode()
    ).hexdigest()
    monkeypatch.setattr(module, "EXPECTED_CORE_NODE_MANIFEST_SHA256", manifest_digest)
    harness = {
        "plugin_callback_count": 22,
        "unload_hook_count": 0,
        "tool_events_captured": True,
        "api_events_captured": True,
        "raw_payload_absent": True,
    }
    results = iter(
        (
            subprocess.CompletedProcess(
                ["pytest"],
                0,
                f"{nodes}\n{module.EXPECTED_CORE_TESTS} tests collected in 0.10s\n",
                "",
            ),
            subprocess.CompletedProcess(
                ["pytest"], 0, f"{module.EXPECTED_CORE_TESTS} passed in 1.00s\n", ""
            ),
            subprocess.CompletedProcess(
                ["pytest"],
                0,
                "AETHER_HARNESS_RESULT=" + json.dumps(harness) + "\n1 passed in 0.10s\n",
                "",
            ),
        )
    )
    monkeypatch.setattr(module, "_run", lambda *_args, **_kwargs: next(results))

    result = module.run_tests(tmp_path, Path(sys.executable))

    assert result["passed"] == module.EXPECTED_CORE_TESTS
    assert result["collected"] == module.EXPECTED_CORE_TESTS
    assert len(result["node_manifest_sha256"]) == 64
    assert result["plugin_callback_count"] == 22
    assert result["unload_hook_count"] == 0
    assert result["tool_events_captured"] is True
    assert result["api_events_captured"] is True
    assert result["raw_payload_absent"] is True
    assert result["qualified_source"]["sha256"] == "c" * 64


def test_run_tests_rejects_same_count_node_manifest_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_runner("qualify_observation_node_manifest_drift")
    evidence = SimpleNamespace(
        path=tmp_path,
        tag=HERMES_BASELINE.tag,
        tag_object=HERMES_BASELINE.tag_object,
        commit=HERMES_BASELINE.commit,
        clean=True,
    )
    monkeypatch.setattr(module, "verify_clean_checkout", lambda *_args, **_kwargs: evidence)
    monkeypatch.setattr(
        module,
        "_materialize_qualification_source",
        lambda _checkout, destination: {"path": str(destination), "sha256": "c" * 64},
    )
    monkeypatch.setattr(module, "_qualification_environment", lambda _source: {})
    nodes = "\n".join(
        f"tests/test_observation_contracts.py::renamed_{index}"
        for index in range(module.EXPECTED_CORE_TESTS)
    )
    monkeypatch.setattr(
        module,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["pytest"],
            0,
            f"{nodes}\n{module.EXPECTED_CORE_TESTS} tests collected in 0.10s\n",
            "",
        ),
    )

    with pytest.raises(RuntimeError, match="node manifest"):
        module.run_tests(tmp_path, Path(sys.executable))


def test_checkout_exact_rejects_a_symlink_before_any_git_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_runner("qualify_observation_checkout_symlink")
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    calls: list[object] = []
    monkeypatch.setattr(module, "_run", lambda *args, **kwargs: calls.append((args, kwargs)))

    with pytest.raises(RuntimeError, match="symlink"):
        module.checkout_exact(alias)

    assert calls == []


def test_prioritize_exact_source_evicts_preloaded_hermes_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_runner("qualify_observation_source_priority")
    source = tmp_path / "tracked-source"
    source.mkdir()
    hostile = object()
    monkeypatch.setitem(sys.modules, "hermes_cli.hostile", hostile)
    monkeypatch.setattr(sys, "path", ["/ignored/editable", *sys.path])

    module._prioritize_hermes_source(source)

    assert sys.path[0] == str(source.resolve())
    assert "hermes_cli.hostile" not in sys.modules


def _exact_source_checkout(runtime_checkout: Path) -> Path:
    """Resolve a checkout for lanes that only *read* the Hermes tree.

    These can be redirected at any clean baseline checkout, unlike the lanes
    that import the installed plugin. Prefer the explicitly configured one so
    the lane still produces evidence on a transitional_fork runtime (#234).
    """

    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
    if configured:
        return Path(configured).resolve(strict=True)
    _skip_unless_runtime_is_exact_baseline(runtime_checkout)
    return runtime_checkout


@pytest.mark.hermes_exact
def test_qualification_source_excludes_ignored_egg_info_and_bytecode(
    tmp_path: Path,
) -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    checkout = _exact_source_checkout(Path(plugins.__file__).resolve().parents[1])
    module = _load_runner("qualify_observation_tracked_source")
    destination = tmp_path / "tracked-source"

    evidence = module._materialize_qualification_source(checkout, destination)

    tracked = set(
        subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "ls-tree",
                "-r",
                "--name-only",
                HERMES_BASELINE.commit,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    observed = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    assert observed == tracked
    assert not any(".egg-info/" in name or "__pycache__/" in name for name in observed)
    assert evidence["source_kind"] == "git_archive_tracked_commit"


def test_run_failure_reports_bounded_content_free_stdout_and_stderr_tails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_runner("qualify_observation_diagnostic_tail")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["pytest"],
            1,
            "FAILED tests/test_safe.py::test_gate - RAW_STDOUT_SECRET\n1 failed in 0.01s\n",
            "RAW_STDERR_SECRET /private/path\n",
        ),
    )

    with pytest.raises(RuntimeError) as captured:
        module._run(["pytest"])

    message = str(captured.value)
    assert "stdout_tail=" in message
    assert "stderr_tail=" in message
    assert "sha256=" in message
    assert "RAW_STDOUT_SECRET" not in message
    assert "RAW_STDERR_SECRET" not in message
    assert "/private/path" not in message


@pytest.mark.hermes_exact
def test_qualification_subprocess_environment_excludes_source_and_ambient_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    checkout = Path(plugins.__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("qualify_observation_environment", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("PYTHONPATH", "/private/editable/hermes:/private/aether/src")

    environment = module._qualification_environment(checkout)

    assert environment["PYTHONPATH"] == str(checkout)
    assert str(ROOT / "src") not in environment["PYTHONPATH"]
    assert str(ROOT / "tests") not in environment["PYTHONPATH"]
    assert "/private" not in environment["PYTHONPATH"]


def test_benchmark_runner_executes_real_events_and_emits_machine_metadata() -> None:
    spec = importlib.util.spec_from_file_location("qualify_observation", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.measure_reduction(1_000)
    assert result["event_count"] == 1_000
    assert result["source_event_count"] == 1_000
    assert result["seconds"] > 0
    assert result["machine"]["python"]
    assert result["machine"]["platform"]


@pytest.mark.parametrize(
    ("ten_thousand_seconds", "p95_ms", "p99_ms", "reason"),
    (
        (2.000001, 1.0, 2.0, "10,000-event full reduction"),
        (0.1, 5.000001, 6.0, "callback p95"),
        (0.1, 1.0, 20.000001, "callback p99"),
    ),
)
def test_benchmark_rejects_every_normative_performance_budget_breach(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ten_thousand_seconds: float,
    p95_ms: float,
    p99_ms: float,
    reason: str,
) -> None:
    module = _load_runner("qualify_observation_performance_gate")
    evidence = SimpleNamespace(path=tmp_path)
    monkeypatch.setattr(module, "verify_clean_checkout", lambda *_args, **_kwargs: evidence)
    monkeypatch.setattr(
        module,
        "_materialize_qualification_source",
        lambda _checkout, destination: (
            destination.mkdir(),
            {"path": str(destination), "sha256": "a" * 64},
        )[1],
    )

    def reduction(count: int) -> dict[str, object]:
        return {
            "event_count": count,
            "source_event_count": count,
            "seconds": ten_thousand_seconds if count == 10_000 else 999.0,
            "events_per_second": 1.0,
            "machine": {},
        }

    monkeypatch.setattr(module, "measure_reduction", reduction)
    monkeypatch.setattr(
        module,
        "measure_callbacks",
        lambda: {
            "p95_ms": p95_ms,
            "p99_ms": p99_ms,
            "plugin_callback_count": 22,
            "unload_hook_count": 0,
        },
    )
    monkeypatch.setattr(module, "measure_out_of_band_flush", lambda: {"sample_count": 1})
    monkeypatch.setattr(module, "measure_incremental_pipeline", lambda: {"measured": True})

    with pytest.raises(RuntimeError, match=reason):
        module.measure_all(tmp_path)


def test_out_of_band_flush_measurement_uses_the_real_supervised_writer(tmp_path: Path) -> None:
    module = _load_runner("qualify_observation_flush")

    result = module.measure_out_of_band_flush(4, root=tmp_path)

    assert result["sample_count"] == 4
    assert result["successful_flushes"] == 4
    assert result["execution_path"] == "supervised_out_of_band"
    assert result["synchronous_callback_fsync"] is False
    assert result["p95_ms"] > 0
    assert result["p99_ms"] >= result["p95_ms"]


def test_incremental_pipeline_is_honest_about_sqlite_ingest_and_full_summary_reduction(
    tmp_path: Path,
) -> None:
    module = _load_runner("qualify_observation_incremental")

    result = module.measure_incremental_pipeline((20, 40), root=tmp_path)

    assert result["mode"] == "incremental_journal_sqlite_projection"
    assert result["summary_reduction_mode"] == "full_reduction"
    assert result["scope"] == "bounded_real_pipeline_probe"
    assert result["normative_counts_complete"] is False
    assert result["twenty"]["event_count"] == 20
    assert result["twenty"]["new_events"] == 20
    assert result["twenty"]["events_inserted"] == 20
    assert result["forty"]["event_count"] == 40
    assert result["forty"]["new_events"] == 20
    assert result["forty"]["events_inserted"] == 20
    assert result["forty"]["source_event_count"] == 40


def test_incremental_pipeline_default_is_the_exact_normative_10k_100k_pair() -> None:
    module = _load_runner("qualify_observation_incremental_default")

    default = (
        inspect.signature(module.measure_incremental_pipeline).parameters["event_counts"].default
    )

    assert default == (10_000, 100_000)


def test_measure_all_rejects_missing_100k_incremental_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_runner("qualify_observation_incremental_gate")
    monkeypatch.setattr(
        module,
        "verify_clean_checkout",
        lambda *_args, **_kwargs: SimpleNamespace(path=tmp_path),
    )
    monkeypatch.setattr(
        module,
        "_materialize_qualification_source",
        lambda _checkout, destination: (
            destination.mkdir(),
            {"path": str(destination), "sha256": "a" * 64},
        )[1],
    )
    monkeypatch.setattr(
        module,
        "measure_reduction",
        lambda count: {
            "mode": "full_reduction",
            "event_count": count,
            "source_event_count": count,
            "seconds": 0.1 if count == 10_000 else 999.0,
        },
    )
    monkeypatch.setattr(
        module,
        "measure_callbacks",
        lambda: {"p95_ms": 1.0, "p99_ms": 2.0},
    )
    monkeypatch.setattr(module, "measure_out_of_band_flush", lambda: {"sample_count": 1})
    monkeypatch.setattr(
        module,
        "measure_incremental_pipeline",
        lambda: {
            "mode": "incremental_journal_sqlite_projection",
            "summary_reduction_mode": "full_reduction",
            "event_counts": [10_000],
            "normative_counts_complete": False,
            "ten_thousand": {"event_count": 10_000, "source_event_count": 10_000},
        },
    )

    with pytest.raises(RuntimeError, match="10,000 and 100,000"):
        module.measure_all(tmp_path)


@pytest.mark.hermes_exact
@pytest.mark.skipif(
    os.environ.get("AETHER_RUN_DEEP_QUALIFICATION") != "1",
    reason="100k qualification runs once through the direct Python 3.11 CI gate",
)
def test_benchmark_cli_executes_100k_and_writes_named_json_artifact(
    tmp_path: Path,
) -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    checkout = Path(plugins.__file__).resolve().parents[1]
    artifact = tmp_path / "observation-benchmark-python-3.11.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "benchmark",
            "--checkout",
            str(checkout),
            "--output",
            str(artifact),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    emitted = json.loads(completed.stdout)
    retained = json.loads(artifact.read_text(encoding="utf-8"))
    assert retained == emitted
    hundred_thousand = retained["reduction"]["one_hundred_thousand"]
    assert hundred_thousand["event_count"] == 100_000
    assert hundred_thousand["source_event_count"] == 100_000
    assert hundred_thousand["seconds"] > 0
    assert hundred_thousand["machine"]["python"]


def test_versioned_validation_contrast_uses_real_outputs_and_never_rewrites_report(
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location("qualify_observation_contrast", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    test_output = tmp_path / "tests.json"
    benchmark_output = tmp_path / "benchmark.json"
    test_payload = {
        "schema_version": 1,
        "passed": 251,
        "minimum": 119,
        "plugin_callback_count": 22,
        "unload_hook_count": 0,
        "core_output": "251 passed in a variable duration",
        "hermes_checkout": {"path": "/tmp/runtime-specific", "clean": True},
    }
    benchmark_payload = {
        "schema_version": 1,
        "reduction": {
            "one_hundred_thousand": {
                "event_count": 100_000,
                "source_event_count": 100_000,
                "seconds": 1.234,
                "events_per_second": 81_037.0,
            }
        },
        "callback": {
            "plugin_callback_count": 22,
            "unload_hook_count": 0,
            "p95_ms": 0.123,
            "p99_ms": 0.234,
            "raw_prompt_absent": True,
            "raw_response_absent": True,
        },
    }
    test_output.write_text(json.dumps(test_payload), encoding="utf-8")
    benchmark_output.write_text(json.dumps(benchmark_payload), encoding="utf-8")
    embedded = {
        "schema_version": 1,
        "claims": {
            "tests": {
                "minimum": 119,
                "plugin_callback_count": 22,
                "unload_hook_count": 0,
                "hermes_checkout": {"clean": True},
            },
            "benchmark": {
                "reduction": {
                    "one_hundred_thousand": {
                        "event_count": 100_000,
                        "source_event_count": 100_000,
                    }
                },
                "callback": {
                    "plugin_callback_count": 22,
                    "unload_hook_count": 0,
                    "raw_prompt_absent": True,
                    "raw_response_absent": True,
                },
            },
        },
    }
    report = tmp_path / "implementation-validation.md"
    report.write_text(
        "\n".join(
            (
                "# Validation evidence",
                RESULTS_BLOCK_BEGIN,
                "```json",
                json.dumps(embedded, sort_keys=True, separators=(",", ":")),
                "```",
                RESULTS_BLOCK_END,
                "Narrative remains owner-authored.",
                "",
            )
        ),
        encoding="utf-8",
    )
    original = report.read_bytes()
    inputs = {"tests": test_output, "benchmark": benchmark_output}

    result = module.contrast_validation_report(report, inputs)
    assert result["schema_version"] == 1
    assert result["matched"] is True
    assert result["result_labels"] == ["benchmark", "tests"]
    assert report.read_bytes() == original

    # Machine, path, output and timing fields are evidence, but deliberately not
    # stable claims: changing them must not make the owner-authored block stale.
    test_output.write_text(
        json.dumps(
            {
                **test_payload,
                "passed": 260,
                "core_output": "260 passed in a different duration",
                "hermes_checkout": {"path": "/tmp/another-run", "clean": True},
            }
        ),
        encoding="utf-8",
    )
    benchmark_output.write_text(
        json.dumps(
            {
                **benchmark_payload,
                "reduction": {
                    "one_hundred_thousand": {
                        **benchmark_payload["reduction"]["one_hundred_thousand"],
                        "seconds": 9.876,
                        "events_per_second": 10_125.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    assert module.contrast_validation_report(report, inputs)["matched"] is True

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "contrast-validation",
            "--report",
            str(report),
            "--result",
            f"tests={test_output}",
            "--result",
            f"benchmark={benchmark_output}",
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["matched"] is True
    assert report.read_bytes() == original

    changed = json.loads(benchmark_output.read_text(encoding="utf-8"))
    changed["reduction"]["one_hundred_thousand"]["event_count"] = 99_999
    benchmark_output.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(RuntimeError, match="claimed qualification value differs"):
        module.contrast_validation_report(report, inputs)
    assert report.read_bytes() == original

    incomplete_report = tmp_path / "incomplete-validation.md"
    incomplete_report.write_text(
        "\n".join(
            (
                RESULTS_BLOCK_BEGIN,
                "```json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "claims": {"tests": embedded["claims"]["tests"]},
                    }
                ),
                "```",
                RESULTS_BLOCK_END,
            )
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="claim labels do not match supplied outputs"):
        module.contrast_validation_report(incomplete_report, inputs)


@pytest.mark.hermes_exact
def test_callback_benchmark_uses_real_plugin_context_and_reports_tail_latency() -> None:
    pytest.importorskip("hermes_cli.plugins")
    spec = importlib.util.spec_from_file_location("qualify_observation_callbacks", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.measure_callbacks(40)
    assert result["sample_count"] == 160
    assert result["plugin_callback_count"] == 22
    assert result["unload_hook_count"] == 0
    assert result["p95_ms"] > 0
    assert result["p99_ms"] >= result["p95_ms"]
    assert result["surfaces"]["tool"]["sample_count"] == 80
    assert result["surfaces"]["tool"]["phases"] == {"pre": 40, "post": 40}
    assert result["surfaces"]["api"]["sample_count"] == 80
    assert result["surfaces"]["api"]["phases"] == {"pre": 40, "post": 40}
    assert result["worst"]["p95_ms"] == result["p95_ms"]
    assert result["worst"]["p99_ms"] == result["p99_ms"]
    assert result["raw_prompt_absent"] is True
    assert result["raw_response_absent"] is True
