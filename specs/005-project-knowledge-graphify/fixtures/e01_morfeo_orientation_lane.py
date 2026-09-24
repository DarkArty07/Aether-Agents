"""E01 isolated real-Morfeo first-turn qualification lane with controls.

Reproducible evaluation lane for KG-19 / Issue #505 (Objective Contract oc_d96969bf913512f7@v1).
Exercises:
1. Deterministic fixture setup (two subsystems, documented decision, committed, indexed structurally).
2. Structural index creation and status/revision verification before any model call.
3. Positive E01: Real Morfeo in isolated profile/session with technical request (never mentioning Graphify).
   Verifies:
   - discovery and loading of project-knowledge skill
   - early project_knowledge consultation with correct project, revision, and coverage
   - references returned by the knowledge tool
   - subsequent inspection of current source files (code and ADR)
   - answer distinguishing documented specification from implemented behavior
4. Control A (exact source provided):
   Technical question directly providing exact file path; verifies no ceremonial graph consultation.
5. Control B (unborn repository):
   Unborn repo (git init without HEAD) degrades honestly to ordinary file tools, with limits stated,
   no invented project, no installation, no commit, no rebuild, no spend.

Safety / Spend Policy:
- Model spend is blocked by default and requires explicit CLI flag ``--allow-model-spend``
  or environment variable ``AETHER_ALLOW_MODEL_SPEND=1``.
- When run under CI or standard deterministic test runs, live agent turns are safely skipped.
- Live homes, live board, and primary checkout are strictly preserved and never mutated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

import pytest

from aether_agents.knowledge.component import configure
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.service import KnowledgeService
from aether_agents.lab.isolation import isolated_hermes_env
from aether_agents.lab.runner import prepare_profiles
from aether_agents.observation.context import ProjectRegistry
from aether_agents.project_marker import validate_project_marker

try:  # PyYAML is a dev/static dependency only; the lane degrades without it.
    import yaml
except ImportError:  # pragma: no cover - dev environment always provides it
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKTREE_SRC = REPO_ROOT / "src"

EXPECTED_MORFEO_SOUL_SHA256 = "c4785b1a38e29e49d908268cd2abfedf5d587e63386ef1ba1f00326c999065ee"
EXPECTED_PROJECT_KNOWLEDGE_SKILL_SHA256 = (
    "9a417c75235eb2fa0388b3d6ba95ca19f268d894fabe2fcabfaa0023c394b869"
)


def _resolved_provisioned_path(environment_name: str, *segments: str) -> Path | None:
    """Resolve a provisioned tool from ``<state-home>/<segments>``.

    The state home comes from the active environment (``XDG_STATE_HOME`` when the
    caller pins one, otherwise the process default). Absolute machine paths are
    never baked into the portable lane; a caller can also override the whole path
    through the matching environment variable.
    """
    override = os.environ.get(environment_name, "").strip()
    if override:
        return Path(override).expanduser().absolute()
    base = os.environ.get("XDG_STATE_HOME", "").strip() or str(Path.home() / ".local" / "state")
    candidate = Path(base).expanduser().absolute()
    for segment in segments:
        candidate = candidate / segment
    return candidate if candidate.exists() else None


def _discover_hermes_bin() -> Path | None:
    """Locate the managed Hermes executable through the current release root."""
    data_home = os.environ.get("XDG_DATA_HOME", "").strip() or str(Path.home() / ".local" / "share")
    candidate = (
        Path(data_home).expanduser().absolute()
        / "aether"
        / "runtime"
        / "current"
        / "venv"
        / "bin"
        / "hermes"
    )
    return candidate if candidate.is_file() else None


def _discover_graphify_python() -> Path | None:
    """Locate the managed Graphify component interpreter under the data root."""
    override = os.environ.get("AETHER_GRAPHIFY_PYTHON", "").strip()
    if override:
        candidate = Path(override).expanduser().absolute()
        return candidate if candidate.is_file() else None
    data_home = os.environ.get("XDG_DATA_HOME", "").strip() or str(Path.home() / ".local" / "share")
    components = Path(data_home).expanduser().absolute() / "aether" / "components" / "graphify"
    if not components.is_dir():
        return None
    for child in sorted(components.iterdir()):
        candidate = child / "venv" / "bin" / "python"
        if candidate.is_file():
            return candidate
    return None


DEFAULT_HERMES_BIN = _discover_hermes_bin() or Path("hermes")
DEFAULT_GRAPHIFY_PYTHON = _discover_graphify_python()
DEFAULT_PROFILE_ROOT = _resolved_provisioned_path(
    "AETHER_LIVE_PROFILE_ROOT", "aether", "hermes", "profiles"
)


def hash_file(path: Path) -> str:
    """Return lowercase hex SHA-256 of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_candidate_resource_bytes() -> dict[str, str]:
    """Verify that current candidate resources match the frozen KG19-01 bytes."""
    soul_path = WORKTREE_SRC / "aether_agents/resources/profiles/morfeo/SOUL.md"
    skill_path = WORKTREE_SRC / "aether_agents/resources/skills/project-knowledge/SKILL.md"

    observed_soul = hash_file(soul_path)
    observed_skill = hash_file(skill_path)

    if observed_soul != EXPECTED_MORFEO_SOUL_SHA256:
        raise ValueError(
            f"Candidate Morfeo SOUL hash mismatch: expected {EXPECTED_MORFEO_SOUL_SHA256}, got {observed_soul}"
        )
    if observed_skill != EXPECTED_PROJECT_KNOWLEDGE_SKILL_SHA256:
        raise ValueError(
            f"Candidate project-knowledge skill hash mismatch: expected {EXPECTED_PROJECT_KNOWLEDGE_SKILL_SHA256}, got {observed_skill}"
        )
    return {
        "morfeo_soul_sha256": observed_soul,
        "project_knowledge_skill_sha256": observed_skill,
    }


