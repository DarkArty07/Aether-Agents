import hashlib
from dataclasses import FrozenInstanceError, replace

import pytest

from olympus_v3.coordination.capabilities import (
    AuthoritySnapshot,
    AuthorizationDenial,
    AuthorizationResult,
    CapabilityClaim,
    ReplayCache,
    SignedCapability,
    ValidationError,
    authorize,
    issue_capability,
    verify_capability_signature,
)
from olympus_v3.coordination.contracts import ContractLimits, ContractState, ExecutionContract, SideEffectPolicy
from olympus_v3.coordination.identity import (
    HolderProof,
    IdentityRegistry,
    KeyPurpose,
    WorkloadBinding,
    create_holder_proof,
    issue_identity_credential,
)
from olympus_v3.coordination.protocol import ParticipantCard, Principal

PROJECT = "project-a"
INSTALL = "install-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hermes", "worker")
ISSUER_SECRET = b"issuer-secret-key-material-0001"
HOLDER_SECRET = b"holder-secret-key-material-0001"
ATTACKER_HOLDER_SECRET = b"attacker-holder-key-material-01"
BINDING = WorkloadBinding(INSTALL, PROJECT, "worker", "hermes-profile", "session-a", "runtime-a")


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


REQUEST_DIGEST = digest("request-1")

BASE_CLAIM_KWARGS = dict(
    capability_id="capability-a", identity_id="identity-a", installation_id=INSTALL, project_id=PROJECT,
    contract_id="contract-a", generation=0, task_id="task-a", audience="olympus-r4", target="repo/file.py",
    permissions=("read_files",), effect_classes=(), fence_epoch=1, revocation_epoch=0, not_before=1000,
    expires_at=5000, nonce=digest("nonce-a"),
)


def make_claim(**overrides):
    return CapabilityClaim(**{**BASE_CLAIM_KWARGS, **overrides})


def make_registry(now=1000, *, clock=None, key_ttl=10_000, identity_ttl=10_000):
    registry = IdentityRegistry(clock=clock or Clock(now))
    registry.register_key("issuer-key-1", ISSUER_SECRET, purpose=KeyPurpose.ISSUER, ttl=key_ttl)
    registry.register_key("holder-key-1", HOLDER_SECRET, purpose=KeyPurpose.HOLDER, ttl=key_ttl)
    registry.register_key("holder-key-2", ATTACKER_HOLDER_SECRET, purpose=KeyPurpose.HOLDER, ttl=key_ttl)
    registry.register_identity("identity-a", ttl=identity_ttl)
    return registry


def make_contract(*, generation=0, revocation_epoch=0, role_permissions=None, status=ContractState.ACTIVE, participants=None):
    return ExecutionContract(
        contract_id="contract-a", project_id=PROJECT, generation=generation, owner=OWNER,
        participants=participants if participants is not None else (OWNER, WORKER),
        objective="build the feature", expected_outcome="verified feature", included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions=role_permissions if role_permissions is not None else {"worker": ("read_files", "write_files")},
        evidence_gates=(), side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 1000, 10, 5),
        escalation_conditions=("ambiguity",), completion_authority=OWNER, amendment_authority=OWNER,
        revocation_epoch=revocation_epoch, status=status,
    )


