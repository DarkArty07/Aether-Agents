# Configuration Reference

Complete reference for configuring Aether Agents profiles, model providers, and agent behavior.

---

## Configuration Layers

Aether Agents uses three layers of configuration, resolved in order of specificity:

| Layer | File | Scope | Priority |
|-------|------|-------|----------|
| **Root** | `home/config.yaml` | All Daimons (fallback) | Lowest |
| **Profile** | `home/profiles/<name>/config.yaml` | Single Daimon | Overrides root |
| **User** | `~/.hermes/config.yaml` | User's local CLI | Highest |

When a Daimon starts, it merges: profile config → root config → user config. The most specific value wins.

---

## Profile Structure

Each Daimon profile directory contains:

```
home/profiles/<daimon>/
├── config.yaml          # Profile-specific settings (gitignored for secrets)
├── config.yaml.template # Template with placeholders (tracked by git)
├── .env.example         # API key template (tracked)
├── .env                 # Actual keys (gitignored)
├── SOUL.md              # Agent identity, rules, and behavior
└── skills/              # Skill definitions (gitignored, generated)
```

### config.yaml vs config.yaml.template

- `config.yaml.template` — Tracked in git. Contains placeholders like `__AETHER_ROOT__` and `__HERMES_PYTHON__`. Safe to share.
- `config.yaml` — **Gitignored**. Generated from the template by `configure.sh`. Contains actual paths and may include API keys. Never commit this file.

After cloning, run:

```bash
bash scripts/configure.sh
```

This generates `config.yaml` from each profile's template, substituting machine-specific paths.

---

## Key Configuration Sections

### Model and Provider

```yaml
model:
  default: "anthropic/claude-sonnet-4"   # Model identifier
  provider: "openrouter"                   # Provider: openrouter, anthropic, zai, etc.
  base_url: "https://openrouter.ai/api/v1"  # Optional override
```

### Agent Identity

```yaml
agent:
  name: hermes
  role: orchestrator
  description: "Technical Lead and architect. Investigates, designs, orchestrates, and decides."
  capabilities:
    - talk_to
    - discover
    - delegate_task
    - all
  launch_command: "hermes acp"
  keep_alive: true
  max_turns: 150
  gateway_timeout: 1800
```

### Terminal Environment

```yaml
terminal:
  shell: /bin/bash
  workdir: /tmp
  background: true
```

---

## ⚠️ Personality Overlay

> **Important for Aether Agents:** The hermes-agent CLI ships with a personality system that appends a style overlay to the system prompt. The default personality is `"kawaii"`, which tells the agent to use cute expressions, sparkles, and enthusiastic tone.
>
> **This conflicts with Daimon identities.** Each Aether Agent's personality is already defined in their `SOUL.md` — a carefully crafted document specifying their role, rules, delegation gates, and communication style. The personality overlay rewrites identity statements (e.g., "You are a kawaii assistant" overrides "You are Hermes, messenger of the gods"), which breaks:
>
> - **Delegation gates** — Requires direct, structured communication
> - **Role clarity** — Daimons need clear, professional identity
> - **Decision flow** — The orchestrated delegation process depends on factual, unambiguous communication
>
> **Always set `display.personality: none` in Aether Agent profiles:**

```yaml
display:
  personality: none    # Disable overlay — use SOUL.md identity instead
```

This applies to all Daimons (Hermes, Ariadna, Hefesto, Etalides, Daedalus, Athena). The `SOUL.md` file in each profile already defines the agent's personality, rules, and communication style.

### Available Personalities

For reference, these are the built-in personalities in hermes-agent:

| Name | Style | Recommended for Aether Agents? |
|------|-------|-------------------------------|
| `none` / `default` / `neutral` | No overlay | ✅ **Yes — use this** |
| `helpful` | Friendly, generic | ❌ Overwrites identity |
| `concise` | Brief, to the point | ❌ Overwrites identity |
| `technical` | Detailed, accurate | ❌ Overwrites identity |
| `creative` | Innovative, out-of-box | ❌ Overwrites identity |
| `teacher` | Patient, examples | ❌ Overwrites identity |
| `kawaii` | Cute, sparkles | ❌ **Breaks delegation** |
| `catgirl` | Anime catgirl | ❌ |
| `pirate` | Nautical, arrr | ❌ |
| `shakespeare` | Flowery prose | ❌ |
| `surfer` | Chill, dude | ❌ |
| `noir` | Detective, moody | ❌ |
| `uwu` | Uwu speech | ❌ |
| `philosopher` | Deep, contemplative | ❌ |
| `hype` | Extremely energetic | ❌ |

### How the Personality System Works

1. `display.personality` in `config.yaml` selects a personality name (default: `"kawaii"`)
2. The name resolves against `agent.personalities` — a dict of one-line system prompt strings
3. The resolved string is injected as `agent.system_prompt` — appended to the end of the full system prompt
4. Since it appears last, it has high interpretive weight and can override earlier identity instructions

Setting `personality: none` returns an empty string, so only the `SOUL.md` identity is used.

---

## MCP Servers

Each Daimon connects to Olympus (the Aether Agents MCP server) for inter-agent communication:

```yaml
mcp_servers:
  olympus:
    command: /path/to/.venv/bin/python
    args:
      - -m
      - olympus.server
    env:
      AETHER_HOME: /path/to/Aether-Agents/home
      PYTHONPATH: /path/to/Aether-Agents/src
    enabled: true
```

Additional MCP servers can be added per-profile (e.g., Context7 for documentation lookup):

```yaml
mcp_servers:
  context7:
    command: npx
    args:
      - -y
      - "@upstreamapi/context7-mcp@latest"
    enabled: true
```

---

## Skills

Skills are loaded from:

```yaml
skills:
  external_dirs:
    - /path/to/Aether-Agents/home/skills
```

Skills are gitignored at the profile level (they're generated during setup). The shared `home/skills/` directory is the canonical source.

---

## SOUL.md — Agent Identity

Each Daimon's `SOUL.md` defines:

- **Identity** — Who the agent is (name, eponym, role)
- **Anti-bias rule** — Don't reveal model/provider
- **Core responsibilities** — What the agent does
- **Delegation gates** — Mandatory checks before execution
- **Limits** — What the agent must not do
- **Communication style** — How the agent speaks
- **Decision flow** — Processing steps

**Do not use personality overlays with custom SOUL.md files.** The personality system is designed for the base hermes-agent CLI where no SOUL.md exists. In Aether Agents, SOUL.md already provides comprehensive identity and behavior instructions.

---

## Quick Reference

| Setting | File | Key | Default | Aether Agents Value |
|---------|------|-----|---------|-------------------|
| Personality overlay | Profile config | `display.personality` | `kawaii` | `none` |
| Agent identity | `SOUL.md` | — | — | Per-Daimon |
| Model | Profile config | `model.default` | — | Per-profile |
| Provider | Profile config | `model.provider` | — | Per-profile |
| Max turns | Profile config | `agent.max_turns` | 60 | 150 (Hermes) |
| MCP server | Profile config | `mcp_servers.olympus` | — | Required |

---

**Next:** [USER_PROFILE.md](./USER_PROFILE.md) · [INSTALLATION.md](./INSTALLATION.md) · [QUICKSTART.md](./QUICKSTART.md)