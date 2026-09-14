# Collaborative execution — inspected sources and scope rationale

This is source-inspection evidence for the draft in `spec.md`, not proof that the proposed collaboration has run.

## Baselines and ownership

- Aether inspected at `aaeacb211b892b5dd893ecaa4abba7933011d12c`; the installed Aether package resolves to the provisioned runtime checkout at `de0a96826eae4022659aee9d943421e3226ec924`.
- The provisioned Hermes interpreter resolves `hermes_cli`, `agent` and `tools.kanban_tools` from its existing editable installation. That installation has a historical HEAD plus documented local changes; HEAD alone is not a description of its current bytes.
- The maintained fork's remote `aether-main` resolves to `3b81e9d91cc3a0662b910726a44c94ed328b1e90` at inspection. Any candidate must reconcile with the maintained fork and preserve unrelated provisioned changes; no upstream upgrade is requested.
- `docs/authority.md:19-42` assigns role authority to `DESIGN.md`, stage requirements to specs, prompt wording to packaged SOUL resources, procedures to skills, and execution state to the native board. It forbids promoting comments or runtime observations into product authority.

## Normative delta

- `DESIGN.md:79-105` presents design/contract defect return and revised-contract delivery. `DESIGN.md:370` (PD-77) keeps ordinary internal milestones silent to the origin. The new active-stewardship intent needs to distinguish internal Morfeo attention from owner-facing messages rather than silently weakening this boundary in a prompt.
- `specs/r6-protocol-and-communication/spec.md`, FR-602..604, uses the durable board for inter-role work and rejects a second inter-role channel. Collaboration should extend that record, not introduce A2A/MCP/another broker.
- `specs/r7-supervision-and-convergence/spec.md`, FR-714e, and `src/aether_agents/resources/profiles/supervisor/SOUL.md:64` currently route only explicit input/revision or terminal events to the origin. FR-736b and SOUL `:107-111` already require convergence reasoning. Do not duplicate this as a numeric review-round rule.
- `src/aether_agents/resources/skills/objective-contract-design/SKILL.md:59-64` already requires resolving material feasibility before a ready handoff. The earlier suggestion to add generic feasibility wording must be reconciled with this existing procedure, not stacked on it.
- `AGENTS.md:71-79` and `docs/guides/execution.md:101-112` still tie organic observation to open #317. The new owner direction changes disposition, not historical evidence or the meaning of behavioral verification.

## Native comment bridge: demonstrated limitations

Inspected installed `tools/kanban_tools.py:372-448`, especially `inject_new_comments_from_env`:

- Comments are persisted separately; the live injection path is best-effort and worker-task scoped.
- An in-memory `_comment_watermark` is seeded to the existing latest comment on first poll.
- The watermark advances before `agent.steer(note)` returns. This is not durable proof of delivery, reading, response or resolution.
- The current profile's own comments are skipped by profile author string; this does not provide addressed peer-instance routing.
- The wrapper labels fresh comments as coming from “the operator”. Cross-role advice must not be promoted to owner instruction by presentation.

The inspected function is byte-identical to maintained-fork `3b81e9d:tools/kanban_tools.py:448-512` (normalized function-text SHA-256 `6474d52cc2e94d282b8498625353a53e6002533709238f8c3408efbb8bb6cdc1`). These limitations are not merely a stale local checkout inference. Source inspection establishes the control flow, not an observed dropped message in this objective.

`tools/kanban_tools.py:_handle_comment` returns successful comment persistence. It does not itself prove the collaboration was consumed. Adding only advice about `kanban_comment` to SOUL cannot honestly establish the stronger lifecycle requested by #334.

## Independent transport cross-check

The bounded independent source review agrees with the main scope finding: current native collaboration keeps Supervisor active internally while Morfeo receives explicit escalation/terminal signals; this is not proactive intermediate participation by Morfeo.

- `flow_attention` wakes the Supervisor flow controller, not Morfeo. For affinity-bound tasks, origin watchers deliberately admit `origin_signal` and `flow_terminal`.
- The TUI does have a native notification/continuation path in `tui_gateway/server.py`; an earlier blanket claim that TUI lacks automatic wake must not guide this design. Source availability and actual end-to-end exercise remain different evidence claims.
- The comment text retains `c.author`; the problem is the enclosing “operator” framing and its semantics, not a claim that author strings are erased.
- Neither a notification cursor nor an injection return value proves cognitive acknowledgment or action. An attributable answer/resolution needs its own evidence in the existing coordination record.

This cross-check is read-only source evidence. It ran no live wake or collaboration scenario and makes no behavioral qualification claim.

## Existing distribution: reuse, not replace

`src/aether_agents/lifecycle.py:482-493` already lists the three roles and the four relevant canonical procedures. `_materialize_profile_bundle`, `_skill_sources` and the profile install/verify paths already package and materialize their files. Prefer editing these existing resources and using normal activation over creating another plugin/skill loader or private per-profile fork.

Existing tests explicitly separate resource correctness from behavior:

- `tests/test_contract_quality_documents.py:1`, `:65-113`, `:115-170` check document obligations and native resource loading.
- `tests/test_contract_result_review.py:1-59` checks resource boundaries and separation of pipeline completion from owner acceptance.
- `tests/test_observation_packaging.py` and lifecycle tests cover packaged resource identity and preservation.

Those checks are useful and must not be described as proof that agents will intervene appropriately or avoid a future 48-hour incident.

## One-PR boundary

A resource/guide/adoption mitigation can fit entirely in Aether. Full native addressed intermediate participation, recoverable consumption and non-owner peer attribution may require a narrow maintained-Hermes-fork change plus the principal Aether delivery. This is one owner objective, but not necessarily one repository PR. Do not hide this difference or create a parallel runtime mechanism merely to keep the PR count at one.

## Tool limits

Project knowledge and role work-memory returned `PROJECT_UNRESOLVED` for this chat. Direct source inspection continued; no graph result or saved experience was fabricated. Runtime paths, destinations, credentials and local identity mappings are omitted from this public research record.
