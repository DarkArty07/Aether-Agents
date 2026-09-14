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

## Reception continuation — native plugin canary (AC-07 / AC-08 / AC-10)

Morfeo's reception of the merged result at `3240bbac8e3835745541c8d062bd7bf289d76bc2`
found AC-10 not demonstrated live and the `HLP-420` live boundary ambiguous, so it
reopened #420 and #423 pending exactly one bounded continuation — at most one
additional live semantic auxiliary call on the unchanged configured primary route.
This section records that continuation. No product source, behavior, interface,
acceptance criterion, configuration or shared decision changed; only this evidence
pair changed.

### Isolated disposable runtime (no live mutation)

| Element | Exact identity |
| --- | --- |
| Clean maintained-fork source | fork `aether-main` head revision `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`, clean working tree |
| Applied patch | `patches/hermes/HLP-420-responses-terminal-fidelity.patch`, SHA-256 `e0caa198c9c61e1235cedbc021c6e1a4d35b114c9c155df3fe1515040c420fa6`; `git apply --check` passed at that revision; preimage `agent/auxiliary_client.py` SHA-256 `93275ed4d6c5d7a84b8607b3f0fcbad998bfdd2f52f6e2516372de66ca6b7ec0` equals the recorded reconstruction input; postimages `agent/auxiliary_client.py` `2c5dfee035dd47a8bb8f2e652983f53f3ebc3b90c06adc87176f4cbf3adc0a30` and `tests/agent/test_auxiliary_client_responses_terminal_420.py` `1c8a21d09950a7bef2fbbac3b03073970f23e3eab32fd15e6e2f12cc4a1434e6` equal the reviewed candidate's recorded hashes |
| Merged Aether source | revision `3240bbac8e3835745541c8d062bd7bf289d76bc2` (this objective's merge), clean |
| Runtime | fresh disposable Python 3.11.15 environment containing only those two source trees; the Aether plugin entry point resolved from installed distribution metadata, and the loaded adapter module proved inside the disposable fork tree |
| Live state | no live profile, service, board, editable runtime or Router configuration was read, reloaded, modified or activated; Router telemetry was inspected read-only |

The disposable **Hermes SessionDB** is a real `SessionDB` instance created in the
disposable profile home. Every session row it holds — the zero-call probe sessions and
the canary session — records the fixture repository root as its native workspace, and
only the canary session carries a usage row. The fixture is a private disposable
two-file Git project (`README.md` states the intake requirement to call
`canary_process`; `workflow.py` defines it), marker-registered in the disposable Aether
state root.

### Invocation — registered native plugin path, not `KnowledgeService`

1. Plugin discovery through the native entry-point group (`hermes_agent.plugins`),
   loading `aether-project-knowledge` → `ctx.register_tool` registers tool
   `project_knowledge` in toolset `aether_knowledge`, handler module
   `aether_agents.knowledge.hermes_plugin` (verified before dispatch).
2. The ordinary ambient accounting context is published exactly as the agent loop
   publishes it at turn entry — `agent.aux_accounting.set_accounting_context(
   session_db, session_id)` with the real disposable `SessionDB` and the session id.
3. The tool is invoked through the runtime's own tool-call executor,
   `model_tools.handle_function_call("project_knowledge", …)` (which routes to
   `tools.registry.dispatch`) with the runtime's `task_id` / `session_id` /
   `tool_call_id` / `turn_id` arguments — the same surface a model-requested call
   uses, so the plugin's native session binding, `context_for_session`,
   `knowledge_cancel_scope` and the Hermes auxiliary client are all exercised.

A zero-budget probe (300-second budget lowered to zero for the probe only) ran the
same path first and confirmed the prerequisites: native registration, native session
binding, component configuration and dispatch all worked with **zero** model calls,
no usage row and an honest pending receipt. Only then was the single live call spent.

### Correlated evidence for the single live call

| Source | Observed |
| --- | --- |
| Content-free adapter terminal state (in-process observation of the auxiliary response the patched adapter returned) | one call; `status=completed`, `finish_reason=stop`, no `incomplete_reason`, no `AuxiliaryResponsesTerminalError`, response content present, usage present |
| Semantic receipt (native `project_knowledge` result) | `outcome=updated`, `semantic.state=complete`, one validated chunk covering both fixture paths, no failure category counted, 13.678 s (inside the 300-second budget), input 948 / output 578 / total 1526 |
| Router attempt (read-only telemetry, the only `web_extract` request in the window) | one attempt, provider `codex`, model `gpt-5.6-luna`, streamed Responses, `outcome=cancelled`, `telemetry_state=partial`, provider-reported input 948 / output 578 / provider total 1526 / reasoning 271 |
| Disposable Hermes SessionDB (`session_model_usage`, read-only SQLite read-back) | exactly one row for that session and task: model `gpt-5.6-luna`, billing provider `custom`, `api_call_count=1`, input 948, output 578, reasoning 0 in its own column — attributed exactly once and reconciling with the receipt |

Structural projection of the persisted snapshots (independent analyzer, nodes *and*
links, LLM-origin records excluded): the composed snapshot preserves the base
structural projection exactly (5 nodes, 4 links, equal digest
`f27db7dfe3f72f16ae61e67c10726ec4876dbc96488e916ee4a6f763ae58cbb1`, no missing node
or link), persists one additive LLM link `readme -> workflow_canary_process`
(`references`, `INFERRED`) that matches the fixture sources, and leaks no LLM-only
attribute onto a structural record.

Zero-call repeat on identical inputs: `outcome=unchanged` in 0.1 s with **zero**
auxiliary calls attempted, the SessionDB row unchanged (`api_call_count=1`, same
usage) and **zero** new Router requests in the repeat window. Total live semantic
auxiliary calls for the continuation: **1**.

### Conclusions

* **AC-07 / AC-08 (#420) — qualified live.** The patched adapter observed a completed
  Responses terminal (`status=completed`, `finish_reason=stop`) and returned its
  answer; a `failed`/`cancelled` terminal raises the typed
  `AuxiliaryResponsesTerminalError` instead of a successful `stop`, and an
  incomplete/max-output or content-filtered terminal maps to `length`/`content_filter`
  — documented by the reviewed fixture matrix, which passes on this exact disposable
  runtime (`tests/agent/test_auxiliary_client_responses_terminal_420.py`: 25 passed;
  the neighbouring auxiliary-client suite: 181 passed) and whose recorded causal RED
  on the unchanged base is 20 failed / 5 passed.
* **Router `cancelled` is a stream-close classification, not a provider terminal.**
  The local Router's streaming wrapper maps an `asyncio.CancelledError` — i.e. the
  client closing the response stream after the final — to `outcome=cancelled` /
  `telemetry_state=partial` (`src/aether_router/app.py`, `except asyncio.CancelledError`
  region) *after* the provider usage has been reported. The same shape recurs on other
  short auxiliary calls whose results are demonstrably consumed (e.g.
  `title_generation`), and the canary's own adapter observation independently saw a
  completed terminal. This settlement is what the earlier canary's ambiguity
  required: the receipt's `complete` was truthful, and the Router label describes
  stream teardown, not the response's terminal status.
* **AC-10 (#423) — qualified live.** The auxiliary response's usage was attributed
  exactly once to the originating session/task in a real Hermes SessionDB, input and
  output tokens reconcile exactly with the operation receipt (948 / 578), and the
  reasoning column is preserved separately.
* **Documented limit (no repair required).** The provider-reported reasoning detail
  (271 on the Router side) never reaches the Aether layer on this auxiliary route: the
  auxiliary Responses shim synthesizes its response usage from input/output/total only,
  so both the receipt and the SessionDB record 0 in the separate reasoning column. The
  Aether extraction layer itself preserves reasoning whenever a response carries it
  (`completion_tokens_details.reasoning_tokens`, covered by the deterministic oracle),
  and it does not change the required exactly-once attribution or the
  input/output/total reconciliation. This is a pre-existing auxiliary-transport detail
  gap, identical in kind to the first canary (Router 335 vs recorded 0), and is **not**
  caused by `HLP-420`; it is recorded here rather than repaired inside this
  continuation.
* No code defect was found in the qualified paths, so no corrective implementation was
  created and no behavioral change was integrated.

### Evidence limits

* One canary attempt. A live provider-side `cancelled` / `incomplete` /
  content-filtered terminal was not induced (no provider control is authorized), so
  the *mapping* authority for those terminals remains the reviewed deterministic
  fixture matrix, not this live run.
* The live run used a private disposable fixture, not a production corpus; it
  qualifies the transport/accounting boundary, not corpus-scale yield.
* The native tool call was executed through the runtime's tool-call executor with a
  synthetic tool-call identity rather than a full model turn, so no additional
  main-loop live call was spent; everything after the tool-call entry (plugin
  handler, session binding, semantic manager, auxiliary client, accounting
  chokepoint) is the unmodified runtime path.

## Morfeo reception record (AC-07 / AC-08 / AC-10)

Recorded by Supervisor from Morfeo's reception of the merged result at
`3240bbac8e3835745541c8d062bd7bf289d76bc2`. The reception verdict is Morfeo's; this
is its record at the existing evidence location, not a substitute for it.

* **Direct Morfeo evidence.** The merged canary receipt recorded one complete
  semantic result (949 input + 630 output = 1579 provider total tokens); Router
  request history for the uniquely matching attempt reported `outcome=cancelled` with
  the same totals and 335 reasoning tokens; `SK-INT.md` recorded that the canary
  invoked the production `KnowledgeService` directly rather than the registered
  native plugin; read-only inspection of all three Aether profile SessionDBs found no
  matching `web_extract` row after the canary window; `HERMES_LOCAL_PATCHES.md`
  records `HLP-420` as source-only, so the patched adapter was not active in that
  canary.
* **Disposition.** AC-10 was not demonstrated live — an evidence gap explicitly
  distinguished from a code defect — and AC-07/AC-08 stayed ambiguous on the live
  boundary because the patched adapter had not been active. #420 and #423 were
  reopened pending this continuation; the four already-supported closures were left
  untouched.
* **Reused pipeline evidence, retained as valid.** The deterministic `HLP-420`
  fixture matrix and the portable patch reconciliation/digests were *not* the basis
  of the reopening and were not invalidated; the supplementary accounting oracles
  remain useful. They are reused here as prior pipeline evidence, not re-verified by
  Morfeo directly.
* **Limit.** Morfeo did not operate the patched runtime or make a live call during
  reception, and no live provider-side cancelled terminal was induced by this
  continuation either.

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
