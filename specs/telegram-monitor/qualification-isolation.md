# D13 — isolated live qualification and production activation

**Authority:** owner approved Morfeo's presented design and requested a renewed Supervisor handoff. This document owns the material qualification design for `oc_f8c9fc9320587cf3@v3`; spec.md and quickstart.md reference it. Version 3 resolves the provisioned-profile/destination preflight returned from terminal integration. No constitutional change. No implementation or live success is claimed by authoring it.

## Decision and preserved outcome

Keep one installation-wide production monitor and its existing destination. Prove synthetic behavior in a disposable native-runtime laboratory, then verify the same candidate on the existing production gateway. A laboratory success is not production acceptance. This replaces shared-registry swapping/restoration, not identity, privacy, concurrency, semantic fidelity or independent review requirements.

Only the laboratory may run a second, temporary **instance of the native Hermes scheduler**, in its own state and without a gateway receiver, implementation dispatcher, auto-start or permanent service. Do not add a scheduler implementation, per-job product namespace, scope selector, new bot or credentials. Do not interrupt concurrent production work or hide registered projects to manufacture silence.

## Inspected feasibility and limits

- Monitor candidate `21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b`: `paths.state_root` resolves XDG state; `monitor.runtime._collector` combines that root with the native Hermes home. Existing job fields cannot namespace the production gateway's Aether root.
- Provisioned Hermes source `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`: `cron.jobs` stores jobs by profile home; `cron.scheduler_provider.InProcessCronScheduler.start(stop_event, ...)` invokes native `cron.scheduler.tick`. Gateway uses that same built-in implementation. Do not run a custom scheduling loop or manually force the two hourly cuts.
- `monitor.delivery._native_bot_api_send` uses the existing outgoing Bot API helper without starting another Telegram receiver.
- A credential-free, network-free fresh-process probe resolved the Morfeo profile, native cron paths and Aether state inside a temporary HOME/HERMES_HOME/XDG tree. No scheduler, model or sender was started. This proves path isolation interfaces, not E2E behavior.
- CronScheduler is marked experimental in the inspected runtime. Preflight must check actual imported distribution, source/signature and candidate compatibility; this objective does not authorize a Hermes patch. Existing selected-baseline/exact-Hermes tests remain required. If no compatible provisioned native trigger exists, return the exact capability gap rather than invent a replacement.

## Laboratory bootstrap

Use the existing qualification harness and provisioned runtime interpreter. Establish the child environment before importing Hermes/Aether:

1. Create one private, exclusive root outside Git worktrees. Give it separate HOME, all XDG roots, temporary directory, cwd and Hermes root with `profiles/morfeo`. All mutable registry, boards, sessions, cron jobs/executions/output, monitor state and plugin state resolve inside it. Reject links or inherited selectors that redirect those writes to production.
2. Pin and load the exact candidate artifact privately with the provisioned interpreter/dependencies; never install it over the running installation during the test. Record loaded module/artifact digests and entry points, not merely a source branch name. The later production acceptance uses the same relevant candidate bytes.
3. Build minimal test configuration preserving the production Morfeo cron/model/fallback, tool/plugin, timezone, limits and transport decisions. Do not clone existing sessions, memories, jobs, registry, boards or authentication stores. Namespaced test identity is still Morfeo, not a fourth product role.
4. Reuse only already provisioned access needed for that exact route and destination through private ephemeral process context. Never accept token/provider/model/destination overrides from CLI arguments, obtain/refresh credentials or persist new secret copies in test files or receipts. If access cannot be reused within that boundary, fail preflight before live spending. Remove inherited production board/session/project routing selectors only in the lab children, without suppressing delegation identity or guard policy.
5. Verify resolved paths, exact route/destination, privacy of the output target and native interfaces before external effects. Configuration drift invalidates qualification; do not silently change the route. These are fail-closed checks inside the harness, not a new global permission engine.
6. Seed only labeled synthetic projects, contracts, boards and native session/work records with the shipped product/native writers. Drive direct-work lifecycle via its supported callbacks. Do not inject accepted snapshots, model answers, delivery acknowledgments or successful summaries. Create enough native source metadata to distinguish real idle from coverage failure.
7. Install one lab monitor job through its normal service with production script/prompt/toolset, `0 * * * *`, `deliver=local` and no per-job model overrides. Run the native InProcessCronScheduler in a bounded supervised child, with only the lab profile and no receiver, gateway housekeeping, profile multiplexing or implementation dispatcher. The native code owns due selection, execution and receipts; the harness only drives scenarios and observes evidence.

