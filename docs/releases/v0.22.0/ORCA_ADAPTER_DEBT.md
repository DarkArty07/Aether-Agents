# Orca Adapter Technical-Debt Ledger

> **Status:** ACCEPTED FOR QUALIFICATION; NOT ACCEPTED FOR ACTIVATION
> **Date:** 2026-08-08
> **Affected provider:** Orca `1.4.167`
> **Owner:** Christopher (DarkArty07)
> **Canonical decision:** `M1_4_R1_ADAPTER_DECISION.md`

This ledger records guarantees intentionally weaker than an ideal native provider
contract. A debt entry permits qualification work only. It does not prove the
mitigation, grant D1, or authorize activation.

## TD-ORCA-001 — Polling instead of provider events

- **Capability:** `events_read`
- **Severity:** Medium
- **Consequence:** state changes may be observed late; no provider-global ordering,
  completeness, or push delivery can be claimed.
- **Mitigation:** bounded status/inbox/list polling, Aether request/receipt journal,
  monotonic Aether event sequence, source/freshness labels, and explicit gaps.
- **Current acceptance:** allowed only as `AETHER_OWNED/DEGRADED/UNQUALIFIED` during
  qualification; correctness must not depend on spontaneous events.
- **Removal condition:** Orca exposes a versioned cursor/event stream with ordering,
  retention, gap, timeout, and restart semantics that passes compatibility tests.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## TD-ORCA-002 — Correlation-bounded resource inventory

- **Capability:** `resource_inventory`
- **Severity:** High
- **Consequence:** resources created outside Aether or changed after correlation may
  be missing or ambiguous; similarly named foreign resources cannot be attributed.
- **Mitigation:** durable creation/admission receipts plus public Run/Task/worker/
  terminal/worktree list/show/status reads; exact IDs only; external drift becomes
  `UNKNOWN`.
- **Current acceptance:** no close/cancel success may rely on inventory until fault,
  restart, foreign-resource, and drift fixtures pass.
- **Removal condition:** Orca exposes complete Run-scoped inventory with stable
  resource identities, ownership provenance, pagination, freshness, and survivors.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## TD-ORCA-003 — Non-atomic compensating cleanup

- **Capability:** `resource_cleanup`
- **Severity:** Critical
- **Consequence:** cleanup can partially succeed, timeout, or leave survivors; there
  is no atomic aggregate rollback.
- **Mitigation:** fence dispatch, enumerate correlated resources, stop/close/remove
  in dependency order, record one receipt per step, re-observe, repeat idempotently,
  and return `CLEANUP_FAILED` or `UNKNOWN` when disposition is not proved.
- **Current acceptance:** qualification only; `CLOSED` is forbidden with any unknown
  or unauthorized survivor.
- **Removal condition:** Orca exposes idempotent Run-scoped cleanup with complete
  result receipts and survivor inventory, or the composition proves equivalent
  guarantees under every accepted fault case.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## TD-ORCA-004 — Non-atomic aggregate cancellation

- **Capabilities:** `run_cancel`, `task_cancel`
- **Severity:** High
- **Consequence:** some workers/terminals may stop while others remain active; a
  timeout can leave the effect ambiguous.
- **Mitigation:** append `CANCEL_REQUESTED`, block new dispatches, stop/fence exact
  correlated resources, observe terminality, and preserve `CANCEL_FAILED` or
  `UNKNOWN`. Never use `task-update --status failed` as cancellation proof.
- **Current acceptance:** qualification only; cancellation request,
  acknowledgement, terminality, and cleanup remain distinct.
- **Removal condition:** Orca exposes versioned Run/Task cancel operations with
  idempotency, acknowledgement, child-resource coverage, timeout, and recovery.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## TD-ORCA-005 — Aether semantic closeout without native Run close

- **Capability:** `run_close`
- **Severity:** Medium
- **Consequence:** Aether can record product-semantic closure but cannot claim an
  Orca-native Run close/seal transition.
- **Mitigation:** require operational terminality, verified correlation inventory,
  cleanup, evidence disposition, zero unknowns, and an explicit semantic closeout
  receipt labelled `AETHER_OWNED`.
- **Current acceptance:** qualification only; projections must expose the actual
  Orca Run status separately from Aether semantic closeout.
