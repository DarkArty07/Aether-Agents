---
name: llm-model-benchmarking
description: "Benchmark LLM models on a custom Python conversation engine (OpenAI-compatible API) with verbatim logging, tool execution, and embeddable evaluation hooks. Controlled test cases with known expected outcomes. NOTE: Original tmux/hermes-agent approach was abandoned 2026-07-01 in favor of a custom engine — see llm-agent-benchmark-design skill for the architectural decision."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [benchmarking, evaluation, llm, hermes-agent, tokens, cost]
---

# LLM Model Benchmarking via Hermes Agent CLI

Benchmark multiple LLM models on a **single hermes-agent instance** to compare quality, cost, speed, and tool-usage. Uses tmux to drive the interactive CLI and `/status` to capture metrics — no custom instrumentation scripts needed.

## When to Use

- Comparing models on a hermes-agent instance (e.g., "which model works best for Asclepio?")
- Measuring token cost across models for the same conversation
- Evaluating quality of tool-calling behavior per model
- Any A/B model comparison where the agent's SOUL.md and MCP tools stay fixed

## When NOT to Use

- Academic benchmarks (MMLU, GSM8K) → use `evaluating-llms-harness` skill instead
- Single-model evaluation (no comparison) → just run the agent normally

## ARCHITECTURAL SHIFT (2026-07-01)

**The tmux/hermes-agent approach described in Steps 2-9 below has been ABANDONED.** The custom Python engine approach is now the recommended method.

**Why:** hermes-agent is opaque — you can't intercept every request/response pair for verbatim logging. tmux `capture-pane` gives fragments. `/status` gives approximate tokens. No hooks between turns for evaluation logic. Switching models requires config edits + restarts.

**What replaced it:** A custom Python engine using the `openai` library (OpenAI-compatible, pointed at LLM Gateway). Built as "Asclepio Motor v2" at `/home/prometeo/Asclepio-Motor/`. Full verbatim logging. Programmatic tool execution. Model switching via a single parameter or runtime API. Embeddable hooks between turns. Dual-endpoint architecture: `POST /assistant` (streaming for assistant-ui frontend) + `POST /api/chat` (headless JSON for benchmark scripts).

**STATUS: BUILT AND WORKING (2026-07-01).** Engine tested end-to-end: LLM calls, tool calling (buscar_doctores found real doctors in Mérida), alarm symptom detection (chest pain → 911), verbatim logging (4 log files in data/logs/), model switching, streaming protocol (assistant-transport), frontend rendering (localhost:3000).

**See `llm-agent-benchmark-design` → `references/conversation-engine-architecture.md` for the full built architecture (directory structure, endpoint specs, tool calling loop, logging format, hooks system).**

**See `llm-agent-benchmark-design` → `references/asclepio-motor-v2.md` for the specific implementation details and startup commands.**

The tmux-specific steps and pitfalls below remain as reference for the model verification, naming conventions, auth patterns, and test case design — all of which are still valid regardless of execution engine. But the execution itself should use the custom Python engine, not tmux + hermes chat.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Hermes (orchestrator)                      │
│  ┌─────────────────────────────────────┐    │
│  │ tmux session                        │    │
│  │  HERMES_HOME=<agent_home> hermes    │    │
│  │  ┌───────────────────────────────┐  │    │
│  │  │ Agent (SOUL.md + MCP tools)   │  │    │
│  │  │ Model: <being tested>         │  │    │
│  │  └───────────────────────────────┘  │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  For each turn:                             │
│  1. tmux send-keys "<user prompt>" Enter    │
│  2. Wait for response (poll tmux pane)      │
│  3. Capture output from pane                │
│                                             │
│  After all turns:                           │
│  4. tmux send-keys "/status" Enter          │
│  5. Parse token count, timing, tools used   │
│  6. Kill session, repeat with next model    │
└─────────────────────────────────────────────┘
```

## Step-by-Step Procedure

### Prerequisites

- The hermes-agent instance must have all target models listed in `config.yaml` under `custom_providers.<name>.models` (or the provider's native model list)
- The agent's SOUL.md and MCP tools must be configured and working
- tmux installed (`apt install tmux`)

### Step 0: Verify Model Availability on the Gateway

**CRITICAL — do this BEFORE proposing a model list to the user.** Never ask the user "is this model available?" — query the gateway yourself and present only confirmed models.

```bash
# Query to a shell variable with the correct name (e.g. $LLMGATEWAY_API_KEY)
# NEVER use literal placeholders like "***" — curl will send an empty Bearer token
export $(grep -v '^#' /path/to/hermes/home/.env | xargs) && \
curl -s "https://api.llmgateway.io/v1/models" \
  -H "Authorization: Bearer *** | \
  jq -r '.data[] | "\\(.family)\\t\\(.id)\\t\\(.name)"' | sort

