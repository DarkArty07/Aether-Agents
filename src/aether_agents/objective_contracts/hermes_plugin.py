"""Hermes plugin exposing Morfeo-only Objective Contract authoring."""

from __future__ import annotations

import json
from typing import Any

from .store import REQUIRED_SECTIONS, ContractError, ObjectiveContractStore

_ACTIONS = (
    "begin",
    "set_section",
    "show",
    "list",
    "validate",
    "finalize",
    "supersede",
    "prepare_handoff",
)


def _required(args: dict[str, Any], name: str) -> Any:
    value = args.get(name)
    if value is None or value == "":
        raise ContractError("AETHER-OBJECTIVE-CONTRACT-ARGUMENT-MISSING", f"{name} is required")
    return value


def _handle(
    args: dict[str, Any],
    *,
    session_id: str = "",
    author_profile: str = "",
    **_kwargs: Any,
) -> str:
    try:
        if author_profile != "morfeo":
            raise ContractError(
                "AETHER-OBJECTIVE-CONTRACT-ROLE-DENIED",
                "Objective Contract authoring is restricted to Morfeo",
            )
        action = _required(args, "action")
        project_id = _required(args, "project_id")
        store = ObjectiveContractStore(author_profile=author_profile)
        if action == "begin":
            result = store.begin(
                project_id=project_id,
                title=_required(args, "title"),
                session_id=session_id,
            )
        elif action == "set_section":
            result = store.set_section(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                expected_revision=_required(args, "expected_revision"),
                section=_required(args, "section"),
                content=_required(args, "content"),
                session_id=session_id,
            )
        elif action == "show":
            result = store.show(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
            )
        elif action == "list":
            result = store.list(project_id=project_id)
        elif action == "validate":
            result = store.validate(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
            )
        elif action == "finalize":
            result = store.finalize(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                expected_revision=_required(args, "expected_revision"),
                session_id=session_id,
            )
        elif action == "supersede":
            result = store.supersede(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                version=_required(args, "version"),
                change_reason=_required(args, "change_reason"),
                session_id=session_id,
            )
        elif action == "prepare_handoff":
            result = store.prepare_handoff(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                version=_required(args, "version"),
            )
        else:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-ACTION-INVALID", "action is not supported")
        return json.dumps(result, ensure_ascii=False)
    except ContractError as exc:
        return json.dumps(
            {"success": False, "error": {"code": exc.code, "message": str(exc)}},
            ensure_ascii=False,
        )


def register(ctx: Any) -> None:
    """Register one transactional authoring tool only in the configured Morfeo profile."""
    get_config = getattr(ctx, "get_config", None)
    profile_name = getattr(ctx, "profile_name", "")
    if (
        profile_name != "morfeo"
        or not callable(get_config)
        or get_config("author_profile", "") != "morfeo"
    ):
        return

    def handler(args: dict[str, Any], **runtime_kwargs: Any) -> str:
        runtime_kwargs.pop("author_profile", None)
        return _handle(
            args,
            author_profile=getattr(ctx, "profile_name", ""),
            **runtime_kwargs,
        )

    ctx.register_tool(
        name="objective_contract",
        toolset="aether_contracts",
        description="Author project-bound Objective Contracts for Morfeo-to-Supervisor handoff.",
        schema={
            "name": "objective_contract",
            "description": (
                "Incrementally author, finalize, version and prepare a project-bound Objective "
                "Contract. Always pass the explicit portable project UUID. Hermes supplies the "
                "authoring session id; never put a complete contract in one call."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action", "project_id"],
                "properties": {
                    "action": {"type": "string", "enum": list(_ACTIONS)},
                    "project_id": {
                        "type": "string",
                        "description": "Portable UUID from the verified .aether/project.toml marker.",
                    },
                    "title": {"type": "string", "maxLength": 200},
                    "contract_id": {"type": "string", "pattern": "^oc_[a-f0-9]{16}$"},
                    "expected_revision": {"type": "integer", "minimum": 1},
                    "section": {"type": "string", "enum": list(REQUIRED_SECTIONS)},
                    "content": {
                        "type": "string",
                        "description": "One accepted section only; do not resend the whole contract.",
                    },
                    "version": {"type": "integer", "minimum": 1},
                    "change_reason": {"type": "string"},
                },
            },
        },
        handler=handler,
        check_fn=lambda: getattr(ctx, "profile_name", "") == "morfeo",
    )