- **Removal condition:** Orca exposes a Run-close/seal operation with immutable
  terminal identity and complete resource disposition, or product evidence proves
  no native close semantics are required.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## TD-ORCA-006 — Eventual consistency and external drift

- **Capabilities:** status, inventory, cancellation, closeout, reconciliation
- **Severity:** High
- **Consequence:** Aether receipts and current Orca observations can temporarily
  disagree; external Orca control may create uncorrelated effects.
- **Mitigation:** source/freshness on every projection, fresh reads before mutation,
  schema/build pinning, reconciliation after restart/timeout, and no cleanup of
  uncorrelated resources.
- **Current acceptance:** direct non-Aether mutation of an admitted Run is outside
  the supported operating contract and must surface as drift/unknown.
- **Removal condition:** an official provider transaction/event contract supplies
  complete causality and ownership, or executed evidence proves bounded drift does
  not violate accepted cases.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## TD-ORCA-007 — Aether-owned response/effect/timeout schemas

- **Capabilities:** all 49 public-command capabilities classified `PARTIAL` by M1.2
- **Severity:** High
- **Consequence:** an Orca update can change output or recovery behavior without a
  catalog-level machine-readable declaration.
- **Mitigation:** pin launcher/artifact/catalog digests, derive bounded schemas from
  isolated fixtures, validate exact response/effect/timeout/recovery behavior, and
  fail closed on material drift.
- **Current acceptance:** all 49 remain `NATIVE/FULL/UNQUALIFIED` until their
  fixtures pass; command existence alone grants no mutation.
- **Removal condition:** Orca publishes complete versioned result, effect, timeout,
  ambiguity, and recovery schemas, or Aether's compatibility suite becomes an
  accepted stable adapter contract.
- **Affected versions:** Orca `1.4.167`; schema bundle is version-specific.

## TD-ORCA-008 — Reconciliation and cleanup latency

- **Capabilities:** reconcile, cancel, close, retry
- **Severity:** Medium
- **Consequence:** safe recovery can take longer than the original operation and
  block dependent dispatch/retry while evidence remains ambiguous.
- **Mitigation:** separate normal timeout, `reconcile_after`, and lease/fence
  deadlines; bounded polling; explicit user-visible `RECONCILIATION_REQUIRED`;
  never infer terminality from deadline expiry.
- **Current acceptance:** latency is acceptable for local bounded swarms only if
  use-case thresholds pass and Hermes remains responsive.
- **Removal condition:** provider receipts/events make terminality immediate enough
  to satisfy the frozen latency/reliability thresholds without polling debt.
- **Affected versions:** Orca `1.4.167`; reassess with measured candidates.

## TD-ORCA-009 — No qualified headless coordinator bootstrap

- **Capabilities:** every coordinator-side orchestration mutation
- **Severity:** Critical
- **Consequence:** `run-create` requires a live admitted Orca terminal sender, but
  the isolated `serve` boundary has no proven public headless sequence for
  registering the synthetic repo/worktree and minting that coordinator identity.
  Read-only status can pass while every swarm mutation remains unavailable.
- **Mitigation:** require a trusted live coordinator terminal binding from Orca
  launch context; validate it with public `terminal show`; bind it to one principal,
  project, provider build, and Run; reject stale/foreign/missing handles; never
  invent or persist a handle as authority. Keep standalone headless mutations
  disabled.
- **Current acceptance:** R3 framing/cold readiness only. Mutation, full lifecycle,
  D1, and R5 remain blocked. A desktop/UI-backed or externally pre-admitted
  coordinator pilot requires a separate operation gate.
- **Removal condition:** Orca exposes a versioned public headless coordinator-admit
  operation, headless worktree/terminal creation returns a usable sender with
  deterministic cleanup, or an explicitly authorized isolated desktop pilot proves
  the trusted binding and restart semantics twice.
- **Affected versions:** Orca `1.4.167`; reassess every provider upgrade.

## Acceptance summary

The product owner accepts these entries as design/qualification debt, not as proof
of operational readiness. D1 and activation require each enabled path's mitigation
to be `PROVEN`; any residual `DEGRADED` guarantee must be explicitly accepted for
the exact candidate.
