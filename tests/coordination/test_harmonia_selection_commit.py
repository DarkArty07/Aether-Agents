from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from olympus_v3.coordination.contracts import (
    ContractLimits,
    ContractState,
    ExecutionContract,
    SideEffectPolicy,
    TaskState,
)
from olympus_v3.coordination.harmonia_selection import (
    Candidate,
    KernelSelectionValidator,
    Prerequisite,
    SelectionAuthority,
    derive_projection,
    propose_selection,
)
from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)
from olympus_v3.coordination.principal import Principal, ValidationError
from olympus_v3.coordination.selection_commit import KernelSelectionCommitter, rebuild_selection_decisions

PROJECT = "project-selection"
CONTRACT = "contract-selection"
RUN = "run-selection"

def _contract():
    owner = Principal(PROJECT, "server", "hermes")
    worker_a = Principal(PROJECT, "server", "worker-a")
    worker_b = Principal(PROJECT, "server", "worker-b")
    return ExecutionContract(CONTRACT, PROJECT, 0, owner, (owner, worker_a, worker_b), "selection", "selection",
        ("src",), ("secrets",), {"worker-a": ("execute",), "worker-b": ("execute",)}, (),
        SideEffectPolicy((), 0, True), ContractLimits(1, 600, 0, 100, 1, 1), ("ambiguity",), owner, owner, 0, ContractState.ACTIVE,
        task_worker_bindings={"task-a": worker_a, "task-b": worker_b})

def _open(path):
    scope = StoreScope("installation-selection", PROJECT)
    auth = HMACWriterAuthenticator({("hermes", "selection-writer"): b"w" * 32})
    ledger = SQLiteLedger(path, scope, writer_authenticator=auth, integrity_signer=HMACIntegritySigner(b"i" * 32, "selection-integrity"))
    if ledger.read_contract(CONTRACT) is None:
        assert ledger.create_contract(_contract()) in (Result.APPLIED, Result.DUPLICATE)
    lease = ledger.acquire_lease("selection-ledger", "hermes", ttl=3_600_000_000_000).lease
    assert lease is not None
    writer = WriterContext(scope, "hermes", "selection-writer", "selection-ledger", lease.epoch, lease.expires_at)
    return ledger, KernelSelectionCommitter(ledger, writer)

def _proposal(epoch=1):
    authority = SelectionAuthority("installation-selection", PROJECT, RUN, CONTRACT, 0, 0, epoch, 4, "sha256:snapshot")
    def c(task):
        return Candidate(task, f"worker-{task}", f"sha256:binding-{task}", (Prerequisite("source", "receipt", "cleanup", TaskState.CLOSED),), TaskState.PROPOSED, True)
    candidates = (c("task-b"), c("task-a"))
    projection = derive_projection(authority, candidates, approved_task_ids=("task-a", "task-b"), bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})
    return projection, propose_selection(projection)

def _validator(projection):
    return KernelSelectionValidator(projection.authority, projection.candidates, approved_task_ids=("task-a", "task-b"), bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})

def test_committer_rejects_projection_different_from_kernel_recomputation(tmp_path):
    ledger, committer = _open(tmp_path / "projection-drift.sqlite")
    trusted_projection, proposal = _proposal()
    trusted_validator = _validator(trusted_projection)
    attacker_candidate = Candidate(
        "task-a",
        "worker-attacker",
        "sha256:attacker-binding",
        trusted_projection.candidates[0].prerequisites,
        TaskState.PROPOSED,
        True,
    )
    forged_projection = derive_projection(
        trusted_projection.authority,
        (attacker_candidate,),
        approved_task_ids=("task-a", "task-b"),
        bindings={"task-a": "worker-attacker", "task-b": "worker-task-b"},
    )

    with pytest.raises(ValidationError, match="projection does not match current kernel state"):
        committer.commit(proposal, forged_projection, trusted_validator)

    assert not [e for e in ledger.events() if e["kind"] == "task.selection.committed"]


def test_sequential_epochs_use_versions_one_and_two(tmp_path):
    ledger, committer = _open(tmp_path / "sequential.sqlite")
    projection_one, proposal_one = _proposal(1)
    projection_two, proposal_two = _proposal(2)
    assert committer.commit(proposal_one, projection_one, _validator(projection_one)).status is Result.APPLIED
    assert committer.commit(proposal_two, projection_two, _validator(projection_two)).status is Result.APPLIED
    events = [e for e in ledger.events() if e["kind"] == "task.selection.committed"]
    assert [event["version"] for event in events] == [1, 2]
    assert [__import__("json").loads(event["payload"])["expected_version"] for event in events] == [0, 1]


def test_epoch_one_replay_after_epoch_two_is_duplicate(tmp_path):
    ledger, committer = _open(tmp_path / "replay-after-two.sqlite")
    projection_one, proposal_one = _proposal(1)
    projection_two, proposal_two = _proposal(2)
    assert committer.commit(proposal_one, projection_one, _validator(projection_one)).status is Result.APPLIED
    assert committer.commit(proposal_two, projection_two, _validator(projection_two)).status is Result.APPLIED
    replay = committer.commit(proposal_one, projection_one, _validator(projection_one))
    assert replay.status is Result.DUPLICATE
    assert len([e for e in ledger.events() if e["kind"] == "task.selection.committed"]) == 2


def test_epoch_two_before_epoch_one_and_epoch_gap_are_rejected(tmp_path):
    for name, epoch in (("before-one", 2), ("gap", 3)):
        ledger, committer = _open(tmp_path / f"{name}.sqlite")
        projection, proposal = _proposal(epoch)
        result = committer.commit(proposal, projection, _validator(projection))
        assert result.status is Result.CAS_CONFLICT
        assert not [e for e in ledger.events() if e["kind"] == "task.selection.committed"]


