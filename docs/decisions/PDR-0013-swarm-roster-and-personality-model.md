# PDR-0013: Stable swarm roster and personality model

- **Status:** APPROVED
- **Date:** 2026-08-06
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** The assumption that every tracked specialist profile belongs in the future active swarm
- **Preserves:** PDR-0005 participant policy and PDR-0012 Hermes–Orca ownership boundary
- **Superseded by:** None
- **Implementation boundary:** Design and documentation only; profile and runtime changes are not authorized

## Context

Aether's v0.22.0 candidate physically retired Olympus and its disconnected native Python core. The product still needs a deliberate specialist team, but a directory of profiles is not a swarm design and a mythology-inspired name is not a reason to create or retain an agent.

The tracked candidate currently contains six specialist profile definitions: Hefesto, Daedalus, Ictinus, Ariadna, Athena, and Etalides. None is runnable through an accepted Aether multi-agent path. Their physical presence records the current repository state; it does not establish their target participation status.

The product owner approved a smaller target team in which:

- Hermes remains the sole user-facing product supervisor;
- stable specialist archetypes are instantiated only when their contribution is material;
- several workers may use the same archetype for separate bounded Tasks;
- profiles are not multiplied by language, framework, file type, or naming symmetry;
- an independent verification contribution is designed before a new profile is implemented;
- obsolete or forbidden profiles are not retained as hidden fallback routes.

This decision records the target roster and its authority model. It does not remove files, create a new profile, activate Orca, or run a worker.

## Decision

### 1. Aether uses stable archetypes and temporary workers

A **Daimon archetype** is a reusable specialist identity with a stable cognitive stance, authority boundary, tool policy, output contract, and activation rule.

A **worker** is one temporary runtime instance of an admitted archetype executing one bounded Task through one Dispatch attempt.

A **Task** defines the deliverable. The archetype does not own the product roadmap or invent its own work.

Consequently:

```text
one archetype != one permanent worker
one Task != one new personality
one technology != one new Daimon
```

Hermes may assign several independent Tasks to several instances of the same archetype. For example, separate Hefesto workers may own frontend and backend scopes without creating separate frontend and backend personalities.

### 2. Hermes is supervisor, not another Daimon

Hermes owns:

- the user relationship and product-language conversation;
- intent interpretation and material clarification;
- the task contract, acceptance criteria, non-goals, and stop condition;
- direct-versus-swarm selection;
- participant admission and effective policy;
- Task decomposition, dependencies, write scopes, and placement;
- product questions and contract amendments;
- deterministic integration and proportional verification;
- final synthesis and the proposal presented for user acceptance;
- release and protected-effect gating.

Hermes may implement bounded work directly. It does not need to create a Run for every request and must not use the swarm when one accountable owner is the shorter reliable path.

### 3. Target roster

Two distinct dimensions are recorded:

- **lifecycle:** `retained`, `conditional`, `proposed`, or `retired`;
- **participation policy:** `required`, `allowed`, `disabled`, or `forbidden` at the applicable user/project/run/task scope.

Runtime availability is separate. The v0.22.0 candidate has accepted bounded M5.4 integration evidence but remains default-off, zero-tool and unregistered. The retained roster is operationally unavailable until the v0.23.0 production-entry and qualification gates pass.

| Identity | Target function | Lifecycle | Default target policy | v0.22.0 implementation state |
|---|---|---|---|---|
| Hermes | Product supervisor, technical lead, integrator, and acceptance synthesizer | retained | not a Daimon policy subject | available for direct work only |
| Hefesto | Production builder | retained | allowed | profile present; no accepted swarm route |
| Daedalus | Experience designer and implementation reviewer | retained | allowed | profile present; no accepted swarm route |
| Ictinus | Architecture consultant | retained | allowed | profile present; no accepted swarm route |
| Ariadna | Bounded context/handoff curator | conditional | disabled | profile present; utility and data contract unaccepted |
| Independent Verifier | Product-behavior and evidence reviewer | proposed | unavailable | role design only; no name, SOUL, config, or runtime profile |
| Athena | Security specialist | retired | forbidden | profile still physically present pending a separately authorized retirement cut |
| Etalides | Research specialist | retired | forbidden | profile still physically present pending a separately authorized retirement cut |

A lower policy layer, retry, fallback, peer request, alias, or equivalent role must not re-enable a disabled or forbidden participant.

### 4. Retained archetypes

