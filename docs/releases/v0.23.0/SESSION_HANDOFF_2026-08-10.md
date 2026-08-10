# v0.23.0 session handoff — 2026-08-10

> **State:** M1.2 implementation paused; fail-closed before offline acceptance and activation.
> **Next owner:** Hermes, continuing the same authorized v0.23.0 cutover.
> **Canonical umbrella:** GitHub issue #167 and `docs/releases/v0.23.0/ROADMAP.md`.

## 1. Exact candidate identity

- Project root: `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover`
- Branch: `v0.23.0-orca-production-cutover`
- Current implementation HEAD before this handoff commit: `4659c1f6ea26f7b63c344655cb501391048a3e00`
- Current implementation tree before this handoff commit: `326784a089ac3a572853b22b4ae20f1cd5852db0`
- Baseline contract commit: `f333e7e`
- Main checkout remains on `docs/canonical-product-documentation`, deliberately dirty, and was not modified by this candidate.

Do not resume in the main checkout. Reconcile Git status in the candidate worktree before any write.

## 2. Active runtime remains unchanged

No production/active cutover occurred.

- `home/SOUL.md` remains active Hermes Prompt 2.0.0, SHA-256 `d981f4e805caa6dee222093cfcc0073aa8fbc6b2864c22335e104ec20e8be31a`.
- `mcp_servers.aether_mcp` is not registered in the active config.
- `olympus_v3`, Graphify, and Context7 remain registered and enabled.
- No gateway/TUI restart, deployment, merge, tag, Release, push, credential change, or spending occurred.
- The v0.23.0 candidate is local only.

## 3. Orca execution state

Qualified provider binding used during dogfood:

- Orca product: `1.4.167`
- AppImage SHA-256: `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`
- Stable profile root: `/home/darkarty/Desktop/agentes/orca/home`
- Actual stable XDG roots are below `profile_root/xdg/{config,cache,data,state}`.
- Actual stable Orca-side Hermes home is `profile_root/hermes-home`.
- Public CLI bootstrap was run from a prepared AppImage extraction through `AppRun` with `ELECTRON_RUN_AS_NODE=1`.

Run:

- Run ID: `run_6e48959461ec`
- Coordinator terminal: `term_e75d9296-30d1-4955-8d6b-40c1fed3e29b`
- Five Tasks are `completed` with result payloads:
  - `task_d2d8e32950df` — initial operational facade
  - `task_650a6b717494` — runtime acceptance corrections
  - `task_933d2f89f0dc` — trace effect classification
  - `task_b33fa9836c86` — local installer
  - `task_29239599ecec` — installer acceptance corrections
- All worker terminals were closed.
- Final inventory before handoff: zero active worktree agents, zero attempt-owned worker terminals, and zero Codex worker processes.
- The coordinator terminal remained present at handoff. Verify it before reuse; if missing/stale, create a replacement terminal and use the existing Run rather than creating an overlapping Run.

`/tmp/aether-orca-cli-root` is only an ephemeral prepared extraction pointer. Do not assume it survives a new session. If absent, recreate a private prepared extraction from the exact AppImage and bind the exact stable profile; do not return to concurrent `APPIMAGE_EXTRACT_AND_RUN` shim calls.

## 4. Commits produced after the frozen contract

1. `f46ef36` — expose operational Aether MCP facade
2. `6b9c71e` — harden operational Orca runtime boundaries
3. `e0c1c22` — classify trace queries as read-only
4. `4ce8d92` — add disabled operational installer
5. `4659c1f` — harden installer acceptance

Aggregate after `f333e7e`: 29 files, 1,399 additions, 66 deletions before this handoff documentation.

## 5. Accepted evidence

M1.1 was independently accepted at `e0c1c22`:

- focused effect regressions: 6 passed;
- Ruff: passed;
- complete `tests/aether_mcp`: 178 passed;
- clean Git tree;
- no worker survivors.

The first real isolated M1.2 reproducer against `4ce8d92` established:

- setup: passed;
- non-editable MCP stdio handshake: passed;
- 15-tool inventory: passed;
- doctor: failed;
- permission gate: failed;
- reported `orca_ready=true` was a false positive because the old doctor checked return code/output size rather than the Orca envelope;
- rollback restored the synthetic config.

