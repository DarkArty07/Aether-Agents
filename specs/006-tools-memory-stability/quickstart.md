# Verification and evidence path

## Prerequisites

Use the assigned project worktree and its exact contract/base. Keep tests in isolated
homes, databases and boards; CONTRIBUTING.md requires removing inherited dispatcher
routing from fixtures (aether_agents.lab.isolated_hermes_env is available). Never run
synthetic contention or guard-negative commands against live production state.

Resolve Python/venv, source paths and hashes before testing. Set up declared locked
dev dependencies in an isolated environment (`uv sync --frozen` for Aether); do not
install globally or silently skip async/native tests when their plugin is absent.
Native Graphify integration uses the existing provisioned isolated component or a
correctly prepared documented fixture, never an automatic semantic/provider call.

## Aether baseline and regression lane

From the repository root:

```bash
uv run --frozen pytest -q tests/test_knowledge_plugin_cli.py tests/test_observation_contracts.py tests/test_observation_reducer.py tests/test_observation_journal_storage.py tests/test_observation_brief_tool.py
uv run --frozen python scripts/run_tests.py
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen pytest -q --cov=aether_agents --cov-report=term-missing
uv run --frozen python scripts/check_documentation.py
uv build
 git diff --check
```

Use the existing bootstrap to authenticate the selected public Hermes source for the
full Aether suite; do not call an editable-source test run exact-baseline qualification.
Also test affected native integration against the exact maintained-fork candidate and
record its distinct revision. Preserve the committed coverage floor and all required
CI checks. Run applicable policy/public-artifact checks from policy.yml; no waiver of
an inherited failing baseline may be invented. A real external blocker is recorded.

The portable diagnostic fixture at fixtures/binding_privacy_probe.py is intentionally
RED on the inspected baseline. Run it from the repo with source/test helper imports:

```bash
PYTHONPATH=src:tests uv run --frozen pytest -q specs/006-tools-memory-stability/fixtures/binding_privacy_probe.py -p no:cacheprovider
```

Expected baseline: 5 failing causal assertions, 9 passing controls. Candidate: all
assertions pass, and native/tool-level boundaries in plan.md also pass. This is a
research fixture, not a replacement for production regression tests. Existing negative
controls are mandatory; any scope refinement changes the owning plan first.

## Maintained Hermes and issue-specific checks

From the clean maintained-fork candidate, use its declared dev/test environment and
existing relevant tests: tests/state/test_write_lock_patience.py, affected FTS/state
and compaction suites, tests/hermes_cli/test_gateway_restart_loop.py and terminal guard
suites, tests/tools/test_vision_tools.py and Codex adapter/transport/image-routing
suites located in that exact revision. Use test collection to resolve names rather
than silently substituting unrelated paths. Add causal tests for the actual fix.

- TS-389: run real guard functions and supervised terminal test doubles on harmless
  data and dangerous command strings. Never execute the dangerous strings.
- TS-382: demonstrate the proven product writer/append overlap in a temporary DB;
  compare pre/post candidate and verify complete transcript, concurrent tail, counts,
  ownership and rollback. A generic timeout demonstration is not causal acceptance.
- TS-275: prepare a valid nontrivial synthetic PNG with content not supplied in the
  question. Through the native provisioned tool/client, request interpretation.
  Record actual route, shape, correlation/status and expected/observed answer privately.
  Run a baseline, then the candidate and a focused confirmation after a demonstrated
  repair. Avoid blind retries; no route/model/provider change merely to obtain success.
- TS-373: native knowledge/memory calls must resolve the exact bound project; execute
  an isolated save/read and negative identity matrix. Graph availability is separate.
- TS-390: use exact project/contract identity in native aether_observe; require a readable
  current summary preserving histogram counts and coverage after safe candidate adoption.

## Acceptance evidence and closeout

Use evidence.md in this stage for each requirement: artifact location, source/candidate
and integrated revision, producer, exact command/tool action, observed result, limits,
independent review and authorized omissions. Keep private payload/log/endpoint/model
selection evidence out of Git. Native board/session receipts remain private side data.

Supervisor follows the graph's review model, integrates reviewed commits without
rewriting history, and runs the normal green GitHub closeout in both affected repos.
Each issue receives its own causal/candidate/integrated/runtime evidence. Do not close
#275/#382 merely because the research gate ended. Report scoped adoption and rollback,
then audit only objective-owned branches/worktrees; preserve pre-existing residue.
Morfeo applies contract-result-review before final owner acceptance. This document is
a runnable verification design, not a claim that future checks have already passed.
