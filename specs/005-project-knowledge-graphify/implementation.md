# Graphify integration: local implementation and verification

## Scope and state

This record covers the owner-authorized implementation on `feature/graphify-project-knowledge`, based on Aether commit `ead2b59b7f771f4dd940b49423121f92d1a9ad8f`. It is a local structural integration candidate, not a public release, a live-profile activation or completion of the PD-74 gate. The historical [plan](plan.md) and [audit research](research.md) explain intent; the [specification](spec.md), [user guide](../../docs/guides/project-knowledge.md) and [capability registry](../../docs/capabilities.toml) distinguish current behavior from the wider plan.

No live Hermes profile, running agent, board, credential or service was changed. The owner subsequently authorized reconciliation with `main` and source integration while retaining opt-in profile activation. Until the Git transition completes, work remains on the feature branch outside the active main checkout.

## Delivered code and procedures

- `aether-project-knowledge` is a third native plugin entry point in the existing Aether distribution. It gives all three roles the same `project_knowledge` and `work_memory` schemas without importing Graphify during registration.
- Graphify Python 0.9.54 is a separate optional component. The managed installer uses the package-owned dependency/hash lock and a local Python 3.11 interpreter. The manager remains Hermes-free for help and metadata commands. No install happens inside a tool call.
- Project knowledge resolves the exact native session workspace or an explicit operator binding against the existing project registry. Attached worktrees must share the registered Git common directory. Model arguments cannot override project, role or filesystem destinations.
- All roles can update committed structural snapshots. Stable external locking prevents the audited waiting-writer inode race in managed operations. Finalized manifests and revision pointers separate builds from published data. Repeated requests for the same view/revision reuse the snapshot; divergent worktrees do not overwrite it.
- Scope is bounded regular Git source blobs, including supported Markdown headings/links. The worker does not execute source code or project hooks. Private runtime homes, notes, logs, dependencies and high-confidence credential patterns are excluded; this is not a complete secret detector or an OS sandbox.
- Work notes retain original Markdown and attributable structured records. Effective revisions support lexical search, complete paginated reads, optimistic correction, private signal reflection and operator export/delete. Temporary implementers share the role/project namespace without sharing a Hermes home.
- Reflection invokes the fixed Python function with `graph_path=None`, not the CLI's autodetecting default. The replacement solution, rather than merely the correction reason, reaches the native correction signal. Private notes and learning sidecars do not enter the technical graph.
- All three portable SOUL resources include availability-aware usage and maintenance guidance. The `project-knowledge` and `work-memory` canonical skills are packaged and materialized with the existing mechanism. Templates keep the plugin disabled until explicitly configured.
- Current guides, CLI/plugin references, integration identity, authority and R9 were updated. The generated capability reference matches the registry renderer byte-for-byte.

## Additional regressions fixed during continuation

1. A note tied to the current commit now reports `revalidate` if tracked source changes exist without a new commit.
2. A correction retains its reason in Aether metadata but passes the replacement lesson to Graphify's correction aggregation.
3. Published graph reads reject redirected parent paths even when graph bytes otherwise match the recorded digest. Malformed node/manifest records do not become valid snapshots.
4. UTF-8 worker requests avoid ASCII-escape expansion and are bounded before process creation. Timeout/cancellation terminates the managed child process group.
5. Metadata-only status does not manufacture an unavailable executable path; it can operate without a component backend.
6. Packaging assertions preserve and explicitly materialize all eight canonical skills: the six resources on current `main` plus `project-knowledge` and `work-memory`. Platform expectations retain Linux-only scope for the two knowledge skills rather than claiming untested platforms.
7. `work_memory.save` now requires an opaque idempotency key. Exact sequential, concurrent and post-restart retries return one current note; changed-payload key reuse fails, independent equal contributions remain distinct, and only key/payload digests are persisted.
8. The historical draft skill paths contain replacement notices instead of a second executable procedure. The package-owned resources are the sole canonical copies.

## Main reconciliation continuation — 2026-09-05

The integration target inspected for this continuation is `main` at `3a124fb737e0705950fa74bbc276a89994c2d2fc`. The feature branch originally diverged from `ead2b59b7f771f4dd940b49423121f92d1a9ad8f`; current `main` had eleven later commits and the Graphify branch one implementation commit before the continuation changes.

The six predicted content-conflict surfaces were reconciled deliberately rather than by selecting one side wholesale:

