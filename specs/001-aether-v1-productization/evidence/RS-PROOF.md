# RS-PROOF — Contaminated-previous disposable two-hop

**Authority.** Objective Contract `oc_f190ae9e878151e6@v2` (SHA-256
`9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188`), in-scope
items 3 and 4; AC-3 and AC-4; breakdown unit RS-PROOF from
`specs/001-aether-v1-productization/tasks-rc4-restore.md`.

**Base.** Commit `3e814325d6108d8d9b61534c8c6c0093a5a68c0e`, breakdown commit
`9ab00bcbe36e26f3f5a6d9d20be84909b0269582`, and reviewed parent unit RS-RESTORE
candidate commit `97539c038d0754de79746e44be8a7fbd4b142b92`.

**Tracked harness.** `specs/001-aether-v1-productization/fixtures/run_rs_proof.py`.
No changes outside `specs/`; `.github/workflows/policy.yml` manifest is preserved
at 429 expected files.

**Unit compatibility.** `patch` (internal verification harness and evidence; no
public schema or external interface changed). Aggregate release conclusions are deferred
to terminal Supervisor integration (`RS-CLOSE`).

---

## 1. Bridge Identity Revalidation (AC-3)

Bridge identities established during BS-BRIDGE were independently revalidated without
recreation or retagging:

| Property | Value / Observed | Revalidation Verdict |
| --- | --- | --- |
| Parent commit | `5a897746afe422f3c07f2290f9115d60204ef4d2` | **PASS** |
| Child commit | `d763c15b30f6edd8709aa2df33772b3601c67915` | **PASS** |
| `git diff --stat 5a897746..d763c15b` | `VERSION \| 2 +-` (1 insertion, 1 deletion: `1.0.0a4\n`) | **PASS** (`VERSION` only) |
| `git cat-file -t v1.0.0-a.4` | `tag` | **PASS** (annotated tag object) |
| Tag object digest | `5350ebb0ea91f6d6099d96d7448590515fff6036` | **PASS** |
| Tag target commit | `d763c15b30f6edd8709aa2df33772b3601c67915` | **PASS** |
| Wheel path | `/tmp/aether-bridge-1.0.0a4/dist/aether_agents-1.0.0a4-py3-none-any.whl` | **PASS** |
| Wheel SHA-256 | `0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec` | **PASS** |
| Wheel `METADATA` Version | `Version: 1.0.0a4` | **PASS** |
| Remote tag status | `git ls-remote --tags origin v1.0.0-a.4` returned empty string | **PASS** (local-only) |

---

## 2. Disposable Contaminated-Previous Two-Hop Proof (AC-4)

### Execution Model and Boundaries
- Isolated disposable base at `/tmp/rs-proof-disposable` with isolated `HOME`, `XDG_DATA_HOME`,
  `XDG_STATE_HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`.
- Confined environment verifies `LifecycleManager._is_installed_environment` is `False`.
- Scrubbed environment variables: `HERMES_KANBAN_*`, `HERMES_HOME`, `HERMES_SESSION_ID`,
  `PYTHONPATH`, `UV_*`, `PIP_*`.
- Seeded previous release: exact `1.0.0rc3-8987f650c027ad09` release record, active record
  and artifacts, with allowlisted contamination (8,884 extra entries across `node_modules/**`,
  `ui-tui/node_modules/**`, `ui-tui/dist/entry.js`, and 19 symlinks matching AC-1 classification).

### Step 1: Pre-Restore Hop 1 Refusal
- Command: Lexical installed rc3 manager python (`RC3_MANAGER_PYTHON`) executed:
  ```bash
  <data-root>/releases/1.0.0rc3-8987f650c027ad09/manager/bin/python \
    -m aether_agents.cli update --local \
    --aether-checkout /tmp/aether-bridge-1.0.0a4 \
    --aether-commit d763c15b30f6edd8709aa2df33772b3601c67915 \
    --fork-checkout /tmp/aether-hermes-aed6591-branch \
    --fork-commit aed6591a69f453a1867b73628603e7b53ba40ffc \
    --yes --json
  ```
- Result: Exited non-zero (return code 4).
- Envelope error:
  `{"code": "LOCAL_UPDATE_REFUSED", "message": "release source tree contains a non-regular file"}`.
- Refusal is strictly in the non-regular/source-integrity class; no private-path miss (`not "private directory component is a symlink"`).
- In accordance with v2 live-hop gating rules, Hop 2 was not started.

### Step 2: Atomic Restoration of Previous rc3
- Consumed reviewed restorer `restore_exact_hermes_source` from RS-RESTORE.
- Restorer verified exact inventory against clean materialized archive (`cc1ebf94…`),
  quarantined contamination to sibling `.quarantine-1.0.0rc3-8987f650c027ad09-<timestamp>`
  outside the release directory, and atomically placed clean fork tree in `hermes-source`.
