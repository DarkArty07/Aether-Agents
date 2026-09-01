# Aether Agents documentation

Aether is a multi-agent software-engineering product built on [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) and the GitHub Spec Kit method. This documentation describes the behavior present in this repository's current build. It is not a release claim: the project remains in operational-reliability stabilization, and its release path is not qualified.

## Start here

1. Read [Authority and status](authority.md) to learn which artifact answers which question and where current implementation status is recorded.
2. Read [Product boundary](product-boundary.md) and [roles and authority](roles-and-authority.md) before operating or changing a role resource.
3. For a local, provider-free inspection path, read [Getting started](getting-started.md) and the [CLI reference](reference/cli.md).
4. Follow the appropriate guide for [project initialization](guides/project-initialization.md), [Objective Contracts](guides/objective-contracts.md), [execution](guides/execution.md), [observation](guides/observation.md), or [policy and recovery](guides/policy-and-recovery.md).

## Current capability status

`docs/capabilities.toml` is the implementation-status and traceability registry. Its committed, generated rendering is [Capability coverage](reference/capabilities.md). Use it to find the current status, source paths, and verification for a public Aether surface; do not treat it as design or behavioral authority.

The current build contains tested `aether init` and `aether observe` behavior, a local lifecycle candidate, two Hermes plugins, Objective Contract handoff support, portable role resources, and a narrow policy hook. It also contains explicit unsupported or unfinished surfaces. See [limitations and troubleshooting](reference/limitations-and-troubleshooting.md) before treating a candidate interface as an installable product capability.

## Documentation map

- [Authority and status](authority.md) — documentary ownership and how to resolve a conflict.
- [Getting started](getting-started.md) — safe local discovery without a provider call.
- [Product boundary](product-boundary.md) — what Aether adds to Hermes and what it deliberately reuses.
- [Roles and authority](roles-and-authority.md) — the owner, Morfeo, Supervisor, and Implementer responsibilities.
- [Lifecycle](guides/lifecycle.md) — the current direct/pipeline model and evidence boundaries.
- [Project initialization](guides/project-initialization.md) — existing-Git-root initialization and exact Hermes Project binding.
- [Objective Contracts](guides/objective-contracts.md) — durable handoff artifacts and validation.
- [Execution](guides/execution.md) — boards, session affinity, worktrees, and review.
- [Observation](guides/observation.md) — bounded observation reads and the qualification laboratory.
- [Policy and recovery](guides/policy-and-recovery.md) — the PD-71 edge guard and rollback-first recovery.
- [CLI reference](reference/cli.md) — parser-backed commands and current limitations.
- [Plugins and tools](reference/plugins-and-tools.md) — package entry points and registered Aether tools.
- [Limitations and troubleshooting](reference/limitations-and-troubleshooting.md) — honest current limits and safe diagnostic steps.
