# Aether and Hermes product boundary

Aether is a product and method layered on [Hermes Agent](https://hermes-agent.nousresearch.com/docs/). It deliberately reuses Hermes mechanisms where they meet the requirement and does not turn framework availability into Aether authority.

| Hermes provides | Aether adds or constrains |
| --- | --- |
| Agent conversation loop, profiles, tools, and hooks | A three-role responsibility model, Objective Contracts, portable role resources, and a small edge-effect policy |
| Durable boards, dispatcher, cards, retries, reclaim, worktrees, review, and session support | Which role uses those primitives, how a finalized contract enters a project/version-specific board, and what evidence must accompany completion |
| Plugin discovery and tool registration | The `aether-contract-observer` and `aether-objective-contracts` entry points and their bounded Aether tools |
| Generic configuration, provider, credential, and service behavior | Product-specific release/project/observation candidates and explicit limits; no duplicated generic manual |

## Aether-owned behavior

The current source contains:

- a parser-backed `aether` CLI, including implemented project initialization and observation reading;
- a validated portable project marker and local project registry binding;
- Morfeo-only Objective Contract authoring and deterministic per-contract-version execution-board handoff;
- bounded Contract Observation capture/read interfaces;
- portable Morfeo, Supervisor, and Implementer resource bundles;
- a policy hook that protects narrow credential, protected external, and destructive edges; and
- a disposable qualification laboratory plus compatibility wrappers.

The status of each surface is not implied by this inventory. Consult [Capability coverage](reference/capabilities.md) for implemented, partial, transitional, and unsupported status.

## Deliberate non-ownership

Aether does not implement its own queue, retry engine, board store, worktree manager, generic plugin system, generic provider manager, or generic Hermes manual. A role having local tool capability does not grant authority to change product intent, acquire credentials, activate services, deploy, publish, or make a protected external effect.

Aether's current source also is not evidence of a stable release, public installation, active service, live profile, configured provider, or qualified model-backed execution. Those distinctions are intentional and visible in [limitations and troubleshooting](reference/limitations-and-troubleshooting.md).
