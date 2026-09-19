# Aether Agents

Aether Agents is a multi-agent software-engineering product and method. It adapts [Hermes Agent](https://hermes-agent.nousresearch.com/docs) as the runtime substrate and [GitHub Spec Kit](https://github.com/github/spec-kit) as the specification method, while defining Aether's role, handoff, policy, and qualification boundaries.

**Status:** the checked-in tree carries the owner-authorized `1.0.0rc3` release candidate, the successor to the local rc.2 candidate: package version `1.0.0rc3` and annotated tag `v1.0.0-rc.3`. The tag is a local-only candidate that is not pushed and not published in this objective, with `release_impact = major`, `release_action = prepare`, `release_channel = prerelease`. The local rc.2 tag and activation history remain immutable and are not acceptance; [`v1.0.0-rc.1`](https://github.com/DarkArty07/Aether-Agents/releases/tag/v1.0.0-rc.1) remains published and byte-immutable but rejected, and must not be activated. This milestone is bounded and pre-stable: explicitly **not** stable `1.0.0`, **not** a PyPI or other package-index publication, and **not** a WSL2 qualification result. Issue #261 therefore stays open with the stable, PyPI/OIDC and WSL2 gates outstanding. Feature expansion and nonessential Hermes changes remain frozen while the rolling reliability gate is qualified.

## Documentation

Start with the [documentation index](docs/index.md). The current documentation owns behavior available in this build; [`docs/capabilities.toml`](docs/capabilities.toml) is the sole current implementation-status and traceability registry. This README is a portal, not a second status table or design manual.

- [Getting started](docs/getting-started.md) and the [product boundary](docs/product-boundary.md)
- [Roles and authority](docs/roles-and-authority.md), [lifecycle](docs/guides/lifecycle.md), and [execution](docs/guides/execution.md)
- [Project initialization](docs/guides/project-initialization.md) and [Objective Contracts](docs/guides/objective-contracts.md)
- [Optional project knowledge and role work memory](docs/guides/project-knowledge.md)
- [Observation](docs/guides/observation.md), [Telegram Monitor](docs/guides/telegram-monitor.md), and [policy and recovery](docs/guides/policy-and-recovery.md)
- [CLI reference](docs/reference/cli.md), [plugins and tools](docs/reference/plugins-and-tools.md), [capabilities reference](docs/reference/capabilities.md), and [limitations and troubleshooting](docs/reference/limitations-and-troubleshooting.md)

## Current beta boundary

Aether uses Hermes-native Projects, boards, worktrees, review, lifecycle, profiles, and tools; it does not replace Hermes with another queue, scheduler, worker manager, or generic manual. A documented transitional downstream is no longer the runtime policy: under PD-49/61/64/65 the executable Hermes source is the maintained fork `DarkArty07/aether-hermes` branch `aether-main`, bound by the release lock's `schema_version` 4 `maintained_fork` source mode through repository, exact commit, source-tree digest, artifact closure and provenance. The fixed public `v2026.8.18` tree remains the reference for upstream-compatible behavior and historical evidence, and `.patch` files stay audit/reconstruction evidence that is never replayed onto an active runtime.

Immutable release code and Graphify components live under the Aether XDG data root, while every mutable Hermes home, session, board, credential, memory, observation, monitor and knowledge artifact stays under the Aether XDG state root. `aether update` is the only supported promotion and activation boundary: its local-candidate route previews explicit clean Aether and fork commits without mutating anything, activation is explicit and may interrupt Aether-owned instances, a partial transition is recoverable, and rollback restores product code without rolling user state backward.

The `aether init` command initializes **an existing Git repository root only**. It writes the portable project marker and binds it to exactly one non-archived native Hermes Project whose primary path matches exactly; `--hermes-project ID` resolves an otherwise ambiguous exact-path match. It neither initializes Git nor creates or changes a native Hermes Project.

The operational `start`, `stop`, `restart`, `status`, and `reconcile` commands remain explicit unsupported placeholders. Public release publication, provider-backed live qualification, credentials, deployment, and activation of a managed service are outside this build's supported boundary. The Telegram Monitor (`aether monitor`, `docs/guides/telegram-monitor.md`) is implemented with deterministic packaging and an offline qualification lane; its real hourly model/Telegram qualification and installation-local activation remain pending terminal integration.

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
