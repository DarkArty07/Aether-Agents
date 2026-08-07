# M1.2 Independent Acceptance Review

> **Decision:** ACCEPTED — PROVIDER SEAM INSUFFICIENT
> **Review date:** 2026-08-07
> **Implementation candidate:** `f9c3460a25cf5b9b97c329fab47817d678652f54`
> **Acceptance owner:** Hermes
> **Next horizon:** M0 design reconciliation only

## 1. Scope and authority

M1.2 was authorized only to collect two isolated `orca agent-context --json`
results and map the frozen Aether MCP contract to Orca's public structured
catalog. No mapped operation, Run, Task, Dispatch, worker, message, terminal,
worktree, coordinator, model or persistent runtime was authorized.

M1.1a remains the accepted identity/catalog basis. M1.1b remains accepted debt
and blocks every M1.3 operation.

## 2. Candidate scope

The implementation candidate has the exact parent
`5eb197889053938e191714be4b7c48646e5f9674`, subject
`docs: map Orca structured provider seams`, and adds only:

- `docs/external-agent/REPORT-M1.2.md`;
- `docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.json`;
- `docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.md`.

No source, test, configuration, dependency, profile, runtime or protected local
state is part of that commit.

## 3. Independent catalog reproduction

Hermes independently executed exactly two isolated read-only probes of:

```text
/home/darkarty/.local/bin/orca agent-context --json
```

Observed identity and catalog facts:

- launcher: 1,015 bytes,
  `89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208`;
- AppImage: 203,385,690 bytes,
  `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`;
- catalog schema: `1`;
- declared and actual commands: `220`;
- catalog bytes: `153496`;
- catalog SHA-256:
  `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`;
- the two raw results were byte-identical;
- stderr was empty in both probes;
- both AppImage mountpoints disappeared after an observed bounded cleanup wait of
  approximately 100 ms;
- both isolated roots were then empty except for their required directories and
  were removed;
- zero Orca-labelled processes and zero review temporaries survived.

The transient `.mount_orca-*` entry is an observed AppImage cleanup phase, not an
authorized inventory exception. A future M1.1b verifier must wait for bounded
cleanup and then require exact emptiness; it must not ignore arbitrary content by
prefix.

## 4. Independent matrix checks

The corrected matrix contains:

- 24 unique Aether MCP tools;
- 55 required M2–M5 capabilities across 12 domains;
- 49 `PARTIAL` capabilities;
- 6 `MISSING` capabilities;
- 0 `SUPPORTED` capabilities under the frozen strict standard;
- 0 `UNKNOWN` capabilities.

For the 49 `PARTIAL` rows:

- every referenced command path exists in the 220-command catalog;
- the rows reference 45 unique public command paths;
- every claimed flag list is byte-for-byte equivalent to catalog metadata;
- the catalog command objects expose only `aliases`, `argumentMode`, `command`,
  `examples`, `flags`, `notes`, `path`, `positionalArgs`, `summary`, and `usage`;
- no command object declares a machine-readable result/output schema, effect,
  timeout contract or recovery contract.

The six `MISSING` capabilities are:

1. `events_read`;
2. `resource_cleanup`;
3. `resource_inventory`;
4. `run_cancel`;
5. `run_close`;
6. `task_cancel`.

A catalog-wide name scan found related stop/reset/close commands, but no public
command whose declared seam satisfies those six aggregate semantics. No private
storage, GUI automation, shell fallback or undocumented command was admitted.

## 5. Candidate defects corrected during acceptance

The implementer result incorrectly reported 54 total capabilities and 5 missing
capabilities. The committed JSON actually contained 55 and 6, while the Markdown
contained both pairs. Independent acceptance corrected the Markdown to 55/6.

The following deterministic defects were also corrected:

- `swarm_reconcile` now reciprocally references the already-declared
  `worker_abandon` capability;
- `orca_batch` is identified as an Aether-owned admitted batch envelope with no
  distinct provider batch command, while each item retains its mapped provider
  capability;
- `blocking_missing_or_unknown_ids` contains only the six matching rows, while a
  separate `blocking_non_supported_ids` preserves all 55 blockers under the
  strict qualification standard;
- trailing whitespace that caused `git diff --check` to fail was removed;
- the implementer report now distinguishes task completion from an insufficient
  provider gate.

These corrections do not improve the provider result or reinterpret missing
catalog evidence as support.

## 6. Acceptance decision

M1.2 is accepted as a complete and reproducible answer to its question:

> Does every required M2–M5 operation have a public Orca seam whose catalog
> declares structured arguments, result, effect, timeout and recovery semantics?

**No.** The accepted gate is `INSUFFICIENT`.

This is a successful discovery milestone, not authorization to implement the
adapter or operate Orca. M1.3, M2 source implementation and all later runtime
horizons remain blocked.

## 7. Required product decision

The next action is one bounded M0 design reconciliation. The viable choices are:

1. require Orca itself to publish the missing operations and machine-readable
   contracts before Aether continues; or
2. permit a version-pinned Aether adapter to own validated output schemas learned
   through separately authorized isolated fixtures and to compose only public
   Orca commands for aggregate event/cancel/close/inventory/cleanup semantics.

Choice 2 is the recommended fast path, but it changes the frozen provider-seam
acceptance model and requires product-owner approval before any implementation or
M1.3 execution.

A private database, UI automation, free-form shell, hidden compatibility shim or
restored Olympus/Aether runtime is not an acceptable third option.
