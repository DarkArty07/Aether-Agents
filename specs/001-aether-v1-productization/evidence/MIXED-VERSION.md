# Mixed-version lifecycle qualification (RC6-QUAL)

**Unit:** RC6-QUAL (Implementer) — Objective Contract `oc_b5926701207812e8@v1`
(SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`) on base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`.

**Status:** direct qualification evidence for D2 / AC-3 and the pre-live half of AC-7, produced
against the recomposed candidate revision on a disposable, isolated installation. This is unit-level
evidence: integrated verification, the local-only annotated tag, and the live activation belong to
RC6-INT and RC6-CLOSE.

**Entry point:** `scripts/qualify_mixed_version_lifecycle.py` (new; pytest contract in
`tests/test_mixed_version_lifecycle_qualification.py`, frozen predecessor record fixtures and real
launch-frame fixtures in `tests/fixtures/mixed-version/`). The entry derives every destination from
`--work-root`, refuses any destination that could overlap the operator installation or the read-only
source store, and runs without the live installation.

```
uv run --frozen python scripts/qualify_mixed_version_lifecycle.py run \
    --repo <clean checkout at the candidate revision> \
    --candidate-commit <composed revision> \
    --fork-checkout <maintained-fork checkout at aed6591a69f453a1867b73628603e7b53ba40ffc> \
    --source-store <read-only installation with the rc3/rc4/rc5 releases> \
    [--bundle-dir <release-bundle directory>]   # unqualified corroboration only, see Findings
    --work-root <disposable work root> \
    --receipts-root <durable private receipts root> \
    --run-id rc6qual-final6 \
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
| RC6-LAUNCH-2 | `4668a6ac5f5d1e19b20194c71a997d3bca5f5e1a` |
| RC6-LAUNCH-4 | `9749dda6446e854198d1d21e52f801c834ea46d7` |

Merge order on the contract base `d2874c2f3fc839a82fbaa96ece6edebab3856298`:
RC6-LIFE → RC6-OBS → RC6-LAUNCH → RC6-OBS-2 → RC6-DOCS → RC6-LIFE-2 → RC6-LAUNCH-2 → RC6-LAUNCH-4
(the RC6-LAUNCH-4 chain carries the LAUNCH-3 commits). Every unit-authored blob in the composition is
byte-identical to its reviewed tip, and every recorded head is an ancestor of the composition commit.
Recomposed commit `114bcc8dde4142a51b60ddfb69b81ec122f46667`, tree
`282d5fe67f36e582de2572ae85d881d05d7808f3`, `VERSION` `1.0.0rc6`.

The recorded **tree** is what RC6-INT must reproduce: replaying the eight heads in the recorded order
onto `d2874c2f` in a scratch worktree yields exactly `282d5fe67f36e582de2572ae85d881d05d7808f3`
(the reproduction was executed for this record; the intermediate merge commits carry different
hashes because a replay is a new commit, while the resulting tree is identical).

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
* candidate `1.0.0rc6-fbdf996193b29625` — built from the recomposed revision by the product's own
  local-candidate builder and promoted into the same store **by the rc5 manager** (the
  mixed-version hop), then rolled back and re-activated; the launch binds
  `<store>/releases/1.0.0rc6-fbdf996193b29625/{runtime,tui}`.

## Scenario → command → result

| Scenario | Representative command (generic paths) | Observed | Assertions | Receipt (private) |
| --- | --- | --- | --- | --- |
| prepare | `aether setup --wheel <rc5 wheel> --hermes-checkout <fork> --release-lock <rc5 lock> --yes --json`; release-copy verification | exact rc5 active, selector inside the isolated store, copies byte-identical | 3 | `run.json` `7fbc4035…` |
| cycle | `aether update --wheel <promotion wheel> --release-lock <promotion lock> --yes`; `aether rollback --yes`; `aether update 1.0.0rc6 --yes`; blocked-projection transition; three SIGKILL interruptions; rollback repair | rc5 → candidate → rc5 → candidate, pointer byte-exact against each target's own record, no false success, no pending half-state | 34 | `scenarios/cycle.json` `d33d5c47…` |
| frozen-readers | frozen rc3 interpreter: `ReleaseRecord.from_json` on the post-rc4 pointer, the null-field variant, the corrected writer's pointer and its own record | rc3 reader rejects the post-rc4 shape (with a real value **and** with `null`), accepts its own generation and accepts the corrected writer's target-owned record | 10 | `scenarios/frozen-readers.json` `baad8b15…` |
| frozen-writer | frozen rc4 interpreter planning projections for a successor record; corrected source asking each target for its own plan | rc4 brands a successor with the legacy `hermes.desktop` shape; each target answers for its own identity with branded bytes | 5 | `scenarios/frozen-writer.json` `5405bb60…` |
| legacy | rc4 writer applying projections; direct non-manager execution refusal (`RECONCILE_REFUSED`, exit 4); projected launcher route dispatches to active manager (exit 0 `planned`); release runtime dispatches to active manager (exit 0 `planned`); manager preview (exit 0 `planned`); apply via projected launcher (exit 0 `changed`, `projections_reconciled: 1`); post-apply idempotency (exit 0 `no_change`); unsupported modes refused (`--to installed` and missing `--to`, exit 3); unprovable-target refusal | direct non-manager execution refuses before mutation; projected launcher and release runtime dispatch to active manager; preview non-mutating; apply finishes the handoff (`projections_reconciled: 1`, zero mismatches) without record edits; post-apply reports `no_change`; unsupported modes refused before bootstrap; unprovable target refused before mutation | 19 | `scenarios/legacy.json` `c2696c42…` |
| launch | packaged selector `aether --project <project> [--resume latest] --check --json` in clean and contaminated environments; fresh, `--resume latest` and held-construction PTY launches; dependency-closure probes against the manager and target-runtime interpreters | exact target backend/TUI/project/Morfeo profile bound; stale `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, session selectors and hostile `TERMINAL_CWD`/`MESSAGING_CWD` neither used nor forwarded; every launch reaches the runtime's post-build session information against a seeded corpus (see the measurement table); the pre-construction frame never satisfies the measurement; the held-construction control stays false while the isolated gateway is stopped; the session's own root is the isolated project; release tree unchanged; manager closure carries only the wheel-declared `jsonschema`, target runtime carries the locked `pyyaml` | 32 | `scenarios/launch.json` `8269c2fb…` |
| docs | repository `check_documentation.py`, usage/documentation pytest modules, manifest oracle on `test_public_artifacts.py`, installed `version --json` | documentation checks clean; usage/documentation modules pass; the manifest oracle passes **at this composed candidate**, which does not yet contain this unit's files (integration must apply the lines below); the installed CLI reports `1.0.0rc6` | 3 | `scenarios/docs.json` `f1fd28ae…` |
| isolation | guard refusal subprocess, split-root and transport-leak checks, live witnesses, service boundary | live work root refused with exit 2; no operator root, board variable, D-Bus socket or credential inherited; live unit/pointer/selector/operator config unchanged; disabled service controller | 7 | `scenarios/isolation.json` `7a25585b…` |

Run-level facts: exit `0`, 113 assertions, 64 recorded commands, elapsed 329 202 ms, environment
identity `f7da6d5740b0f60b5ad1d853f26edfccedeb172c4c08da2d1dfb5fe4c42b4842` (`SUMMARY.txt`
`1023f721…`).
Every scenario ran fresh in this single decisive invocation (`reused scenarios: none`, no receipt
carried over from an earlier harness revision); every receipt records its producing harness SHA-256
`e0d4f62c5e120458286ae1305cf93cd7954c4eb9101eef0c57e7c799beebc100`, argv, cwd, exit status, timing,
stdout/stderr digests and the isolation-relevant environment digest. That digest is the committed
revision of the entry: commit `4bb76f377a9a474831d36b3fb6d8fa02e50d6f38` on the task branch, and no
harness code changed after the decisive run.

## Installed launch measurement

| Quantity | Value |
| --- | --- |
| Launch path | packaged selector → the release's own launcher → release runtime (`hermes --tui --in <project>`) |
| Bound backend | `<store>/releases/1.0.0rc6-fbdf996193b29625/runtime/bin/python` and `…/runtime/bin/hermes` |
| Bound profile / project | `<store>/state/aether/hermes/profiles/morfeo`, the isolated managed project |
| Access kind | `isolated_stub_provider_fixture` (disposable non-sending stub in Morfeo profile `config.yaml`; no operator credentials copied, no external network requests) |
| Fresh PTY launch (contaminated env) | first output 332 ms, composer visible 1112 ms, active-session file 2796 ms, observation journal 3076 ms; **agent constructed 5307 ms** (signal `post_build_session_info_banner`) |
| Resume PTY launch (`--resume latest`) | first output 346 ms, composer visible 1114 ms, active-session file 2299 ms, observation journal 101 ms; **agent constructed 3691 ms** (same signal) |
| Held-construction control launch | pre-construction frame at 2411 ms (prompt painted, lazy counts, measurement false); the isolated gateway child was stopped with `SIGSTOP` for 3000 ms and the measurement stayed false; released, then **agent constructed 6932 ms** |
| Corpus identity/scale at launch | pre-seeded in the isolated store and recorded per launch: fresh 2 segments / 25 events / `99cd9908…`, resume 3 / 25 / `1f9e8025…`, held control 4 / 25 / `667e3c6b…` |
| Session root | each launch's own reported root is the isolated project (`…ual-final6-work/project`), including the fresh launch under hostile `TERMINAL_CWD`/`MESSAGING_CWD` |
| Dependency closures | manager `Declared: jsonschema==4.26.0`, no YAML interpreter (`yaml_available: false`); target runtime carries locked `pyyaml` `6.0.3`; the launcher and the TUI it starts run under the **target runtime** closure |
| Release tree after launch | unchanged for all three launches (`tui` tree digest and `release.json` `tui_sha256` identical before/after) |
| Locked source digest | `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` unchanged |
| Readiness boundary | this pre-live lane does **not** claim provider-backed agent readiness or a successful provider turn; the idle `✓` title, prompt visibility, active-session file and observation journal are supporting observations only |

### What the measured signal is, and why it cannot precede construction

The measurement is read from the **painted screen**, reconstructed by the entry's terminal model
(`TerminalScreen`), never from the concatenated stream. The shipped TUI renders through Ink, which
repaints by rewriting only the cells that changed and moving the cursor over the rest: the real
capture carries ``39 t`` + cursor-forward + ``ols`` for a painted ``39 tools``, so a
strip-and-search reader loses characters that the terminal kept from an earlier frame. That is the
defect the previous revision of this oracle had (its receipts never saw the hydrated banner); the
real repaint bytes are pinned as fixtures and the regression is asserted in the pytest module.

The signal is source-bound in the frozen fork:

* `tui_gateway/methods_session.py` returns the lightweight `session.create` response immediately with
  `"tools": {}`, `"skills": {}`, `"lazy": true` and no `version`, and schedules the deferred build;
  `ui-tui/src/app/useSessionLifecycle.ts` therefore paints `status: 'starting agent…'` and
  `ui-tui/src/components/branding.tsx` paints those empty counts as ``… tools · … skills``. The idle
  `✓` window title and the active-session file are written from that same lazy response and can
  precede construction.
* The deferred build (`tui_gateway/server.py`, `_start_agent_build`) constructs the real agent and only
  then computes `info = _session_info(agent, current)` and emits `session.info`. `_session_info` fills
  `tools` from `getattr(agent, "tools", [])` and `skills` from `get_available_skills()` **only when an
  agent exists**; the lazy response can never carry counts. `createGatewayEventHandler.ts` maps that
  post-build `session.info` to `status: 'ready'`.

So a painted numeric ``N tools · M skills`` banner with the runtime's `ready` status means the
runtime's own deferred agent construction completed. It requires no provider turn, and this lane
therefore names it "agent constructed" rather than "agent ready".

Two negative controls are part of the decisive receipt:

1. **Same-run pre-construction frame.** As soon as the lazy banner is painted, the entry snapshots
   the screen and asserts the measurement is false while the prompt is already visible. Observed for
   fresh (2813 ms), resume (2311 ms) and the held-control launch (2411 ms): `prompt_visible: true`,
   `construction_detected: false`, each strictly before its measurement.
2. **Held construction (real runtime, not a fixture).** A third real launch stops the isolated
   gateway child with `SIGSTOP` once the prompt is painted and the deferred build is unfinished,
   verifies the measurement stays false for 3000 ms, then resumes it with `SIGCONT`. The receipt
   records the stopped processes with their command lines (all inside the disposable store,
   `…/releases/1.0.0rc6-fbdf996193b29625/runtime/bin/python -m tui_gateway.entry`) and the launch only
   completes afterwards (6932 ms). The pytest module additionally pins the synthetic paused frame
   (prompt + idle `✓` title + skeleton rows) and both real frames.

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
   binding with the runtime's own post-build session information (not provider-backed agent
   readiness) plus its real negative controls, and the confinement witnesses. Receipts:
   `<receipts-root>/rc6qual-final6/` (digests above).
