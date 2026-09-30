# EIH-A Evidence — Contract Selection and Board Projection

**Unit**: EIH-A
**Objective Contract**: `oc_f1ea2c4a2e0662da@v1`
**Owning Issue**: [#563](https://github.com/DarkArty07/Aether-Agents/issues/563)
**Base Commit**: `2221302f1c93fb4ffd166df9b5482aa2fecaef7a`
**Task ID**: `t_a1c42d22`
**Profile**: `implementer`

---

## 1. Outcome Summary

Implemented the contract selection parameter `implementer_harness` and its execution-board projection per EIH-01, EIH-02, AC1, AC2, and plan §3.2/§3.3:
1. `objective_contract` accepts optional `implementer_harness` on `begin` and `supersede` only.
2. `begin` with the parameter omitted or `"hermes"` renders final contract bytes identical to the pre-change renderer and projects no `aether_implementer_harness` metadata key onto the execution board.
3. `begin` with `"claude-code"` renders the front-matter key `implementer_harness: "claude-code"` and `prepare_handoff` projects `aether_implementer_harness: "claude-code"` onto execution-board metadata.
4. `supersede`: omitted inherits the superseded version's selection, `"hermes"` clears it, and `"claude-code"` sets it.
5. Unknown values are rejected with `AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID` and never treated as absent. Any action other than `begin` or `supersede` receiving the parameter is rejected with `AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID`.
6. On board reuse, the stored value on `board.json` must equal the contract's selection, both absent included; any mismatch raises `AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT`.
7. `show` reports the selection.
8. An rc17-style parser (parsing every `key: json` front-matter line and requiring only known metadata keys, artifact type, and final status) accepts a selected final contract.
9. Verified byte-for-byte identity of an unselected contract against the pre-change rendering.

---

## 2. Modification Boundary Verification

- **Modified Files**:
  - `src/aether_agents/objective_contracts/store.py`:
    - `begin`: accepts `implementer_harness` (`"hermes"` | `"claude-code"` | `None`). Stores in draft only when set (`"claude-code"`).
    - `_draft_validation`: validates that any draft `implementer_harness` is `"claude-code"`.
    - `_render_final`: emits `implementer_harness: "claude-code"` only when set. When unselected, output is byte-for-byte identical to pre-change rendering.
    - `_validate_final`: rejects unknown or non-`"claude-code"` values with `AETHER-OBJECTIVE-CONTRACT-FINAL-INVALID`.
    - `finalize`: forwards `implementer_harness` in return payload when set.
    - `supersede`: accepts `implementer_harness`, implements inheritance (None), clearing (`"hermes"`), and setting (`"claude-code"`).
    - `prepare_handoff`: includes `implementer_harness` in handoff result when set; preserves envelope without harness text.
  - `src/aether_agents/objective_contracts/hermes_plugin.py`:
    - `_create_metadata_exclusive`: sets `payload["aether_implementer_harness"] = "claude-code"` only when selected.
    - `_validate_execution_metadata`: verifies board metadata equality against contract selection (both absent included), raising `AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT` on mismatch.
    - `_provision_execution_board`: forwards `implementer_harness` to `_create_metadata_exclusive` and `_validate_execution_metadata`.
    - `_handle`: enforces that `implementer_harness` is received on `begin` and `supersede` only; rejects any other action receiving it; forwards parameter to store methods and handoff provisioner.
    - `register`: added `implementer_harness` entry (enum `["hermes", "claude-code"]`) to tool parameters schema properties. No `HERMES_BIN` override logic was added (preserved for EIH-B).
  - `tests/test_implementer_harness_selection.py`:
    - 15 new focused unit tests covering selection, rejection, rendering, rc17 compatibility, supersede inheritance/clearing/setting, and board projection/reuse.
  - `specs/external-implementer-harness/evidence/EIH-A.md`:
    - This evidence receipt.

- **Preserved Boundaries**:
  - `register` function in `hermes_plugin.py`: no `HERMES_BIN` override logic touched (owned by EIH-B per task breakdown correction `t_f6160bfc`).
  - `pyproject.toml` (untouched).
  - `policy/` (untouched).
  - `src/aether_agents/resources/` (untouched).
  - Canonical Objective Contract and specs design artifacts (untouched).
  - No secrets, credentials, or operator home paths added.

---

## 3. Verification and Evidence Matrix

| Check | Command | Observed Result | Evidence Location |
| --- | --- | --- | --- |
| Focused selection tests | `uv run --frozen python scripts/run_tests.py tests/test_implementer_harness_selection.py` | 15 passed in 14.53s | `tests/test_implementer_harness_selection.py` |
| Regression contracts suite | `uv run --frozen python scripts/run_tests.py tests/test_objective_contracts.py` | 45 passed in 211.98s | `tests/test_objective_contracts.py` |
| Linter check | `uv run --frozen ruff check src/aether_agents/objective_contracts/ tests/test_implementer_harness_selection.py` | All checks passed! | Source tree |
| Formatter check | `uv run --frozen ruff format --check src/aether_agents/objective_contracts/ tests/test_implementer_harness_selection.py` | 5 files already formatted | Source tree |
| Type check | `uv run --frozen mypy src/aether_agents/objective_contracts/` | Success: no issues found in 3 source files | Source tree |
| Whitespace & git check | `git diff --check` | Clean (exit code 0) | Git diff |

### Quickstart §1 Bullet Mapping

1. **Contract selection**:
   - `begin` with `implementer_harness=None` (omitted) and `"hermes"` creates draft without `implementer_harness` key; verified in `test_begin_unselected_and_hermes_semantics`.
   - `begin` with `implementer_harness="claude-code"` stores selection and `show` reports it; verified in `test_begin_claude_code_selection`.
   - `begin` with unknown values (`"claude"`, `"gpt-4"`, `""`, `123`) rejected with `AETHER-OBJECTIVE-CONTRACT-HARNESS-INVALID`; verified in `test_begin_rejects_unknown_values`.
   - `supersede` inherits when omitted, clears when `"hermes"`, and sets when `"claude-code"`; verified in `test_supersede_from_unselected_v1` and `test_supersede_from_claude_code_v1`.
   - `_handle` rejects `implementer_harness` on `set_section`, `show`, `list`, `validate`, `finalize`, `prepare_handoff`; verified in `test_hermes_plugin_handle_action_restrictions_and_unknown_rejection`.
   - An rc17-style parser accepts selected final contract; verified in `test_rc17_style_parser_accepts_selected_final_contract`.
   - Byte-for-byte comparison of an unselected contract against pre-change rendering verified in `test_unselected_and_hermes_render_bytes_identical_to_prechange`.

2. **Board projection**:
   - Board creation with and without selection; verified in `test_board_metadata_creation_and_reuse_validation` and `test_prepare_handoff_provisions_and_validates_board_metadata_e2e`.
   - Board reuse equality (both absent included) and mismatch raising `AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT`; verified in `test_board_metadata_creation_and_reuse_validation` and `test_prepare_handoff_provisions_and_validates_board_metadata_e2e`.

---

## 4. Unit Compatibility Conclusion

- **Compatibility impact**: `minor` (additive, opt-in).
  - Existing unselected contracts and boards remain byte-for-byte identical to pre-change behavior.
  - Prior readers (such as rc17) parse and accept contracts carrying `implementer_harness: "claude-code"`.
  - Existing boards without `aether_implementer_harness` remain valid and reusable for unselected contracts.
