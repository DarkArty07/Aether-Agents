"""Documentary observation and launch guidance checks, not organic agent qualification."""

from pathlib import Path

import pytest
import yaml

from aether_agents import launcher
from aether_agents.cli import _build_parser

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".aether/skills/aether-observe/SKILL.md"
GETTING_STARTED = ROOT / "docs/getting-started.md"
CLI_REFERENCE = ROOT / "docs/reference/cli.md"
LIFECYCLE_GUIDE = ROOT / "docs/guides/lifecycle.md"
LIMITATIONS = ROOT / "docs/reference/limitations-and-troubleshooting.md"
OBSERVATION_GUIDE = ROOT / "docs/guides/observation.md"
CAPABILITY_REGISTRY = ROOT / "docs/capabilities.toml"
GENERATED_REFERENCE = ROOT / "docs/reference/capabilities.md"


def test_project_skill_is_discovered_without_identity_hardcoding() -> None:
    text = SKILL.read_text()
    meta = yaml.safe_load(text.split("---", 2)[1])
    assert meta["name"] == "aether-observe"
    assert len(meta["description"]) <= 60
    assert "Project Canonical Skill" in text
    assert ".aether/skills/aether-observe/SKILL.md" in (ROOT / "AGENTS.md").read_text()
    assert "/home/" not in text and "/Users/" not in text
    soul = (ROOT / "src/aether_agents/resources/profiles/morfeo/SOUL.md").read_text()
    section = soul.split("### Status and observation", 1)[1].split("\n### ", 1)[0]
    for required in ("aether_observe", "freshness", "coverage", "targeted", "independent review"):
        assert required in section
    assert ".aether/skills/aether-observe" not in section
    assert "### Final result acceptance" in soul
    assert "contract-result-review" in soul


def test_skill_selects_status_changes_diagnose_and_explicit_fallback() -> None:
    text = SKILL.read_text()
    for required in (
        'action="status"',
        'action="changes"',
        'action="diagnose"',
        "since_summary_id",
        "summary_id",
        "as_of",
        "coverage",
        "Heartbeats prove liveness only",
        "specific requested correction",
        "schema/privacy error",
        "Do not disable privacy guards",
        "independent approval",
        "exact board/task binding",
    ):
        assert required in text


def test_documented_cli_forms_are_real_parser_options() -> None:
    parser = _build_parser()
    parser.parse_args(["observe", "CONTRACT_REF", "--project", "PROJECT_ROOT", "--json"])
    parser.parse_args(
        [
            "observe",
            "CONTRACT_REF",
            "--project",
            "PROJECT_ROOT",
            "--since",
            "sum_" + "0" * 64,
            "--json",
        ]
    )


def test_guide_distinguishes_authority_from_derived_state() -> None:
    text = (ROOT / "docs/guides/observation.md").read_text()
    assert "not a zero-write filesystem probe" in text
    assert "derived observation projection" in text
    assert "../../.aether/skills/aether-observe/SKILL.md" in text
    assert "read-only: it does not mutate" not in text


def test_documented_launch_and_recovery_forms_are_real_parser_options() -> None:
    """Documented launch, reconciliation and recovery forms must be real parser input."""

    parser = _build_parser()
    parser.parse_args(["--project", "/path/to/project", "--json"])
    parser.parse_args(["reconcile", "--to", "active", "--dry-run", "--json"])
    parser.parse_args(["reconcile", "--to", "active", "--yes", "--json"])
    parser.parse_args(["reconcile", "--to", "active"])
    parser.parse_args(["rollback", "--dry-run", "--yes", "--json"])
    parser.parse_args(["rollback", "1.0.0rc6", "--dry-run", "--json"])
    parser.parse_args(["doctor", "--project", "/path/to/project", "--json"])
    parser.parse_args(["observe", "CONTRACT_REF", "--project", "/path/to/project", "--json"])


def _marker(project_id: str, name: str) -> str:
    return (
        "schema_version = 1\n"
        f'project_id = "{project_id}"\n'
        f'name = "{name}"\n'
        'initialized_by = "0.0.0"\n'
        'forge = "local"\n'
        'contract_root = "specs"\n'
    )


def _initialized_project(root: Path, project_id: str, name: str) -> Path:
    (root / ".aether").mkdir(parents=True)
    (root / ".aether" / "project.toml").write_text(_marker(project_id, name), encoding="utf-8")
    (root / "AGENTS.md").write_text("# fixture project\n", encoding="utf-8")
    return root.resolve()


