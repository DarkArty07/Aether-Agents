# HLP-280 bounded flow recovery

## Result and scope

The owner selected direct, bounded runtime recovery after the rejected design
pipelines. Morfeo repaired the existing HLP-211b path without spawning agents,
creating another Objective Contract, or implementing the v4/v5 redesign.

The installed repair is one file, `hermes_cli/kanban_db.py`, distributed here as
[an exact-preimage patch](../../../../patches/hermes/HLP-280-bounded-flow-recovery.patch).
It adds no database tables, migrations, services or dependencies to the runtime.

The local recovery canary passed end-to-end: an affinity root blocked with
`needs_input` **without** an explicit `origin_signal`; the existing native TUI
reader consumed the generated signal and the exact originating Morfeo session
received the follow-up turn. No auxiliary worker or notifier generated the wake.
The canary task was completed, its subscription removed, and only its isolated
board was archived recoverably. Private board/session/process identities and the
archived database remain in the local recovery backup, not this public package.

## Session closure

The [session retrospective](session-retrospective.md) records the delivery failures,
Morfeo's routing/communication lessons, and measured line changes. The
[usage snapshot](session-cost-snapshot.json) reports causally attributed consumption
with explicit coverage and monetary-cost limitations. Neither expands the repair.

## Exact artifact identity

- Patch SHA-256: `59f873ad50e0b3386223bac1fbe2a63699a19dd757175879fefc5bf923f1738b`.
- Required active preimage SHA-256: `58d97754650280db9fd1e7ad545b9af151b86d83d73d653dd84fb531f34a29b3`.
- Installed postimage SHA-256: `10d60a61000b02457381cac3de2b202bf5ecc84bff9ad0f52e4f8f35809a1eb0`.
- Runtime observed at recovery: Hermes distribution `0.20.1`, checkout
  `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`, with preceding local modifications.
- Scope: 143 added / 23 removed source lines. Patch bytes are unchanged by closeout.

This is **not** a clean-upstream patch or a new release of Hermes. The already-dirty
preimage is private; its backup and other untracked runtime files were preserved.
`git apply --check` alone is not a substitute for the full preimage checksum.

## Baseline RED and verified GREEN

| Check | Result |
| --- | --- |
| Installed pre-repair routing | 4 failed, 1 passed |
| Disposable pre-HLP-211b rollback | all five failed; never installed |
| Recovery/atomicity/concurrency/compatibility | 15 passed |
| Existing affected Hermes tests | 129 passed, 1 Windows-only skipped |
| Existing TUI/gateway notifier tests | 44 passed |
| Same 15 probes against the installed postimage | 15 passed |
| Native same-origin TUI follow-up | PASS; canary retired |

Retained outputs: [baseline](baseline-pytest.md),
[recovery tests](final-canary.md), [affected tests](affected-tests-final.md),
[notifier tests](notifier-tests-final.md), [installed tests](installed-canary.md),
and [activation record](activation.json). These are observations, not generated
expected outputs. Historical pytest paths refer to the original local placement.

The four reproduced failures were: controller omission of the explicit signal,
non-affinity child exhaustion not reaching its controller, root failure before
controller creation, and unresolved attention with heartbeat-only liveness.
The already-working internal repair/resume path remains silent.

## Reproduce without touching production

The standalone regression files live next to the patch:

- [routing probes](../../../../patches/hermes/tests/test_hlp280_live_routing_probe.py)
- [compatibility probes](../../../../patches/hermes/tests/test_hlp280_recovery_compatibility.py)

They require the exact provisioned Hermes source; they are deliberately separate
from the Aether package tests that CI runs on its different public Hermes baseline.
They import real DB/routing functions, not an expected-output generator. Run from
this repository root with `HERMES_PYTHON` resolved to the intended interpreter:

```sh
sandbox=$(mktemp -d)
HERMES_HOME="$sandbox/home" HERMES_KANBAN_HOME="$sandbox/boards" PYTHONDONTWRITEBYTECODE=1 \
  "$HERMES_PYTHON" -m pytest -c /dev/null --noconftest -p no:cacheprovider \
  patches/hermes/tests/test_hlp280_live_routing_probe.py \
  patches/hermes/tests/test_hlp280_recovery_compatibility.py \
  --basetemp="$sandbox/cases" -q -ra
```

The fixture confines SQLite to its own temporary root, suppresses lifecycle
observers only inside the test, and refuses any worker spawn. No live board or
Project DB is used. The attention-expiry tests advance a simulated clock across
300 seconds and run the real dispatcher; they are **not** a live timed measurement.

For reproduction from the exact private preimage, construct a disposable checkout,
verify the preimage checksum, run the baseline probes, apply only this patch, verify
the postimage checksum and rerun. Never overwrite unrelated dirty runtime hunks.

## Qualification corrections and limitations

Before activation, qualification caught a nonexistent `scheduled_at` column and
an event-order incompatibility; the candidate was corrected, not the expected
behavior. Test setup errors involving heartbeat/factory names and the intentional
second-cycle triage were corrected before the final results. Async notifier tests
used a test-only `pytest-asyncio` installation, not a runtime dependency change.

The native gateway was gracefully reloaded and the installed bytes retested.
No TUI, unrelated service, rejected candidate or concurrent owner work was reset.
The production repair stopped at the native canary PASS. This closeout only
packages that exact repair, reconciles its ledger entry and preserves evidence.

This does not qualify arbitrary externally corrupted databases, missing/ambiguous
origin subscriptions, or cross-store exactly-once receipts. Those broader v4/v5
requirements are not silently represented as implemented. Repository CI verifies
Aether compatibility and packaging; it does not replace the local runtime canary.

Release conclusions: `release_impact=patch`, `release_action=defer`,
`release_channel=none`. No tag, release, package publication, deployment or upstream
PR is part of this closeout. [Issue #280](https://github.com/DarkArty07/Aether-Agents/issues/280)
retains the design rejections and the direct-recovery evidence.
