# Telegram Monitor

The Telegram Monitor is a principal Aether capability for long-horizon work: once per
hour it collects bounded evidence from explicitly project-bound Aether work and has
Morfeo narrate it into the already configured Telegram conversation. It is an observer:
it never advances a task, accepts a milestone, repairs a blocker or changes an Objective
Contract.

This guide describes the behavior implemented in this build and the limits of its
current qualification. The owning requirements, decisions and acceptance criteria are
in [`specs/telegram-monitor/spec.md`](../../specs/telegram-monitor/spec.md); the selected
technical design is in [`plan.md`](../../specs/telegram-monitor/plan.md).

## What is implemented

- **One native hourly job per installation.** `aether monitor on` creates or reuses
  exactly one native Hermes job owned by the monitor, with schedule `0 * * * *`, the
  packaged pre-check script, the dedicated reporting toolset and `deliver=local`. The
  job's persisted identifier — not a job name — is the runtime authority.
- **Hourly wall-clock cuts.** Cutoffs use the installation's configured IANA timezone,
  including DST folds, and every record carries UTC plus an explicit local offset. A late
  tick resolves to the wall-clock hour it belongs to; missed hours are visible rather than
  invented.
- **Read-only multi-project sources.** The collector enumerates exactly registered,
  marker-verified Aether projects and their bound execution work (open tasks, task runs,
  task events, review/wait/block states, finalized contracts, direct project-bound turns).
  Every source database is opened `mode=ro` with `query_only` asserted; the monitor never
  creates, migrates or rewrites source state.
- **Bounded Morfeo narration.** The model receives one canonical snapshot (24,000
  characters maximum, deterministic ordering) and returns one fixed JSON narrative with
  evidence references. Identity, time headers, provenance labels and message splitting are
  renderer-owned; the model cannot choose the recipient, the identity or the schedule.
  Splitting into Telegram parts never calls the model again. At most one narration is
  attempted per enabled digest.
- **Truthful delivery outcomes.** Parts are sent through the existing native Telegram
  sender to the destination pinned at `on`. Only an explicit successful Bot API response
  with a message identifier is `confirmed`; a post-dispatch timeout or empty result is
  `uncertain`; a known pre-dispatch failure is retried at most three times per part per
  reporting tick. Coverage advances only when every covering part is confirmed.
- **Honest idle.** A genuine idle tick prints the native `{"wakeAgent": false}` gate before
  any inference, so no model call happens. Source failure, a drifted runtime, an
  unfinished report or an unreported final outcome wake instead of looking idle.
- **Durable history.** Snapshots, narratives and per-part delivery outcomes are retained
  for thirty days after resolution. Pending, uncertain and active attribution are never
  purged; source databases are never touched by retention.

## Control surface

```bash
aether monitor status    [--json]
aether monitor on        [--json]
aether monitor off       [--json]
aether monitor history   [--limit N] [--json]
```

Every action emits one JSON envelope:

```json
{
  "schema_version": "aether.telegram-monitor.v1",
  "ok": true,
  "action": "status",
  "result": { "enabled": true, "next_cut_utc": "...", "coverage_gaps": [], "..." : "..." }
}
```

Failures use the same envelope with `"ok": false` and a bounded
`error: {code, message}` object instead of `result`. No action accepts a token,
destination, provider or model argument: the destination and the model route are
resolved from the existing installation configuration.

`status` reports the enabled state, the owned native job, the next cut in UTC and in the
effective zone, the coverage gaps, the last report (including per-part delivery states)
and the aggregate delivery outcomes. `history` returns bounded interval records
(`report_id`, cutoff, collection and resolution times, narrative status, per-part states
and coverage gaps) without source content. `on` validates the provisioned Morfeo runtime
and the existing Telegram destination, installs or reuses the owned job, pins the
destination as an opaque reference and then enables the monitor. `off` persists the
disabled state *before* pausing the owned job, so a racing pre-check or send stops.

The same four actions and the same `--limit` bound are exposed to ordinary Morfeo
sessions through the native `aether_monitor` control tool. Both entry points go through
one service, so the JSON envelope cannot drift between them. Monitor/report runs cannot
control the monitor: a cron session receives `MONITOR_RUN_CONTROL_REFUSED`.

