from pathlib import Path

import pytest

from olympus_v3.coordination import (
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Principal,
    Result,
    SideEffectPolicy,
    SQLiteLedger,
    StoreScope,
    WriterContext,
    amend_contract,
)

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "writer-a")
WORKER = Principal(PROJECT, "hermes", "worker")


def _contract(*, generation: int = 0, revocation_epoch: int = 0, status: ContractState = ContractState.PROPOSED) -> ExecutionContract:
    return ExecutionContract(
        contract_id="contract-a",
        project_id=PROJECT,
        generation=generation,
        owner=OWNER,
        participants=(OWNER, WORKER),
        objective="build the feature",
        expected_outcome="verified feature",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={"worker": ("implement",)},
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 1000, 10, 5),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=OWNER,
        revocation_epoch=revocation_epoch,
        status=status,
    )


def _setup(tmp_path: Path) -> tuple[SQLiteLedger, HMACWriterAuthenticator, WriterContext]:
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("writer-a", "key-a"): b"writer-key"})
    signer = HMACIntegritySigner(b"integrity-key", key_id="integrity-a")
    db = SQLiteLedger(tmp_path / "coord.sqlite", scope, writer_authenticator=auth, integrity_signer=signer)
    lease = db.acquire_lease("ledger", "writer-a", ttl=10_000_000_000)
    assert lease.lease is not None
    context = WriterContext(scope, "writer-a", "key-a", "ledger", lease.lease.epoch, lease.lease.expires_at)
    return db, auth, context


def _signed_event(db: SQLiteLedger, auth: HMACWriterAuthenticator, context: WriterContext, *, aggregate: str = "aggregate-a", message_id: str | None = None):
    draft = db.draft(aggregate, "state.set", {"value": 3}, writer=context)
    return auth.sign(draft, context), message_id


def _snapshot(db: SQLiteLedger, tables: tuple[str, ...]) -> dict[str, list[tuple[object, ...]]]:
    return {
        table: [tuple(row) for row in db.conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        for table in tables
    }


def _raise_at(stage: str):
    def fault(actual: str) -> None:
        if actual == stage:
            raise RuntimeError(f"injected failure at {stage}")

    return fault


@pytest.mark.parametrize("stage", ("after_event_insert", "after_projection", "after_inbox", "after_outbox"))
def test_receive_rolls_back_at_each_transaction_boundary(tmp_path, stage):
    db, auth, context = _setup(tmp_path)
    before = _snapshot(db, ("events", "projections", "inbox", "outbox"))
    draft, message_id = _signed_event(db, auth, context, message_id="message-a")
    db.fault = _raise_at(stage)

    with pytest.raises(RuntimeError, match=stage):
        db.receive(message_id, draft, context)

    assert _snapshot(db, ("events", "projections", "inbox", "outbox")) == before
    db.close()


@pytest.mark.parametrize("stage", ("after_contract_version", "after_contract_head"))
def test_create_contract_rolls_back_at_each_transaction_boundary(tmp_path, stage):
    db, _, _ = _setup(tmp_path)
    before = _snapshot(db, ("contract_versions", "contract_heads"))
    db.fault = _raise_at(stage)

    with pytest.raises(RuntimeError, match=stage):
        db.create_contract(_contract())

    assert _snapshot(db, ("contract_versions", "contract_heads")) == before
    db.close()


def _amendment_proof(db: SQLiteLedger, auth: HMACWriterAuthenticator, context: WriterContext, amendment):
    payload = {
        "contract_id": amendment.new_contract.contract_id,
        "prior_contract": amendment.prior_contract.to_dict(),
        "new_contract": amendment.new_contract.to_dict(),
        "prior_generation": amendment.prior_generation,
        "revocation_epoch": amendment.revocation_epoch,
        "rationale": amendment.rationale,
        "issuer": amendment.issuer.to_dict(),
        "affected_identities": list(amendment.affected_identities),
    }
    return auth.sign(db.draft("contract", "contract.advance", payload, writer=context, contract_generation=0, revocation_epoch=0), context)


@pytest.mark.parametrize(
    "stage",
    (
        "after_event_insert",
        "after_projection",
        "after_contract_version",
        "after_contract_head",
        "after_authority_reconciliation",
        "after_outbox",
    ),
)
def test_advance_contract_rolls_back_at_each_transaction_boundary(tmp_path, stage):
    db, auth, context = _setup(tmp_path)
    original = _contract(status=ContractState.ACTIVE)
    assert db.create_contract(original) is Result.APPLIED
    amendment = amend_contract(original, rationale="scope clarified", issuer=OWNER, affected_identities=("task-1",))
    before = _snapshot(db, ("events", "projections", "contract_versions", "contract_heads", "inbox", "outbox"))
    db.fault = _raise_at(stage)

    with pytest.raises(RuntimeError, match=stage):
        db.advance_contract(
            amendment,
            context,
            expected_generation=0,
            expected_revocation_epoch=0,
            proof=_amendment_proof(db, auth, context, amendment),
        )

    assert _snapshot(db, ("events", "projections", "contract_versions", "contract_heads", "inbox", "outbox")) == before
    db.close()


def test_receive_positive_control_commits_all_rows(tmp_path):
    db, auth, context = _setup(tmp_path)
    draft, message_id = _signed_event(db, auth, context, message_id="message-a")

    assert db.receive(message_id, draft, context).status is Result.APPLIED
    assert all(_snapshot(db, (table,))[table] for table in ("events", "projections", "inbox", "outbox"))
    db.close()


def test_create_contract_positive_control_commits_both_contract_rows(tmp_path):
    db, _, _ = _setup(tmp_path)

    assert db.create_contract(_contract()) is Result.APPLIED
    assert all(_snapshot(db, (table,))[table] for table in ("contract_versions", "contract_heads"))
    db.close()


def test_advance_contract_positive_control_commits_all_rows(tmp_path):
    db, auth, context = _setup(tmp_path)
    original = _contract(status=ContractState.ACTIVE)
    assert db.create_contract(original) is Result.APPLIED
    amendment = amend_contract(original, rationale="scope clarified", issuer=OWNER, affected_identities=("task-1",))

    assert db.advance_contract(
        amendment,
        context,
        expected_generation=0,
        expected_revocation_epoch=0,
        proof=_amendment_proof(db, auth, context, amendment),
    ) is Result.APPLIED
    assert all(
        _snapshot(db, (table,))[table]
        for table in ("events", "projections", "contract_versions", "contract_heads", "outbox")
    )
    db.close()
