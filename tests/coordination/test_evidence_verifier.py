from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aether_agents.evidence import (
    ARTIFACT_RELATIVE_PATH,
    EvidenceIdentity,
    EvidenceVerificationError,
    build_evidence_receipt,
    materialize_captured_result,
    validate_evidence_receipt_payload,
    verify_artifact,
)

FIELDS = (
    "installation_id",
    "project_id",
    "run_id",
    "task_id",
    "attempt",
    "contract_id",
    "contract_generation",
    "revocation_epoch",
    "message_id",
    "logical_session",
    "acp_session_id",
)


def identity(**overrides):
    value = dict(
        installation_id="install-1",
        project_id="project-1",
        run_id="run-1",
        task_id="task-1",
        attempt=1,
        contract_id="contract-1",
        contract_generation=1,
        revocation_epoch=0,
        message_id="message-1",
        logical_session="logical-1",
        acp_session_id="acp-1",
    )
    value.update(overrides)
    return EvidenceIdentity(**value)


def artifact(identity_value=None, **overrides):
    item = identity_value or identity()
    value = {field: getattr(item, field) for field in FIELDS}
    value.update(
        {
            "schema": "AETHER_TASK_RESULT_V1",
            "artifact_generation": 1,
            "result": {"terminal_status": "completed", "answer": "ok"},
        }
    )
    value.update(overrides)
    return value


