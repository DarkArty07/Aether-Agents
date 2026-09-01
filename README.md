# Aether Agents

Aether Agents is a multi-agent software-engineering product and method. It adapts [Hermes Agent](https://hermes-agent.nousresearch.com/docs) as the runtime substrate and [GitHub Spec Kit](https://github.com/github/spec-kit) as the specification method, while defining Aether's role, handoff, policy, and qualification boundaries.

**Status:** the repository contains a beta stabilization build, not a release candidate or a public release. Feature expansion and nonessential Hermes changes remain frozen while the rolling reliability gate is qualified.

## Documentation

Start with the [documentation index](docs/index.md). The current documentation owns behavior available in this build; [`docs/capabilities.toml`](docs/capabilities.toml) is the sole current implementation-status and traceability registry. This README is a portal, not a second status table or design manual.

- [Getting started](docs/getting-started.md) and the [product boundary](docs/product-boundary.md)
- [Roles and authority](docs/roles-and-authority.md), [lifecycle](docs/guides/lifecycle.md), and [execution](docs/guides/execution.md)
- [Project initialization](docs/guides/project-initialization.md) and [Objective Contracts](docs/guides/objective-contracts.md)
- [Observation](docs/guides/observation.md) and [policy and recovery](docs/guides/policy-and-recovery.md)
- [CLI reference](docs/reference/cli.md), [plugins and tools](docs/reference/plugins-and-tools.md), [capabilities reference](docs/reference/capabilities.md), and [limitations and troubleshooting](docs/reference/limitations-and-troubleshooting.md)

## Current beta boundary

Aether uses Hermes-native Projects, boards, worktrees, review, lifecycle, profiles, and tools; it does not replace Hermes with another queue, scheduler, worker manager, or generic manual. A documented transitional downstream is retained only for indispensable qualified runtime fixes and must retire when the exact released upstream behavior passes its gate.

The `aether init` command initializes **an existing Git repository root only**. It writes the portable project marker and binds it to exactly one non-archived native Hermes Project whose primary path matches exactly; `--hermes-project ID` resolves an otherwise ambiguous exact-path match. It neither initializes Git nor creates or changes a native Hermes Project.

The operational `start`, `stop`, `restart`, `status`, and `reconcile` commands remain explicit unsupported placeholders. Public release publication, provider-backed live qualification, credentials, deployment, and activation of a managed service are outside this build's supported boundary.

Non-destructive inspection:

```bash
aether --version
aether observe --help
aether doctor --json
```

`doctor` can honestly return a non-zero readiness result when no managed release is installed.

## Maintainer authorities

- [`DESIGN.md`](DESIGN.md) owns accepted conceptual principles and decisions.
- [`specs/`](specs) owns normative intent; research, plans, and qualification evidence remain historical or evidentiary artifacts.
- [`ROADMAP.md`](ROADMAP.md) describes future work and release-visible limitations.
- [`CHANGELOG.md`](CHANGELOG.md) records release deltas. [`INTEGRATIONS.md`](INTEGRATIONS.md) remains the intentional integration index.
- [`AGENTS.md`](AGENTS.md) states repository evidence, source-resolution, and contribution boundaries.

For generic Hermes operation, consult the [authoritative Hermes documentation](https://hermes-agent.nousresearch.com/docs) rather than copying a second manual here.

## License

MIT — see [LICENSE](LICENSE).
