# Changelog

## 0.23.0 — 2026-08-16

### Hermes-only design reset

- Reset Aether Agents to a single Hermes Agent profile with reproducible configuration and GitHub governance.
- Removed the retired multi-agent product runtime, secondary profiles, custom MCP implementation, orchestration stack, product documentation, tests, schemas, scripts, and repository-owned skill catalog.
- Kept credentials, sessions, memories, databases, and runtime skills private and outside Git.
- Preserved Aether Router and Orca as independent external projects; this release does not modify or retire them.
- Replaced code-oriented CI with policy validation for the canonical 17-file manifest and simplified SemVer release automation.

### Breaking impact

- Previous multi-agent control, worker, coordination, installation, and qualification interfaces are no longer shipped.
- Pull requests and issues targeting the removed architecture are superseded by this reset.
- To roll back the versioned repository, use the `v0.22.0` tag or another earlier release.
