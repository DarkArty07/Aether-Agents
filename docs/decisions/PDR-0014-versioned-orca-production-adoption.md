# PDR-0014: Versioned Orca production adoption

- **Status:** APPROVED — AMENDED 2026-08-11
- **Date:** 2026-08-09; amended 2026-08-11
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** The placement of former v0.22.0 M6-M12 inside one release
- **Preserves:** PDR-0012 Hermes-Orca authority, PDR-0013 roster policy, ADR-0001 Aether MCP boundary, and all accepted M0-M5.4 evidence
- **Superseded by:** None
- **Current authorization**: Documentation planning and authority alignment only; no source, test, schema, profile, configuration, runtime, model, or spending effect

## Context

The v0.22.0 candidate has already resolved the highest-risk technical uncertainty in the Aether-Orca transition. It qualified the exact Orca 1.4.167 desktop-renderer/public-CLI binding, implemented the default-off Aether MCP foundation, exercised deterministic lifecycle and one/two-worker behavior, and accepted one bounded two-worker Codex 0.147.0 model-backed execution through M5.4.

The former roadmap kept roster qualification, learning datasets, optional-role evaluation, productization, controlled comparison, publication, and post-release activation inside the same v0.22.0 envelope. That mixed three different product questions:

1. Can Aether integrate with and safely control Orca?
2. Can Aether use Orca repeatedly for real work with stable generic agents and repair integration failures?
3. Can Aether migrate its process-specific workflows to Orca without a big-bang cutover?

The product owner initially separated those questions into v0.22.0, v0.23.0,
and a proposed v0.24.0. On 2026-08-11 the owner clarified that v0.23.0 is the
active learning, debugging, and optimization release for Aether MCP itself and
that no v0.24.0 work begins without a later explicit decision. The existence of
a proposed successor roadmap, v0.23.0 acceptance, or v0.23.0 release is not that
decision. The owner also requires real Orca use to begin after the
production-entry gate rather than waiting for every future workflow and learning
capability to be implemented.

## Decision

### 1. v0.22.0 ends at the accepted M5.4 boundary

v0.22.0 is the **Orca Integration Foundation** release.

Its accepted capability boundary contains:

- retirement of Olympus/ACP and the disconnected pre-emptive native core from the candidate source;
- the provider-independent, stdio-only, default-off `aether-mcp` distribution;
- exact project admission, contract, receipt, trace, idempotency, reconciliation, privacy, and cleanup foundations;
- exact Orca identity/catalog qualification;
- deterministic lifecycle, one-worker, retry, messaging, recovery, cancellation, two-worker overlap, handoff, integration, and zero-survivor evidence;
- one bounded two-worker model-backed M5.4 acceptance on the exact qualified binding.

v0.22.0 does **not** claim:

- a registered or callable Aether MCP surface in the live Hermes installation;
- production operation through Orca;
- stable-roster qualification;
- process-specific workflow migration;
- Headless-only Orca support;
- full learning-dataset construction;
- installed-runtime cutover or Olympus retirement from the current live installation.

The former M6-M12 items are moved or split. They are not marked implemented or completed.

### 2. v0.23.0 begins production use and repair-driven hardening

v0.23.0 is **Orca Production Dogfood**.

For this project, production means the local Aether installation and sessions used for real project work. It does not imply a public multi-tenant service, but it does require real repositories, real deliverables, honest effects, recovery, rollback, and user-visible failures.

The first v0.23.0 increment must make the approved Aether MCP operational surface real, register it for the named coordinator installation, bind the exact Orca provider, prove one reversible live Task, and verify rollback. The current v0.22.0 zero-tool package must not be described as already active.

After that cutover gate passes:

- every Aether multi-agent Task uses Aether MCP + Orca as its normal execution path;
- an inability to use Orca becomes a visible `ORCA_INTEGRATION_INCIDENT`;
- the original Task remains blocked while the incident is preserved, reproduced, classified, repaired, and verified;
- the original Task is retried through the repaired Orca path;
- Olympus, `talk_to`, Harmonia, ACPManager, renamed substitutes, dual-write, and silent fallback are forbidden for completing that Task;
- rollback remains a safety mechanism for restoring control and preserving evidence, not permission to continue routine work through the legacy coordinator.

Hermes remains allowed to answer or implement directly when one accountable owner is the correct product choice. Direct work is not a hidden Orca fallback. When Orca itself is unavailable, Hermes may act in break-glass mode only to repair the Aether-Orca path; it must not count direct completion of the blocked multi-agent Task as Orca success.

v0.23.0 also qualifies the retained generic roster—Hefesto, Daedalus, and
Ictinus—and refines personalities and contracts from real observed behavior. A
prompt or SOUL change requires a stated behavioral hypothesis, baseline-relative
evidence, and regression coverage where applicable; prose preference alone is
insufficient.

