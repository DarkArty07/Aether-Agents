# v0.22.0 Olympus Retirement Inventory

> **Status:** CURRENT ANALYSIS BASELINE  
> **Date:** 2026-08-03  
> **Source tree:** `main@2b326f05a36cbb77a9bf9475ef914be6f49d886d`  
> **Governing decision:** `docs/decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`

## 1. Purpose

This inventory defines what must happen to every remaining Python module under `src/olympus_v3` before v0.22.0 can remove the package. It distinguishes product behavior that belongs to Aether from generic runtime behavior that Orca can replace and code with no approved future consumer.

This is a retirement contract, not a deletion list. `BLOCKED` means “delete last after named gates,” not “keep forever.” Historical release documents and Git history are outside the executable package inventory and remain preserved.

## 2. Baseline selection

The analysis worktree is on `docs/canonical-product-documentation@a88b5cc`, a clean ancestor of canonical `main`, with extensive unrelated local changes. It is not a valid implementation baseline.

The inventory was therefore computed from an immutable extraction of canonical `main@2b326f0`. That tree:

- contains the released v0.20.0 implementation;
- contains post-release candidate-isolation and promotion work;
- contains commit `9bf3eb0`, which already removed 12,446 lines of unconsumed coordination experiments;
- retains the maintained default-off Olympus/Harmonia/kernel path;
- identifies the package as `olympus-mcp` version `0.20.0`.

The v0.22.0 implementation branch or worktree must be created from the reconciled canonical tree, not from the current stale documentation worktree.

## 3. Measured surface

| Measure | Canonical `main` baseline |
|---|---:|
| Olympus Python modules | 45 |
| Olympus source lines | 19,589 |
| Olympus nonblank source lines | 17,502 |
| Python consumer files outside the package | 57 |
| Test files importing Olympus directly | 43 |
| Test functions in those files | 588 |

### 3.1 Source areas

| Area | Modules | Lines | Initial disposition |
|---|---:|---:|---|
| Coordination | 21 | 10,853 | Rewrite Aether policy; replace runtime; retire Harmonia-specific policy |
| Lifecycle/server | 7 | 4,729 | Replace ACP/session/runtime; split server; retire consulting path |
| Self-improvement | 7 | 2,023 | Rewrite under an Aether-native package unchanged in meaning |
| Continuity | 3 | 1,291 | Rewrite under Aether/Ariadna; preserve schema and data |
| CLI | 5 | 378 | Rewrite package and entry points |
| Olympus observability hooks | 2 | 315 | Replace with Orca/Aether event adapters, then retire |

### 3.2 Classification totals

| Classification | Modules | Meaning |
|---|---:|---|
| `REWRITE` | 23 | Aether-owned behavior must move behind a non-Olympus boundary |
| `REPLACE` | 14 | Generic runtime behavior is replaced by Orca through the adapter |
| `RETIRE` | 5 | No approved future runtime consumer; preserve history and data policy only |
| `BLOCKED` | 3 | Package/server facades removed only after all consumers migrate |

No module is classified `PRESERVE` in place because the target is to remove the `olympus_v3` package. `REWRITE` preserves behavior or evidence while changing its ownership boundary.

## 4. Module-by-module disposition

