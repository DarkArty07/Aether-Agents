# Graphify semantic expansion — Supervisor task breakdown

**Status:** active execution breakdown for Objective Contract `oc_c0abec2179f6b09c@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_c0abec2179f6b09c/v1.md`
(SHA-256 `3b25822ccd005b5f760e902113e5b425c843a65f3836b4c869e20aec7ecf11a9`)
on base `d30be12a1eb6497670e6eeaaa16d751179aeb306`.

**Owning specs:** `specs/005-project-knowledge-graphify/spec.md` (KG-13–KG-18),
`contracts/expanded-tools-and-semantic.md`, `contracts/tools-and-data.md`,
`validation.md` (D01–D40), GitHub #330.

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries. The prior
GK-01–GK-03 breakdown for `oc_7beb699ef34a7f04@v2` is superseded here; that
repair remains in source as the structural baseline.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Contract bytes | SHA-256 matches the envelope |
| Base / HEAD | `d30be12a1eb6497670e6eeaaa16d751179aeb306` (`docs(contract): authorize reusable Graphify expansion`) |
| Design sufficiency | KG-13–KG-18, D33–D40 and AC1–AC8 are decided in the contract and expanded-tools contract; no missing product API |
| Component | `aether knowledge doctor --json` reports Graphify `0.9.54` healthy (managed lock); `semantic_enabled` is still false |
| Knowledge index | bound project matches; current revision is not indexed (`INDEX_MISSING`); source inspection used |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Project Canonical Skills | none under `.aether/skills/`; Aether Canonical procedures apply |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Adapter vs upstream | Graphify 0.9.54 and Hermes stay unmodified; reuse native extract/parse/validate/build, `analyze.god_nodes`, `prs.compute_pr_impact`, HTML exporters | No unit may patch, vendor, bump, or MCP-start those dependencies |
| Catalog | Fourteen `project_knowledge` actions, five unchanged `work_memory` actions, two tools | Schema unit owns the catalog; no third public tool |
| Schema vs sanitizer | Keep root `type=object`, `additionalProperties=false`, `required=["action"]`, union properties for Hermes coercion, action `oneOf` branches, per-field action descriptions | Same D32 shape; extend fields/actions only |
| Shared `limit` | Root property is the union 1..50 so coercion accepts PR limits; `work_memory.search` branch and `validate_arguments` stay 1..20 | Schema unit must not silently raise search's accepted max |
| Recovery wording | `context_filter` is query-only; `undirected` is path-only. Strip `get_node`, MCP, CLI `--budget`, raw graph paths. Do not forbid those literals unconditionally | Native unit updates `normalize_recovery_wording` and D29 tests |
| Native vs manager | `graph_worker.py` is the isolated subprocess; GitHub `gh` and auxiliary-client resolution stay on the manager. No secret, client object, or private endpoint in worker JSON/argv/logs/cache keys | Native unit owns worker JSON; manager unit owns transport |
| `snapshots.py` hotspot | `KnowledgeStore.execute`/`update` is the single envelope, publication lock, semantic fingerprint and new-action dispatch surface | Concentrate D34-envelope + D35–D39 in one manager unit; do not parallelize GitHub/visualize/semantic by issue |
| `graph_worker.py` hotspot | All native Graphify calls already live in one worker | Concentrate stats/god_nodes/query-impact-path controls/native HTML/semantic parse-apply/PR impact compute in one native unit |
| Guidance / policy.yml | New tracked non-`specs/` files must be added to `.github/workflows/policy.yml` expected list in the same unit. Skills/docs/changelog/registry are shared | Delivery unit after manager; do not split script vs docs across concurrent `policy.yml` edits |
| Semantic config | `semantic.enabled` plus `semantic.auxiliary_task=web_extract` for this activation; missing/auto/ambiguous binding is unavailable, never primary-model fallback | Manager unit; no credential/provider/router change |
| Release | Contract: `release_impact=minor`, `release_action=defer`, `release_channel=none` | Units report unit-level compatibility only; terminal owns the aggregate |
| Publication / activation | Implementer commits locally and does not push/PR/merge/close issues or mutate live profiles | Terminal Supervisor closeout and scoped local activation |
| Out of scope | Issue #329, Graphify/Hermes forks, watchers, extra connectors, browser automation, release tags | Report incidental defects; do not absorb them |

Inspected current baseline (HEAD behavior):

