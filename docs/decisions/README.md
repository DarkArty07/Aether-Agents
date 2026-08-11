# Decision records

Decision records explain durable product and architecture choices. They do not override current executable runtime truth or the user's current instruction.

## Current governing set

| Record | Current role |
|---|---|
| [PDR-0014](PDR-0014-versioned-orca-production-adoption.md) | separates released foundation, current 0.23 work and future gated adoption |
| [PDR-0013](PDR-0013-swarm-roster-and-personality-model.md) | stable roster policy; current physical roster is Hefesto, Daedalus and Ictinus |
| [PDR-0012](PDR-0012-hermes-orca-swarm-boundary.md) | Hermes product authority and provider execution boundary |
| [ADR-0001](ADR-0001-aether-mcp-control-and-trace-plane.md) | typed Aether MCP control/trace plane |
| [PDR-0008](PDR-0008-canonical-definition-and-project-completion.md) | product completion contract |
| [PDR-0006](PDR-0006-hermes-native-user-memory-without-honcho.md) | Hermes-native memory, no Honcho dependency |
| [ODR-0001](ODR-0001-main-integration-and-release-automation.md) | integration/release distinction; current user instructions still take precedence |

PDR-0001 through PDR-0007, PDR-0009 and PDR-0011 remain decision history. Superseded implementation details, removed filenames and old release paths inside those records are not supported runtime instructions.

New records must state owner, status, context, decision, alternatives, consequences, validation and implementation authority. Approval of a design never implies activation, spending, publication or deployment.
