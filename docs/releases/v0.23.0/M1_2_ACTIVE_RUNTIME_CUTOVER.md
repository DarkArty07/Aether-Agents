# v0.23.0 M1.2 — Active runtime cutover

- Verdict: **PASS**
- Cutover date: `2026-08-10`
- Runtime activation authorization: explicit product-owner instruction in the active Hermes session
- Installed product version: `0.23.0.dev0`
- Installation source tree at setup: `4d85a7a`
- Post-cutover backup-permission correction: `b6b230cfdef4633d4b983bc9eff596d0c23365a5`
- Orca: `1.4.167`
- AppImage SHA-256: `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`
- Active Hermes home: `/home/darkarty/Desktop/agentes/aether/home`
- Qualified Orca profile root: `/home/darkarty/Desktop/agentes/orca/home`
- Qualified profile id: `default`

## Scope

This operation crossed the separately authorized local-runtime boundary after the
isolated M1.2 acceptance. It:

1. inventoried the active Hermes gateway, Orca profile and MCP registrations;
2. preserved an exact configuration and systemd-unit rollback copy;
3. registered the accepted Aether MCP candidate initially with `enabled: false`;
4. verified status and doctor before activation;
5. removed the `olympus_v3` MCP registration from the active Hermes config;
6. activated `aether_mcp`;
7. refreshed and restarted the exact user gateway service;
8. verified the fresh Hermes gateway and both active Hermes TUI processes;
9. preserved historical Olympus databases, logs and source evidence.

Removing Olympus means it is no longer registered, loaded or running in the
named local runtime. This operation intentionally did not delete preserved
`.olympus` databases, historical logs, profile documents or repository history.

No M1.3 Task, Dispatch, worker, model request, artifact mutation, push, merge,
tag, Release or deployment was performed.

## Exact configuration transition

The original active config SHA-256 was:

```text
6b27105d07ad97156e61c77ef2a6da970b06ec6c6c9946851020f87c68b89bd8
```

The accepted active config SHA-256 is:

```text
aaf726e0f6fd33d030ad0b962aad0c840f905e021ea372f0ebe8a9112e852a6f
```

A secret-safe structural comparison established:

- added MCP server: `aether_mcp`;
- removed MCP server: `olympus_v3`;
- `aether_mcp.enabled=true`;
- no changed common MCP server;
- no unrelated configuration difference;
- no active config token for `olympus_v3`, `olympus_v3.server`,
  `OLYMPUS_DB_PATH` or `talk_to`.

The retained MCP registrations are `context7`, `graphify` and `aether_mcp`.

## Failure, rollback and same-path recovery

The first disabled installation completed, but its initial doctor attempt
reported `MCP_HANDSHAKE_FAILED`. A direct diagnostic handshake then enumerated
all 15 tools; the remaining doctor gate showed the real blocker: Orca was
reachable but its graph remained in `reloading` and did not recover within the
bounded readiness poll.

The operation stopped before Olympus removal or Aether activation. It then:

1. executed the supported Aether MCP rollback;
2. restored the active config byte-for-byte to
   `6b27105d07ad97156e61c77ef2a6da970b06ec6c6c9946851020f87c68b89bd8`;
3. confirmed there were no model workers or live Dispatches;
4. stopped Orca through the official `orca-app stop` wrapper;
5. waited for full process exit;
6. relaunched Orca through `orca-app open`;
7. observed `runtime.state=ready`, `reachable=true` and `graph.state=ready`;
8. rebound setup to the new live coordinator terminal;
9. retried the same disabled setup and doctor path.

The retry passed with `doctor.ok=true`, `orca_ready=true`, 15 tools, valid state
permissions, zero stale resources and zero unknown resources. Only then did the
operation remove Olympus and activate Aether MCP.

This is a real rollback-and-same-path-retry result rather than a bypass.

## Active runtime evidence

After the exact gateway restart:

- the previous gateway PID `895` exited through the graceful restart path;
- the refreshed gateway started as PID `63593`;
- systemd reported `ActiveState=active` and `SubState=running`;
- the gateway cgroup contained an Aether MCP watchdog and its installed
  `site-packages` server child;
- both already-running Hermes TUI processes independently reloaded the same
  Aether MCP registration;
- exact `/proc` inventory found no process whose argv contained `olympus_v3`;
- Orca remained version `1.4.167`, reachable and graph-ready;
- the MCP log recorded new `starting MCP server 'aether_mcp'` events for both
  TUI processes and the gateway, with no later Olympus start event;
- `hermes mcp list` and `hermes tools list --platform cli` reported
  `aether_mcp` enabled and no Olympus registration.

A live MCP initialize/list-tools handshake returned exactly:

```text
orca_call
orca_describe
orca_search
project_admit
project_inspect
swarm_cancel
swarm_close
swarm_dispatch
swarm_message
swarm_reconcile
swarm_retry
swarm_start
swarm_status
swarm_trace
swarm_validate
```

There were no extra Aether MCP tools.

## Rollback assets

The pre-cutover rollback bundle is:

```text
/home/darkarty/Desktop/agentes/aether/home/backups/runtime-cutover-20260810T224623Z/
```

It contains:

- `config.yaml.before`, mode `0600`, SHA-256
  `6b27105d07ad97156e61c77ef2a6da970b06ec6c6c9946851020f87c68b89bd8`;
- `hermes-gateway.service.before`, mode `0600`, SHA-256
  `c6b0b98efa4f3b56c3a246dafb7fab963c4a5d497c431fed56cdb1a12a9e2883`.

The active installation also retains its manifest-bound
`config.yaml.pre-aether-mcp` and `config.yaml.pre-activation` backups. The
external directory is mode `0700`; all secret-bearing backup files are mode
`0600`.

The refreshed active systemd unit SHA-256 is:

```text
84e72a3fdda49a3e1b84881864cecccd44b7eb8b489476454dcd40836e5d1798
```

The rollback executable remains:

```text
.venv/bin/python scripts/aether_mcp/rollback.py \
  --hermes-home /home/darkarty/Desktop/agentes/aether/home
```

A full pre-cutover restore additionally uses the preserved config and systemd
unit above, followed by systemd reload and the same gateway health checks.

## Security correction discovered during cutover

The live inventory found that setup inherited the source config mode for
`config.yaml.pre-aether-mcp`. Because the source config was mode `0644`, the
backup was also mode `0644`, although its parent directory was mode `0700`.

The active file was immediately hardened to `0600`. Strict RED/GREEN tests then
proved and corrected the root cause for both setup and activation backups:
backup files are now always written mode `0600`, while active config writes
continue preserving the config's own mode. The correction is commit
`b6b230cfdef4633d4b983bc9eff596d0c23365a5`.

Post-correction gates:

- focused RED tests failed on observed mode `0644` before the fix;
- focused GREEN tests: `2 passed`;
- complete Aether MCP suite: `205 passed`;
- Ruff: PASS;
- compileall: PASS;
- `git diff --check`: PASS.

The suite retained one known Pydantic incomplete-forward-reference warning in
`test_operational_server.py`; no test failed.

## Boundary and next gate

M1.2 is now accepted in the named active local runtime: Aether MCP is installed,
registered, enabled and loaded; Olympus is retired from that runtime; rollback
is preserved and one real rollback/retry was exercised.

M1 is not yet complete. The next and only next gate is M1.3: one separately
contracted, low-risk, reversible real repository Task through
Hermes -> Aether MCP -> Orca. Production-entry policy does not become fully
active until M1.3 evidence is accepted and M1.4 records the product-owner
entry decision.