`aether monitor --help`, `aether --version`, `status` and `history` do not import the
managed Hermes runtime. When the manager interpreter lacks Hermes, `on`/`off` run through
a validated product-runtime subprocess (`AETHER_HERMES_PYTHON`, otherwise a `hermes`
sibling interpreter, otherwise the manager interpreter; each candidate must pass an
interface probe) and report `RUNTIME_UNAVAILABLE` without changing state when no
candidate qualifies. `AETHER_HERMES_PYTHON` is private operational context, never a
version-controlled default.

## Reporter toolset

The monitor plugin registers exactly two tools and is enabled only by the portable
Morfeo profile opt-in:

| Tool | Toolset | Available to |
| --- | --- | --- |
| `aether_monitor` | `aether_monitor` | ordinary Morfeo sessions |
| `aether_monitor_report_snapshot` | `aether_monitor_reporting` | only the monitor's own hourly run |

The hourly job carries `enabled_toolsets=["aether_monitor_reporting", "no_mcp"]`. The
dedicated toolset restricts the reporter surface to that one read tool, and the supported
`no_mcp` sentinel keeps the native scheduler from default-expanding the per-job list with
provisioned MCP servers, so terminal, file, messaging, board lifecycle, delegation, cron
and control tools are absent from narration. The snapshot read claims the report's private
handoff, so every other session — including a second cron session of the same job — is
refused.

## State, privacy and retention

All monitor state lives in the private Aether state root at `monitor/monitor.sqlite3`
(directory mode `0700`, database and sidecars `0600`). It contains the settings singleton
(enabled flag, exact native job identifier and profile binding, opaque destination
reference, timezone, last cutoff), work enrollment, immutable snapshots, validated
narratives, per-part delivery records and short transactional leases.

- The store persists monitor content, not the conversation: the canonical snapshot
  payload, the validated narrative structure the narrator returned (per-claim text with
  its source references, provenance and status, bounded at 24,000 characters), the
  narrator session identifier and attempt status, and per-part delivery records (outcome,
  attempt count, the accepted Bot API message identifier and a hash of the delivered
  text). Telegram message text is not persisted — only its per-part hash — and no
  credential, chat identifier, raw transcript, tool argument or result, or provider
  binding is persisted or printed. The destination is stored as an opaque digest of the
  pinned target.
- Snapshot construction selects only bounded, allowlisted fields (task titles, bounded
  run summaries, acceptance metadata, known diagnostic codes and selectively redacted
  outcome excerpts) and applies the existing privacy patterns before anything reaches the
  model or the database. Prose items are capped at 600 characters, source excerpts at
  1,200 characters and the model snapshot at 24,000 characters.
- Every narrative claim carries a source reference, provenance (`observed`/`reported`) and
  status (`verified`/`unverified`/`unknown`). A model status must match the canonical
  observed state; references cannot be upgraded by prose.
- Source databases (SessionDB, execution boards, observation projections) are read-only
  from the monitor's perspective and are never migrated, written or purged.

## Failure behavior

| Condition | Observed behavior |
| --- | --- |
| Missing, invalid or changed Telegram destination | `DESTINATION_MISSING` / `DESTINATION_INVALID` / `DESTINATION_CHANGED`; no job, pin or state change, no credential request, no fallback recipient |
| Foreign or missing Morfeo identity | `RUNTIME_MISMATCH` before any pin, job or state mutation |
| Native job replaced, duplicated, unreadable or not updated | `JOB_CONFLICT` / `JOB_OPERATION_FAILED`; the foreign record is never paused, resumed or adopted |
| Source collection failure or a drifted runtime | observable wake (`{"wakeAgent": true}`), never idle |
| Narration failed or rejected | persisted `failed`/`rejected` plus one labeled service notice per report cut; the report never becomes official narrative and progress is not marked covered |
| Post-dispatch ambiguity (timeout, empty, crash) | durable `uncertain`; visible in status/history; never replayed blindly |
| Process death between claim and receipt | the expired lease is recovered and the delivery becomes `uncertain`; the next pre-check re-surfaces the report |
| Manual `off` | durable before the native pause; racing pre-checks and sends stop |

Service notices are explicitly labeled and are not progress coverage. Telegram Bot API
acceptance is recorded as acceptance only; it is not proof that a human read a message.
No exactly-once guarantee is claimed.

## Activation

Code installation does not enable the monitor and does not enroll any other installation.
Activation is a deliberate, installation-local, reversible step:

