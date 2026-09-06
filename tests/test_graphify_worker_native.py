"""Exercise the worker in the isolated engine environment, never inside Hermes.

Run this module with the qualified Graphify interpreter. The ordinary manager
suite reports the explicit missing-component skip instead of installing it.
"""

from __future__ import annotations

import importlib.metadata
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("graphify", reason="Run in the isolated Graphify component environment")

from aether_agents.knowledge import graph_worker


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("native-worker")
    source = root / "sources"
    source.mkdir()
    (source / "order.py").write_text(
        "def charge():\n    return 1\n\ndef reserve():\n    return charge()\n"
    )
    (source / "README.md").write_text("# Reservations\n\nSee [implementation](order.py).\n")
    graph = root / "graphify-out/graph.json"
    with pytest.MonkeyPatch.context() as patch:
        home = root / "home"
        home.mkdir()
        patch.setenv("HOME", str(home))
        patch.setenv("GRAPHIFY_OUT", str(graph.parent))
        patch.setenv("GRAPHIFY_QUERY_LOG_DISABLE", "1")
        patch.chdir(source)
        request = {"source_root": str(source), "graph_path": str(graph)}
        result = graph_worker.execute({**request, "action": "update"})
        assert "built" in result["content"] and graph.is_file()
        yield request


@pytest.mark.parametrize(
    "action,arguments",
    [
        ("query", {"question": "reserve"}),
        ("explain", {"node": "reserve"}),
        ("impact", {"node": "charge", "depth": 2}),
        ("path", {"source": "reserve", "target": "charge"}),
        ("neighbors", {"node": "reserve"}),
        ("neighbors", {"node": "reserve", "relation": "calls"}),
        ("community", {"community_id": 0}),
    ],
)
def test_native_worker_query_contracts(corpus, action: str, arguments: dict) -> None:
    result = graph_worker.execute({**corpus, "action": action, "arguments": arguments})
    assert result["content"]
    assert isinstance(result["references"], list)
    assert len(result["references"]) > 0
    if action == "explain":
        assert "resolved_node" in result
        assert result["resolved_node"]["id"]
    if action == "community":
        assert "community" in result
        assert result["community"]["id"] == arguments["community_id"]


@pytest.mark.parametrize(
    "action,arguments",
    [
        ("neighbors", {"node": "DefinitelyMissingSentinel"}),
        ("community", {"community_id": 999999}),
        ("unsupported", {}),
    ],
)
def test_native_worker_rejects_unresolved_operations(corpus, action: str, arguments: dict) -> None:
    with pytest.raises(ValueError):
        graph_worker.execute({**corpus, "action": action, "arguments": arguments})


def test_native_save_and_reflect_preserve_answer_without_shared_sidecar(corpus) -> None:
    result = graph_worker.execute(
        {
            "action": "memory_save",
            "arguments": {
                "situation": "A corrected integration step",
                "lesson": "Call the verified interface.",
                "applicability": "Only this project's current interface.",
                "outcome": "corrected",
                "correction": "CORRECTED_NATIVE_SOLUTION",
                "source_nodes": ["charge"],
            },
        }
    )
    assert "Call the verified interface." in result["content"]
    reflected = graph_worker.execute(
        {"action": "memory_reflect", "arguments": {"notes": [result["content"]]}}
    )
    assert reflected["count"] == 1
    assert "CORRECTED_NATIVE_SOLUTION" in reflected["content"]
    assert not (Path(corpus["graph_path"]).parent / ".graphify_learning.json").exists()


def test_native_worker_rejects_unqualified_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "99.0.0")
    with pytest.raises(ValueError, match="not qualified"):
        graph_worker.execute({"action": "probe"})


def test_worker_protocol_returns_only_one_json_result(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{"action":"probe"}')))
    assert graph_worker.main() == 0
    response = json.loads(capsys.readouterr().out)
    assert response["ok"] and response["version"] == "0.9.54"
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{"action":"invalid"}')))
    assert graph_worker.main() == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False
