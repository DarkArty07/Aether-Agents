# Mixed-version lifecycle qualification (RC6-QUAL)

**Unit:** RC6-QUAL (Implementer) — Objective Contract `oc_b5926701207812e8@v1`
(SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`) on base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`.

**Status:** direct qualification evidence for D2 / AC-3 and the pre-live half of AC-7, produced
against the composed candidate revision on a disposable, isolated installation. This is unit-level
evidence: integrated verification, the local-only annotated tag, and the live activation belong to
RC6-INT and RC6-CLOSE.

**Entry point:** `scripts/qualify_mixed_version_lifecycle.py` (new; pytest contract in
`tests/test_mixed_version_lifecycle_qualification.py`, frozen predecessor record fixtures in
`tests/fixtures/mixed-version/`). The entry derives every destination from `--work-root`, refuses
any destination that could overlap the operator installation or the read-only source store, and
runs without the live installation.

```
uv run --frozen python scripts/qualify_mixed_version_lifecycle.py run \
    --repo <clean checkout at the candidate revision> \
    --candidate-commit <composed revision> \
    --fork-checkout <maintained-fork checkout at aed6591a69f453a1867b73628603e7b53ba40ffc> \
    --source-store <read-only installation with the rc3/rc4/rc5 releases> \
    [--bundle-dir <release-bundle directory>]   # unqualified corroboration only, see Findings
    --work-root <disposable work root> \
    --receipts-root <durable private receipts root> \
    --scenarios all --json
```

Exit codes: `0` every selected scenario passed, `1` a scenario failed, `2` refused (missing,
mistyped, live or self-contradictory input). Raw receipts are private; this file carries the
sanitized scenario → command → result table, digests and limits.

## Composed candidate

| Input unit | Reviewed branch head |
| --- | --- |
| RC6-LIFE | `e9595d2e97aa85f2e0d7e4a501215865c0ab06ca` |
| RC6-OBS | `00be3b17630e108c53994e15afb380f31dffada3` |
| RC6-LAUNCH | `c79f5b147ae0c4f52c606978ff0bf3e82c5096fb` |
| RC6-OBS-2 | `05eed2dc07eed294dc131b36817c18ef13d1290e` |
| RC6-DOCS | `80ce317809d4413a718b3fec412c543b17e2c3ab` |

Merge order RC6-LIFE → RC6-OBS → RC6-LAUNCH → RC6-OBS-2 → RC6-DOCS on the contract base; every
unit-authored blob in the composition is byte-identical to its reviewed tip. Composed commit
`3dbde1e413a4d4846cd7361b625c3f41ea49af07`, tree
`ccf753d8482e0dd1d2384c45513d45b6f2e52641`, `VERSION` `1.0.0rc6`. The composition is reproducible
from the recorded heads and merge order alone.

## Installed lane under test

Isolated installation (disposable work root; distinct `HOME`, `XDG_*`, `TMPDIR`, `HERMES_HOME`,
project/board registry and every `HERMES_KANBAN_*` variable):

* rc3/rc4 — the authenticated installed trees copied byte-for-byte from the read-only source
  installation; 104 installed package files re-hashed against the frozen revisions' sources with
  no mismatch, and `record.json`/`release.json`/`release-lock.json` byte-identical (rc3
  `d8ff984c…`, rc4 `5a897746…`). They are executed as their own code; the first live hop never
  starts from them.
* rc5 — the exact `ee0aa036…` release installed by the shipped `setup` route from its own
  authenticated wheel and release lock.
* candidate `1.0.0rc6-051c7cb5b0bf5fd3` — built from the composed revision by the product's own
  local-candidate builder and promoted into the same store **by the rc5 manager** (the
  mixed-version hop), then rolled back and re-activated.

## Scenario → command → result

| Scenario | Representative command (generic paths) | Observed | Assertions | Receipt (private) |
| --- | --- | --- | --- | --- |
| prepare | `aether setup --wheel <rc5 wheel> --hermes-checkout <fork> --release-lock <rc5 lock> --yes --json`; release-copy verification | exact rc5 active, selector inside the isolated store, copies byte-identical | 3 | `run.json` `7ed85b39…` |
| cycle | `aether update --wheel <promotion wheel> --release-lock <promotion lock> --yes`; `aether rollback --yes`; `aether update 1.0.0rc6 --yes`; blocked-projection transition; three SIGKILL interruptions; rollback repair | rc5 → candidate → rc5 → candidate, pointer byte-exact against each target's own record, no false success, no pending half-state | 34 | `scenarios/cycle.json` `3e5ccb34…` |
| frozen-readers | frozen rc3 interpreter: `ReleaseRecord.from_json` on the post-rc4 pointer, the null-field variant, the corrected writer's pointer and its own record | rc3 reader rejects the post-rc4 shape (with a real value **and** with `null`), accepts its own generation and accepts the corrected writer's target-owned record | 10 | `scenarios/frozen-readers.json` `d358dcee…` |
| frozen-writer | frozen rc4 interpreter planning projections for a successor record; corrected source asking each target for its own plan | rc4 brands a successor with the legacy `hermes.desktop` shape; each target answers for its own identity with branded bytes | 5 | `scenarios/frozen-writer.json` `0f089f59…` |
| legacy | rc4 writer applying its projections to the managed destinations; `reconcile --to active` preview and apply; `reconcile --to installed`; unprovable-target refusal | preview non-mutating, apply finishes the handoff (`projections_reconciled: 1`, zero mismatches) with the release record byte-identical, unsupported mode refused, unprovable target refused before mutation | 14 | `scenarios/legacy.json` `e8015377…` |
| launch | packaged selector `aether --project <project> [--resume latest] --check --json` in clean and contaminated environments; real PTY launch | exact target backend/TUI/project/Morfeo profile bound; stale `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, session selectors neither used nor forwarded; release tree unchanged | 16 | `scenarios/launch.json` `5575ae66…` |
| docs | repository `check_documentation.py`, usage/documentation pytest modules, installed `aether version --json` | green; installed CLI reports `1.0.0rc6` | 3 | `scenarios/docs.json` `a209c4a2…` |
| isolation | guard refusal subprocess, split-root and transport-leak checks, live witnesses, service boundary | live work root refused with exit 2; no operator root, board variable, D-Bus socket or credential inherited; live unit/pointer/selector/operator config unchanged; disabled service controller | 7 | `scenarios/isolation.json` `31df9d8c…` |

Run-level facts: exit `0`, 92 assertions, 48 recorded commands, 417 744 ms wall clock,
environment identity `8ae12e16…`. Each scenario receipt records its own commands with argv, cwd,
exit status, timing, stdout/stderr digests and the isolation-relevant environment digest.

## Installed launch measurement

| Quantity | Value |
| --- | --- |
| Launch path | packaged selector → `runtime/current/venv/bin/aether` → release runtime (`hermes --tui --in <project>`) |
| Bound backend | `<store>/releases/1.0.0rc6-051c7cb5b0bf5fd3/runtime/bin/python` and `…/runtime/bin/hermes` |
| Bound profile / project | `<store>/state/aether/hermes/profiles/morfeo`, the isolated managed project |
| Time to target runtime's first output | 282 ms (first PTY output; `elapsed_ms` 90 234 is the full bounded observation window, terminated by the harness) |
| Corpus identity/scale at launch | segments 0, events 0, digest `null` (fresh isolated store; the retained-corpus measurement is the observation lane's receipt below) |
| Release tree after launch | unchanged (`tui` tree digest and `release.json` `tui_sha256` identical before/after) |
| Locked source digest | `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` unchanged |
| Agent-ready | **not reached in this lane**: no provisioned model provider exists in a disposable home, so the launched runtime stops at its configuration prompt (`Hermes isn't configured yet -- no API keys or providers found`). No provider quota was spent and no credential was copied. The provider-backed agent-ready measurement and the single live reply stay with the terminal live window. |

No npm/build step runs at launch (the release tree is witnessed unchanged), and neither the
project nor the profile is guessed: two projects in the registry produce a visible ambiguity
refusal, and `AETHER_PROJECT_ROOT` override, unset-default and empty-value refusal are all
exercised through the shipped launcher.

## Combined pre-live evidence set

The pre-live gate for this objective is assembled from two revision-bound lanes:

1. **This unit (RC6-QUAL)** — the exact-version, isolated, mixed-version lifecycle qualification:
   defect reproductions with frozen readers/writers, the rc5 → candidate → rc5 → candidate cycle
   with compensation and interruption invariants, the legacy handoff and its refusals, the
   installed launch binding and the confinement witnesses. Receipts:
   `<receipts-root>/rc6qual-final/` (digests above).
2. **The observation lane (RC6-OBS / RC6-OBS-2)** — registration/hook behavior under a paused
   historical scanner, retained-index scale, and native/CLI parity; owned and evidence-bound by
   `specs/001-aether-v1-productization/evidence/RC6-OBS.md` and its qualification entry
   `scripts/qualify_observation.py` with its locked core-test node digest. Not duplicated here.

My part is lane 1; the observation scenarios (plan scenarios 4 and 5) are deliberately not
re-run by this entry. Aggregate gates, the tag and the live window remain RC6-INT / RC6-CLOSE.

## Disclosed findings (pre-existing, outside this unit's writable surface)

1. `scripts/release_bundle.py build` cannot pass its own handshake probe: the launcher probe binds
   a fixture repository and requires `home/tui`, which `_tui_checkout` (`release_bundle.py:1114-1149`)
   never creates, so the build refuses (`probe-failed: handshake probes failed: aether --project
   --json`). The tool is byte-identical to the contract base and belongs to the publication path,
   which this objective does not exercise; the refusal log is retained in the receipt.
2. The release lock the same tool writes records the maintained fork's *nearest* git-describe tag
   (here `v2026.8.13`), which the product's install/promotion validation refuses because a present
   tag must dereference to the locked commit. The accepted rc5 lock carries no such tag. Neither
   defect is on the authorized delivery path; a future owner-authorized publication objective owns
   their fix.
3. `aether reconcile --to active` cannot be reached through the shipped projected launcher: that
   launcher runs the release *runtime*, while the command's authority proof requires the executing
   interpreter to be the active release's *manager* environment, and `reconcile` is not among the
   commands the CLI redispatches into the active manager. The handoff repair itself is qualified
   here from the active release's own manager environment (receipt
   `scenarios/legacy.json`); the launcher-route refusal is recorded verbatim in the same receipt and
   is reported, not asserted green. Reported for the reconcile surface owner.

