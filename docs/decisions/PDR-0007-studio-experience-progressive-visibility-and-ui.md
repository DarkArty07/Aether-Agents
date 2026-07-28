# PDR-0007: Intelligent software studio experience and progressive visibility

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** None
- **Superseded by:** None

## Context

Aether is intended to coordinate specialized agents, models, tools, memory, project state, evidence, and recovery. Exposing all of that machinery directly would force the user to become an agent operator rather than remain a product owner.

The product nevertheless needs transparency. Users must understand what Aether is trying to achieve, whether work is progressing, which decisions require attention, what risks remain, and which evidence supports completion. Advanced users should also be able to inspect Daimons, tasks, handoffs, model use, costs, tests, findings, and coordination history.

The owner also wants a future user interface that makes this internal organization visible without turning it into noise or allowing the UI to become a competing source of truth.

## Decision

### 1. Product experience

Aether should feel like directing an intelligent software studio, not administering a collection of agents.

The user supplies product vision, priorities, feedback, and material decisions. Aether supplies the technical and specialist organization required to turn that vision into software.

The default experience should convey:

- comprehension of the user's product intent;
- organized autonomous execution;
- continuity across sessions;
- appropriate specialist depth;
- creativity and product judgment;
- visible progress without operational noise;
- confidence grounded in evidence rather than confident prose.

The studio metaphor is a product mental model, not a literal requirement to simulate employees or expose theatrical agent personalities.

### 2. Progressive visibility

Aether uses layered visibility rather than one universal detail level.

#### Default product-owner view

The default experience shows:

- the current product outcome or approved contract;
- the current phase or meaningful stage;
- concise progress and recent material change;
- decisions that require the user;
- material blockers and risks;
- important scope or quality deviations;
- the final result and supporting evidence summary.

Routine peer messages, file reads, internal retries, ordinary tool calls, and repetitive state transitions are hidden by default.

#### Detailed operational view

The user may drill down into:

- participating Daimons and their assigned responsibilities;
- task graph, dependencies, owners, and status;
- contract scope, exclusions, amendments, and acceptance criteria;
- handoffs and artifact lineage;
- tests, builds, screenshots, reviews, and other evidence;
- model and provider selection;
- inference cost, latency, retries, and budget use;
- findings, waivers, residual risks, and failed attempts;
- coordination ledger history and lifecycle state;
- current versus target architecture or feature status when relevant.

Visibility must be available without forcing the user to read it during ordinary work.

### 3. Future UI

A dedicated Aether UI is an approved future product direction.

Its purpose is to make project direction, execution state, decisions, evidence, and specialist collaboration understandable. It should combine a product-owner conversation surface with an optional operational studio view.

The future UI should support at least these conceptual surfaces:

1. **Conversation and direction** — interaction with Hermes in product language.
2. **Project overview** — vision, contract, phase, progress, blockers, and next meaningful outcome.
3. **Decision inbox** — only decisions that genuinely require product-owner authority.
4. **Studio activity** — active Daimons, task ownership, dependencies, and meaningful handoffs.
5. **Evidence and quality** — tests, reviews, visual artifacts, findings, completion confidence, and known deviations.
6. **Resources** — model routing, cost, latency, attempts, and budgets.
7. **Continuity** — durable decisions, memory/profile controls, project history, and resumption state.
8. **Deep inspection** — ledger events, technical sessions, raw evidence, and diagnostic detail for advanced users.

The exact delivery surface—desktop, web, TUI, or a combination—remains a later design decision.

### 4. UI is a projection, not authority

The UI must read and present authoritative state from the appropriate domain:

- product decisions and version-controlled documents;
- contract and coordination ledger state;
- `.aether` continuity;
- Olympus runtime/session facts;
- source, artifacts, tests, builds, screenshots, and receipts;
- Hermes-managed user profile and memory.

A visual card, progress bar, agent animation, or chat message is not authoritative merely because it appears in the UI.

The UI may submit authorized commands and decisions, but must not maintain an independent mutable truth that can diverge from the underlying product, coordination, runtime, or artifact sources.

### 5. Status honesty

The experience must distinguish clearly among:

- proposed;
- approved target;
- implemented;
- enabled;
- executing;
- technically completed;
- semantically accepted;
- blocked;
- failed;
- partially completed;
- experimental;
- retired.

Aether must not display aspirational architecture as current behavior, an ACP session return as project completion, or activity as progress.

### 6. Long-term ambition

