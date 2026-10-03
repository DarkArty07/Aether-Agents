"""Context and skills builder for Claude Code Implementer attempts.

Builds the appended system prompt file, skills plugin directory,
and initial user prompt per specs/external-implementer-harness/plan.md §3.8.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Sequence

from aether_agents.lifecycle import _CANDIDATE_ROLE_SKILLS

TOOL_EQUIVALENCE_TABLE = """# Tool Equivalence Table

The following table maps Hermes tool names used in role instructions, skills,
and guidance to their Claude Code equivalents in this attempt:

| Hermes Tool | Claude Code Equivalent | Notes |
| --- | --- | --- |
| `terminal` | `Bash` | Shell execution, builds, git, tests |
| `read_file` | `Read` | File inspection |
| `write_file` | `Write` | Full file creation and overwrite |
| `patch` | `Edit` / `MultiEdit` | Targeted file modifications |
| `search_files` | `Grep` / `Glob` | Pattern search and file discovery |
| `todo` | `TodoWrite` | Tracking task list |
| `delegate_task` | Subagents | Claude Code subagents within the same authority |
| `kanban_show` | `mcp__aether-worker__kanban_show` | Read task full state and prior attempts |
| `kanban_complete` | `mcp__aether-worker__kanban_complete` | Mark task done with summary and metadata |
| `kanban_request_review` | `mcp__aether-worker__kanban_request_review` | Request supervisor/human review |
| `kanban_request_changes` | `mcp__aether-worker__kanban_request_changes` | Reviewer return to implementer |
| `kanban_block` | `mcp__aether-worker__kanban_block` | Record genuine blocker |
| `kanban_comment` | `mcp__aether-worker__kanban_comment` | Append durable comment |
| `kanban_create` | `mcp__aether-worker__kanban_create` | Create kanban child/follow-up task |
| `kanban_heartbeat` | `mcp__aether-worker__kanban_heartbeat` | Signal liveness during long operations |
| `kanban_link` | `mcp__aether-worker__kanban_link` | Add dependency edge between tasks |
| `kanban_attach` | `mcp__aether-worker__kanban_attach` | Attach file artifact by bytes |
| `kanban_attach_url` | `mcp__aether-worker__kanban_attach_url` | Attach file artifact by URL |
| `kanban_attachments` | `mcp__aether-worker__kanban_attachments` | List attached task artifacts |
| `project_knowledge` | `mcp__aether-worker__project_knowledge` | Consult or refresh project graph |
| `work_memory` | `mcp__aether-worker__work_memory` | Project-scoped role experiences |

Tools without an equivalent are unavailable: `execute_code`, `session_search`, `memory`, `clarify`, `web_search`, `web_extract`, `vision_analyze`, `skill_manage`, `skill_view`, `skills_list`, `process`.
"""


def _resources_root() -> Path:
    return Path(__file__).resolve().parent / "resources"


def load_implementer_soul() -> str:
    """Load the Implementer SOUL.md from packaged resources."""
    path = _resources_root() / "profiles" / "implementer" / "SOUL.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def load_implementation_evidence_skill() -> str:
    """Load the implementation-evidence SKILL.md from packaged resources."""
    path = _resources_root() / "skills" / "implementation-evidence" / "SKILL.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def load_runtime_kanban_guidance() -> str:
    """Import KANBAN_GUIDANCE from the executing Hermes installation at run time.

    This guidance is never copied into Aether source.
    """
    try:
        from agent.prompt_builder import KANBAN_GUIDANCE

        return str(KANBAN_GUIDANCE)
    except Exception:
        return ""


def parse_pinned_skills(argv: Sequence[str]) -> list[str]:
    """Parse task-pinned skill names from dispatcher argv (--skills / -s)."""
    skills: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-s", "--skills"):
            if i + 1 < len(argv):
                for part in argv[i + 1].split(","):
                    cleaned = part.strip()
                    if cleaned and cleaned not in skills:
                        skills.append(cleaned)
                i += 2
                continue
        elif arg.startswith("--skills="):
            for part in arg.split("=", 1)[1].split(","):
                cleaned = part.strip()
                if cleaned and cleaned not in skills:
                    skills.append(cleaned)
        i += 1
    return skills


def load_skill_content(
    name: str,
    *,
    hermes_home: Path | None = None,
    workspace: Path | None = None,
) -> str | None:
    """Find and load a skill's SKILL.md text from known locations."""
    candidates: list[Path] = [
        _resources_root() / "skills" / name / "SKILL.md",
    ]
    if hermes_home is not None:
        candidates.extend(
            [
                hermes_home / "skills" / name / "SKILL.md",
                hermes_home / "profiles" / "implementer" / "skills" / name / "SKILL.md",
            ]
        )
    if workspace is not None:
        candidates.extend(
            [
                workspace / ".aether" / "skills" / name / "SKILL.md",
                workspace / ".hermes" / "skills" / name / "SKILL.md",
                workspace / ".agents" / "skills" / name / "SKILL.md",
            ]
        )
    for cand in candidates:
        if cand.is_file():
            try:
                return cand.read_text(encoding="utf-8")
            except OSError:
                continue
    return None


