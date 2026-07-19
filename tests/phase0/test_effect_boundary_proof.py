"""Phase 0 proof of Hermes' pre-dispatch effect boundary.

These tests use the installed Hermes Agent implementation and replace only
external middleware, approval, plugin, and registry seams.  The fake tool is
never executed and no live gateway is started.
"""

from __future__ import annotations

import builtins
import json
import socket
import subprocess
from types import SimpleNamespace
from typing import Any

import hermes_cli.plugins as plugins
import model_tools
import pytest

TOOL_NAME = "phase0_harmless_fake_tool"
CALL_CONTEXT = {
    "task_id": "task-0",
    "session_id": "session-0",
    "tool_call_id": "call-0",
    "turn_id": "turn-0",
    "api_request_id": "request-0",
    "tool_request_middleware_trace": [{"stage": "phase0", "value": "trace-0"}],
}


@pytest.fixture
def boundary(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    dispatch_calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    pre_calls: list[dict[str, Any]] = []
    post_calls: list[dict[str, Any]] = []
    state = {"pre_result": None, "pre_exception": None}

    def fake_dispatch(name: str, args: dict[str, Any], **kwargs: Any) -> str:
        dispatch_calls.append((name, args, kwargs))
        return json.dumps({"ok": True, "tool": name})

    def fake_invoke_hook(hook_name: str, **kwargs: Any) -> list[Any]:
        if hook_name == "pre_tool_call":
            pre_calls.append(kwargs)
            if state["pre_exception"] is not None:
                raise state["pre_exception"]
            if state["pre_result"] is not None:
                return [{"action": "block", "message": state["pre_result"]}]
        elif hook_name == "post_tool_call":
            post_calls.append(kwargs)
        return []

    def no_middleware(
        name: str,
        args: dict[str, Any],
        **kwargs: Any,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            payload=dict(args), original_payload=dict(args), trace=list(
                CALL_CONTEXT["tool_request_middleware_trace"]
            )
        )

    def run_middleware(
        name: str,
        args: dict[str, Any],
        dispatch: Any,
        **kwargs: Any,
    ) -> str:
        return dispatch(args)

    monkeypatch.setattr(model_tools.registry, "dispatch", fake_dispatch)
    monkeypatch.setattr(plugins, "invoke_hook", fake_invoke_hook)
    monkeypatch.setattr(plugins, "has_hook", lambda hook_name: hook_name == "post_tool_call")

    import hermes_cli.middleware as middleware

    monkeypatch.setattr(middleware, "apply_tool_request_middleware", no_middleware)
    monkeypatch.setattr(middleware, "run_tool_execution_middleware", run_middleware)

    import acp_adapter.edit_approval as edit_approval

    monkeypatch.setattr(edit_approval, "maybe_require_edit_approval", lambda *_args: None)

    import tools.file_tools as file_tools

    monkeypatch.setattr(file_tools, "notify_other_tool_call", lambda *_args: None)

    return {
        "dispatch": dispatch_calls,
        "pre": pre_calls,
        "post": post_calls,
        "state": state,
    }


def invoke(boundary: dict[str, Any], **overrides: Any) -> str:
    args = {"value": "harmless"}
    context = dict(CALL_CONTEXT)
    context.update(overrides)
    return model_tools.handle_function_call(
        TOOL_NAME,
        args,
        **context,
        skip_tool_request_middleware=False,
    )


def test_pre_tool_block_is_structured_and_precedes_dispatch(boundary: dict[str, Any]) -> None:
    boundary["state"]["pre_result"] = "coordination policy denied"

    result = invoke(boundary)

    assert json.loads(result) == {"error": "coordination policy denied"}
    assert boundary["dispatch"] == []
    assert len(boundary["pre"]) == 1


def test_blocked_execution_emits_post_status_and_error_type(boundary: dict[str, Any]) -> None:
    boundary["state"]["pre_result"] = "blocked for proof"

    invoke(boundary)

    assert len(boundary["post"]) == 1
    assert boundary["post"][0]["status"] == "blocked"
    assert boundary["post"][0]["error_type"] == "plugin_block"
    assert boundary["post"][0]["error_message"] == "blocked for proof"


def test_allowed_execution_dispatches_exactly_once(boundary: dict[str, Any]) -> None:
    result = invoke(boundary)

    assert json.loads(result)["ok"] is True
    assert len(boundary["dispatch"]) == 1
    assert boundary["dispatch"][0][0] == TOOL_NAME


def test_pre_hook_receives_full_coordination_context(boundary: dict[str, Any]) -> None:
    invoke(boundary)

    pre = boundary["pre"][0]
    assert {key: pre[key] for key in CALL_CONTEXT if key != "tool_request_middleware_trace"} == {
        "task_id": "task-0",
        "session_id": "session-0",
        "tool_call_id": "call-0",
        "turn_id": "turn-0",
        "api_request_id": "request-0",
    }
    assert pre["middleware_trace"] == CALL_CONTEXT["tool_request_middleware_trace"]


def test_skip_pre_hook_avoids_double_fire_and_still_dispatches(
    boundary: dict[str, Any],
) -> None:
    result = model_tools.handle_function_call(
        TOOL_NAME,
        {"value": "harmless"},
        **CALL_CONTEXT,
        skip_pre_tool_call_hook=True,
    )

    assert json.loads(result)["ok"] is True
    assert boundary["pre"] == []
    assert len(boundary["dispatch"]) == 1


def test_hook_exception_is_fail_open_and_cannot_block_dispatch(
    boundary: dict[str, Any],
) -> None:
    boundary["state"]["pre_exception"] = RuntimeError("coordination hook failed")

    result = invoke(boundary)

    assert json.loads(result)["ok"] is True
    assert len(boundary["dispatch"]) == 1
    assert boundary["post"][0]["status"] == "ok"
    assert boundary["post"][0]["error_type"] is None


def test_boundary_proof_has_no_file_network_or_process_side_effects(
    boundary: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("boundary proof attempted an external side effect")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    boundary["state"]["pre_result"] = "side effect test blocked"

    result = invoke(boundary)

    assert json.loads(result)["error"] == "side effect test blocked"
    assert boundary["dispatch"] == []
