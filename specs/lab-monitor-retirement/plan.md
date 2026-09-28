# Technical plan: subtract Lab and Telegram Monitor

**Owning intent:** [spec.md](spec.md), RET-01–RET-07

**Inspected source:** `21fa590e850dd29f5672a63fb521766431745628`

**Disposition:** material design resolved; implementation delegated after finalized contract

## 1. Route and boundaries

Use one source-retirement Objective Contract for both removals. Their implementation
work can be reviewed independently, but package metadata, lifecycle plugin validation,
current documentation and the repository manifest must converge into one coherent
source outcome. Independent review has concrete value: catching residual imports,
accidental removal of unrelated tests/notifications and legacy-plugin verification
regressions. Supervisor decides the unit breakdown and authors `tasks.md`; this plan
neither creates cards nor prescribes a worker count.

The final artifact is reviewed, verified source merged by the normal GitHub path. This
is not a release candidate, live cutover or qualification of agents. The current product
version and immutable release/tag records are unchanged. Compatibility conclusions are
`release_impact=major`, `release_action=defer`, `release_channel=none`: the Lab Python API
and Monitor CLI/tools are deliberately removed public surfaces; prerelease status does
not make their removal backward-compatible.

## 2. Removal map and retained boundaries

| Area | Required change | Preservation oracle |
| --- | --- | --- |
| Formal Lab | Remove `src/aether_agents/lab/`, `lab/`, `scripts/e2e/`, and `src/aether_agents/resources/lab` mapping/symlink. Remove Lab-only scenario/runner/matrix/persistent/affinity/formalization tests. | No executable/package import or build input depends on the Lab; non-Lab tests still execute. |
| Shared test isolation | Move only the environment-builder closure consumed by the surviving knowledge binding test to `tests/runtime_isolation.py`; import it using the existing sibling test-helper convention. | Existing scoped environment scrubbing and disposable destination containment remain checked; no production export or runner moves with it. |
| Monitor | Remove `src/aether_agents/monitor/`, `src/aether_agents/resources/monitor/`, `scripts/qualify_telegram_monitor.py`, `scripts/telegram_monitor_lab.py`, and dedicated Monitor tests. | No Monitor entry point/tool/command/report resources in a freshly built/installed artifact. |
| Shared code | Remove only Monitor parser/dispatch in `src/aether_agents/cli.py`, entry-point/expectation coupling in `lifecycle.py`, `scripts/release_bundle.py`, `pyproject.toml`, and default Morfeo profile config. | Observation, contracts and knowledge remain the three current official plugins; other commands/profiles remain unchanged. |
| Mixed tests | Reconcile `tests/test_authorized_cleanup.py`, `test_documentation.py`, `test_observation_packaging.py`, `test_public_artifacts.py`, `test_knowledge_session_binding.py` and affected lifecycle tests. | Remove retired assertions, not unrelated cases. New negative checks live in the existing test owners; only a small isolation-helper test module is needed if no existing owner fits. |
| Current guidance/build policy | Reconcile root portals, `docs/`, registry/generated capabilities, applicable guides and `.github/workflows/policy.yml` literal file inventory; remove obsolete build/type-check exceptions for deleted Lab paths. | Documentation derives from actual remaining surfaces; no CI job/threshold/branch protection is disabled or weakened. |

The map is an inspected starting point, not permission to delete everything containing
`lab`, `monitor` or `telegram`. Unrelated names, native cron features, lifecycle monitors,
web components, gateway code and historical evidence are not deletion candidates.

### 2.1 Minimal isolation support

At the inspected revision the retained production-feature consumer is
`tests/test_knowledge_session_binding.py:300-345`. Its dependency is
`isolated_hermes_env(run_root, hermes_root, hermes) -> dict[str, str]`. Preserve that
signature in the test helper so this migration does not redesign the test. Its minimal
closure is the scrub-name/prefix constants, environment scrub, disposable destination
preflight and local error type in `lab/isolation.py:1-150`. Preserve the relevant existing
boundary tests for inherited identity and symlink/escaped destinations. The discarded
native writer probes, subprocess runner, PTY qualification and evidence protocol are
not prerequisites of this consumer and must not be copied wholesale.

