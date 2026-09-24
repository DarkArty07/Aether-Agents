# Execution breakdown: conversational greenfield intake and MCP-enabled TUI startup (#492)

**Status:** verified executable decomposition for Objective Contract
`oc_79b55027e7c3688d@v1`. This is the Supervisor-owned execution breakdown; it does not
widen the contract, redefine the material design in
`specs/001-aether-v1-productization/plan.md` §4.6/§10.1–10.3 or
`specs/002-aether-contract-observation/research.md`, or record acceptance. Card, flow and
board identities stay on the execution board.

**Derived by:** Supervisor (root card of this objective; the opaque flow, task and board
correlation identifiers remain native routing side data and are deliberately not
republished in this public artifact).

**Source contract:** `.aether/objective-contracts/oc_79b55027e7c3688d/v1.md`
(SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), `status:
final`, `version: 1`, `change_reason: null`, on base
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`.

**Owning issue:** [#492](https://github.com/DarkArty07/Aether-Agents/issues/492)
reconciled at intake; it is not contract authority and is dispositioned at closeout.

**Predecessor breakdowns** (`tasks.md`, `tasks-rc2.md` … `tasks-rc6.md`,
`specs/005-project-knowledge-graphify/tasks.md`) remain historical evidence and are not
reopened. The failed rc5 objective and the published-but-rejected rc1 remain non-accepted
history. Frozen rc-era evidence, quarantines and receipts are preserved unchanged.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the contract header and the execution board; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`; tracked, unmodified at the base commit; `status: final`, `version: 1` |
| Base / branch | Board `worktree_base_ref` = HEAD = `004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6` ("docs: finalize project intake and TUI startup objective"). Child worktrees start from that exact base |
| Base vs remote | `origin/main` = `4c1af201c18ced73235d7b49f22a32123c46fb22`. The objective's three commits (`5b6ee19f`, `8da4acba`, `004c5f07`) are **local-only**, so this objective's PR must carry them together with this breakdown, the reviewed unit commits and the terminal evidence |
| Design sufficiency | PD-52 (owner amended 2026-09-23), A1-FR-043/043a/046–052/100, A1-SC-005/018/019, `plan.md` §4.6 and §10.1–10.3, `contracts/cli.md` init/launch, OBS-D-009/032 and OBS-FR-025–028/087 settle every material decision: who creates Git (the owner), what `init` may create (portable marker + one exact native Project + ignore policy only), what may open the TUI (a verified initialized project, `AGENTS.md` optional during intake), how the observer resolves tool categories (lightweight registry accessor + shared-metrics taxonomy, no discovery import), and the bounded onboarding refusal matrix. No missing material product decision was found |
| Stop-condition check: native create/lookup interface | The installed selected runtime exposes `hermes project create <NAME> --primary <PATH>` and honours the selected profile home. Verified read-only on a disposable throwaway home: the command created a Project row under that home's own `projects.db` and returned one id. The manager's existing read-only exact-path lookup then has the matching row to verify. The contract's "selected locked Hermes release lacks a supported native Project-create/registry lookup" stop condition does **not** fire |
| Stop-condition check: registry accessor import safety | The proposed accessor imports cleanly in an isolated subprocess of the selected runtime: `tools.registry.registry.get_toolset_for_tool` and `hermes_cli.observability.shared_metrics_contract.tool_category` import with no `model_tools` and no `hermes_cli.plugins` in `sys.modules`; sampled categories resolve (`kanban`→`planning`, a file tool→`other`, an `mcp…` toolset→`mcp`). The runtime half of the OBS-D-032 stop condition does not fire; the corrected adapter must still be proven by the controlled concurrency regression and the real MCP-enabled startup |
| Baseline focused lane (real run) | `uv run --frozen python scripts/run_tests.py -- tests/test_project_init.py tests/test_aether_tui_launcher.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_usage_guidance.py -q` → **161 passed, 13 subtests passed** (40.72 s) at the contract base |
| Pre-existing gate failure at base | `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` **FAILS** at the contract base: the contract file is tracked but absent from the `.github/workflows/policy.yml` canonical base manifest (446 expected vs 447 tracked non-`specs/` files; the single missing literal is `.aether/objective-contracts/oc_79b55027e7c3688d/v1.md`). Correcting it is objective-owned work, not a unit regression |
| Observation qualification lock | `scripts/qualify_observation.py` locks `EXPECTED_CORE_TESTS = 472`, node-manifest digest `c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a` over seven files, mirrored by literal in `tests/test_observation_qualification.py`; `tests/test_observation_cli_plugin.py` is one of the locked files |
| Installed runtime (read-only prestate) | The current runtime pointer resolves to the managed `1.0.0rc8` candidate; `morfeo`, `supervisor` and `implementer` profiles exist. The Aether project registry entry for this portable project currently carries no `hermes_project_id`. This is preserved state with limits, not an obligation of this objective |
| Interfaces to consume | `src/aether_agents/commands/init.py` (`run_init`, `_plan`, `_native_projects_for`, `_resolve_hermes_project`, `_apply_ignore_policy`); `src/aether_agents/observation/context.py` (`ProjectRegistry`, `read_project_marker`); `src/aether_agents/project_marker.py`; `src/aether_agents/launcher.py` (`_resolve_project`, `_resolve_component_paths`, `inspect_activation`, `main`); `src/aether_agents/observation/capture/hermes_plugin.py` (`_resolve_category_normalizer`, `_Observer`, `register`); `scripts/aether_tui.py`; `docs/capabilities.toml` + `scripts/check_documentation.py` |
| Established gates | `CONTRIBUTING.md:31-90` locked runner (`uv run --frozen python scripts/run_tests.py`), Ruff check/format-check, mypy, coverage floor (`fail_under = 78`, branch coverage), `uv build`, `scripts/check_documentation.py`, public-artifact/privacy scan, `git diff --check`, and the `.github/workflows/policy.yml` manifest oracle |
| Profiles / capacity | `implementer`, `supervisor` and `morfeo` exist; no new role, profile or limit. Board dispatch allows 4 in progress and `implementer` up to 3 concurrent. The three behavior units are genuinely independent in file ownership and exactly fill the `implementer` cap; the remaining edges are real serialization |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` (observation procedure, no authority) |
| Preserved residue | The owner's primary checkout and its uncommitted work, the live `1.0.0rc8` installation (release records, active pointer, projections, unit bytes, profiles, boards, sessions, memories, credentials/provider/model/router configuration), the running gateway and TUI processes, Context7's current mitigation, `home/`, unrelated services/worktrees/branches/tags, the frozen rc3/rc4/rc5 quarantine and recovery receipts, and every historical evidence file |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Who creates Git | The owner runs `git init`; `init` accepts an unborn exact root and creates nothing of its own | `OC79-INIT` removes the "an exact-path native Project must already exist" prerequisite and creates one only through the selected runtime's supported native CLI, never `git init`, remote, commit, constitution, `AGENTS.md`, board or worker |
| Who owns native Project state | The per-profile `$HERMES_HOME/projects.db` owned by the selected managed Morfeo profile; the manager stays Hermes-independent | `OC79-INIT` may invoke `hermes project create` and must verify the returned id and exact primary path by the existing read-only lookup before writing anything. Direct writes to `projects.db`, Hermes imports in manager code, and name/slug/approximate matching stay forbidden. A matching **archived** exact-path Project is a visible identity conflict, not a reason to create a replacement |
| Dry-run and retry semantics | `--dry-run` performs the whole preflight and reports prospective effects; a partial failure retains the verified native Project for idempotent reuse | `OC79-INIT` owns purity (no creation, no marker, no registry, no `.gitignore` change on preview) and the interruption/retry invariant without destructive cleanup |
| Who owns the intake exception | A1-FR-043a/100: a verified initialized project with no `AGENTS.md` and no commit may open the TUI for Morfeo's intake conversation; identity, source and runtime validation are never bypassed | `OC79-LAUNCH` makes missing root `AGENTS.md` an onboarding condition on the verified route only, and keeps every mismatch (marker, registry, profile, runtime, `terminal.cwd`) fail-closed |
| Project selection | Exact and never inferred. A1-FR-043 removes the sole-registered-project fallback | `OC79-LAUNCH` deletes route (5), emits actionable `git init`/`aether init` guidance instead, and updates the documented precedence everywhere it is asserted |
| Board boundary | A1-FR-052: only a finalized contract handoff provisions a board/workspace | No unit creates a board, worker or task outside the native handoff; the onboarding path stays free of execution state |
| Observer category resolution | OBS-D-009/032: reuse the runtime's lightweight registered-tool lookup plus the shared-metrics taxonomy; the discovery module stays unimported during registration | `OC79-OBS` replaces `model_tools.get_toolset_for_tool` with the registry-owned accessor inside the adapter, keeps `NATIVE_TOOL_CATEGORY_UNAVAILABLE` as the visible coverage gap, and proves registered **and** late-registered parity |
| Runtime identity | "Resolve the source actually imported and release-lock fork commit before claiming behavior" | Units that execute Hermes record the runtime actually loaded and its revision; no fork change, no new Hermes capability, no timeout increase |
| Where behaviour is frozen | Source behavior freezes when the three behavior units are reviewed; public guidance and the capability registry must then describe that frozen behaviour | `OC79-DOCS` runs strictly after the three behavior units; `OC79-QUAL` runs strictly after `OC79-DOCS` so the decisive receipt is produced once against the frozen revision (source + docs + manifest) instead of twice |
| Policy manifest | The manifest enumerates every tracked non-`specs/` file and is the CI oracle; it is already stale at base | `.github/workflows/policy.yml` is edited in sequence, never concurrently: `OC79-DOCS` applies the contract line plus any line recorded by the three behavior units; `OC79-QUAL`, which runs strictly after, applies the lines its own new tracked files require; `OC79-INT` re-runs the oracle and applies only residual lines as mechanical config glue |
| Observation qualification lock | The locked core manifest is a deliberate identity, not a formality | Only `OC79-OBS` may re-derive it, only as a consequence of nodes it adds to a locked file, and it records the old→new count and digest |
| Evidence ownership | One public evidence file per unit under `specs/001-aether-v1-productization/evidence/`; private installation witnesses stay private | `OC79-OBS.md`, `OC79-INIT.md`, `OC79-LAUNCH.md`, `OC79-DOCS.md`, `OC79-QUAL.md`; a unit never edits another unit's evidence file. No operator-local paths, secrets, session content or provider identifiers in tracked artifacts |

## Requirement coverage

Each contract obligation maps to the unit that must produce it. "All" means every unit
must respect it; it is a preservation boundary rather than a build deliverable.

| Obligation | Unit(s) |
| --- | --- |
| AC1 — plain directory refused with `git init` guidance and zero mutation; unborn exact root accepted; pure `--dry-run` preview; actual init yields one marker, exact same-profile native Project and registry binding, with no commit/remote/`AGENTS.md`/board/worker/invented principles; repeat init identity-preserving | `OC79-INIT`; installed end-to-end half in `OC79-QUAL` |
| AC2 — one exact Project reused; multiple matches, wrong explicit id, archived/copied marker, nested/non-Git path and cross-profile path refused visibly; interruption after native creation retries without duplicate or destructive cleanup; brownfield files/governance/Git status preserved | `OC79-INIT`; installed half in `OC79-QUAL` |
| AC3 — installed bare `aether` and `--check --json` bind the same portable/native project, Morfeo profile and exact Git-root cwd, open the TUI without `AGENTS.md`, allow the initial intake turn; no sole unrelated Project; mismatched/absent runtime and marker fail closed; readiness ≠ real model reply | `OC79-LAUNCH`; installed TUI cold start in `OC79-QUAL` |
| AC4 — two-thread pre-fix race reaches the import/plugin lock cycle and the candidate does not, within a bounded fixture and without extending the production timeout; registered and late-registered categories match the selected registry/taxonomy; missing native capability is a visible coverage gap; installed candidate emits readiness signals plus a single early turn without observer-induced hang or live-service mutation; MCP unavailability keeps its bounded visible behaviour | race, taxonomy and bounded startup: `OC79-OBS`; installed candidate with fake provider and local MCP fixture: `OC79-QUAL` |
| AC5 — focused and full project gates pass against the exact candidate; no private runtime data in source/docs/package; docs state installed behaviour only when qualified; exact commands/results with independent review | gates and integrated verification: `OC79-INT`; operator-neutral artifacts: all units; independent review: the claimed Supervisor review run on each unit |
| A1-FR-043 (exact selection, no sole-project fallback) | `OC79-LAUNCH` |
| A1-FR-043a (every launch route proves marker, registry and profile; missing `AGENTS.md` is onboarding-only) | `OC79-LAUNCH` |
| A1-FR-046 (greenfield unborn **and** brownfield; plain directory/subdirectory refused) | `OC79-INIT` |
| A1-FR-047 (the owner creates Git; init creates no repo, remote, commit or publication, and needs no first commit for conversation) | `OC79-INIT` (creation half), `OC79-LAUNCH` (conversation half) |
| A1-FR-048 (brownfield governance/files/branches/remotes/dirty state inspected and preserved) | `OC79-INIT` |
| A1-FR-049 (minimum portable identity; reuse one exact non-archived native Project; create and verify one when absent; refuse ambiguous/mismatched/archived/conflicting; no duplicates on repeat; pure `--dry-run`) | `OC79-INIT` |
| A1-FR-050 (constitution and testing standard confirmed by Morfeo with the owner afterwards; init invents neither) | `OC79-INIT` (must not invent), `OC79-LAUNCH` (must open before governance exists) |
| A1-FR-051 (contracts tracked; boards/sessions/memories/credentials/logs/caches/workspaces local and untracked) | all units |
| A1-FR-052 (one exact portable-to-native binding with no board/workspace; boards only from a finalized contract handoff) | `OC79-INIT` (binding), all units (no execution state) |
| A1-FR-100 (first conversation may start without `AGENTS.md`; guidance required before implementation/handoff) | `OC79-LAUNCH` (intake), `OC79-DOCS` (root `AGENTS.md` coherence), `OC79-INT` (final gate) |
| A1-SC-005 (two initialized projects keep distinct identity and local state; onboarding provisions no board/worker) | `OC79-INIT`, `OC79-QUAL` (isolation evidence) |
| A1-SC-018 (accurate `AGENTS.md` with induced updates or concrete non-applicability; closure verification) | `OC79-DOCS`, verified by `OC79-INT` |
| A1-SC-019 (clean empty folder supports the four-step flow with no first commit, remote, `AGENTS.md`, board, worker or automatic principles) | `OC79-INIT` + `OC79-LAUNCH`; end-to-end in `OC79-QUAL` |
| OBS-D-009 / OBS-D-032 (taxonomy and lightweight registry, never the discovery import during registration) | `OC79-OBS` |
| OBS-FR-025 (observer read-only toward Kanban, SessionDB, canonical artifacts, credentials and effect gates) | `OC79-OBS` |
| OBS-FR-026 (collector/reducer/CLI failure never blocks contract work; bounded retryable codes; genuine unreadable state fail-closed) | `OC79-OBS` |
| OBS-FR-027 (degraded collection produces a visible coverage gap; no false exactness) | `OC79-OBS` |
| OBS-FR-028 (no outbound or non-loopback network request; no listener) | `OC79-OBS` |
| OBS-FR-087 (no cyclic wait on plugin/import locks with MCP configured; first turn completes; unavailable MCP degrades boundedly; post-registration categories match; qualification exercises the real selected runtime) | `OC79-OBS` (regression + real MCP-enabled startup), `OC79-QUAL` (installed candidate) |
| Deliverables: source + focused tests for observer startup; source + tests for init and launcher onboarding; updated guidance/references/registry; red/green race reproduction; empty-root, dry-run, brownfield and identity test results; installed candidate TUI/MCP fixture receipt; preservation and diff evidence; separate release conclusions | `OC79-OBS`, `OC79-INIT`, `OC79-LAUNCH`, `OC79-DOCS`, `OC79-QUAL`, `OC79-INT` respectively |
| Non-deliverable: a first owner project, a live Morfeo conversation transcript, an active release activation or a published distribution | no unit — explicitly excluded and reported as such |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| In-scope observer sentence; OBS-D-032, OBS-FR-087; AC4 | **OC79-OBS** (Implementer, root-gated) | The observer adapter resolves tool categories through the selected runtime's lightweight registered-tool accessor plus the shared-metrics taxonomy, with no `model_tools` or plugin-discovery import during registration; a controlled two-thread regression reproduces the import/plugin-lock cycle against the frozen pre-fix source and passes on the candidate; registered and late-registered categories match the selected registry, a missing native capability stays a visible coverage gap, and the locked observation qualification manifest is re-derived deliberately if and only if locked files gain nodes |
| A1-FR-046/047/049, AC1–AC2, `plan.md` §10.1–10.2, `contracts/cli.md` init | **OC79-INIT** (Implementer, root-gated) | `aether init` refuses a plain non-Git directory with `git init` guidance and no filesystem/native/registry mutation; accepts an unborn exact Git root; previews exact native Project creation/reuse plus portable writes under `--dry-run` without performing them; creates exactly one verified native Project through the selected runtime's supported CLI when none exists, reuses one exact match, and refuses ambiguous, mismatched, archived, nested, non-Git, cross-profile and conflicting identity; repeating `init` is identity-preserving and interruption retry creates no duplicate |
| A1-FR-043/043a/100, A1-SC-019, AC3, `contracts/cli.md` launch | **OC79-LAUNCH** (Implementer, root-gated) | From a verified initialized unborn root, bare `aether` and `aether --check --json` bind the same portable/native project, the selected Morfeo profile and the exact Git-root cwd and report a launch plan without requiring root `AGENTS.md` or a commit; an uninitialized cwd refuses with actionable guidance instead of opening a sole unrelated registered Project; every identity, source and runtime mismatch stays fail-closed; conversation readiness stays distinct from a model reply |
| In-scope documentation sentence; AC5 (docs half); deliverable list | **OC79-DOCS** (Implementer, after the three behavior units) | `docs/getting-started.md`, `docs/guides/project-initialization.md`, `docs/reference/cli.md`, `docs/reference/limitations-and-troubleshooting.md`, `docs/capabilities.toml` and its generated reference `docs/reference/capabilities.md` describe only delivered behaviour for both outcomes, with historical evidence retained; the launcher-precedence oracle matches the corrected resolver; the canonical base manifest carries the contract line plus every tracked non-`specs/` file the objective adds; `AGENTS.md` is updated in the same change or given a concrete non-applicability reason |
| Testing Standard installed-path paragraph; AC1–AC4 installed halves; A1-SC-005; deliverables (receipts) | **OC79-QUAL** (Implementer, after DOCS) | One reproducible qualification entry proves, in a fully isolated disposable environment, the installed empty-Git-root sequence (`init --dry-run --json` → `init` → `aether --check --json`), the absence of `HEAD^{commit}` and of any remote before and after, the exact native id/marker and registry binding, and a bounded real TUI/backend cold start with a fake provider and a local MCP fixture that reaches agent readiness, emits the expected readiness/MCP signals and delivers exactly one early turn — plus the brownfield, identity-refusal, partial-retry and MCP-unavailability variants, with before/after preservation witnesses |
| AC5, deliverables (separate conclusions) | **OC79-INT** (Supervisor, same flow, `terminal=true`) | Reviewed units integrated in dependency order onto a candidate branch carrying the objective's local-only commits; residual manifest lines applied as mechanical config glue; integrated gates and the qualification entry re-run on the exact candidate; one PR through required checks and a green merge without bypass; issue #492 dispositioned; and the criterion-by-criterion terminal report with separate `release_impact` / `release_action` / `release_channel` conclusions |

## Execution graph

```text
root (Supervisor decomposition; completes once this breakdown is committed)
    ├── OC79-OBS    (Implementer; base 004c5f07)
    ├── OC79-INIT   (Implementer; base 004c5f07)
    └── OC79-LAUNCH (Implementer; base 004c5f07)
        → same-card Supervisor review on each unit

