# RC16-INT integration evidence — reviewed merge set, gates, protected merge and the local rc.16 tag

## Context and boundaries

- **Unit:** `RC16-INT` (Supervisor integration lane, same-flow card)
- **Objective Contract:** `oc_c770cea3db51d97e@v2`, SHA-256
  `cd80efb52125f45af5340baf8119aeaddc4756f9d04ae7722137ae5df1f9adc7`
- **Execution breakdown:** `specs/issue-494-project-provenance/tasks-rc16.md` (commit `96c200e0`)
- **Integration base:** `dc4872834a2c670c506100fd60c69960247124f2` (a descendant of
  `origin/main` `20f3a2cb8a3360be050c13a0a9c73ed1d17456e2`)
- **Candidate identity:** package `1.0.0rc16` / display `1.0.0-rc.16` / local annotated tag
  `v1.0.0-rc.16`; maintained-fork Hermes exactly
  `58f8c37a49b341f25b8fdd6310542fe932031b8d` with materialized source-tree digest
  `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`
- **Explicit non-claims:** This document records integration-level facts. It does NOT constitute
  independent unit review, live managed cutover, installed-runtime canary, activation,
  publication, stable-release qualification, or agent-behavior qualification. The release
  conclusions (`patch` / `prepare` / `prerelease`) are recorded separately at the end and are
  aggregate conclusions owned by this lane.

## Reviewed units consumed

| Unit | Card | Reviewed tip | Reviewer verdict |
| --- | --- | --- | --- |
| `RC16-IDENT` | `t_313532fd` | `513c9dd3381ed1f802e3453e705fdb68eb880962` | approved, round 1 |
| `RC16-HLP` | `t_eef61de8` | `c2b4a9010efba3fdeebbe949488af3b576a38b69` | approved, round 2 |
| `RC16-TRANS` | `t_bb6dcddc` | `72713359d8568ec59b3f9950dc8ed816303e831e` | approved with an attributed bounded repair (both ordinary returns spent) |
| Decomposition root | `t_21f26600` | `96c200e0` | breakdown consumed as the execution plan |

No unit was consumed unreviewed. Every reviewed tip is an ancestor of the integrated tip, and
every path each unit changed still carries that unit's reviewed blob in the integrated tree
(23/23 paths compared, 0 changed).

## Merge commits (no squash, amend, rebase or history rewrite)

```
01d78f8c  Merge RC16-IDENT reviewed tip 513c9dd3 (rc16 identity, workflow pin, docs)
40ff10ba  Merge RC16-HLP reviewed tip c2b4a901 (HLP-428 required, HLP-433 deferred, pin-accurate reconciliation)
37170f1b  Merge RC16-TRANS reviewed tip 72713359 (exact RC15->RC16 isolated transition oracle)
```

Each unit's own commits remain individually inspectable in the integrated history.

## Attributed integration work by this lane

| Commit | Change | Basis |
| --- | --- | --- |
| `bb61b55d` | Complete the literal canonical base manifest in `.github/workflows/policy.yml` with the four tracked non-`specs/` files the units introduced (the RC16 transition entry, its qualification test, its two fixtures). Roster then exactly equals `git ls-files | grep -v '^specs/'` (478 == 478): four added lines, no CI-logic restructuring, no matrix promotion. | The approved breakdown's integration step, following the accepted LC-INT precedent. |
| `ac293ef1` | Repair two inherited identity-coupled oracles: regenerate the reviewed golden observation summary at the RC16 identity (exactly three version-derived lines move: `collector_version` `1.0.0rc14`→`1.0.0rc16`, `reducer_version` `…v1+1.0.0rc14`→`…v1+1.0.0rc16`, recomputed `summary_id` `sum_5ed729be…`→`sum_8ee21047…`), and record the reviewed packaging skill version bump (`supervisor-decomposition` `0.1.3`→`0.1.4`) in the map whose own comment requires a bump to be recorded so accidental drift stays caught. | Both oracles are **red at the integration base and at `origin/main`** — reproduced independently in a disposable checkout of each — and were hidden from CI because the rc15 release commits carried `[skip ci]`. They would have kept the required coverage lane red. |

## Independent verification of the reviewer-authored correction

The RC16-TRANS tip carries one functional repair authored by that unit's *Supervisor reviewer*
(`51024944`) rather than by its implementer, so it was self-verified at best. A separate
Implementer lane (`t_936c3948`) independently verified it at the integrated revision, plus the
two integration repairs above. Verdict: **pass**, with the confinement invariant held across 21
adversarial vectors (14 derived-destination symlink escapes, symlinked intermediate parent,
two-hop symlink chain, relative and nested relative symlinks, dangling symlink, non-temp work
root), a pre-fix/fixed discriminator (`0ba79130` accepted and materialized outside the work root
where the fixed tip refuses with exit 2 before mutation), the two repaired identity oracles
confirmed minimal and non-weakening, and the decisive qualification re-run green 8/8 with zero
live mutation. That lane's raw receipt is its own; the receipt this lane relies on is the one
recorded below.

## Gates measured at the integrated revision

Revision `1eb7f9003a6aedba8d443b4bf5cae7894b10e684` (tree
`47418bbde2c02c1b6c555fa65f536ed5c4c90d17`); the code-bearing revision for every gate below is
`ac293ef14be18f19127ea0e85b3302680a0c3041` (tree `ef9b119a1ba3105872e5aa9fc5a1a494f3619d2d`),
which differs only by documentation:

