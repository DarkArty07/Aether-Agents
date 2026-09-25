# Aether Agents

Aether Agents is a multi-agent software-engineering product and method. It adapts [Hermes Agent](https://hermes-agent.nousresearch.com/docs) as the runtime substrate and [GitHub Spec Kit](https://github.com/github/spec-kit) as the specification method, while defining Aether's role, handoff, policy, and qualification boundaries.

**Status:** this source revision defines `1.0.0rc13` / `1.0.0-rc.13` as a **local-only forward candidate**. It converges the live rc12 role-aware reader bridge with main's Morfeo MCP: it emits release-lock schema 5 with `hermes.extras` `mcp`, still reads schema 4, and serves the canonical Morfeo role through `aether mcp morfeo serve` on stdio or loopback Streamable HTTP. RC8 restores the new Morfeo SOUL and canonical contract skills following the RC7 compatibility bridge; rc11 and rc12 remain the local readers that can inspect this candidate. Its local annotated tag identity is `v1.0.0-rc.13`; neither this source nor a local tag proves what is installed or that agent behavior improved. Query `aether doctor` for the active version and require a reviewed commit, isolated qualification and an explicit managed cutover before claiming activation. `release_impact = minor`, `release_action = prepare`, `release_channel = prerelease`; no tag is pushed and no GitHub/package publication is authorized. RC7 and earlier local tags remain immutable; RC1 remains [published but rejected](https://github.com/DarkArty07/Aether-Agents/releases/tag/v1.0.0-rc.1) and must not be activated, and #261 remains open. This is **not** stable `1.0.0`, a PyPI release or WSL2 qualification.

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

The operational `start`, `stop`, `restart`, and `status` commands remain explicit unsupported placeholders, and `aether reconcile` supports only its bounded `--to active` form: it reconciles the projections of the already active, authenticated release and refuses every other mode. Public release publication, provider-backed live qualification, credentials, deployment, and activation of a managed service are outside this build's supported boundary. The Telegram Monitor (`aether monitor`, `docs/guides/telegram-monitor.md`) is implemented with deterministic packaging and an offline qualification lane; its real hourly model/Telegram qualification and installation-local activation remain pending terminal integration.

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
