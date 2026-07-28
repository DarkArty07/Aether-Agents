from pathlib import Path

from olympus_v3.coordination.leases import LeaseResult
from olympus_v3.coordination.ledger import HMACIntegritySigner, HMACWriterAuthenticator, SQLiteLedger, StoreScope


def test_lease_acquire_renew_takeover_persists(tmp_path: Path):
    scope = StoreScope("install-a", "project-a")
    now = [100]
    path = tmp_path / "coord.sqlite"
    db = SQLiteLedger(
        path,
        scope,
        writer_authenticator=HMACWriterAuthenticator({}),
        integrity_signer=HMACIntegritySigner(b"key"),
        clock=lambda: now[0],
    )
    first = db.acquire_lease("harmonia", "owner-a", ttl=10)
    assert first.status is LeaseResult.ACQUIRED and first.lease.epoch == 1
    db.close()
    db = SQLiteLedger(
        path,
        scope,
        writer_authenticator=HMACWriterAuthenticator({}),
        integrity_signer=HMACIntegritySigner(b"key"),
        clock=lambda: now[0],
    )
    assert db.acquire_lease("harmonia", "owner-b", ttl=10).status is LeaseResult.CONTENDED
    assert db.renew_lease(first.lease, "owner-a", ttl=10).lease.epoch == 1
    now[0] = 111
    taken = db.acquire_lease("harmonia", "owner-b", ttl=10)
    assert taken.status is LeaseResult.ACQUIRED and taken.lease.epoch == 2
    assert db.check_lease(first.lease).status is LeaseResult.STALE_FENCE
    db.close()
