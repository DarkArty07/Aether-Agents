"""SK-04 manager executor: bounded plan, total budget, cancel, route gate, accounting.

These are deterministic checks of `aether_agents.knowledge.semantic` against a
bounded worker stand-in: no live auxiliary call and no native Graphify component
is required. The compose protocol consumed here is the one stamped in the SK-01
card (`semantic_compose` with a `fragments` list); the stand-in only records it.
"""

from __future__ import annotations

import concurrent.futures
import contextvars
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from test_project_knowledge_engine import PROJECT, project

from aether_agents.knowledge.common import KnowledgeError
from aether_agents.knowledge.context import resolve_context

CONFIGURED = {
    "semantic_auxiliary_task": "web_extract",
    "semantic": {
        "provider": "openrouter",
        "model": "stub-primary-model",
        "api_mode": "chat_completions",
    },
}
ACTUAL_ROUTE = {
    "provider": "openrouter",
    "model": "stub-primary-model",
    "api_mode": "chat_completions",
}


def _fragment_json(marker: str, source_file: str, target: str = "module_process_order") -> str:
    return json.dumps(
        {
            "nodes": [
                {
                    "id": f"Node{marker}",
                    "label": f"Node {marker}",
                    "source_file": source_file,
                    "source_location": "1",
                }
            ],
            "edges": [{"source": f"Node{marker}", "target": target, "relation": "specifies"}],
        }
    )


def _chunk(cid: int, files: list[str]) -> dict[str, Any]:
    """A prepared chunk whose prompt bodies carry an identifying marker."""
    return {
        "chunk_id": cid,
        "files": list(files),
        "system_prompt": f"system-marker-{cid}",
        "user_prompt": f"user-marker-{cid} SECRET-PROMPT-CONTENT-{cid}",
    }