## Model Families (as of 2026-07-01)
**Model selection methodology:**
1. Group results by `family` (openai, anthropic, google, deepseek, moonshot, xiaomi, etc.)
2. For each brand the user wants, identify the most recent "cheap" tier (flash/mini/haiku) and "expensive" tier (pro/opus/max) — pick the highest version number available
3. Present only the confirmed matrix — don't propose models you haven't verified exist on the gateway
4. Some brands don't have a cheap tier (e.g., Moonshot/Kimi only has k2.5 and k2.6 — both full-size; no flash/mini equivalent)
5. User may have preferences about which tier to use (e.g., "don't use haiku, use sonnet as the cheap one") — accommodate and re-verify

**See:**
- `references/gateway-model-catalog.md` — known model families, tiers, and selection examples
- `references/chat-completions-request.md` — pattern for securely querying the gateway with curl via Python execute_code

**Auth note:** The `/v1/models` endpoint may work without the Authorization header, but `/v1/chat/completions` will return HTTP 401 if auth is missing or malformed. Always confirm auth works by testing a chat completion call, not just a models list call.

### Step 1: Design Test Cases

Design **3-5 controlled test cases**. Each case has:

1. **User prompts** (5 turns per case) — written vague, like a real user would speak. NOT clinical/precise.
2. **Expected outcome** — the correct diagnosis/orientation, specialist, and tool calls the agent SHOULD make.
3. **Evaluation criteria** — what to score (see Step 6).

**Example test case structure:**
```
Case 1: Migraine
  Turn 1: "hola, me siento mal"
  Turn 2: "me duele la cabeza, del lado derecho"
  Turn 3: "como desde ayer, y late, como que palpita"
  Turn 4: "la luz me molesta mucho"
  Turn 5: "estoy en Guadalajara"
  
  Expected:
    - Orientation: migraña (cephalea vascular)
    - Specialist: neurología
    - Tools: buscar_doctores(Guadalajara, neurología)
    - Alarm check: should ask about nausea/vomiting, intensity
    - OTC suggestion: paracetamol/ibuprofeno
```

### Step 2: Start a tmux Session with the Agent

```bash
# Source the API key (REQUIRED — hermes chat needs it for the provider)
export $(grep -v '^#' /path/to/agent/.env | xargs)

# Create detached tmux session and launch hermes from the agent directory
tmux new-session -d -s <session_name>
tmux send-keys -t <session_name> \
  "cd /path/to/agent && hermes chat --provider custom:llmgateway -m <model_name>" Enter

# Wait for startup (skills loading, MCP init)
sleep 5
tmux capture-pane -t <session_name> -p
```

**The working pattern:** `cd` to the agent directory (where SOUL.md and config.yaml live), export the API key, then `hermes chat --provider <name> -m <model>`. The `-m` flag overrides the model in config.yaml — no need to edit files between runs. The `--provider` flag is required when using a custom_provider like `custom:llmgateway`.

**Verify:** The status bar should show the correct model name. The startup banner shows `X MCP servers` (verify the expected count).

### Step 3: (Optional) Switch Model

If the agent's default model isn't the one you want to test first, switch it:

```bash
tmux send-keys -t <session_name> "/model <model_name>" Enter
sleep 2
```

### Step 4: Run Test Cases

For each turn in a test case:

```bash
# Send the user prompt
tmux send-keys -t <session_name> "<user prompt text>" Enter

# Wait for the agent to respond (adjust sleep based on model speed)
sleep 8

# Capture the full pane output
tmux capture-pane -t <session_name> -p -S -50
```

**Timing:** The status bar shows `⏲ Xs` — this is the cumulative session time. For per-turn timing, note the `⏲` value before and after each turn.

**Pitfall — sleep duration:** Different models have different response times. If the capture shows the response is still generating (spinner visible), increase the sleep. 8-10 seconds is usually enough for most models. For slow models, use 15-20s.

### Step 5: Capture Metrics with /status

