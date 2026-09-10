"""Canonical skills, shipped contracts and isolated component qualification."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
import yaml
from test_project_knowledge_engine import PROJECT, project

from aether_agents.knowledge.component import install
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.service import KnowledgeService, validate_arguments

ROOT = Path(__file__).parents[1]
RESOURCES = ROOT / "src/aether_agents/resources"


@pytest.mark.parametrize(
    "name,tool", [("project-knowledge", "project_knowledge"), ("work-memory", "work_memory")]
)
def test_skills_are_canonical_procedures_with_valid_examples(name: str, tool: str) -> None:
    text = (RESOURCES / "skills" / name / "SKILL.md").read_text()
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert metadata["name"] == name
    assert len(metadata["description"]) <= 60
    assert metadata["description"].endswith(".")
    assert metadata["platforms"] == ["linux"]
    for heading in (
        "When to Use",
        "Prerequisites",
        "How to Run",
        "Quick Reference",
        "Procedure",
        "Pitfalls",
        "Verification",
    ):
        assert f"## {heading}" in text
    for example in re.findall(r"```json\n(.*?)\n```", text, re.S):
        validate_arguments(tool, json.loads(example))
    assert "/home/" not in text
    assert "never" in text.lower()


def test_qualification_catalog_matches_registered_schemas() -> None:
    from scripts.qualify_knowledge_expansion import _validate_catalog

    result = _validate_catalog()
    assert result["project_actions"] == 14
    assert result["memory_actions"] == 5
    assert result["validated_examples"] == 19
    assert result["rejected_boundary_cases"] == 5


@pytest.mark.parametrize("role", ["morfeo", "supervisor", "implementer"])
def test_role_resources_share_tools_and_are_opt_in(role: str) -> None:
    soul = (RESOURCES / "profiles" / role / "SOUL.md").read_text()
    for name in ("project_knowledge", "work_memory", "project-knowledge", "work-memory"):
        assert f"`{name}`" in soul
    assert "All three roles have the same knowledge and memory tools" in soul
    config = yaml.safe_load((RESOURCES / "profiles" / role / "config.yaml").read_text())
    assert "aether-project-knowledge" in config["plugins"]["enabled"]
    assert config["plugins"]["entries"]["aether-project-knowledge"]["settings"]["enabled"] is False


def test_morfeo_soul_defines_project_experience_save_contract() -> None:
    """Guard prompt requirements, not an LLM's organic behavioral compliance."""
    soul = (RESOURCES / "profiles" / "morfeo" / "SOUL.md").read_text()
    section = soul.split("## Shared project knowledge and role experiences", 1)[1]
    section = section.split("\n## ", 1)[0]
    for instruction in (
        '`work_memory` using `action="save"`',
        "before closing the work or changing objectives",
        "Do not invent lessons or require one note per task",
        "owner-facing preferences belong in personal memory",
        "project decisions and obligations belong in their canonical artifacts",
        "contextual project experiences belong in `work_memory`",
        "reusable procedures belong in skills under existing governance",
        "do not duplicate content indiscriminately",
        "Verify a save through the tool's successful receipt",
        "state explicitly that the experience was not saved there",
        "Search and read original notes before reuse",
        "Correct obsolete notes using the returned revision",
        "Read/update/save do not grant new product authority",
    ):
        assert instruction in section


def test_component_lock_contains_pins_and_hashes() -> None:
    text = (RESOURCES / "graphify" / "requirements.txt").read_text()
    assert "graphifyy==0.9.54" in text
    assert "--hash=sha256:" in text
    assert "/home/" not in text
    requirements = [
        line for line in text.splitlines() if line and not line.startswith(("#", " ", "--"))
    ]
    assert requirements and all("==" in line for line in requirements)


@pytest.mark.integration
def test_managed_component_installs_locked_distribution_and_queries(tmp_path: Path) -> None:
    if os.environ.get("AETHER_TEST_COMPONENT_INSTALL") != "1":
        pytest.skip("Explicit networked disposable component installation lane")
    _root, state = project(tmp_path)
    service = KnowledgeService(state, tmp_path / "cache")
    result = install(service, destination_root=tmp_path / "data")
    assert result["component"]["ownership"] == "managed"
    assert len(result["component"]["lock_id"]) == 64
    assert service.backend().probe()["version"] == "0.9.54"
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    assert (
        service.execute(
            ctx, "project_knowledge", {"action": "update", "reason": "Installed wheel proof"}
        )["outcome"]
        == "updated"
    )
    answer = service.execute(
        ctx, "project_knowledge", {"action": "query", "question": "process_order"}
    )
    assert "process_order" in answer["content"]
    note = service.execute(
        ctx,
        "work_memory",
        {
            "action": "save",
            "idempotency_key": "installed-component-note-01",
            "situation": "Installed component test",
            "lesson": "Original answer remains readable",
            "applicability": "Fixture",
            "outcome": "useful",
            "evidence": [],
        },
    )
    assert (
        "Original answer"
        in service.execute(ctx, "work_memory", {"action": "read", "note_id": note["note_id"]})[
            "content"
        ]
    )
    assert service.execute(ctx, "work_memory", {"action": "reflect"})["count"] == 1
    repeated = install(service, destination_root=tmp_path / "data")
    assert repeated["component"]["python"] == result["component"]["python"]
    assert not list(tmp_path.rglob(".graphify_learning.json"))