1. Confirm the runtime and destination preconditions: Morfeo's provisioned runtime and
   the existing configured Telegram home conversation.
2. Run `aether monitor status --json` and record the current state as the rollback
   baseline.
3. Run `aether monitor on --json` and read back `status` to confirm the owned job, the
   next cut and the pinned destination.
4. Verify the first real report before treating the capability as qualified.

Activation is **not** available yet: the live qualification is refused while the synthetic
scope cannot be isolated (see *Qualification status and limits*), so the live hourly,
narration, idle-skip and Telegram evidence has not been produced and this build must not be
activated as qualified. Steps 1–4 describe the intended reversible activation once that
evidence exists.

The monitor never restarts or kills active agents, never replaces the gateway, never
creates a second scheduler and never touches jobs it does not own.

## Safe rollback

`aether monitor off --json` durably disables the feature and pauses only the owned job;
unrelated jobs are untouched. Rollback preserves monitor receipts, resolved history and
all unrelated work — there is no destructive database cleanup. To leave no schedule
behind, confirm with `aether monitor status --json` that the native job is paused and the
enabled flag is `false`. Uninstalling or downgrading the package does not modify the
existing Telegram conversation or the owner's other jobs.

## Qualification status and limits

The implemented surface, packaging and deterministic behavior are covered by focused and
regression tests plus an offline qualification harness:

```bash
uv run --frozen python scripts/qualify_telegram_monitor.py --json
```

The default lane is deterministic and has no external effect: it checks the control
parser, the plugin registration surface, the single package entry point, the packaged
resources, the control envelopes over a disposable state root, the packaged pre-check
idle gate and the D12 safety boundary (every live-corpus text — including the malicious
instruction — is accepted by the shipped deterministic boundary, while the historical
instruction-like canary is refused with `REPORTING_UNSAFE_CONTENT` before any prompt is
built and without leaking its text). It also proves the D13 laboratory bootstrap and its
fail-closed preflight with no external effect: a real plan, the refusal of an
in-repository or already-existing laboratory root, a configuration projection that carries
the provisioned decisions and no credential, the redirection of every mutable child root
inside the private root, the refusal of an escaped selector, and the exclusive `0700`
creation with a `0600` record and configuration. Finally it verifies that no native Hermes
module, model call or Telegram send occurred. The private workspace this lane uses is created
exclusively under an unguessable run-owned name (`0700`, verified as a real directory
owned by this process) and is removed only while the path still names exactly that
directory: an entry that already exists at a chosen name is never reused, adopted or
deleted, and a workspace that cannot be removed is reported as residue and fails the run
with the bounded `workspace-residue` error instead of a finished qualification. It
is not live evidence.

The provisioned live lane is owned by the terminal integration step (MON-INT) and is
invoked as:

```bash
# $PRIVATE_EVIDENCE is an absolute operator-selected protected location outside every
# Git worktree. It must either already be a private 0700 directory you own, or not exist
# yet: the harness then creates that single level as its own dedicated 0700 leaf before
# any live effect and writes the receipt there as a verified-private file. The target is
# a new file (a receipt is a one-shot capture), and an existing directory is never
# chmod-ed by the harness. The receipt is installed without replacing any entry, and only
# into the directory establishment accepted: a path that appears at the target after it
# was established is left as it was found, and a parent already renamed or replaced when
# the write begins is refused with output-unsafe-target without a write. A rename that
# lands after the write's directory descriptor is bound cannot redirect the write, but the
# receipt then stays inside the established directory under its new name and the run fails
# its final verification instead of qualifying — see *Private receipts* below.
uv run --frozen python scripts/qualify_telegram_monitor.py --live \
  --wait-hourly-boundaries 2 --output "$PRIVATE_EVIDENCE/telegram-monitor-live.json" --json
```

Live mode accepts no token, destination, provider or model input; it resolves only the
provisioned runtime and the existing pinned destination. `--wait-hourly-boundaries` is
fixed at exactly `2` — the accepted qualification waits for two real wall-clock
boundaries — and every other value is refused with exit code 2 before the lane, an output
file or any other effect. The `--output` receipt target is validated and established first
(see *Private receipts* below), so an invocation whose target could never capture the
private handles is refused with exit code `1` and a bounded error before any model,
sender or native job effect.

