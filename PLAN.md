# PLAN: Multi-Project Isolation for .aether

**Branch:** `fix/aether-multi-project-isolation`
**Phase:** PLAN → CODE
**Date:** 2025-05-15

## Problem

Cross-project contamination in `.aether` — data from one project (Barajas Dumont) bleeds into another (Aether Agents) because MCP tools resolve the database path via `AETHER_HOME` environment variable instead of using the `project_root` parameter that already exists in the tool schemas.

### Root Cause Chain

1. **MCP handlers use `get_aether_db_path()`** which resolves via `AETHER_HOME` env var → `home/.aether/aether.db` — a static path shared across all projects
2. **`project_root` param exists but is ignored** — `aether_status`, `aether_update`, `aether_curate` schemas have `project_root` but the handlers don't use it to resolve the DB path
3. **`aether_update` schema lacks `project_root`** — it's not even in the parameter schema
4. **`aether_curate` reads data from wrong DB** — even though it writes CONTEXT.md to the correct `{project_root}/.aether/`, it fetches data from `get_aether_db_path()` → `home/.aether/aether.db`
5. **Stale `.aether_home` files** — Daimon profile files point to previous projects, not current `project_root`
6. **No `project_root` in `hot_state`** — the DB doesn't track which project it belongs to, making it impossible to validate isolation

### Evidence: 3 DBs for 1 Project

| Path | Who reads it | Contents |
|------|-------------|----------|
| `{project_root}/.aether/aether.db` | Plugin hooks (when cwd=project) | Nearly empty, phase=idea |
| `home/.aether/aether.db` | MCP server (Hermes) | Mixed Aether Agents + Barajas data |
| `/mnt/c/.../barajas/.aether/aether.db` | Ariadna (delegated) | 1 session, clean |

## Solution Design

**Principle: `project_root` is the sole project identifier. The DB always lives at `{project_root}/.aether/aether.db`.**

Every `.aether` operation (read, write, curate) resolves the database path from the `project_root` parameter. No fallback to `AETHER_HOME`, `cwd`, or any other mechanism for MCP tools. Plugin hooks (Daimons) continue using `AETHER_HOME` which `acp_manager` sets correctly per session.

## Tasks

### Task 1: Add `resolve_aether_db()` helper in `aether_db.py`

**File:** `src/olympus_v3/aether_db.py`

- Add function `resolve_aether_db(project_root: str) -> Path`
  - Returns `Path(project_root) / ".aether" / "aether.db"`
  - Auto-creates `{project_root}/.aether/` directory if it doesn't exist
  - Logs the resolved path at INFO level
- Keep `get_aether_db_path()` unchanged — it's still used by plugin hooks (Daimons)
- Add `resolve_aether_dir(project_root: str) -> Path` convenience that returns just the `.aether/` directory

**Acceptance criteria:**
- `resolve_aether_db("/home/prometeo/Aether-Agents")` returns `/home/prometeo/Aether-Agents/.aether/aether.db`
- If `.aether/` doesn't exist, it's created automatically
- `get_aether_db_path()` behavior is unchanged (still uses AETHER_HOME → HERMES_HOME → cwd chain)

### Task 2: MCP handlers use `resolve_aether_db(project_root)` instead of `get_aether_db_path()`

**File:** `src/olympus_v3/server.py`

- `_handle_aether_status(args)`:
  - Extract `project_root = args.get("project_root", "")`
  - If empty → return error `"project_root is required for aether_status"`
  - Replace `db_path = get_aether_db_path()` with `db_path = resolve_aether_db(project_root)`
  - Remove the `if not db_path.exists()` guard (resolve_aether_db auto-creates .aether/)

- `_handle_aether_update(args)`:
  - Add `project_root` as a **required** parameter in the tool schema (currently missing)
  - Extract `project_root = args.get("project_root", "")`
  - If empty → return error `"project_root is required for aether_update"`
  - Replace `db_path = get_aether_db_path()` with `db_path = resolve_aether_db(project_root)`
  - Remove the `if not db_path.exists()` guard

- `_handle_aether_curate(args)`:
  - `project_root` is already required, keep it
  - Replace `db_path = get_aether_db_path()` with `db_path = resolve_aether_db(project_root)`
  - Remove the separate `if not aether_dir.exists()` check (resolve_aether_db handles this)
  - Keep the `aether_dir = project_path / ".aether"` for CONTEXT.md path resolution

- Import `resolve_aether_db` from `olympus_v3.aether_db`

**Acceptance criteria:**
- `aether_status(project_root="/home/prometeo/Aether-Agents")` reads from `/home/prometeo/Aether-Agents/.aether/aether.db`
- `aether_status()` without project_root returns error
- `aether_update` requires project_root parameter
- `aether_curate` uses project_root for both DB reads and CONTEXT.md writes

### Task 3: Add `project_root` to `aether_update` tool schema

**File:** `src/olympus_v3/server.py`

- In the `aether_update` tool definition (`inputSchema`), add:
  ```python
  "project_root": {
      "type": "string",
      "description": "Absolute path to the project root. Used to resolve the .aether database path. REQUIRED.",
  }
  ```
