"""Native note rendering with project/role isolation, correction and retrieval."""

from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_project_knowledge_engine import OTHER, PROJECT, git_at, project

from aether_agents.knowledge.common import KnowledgeError, atomic_json
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.graphify import GraphifyBackend
from aether_agents.knowledge.memory import WorkMemoryStore
from aether_agents.knowledge.service import KnowledgeService, validate_arguments


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


def test_evidence_requires_regular_file_at_exact_commit(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    (root / "src").mkdir()
    (root / "src/nested.py").write_text("pass\n")
    (root / "literal[1].py").write_text("pass\n")
    (root / "executable.py").write_text("pass\n")
    (root / "alias.py").symlink_to("module.py")
    git_at(root, "add", ".")
    git_at(root, "update-index", "--chmod=+x", "executable.py")
    git_at(
        root,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{git_at(root, 'rev-parse', 'HEAD')},submodule",
    )
    git_at(root, "commit", "-qm", "evidence object classes")
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    store = WorkMemoryStore(state)
    expected = {
        "module.py": True,
        "src/nested.py": True,
        "executable.py": True,
        "literal[1].py": True,
        "src": False,
        "src/": False,
        "alias.py": False,
        "submodule": False,
        "missing.py": False,
        "module*.py": False,
        ":(glob)*": False,
        ".": False,
    }
    observed = store._evidence(ctx, [{"path": path} for path in expected])
    assert [item["source_exists"] for item in observed] == list(expected.values())
    assert all(item["revision"] == ctx.source_revision for item in observed)
    assert all(item["result_independently_verified"] is False for item in observed)

    tree = git_at(root, "rev-parse", "HEAD^{tree}")
    blob = git_at(root, "rev-parse", "HEAD:module.py")
    invalid = store._evidence(
        ctx, [{"path": "module.py", "revision": rev} for rev in ("0" * 40, tree, blob)]
    )
    assert all(item["source_exists"] is False for item in invalid)
    (root / "module.py").unlink()
    git_at(root, "add", "-u")
    git_at(root, "commit", "-qm", "remove evidence from later revision")
    current = resolve_context(PROJECT, "morfeo", state_root=state)
    refs = store._evidence(
        current, [{"path": "module.py"}, {"path": "module.py", "revision": ctx.source_revision}]
    )
    assert [item["source_exists"] for item in refs] == [False, True]


@pytest.mark.parametrize("field", ["reason", "applicability"])
@pytest.mark.parametrize("size", [4096, 4097, 5000, 16000, 16001])
def test_correction_accepts_advertised_lengths(memory, field: str, size: int) -> None:
    store, state = memory
    assert store.backend is not None
    service = KnowledgeService(state, state / "cache")
    atomic_json(
        service.config_path,
        {
            "schema_version": 1,
            "enabled": True,
            "python": str(store.backend.python),
        },
    )
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    first = service.execute(ctx, "work_memory", {"action": "save", **payload()})
    args = {
        "action": "correct",
        "note_id": first["note_id"],
        "expected_revision": 1,
        "reason": "Verified correction",
        "replacement": {
            "lesson": "Corrected lesson",
            "applicability": "Current sources",
        },
        "evidence": [],
    }
    text = "r" * size
    if field == "reason":
        args["reason"] = text
    else:
        args["replacement"]["applicability"] = text
    if size > 16000:
        with pytest.raises(KnowledgeError, match="schema"):
            validate_arguments("work_memory", args)
        with pytest.raises(KnowledgeError, match="16000"):
            store.execute(ctx, "correct", args)
        assert store.execute(ctx, "read", {"note_id": first["note_id"]})["revision"] == 1
        return
    assert validate_arguments("work_memory", args) == "correct"
    assert service.execute(ctx, "work_memory", args)["revision"] == 2
    note = store.execute(ctx, "export", {})["notes"][0]
    assert note["correction_reason" if field == "reason" else field] == text
    assert (
        service.execute(ctx, "work_memory", {"action": "read", "note_id": first["note_id"]})[
            "revision"
        ]
        == 2
    )


def test_maximum_unicode_correction_is_readable(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    first = store.execute(ctx, "save", payload())
    text = "🌌" * 16000
    args = {
        "action": "correct",
        "note_id": first["note_id"],
        "expected_revision": 1,
        "reason": text,
        "replacement": {"lesson": text, "applicability": text},
        "evidence": [],
    }
    assert validate_arguments("work_memory", args) == "correct"
    assert store.execute(ctx, "correct", args)["revision"] == 2
    note = store.execute(ctx, "export", {})["notes"][0]
    assert all(note[field] == text for field in ("lesson", "applicability", "correction_reason"))
    page = store.execute(ctx, "read", {"note_id": first["note_id"]})
    content = page["content"]
    while page["next_cursor"]:
        page = store.execute(
            ctx, "read", {"note_id": first["note_id"], "cursor": page["next_cursor"]}
        )
        content += page["content"]
    assert text in content


def test_save_keeps_its_smaller_applicability_limit(memory) -> None:
    store, state = memory
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    args = {"action": "save", **payload(), "applicability": "s" * 4097}
    with pytest.raises(KnowledgeError):
        validate_arguments("work_memory", args)
    with pytest.raises(KnowledgeError, match="4096"):
        store.execute(ctx, "save", args)


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


@pytest.fixture
def memory_store(tmp_path: Path):
    _root, state = project(tmp_path)
    return WorkMemoryStore(state, backend=FakeGraphify()), state


def test_sensitive_notes_and_escaping_evidence_are_rejected(memory_store) -> None:
    store, state = memory_store
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    with pytest.raises(KnowledgeError) as denied:
        store.execute(ctx, "save", payload("sk-" + "a" * 32))
    assert denied.value.code == "SENSITIVE_CONTENT"
    data = payload()
    data["evidence"] = [{"path": "../other/secret.py"}]
    with pytest.raises(KnowledgeError):
        store.execute(ctx, "save", data)


@pytest.mark.parametrize(
    "credential_fixture",
    [
        # Demonstrated password assignment shapes
        "pass" + "word = 'synthetic_fake_password_123'",
        "pass" + "wd: synthetic_secret_456",
        "PASS" + 'WORD="synthetic_secret_789"',
        '"pass' + 'word": "synthetic_json_pass_123"',
        # Demonstrated GitHub token prefixes
        "ghp_" + "a" * 36,
        "gho_" + "b" * 36,
        "ghu_" + "c" * 36,
        "ghs_" + "d" * 36,
        "ghr_" + "e" * 36,
        "github_pat_" + "f" * 40,
        # Demonstrated Bearer authorization values
        "Authorization" + ": Bearer synthetic_bearer_token_123",
        "Bearer " + "synthetic_bearer_token_4567890",
    ],
)
def test_demonstrated_credential_shapes_are_rejected_in_note_text(
    memory_store, credential_fixture: str
) -> None:
    store, state = memory_store
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    # Test lesson field
    with pytest.raises(KnowledgeError) as denied:
        store.execute(ctx, "save", payload(credential_fixture))
    assert denied.value.code == "SENSITIVE_CONTENT"

    # Test situation field
    data = payload()
    data["situation"] = credential_fixture
    with pytest.raises(KnowledgeError) as denied_sit:
        store.execute(ctx, "save", data)
    assert denied_sit.value.code == "SENSITIVE_CONTENT"

    # Test applicability field
    data2 = payload()
    data2["applicability"] = credential_fixture
    with pytest.raises(KnowledgeError) as denied_app:
        store.execute(ctx, "save", data2)
    assert denied_app.value.code == "SENSITIVE_CONTENT"


@pytest.mark.parametrize(
    "credential_fixture",
    [
        "pass" + "word=synthetic_evidence_pass_123",
        "pass" + "wd: synthetic_locator_pass_456",
        "ghp_" + "z" * 36,
        "github_pat_" + "z" * 40,
        "Bearer " + "synthetic_bearer_token_evidence_999",
        "Authorization" + ": Bearer synthetic_bearer_locator_888",
    ],
)
def test_demonstrated_credential_shapes_are_rejected_in_evidence(
    memory_store, credential_fixture: str
) -> None:
    store, state = memory_store
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    # Test in result field
    data_res = payload()
    data_res["evidence"] = [{"path": "module.py", "result": credential_fixture}]
    with pytest.raises(KnowledgeError) as denied_res:
        store.execute(ctx, "save", data_res)
    assert denied_res.value.code == "SENSITIVE_CONTENT"

    # Test in locator field
    data_loc = payload()
    data_loc["evidence"] = [{"path": "module.py", "locator": credential_fixture}]
    with pytest.raises(KnowledgeError) as denied_loc:
        store.execute(ctx, "save", data_loc)
    assert denied_loc.value.code == "SENSITIVE_CONTENT"


@pytest.mark.parametrize(
    "benign_text",
    [
        "Investigated password reset flow and confirmed argon2id hashing is used.",
        "Password policy documentation requires 12 characters minimum.",
        "GitHub token prefixes (ghp_ / gho_ / ghu_ / ghs_ / ghr_ / github_pat_) should be documented.",
        "Documented the ghp_ personal access token prefix.",
        "The API implements Bearer authentication according to RFC 6750.",
        "We verified that Bearer authorization is enforced by middleware.",
        "The bearer of this security token must be authorized.",
        "Bearer bonds were issued in 1920.",
    ],
)
def test_benign_prose_and_token_prefix_documentation_are_preserved(
    memory_store, benign_text: str
) -> None:
    store, state = memory_store
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    saved = store.execute(ctx, "save", payload(benign_text))
    assert saved["note_id"].startswith("wn_")


class FakeGraphify(GraphifyBackend):
    def __init__(self, python: Path | None = None):
        super().__init__(python or Path("/dev/null"))

    def run(
        self,
        action: str,
        *,
        source_root: Path | None = None,
        graph_path: Path | None = None,
        arguments: dict | None = None,
        timeout: float | None = None,
    ) -> dict:
        if action == "memory_save":
            assert arguments is not None
            return {
                "content": f"# Work Note\n\n## Situation\n{arguments['situation']}\n\n## Lesson\n{arguments['lesson']}\n"
            }
        if action == "memory_reflect":
            assert arguments is not None
            return {
                "content": "Aggregated reflections.",
                "count": len(arguments.get("notes", [])),
            }
        raise NotImplementedError(action)


def test_untracked_source_changes_mark_freshness_dirty(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    store = WorkMemoryStore(state, backend=FakeGraphify())
    note = store.execute(ctx, "save", payload("Freshness tracking lesson."))
    note_id = note["note_id"]

    read_clean = store.execute(ctx, "read", {"note_id": note_id})
    assert read_clean["freshness"] == "same_revision"
    search_clean = store.execute(ctx, "search", {"query": "Freshness"})
    assert search_clean["matches"][0]["freshness"] == "same_revision"

    untracked = root / "untracked_script.py"
    untracked.write_text("print('untracked')\n")

    read_dirty = store.execute(ctx, "read", {"note_id": note_id})
    assert read_dirty["freshness"] == "revalidate"
    search_dirty = store.execute(ctx, "search", {"query": "Freshness"})
    assert search_dirty["matches"][0]["freshness"] == "revalidate"

    untracked.unlink()
    read_restored = store.execute(ctx, "read", {"note_id": note_id})
    assert read_restored["freshness"] == "same_revision"


def test_reflection_validates_notes_and_hashes_before_cache_reuse(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    store = WorkMemoryStore(state, backend=FakeGraphify())
    saved = store.execute(ctx, "save", payload("Reflection validation lesson."))
    note_id = saved["note_id"]

    first = store.execute(ctx, "reflect", {})
    assert first["reused"] is False
    assert first["count"] == 1

    second = store.execute(ctx, "reflect", {})
    assert second["reused"] is True

    # Tamper with markdown on disk after cache is populated
    note_md = state / "knowledge" / PROJECT / "memory/implementer/notes" / note_id / "1/note.md"
    note_md.write_text("Tampered markdown content.")

    with pytest.raises(KnowledgeError) as failure:
        store.execute(ctx, "reflect", {})
    assert failure.value.code == "MEMORY_CORRUPT"


def test_search_validates_note_hashes(tmp_path: Path) -> None:
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "implementer", state_root=state)
    store = WorkMemoryStore(state, backend=FakeGraphify())
    saved = store.execute(ctx, "save", payload("Search hash validation lesson."))
    note_id = saved["note_id"]

    results = store.execute(ctx, "search", {"query": "Search"})
    assert len(results["matches"]) == 1

    note_md = state / "knowledge" / PROJECT / "memory/implementer/notes" / note_id / "1/note.md"
    note_md.write_text("Tampered markdown content.")

    with pytest.raises(KnowledgeError) as failure:
        store.execute(ctx, "search", {"query": "Search"})
    assert failure.value.code == "MEMORY_CORRUPT"
