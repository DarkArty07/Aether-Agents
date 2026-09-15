"""Document/source loading checks, NOT behavioral or installed-profile qualification."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
RESOURCES = ROOT / "src/aether_agents/resources"
SKILLS = {
    "objective-contract-design": "Morfeo",
    "contract-result-review": "Morfeo",
    "supervisor-decomposition": "Supervisor",
    "implementation-evidence": "Implementer",
}
SKILL_VERSIONS = {
    "objective-contract-design": "0.1.0",
    "contract-result-review": "0.1.0",
    "supervisor-decomposition": "0.1.3",
    "implementation-evidence": "0.1.1",
}


@pytest.mark.parametrize("name,role", SKILLS.items())
def test_skill_metadata_and_single_file_scope(name: str, role: str) -> None:
    directory = RESOURCES / "skills" / name
    assert {p.name for p in directory.iterdir()} == {"SKILL.md"}
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    front, body = text.removeprefix("---\n").split("\n---\n", 1)
    metadata = yaml.safe_load(front)
    assert metadata["name"] == name
    assert role in metadata["description"]
    assert len(metadata["description"]) <= 60
    assert metadata["version"] == SKILL_VERSIONS[name]
    expected_author = (
        "Christopher, Hermes Agent"
        if name == "contract-result-review"
        else "Morfeo (Aether role), Hermes Agent"
    )
    assert metadata["author"] == expected_author
    assert metadata["platforms"] == ["linux", "macos", "windows"]
    for heading in ("When to Use", "Prerequisites", "Procedure", "Pitfalls", "Verification"):
        assert f"## {heading}" in body
    assert "cannot grant authority" in " ".join(body.split()) or (
        "cannot grant" in body and "authority" in body
    )
    assert "project-relative" in body
    assert text.count("```") % 2 == 0
    assert "[truncated]" not in text.lower()
    assert not re.search(r"(?i)/home/|/users/|[a-z]:\\users\\", text)


@pytest.mark.parametrize("name", SKILLS)
def test_skill_content_has_no_executable_template(name: str) -> None:
    text = (RESOURCES / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    # These procedures must remain static documents, not shell preprocessing payloads.
    assert "!`" not in text
    assert "$ARGUMENTS" not in text


def test_unit_review_boundary_is_consistent_in_source_documents() -> None:
    paths = [
        RESOURCES / "profiles/supervisor/SOUL.md",
        RESOURCES / "skills/supervisor-decomposition/SKILL.md",
        RESOURCES / "skills/implementation-evidence/SKILL.md",
    ]
    for path in paths:
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "same-card" in text
        assert "claimed" in text and "review run" in text
        assert "terminal integration" in text.lower()
        assert "trusted runtime graph" in text
    # Presence checks establish documented boundaries, not that an agent obeyed them.


def test_supervisor_convergence_guidance_preserves_authority() -> None:
    """Check documented obligations, not whether a running model obeys them."""
    soul = (RESOURCES / "profiles/supervisor/SOUL.md").read_text()
    skill = (RESOURCES / "skills/supervisor-decomposition/SKILL.md").read_text()
    normalized_skill = " ".join(skill.split())
    spec = (ROOT / "specs/r7-supervision-and-convergence/spec.md").read_text()
    for phrase in (
        "Own review convergence",
        "same failure class recurs",
        "assess the common cause and consolidate findings",
        "Return an unsuitable or missing material design",
        "Preserve the candidate and evidence",
        "Do not invent requirements, weaken existing guarantees",
    ):
        assert phrase in soul
    for phrase in (
        "Tie findings to current obligations",
        "Review the mechanism together",
        "Recognize non-convergence",
        "Return one coherent correction or a material design question",
        "when the contract is complete",
        "Optional work does not",
        "Never approve merely because a round budget was reached",
        "not healthy independent work",
        "A genuinely",
        "not restart a retired synthetic campaign",
    ):
        assert phrase in skill
    assert "FR-736b" in spec
    assert "FR-736c" in spec
    assert "FR-736d" in spec
    assert "no new engine, form or judge is required" in spec
    assert "exact Git/raw artifact" in normalized_skill
    assert "Re-review the delta proportionately" in normalized_skill
    assert "review-round number alone is not a reason" in normalized_skill
    assert "generic `sdlc-review` skill" in normalized_skill
    assert "treat it as supplementary" in normalized_skill
    assert "compact incremental record in the existing review handoff/comment" in normalized_skill
    assert "documentation-only delta normally reuses" in normalized_skill
    assert "functional delta reruns the affected required controls" in normalized_skill
    assert "must not turn an optional improvement into a blocking requirement" in normalized_skill
    assert "At the first source-backed indication that a premise may be false" in normalized_skill
    assert "does not establish efficacy or runtime adoption" in normalized_skill
    assert "Isolated implementation defect" in skill
    assert "unsuitable shared-state isolation design" in skill
    assert "Unrelated optional refactor" in skill
    assert "new real preservation regression" in skill


def test_review_return_cannot_silently_redefine_acceptance() -> None:
    implementer = (RESOURCES / "skills/implementation-evidence/SKILL.md").read_text(
        encoding="utf-8"
    )
    spec = (ROOT / "specs/r7-supervision-and-convergence/spec.md").read_text(encoding="utf-8")
    assert "A review return is execution guidance, not a" in implementer
    assert "before changing code or tests" in implementer
    assert "FR-735a" in spec
    assert "FR-737c" in spec
    assert "Implementer-pinned skills/model overrides" in spec
    assert "A board key alone never opts a task into Aether" in spec
    assert "Legacy exact-flow cycles without the snapshot remain supported" in spec
    assert "creates no magical fail-closed classification" in spec


def test_native_loader_reads_exact_documents_in_disposable_home(tmp_path: Path) -> None:
    if importlib.util.find_spec("hermes_cli") is None:
        pytest.skip("native loader requires the already provisioned Hermes interpreter")
    # Hermes must select the explicitly materialized canonical profile, not an
    # OS-home/private copy with the same names. Everything is established in
    # the child environment before its first Hermes import.
    home = tmp_path / "canonical-profile"
    private_home = tmp_path / "private-os-home"
    expected = {}
    for name in SKILLS:
        data = (RESOURCES / "skills" / name / "SKILL.md").read_bytes()
        target = home / "skills" / name / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        expected[name] = hashlib.sha256(data).hexdigest()
        private_target = private_home / ".hermes" / "skills" / name / "SKILL.md"
        private_target.parent.mkdir(parents=True, exist_ok=True)
        private_target.write_text("private learned copy; must not be selected\n", encoding="utf-8")
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("HERMES_KANBAN_") or key in {
            "HERMES_PROFILE",
            "HERMES_SESSION_ID",
            "HERMES_SKILLS_DIR",
        }:
            env.pop(key)
    # Never suppress a delegated-child identity marker; loading text needs no board mutation.
    env.update(
        {
            "HERMES_HOME": str(home),
            "HOME": str(private_home),
            "HERMES_KANBAN_HOME": str(tmp_path / "kanban-home"),
            "HERMES_KANBAN_DB": str(tmp_path / "kanban-home" / "kanban.db"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    script = """
