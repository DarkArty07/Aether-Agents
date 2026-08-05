---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.4.0
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

**See also:**
- **Provider resolution architecture:** `references/provider-resolution.md` — full chain from config.yaml → runtime_provider.py → auth.py PROVIDER_REGISTRY → credential pool. Common pitfalls: confusing CLI runner (OpenCode Go) with hermes-agent (they're separate systems with separate configs), `providers: {}` empty being normal for built-ins, `config set` not hot-reloading the running gateway, `auth.json` overriding `model.provider`.
- **MCP server configuration:** `references/mcp-server-configuration.md` — three supported transports (stdio / Streamable HTTP / SSE), OAuth 2.1 PKCE flow with **cross-WSL caveat** (callback server on `127.0.0.1`, WSL2 localhost forwarding, `hermes mcp login` guard requiring `auth: oauth`, script pattern to auto-open Chrome on Windows via `cmd.exe`), Bearer/header auth, smoke-test commands, and the cross-instance rule (Prometeo vs Aether-Agents are independent; an MCP added to one is invisible to the other).
- **Multi-instance CLI profile flag:** `references/multi-instance-cli-profile-flag.md` — why `hermes --profile prometeo` and `hermes -p prometeo` both fail with "profile does not exist" (the flag is in `--help` but NOT registered in `hermes_cli.main` — a known hermes-agent bug), the verified working `HERMES_HOME=... python -m hermes_cli.main ...` form, how the `~/.local/bin/hermes` wrapper is locked to Aether, and the optional `hermes-prometeo` wrapper recipe.

**Top 3 pitfalls when configuring hermes-agent:**

1. **Verify support in the installed code, not in adjacent configs.** Before claiming "X is not supported", grep the active venv (`~/.prometeo/.venv-hermes/lib/python*/site-packages/...`) for the actual parser. Pattern-matching from 3 stdio MCPs in a config and concluding "only stdio is supported" is exactly the wrong inference (the dispatch is `"url" in config` — one key). See `references/mcp-server-configuration.md` §"How to verify framework support".
2. **Gateway env does not auto-load profile `.env`.** `systemctl --user hermes-gateway*.service` does NOT source `home/.env` or the profile `.env`. MCP servers that need API keys (Bearer, OPENCODE_*, etc.) work from a shell smoke test but fail under the gateway. Fix: a drop-in override at `~/.config/systemd/user/hermes-gateway.service.d/override.conf` with `EnvironmentFile=`. See `references/mcp-server-configuration.md` §"Gateway env-loading pitfall".
3. **Prometeo and Aether-Agents are independent hermes-agent instances.** Separate `config.yaml`, separate `.env`, separate `hermes-gateway*.service`. Adding an MCP to one does not affect the other. Before editing, confirm which instance you are modifying by `echo $HERMES_HOME` and `pwd`.

## Memory & Configuration Pitfalls

### Pitfall: Memory Snapshot Frozen at Session Start — Char Limit Header Stale

**Symptom (observed 2026-06-05):** User raises `memory_char_limit` in `home/config.yaml` from 4000 to 32000, restarts instance, but the new system prompt still shows the OLD cap as the header: `[93% — 3,742/4,000 chars]` instead of `[15% — 3,742/32,000 chars]`.

**Root cause:** `tools/memory_tool.py` line 121-130, the `_system_prompt_snapshot` field is "frozen at load time, used for system prompt injection. Never mutated mid-session. Keeps prefix cache stable." The header `[X% — current/limit chars]` rendered in the system prompt reflects the cap that was active when the session initialized, NOT the current config.yaml value.

**Diagnostic chain (always run all 3):**
1. `grep -A 6 "^memory:" home/config.yaml` — verify target cap on disk
2. `wc -c home/memories/MEMORY.md home/memories/USER.md` — verify actual file sizes
3. Compare the `[X% — N/L chars]` header in the system prompt — L is the effective cap for THIS session. If L != config.yaml target → snapshot is stale → this session won't pick up the change, NEXT session will.

**Resolution:** The raise takes effect on the NEXT session that starts cold (new agent process → fresh `load_from_disk()` → new snapshot with new caps). No code path to reload snapshot mid-session by design.

**Do NOT:**
- Confuse an optional external memory provider with char-limit invalidation. The built-in `memory_char_limit` / `user_char_limit` in config.yaml govern the local `MEMORY.md` / `USER.md` files independently.
- Trust the rendered `[X% — N/L]` header as ground truth about config.yaml — it shows session-state, not config-state.
- Suggest that an external provider overrides built-in char limits as an explanation for stale headers. Different bug, different fix.
- Try to mutate the snapshot from inside the running agent. No public API exists. Restart is the only path.