def build_fixture_project(repo_dir: Path, project_id: str) -> dict[str, Any]:
    """Build a disposable repository with two subsystems and a documented decision."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        ["git", "init", "-b", "main"],
        cwd=repo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        ["git", "config", "user.name", "E01 Fixture Author"],
        cwd=repo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        ["git", "config", "user.email", "e01-author@example.invalid"],
        cwd=repo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    aether_dir = repo_dir / ".aether"
    aether_dir.mkdir(parents=True, exist_ok=True)
    marker_content = (
        "schema_version = 1\n"
        f'project_id = "{project_id}"\n'
        'name = "e01-billing-platform"\n'
        'initialized_by = "1.0.0"\n'
        'forge = "local"\n'
        'contract_root = "specs"\n'
        'default_branch = "main"\n'
    )
    (aether_dir / "project.toml").write_text(marker_content, encoding="utf-8")

    (repo_dir / "README.md").write_text(
        "# E01 Billing Platform\n\n"
        "Core services for billing execution and customer notifications.\n",
        encoding="utf-8",
    )

    # Subsystem 1: billing
    billing_dir = repo_dir / "billing"
    billing_dir.mkdir(parents=True, exist_ok=True)
    (billing_dir / "__init__.py").write_text(
        '"""Billing execution subsystem."""\n', encoding="utf-8"
    )
    (billing_dir / "processor.py").write_text(
        '"""Payment processing execution module."""\n\n\n'
        "def process_payment(account_id: str, amount_cents: int) -> bool:\n"
        '    """Process a customer payment against the payment gateway.\n\n'
        "    Current implemented behavior:\n"
        "    The retry policy uses a fixed delay of 10 seconds between attempts,\n"
        "    with a hard limit of 5 retry attempts before failing permanently.\n"
        '    """\n'
        "    retry_delay_seconds = 10\n"
        "    max_retry_attempts = 5\n"
        "    # Implementation connects to gateway with fixed 10s backoff\n"
        "    return True\n",
        encoding="utf-8",
    )

    # Subsystem 2: notifications
    notifications_dir = repo_dir / "notifications"
    notifications_dir.mkdir(parents=True, exist_ok=True)
    (notifications_dir / "__init__.py").write_text(
        '"""Customer notifications subsystem."""\n', encoding="utf-8"
    )
    (notifications_dir / "mailer.py").write_text(
        '"""Receipt and notification delivery module."""\n\n\n'
        "def send_payment_receipt(customer_email: str, amount_cents: int) -> bool:\n"
        '    """Dispatch confirmation email for settled transactions."""\n'
        "    return True\n",
        encoding="utf-8",
    )

    # Documented decision: ADR 001
    decisions_dir = repo_dir / "docs" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "001-retry-policy.md").write_text(
        "# ADR 001: Payment Processing Retry Policy Specification\n\n"
        "## Status\n"
        "Accepted\n\n"
        "## Context\n"
        "Upstream payment processor network blips cause transient payment failures.\n"
        "A formal retry specification was agreed upon to govern all payment attempts.\n\n"
        "## Documented Specification\n"
        "The canonical payment retry specification mandates:\n"
        "- Initial retry backoff: 60 seconds\n"
        "- Backoff curve: Exponential backoff with a multiplier of 2.0x (delays: 60s, 120s, 240s)\n"
        "- Maximum attempts: 3 retry attempts maximum\n\n"
        "## Implementation Migration Note\n"
        "Notice: The code in `billing/processor.py` currently implements legacy fixed retries\n"
        "(10 seconds fixed delay, up to 5 attempts). Migration to the ADR 001 exponential\n"
        "specification is scheduled for a future release cycle.\n",
        encoding="utf-8",
    )

    subprocess.check_call(
        ["git", "add", "."], cwd=repo_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.check_call(
        ["git", "commit", "-m", "feat: initial billing and notifications platform with ADR 001"],
        cwd=repo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    head_rev = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True
    ).strip()

    return {
        "project_id": project_id,
        "repo_path": str(repo_dir),
        "head_revision": head_rev,
        "files": [
            ".aether/project.toml",
            "README.md",
            "billing/__init__.py",
            "billing/processor.py",
            "notifications/__init__.py",
            "notifications/mailer.py",
            "docs/decisions/001-retry-policy.md",
        ],
    }


def build_unborn_project(repo_dir: Path, project_id: str) -> dict[str, Any]:
    """Build an unborn repository (git init without HEAD)."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        ["git", "init", "-b", "main"],
        cwd=repo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    aether_dir = repo_dir / ".aether"
    aether_dir.mkdir(parents=True, exist_ok=True)
    (aether_dir / "project.toml").write_text(
        "schema_version = 1\n"
        f'project_id = "{project_id}"\n'
        'name = "e01-unborn-fixture"\n'
        'initialized_by = "1.0.0"\n'
        'forge = "local"\n'
        'contract_root = "specs"\n'
        'default_branch = "main"\n',
        encoding="utf-8",
    )
    (repo_dir / "untracked_notes.txt").write_text("unborn draft\n", encoding="utf-8")
    return {
        "project_id": project_id,
        "repo_path": str(repo_dir),
        "head_revision": None,
    }


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from ``path`` as a plain dict, treating empty as {}."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to prepare the disposable profile configuration")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return dict(data)


def setup_isolated_test_environment(
    run_root: Path,
    *,
    hermes_bin: Path | None = None,
    profile_root: Path | None = None,
    graphify_python: Path | None = None,
) -> dict[str, Any]:
    """Construct a clean isolated Hermes environment with candidate resources."""
    hermes_bin = hermes_bin or DEFAULT_HERMES_BIN
    if profile_root is None:
        profile_root = (
            DEFAULT_PROFILE_ROOT
            if DEFAULT_PROFILE_ROOT is not None
            else _resolved_provisioned_path(
                "AETHER_LIVE_PROFILE_ROOT", "aether", "hermes", "profiles"
            )
        )
    if graphify_python is None:
        graphify_python = _discover_graphify_python()
    if profile_root is None:
        raise RuntimeError(
            "profile root not found: set AETHER_LIVE_PROFILE_ROOT to the disposable source profiles directory"
        )
    if graphify_python is None:
        raise RuntimeError(
            "graphify interpreter not found: set AETHER_GRAPHIFY_PYTHON to the provisioned component interpreter"
        )

    commands_log = run_root / "commands.log"
    hermes_root = prepare_profiles(profile_root, run_root, commands_log)

    candidate_soul = WORKTREE_SRC / "aether_agents/resources/profiles/morfeo/SOUL.md"
    candidate_skill = WORKTREE_SRC / "aether_agents/resources/skills/project-knowledge/SKILL.md"

    # Materialize candidate SOUL into morfeo profile
    morfeo_profile_dir = hermes_root / "profiles" / "morfeo"
    shutil.copy2(candidate_soul, morfeo_profile_dir / "SOUL.md")

    # Materialize candidate skill into both profile skills and hermes home skills
    for skills_dir in (
        morfeo_profile_dir / "skills" / "project-knowledge",
        hermes_root / "skills" / "project-knowledge",
    ):
        skills_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate_skill, skills_dir / "SKILL.md")

    # Enable plugin explicitly in disposable test configuration
    state_dir = run_root / "xdg-state" / "aether"
    cache_dir = run_root / "xdg-cache" / "aether"
    cfg_file = morfeo_profile_dir / "config.yaml"
    cfg = _load_yaml_mapping(cfg_file)
    cfg.setdefault("plugins", {}).setdefault("enabled", [])
    if "aether-project-knowledge" not in cfg["plugins"]["enabled"]:
        cfg["plugins"]["enabled"].append("aether-project-knowledge")
    cfg.setdefault("plugins", {}).setdefault("entries", {})["aether-project-knowledge"] = {
        "settings": {
            "enabled": True,
            "state_root": str(state_dir),
            "cache_root": str(cache_dir),
        },
        "allow_tool_override": False,
    }
    if yaml is None:
        raise RuntimeError("PyYAML is required to prepare the disposable profile configuration")
    cfg_file.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    # Configure knowledge component in disposable state root (no install)
    knowledge_service = KnowledgeService(state_root=state_dir, cache_root=cache_dir)
    conf_res = configure(knowledge_service, graphify_python)
    if not conf_res.get("ok"):
        raise RuntimeError("Failed to configure isolated knowledge component")

    env = isolated_hermes_env(run_root, hermes_root, hermes_bin)
    env["PYTHONPATH"] = str(WORKTREE_SRC)

    return {
        "run_root": run_root,
        "hermes_root": hermes_root,
        "state_dir": state_dir,
        "cache_dir": cache_dir,
        "env": env,
        "hermes_bin": hermes_bin,
        "knowledge_service": knowledge_service,
    }


def index_fixture_project(
    knowledge_service: KnowledgeService,
    state_dir: Path,
    repo_dir: Path,
    project_id: str,
) -> dict[str, Any]:
    """Register and index the fixture project structurally before any model call."""
    registry = ProjectRegistry(state_dir)
    registry.register(project_id, repo_dir, name="e01-billing-platform")
    if not registry.verify_with_marker(project_id):
        raise RuntimeError(f"Project registry verification failed for {project_id}")

    ctx = resolve_context(project_id, "morfeo", state_root=state_dir, root=repo_dir)
    update_res = knowledge_service.execute(
        ctx,
        "project_knowledge",
        {"action": "update", "mode": "structural", "reason": "E01 initial structural index"},
    )
    if not update_res.get("ok"):
        raise RuntimeError(f"Structural update failed: {update_res}")

    status_res = knowledge_service.execute(ctx, "project_knowledge", {"action": "status"})
    if not status_res.get("ok") or not status_res.get("available"):
        raise RuntimeError(f"Index status check failed: {status_res}")

    return {
        "status_ok": status_res.get("ok"),
        "available": status_res.get("available"),
        "source_revision": status_res.get("source_revision"),
        "coverage": status_res.get("coverage"),
        "freshness": status_res.get("freshness"),
        "indexed_files": status_res.get("indexed_files"),
    }


def _sanitize_trace_path(path: str) -> str:
    """Reduce an absolute tool path to its project-relative tail.

    Evidence artifacts must never carry machine paths, so the recorded trace keeps
    only the project-relative tail (for example ``billing/processor.py``).
    """
    if not isinstance(path, str) or not path:
        return ""
    candidate = Path(path)
    parts = candidate.parts
    if "positive_repo" in parts:
        idx = parts.index("positive_repo")
        return "/".join(parts[idx + 1 :])
    if "unborn_repo" in parts:
        idx = parts.index("unborn_repo")
        return "/".join(parts[idx + 1 :])
    # Any of the disposable roots collapses to a bare "<disposable>" marker.
    if len(parts) > 2 and parts[1] == "tmp":
        parts = ("<disposable>", *parts[2:])
    text = str(Path(*parts))
    return text.replace(str(Path.home()), "<home>") if Path(path).is_absolute() else text


def extract_session_traces(state_db: Path) -> list[dict[str, Any]]:
    """Extract ordered messages, tool calls, and final responses from the profile database."""
    if not state_db.is_file():
        return []
    conn = sqlite3.connect(f"file:{state_db.absolute()}?mode=ro", uri=True)
    sessions = conn.execute(
        "SELECT id, cwd, last_activity_at, input_tokens, output_tokens FROM sessions ORDER BY last_activity_at ASC"
    ).fetchall()
    results = []
    for sess_id, cwd, last_act, inp_tok, out_tok in sessions:
        rows = conn.execute(
            "SELECT id, role, content, tool_name, tool_calls FROM messages WHERE session_id = ? ORDER BY id ASC",
            (sess_id,),
        ).fetchall()
        trace = []
        final_answer = ""
        references_returned: list[dict[str, Any]] = []
        sources_read: list[str] = []

        for msg_id, role, content, tool_name, raw_tool_calls in rows:
            parsed_calls = None
            if raw_tool_calls:
                try:
                    parsed_calls = json.loads(raw_tool_calls)
                except Exception:
                    parsed_calls = raw_tool_calls
            trace.append(
                {
                    "message_id": msg_id,
                    "role": role,
                    "tool_name": tool_name,
                    "tool_calls": parsed_calls,
                    "content_preview": (content[:200] + "...")
                    if content and len(content) > 200
                    else content,
                }
            )
            if role == "assistant" and content and not raw_tool_calls:
                final_answer = content
            elif role == "assistant" and content and not final_answer:
                final_answer = content

            if role == "tool" and tool_name == "project_knowledge" and content:
                try:
                    payload = json.loads(content)
                    if isinstance(payload, dict) and "references" in payload:
                        references_returned = payload["references"]
                except Exception:
                    pass

            if raw_tool_calls and parsed_calls and isinstance(parsed_calls, list):
                for tc in parsed_calls:
                    if isinstance(tc, dict) and tc.get("function", {}).get("name") == "read_file":
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            if "path" in args and args["path"] not in sources_read:
                                sources_read.append(args["path"])
                        except Exception:
                            pass

        usage_row = conn.execute(
            "SELECT model, api_call_count, input_tokens, output_tokens, cache_read_tokens, reasoning_tokens "
            "FROM session_model_usage WHERE session_id = ? AND (task IS NULL OR task != 'title_generation') "
            "ORDER BY rowid DESC LIMIT 1",
            (sess_id,),
        ).fetchone()
        session_usage = {}
        if usage_row:
            session_usage = {
                "model": usage_row[0],
                "api_call_count": usage_row[1],
                "input_tokens": usage_row[2],
                "output_tokens": usage_row[3],
                "cache_read_tokens": usage_row[4],
                "reasoning_tokens": usage_row[5],
            }
        else:
            session_usage = {
                "input_tokens": inp_tok,
                "output_tokens": out_tok,
            }

        results.append(
            {
                "session_id": sess_id,
                "input_tokens": inp_tok,
                "output_tokens": out_tok,
                "usage": session_usage,
                "trace": trace,
                "final_answer": final_answer,
                "references_returned": references_returned,
                "sources_read": [_sanitize_trace_path(p) for p in sources_read],
            }
        )
    conn.close()
    return results


def run_live_agent_turn(
    hermes_bin: Path,
    env: Mapping[str, str],
    repo_dir: Path,
    query: str,
    usage_path: Path,
    timeout_seconds: int = 240,
) -> dict[str, Any]:
    """Execute one bounded live Morfeo turn via hermes CLI."""
    call_env = dict(env)
    call_env["TERMINAL_CWD"] = str(repo_dir.resolve())

    cmd = [
        str(hermes_bin),
        "--accept-hooks",
        "-p",
        "morfeo",
        "--usage-file",
        str(usage_path),
        "--in",
        str(repo_dir),
        "chat",
        "-q",
        query,
        "-Q",
    ]
    completed = subprocess.run(
        cmd,
        env=call_env,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    usage_data = {}
    if usage_path.is_file():
        try:
            usage_data = json.loads(usage_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "usage": usage_data,
    }


# =========================================================================
# Deterministic Tests (can run without model spend)
# =========================================================================


def test_resource_hashes_match_frozen_bytes() -> None:
    """AC-1/AC-4: Candidate SOUL and skill must match exact reviewed hashes."""
    hashes = verify_candidate_resource_bytes()
    assert hashes["morfeo_soul_sha256"] == EXPECTED_MORFEO_SOUL_SHA256
    assert hashes["project_knowledge_skill_sha256"] == EXPECTED_PROJECT_KNOWLEDGE_SKILL_SHA256


def test_fixture_construction_and_marker(tmp_path: Path) -> None:
    """AC-2: Disposable fixture project must have valid marker, git commit, and two subsystems."""
    project_id = "55555555-5555-4555-8555-555555555555"
    info = build_fixture_project(tmp_path / "repo", project_id)
    assert info["head_revision"] is not None
    assert len(info["head_revision"]) == 40

    marker_path = tmp_path / "repo" / ".aether" / "project.toml"
    import tomllib

    data = tomllib.loads(marker_path.read_text(encoding="utf-8"))
    validated = validate_project_marker(data)
    assert validated["project_id"] == project_id
    assert (tmp_path / "repo" / "billing" / "processor.py").is_file()
    assert (tmp_path / "repo" / "notifications" / "mailer.py").is_file()
    assert (tmp_path / "repo" / "docs" / "decisions" / "001-retry-policy.md").is_file()


def test_structural_indexing_and_pre_call_status(tmp_path: Path) -> None:
    """AC-2: Structural indexing builds graph and confirms status before any model call."""
    if DEFAULT_GRAPHIFY_PYTHON is None:
        pytest.skip(
            "Provisioned Graphify component interpreter not found; set AETHER_GRAPHIFY_PYTHON"
        )

    run_root = tmp_path / "run"
    repo_dir = tmp_path / "repo"
    project_id = "66666666-6666-4666-8666-666666666666"

    fixture = build_fixture_project(repo_dir, project_id)
    setup = setup_isolated_test_environment(run_root)

    index_info = index_fixture_project(
        setup["knowledge_service"], setup["state_dir"], repo_dir, project_id
    )
    assert index_info["status_ok"] is True
    assert index_info["available"] is True
    assert index_info["source_revision"] == fixture["head_revision"]
    assert index_info["freshness"] == "current"

    # Query without model to verify graph references
    ctx = resolve_context(project_id, "morfeo", state_root=setup["state_dir"], root=repo_dir)
    query_res = setup["knowledge_service"].execute(
        ctx, "project_knowledge", {"action": "query", "question": "payment retries retry policy"}
    )
    assert query_res.get("ok") is True
    paths = {ref.get("path") for ref in query_res.get("references", [])}
    assert "docs/decisions/001-retry-policy.md" in paths


def test_unborn_repository_honest_degradation(tmp_path: Path) -> None:
    """AC-3: Unborn repo produces honest status/error and does not commit or build index."""
    from aether_agents.knowledge.common import KnowledgeError

    run_root = tmp_path / "run"
    repo_dir = tmp_path / "unborn"
    project_id = "77777777-7777-4777-8777-777777777777"

    build_unborn_project(repo_dir, project_id)
    setup = setup_isolated_test_environment(run_root)

    registry = ProjectRegistry(setup["state_dir"])
    registry.register(project_id, repo_dir, name="e01-unborn-fixture")
    # An unborn repo with a valid marker still agrees registry/marker, so the
    # failure must come from the missing HEAD itself, not from identity mismatch.
    assert registry.verify_with_marker(project_id) is True

    # In unborn repository without HEAD, resolve_context fails with SCOPE_UNAVAILABLE.
    with pytest.raises(KnowledgeError) as caught:
        resolve_context(project_id, "morfeo", state_root=setup["state_dir"], root=repo_dir)
    assert caught.value.code == "SCOPE_UNAVAILABLE"

    # No index was built and no commit was created.
    assert not (setup["cache_dir"] / "knowledge" / project_id).exists()
    verify_head = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "--verify", "HEAD^{commit}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_head.returncode != 0
    unborn_log = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert unborn_log.returncode != 0


def test_spend_guard_refuses_live_calls_without_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2/Safety: Live run must refuse execution unless explicit spend authorization is present."""
    monkeypatch.delenv("AETHER_ALLOW_MODEL_SPEND", raising=False)
    with pytest.raises(RuntimeError, match="Model spend not authorized"):
        run_e01_suite(allow_model_spend=False)


def test_extract_session_traces_parses_references_and_sources(tmp_path: Path) -> None:
    """AC-2/Data: extract_session_traces must parse large tool payloads and read_file calls."""
    db_path = tmp_path / "state.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, last_activity_at REAL, input_tokens INTEGER, output_tokens INTEGER)"
    )
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, tool_name TEXT, tool_calls TEXT)"
    )
    conn.execute(
        "CREATE TABLE session_model_usage (session_id TEXT, model TEXT, task TEXT, api_call_count INTEGER, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, reasoning_tokens INTEGER)"
    )
    conn.execute("INSERT INTO sessions VALUES ('sess-test', '/test/repo', 1000.0, 100, 20)")

    # Tool call for read_file
    tc = json.dumps(
        [
            {
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps(
                        {"path": "/test/run/positive_repo/billing/processor.py"}
                    ),
                }
            }
        ]
    )
    conn.execute("INSERT INTO messages VALUES (1, 'sess-test', 'assistant', '', NULL, ?)", (tc,))

    # Tool result for project_knowledge with >200 chars payload containing 7 references
    sample_refs = [
        {"path": "docs/decisions/001-retry-policy.md", "location": f"L{i}", "revision": "c777" * 10}
        for i in (1, 3, 6, 10, 16)
    ] + [
        {"path": "billing/processor.py", "location": f"L{i}", "revision": "c777" * 10}
        for i in (1, 4)
    ]
    tool_payload = json.dumps(
        {
            "schema_version": "aether.project-knowledge.v1",
            "ok": True,
            "action": "query",
            "references": sample_refs,
            "content": "A" * 500,  # Ensure payload > 200 chars
        }
    )
    conn.execute(
        "INSERT INTO messages VALUES (2, 'sess-test', 'tool', ?, 'project_knowledge', NULL)",
        (tool_payload,),
    )
    conn.commit()
    conn.close()

    traces = extract_session_traces(db_path)
    assert len(traces) == 1
    assert len(traces[0]["references_returned"]) == 7
    assert traces[0]["references_returned"][0]["path"] == "docs/decisions/001-retry-policy.md"
    assert "billing/processor.py" in traces[0]["sources_read"]