def build_scenario(
    registry, *, now=1000, generation=0, contract_revocation_epoch=0, fence_epoch=1, fence_expires_at=5000,
    claim_generation=0, claim_revocation_epoch=0, claim_fence_epoch=1, permissions=("read_files",), effect_classes=(),
    target="repo/file.py", task_id="task-a", capability_id="capability-a", nonce=None,
    issuer_ceiling=("read_files", "write_files"), project_ceiling=("read_files", "write_files"), task_grants=None,
    binding=None, principal=WORKER, identity_id="identity-a", holder_key_id="holder-key-1",
    credential_not_before=1000, credential_expires_at=5000, claim_not_before=1000, claim_expires_at=5000,
    role_permissions=None,
):
    contract = make_contract(generation=generation, revocation_epoch=contract_revocation_epoch, role_permissions=role_permissions)
    snapshot = AuthoritySnapshot(
        INSTALL, PROJECT, contract, fence_epoch, fence_expires_at, issuer_ceiling, project_ceiling,
        task_grants if task_grants is not None else {task_id: ("read_files", "write_files")},
        "hermes-issuer", "olympus-r4", ("filesystem",), ("filesystem",), {task_id: ("filesystem",)},
    )
    binding = binding or BINDING
    credential = issue_identity_credential(
        registry, binding, issuer="hermes-issuer", audience="olympus-r4", key_id="issuer-key-1",
        identity_id=identity_id, holder_key_id=holder_key_id, not_before=credential_not_before, expires_at=credential_expires_at,
    )
    claim = CapabilityClaim(
        capability_id, identity_id, INSTALL, PROJECT, "contract-a", claim_generation, task_id, "olympus-r4",
        target, permissions, effect_classes, claim_fence_epoch, claim_revocation_epoch, claim_not_before, claim_expires_at,
        nonce or digest(capability_id),
    )
    capability = issue_capability(registry, claim, issuer="hermes-issuer", key_id="issuer-key-1")
    proof = create_holder_proof(
        registry, holder_key_id, challenge=digest("challenge-1"), subject_canonical=capability.to_dict(), request_digest=REQUEST_DIGEST,
    )
    return {
        "registry": registry, "principal": principal, "request_binding": binding, "credential": credential,
        "capability": capability, "proof": proof, "snapshot": snapshot, "now": now,
    }


def retarget(registry, scenario, **claim_overrides):
    tampered_claim = replace(scenario["capability"].claim, **claim_overrides)
    tampered_capability = issue_capability(registry, tampered_claim, issuer=scenario["capability"].issuer, key_id=scenario["capability"].key_id)
    tampered_proof = create_holder_proof(
        registry, scenario["proof"].holder_key_id, challenge=scenario["proof"].challenge,
        subject_canonical=tampered_capability.to_dict(), request_digest=scenario["proof"].request_digest,
    )
    return {**scenario, "capability": tampered_capability, "proof": tampered_proof}


def call_authorize(
    scenario, *, replay_cache=None, request_permission="read_files", request_effect_class=None,
    request_target="repo/file.py", request_digest=REQUEST_DIGEST, audience="olympus-r4", **overrides,
):
    values = {**scenario, **overrides}
    cache = replay_cache or ReplayCache(clock=Clock(values["now"]))
    return authorize(
        values["registry"], principal=values["principal"], request_binding=values["request_binding"],
        credential=values["credential"], capability=values["capability"], proof=values["proof"], snapshot=values["snapshot"],
        audience=audience, request_target=request_target, request_permission=request_permission,
        request_effect_class=request_effect_class, request_digest=request_digest, replay_cache=cache, now=values["now"],
    )


# ---------------------------------------------------------------------------
# CapabilityClaim: strict wire schema and bounded inputs
# ---------------------------------------------------------------------------

def test_capability_claim_round_trips_and_is_frozen():
    claim = make_claim()
    assert CapabilityClaim.from_dict(claim.to_dict()) == claim
    with pytest.raises(FrozenInstanceError):
        claim.target = "other"


def test_capability_claim_strict_wire_schema_rejects_unknown_and_missing_fields():
    payload = make_claim().to_dict()
    with pytest.raises(ValidationError):
        CapabilityClaim.from_dict({**payload, "extra": True})
    with pytest.raises(ValidationError):
        CapabilityClaim.from_dict({k: v for k, v in payload.items() if k != "nonce"})


def test_capability_claim_rejects_wildcard_audience():
    with pytest.raises(ValidationError):
        make_claim(audience="*")


