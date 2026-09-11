"""Documentary observation guidance checks, not organic agent qualification."""

from pathlib import Path

import yaml

from aether_agents.cli import _build_parser

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".aether/skills/aether-observe/SKILL.md"


def test_project_skill_is_discovered_without_identity_hardcoding() -> None:
    text = SKILL.read_text()
    meta = yaml.safe_load(text.split("---", 2)[1])
    assert meta["name"] == "aether-observe"
    assert len(meta["description"]) <= 60
    assert "Project Canonical Skill" in text
    assert ".aether/skills/aether-observe/SKILL.md" in (ROOT / "AGENTS.md").read_text()
    assert "/home/" not in text and "/Users/" not in text
    soul = (ROOT / "src/aether_agents/resources/profiles/morfeo/SOUL.md").read_text()
    section = soul.split("### Status and observation", 1)[1].split("\n### ", 1)[0]
    for required in ("aether_observe", "freshness", "coverage", "targeted", "independent review"):
        assert required in section
    assert ".aether/skills/aether-observe" not in section
    assert "### Final result acceptance" in soul
    assert "contract-result-review" in soul


def test_skill_selects_status_changes_diagnose_and_explicit_fallback() -> None:
    text = SKILL.read_text()
    for required in (
        'action="status"',
        'action="changes"',
        'action="diagnose"',
        "since_summary_id",
        "summary_id",
        "as_of",
        "coverage",
        "Heartbeats prove liveness only",
        "specific requested correction",
        "schema/privacy error",
        "Do not disable privacy guards",
        "independent approval",
        "exact board/task binding",
    ):
        assert required in text


def test_documented_cli_forms_are_real_parser_options() -> None:
    parser = _build_parser()
    parser.parse_args(["observe", "CONTRACT_REF", "--project", "PROJECT_ROOT", "--json"])
    parser.parse_args(
        [
            "observe",
            "CONTRACT_REF",
            "--project",
            "PROJECT_ROOT",
            "--since",
            "sum_" + "0" * 64,
            "--json",
        ]
    )


def test_guide_distinguishes_authority_from_derived_state() -> None:
    text = (ROOT / "docs/guides/observation.md").read_text()
    assert "not a zero-write filesystem probe" in text
    assert "derived observation projection" in text
    assert "../../.aether/skills/aether-observe/SKILL.md" in text
    assert "read-only: it does not mutate" not in text
