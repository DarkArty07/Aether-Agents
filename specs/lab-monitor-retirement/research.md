# Retirement design research

## Upstream method inspected

Refreshed GitHub Spec Kit's default HEAD via `git ls-remote` on 2026-09-28 UTC:
`c00dc0551583428a10a94443c58c6a41e5e0138c`. Read the actual files at that immutable
revision through GitHub's raw contents API (no vendored checkout or local installation).

- [`templates/spec-template.md`](https://github.com/github/spec-kit/blob/c00dc0551583428a10a94443c58c6a41e5e0138c/templates/spec-template.md),
  lines 11–37 and 71–118: independently testable user journeys, explicit edge cases,
  functional requirements and measurable acceptance.
- [`templates/plan-template.md`](https://github.com/github/spec-kit/blob/c00dc0551583428a10a94443c58c6a41e5e0138c/templates/plan-template.md),
  lines 13–43, 47–64 and 106–110: concrete technical context/testing and constitution
  checks; separate specification, plan, research and quickstart from later task
  decomposition; remove irrelevant structure rather than manufacture empty artifacts.

Reuse: the two subtraction outcomes have independent package/surface oracles, common
preservation constraints and one integrated acceptance path. The plan fixes the actual
cross-cutting identity/isolation boundaries. No new methodology is needed.

Aether-specific gap/adaptation: the owner requests unattended execution. Morfeo resolves
scope and canonical decisions now; Supervisor owns later task decomposition, independent
review and routine GitHub closeout, rather than recommending another interactive command.
No new entity schema, service, scheduler, test framework or upstream patch is justified.

## Current source evidence

All line references below are inspection coordinates at Aether
`21fa590e850dd29f5672a63fb521766431745628`, not a claim that the proposed deletion ran.

| Question | Inspected source | Consequence |
| --- | --- | --- |
| What ships? | `pyproject.toml:28-33,44-74,119-124`; `lab/README.md:1-51`; `lab/__init__.py` lives under `src/aether_agents/lab/`. | Remove the two feature packages/resources and Lab mappings, not only root folders. |
| Shared consumer? | `tests/test_knowledge_session_binding.py:300-345`; `src/aether_agents/lab/isolation.py:49-62,81-150`. | Retain only its environment-builder closure as test support. |
| Where are Monitor calls exposed? | `src/aether_agents/cli.py:74-76,996-999`; `src/aether_agents/resources/profiles/morfeo/config.yaml:7-26`; `scripts/release_bundle.py:49-54`. | Remove callable/default surfaces and their exact expectations together. |
| What would naive deletion break? | `src/aether_agents/lifecycle.py:115-144,6727-6743,6800-6834,6963-7080`; `validate_release:6340-6407`. | Current and historical artifact plugin maps must remain exact; use authenticated actual maps for fingerprints. |
| Are private defaults safe to overwrite? | `src/aether_agents/lifecycle.py:4884-4901`. | No: operator config is preserved. Source retirement must not add a broad migration or edit live state. |
| Shared assertions? | `tests/test_authorized_cleanup.py:1-28`; `test_documentation.py:403-510`; `test_observation_packaging.py:77-111,293-356`; `test_public_artifacts.py:210`. | Update mixed tests selectively; keep non-Lab/Monitor assertions. |
| Verification policy? | `CONTRIBUTING.md:48-77,90-150,167-217`; `.github/workflows/policy.yml:162-171,293-346,386-403,428-459,500-502,592-598`. | Existing exact-Hermes/bootstrap and required checks, with literal inventory reconciliation only. |
| Historical decision conflict? | `DESIGN.md:399-400`; A1 `A1-FR-092/093`; R11 `FR-1104a/1142/1143`, `SC-1116`; `specs/telegram-monitor/spec.md`. | Owner withdrawal belongs in these canonical owners; retiring tooling does not retroactively pass or waive reliability. |

Tracked-source inventory found no production consumer outside the Lab package. The
first inspection found `tests/test_knowledge_session_binding.py`, but **missed** a
second, non-Lab test consumer: the KG-19 E01 knowledge fixture under
`specs/005-project-knowledge-graphify/fixtures/`. U1 found both Lab imports during
execution; the [technical plan](plan.md#21-minimal-isolation-support) and
[`evidence/u1.md`](evidence/u1.md) record the bounded test-only migration and eight
deterministic passes. Lab-only and Monitor-only tests and mixed package/documentation
checks were the other dependency edges. This corrects the original inventory, not the
historical inspection revision or the KG-19 behavioral verdict.

The local observations dated 2026-09-25 supplied hypotheses and historical analysis,
not requirements. The owner's current instruction supersedes their proposal to retain
periodic Telegram reporting. Live read-only Monitor status during intake showed disabled
state and its owned native job paused; no reactivation or delivery was performed. These
are installation-local observations, not a distributed-product guarantee. #367 and its
postmortem [#407](https://github.com/DarkArty07/Aether-Agents/issues/407) are closed prior
work, so retirement has its own issue #546 rather than reopening rejected acceptance.

Project knowledge at the exact inspected revision reported `INDEX_MISSING`; source
inspection was the explicit fallback. No semantic provider or indexing campaign was
invoked to make design available.

## Exploratory findings transferred before retiring local observations

The two local `.aether/observations/` notes dated 2026-09-25 were exploratory,
not implementation authority. Their useful historical findings are retained here and
in the owner decision, not promoted into new acceptance criteria:

- The Monitor analysis counted **38,267 physical lines** across production/resources,
  dedicated qualification scripts/tests and specifications/documentation at historical
  source revision `eeaa24025697ff1b1dbb0ab21e65ffb07f03de5f` (comments and blank
  lines included; not a maintained size target). A read-only collector probe then
  observed zero items and 14 labeled binding/identity gaps. Zero items alone cannot
  establish a defect without reportable work at that instant. The separate natural
  production run did report zero items despite reportable work, and the owner rejected
  acceptance; [postmortem #407](https://github.com/DarkArty07/Aether-Agents/issues/407)
  preserves that attribution and stop decision. Do not infer present-day behavior
  or a need to rebuild the Monitor from those historical probes.
- The Lab exploration did not establish an exact last-use date or prove zero utility.
  The owner chose subtraction based on actual perceived use versus maintenance burden.
  Some test isolation was independently useful, including the later-discovered KG-19
  fixture, and was retained as **unshipped** test support. Deleting the Lab did not
  pass PD-74; its reliability evidence remains an outstanding separate question.
- The earlier proposed thin Telegram notifier was superseded by the owner's explicit
  choice of **no replacement**. Native Hermes cron and ordinary Telegram interaction
  survive; the old installed Monitor remains outside this source-only objective.

## Verified outcome and reusable engineering lessons

The reviewed source retirement [PR #547](https://github.com/DarkArty07/Aether-Agents/pull/547)
and bounded automatic Pages map correction
[PR #548](https://github.com/DarkArty07/Aether-Agents/pull/548) reached final `main`
`d5bed9a8f30c5d5e2289630c4eac1c6585b42c48`. Criterion-level evidence and
its limits are in [`evidence/integration.md`](evidence/integration.md) and Morfeo's
post-merge [`evidence/reception.md`](evidence/reception.md). Lessons are bounded:

- Retire public plugin/CLI surfaces **and** their package identities, docs and tests.
  New candidate artifacts emit three exact plugins; historical four-plugin artifacts
  remain a closed, authenticated read case, not a reason to keep Monitor code or to
  assume an old manager can adopt a new wheel.
- A deleted documentation guide can leave the website's static descriptions map
  stale. Python documentation checks and green PR policy did not detect that edge;
  the automatic Pages run after #547 failed, then #548 fixed that one key and its
  exact-head policy/Pages checks passed. An automatic deployment must be accounted for
  at its own effect boundary; this does not authorize a manual deploy.
- Two combined `pytest-cov` runs failed with mixed statement/branch shards and
  instrumented timing failures. The existing CI split exercised tests, performance
  and unchanged 78% coverage separately, measuring 80% on #547. Those earlier
  failures remain failures, not a retroactive pass or a new generic CI rule.
- A PR cannot truthfully contain evidence of its own later merge and cleanup. The
  reviewed candidate carried pre-merge evidence; Supervisor's final post-merge
  receipt was attached to its terminal task, and Morfeo's exact-revision reception
  was authored afterward. Distinguish these from facts that were already in the PR.
- `VERSION=1.0.0rc17` remains in newer unreleased source, while the RC17 tag and
  selected installation identify earlier bytes. Version text and a merged branch
  cannot establish new RC preparation, installed adoption or PD-74 qualification.

## Alternatives rejected

- Merely pause Monitor or hide Lab exports: retains the maintenance burden the owner
  explicitly wants removed.
- Replace Monitor with an `aether_observe` cron notifier now: explicitly excluded by the
  current owner instruction.
- Delete shared tests/helpers wholesale: violates preservation of other functionality.
- Copy the whole Lab to `tests/`: renames the rejected subsystem instead of removing it.
- Generalize plugin lifecycle or release orchestration: exceeds the subtraction scope;
  two closed exact sets are sufficient for the evidenced compatibility edge.
- Qualify a new RC or live adoption in this contract: separate effect authority and
  concrete old-reader constraints; source closure is independently acceptable.

## Design self-check

Morfeo's self-check maps RET-01–RET-07 to the plan's scenarios and quickstart, separates
current from historical artifact semantics, names the minimal test helper interface,
resolves the existing test standard, and leaves equivalent local implementation choices
to workers. Neither contract schema validity nor this self-check is independent review.
Supervisor must inspect receipt sufficiency and produce its own decomposition/evidence.
