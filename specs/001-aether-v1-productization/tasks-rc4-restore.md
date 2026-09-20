# Execution breakdown: exact rc3 source restoration and rc4 activation finish

**Status:** verified executable decomposition for Objective Contract
`oc_f190ae9e878151e6@v2`. This is the Supervisor-owned execution breakdown; it
does not widen the contract, redefine material design, or record acceptance.
Card and board identities stay on the execution board.

**Derived by:** Supervisor (root task `t_062f75a1`, flow
`aether.flow.v1:d4e442666b317f10b2394f4eda67772d419978b1cde93c61e6c83fd923a8aa94`).

**Source contract:** `.aether/objective-contracts/oc_f190ae9e878151e6/v2.md`
(SHA-256 `9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188`)
on base `3e814325d6108d8d9b61534c8c6c0093a5a68c0e`.

**Predecessor:** `oc_f190ae9e878151e6@v1` (`tasks-rc4-bootstrap.md`) remains
historical. Independently reviewed BS-DIAG / BS-BRIDGE / BS-PROOF evidence is
consumed where identities remain exact. Live hop 1 under v1 correctly refused
before pointer mutation (`LOCAL_UPDATE_REFUSED` / non-regular file in
`hermes-source`) and is preserved; there is no retry under v1. Do not reopen
LG-CLI / LG-LIFE / LG-KNOW / LG-DOCS / LG-INT or BS-DIAG / BS-BRIDGE as new
product work.

