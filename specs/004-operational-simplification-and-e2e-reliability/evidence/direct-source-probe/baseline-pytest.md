# Baseline pytest

Historical command output from the recovery qualification. Paths are redacted;
pytest node paths refer to the original qualification workspace.

```text
.FFFF                                                                    [100%]
=================================== FAILURES ===================================
______ test_controller_needs_input_without_explicit_signal_reaches_origin ______

flow = (<module 'hermes_cli.kanban_db' from '<imported-Hermes>/hermes_...e_safe_read.TrackedConnection object at 0x7f4131dd3250>, <function flow.<locals>.task at 0x7f4131c8d580>, 't_8cabe13d')

    def test_controller_needs_input_without_explicit_signal_reaches_origin(flow):
        kb, conn, unit, controller = topology(flow)
        assert kb.block_task(conn, unit, kind='needs_input', reason='missing owner decision')
        assert origin_events(kb, conn, controller) == []
        assert kb.claim_task(conn, controller)
        assert kb.block_task(conn, controller, kind='needs_input', reason='owner decision required')
        events = origin_events(kb, conn, controller)
>       assert len(events) == 1, 'Both tasks are blocked, but no event can reach origin'
E       AssertionError: Both tasks are blocked, but no event can reach origin
E       assert 0 == 1
E        +  where 0 = len([])

specs/004-operational-simplification-and-e2e-reliability/evidence/direct-source-probe/test_hlp280_live_routing_probe.py:79: AssertionError
____________ test_exhausted_non_affinity_child_routes_to_controller ____________

flow = (<module 'hermes_cli.kanban_db' from '<imported-Hermes>/hermes_...e_safe_read.TrackedConnection object at 0x7f4131b34150>, <function flow.<locals>.task at 0x7f4132317920>, 't_275d0fa9')

    def test_exhausted_non_affinity_child_routes_to_controller(flow):
        kb, conn, unit, controller = topology(flow)
        assert kb._record_task_failure(conn, unit, 'spawn failed', outcome='spawn_failed',
                                       failure_limit=1, release_claim=True, end_run=True)
        # These are the two actual calls used by the current dispatcher failure path.
        kb._route_affinity_terminal(conn, unit, reason='spawn failed', outcome='failed')
>       assert kb.get_task(conn, controller).status == 'ready', 'Controller remains parent-gated'
E       AssertionError: Controller remains parent-gated
E       assert 'todo' == 'ready'
E
E         - ready
E         + todo

specs/004-operational-simplification-and-e2e-reliability/evidence/direct-source-probe/test_hlp280_live_routing_probe.py:89: AssertionError
_____________ test_root_block_before_controller_has_origin_signal ______________

flow = (<module 'hermes_cli.kanban_db' from '<imported-Hermes>/hermes_...e_safe_read.TrackedConnection object at 0x7f4131b35050>, <function flow.<locals>.task at 0x7f4131b227a0>, 't_455b4da1')

    def test_root_block_before_controller_has_origin_signal(flow):
        kb, conn, _, root = flow
        assert kb.claim_task(conn, root)
        assert kb.block_task(conn, root, kind='needs_input', reason='root cannot decompose')
>       assert len(origin_events(kb, conn, root)) == 1, 'Bootstrap root blocks silently'
E       AssertionError: Bootstrap root blocks silently
E       assert 0 == 1
E        +  where 0 = len([])
E        +    where [] = origin_events(<module 'hermes_cli.kanban_db' from '<imported-Hermes>/hermes_cli/kanban_db.py'>, <hermes_cli.sqlite_safe_read.TrackedConnection object at 0x7f4131b35050>, 't_455b4da1')

specs/004-operational-simplification-and-e2e-reliability/evidence/direct-source-probe/test_hlp280_live_routing_probe.py:98: AssertionError
__________ test_pending_attention_cannot_be_kept_silent_by_heartbeats __________

flow = (<module 'hermes_cli.kanban_db' from '<imported-Hermes>/hermes_...e_safe_read.TrackedConnection object at 0x7f4131b35d50>, <function flow.<locals>.task at 0x7f4131b22980>, 't_9c783a04')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7f4131c9e410>

    def test_pending_attention_cannot_be_kept_silent_by_heartbeats(flow, monkeypatch):
        import os
        import time
        kb, conn, unit, controller = topology(flow)
        assert kb.block_task(conn, unit, kind='needs_input', reason='decision unresolved')
        assert kb.claim_task(conn, controller)
        kb._set_worker_pid(conn, controller, os.getpid())
        future = time.time() + 301
        monkeypatch.setattr(kb.time, 'time', lambda: future)
        # The process is alive and refreshes its lease, but has not resolved the attention.
        assert kb.heartbeat_claim(conn, controller)
        assert kb.heartbeat_worker(conn, controller)
        def forbidden_spawn(*args, **kwargs):
            raise AssertionError('Qualification must not spawn any worker')
        result = kb.dispatch_once(conn, spawn_fn=forbidden_spawn, max_spawn=0)
        assert not result.spawned
        assert kb.get_task(conn, controller).status == 'running'
>       assert origin_events(kb, conn, controller), 'Heartbeat-only controller has no bounded escalation'
E       AssertionError: Heartbeat-only controller has no bounded escalation
E       assert []
E        +  where [] = origin_events(<module 'hermes_cli.kanban_db' from '<imported-Hermes>/hermes_cli/kanban_db.py'>, <hermes_cli.sqlite_safe_read.TrackedConnection object at 0x7f4131b35d50>, 't_2ccd7e3e')

specs/004-operational-simplification-and-e2e-reliability/evidence/direct-source-probe/test_hlp280_live_routing_probe.py:118: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../dev::test_controller_needs_input_without_explicit_signal_reaches_origin
FAILED ../../../../../../../dev::test_exhausted_non_affinity_child_routes_to_controller
FAILED ../../../../../../../dev::test_root_block_before_controller_has_origin_signal
FAILED ../../../../../../../dev::test_pending_attention_cannot_be_kept_silent_by_heartbeats
4 failed, 1 passed in 0.53s
```
