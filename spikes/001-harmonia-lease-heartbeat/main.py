#!/usr/bin/env python3
"""Throwaway spike for #107: renewable fencing + terminal/idempotent cleanup."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from olympus_v3.coordination.leases import Lease, LeaseResult
from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    SQLiteLedger,
    StoreScope,
)

SECOND = 1_000_000_000
TTL = 10 * SECOND


@dataclass
class FakeClock:
    now: int = 1_000_000_000_000

    def __call__(self) -> int:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += seconds * SECOND


class PrototypeLifecycle:
    """Disposable projection that models only the decision under test."""

    def __init__(self, ledger: SQLiteLedger, owner: str = "hermes") -> None:
        self.ledger = ledger
        self.owner = owner
        self.ledger.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS spike_terminal(
              run_id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('completed','error','cancelled')),
              observed_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spike_cancel_intent(
              run_id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spike_cleanup(
              run_id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spike_effect(
              run_id TEXT NOT NULL,
              effect TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY(run_id,effect)
            );
            """
        )

    def acquire(self, run_id: str, *, owner: str | None = None) -> Lease:
        result = self.ledger.acquire_lease(f"dispatch:{run_id}", owner or self.owner, ttl=TTL)
        assert result.status is LeaseResult.ACQUIRED and result.lease is not None
        return result.lease

    def heartbeat(self, lease: Lease) -> LeaseResult:
        result = self.ledger.renew_lease(lease, self.owner, ttl=TTL, token=lease.token)
        if result.lease is not None:
            assert result.lease.epoch == lease.epoch
            assert result.lease.token == lease.token
        return result.status

    def terminal(self, run_id: str, session_id: str, status: str) -> None:
        self.ledger.conn.execute(
            "INSERT OR IGNORE INTO spike_terminal VALUES(?,?,?,?)",
            (run_id, session_id, status, self.ledger.clock()),
        )

    def stop(self, run_id: str, session_id: str, lease: Lease) -> dict[str, Any]:
        terminal = self.ledger.conn.execute(
            "SELECT session_id,status FROM spike_terminal WHERE run_id=?", (run_id,)
        ).fetchone()
        if terminal is not None:
            if terminal["session_id"] != session_id:
                return {"state": "reconciliation_required", "effect": None}
            self.ledger.conn.execute(
                "INSERT OR IGNORE INTO spike_cleanup VALUES(?,?,?,?)",
                (run_id, session_id, "terminal_cleanup", self.ledger.clock()),
            )
            return {"state": "terminal_cleanup", "status": terminal["status"], "effect": None}

        if self.ledger.check_lease(lease, self.owner).lease is None:
            return {"state": "reconciliation_required", "effect": None}

        inserted = self.ledger.conn.execute(
            "INSERT OR IGNORE INTO spike_cancel_intent VALUES(?,?,?)",
            (run_id, session_id, self.ledger.clock()),
        ).rowcount
        effect = None
        if inserted:
            self.ledger.conn.execute(
                "INSERT OR IGNORE INTO spike_effect VALUES(?,?,?)",
                (run_id, "cancel", self.ledger.clock()),
            )
            effect = "cancel"
        return {"state": "cancel_requested", "effect": effect}

    def count(self, table: str, run_id: str) -> int:
        allowed = {"spike_terminal", "spike_cancel_intent", "spike_cleanup", "spike_effect"}
        assert table in allowed
        return self.ledger.conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (run_id,)
        ).fetchone()[0]