@pytest.mark.parametrize("field,value", [
    ("not_before", -1), ("not_before", True), ("expires_at", True), ("expires_at", 2**64),
    ("fence_epoch", 0), ("fence_epoch", -1), ("fence_epoch", True),
    ("revocation_epoch", -1), ("revocation_epoch", True), ("generation", -1), ("generation", True),
])
def test_capability_claim_rejects_negative_bool_and_overflow_numeric_fields(field, value):
    with pytest.raises(ValidationError):
        make_claim(**{field: value})


def test_capability_claim_rejects_inverted_or_equal_validity_window():
    with pytest.raises(ValidationError):
        make_claim(not_before=2000, expires_at=1000)
    with pytest.raises(ValidationError):
        make_claim(not_before=1000, expires_at=1000)


def test_capability_claim_rejects_empty_duplicate_and_oversized_permissions():
    with pytest.raises(ValidationError):
        make_claim(permissions=())
    with pytest.raises(ValidationError):
        make_claim(permissions=("read_files", "read_files"))
    with pytest.raises(ValidationError):
        make_claim(permissions=tuple(f"perm_{i}" for i in range(64)))


def test_capability_claim_allows_empty_effect_classes():
    assert make_claim(effect_classes=()).effect_classes == ()


@pytest.mark.parametrize("bad", ["", "not-hex", "a" * 63, "a" * 65, "A" * 64])
def test_capability_claim_rejects_malformed_nonce_shape(bad):
    with pytest.raises(ValidationError):
        make_claim(nonce=bad)


# ---------------------------------------------------------------------------
# SignedCapability: issuance and signature verification
# ---------------------------------------------------------------------------

def test_signed_capability_round_trips_and_valid_path_verifies():
    registry = make_registry()
    signed = issue_capability(registry, make_claim(), issuer="hermes-issuer", key_id="issuer-key-1")
    assert SignedCapability.from_dict(signed.to_dict()) == signed
    assert verify_capability_signature(registry, signed) is True
    with pytest.raises(ValidationError):
        SignedCapability.from_dict({**signed.to_dict(), "extra": 1})


def test_signed_capability_secret_material_never_serialized():
    registry = make_registry()
    signed = issue_capability(registry, make_claim(), issuer="hermes-issuer", key_id="issuer-key-1")
    blob = repr(signed.to_dict())
    assert ISSUER_SECRET.decode() not in blob


def test_issue_capability_fails_closed_for_unknown_or_revoked_key():
    registry = make_registry()
    claim = make_claim()
    with pytest.raises(ValidationError):
        issue_capability(registry, claim, issuer="hermes-issuer", key_id="unknown-key")
    registry.revoke_key("issuer-key-1")
    with pytest.raises(ValidationError):
        issue_capability(registry, claim, issuer="hermes-issuer", key_id="issuer-key-1")


def test_verify_capability_signature_denies_altered_claim_and_reattributed_issuer():
    registry = make_registry()
    signed = issue_capability(registry, make_claim(), issuer="hermes-issuer", key_id="issuer-key-1")
    reattributed = SignedCapability(signed.claim, "someone-else", signed.key_id, signed.signature)
    assert verify_capability_signature(registry, reattributed) is False
    altered = SignedCapability(replace(signed.claim, target="repo/other.py"), signed.issuer, signed.key_id, signed.signature)
    assert verify_capability_signature(registry, altered) is False


# ---------------------------------------------------------------------------
# AuthoritySnapshot
# ---------------------------------------------------------------------------

def test_authority_snapshot_requires_active_contract():
    with pytest.raises(ValidationError):
        AuthoritySnapshot(
            INSTALL, PROJECT, make_contract(status=ContractState.PROPOSED), 1, 5000, (), (), {},
            "hermes-issuer", "olympus-r4", (), (), {},
        )


