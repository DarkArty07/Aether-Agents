# M2 Foundation Acceptance

> **Milestone:** M2.3-M2.7
> **Verdict:** PASS — DEFAULT-OFF; STOP BEFORE M3
> **Accepted candidate:** `3ffd4be15236f4efb50ce3008a176b107a2b006e`
> **Accepted tree:** `d27127e89c25557693a9aa3591da1c73bb269d3c`
> **Date:** 2026-08-09
> **Authority:** Christopher authorized completion through M2 and required a strict stop before M3.

## 1. Result

M2 is technically complete for the exact default-off v0.22.0 candidate. The
implementation adds the internal foundation behind the accepted
`aether.mcp/v1alpha2` schemas without registering any MCP tool and without
starting M3 lifecycle execution.

The completed boundary contains:

- trusted launch-context and project admission with server-generated project IDs;
- exact principal/profile/home and Git common-directory/worktree correlation;
- SQLite WAL schema-v2 operation receipts and semantic decision/evidence events;
- durable-before-effect intents, exact idempotency and explicit `UNKNOWN`;
- hash-chain integrity, monotonic migration and bounded pagination;
- fail-closed AES-256-GCM protected rich content;
- redaction before persistence, project-scoped references, quotas and atomic files;
- deterministic manifest/DAG/write-scope validation;
- a bundled, digest-pinned Orca 1.4.167 read-only command catalog;
- one integrated internal `M2Foundation` service with zero registered/callable tools.

## 2. Coordinator-admission decision

The headless `orca serve` path still cannot create the trusted coordinator
terminal required by Orca 1.4.167. The owner-authorized alternative was therefore
qualified against two independent fresh desktop-renderer profiles using only the
public structured CLI.

Each probe executed:

```text
desktop ready
-> admit isolated repository
-> create coordinator terminal
-> create Run
-> create metadata-only Task
-> inspect projections
-> restart Orca
-> recover Run and Task
-> create replacement terminal
-> run-use at consumer generation 2
-> complete Task without dispatch
-> reset orchestration state
-> close terminal
-> remove all owned resources
```

Both probes passed. They created zero workers, invoked zero models, used no
credentials or budget, and left zero owned process, terminal, worktree/root or
AppImage-extraction survivors.

This qualifies only the exact desktop-renderer/public-CLI binding. It does not
claim that headless `serve` admission works and does not authorize UI automation
as a normal product interface.

## 3. Acceptance by submilestone

### M2.3 — Project and principal admission: PASS

- caller request schemas contain no principal override;
- the coordinator context is fixed at process construction;
- paths must be absolute, canonical, existing and symlink-free;
- Git siblings correlate to one project with distinct placement IDs;
- foreign principals/profiles receive the same non-enumerating failure;
- moved/replaced repositories fail with identity mismatch;
- admission writes only to the isolated Aether state root, never to the project.

### M2.4 — Migrations, journal and receipts: PASS

- schema migration `1 -> 2` preserves operation events;
- newer schemas fail closed;
- intents commit before provider execution;
- concurrent exact first intent has one winner and one replay;
- changed canonical input produces `IDEMPOTENCY_CONFLICT`;
- provider exceptions persist `UNKNOWN` instead of guessing delivery;
- busy/failed storage prevents provider execution;
- operation and semantic hash chains detect direct database tampering.

Aether stores correlation, authorization, decisions, evidence and receipts. It
does not mirror Orca Run, Task, Dispatch, worker, message, terminal or worktree
state.

### M2.5 — Protected content: PASS DEFAULT-OFF

- rich content uses AES-256-GCM with a random 96-bit nonce and authenticated AAD;
- plaintext is redacted before encryption or persistence;
- references are HMAC-derived with a per-project key, preventing cross-project
  content correlation;
- hidden reasoning and non-redaction-compatible binary payloads are rejected;
- wrong-project reads, modified ciphertext and malformed envelopes fail closed;
- atomic temporary-write, `fsync`, replace, quotas and orphan cleanup are covered;
- `cryptography==50.0.0` is directly pinned; `pip-audit` found no known
  vulnerabilities at the executed boundary.

No production key provider is enabled. `DISABLED`, `STRUCTURED_ONLY` rich-content
attempts and `FULL_EPISODE` without an admitted key return `CAPTURE_DISABLED` and
persist nothing. The candidate has no authorized specialist runtime for an
independent security reviewer, so production key custody and any capture
activation remain blocked behind a separate D2 review. This limitation is not
converted into an activation pass.

### M2.6 — Read-only foundation services: PASS

- manifest schemas, dependencies, cycles and independent write conflicts are
  validated without creating a Run;
- decisions/evidence append and query through bounded, project-scoped cursors;
- catalog search and describe bind to the exact catalog digest;
- `orca_call` plans only admitted read-only argv tuples;
- unknown arguments, command IDs, catalog drift and malformed provider envelopes
  fail closed;
- the packaged wheel includes the exact catalog bundle.

### M2.7 — Foundation closure: PASS

The exact detached candidate passed:

- `158 passed`, `0 failed` through `make test`;
- 131 tests collected under `tests/aether_mcp`;
- Ruff;
- `compileall`;
- release-governance policy;
- dependency vulnerability audit;
- sdist and wheel build;
- clean wheel installation;
- bundled catalog load and digest check;
- zero callable tools;
- forbidden runtime namespace and high-confidence secret scans;
- final cleanup and clean worktree verification.

Canonical machine-readable evidence is in
[`M2_FOUNDATION_EVIDENCE.json`](./M2_FOUNDATION_EVIDENCE.json).

## 4. Explicitly not accepted

This milestone did **not**:

- begin M3;
- create an Aether lifecycle Run;
- dispatch a worker;
- use a model, provider credential or budget;
- enable a production key provider or learning capture;
- register or activate Aether MCP;
- push, merge, tag, publish, deploy or create a persistent service.

## 5. Stop condition

Stop here. The next possible action is a separately authorized M3 lifecycle task
with no workers. M4 and every later worker/swarm, model, Release and activation
boundary remain gated independently.
