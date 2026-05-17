---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.0.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---

# Hermes Agent

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Hermes different:

- **Self-improving through skills** — Hermes learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 10+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Hermes instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Hermes for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Hermes Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://hermes-agent.nousresearch.com/docs/

**PREFERENCE:** When looking up documentation for any framework, library, or project, ALWAYS use Context7 MCP (`mcp_context7_resolve_library_id` → `mcp_context7_query_docs`) instead of searching the filesystem or doing a generic `web_search`. Context7 is faster and more accurate for official docs. Only fall back to `web_search` or `web_extract` when Context7 doesn't have the library or the answer isn't in the indexed docs.

## Quick Start

```bash
# Install (v0.14.0+ — PyPI)
pip install hermes-agent

# Alternative: shell installer (Linux/macOS/WSL2)
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Alternative: Windows PowerShell (early beta)
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex

# Interactive chat (default)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard
hermes setup

# Change model/provider
hermes model

# Check health
hermes doctor
```

---

## CLI Reference

### Global Flags

```
hermes [flags] [command]

  --version, -V             Show version
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --pass-session-id         Include session ID in system prompt
```

No subcommand defaults to `chat`.

### Chat

```
hermes chat [flags]
  -q, --query TEXT          Single query, non-interactive
  -m, --model MODEL         Model (e.g. anthropic/claude-sonnet-4)
  -t, --toolsets LIST       Comma-separated toolsets
  --provider PROVIDER       Force provider (openrouter, anthropic, nous, etc.)
  -v, --verbose             Verbose output
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --source TAG              Session source tag (default: cli)
```

### Configuration

```
hermes setup [section]      Interactive wizard (model|terminal|gateway|tools|agent)
hermes model                Interactive model/provider picker
hermes config               View current config
hermes config edit          Open config.yaml in $EDITOR
hermes config set KEY VAL   Set a config value
hermes config path          Print config.yaml path
hermes config env-path      Print .env path
hermes config check         Check for missing/outdated config
hermes config migrate       Update config with new options
hermes login [--provider P] OAuth login (nous, openai-codex)
hermes logout               Clear stored auth
hermes doctor [--fix]       Check dependencies and config
hermes status [--all]       Show component status
```

### Tools & Skills

```
hermes tools                Interactive tool enable/disable (curses UI)
hermes tools list           Show all tools and status
hermes tools enable NAME    Enable a toolset
hermes tools disable NAME   Disable a toolset

hermes skills list          List installed skills
hermes skills search QUERY  Search the skills hub
hermes skills install ID    Install a skill (ID can be a hub identifier OR a direct https://…/SKILL.md URL; pass --name to override when frontmatter has no name)
hermes skills inspect ID    Preview without installing
hermes skills config        Enable/disable skills per platform
hermes skills check         Check for updates
hermes skills update        Update outdated skills
hermes skills uninstall N   Remove a hub skill
hermes skills publish PATH  Publish to registry
hermes skills browse        Browse all available skills
hermes skills tap add REPO  Add a GitHub repo as skill source
```

### MCP Servers

```
hermes mcp serve            Run Hermes as an MCP server
hermes mcp add NAME         Add an MCP server (--url or --command)
hermes mcp remove NAME      Remove an MCP server
hermes mcp list             List configured servers
hermes mcp test NAME        Test connection
hermes mcp configure NAME   Toggle tool selection
```

### Gateway (Messaging Platforms)

```
hermes gateway run          Start gateway foreground
hermes gateway install      Install as background service
hermes gateway start/stop   Control the service
hermes gateway restart      Restart the service
hermes gateway status       Check status
hermes gateway setup        Configure platforms
```

Supported platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Mattermost, Home Assistant, DingTalk, Feishu, WeCom, BlueBubbles (iMessage), Weixin (WeChat), API Server, Webhooks. Open WebUI connects via the API Server adapter.

Platform docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
hermes sessions list        List recent sessions
hermes sessions browse      Interactive picker
hermes sessions export OUT  Export to JSONL
hermes sessions rename ID T Rename a session
hermes sessions delete ID   Delete a session
hermes sessions prune       Clean up old sessions (--older-than N days)
hermes sessions stats       Session store statistics
```

### Cron Jobs

```
hermes cron list            List jobs (--all for disabled)
hermes cron create SCHED    Create: '30m', 'every 2h', '0 9 * * *'
hermes cron edit ID         Edit schedule, prompt, delivery
hermes cron pause/resume ID Control job state
hermes cron run ID          Trigger on next tick
hermes cron remove ID       Delete a job
hermes cron status          Scheduler status
```

### Webhooks

```
hermes webhook subscribe N  Create route at /webhooks/<name>
hermes webhook list         List subscriptions
hermes webhook remove NAME  Remove a subscription
hermes webhook test NAME    Send a test POST
```

### Profiles

```
hermes profile list         List all profiles
hermes profile create NAME  Create (--clone, --clone-all, --clone-from)
hermes profile use NAME     Set sticky default
hermes profile delete NAME  Delete a profile
hermes profile show NAME    Show details
hermes profile alias NAME   Manage wrapper scripts
hermes profile rename A B   Rename a profile
hermes profile export NAME  Export to tar.gz
hermes profile import FILE  Import from archive
```

**⚠ Reserved profile name "hermes":** `hermes profile alias hermes` fails with `Error: 'hermes' is a reserved name`. The workaround is to create the wrapper script manually — see `templates/profile-alias-wrapper.sh`. A bare symlink silently uses the default profile instead of the named one, which is the #1 cause of "my SOUL.md isn't loading" bugs.

**⚠ Wrapper-script alias conflict (THE #2 CAUSE OF PROFILE ISSUES):** If `/home/YOURUSER/.local/bin/hermes` is a custom bash wrapper that injects `-p hermes`, then `hermes profile alias <name>` creates scripts that call `exec hermes -p <name>`, which expands to `exec hermes -p hermes -p <name>`. The pre-parser `_apply_profile_override()` takes the first `-p` (`hermes`), strips it from argv, and argparse then sees `<name>` as a positional subcommand → `error: invalid choice: '<name>'`. **Fix:** All profile alias scripts must call the venv binary directly, NOT via the `hermes` wrapper. Template: `exec /home/YOURUSER/.hermes/hermes-agent/venv/bin/hermes -p <name> "$@"`, plus `export HERMES_HOME=/home/YOURUSER/Aether-Agents/home`. Never use `exec hermes -p <name>` in an alias script if the `hermes` command is itself a wrapper.

### Credential Pools

```
hermes auth add             Interactive credential wizard
hermes auth list [PROVIDER] List pooled credentials
hermes auth remove P INDEX  Remove by provider + index
hermes auth reset PROVIDER  Clear exhaustion status
```

### Other

```
hermes insights [--days N]  Usage analytics
hermes update               Update to latest version
hermes pairing list/approve/revoke  DM authorization
hermes plugins list/install/remove  Plugin management
hermes honcho setup/status  Honcho memory integration (requires honcho plugin)
hermes memory setup/status/off  Memory provider config
hermes completion bash|zsh  Shell completions
hermes acp                  ACP server (IDE integration)
hermes claw migrate         Migrate from OpenClaw
hermes uninstall            Uninstall Hermes
```

---

## Slash Commands (In-Session)

Type these during an interactive chat session.

### Session Control
```
/new (/reset)        Fresh session
/clear               Clear screen + new session (CLI)
/retry               Resend last message
/undo                Remove last exchange
/title [name]        Name the session
/compress            Manually compress context
/stop                Kill background processes
/rollback [N]        Restore filesystem checkpoint
/background <prompt> Run prompt in background
/queue <prompt>      Queue for next turn
/resume [name]       Resume a named session
```

### Configuration
```
/config              Show config (CLI)
/model [name]        Show or change model
/personality [name]  Set personality
/reasoning [level]   Set reasoning (none|minimal|low|medium|high|xhigh|show|hide)
/verbose             Cycle: off → new → all → verbose
/voice [on|off|tts]  Voice mode
/yolo                Toggle approval bypass
/skin [name]         Change theme (CLI)
/statusbar           Toggle status bar (CLI)
```

### Tools & Skills
```
/tools               Manage tools (CLI)
/toolsets            List toolsets (CLI)
/skills              Search/install skills (CLI)
/skill <name>        Load a skill into session
/cron                Manage cron jobs (CLI)
/reload-mcp          Reload MCP servers
/plugins             List plugins (CLI)
```

### Gateway
```
/approve             Approve a pending command (gateway)
/deny                Deny a pending command (gateway)
/restart             Restart gateway (gateway)
/sethome             Set current chat as home channel (gateway)
/update              Update Hermes to latest (gateway)
/platforms (/gateway) Show platform connection status (gateway)
```

### Utility
```
/branch (/fork)      Branch the current session
/fast                Toggle priority/fast processing
/browser             Open CDP browser connection
/history             Show conversation history (CLI)
/save                Save conversation to file (CLI)
/paste               Attach clipboard image (CLI)
/image               Attach local image file (CLI)
```

### Info
```
/help                Show commands
/commands [page]     Browse all commands (gateway)
/usage               Token usage
/insights [days]     Usage analytics
/status              Session info (gateway)
/profile             Active profile info
```

### Exit
```
/quit (/exit, /q)    Exit CLI
```

---

## Key Paths & Config

```
~/.hermes/config.yaml       Main configuration (DEFAULT profile only)
~/.hermes/.env              API keys and secrets (DEFAULT profile only)
$HERMES_HOME/skills/        Installed skills
~/.hermes/sessions/         Session transcripts
~/.hermes/logs/             Gateway and error logs
~/.hermes/auth.json         OAuth tokens and credential pools
~/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `~/.hermes/profiles/<name>/` with the same layout. **Always run `hermes config path` to find the ACTIVE profile directory** — it may NOT be `~/.hermes/`. When using `hermes -p <name>`, the profile home is typically `~/Aether-Agents/home/profiles/<name>/` and contains config.yaml, .env, SOUL.md, memories/, skills/, sessions/, cron/, logs/, state.db. The installation directory (`~/.hermes/hermes-agent/`) is always shared across profiles.

