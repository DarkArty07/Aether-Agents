# M1.1b Canonical Orca Candidate Qualification Acceptance

> **Status:** ACCEPTED
> **Accepted on:** 2026-08-08
> **Technical commit:** `eb7a23baaeb969ef388268786d187d6f4c8bef7d`
> **Authority:** Christopher's 2026-08-08 long-horizon authorization
> **Frozen behavioral contract:** `docs/external-agent/TASK-M1.1B.md`
> **Canonical manifest:** `ORCA_PROVIDER_MANIFEST.json`
> **Committed evidence:** `M1_ORCA_QUALIFICATION.json`

## Outcome

M1.1b now qualifies one exact Orca candidate and nothing broader:

- launcher: `/home/darkarty/.local/bin/orca`, 1,015 bytes,
  SHA-256 `89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208`;
- AppImage: `/home/darkarty/.local/opt/orca/orca-linux.AppImage`,
  203,385,690 bytes,
  SHA-256 `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`;
- product version: `1.4.167` from `orca-ide.desktop`;
- catalog: schema `1`, 220 commands, 153,496 exact bytes,
  SHA-256 `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`.

The qualifier authenticates the committed manifest before consuming any
manifest-controlled path, validates an exact schema recursively, streams both
candidate hashes before execution, runs only metadata extraction and two exact
`agent-context --json` calls, then re-hashes both files before PASS.

The production CLI exposes only `--isolated-root`. The former Bash-semantics
parser and all runtime identity overrides were removed.

## TDD evidence

RED was observed before implementation:

1. production CLI exposed launcher/artifact/hash/version/count/timeout overrides;
2. `parse_static_appimage_binding` remained present;
3. a readable `.mount_orca-*` directory was silently admitted;
4. the FIFO test skipped because its parent directory did not exist.

GREEN evidence at the accepted technical commit:

- focused qualification matrix: `29 passed`;
- full repository suite: `60 passed`, `0 skipped`;
- Ruff: PASS;
- compileall: PASS;
- `make mcp-smoke`: PASS;
- diff and narrow secret scans: PASS;
- temporary-root survivors: `0`;
- Orca process survivors: `0`.

The matrix contains 28 mandatory synthetic tests and one local exact-candidate
test. Only the exact-candidate test is conditionally skipped on hosts where those
pinned local bytes are absent; it executed locally and performed two fresh
qualifications. Unit coverage therefore remains active in clean CI instead of
skipping the entire module.

## Isolation and cleanup decision

Recursive inventory now requires exact equality with the manifest:

- exactly eight required directories;
- exactly `squashfs-root/orca-ide.desktop` as the only file;
- no symlinks, FIFO/socket/device entries, nested extras or broad prefix ignores.

A direct `tmp/.mount_orca-*` child is eligible for bounded waiting only when all
of these hold:

1. the name matches the frozen regex;
2. `lstat` proves a real directory and not a symlink;
3. immediate `scandir` fails with exactly `ENOTCONN`;
4. the entry disappears within 2,000 ms.

Readable directories, wrong errno, wrong type and timeout fail closed. A
short pre-boundary process-settle interval was required so the exact AppImage
could finish normal mount teardown; it does not admit or ignore any entry.

## Preserved boundaries

M1.1b did not:

- grant D1 provider-seam authority;
- implement an Orca adapter, Run, Task, Dispatch, worker or lifecycle operation;
- start the Orca IDE runtime;
- request model or network calls;
- access protected local state;
- register or activate Aether MCP;
- merge, tag, publish or release.

M1.1b is no longer a blocker. The next authorized, independent horizon is M2.2
canonical protocol and stable errors. M1.3 and all provider/lifecycle work remain
gated.
