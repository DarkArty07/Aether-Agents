# LG-INT Integration Evidence — Aether 1.0.0rc4

**Unit:** LG-INT (task `t_a155e30d`, Supervisor-owned integration lane)
**Objective Contract:** `oc_ff82ba151cdf3861@v2`
(SHA-256 `e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`)
**Integration base:** `00715d237d795e365c5e462b6b80d5a1bd8d8188`
**Integration branch:** `aether-agents-2/t_cb240071-execute-v2-launcher-and-graphify-reliabi`
**Consumed breakdown:** `specs/001-aether-v1-productization/tasks-rc4.md` at `155c67ea17704fb468e4ebf523145770bc7e4ee4`
**Status of this record:** pre-publication facts. Merge SHA, local tag and
`aether update --local` preview are recorded after those steps exist.

No secrets, credentials, provider/model/router bindings, operator homes, live
runtime identifiers or board/card identities belong in portable artifacts beyond
the task ids already used as execution routing in this objective.

## 1. Independently reviewed units

| Unit | Card | Review outcome | Reviewed tip |
| --- | --- | --- | --- |
| Decomposition root | `t_cb240071` | completed | `155c67ea` |
| LG-CLI | `t_7fab49b1` | approved (round 2) | `d9f801573e8a496f69714431296b784c3b86ac82` |
| LG-LIFE | `t_3c6f6528` | approved (round 4) | `711b1962e3c051dd9a9f3d9147f80f48bbfe8bc1` |
| LG-KNOW | `t_8b46a2e8` | approved (round 2) | `160abe6c4b1fc6e5adb2db084447602b2417ce20` |
| LG-DOCS | `t_555db066` | approved (round 1) | `28531690d9b2caf691b29003f0436a38f74fafb8` |

LG-DOCS already merged the three behavior units as ordinary merge commits
(`2488572e`, `a4f06b1e`, `91707962`) without squash. Each reviewed tip is an
ancestor of that history.

## 2. Integration history (no rewrite)

On the Supervisor flow branch:

- `005a48401e233aa536e4684a7a487b880d35b7e3` — merge of reviewed LG-DOCS `28531690`
  (preserves LG-CLI / LG-LIFE / LG-KNOW commits and their merge commits)
- `9442740ec983eeab7cfbfc39ca2de99776032a84` — bounded integration repair: disposable
  project binding for the current-tree rc4 prepare/activate fixture

Ancestors of HEAD: `d9f80157`, `711b1962`, `160abe6c`, `28531690`, `155c67ea`,
`00715d23`. `origin/main` (`6431d586`) is already an ancestor. No squash, amend,
rebase or history rewrite.

## 3. Bounded integration repair

`9442740e` only. Cause: LG-LIFE branded one-click projections plus LG-DOCS
`VERSION=1.0.0rc4` made
`tests/test_observation_lifecycle.py::test_prepare_release_installs_one_wheel_in_manager_and_exact_runtime`
fail with `IntegrityError: branded one-click projections require an exact project
binding` because that fixture builds the current tree and activates it with no
registry/marker. Repair: same disposable `project_root` + `ProjectRegistry` pattern
already used by LG-LIFE tests. No production behavior change.

## 4. Local gates on `9442740e`

- `uv run --frozen ruff check src/aether_agents tests scripts` 0
- `uv run --frozen ruff format --check src/aether_agents tests scripts` 0 (173 files)
- `uv run --frozen mypy src/aether_agents` 0 (68 files)
- `uv run --frozen python scripts/check_documentation.py` 0
- `uv run --frozen python scripts/check_public_artifacts.py` 0
- `uv build` → `aether_agents-1.0.0rc4` wheel + sdist; wheel contains
  `aether_agents/launcher.py`, no `scripts/aether_tui.py`
- `git diff --check origin/main...HEAD` 0
- policy.yml expected list set-equals `git ls-files` non-`specs/` (426=426)
- VERSION `1.0.0rc4`; contract SHA-256 unchanged
- Focused exact-Hermes: 162 passed / 30 skipped (launcher, TUI, lifecycle,
  release-bundle, public-artifacts, knowledge)
- Isolated re-run of the prior full-suite lastfailed set: 6 passed (the rc4
  binding node plus five observation-performance / telegram-monitor load flakes)
- Full exact-Hermes on `005a4840` before the fixture repair: 6 failed / 1835 passed /
  70 skipped; after repair, a second full run was 4 failed / 1837 passed / 70 skipped
  with lastfailed equal to the same performance/telegram nodes, which then passed
  isolated. Coverage combine INTERNALERROR was leftover mixed statement/branch
  `.coverage*` residue, not a product failure. Official coverage floor is the
  GitHub `observation-qualification` job.

## 5. Publication (filled after PR/merge)

- PR:
- Required checks:
- Merge commit:
- Merge tree equals reviewed HEAD tree:
- Local annotated tag `v1.0.0-rc.4`:
- Remote rc4 tag: must remain absent
- Non-mutating `aether update --local` preview:

## 6. Remaining for LG-CLOSE

Live activation, doctor/service/TUI integrity, fresh/continue canaries, bounded
semantic receipt, #480/#481/#482 close, residue cleanup. No public tag, GitHub
Release, PyPI or stable/WSL2 claim. Aggregate release conclusions belong only to
LG-CLOSE (`patch` / `prepare` / `prerelease` per the contract).
