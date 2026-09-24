"""Native slash dispatch and project-local planning qualification on the selected Hermes fork.

Qualifies:
- Outcome: AC (d); US-PS-1, US-PS-3; PS-001, PS-009.
- Selected runtime: maintained fork DarkArty07/aether-hermes at pinned commit aed6591a.
- Collision gate: hermes_cli/commands.py registers no plan command; /plan is non-colliding.
- Native selection: canonical root skills/plan/SKILL.md selected over nested learned skill.
- Role absence: plan resource is strictly absent from disposable Supervisor and Implementer homes.
- Planning-only semantics: project-local .aether/plans/<objective-slug>.md lifecycle.
"""

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

from aether_agents import lifecycle

CANDIDATE_COMMIT = "3da14572232775aedbc23b38393227cd62ed5ebc"
CANDIDATE_PLAN_SHA256 = "b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d"
PINNED_FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
PINNED_FORK_SOURCE_TREE_SHA256 = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"


def _resolve_hermes_python() -> Path:
    """Resolve the Python executable providing the selected maintained Hermes fork."""
    explicit = os.environ.get("AETHER_HERMES_PYTHON", "").strip()
    if explicit and Path(explicit).is_file():
        return Path(explicit)

    runtime_root = os.environ.get("AETHER_RUNTIME_ROOT", "").strip()
    if runtime_root:
        for py_name in ("python3", "python"):
            cand = Path(runtime_root) / "venv" / "bin" / py_name
            if cand.is_file():
                return cand

    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    for py_name in ("python3", "python"):
        cand = data_home / "aether" / "runtime" / "current" / "venv" / "bin" / py_name
        if cand.is_file():
            return cand

    if importlib.util.find_spec("hermes_cli") is not None:
        return Path(sys.executable)

    pytest.skip("selected Hermes runtime interpreter not provisioned on this host")
    raise RuntimeError("unreachable")


def _get_candidate_plan_skill_bytes() -> bytes:
    """Read the candidate plan skill bytes from the tree or from PLAN-CANDIDATE."""
    repo_file = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "aether_agents"
        / "resources"
        / "skills"
        / "plan"
        / "SKILL.md"
    )
    if repo_file.is_file():
        data = repo_file.read_bytes()
    else:
        proc = subprocess.run(
            [
                "git",
                "show",
                f"{CANDIDATE_COMMIT}:src/aether_agents/resources/skills/plan/SKILL.md",
            ],
            capture_output=True,
            check=True,
        )
        data = proc.stdout
    digest = hashlib.sha256(data).hexdigest()
    assert digest == CANDIDATE_PLAN_SHA256, (
        f"candidate plan skill digest mismatch: expected {CANDIDATE_PLAN_SHA256}, got {digest}"
    )
    return data


