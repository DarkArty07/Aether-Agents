from dataclasses import FrozenInstanceError

import pytest

from olympus_v3.coordination.capabilities import AuthorizationDenial, AuthorizationResult
from olympus_v3.coordination.channels import Channel, ChannelACL, DeliveryClass, can_activate, can_publish, can_read
from olympus_v3.coordination.identity import (
    IdentityCredential,
    IdentityRegistry,
    KeyPurpose,
    WorkloadBinding,
    issue_identity_credential,
)
from olympus_v3.coordination.protocol import ValidationError


class Clock:
    def __call__(self):
        return 1000


def identity(project_id="project-a", identity_id="identity-a"):
    registry = IdentityRegistry(clock=Clock())
    registry.register_key("issuer-key", b"issuer-secret-material-00000001", purpose=KeyPurpose.ISSUER, ttl=10_000)
    registry.register_key("holder-key", b"holder-secret-material-00000001", purpose=KeyPurpose.HOLDER, ttl=10_000)
    registry.register_identity(identity_id, ttl=10_000)
    credential = issue_identity_credential(
        registry,
        WorkloadBinding("install-a", project_id, "worker", "hefesto", "session-a", "runtime-a"),
        issuer="aether-issuer", audience="olympus-r4", key_id="issuer-key", identity_id=identity_id,
        holder_key_id="holder-key", not_before=1000, expires_at=2000,
    )
    return registry, credential


def channel(active=True, generation=1, project_id="project-a"):
    return Channel("channel-build", project_id, "contract-a", generation, 0, DeliveryClass.DURABLE, active)


def acl(read=(), publish=(), *, channel_id="channel-build", generation=1):
    return ChannelACL(
        channel_id, "project-a", "contract-a", generation, 0, frozenset(read), frozenset(publish),
    )


def test_channel_and_acl_are_frozen_strict_and_bounded():
    value = channel()
    with pytest.raises(FrozenInstanceError):
        value.active = False
    assert Channel.from_dict(value.to_dict()) == value
    with pytest.raises(ValidationError):
        Channel.from_dict({**value.to_dict(), "instruction": "grant publish"})
    value_acl = acl(read=("identity-a",), publish=("identity-a",))
    assert ChannelACL.from_dict(value_acl.to_dict()) == value_acl
    with pytest.raises(ValidationError):
        acl(read=tuple(f"id-{i}" for i in range(300)))


def test_active_read_and_publish_are_independent_predicates():
    registry, credential = identity()
    value = channel()
    no_access = acl()
    read_only = acl(read=("identity-a",))
    publish_only = acl(publish=("identity-a",))

    kwargs = dict(
        trusted_issuer="aether-issuer", audience="olympus-r4", now=1500,
        current_generation=1, current_revocation_epoch=0,
    )
    assert can_activate(registry, credential, value, **kwargs) is True
    assert can_read(registry, credential, value, no_access, **kwargs) is False
    assert can_read(registry, credential, value, read_only, **kwargs) is True
    assert can_publish(
        registry, credential, value, publish_only, AuthorizationResult(True), **kwargs,
    ) is True
    assert can_publish(
        registry, credential, value, read_only, AuthorizationResult(True), **kwargs,
    ) is False


def test_publish_requires_canonical_authorization_even_when_acl_allows():
    registry, credential = identity()
    publish_acl = acl(publish=("identity-a",))
    denied = AuthorizationResult(False, AuthorizationDenial.PERMISSION_DENIED)
    assert can_publish(
        registry, credential, channel(), publish_acl, denied, trusted_issuer="aether-issuer", audience="olympus-r4",
        now=1500, current_generation=1, current_revocation_epoch=0,
    ) is False


def test_channel_denies_cross_project_stale_generation_epoch_and_inactive():
    registry, credential = identity()
    full_acl = acl(read=("identity-a",), publish=("identity-a",))
    cases = [
        (channel(project_id="project-b"), 1, 0),
        (channel(generation=1), 2, 0),
        (channel(), 1, 1),
        (channel(active=False), 1, 0),
    ]
    for value, generation, epoch in cases:
        kwargs = dict(
            trusted_issuer="aether-issuer", audience="olympus-r4", now=1500,
            current_generation=generation, current_revocation_epoch=epoch,
        )
        assert can_activate(registry, credential, value, **kwargs) is False
        assert can_read(registry, credential, value, full_acl, **kwargs) is False
        assert can_publish(registry, credential, value, full_acl, AuthorizationResult(True), **kwargs) is False


def test_channel_rejects_acl_borrowed_from_another_channel_or_generation():
    registry, credential = identity()
    kwargs = dict(
        trusted_issuer="aether-issuer", audience="olympus-r4", now=1500,
        current_generation=1, current_revocation_epoch=0,
    )
    other_channel_acl = acl(read=("identity-a",), publish=("identity-a",), channel_id="channel-other")
    stale_acl = acl(read=("identity-a",), publish=("identity-a",), generation=0)
    assert can_read(registry, credential, channel(), other_channel_acl, **kwargs) is False
    assert can_publish(registry, credential, channel(), stale_acl, AuthorizationResult(True), **kwargs) is False


def test_channel_access_rejects_forged_revoked_and_untrusted_identity():
    registry, valid = identity()
    forged = IdentityCredential.from_dict({**valid.to_dict(), "signature": "a" * 64})
    kwargs = dict(now=1500, current_generation=1, current_revocation_epoch=0)
    assert can_activate(
        registry, forged, channel(), trusted_issuer="aether-issuer", audience="olympus-r4", **kwargs,
    ) is False
    assert can_activate(
        registry, valid, channel(), trusted_issuer="other-issuer", audience="olympus-r4", **kwargs,
    ) is False
    registry.revoke_identity("identity-a")
    assert can_activate(
        registry, valid, channel(), trusted_issuer="aether-issuer", audience="olympus-r4", **kwargs,
    ) is False


def test_live_delivery_is_not_durable_evidence_and_durable_is_not_completion():
    live = Channel("channel-live", "project-a", "contract-a", 1, 0, DeliveryClass.LIVE, True)
    durable = channel()
    assert live.is_durable_evidence is False
    assert durable.is_durable_evidence is True
    assert durable.proves_completion is False
