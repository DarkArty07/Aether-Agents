# M1.2 isolated installation acceptance

**Verdict:** PASS on the committed candidate `a8c326c` (before this evidence
commit), 2026-08-10.

The qualified AppImage
`/home/darkarty/.local/opt/orca/orca-linux.AppImage` had SHA-256
`813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`.
The stable provider profile was
`/home/darkarty/Desktop/agentes/orca/home`, with explicit Aether profile ID
`default`; the installer used a disposable `/tmp/aether-m1-2-credvl` Hermes
home and never used the active Aether home.

The real sequence passed: disabled setup, status, exact 15-tool stdio doctor
handshake, enabled toggle, disabled toggle, rollback, and a second idempotent
rollback. Doctor returned `ok: true`, `orca_ready: true`, a performed process
inventory with zero owned processes, and nine shared Orca provider processes
classified as provider state rather than stale installation resources.

The temporary configuration restored byte-for-byte, the `.aether-mcp` payload
was absent after rollback, and `.aether-mcp-state` remained present. The active
Aether configuration SHA-256 was unchanged before and after:
`6b27105d07ad97156e61c77ef2a6da970b06ec6c6c9946851020f87c68b89bd8`.

No installation-owned survivor was observed; shared Orca remained alive. No
UNKNOWN result was returned by the real inventory, and no active configuration,
registration, reload, worker, credential, or spend effect was performed.
