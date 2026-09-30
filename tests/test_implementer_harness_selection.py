"""Tests for EIH-A: contract selection (implementer_harness) and board projection."""

from __future__ import annotations

import json
import re
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from aether_agents.objective_contracts import (
    REQUIRED_SECTIONS,
    ContractError,
    ObjectiveContractStore,
)
from aether_agents.objective_contracts.store import (
    _FINAL_REQUIRED_METADATA,
    _SECTION_TITLES,
    _TITLE_TO_SECTION,
    _TRACE_ID_RE,
    _TRUNCATION_RE,
)
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.privacy import contains_secret_shape

PROJECT_A = "11111111-1111-4111-8111-111111111111"
PROJECT_B = "22222222-2222-4222-8222-222222222222"
FIXED_NOW = datetime(2026, 9, 30, 10, 0, tzinfo=timezone(timedelta(hours=-6)))


def _project(tmp_path: Path, registry: ProjectRegistry, project_id: str, name: str) -> Path:
    root = tmp_path / name
    marker = root / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'project_id = "{project_id}"',
                f'name = "{name}"',
                'initialized_by = "1.0.0"',
                'forge = "local"',
                'contract_root = "specs"',
                "",
            )
        ),
        encoding="utf-8",
    )
    (root / "specs").mkdir(parents=True, exist_ok=True)
    subprocess.run(("git", "init", "-q"), cwd=root, check=True)
    assert registry.register(project_id, root, name)
    return root


def _store(tmp_path: Path) -> tuple[ObjectiveContractStore, ProjectRegistry]:
    registry = ProjectRegistry(root=tmp_path / "state")
    return ObjectiveContractStore(registry=registry, clock=lambda: FIXED_NOW), registry


def _complete(
    store: ObjectiveContractStore, project_id: str, contract_id: str, revision: int
) -> int:
    for section in REQUIRED_SECTIONS:
        result = store.set_section(
            project_id=project_id,
            contract_id=contract_id,
            expected_revision=revision,
            section=section,
            content=f"Accepted content for {section.replace('_', ' ')}.",
            session_id="session-author",
        )
        revision = result["revision"]
    return revision