def test_authority_snapshot_rejects_project_mismatch():
    other_owner = Principal("project-b", "hermes", "owner")
    other_worker = Principal("project-b", "hermes", "worker")
    contract = ExecutionContract(
        contract_id="contract-a", project_id="project-b", generation=0, owner=other_owner,
        participants=(other_owner, other_worker), objective="x", expected_outcome="y", included_scopes=("src/",),
        excluded_scopes=(), role_permissions={}, evidence_gates=(), side_effect_policy=SideEffectPolicy((), 1, True),
        limits=ContractLimits(1, 1, 1, 10, 1, 1), escalation_conditions=("ambiguity",), completion_authority=other_owner,
        amendment_authority=other_owner, status=ContractState.ACTIVE,
    )
    with pytest.raises(ValidationError):
        AuthoritySnapshot(
            INSTALL, PROJECT, contract, 1, 5000, (), (), {}, "hermes-issuer", "olympus-r4", (), (), {},
        )


@pytest.mark.parametrize("fence_epoch,fence_expires_at", [(0, 5000), (-1, 5000), (True, 5000), (1, 0), (1, True)])
def test_authority_snapshot_rejects_invalid_fence_fields(fence_epoch, fence_expires_at):
    with pytest.raises(ValidationError):
        AuthoritySnapshot(
            INSTALL, PROJECT, make_contract(), fence_epoch, fence_expires_at, (), (), {},
            "hermes-issuer", "olympus-r4", (), (), {},
        )