After completing all turns of a test case (or all test cases for a model):

```bash
tmux send-keys -t <session_name> "/status" Enter
sleep 3
tmux capture-pane -t <session_name> -p -S -50
```

**What `/status` returns:**

| Field | Where | What it means |
|-------|-------|---------------|
| `Tokens: N` | /status output | Total tokens consumed (prompt + completion, cumulative) |
| `ctx X/128K` | Status bar | Current context window usage |
| `[████░░] X%` | Status bar | Context window percentage |
| `⏲ Xs` | Status bar | Total session elapsed time |
| `Tools used: tool×N` | /status output | Which MCP tools were called and how many times |
| `Session recap` | /status output | Turn count, last message summary |
| `Title` | /status output | Auto-generated session title |

### Step 6: Record Results

For each model × test case, record:

```
Model: <name>
Case: <case name>
Tokens total: <from /status>
Context peak: <from status bar>
Time total: <from ⏲>
Tools called: <from /status>
Diagnosis accuracy: 0-3 (0=wrong, 1=vague, 2=close, 3=correct)
Specialist correct: Yes/No/Parcial
Alarm handling: Yes/No (did it check for emergency symptoms?)
Flow quality: 1-5 (structure, empathy, correct order, no skipped steps)
Cost: tokens × price_per_token (look up model pricing)
```

### Step 7: Switch to Next Model and Repeat

**Use fresh sessions (Option B) — do NOT reuse the same session across models.** Context window contamination from model A's conversation gives model B an unfair advantage or disadvantage.

```bash
# Kill previous session
tmux kill-session -t <session_name>

# Start fresh with next model — just change the -m flag
tmux new-session -d -s <next_session_name>
tmux send-keys -t <next_session_name> \
  "cd /path/to/agent && hermes chat --provider custom:llmgateway -m <next_model>" Enter
sleep 5
```

**The `-m MODEL` flag is the only thing that changes between runs.** Same agent directory, same SOUL.md, same MCP server, same provider. Do NOT create separate agent configs per model — see Pitfall 11.

### Step 8: Calculate Cost

The LLM Gateway response includes `usage.cost` directly in the response — no need to calculate from token prices:

```bash
jq '.usage.cost' /path/to/response.json
```

If you need to verify or the cost field isn't available, use:

```bash
# Token pricing varies by model. Look up at the provider's pricing page.
# Formula:
#   cost = (prompt_tokens × input_price_per_1K) + (completion_tokens × output_price_per_1K)
#
# /status gives TOTAL tokens (prompt + completion combined).
# If the provider's pricing differs for input vs output, you need the breakdown.
# The status bar's "ctx X/128K" gives current context (≈ prompt tokens for last turn).
# Estimate: completion_tokens ≈ total_tokens - context_tokens
```

### Step 9: Cleanup

```bash
tmux send-keys -t <session_name> "/exit" Enter
sleep 2
tmux kill-session -t <session_name> 2>/dev/null
```

## Evaluation Criteria (Recommended)

| Criterion | Scale | How to measure |
|-----------|-------|----------------|
| Diagnosis accuracy | 0-3 | Compare agent's orientation to expected diagnosis |
| Specialist routing | Yes/No/Parcial | Did it suggest the right medical specialty? |
| Alarm symptom handling | Yes/No | Did it check for emergency symptoms before proceeding? |
| Tool usage correctness | Yes/No | Did it call the right MCP tools at the right time? |
| Conversational flow | 1-5 | Structure, empathy, clarity, no skipped steps |
| Token efficiency | count | Lower is better (same quality) |
| Response speed | seconds | Lower is better |
| Cost | USD | tokens × pricing |

## Pitfalls

### Pitfall 1 — Don't use `talk_to` for benchmarking
The `talk_to` MCP tool (delegate/open/message/poll) does NOT expose token counts from the underlying LLM calls. Use tmux + interactive CLI + `/status` instead.

### Pitfall 2 — ~~Don't write a custom API script~~ NOW: DO write a custom engine

**SUPERSEDED (2026-07-01).** This pitfall originally said "Reinventing the agent loop is unnecessary. The hermes CLI already does all of this." That advice was wrong for benchmarking. The hermes CLI is opaque — it hides request/response pairs, gives approximate token counts, and doesn't support embeddable evaluation hooks between turns.

