"""M2.5 protected content, privacy, quota, and integrity tests."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from aether_mcp.content_store import ContentError, ProtectedContentStore, StaticKeyProvider


def _project() -> str:
    return str(uuid.uuid4())


def _store(tmp_path: Path, *, quota: int = 1_000_000) -> tuple[ProtectedContentStore, StaticKeyProvider]:
    provider = StaticKeyProvider({})
    store = ProtectedContentStore(tmp_path / "content", key_provider=provider, quota_bytes=quota)
    return store, provider


def test_full_capture_requires_explicit_key_and_disabled_capture_persists_nothing(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    project_id = _project()

    for policy in ("DISABLED", "STRUCTURED_ONLY", "FULL_EPISODE"):
        with pytest.raises(ContentError) as captured:
            store.put(project_id=project_id, content_type="model_visible_text", payload=b"hello", capture_policy=policy)
        assert captured.value.code == "CAPTURE_DISABLED"
    assert list((tmp_path / "content").rglob("*.blob")) == []


def test_secret_redaction_happens_before_authenticated_encryption(tmp_path: Path) -> None:
    store, keys = _store(tmp_path)
    project_id = _project()
    keys.set_key(project_id, os.urandom(32))
    secret = "ghp_" + "a" * 36

    reference = store.put(
        project_id=project_id,
        content_type="model_visible_text",
        payload=f"token={secret}; Authorization: Bearer {'abc' + '.def' + '.ghi'}".encode(),
        capture_policy="FULL_EPISODE",
        secret_values=(secret,),
    )

    raw = reference.path.read_bytes()
    assert secret.encode() not in raw
    assert b"abc" + b".def" + b".ghi" not in raw
    plaintext = store.get(project_id=project_id, content_ref=reference.content_ref)
    assert secret.encode() not in plaintext
    assert b"[REDACTED]" in plaintext
    assert reference.path.stat().st_mode & 0o077 == 0


def test_duplicate_content_is_project_scoped_and_nonce_unique(tmp_path: Path) -> None:
    store, keys = _store(tmp_path)
    first_project = _project()
    second_project = _project()
    keys.set_key(first_project, os.urandom(32))
    keys.set_key(second_project, os.urandom(32))

    first = store.put(project_id=first_project, content_type="model_visible_text", payload=b"same", capture_policy="FULL_EPISODE")
    repeated = store.put(project_id=first_project, content_type="model_visible_text", payload=b"same", capture_policy="FULL_EPISODE")
    distinct = store.put(project_id=first_project, content_type="model_visible_text", payload=b"distinct", capture_policy="FULL_EPISODE")
    other = store.put(project_id=second_project, content_type="model_visible_text", payload=b"same", capture_policy="FULL_EPISODE")

    assert first.content_ref == repeated.content_ref
    assert first.content_ref != other.content_ref
    assert first.path != other.path
    first_envelope = json.loads(first.path.read_text())
    distinct_envelope = json.loads(distinct.path.read_text())
    assert first_envelope["nonce"] != distinct_envelope["nonce"]


def test_wrong_project_tamper_and_hidden_reasoning_fail_closed(tmp_path: Path) -> None:
    store, keys = _store(tmp_path)
    project_id = _project()
    foreign = _project()
    keys.set_key(project_id, os.urandom(32))
    keys.set_key(foreign, os.urandom(32))
    reference = store.put(project_id=project_id, content_type="tool_result", payload=b"safe", capture_policy="FULL_EPISODE")

    with pytest.raises(ContentError) as captured:
        store.get(project_id=foreign, content_ref=reference.content_ref)
    assert captured.value.code == "TRACE_INTEGRITY_FAILURE"

    envelope = json.loads(reference.path.read_text())
    envelope["ciphertext"] = envelope["ciphertext"][:-4] + "AAAA"
    reference.path.write_text(json.dumps(envelope))
    with pytest.raises(ContentError) as captured:
        store.get(project_id=project_id, content_ref=reference.content_ref)
    assert captured.value.code == "TRACE_INTEGRITY_FAILURE"

    with pytest.raises(ContentError) as captured:
        store.put(project_id=project_id, content_type="hidden_reasoning", payload=b"private chain", capture_policy="FULL_EPISODE")
    assert captured.value.code == "PRIVACY_POLICY_VIOLATION"


def test_quota_and_oversized_payload_fail_before_persistence(tmp_path: Path) -> None:
    store, keys = _store(tmp_path, quota=600)
    project_id = _project()
    keys.set_key(project_id, os.urandom(32))

    with pytest.raises(ContentError) as captured:
        store.put(project_id=project_id, content_type="model_visible_text", payload=b"x" * 20_000_000, capture_policy="FULL_EPISODE")
    assert captured.value.code == "CAPTURE_QUOTA_EXCEEDED"
    assert list((tmp_path / "content").rglob("*.blob")) == []


def test_orphan_cleanup_removes_only_atomic_temp_files(tmp_path: Path) -> None:
    store, keys = _store(tmp_path)
    project_id = _project()
    keys.set_key(project_id, os.urandom(32))
    reference = store.put(project_id=project_id, content_type="model_visible_text", payload=b"safe", capture_policy="FULL_EPISODE")
    orphan = reference.path.parent / ".orphan.tmp"
    orphan.write_bytes(b"partial")

    assert store.cleanup_orphans(project_id=project_id) == 1
    assert reference.path.exists()
    assert not orphan.exists()
