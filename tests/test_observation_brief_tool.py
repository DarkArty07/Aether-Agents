from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from observation_helpers import (
    PROJECT_ID,
    TRACE_ID,
    EventFactory,
    complete_trace,
    native_pseudonym,
    project_marker,
)

from aether_agents.observation import brief, query, report
from aether_agents.observation.capture.journal import JournalWriter
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import (
    canonical_json_bytes,
    is_finish_reason_count,
    is_finish_reason_name,
    summary_validator,
    validate_summary,
)
from aether_agents.observation.identity import summary_id as make_summary_id
from aether_agents.observation.privacy import ForbiddenPayload, assert_clean, scan
from aether_agents.paths import ObservationPaths


def _project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, ObservationPaths]:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(project_marker(PROJECT_ID), encoding="utf-8")
    assert ProjectRegistry().register(PROJECT_ID, project, "brief")
    return project, ObservationPaths.for_project(PROJECT_ID)


def _journal(paths: ObservationPaths) -> None:
    fixture = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    try:
        for event in fixture.events:
            assert writer.append(event).accepted
    finally:
        writer.close()


def test_status_is_curated_bounded_and_contains_no_raw_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _project(monkeypatch, tmp_path)
    _journal(paths)
    value = brief.observe(
        {"action": "status", "project": str(project), "ref": TRACE_ID},
        profile_name="morfeo",
    )
    assert value["schema_version"] == brief.SCHEMA_VERSION
    assert value["state"] == "ready"
    summary = query.load_summary(paths, TRACE_ID)
    assert value["completion_state"] == summary["completion_state"]
    assert value["runtime_state"] == summary["runtime_state"]
    assert value["work"]["all_required_done"] == summary["work_graph"]["all_required_done"]
    assert value["acceptance"]["complete"] == summary["acceptance"]["complete"]
    encoded = json.dumps(value, sort_keys=True)
    assert len(encoded.encode()) <= 2048
    for forbidden in ("raw", "prompt", "response", "command", "output", "diff", "reasoning"):
        assert forbidden not in encoded.lower()
    assert summary["summary_id"] == value["summary_id"]


def test_diagnose_returns_only_bounded_codes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, _paths = _project(monkeypatch, tmp_path)
    _journal(_paths)
    value = brief.observe(
        {"action": "diagnose", "project": str(project), "ref": TRACE_ID},
        profile_name="morfeo",
    )
    assert value["action"] == "diagnose"
    assert len(value["coverage"]["reason_codes"]) <= 5
    assert len(value["finding_codes"]) <= 5
    assert len(value["bottleneck_classes"]) <= 5
    assert len(value["defect_classes"]) <= 5
    assert len(json.dumps(value).encode()) <= 4096