**PITFALL:** Editing `~/.hermes/config.yaml` when the active profile is at `~/Aether-Agents/home/profiles/hermes/config.yaml` changes the WRONG file. Always check with `hermes config path` first.

### Config Sections

Edit with `hermes config edit` or `hermes config set section.key value`.

| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20), `protect_last_n` (20), `hygiene_hard_message_limit` (400) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost`, `streaming` |
| `stt` | `enabled`, `provider` (local/groq/openai/mistral) |
| `tts` | `provider` (edge/elevenlabs/openai/minimax/mistral/neutts) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `base_url`, `api_key`, `max_iterations` (50), `reasoning_effort`, `max_spawn_depth` (1), `max_concurrent_children` (5), `child_timeout_seconds` (600), `subagent_auto_approve` (false), `inherit_mcp_toolsets` (true) |
| `approvals` | `mode` (manual/smart/off), `timeout` (60), `cron_mode` (deny) |
| `stt` | `enabled`, `provider` (local/groq/openai/mistral), `local.model` (tiny/base/small/medium/large-v3) |

#### Reasoning Effort — GLM-5.1 / OpenCode Go

GLM-5.1 has **thinking mode enabled by default** (Interleaved Thinking). It does NOT use OpenAI-style `reasoning_effort` levels — it's either ON or OFF via `thinking.type`. With OpenCode Go in `chat_completions` mode, `reasoning_effort` set in Hermes config is likely **ignored**. Leave `delegation.reasoning_effort: ''` (empty). See `references/opencode-go-models.md` for full details.

#### STT Model — GPU-Optimized Selection

With `stt.provider: local` (faster-whisper), choose the Whisper model based on available GPU VRAM. For RTX 4070 Ti Super 16GB: use `medium` (~5 GB VRAM, very good Spanish accuracy). Set with `hermes config set stt.local.model medium`. First use auto-downloads the model.
| `checkpoints` | `enabled`, `max_snapshots` (50) |

#### Auxiliary Model Slots

All auxiliary sub-tasks can have their own `provider`, `model`, `base_url`, `api_key`, `timeout`, and `extra_body` under `auxiliary.<slot>:`. The full list:

| Slot | Purpose | Recommended model |
|------|---------|-------------------|
| `vision` | Image analysis | Multimodal model (qwen3.6-plus, gemini-2.5-flash) |
| `compression` | Context summarization | Fast cheap model (deepseek-v4-flash) |
| `web_extract` | Web content extraction | Fast cheap model (deepseek-v4-flash) |
| `session_search` | Search past conversations | Fast cheap model |
| `skills_hub` | Search/install skills | Fast cheap model |
| `title_generation` | Session titles | Fast cheap model |
| `approval` | Command-safety decisions | Fast cheap model (irrelevant if `approvals.mode: off`) |
| `mcp` | Process MCP responses | Fast cheap model |
| `curator` | Memory maintenance/cleanup | Fast cheap model |
| `flush_memories` | Flush stale memories | Fast cheap model |

**Cost optimization**: Set all non-vision auxiliary slots to a fast cheap model (e.g., deepseek-v4-flash). Leave only `vision` on a multimodal model. This dramatically reduces cost and latency since auxiliaries fire frequently.

#### Compression System

Hermes uses a **dual compression system**:

1. **Agent ContextCompressor** — fires at `threshold`% of context window (default 50%). Primary compression with accurate token counts from API.
2. **Gateway Session Hygiene** — fires at 85% of context. Safety net for sessions that accumulate messages between turns (e.g., Telegram overnight).

**Algorithm**: When threshold is hit, the conversation is split into Head (system prompt + first exchange, always preserved), Middle (old history, summarized by the compression model), and Tail (last N messages, preserved intact using `target_ratio` and `protect_last_n`).

**Config values**:
- `threshold` (0.50 default): Fraction of context that triggers compression
- `target_ratio` (0.20 default): Fraction of threshold tokens reserved as "protected tail"
- `protect_last_n` (20 default): Minimum recent messages always preserved
- `hygiene_hard_message_limit` (400 default): Hard message count limit for gateway hygiene safety net

Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

### Providers

20+ providers supported. Set via `hermes model` or `hermes setup`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `hermes auth` |
| OpenAI Codex | OAuth | `hermes auth` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| Google Gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API key | `XAI_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| MiniMax CN | API key | `MINIMAX_CN_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Xiaomi MiMo | API key | `XIAOMI_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| AI Gateway (Vercel) | API key | `AI_GATEWAY_API_KEY` |
| OpenCode Zen | API key | `OPENCODE_ZEN_API_KEY` |
| OpenCode Go | API key | `OPENCODE_GO_API_KEY` |
| Qwen OAuth | OAuth | `hermes login --provider qwen-oauth` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |

### Custom Providers (Third-Party Proxies & Local Endpoints)

For Anthropic-compatible proxies, local LLMs, or any endpoint not in the built-in list:

```yaml
```yaml
custom_providers:
  - name: aiprimetech
    base_url: https://aiprimetech.io          # NO /v1 — Hermes adds /v1/messages for anthropic_messages
    api_key: sk-...                             # Direct key (use if key_env fails with systemd)
    # key_env: AIPRIMETECH_API_KEY             # Alt: env var name (may not work with systemd)
    api_mode: anthropic_messages                # REQUIRED for Anthropic-compatible proxies
    models:                                     # REQUIRED — no /v1/models endpoint
      claude-sonnet-4-6:
        context_length: 256000
      claude-opus-4-6:
        context_length: 256000
