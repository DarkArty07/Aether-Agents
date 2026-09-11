# Authoring checkpoint — not implementation acceptance

- Objective Contract `oc_f8c9fc9320587cf3@v1` was incrementally authored and finalized by
  the native capability. Structural validation returned valid with no missing section.
- Requirements, material native-adapter/data/source design, concrete test path, scope,
  preservation and delegated decisions are in the adjacent spec/plan/quickstart/research.
  No material open design choice is deferred to Implementer. Supervisor receipt review
  and implementation decomposition have not been claimed as already performed.
- `uv run --frozen python scripts/check_documentation.py`: passed.
- `git diff --check` and staged diff check: passed.
- An initial direct pytest command imported the local editable Hermes fork and yielded
  42 passes, 6 disposable-board failures due to inherited delegated-child process
  classification. Recorded as additional evidence in existing issue #310; no runtime,
  guard, source or test modification was made for it.
- The documented baseline runner
  `uv run --frozen python scripts/run_tests.py -- tests/test_documentation.py tests/test_objective_contracts.py -q`
  returned **48 passed in 1.85s**. This verifies authoring/documentation against the
  selected baseline, not the new monitor's behavior or activation.
- Root AGENTS exception linkage passed the normal guard after the owner's explicit
  up-front protected-edit request. All three SOUL files remain unchanged and out of scope.
- A native Telegram startup message was accepted and the temporary hourly build reporter
  was registered. Private operational receipts stay outside public source. This is
  progress-channel readiness only, not final feature evidence.
- Preexisting source branch, concurrent remediation work, other jobs and stashes were
  preserved. No source-feature implementation, fork patch, provider/configuration rewrite,
  activation of the final monitor, package publication or cleanup occurred in authoring.

Supervisor must inspect the canonical artifacts, create its own coverage/dependency
breakdown, and verify actual unit/integration/live outcomes before terminal closure.

## v2 — owner-approved isolation revision

The owner approved D13's presented laboratory plus production-activation design and
requested renewed Supervisor handoff. The native capability supersedes immutable v1;
its v2 draft passed structural validation with all sections present. Design sufficiency
was self-checked against scope, authority, original AC-1..9 and expected test effects:
lab roots are private; native scheduler is reused without another receiver/dispatcher;
production registry replacement is prohibited; lab and actual gateway evidence are
separate; retained private evidence replaces unsafe cleanup, not preservation itself.

The existing canonical baseline runner for `tests/test_documentation.py` and
`tests/test_objective_contracts.py` returned **48 passed in 1.94s**. Documentation
validation and `git diff --check` passed. These are authoring/source checks, not live
monitor qualification. Prior approved candidate hashes were checked as reachable Git
commits and matched the predecessor's durable independent-review summaries; no claim
of rerunning those unit suites is made. D13 lists the exact reuse/provenance boundaries.

The source/path-resolution probe verified isolated native roots and the Morfeo identity
with no scheduler/model/sender execution. Actual artifact/config/plugin qualification
remains an explicit preflight in D13 before spending the approved live budget. No
product code, credentials, profiles or existing worker state were mutated by authoring.
The existing Project knowledge component returned VIEW_MISMATCH for the native session
workspace; direct current source inspection was used, not a substituted graph result.

## v3 — provisioned profile and destination preflight

Supervisor integrated every accepted v2 unit at `19dfc9d68e797f7d365f078ef65be70fbd16f158`,
completed deterministic verification and preserved a no-effect `lab-config` refusal. The
refusal proved two interface gaps before the experiment boundary: the harness assumed
`HERMES_HOME` was always a multi-profile root although this installation uses the exact
Morfeo profile home, and its restricted reference probe neither inherited `TELEGRAM_*`
nor invoked the provisioned dotenv loader. No lab, credential read, model or send occurred.

Morfeo selected one source-owned resolution: normalize both supported HERMES_HOME forms
to the exact verified Morfeo profile; establish the provisioned reference in a restricted
child by loading the profile dotenv with Hermes' native loader before gateway config; keep
lab access separate and ephemeral; compare only bounded target/config digests. Injecting
lab access into the reference probe is rejected. The preserved refusal consumed no live
budget; after D14 correction and independent review, exactly one corrected attempt remains.

The v3 draft passed structural validation with all sections present. The existing authoring
runner returned **48 passed in 7.44s**; documentation and `git diff --check` passed. This
proves source/contract consistency only. No credential value was read or written by this
authoring phase, no profile/config/provider/model changed, no live command was rerun and
no qualification/production acceptance is claimed.

## D17 — owner-approved pragmatic terminal closeout

After approximately 44 hours of pipeline activity, the owner directed the fastest complete closeout without omitting product behavior. D17 ends further live-laboratory attempts. Retained v7 evidence already records one real Morfeo narration and three confirmed Telegram parts; D16U must be independently accepted and replay that evidence while deterministically proving the legitimate `pending -> accepted` transition and genuine duplicate refusal. Production then uses the exact reviewed candidate, a verified zero-worker activation window, one immediate native `cron run`, confirmed delivery, unchanged `0 * * * *` schedule/next due and rollback. The first natural permanent-job run is post-close monitoring and cannot be claimed as pre-close evidence. This changes verification allocation, not the product's hourly cadence, identity, privacy, deduplication or silence behavior.

## D15 — autonomous additional live-attempt authority

After D14R candidate `f603f8f1ace4dbb112afb05e032da620642e7050` passed independent
review and integrated verification, the owner instructed Morfeo to stop asking for this
routine continuation and work autonomously. One additional live qualification attempt is
therefore authorized on that exact candidate and a new no-overwrite private target. The
prior v3 failure remains preserved and produced no job, scheduler, model or Telegram
effect. Pre-effect recovery remains bounded and reversible; any failure after external
qualification effects begin stops without an automatic rerun. This is authority to run
the existing accepted test, not evidence that it passed or authority to change the
candidate, destination, credentials, provider/model or acceptance criteria.

## D16 — accelerated laboratory temporal oracle

The owner rejected the multi-hour lab wait as disproportionate and requested simulation.
Inspection of the provisioned native scheduler confirmed `compute_next_run` resolves
`* * * * *` to the next minute and `0 * * * *` to the next hour, and `update_job`
recomputes stored due state through the supported cron interface. D16 therefore keeps the
system clock and scheduler real but changes only the private lab job to minute cadence:
two active and one idle cut in minutes. Production remains hourly and one natural
production due/report/ack remains mandatory. Lab receipts must name their actual cadence
and cannot claim elapsed-hour evidence. This authoring performed no scheduler/model/send
operation and did not change the in-flight D15R review; it only prevented another old-plan
live run while v4 is finalized.
