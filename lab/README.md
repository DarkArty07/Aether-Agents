# Aether laboratory

`aether_agents.lab` is the formal, Hermes-free Python API for the disposable E2E qualification harness. It owns the scenario loader, deterministic preparation, live one-shot lane, matrix score, observation preparation/live lane, and persistent-session qualification helpers. The package never starts a model or provider during import or preparation.

## Source checkout and installed package

The five historical scripts remain compatibility wrappers. They can be run directly from a checkout:

```bash
python3 scripts/e2e/run.py e2e-01 --prepare-only --run-root /tmp/aether-e2e-01
python3 scripts/e2e/matrix.py --suite full --prepare-only \
  --matrix-root /tmp/aether-e2e-full \
  --history /tmp/aether-e2e-history.jsonl
```

The package API is importable without Hermes:

```python
from aether_agents.lab import load_scenario, prepare_only, score_history
scenario = load_scenario("e2e-01")
```

`--prepare-only` creates only disposable fixtures and compact qualification evidence. It never counts as live reliability. `--live` requires an exact caller-supplied Hermes executable, candidate profile configuration, and the explicit `--allow-model-spend` acknowledgement; this card does not run a model.

## Isolation and parallelism

`matrix.py --parallel 2` is the default and the hard maximum. Independent roots may run concurrently, but each receives a distinct repository/worktree, `HERMES_HOME`, Kanban SQLite board, XDG state/data roots, and evidence root. E2E-15 and any lane sharing a Morfeo session are serialized. An isolation assertion is fatal when it fails.

## Observation suite

The `observation` suite is separate from the PD-74 rolling 20-run score:

```bash
python3 scripts/e2e/matrix.py --suite observation --prepare-only \
  --matrix-root /tmp/aether-observation \
  --history /tmp/aether-observation-history.jsonl
```

Preparation seeds a real local Contract Observation journal and calls the plugin-registered `aether_observe` handler for `status`, `changes`, and `diagnose`. Only action/result metadata is retained. Status and changes are capped at 2048 UTF-8 bytes; diagnose is capped at 4096 bytes. Raw prompts, responses, commands, files, diffs, logs, and events are never evidence fields.

## Persistent E2E-15 prerequisite

The persistent lane uses the native Hermes CLI/TUI under a PTY, sends the scenario's sole owner message once, and observes `state.db` plus the disposable Kanban DB while the process is still alive. A pass requires a post-baseline `flow_terminal` event whose durable task/session relation resolves to the same Morfeo session, a later non-empty assistant report persisted in `state.db`, and exactly one durable owner message matching the supplied input. PTY output is never evidence and no harness continuation is sent. If any native observation is unavailable, the result remains `CAPABILITY_WALL` with the bounded reason `native_same_session_wake_unobserved`; no notifier substitute is created.

## Per-flow E2E-16 qualification lane

E2E-16 is the serial persistent-session qualification lane. The live runner invokes the exact caller-supplied Hermes executable, waits for the first native Supervisor affinity binding, terminates that worker process, and uses Hermes's disposable-board reclaim/dispatch path to resume the same flow. After dispatch it runs a separate native-Hermes interpreter over the disposable board/state databases: observed affinity rows provide non-empty cross-flow/Project/role session ids, the native registration guard is exercised with wrong identities, stale-generation writes are attempted on a database copy, and native notification claims verify internal suppression plus terminal/input/revision routing. Workspace identity is compared with the worker's authorized workspace, durable tool evidence is read from the Supervisor transcript, and Implementer sessions are read from the Implementer state database. The harness never sends a reconstructed continuation input or accepts worker-authored task metadata as a control receipt. It records only bounded ids, booleans, route classes, and process exit codes under `affinity`; it is marked `rolling_reliability_counted: false` so a qualification result cannot inflate the rolling reliability score. Missing native affinity support is reported honestly as a capability wall, and live execution remains spend-gated.

## Evidence

`run.json`, `matrix.json`, and observation/persistent reports use the compact `aether.lab.evidence.v1` schema. They record statuses, counts, route classes, bounded booleans, and safe action metadata only. Legacy wrapper filenames are retained where callers already depend on them, but their contents are redacted metadata rather than command output, transcripts, raw events, or diffs. The provider-backed observation lane remains separate from PD-74. The native E2E-15 runner now uses the persistent PTY lane and records the explicit capability wall when its database proof is unavailable; it never upgrades a one-shot or synthetic continuation to persistent wake, so persistent wake and the rolling reliability gate remain pending until a live native proof passes.