- `KNOWLEDGE_ACTIONS` is the eight structural actions; `query` hardcodes `mode=bfs`, `depth=2`, `context_filters=[]`; `path` hardcodes `undirected=False`.
- `normalize_recovery_wording` strips `context_filter` and `undirected=true` unconditionally; D29 tests assert that.
- `KnowledgeStore.execute` allow-list is the eight actions; `update` always leaves `semantic_pending=True` and coverage `structural_only`.
- `component.py` / doctor hardcode `semantic_enabled: false`.
- No `scripts/qualify_knowledge_expansion.py`. Packaged skills still document `context_filter` as unsupported.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| AC1 / D33 / KG-18 catalog | GX-01 | 14/5 actions, sanitizer, identity rejection, old shapes |
| AC2 / D34 / KG-15 native | GX-02 | Native stats, ranking, query/impact/path controls, refs/truncation |
| AC2 / D34 envelope | GX-03 | Copy native additive objects through `aether.project-knowledge.v1` |
| AC3 / D35 / KG-13–KG-14 live extract | GX-03 + GX-04 live lane; GX-INT independent review | Two fixture projects + one bound-project inspection |
| AC4 / D36 fingerprint/cache | GX-03 | Same-commit enrich, zero-call repeat, rename/delete/config, resume |
| AC5 / D37 failure preservation | GX-03 | Exhaustion, hollow/malformed, timeout, cancel, concurrency |
| AC6 / D38 / KG-16 | GX-03 | Read-only gh + native impact; unavailable ≠ zero impact |
| AC7 / D39 / KG-17 | GX-02 native render; GX-03 export envelope | Real graph/tree HTML, snapshot bytes unchanged |
| AC8 / D40 docs, gates, activation | GX-04 guidance/script; GX-INT merge/activation | Fresh-process load and managed skill copies at terminal |
| D29–D32 regressions | GX-01/GX-02/GX-03 as touched; GX-INT full | Update unconditional `context_filter` prohibitions |
| Non-build | GX-INT | GitHub closeout, #330, scoped activation, graph refresh as navigation |

## Shared decisions (stamp into every implementation unit)

1. Do not modify Graphify, Hermes, lockfiles, or add a third public tool. Do not acquire credentials, change router/provider/model, open a browser, or publish.
2. Catalog (project_knowledge): `status`, `query`, `explain`, `neighbors`, `community`, `path`, `impact`, `update`, `stats`, `god_nodes`, `list_prs`, `pr_impact`, `triage_prs`, `visualize`. Memory: `save`, `search`, `read`, `correct`, `reflect` unchanged.
3. New/changed model fields (missing optional fields preserve old behavior):
   - `query`: optional `traversal` (`bfs`\|`dfs`, default `bfs`), `depth` (1..6, default 2), `context_filter` (array, max 20 nonempty strings, each <=80 chars).
   - `impact`: optional `relations` (array, max 20 nonempty strings, each <=80 chars).
   - `path`: optional `undirected` (boolean, default false).
   - `god_nodes`: optional `top_n` (1..50, default 10), `exclude_hubs_percentile` (0..100), `budget_tokens`.
   - `list_prs` / `triage_prs`: optional `base` (1..255 chars), `limit` (1..50, default 20), `budget_tokens`.
   - `pr_impact`: required `pr_number` (positive integer); optional `budget_tokens`.
   - `visualize`: optional `format` (`graph`\|`tree`, default `graph`), `detail` (`auto`\|`full`, default `auto`, graph only). No `budget_tokens`.
   - `stats`: no extra arguments and no `budget_tokens`.
