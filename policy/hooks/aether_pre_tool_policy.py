#!/usr/bin/env python3
"""Fail-closed Aether pre-tool policy for one Hermes profile.

The role is derived from the profile directory containing this script. The hook
never widens or rewrites a call: it returns either an explicit block directive or
an empty object. It uses only the Python standard library so hook availability
does not depend on the agent environment.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sqlite3
import subprocess
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
FILE_MUTATION_TOOLS = {"write_file", "patch"}
MORFEO_FORBIDDEN_EXECUTION_TOOLS = {
    "computer_use",
    "browser_exec",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_dialog",
}
IMPLEMENTER_INTERACTIVE_EXTERNAL_TOOLS = {
    "computer_use",
    "browser_exec",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_dialog",
    "cronjob",
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

CREDENTIAL_FILE_NAMES = {
    ".env",
    "auth.json",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "application_default_credentials.json",
    "id_rsa",
    "id_ed25519",
}
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

IMPLEMENTER_HISTORY_RE = re.compile(
    r"(?is)(?:"
    r"\bgit\s+(?:[^\n;&|]*\s)?(?:rebase|filter-branch|replace)\b|"
    r"\bgit\s+filter-repo\b|"
    r"\bgit\s+(?:[^\n;&|]*\s)?commit\b[^\n;&|]*--amend\b|"
    r"\bgit\s+(?:[^\n;&|]*\s)?reset\b|"
    r"\bgit\s+(?:[^\n;&|]*\s)?push\b|"
    r"\bgit\s+(?:[^\n;&|]*\s)?(?:checkout|switch|branch|worktree|merge|cherry-pick|revert|tag)\b|"
    r"\bgit\s+(?:[^\n;&|]*\s)?pull\b"
    r")"
)
IMPLEMENTER_READ_ONLY_BRANCH_ATOM_RE = re.compile(
    r"[ \t]*git[ \t]+branch[ \t]+--show-current[ \t]*"
)
IMPLEMENTER_EXTERNAL_EFFECT_RE = re.compile(
    r"(?is)(?:"
    r"\bgh\s+(?:pr\s+(?:create|merge|close)|release\s+(?:create|delete)|api\b(?![^\n]*\s--method\s+GET))|"
    r"\bglab\s+(?:mr\s+(?:create|merge|close)|release\s+create)|"
    r"\b(?:npm|pnpm|yarn|cargo|gem)\s+publish\b|"
    r"\b(?:twine\s+upload|dotnet\s+nuget\s+push|docker\s+push)\b|"
    r"\b(?:kubectl\s+(?:apply|create|delete|patch|replace|scale|rollout)|helm\s+(?:install|upgrade|uninstall))\b|"
    r"\b(?:terraform|tofu)\s+(?:apply|destroy|import)\b|"
    r"\bpulumi\s+(?:up|destroy)\b|"
    r"\b(?:fly\s+deploy|vercel\s+(?:deploy|--prod)|netlify\s+deploy|railway\s+up)\b|"
    r"\b(?:gcloud\s+(?:app|functions|run)\s+deploy|aws\s+cloudformation\s+(?:deploy|delete-stack)|az\s+deployment\s+)\b|"
    r"\b(?:alembic\s+upgrade|prisma\s+migrate\s+deploy|sequelize\s+db:migrate|rails\s+db:migrate|"
    r"manage\.py\s+migrate|dotnet\s+ef\s+database\s+update)\b|"
    r"\bcurl\b[^\n]*(?:\s-X\s*(?:POST|PUT|PATCH|DELETE)\b|--request\s+(?:POST|PUT|PATCH|DELETE)\b|"
    r"(?:\s|^)(?:-d|--data|--data-raw|--data-binary)\s)|"
    r"\bwget\b[^\n]*(?:--post-data|--post-file)\b|"
    r"\bhttp(?:ie)?\s+(?:POST|PUT|PATCH|DELETE)\b"
    r")"
)

CONTRACT_BASENAMES = {
    "constitution.md",
    "spec.md",
    "plan.md",
    "data-model.md",
    "quickstart.md",
    "tasks.md",
}
MORFEO_OWNED_BASENAMES = CONTRACT_BASENAMES - {"tasks.md"}
SHELL_MUTATION_RE = re.compile(
    r"(?is)(?:>|>>|\b(?:rm|mv|cp|touch|install|truncate|tee)\b|\bsed\b[^\n]*\s-i\b|"
    r"\bperl\b[^\n]*\s-pi\b|\b(?:write_text|write_bytes|write_file)\s*\(|"
    r"\bopen\s*\([^\n]*,[^\n]*[\"'][wax+]|\bgit\s+(?:apply|checkout|restore|merge|cherry-pick)\b)"
)
GIT_LITERAL_PRETTY_RE = re.compile(
    r"(?is)(\bgit\s+[^;&|\n]*?\b(?:log|show)\b[^;&|\n]*?--(?:format|pretty)=)'([^']*)'"
)


class Undecidable(RuntimeError):
    """Raised when a protected effect cannot be classified safely."""


def _block(code: str, reason: str) -> NoReturn:
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


def _contains_secret(value: Any, *, broad: bool = True) -> bool:
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
                if isinstance(nested, str) and not _is_placeholder(nested) and len(nested.strip()) >= 8:
                    return True
            if _contains_secret(nested, broad=broad):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_contains_secret(item, broad=broad) for item in value)
    return False


def _safe_audit_shape(payload: dict[str, Any]) -> None:
    destination = os.environ.get("AETHER_HOOK_AUDIT_PATH", "").strip()
    if not destination:
        return
    record = {
        "role": ROLE,
        "event": payload.get("hook_event_name"),
        "top_level_keys": sorted(str(k) for k in payload),
        "tool_name": payload.get("tool_name"),
        "tool_input_type": type(payload.get("tool_input")).__name__,
        "tool_input_keys": sorted(str(k) for k in (payload.get("tool_input") or {})),
        "extra_keys": sorted(str(k) for k in (payload.get("extra") or {})),
        "cwd_present": isinstance(payload.get("cwd"), str) and bool(payload.get("cwd")),
    }
    path = Path(destination)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, (json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def _path(raw: Any, cwd: Path) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise Undecidable("missing path")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return candidate.resolve(strict=False)


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _patch_raw_targets(args: dict[str, Any]) -> list[str]:
    mode = str(args.get("mode") or "replace").casefold()
    if mode == "replace":
        raw = args.get("path")
        if not isinstance(raw, str) or not raw.strip():
            raise Undecidable("missing path")
        return [raw]
    if mode != "patch":
        raise Undecidable(f"unknown patch mode {mode!r}")
    patch_text = args.get("patch")
    if not isinstance(patch_text, str) or not patch_text.strip():
        raise Undecidable("patch payload is empty")

    lines = patch_text.splitlines()
    begin = re.compile(r"^\*\*\*\s*Begin\s+Patch\s*$")
    end = re.compile(r"^\*\*\*\s*End\s+Patch\s*$")
    start_index = -1
    end_index = len(lines)
    for index, line in enumerate(lines):
        if begin.match(line):
            start_index = index
        elif end.match(line):
            end_index = index
            break

    raw_targets: list[str] = []
    operation_prefix = re.compile(r"^\*\*\*\s*(?:Add|Update|Delete|Move)\b")
    for line in lines[start_index + 1 : end_index]:
        match = re.match(r"^\*\*\*\s*(?:Add|Update|Delete)\s+File:\s*(.+)", line)
        if match:
            raw_targets.append(match.group(1).strip())
            continue
        move = re.match(r"^\*\*\*\s*Move\s+File:\s*(.+?)\s*->\s*(.+)", line)
        if move:
            raw_targets.extend((move.group(1).strip(), move.group(2).strip()))
            continue
        if operation_prefix.match(line):
            raise Undecidable("patch payload contains an unrecognized patch operation header")
    if not raw_targets or any(not raw for raw in raw_targets):
        raise Undecidable("patch payload has no recognized file targets")
    return raw_targets


def _patch_targets(args: dict[str, Any], cwd: Path) -> list[Path]:
    return [_path(raw, cwd) for raw in _patch_raw_targets(args)]


def _raw_mutation_targets(tool_name: str, args: dict[str, Any]) -> list[str]:
    if tool_name == "write_file":
        raw = args.get("path")
        if not isinstance(raw, str) or not raw.strip():
            raise Undecidable("missing path")
        return [raw]
    if tool_name == "patch":
        return _patch_raw_targets(args)
    return []


def _mutation_targets(tool_name: str, args: dict[str, Any], cwd: Path) -> list[Path]:
    if tool_name == "write_file":
        return [_path(args.get("path"), cwd)]
    if tool_name == "patch":
        return _patch_targets(args, cwd)
    return []


def _require_absolute_mutation_targets(tool_name: str, args: dict[str, Any]) -> None:
    raw_targets = _raw_mutation_targets(tool_name, args)
    if not raw_targets:
        raise Undecidable("file mutation has no target")
    for raw in raw_targets:
        if not Path(raw).expanduser().is_absolute():
            raise Undecidable("Morfeo task-bound structured writes require absolute paths")


def _credential_target(path: Path) -> bool:
    name = path.name.casefold()
    if name.endswith((".example", ".sample", ".template")):
        return False
    if name in CREDENTIAL_FILE_NAMES:
        return True
    if name.endswith((".pem", ".key", ".p12", ".pfx", ".kdbx")):
        return True
    normalized = path.as_posix().casefold()
    return any(
        marker in normalized
        for marker in (
            "/.aws/credentials",
            "/.ssh/id_",
            "/.config/gcloud/application_default_credentials.json",
            "/.docker/config.json",
        )
    )


def _run_git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=3,
        check=False,
    )
    if completed.returncode != 0:
        raise Undecidable(f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _resolve_git_path(raw: str, cwd: Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = cwd / path
    return path.resolve(strict=False)


def _git_context(cwd: Path) -> dict[str, Any]:
    top = Path(_run_git(cwd, "rev-parse", "--show-toplevel")).resolve()
    git_dir = _resolve_git_path(_run_git(cwd, "rev-parse", "--git-dir"), cwd)
    common_dir = _resolve_git_path(_run_git(cwd, "rev-parse", "--git-common-dir"), cwd)
    branch = _run_git(cwd, "branch", "--show-current")
    if not branch:
        raise Undecidable("detached HEAD")
    integration = os.environ.get("AETHER_INTEGRATION_BRANCH", "").strip()
    if not integration:
        probe = subprocess.run(
            ["git", "-C", str(cwd), "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            integration = probe.stdout.strip().split("/", 1)[-1]
    if not integration:
        branches = {
            item.strip()
            for item in _run_git(
                cwd,
                "for-each-ref",
                "--format=%(refname:short)",
                "refs/heads",
            ).splitlines()
            if item.strip()
        }
        if "main" in branches:
            integration = "main"
        elif "master" in branches:
            integration = "master"
        elif len(branches) == 1:
            integration = next(iter(branches))
    return {
        "top": top,
        "git_dir": git_dir,
        "common_dir": common_dir,
        "branch": branch,
        "integration": integration,
        "main_worktree": git_dir == common_dir,
    }


def _relative_to_repo(path: Path, context: dict[str, Any]) -> str:
    try:
        return path.resolve(strict=False).relative_to(context["top"]).as_posix()
    except ValueError as exc:
        raise Undecidable("path is outside the current project") from exc


def _is_contract_rel(relative: str) -> bool:
    parts = tuple(part for part in Path(relative).parts if part not in (".", ""))
    if parts == (".specify", "memory", "constitution.md"):
        return True
    if len(parts) >= 3 and parts[0] == "specs":
        if parts[-1] in CONTRACT_BASENAMES:
            return True
        if "contracts" in parts[2:]:
            return True
    return False


def _is_morfeo_owned_rel(relative: str) -> bool:
    parts = tuple(part for part in Path(relative).parts if part not in (".", ""))
    if parts == (".specify", "memory", "constitution.md"):
        return True
    if len(parts) >= 3 and parts[0] == "specs":
        if parts[-1] in MORFEO_OWNED_BASENAMES:
            return True
        if "contracts" in parts[2:]:
            return True
    return False


def _is_tasks_rel(relative: str) -> bool:
    parts = tuple(Path(relative).parts)
    return len(parts) >= 3 and parts[0] == "specs" and parts[-1] == "tasks.md"


def _require_integration(context: dict[str, Any]) -> None:
    if not context["main_worktree"]:
        raise Undecidable("not the project's main worktree")
    if not context["integration"] or context["branch"] != context["integration"]:
        raise Undecidable("current branch is not the integration branch")


def _contract_reference(text: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:^|[/\\])(?:constitution|spec|plan|data-model|quickstart|tasks)\.md\b|"
            r"(?:^|[/\\])contracts[/\\]",
            text,
        )
    )


def _extract_command(args: dict[str, Any]) -> str:
    for key in ("command", "code", "script"):
        value = args.get(key)
        if isinstance(value, str):
            return value
    return json.dumps(args, ensure_ascii=False, sort_keys=True)


def _literal_single_quote_spans(command: str) -> set[tuple[int, int]]:
    spans: set[tuple[int, int]] = set()
    quote: str | None = None
    content_start = 0
    index = 0
    while index < len(command):
        character = command[index]
        if quote == "'":
            if character == "'":
                spans.add((content_start, index))
                quote = None
            index += 1
            continue
        if quote == '"':
            if character == "\\":
                index += 2
            elif character == '"':
                quote = None
                index += 1
            else:
                index += 1
            continue
        if character == "\\":
            index += 2
            continue
        if character == "'":
            quote = character
            content_start = index + 1
        elif character == '"':
            quote = character
        index += 1
    return spans


def _shell_mutation(command: str) -> bool:
    if "<<" in command:
        return bool(SHELL_MUTATION_RE.search(command))
    literal_spans = _literal_single_quote_spans(command)

    def mask_literal_pretty(match: re.Match[str]) -> str:
        if match.span(2) not in literal_spans:
            return match.group(0)
        return f"{match.group(1)}'{' ' * len(match.group(2))}'"

    inspected = GIT_LITERAL_PRETTY_RE.sub(mask_literal_pretty, command)
    return bool(SHELL_MUTATION_RE.search(inspected))


def _implementer_chain_segments(command: str) -> list[tuple[int, int]] | None:
    """Return safe top-level chain spans, or None for shell context syntax."""
    if any(character in command for character in "\r\n"):
        return None
    segments: list[tuple[int, int]] = []
    segment_start = 0
    quote: str | None = None
    index = 0
    while index < len(command):
        character = command[index]
        if quote == "'":
            if character == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if character == "\\":
                index += 2
            elif character == '"':
                quote = None
                index += 1
            else:
                index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            index += 1
            continue
        if character in {"\\", "#", "$", "`", "(", ")", "{", "}", "<", ">"}:
            return None
        if character in {"|", "&"}:
            separator = character * 2
            if command[index : index + 2] != separator:
                return None
            if not command[segment_start:index].strip():
                return None
            segments.append((segment_start, index))
            index += 2
            segment_start = index
            continue
        if character == ";":
            if not command[segment_start:index].strip():
                return None
            segments.append((segment_start, index))
            index += 1
            segment_start = index
            continue
        index += 1
    if quote is not None or not command[segment_start:].strip():
        return None
    segments.append((segment_start, len(command)))
    return segments


def _remove_read_only_branch_atoms(command: str) -> str:
    segments = _implementer_chain_segments(command)
    if segments is None:
        return command
    output: list[str] = []
    cursor = 0
    for start, end in segments:
        output.append(command[cursor:start])
        if not IMPLEMENTER_READ_ONLY_BRANCH_ATOM_RE.fullmatch(command[start:end]):
            output.append(command[start:end])
        cursor = end
    output.append(command[cursor:])
    return "".join(output)


def _credential_operation(tool_name: str, args: dict[str, Any], cwd: Path) -> bool:
    if tool_name in FILE_MUTATION_TOOLS:
        for target in _mutation_targets(tool_name, args, cwd):
            if _credential_target(target):
                return True
    text = _extract_command(args)
    if CREDENTIAL_OPERATION_RE.search(text):
        return True
    if tool_name.startswith("browser_"):
        url = str(args.get("url") or args.get("text") or "")
        if re.search(r"(?i)(?:/|\b)(?:oauth|authorize|login|signin|device-code)(?:/|\b)", url):
            return True
    return False


def _scan_attachment(tool_name: str, args: dict[str, Any], cwd: Path) -> bool:
    if tool_name != "kanban_attach":
        return False
    raw = args.get("path") or args.get("file_path")
    if not raw:
        return False
    target = _path(raw, cwd)
    if _credential_target(target):
        return True
    try:
        if target.is_file() and target.stat().st_size <= 2_000_000:
            return _contains_secret(target.read_text(encoding="utf-8", errors="ignore"), broad=True)
    except OSError:
        raise Undecidable("attachment could not be inspected")
    return False


def _decision_shape(title: Any, body: Any) -> bool:
    # R7 defines the card by its bounded decision content, not by a literal
    # title convention. The assignee check is enforced separately.
    _ = title
    body_text = str(body or "").casefold()
    has_question = "question" in body_text or "?" in body_text
    has_options = any(word in body_text for word in ("option", "candidate", "alternative"))
    has_consequences = any(word in body_text for word in ("consequence", "implication", "trade-off", "tradeoff"))
    return has_question and has_options and has_consequences


def _board_path(args: dict[str, Any]) -> Path:
    explicit = args.get("board")
    env_path = os.environ.get("HERMES_KANBAN_DB", "").strip()
    if explicit and Path(str(explicit)).suffix == ".db":
        return Path(str(explicit)).expanduser().resolve()
    if explicit and env_path:
        # A slug cannot be safely mapped here; require the worker's pinned board.
        raise Undecidable("board override cannot be proven to be the pinned board")
    if env_path:
        return Path(env_path).expanduser().resolve()
    raise Undecidable("worker board path is unavailable")


def _implementer_kanban(tool_name: str, args: dict[str, Any], payload: dict[str, Any]) -> None:
    if tool_name == "kanban_create":
        if str(args.get("assignee") or "").casefold() != "supervisor":
            _block("CARD-SCOPE", "Implementer may create only a decision card addressed to Supervisor")
        if not _decision_shape(args.get("title"), args.get("body")):
            _block("CARD-SHAPE", "decision card must state the question, options, and consequences")
        if args.get("parents") not in (None, [], ()):
            _block("CARD-LINK", "decision card is linked as a parent after creation, not created as a child")
        forbidden_overrides = {
            "model",
            "provider",
            "workspace_path",
            "skills",
            "triage",
            "goal_mode",
        }
        if any(args.get(key) not in (None, False, [], "") for key in forbidden_overrides):
            _block("CARD-AUTHORITY", "decision card may not widen execution settings or authority")
        return
    if tool_name != "kanban_link":
        return
    extra = payload.get("extra") or {}
    current_task = str(extra.get("task_id") or os.environ.get("HERMES_KANBAN_TASK") or "").strip()
    if not current_task or str(args.get("child_id") or "") != current_task:
        _block("CARD-LINK", "Implementer may link only its own card as the decision card's child")
    parent_id = str(args.get("parent_id") or "").strip()
    if not parent_id:
        _block("CARD-LINK", "decision parent id is missing")
    board = _board_path(args)
    try:
        conn = sqlite3.connect(f"file:{board}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT title, body, assignee, created_by FROM tasks WHERE id = ?",
                (parent_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise Undecidable("decision parent could not be inspected") from exc
    if row is None:
        _block("CARD-LINK", "decision parent does not exist")
    if str(row["assignee"] or "").casefold() != "supervisor":
        _block("CARD-LINK", "decision parent is not addressed to Supervisor")
    if str(row["created_by"] or "").casefold() != "implementer":
        _block("CARD-LINK", "decision parent was not created by Implementer")
    if not _decision_shape(row["title"], row["body"]):
        _block("CARD-LINK", "parent is not a complete decision card")


def _implementer_context(payload: dict[str, Any], args: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    workspace_raw = os.environ.get("HERMES_KANBAN_WORKSPACE", "").strip()
    branch_expected = os.environ.get("HERMES_KANBAN_BRANCH", "").strip()
    if not workspace_raw or not branch_expected:
        raise Undecidable("worker workspace or branch binding is unavailable")
    workspace = Path(workspace_raw).expanduser().resolve()
    raw_workdir = args.get("workdir") or payload.get("cwd")
    workdir = _path(raw_workdir, workspace)
    if not _under(workdir, workspace):
        raise Undecidable("tool working directory is outside the assigned workspace")
    context = _git_context(workdir)
    if workspace != context["top"]:
        raise Undecidable("worker workspace does not match the current project root")
    if context["branch"] != branch_expected:
        raise Undecidable("current branch does not match the worker branch binding")
    return workspace, context


def _morfeo_mutation_context(
    payload: dict[str, Any], args: dict[str, Any], cwd: Path
) -> tuple[Path, dict[str, Any]]:
    context = _git_context(cwd)
    if (
        context["main_worktree"]
        and context["integration"]
        and context["branch"] == context["integration"]
    ):
        return context["top"], context

    workspace_raw = os.environ.get("HERMES_KANBAN_WORKSPACE", "").strip()
    branch_expected = os.environ.get("HERMES_KANBAN_BRANCH", "").strip()
    task_id = os.environ.get("HERMES_KANBAN_TASK", "").strip()
    run_raw = os.environ.get("HERMES_KANBAN_RUN_ID", "").strip()
    if not workspace_raw or not branch_expected or not task_id or not run_raw:
        raise Undecidable("Morfeo task workspace, branch, task, or run binding is unavailable")
    try:
        run_id = int(run_raw)
    except ValueError as exc:
        raise Undecidable("worker run binding is invalid") from exc

    workspace = Path(workspace_raw).expanduser().resolve()
    raw_workdir = args.get("workdir") or payload.get("cwd")
    workdir = _path(raw_workdir, workspace)
    if not _under(workdir, workspace):
        raise Undecidable("tool working directory is outside the assigned Morfeo workspace")
    context = _git_context(workdir)
    if workspace != context["top"]:
        raise Undecidable("Morfeo workspace does not match the current project root")
    if context["main_worktree"]:
        raise Undecidable("Morfeo task workspace is not a linked worktree")
    if context["branch"] != branch_expected:
        raise Undecidable("current branch does not match the Morfeo branch binding")

    board = _board_path({})
    try:
        conn = sqlite3.connect(f"file:{board}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                """
                SELECT t.assignee, t.status, t.workspace_kind, t.workspace_path, t.branch_name,
                       t.current_run_id, r.profile AS run_profile,
                       r.status AS run_status, r.task_id AS run_task_id
                FROM tasks AS t
                LEFT JOIN task_runs AS r ON r.id = t.current_run_id
                WHERE t.id = ?
                """,
                (task_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise Undecidable("Morfeo task binding could not be inspected") from exc
    if row is None:
        raise Undecidable("Morfeo task does not exist on the pinned board")
    if str(row["assignee"] or "").casefold() != "morfeo":
        raise Undecidable("task is not assigned to Morfeo")
    if str(row["status"] or "").casefold() != "running":
        raise Undecidable("Morfeo task is not running")
    if str(row["workspace_kind"] or "").casefold() != "worktree":
        raise Undecidable("Morfeo task workspace is not an isolated worktree")
    board_workspace = str(row["workspace_path"] or "").strip()
    if not board_workspace:
        raise Undecidable("board workspace is unavailable")
    if Path(board_workspace).expanduser().resolve() != workspace:
        raise Undecidable("board workspace does not match the Morfeo workspace binding")
    if str(row["branch_name"] or "") != branch_expected:
        raise Undecidable("board branch does not match the Morfeo branch binding")
    if row["current_run_id"] != run_id:
        raise Undecidable("board run does not match the Morfeo run binding")
    if str(row["run_task_id"] or "") != task_id:
        raise Undecidable("active task run does not belong to the Morfeo task")
    if str(row["run_profile"] or "").casefold() != "morfeo":
        raise Undecidable("active task run does not belong to Morfeo")
    if str(row["run_status"] or "").casefold() != "running":
        raise Undecidable("Morfeo task run is not active")
    return workspace, context


def _integration_refs(command: str, operation: str) -> list[str]:
    if re.search(r"[;&|`$<>\n]", command):
        raise Undecidable(f"complex git {operation} command cannot be inspected safely")
    tokens = shlex.split(command)
    try:
        index = tokens.index(operation)
    except ValueError as exc:
        raise Undecidable(f"git {operation} arguments could not be parsed") from exc
    refs: list[str] = []
    for token in tokens[index + 1 :]:
        if token == "--":
            continue
        if token.startswith("-"):
            continue
        refs.append(token)
    if not refs:
        raise Undecidable(f"git {operation} has no inspectable revision")
    return refs


def _supervisor_integration_guard(command: str, cwd: Path) -> None:
    operation = None
    if re.search(r"(?is)\bgit\b[^\n;&|]*(?<![\w-])merge(?=$|[\s;&|])", command):
        operation = "merge"
    elif re.search(r"(?is)\bgit\b[^\n;&|]*\bcherry-pick\b", command):
        operation = "cherry-pick"
    if operation is None:
        return
    context = _git_context(cwd)
    _require_integration(context)
    for ref in _integration_refs(command, operation):
        if operation == "merge":
            changed = _run_git(cwd, "diff", "--name-only", f"HEAD...{ref}")
        else:
            changed = _run_git(cwd, "diff-tree", "--no-commit-id", "--name-only", "-r", ref)
        for relative in changed.splitlines():
            if _is_morfeo_owned_rel(relative.strip()):
                _block("CONTRACT-OWNER", "integration input modifies a Morfeo-owned contract artifact")


def _apply_morfeo(tool_name: str, args: dict[str, Any], payload: dict[str, Any], cwd: Path) -> None:
    if tool_name in MORFEO_FORBIDDEN_EXECUTION_TOOLS:
        _block("UNRELATED-TOOLSET", "this tool is outside Morfeo's authorized operational surface")
    if tool_name not in FILE_MUTATION_TOOLS:
        return
    _require_absolute_mutation_targets(tool_name, args)
    workspace, context = _morfeo_mutation_context(payload, args, cwd)
    targets = _mutation_targets(tool_name, args, cwd)
    if not targets:
        raise Undecidable("file mutation has no target")
    for target in targets:
        # Ownership no longer confines Morfeo to canonical Spec Kit contract
        # artifacts (bounded operational write access, authorized directly by
        # the owner). Still resolved relative to the repo so the call fails
        # closed — via _relative_to_repo's Undecidable — for any target
        # outside the current project, same as every other role.
        if not _under(target, workspace):
            raise Undecidable("Morfeo file mutation is outside the authorized workspace")
        _relative_to_repo(target, context)


def _apply_supervisor(tool_name: str, args: dict[str, Any], payload: dict[str, Any], cwd: Path) -> None:
    if tool_name in FILE_MUTATION_TOOLS:
        context = _git_context(cwd)
        for target in _mutation_targets(tool_name, args, cwd):
            relative = _relative_to_repo(target, context)
            if _is_morfeo_owned_rel(relative):
                _block("CONTRACT-OWNER", "Supervisor may not mutate a Morfeo-owned contract artifact")
            if _is_tasks_rel(relative):
                _require_integration(context)
    if tool_name in {"terminal", "execute_code"}:
        command = _extract_command(args)
        if _contract_reference(command) and _shell_mutation(command):
            # tasks.md is Supervisor-owned, but any shell mutation must still be on integration.
            context = _git_context(Path(args.get("workdir") or cwd))
            if re.search(r"(?i)(?:^|[/\\])tasks\.md\b", command):
                _require_integration(context)
            if re.search(
                r"(?i)(?:^|[/\\])(?:constitution|spec|plan|data-model|quickstart)\.md\b|"
                r"(?:^|[/\\])contracts[/\\]",
                command,
            ):
                _block("CONTRACT-OWNER", "Supervisor shell call may mutate a Morfeo-owned contract artifact")
        _supervisor_integration_guard(command, Path(args.get("workdir") or cwd))


def _apply_implementer(tool_name: str, args: dict[str, Any], payload: dict[str, Any], cwd: Path) -> None:
    if tool_name in {"kanban_create", "kanban_link"}:
        _implementer_kanban(tool_name, args, payload)
    if tool_name in FILE_MUTATION_TOOLS:
        workspace, context = _implementer_context(payload, args)
        for target in _mutation_targets(tool_name, args, cwd):
            if not _under(target, workspace):
                _block("WORKSPACE", "Implementer file mutation is outside the assigned workspace")
            relative = _relative_to_repo(target, context)
            if _is_contract_rel(relative):
                _block("CONTRACT-OWNER", "Implementer may not mutate any contract artifact")
    if tool_name in {"terminal", "execute_code"}:
        workspace, context = _implementer_context(payload, args)
        command = _extract_command(args)
        history_command = _remove_read_only_branch_atoms(command)
        if IMPLEMENTER_HISTORY_RE.search(history_command):
            _block("BRANCH-HISTORY", "Implementer may not change branches, integrate, publish, or rewrite history")
        if IMPLEMENTER_EXTERNAL_EFFECT_RE.search(command):
            _block("EXTERNAL-EFFECT", "irreversible external effects belong to Supervisor integration")
        if _contract_reference(command) and _shell_mutation(command):
            _block("CONTRACT-OWNER", "Implementer shell call may mutate a contract artifact")
        # A mutating shell call that names an absolute path outside the workspace is undecidable.
        if _shell_mutation(command):
            for raw in re.findall(r"(?<![A-Za-z0-9_.-])(/[A-Za-z0-9_./@+:-]+)", command):
                candidate = Path(raw).resolve(strict=False)
                if not _under(candidate, workspace) and not str(candidate).startswith(("/usr/", "/bin/")):
                    raise Undecidable("mutating command names a path outside the assigned workspace")
        if context["branch"] != os.environ.get("HERMES_KANBAN_BRANCH"):
            raise Undecidable("worker branch changed during policy evaluation")
    if tool_name in IMPLEMENTER_INTERACTIVE_EXTERNAL_TOOLS:
        _block("EXTERNAL-EFFECT", "interactive or scheduled external effects belong to Supervisor integration")


def main() -> None:
    if ROLE not in VALID_ROLES:
        _block("PROFILE", "policy is not installed under a recognized profile")
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _block("PAYLOAD", "hook payload is not valid JSON")
    if not isinstance(payload, dict):
        _block("PAYLOAD", "hook payload is not an object")
    try:
        _safe_audit_shape(payload)
    except Exception:
        _block("AUDIT", "payload-shape audit could not be recorded")
    if payload.get("hook_event_name") != "pre_tool_call":
        _block("PAYLOAD", "unexpected hook event")
    tool_name = payload.get("tool_name")
    args = payload.get("tool_input")
    extra = payload.get("extra")
    if not isinstance(tool_name, str) or not tool_name:
        _block("PAYLOAD", "tool_name is missing")
    if not isinstance(args, dict):
        _block("PAYLOAD", "tool_input is not an object")
    if not isinstance(extra, dict):
        _block("PAYLOAD", "extra metadata is not an object")
    try:
        cwd = _path(payload.get("cwd"), Path.cwd())
        if tool_name in DURABLE_TOOLS and (_contains_secret(args, broad=True) or _scan_attachment(tool_name, args, cwd)):
            _block("DURABLE-SECRET", "credential-shaped content may not enter durable fields")
        if tool_name not in DURABLE_TOOLS and _contains_secret(args, broad=False):
            _block("CREDENTIAL", "new credential material may not be supplied through a tool call")
        if _credential_operation(tool_name, args, cwd):
            _block("CREDENTIAL", "credential acquisition or widening is not authorized")
        if ROLE == "morfeo":
            _apply_morfeo(tool_name, args, payload, cwd)
        elif ROLE == "supervisor":
            _apply_supervisor(tool_name, args, payload, cwd)
        else:
            _apply_implementer(tool_name, args, payload, cwd)
    except Undecidable as exc:
        _block("UNDECIDABLE", str(exc))
    except SystemExit:
        raise
    except Exception:
        _block("UNDECIDABLE", "policy evaluation failed")
    _allow()


if __name__ == "__main__":
    main()
