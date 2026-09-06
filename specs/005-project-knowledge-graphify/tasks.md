# Graphify knowledge-tool boundary repair — Supervisor task breakdown

**Status:** active execution breakdown for Objective Contract `oc_7beb699ef34a7f04@v2`.

**Derived by:** Supervisor, 2026-09-06

**Source contract:** `.aether/objective-contracts/oc_7beb699ef34a7f04/v2.md`
(SHA-256 `58aab1be1d4c32abdeacbc3a83b2ee8533a2536d73f267f748123f514bfb1c69`)
on base `ccd862b7e295669ec9dcc3d6cdf7145636614354`.

**Owning specs:** `specs/005-project-knowledge-graphify/spec.md` (KG-01–KG-12),
`contracts/tools-and-data.md`, `validation.md` (D29–D32), GitHub #324–#327.

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Contract bytes | SHA-256 matches the envelope |
| Base / HEAD | `ccd862b7e295669ec9dcc3d6cdf7145636614354` (`docs(contract): clarify Graphify repair authority`) |
| Design sufficiency | D29–D32 and AC1–AC8 are decided in the contract and tool/data contract; no missing product API |
| Component | `aether knowledge doctor --json` reports Graphify `0.9.54` healthy (managed lock) |
| Knowledge index | bound project matches; current revision is not indexed (`INDEX_MISSING`); source inspection used |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Project Canonical Skills | none under `.aether/skills/`; Aether Canonical procedures apply |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Adapter vs upstream | Graphify 0.9.54 and Hermes stay unmodified; repair is Aether adapter/envelope/schema/tests/guidance | No unit may patch, vendor, or bump those dependencies |
| Truncation | `truncated` is cumulative: native omission, Aether content bound, or 50-reference cap. Complete native answers that only exceed the requested estimate stay `truncated=false` with an explicit warning | Envelope unit owns the flag composition |
| Recovery wording | Preserve useful native content; replace `context_filter`, `get_node`, graph-path, CLI/MCP recovery with narrower `question`, higher `budget_tokens` (128–8000), or `explain` on a returned node | Envelope unit rewrites boundary guidance only |
| Provenance | `query`/`explain`/`neighbors`/`community`/`path`/`impact` return revision-bound, project-relative, deduplicated `{path,location,revision}` in stable order; cap 50 is never silent | Envelope unit; `snapshots.py` already binds/caps but does not set `truncated` on cap |
| Community discovery | No new action. `explain` adds `resolved_node={id,community_id,community_name}`; `community` adds `community={id,name,node_count}`; nulls allowed; IDs snapshot-local | Envelope unit |
| Schema | Keep top-level properties for Hermes coercion; add action-discriminated branches; every field description names applicable actions because Hermes `schema_sanitizer._strip_top_level_combinators` drops top-level `oneOf`/`anyOf`/`allOf`/`enum`/`not`. Runtime `validate_arguments` remains authoritative | Schema unit |
| Shared files | `graph_worker.py` and `snapshots.py` implement D29–D31 on the same query/explain/impact/path/community branches | Concentrate D29–D31; do not parallelize by issue number |
| Schema files | `service.py` `parameters()`/`validate_arguments()` are independent of the native worker | Schema unit may run with the envelope unit |
| Guidance files | Guide, packaged skills, changelog, stage-005 evidence, and generated reference would collide if split | One docs unit after both behavior units |
| Release | Contract decision 7: `release_impact=patch`, `release_action=defer`, `release_channel=none` | Units report unit-level compatibility only; terminal owns the aggregate |
| Publication | Implementer commits locally and does not push/PR/merge/close issues | Terminal Supervisor closeout |

Inspected current defects (base behavior):