- Preservation witness: `record.json`, `release.json`, `release-lock.json`, `profile-bundle.json`,
  `manager/bin/python`, `active.json`, and `runtime/current` symlink target verified **100% byte-identical**
  before and after restoration.
- Validation: Restored rc3 `validate_release` passed (`1.0.0rc3`), and `doctor` returned
  `ready: True` with zero diagnostic codes (`codes: []`).

### Step 3: Hop 1 Post-Restore Execution (rc3 -> bridge)
- Re-ran Hop 1 with lexical rc3 manager python.
- Result: Exited 0 (`result: "changed"`).
- Activated release: `1.0.0a4-0345df7335d338ff`.
- Wheel SHA-256: `0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec`.
- Manager authority: Authenticated and executed via bridge manager python
  (`<data-root>/releases/1.0.0a4-0345df7335d338ff/manager/bin/python`).
- Bridge constraints: TUI directory is absent (`releases/1.0.0a4-.../tui` does not exist);
  no ordinary workload or canary executed on the bridge.

### Step 4: Hop 2 Execution (bridge -> final rc4)
- Command: Executed from bridge manager python:
  ```bash
  <data-root>/releases/1.0.0a4-0345df7335d338ff/manager/bin/python \
    -m aether_agents.cli update --local \
    --aether-checkout /tmp/aether-rc4-candidate \
    --aether-commit 5a897746afe422f3c07f2290f9115d60204ef4d2 \
    --fork-checkout /tmp/aether-hermes-aed6591-branch \
    --fork-commit aed6591a69f453a1867b73628603e7b53ba40ffc \
    --yes --json
  ```
- Result: Exited 0 (`result: "changed"`).
- Activated release: `1.0.0rc4-9316cbddfee2b795`.
- Executing manager release ID: `1.0.0a4-0345df7335d338ff`.
- TUI verification:
  - TUI entry exists at `<release>/tui/dist/entry.js`.
  - SHA-256 matches exact prebuild: `f56f6225d9124376eedec1834d372c76a33292aedc41021cc13d6c3b32a05643`.
  - `tui/provenance.json` binds `hermes_commit: aed6591a69f453a1867b73628603e7b53ba40ffc`.
- Confined branded projections:
  - Launcher projection contains `export HERMES_TUI_DIR="$AETHER_RUNTIME_ROOT/tui"`.
  - Branded desktop entry contains `Name=Aether`, `Actions=Continue;`, `Name=Continue Aether`.
  - Legacy desktop entry `hermes.desktop` does not exist.
  - Service unit projection contains `Environment="HERMES_TUI_DIR=`.
- Final rc4 doctor check:
  - Exited 0 (`result: "ready"`).
  - Observer status `ready`, `diagnostic_codes: []`.
  - Projections `mismatches: []`.
  - Transition journal `pending_count: 0`.

---

## 3. Live System Witness Preservation

Pre-run and post-run fingerprints of ambient live system state were captured and compared:

| Witness | Pre-Run Fingerprint | Post-Run Fingerprint | Comparison |
| --- | --- | --- | --- |
| `active.json` | `9a633a0761d726730d118bfdfd82ed5dc2f498cefda2afe41298bc5b8a7e170a` | `9a633a0761d726730d118bfdfd82ed5dc2f498cefda2afe41298bc5b8a7e170a` | **Byte-identical** |
| `runtime/current` symlink target | `.../releases/1.0.0rc3-8987f650c027ad09` | `.../releases/1.0.0rc3-8987f650c027ad09` | **Byte-identical** |
| `hermes-gateway-morfeo.service` unit | `01190bc11de85fc0b43d874475a28bf875af9671ac0e14a5eb2e8aeb2adf465c` | `01190bc11de85fc0b43d874475a28bf875af9671ac0e14a5eb2e8aeb2adf465c` | **Byte-identical** |
| Launcher `~/.local/bin/aether` | `7c70dfdae4537d32a77164cddba2a774aee454ab5b503aba2fbabab8f7683d47` | `7c70dfdae4537d32a77164cddba2a774aee454ab5b503aba2fbabab8f7683d47` | **Byte-identical** |
| Legacy desktop entry `hermes.desktop` | `f552250a518cdad324c56ecadef18415b9e2afd920ea27dca5344827c5adff2a` | `f552250a518cdad324c56ecadef18415b9e2afd920ea27dca5344827c5adff2a` | **Byte-identical** |
| Branded desktop entry `aether.desktop` | `None` (absent) | `None` (absent) | **Byte-identical** |
| WSL shortcuts | `{}` | `{}` | **Byte-identical** |

Zero live system mutation occurred.

---

## 4. Raw JSON Receipts

### 4.1 Hop 1 Pre-Restore Refusal Receipt
```json
{
  "changed": false,
  "command": "update",
  "data": {},
  "errors": [
    {
      "code": "LOCAL_UPDATE_REFUSED",
      "message": "release source tree contains a non-regular file"
    }
  ],
  "manager_version": "1.0.0rc3",
  "result": "error",
  "schema_version": 1,
  "warnings": []
}
```

