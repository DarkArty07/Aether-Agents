# Authority and current status

Aether keeps design intent, current behavior, implementation status, and release history in different artifacts. A later artifact cannot silently override an earlier owner-approved decision. When artifacts disagree, resolve the conflict at the artifact that owns the question and preserve historical evidence rather than editing it to resemble the present.

| Artifact | Owns | Does not own |
| --- | --- | --- |
| [`DESIGN.md`](../DESIGN.md) | Accepted conceptual product principles, roles, authority, and high-level decisions | Detailed implementation status or release proof |
| [`ROADMAP.md`](../ROADMAP.md) | Design-area index, dependencies, future areas, visible release limitations | A workflow engine or automatic authority |
| `specs/**/spec.md` | Normative requirements and decisions for the named stage | Current source behavior when implementation differs |
| `specs/**/research.md`, plans, tasks, and evidence | Historical rationale, qualification evidence, and planning context | A replacement for current behavior or owner intent |
| `docs/` | Current behavior available in this build and how to use or diagnose it | Conceptual design, normative requirements, or live runtime state |
| [`docs/capabilities.toml`](capabilities.toml) | Current implementation status and paths that trace public surfaces to docs, source, and verification | Behavioral contract or design authority |
| [`CHANGELOG.md`](../CHANGELOG.md) | Release deltas, including `Unreleased` changes | The complete current manual |
| [`README.md`](../README.md) | Concise project portal and orientation | A second full status or design manual |
| [`INTEGRATIONS.md`](../INTEGRATIONS.md) | Deliberately adopted external and companion integration index | Dependency lock or current runtime configuration |

## How to read a capability status

The registry uses only these statuses:

- **implemented** — the source and focused verification support the documented current behavior.
- **partial** — some useful behavior exists, but a stated functional or qualification boundary is absent.
- **transitional** — a candidate or transition mechanism is intentionally present while its public qualification or retirement condition remains open.
- **unsupported** — the visible interface refuses rather than pretending to perform the promised product effect.
- **deprecated** — a retained compatibility surface has a documented replacement or retirement path.

The registry's generated report sorts capability IDs and lists its documents, specifications, source files, tests, and current limits. The referenced source and tests are evidence for a claim; direct execution is stronger evidence when it is available.

## Historical artifacts remain historical

Specifications, research, plans, evidence, the changelog, and `INCOMPLETE_IMPLEMENTATIONS.md` remain in place because they explain why the present state exists. They must not be rewritten or treated as an active implementation-status registry. In particular, a candidate lifecycle implementation or a local qualification result is not an installed service, public release, or provider-backed success claim.

## Updating this documentation

A public-facing surface change needs a corresponding registry update or a documented non-applicability rationale. Internal refactors and behavior-preserving fixes do not require ceremonial documentation churn. Current docs must not include credentials, private profile content, sessions, model/provider bindings, editable-runtime revisions, or machine-specific paths.
