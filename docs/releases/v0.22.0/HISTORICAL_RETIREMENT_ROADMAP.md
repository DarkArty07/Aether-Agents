# Historical v0.22.0 Olympus Retirement Roadmap

> **Status:** HISTORICAL — superseded by `ROADMAP.md`
> **Date:** 2026-08-06
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `PDR-0012`, `PDR-0013` (preserving the applicable retirement and data-safety clauses of `PDR-0011`)

> **Supersession:** This file preserves the detailed source-retirement sequence,
> intermediate native-core work, and superseded Orca adapter proposals. The
> current v0.22.0 scope, milestones, acceptance gates, and stop conditions are in
> `ROADMAP.md`. Nothing below authorizes restoration of Olympus, Harmonia, the
> kernel, ACPManager, the disconnected Python core, or a broad adapter facade.

## 1. Outcome

v0.22.0 physically retires Olympus and the disconnected Python core that was
extracted from it before replacement-runtime work continues. Aether remains the
Hermes product layer—vision, profiles, policies, skills, routing judgment and
semantic acceptance—while Orca is the intended owner of Run, Task, Dispatch,
worker, message, worktree, recovery and cleanup mechanics. Multi-agent execution
remains unavailable until the Hermes-led Orca swarm path passes its separate gates.

The roadmap completes when the exact v0.22.0 candidate has:

- no active runtime, import, entry point, plugin, template, or current-facing documentation dependency on `olympus_v3`;
- no disconnected `aether_agents` runtime package, profile plugin, editable install or package-build surface;
- preserved Aether product authority in Hermes, product decisions, profiles, skills and acceptance policy;
- preserved local continuity and self-improvement stores without an active writer or destructive migration;
- proven Orca lifecycle, recovery, isolation and cleanup on the affected equivalence class;
- preserved read-only historical evidence and rollback;
- passed focused and full regression gates.

It does not include production activation, deployment, credentials, destructive data migration, or automatic release.

## 2. Non-negotiable invariants

Every milestone must preserve:

1. Aether remains the product layer; it does not duplicate Orca runtime state.
2. Hermes owns product intent, task decomposition, routing, supervision, synthesis and semantic acceptance.
3. Orca owns Run/Task/Dispatch, worker, terminal, worktree, message, recovery and cleanup mechanics.
4. Every operation binds to one canonical `PROJECT_ROOT` and approved profile.
5. Technical worker completion remains distinct from semantic acceptance.
6. A failed or stopped worker is not proof of cleanup.
7. Historical release evidence is not rewritten.
8. `.aether/aether.db`, `CONTEXT.md`, and self-improvement evidence are not destroyed or silently migrated.
9. There is no hidden ACP/Olympus fallback after a consumer switches to Orca.
10. The implementation tree remains independently reversible until final acceptance.

## 3. Baseline and sequencing truth

- Latest official release: `v0.20.0`.
- Canonical source baseline: `main@2b326f05a36cbb77a9bf9475ef914be6f49d886d`.
- Current documentation worktree: `feature/v0.22.0-orca-transition@99653b2e1c9c` before the uncommitted design-only diff.
- The stale `docs/canonical-product-documentation@a88b5cc` worktree remains separate and untouched by this design cut.
- Post-v0.20 candidate-isolation/promotion work is already integrated on `main`.
- No v0.21.x tag or GitHub Release was found during analysis.
- The product owner delegated the release-identity decision on 2026-08-06. The existing approved candidate identity remains v0.22.0; no renumbering to v0.21.0 is planned.
- Orca CLI is installed. Analysis began with no runtime; M0 now uses a dedicated
  headless runtime with pairing disabled and state isolated under `.aether/orca-v022/`.

No implementation milestone may begin from the stale documentation worktree or from this design-only authorization.

### 3.1 Current post-retirement sequence

PDR-0012 superseded the pre-emptive native-core and broad adapter design. PDR-0013
now fixes the target roster before runtime work. The current sequence is:

| Gate | Scope | Current state |
|---|---|---|
| D0 | Approve stable archetypes, participation states, communication, and Hermes–Orca operating model | direction approved; document review pending |
| D1 | Specify exact physical retirement cut for Athena and Etalides and the conditional Ariadna boundary | designed; repository mutation not authorized |
| P0 | Prove isolated Orca cold start, restart, stop, rollback, and zero survivors | blocked / not started |
| P1 | Prove one profile-bound Hermes worker with explicit `HERMES_HOME`, one Task, one Dispatch, question/reply, evidence, and cleanup | not started |
| P2 | Prove two parallel workers, independent scopes/worktrees, direct messaging, retry lineage, integration, and cleanup | not started |
| P3 | Design, implement, and benchmark the Independent Verifier; separately evaluate Ariadna utility | role design only |
| A0 | Accept the exact candidate, integrate, and consider release; activation remains a separate gate | not started |

The canonical target documents are:

- `docs/architecture/DAIMONS.md`;
- `docs/architecture/ORCHESTRATION.md`;
- `docs/decisions/PDR-0013-swarm-roster-and-personality-model.md`.

The detailed M2–M5 proposals below predate PDR-0012/PDR-0013 and are retained as
historical design evidence. They are not implementation authority. Any future
Orca integration starts from gates P0–P2 and introduces only the smallest seam
required by observed public Orca behavior.

## 4. Milestone M0 — Exact candidate isolation and baseline

### Goal

Create a clean, reproducible v0.22.0 candidate from canonical `main` without disturbing the current dirty documentation worktree.

### Actions

1. Re-fetch and verify `origin/main` and the exact baseline commit.
2. Reconcile or land the canonical documentation work before selecting the candidate tree.
3. Create a disposable v0.22.0 worktree/branch from the approved baseline using the existing candidate-isolation mechanism.
4. Record:
   - commit;
   - clean dirty-set digest;
   - Python and dependency lock/environment identity;
   - full test, Ruff, compile and build baseline;
   - source/module/import counts;
   - Orca AppImage path, digest and runtime state.
5. Resolve or fail closed on GitHub #147: `hot_state.project_root` currently names a nonexistent legacy root and must not become adapter authority.
6. Add removal-contract tests that fail if already retired experiments or future deleted modules reappear.
7. Freeze Olympus: only migration compatibility or migration-blocking fixes may touch it.

### Current evidence

- release-governance preflight: `PASS` on synchronized `main`;
- Orca-managed top-level worktree:
  `/home/darkarty/orca/workspaces/aether/feature-v0.22.0-orca-transition`;
- branch: `feature/v0.22.0-orca-transition` from `origin/main@2b326f0`;
- clean baseline initially exposed GitHub #148: the concurrent close test failed
  with `ValueError: INVALID_INPUT`;
- bounded baseline-compatibility correction: `a67f7ca`;
- post-correction evidence: exact regression `PASS`, repeated race `10/10`,
  lifecycle file `64 passed`, full suite `826 passed`;
- remaining M0 blocker: continuity identity issue #147.

### Acceptance

- clean candidate worktree;
- exact baseline commit and digest recorded;
- full existing suite green in the isolated tree;
- current dirty work preserved unchanged;
- candidate can be discarded without affecting `main` or `.aether`.

### Rollback

Discard the candidate worktree and branch, stop the dedicated headless runtime,
and remove only `.aether/orca-v022/`. Production/runtime data and historical
continuity stores remain unchanged.

## 5. Historical milestone M1 — Extract the Aether-native core (superseded)

> **Disposition (2026-08-05):** The extraction was completed and verified as
> recorded below, but PDR-0012 determined that the resulting package has no
> production consumer in the Hermes-led Orca swarm target. Its implementation is
> being retired under #160. The following text remains historical evidence and is
> not the current target architecture.

### Goal

Move every Aether-owned capability out of the Olympus namespace before replacing lifecycle.

### Proposed package boundary

```text
src/aether_agents/
  identity.py
  contracts/
  continuity/
  evidence/
  effects/
  review/
  self_improvement/
  ariadna/
  orca/
  mcp/
  cli/
```

The final module split may be refined, but lifecycle-independent imports and public contracts must be established before deletion.

### M1.1 Continuity extraction

- move `aether_db.py` and `aether_hooks` behavior;
- preserve the `.aether/aether.db` schema and path;
- replace Olympus PID/session lookup with explicit Aether session/project binding;
- keep hot-start, file-change, issue, decision, task and session behavior;
- retain `CONTEXT.md` read/validation semantics.

