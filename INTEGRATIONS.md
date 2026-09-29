# Aether Integrations Index

**Purpose:** keep one concise, reviewable record of the external and companion projects Aether deliberately relies on, what each one contributes, why it was adopted, and what problem it is meant to solve.

This is an architectural integration index, not a duplicate of `pyproject.toml` or `uv.lock`. Ordinary package dependencies, test libraries, transitive dependencies, model vendors, and every bundled Hermes tool are out of scope unless Aether deliberately adopts them as a named capability or architectural dependency.

## Status vocabulary

- **FOUNDATION** — Aether's product or method is deliberately built on this project.
- **ACTIVE** — enabled in the current Aether runtime/configuration and used as a capability.
  Effective enablement is installation-specific and local (see [`docs/authority.md`](docs/authority.md));
  the status marks an owner-selected capability, and each entry note states its verified limit.
- **OPTIONAL** — installed or available to Aether, but not required by the normal workflow.
- **RETIRED** — previously adopted but no longer used; keep the entry long enough to preserve the reason for removal.

A project should not be added here merely because it was researched. Add it when Aether actually adopts, installs, enables, or deliberately carries it as an available capability.

## Current registry

| Project | Status | Scope | Integration point | Why Aether uses it | Problem it solves |
|---|---|---|---|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | **FOUNDATION** | All roles / runtime | Managed `hermes-agent` runtime, profiles, tools, board, dispatcher, worktrees, sessions, hooks, skills | Reuse a mature agent/runtime substrate instead of rebuilding execution infrastructure | Agent loop, tool execution, durable coordination, retries/reclaim, process spawning, worktrees, review/lifecycle, memory and skills |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | **FOUNDATION** | Software-engineering method across Morfeo → Supervisor → Implementer | `.specify/` plus generated `speckit-*` skills; local materialization currently records Spec Kit `0.16.4` | Reuse an established Spec-Driven Development method instead of inventing Aether's own software methodology | Turns owner intent into explicit specifications, plans, tasks, quality checks and convergence artifacts; reduces ambiguity and implementation drift |
| [Aether Router](https://github.com/DarkArty07/aether-router) | **ACTIVE** | Model access for Aether profiles | Hermes custom provider `custom:aether-router` | Centralize model/provider access outside the role logic and keep routing policy independent from Aether Agents | Model routing, provider abstraction, credentials/access path, context/model selection and model-economics concerns |
| [Context7](https://github.com/upstash/context7) | **ACTIVE** (configuration-dependent) | Primarily Morfeo research/design | Optional MCP server, owner-selected; the packaged Aether profiles ship no `context7` entry | Give Morfeo current, library-specific documentation instead of relying on stale model knowledge or generic web results | Current APIs, SDK/framework documentation, configuration, migrations and version-specific usage during design/research |
| [Exa](https://github.com/exa-labs/exa-py) | **ACTIVE** (configured in packaged profiles; local credentials required) | Primarily Morfeo research | Hermes web search/extract backend configured as `exa` in the packaged profile resources | Give Morfeo general current-web discovery and extraction beyond library documentation | Fresh public-web research, source discovery and page extraction when Context7 is not the right source |
| [Graphify Python](https://github.com/Graphify-Labs/graphify) | **OPTIONAL** | All three roles; project/revision graphs and separate project/role experiences | Packaged `aether-project-knowledge` native Hermes plugin, two canonical skills and isolated hash-locked `graphifyy==0.9.54` component | Reuse structural extraction and graph navigation while Aether binds identity, coordinates writes and separates notes | Repeated repository discovery, stale maps and loss of useful technical experiences between sessions; savings remain to be measured |

## Integration notes

### Hermes Agent

Hermes is Aether's runtime substrate, not just another tool. Aether deliberately keeps ownership boundaries explicit: Hermes owns generic agent/runtime mechanisms; Aether owns the three-role contract, authority model, Objective Contracts, policy, product packaging and qualification.

The exact Hermes source/version used for a release is governed by Aether's release lock and `HERMES_LOCAL_PATCHES.md`; this index should not become a second version authority.

### GitHub Spec Kit

Spec Kit is Aether's methodological foundation. Aether distributes its phases across the three roles rather than replacing them with a competing planning system. The current local materialization reports `speckit_version: 0.16.4` and exposes ten `speckit-*` skills for constitution, specify, clarify, plan, tasks, analyze, checklist, implement, converge and tasks-to-issues workflows.

Spec Kit artifacts remain project artifacts. Aether may adapt ownership and unattended handoffs, but should record meaningful deviations instead of silently forking the method.

### Aether Router

Aether Router is a first-party companion project rather than a third-party dependency. Aether profiles use it as a custom Hermes model provider so model routing does not become embedded in Morfeo, Supervisor or Implementer behavior.

The Router is independently versioned and operated. Aether Agents should depend on its public/provider contract, not its internal implementation.

### Context7

Context7 is the owner-selected documentation MCP server for Morfeo research and design: it fetches up-to-date documentation for libraries, frameworks, SDKs, APIs and tooling. It is not a replacement for general web research, codebase inspection or project memory.

**Verified status and limit.** The packaged Aether profile resources do not enable Context7: `src/aether_agents/resources/profiles/morfeo/config.yaml` configures the `exa` web backends and declares no `context7` or `mcp_servers` entry, and `docs/guides/morfeo-mcp.md` records that Context7 and other configured MCP servers are not federated through Aether's Morfeo MCP surface. Effective enablement is therefore installation-specific and local, not portable public status. An installation that enables it should record its own invocation and version separately.

The owner-selected local template invokes `@upstash/context7-mcp` without an explicit package version, so that configuration floats rather than release-pins the package. That is a limit of the local recipe, not a shipped Aether default; if reproducible tool behavior becomes a release requirement, the pin decision belongs to the installation that enables the server.

### Exa

The packaged Aether profile resources configure Hermes's web search/extract backend as `exa` for all three roles (`src/aether_agents/resources/profiles/*/config.yaml`). It complements Context7:

- **Context7:** authoritative/current developer documentation.
- **Exa:** broad public-web discovery and extraction.

Aether consumes Exa through Hermes's web capability rather than owning a direct Exa SDK integration. Effective availability still depends on the local credential each installation supplies for the provider; the packaged configuration records no key material.

### Graphify

The selected distribution is the Python project `Graphify-Labs/graphify`, package `graphifyy`, not the separate `rhanka/graphify` TypeScript port. Historical project-local skills are not the managed integration or its version authority.

Aether packages `project_knowledge` and `work_memory` with the same operations for Morfeo, Supervisor and Implementer. The component is installed separately with the hash lock under `src/aether_agents/resources/graphify/`; Graphify is not a dependency of the Hermes-free manager import path. The native MCP is not required and does not by itself expose the update/save/reflect operations this integration needs.

Structural code and supported Markdown navigation are implemented. Rich semantic extraction and model-driven qualification remain pending. Graphs are revision-scoped shared derivatives; notes, original answers and signal-only reflections belong to a project/role namespace. A stable Aether lock, explicit path selection and Python reflection without a graph address the behaviors reproduced in the audit.

Keep this entry `OPTIONAL`: portable templates are disabled until explicitly configured, and package inclusion does not establish live activation or measured token savings. See the [project-knowledge guide](docs/guides/project-knowledge.md), [005 specification](specs/005-project-knowledge-graphify/spec.md) and implementation registry for current limits. Retire or disable the component if its measured cost, correctness or maintenance burden outweighs the exploration it avoids; normal source-file tools remain available.

## Update rule

Whenever Aether deliberately adopts or retires a named external/companion capability, update this file in the same change that introduces or removes the integration. At minimum record:

1. **What it is** and its canonical upstream/source.
2. **Status** (`FOUNDATION`, `ACTIVE`, `OPTIONAL`, or `RETIRED`).
3. **Where it is integrated** and which role(s) use it.
4. **Why Aether adopted it** instead of solving the problem itself.
5. **What concrete problem it is expected to solve or reduce.**
6. **Version/pinning policy** when reproducibility matters.
7. **Removal or downgrade condition** when the integration is experimental or replaceable.

Do not promote a researched candidate to `ACTIVE` until there is repository or runtime evidence that Aether actually uses it. When the evidence is installation-specific, keep the entry `ACTIVE` but state the verified limit in the entry note rather than asserting a shipped default.

## Current exclusions worth remembering

- **Hindsight:** Hermes contains native Hindsight support and Aether has runtime artifacts related to it, but Morfeo's current `memory.provider` is empty. It is therefore **not an active Aether integration**.
- **RTK:** researched as a promising Hermes terminal-output optimization, but not yet installed in Aether. Do not list it as active until its plugin/tool integration is actually added and verified.
- Ordinary dependencies such as `jsonschema`, Hatchling, pytest, PyYAML and Ruff remain governed by `pyproject.toml`/`uv.lock`, not this architectural index.
