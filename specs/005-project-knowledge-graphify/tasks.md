# Semantic project-knowledge remediation — Supervisor task breakdown

**Status:** active execution breakdown for Objective Contract `oc_f2acfb5effb21f6d@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_f2acfb5effb21f6d/v1.md`
(SHA-256 `a8d6f534acf8121fbdc46b1119d9b0ab019c77db5694c1e2d06824c9819254a0`)
on base `06938e85b86e38f24c19caed8e6ea54d2ed38ae3`.

**Owning specs:** `specs/005-project-knowledge-graphify/spec.md` (KG-13–KG-18),
`contracts/expanded-tools-and-semantic.md` (reconcile the former 600-second/merge
assumptions), GitHub issues #416, #418, #419, #420, #423, #424.

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries. The prior
GX-01–GX-INT breakdown for `oc_c0abec2179f6b09c@v1` is historical expansion
context; this remediation does not reopen that catalog.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Bound knowledge project | `project_knowledge` status returns the same project id and source revision `06938e85b86e38f24c19caed8e6ea54d2ed38ae3` (`INDEX_MISSING`; source inspection used) |
| Contract bytes | SHA-256 matches the envelope |
| Base / HEAD | `06938e85b86e38f24c19caed8e6ea54d2ed38ae3` (`docs(contract): authorize semantic knowledge remediation`) |
| Execution board | native board bound to this contract version; no default-board fallback |
| Design sufficiency | issues #416/#418/#419/#420/#423/#424 plus owner comments settle overlay, 300s bound, fail-closed route, Responses fidelity, ContextVar copy, migration/quarantine, warning language, and the four-call live ceiling |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Policy base debt | tracked contract path is absent from `.github/workflows/policy.yml` expected list; SK-06 registers it. Do not waive the gate. |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Overlay vs merge | Committed structural graph is immutable. Semantic data is an additive `origin=llm` overlay. `semantic_apply` must not call Graphify `build_merge` / global label dedup over the existing graph. Graphify 0.9.54 remains query/validate/cluster/export. | SK-01 replaces per-fragment `build_merge`. No Graphify version/fork/upstream wait. |
| Compose-once | One configured update loads the candidate graph once and performs at most one cluster/export publication transaction. Hyperedges are in the overlay. | Worker protocol below is the shared interface. SK-04 calls it once; SK-01 implements it. |
| Structural projection | Before publication, compare canonical structural projection: node identity, source/provenance attributes, edge endpoints/relation/site, graph direction. Derived community ids and equivalent explicit `origin=ast` alias may be normalized. Any structural identity/relation/source/provenance loss aborts publication. | SK-01 computes the digest; SK-03 refuses the pointer when it mismatches. |
| Bounds | 300-second total monotonic budget from entry through pointer publication; concurrency ≤2; reserve finalization before another model call. Natural exhaustion returns a valid partial receipt. Host/user cancel stops scheduling, propagates to in-flight auxiliary calls where supported, retains validated cache, never publishes the cancelled candidate. No daemon/watcher/hidden continuation. | SK-04 owns the executor clock; SK-03 owns lock/pointer/cancel wiring. Former 600s default is withdrawn. |
| Route | Primary-only fail-closed. Unresolved or mismatched effective non-secret provider/model/protocol is neither cached nor applied; chunk is pending/rejected with `route` category. Multi-route snapshots are out of scope. | SK-04 closes the #424 hole that still applies after skipping cache. |
| Responses | Maintained Hermes adapter preserves phase, top-level and item status, incomplete reason, output-text fallback and tool calls; incomplete/cancelled must never become `finish_reason=stop`. Aether consumes one unambiguous final-answer text or exactly one expected structured fragment call, then the existing strict Graphify validator. Forced `tool_choice` + `submit_graph_fragment` is a bounded contingency only after the first live text probe yields complete-but-invalid JSON, using at most two extra calls. Total new live calls ≤4. No Router widening. | SK-02 is the portable Hermes patch. SK-04 consumes the stamped metadata. SK-INT owns the live canary. |
| Accounting | Each semantic worker gets its own `contextvars.copy_context()` (or Hermes equivalent). One Context object is never entered concurrently. Shared `threading.Event` is separate from ContextVar propagation. | SK-04 wraps executor submissions. Session identity never enters worker JSON. |
| Snapshots | Persist semantic snapshot/plan/cache policy versions and a structural-base reference. Legacy semantic snapshots lacking the new integrity version are not served as trusted semantic results. Matching validated cache fragments may be revalidated and reused without new model calls. Old artifacts remain retained evidence. Structural mode or integrity recovery can select/rebuild a pure structural base. | SK-03 owns publication, migration, rollback/rebuild, warning selection. |
| `graph_worker.py` hotspot | Native Graphify calls already live in one worker. Overlay composition cannot be split from apply. | SK-01 is concentrated on that file. |
| `semantic.py` hotspot | Prepare, auxiliary call, route, cache, plan, deadline, cancel and accounting share one manager module. | SK-04 is concentrated on that file; do not parallelize route vs plan. |
| `snapshots.py` hotspot | Envelope, lock, pointer, migration, warning and structural recovery share one store. | SK-03 is concentrated; do not parallelize warnings vs publication. |
| `policy.yml` hotspot | New tracked non-`specs/` files must be added to the expected list. Base already omits this contract path. SK-02 will add a patch artifact. | Only SK-06 among implementation units edits `.github/workflows/policy.yml`. |
| Live budget | At most four new live semantic auxiliary calls, primary route only, after deterministic/component gates. | No Implementer unit makes live auxiliary calls. SK-INT owns the canary and post-merge zero-call reuse. |
| Release | Contract: `release_impact=patch`, `release_action=defer`, `release_channel=none` unless integrated evidence proves an additive public control is unavoidable. | Units report unit-level compatibility only; terminal owns the aggregate. |
| Publication | Implementer commits locally and does not push/PR/merge/close issues or mutate live profiles. | Terminal Supervisor closeout. |