**Gate:** existing continuity tests pass against the new package and a byte-preserving test fixture; no Olympus DB read is required for session summaries.

**Prerequisite status (M1.1a): LOCALLY VERIFIED.** `aether_agents.identity`
now binds canonical existing project roots, separate profile homes, explicit
`live`/`synthetic` execution domains and project allowlists. Path-bound DTOs
reject forged digests. Continuity hooks treat a persisted `project_root` only as
an assertion: the known stale value remains untouched, but cannot become current
authority or drive path relativization. The focused gate passes `94/94` and the
full suite passes `414/414`.

**Candidate status (M1.1b): LOCALLY VERIFIED.** The DB and hook implementation
was moved without legacy copies into `aether_agents.continuity`. Six profile
plugin wrappers now delegate to the native package. Hooks bind the explicit
event `session_id` and optional `result_summary`; they no longer read Olympus
PID/session files or `olympus_v3.db`. Schema, `.aether/aether.db` path and
`CONTEXT.md` behavior remain unchanged. A read-only reopen preserves the exact
database bytes, the focused continuity gate passes `91/91`, and the full suite
passes `417/417`.

### M1.2 Self-improvement extraction

- move manifest, ledger, hooks, evidence, causality and promotion;
- preserve schema version and `.aether/self_improvement.db` rows;
- replace Harmonia-specific outcome classification with substrate-neutral execution outcomes;
- keep candidate isolation and human promotion authority.

**Gate:** all self-improvement tests use only `aether_agents.*`; the current ledger remains readable; no automatic activation is introduced.

**Candidate status (M1.2): LOCALLY VERIFIED.** Seven modules totaling 2,043
lines were moved without legacy copies into `aether_agents.self_improvement`.
All internal and test imports are Aether-native; the plugin wrapper moved with
them but remains absent from `plugins.enabled`. Ledger schema 5 reopens
byte-for-byte without migration, candidate isolation and named human promotion
authority are unchanged, and no activation path was added. The focused gate
passes `87/87` and the full suite passes `420/420`.

With M1.1, M1.2 and M1.3 locally verified, M1 is locally complete. This does
not approve integration, activation, release or any Orca runtime pilot.

### M1.3 Authority, contract and evidence extraction

- move or rewrite project principal;
- define substrate-neutral Aether Run/Task/Attempt contracts;
- preserve budgets, effect states, review, closure and evidence verification;
- separate Aether semantic state from Orca operational state.

**Gate:** deterministic contract/evidence/effect/review/closure tests pass without importing the kernel runtime or Orca.

**Candidate status (R3a): LOCALLY VERIFIED.** Seven semantic modules were moved
without legacy copies into `aether_agents`; the native package has zero Olympus
or Orca imports. The semantic gate passes `143/143`, coordination passes
`407/407`, and the full suite passes `653/653`. The temporary Olympus facade was
then deleted by the independently validated R3b cut.

### Rollback

Compatibility imports may temporarily re-export from the new package, so active behavior can return to the prior server while the new modules remain unused. Every shim must name its deletion milestone.

## 6. Historical M2 proposal — Harden Orca and implement the adapter (superseded)

### Goal

Exercise one isolated vertical slice without switching Aether's active runtime.

### M2.1 Local hardening

- pin the AppImage/build digest;
- verify Linux Chromium sandbox;
- allocate dedicated Orca state and `HERMES_HOME`;
- enforce Manual permissions and Yolo off;
- disable telemetry, LAN/mobile relay, plugins and external automations;
- use a synthetic repository without remotes or credentials;
- enforce environment and project-root allowlists;
- verify private file permissions and rollback.

**Gate:** every negative cross-project/profile/network test passes. Failure stops the pilot.

### M2.2 Adapter implementation

Implement a narrow JSON client and validated schemas for:

- runtime status and build identity;
- Run create/show/list/use;
- Task create/update/list;
- worker start/show/read/stop;
- Dispatch inspection;
- send/ask/reply/check;
- terminal and worktree inspection/cleanup;
- structured effects, residual resources and errors.

The adapter must:

- reject unknown fields where authority depends on them;
- preserve unknown runtime state as unknown;
- never silently retry a mutation;
- correlate Aether contract/task/attempt IDs to Orca IDs;
- record exact command/build/receipt identity;
- expose no release or protected effect operation.

### M2.3 Synthetic vertical slice

Run one deterministic task in a disposable repository:

```text
Aether contract
-> Orca Run
-> Task
-> supervised worker
-> worker_done
-> Aether evidence verification
-> Aether semantic acceptance
-> explicit cleanup
-> zero survivors
```

**Gate:** exact receipts, evidence, restart observation and cleanup pass; rollback removes all pilot state without affecting Aether.

## 7. Historical M3 proposal — Prove lifecycle parity and switch one bounded path (superseded)

### Goal

Implement a bounded two-worker Aether path without reintroducing Olympus. Rollback uses the exact predecessor tree and untouched historical stores, never coexisting legacy code or a hidden fallback.

### Cases

1. two independent Tasks and two workers;
2. question/reply and bounded coordinator wait;
3. retry after a proven worker failure;
4. stale Dispatch/terminal rejection;
5. restart and authority recovery;
6. partial start with residual resources;
7. cancellation and full cleanup;
8. no cross-project/profile access;
9. no forbidden participant admission;
10. no protected effect without Aether authorization;
11. digest-bound evidence and semantic acceptance;
12. zero workers, terminals, setup processes, worktrees and pending messages after closeout.

### Switch rule

The first active consumer may switch only when the Orca path passes all cases on the exact candidate. The configuration must select one path explicitly. If Orca fails after selection, fail visibly and roll back through an operator-controlled configuration change; do not invoke ACP automatically.

### Sequencing update

At the product owner's direction, R4/R5 removed ACPManager, its database, hooks,
server and public tools before this milestone. M3 must therefore implement a new
path from the clean boundary; it may not restore retired code for rollback.

## 8. Historical M4 proposal — Reimplement Ariadna outside Olympus (superseded)

### Goal

Preserve Aether continuity and curation while removing Ariadna's ACP/Olympus wrapper.

### Contract

Ariadna receives:

- exact project root;
- continuity database path and schema identity;
- current hot state and bounded recent evidence;
- curation request ID;
- expected output path;
- freshness baseline;
- validation requirements.

Ariadna returns:

- structured outcome;
- exact `CONTEXT.md` path;
- freshness and digest evidence;
- validation result;
- uncertainty or failure.

### Execution

Orca may run Ariadna as a supervised worker, but Aether owns the request, data projection, validation and acceptance. Ariadna must not receive unrestricted secrets, other-project state, or authority to mutate arbitrary files.

### Gate

- valid fresh curation succeeds;
- stale/missing/invalid output fails visibly;
- project isolation negative tests pass;
- `aether_status`, `aether_update`, and `aether_curate` work without `olympus_v3` imports;
- `.aether/CONTEXT.md` is never edited through an unsupported direct path.

## 9. Historical M5 proposal — Migrate active consumers and state ownership (superseded)

### Source/config consumers

Migrate in independently testable cuts:

1. Aether plugin wrappers;
2. retirement of the obsolete v0.20 self-improvement plugin import;
3. profile templates;
4. Aether configuration template;
5. setup/update/doctor scripts;
6. package metadata and entry points;
7. active skills and current-facing docs;
8. website and onboarding.

### Data transition

- keep `.aether/aether.db` and `.aether/self_improvement.db` in place;
- inspect and archive legacy consulting data if present;
- stop writes to Olympus session and coordination stores;
- record final read-only fingerprints and archive locations;
- remove PID markers only after live-process reconciliation;
- do not copy raw turns, reasoning, tool arguments or secrets into Orca/Aether replacement stores.

### Gate

A clean install and update from the supported predecessor succeed with the new package and preserve project continuity. Rollback restores the prior configuration and reads the untouched legacy stores.

## 10. Milestone M6 — Progressive Olympus retirement

Each cut has a pre-removal characterization, a removal contract, focused tests, full affected tests and rollback.

### Cut R1 — Dead consulting workflow

**Status: COMPLETE in the isolated candidate.**

Remove:

- `consult_action.py`;
- `consulting_db.py`;
- direct tests and current-facing references.

