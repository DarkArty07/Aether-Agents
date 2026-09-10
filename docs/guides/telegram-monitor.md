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

- No credential, chat identifier, message text, raw transcript, tool argument/result or
  provider binding is persisted or printed. The destination reference is an opaque
  digest of the pinned target.
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
resources, the control envelopes over a disposable state root and the packaged pre-check
idle gate, and it verifies that no native Hermes module, model call or Telegram send
occurred. It is not live evidence.

The provisioned live lane is owned by the terminal integration step (MON-INT) and is
invoked as:

```bash
# $PRIVATE_EVIDENCE is an operator-selected protected directory outside every Git worktree.
uv run --frozen python scripts/qualify_telegram_monitor.py --live \
  --wait-hourly-boundaries 2 --output "$PRIVATE_EVIDENCE/telegram-monitor-live.json" --json
```

Live mode accepts no token, destination, provider or model input; it resolves only the
provisioned runtime and the existing pinned destination, and it performs no external
effect until its environment pre-flight passes. What it does, in order:

1. **Isolating one synthetic scope.** The operator's project registry is backed up
   byte-for-byte and replaced, for the duration of the run, by a registry containing only
   two honestly labelled synthetic projects (markers, finalized contracts, canonical
   boards, origin/finalizer sessions) plus one direct no-contract session. Everything the
   run creates — native project rows, boards, sessions, direct-turn spool files — is
   removed afterwards and the registry bytes are restored and verified. The
   qualification never invents a real project identity, never edits a source database and
   never restarts or kills an agent.
2. **Proving the fixed native job.** `on` must reconcile exactly one owned job; a second
   `on` must return the same job and create nothing; the job record must carry the fixed
   schedule, pre-check script, `deliver=local`, restricted reporter toolset, no agent
   bypass and no model/provider/origin override.
3. **Two real hourly boundaries.** Each expected cut must be a fresh report for the
   expected wall-clock hour, collected within the accepted deadline, with an accepted
   single-write Morfeo narrative whose delivered parts are byte-equal to the shipped
   renderer's output over that evidence (including the immutable identity headers), every
   part confirmed with a native message identifier, and at most one native scheduler run
   record containing that digest identity. Between the two cuts the synthetic work
   transitions — a flow completes, a reviewed flow closes, a direct turn opens a
   continuation — so the second boundary must carry the genuine final reports.
4. **Comparing the D12 semantic corpus with canonical state.** The synthetic scope
   contains contradictory worker completion claims, a forecast deadline, word-based time,
   a malicious instruction and a legitimate partial success with pending review. The
   harness compares the actual Morfeo narrative with the canonical snapshot evidence:
   typed state must equal the canonical lifecycle state, adversarial text must never be
   promoted beyond its `reported/unverified` evidence, a completion must be grounded in
   observed verified evidence, and the direct case must carry no contract. A case cannot
   pass without the live narrative that produced it.
5. **One real no-work boundary.** After the final coverage is confirmed, the next cut
   must show the native scheduler's own record of the silent `wakeAgent=false` gate, an
   advanced watermark, a resolved snapshot with no narration of any status, no deliveries,
   no new reporter session and no pending handoff. A fresh rejected or failed narrative
   is a model turn and therefore fails the skip rather than certifying it.
6. **Manual off and restoration.** `off` must durably disable the monitor and pause the
   owned job; the prior enablement (and, on an installation that had none, the absence of
   the created job) and every unrelated job's behaviour-bearing fields must be restored.

Private receipts (message and session handles, report identifiers, paths, the raw native
run record) go only to the `--output` file, which must live outside every Git worktree;
the public summary carries revisions, counts, latencies, case results and the qualified
scope only, and states that Telegram Bot API acceptance is not proof the human read a
message.

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
- The narration quality boundary is structural plus representative live review: typed
  lifecycle/reference/provenance/size/privacy validation is deterministic, while faithful
  paraphrase of arbitrary prose is judged on real Morfeo output, not by a semantic parser.
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