def reference_prechange_render(
    draft: dict[str, Any], *, finalized_utc: str, finalized_local: str, session_id: str
) -> bytes:
    """Exact pre-change renderer logic from 4bbf8ac2."""
    metadata = {
        "artifact_type": "aether.objective-contract.v1",
        "project_id": draft["project_id"],
        "contract_id": draft["contract_id"],
        "version": draft["target_version"],
        "status": "final",
        "title": draft["title"],
        "created_at_utc": draft["created_at_utc"],
        "created_at_local": draft["created_at_local"],
        "finalized_at_utc": finalized_utc,
        "finalized_at_local": finalized_local,
        "author_profile": draft["author_profile"],
        "created_in_session": draft["created_in_session"],
        "finalized_in_session": session_id,
        "supersedes": draft.get("supersedes"),
        "change_reason": draft.get("change_reason"),
        "observation_trace_id": "ctr_" + "0" * 32,
    }
    lines = ["---"]
    lines.extend(
        f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()
    )
    lines.extend(("---", "", f"# Objective Contract: {draft['title']}", ""))
    sections = draft["sections"]
    for key in REQUIRED_SECTIONS:
        lines.extend((f"## {_SECTION_TITLES[key]}", "", sections[key], ""))
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def rc17_style_parse_and_validate(text: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Exact rc17 parser and validator (unaware of implementer_harness)."""
    assert text.startswith("---\n") and "\n---\n" in text[4:]
    front, body = text[4:].split("\n---\n", 1)
    metadata: dict[str, Any] = {}
    for line in front.splitlines():
        key, raw = line.split(": ", 1)
        metadata[key] = json.loads(raw)
    sections: dict[str, str] = {}
    matches = list(re.finditer(r"^## (.+)$", body, flags=re.MULTILINE))
    for index, match in enumerate(matches):
        key = _TITLE_TO_SECTION.get(match.group(1))
        if key is None:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[key] = body[start:end].strip()

    # rc17 validation checks:
    assert not any(key not in metadata for key in _FINAL_REQUIRED_METADATA)
    assert not any(not sections.get(key, "").strip() for key in REQUIRED_SECTIONS)
    assert metadata["artifact_type"] == "aether.objective-contract.v1"
    assert metadata["status"] == "final"
    text_fields = (
        "title",
        "created_at_utc",
        "created_at_local",
        "finalized_at_utc",
        "finalized_at_local",
        "created_in_session",
        "finalized_in_session",
    )
    assert metadata["author_profile"] == "morfeo"
    assert not any(
        not isinstance(metadata[key], str) or not metadata[key].strip() for key in text_fields
    )
    trace_id = metadata.get("observation_trace_id")
    if trace_id is not None:
        assert isinstance(trace_id, str) and _TRACE_ID_RE.fullmatch(trace_id) is not None
    assert not any(
        _TRUNCATION_RE.search(value) or contains_secret_shape(value) for value in sections.values()
    )
    return metadata, sections


def test_begin_unselected_and_hermes_semantics(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")

    # 1. begin with implementer_harness omitted (None)
    res_none = store.begin(project_id=PROJECT_A, title="Unselected contract", session_id="s1")
    assert res_none.get("implementer_harness") is None
    show_none = store.show(project_id=PROJECT_A, contract_id=res_none["contract_id"])
    assert show_none.get("implementer_harness") is None
    draft_none = json.loads(
        (tmp_path / "alpha" / ".aether" / "drafts" / f"{res_none['contract_id']}.json").read_text(
            encoding="utf-8"
        )
    )
    assert "implementer_harness" not in draft_none

    # 2. begin with implementer_harness="hermes"
    res_hermes = store.begin(
        project_id=PROJECT_A,
        title="Explicit hermes contract",
        session_id="s1",
        implementer_harness="hermes",
    )
    assert res_hermes.get("implementer_harness") is None
    show_hermes = store.show(project_id=PROJECT_A, contract_id=res_hermes["contract_id"])
    assert show_hermes.get("implementer_harness") is None
    draft_hermes = json.loads(
        (tmp_path / "alpha" / ".aether" / "drafts" / f"{res_hermes['contract_id']}.json").read_text(
            encoding="utf-8"
        )
    )
    assert "implementer_harness" not in draft_hermes


def test_begin_claude_code_selection(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")

    res = store.begin(
        project_id=PROJECT_A,
        title="Claude Code contract",
        session_id="s1",
        implementer_harness="claude-code",
    )
    assert res.get("implementer_harness") == "claude-code"
    show_res = store.show(project_id=PROJECT_A, contract_id=res["contract_id"])
    assert show_res.get("implementer_harness") == "claude-code"
    draft_res = json.loads(
        (tmp_path / "alpha" / ".aether" / "drafts" / f"{res['contract_id']}.json").read_text(
            encoding="utf-8"
        )
    )
    assert draft_res.get("implementer_harness") == "claude-code"


def test_begin_rejects_unknown_values(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")

    invalid_values = ["claude", "gpt-4", "", "hermes-agent", "Claude-Code", 123, True]
    for val in invalid_values:
        with pytest.raises(ContractError) as exc_info:
            store.begin(
                project_id=PROJECT_A,
                title="Invalid harness contract",
                session_id="s1",
                implementer_harness=val,  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID"


def test_unselected_and_hermes_render_bytes_identical_to_prechange(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, registry = _store(tmp_path)
    _project(tmp_path, registry, PROJECT_A, "alpha")
    _project(tmp_path, registry, PROJECT_B, "beta")

    # Test omitted
    res_none = store.begin(project_id=PROJECT_A, title="Contract A", session_id="s1")
    _complete(store, PROJECT_A, res_none["contract_id"], 1)
    draft_none = store.show(project_id=PROJECT_A, contract_id=res_none["contract_id"])

    # Pin trace id during rendering so observation_trace_id is deterministic
    monkeypatch.setattr(secrets, "token_hex", lambda n: "0" * (2 * n))

    rendered_none = store._render_final(
        draft_none,
        finalized_utc="2026-09-30T16:00:00Z",
        finalized_local="2026-09-30T10:00:00-06:00",
        session_id="s1",
    )
    expected_prechange = reference_prechange_render(
        draft_none,
        finalized_utc="2026-09-30T16:00:00Z",
        finalized_local="2026-09-30T10:00:00-06:00",
        session_id="s1",
    )
    assert rendered_none == expected_prechange
    assert b"implementer_harness" not in rendered_none

    monkeypatch.undo()

    # Test hermes
    res_hermes = store.begin(
        project_id=PROJECT_B, title="Contract B", session_id="s1", implementer_harness="hermes"
    )
    _complete(store, PROJECT_B, res_hermes["contract_id"], 1)
    draft_hermes = store.show(project_id=PROJECT_B, contract_id=res_hermes["contract_id"])
    draft_hermes["project_id"] = draft_none["project_id"]
    draft_hermes["contract_id"] = draft_none["contract_id"]
    draft_hermes["title"] = draft_none["title"]
    draft_hermes["created_at_utc"] = draft_none["created_at_utc"]
    draft_hermes["created_at_local"] = draft_none["created_at_local"]

    monkeypatch.setattr(secrets, "token_hex", lambda n: "0" * (2 * n))

    rendered_hermes = store._render_final(
        draft_hermes,
        finalized_utc="2026-09-30T16:00:00Z",
        finalized_local="2026-09-30T10:00:00-06:00",
        session_id="s1",
    )
    assert rendered_hermes == expected_prechange
    assert b"implementer_harness" not in rendered_hermes


def test_claude_code_renders_frontmatter_key_and_finalizes(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    res = store.begin(
        project_id=PROJECT_A,
        title="Claude Contract",
        session_id="s1",
        implementer_harness="claude-code",
    )
    rev = _complete(store, PROJECT_A, res["contract_id"], 1)
    finalized = store.finalize(
        project_id=PROJECT_A,
        contract_id=res["contract_id"],
        expected_revision=rev,
        session_id="s1",
    )
    assert finalized.get("implementer_harness") == "claude-code"

    final_file = project / finalized["relative_path"]
    final_bytes = final_file.read_bytes()
    assert b'implementer_harness: "claude-code"\n' in final_bytes

    # Parse through _parse_final
    metadata, sections = store._parse_final(final_file)
    assert metadata.get("implementer_harness") == "claude-code"
    store._validate_final(metadata, sections)


def test_validate_final_accepts_claude_and_rejects_unknown(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    res = store.begin(
        project_id=PROJECT_A,
        title="Valid Claude",
        session_id="s1",
        implementer_harness="claude-code",
    )
    rev = _complete(store, PROJECT_A, res["contract_id"], 1)
    finalized = store.finalize(
        project_id=PROJECT_A,
        contract_id=res["contract_id"],
        expected_revision=rev,
        session_id="s1",
    )
    final_file = project / finalized["relative_path"]

    metadata, sections = store._parse_final(final_file)
    assert metadata["implementer_harness"] == "claude-code"
    store._validate_final(metadata, sections)  # Should not raise

    # Case: unknown value in final metadata
    bad_meta = dict(metadata)
    bad_meta["implementer_harness"] = "hermes"  # Final contract cannot have hermes (must be absent)
    with pytest.raises(ContractError) as exc_info:
        store._validate_final(bad_meta, sections)
    assert exc_info.value.code == "AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID"

    bad_meta["implementer_harness"] = "unknown"
    with pytest.raises(ContractError) as exc_info:
        store._validate_final(bad_meta, sections)
    assert exc_info.value.code == "AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID"

    bad_meta["implementer_harness"] = None
    with pytest.raises(ContractError) as exc_info:
        store._validate_final(bad_meta, sections)
    assert exc_info.value.code == "AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID"


def test_rc17_style_parser_accepts_selected_final_contract(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    res = store.begin(
        project_id=PROJECT_A,
        title="RC17 Compatibility",
        session_id="s1",
        implementer_harness="claude-code",
    )
    rev = _complete(store, PROJECT_A, res["contract_id"], 1)
    finalized = store.finalize(
        project_id=PROJECT_A,
        contract_id=res["contract_id"],
        expected_revision=rev,
        session_id="s1",
    )
    final_file = project / finalized["relative_path"]
    final_text = final_file.read_text(encoding="utf-8")

    meta, secs = rc17_style_parse_and_validate(final_text)
    assert meta["implementer_harness"] == "claude-code"
    assert meta["artifact_type"] == "aether.objective-contract.v1"
    assert meta["status"] == "final"


def test_supersede_from_unselected_v1(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    # Start unselected v1
    res = store.begin(project_id=PROJECT_A, title="Unselected v1", session_id="s1")
    cid = res["contract_id"]
    rev = _complete(store, PROJECT_A, cid, 1)
    store.finalize(project_id=PROJECT_A, contract_id=cid, expected_revision=rev, session_id="s1")

    # 1. supersede with implementer_harness omitted (inherits None)
    sup_none = store.supersede(
        project_id=PROJECT_A,
        contract_id=cid,
        version=1,
        change_reason="Add detail.",
        session_id="s2",
    )
    assert sup_none.get("implementer_harness") is None
    show_none = store.show(project_id=PROJECT_A, contract_id=cid)
    assert show_none.get("implementer_harness") is None
    # Delete draft to test next case
    (project / sup_none["draft_path"]).unlink()

    # 2. supersede with implementer_harness="hermes" (clears/unselected)
    sup_hermes = store.supersede(
        project_id=PROJECT_A,
        contract_id=cid,
        version=1,
        change_reason="Stay on hermes.",
        session_id="s2",
        implementer_harness="hermes",
    )
    assert sup_hermes.get("implementer_harness") is None
    show_hermes = store.show(project_id=PROJECT_A, contract_id=cid)
    assert show_hermes.get("implementer_harness") is None
    (project / sup_hermes["draft_path"]).unlink()

    # 3. supersede with implementer_harness="claude-code" (sets selection)
    sup_claude = store.supersede(
        project_id=PROJECT_A,
        contract_id=cid,
        version=1,
        change_reason="Switch to claude.",
        session_id="s2",
        implementer_harness="claude-code",
    )
    assert sup_claude.get("implementer_harness") == "claude-code"
    show_claude = store.show(project_id=PROJECT_A, contract_id=cid)
    assert show_claude.get("implementer_harness") == "claude-code"
    (project / sup_claude["draft_path"]).unlink()

    # 4. supersede with invalid value rejected
    with pytest.raises(ContractError) as exc_info:
        store.supersede(
            project_id=PROJECT_A,
            contract_id=cid,
            version=1,
            change_reason="Bad harness.",
            session_id="s2",
            implementer_harness="unknown",
        )
    assert exc_info.value.code == "AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID"


def test_supersede_from_claude_code_v1(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    # Start claude-code v1
    res = store.begin(
        project_id=PROJECT_A,
        title="Claude v1",
        session_id="s1",
        implementer_harness="claude-code",
    )
    cid = res["contract_id"]
    rev = _complete(store, PROJECT_A, cid, 1)
    store.finalize(project_id=PROJECT_A, contract_id=cid, expected_revision=rev, session_id="s1")

    # 1. supersede with implementer_harness omitted (inherits "claude-code")
    sup_none = store.supersede(
        project_id=PROJECT_A,
        contract_id=cid,
        version=1,
        change_reason="Inherit claude.",
        session_id="s2",
    )
    assert sup_none.get("implementer_harness") == "claude-code"
    show_none = store.show(project_id=PROJECT_A, contract_id=cid)
    assert show_none.get("implementer_harness") == "claude-code"
    (project / sup_none["draft_path"]).unlink()

    # 2. supersede with implementer_harness="hermes" (clears to None)
    sup_hermes = store.supersede(
        project_id=PROJECT_A,
        contract_id=cid,
        version=1,
        change_reason="Revert to hermes.",
        session_id="s2",
        implementer_harness="hermes",
    )
    assert sup_hermes.get("implementer_harness") is None
    show_hermes = store.show(project_id=PROJECT_A, contract_id=cid)
    assert show_hermes.get("implementer_harness") is None
    (project / sup_hermes["draft_path"]).unlink()

    # 3. supersede with implementer_harness="claude-code" (explicitly sets "claude-code")
    sup_claude = store.supersede(
        project_id=PROJECT_A,
        contract_id=cid,
        version=1,
        change_reason="Keep claude.",
        session_id="s2",
        implementer_harness="claude-code",
    )
    assert sup_claude.get("implementer_harness") == "claude-code"
    show_claude = store.show(project_id=PROJECT_A, contract_id=cid)
    assert show_claude.get("implementer_harness") == "claude-code"
    (project / sup_claude["draft_path"]).unlink()


def test_prepare_handoff_selection_projection_and_envelope_preservation(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    # 1. Claude Code contract
    res_claude = store.begin(
        project_id=PROJECT_A,
        title="Claude Contract",
        session_id="s1",
        implementer_harness="claude-code",
    )
    cid_c = res_claude["contract_id"]
    rev_c = _complete(store, PROJECT_A, cid_c, 1)
    store.finalize(
        project_id=PROJECT_A, contract_id=cid_c, expected_revision=rev_c, session_id="s1"
    )

    # Commit contract and marker into git base
    subprocess.run(
        ("git", "add", ".aether/project.toml", ".aether/objective-contracts"),
        cwd=project,
        check=True,
    )
    subprocess.run(
        ("git", "commit", "-qm", "docs: finalize claude contract"), cwd=project, check=True
    )

    handoff_claude = store.prepare_handoff(project_id=PROJECT_A, contract_id=cid_c, version=1)
    assert handoff_claude["handoff_ready"] is True
    assert handoff_claude.get("implementer_harness") == "claude-code"
    # Envelope must not contain harness text
    assert "claude" not in handoff_claude["envelope"].lower()
    assert "harness" not in handoff_claude["envelope"].lower()

    # 2. Unselected contract
    res_unsel = store.begin(project_id=PROJECT_A, title="Unselected Contract", session_id="s1")
    cid_u = res_unsel["contract_id"]
    rev_u = _complete(store, PROJECT_A, cid_u, 1)
    store.finalize(
        project_id=PROJECT_A, contract_id=cid_u, expected_revision=rev_u, session_id="s1"
    )

    subprocess.run(
        ("git", "add", ".aether/objective-contracts"),
        cwd=project,
        check=True,
    )
    subprocess.run(
        ("git", "commit", "-qm", "docs: finalize unselected contract"), cwd=project, check=True
    )

    handoff_unsel = store.prepare_handoff(project_id=PROJECT_A, contract_id=cid_u, version=1)
    assert handoff_unsel["handoff_ready"] is True
    assert "implementer_harness" not in handoff_unsel
    assert "claude" not in handoff_unsel["envelope"].lower()
    assert "harness" not in handoff_unsel["envelope"].lower()


def test_draft_validation_rejects_tampered_harness(tmp_path: Path) -> None:
    store, registry = _store(tmp_path)
    project = _project(tmp_path, registry, PROJECT_A, "alpha")

    res = store.begin(project_id=PROJECT_A, title="Tamper Contract", session_id="s1")
    cid = res["contract_id"]
    draft_file = project / res["draft_path"]
    data = json.loads(draft_file.read_text(encoding="utf-8"))
    data["implementer_harness"] = "invalid-harness"
    draft_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ContractError) as exc_info:
        store.validate(project_id=PROJECT_A, contract_id=cid)
    assert exc_info.value.code == "AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID"


def test_hermes_plugin_handle_action_restrictions_and_unknown_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aether_agents.objective_contracts import hermes_plugin

    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state-home"))

    project = tmp_path / "repo"
    project.mkdir()
    subprocess.run(("git", "init", "-q"), cwd=project, check=True)
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        f'schema_version = 1\nproject_id = "{PROJECT_A}"\nname = "repo"\ninitialized_by = "1.0.0"\nforge = "local"\ncontract_root = "specs"\n',
        encoding="utf-8",
    )
    registry = ProjectRegistry()
    registry.register(PROJECT_A, project, "repo")

    # Mock _native_session_workspace to return project
    monkeypatch.setattr(hermes_plugin, "_native_session_workspace", lambda s: project)

    # 1. Any action other than begin/supersede receiving implementer_harness is rejected
    forbidden_actions = [
        {
            "action": "set_section",
            "contract_id": "oc_" + "1" * 16,
            "expected_revision": 1,
            "section": "owner_intent",
            "content": "hello",
        },
        {"action": "show", "contract_id": "oc_" + "1" * 16},
        {"action": "list"},
        {"action": "validate", "contract_id": "oc_" + "1" * 16},
        {"action": "finalize", "contract_id": "oc_" + "1" * 16, "expected_revision": 1},
        {"action": "prepare_handoff", "contract_id": "oc_" + "1" * 16, "version": 1},
    ]
    for args in forbidden_actions:
        args["project_id"] = PROJECT_A
        args["implementer_harness"] = "claude-code"
        res = json.loads(hermes_plugin._handle(args, session_id="s1", author_profile="morfeo"))
        assert res.get("success") is False, (
            f"Action {args['action']} did not fail when receiving implementer_harness"
        )
        assert res.get("error", {}).get("code") == "AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID"

        # Also test with "hermes"
        args["implementer_harness"] = "hermes"
        res = json.loads(hermes_plugin._handle(args, session_id="s1", author_profile="morfeo"))
        assert res.get("success") is False
        assert res.get("error", {}).get("code") == "AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID"

    # 2. begin via _handle with unknown implementer_harness is rejected
    res_bad = json.loads(
        hermes_plugin._handle(
            {
                "action": "begin",
                "project_id": PROJECT_A,
                "title": "Bad harness",
                "implementer_harness": "unknown-harness",
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert res_bad.get("success") is False
    assert res_bad.get("error", {}).get("code") == "AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID"

    # 3. begin via _handle with claude-code succeeds
    res_claude = json.loads(
        hermes_plugin._handle(
            {
                "action": "begin",
                "project_id": PROJECT_A,
                "title": "Claude contract",
                "implementer_harness": "claude-code",
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert res_claude.get("implementer_harness") == "claude-code"
    cid = res_claude["contract_id"]

    # 4. show reports the selection
    res_show = json.loads(
        hermes_plugin._handle(
            {"action": "show", "project_id": PROJECT_A, "contract_id": cid},
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert res_show.get("implementer_harness") == "claude-code"


def test_board_metadata_creation_and_reuse_validation(tmp_path: Path) -> None:
    from aether_agents.objective_contracts.execution_boards import ExecutionBoardError
    from aether_agents.objective_contracts.hermes_plugin import (
        _create_metadata_exclusive,
        _validate_execution_metadata,
    )

    project_root = tmp_path / "repo"
    meta_path = tmp_path / "board.json"

    # 1. Exclusive creation without selection
    created = _create_metadata_exclusive(
        meta_path,
        slug="board-unselected",
        project_root=project_root,
        runtime_project_id="proj-1",
        aether_project_id=PROJECT_A,
        contract_id="oc_aaaaaaaaaaaaaaaa",
        version=1,
        implementer_harness=None,
    )
    assert created is True
    meta_unsel = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "aether_implementer_harness" not in meta_unsel

    # Reuse validation: unselected contract matches unselected board
    _validate_execution_metadata(
        meta_unsel,
        runtime_project_id="proj-1",
        project_root=project_root,
        aether_project_id=PROJECT_A,
        contract_id="oc_aaaaaaaaaaaaaaaa",
        version=1,
        implementer_harness=None,
    )

    # Reuse validation: claude-code contract against unselected board raises IDENTITY-CONFLICT
    with pytest.raises(ExecutionBoardError) as exc_info:
        _validate_execution_metadata(
            meta_unsel,
            runtime_project_id="proj-1",
            project_root=project_root,
            aether_project_id=PROJECT_A,
            contract_id="oc_aaaaaaaaaaaaaaaa",
            version=1,
            implementer_harness="claude-code",
        )
    assert exc_info.value.code == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"

    # 2. Exclusive creation with claude-code selection
    meta_path_claude = tmp_path / "board_claude.json"
    created_claude = _create_metadata_exclusive(
        meta_path_claude,
        slug="board-claude",
        project_root=project_root,
        runtime_project_id="proj-1",
        aether_project_id=PROJECT_A,
        contract_id="oc_aaaaaaaaaaaaaaaa",
        version=1,
        implementer_harness="claude-code",
    )
    assert created_claude is True
    meta_claude = json.loads(meta_path_claude.read_text(encoding="utf-8"))
    assert meta_claude.get("aether_implementer_harness") == "claude-code"

    # Reuse validation: claude-code contract matches claude-code board
    _validate_execution_metadata(
        meta_claude,
        runtime_project_id="proj-1",
        project_root=project_root,
        aether_project_id=PROJECT_A,
        contract_id="oc_aaaaaaaaaaaaaaaa",
        version=1,
        implementer_harness="claude-code",
    )

    # Reuse validation: unselected contract against claude-code board raises IDENTITY-CONFLICT
    with pytest.raises(ExecutionBoardError) as exc_info:
        _validate_execution_metadata(
            meta_claude,
            runtime_project_id="proj-1",
            project_root=project_root,
            aether_project_id=PROJECT_A,
            contract_id="oc_aaaaaaaaaaaaaaaa",
            version=1,
            implementer_harness=None,
        )
    assert exc_info.value.code == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"

    # 3. Invalid board value (e.g. "hermes" on board) raises IDENTITY-CONFLICT for both
    meta_invalid = dict(meta_unsel)
    meta_invalid["aether_implementer_harness"] = "hermes"
    with pytest.raises(ExecutionBoardError) as exc_info:
        _validate_execution_metadata(
            meta_invalid,
            runtime_project_id="proj-1",
            project_root=project_root,
            aether_project_id=PROJECT_A,
            contract_id="oc_aaaaaaaaaaaaaaaa",
            version=1,
            implementer_harness=None,
        )
    assert exc_info.value.code == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"

    with pytest.raises(ExecutionBoardError) as exc_info:
        _validate_execution_metadata(
            meta_invalid,
            runtime_project_id="proj-1",
            project_root=project_root,
            aether_project_id=PROJECT_A,
            contract_id="oc_aaaaaaaaaaaaaaaa",
            version=1,
            implementer_harness="claude-code",
        )
    assert exc_info.value.code == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"


def test_registered_tool_schema_contains_implementer_harness() -> None:
    from aether_agents.objective_contracts import hermes_plugin

    registered: dict[str, Any] = {}

    class DummyContext:
        profile_name = "morfeo"

        def get_config(self, key: str, default: Any = None) -> Any:
            return "morfeo" if key == "author_profile" else default

        def register_tool(self, **kwargs: Any) -> None:
            registered.update(kwargs)

    hermes_plugin.register(DummyContext())
    assert registered["name"] == "objective_contract"
    schema = registered["schema"]
    properties = schema["parameters"]["properties"]
    assert "implementer_harness" in properties
    assert properties["implementer_harness"]["type"] == "string"
    assert properties["implementer_harness"]["enum"] == ["hermes", "claude-code"]


def test_prepare_handoff_provisions_and_validates_board_metadata_e2e(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hermes_cli import kanban_db, projects_db

    from aether_agents.objective_contracts import hermes_plugin

    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state-home"))
    for name in ("HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_HOME"):
        monkeypatch.delenv(name, raising=False)

    project = tmp_path / "repo"
    project.mkdir()
    subprocess.run(("git", "init", "-q"), cwd=project, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=project, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=project, check=True)

    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        f'schema_version = 1\nproject_id = "{PROJECT_A}"\nname = "repo"\ninitialized_by = "1.0.0"\nforge = "local"\ncontract_root = "specs"\n',
        encoding="utf-8",
    )
    registry = ProjectRegistry()
    registry.register(PROJECT_A, project, "repo")

    with projects_db.connect_closing() as connection:
        projects_db.create_project(connection, name="Repo", primary_path=str(project))

    # Mock _native_session_workspace
    monkeypatch.setattr(hermes_plugin, "_native_session_workspace", lambda s: project)

    # 1. Author and finalize claude-code contract
    res_claude = json.loads(
        hermes_plugin._handle(
            {
                "action": "begin",
                "project_id": PROJECT_A,
                "title": "E2E Claude Contract",
                "implementer_harness": "claude-code",
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    cid_c = res_claude["contract_id"]
    rev = 1
    for sec in REQUIRED_SECTIONS:
        updated = json.loads(
            hermes_plugin._handle(
                {
                    "action": "set_section",
                    "project_id": PROJECT_A,
                    "contract_id": cid_c,
                    "expected_revision": rev,
                    "section": sec,
                    "content": f"E2E content for {sec}",
                },
                session_id="s1",
                author_profile="morfeo",
            )
        )
        rev = updated["revision"]

    finalized_c = json.loads(
        hermes_plugin._handle(
            {
                "action": "finalize",
                "project_id": PROJECT_A,
                "contract_id": cid_c,
                "expected_revision": rev,
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert finalized_c["status"] == "final"

    # Commit files to git base
    subprocess.run(("git", "add", "."), cwd=project, check=True)
    subprocess.run(("git", "commit", "-qm", "docs: finalize claude"), cwd=project, check=True)

    # Prepare handoff
    prepared_c = json.loads(
        hermes_plugin._handle(
            {
                "action": "prepare_handoff",
                "project_id": PROJECT_A,
                "contract_id": cid_c,
                "version": 1,
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert prepared_c["handoff_ready"] is True
    assert prepared_c["implementer_harness"] == "claude-code"

    board_slug_c = prepared_c["execution_board"]
    meta_c = kanban_db.read_board_metadata(board_slug_c)
    assert meta_c["aether_implementer_harness"] == "claude-code"

    # Reuse: calling prepare_handoff again succeeds idempotently
    reused_c = json.loads(
        hermes_plugin._handle(
            {
                "action": "prepare_handoff",
                "project_id": PROJECT_A,
                "contract_id": cid_c,
                "version": 1,
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert reused_c["handoff_ready"] is True

    # Tampering: if the board's harness selection is cleared, reuse fails
    board_dir = kanban_db.board_dir(board_slug_c)
    meta_file = board_dir / "board.json"
    meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
    del meta_data["aether_implementer_harness"]
    meta_file.write_text(json.dumps(meta_data), encoding="utf-8")

    mismatch_res = json.loads(
        hermes_plugin._handle(
            {
                "action": "prepare_handoff",
                "project_id": PROJECT_A,
                "contract_id": cid_c,
                "version": 1,
            },
            session_id="s1",
            author_profile="morfeo",
        )
    )
    assert mismatch_res.get("success") is False
    assert mismatch_res.get("error", {}).get("code") == "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT"