2. **The observation lane (RC6-OBS / RC6-OBS-2)** — registration/hook behavior under a paused
   historical scanner, retained-index scale, and native/CLI parity; owned and evidence-bound by
   `specs/001-aether-v1-productization/evidence/RC6-OBS.md` and its qualification entry
   `scripts/qualify_observation.py` with its locked core-test node digest. Not duplicated here.

My part is lane 1; the observation scenarios (plan scenarios 4 and 5) are deliberately not
re-run by this entry. Aggregate gates, the tag and the live window remain RC6-INT / RC6-CLOSE.

## Direct-versus-reused attribution

**Direct test evidence (this unit):** every row of the scenario table above ran in the single
decisive invocation (`reused scenarios: none`, 113 assertions, elapsed 329 202 ms), including the
painted-screen launch measurement, its two negative controls, the dependency-closure probes and the
confinement witnesses.

**Reused evidence (unchanged artifact identity):** the observation lane's retained-corpus and
native-parity receipts (`RC6-OBS.md`, `scripts/qualify_observation.py` at the candidate
revision); the frozen predecessor releases' own authenticated artifacts from the read-only
installation (their identities re-verified here, not re-derived); the accepted maintained-fork
checkout identity (`aed6591a…`, tree `cc1ebf94…`). No scenario row was carried over from an earlier
invocation.

