# Contract-first TDD QA: worked pattern

Use this reference when a task defines tests and an oracle before a production module exists.

## RED evidence protocol

Run three scopes separately:

```bash
# 1. Oracle/helpers must be green
pytest path/to/test_contract.py::TestReference -q

# 2. Existing behavior must remain green
pytest -q --ignore=path/to/intentional_red_tests

# 3. Production contract must be uniformly red
pytest path/to/test_contract.py::TestProductionContract -q --tb=short
```

Record exact counts. Accept RED only when every production case is collected and all failures share the expected missing-feature cause. A typo, fixture setup error, unrelated exception, skip, xfail, mock, stub, or accidental implementation invalidates the evidence.

## Independent-oracle checklist

- Include at least one hand-derived one-step example proving orientation and operation order.
- Include a fixed multi-step example whose expected state and reads are literal values, not output from the recurrence helper.
- Use deterministic tensors and shared weights when comparing precision paths.
- Compare values and dtypes, not shapes alone.
- Keep oracle helpers outside production imports.

## Coverage matrix template

Fill every applicable cell before independent review:

| Contract invariant | constructor | step/recurrent | chunk/batch |
|---|---|---|---|
| accepted input rank/shape | | | |
| input dtype | | | |
| input device | | | |
| supplied-state batch/shape | | | |
| supplied-state dtype | | | |
| supplied-state device | | | |
| default zero state | | | |
| state non-mutation | | | |
| empty input | | | |
| causality/order | | | |
| chunk equivalence | | | |
| gradients across state boundary | | | |
| informative error type/message | | | |

When a reviewer finds one missing cell, inspect the entire row and all sibling rows for every public entry point before requesting re-review.

## Mixed-precision pattern

Distinguish:

- **observable compute contract:** Q/K/V and output dtype;
- **state contract:** writes, reads, accumulation, and returned state in FP32;
- **storage policy:** parameter weights may remain FP32 masters unless explicitly forbidden.

A storage-neutral expected projection can use:

```python
expected_q = torch.nn.functional.linear(
    x,
    module.q_proj.weight.to(compute_dtype),
    bias=None,
)
```

Build expected state/read with an independent FP32 scan over projected Q/K/V. Assert the returned state is FP32 and output is `compute_dtype`. Exercise both CPU and accelerator where the contract promises both.

## Pytest missing-module classification

Importing the absent module in fixture setup produces `ERROR`. Use a lazy factory so the import occurs during the test call and produces intentional `FAILED` cases:

```python
@pytest.fixture
def Feature():
    def construct(*args, **kwargs):
        from package.feature import Feature as cls
        return cls(*args, **kwargs)
    return construct
```

## Reviewer-cycle discipline

Before each re-review:

1. Translate findings into invariant classes, not literal one-line patches.
2. Re-run the matrix.
3. Verify oracle GREEN, regression GREEN, intentional RED.
4. Verify no production artifacts were created.
5. Run lint/format/diff checks.
6. Give the reviewer the original contract, prior findings, exact correction mapping, and commands already run.

This batching step prevents adjacent omissions from consuming one review cycle each.
