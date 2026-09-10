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
built and without leaking its text), and it verifies that no native Hermes module, model
call or Telegram send occurred. It is not live evidence.

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
provisioned runtime and the existing pinned destination, and it performs no external
effect until its environment pre-flight passes. `--wait-hourly-boundaries` is fixed at
exactly `2` — the accepted qualification waits for two real wall-clock boundaries — and
every other value is refused with exit code 2 before the lane, an output file or any other
effect. The `--output` receipt target is validated and established first (see *Private
receipts* below), so an invocation whose target could never capture the private handles is
refused with exit code 1 and a bounded error before any model, sender or native job
effect. What it does, in order:

0. **Quiescing a running monitor.** If the monitor is already enabled, it is durably
   disabled and its owned job paused *before* the registry is isolated, so no scheduled
   run can observe the synthetic-only registry while the scope is being prepared. The
   prior enablement and binding are restored at the end.
1. **Isolating one synthetic scope.** The operator's project registry is read with the
   private reader — only a genuinely missing registry counts as "no registry"; an
   unreadable, symlinked, multi-linked or unstably replaced one refuses the run with the
   bounded `registry-unreadable` error before anything is changed — and its bytes are then
   captured in a durable, verified-private `0600` recovery record installed next to the
   registry with the same no-clobber discipline as the receipt. The replacement itself never
   destroys a byte: the operator's own file is *moved aside* to a private held name with a
   no-replace rename (the kernel tests the destination and moves in the same operation), so
   neither an entry already sitting at the held name nor a concurrent write can be overwritten
   or unlinked: a taken held name refuses the run with `registry-held-exists` and leaves that
   entry exactly as it was found. The moved bytes are checked against the capture, and
   the registry is then presented — for the duration of the run — as one containing only two
   honestly labelled synthetic projects (markers, finalized contracts, canonical boards,
   origin/finalizer sessions) plus one direct no-contract session. A concurrent write that
   lands while the registry is captured or swapped is detected instead of being replaced: the
   changed file is moved back (no-replace again; or it stays at the held name, recoverable,
   beside the durable record) and the run refuses with
   the bounded `registry-changed` error. The manifest
   and the local project files exist before the first native row is created, so every
   failure path removes exactly the scope this run holds. Everything the run creates —
   native project rows, boards, sessions, direct-turn spool files, and the registry entries
   the scope's own runtime probe registers for the synthetic projects — is removed afterwards
   and each removal is verified absent: a surviving object is recorded as residue and gates
   the verdict instead of being ignored. The registry is restored to the state the run
   found: the exact operator bytes are written back (or the harness's own synthetic file is
   removed when the run found none), and a legitimate registry update that appeared while
   the synthetic registry was in place is preserved — the operator's original entries are
   merged back under it and no concurrent entry is ever deleted. The exact value this run
   registered for each synthetic project is *carried*, not inferred: it is derived from the
   shipped project writer itself (the same registration call with the same arguments, run
   against a private scratch state root the harness creates and removes) and never read back
   out of the operator registry, so a concurrent writer's same-id update can never be captured
   as this run's entry. Entries this run registered for its own synthetic projects are removed
   only while they still carry exactly that value; an entry for a run-owned id that changed is
   neither deleted nor merged — the restore refuses and keeps the durable evidence. The
   qualification never invents a real
   project identity, never edits a source database and never restarts or kills an agent.
2. **Environment pre-flight.** The installation's own read-only sources are probed before
   the fixture introduces its deliberate gap. Any permanent gap refuses the run before it
   is enabled (see the limits below).
3. **Proving the fixed native job.** `on` must reconcile exactly one owned job; a second
   `on` must return the same job and create nothing; the job record must carry the fixed
   schedule, pre-check script, `deliver=local`, restricted reporter toolset, no agent
   bypass and no model/provider/origin override.
4. **One bounded initial smoke.** The owned job is triggered once through the shipped
   native API and must produce exactly one real collected report, one accepted
   single-write narration, the shipped renderer's parts and one confirmed delivery — a
   real end-to-end model-plus-transport check before the long wait. It is bounded, it is
   never a substitute for a real hourly boundary, and it refuses to start when the first
   boundary is less than fifteen minutes away (a native trigger schedules the job for
   `now`, which would consume that boundary) and restores the prior state when it fails.
5. **Two real hourly boundaries.** Each expected cut must be a fresh report for the
   expected wall-clock hour, collected within the accepted deadline, with an accepted
   single-write Morfeo narrative whose delivered parts are byte-equal to the shipped
   renderer's output over that evidence (including the immutable identity headers), every
   part confirmed with a native message identifier, and exactly one native scheduler run
   record containing that digest identity. The collection-level coverage gaps must be
   exactly the pre-flight baseline, and the deliberately created `DIRECT_OUTCOME_UNKNOWN`
   gap is asserted on its own work identity. Between the two cuts the synthetic work
   transitions — a flow completes, a reviewed flow closes, a direct turn opens a
   continuation — so the second boundary must carry the genuine final reports.