```

Then reference as `custom:<name>`:
```yaml
model:
  provider: custom:aiprimetech
  default: claude-opus-4-6
```

**`api_mode` values:**
- `chat_completions` — OpenAI-compatible (default, auto-detected from URL patterns like `/v1/`)
- `anthropic_messages` — Required for Anthropic-native endpoints (aiprimetech.io, Azure Anthropic proxies). Without this, Hermes sends OpenAI-format messages to an Anthropic endpoint → authentication errors, empty responses, or garbled output.

**Pitfall:** For any Anthropic-compatible proxy (aiprimetech.io, Azure Anthropic, etc.), you MUST set `api_mode: anthropic_messages`. The auto-detection only works for recognizable URL patterns (`anthropic.com`, `openai.com`), not third-party domains.

**Pitfall:** `key_env` takes an **environment variable NAME**, not a raw API key. Put the key in `.env` and reference it: `key_env: MY_PROXY_API_KEY` → `export MY_PROXY_API_KEY=sk-...` in `.env`. **However**, when Hermes runs as a systemd service, it does NOT load `~/.bashrc` — so env vars defined there are invisible. If `key_env` fails with "Token prefix: no-key-requi..." or 401 auth errors, use `api_key: sk-...` directly in `config.yaml` instead. The key is stored in `.env` (gitignored) via `config.yaml` which Hermes reads directly.

**Pitfall — base_url for Anthropic-mode:** When `api_mode: anthropic_messages`, Hermes appends `/v1/messages` to `base_url` automatically. Do NOT include `/v1` in the base_url — it will double to `/v1/v1/messages`. Use `base_url: https://aiprimetech.io` (NOT `https://aiprimetech.io/v1`). For `chat_completions` mode, do include `/v1` since Hermes appends `/chat/completions` (not `/v1/chat/completions`).

