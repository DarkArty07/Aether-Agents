#!/usr/bin/env python3
"""Minimal Aether pre-tool guard for irreversible/external edge effects.

Aether roles share one trusted local-user boundary. Ordinary local and reversible
work is governed by scope, Git, tests, review, and rollback — not by this hook.
The guard blocks only high-confidence edge effects plus malformed hook input.

It intentionally has no Kanban/SQLite/Git subprocess dependency and does not
infer role ownership, task size, workspace confinement, or routing from shell
text. Keep this file small: expanding the protected-effect families is a design
change owned by R10/PD-71, not an implementation convenience.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, NoReturn

BLOCK_EXIT = 2
ROLE = Path(__file__).resolve().parents[1].name.casefold()
VALID_ROLES = {"morfeo", "supervisor", "implementer"}

DURABLE_TOOLS = {
    "kanban_create",
    "kanban_complete",
    "kanban_block",
    "kanban_request_review",
    "kanban_request_changes",
    "kanban_heartbeat",
    "kanban_comment",
    "kanban_attach",
    "kanban_attach_url",
    "memory",
}

PLACEHOLDERS = {
    "",
    "[redacted]",
    "<redacted>",
    "redacted",
    "***",
    "dummy",
    "fake",
    "test",
    "test-only",
    "password",
    "example",
    "example-only",
    "changeme",
    "not-set",
    "none",
    "null",
}

SENSITIVE_KEYS = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|"
    r"client[_-]?secret|password|passwd|private[_-]?key|secret[_-]?key|"
    r"connection[_-]?string|credential)"
)

HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bxapp-\d+-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"(?i)\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic)\s+\S+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/]+:[^\s@/]+@"),
    re.compile(r"(?i)[?&](?:token|access_token|api_key|key|signature|sig)=[^&#\s]{8,}"),
)

BROAD_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|"
        r"password|passwd|private[_-]?key|secret[_-]?key)\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)

# High-confidence credential creation/acquisition. These operations change the
# authority available to the local agent and therefore stay outside normal work.
CREDENTIAL_OPERATION_RE = re.compile(
    r"(?is)(?:"
    r"\b(?:gh|glab|gcloud|az|hermes|docker|npm|pnpm|yarn|pip|twine)\s+(?:auth\s+)?login\b|"
    r"\baws\s+configure\b|"
    r"\bgit\s+credential\b|"
    r"\bssh-keygen\b|"
    r"\bgpg\s+(?:--gen-key|--full-generate-key)\b|"
    r"\bopenssl\s+(?:genrsa|genpkey)\b|"
    r"\b(?:keyring\s+set|secret-tool\s+store|pass\s+insert|op\s+item\s+create|vault\s+write)\b|"
    r"\bkubectl\s+create\s+secret\b|"
    r"\b(?:oauth|device[-_ ]?code)\s+(?:login|authorize|flow)\b"
    r")"
)

# Obvious remote/public mutations. The policy deliberately omits local database
# migrations, local branches/commits, package installation, builds, and tests.
REMOTE_MUTATION_RE = re.compile(
    r"(?is)(?:"
    r"\bgit\s+(?:[^\n;&|]*\s)?push\b|"
    r"\bgh\s+(?:pr\s+(?:create|merge|close)|release\s+(?:create|delete)|api\b[^\n;&|]*(?:(?:--method|-X)\s+(?:POST|PUT|PATCH|DELETE)\b))|"
    r"\bglab\s+(?:mr\s+(?:create|merge|close)|release\s+create)|"
    r"\b(?:npm|pnpm|yarn|cargo|gem)\s+publish\b|"
    r"\b(?:twine\s+upload|dotnet\s+nuget\s+push|docker\s+push)\b|"
    r"\b(?:kubectl\s+(?:apply|create|delete|patch|replace|scale|rollout)|helm\s+(?:install|upgrade|uninstall))\b|"
    r"\b(?:terraform|tofu)\s+(?:apply|destroy|import)\b|"
    r"\bpulumi\s+(?:up|destroy)\b|"
    r"\b(?:fly\s+deploy|vercel\s+(?:deploy|--prod)|netlify\s+deploy|railway\s+up)\b|"
    r"\b(?:gcloud\s+(?:app|functions|run)\s+deploy|aws\s+cloudformation\s+(?:deploy|delete-stack)|az\s+deployment\s+)\b|"
    r"\bcurl\b[^\n]*(?:\s-X\s*(?:POST|PUT|PATCH|DELETE)\b|--request\s+(?:POST|PUT|PATCH|DELETE)\b|(?:\s|^)(?:-d|--data|--data-raw|--data-binary)\s)|"
    r"\bwget\b[^\n]*(?:--post-data|--post-file)\b|"
    r"\bhttp(?:ie)?\s+(?:POST|PUT|PATCH|DELETE)\b"
    r")"
)

# Only unambiguous local destruction is blocked. Project-local rm/mv/edit and
# ordinary Git operations stay reversible workflow, not pre-tool policy.
DESTRUCTIVE_OPERATION_RE = re.compile(
    r"(?is)(?:"
    r"\bgit\s+clean\b[^\n;&|]*(?:-[A-Za-z]*f[A-Za-z]*d[A-Za-z]*x|-[A-Za-z]*x[A-Za-z]*d[A-Za-z]*f|--force[^\n;&|]*--ignored)|"
    r"\bgit\s+reset\b[^\n;&|]*--hard\b|"
    r"\b(?:mkfs(?:\.[A-Za-z0-9_-]+)?|wipefs|blkdiscard|shred)\b|"
    r"\bdd\b[^\n;&|]*\bof=/dev/|"
    r"\brm\b[^\n;&|]*(?:-[A-Za-z]*r[A-Za-z]*f|-[A-Za-z]*f[A-Za-z]*r)[^\n;&|]*(?:\s|^)(?:/|~|\$HOME)(?:/[*]?)?(?:\s|$)"
    r")"
)


def _audit_denial(code: str) -> None:
    """Optionally record one content-free denial fact for disposable E2E evidence."""

    raw_path = os.environ.get("AETHER_HOOK_DENIAL_AUDIT_PATH", "").strip()
    if not raw_path:
        return
    try:
        path = Path(raw_path).expanduser()
        line = json.dumps(
            {"role": ROLE, "code": code},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
    except (OSError, UnicodeError, ValueError):
        # Audit is evidence only; it must never become another availability gate.
        return


def _block(code: str, reason: str) -> NoReturn:
    _audit_denial(code)
    payload = {
        "decision": "block",
        "reason": f"AETHER-{ROLE.upper()}-{code}: {reason}",
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(BLOCK_EXIT)


def _allow() -> NoReturn:
    print("{}")
    raise SystemExit(0)


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, nested in value.items():
            yield str(key)
            yield from _strings(nested)
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _strings(nested)


def _is_placeholder(value: str) -> bool:
    return value.strip().casefold() in PLACEHOLDERS


def _contains_secret(value: Any, *, broad: bool) -> bool:
    for text in _strings(value):
        sanitized = text
        for placeholder in ("[REDACTED]", "<REDACTED>", "[redacted]", "<redacted>"):
            sanitized = sanitized.replace(placeholder, "")
        if any(pattern.search(sanitized) for pattern in HIGH_CONFIDENCE_SECRET_PATTERNS):
            return True
        if broad and any(pattern.search(sanitized) for pattern in BROAD_SECRET_PATTERNS):
            return True

    if broad and isinstance(value, dict):
        for key, nested in value.items():
            if SENSITIVE_KEYS.fullmatch(str(key).strip()):
                if (
                    isinstance(nested, str)
                    and not _is_placeholder(nested)
                    and len(nested.strip()) >= 8
                ):
                    return True
            if _contains_secret(nested, broad=broad):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_contains_secret(item, broad=broad) for item in value)
    return False


def _command_text(tool_name: str, args: dict[str, Any]) -> str | None:
    """Return only explicit shell command text; never infer program behavior."""

    if tool_name != "terminal":
        return None
    for key in ("command", "cmd"):
        value = args.get(key)
        if isinstance(value, str):
            return value
    return None


def main() -> None:
    if ROLE not in VALID_ROLES:
        _block("PROFILE", "policy is not installed under a recognized Aether role")

    try:
        payload = json.load(sys.stdin)
    except Exception:
        _block("PAYLOAD", "hook payload is not valid JSON")
    if not isinstance(payload, dict):
        _block("PAYLOAD", "hook payload is not an object")
    if payload.get("hook_event_name") != "pre_tool_call":
        _block("PAYLOAD", "unexpected hook event")

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        _block("PAYLOAD", "tool_name is missing")

    # Private Hermes runtime captures used tool_input while the selected public
    # docs name args. Supporting both prevents compatibility drift from becoming
    # a blanket denial; both must still be mappings when present.
    raw_args = payload.get("tool_input")
    if raw_args is None:
        raw_args = payload.get("args")
    if not isinstance(raw_args, dict):
        _block("PAYLOAD", "tool arguments are not an object")
    args: dict[str, Any] = raw_args

    if tool_name in DURABLE_TOOLS and _contains_secret(args, broad=True):
        _block("DURABLE-SECRET", "credential-shaped content may not enter durable fields")
    if tool_name not in DURABLE_TOOLS and _contains_secret(args, broad=False):
        _block("CREDENTIAL", "credential material may not be supplied through a tool call")

    command = _command_text(tool_name, args)
    if command is not None:
        if CREDENTIAL_OPERATION_RE.search(command):
            _block("CREDENTIAL", "credential acquisition or widening is not authorized")
        if REMOTE_MUTATION_RE.search(command):
            _block(
                "EXTERNAL-EFFECT",
                "remote publication, deploy, or external mutation requires an explicit gate",
            )
        if DESTRUCTIVE_OPERATION_RE.search(command):
            _block(
                "DESTRUCTIVE", "clearly destructive irreversible local operation is not authorized"
            )

    _allow()


if __name__ == "__main__":
    main()