Aether aspires to become an adaptive AI software production studio that enables individuals and small teams to produce software with quality approaching that of a competent multidisciplinary team.

This ambition remains limited to software. It includes product thinking, research, UX, architecture, implementation, verification, security proportional to risk, documentation, continuity, and operations when those disciplines are required by the software project.

Aether does not promise to eliminate all human expertise or judgment. It aims to make broad, coordinated specialist capacity available to a product owner while keeping material product authority human.

## Rationale

A multi-agent product creates value only when the user experiences better software, not when they experience more agent activity. The studio model communicates broad capability while preserving the user's role as product owner.

Progressive visibility resolves the tension between simplicity and trust. A concise default view keeps routine work usable; drill-down preserves auditability and advanced control.

A future UI can make Aether's differentiation tangible: continuity, specialist coordination, evidence, model economics, and product-owner authority are difficult to communicate through a plain chat transcript alone.

Keeping the UI as a projection prevents a common architecture failure where dashboards, caches, and conversational summaries begin making conflicting state claims.

## Alternatives considered

### Show every internal agent message by default

- **Benefits:** Maximum apparent transparency.
- **Costs:** Noise, context overload, approval fatigue, leaked internal mechanics, and the user becoming coordinator.
- **Decision:** Rejected.

### Hide all internal work and show only final answers

- **Benefits:** Very simple experience.
- **Costs:** Weak trust, poor diagnosis, invisible stalls, unverifiable completion, and no meaningful operator control.
- **Decision:** Rejected.

### Make the UI the central orchestration database

- **Benefits:** Simplified frontend development and direct control.
- **Costs:** Creates duplicate authority, drift from runtime truth, fragile recovery, and misleading status.
- **Decision:** Rejected.

### Remain permanently CLI/chat-only

- **Benefits:** Lower implementation cost and fewer surfaces.
- **Costs:** Limits observability, product accessibility, project overview, evidence inspection, and adoption by non-expert product owners.
- **Decision:** Rejected as the long-term product ambition.

### Present Aether primarily as a virtual team simulation

- **Benefits:** Memorable and visually engaging.
- **Costs:** Encourages agent theater, anthropomorphic noise, and attention to personalities instead of project outcomes.
- **Decision:** Rejected as the governing experience. Mythological identity may enrich the interface but cannot replace truthful product state.

## Consequences

### Positive

- The user remains focused on product outcomes.
- Aether can expose deep evidence without cluttering normal interaction.
- The future UI has a clear purpose and information hierarchy.
- Operational state remains auditable and honest.
- The product differentiates itself beyond a command-line coding assistant.

### Negative

- Multiple visibility layers require careful information architecture.
- The future UI must integrate several authoritative stores without duplicating them.
- Progress and completion cannot be represented through one simplistic percentage.
- Advanced observability may increase implementation complexity.

### Risks

- A visually impressive UI may create false confidence unsupported by evidence.
- Agent personality and animation may overshadow product outcomes.
- Users may interpret estimates or progress bars as guarantees.
- Sensitive prompts, memories, credentials, or internal reasoning could be exposed through excessive drill-down.
- A desktop, web, and TUI strategy could fragment unless they share one projection contract.

## Validation or review gate

Later product and UI design must demonstrate:

1. a product owner can understand current project state without reading internal agent chatter;
2. material decisions are easy to identify and explain consequences clearly;
3. detailed task, agent, evidence, cost, and ledger information is available on demand;
4. visible status maps to authoritative underlying facts;
5. proposed, experimental, current, blocked, and completed states cannot be confused;
6. the UI does not maintain a second coordination truth;
7. private memory, credentials, and sensitive internal data are appropriately bounded;
8. the experience remains usable for non-expert users while supporting advanced inspection;
9. progressive visibility reduces rather than increases user coordination burden;
10. the interface communicates project quality and evidence, not merely activity.

## Implementation authorization

Approval of this record authorizes product documentation alignment and future UI research, requirements discovery, information architecture, and design exploration. It does not authorize frontend implementation, runtime/API changes, ledger changes, deployment, publication, model changes, or live service activation.

## References

- Product experience: `docs/product/EXPERIENCE.md`
- Product vision: `docs/product/VISION.md`
- Product mission: `docs/product/MISSION.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Authority model: `docs/knowledge/AUTHORITY.md`
- Multi-agent model: `docs/knowledge/MULTI_AGENT_MODEL.md`