class _StubBackend:
    """Bounded worker stand-in implementing prepare/validate/compose only."""

    def __init__(
        self,
        chunks: list[dict[str, Any]] | None = None,
        *,
        validate=None,
        compose=None,
        prepare=None,
    ) -> None:
        self.python = Path("stub-component-python")
        self.calls: list[dict[str, Any]] = []
        self._chunks = list(chunks or [])
        self._validate = validate
        self._compose = compose
        self._prepare = prepare
        self.lock = threading.Lock()

    def action_calls(self, action: str) -> list[dict[str, Any]]:
        return [call for call in self.calls if call["action"] == action]

    def run(
        self,
        action: str,
        *,
        source_root: Path | None = None,
        graph_path: Path | None = None,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        record = {
            "action": action,
            "arguments": dict(arguments or {}),
            "timeout": timeout,
            "cancel_event": cancel_event,
            "graph_path": graph_path,
        }
        with self.lock:
            self.calls.append(record)
        if action == "semantic_prepare":
            if self._prepare is not None:
                return self._prepare(record["arguments"])
            return {
                "ok": True,
                "chunks": self._chunks,
                "total_chunks": len(self._chunks),
                "has_more": False,
            }
        if action == "semantic_validate":
            model_text = str(record["arguments"].get("model_text") or "")
            if self._validate is not None:
                return self._validate(model_text, record["arguments"])
            return {"ok": True, "fragment": _strict_fragment(model_text)}
        if action == "semantic_compose":
            fragments = list(record["arguments"].get("fragments") or [])
            if self._compose is not None:
                return self._compose(record["arguments"])
            return {
                "ok": True,
                "content": f"composed {len(fragments)} fragments",
                "applied_nodes": len(fragments),
                "structural_digest": "stub-structural-digest",
                "structural_preserved": True,
            }
        raise AssertionError(f"unexpected worker action: {action}")


def _strict_fragment(model_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(model_text)
    except ValueError as exc:
        raise KnowledgeError(
            "INDEX_CORRUPT", f"Malformed model text: failed to parse JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict) or (not parsed.get("nodes") and not parsed.get("edges")):
        raise KnowledgeError(
            "INDEX_CORRUPT", "Hollow model fragment: both nodes and edges are empty."
        )
    return parsed


class _Aux:
    """Scripted auxiliary transport with recorded calls and a controllable clock."""

    def __init__(self, responses, *, clock: list[float] | None = None) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []
        self.clock = clock
        self.lock = threading.Lock()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        with self.lock:
            index = len(self.calls)
            self.calls.append({"args": args, "kwargs": kwargs})
        response = self._responses[min(index, len(self._responses) - 1)]
        if callable(response):
            return response(len(self.calls) - 1)
        return response


def _text_usage(text: str, *, total: int = 100, meta: dict[str, Any] | None = None):
    usage: dict[str, Any] = {
        "prompt_tokens": total,
        "completion_tokens": 0,
        "total_tokens": total,
        "route": dict(ACTUAL_ROUTE),
    }
    return (text, usage, dict(meta or {}))


def _semantic_module():
    import aether_agents.knowledge.semantic as sem_mod

    return sem_mod


def _cache_dir(cache_root: Path) -> Path:
    return cache_root / "knowledge" / PROJECT / "semantic_cache"


def _plan_dir(cache_root: Path) -> Path:
    return cache_root / "knowledge" / PROJECT / "semantic_plans"


def _graph_file(root: Path) -> Path:
    target = root / "graphify-out" / "graph.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        target.write_text(
            json.dumps({"nodes": [], "edges": [], "directed": True}), encoding="utf-8"
        )
    return target


def _inputs(files: list[str]) -> dict[str, str]:
    return {name: hashlib.sha256(name.encode()).hexdigest() for name in files}


def test_unresolved_route_is_rejected_without_cache_or_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unresolved effective route neither calls the model nor mutates anything."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    backend = _StubBackend([_chunk(0, ["README.md"])])
    aux = _Aux([_text_usage(_fragment_json("A", "README.md"))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)

    graph_path = _graph_file(root)
    before = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    cache_root = tmp_path / "cache"

    result = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=_inputs(["README.md"]),
        cache_root=cache_root,
        ctx=ctx,
        configuration={
            "semantic_auxiliary_task": "web_extract",
            "semantic": {"provider": "unresolved", "model": "unresolved", "api_mode": "unresolved"},
        },
    )

    assert aux.calls == []
    assert backend.action_calls("semantic_compose") == []
    assert list(_cache_dir(cache_root).glob("*.json")) == []
    assert result["observed_usage"]["model_calls"] == 0
    assert result["observed_usage"]["categories"]["route"] > 0
    assert result["state"] in ("pending", "unavailable")
    assert result["structural_preserved"] is None
    assert hashlib.sha256(graph_path.read_bytes()).hexdigest() == before


def test_mismatched_route_is_not_cached_or_composed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A response from a different effective route is rejected, not composed."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    backend = _StubBackend([_chunk(0, ["README.md"])])

    def mismatched(*args: Any, **kwargs: Any) -> Any:
        route_info = kwargs.get("route_info")
        if isinstance(route_info, dict):
            route_info.update(
                {"provider": "other", "model": "other", "api_mode": "chat_completions"}
            )
        return _text_usage(_fragment_json("B", "README.md"))

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", mismatched)
    graph_path = _graph_file(root)
    before = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    cache_root = tmp_path / "cache"

    result = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=_inputs(["README.md"]),
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )

    assert result["observed_usage"]["model_calls"] == 1
    assert result["observed_usage"]["categories"]["route"] == 1
    assert list(_cache_dir(cache_root).glob("*.json")) == []
    assert backend.action_calls("semantic_compose") == []
    assert result["state"] != "complete"
    assert hashlib.sha256(graph_path.read_bytes()).hexdigest() == before


def test_deadline_zero_returns_honest_pending_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """deadline_seconds=0 schedules nothing, composes nothing, and keeps the cache."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend = _StubBackend(chunks)
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"N{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py"])

    first = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
        deadline_seconds=300.0,
    )
    assert first["state"] == "complete"
    assert len(backend.action_calls("semantic_compose")) == 1
    cached_files = sorted(p.name for p in _cache_dir(cache_root).glob("*.json"))
    assert len(cached_files) == 2

    calls_after_first = len(aux.calls)
    deadline_run = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED | {"semantic_deadline_seconds": 0.0},
    )

    assert len(aux.calls) == calls_after_first, "no new model call after the budget expired"
    assert deadline_run["observed_usage"]["model_calls"] == 0
    assert len(backend.action_calls("semantic_compose")) == 1, (
        "compose must not start after the deadline"
    )
    assert deadline_run["state"] in ("pending", "partial")
    assert deadline_run["covered_paths"] == []
    assert sorted(deadline_run["pending_paths"]) == ["README.md", "module.py"]
    assert deadline_run["observed_usage"]["chunk_counts"]["cached"] == 2
    assert deadline_run["observed_usage"]["categories"]["deadline"] > 0
    assert deadline_run["pipeline"]["deadline_exhausted"] is True
    assert sorted(p.name for p in _cache_dir(cache_root).glob("*.json")) == cached_files


def test_deadline_firing_before_compose_stops_new_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A budget that expires while a chunk is in flight stops scheduling and composition."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend = _StubBackend(chunks)

    clock = [sem_mod._now()] if hasattr(sem_mod, "_now") else [time.monotonic()]
    monkeypatch.setattr(sem_mod, "_now", lambda: clock[0], raising=False)

    def aux(*args: Any, **kwargs: Any) -> Any:
        clock[0] += 10_000.0  # fire the total deadline while this chunk is in flight
        return _text_usage(_fragment_json("late", "README.md"))

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"

    result = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=_inputs(["README.md", "module.py"]),
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )

    assert result["observed_usage"]["model_calls"] == 1, "no chunk starts after the deadline fired"
    assert result["observed_usage"]["categories"]["deadline"] > 0
    assert backend.action_calls("semantic_compose") == []
    assert result["state"] in ("pending", "partial")
    assert result["pipeline"]["budget_seconds"] == 300.0
    assert result["pipeline"]["deadline_exhausted"] is True


def test_cancel_stops_scheduling_retains_cache_and_never_composes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host cancel stops scheduling, keeps the validated cache and never composes."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend = _StubBackend(chunks)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py"])
    pre_cancelled = threading.Event()
    pre_cancelled.set()

    with pytest.raises(KnowledgeError) as excinfo:
        sem_mod.run_semantic_extraction(
            backend=backend,
            source_root=root,
            graph_path=graph_path,
            inputs=inputs,
            cache_root=cache_root,
            ctx=ctx,
            configuration=CONFIGURED,
            cancel_event=pre_cancelled,
        )
    assert excinfo.value.code == "OPERATION_CANCELLED"
    assert backend.calls == [], "an already-cancelled run schedules nothing"

    # Validated work from a completed run survives a later cancelled run.
    aux_ok = _Aux(
        [lambda index: _text_usage(_fragment_json(f"K{index}", chunks[index]["files"][0]))]
    )
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux_ok)
    completed = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert completed["state"] == "complete"
    cached_before = sorted(p.name for p in _cache_dir(cache_root).glob("*.json"))
    assert len(cached_before) == 2

    cancel_event = threading.Event()
    inflight: list[str] = []

    def cancelling_aux(*args: Any, **kwargs: Any) -> Any:
        from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]
            _aux_interrupt_cancel_requested,
        )

        inflight.append(str(kwargs.get("user_prompt")))
        assert _aux_interrupt_cancel_requested() is False, (
            "the transport sees the shared cancel event before it fires"
        )
        cancel_event.set()  # the host cancels while this chunk is in flight
        assert _aux_interrupt_cancel_requested() is True, (
            "an in-flight call is cancellable through the existing transport hook"
        )
        from agent.auxiliary_client import AuxiliaryExplicitCancellation

        raise AuxiliaryExplicitCancellation()

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", cancelling_aux)
    new_chunk = _chunk(0, ["docs/extra.md"])
    cancelled_backend = _StubBackend([new_chunk])
    cancel_inputs = _inputs(["docs/extra.md"])

    with pytest.raises(KnowledgeError) as cancel_info:
        sem_mod.run_semantic_extraction(
            backend=cancelled_backend,
            source_root=root,
            graph_path=graph_path,
            inputs=cancel_inputs,
            cache_root=cache_root,
            ctx=ctx,
            configuration=CONFIGURED,
            cancel_event=cancel_event,
        )
    assert cancel_info.value.code == "OPERATION_CANCELLED"
    assert len(cancelled_backend.calls) == 1, "exactly the in-flight chunk was scheduled"
    assert cancelled_backend.action_calls("semantic_compose") == []
    assert sorted(p.name for p in _cache_dir(cache_root).glob("*.json")) == cached_before, (
        "validated cache is retained across the cancelled run"
    )
    assert inflight == ["user-marker-0 SECRET-PROMPT-CONTENT-0"], (
        "the in-flight auxiliary call observed the shared cancel event"
    )


def test_plan_is_bounded_persisted_and_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One plan per compatible revision/policy, content-free, reused on retry."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend = _StubBackend(chunks)
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"P{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py"])

    first = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert first["state"] == "complete"
    assert first["pipeline"]["plan_reused"] is False
    assert first["pipeline"]["plan_persisted"] is True
    plan_files = sorted(_plan_dir(cache_root).glob("*.json"))
    assert len(plan_files) == 1

    plan_bytes = plan_files[0].read_text(encoding="utf-8")
    plan = json.loads(plan_bytes)
    for marker in ("SECRET-PROMPT-CONTENT-0", "SECRET-PROMPT-CONTENT-1", "system-marker-0"):
        assert marker not in plan_bytes, "plan records stay size/path bounded, never content"
    assert plan["pipeline_version"] == first["pipeline"]["version"]
    assert plan["cache_version"] == first["pipeline"]["cache_version"]
    assert plan["policy"] == {"deep": False, "token_budget": 4000}
    assert plan["structural_base"]["digest"], "structural-base reference is persisted"
    assert [record["files"] for record in plan["chunks"]] == [["README.md"], ["module.py"]]
    assert plan["plan_id"] == first["pipeline"]["plan_id"]

    prepare_calls_before = len(backend.action_calls("semantic_prepare"))
    second = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert second["pipeline"]["plan_reused"] is True
    assert second["observed_usage"]["model_calls"] == 0
    assert second["state"] == "complete"
    assert len(backend.action_calls("semantic_prepare")) == prepare_calls_before, (
        "a compatible plan is reused instead of repacking the corpus"
    )
    assert len(list(_plan_dir(cache_root).glob("*.json"))) == 1


def test_plan_compatible_partial_retry_makes_no_repeat_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A compatible retry reuses plan, structural base and cache; only pending work runs."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend = _StubBackend(chunks)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py"])

    def flaky(*args: Any, **kwargs: Any) -> Any:
        user_prompt = str(kwargs.get("user_prompt") or "")
        if "SECRET-PROMPT-CONTENT-1" in user_prompt:
            raise KnowledgeError("AUXILIARY_FAILED", "stub transport failure")
        return _text_usage(_fragment_json("A", "README.md"))

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", flaky)
    first = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert first["state"] == "partial"
    assert first["observed_usage"]["chunk_counts"]["cached"] == 0
    assert first["observed_usage"]["chunk_counts"]["validated"] == 1
    assert first["observed_usage"]["chunk_counts"]["failed"] == 1

    retry_calls = _Aux([lambda index: _text_usage(_fragment_json("B", "module.py"))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", retry_calls)
    prepare_before = len(backend.action_calls("semantic_prepare"))
    second = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )

    assert second["pipeline"]["plan_reused"] is True
    assert len(retry_calls.calls) == 1, "already accepted chunks add no model calls"
    assert second["observed_usage"]["chunk_counts"]["cached"] == 1
    assert second["state"] == "complete"
    assert len(backend.action_calls("semantic_prepare")) - prepare_before == 1, (
        "only the pending chunk is reprepared"
    )


def test_compose_is_invoked_once_with_all_accepted_fragments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N accepted fragments produce exactly one semantic_compose call, never semantic_apply."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [
        _chunk(0, ["README.md"]),
        _chunk(1, ["module.py"]),
        _chunk(2, ["docs/guide.md"]),
    ]
    backend = _StubBackend(chunks)
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"C{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py", "docs/guide.md"])

    first = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert first["state"] == "complete"

    compose_before = len(backend.action_calls("semantic_compose"))
    calls_before = len(aux.calls)
    second = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )

    assert len(aux.calls) == calls_before, "cache hits add no calls"
    compose_calls = backend.action_calls("semantic_compose")
    assert len(compose_calls) - compose_before == 1
    fragments = compose_calls[-1]["arguments"]["fragments"]
    assert len(fragments) == 3, "one compose call carries every accepted fragment"
    assert second["validated_chunk_ids"] == [0, 1, 2]
    assert second["compose"]["invoked"] is True
    assert second["compose"]["structural_preserved"] is True
    assert second["structural_digest"] == "stub-structural-digest"
    assert all(call["action"] != "semantic_apply" for call in backend.calls)


def test_compose_failure_is_category_apply_and_bounds_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed composition is reported as `apply`, never as complete coverage."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"])]
    backend = _StubBackend(chunks)

    def compose(arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": False,
            "error": "structural projection mismatch",
            "structural_preserved": False,
        }

    backend._compose = compose  # noqa: SLF001 - deterministic failure injection
    aux = _Aux([_text_usage(_fragment_json("D", "README.md"))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"

    result = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=_inputs(["README.md"]),
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )

    assert result["state"] != "complete"
    assert result["observed_usage"]["categories"]["apply"] == 1
    assert result["compose"]["invoked"] is True
    assert result["compose"]["structural_preserved"] is False
    assert result["covered_paths"] == []
    assert len(list(_cache_dir(cache_root).glob("*.json"))) == 1, "validated cache is retained"


def test_response_metadata_matrix_never_parses_incomplete_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Incomplete/cancelled/filtered/empty responses never enter the cache or the graph."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    good = _fragment_json("G", "README.md")

    cases = {
        "length": _text_usage(good, meta={"finish_reason": "length"}),
        "content_filter": _text_usage(
            good, meta={"status": "incomplete", "incomplete_reason": "content_filter"}
        ),
        "cancelled": _text_usage(good, meta={"status": "cancelled"}),
        "empty": _text_usage("", meta={"finish_reason": "stop"}),
        "commentary": _text_usage(good, meta={"phase": "commentary"}),
        "malformed": _text_usage("{not json", meta={"finish_reason": "stop"}),
        "tool_call": _text_usage(
            "",
            meta={"finish_reason": "tool_calls", "tool_calls": [{"name": "submit_graph_fragment"}]},
        ),
    }

    for name, response in cases.items():
        cache_root = tmp_path / f"cache-{name}"
        backend = _StubBackend([_chunk(0, ["README.md"])])
        monkeypatch.setattr(sem_mod, "_call_auxiliary_model", _Aux([response]))
        result = sem_mod.run_semantic_extraction(
            backend=backend,
            source_root=root,
            graph_path=_graph_file(root),
            inputs=_inputs(["README.md"]),
            cache_root=cache_root,
            ctx=ctx,
            configuration=CONFIGURED,
        )
        assert result["state"] != "complete", name
        assert result["validated_chunk_ids"] == [], name
        assert result["covered_paths"] == [], name
        assert list(_cache_dir(cache_root).glob("*.json")) == [], name
        assert backend.action_calls("semantic_compose") == [], name
        categories = result["observed_usage"]["categories"]
        if name in ("length", "content_filter", "cancelled", "commentary", "tool_call"):
            assert categories["incomplete"] == 1, name
        elif name == "empty":
            assert categories["empty"] == 1, name
        else:
            assert categories["malformed_json"] == 1, name

    # A complete final answer still validates, caches and composes exactly once.
    cache_root = tmp_path / "cache-complete"
    backend = _StubBackend([_chunk(0, ["README.md"])])
    monkeypatch.setattr(
        sem_mod, "_call_auxiliary_model", _Aux([_text_usage(good, meta={"finish_reason": "stop"})])
    )
    complete = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=_graph_file(root),
        inputs=_inputs(["README.md"]),
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert complete["state"] == "complete"
    assert complete["validated_chunk_ids"] == [0]
    assert len(list(_cache_dir(cache_root).glob("*.json"))) == 1

    # Output-text fallback and the dormant structured-call hook are consumed, not guessed.
    fallback_meta = {"finish_reason": "stop", "output_text_used": True, "phase": "commentary"}
    backend = _StubBackend([_chunk(0, ["README.md"])])
    monkeypatch.setattr(
        sem_mod, "_call_auxiliary_model", _Aux([_text_usage(good, meta=fallback_meta)])
    )
    fallback = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=_graph_file(root),
        inputs=_inputs(["README.md"]),
        cache_root=tmp_path / "cache-fallback",
        ctx=ctx,
        configuration=CONFIGURED,
    )
    assert fallback["state"] == "complete", "output-text fallback remains eligible"

    structured = _text_usage(
        "",
        meta={
            "finish_reason": "tool_calls",
            "tool_calls": [{"name": "submit_graph_fragment", "arguments": good}],
        },
    )
    backend = _StubBackend([_chunk(0, ["README.md"])])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", _Aux([structured]))
    dormant = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=_graph_file(root),
        inputs=_inputs(["README.md"]),
        cache_root=tmp_path / "cache-structured-off",
        ctx=ctx,
        configuration=CONFIGURED,
        structured_call_enabled=False,
    )
    assert dormant["state"] != "complete", "the structured-call contingency is off by default"

    backend = _StubBackend([_chunk(0, ["README.md"])])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", _Aux([structured]))
    proven = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=_graph_file(root),
        inputs=_inputs(["README.md"]),
        cache_root=tmp_path / "cache-structured-on",
        ctx=ctx,
        configuration=CONFIGURED,
        structured_call_enabled=True,
    )
    assert proven["state"] == "complete"
    assert proven["validated_chunk_ids"] == [0]


def test_legacy_cache_entry_is_not_reused_and_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cache entry without pipeline/route identity is counted, not trusted."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunk = _chunk(0, ["README.md"])
    backend = _StubBackend([chunk])
    aux = _Aux([_text_usage(_fragment_json("L", "README.md"))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"

    inputs = _inputs(["README.md"])
    route = sem_mod.resolve_auxiliary_route(CONFIGURED, "web_extract")
    fingerprint = sem_mod.compute_chunk_fingerprint(
        "regular-tracked-v1",
        chunk["system_prompt"] + "\n" + chunk["user_prompt"],
        {"deep": False, "token_budget": 4000},
        sem_mod.get_model_identity_digest(
            "web_extract",
            provider=route.get("provider"),
            model=route.get("model"),
            api_mode=route.get("api_mode"),
        ),
        {"README.md": inputs["README.md"]},
    )
    legacy = sem_mod.SemanticCache(_cache_dir(cache_root))
    legacy.put(fingerprint, {"nodes": [{"id": "Legacy"}], "edges": [], "hyperedges": []})

    result = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )

    assert len(aux.calls) == 1, "an unqualified cache entry is re-derived, not trusted"
    assert result["observed_usage"]["categories"]["cache"] == 1
    assert result["state"] == "complete"


def test_two_concurrent_contexts_stay_isolated_and_account_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fresh copied context per worker: isolation, plus exactly-once session accounting."""
    root, state = project(tmp_path)
    sem_mod = _semantic_module()
    marker: contextvars.ContextVar[str] = contextvars.ContextVar("sk04_marker", default="unset")
    seen: list[tuple[str, str]] = []
    seen_lock = threading.Lock()

    def aux(*args: Any, **kwargs: Any) -> Any:
        with seen_lock:
            seen.append((threading.current_thread().name, marker.get()))
        return _text_usage(_fragment_json("X", "README.md"))

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)

    for label in ("alpha", "beta"):
        ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
        cache_root = tmp_path / f"cache-{label}"
        chunks = [_chunk(index, ["README.md"]) for index in range(4)]
        backend = _StubBackend(chunks)
        token = marker.set(label)
        try:
            result = sem_mod.run_semantic_extraction(
                backend=backend,
                source_root=root,
                graph_path=graph_path,
                inputs=_inputs(["README.md"]),
                cache_root=cache_root,
                ctx=ctx,
                configuration=CONFIGURED,
            )
        finally:
            marker.reset(token)
        assert result["state"] == "complete", label

    assert len(seen) == 8
    assert {label for _thread, label in seen} == {"alpha", "beta"}, (
        "each worker sees its own copied context, never a sibling's"
    )
    assert marker.get() == "unset"


