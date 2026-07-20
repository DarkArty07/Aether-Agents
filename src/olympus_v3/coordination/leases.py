"""SQLite-backed monotonic leases used for transaction fencing."""

from __future__ import annotations

import re
import secrets
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from .ledger import StoreScope

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_MAX_SQLITE_INTEGER = (1 << 63) - 1


def _valid_identifier(value: object) -> bool:
    return isinstance(value, str) and value == value.strip() and bool(_ID.fullmatch(value))


def _valid_ttl(value: object, now: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
        and 0 <= now <= _MAX_SQLITE_INTEGER
        and value <= _MAX_SQLITE_INTEGER - now
    )


class LeaseResult(StrEnum):
    ACQUIRED = "ACQUIRED"
    CONTENDED = "CONTENDED"
    STALE_FENCE = "STALE_FENCE"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    NOT_LEASE_OWNER = "NOT_LEASE_OWNER"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True, slots=True)
class Lease:
    scope: StoreScope
    resource: str
    owner: str
    epoch: int
    expires_at: int
    token: str = ""

    def __post_init__(self) -> None:
        if (
            not isinstance(self.scope, StoreScope)
            or not _valid_identifier(self.resource)
            or not _valid_identifier(self.owner)
            or not isinstance(self.epoch, int)
            or isinstance(self.epoch, bool)
            or self.epoch <= 0
            or not isinstance(self.expires_at, int)
            or isinstance(self.expires_at, bool)
            or self.expires_at <= 0
            or not isinstance(self.token, str)
            or len(self.token) > 128
        ):
            raise ValueError("invalid lease")


@dataclass(frozen=True, slots=True)
class LeaseOutcome:
    status: LeaseResult
    lease: Lease | None = None


class LeaseManager:
    """A small lease manager that persists state in a caller-owned SQLite file."""

    def __init__(self, path: str | None = None, scope: StoreScope | None = None, *, clock: Callable[[], int]):
        self.clock = clock
        self._conn = sqlite3.connect(path or ":memory:", isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._scope = scope
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS leases(
            installation_id TEXT NOT NULL, project_id TEXT NOT NULL, resource TEXT NOT NULL,
            owner TEXT NOT NULL, epoch INTEGER NOT NULL, expires_at INTEGER NOT NULL, token TEXT NOT NULL,
            PRIMARY KEY(installation_id, project_id, resource))"""
        )

    def _scope_ok(self, scope: StoreScope) -> bool:
        return isinstance(scope, StoreScope) and (self._scope is None or scope == self._scope)

    def acquire(self, scope: StoreScope, resource: str, owner: str, *, ttl: int) -> LeaseOutcome:
        now = self.clock()
        if (
            not self._scope_ok(scope)
            or not _valid_identifier(resource)
            or not _valid_identifier(owner)
            or not _valid_ttl(ttl, now)
        ):
            return LeaseOutcome(LeaseResult.INVALID_INPUT)
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
                (scope.installation_id, scope.project_id, resource),
            ).fetchone()
            if row and row["expires_at"] > now and row["owner"] != owner:
                self._conn.rollback()
                return LeaseOutcome(LeaseResult.CONTENDED)
            epoch = (
                row["epoch"]
                if row and row["owner"] == owner and row["expires_at"] > now
                else (row["epoch"] + 1 if row else 1)
            )
            token = row["token"] if row and row["owner"] == owner and row["expires_at"] > now else secrets.token_hex(32)
            self._conn.execute(
                "INSERT OR REPLACE INTO leases VALUES(?,?,?,?,?,?,?)",
                (scope.installation_id, scope.project_id, resource, owner, epoch, now + ttl, token),
            )
            self._conn.commit()
            return LeaseOutcome(LeaseResult.ACQUIRED, Lease(scope, resource, owner, epoch, now + ttl, token))
        except sqlite3.OperationalError:
            self._conn.rollback()
            return LeaseOutcome(LeaseResult.CONTENDED)

    def renew(self, lease: Lease, owner: str, epoch: int, *, ttl: int, token: str | None = None) -> LeaseOutcome:
        now = self.clock()
        if (
            not isinstance(lease, Lease)
            or not _valid_identifier(owner)
            or not isinstance(epoch, int)
            or isinstance(epoch, bool)
            or epoch <= 0
            or not _valid_ttl(ttl, now)
        ):
            return LeaseOutcome(LeaseResult.INVALID_INPUT)
        current = self._read(lease)
        if current is None or current.owner != owner or current.epoch != epoch:
            return LeaseOutcome(LeaseResult.STALE_FENCE)
        if token is not None and token != current.token:
            return LeaseOutcome(LeaseResult.NOT_LEASE_OWNER)
        if current.expires_at <= now:
            return LeaseOutcome(LeaseResult.LEASE_EXPIRED)
        updated = Lease(current.scope, current.resource, owner, epoch, now + ttl, current.token)
        self._conn.execute(
            "UPDATE leases SET expires_at=? WHERE installation_id=? AND project_id=? AND resource=? AND owner=? AND epoch=? AND token=?",
            (
                updated.expires_at,
                lease.scope.installation_id,
                lease.scope.project_id,
                lease.resource,
                owner,
                epoch,
                current.token,
            ),
        )
        return LeaseOutcome(LeaseResult.ACQUIRED, updated)

    def check(
        self, lease: Lease, owner: str | None = None, epoch: int | None = None, token: str | None = None
    ) -> LeaseOutcome:
        current = self._read(lease)
        if (
            current is None
            or (owner is not None and current.owner != owner)
            or (epoch is not None and current.epoch != epoch)
        ):
            return LeaseOutcome(LeaseResult.STALE_FENCE)
        if token is not None and current.token != token:
            return LeaseOutcome(LeaseResult.NOT_LEASE_OWNER)
        if current.expires_at <= self.clock():
            return LeaseOutcome(LeaseResult.LEASE_EXPIRED)
        return LeaseOutcome(LeaseResult.ACQUIRED, current)

    def _read(self, lease: Lease) -> Lease | None:
        row = self._conn.execute(
            "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
            (lease.scope.installation_id, lease.scope.project_id, lease.resource),
        ).fetchone()
        return (
            Lease(lease.scope, row["resource"], row["owner"], row["epoch"], row["expires_at"], row["token"])
            if row
            else None
        )

    def close(self) -> None:
        self._conn.close()


__all__ = ["Lease", "LeaseManager", "LeaseOutcome", "LeaseResult"]