def test_different_candidates_racing_for_same_epoch_have_one_winner(tmp_path):
    path = tmp_path / "candidate-race.sqlite"
    ledger, _ = _open(path)
    ledger.close()
    projection_a, proposal_a = _proposal(1)
    authority = projection_a.authority
    candidate_b = Candidate("task-b", "worker-task-b", "sha256:binding-task-b", projection_a.candidates[1].prerequisites, TaskState.PROPOSED, True)
    projection_b = derive_projection(authority, (candidate_b,), approved_task_ids=("task-a", "task-b"), bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})
    proposal_b = propose_selection(projection_b)

    def race(projection, proposal):
        local, committer = _open(path)
        try:
            return committer.commit(proposal, projection, _validator(projection))
        finally:
            local.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda values: race(*values), ((projection_a, proposal_a), (projection_b, proposal_b))))
    assert sorted(result.status.value for result in results) == ["APPLIED", "CAS_CONFLICT"]
    check, _ = _open(path)
    assert len([e for e in check.events() if e["kind"] == "task.selection.committed"]) == 1
    check.close()

def test_commit_exact_replay_has_one_event_and_rebuilds(tmp_path):
    ledger, committer = _open(tmp_path / "selection.sqlite")
    projection, proposal = _proposal()
    validator = _validator(projection)
    first = committer.commit(proposal, projection, validator)
    second = committer.commit(proposal, projection, validator)
    assert first.status is Result.APPLIED
    assert second.status is Result.DUPLICATE
    events = [e for e in ledger.events() if e["kind"] == "task.selection.committed"]
    assert len(events) == 1
    assert events[0]["aggregate"] == f"selection:{RUN}"
    assert rebuild_selection_decisions(ledger)[(RUN, 1)].selected_task_id == "task-a"

def test_same_proposal_id_changed_bytes_is_conflict_without_event(tmp_path):
    ledger, committer = _open(tmp_path / "conflict.sqlite")
    projection, proposal = _proposal()
    validator = _validator(projection)
    assert committer.commit(proposal, projection, validator).status is Result.APPLIED
    changed = replace(proposal, selected_task_id="task-b")
    result = committer.commit(changed, projection, validator)
    assert result.status is Result.IDEMPOTENCY_CONFLICT
    assert len([e for e in ledger.events() if e["kind"] == "task.selection.committed"]) == 1

def test_different_proposal_for_committed_epoch_is_cas_conflict(tmp_path):
    ledger, committer = _open(tmp_path / "epoch.sqlite")
    projection, proposal = _proposal()
    validator = _validator(projection)
    assert committer.commit(proposal, projection, validator).status is Result.APPLIED
    other_projection, other = _proposal()
    other = replace(other, proposal_id="sha256:other-proposal")
    result = committer.commit(other, other_projection, _validator(other_projection))
    assert result.status is Result.CAS_CONFLICT
    assert len([e for e in ledger.events() if e["kind"] == "task.selection.committed"]) == 1

def test_two_connections_have_one_cas_winner(tmp_path):
    path = tmp_path / "race.sqlite"
    ledger, committer = _open(path)
    projection, proposal = _proposal()
    ledger.close()
    def race_commit():
        local, local_commit = _open(path)
        try:
            return local_commit.commit(proposal, projection, _validator(projection))
        finally:
            local.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: race_commit(), (1, 2)))
    assert sorted(result.status.value for result in results) == ["APPLIED", "DUPLICATE"]
    check, _ = _open(path)
    assert len([e for e in check.events() if e["kind"] == "task.selection.committed"]) == 1
    check.close()

def test_stale_or_tampered_proposal_has_zero_effects(tmp_path):
    ledger, committer = _open(tmp_path / "stale.sqlite")
    projection, proposal = _proposal()
    before = len(ledger.events())
    for bad in (
        replace(proposal, contract_generation=99),
        replace(proposal, revocation_epoch=99),
        replace(proposal, plan_revision=99),
        replace(proposal, snapshot_digest="sha256:bad"),
        replace(proposal, eligibility_projection_digest="sha256:bad"),
        replace(proposal, policy_id="other-policy"),
        replace(proposal, selected_task_id="task-b"),
    ):
        with pytest.raises(ValidationError):
            committer.commit(bad, projection, _validator(projection))
    assert len(ledger.events()) == before

def test_crash_before_commit_persists_no_selection_and_can_retry(tmp_path):
    ledger, committer = _open(tmp_path / "crash.sqlite")
    projection, proposal = _proposal()
    original = ledger._stage
    ledger.fault = lambda stage: (_ for _ in ()).throw(RuntimeError("crash")) if stage == "before_commit" else None
    with pytest.raises(RuntimeError, match="crash"):
        committer.commit(proposal, projection, _validator(projection))
    assert not [e for e in ledger.events() if e["kind"] == "task.selection.committed"]
    ledger.fault = None
    ledger._stage = original
    assert committer.commit(proposal, projection, _validator(projection)).status is Result.APPLIED


def test_commit_payload_contains_authority_and_cas_fields_and_chain_verifies(tmp_path):
    ledger, committer = _open(tmp_path / "payload.sqlite")
    projection, proposal = _proposal()
    assert committer.commit(proposal, projection, _validator(projection)).status is Result.APPLIED
    payload = next(__import__("json").loads(e["payload"]) for e in ledger.events() if e["kind"] == "task.selection.committed")
    assert payload["expected_version"] == 0
    assert payload["proposal_id"] == proposal.proposal_id
    assert payload["eligibility_projection_digest"] == projection.digest
    assert payload["resolved_worker_id"] == "worker-task-a"
    assert payload["binding_digest"] == "sha256:binding-task-a"
    assert ledger.verify_chain()