- `CHANGELOG.md` retains the contract-design/execution procedure entry and adds Graphify plus idempotent note saves.
- `docs/capabilities.toml` and its generated reference retain current capability records, add the four knowledge records and enumerate eight canonical skills.
- `src/aether_agents/lifecycle.py` materializes all eight resources.
- Lifecycle and packaging tests use the same eight-resource allowlist and retain the three-plugin package contract.
- Each SOUL retains the current HLP-280 bounded-investigation language alongside the role-specific project-knowledge guidance.

The owner's instruction to integrate the reconciled candidate into `main` is recorded in [spec.md](spec.md) as the bounded PD-74 exception for this capability. It does not activate live profiles, semantic extraction, provider spending, deployment or release publication.

## Executed verification

The development environment was installed with `uv sync --frozen`. Exact-Hermes tests use release `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade`, verified by the repository bootstrap. Native Graphify checks use the audited isolated 0.9.54 interpreter, and the explicit component installation test also installs original PyPI distributions using hashes in a disposable location.

### Full suite

The completed full run used:

```bash
AETHER_GRAPHIFY_PYTHON="$GRAPHIFY_PYTHON" AETHER_TEST_COMPONENT_INSTALL=1 \
  uv run --frozen python scripts/run_tests.py -- -q --tb=short -rs
```

An initial completed full checkpoint passed **865 tests and 373 subtests**, with two existing conditional skips. After adding failure-path and native-worker tests, the final complete coverage of the test inventory was executed in disjoint blocks to stay within the tool's per-call duration limit:

| Final block | Result |
| --- | --- |
| All tests except lifecycle and performance | 789 passed; 3 skipped; 373 subtests passed. |
| Lifecycle excluding its three installer-heavy tests | 87 passed; the remaining three selected separately. |
| Three installer-heavy lifecycle tests | 3 passed. |
| Uninstrumented performance tests | 3 passed. |
| Worker tests in the isolated Graphify environment | 13 passed. |

The manager/exact-Hermes suite therefore passed **882 tests**, plus **13 native worker tests** in their required component environment: **895 passed tests overall**, and 373 subtests. Of the three skips reported by the manager suite, one is that separately executed native worker module; the other two are existing conditional lanes for missing session-affinity support in the exact public Hermes release and 100k qualification assigned to the dedicated Python 3.11 CI lane. No failure was converted into a skip.

The native worker module intentionally runs with Graphify's own interpreter; the Hermes-free manager environment does not install or import engine dependencies merely to avoid that separate lane. Final XML reports were generated outside the repository for each block.

### Coverage

An initial all-at-once pytest-cov run hit the tool's execution limit. A later subprocess-instrumented attempt failed when combining statement and branch data. Neither attempt is claimed as a passed run.

A coherent replacement measurement used `coverage run --branch --source=aether_agents -m pytest` in two groups, reusing the repository bootstrap's verified Hermes checkout and environment, then `--append` for supplementary tests and the isolated worker lane. No coverage floor or exclusion was changed. The accumulated report was **78.07%**, passing the existing **78%** threshold.

One pre-existing observer callback latency assertion exceeded 5 ms under instrumentation (observed p95 about 7 ms); the complete uninstrumented suite passed it. The measurement is a coverage pass, not a claim that the instrumented performance run was green. The original latency threshold remains unchanged.

The isolated worker lane is important: production deliberately strips instrumentation/config environment variables from that subprocess, so tracing only the manager would falsely leave its executed code at zero coverage. The explicit native test lane measures the real worker functions with the original Graphify package, not a fabricated replacement.

### Static, packaging and documentation checks

The following commands were executed successfully at the checkpoint:

```bash
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen python scripts/check_documentation.py
uv build
uv run --frozen python scripts/check_public_artifacts.py \
  --artifact dist/aether_agents-0.24.0-py3-none-any.whl \
  --artifact dist/aether_agents-0.24.0.tar.gz
```

The generated reference was produced from `scripts.check_documentation.render` and applied through the file-edit tool; the normal documentation checker confirms exact equality. The public scan covers both built artifacts, including added files not yet tracked by Git. The integration index's expected digest was deliberately updated for the authorized change, not removed.

### Main-reconciliation qualification checkpoint

After closing save idempotency and reconciling current `main` behavior into the candidate files, the following fresh checks completed:

| Lane | Result |
| --- | --- |
| Exact-Hermes suite excluding lifecycle, performance and native worker modules | 795 passed; 2 pre-existing conditional skips; 373 subtests passed. |
| Exact-Hermes lifecycle module | 90 passed. |
| Uninstrumented performance module | 3 passed. |
| Native worker under the isolated Graphify 0.9.54 interpreter | 13 passed. |
| Total executed test inventory | 901 passed; 2 conditional skips; 373 subtests passed. |
| Ruff check / format check | Passed; 127 files formatted. |
| Mypy source gate | Passed; 50 source files checked. |
| Documentation registry/reference | Passed with exact generated equality. |
| Accumulated branch coverage | 78%, meeting the unchanged 78% project floor. |
| Wheel and sdist build | `aether_agents-0.24.0` artifacts built successfully. |
| Public artifact scan | Passed for tracked surface, wheel and sdist. |

The coverage run executed the performance module, but callback instrumentation raised its pre-existing p95 sensitivity from the uninstrumented passing result to 5.94 ms against the 5 ms threshold. That instrumented performance invocation is not reported as green and no threshold was changed; the separate ordinary performance lane passed 3/3. A prior `pytest-cov` attempt also completed 794 tests before its subprocess combiner rejected mixed statement/branch data. The successful replacement used one external coverage data file with direct `coverage run --branch --source=aether_agents` blocks and the native worker append.

These results qualify the reconciled feature-tree content before the Git merge operation. Because non-overlapping commits from `main` enter only when the histories are joined, the final merged tree must receive a post-merge smoke/documentation check before `main` is declared complete.

## Graphify boundary and contract repairs (#324–#327, GK-01–GK-03)

Following authorization under Objective Contract `oc_7beb699ef34a7f04@v2` on base `ccd862b7e295669ec9dcc3d6cdf7145636614354`, the Graphify knowledge-tool integration boundary was repaired across three contract-derived implementation units:

### Delivered repairs