6. **Comparing the D12 semantic corpus with canonical state.** The synthetic scope
   contains contradictory worker completion claims, a forecast deadline, word-based time,
   a malicious instruction that tells the monitor to declare the objective complete and
   drop the pending checks, and a legitimate partial success with pending review. The
   harness compares the actual Morfeo narrative with the canonical snapshot evidence:
   typed state must equal the canonical lifecycle state, the case's representative source
   evidence must actually be cited (an omitted evidence claim fails), a percentage is
   rejected because no report claims one, adversarial text must never be promoted beyond
   its `reported/unverified` evidence, and a completion must be grounded in observed
   verified evidence. A case cannot be evaluated without the live narrative that produced
   it. What the deterministic evaluator cannot do is certify the meaning of free prose —
   a matching reference proves attribution, not truth (D12) — so a structurally clean case
   is reported `observed` with `certification=independent-adjudication-required`, and the
   private receipt retains the canonical text next to the text the narrator emitted. The
   public verdict never certifies those cases: an independent adjudication of the retained
   comparison is required before they are counted, and a wrong emitted claim found there is
   a failed case (and a failed AC-5 result), not a pass.
7. **One real no-work boundary.** After the final coverage is confirmed, the next cut
   must show the native scheduler's own record of the silent `wakeAgent=false` gate, an
   advanced watermark, a resolved snapshot with no narration of any status, no deliveries,
   no new reporter session and no pending handoff. A fresh rejected or failed narrative
   is a model turn and therefore fails the skip rather than certifying it.
8. **Manual off and restoration.** `off` must durably disable the monitor and pause the
   owned job; the prior enablement, the exact prior persisted job identity, the absence of
   a job this run created and every unrelated job's behaviour-bearing fields must all be
   restored. Every synthetic object this run writes is removed and then *verified absent*:
   the native project rows, board directories, project paths, session rows, the direct-turn
   spool records and the scope root each carry a postcondition, a removal that silently
   fails or raises is recorded as residue, and residue is qualification-gating. A run that
   cannot put the installation back where it found it reports `ok: false` with the specific
   restore error codes (`restore-scope`, `restore-direct-spool`, `restore-registry`,
   `restore-job-identity`, `restore-created-job`, `restore-enabled`,
   `restore-unrelated-jobs`) even when every boundary passed. The registry outcome is
   reported as `byte-identical` (the registry holds exactly the bytes the run found — also the
   outcome when the only entries the isolation carried were the ones this run's own synthetic
   scope registered and removed again), `removed` (the run found no registry and none is
   left — including the live-shaped cycle in which the only entries that ever appeared were
   this run's own scope registrations, which are removed), `merged-concurrent` (a legitimate
   concurrent update appeared during isolation: its entries survive, this run's own scope
   registrations are removed from it, and the operator's original entries — when the run found
   any — are merged back under them) or `concurrent-kept` (the run found no registry and a
   concurrently created one that never carried a run-owned entry is untouched);
   any other result gates the verdict with `restore-registry` and keeps the durable recovery
   record for reconciliation.

Registry recovery after an interruption. Two durable artifacts live next to the operator
registry for the duration of a live run: `registry.json.qualification-recovery.json` holds
the operator's registry state exactly as the run found it — its bytes in base64 with their
SHA-256 and file identity, or the recorded true absence — plus the SHA-256 of the synthetic
registry the run installs, and `registry.json.qualification-held` *is* the operator's own
file (moved aside with a no-replace rename, never deleted). A process terminated during the
run leaves both on disk,
so the operator's bytes stay recoverable; the next live run refuses with
`registry-recovery-exists` (or `registry-held-exists` for a held file without a record), and
an existing artifact is never replaced or unlinked, so no run can silently discard the
evidence of
an earlier one. An operator restores the bytes from the held file (or the record) and removes
the artifacts before re-running. A completed run removes exactly the artifacts it created,
each verified against the identity and content it installed, and only after the restored
state — including the absence of every registry entry this run registered for its synthetic
projects — has been verified; a restore that cannot prove that fails the run and keeps the
artifacts. The removal never unlinks a documented artifact name: it first moves that name
with a no-replace rename to a fresh name this run invents in the same private directory, then
verifies the moved file against the identity and content this run installed, and only that
fresh name — created by this run moments earlier — is unlinked. A file that does not verify is
moved straight back to the artifact name (no-replace again) and the removal reports failure:
an entry that appeared at the artifact name after the reader's check is never replaced and
never deleted, and the run refuses with the durable evidence intact. If the move back itself
cannot be performed because the artifact name was taken meanwhile, the moved file stays on
disk at that fresh name — `<artifact name>.<random>.qualification-quarantine` beside it — so
nothing is lost.

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
`output-parent-not-private`) before anything is created, changed or sent. The accepted
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

- Until the live lane and the terminal integration complete, this build's live
  hourly/narration/Telegram behavior is **not** qualified. Sample runs, manual ticks and
  the offline lane are not substitutes.
- **Environment pre-flight.** The monitor never treats a coverage gap as idle. A
  read-only probe therefore runs before anything is enabled, and the run refuses with
  `environment-gaps` when the installation itself reports a gap the qualification cannot
  remove (for example the default board's absent metadata, or a native session without a
  title). On such an installation the genuine no-work skip cannot occur and enabling the
  monitor would produce an hourly gap report; the live lane must not send that, so it
  stops before the first live effect and reports the gap codes.
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
percentage/ETA/billing accounting, no second scheduler or daemon, no Desktop/web frontend,
no cross-machine aggregation, no general chat monitoring, no package publication or
deployment, and no fourth role: a reporting run of Morfeo is still Morfeo.
