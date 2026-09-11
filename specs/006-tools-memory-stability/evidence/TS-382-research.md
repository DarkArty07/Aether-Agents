# TS-382 research — SessionDB transcript-write starvation: causal boundary and pre/post oracle

Unit `U382R` of Objective Contract `oc_6176d2be6cb7e6fe@v1`
(`.aether/objective-contracts/oc_6176d2be6cb7e6fe/v1.md`, digest
`69765e73e657b7c0854454a4257a43e5f113ed9c4deb9c6559c536b374a5c040`) at Aether base
`3ce47369165dda9c7df3452730c8caf1ee0a6ca0`.

**This is a research result, not a fix.** No fork source, configuration, timeout, live
database or runtime was modified. It does not close issue #382. `spec.md` requires the
material premise below to return to Morfeo for a recorded design before `U382F` builds
a repair.

## 1. Exact loaded source / route

| Source | Revision | Role in this result |
|---|---|---|
| Maintained fork `DarkArty07/aether-hermes` | `266e412fb83ad32af92ed391db942f88993d76a2` | inspection + reproduction source (detached read-only worktree) |
| Live editable runtime tree | `0b288979e2322c02ab42c05f1e183bb31cfa5aa9` + 44 uncommitted files | evidence of what the incident actually executed |
| Aether execution base | `3ce47369165dda9c7df3452730c8caf1ee0a6ca0` | this unit's base |

File identity was resolved by content hash, not by HEAD label. **All five state modules
are byte-identical between the fork revision and the live runtime's working tree**, so
the incident runtime and the repair source execute the same state-store code:

| File | SHA-256 (both trees) |
|---|---|
| `hermes_state.py` | `3047eef4ebeff82e54334f6d4b3f4566ce48f9efd3f729bf11b838e4a280f834` |
| `hermes_state_common.py` | `8df339f003a38df135301759cc18d4f43af831a83d103b2a388d949371aef9ca` |
| `hermes_state_schema.py` | `21247aee55bcb18fbd4f7795402c86e6316b8565f18b45cf4b1dfbe123a4a3d6` |
| `hermes_state_search.py` | `04ca7657f83756d6b195fa22cc5b9c96dac10d918b1f2130a37c2fb8de47c0ad` |
| `tests/state/test_write_lock_patience.py` | `a45f61bf55e54a1ada9dcacbef6a529fa4309e59a54facd1ddaca2629815c9fc` |

### Write path (one writer, one lock, one budget)

- `SessionDB._execute_write` — `hermes_state.py:3935`; `BEGIN IMMEDIATE` at `:3984`;
  on lock exhaustion it re-raises the storage-busy message at `:4029-4035`. **Every**
  write in the process serialises through this function and through the SQLite write
  lock; budgets are `_WRITE_PATIENCE_S = 20.0` (`:3103`) and
  `_TRANSCRIPT_WRITE_PATIENCE_S = 60.0` (`:3104`).
- `append_message` — `:9063`, transcript-critical write at `:9203-9205`.
- `append_messages_batch` — `:9207`; explicitly *chunked* (`chunk_rows`) with the
  recorded rationale at `:9234-9241`: a 10k-row copy "would monopolize the write lock
  and starve concurrent writers".
