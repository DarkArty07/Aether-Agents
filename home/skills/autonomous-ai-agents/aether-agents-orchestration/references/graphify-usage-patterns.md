# Graphify Usage Patterns — Discovered Through Testing

Last updated: 2026-06-02 (session testing feature/graphify-integration branch)

## Graph Overview

- **Nodes:** 23,942 | **Edges:** 41,209 | **Communities:** 1,513
- **Extraction:** 80% EXTRACTED (AST), 20% INFERRED (LLM semantic via deepseek-v4-flash)
- **Graph file:** `graphify-out/graph.json` (22.8 MB)
- **Provider:** Custom `aether-openai` in `.graphify/providers.json` → opencode-go v1 endpoint
- **Manifest:** `graphify-out/manifest.json` (293 KB) — tracks per-file mtime, ast_hash, semantic_hash

## Query Patterns — What Works Well

### 1. `graphify explain <exact-node-name>` — MOST RELIABLE

Precise node inspection with all connections in one call. Always use exact node names (not fuzzy).

```
graphify explain "ACPManager"
→ 48 connections: .delegate(), .send_message(), .spawn_agent(), ._spawn_process()
→ Used by: init_server(), server.py, consult_action.py, Test* classes
→ Community 42 (56 nodes including poll, delegate, close, cancel)
```

### 2. `get_neighbors <node-id>` — Import Tracing in ONE Call

Replaces manually opening 3-4 files and following imports.

```
get_neighbors("olympus_v3_server")
→ Imports from: acp_manager.py (ACPManager), aether_db.py, db.py
→ Contains handlers: _handle_talk_to, _handle_discover, _handle_aether_curate, etc.
```

### 3. `graph_stats` — Quick Health Check

Confirms graph is loaded and responding. Use as smoke test.

### 4. `god_nodes(top_n=N)` — Core Abstractions

Shows most-connected nodes. Currently dominated by Honcho types (datetime 656 edges, MessageCreateParams 153, SessionConfiguration 149).

## Pitfalls Discovered

### Pitfall A: BFS/DFS Queries Biased Toward Honcho + Skills

**Root cause:** Graph was generated from entire repo (`/home/prometeo/Aether-Agents`) including `home/skills/` (hundreds of skill files) and `honcho-server/` (large submodule). Honcho types dominate the node space.

**Symptoms:**
- `query_graph(question="acp delegate poll session")` → resolves "Session" to Honcho's Session class
- `query_graph(question="SOUL.md daimon configuration")` → matches unrelated "Configuration" from skill references
- All BFS traversals start from Honcho nodes, not Aether Agents core

**Workaround:** Use `get_node` with exact names first, then `get_neighbors`. Avoid BFS/DFS for Aether Agents architecture queries until graph is regenerated with focused scope.

### Pitfall B: `shortest_path` / `path` CLI Fail with Ambiguous Matches

**Root cause:** Concepts like "Hefesto", "SOUL.md", "delegate" appear in dozens of contexts (skill files, Daimon profiles, docs). The fuzzy matcher gets ambiguous results.

```
graphify path "Hefesto" "SOUL.md"
→ warning: source match was ambiguous (top score 748.214, runner-up 748.214)
→ warning: target match was ambiguous (top score 673.496, runner-up 673.496)
→ No path found
```

**Workaround:** Use exact node IDs (e.g., `olympus_v3_server`) instead of conceptual names.

### Pitfall C: Core Architecture Queries Drowned in Noise

**Symptom:** Searching for "delegate", "acp", "daimon" resolves to Honcho/Session instead of `olympus_v3` code.

**Root cause:** 1,321 files in extraction scope. Honcho-server submodule + 100+ skills dominate the keyword space.

**Fix:** Regenerate graph with focused scope excluding `home/skills/` and `honcho-server/`:
```bash
# Recommended: focused extraction on Aether Agents core
graphify extract src/ home/profiles/ --exclude home/skills/ honcho-server/ home/cache/
```

## Extraction Modes

### `graphify extract <path>` — Full (AST + LLM Semantic)
- Does both AST extraction AND LLM semantic inference
- Slow but produces INFERRED edges (20% of total)
- Use weekly or after major refactors
- Provider: uses `.graphify/providers.json` (aether-openai → deepseek-v4-flash)
- Flags: `--backend`, `--model`, `--mode deep`, `--max-workers`, `--token-budget`

