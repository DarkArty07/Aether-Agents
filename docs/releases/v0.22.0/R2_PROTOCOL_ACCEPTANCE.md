# R2 — Successor Alpha Protocol Acceptance

> **Status:** CLOSED / PASS
> **Date:** 2026-08-08
> **Protocol:** `aether.mcp/v1alpha2`
> **Historical protocol preserved:** `aether.mcp/v1alpha1`
> **Implementation owner:** Hermes
> **Acceptance owner:** Hermes for the deterministic R2 gate
> **Canonical task:** `../../external-agent/TASK-ORCA-ADAPTER-REDESIGN.md`
> **MCP registration/activation:** Absent

## 1. Scope accepted

R2 replaces the unregistered historical 24-schema alpha contract with a new
unregistered 15-schema successor without rewriting historical evidence.

Accepted successor operational tools:

```text
project_admit
project_inspect
swarm_validate
swarm_start
swarm_status
swarm_dispatch
swarm_message
swarm_reconcile
swarm_retry
swarm_cancel
swarm_close
swarm_trace
orca_search
orca_describe
orca_call
```

The following prior names are absent from the successor bundle and reject request
validation:

```text
swarm_record_decision
swarm_record_evidence
orca_batch
orca_events
learning_capture
learning_label
learning_dataset
learning_export
project_forget
```

## 2. Protocol changes

- Product protocol advanced from `aether.mcp/v1alpha1` to
  `aether.mcp/v1alpha2` because tool removal and `swarm_trace` required-field/
  semantic changes are not compatible amendments.
- `swarm_trace` now has exact `query`, `record_decision`, and `record_evidence`
  actions.
- Query requires no operation identity and accepts only query fields.
- Append actions require one `LOCAL_APPEND_ONLY` operation, the same project
  identity, a non-null Run, and exactly one typed decision/evidence body.
- Explicit `CANCELLED`, `CANCEL_FAILED`, and `CLEANUP_FAILED` outcomes were added.
- The public registry remains deeply immutable.
- Unknown request fields, caller principal fields, arbitrary shell/command fields,
  unbounded values, malformed identities, and protocol mismatch remain fail-closed.

## 3. Schema evidence

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `schemas/aether-mcp/v1alpha2/bundle.json` | 66,228 | `336e141d56563da882ae7426ae2a0b8647aef501962a56357f11652265d05723` |
| historical `schemas/aether-mcp/v1alpha1/bundle.json` | 94,139 | `e7f39a76ac4795ade2ec0a15bf64b4cab2233b912cf2285b0ce76d2805a2e605` |

Generation from `schema_bundle_bytes()` matched the committed successor bytes
exactly. The historical alpha1 digest remained exact.

## 4. TDD evidence

### Baseline

The existing suite, excluding only the real M1.3 lifecycle test whose temporary
Xvfb fixture had been removed at the prior closeout, returned:

```text
100 passed, 1 deselected
```

The excluded test is deliberately reconstructed and executed in R3.

### RED

Before production edits, the successor-focused selection returned:

```text
6 failed, 1 passed, 19 deselected
```

The six causal failures covered:

1. protocol still `v1alpha1`;
2. 24 schemas instead of 15;
3. removed/deferred names still exported;
4. missing cancel/cleanup outcomes;
5. no typed `swarm_trace` action contract;
6. missing `v1alpha2` snapshot.

### GREEN and regression

```text
focused protocol + bootstrap: 30 passed
full non-real suite:          105 passed, 1 deselected
Ruff affected files:         PASS
compileall src + tests:       PASS
schema regeneration:         PASS
stdio zero-tool smoke:        PASS
```

## 5. Runtime and safety evidence

- `CALLABLE_TOOL_NAMES == frozenset()`;
- FastMCP server registry contains exactly zero tools;
- no Aether MCP profile/config registration exists;
- no Orca command or process was invoked in R2;
- no listener or persistent service was started;
- no credential/provider/model path was used;
- dependency resolution occurred only through an ephemeral `/tmp` uv cache;
- no system/global package or project runtime was changed.

## 6. Acceptance result

R2 is `PASS`. The provider-independent `v1alpha2` contract is ready for R3
lifecycle qualification and later R4 adapter implementation.

This result does not grant D1, prove any Orca capability, register a tool, accept
adapter behavior, authorize model-backed workers, or authorize integration,
Release, deployment, or activation.