import hashlib, json, os
from pathlib import Path
from tools.skills_tool import skill_view
result = {}
for name in json.loads(os.environ['CHECK_SKILL_NAMES']):
    response = json.loads(skill_view(name, preprocess=False))
    assert response.get('success'), response
    data = response['content'].encode('utf-8')
    source = Path(response['_source_path']).resolve()
    source.relative_to(Path(os.environ['HERMES_HOME']).resolve())
    assert source != (Path(os.environ['HOME']) / '.hermes' / 'skills' / name / 'SKILL.md')
    result[name] = hashlib.sha256(data).hexdigest()
print(json.dumps(result, sort_keys=True))
"""
    env["CHECK_SKILL_NAMES"] = json.dumps(list(SKILLS))
    run = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == expected


def test_sectorized_souls_and_canonical_procedures_carry_d6_amendments() -> None:
    """Document/source loading checks for D6 amendments in SOULs and four canonical procedures."""
    morfeo_soul = (RESOURCES / "profiles/morfeo/SOUL.md").read_text(encoding="utf-8")
    supervisor_soul = (RESOURCES / "profiles/supervisor/SOUL.md").read_text(encoding="utf-8")
    implementer_soul = (RESOURCES / "profiles/implementer/SOUL.md").read_text(encoding="utf-8")

    # D6 Morfeo amendment in working method / observation
    assert "Remain the design steward after handoff" in morfeo_soul
    assert "distinguish a local correction from a false premise" in morfeo_soul
    assert "Acknowledge a sound continuation without duplicating Supervisor's review" in morfeo_soul
    assert (
        "Do not wait for the final result when current evidence already invalidates the approach; do not take over implementation"
        in morfeo_soul
    )

    # D6 Supervisor amendment in communication / convergence
    assert (
        "Share concrete questions and material execution evidence with the originating design steward during the contract"
        in supervisor_soul
    )
    assert "An existing design may be unsuitable even when no section is missing" in supervisor_soul
    assert (
        "Consume and disposition the answer against current sources; retain execution, review and integration ownership"
        in supervisor_soul
    )
    assert (
        "Peer advice never supplies owner authority or independent approval of coauthored changes"
        in supervisor_soul
    )

    # D6 Implementer amendment in verification / escalation
    assert (
        "Before encoding a test oracle, verify that the required state or transition is possible in the actual interface"
        in implementer_soul
    )
    assert (
        "Ask a bounded, source-backed question when the agreed design contradicts that interface; continue unrelated authorized work"
        in implementer_soul
    )
    assert (
        "Record consumption and disposition of peer help without transferring writable ownership or inventing new acceptance"
        in implementer_soul
    )

    # Nine-sector headings remain intact across all three SOULs
    expected_headings = [
        "## 01. Identity and purpose",
        "## 02. Authority, scope, and boundaries",
        "## 03. Decision criteria",
        "## 04. Working method",
        "## 05. Procedures, tools, and coordination",
        "## 06. Evidence, acceptance, and closeout",
        "## 07. Failures, rework, and recovery",
        "## 08. Knowledge, memory, and learning",
        "## 09. Portability and runtime boundaries",
    ]
    for soul_text in (morfeo_soul, supervisor_soul, implementer_soul):
        headings = [line for line in soul_text.splitlines() if line.startswith("## ")]
        assert headings == expected_headings
        assert (
            "Aether has exactly three product roles: Morfeo, Supervisor, and Implementer."
            in soul_text
        )

    # Four canonical procedures carry collaboration comment lifecycle, action verbs, and distinction
    oc_skill = (RESOURCES / "skills/objective-contract-design/SKILL.md").read_text(encoding="utf-8")
    sd_skill = (RESOURCES / "skills/supervisor-decomposition/SKILL.md").read_text(encoding="utf-8")
    ie_skill = (RESOURCES / "skills/implementation-evidence/SKILL.md").read_text(encoding="utf-8")
    crr_skill = (RESOURCES / "skills/contract-result-review/SKILL.md").read_text(encoding="utf-8")

    for skill_text in (oc_skill, sd_skill, ie_skill, crr_skill):
        norm_text = " ".join(skill_text.split())
        assert "kanban_comment" in norm_text
        assert "Early advice is not final result acceptance" in norm_text

    for skill_text in (oc_skill, sd_skill, ie_skill):
        assert '"action": "request"' in skill_text or "'action': 'request'" in skill_text
        assert '"action": "resolve"' in skill_text or "'action': 'resolve'" in skill_text
        assert "disposition" in skill_text