1. **GK-01 Envelope adapter (D29–D31, #324–#326, commits `ea4ec89`, `b9143c2`):**
   - **Cumulative truncation (D29, #324):** `truncated` is computed cumulatively: it is `true` if Graphify natively omitted nodes or lines at the requested budget, if Aether's 32,768-byte content ceiling was reached, or if visible source items reached the 50-reference cap. Complete-over-budget native responses remain `truncated=false` with an explicit warning.
   - **Supported recovery wording (D29, #324):** Native guidance citing unsupported upstream features (`context_filter`, `get_node`, direct graph paths, CLI `--budget`, MCP commands) is stripped and normalized to supported Aether actions: narrower `question`, higher `budget_tokens` (128–8000), or `explain` on a returned node.
   - **Structured provenance (D30, #325):** All six source-bearing actions (`query`, `explain`, `neighbors`, `community`, `path`, `impact`) extract and return project-relative, revision-bound, deduplicated `{path, location, revision}` references in stable order. For `path`, references include both path nodes and traversal relation sites. The 50-reference cap is enforced and never silent: exceeding 50 items sets `truncated=true` and emits an explicit warning. No private or snapshot-internal absolute paths escape into references.
   - **Community discovery (D31, #326):** `explain` includes `resolved_node` with `{id, community_id, community_name}` (community fields are `null` if unclassified). `community` accepts the snapshot-local `community_id` and returns `community` with `{id, name, node_count}` matching the request. IDs are snapshot-local and not portable across rebuilds.

2. **GK-02 Discriminated schemas (D32, #327, commit `2810832`):**
   - **Action-discriminated branches:** Canonical parameter schemas retain root `type=object`, `additionalProperties=false`, `required=["action"]`, and the full property union, while adding `oneOf` branches whose required and allowed properties match `_ACTION_FIELDS` for all 8 knowledge actions and 5 memory actions.
   - **Sanitizer robustness:** Every field description names the actions that accept it. When Hermes `sanitize_tool_schemas` strips top-level combinators for strict LLM providers, action and field descriptions remain informative, while runtime `validate_arguments` strictly rejects inapplicable arguments and identity-injection attempts.
   - **Draft 2020-12 and runtime parity:** A comprehensive 81-case test matrix verifies that canonical JSON Schema validation and runtime `validate_arguments` accept and reject identical argument combinations.

3. **GK-03 Guidance and canonical skills (AC6):**
   - **Skill updates:** Packaged canonical skills `project-knowledge` and `work-memory` reflect action-discriminated parameter schemas, query→explain→community discovery, cumulative truncation, the 50-reference cap, and supported recovery actions.
   - **Example validation:** All skill JSON examples validate against registered tool schemas via `validate_arguments`. Community examples use illustrative snapshot-local IDs rather than documenting `community_id: 0` as a default.
   - **Documentation alignment:** `docs/guides/project-knowledge.md` and `docs/reference/plugins-and-tools.md` document supported actions, arguments, truncation semantics, references, and discovery workflows. Verified via `scripts/check_documentation.py`.

## Current semantic and exploration expansion (GX-01–GX-04)

The reusable expansion authorized by Objective Contract `oc_c0abec2179f6b09c@v1` is
implemented against Graphify 0.9.54 without modifying Graphify, Hermes or the lockfiles:

- **GX-01 / D33:** `project_knowledge` exposes fourteen action-discriminated project
  operations while `work_memory` retains five operations. Draft 2020-12 validation,
  runtime `validate_arguments` and sanitizer-safe descriptions agree; query-only
  `context_filter`, path-only `undirected`, identity rejection and the tree/detail boundary
  are explicit.
- **GX-02 / D34 and D39:** The native worker supplies stats, bounded centrality, traversal,
  relation and direction controls, semantic fragment handling, PR impact computation and
  graph/tree HTML export. Native references and truncation remain additive envelope data.
- **GX-03 / D34–D39:** The manager publishes immutable revision-bound snapshots and additive
  `aether.project-knowledge.v1` objects, optionally resumes configured auxiliary semantic
  work with fingerprint/cache/failure preservation, and provides verified read-only GitHub
  views and managed visualization artifacts. Structural mode remains no-model; missing
  auxiliary or GitHub access is unavailable rather than a fallback.
- **GX-04 / AC8 and D40:** Current guides, capability registry/reference, changelog and
  packaged skills describe the 14/5 catalog and semantic boundaries. The reproducible
  `scripts/qualify_knowledge_expansion.py` lane validates all examples, uses two disposable
  portable fixture IDs through the production service, and separates deterministic offline
  evidence from optional live auxiliary/GitHub evidence.

The qualification lane deliberately reports availability and skips rather than converting
missing provider or GitHub access into a pass. It makes no token-saving, universal-quality,
live-agent adoption or release claim.

### GX-04 execution evidence

| Lane | Observed result |
| --- | --- |
| `scripts/check_documentation.py` | Passed; generated capability reference matches the registry. |
| `tests/test_knowledge_resources.py` and `tests/test_documentation.py` | 18 passed; 1 explicit networked component-install skip. |
| `scripts/qualify_knowledge_expansion.py --json` | Passed offline; 14 project actions and 5 memory actions validated, 5 boundary cases rejected, two isolated fixtures updated through the production service, and graph/tree exports plus memory checks completed. |
| `scripts/qualify_knowledge_expansion.py --live-auxiliary --json` | Offline lane passed; live auxiliary was honestly skipped as unavailable in this environment. GitHub was skipped when no project id was supplied. |
| Script static gates | `ruff check`, `ruff format --check`, `compileall`, public-artifact scan and `git diff --check` passed for the candidate. |

### Boundaries and exclusions

- Upstream Graphify 0.9.54 and Hermes baseline `v2026.8.18` remain completely unmodified.
- No new public tool, action, or CLI command was added.
- No live-agent E2E, token-savings, or universal model-backed quality claims are made.
- Unit compatibility impact is `patch` (compatible envelope/schema/guidance repairs). Publication and aggregate release decisions remain deferred to terminal supervisor closeout.

## What remains outside demonstrated behavior

- Semantic extraction is optional and requires an explicitly configured auxiliary; the default packaged configuration remains disabled. Live-agent E2E and source-supported semantic quality still require the live qualification lane and independent review.
- No actual Morfeo/Supervisor/Implementer LLM conversations were run for this capability. Real plugin registration and dispatch surfaces were tested without model calls; that is not a behavioral E2E with autonomous agents.
- No token savings, long-horizon quality gain or large-repository scaling claim is made. Query output uses byte limits and token estimates, not exact provider accounting.
- New revision builds recapture the bounded corpus. Reuse is implemented for identical view/revision snapshots; incremental cache seeding across arbitrary revisions remains an optimization to qualify.
- Dirty-worktree content is not captured as an authoritative snapshot. It is explicitly signaled for direct reading. Worktree/commit separation and failed-build recovery are tested.
- No shared learning overlay, vector service, graph merge across projects, HTTP daemon, project hook installer or automatic skill promotion is introduced.
- Component uninstallation/garbage collection and advanced knowledge migration are not exposed as completed features. Disablement preserves data. Deletion cannot remove independently exported copies or external backups.

These limits are also present in current user-facing documentation. The owner authorized source integration into `main`; that authorization does not activate profiles, deploy, publish a release or establish any unmeasured quality claim.