### D14 provisioned profile and destination preflight

The qualification command is valid when `HERMES_HOME` denotes either the installation's
multi-profile root or the exact `profiles/morfeo` home used by a profile-scoped runtime.
Normalize both forms to one exact, existing Morfeo profile directory: use the current
path directly only when it is canonically the named profile and carries the expected
profile configuration; otherwise resolve its `profiles/morfeo` child. Reject missing,
ambiguous, linked, conflicting or differently named candidates. Current worker cwd or
profile identity is not a fallback. Record only the normalized-path class and a digest,
never a machine path in public evidence.

After that identity is fixed, establish the **provisioned reference destination** in a
restricted child using the exact Morfeo profile home. The child invokes Hermes'
provisioned `hermes_cli.env_loader.load_hermes_dotenv()` before
`gateway.config.load_gateway_config()`, so profile-local `.env` configuration is visible
through the runtime's supported loader. It returns only the existing bounded destination
projection/digest and presence flags. It must not print, persist, copy or return
credential values, and it performs no model or transport call.

Separately collect only the already-authorized access names needed by the lab into the
parent's ephemeral memory and pass them only to lab children. The lab's resolved target,
route and relevant configuration digests must exactly match the provisioned reference.
Supplying those values to the reference probe would compare an injected environment to
itself and is rejected; loading the provisioned dotenv is the reference side, while
ephemeral access is the lab side. No new CLI credential/destination input is added.

The preserved `lab-config` refusal occurred during bootstrap preflight, before laboratory
creation, credential loading, model/sender calls or the experiment attempt boundary. It
consumed none of the one-smoke/two-active-cut/idle-cut budget. After the D14 correction is
implemented and independently reviewed, exactly one corrected live qualification attempt
is authorized with a new no-overwrite receipt target. This is an explicit continuation,
not an automatic retry. Any subsequent live failure stops the experiment under the
existing rule.

### D15 autonomous continuation after recovered provisioned-runtime drift

The owner explicitly renewed autonomous continuation after the single v3 attempt failed
before any job, scheduler, model or Telegram effect. D14R candidate
`f603f8f1ace4dbb112afb05e032da620642e7050` is independently reviewed and integrated;
the provisioned editable metadata was recovered without changing source, dependencies,
profiles, credentials or running processes. One additional live qualification attempt is
authorized on that exact candidate with a new no-overwrite private target. Morfeo and
Supervisor must not ask again for routine bounded, reversible recovery that occurs before
external qualification effects and stays within the existing recovery limits. Once the
attempt starts a lab job/scheduler, model call or Telegram send, a failure stops the live
experiment with evidence and no automatic rerun. This authorization does not permit a
different candidate, destination, provider/model change, credential widening, weakened
acceptance, fabricated receipt or unbounded retry loop.

### D16 proportionate accelerated laboratory schedule

The owner rejected the multi-hour laboratory wait as disproportionate and selected an
accelerated temporal oracle. Production cadence remains exactly `0 * * * *`. After the
normal monitor service creates and validates the isolated lab job, the harness uses the
native `cron.jobs.update_job` interface **inside the private lab store only** to set that
job's qualification schedule to `* * * * *`. The same native `get_due_jobs` and
`InProcessCronScheduler` then cross real minute boundaries: two active cuts followed by
one idle cut. Do not change the system clock, monkeypatch a fake scheduler clock, invoke
manual/forced ticks as evidence, build another scheduler or use this accelerated schedule
in production.

The existing `--wait-hourly-boundaries 2` spelling is retained only to avoid expanding the
unfinished private harness interface; under D16 it selects two hourly-behavior scenarios
executed on accelerated **lab scheduled boundaries**, not evidence of elapsed hours. The
receipt must state the actual lab cron expression and timestamps and must never label
those cuts as production-hourly evidence. Deterministic tests separately prove the fixed
production job shape `0 * * * *`, schedule calculation, DST/restart and drift refusal.

After independent laboratory acceptance, activate the exact candidate with `0 * * * *`
on the existing production gateway and observe one natural hourly due execution and real
Telegram acknowledgment. That single production cut is the only wall-clock hourly oracle;
it is not replaced by the minute laboratory. No second production idle hour is required:
the idle behavior is accepted from the real native scheduler/monitor/transport path in the
isolated lab plus deterministic controls. Maximum unavoidable wait after production
activation is one hour, plus ordinary delivery and GitHub closeout.

