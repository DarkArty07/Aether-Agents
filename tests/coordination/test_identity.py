from dataclasses import FrozenInstanceError

import pytest

from olympus_v3.coordination.identity import (
    ALGORITHM,
    ENCODING_VERSION,
    HolderProof,
    IdentityCredential,
    IdentityRegistry,
    KeyPurpose,
    ValidationError,
    WorkloadBinding,
    create_holder_proof,
    issue_identity_credential,
    verify_holder_proof,
    verify_identity_credential,
)

BINDING = WorkloadBinding("install-a", "project-a", "worker", "hermes", "session-a", "runtime-a")
ISSUER_SECRET = b"issuer-secret-key-material-0001"
HOLDER_SECRET = b"holder-secret-key-material-0001"
OTHER_HOLDER_SECRET = b"other-holder-key-material-00001"


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


def clock_at(value):
    return Clock(value)


def make_registry(now=1000, *, key_ttl=10_000, identity_ttl=10_000, clock=None):
    registry = IdentityRegistry(clock=clock or clock_at(now))
    registry.register_key("issuer-key-1", ISSUER_SECRET, purpose=KeyPurpose.ISSUER, ttl=key_ttl)
    registry.register_key("holder-key-1", HOLDER_SECRET, purpose=KeyPurpose.HOLDER, ttl=key_ttl)
    registry.register_identity("identity-a", ttl=identity_ttl)
    return registry


def issue(registry, *, not_before=1000, expires_at=2000, binding=BINDING, key_id="issuer-key-1", holder_key_id="holder-key-1", identity_id="identity-a"):
    return issue_identity_credential(
        registry, binding, issuer="hermes-issuer", audience="olympus-r4", key_id=key_id,
        identity_id=identity_id, holder_key_id=holder_key_id, not_before=not_before, expires_at=expires_at,
    )


def test_workload_binding_is_frozen_and_round_trips_strictly():
    with pytest.raises(FrozenInstanceError):
        BINDING.role = "owner"
    assert WorkloadBinding.from_dict(BINDING.to_dict()) == BINDING
    with pytest.raises(ValidationError):
        WorkloadBinding.from_dict({**BINDING.to_dict(), "unknown": "x"})
    with pytest.raises(ValidationError):
        WorkloadBinding.from_dict({k: v for k, v in BINDING.to_dict().items() if k != "role"})


@pytest.mark.parametrize("field", ["installation_id", "project_id", "role", "profile", "session_id", "runtime_id"])
def test_workload_binding_rejects_malformed_fields(field):
    values = BINDING.to_dict()
    for bad in ("", " ", "UPPER", "has space", "x" * 200, None, 5, "-leading-dash"):
        values[field] = bad
        with pytest.raises(ValidationError):
            WorkloadBinding(**values)


def test_algorithm_and_encoding_are_fixed():
    assert ALGORITHM == "HMAC-SHA256"
    assert ENCODING_VERSION == 1


def test_identity_registry_key_lifecycle_ttl_and_rotation():
    clock = clock_at(1000)
    registry = make_registry(now=1000, key_ttl=500, clock=clock)
    assert registry.is_key_active("issuer-key-1", purpose=KeyPurpose.ISSUER)
    clock.value = 1499
    assert registry.is_key_active("issuer-key-1", purpose=KeyPurpose.ISSUER)
    clock.value = 1500
    assert not registry.is_key_active("issuer-key-1", purpose=KeyPurpose.ISSUER)
    assert not registry.is_key_active("unknown-key", purpose=KeyPurpose.ISSUER)

    registry2 = make_registry(now=1000)
    registry2.revoke_key("issuer-key-1")
    assert not registry2.is_key_active("issuer-key-1", purpose=KeyPurpose.ISSUER)
    with pytest.raises(ValidationError):
        registry2.revoke_key("nonexistent")

    registry3 = make_registry(now=1000)
    registry3.rotate_key("issuer-key-1", "issuer-key-2", b"new-secret-key-material-000001", ttl=1000)
    assert not registry3.is_key_active("issuer-key-1", purpose=KeyPurpose.ISSUER)
    assert registry3.is_key_active("issuer-key-2", purpose=KeyPurpose.ISSUER)


def test_identity_registry_identity_lifecycle_revocation_and_epoch():
    clock = clock_at(1000)
    registry = make_registry(now=1000, identity_ttl=500, clock=clock)
    assert registry.active_identity_epoch("identity-a") == 0
    clock.value = 1500
    assert registry.active_identity_epoch("identity-a") is None  # expired identity fails closed
    assert registry.active_identity_epoch("unknown-identity") is None

    registry2 = make_registry(now=1000)
    registry2.advance_identity_epoch("identity-a")
    assert registry2.active_identity_epoch("identity-a") == 1

    registry3 = make_registry(now=1000)
    registry3.revoke_identity("identity-a")
    assert registry3.active_identity_epoch("identity-a") is None
    with pytest.raises(ValidationError):
        registry3.revoke_identity("nonexistent")