Assumption: the tracked dependency inventory is complete at the handoff base. If a
further retained consumer is found, preserve its actual guarantee with the smallest
shared test support; consult Morfeo if that would require another product-level API or
retaining a substantial Lab lane. Do not silently skip the consumer.

### 2.2 Exact plugin verification without breaking retained releases

Simply changing the current entry-point dictionary from four plugins to three is not
sufficient. `RuntimeInstaller._inspect_wheel` (around line 6727),
`_installed_aether_identity` (around 7031), `validate_release` (around 6351/6387), and
`_verify_installed_environment` bind plugin sets and fingerprints. The installed release
may still carry the historical Monitor plugin.

Decision: current artifacts emit exactly the three retained official plugins. Read and
integrity-validation paths may recognize **only two closed, exact maps**: that current
map and the already-known historical map consisting of the same three plus the exact
`aether-telegram-monitor = aether_agents.monitor.hermes_plugin` entry. This is minimal
read compatibility, not a new plugin negotiation framework or an active Monitor export.

- Retain artifact digest, provenance, observer/schema, profile-bundle and manager/runtime
  equality checks. No prefix/subset match, arbitrary extra plugin or permissive fallback.
- Fingerprints must use the actually authenticated entry-point map, not substitute the
  executing manager's current map into a historical artifact's identity.
- Candidate installation probes compare with the inspected artifact's exact expected
  map. Fresh artifact tests require the current three-plugin set, with no Monitor code.
- Preserve deterministic rejection of unknown names/targets, missing retained plugins,
  mismatched manager/runtime sets and changed artifact fingerprints.
- Reuse existing release/lifecycle fixture infrastructure for these cases. Do not build
  a general old-version oracle, live transition matrix or bridge release here.

The old installed manager itself may reject a new three-plugin artifact because its
code is immutable. That **forward-adoption limit** must be recorded, not solved by
rewriting an installed release or preparing a new RC. A future authorized release must
choose its managed adoption path. Preserving the new reader's validation of known old
artifacts is in scope; claiming that the frozen old reader learned new semantics is not.

### 2.3 Profiles, cron and state

Remove Monitor from shipped defaults and plugin discovery. Preserve the lifecycle rule
that operator-provisioned `config.yaml` is not overwritten (currently around
`lifecycle.py:4884-4901`). Do not add hidden config migration, cron cleanup or token work.
Private legacy Monitor configuration/job/history can remain inert on the currently
installed old runtime; they are not shipped source and are not purged by this contract.
No existing job is created, resumed, executed or removed for qualification. No Telegram
message is sent. Hermes native cron implementation, ordinary scheduling semantics and
user-created jobs are untouched.

## 3. Canonical/documentary reconciliation

The authoring changes capture the owner decision in PD-75, A1-FR-092, R11 and historical
Monitor/004 notices. Implementation reconciles any remaining active Lab/Monitor promise
in the current documentation and capability registry. Remove the two active capability
records and regenerate `docs/reference/capabilities.md` through
`scripts/check_documentation.py --write`; do not pretend that removed callable surfaces
still exist as `deprecated`. Keep one concise retirement/migration note in existing
current guidance and an unreleased changelog entry, not a replacement manual.

Historical `specs/telegram-monitor/`, 004 evidence, finalized Lab/Monitor contracts,
postmortem #407 and previous release history remain attributable history. Mutable
historical specification/plan entry points may carry a supersession banner; do not
rewrite prior acceptance/rejection evidence. For current links to removed tools, explain
retirement or link to the inspected historical Git revision rather than recreate a stub.

## 4. Testing standard and acceptance mapping

The owner supplied no different testing policy for this objective. Resolve it to the
existing `CONTRIBUTING.md:48-77,90-150,167-217` standard: focused tests during work; one
integrated full exact-Hermes bootstrap with unchanged coverage and static checks before
handoff because lifecycle/packaging/CI boundaries are touched; normal required PR checks.
Combine full tests and coverage in one run where applicable. Reuse exact-revision,
applicable unit evidence rather than make every worker repeat the full suite.