OC79-OBS, OC79-INIT, OC79-LAUNCH
    → OC79-DOCS  (Implementer; as-built guidance, capabilities, manifest)
    → OC79-QUAL  (Implementer; decisive isolated installed-path receipts)
    → OC79-INT   (Supervisor, same flow, terminal=true)
```

`OC79-OBS`, `OC79-INIT` and `OC79-LAUNCH` are disjoint in writable surface (observation
package and its locked manifest vs `commands/init.py` vs `launcher.py`) and none requires
another unit's accepted commit as its base, so they run together inside the single
`implementer` profile's capacity of 3. The remaining edges are real:

- `OC79-DOCS` writes guidance, the capability registry and the manifest for surfaces the
  three behavior units freeze. Documenting behaviour that can still change would produce a
  false as-built claim, and the launcher-precedence oracle must match the final resolver.
- `OC79-QUAL` needs the frozen revision. It measures the delivered artifacts and their
  public claims, so running it before `OC79-DOCS` would require measuring twice.
- `OC79-INT` consumes every reviewed unit and the qualification receipts; it is the
  terminal integration/closeout card and does not replace unit review.

`OC79-QUAL` is materially concentrated by necessity: the contract defines one
installed-path sequence ("`init --dry-run --json`, `init`, `aether --check --json`, then a
bounded real TUI/backend cold start with fake provider and local MCP fixture"), and both
outcome families are observed inside that same isolated installation. Splitting it would
duplicate the isolation/provisioning harness and the MCP fixture across two units that
would then edit the same new files — a real collision, not independence.

## Shared decisions stamped into every unit card

1. **Authority.** Objective Contract `oc_79b55027e7c3688d@v1` (SHA-256
   `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`) on base
   `004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, plus this breakdown, `plan.md`
   §4.6/§10.1–10.3, `contracts/cli.md`, OBS-D-009/032 and OBS-FR-025–028/087. Skills are
   reusable procedure only. Never edit, stage, exact-copy or re-finalize the canonical
   contract; a genuine contract defect returns to Morfeo through the existing
   collaboration path.
