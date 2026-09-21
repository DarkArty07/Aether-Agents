# Mixed-version lifecycle qualification (RC6-QUAL)

**Unit:** RC6-QUAL (Implementer) — Objective Contract `oc_b5926701207812e8@v1`
(SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`) on base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`.

**Status:** direct qualification evidence for D2 / AC-3 and the pre-live half of AC-7, produced
against the recomposed candidate revision on a disposable, isolated installation. This is unit-level
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
    --run-id rc6qual-final \
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
| RC6-LIFE-2 | `6941594ee4e2c09a463181e6a64376cdd28151b7` |

Merge order RC6-LIFE → RC6-OBS → RC6-LAUNCH → RC6-OBS-2 → RC6-DOCS → RC6-LIFE-2 on the contract base;
every unit-authored blob in the composition is byte-identical to its reviewed tip. Recomposed commit
`f59900a99837d6efefc7bc3140e89fa287f18b4f`, tree
`90eff5151e9f8cfd3bbcc3d15287f0ba2446c7c5`, `VERSION` `1.0.0rc6`. The composition is reproducible
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
* candidate `1.0.0rc6-c8ac4dd255ed4a64` — built from the recomposed revision by the product's own
  local-candidate builder and promoted into the same store **by the rc5 manager** (the
  mixed-version hop), then rolled back and re-activated.

## Scenario → command → result

| Scenario | Representative command (generic paths) | Observed | Assertions | Receipt (private) |
| --- | --- | --- | --- | --- |
| prepare | `aether setup --wheel <rc5 wheel> --hermes-checkout <fork> --release-lock <rc5 lock> --yes --json`; release-copy verification | exact rc5 active, selector inside the isolated store, copies byte-identical | 3 | `run.json` `664eeb09…` |
| cycle | `aether update --wheel <promotion wheel> --release-lock <promotion lock> --yes`; `aether rollback --yes`; `aether update 1.0.0rc6 --yes`; blocked-projection transition; three SIGKILL interruptions; rollback repair | rc5 → candidate → rc5 → candidate, pointer byte-exact against each target's own record, no false success, no pending half-state | 34 | `scenarios/cycle.json` `eb61c8ce…` |
| frozen-readers | frozen rc3 interpreter: `ReleaseRecord.from_json` on the post-rc4 pointer, the null-field variant, the corrected writer's pointer and its own record | rc3 reader rejects the post-rc4 shape (with a real value **and** with `null`), accepts its own generation and accepts the corrected writer's target-owned record | 10 | `scenarios/frozen-readers.json` `ab2a0cca…` |
| frozen-writer | frozen rc4 interpreter planning projections for a successor record; corrected source asking each target for its own plan | rc4 brands a successor with the legacy `hermes.desktop` shape; each target answers for its own identity with branded bytes | 5 | `scenarios/frozen-writer.json` `5612a3dd…` |
| legacy | rc4 writer applying projections; direct non-manager execution refusal (`RECONCILE_REFUSED`, exit 4); projected launcher route dispatches to active manager (exit 0 `planned`); release runtime dispatches to active manager (exit 0 `planned`); manager preview (exit 0 `planned`); apply via projected launcher (exit 0 `changed`, `projections_reconciled: 1`); post-apply idempotency (exit 0 `no_change`); unsupported modes refused (`--to installed` and missing `--to`, exit 3); unprovable-target refusal | direct non-manager execution refuses before mutation; projected launcher and release runtime dispatch to active manager; preview non-mutating; apply finishes the handoff (`projections_reconciled: 1`, zero mismatches) without record edits; post-apply reports `no_change`; unsupported modes refused before bootstrap; unprovable target refused before mutation | 19 | `scenarios/legacy.json` `080024e6…` |
| launch | packaged selector `aether --project <project> [--resume latest] --check --json` in clean and contaminated environments; fresh and resume PTY launches | exact target backend/TUI/project/Morfeo profile bound; stale `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, session selectors neither used nor forwarded; fresh and resume reach interactive agent prompt readiness against seeded corpus; release tree unchanged | 20 | `scenarios/launch.json` `9a24a566…` |
| docs | repository `check_documentation.py`, usage/documentation pytest modules, manifest oracle on `test_public_artifacts.py` | documentation checks clean; test modules pass; manifest oracle records expected absence | 3 | `scenarios/docs.json` `dc8e3582…` |
| isolation | guard refusal subprocess, split-root and transport-leak checks, live witnesses, service boundary | live work root refused with exit 2; no operator root, board variable, D-Bus socket or credential inherited; live unit/pointer/selector/operator config unchanged; disabled service controller | 7 | `scenarios/isolation.json` `dc35d844…` |

Run-level facts: exit `0`, 101 assertions, 61 recorded commands, elapsed 322 382 ms, environment identity `8ae12e16…`.
Every scenario ran fresh in this single decisive invocation (`reused scenarios: none`); every receipt records
its producing harness SHA-256 (`0df3c90980d11504eca458d24c7e643a836c9867cae88dd86ae8a719bde6f30d`), argv,
cwd, exit status, timing, stdout/stderr digests and the isolation-relevant environment digest.

## Installed launch measurement

| Quantity | Value |
| --- | --- |
| Launch path | packaged selector → `runtime/current/venv/bin/aether` → release runtime (`hermes --tui --in <project>`) |
| Bound backend | `<store>/releases/1.0.0rc6-c8ac4dd255ed4a64/runtime/bin/python` and `…/runtime/bin/hermes` |
| Bound profile / project | `<store>/state/aether/hermes/profiles/morfeo`, the isolated managed project |
| Access kind | `isolated_stub_provider_fixture` (disposable non-sending stub in Morfeo profile `config.yaml`; no operator credentials copied, no external network requests) |
| Fresh PTY launch (contaminated env) | first output 266 ms, composer visible 995 ms, **agent prompt ready 3421 ms** (signal `window_title_ready_glyph`, active session file 3421 ms) |
| Resume PTY launch (`--resume latest`) | first output 273 ms, composer visible 1012 ms, **agent prompt ready 2085 ms** (signal `window_title_ready_glyph`, active session file 2085 ms) |
| Corpus identity/scale at launch | segments 2, events 25, digest `da9094937c8f01b7ae13b6f41f754a9ece7ae3131a0ab0a3996a8b3ec3716355` (pre-seeded in isolated store) |
| Release tree after launch | unchanged (`tui` tree digest and `release.json` `tui_sha256` identical before/after for both launches) |
| Locked source digest | `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` unchanged |
| Agent-ready verification | **reached and verified in this lane**: the candidate runtime and TUI package fully initialize under the isolated non-sending provider fixture; both fresh and resume launches reach interactive prompt readiness (`❯ Try ...` with terminal title set to `✓ stub-non-sending` and session active file written). Negative unit tests verify that a visible prompt with paused construction does NOT pass. The single live provider completion belongs to RC6-CLOSE. |

No npm/build step runs at launch (the release tree is witnessed unchanged), and neither the
project nor the profile is guessed: two projects in the registry produce a visible ambiguity
refusal, and `AETHER_PROJECT_ROOT` override, unset-default and empty-value refusal are all
exercised through the shipped launcher.

## Combined pre-live evidence set

The pre-live gate for this objective is assembled from two revision-bound lanes:

1. **This unit (RC6-QUAL)** — the exact-version, isolated, mixed-version lifecycle qualification:
   defect reproductions with frozen readers/writers, the rc5 → candidate → rc5 → candidate cycle
   with compensation and interruption invariants, the legacy handoff and its refusals, the
   reconcile entry-point matrix across projected launcher and release runtime, the installed launch
   binding with real agent readiness, and the confinement witnesses. Receipts:
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
3. `aether reconcile --to active` is fully reachable through the projected launcher and release
   runtime entry points in the candidate, as routed by RC6-LIFE-2 and verified in `scenario_legacy`
   (exit 0 `planned`, `manager_version: 1.0.0rc6`, applied `changed` with `projections_reconciled: 1`,
   and post-apply `no_change`). Direct non-manager execution continues to refuse before mutation
   (exit 4 `RECONCILE_REFUSED`), which is verified as the historical and boundary reproduction.

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

**Direct test evidence (this unit):** ALL 8 rows of the scenario table in the decisive single-invocation
run (`reused scenarios: none`, elapsed 322 382 ms, 101 assertions), the recomposed candidate revision
record (`f59900a9` / tree `90eff515`), the installed-lane identity (`1.0.0rc6-c8ac4dd255ed4a64`, wheel
`c8ac4dd2…`), the launch measurements (fresh 3421 ms, resume 2085 ms against seeded corpus, title `✓`),
and the confinement witnesses.

**Reused evidence (unchanged artifact identity):** the observation lane's retained-corpus and
native-parity receipts (`RC6-OBS.md`, `scripts/qualify_observation.py` at the candidate
revision); the frozen predecessor releases' own authenticated artifacts from the read-only
installation (their identities re-verified here, not re-derived); the accepted maintained-fork
checkout identity (`aed6591a…`, tree `cc1ebf94…`). No scenario rows were carried over from earlier
invocations (`reused: none`).

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
