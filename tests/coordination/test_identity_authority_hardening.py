import hashlib
from threading import Barrier, BrokenBarrierError, Thread

import pytest

from olympus_v3.coordination.capabilities import (
    AuthoritySnapshot,
    AuthorizationDenial,
    CapabilityClaim,
    ReplayCache,
    authorize,
    issue_capability,
)
from olympus_v3.coordination.contracts import ContractLimits, ContractState, ExecutionContract, SideEffectPolicy
from olympus_v3.coordination.identity import (
    IdentityRegistry,
    KeyPurpose,
    WorkloadBinding,
    create_holder_proof,
    issue_identity_credential,
    verify_holder_proof,
)
from olympus_v3.coordination.protocol import Principal, ValidationError


class Clock:
    def __init__(self, value: int = 1_000):
        self.value = value

    def __call__(self) -> int:
        return self.value


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _registry() -> IdentityRegistry:
    registry = IdentityRegistry(clock=Clock())
    registry.register_key("issuer-key", b"issuer-secret-material-00000001", purpose=KeyPurpose.ISSUER, ttl=10_000)
    registry.register_key("holder-key", b"holder-secret-material-00000001", purpose=KeyPurpose.HOLDER, ttl=10_000)
    registry.register_identity("identity-a", ttl=10_000)
    return registry


def _contract(*, allowed_effects=("filesystem",)) -> ExecutionContract:
    owner = Principal("project-a", "hermes", "owner")
    worker = Principal("project-a", "hermes", "worker")
    return ExecutionContract(
        contract_id="contract-a",
        project_id="project-a",
        generation=0,
        owner=owner,
        participants=(owner, worker),
        objective="secure coordination",
        expected_outcome="verified boundary",
        included_scopes=("src/",),
        excluded_scopes=(),
        role_permissions={"worker": ("publish",)},
        evidence_gates=(),
        side_effect_policy=SideEffectPolicy(allowed_effects, 1, True),
        limits=ContractLimits(1, 60, 1, 100, 5, 5),
        escalation_conditions=("ambiguity",),
        completion_authority=owner,
        amendment_authority=owner,
        status=ContractState.ACTIVE,
    )


def _scenario(*, issuer="aether-issuer", audience="olympus-r4", snapshot_issuer="aether-issuer", snapshot_audience="olympus-r4", issuer_effects=("filesystem",), project_effects=("filesystem",), task_effects=("filesystem",)):
    registry = _registry()
    binding = WorkloadBinding("install-a", "project-a", "worker", "hefesto", "session-a", "runtime-a")
    credential = issue_identity_credential(
        registry,
        binding,
        issuer=issuer,
        audience=audience,
        key_id="issuer-key",
        identity_id="identity-a",
        holder_key_id="holder-key",
        not_before=1_000,
        expires_at=2_000,
    )
    claim = CapabilityClaim(
        "capability-a",
        "identity-a",
        "install-a",
        "project-a",
        "contract-a",
        0,
        "task-a",
        audience,
        "channel:build",
        ("publish",),
        ("filesystem",),
        1,
        0,
        1_000,
        2_000,
        _digest("nonce"),
    )
    capability = issue_capability(registry, claim, issuer=issuer, key_id="issuer-key")
    request_digest = _digest("request")
    proof = create_holder_proof(
        registry,
        "holder-key",
        challenge=_digest("challenge"),
        subject_canonical=capability.to_dict(),
        request_digest=request_digest,
    )
    snapshot = AuthoritySnapshot(
        installation_id="install-a",
        project_id="project-a",
        contract=_contract(),
        fence_epoch=1,
        fence_expires_at=2_000,
        issuer_ceiling=("publish",),
        project_ceiling=("publish",),
        task_grants={"task-a": ("publish",)},
        trusted_issuer=snapshot_issuer,
        audience=snapshot_audience,
        issuer_effect_ceiling=issuer_effects,
        project_effect_ceiling=project_effects,
        task_effect_grants={"task-a": task_effects},
    )
    return registry, binding, credential, capability, proof, snapshot, request_digest


def _authorize(scenario):
    registry, binding, credential, capability, proof, snapshot, request_digest = scenario
    return authorize(
        registry,
        principal=Principal("project-a", "hermes", "worker"),
        request_binding=binding,
        credential=credential,
        capability=capability,
        proof=proof,
        snapshot=snapshot,
        audience=credential.audience,
        request_target="channel:build",
        request_permission="publish",
        request_effect_class="filesystem",
        request_digest=request_digest,
        replay_cache=ReplayCache(clock=Clock()),
        now=1_500,
    )


