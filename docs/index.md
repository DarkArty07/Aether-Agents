# Aether Agents documentation

Aether is a multi-agent software-engineering product built on [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) and the GitHub Spec Kit method. This documentation describes the behavior present in this repository's current build. It is not a release claim: the project remains in operational-reliability stabilization, and its release path is not qualified.

This index is navigation only and routes reader questions to the appropriate guide, reference, or authority artifact. For the complete reader-facing placement and conflict-resolution map across all artifact classes, see [Authority and artifact ownership](authority.md).

This source tree defines the local-only `1.0.0rc9` compatibility bridge. It
reads release-lock schema 4 and schema 5, still emits schema 4, and does not
publish Morfeo MCP. Source and local tags do not prove runtime activation or
agent behavior. Consult `aether doctor` and a verified cutover receipt.
The executable Hermes source is Aether's maintained fork
`DarkArty07/aether-hermes` branch `aether-main`, bound
by release-lock schema 4 or 5 `maintained_fork` and installed through `aether update`.
In the historical rc3 qualification, active release `1.0.0rc3-8987f650c027ad09` was
locally selected from Aether merge `d8ff984c67bfc147ac9c83cf8a34a72edc27c8df` and
maintained-fork commit `aed6591a69f453a1867b73628603e7b53ba40ffc`; `aether doctor`
reported `ready` with 22/22 callbacks. On the original large #417 trace, status completed
in 19.266s then 15.598s, changes in 15.576s, and post-reactivation status in 34.655s then
23.495s; watch emitted its baseline and all requests remained below the 420-second native
bound. One rollback to `1.0.0rc2-b3ad4dd42eb0e1da` and forward reactivation preserved
mutable state. This is not a public GitHub Release, stable `1.0.0`, a package-index
publication or a WSL2 qualification result; the annotated tag remains local-only, and
issue #261 stays open with those publication and platform gates outstanding. See
[Lifecycle](guides/lifecycle.md), [Policy and recovery](guides/policy-and-recovery.md) and
[CLI reference](reference/cli.md).

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
- **How does one objective keep its route, stop conditions and continuity across sessions and contracts?**
  See [Objective Plans](guides/objective-plans.md).
- **How are objective outcomes, acceptance criteria, and handoffs structured?**
  See [Objective Contracts](guides/objective-contracts.md).
- **How do multi-agent task execution, worktree isolation, and review cycles operate?**
  See [Execution](guides/execution.md).
- **What is the current lifecycle execution flow and evidence model?**
  See [Lifecycle](guides/lifecycle.md).

### Operations, safety, and diagnostics
- **How do I run read-only system observations or qualification checks?**
  See [Observation](guides/observation.md).
- **How do I read or control the hourly Telegram progress reports?**
  See [Telegram Monitor](guides/telegram-monitor.md).
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