`4659c1f` is a correction candidate only. It has not passed independent real-AppImage/profile acceptance and must not be activated.

## 6. Known gaps remaining in `4659c1f`

Inspect and correct these before rerunning M1.2:

1. **Direct wrapper profile binding is still absent.** The MCP launcher exports environment values, but `doctor()` invokes `installation.wrapper` directly. The wrapper itself currently exports only AppImage/Electron fields, so doctor can query the ambient/default Orca profile.
2. **Profile path semantics are wrong.** `setup()` derives XDG roots as `profile_root/{config,cache,data,state}`; the qualified profile uses `profile_root/xdg/{config,cache,data,state}` and `profile_root/hermes-home`.
3. **Aether profile ID is derived from `profile_root.name`.** For the real root this becomes `home`, which is not an approved Aether profile identity. Make profile ID an explicit validated input (normally `default`) rather than deriving it from a filesystem basename.
4. **Extraction does not yet sanitize inherited `APPIMAGE_EXTRACT_AND_RUN`.** The generated wrapper unsets it, but the initial `subprocess.run([AppImage, --appimage-extract])` still inherits the caller environment.
5. **Rollback process cleanup is not implemented.** It removes files/config but does not prove or terminate only attempt-owned installation processes.
6. **Resource inventory needs a real-profile check.** Ensure doctor does not flag its shell/parent as a survivor and does not miss children using the qualified profile.

Use TDD for each equivalence class. Do not weaken doctor or substitute a fake-only pass.

## 7. Exact next action

Resume M1.2 in the candidate worktree without activation:

1. Verify candidate Git status and the coordinator/Run inventory.
2. Create one Orca correction Task in `run_6e48959461ec` using the existing candidate worktree and coordinator (or a replacement coordinator rebound to the same Run).
3. Correct the six gaps above in the owning installation layer and tests.
4. Run focused operational-installation tests, Ruff, and the full affected Aether MCP suite.
5. Run the real isolated sequence in a temporary `HERMES_HOME` using the exact AppImage/profile:
   - setup disabled;
   - status;
   - doctor;
   - activate;
   - status enabled;
   - deactivate;
   - rollback;
   - second rollback idempotency;
   - exact config restoration;
   - preserved state/evidence;
   - zero owned survivors.
6. Accept M1.2 only if every result is truthful and green.

Only after M1.2 acceptance:

- register Aether MCP disabled in the active Aether home;
- run doctor;
- activate/reload;
- verify exactly 15 tools from a fresh Hermes process;
- execute one reversible real Task through Hermes → Aether MCP → Orca;
- close with zero survivors.

## 8. Prompt experiment state

The Hermes Prompt 3.0.0 candidate is preserved as `prompt/HERMES_CANDIDATE_3_0_0.md`; its disposition is preserved as `prompt/PROMPT_3_0_0_RESULT.md`.

- Candidate SHA-256: `54241ae89f986a644dd7f328b84e72fdb7f453f45532b00c5854d0a714fe7444`
- Active prompt remains 2.0.0.
- Three frozen experiments, 48 one-shot model calls, all rejected for promotion.
- Aggregate reported usage: 99,030 input tokens and 5,492 output tokens; monetary cost unavailable.
- Do not modify or promote the active prompt from this evidence. Redesign benchmark semantics prospectively before another attempt.

## 9. GitHub incident/issues index

Created from the first real Orca Run:

- #171 — AppImage/profile binding and extraction race
- #172 — Run/Task/Dispatch/worker projection reconciliation
- #173 — aggregate worker close and zero-survivor verification
- #174 — truthful profile-exact status/doctor/rollback
- #175 — machine-readable Orca CLI IDs/message-type contract
- #176 — proportional routing for trivial changes

Additional evidence was added to:

- #97 — worker can report success with inconsistent Git/evidence state
- #150 — related isolated Orca bootstrap failure
- #167 — v0.23.0 umbrella and linked issue index

## 10. Protected stop state

At handoff, the safe stop condition is satisfied:

- active runtime unchanged;
- candidate work is isolated;
- workers closed;
- coordinator preserved for resumption;
- known gaps and next reproducer documented;
- prompt not self-promoted;
- issues externalized;
- no publication or activation performed.
