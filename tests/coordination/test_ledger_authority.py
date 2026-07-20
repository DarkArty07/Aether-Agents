from pathlib import Path

from olympus_v3.coordination import (
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    Principal,
    SideEffectPolicy,
    amend_contract,
)
from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
REVIEWER = Principal(PROJECT, "hermes", "reviewer")
IMPOSTOR = Principal(PROJECT, "mallory", "owner")


def make_contract(*, amendment_authority=OWNER, generation=0, revocation_epoch=0, status=ContractState.ACTIVE):
    participants = (OWNER, REVIEWER) if amendment_authority is OWNER else (OWNER, REVIEWER, amendment_authority)
    return ExecutionContract(
        contract_id="contract-a",
        project_id=PROJECT,
        generation=generation,
        owner=OWNER,
        participants=participants,
        objective="build the feature",
        expected_outcome="verified feature",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={"reviewer": ("review",)},
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 1000, 10, 5),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=amendment_authority,
        revocation_epoch=revocation_epoch,
        status=status,
    )


def setup(tmp_path: Path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key", ("reviewer", "key-reviewer"): b"reviewer-key"})
    signer = HMACIntegritySigner(b"integrity-key", key_id="integrity-a")
    db = SQLiteLedger(tmp_path / "coord.sqlite", scope, writer_authenticator=auth, integrity_signer=signer)
    lease = db.acquire_lease("ledger", "owner", ttl=10_000_000_000)
    context = WriterContext(scope, "owner", "key-owner", "ledger", lease.lease.epoch, lease.lease.expires_at)
    return db, auth, context


def amendment_proof(db, auth, amendment, context):
    return auth.sign(db._amendment_draft(amendment, context), context)


def snapshot(db):
    tables = ("events", "projections", "contract_versions", "contract_heads", "inbox", "outbox")
    return {
        table: [dict(row) for row in db.conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        for table in tables
    }


def provision(db, contract):
    assert db.create_contract(contract) is Result.APPLIED


def test_wrong_issuer_rejects_without_mutating_any_authority_table(tmp_path):
    db, auth, context = setup(tmp_path)
    provision(db, make_contract())
    amendment = amend_contract(db.read_contract("contract-a"), rationale="tighten scope", issuer=OWNER, affected_identities=("task-1",))
    object.__setattr__(amendment, "issuer", IMPOSTOR)
    before = snapshot(db)

    assert db.advance_contract(amendment, context, expected_generation=0, expected_revocation_epoch=0, proof=amendment_proof(db, auth, amendment, context)) is Result.AUTHENTICATION_FAILED
    assert snapshot(db) == before
    db.close()


def test_wrong_proof_identity_rejects_without_mutating_any_authority_table(tmp_path):
    db, auth, context = setup(tmp_path)
    provision(db, make_contract())
    amendment = amend_contract(db.read_contract("contract-a"), rationale="tighten scope", issuer=OWNER, affected_identities=("task-1",))
    wrong_context = WriterContext(context.scope, "reviewer", "key-reviewer", "ledger", context.fence, context.expires_at)
    before = snapshot(db)

    assert db.advance_contract(amendment, context, expected_generation=0, expected_revocation_epoch=0, proof=amendment_proof(db, auth, amendment, wrong_context)) is Result.AUTHENTICATION_FAILED
    assert snapshot(db) == before
    db.close()


def test_expected_generation_mismatch_is_atomic(tmp_path):
    db, auth, context = setup(tmp_path)
    provision(db, make_contract())
    amendment = amend_contract(db.read_contract("contract-a"), rationale="tighten scope", issuer=OWNER, affected_identities=("task-1",))
    before = snapshot(db)

    assert db.advance_contract(amendment, context, expected_generation=9, expected_revocation_epoch=0, proof=amendment_proof(db, auth, amendment, context)) is Result.CAS_CONFLICT
    assert snapshot(db) == before
    db.close()


def test_expected_revocation_epoch_mismatch_is_atomic(tmp_path):
    db, auth, context = setup(tmp_path)
    provision(db, make_contract())
    amendment = amend_contract(db.read_contract("contract-a"), rationale="tighten scope", issuer=OWNER, affected_identities=("task-1",))
    before = snapshot(db)

    assert db.advance_contract(amendment, context, expected_generation=0, expected_revocation_epoch=9, proof=amendment_proof(db, auth, amendment, context)) is Result.CAS_CONFLICT
    assert snapshot(db) == before
    db.close()


def test_stale_queued_authority_after_valid_amendment_is_atomic(tmp_path):
    db, auth, context = setup(tmp_path)
    provision(db, make_contract())
    original = db.read_contract("contract-a")
    queued = amend_contract(original, rationale="queued change", issuer=OWNER, affected_identities=("task-queued",))
    queued_proof = amendment_proof(db, auth, queued, context)
    valid = amend_contract(original, rationale="valid change", issuer=OWNER, affected_identities=("task-valid",))
    assert db.advance_contract(valid, context, expected_generation=0, expected_revocation_epoch=0, proof=amendment_proof(db, auth, valid, context)) is Result.APPLIED
    before = snapshot(db)

    assert db.advance_contract(queued, context, expected_generation=0, expected_revocation_epoch=0, proof=queued_proof) is Result.CAS_CONFLICT
    assert snapshot(db) == before
    db.close()


def test_owner_authorized_amendment_applies_atomically(tmp_path):
    db, auth, context = setup(tmp_path)
    provision(db, make_contract())
    amendment = amend_contract(db.read_contract("contract-a"), rationale="tighten scope", issuer=OWNER, affected_identities=("task-1",))

    assert db.advance_contract(amendment, context, expected_generation=0, expected_revocation_epoch=0, proof=amendment_proof(db, auth, amendment, context)) is Result.APPLIED
    assert db.read_contract("contract-a").generation == 1
    assert db.read_contract("contract-a").revocation_epoch == 1
    assert db.conn.execute("SELECT COUNT(*) FROM events WHERE kind='contract.advance'").fetchone()[0] == 1
    assert db.conn.execute("SELECT COUNT(*) FROM contract_versions").fetchone()[0] == 2
    assert tuple(db.conn.execute("SELECT generation,revocation_epoch FROM contract_heads").fetchone()) == (1, 1)
    assert db.conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1
    db.close()
