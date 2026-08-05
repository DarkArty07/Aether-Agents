# Post-Olympus Residue Cleanup Implementation Plan

> **For Hermes:** Execute this plan through the current task contract; use `milestone-implementation-governance` for the atomic implementation and closure gate.
> **Status:** EXECUTED — LOCALLY VERIFIED

**Goal:** Remove the remaining active Honcho and Graphify installation surfaces and make every current-facing product document agree that Olympus/Harmonia are historical and that multi-agent execution is unavailable in the v0.22.0 candidate.

**Architecture:** This is a deletion-dominant candidate cleanup after the Aether-native extraction. Active configuration, setup, operational skills, and current documentation move to Hermes-native memory and the already-established capability gap. Two clean-install defects discovered by the gate are corrected without adding a runtime. Historical decisions, releases, benchmarks, stores, and the ACP V1 evidence decoder remain untouched.

**Tech Stack:** Python 3.11, pytest, Ruff, Bash, YAML, setuptools/uv, Git/GitHub.

---

## Task 1: Freeze executable absence contracts

**Objective:** Add tests that fail on the current Honcho, Graphify, and stale current-documentation surfaces.

**Files:**
- Create: `tests/test_post_olympus_residue_retirement.py`
- Read: `tests/test_olympus_package_retirement.py`
- Read: `tests/test_setup_script.py`

**Steps:**
1. Assert the Honcho submodule, Compose stack, setup script, active setup documentation, and Aether-specific skill reference are absent.
2. Assert the Graphify provider file and enabled MCP template block are absent.
3. Assert setup/config templates contain only supported machine placeholders and no retired installation commands.
4. Assert current-facing product/knowledge/contributor documents do not advertise removed tools or current Olympus/Harmonia lifecycle ownership.
5. Run the focused file and preserve the expected RED failures.

**Gate:** Focused tests fail only because the enumerated residue still exists.

## Task 2: Retire Honcho and Graphify installation surfaces

**Objective:** Remove zero-consumer external runtime artifacts without touching local services, credentials, or historical data.

**Files:**
- Delete: `.gitmodules`
- Delete: `honcho-server` gitlink
- Delete: `docker-compose.yml`
- Delete: `scripts/setup-honcho.sh`
- Delete: `docs/honcho-setup.md`
- Delete: `home/skills/autonomous-ai-agents/hermes-agent/references/honcho-integration.md`
- Delete: `.graphify/providers.json`
- Modify: `scripts/setup.sh`
- Modify: `Makefile`
- Modify: `home/config.yaml.template`
- Modify: `home/skills/autonomous-ai-agents/hermes-agent/SKILL.md`

