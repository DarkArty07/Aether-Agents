"""Version-pinned read-only Orca command catalog for M2.6."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, NoReturn

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
_COMMAND_ID = re.compile(r"^[a-z][a-z0-9_.]{0,127}$")
_MAX_RESPONSE_BYTES = 1_048_576


class CatalogError(ValueError):
    """Stable provider-catalog failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise CatalogError(code, message)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass(frozen=True)
class CatalogArgument:
    name: str
    flag: str
    required: bool
    value_type: str
    minimum: int | None
    maximum: int | None


@dataclass(frozen=True)
class CatalogEntry:
    command_id: str
    description: str
    effect: str
    argv_prefix: tuple[str, ...]
    arguments: tuple[CatalogArgument, ...]


@dataclass(frozen=True)
class CatalogPlan:
    command_id: str
    effect: str
    argv: tuple[str, ...]
    catalog_digest: str


class OrcaCatalog:
    """Strict immutable catalog; mutating Orca commands are intentionally absent."""

    def __init__(self, *, product_version: str, digest: str, entries: tuple[CatalogEntry, ...]) -> None:
        self.product_version = product_version
        self.digest = digest
        self.entries = entries
        self._by_id = {entry.command_id: entry for entry in entries}

    @classmethod
    def bundled(cls, product_version: str = "1.4.167") -> "OrcaCatalog":
        if product_version != "1.4.167":
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider version is not bundled")
        resource = files("aether_mcp").joinpath("data", "orca", product_version, "catalog.json")
        with as_file(resource) as path:
            return cls.load(path)

    @classmethod
    def load(cls, path: Path) -> "OrcaCatalog":
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider catalog is unavailable or malformed")
        if not isinstance(payload, dict) or set(payload) != {
            "schema_version",
            "product_version",
            "catalog_sha256",
            "commands",
        }:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider catalog shape changed")
        digest = payload["catalog_sha256"]
        body = {key: value for key, value in payload.items() if key != "catalog_sha256"}
        observed = hashlib.sha256(_canonical(body)).hexdigest()
        if payload["schema_version"] != 1 or not isinstance(digest, str) or digest != observed:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider catalog digest changed")
        version = payload["product_version"]
        if not isinstance(version, str) or not version or len(version) > 64:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider version is invalid")
        commands = payload["commands"]
        if not isinstance(commands, list) or not commands or len(commands) > 128:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider command catalog is invalid")
        entries: list[CatalogEntry] = []
        seen: set[str] = set()
        for raw in commands:
            if not isinstance(raw, dict) or set(raw) != {
                "command_id",
                "description",
                "effect",
                "argv_prefix",
                "arguments",
            }:
                _fail("PROVIDER_SCHEMA_DRIFT", "Provider command shape changed")
            command_id = raw["command_id"]
            if not isinstance(command_id, str) or _COMMAND_ID.fullmatch(command_id) is None or command_id in seen:
                _fail("PROVIDER_SCHEMA_DRIFT", "Provider command identity is invalid")
            seen.add(command_id)
            if raw["effect"] != "READ_ONLY":
                _fail("PROVIDER_SCHEMA_DRIFT", "M2 catalog contains a mutable command")
            description = raw["description"]
            prefix = raw["argv_prefix"]
            if not isinstance(description, str) or not description or len(description.encode()) > 512:
                _fail("PROVIDER_SCHEMA_DRIFT", "Provider command description is invalid")
            if (
                not isinstance(prefix, list)
                or not prefix
                or len(prefix) > 8
                or any(not isinstance(token, str) or _SAFE_VALUE.fullmatch(token) is None for token in prefix)
            ):
                _fail("PROVIDER_SCHEMA_DRIFT", "Provider command argv prefix is invalid")
            arguments_raw = raw["arguments"]
            if not isinstance(arguments_raw, dict) or len(arguments_raw) > 16:
                _fail("PROVIDER_SCHEMA_DRIFT", "Provider command arguments are invalid")
            arguments: list[CatalogArgument] = []
            for name, specification in arguments_raw.items():
                if not isinstance(name, str) or _COMMAND_ID.fullmatch(name) is None or not isinstance(specification, dict):
                    _fail("PROVIDER_SCHEMA_DRIFT", "Provider argument identity is invalid")
                allowed = {"flag", "required", "type", "minimum", "maximum"}
                if not set(specification).issubset(allowed) or not {"flag", "required"}.issubset(specification):
                    _fail("PROVIDER_SCHEMA_DRIFT", "Provider argument schema is invalid")
                flag = specification["flag"]
                required = specification["required"]
                value_type = specification.get("type", "string")
                minimum = specification.get("minimum")
                maximum = specification.get("maximum")
                if (
                    not isinstance(flag, str)
                    or not flag.startswith("--")
                    or _SAFE_VALUE.fullmatch(flag[2:]) is None
                    or not isinstance(required, bool)
                    or value_type not in {"string", "integer"}
                    or (minimum is not None and not isinstance(minimum, int))
                    or (maximum is not None and not isinstance(maximum, int))
                ):
                    _fail("PROVIDER_SCHEMA_DRIFT", "Provider argument schema is invalid")
                arguments.append(CatalogArgument(name, flag, required, value_type, minimum, maximum))
            entries.append(CatalogEntry(command_id, description, "READ_ONLY", tuple(prefix), tuple(arguments)))
        return cls(product_version=version, digest=digest, entries=tuple(entries))

    def _entry(self, command_id: str) -> CatalogEntry:
        entry = self._by_id.get(command_id)
        if entry is None:
            _fail("CAPABILITY_UNAVAILABLE", "Provider command is not admitted")
        return entry

    def _check_digest(self, catalog_digest: str) -> None:
        if not isinstance(catalog_digest, str) or _HEX64.fullmatch(catalog_digest) is None or catalog_digest != self.digest:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider catalog digest does not match admission")

    def search(self, query: str, *, limit: int) -> tuple[CatalogEntry, ...]:
        if not isinstance(query, str) or not query.strip() or len(query.encode()) > 512:
            _fail("INVALID_INPUT", "Catalog query is invalid")
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            _fail("INVALID_INPUT", "Catalog search limit is invalid")
        terms = query.casefold().split()
        matched = [
            entry
            for entry in self.entries
            if all(term in f"{entry.command_id} {entry.description}".casefold() for term in terms)
        ]
        return tuple(matched[:limit])

    def describe(self, command_id: str, *, catalog_digest: str) -> CatalogEntry:
        self._check_digest(catalog_digest)
        return self._entry(command_id)

    def plan_read_only(
        self,
        command_id: str,
        arguments: dict[str, object],
        *,
        catalog_digest: str,
    ) -> CatalogPlan:
        self._check_digest(catalog_digest)
        entry = self._entry(command_id)
        if not isinstance(arguments, dict):
            _fail("INVALID_INPUT", "Provider arguments must be an object")
        admitted = {argument.name: argument for argument in entry.arguments}
        if not set(arguments).issubset(admitted) or any(
            argument.required and argument.name not in arguments for argument in entry.arguments
        ):
            _fail("INVALID_INPUT", "Provider arguments do not match the admitted schema")
        argv = list(entry.argv_prefix)
        for argument in entry.arguments:
            if argument.name not in arguments:
                continue
            value = arguments[argument.name]
            if argument.value_type == "integer":
                if isinstance(value, bool) or not isinstance(value, int):
                    _fail("INVALID_INPUT", "Provider integer argument is invalid")
                if argument.minimum is not None and value < argument.minimum:
                    _fail("INVALID_INPUT", "Provider integer argument is below its bound")
                if argument.maximum is not None and value > argument.maximum:
                    _fail("INVALID_INPUT", "Provider integer argument exceeds its bound")
                rendered = str(value)
            else:
                if not isinstance(value, str) or _SAFE_VALUE.fullmatch(value) is None:
                    _fail("INVALID_INPUT", "Provider string argument is invalid")
                rendered = value
            argv.extend((argument.flag, rendered))
        argv.append("--json")
        return CatalogPlan(entry.command_id, entry.effect, tuple(argv), self.digest)

    def parse_response(self, command_id: str, payload: bytes) -> dict[str, Any]:
        self._entry(command_id)
        if not isinstance(payload, bytes) or len(payload) > _MAX_RESPONSE_BYTES:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider response exceeds its bound")
        try:
            decoded = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail("PROVIDER_RESPONSE_INVALID", "Provider response is not JSON")
        if (
            not isinstance(decoded, dict)
            or not {"id", "ok", "result", "_meta"}.issubset(decoded)
            or decoded["ok"] is not True
            or not isinstance(decoded["id"], str)
            or not isinstance(decoded["result"], dict)
            or not isinstance(decoded["_meta"], dict)
        ):
            _fail("PROVIDER_RESPONSE_INVALID", "Provider response envelope is invalid")
        return decoded
