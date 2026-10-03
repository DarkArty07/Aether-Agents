# Aether Agents documentation

Aether Agents is a multi-agent software-engineering product built on
[Hermes Agent](https://hermes-agent.nousresearch.com/docs/) and the GitHub Spec Kit method.
This documentation describes the behavior of the `1.0.0` release in this repository.
`1.0.0` is the final feature set: the maintainer froze features at this release and
publishes it as-is (see the [release record](../specs/v1-stable-release/spec.md) and the
[known issues](reference/limitations-and-troubleshooting.md#known-issues)).

This index is navigation only. For the reader-facing placement and conflict-resolution
map across all artifact classes, see [Authority and artifact ownership](authority.md).
Use `aether doctor --json` to identify the release that is actually installed; the
source version and tags never prove what is active.

## Start here

1. [Installation](installation.md) — download the release bundle, install it with
   `aether setup`, configure a model for each role.
2. [Getting started](getting-started.md) — initialize a project, launch Morfeo and learn
   the provider-free inspection commands.
3. [Tutorial: your first objective](tutorials/first-objective.md) — the direct route and
   the full pipeline on a practice repository.

## Tutorials

- [Your first objective](tutorials/first-objective.md): adopt a project, complete a direct
  change, plan with `/aether-plan`, deliver through the pipeline and observe it.
- [Use Aether with Claude Code](tutorials/claude-code.md): Morfeo over MCP, and Claude Code
  as an opt-in Implementer.
- [Give every role a map of your project](tutorials/project-knowledge.md): install and enable
  Graphify-based project knowledge and role work memory.

## Concepts

- [Product boundary](product-boundary.md): what Aether adds to Hermes and what it reuses.
- [Roles and authority](roles-and-authority.md): Morfeo, Supervisor and Implementer.
- [Lifecycle](guides/lifecycle.md) and [Execution](guides/execution.md): routes, boards,
  worktrees, review and closeout.

## Navigate by question

### Architectural authority and product boundaries
- **Which artifact owns which decision, where does information belong, and how are conflicts resolved?**
  See [Authority and artifact ownership](authority.md).
- **What does Aether add to Hermes, and what are the system boundaries?**
  See [Product boundary](product-boundary.md).
- **What are the product roles (Morfeo, Supervisor, Implementer) and their authority limits?**
  See [Roles and authority](roles-and-authority.md).

### Getting started and project setup
- **How do I install, update, roll back or uninstall Aether?**
  See [Installation](installation.md).
- **What should Aether do without repeated reminders, and where are those instructions?**
  See [Expected behavior of Aether agents](guides/expected-behavior.md), including triggers,
  limits and the distinction between source instructions, installation and observed conduct.
- **How do I explore Aether without provider calls or credentials?**
  See [Getting started](getting-started.md#inspect-without-changing-anything).
- **How do I launch Aether in an already initialized project, and which commands recover an active installation?**
  See [Launch Aether in an initialized project](getting-started.md#launch-aether-in-an-initialized-project) and the [lifecycle recovery surfaces](guides/lifecycle.md#recovery-surfaces).
- **How do I bind an existing Git repository root to a Hermes Project?**
  See [Project initialization](guides/project-initialization.md).

### Project knowledge and learning
- **How do all three roles reuse and maintain a project's technical map?**
  See [Project knowledge and role work memory](guides/project-knowledge.md).
- **How are experiences kept separate and the two canonical skills used?**
  See the same guide's experience, storage and tool sections, plus [Plugins and tools](reference/plugins-and-tools.md).

### Objective handoffs, execution, and lifecycle
- **What does explicit `/aether-plan` planning produce, and how does exploration differ?**
  See [Objective Plans](guides/objective-plans.md#exploration-before-a-plan). Generic `/plan`
  is not the Aether planning entry.
- **How does one objective keep its route, stop conditions and continuity across sessions and contracts?**
  See [Objective Plans](guides/objective-plans.md).
- **How are objective outcomes, acceptance criteria, and handoffs structured?**
  See [Objective Contracts](guides/objective-contracts.md).
- **How do multi-agent task execution, worktree isolation, and review cycles operate?**
  See [Execution](guides/execution.md).
- **What is the current lifecycle execution flow and evidence model?**
  See [Lifecycle](guides/lifecycle.md).

### Operations, safety, and diagnostics
- **How do I inspect a compact contract observation?**
  See [Observation](guides/observation.md).
- **Has Aether replaced its hourly Telegram progress reports?**
  No. The owner retired the Aether Monitor and its periodic reports without a replacement.
  Native Hermes cron, ordinary Telegram interaction, and native task/final/input
  notifications remain unchanged. See the [retirement decision](../specs/lab-monitor-retirement/spec.md).
- **What are the edge safety guards and rollback-first recovery policies?**
  See [Policy and recovery](guides/policy-and-recovery.md).
- **What CLI commands and options are supported in this build?**
  See [CLI reference](reference/cli.md).
- **What plugins and registered tools are included in Aether?**
  See [Plugins and tools](reference/plugins-and-tools.md).
- **How can users choose tools for each role, and why does the documented recipe include or exclude them?**
  See [Tool selection by role](guides/morfeo-tool-configuration.md), a user-selected local recipe rather than a mandatory product preset.
- **What are the known current limits and safe diagnostic steps?**
  See [Limitations and troubleshooting](reference/limitations-and-troubleshooting.md).

### Capability implementation status
- **What is the verified implementation status of each public surface?**
  See [Capability coverage](reference/capabilities.md), generated from the authoritative registry in [`docs/capabilities.toml`](capabilities.toml).
