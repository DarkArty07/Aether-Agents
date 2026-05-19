# MCP Delegation Content Size Limits

## Problem

When Hermes needs to pass large content (e.g., a full SOUL.md of 15K-24K chars) to a Daimon via `talk_to(action="delegate")`, the prompt can exceed practical limits. Combined with Hermes' rule against writing files, this creates a **double bind**: Hermes can't write the file, and Hefesto can't guess the content.

This has caused problems in multiple sessions (Athena rework, SOUL.md transfers).

## Investigation Results (2026-05-19)

### 1. No `maxLength` in MCP Tool Schema

The `talk_to` tool schema in `olympus_v3/server.py` defines the `prompt` parameter as `"type": "string"` with **no `maxLength` constraint**. The MCP protocol (JSON-RPC over stdio) also has no inherent message size limit.

### 2. `tool_output.max_bytes: 50,000` — Response Truncation Only

Located in `hermes_cli/config.py` (default config). This truncates **tool output** (what Daimons return to Hermes), NOT **tool input** (the prompt Hermes sends).

```yaml
# Default config
tool_output:
  max_bytes: 50_000       # terminal output cap (chars)
  max_lines: 2_000        # read_file pagination cap
  max_line_length: 2_000  # per-line cap in read_file
```

For large context models (200K+), the recommended setting is:
```yaml
tool_output:
  max_bytes: 150_000
  max_lines: 5_000
```

### 3. ACP `outputByteLimit` — Daimon Output Truncation

The ACP schema (`acp/schema.py`) has an `outputByteLimit` field that truncates the **Daimon's response** when it exceeds the limit. This is also output-side only, not prompt-side.

### 4. Model Output Token Limit — The Real Bottleneck

The actual bottleneck for large delegation prompts is the **model's output token limit**. When Hermes (the LLM) generates a tool call like `talk_to(prompt="<15K+ chars>")`, the entire prompt text must fit within the model's output token limit. If the model's max output tokens can't fit the full tool call parameter, it gets truncated.

**Concrete model data** (from `models_dev_cache.json` per profile, loaded by `agent/models_dev.py` `get_model_capabilities()`):
- **glm-5.1** (opencode-go): context=202,752, output=32,768 tokens (~90K chars)
- **glm-5** (opencode-go): context=202,752, output=32,768 tokens

The `ModelCapabilities` dataclass defaults are: `context_window=200,000`, `max_output_tokens=8,192`. Per-model overrides come from the models.dev API cache.

**No local config knob**: there is no `max_output_tokens` or `max_completion_tokens` in hermes config.yaml for the orchestrator model. The output limit is determined by the provider/model, not a local setting. To get more output tokens, you'd need to switch to a model with a higher limit or add a provider-level override.

**For context**: 32,768 output tokens ≈ 90,000 chars. A SOUL.md of 15-24K chars = 5-8K tokens, well within the limit. The bottleneck is more likely `tool_output.max_bytes` (response truncation) than the output token limit for this model.

### 5. 3-Layer Tool Result Persistence System

hermes-agent has a 3-layer system for managing tool result size (`tools/budget_config.py`):

| Layer | What | Default | Source |
|-------|------|---------|--------|
| Per-tool registry | `registry.get_max_result_size(tool_name)` | Varies per tool | `tools/registry.py` |
| Per-result persistence | `maybe_persist_tool_result()` | 100,000 chars | `DEFAULT_RESULT_SIZE_CHARS` |
| Per-turn budget | Total across all tool results in one turn | 200,000 chars | `DEFAULT_TURN_BUDGET_CHARS` |

When a single tool result exceeds the per-result threshold (100K), hermes writes it to a file and replaces it with a preview (1,500 chars by default, `DEFAULT_PREVIEW_SIZE_CHARS`). When the total across all results in one turn exceeds 200K, the largest non-persisted results are persisted first.

**This means**: Daimon responses larger than 100K chars get written to disk and replaced with a preview + file path. The model never sees the full content — it sees a truncated preview and must `read_file` the persisted path to get the rest.

### 6. Other Config Limits

```yaml
file_read_max_chars: 100_000   # Default — rejects single reads > 100K chars
                               # Large context models: 200_000
memory_char_limit: 2_200       # ~800 tokens
user_char_limit: 1_375          # ~500 tokens
```

Environment variable: `MAX_MCP_OUTPUT_TOKENS` — caps MCP tool result size (prevents context flooding).

## Diagnosis Checklist

When delegation of large content fails, check in this order:

1. **model output tokens** — Does the prompt fit within the model's `max_output_tokens`? Check `models_dev_cache.json` for the model's output limit. For glm-5.1: 32,768 tokens (~90K chars) — plenty for SOUL.md transfers.
2. **`tool_output.max_bytes`** — Is the Daimon's response being truncated? Default is 50K chars. Increase to 150K-200K for large-context models.
3. **Result persistence threshold** — Is the result exceeding 100K chars and getting written to disk (preview only)? This is `DEFAULT_RESULT_SIZE_CHARS` and is usually fine.
4. **MCP protocol** — No inherent limit. The `talk_to` prompt parameter has no `maxLength` in the schema.

## Recommended Fix

**Primary** (user's preferred approach): Increase `tool_output.max_bytes` in `config.yaml` to accommodate Daimon responses that include large file contents:

```yaml
# Current (default)
tool_output:
  max_bytes: 50_000
  max_lines: 2_000
  max_line_length: 2_000

# Recommended for 128K+ context models (Aether Agents)
tool_output:
  max_bytes: 200_000    # was 50K — allows full SOUL.md transfers
  max_lines: 5_000
  max_line_length: 2_000
```

This is single-config change, no code modifications needed.

**For delegation prompts specifically**: The model output token limit (32K for glm-5.1) is unlikely the bottleneck — SOUL.md transfers are 15-24K chars = 5-8K tokens, well within the 32K output limit. If a different model with lower output limits is used, workarounds:

1. **File reference pattern**: Include exact file references (path + line ranges) in delegation prompts so Hefesto can `read_file` the target content himself
2. **Future architectural fix**: Allow Hermes to write to designated project paths (not "implementing" — preparing context for Daimons)
3. **Future option**: A `talk_to` prompt-file mode where Hermes writes context to a temp file and the Daimon reads it

## Affected Workflows

| Workflow | Impact | Workaround |
|----------|--------|------------|
| SOUL.md rewrites (full content transfer) | HIGH — can't send 15-24K chars inline | File references + Hefesto reads |
| Config file updates (full content transfer) | MEDIUM — configs are smaller | Usually fits in prompt |
| Design docs (full content transfer) | HIGH — design docs can be 5K+ chars | File references |
| Instructions-only delegation | LOW — structured instructions are <2K chars | N/A |

## Architecture Impact

This double bind (Hermes can't write + Daimon can't guess) affects every Daimon rework where SOUL.md needs to be rewritten. The v0.11.0+ workflow is: Hermes designs the SOUL.md content → Hefesto implements it. Without a way to transfer the content, Hermes must rely on detailed instructions + file references.