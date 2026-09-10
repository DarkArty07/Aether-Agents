"""Read-only product diagnostics. All mutable fixtures live under pytest tmp_path.
Failures here represent the reported desired behavior, not implementation changes.
"""
import json
import sqlite3
from pathlib import Path
import pytest
from test_project_knowledge_engine import PROJECT, OTHER, project
from aether_agents.knowledge.bindings import bind_session, context_for_session
from aether_agents.knowledge.common import KnowledgeError
from aether_agents.observation.contracts import validate_summary
from aether_agents.observation.privacy import assert_clean, ForbiddenPayload

ROOT = Path(__file__).resolve().parents[3]

def native_home(tmp_path, cwd):
    home = tmp_path / 'native-home'
    home.mkdir()
    with sqlite3.connect(home / 'state.db') as conn:
        conn.execute('CREATE TABLE sessions(id TEXT PRIMARY KEY, cwd TEXT)')
        conn.execute('INSERT INTO sessions VALUES (?,?)', ('exact-session', cwd))
    return home

@pytest.mark.parametrize('cwd_kind', ['absent', 'empty', 'plain-directory'])
def test_373_explicit_binding_with_no_usable_native_project(tmp_path, cwd_kind):
    root, state = project(tmp_path)
    bind_session(state, PROJECT, 'morfeo', 'exact-session', root=root)
    plain = tmp_path / 'plain-directory'
    plain.mkdir()
    cwd = {'absent':None, 'empty':'', 'plain-directory':str(plain)}[cwd_kind]
    home = native_home(tmp_path, cwd)
    assert context_for_session(state, 'morfeo', 'exact-session', hermes_home=home).root == root

@pytest.mark.parametrize('case', ['different-native-project', 'different-session'])
def test_373_conflicting_or_other_session_binding_stays_rejected(tmp_path, case):
    root, state = project(tmp_path)
    other, _ = project(tmp_path, OTHER, 'beta')
    bind_session(state, PROJECT, 'morfeo', 'exact-session', root=root)
    home = native_home(tmp_path, str(other) if case == 'different-native-project' else None)
    session = 'exact-session' if case == 'different-native-project' else 'another-session'
    with pytest.raises(KnowledgeError) as caught:
        context_for_session(state, 'morfeo', session, hermes_home=home)
    assert caught.value.code == ('PROJECT_CONFLICT' if case == 'different-native-project' else 'PROJECT_UNRESOLVED')

@pytest.mark.parametrize('reason', ['stop', 'tool_calls', 'error'])
def test_390_schema_valid_numeric_histogram_passes_privacy(reason):
    summary = json.loads((ROOT / 'tests/fixtures/observation/complete-summary.json').read_text())
    summary['model_context_economics']['finish_reasons'] = {reason:1}
    validate_summary(summary)
    assert_clean(summary)

@pytest.mark.parametrize('reason', ['stop', 'tool_calls', 'error'])
def test_390_real_event_reducer_and_storage_boundary(tmp_path, reason):
    from observation_helpers import EventFactory, PROJECT_ID, native_pseudonym
    from aether_agents.observation.storage import ReadModel
    from aether_agents.paths import ObservationPaths
    f = EventFactory()
    f.opened(0)
    f.add(f.builder.model_request(
        state='completed', request_ref=native_pseudonym('api_request', 'synthetic-request'),
        model='synthetic-model', provider='synthetic-provider', duration_ms=1,
        finish_reason=reason, message_count=1, tool_count=1, attempt_count=1,
        tokens={'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2},
        usage_coverage='exact', occurred_at=f.at(1),
        session_id=native_pseudonym('session', 'synthetic-session'),
    ))
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with ReadModel.open(paths) as model:
        assert model.upsert_events(f.events) == len(f.events)
        summary = f.summary()
        assert summary['model_context_economics']['finish_reasons'] == {reason: 1}
        assert model.record_summary(summary)


@pytest.mark.parametrize('payload', [
    {'tool_calls': [{'arguments': 'raw synthetic text'}]},
    {'error':'synthetic error contents'},
    {'elsewhere':{'tool_calls':1}},
])
def test_390_raw_and_wrong_namespace_payloads_stay_rejected(payload):
    with pytest.raises(ForbiddenPayload):
        assert_clean(payload)