#### Hefesto — Production Builder

Hefesto is pragmatic, implementation-focused, evidence-oriented, and resistant to speculative redesign. Hefesto may write production code and tests inside an exact Task scope, debug root causes, and produce an implementation report.

Hefesto may not amend product intent, create sibling workers, expand scope, choose protected effects, or self-accept a material feature.

#### Daedalus — Experience Designer

Daedalus reasons from user goals, interaction clarity, information hierarchy, visual coherence, and rendered evidence. Daedalus may create design artifacts and non-production prototypes and may review whether implementation preserves accepted design intent.

Daedalus may not decide product scope, select the technology stack, or silently turn a prototype into production implementation.

#### Ictinus — Architecture Consultant

Ictinus evaluates structure, data, APIs, scale, operability, and trade-offs. Ictinus participates only when architecture consequence justifies consultation cost.

Ictinus is advisory. It may not implement, assign work, impose speculative scale, or become a mandatory gate for routine changes.

### 5. Ariadna is conditional rather than core

Ariadna is not a standing project manager and does not own global memory. Hermes Agent's native memory, session search, Curator, and version-controlled project documentation remain canonical.

A future Ariadna Task may receive an explicitly authorized, bounded context projection and return a concise handoff. Ariadna must not read or write protected `.aether` stores through an unsupported path.

Ariadna remains disabled until a separate gate proves that:

1. its contribution is distinct from Hermes' native continuity mechanisms;
2. its input source, privacy boundary, freshness, and output contract are explicit;
3. the output improves a cold handoff measurably;
4. failure is visible and does not corrupt authority;
5. the benefit exceeds the additional model and coordination cost.

If that gate fails, Ariadna should be retired rather than preserved ceremonially.

### 6. An Independent Verifier is the next proposed archetype

The roster needs a contribution that is independent from implementation but does not replace Hermes' semantic acceptance.

The proposed Verifier is:

- skeptical without being adversarial for its own sake;
- experimental and reproduction-oriented;
- focused on user-visible behavior, contracts, regressions, and evidence;
- explicit about unknowns and unavailable evidence;
- prohibited from treating test count as product correctness.

A future Verifier may read implementation, execute tests/builds/E2E flows, inspect rendered artifacts, reproduce defects, and—when explicitly scoped—write acceptance tests or evidence artifacts. It must not silently repair production code, redefine acceptance, impose style preferences, or declare final product acceptance.

Its required output distinguishes:

- contract coverage;
- executed evidence;
- verified outcomes;
- blocking and non-blocking findings;
- unknowns;
- one of `READY_FOR_HERMES_REVIEW`, `CORRECTION_REQUIRED`, or `INSUFFICIENT_EVIDENCE`.

The role is approved for detailed design. Its name, eponym, SOUL, model, toolset, benchmark, and activation are separate future decisions.

### 7. Athena and Etalides have target retirement disposition

Athena is forbidden under the current product-owner policy. Security remains a quality dimension, but universal Athena participation previously added process and complexity disproportionate to actual risk. Hermes must apply proportional security checks, use deterministic tools, seek an independently authorized review when consequence requires it, or disclose a capability gap. A renamed or equivalent hidden Athena fallback is prohibited.

Etalides must not receive new workflow dependencies. Research remains an activity Aether may need, but the current profile is not the approved future solution. Hermes performs bounded research directly or discloses a capability gap until a replacement role is justified and separately approved.

Historical release evidence mentioning either profile remains unchanged. Physical profile and current-facing-surface removal is a later implementation cut and is not performed by this design decision.

### 8. Every archetype requires a complete contract

No profile is accepted from personality prose alone. It must define:

1. the recurring product failure it addresses;
2. its distinct reusable contribution;
3. cognitive stance and behavioral character;
4. allowed decisions and mutations;
5. explicit prohibitions;
6. required input contract;
7. structured deliverable and evidence;
8. tools, model class, and data access;
9. communication recipients and escalation rules;
10. activation, stop, retry, and cleanup criteria;
11. benchmark or acceptance evidence demonstrating value;
12. retirement conditions.

### 9. Hermes selects the smallest sufficient team

For each task contract, Hermes must:

1. determine whether direct execution is sufficient;
2. identify a distinct specialist contribution, not merely a convenient job title;
3. resolve effective participant policy before routing;
4. define one deliverable and owner per Task;
5. define dependencies, write scope, evidence, and stop condition;
6. start independent Tasks in parallel only when scopes and dependencies permit;
7. prefer multiple instances of an existing archetype over creating a redundant personality;
8. stop expanding the swarm when the acceptance condition is covered.

