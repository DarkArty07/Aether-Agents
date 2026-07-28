# v0.19.x Incremental Kernel Migration — Roadmap Closeout

**Status:** CLOSED

**Date:** 2026-07-27

**Final implemented boundary:** v0.19.5

**Architecture verdict:** `VIABLE — BOUNDED`

**Candidate head:** `e8b287b`

**PR:** #113 remains draft; merge and release are not part of this closeout

## 1. Closed question

This roadmap asked whether Aether could replace Hermes' routine hub-and-spoke coordination with a durable kernel while retaining Hermes as the user-facing strategic authority and ACPManager as lifecycle owner.

The answer is **yes for the demonstrated bounded topology**.

The final real path executed:

```text
one immutable contract submission
  -> real Hefesto source task
  -> verifier-owned source evidence and cleanup
  -> kernel-derived bounded eligibility projection
  -> deterministic Harmonia task-only proposal
  -> kernel revalidation and CAS commit
  -> immutable contract resolves Daedalus
  -> real Daedalus successor consumes source evidence
  -> verifier-owned successor evidence and cleanup
  -> zero routine Hermes relay and zero survivors
```

Canonical evidence is recorded in `V0.19.5_GATE_C_EVIDENCE.md`.

## 2. Increment disposition

| Increment | Final disposition |
|---|---|
| v0.19.0 | Frozen baseline; did not claim operational replacement. |
| v0.19.1 | Implemented the real server-owned single-task kernel composition seam. |
| v0.19.2 | Implemented verifier-bound trusted result evidence. |
| v0.19.3 | Implemented semantic closure and ACPManager-owned cleanup; later live paths exercised the corrected lifecycle. |
| v0.19.4 | Validated a real fixed two-agent handoff with zero routine Hermes relay. |
| v0.19.5 | Validated real bounded deterministic next-task selection and semantic successor consumption. |
| v0.19.6 | Closed without a separate patch. Its formal viability decision is satisfied by the v0.19.5 deterministic fault matrix, fail-closed live corrections and final real Gate C; no additional pilot is pending in this roadmap. |

Chris explicitly requested roadmap closeout after the bounded architecture verdict so work can move to another topic in the same project. v0.19.6 is therefore not an unfinished implementation item.

## 3. Final bounded verdict

`VIABLE — BOUNDED` means the evidence supports:

- one contract submission by Hermes;
- zero routine Hermes result relays after admission;
- zero Hermes successor/worker selections after admission;
- kernel ownership of eligibility, commit, dispatch authority, evidence and closure transitions;
- ACPManager ownership of real Daimon lifecycle;
- deterministic CAS winner selection;
- immutable worker resolution from the contract;
- no hidden retry, second selection or legacy fallback;
- trusted semantic source-to-successor handoff;
- fail-closed behavior during live-discovered isolation and lease defects;
- final cleanup with zero attributable survivors.

The verdict remains limited to one source, two candidate successors and one sequential selected successor. It is not a general production-readiness claim.

## 4. Explicitly deferred from this roadmap

These are not unfinished v0.19.x deliverables:

- arbitrary DAG, fan-out, fan-in or broad parallel scheduling;
- open-ended planning or arbitrary task creation;
- LLM/model-driven Harmonia selection;
- dynamic worker substitution or task-worker matrices;
- repair/retry policy after a committed selection;
- multi-project load and long-duration soak testing;
- production migration or global Harmonia activation;
- replacement of Hermes as strategic/user-facing authority;
- resolution or mutation of the preserved historical R8 Snake pilot.

Any of these requires a new, separately approved roadmap.

## 5. Open engineering records

Roadmap closure does not conceal framework issues:

- #108 — continuity curation schema defect;
- #114 — clean-checkout CI correction remains open until merged to `main`;
- #115 — continuity foreign-key error handling;
- #117 — isolated ACPManager observability DB correction, validated on this branch;
- #118 — contract-sized dispatch fence correction, validated on this branch;
- #119 — ACP stdio asynchronous-generator shutdown warning after successful cleanup.

Issues #117 and #118 are corrected and Gate C-validated but remain open until their commits reach `main`. Issue #119 is residual technical debt and did not leave a logical or OS survivor in the accepted run.

## 6. Publication boundary

This closeout is a versioned technical and architectural boundary only. It does not:

- mark PR #113 ready;
- merge any branch;
- create a tag or GitHub Release;
- deploy or publish;
- enable Harmonia in live configuration;
- modify production state.

Those remain explicit external-effect decisions. The next project topic can start without reopening this roadmap.
