# Execution breakdown: installed launcher, Graphify operation deadline, local rc4

**Status:** verified executable decomposition for Objective Contract
`oc_ff82ba151cdf3861@v2`. This is the Supervisor-owned execution breakdown; it does
not widen the contract, redefine material design, or record acceptance. Card and
board identities stay on the execution board.

**Derived by:** Supervisor (root task `t_cb240071`, flow
`aether.flow.v1:5f609ce87028bb2c6cd299c383ee1e919dd30d00255ebf27cc1c002cb444407c`).

**Source contract:** `.aether/objective-contracts/oc_ff82ba151cdf3861/v2.md`
(SHA-256 `e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`) on
base `00715d237d795e365c5e462b6b80d5a1bd8d8188`.

**Owning issues:** [#480](https://github.com/DarkArty07/Aether-Agents/issues/480),
[#481](https://github.com/DarkArty07/Aether-Agents/issues/481),
[#482](https://github.com/DarkArty07/Aether-Agents/issues/482).
[#261](https://github.com/DarkArty07/Aether-Agents/issues/261) stays open.

**Predecessor breakdowns** (`tasks.md`, `tasks-rc2.md`, `tasks-rc3.md`,
`specs/005-project-knowledge-graphify/tasks.md`) remain historical evidence and
are not reopened.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope; repository `DarkArty07/Aether-Agents` |
| Bound knowledge project | `project_knowledge` status returns the same project id and source revision `00715d237d795e365c5e462b6b80d5a1bd8d8188` (`INDEX_MISSING`; source inspection used) |
| Contract bytes | SHA-256 `e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`; `status: final`, `version: 2`, supersedes v1 |
| Base / branch | Board `worktree_base_ref` = HEAD = `00715d237d795e365c5e462b6b80d5a1bd8d8188`. Child worktrees on this board are created from that exact base |
| Maintained fork | `DarkArty07/aether-hermes` `aether-main` `aed6591a69f453a1867b73628603e7b53ba40ffc`, unchanged |
| Design sufficiency | Owner intent, objective, delegated decisions, in-scope 1–7, out-of-scope, authority, seven deliverables, AC-1…AC-11, testing standard and stop conditions settle outcome, interfaces, oracles and authority. No missing material product decision found |
| Policy debt | Tracked contract paths `.aether/objective-contracts/oc_ff82ba151cdf3861/{v1,v2}.md` are absent from `.github/workflows/policy.yml` (422 expected vs 424 non-`specs/` files). LG-DOCS registers both plus any new non-`specs/` paths. Do not waive the gate |
| Primary-checkout residue | Owner primary tree is dirty only in `tests/test_aether_tui_launcher.py` (wrap-only, 5 insertions / 1 deletion). Isolated unit worktrees start clean at the base. Do not edit the primary checkout |
| Profiles | `implementer`, `supervisor`, `morfeo` exist; no extra role or limit is introduced |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Two workstreams | Launcher/TUI/lifecycle and Graphify deadline share no writable files and no runtime interface beyond preservation | LG-CLI, LG-LIFE and LG-KNOW are root-gated and independent |
| Packaged launcher vs checkout script | Manager package owns validation and `exec` of managed Hermes; it must not import Hermes; `scripts/aether_tui.py` is not an installed dependency | LG-CLI authors `src/aether_agents/launcher.py` and CLI dispatch; the checkout script may remain only as a shim |
| `lifecycle.py` hotspot | Projections, TUI asset staging, doctor drift, update/rollback/service env live in one 6646-line module | LG-LIFE is concentrated on that file; do not parallelize Desktop vs TUI asset |
| `snapshots.py` + `semantic.py` hotspot | v2 requires one monotonic budget from `KnowledgeStore.update()` entry through pointer publication, consumed by every Graphify call including prepare/validate/compose | LG-KNOW owns both modules plus `graphify.py` fences; splitting them would leave an incomplete budget |
| `policy.yml` hotspot | New tracked non-`specs/` files must appear in the heredoc; base already omits this contract | Only LG-DOCS among implementation units edits it |
| Identity oracles | `VERSION`, README status, `AGENTS.md`, changelog and `tests/test_public_artifacts.py` are one atomic rc4 identity move | LG-DOCS owns them after the three behavior units are independently reviewed |
| Publication | Implementers never push, PR, merge, tag, activate or mutate issues | LG-INT / LG-CLOSE own remote and live effects |
| Activation interruption | `aether update --local --yes` rewrites Aether-owned projections and restarts the Aether-owned gateway | Durable evidence precedes activation; only LG-CLOSE may interrupt |
| TUI immutability | Prebuilt `ui-tui/dist` is built once from the exact fork commit in a disposable workspace and stored outside locked `hermes-source` | LG-LIFE owns preparation/binding; runtime launch never runs npm/build |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| In-scope 1; AC-1, AC-2; #480 launcher half | **LG-CLI** (Implementer, root-gated) | Packaged Hermes-free launcher module and CLI dispatch: exact project resolution, `--json` plan, reserved-argument policy, launch-env scrub including release-owned `HERMES_TUI_DIR`, installed-wheel path with no checkout `scripts/` dependency |
| In-scope 2, 3; AC-3, AC-4, AC-5; #480 projections, #481 | **LG-LIFE** (Implementer, root-gated) | Release-owned prebuilt TUI asset, hash-binding, service/launcher `HERMES_TUI_DIR`, branded `Aether` / `Continue Aether` Desktop and WSL Windows-Terminal actions, doctor drift, disposable update/rollback coherence |
| In-scope 4; AC-6, AC-7; #482 / #418 | **LG-KNOW** (Implementer, root-gated) | One monotonic `KnowledgeStore.update()` budget through pointer publication; remaining-time and shared-cancel on every budget-consuming Graphify call including semantic prepare/validate/compose; post-call fences; timeout/cancel/apply classification |
| In-scope 5; AC-9 docs/identity half; AC-10 identity | **LG-DOCS** (Implementer; after independently reviewed LG-CLI, LG-LIFE, LG-KNOW) | `1.0.0rc4` / `1.0.0-rc.4` identity, AGENTS/changelog/README/capabilities/CLI/knowledge docs, `policy.yml` manifest including this contract, coupled public-artifact oracles |
| In-scope 6; AC-9 gates; AC-10 tag/preview | **LG-INT** (Supervisor, same flow, non-terminal) | Integrate reviewed units, one PR, seven protected checks, green merge, local annotated `v1.0.0-rc.4`, non-mutating `aether update --local` preview |
| In-scope 7; AC-8, AC-10 activation, AC-11 | **LG-CLOSE** (Supervisor, same flow, `terminal=true`) | Pre-state witness, local rc4 activation, doctor/service/launcher/TUI integrity, fresh/continue canaries, bounded live semantic receipt, #480/#481/#482 close, residue cleanup, three release conclusions |

## Execution graph

```text
t_cb240071 (Supervisor decomposition root)
    ├── LG-CLI   (Implementer; base 00715d23)
    ├── LG-LIFE  (Implementer; base 00715d23)
    └── LG-KNOW  (Implementer; base 00715d23)

LG-CLI, LG-LIFE, LG-KNOW
    → same-card Supervisor review on each unit
    → LG-DOCS  (Implementer; after those three are independently reviewed)

LG-DOCS → same-card Supervisor review
    → LG-INT   (Supervisor, same flow, terminal=false)
        → LG-CLOSE (Supervisor, same flow, terminal=true)
```

LG-CLI, LG-LIFE and LG-KNOW are disjoint in writable surface and share only the
stamped interfaces below, so they can run together. LG-DOCS is serialized because
identity/docs/capability/policy must describe implemented behavior and register
new tracked files. LG-LIFE is concentrated because `lifecycle.py` is the single
projection/TUI-asset hotspot. LG-KNOW is concentrated because the operation
budget cannot be split across `snapshots.py` and `semantic.py`.

Same-card Supervisor review is the unit review lane. LG-INT/LG-CLOSE consume
independently reviewed units and do not replace unit review.

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_ff82ba151cdf3861@v2` (SHA-256
   `e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`) on base
   `00715d237d795e365c5e462b6b80d5a1bd8d8188`, plus this breakdown. Skills are
   reusable procedure only. Never create, edit, stage or exact-copy the canonical
   contract.
2. Release identity (source lands in LG-DOCS; tag/activation are Supervisor):
   package `1.0.0rc4`, display `1.0.0-rc.4`, local annotated tag `v1.0.0-rc.4`;
   conclusions `release_impact=patch`, `release_action=prepare`,
   `release_channel=prerelease`. No public tag, GitHub Release, PyPI or stable
   claim. Rc1/rc2/rc3 tags/releases/evidence remain immutable.
3. Maintained fork: `DarkArty07/aether-hermes` `aether-main`
   `aed6591a69f453a1867b73628603e7b53ba40ffc`, unchanged. `.patch` files are
   never replayed. A fork change requires a canonical design revision; stop.
4. Preservation: never edit the owner's primary checkout (including its
   uncommitted wrap-only `tests/test_aether_tui_launcher.py`), live
   `$XDG_DATA_HOME/aether/runtime`, mutable `$XDG_STATE_HOME/aether`, `home/`,
   credentials/provider/model/router settings, the unrelated
   `hermes-gateway-hestia` service, unrelated worktrees/branches/stashes/boards,
   or prior release evidence. Implementer units make no remote or live effect.
5. Packaged launcher (LG-CLI implements; LG-LIFE consumes): new module
   `src/aether_agents/launcher.py`, Hermes-import-free. Public API:
   `inspect_activation(extra_args=()) -> dict` and `main(argv=None) -> int`.
   JSON plan keys (stable, sorted when printed): `result`, `project_id`,
   `repo_root`, `hermes_home`, `cwd`, `hermes_executable`, `required_toolsets`,
   `command`, `tui_dir`. `cli.py` bare `aether [--project PATH] [--json]`
   dispatches here; it must not `exec` checkout `scripts/aether_tui.py`.
   `scripts/aether_tui.py` may remain a thin shim that calls the packaged
   module. Installed wheels must succeed without a checkout `scripts/` tree.
6. Project resolution (exact, never display name or recency): (1) explicit
   `--project PATH`; (2) explicit verified `AETHER_PROJECT_ID` when registry and
   portable marker agree; (3) current repository marker or the sole registered
   project only when registry and marker agree; otherwise fail nonzero and
   visibly. One-click entries carry an explicit local project binding.
7. Launch environment: remove conflicting `PYTHON*` / `HERMES_PROFILE` /
   ambient `HERMES_TUI*` / inherited top-level session, task, cron and Kanban
   launch residue (`HERMES_SESSION_ID`, `HERMES_KANBAN_*`, `HERMES_TASK*`);
   preserve ordinary credentials and config; then set exact `HERMES_HOME`,
   `AETHER_PROJECT_ID`, cwd and `HERMES_TUI_DIR` to the active release-owned TUI
   directory. Reserved binding flags remain the current
   `scripts/aether_tui.py` `_RESERVED_ARGS` set (`--in`, `--profile`, `--tui`,
   `--cli`, `--toolsets`, `-t`, `-p`, `--safe-mode`, `--ignore-user-config`,
   `--ignore-rules`). `--resume` is permitted passthrough.
8. TUI asset (LG-LIFE implements; LG-CLI/service consume): build
   `ui-tui/dist/entry.js` once from the exact fork commit in a disposable
   workspace; install under `<release>/tui/` **outside** locked `hermes-source`;
   record digest/provenance in the release record; expose the active path as
   `runtime/current/tui` (or equivalent selector-relative path).
   `HERMES_TUI_DIR` is that directory. Runtime launch never runs npm/build,
   never trusts an ambient TUI path, and never weakens `_tree_sha256`. Node/npm
   versions and output digest are evidence, not product identity.
9. Projections (LG-LIFE): branded `Aether` (fresh) and `Continue Aether`
   (`--resume latest` with launcher-owned exact `--in`). `Exec` targets the
   stable selector `runtime/current/venv/bin/aether` with explicit `--project
   <exact Aether Agents root>`, never a version-specific Hermes path. Linux
   desktop entries are terminal-based. This host's WSL adapters invoke existing
   Windows Terminal into the existing WSL distribution. Update/rollback/uninstall
   remain reversible. No operator home, Windows username or machine identity
   enters versioned/public artifacts.
10. Knowledge budget (LG-KNOW): `KnowledgeStore.update()` starts one monotonic
    deadline at native entry (`time.monotonic()` + `min(300, configured lower)`).
    That deadline remains authoritative through terminal operation record and
    pointer publication. One helper wraps every Graphify invocation that consumes
    the budget (`probe`, structural `update`, `semantic_prepare`,
    `semantic_validate`, `semantic_compose`, and any equivalent). Each call
    receives the same shared `cancel_event` and a positive timeout no greater
    than remaining time less the existing `FINALIZATION_RESERVE_SECONDS` (5.0).
    `run_semantic_extraction` consumes the operation deadline; it must not start
    a second 300s clock. Post-call fences reject results returned after
    cancel/deadline. Host cancel re-raises `OPERATION_CANCELLED` and kills the
    process group. Natural exhaustion or Graphify `TIMEOUT` caused by this budget
    returns the established pending/partial receipt with deadline attribution,
    retains validated cache, releases the lock and does not publish. Independent
    compose defects remain bounded `apply` failures. No model/provider/router
    change.
11. `policy.yml`: only LG-DOCS among implementation units edits it. LG-CLI /
    LG-LIFE / LG-KNOW record every new tracked non-`specs/` path in the handoff.
    LG-DOCS adds those paths and
    `.aether/objective-contracts/oc_ff82ba151cdf3861/v1.md` plus `v2.md`.
12. Test standard (`CONTRIBUTING.md`, not weakened): fail-first focused nodes,
    then `uv run --frozen ruff check/format --check src/aether_agents tests scripts`,
    `uv run --frozen mypy src/aether_agents`, `uv run --frozen pytest -q
    --cov=aether_agents --cov-report=term-missing` (78% branch floor), `uv build`,
    `uv run --frozen python scripts/check_documentation.py`, and
    `uv run --frozen python scripts/run_tests.py` before handoff for surfaces the
    unit touches. No new skip. No live auxiliary/model calls in Implementer units.
    Distinguish deterministic, live, skipped and reused evidence.
13. Evidence: each unit writes exactly one record at
    `specs/001-aether-v1-productization/evidence/<unit-id>.md`. Larger logs travel
    as native task attachments. No secrets, credentials, provider/model/router
    bindings, operator homes, live-state values, board/card identities or
    machine-specific paths in portable artifacts.
14. Unit compatibility evidence is `patch` unless the unit proves otherwise.
    Aggregate `release_impact` / `release_action` / `release_channel` belongs
    only to LG-CLOSE.
15. Completion: local commit; same-card review (`kanban_request_review`,
    reviewer `supervisor`); no push/PR/merge/tag/issue mutation. If inspection
    shows a unit is oversized, colliding, or unsupported by the contract, stop
    and return a source-backed question rather than widening scope.

## LG-CLI — Packaged launcher and exact project binding

- Source: in-scope 1; AC-1, AC-2; #480 launcher/CLI half; this unit.
- Outcome: installed `aether [--project PATH] [--json]` validates and launches
  project-bound Morfeo from packaged manager code. `--json` is a non-mutating
  plan with the stamped keys. Missing/conflicting/ambiguous identity fails
  visibly. Launch cwd/`HERMES_HOME`/`AETHER_PROJECT_ID`/`HERMES_TUI_DIR` are
  exact; reserved overrides are rejected; `--resume latest` is preserved.
  Excludes lifecycle projections, TUI *build*, VERSION/docs/`policy.yml`,
  Graphify, live activation.
- Inputs: base `00715d23`. Shared decisions 5–7. TUI directory convention from
  decision 8 (`<active-runtime>/tui`); fixture it in tests when no asset exists.
- Boundaries: writable `src/aether_agents/launcher.py` (new),
  `src/aether_agents/cli.py`, `scripts/aether_tui.py` (shim only),
  `tests/test_aether_tui_launcher.py`, `tests/test_project_marker_validation.py`
  only as required to follow the packaged module. Preserve `lifecycle.py`,
  `knowledge/*`, VERSION, docs, `policy.yml`, the Objective Contract.
- Judgement: helper names, plan-error strings, how the shim locates the module.
  Escalate if packaged launch requires importing Hermes or a fork API change.
- Verification: RED then GREEN. Cover path/UUID/registry/marker agreement and
  conflict; `--json` non-mutation; reserved-arg refusal; env scrub including
  Kanban/session/TUI residue; `--resume latest`; clean installed-wheel launch
  path that does not read checkout `scripts/`. Do not treat the primary
  checkout's wrap-only dirty test as a source. Then the canonical commands in
  decision 12 for touched Python.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch`; record
  new non-`specs/` paths for LG-DOCS.

## LG-LIFE — Release-owned TUI and branded projections

- Source: in-scope 2, 3; AC-3, AC-4, AC-5; #480 projections; #481; this unit.
- Outcome: candidate preparation builds the prebuilt TUI from the exact fork
  commit in a disposable workspace, hash-binds it outside `hermes-source`, and
  makes launcher, service, doctor, update and rollback agree on that asset.
  Branded `Aether` and `Continue Aether` actions target the stable `aether`
  selector with explicit project binding. Doctor reports missing/altered
  launcher/TUI bytes. Projection failure restores prior opaque state. Live rc3
  is never edited. Excludes packaged CLI module, Graphify, VERSION/docs identity,
  live host activation.
- Inputs: base `00715d23`. Shared decisions 8–9. Packaged launcher CLI surface
  from decision 5 (projections exec `aether`, not `scripts/aether_tui.py`).
- Boundaries: writable `src/aether_agents/lifecycle.py`,
  `scripts/release_bundle.py`, `tests/test_lifecycle_projections.py`,
  `tests/test_release_bundle.py` (TUI/projection qualification only), and a new
  focused test module under `tests/` if that avoids colliding with LG-CLI's
  launcher tests. Do not edit `scripts/aether_tui.py` or `cli.py`. Preserve
  knowledge modules, VERSION, docs, `policy.yml`.
- Judgement: exact TUI dist file layout under `<release>/tui/`, Windows Terminal
  shortcut file format, Desktop `Name`/`Exec` strings. Escalate if the inspected
  prebuilt interface cannot bind without a maintained-fork change.
- Verification: RED then GREEN. Disposable prepare records digest/provenance;
  activation/rollback/forward in disposable roots agree on selector, launcher,
  Desktop/host entries, service env and TUI digest; doctor fail-closed on
  altered/missing TUI; locked-source inventory/hash identical before/after a
  real PTY launch that must not invoke npm/build or write `node_modules` into
  hermes-source. Maintained-fork Node/TUI build runs only in a clean disposable
  exact-commit workspace. Then decision-12 commands for touched surfaces.
- Dependencies: decomposition root only. Do not wait for LG-CLI source; consume
  the stamped `aether --project` / `--resume latest` interface.
- Completion: local commit; same-card review; unit compatibility `patch`; record
  new non-`specs/` paths for LG-DOCS.

## LG-KNOW — Operation-wide Graphify deadline

- Source: in-scope 4; AC-6, AC-7; #482; historical #418; this unit.
- Outcome: deterministic tests prove one monotonic deadline begins at
  `KnowledgeStore.update()` entry and remains authoritative through terminal
  operation record and pointer publication. Prepare, validate and compose are
  explicit oracles for remaining-time and shared-cancel propagation. Late
  backend results are not accepted or persisted. Slow prepare/validate/compose
  cannot cross the operation budget. Host cancel terminates the Graphify
  process group and returns `OPERATION_CANCELLED`. Excludes launcher/TUI,
  VERSION/docs, live auxiliary canary, Graphify feature redesign.
- Inputs: base `00715d23`. Shared decision 10. Existing
  `FINALIZATION_RESERVE_SECONDS = 5.0`, `MAX_TOTAL_BUDGET_SECONDS = 300.0`.
- Boundaries: writable `src/aether_agents/knowledge/snapshots.py`,
  `semantic.py`, `graphify.py`, and only if required `hermes_plugin.py`;
  `tests/test_knowledge_semantic_manager.py`, `tests/test_knowledge_regressions.py`,
  plus Graphify backend process tests already in those modules. Preserve
  `graph_worker.py` overlay compositor unless a fence cannot be implemented in
  the adapter. Preserve launcher/lifecycle/docs/`policy.yml`.
- Judgement: helper placement (store-owned wrapper vs backend kwargs), fake-clock
  style. Escalate if deadline ownership would require a Graphify upgrade,
  semantic fallback, or a second public tool.
- Verification: fail-first fake-clock / slow-backend / host-cancel cases with no
  live model. Prove: deadline start at native update entry; remaining-time and
  shared event on prepare, validate and compose; pre/post-call fences; elapsed
  bound; process-group cleanup; terminal attribution; cache retention; lock
  release; no late pointer mutation; compose defects still `apply`. Keep existing
  GX-06 / D37 cancel oracles green. Native Graphify process tests use a
  disposable pinned 0.9.54 interpreter (`AETHER_GRAPHIFY_PYTHON`), never pytest
  installed into the live component. Then decision-12 commands for knowledge
  surfaces.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch`; record
  new non-`specs/` paths for LG-DOCS.

## LG-DOCS — rc4 identity, docs, capabilities, policy

- Source: in-scope 5; AC-9 documentation/public-artifact half; AC-10 identity
  half; this unit.
- Outcome: `VERSION` `1.0.0rc4`; truthful local-only README/AGENTS/changelog
  status; capability/CLI/getting-started/lifecycle/project-knowledge docs match
  the packaged launcher, branded projections, release-owned TUI and
  operation-wide 300s budget; `docs/capabilities.toml` launch status is honest;
  `policy.yml` lists this contract's v1 and v2 plus new non-`specs/` paths from
  reviewed siblings; coupled oracles in `tests/test_public_artifacts.py` (and
  observation golden only if the digest relation flips) are GREEN. Excludes
  `website/**` behavior changes beyond what public-artifact oracles already
  require, live activation, Graphify code.
- Inputs: independently reviewed LG-CLI, LG-LIFE and LG-KNOW commits/handoffs
  (new tracked paths and implemented surfaces). Do not invent surfaces the
  siblings did not deliver.
- Boundaries: writable `VERSION`, `CHANGELOG.md`, `README.md`, `AGENTS.md`,
  `docs/**` (not a website redesign), `docs/capabilities.toml` and generated
  `docs/reference/capabilities.md` via the existing checker, `.github/workflows/policy.yml`,
  `tests/test_public_artifacts.py`, and other coupled identity oracles only if
  they fail because of the identity move. Preserve implementation modules
  unless a one-line capability path/import reference is required.
- Judgement: changelog wording. Escalate if identity oracles demand a public
  rc4 link or a Pages-only rewrite.
- Verification: RED identity oracles, then GREEN. `scripts/check_documentation.py`.
  Policy expected list equals `git ls-files | grep -v '^specs/'`. Decision-12
  commands for touched surfaces. No live launch/semantic canary.
- Dependencies: independently reviewed LG-CLI, LG-LIFE, LG-KNOW.
- Completion: local commit; same-card review; unit compatibility `patch`.

## LG-INT / LG-CLOSE (Supervisor; not Implementer work)

LG-INT merges the four reviewed units without history rewrite, opens one PR,
waits for the seven protected checks, merges green without bypass, records the
merge SHA, creates exactly one local annotated `v1.0.0-rc.4` on that commit,
and records a non-mutating `aether update --local` preview. No remote tag.

LG-CLOSE records pre-state witnesses; activates rc4 explicitly; verifies
doctor/service/selector/TUI integrity and source inventory before/after real
fresh and continue launches; runs one configured semantic update (plus at most
one resume if pending with progress) with monotonic elapsed time before the
420s host boundary; closes #480/#481/#482 only with criterion-linked evidence;
leaves #261 open; cleans objective-owned residue; states
`release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`
separately from evidence.

## Verification of this decomposition

Traceability: AC-1/AC-2 → LG-CLI; AC-3/AC-4/AC-5 → LG-LIFE; AC-6/AC-7 → LG-KNOW;
AC-9 docs/identity and AC-10 identity → LG-DOCS; AC-9 gates and AC-10
tag/preview → LG-INT; AC-8/AC-10 activation/AC-11 → LG-CLOSE. Every in-scope
item maps to exactly one unit; out-of-scope items appear only as preserved
boundaries.

Independence: the three root-gated implementation units own disjoint files.
Necessary serialization is docs-after-behavior, then publication, then
activation. Same-file collisions (`lifecycle.py`, `snapshots.py`+`semantic.py`,
`policy.yml`, VERSION/README oracles) are not split.