v0.23.0 additionally owns the Aether MCP learning and optimization cycle. Real
and controlled use must improve tool descriptions, progressive disclosure,
precondition and identity guidance, error/recovery semantics, context cost, and
the ordinary Hermes tool surface when evidence justifies it. The current 15-tool
contract remains the compatibility baseline. An intent-level surface with the
low-level operations retained for diagnostics is a proposal for comparison, not
an approved replacement. No tool is removed, hidden, renamed, grouped, or
deprecated without frozen comparative evidence and an explicit product-owner
decision inside v0.23.0.

On 2026-08-11 UTC the product owner approved the skill-independent cold-start
guidance architecture as design only. The accepted placement is an isolated
Aether SOUL prompt candidate for mandatory lifecycle invariants, intent-oriented
tool descriptions, JSON Schema identity provenance, typed state-dependent
result/error guidance, and repeated cold-session evaluation. Canonical design,
implementation plan, and handoff are
`../releases/v0.23.0/MCP_COLD_START_GUIDANCE_DESIGN.md`,
`../releases/v0.23.0/MCP_COLD_START_IMPLEMENTATION_PLAN.md`, and
`../releases/v0.23.0/MCP_COLD_START_HANDOFF.md`. This decision does not authorize
source/schema/prompt implementation, active SOUL or runtime mutation, model use,
spending, tool removal, integration, release, or v0.24.0 work.

### 3. v0.24.0 remains a preserved, separately gated proposal

The preserved v0.24.0 direction is **Gradual Workflow Migration**, but it is not
an active next version and has no automatic entry from v0.23.0.

Stable archetypes remain generic. Process behavior is composed from versioned Task contracts, skills, tool policy, acceptance criteria, and evidence. Aether does not create a new personality for every framework, file type, or workflow.

Each specific process is migrated independently:

```text
inventory legacy behavior
-> freeze baseline and acceptance
-> design one Orca contract
-> execute a bounded real candidate
-> compare and repair
-> activate only that process
-> prove rollback
-> retire only its legacy path
```

If the product owner later opens v0.24.0, the process order is selected from
v0.23.0 production evidence rather than frozen speculatively. Olympus or another
legacy runtime may be retired only after the required-consumer inventory is
empty, every replacement path is explicit, no hidden fallback remains, and full
rollback is verified.

v0.23.0 acceptance, source publication, accumulated evidence, issue closure, or
the presence of `docs/releases/v0.24.0/ROADMAP.md` does not authorize opening a
v0.24.0 branch, implementing a workflow migration, activating a process, or
retiring a legacy path. Those actions require a later explicit owner decision.

### 4. Former M6-M12 disposition

| Former v0.22.0 work | New disposition |
|---|---|
| M6 stable roster | v0.23.0 generic-agent qualification |
| M7 learning episodes/datasets | minimum privacy-safe diagnostic trace in v0.23.0; full dataset/export program deferred to a separately scoped later version |
| M8 Verifier/Ariadna decision | v0.23.0 evidence-backed optional-role decision |
| M9 productization | v0.23.0 production entry, status, doctor, cleanup, and rollback; further workflow packaging belongs to v0.24.0 only if that proposal is separately opened |
| M10 evaluation | generic-operation evaluation in v0.23.0; per-process evaluation remains in the separately gated v0.24.0 proposal |
| M11 publication | independent release gates for v0.22.0 and v0.23.0; a v0.24.0 release gate exists only if that version is explicitly opened |
| M12 activation | controlled production entry in v0.23.0; broader process cutover remains in the separately gated v0.24.0 proposal |

Full SFT/preference/tool-policy dataset construction, training, fine-tuning, external upload, or model promotion is not silently absorbed by v0.23.0 or v0.24.0.

### 5. Incident repair is part of v0.23.0 product work

Every production integration incident follows:

```text
preserve failure
-> bound and clean only owned resources
-> reproduce
-> classify Aether / adapter / Orca / environment / provider
-> add failing evidence
-> implement the smallest correction in the owning layer
-> verify the correction and affected equivalence class
-> retry the original Task through Orca
-> record the durable operational lesson
```

A direct workaround without retrying the intended Orca path is not evidence that the integration improved. After three failed attempts using the same repair approach, the incident stops with preserved evidence and an explicit blocker rather than an invented PASS.

### 6. Source release, runtime activation, and ongoing operation remain distinct

The sequence is:

1. reconcile and publish the exact v0.22.0 source boundary;
2. freeze the exact first v0.23.0 implementation and activation Task;
3. implement and verify the operational control surface offline;
4. separately authorize and execute the named local cutover;
5. use Orca for real multi-agent sessions and repair incidents;
6. learn, compare, and explicitly decide the v0.23.0 MCP guidance and tool
   surface without treating fewer tools as automatic improvement;
7. release v0.23.0 only after the generic operating and MCP learning contract is
   accepted;
8. present any successor evidence to the product owner and wait for a separate
   explicit decision before beginning v0.24.0.

A GitHub tag or Release does not activate the installed runtime. A local activation does not by itself make a source candidate released.