def test_authority_snapshot_is_frozen():
    snapshot = AuthoritySnapshot(
        INSTALL, PROJECT, make_contract(), 1, 5000, (), (), {}, "hermes-issuer", "olympus-r4", (), (), {},
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.fence_epoch = 2


# ---------------------------------------------------------------------------
# ReplayCache and AuthorizationResult
# ---------------------------------------------------------------------------

def test_replay_cache_consumes_once_and_prunes_expired_entries():
    clock = Clock(1000)
    cache = ReplayCache(clock=clock)
    assert cache.consume("key-a", expires_at=1500) is True
    assert cache.consume("key-a", expires_at=1500) is False
    clock.value = 1500
    assert cache.consume("key-a", expires_at=2000) is True


def test_authorization_result_requires_reason_iff_denied():
    with pytest.raises(ValidationError):
        AuthorizationResult(False, None)
    with pytest.raises(ValidationError):
        AuthorizationResult(True, AuthorizationDenial.EXPIRED)
    with pytest.raises(ValidationError):
        AuthorizationResult(1, None)
    assert AuthorizationResult(True, None).granted is True
    assert AuthorizationResult(False, AuthorizationDenial.EXPIRED).granted is False


# ---------------------------------------------------------------------------
# authorize(): valid path
# ---------------------------------------------------------------------------

def test_authorize_grants_on_the_valid_path():
    registry = make_registry()
    result = call_authorize(build_scenario(registry))
    assert result.granted is True
    assert result.reason is None


def test_authorize_grants_with_matching_requested_effect_class():
    registry = make_registry()
    scenario = build_scenario(registry, effect_classes=("filesystem",))
    result = call_authorize(scenario, request_effect_class="filesystem")
    assert result.granted is True


# ---------------------------------------------------------------------------
# authorize(): identity/key lifecycle
# ---------------------------------------------------------------------------

def test_authorize_denies_revoked_identity():
    registry = make_registry()
    scenario = build_scenario(registry)
    registry.revoke_identity("identity-a")
    result = call_authorize(scenario)
    assert result.granted is False and result.reason == AuthorizationDenial.REVOKED


def test_authorize_denies_revoked_issuer_key():
    registry = make_registry()
    scenario = build_scenario(registry)
    registry.revoke_key("issuer-key-1")
    result = call_authorize(scenario)
    assert result.granted is False and result.reason == AuthorizationDenial.UNKNOWN_KEY


def test_authorize_denies_old_key_after_rotation():
    registry = make_registry()
    scenario = build_scenario(registry)
    registry.rotate_key("issuer-key-1", "issuer-key-2", b"rotated-secret-key-material-0001", ttl=10_000)
    result = call_authorize(scenario)
    assert result.granted is False and result.reason == AuthorizationDenial.UNKNOWN_KEY


def test_authorize_denies_revoked_holder_key():
    registry = make_registry()
    scenario = build_scenario(registry)
    registry.revoke_key("holder-key-1")
    result = call_authorize(scenario)
    assert result.granted is False and result.reason == AuthorizationDenial.UNKNOWN_KEY


# ---------------------------------------------------------------------------
# authorize(): validity windows
# ---------------------------------------------------------------------------

def test_authorize_denies_not_yet_valid_and_expired_credential():
    registry = make_registry()
    early = call_authorize(build_scenario(registry, credential_not_before=2000, credential_expires_at=3000, now=1000))
    assert early.granted is False and early.reason == AuthorizationDenial.NOT_YET_VALID
    late = call_authorize(build_scenario(make_registry(), credential_not_before=1000, credential_expires_at=2000, now=2000))
    assert late.granted is False and late.reason == AuthorizationDenial.EXPIRED


def test_authorize_denies_not_yet_valid_and_expired_capability_claim():
    registry = make_registry()
    early = call_authorize(build_scenario(registry, claim_not_before=2000, claim_expires_at=3000, now=1000))
    assert early.granted is False and early.reason == AuthorizationDenial.NOT_YET_VALID
    late = call_authorize(build_scenario(make_registry(), claim_not_before=1000, claim_expires_at=2000, now=2000))
    assert late.granted is False and late.reason == AuthorizationDenial.EXPIRED


# ---------------------------------------------------------------------------
# authorize(): contract generation / revocation epoch / fence liveness
# ---------------------------------------------------------------------------

def test_authorize_denies_lower_and_higher_generation():
    low = call_authorize(build_scenario(make_registry(), generation=5, claim_generation=4))
    assert low.granted is False and low.reason == AuthorizationDenial.STALE_AUTHORITY
    high = call_authorize(build_scenario(make_registry(), generation=5, claim_generation=6))
    assert high.granted is False and high.reason == AuthorizationDenial.STALE_AUTHORITY


def test_authorize_denies_stale_contract_revocation_epoch():
    result = call_authorize(build_scenario(make_registry(), contract_revocation_epoch=2, claim_revocation_epoch=1))
    assert result.granted is False and result.reason == AuthorizationDenial.STALE_AUTHORITY


def test_authorize_denies_stale_fence_epoch():
    result = call_authorize(build_scenario(make_registry(), fence_epoch=3, claim_fence_epoch=2))
    assert result.granted is False and result.reason == AuthorizationDenial.STALE_AUTHORITY


def test_authorize_denies_expired_lease_snapshot():
    result = call_authorize(build_scenario(make_registry(), fence_expires_at=1000, now=1000))
    assert result.granted is False and result.reason == AuthorizationDenial.STALE_AUTHORITY


def test_authorize_denies_wrong_contract_id():
    registry = make_registry()
    tampered = retarget(registry, build_scenario(registry), contract_id="contract-b")
    result = call_authorize(tampered)
    assert result.granted is False and result.reason == AuthorizationDenial.STALE_AUTHORITY


# ---------------------------------------------------------------------------
# authorize(): binding exactness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("installation_id", "install-b"), ("project_id", "project-b"), ("role", "owner"),
    ("profile", "other-profile"), ("session_id", "session-b"), ("runtime_id", "runtime-b"),
])
def test_authorize_denies_wrong_request_binding_field(field, value):
    registry = make_registry()
    scenario = build_scenario(registry)
    tampered_binding = replace(scenario["request_binding"], **{field: value})
    result = call_authorize({**scenario, "request_binding": tampered_binding})
    assert result.granted is False and result.reason == AuthorizationDenial.BINDING_MISMATCH


