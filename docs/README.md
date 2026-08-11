# Aether documentation

Last audited: 2026-08-11. These documents describe the current `0.23.0.dev0` source and named local runtime.

## Current facts

- one persistent repository checkout on local `main`;
- Hermes prompt `3.0.0-hot.3`;
- installed and registered Aether MCP with 15 tools;
- three allowed profiles: Hefesto, Daedalus and Ictinus;
- no supported Olympus, ACPManager, Harmonia, `talk_to` or Honcho path;
- model-backed multi-agent production entry is not yet accepted.

## Reading map

| Need | Canonical document |
|---|---|
| Product purpose and boundaries | [Product](product/README.md) |
| Current runtime components | [Architecture](architecture/README.md) |
| Installation and first checks | [Quickstart](guides/QUICKSTART.md) |
| Machine-local configuration | [Configuration](guides/CONFIGURATION.md) |
| Status, doctor, rollback and incidents | [Operations](operations/README.md) |
| Tools, effects and schemas | [Reference](reference/README.md) |
| Authority boundaries | [Authority](knowledge/AUTHORITY.md) |
| Durable user memory and skills | [Hermes learning model](knowledge/HERMES_LEARNING_MODEL.md) |
| Durable decisions | [Decision index](decisions/README.md) |
| Current release state | [v0.23 status](releases/v0.23.0/STATUS.yaml) |
| Contributor workflow | [CONTRIBUTING.md](../CONTRIBUTING.md) |

## Truth hierarchy

Observed runtime status and executable source/tests outrank narrative documents. Current canonical docs outrank release evidence. Decision records preserve why a boundary exists, but a superseded or historical record does not reactivate removed behavior.

Only two v0.22 JSON files remain because provider qualification code/tests consume them. They are fixtures, not current operating instructions.
