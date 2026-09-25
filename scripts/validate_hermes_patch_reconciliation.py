#!/usr/bin/env python3
"""Validate and aggregate portable Hermes patch-reconciliation evidence.

Two modes:

* **Generate** (default): validate the ledger fragments and write the aggregate plus
  the preflight decision aid.
* **Check** (``--check``): regenerate the same aggregate in memory from the committed
  inputs and compare it with the committed files.  Nothing is written; a stale, missing
  or malformed evidence file exits non-zero.  This answers whether the committed
  evidence matches the canonical reconciliation.
* **Candidate check** (``--candidate-check``): qualify one exact maintained-fork
  revision for a candidate release.  Every HLP stays in the evidence.  An entry whose
  ``candidate_requirement`` is ``required`` (including an entry that omits the field)
  must be present.  ``deferred`` stays visible and does not block or retire the HLP.

Reconciliation is performed against the *selected* Hermes source — the maintained fork
``DarkArty07/aether-hermes`` — not against the retired fixed public baseline.  Each
entry must account for its behavior at the selected revision: every repository-relative
component path it declares (or the paths of its declared portable patches) has to exist
in the supplied ``--fork-checkout`` tree at that exact commit.  An entry that is absent
or only partially present at the selected revision refuses preparation instead of being
silently accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aether.hermes-patch-reconciliation.v1"
#: The accepted maintained-fork source identity for Aether 1.0.
FORK_REPOSITORY = "https://github.com/DarkArty07/aether-hermes"
FORK_BRANCH = "aether-main"
DEFAULT_LEDGER = Path("HERMES_LOCAL_PATCHES.md")
DEFAULT_ENTRIES = Path(
    "specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries"
)
DEFAULT_SCHEMA = (
    ROOT
    / "specs"
    / "001-aether-v1-productization"
    / "contracts"
    / "hermes-patch-reconciliation.schema.json"
)
DEFAULT_OUTPUT = Path(
    "specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation.v1.json"
)
DEFAULT_PREFLIGHT = Path("specs/001-aether-v1-productization/evidence/hermes-patch-preflight.md")
_HLP_SECTION = re.compile(r"^##\s+(HLP-[0-9]+)\s+—", re.MULTILINE)
_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_REVISION = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_PATCH_TARGET = re.compile(r"^\+\+\+ b/(?P<path>.+)$", re.MULTILINE)
_REPO_RELATIVE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")
_UNIX_HOME = re.compile(r"(?<![A-Za-z0-9_$}>])/(?:" + "home" + r"|Users)/[A-Za-z0-9._-]+/")
_WINDOWS_HOME = re.compile(r"(?i)(?<![A-Za-z0-9_$}>])[A-Z]:\\" + "Users" + r"\\[^\\\s]+\\")
_PRIVATE_DESKTOP = re.compile(
    r"(?i)(?<![A-Za-z0-9_<])(?:" + "Desktop" + r"|Escritorio)/(?:agentes|dev)/"
)


class ReconciliationError(ValueError):
    """Raised for an evidence input that cannot support a portable aggregate."""


_CANDIDATE_REQUIREMENTS = frozenset({"required", "deferred"})


def entry_candidate_requirement(record: dict[str, Any]) -> str:
    """Return the closed candidate obligation for one HLP entry.

    A missing field is ``required``.  An unknown value is a schema/refusal error and
    is never treated as optional.
    """

    if "candidate_requirement" not in record:
        return "required"
    value = record["candidate_requirement"]
    if value not in _CANDIDATE_REQUIREMENTS:
        identifier = record.get("id", "<unknown>")
        raise ReconciliationError(
            f"{identifier} candidate_requirement {value!r} is not required or deferred"
        )
    return value


def candidate_qualification(aggregate: dict[str, Any]) -> dict[str, Any]:
    """Classify every HLP for one selected revision without retiring anything.

    Deferred absence stays in the evidence and is not a preparation blocker.
    Retirement gates and artifact verification are not rewritten.
    """

    required_hlps: list[str] = []
    deferred_hlps: list[dict[str, Any]] = []
    refusing: list[dict[str, str]] = []
    for record in aggregate["records"]:
        requirement = entry_candidate_requirement(record)
        selected = record["selected_source"]
        missing = [row["path"] for row in selected["paths"] if not row["present"]]
        if requirement == "deferred":
            deferred_hlps.append(
                {
                    "id": record["id"],
                    "presence": selected["presence"],
                    "missing": missing,
                }
            )
            continue
        required_hlps.append(record["id"])
        if selected["presence"] in {"absent", "partial"}:
            refusing.append(
                {
                    "id": record["id"],
                    "kind": "selected_source",
                    "detail": (
                        "Declared source path(s) missing at the selected revision "
                        f"{selected['revision']}: {', '.join(missing)}."
                    ),
                }
            )
    return {
        "required_hlps": required_hlps,
        "deferred_hlps": deferred_hlps,
        "refusing": refusing,
        "refusing_hlps": [item["id"] for item in refusing],
    }


def active_detailed_ledger_ids(ledger_path: Path) -> tuple[str, ...]:
    """Return the canonical detailed HLP IDs, independent of the summary table.

    The ledger's HLP level-two sections are its detailed active records.  Parsing
    those headings intentionally includes HLP-247, which the current summary
    table omits, and prevents the table from becoming an incomplete source of
    truth for reconciliation coverage.
    """

    try:
        ledger = ledger_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReconciliationError("cannot read canonical patch ledger") from error
    identifiers = [match.group(1) for match in _HLP_SECTION.finditer(ledger)]
    if not identifiers:
        raise ReconciliationError("canonical patch ledger has no detailed HLP sections")
    duplicates = sorted(
        {identifier for identifier in identifiers if identifiers.count(identifier) > 1}
    )
    if duplicates:
        raise ReconciliationError(
            f"canonical patch ledger has duplicate IDs: {', '.join(duplicates)}"
        )
    return tuple(sorted(identifiers, key=_ledger_id_sort_key))


def _selected_source_paths(record: dict[str, Any], root: Path) -> list[str]:
    """Return the repository-relative paths that prove this behavior in the fork."""

    paths = [component for component in record["components"] if "/" in component]
    if not paths:
        for artifact in record["artifact_verification"]["artifacts"]:
            if artifact["kind"] != "patch":
                continue
            patch_path = Path(artifact["reference"])
            if patch_path.is_absolute() or ".." in patch_path.parts:
                raise ReconciliationError(f"non-portable patch reference for {record['id']}")
            try:
                patch_bytes = (root / patch_path).read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise ReconciliationError(
                    f"cannot read declared patch for {record['id']}"
                ) from error
            paths.extend(
                match.group("path").strip() for match in _PATCH_TARGET.finditer(patch_bytes)
            )
    unique = sorted({path for path in paths if path and path != "/dev/null"})
    for path in unique:
        if (
            path.startswith("/")
            or ".." in Path(path).parts
            or _REPO_RELATIVE.fullmatch(path) is None
        ):
            raise ReconciliationError(f"non-portable source path for {record['id']}: {path}")
    return unique


def selected_source_record(
    record: dict[str, Any],
    *,
    root: Path,
    fork_root: Path,
    repository: str,
    revision: str,
) -> dict[str, Any]:
    """Prove one entry's declared source paths at the selected fork revision."""

    paths = _selected_source_paths(record, root)
    if not paths:
        return {
            "repository": repository,
            "revision": revision,
            "presence": "unverified",
            "paths": [],
            "unverified_reason": (
                "no repository-relative component path or declared portable patch path "
                "is recorded for this entry"
            ),
        }
    rows = [
        {
            "path": path,
            "present": (fork_root / path).is_file() and not (fork_root / path).is_symlink(),
        }
        for path in paths
    ]
    present = sum(1 for row in rows if row["present"])
    if present == len(rows):
        presence = "present"
    elif present:
        presence = "partial"
    else:
        presence = "absent"
    return {
        "repository": repository,
        "revision": revision,
        "presence": presence,
        "paths": rows,
        "unverified_reason": None,
    }