@pytest.mark.parametrize("ttl", [0, -1, True, "10", 1.5, None])
def test_identity_registry_rejects_invalid_ttl_and_key_material(ttl):
    registry = IdentityRegistry(clock=clock_at(1000))
    with pytest.raises(ValidationError):
        registry.register_key("issuer-key-1", ISSUER_SECRET, purpose=KeyPurpose.ISSUER, ttl=ttl)
    with pytest.raises(ValidationError):
        registry.register_identity("identity-a", ttl=ttl)


@pytest.mark.parametrize("secret", [b"short", b"", "not-bytes", None, 12345])
def test_identity_registry_rejects_invalid_key_material(secret):
    registry = IdentityRegistry(clock=clock_at(1000))
    with pytest.raises(ValidationError):
        registry.register_key("issuer-key-1", secret, purpose=KeyPurpose.ISSUER, ttl=1000)


def test_identity_credential_issues_and_verifies_on_the_valid_path():
    registry = make_registry(now=1000)
    credential = issue(registry)
    assert isinstance(credential, IdentityCredential)
    assert verify_identity_credential(registry, credential, audience="olympus-r4", now=1500) is True
    assert credential.to_dict() == IdentityCredential.from_dict(credential.to_dict()).to_dict()
    with pytest.raises(FrozenInstanceError):
        credential.identity_id = "other"


def test_identity_credential_signature_material_never_serialized():
    registry = make_registry(now=1000)
    credential = issue(registry)
    blob = repr(credential.to_dict())
    assert ISSUER_SECRET.decode() not in blob
    assert HOLDER_SECRET.decode() not in blob


def test_identity_credential_strict_wire_schema_rejects_unknown_and_missing_fields():
    registry = make_registry(now=1000)
    credential = issue(registry)
    payload = credential.to_dict()
    with pytest.raises(ValidationError):
        IdentityCredential.from_dict({**payload, "unexpected": True})
    with pytest.raises(ValidationError):
        IdentityCredential.from_dict({k: v for k, v in payload.items() if k != "signature"})


def test_issue_identity_credential_fails_closed_for_unavailable_keys_and_identity():
    registry = make_registry(now=1000)
    with pytest.raises(ValidationError):
        issue(registry, key_id="unknown-issuer-key")
    with pytest.raises(ValidationError):
        issue(registry, holder_key_id="unknown-holder-key")
    with pytest.raises(ValidationError):
        issue(registry, identity_id="unknown-identity")

    revoked_registry = make_registry(now=1000)
    revoked_registry.revoke_key("issuer-key-1")
    with pytest.raises(ValidationError):
        issue(revoked_registry)


@pytest.mark.parametrize("not_before,expires_at,now,expected", [
    (1000, 2000, 999, False),   # not yet valid
    (1000, 2000, 2000, False),  # expired (half-open interval)
    (1000, 2000, 1999, True),
    (1000, 2000, 1000, True),
])
def test_verify_identity_credential_enforces_validity_window(not_before, expires_at, now, expected):
    registry = make_registry(now=1000)
    credential = issue(registry, not_before=not_before, expires_at=expires_at)
    assert verify_identity_credential(registry, credential, audience="olympus-r4", now=now) is expected


@pytest.mark.parametrize("now", [-1, True, 1.5, "1500", None])
def test_verify_identity_credential_rejects_bool_and_malformed_now(now):
    registry = make_registry(now=1000)
    credential = issue(registry)
    assert verify_identity_credential(registry, credential, audience="olympus-r4", now=now) is False


def test_verify_identity_credential_denies_wrong_audience():
    registry = make_registry(now=1000)
    credential = issue(registry)
    assert verify_identity_credential(registry, credential, audience="other-audience", now=1500) is False


def test_verify_identity_credential_denies_after_key_rotation_or_revocation():
    registry = make_registry(now=1000)
    credential = issue(registry)
    registry.rotate_key("issuer-key-1", "issuer-key-2", b"new-secret-key-material-000001", ttl=10_000)
    assert verify_identity_credential(registry, credential, audience="olympus-r4", now=1500) is False

    registry2 = make_registry(now=1000)
    credential2 = issue(registry2)
    registry2.revoke_key("holder-key-1")
    assert verify_identity_credential(registry2, credential2, audience="olympus-r4", now=1500) is False


def test_verify_identity_credential_denies_stale_and_revoked_identity_epoch():
    registry = make_registry(now=1000)
    credential = issue(registry)
    registry.advance_identity_epoch("identity-a")
    assert verify_identity_credential(registry, credential, audience="olympus-r4", now=1500) is False  # stale epoch

    registry2 = make_registry(now=1000)
    credential2 = issue(registry2)
    registry2.revoke_identity("identity-a")
    assert verify_identity_credential(registry2, credential2, audience="olympus-r4", now=1500) is False


def test_verify_identity_credential_denies_one_byte_altered_signature():
    registry = make_registry(now=1000)
    credential = issue(registry)
    flipped = "0" if credential.signature[-1] != "0" else "1"
    tampered = IdentityCredential.from_dict({**credential.to_dict(), "signature": credential.signature[:-1] + flipped})
    assert verify_identity_credential(registry, tampered, audience="olympus-r4", now=1500) is False