def test_hermes_session_accounting_reconciles_with_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each usage-bearing response is attributed once to the originating session."""
    try:
        from agent import aux_accounting
    except Exception as exc:  # pragma: no cover - exact-Hermes lane always provides it
        pytest.skip(f"exact-Hermes auxiliary accounting is unavailable ({exc})")

    class _SessionDB:
        def __init__(self) -> None:
            self.records: list[tuple[str, str, int]] = []

        def record_auxiliary_usage(self, session_id: str, task: str, **kwargs: Any) -> None:
            self.records.append((session_id, task, int(kwargs.get("input_tokens") or 0)))

    root, state = project(tmp_path)
    sem_mod = _semantic_module()
    graph_path = _graph_file(root)
    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    inputs = _inputs(["README.md", "module.py"])

    def run_for(label: str) -> tuple[dict[str, Any], list[tuple[str, str, int]]]:
        db = _SessionDB()
        ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
        token = aux_accounting.set_accounting_context(db, f"session-{label}")
        try:
            result = sem_mod.run_semantic_extraction(
                backend=_StubBackend(chunks),
                source_root=root,
                graph_path=graph_path,
                inputs=inputs,
                cache_root=tmp_path / f"cache-{label}",
                ctx=ctx,
                configuration=CONFIGURED,
            )
        finally:
            aux_accounting.reset_accounting_context(token)
        return result, list(db.records)

    class _Response:
        def __init__(self, total: int) -> None:
            self.usage = type(
                "Usage",
                (),
                {
                    "prompt_tokens": total,
                    "completion_tokens": 0,
                    "total_tokens": total,
                    "input_tokens": total,
                    "output_tokens": 0,
                },
            )()
            self.model = "stub-primary-model"

    ambient_sessions: list[str] = []
    ambient_lock = threading.Lock()

    def aux(*args: Any, **kwargs: Any) -> Any:
        # Mirror the Hermes auxiliary client's single accounting chokepoint: it
        # records usage against whatever session context the worker inherited.
        context = aux_accounting.get_accounting_context()
        assert context is not None, "the worker must inherit the owning turn's context"
        with ambient_lock:
            ambient_sessions.append(str(context[1]))
        aux_accounting.record_aux_usage(_Response(100), "web_extract")
        return _text_usage(_fragment_json("S", "README.md"))

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)

    results: dict[str, tuple[dict[str, Any], list[tuple[str, str, int]]]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {label: pool.submit(run_for, label) for label in ("alpha", "beta")}
        for label, future in futures.items():
            results[label] = future.result(timeout=60)

    assert sorted(ambient_sessions) == [
        "session-alpha",
        "session-alpha",
        "session-beta",
        "session-beta",
    ]
    for label, (result, records) in results.items():
        assert result["state"] == "complete", label
        assert result["observed_usage"]["model_calls"] == 2, label
        assert len(records) == result["observed_usage"]["model_calls"], (
            f"{label}: one session record per usage-bearing response"
        )
        assert {session for session, _task, _tokens in records} == {f"session-{label}"}, (
            f"{label}: no sibling session may be charged"
        )

    # A repeat run over the warm cache adds no calls and therefore no session records.
    repeat_db = _SessionDB()

    class _NoCallAux:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            raise AssertionError("cache hits must not call the auxiliary model")

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", _NoCallAux())
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    token = aux_accounting.set_accounting_context(repeat_db, "session-repeat")
    try:
        repeat = sem_mod.run_semantic_extraction(
            backend=_StubBackend(chunks),
            source_root=root,
            graph_path=graph_path,
            inputs=inputs,
            cache_root=tmp_path / "cache-alpha",
            ctx=ctx,
            configuration=CONFIGURED,
        )
    finally:
        aux_accounting.reset_accounting_context(token)
    assert repeat["state"] == "complete"
    assert repeat["observed_usage"]["model_calls"] == 0
    assert repeat_db.records == []


def test_auxiliary_response_boundary_consumes_real_terminal_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The transport boundary preserves terminal/phase/shape metadata, no live call."""
    try:
        import agent.auxiliary_client as aux_client
    except Exception as exc:  # pragma: no cover - exact-Hermes lane always provides it
        pytest.skip(f"exact-Hermes auxiliary client is unavailable ({exc})")

    sem_mod = _semantic_module()

    class _Usage:
        prompt_tokens = 7
        completion_tokens = 3
        total_tokens = 10
        completion_tokens_details = type("Details", (), {"reasoning_tokens": 2})()

    class _Message:
        content = "{}"
        tool_calls: list[Any] = []

    class _Choice:
        message = _Message()
        finish_reason = "stop"
        index = 0

    class _Response:
        choices = [_Choice()]
        usage = _Usage()
        model = "stub-primary-model"
        status = "incomplete"
        incomplete_reason = "max_output_tokens"
        phase = "commentary"
        output_text = ""

    def fake_call_llm(*, task: str, messages: list, timeout=None, route_info=None, **kwargs: Any):
        if isinstance(route_info, dict):
            route_info.update(
                {
                    "provider": "openrouter",
                    "model": "stub-primary-model",
                    "api_mode": "chat_completions",
                }
            )
        return _Response()

    monkeypatch.setattr(aux_client, "call_llm", fake_call_llm)
    route_info: dict[str, Any] = {}

    text, usage, meta = sem_mod._call_auxiliary_model(
        "web_extract", "system", "user", timeout=5.0, route_info=route_info
    )

    assert text == "{}"
    assert usage["total_tokens"] == 10
    assert usage["reasoning_tokens"] == 2
    assert usage["route"]["provider"] == "openrouter"
    assert route_info["api_mode"] == "chat_completions"
    assert meta["status"] == "incomplete"
    assert meta["incomplete_reason"] == "max_output_tokens"
    assert meta["phase"] == "commentary"
    # A truncated-but-parseable body still never becomes a final answer.
    assert sem_mod.classify_auxiliary_response(text, meta) == ("incomplete", "max_output_tokens")

    class _OutputTextMessage:
        content = ""
        tool_calls: list[Any] = []

    class _OutputTextChoice:
        message = _OutputTextMessage()
        finish_reason = "stop"
        index = 0

    class _OutputTextResponse:
        choices = [_OutputTextChoice()]
        usage = _Usage()
        model = "stub-primary-model"
        status = "completed"
        phase = "final_answer"
        output_text = "FINAL ANSWER TEXT"

    monkeypatch.setattr(aux_client, "call_llm", lambda **kwargs: _OutputTextResponse())
    fallback_text, _fallback_usage, fallback_meta = sem_mod._call_auxiliary_model(
        "web_extract", "system", "user", timeout=5.0
    )
    assert fallback_text == "FINAL ANSWER TEXT"
    assert fallback_meta["output_text_used"] is True
    assert sem_mod.classify_auxiliary_response(fallback_text, fallback_meta)[0] == "text"


