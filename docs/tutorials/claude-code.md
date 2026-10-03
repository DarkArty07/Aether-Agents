# Tutorial: use Aether with Claude Code

Aether integrates with [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)
in two independent ways:

- **Part A — Morfeo inside Claude Code.** Claude Code's model acts as Morfeo through MCP.
  Aether supplies Morfeo's profile, project binding, memory, board and tools.
- **Part B — Claude Code as the Implementer.** For a contract where you ask for it, the
  Implementer units run on Claude Code instead of Hermes, with an automatic fallback to
  Hermes.

Both require an installed Aether release and an initialized project
([Getting started](../getting-started.md)).

## Part A: Morfeo inside Claude Code

### 1. Register the MCP server

From the project root, register Morfeo for this project only:

```bash
claude mcp add morfeo -- aether mcp morfeo serve --mode harness --project "$PWD"
claude mcp get morfeo
```

Use an absolute project path. The default scope is local: private to you and to this
project directory.

### 2. Raise Claude Code's MCP output limit

`morfeo_bootstrap` returns Morfeo's complete role context in one result, about 70,000
characters. Claude Code's default MCP output limit is smaller, so it spills the result to
a file ([#558](https://github.com/DarkArty07/Aether-Agents/issues/558)). Raise the limit
when you start Claude Code:

```bash
MAX_MCP_OUTPUT_TOKENS=60000 claude
```

You can also set `MAX_MCP_OUTPUT_TOKENS` in the `env` block of your Claude Code settings.

### 3. Bootstrap Morfeo

Start a session in the project and ask:

> Call `morfeo_bootstrap`, then act as Morfeo for this project.

`morfeo_bootstrap` must be the first tool call on each connection; a second call returns
the same context revision. From then on, work exactly as in
[your first objective](first-objective.md): ask for objectives, use `/aether-plan`, approve
contracts and ask for progress.

### What harness mode changes

- Claude Code keeps its own model and its own file and terminal tools. Harness mode
  therefore does not publish Hermes' `terminal`, `process`, `read_file`, `write_file`,
  `patch`, `search_files` or `execute_code`.
- Morfeo's Aether and Hermes tools come from the MCP server: Objective Contracts, the
  board, observation, memory and, when enabled, project knowledge.
- Native `delegate_task` children use Morfeo's configured Hermes model, not Claude.
- Supervisor and Implementer still run on the Hermes board. MCP is not a transport between
  roles.

### Chatbot mode over HTTP

For a client without its own file and terminal tools, serve chatbot mode over Streamable
HTTP on the loopback interface:

```bash
aether mcp morfeo serve --mode chatbot --transport streamable-http \
  --project /path/to/project --port 8765
```

The server binds only `127.0.0.1`. It opens no tunnel and accepts no provider credentials.
See [Morfeo MCP](../guides/morfeo-mcp.md).

## Part B: Claude Code as the Implementer

### Requirements

- Claude Code is installed, on the `PATH` of the gateway service, and logged in by you.
  Aether never reads, manages or stores Claude credentials.
- Claude Code can work unattended. Adjust any hook, plugin or setting of yours that
  waits for human input. If `disableBypassPermissionsMode` is set, attempts fall back to
  Hermes.
- Each attempt consumes your own Claude plan. Parallel units run parallel attempts.

### 1. Ask for it explicitly

The opt-in is per contract and only on your explicit request. When Morfeo prepares the
contract, say so:

> Use Claude Code as the Implementer harness for this contract.

Without that request, every role runs on Hermes, and Morfeo neither proposes nor asks
about another harness. The finalized contract records `implementer_harness: "claude-code"`:

```bash
grep -r "implementer_harness" .aether/objective-contracts/
```

### 2. What happens during execution

- Each Implementer attempt is one Claude Code turn. Aether supplies the unit's context,
  the canonical skills, a worker MCP server for board operations and its pre-tool policy
  hook for the run. It does not curate the rest of your Claude configuration.
- A missing binary, disabled bypass mode, authentication failure, exhausted quota, error
  result or unready hook or MCP server makes that attempt fall back to Hermes within the
  same claim.
- Morfeo, the Supervisor, goal-mode cards and **all** reviews stay on Hermes, so review
  stays independent of the harness that wrote the code.

Observe the contract as usual with `aether observe`. See
[Execution](../guides/execution.md#opt-in-implementer-harness-claude-code).

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| Claude Code saves the bootstrap result to a file | Raise `MAX_MCP_OUTPUT_TOKENS` (step A2). |
| `claude mcp get morfeo` shows a failed connection | Check `aether doctor` and that the `--project` path is an initialized project root. |
| Implementer attempts always run on Hermes | Confirm the contract records `implementer_harness`, that `claude` is on the service's `PATH` and logged in, and that bypass mode is not disabled. |
