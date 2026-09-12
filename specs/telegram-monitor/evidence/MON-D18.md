# MON-D18 Implementation Evidence — board contract resolution from the validated `worktree_base_ref`

**Unit:** D18 — resolve the execution board's contract from its validated `worktree_base_ref`
**Task:** `t_29621955` (Implementer)
**Objective Contract:** `oc_f8c9fc9320587cf3@v5` (SHA-256 `709aebb5bf01d11f5e9758bcd9f4d5fd664b55fa50f222843fd9ac165e1107d5`)
**Base commit:** `fa164c5a4c7d5080378c28b19d80a74839850c05` (`fa164c5`, materialized worktree base)
**Candidate implementation commit:** `23068a6a5bb7f2af2782b12385514c9382f66e40` (`23068a6`); the review candidate is this commit plus the evidence commit that introduces this file.
**Phase:** Implementer unit; **no live effect performed**. No `--live` run, model call, Telegram send, native job enable/disable, scheduler start, profile/plugin/service/credential change, runtime update, push, PR, merge or issue mutation was performed. The production canary and installation-wide attribution belong to the terminal card `MON-V5-INT`.

## Defect measured on the unchanged base

`src/aether_agents/monitor/sources.py::_contract_metadata` read `.aether/objective-contracts/<contract>/v<version>.md` only from the registered primary checkout (`project.path`). A canonical board whose finalized contract is committed at its validated `worktree_base_ref` but absent from that checkout therefore failed as `FINAL_CONTRACT_UNREADABLE`, producing no `BoardBinding` and no work item. Reproduced first-hand with a real temporary Git repository (contract committed at the base ref, removed from the primary working tree):

| Behavior-bearing check | Base `fa164c5` observation | Candidate `23068a6` observation |
| --- | --- | --- |
| Contract only at the board base ref (`test_board_contract_resolves_from_validated_base_ref_without_primary_artifact`) | **FAIL**: `assert ('FINAL_CONTRACT_UNREADABLE',) == ()`; no binding, no item | **PASS**: one `BoardBinding` (project `11111111-…`, contract `oc_abcdef0123456789` `v1`, origin `origin-1`, finalizer `finalizer-1`) and one attributed item |
| Base-ref bytes win over a valid, differing mutable copy (`test_base_ref_contract_bytes_are_authoritative_over_a_valid_primary_copy`) | **FAIL**: `assert 'Bound fixture objective' == 'Base ref objective'` — the mutable copy was read | **PASS**: the binding carries the base-ref title |
| Present-but-invalid ref with a valid mutable copy (`test_present_but_invalid_base_ref_format_fails_closed_without_primary_fallback`) | **FAIL**: the ref was ignored and a `BoardBinding` was built from the mutable copy | **PASS**: no binding; the ref is authoritative and fails closed |
| Unknown commit, missing blob, marker mismatch, contract identity mismatch, unrelated invalid board, read-only proof | **FAIL** on base (same class: ref ignored, mutable artifact used, or no `BOARD_BASE_REF_UNREADABLE` gap) | **PASS** (see mapping below) |

Command (unchanged base `fa164c5` in a disposable detached checkout, carrying the final test content and the unmodified base `sources.py`): `uv run --frozen python -m pytest -q tests/test_telegram_monitor_sources.py -k base_ref -p no:randomly` → `18 failed, 43 deselected`. Same command in the candidate worktree: `18 passed, 43 deselected`. The complete file passes `61 passed` (default plugin order) on the candidate.

## Bounded implementation

Changed paths: `src/aether_agents/monitor/sources.py`, `tests/test_telegram_monitor_sources.py`. No other module, test, script, doc, workflow, spec or contract artifact was modified; no doc update was required (D18 behavior is already documented in `spec.md` §D18, `plan.md` §4 and `quickstart.md` §5).