This is operational isolation for cooperating processes and controlled paths, not an OS sandbox against a malicious process of the same user. Production state may legitimately change because other agents work; do not demand that all production files remain byte-identical. The harness itself must never replace, restore, quarantine, merge or delete the production registry.

## Live sequence and budget

Retain the public harness interface:

```bash
uv run --frozen python scripts/qualify_telegram_monitor.py --json
uv run --frozen python scripts/qualify_telegram_monitor.py --live \
  --wait-hourly-boundaries 2 --output "$PRIVATE_EVIDENCE/telegram-monitor-live.json" --json
```

Without `--live`, there are zero model/sender calls. `2` means two active lab scheduled
boundaries, followed by one lab idle boundary. Under D16 these are real minute boundaries
on the private `* * * * *` job; production remains hourly. Existing D2 pickup/lateness
tolerances apply relative to the actual schedule being observed.

- First run deterministic/static/exact-runtime gates and bootstrap preflight.
- One initial bounded native model/transport smoke, labeled test; not a substitute for a scheduled boundary. Preserve the existing lead-time/deadline limits so the smoke cannot be counted as the first cut.
- First accelerated lab cut: two projects/origins/contracts, a completed decomposition root with open descendant, review/blocked/unchanged work, and direct no-contract work. Cover the existing D12 semantic corpus within the smoke/lab narratives; independently assess fidelity, not only structural validation.
- Between cuts: create a short-lived work interval and finish it; complete the other synthetic scenarios through supported lifecycle. Do not directly edit source SQL or fabricate closure evidence.
- Second accelerated lab cut: report pending final outcomes once with correct period/identity and actual native Telegram acknowledgments. Keep projects registered; only their work terminates.
- Next accelerated lab cut: same registered projects, genuinely no work and no unreported outcome. Require the native silent gate, zero new narration and zero new send. Unreadable/ambiguous source state is not idle.
- Preserve manual-off/idempotence/recovery controls. Induce network/fault/concurrency cases only through deterministic adapters and test-owned roots, never the owner's real transport or shared state.

Budget is one smoke plus at most one normal narration per active lab digest, with existing provisioned fallback/agent bounds. One narration may contain multiple tool/model requests; do not misreport this as one HTTP call. The idle cut consumes none. No automatic live rerun loop. A failed qualification stops with evidence; a retry needs the corrected cause and an explicit remaining budget within approved authority. Scheduler lifetime is bounded to the three accelerated lab boundaries plus existing tolerances; closing the test TUI must not stop it.

## Receipt, shutdown and retention

A private receipt correlates candidate/artifact/native revisions, lab identity, source binding, due/capture/narration/ack times in UTC and local offset, job/session/report, status per criterion, limits/failures and shutdown. Public evidence contains sanitized references/timings/counts, not native live identifiers, paths, credentials or transcripts. Synthetic source labels produce visible test labeling without post-editing generated messages. Bot API acceptance is not human reading.

Preflight output capture before any costly effect. Use an exclusively owned evidence target and no-overwrite finalization; preserve the existing private-write controls that still apply. Disable only the lab job, stop its native scheduler cooperatively and drain in-flight work under existing bounds. Uncertain delivery or a runner that fails to stop is not success.

**Do not self-delete the laboratory in the test.** Retain its private root and receipt as explicitly reported objective evidence. Cleanup, if authorized at final closeout, is confined to proven test-owned state after processes end and evidence is durable. No real registry restoration is required. Removing the old shared-registry/cleanup mechanism removes its race surface; it does not waive preservation of unrelated data.

## Real installation activation

### D17 — pragmatic terminal acceptance without another live laboratory

The owner directs the fastest complete closeout and rejects further live laboratory attempts. The retained v7 evidence proves the actual Morfeo model/narration/native sender path and three confirmed Telegram parts. Independently accepted D16U must prove, with the shipped store/runtime APIs and a read-only replay of v7, that one `pending -> accepted` narrative is accepted and a genuine second narration is refused. Together these replace another live laboratory run; neither alone proves production activation.

Activate the same reviewed candidate in the provisioned Morfeo runtime only during a verified zero-worker window. Keep the production job at `0 * * * *`. Immediately request one run of that installed job through Hermes' native `cron run` operation; this is an installation and delivery canary, not evidence of a natural hourly trigger. Verify its result, Telegram acknowledgment, persisted monitor status, exact job identity/schedule and next hourly due time. Existing successful hourly execution of the temporary build reporter proves the provisioned scheduler infrastructure; the first natural run of the permanent job is post-close operational confirmation. If the immediate production canary fails, rollback and do not close. If the later natural run fails, reopen #367 and apply the documented scoped rollback. Closeout may proceed after the production canary, required repository checks and merge; label the omitted pre-close natural-hour observation explicitly rather than claiming it ran.

