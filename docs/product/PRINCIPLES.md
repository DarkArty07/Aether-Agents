# Product and Engineering Principles

> **Status:** APPROVED PRODUCT BASELINE — discovery complete
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0002-generic-adaptive-software-product.md`, `../decisions/PDR-0003-quality-doctrine-and-model-economics.md`, `../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`, `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`, `../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **v0.22.0 runtime decision:** `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

These principles contain the approved product baseline established through discovery Phases 1 through 8. Detailed implementation, shared-skill write governance, memory review UX, future UI design, benchmark construction, migration, and runtime enforcement remain later design and validation work.

## Product principles

### 1. Do only the approved work

- **Rule:** Do not implement, redesign, generalize, optimize, or add capabilities the user did not request unless they are strictly necessary to satisfy the approved result.
- **Why:** Unrequested work is one of the most damaging LLM failure modes. It can be technically impressive while consuming time, increasing maintenance, and displacing the user's actual vision.
- **Favors:** Explicit scope, frozen decisions, necessity arguments, visible options, and confirmation before material expansion.
- **Rejects:** Opportunistic features, speculative abstractions, silent redesigns, and specialist preferences presented as requirements.
- **Conflict rule:** Scope fidelity outranks creativity, architecture elegance, security hardening, and optimization unless a missing change is demonstrably required for correctness or safety.

### 2. Empirical need before architectural novelty

- **Rule:** Every major capability must address an observed failure, materially improve a software-project outcome, or reduce the burden required to obtain that outcome.
- **Why:** Aether is the convergence of practical experience using LLMs, not an abstract demonstration of agent architecture.
- **Favors:** Evidence-backed additions, explicit problem statements, measured improvements, and removal of ineffective mechanisms.
- **Rejects:** Adding a Daimon, memory, MCP integration, skill, workflow, or governance layer merely because it is technically interesting.

### 3. Software projects over code output

- **Rule:** Aether exists to materialize ideas and vision as complete software projects, not merely to generate code.
- **Why:** Code can be locally correct while the product remains incoherent, incomplete, poorly designed, undocumented, or misaligned with user intent.
- **Favors:** Product understanding, proportional specialist input, usable outcomes, verification, documentation, and continuity.
- **Rejects:** Treating generated files, a passing code fragment, or agent completion prose as sufficient project success.

The exact complete-project contract remains open.

### 4. Correctness includes logic and architecture

- **Rule:** High-quality code must minimize logical, architectural, integration, and syntactic defects.
- **Why:** Parsing, compiling, or passing a narrow test does not prove that the system behaves correctly or is structured proportionally.
- **Favors:** Requirement-driven behavior, coherent boundaries, proportional architecture, runtime validation, negative testing where relevant, and explicit known limitations.
- **Rejects:** Syntax-only success, premature abstraction, overarchitecture, hidden integration assumptions, and completion claims unsupported by evidence.

### 5. Creative product quality is a first-class outcome

- **Rule:** Aether should produce software with appropriate originality, visual coherence, usability, and product judgment, especially in frontend and UX work.
- **Why:** General-purpose LLMs often produce generic or visually weak interfaces even when the code is functional.
- **Favors:** Real product context, rendered visual evidence, coherent design direction, specialist collaboration when it adds value, and implementation that preserves design intent.
- **Rejects:** Generic dashboard aesthetics by default, design judged only from code, random visual novelty, and multiple designers pulling the product in conflicting directions.
- **Conflict rule:** Creativity enriches the approved vision; it does not authorize scope expansion or product-direction changes.

### 6. Continuity is part of quality

- **Rule:** Project vision, decisions, structure, progress, and unresolved issues must remain understandable across agents and sessions.
- **Why:** Context loss causes repeated investigation, contradictory work, and drift from prior decisions.
- **Favors:** Durable product documents, decision records, project-local continuity, verified curation, explicit supersession, and cold-session resumption tests.
- **Rejects:** Reliance on one conversation, private agent memory as sole authority, stale summaries, and repeated rediscovery of settled decisions.

### 7. A generic foundation should learn the user

- **Rule:** Aether should be reusable by different users while becoming progressively aligned with each individual's preferences, standards, recurring decisions, and effective procedures.
- **Why:** A static generic assistant repeatedly requires the user to teach the same expectations and corrections.
- **Favors:** Durable preferences, correctable memory, user-specific standards, reusable skills, portability, and explicit current-intent precedence.
- **Rejects:** Permanent one-size-fits-all behavior, hidden profiling, irreversible learning, and stale preferences overriding a current request.

The exact user-facing review, correction, export, reset, and deletion experience remains open.

### 8. Hermes owns the global user model

- **Rule:** Hermes is responsible for detecting, organizing, correcting, and selectively sharing the user's durable profile and preferences.
- **Why:** Hermes is the primary user-facing agent and can reconcile current intent, repeated corrections, project context, and specialist observations into one coherent model.
- **Favors:** Compact `USER.md`, stable `MEMORY.md`, deduplication, current-intent precedence, relevant delegation context, and visible correction.
- **Rejects:** Conflicting Daimon-owned profiles, one-off instructions promoted as durable preferences, and specialist assumptions treated as global user truth.

### 9. Reuse Hermes' native learning framework

- **Rule:** Aether uses Hermes-native memory, `skill_manage`, `/learn`, session search, and Curator as its canonical learning stack.
- **Why:** Rebuilding those capabilities would create duplicate formats, stores, curators, and authorities while weakening the reason Aether is built on Hermes Agent.
- **Favors:** Extension, configuration, governance, and evidence-driven patches to Hermes capabilities.
- **Rejects:** A parallel general memory engine, competing skill format, second curator, or duplicated automatic-learning loop without a verified missing capability.

### 10. Honcho is not part of the target product

- **Rule:** Aether must operate without Honcho or another required external semantic memory service.
- **Why:** Honcho caused operational problems, increases installation and service complexity, and creates an unnecessary second memory authority.
- **Favors:** Hermes-native memory, zero required external memory services, and clear ownership.
- **Rejects:** Honcho as a normal dependency, hidden fallback, installation requirement, or source of product authority.

### 11. User preferences do not become universal skills

- **Rule:** User-specific preferences normally belong in Hermes-managed profile and memory, while shared skills remain reusable and user-neutral.
- **Why:** Aether is a generic product; hard-coding one user's preferences into shared procedural knowledge contaminates behavior for other users and profiles.
- **Favors:** Skills that consult the active user profile, class-level reusable procedures, and possible future private per-user skills.
- **Rejects:** One user's style, tooling preference, or correction encoded as a universal workflow rule.

### 12. User vision is the project anchor

- **Rule:** Specialist intelligence and learned preferences should enrich and materialize the user's current vision, not silently replace it.
- **Why:** Specialists and memory can both produce locally reasonable behavior that causes global project drift.
- **Favors:** Explicit intent, frozen decisions, bounded specialist contribution, visible disagreements, and traceable changes in direction.
- **Rejects:** Allowing an agent's specialty, a past preference, or an inferred pattern to become product authority by default.

The approved authority and escalation model is defined below and in `../knowledge/AUTHORITY.md`; exact autonomy profiles and deterministic enforcement remain open.

### 13. Multi-agent architecture is a means, not a success metric

- **Rule:** Agent count, delegation count, and workflow complexity do not constitute product value.
- **Why:** Specialists are useful only when their contribution exceeds the coordination cost they introduce.
- **Favors:** Selective participation, the shortest reliable work path, and specialist use justified by material impact.
- **Rejects:** Mandatory ceremonies or full-team workflows for tasks that do not need them.

The approved participation policy classifies each Daimon as `required`, `allowed`, `disabled`, or `forbidden` in the applicable scope. Current user policy takes precedence over default routing, learned preferences, peer proposals, and fallback behavior. Current authority is defined in `../knowledge/AUTHORITY.md`; `../knowledge/MULTI_AGENT_MODEL.md` preserves the historical v0.19 operating model.

### 14. New Daimons require a distinct software contribution

- **Rule:** The Daimon team may grow only when a software discipline has a distinct, reusable contribution expected to improve project quality materially.
- **Why:** More roles can create overlap, vision drift, and coordination overhead without increasing capability.
- **Favors:** Clear domain boundaries, measurable contribution, non-overlapping authority, and evidence that specialization helps.
- **Rejects:** New Daimons created for naming symmetry, mythology, novelty, or capabilities already covered adequately.

### 15. Tests must be necessary and sufficient

- **Rule:** Execute the tests and checks needed to support material claims, selected according to scope and risk.
- **Why:** Skipping necessary tests creates false confidence, while maximizing test count can slow simple work without increasing meaningful assurance.
- **Favors:** Focused regression tests, project-appropriate integration and runtime checks, negative cases where relevant, and explicit evidence.
- **Rejects:** Untested completion claims, ritual full-suite execution with no relevance, test quantity as a quality proxy, and tests that validate only implementation details while missing product behavior.

### 16. Security must be proportional to actual risk

- **Rule:** Security expertise should be routed according to realistic threat, consequence, and change scope rather than applied maximally to every task.
- **Why:** The prior Athena experience showed that universal specialist review can introduce disproportionate complexity and delay.
- **Favors:** Explicit risk classification, bounded threat analysis, concrete findings, least-complex effective mitigations, and security evidence appropriate to deployment context.
- **Rejects:** Universal review, speculative hardening, maximal controls without threat justification, and treating security as exempt from coordination-cost analysis.
- **Conflict rule:** Material safety and security risks can block release, but low-risk concerns do not authorize unrelated architecture or scope growth.

### 17. Documentation must remain current and authoritative

- **Rule:** Product, architecture, decision, usage, and operational documentation should evolve with the approved project state.
- **Why:** Stale documentation makes agents infer intent, repeat errors, and act from obsolete assumptions.
- **Favors:** Clear ownership, canonical sources, explicit status, supersession, link validation, contradiction checks, and documentation work included in completion when relevant.
- **Rejects:** Documentation as an optional afterthought, duplicated authorities, release evidence presented as product vision, and unverified summaries.

A dedicated documentation or continuity Daimon is a possible mechanism, not yet an approved role design.

### 18. Comparative project quality is the product proof

- **Rule:** Aether's complexity is justified only when representative same-prompt evaluation shows project quality equal to or better than strong general-purpose coding agents.
- **Why:** Internal tests can prove that coordination machinery works without proving that the product produces better software.
- **Favors:** Controlled baselines, executed project tests, broad quality rubrics, reproducibility, and honest negative results.
- **Rejects:** Superiority claims based on agent count, architecture, activity, generated volume, or internal test totals alone.

The precise benchmark design remains open.

### 19. Use expensive intelligence where judgment matters most

- **Rule:** Allocate model capability according to cognitive difficulty, uncertainty, and consequence.
- **Why:** Frontier models provide the highest value for orchestration, design, architecture, complex reasoning, and difficult debugging, while smaller models have become highly capable at routine coding and mechanical execution.
- **Favors:** Expensive models for strategic and intellectually complex work; capable smaller models for bounded implementation, transformations, checks, and repetitive tasks; ongoing empirical routing evaluation.
- **Rejects:** One-model-fits-all routing, role names permanently tied to cost tiers, cheap routing that creates hidden rework, and frontier-model use for mechanical chatter.
- **Conflict rule:** Quality gates remain fixed. Cost optimization may change who performs the work, not what evidence the result must satisfy.

### 20. Useful autonomy must reduce user coordination

- **Rule:** Aether should not introduce more management, waiting, translation, or review effort than it removes.
- **Why:** An autonomous system that requires constant supervision recreates the burden it was meant to solve.
- **Favors:** Internal mechanical coordination, concise escalation, preserved continuity, and user attention reserved for meaningful decisions.
- **Rejects:** Autonomous bureaucracy, unnecessary approval loops, and opaque drift presented as convenience.

### 21. Product outcomes over agent theater

- **Rule:** Aether should feel like an intelligent software studio focused on the project, not a simulation whose primary spectacle is agent activity.
- **Why:** Agent personalities and collaboration are useful only when they improve the software and reduce user coordination.
- **Favors:** Product-owner language, accountable outcomes, meaningful milestones, and evidence-backed confidence.
- **Rejects:** Noisy swarms, competitive personalities, decorative activity, and gamification that confuses motion with progress.

### 22. Visibility should be progressive

- **Rule:** Show product outcomes, meaningful progress, decisions, blockers, risks, and evidence by default; expose operational detail through deliberate drill-down.
- **Why:** Trust requires transparency, but ordinary users should not need to read every tool call, retry, or peer message.
- **Favors:** Layered summaries, decision inboxes, studio views, evidence panels, resource views, and deep diagnostics on demand.
- **Rejects:** Universal raw logs by default and black-box final answers with no inspectable basis.

### 23. Interfaces project authority; they do not own it

- **Rule:** A future UI may present and submit actions against authoritative product, ledger, runtime, continuity, memory, artifact, and evidence systems, but must not maintain a competing truth.
- **Why:** A dashboard that diverges from actual state creates misleading progress, unsafe control, and broken recovery.
- **Favors:** Reconstructable projections, explicit source attribution, shared contracts across clients, and truthful status vocabulary.
- **Rejects:** UI-local semantic state, unsupported progress percentages, session completion shown as project acceptance, and aspirational features presented as current.

### 24. Requirements understanding is Hermes' responsibility

- **Rule:** Hermes must discover, clarify, structure, preserve, and validate the user's intended product outcome before and throughout execution.
- **Why:** A technically strong implementation is still a product failure when it solves the wrong problem.
- **Favors:** Product-level questions for material ambiguity, explicit assumptions, bounded contracts, visible amendments, and current-intent precedence.
- **Rejects:** Asking the user to solve routine technical mechanics, silently choosing among materially different product interpretations, and rewriting requirements after implementation.

### 25. User outcome defines project completion

- **Rule:** A project is complete when the user obtained and accepts the intended software result.
- **Why:** Agent sessions, generated files, tests, documentation, and workflow terminality are evidence and enabling conditions, not the semantic definition of success.
- **Favors:** Outcome validation, proportional evidence, honest limitations, continuity, and explicit acceptance of material deviations.
- **Rejects:** A generic `done` state, technical completion presented as product acceptance, and success claims contradicted by the user's experience.

### 26. Non-negotiable product integrity

- **Rule:** Aether may trade speed, model expense, Daimon count, secondary scope, ceremony, nonessential polish, and premature optimization, but never current approved intent, honesty, essential correctness, product-owner authority, material safety, credential protection, evidence, known-deviation disclosure, or sufficient project continuity.
- **Why:** Sacrificing these properties would negate Aether's product thesis regardless of throughput or architectural sophistication.
- **Favors:** Explicit compromise, narrower honest delivery, fail-closed consequential actions, and accepted known deviations.
- **Rejects:** Hidden defects, retrospective goal changes, unsupported completion, silent risk acceptance, and false progress.

## Approved trade-off order

When principles conflict, use this order unless a material safety boundary requires escalation:

1. Adequately understood current user intent, intended outcome, and requested scope.
2. Technical correctness and prevention of material harm.
3. Product coherence, creativity, and usability.
4. Continuity, maintainability, and current documentation.
5. Proportional tests and security assurance.
6. Speed, inference cost, and operational convenience.

Cost and speed are important, but they are optimized after preserving the higher-order quality dimensions. Unlimited spending for marginal improvement is also rejected; exact limits remain an evaluation decision.

## Human authority principles

### Product-owner-first interaction

- **Rule:** The user owns product vision, requested behavior, material scope, priorities, accepted compromises, consequential external effects, and final acceptance.
- **Why:** Aether is intended to let a person direct software production without requiring advanced technical knowledge or manual agent coordination.
- **Favors:** Product-language questions, clear recommendations, consequence-based trade-offs, and autonomous resolution of routine technical work.
- **Rejects:** Asking the user to select unexplained technologies, coordinate Daimons, design test mechanics, or diagnose routine failures.

### Technical autonomy inside approved boundaries

- **Rule:** Aether owns routine technical means within the approved product contract.
- **Why:** Transferring implementation, routing, tool, model, test, and recovery decisions to the user would recreate the burden Aether is meant to remove.
- **Favors:** Autonomous decomposition, specialist selection, model routing, implementation details, proportional verification, bounded recovery, and documentation maintenance.
- **Rejects:** Approval loops for reversible internal decisions and technical uncertainty used to offload engineering analysis onto the user.

### Material consequences require human authority

- **Rule:** Aether must escalate when a decision changes visible product outcomes, material scope, foundational commitments, accepted risk, meaningful cost, external accounts, publication, deployment, or irreversible state.
- **Why:** Those consequences express product ownership and cannot be inferred safely from technical optimization alone.
- **Favors:** One synthesized decision, an explicit recommendation, meaningful alternatives, and clear product consequences.
- **Rejects:** Silent scope expansion, hidden trade-offs, irreversible action by implication, and raw specialist disagreements sent directly to the user.

### Current intent outranks stored knowledge

- **Rule:** Current explicit user instructions override learned preferences, historical memory, specialist assumptions, and inferred patterns.
- **Why:** Personalization exists to serve the user, not acquire authority over the present request.
- **Favors:** Visible conflict detection and escalation only when the contradiction materially affects the product.
- **Rejects:** Stale preferences silently redirecting current work.

The canonical target authority matrix is maintained in `../knowledge/AUTHORITY.md`. Exact autonomy profiles, attempt budgets, and deterministic enforcement mechanisms remain later design decisions.

## Agent-system principles

### User-controlled specialist participation

- **Rule:** The product owner may classify any Daimon as `required`, `allowed`, `disabled`, or `forbidden` globally, per project, per run, or per task.
- **Why:** Specialist value is contextual, and the Athena experience demonstrated that a useful discipline can still impose disproportionate complexity and delay.
- **Favors:** Explicit participant policy, current-user precedence, honest substitutes, and visible residual risk.
- **Rejects:** Universal phase gates, hidden reactivation, renamed substitutes, and fallback paths that bypass user policy.

### Centralized intent, lateral execution

- **Rule:** Hermes centralizes user intent, contract meaning, amendments, and product synthesis; authorized Daimons may coordinate routine work directly inside the approved contract.
- **Why:** Requiring Hermes to relay every message turns the most capable model into an expensive message bus and prevents autonomous specialist collaboration.
- **Favors:** Direct bounded handoffs, shared evidence, accountable ownership, durable task state, and Hermes visibility through milestones and escalations rather than all peer chatter.
- **Rejects:** Mandatory Hermes relay and unrestricted self-organizing agents without contract authority.

### The execution substrate must not govern the product

- **Rule:** A future accepted substrate may coordinate admitted work, dependencies, budgets, evidence, retries, and recovery, but may not redefine product intent, override participant policy, become a domain owner, or accept its own results.
- **Why:** Moving routine coordination out of Hermes must not create a second strategic authority or another mandatory relay.
- **Favors:** Bounded selection, deterministic validation, one authority per fact, explicit lifecycle ownership, and replaceable adapters.
- **Rejects:** Runtime-authored product amendments, forbidden-Daimon selection, hidden fallback, self-approval, and substrate identity embedded in Aether semantic contracts.

### Evidence and authority resolve disagreements

- **Rule:** Daimon disagreements resolve through current user intent, approved decisions, contract, artifacts, reproducible evidence, quality doctrine, and domain authority—not majority vote.
- **Why:** Several agents can share the same error, and confidence or repetition does not establish truth or product authority.
- **Favors:** Independent domain gates, reproducible evidence, bounded correction, explicit waiver, Hermes cross-domain synthesis, and product-owner escalation only for material consequences.
- **Rejects:** Voting, repetition, model-size authority, indefinite unsupported blocking, and specialist preference presented as fact.

The retired v0.19.0/v0.19.x operating model is preserved in `../knowledge/MULTI_AGENT_MODEL.md`. Any replacement execution model is governed by PDR-0011 and must preserve these authority principles.

## Engineering principles

Engineering work must preserve scope fidelity, correctness, proportional architecture, verification, continuity, and documentation. Specific technologies, models, providers, and implementation patterns are not product principles by themselves.

## Safety and trust principles

Security is risk-proportional, but material safety, permissions, credentials, spending, publication, deployment, and irreversible effects remain explicit authority boundaries. Documentation approval alone does not authorize implementation or external effects.

## Rejected principles

The following philosophies are explicitly rejected:

- Doing extra work is inherently helpful.
- More agents necessarily produce a better result.
- A technically possible integration belongs in the product by default.
- Agent activity is equivalent to progress.
- Specialist confidence is equivalent to product authority.
- A learned historical preference overrides current explicit intent.
- Autonomous operation is valuable even when it increases user coordination.
- Internal runtime correctness proves superior project quality.
- Technical terminality, passing tests, commits, generated files, or agent completion prose automatically means the user obtained the intended product.
- Requirements may be rewritten after implementation to match the produced artifact.
- Tests, security controls, or documentation volume can compensate for solving the wrong problem.
- Every task requires maximum security review.
- The largest or most expensive model should perform every task.
- The cheapest model is preferable when it creates defects or rework.
- Aether should imitate a generic coding assistant as its governing identity.
- Aether should expand into unrelated non-software domains merely because LLMs can discuss them.