**Not claimed:** qualified release bundle, aggregate release conclusion, integrated candidate
gates, tag, publication, activation or any live effect.

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
   their fix. The supplied `--bundle-dir` is recorded only as unqualified corroboration: its lock
   names the earlier composition `3dbde1e4`, its wheel `504cdba1…` is not the promoted/installed
   `fbdf9961…`, and no qualified bundle is implied.
3. `aether reconcile --to active` is fully reachable through the projected launcher and release
   runtime entry points in the candidate, as routed by RC6-LIFE-2 and verified in `scenario_legacy`
   (exit 0 `planned`, `manager_version: 1.0.0rc6`, applied `changed` with `projections_reconciled: 1`,
   and post-apply `no_change`). Direct non-manager execution continues to refuse before mutation
   (exit 4 `RECONCILE_REFUSED`), which is verified as the historical and boundary reproduction.
4. Inherited modern cwd selectors (`TERMINAL_CWD`, `MESSAGING_CWD`) steering the fresh session root
   (routed to RC6-LAUNCH-2 `t_b0975e1c`): the launcher previously scrubbed `HERMES_CWD` but omitted
   the modern `TERMINAL_CWD` and `MESSAGING_CWD` variables that the runtime reads as the workspace
   and terminal cwd. As a result, an ambient cwd selector steered the launched session's own root
   despite `--project` resolution. The earlier fresh-launch receipt witnessed the `--project`
   resolution in the activation report but did not witness the runtime's own reported session root
   (which carried the ambient caller worktree in the OSC window title). The recomposed candidate
   incorporates the scrub fix from RC6-LAUNCH-2, and `scenario_launch` now asserts that the fresh
   session's own root equals the isolated project despite hostile `TERMINAL_CWD`/`MESSAGING_CWD` in
   the parent environment. The same contamination is what makes the earlier failure visible at all:
   when a launch fell back to the rc5 launcher (which has no scrub fix) the TUI could not start its
   gateway and painted `gateway exited`; the candidate binds the exact target instead.