- Add `"project_root"` to the `"required"` list of the schema

**Acceptance criteria:**
- The MCP tool schema for `aether_update` includes `project_root` as required
- Calling `aether_update` without `project_root` returns a clear error

### Task 4: Plugin hooks write `project_root` to `hot_state`

**File:** `src/olympus_v3/aether_hooks/hooks.py`

- In `on_post_llm_call` (first turn):
  - After writing `last_request`, also write `project_root` from `AETHER_HOME` env var:
    ```python
    aether_home = os.environ.get("AETHER_HOME")
    if aether_home:
        db.update_hot_state(project_root=aether_home)
    ```

- In `on_session_end`:
  - Same: write `project_root` from `AETHER_HOME` when updating hot_state

- This ensures every `.aether` DB knows which project it belongs to, enables future validation

**Acceptance criteria:**
- After a Daimon session, `hot_state.project_root` contains the AETHER_HOME value
- If AETHER_HOME is not set, project_root is not updated (it may already have a value from a previous operation)

### Task 5: Clean up stale `.aether_home` files

**Files:** Daimon profile directories

- Delete `.aether_home` from all Daimon profile directories:
  - `home/profiles/hefesto/.aether_home` (points to `/home/prometeo/Aether-Agents/home` — wrong)
  - `home/profiles/ariadna/.aether_home` (points to `/mnt/c/.../barajas-dumont-erp` — stale)
  - Any other Daimon profiles that have `.aether_home` files

- These files are written by `acp_manager` on every `send_message` call, so there's no risk in deleting them — they'll be recreated correctly when the next session starts

- Verify in `acp_manager.py` that `.aether_home` always gets `session.project_root` (which comes from the `project_root` argument of `spawn_agent`/`send_message`)

**Acceptance criteria:**
- No `.aether_home` files exist in Daimon profiles before they're recreated by acp_manager
- `acp_manager._spawn_process` still writes `.aether_home` with the current `project_root`

### Task 6: Migrate data from `home/.aether/` to project-level `.aether/`

This task merges useful data from the contaminated `home/.aether/aether.db` into the correct `Aether-Agents/.aether/aether.db`, then removes the contaminated DB.

**Steps:**
1. Read `home/.aether/aether.db` and extract valid Aether Agents data:
   - Sessions where `result_summary` or `request` mentions Aether Agents topics (olympus, aether, hefesto, plugin, hooks, etc.)
   - Decisions (all 3 are about Aether Agents architecture)
   - Exclude: Issue #2 (Tauri bug belongs to Barajas), any sessions about Barajas
2. Merge into `Aether-Agents/.aether/aether.db`:
   - Insert valid sessions
   - Insert decisions with new IDs
   - Update `hot_state` with correct `project_root=/home/prometeo/Aether-Agents`
3. Delete `home/.aether/aether.db` (and the `home/.aether/` directory if empty)
4. Clean up the Barajas project DB: run `aether_curate` to regenerate its CONTEXT.md with correct data

**Acceptance criteria:**
- `home/.aether/aether.db` no longer exists
- `Aether-Agents/.aether/aether.db` has the 3 Aether Agents decisions
- Barajas `.aether/aether.db` is clean (only Barajas data, no Aether Agents contamination)
- No issue #2 (Tauri bug) exists in the Aether Agents DB — it stays only in Barajas project if Chris wants it there

### Task 7: Update tests

**File:** `tests/test_aether.py`

- Add tests for `resolve_aether_db()`:
  - Returns correct path for a given project_root
  - Auto-creates `.aether/` directory
  - Works with paths containing spaces and special characters

- Update existing `aether_status`, `aether_update`, `aether_curate` tests to pass `project_root`

- Add test that `aether_status` without `project_root` returns an error

- Add test that DB reads/writes go to `{project_root}/.aether/aether.db`, not `home/.aether/`

**Acceptance criteria:**
- All existing tests pass
- New tests cover the isolation guarantee: different project_root → different DB

## Verification Checklist

After all tasks are complete:

1. `aether_status(project_root="/home/prometeo/Aether-Agents")` → reads from Aether Agents DB, shows Aether Agents data only
2. `aether_status(project_root="/mnt/c/.../barajas-dumont-erp")` → reads from Barajas DB, shows Barajas data only
3. `aether_update(action="add_issue", project_root="/home/prometeo/Aether-Agents", ...)` → writes to Aether Agents DB only
4. `aether_curate(project_root="/home/prometeo/Aether-Agents")` → reads AND writes from/to Aether Agents project only
5. A Daimon spawned with `project_root=Barajas` writes sessions to Barajas `.aether/aether.db` (via AETHER_HOME)
6. A Daimon spawned with `project_root=Aether-Agents` writes sessions to Aether Agents `.aether/aether.db` (via AETHER_HOME)
7. No `home/.aether/aether.db` contamination path exists
8. Tests pass

## Out of Scope

- Schema migration (no `project_id` column — the path IS the namespace)
- New Daimon profiles
- Changes to plugin hook resolution chain (AETHER_HOME stays for Daimons)
- CONTEXT.md content format changes