- `_insert_message_rows` — `:9530` (shared row-serialisation for every bulk writer;
  per-row JSON encoding/scrubbing run *inside* the caller's transaction).
- `replace_messages` — `:9623` (transaction `:9667-9706`): rewind/edit/retry/compress/
  fork/import rewrites.
- **`archive_and_compact` — `:9723` (transaction `:9755-9795`)**: soft-archives every
  live row (`:9772-9776`) and re-inserts the published set (`:9777-9779`) in one
  transaction. Automatic callers:
  - in-place compaction — `agent/conversation_compression.py:3419-3426`;
  - **proactive tool-result prune — `agent/context_compressor.py:3758-3764`**
    (`prune_tool_results_only`, `:3665-3776`), whose `pruned_msgs` is the *entire live
    message list* with old tool results rewritten — not just the changed rows.
- Maintenance writers with their own bounds: `_try_incremental_merge_fts`
  (`hermes_state_search.py:82`, 1000-write cadence, bounded `merge` commands — the
  unbounded `optimize` was already removed, `hermes_state.py:3126-3140`),
  `_try_wal_checkpoint` (`:4287`, PASSIVE), `optimize_fts_storage`
  (`hermes_state_search.py:747`, opt-in, chunked + throttled engine at `:4392-4424`),
  `vacuum` (`:12438`), `maybe_auto_prune_and_vacuum` (`:12491`).
- Open-time rebuild paths: `_rebuild_legacy_fts_indexes` (`hermes_state_schema.py:340`),
  `_recover_stale_fts` (`:390`), `_init_schema` (`:834`, legacy branch `:1266-1281`).

## 2. Discriminating failing scenario with sanitized observation

### Live-store shape (read-only metadata only; no content, ids or payloads)

The affected profile store (the profile whose sessions failed, and the only profile
with the prune trigger configured) is a **legacy inline-FTS** install:

- 10,882,012,992-byte `state.db` (page_size 4096 × page_count 2,656,302) with a
  67,108,864-byte WAL; max message id 776,912; 758 sessions.
- `messages_fts` / `messages_fts_trigram` are inline `fts5(content)` tables with
  **776,917** stored copies in `messages_fts_content` — i.e. each row's
  `content || tool_name || tool_calls` is stored *and* indexed in two indexes. The
  historical rows before the Aether #305 high-water
  (`aether_legacy_fts_tool_full_content_high_water = 692452`) were indexed at full
  length; `fts_optimize_available = 1` shows the store was never migrated to the v23
  external-content layout that excludes tool rows from the trigram index
  (`hermes_state_common.py:478-560`).
- The six `messages_fts*` triggers are present with the #305 8192-character
  tool-content bound and `AFTER UPDATE OF` forms; no CJK objects; no `fts_stale`
  breadcrumb; no `last_auto_prune` / `last_vacuum` markers on any profile store.
- On the session that failed first, the store holds **21,706 rows: 20,660 archived
  (`active = 0, compacted = 1`) and 1,046 live**, distributed over **29 contiguous
  insert runs larger than 50 rows, growing from 59 to 1,801 rows**. Contiguous ids
  mean one transaction (SQLite allocates ids at insert time). Those runs are the
  fingerprint of `archive_and_compact` publications: each publication re-inserts the
  live transcript as a single transaction and archives the previous generation.

### Incident (recurring signature, from the affected profile's own logs)

- 2026-09-10 04:47:10 → 04:48:38: the write lock was held continuously for **≥ 88 s**.
  `append_message` for two different sessions of the same store exhausted its **60 s**
  transcript budget at 04:48:16 and 04:48:38, the second turn ending as
  `session_persistence_failed`; token accounting failed at 04:48:10/04:48:39; the
  lease refresher exhausted its **20 s** routine budget at 04:47:34 and 04:48:25
  ("transient storage contention"), also at 04:43:00/04:43:03.
- Same signature on 09-04 16:23 and 20:46 and on 09-10 00:29, 00:35, 00:39 — all
  ≥ 60 s budget exhaustions; at 00:35:20 the **proactive prune's own commit** failed
  after its 20 s budget ("Proactive tool-result prune DB commit failed; keeping the
  original transcript", `agent/context_compressor.py:3766`).
- The error text raised is exactly the `_execute_write` storage-busy message
  (`hermes_state.py:4029-4035`): "database is locked (another Hermes process held the
  state.db write lock for over 60s …)". It is raised when `BEGIN IMMEDIATE` fails
  against *another connection*: a different process (CLI, cron, kanban worker,
  desktop) **or** another writable `SessionDB` connection in the same process (for
  example the TUI gateway's own store handle alongside an agent's).

### Deterministic reproduction (temporary database, real code paths)

Fixture: `specs/006-tools-memory-stability/fixtures/ts382_transcript_replacement_oracle.py`.
It builds the production store shape (legacy inline FTS + #305 marker, and a v23
external-content store for comparison) with the real `SessionDB`, publishes a
rewritten transcript through the real `archive_and_compact`, and drives a concurrent
append from a second real `SessionDB` connection. Nothing touches live state; the
append budget is *shortened* for the fixture — no product timeout is raised.

```bash
HERMES_FORK_SRC=<fork-checkout> <fork-checkout>/.venv/bin/python -m pytest -q \
  specs/006-tools-memory-stability/fixtures/ts382_transcript_replacement_oracle.py \
  -p no:cacheprovider
```

Observed at fork `266e412f` (three consecutive repetitions of the acceptance test
produced the same failure):

- `[legacy] longest write-lock hold: 2.137 s of 1 transaction` for a 2,400-row
  publication against a 1.0 s append budget → **RED** (repeat runs: 2.137 s, 2.058 s,
  2.074 s — stable).
- The concurrent `append_message` raised
  `sqlite3.OperationalError: database is locked (another Hermes process held the
  state.db write lock for over 1s — likely a long maintenance operation …; the
  database itself is healthy)` — the product's own storage-busy surface, from
  `hermes_state.py:3984`/`:4029`.
- Scale measurements of the same publication path (detached read-only worktree, temp
  DB): legacy inline layout **0.76 ms/row** (400 rows), **0.81 ms/row** (1,200 rows),
  **0.86-0.89 ms/row** (2,400 rows); v23 external-content layout 0.16 s per 1,200
  rows; with the FTS triggers detached **0.06 ms/row** on the same rows (0.58-2.78
  ms/row with them) — i.e. ~90-98 % of the critical section is FTS trigger work, of
  which the injected-preparation saving in item 1 below is the remainder. Python
  preparation is *not* the dominated cost; the transaction length is.
- Negative control (in-fixture and in `tests/state/test_write_lock_patience.py`): a
  0.2 s lock held by a plain SQLite connection is waited out; an append only fails
  when a *product* transaction holds the lock past the budget.

## 3. Causal boundary

**Which writer contends.** An automatic transcript publisher: `archive_and_compact`
(`hermes_state.py:9723-9795`) as invoked by in-place compaction
(`agent/conversation_compression.py:3419`) and by the proactive tool-result prune
(`agent/context_compressor.py:3758`), which is enabled precisely in the affected store
(`compression.proactive_prune_tokens: 48000`, the only profile that sets it). Each
publication is one `BEGIN IMMEDIATE` transaction over the whole rewritten transcript —
hundreds to ~1,800 rows in the affected store — with both legacy FTS insert triggers
firing per row and *no bound at all* on how long the store's single write lock is held.
The same transaction also holds the store's cross-process lock for every other session,
process and profile worker that shares the database.

**Visible symptom.** Every competing writer exhausts its own budget while a publisher
runs: transcript appends fail as `session_persistence_failed` (60 s budget), lease
refreshes and the prune's own commit fail as "transient storage contention" (20 s
budget). The database is healthy; nothing is corrupt; the turn is lost.

