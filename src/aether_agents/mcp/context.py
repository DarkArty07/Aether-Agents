"""Transferable Morfeo context. Does not include the Hermes system prompt."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_SECRET_LINE = re.compile(
    r"(?i)(?:api[_-]?key|token|secret|password|authorization)\s*[:=]\s*\S+"
    r"|sk-[A-Za-z0-9]{8,}"
    r"|\b\d{6,}:[A-Za-z0-9_-]{20,}\b"
)


def section_record(name: str, text: str) -> dict[str, Any]:
    """Metadata safe to log, plus the redacted text the MCP client must receive."""

    raw = text or ""
    redacted, removed = _redact(raw)
    encoded = redacted.encode("utf-8")
    return {
        "name": name,
        "text": redacted,
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "redacted_lines": removed,
    }


def _redact(text: str) -> tuple[str, int]:
    removed = 0
    lines: list[str] = []
    for line in text.splitlines():
        if _SECRET_LINE.search(line):
            removed += 1
            lines.append("[redacted]")
        else:
            lines.append(line)
    return "\n".join(lines), removed


def build_snapshot(
    *,
    sections: dict[str, str],
    role: str,
    mode: str,
    project_id: str,
    project_root: str,
    tool_names: list[str],
) -> dict[str, Any]:
    """Freeze one bootstrap snapshot. A later memory write does not rewrite it."""

    ordered = (
        "soul",
        "user",
        "memory",
        "project_context",
        "skills",
    )
    rendered = {name: section_record(name, sections.get(name, "")) for name in ordered}
    body = {
        "role": role,
        "mode": mode,
        "project_id": project_id,
        "project_root": project_root,
        "sections": rendered,
        "tools": list(tool_names),
    }
    revision = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    body["context_revision"] = revision
    return body


def _canonical(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def log_records(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Section name, size and digest only. Never the private text."""

    sections = snapshot.get("sections") or {}
    records = []
    for name, record in sections.items():
        if not isinstance(record, dict):
            continue
        records.append(
            {
                "section": name,
                "bytes": record.get("bytes"),
                "sha256": record.get("sha256"),
                "redacted_lines": record.get("redacted_lines"),
            }
        )
    return records
