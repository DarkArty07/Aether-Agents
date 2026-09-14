# Morfeo intermediate direction — origin identity and DELIVER convergence

## Trigger and verified execution history

The owner asked why no terminal result followed a progress report by roughly an hour and forty minutes. Targeted native board evidence for CE-HF-DELIVER (`t_8edf43f3`) shows the following on 2026-09-13, UTC−06. These are execution records, not independent re-runs by Morfeo:

- Run 24: 18:04:42–19:08:45, Supervisor requested changes for repeated wake after lease expiry and route selection with both TUI and Telegram notification subscriptions.
- Run 25: 19:08:55–19:19:52, Implementer exited without a successful lifecycle handoff; runtime recorded `protocol_violation` and retried the same card.
- Run 26: 19:19:53–19:46:58, Implementer supplied the second candidate and review handoff.
- Run 27: 19:47:49–20:14:15, Supervisor requested another correction: the same message's exclusive lease prevented the other platform consumer from collecting it.
- Run 28: 20:14:42–20:38:58, Implementer supplied the third candidate, reporting 615 required tests, 23 focused tests and 102 CORE regression tests.
- Run 29 began 20:39:02; it was still the active review at this inspection. CE-INT had no run; no collaboration PR or runtime adoption was present.

The graph still has six objective cards and twelve previously disclosed synthetic records. The delay above is reviews/rework plus one protocol retry, not twelve new requirements and not CI wait. Historical PASS counts do not establish acceptance of the current candidate.

## Material question found in the review

Supervisor's round-1 and round-2 review notes require `telegram+tui on one root` to produce both a Telegram wake and a TUI collection of the same origin-addressed request. The second correction made those two consumers compete for the exclusive claim.

Morfeo directly re-read plan.md D1/D3/D5 and spec.md CE-01/CE-04/CE-06: the addressed origin is the trusted commissioning session, and unrelated notification subscribers cannot widen that recipient. Multi-surface support is not collaboration fan-out. Requiring successful delivery to both different origins is not an acceptance criterion of this contract. The repeated-wake-after-lease defect is independently relevant and remains required to be corrected.

## Direction and assumption

Decision: clarify D5 in the owning plan, preserving the finalized contract and its exact-origin requirement. Assumption: a root's commissioning origin is singular; additional native notification subscriptions are not a second originating design steward. The clarification does not remove either supported surface or add a fixed review/time budget.

Supervisor must use the existing contract lens to verify one coherent mechanism: trusted origin selection, exclusion of other subscribers, no repeated wake to a still-live addressed origin, and recoverable same-origin delivery after process loss. Both consumer orderings may test exclusion, not mandate two successful wakes. If trusted persisted identity is insufficient for that decision, return the specific interface/design defect to Morfeo with source evidence rather than approximate identity or invent multicast. A real pending/queued lease race must be reproduced and assigned to its owning unit; lexical suspicion or an unrelated stale table label is not a new behavioral requirement.

Keep independent review and required checks. Reuse unchanged, revision-bound evidence rather than restart broad discovery or repeat pre-consumer demonstrations without a changed obligation. Group any remaining material defects into one actionable return; do not approve because elapsed time or a round count was reached. No new state machine, scheduler, schema or owner authority is introduced by this clarification.

## Attribution and limits

This is Morfeo design stewardship, not a Supervisor verdict or product implementation. It changes the owning plan clarification and records the steering decision; it does not edit completed board state, bypass tests, accept a failed criterion or restart the runtime. The latest candidate's claimed results remain attributed to their producers pending review.
