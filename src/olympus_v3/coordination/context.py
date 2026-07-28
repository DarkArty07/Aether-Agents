"""Bounded, provenance-preserving R4 context rendering.

Rendered model context is data, not authority. Taint labels cannot prevent a model from
being persuaded; capability enforcement remains independent of this renderer.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .protocol import ValidationError

MAX_CONTEXT_ITEM_BYTES = 16_384
MAX_CONTEXT_ITEMS = 256
MAX_PROVENANCE_PARENTS = 64
_MAX_RENDER_BYTES = 1_048_576
_MAX_DEPTH = 32
_MAX_INT = (1 << 63) - 1
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_SECRET_REF = re.compile(r"^secretref:([a-z0-9][a-z0-9._:-]{0,127}):([a-z0-9][a-z0-9._:-]{0,127})$")
_AUTHORITATIVE_SOURCES = frozenset({"contract", "ledger", "capability_decision"})


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0, maximum: int = _MAX_INT) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValidationError(f"invalid {label}")
    return value


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


class Taint(StrEnum):
    TRUSTED_METADATA = "trusted_metadata"
    UNTRUSTED_TEXT = "untrusted_text"
    EXTERNAL_DATA = "external_data"
    MODEL_SUMMARY = "model_summary"
    SECRET_REFERENCE = "secret_reference"


@dataclass(frozen=True, slots=True)
class Provenance:
    project_id: str
    source_kind: str
    source_id: str
    event_id: str
    parent_ids: tuple[str, ...]
    taint: Taint
    authoritative: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        object.__setattr__(self, "source_kind", _id(self.source_kind, "source kind"))
        object.__setattr__(self, "source_id", _id(self.source_id, "source id"))
        object.__setattr__(self, "event_id", _id(self.event_id, "event id"))
        if not isinstance(self.parent_ids, tuple) or len(self.parent_ids) > MAX_PROVENANCE_PARENTS:
            raise ValidationError("invalid provenance parents")
        parents = tuple(_id(parent, "parent id") for parent in self.parent_ids)
        if len(set(parents)) != len(parents):
            raise ValidationError("duplicate provenance parent")
        object.__setattr__(self, "parent_ids", parents)
        if not isinstance(self.taint, Taint) or not isinstance(self.authoritative, bool):
            raise ValidationError("invalid provenance trust metadata")
        if self.authoritative and (
            self.taint is not Taint.TRUSTED_METADATA or self.source_kind not in _AUTHORITATIVE_SOURCES
        ):
            raise ValidationError("tainted content cannot be authoritative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "event_id": self.event_id,
            "parent_ids": list(self.parent_ids),
            "taint": self.taint.value,
            "authoritative": self.authoritative,
        }

    @classmethod
    def from_dict(cls, value: Any) -> Provenance:
        fields = {"project_id", "source_kind", "source_id", "event_id", "parent_ids", "taint", "authoritative"}
        _fields(value, fields, "provenance")
        if not isinstance(value["parent_ids"], list):
            raise ValidationError("invalid provenance parents")
        try:
            taint = Taint(value["taint"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid taint") from exc
        return cls(
            value["project_id"], value["source_kind"], value["source_id"], value["event_id"],
            tuple(value["parent_ids"]), taint, value["authoritative"],
        )


@dataclass(frozen=True, slots=True)
class ContextItem:
    item_id: str
    text: str
    provenance: Provenance
    priority: int
    required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _id(self.item_id, "context item id"))
        if not isinstance(self.text, str) or len(self.text.encode("utf-8")) > MAX_CONTEXT_ITEM_BYTES:
            raise ValidationError("invalid context item text")
        if not isinstance(self.provenance, Provenance):
            raise ValidationError("invalid context provenance")
        object.__setattr__(self, "priority", _integer(self.priority, "context priority"))
        if not isinstance(self.required, bool):
            raise ValidationError("invalid required flag")


@dataclass(frozen=True, slots=True)
class RenderedContext:
    text: str
    included_ids: tuple[str, ...]
    omitted_ids: tuple[str, ...]
    omission_summary: str
    byte_count: int


def _depth(item_id: str, by_id: dict[str, ContextItem], visiting: set[str], memo: dict[str, int]) -> int:
    if item_id in memo:
        return memo[item_id]
    if item_id in visiting:
        raise ValidationError("cyclic context provenance")
    visiting.add(item_id)
    item = by_id[item_id]
    depth = 1
    for parent in item.provenance.parent_ids:
        if parent not in by_id:
            raise ValidationError("missing context provenance parent")
        depth = max(depth, 1 + _depth(parent, by_id, visiting, memo))
    visiting.remove(item_id)
    memo[item_id] = depth
    return depth


def _block(item: ContextItem) -> str:
    provenance = item.provenance
    authoritative = "true" if provenance.authoritative else "false"
    return (
        f"[CONTEXT_ITEM id={item.item_id} source={provenance.source_kind}:{provenance.source_id} "
        f"event={provenance.event_id} taint={provenance.taint.value} authoritative={authoritative}]\n"
        f"<DATA>\n{item.text}\n</DATA>\n[/CONTEXT_ITEM]\n"
    )


def _omission(ids: tuple[str, ...]) -> str:
    if not ids:
        return ""
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return f"[OMISSION omitted_count={len(ids)} omitted_sha256={digest}]\n"


def render_context(
    items: tuple[ContextItem, ...],
    *,
    project_id: str,
    max_bytes: int,
    max_items: int,
    max_depth: int,
    allowed_secret_references: frozenset[str] = frozenset(),
) -> RenderedContext:
    project_id = _id(project_id, "project id")
    max_bytes = _integer(max_bytes, "max bytes", minimum=1, maximum=_MAX_RENDER_BYTES)
    max_items = _integer(max_items, "max items", minimum=1, maximum=MAX_CONTEXT_ITEMS)
    max_depth = _integer(max_depth, "max depth", minimum=1, maximum=_MAX_DEPTH)
    if not isinstance(items, tuple) or len(items) > MAX_CONTEXT_ITEMS or any(not isinstance(item, ContextItem) for item in items):
        raise ValidationError("invalid context items")
    if not isinstance(allowed_secret_references, frozenset):
        raise ValidationError("invalid secret reference allowlist")

    by_id = {item.item_id: item for item in items}
    if len(by_id) != len(items):
        raise ValidationError("duplicate context item id")
    for item in items:
        if item.provenance.project_id != project_id:
            raise ValidationError("context project mismatch")
        if item.provenance.taint is Taint.SECRET_REFERENCE:
            match = _SECRET_REF.fullmatch(item.text)
            if match is None or match.group(1) != project_id or item.text not in allowed_secret_references:
                raise ValidationError("invalid or unauthorized secret reference")
    memo: dict[str, int] = {}
    if any(_depth(item.item_id, by_id, set(), memo) > max_depth for item in items):
        raise ValidationError("context provenance exceeds maximum depth")

    ordered = sorted(items, key=lambda item: (not item.required, -item.priority, item.item_id))
    required = [item for item in ordered if item.required]
    if len(required) > max_items:
        raise ValidationError("required context exceeds item limit")

    included: list[ContextItem] = []
    body = ""
    for item in ordered:
        block = _block(item)
        if len(included) >= max_items or len((body + block).encode("utf-8")) > max_bytes:
            if item.required:
                raise ValidationError("required context exceeds byte limit")
            continue
        included.append(item)
        body += block

    included_ids = {item.item_id for item in included}
    omitted = tuple(item.item_id for item in ordered if item.item_id not in included_ids)
    summary = _omission(omitted)
    while len((body + summary).encode("utf-8")) > max_bytes:
        removable = next((index for index in range(len(included) - 1, -1, -1) if not included[index].required), None)
        if removable is None:
            raise ValidationError("required context leaves no room for omission metadata")
        del included[removable]
        body = "".join(_block(item) for item in included)
        included_ids = {item.item_id for item in included}
        omitted = tuple(item.item_id for item in ordered if item.item_id not in included_ids)
        summary = _omission(omitted)

    text = body + summary
    return RenderedContext(
        text,
        tuple(item.item_id for item in included),
        omitted,
        summary,
        len(text.encode("utf-8")),
    )


__all__ = [
    "ContextItem",
    "MAX_CONTEXT_ITEM_BYTES",
    "MAX_CONTEXT_ITEMS",
    "MAX_PROVENANCE_PARENTS",
    "Provenance",
    "RenderedContext",
    "Taint",
    "render_context",
]