2. **No release identity movement.** `VERSION` stays `1.0.0rc8`; no tag, publication,
   activation, cutover, settings change, credential acquisition or history rewrite. The
   contract's compatibility assessment (`minor` / `defer` / `none`) is a hypothesis the
   terminal card reports with its limits — it is not publication permission.
3. **Runtime source of truth.** The selected maintained runtime is the installed managed
   `1.0.0rc8` candidate behind the current runtime pointer. Any unit that executes Hermes
   resolves the source actually imported and records its identity; no fork change, no new
   downstream-only capability, and no timeout increase as a substitute for a fix.
4. **Native Project binding.** Exact per-profile `$HERMES_HOME/projects.db` lookup by exact
   `primary_path` only. Reuse exactly one non-archived match; refuse several, refuse an
   explicit id whose path differs, refuse a matching archived Project, and create only
   when zero active and zero archived exact matches exist — through the selected runtime's
   supported native CLI under the selected Morfeo profile home, followed by readback
   verification. Never write `projects.db` directly and never import Hermes into manager
   code (the import-boundary oracle in `tests/test_observation_cli_plugin.py` enforces
   that `hermes_cli`/`hermes_state` stay confined to the two plugin modules).
5. **Runtime/profile resolution stays local to its unit, with one pinned precedence.** No
   new shared module is introduced in this objective: `commands/init.py` resolves the
   selected Morfeo profile home and the runtime `hermes` executable itself, following the
   same precedence `launcher.py` already implements, and `launcher.py` keeps its existing
   private helpers. Both units MUST use the same order so `init` and the launch path bind
   the same profile: profile home = `AETHER_HERMES_ROOT/profiles/morfeo`, else
   `state_root()/hermes/profiles/morfeo`, else `<repo>/home/profiles/morfeo`, else
   `state_root()/hermes/profiles/morfeo`; runtime executable =
   `AETHER_RUNTIME_ROOT/venv/bin/hermes`, else
   `data_root()/runtime/current/venv/bin/hermes`, else `<repo>/home/.venv-hermes/bin/hermes`,
   else `data_root()/runtime/current/venv/bin/hermes`. Extracting a shared helper would put
   two concurrent units in one file; if duplication is judged unacceptable it is recorded
   as an optional improvement, not absorbed into this objective.
