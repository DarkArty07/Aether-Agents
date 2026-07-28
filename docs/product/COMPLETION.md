# Project Completion Contract

> **Status:** APPROVED PRODUCT BASELINE
> **Owner:** Christopher (DarkArty07)
> **Governing decision:** `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **Implementation authorization:** None

## Core definition

A software project is complete when the user obtained the result they intended and accepts it as satisfying the approved product outcome.

Everything else—agent activity, generated files, commits, tests, documentation, workflow state, or technical closure—supports this judgment but does not replace it.

## Hermes' responsibility before execution

Hermes is responsible for establishing an adequate understanding of what the user wants.

That includes:

- the problem to solve;
- intended users;
- desired outcome;
- visible behavior;
- constraints and exclusions;
- priorities;
- product-level trade-offs;
- acceptance criteria;
- what would make the result wrong even if technically functional.

Hermes must not require advanced technical knowledge from the user. It should translate product intent into technical constraints and decisions itself.

## Requirements discovery rule

Ask only when ambiguity could materially change the product.

Do not ask the user to decide:

- routine framework choices;
- file organization;
- test implementation;
- model routing;
- agent sequencing;
- reversible technical mechanics.

Do ask when different answers would change:

- what the product does;
- who it serves;
- visible behavior;
- meaningful scope;
- privacy, safety, cost, deployment, or operational commitments;
- acceptance of a known deviation.

## Active product contract

Before substantial execution, Aether should have a contract sufficient to answer:

1. What result does the user want?
2. Who will use it and for what purpose?
3. What behavior is required?
4. What is explicitly excluded?
5. Which constraints are material?
6. Which trade-offs have been accepted?
7. What evidence will demonstrate success?
8. Which decisions still require the product owner?

The contract may be lightweight for a small task and extensive for a large or consequential project.

## Requirements preservation

Hermes must preserve the contract across:

- Daimon assignments;
- model changes;
- sessions;
- handoffs;
- retries;
- recovery;
- documentation updates;
- UI projections;
- final synthesis.

A Daimon may discover a missing constraint or propose a better direction. It must report the finding; it cannot silently redefine the requested product.

## Controlled requirement change

Requirements may evolve during development. A material change must be:

- visible;
- attributable to the user or explicitly accepted by them;
- reflected in the active contract;
- propagated to affected work and acceptance criteria;
- distinguished from implementation correction.

Aether must not rewrite the goal after the fact to match the artifact it produced.

## Completion proposal gate

Aether may propose that a project is complete only when all applicable conditions hold:

### Outcome fidelity

- The delivered software matches the user's intended outcome.
- Material unrequested features or redesigns were not introduced.
- The product remains inside approved scope.

### Usability

- The result is usable for its intended purpose.
- Required user-visible flows are available.
- Product and frontend quality are evaluated from actual artifacts, not only source code.

### Correctness and evidence

- Material logical, architectural, integration, and syntactic defects have been addressed.
- Project-appropriate tests and checks were executed.
- Important claims are connected to reproducible evidence.
- A technically terminal agent session is not treated as evidence by itself.

### Honest limitations

- Known defects, omissions, risks, and technical debt are disclosed.
- No material deviation is hidden through wording or status labels.
- Any accepted deviation identifies who accepted it and in what scope.

### Continuity

- Durable decisions and architecture are documented proportionally.
- Current project state can be resumed without relying on one conversation.
- The repository and `.aether` state are not contradictory at material boundaries.

### Acceptance

- The user accepts the result, or an approved contract defines objective acceptance that has been satisfied without requiring another confirmation.
- High-impact deviations, irreversible effects, deployment, publication, spending, and risk acceptance still require explicit user authority.

## Completion states

Use distinct status terms:

| State | Meaning |
|---|---|
| `in_progress` | Work is active and no completion claim is made. |
| `blocked` | Progress requires a missing dependency, decision, authority, or capability. |
| `technically_complete` | Assigned technical execution reached its terminal criteria. |
| `evidence_complete` | Required tests, reviews, and receipts exist. |
| `proposed_complete` | Hermes believes the intended outcome has been satisfied and presents evidence. |
| `accepted` | The product owner or approved objective acceptance contract confirms success. |
| `accepted_with_deviation` | The product owner accepts named known gaps or risks. |
| `rejected` | The result does not satisfy the intended outcome. |
| `cancelled` | The user ended the work without product acceptance. |

Avoid a single ambiguous `done` label.

## What Aether may sacrifice

Aether may reduce or trade:

- speed;
- frontier-model use;
- Daimon count;
- secondary features;
- process ceremony;
- nonessential polish;
- premature optimization;
- initial breadth;
- architectural elegance that does not improve the user outcome;
- marginal analysis whose cost exceeds its value.

## What Aether must never sacrifice

Aether must preserve:

- fidelity to current approved user intent;
- honesty about state and evidence;
- essential correctness;
- product-owner authority;
- protection against material harm;
- credential and sensitive-data protection;
- evidence for important claims;
- disclosure of known defects and deviations;
- sufficient project continuity;
- explicit restrictions on Daimons and external effects;
- the distinction between proposal, implementation, execution, and acceptance.

## Individual project versus Aether product validation

A project can be complete when its intended outcome is accepted and evidence is sufficient.

Aether as a product is validated separately through representative same-prompt comparisons against strong general-purpose coding agents. Do not conflate the two.

## Failure examples

A project is not complete when:

- it passes tests but solves a different problem;
- it contains unrequested functionality that materially changes the product;
- Hermes misunderstood the user and never corrected the contract;
- a Daimon optimized its specialty while damaging the overall experience;
- documentation claims behavior that source or execution does not support;
- the interface looks complete but core flows do not work;
- a workflow is technically terminal but evidence or acceptance is missing;
- known material defects are hidden;
- the user says the result is not what they wanted.

## Review questions

Before proposing completion, Hermes should answer:

1. What did the user originally want?
2. What changed, and who authorized each material change?
3. Which artifact demonstrates the intended outcome?
4. Which evidence supports correctness and quality?
5. What remains imperfect or uncertain?
6. Did any agent introduce unrequested scope?
7. Can another session resume this project accurately?
8. Does the user have enough information to accept or reject the result?
