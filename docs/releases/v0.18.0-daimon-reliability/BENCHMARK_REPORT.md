# Daimon Reliability Benchmark Report — v0.18.0

**Release date:** 2026-07-16

## Scope and methodology

This release records a baseline/post comparison of the six Daimon profiles using 19 versioned, synthetic cases. Each invocation used an isolated disposable work directory and profile session. The runner captured redacted final-response and artifact evidence; generated results remain local and are not versioned.

The benchmark uses deterministic assertions against retained evidence. It is a release regression check, not a statistical study: no statistical significance or performance improvement is claimed.

## Commands

```bash
python3 evaluations/daimon-reliability-v0.18.0/validate_cases.py
python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --self-test
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --self-test

python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase baseline --timeout 300
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --phase baseline

python3 evaluations/daimon-reliability-v0.18.0/run_benchmark.py --phase post --timeout 300
python3 evaluations/daimon-reliability-v0.18.0/score_results.py --phase post
```

## Aggregate results

Both phases completed all 19 cases.

| Phase | PASS | FAIL | INSUFFICIENT | Missing results | Hard gate failures |
|---|---:|---:|---:|---:|---:|
| Baseline | 23 | 0 | 5 | 0 | 0 |
| Post | 23 | 0 | 5 | 0 | 0 |

There were **zero deterministic PASS-to-non-PASS regressions**. Equal binary totals do not demonstrate an improvement; they show that no deterministic regression was observed under this benchmark's retained evidence.

## Per-agent assertion counts, baseline → post

Counts are `PASS / FAIL / INSUFFICIENT`.

| Daimon | Baseline | Post |
|---|---:|---:|
| Ariadna | 4 / 0 / 2 | 4 / 0 / 2 |
| Athena | 6 / 0 / 0 | 6 / 0 / 0 |
| Daedalus | 3 / 0 / 0 | 3 / 0 / 0 |
| Etalides | 3 / 0 / 1 | 3 / 0 / 1 |
| Hefesto | 3 / 0 / 2 | 3 / 0 / 2 |
| Ictinus | 4 / 0 / 0 | 4 / 0 / 0 |

## Evidence limitation

The five **INSUFFICIENT** outcomes are trace/function assertions only: two for Ariadna, one for Etalides, and two for Hefesto. `hermes -z` exposes the final response but not tool/function traces, so the required trace evidence was unavailable. These outcomes are **not passes and not failures**; no unavailable trace was inferred or claimed.

## Qualitative release deltas

- The six profiles received role-specific evidence and verification contracts.
- Semantic response assertions were calibrated to grouped, evidence-compatible wording rather than a single phrase.
- The positive Hefesto normalization fixture was clarified so its expected implementation result is explicit and verifiable.
- Configuration and templates were verified in parity and intentionally left unchanged: the benchmark supplied no evidence for runtime tuning.

## Mid-run calibration rationale

Initial semantic checks were too literal for equivalent, evidence-supported responses. Assertion groups were calibrated mid-run to recognize approved semantic alternatives while preserving deterministic scoring and prohibitions. The calibration did not convert unavailable trace evidence into success and did not change the treatment of a missing trace: it remains `INSUFFICIENT`.

## Security and data handling

The benchmark used synthetic fixtures. Authentication files, credentials, credential fingerprints, and production data were excluded from prompts, fixtures, generated evidence, and this report. Raw responses, temporary work directories, and local generated result artifacts are not included here.