5a. **Availability versus emptiness.** The native create/lookup interface counts as
   available when the selected runtime's `hermes` executable resolves and executes. An
   unresolvable, non-executable or failing target runtime refuses with an actionable error
   *before* any mutation (`plan.md` §4.6). An absent per-profile `projects.db` is **zero
   exact matches**, not an unavailable runtime, because the supported create path
   establishes it; the pre-existing `AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE` refusal stays
   for a genuinely unreadable or schema-invalid database.
6. **Observer taxonomy.** Category resolution goes through the selected runtime's
   lightweight registered-tool accessor plus the shared-metrics taxonomy and must not
   import the discovery-bearing module during registration. Missing native capability
   remains the visible `NATIVE_TOOL_CATEGORY_UNAVAILABLE` coverage gap, never a fabricated
   exact classification and never a reason to stop an agent.
7. **Onboarding boundary.** Only a finalized contract handoff provisions a board or
   workspace. `init`, the intake conversation and the launch path create no board, worker,
   task, commit, remote, constitution, root `AGENTS.md` or generic testing standard.
8. **Exact project selection.** No display-name, recency, board-default or approximate-path
   inference, and no fallback to a sole unrelated registered Project from an uninitialized
   cwd — actionable `git init` / `aether init` guidance instead.
9. **Isolation and preservation.** Fixtures isolate HOME, XDG data/config/state/cache,
   `TMPDIR`, `HERMES_HOME`, the project/board registry and every `HERMES_KANBAN_*`
   routing variable, and record before/after witnesses. Never touch the live installation,
   live profiles or boards, the running gateway/TUI, Context7's mitigation, `home/`,
   credentials, unrelated worktrees/branches/tags or historical evidence. Mocked OS
   supervision is labelled and never substitutes for real installed-package behaviour.