Inspected current baseline (HEAD behavior):

- `graph_worker.py` `semantic_apply` calls `build_merge` per fragment and restores provenance only when original IDs survive.
- `semantic.py` default deadline is 600s; apply-all runs after the deadline; mismatched routes skip cache then still apply; `ThreadPoolExecutor.submit` does not copy ContextVar context; `_call_auxiliary_model` reads only `choices[0].message.content`.
- `snapshots.py` query warning treats any non-`semantic` document coverage as “semantic extraction is not enabled”; `update(mode=structural)` same-inputs fast path cannot rebuild a pure structural base from a corrupt semantic snapshot.
- `KnowledgeStore.update` does not pass `cancel_event`; `hermes_plugin.py` does not observe host interrupt.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| AC-01 / AC-02 / AC-03 / #419 overlay | SK-01 | Structural projection, additive LLM overlay including hyperedges, no `build_merge`, one load/compose/cluster/export |
| AC-07 Responses fidelity / #420 adapter | SK-02 | Portable Hermes patch; incomplete/cancelled never become `stop` |
| AC-04 / AC-05 / AC-08 diagnostics / AC-09 / AC-10 / #418 #420 #423 #424 manager | SK-04 | One-pass plan, 300s bound, cancel, route fail-closed, content-free categories, ContextVar accounting |
| AC-06 / AC-11 / AC-12 / AC-13 snapshot half / #416 #418 #419 recovery | SK-03 | Atomic pointer, operation metadata, migration/quarantine, structural rollback, honest warnings, structural query on failure |
| AC-08 live yield / AC-14 / AC-15 | SK-INT | Four-call canary, integrated gates, GitHub closeout, issue evidence |
| Deliverable 1 / 600s reconciliation / policy | SK-06 | Stage-005 contract, user-facing docs, `policy.yml` |
| AC-13 catalog compatibility | all | 14/5 actions and successful v1 envelope fields stay compatible; new receipt fields additive |
| Non-build | SK-INT | Push/PR/merge/issue close; no tag/release/deploy |

## Shared decisions (stamp into every implementation unit)