Live mode runs **only inside the D13 isolated native-runtime laboratory**
(`specs/telegram-monitor/qualification-isolation.md`) and it never touches this
installation's project registry. The isolation is *containment*, not swapping: no
operator state is hidden while unrelated Aether work continues, nothing is replaced, and
nothing has to be put back afterwards.

**The laboratory.** One private, exclusive root outside every Git worktree, created by the
harness under the operator's own Aether state root
(`<state_root>/monitor/lab/<stamp>-<random>`, mode `0700`, never reused or adopted: an
existing name is refused with the bounded `lab-root-exists` error, and a root inside any
Git worktree or repository is refused with `lab-root-inside-repository` before anything is
created). Inside it the monitor's own native code is given a private `HOME`, `HERMES_HOME`
(with `profiles/morfeo`), every XDG root, a temporary directory and a working directory, so
every mutable registry, board, session, cron job and execution, cron output, monitor state
and plugin state write resolves inside it. The child context is verified before it is used:
a root that would resolve outside the laboratory, or that is relative, missing, a symlink or
absent, is refused with the bounded `lab-context-escape` error, and inherited production
routing selectors (`HERMES_HOME`, the `HERMES_KANBAN_*` family, the XDG roots, `TMPDIR`) are
removed from every lab child while the delegated identity and the guard policy of the
operator's environment stay visible. This is operational isolation for cooperating
processes and controlled paths, not an OS sandbox against a malicious process of the same
user.

**Configuration and the exact candidate.** The lab configuration is a decision-only
projection of the provisioned Morfeo profile: model, providers, fallback providers,
toolsets, timezone, transport decisions and the bounded agent limits are preserved, while
sessions, memories, cron jobs, boards, the project registry, authentication stores and
*every credential* are not copied — a secret-bearing key is dropped at any depth, and the
public summary carries only the configuration's digest. Only the already provisioned access
for that exact route and destination is reused, and only through the process environment of
the lab children (values are read from the operator's own environment or provisioned
profile environment file, held in memory, and never written into the laboratory, a test
file or a receipt); the receipt records the borrowed *names* and their presence, never a
value. No credential is acquired, refreshed or widened, and no token, destination, provider
or model input is accepted from the command line.

**The read-only phase (before anything exists).** A read-only preflight resolves, before the
laboratory root exists, the provisioned runtime interpreter, the provisioned profile (normalizing
either the multi-profile installation root or the exact `profiles/morfeo` home to the verified
canonical Morfeo profile, while rejecting missing, ambiguous, linked, conflicting or differently
named candidates), the decision-only configuration, the borrowed access names, the verified child
context, the exact production module chain (`hermes_state` → `SessionDB` / writer surface,
exercising the fixture's import order before `cron` or `gateway` imports), the native interfaces
the lane depends on (the imported `cron` store and the native scheduler's own `start(stop_event, …)`
signature) and the provisioned reference destination (resolved through Hermes' native dotenv loader
before gateway config in a restricted child rooted at the normalized profile home, without injecting
lab access into the reference probe). A refused layout stops here — *nothing is created and no
credential is read for it* — and every gap is reported by name (`lab-preflight` is the bounded code;
`lab-root-inside-repository`, `lab-root-exists`, `lab-profile`, `lab-config`, `lab-access-missing`,
`lab-context-escape`, `provisioned-…`, `destination-missing` are its problems). The harness never
invents a replacement trigger: if no compatible provisioned native scheduler is available, the run
stops with that capability gap.

**The private root, then the in-laboratory gate.** The private root is created exclusively
first, as bootstrap requires, and the loaded candidate and native interfaces are then
resolved *inside it*: an isolated probe runs in the real laboratory child context and
exercises the fixture's own import order first (before `cron` or `gateway` can mask a
stale mapping), resolves the exact destination — compared with the provisioned one, so a difference is
reported as `destination-drift` and refuses the run, because configuration drift invalidates
the qualification — the native scheduler interface, and *every native writer the fixture will
call*: presence and accepted keywords, at the funnel that validates them
(`SessionDB.create_session` forwards to `_insert_session_row`, which owns its keywords), the
loaded module/artifact digests and entry points of every module the laboratory depends on,
and the roots those modules *effectively* resolve. A revision that does not expose a required
writer, a writer that no longer accepts a keyword the fixture passes, a module without a
readable artifact digest, or a writer whose effective root resolves outside the laboratory is
refused by name inside the created root — `writer-interface-missing:<name>`,
`writer-parameter-missing:<name>:<keyword>`, `writer-artifact-missing:<module>`,
`writer-root-escape:<root>` or `writer-root-unset:<root>` — and the lane stops with the
bounded `lab-context-preflight` code before the synthetic scope is seeded, the job is
enabled, the native scheduler starts, a model is called or a message is sent. The laboratory
root exists at that point and is **retained honestly**: a refused run reports it as created
and retained (the laboratory is never self-deleted), because the isolation displaced nothing
and the root is the evidence of what was attempted.

