"""The only module that imports Hermes internals."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from aether_agents.mcp.context import build_snapshot, log_records
from aether_agents.mcp.contracts import EXTERNAL_MCP_PREFIX, PROFILE_NAME, SESSION_SOURCE

logger = logging.getLogger("aether_agents.mcp")


def bind_profile(profile: Path, project: Path, project_id: str) -> None:
    """Point the process at the canonical Morfeo home and the selected project."""

    os.environ["HERMES_HOME"] = str(profile)
    os.environ["AETHER_PROJECT_ID"] = project_id
    os.chdir(project)


def discover_effective_tools(profile: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Load config, discover plugins, and return checked tool definitions.

    External MCP servers, including Context7, are not part of this surface.
    """

    os.environ["HERMES_HOME"] = str(profile)
    from hermes_cli.config import load_config
    from hermes_cli.plugins import discover_plugins
    from hermes_cli.tools_config import _get_platform_tools
    from model_tools import get_tool_definitions

    discover_plugins()
    config = load_config()
    toolsets = _get_platform_tools(config, "cli", include_default_mcp_servers=False)
    definitions = get_tool_definitions(
        enabled_toolsets=sorted(toolsets),
        quiet_mode=True,
        skip_tool_search_assembly=True,
    )
    kept: list[dict[str, Any]] = []
    for item in definitions or []:
        if not isinstance(item, dict) or item.get("type") != "function":
            continue
        function = item.get("function") or {}
        name = function.get("name")
        if not isinstance(name, str) or name.startswith(EXTERNAL_MCP_PREFIX):
            continue
        kept.append(item)
    return kept, sorted(str(item) for item in toolsets)


def load_sections(profile: Path, project: Path) -> dict[str, str]:
    """Load SOUL, memory files, project context and the skill index via Hermes."""

    os.environ["HERMES_HOME"] = str(profile)
    from agent.prompt_builder import (
        build_context_files_prompt,
        build_skills_system_prompt,
        load_soul_md,
    )
    from tools.memory_tool import get_memory_dir

    memory_dir = Path(get_memory_dir())
    return {
        "soul": load_soul_md(home_override=profile) or "",
        "user": _read_text(memory_dir / "USER.md"),
        "memory": _read_text(memory_dir / "MEMORY.md"),
        "project_context": build_context_files_prompt(
            cwd=str(project),
            skip_soul=True,
            home_override=profile,
        )
        or "",
        "skills": build_skills_system_prompt() or "",
    }


def _read_text(path: Path) -> str:
    if path.name == ".env" or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def open_session_db() -> Any:
    from hermes_state import SessionDB

    return SessionDB()


def create_hermes_session(database: Any, project: Path) -> str:
    session_id = uuid.uuid4().hex
    database.create_session(
        session_id,
        SESSION_SOURCE,
        profile_name=PROFILE_NAME,
        cwd=str(project),
        git_repo_root=str(project),
    )
    return session_id


def end_hermes_session(database: Any, session_id: str) -> None:
    database.end_session(session_id, "mcp_disconnect")


def make_snapshot(
    *,
    profile: Path,
    project: Path,
    project_id: str,
    mode: str,
    tool_names: list[str],
) -> dict[str, Any]:
    snapshot = build_snapshot(
        sections=load_sections(profile, project),
        role=PROFILE_NAME,
        mode=mode,
        project_id=project_id,
        project_root=str(project),
        tool_names=tool_names,
    )
    for record in log_records(snapshot):
        logger.info(
            "bootstrap section=%s bytes=%s sha256=%s redacted_lines=%s",
            record["section"],
            record["bytes"],
            record["sha256"],
            record["redacted_lines"],
        )
    return snapshot