1. Do not modify Graphify version/core, Aether Router, credentials, providers, models, fallback chains, or lockfiles except as required by an existing test pin. Do not add a third public tool, watcher, daemon, vector store, or dashboard. Do not acquire credentials, publish, deploy, force-push, rewrite history, or delete retained evidence. The dirty live editable Hermes checkout is never a source candidate.
2. Catalog remains fourteen `project_knowledge` actions and five `work_memory` actions. Successful v1 envelope fields stay compatible; new receipt/warning/semantic fields are additive. Query/status/greetings never invoke a model.
3. Worker compose protocol (SK-01 implements; SK-04 consumes; do not invent a second path):
   - Action name: `semantic_compose` (keep `semantic_apply` as a compatibility wrapper that forwards a single fragment through the same overlay compositor, never through `build_merge`).
   - Arguments: `fragments` (list of already-validated fragment dicts; a single `fragment`/`model_text` remains accepted for the wrapper), `allowed_sources`, `allow_empty`.
   - Behavior: load existing graph once; build structural-anchor indices; remap only uniquely proven collisions onto existing structural identities; add only `origin=llm` nodes/edges/hyperedges bound to captured sources/anchors; omit ambiguous/colliding/dangling members with a bounded reason; never copy LLM-only attributes (`rationale`, `author`, `source_url`, unscoped `source`, etc.) onto structural records; one `cluster` and one `export.to_json`; compare the canonical structural projection before returning success.
   - Canonical structural projection covers node IDs, source/provenance attributes, edge endpoints/relation/site, and graph direction. Derived community identifiers and an equivalent explicit `origin=ast` alias may be normalized. Mismatch returns `ok=false` and must not overwrite `graph.json`.
   - Receipt keys: `applied_nodes`, `applied_edges`, `applied_hyperedges`, `omitted_nodes`, `omitted_edges`, `omitted_hyperedges`, `structural_digest`, `structural_preserved`.
4. Manager executor protocol (SK-04 implements; SK-03 consumes):
   - Prepare one private bounded plan per compatible revision/policy; persist plan/cache/policy versions and a structural-base reference. Plan records are size/path bounded; content never enters receipts/logs.
   - Compatible partial retry reuses plan, structural base and validated cache and makes zero repeat model calls for already accepted chunks.
   - Default total budget 300 seconds from `run_semantic_extraction` entry through return, including prepare/model/validate/compose. Reserve finalization time before starting another model call. `semantic_deadline_seconds` may only lower the budget, not raise it above 300.
   - Concurrency at most two. Replace blocking `wait(all)` with a bounded poll on the owning thread. Shared `threading.Event` for cancel; each submitted chunk runs under a fresh `contextvars.copy_context()` (or Hermes `propagate_context_to_thread`). One Context is never entered by two workers.
   - Route policy is primary-only fail-closed. `route_ok` is required before cache **and** before inserting into the apply/compose set. Mismatch/unresolved => category `route`, pending/rejected, no graph mutation.
   - Consume auxiliary metadata as: terminal/phase/status, `finish_reason`, incomplete reason, output-text fallback, tool calls. Incomplete/cancelled/`length`/`content_filter` never become `stop` and never enter parse/cache/overlay. Only one unambiguous final text **or** exactly one expected `submit_graph_fragment` call is eligible for strict validation.
   - Content-free categories (at least): `empty`, `incomplete`, `malformed_json`, `schema`, `source`, `route`, `cache`, `apply`, `deadline`. Receipts also count bounded input/output/reasoning/total usage. No raw model/source content is persisted.
   - `length`/incomplete: defer/split that chunk deterministically; do not cache as complete. Hollow: bounded same-chunk retry per existing attempt semantics. Complete-but-invalid JSON: validation failure, no permissive parser.
   - Forced structured-call contingency is **not** implemented unless SK-INT reports that corrected text mode failed within its first two live calls. SK-04 may add a dormant, test-only hook behind an explicit argument defaulting off; production configured updates stay on the text path.
5. Snapshot/publication protocol (SK-03 implements):
   - New integrity/pipeline version on semantic manifests, plus `base_structural_snapshot_id` and structural digest. Candidate manifest/hash/integrity validation precedes one atomic pointer change.
   - Content-free operation metadata identifies phase, revision/input identity and terminal outcome. An operation journal alone is never published evidence.
   - Crash/cancel at prepare, validate, compose, manifest and pointer boundaries leaves either the previous valid snapshot or the fully validated new one. Cancelled candidates are never published.
   - Legacy semantic snapshots without the new version are not served as trusted semantic results. Matching old cache fragments may be revalidated and reused without model calls. Retained historical artifacts are not deleted.
   - `update(mode=structural)` remains no-LLM. When integrity fails or a legacy untrusted semantic snapshot is current, structural mode must be able to select/rebuild a pure structural base through a supported operation rather than the same-inputs fast path that would keep the corrupt overlay.
   - Warning helper is selected from `manifest.semantic.state`, not from current component configuration and not inferred solely from `coverage.documents`:
     - `complete` + documents semantic: no limitation warning;
     - `partial`: partial semantic coverage; remaining paths stay structural; bounded covered/pending/failed counts when present;
     - `pending`: semantic enrichment is pending for this snapshot; current document results are structural;
     - `unavailable`: semantic enrichment was unavailable when this snapshot was built; current results are structural; optional bounded reason category;
     - `disabled`: semantic extraction was disabled when this snapshot was built;
     - missing/unknown/inconsistent: fail closed with unknown/inconsistent-state wording, never “disabled”.
     Use the same helper for every graph-reading action.