**Competing explanations ruled out (with the evidence used).**

| Hypothesis | Verdict | Basis |
|---|---|---|
| Short contention is mishandled | No — short holds are waited out | fixture control; existing `tests/state/test_write_lock_patience.py` |
| Legacy FTS triggers are unbounded and alone explain it | No — the #305 bound is present, but it only truncates tool `content`; the *transaction* stays unbounded | live trigger SQL + high-water marker; measured per-row cost still 0.8 ms/row bounded, on a 776,917-document index |
| FTS `optimize` holds the lock | No — replaced by bounded `merge` commands on a 1000-write cadence | `hermes_state.py:3126-3140`, `hermes_state_search.py:82` |
| WAL checkpoint / close | No — PASSIVE only, cannot hold the write lock | `hermes_state.py:4287-4309` |
| VACUUM / auto prune maintenance | No — never ran on any profile store | absence of `last_auto_prune` / `last_vacuum`; `maybe_auto_prune_and_vacuum` `:12491` |
| Open-time stale-FTS rebuild | No for this store — requires the `fts_stale` breadcrumb or missing triggers; neither exists (all six triggers present) | live schema query; `hermes_state_schema.py:390`, `:1266-1281` |
| Disk pressure caused the lock | Not proven and not needed — no `SQLITE_FULL`, the surfaced error is a lock, and the store recovered without cleanup | incident report + logs |
| "Another conversation" (the generic message's guess) | Not established — the error only proves a different *connection* held the lock; the fingerprint shows multi-hundred-row publish transactions, not single-row writes | section 2 |

**Precision limit (stated, not papered over).** The *identity of the historical holder
instance* is **not recoverable**: no lock-owner snapshot was captured during the
incident, the recovery pass found only read locks afterwards, and the logs record
victims, not the holder. What is established is the causal class, its mechanism, the
store's structural fingerprint, and a deterministic RED. `spec.md`'s research gate is
therefore met as a *class* qualification; the repair must remove the class (an
unbounded single-transaction publication on the shared write lock), not one instance.

## 4. Smallest compatible repair proposal (inside `plan.md`'s envelope)

Envelope from `plan.md` (TS-382): shorten the proven writer critical section while
preserving atomic visible transcript replacement, session/lease ownership, concurrent
append ordering, archived/search semantics, counters, model metadata, error propagation
and rollback; move pure preparation outside the writer transaction where sufficient.

1. **Preparation outside the transaction (necessary, measurably insufficient alone).**
   `_insert_message_rows` performs per-row `_encode_content` / `_scrub_surrogates` /
   JSON dumping inside the transaction (`hermes_state.py:9530-9621`). Moving that into a
   pre-serialised row plan is safe and reversible, but it removes only ~2-10 % of the
   measured hold (0.06 ms of 0.58-2.78 ms per row). It must not be presented as the
   fix.
2. **Bounded staging is genuinely necessary.** The dominant cost is FTS trigger work
   that cannot be moved out of the insert, so the critical section can only be bounded
   by *committing the publication in several short transactions*. A shape that reuses
   existing boundaries without a new queue or store:
   - stage the published rows **invisible** (`active = 0`, `compacted = 0`, exactly the
     rewind marking the read paths already exclude from both the live transcript and
     default search) in bounded chunks, newest-first;
   - publish with **one short transaction**: archive the old live set
     (`active = 0, compacted = 1`), flip the staged set to `active = 1`, apply the
     counter/model-config patch. `active`/`compacted` flips do not fire the FTS update
     triggers (`AFTER UPDATE OF content, tool_name, tool_calls`), so this final
     transaction is cheap; readers observe complete-old or complete-new, never partial.
   - `append_messages_batch`'s `chunk_rows` (`:9234-9241`) and the chunked FTS rebuild
     engine (`:4392-4424`) are the existing in-repo discipline to reuse.
3. **What Morfeo must decide before `U382F` builds it** (these are product semantics,
   not local choices):
   - **staging identity/visibility boundary**: how a staged row is durably identified
     (a new column vs. an in-memory row-id set — the latter cannot answer "what is
     staged" after a crash), and whether staged rows must be invisible to *search* as
     well as to the live load (they are, under `active = 0, compacted = 0`);
   - **crash/cleanup behavior**: staged-but-never-published rows must be reaped (age?
     next publication? open-time sweep?) without ever being mistaken for rewind rows;
   - **ordering**: concurrent appends that land between chunks must remain ordered
     relative to the publication (the publisher's own `message_count` write and the
     turn flush identity set must agree), and the turn lease must keep working across
     the multi-transaction window;
   - **interrupted publication**: an injected failure after the first chunk must leave
     the old transcript visible, counters unchanged and no staged text searchable
     (the oracle's rollback test asserts exactly this and currently passes only because
     the publication is a single transaction).
4. **Also compatible and cheaper to reason about, but a product decision**: publish only
   the *changed* rows (e.g. `UPDATE` the pruned tool rows) instead of re-inserting the
   whole transcript. It shortens the section proportionally but changes row identity and
   the durable-archive guarantee `archive_and_compact` exists to provide.

Nothing here authorises a new global queue, a secondary store, dropped writes, a live
DB migration, unbounded retries, timeout inflation, or a new chunk size chosen locally.

## 5. Runnable pre/post oracle

`specs/006-tools-memory-stability/fixtures/ts382_transcript_replacement_oracle.py`
(fixture, no live state, ~12 s at default scale). The repair unit runs it unchanged:

```bash
HERMES_FORK_SRC=<fork-checkout> <fork-checkout>/.venv/bin/python -m pytest -q \
  specs/006-tools-memory-stability/fixtures/ts382_transcript_replacement_oracle.py \
  -p no:cacheprovider
```

| Test | Assertion | Pre-fix result |
|---|---|---|
| `test_generic_short_lock_is_waited_out` | a 0.2 s generic lock never starves an append | passes (control) |
| `test_replacement_does_not_starve_concurrent_append` | a real append lands within its budget while a publication runs | **RED on the legacy store shape** (`database is locked …`, `hermes_state.py:4029`) |
| `test_replacement_lock_hold_within_budget` | no single publication transaction exceeds the append budget | **RED on the legacy store shape** (2.06-2.14 s > 1.0 s over repeated runs) |
| `test_replacement_preserves_visibility_counters_archive_and_search` | atomic visible replacement (sampled concurrently), counters, soft-archive + archived-row searchability, `model_config` patch | passes; must stay green |
| `test_failed_replacement_rolls_back_visible_transcript` | injected mid-publication failure leaves the old transcript visible, counters unchanged, failed text unsearchable | passes; must stay green |

Scale knobs (`TS382_REPLACEMENT_ROWS`, `TS382_CONTENT_CHARS`, `TS382_APPEND_BUDGET_S`)
exist so `U382F` can re-run at its own scale; the default pair (2,400 rows / 1.0 s)
reproduces the RED on the legacy layout while the v23 external-content layout still
passes at that scale — the production store is the legacy one. **No product timeout is
raised anywhere**: the fixture only shortens the append budget, and the reproduction's
RED is a *bounded transaction*, not an artificial lock.

## Attribution, limits and privacy

- Producer: `U382R` (Implementer, evidence-only unit) on this unit's branch; fixture
  and this record are the only committed artifacts.
- Evidence classes: live-store metrics and incident timings (read-only inspection of
  the operator's live state and logs, sanitized to aggregate numbers); source
  inspection at exact hashes; own measurements in temporary databases.
- Not done here: no repair, no fork edit, no timeout change, no live-DB maintenance,
  no process intervention, no issue comment or close, no push.
- Independent review is pending; nothing in this record is an issue closure or an
  owner-objective acceptance.
