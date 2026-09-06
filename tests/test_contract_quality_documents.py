"""Document/source loading checks, NOT behavioral or installed-profile qualification."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
RESOURCES = ROOT / "src/aether_agents/resources"
SKILLS = {
    "objective-contract-design": "Morfeo",
    "supervisor-decomposition": "Supervisor",
    "implementation-evidence": "Implementer",
}


@pytest.mark.parametrize("name,role", SKILLS.items())
def test_skill_metadata_and_single_file_scope(name: str, role: str) -> None:
    directory = RESOURCES / "skills" / name
    assert {p.name for p in directory.iterdir()} == {"SKILL.md"}
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    front, body = text.removeprefix("---\n").split("\n---\n", 1)
    metadata = yaml.safe_load(front)
    assert metadata["name"] == name
    assert role in metadata["description"]
    assert len(metadata["description"]) <= 60
    assert metadata["version"] == "0.1.0"
    assert metadata["author"] == "Morfeo (Aether role), Hermes Agent"
    assert metadata["platforms"] == ["linux", "macos", "windows"]
    for heading in ("When to Use", "Prerequisites", "Procedure", "Pitfalls", "Verification"):
        assert f"## {heading}" in body
    assert "cannot grant authority" in " ".join(body.split()) or (
        "cannot grant" in body and "authority" in body
    )
    assert "project-relative" in body
    assert text.count("```") % 2 == 0
    assert "[truncated]" not in text.lower()
    assert not re.search(r"(?i)/home/|/users/|[a-z]:\\users\\", text)


@pytest.mark.parametrize("name", SKILLS)
def test_skill_content_has_no_executable_template(name: str) -> None:
    text = (RESOURCES / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    # These procedures must remain static documents, not shell preprocessing payloads.
    assert "!`" not in text
    assert "$ARGUMENTS" not in text


def test_unit_review_boundary_is_consistent_in_source_documents() -> None:
    paths = [
        RESOURCES / "profiles/supervisor/SOUL.md",
        RESOURCES / "skills/supervisor-decomposition/SKILL.md",
        RESOURCES / "skills/implementation-evidence/SKILL.md",
    ]
    for path in paths:
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "same-card" in text
        assert "claimed" in text and "review run" in text
        assert "terminal integration" in text.lower()
        assert "trusted runtime graph" in text
    # Presence checks establish documented boundaries, not that an agent obeyed them.


def test_native_loader_reads_exact_documents_in_disposable_home(tmp_path: Path) -> None:
    if importlib.util.find_spec("hermes_cli") is None:
        pytest.skip("native loader requires the already provisioned Hermes interpreter")
    home = tmp_path / "home"
    expected = {}
    for name in SKILLS:
        data = (RESOURCES / "skills" / name / "SKILL.md").read_bytes()
        target = home / "skills" / name / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        expected[name] = hashlib.sha256(data).hexdigest()
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("HERMES_KANBAN_") or key in {
            "HERMES_PROFILE", "HERMES_SESSION_ID", "HERMES_SKILLS_DIR",
        }:
            env.pop(key)
    # Never suppress a delegated-child identity marker; loading text needs no board mutation.
    env.update({
        "HERMES_HOME": str(home),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    script = """
import hashlib, json, os
from pathlib import Path
from tools.skills_tool import skill_view
result = {}
for name in json.loads(os.environ['CHECK_SKILL_NAMES']):
    response = json.loads(skill_view(name, preprocess=False))
    assert response.get('success'), response
    data = response['content'].encode('utf-8')
    source = Path(response['_source_path']).resolve()
    source.relative_to(Path(os.environ['HERMES_HOME']).resolve())
    result[name] = hashlib.sha256(data).hexdigest()
print(json.dumps(result, sort_keys=True))
"""
    env["CHECK_SKILL_NAMES"] = json.dumps(list(SKILLS))
    run = subprocess.run(
        [sys.executable, "-B", "-c", script], cwd=tmp_path, env=env,
        text=True, capture_output=True, timeout=60, check=False,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == expected
