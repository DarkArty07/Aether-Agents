# Technical Debt — v0.19 Autonomous Coordination

## TD-v0.19-001 — Risk-based Athena routing in Hermes

**Status:** Open<br>
**Owner:** Hermes architecture / user approval<br>
**Priority:** Deferred until the kernel-backed architecture is proven<br>
**Introduced:** 2026-07-25

### Context

Athena has been used too broadly as a recurring review gate. Invoking it for ordinary changes and every project phase creates excessive latency, repeated correction/review loops, and slows validation of the underlying coordination architecture.

The user has suspended Athena globally until explicit reactivation. This suspension is current policy; it is not an authorization to remove the Athena profile or implement a replacement reviewer.

### Debt

Hermes' future system prompt and routing policy must teach the orchestrator to invoke Athena selectively rather than universally. The policy must distinguish at least:

- **Required:** material authentication or authorization changes, trust-boundary changes, credential custody, externally exposed security-sensitive releases, or an explicit user-mandated security gate.
- **Optional/consultative:** ambiguous security design where independent adversarial analysis materially improves the decision.
- **Not required:** ordinary implementation, documentation, deterministic bug fixes, low-risk configuration, routine milestone progression, and work already covered by reproducible tests and direct Hermes verification.
- **Forbidden:** whenever the user has suspended Athena for the project or task.

### Acceptance criteria for future closure

1. Hermes' versioned system prompt defines risk-based Athena routing and does not make Athena a universal phase gate.
2. User/project policy can disable Athena and takes precedence over default routing.
3. Ordinary QA has a deterministic path that does not require a Daimon review.
4. Security-critical boundaries retain an explicit escalation path when Athena is enabled.
5. Tests or controlled scenarios demonstrate correct `required`, `optional`, `not required`, and `forbidden` routing.
6. Existing architecture and release documents that assume mandatory Athena gates are reconciled.
7. The user explicitly approves reactivation or the revised routing policy before Athena is used again.

### Current containment

- Do not dispatch work to Athena until explicit user instruction.
- Use deterministic tests, direct Hermes review, reproducible evidence, and risk-proportional validation.
- Do not implement dynamic Daimon hiring as part of this debt. Dynamic capability-based hiring is a separate future architectural requirement.