### `graphify update <path>` — Incremental (AST Only)
- Re-extracts code files, updates graph WITHOUT LLM
- Fast — no API calls
- Use daily or pre-commit
- Safe: `--force` flag needed only if refactor removed code (fewer nodes)
- Does NOT add new INFERRED edges

### `graphify check-update <path>` — CI Integration
- Checks `needs_update` flag
- Cron-safe — returns exit code for scripting
- Use as pre-commit hook or CI check

### `graphify cluster-only <path>` — Rerun Clustering
- Re-clusters existing graph.json without re-extraction
- Use when extraction is fresh but communities need recalculation
- `--no-viz` for >5000 node graphs or CI

## CLI Quick Reference

| Command | Purpose | LLM? | Speed |
|---------|---------|------|-------|
| `graphify explain NODE` | Inspect a node + connections | No | Instant |
| `graphify path A B` | Shortest path between two nodes | No | Instant |
| `graphify update .` | Incremental AST re-extraction | No | Fast |
| `graphify extract .` | Full AST + LLM extraction | Yes | Slow |
| `graphify cluster-only .` | Re-cluster existing graph | No | Medium |
| `graphify check-update .` | CI: check if extraction needed | No | Instant |
| `graphify diagnose multigraph` | Report edge collapse risk | No | Fast |

## Provider Configuration

`.graphify/providers.json`:
```json
{
  "aether-openai": {
    "base_url": "https://opencode.ai/zen/go/v1",
    "default_model": "deepseek-v4-flash",
    "env_key": "OPENCODE_API_KEY",
    "model_env_key": "GRAPHIFY_AETHER_MODEL",
    "pricing": { "input": 0.0, "output": 0.0 },
    "temperature": 0,
    "max_tokens": 16384
  }
}
```

- Uses opencode-go endpoint (same as Hermes' main provider)
- `deepseek-v4-flash` for cost efficiency on LLM extraction
- `pricing: 0.0` because opencode-go bills by subscription, not per-token
- Override model via `GRAPHIFY_AETHER_MODEL` env var

## Key Insight: Token Reduction

Graphify compresses 1,321 files into a 22.8 MB graph.json. MCP tools return targeted subgraphs (typically 100-500 nodes per query) instead of raw file contents. For codebase exploration tasks, this replaces multiple `read_file` + `search_files` calls with a single MCP call.

**Example savings:**
- Before: `read_file(server.py)` + `search_files("import.*acp")` + `read_file(acp_manager.py)` + `search_files("ACPManager")` = 4 calls, ~15K tokens
- After: `get_neighbors("olympus_v3_server")` = 1 call, ~500 tokens

## Advanced Techniques — Discovered 2026-06-02

### Technique 1: shortest_path Works with Method Labels (Not Node IDs)

**Problem:** `shortest_path` fails with node IDs (e.g., `olympus_v3_server_handle_talk_to`) but works with method labels that include parentheses.

**Discovery process:**
- `get_node("_handle_talk_to")` → ID: `olympus_v3_server_handle_talk_to`
- `shortest_path(source="olympus_v3_server_handle_talk_to", target="...")` → "No node matching source"
- `shortest_path(source="_handle_talk_to()", target="._spawn_process()")` → Found! 3 hops

**Rule:** Use `get_node` to find the label (not the ID), then use that label in `shortest_path`. Labels with parentheses are the reliable format.

### Technique 2: context_filter Eliminates Skill/Doc Noise

**Problem:** BFS/DFS queries return Honcho types and skill documentation instead of core code.

**Solution:** Pass `context_filter` to filter edges by type:

| Query | Without Filter | With `context_filter=["call","method"]` |
|-------|---------------|----------------------------------------|
| "acp_manager delegate" | 224 nodes (Honcho Session, Message, etc.) | 3 nodes (acp_manager.py + 2 docs) |
| "spawn_agent process" | 224 nodes (mostly Honcho) | 3 nodes (focused on code) |

**Effective filter combinations:**
- `["call","method","contains"]` — code structure tracing
- `["imports","imports_from"]` — dependency analysis
- `["call"]` — runtime call graph only

**Rule:** Always add `context_filter` to `query_graph` when searching for code relationships. Omit it only for truly open-ended exploration.
