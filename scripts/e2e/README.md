# Aether disposable E2E laboratory

This directory preserves the historical command surface for PD-71 through PD-76. The canonical implementation is the Hermes-free `aether_agents.lab` package and the canonical resources/operator documentation live under [`lab/`](../../lab/README.md); files here are thin compatibility wrappers. The laboratory does not add a daemon, workflow engine, database, notifier, or evaluator model.

## What is real

A `--live` run uses the caller-supplied Hermes executable, candidate profile configuration, candidate tracked `SOUL.md` files, the real pre-tool hook, a real SQLite Kanban board, real worker processes, real Git repositories/worktrees, and the scenario's deterministic acceptance command.

Only the repository fixture, owner message, isolated profile/state roots, and optional fault injection are synthetic.

The harness never copies private profile sessions or memories into the run and never serializes subprocess environment values into evidence.

## Deterministic preparation

Validate all fixtures and evidence paths without invoking Hermes or a model:

```bash
python3 scripts/e2e/matrix.py \
  --suite full \
  --prepare-only \
  --matrix-root /tmp/aether-e2e-prepared \
  --history /tmp/aether-e2e-history.jsonl
```

`PREPARED` is deliberately not counted as agent reliability.

## One live scenario

A live scenario may consume provider/model quota. The runner refuses to start Hermes unless the explicit spend acknowledgement is present:

```bash
python3 scripts/e2e/run.py e2e-01 \
  --live \
  --hermes /path/to/exact/hermes \
  --profile-root /path/to/candidate-profile-configs \
  --allow-model-spend
```

`--profile-root` contains `morfeo/`, `supervisor/`, and `implementer/` `config.yaml` files. The harness copies only those configs into disposable homes, overlays the versioned candidate `SOUL.md` files, rewrites the candidate hook path to the disposable profile, and installs the versioned hook bytes there.

## Canary and reliability matrix

The mandatory small canary is scenarios `01, 03, 07, 08, 11`:

```bash
python3 scripts/e2e/matrix.py \
  --suite canary \
  --live \
  --hermes /path/to/exact/hermes \
  --profile-root /path/to/candidate-profile-configs \
  --allow-model-spend
```

The reliability suite executes the fifteen scenarios once plus the five canaries again, yielding the 20-run PD-74 window:

```bash
python3 scripts/e2e/matrix.py \
  --suite reliability \
  --live \
  --hermes /path/to/exact/hermes \
  --profile-root /path/to/candidate-profile-configs \
  --allow-model-spend
```

The gate requires:

- at least 19 PASS results in the latest 20 live runs;
- the latest 10 live runs all PASS;
- direct, pipeline, safety, and recovery scenarios represented;
- zero guard-caused manual recovery;
- zero observed protected-edge violation;
- zero unintended Aether source-tree modification.

## Synthetic owner

Each scenario contains one owner message and only the owner replies explicitly authorized by the scenario. An unexpected clarification fails as `UNEXPECTED_OWNER_DEPENDENCY`; the harness does not improvise an answer to keep Morfeo moving.

For exploratory qualification, the current owner or an evaluator acting from the same prepared scenario can answer naturally while deliberately refusing to inspect or repair the board/runtime during the dialogue. Once behavior is stable, the scripted lane is the regression surface. The portable harness does not encode a specific person's identity.

## Recovery fault

E2E-11 injects one disposable false-positive hook into Morfeo's isolated profile. The injected wrapper blocks ordinary structured file mutation but delegates all other calls to a sibling `known-good` copy of the candidate hook. PASS requires Morfeo to restore the real hook bytes and finish the project canary; changing Aether source is a failure.

## Persistent Morfeo qualification

The one-shot runner can reconstruct the final Morfeo turn after the board settles, but that continuation is recorded as **harness input, not owner input** and does not qualify autonomous wake/resume.

E2E-15 remains the explicit persistent-session gate. The project must first run a live probe of the supported Hermes CLI/TUI/gateway surfaces and select only a lane that demonstrably wakes the same Morfeo session from the real terminal board event. Do not build a notifier substitute merely to make this gate pass.
