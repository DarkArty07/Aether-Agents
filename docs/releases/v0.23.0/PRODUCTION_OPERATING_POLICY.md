# v0.23.0 Orca Production Operating Policy

> **Status:** APPROVED POLICY — EFFECTIVE ONLY AFTER THE M1 PRODUCTION-ENTRY GATE
> **Date:** 2026-08-09; amended 2026-08-11
> **Owner:** Christopher (DarkArty07)
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`

## Purpose

This policy governs real Aether multi-agent work after Aether MCP + Orca has been installed, registered, validated, and accepted through v0.23.0 M1. It prevents production dogfooding from hiding defects through a legacy fallback.

Until M1 passes, Aether MCP may be installed and active as a bounded v0.23.0
candidate, but Orca is not yet the accepted normal multi-agent path. The current
named installation exposes 15 tools and has passed M1.2; M1.3 model-backed
qualification and the M1.4 production-entry decision remain pending. This policy
therefore describes the post-entry routing contract while current candidate use
remains controlled qualification and repair.

## Routing rule

Hermes first decides whether a Task needs a specialist contribution.

- If one accountable owner is sufficient, Hermes may work directly.
- If a multi-agent or specialist Task is selected, Aether MCP + Orca is mandatory.
- A failed Orca Task may not be completed through Olympus, `talk_to`, Harmonia, ACPManager, a renamed equivalent, or dual-write.
- A separately selected direct Hermes Task must be justified by the work contract, not by an unrecorded Orca failure.

## Production state model

```text
ORCA_REQUIRED
  -> RUNNING
  -> SUCCEEDED
  -> VERIFIED
  -> CLOSED

ORCA_REQUIRED / RUNNING
  -> ORCA_INTEGRATION_INCIDENT
  -> REPAIRING
  -> RETRY_REQUIRED
  -> RUNNING

ORCA_INTEGRATION_INCIDENT
  -> BLOCKED