4. Root schema `limit` is integer 1..50 (union). `work_memory.search` oneOf/`validate_arguments` remain 1..20. Values 21..50 are valid only for `list_prs`/`triage_prs`. Do not add identity/repo/path/provider/secret arguments.
5. Additive output objects follow `contracts/expanded-tools-and-semantic.md`. Empty successful PR lists are distinct from `GITHUB_UNAVAILABLE`. Unknown filters return empty explicit results, not an unfiltered fallback. LLM origin is `origin=llm`; model EXTRACTED is stored as INFERRED or AMBIGUOUS, never AST fact. Do not invent locators.
6. Worker protocol: trusted manager JSON only. Extend `arguments`; optional additive result keys (`stats`, `nodes`, `query_options`, `github`, `pr`, `impact`, `prs`, `artifact`, semantic coverage). Manager rewrites any worker-local path to the public export handle. No raw secret or client object in the worker request.
7. Semantic transport: existing Hermes profile-scoped auxiliary client; this activation uses `semantic.auxiliary_task=web_extract`. Structural `update(mode=structural)` stays no-LLM and must not downgrade a complete same-revision semantic snapshot. Repeat unchanged complete configured work makes zero model calls. Bounded defaults: max_concurrency=2, request timeout min(auxiliary, 180s), one transient retry/chunk, invocation deadline 600s.
8. GitHub: resolve repository from the project marker and verified Git remote; `--repo` only; fixed argv; read-only `gh pr view` / `gh pr list` / bounded file pagination. No checkout, approve, comment, merge, or extra LLM ranking.
9. Visualize: managed `knowledge/<project_id>/exports/<snapshot_id>/`; fixed names by format/detail; snapshot digest unchanged; disclose aggregation and native external assets; do not open a browser.
10. First add focused regressions that fail on this base, then implement. Native GraphifyBackend tests must not skip. Do not print or persist the component interpreter path, auxiliary URL, or model identifier in public artifacts.
11. Local judgement: helper module names under `src/aether_agents/knowledge/`, cache serialization, and equivalent bounded batching. Return to Supervisor if a new public action, upstream patch, credential/provider change, or graph-union appears required.
12. Unit compatibility evidence is `minor` for catalog/behavior additions and `none` or `minor` for docs. Do not publish. Aggregate belongs to GX-INT: minor / defer / none.

## Execution graph

```text
t_e725e76d (Supervisor decomposition root)
    → GX-01 schema D33 (Implementer, isolated worktree)
    → GX-02 native worker D34/D39-render/parse (Implementer, isolated worktree)
         ↘
    GX-03 manager envelope + semantic + GitHub + visualize D34-env/D35–D39
         (Implementer; after independently reviewed GX-01 and GX-02)
         ↘
    GX-04 guidance, qualify script, policy manifest (Implementer; after GX-03)
    → same-card Supervisor review on each implementation unit
    → GX-INT terminal integration/closeout (Supervisor, same flow, terminal=true)
```

GX-01 and GX-02 are independent: different writable files, no shared interface they
must invent (the field catalog is stamped above). GX-03 is concentrated because
`snapshots.py` / `graphify.py` own dispatch, publication, envelope keys and
manager-side I/O for every new action; splitting semantic/GitHub/visualize would
be a `snapshots.py` hotspot. GX-04 is serialized because skills/docs/`policy.yml`
must describe the implemented catalog and register any new tracked files.

Same-card review is the unit review lane. GX-INT consumes independently reviewed
units and does not replace unit review.

## GX-01 — Discriminated schemas (D33)

- Source: AC1, D33, KG-18 catalog; this unit.
- Outcome: canonical 14/5 action-discriminated schemas; Draft 2020-12 and `validate_arguments` identical; sanitizer-usable descriptions; old successful calls still valid; identity/secret inputs rejected. Excludes native/manager behavior, docs, publication.
- Inputs: base `d30be12`; no prerequisite unit.
- Boundaries: writable `src/aether_agents/knowledge/service.py` (`KNOWLEDGE_ACTIONS`, `_FIELDS`, `_ACTION_FIELDS`, `_FIELD_DESCRIPTIONS`, `parameters()`, `validate_arguments()` only), `tests/test_knowledge_schema.py`. `tests/test_knowledge_plugin_cli.py` only if existing identity tests need the new action names. Preserve worker, snapshots, memory behavior, docs, lockfiles, Objective Contract.
- Judgement: JSON Schema combinator layout as long as shared decisions 2–4 hold. Do not change `KnowledgeService.execute` routing.
- Verification: fail-first parity matrix for every new action/field, including `query`+`depth`/`traversal`/`context_filter`, `path`+`undirected`, `impact`+`relations`, `stats` rejecting `budget_tokens`, `work_memory.search` `limit=21` rejected and `list_prs` `limit=21` accepted, identity injection. Sanitizer test using exact-Hermes `sanitize_tool_schemas`. `AETHER_GRAPHIFY_PYTHON` from `KnowledgeService().configuration()["python"]`; `uv run --frozen python scripts/run_tests.py -- -q -rs tests/test_knowledge_schema.py tests/test_knowledge_plugin_cli.py tests/test_work_memory.py`; ruff/format/mypy on touched Python.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `minor`; no push.

## GX-02 — Native worker operations (D34 native, D39 render, semantic parse/apply, PR compute)

