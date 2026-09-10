# Observation

Aether Contract Observation is a bounded, metadata-oriented view of a contract flow. It is not a workflow controller, a raw log browser, or a provider call.

## Read one review brief

```bash
aether observe [REF] [--project PATH] [--since SUMMARY_ID] [--watch] [--json]
```

`REF` may identify a trace, contract, or bound task. Without it, the command selects one open trace only when unambiguous. It returns an explicit empty state when there is no open trace and an error when multiple candidates exist rather than guessing.

The normal output is one deterministic review brief. `--json` returns one stable JSON envelope whose `data.state` is either `summary` or `empty`. `--since` requests a deterministic comparison with a prior summary; incompatible schemas return an error instead of a manufactured diff. `--watch` refreshes selected summary facets and cannot be combined with `--json`.

The command is read-only with respect to the board, sessions and canonical artifacts, and it makes no network or model call. It may ingest events and update its own derived observation projection and retained summaries; it is not a zero-write filesystem probe. Partial, estimated, unavailable, and coverage-limited information must remain visibly labeled.

For routine contract-wide questions, Morfeo starts with the compact `aether_observe` tool: `status` normally, `changes` against a known successful summary, and `diagnose` for an actual anomaly. Verify the exact project/contract, freshness and coverage before reporting. Consult individual review handoffs, code or logs for specific details or when observation is unavailable; disclose a failed observation rather than silently substituting a full-history reconstruction. Final acceptance still requires the contract-result review and supporting evidence.

This project's complete procedure is the [Project Canonical Skill](../../.aether/skills/aether-observe/SKILL.md), discovered through root `AGENTS.md`. It is procedure, not authority or proof that a live observer deployment is healthy.

## Observer plugin and curated tool

The `aether-contract-observer` entry point is a passive observer: its callbacks do not direct native lifecycle actions or expose prompt, result, error, command, diff, or raw event content. In configured Morfeo resources it can register `aether_observe` in the `aether_observation` toolset. That tool has only `status`, `changes`, and `diagnose` actions and returns a bounded curated response.

The plugin entry point and provider-free read behavior are tested. Portable resource presence is not proof of installed profile activation or public lifecycle qualification; see [Plugins and tools](../reference/plugins-and-tools.md).

## Qualification laboratory

`aether_agents.lab` and the retained `scripts/e2e/` wrappers prepare disposable evidence roots. Deterministic preparation is useful evidence but is not a live provider-backed reliability run or release qualification. Live model execution requires its separately authorized gate, and the known persistent-session wake capability wall is documented in [limitations](../reference/limitations-and-troubleshooting.md).