**Owning issues:** [#485](https://github.com/DarkArty07/Aether-Agents/issues/485)
(bootstrap/restoration; stays open for permanent single-hop).
[#480](https://github.com/DarkArty07/Aether-Agents/issues/480),
[#481](https://github.com/DarkArty07/Aether-Agents/issues/481),
[#482](https://github.com/DarkArty07/Aether-Agents/issues/482) close only from
final live evidence. [#261](https://github.com/DarkArty07/Aether-Agents/issues/261)
stays open.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03`; repository `DarkArty07/Aether-Agents` |
| Bound knowledge | `project_knowledge` `INDEX_MISSING` at this revision; source inspection used |
| Contract bytes | SHA-256 `9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188`; `status: final`, `version: 2`, supersedes v1 |
| Base / branch | Board `worktree_base_ref` = HEAD = `3e814325d6108d8d9b61534c8c6c0093a5a68c0e`. Child worktrees start from that base unless a unit stamps a different parent |
| Merged rc4 | `5a897746afe422f3c07f2290f9115d60204ef4d2`; local annotated tag `v1.0.0-rc.4` (tag object `fc2a196c…`); not on origin. `origin/main` is still `5a897746` |
| Maintained fork | `DarkArty07/aether-hermes` `aether-main` `aed6591a69f453a1867b73628603e7b53ba40ffc`; release-lock `hermes.source_tree_sha256` `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` |
| Reviewed bridge | Local commit `d763c15b30f6edd8709aa2df33772b3601c67915` (VERSION-only child of `5a897746`); annotated tag `v1.0.0-a.4` (tag object `5350ebb0…`); wheel `aether_agents-1.0.0a4-py3-none-any.whl` SHA-256 `0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec`. Revalidate immediately before use; do not recreate |
| Active install | `1.0.0rc3-8987f650c027ad09`; doctor historically `ACTIVE_RELEASE_REVALIDATION_FAILED`; pending transitions 0. `hermes-source` contains `node_modules/`, `ui-tui/node_modules/` and `ui-tui/dist/entry.js`. Live hop 1 under v1 refused `LOCAL_UPDATE_REFUSED` before any pointer move |
| Reviewed helpers | `src/aether_agents/lifecycle.py`: `_tree_sha256` (refuses symlinks/non-regular), `_materialize_git_archive`, `_harden_private_tree`, `validate_release` (walks `hermes-source` with `_tree_sha256`), `_activate_existing_locked` (revalidates **previous** before pointer move) |
| Design sufficiency | Owner intent, exact-byte restoration, allowlist, atomic quarantine/swap/rollback, in-scope 1–7, out-of-scope, authority, six deliverables, AC-1…AC-8, testing standard and stop conditions settle outcome, interfaces, oracles and authority. No missing material product decision found |
| Policy debt | Tracked `.aether/objective-contracts/oc_f190ae9e878151e6/{v1,v2}.md` are absent from `.github/workflows/policy.yml` (426 expected vs 428 non-`specs/` files). RS-RESTORE registers both plus any new non-`specs/` paths it adds. Do not waive the gate |
| v1 residue | BS-DIAG tests/policy/evidence and BS-PROOF harness/evidence live on unmerged unit branches, not on this base. Consume identities/oracles; do not merge those branches as a hidden base. BS-CLOSE on the v1 board stays blocked; this v2 graph replaces that live lane |
| Profiles | `implementer`, `supervisor`, `morfeo` exist; no extra role or limit |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Restoration is rollback, not a bypass | Exact `git archive` of `aed6591…` must hash to `cc1ebf94…`. Expected files have zero missing/changed/type-mismatched entries. Live extras must be confined to the three npm/TUI prefixes. Integrity checks stay armed | RS-RESTORE refuses and does not mutate on any other delta. No unit weakens `_tree_sha256` or edits expected bytes |
| `lifecycle.py` hotspot | Production restore is a bounded fixture, not a new public lifecycle API. #485 owns permanent single-hop/restoration machinery | RS-RESTORE must not edit `src/aether_agents/lifecycle.py` except by returning a source-backed question. Call existing helpers |
| Same-file collisions | `policy.yml` is the only production-adjacent hotspot this objective may edit among Implementers. `tests/test_observation_lifecycle.py` stays untouched to avoid colliding with unmerged BS-DIAG | New tests go in a new module. Only RS-RESTORE edits `policy.yml` |
| Inventory vs restorer | Classification is the restorer's admission gate and uses the same archive/hash/allowlist | One Implementer unit owns both. Splitting them would serialize on the same oracles and duplicate inventory code |
| Contaminated-previous hops | v1 disposable hop 1 had no previous release, so it did not cover `validate_release(previous)`. v2 proof must start from a contaminated previous | RS-PROOF is serialized after independently reviewed RS-RESTORE. It does not reimplement the restorer |
| Bridge parent | Bridge commit parent is `5a897746`, not `3e814325`. Do not recreate or retag | RS-PROOF / RS-CLOSE revalidate `d763c15b` / `v1.0.0-a.4` / wheel `0345df73…` |
| Live cutover kills the worker | Restoration quiesces Aether-owned gateway/TUI; hops rewrite projections and restart `hermes-gateway-morfeo.service` | Only RS-CLOSE mutates live state, from a durable transient user unit that is **not** a child of that gateway |
| Publication | Implementers never push, PR, merge, remote-tag, activate, or mutate issues | RS-CLOSE owns live effects, issue comments, and any later source PR for restoration tests |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| In-scope 1–2; AC-1, AC-2; testing-standard restoration tests | **RS-RESTORE** (Implementer, root-gated) | Independent live inventory proving expected-file equality and allowlisted extras; tested restorer that materializes/hardens a clean sibling, atomically quarantines/swaps, makes disposable `validate_release`/doctor ready, and rolls back injected failures. No live mutation, no hops |
| In-scope 3–4; AC-3, AC-4 | **RS-PROOF** (Implementer; after independently reviewed RS-RESTORE) | Revalidated bridge identities plus a disposable contaminated-previous two-hop: pre-restore hop refuses; reviewed restorer makes rc3 ready; lexical rc3 then prepares/activates the bridge; bridge manager prepares/activates exact final rc4. Live selectors untouched |
| In-scope 5–7; AC-5, AC-6, AC-7, AC-8; resumed LG-CLOSE | **RS-CLOSE** (Supervisor, same flow, `terminal=true`) | Pre-live witnesses; live atomic restoration; ready rc3 validation/doctor; two hops from one durable user unit; final rc4 doctor/TUI/launcher/Graphify/state; #480/#481/#482 close; #485 honest open record; quarantine retained; residue audit; three release conclusions |

## Execution graph

```text
t_062f75a1 (Supervisor decomposition root)
    └── RS-RESTORE (Implementer; base 3e814325)

RS-RESTORE → same-card Supervisor review
    → RS-PROOF (Implementer; after independently reviewed restorer)

RS-PROOF → same-card Supervisor review
    → RS-CLOSE (Supervisor, same flow, terminal=true)
```

RS-RESTORE is root-gated and concentrated because inventory, allowlist refusal,
hardening, swap and rollback share one writable restorer/test surface.
RS-PROOF is serialized because it must import the reviewed restorer and seed a
contaminated previous. RS-CLOSE is serialized because live restoration and
cutover are Supervisor-owned and interrupt the Aether-owned gateway.

Same-card Supervisor review is the unit review lane. RS-CLOSE consumes
independently reviewed units and does not replace unit review.

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_f190ae9e878151e6@v2` (SHA-256
   `9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188`) on base
   `3e814325d6108d8d9b61534c8c6c0093a5a68c0e`, plus this breakdown. Skills are
   reusable procedure only. Never create, edit, stage or exact-copy the
   canonical contract.
2. Final rc4 identity is immutable: package `1.0.0rc4`, display `1.0.0-rc.4`,
   local annotated tag `v1.0.0-rc.4` on `5a897746afe422f3c07f2290f9115d60204ef4d2`.
   Do not move, delete or recreate that tag. Fork
   `aed6591a69f453a1867b73628603e7b53ba40ffc` is unchanged. Source digest
   `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`.
   `.patch` files are never replayed.
3. Bridge identity (local-only, not a user candidate): package `1.0.0a4`,
   display `1.0.0-a.4`, annotated local tag `v1.0.0-a.4` on
   `d763c15b30f6edd8709aa2df33772b3601c67915` (VERSION-only child of
   `5a897746`; tag object `5350ebb0ea91f6d6099d96d7448590515fff6036`; wheel
   SHA-256 `0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec`).
   Revalidate those bytes immediately before disposable or live use; do not
   recreate the commit/tag. Bridge conclusions `none/defer/none`. Restoration
   conclusions `none/defer/none`. Final rc4 retains `patch/prepare/prerelease`.
   No public tag/branch/release/package.
4. Extra-path allowlist (closed): extras may be regular files or symlinks and
   must be confined to `node_modules/**`, `ui-tui/node_modules/**`, or
   `ui-tui/dist/entry.js`. Any extra outside those prefixes, any expected path
   missing/changed/type-mismatched, or a clean-archive digest other than
   `cc1ebf94…` refuses restoration with no mutation.
5. Preservation: never edit the owner's primary checkout, live
   `$XDG_DATA_HOME/aether` / `$XDG_STATE_HOME/aether` (except RS-CLOSE through
   the reviewed restorer and supported lifecycle commands), `home/`,
   credentials/provider/model/router, the unrelated `hermes-gateway-hestia`
   service, unrelated worktrees/branches/stashes/boards, prior rc1/rc2/rc3/rc4
   tags, the bridge tag/commit, or release records/selectors/wheels/profiles.
   Implementer units make **no** live source swap, process stop, hop, or remote
   effect. Runtime/current, active/record JSON, manager/runtime environments
   and mutable state are not edited by restoration: only the `hermes-source`
   directory is swapped.
6. Restorer mechanics (RS-RESTORE implements; RS-PROOF/RS-CLOSE consume):
   materialize `git archive` of the exact fork commit via
   `lifecycle._materialize_git_archive` into a sibling directory on the **same
   filesystem** as the target `hermes-source`; require
   `_tree_sha256(clean) == cc1ebf94…`; compare every expected relative
   path/type/hash; harden the clean tree with `_harden_private_tree`; quiesce
   is **not** part of the fixture (live-only in RS-CLOSE); atomically
   `os.rename` the contaminated tree to a durable quarantine **outside** the
   release (sibling of the release directory, never inside `hermes-source`,
   never deleted) and rename the clean tree into `hermes-source`; fsync
   parents. Cross-device rename is a refuse. Post-swap, disposable
   `validate_release` and doctor for that previous release must be ready.
   Injected failures at pre-swap refuse, swap rename, and post-swap
   validation restore the original tree and leave exactly one `hermes-source`
   (no ambiguous pair). The fixture is not a public CLI and not a general
   cleanup policy.
7. Invoke managers by lexical immutable release path
   `<data-root>/releases/<release-id>/manager/bin/python` (or that tree's
   `-m aether_agents.cli`). Never `runtime/current`, never `PYTHONPATH` as
   installation, never a candidate interpreter as if already active. Compare
   paths with `os.path.abspath` / `normcase`; do not `Path.resolve()` the venv
   python.
8. Disposable fixture environment (RS-PROOF; RS-RESTORE tests use `tmp_path`):
   isolated `HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CONFIG_HOME`,
   `XDG_CACHE_HOME` such that `LifecycleManager._is_installed_environment` is
   **false**. Do not set those so the disposable store equals
   `Path.home()/".local/share/aether"`. Scrub inherited `HERMES_KANBAN_*`,
   `HERMES_HOME`, `HERMES_SESSION_ID`, `PYTHONPATH`, `UV_*`, `PIP_*`. Witness
   live `active.json`, `runtime/current`, Aether-owned unit file and operator
   projections before/after; they must be byte-identical for Implementer units.
9. Hop 1 runs the live lexical rc3 manager python with redirected XDG so rc3
   **code** prepares the bridge into the disposable store. Hop 2 runs the
   **bridge** manager from its disposable immutable release path. Bridge is
   never a user candidate: no ordinary workload, launcher canary or Graphify
   canary there. Final rc4 must contain hash-bound TUI/provenance and branded
   projections; doctor ready; pending transitions 0.
10. Under v2, no live hop starts until restoration and the contaminated-previous
    two-hop proof pass independent review. Live restoration failure rolls back
    and stops; hop-1 failure preserves restored rc3; hop-2 failure preserves
    the bridge and uses only reviewed supported disposition.
11. Test standard (`CONTRIBUTING.md`, not weakened): fail-first focused nodes,
    then `uv run --frozen ruff check/format --check src/aether_agents tests scripts`,
    `uv run --frozen mypy src/aether_agents` when Python under `src/` changed
    (RS-RESTORE should not change `src/`; record that skip reason), focused
    pytest for new nodes, `git diff --check`. Full coverage/docs/build gates
    apply to surfaces the unit touches. No new skip. No live auxiliary/model
    in Implementer units. Distinguish deterministic, live, skipped and reused
    evidence. Reused PR #484 and reviewed v1 BS-* evidence is attributed
    separately and is not new proof.
12. Evidence: each Implementer unit writes exactly one record at
    `specs/001-aether-v1-productization/evidence/<unit-id>.md`. Larger logs
    travel as native task attachments. No secrets, credentials,
    provider/model/router bindings, operator homes, live-state values,
    board/card identities or machine-specific paths in portable artifacts.
    Runtime paths belong in the private card handoff only.
13. `policy.yml`: only RS-RESTORE among implementation units edits it, and only
    to add `.aether/objective-contracts/oc_f190ae9e878151e6/v1.md`,
    `v2.md`, plus any new non-`specs/` paths that unit itself adds. RS-PROOF
    prefers `specs/001-aether-v1-productization/fixtures/` so it does not
    touch `policy.yml`.
14. Unit compatibility evidence is `none` for restoration/bridge (local-only
    unblocker, never published) unless a unit lands tests that should later
    merge (`patch` in that case, still not a release). Aggregate
    `release_impact` / `release_action` / `release_channel` belong only to
    RS-CLOSE.
15. Completion: local commit; same-card review (`kanban_request_review`,
    reviewer `supervisor`); no push/PR/merge/remote-tag/issue mutation. If
    inspection shows a unit is oversized, colliding, or unsupported, stop and
    return a source-backed question. If live extras escape the allowlist or an
    expected file differs, stop and return to Morfeo; do not widen the
    allowlist.

## RS-RESTORE — Exact inventory and atomic restorer

- Source: in-scope 1–2; AC-1, AC-2; testing-standard restoration tests; this
  unit.
- Outcome: (1) independently materialized `git archive` of fork `aed6591…`
  hashes to `cc1ebf94…`; every expected path/type/hash matches the active rc3
  `hermes-source` with zero missing/changed entries; every extra is a regular
  file or symlink under the three allowlisted prefixes; any other delta
  refuses. (2) A reviewed fixture that materializes/hardens a clean sibling,
  atomically quarantines and swaps, makes disposable rc3 `validate_release`
  and doctor ready, leaves record/selector/manager/runtime/profile/state
  bytes unchanged, and on injected failures restores the original tree with
  no ambiguous pair. Excludes live mutation, process quiesce, hops, issue
  comments, activation, `lifecycle.py` production edits, bridge recreation.
- Inputs: base `3e814325`. Shared decisions 4 and 6. Existing helpers
  `_materialize_git_archive`, `_harden_private_tree`, `_tree_sha256`,
  `validate_release`. Fork commit `aed6591…` from a **disposable** clone or a
  verified-clean checkout at that exact commit (do not mutate a dirty
  provisioned fork tree). Live `hermes-source` is **read-only**.
- Boundaries: writable
  `specs/001-aether-v1-productization/fixtures/restore_exact_hermes_source.py`
  (name may vary under that fixtures directory),
  `tests/test_source_restoration.py` (new module; do not edit
  `tests/test_observation_lifecycle.py`),
  `specs/001-aether-v1-productization/evidence/RS-RESTORE.md`,
  `.github/workflows/policy.yml` (this contract's v1 and v2 plus this unit's
  new non-`specs/` files only). Preserve `src/**`, `VERSION`, tags, live
  state, bridge refs.
- Judgement: quarantine directory naming, how tests inject rename/validation
  failure, whether doctor-ready is asserted via `LifecycleManager` in
  `tmp_path` rather than the live CLI. Escalate if helpers cannot swap without
  editing production `lifecycle.py`, if live extras escape the allowlist, if
  expected files differ, or if same-filesystem atomic rename is impossible.
- Verification: fail-first then GREEN on: expected-file hash equality;
  extra-prefix refusal; symlink/non-regular extras inside the allowlist
  accepted as extras (not copied into the clean tree); extras outside the
  allowlist refuse with zero mutation; hardening of the clean tree; refuse
  cross-device; quarantine durable after success; rollback on injected
  pre-swap/swap/post-swap failure; no mutation outside the target
  `hermes-source`/quarantine pair; disposable contaminated previous becomes
  `validate_release`-ready after swap and unchanged in record/selector bytes.
  Independent live inventory evidence (counts + hash equality, not a dump of
  paths that include operator homes). `git diff --check`; ruff/format for
  touched Python; policy expected list equals
  `git ls-files | grep -v '^specs/'`. No live `aether update --yes`, no
  process stop, no hop.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; unit compatibility `patch` if
  tests land, else `none`.

## RS-PROOF — Contaminated-previous disposable two-hop

- Source: in-scope 3–4; AC-3, AC-4; this unit.
- Outcome: revalidated bridge identities (AC-3) plus one disposable proof
  whose previous release is an exact rc3 record **with** allowlisted
  contamination: lexical rc3 manager first refuses; reviewed restorer makes
  that previous ready without changing record/selector/manager bytes; rc3 then
  prepares/activates the bridge; the bridge manager authenticates the
  rc3-created record and prepares/activates exact final rc4 with hash-bound
  TUI/provenance, branded projections, doctor ready, pending 0. Live
  selectors/services/profiles/records byte-identical. Excludes live cutover,
  issue mutation, public refs, ordinary workload on the bridge, restorer
  redesign.
- Inputs: independently reviewed RS-RESTORE fixture and oracles; reviewed
  BS-BRIDGE commit/tag/wheel (revalidate; do not recreate); reviewed BS-PROOF
  hop receipts as identity hints only (those hops had no previous release).
  Fork at exact `aed6591…` in a disposable checkout. rc4 checkout at
  `5a897746` with tag `v1.0.0-rc.4`. Bridge checkout at `d763c15b` with tag
  `v1.0.0-a.4`. Lexical installed rc3 manager python for
  `1.0.0rc3-8987f650c027ad09`.
- Boundaries: writable evidence
  `specs/001-aether-v1-productization/evidence/RS-PROOF.md` and harness under
  `specs/001-aether-v1-productization/fixtures/` only. Consume the reviewed
  restorer by import/path from the reviewed RS-RESTORE commit; do not fork a
  second restorer. Preserve `src/**`, `VERSION` on `main`, live XDG, services,
  tags.
- Judgement: how to seed a disposable previous rc3 release with representative
  extras without copying live `active.json` as installation; whether to adapt
  the unmerged v1 `run_bs_proof.py` from commit `37f3487e` as a starting
  point. Escalate if the lexical rc3 manager cannot refuse then succeed after
  restore, if the bridge manager cannot authenticate its rc3-created record,
  if final rc4 TUI is incomplete, or if any live path is required.
- Verification: revalidate `git diff --stat 5a897746..d763c15b` is VERSION
  only, tag object/target, wheel `Version: 1.0.0a4`, no remote ref. Pre/post
  fingerprints of live `active.json`, `runtime/current` target, Aether-owned
  unit file and operator launcher/Desktop/WSL projections. Pre-restore hop
  1 refuses with the non-regular/source-integrity class (not a private-path
  miss). Post-restore: rc3 `validate_release`/doctor ready in the disposable
  store; hop 1 bridge identity/authority, TUI may be absent, no canary; hop 2
  final `5a897746` / `v1.0.0-rc.4` / fork digest / TUI sha / branded
  projections / doctor ready / pending 0. Attach raw JSON receipts. No live
  mutation.
- Dependencies: independently reviewed RS-RESTORE.
- Completion: local commit of evidence/harness only; same-card review;
  unit compatibility `patch` (harness) or `none` (evidence-only).

## RS-CLOSE — Live restore, two-hop, LG-CLOSE canaries, issues, residue (Supervisor)

Not Implementer work. After independently reviewed RS-RESTORE and RS-PROOF:

1. Record pre-live witnesses (active rc3 selector/service/state, active-source
   inventory). Doctor may already be non-ready; that is history, not a reason
   to patch rc3.
2. From one durable transient **user** unit that is **not** a child of
   `hermes-gateway-morfeo.service`, quiesce only Aether-owned gateway/TUI
   processes, run the reviewed atomic restoration, record quarantine and
   hashes, prove rc3 `validate_release`/doctor ready, and otherwise leave
   release inventory/records/selectors/state unchanged. Failure rolls back and
   stops before hop 1.
3. The same durable unit invokes lexical immutable managers and supported
   commands for rc3→bridge then bridge→final-rc4. No ordinary workload/canary
   in bridge. Final selector, active record, wheels, fork digest, tag,
   TUI/provenance and projections agree; pending transitions 0. Hop-1 failure
   preserves restored rc3; hop-2 failure preserves the bridge.
4. Verify final rc4 (AC-7): installed `aether` / `Aether` / `Continue Aether`
   project-bound Morfeo; real TUI start/exit creates no source extras or
   digest drift; doctor remains ready; one configured Project Knowledge
   update returns a terminal receipt inside operation/host bounds; report
   route/fallback honestly; projects/boards/sessions/credentials/knowledge/
   observations/profiles remain present.
5. Close #480/#481/#482 only with criterion-linked live evidence. Comment on
   #485 that this restoration plus bridge is a one-time unblocker, not a
   general validation bypass, and keep #485 open for permanent single-hop.
   Leave #261 open. #481 may close only after final rc4 proves normal TUI use
   no longer recreates contamination.
6. No public bridge/rc4 tag, GitHub Release or PyPI. Local `v1.0.0-a.4`,
   quarantine and private receipts retained as audit. Objective-owned residue
   cleanup after durable evidence; preserve unrelated work.
7. Report separately: restoration `none/defer/none`; bridge `none/defer/none`;
   final rc4 `release_impact=patch`, `release_action=prepare`,
   `release_channel=prerelease`.

Any restoration tests that should land on `main` go through one normal PR
from this objective after review; the bridge branch/tag and quarantine are
never pushed.

## Verification of this decomposition

Traceability: AC-1/AC-2 → RS-RESTORE; AC-3/AC-4 → RS-PROOF; AC-5/AC-6/AC-7/AC-8
→ RS-CLOSE. Every in-scope item maps to exactly one unit; out-of-scope items
appear only as preserved boundaries.

Independence: only RS-RESTORE is root-gated. Necessary serialization is
proof-after-reviewed-restorer, then live restoration and cutover. Same-file
collisions (`lifecycle.py`, `policy.yml`, `tests/test_observation_lifecycle.py`)
are not split. Live inventory is part of RS-RESTORE because it is the restorer's
admission gate, not a second product.