def test_validation_failure_categories_are_content_free() -> None:
    """Malformed JSON, schema, hollow and source failures keep distinct categories."""
    sem_mod = _semantic_module()

    assert (
        sem_mod.classify_validation_failure(
            "{not json", "Malformed model text: no valid JSON found."
        )
        == "malformed_json"
    )
    assert (
        sem_mod.classify_validation_failure(
            "{}", "Semantic fragment schema validation failed: nodes.0.id is required"
        )
        == "schema"
    )
    assert (
        sem_mod.classify_validation_failure(
            "{}", "Hollow model fragment: both nodes and edges are empty."
        )
        == "schema"
    )
    assert (
        sem_mod.classify_validation_failure(
            '{"nodes": [], "edges": []}',
            "Semantic edge endpoints do not bind to accepted fragment or structural nodes",
        )
        == "source"
    )
    assert (
        sem_mod.classify_validation_reason(
            "{}", "Hollow model fragment: both nodes and edges are empty."
        )
        == "hollow"
    )

    # Categories and reasons are bounded labels, never payload fields.
    import aether_agents.knowledge.semantic as module

    for name in (
        "empty",
        "incomplete",
        "malformed_json",
        "schema",
        "source",
        "route",
        "cache",
        "apply",
        "deadline",
    ):
        assert name in module._CATEGORY_NAMES


