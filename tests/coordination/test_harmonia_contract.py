from __future__ import annotations

from pathlib import Path

import pytest

from olympus_v3.coordination.harmonia_contract import (
    HARMONIA_ERROR_CODES,
    HarmoniaGenesisSpec,
    HarmoniaStartRequest,
    HarmoniaStatusRequest,
    HarmoniaStopRequest,
    InvalidHarmoniaRequest,
    parse_harmonia_request,
    public_error,
)


def _genesis(**overrides):
    value = {
        "worker": "hefesto",
        "objective": "Implement one bounded task",
        "expected_outcome": "Focused tests pass",
        "included_scopes": ["src/olympus_v3/coordination"],
        "excluded_scopes": ["home/config.yaml"],
        "worker_permissions": ["read", "write"],
        "time_seconds": 600,
        "model_budget": 100,
        "qa_reserve": 1,
        "recovery_reserve": 1,
        "escalation_conditions": ["ambiguity"],
    }
    value.update(overrides)
    return value


def _start(project_root: Path, **overrides):
    value = {
        "action": "start",
        "project_root": str(project_root),
        "request_id": "slice-1",
        "contract": _genesis(),
        "plan_revision": 1,
        "snapshot_digest": "sha256:" + "a" * 64,
    }
    value.update(overrides)
    return value


def test_start_request_round_trips_only_caller_authorized_fields(tmp_path):
    request = parse_harmonia_request(_start(tmp_path))

    assert isinstance(request, HarmoniaStartRequest)
    assert isinstance(request.contract, HarmoniaGenesisSpec)
    assert request.project_root == tmp_path.resolve()
    assert request.to_dict() == _start(tmp_path)
    assert not {
        "project_id",
        "contract_id",
        "run_id",
        "task_id",
        "session_id",
        "writer_id",
        "key_id",
        "runtime_authority",
        "generation",
        "revocation_epoch",
        "status",
        "side_effect_policy",
        "completion_authority",
        "amendment_authority",
    } & set(request.contract.to_dict())


def test_status_and_stop_have_strict_action_specific_shapes(tmp_path):
    run_id = "run-" + "b" * 32

    status = parse_harmonia_request({"action": "status", "project_root": str(tmp_path), "run_id": run_id})
    stop = parse_harmonia_request(
        {"action": "stop", "project_root": str(tmp_path), "run_id": run_id, "reason": "operator request"}
    )

    assert isinstance(status, HarmoniaStatusRequest)
    assert status.to_dict() == {"action": "status", "project_root": str(tmp_path.resolve()), "run_id": run_id}
    assert isinstance(stop, HarmoniaStopRequest)
    assert stop.to_dict() == {
        "action": "stop",
        "project_root": str(tmp_path.resolve()),
        "run_id": run_id,
        "reason": "operator request",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"action": "unknown", "project_root": "/tmp"},
        {"action": "status", "project_root": "/tmp", "run_id": "run-" + "a" * 32, "reason": "wrong"},
        {"action": "stop", "project_root": "/tmp", "run_id": "run-" + "a" * 32, "contract": {}},
        {"action": "start", "project_root": "/tmp", "request_id": "x", "contract": {}, "plan_revision": 1, "snapshot_digest": "sha256:" + "a" * 64, "unknown": True},
    ],
)
def test_unknown_actions_fields_and_action_incompatible_fields_fail_closed(payload):
    with pytest.raises(InvalidHarmoniaRequest, match="invalid request"):
        parse_harmonia_request(payload)


@pytest.mark.parametrize(
    "forbidden",
    [
        "project_id",
        "contract_id",
        "run_id",
        "task_id",
        "session_id",
        "writer_id",
        "key_id",
        "runtime_authority",
        "generation",
        "revocation_epoch",
        "status",
        "concurrency",
        "retries",
        "evidence_gates",
        "side_effect_policy",
        "completion_authority",
        "amendment_authority",
    ],
)
def test_genesis_rejects_caller_asserted_authority_fields(tmp_path, forbidden):
    contract = _genesis(**{forbidden: "caller-controlled"})

    with pytest.raises(InvalidHarmoniaRequest, match="invalid request"):
        parse_harmonia_request(_start(tmp_path, contract=contract))


@pytest.mark.parametrize("worker", ["Hermes", "hermes", "harmonia", "athena", "unknown worker", ""])
def test_genesis_rejects_invalid_or_suspended_worker_identifiers(tmp_path, worker):
    with pytest.raises(InvalidHarmoniaRequest, match="invalid request"):
        parse_harmonia_request(_start(tmp_path, contract=_genesis(worker=worker)))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("included_scopes", []),
        ("included_scopes", ["same", "same"]),
        ("worker_permissions", []),
        ("worker_permissions", ["read", "read"]),
        ("time_seconds", 0),
        ("time_seconds", True),
        ("model_budget", 1),
        ("qa_reserve", 0),
        ("recovery_reserve", 0),
        ("escalation_conditions", "ambiguity"),
    ],
)
def test_genesis_rejects_malformed_scopes_permissions_and_limits(tmp_path, field, value):
    with pytest.raises(InvalidHarmoniaRequest, match="invalid request"):
        parse_harmonia_request(_start(tmp_path, contract=_genesis(**{field: value})))


@pytest.mark.parametrize(
    "overrides",
    [
        {"project_root": "relative/path"},
        {"project_root": "/definitely/not/a/real/harmonia/project"},
        {"request_id": "Uppercase"},
        {"request_id": "bad id"},
        {"plan_revision": 0},
        {"plan_revision": True},
        {"snapshot_digest": "sha256:ABC"},
        {"snapshot_digest": "md5:" + "a" * 32},
        {"snapshot_digest": "sha256:" + "a" * 63},
    ],
)
def test_start_rejects_malformed_identity_revision_digest_and_root(tmp_path, overrides):
    payload = _start(tmp_path)
    payload.update(overrides)
    with pytest.raises(InvalidHarmoniaRequest, match="invalid request"):
        parse_harmonia_request(payload)


@pytest.mark.parametrize("run_id", ["task-" + "a" * 32, "run-short", "run-" + "A" * 32, "run-" + "a" * 33])
def test_status_rejects_malformed_run_ids(tmp_path, run_id):
    with pytest.raises(InvalidHarmoniaRequest, match="invalid request"):
        parse_harmonia_request({"action": "status", "project_root": str(tmp_path), "run_id": run_id})


def test_public_error_is_stable_and_does_not_echo_internal_detail():
    error = public_error("start", "storage_unavailable", retryable=True)

    assert set(HARMONIA_ERROR_CODES) == {
        "feature_disabled",
        "invalid_request",
        "project_not_allowed",
        "key_provider_unavailable",
        "storage_unavailable",
        "schema_incompatible",
        "contract_conflict",
        "idempotency_conflict",
        "admission_limit",
        "not_found",
        "authority_mismatch",
        "external_unknown",
        "internal_failure",
    }
    assert error == {
        "action": "start",
        "ok": False,
        "runtime_authority": "kernel",
        "durable": False,
        "state": None,
        "uncertainty": None,
        "error": {
            "code": "storage_unavailable",
            "message": "Coordination storage is unavailable.",
            "retryable": True,
        },
    }
    with pytest.raises(ValueError, match="unknown public error code"):
        public_error("start", "sqlite said /secret/path")