- Source: AC2/D34 native, AC7/D39 renderer, worker half of D35/D38; this unit.
- Outcome: Graphify 0.9.54 worker supports stats, god_nodes, query traversal/depth/context_filter, impact relations, path undirected, native graph/tree HTML write, semantic chunk prepare/parse/validate/apply from supplied model text, and `prs.compute_pr_impact` from supplied file lists. Recovery wording distinguishes supported query `context_filter` and path `undirected` from unsupported `get_node`/MCP/CLI. Excludes manager auxiliary/gh, snapshot publication, docs, publication.
- Inputs: base `d30be12`; no prerequisite unit. Shared field catalog is in the decisions above, not sibling source.
- Boundaries: writable `src/aether_agents/knowledge/graph_worker.py`, `tests/test_graphify_worker_native.py`, and native-only recovery assertions in `tests/test_knowledge_regressions.py` if they import the worker helper. Preserve `service.py`, `snapshots.py`, docs, lockfiles, Objective Contract. Do not call `gh` or Hermes auxiliary from the worker.
- Judgement: worker action/subcommand names and how HTML is written to a manager-supplied export path. Escalate if native HTML or parse APIs cannot be used without patching Graphify.
- Verification: fail-first native tests in the isolated Python 3.11 Graphify env (do not install pytest into the live managed component; follow the existing disposable-component pattern). Stats/ranking agree with the built graph; DFS vs BFS and context_filter change the result set; undirected path differs from directed; HTML files parse and leave `graph.json` bytes unchanged when invoked with a side export path; malformed model text is rejected without publishing; supplied PR file lists compute impact without network. Update D29 tests so `context_filter` is forbidden as recovery for non-query actions and allowed as a query argument. `AETHER_GRAPHIFY_PYTHON="$GRAPHIFY_PYTHON" uv run --frozen python scripts/run_tests.py -- -q -rs tests/test_graphify_worker_native.py`; ruff/format/mypy on touched Python. Native tests must not skip.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `minor`; no push.

## GX-03 — Manager envelope, semantic lifecycle, GitHub, visualize (D34-env, D35–D39)

- Source: AC2 envelope, AC3–AC7, D35–D39, KG-13/KG-14/KG-16/KG-17; this unit.
- Outcome: `KnowledgeStore` dispatches all fourteen actions; exploration/GitHub/visualize additive objects appear in the v1 envelope; configured updates perform/resume semantic extraction through the existing auxiliary; structural mode stays no-LLM; GitHub is optional read-only; visualize artifacts are real export handles. Excludes packaged-skill/guide rewrites, qualify script, publication, live profile mutation.
- Inputs: independently reviewed GX-01 and GX-02 commits. Do not treat parent prose as the current tree. Inspect current `service.py` / `graph_worker.py` after those commits.
- Boundaries: writable `src/aether_agents/knowledge/snapshots.py`, `src/aether_agents/knowledge/graphify.py` (request/timeout/cancellation only), `src/aether_agents/knowledge/component.py`, `src/aether_agents/commands/knowledge.py` (doctor/config reporting), new cohesive helpers under `src/aether_agents/knowledge/` as needed, and tests `tests/test_knowledge_regressions.py`, `tests/test_project_knowledge_engine.py`, `tests/test_knowledge_failures.py`, plus new focused test modules if required. If a new non-`specs/` file is added, update `.github/workflows/policy.yml` expected list in this commit. Preserve schema field definitions (GX-01), worker native functions (GX-02), memory.py behavior, lockfiles, Objective Contract.
- Judgement: helper module names, chunk-cache serialization, gh pagination details within the contract. Escalate if auxiliary resolution would require a new credential, primary-model fallback, or Graphify fork.
- Verification: fail-first manager tests for envelope keys, semantic fingerprint/repeat-zero-calls/rename-delete/resume, failure classes (timeout, 429/exhaustion, hollow, cancel, concurrent update), GitHub unavailable vs empty list vs moving head vs large/truncated files, both HTML formats with digest-stable snapshots. Live auxiliary is authorized here for fixture-level D35 evidence when the provisioned connection works; record skip vs exercised honestly. Resolve GRAPHIFY_PYTHON from configuration. Focused `scripts/run_tests.py` on the touched test modules; ruff/format/mypy on touched Python. Public artifacts must not contain auxiliary URL, model id, or machine paths.
- Dependencies: independently reviewed GX-01 and GX-02 (`snapshots.py` dispatch and worker protocol).
- Completion: local commit; same-card review; unit compatibility `minor`; no push.

