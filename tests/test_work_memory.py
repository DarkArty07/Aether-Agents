"""Native note rendering with project/role isolation, correction and retrieval."""

from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_project_knowledge_engine import OTHER, PROJECT, project

from aether_agents.knowledge.common import KnowledgeError
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.memory import WorkMemoryStore


@pytest.fixture
def memory(tmp_path: Path):
    raw = os.environ.get("AETHER_GRAPHIFY_PYTHON")
    if not raw:
        pytest.skip("Set AETHER_GRAPHIFY_PYTHON for native Graphify memory verification")
    _root, state = project(tmp_path)
    return WorkMemoryStore(state, Path(raw)), state


def payload(lesson: str = "Use the committed source revision.", *, key: str | None = None) -> dict:
    save_key = key or "test-save-" + hashlib.sha256(lesson.encode()).hexdigest()[:16]
    return {
        "idempotency_key": save_key,
        "situation": "Which revision is indexed?",
        "lesson": lesson,
        "applicability": "When checking project knowledge.",
        "outcome": "useful",
        "evidence": [],
        "source_nodes": ["process_order"],
    }


def test_roles_share_no_personal_notes_or_reflections(memory, tmp_path: Path) -> None:
    store, state = memory
    contexts = {
        role: resolve_context(PROJECT, role, state_root=state)
        for role in ("morfeo", "supervisor", "implementer")
    }
    ids = {}
    for role, ctx in contexts.items():
        ids[role] = store.execute(ctx, "save", payload(f"{role}_private_canary"))["note_id"]
    for role, ctx in contexts.items():
        response = store.execute(ctx, "read", {"note_id": ids[role]})
        assert f"{role}_private_canary" in response["content"]
        assert response["verification"] == "reported"
        for other in contexts:
            matches = store.execute(ctx, "search", {"query": f"{other}_private_canary"})["matches"]
            assert bool(matches) == (other == role)
        store.execute(ctx, "reflect", {})
    assert not list(tmp_path.rglob(".graphify_learning.json"))