**Pitfall — Zero models on Anthropic-mode custom providers:** Custom providers with `api_mode: anthropic_messages` do NOT have a `/v1/models` endpoint (that's an OpenAI convention). Without a models list, Hermes shows "0 models" when switching, even though the API works fine via curl. **You MUST add a `models` dict** with each model name and its context length. Without it, `/model custom:<name>` returns zero models and the provider appears broken.

```yaml
custom_providers:
  - name: aiprimetech
    base_url: https://aiprimetech.io/v1
    key_env: AIPRIMETECH_API_KEY
    api_mode: anthropic_messages
    models:                               # ← REQUIRED for Anthropic-mode providers
      claude-sonnet-4-6:
        context_length: 200000
      claude-opus-4-6:
        context_length: 200000
```

Then switch with: `/model custom:aiprimetech:claude-opus-4-6`

Full provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

**API model verification:** When testing whether a proxy serves legitimate models, use the three-test protocol (identity probe → physical reasoning → logic puzzle) and structural fingerprinting. See `references/api-model-verification.md`.

### Toolsets

### Toolsets

Enable/disable via `hermes tools` (interactive) or `hermes tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch (all four tools) |
| `file-read` | **Read-only file tools:** `read_file`, `search_files` (split from `file`) |
| `file-write` | **File modification tools:** `write_file`, `patch` (split from `file`) |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `messaging` | Cross-platform message sending |
| `search` | Web search only (subset of `web`) |
| `todo` | In-session task planning and tracking |
| `rl` | Reinforcement learning tools (off by default) |
| `moa` | Mixture of Agents (off by default) |
| `homeassistant` | Smart home control (off by default) |
| `hermes-orchestrator` | **Orchestrator-only tools:** read context, research, plan, and delegate. No implementation tools. Used by the Hermes orchestrator profile to force delegation. |

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

#### Structural Delegation Enforcement (hermes-orchestrator toolset)

The `hermes-orchestrator` toolset is a custom toolset designed to **structurally enforce delegation** by removing implementation tools from the orchestrator's tool schema. When an LLM cannot call `write_file` or `terminal`, it cannot implement code directly — it must delegate.

**Why `file-read` and `file-write` exist:** The `disabled_toolsets` config subtracts ALL tools in a toolset. If you disable the `file` toolset, you also lose `read_file` and `search_files` — tools the orchestrator needs for context. Splitting `file` into `file-read` and `file-write` lets you disable only the write portion.

**Hermes orchestrator profile config (granular toolsets with terminal write restriction — recommended):**
```yaml
# In ~/Aether-Agents/home/profiles/hermes/config.yaml
toolsets:
  - web
  - file-read
  - vision
  - skills
  - todo
  - memory
  - session_search
  - clarify
  - cronjob
  - tts
  - messaging
  - terminal              # Terminal ENABLED for git, systemctl, cp, rm, etc.
agent:
  disabled_toolsets:
    - file-write      # Blocks write_file, patch
    - code_execution  # Blocks execute_code
    - delegation       # Blocks delegate_task (safety net)
  # NOTE: terminal is NOT disabled — write commands are filtered by pre_tool_call hook
hooks:
  pre_tool_call:
    - matcher: "terminal"
      command: "/home/prometeo/Aether-Agents/home/profiles/hermes/agent-hooks/block-write-commands.sh"
      timeout: 5
hooks_auto_accept: false
platform_toolsets:
  cli:
    - web
    - file-read
    - vision
    - skills
    - todo
    - memory
    - session_search
    - clarify
    - cronjob
    - tts
    - messaging
    - terminal
  telegram:
    - web
    - file-read
    - vision
    - skills
    - todo
    - memory
    - session_search
    - clarify
    - cronjob
    - tts
    - messaging
    - terminal
```

This creates **defense-in-depth**: `disabled_toolsets` removes `write_file`/`patch`/`execute_code`/`delegate_task` from the tool schema (the LLM can't even see them), while the `pre_tool_call` hook blocks write commands in terminal via regex (the LLM can see terminal but can't use it to write files). Terminal allows `git push`, `systemctl restart`, `cp`, `mv`, `rm`, `pip install`, and read-only commands. See `references/terminal-write-restriction.md` for full details.

**Why granular toolsets instead of `hermes-orchestrator`:** The `hermes-orchestrator` composite toolset includes `delegate_task` directly. Using `disabled_toolsets: [delegation]` should remove it at the low-level tool resolution, but some code paths (TUI banner, etc.) call `get_tool_definitions()` without passing `disabled_toolsets`, causing `delegate_task` to appear available. Listing granular toolsets avoids this entirely — `delegate_task` is never included because only `delegation` and `hermes-orchestrator` contain it, and neither is listed.

**Result:** Hermes has ~15 tools (read context, NO delegate), and CANNOT call `write_file`, `patch`, `execute_code`, or `delegate_task` — these are removed from the tool schema by `disabled_toolsets`. However, **terminal write commands are NOT blocked in TUI mode** because the `pre_tool_call` hook is not registered by `tui_gateway/` at startup (only CLI and gateway modes register hooks). Terminal is available and unrestricted for writes in TUI. Other Daimons (Hefesto, Etalides, etc.) continue using the full `hermes-cli` toolset.

**Verification script:** `scripts/verify-orchestrator-toolset.py` in the `orchestration` skill directory checks that the toolset resolution and subtraction produce the expected final toolset.

**Important:** `disabled_toolsets` subtraction happens AFTER `enabled_toolsets` resolution. If both `hermes-orchestrator` (which includes `read_file`) and `disabled_toolsets: [file]` are set, `read_file` IS removed because it belongs to the `file` toolset. Use `disabled_toolsets: [file-write]` instead.

**PITFALL — `delegate_task` appears in TWO toolsets:** The `delegate_task` tool is included in both the `delegation` toolset (which only contains `delegate_task`) AND the `hermes-orchestrator` toolset (which contains it alongside other orchestrator tools). This means:

1. Adding `delegation` to `disabled_toolsets` attempts to remove `delegate_task`, and at the low-level tool resolution (`model_tools.py: _compute_tool_definitions`), it IS removed via `difference_update({delegate_task})`. So `disabled_toolsets: [delegation]` SHOULD work.

2. HOWEVER, at the high-level platform resolution (`tools_config.py: _get_platform_tools`), `disabled_toolsets` subtracts **toolset names** from the enabled set, not tool names. So `{hermes-orchestrator} - {delegation}` = `{hermes-orchestrator}` (the names don't match, so `hermes-orchestrator` stays). Then when resolved to tools, ALL tools in `hermes-orchestrator` (including `delegate_task`) are included.

3. Whether `disabled_toolsets: [delegation]` actually removes `delegate_task` depends on which code path resolves the tools. The `AIAgent` class passes `disabled_toolsets` to `get_tool_definitions()`, which performs tool-name-level subtraction (removes `delegate_task`). But some code paths (like the TUI banner) only call `get_tool_definitions(enabled_toolsets=...)` WITHOUT passing `disabled_toolsets`, so `delegate_task` can appear available even when it shouldn't be.

**If `disabled_toolsets: [delegation]` doesn't reliably remove `delegate_task`, the recommended alternative is to NOT use the `hermes-orchestrator` composite toolset and instead list individual toolsets granularly in `platform_toolsets` with terminal write restriction via `pre_tool_call` hook:**

```yaml
platform_toolsets:
  cli:
    - web
    - file-read
    - vision
    - skills
    - todo
    - memory
    - session_search
    - clarify
    - cronjob
    - tts
    - messaging
    - terminal
  telegram:
    - web
    - file-read
    - vision
    - skills
    - todo
    - memory
    - session_search
    - clarify
    - cronjob
    - tts
    - messaging
    - terminal
agent:
  disabled_toolsets:
    - file-write
    - code_execution
    - delegation
hooks:
  pre_tool_call:
    - matcher: "terminal"
      command: "<profile_dir>/agent-hooks/block-write-commands.sh"
      timeout: 5
```

This approach avoids the ambiguity entirely because none of the individual toolsets include `delegate_task` (only `delegation` and `hermes-orchestrator` do). The `disabled_toolsets` line is a safety net in case any MCP toolset or future composite toolset re-introduces `delegate_task`. Terminal is enabled at platform level but write commands are filtered by the hook.

---

### `pre_tool_call` Hooks — Terminal Write Restriction (⚠️ RUNTIME GAP)

The `pre_tool_call` hook for terminal write restriction blocks 14+ command patterns in the script logic. Three rounds of script-level penetration testing closed all known bypass vectors. **However, as of 2026-05-06, the hook is NOT executing at runtime** — the Hermes gateway does not invoke the `pre_tool_call` hook before terminal tool calls despite correct config. All 12 write vectors (redirect, heredoc, python -c, tee, sed -i, perl -e, node -e, dd of=, install -m, awk, printf, curl -o) pass through unblocked. Only Layer 1 (`disabled_toolsets`) is active. See `references/terminal-write-restriction.md` for the full documentation, audit results, and setup steps.

**Key design decisions:**
- **No `/tmp/` exception** — allowing redirects to `/tmp/` creates a two-step bypass (write script to `/tmp/`, execute it). Only `/dev/` redirects are allowed.
- **All `python -c` blocked** — multiline strings bypass same-line regex detection of `open()`. Blocking all `python -c` is simpler and more bulletproof than pattern-matching dangerous functions.
- **All `perl -e` blocked** — same rationale as `python -c`. Perl one-liners can write files without `-i` via `open()`.
- **`curl -o` / `wget -O` blocked** — download-to-disk is file creation. Use `pip install` for packages.
- **`dd of=` blocked** — arbitrary file writing via dd output.
- **`install -m` blocked** — creates files with permissions.

**Three-layer defense:**
1. `disabled_toolsets: [file-write, code_execution, delegation]` — removes tools from schema (architectural)
2. `pre_tool_call` hook with `block-write-commands.sh` — regex filter on terminal commands (architectural)
3. SOUL.md "NEVER implement" rule — behavioral reinforcement (prompt-based, not architectural)

The corrected script template is at `scripts/block-write-commands.sh` — copy it to `<profile_dir>/agent-hooks/` and `chmod +x`.

### `hermes config set` and YAML Falsy Values

`hermes config set` does NOT quote string values. Any value that YAML interprets as boolean/null will be written without quotes and parsed incorrectly. Affected values: `off`, `on`, `yes`, `no`, `true`, `false`, `null`, `~`.

```bash
# BUG: hermes config set approvals.mode off → writes "mode: false" (boolean)
hermes config set approvals.mode off   # WRONG — writes mode: false

# FIX: Edit config.yaml directly or verify after setting
hermes config set approvals.mode 'off'  # Still writes mode: false!
# Must manually edit: mode: 'off'  (with quotes)
```

Always verify after setting: `grep 'mode' config.yaml`. See references/auxiliary-models.md Pitfall #0 for the full list and workaround.

### `pre_tool_call` Hooks (Command Filtering)

Hermes supports shell hooks that fire before every tool execution. The `pre_tool_call` hook receives JSON on stdin with `{tool_name, tool_input: {command: "..."}}` and returns either `{}` (allow) or `{"decision": "block", "reason": "..."}` (block).

**Configuration in config.yaml:**
```yaml
hooks:
  pre_tool_call:
    - matcher: "terminal"          # Regex matching tool name
      command: "/path/to/script.sh" # Shell script to execute
      timeout: 5                    # Seconds
hooks_auto_accept: false           # Prompt before accepting new hooks
```

**Hook script protocol:**
1. Script receives JSON on stdin
2. Parse `tool_input.command` with `jq`
3. Match against dangerous patterns
4. Return `{"decision": "block", "reason": "..."}` to block, or `{}` to allow

**Orchestrator write-restriction pattern** — When using `disabled_toolsets: [file-write]` to block `write_file`/`patch` tools but still needing terminal for `git push`, `systemctl`, etc., add a `pre_tool_call` hook to block write commands in terminal. This creates defense-in-depth: tool-level blocking (tools removed from schema) + command-level blocking (regex filter). See `references/terminal-write-restriction.md` for the full script template and config.

**Python hook variant** — You can also register hooks via Python plugin with `ctx.register_hook("pre_tool_call", callback)`. The callback receives `(tool_name, args, task_id, **kwargs)` and can return `{"action": "block", "message": "..."}` to block. Python hooks run before shell hooks.

### Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Secret redaction is **off by default** — tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) passes through unmodified. If the user wants Hermes to auto-mask strings that look like API keys, tokens, and secrets before they enter the conversation context and logs:

```bash
hermes config set security.redact_secrets true       # enable globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — toggling it mid-session (e.g. via `export HERMES_REDACT_SECRETS=true` from a tool call) will NOT take effect for the running process. Tell the user to run `hermes config set security.redact_secrets true` in a terminal, then start a new session. This is deliberate — it prevents an LLM from flipping the toggle on itself mid-task.

Disable again with:
```bash
hermes config set security.redact_secrets false
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: manual`), Hermes prompts the user before running shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). The modes are:

- `manual` — always prompt (default)
- `smart` — use an auxiliary LLM to auto-approve low-risk commands, prompt on high-risk
- `off` — skip all approval prompts (equivalent to `--yolo`)

```bash
hermes config set approvals.mode smart       # recommended middle ground
hermes config set approvals.mode off          # bypass everything (full auto-approve)
```

**PITFALL:** `hermes config set approvals.mode off` writes Python `false` to YAML instead of the string `'off'`. If you run this command, verify with `grep approvals config.yaml` — you may need to manually edit the file to change `mode: false` to `mode: 'off'`. The other string values (`manual`, `smart`) are not affected because they don't look like Python booleans.