def reconcile(
    *,
    repository_root: Path,
    ledger_path: Path,
    entries_dir: Path,
    schema_path: Path,
    observed_at_utc: str,
    selected_revision: str,
    upstream_repository: str | None = None,
    upstream_revision: str | None = None,
    fork_root: Path | None = None,
    fork_repository: str = FORK_REPOSITORY,
) -> dict[str, Any]:
    """Validate fragment inputs and build the deterministic aggregate in memory.

    ``selected_revision`` is the maintained-fork commit the evidence must be current at.
    ``upstream_repository``/``upstream_revision`` record the historical public-source
    inspection the fragments were written against; they default to the fragments'
    agreed value and can never be invented by the caller.
    """

    if not _TIMESTAMP.fullmatch(observed_at_utc):
        raise ReconciliationError("observed_at_utc must be an explicit UTC timestamp ending in Z")
    if not _REVISION.fullmatch(selected_revision):
        raise ReconciliationError("selected revision must be an exact lowercase Git revision")

    root = repository_root.resolve()
    ledger_path = _inside_root(root, ledger_path, "ledger")
    entries_dir = _inside_root(root, entries_dir, "entries directory")
    schema = _load_schema(schema_path)
    expected_ids = active_detailed_ledger_ids(ledger_path)
    records = _load_fragments(entries_dir, _validator_for(schema, "entry"))

    inspected_repository, inspected_revision = _validate_record_set(
        records=records,
        expected_ids=expected_ids,
        root=root,
    )
    if upstream_repository is not None and upstream_repository != inspected_repository:
        raise ReconciliationError("upstream repository disagreement with the recorded fragments")
    if upstream_revision is not None and upstream_revision != inspected_revision:
        raise ReconciliationError("upstream revision disagreement with the recorded fragments")
    upstream_repository = inspected_repository
    upstream_revision = inspected_revision
    if fork_root is not None:
        fork_repository = _verified_fork_checkout(fork_root, selected_revision)
    selected = [
        selected_source_record(
            record,
            root=root,
            fork_root=fork_root if fork_root is not None else root,
            repository=fork_repository,
            revision=selected_revision,
        )
        for record in records
    ]
    for record, resolution in zip(records, selected):
        record["selected_source"] = resolution
    _validate_selected_source(records, selected, fork_resolved=fork_root is not None)
    records.sort(key=lambda record: _ledger_id_sort_key(record["id"]))
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "observed_at_utc": observed_at_utc,
        "upstream": {
            "repository": upstream_repository,
            "inspected_revision": upstream_revision,
        },
        "selected_source": {
            "repository": fork_repository,
            "revision": selected_revision,
            "resolved_from_checkout": fork_root is not None,
            "present": sum(1 for item in selected if item["presence"] == "present"),
            "partial": sum(1 for item in selected if item["presence"] == "partial"),
            "absent": sum(1 for item in selected if item["presence"] == "absent"),
            "unverified": sum(1 for item in selected if item["presence"] == "unverified"),
        },
        "source_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "records": records,
        "overall_blockers": _overall_blockers(records),
    }
    _validate_instance(_validator_for(schema, "aggregate"), aggregate, "aggregate")
    return aggregate


