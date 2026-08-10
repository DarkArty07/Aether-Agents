# v0.22.0 Swarm Measurement Contract

> **Status:** ACCEPTED AND FROZEN M0 MEASUREMENT CONTRACT; NOT IMPLEMENTED
> **Date:** 2026-08-06
> **Owner:** Christopher (DarkArty07)
> **Authority:** ADR-0001 and `docs/architecture/AETHER_MCP.md`
> **Implementation authorization:** M1.1 repository qualification only

## 1. Purpose

The Aether MCP and Orca-backed swarm add complexity. Their trace exists primarily
to explain behavior, compare strategies and produce trustworthy learning data
for prompt/policy/skill/routing improvement and future fine-tuning. Audit and
incident reconstruction are secondary benefits.

That complexity is accepted only when controlled, replayable use cases
demonstrate better software outcomes or lower supervision burden than a simpler
baseline. Recording an episode is not evidence that the system improved.

This document freezes the shape of measurable cases before implementation. The
concrete cases reserved for the final design step are now specified in
`USE_CASE_CATALOG.md`; no fixture, evaluator, MCP, or runtime has been built.

## 2. Evaluation unit

One evaluation unit is:

```text
versioned use case
+ frozen initial state
+ frozen product contract
+ one variant
+ exact model/tool/runtime environment
+ executed artifacts/evidence
+ Aether semantic trace and sealed learning episode
+ versioned labels and dataset-lineage disposition
+ evaluator verdict
+ user disposition where required
```

A Run that lacks its immutable use-case/variant binding cannot count as
comparative product evidence.

## 3. Required use-case specification

Every future use case must define:

```yaml
use_case_id: UC-XXX
version: 1
title: concise product-level name
hypothesis: falsifiable expected improvement
project_class: representative software-project class
input_contract: exact user prompt and supplied artifacts
initial_state: repository/environment/credentials-free fixture identity
variants:
  - direct_baseline
  - swarm_candidate
models_and_routes: exact and equivalent where comparison requires it
participant_policy: required/allowed/disabled/forbidden snapshot
expected_topology: direct or bounded Task DAG
acceptance_criteria: observable criteria with IDs
fault_cases: deterministic failures to exercise
metrics: metric IDs and authoritative sources
thresholds: pass/fail/non-inferiority rules
evaluator: independent deterministic/human authority
stop_condition: exact end of the case
cleanup_contract: resources that must reach known disposition
privacy_classification: allowed and forbidden captured data
capture_policy: DISABLED, STRUCTURED_ONLY, or FULL_EPISODE
learning_purpose: evaluation, SFT, preference, tool-policy, repair, or routing eligibility
```

## 4. Baselines and variants

At minimum, comparative cases should distinguish:

- **Direct baseline:** Hermes or the selected strong general-agent baseline solves
  the same contract without the Aether swarm.
- **Swarm candidate:** Hermes uses the Aether MCP and admitted Orca workers under
  the frozen architecture.

Equivalent conditions require:

- the same product prompt and supplied artifacts;
- equivalent initial repository/environment state;
- declared model and route differences;
- the same acceptance criteria frozen before execution;
- an evaluator and thresholds that the candidate cannot change;
- no retroactive requirement rewrite;
- failed, blocked, unknown, and corrected attempts retained in evidence.

A case may be non-comparative when it targets lifecycle, isolation, recovery,
privacy, or cleanup invariants. Its hypothesis and threshold must still be
frozen beforehand.

## 5. Metric vector

No single score determines success. The minimum vector is:

### Product and quality

- scope fidelity;
- acceptance-criterion coverage;
- functional correctness;
- user-visible coherence/UX where applicable;
- regression count and severity;
- defect escape after candidate review;
- user corrections and rework;
- final acceptance, rejection, redirection, or accepted limitation.

### Time and coordination

- time to first useful result;
- total elapsed time;
- worker active time and actual overlap;
- Hermes supervision time where measurable;
- Task/Dispatch/attempt count;
- messages, questions, waits, and user interruptions;
- retries, cancellations, blocked and unknown outcomes;
- correction cycles.

### Resources and economics

- model/provider route by participant;
- input/output/cache/reasoning tokens when authoritatively reported;
- reported or list-price estimated cost with coverage and source;
- tool and MCP call counts;
- runtime/process/resource footprint where relevant.

### Reliability and trust

- identity/scope/policy violations;
- stale or duplicate attempt events;
- provider/MCP schema drift events;
- evidence completeness and unknowns;
- restart/recovery correctness;
- cleanup duration;
- surviving/unknown resources;
- trace integrity and privacy violations.

### Learning-data quality

- exactness/coverage of model-visible context, messages and tool exchanges;
- explicit capture gaps and unavailable provider metadata;
- secret-redaction and sensitivity-classification findings;
- user-correction and accepted-target coverage;
- outcome/quality labels by authority class;
- sealed, quarantined, eligible and rejected episode counts;
- dataset yield by purpose rather than raw event volume;
- project/task lineage and train/development/test split isolation;
- benchmark contamination, duplicate and license/consent findings;
- revocation/deletion/export lineage completeness.

Fewer calls, agents, tokens, or minutes are not automatically better when quality
or scope fidelity regresses. More tests or specialists are not automatically
better when they add no outcome value.

## 6. Metric authority