**PITFALL:** `hermes config set delegation.api_key <raw_key>` writes the key directly into `config.yaml` as plaintext instead of an env var reference (`${OPENCODE_GO_API_KEY}`). Always verify after setting and replace hardcoded keys with env var references.

**WSL CUDA PITFALL:** Even after installing nvidia-cublas-cu12 etc. via pip and setting LD_LIBRARY_PATH in `.bashrc`, the gateway systemd service does NOT inherit shell environment variables. You must add `Environment="LD_LIBRARY_PATH=..."` to the systemd service file (`~/.config/systemd/user/hermes-gateway-<profile>.service`) and run `systemctl --user daemon-reload && hermes gateway restart`. Without this, faster-whisper falls back to CPU in the gateway process.

Per-invocation bypass without changing config:
- `hermes --yolo …`
- `export HERMES_YOLO_MODE=1`

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

#### Delegation (Subagent Orchestration)

Hermes can spawn child agents to handle subtasks. Key settings:

```bash
# Enable full multi-layer orchestration (agents can delegate to agents)
hermes config set delegation.max_spawn_depth 2    # default=1, set 2 for multi-layer

# Auto-approve subagent commands (no manual approval per command)
hermes config set delegation.subagent_auto_approve true  # default=false

# Other delegation settings
hermes config set delegation.max_iterations 50           # max turns per subagent
hermes config set delegation.max_concurrent_children 5   # parallel subagents
hermes config set delegation.child_timeout_seconds 600   # timeout per subagent
hermes config set delegation.inherit_mcp_toolsets true   # subagents get parent's MCP tools
```

**`max_spawn_depth`** controls delegation depth:
- `1` (default): only Hermes can spawn subagents. Subagents cannot delegate further.
- `2`: subagents can also delegate tasks, enabling multi-layer orchestration (Hermes → Hefesto → further subagent).
- Higher values allow deeper chains but increase complexity.

**`subagent_auto_approve`** controls whether subagent commands need manual approval:
- `false` (default): subagent commands are subject to the same `approvals.mode` rules.
- `true`: subagents bypass approval entirely, running commands freely.

### Display Streaming

By default, CLI responses arrive all at once (buffered). Enable streaming for token-by-token display:

```bash
hermes config set display.streaming true
```

After changing, run `/reset` (CLI) or restart the gateway for changes to take effect. Streaming is most noticeable in CLI sessions — gateway (Telegram, Discord) platforms handle streaming differently per platform adapter.

Note: `display.streaming` is a boolean (`true`/`false`). Unlike `approvals.mode`, this value is a proper YAML boolean so `hermes config set` handles it correctly without quoting.

### Terminal Write Restriction Hook (Orchestrator Pattern)

When using Hermes as a pure orchestrator (no direct implementation), restrict terminal write commands via a `pre_tool_call` shell hook. This enforces delegation architecturally — the LLM physically cannot write files via terminal, even if the SOUL.md rule is ignored.

**Three-layer defense:**
1. `disabled_toolsets: [file-write, code_execution, delegation]` — removes `write_file`, `patch`, `execute_code`, `delegate_task` from tool schema
2. `pre_tool_call` hook — bash script that blocks write patterns in terminal commands
3. SOUL.md — behavioral instruction ("NEVER implement")

**Pitfall — `yaml.dump` loses comments:** When modifying `config.yaml` via Python (`yaml.safe_load` → modify dict → `yaml.dump`), ALL comments are stripped. This happened during the Olympus v3 implementation (2026-05-08) — the entire comments section of config.yaml was lost. `ruamel.yaml` preserves comments but is not installed by default. Alternatives: (1) Use `hermes config set` for simple key=value changes (but watch for YAML falsy coercion — `off` becomes `false`), (2) Use Python `sed`-like line replacement for surgical edits that preserve comments, (3) Install `ruamel.yaml` (`pip install ruamel.yaml`) and use `YAML().load()` / `YAML().dump()`. If comments are lost, reconstruct from memory or git history — don't leave the config bare.

**Config:**
```yaml
agent:
  disabled_toolsets:
    - file-write      # Blocks write_file, patch
    - code_execution  # Blocks execute_code
    - delegation       # Blocks delegate_task (safety net)

hooks:
  pre_tool_call:
    - matcher: "terminal"
      command: "/path/to/profile/agent-hooks/block-write-commands.sh"
      timeout: 5

# Terminal MUST be added to platform_toolsets (it was removed from disabled_toolsets)
platform_toolsets:
  cli:
    - web
    - file-read
    - vision
    - skills
    - todo
    - memory
    - session_search
    - clarify
    - cronjob
    - tts
    - messaging
    - terminal
  telegram:
    # ... same list including terminal
```

**Hook script** (`agent-hooks/block-write-commands.sh`) — blocks 15+ write patterns:
- `sed -i / --in-place`, `perl -i`, `perl -e`
- `patch`
- File redirects (`>`, `>>`) — only `/dev/` exempt (NO `/tmp/` exemption — prevents two-step bypass)
- `tee` to files (not `/dev/`)
- `python -c`, `node -e writeFile`, `ruby -e File.write`
- Heredocs feeding interpreters (`python3 <<`, `bash <<`, `node <<`, etc.)
- `awk >`, `curl -o`, `wget -O`, `dd of=`, `install -m`

**Role-reinforcing messages:** Block reasons use Spanish: `"Delega a Hefesto — eres orquestador, no implementador. [specific reason]."` instead of technical `"blocked: ..."`.

**Key pitfalls:**
- `/tmp/` exemption enables a two-step bypass (write script to /tmp/, execute it). Remove it.
- Multiline `python -c` with `open()` on a different line escapes single-line regex detection of `open()`. Block ALL `python -c`.
- `perl -e` without `-i` can still write files. Block ALL `perl -e`, not just `perl -i`.
- Heredoc feeding (`python3 << 'EOF'`) bypasses `-c` detection. Block interpreter+heredoc patterns.
- The hook path MUST use the profile directory (e.g., `~/Aether-Agents/home/profiles/hermes/agent-hooks/`), NOT `~/.hermes/agent-hooks/`.
- `hooks_auto_accept: false` ensures hooks fire every time without prompting.

**⚠️ KNOWN ISSUE — Hook not executing in TUI mode (2026-05-06):**
The `pre_tool_call` hook script works correctly when tested manually, but it is NOT invoked when running `hermes --tui`. Root cause confirmed: `tui_gateway/server.py` never calls `register_from_config()` during startup, so shell hooks are never registered in the plugin manager. CLI mode (`hermes chat`) and gateway mode (`hermes gateway run`) both register hooks correctly. **Only Layer 1 (disabled_toolsets) is active in TUI mode.** Layer 2 (shell hook) is dead in TUI but works in CLI/gateway. Fix: add `register_from_config(load_config(), accept_hooks=False)` to TUI gateway startup. See `references/terminal-write-restriction.md` for full details, source code evidence, and verification commands.

**⚠️ KNOWN ISSUE — `pip install` blocked by write-restriction hook:**
The `block-write-commands.sh` hook matches `\binstall\s+-` which blocks `pip install -e .` (editable install) and `pip install -e /path/` as false positives. The hook reports "Install creates files." even though package installation is a legitimate read-write operation, not a code-writing bypass. **Workarounds:** (1) Run `pip install` commands from a profile that doesn't have the write-restriction hook (e.g., the gateway profile or a bare shell), (2) Use `pip install /path/` WITHOUT `-e` (editable mode) which isn't caught by this regex, but note that non-editable installs copy files instead of linking — changes to source won't take effect until reinstall, (3) Delegating to Hefesto works because Daimon profiles don't have this hook. This especially affects installing local packages like `olympus-mcp` after a venv migration.