def _validate_selected_source(
    records: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    *,
    fork_resolved: bool,
) -> None:
    """Refuse a selected-source claim that a resolution could not check."""

    if any(item["presence"] != "unverified" for item in selected) and not fork_resolved:
        raise ReconciliationError(
            "selected-source presence claims require --fork-checkout at the selected revision"
        )
    for record, item in zip(records, selected):
        if item["presence"] in {"absent", "partial"}:
            missing = [row["path"] for row in item["paths"] if not row["present"]]
            if not missing:
                raise ReconciliationError(
                    f"selected-source verdict is incoherent for {record['id']}"
                )


def _verified_fork_checkout(fork_root: Path, revision: str) -> str:
    """Prove a supplied fork checkout is the exact clean selected revision."""

    try:
        root = fork_root.expanduser().resolve(strict=True)
    except OSError as error:
        raise ReconciliationError("--fork-checkout is unavailable") from error
    if not root.is_dir():
        raise ReconciliationError("--fork-checkout is not a directory")
    head = _git(root, "rev-parse", "HEAD")
    if head != revision:
        raise ReconciliationError(
            f"--fork-checkout HEAD {head} is not the selected revision {revision}"
        )
    dirty = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise ReconciliationError("--fork-checkout is dirty")
    repository = _git(root, "remote", "get-url", "origin", check=False)
    normalized = repository.strip().removesuffix(".git").rstrip("/")
    for prefix in ("git@github.com:", "ssh://git@github.com/"):
        if normalized.startswith(prefix):
            normalized = "https://github.com/" + normalized.removeprefix(prefix)
    if normalized != FORK_REPOSITORY:
        raise ReconciliationError("--fork-checkout origin is not the maintained fork")
    return normalized


