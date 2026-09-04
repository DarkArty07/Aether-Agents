# Contributing

Thank you for improving Aether Agents. Keep every contribution within the versioned
design, the owning specification or contract, repository policy, and the current
authority for the effect being performed. A design or test result is not authority to
activate a runtime, acquire credentials, publish, deploy, or release.

## Prerequisites

- Git and [uv](https://docs.astral.sh/uv/) must be available.
- Use a Python version supported by `pyproject.toml` (currently 3.11 through 3.13).
- Do not place credentials, local profile state, databases, sessions, memories, logs,
  caches, machine-specific paths, or generated runtime material under version control.

## Start from a fresh clone

Run the following from a new clone. `uv sync --frozen` creates the locked development
environment without changing the lockfile.

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
uv sync --frozen
```

Read `AGENTS.md` before designing or changing an area. Then read `README.md`,
[`docs/authority.md`](docs/authority.md), `DESIGN.md`, `ROADMAP.md`, and the relevant
material under `specs/`. `CLAUDE.md` adds guidance for coding assistants but does not
replace these repository rules.

## Test with the locked Hermes baseline

The full exact-Hermes suite is run through the repository bootstrap. It recreates and
verifies the selected public Hermes source and supplies it to the tests, so do not set
`PYTHONPATH` by hand:

```bash
uv run --frozen python scripts/run_tests.py
```

The initial run needs network access to obtain the selected public source. A focused
test that does not need the exact-Hermes fixture can run directly; replace the example
with the narrowest relevant test path or node:

```bash
uv run --frozen pytest -q tests/test_objective_contracts.py
```

Run focused tests while iterating and the full bootstrap before handoff. Do not remove,
skip, or weaken a test to obtain a green result.

## Quality checks

Run the checks relevant to every changed Python path. The examples below cover the
repository's Python source, tests, and scripts:

```bash
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen pytest -q --cov=aether_agents --cov-report=term-missing
uv build
```

Apply formatting only when you intend to modify files, then rerun the format check and
inspect the resulting diff:

```bash
uv run --frozen ruff format src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
```

For policy-hook changes, also run the focused policy and launcher suites:

```bash
uv run --frozen python -m unittest discover -s tests -p 'test_policy_hooks.py' -v
uv run --frozen python -m unittest discover -s tests -p 'test_aether_tui_launcher.py' -v
```

Use the repository runner for exact-Hermes integration coverage even if the ordinary
focused test or coverage command passes. The committed configuration enforces the
current coverage floor; do not lower it to make a contribution pass.

## Prepare a contribution

### Documentation impact

A change to a public or user-visible surface must update the applicable current page and
`docs/capabilities.toml`, including its generated reference. If no update is applicable,
provide a specific non-applicability rationale in the pull request. Behavior-preserving internal refactors
do not require ceremonial documentation churn. Before handing off a change that updates
the registry or current pages, run:

```bash
uv run --frozen python scripts/check_documentation.py
```

1. Make one scoped change and update the artifact that owns any decision before updating
   a derived artifact (see [`docs/authority.md`](docs/authority.md) for artifact ownership and conflict rules). Canonical documentation and durable system prompts are English.
2. Keep `ROADMAP.md` shallow; detailed stage material belongs under `specs/<stage>/`.
3. Check Markdown links, YAML, file modes, and the complete diff. For a change intended
   for commit, run:

   ```bash
   git diff --check
   git diff --cached --check
   git status --short
   ```

4. Review the staged diff for local runtime state and unrelated changes. Record the
   commands actually run, their results, and remaining material risk.
5. Create one logical commit with a Conventional Commit message. Follow
   [the pull-request template](.github/PULL_REQUEST_TEMPLATE.md) when opening a pull
   request, including validation and manifest evidence.

## Canonical skills

Aether Canonical Skills are public, versioned, package-owned resources under
`src/aether_agents/resources/skills/<skill-name>/SKILL.md`. Project Canonical Skills are
tracked and portable under `.aether/skills/<skill-name>/SKILL.md`; root `AGENTS.md` is
the discovery pointer, and agents read applicable files directly from the project
worktree. Learned Profile Skills remain private, local, adaptive, and non-canonical.

Skills own reusable procedure only. They are subordinate to owner instruction, the
constitution, `DESIGN.md`, stage specifications, Objective Contracts, repository rules,
and protected-effect policy; they cannot grant authority. A learned procedure may enter
versioned source only after sanitization, generalization, focused verification,
independent review, commit, and pull request. Do not copy private skill text, identities,
machine paths, runtime state, providers, models, repository details, or credentials.

## External effects

Remote pushes, pull requests, merges, tags, publication, release, and deployment are
external effects. Perform them only when the current task and repository authority
permit them; this guide does not grant that authority.

## Maintain the repository

- Keep `pyproject.toml` and `uv.lock` consistent. When a dependency change is in scope,
  regenerate the lockfile deliberately and confirm `uv sync --frozen` succeeds.
- If a change affects policy, canonical manifests, packaging, or public artifacts, read
  the corresponding checks in `.github/workflows/policy.yml` and run the applicable
  local commands before handoff.
- Preserve accepted decisions and historical evidence. Update an owning artifact when a
  decision changes; do not silently rewrite history or treat local runtime state as
  documentation.
- Report security issues privately as described in `SECURITY.md`, without committing
  sensitive material.