| Criterion | Decisive scenario/result | Evidence |
| --- | --- | --- |
| RET-01 | Fresh checkout/build has no Lab modules, resources, wrappers or executable consumers. Remaining test suite collects/runs without Lab. | Tracked diff/reference classification; package member checks; tests. |
| RET-02 | Installed CLI rejects `monitor` through the ordinary unknown-command path; plugin discovery has no Monitor/tools; no dedicated reporting resources/scripts/default opt-in ship. | Existing packaging/CLI/plugin tests updated with absence assertions. |
| RET-03/04 | Knowledge's isolated native-boundary test keeps its semantics; minimal helper tests reject unsafe destinations and scrub outer identity; retained CLI/plugins and other tests pass. | Focused tests plus integrated repository checks; diff confirms Hermes/gateway/cron/pin are untouched. |
| RET-05 | New three-plugin artifact works; known historical four-plugin identity validates without losing digest/equality checks; malformed/mismatched identities refuse. | Focused existing lifecycle/release/packaging fixtures, not live old-release mutation. |
| RET-06 | Registry, generated reference, current docs, policy manifest and canonical owners agree; residual references are historical or unrelated and attributed. | Documentation/public-artifact/manifest checks and reviewed residual inventory. |
| RET-07 | Independently reviewed units, required checks green, normal merge/issue closure and scoped cleanup proven. | Supervisor final receipt; Morfeo criterion-by-criterion reception at final revision. |

[quickstart.md](quickstart.md) carries runnable commands and prerequisites. Added checks
are limited to uncovered subtraction risks: removed surfaces must actually be absent,
remaining isolation must not weaken, and legacy plugin identity must stay exact. No
provider-backed synthetic owner, last Lab run, Telegram canary, load test or behavioral
qualification is required or authorized.

## 5. Authority, convergence and stop

Supervisor uses the real provisioned profiles and native Project/board/worktrees. It
owns receipt review, decomposition, implementation review and routine GitHub closeout
under R8 FR-824: ordinary branch push, PR, required checks, non-bypass green merge, issue
reconciliation and objective-owned merged-branch/worktree cleanup. Implementer owns
local implementation and commits, never publication. Preserve per-unit reversible
history; no squash/rebase/amend/force of integrated work.

Source changes and deterministic disposable checks are authorized. No new package or
provider, Hermes fork change, profile/service activation, external report, runtime-state
purge, release/tag/package publication, manual deployment or credential acquisition is
authorized. Existing CI behavior is not redesigned by this contract.

Use the canonical Supervisor convergence procedure: at most two ordinary returns per
logical unit, preserving history across replacement cards. A recurring same-cause issue
or material design gap returns to Morfeo with the candidate and concrete evidence;
neither another arbitrary repair campaign nor automatic acceptance follows. Stop the
dependent work for an unavoidable change to retained functionality, missing effect
permission, ambiguous identity or a genuine protected-edge denial. Morfeo resolves
in-scope design details; only missing material owner intent returns to the owner.

Before the implementation PR merges, commit reviewed per-unit evidence and a pre-merge
acceptance mapping under this objective's `evidence/`; neither may predict CI, merge,
issue closure or cleanup. After the actual green merge and applicable reconciliation,
Supervisor writes the `evidence/final.md` receipt in its owned project worktree, attaches
those exact bytes to its own native terminal closeout task **before** retiring that
worktree, reads back the attachment identity and content/digest, and records the
attachment locator and exact merged revision in its terminal handoff. The post-merge
receipt persists as a native task attachment, not as a file already tracked on `main`;
no second evidence-only PR is required. Morfeo records its subsequent acceptance
in `evidence/reception.md` locally and references that result in the existing Objective
Plan and root task comment; it must not claim the post-merge reception was in the merged
PR. Raw logs and disposable builds stay in owned local scratch and are retired after
preserving necessary evidence. No bulk cleanup of pre-existing worktrees or private state.
