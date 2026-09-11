# TS-275 design checkpoint — proactive auxiliary-image preparation

Decision owner: Morfeo, under the owner's delegated reversible design for
`oc_6176d2be6cb7e6fe@v1`. Status: **build-ready for U275F**.
This fulfills the payload/preparation decision reserved by v1. No new objective,
provider, authority, contract version or execution board is introduced.

## V1 — Accepted premise and precise scope

Approved research is `9245d435410eb23cf5a2f0fd29add94cc8c1f20e`,
`specs/006-tools-memory-stability/evidence/TS-275-research.md`, sections 2–6.
Its real-route evidence was independently reviewed by Supervisor; Morfeo reuses that
attributed evidence and independently inspected the exact preparation code and existing
resize primitive. No fresh real-provider qualification is claimed by this design record.

The original small-image/session-header episode was repaired outside this repository;
do not reimplement that backend change or attribute it to this unit. The proven remaining
boundary is auxiliary preparation in `tools/vision_tools.py`: a small-byte, extremely
long image reaches the provider without the dimension cap already used on the native
path. A generic HTTP 400 cannot reliably trigger its current reactive size classifier.
The actual auxiliary route uses the Codex-Responses adapter, but that conversion preserves
prepared image bytes and is not the defective surface. Routing/entitlement is not changed.

## V2 — Chosen minimal behavior

In `vision_analyze_tool`, after existing source resolution, supported-format normalization,
optional region cropping and ordinary encoding, but BEFORE constructing/sending the first
auxiliary model request, apply the existing proactive embed policy:

- use existing `_EMBED_TARGET_BYTES` (4 MiB) and `_EMBED_MAX_DIMENSION` (7,900 px);
- byte comparison is on the encoded data-URL length, matching the current native path,
  NOT decoded file bytes or a newly invented pixel-area limit;
- if either the encoded payload exceeds that target or the longest side exceeds that
  dimension, call existing `_resize_image_for_vision` with both explicit caps;
- use `_run_encode_on_cpu_executor` for dimension inspection and resizing, preserving
  its concurrency bound and avoiding synchronous image work on the event loop;
- pass the existing `_scale_info` to the resizer and retain `_build_scale_note` so any
  actual rescale/crop coordinate transformation remains disclosed by the current result;
- the ordinary within-bounds path must not invoke resize or re-encode its image content.

Reuse the native preparation semantics in this same module. A small helper shared by
native and auxiliary call sites is optional local freedom only if it preserves native
behavior; copying the small guarded preparation step is also acceptable. No general media
framework, new retry state machine, image tiling, replacement description, external OCR,
new constants or configuration knobs are requested.

Keep source files immutable. Preserve aspect ratio, orientation, supported media semantics
and source/crop coordinate mapping; do not crop away information unless the caller supplied
`region`. Keep the existing normalization, optional dependency policy, download/confinement
checks and absolute 20-MiB error boundary. Do not silently install/enable a new dependency
or treat unknown/failed normalization as verified cap compliance. If necessary preparation
cannot be performed, retain an honest structured error/capability result, not fabricated
image understanding or a broad retry of every HTTP 400.

## V3 — Byte preservation and transport decision

For already-supported, uncropped images inside both caps, decoded outbound image bytes
must equal input bytes exactly; this includes both successful research controls. Existing
explicit format normalization/cropping retains its own prior contract.
For an oversized image, deliberate normalization by the ALREADY EXISTING resizer is
permitted to make it representable to the provider, preserving image meaning/aspect ratio
and disclosing the scale. This is the v1 reserved preparation decision, not permission to
globally replace/drop image content or weaken image interpretation acceptance. After that
preparation, the adapter must carry its output byte-exactly; no transport rewriting is added.

Do not change the public tool schema/arguments/result keys, task/service attribution,
tool-call identity, response chronology, prompt content, client selection, provider/model,
endpoint, headers, credentials or timeout. Do not change `agent/image_routing.py`,
`agent/codex_responses_adapter.py`, `agent/auxiliary_client.py` or `agent/transports/codex.py`
without a newly demonstrated cause and a returned Morfeo decision. Existing unrelated
classified-size/empty-response behavior remains; no "retry any 400" workaround.

## V4 — Feasibility evidence and limits

Morfeo exercised the EXISTING resizer at fork
`266e412fb83ad32af92ed391db942f88993d76a2` offline, with the research inputs verified by
full SHA-256. With both existing caps supplied:

| Input | Source SHA-256 | Primitive result |
|---|---|---|
| `ts275-tall-800x40000.png` | `9a7641f68b9c352f6eddb4568759d0d952372717dd677230db680a9d6f0fdf3b` | 100×5,000 px; data URL length 18,654; scale mapping retained |
| `ts275-square-5000x5000.png` | `ebc32c8d1b8c038560685ddcc2c45ec70ab523eb9d9d93498f624c8d3c5ca4a5` | 5,000×5,000 px; decoded bytes unchanged; no scale note |
| `ts275-synthetic.png` | `e87e8160439ffd9f8c0ae99d751587140f0c460b2b7ce469a7d5d31e209ea5fd` | 640×360 px; decoded bytes unchanged; no scale note |

These are observed primitive results, not required exact compressed sizes or a completed
repair. In particular, do not force the long image to exactly 7,900 px: that is a maximum;
the existing resizer's bounded steps can choose a smaller result. The upstream's exact
limit remains unknown. Real interpretation of the normalized long image is mandatory.

## V5 — Scope and acceptance

Writable product scope is `tools/vision_tools.py` and its focused vision/preparation tests
in the maintained fork. A focused new test module is permitted, not a new product helper
package. Aether output for U275F remains `evidence/TS-275.md`; Supervisor owns ledger,
integration, publication and runtime adoption. No live source/config edit in this unit.

Use section 6 of the approved research as the unchanged live pre/post oracle. Privately
supplied exact synthetic fixtures are identified above; verify their bytes before use.
PRE is the recorded/rechecked first-attempt decode-limit failure of the long image.
POST must return `success:true` and actually read `QUARTZ-77` and its fill colour through
the already provisioned route. The question must not supply the token or describe the
answer. The controls must continue reading `MARLIN-31` / `ZEPHYR-42` and their colours.
A 200 status, generic acknowledgement, HTTP fixture or altered model is not acceptance.
If resizing removes too much information to satisfy the oracle, return that exact evidence
rather than weaken the oracle or invent tiling/zoom behavior without a recorded decision.

Add offline capture tests at the auxiliary-call boundary showing: long-small-byte inputs
are normalized on the FIRST request; byte-only/dimension-only/both-limit cases; exact-edge
and already-compliant byte preservation; crop-before-cap and correct scale disclosure;
existing invalid-source/confinement failures before model calls; no synchronous event-loop
CPU regression, global 400 retry, temp/source-file leak or cleanup of user originals.
Verify the native branch and encoded chat-to-Responses conversion are unchanged. Run
`tests/tools/test_vision_tools.py`, `tests/run_agent/test_image_shrink_recovery.py`, relevant
auxiliary/adapter suites and touched-file static checks via the fork's declared environment.
Keep missing prerequisites/skips explicit, never silently omit required async tests.

Acceptance, review and scoped runtime qualification remain pending until that actual
candidate evidence exists. Neither this checkpoint nor the historical backend recovery
closes issue #275 or the five-issue objective.