For any supplied `--bundle-dir` the entry records only unqualified corroboration (identity,
refusal log, digest inequality) and never treats it as a qualified bundle.

## Manifest lines for integration

Tracked non-`specs/` additions of this unit, as literal manifest lines for
`.github/workflows/policy.yml`:

```text
scripts/qualify_mixed_version_lifecycle.py
tests/fixtures/mixed-version/candidate-record.json
tests/fixtures/mixed-version/rc3-record.json
tests/fixtures/mixed-version/rc4-record.json
tests/fixtures/mixed-version/rc5-record.json
tests/test_mixed_version_lifecycle_qualification.py
```

The workflow's explicit `compileall`/`ruff check`/`ruff format --check` argument lists also
enumerate individual script paths; `scripts/qualify_mixed_version_lifecycle.py` must be added to
those three lines. `tests/test_mixed_version_lifecycle_qualification.py` is already covered by the
`tests` argument.

## Attribution

**Direct test evidence (this unit):** every row of the scenario table, the composed-revision
record, the installed-lane identity (copy verification, release ids, wheel/lock digests), the
launch measurements and the confinement witnesses.

**Reused evidence (unchanged artifact identity):** the observation lane's retained-corpus and
native-parity receipts (`RC6-OBS.md`, `scripts/qualify_observation.py` at the same composed
revision); the frozen predecessor releases' own authenticated artifacts from the read-only
installation (their identities re-verified here, not re-derived); the accepted maintained-fork
checkout identity (`aed6591a…`, tree `cc1ebf94…`).