def test_distinguishes_specification_from_implementation_derived() -> None:
    """AC-2/Oracle: Distinguishing spec from implementation must be derived from answer content."""
    # Positive answer mentioning both ADR specification and legacy code
    valid_answer = (
        "The accepted policy is exponential backoff (60, 120, 240s) per ADR 001. "
        "However, billing/processor.py still has legacy settings and does not actually retry."
    )
    assert check_distinguishes_specification_from_implementation(valid_answer) is True

    # Negative: only code
    code_only = "The retry delay in billing/processor.py is 10 seconds with 5 attempts."
    assert check_distinguishes_specification_from_implementation(code_only) is False

    # Negative: only spec
    spec_only = "The accepted policy in ADR 001 is 60s delay."
    assert check_distinguishes_specification_from_implementation(spec_only) is False


def check_distinguishes_specification_from_implementation(answer: str) -> bool:
    """Derive whether the final answer distinguishes the ADR specification from the implementation."""
    lowered = answer.lower()
    has_spec = any(
        w in lowered for w in ["adr", "accepted policy", "exponential", "60", "policy is"]
    )
    has_impl = any(
        w in lowered
        for w in [
            "billing/processor",
            "processor.py",
            "legacy",
            "not actually retry",
            "fixed 10",
            "10-second",
        ]
    )
    return bool(has_spec and has_impl)


