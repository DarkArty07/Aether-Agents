"""Resource regression checks, not proof of agent compliance or independent review."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
RESOURCES = ROOT / "src/aether_agents/resources"


def _text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_morfeo_receives_result_without_taking_supervisor_closeout() -> None:
    soul = _text(RESOURCES / "profiles/morfeo/SOUL.md")
    receipt = soul.split("### Final result acceptance", 1)[1].split("### ", 1)[0]
    for requirement in (
        "contract-result-review",
        "current owner instruction",
        "finalized Objective Contract",
        "final artifact",
        "material acceptance criterion",
        "evidence producer",
        "revision",
        "unverified",
        "Supervisor owns normal pipeline closeout",
    ):
        assert requirement in receipt
    assert "Return material discrepancies through sector 07" in receipt
    rework = soul.split("### Objective discrepancies and incidental defects", 1)[1].split(
        "### ", 1
    )[0]
    assert "Do not weaken acceptance or create an exception without owner authority" in rework
    assert "instead of repairing product implementation or changing completed board state" in rework


def test_receipt_skill_keeps_provenance_and_proportionate_verification_explicit() -> None:
    path = RESOURCES / "skills/contract-result-review/SKILL.md"
    assert path.is_file(), "The canonical reception procedure must be distributed"
    skill = _text(path)
    for requirement in (
        "Read intent before the handoff",
        "every material criterion",
        "exact revision",
        "directly verified by Morfeo",
        "reused pipeline evidence",
        "unverified",
        "supported continuation/rework",
        "not a fixed sample quota",
        "not an automatic full-suite rerun",
        "No acceptance waiver",
        "not a behavioral guarantee",
    ):
        assert requirement in skill


def test_design_distinguishes_terminal_execution_from_owner_acceptance() -> None:
    design = _text(ROOT / "DESIGN.md")
    assert "Pipeline execution completion is not automatically owner-objective acceptance" in design
    assert "contract-result-review" in design
