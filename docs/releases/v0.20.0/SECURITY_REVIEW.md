# v0.20.0 Self-Improvement Bootstrap — Security Review

## Verdict

`PASS FOR DEFAULT-OFF SOURCE INTEGRITY`

`NOT REVIEWED FOR ACTIVATION OR PRODUCTION RELEASE`

Athena was not invoked under the project operator's standing exclusion. Hermes performed a direct deterministic review using the repository security checklist and injected failure tests.

## Trust boundaries reviewed

- Aether versus foreign project identity
- Project-local ledger path
- Plugin activation boundary
- SQLite transaction integrity
- Session concurrency and stale-owner reconciliation
- Tool, model, and coordination telemetry
- Secret and conversation payload exclusion
- Release-evidence authority

## Findings corrected during implementation

### 1. Symlinked ledger path could escape project-local storage

- Severity: Medium in the local trusted-repository deployment model
- Initial cause: resolving the final database path before checking for symlinks followed `.aether` to an external directory.
- Correction: preserve the lexical path, reject symlinked `.aether` and database paths, and verify no external database is created.
- Evidence: deterministic symlink adversarial test passes.

### 2. Harmonia tool metric and classification were not atomic

- Severity: Medium for evidence integrity
- Initial cause: generic tool evidence and coordination classification committed in separate SQLite transactions.
- Correction: `record_tool_observation` writes both records in one transaction.
- Evidence: an injected SQLite trigger aborts the classification insert and proves that the generic tool row also rolls back.

### 3. New sessions could misclassify live concurrent sessions as abandoned

- Severity: Medium for lifecycle integrity
- Initial cause: all prior active rows were reconciled when a new session started.
- Correction: persist runtime instance and PID ownership, protect known same-runtime sessions, preserve live external owners, and reconcile only replaced or dead owners.
- Evidence: deterministic same-runtime, live-process, and replaced-runtime tests pass.

### 4. Foreign workspaces could resolve the Aether ledger through ambient or parent state

- Severity: High for the cross-project isolation contract if the plugin were activated.
- Initial cause: project discovery accepted a process-wide `AETHER_PROJECT_ROOT` fallback and searched past a nearer foreign Git repository until it found the parent Aether manifest.
- Correction: ambient redirection was removed and discovery now stops at the nearest Git repository boundary, accepting it only when that repository carries the validated Aether manifest.
- Evidence: deterministic regressions prove that an environment variable cannot redirect a foreign workspace, a nested foreign repository cannot inherit parent Aether identity, and a genuine Aether subdirectory still resolves correctly. Tracked in GitHub #125 until integration.

## Controls verified

- YAML uses `safe_load` and the manifest is validated against fixed safety invariants.
- SQL values are parameterized; the only dynamic SQL fragment is a placeholder list derived from an internal row count.
- The SQLite file is created with mode `0600` before opening.
- Hook payloads never persist tool arguments, tool results, user messages, assistant responses, prompts, or conversation history.
- Router fields are allowlisted, bounded, and redacted when secret-like.
- Missing route metadata remains `NULL`/unknown rather than being inferred.
- The plugin is discoverable but not enabled.
- Non-Aether workspaces cannot create or mutate the cycle ledger.
- Interrupted sessions cannot be relabelled as cleanly finalized.
- Release evidence never approves merge, tag, release, deployment, or architecture.

## Residual risks and deferred review

- PID reuse may conservatively defer reconciliation; it cannot create a false success signal.
- Hook failures are logged and omit evidence rather than crashing Hermes; omitted evidence keeps acceptance at `REQUIRES_MORE_EVIDENCE`.
- Live multi-process SQLite contention has not been exercised through an activated Hermes runtime in this increment.
- Provider route fields depend on metadata supplied by future Hermes hook payloads; unavailable values remain unknown.
- Activation, restart, live pilot, credentials, deployment, and release require a separate review and authorization.