Evidence: no active route, zero executable importers, no consulting database
present, removal-contract RED `2 failed`, focused GREEN `13 passed`, residual
import scan `PASS`, and full suite `828 passed`. The cut removed 2 modules and
1,373 source lines; Olympus now contains 43 Python modules and 18,234 lines.

### Cut R2 — Harmonia public/runtime wrapper

**Status: LOCALLY COMPLETE — integration/activation remains gated.**

Remove:

- `harmonia_contract.py`;
- `harmonia_runtime.py`;
- `harmonia_service.py`;
- `harmonia_store.py`;
- `harmonia_selection.py`;
- `selection_commit.py`;
- Harmonia configuration, scripts and tests.

Local evidence: the public route, server composition, configuration and demo
were disconnected before physical deletion. The removal contract was observed
RED (`8 failed`, `64 passed`), focused GREEN passed `128/128`, the full suite
passed `649`, and the residual import scan found zero importers. Olympus now has
37 modules and 15,991 source lines.

Integration prerequisite: prove no live Harmonia runtime remains and fingerprint
and freeze historical stores read-only. The isolated source cut did not mutate
or migrate any store and does not authorize activation.

### Cut R3 — Generic kernel lifecycle

R3a extracted identity, contracts, budgets, evidence, effects, review and
closure into `aether_agents`. Olympus decreased from 37 to 30 modules and from
15,991 to 13,183 source lines without duplicating the moved implementation.

**R3b candidate status: LOCALLY VERIFIED.** The following runtime implementation
was removed with zero active source/script importers:

- dispatcher, runtime, leases, ledger, operational projections and workflow implementation;
- tests that assert only the retired implementation.

Applicable tests were converted into substrate-neutral Aether contracts before
deletion. Aether contracts, budgets, evidence, effects, review and closure
remain under the new package.

The R3b contract was observed RED and then GREEN. Thirteen pure Aether budget
tests preserve applicable semantics; the focused gate passes `160/160` and the
full candidate suite passes `406/406`. Olympus now has 22 modules and 7,198
source lines. No persistent store was mutated.

### Cut R4 — ACP lifecycle and Olympus observability

**Status: LOCALLY IMPLEMENTED — final acceptance in M7.**

Remove:

- `acp_manager.py`;
- `db.py`;
- `olympus_v3_hooks`;
- ACP config, PID markers and active plugin wrappers;
- ACP-only dependencies after residual import verification.

The candidate is isolated and not activated. This source cut did not modify or
delete live runtime state or historical stores; replacement parity is now a
prerequisite for restoring execution, not for retaining legacy code.

### Cut R5 — Server, CLI and package facade

**Status: LOCALLY IMPLEMENTED — final acceptance in M7.**

Remove:

- old `server.py` after all public capabilities moved;
- Olympus CLI package after Aether setup/doctor parity;
- `config_loader.py` after config migration;
- package `__init__.py` after the R3 coordination facade removal;
- `olympus` and `olympus-v3` entry points;
- the `olympus-mcp` package identity.

At this historical cut the candidate became the `aether-agents` 0.22.0 Python
distribution with zero Aether MCP tools. PDR-0012 later retired that disconnected
distribution in R4.2.

### Cut R4.1 — Obsolete v0.20 self-improvement bootstrap

**Status: LOCALLY VERIFIED.**

Remove:

- the `aether-self-improvement` plugin wrapper and manifest;
- v0.20-bound session hooks;
- the strict v0.20 cycle-manifest reader;
- the manifest-bound release-evidence projector;
- tests whose only acceptance subject was that executable bootstrap.

This cut initially preserved the schema-v5 ledger, deterministic causality
comparison, disposable candidate, and human-promotion primitives as inert
libraries. R4.2 subsequently removed those unconsumed implementations while
preserving `.aether/self_improvement.db` and all v0.20 reports byte-for-byte.

### Cut R4.2 — Disconnected Aether native core

**Status: LOCALLY VERIFIED.**

PDR-0012 supersedes the pre-emptive native-core requirement. The candidate removes:

- all 15 native Python modules (5,500 physical lines);
- all six two-file profile continuity plugins;
- 18 implementation-only test files;
- `src/requirements.txt`, `aiosqlite`, editable installation, package build and artifact upload;
- current documentation and profile claims that `.aether` is an active API.