6. Hermes patch protocol (SK-02 implements):
   - Ledger id `HLP-420`. Portable patch against verified clean identified source (selected public `v2026.8.18` and/or maintained-fork clean tree as required by `HERMES_LOCAL_PATCHES.md` / reconciliation schema). Never copy from the dirty live editable checkout.
   - Preserve Responses phase, top-level and item status, incomplete reason, output-text fallback and tool calls. Align with the main Codex response normalizer rather than concatenating every message item.
   - `tool_choice` passthrough is authorized in the adapter so the later contingency can be proven deterministically; do not send unsupported Router fields (`max_output_tokens`, `response_format`, `text`).
   - Focused fork/upstream comparison, reconciliation ledger entry, rollback and retirement gate are required in the same unit.
7. `policy.yml`: only SK-06 among implementation units edits it. SK-01/SK-02/SK-04 record any new tracked non-`specs/` paths in their handoff. SK-06 adds those paths and the already-tracked contract `.aether/objective-contracts/oc_f2acfb5effb21f6d/v1.md`.
8. First add focused RED tests that fail on this base, then GREEN them without deleting or weakening the oracle. Native Graphify worker tests run in a disposable Python 3.11 environment with pinned Graphify 0.9.54; never install pytest into the live managed component. Exact-Hermes Aether tests use `scripts/run_tests.py`, not ambient `PYTHONPATH`. Do not print or persist component interpreter paths, auxiliary URLs, model identifiers, or operator home paths in public artifacts.
9. No Implementer unit performs live auxiliary calls. SK-INT owns the owner-authorized four-call canary and the post-merge zero-call reuse. Skipped live/component lanes are reported as skipped, never PASS.
10. Local judgement: private helper names under `src/aether_agents/knowledge/`, cache/plan serialization details, equivalent bounded polling. Return to Supervisor (do not invent) if Graphify must be forked/upgraded, Router must accept new fields, a mixed-route policy is required, live yield needs more than four calls, or structural preservation cannot be demonstrated additively.
11. Unit compatibility evidence is `patch` unless the unit proves an additive public control. Do not publish. Aggregate belongs to SK-INT: patch / defer / none unless evidence forces otherwise.
12. Implementer: local commit, same-card review, no push/PR/merge/issue close/live profile mutation.

## Execution graph

```text
t_a6a6070a (Supervisor decomposition root)
    → t_37f3e4a0 SK-01 overlay compositor (Implementer, isolated worktree)
    → t_2bd12618 SK-02 Hermes Responses adapter HLP-420 (Implementer, isolated worktree)
    → t_96dbb0bf SK-04 semantic manager plan/bounds/route/accounting (Implementer, isolated worktree)
         ↘
    t_39481b81 SK-03 snapshot lifecycle, migration, warnings
         (Implementer; after independently reviewed SK-01 and SK-04)
         ↘
    t_383ba973 SK-06 docs, 300s reconciliation, policy manifest
         (Implementer; after independently reviewed SK-02 and SK-03)
    → same-card Supervisor review on each implementation unit
    → t_e064439e SK-INT terminal integration/closeout (Supervisor, same flow, terminal=true)
```

SK-01, SK-02 and SK-04 are independent: different writable files, and the compose/response contracts are stamped above. SK-03 is serialized on SK-01+SK-04 because `snapshots.py` consumes both the overlay publication result and the manager receipt. SK-06 is serialized because `policy.yml` and user-facing docs must describe implemented behavior and register new tracked files. SK-04 is concentrated because `semantic.py` is the single manager hotspot; splitting route from deadline would collide. SK-01 is concentrated because `graph_worker.py` already owns native apply.

Same-card review is the unit review lane. SK-INT consumes independently reviewed units and does not replace unit review.

