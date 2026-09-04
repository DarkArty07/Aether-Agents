# Aether Agents documentation

Aether is a multi-agent software-engineering product built on [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) and the GitHub Spec Kit method. This documentation describes the behavior present in this repository's current build. It is not a release claim: the project remains in operational-reliability stabilization, and its release path is not qualified.

This index is navigation only and routes reader questions to the appropriate guide, reference, or authority artifact. For the complete reader-facing placement and conflict-resolution map across all artifact classes, see [Authority and artifact ownership](authority.md).

## Navigate by question

### Architectural authority and product boundaries
- **Which artifact owns which decision, where does information belong, and how are conflicts resolved?**
  See [Authority and artifact ownership](authority.md).
- **What does Aether add to Hermes, and what are the system boundaries?**
  See [Product boundary](product-boundary.md).
- **What are the product roles (Morfeo, Supervisor, Implementer) and their authority limits?**
  See [Roles and authority](roles-and-authority.md).

### Getting started and project setup
- **How do I explore Aether locally without provider calls or credentials?**
  See [Getting started](getting-started.md).
- **How do I bind an existing Git repository root to a Hermes Project?**
  See [Project initialization](guides/project-initialization.md).

### Objective handoffs, execution, and lifecycle
- **How are objective outcomes, acceptance criteria, and handoffs structured?**
  See [Objective Contracts](guides/objective-contracts.md).
- **How do multi-agent task execution, worktree isolation, and review cycles operate?**
  See [Execution](guides/execution.md).
- **What is the current lifecycle execution flow and evidence model?**
  See [Lifecycle](guides/lifecycle.md).

### Operations, safety, and diagnostics
- **How do I run read-only system observations or qualification checks?**
  See [Observation](guides/observation.md).
- **What are the edge safety guards and rollback-first recovery policies?**
  See [Policy and recovery](guides/policy-and-recovery.md).
- **What CLI commands and options are supported in this build?**
  See [CLI reference](reference/cli.md).
- **What plugins and registered tools are included in Aether?**
  See [Plugins and tools](reference/plugins-and-tools.md).
- **What are the known current limits and safe diagnostic steps?**
  See [Limitations and troubleshooting](reference/limitations-and-troubleshooting.md).

### Capability implementation status
- **What is the verified implementation status of each public surface?**
  See [Capability coverage](reference/capabilities.md), generated from the authoritative registry in [`docs/capabilities.toml`](capabilities.toml).
