# Aether Integrations Index

**Purpose:** keep one concise, reviewable record of the external and companion projects Aether deliberately relies on, what each one contributes, why it was adopted, and what problem it is meant to solve.

This is an architectural integration index, not a duplicate of `pyproject.toml` or `uv.lock`. Ordinary package dependencies, test libraries, transitive dependencies, model vendors, and every bundled Hermes tool are out of scope unless Aether deliberately adopts them as a named capability or architectural dependency.

## Status vocabulary

- **FOUNDATION** — Aether's product or method is deliberately built on this project.
- **ACTIVE** — enabled in the current Aether runtime/configuration and used as a capability.
- **OPTIONAL** — installed or available to Aether, but not required by the normal workflow.
- **RETIRED** — previously adopted but no longer used; keep the entry long enough to preserve the reason for removal.

A project should not be added here merely because it was researched. Add it when Aether actually adopts, installs, enables, or deliberately carries it as an available capability.

## Current registry

| Project | Status | Scope | Integration point | Why Aether uses it | Problem it solves |
|---|---|---|---|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | **FOUNDATION** | All roles / runtime | Managed `hermes-agent` runtime, profiles, tools, board, dispatcher, worktrees, sessions, hooks, skills | Reuse a mature agent/runtime substrate instead of rebuilding execution infrastructure | Agent loop, tool execution, durable coordination, retries/reclaim, process spawning, worktrees, review/lifecycle, memory and skills |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | **FOUNDATION** | Software-engineering method across Morfeo → Supervisor → Implementer | `.specify/` plus generated `speckit-*` skills; local materialization currently records Spec Kit `0.16.4` | Reuse an established Spec-Driven Development method instead of inventing Aether's own software methodology | Turns owner intent into explicit specifications, plans, tasks, quality checks and convergence artifacts; reduces ambiguity and implementation drift |
| [Aether Router](https://github.com/DarkArty07/aether-router) | **ACTIVE** | Model access for Aether profiles | Hermes custom provider `custom:aether-router` | Centralize model/provider access outside the role logic and keep routing policy independent from Aether Agents | Model routing, provider abstraction, credentials/access path, context/model selection and model-economics concerns |
| [Context7](https://github.com/upstash/context7) | **ACTIVE** | Primarily Morfeo research/design | MCP server via `npx -y @upstash/context7-mcp` | Give Morfeo current, library-specific documentation instead of relying on stale model knowledge or generic web results | Current APIs, SDK/framework documentation, configuration, migrations and version-specific usage during design/research |
| [Exa](https://github.com/exa-labs/exa-py) | **ACTIVE** | Primarily Morfeo research | Hermes web search/extract backend configured as `exa` | Give Morfeo general current-web discovery and extraction beyond library documentation | Fresh public-web research, source discovery and page extraction when Context7 is not the right source |
| [Graphify](https://github.com/rhanka/graphify) | **OPTIONAL** | Project/codebase understanding | Project-local Hermes skill plus installed `graphify` CLI; local skill version `0.8.28` | Preserve a reusable structural/semantic graph when a corpus or codebase benefits from relationship-oriented navigation | Re-reading large corpora, cross-file/cross-document relationships, architecture exploration and persistent queryable context |

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

Context7 is currently enabled as an MCP server for Morfeo. Its role is narrow and valuable: fetch up-to-date documentation for libraries, frameworks, SDKs, APIs and tooling when Morfeo is researching or designing.

Current Aether configuration invokes `@upstash/context7-mcp` without an explicit package version. That means the MCP package is presently floating rather than release-pinned; if reproducible tool behavior becomes a release requirement, this should be revisited.

Context7 is not a replacement for general web research, codebase inspection or project memory.

### Exa

Exa is the configured Hermes web search and extraction backend for Morfeo. It complements Context7:

- **Context7:** authoritative/current developer documentation.
- **Exa:** broad public-web discovery and extraction.

Aether currently consumes Exa through Hermes's web capability rather than owning a direct Exa SDK integration.

### Graphify

Graphify is present as a project-local Hermes skill and CLI, but it is **not currently a required runtime integration**: no Graphify MCP is configured in Morfeo's active profile and no `.graphify/` project graph is currently present.

Keep it `OPTIONAL` until Aether deliberately makes a persistent graph part of a normal role workflow. Presence of a skill alone must not be mistaken for an architectural dependency.

## Update rule

Whenever Aether deliberately adopts or retires a named external/companion capability, update this file in the same change that introduces or removes the integration. At minimum record:

1. **What it is** and its canonical upstream/source.
2. **Status** (`FOUNDATION`, `ACTIVE`, `OPTIONAL`, or `RETIRED`).
3. **Where it is integrated** and which role(s) use it.
4. **Why Aether adopted it** instead of solving the problem itself.
5. **What concrete problem it is expected to solve or reduce.**
6. **Version/pinning policy** when reproducibility matters.
7. **Removal or downgrade condition** when the integration is experimental or replaceable.

Do not promote a researched candidate to `ACTIVE` until there is repository/runtime evidence that Aether actually uses it.

## Current exclusions worth remembering

- **Hindsight:** Hermes contains native Hindsight support and Aether has runtime artifacts related to it, but Morfeo's current `memory.provider` is empty. It is therefore **not an active Aether integration**.
- **RTK:** researched as a promising Hermes terminal-output optimization, but not yet installed in Aether. Do not list it as active until its plugin/tool integration is actually added and verified.
- Ordinary dependencies such as `jsonschema`, Hatchling, pytest, PyYAML and Ruff remain governed by `pyproject.toml`/`uv.lock`, not this architectural index.