**New guidance:** DO write a custom Python conversation engine. Use the `openai` library pointed at your LLM Gateway. Load SOUL.md as system prompt. Define tools as function schemas. Execute tools programmatically. Log every request AND response verbatim. This gives you full control, exact token counts from the API `usage` field, and the ability to embed scoring/gates/metrics between turns.

**If the user also wants a frontend** (Chris does): Use assistant-ui (React/Next.js) for the chat UI + the `assistant-stream` Python library for the streaming protocol bridge. Build a dual-endpoint backend: `POST /assistant` (streaming for the frontend) + `POST /api/chat` (headless JSON for benchmark scripts). Both endpoints share the same engine. See Asclepio Motor v2 at `/home/prometeo/Asclepio-Motor/` for a working example.

See `llm-agent-benchmark-design` → `references/conversation-engine-architecture.md` for the full built architecture.

### Pitfall 3 — Fresh session per model
Don't test model B in the same session as model A. The context window will contain model A's previous turns, giving model B an unfair advantage (or disadvantage). Kill the tmux session and start fresh for each model.

### Pitfall 4 — Vague user prompts, not clinical ones
Write test prompts as a real user would speak: "me duele la cabeza" not "tengo cefalea unilateral pulsátil de 8/10 en la escala visual análoga". The benchmark tests whether the model can extract the clinical picture from natural language.

### Pitfall 5 — Sleep timing must account for tool calls
When the agent calls MCP tools (buscar_doctores, buscar_cerca), the response takes longer. Use 10-15s sleep for turns that should trigger tool calls, vs 5-8s for pure conversational turns.

### Pitfall 6 — `/status` tokens are cumulative
The `Tokens: N` field shows the TOTAL for the entire session, not per-turn. To get per-turn tokens, run `/status` after each turn and subtract. Or note the delta between consecutive `/status` calls.

### Step 1b: Design the Full Benchmark with a Model Caro (API Pattern)

For complex benchmarks, use an expensive reasoning model to design the full evaluation framework. This produces a richer scoring system, better test cases, and more thorough protocol than manual design.

**When to use this pattern:**
- Benchmarking 6+ models across multiple brands
- The agent has complex tool-calling behavior (MCP tools, multi-step flows)
- You need a scoring system with safety gates, weighted dimensions, and penalties
- The evaluation criteria span quantitative (tokens, time, cost) AND qualitative (tone, empathy, diagnostics)

**Procedure:**

1. **Write a comprehensive design prompt** — include the agent's full SOUL.md, all MCP tool definitions, the test cases with their vague turns, the model matrix, and the desired deliverables (scoring system, planilla, protocol, ambiguity guide, expected analysis). Save to a `.md` file.

2. **Deploy the prompt via LLM Gateway API** (use Hefesto for the curl request):
```bash
export $(grep -v '^#' <project>/.env | xargs)
jq -n --arg prompt "$(cat <design-prompt>.md)" '{
  model: "claude-opus-4-8",
  messages: [{role: "user", content: $prompt}],
  temperature: 0.7,
  max_tokens: 32000
}' | curl -s -X POST "https://api.llmgateway.io/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer *** \
  -d @- --max-time 300 -o <response>.json
```

3. **Extract the design**: `jq -r '.choices[0].message.content' <response>.json > <design>.md`

4. **Key constraints for the design prompt:**
   - Tell the model caro the output is for a human evaluator (Chris) who will measure ambiguity
   - Specify exact deliverables: scoring formula, planilla columns, protocol steps, ambiguity criteria
   - Include the agent's full SOUL.md — the model needs to understand the agent's behavior
   - Specify what the model should NOT do (no SWE-bench, no bug-fixing, etc.)
   - Safety = gate (veto), quality = scale (0-100). Never average them.

5. **The model caro should deliver:**
   - **A. Scoring system** — weights per dimension, formula, penalties, thresholds
   - **B. Evaluation spreadsheet** — column layout for manual data entry
   - **C. Execution protocol** — step-by-step, including tmux setup, error handling, execution order
   - **D. Ambiguity criteria** — guide for the human to judge turn vagueness
   - **E. Expected analysis** — what conclusions should be extractable

**See `references/asclepio-benchmark-design.md` for a complete real-world example** with 5 test cases, dual-layer scoring (safety gates + quality), multi-sheet planilla, and tmux protocol.

### Pitfall 7 — Model names use hyphens (`-`), not dots (`.`)

