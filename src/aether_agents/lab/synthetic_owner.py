"""Scenario loading and scripted owner replies for Aether E2E runs.

The scripted owner is intentionally dumb: it never inspects the board or repairs the
agent. An unexpected clarification is evidence that the scenario depends on owner
attention and fails unless the scenario explicitly supplied a reply.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .resources import resource_json, scenario_resource, source_root


class ScenarioError(ValueError):
    """A scenario is malformed or asks the harness to invent owner intent."""


@dataclass(frozen=True, slots=True)
class ScriptedReply:
    pattern: re.Pattern[str]
    reply: str


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    fixture: str
    owner_message: str
    expected_route: str
    acceptance_command: tuple[str, ...]
    timeout_seconds: int
    max_dispatch_passes: int
    scripted_replies: tuple[ScriptedReply, ...]
    forbidden_paths: tuple[str, ...]
    required_paths: tuple[str, ...]
    live_requires_spend: bool
    fault_injection: str | None
    expected_owner_interventions: int
    expected_guard_denial_codes: tuple[str, ...]


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ScenarioError(f"{field} must be a list of non-empty strings")
    return tuple(value)


@lru_cache(maxsize=1)
def _scenario_validator() -> Draft202012Validator:
    return Draft202012Validator(resource_json("schemas/scenario.schema.json"))


def validate_scenario(value: Any) -> None:
    """Validate a scenario before any harness state is created."""
    if not isinstance(value, dict):
        raise ScenarioError("scenario root must be an object")
    errors = sorted(_scenario_validator().iter_errors(value), key=lambda error: tuple(error.path))
    if errors:
        raise ScenarioError("scenario failed schema validation")


def _scenario_path(value: str | Path) -> Path | None:
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    identifier = str(value).casefold()
    if re.fullmatch(r"(?:e2e-)?[0-9]{1,2}", identifier):
        number = int(identifier.rsplit("-", 1)[-1])
        candidate = source_root() / "lab" / "scenarios" / f"e2e-{number:02d}.json"
        if candidate.is_file():
            return candidate
    candidate = source_root() / "lab" / "scenarios" / str(value)
    if candidate.is_file():
        return candidate
    return None


def load_scenario(path: Path | str) -> Scenario:
    try:
        candidate = _scenario_path(path)
        if candidate is not None:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        else:
            identifier = str(path)
            filename = identifier if identifier.endswith(".json") else f"{identifier}.json"
            if not re.fullmatch(r"e2e-[0-9]{2}\.json", filename):
                raise ScenarioError(f"scenario not found: {path}")
            raw = json.loads(scenario_resource(filename))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScenarioError(f"cannot read scenario: {path}") from exc
    except (KeyError, ValueError) as exc:
        raise ScenarioError(f"scenario not found: {path}") from exc
    validate_scenario(raw)

    identifier = raw.get("id")
    fixture = raw.get("fixture")
    owner_message = raw.get("owner_message")
    expected_route = raw.get("expected_route")
    acceptance = raw.get("acceptance_command")
    if not isinstance(identifier, str) or not re.fullmatch(r"e2e-[0-9]{2}", identifier):
        raise ScenarioError("scenario id must match e2e-NN")
    if not isinstance(fixture, str) or not fixture or "/" in fixture or "\\" in fixture:
        raise ScenarioError("fixture must be one directory name")
    if not isinstance(owner_message, str) or not owner_message.strip():
        raise ScenarioError("owner_message is required")
    if expected_route not in {"direct", "pipeline", "safety", "recovery"}:
        raise ScenarioError("expected_route must be direct, pipeline, safety, or recovery")
    if (
        not isinstance(acceptance, list)
        or not acceptance
        or not all(isinstance(item, str) and item for item in acceptance)
    ):
        raise ScenarioError("acceptance_command must be a non-empty argv list")

    replies: list[ScriptedReply] = []
    raw_replies = raw.get("scripted_replies", [])
    if not isinstance(raw_replies, list):
        raise ScenarioError("scripted_replies must be a list")
    for item in raw_replies:
        if not isinstance(item, dict) or set(item) != {"pattern", "reply"}:
            raise ScenarioError("each scripted reply needs pattern and reply")
        pattern = item["pattern"]
        reply = item["reply"]
        if not isinstance(pattern, str) or not isinstance(reply, str) or not reply.strip():
            raise ScenarioError("scripted reply values must be strings")
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        except re.error as exc:
            raise ScenarioError(f"invalid scripted reply regex: {pattern}") from exc
        replies.append(ScriptedReply(compiled, reply))

    timeout_seconds = raw.get("timeout_seconds", 900)
    max_dispatch_passes = raw.get("max_dispatch_passes", 40)
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 14_400:
        raise ScenarioError("timeout_seconds must be 1..14400")
    if not isinstance(max_dispatch_passes, int) or not 1 <= max_dispatch_passes <= 500:
        raise ScenarioError("max_dispatch_passes must be 1..500")

    fault_injection = raw.get("fault_injection")
    if fault_injection not in {None, "hook_false_positive_file_mutation"}:
        raise ScenarioError("unsupported fault_injection")
    expected_owner_interventions = raw.get("expected_owner_interventions", 0)
    if (
        not isinstance(expected_owner_interventions, int)
        or expected_owner_interventions < 0
        or expected_owner_interventions > len(replies)
    ):
        raise ScenarioError(
            "expected_owner_interventions must be an integer between 0 and the scripted reply count"
        )

    expected_guard_denial_codes = _strings(
        raw.get("expected_guard_denial_codes"), "expected_guard_denial_codes"
    )
    if expected_guard_denial_codes and expected_route != "safety":
        raise ScenarioError("expected_guard_denial_codes are valid only for safety scenarios")

    return Scenario(
        id=identifier,
        fixture=fixture,
        owner_message=owner_message.strip(),
        expected_route=expected_route,
        acceptance_command=tuple(acceptance),
        timeout_seconds=timeout_seconds,
        max_dispatch_passes=max_dispatch_passes,
        scripted_replies=tuple(replies),
        forbidden_paths=_strings(raw.get("forbidden_paths"), "forbidden_paths"),
        required_paths=_strings(raw.get("required_paths"), "required_paths"),
        live_requires_spend=bool(raw.get("live_requires_spend", True)),
        fault_injection=fault_injection,
        expected_owner_interventions=expected_owner_interventions,
        expected_guard_denial_codes=expected_guard_denial_codes,
    )


def matching_reply(scenario: Scenario, assistant_text: str) -> str | None:
    """Return one pre-authorized owner reply, never an invented fallback."""

    for candidate in scenario.scripted_replies:
        if candidate.pattern.search(assistant_text):
            return candidate.reply
    return None