- `sources.py:59`: `_BASE_REF_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)` — the stamped lowercase 40-character SHA-1 grammar.
- `sources.py:85,87`: `_GIT_READ_TIMEOUT_SECONDS = 30` (bounded object read) and `_GIT_REPOSITORY_REDIRECTIONS = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}` (an ambient redirection cannot move the read off the registered repository).
- `sources.py:423-437`: `_marker_from_bytes` extracts the existing marker validation unchanged; `_read_marker` keeps reading the primary marker through `read_private_bytes` with the same exception set as before.
- `sources.py:440-447`: `_git_read_environment` sets `GIT_OPTIONAL_LOCKS=0` and `GIT_TERMINAL_PROMPT=0` for a lock-free, prompt-free read.
- `sources.py:450-476`: `_git_object_bytes` runs `git -C <registered repo> show <rev>^{commit}:<path>` as an argument array (no shell, `stdin=DEVNULL`, `stderr=DEVNULL`, bounded timeout). `^{commit}` keeps the revision an exact commit, so a tree/blob object id is rejected rather than read; unknown revisions, missing blobs and invocation failures fail closed as `None`.
- `sources.py:598-636`: `_parse_contract_metadata` carries the pre-existing front-matter parse and finalized-contract validation (`artifact_type`, `status: final`, canonical project UUID, `contract_id`, normalized `version`, title, created/finalized session refs) with the raw bytes as input, so the same single rule set applies to filesystem and Git-object bytes.
- `sources.py:639-654`: `_contract_metadata` keeps the previous primary-filesystem path and behavior unchanged.
- `sources.py:657-690`: `_contract_metadata_from_base_ref` validates the ref grammar, reads `.aether/project.toml` from that exact commit, requires a schema-valid marker whose canonical UUID equals the board's portable project, then reads and validates the contract blob at `.aether/objective-contracts/<contract>/v<version>.md` of the same commit. Every failure returns `None`.
- `sources.py:824-837`: `_read_board_bindings` treats key presence as the switch. `worktree_base_ref` present → base-ref resolution and the new `BOARD_BASE_REF_UNREADABLE` gap on failure; key absent → the previous primary-filesystem resolution and the unchanged `FINAL_CONTRACT_UNREADABLE` gap. Missing refs never fall back to the primary artifact, another board or another commit.

Gap vocabulary: existing codes keep their names and meanings (`FINAL_CONTRACT_UNREADABLE`, `BOARD_IDENTITY_CONFLICT`, `BOARD_CONTRACT_UNBOUND`, …). One new code, `BOARD_BASE_REF_UNREADABLE`, covers a present-but-unusable ref (format, object, blob, marker or identity problem) and is emitted for that board only.

## Acceptance coverage

| Card obligation | Check and observed result | Evidence location |
| --- | --- | --- |
| R1 — ref authoritative; read from that exact commit through a read-only Git object read in the registered repository, argument array, no shell | **PASS**: the recorded Git argv during collection is `git -C <registered project> show <base_ref>^{commit}:<path>`; `stderr`/exit failures are bounded; no checkout/worktree/fetch/gc is issued. Differing-but-valid bytes resolve from the ref, not from a valid mutable copy | `tests/test_telegram_monitor_sources.py:1803-1836`, `src/aether_agents/monitor/sources.py:450-476` |
| R2 — marker UUID and contract identity agree with board metadata and existing validation | **PASS**: reuse of `validate_project_marker`/`_parse_contract_metadata`; positive and mismatch cases below | `src/aether_agents/monitor/sources.py:657-690`, tests `1627-1658`, `1661-1677`, `1715-1765` |
| R3 — no `worktree_base_ref` key keeps today's primary-filesystem path | **PASS**: all pre-existing board tests (legacy metadata without the key) still pass; the branch is key-presence driven | `src/aether_agents/monitor/sources.py:824-837`, full-file `61 passed` |
| R4 — invalid format / unreachable object / missing blob or marker / unreadable / mismatch → labeled gap for that board only, never a fallback | **PASS**: `uppercase`, `truncated`, `abbreviated` format variants; `0`×40 unknown commit; contract only in the mutable worktree; foreign marker UUID at the ref; `status`, `artifact-type`, `contract-id`, `version`, `project-id`, `created-session`, `finalized-session`, `title` mutations | tests `1680-1765` |
| R5 — unrelated invalid boards keep their own gap without erasing a valid binding; SQLite stays `mode=ro`/`query_only`; no Git working tree/index/ref/object change | **PASS**: a stale board (`BOARD_SLUG_C`, invalid ref) contributes `BOARD_BASE_REF_UNREADABLE` while the base-ref board still yields its one item; collection leaves `git status --porcelain`, the ref list and the three source SQLite digests unchanged and does not materialize the contract | tests `1767-1836` |
| R6 — gap codes consistent with the existing vocabulary | **PASS**: no existing code renamed or remeant; one new code for an unreadable base ref | gap assertions in tests `1680-1765`; `sources.py:831,834` |
| R7 — tests in the existing file, real temporary Git repository, no new tracked non-spec file | **PASS**: only `tests/test_telegram_monitor_sources.py` gained tests plus this evidence file under `specs/`; helper reuse (`_fixture`, `_write_project`, `_write_contract`) with additive `exist_ok`/`metadata_overrides` reuse | test diff `1499-1836` |
| R8 — no live external effect | **PASS**: only local pytest/ruff/mypy/compileall/script runs in the worktree; no `--live`, model, Telegram, native job, scheduler, profile/plugin/service, push, PR, merge or issue operation | this record; commit `23068a6` |
| R9 — evidence record with mapping, candidate, commands, controls, risk | **PASS**: this file | `specs/telegram-monitor/evidence/MON-D18.md` |

