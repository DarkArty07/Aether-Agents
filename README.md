# Aether Agents

Aether Agents is a multi-agent software-engineering product and method. It adapts [Hermes Agent](https://hermes-agent.nousresearch.com/docs) as the runtime substrate and [GitHub Spec Kit](https://github.com/github/spec-kit) as the specification method, while defining Aether's role, handoff, policy, and qualification boundaries.

**Source versus release:** this revision is the local `1.0.0rc18` / `1.0.0-rc.18`
**adoption bridge** (local tag `v1.0.0-rc.18`), never merged into `main`. It carries
the RC19 source, manager and Hermes pin with the historical package shape that RC17's
frozen manager accepts: the single `aether` console script and an inert
`aether-telegram-monitor` entry that registers nothing. The #563 launcher is therefore
absent while the bridge is active. The update continues to `1.0.0rc19`; see the
[RC19 scope](specs/rc19-local-release/spec.md). Check the selected installation with
`aether doctor --json`; no tag is pushed and no GitHub/package publication is
authorized.

The historical [RC17 local candidate](specs/rc17-local-release/spec.md) binds reviewed
maintained-fork Hermes commit `007cfb77676b6b024d2c0986f4585e6cfdcf18d6`
(tree `b26638974fc134da866b821ab3c4b34ab430aeb3`), including
HLP-433/435/460/473/474/475, portable methodology, `/aether-plan`, schema 5 with
the `mcp` extra, and schema 4 readers. Its own conclusions were
`release_impact=major` for the incompatible command rename,
`release_action=prepare`, `release_channel=prerelease`. No tag was pushed or package
published. Earlier local tags remain immutable; RC1 remains
[published but rejected](https://github.com/DarkArty07/Aether-Agents/releases/tag/v1.0.0-rc.1),
and #261 remains open. Neither this source nor RC17 qualifies stable `1.0.0`, PyPI,
WSL2, or agent behavior.

Historical context: RC8 restores the new Morfeo SOUL and canonical contract skills
following the RC7 bridge; that historical statement is not RC17 qualification.

## Documentation

Start with the [documentation index](docs/index.md). The current documentation owns behavior available in this build; [`docs/capabilities.toml`](docs/capabilities.toml) is the sole current implementation-status and traceability registry. This README is a portal, not a second status table or design manual.

- [Getting started](docs/getting-started.md) and the [product boundary](docs/product-boundary.md)
- [Roles and authority](docs/roles-and-authority.md), [lifecycle](docs/guides/lifecycle.md), and [execution](docs/guides/execution.md)
- [Project initialization](docs/guides/project-initialization.md) and [Objective Contracts](docs/guides/objective-contracts.md)
- [Optional project knowledge and role work memory](docs/guides/project-knowledge.md)
- [Observation](docs/guides/observation.md) and [policy and recovery](docs/guides/policy-and-recovery.md)
- [CLI reference](docs/reference/cli.md), [plugins and tools](docs/reference/plugins-and-tools.md), [capabilities reference](docs/reference/capabilities.md), and [limitations and troubleshooting](docs/reference/limitations-and-troubleshooting.md)

## Current beta boundary

Aether uses Hermes-native Projects, boards, worktrees, review, lifecycle, profiles, and tools; it does not replace Hermes with another queue, scheduler, worker manager, or generic manual. A documented transitional downstream is no longer the runtime policy: under PD-49/61/64/65 the executable Hermes source is the maintained fork `DarkArty07/aether-hermes` branch `aether-main`, bound by the release lock's `maintained_fork` source mode — emitted as `schema_version` 5 with the closed `hermes.extras` allowlist, readable as schema 4 — through repository, exact commit, source-tree digest, artifact closure and provenance. The fixed public `v2026.8.18` tree remains the reference for upstream-compatible behavior and historical evidence, and `.patch` files stay audit/reconstruction evidence that is never replayed onto an active runtime.

Immutable release code and Graphify components live under the Aether XDG data root, while every mutable Hermes home, session, board, credential, memory, observation, knowledge artifact, and any retained historical Monitor data stays under the Aether XDG state root. `aether update` is the only supported promotion and activation boundary: its local-candidate route previews explicit clean Aether and fork commits without mutating anything, activation is explicit and may interrupt Aether-owned instances, a partial transition is recoverable, and rollback restores product code without rolling user state backward.

The `aether init` command initializes **an existing Git repository root only**. It writes the portable project marker and binds it to exactly one non-archived native Hermes Project whose primary path matches exactly; `--hermes-project ID` resolves an otherwise ambiguous exact-path match. It does not initialize Git or modify existing native Projects; when none matches, it creates and verifies one.

The operational `start`, `stop`, `restart`, and `status` commands remain explicit unsupported placeholders, and `aether reconcile` supports only its bounded `--to active` form: it reconciles the projections of the already active, authenticated release and refuses every other mode. Public release publication, provider-backed live qualification, credentials, deployment, and activation of a managed service are outside this build's supported boundary.

The owner retired Aether's formal Qualification Lab and Telegram Monitor, including periodic progress reports, on 2026-09-28 with no replacement. Hermes-native cron, ordinary Telegram interaction, and native task/final/input notifications remain unchanged. This source decision does not prove an installed runtime has changed; historical private state is preserved, and deleting qualification tooling is not a reliability PASS. See the [retirement decision](specs/lab-monitor-retirement/spec.md).

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