**Verification after setup:**
```bash
echo '{"tool_name":"terminal","tool_input":{"command":"echo test > file.py"}}' | bash /path/to/block-write-commands.sh
# Expected: {"decision": "block", "reason": "Delega a Hefesto — ..."}

echo '{"tool_name":"terminal","tool_input":{"command":"git status"}}' | bash /path/to/block-write-commands.sh
# Expected: {}
```

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `~/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

### RL Training (Tinker-Atropos)

Built-in RL fine-tuning pipeline using GRPO + LoRA. Orchestrated through `rl_*` tools, requires separate services.

**Requirements:**
- `TINKER_API_KEY` + `WANDB_API_KEY` (both required)
- Python >= 3.11
- `tinker-atropos/` submodule in Hermes root

**Available tools (off by default, enable with `hermes tools enable rl`):**

| Tool | Purpose |
|------|---------|
| `rl_list_environments` | Discover available environments (e.g., GSM8K) |
| `rl_select_environment` | Load an environment and show config |
| `rl_get_current_config` | View configurable and locked fields |
| `rl_edit_config` | Modify group_size, batch_size, etc. |
| `rl_start_training` | Launch training (3 processes: Atropos API, Tinker Trainer, Environment) |
| `rl_check_status` | Monitor progress + WandB metrics |
| `rl_stop_training` | Stop running job |
| `rl_get_results` | Final metrics + LoRA weights path |
| `rl_list_runs` | List active and completed runs |
| `rl_test_inference` | Quick test via OpenRouter (no Tinker key needed) |

**Architecture:**
- Your machine runs Atropos (trajectory API, localhost:8000) + the environment (dataset + scoring)
- Tinker cloud (thinkingmachines.ai) runs GPU training (forward-backward, LoRA updates, checkpoints)
- Output: LoRA adapter weights saved locally

**Config example:**
```yaml
# The rl toolset auto-enables when TINKER_API_KEY + WANDB_API_KEY are present
# No config.yaml changes needed — credentials go in .env
```

This is a research/ML feature. For daily use (coding, automation, chat), it's irrelevant. For fine-tuning workflows, see the [RL Training docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/rl-training).

**Cost reality check:** Tinker charges per million tokens (prefill, sample, train). For Qwen3.6-35B-A3B: prefill $0.36/M, sample $0.89/M, train $1.07/M. With default settings (batch_size=128, group_size=16), each training step costs ~$6.19. Realistic scenarios:
- 50-100 steps (PoC test): $310-620
- 300-500 steps (basic agent): $1,850-3,100
- 1000-2000 steps (functional agent): $6,200-12,400
- 3000-5000 steps (production quality): $18,600-31,000+

A more practical approach: generate SFT data with `save_trajectories: true`, fine-tune locally with Unsloth on a rented A100 ($1-2/hr on RunPod), and only consider Tinker RL if SFT results need refinement. See the `unsloth` skill for GPU selection and cost estimates.

### Self-Improvement & Background Maintenance (Heartbeats)

Hermes runs several background loops that maintain and improve itself without user intervention. These are triggered by activity patterns, not by explicit cron schedules:

**1. Curator (skill maintenance)**
Runs every 7 days (configurable) when the agent has been idle 2+ hours. Two-phase process:
- Phase 1 (deterministic): Skills unused 30+ days → stale, 90+ days → archived (not deleted, recoverable with `hermes curator restore`)
- Phase 2 (LLM review): Auxiliary model reviews skills, proposes consolidations/patches

Config:
```yaml
curator:
  enabled: true
  interval_hours: 168        # 7 days
  min_idle_hours: 2          # Only run when idle
  stale_after_days: 30
  archive_after_days: 90
  backup:
    enabled: true
    keep: 5                   # Keep 5 snapshots before pruning
```

Uses `auxiliary.curator` model slot (set to a cheap model like deepseek-v4-flash).

CLI commands:
```bash
hermes curator status         # Last run, counts, pinned list, LRU top 5
hermes curator run            # Trigger review now
hermes curator run --dry-run  # Preview only, no mutations
hermes curator run --sync     # Block until LLM pass finishes
hermes curator backup         # Manual snapshot
hermes curator rollback       # Restore from newest snapshot
hermes curator rollback --list
hermes curator pin <skill>    # Protect from auto-transitions
hermes curator unpin <skill>
hermes curator restore <skill>  # Move archived skill back to active
hermes curator pause/resume
```

**Pinned skills** are off-limits to both curator auto-transitions AND the agent's `skill_manage` tool. Pin important skills before the first curator run.

**2. Memory Nudge & Flush**
- `nudge_interval: 10` — every 10 user turns, reminds the agent to consider saving memories
- `flush_min_turns: 6` — before context loss (compression, /new, /reset, exit), gives the agent one turn to save memories (only if session had 6+ user turns)

**3. Skill Creation Nudge**
- `creation_nudge_interval: 15` — every 15 tool-calling iterations, reminds the agent to consider saving a skill

**4. Cron Ticker (gateway only)**
Gateway runs a background thread that ticks every 60 seconds. Each tick:
1. Checks cron job schedules, fires due jobs
2. Cleans up expired sessions
3. Flushes memory before session expiry
4. Refreshes model/provider caches

**5. Session Auto-Reset (messaging platforms)**
```yaml
session_reset:
  mode: both         # both | idle | daily | none
  idle_minutes: 1440  # 24 hours
  at_hour: 4          # 4 AM local time
```
Before reset, agent gets one turn to save memories and skills.

**First-run safety:** The curator does NOT run immediately after installation. The first observation seeds `last_run_at` to "now" and defers the first real pass by one full `interval_hours`. This gives you time to pin important skills or opt out before any mutations happen.

### Saving Conversations as Training Data

Hermes can save conversations in ShareGPT-compatible JSONL format for fine-tuning. This is the primary way to generate SFT training data from agent interactions.

```yaml
# config.yaml — enable trajectory saving
agent:
  save_trajectories: true   # default: false
```

When enabled, each completed conversation is appended to `trajectory_samples.jsonl` in the working directory. Failed/incomplete conversations go to `failed_trajectories.jsonl`.

**What gets saved:**
- Full conversation in ShareGPT format (`from: system/human/gpt/tool`, `value: content`)
- Tool calls normalized to `｢sched｣...｣/sched｣` XML tags with parsed JSON arguments
- Tool responses grouped by parent assistant turn
- Reasoning normalized to `｢think｣...｣/think｣` tags (regardless of original format)
- Metadata: model name, timestamp, `completed` flag
- Every `gpt` turn guaranteed to have a `｢think｣` block (empty if no reasoning)

**Batch processing** for generating large datasets:
```bash
python batch_runner.py \
    --dataset_file=data/prompts.jsonl \
    --batch_size=20 \
    --run_name=my_run \
    --model=anthropic/claude-sonnet-4.6 \
    --num_workers=4 \
    --max_turns=15
```

Batch runner adds extra fields: `tool_stats`, `tool_error_counts`, `toolsets_used`, `api_calls`, `prompt_index`. Output goes to `data/<run_name>/trajectories.jsonl`.

**Privacy:** Use `ephemeral_system_prompt` to set a system prompt that guides behavior but is NOT saved to trajectory files (keeps training data clean):
```python
agent = AIAgent(
    model="...",
    save_trajectories=True,
    ephemeral_system_prompt="You are a SQL expert. Only answer database questions.",
)
```

**PITFALL: `platform_toolsets` overrides `toolsets` top-level.** When Hermes starts via a platform (CLI, Telegram, etc.), it resolves tools from `platform_toolsets.<platform>`, NOT from the top-level `toolsets` key. If you change `toolsets: [hermes-orchestrator]` at the top but leave `platform_toolsets.cli` listing old per-toolset names (like `file`, `terminal`, `code_execution`), the old tools OVERRIDE the top-level config. Always update BOTH the top-level `toolsets` AND the `platform_toolsets` section for every platform the agent operates on. The `agent.disabled_toolsets` key is a global safety net that applies AFTER platform resolution, but don't rely on it alone — set both layers consistently.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See the Tools & Skills section above.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — free tier: set `GROQ_API_KEY`
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — set `MISTRAL_API_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, groq, openai, mistral
  local:
    model: base          # tiny, base, small, medium, large-v3
    language: ''         # empty = auto-detect, or set 'es', 'en', etc.
