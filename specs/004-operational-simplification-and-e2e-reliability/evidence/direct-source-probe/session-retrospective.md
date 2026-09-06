# HLP-280 session retrospective and recorded cost

## Final disposition

[Issue #280](https://github.com/DarkArty07/Aether-Agents/issues/280) is closed as
completed. [PR #318](https://github.com/DarkArty07/Aether-Agents/pull/318) merged the
bounded recovery and evidence at `c71cb3e024eefd3ad489031a1f36e43ccda83137`.
The [recovery report](README.md), [activation evidence](activation.json), and
[patch integrity proof](package-integrity.json) remain authoritative for what
was actually installed and tested. This retrospective changes documentation
only: it does not reopen the issue, extend the repair, amend project principles,
or qualify the rejected v4/v5 architecture.

## What went wrong

1. **Runtime defect:** some blockers never produced a deliverable origin signal;
   exhausted non-affinity workers missed controller recovery; unresolved attention
   could persist despite fresh heartbeats. The ordinary repair/resume control worked.
2. **Candidate defects:** earlier attempts introduced or retained invalid-state,
   identity, transaction, replay, and concurrency errors. Independent review
   correctly prevented those candidates from being activated.
3. **Scope and orchestration error:** Morfeo escalated repeated patch failures
   into a larger schema/state-machine/receipt redesign without first establishing
   that the original operational failure required all of it. Several contracts
   themselves needed semantic corrections. Structural validation was too often
   communicated as more progress toward a working result than it demonstrated.
4. **Evidence defects:** the v5 generator wrote expected answers from the same
   classifier later tested against them; human design and SQL disagreed; coverage
   excluded requirements when calculating missing cases; historical RED checks
   verified Git-object existence instead of executing the predecessor. These are
   delivery defects, not missing owner intent. Review reports retained in
   [#280](https://github.com/DarkArty07/Aether-Agents/issues/280#issuecomment-5555492443)
   explain the rejection.
5. **Convergence error:** correction budgets and repeated broad reviews turned
   delivery defects into repeated requests for owner decisions. Review provided
   a safety barrier, but the workflow did not converge to a working repair.
6. **Role interpretation error:** Morfeo initially refused the complete direct
   request too broadly, failing to distinguish general product implementation
   from the authorized bounded recovery exception when Aether itself blocks the
   requested route. That interpretation was corrected explicitly.

## Why the direct recovery succeeded

It began with the imported active source and four concrete RED cases plus a
working control, not a generated matrix. The rollback candidate failed all five
controls and was not installed. The focused repair reused existing transactions,
controller attention, dispatcher ticks and native notifications. It introduced
no new tables, migrations, services or runtime dependencies.

Morfeo also made mistakes during qualification: a nonexistent column, event
ordering, and test setup/API assumptions. These were exposed and corrected before
activation rather than hidden by weakening the expected behavior. The final
qualification was 15 focused probes, 129 existing affected tests with one
Windows-only skip, 44 notifier tests, and a native same-origin follow-up turn.

This was a delicate concurrency/lifecycle defect, not a trivial missing field.
However, the final recovery did not need the proposed general redesign. The
later direct success is not a controlled comparison of model capability or proof
that multi-agent work is inherently incapable: its scope was smaller and it
benefited from evidence accumulated during the unsuccessful attempts. Arbitrary
external database corruption and cross-store exactly-once receipts remain outside
the demonstrated result.

## Reusable lesson

- Failed solutions are not proof that a replacement architecture is necessary.
  Reproduce the original failure and distinguish it from defects in proposed work.
- Inspect the actually imported source and schema before designing a repair;
  preserve known-working controls, unrelated local changes and reversible backups.
- Use the route appropriate to the complete objective. Do not fragment architecture
  into purportedly small direct edits; equally, do not refuse authorized bounded
  system recovery merely because normal product implementation belongs elsewhere.
- Expected outputs must be independent of the code being checked. A historical
  reproduction needs an exact source revision, command, exit status and observed
  failure, not a label or existence check.
- Document validation, semantic acceptance, implementation, activation and actual
  delivery are different milestones. A heartbeat is not progress, and a consumed
  notification cursor is not yet a resumed agent turn.
- Stop recovery when the canary passes. Publish the exact repaired bytes with
  explicit limits; do not claim the rejected broader acceptance was satisfied.
- Retain failures and distinguish observation from inference. Do not infer a
  causal model-performance ranking from this session.

These lessons were also added to Morfeo's existing learned procedure
`agentic-work-routing`, reference
`references/direct-recovery-after-pipeline-overextension.md`. That procedure is
subordinate to current owner intent and canonical rules; it grants no new authority.

## Line-change accounting

GitHub PR metadata and the merged patch were measured rather than recalled.

| Surface | Added | Removed | Net |
| --- | ---: | ---: | ---: |
| Actual installed Hermes source, one file | 143 | 23 | +120 |
| Accepted repair PR #318: patch representation, tests, ledger and evidence | 1,001 | 4 | +997 |
| Five preceding contract PRs #307/#308/#309/#311/#314 | 830 | 0 | +830 |
| All six merged PRs through #318 | 1,831 | 4 | +1,827 |

The runtime and repository rows are **not additive**: the repository contains the
textual representation of the runtime patch. Unmerged/rejected generated code is
excluded from shipped LOC, not counted as zero effort. This later documentation
closure is a separate diff, whose final size is reported at its own merge.

## Recorded consumption, not an invoice

The [machine-readable snapshot](session-cost-snapshot.json) was captured at
`2026-09-06T01:17:47.904320+00:00`. It covers this origin conversation, its native
subagent descendants, and causally matched workers for the five contract boards.
Shared Supervisor sessions are counted once, not once per card. Native run/session
bindings and exact task identifiers were cross-checked. There are 32 unique
selected sessions and no selected duplicate session IDs across stores.

| Group | Sessions | Primary recorded API calls |
| --- | ---: | ---: |
| Origin conversation, including direct repair and earlier coordination | 1 | 655 |
| Origin's delegated analyses/reviews | 13 | 203 |
| Supervisor workers | 6 | 339 |
| Implementer workers, including failed/retried attempts | 12 | 1,865 |
| Total primary usage | 32 | 3,062 |
| Separately recorded auxiliary calls (titles/compression etc.) | — | 27 |
| Combined recorded API calls | — | **3,089** |

| Canonical persisted counter, including auxiliaries | Tokens |
| --- | ---: |
| Uncached input | 31,156,632 |
| Cache reads | 742,609,618 |
| Cache writes | 0 |
| Output | 1,796,713 |
| Reasoning, reported separately and not added again | 1,076,164 |
| Canonical total: input + cache read/write + output | 775,562,963 |

Cache reads are repeated context reuse across calls, not that much unique new
text. The source's `CanonicalUsage.total_tokens` does not add reasoning a second
time. Primary session totals and primary per-model usage rows are not summed
with each other; auxiliary `session_model_usage` entries are additional by the
runtime's documented accounting semantics.

**Verified total monetary charge: unavailable.** All 32 selected session rows
have `cost_status=unknown` and no actual USD cost. Stored estimated zeros with
unknown pricing are not evidence of free usage. No token-price conversion,
subscription allocation or provider invoice was fabricated.

Wall-clock time from the origin session start to the repair PR merge was
79,702 seconds (**22 h 08 min 22 s**), including waiting and interruptions. This is
not billed engineering time. The snapshot includes discussion of incidental
#267/#305/#310 and bookkeeping; it cannot isolate the direct-repair fraction from
all earlier turns. Earlier sessions outside this conversation, unpersisted failed
requests, CI/network costs, subscription fees, later documentation work and the
final answer are not included. No-agent milestone scripts contribute no agent
API calls. Private attribution rows and source identifiers are retained locally,
not published in this report.
