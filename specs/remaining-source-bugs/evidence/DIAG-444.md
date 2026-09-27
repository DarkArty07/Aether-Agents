# DIAG-444 — bounded Python 3.12 checkpoint authority diagnosis

- Objective Contract: `oc_3f280963213d234e@v1` (AC1/AC3/AC5)
- Plan: `specs/remaining-source-bugs/plan.md` §#444
- Supervisor breakdown: `specs/remaining-source-bugs/tasks.md` at `dabeeb6af25d18d3e2dc7307673159d418c49ac0`
- Aether base: `8721f54b9a2d3be4638812f5fd660800ed07bd41`, tree digest
  `2b10b433911293a00879aba0c48d24c895012b79ccbb5e0bb9a91c60bd1adfa0` (verified at receipt)
- Worktree branch: `aether-agents-2/t_78e06a92-diag-444-bounded-python-3.12-checkpoint`
- Issue: [#444](https://github.com/DarkArty07/Aether-Agents/issues/444) — OPEN at receipt

## Disposition

**Fixture synchronization defect — proven, corrected, bounded.** The reported
Python 3.12-only intermittent failure is a test-side flusher race, not a product
defect in `src/aether_agents/observation/checkpoint.py` or
`src/aether_agents/observation/capture/journal.py`. No product source changed.
The fail-closed review-authority contract is unchanged and the original
assertions, tolerances and timeout constants are untouched.

## Exact mechanism

`CheckpointSink._durable_trace_events` reads durable state through
`JournalWriter.durable_snapshot()`
(`src/aether_agents/observation/capture/journal.py:756`), which acquires the
writer's `_lock` with a bounded timeout
`DURABLE_SNAPSHOT_LOCK_TIMEOUT_S = 0.005`
(`src/aether_agents/observation/capture/journal.py:72,767`). The acquisition is
deliberately bounded so a checkpoint never inherits unbounded kernel-fsync
latency; a timeout returns `None`, and every `None` upstream in
`_durable_review_principal` fails closed to
`CHECKPOINT_AUTHORITY_UNVERIFIED`
(`src/aether_agents/observation/checkpoint.py:789-801,529-531`).

The failure sequence, all inside the final `Collector` of the #444 node:

1. The test appends `review_requested` through `CheckpointSink.emit`, then calls
   `collector.writer.flush()` (`tests/test_observation_journal_storage.py:1188`).
2. The forged `review_approved` is rejected with
   `CHECKPOINT_REFERENCE_UNKNOWN` before any authority read. That rejection
   writes a `critical=True` coverage-gap diagnostic via
   `append_nonblocking` (`checkpoint.py:947-962`, `journal.py:706`), which sets
   `_flush_signal`.
3. The supervised `Flusher` daemon
   (`src/aether_agents/observation/capture/flusher.py:61-77,146-155`) wakes on
   `_flush_signal`, acquires `_lock`, and performs `os.fsync` while holding it.
4. The legitimate `review_approved` then enters `durable_snapshot()`. If the
   flush's fsync is still in flight when the 5 ms lock timeout elapses, the
   snapshot is `None` and the checkpoint is refused.

Instrumentation confirmed step 3/4 as the exact site: a wrapper that probes the
writer lock with the identical `acquire(timeout=DURABLE_SNAPSHOT_LOCK_TIMEOUT_S)`
call recorded a timeout on `MainThread` only during the legitimate emission, and
only when the live flusher was active.

The race is timing-dependent rather than version-dependent — the failure needs
fsync latency that exceeds 5 ms inside the wake window. That is why the node
passed on 3.11 and 3.13 in the same CI matrix, and why it now passes on this
machine's local filesystems, where an explicit `writer.flush()` releases the lock
quickly. CI's loaded, slower-disk runner was the environment that made the window
probable. This is a scheduling/latency race, not a CPython-version semantic
difference: no 3.12-specific behavior in this path was identified or needed for
the diagnosis.

## Correction (smallest complete)

Apply the precedent already established in the same file by `84d83dc1`
("test(observation): isolate checkpoint flusher") to the final Collector of the
#444 node: keep that Collector synchronous so its background flusher cannot race
the explicit flush for the writer lock.

`tests/test_observation_journal_storage.py:1110-1123`

The two earlier Collectors in the same node (native assignment and
classification) are left with their ordinary supervised lifecycle; each is closed
before the next starts, so their final flushes still execute.

The change is a fixture synchronization correction only. It does not alter any
asserted outcome, any tolerance, any timeout constant, or the fail-closed
authority derivation. `src/aether_agents/observation/checkpoint.py`,
`journal.py`, `collector.py` and `flusher.py` are byte-identical to base.

## Verification — direct, this run

Environment: Python 3.12.13 (uv-managed `cpython-3.12`), one isolated worktree
`.venv`, exact Hermes baseline `v2026.8.18` @ `e624e9fde561e1add9388384012b295fde669ade`
already cached at `~/.cache/aether-agents/hermes/v2026.8.18` and re-verified by
the runner. No live board, home, DB, journal or production state was touched;
every fixture used a fresh `tmp_path`.

| Check | Command | Result |
| --- | --- | --- |
| Target node, no contention | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_journal_storage.py::test_checkpoint_sink_derives_review_authority_from_durable_native_assignment` | 1 passed (x6 runs, 3.12) |
| **Fail-before** (git base node, contended fsync) | node under a 50 ms-per-fsync injection, Python 3.12 | **FAILED** at `tests/test_observation_journal_storage.py:1206`: `CheckpointResult(accepted=False, reason_code='CHECKPOINT_AUTHORITY_UNVERIFIED')` |
| **Pass-after** (fixed node, contended fsync) | same injection, Python 3.12 | 1 passed |
| Forged-approval refusal (negative control) | isolated-Collector scenario, forged `profile="morfeo" role="verification"` | refused, `CHECKPOINT_REFERENCE_UNKNOWN` — unchanged |
| Legitimate approval accepted (negative control) | isolated-Collector scenario | accepted, `None` |
| Fail-closed authority preserved when the flusher does race | live-Collector scenario under 50 ms fsync | refused, `CHECKPOINT_AUTHORITY_UNVERIFIED` — the contract still bites |
| Full affected file | `scripts/run_tests.py -- -q tests/test_observation_journal_storage.py` | 119 passed (3.12; repeated on 3.11 and 3.13) |
| Observation siblings | `scripts/run_tests.py -- -q tests/test_observation_{lifecycle,contracts,cli_plugin,reducer}.py tests/test_hermes_baseline.py` | 442 passed |
| Durability siblings | `tests/test_observation_{path_confinement,passive_startup,query_parity}.py`, `tests/test_observation_performance.py` | 36 passed, 4 passed |
| Lab isolation (untouched, regression guard) | `tests/test_lab_writer_isolation.py tests/test_lab_formalization.py` | 37 passed, 1 skipped |
| Python 3.11.15 | full `tests/test_observation_journal_storage.py` | 119 passed |
| Python 3.13.15 | full `tests/test_observation_journal_storage.py` | 119 passed (x3) |
| Ruff check | `ruff check src tests scripts` | All checks passed |
| Ruff format | `ruff format --check src tests scripts` | 200 files already formatted |
| Mypy | `mypy` | Success: no issues found in 77 source files |
| Documentation gate | `scripts/check_documentation.py` | passed |
| Public-artifact gate | `scripts/check_public_artifacts.py --root .` | passed |

## Attributed evidence

Direct, produced by this run: the fail-before/pass-after pair, the three
negative controls, the lock-timeout instrumentation, and every green run above,
all on Python 3.12.13 at base `8721f54b` plus the suite-wide confirmation on
3.11.15 and 3.13.15.

Reused, not re-measured: the issue's recorded historical CI evidence (run
`34959238413`, head `be9f4ac7ac5f881eaa9b338367d1e9b49d7fde0a`, job
`104348599838`, failure at `tests/test_observation_journal_storage.py:1206`)
and its five isolated 3.12.13 repetitions. The historical and current node
bodies were compared directly: the only differences between
`be9f4ac7:tests/test_observation_journal_storage.py` and base are three
unrelated nodes (reader-fence deadline `1.0`→`30.0` at line 2382/2384ff, one
added `XDG_DATA_HOME` fixture line at 2701). The #444 node body itself and
`checkpoint.py`, `journal.py` and `collector.py` are unchanged between
`be9f4ac7` and base, so the historical failure is the same code path.

## NOT RUN

- Full repository test suite and any stress/retry campaign (explicitly excluded;
  a pass streak is not causality and no new causal signal requires it).
- The Python 3.11/3.12/3.13 CI matrix itself; local equivalents were run
  per-version instead.
- Integrated acceptance, PR, check, merge, issue comment/closure and
  branch/worktree cleanup — all owned by the terminal integration card.
- Any live runtime, gateway, service, profile, credential, agent-canary or
  installed-behavior qualification. No claim about installed behavior is made.
- Live production board/home/DB probing; none was contacted.

## Residual and compatibility impact

- Residual: none for this failure mode. The mechanism, the exact site and the
  correction are established by an instrumented reproduction, not inference.
- `release_impact: none` — a test fixture synchronization change only, with no
  product source delta, no public interface change, no dependency change and no
  new behavior. `release_action: defer`, `release_channel: none`.

## Commit

One scoped commit on `aether-agents-2/t_78e06a92-diag-444-bounded-python-3.12-checkpoint`
touching only `tests/test_observation_journal_storage.py`. No canonical Objective
Contract, plan or tasks file was modified, copied, staged or committed. No push,
PR, tag, release or remote action was performed.
