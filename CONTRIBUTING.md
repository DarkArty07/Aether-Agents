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

### Owner-directed instruction maintenance (#541)

For the portable-methodology, expected-behavior documentation and `aether-plan`
rename objective, the owner explicitly selects direct Morfeo work and diff/reference
inspection only. Do not run test suites, builds, linters, extra validation campaigns
or CI for this local maintenance. The scope includes the minimal resource-name and
test-expectation reconciliation required by the rename, not new execution machinery.
Report all unexecuted checks honestly; this is not runtime or agent-behavior qualification.

This objective-specific instruction supersedes the execution of the checks listed
below for this local delivery only. It does not disable a workflow, change repository
protection, authorize a bypass, or permit push, merge, publication or runtime adoption.
Other objectives retain their existing verification obligations. The owning amendment
is in `specs/r2-contract-and-handoff/spec.md`.

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

Run focused tests while iterating. Pull requests use Python 3.11 as the primary
development lane, while Python 3.12 and 3.13 run a lightweight compatibility smoke for
ordinary code changes. Expensive domain qualification is selected by changed paths, and
every push to `main` still runs the exhaustive three-version qualification matrix. Run
the full bootstrap locally before handoff when the change touches a release/lifecycle,
observation, knowledge/Graphify, Hermes-baseline, or CI-policy boundary; ordinary scoped
changes may rely on the focused tests plus the PR development lane. Do not remove, skip,
or weaken a test merely to obtain a green result.

Kanban fixtures must isolate dispatcher routing and execution identity, not only
`HERMES_HOME`: inherited `HERMES_KANBAN_*` variables can still select the worker's live
board or workspace. Use a scoped environment change with temporary destinations and
verify that the outer board is unchanged. Subprocess probes use only the minimal test-only
isolation support in `tests/runtime_isolation.py`; never test isolation against a live
board.

### RC17 bounded release verification (#542)

The owner separately authorizes RC17 source integration and one local managed cutover.
Reuse reviewed fixes and their attributed evidence; run focused resource/name/old-reader
checks and normal package preparation, followed by one post-cutover coherence check.
Do not repeat the full suite locally before required PR checks, add agent campaigns,
stress loops or a live rollback rehearsal. A required check failure still needs concrete
diagnosis; this direction neither disables CI nor permits a protected-check bypass.
The #541 no-test instruction continues to describe that earlier local source delivery,
not this separately authorized release. Keep its evidence attribution unchanged.

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

For policy-hook changes, also run the focused policy suite. Packaged launcher tests
import `aether_agents` and belong on the exact-Hermes pytest lane, not the stdlib-only
hook check:

```bash
uv run --frozen python -m unittest discover -s tests -p 'test_policy_hooks.py' -v
uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -q
```

Use the repository runner for exact-Hermes integration coverage even if the ordinary
focused test or coverage command passes. The committed configuration enforces the
current coverage floor; do not lower it to make a contribution pass.

### CI tiers

Repository Policy deliberately separates iteration speed from release confidence:

- **Ordinary pull requests:** Python 3.11 runs the full exact-Hermes test suite without
  the expensive observation performance/coverage qualification; Python 3.12 and 3.13
  compile/import the changed code as compatibility smoke checks. Static, documentation,
  build and public-artifact checks run once on the primary lane where applicable.
- **Sensitive pull requests:** changes to lifecycle/release identity, observation,
  knowledge/Graphify, or Hermes-baseline inputs retain their deeper qualification on the
  Python 3.11 primary lane; Python 3.12 and 3.13 stay compatibility smoke lanes. A
  policy-workflow change is the exception: it self-qualifies through the old exhaustive
  three-version behavior before the faster policy can land.
- **`main`:** every integrated change runs the exhaustive Python 3.11/3.12/3.13
  qualification, integrated coverage, observation performance evidence, build and
  public-artifact checks. A faster PR therefore moves some detection later to `main`;
  it does not remove the final qualification boundary.

Superseded pull-request runs are cancelled when a newer commit is pushed to the same PR.
Main-branch qualification runs are never cancelled by this concurrency rule.
Adding tracked files to the repository manifest does not by itself count as a CI-logic
change, and static Python checks target the complete `src/aether_agents`, `tests`, and
`scripts` trees so a new script does not require another hand-maintained Ruff/compile list.
The authenticated public Hermes baseline checkout is cached by its versioned baseline
resource identity. A restored checkout is re-verified locally before reuse; only a stale
or incomplete cache entry performs a network refresh, so caching never substitutes for
the exact tag-object/commit gate.

## Prepare a contribution

### Documentation impact

A change to a meaningful agent expectation must reconcile
`docs/guides/expected-behavior.md` in the same change, or state why no entry is affected.
That guide explains triggers, limits, sources and observable signs; it is not another
authority, capability registry or record of behavioral PASS. Preserve the distinction
between source instructions, installed instructions and observed conduct.

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