def test_changes_uses_existing_semantic_diff_and_requires_since(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _project(monkeypatch, tmp_path)
    _journal(paths)
    current = query.load_summary(paths, TRACE_ID)
    previous = deepcopy(current)
    previous["review_brief"]["verdict"] = "work_remaining"
    previous["summary_id"] = make_summary_id(previous)
    paths.summaries.mkdir(parents=True, exist_ok=True)
    previous_path = paths.summary_file(previous["summary_id"])
    previous_path.write_bytes(canonical_json_bytes(previous))
    previous_path.chmod(0o600)
    value = brief.observe(
        {
            "action": "changes",
            "project": str(project),
            "ref": TRACE_ID,
            "since_summary_id": previous["summary_id"],
        },
        profile_name="morfeo",
    )
    assert value["comparable"] is True
    assert "verdict" in value["change_classes"]
    assert "details" not in value
    with pytest.raises(brief.BriefError, match="requires since_summary_id"):
        brief.observe(
            {"action": "changes", "project": str(project), "ref": TRACE_ID},
            profile_name="morfeo",
        )


def test_empty_unknown_and_role_gate_are_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, _paths = _project(monkeypatch, tmp_path)
    value = brief.observe({"action": "status", "project": str(project)}, profile_name="morfeo")
    assert value == {
        "schema_version": brief.SCHEMA_VERSION,
        "action": "status",
        "state": "empty",
        "project_id": PROJECT_ID,
        "trace_id": None,
        "contract_id": None,
        "summary_id": None,
    }
    with pytest.raises(brief.BriefError) as denied:
        brief.observe({"action": "status", "project": str(project)}, profile_name="supervisor")
    assert denied.value.code == "AETHER-OBSERVE-ROLE-DENIED"


def test_plugin_registers_tool_only_for_enabled_morfeo(monkeypatch: pytest.MonkeyPatch) -> None:
    from aether_agents.observation.capture import hermes_plugin

    registered: dict[str, Any] = {}

    class Context:
        profile_name = "morfeo"

        def get_config(self, key: str, default: object = None) -> object:
            return True if key == "curated_tool" else default

        def register_tool(self, **kwargs: Any) -> None:
            registered.update(kwargs)

        def register_hook(self, _name: str, _callback: Any) -> None:
            pass

        def on_unload(self, _callback: Any) -> None:
            pass

    ctx = Context()
    monkeypatch.setattr(hermes_plugin, "_REGISTERED", set())
    monkeypatch.setattr(hermes_plugin, "_REGISTERED_FALLBACK", set())
    hermes_plugin.register(ctx)
    assert registered["name"] == "aether_observe"
    assert registered["toolset"] == "aether_observation"
    handler = registered["handler"]
    ctx.profile_name = "supervisor"
    denied = json.loads(handler({"action": "status"}))
    assert denied["error"]["code"] == "AETHER-OBSERVE-ROLE-DENIED"

    class Supervisor(Context):
        profile_name = "supervisor"

    other: dict[str, Any] = {}
    sup = Supervisor()
    sup.register_tool = lambda **kwargs: other.update(kwargs)  # type: ignore[method-assign]
    hermes_plugin.register(sup)
    assert other == {}

    failing: dict[str, Any] = {}
    broken = Context()
    broken.get_config = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("config"))  # type: ignore[method-assign]
    broken.register_tool = lambda **kwargs: failing.update(kwargs)  # type: ignore[method-assign]
    hermes_plugin.register(broken)
    assert failing == {}


