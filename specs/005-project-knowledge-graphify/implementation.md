# Graphify integration: local implementation and verification

## Scope and state

This record covers the owner-authorized implementation on `feature/graphify-project-knowledge`, based on Aether commit `ead2b59b7f771f4dd940b49423121f92d1a9ad8f`. It is a local structural integration candidate, not a public release, a live-profile activation or completion of the PD-74 gate. The historical [plan](plan.md) and [audit research](research.md) explain intent; the [specification](spec.md), [user guide](../../docs/guides/project-knowledge.md) and [capability registry](../../docs/capabilities.toml) distinguish current behavior from the wider plan.

No live Hermes profile, running agent, board, credential or service was changed. Work stays on the feature branch, outside the active main checkout. The three unrelated skills already present in the base were preserved; this change does not silently expand their lifecycle materialization.

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
6. Packaging assertions preserve the extra skills inherited from the branch base while explicitly testing the five materialized resources. Platform expectations retain Linux-only scope for the new skills rather than claiming untested platforms.

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

## What remains outside demonstrated behavior

- No model-backed semantic document extraction is configured. `configured` and `structural` modes both use the implemented local structural path, with semantic coverage pending.
- No actual Morfeo/Supervisor/Implementer LLM conversations were run for this capability. Real plugin registration and dispatch surfaces were tested without model calls; that is not a behavioral E2E with autonomous agents.
- No token savings, long-horizon quality gain or large-repository scaling claim is made. Query output uses byte limits and token estimates, not exact provider accounting.
- New revision builds recapture the bounded corpus. Reuse is implemented for identical view/revision snapshots; incremental cache seeding across arbitrary revisions remains an optimization to qualify.
- Dirty-worktree content is not captured as an authoritative snapshot. It is explicitly signaled for direct reading. Worktree/commit separation and failed-build recovery are tested.
- No shared learning overlay, vector service, graph merge across projects, HTTP daemon, project hook installer or automatic skill promotion is introduced.
- Component uninstallation/garbage collection and advanced knowledge migration are not exposed as completed features. Disablement preserves data. Deletion cannot remove independently exported copies or external backups.

These limits are also present in current user-facing documentation. A local package/verification result does not grant authority to activate profiles, deploy, merge main, push or publish a release.