5. Launch process residue observation: each PTY launch in the disposable lane leaves a detached
   `tui_gateway` child process after the interactive TUI is terminated. The qualification harness now
   terminates these processes during lane cleanup (resuming a held process first) and records the
   observation for the pre-live witness record and final residue report (owned by RC6-CLOSE).
6. Corrected within this unit's own surface (harness, not product): the previous revision's launch
   oracle stripped terminal control sequences and searched the concatenated stream, which cannot
   recover Ink's incremental repaints. The receipts it produced recorded a rendered title glyph as
   readiness, which the reviewer and the design steward correctly rejected: the title fires from the
   lazy response, before construction. The current oracle reads the painted screen, is source-bound
   to the post-build `session.info`, and carries the two negative controls above.

## Manifest lines for integration

Tracked non-`specs/` additions of this unit, as literal manifest lines for
`.github/workflows/policy.yml`:

```text
scripts/qualify_mixed_version_lifecycle.py
tests/fixtures/mixed-version/candidate-record.json
tests/fixtures/mixed-version/launch-ink-hydrated-frame.bin
tests/fixtures/mixed-version/launch-ink-lazy-frame.bin
tests/fixtures/mixed-version/rc3-record.json
tests/fixtures/mixed-version/rc4-record.json
tests/fixtures/mixed-version/rc5-record.json
tests/test_mixed_version_lifecycle_qualification.py
```