def _git(checkout: Path, *arguments: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise ReconciliationError(f"Git inspection failed ({arguments[0]})")
    return completed.stdout.strip()


def render_preflight(aggregate: dict[str, Any]) -> str:
    """Render the bounded human decision aid from an already-validated aggregate."""

    records = aggregate["records"]
    remaining = [record for record in records if record["retirement_recommendation"] == "retain"]
    equivalents = [
        record for record in records if record["upstream"]["disposition"] == "upstream_verified"
    ]
    lines = [
        "# Hermes patch reconciliation preflight",
        "",
        f"Observation timestamp: `{aggregate['observed_at_utc']}`",
        "",
        "Upstream inspected: "
        f"`{aggregate['upstream']['repository']}@{aggregate['upstream']['inspected_revision']}`",
        "",
        f"Source ledger SHA-256: `{aggregate['source_ledger_sha256']}`",
        "",
        "## Remaining local guarantees",
        "",
    ]
    lines.extend(_record_bullets(remaining, lambda record: record["summary"]))
    lines.extend(("", "## Qualified upstream equivalents", ""))
    lines.extend(
        _record_bullets(
            equivalents,
            lambda record: (
                f"Qualified source disposition: {record['upstream']['disposition']}; "
                f"retirement recommendation: {record['retirement_recommendation']}."
            ),
        )
    )
    lines.extend(("", "## Retirement blockers", ""))
    lines.extend(
        [
            f"- `{blocker['id']}` ({blocker['kind']}): {blocker['detail']}"
            for blocker in aggregate["overall_blockers"]
        ]
        or ["- None recorded."]
    )
    lines.extend(("", "## Artifact integrity", ""))
    lines.extend(
        [f"- `{record['id']}`: {record['artifact_verification']['status']}" for record in records]
        or ["- None recorded."]
    )
    lines.extend(_render_selected_source(aggregate))
    lines.extend(
        (
            "",
            "## Safe next decisions",
            "",
            "- Retain every local guarantee whose exact-revision full behavioral gate is not passed.",
            "- Execute the recorded gates on a separately selected, read-only candidate revision before any retirement decision.",
            "- No final runtime is selected by this report, and it does not make a release claim.",
            "",
        )
    )
    return "\n".join(lines)


def _render_selected_source(aggregate: dict[str, Any]) -> list[str]:
    selected = aggregate["selected_source"]
    lines = [
        "",
        "## Selected maintained-fork source",
        "",
        f"Selected source: `{selected['repository']}@{selected['revision']}`"
        f" (presence resolved from a checkout: `{str(selected['resolved_from_checkout']).lower()}`)",
        "",
        "| Verdict | Entries |",
        "| --- | --- |",
        f"| present | {selected['present']} |",
        f"| partial | {selected['partial']} |",
        f"| absent | {selected['absent']} |",
        f"| unverified | {selected['unverified']} |",
        "",
    ]
    unresolved = [
        record
        for record in aggregate["records"]
        if record["selected_source"]["presence"] in {"partial", "absent", "unverified"}
    ]
    for record in unresolved:
        resolution = record["selected_source"]
        if resolution["presence"] == "unverified":
            detail = resolution["unverified_reason"]
        else:
            detail = "missing: " + ", ".join(
                row["path"] for row in resolution["paths"] if not row["present"]
            )
        lines.append(f"- `{record['id']}`: {resolution['presence']} — {detail}")
    if not unresolved:
        lines.append("- Every declared behavior path is present at the selected revision.")
    return lines


def _inside_root(root: Path, candidate: Path, label: str) -> Path:
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ReconciliationError(f"{label} must remain inside the repository root") from error
    return resolved


def _ledger_id_sort_key(identifier: str) -> tuple[int, str]:
    return (int(identifier.removeprefix("HLP-")), identifier)


def _load_fragments(
    entries_dir: Path, validator: jsonschema.Draft202012Validator
) -> list[dict[str, Any]]:
    if not entries_dir.is_dir():
        raise ReconciliationError("fragment entries directory does not exist")
    paths = sorted(path for path in entries_dir.glob("*.json") if path.is_file())
    if not paths:
        raise ReconciliationError("fragment entries directory has no JSON inputs")
    records: list[dict[str, Any]] = []
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReconciliationError(f"cannot parse fragment JSON: {path.name}") from error
        _validate_instance(validator, value, f"fragment {path.name}")
        if not isinstance(value, dict):
            raise ReconciliationError(f"fragment {path.name} is not an object")
        records.append(value)
    return records


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReconciliationError("cannot parse reconciliation schema") from error
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        aggregate_version = schema["$defs"]["aggregate"]["properties"]["schema_version"]["const"]
    except (KeyError, jsonschema.SchemaError) as error:
        raise ReconciliationError("invalid reconciliation schema") from error
    if aggregate_version != SCHEMA_VERSION:
        raise ReconciliationError("schema version drift")
    return schema


def _validator_for(schema: dict[str, Any], definition: str) -> jsonschema.Draft202012Validator:
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/$defs/{definition}",
        "$defs": schema["$defs"],
    }
    return jsonschema.Draft202012Validator(wrapper, format_checker=jsonschema.FormatChecker())


