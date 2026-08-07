# Aether Native Core Retirement Implementation Plan

> **Status:** HISTORICAL COMPLETED RETIREMENT PLAN. It proves removal of the
> disconnected native core and the deliberate absence of a replacement at that
> cut. ADR-0001 later approved a new bounded Aether MCP control/trace plane; this
> plan does not govern that proposed design. See
> `../../architecture/AETHER_MCP.md` and `ROADMAP.md`.

> **For Hermes:** Execute this plan through the current task contract; use `milestone-implementation-governance` for the atomic retirement and exact-candidate closure.
> **Status:** EXECUTED — LOCALLY VERIFIED

**Goal:** Remove the disconnected Aether-native Python core extracted from Olympus while preserving Aether's Hermes profiles, skills, configuration, operational tooling, historical evidence, and future Orca swarm boundary.

**Architecture:** Aether remains a product layer over Hermes Agent. Orca owns Run/Task/Dispatch, messages, workers, terminals, worktrees, recovery, and cleanup. This cut creates an explicit capability gap: it removes the unused native core and does not implement a replacement adapter.

**Tech Stack:** Hermes Agent configuration and profiles, Orca public CLI contract, Bash setup/update/gateway tooling, Python repository-governance tests, Git/GitHub.

---

## Authorized horizon and stop condition

This plan authorizes repository-only retirement, deterministic validation, atomic commits, feature-branch push, and issue reconciliation. It stops with a clean synchronized feature worktree. It does not authorize an Orca launch, worker pilot, service activation, PR, merge, tag, GitHub Release, deployment, data migration, credential change, or spending.

The task is complete when the exact commit contains no Aether runtime package or consumer, retained setup/config/release behavior passes, local historical stores are untouched, and current architecture documentation agrees with PDR-0012.

### Task 1: Freeze the corrected product boundary

**Objective:** Record Hermes-led Orca swarm ownership and supersede pre-emptive native-core retention.

**Files:**
- Create: `docs/decisions/PDR-0012-hermes-orca-swarm-boundary.md`
- Create: `docs/releases/v0.22.0/AETHER_NATIVE_CORE_RETIREMENT_PLAN.md`
- Modify: `docs/releases/v0.22.0/ROADMAP.md`
- Modify: `docs/releases/v0.22.0/STATUS.yaml`

**Acceptance:**
- Aether product authority is expressed through Hermes, profiles, skills, configuration, and decisions.
- Orca owns operational swarm mechanics.
- One feature branch is the integration line; child worktrees isolate potentially conflicting writers.
- The removal cut explicitly does not implement a replacement.

### Task 2: Add the removal contract and observe RED

**Objective:** Prove the current candidate still retains disconnected runtime surfaces.

**Files:**
- Modify: `tests/test_post_olympus_residue_retirement.py`
- Modify: `tests/test_setup_script.py`

**RED assertions:**
- `src/aether_agents` and all six profile Aether plugins are absent.
- profile templates do not enable the plugin.
- `pyproject.toml` is tooling-only and has no build system, project package, or `aiosqlite`.
- setup/update/doctor and CI do not install, import, lint, compile, build, or publish an Aether package.
- current entry documentation does not advertise the removed native core.

**Run:**

```bash
python -m pytest -q tests/test_post_olympus_residue_retirement.py tests/test_setup_script.py
```

**Expected RED:** failures identify the still-present package, plugins, dependency/install/build consumers, and documentation claims.

### Task 3: Retire source, wrappers, and implementation-only tests

**Objective:** Delete the extracted native core and tests that exist only to preserve it.

**Delete:**
- `src/aether_agents/`
- `home/profiles/*/plugins/aether/`
- native identity/continuity/contract/budget/evidence/effects/review/self-improvement tests
- retired coordination test package

**Preserve:**
- `.aether` and every local/historical database byte;
- release history and historical evidence;
- setup/release/removal regression tests;
- benchmark scripts and skill utilities unrelated to the retired runtime.

**Acceptance:** no production consumer imports `aether_agents`; no active profile initializes an Aether plugin.

### Task 4: Convert packaging and operations to a content/config product

**Objective:** Stop installing or publishing an empty Python runtime while retaining useful repository tooling.

**Files:**
- Modify: `pyproject.toml` to retain only pytest/Ruff configuration; remove `[build-system]` and `[project]`.
- Create: `VERSION` as the product SemVer authority.
- Modify: `scripts/setup.sh` to install Hermes only and validate profiles/configuration instead of the Aether import.
- Modify: `scripts/update.sh` to upgrade Hermes and regenerate the root plus six profile configs without reinstalling Aether.
- Modify: `Makefile` doctor to validate Hermes, templates, profile count, and resolved generated configuration.
- Modify: `scripts/check_release_governance.py` to read `VERSION` and stop inspecting package dependencies.
- Modify: `.github/workflows/test.yml`, `.github/workflows/release.yml`, and release policy tests to validate a content/config/tooling repository without building Python artifacts.

**Acceptance:** disposable two-pass setup produces seven parseable configs, preserves them on rerun, and doctor proves the candidate-local Hermes installation without importing project code.

### Task 5: Reconcile current-facing product documentation

**Objective:** Remove claims that the extracted native core remains part of the current architecture.

**Files:**
- Modify: `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Modify: current product/knowledge/guides/index documents with active native-core claims
- Modify: `website/index.html` and any current website surface that advertises the package
- Amend current v0.22.0 roadmap/status/inventory/matrix with a superseding retirement record
- Preserve earlier PDRs, releases, benchmarks, and closeouts as historical truth

**Acceptance:** current docs describe the Hermes + Orca target, explicit capability gap, and protected historical stores without claiming a live swarm or adapter.

### Task 6: Verify and version the exact candidate

**Objective:** Prove the retirement and leave a reproducible handoff.

**Gates:**

1. focused removal/setup/release tests;
2. full remaining suite;
3. Ruff over retained Python tests/scripts;
4. `compileall` over retained Python tests/scripts;
5. Bash syntax for all retained shell scripts;
6. parse every YAML/YAML template;
7. current Markdown link check;
8. static scan for `aether_agents`, ACP/Olympus executable consumers, profile plugin activation, editable install, package build, and `aiosqlite`;
9. disposable two-pass setup plus candidate-local doctor;
10. verify `.aether` fingerprints unchanged;
11. `git diff --check`, staged path/secret review, atomic commit, push, remote synchronization, and clean worktree.

**Expected result:** PDR-0012 and #160 are implemented on the feature branch; Orca runtime integration remains the next separately gated horizon.
