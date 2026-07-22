# R7 Shadow Mode — First Controlled Run

**Date:** 2026-07-21
**Status:** executed; R7 remains active and default-off
**Authority:** observational only; no coordination dispatch or semantic completion authority

## Purpose

Compare one real execution through the existing `talk_to`/Olympus ACP path with the deterministic session correlation predicted by the R7 coordination architecture.

## Controlled actual execution

- Existing path: `talk_to` → Olympus ACP → Etalides
- Project root: Aether Agents repository
- Task: `shadow-probe-1`
- Requested behavior: return one exact marker with no tools or side effects
- Actual Olympus session: `0c4601e3-f66e-4c15-b4ee-2738034afc38`
- Tool calls: `0`
- Technical status: `completed`
- Exact response:

```text
SHADOW_ACTUAL_OK task_id=shadow-probe-1 participant=etalides technical_status=completed
```

The logical Olympus session was closed after observation.

## Shadow prediction and comparison

The R7 observer ran locally over an admitted `HarmoniaPlan`. It did not call ACP, mutate a ledger, activate the gateway, or claim semantic completion.

```json
{
  "enabled": true,
  "assignment_agreement": true,
  "participant_agreement": true,
  "session_agreement": false,
  "status_agreement": true,
  "mismatches": ["session_mismatch"],
  "predicted_session": "d85b8449-5ba0-501e-8170-5e1342424e1e",
  "actual_session": "0c4601e3-f66e-4c15-b4ee-2738034afc38",
  "semantic_complete": false
}
```

## Interpretation

The first shadow run agrees on task assignment, participant, and technical completion. It deliberately exposes one integration mismatch: the current MCP `talk_to(open)` path allocates an Olympus session ID, while the proposed runtime adapter derives a deterministic ID from project root, task, and participant. The shadow observer correctly detected this instead of masking it.

This is not evidence that Olympus failed. It identifies the compatibility seam R7 must resolve: either carry the deterministic correlation into the existing open path or persist an explicit mapping between coordination identity and the actual Olympus session. Olympus remains the sole lifecycle owner in either design.

## Safety result

- Gateway/runtime activation: **not performed**
- Live configuration mutation: **not performed**
- New coordination dispatch: **not performed**
- Ledger mutation: **not performed**
- Semantic completion assertion: **false**
- R8/pilot/release: **not started**

## Correlation correction and second controlled run

R7 now represents the compatibility seam explicitly as an immutable, read-only correlation:

```text
coordination session 8fa7d7b5-d4e9-54dc-93f2-5f1ee6058f3d
    ↔ Olympus session d336cf7b-6be9-44be-8e0e-08ad669fb8c1
```

A second zero-tool Etalides execution returned:

```text
SHADOW_CORRELATED_OK task_id=shadow-probe-2 participant=etalides technical_status=completed
```

The correlated comparison passed every technical dimension:

```json
{
  "assignment_agreement": true,
  "participant_agreement": true,
  "session_agreement": true,
  "status_agreement": true,
  "mismatches": [],
  "semantic_complete": false
}
```

The mapping does not replace or rewrite the actual Olympus ID. Olympus remains the lifecycle owner; coordination keeps a separate deterministic identity and a checked association to the observed session.

After independent review found that the first mapping still trusted caller-supplied IDs and merely allowlisted statuses, the evidence path was hardened. The final comparison now:

- reads the actual session and final assistant turn through OlympusDB's public read APIs;
- verifies session ID, Daimon profile, canonical project root, task marker, participant marker, and exact persisted status;
- signs the resulting process-local evidence and rejects altered or caller-only observations;
- requires explicit expected project, contract, generation, and technical status;
- authenticates the generated report and rejects direct/altered report objects;
- prevents one actual Olympus session from being borrowed by another task in the same process;
- canonicalizes root aliases and rejects non-finite latency values.

The second real session was re-read from `home/.olympus/olympus_v3.db`; the authenticated comparison reproduced all four agreements with no mismatch, a verifiable report signature, and `semantic_complete=false`.

After the exact-envelope correction, a third controlled zero-tool run returned exactly:

```text
AETHER_SHADOW_V1 task_id=shadow-probe-3 participant=etalides technical_status=completed
```

Olympus session `0f75fe3f-5a5e-4c16-b054-5446ae488ea3` was then re-read through the final evidence producer. Assignment, participant, correlated session, and expected status all agreed; mismatches were empty, the report signature verified, and `semantic_complete` remained false. The deterministic coordination ID was `37b2d78d-2566-55db-9d14-4453df20b420`; the separate actual Olympus ID was preserved unchanged.

## Failure and recovery matrix

Executable tests cover these fail-closed observations without producing effects:

- duplicate delivery;
- runtime unavailable or lost;
- stale generation;
- reviewer-independence violation;
- exhausted budget;
- restart with coordination disabled;
- correlation tampering across task, participant, predicted ID, and actual ID.

Each adverse condition remains observational, makes technical agreement fail closed where applicable, and can never set `semantic_complete=true`.

## Next R7 gate

Run consolidated validation and independent risk review over the complete R7 shadow equivalence class. Do not activate the live runtime before those gates pass and a separate user authorization is given.