def run_spike(db_path: Path) -> dict[str, Any]:
    clock = FakeClock()
    ledger = SQLiteLedger(
        db_path,
        StoreScope("spike-install", "spike-project"),
        writer_authenticator=HMACWriterAuthenticator({("hermes", "default"): b"spike-writer-key"}),
        integrity_signer=HMACIntegritySigner(b"spike-integrity-key"),
        clock=clock,
    )
    lifecycle = PrototypeLifecycle(ledger)
    results: dict[str, Any] = {}
    try:
        # Scenario 1: heartbeat preserves the exact fence beyond its original deadline.
        lease = lifecycle.acquire("run-heartbeat")
        original_expiry = lease.expires_at
        clock.advance(8)
        assert lifecycle.heartbeat(lease) is LeaseResult.ACQUIRED
        renewed = ledger.check_lease(lease, "hermes").lease
        assert renewed is not None
        assert renewed.epoch == lease.epoch and renewed.token == lease.token
        assert renewed.expires_at > original_expiry
        clock.advance(3)
        assert clock.now > original_expiry
        assert ledger.check_lease(lease, "hermes").lease is not None
        lifecycle.terminal("run-heartbeat", "session-a", "completed")
        clock.advance(8)
        assert ledger.check_lease(lease, "hermes").lease is None
        first = lifecycle.stop("run-heartbeat", "session-a", lease)
        second = lifecycle.stop("run-heartbeat", "session-a", lease)
        assert first == second == {"state": "terminal_cleanup", "status": "completed", "effect": None}
        assert lifecycle.count("spike_terminal", "run-heartbeat") == 1
        assert lifecycle.count("spike_cleanup", "run-heartbeat") == 1
        assert lifecycle.count("spike_cancel_intent", "run-heartbeat") == 0
        assert lifecycle.count("spike_effect", "run-heartbeat") == 0
        results["heartbeat_terminal_cleanup"] = {
            "result": "PASS",
            "same_epoch": renewed.epoch == lease.epoch,
            "same_token": renewed.token == lease.token,
            "original_deadline_crossed": True,
            "terminal_rows": 1,
            "cleanup_rows_after_two_stops": 1,
            "cancel_effects": 0,
        }

        # Scenario 2: active stop keeps write-ahead intent and deduplicates the effect.
        active = lifecycle.acquire("run-active")
        active_first = lifecycle.stop("run-active", "session-b", active)
        active_second = lifecycle.stop("run-active", "session-b", active)
        assert active_first == {"state": "cancel_requested", "effect": "cancel"}
        assert active_second == {"state": "cancel_requested", "effect": None}
        assert lifecycle.count("spike_cancel_intent", "run-active") == 1
        assert lifecycle.count("spike_effect", "run-active") == 1
        results["active_stop_write_ahead"] = {
            "result": "PASS",
            "intent_rows_after_two_stops": 1,
            "external_cancel_effects_after_two_stops": 1,
        }

        # Scenario 3: expiry without terminal evidence remains fail-closed.
        expired = lifecycle.acquire("run-expired")
        clock.advance(11)
        expired_stop = lifecycle.stop("run-expired", "session-c", expired)
        assert expired_stop == {"state": "reconciliation_required", "effect": None}
        assert lifecycle.count("spike_cleanup", "run-expired") == 0
        assert lifecycle.count("spike_effect", "run-expired") == 0
        results["expired_without_evidence"] = {"result": "PASS", **expired_stop}

        # Scenario 4: foreign token, replaced epoch and mismatched session are rejected.
        protected = lifecycle.acquire("run-protected")
        foreign = ledger.renew_lease(protected, "hermes", ttl=TTL, token="foreign-token")
        assert foreign.status is LeaseResult.NOT_LEASE_OWNER
        clock.advance(11)
        replacement = lifecycle.acquire("run-protected", owner="other-owner")
        stale = ledger.renew_lease(protected, "hermes", ttl=TTL, token=protected.token)
        assert replacement.epoch > protected.epoch
        assert stale.status is LeaseResult.STALE_FENCE

        matched = lifecycle.acquire("run-mismatch")
        lifecycle.terminal("run-mismatch", "session-correct", "completed")
        mismatch = lifecycle.stop("run-mismatch", "session-wrong", matched)
        assert mismatch == {"state": "reconciliation_required", "effect": None}
        assert lifecycle.count("spike_cleanup", "run-mismatch") == 0
        results["adversarial_fencing"] = {
            "result": "PASS",
            "foreign_token": foreign.status.value,
            "replaced_epoch": stale.status.value,
            "mismatched_session": mismatch["state"],
        }

        integrity = ledger.conn.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok"
        results["sqlite_integrity"] = {"result": "PASS", "value": integrity}
        results["verdict"] = "VALIDATED"
        return results
    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Preserve the experimental SQLite file")
    args = parser.parse_args()
    if args.db:
        args.db.parent.mkdir(parents=True, exist_ok=True)
        result = run_spike(args.db)
        result["database"] = str(args.db.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="harmonia-heartbeat-spike-") as directory:
            result = run_spike(Path(directory) / "spike.sqlite")
            result["database"] = "temporary"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
