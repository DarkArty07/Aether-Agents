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
retained direct test consumer is the knowledge test; Lab-only and Monitor-only tests and
mixed packaging/documentation checks form the remaining dependency edges. Workers must
revalidate at their exact base, not assume this inspection is a runtime qualification.

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