def write_artifact(root: Path, payload: bytes) -> None:
    path = root / ARTIFACT_RELATIVE_PATH.format(run_id="run-1", task_id="task-1", attempt=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_json(root: Path, value: dict) -> None:
    write_artifact(root, json.dumps(value, ensure_ascii=False).encode())


def test_valid_artifact_verifies_and_receipt_is_deterministic(tmp_path):
    write_json(tmp_path, artifact())
    verified = verify_artifact(tmp_path, identity())
    receipt = build_evidence_receipt(identity(), verified, "completed")
    again = build_evidence_receipt(identity(), verify_artifact(tmp_path, identity()), "completed")
    assert verified.schema == "AETHER_TASK_RESULT_V1"
    assert verified.generation == 1
    assert verified.relative_path == " .aether/evidence/run-1/task-1/1/result.json".strip()
    assert verified.digest.startswith("sha256:") and len(verified.digest) == 71
    assert receipt == again
    assert receipt.identity == "kernel.artifact-verifier"
    assert receipt.version == 1
    assert receipt.algorithm == "sha256-canonical-json"
    assert receipt.schema == "AETHER_EVIDENCE_RECEIPT_V1"


def test_kernel_materializes_captured_result_atomically_and_idempotently(tmp_path):
    expected = identity()
    first = materialize_captured_result(tmp_path, expected, {"answer": "ok", "verified": True})
    second = materialize_captured_result(tmp_path, expected, {"answer": "ok", "verified": True})

    assert first == second
    assert dict(first.result) == {"answer": "ok", "verified": True}
    with pytest.raises(EvidenceVerificationError, match="stale_artifact"):
        materialize_captured_result(tmp_path, expected, {"answer": "conflict"})


def test_receipt_payload_is_flat_bounded_and_excludes_result(tmp_path):
    write_json(tmp_path, artifact(result={"answer": "large-result-stays-in-file"}))
    verified = verify_artifact(tmp_path, identity())
    receipt = build_evidence_receipt(identity(), verified, "completed")
    payload = receipt.event_payload()

    assert payload["contract_id"] == "contract-1"
    assert payload["acp_session_id"] == "acp-1"
    assert payload["terminal"] == {"technical_status": "completed"}
    assert "evidence_identity" not in payload
    assert "result" not in payload["artifact"]
    assert payload["receipt_id"] == receipt.receipt_id
    assert payload["receipt_payload_digest"] == receipt.receipt_payload_digest
    base = {key: value for key, value in payload.items() if key not in {"receipt_id", "receipt_payload_digest"}}
    canonical = json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert payload["receipt_payload_digest"] == "sha256:" + hashlib.sha256(canonical).hexdigest()
    assert payload["receipt_id"] == "receipt:" + hashlib.sha256(
        b"AETHER_EVIDENCE_RECEIPT_V1\0" + canonical
    ).hexdigest()
    validate_evidence_receipt_payload(payload)


@pytest.mark.parametrize(
    "mutation",
    ["digest", "receipt-id", "verifier", "bool-version", "bool-generation", "path", "extra", "result"],
)
def test_receipt_payload_validator_rejects_forged_or_extended_payload(tmp_path, mutation):
    write_json(tmp_path, artifact())
    receipt = build_evidence_receipt(identity(), verify_artifact(tmp_path, identity()), "completed")
    payload = receipt.event_payload()
    if mutation == "digest":
        payload["receipt_payload_digest"] = "sha256:" + "0" * 64
    elif mutation == "receipt-id":
        payload["receipt_id"] = "receipt:" + "0" * 64
    elif mutation == "verifier":
        payload["verifier"]["identity"] = "worker-claimed-verifier"
    elif mutation == "bool-version":
        payload["verifier"]["version"] = True
    elif mutation == "bool-generation":
        payload["artifact"]["generation"] = True
    elif mutation == "path":
        payload["artifact"]["relative_path"] = "caller/result.json"
    elif mutation == "extra":
        payload["extra"] = True
    else:
        payload["artifact"]["result"] = {"answer": "forged"}

    with pytest.raises(EvidenceVerificationError):
        validate_evidence_receipt_payload(payload)


def test_whitespace_and_key_order_do_not_change_digest(tmp_path):
    value = artifact()
    write_json(tmp_path, value)
    first = verify_artifact(tmp_path, identity()).digest
    ordered = {key: value[key] for key in reversed(list(value))}
    write_artifact(
        tmp_path,
        (
            " {\n"
            + ",\n".join(json.dumps(k) + ": " + json.dumps(v, ensure_ascii=False) for k, v in ordered.items())
            + "\n} "
        ).encode(),
    )
    assert verify_artifact(tmp_path, identity()).digest == first


@pytest.mark.parametrize(
    "case", ["missing", "directory", "oversize", "utf8", "malformed", "duplicate", "nonfinite", "deep"]
)
def test_invalid_artifacts_have_typed_nonleaking_errors(tmp_path, case):
    path = tmp_path / ".aether/evidence/run-1/task-1/1/result.json"
    if case == "missing":
        pass
    elif case == "directory":
        path.mkdir(parents=True)
    else:
        path.parent.mkdir(parents=True)
        data = json.dumps(artifact()).encode()
        if case == "oversize":
            data = b"x" * 65537
        if case == "utf8":
            data = b"\xff"
        if case == "malformed":
            data = b"{"
        if case == "duplicate":
            data = b'{"schema":"AETHER_TASK_RESULT_V1","schema":"x"}'
        if case == "nonfinite":
            data = json.dumps(artifact(result={"x": float("nan")})).encode()
        if case == "deep":
            data = json.dumps(
                artifact(result={"x": [[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]})
            ).encode()
        path.write_bytes(data)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code
    assert str(tmp_path) not in str(exc.value)
    assert "result.json" not in str(exc.value)
    assert "terminal_status" not in str(exc.value)


def test_extreme_nesting_fails_closed_without_recursion_leak(tmp_path):
    value = json.dumps(artifact(result={}), separators=(",", ":"))
    value = value.replace('"result":{}', '"result":{"x":' + "[" * 1100 + "0" + "]" * 1100 + "}")
    write_artifact(tmp_path, value.encode())

    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())

    assert exc.value.code == "artifact_invalid"


def test_unknown_or_missing_top_level_key_is_invalid(tmp_path):
    value = artifact()
    value.pop("message_id")
    value["extra"] = 1
    write_json(tmp_path, value)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "artifact_invalid"


@pytest.mark.parametrize("field", FIELDS)
def test_each_identity_field_mismatch_is_rejected(tmp_path, field):
    value = artifact()
    value[field] = "wrong" if field not in {"attempt", "contract_generation", "revocation_epoch"} else 9
    write_json(tmp_path, value)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "artifact_mismatch"


@pytest.mark.parametrize("field", ["attempt", "contract_generation", "revocation_epoch", "artifact_generation"])
def test_booleans_are_not_integers(tmp_path, field):
    value = artifact()
    value[field] = True
    write_json(tmp_path, value)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "artifact_invalid"


def test_generation_other_than_one_is_stale(tmp_path):
    value = artifact()
    value["artifact_generation"] = 2
    write_json(tmp_path, value)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "stale_artifact"


def test_result_is_arbitrary_and_deeply_immutable(tmp_path):
    value = artifact(result={"answer": {"items": [1, 2, 3]}})
    write_json(tmp_path, value)

    verified = verify_artifact(tmp_path, identity())

    assert verified.result["answer"]["items"] == (1, 2, 3)
    with pytest.raises(TypeError):
        verified.result["answer"]["items"][0] = 9
    with pytest.raises(TypeError):
        verified.result["answer"]["new"] = "mutable"


def test_terminal_status_is_validated_by_receipt_not_worker_result(tmp_path):
    value = artifact(result={"answer": "ok"})
    write_json(tmp_path, value)
    verified = verify_artifact(tmp_path, identity())

    with pytest.raises(EvidenceVerificationError) as exc:
        build_evidence_receipt(identity(), verified, "running")
    assert exc.value.code == "invalid_terminal_status"

    value = artifact(result=[])
    write_json(tmp_path, value)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "artifact_invalid"


def test_receipt_rejects_artifact_verified_for_different_identity(tmp_path):
    write_json(tmp_path, artifact())
    verified = verify_artifact(tmp_path, identity())

    with pytest.raises(EvidenceVerificationError) as exc:
        build_evidence_receipt(identity(contract_id="contract-2"), verified, "completed")

    assert exc.value.code == "artifact_mismatch"


def test_verifier_reads_from_nofollow_descriptor_not_reopened_path(tmp_path, monkeypatch):
    write_json(tmp_path, artifact())

    def reject_path_read(_path):
        raise AssertionError("path reopened after validation")

    monkeypatch.setattr(Path, "read_bytes", reject_path_read)
    assert verify_artifact(tmp_path, identity()).digest.startswith("sha256:")


def test_symlink_and_intermediate_escape_are_rejected(tmp_path):
    outside = tmp_path.parent / "outside-evidence"
    outside.mkdir(exist_ok=True)
    target = outside / "result.json"
    target.write_text(json.dumps(artifact()))
    path = tmp_path / ".aether/evidence/run-1/task-1/1/result.json"
    path.parent.mkdir(parents=True)
    path.symlink_to(target)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "artifact_escape"
    path.unlink()
    path.parent.rmdir()
    path.parent.parent.rmdir()
    path.parent.parent.parent.rmdir()
    outside_task = outside / "task-1"
    (outside_task / "1").mkdir(parents=True)
    (outside_task / "1/result.json").write_text(json.dumps(artifact()))
    intermediate = tmp_path / ".aether/evidence/run-1/task-1"
    intermediate.parent.mkdir(parents=True)
    intermediate.symlink_to(outside_task, target_is_directory=True)
    with pytest.raises(EvidenceVerificationError) as exc:
        verify_artifact(tmp_path, identity())
    assert exc.value.code == "artifact_escape"


def test_receipt_changes_for_status_or_result(tmp_path):
    write_json(tmp_path, artifact())
    ident = identity()
    first = verify_artifact(tmp_path, ident)
    completed = build_evidence_receipt(ident, first, "completed")
    cancelled = build_evidence_receipt(ident, first, "cancelled")
    changed = artifact(result={"terminal_status": "completed", "answer": "changed"})
    write_json(tmp_path, changed)
    changed_receipt = build_evidence_receipt(ident, verify_artifact(tmp_path, ident), "completed")
    assert completed.receipt_id != cancelled.receipt_id
    assert completed.receipt_payload_digest != changed_receipt.receipt_payload_digest


def test_only_kernel_derived_path_is_used(tmp_path):
    write_json(tmp_path, artifact())
    with pytest.raises(TypeError):
        verify_artifact(tmp_path, identity(), "/caller/selected.json")