def test_real_plugin_context_registers_and_unloads_curated_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("hermes_cli.plugins")
    home = tmp_path / "profiles" / "morfeo"
    home.mkdir(parents=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  entries:\n"
        "    aether-contract-observer:\n"
        "      settings:\n"
        "        curated_tool: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
    from tools.registry import registry

    from aether_agents.observation.capture import hermes_plugin

    manager = PluginManager(scope_key=str(home))
    manifest = PluginManifest(
        name="aether-contract-observer",
        key="aether-contract-observer",
        source="entrypoint",
    )
    context = PluginContext(manifest, manager)
    monkeypatch.setattr(hermes_plugin, "_REGISTERED", set())
    monkeypatch.setattr(hermes_plugin, "_REGISTERED_FALLBACK", set())
    hermes_plugin.register(context)
    entry = registry.get_entry("aether_observe", scope=manager.scope_key)
    assert entry is not None
    assert entry.toolset == "aether_observation"
    assert manager.unload(manifest)
    assert registry.get_entry("aether_observe", scope=manager.scope_key) is None


# --------------------------------------------------------------------------------------
# TS-390: the schema-owned finish-reason histogram survives the real pipeline
#
# ``model_context_economics.finish_reasons`` is the single integer histogram owned by
# ``observation-summary.schema.json``.  A native finish reason such as ``tool_calls`` or
# ``error`` is typed data inside that namespace, not the raw payload field of the same
# name, so it must survive projection, journal persistence, reduction, storage and this
# compact observation boundary with its original count.  Every other location --
# including a look-alike path in unrelated payload -- keeps the forbidden-key behavior.
# This lane lives here because the locked qualification node manifest pins the exact
# node identity of the other observation test modules.
# --------------------------------------------------------------------------------------

FINISH_REASONS = ("stop", "tool_calls", "error")
_COMPLETE_SUMMARY = (
    Path(__file__).resolve().parent / "fixtures" / "observation/complete-summary.json"
)


def _finish_reason_request(f: EventFactory, reason: str, ordinal: int) -> dict[str, Any]:
    return f.add(
        f.builder.model_request(
            state="completed",
            # Every native API request has its own identity; the reducer's existing
            # reconciliation keeps two terminals of one identity as one attempt.
            request_ref=native_pseudonym("api_request", f"synthetic-request-{ordinal}"),
            model="synthetic-model",
            provider="synthetic-provider",
            duration_ms=1,
            finish_reason=reason,
            message_count=1,
            tool_count=1,
            attempt_count=1,
            tokens={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            usage_coverage="exact",
            occurred_at=f.at(float(ordinal)),
            session_id=native_pseudonym("session", "synthetic-session"),
        )
    )


def _finish_reason_trace(*reasons: str) -> EventFactory:
    f = EventFactory()
    f.opened(0)
    for ordinal, reason in enumerate(reasons, start=1):
        _finish_reason_request(f, reason, ordinal)
    return f


def _event_journal(paths: ObservationPaths, f: EventFactory) -> None:
    writer = JournalWriter(paths=paths, producer_epoch=f.epoch)
    writer.open()
    try:
        for event in f.events:
            assert writer.append(event).accepted
    finally:
        writer.close()


@pytest.mark.parametrize("reason", FINISH_REASONS)
def test_finish_reason_histogram_is_schema_valid_and_privacy_clean(reason: str) -> None:
    """The published schema and the privacy guard must not contradict each other."""
    summary = json.loads(_COMPLETE_SUMMARY.read_text(encoding="utf-8"))
    summary["model_context_economics"]["finish_reasons"] = {reason: 1}
    validate_summary(summary)
    assert_clean(summary)


@pytest.mark.parametrize("reason", FINISH_REASONS)
def test_finish_reason_histogram_survives_persistence_reduction_storage_and_compact_observe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reason: str
) -> None:
    """TS-390 traversal: model_request -> journal -> reduce -> storage -> compact query."""
    project, paths = _project(monkeypatch, tmp_path)
    _event_journal(paths, _finish_reason_trace(reason))

    # Persistence: the canonical journal line keeps the native reason verbatim.
    persisted = b"".join(
        path.read_bytes() for path in paths.project.rglob("*.jsonl") if path.is_file()
    )
    assert f'"finish_reason":"{reason}"'.encode() in persisted

    # query.load_summary performs the real ingest -> reduce -> ReadModel.record_summary
    # path for this project; a rejected histogram would surface as an unreadable state.
    summary = query.load_summary(paths, TRACE_ID)
    validate_summary(summary)
    assert_clean(summary)
    assert summary["model_context_economics"]["finish_reasons"] == {reason: 1}

    # The immutable on-disk summary is re-validated by the guard when it is loaded back
    # for `aether observe --since`.
    retained = query.load_previous_summary(paths, summary["summary_id"])
    assert retained["model_context_economics"]["finish_reasons"] == {reason: 1}

    # Compact observation of the same trace stays readable, and the compact human brief
    # reports the original count.
    observed = brief.observe(
        {"action": "status", "project": str(project), "ref": TRACE_ID},
        profile_name="morfeo",
    )
    assert observed["state"] == "ready"
    assert observed["summary_id"] == summary["summary_id"]
    assert f"{reason}=1" in report.render_brief(summary)


def test_every_finish_reason_count_survives_one_trace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """All three native reasons persist together with their own counts preserved."""
    _project_path, paths = _project(monkeypatch, tmp_path)
    _event_journal(paths, _finish_reason_trace("stop", "tool_calls", "tool_calls", "error"))

    expected = {"error": 1, "stop": 1, "tool_calls": 2}
    summary = query.load_summary(paths, TRACE_ID)
    assert summary["model_context_economics"]["finish_reasons"] == expected
    assert (
        query.load_previous_summary(paths, summary["summary_id"])["model_context_economics"][
            "finish_reasons"
        ]
        == expected
    )

    rendered = report.render_brief(summary)
    assert "finish reasons: error=1, stop=1, tool_calls=2" in rendered


def test_guard_interprets_the_histogram_exactly_as_the_summary_schema() -> None:
    """The typed predicate and the normative schema grammar are one interpretation."""
    schema = summary_validator().schema
    assert isinstance(schema, dict)
    histogram = schema["$defs"]["modelContextEconomics"]["properties"]["finish_reasons"]
    economics = schema["$defs"]["modelContextEconomics"]
    assert histogram["propertyNames"]["pattern"] == r"^[A-Za-z0-9_.:-]{1,64}$"
    assert histogram["additionalProperties"] == {"type": "integer", "minimum": 0}
    assert economics["required"].count("finish_reasons") == 1
    validator = Draft202012Validator(histogram)

    names = (
        "stop",
        "tool_calls",
        "error",
        "length",
        "content_filter:limit",
        "MAX_TOKENS",
        "a" * 64,
    )
    for name in names:
        assert validator.is_valid({name: 1}) is is_finish_reason_name(name)
    rejected_names = ("", "tool calls", "a" * 65, "naïve", "stop!", "./stop", "@stop")
    for name in rejected_names:
        assert validator.is_valid({name: 1}) is is_finish_reason_name(name)
    for count in (0, 1, 7, 2**53, -1, True, False, 1.5, "1", None, [], {"n": 1}):
        assert validator.is_valid({"stop": count}) is is_finish_reason_count(count)


def test_privacy_guard_relaxes_only_the_schema_owned_finish_reason_histogram() -> None:
    # TS-390: typed histogram data at the one schema-owned path...
    assert_clean({"model_context_economics": {"finish_reasons": {"tool_calls": 1, "error": 2}}})
    # ...and nowhere else.
    with pytest.raises(ForbiddenPayload):
        assert_clean({"elsewhere": {"finish_reasons": {"tool_calls": 1}}})
    with pytest.raises(ForbiddenPayload):
        assert_clean({"model_context_economics": {"tool_calls": 1}})


@pytest.mark.parametrize(
    ("payload", "reason_code"),
    [
        # Raw payload fields anywhere else keep the forbidden-key behavior.
        ({"tool_calls": [{"arguments": "raw synthetic text"}]}, "FORBIDDEN_KEY"),
        ({"error": "synthetic error contents"}, "FORBIDDEN_KEY"),
        ({"elsewhere": {"tool_calls": 1}}, "FORBIDDEN_KEY"),
        ({"elsewhere": {"error": 1}}, "FORBIDDEN_KEY"),
        # Wrong namespace: a summary key that is not the schema-owned histogram.
        ({"flow": {"finish_reasons": {"tool_calls": 1}}}, "FORBIDDEN_KEY"),
        ({"runtime_state": {"finish_reasons": {"error": 1}}}, "FORBIDDEN_KEY"),
        # A nested look-alike path is not the schema-owned histogram path.
        (
            {"other": {"model_context_economics": {"finish_reasons": {"tool_calls": 1}}}},
            "FORBIDDEN_KEY",
        ),
        # A forbidden key beside the histogram inside the same object is still forbidden.
        (
            {"model_context_economics": {"finish_reasons": {"stop": 1}, "tool_calls": 2}},
            "FORBIDDEN_KEY",
        ),
        # Nested data is never histogram data.
        (
            {"model_context_economics": {"finish_reasons": ["stop"]}},
            "INVALID_FINISH_REASON_HISTOGRAM",
        ),
        (
            {"model_context_economics": {"finish_reasons": None}},
            "INVALID_FINISH_REASON_HISTOGRAM",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"stop": {"count": 1}}}},
            "INVALID_FINISH_REASON_COUNT",
        ),
        # Unsafe names.
        (
            {"model_context_economics": {"finish_reasons": {"tool calls": 1}}},
            "INVALID_FINISH_REASON_NAME",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"a" * 65: 1}}},
            "INVALID_FINISH_REASON_NAME",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"estopé": 1}}},
            "INVALID_FINISH_REASON_NAME",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"/absolute/path": 1}}},
            "INVALID_FINISH_REASON_NAME",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"sk-" + "a" * 20: 1}}},
            "INVALID_FINISH_REASON_NAME",
        ),
        # Counts that are not strict non-negative integers.
        (
            {"model_context_economics": {"finish_reasons": {"stop": -1}}},
            "INVALID_FINISH_REASON_COUNT",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"stop": 1.0}}},
            "INVALID_FINISH_REASON_COUNT",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"stop": True}}},
            "INVALID_FINISH_REASON_COUNT",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"stop": "1"}}},
            "INVALID_FINISH_REASON_COUNT",
        ),
        (
            {"model_context_economics": {"finish_reasons": {"stop": None}}},
            "INVALID_FINISH_REASON_COUNT",
        ),
    ],
)
def test_forbidden_and_ill_typed_histogram_payloads_stay_rejected(
    payload: dict[str, Any], reason_code: str
) -> None:
    found = scan(payload)
    assert found is not None, f"accepted forbidden payload at {sorted(payload)}"
    assert found[0] == reason_code
    with pytest.raises(ForbiddenPayload):
        assert_clean(payload)


@pytest.mark.parametrize(
    "histogram",
    [
        {},
        {"stop": 0},
        {"stop": 12, "tool_calls": 3, "error": 1},
        {"MAX_TOKENS": 1, "content_filter:limit": 2, "length_limit": 3},
    ],
)
def test_schema_owned_histogram_shapes_stay_accepted(histogram: dict[str, int]) -> None:
    assert_clean({"model_context_economics": {"finish_reasons": histogram}})