## GX-04 — Guidance, qualification script, policy manifest (D40 docs/script)

- Source: AC8 docs/skills/registry, D40 script, deliverable guidance; this unit.
- Outcome: current guide, packaged skills, SOUL-compatible examples, changelog, capability registry/generated reference, stage-005 implementation evidence, and `scripts/qualify_knowledge_expansion.py` (`--live-auxiliary`, `--project-id`, `--pr-number`, `--json`) describe and exercise the 14/5 catalog. Skill JSON examples validate. No savings/superiority claim. Excludes adapter behavior changes unless a checked example is invalid (then fix the example).
- Inputs: independently reviewed GX-03 (and therefore GX-01/GX-02). Do not treat parent prose as the current tree.
- Boundaries: writable `docs/guides/project-knowledge.md`, `docs/reference/plugins-and-tools.md`, `docs/reference/cli.md`, `docs/capabilities.toml`, generated `docs/reference/capabilities.md`, `CHANGELOG.md`, `src/aether_agents/resources/skills/project-knowledge/SKILL.md`, `src/aether_agents/resources/skills/work-memory/SKILL.md` only if examples/procedure need it, role SOUL knowledge paragraphs only if the catalog sentence is now false, `specs/005-project-knowledge-graphify/implementation.md`, `scripts/qualify_knowledge_expansion.py`, tests `tests/test_knowledge_resources.py`, `tests/test_documentation.py`, and `.github/workflows/policy.yml` expected/compileall lists for the new script. Preserve adapter/schema sources. Do not edit live `home/` profiles or the Objective Contract.
- Judgement: wording and example selection. `context_filter` is documented as query-only recovery, not as a general substitute for `get_node`.
- Verification: skill examples `validate_arguments`; `uv run --frozen python scripts/check_documentation.py`; focused resource/documentation tests; offline `scripts/qualify_knowledge_expansion.py --json` (no live flag) passes deterministic cases; with `--live-auxiliary` run authorized live/gh cases or report the actual skip. No machine paths/credentials in public text.
- Dependencies: independently reviewed GX-03 (shared guidance files, policy manifest, and script must target real behavior).
- Completion: local commit; same-card review; unit compatibility `minor` or `none` with evidence; no push.

## GX-INT — Terminal integration, closeout, scoped activation

- Source: AC8, D40, deliverables including merge and local activation; this unit.
- Outcome: integrated tree on the objective branch, full exact-Hermes gates, live qualification evidence, CI-green merge to `main`, #330 reconciled only after merge, objective residue cleaned after durable evidence, scoped local activation of the feature (component settings, safe sync of clean primary checkout, feature-owned managed skill copies for Morfeo/Supervisor/Implementer with custom copies preserved), fresh-process canary, current integrated graph. No release artifact.
- Inputs: independently reviewed GX-01..GX-04 commits. Preserve each as its own commit; no squash/amend/rebase/history rewrite. Commit this `tasks.md` if it is not already on the integrated branch.
- Boundaries: integration-owned conflict/import/wiring/docs-path/`policy.yml` repairs that introduce no new behavior. Behavior gaps return as implementation rework. Scoped activation may coordinate drain/reload of the provisioned gateway without interrupting active sessions.
- Verification: contract testing standard in full, including native worker lane, complete `scripts/run_tests.py`, ruff, format, mypy, coverage ≥78% branch, `check_documentation.py`, `uv build`, public-artifact scan, `git diff --check`, `scripts/qualify_knowledge_expansion.py --live-auxiliary` (or recorded unavailability). Then git-github-closeout. Post-merge smoke and activation evidence. Independent review of source-supported semantic relations vs structural-only.
- Dependencies: decomposition root and all four independently reviewed implementation units.
- Completion: aggregate `release_impact=minor`, `release_action=defer`, `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary configured Supervisor/Implementer execution, live auxiliary extraction for qualification, provisioned GitHub read, and routine closeout are authorized. Stop and return `needs-contract-revision` only for a genuine contract defect (Hermes/Graphify fork required, new credential/provider authority, graph union, or changed public action set). Missing configured auxiliary or exhausted router is unavailable/deferred, not fallback. Do not absorb issue #329. Do not overwrite conflicting custom profile skills, move a dirty/concurrent primary checkout, or interrupt live sessions.