def _validate_instance(
    validator: jsonschema.Draft202012Validator, instance: Any, label: str
) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "root"
        raise ReconciliationError(
            f"schema validation failed for {label} at {location}: {first.message}"
        )


def _validate_record_set(
    *,
    records: list[dict[str, Any]],
    expected_ids: tuple[str, ...],
    root: Path,
) -> tuple[str, str]:
    identifiers = [record["id"] for record in records]
    duplicates = sorted(
        {identifier for identifier in identifiers if identifiers.count(identifier) > 1}
    )
    if duplicates:
        raise ReconciliationError(f"duplicate fragment IDs: {', '.join(duplicates)}")
    expected = set(expected_ids)
    observed = set(identifiers)
    unknown = sorted(observed - expected, key=_ledger_id_sort_key)
    if unknown:
        raise ReconciliationError(f"unknown ledger IDs: {', '.join(unknown)}")
    missing = sorted(expected - observed, key=_ledger_id_sort_key)
    if missing:
        raise ReconciliationError(f"missing ledger IDs: {', '.join(missing)}")

    inspected = {
        (record["upstream"]["repository"], record["upstream"]["inspected_revision"])
        for record in records
    }
    if len(inspected) != 1:
        raise ReconciliationError("fragments disagree on the public-source inspection identity")
    upstream_repository, upstream_revision = inspected.pop()

    for record in records:
        identifier = record["id"]
        if identifier == "HLP-211" and "HLP-211b" not in record["components"]:
            raise ReconciliationError("HLP-211 must declare the combined HLP-211b component")
        if identifier == "HLP-226":
            components = set(record["components"])
            required_components = {"HLP-226", "HLP-226b", "HLP-226c"}
            missing_components = sorted(required_components - components)
            if missing_components:
                raise ReconciliationError(
                    "HLP-226 must declare the combined components: " + ", ".join(missing_components)
                )
            declared_patches = {
                artifact["reference"]
                for artifact in record["artifact_verification"]["artifacts"]
                if artifact["kind"] == "patch"
            }
            required_patches = {
                "patches/hermes/HLP-226b-affinity-terminal-project-inheritance.patch",
                "patches/hermes/HLP-226c-cross-board-project-inheritance.patch",
            }
            missing_patches = sorted(required_patches - declared_patches)
            if missing_patches:
                raise ReconciliationError(
                    "HLP-226 must declare the combined portable patch artifacts: "
                    + ", ".join(missing_patches)
                )
        if _contains_nonportable_value(record):
            raise ReconciliationError(f"non-portable/private content in fragment {identifier}")
        _validate_retirement_candidacy(record)
        _validate_artifacts(record, root)
    return upstream_repository, upstream_revision