def test_full_answer_recovered_and_corrections_do_not_inflate_reflection(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    first = store.execute(ctx, "save", payload("ORIGINAL_FULL_TECHNICAL_ANSWER"))
    assert (
        "ORIGINAL_FULL_TECHNICAL_ANSWER"
        in store.execute(ctx, "read", {"note_id": first["note_id"]})["content"]
    )
    replacement = {
        "note_id": first["note_id"],
        "expected_revision": 1,
        "reason": "A verified correction",
        "replacement": {
            "lesson": "CORRECTED_TECHNICAL_ANSWER",
            "applicability": "Current revision only",
        },
        "evidence": [],
    }
    changed = store.execute(ctx, "correct", replacement)
    assert changed["revision"] == 2
    with pytest.raises(KnowledgeError) as conflict:
        store.execute(ctx, "correct", replacement)
    assert conflict.value.code == "REVISION_CONFLICT"
    read = store.execute(ctx, "read", {"note_id": first["note_id"]})
    assert "CORRECTED_TECHNICAL_ANSWER" in read["content"]
    assert "ORIGINAL_FULL_TECHNICAL_ANSWER" not in read["content"]
    assert store.execute(ctx, "reflect", {})["count"] == 1


def test_pagination_and_foreign_project_isolation(memory, tmp_path: Path) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    text = "Long experience with Unicode áéí. " * 390
    note = store.execute(ctx, "save", payload(text))
    page = store.execute(ctx, "read", {"note_id": note["note_id"]})
    content = page["content"]
    while page["next_cursor"]:
        page = store.execute(
            ctx, "read", {"note_id": note["note_id"], "cursor": page["next_cursor"]}
        )
        content += page["content"]
    assert text.strip() in content
    assert content.count("Long experience with Unicode áéí.") == 390
    project(tmp_path, OTHER, "other")
    other = resolve_context(OTHER, "implementer", state_root=state)
    assert store.execute(other, "search", {"query": "Unicode"})["matches"] == []
    with pytest.raises(KnowledgeError):
        store.execute(other, "read", {"note_id": note["note_id"]})


def test_save_retry_is_idempotent_across_store_restart(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    data = payload("A retry must reuse the original note.", key="retry-across-restart")

    first = store.execute(ctx, "save", data)
    restarted = WorkMemoryStore(state, Path(os.environ["AETHER_GRAPHIFY_PYTHON"]))
    replay = restarted.execute(ctx, "save", data)

    assert first["idempotent_replay"] is False
    assert replay["idempotent_replay"] is True
    assert replay["note_id"] == first["note_id"]
    assert replay["revision"] == first["revision"] == 1
    assert len(restarted.execute(ctx, "export", {})["notes"]) == 1


def test_parallel_retries_publish_one_note(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    data = payload("Concurrent retries share one operation.", key="parallel-retry-operation")

    with ThreadPoolExecutor(max_workers=4) as pool:
        saved = list(pool.map(lambda _index: store.execute(ctx, "save", data), range(12)))

    assert len({note["note_id"] for note in saved}) == 1
    assert sum(not note["idempotent_replay"] for note in saved) == 1
    assert len(store.execute(ctx, "export", {})["notes"]) == 1


def test_reused_key_conflicts_but_distinct_keys_preserve_equal_contributions(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    first = store.execute(ctx, "save", payload("Same lesson.", key="independent-operation-a"))

    with pytest.raises(KnowledgeError) as conflict:
        store.execute(ctx, "save", payload("Changed lesson.", key="independent-operation-a"))
    assert conflict.value.code == "IDEMPOTENCY_CONFLICT"

    second = store.execute(ctx, "save", payload("Same lesson.", key="independent-operation-b"))
    assert first["note_id"] != second["note_id"]
    assert len(store.execute(ctx, "export", {})["notes"]) == 2


def test_save_retry_tracks_the_current_corrected_revision(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    original = payload("Original answer.", key="corrected-save-operation")
    saved = store.execute(ctx, "save", original)
    store.execute(
        ctx,
        "correct",
        {
            "note_id": saved["note_id"],
            "expected_revision": 1,
            "reason": "The verified behavior changed.",
            "replacement": {
                "lesson": "Corrected answer.",
                "applicability": "Current revision only.",
            },
            "evidence": [],
        },
    )

    replay = store.execute(ctx, "save", original)
    assert replay["idempotent_replay"] is True
    assert replay["note_id"] == saved["note_id"]
    assert replay["revision"] == 2
    assert len(store.execute(ctx, "export", {})["notes"]) == 1


def test_parallel_implementer_notes_are_all_retained(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    with ThreadPoolExecutor(max_workers=4) as pool:
        saved = list(
            pool.map(
                lambda i: store.execute(ctx, "save", payload(f"Experience number {i}")), range(12)
            )
        )
    assert len({note["note_id"] for note in saved}) == 12
    assert len(store.execute(ctx, "export", {})["notes"]) == 12


def test_delete_invalidates_reflection_and_removes_history(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "supervisor", state_root=state)
    saved = store.execute(ctx, "save", payload())
    assert store.execute(ctx, "reflect", {})["count"] == 1
    store.execute(ctx, "delete", {"note_id": saved["note_id"]})
    assert store.execute(ctx, "reflect", {})["count"] == 0
    assert store.execute(ctx, "export", {})["notes"] == []
    assert not list(state.rglob(saved["note_id"]))


def test_sensitive_notes_and_escaping_evidence_are_rejected(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    with pytest.raises(KnowledgeError) as denied:
        store.execute(ctx, "save", payload("sk-" + "a" * 32))
    assert denied.value.code == "SENSITIVE_CONTENT"
    data = payload()
    data["evidence"] = [{"path": "../other/secret.py"}]
    with pytest.raises(KnowledgeError):
        store.execute(ctx, "save", data)