def test_authorize_denies_wrong_installation_or_project_in_claim():
    registry = make_registry()
    scenario = build_scenario(registry)
    wrong_install = call_authorize(retarget(registry, scenario, installation_id="install-b"))
    assert wrong_install.granted is False and wrong_install.reason == AuthorizationDenial.BINDING_MISMATCH
    wrong_project = call_authorize(retarget(registry, scenario, project_id="project-b"))
    assert wrong_project.granted is False and wrong_project.reason == AuthorizationDenial.BINDING_MISMATCH


def test_authorize_denies_wrong_audience():
    registry = make_registry()
    scenario = build_scenario(registry)
    tampered = retarget(registry, scenario, audience="other-audience")
    result = call_authorize(tampered)
    assert result.granted is False and result.reason == AuthorizationDenial.BINDING_MISMATCH
    result2 = call_authorize(scenario, audience="other-audience")
    assert result2.granted is False and result2.reason == AuthorizationDenial.BINDING_MISMATCH


def test_authorize_denies_cross_issuer_credential_capability_pair():
    registry = make_registry()
    scenario = build_scenario(registry)
    other_capability = issue_capability(registry, scenario["capability"].claim, issuer="different-issuer", key_id="issuer-key-1")
    result = call_authorize({**scenario, "capability": other_capability})
    assert result.granted is False and result.reason == AuthorizationDenial.BINDING_MISMATCH


def test_authorize_denies_principal_not_in_contract_participants():
    registry = make_registry()
    intruder = Principal(PROJECT, "hermes", "intruder")
    scenario = build_scenario(registry, principal=intruder, binding=replace(BINDING, role="intruder"))
    result = call_authorize(scenario)
    assert result.granted is False and result.reason == AuthorizationDenial.BINDING_MISMATCH


# ---------------------------------------------------------------------------
# authorize(): target / permission / effect exactness and layered ceilings
# ---------------------------------------------------------------------------

def test_authorize_denies_target_prefix_or_substring_not_exact():
    registry = make_registry()
    scenario = build_scenario(registry, target="repo/file.py")
    longer = call_authorize(scenario, request_target="repo/file.py.bak")
    assert longer.granted is False and longer.reason == AuthorizationDenial.PERMISSION_DENIED
    shorter = call_authorize(scenario, request_target="repo/file")
    assert shorter.granted is False and shorter.reason == AuthorizationDenial.PERMISSION_DENIED


def test_authorize_denies_requested_effect_class_outside_claim():
    registry = make_registry()
    scenario = build_scenario(registry, effect_classes=("filesystem",))
    result = call_authorize(scenario, request_effect_class="network")
    assert result.granted is False and result.reason == AuthorizationDenial.PERMISSION_DENIED


def test_authorize_denies_unknown_task_grant():
    registry = make_registry()
    scenario = build_scenario(registry, task_id="task-b", task_grants={"task-a": ("read_files",)})
    result = call_authorize(scenario)
    assert result.granted is False and result.reason == AuthorizationDenial.PERMISSION_DENIED


@pytest.mark.parametrize("layer", ["issuer_ceiling", "project_ceiling", "task_grant", "claim_permissions", "role_permissions"])
def test_authorize_denies_permission_missing_from_any_single_intersection_layer(layer):
    registry = make_registry()
    kwargs = {}
    if layer == "issuer_ceiling":
        kwargs["issuer_ceiling"] = ("write_files",)
    elif layer == "project_ceiling":
        kwargs["project_ceiling"] = ("write_files",)
    elif layer == "task_grant":
        kwargs["task_grants"] = {"task-a": ("write_files",)}
    elif layer == "claim_permissions":
        kwargs["permissions"] = ("write_files",)
    elif layer == "role_permissions":
        kwargs["role_permissions"] = {"worker": ("write_files",)}
    result = call_authorize(build_scenario(registry, **kwargs))
    assert result.granted is False and result.reason == AuthorizationDenial.PERMISSION_DENIED


def test_authorize_grants_when_every_layer_permits_the_permission():
    result = call_authorize(build_scenario(make_registry()))
    assert result.granted is True


# ---------------------------------------------------------------------------
# authorize(): holder proof binding, copied bearer, replay protection
# ---------------------------------------------------------------------------

