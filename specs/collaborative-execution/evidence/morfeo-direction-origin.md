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

## Follow-through after the interrupted tool call

Morfeo verified that direction commit `162a27e1eec35a98d9c838a1cbc01893f4912df4` and its GitHub issue note persisted. No side effect was repeated merely because the readback command was interrupted. The review log subsequently shows reads of that exact owning plan, but this is not a completed verdict.

Targeted source inspection at actual fork candidate `d1d1f9e9f41b72b9178b52bdf5c7ff4a6f40457f` found the shared data gap:

- `hermes_cli/kanban_db.py:5011-5063`, `opt_in_collaboration`, stores `origin_session_id` plus project/contract data, without an exact platform/chat/thread/profile route.
- `tools/kanban_tools.py:1796-1977`, `_maybe_auto_subscribe`, has the native commissioning tuple at creation, but a later notification-subscription row is not independently marked as the collaboration origin. Its API remains boolean and current normal gateway metadata does not generally bind the raw SessionDB id.
- `gateway/kanban_watchers.py:808-860` chooses a unique reachable platform subscription, not a stored commissioning identity.
- `tests/gateway/test_kanban_collaboration_delivery.py:148-150` constructs `opt_in_collaboration(session_id=chat_id)`, making two separate identity namespaces equal in a fixture.

D5 now fixes the shared answer explicitly: persist a runtime-derived `origin_route` in the existing opt-in event and match it before either consumer claims; do not reconstruct provenance from arbitrary subscribers. This retains CE-01/06 and contract v1, but makes the missing material data shape explicit. Morfeo owns this design clarification; Supervisor owns the corresponding bounded scope reconciliation and independent review. No claim that the candidate already passes this corrected oracle is made.

The current fork commit is the exact `d1d1f9e9f41b72b9178b52bdf5c7ff4a6f40457f` returned by Git. A different full hash in Implementer's prose must not be used as artifact identity or evidence.