def test_auxiliary_explicit_cancellation_does_not_leak_and_joins_workers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In-flight AuxiliaryExplicitCancellation (BaseException) never leaks out of extraction.

    Host cancel converts to OPERATION_CANCELLED, natural budget abort returns an honest
    pending receipt with deadline_exhausted, no compose is run, and workers are joined.
    """
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]
        AuxiliaryExplicitCancellation,
        _aux_interrupt_cancel_requested,
    )

    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend: Any = _StubBackend(chunks)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py"])

    # 1. Host cancel while in flight
    cancel_event = threading.Event()
    worker_started = threading.Event()
    scheduled_calls = 0

    def cancelling_worker(*args: Any, **kwargs: Any) -> Any:
        nonlocal scheduled_calls
        scheduled_calls += 1
        worker_started.set()
        cancel_event.set()
        assert _aux_interrupt_cancel_requested() is True
        raise AuxiliaryExplicitCancellation()

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", cancelling_worker)

    with pytest.raises(KnowledgeError) as exc_info:
        sem_mod.run_semantic_extraction(
            backend=backend,
            source_root=root,
            graph_path=graph_path,
            inputs=inputs,
            cache_root=cache_root,
            ctx=ctx,
            configuration=CONFIGURED,
            cancel_event=cancel_event,
        )
    assert exc_info.value.code == "OPERATION_CANCELLED"
    assert scheduled_calls == 1, "no further chunk is scheduled after in-flight cancel"
    assert backend.action_calls("semantic_compose") == [], "compose never runs on cancel"

    # 2. Budget exhaustion while in flight
    backend_budget: Any = _StubBackend([_chunk(0, ["README.md"])])
    clock = [1000.0]
    monkeypatch.setattr(sem_mod, "_now", lambda: clock[0])

    def budget_worker(*args: Any, **kwargs: Any) -> Any:
        clock[0] += 500.0  # exhaust the budget while in flight
        assert _aux_interrupt_cancel_requested() is True
        raise AuxiliaryExplicitCancellation()

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", budget_worker)

    receipt = sem_mod.run_semantic_extraction(
        backend=backend_budget,
        source_root=root,
        graph_path=graph_path,
        inputs=_inputs(["README.md"]),
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED | {"semantic_deadline_seconds": 300.0},
    )
    assert receipt["state"] in ("pending", "partial")
    assert receipt["pipeline"]["deadline_exhausted"] is True
    assert receipt["observed_usage"]["categories"]["deadline"] > 0
    assert backend_budget.action_calls("semantic_compose") == []


def test_executor_shutdown_does_not_block_past_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ThreadPoolExecutor does not block past the budget when in-flight workers sleep.

    AC-05 requires return within the configured budget from entry through return.
    When deadline fires, an uncooperative worker that ignores timeout and cancel
    cannot hold the executor join past the deadline.
    """
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()

    chunks = [_chunk(0, ["README.md"]), _chunk(1, ["module.py"])]
    backend: Any = _StubBackend(chunks)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md", "module.py"])

    worker_started = threading.Event()

    def slow_worker_ignoring_timeout_and_cancel(*args: Any, **kwargs: Any) -> Any:
        # Uncooperative worker: ignores call timeout AND does not poll cancel.
        # Sleeps for 2.5s regardless of cancel/interrupt signals.
        worker_started.set()
        time.sleep(2.5)
        return _text_usage(_fragment_json("slow", "README.md"))

    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", slow_worker_ignoring_timeout_and_cancel)

    t0 = time.monotonic()
    receipt = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED | {"semantic_deadline_seconds": 0.5},
    )
    elapsed = time.monotonic() - t0

    assert worker_started.is_set(), "worker must have started before deadline"
    # Must return well before 2.5s (typically ~0.5s - 0.7s)
    assert elapsed < 1.5, f"Execution took {elapsed:.2f}s; exceeded budget on shutdown"
    assert receipt["state"] in ("pending", "partial")
    assert receipt["pipeline"]["deadline_exhausted"] is True
    assert receipt["observed_usage"]["categories"]["deadline"] > 0
    assert backend.action_calls("semantic_compose") == []