def test_authorize_denies_copied_capability_used_with_another_holder_key():
    registry = make_registry()
    scenario = build_scenario(registry)
    forged_proof = create_holder_proof(
        registry, "holder-key-2", challenge=digest("challenge-1"), subject_canonical=scenario["capability"].to_dict(),
        request_digest=REQUEST_DIGEST,
    )
    result = call_authorize({**scenario, "proof": forged_proof})
    assert result.granted is False and result.reason == AuthorizationDenial.BAD_PROOF


def test_authorize_denies_one_byte_altered_proof_signature():
    registry = make_registry()
    scenario = build_scenario(registry)
    proof = scenario["proof"]
    flipped = "0" if proof.signature[-1] != "0" else "1"
    tampered_proof = HolderProof(proof.holder_key_id, proof.challenge, proof.request_digest, proof.signature[:-1] + flipped)
    result = call_authorize({**scenario, "proof": tampered_proof})
    assert result.granted is False and result.reason == AuthorizationDenial.BAD_PROOF


def test_authorize_denies_altered_signed_claim_after_signing():
    registry = make_registry()
    scenario = build_scenario(registry)
    tampered_claim = replace(scenario["capability"].claim, target="repo/other.py")
    tampered_capability = SignedCapability(tampered_claim, scenario["capability"].issuer, scenario["capability"].key_id, scenario["capability"].signature)
    result = call_authorize({**scenario, "capability": tampered_capability})
    assert result.granted is False and result.reason == AuthorizationDenial.BAD_SIGNATURE


def test_authorize_denies_proof_reused_for_different_request_digest():
    registry = make_registry()
    scenario = build_scenario(registry)
    result = call_authorize(scenario, request_digest=digest("request-2"))
    assert result.granted is False and result.reason == AuthorizationDenial.BAD_PROOF


def test_authorize_denies_replay_of_same_proof_and_request():
    registry = make_registry()
    scenario = build_scenario(registry)
    cache = ReplayCache(clock=Clock(scenario["now"]))
    first = call_authorize(scenario, replay_cache=cache)
    second = call_authorize(scenario, replay_cache=cache)
    assert first.granted is True
    assert second.granted is False and second.reason == AuthorizationDenial.REPLAYED


def test_authorize_denial_does_not_consume_the_replay_cache():
    registry = make_registry()
    scenario = build_scenario(registry)
    cache = ReplayCache(clock=Clock(scenario["now"]))
    denied = call_authorize(scenario, replay_cache=cache, request_digest=digest("request-2"))
    assert denied.granted is False
    granted = call_authorize(scenario, replay_cache=cache)
    assert granted.granted is True


# ---------------------------------------------------------------------------
# authorize(): invalid input, free text cannot affect authority
# ---------------------------------------------------------------------------

def test_authorize_denies_invalid_input_types():
    registry = make_registry()
    scenario = build_scenario(registry)
    bad_principal = call_authorize({**scenario, "principal": "not-a-principal"})
    assert bad_principal.granted is False and bad_principal.reason == AuthorizationDenial.INVALID_INPUT
    bad_now = call_authorize(scenario, now=True)
    assert bad_now.granted is False and bad_now.reason == AuthorizationDenial.INVALID_INPUT
    bad_digest = call_authorize(scenario, request_digest="not-hex")
    assert bad_digest.granted is False and bad_digest.reason == AuthorizationDenial.INVALID_INPUT


def test_participant_card_and_free_text_cannot_affect_authority():
    registry = make_registry()
    scenario = build_scenario(registry)
    card = ParticipantCard(WORKER, "owner", "gpt-9", ("everything",), {"permission": "admin"})
    result = call_authorize(scenario, principal=card)
    assert result.granted is False and result.reason == AuthorizationDenial.INVALID_INPUT
    genuine = call_authorize(scenario)
    assert genuine.granted is True
    assert card.role == "owner"