Model IDs on the LLM Gateway use hyphens between segments (e.g., `claude-opus-4-8`, `gpt-5-5-pro`, `deepseek-v4-flash`), NOT dots (`claude-opus-4.8`, `gpt-5.5-pro`). If you use dots, the gateway returns HTTP 400 with `"Requested model X not supported"`. Always check the model `id` exactly as returned by `/v1/models` — that's the string you must use in the chat completions request.

Exception: some model names contain dots as sub-versioning within a segment (e.g., `kimi-k2.5`). The rule is: brand-family-version segments use hyphens, only internal version strings within a segment may use dots. When in doubt, copy the exact `id` field from the models list.

**How to verify:** Query `/v1/models`, filter by family, and extract the `id` field:
```bash
curl -s https://api.llmgateway.io/v1/models | jq -r '.data[] | select(.family=="anthropic") | .id'
```

### Pitfall 8 — Auth: `/v1/models` may not require a key, but `/v1/chat/completions` always does

The models listing endpoint may work without authentication, but the chat completions endpoint will return HTTP 401 `"No API key provided"` if the `Authorization` header is missing or malformed. Always test a chat completion call to confirm auth is set up correctly, not just a models list call.

### Pitfall 9 — Never ask the user to verify model availability
The user expects you to query the gateway yourself. Do not propose a model matrix and then ask "is this available?" — that wastes a round-trip and signals you didn't do your homework. Always run Step 0 first, then present only confirmed models. If a model the user mentioned isn't on the gateway, say so proactively with the closest alternative.

### Pitfall 10 — Don't over-design test cases before getting user approval
The user (Chris) wants to approve the cases AND their turn-level vagueness before the benchmark begins. Present the cases with all their turns, explain what each case evaluates, and get explicit approval before proceeding to scoring design or execution. Ambiguity is measured by the human, not the benchmark.

### Pitfall 11 — DON'T create separate agent configs per model
You do NOT need 12 agent configuration directories for a 12-model benchmark. One SOUL.md, one MCP server, one config.yaml. Just override the model via CLI:

```bash
cd /path/to/agent
export $(grep API_KEY .env)
hermes chat --provider custom:llmgateway -m <model_name>
```

Between models, kill the tmux session and restart fresh with a different `-m` flag. Creating separate configs wastes time and violates the "single source of truth" principle — all models MUST share the same SOUL.md and MCP tools for a fair comparison. The user will NOT appreciate being told to create 12 duplicate agent directories.

### Pitfall 12 — Verify model availability BEFORE proposing, not after
Query the gateway catalog (/v1/models) and present only confirmed models. Do NOT propose a model matrix and then ask "is this available?" — that wastes a round-trip and signals you didn't do your homework. If a model the user mentioned isn't on the gateway, state it proactively with the closest alternative.

### Pitfall 13 — tmux send-keys: send text and Enter separately
When driving `hermes chat` via tmux, send the message text first, then send `Enter` as a separate command. Sending them together can cause the text to arrive before the CLI is ready to accept input. Also, `/status` must only be sent AFTER the model's response is fully complete — if sent too early, it arrives as a message to the model instead of a CLI command.

**Working pattern:**
```bash
tmux send-keys -t <session> "patient message text"
sleep 1
tmux send-keys -t <session> Enter
sleep 10  # wait for response completion
tmux send-keys -t <session> "/status"
sleep 1
tmux send-keys -t <session> Enter
sleep 3
tmux capture-pane -t <session> -p -S -50
```

### Pitfall 14 — HERMES_HOME and API key must be exported before hermes chat
`hermes chat` fails with "Provider X is set in config.yaml but no API key was found" if the API key isn't in the environment. Source the agent's `.env` before launching:

```bash
cd /path/to/agent
export $(grep -v '^#' .env | xargs)
hermes chat --provider custom:llmgateway -m <model>
```

For tmux sessions, export inline. Do NOT assume HERMES_HOME is inherited from the orchestrator — it points to the orchestrator's home, not the agent's.

### Pitfall 15 — The orchestrator (Hermes) does the qualitative evaluation, not the user
Chris does NOT want to evaluate responses manually. Division of labor:
- **Script**: captures tokens, time, tool calls, raw responses automatically
- **Hermes**: reads responses, applies rubric (D1-D6, penalties, safety flags), fills granular.csv + maestra.csv, writes report
- **Chris**: reviews final report, validates ambiguity if desired, makes deployment decision

