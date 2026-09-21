# Execution breakdown: Hermes-owned gateway service and rc5

**Status:** verified executable decomposition for Objective Contract
`oc_a7a3cff05e82c148@v1`. This is the Supervisor-owned execution breakdown; it does
not widen the contract, redefine the material design in the contract, `spec.md`,
`plan.md` or `research.md`, or record acceptance. Card and board identities stay on
the execution board.

**Derived by:** Supervisor (root task `t_6529b562`, flow
`aether.flow.v1:91afb86c3355dd72fd94afbfdb284cbaed2356903c2c624ae78596a59c988954`).

**Source contract:** `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md`
(SHA-256 `ad216e2a71737fb0f324f8f3c3b2391473e0c8e7aa41077dfe1ce70ba241a588`) on base
`e1c5f9a49d0513b1903c52368b29c4dd39033fdc`.

**Owning issues:** [#487](https://github.com/DarkArty07/Aether-Agents/issues/487)
(owner-selected option B), with the prior incomplete closeout issues
[#480](https://github.com/DarkArty07/Aether-Agents/issues/480),
[#481](https://github.com/DarkArty07/Aether-Agents/issues/481),
[#482](https://github.com/DarkArty07/Aether-Agents/issues/482),
[#485](https://github.com/DarkArty07/Aether-Agents/issues/485). Issue
[#261](https://github.com/DarkArty07/Aether-Agents/issues/261) stays open for the
stable/PyPI/platform gates.

**Predecessor breakdowns** (`tasks.md`, `tasks-rc2.md`, `tasks-rc3.md`,
`tasks-rc4.md`, `tasks-rc4-restore.md`, `specs/005-project-knowledge-graphify/tasks.md`)
remain historical evidence and are not reopened.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `ad216e2a71737fb0f324f8f3c3b2391473e0c8e7aa41077dfe1ce70ba241a588`; `status: final`, `version: 1`, `change_reason: null` |
| Base / branch | Board `worktree_base_ref` = HEAD = `e1c5f9a49d0513b1903c52368b29c4dd39033fdc` ("docs: authorize Hermes-owned gateway service boundary"). Child worktrees start from that exact base |
| Base vs remote | `origin/main` is still `9ab891241d5be863d796b3ef062ffde8286c5870`; the contract commit `e1c5f9a4` is **local-only** and must be carried by this objective's PR, together with `tasks-rc5.md` |
| Bound knowledge | `project_knowledge` `status` returns the same project id; `available: false`, empty coverage at `e1c5f9a4` (`INDEX_MISSING`). Source inspection used; AC-8's structural refresh is closeout work |
| Maintained fork | `DarkArty07/aether-hermes` `aether-main` `aed6591a69f453a1867b73628603e7b53ba40ffc`, source-tree digest `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` (active release lock). The local research checkout `<local aether-hermes checkout, outside this repository>` is at a divergent `aether-main` tip `54eeb56d…`; inspect the **pinned** revision with `git show aed6591a…:<path>` and never treat the checkout tip as the deployed source |
| Live install | Active release `1.0.0rc4-9316cbddfee2b795` (`active.json` `version` `1.0.0rc4`, wheel SHA `9316cbdd…`); `runtime/current` → that release; retained `1.0.0rc3-8987f650c027ad09` is the rollback qualification target; no `hermes-gateway-morfeo.service.d` drop-in exists |
| Live unit state | `~/.config/systemd/user/hermes-gateway-morfeo.service` is already a **Hermes-generated** unit: `Description=Hermes Agent Gateway…`, `ExecStart=<XDG_DATA_HOME>/aether/runtime/current/venv/bin/python -m hermes_cli.main --profile morfeo gateway run`, `WorkingDirectory=<XDG_STATE_HOME>/aether/hermes/profiles/morfeo`, `Environment="VIRTUAL_ENV=…/runtime/current/venv"`, `Environment="HERMES_HOME=…/profiles/morfeo"`, WSL interop PATH entries, **no** `HERMES_TUI_DIR`. This is the observed ownership drift the contract resolves: rc4's doctor demands the Aether-owned TUI selector line that the gateway's own refresh removes |
| Pinned Hermes surface | At `aed6591a…`: `get_service_name()` derives `hermes-gateway-morfeo` from `HERMES_HOME=<root>/profiles/morfeo`; `generate_systemd_unit()` emits the selected `runtime/current` Python, profile `--profile morfeo`, `WorkingDirectory` = resolved `HERMES_HOME`, `VIRTUAL_ENV` and `HERMES_HOME`; `systemd_unit_is_current`/`refresh_systemd_unit_if_needed`/`systemd_install`/`systemd_uninstall` own write/rewrite/removal; `gateway install` exposes `--force`, `--no-start-now`, `--start-on-login` |
| Baseline gates | `uv run --frozen` provisions a per-worktree `.venv` from the warm uv cache; `pytest -q tests/test_tui_projections.py tests/test_lifecycle_projections.py tests/test_projection_transition_runner.py` = **58 passed** at base. `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` **fails at base**: `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md` is absent from `.github/workflows/policy.yml` |
| Exact-Hermes lane | `scripts/run_tests.py` materializes the authenticated exact baseline checkout at `~/.cache/aether-agents/hermes/v2026.8.18` (`e624e9fde561e1add9388384012b295fde669ade`); its `hermes_cli/gateway.py` carries the same generator/refresh functions, so a real generator integration is available offline |
| Interfaces to consume | `src/aether_agents/lifecycle.py` `{ProjectionRoots, ProjectionSpec, projection_spec, project_release, projection_status, _service_unit_selects_release, ServiceController, SystemdUserController, DisabledServiceController, doctor, rollback, uninstall}`; `src/aether_agents/launcher.py`; `src/aether_agents/cli.py` (`doctor`/`update [version]`/`rollback [version]`/`uninstall`) |
| Profiles | `implementer`, `supervisor`, `morfeo` exist; no extra role, profile or limit is introduced |
| Preserved residue | Owner primary checkout `<owner Aether checkout>` is clean at `e1c5f9a4`; retained `$XDG_STATE_HOME/aether/rc3-preflight`, `rc4-bootstrap*`, `recovery`, `diagnostics`, `hermes-preseed-partial-*` and the retained rc3 source quarantine stay untouched; unrelated units (`hermes-gateway-hestia`, `aether-router*`, `prometeo-*`) are never touched |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Ownership, not a workaround | Owner selected option B: Hermes owns the whole main unit and may rewrite it; `HERMES_TUI_DIR` is a launcher invariant only. A drop-in, a runtime-only unit edit or a periodic re-projection loop are explicitly out of scope | The Aether-side change is projection/doctor/transition ownership plus the Hermes-CLI seam, not a new generator and not a wrapper unit |
| `lifecycle.py` hotspot | Projections, TUI binding, doctor, transition orchestration, service controller and uninstall live in one 7293-line module | One implementation unit (GW-SERVICE) owns `lifecycle.py` and its projection/doctor test modules; the service probe is never parallelized across cards |
| Legacy records | rc3 is the rollback qualification target and rc4 keeps its historically rejected oracle. Aether must not have to write its own unit bytes to make a legacy release coherent | The active-release service check is semantic (Hermes-owned selector invariants) for every active record; the pre-existing `_service_unit_selects_release` tolerance is the seam. rc4 is never re-activated; an implicit `aether rollback` to rc4 is not the qualification path |
| Hermes CLI seam | Aether invokes the **selected** release's own Hermes through the stable selector: `<store root>/runtime/current/venv/bin/python -m hermes_cli.main --profile morfeo gateway install --force --no-start-now --start-on-login`, `HERMES_HOME` = Morfeo profile home, isolated subprocess environment, non-interactive. Then only that unit is daemon-reloaded/restarted through the existing `ServiceController` | Deterministic tests need an injectable seam and a faithful/real generator; an equivalent supported command shape is Implementer freedom only if the semantics are preserved and directly tested |
| Unit-name coupling | Hermes derives `hermes-gateway-morfeo` from the Morfeo `HERMES_HOME` suffix; the Aether projection constant `AETHER_GATEWAY_UNIT` names the same unit | Tests must prove the name agreement instead of assuming it, and must never write to the operator's real unit path |
| Launcher/TUI preservation | The launcher, Desktop entry and WSL actions already deliver the release TUI; the gateway must not depend on that variable | TUI-PRESERVE owns the launcher-side preservation tests; GW-SERVICE owns the gateway-side independence and doctor semantics. The two units share no writable file |
| `policy.yml` hotspot | The heredoc must list every tracked non-`specs/` file and already omits this contract path | Only DOCS edits `.github/workflows/policy.yml`, and only after the behavior units are independently reviewed |
| Identity oracles | `VERSION`, `README.md`, `docs/index.md`, `CHANGELOG.md`, `AGENTS.md`, `docs/capabilities.toml`, `tests/test_public_artifacts.py`, `tests/test_release_bundle.py`, `tests/fixtures/observation/complete-summary.json` and the branding checks inside `lifecycle.py` are one coupled rc5 identity move | GW-SERVICE generalizes the in-code branding boundary; DOCS moves the public identity and its coupled oracles once the behavior units are frozen |
| Live cutover kills the worker | Activation rewrites the selector and restarts `hermes-gateway-morfeo.service`, which owns the dispatcher and this flow's own session | Only the terminal CLOSE card mutates live state, from a durable transient user unit that is **not** a child of that gateway; all durable evidence precedes it |
| Publication | Implementers never push, PR, merge, tag, activate or mutate issues | INT and CLOSE own every remote and live effect |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| In-scope 1, 2; AC-1, AC-2, AC-3, AC-4; testing-standard service/doctor/transition fixtures | **GW-SERVICE** (Implementer, root-gated) | Hermes-owned gateway boundary in `lifecycle.py`: rc5-and-newer projections carry no Aether-owned unit bytes, the transition refreshes the unit through the selected release's Hermes CLI before restart, the doctor validates the Hermes-owned unit semantically and attributes every invalid class, transition failure restores selector/files/opaque prior unit, and uninstall requests removal through Hermes; deterministic fixtures cover fresh absence, exact generated unit, repeated refresh mutation, incidental differences, each invalid selector class, refresh failure, rc4→rc5, rc3 rollback/forward rc5 and uninstall |
| In-scope 3; AC-5 (launcher/Desktop/WSL half), AC-1 (launcher half) | **TUI-PRESERVE** (Implementer, root-gated) | Preservation tests proving the packaged launcher, Desktop entry and WSL actions deliver the hash-bound release TUI with the exact project/profile binding for fresh and `--resume latest` launches, and that a launch performs no npm/build/source mutation; portable and installed-wheel lanes |
| In-scope 4; AC-6 (identity/docs half); AC-1/AC-3 docs half | **DOCS** (Implementer; after independently reviewed GW-SERVICE and TUI-PRESERVE) | `1.0.0rc5` / `1.0.0-rc.5` identity, changelog, README/index/AGENTS authorization paragraph, capabilities registry, lifecycle guide and reference to the Hermes-owned boundary, and `policy.yml` including this contract and every new non-`specs/` path |
| In-scope 5; AC-6 (gates); AC-7 (tag/preview) | **INT** (Supervisor, same flow, `terminal=false`) | Reviewed units integrated in dependency order, `tasks-rc5.md` and the contract commit carried, integrated gates green on the exact candidate, one PR, required checks, green merge without bypass, local annotated `v1.0.0-rc.5` on the exact merge, non-mutating update preview |
| In-scope 6, 7; AC-7, AC-8 | **CLOSE** (Supervisor, same flow, `terminal=true`) | Durable-transient-unit live rc5 activation, doctor/service/launcher/TUI/source-digest witnesses, rc3 rollback and forward rc5 reactivation, Graphify bounded receipt, structural Project Knowledge refresh, issue reconciliation, objective-owned residue cleanup and the three release conclusions |

## Execution graph

```text
t_6529b562 (Supervisor decomposition root)
    ├── GW-SERVICE  (Implementer; base e1c5f9a4)
    └── TUI-PRESERVE (Implementer; base e1c5f9a4)

GW-SERVICE, TUI-PRESERVE
    → same-card Supervisor review on each unit
    → DOCS  (Implementer; after both are independently reviewed)

DOCS → same-card Supervisor review
    → INT   (Supervisor, same flow, terminal=false)
        → CLOSE (Supervisor, same flow, terminal=true)
```

GW-SERVICE and TUI-PRESERVE are independent: `lifecycle.py` and its projection/doctor
test modules versus `launcher.py`, `scripts/aether_tui.py` and the launcher test module.
They share only the read-only interface recorded in Shared decision 6. DOCS is
serialized because the identity move invalidates the oracles the behavior units must
first freeze, and because `policy.yml` is a single-writer manifest. INT and CLOSE are
serialized because integration, publication and live cutover are Supervisor-owned and
the cutover interrupts the Aether-owned gateway.

Same-card Supervisor review is the unit review lane. CLOSE consumes independently
reviewed units and does not replace unit review.

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_a7a3cff05e82c148@v1` (SHA-256
   `ad216e2a71737fb0f324f8f3c3b2391473e0c8e7aa41077dfe1ce70ba241a588`) on base
   `e1c5f9a49d0513b1903c52368b29c4dd39033fdc`, plus this breakdown. Skills are
   reusable procedure only and grant no authority. Never create, edit, stage or
   exact-copy the canonical contract; consume it read-only.
2. Release identity for this objective: package `1.0.0rc5`, display `1.0.0-rc.5`,
   one local annotated tag `v1.0.0-rc.5` on the exact merge, never pushed. Conclusions
   `release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`.
   `v1.0.0-rc.1`…`v1.0.0-rc.4` and `v1.0.0-a.4` are immutable; rc4 is never activated
   again; rc3 stays the rollback qualification target.
3. The Hermes side is pinned and unchanged: fork `aed6591a69f453a1867b73628603e7b53ba40ffc`,
   tree digest `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`,
   `aether-main`. No fork change, no `.patch` replay, no runtime-only unit edit and no
   systemd drop-in.
4. Ownership boundary: for rc5-and-newer releases Aether neither writes nor
   byte-compares `hermes-gateway-morfeo.service` and does not include its bytes in
   projection digests. Fresh setup, update, rollback and forward reactivation refresh
   the unit through the selected release's Hermes CLI before restart; uninstall asks
   Hermes to remove its unit. The prior opaque unit bytes may be snapshotted **only**
   as transactional recovery for a failed transition.
5. Semantic doctor: the unit must be a regular user unit whose single `ExecStart`
   selects the active `runtime/current` Python with `hermes_cli.main --profile morfeo
   gateway run`, with the exact Morfeo `WorkingDirectory`/`HERMES_HOME` and active
   `VIRTUAL_ENV`, no duplicate or conflicting selector lines, plus a separately probed
   available/running service. `HERMES_TUI_DIR` is neither required nor rejected, and
   Hermes-owned incidental `Description`/`PATH`/cleanup/watchdog/timeout differences
   never produce drift. Wrong runtime/profile/home/working directory, conflicting
   selectors, an absent/non-regular unit and an unavailable service stay visible and
   attributed.
6. Launcher/TUI invariants: the packaged launcher keeps exporting
   `HERMES_TUI_DIR=<runtime/current>/tui` to the Hermes process it launches; Desktop and
   WSL actions keep targeting the stable `runtime/current/venv/bin/aether` entry point
   with the exact initialized project root and the hash-bound release TUI. Gateway
   operation must not require that variable, and a launch must not create npm/build or
   `hermes-source` extras.
7. Deterministic isolation: every fixture uses isolated `HOME`/`XDG_CONFIG_HOME`/
   `XDG_DATA_HOME`/`XDG_STATE_HOME` roots and can never read or write the operator's
   live unit, live state root or live XDG destinations; the exact-Hermes lane runs
   through `uv run --frozen python scripts/run_tests.py`. No gate is weakened, no test
   removed or skipped, and the coverage floor is not lowered. A real or faithful
   Hermes generator/refresh integration is required; never infer live behavior from
   source-only tests.
8. Publication boundary: Implementers commit reviewed worktree changes only and never
   push, open/merge a PR, create a tag, activate a release or mutate an issue. INT and
   CLOSE own all remote and live effects.
9. Environment: run `uv run --frozen …` from the unit's own worktree so it provisions
   its private `.venv` from the warm uv cache; never point `UV_PROJECT_ENVIRONMENT` at
   the owner's primary checkout and never write the owner's Aether checkout
   or any live `$XDG_*` destination. Follow `CONTRIBUTING.md` for the canonical
   commands.
10. Remaining-risk honesty: record direct versus reused evidence, any provider or
    external route limit, and any obligation the unit could not exercise. Do not claim
    a fork, platform or stable-release qualification, and do not repair rc4's rejected
    oracle.

## Live-cutover note (CLOSE only)

The activation lane runs from a durable transient **user** unit that is not a child of
`hermes-gateway-morfeo.service`, writes private prestate/receipt markers and does not
poll the doctor while the mutation lock is held. Expected TUI/gateway/worker termination
during an authorized transition is not failure; recovery uses the durable receipts. If
live rc5 fails, use the supported rollback to coherent rc3 once, preserve evidence and
return to source correction instead of editing the live unit or looping transitions.