The workflow's explicit `compileall`/`ruff check`/`ruff format --check` argument lists also
enumerate individual script paths; `scripts/qualify_mixed_version_lifecycle.py` must be added to
those three lines. `tests/test_mixed_version_lifecycle_qualification.py` is already covered by the
`tests` argument. The manifest oracle passes at the composed candidate revision only because these
paths are not yet present there; on this branch it fails precisely on them, which is the expected
pre-integration state.

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
* The launch measurement is taken from the shipped TUI's own painted frame for the runtime's
  post-build session information; it is a real runtime measurement against a real installed release,
  but it does not include a provider turn, so it is deliberately not named "agent ready". The
  held-construction control stops only the isolated store's gateway child and resumes it, and it is
  recorded as an explicit test controller.

## Residual risk

* Live activation, the single provider-backed reply, gateway restart stability and the owner's
  real projections remain RC6-CLOSE's window; this lane proves the pre-live half only.
* The legacy boundary is qualified with rc4 as the *writer* and the candidate as the already
  activated self-authenticating target; older routes that cannot prove target integrity are
  reported as refusals, which is the documented disposition rather than a passed rollback.
* `doctor`'s aggregate readiness cannot be reached in a disposable lane by construction, so
  aggregate readiness statements rely on the live window.
* The launch measurement's absolute value depends on the host and on the seeded corpus; the receipt
  carries the corpus identity/scale and the per-launch signal timeline, and no universal latency
  threshold is claimed.
