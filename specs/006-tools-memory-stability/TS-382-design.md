# TS-382 design checkpoint — bounded, atomic transcript publication

Decision owner: Morfeo, exercising the owner's delegated reversible technical design
for Objective Contract `oc_6176d2be6cb7e6fe@v1`. Status: **build-ready for U382F**.
This fulfills the research gate already required by v1; it neither supersedes v1 nor
changes issue scope, acceptance, release action, testing authority or protected edges.
The finalized v1 bytes/digest and existing execution board remain unchanged.

## Evidence and chosen boundary

Approved research: `26f0a885287cb380d12c92d13ede992f2dcd6f7c`,
`specs/006-tools-memory-stability/evidence/TS-382-research.md` and
`fixtures/ts382_transcript_replacement_oracle.py`. Fork repair base:
`266e412fb83ad32af92ed391db942f88993d76a2`.
Morfeo independently ran the unchanged oracle against that fork in isolated temporary
state: **2 failed, 8 passed**; only the legacy append/long-transaction cases failed;
measured longest publication transaction 2.465 s against the fixture's 1.0 s budget.
This confirms the causal class, not the unavailable historical holder identity.

Decision: bound `archive_and_compact`, covering in-place compaction, proactive prune
and gated micro-compaction through that shared writer. Stage expensive FTS inserts in
small committed batches; publish with one metadata-only cutover. Moving serialization
alone, savepoints within one transaction, timeout increases and in-place destructive
edits of the original messages are rejected. `replace_messages` and rotation are not
silently redesigned by this patch.

## D1 — Existing store, durable ownership, no schema migration

Use only the existing SQLite database and its `messages`, `sessions`, `state_meta`
and existing ownership records. No new table/column, schema-version change, attached
store, queue, service, global reaper, live maintenance or migration is authorized.

A publication has a unique opaque generation/owner token and a hidden staging session:
- internal source `hermes-compaction-stage-v1`, `hidden=1`, `archived=1`;
- a reserved random staging id, never the target id, with no parent/lineage link;
- minimal internal `model_config` marker containing version, target id and owner;
- no inherited title, cwd, provider configuration or real-session counters.

Durable per-target ownership lives in one existing `state_meta` entry. Key:
`hermes.compaction.publication.v1:` followed by SHA-256 of the exact target session id.
Value is a versioned JSON object: `v`, `target`, `stage`, `owner`, `expires_at`,
`watermark`, `source_digest`, `phase`, `staged_rows`, `staged_tool_calls`, and
`tail_watermark`. Marker contents are private local runtime metadata, not public logs.
Create/claim/renew/release it with compare-and-set predicates in `_execute_write`.
Use the native structured holder convention and its dead-local-process test; use the
existing compression-lease duration (300 s), renewed only by the exact unexpired owner
in each successful batch. A reclaimed owner cannot stage, clean another owner's data,
or publish. Unknown/malformed ownership is an explicit conflict, never adopted.

This is a per-operation marker in the existing store, not a second admission system
for turns. In particular, **do not acquire a new target compression lock just to stage**:
`append_message` enforces that lock and doing so would prevent the very concurrent
append the oracle requires. Preserve native compression/turn-lease enforcement;
do not steal, release or extend those leases. An in-place compressor that already owns
a compression lease passes its existing `_lock_holder` through a private optional
argument and the writer verifies it inside each batch/cutover. A different live
compression holder is not borrowed by a prune or micro-compaction. Calls without an
existing compression lease remain possible and are serialized only against another
publication of the same target, not against ordinary append operations.

## D2 — Snapshot and visibility

Capture a stable target-prefix snapshot before computing the replacement when the
native caller can supply it: target identity, largest stored row id (watermark),
row count and digest of the exact persisted row values. This private snapshot is not
model-supplied identity or a durable copy of transcript content. The existing
`archive_and_compact(session_id, messages, model_config_patch=None)` call shape keeps
working; optional keyword-only native context may carry the snapshot/known holder.
Without that context, capture the snapshot at method entry. Native caller adjustments
must be feature-detected so duck-typed third-party stores still receive the old call.
No explicit source snapshot may be silently replaced with a newer one after a conflict.

