# Execution breakdown: Aether 1.0.0-rc.3 local activation and #417 runtime qualification

**Status:** Supervisor-owned execution breakdown for Objective Contract
`oc_a179da8d654aec8b@v1`. It does not widen the contract, redefine material design, or
record acceptance. Unit and card identities, board values and live-state values stay on
the owning execution board and are not published here.

**Source contract:** `.aether/objective-contracts/oc_a179da8d654aec8b/v1.md`
(SHA-256 `0f045ab552c277a88c19c07b3e695b313c0f0a3a14f8bcd632700f8c1b68a7b6`), `status: final`.

**Owning issue:** [#261](https://github.com/DarkArty07/Aether-Agents/issues/261);
qualification target [#417](https://github.com/DarkArty07/Aether-Agents/issues/417).

**Predecessors:** `specs/001-aether-v1-productization/tasks-rc2.md` (historical procedure
evidence for the non-accepting rc.2 lane) and the published-but-rejected rc.1 lane remain
evidence only. Nothing in this file supersedes them.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | Repository `DarkArty07/Aether-Agents`; contract `project_id` matches the provisioned project binding; contract bytes hash to `0f045ab5…`, `status: final`, `version: 1` |
| Base | Board `worktree_base_ref` is `ad85b729746a1eb756f96f138894d527122ab2fd` = accepted `origin/main` `78984ebf9468892e9569ecbdead1977d6a2134ee` + the rc.3 authorization commit (contract file + its `policy.yml` manifest line). Every unit worktree on this board is created from that exact base |
| Maintained fork | `https://github.com/DarkArty07/aether-hermes` `aether-main` accepted revision `aed6591a69f453a1867b73628603e7b53ba40ffc`; `release.yml` `FORK_COMMIT` already pins it; the contract fixes it unchanged for rc.3 |
| Current runtime (pre-state) | Active release `1.0.0rc2-b3ad4dd42eb0e1da`, `aether doctor` ready, source mode `maintained_fork` at `aed6591…`, service `hermes-gateway-morfeo.service` active. Recorded as the pre-state to re-measure at activation time, not as rc.3 evidence |
| Release inputs | `VERSION` is `1.0.0rc2`; rc.3 tag/release do not exist locally or remotely; the rc.2 local tag `v1.0.0-rc.2` → `9df250eb…` and the rc.1 public tag/release stay byte-immutable |
| Design sufficiency | Owner intent, objective, decisions, in-scope/out-of-scope, authority, six deliverables, AC-1…AC-7, testing standard and stop conditions settle outcome, oracles, sequence and authority for the whole remaining work. No missing material product decision was found |
| Environment limits | One shared host; CI provides the seven protected checks (the heavy qualification). Local heavy suites are not duplicated for ceremony; the runtime interruption caused by activation is expected and authorized |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Publication ownership | Implementer units never push, open a PR, merge, tag, activate or mutate issues | One Implementer unit; every remote/live effect belongs to the Supervisor lanes |
| Deployment boundary | The repository's Pages workflow triggers on pushes to `main` touching `docs/**`, `website/**` or itself. The rc.3 identity changes live in root files, `tests/**`, `.github/workflows/release.yml` and `specs/**`, none of which trigger it | No unit may change `docs/**`, `website/**` or `.github/workflows/pages.yml`. Stale `docs/**` statements are recorded as residuals, never repaired here |
| Candidate identity | `aether update --local` requires a clean Aether checkout whose HEAD is the exact candidate commit carrying **exactly one** annotated release tag equal to `v` + display version, plus a fork checkout at the exact fork commit (`src/aether_agents/lifecycle.py:4288-4360`) | The source PR must merge first; the local tag is created on that merge before any preview/activation; the candidate checkout is dedicated and clean |
| Gate ownership | The seven protected checks run on the PR head in CI (`.github/workflows/policy.yml`: `pull-request-target`, `policy (3.11/3.12/3.13)`, `observation-qualification (3.11/3.12/3.13)`) and cover the full suite, coverage floor, mypy/ruff, docs registry, build and public-artifact scans | The source lane runs the focused set plus build/Ruff/mypy/docs checks locally; the merged revision is not re-qualified by a duplicated local heavy gate |
| Merge shape | AC-2: the PR is reviewed, the seven protected checks are green on its exact head, and it merges normally; no later source commit enters the candidate | The freeze records the merge commit and verifies its tree equals the reviewed head tree |
| Runtime interruption | Activation rewrites the Aether-owned service/launcher/Desktop projections and restarts the Aether-owned gateway, which owns the dispatcher and this flow's session. The unrelated gateway is never touched | All durable evidence precedes activation; the terminal card is the only step that may interrupt, and it resumes from its own card |
| Immutability | Rc.1's tag/assets/warning and rc.2's local tag/activation history are read-only evidence; no move, retarget, delete, `--force` or asset replacement is permitted | Verification lanes read them; the rc.3 artifact is a successor, never a repair of theirs |
| Public effect | This objective publishes nothing: no tag push, GitHub Release, bundle publication or package-index effect | Rollback/forward use the supported local paths only; a remote rc.3 tag must not exist at closeout |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| In-scope 1; AC-1; testing standard (source lane); decisions | **RC3-IDENTITY** (Implementer, root-gated) | The rc.3 identity in canonical source: `VERSION` `1.0.0rc3`; a truthful, local-only README status paragraph; a changelog entry; the `AGENTS.md` bounded-objective paragraph; reconciled release-workflow authority comments with the pin unchanged; every coupled oracle measured RED/repair/GREEN (`tests/test_public_artifacts.py`, `tests/test_release_bundle.py`, the observation golden fixture and, only if the digest relation flips, the reducer conflict-precondition case); one evidence record. Excludes `docs/**`, `website/**`, `.github/workflows/pages.yml`, `ROADMAP.md` |
| In-scope 2, 3; D1, D2; AC-2, AC-3; testing standard (freeze) | **RC3-INTEGRATE-TAG** (Supervisor, same flow, non-terminal) | Reviewed identity merged by normal PR with the seven protected checks green on the exact head; frozen merge recorded in a private preflight receipt; exactly one local annotated `v1.0.0-rc.3` tag on that commit; clean Aether and fork candidates verified; package build and non-mutating `aether update --local` preview recorded before activation |
| In-scope 4, 5, 6, 7; D3, D4, D5, D6; AC-4, AC-5, AC-6, AC-7 | **RC3-ACTIVATE-CLOSEOUT** (Supervisor, same flow, `terminal=true`) | Pre-state witness; explicit activation of the immutable local rc.3 release; doctor/service/selector/lock/import/profile/plugin/state checks; bounded live #417 status/changes/diagnose/watch canaries on the original large trace with monotonic elapsed times; one supported rollback to the recorded pre-state and forward rc.3 reactivation with mutable-state witnesses; truthful #417/#261 reconciliation; objective-owned residue cleanup; terminal report with the three release conclusions stated separately from their evidence |

## Execution graph

```text
decomposition root (Supervisor; this card)
    ├── RC3-IDENTITY (Implementer)

RC3-IDENTITY → reviewed → RC3-INTEGRATE-TAG (Supervisor; PR, checks, merge, local tag, preflight)
                                               └── RC3-ACTIVATE-CLOSEOUT (Supervisor; terminal=true)
```

Same-card Supervisor review applies to the Implementer unit; the integration and terminal
lanes consume the reviewed unit and never replace unit review.

## Dependency rationale

- `RC3-IDENTITY` is root-gated: it needs the verified receipt above and the exact base,
  both of which exist at `ad85b729`.
- `RC3-INTEGRATE-TAG` cannot start before the identity unit is reviewed and its branch is
  durably available; pushing, opening the PR, merging, tagging and previewing are
  Supervisor-owned publication-adjacent steps.
- `RC3-ACTIVATE-CLOSEOUT` depends on the frozen tag and the recorded preview; activation
  is the only step that may interrupt the Aether-owned runtime, so it runs last and
  resumes from its own card.
- No two units share a writable file: the Implementer unit writes the source surfaces and
  its evidence record; the Supervisor lanes write only their private receipts/evidence.

## Shared decisions stamped into every unit card

1. Authority is Objective Contract `oc_a179da8d654aec8b@v1` (SHA-256
   `0f045ab552c277a88c19c07b3e695b313c0f0a3a14f8bcd632700f8c1b68a7b6`) plus this
   breakdown. Skills are reusable procedure only. Never create, edit, stage or copy the
   canonical contract.
2. Release identity: package `1.0.0rc3`, display `1.0.0-rc.3`, annotated tag
   `v1.0.0-rc.3`; conclusions `release_impact=major`, `release_action=prepare`,
   `release_channel=prerelease`. The tag is local only in this objective and is never
   pushed. Rc.1 stays published/rejected; rc.2's local tag and activation stay immutable
   and non-accepting.
3. Maintained fork: `DarkArty07/aether-hermes` `aether-main` at
   `aed6591a69f453a1867b73628603e7b53ba40ffc`, unchanged by this objective. `.patch`
   files and HLP records are never replayed onto the active runtime.
4. Non-negotiable preservation: never edit the owner's primary checkout or its
   uncommitted paths, the live runtime release or mutable state under the Aether XDG
   roots, `home/`, credentials or provider/model/router configuration, the unrelated
   gateway service, unrelated worktrees/branches/stashes/boards, or the migration
   backups. Implementer units make no remote or live effect.
5. Deployment boundary: no unit may change `docs/**`, `website/**` or
   `.github/workflows/pages.yml`. Stale statements there are reported as residuals.
6. Evidence: each unit writes exactly one record at
   `specs/001-aether-v1-productization/evidence/<unit-id>.md`; larger logs travel as
   native task attachments. No secrets, credentials, provider/model/router bindings,
   operator paths, live-state values, board/card identities or machine-specific paths in
   portable artifacts.
7. Test standard (`CONTRIBUTING.md`, not weakened): focused nodes first, then the
   canonical commands for the surfaces the unit touches; a skip is never added or
   weakened to obtain green, and a run under abnormal load is reported as such instead
   of as a gate number.
8. Unit review is same-card (`kanban_request_review`, reviewer `supervisor`) with no
   implementation affinity; the integration and closeout lanes consume reviewed units and
   never replace unit review. A unit reports its own compatibility evidence; only the
   terminal report aggregates the three release conclusions.
9. If inspection shows a unit is oversized, colliding or unsupported by the contract,
   stop expanding it and return a source-backed question through the card's
   collaboration path instead of widening scope or weakening an oracle.

## Verification of this decomposition

Traceability: AC-1 and the source half of the testing standard map to `RC3-IDENTITY`;
AC-2 and AC-3 and the freeze half of the testing standard map to `RC3-INTEGRATE-TAG`;
AC-4…AC-7 and the activation/canary/rollback half map to `RC3-ACTIVATE-CLOSEOUT`. Every
in-scope item and deliverable is covered by exactly one unit; out-of-scope items appear
only as preserved boundaries or recorded residuals.

Independence: the single Implementer unit owns the whole identity surface because the
five source files and their coupled oracles are one atomic identity move — a split would
produce concurrent edits to the same files, which is not independence. The two Supervisor
lanes are serialized by authority and by the runtime interruption they may cause; they
write only their own receipts and evidence.

## Remaining Supervisor sequence (not acceptance)

1. `RC3-INTEGRATE-TAG`: push the reviewed identity branch, open the normal PR, confirm the
   seven protected checks on the exact head, merge normally without bypass, record the
   merge SHA and tree equality in the private preflight receipt, create exactly one local
   annotated `v1.0.0-rc.3` tag on that commit, prove clean Aether/fork candidate
   checkouts, build the candidate wheel, and record the non-mutating
   `aether update --local` preview (selector, release id, source/lock identity).
2. `RC3-ACTIVATE-CLOSEOUT`: record the pre-state witness, activate rc.3 explicitly,
   verify installed identity/health/imports/profiles/plugins/service, run the bounded
   #417 canaries on `ctr_80c325f04f9cae67bb4fcce7a782889c`, roll back once to the recorded
   pre-state, forward-reactivate rc.3, reconcile #417/#261 truthfully, audit
   objective-owned residue, and state the three release conclusions separately from their
   evidence. No remote tag, release, bundle or package-index effect may exist at closeout.