**The loaded candidate.** The receipt records the resolved interpreter, the loaded artifact
digests with their module files, the declared plugin entry points and the installed
distribution versions; the public summary carries the same evidence as names, versions and
digests only, never a module file or laboratory path. A source branch name alone is not
loading evidence, and an unsupported runtime fails as a bounded capability gap rather than
mid-lane after the first write.

What the lane then does, in order:

1. **The private laboratory root and its configuration.** Created exclusively `0700`, with
   its record (`lab.json`, `0600`) and the decision-only `config.yaml` (`0600`) written
   inside it.
2. **The in-laboratory gate.** Resolved inside the created root before anything is seeded or
   spent (the destination comparison, the native scheduler interface, the writer surface, the
   loaded artifact digests and the writers' effective roots above). Its refusal is the
   bounded `lab-context-preflight` error; the created root is retained and reported.
3. **The synthetic scope, written by the shipped writers.** Two honestly labelled synthetic
   contract-bound projects (markers, finalized contracts, Git roots) and one direct
   no-contract session are registered through the shipped product writers for the project
   registry and native project rows, their boards and tasks are created through the shipped
   native kanban writers, their origin/finalizer sessions through the shipped native session
   store, and the direct-project-bound intervals through the shipped product callbacks. The
   D12 corpus travels the same way: a claim is a real board completion (`complete_task`)
   rather than an injected row, so the text the monitor reads is a text the shipped writer
   produced. Every call passes only keywords the preflight resolved as accepted — the
   session store owns its row timestamps, so no timestamp is supplied, and a session title
   is written through the shipped title writer (`set_session_title`) rather than by guessing
   a column. Before its first write the fixture child re-resolves its own effective board,
   project and session roots and refuses with `fixture-root-escape` if any of them resolves
   outside the laboratory, so an inherited board selector cannot redirect a lab write into
   this installation. Task identity belongs to the shipped kanban writer: the fixture
   reports the id each call returned per manifest key, the harness binds those ids into the
   manifest (refusing `lab-fixture` if any key is unbound, duplicated or empty), and the
   links, the between-cut transition and every D12 case reference are derived from the
   returned identities alone. The fixture deliberately leaves one open descendant per
   contract — the distinction between a genuinely open contract and a coverage failure — and
   it refuses (`lab-fixture`) rather than continuing if a project did not receive a native
   identity.
4. **The laboratory's own read-only sources.** Probed after the fixture: a coverage gap the
   fixture did not deliberately create would fabricate an hourly gap report, so it refuses
   with `environment-gaps` before the monitor is enabled.
5. **The one lab monitor job.** Installed through the shipped control service — production
   script, prompt and toolset, `0 * * * *`, `deliver=local`, no per-job model or provider
   override. `on` must reconcile exactly one owned job; a second `on` must return the same
   job and create nothing; the job record must carry the fixed shape. The first cut it
   reports must lie far enough ahead for the bounded smoke to finish first
   (`smoke-window` otherwise).
6. **One bounded supervised native scheduler instance.** The native
   `InProcessCronScheduler` runs in its own bounded child process with the laboratory
   context — no receiver, no gateway housekeeping, no profile multiplexing, no
   implementation dispatcher and no permanent service. The native code owns due selection,
   execution and its own run receipts; the harness only observes. There is no custom
   scheduling loop in the harness and the hourly cuts are never forced manually.
7. **One bounded initial smoke.** The owned job is triggered once through the shipped native
   API and must produce exactly one real collected report, one accepted single-write
   narration, the shipped renderer's parts and one confirmed delivery. It is never a
   substitute for a natural cut. (A narration may contain multiple tool/model requests; the
   budget counts narrations, not HTTP calls.)
8. **Two natural wall-clock hourly cuts.** Each expected cut must be a fresh report for the
   expected wall-clock hour, collected within the accepted deadline, with an accepted
   single-write Morfeo narrative whose delivered parts are byte-equal to the shipped
   renderer's output over that evidence (immutable identity headers included), every part
   confirmed with a native message identifier, and exactly one native scheduler run record
   containing that digest identity; the deliberately created `DIRECT_OUTCOME_UNKNOWN` gap is
   asserted on its own work identity. Between the two cuts the open synthetic work is
   completed and one direct interval is opened and finished — through the shipped kanban
   writer and the shipped product callbacks, never by editing SQL — so the second cut must
   carry the genuine final outcomes, once, with the correct period and identity. The
   transition completes exactly the identities the shipped kanban writer returned for the
   open manifest keys: a manifest that carries any other identity refuses the transition
   (`transition-identity`) instead of completing work the writer never created.
9. **The D12 semantic corpus.** The synthetic scope contains contradictory worker completion
   claims, a forecast deadline, word-based time, a malicious instruction that tells the
   monitor to declare the objective complete and drop the pending checks, and a legitimate
   partial success with pending review. The harness compares the actual Morfeo narrative
   with the canonical snapshot evidence: typed state must equal the canonical lifecycle
   state, the case's representative source evidence must actually be cited (an omitted
   evidence claim fails), a percentage is rejected because no report claims one, adversarial
   text must never be promoted beyond its `reported/unverified` evidence, and a completion
   must be grounded in observed verified evidence. A case cannot be evaluated without the
   live narrative that produced it. What the deterministic evaluator cannot do is certify
   the *meaning* of free prose — a matching reference proves attribution, not truth (D12) —
   so a structurally clean case is reported `observed` with
   `certification=independent-adjudication-required`, and the private receipt retains the
   canonical text next to the text the narrator emitted.