| Module | Lines | Class | Required result before removal |
|---|---:|---|---|
| `src/olympus_v3/__init__.py` | 2 | `BLOCKED` | Remove only after the last `olympus_v3` import and package entry point is gone. |
| `src/olympus_v3/acp_manager.py` | 1,241 | `REPLACE` | Orca adapter proves spawn, message, observe, cancel, close, restart, and cleanup parity without duplicate editors. |
| `src/olympus_v3/aether_db.py` | 726 | `REWRITE` | Move to Aether-native continuity package with schema/path compatibility for `.aether/aether.db`. |
| `src/olympus_v3/aether_hooks/__init__.py` | 2 | `REWRITE` | Plugin imports the Aether-native continuity hook package. |
| `src/olympus_v3/aether_hooks/hooks.py` | 563 | `REWRITE` | Remove Olympus session/DB coupling; preserve hot start, file-change, session, and CONTEXT behavior. |
| `src/olympus_v3/cli/__init__.py` | 0 | `REWRITE` | CLI package moves to the new Aether package. |
| `src/olympus_v3/cli/setup.py` | 238 | `REWRITE` | Setup installs Aether plus the pinned Orca adapter/configuration without Olympus entry points. |
| `src/olympus_v3/cli/ui/__init__.py` | 0 | `REWRITE` | UI helpers move with the Aether CLI if still consumed. |
| `src/olympus_v3/cli/ui/banner.py` | 113 | `REWRITE` | Retain only if the new Aether CLI still presents it. |
| `src/olympus_v3/cli/wrappers.py` | 27 | `REWRITE` | Generate Aether/Orca wrappers rather than Olympus commands. |
| `src/olympus_v3/config_loader.py` | 227 | `REWRITE` | Split Aether profile/project policy from Olympus DB and Harmonia configuration. |
| `src/olympus_v3/consult_action.py` | 678 | `RETIRE` | Prove no active MCP route or supported workflow consumes it; archive any consulting state first. |
| `src/olympus_v3/consulting_db.py` | 695 | `RETIRE` | Inspect `.aether/.consulting/consulting.db`; export/archive if present; remove auto-creation. |
| `src/olympus_v3/coordination/__init__.py` | 41 | `BLOCKED` | Remove after every maintained coordination symbol is rewritten, replaced, or retired. |
| `src/olympus_v3/coordination/budget.py` | 307 | `REWRITE` | Express budget and attempt limits as Aether execution-contract policy independent of Orca storage. |
| `src/olympus_v3/coordination/closure.py` | 324 | `REWRITE` | Preserve semantic closure outside terminal/Dispatch completion. |
| `src/olympus_v3/coordination/contracts.py` | 457 | `REWRITE` | Define substrate-neutral immutable Aether task/authority contracts. |
| `src/olympus_v3/coordination/effects.py` | 546 | `REWRITE` | Preserve protected-effect intent, approval, execution, and evidence states under Aether authority. |
| `src/olympus_v3/coordination/evidence.py` | 602 | `REWRITE` | Preserve canonical artifact, digest, attempt, and handoff verification outside Orca result prose. |
| `src/olympus_v3/coordination/harmonia_contract.py` | 376 | `RETIRE` | Remove public Harmonia `start/status/stop` surface after the Orca-backed Aether surface is active. |
| `src/olympus_v3/coordination/harmonia_runtime.py` | 543 | `REPLACE` | Orca owns worker/runtime composition; Aether adapter preserves exact project and contract binding. |
| `src/olympus_v3/coordination/harmonia_selection.py` | 212 | `RETIRE` | Preserve v0.19.5 evidence; routing returns to Hermes/Aether rather than a fixed bounded selector. |
| `src/olympus_v3/coordination/harmonia_service.py` | 514 | `REPLACE` | New Aether service creates and supervises Orca Runs/Tasks/Dispatches without a Harmonia wrapper. |
| `src/olympus_v3/coordination/harmonia_store.py` | 285 | `REPLACE` | Freeze old coordination stores read-only; current lifecycle state comes from Orca. |
| `src/olympus_v3/coordination/kernel_dispatcher.py` | 1,531 | `REPLACE` | Orca dispatch/worker lifecycle passes fencing, retry, recovery, and no-duplicate-editor contract tests. |
| `src/olympus_v3/coordination/kernel_runtime.py` | 815 | `REPLACE` | Aether adapter plus Orca replaces command authority and runtime reduction; semantic acceptance stays Aether-owned. |
| `src/olympus_v3/coordination/leases.py` | 190 | `REPLACE` | Prove active Dispatch generation/capability/takeover prevents stale mutation; retain no duplicate lease DB. |
| `src/olympus_v3/coordination/ledger.py` | 2,262 | `REPLACE` | Orca persists lifecycle; Aether persists only product contracts/evidence needed beyond Orca. |
| `src/olympus_v3/coordination/olympus_adapter.py` | 239 | `REPLACE` | Replace with the stable Aether-Orca adapter; no import or call to ACPManager remains. |
| `src/olympus_v3/coordination/principal.py` | 59 | `REWRITE` | Preserve canonical Aether installation/project/actor identity independent of Orca handles. |
| `src/olympus_v3/coordination/projections.py` | 113 | `REPLACE` | Orca owns operational projections; Aether retains deterministic semantic projections only where required. |
| `src/olympus_v3/coordination/review.py` | 523 | `REWRITE` | Preserve independent review, waiver, and acceptance semantics outside worker completion. |
| `src/olympus_v3/coordination/selection_commit.py` | 144 | `RETIRE` | Preserve historical CAS evidence; do not retain fixed v0.19.5 candidate selection as future routing. |
| `src/olympus_v3/coordination/workflow.py` | 770 | `REPLACE` | Map operational task states to Orca while keeping explicit Aether semantic states at the adapter boundary. |
| `src/olympus_v3/db.py` | 783 | `REPLACE` | Orca replaces session/turn/tool/steering lifecycle; archive `olympus_v3.db` read-only. |
| `src/olympus_v3/olympus_v3_hooks/__init__.py` | 2 | `REPLACE` | Remove plugin wrapper after profiles use the sanitized Aether-Orca event path. |
| `src/olympus_v3/olympus_v3_hooks/hooks.py` | 313 | `REPLACE` | Replace raw turn/tool observability with bounded Orca/Aether receipts; do not persist conversation payloads. |
| `src/olympus_v3/self_improvement/__init__.py` | 1 | `REWRITE` | Move package namespace without changing authority. |
| `src/olympus_v3/self_improvement/causality.py` | 343 | `REWRITE` | Preserve frozen-evaluation and deterministic before/after comparison. |
| `src/olympus_v3/self_improvement/evidence.py` | 103 | `REWRITE` | Preserve non-authorizing evidence projection. |
| `src/olympus_v3/self_improvement/hooks.py` | 510 | `REWRITE` | Remove Harmonia classification dependency; record substrate-neutral coordination outcomes. |
| `src/olympus_v3/self_improvement/ledger.py` | 688 | `REWRITE` | Preserve schema/data in `.aether/self_improvement.db` under Aether namespace. |
| `src/olympus_v3/self_improvement/manifest.py` | 205 | `REWRITE` | Point manifest identity and artifacts to the current release contract without Olympus imports. |
| `src/olympus_v3/self_improvement/promotion.py` | 173 | `REWRITE` | Preserve disposable candidate and human promotion gate; optionally bind worktree operations through Orca only after parity. |
| `src/olympus_v3/server.py` | 1,103 | `BLOCKED` | Split all public capabilities and remove the MCP server only after every replacement route is verified. |

