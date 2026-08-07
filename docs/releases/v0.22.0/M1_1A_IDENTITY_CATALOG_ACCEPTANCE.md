# M1.1a Orca Identity and Catalog Fast-Track Acceptance

> **Status:** ACCEPTED — BOUNDED READ-ONLY BASIS FOR M1.2
> **Accepted on:** 2026-08-07
> **Product owner:** Christopher (DarkArty07)
> **Acceptance owner:** Hermes
> **Accepted candidate HEAD:** `539c09b79edff460ce152f9134c14866390bf542`
> **Fast-track authorization:** user requested the M1.2 prompt and prioritized faster advancement after the M1.1a/M1.1b split was presented

## 1. Decision

M1.1 is split for fast, honest progress:

- **M1.1a — exact identity and catalog:** accepted as the sufficient read-only
  prerequisite for M1.2.
- **M1.1b — reusable adversarial isolation qualifier:** deferred as accepted debt
  that must close before any M1.3 lifecycle operation.

This does not relabel the full M1.1 qualifier PASS. It narrows the claim to the
installed Orca candidate and permits only read-only structured-seam analysis.

## 2. Accepted identity and catalog facts

Independently reproduced evidence fixes:

```text
launcher path: /home/darkarty/.local/bin/orca
launcher size: 1015 bytes
launcher SHA-256: 89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208
AppImage path: /home/darkarty/.local/opt/orca/orca-linux.AppImage
AppImage size: 203385690 bytes
AppImage SHA-256: 813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33
product version: 1.4.167
catalog schema: 1
declared commands: 220
actual commands: 220
catalog bytes: 153496
catalog SHA-256: 068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b
qualification evidence SHA-256: 94d3b6ba88490d3b8621783f1ae39cb9f09b6a723130830d5c1e991543487908
```

Hermes independently reproduced two byte-identical real catalog probes, exact
versioned JSON equality, exact real-root final inventories, empty stderr, zero
Orca-labelled survivors and complete test-owned temporary cleanup.

These facts are accepted only while all pinned path, size and digest values remain
unchanged. Drift blocks M1.2 rather than silently recalifying another candidate.

## 3. Deferred M1.1b debt

`M1_1_CORRECTION_2_REVIEW.md` remains authoritative for unresolved reusable
qualifier claims:

1. a `tmp/.mount_orca-*` prefix can hide unexpected nested state;
2. the generic Bash mutation blacklist can be bypassed by constructs such as
   `printf -v APPIMAGE`;
3. the mandatory FIFO regression was skipped by a bad fixture while reported as
   PASS.

Disposition:

- no Correction 3 against the blacklist design;
- replace the generic parser with candidate-specific canonical manifest/digest
  verification;
- remove every inventory prefix exception;
- make the FIFO regression execute without skip;
- independently accept the replacement before M1.3.

**Expiry gate:** M1.3 may not start, even in isolation, while any M1.1b item is
open. M1.4, adapter implementation and all runtime activation also remain blocked
by their existing gates.

## 4. Why M1.2 may proceed

M1.2 is read-only catalog analysis. It may:

- recheck pinned launcher/AppImage identity without opening protected state;
- invoke only `orca agent-context --json` under fresh isolated HOME/XDG/TMP roots;
- compare two raw catalog outputs byte-for-byte;
- map public command metadata to required Aether provider capabilities;
- classify seams `SUPPORTED`, `PARTIAL`, `MISSING` or `UNKNOWN`.

It may not invoke any mapped operation, start an Orca runtime, create Run/Task/
Dispatch/worker/terminal/worktree/message state, read private Orca storage, use GUI
or shell fallbacks, call a model/provider/network API, install dependencies or
begin M1.3.

The known qualifier gaps do not alter the accepted real catalog bytes. They remain
runtime/isolation blockers rather than blockers to read-only catalog
classification.

## 5. M1.2 acceptance boundary

M1.2 must produce a versioned structured matrix covering all 24 Aether MCP tools
and every M2–M5 provider capability. Every positive mapping requires an exact
public Orca command and catalog evidence. Missing result schema, effect, timeout or
recovery semantics must remain `PARTIAL` or `UNKNOWN`; prose cannot be promoted to
control input.

A required capability available only through private storage, GUI automation,
free-form shell or unstable prose is `MISSING` and blocks the later provider
decision. The implementer cannot accept its own matrix. Hermes will inspect and
reproduce the exact catalog mapping before authorizing any next step.