The contract was observed RED (`5 failed`, `8 passed`) and then GREEN. The exact
working tree passes `25/25` retained tests, Ruff, compileall, shell/YAML parsing,
release governance, zero-runtime scanning, two isolated setup passes, seven
resolved configs, wrapper isolation and candidate-local doctor. Existing
`.aether/aether.db` remains 53,248 bytes with SHA-256
`30799762ec52a33ec5344987ef8b949581e1781eb3882f1499e584359222a9bc`.

## 11. Milestone M7 — Dependency and documentation cleanup

**Status: LOCALLY COMPLETE.** Source dependencies, templates,
setup/update/doctor, README, guides, active context and website are migrated.
R4.1's package evidence remains historical; R4.2 removes the package itself.

**Post-retirement cleanup: LOCALLY VERIFIED.** Issues #154–#158 remove the
remaining active Honcho and Graphify installation/configuration surfaces,
reclassify current Olympus/Harmonia documentation under PDR-0011, generate the
root Hermes config during clean setup, and make doctor inspect the
candidate-local Hermes installation without inherited source overrides. The
exact cleanup tree passes 239 tests, Ruff, compileall, shell/YAML parsing, 48
current Markdown links, active-residual scanning, a 20-entry wheel, a 49-entry
sdist, clean wheel installation, two isolated setup passes with seven resolved
configs, and a candidate-local doctor smoke. No runtime, service, credential,
historical store, or local data was changed.

The current content/config product gate is:

1. no production `src/` tree, runtime dependency, plugin, entry point, or editable install;
2. tooling-only `pyproject.toml` plus `VERSION` product metadata;
3. seven valid config outputs and idempotent setup;
4. candidate-local wrapper and doctor;
5. current README, guides, product policy, profiles and website aligned with PDR-0012;
6. historical release references and protected stores unchanged.

## 12. Milestone M8 — Exact candidate acceptance

### Required evidence

- exact candidate commit and clean tree;
- focused tests for every migrated boundary;
- full suite;
- Ruff and compilation;
- tooling/test compilation and explicit package absence;
- clean setup/update/doctor smoke;
- synthetic and bounded Aether-Orca E2E;
- restart/recovery evidence;
- security/isolation negative tests;
- zero-survivor cleanup;
- rollback execution;
- residual import/entry-point/plugin/config/current-doc search;
- preserved historical references and store fingerprints;
- disclosed unknowns and limits.

### Release verdicts

- `IMPLEMENTED — DEFAULT OFF`: source transition complete, runtime not activated;
- `CANDIDATE ACCEPTED`: exact tree passes all source and pilot gates;
- `RELEASE READY`: product version, source tree and release evidence reconciled;
- `ACTIVATED`: separate operational authority and live evidence; not implied by release.

## 13. Verification cadence

For each cut:

```text
characterization test
-> replacement test
-> residual consumer search
-> affected suite
-> full suite when shared behavior changes
-> diff review
-> rollback check
```

Do not rerun expensive unchanged gates after documentation-only edits unless the candidate tree or gate inputs changed.

## 14. Current stop condition and next action

R1–R5 are committed and R4.2 is locally verified in the isolated candidate.
`src/olympus_v3`, `src/aether_agents`, the remaining `src/requirements.txt`,
runtime facades, plugins, templates, entry points and dependencies are absent.
The M7 content/config product gates pass.

PDR-0012 supersedes the stable session service, private adapter ledger and
pre-emptive API proposed by the earlier Orca research. Its installed-capability
findings remain evidence; it is not an implementation plan and does not mark M2
as started or passed.

The immediate authorized gate is documentation review of PDR-0013,
`docs/architecture/DAIMONS.md`, and `docs/architecture/ORCHESTRATION.md`. This gate
ends when the documents are internally coherent, links are valid, the diff is
documentation-only, and the product owner accepts or corrects the design.

No profile/config/script/test mutation, Orca execution, Aether Dispatch, live
configuration or state transition, candidate integration, release, or activation
is authorized by this milestone. After separate authorization, P0 begins by
resolving issue #150 and proving a pinned isolated Orca runtime can cold-start,
restart and stop without survivors.