def _contains_nonportable_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(
            _UNIX_HOME.search(value)
            or _WINDOWS_HOME.search(value)
            or _PRIVATE_DESKTOP.search(value)
        )
    if isinstance(value, dict):
        return any(_contains_nonportable_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_nonportable_value(item) for item in value)
    return False


def _validate_retirement_candidacy(record: dict[str, Any]) -> None:
    if record["retirement_recommendation"] == "retain":
        return
    gate = record["retirement_gate"]
    has_test = any(item["kind"] == "test" for item in gate["evidence"])
    if gate["status"] != "passed" or not has_test:
        raise ReconciliationError(
            f"{record['id']} retirement candidacy requires an exact-revision full passed gate"
        )


def _validate_artifacts(record: dict[str, Any], root: Path) -> None:
    verification = record["artifact_verification"]
    artifacts = verification["artifacts"]
    if verification["status"] == "passed" and any(
        artifact["result"] in {"failed", "unavailable"} for artifact in artifacts
    ):
        raise ReconciliationError(
            f"{record['id']} artifact verification status cannot be passed with "
            "a failed or unavailable declared artifact"
        )
    for artifact in artifacts:
        if artifact["kind"] != "patch":
            continue
        reference = artifact["reference"]
        artifact_path = Path(reference)
        if artifact_path.is_absolute() or ".." in artifact_path.parts:
            raise ReconciliationError(f"non-portable artifact reference for {record['id']}")
        path = (root / artifact_path).resolve()
        try:
            path.relative_to(root)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, ValueError) as error:
            raise ReconciliationError(
                f"cannot read referenced patch artifact for {record['id']}"
            ) from error
        if actual != artifact["ledger_sha256"] or actual != artifact["computed_sha256"]:
            raise ReconciliationError(f"artifact digest mismatch for {record['id']}")
        if artifact["checksum_status"] != "passed" or artifact["parse_status"] != "passed":
            raise ReconciliationError(
                f"artifact verification status is not passed for {record['id']}"
            )