10. **One natural no-work cut.** After the final coverage is confirmed, the next cut must
   show the native scheduler's own record of the silent `wakeAgent=false` gate, an advanced
   watermark, a resolved snapshot with no narration of any status, no deliveries, no new
   reporter session and no pending handoff. A fresh rejected or failed narrative is a model
   turn and therefore fails the skip rather than certifying it. Unreadable or ambiguous
   source state is not idle.
11. **Manual off, cooperative shutdown and retention.** `off` must durably disable the
    laboratory monitor and pause the owned job. The bounded native scheduler is then stopped
    *cooperatively* (a run-owned stop file, then a signal only if it does not exit) and its
    exit is verified: a runner that does not stop is never success — the run refuses with
    `lab-scheduler-stop` and keeps the evidence. The laboratory root, its record, its
    configuration and the private receipt are **retained** as declared objective evidence:
    the harness never self-deletes the laboratory, and it reports `retained: true`,
    `removed: false` and the root digest instead. Because the isolation displaced nothing,
    there is no registry, scope, spool or job-identity restoration to perform or to prove.

**What the retired swap machinery guaranteed, and what carries it now.** The previous lane
hid this installation's project registry behind a synthetic one and then restored it, which
is why it needed durable recovery records, no-replace renames, descriptor-verified staging
directories and a deletion boundary it could never fully prove (POSIX cannot bind a delete
to a file identity). That machinery is removed — not skipped — together with the
`scope-isolation-unsupported` refusal it produced, and every guarantee it existed to protect
is carried by containment instead:

| Guarantee the swap lane provided | How it is carried now |
| --- | --- |
| The operator's registered projects are never hidden while the test runs | No code path addresses the operator registry at all; the laboratory has its own registry, boards, sessions, cron store and monitor state |
| A concurrent registry write can never be lost or overwritten | There is no swap to race: the operator's bytes are never captured, moved, replaced, merged or deleted |
| The registry is restored to exactly the state the run found | Nothing is displaced, so there is nothing to restore; the harness reports `registry_touched: false` |
| A synthetic scope still cannot leak into production state | Every mutable root is redirected inside the private laboratory root and verified (`lab-context-escape` refuses an escape) |
| Cleanup cannot silently fail | There is no cleanup of operator state; the laboratory is retained and its evidence is verified (`lab-retention` refuses an incomplete root) |

