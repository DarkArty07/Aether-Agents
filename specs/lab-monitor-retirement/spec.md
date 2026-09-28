# Lab and Telegram Monitor retirement

**Decision authority:** project owner

**Accepted:** 2026-09-28 UTC (2026-09-27 in the owner's local conversation)

**Status:** source retirement reviewed, merged and accepted at
`d5bed9a8f30c5d5e2289630c4eac1c6585b42c48` via PRs #547/#548; no new RC or
installed cutover

**Design steward:** Morfeo

**Objective issue:** [#546](https://github.com/DarkArty07/Aether-Agents/issues/546)

## 1. Owner decision

The owner directs the complete removal of Aether's formal Qualification Lab and
Telegram Monitor, including its periodic Telegram progress reports. Neither subsystem
justifies its maintenance cost for the owner's actual use. This supersedes the earlier
idea of replacing the Monitor with a thinner periodic notifier: **no replacement is part
of this objective**. Hermes's native cron remains available unchanged. All other product
functionality is preserved.

This is subtraction, not a new scheduler, notification service, laboratory, qualification
framework, observability expansion or agent-behavior campaign. The current instruction
authorizes autonomous implementation and normal reviewed source closeout. It does not
authorize a new release, package publication, installed-runtime cutover, credential change,
external Telegram delivery or purge of historical/private state.

## 2. Required end state

- **RET-01 — Formal Lab removed.** Remove `aether_agents.lab`, the `lab/` scenario,
  fixture and schema tree, `scripts/e2e/` compatibility entry points and their resource
  mappings. Remove tests whose sole subject is the retired Lab. Do not preserve the
  subsystem by relocating its runner, matrix, synthetic owner, persistent/affinity lanes,
  evidence schema or public API under another name.
- **RET-02 — Monitor and periodic reports removed.** Remove `aether_agents.monitor`,
  its resources, `aether monitor` command, both native monitor tools/toolsets, plugin
  entry point, default profile opt-in, dedicated qualification scripts and exclusive
  tests. The resulting source/package must not schedule, collect, narrate or deliver
  automatic Aether progress reports. Do not add a replacement cron job or notifier.
- **RET-03 — Retained behavior preserved.** Preserve native Hermes cron and messaging,
  ordinary Telegram interaction and native task/final/input notifications, Contract
  Observation and `aether_observe`, Objective Contracts, project knowledge/work memory,
  MCP, Projects, boards, worktrees, role boundaries, policy edges and lifecycle behavior.
  No Hermes fork/source/pin change, cron implementation change or gateway reconfiguration
  is necessary or authorized.
- **RET-04 — Useful test isolation preserved.** A surviving non-Lab test must not lose
  environment scrubbing or disposable destination containment merely because its helper
  currently lives in the Lab. Retain only the minimal support actually consumed by those
  tests, outside the shipped product, and preserve the corresponding isolation checks.
  Removal of Lab-exclusive tests is deliberate scope reduction, not permission to skip
  failing tests of retained behavior or lower coverage/CI gates.
- **RET-05 — Package/lifecycle coherence.** New wheel and sdist contain neither retired
  implementation nor Lab resources. Plugin manifests, profile resources, installer
  verification and release-bundle expectations agree on the retained three official
  plugins. Preserve release identity, existing supported reader/writer and rollback
  behavior; do not weaken exact candidate verification or modify old releases. Source
  acceptance must identify any old-reader adoption limit rather than claim a cutover.
- **RET-06 — Current guidance reconciled; history preserved.** Reconcile current
  guidance, capability registry/generated reference, operating instructions, applicable
  normative implementation requirements and the literal repository manifest. Retain
  historical specifications, finalized contracts, evidence, failures, postmortem and
  release history with clear supersession notices; do not rewrite prior failure as PASS.
- **RET-07 — Proportionate verified closeout.** Exercise retained affected tests,
  negative package/surface checks and the applicable repository gates. Supervisor owns
  independent review, per-unit reversible integration, normal PR/required checks/merge,
  issue reconciliation and owned temporary/worktree cleanup. Morfeo accepts the result
  against the finalized contract and exact final revision, not board status alone.

## 3. Qualification and preservation boundary

The owner retires the formal Lab as a required product implementation/evidence producer.
This supersedes PD-75 and Lab-specific implementation mandates in A1/R11/004; it does
**not** pass, waive or redesign PD-74's outstanding reliability/release conditions. Those
remain unsatisfied unless independently supported by their own authorized evidence.
Deleting the scorer cannot count as satisfying its threshold. A later release objective
must reconcile its qualification route before relying on the retired tooling; this
retirement does not implement that future route or demand a final Lab campaign.

The source objective and installed state are distinct. Historical monitor receipts,
sessions, credentials, private profile configuration, paused cron records and prior
release sets are not disposable source residue. They remain untouched by this contract.
An already disabled Monitor is not re-enabled for verification. No live report is sent.
A future managed activation is a separate effect requiring its own bounded authority;
source integration alone must never be reported as installed retirement.

## 4. Acceptance

Acceptance uses RET-01 through RET-07, the technical decisions and runnable checks in
[`plan.md`](plan.md), and the finalized Objective Contract. Each result records the exact
revision, command/check, producer, outcome and limitation in this objective's evidence
location. An inventory explains intentional historical references and retained isolation
support, rather than requiring an indiscriminate zero-string match.

The compatible remainder of the product remains subject to its existing specifications.
No performance target, line-count quota, broad cleanup, new native integration or
behavioral qualification claim is added by this retirement.

## 5. Subsequent documentation closeout authority

After source acceptance, the owner requested a bounded documentation consolidation and
retirement of the two resolved local observation notes. On 2026-09-28 UTC the owner
**separately authorized the existing automatic deployment to Aether's GitHub Pages site
caused by a normal green merge of documentation PR #549**. This applies only to that
site and that PR's documented changes. It grants no manual Pages dispatch, deployment
to another target, package publication, new RC, runtime cutover or change to prior
historical/private state. The original retirement's no-deployment boundary remains
accurate for its earlier source work; this later owner instruction resolves the
specific additional effect. Review and required checks still gate the merge, and the
deployment must be observed on the exact merged revision before claiming success.