## SK-01 — Additive overlay compositor (#419, AC-01/AC-02/AC-03)

- Source: AC-01, AC-02, AC-03, issue #419 and its overlay comments; this unit.
- Outcome: `semantic_compose` / `semantic_apply` preserve every baseline structural node ID and source/provenance attribute and every structural edge endpoint/relation/site on repeated headings, cross-file equal labels, exact/fuzzy AST–LLM collisions, hyperedges, and a retained real-sized fixture. LLM additions are `origin=llm`, bind only to captured sources/anchors, survive serialization, and are omitted with a bounded reason on collision. `build_merge` is absent from semantic application. One load/compose/cluster/export per compose call. A mismatch does not write `graph.json`. Excludes manager auxiliary/plan/publication, docs, live calls, `policy.yml`.
- Inputs: base `06938e85b86e38f24c19caed8e6ea54d2ed38ae3`. No prerequisite unit. Compose protocol is decision 3.
- Boundaries: writable `src/aether_agents/knowledge/graph_worker.py`, `tests/test_graphify_worker_native.py`, and a new private helper under `src/aether_agents/knowledge/` only if imported solely by the worker. Preserve `semantic.py`, `snapshots.py`, `service.py`, docs, lockfiles, Objective Contract. Do not call `gh` or Hermes auxiliary. Do not edit `.github/workflows/policy.yml`.
- Judgement: in-memory index structure and omit-reason strings. Escalate if structural preservation requires a Graphify upgrade/fork.
- Verification: fail-first native tests in the disposable Python 3.11 Graphify 0.9.54 env (`AETHER_GRAPHIFY_PYTHON` from configuration or a disposable venv synced from `src/aether_agents/resources/graphify/requirements.txt`; never install pytest into the live managed component). Cover repeated same-file headings, cross-file equal labels, ghost-ID collisions, reverse-direction structural edges, hyperedge remap/reject, LLM-attribute non-leak onto AST nodes, one load/cluster/export sequence, and digest abort. Keep existing GX apply oracles. `uv run --frozen ruff check/format` and mypy on touched Python.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch`; no push. Record any new non-`specs/` path for SK-06.

## SK-02 — Hermes Responses adapter HLP-420 (#420, AC-07)

- Source: AC-07, issue #420 adapter comments; this unit.
- Outcome: portable `HLP-420` patch plus focused tests, ledger row, and reconciliation entry so incomplete/max-output, content-filter, cancelled, commentary-plus-final, output-text fallback, tool-call, empty and malformed Responses fixtures preserve real terminal/phase shape. Incomplete/cancelled output never becomes `finish_reason=stop`. `tool_choice` passthrough exists; unsupported Router fields are not sent. Excludes Aether `semantic.py` consumption, live calls, `policy.yml`, publication.
- Inputs: base `06938e85`. Clean identified Hermes source only.
- Boundaries: writable `patches/hermes/HLP-420-*.patch` (and patch-local tests if required), `HERMES_LOCAL_PATCHES.md`, `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-420.json`, `tests/test_hermes_patch_reconciliation.py` (`EXPECTED_ACTIVE_IDS` / digests / copy list). Preserve Aether knowledge runtime modules. Do not edit `.github/workflows/policy.yml` (SK-06 adds the patch path). Do not mutate a live editable runtime.
- Judgement: exact alignment with the main Codex normalizer vs a bounded adapter-local equivalent, provided fixtures in decision 6 hold. Escalate if the adapter can only work by widening Router.
- Verification: RED on current adapter mapping `incomplete`/`max_output_tokens` to `stop`; GREEN on the fixture matrix; `uv run --frozen python scripts/validate_hermes_patch_reconciliation.py`; focused `tests/test_hermes_patch_reconciliation.py`; ruff/format on touched Python. Record inspected clean source identity without private paths.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch`; no push. Handoff lists the new tracked patch path(s) for SK-06.

## SK-04 — Semantic manager: plan, bounds, route, diagnostics, accounting (#418/#420/#423/#424, AC-04/AC-05/AC-08/AC-09/AC-10)