Do NOT design the benchmark assuming the user fills in qualitative scores. The user's role is oversight and ambiguity validation only.

### Pitfall 16 — /reset between cases within a model, not just between models

Pitfall 3 says to kill the tmux session between models. But you ALSO need to /reset between CASES within the same model. If Case 1's context bleeds into Case 2, the model gets an unfair advantage (it remembers the previous patient's symptoms and the tools it already called).

```bash
tmux send-keys -t <session> "/reset" Enter
sleep 4
# /reset shows a menu — select option 1 for full reset
tmux send-keys -t <session> "1" Enter
sleep 3
# Verify: status bar should show 0/128K and [░░░░░░░░░░] 0%
tmux capture-pane -t <session> -p | grep "New session"
```

If the model says "no tengo los detalles de lo que platicamos antes" on Case 2 Turn 1, the reset WORKED (fresh session). If it remembers the previous patient, the reset FAILED.

### Pitfall 17 — tmux capture-pane -S -50 is too small for full transcripts

The default `-S -50` captures only 50 lines of scrollback. For agent responses with tool calls (buscar_doctores returns multi-line results), 50 lines misses the beginning of the response. Use `-S -200` minimum, or `-S -` for unlimited scrollback. See `llm-agent-benchmark-design` Principle 1 for why full transcripts are mandatory — without them, qualitative evaluation is impossible and the benchmark gets scrapped.

### Pitfall 18 — /status after EVERY turn, not just at case end

Pitfall 6 notes tokens are cumulative. But if you only run /status at the end of the case, you lose per-turn token data. Without per-turn deltas, you can't identify which turns triggered tool calls or which were most expensive. Run `/status` after EVERY turn and save the output to disk immediately.

### Related Skill: llm-agent-benchmark-design

For methodology and design pitfalls (save full transcripts, designer ≠ evaluated model, qualitative evaluation before declaring results, domain expert validation, convergence tracking), see the `llm-agent-benchmark-design` skill. This skill covers the MECHANICS (tmux, /status, model IDs, auth); that skill covers the METHODOLOGY (what to measure, when to evaluate, how to avoid bias). Both are needed for a successful benchmark.

### Documentation Structure for Benchmark Projects
All benchmark artifacts in a self-contained folder for future refinement:

```
<project>/benchmark/
├── README.md              # What it is, methodology, how to reproduce
├── DESIGN.md              # Model-caro design (scoring, rubrics, protocol)
├── MODELOS.md             # Model matrix, prices, justification
├── CASOS.md               # Test cases with turns and evaluation criteria
├── cases/
│   ├── caso1.txt ... caso5.txt   # 5 turns per file, 1 per line (for script)
├── ejecutar.sh            # tmux + /status automation script
├── results/
│   ├── maestra.csv        # 12 rows: final score + classification + safety flag
│   ├── granular.csv       # 60 rows: D1-D6 + penalties per (model x case)
│   ├── por_turno.csv      # 300 rows: tokens/time/tools per (model x case x turn)
│   └── raw/
│       └── turnos.jsonl   # 300 lines: full response + status per turn (auditing)
└── analysis/
    └── reporte.md         # Final analysis: ranking, Pareto, safety blacklist
```

**Why JSONL for raw:** Each line captures full response, status output, and tool calls without truncation. Appendable (`>>`) — script adds one line per turn. CSV truncates long text; JSONL preserves everything for audit.

## User Preferences (Chris)

- **Controlled and repeatable:** Test cases must have known expected outcomes. No subjective free-form testing.
- **Vague prompts:** User prompts should read like a real patient, not a medical textbook.
- **5 turns per case:** Enough for the agent to gather symptoms, orient, and use tools.
- **Token cost is critical:** Token measurement is a first-class requirement, not optional.
- **All metrics matter:** Diagnosis accuracy, specialist routing, flow quality, speed, AND cost.
- **Verify gateway yourself:** Never ask the user to confirm model availability — query the gateway catalog and present only confirmed models.
- **Tier preferences:** For Claude, prefers sonnet as the "cheap" tier (not haiku). Rejects outdated model versions — always pick the most recent available.
- **Brand coverage:** Wants benchmark coverage across major brands (OpenAI, Anthropic, Google, DeepSeek, Moonshot/Kimi, Xiaomi/MiMo) with cheap + expensive tier per brand.