After independent lab review, use the supported scoped monitor activation and rollback, preserving the running gateway/agents:

1. Revalidate exact candidate modules/plugins and relevant provisioned configuration. Cached code from a different candidate is not parity. Activate only during a verified zero-worker window; if work appears, wait rather than interrupt it.
2. Register/reuse the production monitor with D3's actual installation-wide scope. Never copy lab job IDs, cursors, snapshots, source records, receipts or approval flags into production.
3. Request one immediate run through the native cron interface and verify authoritative source identity, period, actual tool/plugin path, Telegram acknowledgment, `0 * * * *` persistence and next due time. Do not call this a natural hourly run.
4. Keep the first natural permanent-job hour as monitored post-close evidence. Do not force production idle while other agents work; deterministic coverage proves idle. A natural-run failure reopens #367 and invokes scoped rollback.
5. Retire the exact temporary build reporter only after the production canary is confirmed and the permanent hourly job is verified scheduled. On canary failure, retain evidence, roll back and keep #367 open.

## Continuation and preservation of previous work

Version 2 supersedes the executable v1 design without invalidating reviewed code by fiat. Supervisor independently confirms reusable commits/receipts, maps the existing outcomes into the revised execution flow and owns any continuation/decomposition. Do not dispatch duplicate implementation for accepted outcomes or mark blocked v1 work done merely to satisfy a parent edge. Do not resume the old unsafe live lane. The v2 root ends after verified executable continuation handoff; implementation/review/integration remain separate native lifecycle phases.

Retain the immutable v1 artifact and actual reviewed commits:

| Outcome | Candidate/evidence revision | Evidence path |
| --- | --- | --- |
| MON-01 approved | cfbab930727c2e68fb6a0391088e77918b712edd | specs/telegram-monitor/evidence/MON-01.md |
| MON-02 approved | 55334be6fb0d187fef341689775e929a8a286b56 | specs/telegram-monitor/evidence/MON-02.md |
| MON-03 approved | dc19fe31d3c7cf21dbf35cb6669f495f39ee97e2; receipt 53e1b2da92e872823c56626ab716cc1ebce7fc77 | specs/telegram-monitor/evidence/MON-03.md |
| MON-04 approved | d908c033d139e9dfeddfedf4461f85b40faedadc | specs/telegram-monitor/evidence/MON-04.md |
| MON-05 approved | 2d49418b2ac9a3f64764b84e1b071df48b85070f | specs/telegram-monitor/evidence/MON-05.md |
| MON-05-R1 approved, test-only | 704b729bc418f0d009ec32ac6a01e47197f36774 | specs/telegram-monitor/evidence/MON-05-R1.md |
| MON-06 preserved, NOT approved | 21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b | specs/telegram-monitor/evidence/MON-06.md |

The table is source evidence from prior durable review handoffs, not a claim that Morfeo independently reran all suites. Use the exact predecessor contract binding for targeted board evidence when needed. Integration preserves commits and reconciles main changes, including canonical Supervisor convergence guidance and worker tools, rather than reverting them to a stale unit base.

The expected remaining changes are the qualification harness/tests/documentation, its private bootstrap/scenario/receipt/shutdown helpers and the previously identified mechanical lifecycle plugin allowlist integration. Preserve approved production behavior; material new shared interfaces return to Morfeo. Remove `scope-isolation-unsupported` only after the real isolated preflight replaces the unsafe lane, not as an unconditional bypass. Local helper names, equivalent algorithms and test organization remain Implementer choices. No implementation cards are authored here.

## Failure ownership and rejected alternatives

A real source gap such as #390 must remain explicit. Fix only objective-blocking defects within existing authority through the correct role; otherwise record dependency/limits. Never hand back a false idle/success snapshot. Hermes recovery remains Morfeo's bounded operation, not a new framework repair inside this feature.

Rejected: swapping the live registry; mocks-only live claims; extending product/gateway scope per job merely for a test; pausing all real agents; starting another Telegram receiver. All original AC-1..9 remain required with D13's explicit allocation of lab and production evidence. Release impact expected minor/additive, action defer, channel none; no publication/tag authority is added.