@pytest.mark.parametrize("bad_signature", ["", "not-hex", "a" * 63, "a" * 65, "A" * 64, "g" * 64])
def test_identity_credential_rejects_malformed_signature_shape(bad_signature):
    with pytest.raises(ValidationError):
        IdentityCredential(BINDING, "hermes-issuer", "olympus-r4", "issuer-key-1", "identity-a", "holder-key-1", 0, 1000, 2000, bad_signature)


@pytest.mark.parametrize("not_before,expires_at", [(-1, 2000), (True, 2000), (1000, True), (1000, 2**64), (2000, 1000), (1000, 1000)])
def test_identity_credential_rejects_negative_bool_overflow_and_inverted_time(not_before, expires_at):
    with pytest.raises(ValidationError):
        IdentityCredential(BINDING, "hermes-issuer", "olympus-r4", "issuer-key-1", "identity-a", "holder-key-1", 0, not_before, expires_at, "a" * 64)


@pytest.mark.parametrize("epoch", [-1, True, 2**64])
def test_identity_credential_rejects_negative_bool_and_overflow_revocation_epoch(epoch):
    with pytest.raises(ValidationError):
        IdentityCredential(BINDING, "hermes-issuer", "olympus-r4", "issuer-key-1", "identity-a", "holder-key-1", epoch, 1000, 2000, "a" * 64)


def test_holder_proof_round_trips_and_valid_path_verifies():
    registry = make_registry(now=1000)
    subject = {"example": "capability"}
    proof = create_holder_proof(registry, "holder-key-1", challenge="a" * 64, subject_canonical=subject, request_digest="b" * 64)
    assert isinstance(proof, HolderProof)
    assert HolderProof.from_dict(proof.to_dict()) == proof
    assert verify_holder_proof(registry, proof, expected_holder_key_id="holder-key-1", subject_canonical=subject, request_digest="b" * 64) is True


def test_holder_proof_denies_wrong_holder_key_copied_bearer():
    registry = make_registry(now=1000)
    registry.register_key("holder-key-2", OTHER_HOLDER_SECRET, purpose=KeyPurpose.HOLDER, ttl=10_000)
    subject = {"example": "capability"}
    proof = create_holder_proof(registry, "holder-key-2", challenge="a" * 64, subject_canonical=subject, request_digest="b" * 64)
    # A copied proof/credential without the bound holder key must not authorize.
    assert verify_holder_proof(registry, proof, expected_holder_key_id="holder-key-1", subject_canonical=subject, request_digest="b" * 64) is False


def test_holder_proof_binds_challenge_subject_and_request_digest():
    registry = make_registry(now=1000)
    subject = {"example": "capability"}
    proof = create_holder_proof(registry, "holder-key-1", challenge="a" * 64, subject_canonical=subject, request_digest="b" * 64)
    assert verify_holder_proof(registry, proof, expected_holder_key_id="holder-key-1", subject_canonical={"example": "different"}, request_digest="b" * 64) is False
    assert verify_holder_proof(registry, proof, expected_holder_key_id="holder-key-1", subject_canonical=subject, request_digest="c" * 64) is False


def test_holder_proof_denies_one_byte_altered_signature():
    registry = make_registry(now=1000)
    subject = {"example": "capability"}
    proof = create_holder_proof(registry, "holder-key-1", challenge="a" * 64, subject_canonical=subject, request_digest="b" * 64)
    flipped = "0" if proof.signature[-1] != "0" else "1"
    tampered = HolderProof(proof.holder_key_id, proof.challenge, proof.request_digest, proof.signature[:-1] + flipped)
    assert verify_holder_proof(registry, tampered, expected_holder_key_id="holder-key-1", subject_canonical=subject, request_digest="b" * 64) is False


@pytest.mark.parametrize("field,bad", [
    ("holder_key_id", ""), ("holder_key_id", "UPPER"),
    ("challenge", ""), ("challenge", "not-hex-and-too-short"), ("challenge", "a" * 65),
    ("request_digest", ""), ("request_digest", "g" * 64),
    ("signature", ""), ("signature", "a" * 63),
])
def test_holder_proof_rejects_malformed_or_oversized_fields(field, bad):
    values = {"holder_key_id": "holder-key-1", "challenge": "a" * 64, "request_digest": "b" * 64, "signature": "c" * 64}
    values[field] = bad
    with pytest.raises(ValidationError):
        HolderProof(**values)


def test_create_holder_proof_fails_closed_for_unknown_or_revoked_holder_key():
    registry = make_registry(now=1000)
    with pytest.raises(ValidationError):
        create_holder_proof(registry, "unknown-holder-key", challenge="a" * 64, subject_canonical={}, request_digest="b" * 64)
    registry.revoke_key("holder-key-1")
    with pytest.raises(ValidationError):
        create_holder_proof(registry, "holder-key-1", challenge="a" * 64, subject_canonical={}, request_digest="b" * 64)
