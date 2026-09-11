# Morfeo receipt — TS-275 research-to-design checkpoint

Contract `oc_6176d2be6cb7e6fe@v1` remains unchanged, digest
`69765e73e657b7c0854454a4257a43e5f113ed9c4deb9c6559c536b374a5c040`.
This is a reserved technical design decision, not a product fix or final acceptance.

## Evidence attribution

- Approved research exact revision: `9245d435410eb23cf5a2f0fd29add94cc8c1f20e`,
  `evidence/TS-275-research.md`; Supervisor's round-3 contract-lens review accepted
  the route/source evidence, historical attribution, three real invocations and
  their image-only oracles. That live evidence is REUSED, not rerun by Morfeo here.
- Morfeo independently inspected the native and auxiliary preparation branches,
  constants, CPU executor, normalization/crop order, scale disclosure and resize
  helper at maintained fork `266e412fb83ad32af92ed391db942f88993d76a2`.
- Morfeo independently exercised the existing resizer with both existing caps on
  the three original research fixtures, whose complete input hashes were verified:
  tall input becomes 100×5,000 with its scale metadata; square/ordinary controls
  preserve decoded image bytes exactly. Exact observations and hashes are in
  `TS-275-design.md` V4. This is offline feasibility evidence, not a live candidate.

## Decision and routing

`plan.md` and `spec.md` now declare TS-275 build-ready and reference
`TS-275-design.md` V1-V5. The repair is confined to proactive auxiliary preparation,
reusing existing caps/resizer; no route/provider/transport/header change or generic
400 retry. Within-bounds byte fidelity and real image-only interpretation remain
required. Deliberate oversized-input normalization is the reserved v1 preparation
choice, not a general permission to replace image content.

No v2 or alternate board is created: the original scope, authority, acceptance and
finalized contract bytes remain intact. U275F resumes only after consuming this exact
committed checkpoint. Implementation, independent review and runtime qualification
remain owned by the existing pipeline.

The earlier attempted configured knowledge update after the TS-382 design timed out
without a successful receipt. No graph-maintenance success is claimed and it is not a
precondition to this routing; current source/artifact inspection remained available.
