# v0.23.0 M1.2 — Isolated installation acceptance

- Verdict: **PASS**
- Exact technical candidate: `0debf07db3601a14c88262d741727e5a527f3444`
- Orca: `1.4.167`
- AppImage SHA-256: `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`
- Qualified profile root: `/home/darkarty/Desktop/agentes/orca/home`
- Qualified profile id: `default`

## Orca worker-system trial

The implementation was intentionally routed through the existing Orca Run to
exercise the production worker path:

- Run: `run_6e48959461ec`;
- Task: `task_fbdcc474af28`;
- Dispatch: `ctx_87ebf09b2283`;
- worker: Codex with `gpt-5.6-terra`;
- worker commits: `a8c326c8bae9ae45be77048d6b5ec6a55cc5182c` and
  `4c21a73183e9042594516192e481f487ccf3760e`.

The worker reported `worker_done` with status `failed`, accurately classifying
its output as partial: the real isolated sequence had passed, but the required
equivalence-class tests and detached-tree verification were incomplete. Orca
closed the Dispatch and revoked its capability. Hermes then became the only
writer under the plan's explicit fallback, added the missing RED/GREEN coverage,
corrected unsafe process ownership and froze the exact technical candidate
above. No writers overlapped.

This is a positive mechanics result for Orca Task/Dispatch creation,
model-backed execution, structured completion and capability revocation. It is
not recorded as a worker semantic PASS.

## Six-gap closure

1. **Wrapper/profile binding:** the wrapper exports the qualified profile's
   `HOME`, Orca `HERMES_HOME` and four XDG homes directly. A poisoned ambient
   profile test verifies the child receives only those values. The MCP launcher
   retains the separate temporary Aether `HERMES_HOME`.
2. **XDG layout:** the accepted layout is
   `profile_root/xdg/{config,cache,data,state}` plus
   `profile_root/hermes-home`; setup rejects unqualified layouts before config
   mutation.
3. **Profile identity:** `--profile-id` is mandatory, validated and persisted;
   it is never derived from `profile_root.name`.
4. **AppImage extraction:** the extraction child removes inherited
   `APPIMAGE_EXTRACT_AND_RUN`. Installer children use new sessions, bounded
   output and group cleanup on timeout/failure; successful parents that leave
   descendants are rejected and cleaned.
5. **Rollback ownership:** inventory uses exact argv/executable paths,
   transitive PPID closure and `/proc` start-time identity. It excludes invoking
   ancestors and prefix lookalikes, revalidates identity before signals,
   preserves foreign processes and retains the manifest on incomplete cleanup.
6. **Doctor truthfulness:** inventory distinguishes installation-owned MCP
   processes from shared Orca-provider processes, validates the public
   `worktree ps --json` envelope, reports plausible opaque processes as
   `UNKNOWN`, and blocks `doctor.ok` on unknown or failed inventory.

## Deterministic gates

On the candidate worktree and again from detached candidate
`0debf07db3601a14c88262d741727e5a527f3444`:

- focused operational-installation matrix: `26 passed`;
- complete Aether MCP suite: `204 passed`;
- Ruff: PASS;
- compileall: PASS;
- whitespace check: PASS;
- non-editable wheel installation: PASS;
- import provenance: `site-packages`, not the source tree.

The suite emitted one existing Pydantic incomplete-forward-reference warning in
`test_operational_server.py`; no test failed and M1.2 does not change that model.

## Exact real isolated sequence

The detached committed scripts were executed against the exact Orca AppImage,
the qualified isolated profile and a fresh temporary Hermes home. The setup
parent inherited `APPIMAGE_EXTRACT_AND_RUN=1`; `doctor` inherited deliberately
false `HOME`, `HERMES_HOME` and XDG values.

Sequence:

1. setup with the registration disabled;
2. disabled status;
3. live MCP handshake and 15-tool enumeration;
4. doctor;
5. activate;
6. enabled status;
7. deactivate;
8. disabled status;
9. rollback;
10. second rollback.

Observed:

- setup and the live handshake each reported exactly 15 tools;
- doctor reported `ok=true`, `orca_ready=true`, valid state permissions, a
  validated worktree inventory, zero stale resources and zero unknown entries;
- activation and deactivation changed only the temporary registration flag;
- rollback restored the temporary config byte-for-byte;
- the second rollback reported `already_rolled_back=true`;
- the state root was preserved;
- wrapper, virtualenv, extraction directory, manifest and installation payload
  were absent after rollback;
- exact-path process inventory, excluding verifier ancestry, found zero
  survivors;
- Orca was `ready` before and after with version `1.4.167`;
- the active Aether config SHA-256 remained
  `6b27105d07ad97156e61c77ef2a6da970b06ec6c6c9946851020f87c68b89bd8`;
- the active parser reported `aether_mcp_present=false` and
  `aether_mcp_enabled=false`.

## Boundary

M1.2 accepts the exact source candidate's isolated operational installation and
rollback. Aether MCP remains absent from the active runtime configuration. No
active registration, runtime restart/reload, persistent activation, M1.3 task,
push, merge, tag or release was performed.

The next gate is a separate owner-authorized operation: register the accepted
Aether MCP entry in the active Hermes configuration with `enabled: false`.
Activation and the first real M1.3 Task remain later, separately authorized
gates.