```

**GPU verification script:** After configuring STT, run `bash scripts/verify_cuda_stt.sh` from the hermes-agent skill directory to confirm faster-whisper is using GPU (CUDA) and not falling back to CPU.

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| MiniMax | `MINIMAX_API_KEY` | Paid |
| Mistral (Voxtral) | `MISTRAL_API_KEY` | Paid |
| NeuTTS (local) | None (`pip install neutts[all]` + `espeak-ng`) | Free |

Voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

---

## Spawning Additional Hermes Instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="hermes chat -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Hermes uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `pip install faster-whisper` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes login` — re-authenticate OAuth providers
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `/skill name` or `hermes -s name`

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows HTTP 400 "No models provided"**: Config file encoding issue (BOM). Ensure `config.yaml` is saved as UTF-8 without BOM.

### Configuring Auxiliary Models

Auxiliary models handle side tasks separate from the main LLM. **10 sub-task slots** can each have their own `provider`, `model`, `base_url`, `api_key`, `timeout`, and `extra_body`. See the "Auxiliary Model Slots" table above for the full list.

**Quick check — what's configured?**
```bash
hermes config | grep -A10 "Auxiliary"
```

**Cost optimization pattern — set all non-vision auxiliaries to a fast cheap model:**
```bash
# Example: all auxiliaries on deepseek-v4-flash via opencode-go
for slot in compression web_extract session_search skills_hub title_generation approval mcp curator flush_memories; do
  hermes config set auxiliary.$slot.provider opencode-go
  hermes config set auxiliary.$slot.model deepseek-v4-flash
  hermes config set auxiliary.$slot.base_url https://opencode.ai/zen/go/v1
  hermes config set auxiliary.$slot.api_key '${OPENCODE_GO_API_KEY}'
done

# Then set vision to a multimodal model (ONLY slot that must support images)
hermes config set auxiliary.vision.provider opencode-go
hermes config set auxiliary.vision.model qwen3.6-plus
hermes config set auxiliary.vision.base_url https://opencode.ai/zen/go/v1
hermes config set auxiliary.vision.api_key '${OPENCODE_GO_API_KEY}'
```

**CRITICAL:** Use `${OPENCODE_GO_API_KEY}` for OpenCode Go, NOT `${GLM_API_KEY}`. The GLM_API_KEY is only for Z.AI's direct API and returns HTTP 401 on the OpenCode Go endpoint.

**Set up vision (most common auxiliary):**
```bash
# Option 1: Google Gemini (free tier, excellent vision)
hermes config set auxiliary.vision.provider google
hermes config set auxiliary.vision.model gemini-2.5-flash
# Requires GOOGLE_API_KEY in .env

# Option 2: OpenRouter (multiple models through one key)
hermes config set auxiliary.vision.provider openrouter
hermes config set auxiliary.vision.model google/gemini-2.5-flash
# Requires OPENROUTER_API_KEY in .env

# Option 3: OpenAI
hermes config set auxiliary.vision.provider openai
hermes config set auxiliary.vision.model gpt-4o
# Requires OPENAI_API_KEY in .env
```

**Important:** Model name format depends on provider. OpenRouter uses `provider/model` (e.g., `google/gemini-2.5-flash`). Direct providers use just the model name (e.g., `gemini-2.5-flash`). After config changes, `/reset` or restart session.

**PITFALL — `hermes config set` type coercion:** Setting string values like `off`, `true`, `false` via `hermes config set` may convert them to Python booleans instead of YAML strings. For example, `hermes config set approvals.mode off` writes `mode: false` instead of `mode: 'off'`. For config keys that expect string values (`approvals.mode`: manual/smart/off), always verify the written value with `hermes config` or `cat config.yaml`, and patch manually if needed.

**OpenCode Go vision:** If using an OpenCode Go plan, the recommended vision models are `kimi-k2.5` (best value, native multimodal, chat/completions format) or `qwen3.6-plus` (1M context, strong vision). All use the same API key/endpoint. **CRITICAL:** Many Go models are text-only — see `references/auxiliary-models.md` for the full comparison table, including DeepSeek V4 (text-only despite marketing), GLM-5/5.1 (text-only), and Kimi K2.6 (text-only despite K2.5 being multimodal). When researching which models support a modality, check EVERY model in the plan, not just the well-known ones.

**Hindsight as Memory Provider:**

```bash
# 1. Start daemon and create bank (bank does NOT auto-create)
hindsight-embed daemon start --profile hermes
curl -X PUT http://localhost:9100/v1/default/banks/hermes -H 'Content-Type: application/json' -d '{}'

# 2. Create plugin config at <profile>/hindsight/config.json
# This controls auto_retain, recall_prefetch_method (reflect vs recall), memory_mode, etc.
# Without it, Hermes uses defaults.
mkdir -p <profile_dir>/hindsight
cat > <profile_dir>/hindsight/config.json << 'EOF'
{
  "auto_retain": true,
  "memory_mode": "hybrid",
  "recall_prefetch_method": "reflect",
  "recall_budget": "mid",
  "bank_id": "hermes"
}
EOF

# 3. Enable in Hermes config
hermes config set memory.provider hindsight
hermes memory status   # verify
```

Key config.json options:
- `recall_prefetch_method`: `recall` (raw facts, fast) or `reflect` (LLM-synthesized context, higher quality, +1-3s per turn)
- `memory_mode`: `simple` (facts), `hybrid` (facts + experiences), `rich` (full context)
- `llm_*` keys: override the LLM used for reflect synthesis (default: same as Hindsight profile env). Use a fast cheap model like deepseek-v4-flash.

**PITFALL: Bank creation.** The bank matching the profile name (e.g., "hermes") does NOT auto-create on first retain. You must create it manually via the API. Without it, auto-retain silently fails.

**PITFALL: Plugin config.json.** Without `<profile>/hindsight/config.json`, Hermes uses hardcoded defaults. To customize recall behavior, auto_retain, LLM for reflect, etc., create this file. It lives under the profile directory (e.g., `~/Aether-Agents/home/profiles/hermes/hindsight/config.json`), NOT under `~/.hindsight/`.

Full Hindsight setup guide: see the `hindsight` skill (`mlops/hindsight`).

**Full reference:** See `references/auxiliary-models.md` for detailed config schema, all auxiliary sections, provider/model pairs, and common pitfalls.

**Installation & Migration reference:** See `references/pip-installation-migration.md` for v0.14.0 pip install changes, git-clone→pip migration steps, wrapper script updates, systemd service paths, and version-specific pitfalls.

**OpenCode Go models:** See `references/opencode-go-models.md` for model IDs, multimodal support matrix, usage limits, and configuration patterns.

**Training data & fine-tuning costs:** See `references/training-data-and-costs.md` for ShareGPT trajectory format, Tinker RL pricing, RunPod GPU selection, Unsloth SFT setup, and cost estimates per training scenario.

**Compression tuning:** See `references/compression-tuning.md` for orchestration-optimized compression settings vs defaults, visual diagrams, and commands.

### Auxiliary models not working
Three common failure modes — the first two are subtle and the third is the most common:

**Silent failure (no error visible):** The `auto` provider can't find a backend with credentials. Fix: set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider.