### 4.2 Restoration Receipt
```json
{
  "status": "restored",
  "clean_digest": "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7",
  "quarantine_path": "<disposable-data>/releases/.quarantine-1.0.0rc3-8987f650c027ad09-20260920154005",
  "inventory": {
    "clean_digest": "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7",
    "expected_files_count": 9377,
    "target_files_count": 18261,
    "missing_count": 0,
    "changed_count": 0,
    "extras_count": 8884,
    "extras_breakdown": {
      "node_modules": 8653,
      "ui_tui_node_modules": 230,
      "ui_tui_dist_entry_js": 1,
      "symlinks": 19
    },
    "disallowed_extras": [],
    "missing_files": [],
    "changed_files": []
  },
  "rc3_doctor_ready": true,
  "rc3_doctor_codes": []
}
```

### 4.3 Hop 1 Bridge Activation Receipt
```json
{
  "active_version": "1.0.0a4",
  "changed": true,
  "command": "update",
  "data": {
    "active_release_id": "1.0.0a4-0345df7335d338ff",
    "executing_manager_release_id": "1.0.0rc3-8987f650c027ad09",
    "hermes_commit": "aed6591a69f453a1867b73628603e7b53ba40ffc",
    "mode": "local",
    "observation_state_preserved": true,
    "wheel_sha256": "0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec"
  },
  "errors": [],
  "manager_version": "1.0.0rc3",
  "result": "changed",
  "schema_version": 1,
  "warnings": []
}
```

### 4.4 Hop 2 Final rc4 Activation Receipt
```json
{
  "active_version": "1.0.0rc4",
  "changed": true,
  "command": "update",
  "data": {
    "active_release_id": "1.0.0rc4-9316cbddfee2b795",
    "executing_manager_release_id": "1.0.0a4-0345df7335d338ff",
    "hermes_commit": "aed6591a69f453a1867b73628603e7b53ba40ffc",
    "mode": "local",
    "observation_state_preserved": true,
    "wheel_sha256": "9316cbddfee2b795c7dad29bcd7685e71a1ea037f336b9d7ee42f762d477982f"
  },
  "errors": [],
  "manager_version": "1.0.0a4",
  "result": "changed",
  "schema_version": 1,
  "warnings": []
}
```

### 4.5 Final rc4 Doctor Receipt
```json
{
  "active_version": "1.0.0rc4",
  "changed": false,
  "command": "doctor",
  "data": {
    "observer": {
      "active_release_id": "1.0.0rc4-9316cbddfee2b795",
      "active_version": "1.0.0rc4",
      "diagnostic_codes": [],
      "hook_probe": {
        "expected_callbacks": 22,
        "registered_callbacks": 22,
        "remaining_callbacks": 0
      },
      "observer_state": {
        "health_counter_classes": 0,
        "health_counter_total": 0,
        "incomplete_summary_count": 0,
        "invalid_summary_count": 0,
        "journal_file_count": 0,
        "project_count": 0,
        "projection_file_count": 0,
        "projection_integrity_failures": 0,
        "quarantine_file_count": 0,
        "summary_file_count": 0
      },
      "profile_count": 3,
      "projections": {
        "mismatches": [],
        "projection_digests": {
          "desktop": "785935c83369ad3533093a8a9c18273cebe0cbaaf085eeb6c2ddcb662c254380",
          "launcher": "dfbf5af6529947900edda7b7baf6d509e8d41b5357446e8c02b158dc100c8391",
          "service": "b8646b45412f85a7a6aa36b53a3f26ae92736fecdccb7d85eeb88ad63811e177",
          "wsl_aether": "234768913dc51759e262b9b435dc726b64c1da45c2e5f607ae4db0a98e0f74a1",
          "wsl_continue_aether": "6a650b506d2af026b3b76c4732eae97307fc3c763c31f7b1e80dc37c7a781f9e"
        },
        "runtime_current": "<disposable-data>/releases/1.0.0rc4-9316cbddfee2b795",
        "service_unit": "hermes-gateway-morfeo.service"
      },
      "service_controller": {
        "available": false,
        "reason": "disabled_non_installed_environment"
      },
      "source": {
        "artifacts": 1,
        "branch": "aether-main",
        "commit": "aed6591a69f453a1867b73628603e7b53ba40ffc",
        "lock_sha256": "304ed4dfc53cd4db744f632adab02789e36d74fcdfaed3321052423582b08c92",
        "repository": "https://github.com/DarkArty07/aether-hermes",
        "source_mode": "maintained_fork",
        "source_tree_sha256": "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7",
        "version": "0.20.1"
      },
      "status": "ready",
      "transition_journal": {
        "journal_count": 2,
        "pending_count": 0
      }
    }
  },
  "errors": [],
  "manager_version": "1.0.0rc4",
  "result": "ready",
  "schema_version": 1,
  "warnings": []
}
```