def test_documented_project_selection_precedence_matches_the_implemented_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The documented precedence is exercised against the real resolver, not just prose."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("AETHER_HERMES_ROOT", raising=False)
    monkeypatch.delenv("AETHER_PROJECT_ID", raising=False)
    monkeypatch.delenv("AETHER_PROJECT_ROOT", raising=False)

    from aether_agents.observation.context import ProjectRegistry

    registry = ProjectRegistry()
    alpha = _initialized_project(
        tmp_path / "alpha", "11111111-1111-4111-8111-111111111111", "alpha"
    )
    beta = _initialized_project(tmp_path / "beta", "22222222-2222-4222-8222-222222222222", "beta")
    assert registry.register("11111111-1111-4111-8111-111111111111", alpha, "alpha")
    assert registry.register("22222222-2222-4222-8222-222222222222", beta, "beta")

    # (1) An explicit --project wins over the current directory.
    monkeypatch.chdir(beta)
    assert launcher._resolve_project(str(alpha)) == (alpha, "11111111-1111-4111-8111-111111111111")

    # (2) AETHER_PROJECT_ROOT also outranks the current directory.
    monkeypatch.setenv("AETHER_PROJECT_ROOT", str(alpha))
    assert launcher._resolve_project(None) == (alpha, "11111111-1111-4111-8111-111111111111")

    # An empty or relative AETHER_PROJECT_ROOT is refused instead of falling back to cwd.
    monkeypatch.setenv("AETHER_PROJECT_ROOT", "")
    with pytest.raises(launcher.ActivationError, match="must not be empty"):
        launcher._resolve_project(None)
    monkeypatch.setenv("AETHER_PROJECT_ROOT", "relative/project")
    with pytest.raises(launcher.ActivationError, match="must be an absolute path"):
        launcher._resolve_project(None)
    monkeypatch.delenv("AETHER_PROJECT_ROOT")
    with pytest.raises(launcher.ActivationError, match="project path must not be empty"):
        launcher._resolve_project("")

    # (4) The current directory selects its own initialized project.
    assert launcher._resolve_project(None) == (beta, "22222222-2222-4222-8222-222222222222")

    # (3b) A relative --project PATH is resolved against the working directory (only
    # an empty value is refused), which is why the documented split names the exact
    # value that fails per surface. See the identity-split guidance oracle below.
    monkeypatch.chdir(tmp_path)
    assert launcher._resolve_project("alpha") == (alpha, "11111111-1111-4111-8111-111111111111")

    # (5) An uninitialized cwd never opens an unrelated registered project:
    # with several it reports ambiguous identity, and with one it gives actionable init guidance.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(launcher.ActivationError, match="ambiguous project identity"):
        launcher._resolve_project(None)

    solo_state = tmp_path / "solo_state"
    solo_registry = ProjectRegistry(root=solo_state / "aether")
    solo_proj = _initialized_project(
        tmp_path / "solo", "44444444-4444-4444-8444-444444444444", "solo"
    )
    solo_registry.register("44444444-4444-4444-8444-444444444444", solo_proj, "solo")
    monkeypatch.setenv("XDG_STATE_HOME", str(solo_state))
    with pytest.raises(launcher.ActivationError, match="run 'git init' and 'aether init'"):
        launcher._resolve_project(None)


def test_documented_launch_and_shell_default_guidance_states_the_implemented_behavior() -> None:
    guide = GETTING_STARTED.read_text(encoding="utf-8")
    for required in (
        "an explicit `--project PATH`",
        "`AETHER_PROJECT_ROOT` in the environment, which also takes precedence over the current directory",
        "a verified `AETHER_PROJECT_ID` whose project-registry entry and portable marker agree",
        "the current directory, or its nearest initialized parent directory",
        "never silently opens an unrelated registered project",
        "`ambiguous project identity`",
        "aether --project /path/to/project --resume latest",
        "`Aether` (fresh) and `Continue Aether` (`--resume latest`)",
        "never writes a personal shell preference",
        "~/.bashrc",
        "~/.zshrc",
        "unalias aether",
        "~/.config/fish/config.fish",
        "functions -e aether",
    ):
        assert required in guide, required

    # The optional project default is taught in its own right, with generic paths
    # and its matching removal command, next to the executable shortcut.
    shell_section = guide.split("### Optional personal shell defaults", 1)[1]
    shell_section = shell_section.split("\n## ", 1)[0]
    for required in (
        "takes precedence over the current directory",
        "export AETHER_PROJECT_ROOT='/path/to/an/initialized/project'",
        "unset AETHER_PROJECT_ROOT",
        "set -gx AETHER_PROJECT_ROOT /path/to/an/initialized/project",
        "set -e AETHER_PROJECT_ROOT",
        "never writes a personal shell preference",
        "alias aether='/path/to/aether/runtime/current/venv/bin/aether'",
        "/path/to/aether/runtime/current/venv/bin/aether $argv",
    ):
        assert required in shell_section, required
    assert "/home/" not in guide and "/Users/" not in guide

    # Aether itself never writes a personal shell preference: no product source
    # references a personal shell configuration file.
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "src").rglob("*.py"))
    )
    for fragment in (".bashrc", ".zshrc", "config.fish", "bash_profile", "profile.d"):
        assert fragment not in sources, fragment


