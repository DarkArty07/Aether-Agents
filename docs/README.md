# Aether Agents Documentation

> **Status:** Documentation map — current
> **Audience:** Users, operators, contributors, maintainers, and incoming agents

This directory is the canonical map of Aether Agents documentation. It separates product intent, verified system knowledge, technical architecture, operational guidance, and historical evidence so that no agent has to infer the project's purpose from release artifacts.

## Read this first

| If you are… | Start here | Then read |
|---|---|---|
| An incoming agent | [Agent onboarding](./AGENT_ONBOARDING.md) | Product → Knowledge → relevant architecture |
| Evaluating the project | [Product documentation](./product/README.md) | [Architecture](./architecture/README.md) |
| Installing or using Aether | [Guides](./guides/) | [Reference](./reference/README.md) |
| Operating a live installation | [Operations](./operations/README.md) | [Knowledge](./knowledge/README.md) |
| Contributing code or documentation | [Contributing](./contributing/README.md) | [Decisions](./decisions/README.md) |
| Investigating a release | [Release evidence](./releases/) | The specific release closeout or evidence document |

## Active Orca transition

- [v0.22.0 — Orca Integration Foundation](./releases/v0.22.0/ROADMAP.md): scope closed at accepted M5.4; source Release pending; no activation.
- [v0.23.0 — Orca Production Dogfood](./releases/v0.23.0/ROADMAP.md): approved plan for real repair-first Aether MCP + Orca use and generic-agent refinement; not yet implemented or activated.
- [v0.24.0 — Gradual Workflow Migration](./releases/v0.24.0/ROADMAP.md): approved evidence-driven direction; process order intentionally not frozen.
- [Governing product decision](./decisions/PDR-0014-versioned-orca-production-adoption.md) and [cross-version plan](./plans/2026-08-09-orca-production-adoption.md).

Current runtime truth remains distinct from approved direction: the v0.22.0 Aether MCP is default-off, unregistered, and zero-tool until the v0.23.0 production-entry gate passes.

## Documentation hierarchy

When documents disagree, use this order:

1. **Approved product documentation** in `docs/product/` — definition, vision, mission, objectives, scope, principles, experience, and completion contract.
2. **Approved architecture decisions** in `docs/decisions/` and current architecture in `docs/architecture/`.
3. **Verified current-system knowledge** in `docs/knowledge/`.
4. **Current guides, reference, and operations documentation**.
5. **Implementation plans and active release designs**.
6. **Historical evidence, handoffs, benchmarks, and test drives**.
7. **Conversation summaries or inferred intent**.

Source code and executable tests remain authoritative for current mechanical behavior. They do not define product purpose by themselves.

## Documentation families

### Product — `docs/product/`

Normative answers to:

- Why does Aether Agents exist?
- For whom is it built?
- What problem does it solve?
- What future does it pursue?
- What belongs inside or outside the product?
- How should the product feel and expose internal work?
- When is a software project actually complete?
- Which principles constrain technical decisions?

### Knowledge — `docs/knowledge/`

Shared project knowledge needed to reason correctly:

- stable concepts and terminology;
- current versus target system distinctions;
- constraints, assumptions, and invariants;
- ownership and authority boundaries;
- verified capabilities and known limitations.

### Architecture — `docs/architecture/`

Technical system explanation:

- system context and components;
- orchestration and session lifecycle;
- Daimon roles and authority;
- the retired Olympus and disconnected native runtimes;
- the Hermes product layer, protected `.aether` history, and target Orca boundary;
- configuration, runtime, data, and trust boundaries.

### Guides — `docs/guides/`

Task-oriented instructions for installation, configuration, first use, the current specialist capability gap, protected historical state, and gateway use.

### Reference — `docs/reference/`

Exact, lookup-oriented contracts: tools, actions, schemas, configuration keys, environment variables, file layout, commands, and compatibility notes.

### Operations — `docs/operations/`

Runbooks for health checks, updates, backups, gateway operation, troubleshooting, recovery, incident handling, and retirement of legacy services such as Honcho.

### Contributing — `docs/contributing/`

Developer setup, repository conventions, testing, documentation standards, architecture-change workflow, and release process.

### Decisions — `docs/decisions/`

Durable product and architecture decisions, including rationale, alternatives, consequences, status, and supersession. Decisions must not live only in chat or `.aether`.

### Plans, releases, and evidence

- `docs/plans/` — proposed or approved implementation plans.
- `docs/releases/` — version-specific designs, evidence, closeouts, and migration records.
- `docs/test-drives/` — exploratory evaluations and observed behavior.

These are evidence and execution artifacts. They are not substitutes for product vision.

## Document status vocabulary

Every normative document should declare one status:

- **DISCOVERY** — incomplete; questions remain and content is not approved.
- **PROPOSED** — coherent proposal awaiting owner approval.
- **APPROVED** — owner-approved direction; implementation may still be unauthorized.
- **CURRENT** — describes verified behavior or an active operational contract.
- **SUPERSEDED** — replaced by a named newer document or decision.
- **HISTORICAL** — retained as evidence, not active direction.

Approval of documentation does not authorize implementation, deployment, spending, credentials, publication, or other external effects.

## Maintenance rules

1. Do not infer product purpose from code or release chronology.
2. Do not present target architecture as current behavior.
3. Link facts to their canonical source instead of copying them across many files.
4. Update cross-references when a canonical section or document changes.
5. Mark superseded decisions explicitly; never leave contradictory decisions active.
6. Keep secrets, credentials, personal data, and runtime databases out of documentation.
7. Validate links, commands, file paths, and examples before marking a guide current.
