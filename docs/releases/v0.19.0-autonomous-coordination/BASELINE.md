# v0.19.0 Autonomous Coordination — Baseline

**Status:** **VERIFIED baseline map** from the v0.18.2 repository source and retained release evidence. Nothing in this document asserts a newly executed test result.

**Cross-reference:** target changes are constrained by [DESIGN.md](DESIGN.md); research and fit are in [RESEARCH.md](RESEARCH.md) and [FEASIBILITY.md](FEASIBILITY.md).

## 1. Release and public surface

| Item | Verified baseline |
|---|---|
| Version | `0.18.2` in `pyproject.toml` |
| Python | `>=3.11` |
| Entry point | `olympus-v3 = olympus_v3.server:main` |
| Historical test evidence | 121 tests passed for v0.18.2; **not executed for this documentation task** |
| MCP tools | `talk_to`, `discover`, `aether_status`, `aether_update`, `aether_curate` |
| `talk_to` actions | `open`, `message`, `poll`, `close`, `cancel`, `delegate`, `steer` |

## 2. Current source map

| Path | Verified symbols/responsibility | Current authority |
|---|---|---|
| `src/olympus_v3/server.py` | `init_server`, `list_tools`, `call_tool`, `_handle_talk_to`, `_build_response` | MCP tool routing and server-level orchestration |
| `src/olympus_v3/acp_manager.py` | `AgentState`, `SessionInfo`, `ACPManager.spawn_agent`, `_spawn_process`, `send_message`, `poll`, `close`, `cancel`, `delegate`, `shutdown_agent`, `OlympusACPClient` | ACP process/session management |
| `src/olympus_v3/db.py` | `OlympusDB`, `OlympusDBSync` | Olympus session/turn/tool/steering persistence |
| `src/olympus_v3/aether_db.py` | `AetherDB`, `AetherDBSync` | `.aether` continuity persistence |
| `src/olympus_v3/aether_hooks/hooks.py` | Aether project-continuity hook integration | Hook-side continuity updates |
| `src/olympus_v3/olympus_v3_hooks/hooks.py` | Olympus session/turn/tool hook integration | Hook-side runtime observability updates |
| `tests/test_server_schema.py` | MCP schema coverage | Public tool/action regression coverage |
| `tests/test_aether.py`, `tests/test_aether_curate.py`, `tests/test_aether_setup_cli.py` | Continuity, curation, setup coverage | Existing behavior regression coverage |

## 3. Persistence map

Both database modules enable SQLite WAL and foreign keys; polling checkpoints WAL. This supports existing concurrent observation but is **not** a semantic coordination ledger.

| Store | Tables | What it proves today | What it does not prove |
|---|---|---|---|
| Olympus DB (`.olympus/olympus_v3.db`) | `sessions`, `turns`, `tool_calls`, `steering` | Session records, turns, tool calls, persisted steering | Contract authority, capability enforcement, fencing, immutable coordination events, semantic closure |
| Aether DB (`.aether/aether.db`) | `hot_state`, `sessions`, `file_changes`, `decisions`, `issues` | Durable project continuity and curated context inputs | Task graph, append-only integrity chain, effect reconciliation, capability grants |
| `.aether/CONTEXT.md` | Curated projection file | First-turn project context | Primary operational state or authoritative event log |
| Artifact target | Repository/files/reports/remote receipts | Actual work-product contents | Contract/gate decision authority |

## 4. Existing lifecycle map

1. `server.init_server()` connects `OlympusDB` and constructs `ACPManager`.
2. `talk_to open/delegate` reaches `ACPManager.spawn_agent()`; agent state is keyed by `(agent_name, project_root)`.
3. `_spawn_process()` invokes Hermes ACP with profile-specific `HERMES_HOME`, project `AETHER_HOME`, `PYTHONPATH`, and `OLYMPUS_DB_PATH`.
4. An ACP session is created and persisted; messages are sent through ACP; polling reads SQLite rather than ACP streaming.
5. `aether_hooks` and `olympus_v3_hooks` write hooks-side records. `CONTEXT.md` is the curated first-turn projection; steering is persisted and consumed before model work.
6. `shutdown_agent` owns process teardown via the async process context manager, with bounded subprocess fallback. `close`/`cancel` do not terminate an idle reusable process; completed delegated sessions remain open.

## 5. Baseline non-regression invariants

The v0.19 implementation may extend but must not regress these facts without separately approved migration and evidence:

1. Olympus/ACP remains the only owner of spawned process and ACP-session lifecycle.
2. Process context and yielded subprocess remain distinct ownership objects; normal teardown is exact-once and fallback is bounded.
3. A completed delegate session remains reusable/open according to existing lifecycle behavior; `close`/`cancel` do not indiscriminately kill an idle runtime.
4. The five MCP tools and seven `talk_to` actions retain documented semantics unless a separately approved public-contract migration changes them.
5. Existing `.aether` continuity remains durable, and `CONTEXT.md` remains a curated projection rather than raw state.
6. Existing WAL/FK behavior remains enabled; a new store cannot silently weaken current durability or isolation.
7. Persisted steering remains pre-LLM consumed; external/peer payloads cannot gain system authority through any new coordination context path.
8. Artifact truth and historical 121-test evidence must not be relabeled as new v0.19 execution evidence.

## 6. Explicit gaps (not defects silently filled by prose)

**VERIFIED absent from current stores:** semantic coordination ledger, authenticated append-only event integrity, fencing epochs, contract generation transitions, transactional inbox/outbox, task capability issuance/validation, effect receipts/reconciliation, and semantic completion authority.

**PROPOSED response:** add these only through the staged Aether-owned control plane in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), after Phase 0 seam verification.
