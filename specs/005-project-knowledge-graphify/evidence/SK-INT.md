# SK-INT — terminal integration evidence

**Status:** Supervisor terminal integration record for Objective Contract
`oc_f2acfb5effb21f6d@v1`. This is evidence, not a release or readiness claim.

**Integrated candidate:** the reviewed unit commits below merged, in dependency
order, onto the objective branch without squash, amend or rebase.

| Unit | Reviewed commit | Integration merge |
| --- | --- | --- |
| SK-01 additive overlay compositor | `103b080` | `9276375` |
| SK-02 Hermes Responses adapter `HLP-420` | `88624fb` | `f5e8bb5` |
| SK-04 semantic manager plan/bounds/route/accounting | `b212b8a` | `a147329` |
| SK-03 snapshot lifecycle, migration, warnings | `0f103e4` | `86520c1` |
| SK-06 docs, 300-second reconciliation, policy manifest | `4089570` | `ce8968a` |

Supervisor breakdown `specs/005-project-knowledge-graphify/tasks.md` is its own
commit (`d87cf62`) on the integrated branch. The integrated tree equals the
reviewed cumulative tip plus only that breakdown.

## Deterministic and component gates

| Gate | Command | Observed |
| --- | --- | --- |
| Base manifest (CI step verbatim) | `.github/workflows/policy.yml` policy job, step 02 | exit 0 |
| Reproducible policy hooks | policy job, step 03 | exit 0 |
| R0 design baseline incl. markdown link/fence sweep | policy job, step 04 | exit 0 |
| Whitespace | `git diff --check 06938e8...HEAD` | exit 0 |
| Bytecode | `python -m compileall -q` on the CI file list | exit 0 |
| Types | `uv run --frozen mypy src/aether_agents` | 67 files, no issues |
| Lint | `uv run --frozen ruff check` on the CI file list | all checks passed |
| Format | `uv run --frozen ruff format --check` on the CI file list | 156 files already formatted |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` | passed |
| Offline knowledge qualification | `uv run --frozen python scripts/qualify_knowledge_expansion.py --json` | passed (14/5 catalog, two isolated fixtures) |
| Package build | `uv build` | wheel + sdist |
| Public-artifact scan | `scripts/check_public_artifacts.py` over tracked surface + 2 artifacts | passed |
| Aggregate exact-Hermes suite | `PYTHONPATH=<exact checkout> AETHER_GRAPHIFY_PYTHON=<0.9.54 component> coverage run -m pytest -q --ignore=tests/test_observation_performance.py` | 1743 passed, 9 skipped, 3 failed (see below) |
| Native Graphify worker lane | `<0.9.54 component>/bin/python -m coverage run --append -m pytest -q tests/test_graphify_worker_native.py` | 36 passed, 0 skipped |
| Coverage floor | `coverage report --format=total` | 79 (configured floor 78) |

### Aggregate-suite failures — pre-existing, unrelated

| Test | Local cause | Classification |
| --- | --- | --- |
| `tests/test_telegram_monitor_cli_plugin.py::test_d15r_fixture_and_environment_gaps_chain_end_to_end` | Reproduced identically on the clean base `06938e8` at the same worktree depth: `QualificationError` from the live product-runtime laboratory writers. The lane only runs when a live `home/.venv-hermes` interpreter is present, so public CI skips it (`product runtime interpreter not available`). | Pre-existing environmental, not candidate-caused |
| `tests/test_telegram_monitor_cli_plugin.py::test_d16t_lab_scheduler_stop_detects_cooperative_exit_and_records_status` | Passed on the clean base and on the candidate in isolation; failed once in the load-saturated aggregate run (the aggregate lane is load-sensitive in untouched monitor tests). | Load-sensitive pre-existing, not candidate-caused |
| `tests/test_telegram_monitor_delivery.py::test_exact_hermes_single_attempt_seam_never_replays_or_falls_back` | Invocation artifact: the local runner set `PYTHONPATH` to an explicit checkout without `AETHER_EXACT_HERMES_CHECKOUT`; with both pointed at the same verified checkout the test passes. | Local invocation artifact, not candidate-caused |

No failure touches `src/aether_agents/knowledge/`, and none reproduces on the
candidate in isolation with the CI-equivalent environment.

### Supervisor integration repair — route fixture binding (public CI)

The first pull-request run of the non-required `observation-qualification` job
showed five knowledge oracles failing only in the credential-free CI environment:
`test_d36_semantic_lifecycle_cache_and_enrichment`,
`test_d37_failure_preservation_timeout_exhaustion_malformed`,
`test_large_corpus_semantic_prepare_bounded_paging`,
`test_gx06_mixed_case_distinct_counts_and_paths` and
`test_gx06_split_file_conservative_coverage`.

Cause: those deterministic oracles bound only `semantic_auxiliary_task` and relied
on the pre-repair permissive routing. The accepted fail-closed route gate refuses to
cache or apply output whose effective route is unresolved, which is exactly what a
credential-free environment resolves to, so the oracles observed pending states
instead of the enrichment path they assert. This is a fixture gap, not a product
defect: the unresolved and mismatched route cases keep their own dedicated tests.

Supervisor integration repair (authored by Supervisor, therefore not covered by the
independent unit review): one explicit deterministic non-secret expected route
constant bound at the nine configuration sites inside those five oracles. No product
behavior, interface, acceptance criterion or shared decision changed.

Re-verification of the repair:

| Check | Command | Observed |
| --- | --- | --- |
| Five repaired oracles, credential-free | `env -u HERMES_HOME … HOME=<clean> scripts/run_tests.py -- -q tests/test_knowledge_regressions.py -k "<five>"` | 5 passed |
| Five repaired oracles, configured | same selection with the provisioned profile | 5 passed |
| Full knowledge lane, credential-free | `scripts/run_tests.py -- -q tests/test_knowledge_regressions.py tests/test_knowledge_semantic_manager.py tests/test_knowledge_failures.py tests/test_knowledge_plugin_cli.py tests/test_project_knowledge_engine.py tests/test_work_memory.py tests/test_knowledge_resources.py tests/test_knowledge_schema.py` | 362 passed, 3 skipped (GH unauthenticated, live auxiliary unprovisioned, networked install lane) |
| Knowledge lane, configured | same modules | 67 passed / 1 skipped (regression + manager modules) |
| Static | `ruff check`, `ruff format --check`, `mypy src/aether_agents` | clean; the test-invocation typing notes are identical on the clean base |

### Pre-existing CI failures on `main` (unchanged by this objective)

The `observation-qualification` job is red on `main` itself for the collaboration
scope (`tests/test_hermes_editable.py` ×11 and
`tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`).
Those failures are reproduced on an untouched `origin/main` checkout and are not
caused by this objective; the required merge checks (`policy (3.11)`, `policy (3.12)`,
`policy (3.13)`, `pull-request-target`) pass on this pull request.

## Bounded live semantic canary

Machine-readable record: `specs/005-project-knowledge-graphify/evidence/SK-INT-live-canary.json`.

* Disposable two-file fixture (`README.md` documents the requirement to call
  `canary_process`; `workflow.py` defines it), registered in a private temporary
  state/cache root through the production `KnowledgeService` path — no repository
  state was read or written.
* Configured primary auxiliary route resolved (non-secret digest recorded), one
  configured update, **one new live call total** against an authorized ceiling of four.
* Receipt: `semantic.state=complete`, one validated chunk covering both files, zero
  opaque failure categories, 1579 total tokens, 14.99 s elapsed — inside the
  300-second budget and the host bound.
* Canonical structural projection identical before/after (5 nodes, 4 links, equal
  digest); no LLM-only attribute appears on a structural record.
* Independently inspected relation: the persisted overlay contains exactly one
  semantic edge `readme -> workflow_canary_process` (`references`, `INFERRED`),
  which matches the fixture sources and is the documented requirement -> code link.
* Unchanged repeat: `outcome=unchanged`, 0.34 s, **zero new calls** (router attempt
  counter unchanged; the cached receipt retains the first run's usage).

Skipped lanes are reported as skipped, never as passing. No live call is made by
any implementation unit; the canary above is the only provider-backed step.

## Release conclusions

* `release_impact = patch` — internal correctness repair plus additive receipt
  fields; no public control, action or envelope field was added or removed.
* `release_action = defer` — no release is prepared or published by this objective.
* `release_channel = none`.

## Omitted closeout steps

* Package publication, tag, deployment, provider/model/Router change, force
  operation and destructive cleanup: outside the Objective Contract; not attempted.
* Observation-qualification harness lane (`scripts/qualify_observation.py test`):
  not re-run locally; it exercises observation capture, which this objective does
  not modify, and it remains a required public check on the pull request.
