# Aether and Hermes product boundary

Aether is a product and method layered on [Hermes Agent](https://hermes-agent.nousresearch.com/docs/). It deliberately reuses Hermes mechanisms where they meet the requirement and does not turn framework availability into Aether authority.

If you are learning the system for the first time, read [Start here](start-here.md) before this boundary reference.

| Hermes provides | Aether adds or constrains |
| --- | --- |
| Agent conversation loop, profiles, tools, and hooks | A three-role responsibility model, Objective Contracts, portable role resources, and a small edge-effect policy |
| Durable boards, dispatcher, cards, retries, reclaim, worktrees, review, and session support | Which role uses those primitives, how a finalized contract enters a project/version-specific board, and what evidence must accompany completion |
| Plugin discovery and tool registration | The `aether-contract-observer`, `aether-objective-contracts` and optional `aether-project-knowledge` entry points and their bounded Aether tools |
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

## Optional Graphify component

[Project knowledge](guides/project-knowledge.md) uses an isolated original Graphify distribution for structural extraction and graph navigation. Aether owns project/revision selection, coordinated publication, bounded tool responses and separate role/project experience records. All three roles have the same tools and can maintain the graph. Native reflection is a private signal report; original notes stay retrievable, and neither graph nor notes become project authority.

The two package-owned canonical skills teach use of `project_knowledge` and `work_memory`; they do not add roles, gates or a second skills loader. This component does not change Hermes core, replace its memory providers or require its MCP transport. Live-profile activation and semantic extraction remain separate from the local component implementation.

## Deliberate non-ownership

Aether does not implement its own queue, retry engine, board store, worktree manager, generic plugin system, generic provider manager, or generic Hermes manual. A role having local tool capability does not grant authority to change product intent, acquire credentials, activate services, deploy, publish, or make a protected external effect.

Aether's current source also is not evidence of a stable release, public installation, active service, live profile, configured provider, or qualified model-backed execution. Those distinctions are intentional and visible in [limitations and troubleshooting](reference/limitations-and-troubleshooting.md).

## Next step

Read [Roles and authority](roles-and-authority.md) to see who owns each decision, then [Start here](start-here.md) if you have not yet followed the beginner path.
