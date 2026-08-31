#!/usr/bin/env python3
"""Validate and aggregate portable Hermes patch-reconciliation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aether.hermes-patch-reconciliation.v1"
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
_UNIX_HOME = re.compile(r"(?<![A-Za-z0-9_$}>])/(?:" + "home" + r"|Users)/[A-Za-z0-9._-]+/")
_WINDOWS_HOME = re.compile(r"(?i)(?<![A-Za-z0-9_$}>])[A-Z]:\\" + "Users" + r"\\[^\\\s]+\\")
_PRIVATE_DESKTOP = re.compile(
    r"(?i)(?<![A-Za-z0-9_<])(?:" + "Desktop" + r"|Escritorio)/(?:agentes|dev)/"
)


class ReconciliationError(ValueError):
    """Raised for an evidence input that cannot support a portable aggregate."""


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


def reconcile(
    *,
    repository_root: Path,
    ledger_path: Path,
    entries_dir: Path,
    schema_path: Path,
    observed_at_utc: str,
    upstream_repository: str,
    upstream_revision: str,
) -> dict[str, Any]:
    """Validate fragment inputs and build the deterministic aggregate in memory."""

    if not _TIMESTAMP.fullmatch(observed_at_utc):
        raise ReconciliationError("observed_at_utc must be an explicit UTC timestamp ending in Z")
    if not _REVISION.fullmatch(upstream_revision):
        raise ReconciliationError("upstream revision must be an exact lowercase Git revision")
    if not upstream_repository.startswith("https://github.com/"):
        raise ReconciliationError("upstream repository must be a public GitHub URL")

    root = repository_root.resolve()
    ledger_path = _inside_root(root, ledger_path, "ledger")
    entries_dir = _inside_root(root, entries_dir, "entries directory")
    schema = _load_schema(schema_path)
    expected_ids = active_detailed_ledger_ids(ledger_path)
    records = _load_fragments(entries_dir, _validator_for(schema, "entry"))

    _validate_record_set(
        records=records,
        expected_ids=expected_ids,
        root=root,
        upstream_repository=upstream_repository,
        upstream_revision=upstream_revision,
    )
    records.sort(key=lambda record: _ledger_id_sort_key(record["id"]))
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "observed_at_utc": observed_at_utc,
        "upstream": {
            "repository": upstream_repository,
            "inspected_revision": upstream_revision,
        },
        "source_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "records": records,
        "overall_blockers": _overall_blockers(records),
    }
    _validate_instance(_validator_for(schema, "aggregate"), aggregate, "aggregate")
    return aggregate


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
    upstream_repository: str,
    upstream_revision: str,
) -> None:
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

    for record in records:
        identifier = record["id"]
        if identifier == "HLP-211" and "HLP-211b" not in record["components"]:
            raise ReconciliationError("HLP-211 must declare the combined HLP-211b component")
        if identifier == "HLP-226":
            components = set(record["components"])
            required_components = {"HLP-226", "HLP-226b"}
            missing_components = sorted(required_components - components)
            if missing_components:
                raise ReconciliationError(
                    "HLP-226 must declare the combined components: " + ", ".join(missing_components)
                )
            if not any(
                artifact["kind"] == "patch"
                and artifact["reference"]
                == "patches/hermes/HLP-226b-affinity-terminal-project-inheritance.patch"
                for artifact in record["artifact_verification"]["artifacts"]
            ):
                raise ReconciliationError(
                    "HLP-226 must declare the HLP-226b portable patch artifact"
                )
        if _contains_nonportable_value(record):
            raise ReconciliationError(f"non-portable/private content in fragment {identifier}")
        upstream = record["upstream"]
        if upstream["repository"] != upstream_repository:
            raise ReconciliationError(f"upstream repository disagreement for {identifier}")
        if upstream["inspected_revision"] != upstream_revision:
            raise ReconciliationError(f"upstream revision disagreement for {identifier}")
        _validate_retirement_candidacy(record)
        _validate_artifacts(record, root)


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
    return sorted(
        blockers, key=lambda blocker: (_ledger_id_sort_key(blocker["id"]), blocker["kind"])
    )


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
    parser.add_argument("--observed-at-utc", required=True)
    parser.add_argument("--upstream-repository", required=True)
    parser.add_argument("--upstream-revision", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        output = _inside_root(root, args.output, "output")
        preflight = _inside_root(root, args.preflight, "preflight")
        aggregate = reconcile(
            repository_root=root,
            ledger_path=args.ledger,
            entries_dir=args.entries_dir,
            schema_path=args.schema,
            observed_at_utc=args.observed_at_utc,
            upstream_repository=args.upstream_repository,
            upstream_revision=args.upstream_revision,
        )
        _write_text(output, json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
        _write_text(preflight, render_preflight(aggregate))
    except ReconciliationError as error:
        print(f"reconciliation validation failed: {error}", file=sys.stderr)
        return 2
    print(
        f"reconciliation validation passed: {output.relative_to(root)}, {preflight.relative_to(root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
