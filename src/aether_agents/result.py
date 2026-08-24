"""Stable Aether CLI result envelope.

Normative source: ``specs/001-aether-v1-productization/contracts/cli.md`` sections 3 and 4.
The envelope is shared by every ``--json`` command, including ``aether observe``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

__all__ = [
    "ENVELOPE_SCHEMA_VERSION",
    "EXIT_CODES",
    "Envelope",
    "Note",
    "exit_code_for",
]

ENVELOPE_SCHEMA_VERSION = 1

ResultValue = Literal[
    "ready",
    "changed",
    "no_change",
    "planned",
    "blocked",
    "unsupported",
    "error",
]

#: cli.md section 4. A command must never encode detailed domain state only in the code.
EXIT_CODES: dict[str, int] = {
    "ready": 0,
    "changed": 0,
    "no_change": 0,
    "planned": 0,
    "invalid_input": 2,
    "missing_prerequisite": 3,
    "integrity_failure": 4,
    "blocked": 5,
    "runtime_failure": 6,
    "internal_error": 10,
}


def exit_code_for(result: str, *, failure_kind: str = "invalid_input") -> int:
    """Map a result value to its documented process exit code."""
    if result in ("ready", "changed", "no_change", "planned"):
        return 0
    if result == "blocked":
        return EXIT_CODES["blocked"]
    if result == "unsupported":
        return EXIT_CODES["missing_prerequisite"]
    return EXIT_CODES.get(failure_kind, EXIT_CODES["invalid_input"])


@dataclass(frozen=True, slots=True)
class Note:
    """One warning or error entry. It must never carry a secret value."""

    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload


@dataclass(slots=True)
class Envelope:
    """One command result rendered as the stable JSON object."""

    command: str
    result: ResultValue
    changed: bool = False
    manager_version: str | None = None
    active_version: str | None = None
    warnings: list[Note] = field(default_factory=list)
    errors: list[Note] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    failure_kind: str = "invalid_input"

    def warn(self, code: str, message: str, **details: Any) -> None:
        self.warnings.append(Note(code, message, details or None))

    def fail(self, code: str, message: str, **details: Any) -> None:
        self.errors.append(Note(code, message, details or None))

    @property
    def exit_code(self) -> int:
        return exit_code_for(self.result, failure_kind=self.failure_kind)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "command": self.command,
            "result": self.result,
            "changed": self.changed,
            "warnings": [note.to_json() for note in self.warnings],
            "errors": [note.to_json() for note in self.errors],
            "data": self.data,
        }
        if self.manager_version is not None:
            payload["manager_version"] = self.manager_version
        if self.active_version is not None:
            payload["active_version"] = self.active_version
        return payload
