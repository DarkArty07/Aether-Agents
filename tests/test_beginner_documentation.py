from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs"


REQUIRED_PAGES = (
    "docs/start-here.md",
    "docs/guides/first-objective.md",
    "docs/reference/glossary.md",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _links(markdown: str) -> list[str]:
    return [match.group(1).split(maxsplit=1)[0].strip("<>") for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", markdown)]


def test_beginner_pages_exist_with_decided_slugs_and_titles() -> None:
    for relative in REQUIRED_PAGES:
        page = ROOT / relative
        assert page.is_file(), relative
        assert re.search(r"^#\s+\S", page.read_text(encoding="utf-8"), re.MULTILINE), relative


def test_index_exposes_one_ordered_beginner_journey_and_all_canonical_pages() -> None:
    index = _read("docs/index.md")
    groups = ("Start here", "Core concepts", "Working with Aether", "Operations and safety", "Reference")
    positions = [index.index(f"## {group}") for group in groups]
    assert positions == sorted(positions)
    assert "docs/index/" not in index
    assert "[Start here](start-here.md)" in index

    expected = {
        "start-here.md",
        "getting-started.md",
        "product-boundary.md",
        "roles-and-authority.md",
        "authority.md",
        "guides/project-initialization.md",
        "guides/objective-contracts.md",
        "guides/first-objective.md",
        "guides/execution.md",
        "guides/lifecycle.md",
        "guides/project-knowledge.md",
        "guides/observation.md",
        "guides/policy-and-recovery.md",
        "reference/cli.md",
        "reference/plugins-and-tools.md",
        "reference/limitations-and-troubleshooting.md",
        "reference/capabilities.md",
        "reference/glossary.md",
    }
    linked = {link.removeprefix("docs/").split("#", 1)[0] for link in _links(index) if link.endswith(".md")}
    assert expected <= linked


def test_getting_started_puts_prerequisites_before_provider_free_commands() -> None:
    page = _read("docs/getting-started.md")
    prerequisite = page.index("## Prerequisites")
    first_command = page.index("uv run --frozen aether --version")
    assert prerequisite < first_command
    for term in (
        "provider-free source checkout",
        "stabilization build",
        "not a public release",
        "uv run --frozen aether --help",
        "uv run --frozen aether observe --help",
        "existing Git repository root",
        "exact-path",
        "native Hermes Project",
        "Hermes Agent",
    ):
        assert term.lower() in page.lower(), term
    assert "## Next step" in page


def test_first_objective_is_non_normative_and_covers_both_routes() -> None:
    page = _read("docs/guides/first-objective.md")
    lower = page.lower()
    assert "illustrative" in lower
    assert "non-normative" in lower
    assert "provider-backed execution" in lower
    ordered_sections = (
        "## 1. Owner intake",
        "## 2. Morfeo confirms scope and chooses a route",
        "## 3. Objective Contract when the pipeline requires one",
        "## 4. Supervisor prepares the board",
        "## 5. Implementers work in isolated worktrees",
        "## 6. Independent review and evidence",
        "## 7. GitHub-backed closeout and terminal reporting",
    )
    positions = [lower.index(section.lower()) for section in ordered_sections]
    assert positions == sorted(positions)
    for term in (
        "morfeo",
        "route",
        "objective contract",
        "supervisor",
        "board",
        "worktree",
        "implementer",
        "independent review",
        "evidence",
        "github",
        "terminal",
        "direct",
        "pipeline",
    ):
        assert term in lower, term
    assert "## Next step" in page


def test_glossary_defines_beginner_terms_and_points_to_detail() -> None:
    page = _read("docs/reference/glossary.md")
    lower = page.lower()
    for term in (
        "aether",
        "owner",
        "morfeo",
        "supervisor",
        "implementer",
        "objective contract",
        "direct route",
        "pipeline",
        "worktree",
        "evidence",
        "capability registry",
        "stabilization build",
        "provider-free",
    ):
        assert term in lower, term
    assert "docs/start-here.md" not in page
    assert "## Next step" in page


def test_new_content_has_current_intended_and_safety_boundaries() -> None:
    start = _read("docs/start-here.md").lower()
    walkthrough = _read("docs/guides/first-objective.md").lower()
    for phrase in (
        "implemented",
        "partial",
        "transitional",
        "unsupported",
        "intended",
        "historical",
        "provider-free",
        "credentials",
        "not a public release",
    ):
        assert phrase in start or phrase in walkthrough, phrase
    combined = start + "\n" + walkthrough
    assert "/home/" not in combined
    assert "api key" not in combined
    assert "private profile" in combined
    assert "do not" in combined


def test_reader_pages_offer_role_route_and_next_step_orientation() -> None:
    start = _read("docs/start-here.md").lower()
    for term in ("owner", "morfeo", "supervisor", "implementer", "direct route", "pipeline route"):
        assert term in start, term
    pages = (
        "docs/start-here.md",
        "docs/getting-started.md",
        "docs/guides/first-objective.md",
        "docs/guides/project-initialization.md",
        "docs/guides/objective-contracts.md",
        "docs/guides/execution.md",
        "docs/guides/lifecycle.md",
        "docs/guides/project-knowledge.md",
        "docs/guides/observation.md",
        "docs/guides/policy-and-recovery.md",
        "docs/reference/glossary.md",
        "docs/reference/cli.md",
        "docs/reference/plugins-and-tools.md",
        "docs/reference/limitations-and-troubleshooting.md",
    )
    for relative in pages:
        assert "## Next step" in _read(relative), relative


def test_canonical_relative_links_resolve_from_their_source_pages() -> None:
    for page in sorted(DOCS.rglob("*.md")):
        markdown = page.read_text(encoding="utf-8")
        for href in _links(markdown):
            if not href or href.startswith(("#", "http:", "https:", "mailto:")):
                continue
            target_text, _, _fragment = unquote(href).partition("#")
            target = page if not target_text else (page.parent / target_text)
            assert target.exists(), f"{page.relative_to(ROOT)} -> {href}"


def test_landing_copy_labels_intended_scope_without_claiming_current_greenfield_pipeline() -> None:
    copy = _read("website/src/data/content.ts").lower()
    for phrase in (
        "intended",
        "current build",
        "provider-free",
        "not a public release",
        "not release-qualified",
        "existing git repository",
        "exact-path",
    ):
        assert phrase in copy, phrase
    assert "the current build creates a project from scratch" not in copy
    assert "aether runs the complete pipeline today" not in copy
    assert "aether executes the pipeline" not in copy
