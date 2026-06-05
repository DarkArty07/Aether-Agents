---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.2.0
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

**Top 3 pitfalls when configuring hermes-agent:**

1. **Verify support in the installed code, not in adjacent configs.** Before claiming "X is not supported", grep the active venv (`~/.prometeo/.venv-hermes/lib/python*/site-packages/...`) for the actual parser. Pattern-matching from 3 stdio MCPs in a config and concluding "only stdio is supported" is exactly the wrong inference (the dispatch is `"url" in config` — one key). See `references/mcp-server-configuration.md` §"How to verify framework support".
2. **Gateway env does not auto-load profile `.env`.** `systemctl --user hermes-gateway*.service` does NOT source `home/.env` or the profile `.env`. MCP servers that need API keys (Bearer, OPENCODE_*, etc.) work from a shell smoke test but fail under the gateway. Fix: a drop-in override at `~/.config/systemd/user/hermes-gateway.service.d/override.conf` with `EnvironmentFile=`. See `references/mcp-server-configuration.md` §"Gateway env-loading pitfall".
3. **Prometeo and Aether-Agents are independent hermes-agent instances.** Separate `config.yaml`, separate `.env`, separate `hermes-gateway*.service`. Adding an MCP to one does not affect the other. Before editing, confirm which instance you are modifying by `echo $HERMES_HOME` and `pwd`.

### Pitfall #N — Graphify `serve` Uses Relative Path, Breaks from Gateway CWD

**Síntoma:** Agregas `mcp_servers.graphify` a `config.yaml` con `args: ["-m", "graphify.serve"]`. El gateway arranca graphify, pero `_load_graph()` falla con `FileNotFoundError: graph.json not found`. Desde shell con `python -m graphify.serve` funciona perfecto.

**Causa raíz:** `graphify.serve` lee `sys.argv[1]` para el path del graph.json, con default `graphify-out/graph.json` (relativa). Cuando lo lanza el gateway via MCP, el CWD del proceso es el del gateway (típicamente el home del venv o el directorio del usuario), NO la raíz del repo Aether-Agents. La resolución relativa falla.

**Fix correcto (pasado en sesión 06-04):**

```yaml
mcp_servers:
  graphify:
    command: /home/prometeo/Aether-Agents/home/.venv-hermes/bin/python3.11
    args:
      - -m
      - graphify.serve
      - /home/prometeo/Aether-Agents/graphify-out/graph.json  # ← ABSOLUTA, no relativa
    enabled: true
    env:
      GRAPHIFY_PROJECT: /home/prometeo/Aether-Agents
      OPENCODE_API_KEY: ${OPENCODE_API_KEY}
    timeout: 600
```

La ruta absoluta como `argv[1]` resuelve el problema sin importar el CWD del proceso.

**Diagnóstico rápido cuando graphify no arranca:**
```bash
# 1. Verifica el proceso y su CWD
GW_PID=$(systemctl --user show -p MainPID hermes-gateway.service | cut -d= -f2)
cat /proc/$GW_PID/cwd 2>/dev/null  # te dice el CWD del gateway

# 2. Verifica si la ruta existe desde ese CWD
sudo -u $(whoami) ls -l $(cat /proc/$GW_PID/cwd 2>/dev/null)/graphify-out/graph.json
# Si falla, el problema es CWD relativa

# 3. Test directo del módulo
cd / && home/.venv-hermes/bin/python -m graphify.serve /home/prometeo/Aether-Agents/graphify-out/graph.json
# Si esto funciona, confirma que el fix es pasar ruta absoluta
```

**Regla:** Cualquier MCP server que abra un archivo en el proyecto (graph.json, db.sqlite, .env) DEBE recibir la ruta absoluta via args o env var, nunca depender de CWD.