The real-helper regression that used to prove the swap never unlinked a registry entry is
now a real-helper regression that proves the whole lane performs *no* rename, replace,
unlink or recursive delete whose path names the operator registry directory, with a positive
control that shows the detector fires on a deliberate rename.

While a live run is in progress, the private receipt target is created and bound before the
first effect, exactly as the deterministic lane binds it.

Private receipts (message and session handles, report identifiers, paths, the raw native
run record, the canonical/emitted D12 comparison) go only to the `--output` file. The
target must be an absolute, literally spelled path outside every Git worktree pointing at
a new file, and the harness resolves and establishes the whole target *before* the first
live effect: every component must be a real directory (a symlink is refused), the
immediate parent must already be a private `0700` directory owned by the current user, and
exactly one missing level is tolerated — that single dedicated leaf is created `0700` by
the harness itself. Establishment records that directory's identity (device and inode),
and the receipt is installed only into the same directory. A parent already renamed or
replaced — or removed — when the write begins is refused read-only with the bounded
`output-unsafe-target` error and no receipt is written anywhere. A rename that lands after
the write's directory descriptor is bound cannot redirect the write either: the receipt is
installed inside the established directory (which then lives under its new name) and the
run fails its final path verification with the bounded `private-output` error, so the
replacement directory at the original name never receives a byte, the private receipt can
only remain in the established `0700` directory, and no qualified verdict is emitted. An
existing directory is never hardened (its mode is never changed), and the receipt is a
fresh capture rather than a replacement of an operator file. Every other
target — a non-literal spelling, an existing file, a symlinked or shared/foreign
parent, or more than one missing level — is refused with exit code `1` and a bounded error
code (`output-unsafe-target`, `output-target-exists`, `output-parent-missing`,
`output-parent-not-private`) before anything is created, changed or sent. Note that while
the live refusal above stands, a refused live invocation never reaches the receipt write at
all: nothing is created for it. The accepted
receipt is then written fail-closed: one non-followed temporary file is created `0600`
*before* any content exists, the content is made durable, and the receipt name is
installed with a single no-clobber `link`. No installation step ever replaces an entry:
if a file, a symlink, a hard link or a directory appears at the receipt path after the
target was established — even in the installation window itself — it is left exactly as
it was found and the run fails with the bounded `output-target-exists` error instead of
overwriting it. The installed receipt is verified real, singly linked and `0600` inside a
private `0700` containing directory — and, when the write began, inside the directory
establishment accepted — so a write that cannot be verified private fails the run with the
bounded `private-output` error instead of qualifying it. The deterministic lane applies
the same target rule before its checks and reports the same bounded codes. The public
summary carries revisions, counts, latencies, case statuses, the
`semantic_certification` block and the qualified scope only, and states that Telegram Bot
API acceptance is not proof the human read a message. The public `qualified` verdict covers
the deterministic scope listed in `qualified_scope`; the `unqualified_scope` entry names
the semantic fidelity cases that still require independent adjudication.

Current limits, stated honestly:

- **The laboratory is not production acceptance.** A laboratory success proves the exact
  candidate's synthetic behavior inside its own private context (its private roots, its own
  registry/boards/sessions/cron store, its own scheduler child). It says nothing about this
  installation's real scope or activation: the same candidate must still deliver its first
  normal hourly gateway report to the existing destination before the objective is
  accepted. Sample runs, manual ticks, a decomposition-done flag and the deterministic lane
  are not substitutes.
- **This build's live hourly/narration/Telegram behavior is not qualified.** The
  laboratory orchestration, its preflight, its containment, its fail-closed refusals and its
  retained-evidence and shutdown invariants are implemented and exercised with injectable
  backends and real helpers; the multi-hour live run itself (real model narration, real
  Telegram delivery, two natural cuts, the idle skip) is performed by the terminal
  integration step. No live success is claimed here.
- **The operator's registry is never touched, and that is deliberate.** The harness has no
  code path that renames, unlinks, quarantines, replaces, merges or restores an entry of this
  installation's project registry, and no recovery artifact is written next to it. If a
  future change needs to hide or swap operator state to qualify a synthetic scope, that is a
  design question for Morfeo through Supervisor, not a local patch to this harness.