Prepare replacement row values outside the SQLite writer transaction, preserving the
current serializer's handling of content, reasoning, tool calls, timestamps,
`api_content`, display metadata and every stored message field. Work on private copies:
caller dictionaries and `_row_id`/persisted markers change only after successful commit.
Keep `_insert_message_rows(conn, session_id, messages)` as the exercised insertion seam
with its existing positional shape; use a private prepared-row representation, not an
untrusted dictionary flag, to avoid repeated encoding inside the writer transaction.

Staged messages are committed under the staging session with `active=0, compacted=0`.
If the existing insert seam initially sets `active=1`, flip flags before that batch
commits; no reader may observe that intermediate state. The target's visible transcript,
archive, counters and config are untouched during staging. Internal staging sessions
and their messages are excluded from public session listing, counts, transcript/export
and search surfaces, including explicit inactive/hidden modes; internal cleanup uses
private SQL, not an API that exposes a staging session as a conversation. Do not hide
ordinary user rewind/history rows. Default search exclusion by flags alone is insufficient
for the explicit inactive case. Test both legacy-inline and external-content FTS.

## D3 — Concrete batch and fairness policy

Initial limits: **128 rows and 512 KiB of prepared serialized values per transaction**,
whichever is reached first. A single already-supported oversized row is processed alone,
without truncation or a new rejection limit. Such a row is not a universal latency claim;
measure the largest relevant supported input and return to Morfeo if it reproduces the
original failure rather than declaring acceptance through a size assumption.
Release both SQLite's writer lock and the instance lock after every batch; yield **10 ms**
outside both locks before taking another batch. These are internal constants, not new
user configuration. Preserve the original routine/transcript patience budgets, jitter,
FTS high-water mark, checkpoint mode and existing trigger definitions.

All staging, tail-copy and cleanup batches follow these limits. Every batch verifies
exact target/generation ownership and updates its durable count/phase atomically with
its rows. A transaction exception rolls back that batch. The instance's actual lock is
non-reentrant (`threading.Lock`): never hold it around a nested `_execute_write` call or
around the entire publication. Same-instance and separate-instance writers must both
get opportunities between batches.

## D4 — Concurrent appends and stable ordering

Insert the prepared replacement in its original order. Never change an existing message
row id or allocate ranges by editing `sqlite_sequence`: FTS document ids and message
references must stay valid.

Target rows above the source watermark that arrive while staging are not part of the
summarized-away prefix. Preserve them byte-for-byte and exactly once after the replacement.
Because their ids can interleave with staged ids, copy the interleaved tail into the
staging session in original id order, in bounded batches, after the replacement rows.
Track the exact original tail cutoff and corresponding staged copies in the generation.
Repeat catch-up for newly interleaved target rows. Target tail rows whose ids exceed the
last staged id can remain in place: their order is already after the entire staged set.
Never copy a tail row twice or deduplicate distinct messages by text or tool-call name.

At successful cutover, summarized prefix originals become `active=0, compacted=1` and
remain searchable; originals that were only relocated as concurrent tail become
`active=0, compacted=0` (recoverable but not duplicated in default search); unrelocated
tail remains active. Staged replacement and copied tail become the new active rows.
The final live order is exactly replacement -> concurrent tail in original append order.
Counters/return count include both copied and untouched tail, with exact tool-call counts.
A tail appender's already-persisted row must never be lost because compaction finished;
exercise subsequent flush/resume and message/reference handling, not only a row count.

Permit at most **8 catch-up/final-validation rounds** per publication. Continuous
same-session mutation or an invalidated source prefix causes an explicit publication
conflict: retain complete original history plus every committed append and let the
existing caller's keep-original/error path handle it. Do not spin, extend timeout,
restart publication indefinitely, or turn a failed compaction into a failed append.

## D5 — Final validation and one atomic cutover

Precompute/validate the source-prefix digest, staged ownership/counts and tail plan
outside a SQLite writer transaction on the same writer connection. Fence that validation
against concurrent writers with that connection's `PRAGMA data_version`: read it before
and after validation, acquire `BEGIN IMMEDIATE`, and require the same value before any
mutation. No external commit may slip between validation and publication. Do not compare
values from different connections. Morfeo verified the primitive in isolated SQLite:
an intervening external commit is visible after `BEGIN IMMEDIATE`, while a stable version
remains equal. This is a primitive check, not qualification of the complete algorithm.