- Source: AC-04, AC-05, AC-08 (deterministic half), AC-09, AC-10; issues #418, #420 (Aether half), #423, #424; this unit.
- Outcome: one-pass private plan; 300s total budget with finalization reserve; cooperative cancel; fail-closed route; content-free failure categories; ContextVar-accurate per-session usage; compose invoked once via decision 3; no hidden continuation; cache reuse without repeat model calls. Excludes native overlay internals (SK-01), snapshot pointer/migration/warnings (SK-03), Hermes adapter source (SK-02), live calls, docs, `policy.yml`.
- Inputs: base `06938e85`. Compose and response metadata contracts are decisions 3–4, not sibling trees.
- Boundaries: writable `src/aether_agents/knowledge/semantic.py`, focused tests in `tests/test_knowledge_regressions.py` and/or a new `tests/test_knowledge_semantic_*.py`. Preserve `graph_worker.py` native compositor, `snapshots.py` publication, lockfiles, Objective Contract. Do not edit `.github/workflows/policy.yml`.
- Judgement: plan file layout, poll interval, split granularity for `length`. Escalate if cancel cannot prevent late compose without a watcher, or if mixed-route policy appears required.
- Verification: fail-first tests for (a) unresolved/mismatched route leaves graph bytes/projection unchanged and writes no cache; (b) deadline=0 / mid-apply deadline makes zero new calls after fire, no compose after cancel, cache retained; (c) host-timeout/manual-cancel simulation with no late graph write and no orphan worker; (d) two concurrent copied contexts isolate SessionDB usage; cache hits add no calls; retries follow existing attempt semantics; (e) synthetic complete/incomplete/filter/cancelled/commentary/output-text/tool-call/empty/malformed fixtures never parse incomplete as `stop`; (f) one `semantic_compose` call for N cached fragments (mock or real backend). `AETHER_GRAPHIFY_PYTHON` as needed; `scripts/run_tests.py` on the focused modules; ruff/format/mypy on touched Python.
- Dependencies: decomposition root only (interface-stamped). Do not parent SK-01/SK-02.
- Completion: local commit; same-card review; unit compatibility `patch`; no push. Record any new test module path for SK-06.

## SK-03 — Snapshot lifecycle, migration, honest warnings (#416/#418/#419 recovery, AC-06/AC-11/AC-12/AC-13)

- Source: AC-06, AC-11, AC-12, AC-13; issues #416, #418 publication, #419 recovery comment; this unit.
- Outcome: integrity-versioned semantic manifests with structural-base reference; atomic pointer only after digest/manifest validation; crash/cancel boundary matrix; legacy snapshots quarantined not served; structural rebuild/rollback supported without deleting evidence; query/status warnings distinguish configuration, immutable snapshot state and active operation; structural query remains available when semantic work fails; `cancel_event` / host interrupt reaches the executor and Graphify subprocess. Excludes compositor internals, auxiliary parsing, live calls, docs, `policy.yml`.
- Inputs: independently reviewed SK-01 and SK-04 commits. Inspect current `graph_worker.py` / `semantic.py`; do not treat parent prose as the tree.
- Boundaries: writable `src/aether_agents/knowledge/snapshots.py`, `src/aether_agents/knowledge/hermes_plugin.py`, `src/aether_agents/knowledge/graphify.py` (timeout/cancel/process-group only), `src/aether_agents/knowledge/component.py` and `src/aether_agents/commands/knowledge.py` only if doctor/status fields must expose the new integrity/operation metadata additively, plus tests in `tests/test_knowledge_regressions.py`, `tests/test_project_knowledge_engine.py`, `tests/test_knowledge_plugin_cli.py` as needed. Preserve worker compositor logic and `semantic.py` executor internals. Do not edit `.github/workflows/policy.yml`.
- Judgement: operation-journal file names and additive envelope keys. Escalate if recovery requires deleting diagnostic snapshots.
- Verification: fail-first table for warning states including live reproduction `semantic.state=pending` + `coverage.documents=structural_only`; current component config change after publication does not rewrite historical wording; legacy snapshot is not served as trusted semantic; structural rebuild restores the base digest; cancel/crash at prepare/validate/compose/manifest/pointer never publishes a cancelled candidate and never leaves `update.lock` held; query after semantic failure still returns structural content. Focused `scripts/run_tests.py`; ruff/format/mypy.
- Dependencies: independently reviewed SK-01 and SK-04.
- Completion: local commit; same-card review; unit compatibility `patch`; no push.

## SK-06 — Docs, 600s reconciliation, policy manifest (deliverable 1, AC-11 wording)

