"""Durable, project-bound Objective Contract lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import threading
import tomllib
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Final, Iterator

from jsonschema import Draft202012Validator

from aether_agents.observation.context import ProjectRegistry, canonical_project_id
from aether_agents.observation.privacy import contains_secret_shape
from aether_agents.paths import (
    FILE_MODE,
    UnsafeObservationPath,
    _open_private_directory,
    atomic_private_write,
    ensure_private_dir,
    read_private_bytes,
)

_CONTRACT_ID_RE: Final = re.compile(r"^oc_[a-f0-9]{16}$", re.ASCII)
_SESSION_RE: Final = re.compile(r"^[^\x00-\x1f\x7f]{1,256}$")
_TRUNCATION_RE: Final = re.compile(r"(?:\.\.\.)?\[truncated\]", re.IGNORECASE)
_PROJECT_SCHEMA_PACKAGED: Final = (
    Path(__file__).resolve().parent.parent / "resources" / "schemas" / "project.schema.json"
)
_PROJECT_SCHEMA_SOURCE: Final = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-aether-v1-productization"
    / "contracts"
    / "project.schema.json"
)
_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def _git_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


@lru_cache(maxsize=1)
def _project_schema_validator() -> Draft202012Validator:
    path = _PROJECT_SCHEMA_PACKAGED if _PROJECT_SCHEMA_PACKAGED.is_file() else _PROJECT_SCHEMA_SOURCE
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("PROJECT-MARKER-INVALID", "project schema is unavailable") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@contextmanager
def _contract_lock(root: Path, contract_id: str) -> Iterator[None]:
    lock_dir = ensure_private_dir(root / ".aether" / "locks" / "objective-contracts")
    lock_name = f"{contract_id}.lock"
    key = str(lock_dir / lock_name)
    with _PROCESS_LOCKS_GUARD:
        process_lock = _PROCESS_LOCKS.setdefault(key, threading.RLock())
    with process_lock:
        directory_fd = _open_private_directory(lock_dir)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = -1
        locked = False
        try:
            descriptor = os.open(lock_name, flags, FILE_MODE, dir_fd=directory_fd)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise UnsafeObservationPath("contract lock is not a regular file")
            try:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX)
                locked = True
            except ImportError:
                pass
            yield
        finally:
            if descriptor >= 0:
                if locked:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
            os.close(directory_fd)


def _exclusive_private_write(path: Path, data: bytes) -> None:
    parent = ensure_private_dir(path.parent)
    directory_fd = _open_private_directory(parent)
    temporary = f".{path.name}.{secrets.token_hex(8)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(temporary, flags, FILE_MODE, dir_fd=directory_fd)
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("short write while persisting Objective Contract")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(
                temporary,
                path.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise ContractError(
                "AETHER-OBJECTIVE-CONTRACT-IMMUTABLE",
                "finalized version already exists",
            ) from exc
        os.fsync(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)

REQUIRED_SECTIONS: Final = (
    "owner_intent",
    "objective",
    "decisions_and_assumptions",
    "in_scope",
    "out_of_scope",
    "authority",
    "deliverables",
    "acceptance_criteria",
    "testing_standard",
    "stop_conditions",
    "canonical_references",
)
_SECTION_TITLES: Final = {
    "owner_intent": "Owner Intent",
    "objective": "Objective",
    "decisions_and_assumptions": "Decisions and Assumptions",
    "in_scope": "In Scope",
    "out_of_scope": "Out of Scope",
    "authority": "Authority",
    "deliverables": "Deliverables",
    "acceptance_criteria": "Acceptance Criteria",
    "testing_standard": "Testing Standard",
    "stop_conditions": "Stop Conditions",
    "canonical_references": "Canonical References",
}
_TITLE_TO_SECTION: Final = {title: key for key, title in _SECTION_TITLES.items()}
_FINAL_REQUIRED_METADATA: Final = (
    "artifact_type",
    "project_id",
    "contract_id",
    "version",
    "status",
    "title",
    "created_at_utc",
    "created_at_local",
    "finalized_at_utc",
    "finalized_at_local",
    "author_profile",
    "created_in_session",
    "finalized_in_session",
    "supersedes",
    "change_reason",
)


class ContractError(RuntimeError):
    """Stable Objective Contract failure safe to return through a tool boundary."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class ObjectiveContractStore:
    """Author Objective Contracts inside one explicitly verified Aether Project."""

    def __init__(
        self,
        *,
        registry: ProjectRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
        author_profile: str = "morfeo",
    ) -> None:
        self.registry = registry or ProjectRegistry()
        self.clock = clock or (lambda: datetime.now().astimezone())
        self.author_profile = author_profile

    @staticmethod
    def _session(value: str) -> str:
        if not isinstance(value, str) or _SESSION_RE.fullmatch(value) is None:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-SESSION-INVALID", "Hermes session id is missing or invalid")
        return value

    def _now(self) -> tuple[str, str]:
        current = self.clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-CLOCK-INVALID", "system clock must be timezone-aware")
        local = current.isoformat(timespec="seconds")
        utc = current.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return utc, local

    def _project(self, project_id: str) -> tuple[str, Path]:
        canonical = canonical_project_id(project_id)
        if canonical is None:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-INVALID", "project_id must be a canonical UUID")
        root = self.registry.project_path(canonical)
        if root is None or not self.registry.knows(canonical):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT", "registry and .aether/project.toml do not identify the same project")
        if root.is_symlink():
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT", "registered project root cannot be a symlink")
        resolved = root.expanduser().resolve()
        if not resolved.is_dir():
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-UNRESOLVED", "registered project root is unavailable")

        marker_path = resolved / ".aether" / "project.toml"
        directory_fd = -1
        descriptor = -1
        try:
            directory_fd = _open_private_directory(marker_path.parent)
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(marker_path.name, flags, dir_fd=directory_fd)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise UnsafeObservationPath("project marker is not a regular file")
            marker_bytes = b""
            while chunk := os.read(descriptor, 65536):
                marker_bytes += chunk
            marker = tomllib.loads(marker_bytes.decode("utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError, UnsafeObservationPath) as exc:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-MARKER-INVALID", "project marker is missing, unsafe, or malformed") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if directory_fd >= 0:
                os.close(directory_fd)
        errors = sorted(_project_schema_validator().iter_errors(marker), key=lambda error: list(error.path))
        if errors:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-MARKER-INVALID", errors[0].message)
        marker_id = canonical_project_id(marker.get("project_id"))
        if marker_id != canonical:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT", "registry and .aether/project.toml do not identify the same project")

        git_root = subprocess.run(
            ("git", "rev-parse", "--show-toplevel"),
            cwd=resolved,
            check=False,
            capture_output=True,
            text=True,
            env=_git_environment(),
        )
        if git_root.returncode != 0 or Path(git_root.stdout.strip()).resolve() != resolved:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-GIT-ROOT", "registered project root is not exactly one Git repository root")
        return canonical, resolved

    @staticmethod
    def _contract_id(value: str) -> str:
        if not isinstance(value, str) or _CONTRACT_ID_RE.fullmatch(value) is None:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-ID-INVALID", "contract_id is invalid")
        return value

    @staticmethod
    def _draft_path(root: Path, contract_id: str) -> Path:
        return root / ".aether" / "drafts" / f"{contract_id}.json"

    @staticmethod
    def _final_path(root: Path, contract_id: str, version: int) -> Path:
        return root / ".aether" / "objective-contracts" / contract_id / f"v{version}.md"

    @staticmethod
    def _relative(root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        atomic_private_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    def begin(self, *, project_id: str, title: str, session_id: str) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        session_id = self._session(session_id)
        title = title.strip() if isinstance(title, str) else ""
        if (
            not title
            or len(title) > 200
            or _TRUNCATION_RE.search(title)
            or contains_secret_shape(title)
        ):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-TITLE-INVALID", "title is empty, too long, truncated, or secret-shaped")
        with _contract_lock(root, "begin"):
            utc, local = self._now()
            for _attempt in range(8):
                contract_id = "oc_" + secrets.token_hex(8)
                path = self._draft_path(root, contract_id)
                if not path.exists():
                    break
            else:
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-ID-COLLISION", "could not allocate a unique contract id")
            draft = {
                "schema_version": 1,
                "artifact_type": "aether.objective-contract.draft.v1",
                "project_id": project_id,
                "contract_id": contract_id,
                "target_version": 1,
                "status": "draft",
                "title": title,
                "revision": 1,
                "created_at_utc": utc,
                "created_at_local": local,
                "author_profile": self.author_profile,
                "created_in_session": session_id,
                "last_edited_in_session": session_id,
                "supersedes": None,
                "change_reason": None,
                "sections": {},
            }
            self._write_json(path, draft)
            return {
                "project_id": project_id,
                "contract_id": contract_id,
                "revision": 1,
                "status": "draft",
                "draft_path": self._relative(root, path),
                "created_in_session": session_id,
            }

    def _load_draft(self, root: Path, project_id: str, contract_id: str) -> tuple[Path, dict[str, Any]]:
        contract_id = self._contract_id(contract_id)
        path = self._draft_path(root, contract_id)
        try:
            value = json.loads(read_private_bytes(path).decode("utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-DRAFT-MISSING", "draft is missing or unreadable") from exc
        if (
            not isinstance(value, dict)
            or value.get("project_id") != project_id
            or value.get("contract_id") != contract_id
            or value.get("status") != "draft"
        ):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT", "draft identity does not match the explicit project")
        return path, value

    @staticmethod
    def _expect_revision(draft: dict[str, Any], expected_revision: int) -> None:
        if not isinstance(expected_revision, int) or draft.get("revision") != expected_revision:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-REVISION-CONFLICT", "expected_revision does not match persisted draft")

    def set_section(
        self,
        *,
        project_id: str,
        contract_id: str,
        expected_revision: int,
        section: str,
        content: str,
        session_id: str,
    ) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        session_id = self._session(session_id)
        contract_id = self._contract_id(contract_id)
        with _contract_lock(root, contract_id):
            path, draft = self._load_draft(root, project_id, contract_id)
            self._expect_revision(draft, expected_revision)
            if section not in _SECTION_TITLES:
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-SECTION-INVALID", "section is not part of the Objective Contract schema")
            content = content.strip() if isinstance(content, str) else ""
            if not content:
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-SECTION-EMPTY", "section content is empty")
            if _TRUNCATION_RE.search(content):
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-TRUNCATED", "section contains a truncation sentinel")
            if contains_secret_shape(content):
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-SECRET", "section contains secret-shaped content")
            sections = dict(draft.get("sections") or {})
            sections[section] = content
            draft["sections"] = sections
            draft["revision"] = expected_revision + 1
            draft["last_edited_in_session"] = session_id
            self._write_json(path, draft)
            return {
                "project_id": project_id,
                "contract_id": contract_id,
                "revision": draft["revision"],
                "status": "draft",
                "draft_path": self._relative(root, path),
                "section": section,
                "section_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "persisted_chars": len(content),
            }

    def show(self, *, project_id: str, contract_id: str) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        path, draft = self._load_draft(root, project_id, contract_id)
        return {**draft, "draft_path": self._relative(root, path)}

    def list(self, *, project_id: str) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        drafts: list[dict[str, Any]] = []
        drafts_root = root / ".aether" / "drafts"
        if drafts_root.is_dir() and not drafts_root.is_symlink():
            for path in sorted(drafts_root.glob("oc_*.json")):
                try:
                    value = json.loads(read_private_bytes(path).decode("utf-8"))
                except (OSError, UnicodeError, ValueError):
                    continue
                if value.get("project_id") == project_id and value.get("status") == "draft":
                    drafts.append({key: value.get(key) for key in ("contract_id", "title", "revision", "target_version", "status")})
        finalized: list[dict[str, Any]] = []
        final_root = root / ".aether" / "objective-contracts"
        if final_root.is_dir() and not final_root.is_symlink():
            for path in sorted(final_root.glob("oc_*/v*.md")):
                try:
                    metadata, _sections = self._parse_final(path)
                except ContractError:
                    continue
                if metadata.get("project_id") == project_id:
                    finalized.append({key: metadata.get(key) for key in ("contract_id", "title", "version", "status")})
        return {"project_id": project_id, "drafts": drafts, "finalized": finalized}

    @staticmethod
    def _draft_validation(draft: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
        raw_sections = draft.get("sections")
        sections: dict[str, str] = (
            {str(key): value for key, value in raw_sections.items() if isinstance(value, str)}
            if isinstance(raw_sections, dict)
            else {}
        )
        missing = [
            key
            for key in REQUIRED_SECTIONS
            if not isinstance(sections.get(key), str) or not sections[key].strip()
        ]
        if any(_TRUNCATION_RE.search(value) for value in sections.values() if isinstance(value, str)):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-TRUNCATED", "contract contains a truncation sentinel")
        if any(
            contains_secret_shape(value)
            for value in sections.values()
            if isinstance(value, str)
        ):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-SECRET", "contract contains secret-shaped content")
        return sections, missing

    def validate(self, *, project_id: str, contract_id: str) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        contract_id = self._contract_id(contract_id)
        with _contract_lock(root, contract_id):
            path, draft = self._load_draft(root, project_id, contract_id)
            _sections, missing = self._draft_validation(draft)
            return {
                "project_id": project_id,
                "contract_id": contract_id,
                "revision": draft["revision"],
                "valid": not missing,
                "missing_sections": missing,
                "draft_path": self._relative(root, path),
            }

    @staticmethod
    def _render_final(draft: dict[str, Any], *, finalized_utc: str, finalized_local: str, session_id: str) -> bytes:
        metadata = {
            "artifact_type": "aether.objective-contract.v1",
            "project_id": draft["project_id"],
            "contract_id": draft["contract_id"],
            "version": draft["target_version"],
            "status": "final",
            "title": draft["title"],
            "created_at_utc": draft["created_at_utc"],
            "created_at_local": draft["created_at_local"],
            "finalized_at_utc": finalized_utc,
            "finalized_at_local": finalized_local,
            "author_profile": draft["author_profile"],
            "created_in_session": draft["created_in_session"],
            "finalized_in_session": session_id,
            "supersedes": draft.get("supersedes"),
            "change_reason": draft.get("change_reason"),
        }
        lines = ["---"]
        lines.extend(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items())
        lines.extend(("---", "", f"# Objective Contract: {draft['title']}", ""))
        sections = draft["sections"]
        for key in REQUIRED_SECTIONS:
            lines.extend((f"## {_SECTION_TITLES[key]}", "", sections[key], ""))
        return ("\n".join(lines).rstrip() + "\n").encode("utf-8")

    @staticmethod
    def _parse_final(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
        try:
            text = read_private_bytes(path).decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-MISSING", "final contract is unreadable") from exc
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract metadata is malformed")
        front, body = text[4:].split("\n---\n", 1)
        metadata: dict[str, Any] = {}
        try:
            for line in front.splitlines():
                key, raw = line.split(": ", 1)
                metadata[key] = json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract metadata is malformed") from exc
        sections: dict[str, str] = {}
        matches = list(re.finditer(r"^## (.+)$", body, flags=re.MULTILINE))
        for index, match in enumerate(matches):
            key = _TITLE_TO_SECTION.get(match.group(1))
            if key is None:
                continue
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            sections[key] = body[start:end].strip()
        return metadata, sections

    @staticmethod
    def _validate_final(metadata: dict[str, Any], sections: dict[str, str]) -> None:
        if any(key not in metadata for key in _FINAL_REQUIRED_METADATA):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract metadata is incomplete")
        if any(not sections.get(key, "").strip() for key in REQUIRED_SECTIONS):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract sections are incomplete")
        if metadata["artifact_type"] != "aether.objective-contract.v1" or metadata["status"] != "final":
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract type or status is invalid")
        text_fields = ("title", "created_at_utc", "created_at_local", "finalized_at_utc", "finalized_at_local", "created_in_session", "finalized_in_session")
        if metadata["author_profile"] != "morfeo" or any(not isinstance(metadata[key], str) or not metadata[key].strip() for key in text_fields):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract provenance is invalid")
        if any(
            _TRUNCATION_RE.search(value) or contains_secret_shape(value)
            for value in sections.values()
        ):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "final contract content is unsafe")

    def finalize(
        self,
        *,
        project_id: str,
        contract_id: str,
        expected_revision: int,
        session_id: str,
    ) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        session_id = self._session(session_id)
        contract_id = self._contract_id(contract_id)
        with _contract_lock(root, contract_id):
            draft_path, draft = self._load_draft(root, project_id, contract_id)
            self._expect_revision(draft, expected_revision)
            _sections, missing = self._draft_validation(draft)
            if missing:
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-INCOMPLETE", "missing required sections: " + ", ".join(missing))
            version = draft.get("target_version")
            if not isinstance(version, int) or version < 1:
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-VERSION-INVALID", "target version is invalid")
            final_path = self._final_path(root, contract_id, version)
            utc, local = self._now()
            data = self._render_final(draft, finalized_utc=utc, finalized_local=local, session_id=session_id)
            _exclusive_private_write(final_path, data)
            persisted = read_private_bytes(final_path)
            if persisted != data:
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-WRITE-MISMATCH", "final bytes differ after persistence")
            digest = hashlib.sha256(persisted).hexdigest()
            draft_path.unlink()
            return {
                "project_id": project_id,
                "contract_id": contract_id,
                "version": version,
                "status": "final",
                "relative_path": self._relative(root, final_path),
                "sha256": digest,
                "created_in_session": draft["created_in_session"],
                "finalized_in_session": session_id,
            }

    def supersede(
        self,
        *,
        project_id: str,
        contract_id: str,
        version: int,
        change_reason: str,
        session_id: str,
    ) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        contract_id = self._contract_id(contract_id)
        session_id = self._session(session_id)
        if not isinstance(version, int) or version < 1:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-VERSION-INVALID", "source version is invalid")
        reason = change_reason.strip() if isinstance(change_reason, str) else ""
        if not reason or _TRUNCATION_RE.search(reason):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-CHANGE-INVALID", "change reason is empty or truncated")
        if contains_secret_shape(reason):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-SECRET", "change reason contains secret-shaped content")
        with _contract_lock(root, contract_id):
            source = self._final_path(root, contract_id, version)
            metadata, sections = self._parse_final(source)
            if (
                metadata.get("project_id") != project_id
                or metadata.get("contract_id") != contract_id
                or metadata.get("version") != version
                or metadata.get("status") != "final"
            ):
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT", "source contract identity does not match")
            if any(key not in sections for key in REQUIRED_SECTIONS):
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID", "source contract is missing required sections")
            draft_path = self._draft_path(root, contract_id)
            if draft_path.exists() or self._final_path(root, contract_id, version + 1).exists():
                raise ContractError("AETHER-OBJECTIVE-CONTRACT-AMENDMENT-EXISTS", "a draft or target version already exists")
            utc, local = self._now()
            draft = {
                "schema_version": 1,
                "artifact_type": "aether.objective-contract.draft.v1",
                "project_id": project_id,
                "contract_id": contract_id,
                "target_version": version + 1,
                "status": "draft",
                "title": metadata["title"],
                "revision": 1,
                "created_at_utc": utc,
                "created_at_local": local,
                "author_profile": self.author_profile,
                "created_in_session": session_id,
                "last_edited_in_session": session_id,
                "supersedes": f"{contract_id}@v{version}",
                "change_reason": reason,
                "sections": sections,
            }
            self._write_json(draft_path, draft)
            return {
                "project_id": project_id,
                "contract_id": contract_id,
                "revision": 1,
                "target_version": version + 1,
                "status": "draft",
                "draft_path": self._relative(root, draft_path),
                "supersedes": draft["supersedes"],
            }

    @staticmethod
    def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ("git", *args),
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=_git_environment(),
        )

    def prepare_handoff(
        self,
        *,
        project_id: str,
        contract_id: str,
        version: int,
    ) -> dict[str, Any]:
        project_id, root = self._project(project_id)
        contract_id = self._contract_id(contract_id)
        if not isinstance(version, int) or version < 1:
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-VERSION-INVALID", "version is invalid")
        final_path = self._final_path(root, contract_id, version)
        metadata, sections = self._parse_final(final_path)
        self._validate_final(metadata, sections)
        if (
            metadata.get("project_id") != project_id
            or metadata.get("contract_id") != contract_id
            or metadata.get("version") != version
            or metadata.get("status") != "final"
        ):
            raise ContractError("AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT", "final contract identity does not match")
        head = self._git(root, "rev-parse", "--verify", "HEAD^{commit}")
        if head.returncode != 0:
            return {"handoff_ready": False, "reason": "NOT_IN_BASE"}
        base_commit = head.stdout.decode("ascii").strip()
        if re.fullmatch(r"[0-9a-f]{40,64}", base_commit) is None:
            return {"handoff_ready": False, "reason": "NOT_IN_BASE"}
        relative = self._relative(root, final_path)
        committed = self._git(root, "show", f"{base_commit}:{relative}")
        marker = self._git(root, "show", f"{base_commit}:.aether/project.toml")
        if (
            committed.returncode != 0
            or marker.returncode != 0
            or committed.stdout != read_private_bytes(final_path)
            or marker.stdout != read_private_bytes(root / ".aether" / "project.toml")
        ):
            return {"handoff_ready": False, "reason": "NOT_IN_BASE"}
        try:
            committed_marker = tomllib.loads(marker.stdout.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError):
            return {"handoff_ready": False, "reason": "NOT_IN_BASE"}
        if (
            list(_project_schema_validator().iter_errors(committed_marker))
            or canonical_project_id(committed_marker.get("project_id")) != project_id
        ):
            return {"handoff_ready": False, "reason": "NOT_IN_BASE"}
        current_head = self._git(root, "rev-parse", "--verify", "HEAD^{commit}")
        if current_head.returncode != 0 or current_head.stdout.decode("ascii").strip() != base_commit:
            return {"handoff_ready": False, "reason": "NOT_IN_BASE"}
        digest = hashlib.sha256(committed.stdout).hexdigest()
        envelope = "\n".join(
            (
                f"Execute Objective Contract {contract_id}@v{version}.",
                f"Portable project: {project_id}",
                f"Artifact: {relative}",
                f"SHA-256: {digest}",
                f"Base commit: {base_commit}",
                "Verify project binding, artifact digest and base commit before decomposition; block before creating children on any mismatch.",
            )
        )
        return {
            "handoff_ready": True,
            "project_id": project_id,
            "contract_id": contract_id,
            "version": version,
            "relative_path": relative,
            "sha256": digest,
            "base_commit": base_commit,
            "envelope": envelope,
        }
