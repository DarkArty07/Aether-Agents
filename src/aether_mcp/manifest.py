"""Deterministic, no-dispatch swarm manifest validation for M2.6."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, NoReturn

from .protocol import ProtocolError, validate_request

_BUNDLED_CATALOG_DIGEST = "00df83ec1686a56344c78a49d75ff8dec63d988e588642236172180742b23c25"


class ManifestError(ValueError):
    """Stable swarm-manifest validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise ManifestError(code, message)


@dataclass(frozen=True)
class ValidatedManifest:
    project_id: str
    digest: str
    manifest_ref: str
    provider_binding_digest: str
    topological_order: tuple[str, ...]
    canonical: dict[str, Any]


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def validate_swarm_manifest(manifest: object, *, provider_binding_digest: str | None = None) -> ValidatedManifest:
    """Validate schema, DAG, and independent write scopes without starting M3."""
    try:
        validated = validate_request("swarm_validate", {"manifest": manifest})["manifest"]
    except ProtocolError:
        _fail("MANIFEST_INVALID", "Swarm manifest does not match the v1alpha2 contract")
    if not isinstance(validated, dict):  # defensive boundary for type checkers
        _fail("MANIFEST_INVALID", "Swarm manifest is not an object")
    tasks = validated["tasks"]
    if any(task["archetype"] not in {"fixture", "model"} for task in tasks):
        _fail("PARTICIPANT_FORBIDDEN", "Manifest requests a participant unavailable in this candidate")
    admitted_effects = {"READ_ONLY", "LOCAL_APPEND_ONLY", "LOCAL_REVERSIBLE"}
    if not set(validated["contract"]["authorized_effects"]).issubset(admitted_effects):
        _fail("EFFECT_NOT_AUTHORIZED", "Manifest requests an effect without exact authority")
    keys = [task["task_key"] for task in tasks]
    if len(set(keys)) != len(keys):
        _fail("MANIFEST_INVALID", "Task identities must be unique")
    task_by_key = {task["task_key"]: task for task in tasks}
    for task in tasks:
        if task["task_key"] in task["dependencies"] or any(dep not in task_by_key for dep in task["dependencies"]):
            _fail("MANIFEST_INVALID", "Task dependency is missing or self-referential")

    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(key: str) -> None:
        if key in visiting:
            _fail("DEPENDENCY_CYCLE", "Task dependency graph contains a cycle")
        if key in visited:
            return
        visiting.add(key)
        for dependency in task_by_key[key]["dependencies"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
        order.append(key)

    for key in keys:
        visit(key)

    ancestors: dict[str, set[str]] = {key: set() for key in keys}
    for key in order:
        for dependency in task_by_key[key]["dependencies"]:
            ancestors[key].add(dependency)
            ancestors[key].update(ancestors[dependency])
    for index, first in enumerate(keys):
        first_scope = set(task_by_key[first]["write_scope"])
        if not first_scope:
            continue
        for second in keys[index + 1 :]:
            if first in ancestors[second] or second in ancestors[first]:
                continue
            if first_scope.intersection(task_by_key[second]["write_scope"]):
                _fail("WRITE_SCOPE_CONFLICT", "Independent tasks have overlapping write scope")

    digest = hashlib.sha256(_canonical(validated)).hexdigest()
    binding = provider_binding_digest or _BUNDLED_CATALOG_DIGEST
    if not isinstance(binding, str) or len(binding) != 64 or any(char not in "0123456789abcdef" for char in binding):
        _fail("PROVIDER_SCHEMA_DRIFT", "Provider binding digest is invalid")
    return ValidatedManifest(
        project_id=validated["project_id"],
        digest=digest,
        manifest_ref=f"manifest:{digest}",
        provider_binding_digest=binding,
        topological_order=tuple(order),
        canonical=validated,
    )
