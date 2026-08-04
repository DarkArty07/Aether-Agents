"""Strict manifest loading and fail-closed Aether project identity verification."""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_MANIFEST = Path("docs/releases/v0.20.0/CYCLE.yaml")
_CANDIDATE_VERSION = _MANIFEST.parent.name.removeprefix("v")
_LEDGER = Path(".aether/self_improvement.db")
_EVIDENCE = Path("docs/releases/v0.20.0/SELF_IMPROVEMENT_EVIDENCE.md")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_ALLOWED_STATUSES = {"implementation_in_progress", "implemented_default_off", "released_default_off"}

# Gates that record an event which has already happened. Their value is a
# historical fact, so the contract has to be able to state it. v0.20.0 was
# merged, tagged and published on 2026-07-28 while this block still declared all
# four closed, so the shipped artifact asserted that its own publication was
# unauthorized. A contract that cannot describe its own successor state forces
# the owner to choose between lying and deleting the cycle.
_HISTORICAL_GATES = frozenset({"merge", "tag", "release", "publication"})

# Gates that would change how the runtime behaves. While the candidate is
# default-off the contract must still assert these are closed, and a manifest
# claiming otherwise refuses to load. That interlock is deliberate, is covered by
# an existing acceptance test, and is NOT relaxed here. What was wrong is that
# the refusal was *silent* — callers now log it (see `hooks._initialize`) so an
# owner who grants a gate can tell an intentional interlock from a corrupt file.
_RUNTIME_GATES = frozenset(
    {
        "harmonia_activation",
        "coordination_key_creation",
        "runtime_restart",
        "deployment",
    }
)
_AUTHORIZATION_VALUES = frozenset({"authorized", "not_authorized"})


class ManifestError(ValueError):
    """The cycle manifest is absent, malformed, or violates a safety invariant."""


@dataclass(frozen=True)
class CycleManifest:
    """Validated subset of the active cycle contract used by the runtime plugin."""

    project_root: Path
    schema_version: int
    status: str
    candidate_version: str
    candidate_name: str
    next_minor_scope: str
    hypothesis: str
    logical_provider: str
    current_hermes_model: str
    ledger_path: Path
    release_evidence_path: Path
    digest: str
    open_gates: frozenset[str] = frozenset()


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{name} must be a mapping")
    return value


