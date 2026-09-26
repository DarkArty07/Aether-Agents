# RC16-CUTOVER evidence — managed local cutover to RC16 and post-cutover coherence

## Context and boundaries

- **Unit:** `RC16-CUTOVER` (Supervisor, same-flow card)
- **Objective Contract:** `oc_c770cea3db51d97e@v2`
- **Material design:** `specs/issue-494-project-provenance/plan-release.md` §4
- **Predecessor:** Aether `1.0.0rc15`, release `1.0.0rc15-5dc9cd69da8d18f3`, Hermes
  `5b2b6ba543680c6fe8a62de4b467d1107be3abf4` / digest `adf77d5840028f490818a3f78304a9f3835bff176df3ad34255aea2f9882aba2`
- **Target:** Aether `1.0.0rc16` / `1.0.0-rc.16`, merge commit
  `d9e396462948ef3721612f6909371e22efb10115` (PR #524), local annotated tag
  `v1.0.0-rc.16`, Hermes `58f8c37a49b341f25b8fdd6310542fe932031b8d` / digest
  `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`
- **Result:** RC16 is selected and coherent; the transition succeeded with **exit 0**.
- **Explicit non-claims:** This document records the cutover and its post-cutover readback.
  It is not the installed-runtime #494 behaviour canary (that is a separate downstream lane),
  not publication, not a stable-release claim, and not agent-behaviour qualification.

## Why a durable launcher was required

The executing worker and the dispatcher both run inside `hermes-gateway-morfeo.service`, and
the supported managed update restarts that unit as its final projecting step. An in-cgroup
launch would therefore be killed mid-transition. The transition was launched as a transient
systemd user unit in its own cgroup, outside that subtree, with a phase receipt written after
every step so the outcome is readable after the restart.

## Non-mutating preview (recorded before any effect)

`aether update --local --dry-run --json` with the candidate checkout at the merged commit and
the maintained-fork checkout at the pinned commit returned `result: planned`, `changed: false`,
`blockers: []`, target `1.0.0rc16` / `1.0.0-rc.16`, current release `1.0.0rc15-5dc9cd69da8d18f3`,
the pinned fork commit and digest, HLP coverage `qualified` (HLP-428 among 32 required HLPs,
HLP-433 deferred/absent, `refusing_hlps: []`), and a service plan of
`immediate restart, no drain` on exactly the Aether-owned unit, with `unrelated_services: preserved`.

## The two launch attempts

| Attempt | Launcher form | Outcome |
| --- | --- | --- |
| 1 | transient systemd user unit, default unit environment | **refused before effect** — exit 4, `LOCAL_UPDATE_REFUSED: candidate environment tool is unavailable`, `changed: false` |
| 2 | same form, with the provisioned tool directory on `PATH` | **succeeded** — activation exit 0, `changed: true`, `active_version 1.0.0rc16` |

Attempt 1 was a defect of the *launch form*, not of the product: the supported activation
resolves its build tool by bare name, and a transient systemd unit inherits only the default
`PATH`, which omits the operator's provisioned tool directory. The product behaved correctly and
fail-closed: it refused **before** building or moving anything. Verified by hash comparison
against the pre-state, attempt 1 changed nothing — `active.json`, the RC15 `record.json` and
`release-lock.json`, and the service unit file were all byte-identical, the selector still named
the RC15 release, and the gateway unit kept its original PID and start time. Attempt 2 is the
same single cutover, correctly launched, not a second cutover, and the RC15 fallback remained
unused.

## Pre-state witnesses (captured immediately before effect)

| Witness | Value at pre-state |
| --- | --- |
| Active record hash | matches the RC15 record hash (single coherent release) |
| RC15 release record / lock | present, unchanged from installation |
| Selected release | RC15 `1.0.0rc15-5dc9cd69da8d18f3` |
| Manager / CLI identity | `1.0.0rc15` |
| Gateway unit | active, original PID and start time recorded |
| Unrelated unit exclusion | the unrelated Hestia gateway unit recorded as an explicit exclusion |
| Project registry | present and unchanged (hash recorded) |
| Board fingerprint | 97 boards, 567 tasks, 1503 comments, 2296 runs |
| Profiles | 3 role profiles |
| Pending transitions | recorded |

## Post-cutover coherence (step 5)

| Check | Observed |
| --- | --- |
| `aether doctor` | `result: ready`, `active_version: 1.0.0rc16`, no diagnostics, no errors, no warnings |
| Selected release | `1.0.0rc16-14fa64728b9aaeae` |
| Loaded Hermes source | commit `58f8c37a49b341f25b8fdd6310542fe932031b8d`, mode `maintained_fork`, version `0.20.1` |
| Installed source-tree digest | re-derived over the installed tree: `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144` — **equals the pin** |
| Release lock identity | package `1.0.0rc16`, display `1.0.0-rc.16`, tag `v1.0.0-rc.16`, Aether commit `d9e39646…`, fork commit/digest as above |
| Hooks | 22 expected / 22 registered / 0 remaining |
| Projections | no mismatches; integrity failures 0; quarantine 0 |
| Service | Aether-owned unit active with a **new PID (782228)** whose start time (`02:28:28`) is after the change |
| Interpreters | both provisioned interpreters resolve `aether_agents` 1.0.0rc16 and the adopted `hermes_cli`/`agent` modules from the new release tree |
| Transition journal | pending count 0 |
| Unrelated services | the unrelated Hestia gateway unit and the other user services remain active and untouched |

### Wheel digest note

The wheel installed by the cutover has a different file digest from the release bundle built by
the integration lane, because the two builds stamp different zip container metadata (the cutover
build uses a fixed reproducible epoch; the bundle tool stamps the commit time). This is not
content drift: both wheels contain the same 169 entries, and **every entry's bytes are
identical**. The release record binds the installed wheel digest and the cutover's own
`--aether-commit`/`--fork-commit` inputs.

## Preservation witnesses (pre-state vs post-state)

- The RC15 release record and release lock are byte-identical to the pre-state — the predecessor
  release, its published prerelease and its local tag remain immutable.
- The native project registry is unchanged; the three role profiles remain.
- Unrelated boards are untouched: total task count is unchanged (567) and the only board
  activity in the interval is this objective's own board (its own card comment and run rows),
  which is expected control-plane activity, not collateral change.
- The unrelated Hestia gateway unit and the other user services remain active.
- The project's own unrelated dirty working-tree file remains preserved.
- No release tag was pushed, no package was published, no deployment was dispatched, and no
  credential/provider/router binding was changed.

## Fallback

The single prequalified RC15 rollback was **not used**: the transition succeeded on its first
effective attempt, so no fallback receipt exists. RC15 remains installed and selectable as the
coherent predecessor.

## Limits

- This lane proves the selected runtime identity and coherence. It does not prove the #494
  Project/review behaviour on the installed runtime; that is the separate canary lane's
  obligation.
- The cutover restarted the Aether-owned gateway unit once, as designed. The unrelated units
  were not restarted or signalled.
- Receipts for this lane are private and durable in the objective's own state area; the launch
  form, the phase receipt path, and the observed envelopes are recorded above in portable form.