- `graph_worker.py` query/explain/impact capture CLI stdout and return `references: []` with no native truncation metadata.
- `graph_worker.py` path returns `references: []`.
- `snapshots.py` overwrites `truncated` from `bounded(...)` only and slices `refs[:50]` without a cap warning.
- `service.py` `parameters()` is a field union; `validate_arguments()` then rejects inapplicable combinations (#327).
- Native/regression tests assert non-empty content and that `references` is a list, so an empty list currently passes.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| AC1 / D29 / #324 | GK-01 | Native truncation honesty + supported recovery wording |
| AC2 / D30 / #325 | GK-01 | Structured references + silent-cap repair |
| AC3 / D31 / #326 | GK-01 | `query` → `explain` → `community` without guessing |
| AC4 / D32 / #327 | GK-02 | Discriminated schema parity with `validate_arguments` and sanitizer |
| AC5 | GK-01, GK-02, GK-03 preserve; GK-INT verifies | Isolation, limits, pin, work-memory, update semantics |
| AC6 | GK-03 | Guide, packaged skills, registry/generated reference |
| AC7 | Each unit RED-GREEN; GK-INT full gates | No skipped/weakened tests; 78% branch floor unchanged |
| AC8 | GK-INT | Merge, issue reconciliation, no release artifact |
| KG-05/KG-06/KG-10/KG-11 | preserved by all | No new tool/action; fallback to file inspection remains |
| Non-build | GK-INT | GitHub closeout, graph refresh as navigation coverage |

## Shared decisions (stamp into every implementation unit)

1. Do not modify Graphify, Hermes, lockfiles, or add a public tool/action.
2. `truncated=true` if any of: Graphify omitted nodes/lines; Aether `bounded()` cut content; the existing 50-reference cap omitted a visible source. A complete native answer that only exceeds the requested estimate remains `truncated=false` with an explicit warning. Do not parse untrusted prose as the sole proof of functional success; use exact-version adapter results plus envelope composition.
3. Replace unsupported recovery (`context_filter`, `get_node`, direct graph paths, CLI `--budget` / MCP) with supported Aether calls only.
4. References are project-relative, revision-bound, deduplicated, stable order, max 50. No snapshot/private absolute path may escape. `path` includes nodes and relation sites on the path.
5. `explain.resolved_node={id, community_id, community_name}`; `community.community={id, name, node_count}` with `id` equal to the requested `community_id`. Unclassified nodes use JSON `null` community fields. IDs are snapshot-local and must not be documented as portable across rebuilds.
6. Canonical `parameters()` retains root `type=object`, `additionalProperties=false`, `required=["action"]`, and the union of properties Hermes coercion needs. Add action-discriminated branches whose required/allowed fields match `_ACTION_FIELDS`. Every property description names the actions that accept it. `Draft202012Validator(parameters(tool))` and `validate_arguments` accept/reject the same representative matrix. After `tools.schema_sanitizer.sanitize_tool_schemas`, top-level combinators may be absent; usable action/field descriptions remain. Identity-injection payloads still fail.
7. Work-memory actions stay behaviorally unchanged except schema parity. Do not alter snapshot publication, update, or note semantics beyond the envelope/schema fields above.
8. First add focused regressions that fail on this base, then implement. Native GraphifyBackend tests must not skip. Do not print or persist the component interpreter path.
9. Local judgement: smallest exact-version technique to extract native truncation, visible references, path nodes, and community membership from Graphify 0.9.54 (`graphify/serve.py`, `graphify/__main__.py`, `graphify/affected.py`). Escalate only if that requires patching upstream or a new public action.
10. Unit compatibility evidence is `patch` (compatible fix / additive metadata). Do not publish. Aggregate release conclusions belong to GK-INT: patch / defer / none.

## Execution graph

```text
t_979bdeac (Supervisor decomposition root)
    → GK-01 envelope D29–D31 (Implementer, isolated worktree)
    → GK-02 schema D32 (Implementer, isolated worktree)
         ↘
    GK-03 guidance AC6 (Implementer; after independently reviewed GK-01 and GK-02)
    → same-card Supervisor review on each implementation unit
    → GK-INT terminal integration/closeout (Supervisor, same flow, terminal=true)
```

GK-01 and GK-02 are independent: different writable files, different tests, no shared interface they must invent. GK-03 is serialized because the guide and packaged skills are shared writable files that must describe both behaviors and keep examples valid against the new schema. D29–D31 are one concentrated unit because they collide on `graph_worker.py` and `snapshots.py`; splitting by issue would be a hotspot, not parallelism.

Same-card review is the unit review lane. GK-INT consumes independently reviewed units and does not replace unit review.

## GK-01 — Envelope adapter (D29–D31)

- Source: AC1–AC3, D29–D31, issues #324–#326; this unit.
- Outcome: honest cumulative `truncated`, supported recovery wording, structured references for all six source-bearing actions, and query→explain→community discovery via `resolved_node` / `community`. Excludes schema combinators, packaged-skill/guide rewrites, publication.
- Inputs: base `ccd862b`; Graphify 0.9.54 doctor healthy; no prerequisite unit.
- Boundaries: writable `src/aether_agents/knowledge/graph_worker.py`, `src/aether_agents/knowledge/snapshots.py`, `tests/test_graphify_worker_native.py`, `tests/test_knowledge_regressions.py`, and envelope assertions in `tests/test_project_knowledge_engine.py` if needed. `common.py` only if composition cannot live in `snapshots.py` (flag hotspot). Preserve `service.py`, `hermes_plugin.py`, `memory.py`, skills, docs, lockfiles, Objective Contract.
- Judgement: adapter extraction technique. Return to Supervisor if a new public action or upstream patch appears required.
- Verification: fail-first focused native/regression tests for D29–D31; then
  `GRAPHIFY_PYTHON="$(uv run --frozen python -c 'from aether_agents.knowledge.service import KnowledgeService; print(KnowledgeService().configuration()["python"])')"`
  `uv run --frozen aether knowledge doctor --json` → version 0.9.54
  `AETHER_GRAPHIFY_PYTHON="$GRAPHIFY_PYTHON" uv run --frozen python scripts/run_tests.py -- -q -rs tests/test_graphify_worker_native.py tests/test_knowledge_regressions.py tests/test_project_knowledge_engine.py`
  plus ruff/format/mypy on touched Python. GraphifyBackend tests must not skip.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch`; no push.

## GK-02 — Discriminated schemas (D32)

- Source: AC4, D32, issue #327; this unit.
- Outcome: canonical action-discriminated schemas for `project_knowledge` and `work_memory` with identical Draft 2020-12 and `validate_arguments` outcomes; sanitizer-usable descriptions; no registration/call regression. Excludes envelope behavior, docs/skills, publication.
- Inputs: base `ccd862b`; no prerequisite unit. Inspect exact Hermes `tools/schema_sanitizer.py` via the repository bootstrap, not a random checkout.
- Boundaries: writable `src/aether_agents/knowledge/service.py`; schema tests in `tests/test_knowledge_plugin_cli.py` and/or a new `tests/test_knowledge_schema.py`. `hermes_plugin.py` only if registration wrapping is required (prefer `parameters()` only). Preserve worker/snapshots/docs/skills/memory behavior.
- Judgement: JSON Schema shape (`oneOf` vs `allOf`/`if-then`) as long as decisions 6 hold. Do not put the only discrimination in a top-level combinator without retaining root properties and per-field action descriptions.
- Verification: fail-first matrix of valid/invalid action/field combinations (including `status`+`budget_tokens`, missing required fields, identity injection, work_memory cross-action fields) against `Draft202012Validator` and `validate_arguments`; sanitizer test using `sanitize_tool_schemas` on OpenAI-format wrappers; existing plugin register/dispatch/identity tests.
  `AETHER_GRAPHIFY_PYTHON="$GRAPHIFY_PYTHON" uv run --frozen python scripts/run_tests.py -- -q -rs tests/test_knowledge_plugin_cli.py tests/test_work_memory.py` and any new schema test module; ruff/format/mypy on touched Python.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch`; no push.

## GK-03 — Guidance and evidence (AC6)

- Source: AC6, KG-10, deliverable 3; this unit.
- Outcome: current guide and packaged canonical skills describe only supported calls and the new truncation/reference/community/schema semantics; all skill JSON examples validate; documentation registry/generated reference current if the checker requires it; stage-005 implementation evidence records this repair without claiming E2E/token savings. Excludes adapter/schema code unless a checked example is invalid (then fix the example, not the schema).
- Inputs: independently reviewed GK-01 and GK-02 commits/tests. Do not treat parent prose as the current tree.
- Boundaries: writable `docs/guides/project-knowledge.md`, `docs/reference/plugins-and-tools.md`, `src/aether_agents/resources/skills/project-knowledge/SKILL.md`, `src/aether_agents/resources/skills/work-memory/SKILL.md` only if procedure/examples need it, `specs/005-project-knowledge-graphify/implementation.md`, `CHANGELOG.md`, and `docs/capabilities.toml` plus generated `docs/reference/capabilities.md` if `scripts/check_documentation.py` requires. Tests: `tests/test_knowledge_resources.py`, `tests/test_documentation.py` as needed. Preserve adapter/schema sources.
- Judgement: wording and example selection. Do not add `community_id: 0` as if it were a portable default. Do not document upstream-only recovery.
- Verification: skill examples `validate_arguments`; `uv run --frozen python scripts/check_documentation.py`; focused `tests/test_knowledge_resources.py tests/test_documentation.py`; no machine paths/credentials in public text.
- Dependencies: independently reviewed GK-01 and GK-02 (shared guidance files and example/schema coupling).
- Completion: local commit; same-card review; unit compatibility `patch` (docs/guidance for a compatible fix); no push.

## GK-INT — Terminal integration and closeout

- Source: AC5, AC7, AC8, deliverables 4–6; this unit.
- Outcome: integrated tree on the objective branch, full exact-Hermes gates, CI-green merge to `main`, #324–#327 reconciled only after merge, objective residue cleaned after durable evidence, graph refresh reported as navigation coverage. No release artifact.
- Inputs: independently reviewed GK-01, GK-02, GK-03 commits. Preserve each as its own commit; no squash/amend/rebase/history rewrite.
- Boundaries: integration-owned conflict/import/wiring/docs-path repairs that introduce no new behavior. Behavior gaps return as implementation rework.
- Verification: contract testing standard in full, including focused native set, complete `scripts/run_tests.py`, ruff, format, mypy, coverage ≥78% branch, `check_documentation.py`, `uv build`, public-artifact scan, `git diff --check`. Then git-github-closeout. Post-merge smoke of D29–D32 on exact `main`.
- Dependencies: decomposition root and all three independently reviewed implementation units.
- Completion: aggregate `release_impact=patch`, `release_action=defer`, `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary configured Supervisor/Implementer execution is authorized. Stop and return `needs-contract-revision` only for a genuine contract defect. Do not activate profiles, change providers/models, run extra live product probes, acquire dependencies, bypass checks, force-push, or publish a release.