## Verification commands and observed results (candidate `23068a6`)

| Command | Observed result |
| --- | --- |
| `uv run --frozen python -m pytest -q tests/test_telegram_monitor_sources.py -k base_ref -p no:randomly` | `18 passed, 43 deselected` (base: `18 failed, 43 deselected`) |
| `uv run --frozen python -m pytest -q tests/test_telegram_monitor_sources.py` | `61 passed` |
| `uv run --frozen python -m pytest -q tests/test_telegram_monitor_sources.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_runtime.py tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_cli_plugin.py` | `287 passed, 5 skipped, 0 failed` |
| `uv run --frozen pytest -q` (console script, as written on the card) over the same five files | `7 failed, 285 passed` — all seven are `ModuleNotFoundError: No module named 'scripts'` at import, an invocation artifact of the console script (the repository root is not on `sys.path`; the canonical `scripts/run_tests.py` and `python -m pytest` put it there). The same seven ids fail identically at `fa164c5` with the untouched `tests/test_telegram_monitor_cli_plugin.py`, so the candidate adds no failure. In that untouched file the five `AETHER_HERMES_PYTHON`-dependent tests also skip or run depending on the invocation and test order (observed: 5 skipped in the canonical five-file run, 0 skipped in the console five-file run, 2 skipped in a console single-file run of the base); no monitor test creates a board with `worktree_base_ref`, so this is independent of the candidate and was not chased further |
| `uv run --frozen python scripts/run_tests.py` | `2 failed, 1601 passed, 70 skipped` in 285.26 s, exit 1. Both failures are pre-existing and candidate-independent: `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths` and `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`. Baseline comparison at `fa164c5` for exactly those two files: `2 failed, 14 passed` with the identical two test ids and messages; candidate: identical |
| `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` (exit 0) |
| `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 65 source files` |
| `uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_telegram_monitor.py` | `All checks passed!` |
| `uv run --frozen ruff format --check src tests scripts/check_documentation.py scripts/qualify_telegram_monitor.py` | `144 files already formatted` |
| `uv run --frozen python -m compileall -q src tests scripts/qualify_telegram_monitor.py` | exit 0, no output |
| `git diff --check` | exit 0 |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | exit 1, pre-existing: `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home`, `…: operator-desktop-layout`. That contract file is untouched by this unit (last changed in `dad66f7`); the baseline scan at `fa164c5` reports the identical two findings |

Coverage note (bounded): measured on `tests/test_telegram_monitor_sources.py` alone, `src/aether_agents/monitor/sources.py` reports 76 % statement coverage; within the new code the only uncovered lines are the defensive exception handlers `sources.py:427-428` (invalid marker at the ref) and `sources.py:470-471` (Git invocation failure), both exercised conceptually by the fail-closed design but not by a dedicated fault injection. Every mainline branch added by D18 is exercised by the new tests. The integrated 78 % floor and its policy environment are owned by the repository CI and the terminal integration card; no floor or policy was changed here.

## Read-only proof detail

The read-only test asserts, after a successful collection that produced its item:

- the recorded Git argv list is non-empty, each entry starts with `git`, contains `show`, contains no write subcommand (`checkout`, `worktree`, `fetch`, `gc`, `add`, `commit`, `update-ref`, `rm`, `reset`, `restore`, `stash`, `switch`, `prune`, `repack`) and names the board's exact base ref;
- `git status --porcelain=v1 --untracked-files=all` and `git for-each-ref` are byte-identical before and after;
- the SHA-256 digests of the board, session and native-projects SQLite files are identical before and after (they are additionally opened with the module's existing `mode=ro`/`query_only` helper);
- the contract file is still absent from the primary working tree, i.e. nothing was checked out or materialized.

## Residual risk and open items

- Two defensive exception branches of the new read helper are not covered by a dedicated fault-injection test (above). Behavior is fail-closed by construction and by the surrounding negative controls.
- The ref path reads the repository at `project.path`; an exotic object store reachable only through ambient Git variables is deliberately not honored (`GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` are removed) and would be reported as an unreadable ref rather than silently reading another repository.
- Cross-artifact wording note (reported, not silently rewritten): `plan.md` §4 says legacy boards "without a usable base ref" may use the registered primary artifact when it independently passes the same checks, while `spec.md` §D18 says missing, invalid, unreachable or conflicting refs "remain a labeled gap for that board" and card requirements R3/R4 resolve the distinction. This unit follows `spec.md` §D18 and the stamped card: key absent → legacy primary path; key present (even unusable) → authoritative, gap, no fallback. No documentation was edited by this unit.
- This unit does not claim installation-wide attribution or a production snapshot result; the real-board canary, runtime update and aggregate closeout remain with `MON-V5-INT` (terminal card), and independent review remains with the same-card Supervisor review lane.