## 5. `server.py` decomposition

Deleting `server.py` before splitting it would remove both legacy runtime and Aether product capabilities.

| Current capability | Future owner | Disposition |
|---|---|---|
| `talk_to` lifecycle | Aether-Orca adapter | Replace with explicit Run/Task/Dispatch operations; no hidden ACP fallback. |
| `discover` | Aether profile registry | Rewrite independently of Orca process discovery. |
| `harmonia` | None as a public future runtime | Retire after Orca vertical slice and active consumer migration. |
| `aether_status` | Aether continuity service | Rewrite against `.aether/aether.db`. |
| `aether_update` | Aether continuity service | Rewrite with current project-root and schema guarantees. |
| `aether_curate` | Ariadna service | Rewrite Ariadna invocation without ACPManager/Olympus. |
| MCP stdio server | Aether integration boundary, if still required | Replace package/entry point; do not preserve the `olympus-v3` identity. |

## 6. Active non-source consumers

The final cut must migrate these active classes of consumer, not merely source imports:

- `pyproject.toml` package name, dependencies, and `olympus`/`olympus-v3` scripts;
- `Makefile` setup, doctor, and test assumptions;
- `scripts/setup.sh`, `scripts/update.sh`, and active migration/demo scripts;
- `home/config.yaml.template` MCP server command and tool surface;
- six Daimon profile templates;
- six `aether` plugin wrappers and six `olympus_v3` plugin wrappers;
- `home/olympus_v3.yaml.template`;
- the `aether-self-improvement` plugin import path;
- current README, installation, configuration, architecture, onboarding, and website material;
- current direct and indirect test consumers discovered by the full suite.

Generated live profiles and active runtime configuration are migration targets, not version-controlled editing targets. They remain untouched until the operational activation gate.

## 7. Persistent state disposition

