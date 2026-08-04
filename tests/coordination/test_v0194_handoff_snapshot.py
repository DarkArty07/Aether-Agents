from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from test_evidence_verifier import artifact, identity, write_json

from aether_agents.evidence import (
    EvidenceVerificationError,
    HandoffSnapshot,
    build_evidence_receipt,
    create_handoff_snapshot,
    validate_handoff_snapshot,
    verify_artifact,
)


def test_verified_artifact_has_immutable_digest_bound_handoff_snapshot(tmp_path: Path):
    write_json(tmp_path, artifact(result={"answer": "before"}))
    verified = verify_artifact(tmp_path, identity())
    receipt = build_evidence_receipt(identity(), verified, "completed")
    snapshot = create_handoff_snapshot(tmp_path, identity(), receipt.receipt_id, verified)

    assert isinstance(snapshot, HandoffSnapshot)
    assert snapshot.snapshot_relative_path.startswith(".aether/evidence/run-1/handoffs/task-1/")
    assert snapshot.source_receipt_id == receipt.receipt_id
    assert snapshot.snapshot_digest.startswith("sha256:")
    assert snapshot.canonical_size_bytes > 0
    validate_handoff_snapshot(tmp_path, snapshot)

    # The mutable source can change, but the published handoff remains the old bytes.
    write_json(tmp_path, artifact(result={"answer": "after"}))
    validate_handoff_snapshot(tmp_path, snapshot)
    assert json.loads((tmp_path / snapshot.snapshot_relative_path).read_bytes()) ["result"] == {"answer": "before"}


def test_snapshot_rejects_missing_replaced_out_of_root_wrong_size_and_digest(tmp_path: Path):
    write_json(tmp_path, artifact())
    verified = verify_artifact(tmp_path, identity())
    receipt = build_evidence_receipt(identity(), verified, "completed")
    snapshot = create_handoff_snapshot(tmp_path, identity(), receipt.receipt_id, verified)
    path = tmp_path / snapshot.snapshot_relative_path

    for mutation in ("missing", "replaced", "size", "digest", "out-of-root"):
        if mutation == "missing":
            path.unlink()
        elif mutation == "replaced":
            os.chmod(path, 0o644)
            path.write_bytes(b"{}")
        elif mutation == "size":
            validate_handoff_snapshot(tmp_path, snapshot)
            bad = replace(snapshot, canonical_size_bytes=snapshot.canonical_size_bytes + 1)
            with pytest.raises(EvidenceVerificationError):
                validate_handoff_snapshot(tmp_path, bad)
            continue
        elif mutation == "digest":
            bad = replace(snapshot, snapshot_digest="sha256:" + "0" * 64)
            with pytest.raises(EvidenceVerificationError):
                validate_handoff_snapshot(tmp_path, bad)
            continue
        else:
            bad = replace(snapshot, snapshot_relative_path="../outside.json")
            with pytest.raises(EvidenceVerificationError):
                validate_handoff_snapshot(tmp_path, bad)
            continue
        with pytest.raises(EvidenceVerificationError):
            validate_handoff_snapshot(tmp_path, snapshot)
        if not path.exists():
            create_handoff_snapshot(tmp_path, identity(), receipt.receipt_id, verified)
        else:
            path.write_bytes(verified.canonical_bytes)


def test_snapshot_exclusive_creation_rejects_conflict_but_converges_identical(tmp_path: Path):
    write_json(tmp_path, artifact())
    verified = verify_artifact(tmp_path, identity())
    receipt = build_evidence_receipt(identity(), verified, "completed")
    relative = f".aether/evidence/run-1/handoffs/task-1/{receipt.receipt_id}/{verified.digest[7:]}.json"
    planted = tmp_path / relative
    planted.parent.mkdir(parents=True)
    planted.write_bytes(b"conflict")
    with pytest.raises(EvidenceVerificationError):
        create_handoff_snapshot(tmp_path, identity(), receipt.receipt_id, verified)
    planted.write_bytes(verified.canonical_bytes)
    converged = create_handoff_snapshot(tmp_path, identity(), receipt.receipt_id, verified)
    assert converged.snapshot_digest == snapshot_digest(verified)


def test_snapshot_rejects_symlinked_parent_before_writing_any_bytes(tmp_path: Path):
    write_json(tmp_path, artifact())
    verified = verify_artifact(tmp_path, identity())
    receipt = build_evidence_receipt(identity(), verified, "completed")
    handoffs_root = tmp_path / ".aether/evidence/run-1/handoffs"
    redirected = tmp_path / ".aether/redirected"
    redirected.mkdir(parents=True)
    handoffs_root.parent.mkdir(parents=True, exist_ok=True)
    handoffs_root.symlink_to(redirected, target_is_directory=True)

    with pytest.raises(EvidenceVerificationError):
        create_handoff_snapshot(tmp_path, identity(), receipt.receipt_id, verified)

    assert list(redirected.rglob("*")) == []


def snapshot_digest(verified):
    return verified.digest


def test_receipt_and_release_metadata_is_bounded_and_exactly_shared(tmp_path: Path):
    write_json(tmp_path, artifact())
    verified = verify_artifact(tmp_path, identity())
    preliminary = build_evidence_receipt(identity(), verified, "completed")
    handoff = create_handoff_snapshot(tmp_path, identity(), preliminary.receipt_id, verified)
    receipt = build_evidence_receipt(identity(), verified, "completed", handoff)
    payload = receipt.event_payload()
    assert "result" not in payload
    assert set(payload["handoff"]) == {
        "source_run_id", "source_task_id", "source_attempt", "source_receipt_id",
        "source_artifact_generation", "snapshot_relative_path", "snapshot_digest", "canonical_size_bytes",
    }
    validate_handoff_snapshot(tmp_path, HandoffSnapshot.from_dict(payload["handoff"]))