def test_prepare_validate_compose_receive_positive_timeout_and_shared_cancel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-6: prepare, validate, and compose receive positive timeout <= remaining - 5s and shared cancel."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"])]
    backend = _StubBackend(chunks)
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"X{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md"])
    cancel_ev = threading.Event()

    result = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
        cancel_event=cancel_ev,
        deadline_seconds=300.0,
    )
    assert result["state"] == "complete"

    prep_calls = backend.action_calls("semantic_prepare")
    assert len(prep_calls) >= 1
    for call in prep_calls:
        assert call["timeout"] is not None
        assert 0 < call["timeout"] <= 295.0
        assert call["cancel_event"] is cancel_ev

    val_calls = backend.action_calls("semantic_validate")
    assert len(val_calls) >= 1
    for call in val_calls:
        assert call["timeout"] is not None
        assert 0 < call["timeout"] <= 295.0
        assert call["cancel_event"] is cancel_ev

    comp_calls = backend.action_calls("semantic_compose")
    assert len(comp_calls) == 1
    for call in comp_calls:
        assert call["timeout"] is not None
        assert 0 < call["timeout"] <= 295.0
        assert call["cancel_event"] is cancel_ev


def test_compose_timeout_while_budget_remains_is_a_bounded_apply_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-7: a Graphify TIMEOUT with the operation budget intact stays typed/apply, never deadline."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"])]
    backend = _StubBackend(chunks)

    def failing_compose(*_args: Any, **_kwargs: Any) -> Any:
        raise KnowledgeError("TIMEOUT", "Graphify exceeded its execution limit.")

    backend._compose = failing_compose  # noqa: SLF001
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"Y{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md"])

    receipt = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
    )
    # A component timeout with minutes left on the operation clock is not operation exhaustion.
    assert receipt["pipeline"]["deadline_exhausted"] is False
    assert receipt["observed_usage"]["categories"].get("deadline", 0) == 0
    # It remains a bounded composition failure.
    assert receipt["observed_usage"]["categories"].get("apply", 0) > 0
    assert receipt["state"] in ("partial", "unavailable", "pending")
    # Cache was written before compose and must be retained
    cached_files = list(_cache_dir(cache_root).glob("*.json"))
    assert len(cached_files) == 1