Local writes on the same connection must not interleave between validation and BEGIN.
Selected mechanism: a private publication-cutover callable can provide a pre-BEGIN
preflight recognized by `_execute_write`, run under its existing instance lock before
BEGIN, then check the version within its normal transaction callback. Ordinary writer
callables and the existing `_execute_write(fn, patience_s=None)` signature/behavior stay
unchanged. This avoids a nested non-reentrant lock and preserves the oracle seam.
The preflight must not write, commit, recurse into `_execute_write`, retain a cursor,
or hold SQLite's writer slot while serializing/hash-validating the transcript.

The cutover callback rechecks generation/lease/target existence, source and staged count
identity, and the validated tail cutoff, then only performs metadata operations:
1. archive the proven source prefix and hide the exact relocated-tail originals;
2. move the exact staging generation's rows to the target and activate them;
3. keep any validated later, unrelocated tail active;
4. reconcile live message/tool counts and merge `model_config_patch` against the CURRENT
   target config (`None` removes its key), preserving unrelated config updates;
5. remove the empty staging session and the exact operation marker.
All five happen in one transaction or none happens. Do not modify content/role/id in
this transaction or rebuild FTS; the inspected trigger column lists permit these
metadata changes without repeating the expensive indexing. Verify that assumption
against both candidate layouts rather than relying on comments.

## D6 — Failure, crash and cleanup

Before cutover commits: propagate real errors, retain the target's old transcript,
archive/config and counters except for independently committed appends, restore any
caller-owned bookkeeping, and keep staged text invisible. Best-effort cleanup may delete
ONLY this exact generation's hidden rows/session/marker in bounded batches. Cleanup
failure must not hide the original exception; retain a typed `cleanup` marker so the
remaining generation is identifiable. Never sweep arbitrary `active=0, compacted=0` rows.

Crash recovery is lazy and target-local: the next publication for that target checks the
operation marker and may reclaim only an expired/dead-owner generation with validated
source/id/marker agreement. Delete that generation's hidden rows in bounded batches,
then its empty internal session/marker. A fresh/live owner is never reaped merely by age
or a different caller. No open-time full-store sweep, cron, vacuum or background service.

After cutover commits: the new view is authoritative. No fallible cleanup, callback or
compensating rewrite may restore the old view or falsely claim a database rollback.
A crash before acknowledgement can leave the complete new view; a later caller must
reread it, and an explicitly stale source snapshot is rejected. This is atomic durability,
not a new cross-crash exactly-once acknowledgement protocol.

## D7 — Implementation scope and non-negotiable verification

Writable fork surfaces: `hermes_state.py`, `hermes_state_search.py`, adjacent state helpers
(a focused private `hermes_state_compaction.py` is allowed), narrowly required packaging
registration for that helper, affected `tests/state/*`, and the three native caller
sites in `agent/context_compressor.py` / `agent/conversation_compression.py` only for
snapshot/holder propagation and success-vs-failure bookkeeping. Do not rewrite compression
policy, thresholds, summarization, rotation, session schemas or unrelated modules.
Aether unit output remains its assigned `evidence/TS-382.md`; Supervisor owns integration
and the patch ledger. Naming/equivalent helpers inside this design are local freedom;
changing the ownership, visibility, transaction, tail or rollback semantics returns to Morfeo.

Run the approved research oracle UNCHANGED at base and candidate, then add deterministic
barrier/fault-injection coverage beyond its sampled-read checks:
- same and different session/connection concurrent appends; actual BEGIN/COMMIT timings;
- complete-old/complete-new reads; staged content absent from all public query variants;
- ordered, exact-once interleaved tail and later untouched tail; all message sidecars,
  counters, model patch, row-id/flush bookkeeping and resumed transcript verified;
- exception in preparation, each stage boundary and cutover; old state remains intact;
- process death after a committed chunk, lazy bounded reclamation, and no damage to
  ordinary rewind rows or another generation; crash after commit exposes complete-new;
- concurrent publisher exclusion, stale/expired owner rejection, prefix rewrite/edit,
  target deletion/closure and lease reassignment; no stolen or extended native lease;
- pre-BEGIN external commit and same-instance write races; no non-reentrant-lock deadlock;
- bounded conflict exit under continuous tail activity, with every append retained;
- every automatic caller, including unconfigured micro-compaction, inherits the writer
  bound and only stamps persistence/rearm markers after a successful publication;
- original state/writer/static checks, unchanged budgets/FTS definitions and no live DB access.
The source-level fix, independent review and integrated/runtime acceptance are still pending.
