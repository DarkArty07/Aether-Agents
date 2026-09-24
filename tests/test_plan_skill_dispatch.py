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
import tempfile
from pathlib import Path

import pytest
import yaml

from aether_agents import lifecycle

CANDIDATE_COMMIT = "3da14572232775aedbc23b38393227cd62ed5ebc"
CANDIDATE_PLAN_SHA256 = "b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d"
PINNED_FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
PINNED_FORK_SOURCE_TREE_SHA256 = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"
FORK_BUNDLED_PLAN_SHA256 = "7513da40fbbbf899bc94ffdf05921a8187866745e67e2d81a55790b70daca72c"


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


def _get_candidate_role_skills() -> dict[str, tuple[str, ...]]:
    """Derive the per-role skill inventory from candidate distribution or git archive fallback."""
    if hasattr(lifecycle, "_CANDIDATE_ROLE_SKILLS"):
        raw = getattr(lifecycle, "_CANDIDATE_ROLE_SKILLS")
        return {r: tuple(raw[r]) for r in ("morfeo", "supervisor", "implementer")}
    if hasattr(lifecycle.LifecycleManager, "_role_skills"):
        mgr_fn = getattr(lifecycle.LifecycleManager, "_role_skills")
        return {r: tuple(mgr_fn(r)) for r in ("morfeo", "supervisor", "implementer")}

    with tempfile.TemporaryDirectory() as td:
        tar_proc = subprocess.Popen(
            ["git", "archive", CANDIDATE_COMMIT, "src/aether_agents"],
            stdout=subprocess.PIPE,
        )
        subprocess.run(["tar", "-x", "-C", td], stdin=tar_proc.stdout, check=True)
        tar_proc.wait()

        script = """
import json, sys
sys.path.insert(0, sys.argv[1])
from aether_agents.lifecycle import LifecycleManager
res = {role: list(LifecycleManager._role_skills(role)) for role in ("morfeo", "supervisor", "implementer")}
print(json.dumps(res))
"""
        proc = subprocess.run(
            [sys.executable, "-B", "-c", script, str(Path(td) / "src")],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        return {k: tuple(v) for k, v in data.items()}


def _get_fork_bundled_plan_skill_bytes() -> bytes | None:
    """Resolve the fork's bundled Plan-Mode skill bytes if present in the runtime tree."""
    hermes_python = _resolve_hermes_python()
    for cand in (
        hermes_python.parents[2]
        / "hermes-source"
        / "skills"
        / "software-development"
        / "plan"
        / "SKILL.md",
        Path(__file__).resolve().parents[1]
        / "hermes-source"
        / "skills"
        / "software-development"
        / "plan"
        / "SKILL.md",
    ):
        if cand.is_file():
            return cand.read_bytes()
    return None


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
    """Required evidence (1): agent.skill_commands imports from the pinned fork commit's tree.

    Two lanes can satisfy this node and they carry different obligations:

    * a provisioned maintained-fork release runtime or an explicit
      ``AETHER_HERMES_PYTHON``/``AETHER_RUNTIME_ROOT`` override -- the selected fork,
      where the exact fork commit, the ``maintained_fork`` source mode and the fork
      source-tree digest are all required;
    * the repository's policy lane, which provisions only the authenticated **public**
      baseline checkout on ``AETHER_EXACT_HERMES_CHECKOUT`` (``hermes-exact``). That
      checkout is the reference baseline, never the selected fork, so demanding the fork
      leaf name or the fork digest from it would assert a false identity. This node then
      proves what that lane can actually prove: the imported ``agent.skill_commands``
      really is that authenticated baseline tree, while fork-identity assertions stay
      gated on the fork lane.
    """
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

    hermes_source_path = Path(data["hermes_source"])
    if data["lock_file_exists"]:
        # A provisioned release runtime names its own identity; the lock is authoritative.
        assert data["hermes_commit"] == PINNED_FORK_COMMIT
        assert data["source_tree_sha256"] == PINNED_FORK_SOURCE_TREE_SHA256
        assert data["source_mode"] == "maintained_fork"
        assert lifecycle._tree_sha256(hermes_source_path) == PINNED_FORK_SOURCE_TREE_SHA256
        return

    # No release lock: distinguish an authenticated public-baseline checkout from the
    # selected fork. Never infer the fork from a directory leaf name.
    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT", "").strip()
    if configured:
        checkout = lifecycle.verify_clean_checkout(Path(configured))
        assert checkout.clean is True
        assert hermes_source_path.resolve() == Path(configured).resolve()
        assert (
            lifecycle._tree_sha256(hermes_source_path)
            == lifecycle._tree_sha256(Path(configured))
        )
        return

    hermes_repository = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=hermes_source_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if "aether-hermes" in hermes_repository:
        # The maintained fork without a release lock: the fork pin is the whole claim.
        assert lifecycle._tree_sha256(hermes_source_path) == PINNED_FORK_SOURCE_TREE_SHA256
        return

    pytest.fail(
        "imported agent.skill_commands is neither the pinned maintained fork nor an "
        f"authenticated public baseline checkout (source={hermes_source_path}, "
        f"repository={hermes_repository or 'unknown'})"
    )


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

    # 1. Derive per-role inventory from candidate distribution
    role_skills = _get_candidate_role_skills()
    assert "plan" in role_skills["morfeo"]
    assert "plan" not in role_skills["supervisor"]
    assert "plan" not in role_skills["implementer"]
    assert len(role_skills["morfeo"]) == 10
    assert len(role_skills["supervisor"]) == 9
    assert len(role_skills["implementer"]) == 9

    # 2. Materialize homes according to the candidate role-scoping inventory
    for role, home in (
        ("morfeo", morfeo_home),
        ("supervisor", supervisor_home),
        ("implementer", implementer_home),
    ):
        skills_dir = home / "skills"
        for name in role_skills[role]:
            dst = skills_dir / name / "SKILL.md"
            dst.parent.mkdir(parents=True, exist_ok=True)
            if name == "plan":
                dst.write_bytes(_get_candidate_plan_skill_bytes())
            else:
                src = resources_skills / name / "SKILL.md"
                dst.write_bytes(src.read_bytes())

    # 3. Assert on-disk presence / absence of the managed root resource
    assert (morfeo_home / "skills" / "plan" / "SKILL.md").is_file()
    assert not (supervisor_home / "skills" / "plan").exists()
    assert not (implementer_home / "skills" / "plan").exists()

    # 4. In minimal managed homes (no bundled skills present):
    # Morfeo registers /plan to the managed root resource.
    # Supervisor and Implementer do not register /plan at all (has_plan=False).
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
plan_cmd = cmds.get("/plan")
print(json.dumps({
    "has_plan": plan_cmd is not None,
    "path": plan_cmd["skill_md_path"] if plan_cmd else None,
}))
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
        if expect_plan:
            assert res["path"] == str((morfeo_home / "skills" / "plan" / "SKILL.md").resolve())

    # 5. In realistic profile homes including the fork's bundled plan skill:
    # (skills/software-development/plan/SKILL.md shipped by the pinned fork runtime)
    fork_plan_bytes = _get_fork_bundled_plan_skill_bytes()
    if fork_plan_bytes is not None:
        assert hashlib.sha256(fork_plan_bytes).hexdigest() == FORK_BUNDLED_PLAN_SHA256
        for home in (morfeo_home, supervisor_home, implementer_home):
            bundled_path = home / "skills" / "software-development" / "plan" / "SKILL.md"
            bundled_path.parent.mkdir(parents=True, exist_ok=True)
            bundled_path.write_bytes(fork_plan_bytes)

        # Morfeo: canonical root skills/plan/SKILL.md wins over the bundled shadow
        env_morfeo = _scrubbed_hermes_env(morfeo_home)
        proc_m = subprocess.run(
            [str(hermes_python), "-B", "-c", script],
            env=env_morfeo,
            capture_output=True,
            text=True,
            check=True,
        )
        res_m = json.loads(proc_m.stdout)
        assert res_m["has_plan"] is True
        assert res_m["path"] == str((morfeo_home / "skills" / "plan" / "SKILL.md").resolve())

        # Supervisor / Implementer: managed root is absent, so /plan resolves to bundled skill
        for role, home in (("supervisor", supervisor_home), ("implementer", implementer_home)):
            env_role = _scrubbed_hermes_env(home)
            proc_r = subprocess.run(
                [str(hermes_python), "-B", "-c", script],
                env=env_role,
                capture_output=True,
                text=True,
                check=True,
            )
            res_r = json.loads(proc_r.stdout)
            assert res_r["has_plan"] is True
            expected_bundled = str(
                (home / "skills" / "software-development" / "plan" / "SKILL.md").resolve()
            )
            assert res_r["path"] == expected_bundled
            # Managed root resource remains absent
            assert not (home / "skills" / "plan").exists()


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


def test_decision_5_planning_only_semantics_static_specification_checks() -> None:
    """Required evidence (5): static specification checks for Decision 5 planning semantics.

    Validates that the candidate plan skill artifact explicitly specifies:
    - 5a: Project-local destination at .aether/plans/<objective-slug>.md; no code/boards/cards.
    - 5b: Reuse and in-place update of existing file; no duplicates.
    - 5c: Project separation; no global or framework-default leakage.
    - 5d: Refusal/stop on absent or ambiguous project binding.
    - 5e: Forecasts remain non-capping projections rather than numeric quotas.
    """
    data = _get_candidate_plan_skill_bytes()
    text = data.decode("utf-8")
    assert len(text) == 3765
    norm = re.sub(r"\s+", " ", text)

    # 5a: Single plan created at .aether/plans/<objective-slug>.md; planning-only boundary
    assert ".aether/plans/<objective-slug>.md" in norm
    assert (
        "without writing implementation code, dispatching workers, or creating task cards." in norm
    )
    assert "Verify that no task cards, boards, or code edits were created during planning." in norm

    # 5b: Reuse and update existing file across invocations
    assert (
        "Reuse and update the existing file across invocations for the same objective; never create duplicate files or global plans."
        in norm
    )

    # 5c: Project separation and avoidance of global/framework default locations
    assert "inside the explicitly resolved project" in norm
    assert (
        "Writing plans to global, user home, or framework default locations instead of the project-local"
        in norm
    )

    # 5d: Stop and surface ambiguity if no single project or objective can be identified
    assert "Stop and surface ambiguity if no single project or objective can be identified." in norm

    # 5e: Anticipated contracts as revisable forecast, never a numeric cap
    assert "Treat anticipated Objective Contracts as a revisable forecast (never a cap)." in norm
    assert "not forced by a predetermined quota." in norm
    assert "Treating anticipated Objective Contracts as a numerical cap or mandatory quota." in norm