## Rationale

This split gives each active minor version a falsifiable product claim, reduces
the time before real feedback, preserves an exact rollback baseline, and
prevents v0.22.0 from remaining open while Aether attempts every future
capability. Production dogfooding exposes liveness, profile, tool selection,
context, recovery, cleanup, and integration defects that controlled fixtures
cannot reveal. Keeping MCP optimization in v0.23.0 avoids declaring the control
surface finished before Hermes can use it reliably.

The fail-closed repair policy ensures that failures improve the intended architecture instead of silently restoring Olympus under another name.

## Alternatives considered

### Keep M6-M12 in v0.22.0

Rejected. It conflates integration, operation, learning-data infrastructure, workflow migration, release, and activation and delays real Orca use.

### Activate the v0.22.0 zero-tool package and call it production

Rejected. The v0.22.0 source candidate is unregistered and intentionally exposes zero callable tools. Production entry requires a real, reversible v0.23.0 control surface.

### Keep Olympus as an automatic fallback while learning Orca

Rejected. It hides integration defects, creates ambiguous authority, and prevents same-path repair evidence. A separately selected legacy task may remain visible during a bounded transition, but no Orca Task may fall through silently.

### Migrate every workflow before real use

Rejected. It creates a big-bang cutover based on speculative requirements instead of production evidence.

### Encode each process as a new personality

Rejected. Stable generic archetypes plus versioned process contracts preserve authority, benchmarks, reuse, and maintainability.

## Consequences

### Positive

- Real Orca use starts as soon as the production-entry gate passes.
- v0.22.0 remains a bounded, honest, reproducible integration foundation.
- v0.23.0 turns defects, tool-use friction, context cost, and unmet needs into
  explicit product work.
- A future v0.24.0 decision can use observed evidence without being implied by
  that evidence.
- Legacy fallback cannot disguise a broken Orca path.
- Full dataset/training work no longer blocks operational learning.

### Negative

- The first v0.23.0 increment is a real operational cutover and must prove rollback.
- Some real Tasks will stop visibly while Orca incidents are repaired.
- Olympus may remain physically present for a bounded interval even though it cannot be a hidden fallback.
- v0.23.0 scope must remain disciplined so incident-driven learning does not become unlimited unrelated cleanup.
- v0.23.0 may remain open for additional controlled MCP optimization cycles, so
  evidence and explicit stop conditions must prevent endless cosmetic tuning.

## Validation or review gate

This decision is correctly reflected when:

1. v0.22.0 current roadmap and status end at M5.4 and preserve the old M0-M12 plan as historical;
2. v0.23.0 has a production-entry, MCP learning/tool-surface optimization,
   generic-roster, incident-repair, personality-refinement, hardening,
   evaluation, and release plan;
3. v0.24.0 is marked as a preserved, inactive per-process migration proposal
   requiring a new explicit owner decision;
4. GitHub has separate milestones and tracking issues for all three versions;
5. Draft PR #163 states the new v0.22.0 boundary and does not claim activation;
6. no source, tests, scripts, profiles, configuration, runtime registration, credentials, or services changed under this documentation-only task.

## Implementation authorization

The product owner authorized the original decision, versioned roadmaps, GitHub
milestones/issues, and updates to the existing Draft PR on 2026-08-09. On
2026-08-11 the owner authorized documentation of the expanded v0.23.0 MCP
learning/optimization boundary and the explicit block on automatic v0.24.0
progression.

This decision does **not** authorize this documentation task to:

- modify production source, tests, schemas, scripts, profiles, SOULs, or configuration;
- register or activate Aether MCP or Orca;
- restart services or mutate the installed Hermes/Aether runtime;
- use provider credentials, spend, or execute a worker;
- merge, tag, publish a Release, deploy, or perform another runtime retirement.

Those effects remain gated by the relevant v0.22.0 release or v0.23.0 implementation/activation Task.

## References

- v0.22.0 boundary: `../releases/v0.22.0/RELEASE_BOUNDARY.md`
- v0.22.0 roadmap: `../releases/v0.22.0/ROADMAP.md`
- v0.23.0 roadmap: `../releases/v0.23.0/ROADMAP.md`
- v0.24.0 roadmap: `../releases/v0.24.0/ROADMAP.md`
- Cross-version adoption plan: `../plans/2026-08-09-orca-production-adoption.md`
- Hermes-Orca boundary: `PDR-0012-hermes-orca-swarm-boundary.md`
- Stable roster: `PDR-0013-swarm-roster-and-personality-model.md`
- Aether MCP control plane: `ADR-0001-aether-mcp-control-and-trace-plane.md`
- GitHub v0.22.0 ledger: https://github.com/DarkArty07/Aether-Agents/issues/166
- GitHub v0.23.0 ledger: https://github.com/DarkArty07/Aether-Agents/issues/167
- GitHub v0.24.0 ledger: https://github.com/DarkArty07/Aether-Agents/issues/168
