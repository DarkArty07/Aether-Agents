# Aether Agents v0.20.0 — Self-Improvement Instrumentation

v0.20.0 brings the last two weeks of verified development back onto `main` and publishes it as an honest, default-off capability boundary.

## Highlights

- **Bounded Harmonia foundation:** the internal v0.19.x technical train is integrated with project-scoped contracts, durable evidence, lifecycle fencing, deterministic bounded selection, semantic handoff, cleanup, and zero-survivor verification. Harmonia remains disabled by default.
- **Self-improvement instrumentation:** a Hermes lifecycle plugin can record redacted, project-local session, tool, model, and Harmonia facts without storing prompts, responses, arguments, results, or secrets.
- **Independent correction:** an external adversarial audit found integration-contract, identity, schema, lifecycle, manifest, evidence, and replay defects. A separate review reproduced residual gaps and corrected them before release.
- **Repository governance:** `main` is now the latest integrated, tested state. Agents may complete gated GitHub lifecycle operations automatically, while activation, deployment, migrations, credentials, spending, and regression acceptance remain separate boundaries.
- **Automatic release reflection:** annotated SemVer tags are validated against the exact `origin/main` commit, package version, README, changelog, and release notes before GitHub Release creation.

## Important capability boundary

This release is **instrumentation, not causal self-improvement**.

It does not yet provide:

- a frozen evaluator the candidate cannot edit;
- isolated baseline and candidate executions;
- before/after comparison against a fixed task contract;
- automatic promotion;
- runtime rollback after promotion;
- live Harmonia activation or production deployment.

The plugin is not enabled in the release configuration. Installing or updating to v0.20.0 does not activate Harmonia or start a self-modifying runtime.

## Correctness and isolation fixes

- Harmonia classification now reads the real public `error.code`, `state`, and `uncertainty` contract.
- Host-supplied tool status takes precedence over local inference, preventing known failures from being recorded as success.
- Tool observations are scoped by session, turn, API request, and call identity, preserving real retries while duplicate deliveries remain idempotent.
- Foreign workspaces cannot redirect evidence through environment variables or explicit project-root assertions.
- Resumed sessions initialize lazily; linked worktree commits resolve correctly; dirty baselines are digested; interrupted turns remain visible without permanently poisoning a session.
- Manifest drift and incompatible ledger schemas fail visibly.
- Internally signed `dispatch.unknown` events are authenticated correctly during replay, removing the intermittent concurrent reconciliation failure.

## Verification

The exact committed release tree passed:

- 54 self-improvement tests;
- 944 coordination tests;
- 1198 repository tests;
- Ruff;
- compileall;
- package build;
- Python 3.11 and 3.12 CI;
- release-governance and PR-target checks;
- clean-checkout dependency verification with MCP 1.29.0.

## Upgrade notes

- No runtime configuration migration is required.
- The supported `mcp` dependency is capped below 2.0 because Olympus currently uses the MCP 1.x `Server.list_tools` API.
- Existing local runtime configuration remains untouched by the release.

## Evidence

- [External logic audit](./EXTERNAL_LOGIC_AUDIT.md)
- [External correction report](./EXTERNAL_CORRECTION_REPORT.md)
- [Independent Phase 1 review](./INDEPENDENT_PHASE1_REVIEW.md)
- [Implementation report](./IMPLEMENTATION_REPORT.md)
- [Benchmark report](./BENCHMARK_REPORT.md)
- [Cycle manifest](./CYCLE.yaml)