10. **Evidence and attribution.** Public evidence goes to
    `specs/001-aether-v1-productization/evidence/<UNIT>.md` (one file per unit,
    `OC79-OBS.md`, `OC79-INIT.md`, `OC79-LAUNCH.md`, `OC79-DOCS.md`, `OC79-QUAL.md`);
    private installation witnesses stay private. Tracked artifacts carry no
    operator-local paths, secrets, session content or provider/model identifiers. Record
    actual exits, skips and provenance; never invent pass counts. Mark reused evidence as
    still current or invalidated with its concrete reason.
11. **Review lane.** Every implementer unit self-checks and then hands off with the
    same-card review request (`kanban_request_review`, reviewer `supervisor`).
    Implementer never completes its own card; the claimed Supervisor review run issues the
    verdict. The terminal card consumes reviewed units and does not replace unit review.
12. **Manifest rule.** `.github/workflows/policy.yml` enumerates every tracked
    non-`specs/` file and `tests/test_public_artifacts.py` is the oracle. It is stale at
    base for the contract file itself. Any unit that adds, renames or removes a tracked
    non-`specs/` file records the exact literal line(s) in its completion handoff. `DOCS`
    applies the contract line and those recorded lines; `QUAL`, strictly after `DOCS`,
    applies the lines its own new files require and re-runs the oracle; `INT` re-runs it
    and applies only residual lines as mechanical config glue.
