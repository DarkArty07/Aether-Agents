# Validation quickstart: Lab/Monitor retirement

These are the proposed runnable checks for the implemented candidate, not evidence that
they have already passed. Run from its assigned repository worktree with provisioned
access and a supported Python 3.11–3.13 interpreter. Use `uv sync --frozen`; do not alter
the dependency lock or install into system Python to work around an unrelated host.

## Focused subtraction/preservation checks

After implementing the design, use the existing test owners (new isolation tests, if
needed, join this set):

```sh
uv run --frozen python scripts/run_tests.py -- -q \
  tests/test_knowledge_session_binding.py \
  tests/test_authorized_cleanup.py \
  tests/test_observation_packaging.py \
  tests/test_documentation.py \
  tests/test_public_artifacts.py \
  tests/test_release_bundle.py \
  tests/test_lifecycle_profile_transfer.py \
  tests/test_mixed_version_lifecycle_qualification.py
```

Exercise the changed lifecycle plugin-identity cases in their existing test owner as
well. A skipped native knowledge integration prerequisite is disclosed, not a PASS;
retain the deterministic isolation-helper coverage regardless. Do not use the removed
Lab/Monitor tests or scripts as prerequisites.

The independently retained KG-19 knowledge fixture is not a Lab scenario and lives
outside the default `tests/` collection. Once its Lab imports are removed, run its
existing deterministic tests without any model-spend flag:

```sh
uv run --frozen python scripts/run_tests.py -- -q \
  specs/005-project-knowledge-graphify/fixtures/e01_morfeo_orientation_lane.py
```

Record each result or skip honestly. Do not run the fixture's optional live E01 suite,
claim agent behavior was qualified, or demand a new provider-backed campaign.

The packaging fixture already builds wheel/sdist and checks isolated installs. Extend
its existing assertions to require absence of retired modules/resources/entry points,
exact current three-plugin metadata, ordinary unknown-command refusal for `monitor`,
and functioning retained CLI/import surfaces. Do not write a new packaging harness.
Use existing lifecycle fixtures to prove exact historical-four/current-three validation
and refusal of unknown/mismatched identities without touching an installed release.

## Integrated repository gate

Since lifecycle, packaging and the literal policy manifest change, the existing project
standard requires one integrated full bootstrap. Combine coverage rather than repeat
another full suite just for the counter:

```sh
uv run --frozen python scripts/run_tests.py -- -q \
  --cov=aether_agents --cov-report=term-missing
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen python scripts/check_documentation.py
uv build --out-dir .aether/tmp/lab-monitor-retirement/dist
for artifact in .aether/tmp/lab-monitor-retirement/dist/*.whl \
                .aether/tmp/lab-monitor-retirement/dist/*.tar.gz; do
  uv run --frozen python scripts/check_public_artifacts.py --artifact "$artifact"
done
git diff --check
```

The scanner's repeatable `--artifact` flag is defined in
`scripts/check_public_artifacts.py:76-82`. Reuse the packaging fixture's built artifacts
instead of the separate `uv build` when their
exact revision and outputs cover this check. Check destination capacity first, keep
worker scratch paths distinct, and remove owned disposable outputs after evidence is
preserved. Do not change coverage thresholds, CI-selection semantics or required checks.

The literal repository inventory is checked by the existing `Validate canonical base
manifest` workflow step. Reconcile removed paths and any specifically added test helper;
no wildcard widening or bypass. The public documentation reference is generated from
`docs/capabilities.toml` with `scripts/check_documentation.py --write`, then checked without
`--write`. Any unrelated baseline failure is reported with its actual output rather
than weakening a gate.

## Decisive result and closeout

- Wheel/sdist and current callable surface contain neither retired subsystem.
- Retained commands/plugins/tests and old/new exact identity checks pass as specified.
- Native Hermes cron, gateway/Telegram interaction, notifications, private configuration,
  live jobs, current release selector and historical data are unchanged by this work.
- Current documentation/manifest/capability checks agree with the implemented source.
- Supervisor records actual commands, results, revisions, producers, intentional test
  removals, historical references and untested limits; normal required PR checks and
  green merge are verified without bypass. Local integration is not terminal closeout.
- Morfeo reviews the exact merged result against RET-01–RET-07 and the finalized contract.

No Telegram message, Monitor reactivation, live update/rollback rehearsal, new release,
provider probe or synthetic agent campaign is a validation step. Old-reader forward
adoption remains explicitly deferred to a separately authorized release objective.
