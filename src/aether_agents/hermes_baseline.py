"""Load the one authoritative Hermes release-baseline resource."""

from __future__ import annotations

import importlib.resources
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


class HermesBaselineError(RuntimeError):
    """The packaged Hermes baseline resource is unavailable or malformed."""


@dataclass(frozen=True, slots=True)
class HermesBaseline:
    repository: str
    tag: str
    tag_object: str
    commit: str
    distribution: str
    version: str
    python_requires: str
    observer_entry_point: str


@dataclass(frozen=True, slots=True)
class HistoricalSnapshot:
    path: str
    classification: str
    version: str
    commit: str


@dataclass(frozen=True, slots=True)
class DerivedDocument:
    path: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HermesBaselineResource:
    baseline: HermesBaseline
    derived_documents: tuple[DerivedDocument, ...]
    historical_snapshots: tuple[HistoricalSnapshot, ...]


_BASELINE_FIELDS = frozenset(HermesBaseline.__dataclass_fields__)
_RESOURCE_FIELDS = frozenset(
    {"schema_version", "baseline", "derived_documents", "historical_snapshots"}
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$", re.ASCII)
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$", re.ASCII)
_CLASSIFICATION_RE = re.compile(r"^[a-z][a-z_]{2,63}$", re.ASCII)


def _resource_bytes() -> bytes:
    resource = importlib.resources.files("aether_agents").joinpath("resources/hermes-baseline.json")
    try:
        return resource.read_bytes()
    except (FileNotFoundError, OSError) as error:
        raise HermesBaselineError("Hermes baseline resource is unavailable") from error


def _relative_path(value: Any) -> str:
    if not isinstance(value, str):
        raise HermesBaselineError("Hermes baseline path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise HermesBaselineError("Hermes baseline path is invalid")
    return path.as_posix()


def _baseline_from_record(value: Any) -> HermesBaseline:
    if not isinstance(value, dict) or set(value) != _BASELINE_FIELDS:
        raise HermesBaselineError("Hermes baseline identity shape is invalid")
    if not all(isinstance(item, str) and item for item in value.values()):
        raise HermesBaselineError("Hermes baseline identity contains an invalid value")
    baseline = HermesBaseline(**value)
    if (
        not baseline.repository.startswith("https://")
        or not baseline.repository.endswith(".git")
        or _TAG_RE.fullmatch(baseline.tag) is None
        or _SHA1_RE.fullmatch(baseline.tag_object) is None
        or _SHA1_RE.fullmatch(baseline.commit) is None
        or _VERSION_RE.fullmatch(baseline.version) is None
        or not baseline.distribution
        or not baseline.python_requires.startswith(">=")
        or "=" not in baseline.observer_entry_point
    ):
        raise HermesBaselineError("Hermes baseline identity values are invalid")
    return baseline


def _historical_snapshots(value: Any) -> tuple[HistoricalSnapshot, ...]:
    if not isinstance(value, list):
        raise HermesBaselineError("Hermes baseline historical snapshots are invalid")
    snapshots: list[HistoricalSnapshot] = []
    seen_paths: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "classification",
            "version",
            "commit",
        }:
            raise HermesBaselineError("Hermes baseline historical snapshot shape is invalid")
        path = _relative_path(item["path"])
        classification = item["classification"]
        version = item["version"]
        commit = item["commit"]
        if (
            path in seen_paths
            or not isinstance(classification, str)
            or _CLASSIFICATION_RE.fullmatch(classification) is None
            or not isinstance(version, str)
            or _VERSION_RE.fullmatch(version) is None
            or not isinstance(commit, str)
            or _SHA1_RE.fullmatch(commit) is None
        ):
            raise HermesBaselineError("Hermes baseline historical snapshot values are invalid")
        seen_paths.add(path)
        snapshots.append(HistoricalSnapshot(path, classification, version, commit))
    return tuple(snapshots)


def _derived_documents(value: Any) -> tuple[DerivedDocument, ...]:
    if not isinstance(value, list):
        raise HermesBaselineError("Hermes baseline document list is invalid")
    documents: list[DerivedDocument] = []
    seen_paths: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "fields"}:
            raise HermesBaselineError("Hermes baseline document shape is invalid")
        path = _relative_path(item["path"])
        fields = item["fields"]
        if (
            path in seen_paths
            or not isinstance(fields, list)
            or not fields
            or any(not isinstance(field, str) or field not in _BASELINE_FIELDS for field in fields)
            or len(set(fields)) != len(fields)
        ):
            raise HermesBaselineError("Hermes baseline document values are invalid")
        seen_paths.add(path)
        documents.append(DerivedDocument(path=path, fields=tuple(fields)))
    return tuple(documents)


def load_hermes_baseline_resource() -> HermesBaselineResource:
    """Load and validate the packaged, machine-readable release-baseline record."""

    try:
        payload = json.loads(_resource_bytes())
    except (UnicodeError, json.JSONDecodeError) as error:
        raise HermesBaselineError("Hermes baseline resource is malformed") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != _RESOURCE_FIELDS
        or payload["schema_version"] != 1
    ):
        raise HermesBaselineError("Hermes baseline resource shape is invalid")
    derived_documents = _derived_documents(payload["derived_documents"])
    if not derived_documents:
        raise HermesBaselineError("Hermes baseline document list is invalid")
    return HermesBaselineResource(
        baseline=_baseline_from_record(payload["baseline"]),
        derived_documents=derived_documents,
        historical_snapshots=_historical_snapshots(payload["historical_snapshots"]),
    )


def load_hermes_baseline() -> HermesBaseline:
    """Return the exact selected Hermes release identity."""

    return load_hermes_baseline_resource().baseline


__all__ = [
    "DerivedDocument",
    "HermesBaseline",
    "HermesBaselineError",
    "HermesBaselineResource",
    "HistoricalSnapshot",
    "load_hermes_baseline",
    "load_hermes_baseline_resource",
]
