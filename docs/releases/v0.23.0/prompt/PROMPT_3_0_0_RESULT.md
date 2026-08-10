# Hermes Prompt 3.0.0 Candidate — Experiment Result

> **Disposition:** NOT PROMOTED
> **Active prompt remains:** 2.0.0 (`d981f4e805caa6dee222093cfcc0073aa8fbc6b2864c22335e104ec20e8be31a`)
> **Final candidate:** 3.0.0 (`54241ae89f986a644dd7f328b84e72fdb7f453f45532b00c5854d0a714fe7444`)
> **Provider/model:** `custom` / `gpt-5.6-sol`
> **Reported monetary cost:** UNKNOWN

## Intended change

Replace obsolete Olympus/Harmonia execution authority with the approved Aether MCP + Orca ownership model; enforce the v0.23.0 roster; make `ORCA_INTEGRATION_INCIDENT` the mandatory route before reconciliation; and distinguish Ictinus architectural judgment from Hefesto implementation ownership.

## Frozen experiments

### V1 — rejected evaluator contract

- Report SHA-256: `20788b58055220b07cb2aa947d878adfcc1ccc6fecffe49aa8ddeddff16a0bc1`
- Baseline: 0/8; candidate: 0/8; valid JSON: 16/16.
- Classification: `evaluator_contract_underspecified`.
- Cause: route enums and participant semantics were not defined in the case prompts. Semantically correct labels such as `aether_mcp_orca` could not match undeclared exact labels such as `AETHER_MCP_ORCA`.
- V1 remains immutable evidence and was not rescored.

### V2 — candidate improved but failed one hard invariant

- Report SHA-256: `de3f9b501abd6a274e672bdfd603ec63466fe45cafa086c43e12fc22b6f33cec`
- Baseline: 6/8, hard 3/4.
- Candidate: 7/8, hard 3/4.
- Candidate improved forbidden-participant enforcement, incident routing and semantic closure.
- Failure: selected Hefesto instead of Ictinus for explicit backend architectural judgment.
- Causal candidate correction: add architecture-versus-implementation routing discriminators.

### V3 — rejected; no further promotion attempts

- Report SHA-256: `fe675af042581929bf537e5df62fbeaf5b11f6bc33b441358ac7a8c13ebe46e1`.
- Baseline: 4/8, hard 1/4.
- Candidate: 5/8, hard 2/4.
- Candidate selected the correct route and denied Athena/Etalides, but failed frozen expected booleans for verification/closure on policy denials; it also differed on `must_verify` for an already verified implementation at a later release gate.
- These differences expose unresolved benchmark semantics and run-to-run variance. They do not satisfy the frozen hard threshold.
- Three rounds were reached. Promotion stops instead of lowering thresholds or continuing to fit the prompt to the benchmark.

## Aggregate observed usage

- 48 one-shot calls.
- 99,030 input tokens.
- 5,492 output tokens.
- All reported monetary-cost fields unavailable: `UNKNOWN`.

## Product conclusion

The 3.0.0 text is a useful candidate and produced several intended routing improvements, but it is not accepted as the active policy. A later experiment must prospectively define:

1. whether a policy denial itself requires additional verification;
2. whether a correctly denied request may close immediately;
3. whether `must_verify` describes already-completed evidence or a future obligation;
4. repeated-run stability thresholds rather than one sample per case;
5. a semantic outcome score separated from exact serialization.

Until that redesign is frozen and passed, `home/SOUL.md` must remain byte-for-byte at active 2.0.0. The candidate may inform v0.23.0 dogfooding and future prompt experiments but cannot self-certify or activate.