def test_operation_budget_compose_timeout_attributes_deadline_and_retains_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-7: a compose TIMEOUT that consumed the operation budget is deadline, not apply."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    clock = [1000.0]
    monkeypatch.setattr(sem_mod, "_now", lambda: clock[0])
    chunks = [_chunk(0, ["README.md"])]
    backend = _StubBackend(chunks)

    def budget_exhausting_compose(*_args: Any, **_kwargs: Any) -> Any:
        # The component reports a TIMEOUT only after the operation clock ran out.
        clock[0] = 1400.0
        raise KnowledgeError("TIMEOUT", "Graphify exceeded its execution limit.")

    backend._compose = budget_exhausting_compose  # noqa: SLF001
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"W{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md"])

    receipt = sem_mod.run_semantic_extraction(
        backend=backend,
        source_root=root,
        graph_path=graph_path,
        inputs=inputs,
        cache_root=cache_root,
        ctx=ctx,
        configuration=CONFIGURED,
        operation_deadline=1300.0,
    )
    assert receipt["pipeline"]["deadline_exhausted"] is True
    assert receipt["pipeline"]["operation_wide"] is True
    assert receipt["state"] in ("pending", "partial")
    assert receipt["observed_usage"]["categories"].get("apply", 0) == 0
    assert (
        receipt["observed_usage"]["categories"].get("deadline", 0) > 0
        or receipt["observed_usage"]["categories"].get("deadline_deferred", 0) > 0
    )
    # Cache was written before compose and must be retained
    cached_files = list(_cache_dir(cache_root).glob("*.json"))
    assert len(cached_files) == 1


def test_compose_cancel_reraises_operation_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-7: A compose cancellation re-raises OPERATION_CANCELLED, never swallows as apply."""
    root, state = project(tmp_path)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state, root=root)
    sem_mod = _semantic_module()
    chunks = [_chunk(0, ["README.md"])]
    backend = _StubBackend(chunks)

    def cancelling_compose(*_args: Any, **_kwargs: Any) -> Any:
        raise KnowledgeError("OPERATION_CANCELLED", "Operation was cancelled.")

    backend._compose = cancelling_compose  # noqa: SLF001
    aux = _Aux([lambda index: _text_usage(_fragment_json(f"Z{index}", chunks[index]["files"][0]))])
    monkeypatch.setattr(sem_mod, "_call_auxiliary_model", aux)
    graph_path = _graph_file(root)
    cache_root = tmp_path / "cache"
    inputs = _inputs(["README.md"])

    with pytest.raises(KnowledgeError) as exc_info:
        sem_mod.run_semantic_extraction(
            backend=backend,
            source_root=root,
            graph_path=graph_path,
            inputs=inputs,
            cache_root=cache_root,
            ctx=ctx,
            configuration=CONFIGURED,
        )
    assert exc_info.value.code == "OPERATION_CANCELLED"
