# PDR-0009: SemVer-governed Aether self-improvement cycle

- **Status:** APPROVED
- **Date:** 2026-07-28
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** Any assumption that Aether's next coordinator or next minor version must be model-backed
- **Superseded by:** None

## Context

Aether must learn from real use of its own coordination and development paths rather than hide defects behind a legacy fallback or choose future architecture before evidence exists. The owner removed the model-visible `talk_to` tool from the active Aether dogfood Hermes profile and established a project boundary: inside Aether, Hermes may diagnose and repair the framework directly; inside any other project, Hermes works directly on that project and must not mutate Aether incidentally.

The v0.19.x roadmap closed at v0.19.5 with a `VIABLE — BOUNDED` verdict for deterministic Harmonia selection and one bounded no-relay lifecycle. That evidence did not establish global activation, arbitrary planning, or a need for an LLM-backed coordinator. The last official release remains v0.18.2; v0.19.5 is a closed technical candidate whose integration, version reconciliation, tag, and publication remain separate gates.

The product needs a repeatable way for every new Hermes session working on Aether to load the active improvement hypothesis, exercise the system when applicable, measure outcomes, preserve failures, repair framework defects, verify corrections, and accumulate evidence for the next minor version. Memory alone is insufficient because it is bounded and model-mediated.

## Decision

### 1. Every Aether Hermes session participates in the active cycle

Each new Hermes session whose verified project root is Aether Agents enters the active SemVer self-improvement cycle before project work. The cycle wraps the user's real task; it does not replace user intent or manufacture unnecessary agent work.

The required lifecycle is:

```text
orient -> baseline -> execute -> measure -> classify
       -> repair when justified -> verify -> retry intended path
       -> record evidence -> update next-minor signals
```

A question, editorial task, or precise direct edit does not require a ceremonial Harmonia run. Work that materially benefits from a Daimon must use Harmonia because `talk_to` is unavailable.

### 2. Dogfooding is fail-visible and project-scoped

Inside Aether:

```text
Harmonia attempt
-> preserve failure evidence
-> reconcile and verify cleanup when authority or effects may exist
-> Hermes diagnoses and repairs a framework defect directly
-> deterministic verification
-> retry through Harmonia
```

The retry is required evidence that the framework path improved rather than being bypassed. Contract defects, worker defects, and intentional disabled/configuration states must be classified separately; they do not automatically justify kernel changes.

Outside Aether, Hermes completes the external project directly when coordination is unavailable. It does not modify Aether from that project. Framework work waits for a dedicated Aether session.

### 3. SemVer expresses evidence-backed capability

Each minor version represents one approved capability hypothesis. Multiple sessions may contribute evidence to one minor candidate. A session may emit a `MINOR_CAPABILITY_SIGNAL`, but it cannot approve, implement, or release the next minor by itself.

- **PATCH** increments contain compatible corrections or bounded internal improvements to an already approved capability.
- **MINOR** increments contain an evidence-backed backward-compatible capability addition or material operating-model change.
- **MAJOR** increments contain breaking public or migration boundaries under the repository's release policy.

No future minor is reserved for an LLM coordinator. Whether model-backed planning is useful remains an empirical question. A fixed policy, another deterministic mechanism, an LLM proposal layer, or no coordinator change are all valid future outcomes until evidence distinguishes them.

### 4. The first cycle candidate is v0.20.0

The approved design candidate is:

> **v0.20.0 — Self-Improvement Cycle Bootstrap**

Its intended capability is automatic, measurable, project-isolated cycle initialization and evidence accumulation for Aether sessions. It includes a versioned cycle contract, machine-readable manifest, deterministic session hooks, local operational ledger, Aether Router measurement, mandatory absence of `talk_to`, Harmonia use when applicable, safe direct takeover, repair verification, and next-minor evidence signals.

The active manifest is `docs/releases/v0.20.0/CYCLE.yaml`. This approval does not claim that the runtime behavior is implemented.

### 5. Aether Router is compute substrate, not acceptance authority

The cycle uses the configured `custom:aether-router` provider. Evidence records the logical provider, requested model, resolved route/model when reported, latency, token usage, cost when reported, and errors without credentials or account secrets.

Provider or account routing does not certify improvement. Deterministic tests, artifacts, kernel and lifecycle facts, proportional acceptance evidence, Hermes synthesis, and owner authority remain independent. Missing telemetry is `unknown`; it must not be inferred.

### 6. Continuity uses layered enforcement

The cycle must not depend on memory alone. The approved layers are:

1. this PDR for durable owner authority;
2. `docs/knowledge/SELF_IMPROVEMENT_CYCLE.md` for the shared operating model;
3. `AGENTS.md` and `docs/AGENT_ONBOARDING.md` for automatic incoming-session discovery;
4. a versioned `CYCLE.yaml` manifest for machine-readable active state;
5. a default-off profile-scoped Hermes plugin using supported lifecycle hooks;
6. a local `.aether` improvement ledger for operational records;
7. release evidence generated from validated aggregate facts.

The implemented plugin fails closed when it cannot prove project identity. It must not write Aether state for another project.

