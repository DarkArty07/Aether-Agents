"""Contract tests for deterministic Hermes patch reconciliation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "specs"
    / "001-aether-v1-productization"
    / "contracts"
    / "hermes-patch-reconciliation.schema.json"
)
SCRIPT = ROOT / "scripts" / "validate_hermes_patch_reconciliation.py"
LEDGER_PATH = ROOT / "HERMES_LOCAL_PATCHES.md"
UPSTREAM_REPOSITORY = "https://github.com/NousResearch/hermes-agent"
UPSTREAM_REVISION = "a" * 40
OBSERVED_AT = "2026-08-30T20:00:00Z"


def _load_validator():
    spec = importlib.util.spec_from_file_location("hermes_patch_reconciliation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _evidence(kind: str, reference: str, result: str) -> dict[str, str]:
    return {"kind": kind, "reference": reference, "result": result}


def _record(identifier: str) -> dict[str, Any]:
    components = [identifier]
    if identifier == "HLP-211":
        components.append("HLP-211b")
    return {
        "id": identifier,
        "ledger_locator": "HERMES_LOCAL_PATCHES.md:1-1",
        "components": components,
        "required_behavior": f"Retain the required {identifier} behavior.",
        "local_status": "ACTIVE_LOCAL",
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "inspected_revision": UPSTREAM_REVISION,
            "linked_refs": [],
            "disposition": "upstream_missing",
            "evidence": [
                _evidence(
                    "source",
                    "https://github.com/NousResearch/hermes-agent/blob/main/source.py",
                    "Equivalent behavior is absent at the inspected revision.",
                )
            ],
        },
        "retirement_gate": {
            "summary": "Run the recorded behavioral gate at the exact target revision.",
            "status": "failed",
            "evidence": [_evidence("test", "tests/test_gate.py", "The required behavior failed.")],
        },
        "artifact_verification": {
            "status": "not_applicable",
            "artifacts": [],
            "blocker": None,
        },
        "retirement_recommendation": "retain",
        "blocking_uncertainty": ["The local behavior remains required."],
        "summary": f"Retain {identifier} pending a complete target gate.",
    }


def _write_fixture(root: Path, records: list[dict[str, Any]]) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    ledger = root / "HERMES_LOCAL_PATCHES.md"
    ledger.write_text(
        "\n".join(
            (
                "# Ledger",
                "",
                "## Registro activo",
                "",
                "| ID | Estado |",
                "|---|---|",
                "| `HLP-211` | `ACTIVE_LOCAL` |",
                "",
                "## HLP-211 — combined behavior",
                "",
                "Active detailed record.",
                "",
                "## HLP-247 — omitted from the summary table",
                "",
                "Active detailed record.",
                "",
            )
        ),
        encoding="utf-8",
    )
    entries = root / "entries"
    entries.mkdir()
    for index, record in enumerate(records):
        suffix = "" if index == 0 else f"-{index}"
        path = entries / f"{record['id']}{suffix}.json"
        path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    return ledger, entries


def _reconcile(
    tmp_path: Path,
    records: list[dict[str, Any]],
    *,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    ledger, entries = _write_fixture(tmp_path, records)
    return _load_validator().reconcile(
        repository_root=tmp_path,
        ledger_path=ledger,
        entries_dir=entries,
        schema_path=schema_path,
        observed_at_utc=OBSERVED_AT,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_revision=UPSTREAM_REVISION,
    )


def test_reconciliation_contract_and_validator_are_present() -> None:
    assert SCHEMA_PATH.is_file()
    assert SCRIPT.is_file()


def test_active_detailed_ledger_ids_include_hlp247_not_in_summary_table() -> None:
    validator = _load_validator()

    assert validator.active_detailed_ledger_ids(LEDGER_PATH) == (
        "HLP-188",
        "HLP-189",
        "HLP-191",
        "HLP-194",
        "HLP-198",
        "HLP-204",
        "HLP-209",
        "HLP-211",
        "HLP-226",
        "HLP-246",
        "HLP-247",
        "HLP-262",
    )


def test_reconcile_sorts_records_binds_provenance_and_writes_deterministic_outputs(
    tmp_path: Path,
) -> None:
    records = [_record("HLP-247"), _record("HLP-211")]
    aggregate = _reconcile(tmp_path, records)

    assert aggregate["schema_version"] == "aether.hermes-patch-reconciliation.v1"
    assert aggregate["observed_at_utc"] == OBSERVED_AT
    assert aggregate["upstream"] == {
        "repository": UPSTREAM_REPOSITORY,
        "inspected_revision": UPSTREAM_REVISION,
    }
    assert (
        aggregate["source_ledger_sha256"]
        == hashlib.sha256((tmp_path / "HERMES_LOCAL_PATCHES.md").read_bytes()).hexdigest()
    )
    assert [record["id"] for record in aggregate["records"]] == ["HLP-211", "HLP-247"]
    assert aggregate["overall_blockers"]

    output = tmp_path / "reconciliation.json"
    preflight = tmp_path / "preflight.md"
    completed = subprocess.run(
        (
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--ledger",
            "HERMES_LOCAL_PATCHES.md",
            "--entries-dir",
            "entries",
            "--schema",
            str(SCHEMA_PATH),
            "--observed-at-utc",
            OBSERVED_AT,
            "--upstream-repository",
            UPSTREAM_REPOSITORY,
            "--upstream-revision",
            UPSTREAM_REVISION,
            "--output",
            str(output),
            "--preflight",
            str(preflight),
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    first_json = output.read_bytes()
    first_preflight = preflight.read_bytes()
    rerun = subprocess.run(
        completed.args,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rerun.returncode == 0, rerun.stderr
    assert output.read_bytes() == first_json
    assert preflight.read_bytes() == first_preflight
    report = preflight.read_text(encoding="utf-8")
    for heading in (
        "## Remaining local guarantees",
        "## Qualified upstream equivalents",
        "## Retirement blockers",
        "## Artifact integrity",
        "## Safe next decisions",
    ):
        assert heading in report
    assert "No final runtime is selected" in report
    assert "does not make a release claim" in report


@pytest.mark.parametrize(
    ("records", "message"),
    (
        ([_record("HLP-211")], "missing ledger IDs"),
        ([_record("HLP-211"), _record("HLP-211"), _record("HLP-247")], "duplicate"),
        ([_record("HLP-211"), _record("HLP-247"), _record("HLP-999")], "unknown ledger IDs"),
    ),
)
def test_reconcile_rejects_omitted_duplicate_or_unknown_ledger_ids(
    tmp_path: Path, records: list[dict[str, Any]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _reconcile(tmp_path, records)


def test_reconcile_rejects_hlp211_without_combined_hlp211b_component(tmp_path: Path) -> None:
    records = [_record("HLP-211"), _record("HLP-247")]
    records[0]["components"] = ["HLP-211"]

    with pytest.raises(ValueError, match="HLP-211b"):
        _reconcile(tmp_path, records)


def test_reconcile_rejects_schema_enum_and_version_drift(tmp_path: Path) -> None:
    records = [_record("HLP-211"), _record("HLP-247")]
    records[0]["upstream"]["disposition"] = "unreviewed"

    with pytest.raises(ValueError, match="schema validation"):
        _reconcile(tmp_path, records)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema["$defs"]["aggregate"]["properties"]["schema_version"]["const"] = "wrong.v1"
    drifted_schema = tmp_path / "drifted.schema.json"
    drifted_schema.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(ValueError, match="schema version drift"):
        _reconcile(
            tmp_path / "version-drift",
            [_record("HLP-211"), _record("HLP-247")],
            schema_path=drifted_schema,
        )


def test_reconcile_rejects_stale_artifact_hashes(tmp_path: Path) -> None:
    records = [_record("HLP-211"), _record("HLP-247")]
    patch_path = tmp_path / "patches" / "hermes" / "HLP-211b.patch"
    patch_path.parent.mkdir(parents=True)
    patch_path.write_text("portable patch\n", encoding="utf-8")
    digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    records[0]["artifact_verification"] = {
        "status": "passed",
        "artifacts": [
            {
                "kind": "patch",
                "reference": "patches/hermes/HLP-211b.patch",
                "result": "passed",
                "ledger_sha256": digest,
                "computed_sha256": "0" * 64,
                "checksum_status": "passed",
                "parse_status": "passed",
            }
        ],
        "blocker": None,
    }
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        _reconcile(tmp_path, records)


def test_reconcile_rejects_retirement_candidate_without_full_exact_gate(tmp_path: Path) -> None:
    records = [_record("HLP-211"), _record("HLP-247")]
    records[0]["retirement_recommendation"] = "retirement_candidate"

    with pytest.raises(ValueError, match="full passed gate"):
        _reconcile(tmp_path, records)


@pytest.mark.parametrize(
    ("mutator", "message"),
    (
        (
            lambda record: record.__setitem__(
                "summary", "Copied from /" + "home" + "/operator/private-runtime."
            ),
            "non-portable",
        ),
        (
            lambda record: record["upstream"].__setitem__("inspected_revision", "b" * 40),
            "upstream revision",
        ),
    ),
)
def test_reconcile_rejects_private_content_or_upstream_disagreement(
    tmp_path: Path, mutator: Any, message: str
) -> None:
    records = [_record("HLP-211"), _record("HLP-247")]
    mutator(records[1])

    with pytest.raises(ValueError, match=message):
        _reconcile(tmp_path, records)