13. **Observation qualification lock.** `tests/test_observation_cli_plugin.py` is one of
    the seven locked core-test files; adding nodes there changes both the expected count
    and the node-manifest digest. Only `OC79-OBS` may update
    `scripts/qualify_observation.py` and its literal mirror in
    `tests/test_observation_qualification.py`, only as a direct consequence of its own new
    nodes, and it records the old→new count and digest with the derivation.
14. **Publication split.** Implementer units make no remote or live effect: no push, PR,
    merge, tag, release, activation, service restart, issue mutation or direct board
    cleanup. The terminal Supervisor card owns branch, PR, required checks, green merge
    without bypass, issue disposition and terminal evidence.

## Non-build obligations

- Authority is not expanded by this breakdown: no credentials, no provider/router/model or
  profile tuning, no check bypass, no force-push or history rewrite, no manual Pages
  dispatch, no extra release, no destructive cleanup, no live experiment on the installed
  candidate, no hand-edited release record and no live cutover.
- The contract's Stop Conditions stay binding. A genuine protected-edge denial stops that
  effect and is reported, never routed around through shell, manual database edits or new
  credentials. Repeated same-cause failure means reconsider the premise and report an
  incomplete stop rather than starting an unbounded campaign.
- Non-applicability is recorded, not silently skipped: where a required obligation does
  not apply to a unit, the handoff states the concrete reason.
- Closeout distinguishes objective-owned residue from retained historical artifacts, and
  reports `release_impact`, `release_action` and `release_channel` separately from the
  compatibility evidence that supports them. Neither green unit tests nor a board done
  state equals owner-objective acceptance.