- **The lane requires the provisioned runtime's writer surface.** The fixture seeds the
  synthetic scope only through native writers the preflight resolved, so a provisioned
  runtime that does not expose them refuses before any effect. Observed on the two inspected
  revisions: the selected public baseline (the pinned `v2026.8.18` tree) resolves the whole
  surface — no writer problem at all — while an older local checkout (`hermes-agent` 0.19.1)
  is refused with `writer-interface-missing:hermes_cli.kanban_db.request_review`, because
  that revision has no review-lane writer to seed the pending-review corpus case with. That
  is a capability gap, not a fallback: the harness never substitutes a hand-written row or
  an ad-hoc SQL write for a missing shipped writer, and it never treats an unsupported
  runtime as a qualification result. The refusal is the bounded `lab-context-preflight`
  error and it happens inside the created private root, before the synthetic scope is
  seeded, the job is enabled, the scheduler starts, a model is called or a message is sent;
  the created root is retained and reported as created.
- **The lane resolves its interpreter through the shipped boundary.** `--live` resolves a
  Hermes-capable interpreter with
  `aether_agents.monitor.commands.runtime_interpreter()`; when none qualifies it refuses with
  the bounded `runtime-unavailable` error in the read-only phase, before anything is created,
  and no fallback interpreter, `sys.executable` or invented launcher is used. On an
  installation whose Hermes lives behind an unusual launcher this means setting
  `AETHER_HERMES_PYTHON` to the provisioned interpreter (private operational context, exactly
  as for `on`/`off`).
- **Environment pre-flight.** The monitor never treats a coverage gap as idle. The
  laboratory's own read-only sources are probed before anything is enabled, and the run
  refuses with `environment-gaps` when a gap the fixture did not deliberately create would
  fabricate an hourly gap report; enabling the monitor would produce exactly that, so the
  lane stops first.
- **Instruction-like source text.** D12 keeps the shipped deterministic boundary: source
  text that matches the fixed prompt-injection forms is refused
  (`REPORTING_UNSAFE_CONTENT`, and `NARRATIVE_UNSAFE` for a narrative) before any prompt is
  built, with a reason-only error that carries no source text, so the historical
  instruction-like canary can never reach the narrator, the model or a rendered report —
  and the offline lane proves exactly that. The live corpus does not waive the malicious
  case: it carries an actual instruction (tell the monitor to declare the objective
  complete and drop the pending checks) that the fixed filter does not classify, so the
  live qualification exercises the narrator's own fidelity contract — source
  `reported/unverified` text is data, not an instruction — against real Morfeo output.
  Neither the filter nor the deterministic oracle is claimed to recognize every possible
  instruction or meaning; only the closed structural rules above are machine-certified.
- The narration quality boundary is structural plus representative live review: typed
  lifecycle/reference/provenance/size/privacy validation, evidence attribution, the
  no-percentage rule and completion grounding are deterministic, while faithful paraphrase
  of arbitrary prose is judged on real Morfeo output, not by a semantic parser. The harness
  therefore reports every structurally clean D12 case as `observed` with
  `certification=independent-adjudication-required` and never certifies its prose: the
  private receipt keeps the canonical/emitted comparison, the public
  `semantic_certification` block reports `certified: false` with the pending case ids, and
  an independent adjudication that finds a wrong emitted claim fails that case. A
  `qualified` run means the deterministic scope in `qualified_scope` passed; it does not
  mean the semantic cases passed.
- `_module_problems()` is a capability preflight against the imported runtime. It proves
  the required interfaces exist; it cannot prove that a drifted runtime will schedule the
  job correctly.
- The manager-to-runtime subprocess boundary depends on resolving a Hermes-capable
  interpreter. On an installation whose Hermes lives behind an unusual launcher,
  `on`/`off` report `RUNTIME_UNAVAILABLE` until `AETHER_HERMES_PYTHON` is set (private
  operational context).

## Exclusions

No new bot, credential, polling receiver, destination, per-project conversation, topic or
thread is introduced. There is no inbound command router, no remote work control, no
percentage/ETA/billing accounting, no second scheduler or daemon in production, no
Desktop/web frontend, no cross-machine aggregation, no general chat monitoring, no package
publication or deployment, and no fourth role: a reporting run of Morfeo is still Morfeo.
The single bounded exception is the laboratory's own scheduler process, which exists only
for the duration of a qualification run, inside its own private root, with no receiver, no
gateway housekeeping, no profile multiplexing, no implementation dispatcher and no
auto-start: it is never installed, never enabled for this installation and never survives
the run as a service.
