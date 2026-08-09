"""Public Orca no-model fixture worker adapter contracts for M4."""

from __future__ import annotations

from typing import Any

from aether_mcp.orca_provider import FixtureRuntimeConfig, PublicOrcaLifecycleProvider


class Transport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.worktrees = 0
        self.terminals = 0
        self.dispatches = 0
        self.messages = 0

    def __call__(self, argv: tuple[str, ...]) -> dict[str, Any]:
        self.calls.append(argv)
        command = argv[:2]
        if command == ("worktree", "create"):
            self.worktrees += 1
            return {
                "id": f"req-worktree-{self.worktrees}",
                "ok": True,
                "result": {"worktree": {"id": f"worktree_{self.worktrees}", "path": f"/tmp/fixture-{self.worktrees}"}},
            }
        if command == ("terminal", "create"):
            self.terminals += 1
            return {
                "id": f"req-terminal-{self.terminals}",
                "ok": True,
                "result": {"terminal": {"agentTerminalHandle": f"term_fixture_{self.terminals}"}},
            }
        if command == ("orchestration", "dispatch"):
            self.dispatches += 1
            return {
                "id": f"req-worker-{self.dispatches}",
                "ok": True,
                "result": {
                    "dispatch": {"dispatchId": f"dispatch_fixture_{self.dispatches}"},
                },
            }
        if command == ("orchestration", "task-update"):
            status = argv[argv.index("--status") + 1]
            return {"id": "req-task-update", "ok": True, "result": {"task": {"status": status}}}
        if command == ("terminal", "send"):
            return {"id": "req-send-command", "ok": True, "result": {"sent": True}}
        if command == ("terminal", "stop"):
            return {"id": "req-terminal-stop", "ok": True, "result": {"stopped": True}}
        if command == ("orchestration", "send"):
            self.messages += 1
            return {
                "id": f"req-message-{self.messages}",
                "ok": True,
                "result": {"message": {"messageId": f"message_fixture_{self.messages}"}},
            }

        if command == ("terminal", "close"):
            return {"id": "req-close", "ok": True, "result": {"closed": True}}
        if command == ("worktree", "rm"):
            return {"id": "req-rm", "ok": True, "result": {"removed": True}}
        raise AssertionError(argv)


def _provider(transport: Transport) -> PublicOrcaLifecycleProvider:
    return PublicOrcaLifecycleProvider(
        transport=transport,
        binding_digest="a" * 64,
        coordinator_handle="term-coordinator",
        fixture_runtime=FixtureRuntimeConfig(
            repo_selector="path:/tmp/source",
            base_ref="HEAD",
            command_builder=lambda dispatch_id, worktree, _spec, generation: (
                f"python fixture.py --dispatch {dispatch_id} --root {worktree} --generation {generation}"
            ),
        ),
    )


def test_public_worker_adapter_creates_isolated_worktree_dispatch_and_command() -> None:
    transport = Transport()
    provider = _provider(transport)
    result = provider.dispatch_fixture(
        provider_run_id="run_fixture",
        provider_task_id="task_fixture",
        logical_dispatch_id="11111111-1111-4111-8111-111111111111",
        task_spec={"task_key": "worker", "placement": "child_worktree"},
        attempt_generation=1,
    )
    assert result.outcome == "APPLIED"
    assert result.provider_dispatch_id == "dispatch_fixture_1"
    assert result.worker_id == "term_fixture_1"
    assert result.terminal_id == "term_fixture_1"
    assert result.worktree_id == "path:/tmp/fixture-1"
    worker_start = next(call for call in transport.calls if call[:2] == ("orchestration", "dispatch"))
    assert worker_start[worker_start.index("--to") + 1] == "term_fixture_1"
    command_send = next(call for call in transport.calls if call[:2] == ("terminal", "send"))
    assert "11111111-1111-4111-8111-111111111111" in command_send[command_send.index("--text") + 1]


def test_public_worker_message_retry_and_cleanup_use_exact_dispatch() -> None:
    transport = Transport()
    provider = _provider(transport)
    first = provider.dispatch_fixture(
        provider_run_id="run_fixture",
        provider_task_id="task_fixture",
        logical_dispatch_id="11111111-1111-4111-8111-111111111111",
        task_spec={"task_key": "worker", "placement": "child_worktree"},
        attempt_generation=1,
    )
    message = provider.send_worker_message(
        provider_run_id="run_fixture",
        provider_task_id="task_fixture",
        provider_dispatch_id=first.provider_dispatch_id or "",
        terminal_id=first.terminal_id or "",
        from_coordinator=False,
        kind="completion_reference",
        payload={"outcome": "SUCCEEDED"},
        outcome="SUCCEEDED",
    )
    assert message.outcome == "APPLIED"
    completion = [call for call in transport.calls if call[:2] == ("orchestration", "task-update")][-1]
    assert completion[completion.index("--id") + 1] == "task_fixture"
    assert completion[completion.index("--status") + 1] == "completed"

    retry = provider.retry_fixture(
        provider_run_id="run_fixture",
        provider_task_id="task_fixture",
        prior_provider_dispatch_id="dispatch_fixture_1",
        logical_dispatch_id="22222222-2222-4222-8222-222222222222",
        task_spec={"task_key": "worker", "placement": "child_worktree"},
        attempt_generation=2,
    )
    assert retry.provider_dispatch_id == "dispatch_fixture_2"
    retry_call = [call for call in transport.calls if call[:2] == ("orchestration", "dispatch")][-1]
    assert retry_call[retry_call.index("--to") + 1] == "term_fixture_2"
    assert any(call[:2] == ("orchestration", "task-update") for call in transport.calls)

    cleaned = provider.cleanup_worker(
        provider_dispatch_id=retry.provider_dispatch_id or "",
        terminal_id=retry.terminal_id or "",
        worktree_id=retry.worktree_id or "",
    )
    assert cleaned.outcome == "APPLIED" and cleaned.cleanup_complete
    assert [call[:2] for call in transport.calls[-2:]] == [
        ("terminal", "stop"),
        ("worktree", "rm"),
    ]