| Store or marker | Current owner | v0.22.0 action |
|---|---|---|
| `.aether/aether.db` | Aether continuity | Preserve in place and keep schema-compatible. |
| `.aether/CONTEXT.md` | Ariadna projection | Preserve; only supported curation may rewrite it. |
| `.aether/self_improvement.db` | Aether evidence | Preserve; move implementation namespace only. |
| `.aether/.consulting/consulting.db` | Legacy consult workflow | Inspect without auto-creation; export or archive if present; then retire. |
| `$AETHER_HOME/.olympus/olympus_v3.db` | Olympus sessions/turns/tools | Stop writes after Orca cutover; archive read-only; do not import full conversation payloads into Orca. |
| `$AETHER_HOME/.olympus/projects/*/coordination-v0.19.1.sqlite` | Harmonia/kernel | Freeze read-only as historical evidence after no active Run remains. |
| `.aether/evidence/...` | Aether/kernel evidence | Preserve verified artifacts and handoffs; migrate verifier ownership, not bytes. |
| `$HERMES_HOME/.olympus_session.*` | ACP session mapping | Delete only after process reconciliation proves no consumer. |
| `$HERMES_HOME/.olympus_db_path.*` | Olympus observability mapping | Delete only after process reconciliation proves no consumer. |
| `$HERMES_HOME/.aether_home.*` | Project continuity mapping | Replace with explicit project binding before removal. |

## 8. Historical reference policy

Historical reports under `docs/releases/v0.19.0-*`, `docs/releases/v0.19.x-*`, and the v0.20.0 release evidence retain their original Olympus paths and findings. They describe the tree that existed at those milestones.

Current-facing documentation, setup instructions, package metadata, active skills, plugin manifests, and profile templates must instead migrate to the Aether-Orca architecture. Residual-reference verification must therefore distinguish preserved historical evidence from executable or current-facing references.

## 9. Candidate retirement progress

### R1 — Dead consulting workflow: COMPLETE

The isolated candidate proved that `consult` was not registered, found zero
executable importers, and found no `.aether/.consulting/consulting.db` to
preserve. It then removed:

- `src/olympus_v3/consult_action.py` — 678 lines;
- `src/olympus_v3/consulting_db.py` — 695 lines.

The removal contract was observed RED (`2 failed`) before deletion and GREEN
afterward. Focused schema/removal tests passed `13/13`; the full suite passed
`828` tests; Ruff, compileall, fresh server import and residual AST import scan
passed. No persistent data was created, changed or removed.

Candidate delta after R1:

| Metric | Canonical baseline | Candidate after R1 |
|---|---:|---:|
| Olympus Python modules | 45 | 43 |
| Olympus source lines | 19,589 | 18,234 |
| Source lines removed by R1 | 0 | 1,373 |

The module table above remains the immutable canonical-baseline inventory; these
two `RETIRE` rows now have an executed disposition in the candidate.

### R2 — Harmonia public/runtime wrapper: LOCALLY COMPLETE

The candidate first disconnected the `harmonia` MCP tool, server composition,
legacy `CoordinationConfig`, and the bounded demo. Self-improvement no longer
imports the retired runtime; it retains only frozen v0.20 wire vocabulary so
already-recorded default-off observations remain interpretable.

Removed source modules:

- `harmonia_contract.py` — 376 lines;
- `harmonia_runtime.py` — 543 lines;
- `harmonia_selection.py` — 212 lines;
- `harmonia_service.py` — 514 lines;
- `harmonia_store.py` — 285 lines;
- `selection_commit.py` — 144 lines.

The six modules account for 2,074 deleted source lines. Additional wiring and
configuration removal reduces Olympus by 2,243 source lines relative to R1.
The 268-line `run_harmonia_bounded_demo.py`, 11 wrapper/selection test files,
and 376 lines from the mixed lifecycle test were also retired. Forty-one tests
remain in that mixed file to protect the retained kernel behavior.

The R2 contract was observed RED (`8 failed`, `64 passed`) and then GREEN.
Focused affected tests passed `128/128`; the full candidate suite passed `649`
tests. Targeted Ruff, compile/import checks, and residual AST import scanning
passed with zero retired modules or importers.

Candidate delta after R2:

| Metric | Canonical baseline | Candidate after R1 | Candidate after R2 |
|---|---:|---:|---:|
| Olympus Python modules | 45 | 43 | 37 |
| Olympus source lines | 19,589 | 18,234 | 15,991 |
| Candidate source delta vs baseline | 0 | -1,355 | -3,598 |
| Registered MCP tools | 6 | 6 | 5 |

This is a local source cut only. Integration or activation remains blocked
until no live Harmonia runtime exists and historical coordination stores are
fingerprinted and frozen read-only without mutating their contents.
