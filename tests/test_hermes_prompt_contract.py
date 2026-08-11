"""Regression contract for the lean Hermes Prompt 0.4.0 migration."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PROMPT = ROOT / "home" / "SOUL.md"
PROMPT_ARCHIVE = ROOT / "home" / "prompts" / "hermes" / "0.4.0" / "SOUL.md"
ROLLBACK_PROMPT = ROOT / "home" / "prompts" / "hermes" / "3.0.0-hot.3" / "SOUL.md"
ROLLBACK_SHA256 = "1c942a130189017f74b5eb675170d8ac8a5b0fa3926dd807db87454ec8cb78b1"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_prompt_has_exact_archive_and_preserved_rollback() -> None:
    active = ACTIVE_PROMPT.read_bytes()

    assert active == PROMPT_ARCHIVE.read_bytes()
    assert active != ROLLBACK_PROMPT.read_bytes()
    assert hashlib.sha256(ROLLBACK_PROMPT.read_bytes()).hexdigest() == ROLLBACK_SHA256


def test_prompt_is_lean_identity_policy_with_exact_seven_axes() -> None:
    prompt = _text(ACTIVE_PROMPT)
    headings = re.findall(r"^## (.+)$", prompt, flags=re.MULTILINE)

    assert "**Prompt version:** 0.4.0" in prompt
    assert len(prompt.splitlines()) <= 100
    assert len(prompt.encode("utf-8")) <= 8_000
    assert headings == [
        "1. Outcome and truth",
        "2. Authority without approval theatre",
        "3. Scope and execution",
        "4. Routing and model economics",
        "5. Orchestration",
        "6. Verification and learning",
        "7. Communication and completion",
    ]


def test_prompt_encodes_autonomy_economics_supervision_and_acceptance() -> None:
    prompt = _text(ACTIVE_PROMPT)
    required = (
        "it does not mean asking for the same confirmation again",
        "autonomously choose tools, files, tests, workers, provider/model tier",
        "Hermes decides autonomously whether to work directly or orchestrate",
        "cheapest model tier that can preserve quality",
        "Do not ask for permission merely to activate an already authorized coordination path",
        "Worker completion is a claim, not acceptance",
        "Hermes takes over only when that is the best quality/cost decision",
        "Skills contain reusable procedures and follow the current Hermes skill-review and curation policy",
    )

    assert [fragment for fragment in required if fragment not in prompt] == []


def test_prompt_excludes_volatile_runtime_inventory_and_retired_names() -> None:
    prompt = _text(ACTIVE_PROMPT)
    volatile = (
        "project_admit",
        "swarm_start",
        "swarm_dispatch",
        "swarm_close",
        "15-tool",
        "15 tools",
        "Hefesto",
        "Daedalus",
        "Ictinus",
        "Ariadna",
        "Athena",
        "Etalides",
        "Olympus",
        "ACPManager",
        "Harmonia",
        "talk_to",
        "aether_curate",
    )

    assert [name for name in volatile if name in prompt] == []


def test_current_entrypoints_identify_prompt_0_4_0() -> None:
    current_pointers = (
        ROOT / "AGENTS.md",
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "README.md",
        ROOT / "home" / "README.md",
        ROOT / "docs" / "releases" / "v0.23.0" / "ROADMAP.md",
        ROOT / "docs" / "releases" / "v0.23.0" / "STATUS.yaml",
    )

    assert [str(path.relative_to(ROOT)) for path in current_pointers if "0.4.0" not in _text(path)] == []


def test_hot_runtime_evidence_remains_historical() -> None:
    evidence = _text(ROOT / "docs" / "releases" / "v0.23.0" / "MCP_COLD_START_HOT_RUNTIME_EVIDENCE.md")

    assert "3.0.0-hot.3" in evidence
    assert "0.4.0" not in evidence


def test_template_preserves_standard_automatic_skill_values() -> None:
    template = _text(ROOT / "home" / "config.yaml.template")

    assert re.search(r"(?m)^  user_char_limit: 4000$", template)
    assert "creation_nudge_interval" not in template
    assert re.search(r"(?m)^curator:\n  enabled: true$", template)
    assert "  background_review:\n" not in template


def test_migration_document_redirects_every_removed_policy_family() -> None:
    migration = _text(
        ROOT / "docs" / "releases" / "v0.23.0" / "HERMES_PROMPT_0_4_0_MIGRATION.md"
    )
    destinations = (
        "docs/knowledge/AUTHORITY.md",
        "docs/product/EXPERIENCE.md",
        "docs/product/PRINCIPLES.md",
        "docs/product/COMPLETION.md",
        "docs/architecture/ORCHESTRATION.md",
        "docs/architecture/AETHER_MCP.md",
        "docs/architecture/DAIMONS.md",
        "docs/releases/v0.23.0/STATUS.yaml",
        "docs/knowledge/HERMES_LEARNING_MODEL.md",
    )

    assert [destination for destination in destinations if destination not in migration] == []