No role is mandatory merely because it exists.

### 10. Lateral communication is bounded by the contract

Admitted workers may exchange routine progress, artifact references, dependency handoffs, review requests, questions, and evidence through Orca. A message may inform reasoning but cannot:

- add scope;
- amend product intent;
- grant authority;
- re-enable a participant;
- approve a protected effect;
- waive acceptance evidence;
- authorize release or activation.

Product-material questions return to Hermes. Hermes escalates to the user only when user-owned meaning, compromise, consequence, or authority is involved.

### 11. Technical completion and product acceptance remain separate

`worker_done` means an Orca Dispatch reached a worker-reported terminal outcome. It moves the Task to review; it does not establish acceptance.

Specialist review may establish domain findings. The proposed Verifier may establish independent evidence. Hermes compares integrated artifacts and evidence against the contract and proposes acceptance. The user remains final product acceptance authority.

## Rationale

A small stable roster reduces agent theater, coordination overhead, prompt drift, and duplicated authority. Reusing an archetype across multiple workers preserves a coherent team model while allowing parallelism. Separating lifecycle from participation policy prevents a tracked profile from being mistaken for an authorized participant.

The target roster retains the strongest differentiated contributions already present, makes Ariadna prove its value, removes forbidden or deprecated routing targets, and closes the missing independent-verification discipline without prematurely creating another personality.

## Alternatives considered

### Keep all six tracked profiles as the target roster

Rejected. Physical presence is not evidence of product value, Athena is forbidden, Etalides has no approved future dependency, and Ariadna duplicates native continuity unless a distinct contribution is proven.

### Create one specialist personality per technical stack

Rejected. Task contracts and multiple worker instances provide bounded specialization without multiplying identities and maintenance.

### Generate a new personality dynamically for every Run

Rejected for the initial target. Dynamic identities weaken stable authority, benchmarks, participant policy, and user comprehension. Future evidence may justify controlled role generation, but it is not presumed.

### Let Hermes perform every discipline alone

Rejected as the product target. Direct execution is preferred for bounded work, but distinct design, architecture, implementation, and independent verification contributions can improve substantial projects.

### Make the Verifier the final acceptance authority

Rejected. Independent verification provides evidence; Hermes owns semantic synthesis and the user owns final acceptance.

## Consequences

### Positive

- The target team is understandable and intentionally small.
- Parallelism does not require identity proliferation.
- Forbidden and deprecated profiles cannot become fallback routes.
- Independent verification has a clear design boundary.
- Ariadna must demonstrate distinct value instead of surviving by history.
- Hermes remains accountable for product coherence.

### Negative

- Research has no dedicated target specialist yet.
- Security-critical work may expose an explicit independent-review capability gap.
- The Verifier still requires naming, implementation, and benchmark work.
- Current tracked profile directories temporarily differ from the target roster until a later authorized cut.

## Validation or review gate

This design is accepted when:

1. the canonical architecture documents distinguish archetype, worker, Task, and Dispatch;
2. current physical profile presence is not presented as target admission;
3. target lifecycle and default policy are explicit for every existing profile;
4. Hermes selection and lateral-message authority are explicit;
5. the Verifier is designed without being claimed as implemented;
6. Ariadna's conditional gate and the research capability gap are honest;
7. Athena and Etalides retirement does not rewrite historical evidence;
8. Orca activation and physical repository changes remain separately gated.

## Implementation authorization

The product owner authorized design and documentation on 2026-08-06.

This decision does **not** authorize:

- deleting or modifying profile files, configs, scripts, tests, or active runtime configuration;
- creating the Verifier profile;
- launching a specialist worker or activating Orca;
- migrating or editing `.aether` state;
- committing, integrating, releasing, deploying, changing credentials, or spending.

A later implementation instruction must select exact removal and creation cuts and their evidence gates.

## References

- Participant policy: `PDR-0005-multi-agent-participation-and-coordination.md`
- Hermes–Orca boundary: `PDR-0012-hermes-orca-swarm-boundary.md`
- Product scope: `../product/SCOPE.md`
- Product experience: `../product/EXPERIENCE.md`
- Canonical roster: `../architecture/DAIMONS.md`
- Target operating model: `../architecture/ORCHESTRATION.md`