def _required_text(mapping: dict[str, Any], key: str, section: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{section}.{key} must be a non-empty string")
    return value.strip()


def _required_bool(mapping: dict[str, Any], key: str, section: str, expected: bool) -> None:
    if mapping.get(key) is not expected:
        raise ManifestError(f"{section}.{key} must be {str(expected).lower()}")


def load_cycle_manifest(project_root: Path) -> CycleManifest:
    """Load and validate the v0.20.0 contract without creating project state."""

    root = Path(project_root).expanduser().resolve()
    path = root / _MANIFEST
    raw = path.read_bytes()
    payload = yaml.safe_load(raw)
    data = _mapping(payload, "manifest")

    if data.get("schema_version") != 1:
        raise ManifestError("schema_version must be 1")
    status = _required_text(data, "status", "manifest")
    if status not in _ALLOWED_STATUSES:
        raise ManifestError(f"unsupported cycle status: {status}")

    semver = _mapping(data.get("semver"), "semver")
    candidate = _required_text(semver, "candidate_version", "semver")
    if not _SEMVER.fullmatch(candidate):
        raise ManifestError("semver.candidate_version must be MAJOR.MINOR.PATCH")
    # The loader reads one hard-coded release directory, so a manifest that
    # declares a different candidate would attribute evidence to a version that
    # does not exist at that path.
    if candidate != _CANDIDATE_VERSION:
        raise ManifestError(
            f"semver.candidate_version {candidate!r} does not match its release directory "
            f"({_CANDIDATE_VERSION!r})"
        )
    next_minor = _required_text(semver, "next_minor_scope", "semver")
    if next_minor != "undecided_pending_evidence":
        raise ManifestError("the next minor scope must remain undecided pending evidence")

    hypothesis = _required_text(_mapping(data.get("hypothesis"), "hypothesis"), "statement", "hypothesis")

    runtime = _mapping(data.get("runtime_contract"), "runtime_contract")
    _required_bool(runtime, "project_root_required", "runtime_contract", True)
    _required_bool(runtime, "talk_to_available_to_hermes", "runtime_contract", False)
    _required_bool(runtime, "harmonia_when_applicable", "runtime_contract", True)
    _required_bool(runtime, "ceremonial_harmonia_runs_forbidden", "runtime_contract", True)
    _required_bool(runtime, "cross_project_aether_mutation_forbidden", "runtime_contract", True)
    _required_bool(runtime, "direct_takeover_requires_cleanup_verification", "runtime_contract", True)

    provider = _mapping(data.get("provider"), "provider")
    logical_provider = _required_text(provider, "logical_provider", "provider")
    if logical_provider != "custom:aether-router":
        raise ManifestError("provider.logical_provider must remain custom:aether-router")
    _required_bool(provider, "provider_is_acceptance_authority", "provider", False)
    _required_bool(provider, "secrets_in_evidence_forbidden", "provider", True)

    signals = _mapping(data.get("next_version_signals"), "next_version_signals")
    _required_bool(signals, "automatically_approves_version", "next_version_signals", False)
    _required_bool(signals, "product_owner_approval_required", "next_version_signals", True)
    _required_bool(signals, "llm_coordinator_presumed", "next_version_signals", False)

    persistence = _mapping(data.get("persistence"), "persistence")
    ledger_relative = Path(_required_text(persistence, "operational_ledger_target", "persistence"))
    if ledger_relative != _LEDGER or ledger_relative.is_absolute() or ".." in ledger_relative.parts:
        raise ManifestError("persistence.operational_ledger_target is outside the approved project-local path")
    evidence_relative = Path(_required_text(persistence, "release_evidence_target", "persistence"))
    if evidence_relative != _EVIDENCE or evidence_relative.is_absolute() or ".." in evidence_relative.parts:
        raise ManifestError("persistence.release_evidence_target is outside the approved release path")
    if _required_text(persistence, "incoming_agent_context", "persistence") != "AGENTS.md":
        raise ManifestError("persistence.incoming_agent_context must be AGENTS.md")
    _required_bool(persistence, "context_projection_is_sole_authority", "persistence", False)

    authorization = _mapping(data.get("authorization"), "authorization")
    for key in ("documentation_alignment", "implementation_plan", "source_or_plugin_implementation"):
        if authorization.get(key) != "authorized":
            raise ManifestError(f"authorization.{key} must be authorized")
    for key in _RUNTIME_GATES:
        if authorization.get(key) != "not_authorized":
            raise ManifestError(
                f"authorization.{key} must remain not_authorized while the candidate is default-off"
            )
    open_gates = set()
    for key in _HISTORICAL_GATES:
        value = authorization.get(key)
        if value not in _AUTHORIZATION_VALUES:
            raise ManifestError(f"authorization.{key} must be authorized or not_authorized")
        if value == "authorized":
            open_gates.add(key)

    return CycleManifest(
        project_root=root,
        schema_version=1,
        status=status,
        candidate_version=candidate,
        candidate_name=_required_text(semver, "candidate_name", "semver"),
        next_minor_scope=next_minor,
        hypothesis=hypothesis,
        logical_provider=logical_provider,
        current_hermes_model=_required_text(provider, "current_hermes_model", "provider"),
        ledger_path=root / ledger_relative,
        release_evidence_path=root / evidence_relative,
        digest=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        open_gates=frozenset(open_gates),
    )


def verify_project_identity(project_root: Path) -> CycleManifest | None:
    """Return a validated cycle only for the canonical Aether repository shape.

    This function is deliberately side-effect free. Callers may create the ledger
    only after it succeeds.
    """

    try:
        root = Path(project_root).expanduser().resolve(strict=True)
        agents = root / "AGENTS.md"
        pyproject = root / "pyproject.toml"
        if not agents.is_file() or not pyproject.is_file() or not (root / ".git").exists():
            return None
        if not agents.read_text(encoding="utf-8").startswith("# Aether Agents"):
            return None
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if project.get("project", {}).get("name") != "aether-agents":
            return None
        return load_cycle_manifest(root)
    except (ManifestError, OSError, TypeError, UnicodeError, ValueError, yaml.YAMLError, tomllib.TOMLDecodeError):
        return None
