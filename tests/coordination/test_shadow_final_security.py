"""Regressions for R7 final independent security review findings."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from test_shadow import CONTRACT, GENERATION, PROJECT, ROOT, WORKER, evidence, make_plan
from test_shadow_store import correlation

from olympus_v3.coordination import ShadowCorrelationRegistry, ShadowSessionCorrelation
from olympus_v3.coordination.protocol import ValidationError
from olympus_v3.coordination.shadow_store import DurableShadowCorrelationRegistry


def test_evidence_rejects_project_identity_not_bound_to_participant():
    with pytest.raises(ValidationError, match="project identity"):
        asyncio.run(evidence(project_id="other-project"))


@pytest.mark.parametrize("metadata", ["[]", "null", '"scalar"', "{}", '{"project_root":null}'])
def test_evidence_rejects_missing_non_string_or_non_object_metadata_root(metadata):
    class BadMetadataDB:
        async def get_session(self, session_id):
            return {
                "session_id": session_id,
                "agent": WORKER.actor_id,
                "status": "completed",
                "metadata": metadata,
            }

        async def get_latest_turn(self, _session_id):
            return {"content": "AETHER_SHADOW_V1 task_id=task-a participant=hefesto technical_status=completed"}

    with pytest.raises(ValidationError, match="unbound Olympus session evidence"):
        asyncio.run(evidence(BadMetadataDB()))


def test_process_registry_rejects_incomplete_or_cross_project_binding():
    incomplete = ShadowSessionCorrelation("task-a", WORKER, ROOT, "predicted", "actual", "signature")
    cross_project = replace(
        incomplete,
        project_id="other-project",
        contract_id=CONTRACT,
        generation=GENERATION,
    )

    registry = ShadowCorrelationRegistry()
    assert registry.consume(incomplete) is False
    assert registry.consume(cross_project) is False


def test_process_registry_requires_complete_binding_and_both_session_identities_unique():
    item = asyncio.run(evidence())
    base = __import__(
        "olympus_v3.coordination", fromlist=["ShadowSessionCorrelation"]
    ).ShadowSessionCorrelation.from_evidence(make_plan(), item)
    registry = ShadowCorrelationRegistry()

    assert registry.consume(base) is True
    assert registry.consume(base) is True
    assert registry.consume(replace(base, actual_session_id="actual-other")) is False
    assert registry.consume(replace(base, predicted_session_id="predicted-other")) is False
    assert registry.consume(replace(base, contract_id="contract-other")) is False
    assert registry.consume(replace(base, generation=GENERATION + 1)) is False
    assert registry.consume(replace(base, project_id=PROJECT, project_root=ROOT)) is True


def test_durable_registry_serializes_same_instance_calls(tmp_path):
    registry = DurableShadowCorrelationRegistry(tmp_path / "shared.db", busy_timeout_ms=1000)
    item = correlation()
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: registry.consume(item), range(32)))
    finally:
        registry.close()

    assert results == [True] * 32


def test_durable_registry_same_instance_conflicts_fail_closed(tmp_path):
    registry = DurableShadowCorrelationRegistry(tmp_path / "shared.db", busy_timeout_ms=1000)
    base = correlation()
    conflict = replace(base, actual_session_id="actual-other")
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(registry.consume, [base, conflict] * 8))
    finally:
        registry.close()

    assert any(results)
    assert not all(results)
    assert sum(results) in {8}


def test_common_evidence_context_remains_complete():
    item = asyncio.run(evidence())
    assert (item.project_id, item.contract_id, item.generation) == (
        PROJECT,
        CONTRACT,
        GENERATION,
    )
