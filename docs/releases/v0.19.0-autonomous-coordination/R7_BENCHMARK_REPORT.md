# R7 Shadow Benchmark Report

## Scope and commands

R7 was exercised through the real `observe_olympus_session`, `ShadowSessionCorrelation`, `compare_shadow`, process-local registry, and disposable durable SQLite registry APIs. The Olympus evidence source was a local read-only fake implementing the two public evidence methods; no live Daimon, gateway, runtime, authentication, configuration, service, lifecycle, or external-effect calls were used.

Executed on 2026-07-22:

```text
uv run pytest tests/coordination/test_r7_system.py -q
uv run python scripts/run_r7_shadow_benchmark.py --output /tmp/r7-shadow-a.json --repetitions 5
uv run python scripts/run_r7_shadow_benchmark.py --output /tmp/r7-shadow-b.json --repetitions 5
```

Observed outputs:

```text
15 passed
{"detected_failure_runs": 25, "lifecycle_effect_calls": 0, "runs": 50, "scenarios": 10, "schema_version": "r7-shadow-benchmark-v2"}
{"detected_failure_runs": 25, "lifecycle_effect_calls": 0, "runs": 50, "scenarios": 10, "schema_version": "r7-shadow-benchmark-v2"}
```

The two output files had equal semantic summaries. Timing varied as expected.

## Measured results

- Schema: `r7-shadow-benchmark-v2`.
- Scenarios: 10; repetitions per scenario: 5; total runs per execution: 50.
- Injected failure runs: 25; detected failure runs: 25; detection recall: `1.000`.
- Clean false-positive rate: `0.000`.
- Real probe count: `0`; external effects: `0`; lifecycle/effect calls: `0`.
- Manual reconciliation steps avoided: 25 per execution. Counting rule: one avoided inspection when a typed injected fault is detected; clean and disabled paths count zero.
- Durable registry growth: 24,576 bytes per disposable restart scenario.
- Cost: `unknown`.

Mean observation overhead in the first/second execution, milliseconds:

| Scenario | Run A | Run B |
|---|---:|---:|
| clean single task | 0.4288 | 0.4821 |
| dependency chain | 0.9175 | 0.9064 |
| parallel independent | 0.8575 | 0.8316 |
| duplicate dispatch | 0.3029 | 0.3166 |
| runtime unavailable then restored | 0.6232 | 0.5518 |
| durable restart/rebuild | 1.4464 | 1.4432 |
| budget rejection | 0.2959 | 0.3016 |
| reviewer violation | 0.3232 | 0.3140 |
| unknown effect | 0.5829 | 0.5132 |
| disabled rollback | 0.0406 | 0.0397 |

Maximum measured recovery time was 0.4683/0.2592 ms for runtime restoration and 0.5832/0.5843 ms for durable registry recreation.

## Scenario evidence

The benchmark exercised clean single-task observation, a three-stage dependency chain, three independent tasks, duplicate delivery, runtime loss followed by restoration, durable registry recreation, budget rejection, reviewer violation, unknown effect, and disabled rollback. Clean observations agreed on assignment, participant, session correlation, and status. Injected conditions generated typed mismatches. Every report retained `semantic_complete=false`.

The disabled rollback path used only `compare_shadow` with the default configuration and verified zero observer reads, session derivations, and store writes.

## Limitations

- This is isolated local evidence, not a live pilot. The fake evidence source does not validate ACP transport, model behavior, gateway health, provider cost, or production throughput.
- Detection recall is reported instead of “precision”: all benchmark positives were injected known faults, so the test can measure whether faults were detected but cannot estimate real-world positive predictive value.
- The three-stage dependency scenario validates staged shadow observation; it does not grant the coordinator scheduling authority.
- Timing is Python/SQLite micro-benchmark data on one host and must not be generalized to production.
- No metered provider was used, so cost savings remain unknown.
- Durable SQLite evidence is disposable and local; production key custody, cross-host identity, and activation migration remain separate prerequisites.
- Shadow mode never establishes semantic completion or lifecycle ownership.
