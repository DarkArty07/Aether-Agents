# Unit Evidence: U275R — bounded real-route qualification for image interpretation (TS-275 research gate)

- **Unit:** U275R (research gate for TS-275; repair unit U275F is gated on this outcome)
- **Issue:** [#275](https://github.com/DarkArty07/Aether-Agents/issues/275) — **remains OPEN**; this unit does not close it
- **Objective Contract:** `oc_6176d2be6cb7e6fe@v1`, digest `69765e73e657b7c0854454a4257a43e5f113ed9c4deb9c6559c536b374a5c040`
- **Supervisor breakdown:** `specs/006-tools-memory-stability/tasks.md` at `ef69bdc771821416feb3bb65093d3b70013a54a8` (unit U275R)
- **Review lane:** same-card Supervisor review (`reviewer="supervisor"`)
- **Unit compatibility impact:** `none` — evidence-only research; no product source, configuration, adapter or transport change

**This is a research result, not a fix.** The repair premise returns to Morfeo for a recorded design before U275F is built.

*Revision note:* review round 1 requested four corrections — removal of a private card identifier from the
header, a factual re-scoping of the adapter/transport boundary, a corrected historical window/count, and the
provenance of the production cross-check figures. Review round 2 requested that the historical episode's
non-vision breakdown be stated only as far as the routing product's records reproduce it, and that the
plain-language summary window match the detailed section. All corrections are applied below, and every claim
they touch is re-derived from the sources cited inline.

## 0. Result in plain language

1. **The supported provisioned route does interpret image-only content.** A real invocation through the
   already-provisioned vision tool returned a correct reading of content that appeared only in the image
   (an exact token, two shape colours and the background colour), never described in the question.
2. **The failure class reported in #275 does not reproduce in the current provisioned configuration.** Valid
   small images are interpreted. The historical 400 episode recorded 62 rejected vision requests between
   2026-09-09 17:43:53 and 2026-09-10 03:03:45; 60 of them (2026-09-09 17:43:53 → 2026-09-10 02:21:19) are
   attributable to an upstream gateway requirement (a per-conversation session header) that the separate
   routing product began enforcing and then fixed outside this repository on 2026-09-10, and the remaining
   two (03:03:44/45) are the dimension failure class in item 3. Neither is an image, adapter or transport
   defect.
3. **One residual failure class was reproduced through the real route:** images whose longest side is
   extreme are rejected by the gateway's image *decode* limit, and the fork's auxiliary preparation path
   neither caps that dimension nor retries it. This is the only proven in-repository boundary in this unit.
4. **Byte preservation, tool-call identity, chronology and the public tool interface were not modified**; no
   provider, model, route or credential was changed to obtain any result.

## 1. Source identity and modification boundary

| Item | Observed |
| --- | --- |
| Aether starting revision | `3ce47369165dda9c7df3452730c8caf1ee0a6ca0` (worktree HEAD, clean at start) |
| Contract digest | Re-read from `.aether/objective-contracts/oc_6176d2be6cb7e6fe/v1.md`; matched the assigned digest |
| Maintained fork (repair source) | `DarkArty07/aether-hermes` at `266e412fb83ad32af92ed391db942f88993d76a2` |
| Loaded editable runtime revision | `0b288979e2322c02ab42c05f1e183bb31cfa5aa9` (44 unrelated dirty entries, none in the inspected files) |
| Import resolution | `import tools.vision_tools / agent.image_routing / agent.codex_responses_adapter / agent.transports.codex` resolved to the loaded editable tree, not to a site-packages copy |
| Writable surface used | `specs/006-tools-memory-stability/evidence/TS-275-research.md` (this file) only |

Parity of the inspected surface (SHA-256, first 16 hex digits; live working tree = live `HEAD` blob = fork
blob at the pinned revision), so the compiled/loaded behaviour and the pinned fork source are the same bytes:

| File | SHA-256 (leading 16) | Dirty in live tree |
| --- | --- | --- |
| `tools/vision_tools.py` | `e2892b63cf23498d` | no |
| `agent/image_routing.py` | `318914ecdde9ca8a` | no |
| `agent/codex_responses_adapter.py` | `539dabc336212a0b` | no |
| `agent/transports/codex.py` | `c80c2244db13e76f` | no |

Read-only evidence inspected outside the repository: the loaded runtime's own configuration and logs, and
the routing product's request telemetry (process journal + metrics database, opened read-only). Private
route/model/endpoint identities and machine locations are deliberately excluded here and are retained in the
card's private completion metadata.

## 2. Effective route recovered from the live turn

Routing was recovered by executing the loaded runtime's own resolution functions with the live profile
context — not from shell defaults or an unrelated subprocess reading another profile's configuration:

| Resolution step | Observed |
| --- | --- |
| `_read_main_provider()` / `_read_main_model()` | the profile's configured main provider/model pair for the live turn |
| `agent.image_input_mode` | `auto` |
| `_supports_vision_override(...)` | `null` (no explicit declaration) |
| `_lookup_supports_vision(...)` | `null` (no resolvable capability) |
| `decide_image_input_mode(...)` | `text` |
| `_explicit_aux_vision_override(...)` | `true` |
| `_supports_media_in_tool_results(...)` | `false` |
| `_should_use_native_vision_fast_path()` | `false` |
| `resolve_vision_provider_client()` | client constructed, provider `custom`, resolved model = the profile's auxiliary vision model, base URL = the local routing hop with the role-scoped vision operation/service query |

Consequence: for the provisioned roles the **auxiliary ("legacy") vision branch of `_handle_vision_analyze`
is the effective route**; the main-model native fast path is not selected, so no image is ever placed into a
`function_call_output` in this installation. This is confirmed by the live process log for the baseline call,
which shows the auxiliary prompt prefix (`Fully describe and explain everything about this image…`) rather
than the native branch, and by the routing product recording the request with the role-scoped vision
operation attributed from the request query.

The adapter/transport boundary is therefore **not** bypassed on the executed path, and the pattern is
subtler than "an image never reaches the Responses conversion":

- The *native fast path's* tool-result conversion is not selected: no image is placed into a
  `function_call_output` for the provisioned roles, because that path is not taken at all.
- The auxiliary request, however, **is** delivered as a Codex-Responses call. The provisioned auxiliary vision
  client resolves to `AsyncCodexAuxiliaryClient` → `_AsyncCodexCompletionsAdapter` → `_CodexCompletionsAdapter`,
  whose `create()` converts the chat-shaped vision message through the shared
  `agent/codex_responses_adapter._chat_messages_to_responses_input` (import at `agent/auxiliary_client.py:1481`,
  call at `:1508`) and posts it with `responses.create` (`agent/auxiliary_client.py:1783`). The runtime's own
  traceback for this unit's tall probe runs exactly `auxiliary_client.py:1932 → :1783 →
  openai.BadRequestError` (2026-09-10 17:52:52).
- That conversion is byte-preserving: driving it offline with the vision message shape emits
  `{"type": "input_image", "image_url": <data URL>}` as `input[0].content[1]` — the position the upstream 400
  names — with the decoded payload byte-identical to the source file (SHA-256 match).

Consequence: no adapter or transport change is indicated; the #275 byte-exact conversion check therefore
applies to a live path, which strengthens the rejection rather than resting on an offline-only result.

## 3. Discriminating real invocations through the provisioned tool

Three bounded invocations were made with the already-provisioned `vision_analyze` tool and the existing
credentials. No provider, model, route or configuration change was made; no retry was used to obtain success.
Each fixture is deterministic (regeneration reproduces the exact bytes), lives outside Git, and contains
content that is not described in the question asked.

| Fixture (private dir) | Pixels | Bytes | SHA-256 (leading 16) | Observed result |
| --- | --- | --- | --- | --- |
| `ts275-synthetic.png` (640×360) | 230,400 | 7,699 | `e87e8160439ffd9f` | **success** — exact image-only token, both shape colours and the background colour reported correctly |
| `ts275-tall-800x40000.png` (800×40,000) | 32,000,000 | 185,620 | `9a7641f68b9c352f` | **failure** — HTTP 400, generic client-visible detail; upstream reason: image decode limit exceeded for the `image/png` payload |
| `ts275-square-5000x5000.png` (5000×5000) | 25,000,000 | 92,570 | `ebc32c8d1b8c0385` | **success** — exact image-only token and fill colour reported correctly |

Sanitized observations:

- **Baseline (success).** Tool-level result `success: true` after ~12.5 s; router fact recorded the request
  on the role-scoped vision operation with a single attempt, upstream status 200 and no rotation or backup.
  The returned analysis named the token written only in the image, both shapes and the background — content
  that could not be produced without reading the pixels.
- **Discriminating failure.** Tool-level result `success: false`; the client-visible error was
  `Error code: 400 - {'detail': '<routing product’s generic rejection text>'}` with no size hint. The routing
  product's own log for the same request holds the upstream message naming the *decode limits*, and its
  telemetry recorded one attempt (`attempts=1`, no rotation, no backup) with upstream status 400 in 0.30 s —
  i.e. the fork neither downscaled nor retried, because its only retry branch requires a base64 payload
  larger than 5 MB and this payload was ~247 KB.
- **Second success (25 Mpx square).** Tool-level result `success: true` after ~13.7 s with a 1,582-character
  analysis containing the image-only token; a single attempt on the vision lane with no upstream error
  status. (The routing product labels this stream close `cancelled` with human result "completed"; the
  client received the complete analysis, so this is a telemetry label rather than a functional failure.)

Production cross-check (read-only telemetry, re-sourced from the routing product's own records): the four
dimensions quoted here are local website screenshot files under `website/test-results/visual/` —
`1440-docs-reference.png` 1440×40,528; `390-docs-reference.png` 390×46,026; `1440-docs-walkthrough.png`
1440×6,089; `390-docs-walkthrough.png` 390×9,865 — listed by this environment's profile sessions on
2026-09-09 (20:29, 21:17, 23:24) and 2026-09-10 (03:03, 17:52), and they were the *inputs* of failing vision
attempts, not samples accepted or rejected by the lane. The routing record contains no successful vision
request between 2026-09-09 17:43:53 and 2026-09-10 17:47:25: all 62 recorded rows are HTTP 400. The two
`*-docs-reference.png` inputs are the two 400s at 03:03:44/45 (decode-limit message; journal 03:03:49); the
other six inputs of that batch (sides 4,798–9,865 px) have no metrics row at all — the journal shows their
response headers starting at 03:03:45–47, the router then restarted at 03:04:09 (journal: six running tasks
cancelled) and the client-side tool results were connection errors, so none of them was accepted either.
(Access logs in this stack record the status when response headers are sent, so a journal "200" for a
streaming call means the stream started, not that an interpretation reached the client.) The discriminating
per-side datum therefore comes from the production *rejection* of a 17.95 Mpx image (390×46,026 — smaller in
area than this unit's accepted 25.0 Mpx square), not from any accepted production sample.

## 4. Causal boundary

**Proven**

- The provisioned vision route interprets valid image-only content today (Section 3), so no entitlement,
  credential or provider change is required to interpret an ordinary image.
- The upstream gateway rejects a PNG whose longest side is extreme with a *decode-limit* error. Sides
  observed through the provisioned route: rejected 40,000 px (this unit's probe, 2026-09-10 17:52), 40,528 px
  and 46,026 px (production, 2026-09-10 03:03:44/45); accepted 5,000 px (this unit's 25.0 Mpx square). The
  limit is per-side, not area: the rejected 390×46,026 sample is only 17.95 Mpx, below the accepted 25.0 Mpx
  square, so total pixel area cannot be the operative constraint.
- The fork's auxiliary preparation path applies no dimension cap: `_EMBED_MAX_DIMENSION` /
  `_EMBED_TARGET_BYTES` are used only by the native fast path (`tools/vision_tools.py`, native branch), while
  the auxiliary branch resizes only when the payload exceeds the 20 MB hard ceiling or when a *classified*
  size error arrives **and** the payload is already above the 5 MB resize target. Neither condition is
  reachable for a small-byte, large-dimension image.
- The client-visible detail is deliberately reduced by the routing product to a generic rejection text
  (its own design note: never expose the upstream body to clients). Consequently the fork's size-error
  classifier cannot match the rejection — the text carries no size semantics — so a message-driven retry
  cannot be made reliable from this repository alone.
- The historical 400 episode on this lane, re-sourced from the routing product's own records (source: its
  request metrics filtered to the vision operation; its journal lines for the same window joined to the
  operation named in each request line): 62 vision-lane HTTP-400 rows lie between 2026-09-09 17:43:53 and
  2026-09-10 03:03:45, and one success follows at
  2026-09-10 17:47:25 (this unit's baseline) — 62 of the 63 vision requests recorded up to that point. Sixty
  of the 62 (2026-09-09 17:43:53 → 2026-09-10 02:21:19) carry the upstream message that a per-conversation
  session header is missing; the routing product added it in commit `f9e4e8f` (2026-09-10 02:52) and
  restarted at 02:57:14, and its journal records no session-header 400 after 02:46:38. The remaining two
  (03:03:44/45) are the dimension class of the previous bullet. The session-header class was not
  image-specific: of the 96 upstream rejections carrying that message (journal 2026-09-09 17:29:21 →
  2026-09-10 02:46:38, each joined to the operation tag on its request line), 60 are the vision-lane rows
  above, 23 are web extraction, 1 is title generation and 12 carry no operation tag in either record; no
  goal-judging request carries any rejection status anywhere in the record (77 requests: 71 cancelled, 6
  successful).
  Neither Aether nor the maintained fork is the client of that upstream gateway — the routing product is.

**Not proven / rejected hypotheses**

- An adapter or transport defect in `agent/codex_responses_adapter.py` or `agent/transports/codex.py`: both
  surfaces are executed for the auxiliary vision call — `_chat_messages_to_responses_input` converts the
  vision chat message and `responses.create` posts it (`agent/auxiliary_client.py:1508`, `:1783`; the runtime
  traceback of the tall probe) — and that conversion is byte-exact (`input[0].content[1]` decodes to the
  source image's SHA-256). The observed rejection is the upstream decode limit on the original dimensions;
  no conversion defect is indicated, and the byte-exact check from issue #275 is confirmed on the live path
  rather than being an offline-only result.
- A defect in the routing decision itself: `text` mode is the documented consequence of an undeclared main
  model capability plus an explicit auxiliary vision configuration, not a defect. Changing it would alter the
  configured route and is therefore not a local decision.
- Total-pixel-area limits, image-format limits, or credential/entitlement exhaustion for the failing
  invocations: contradicted by the 25 Mpx success and by the successful baseline on the same lane.

**Still unknown (state plainly)**

- The exact per-side threshold enforced by the upstream gateway (only bounded: accepted side 5,000 px;
  rejected sides 40,000 px, 40,528 px and 46,026 px). The vendor's public attachment documentation describes
  a different pipeline (2,000 px / 5 MB) and does not document this API path's decode limit.
- Whether other provider lanes or models behind the routing product enforce different limits; only the
  role's provisioned vision lane was exercised.
- Whether the gateway's limit is stable over time or configurable by the operator.

## 5. Smallest compatible repair proposal (for the Morfeo design record)

**Boundary to correct (proven, in-repository):** the *preparation* step of the auxiliary vision path in
`tools/vision_tools.py` (`vision_analyze_tool`) can emit an image whose longest side exceeds what the
provisioned backend accepts, and its recovery branch cannot fire for small-byte payloads.

**Recommended smallest change:** apply the policy the repository already implements and reviews on its native
path — the embed cap (`_EMBED_MAX_DIMENSION`, `_EMBED_TARGET_BYTES`) — to the encoded image before the
auxiliary call, i.e. downscale only when the longest side exceeds 7,900 px or the payload exceeds 4 MB.
Properties preserved: image bytes are unchanged for every image inside both caps (the vast majority,
including both images this unit's probes show the route accepts); the public tool schema, tool-call identity
and response chronology are unchanged; no provider, model or route is touched; the change is confined to one
module and is protocol-independent. The cap must sit between the largest side observed accepted (5,000 px)
and the smallest side observed rejected (40,000 px); the repository's existing 7,900 px value lies in that
gap and far below every rejected side, so it is conservative with respect to the unknown exact threshold and
invents no new constant.

**Alternatives considered and not recommended**

- *Reactive retry on the upstream rejection*: the classifier never matches because the client-visible detail
  is generic by design; forcing a retry on any 400 would retry genuinely invalid requests, so this needs a
  routing-product change (a different product, outside this objective) to carry a classifiable reason.
- *Lower the route's limits in configuration or change the auxiliary model*: a route/provider decision, not a
  local implementation choice.
- *Drop or replace the image*: prohibited by the repair envelope (image content must not be globally
  dropped or replaced).

**Explicitly not in scope / not done:** no edit to the routing product, no credential or subscription change,
no provider/model/route change, no change to the adapter, transport or routing-decision modules.

## 6. Runnable pre/post oracle for the repair unit U275F

Run against the maintained fork candidate with its declared runner; the fixtures are generated outside Git.

1. **Fixtures (deterministic).**
   - `ts275-tall-800x40000.png` — 800×40,000 px, 185,620 bytes, SHA-256 `9a7641f6…` (failing case).
   - `ts275-square-5000x5000.png` — 5000×5000 px, 92,570 bytes, SHA-256 `ebc32c8d…` (within-limit control).
   - `ts275-synthetic.png` — 640×360 px, 7,699 bytes, SHA-256 `e87e8160…` (ordinary control).
   Regeneration must reproduce the same bytes (content is fixed; no timestamps).
2. **PRE (expected RED, reproduced in this unit).** Call the provisioned `vision_analyze` with the tall
   fixture and a question that never describes its content. Expected: `success: false` with an HTTP 400-class
   error, a single attempt, no downscale retry. Assert on the tool result, not on prose.
3. **POST (expected GREEN).** The same call must return `success: true` and an analysis that names the
   image-only token written in the fixture (`QUARTZ-77`) and the fill colour. Assert on the content, not on
   the fact that an HTTP 200 was seen: a review-run observation (supervisor round 1, not this unit's probe)
   recorded 200-OK vision responses whose descriptions never read the image, so only the image-only token is
   a valid completion signal.
4. **Preservation controls (must not regress).**
   - The square and ordinary fixtures still return `success: true` with their image-only tokens
     (`MARLIN-31`, `ZEPHYR-42`) and their shape colours.
   - An image inside both caps is transmitted byte-identical: decode the data URL produced for the auxiliary
     call and compare its SHA-256 with the source file (offline assertion; no provider call).
   - The tool schema, its argument names and the JSON result shape are unchanged; tool-call identity and
     response ordering are unaffected.
5. **Fork regression anchors.** `tests/tools/test_vision_tools.py` (existing size/dimension and classifier
   tests, including the tall-small-byte dimension case), `tests/run_agent/test_image_shrink_recovery.py`, and
   the auxiliary-client suites, run through the fork's declared runner with the repository's normal checks.
6. **Negative boundary.** An image *below* the caps must not be resized or re-encoded on the default path
   (no unconditional recompression), and a genuinely invalid local file must still be rejected before any
   provider call.

## 7. Preservation, scope and residue

- Only this evidence file was added; no other repository file was modified in this unit's branch.
- No runtime configuration, profile, credential or provider binding was changed; the routing product was
  read only (journal and metrics opened read-only) and never modified.
- No credential was read or printed; synthetic fixtures and captured correlation metadata live outside Git.
- Unrelated dirty runtime source files and unrelated sessions/boards/worktrees were untouched; the three
  real provider calls are the only external effects, all on the already-provisioned route.

## 8. Publication and remaining risk

No push, PR, merge, tag, release or issue mutation was performed; #275 stays open. The remaining risk is
that the residual failure class above (extreme per-side dimensions) stays user-visible until Morfeo records
the design and U275F implements it, and that the upstream threshold remains only bounded rather than exact —
so the oracle asserts content, and the proposed cap is chosen conservatively inside the observed
accept/reject gap rather than at its edge. The original #275 symptom class (small valid images failing)
could not be reproduced in the current provisioned configuration; a later independent check should confirm
whether the upstream gateway's session requirement or decode limit changes again.