**Steps:**
1. Remove normal-setup submodule initialization and Honcho Make targets.
2. Keep Hermes built-in `MEMORY.md`/`USER.md` enabled while removing `memory.provider: honcho`.
3. Remove the unsupported Graphify MCP block and unresolved `__PYTHON_BIN__` placeholder.
4. Remove active operational skill guidance while preserving ignore rules for any local historical runtime data that must never be committed.
5. Run focused tests, setup shell syntax, template YAML parsing, and a residual active-surface scan.
6. Generate the root Hermes config as well as all six profile configs and preserve configured files on rerun (#157).
7. Make doctor prefer the local Hermes installation and remove inherited Python source overrides (#158).

**Gate:** No supported setup/config/skill path can initialize or advertise Honcho or Graphify.

## Task 3: Reconcile current product truth

**Objective:** Apply PDR-0011 and the completed Honcho retirement to current-facing documentation while preserving historical evidence.

**Files:**
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/product/{README,VISION,MISSION,OBJECTIVES,SCOPE,PRINCIPLES,EXPERIENCE}.md`
- Modify: `docs/knowledge/{README,AUTHORITY,MULTI_AGENT_MODEL,HERMES_LEARNING_MODEL}.md`
- Modify: `docs/guides/USER_PROFILE.md`
- Modify: `docs/architecture/README.md`
- Modify: `docs/reference/README.md`
- Modify: `docs/contributing/README.md`

**Steps:**
1. Replace current Olympus/Harmonia ownership with substrate-neutral Aether authority and an explicit no-runtime capability gap.
2. Mark `MULTI_AGENT_MODEL.md` as a historical v0.19 model superseded for runtime selection by PDR-0011.
3. Change Honcho migration-pending claims to completed source/config retirement; keep PDR-0006 as historical rationale.
4. Remove obsolete Olympus planned-document rows and removed command/tool instructions.
5. Validate current Markdown links and the documentation regression.

**Gate:** Current docs agree on the v0.22 boundary; historical release and decision evidence remains byte-preserved.

## Task 4: Record exact candidate evidence

**Objective:** Update the v0.22 status and roadmap with the post-retirement cleanup result.

**Files:**
- Modify: `docs/releases/v0.22.0/STATUS.yaml`
- Modify: `docs/releases/v0.22.0/ROADMAP.md`
- Modify: this plan

**Steps:**
1. Record issues #154, #155, #156, #157, and #158 and the exact removed or corrected surfaces.
2. Record RED/GREEN, full-suite, lint, compile, archive, clean-install, setup, and doctor evidence only after execution.
3. Keep M2, Orca activation, Evidence Identity V2, runtime migration, and release outside this cut.

**Gate:** Versioned evidence matches real executed commands and the final Git tree.

## Task 5: Verify and version the atomic cut

**Objective:** Prove the exact candidate, commit it, publish the feature branch, and leave no dirty worktree state.

**Steps:**
1. Run focused retirement/setup tests.
2. Run the complete pytest suite, Ruff, compileall, Bash/YAML parsing, release-governance policy, and residual scans.
3. Build wheel and sdist; inspect dependencies, entries, and entry points.
4. Install the exact wheel in an empty venv and execute a native Aether operation.
5. Run disposable isolated setup twice, generated-config scan, wrapper smoke, and doctor without Honcho or Graphify.
6. Review intended paths, diff integrity, and staged secret scan.
7. Commit with an English conventional subject that closes #154, #155, #156, #157, and #158; push the feature branch.
8. Verify `git status --short` is empty.

**Stop condition:** The feature branch contains one verified atomic post-Olympus cleanup commit, the remote branch is synchronized, issues are linked for closure, and the local worktree is clean. PR merge, tag, GitHub Release, Orca activation, deployment, service restart, historical-store mutation, and credential changes are not part of this cut.

## Rollback

The exact source rollback is candidate predecessor `f53168aff645020607a63f8a70f1c109081a91b2`. No running Honcho service, Docker volume, local Honcho data, Graphify process, credential, or historical database is stopped, deleted, or modified by this source-only plan.

## Executed evidence

- Retirement contract: 8 expected RED failures, then GREEN.
- Setup root-config regression: expected RED, then GREEN.
- Doctor local-precedence and inherited-environment regressions: expected RED, then GREEN.
- Focused retirement/setup gate: 19 passed.
- Repository suite: 239 passed.
- Ruff and compileall: pass.
- Bash syntax and seven YAML templates/placeholders: pass.
- Current Markdown links: 48 checked, 0 broken.
- Active operational surfaces: 0 Honcho/Graphify consumers across the enumerated setup/config/skill boundary.
- Distribution: 20-entry wheel and 49-entry sdist; 0 retired executable source entries, 0 console entry points, and 2 intentional retirement-contract tests in the sdist.
- Clean wheel installation: pass with only the declared `aiosqlite` runtime dependency.
- Isolated setup: two passes, one root plus six profile configs, all placeholders resolved, all seven configs preserved on rerun.
- Isolated doctor: pass against the temporary pip installation; no fallback to the developer's global Hermes checkout.
- Runtime/service/data effects: none.