- Source: deliverable 1, in-scope documentation, AC-11 user-facing language; this unit.
- Outcome: stage-005 expanded semantic contract and current user-facing capability/troubleshooting/guide/skill text describe overlay composition, 300-second bound, fail-closed route, honest snapshot warnings, and no-hidden-continuation. `policy.yml` expected list includes this objective contract path and every new tracked non-`specs/` file from SK-01/SK-02/SK-04. No savings/superiority claim. Excludes adapter behavior changes unless a checked example is invalid (then fix the example).
- Inputs: independently reviewed SK-02 and SK-03 (and therefore SK-01/SK-04). Read those handoffs for new paths.
- Boundaries: writable `specs/005-project-knowledge-graphify/contracts/expanded-tools-and-semantic.md`, `specs/005-project-knowledge-graphify/spec.md` only where it still forbids current authorized semantic behavior, `docs/guides/project-knowledge.md`, `docs/reference/plugins-and-tools.md`, `docs/reference/cli.md`, `docs/reference/limitations-and-troubleshooting.md`, `docs/capabilities.toml` + generated `docs/reference/capabilities.md`, `CHANGELOG.md`, packaged `src/aether_agents/resources/skills/project-knowledge/SKILL.md` (and work-memory only if a checked example is now false), `.github/workflows/policy.yml` expected/compileall lists, `tests/test_knowledge_resources.py` / `tests/test_documentation.py` as needed. Preserve adapter/schema sources. Do not edit live `home/` profiles or the Objective Contract body.
- Judgement: wording. Do not reintroduce `build_merge` or a 600-second default.
- Verification: `uv run --frozen python scripts/check_documentation.py`; skill examples still `validate_arguments`; policy expected list equals `git ls-files | grep -v '^specs/'`; no machine paths/credentials in public text.
- Dependencies: independently reviewed SK-02 and SK-03.
- Completion: local commit; same-card review; unit compatibility `patch` or `none` with evidence; no push.

## SK-INT — Terminal integration, qualification, closeout

- Source: AC-08 live, AC-14, AC-15, deliverable 10; this unit.
- Outcome: integrated tree on the objective branch; full exact-Hermes and native Graphify gates; one disposable native-plugin semantic canary ≤4 new primary-route calls proving one independently inspected document/code relation, structural digest preserved, host bound honored, then unchanged repeat with zero new calls; CI-green merge to `main`; issues #416, #418, #419, #420, #423, #424 closed only with criterion-specific evidence or left open with the exact unsupported criterion/blocker; objective residue cleaned after durable evidence. No tag, package release, deployment, provider/model/Router change, force operation or destructive cleanup.
- Inputs: independently reviewed SK-01, SK-02, SK-03, SK-04, SK-06. Preserve each as its own commit; no squash/amend/rebase/history rewrite. Commit this `tasks.md` if it is not already on the integrated branch.
- Boundaries: integration-owned conflict/import/wiring/docs-path/`policy.yml` repairs that introduce no new behavior. Behavior gaps return as implementation rework. Live canary uses already provisioned auxiliary access only.
- Verification: contract testing standard in full, including native worker lane, `uv run --frozen python scripts/run_tests.py -- -q -rs`, ruff, format, mypy, coverage at the unchanged floor, `check_documentation.py`, public-artifact/policy/Hermes-patch checks, `uv build`, `git diff --check`. Then git-github-closeout. Post-merge smoke repeats structural invariant, no-model query, and bounded canary/cache reuse (zero new calls unless the first evidence cannot be bound to the merged revision). Independent review of unit diffs is already done; this card does not replace it.
- Dependencies: decomposition root and all five independently reviewed implementation units.
- Completion: aggregate `release_impact=patch`, `release_action=defer`, `release_channel=none` unless integrated compatibility evidence proves otherwise. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary configured Supervisor/Implementer execution, provisioned GitHub closeout, and the four-call live canary are authorized. Stop and return `needs-contract-revision` only for a genuine contract defect (Graphify fork/version required, Router field required, mixed-route policy required, overlay cannot preserve the structural projection, cancel cannot prevent late publication, live ceiling exhausted without one valid source-bound result, or protected-edge/credential/publication demand). Ordinary implementation failures stay on the review path. Do not close an issue from a partial board summary. If pipeline infrastructure itself regresses, use rollback-first runtime recovery rather than asking workers to repair their dispatcher.
