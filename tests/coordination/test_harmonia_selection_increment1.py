from dataclasses import replace

import pytest

from olympus_v3.coordination.contracts import TaskState
from olympus_v3.coordination.harmonia_selection import (
    Candidate,
    KernelSelectionValidator,
    Prerequisite,
    SelectionAuthority,
    SelectionEscalation,
    derive_projection,
    propose_selection,
)
from olympus_v3.coordination.protocol import ValidationError


def authority(**changes):
    values = dict(
        installation_id="install-a", project_id="project-a", run_id="run-a",
        contract_id="contract-a", contract_generation=3, revocation_epoch=2,
        selection_epoch=7, plan_revision=4, snapshot_digest="sha256:snapshot",
    )
    values.update(changes)
    return SelectionAuthority(**values)


def candidate(task_id, worker_id=None):
    return Candidate(
        task_id=task_id, resolved_worker_id=worker_id or f"worker-{task_id}",
        binding_digest=f"sha256:binding-{task_id}",
        prerequisites=(Prerequisite("source-a", "receipt-a", "cleanup-a", TaskState.CLOSED),),
        current_task_state=TaskState.PROPOSED, released=True,
    )

def projection():
    return derive_projection(authority(), (candidate("task-b"), candidate("task-a")),
                             approved_task_ids=("task-a", "task-b"),
                             bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})


def test_projection_is_canonical_and_digest_stable():
    first = derive_projection(authority(), (candidate("task-b"), candidate("task-a")),
                              approved_task_ids=("task-a", "task-b"),
                              bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})
    second = derive_projection(authority(), tuple(reversed(first.candidates)),
                              approved_task_ids=("task-b", "task-a"),
                              bindings={"task-b": "worker-task-b", "task-a": "worker-task-a"})
    assert tuple(c.task_id for c in first.candidates) == ("task-a", "task-b")
    assert first.digest == second.digest


def test_policy_selects_first_and_empty_projection_escalates():
    p = projection()
    proposal = propose_selection(p)
    assert proposal.selected_task_id == "task-a"
    assert proposal.policy_id == "lowest-canonical-eligible-task-id"
    empty = derive_projection(authority(), (), approved_task_ids=(), bindings={})
    with pytest.raises(SelectionEscalation, match="no eligible candidate"):
        propose_selection(empty)


def test_proposal_is_task_only_and_rejects_worker_injection():
    p = projection()
    with pytest.raises(ValidationError, match="forbidden proposal field"):
        propose_selection(p, worker_id="attacker")
    wire = propose_selection(p).to_dict()
    assert not {"worker_id", "resolved_worker_id", "binding_digest", "contract_amendment", "evidence", "acp_session_id", "retry", "graph", "dispatch", "model", "agent"} & wire.keys()


def test_unknown_candidate_is_rejected_by_kernel_projection():
    with pytest.raises(ValidationError, match="unknown candidate"):
        derive_projection(authority(), (candidate("task-unknown"),),
                          approved_task_ids=("task-a", "task-b"),
                          bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})


def test_proposal_parser_is_exact_and_digest_bound():
    proposal = propose_selection(projection())
    assert proposal.from_dict(proposal.to_dict()) == proposal
    with pytest.raises(ValidationError):
        proposal.from_dict({**proposal.to_dict(), "worker_id": "attacker"})
    with pytest.raises(ValidationError):
        proposal.from_dict({**proposal.to_dict(), "selected_task_id": "task-b"})


def test_validator_recomputes_policy_and_rejects_unknown_or_tampered_values():
    p = projection()
    proposal = propose_selection(p)
    validator = KernelSelectionValidator(authority(), (candidate("task-a"), candidate("task-b")),
                                         approved_task_ids=("task-a", "task-b"),
                                         bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})
    assert validator.validate(proposal) == "task-a"
    for bad in (
        replace(proposal, selected_task_id="task-unknown"),
    ):
        with pytest.raises(ValidationError):
            validator.validate(bad)
    with pytest.raises(ValidationError):
        validator.validate(replace(proposal, eligibility_projection_digest="sha256:forged"))
    with pytest.raises(ValidationError):
        validator.validate(replace(proposal, plan_revision=99))


def test_authority_tamper_and_projection_tamper_fail_closed_without_effects():
    p = projection()
    validator = KernelSelectionValidator(authority(), (candidate("task-a"), candidate("task-b")),
                                         approved_task_ids=("task-a", "task-b"),
                                         bindings={"task-a": "worker-task-a", "task-b": "worker-task-b"})
    proposal = propose_selection(p)
    before = (p.digest, proposal.to_dict())
    with pytest.raises(ValidationError):
        validator.validate(replace(proposal, snapshot_digest="sha256:other"))
    assert before == (p.digest, proposal.to_dict())