## Rationale

A forced legacy cutover only creates product value when failures become observable and lead to verified improvements. A session-level evidence loop makes dogfooding cumulative instead of anecdotal. SemVer provides bounded hypotheses and prevents version churn, while a machine-readable manifest and deterministic hooks make the cycle discoverable even when memory is absent or stale.

Keeping Aether Router as the compute substrate avoids unnecessary provider migration. Separating compute from acceptance prevents the same model's narrative from becoming self-certifying evidence.

Deferring any LLM coordinator decision preserves causal attribution. The deterministic runtime, session cycle, takeover, measurement, and isolation hypotheses must be exercised before introducing another trust boundary.

## Alternatives considered

### Reserve the next minor for an LLM-backed Harmonia

- **Benefits:** Moves quickly toward adaptive planning.
- **Costs:** Presumes need before using the current system and mixes model quality with runtime, authority, and lifecycle defects.
- **Decision:** Rejected. Future planner architecture remains evidence-dependent.

### Rely on Hermes memory and instructions only

- **Benefits:** No new runtime mechanism.
- **Costs:** Bounded storage, model-mediated compliance, no deterministic session initialization, and weak auditability.
- **Decision:** Rejected as the guarantee. Memory remains a compact backup.

### Run a Harmonia task in every session regardless of the user's work

- **Benefits:** Maximizes invocation count.
- **Costs:** Artificial workload, unnecessary cost, metric gaming, and possible distraction from user intent.
- **Decision:** Rejected. Harmonia is mandatory when applicable, not ceremonial.

### Let every session choose and start a new minor

- **Benefits:** High apparent iteration speed.
- **Costs:** Version churn, weak evidence, unstable scope, and loss of owner authority.
- **Decision:** Rejected. Sessions accumulate signals; the owner approves version scope.

## Consequences

### Positive

- Every Aether session has a durable improvement context.
- Real framework failures become evidence instead of hidden fallback events.
- The next minor is selected from accumulated observations rather than speculation.
- Aether Router remains reusable without becoming an evaluator.
- Cross-project contamination is explicitly prohibited.
- Model-backed coordination remains possible but must earn its place through evidence.

### Negative

- Session hooks, measurement storage, reconciliation, and release evidence add implementation complexity.
- Some telemetry may be unavailable and remain unknown.
- A session can initialize the cycle deterministically but still requires Hermes to reason correctly about the task.
- Operational ledgers require schema, lifecycle, and privacy governance.

### Risks

- Metrics may reward invocation volume instead of user outcome.
- A direct takeover may overlap an unresolved Harmonia effect.
- Session completion may be falsely inferred from a per-turn hook.
- A plugin may activate under the wrong project root.
- Version evidence may drift from tags, manifests, or GitHub Releases.

The implementation must use a metric vector rather than one self-score, verify cleanup before direct takeover, use the true session-finalization boundary with crash recovery, fail closed on identity uncertainty, and reconcile SemVer at release gates.

## Validation or review gate

v0.20.0 implementation must demonstrate:

1. a clean new Aether session initializes exactly one cycle record automatically;
2. the first model turn receives the active cycle context even without the memory entry;
3. the active manifest identifies the official baseline, technical predecessor, candidate, hypothesis, status, metrics, and exclusions;
4. `talk_to` is absent while Harmonia and continuity tools remain available;
5. applicable specialist work attempts Harmonia without a hidden legacy fallback;
6. pre-admission and post-admission failures are distinguished;
7. direct takeover cannot begin until potentially accepted effects and cleanup are reconciled;
8. a repaired framework defect passes deterministic verification and is retried through Harmonia;
9. session interruption is preserved and reconciled rather than marked complete;
10. Aether Router metadata and available usage are recorded without secrets;
11. unavailable usage remains explicitly unknown;
12. another project's Hermes profile cannot initialize or mutate the Aether cycle;
13. session evidence produces patch or minor signals without automatically approving a version;
14. release evidence is generated from validated facts rather than model prose;
15. no architecture, including an LLM coordinator, is treated as the predetermined next minor.

## Implementation authorization

Initial approval of this record authorized documentation alignment and preparation of a v0.20.0 implementation plan. On 2026-07-28, the owner separately authorized local plugin/source implementation, manifest loading, the project-scoped ledger, measurement, isolation, and tests. The resulting plugin is implemented default-off.

That separate authorization does not authorize Harmonia activation, coordination-key creation, runtime restart, migration, merge, tag, release, deployment, publication, spending, or model/provider changes.

## References

- Self-improvement operating model: `docs/knowledge/SELF_IMPROVEMENT_CYCLE.md`
- Active cycle manifest: `docs/releases/v0.20.0/CYCLE.yaml`
- Hermes learning model: `docs/knowledge/HERMES_LEARNING_MODEL.md`
- Multi-agent model: `docs/knowledge/MULTI_AGENT_MODEL.md`
- Product authority: `docs/knowledge/AUTHORITY.md`
- Product completion contract: `docs/product/COMPLETION.md`
- v0.19.x closeout: `docs/releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`