**Not claimed:** qualified release bundle, aggregate release conclusion, integrated candidate
gates, tag, publication, activation or any live effect.

## Environment limits

* The disposable lane cannot materialize the Hermes-owned gateway unit (no D-Bus or `systemctl`
  effect is permitted), so `doctor` reports `SERVICE_PROJECTION_MISMATCH` in every isolated state;
  the lifecycle witnesses (active record, journal, profiles, projections, locked source) are
  asserted coherent and the diagnostic is disclosed rather than asserted green.
* Interruption offsets are wall-clock kills: which side of the commit point a run lands on varies.
  The recorded oracle is the atomic-outcome invariant (no pending half-state, no false success, a
  ready report must be fully coherent) plus a documented repair route, not a fixed winner.
* The published bundle wheel and the locally built promotion wheel are not byte-identical
  (independent `uv` builds); the artifact under test is the product-built promotion wheel whose
  digest the isolated store authenticated.
* The isolated Morfeo profile is a fixture: the launcher's documented toolsets are supplied to the
  disposable profile instead of relaxing the launcher check.
* Copying the frozen releases rather than rebuilding them keeps the exact predecessor bytes while
  the copies are executed only as their own code; the live rc3/rc4 trees are never modified and no
  live rc3/rc4 bootstrap or rollback is performed.

## Residual risk

* Live activation, the single provider-backed reply, gateway restart stability and the owner's
  real projections remain RC6-CLOSE's window; this lane proves the pre-live half only.
* The legacy boundary is qualified with rc4 as the *writer* and the candidate as the already
  activated self-authenticating target; older routes that cannot prove target integrity are
  reported as refusals, which is the documented disposition rather than a passed rollback.
* `doctor`'s aggregate readiness cannot be reached in a disposable lane by construction, so
  aggregate readiness statements rely on the live window.