| Metric family | Authoritative source | Honest fallback |
|---|---|---|
| Contract and user decisions | Aether semantic trace plus versioned contract | unknown if not explicitly recorded |
| Run/Task/Dispatch lifecycle | Orca structured state/events | unknown; never infer from terminal prose |
| Artifacts and commits | Git/filesystem digests | unknown if artifact unavailable |
| Tests/builds/E2E | Executed evidence receipts | insufficient/unknown, not pass |
| Time | MCP server and provider timestamps with source | partial coverage |
| Tokens/cost | Provider/runtime canonical usage facts | unknown; estimate labelled with coverage |
| Messages/operations | Orca receipts plus Aether operation trace | partial coverage declared |
| Defects/acceptance | Evaluator findings and explicit user/Hermes decisions | not evaluated |
| Cleanup | Fresh resource inventory and Orca state | blocked/unknown |
| Model-visible context/messages/tool trajectory | Protected sealed learning episode with exactness/redaction class | partial/missing; summaries are not equivalent |
| Corrections/preferences | Explicit user decision or authorized comparison label plus source turn | observational/unknown; never infer preference from closure alone |
| Dataset membership/splits | Immutable dataset manifest and source lineage | ineligible/unknown |
| Training eligibility | Consent, quality, contamination and independent/owner label set | not eligible; model/worker self-report is insufficient |

## 7. Trace binding

Every evaluation mutation includes:

- `use_case_id` and version;
- variant;
- environment and initial-state digests;
- contract generation;
- operation ID;
- reason and authority reference;
- Orca build/catalog identity;
- artifact/evidence references.
- capture-policy generation and learning purpose;
- episode/content references and exactness/coverage.

The closeout bundle includes:

- trace sequence range and integrity root;
- exact candidate and environment identity;
- metric values with source and coverage;
- criteria-to-evidence mapping;
- all failures, retries, corrections, and unknowns;
- resource disposition;
- evaluator and user disposition.
- sealed episode/content root, capture gaps, redactions and quarantine state;
- label authorities and learning-eligibility disposition;
- dataset/export/revocation lineage when applicable.

## 8. Learning episode and dataset contract

`FULL_EPISODE` evaluation preserves the exact secret-redacted content visible to
participants, including system/profile/skill/context components, user and worker
messages, assistant responses, MCP/tool calls/results, handoffs, corrections,
artifact diffs/references and final outcomes. Hidden chain-of-thought is neither
required nor captured.

Each episode is sealed before curation. A dataset candidate freezes:

- purpose and eligibility rules;
- source episodes, turns and labels;
- redaction, sensitivity and consent policy;
- transform/deduplication version;
- project/task/use-case-lineage split policy;
- benchmark-contamination exclusions;
- content and manifest roots;
- known gaps and limitations.

Evaluation-only episodes and sibling retries cannot leak into training splits.
SFT targets require explicit quality selection. Preference examples require an
explicit user correction or authorized controlled comparison; a Run completing
does not make every assistant response preferred. Dataset export remains local
and cannot start training, upload data or change a deployed model.

The schema is `../../reference/AETHER_LEARNING_EPISODE_SCHEMA.md`.

## 9. Case families covered by the final design

The final catalog covers distinct equivalence classes rather than many
near-duplicate demos:

- lifecycle/isolation/rollback without a worker;
- one bounded worker and one deterministic artifact;
- two independent workers with real overlap;
- dependency handoff and bounded peer communication;
- failed attempt, fencing, retry, and stale-message rejection;
- runtime/MCP restart and recovery without duplicate authority;
- integrated user-facing software increment;
- independent verification value;
- privacy and cleanup negative cases;
- direct-versus-swarm product-quality comparison.
- full episode capture/replay and secret redaction;
- label authority, curation, split isolation and contamination;
- local export plus blocked upload/training/promotion.

The final catalog selects and concretizes these families in
`USE_CASE_CATALOG.md`.

## 10. Acceptance classes

Each case ends in one of:

```text
PASS
FAIL
BLOCKED
INSUFFICIENT_EVIDENCE
UNKNOWN
```

`PASS` requires every required threshold. `BLOCKED`, `INSUFFICIENT_EVIDENCE`,
and `UNKNOWN` are not zero or partial passes.

The release aggregate must define whether every case is mandatory, a
non-inferiority gate, an improvement gate, or diagnostic-only before execution.

## 11. Anti-bias and learning-contamination rules

- Freeze prompts, criteria, metrics, thresholds, and evaluator before execution.
- Do not let the candidate modify its benchmark or acceptance artifacts.
- Preserve failed runs and user corrections.
- Use the same model and equivalent conditions for causal comparisons unless the
  explicit hypothesis is model routing.
- Do not discard coordination overhead from swarm totals.
- Do not score worker prose as evidence.
- Do not infer missing token/cost/identity facts.
- Do not rewrite scope after seeing the result.
- Separate product quality, operational reliability, cost, and latency.
- Split by project/task/use-case lineage, never random turns from one episode.
- Keep frozen evaluation prompts, expected outputs, judge artifacts and
  evaluation-only episodes out of training datasets.
- Preserve rejected/corrected attempts; do not curate only successful prose.
- Do not let a worker/candidate model label itself as accepted or eligible.
- Treat synthetic preferences as synthetic, not as user feedback.
- Version every transformation so a dataset candidate is reproducible.
- Do not upload, train or promote from captured data without separate authority.

## 12. Current gate

The proposed final catalog now defines conformance, learning-data,
controlled-architecture and product-topology cases; baseline forms; task/fixture
specifications; metrics; thresholds; evaluator authority; gate mapping; and
evidence/cleanup/episode bundles.

Before implementation, Christopher must accept or revise:

1. the case set and hard gates;
2. comparative thresholds and repetition count;
3. evaluator authority and ambiguity handling;
4. intended product model routes;
5. which cases block v0.22.0 Release.
6. rich-episode capture, labeling, retention, lineage and export policy.

Exact fixture bytes, evaluator implementation, prompts, and initial-state digests
will be frozen as benchmark artifacts only after separate implementation
authorization and before the first evaluation. The candidate cannot modify them.