def create_context_agent(
    *,
    session_id: str,
    session_db: Any,
    task_id: str,
    project: Path,
    toolsets: list[str],
) -> Any:
    """Build a real AIAgent subclass without resolving or calling a provider."""

    from run_agent import AIAgent

    route = _configured_parent_route()

    class MorfeoMcpContextAgent(AIAgent):
        def __init__(self) -> None:
            # AIAgent.__init__ resolves a provider and refuses to start without
            # credentials. This object is a tool container, not a model turn.
            self.session_id = session_id
            self.session_db = session_db
            self._session_db = session_db
            self._owns_session_db = False
            self._persist_disabled = False
            self.task_id = task_id
            self._memory_manager = None
            self._todo_store = None
            self.valid_tool_names = None
            self.clarify_callback = None
            self.enabled_toolsets = list(toolsets)
            self.disabled_toolsets: list[str] = []
            self._delegate_depth = 0
            self._current_turn_id = ""
            self._current_api_request_id = ""
            self.quiet_mode = True
            self.model = route["model"]
            self.provider = route["provider"]
            self.api_key = route["api_key"]
            self.api_mode = route["api_mode"]
            self.base_url = route["base_url"]
            self._client_kwargs = {
                key: value
                for key, value in {
                    "base_url": route["base_url"],
                    "api_key": route["api_key"],
                }.items()
                if value
            }
            self.client = None
            self.acp_command = None
            self.acp_args: list[str] = []
            self.reasoning_config = None
            self.prefill_messages = None
            self._fallback_chain: list[dict[str, Any]] = []
            self.providers_allowed = None
            self.providers_ignored = None
            self.providers_order = None
            self.provider_sort = None
            self.provider_require_parameters = False
            self.provider_data_collection = ""
            self.openrouter_min_coding_score = None
            self.max_tokens = None
            self.request_overrides: dict[str, Any] = {}
            self.cwd = str(project)
            self._memory_store = None
            self._memory_enabled = False
            self._user_profile_enabled = False
            try:
                from tools.memory_tool import MemoryStore

                self._memory_store = MemoryStore()
                self._memory_store.load_from_disk()
                self._memory_enabled = True
            except Exception:
                logger.debug("memory store unavailable", exc_info=True)

        def _get_session_db_for_recall(self) -> Any:
            if self._persist_disabled:
                return None
            return self._session_db

        def _dispatch_delegate_task(self, function_args: dict) -> str:
            from tools.delegate_tool import (
                _strip_model_hidden_task_fields,
            )
            from tools.delegate_tool import (
                delegate_task as _delegate_task,
            )

            # Native Morfeo may return in the background. An external MCP host
            # has no conversation injection channel, so this spawn waits.
            return _delegate_task(
                goal=function_args.get("goal"),
                context=function_args.get("context"),
                tasks=_strip_model_hidden_task_fields(function_args.get("tasks")),
                max_iterations=function_args.get("max_iterations"),
                role=function_args.get("role"),
                background=False,
                action=function_args.get("action"),
                subagent_id=function_args.get("subagent_id"),
                message=function_args.get("message"),
                parent_agent=self,
            )

    return MorfeoMcpContextAgent()


def _configured_parent_route() -> dict[str, Any]:
    """Read Morfeo's configured route without opening a provider client."""

    from hermes_cli.config import load_config

    config = load_config() or {}
    raw_model = config.get("model")
    if isinstance(raw_model, dict):
        model = str(raw_model.get("default") or raw_model.get("model") or "").strip()
        provider = str(raw_model.get("provider") or config.get("provider") or "").strip()
        base_url = str(raw_model.get("base_url") or "").strip()
        api_mode = str(raw_model.get("api_mode") or "").strip() or None
        api_key = str(raw_model.get("api_key") or "")
    else:
        model = str(raw_model or "").strip()
        provider = str(config.get("provider") or "").strip()
        base_url = str(config.get("base_url") or "").strip()
        api_mode = str(config.get("api_mode") or "").strip() or None
        api_key = str(config.get("api_key") or "")
    return {
        "model": model,
        "provider": provider,
        "base_url": base_url,
        "api_mode": api_mode,
        "api_key": api_key,
    }


def invoke(
    agent: Any, name: str, arguments: dict[str, Any], task_id: str, tool_call_id: str
) -> str:
    from agent.agent_runtime_helpers import invoke_tool

    agent._current_turn_id = tool_call_id
    return invoke_tool(agent, name, arguments, task_id, tool_call_id)