def build_appended_context(
    *,
    task_id: str,
    workspace: Path | str,
    pinned_skills: Sequence[str] = (),
    hermes_home: Path | str | None = None,
) -> str:
    """Assemble the attempt context file per plan §3.8."""
    workspace_path = Path(workspace)
    home_path = Path(hermes_home) if hermes_home else None

    sections: list[str] = []

    # Attempt header
    header = (
        f"# Implementer Task Attempt\n\n"
        f"- **Task ID:** `{task_id}`\n"
        f"- **Workspace:** `{workspace_path}`\n"
        f"- **Delivery rule:** Deliver work solely through native Kanban tools "
        f"(`kanban_complete`, `kanban_request_review`, `kanban_block`).\n"
    )
    sections.append(header)

    # Tool equivalence table
    sections.append(TOOL_EQUIVALENCE_TABLE.strip())

    # Implementer SOUL
    soul = load_implementer_soul()
    if soul:
        sections.append(f"# Role SOUL: Implementer\n\n{soul.strip()}")

    # implementation-evidence skill
    evidence_skill = load_implementation_evidence_skill()
    if evidence_skill:
        sections.append(
            f"# Canonical Procedure: Implementation and Unit Evidence\n\n{evidence_skill.strip()}"
        )

    # Runtime KANBAN_GUIDANCE from Hermes
    guidance = load_runtime_kanban_guidance()
    if guidance:
        sections.append(guidance.strip())

    # Task-pinned skills from --skills
    for skill_name in pinned_skills:
        content = load_skill_content(skill_name, hermes_home=home_path, workspace=workspace_path)
        if content:
            sections.append(f"# Pinned Skill: {skill_name}\n\n{content.strip()}")

    return "\n\n---\n\n".join(sections) + "\n"


def build_skills_plugin(plugin_dir: Path | str) -> Path:
    """Build the per-attempt skills plugin directory per plan §3.8.

    Holds exactly the Implementer role's canonical skill set from lifecycle.py's
    role map at the running release.
    """
    plugin_path = Path(plugin_dir).resolve()
    plugin_path.mkdir(parents=True, exist_ok=True)

    claude_plugin_dir = plugin_path / ".claude-plugin"
    claude_plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_manifest = claude_plugin_dir / "plugin.json"
    manifest_data = {
        "name": "aether-implementer-skills",
        "version": "1.0.0",
        "description": "Aether Implementer canonical skills plugin",
    }
    plugin_manifest.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    skills_root = plugin_path / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    canonical_skills = _CANDIDATE_ROLE_SKILLS.get("implementer", ())
    resources = _resources_root() / "skills"

    for skill_name in canonical_skills:
        src = resources / skill_name / "SKILL.md"
        if src.is_file():
            dest_dir = skills_root / skill_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / "SKILL.md")

    return plugin_path


def build_first_user_message(db_path: Path | str, task_id: str) -> str:
    """Construct the first user message per plan §3.8 over a read-only board connection."""
    resolved_db = Path(db_path).resolve()
    worker_context = ""
    try:
        from hermes_cli.kanban_db import build_worker_context

        # Use read-only sqlite3 URI if possible
        try:
            conn = sqlite3.connect(f"file:{resolved_db}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            conn = sqlite3.connect(str(resolved_db))
        conn.row_factory = sqlite3.Row
        try:
            worker_context = build_worker_context(conn, task_id)
        finally:
            conn.close()
    except Exception as exc:
        worker_context = f"(Unable to read worker context: {exc})"

    return f"Work Aether Kanban task {task_id}.\n\n{worker_context}"
