# RC16-IDENT — rc16 identity, workflow pin, documentation, and manifest coherence

**Unit.** RC16-IDENT (Implementer) of the Aether `1.0.0-rc.16` objective (#494).

**Authority.** Objective Contract `oc_c770cea3db51d97e@v2`, SHA-256
`cd80efb52125f45af5340baf8119aeaddc4756f9d04ae7722137ae5df1f9adc7`, plus the
Supervisor-owned execution breakdown `specs/issue-494-project-provenance/tasks-rc16.md`
(commit `96c200e0`).

**Base commit.** `dc4872834a2c670c506100fd60c69960247124f2` (contract authorization
commit).

**Effects.** Local and reversible unit changes only: file edits in `<aether-unit-worktree>`,
one local commit on the unit branch, and read-only test/scan runs. No push, no PR, no merge,
no tag creation, no package publication, no release creation, no deployment, no service
restart, and no credential or provider/config use.

**Status of this record.** Unit-level implementation evidence. It is not independent review,
not integration, not activation, and does not claim any merge, tag, PR, or publication state.
Supervisor owns aggregate release conclusions and pipeline integration; Morfeo owns final
reception.

---

## 0. Reading conventions and sanitization

- All file references are project-relative.
- No machine paths, operating-system usernames, provider credentials, board IDs, or session IDs are included.
- Exact commit SHAs, SHA-256 digests, and canonical public URLs are recorded verbatim.

---

## 1. What changed

```console
$ git status --porcelain
 M .github/workflows/policy.yml
 M .github/workflows/release.yml
 M CHANGELOG.md
 M README.md
 M VERSION
 M docs/index.md
 M docs/reference/limitations-and-troubleshooting.md
 M tests/test_public_artifacts.py
 M tests/test_release_bundle.py
?? specs/issue-494-project-provenance/evidence/RC16-IDENT.md
```

| Path | Change | sha256 (delivered) |
| --- | --- | --- |
| `VERSION` | `1.0.0rc15` → `1.0.0rc16` (single source of truth for the package version) | `f83b4a1ec460803de26aa2c351c13d8c84819a9931b80784877fa97b9a916f90` |
| `CHANGELOG.md` | Add `## 1.0.0rc16` section detailing HLP-428 requirement, HLP-433 deferral, exact maintained-fork commit/digest pin, and retained RC15 review guidance durable-history fallback | `d37da59f2554cb626bd77c325ba5117862bf312a7f38e74dbebfe2153ca27a25` |
| `README.md` | Status paragraph updated to local-only `1.0.0rc16` / `1.0.0-rc.16` candidate identity, patch/prepare/prerelease conclusions, honest limits, and predecessor dispositions | `4eea8c9129a8924636e7332d1cd7b6573efefe3e5b5ba9f38e83eb368c0fe068` |
| `docs/index.md` | Update candidate declaration to `1.0.0rc16`, maintained-fork commit `58f8c37a49…` and digest `a2a9b374bd…`, HLP-428 required, HLP-433 deferred, and retained RC15 review fallback | `4f96b0cfa163b7e91211a18d5c6a8088b14c8199ae36e4a3757565427daae22a` |
| `docs/reference/limitations-and-troubleshooting.md` | Update `Release-candidate scope` table entry to `1.0.0rc16` candidate scope, exact fork pin and digest, and isolated transition verification requirement | `f175cbe049c76fa9922920cc1234850475e53c98187a4fae4ad850963487c54d` |
| `.github/workflows/release.yml` | Update `FORK_COMMIT` to `58f8c37a49b341f25b8fdd6310542fe932031b8d` and reconcile explanatory comment | `4bc2b1f96fefb3b92d8b31c6b1acfb01d0d961b2b963bb73d1c974e35a935952` |
| `.github/workflows/policy.yml` | Add missing literal roster lines for `.aether/objective-contracts/oc_c770cea3db51d97e/{v1,v2}.md` in alphabetical order, resolving base-commit red | `f1fe8b32b3d50e6bf62abd58c43a17040a6f3e208ca3b7ec1637df3459603ca7` |
| `tests/test_release_bundle.py` | Update `FORK_COMMIT` to `58f8c37a49b341f25b8fdd6310542fe932031b8d` and `test_version_file_carries_the_objective_release_identity` to assert `1.0.0rc16` / `1.0.0-rc.16` / `v1.0.0-rc.16` | `20c9f0841498e8c6b60a957fd76d9c5f587c65a5f3edf752297f0b2338888693` |
| `tests/test_public_artifacts.py` | Add `1.0.0rc15` and `1.0.0rc16` to `ACCEPTED_PACKAGE_IDENTITIES` and update README/status assertions for rc16 candidate text without weakening refusal cases | `171118b762f82063bf09e435c1aa46d0b0067310c6ebb249fcea7d3288bf56e4` |
| `specs/issue-494-project-provenance/evidence/RC16-IDENT.md` | This unit evidence document | *(this file)* |

---

## 2. Peer evidence disposition and non-applicability of root AGENTS.md update

- **Peer advice received mid-turn:**
  Design-steward correction regarding WORK ITEM 4 / writable surface: the owner's current instruction explicitly specifies that the root `AGENTS.md` write was denied by an approval-timeout guard; do not retry or route around that write, and report guidance-update non-applicability.
- **Disposition:**
  Concurred and applied. In accordance with Aether operating guidance (sector 04: "If the guidance update is not in scope, give a specific non-applicability reason in the evidence. Preserve brownfield instructions rather than replacing them generically.") and the owner's current instruction:
  - `AGENTS.md` is **not modified** in this unit.
  - The root guidance update is reported as non-applicable to this unit's local execution because the write is guard-restricted by owner instruction.
  - No test suite check depends on modifying `AGENTS.md`.

---

## 3. Preservation of RC15 resources

The contract and task delivery mandate that the two RC15 Supervisor resource files remain byte-identical:
- `src/aether_agents/resources/profiles/supervisor/SOUL.md`:
  `sha256: 805cf49de01d09a0586747217ddd271e142217ae0a85e84296774c99bc1389af`
- `src/aether_agents/resources/skills/supervisor-decomposition/SKILL.md`:
  `sha256: d201fee726014df9913edc2c7f3978fa1a50dcac83f0a4469badd93067417941`

Verification:
```console
$ sha256sum src/aether_agents/resources/profiles/supervisor/SOUL.md src/aether_agents/resources/skills/supervisor-decomposition/SKILL.md
805cf49de01d09a0586747217ddd271e142217ae0a85e84296774c99bc1389af  src/aether_agents/resources/profiles/supervisor/SOUL.md
d201fee726014df9913edc2c7f3978fa1a50dcac83f0a4469badd93067417941  src/aether_agents/resources/skills/supervisor-decomposition/SKILL.md
```
Both files remain untouched and byte-identical to base.

---

## 4. Policy workflow literal roster completion

The base commit violated `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` because `.aether/objective-contracts/oc_c770cea3db51d97e/v1.md` and `v2.md` were tracked without being present in the literal manifest in `.github/workflows/policy.yml` (manifest had 472 entries vs 474 tracked non-`specs/` files).

These two lines were inserted in alphabetical order. Per instructions, roster lines for files created by downstream units (e.g., transition qualification script and fixtures) are deliberately **not** added here; `RC16-INT` completes the roster after merge, matching the accepted `LC-INT` precedent.

---

## 5. Acceptance verification and raw command results

### Check 1: Release bundle and public artifacts test suite
```console
$ uv run --frozen python scripts/run_tests.py -- tests/test_release_bundle.py tests/test_public_artifacts.py -q
................................................                         [100%]
48 passed in 8.89s
```
**Result:** 48 passed, 0 failed.

### Check 2: Documentation registry check
```console
$ uv run --frozen python scripts/check_documentation.py
documentation validation passed
```
**Result:** PASS (exit code 0).

### Check 3: Public artifact scanner
```console
$ uv run --frozen python scripts/check_public_artifacts.py --root .
public artifact path scan passed: tracked surface + 0 artifact(s)
```
**Result:** PASS (exit code 0).

### Check 4: Ruff linter
```console
$ uv run --frozen ruff check src/aether_agents tests scripts
All checks passed!
```
**Result:** PASS (exit code 0).

### Check 5: Ruff format check
```console
$ uv run --frozen ruff format --check src/aether_agents tests scripts
198 files already formatted
```
**Result:** PASS (exit code 0).

### Check 6: Git diff check
```console
$ git diff --check
(clean, exit code 0)
```
**Result:** PASS (exit code 0).

---

## 6. Requirement coverage

| Requirement | Addressed in this unit | Evidence |
| --- | --- | --- |
| Package identity `1.0.0rc16` | `VERSION`, `tests/test_release_bundle.py` | `VERSION` carries `1.0.0rc16`; test passes |
| Display identity `1.0.0-rc.16` | `CHANGELOG.md`, `README.md`, `docs/index.md`, `docs/reference/limitations-and-troubleshooting.md`, `tests/test_release_bundle.py` | Release identity tests and docs tests pass |
| Tag identity `v1.0.0-rc.16` | `tests/test_release_bundle.py`, `tests/test_public_artifacts.py` | `test_version_file_carries_the_objective_release_identity` passes; status assertions verify tag identity |
| Maintained-fork pin | `.github/workflows/release.yml`, `tests/test_release_bundle.py` | `FORK_COMMIT` set to `58f8c37a49b341f25b8fdd6310542fe932031b8d`; release bundle tests pass |
| Base manifest red repair | `.github/workflows/policy.yml` | `test_canonical_base_manifest_matches_tracked_non_specs_files` passes |
| Preserved RC15 resources | `src/aether_agents/resources/**` untouched | Exact sha256 confirmed unchanged |
| Root `AGENTS.md` non-applicability | Documented in Section 2 above | Peer guidance and owner instruction respected |

---

## 7. Compatibility conclusion

- **Unit-level release impact:** `release_impact=patch`
- **Unit-level release action:** `release_action=prepare`
- **Unit-level release channel:** `release_channel=prerelease`
- **Scope:** Local-only candidate. No tag push, no package publication, no deployment, and no stable `1.0.0` claim. Supervisor owns aggregate release conclusions.

---

## 8. Limits and remaining risk

- This unit delivers the identity and static baseline for RC16. It does not qualify the isolated transition (owned by `RC16-TRANS`), perform the integration merge and local tagging (owned by `RC16-INT`), perform the live cutover (owned by `RC16-CUTOVER`), or execute the canary (owned by `RC16-CANARY`).
- Neither this source nor a local tag proves what is active on the host or that agent behavior improved.