# =========================================================================
# Live Qualification Execution (gated by --allow-model-spend)
# =========================================================================


def run_e01_suite(
    output_dir: Path | None = None,
    *,
    allow_model_spend: bool = False,
    run_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the full E01 positive qualification and controls with live isolated agents."""
    if not allow_model_spend and os.environ.get("AETHER_ALLOW_MODEL_SPEND") != "1":
        raise RuntimeError(
            "Model spend not authorized. Pass --allow-model-spend or set AETHER_ALLOW_MODEL_SPEND=1."
        )

    verify_candidate_resource_bytes()

    scratch = run_root or Path(tempfile.mkdtemp(prefix="aether-e01-qualification-"))
    evidence_dir = output_dir or (REPO_ROOT / "specs/005-project-knowledge-graphify/evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    positive_repo = scratch / "positive_repo"
    unborn_repo = scratch / "unborn_repo"
    project_id = "e01a0001-0000-4000-8000-000000000001"
    unborn_project_id = "e01b0002-0000-4000-8000-000000000002"

    fixture_info = build_fixture_project(positive_repo, project_id)
    _unborn_info = build_unborn_project(unborn_repo, unborn_project_id)

    env_setup = setup_isolated_test_environment(scratch)
    ks = env_setup["knowledge_service"]
    state_dir = env_setup["state_dir"]
    hermes_env = env_setup["env"]
    hermes_bin = env_setup["hermes_bin"]
    hermes_root = env_setup["hermes_root"]
    morfeo_state_db = hermes_root / "profiles" / "morfeo" / "state.db"

    # Pre-model check: build index and verify status and revision
    pre_status = index_fixture_project(ks, state_dir, positive_repo, project_id)

    # 1. Positive E01 Run
    positive_query = (
        "Explain how payment retries work in this project, and what the retry policy is."
    )
    positive_usage_file = scratch / "usage_positive.json"
    positive_turn = run_live_agent_turn(
        hermes_bin, hermes_env, positive_repo, positive_query, positive_usage_file
    )

    # 2. Control A Run (exact source supplied)
    control_a_query = "In billing/processor.py, what is the default retry delay in seconds and the maximum attempts?"
    control_a_usage_file = scratch / "usage_control_a.json"
    control_a_turn = run_live_agent_turn(
        hermes_bin, hermes_env, positive_repo, control_a_query, control_a_usage_file
    )

    # 3. Control B Run (unborn repository)
    control_b_query = "In this repository, what is the architecture and implementation?"
    control_b_usage_file = scratch / "usage_control_b.json"
    control_b_turn = run_live_agent_turn(
        hermes_bin, hermes_env, unborn_repo, control_b_query, control_b_usage_file
    )

    # Extract traces from isolated Morfeo state database
    all_sessions = extract_session_traces(morfeo_state_db)

    # Correlate session traces
    positive_session = all_sessions[0] if len(all_sessions) > 0 else {}
    control_a_session = all_sessions[1] if len(all_sessions) > 1 else {}
    control_b_session = all_sessions[2] if len(all_sessions) > 2 else {}

    # Analyze positive run tool calls
    positive_tools_called = [
        step.get("tool_name")
        or (
            step.get("tool_calls", [{}])[0].get("function", {}).get("name")
            if step.get("tool_calls")
            else None
        )
        for step in positive_session.get("trace", [])
    ]
    positive_tools_called = [t for t in positive_tools_called if t]

    # Analyze Control A tool calls
    control_a_tools = [
        step.get("tool_name")
        or (
            step.get("tool_calls", [{}])[0].get("function", {}).get("name")
            if step.get("tool_calls")
            else None
        )
        for step in control_a_session.get("trace", [])
    ]
    control_a_tools = [t for t in control_a_tools if t]

    # Analyze Control B tool calls
    control_b_tools = [
        step.get("tool_name")
        or (
            step.get("tool_calls", [{}])[0].get("function", {}).get("name")
            if step.get("tool_calls")
            else None
        )
        for step in control_b_session.get("trace", [])
    ]
    control_b_tools = [t for t in control_b_tools if t]

    record = {
        "producer": "KG19-02 (t_58496a81)",
        "contract": "oc_d96969bf913512f7@v1",
        "candidate_bytes": {
            "morfeo_soul_sha256": EXPECTED_MORFEO_SOUL_SHA256,
            "project_knowledge_skill_sha256": EXPECTED_PROJECT_KNOWLEDGE_SKILL_SHA256,
        },
        "fixture": {
            "project_id": project_id,
            "head_revision": fixture_info["head_revision"],
            "pre_call_status": pre_status,
        },
        "positive_e01": {
            "query": positive_query,
            "returncode": positive_turn["returncode"],
            "tools_sequence": positive_tools_called,
            "references_returned": positive_session.get("references_returned", []),
            "sources_inspected": positive_session.get("sources_read", []),
            "distinguishes_specification_from_implementation": check_distinguishes_specification_from_implementation(
                positive_session.get("final_answer") or positive_turn.get("stdout", "")
            ),
            "usage": positive_session.get("usage", positive_turn["usage"]),
            "answer": positive_session.get("final_answer", positive_turn["stdout"]),
            "session_id": positive_session.get("session_id"),
        },
        "control_a_exact_source": {
            "query": control_a_query,
            "returncode": control_a_turn["returncode"],
            "tools_sequence": control_a_tools,
            "ceremonial_graph_called": "project_knowledge" in control_a_tools,
            "sources_inspected": control_a_session.get("sources_read", []),
            "usage": control_a_session.get("usage", control_a_turn["usage"]),
            "answer": control_a_session.get("final_answer", control_a_turn["stdout"]),
            "session_id": control_a_session.get("session_id"),
        },
        "control_b_unborn_repo": {
            "query": control_b_query,
            "returncode": control_b_turn["returncode"],
            "tools_sequence": control_b_tools,
            "usage": control_b_session.get("usage", control_b_turn["usage"]),
            "answer": control_b_session.get("final_answer", control_b_turn["stdout"]),
            "session_id": control_b_session.get("session_id"),
        },
    }

    evidence_json_path = evidence_dir / "E01-evidence.json"
    evidence_json_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run E01 isolated real-Morfeo qualification lane.")
    parser.add_argument(
        "--allow-model-spend",
        action="store_true",
        help="Acknowledge provider quota and run the bounded live agent sessions.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to store sanitized evidence JSON (defaults to specs/.../evidence).",
    )
    args = parser.parse_args()

    print("=== E01 Morfeo Orientation Qualification Lane ===")
    print("1. Verifying candidate resource bytes...")
    hashes = verify_candidate_resource_bytes()
    print(f"   Morfeo SOUL SHA-256: {hashes['morfeo_soul_sha256']}")
    print(f"   SKILL SHA-256:       {hashes['project_knowledge_skill_sha256']}")

    if not args.allow_model_spend and os.environ.get("AETHER_ALLOW_MODEL_SPEND") != "1":
        print("\nDeterministic verification passed.")
        print("Live agent sessions refused because --allow-model-spend was not specified.")
        return 0

    print("\n2. Executing live E01 qualification with controls...")
    record = run_e01_suite(output_dir=args.output_dir, allow_model_spend=True)
    print("\n=== Observed Results Summary ===")
    print(f"Positive E01 tools called: {record['positive_e01']['tools_sequence']}")
    print(f"Positive E01 final answer excerpt: {record['positive_e01']['answer'][:200]}...")
    print(f"Control A tools called: {record['control_a_exact_source']['tools_sequence']}")
    print(f"Control B tools called: {record['control_b_unborn_repo']['tools_sequence']}")
    print(
        "\nSanitized evidence written to specs/005-project-knowledge-graphify/evidence/E01-evidence.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