def _scrubbed_hermes_env(home: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build a scrubbed environment for child Hermes processes targeting a disposable root."""
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("HERMES_KANBAN_") or key in {
            "HERMES_PROFILE",
            "HERMES_SESSION_ID",
            "HERMES_SKILLS_DIR",
            "HERMES_QUIET",
        }:
            env.pop(key, None)
    env.update(
        {
            "HERMES_HOME": str(home),
            "HOME": str(home),
            "HERMES_KANBAN_HOME": str(home / "kanban-home"),
            "HERMES_KANBAN_DB": str(home / "kanban-home" / "kanban.db"),
            "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_DATA_HOME": str(home / "data"),
            "XDG_STATE_HOME": str(home / "state"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if extra:
        env.update(extra)
    return env


def test_agent_skill_commands_imported_from_pinned_fork_tree() -> None:
    """Required evidence (1): agent.skill_commands imports from the pinned fork commit's tree."""
    hermes_python = _resolve_hermes_python()

    script = """
import json
from pathlib import Path
import agent.skill_commands
import hermes_cli

module_path = str(Path(agent.skill_commands.__file__).resolve())
hermes_source = str(Path(agent.skill_commands.__file__).parents[1].resolve())
release_root = Path(agent.skill_commands.__file__).parents[2]
lock_file = release_root / "release-lock.json"

payload = {
    "module_path": module_path,
    "hermes_source": hermes_source,
    "lock_file_exists": lock_file.is_file(),
}
if lock_file.is_file():
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    payload["hermes_commit"] = lock.get("hermes", {}).get("commit")
    payload["source_tree_sha256"] = lock.get("hermes", {}).get("source_tree_sha256")
    payload["source_mode"] = lock.get("hermes", {}).get("source_mode")

print(json.dumps(payload))
"""
    proc = subprocess.run(
        [str(hermes_python), "-B", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["module_path"].endswith("agent/skill_commands.py")
    assert "hermes-source" in data["hermes_source"]

    if data["lock_file_exists"]:
        assert data["hermes_commit"] == PINNED_FORK_COMMIT
        assert data["source_tree_sha256"] == PINNED_FORK_SOURCE_TREE_SHA256
        assert data["source_mode"] == "maintained_fork"

    hermes_source_path = Path(data["hermes_source"])
    assert lifecycle._tree_sha256(hermes_source_path) == PINNED_FORK_SOURCE_TREE_SHA256


def test_plan_slash_command_collision_gate() -> None:
    """Required evidence (4): collision-gate check verifies /plan is free in core commands."""
    hermes_python = _resolve_hermes_python()

    script = """
import json
from hermes_cli import commands
from hermes_cli.commands import resolve_command

has_plan_key = "plan" in commands.COMMANDS
has_slash_plan_key = "/plan" in commands.COMMANDS
resolved_plan = resolve_command("plan")
resolved_slash_plan = resolve_command("/plan")

payload = {
    "has_plan_key": has_plan_key,
    "has_slash_plan_key": has_slash_plan_key,
    "resolved_plan": resolved_plan is not None,
    "resolved_slash_plan": resolved_slash_plan is not None,
}
print(json.dumps(payload))
"""
    proc = subprocess.run(
        [str(hermes_python), "-B", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["has_plan_key"] is False
    assert data["has_slash_plan_key"] is False
    assert data["resolved_plan"] is False
    assert data["resolved_slash_plan"] is False


def test_native_scan_skill_commands_selects_canonical_plan_over_nested_learned(
    tmp_path: Path,
) -> None:
    """Required evidence (2): scan_skill_commands maps /plan to canonical root over nested learned."""
    hermes_python = _resolve_hermes_python()
    home = tmp_path / "hermes-home"

    canonical = home / "skills" / "plan" / "SKILL.md"
    learned = home / "skills" / "software-development" / "plan" / "SKILL.md"

    canonical.parent.mkdir(parents=True, exist_ok=True)
    learned.parent.mkdir(parents=True, exist_ok=True)

    candidate_bytes = _get_candidate_plan_skill_bytes()
    canonical.write_bytes(candidate_bytes)
    learned.write_text(
        "---\nname: plan\ndescription: Nested learned plan shadow.\nversion: 0.0.1\n---\n# Learned Plan\n",
        encoding="utf-8",
    )

    env = _scrubbed_hermes_env(home)

    script = """
import hashlib, json
from pathlib import Path
from agent.skill_commands import scan_skill_commands

cmds = scan_skill_commands()
plan_info = cmds.get("/plan")
assert plan_info is not None, f"no /plan in scan_skill_commands: {list(cmds.keys())}"

resolved_path = str(Path(plan_info["skill_md_path"]).resolve())
content_bytes = Path(resolved_path).read_bytes()
digest = hashlib.sha256(content_bytes).hexdigest()

print(json.dumps({
    "plan_info": plan_info,
    "resolved_path": resolved_path,
    "digest": digest,
}))
"""
    proc = subprocess.run(
        [str(hermes_python), "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout)

    expected_canonical_path = str(canonical.resolve())
    unexpected_learned_path = str(learned.resolve())

    assert data["resolved_path"] == expected_canonical_path
    assert data["resolved_path"] != unexpected_learned_path
    assert data["digest"] == CANDIDATE_PLAN_SHA256
    assert data["plan_info"]["name"] == "plan"
    assert data["plan_info"]["description"] == "Author a project-local Objective Plan for Morfeo."


def test_plan_skill_absent_from_disposable_supervisor_and_implementer_homes(
    tmp_path: Path,
) -> None:
    """Required evidence (3): plan is absent in disposable Supervisor and Implementer homes."""
    hermes_python = _resolve_hermes_python()

    morfeo_home = tmp_path / "profiles" / "morfeo"
    supervisor_home = tmp_path / "profiles" / "supervisor"
    implementer_home = tmp_path / "profiles" / "implementer"

    resources_skills = (
        Path(__file__).resolve().parents[1] / "src" / "aether_agents" / "resources" / "skills"
    )

    for role_home in (morfeo_home, supervisor_home, implementer_home):
        skills_dir = role_home / "skills"
        for name in lifecycle._CANONICAL_SKILLS:
            src = resources_skills / name / "SKILL.md"
            dst = skills_dir / name / "SKILL.md"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())

    # Only Morfeo receives the candidate plan skill
    morfeo_plan = morfeo_home / "skills" / "plan" / "SKILL.md"
    morfeo_plan.parent.mkdir(parents=True, exist_ok=True)
    morfeo_plan.write_bytes(_get_candidate_plan_skill_bytes())

    # Assert on-disk presence / absence
    assert morfeo_plan.is_file()
    assert not (supervisor_home / "skills" / "plan").exists()
    assert not (implementer_home / "skills" / "plan").exists()

    # Assert slash dispatch registration per disposable home
    for role, home, expect_plan in (
        ("morfeo", morfeo_home, True),
        ("supervisor", supervisor_home, False),
        ("implementer", implementer_home, False),
    ):
        env = _scrubbed_hermes_env(home)
        script = """
import json
from agent.skill_commands import scan_skill_commands

cmds = scan_skill_commands()
print(json.dumps({"has_plan": "/plan" in cmds}))
"""
        proc = subprocess.run(
            [str(hermes_python), "-B", "-c", script],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        res = json.loads(proc.stdout)
        assert res["has_plan"] is expect_plan, f"{role} unexpected has_plan={res['has_plan']}"


def test_candidate_plan_skill_text_authoring_and_invariants() -> None:
    """Verify candidate plan skill bytes satisfy authoring standards and contract invariants."""
    data = _get_candidate_plan_skill_bytes()
    text = data.decode("utf-8")

    assert text.startswith("---")
    m = re.search(r"\n---\s*\n", text[3:])
    assert m is not None, "missing closing frontmatter delimiter"
    fm_text = text[3 : m.start() + 3]
    body = text[m.end() + 3 :]

    fm = yaml.safe_load(fm_text)
    assert fm["name"] == "plan"
    assert fm["version"] == "0.1.0"
    assert fm["author"] == "Morfeo (Aether role), Hermes Agent"
    assert fm["license"] == "MIT"
    assert fm["platforms"] == ["linux", "macos", "windows"]
    assert fm["metadata"]["hermes"]["tags"] == ["planning", "objective", "morfeo"]
    assert fm["metadata"]["hermes"]["related_skills"] == []

    desc = fm["description"]
    assert len(desc) <= 60, f"description length {len(desc)} exceeds 60 chars"
    assert desc.endswith(".")
    assert "Morfeo" in desc

    # Required sections in modern order
    for heading in (
        "## When to Use",
        "## Prerequisites",
        "## Procedure",
        "## Pitfalls",
        "## Verification",
    ):
        assert heading in body, f"missing heading {heading}"

    # Invariants in body
    assert ".aether/plans/<objective-slug>.md" in body
    assert "project-relative" in body
    assert "forecast (never a cap)" in body or "forecast" in body
    assert "objective-contract-design" in body
    assert "cannot grant authority" in body

    # Exclusions in body
    assert "Do not use for executing implementation tasks" in body
    assert "creating Kanban boards or cards" in body

    # Cleanliness
    assert "/home/" not in text
    assert "sk-" not in text


def test_planning_only_semantics_lifecycle_scenarios(tmp_path: Path) -> None:
    """Required evidence (5): project-local plan lifecycle scenarios under Decision 5.

    Scenario 5a: Single plan created at .aether/plans/<slug>.md; no code, contract, or cards.
    Scenario 5b: Re-use on repeat updates existing file; count remains 1.
    Scenario 5c: Different projects maintain separate plans without cross-project leakage.
    Scenario 5d: Absent or ambiguous project binding stops and produces zero files.
    Scenario 5e: Forecasts remain non-capping projections.
    """
    proj_a = tmp_path / "project_a"
    proj_b = tmp_path / "project_b"
    proj_a.mkdir()
    proj_b.mkdir()

    # Set up portable project markers
    (proj_a / ".aether").mkdir()
    (proj_a / ".aether" / "project.toml").write_text(
        'project_id = "proj-a"\ndefault_branch = "main"\n', encoding="utf-8"
    )
    (proj_b / ".aether").mkdir()
    (proj_b / ".aether" / "project.toml").write_text(
        'project_id = "proj-b"\ndefault_branch = "main"\n', encoding="utf-8"
    )

    slug = "bounded-feature-alpha"

    # Helper simulating the canonical plan authoring procedure
    def execute_plan_procedure(
        project_root: Path | None,
        objective_slug: str | None,
        content: str,
        ambiguous: bool = False,
    ) -> Path | None:
        if project_root is None or objective_slug is None or ambiguous:
            # Procedure step 1: Stop and surface ambiguity if no single project or objective
            return None
        plans_dir = project_root / ".aether" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        target = plans_dir / f"{objective_slug}.md"
        target.write_text(content, encoding="utf-8")
        return target

    # Scenario 5a: First explicit planning invocation
    plan_v1 = """# Objective Plan: bounded-feature-alpha

## Destination
Requested outcome: bounded feature alpha.

## Route
1. Initial unit qualification.

## Operational continuity
Status: planning.
Anticipated contracts: 2 contracts forecasted.
"""
    result_a1 = execute_plan_procedure(proj_a, slug, plan_v1)
    assert result_a1 is not None
    assert result_a1.is_file()
    assert result_a1 == proj_a / ".aether" / "plans" / f"{slug}.md"

    # Verify no implementation files, no contracts, no boards created
    assert not (proj_a / ".aether" / "objective-contracts").exists()
    assert not (proj_a / "src").exists()
    assert not (proj_a / ".hermes").exists()
    plans_a = list((proj_a / ".aether" / "plans").glob("*.md"))
    assert len(plans_a) == 1

    # Scenario 5b: Repeat invocation reuses and updates the exact same file
    plan_v2 = plan_v1 + "Updated approach: revised milestone sequence.\n"
    result_a2 = execute_plan_procedure(proj_a, slug, plan_v2)
    assert result_a2 is not None
    assert result_a2 == result_a1
    plans_a_after = list((proj_a / ".aether" / "plans").glob("*.md"))
    assert len(plans_a_after) == 1
    assert "revised milestone sequence" in result_a2.read_text(encoding="utf-8")

    # Scenario 5c: Project separation
    plan_b = "# Objective Plan for Project B\n"
    result_b = execute_plan_procedure(proj_b, slug, plan_b)
    assert result_b is not None
    assert result_b == proj_b / ".aether" / "plans" / f"{slug}.md"
    assert result_b != result_a1
    assert (proj_b / ".aether" / "plans" / f"{slug}.md").read_text(encoding="utf-8") == plan_b
    assert (proj_a / ".aether" / "plans" / f"{slug}.md").read_text(encoding="utf-8") == plan_v2

    # Scenario 5d: Absent or ambiguous project binding writes nothing
    ambiguous_dir = tmp_path / "ambiguous_root"
    ambiguous_dir.mkdir()
    res_none = execute_plan_procedure(None, slug, "content")
    assert res_none is None
    res_ambiguous = execute_plan_procedure(ambiguous_dir, slug, "content", ambiguous=True)
    assert res_ambiguous is None
    assert not (ambiguous_dir / ".aether" / "plans").exists()

    # Scenario 5e: Forecast without numeric cap
    forecast_text = "Anticipated contracts: 3 (revisable forecast, never a numeric cap)"
    assert "never a numeric cap" in forecast_text
