# Daimon Reliability Benchmark — v0.18.0

This package provides a reproducible baseline/post-prompt benchmark for the six GPT-5.6-Terra Daimons. It does **not** modify runtime `SOUL.md`, configuration, templates, or baseline v0.17 prompts.

## Contents

- `cases.json` — versioned contract for all 19 cases, each bound to a concrete fixture.
- `fixtures/<CASE-ID>/fixture.md` — safe synthetic input copied to a fresh disposable work directory for that case.
- `run_benchmark.py` — stdlib-only isolated runner.
- `score_results.py` — deterministic evidence scorer.
- `validate_cases.py` — structural case validator.
- `results/` — output destination; generated result data is not versioned.

## Safety model

Every invocation gets a fresh `HERMES_HOME` profile session and a fresh working copy below the system temporary directory (`/tmp/aether-daimon-reliability/<phase>/`). The runner never points an agent at this repository or a production fixture. The structured prompt embeds the concrete fixture text, including no-tool synthetic cases, and forbids network, credential, production, and outside-workdir access.

The runner records its prompt, redacted stdout/stderr, return code, elapsed time, profile, non-secret model/provider metadata, and an artifact snapshot. `hermes -z` only prints the final response, so tool/function trace evidence is recorded as unavailable (`null`) rather than invented. The scorer therefore marks trace/function assertions `INSUFFICIENT` unless a result file explicitly contains retained trace evidence.

## Validation and local self-tests

```bash
python3 evaluations/daimon-reliability-v0.18.0/validate_cases.py
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --self-test
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --self-test
```

## Exact benchmark commands

Run the untouched-prompt baseline:

```bash
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase baseline --timeout 300
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --phase baseline
```

After the separately approved prompt-only change, run the comparable post phase:

```bash
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase post --timeout 300
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --phase post
```

Useful scoped operations:

```bash
# inspect all 19 profile/fixture/workdir plans without invoking a model
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase baseline --dry-run

# run or resume a subset
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase baseline --agent athena --timeout 300
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase baseline --case ATHENA-001 --resume

# generate an explicitly partial score; hard deterministic failures still return nonzero
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --phase baseline --allow-incomplete
```

Each case result is incrementally written to `results/<phase>/<CASE-ID>.json`; score output is `summary.json` and `SUMMARY.md` in the same phase directory. The scorer returns nonzero for missing required results (unless `--allow-incomplete`) or any deterministic `FAIL`. It does not treat `INSUFFICIENT` evidence as a pass.

## Cleanup and restoration

1. Generated results are local evidence. Archive them outside the repository if they must be retained, then remove only the generated phase directory: `rm -rf evaluations/daimon-reliability-v0.18.0/results/baseline evaluations/daimon-reliability-v0.18.0/results/post`.
2. Remove disposable copies at any time: `rm -rf /tmp/aether-daimon-reliability`.
3. No runtime profile, prompt, configuration, or production project is modified by the runner. To restore the benchmark package itself, discard only changes under `evaluations/daimon-reliability-v0.18.0/`; do not discard unrelated local work.

Do not average away a release-blocking deterministic failure. Operational failures remain distinct from security or behavioral failures and are scored only from current retained evidence.
