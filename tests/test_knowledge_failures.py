"""Failure-path behavior for private notes, contexts and operator commands."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_project_knowledge_engine import PROJECT, project
from test_project_knowledge_engine import native_python as native_python
from test_work_memory import payload

from aether_agents.cli import _build_parser
from aether_agents.commands.knowledge import run_knowledge
from aether_agents.knowledge.common import KnowledgeError
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.memory import WorkMemoryStore
from aether_agents.knowledge.service import KnowledgeService


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"situation": ""}, "ARGUMENT_INVALID"),
        ({"lesson": "x" * 16001}, "ARGUMENT_INVALID"),
        ({"lesson": "sk-" + "a" * 40}, "SENSITIVE_CONTENT"),
        ({"outcome": "invented"}, "ARGUMENT_INVALID"),
        ({"evidence": "not a list"}, "ARGUMENT_INVALID"),
        ({"evidence": [{"path": "module.py", "secret": "unknown"}]}, "ARGUMENT_INVALID"),
        ({"evidence": [{"path": ""}]}, "ARGUMENT_INVALID"),
        ({"evidence": [{"path": "../elsewhere.py"}]}, "UNSAFE_PATH"),
        ({"evidence": [{"path": "module.py", "revision": "HEAD"}]}, "ARGUMENT_INVALID"),
        ({"source_nodes": [None]}, "ARGUMENT_INVALID"),
        ({"source_nodes": ["sk-" + "a" * 40]}, "SENSITIVE_CONTENT"),
    ],
)
def test_invalid_notes_are_rejected_before_publication(
    tmp_path: Path, overrides: dict, code: str
) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = WorkMemoryStore(state)
    with pytest.raises(KnowledgeError) as failure:
        store.execute(ctx, "save", {**payload(), **overrides})
    assert failure.value.code == code
    assert store.execute(ctx, "export", {})["notes"] == []


@pytest.mark.parametrize("identity,role", [("invalid", "morfeo"), (PROJECT, "unknown")])
def test_invalid_memory_namespace_cannot_select_storage(
    tmp_path: Path, identity: str, role: str
) -> None:
    _root, state = project(tmp_path)
    original = resolve_context(PROJECT, "morfeo", state_root=state)
    context = replace(original, project_id=identity, role_id=role)
    with pytest.raises(KnowledgeError) as failure:
        WorkMemoryStore(state).execute(context, "export", {})
    assert failure.value.code == "PROJECT_UNRESOLVED"


def test_memory_unavailable_component_and_invalid_query_paths(tmp_path: Path) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = WorkMemoryStore(state)
    for action, args, code in (
        ("save", payload(), "COMPONENT_UNAVAILABLE"),
        ("search", {"query": "sample", "limit": 0}, "ARGUMENT_INVALID"),
        ("read", {"note_id": "wn_" + "a" * 32}, "NOTE_MISSING"),
        ("delete", {"note_id": "bad"}, "ARGUMENT_INVALID"),
        ("delete", {"note_id": "wn_" + "a" * 32}, "NOTE_MISSING"),
        ("correct", {"note_id": "wn_" + "a" * 32}, "NOTE_MISSING"),
        ("unknown", {}, "ARGUMENT_INVALID"),
    ):
        with pytest.raises(KnowledgeError) as failure:
            store.execute(ctx, action, args)
        assert failure.value.code == code


def test_evidence_is_project_relative_and_remains_reported(
    tmp_path: Path, native_python: Path
) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "supervisor", state_root=state)
    store = WorkMemoryStore(state, native_python)
    evidence = [{"path": "module.py", "result": "Agent reported pass"}, {"path": "missing.py"}]
    note = store.execute(ctx, "save", {**payload(), "evidence": evidence})
    result = store.execute(ctx, "read", {"note_id": note["note_id"]})
    assert result["verification"] == "reported"
    assert [item["source_exists"] for item in result["evidence"]] == [True, False]
    assert not any(item["result_independently_verified"] for item in result["evidence"])
    with pytest.raises(KnowledgeError) as failure:
        store.execute(
            ctx,
            "save",
            {**payload(), "evidence": [{"path": "module.py", "result": "sk-" + "z" * 40}]},
        )
    assert failure.value.code == "SENSITIVE_CONTENT"


def test_corrupt_notes_are_not_served_and_stale_cursors_are_rejected(
    tmp_path: Path, native_python: Path
) -> None:
    _root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    store = WorkMemoryStore(state, native_python)
    saved = store.execute(ctx, "save", payload())
    note_id = saved["note_id"]
    for cursor, code in (("not-a-cursor", "ARGUMENT_INVALID"), ("2:0", "REVISION_CONFLICT")):
        with pytest.raises(KnowledgeError) as failure:
            store.execute(ctx, "read", {"note_id": note_id, "cursor": cursor})
        assert failure.value.code == code
    with pytest.raises(KnowledgeError) as failure:
        store.execute(
            ctx, "correct", {"note_id": note_id, "expected_revision": 1, "replacement": "bad"}
        )
    assert failure.value.code == "ARGUMENT_INVALID"
    root = state / "knowledge" / PROJECT / "memory/implementer"
    note = root / "notes" / note_id / "1/note.md"
    note.write_text("tampered outside the recorded generation")
    for action, args in (("read", {"note_id": note_id}), ("reflect", {})):
        with pytest.raises(KnowledgeError) as failure:
            store.execute(ctx, action, args)
        assert failure.value.code == "MEMORY_CORRUPT"
    (root / "notes" / note_id / "1/record.json").write_text("[]")
    with pytest.raises(KnowledgeError) as failure:
        store.execute(ctx, "read", {"note_id": note_id})
    assert failure.value.code == "MEMORY_CORRUPT"
    (root / "index.json").write_text("[]")
    with pytest.raises(KnowledgeError) as failure:
        store.execute(ctx, "search", {"query": "sample"})
    assert failure.value.code == "MEMORY_CORRUPT"


def test_operator_cli_complete_note_and_binding_cycle(
    tmp_path: Path, native_python: Path, capsys
) -> None:
    _root, state = project(tmp_path)
    service = KnowledgeService(state, tmp_path / "cache")
    parser = _build_parser()

    def call(*arguments: str) -> tuple[int, dict]:
        code = run_knowledge(parser.parse_args(["knowledge", *arguments, "--json"]), service)
        return code, json.loads(capsys.readouterr().out)

    assert call("configure", "--python", str(native_python))[0] == 0
    assert call("doctor")[1]["component"]["version"] == "0.9.54"
    assert call("bind", "--project-id", PROJECT, "--session", "operator-session")[0] == 0
    assert call("status", "--project-id", PROJECT)[1]["available"] is False
    code, saved = call(
        "call",
        "--project-id",
        PROJECT,
        "--tool",
        "work_memory",
        "--arguments",
        json.dumps({"action": "save", **payload()}),
    )
    assert code == 0
    assert len(call("export", "--project-id", PROJECT)[1]["notes"]) == 1
    refused = call("delete", "--project-id", PROJECT, "--note-id", saved["note_id"])
    assert refused[0] == 1 and refused[1]["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert call("delete", "--project-id", PROJECT, "--note-id", saved["note_id"], "--yes")[0] == 0
    invalid = call("call", "--project-id", PROJECT, "--tool", "work_memory", "--arguments", "{")
    assert invalid[0] == 1 and invalid[1]["error"]["code"] == "ARGUMENT_INVALID"
    assert call("disable")[1]["enabled"] is False
    assert call("doctor")[0] == 1