def _overall_blockers(records: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for record in records:
        identifier = record["id"]
        gate = record["retirement_gate"]
        if gate["status"] != "passed":
            blockers.append(
                {
                    "id": identifier,
                    "kind": "retirement_gate",
                    "detail": f"Retirement gate status is {gate['status']}.",
                }
            )
        artifact = record["artifact_verification"]
        if artifact["status"] in {"failed", "unavailable"}:
            detail = artifact["blocker"] or f"Artifact verification status is {artifact['status']}."
            blockers.append({"id": identifier, "kind": "artifact", "detail": detail})
        uncertainty = record["blocking_uncertainty"]
        items = [uncertainty] if isinstance(uncertainty, str) else uncertainty
        blockers.extend(
            {"id": identifier, "kind": "uncertainty", "detail": detail} for detail in items
        )
        selected = record.get("selected_source")
        if isinstance(selected, dict) and selected.get("presence") in {"absent", "partial"}:
            missing = ", ".join(row["path"] for row in selected["paths"] if not row["present"])
            blockers.append(
                {
                    "id": identifier,
                    "kind": "selected_source",
                    "detail": (
                        f"Declared source path(s) missing at the selected revision "
                        f"{selected['revision']}: {missing}."
                    ),
                }
            )
        elif isinstance(selected, dict) and selected.get("presence") == "unverified":
            blockers.append(
                {
                    "id": identifier,
                    "kind": "selected_source_evidence",
                    "detail": str(selected.get("unverified_reason")),
                }
            )
    return sorted(
        blockers, key=lambda blocker: (_ledger_id_sort_key(blocker["id"]), blocker["kind"])
    )


def selected_source_blockers(aggregate: dict[str, Any]) -> list[dict[str, str]]:
    """Return the blockers that refuse candidate preparation.

    Only a behavior that is absent or partially present at the selected revision
    refuses preparation.  ``selected_source_evidence`` records an entry that declares no
    source path at all, so no mechanical presence claim is possible; it stays visible in
    the aggregate and in the local preview instead of being silently accepted or
    silently failing the route.
    """

    return [
        blocker for blocker in aggregate["overall_blockers"] if blocker["kind"] == "selected_source"
    ]


def _record_bullets(records: Iterable[dict[str, Any]], detail: Any) -> list[str]:
    bullets = [f"- `{record['id']}`: {detail(record)}" for record in records]
    return bullets or ["- None recorded."]


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--entries-dir", type=Path, default=DEFAULT_ENTRIES)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--observed-at-utc",
        default=None,
        help="explicit UTC timestamp ending in Z; required to generate, ignored by --check",
    )
    parser.add_argument(
        "--selected-revision",
        default=None,
        help="maintained-fork commit the evidence must be current at",
    )
    parser.add_argument(
        "--upstream-repository",
        default=None,
        help="historical public-source repository; defaults to the fragments' agreed value",
    )
    parser.add_argument(
        "--upstream-revision",
        default=None,
        help="historical public-source revision; defaults to the fragments' agreed value",
    )
    parser.add_argument(
        "--fork-checkout",
        type=Path,
        default=None,
        help="clean maintained-fork checkout at --upstream-revision used to resolve presence",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="compare regenerated evidence with the committed files; never write",
    )
    mode.add_argument(
        "--candidate-check",
        action="store_true",
        help=(
            "qualify required HLP presence at --selected-revision; "
            "deferred HLPs stay visible and do not block; never write"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable summary")
    return parser


def _candidate_summary(aggregate: dict[str, Any], qualification: dict[str, Any]) -> dict[str, Any]:
    """Return the public candidate qualification record.

    Paths here are repository-relative Hermes paths already stored in the ledger.
    Checkout paths and other private locations are not included.
    """

    refusing = qualification["refusing"]
    return {
        "status": "qualified" if not refusing else "refused",
        "schema_version": aggregate["schema_version"],
        "observed_at_utc": aggregate["observed_at_utc"],
        "selected_source": aggregate["selected_source"],
        "selected_revision": aggregate["selected_source"]["revision"],
        "records": len(aggregate["records"]),
        "required_hlps": qualification["required_hlps"],
        "deferred_hlps": qualification["deferred_hlps"],
        "refusing": refusing,
        "refusing_hlps": qualification["refusing_hlps"],
        "unverified": [
            record["id"]
            for record in aggregate["records"]
            if record["selected_source"]["presence"] == "unverified"
        ],
    }


def _candidate_check(
    *,
    root: Path,
    args: argparse.Namespace,
    output: Path,
) -> tuple[int, dict[str, Any] | None, str]:
    """Qualify one selected revision.  Do not compare or rewrite committed evidence."""

    if args.selected_revision is None:
        return 2, None, "--selected-revision is required for candidate qualification"
    if args.fork_checkout is None:
        return 2, None, "--fork-checkout is required for candidate qualification"
    observed_at_utc = "2026-09-24T00:00:00Z"
    if output.is_file():
        try:
            committed = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            committed = None
        if isinstance(committed, dict):
            stamp = committed.get("observed_at_utc")
            if isinstance(stamp, str) and _TIMESTAMP.fullmatch(stamp):
                observed_at_utc = stamp
    aggregate = reconcile(
        repository_root=root,
        ledger_path=args.ledger,
        entries_dir=args.entries_dir,
        schema_path=args.schema,
        observed_at_utc=observed_at_utc,
        selected_revision=args.selected_revision,
        upstream_repository=args.upstream_repository,
        upstream_revision=args.upstream_revision,
        fork_root=args.fork_checkout,
    )
    qualification = candidate_qualification(aggregate)
    if qualification["refusing"]:
        identifiers = ", ".join(qualification["refusing_hlps"])
        return (
            2,
            aggregate,
            f"required HLP behavior is absent at the selected revision: {identifiers}",
        )
    return 0, aggregate, "candidate runtime satisfies required HLP coverage"


def _summary(aggregate: dict[str, Any], status: str) -> dict[str, Any]:
    refusing = selected_source_blockers(aggregate)
    return {
        "status": status,
        "schema_version": aggregate["schema_version"],
        "observed_at_utc": aggregate["observed_at_utc"],
        "selected_source": aggregate["selected_source"],
        "records": len(aggregate["records"]),
        "refusing": [
            {"id": blocker["id"], "kind": blocker["kind"], "detail": blocker["detail"]}
            for blocker in refusing
        ],
        "unverified": [
            record["id"]
            for record in aggregate["records"]
            if record["selected_source"]["presence"] == "unverified"
        ],
    }


def _check(
    *,
    root: Path,
    args: argparse.Namespace,
    output: Path,
    preflight: Path,
) -> tuple[int, dict[str, Any] | None, str]:
    """Regenerate the aggregate in memory and compare it with the committed files."""

    if not output.is_file() or not preflight.is_file():
        return 2, None, "committed reconciliation evidence is missing"
    try:
        committed = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 2, None, "committed reconciliation aggregate is unreadable"
    observed_at_utc = committed.get("observed_at_utc")
    if not isinstance(observed_at_utc, str) or not _TIMESTAMP.fullmatch(observed_at_utc):
        return 2, None, "committed reconciliation aggregate has no observation timestamp"
    selected_revision = args.selected_revision or (
        committed.get("selected_source", {}).get("revision")
        if isinstance(committed.get("selected_source"), dict)
        else None
    )
    if not isinstance(selected_revision, str) or not _REVISION.fullmatch(selected_revision):
        return 2, None, "no selected maintained-fork revision is available to check"
    aggregate = reconcile(
        repository_root=root,
        ledger_path=args.ledger,
        entries_dir=args.entries_dir,
        schema_path=args.schema,
        observed_at_utc=observed_at_utc,
        selected_revision=selected_revision,
        upstream_repository=args.upstream_repository,
        upstream_revision=args.upstream_revision,
        fork_root=args.fork_checkout,
    )
    if committed != aggregate:
        differences = sorted(
            key
            for key in set(committed) | set(aggregate)
            if committed.get(key) != aggregate.get(key)
        )
        return (
            2,
            aggregate,
            (
                "committed reconciliation evidence is stale; differing sections: "
                + ", ".join(differences)
            ),
        )
    committed_preflight = preflight.read_text(encoding="utf-8")
    rendered = render_preflight(aggregate)
    if committed_preflight != rendered:
        return 2, aggregate, "committed reconciliation preflight is stale"
    return 0, aggregate, "reconciliation evidence is current"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        output = _inside_root(root, args.output, "output")
        preflight = _inside_root(root, args.preflight, "preflight")
        if args.check:
            code, aggregate, message = _check(
                root=root,
                args=args,
                output=output,
                preflight=preflight,
            )
            if args.json and aggregate is not None:
                print(json.dumps(_summary(aggregate, "current" if code == 0 else "stale")))
            if code != 0:
                print(f"reconciliation validation failed: {message}", file=sys.stderr)
                return code
            print(f"reconciliation validation passed: {message}")
            return 0
        if args.candidate_check:
            code, aggregate, message = _candidate_check(
                root=root,
                args=args,
                output=output,
            )
            qualification = candidate_qualification(aggregate) if aggregate is not None else None
            if args.json and aggregate is not None and qualification is not None:
                print(json.dumps(_candidate_summary(aggregate, qualification)))
            if code != 0:
                print(f"candidate qualification failed: {message}", file=sys.stderr)
                return code
            print(f"candidate qualification passed: {message}")
            return 0
        if args.observed_at_utc is None:
            print(
                "reconciliation validation failed: --observed-at-utc is required to generate",
                file=sys.stderr,
            )
            return 2
        if args.selected_revision is None:
            print(
                "reconciliation validation failed: --selected-revision is required to generate",
                file=sys.stderr,
            )
            return 2
        aggregate = reconcile(
            repository_root=root,
            ledger_path=args.ledger,
            entries_dir=args.entries_dir,
            schema_path=args.schema,
            observed_at_utc=args.observed_at_utc,
            selected_revision=args.selected_revision,
            upstream_repository=args.upstream_repository,
            upstream_revision=args.upstream_revision,
            fork_root=args.fork_checkout,
        )
        _write_text(output, json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
        _write_text(preflight, render_preflight(aggregate))
    except ReconciliationError as error:
        print(f"reconciliation validation failed: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_summary(aggregate, "generated")))
    print(
        f"reconciliation validation passed: {output.relative_to(root)}, {preflight.relative_to(root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