```

`worker_done` is technical terminality, not product acceptance. Hermes verifies artifacts and evidence before semantic closure.

## Incident protocol

An `ORCA_INTEGRATION_INCIDENT` is opened when the required path cannot safely admit, start, dispatch, observe, message, recover, retry, cancel, close, or clean the Task, or when the expected generic specialist contract cannot be executed without leaving the approved path.

### Required sequence

1. **Preserve:** record a redacted failure signature, exact component/version identities, Task/Run/Dispatch correlations, last known state, user impact, and surviving resources.
2. **Contain:** stop further effects and clean only resources proven to belong to the attempt. Preserve diagnostic evidence.
3. **Reproduce:** create the smallest safe reproducer or deterministic diagnostic. A fixture does not replace the later real-path retry.
4. **Classify:** assign one primary owning layer and record contributing conditions.
5. **Repair:** make the smallest coherent correction in the owning layer.
6. **Verify:** run the reproducer, affected-path checks, and cleanup/restart checks proportional to the defect.
7. **Retry:** repeat the original Task or a contract-equivalent real Task through Aether MCP + Orca.
8. **Close:** record before/after evidence, result, residual unknowns, regression, and zero-survivor state.

After three failed attempts using the same repair approach, stop, preserve evidence, and escalate the actual blocker. Do not rename the approach and continue indefinitely.

## Classification

### Aether product or contract

Examples: wrong task decomposition, participant policy, acceptance, authority, retry rule, or unsupported product expectation.

Repair the Aether contract or return the product decision to Hermes/user authority. Do not patch Orca to absorb product meaning.

### Aether MCP or adapter

Examples: receipt composition, CLI/result parsing, identity correlation, liveness inference, idempotency, reconciliation, timeout, evidence, or cleanup-plan defects.

Repair Aether MCP/adapter behavior against Orca's public interface. Do not read or mutate Orca private stores as a shortcut.

### Orca

Examples: public lifecycle operation violates its documented contract, loses authoritative state, creates an unmanageable resource, or cannot recover/clean a resource it owns.

Prove the defect at the Orca boundary first. Then select the smallest controlled action: compatible Orca update, isolated correction, upstream contribution, or exact patched build. Do not rebuild Orca mechanics inside Aether and call the integration healthy.

### Environment

Examples: X11/display, filesystem, permissions, process supervision, package identity, or resource exhaustion.

Repair the named environment with reversible, least-scope changes and preserve the exact before/after identity.

### Provider/account

Examples: authentication, quota, rate limit, model availability, or provider timeout.

Report typed `BLOCKED` or `UNKNOWN`. Do not reauthenticate, rotate credentials, switch protected accounts, enable PAYG, spend, or substitute a model without authority.

## Break-glass maintenance

If Orca is unavailable, Hermes may repair Aether MCP, the adapter, Orca, or the named environment directly because the broken runtime cannot reliably delegate its own repair.

Break-glass maintenance must:

- stay inside the incident repair scope;
- preserve the blocked original Task;
- avoid completing that Task and labelling it Orca success;
- verify the repaired runtime independently;
- retry the original or contract-equivalent real Task through Orca;
- end when the execution path is restored or the incident is explicitly blocked.

## Rollback

Rollback is mandatory for production entry and material runtime changes. It must preserve:

- user project data;
- historical `.aether` stores;
- diagnostic evidence;
- previous version/config source;
- secret custody;
- unrelated sessions and processes.

Rollback must prove the named registration, wrapper, process, listener, worktree, terminal, lease, and data-root state. It is not permission to continue normal multi-agent work through Olympus.

## Evidence and privacy

Operational evidence may contain only the minimum needed to diagnose and compare:

- redacted model-visible context and Task contract;
- tool schemas/calls/results and public Orca operations;
- artifact references/digests and verification;
- typed errors, corrections, retries, timing, usage/cost when available;
- participant/profile/model/toolset and source identities;
- outcome, acceptance, cleanup, and residual unknowns.

Never persist credentials, tokens, passwords, connection strings, private chain-of-thought, unrestricted terminal history, foreign-project content, or unreviewed raw provider payloads. Sensitive values are replaced with `[REDACTED]`; a redaction failure quarantines the evidence.

Operational traces are not automatically training-eligible. Dataset construction, export, training, fine-tuning, and promotion require separate scope and authority.

## MCP learning and tool-surface optimization

v0.23.0 treats the usability of the Aether MCP contract as product behavior, not
cosmetic documentation. An incident may include:

- a generic or misleading tool description;
- a missing precondition or identity provenance rule;
- an avoidable wrong-order or wrong-target call;
- an error that does not distinguish retry, reconcile, user decision, or hard
  blocker;
- excessive always-visible context or repeated mechanical correlation work;
- a result that implies execution when it only validates or plans;
- source, wheel, installed package, live process, discovered catalog, or prompt
  cache drift.

Accepted repairs should place learning in the narrowest durable layer:
descriptions and field schemas for selection context, typed results/errors for
state transitions, tests for mechanical regressions, reference for exact lookup,
trace/evidence for observed runs, and decisions for product authority.

The current 15 tools remain the compatibility baseline. A smaller intent-level
normal surface with retained diagnostic operations is a proposal under
`MCP_TOOL_SURFACE_LEARNING_PLAN.md`, not an accepted replacement. Tool count,
call count, or token reduction cannot compensate for hidden effects, weaker
diagnostics, authority drift, lower correctness, or incomplete cleanup.

No v0.23.0 acceptance, incident evidence, or source Release automatically starts
v0.24.0. Version progression requires a later explicit product-owner decision.

## Session closeout

A real multi-agent session closes only when:

- the Task outcome is verified or explicitly blocked;
- any incident has a GitHub/state record with its actual disposition;
- no automatic legacy fallback occurred;
- cleanup and surviving-resource inventory are complete;
- user-visible unknowns and limitations are stated;
- durable product learning is stored in the proper versioned document, issue, test, skill, or decision layer.