**HTTP 401 "Invalid API key" — WRONG KEY:** OpenCode Go has TWO keys: `GLM_API_KEY` (for Z.AI direct API at `api.z.ai`) and `OPENCODE_GO_API_KEY` (for OpenCode Go at `opencode.ai/zen/go/v1`). They are NOT interchangeable — `GLM_API_KEY` returns 401 on the OpenCode Go endpoint and vice versa. When configuring auxiliary models with `hermes config set`, always use `${OPENCODE_GO_API_KEY}` for the `opencode.ai/zen/go/v1` endpoint. Verify with: `curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $OPENCODE_GO_API_KEY" -H "Content-Type: application/json" -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' https://opencode.ai/zen/go/v1/chat/completions`. A 200 response confirms the correct key.

**HTTP 401 "Invalid API key" — AUTO PROXY FALLBACK (MOST COMMON):** When `provider: "auto"` is set (the default for all auxiliary tasks), the auto-detection chain tries providers in order: OpenRouter → Nous Portal → Custom endpoint → Codex OAuth → API-key providers. If `OPENROUTER_API_KEY` is missing or invalid, auxiliary tasks fail with 401 **before ever reaching your configured custom endpoint** (e.g., OpenCode Go). This means even though you have valid OpenCode Go credentials, the auxiliary task never tries them because OpenRouter is tried first and fails first.

**This is the #1 cause of "Auxiliary title generation failed: HTTP 401: Invalid API key" errors.** The fix is to never leave auxiliary tasks on `auto` — explicitly set each one:

```yaml
auxiliary:
  vision:
    provider: "opencode-go"
    model: "qwen3.6-plus"
  title_generation:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  compression:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  web_extract:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  session_search:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  curator:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  skills_hub:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  approval:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
```

Or via CLI:
```bash
# All text auxiliaries on opencode-go with the CORRECT key
for slot in compression web_extract session_search skills_hub title_generation approval mcp curator flush_memories; do
  hermes config set auxiliary.$slot.provider opencode-go
  hermes config set auxiliary.$slot.model deepseek-v4-flash
  hermes config set auxiliary.$slot.base_url https://opencode.ai/zen/go/v1
  hermes config set auxiliary.$slot.api_key '${OPENCODE_GO_API_KEY}'
done
# Vision needs multimodal
hermes config set auxiliary.vision.provider opencode-go
hermes config set auxiliary.vision.model qwen3.6-plus
hermes config set auxiliary.vision.base_url https://opencode.ai/zen/go/v1
hermes config set auxiliary.vision.api_key '${OPENCODE_GO_API_KEY}'
```
See `references/auxiliary-models.md` → Pitfall #8 for full diagnosis.

### Memory Configuration

Hermes has built-in persistent memory (MEMORY.md + USER.md, 2200/1375 chars) plus 8 optional external providers. Only one external provider can be active at a time; built-in memory always runs alongside it.

```bash
hermes memory status   # Check current provider
hermes memory setup    # Interactive picker for providers
hermes memory off      # Disable external provider
```

**Provider recommendations by use case:**
- **Programming / long sessions / cross-session knowledge** → **Hindsight** (knowledge graph + `reflect` synthesis + stale detection)
- **Zero config / max privacy** → **Holographic** (local SQLite, no external deps)
- **Hands-off auto-extraction** → **Mem0** (pre-installed, local ChromaDB mode)
- **Structured navigation / filesystem hierarchy** → **OpenViking** (6 categories, tiered retrieval)
- **Multi-agent user modeling** → **Honcho** (dialectic reasoning, peer cards)

**Critical:** Only one external provider active at a time. Built-in MEMORY.md/USER.md always runs alongside.

**Memory limits are tight by default** (2200 chars for MEMORY.md, 1375 for USER.md). If filling up: increase limits in config (`memory_char_limit`, `user_char_limit`) or add an external provider for depth.

**Context file loading uses two systems** — see `references/context-files.md` for the full mechanism, cross-tool compatibility (Hermes/Cursor/Claude Code), and recommendations.

**System 1: Startup Context** (loaded once at session start, system prompt). Priority is **first-match-wins** — only ONE source is loaded:
1. `.hermes.md` / `HERMES.md` (walks cwd → git root, highest priority)
2. `AGENTS.md` / `agents.md` (cwd only)
3. `CLAUDE.md` / `claude.md` (cwd only)
4. `.cursorrules` + `.cursor/rules/*.mdc` (cwd only, all .mdc loaded together)

If `.hermes.md` is found, `AGENTS.md`/`CLAUDE.md`/`.cursorrules` are silently skipped. Do NOT place both in the same project.

**System 2: Subdirectory Hints** (loaded on-demand when tools access files in new dirs). Searches for `AGENTS.md`/`CLAUDE.md`/`.cursorrules` in ancestor dirs (up to 5 levels). Loads ALL found hints (not first-match-wins). Truncated to 8,000 chars. Does NOT search for `.hermes.md`. Injected as tool-result suffix, NOT in system prompt.

**Recommendation:** Use `AGENTS.md` — it's the only format natively supported by all three systems (Hermes, Cursor, Claude Code). Hermes does NOT have `/init` to auto-generate project context (Claude Code does).

**Startup context files have a 20,000 char hard limit** in `_truncate_content()` (70% head / 20% tail / 10% marker). Subdirectory hints have an 8,000 char limit. Neither is configurable via config.yaml — only MEMORY.md and USER.md have adjustable limits. SKILL.md has a separate 100,000 char limit with a 1,024 char description limit.

Full memory provider comparison, Hindsight configuration, and `reflect` vs `recall` explanation: see `references/auxiliary-models.md`.

### Timezone

```bash
hermes config set timezone 'America/Mexico_City'
# IANA timezone strings: 'America/New_York', 'Europe/Madrid', 'America/Bogota', etc.
```

---

## Where to Find Things

| Looking for... | Location |
|----------------|----------|
| Config options | `hermes config edit` or [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Available tools | `hermes tools list` or [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Slash commands | `/help` in session or [Slash commands reference](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) |
| Skills catalog | `hermes skills browse` or [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `hermes model` or [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Platform setup | `hermes gateway setup` or [Messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) |
| MCP servers | `hermes mcp list` or [MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) |
| Profiles | `hermes profile list` or [Profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) |
| Cron jobs | `hermes cron list` or [Cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |
| Memory | `hermes memory status` or [Memory docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| Env variables | `hermes config env-path` or [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| CLI commands | `hermes --help` or [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) |
| Gateway logs | `~/.hermes/logs/gateway.log` |
| Session files | `~/.hermes/sessions/` or `hermes sessions browse` |
| Source code | `~/.hermes/hermes-agent/` (git-clone install only — not present with pip install) |

**Note:** With `pip install hermes-agent` (v0.14.0+), source code is not installed locally. Use `pip show hermes-agent` to find package location, or clone the repo separately if needed.

---

## Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://hermes-agent.nousresearch.com/docs/developer-guide/

### Project Layout

```
hermes-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (HermesCLI)
├── hermes_state.py       # SQLite session store
├── agent/                # Prompt builder, context compression, memory, model routing, credential pooling, skill dispatch
├── hermes_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # ~3000 pytest tests
└── website/              # Docusaurus docs site
```

Config: `~/.hermes/config.yaml` (settings), `~/.hermes/.env` (API keys).

### Adding a Tool (3 files)

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Add to `toolsets.py`** → `_HERMES_CORE_TOOLS` list.

Auto-discovery: any `tools/*.py` file with a top-level `registry.register()` call is imported automatically — no manual list needed.

All handlers must return JSON strings. Use `get_hermes_home()` for paths, never hardcode `~/.hermes`.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

```bash
python -m pytest tests/ -o 'addopts=' -q   # Full suite
python -m pytest tests/tools/ -q            # Specific area
```

- Tests auto-redirect `HERMES_HOME` to temp dirs — never touch real `~/.hermes/`
- Run full suite before pushing any change
- Use `-o 'addopts='` to clear any baked-in pytest flags

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_hermes_home()` from `hermes_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met