| Gate | Result |
| --- | --- |
| Full exact-Hermes runner (`uv run --frozen python scripts/run_tests.py`) | **2057 passed, 70 skipped, 0 failed**, exit 0 (1268.92 s) |
| Focused RC16 transition oracle (`tests/test_rc16_transition_qualification.py`) | 17 passed |
| `ruff check src/aether_agents tests scripts` | All checks passed |
| `ruff format --check src/aether_agents tests scripts` | 200 files already formatted |
| `mypy src/aether_agents` | Success: no issues found in 77 source files |
| `scripts/check_documentation.py` | documentation validation passed |
| `scripts/check_public_artifacts.py --root .` | public artifact path scan passed: tracked surface + 0 artifacts |
| `scripts/validate_hermes_patch_reconciliation.py --check --fork-checkout <clean pin checkout>` | `status: current`, exit 0; 33 records, `present: 30`, `absent: 1` (the deferred HLP-433 regression module), `unverified: 2` (`HLP-246`, `HLP-247`) |
| `scripts/validate_hermes_patch_reconciliation.py --candidate-check --selected-revision 58f8c37… --fork-checkout <clean pin checkout>` | `status: qualified`, exit 0; HLP-428 in the required set (32 required), HLP-433 deferred with `presence: absent`, `refusing_hlps: []` |
| `git diff --check` over the committed range | clean |
| Canonical base manifest (offline reproduction of the CI step) | exact match, 478 == 478, no duplicates |
| Local reproductions of the CI policy steps (canonical manifest, VERSION guard, legacy-name and forbidden-path guards, R0 design-baseline link check, `git ls-files -s specs` mode/stage assertions) | all pass |

## Isolated RC15 → RC16 qualification at the integrated revision

Executed against the exact integrated revision with a composed candidate whose only additional
content is the objective's own annotated tag identity, and with the maintained-fork pin checkout
at the pinned commit on branch `aether-main`:

| Scenario | Result |
| --- | --- |
| isolation | PASS |
| rc15-immutability | PASS |
| candidate-identity | PASS |
| transition-cycle | PASS |
| refusal-matrix | PASS |
| hlp-reconciliation | PASS |
| review-fallback | PASS |
| fork-regression | PASS |

`overall_status: passed`, exit 0, 108.1 s. The candidate identity scenario re-derived the pinned
fork digest `a2a9b374…` through the product's own lifecycle recipe on 9,378 materialized files,
and the refusal matrix covered wrong commit, wrong source digest, missing required HLP-428
component, dirty fork checkout, foreign fork origin and malformed lock. The release id resolved
by the transition cycle is `1.0.0rc16-14fa64728b9aaeae`.

Raw receipt (durable, ignored, private):
`.aether/receipts/rc16-int/rc16-transition-receipt-1790402684.json`,
SHA-256 `0f0a53a975f608abd5f9292905dce12d5d4ebbb95c5a00a1c0ebcd92eb94040a`.

## Release bundle and package-installed candidate

Built with `scripts/release_bundle.py build` at the integrated source revision with the pin
checkout, all probes clean and `failed_probes: []`:

| Member | SHA-256 |
| --- | --- |
| `aether_agents-1.0.0rc16-py3-none-any.whl` | `db90f0f55e019937189728e3be055b858848942a507c967f9c6b1ad2df8b0432` |
| `aether_agents-1.0.0rc16.tar.gz` | `790392787f4429055bf8aa089c4431a5df19a56aa6f6d25b2da34aca3a255087` |
| `aether-hermes-source-58f8c37a49b341f25b8fdd6310542fe932031b8d.tar.gz` | `dcb05748fc2109e30b7ee180aeefbbceb2616e79bb2d50d5a27c97acabf63b65` |
| `aether-agents-1.0.0rc16-release-lock.json` | `508f8942ec721bfe3ddfa1ff1b036de6aaca588aa5bf3c0a347734c3ad457829` |
| `aether-agents-1.0.0rc16-provenance.json` | `36bce1c4ff460f7e42bba68cab957129ce7aa89c12aea2757d7421f72bfe39e5` |
| `aether-agents-1.0.0rc16-package-members.json` | `88b73eeeef82c8ebc01fd26eaf79f36ebafb51c4faa86ad971ae0b12b5a1dd3c` |
| `aether-agents-1.0.0rc16-clean-install.json` | `d9c14d2dc52253e585be2d6c68d5b15e8c2070ee6f4692e71133df6fac6fbf72` |

The bundle's release lock carries schema version 5, source mode `maintained_fork`, repository
`https://github.com/DarkArty07/aether-hermes`, branch `aether-main`, commit
`58f8c37a49b341f25b8fdd6310542fe932031b8d`, digest
`a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144` and extras `["mcp"]`.

The package-installed clean-install probes report `aether 1.0.0rc16` and
`aether version --json` with `active_version` / `product_version` `1.0.0rc16`. The bundle is
local evidence only and is not published or attached to any release.

## Preservation witnesses

- The unrelated dirty file `specs/001-aether-v1-productization/plan-rc6.md` in the primary
  worktree is preserved and untouched by this lane.
- The stopped RC15 execution board and the historical incident board are untouched; the RC15
  release record, lock, local tag (`v1.0.0-rc.15` at
  `20f3a2cb8a3360be050c13a0a9c73ed1d17456e2`) and installed projection remain as they were.
- The unrelated `hermes-gateway-hestia` unit and the other user services are outside this lane.
- No release tag is pushed, no package is published, no deployment is dispatched, and no live
  installation is activated by this lane.

## Release conclusions (aggregate, owned by this lane)

- `release_impact = patch`
- `release_action = prepare`
- `release_channel = prerelease`

A merge does not imply a release. RC16 remains a local-only, unpublished prerelease candidate;
the annotated tag is local-only and is never pushed.

## Publication and tag receipt

Recorded after the fact, because a commit cannot contain the identity of the tag that points at
it: see the closing section appended by the integration lane once the protected merge and the
local tag exist.
