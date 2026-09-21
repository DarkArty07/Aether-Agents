# Execution breakdown: bounded lifecycle, observer startup and launcher usability correction (rc6)

**Status:** verified executable decomposition for Objective Contract
`oc_b5926701207812e8@v1`. This is the Supervisor-owned execution breakdown; it does not
widen the contract, redefine the material design in
`specs/001-aether-v1-productization/plan-rc6.md`, or record acceptance. Card, flow and
board identities stay on the execution board.

**Derived by:** Supervisor (root task `t_6610f2a5`, flow
`aether.flow.v1:a88871409f103f77ed209cc18e9ab9bbd17c5f69b9a8d686330b0c9e93b6c11a`).

**Source contract:** `.aether/objective-contracts/oc_b5926701207812e8/v1.md`
(SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), `status:
final`, `version: 1`, `change_reason: null`, on base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`.

**Owning issues:**
[#485](https://github.com/DarkArty07/Aether-Agents/issues/485) (canonical objective),
[#488](https://github.com/DarkArty07/Aether-Agents/issues/488) and
[#490](https://github.com/DarkArty07/Aether-Agents/issues/490) (included defects);
applicable evidence from [#480](https://github.com/DarkArty07/Aether-Agents/issues/480),
[#481](https://github.com/DarkArty07/Aether-Agents/issues/481),
[#482](https://github.com/DarkArty07/Aether-Agents/issues/482),
[#487](https://github.com/DarkArty07/Aether-Agents/issues/487) and
[#439](https://github.com/DarkArty07/Aether-Agents/issues/439);
[#261](https://github.com/DarkArty07/Aether-Agents/issues/261) stays open.

**Predecessor breakdowns** (`tasks.md`, `tasks-rc2.md`, `tasks-rc3.md`,
`tasks-rc4.md`, `tasks-rc4-restore.md`, `tasks-rc5.md`,
`specs/005-project-knowledge-graphify/tasks.md`) remain historical evidence and are not
reopened. The rejected objective `oc_a7a3cff05e82c148@v1` and its rc5 activation failure
remain non-accepted history; this breakdown reuses its *source facts*, never its
acceptance.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope and the board; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`; tracked and unmodified at the base commit; `status: final` |
| Base / branch | Board `worktree_base_ref` = HEAD = `d2874c2f3fc839a82fbaa96ece6edebab3856298` ("docs: bound final launcher lifecycle and observer correction"). Child worktrees start from that exact base |
| Base vs remote | `origin/main` = `ee0aa036b2e0b70b137f761668209a5104f2e032`; the contract/plan/AGENTS commit `d2874c2f` is **local-only**, so this objective's PR must carry it together with `tasks-rc6.md` and the reviewed unit commits |
| Design sufficiency | `plan-rc6.md` L1/L2/O1/O2/U1 settle the material decisions (target-owned record and projection bytes, parent-owned lock/CAS/compensation, bounded `--to active` reconcile, asynchronous retained-history recovery with one validated index per snapshot, fixed transient codes, launcher preservation, rc6 identity and conclusions `patch`/`prepare`/`prerelease`). No missing material product decision was found |
| Live install prestate (read-only) | Supported `aether doctor --project <bound root> --json` returns `result: ready`, `active_version 1.0.0rc5`, zero diagnostic codes, `pending_count 0`, three profiles, no projection mismatches, service `active`. `runtime/current` resolves to the `1.0.0rc5-40d506a4117229ad` release. This is the coherent recovered rc5 the contract names as the only live fallback |
| Frozen artifacts | rc3 `d8ff984c67bfc147ac9c83cf8a34a72edc27c8df`, rc4 `5a897746afe422f3c07f2290f9115d60204ef4d2`, rc5 `ee0aa036b2e0b70b137f761668209a5104f2e032` all resolve in this repository. The rc3 reader lacks `tui_sha256`; the rc4 writer brands projections by exact `record.version == "1.0.0rc4"` |
| Tag state | Local annotated `v1.0.0-rc.1` … `v1.0.0-rc.5` exist; `v1.0.0-rc.6` is absent locally and remotely. `origin` carries only `v1.0.0-rc.1` |
| Retained corpus (private, observation store) | Scale that made foreground startup slow: 244 journal files, 76 summaries (75 incomplete), 7 projects, 22 registered plugin callbacks. O1's acceptance needs nameable corpus + measured time, not a universal SLO |
| Interfaces to consume | `src/aether_agents/lifecycle.py` (`LifecycleManager.{update,update_local,activate_existing,recover,rollback,doctor}`, `_reconcile_release_projections_locked`, `_commit_active`, projection specs, service controller); `src/aether_agents/cli.py` (`_UNSUPPORTED_COMMANDS` still lists `reconcile`); `src/aether_agents/launcher.py`; `scripts/aether_tui.py`; `src/aether_agents/observation/capture/hermes_plugin.py` (`_Observer`, `_collector_for_project`, `_restore_all_retained_bindings`, `_retained_trace_exists`, `register`), `observation/query.py` (`_ingest_for_query`), `observation/brief.py`, `commands/observe.py`; `scripts/qualify_observation.py` (locked core-test manifest `EXPECTED_CORE_TESTS`/node digest, mirrored in `tests/test_observation_qualification.py`) |
| Established gates | `CONTRIBUTING.md` locked runner (`uv run --frozen python scripts/run_tests.py`), Ruff check/format, mypy, `scripts/check_documentation.py`, `uv build`, public-artifact/privacy scan (`scripts/check_public_artifacts.py`), the pytest coverage floor (`fail_under = 78`, branch coverage), `tests/test_public_artifacts.py` base-manifest equality, and the `observation-qualification` CI job |
| Profiles / capacity | `implementer`, `supervisor`, `morfeo` exist; no new role, profile or limit. Board dispatch allows 4 in progress, `implementer` up to 3 concurrent, `supervisor` 1. Three of the five implementation units are genuinely independent and can overlap; the remaining chain is real serialization, not ceremony |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` (observation procedure, no authority) |
| Preserved residue | Owner primary checkout and its uncommitted work, the live rc5 install and its gateway/TUI processes, `~/.local/bin` operator wrappers, unrelated services (`hermes-gateway-hestia`, router, monitor units), retained rc3/rc4 quarantine and recovery receipts, unrelated worktrees/branches/tags, and every historical evidence file |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Who owns the active record bytes | The immutable **target** `record.json`, validated against its release lock/installed fingerprint, owns field shape and values; the source manager owns the lock, journal, CAS and compensation | `RC6-LIFE` must prepare/validate through the target's own reader in a bounded isolated subprocess and must never serialize source defaults, drop unknown keys, or "fix" a record by editing bytes |
| Who owns projection bytes | The authenticated **target** code produces launcher/Desktop/WSL bytes; the parent only validates bounds/ownership, journals prestate, commits with CAS and validates from the selected target | Projection generation moves into the target-interpreter pattern; the legacy `branded = record.version == "…"` branch in the executing source must stop deciding a successor's bytes |
| Reconcile surface | Only the already-active authenticated release may be reconciled through the reserved `aether reconcile --to active [--dry-run] [--yes] [--json]` surface; preview is non-mutating; unsupported modes stay unsupported | `RC6-LIFE` completes that CLI surface; `--to installed`, release selection, package install, service restart or record edits are explicitly out of scope |
| Launcher boundary | The generated launcher projection `exec`s `"$AETHER_RUNTIME_ROOT/venv/bin/aether"`, and the Desktop/WSL entries point at the release console script | The inherited-transport scrub belongs in the packaged launch path (`launcher.py`, `scripts/aether_tui.py`, owned by `RC6-LAUNCH`); projection *text* stays in `lifecycle.py` (owned by `RC6-LIFE`) and needs no second scrub implementation |
| Observer startup | Registration and hot native hooks install tools/hooks and record bounded events; retained-history recovery moves to the existing plugin worker with one validated index per catch-up snapshot | `RC6-OBS` owns the observation package and its qualification lock; the callback p95 ≤ 5 ms / p99 ≤ 20 ms and reduction gates stay unchanged |
| Observation identity strings | `tests/fixtures/observation/complete-summary.json` embeds the release identity (`collector_version`) | `RC6-OBS` must not regenerate it; `RC6-DOCS` regenerates it at the rc6 identity after the behavior units freeze |
| Identity is one coupled move | `VERSION`, `README.md`, `docs/index.md`, `CHANGELOG.md`, `docs/capabilities.toml`, the policy-workflow version guard, the base manifest, `tests/test_public_artifacts.py`, `tests/test_release_bundle.py` and the golden observation summary must move together | Only `RC6-DOCS` edits public identity and its oracles; behavior units keep brand-agnostic code |
| Policy manifest hotspot | `.github/workflows/policy.yml` must list every tracked non-`specs/` file; it currently omits this contract, and units that add files make it stale | Only `RC6-DOCS` edits `policy.yml`; every unit that adds or renames tracked files records the exact lines in its handoff, and `RC6-INT` applies those recorded lines as mechanical config glue before running the manifest oracle |
| Test isolation | `#439`: fixtures must never touch live HOME/XDG/profiles/boards/units/selectors/configuration, and mocked supervision must be disclosed | Every unit isolates HOME/XDG/TMPDIR/HERMES_HOME/board registry/`HERMES_KANBAN_*` and records before/after witnesses; `RC6-QUAL` is the unit that must prove confinement |
| Publication split | Implementer units never push, PR, merge, tag, activate or mutate issues; Aether does not own the gateway unit | `RC6-INT` owns branch, PR, checks, green merge and the local tag; `RC6-CLOSE` owns the single live window |
| Live-window hazard | Activating the candidate rewrites projections and restarts `hermes-gateway-morfeo.service`, which owns the dispatcher and every running worker, including this flow's own session | Only `RC6-CLOSE` mutates live state, from a durable transient user unit that is not a child of that gateway, with receipts stored outside the gateway cgroup and all durable evidence captured first |
| Legacy boundary | Frozen rc3/rc4 are isolated regressions only; the first live hop starts from recovered rc5; the required cycle is exact rc5 → candidate → rc5 → candidate in an isolated store | `RC6-QUAL` owns that cycle; unsupported legacy routes must refuse before mutation and be disclosed, never reported green |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| L1, L2; D1; AC-1, AC-2 | **RC6-LIFE** (Implementer, root-gated) | Target-compatible active-record persistence and byte-exact compensation, target-generated launcher/Desktop/WSL projections through the authenticated target interpreter, bounded non-mutating `aether reconcile --to active` completion that only reconciles the already-active release, target-reader validation before any mutation, and safe refusal for unsupported legacy routes — with focused regression coverage |
| O1, O2; D1; AC-4, AC-5 | **RC6-OBS** (Implementer, root-gated) | Registration and hot hooks return while the retained-history scanner is deliberately paused; retained bindings restore asynchronously through the existing worker with one validated index per catch-up snapshot and honest incomplete coverage; transient contention yields the fixed bounded codes in native tool and CLI while settled state still succeeds and corruption stays fail-closed; observation qualification lock updated deliberately |
| U1; D1; AC-6 (code half) | **RC6-LAUNCH** (Implementer, root-gated) | Packaged launch clears inherited transport selectors (`HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, stale active-session transport paths) and then binds the target interpreter/source/TUI; fresh and `--resume latest` launches select the exact backend, TUI, profile and project from a clean or contaminated parent environment, with unchanged locked-source digests and no npm/build |
| In-scope 7, 11; D3; AC-6 (guidance half), AC-8 (reporting) | **RC6-DOCS** (Implementer, after the three behavior units) | rc6 identity and coupled oracles, accurate startup/default-selection/recovery guidance (within-project, `--project PATH`, ambiguity, optional `AETHER_PROJECT_ROOT` precedence and removal for Bash/Zsh and Fish, generic paths only), canonical CLI/observation spec and capability reconciliation, and the policy manifest carrying this contract plus every file the objective adds |
| D2; AC-3, AC-7 (pre-live half) | **RC6-QUAL** (Implementer, after DOCS) | One reproducible qualification entry (`scripts/qualify_mixed_version_lifecycle.py`) with exact artifact/revision inputs and receipt output, runnable without the live installation: frozen rc3/rc4/rc5 defect reproductions, the exact rc5 → candidate → rc5 → candidate cycle against distinct real installed interpreters/records/serializers/generators, failure/interruption compensation, isolated installed fresh/resume PTY startup with polluted transport, documentation/usage checks, and before/after confinement witnesses for the live unit, active pointer and operator configuration |
| D4; AC-7 | **RC6-INT** (Supervisor, same flow, terminal=false) | Reviewed unit commits integrated in dependency order, recorded manifest lines applied, integrated gates and the qualification entry re-run on the exact candidate, one PR through required checks and a green merge without bypass, one local-only annotated `v1.0.0-rc.6` tag, non-mutating update preview, and the separate `patch`/`prepare`/`prerelease` conclusions |
| D5; AC-8 | **RC6-CLOSE** (Supervisor, same flow, terminal=true) | Pre-activation witnesses and re-validated rc5 fallback, one controlled activation from a durable transient unit outside the gateway cgroup, post-reopen doctor/state/service proofs with one native restart stability check, fresh/resume launcher canaries with measured time-to-agent-ready and one attributed minimal live reply, truthful issue dispositions, final-revision knowledge refresh, objective-owned residue cleanup and the criterion-by-criterion terminal report |

## Execution graph

```text
t_6610f2a5 (Supervisor decomposition root; completes once this breakdown is committed)
    ├── RC6-LIFE   (Implementer; base d2874c2f)
    ├── RC6-OBS    (Implementer; base d2874c2f)
    └── RC6-LAUNCH (Implementer; base d2874c2f)

RC6-LIFE, RC6-OBS, RC6-LAUNCH
    → same-card Supervisor review on each unit
    → RC6-DOCS   (Implementer; identity + guidance + manifest for frozen surfaces)
    → RC6-QUAL   (Implementer; composes the reviewed branches, decisive receipts)
    → RC6-INT    (Supervisor, same flow, terminal=false)
    → RC6-CLOSE  (Supervisor, same flow, terminal=true)
```

`RC6-LIFE`, `RC6-OBS` and `RC6-LAUNCH` are disjoint in writable surface (lifecycle/CLI vs
observation package vs launcher) and none requires another unit's accepted commit as its
base, so they can run together inside the single `implementer` profile's capacity of 3.
The remaining edges are real:

- `RC6-DOCS` moves public identity, guidance and the manifest, which must describe surfaces
  frozen by the three behavior units; it also needs the file list those units add.
- `RC6-QUAL` needs the corrected source. Its worktree starts at the contract base, so it
  composes the reviewed unit branches (recorded in its card) before building the candidate
  artifacts; it cannot run before them and must not re-implement their fixes.
- `RC6-INT` consumes every reviewed unit and the qualification receipts; `RC6-CLOSE`
  consumes the merged revision, the tag and the pre-live gate.

`RC6-LIFE` is materially concentrated by necessity: active-record persistence, projection
preparation, transitions, compensation, doctor and the reconcile surface live in one
7.7k-line module (`src/aether_agents/lifecycle.py`) whose regions are byte-coupled, and
concurrent edits to one file are not independent under current policy. Splitting it into
two cards would create a real same-file collision.

## Shared decisions stamped into every unit card

1. Authority is Objective Contract `oc_b5926701207812e8@v1` (SHA-256
   `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`) on base
   `d2874c2f3fc839a82fbaa96ece6edebab3856298`, plus this breakdown and
   `specs/001-aether-v1-productization/plan-rc6.md`. Skills are reusable procedure only.
   Never edit, stage, exact-copy or re-finalize the canonical contract; a genuine contract
   defect returns to Morfeo through the existing collaboration path.
2. Release identity: package `1.0.0rc6`, display `1.0.0-rc.6`, one **local-only** annotated
   tag `v1.0.0-rc.6`; `release_impact=patch`, `release_action=prepare`,
   `release_channel=prerelease`. No publication, no remote tag, no PyPI/OIDC, no stable
   `1.0.0` claim. Executable Hermes stays the maintained fork
   `DarkArty07/aether-hermes` `aether-main` `aed6591a69f453a1867b73628603e7b53ba40ffc`
   (source-tree digest `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`);
   no fork change.
3. Pinned surfaces that must not drift: `aether update [VERSION] …`, `aether reconcile
   --to active [--dry-run] [--yes] [--json]`, `aether rollback [VERSION]`, `aether doctor
   [--project PATH] [--json]`, bare `aether [--project PATH] [--json]` and
   `--resume latest`; native observation codes `AETHER-OBSERVE-BUSY` /
   `AETHER-OBSERVE-CATCHUP-INCOMPLETE`; CLI codes `STATE_BUSY` /
   `CATCHUP_INCOMPLETE` alongside the existing `STATE_UNREADABLE`; existing success/empty
   schemas and privacy limits unchanged.
4. Non-negotiable preservation: never touch the owner's primary checkout or its
   uncommitted work, the live rc5 installation (records, selector, projections, unit
   bytes), the running gateway/TUI processes, `home/`, credentials/provider/model/router
   configuration, unrelated services, unrelated worktrees/branches/tags, the retained
   rc3/rc4 quarantine and recovery receipts, or historical evidence. Implementer units
   make no remote or live effect: no push, PR, merge, tag, release, issue mutation,
   service restart, activation, or direct board/database cleanup.
5. Isolation is an acceptance prerequisite, not a test detail: distinct HOME, XDG
   data/config/state/cache, TMPDIR, HERMES_HOME, project/board registry and every
   `HERMES_KANBAN_*` routing variable; no inherited live D-Bus socket or `systemctl`
   side effects; hash/inode/mtime witnesses prove the live unit, active pointer and
   operator configuration were untouched. Mocked OS supervision is labelled and never
   substitutes for real installed-package behavior.
6. Evidence and attribution: public evidence belongs in
   `specs/001-aether-v1-productization/evidence/`; private installation witnesses stay in
   private state. Public or tracked artifacts contain no operator-local paths, secrets,
   session content or provider identifiers — use `<…>` placeholders and project-relative
   references. Distinguish direct-test evidence, reused exact evidence (state its
   unchanged artifact identity and scope), supported routes, and safe refusals.
7. Reused evidence: rc5-era evidence (`GW-SERVICE.md`, `TUI-PRESERVE.md`, `LG-CLI.md`,
   `LG-KNOW.md`, `RS-PROOF.md`, `DOCS.md`) may be cited only where its artifact identity
   and criterion applicability still match after the delta; the units record which items
   remain current and which are invalidated.
8. Review lane: every implementation unit is handed off with the same-card review request
   (`kanban_request_review`, reviewer `supervisor`) after self-check. Implementer never
   completes its own card; the claimed Supervisor review run issues the verdict. The
   terminal integration card consumes reviewed units and does not replace unit review.
9. Manifest lines: any unit that adds, renames or removes a tracked non-`specs/` file
   records the exact literal lines in its completion handoff for
   `.github/workflows/policy.yml`; `RC6-INT` applies them as mechanical config glue and
   then runs `tests/test_public_artifacts.py` as the oracle.
10. Checkpoint: seven hours from root claim
    (`2026-09-21T04:54:32Z` → `2026-09-21T11:54:32Z`) is a progress checkpoint. If the
    objective is incomplete then, the flow sends a compact exact
    progress/blocker/remaining-work update to the originating design steward; it never
    justifies weakening criteria, silently widening scope, a second live attempt, or
    killing healthy work.

## Non-build obligations

- Authority is not expanded by this breakdown: no credentials, no provider/router/profile
  tuning, no check bypass, no force-push or history rewrite, no manual Pages dispatch, no
  extra release, no destructive cleanup, no live rc3/rc4 experiment, no hand-edited
  release record and no second activation attempt.
- The failed rc5 objective stays non-accepted history; its operational recovery is not
  retroactive acceptance and its literal rc3 criterion is not waived here.
- The owner's current TUI is preserved until a new candidate TUI is verified; the live
  window never terminates it by convenience process-group scanning.
- Closeout distinguishes objective-owned merged residue from retained historical
  artifacts, and reports `release_impact`, `release_action` and `release_channel`
  separately from the compatibility evidence that supports them.