def test_registry_separates_issuer_and_holder_key_purposes():
    registry = _registry()
    claim = CapabilityClaim(
        "capability-a", "identity-a", "install-a", "project-a", "contract-a", 0, "task-a", "olympus-r4",
        "channel:build", ("publish",), (), 1, 0, 1_000, 2_000, _digest("nonce"),
    )
    with pytest.raises(ValidationError):
        issue_capability(registry, claim, issuer="aether-issuer", key_id="holder-key")
    with pytest.raises(ValidationError):
        create_holder_proof(
            registry,
            "issuer-key",
            challenge=_digest("challenge"),
            subject_canonical={},
            request_digest=_digest("request"),
        )


def test_authorize_denies_jointly_signed_but_untrusted_issuer():
    result = _authorize(_scenario(issuer="attacker-issuer"))
    assert result.granted is False
    assert result.reason == AuthorizationDenial.BINDING_MISMATCH


def test_authorize_denies_caller_selected_untrusted_audience():
    result = _authorize(_scenario(audience="attacker-service"))
    assert result.granted is False
    assert result.reason == AuthorizationDenial.BINDING_MISMATCH


@pytest.mark.parametrize(
    "overrides",
    [
        {"issuer_effects": ()},
        {"project_effects": ()},
        {"task_effects": ()},
    ],
)
def test_authorize_denies_effect_missing_from_any_policy_layer(overrides):
    result = _authorize(_scenario(**overrides))
    assert result.granted is False
    assert result.reason == AuthorizationDenial.PERMISSION_DENIED


def test_authorize_grants_effect_only_when_every_policy_layer_and_contract_allow_it():
    assert _authorize(_scenario()).granted is True


def test_identity_and_capability_ttls_are_bounded():
    registry = _registry()
    binding = WorkloadBinding("install-a", "project-a", "worker", "hefesto", "session-a", "runtime-a")
    with pytest.raises(ValidationError):
        issue_identity_credential(
            registry,
            binding,
            issuer="aether-issuer",
            audience="olympus-r4",
            key_id="issuer-key",
            identity_id="identity-a",
            holder_key_id="holder-key",
            not_before=1_000,
            expires_at=1_000 + 86_401,
        )
    with pytest.raises(ValidationError):
        CapabilityClaim(
            "capability-a", "identity-a", "install-a", "project-a", "contract-a", 0, "task-a", "olympus-r4",
            "channel:build", ("publish",), (), 1, 0, 1_000, 1_000 + 86_401, _digest("nonce"),
        )


def test_replay_cache_consumption_is_atomic_under_concurrency():
    barrier = Barrier(2)

    class RacingDict(dict):
        def __contains__(self, key):
            present = super().__contains__(key)
            try:
                barrier.wait(timeout=0.1)
            except BrokenBarrierError:
                pass
            return present

    cache = ReplayCache(clock=Clock())
    cache._entries = RacingDict()
    results = []
    workers = [Thread(target=lambda: results.append(cache.consume("same-proof", expires_at=2_000))) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=1)
    assert all(not worker.is_alive() for worker in workers)
    assert results.count(True) == 1
    assert results.count(False) == 1


def test_holder_proof_subject_is_size_and_depth_bounded_and_verifier_fails_closed():
    registry = _registry()
    request_digest = _digest("request")
    proof = create_holder_proof(
        registry, "holder-key", challenge=_digest("challenge"), subject_canonical={"claim": "bounded"},
        request_digest=request_digest,
    )
    oversized = {"claim": "x" * 65_537}
    with pytest.raises(ValidationError):
        create_holder_proof(
            registry, "holder-key", challenge=_digest("challenge"), subject_canonical=oversized,
            request_digest=request_digest,
        )
    assert verify_holder_proof(
        registry, proof, expected_holder_key_id="holder-key", subject_canonical=oversized,
        request_digest=request_digest,
    ) is False
    nested = "leaf"
    for _ in range(18):
        nested = [nested]
    with pytest.raises(ValidationError):
        create_holder_proof(
            registry, "holder-key", challenge=_digest("challenge"), subject_canonical=nested,
            request_digest=request_digest,
        )
