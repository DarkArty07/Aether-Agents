# Morfeo receipt — TS-382 research-to-design checkpoint

Contract: `oc_6176d2be6cb7e6fe@v1`, unchanged digest
`69765e73e657b7c0854454a4257a43e5f113ed9c4deb9c6559c536b374a5c040`.
This is the explicitly reserved technical design checkpoint, not a repaired issue,
independent implementation review, or final contract acceptance.

## Premise and verification

- Approved research exact revision: `26f0a885287cb380d12c92d13ede992f2dcd6f7c`.
  Evidence: `evidence/TS-382-research.md`; unchanged oracle:
  `fixtures/ts382_transcript_replacement_oracle.py` at that revision.
- Morfeo independently read the real `archive_and_compact`, `_insert_message_rows`,
  `_execute_write`, lock/lease methods and all three native callers at maintained
  fork `266e412fb83ad32af92ed391db942f88993d76a2`.
- Morfeo independently ran the unchanged oracle against that exact fork in temporary
  state, clearing inherited Kanban identity and setting an isolated Hermes home:
  **2 failed, 8 passed in 72.61 s**. Both failures were the expected legacy contention
  cases; the longest measured publication transaction was **2.465 s** against the
  shortened fixture budget of **1.0 s**. No live database was used.
- An isolated SQLite primitive check confirmed that a same-connection data_version
  fence detects an intervening external commit after BEGIN IMMEDIATE and remains
  equal when no external commit occurred. This does not validate a complete repair.
- Source checks material to the decision: SessionDB's instance lock is non-reentrant;
  appends enforce target compression locks; blindly acquiring that lock for staging
  would defeat the concurrent-append oracle. Both facts are explicitly accounted for
  in the chosen design rather than left for the Implementer to discover as product intent.

## Recorded decisions and disposition

`plan.md` now declares TS-382 build-ready and owns the link to `TS-382-design.md` D1-D7:
existing-store hidden staging + per-publication metadata ownership; 128-row/512-KiB
batches with an outside-lock 10-ms yield; stable source snapshots; exact interleaved
tail preservation; version-fenced metadata cutover; bounded target-local cleanup and
crash semantics; explicit caller/field/lease preservation; runnable acceptance matrix.

The v1 objective, authority, acceptance, testing standard, issue set, board and finalized
contract bytes are unchanged. Thus no v2/alternate board is created: this record fulfills
v1's research gate through the existing continuation. TS-275 remains separately gated
until its research is approved and its own material decision is recorded.

No product source was implemented by Morfeo for this checkpoint. Supervisor retains
unit review, integration and closeout. U382F must consume the exact committed design
before building and return a demonstrated design discrepancy rather than silently
choosing another persistence algorithm.

Knowledge navigation returned INDEX_MISSING for this revision; source inspection was
used instead. No index, dependency, model or profile was installed to hide that limit.
