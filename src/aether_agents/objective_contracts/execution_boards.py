"""Portable execution-board identity for Objective Contracts.

The portable contract never contains a board reference. The deterministic slug is safe
to calculate from manager/store code; all Hermes imports and local provisioning stay in
``hermes_plugin`` at the runtime boundary.
"""

from __future__ import annotations

import re

__all__ = ["ExecutionBoardError", "execution_board_slug"]

_PROJECT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_CONTRACT_ID = re.compile(r"^oc_([0-9a-f]{16})$")


class ExecutionBoardError(RuntimeError):
    """A ready contract could not acquire its exact local execution board."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def execution_board_slug(project_id: str, contract_id: str, version: int) -> str:
    """Return the exact board identity for one executable contract version.

    All identity bytes are represented (UUID hex + contract hex + hexadecimal version),
    so the mapping has no truncated hash or probabilistic collision. The resulting slug
    is inside Hermes' 64-character board grammar for every supported contract version.
    """
    if not isinstance(project_id, str) or _PROJECT_ID.fullmatch(project_id) is None:
        raise ValueError("project_id must be a canonical UUID")
    contract = _CONTRACT_ID.fullmatch(contract_id) if isinstance(contract_id, str) else None
    if contract is None:
        raise ValueError("contract_id is invalid")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("version is invalid")
    slug = f"oc-{project_id.replace('-', '')}-{contract.group(1)}-v{version:x}"
    if len(slug) > 64:
        raise ValueError("version is too large for an execution-board identity")
    return slug