def test_documented_recovery_surfaces_and_transient_codes_match_the_implementation() -> None:
    cli_reference = CLI_REFERENCE.read_text(encoding="utf-8")
    lifecycle = LIFECYCLE_GUIDE.read_text(encoding="utf-8")
    limitations = LIMITATIONS.read_text(encoding="utf-8")
    observation = OBSERVATION_GUIDE.read_text(encoding="utf-8")

    for required in (
        "aether reconcile --to active --json",
        "aether reconcile --to active --yes --json",
        "UNSUPPORTED_RECONCILE_MODE",
        "RECONCILE_REFUSED",
    ):
        assert required in cli_reference, required
    for required in (
        "aether doctor [--project PATH] [--json]",
        "aether reconcile --to active [--dry-run] [--yes] [--json]",
        "aether rollback [VERSION] [--dry-run] [--yes] [--json]",
    ):
        assert required in lifecycle, required

    # The recovery preamble must not deny the rollback surface's own release
    # switch, and it must keep the refusals that are true of all three surfaces.
    assert "None of them selects a different release" not in lifecycle
    for required in (
        "installs a package, acquires credentials, or rolls user state backward",
        "`aether rollback` is the one surface that selects a different release",
        "switches the product-owned runtime, launcher and service pointers",
        "or to the explicitly named one",
        "Observation journals, key epochs and other user state continue forward unchanged",
    ):
        assert required in lifecycle, required
    for required in ("STATE_BUSY", "CATCHUP_INCOMPLETE", "STATE_UNREADABLE"):
        assert required in observation, required
        assert required in limitations, required

    # The documented transient/unreadable codes are the ones the CLI actually emits.
    observe_source = (ROOT / "src/aether_agents/commands/observe.py").read_text(encoding="utf-8")
    for code in ("STATE_BUSY", "CATCHUP_INCOMPLETE", "STATE_UNREADABLE"):
        assert f'code="{code}"' in observe_source, code
    brief_source = (ROOT / "src/aether_agents/observation/brief.py").read_text(encoding="utf-8")
    for code in (
        "AETHER-OBSERVE-BUSY",
        "AETHER-OBSERVE-CATCHUP-INCOMPLETE",
        "AETHER-OBSERVE-STATE-UNREADABLE",
    ):
        assert f'"{code}"' in brief_source, code


def test_documented_identity_value_split_matches_the_implemented_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every identity surface states which value is refused and which is resolved."""

    surfaces = {
        "docs/getting-started.md": GETTING_STARTED.read_text(encoding="utf-8"),
        "docs/reference/cli.md": CLI_REFERENCE.read_text(encoding="utf-8"),
        "docs/capabilities.toml": CAPABILITY_REGISTRY.read_text(encoding="utf-8"),
        "docs/reference/capabilities.md": GENERATED_REFERENCE.read_text(encoding="utf-8"),
    }
    for name, text in surfaces.items():
        flat = text.replace("`", "")
        for required in (
            "an empty --project value is refused",
            "a relative --project PATH is resolved against the current working directory",
            "AETHER_PROJECT_ROOT must be an absolute path",
            "AETHER_PROJECT_ID must be a canonical UUID",
        ):
            assert required in flat, (name, required)
        assert "empty or relative identities fail visibly" not in flat, name

    # That split is the one the real resolver implements.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("AETHER_HERMES_ROOT", raising=False)
    monkeypatch.delenv("AETHER_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("AETHER_PROJECT_ID", raising=False)

    from aether_agents.observation.context import ProjectRegistry

    project_id = "11111111-1111-4111-8111-111111111111"
    project = _initialized_project(tmp_path / "alpha", project_id, "alpha")
    assert ProjectRegistry().register(project_id, project, "alpha")

    monkeypatch.chdir(tmp_path)
    # A relative --project PATH resolves against the working directory...
    assert launcher._resolve_project("alpha") == (project, project_id)
    # ...an empty --project value is refused...
    with pytest.raises(launcher.ActivationError, match="project path must not be empty"):
        launcher._resolve_project("")
    # ...and AETHER_PROJECT_ROOT must be absolute.
    monkeypatch.setenv("AETHER_PROJECT_ROOT", "relative/project")
    with pytest.raises(launcher.ActivationError, match="must be an absolute path"):
        launcher._resolve_project(None)
